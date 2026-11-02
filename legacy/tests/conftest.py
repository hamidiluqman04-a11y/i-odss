"""
Shared test helpers for the legacy FastAPI app.

These tests are a "safety net": they record what the ORIGINAL system returns,
so that when we rebuild it in Django we can prove which numbers stayed the
same and which ones changed on purpose.
"""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

LEGACY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LEGACY / "backend"))

import main  # noqa: E402  (the legacy FastAPI app)

SAMPLES = LEGACY / "frontend" / "static" / "samples"
SNAPSHOTS = Path(__file__).resolve().parent / "snapshots"
SAMPLE_FILES = sorted(p.name for p in SAMPLES.glob("*.csv"))

# Every GET endpoint whose output depends on the uploaded data.
ANALYTICS_ENDPOINTS = [
    "metrics", "inventory", "pricing", "bundles", "forecast", "sales-trend",
    "top-skus", "category-breakdown", "regional", "sku-list", "session-summary",
]


@pytest.fixture
def client():
    # The legacy app keeps data in one global dict; reset it between tests.
    main.STORE.update({"data": None, "filename": None, "rows": 0})
    return TestClient(main.app)


def upload_bytes(client, name, content):
    return client.post("/api/upload", files={"file": (name, content, "text/csv")})


def upload_sample(client, name):
    return upload_bytes(client, name, (SAMPLES / name).read_bytes())


def capture_outputs(client, name):
    """Upload one sample file and collect every analytics response."""
    out = {"upload": upload_sample(client, name).json()}
    for ep in ANALYTICS_ENDPOINTS:
        out[ep] = client.get(f"/api/{ep}").json()
    first_sku = out["sku-list"]["skus"][0]["sku"]
    out["simulate_promo_10pct"] = client.post(
        "/api/simulate/promo", json={"sku": first_sku, "discount_pct": 10}
    ).json()
    return out
