r"""
Smoke test against a RUNNING I-ODSS server — checks the whole system from outside.

Start the backend first (and optionally the frontend), then from backend\ run:

    ..\.venv\Scripts\python scripts\smoke_test.py                         # Django directly
    ..\.venv\Scripts\python scripts\smoke_test.py http://localhost:5173   # through the React dev proxy

It logs in as the demo account from backend\.env, uploads a sample file,
reads every result, runs a promotion simulation, deletes the upload again
and logs out. Exit code 0 = every check passed.
"""
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

BACKEND = Path(__file__).resolve().parent.parent
SAMPLE = BACKEND / "tests" / "fixtures" / "data_bundling_test.csv"
load_dotenv(BACKEND / ".env")

base = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://127.0.0.1:8000"
client = httpx.Client(base_url=base, timeout=120)
failures = []


def check(label, response, expected_status):
    ok = response.status_code == expected_status
    print(f"{'PASS' if ok else 'FAIL'}  {response.status_code}  {label}")
    if not ok:
        failures.append(label)
        print(f"      expected {expected_status}, body: {response.text[:300]}")
    return response


def headers():
    return {"X-CSRFToken": client.cookies.get("csrftoken", ""), "Referer": base + "/"}


def main():
    email, password = os.environ.get("DEMO_USER_EMAIL"), os.environ.get("DEMO_USER_PASSWORD")
    if not email or not password:
        sys.exit("Set DEMO_USER_EMAIL and DEMO_USER_PASSWORD in backend/.env and run create_demo_user first.")

    try:
        check("health check", client.get("/api/health/"), 200)
    except httpx.ConnectError:
        sys.exit(f"Cannot connect to {base}. Is the server running?")

    check("data is private before login", client.get("/api/datasets/"), 403)
    check("get CSRF cookie", client.get("/api/auth/csrf/"), 200)
    check("log in as demo user", client.post("/api/auth/login/", json={"email": email, "password": password},
                                             headers=headers()), 200)

    r = check("upload sample CSV", client.post(
        "/api/datasets/", files={"file": (SAMPLE.name, SAMPLE.read_bytes(), "text/csv")}, headers=headers()), 201)
    if r.status_code != 201:
        return
    ds = r.json()["dataset"]["id"]
    check("bad file is rejected", client.post(
        "/api/datasets/", files={"file": ("bad.csv", b"Colour,Size\nRed,L\n", "text/csv")}, headers=headers()), 422)

    for kind in ["dashboard", "inventory", "forecast", "bundles", "pricing"]:
        check(f"read {kind} result", client.get(f"/api/datasets/{ds}/{kind}/"), 200)
    check("promotion simulation", client.post(f"/api/datasets/{ds}/promo-simulation/",
                                               json={"sku": "SKU-001", "discount_pct": 10}, headers=headers()), 200)
    check("request without CSRF token is refused", client.post(
        f"/api/datasets/{ds}/promo-simulation/", json={"sku": "SKU-001", "discount_pct": 10}), 403)

    check("delete the test upload", client.delete(f"/api/datasets/{ds}/", headers=headers()), 204)
    check("log out", client.post("/api/auth/logout/", headers=headers()), 204)
    check("data is private after logout", client.get("/api/datasets/"), 403)


if __name__ == "__main__":
    main()
    print()
    if failures:
        print(f"{len(failures)} check(s) FAILED: {', '.join(failures)}")
        sys.exit(1)
    print("All checks passed.")
