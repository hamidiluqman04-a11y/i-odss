"""
End-to-end tests: the complete workflow through the HTTP API, the same way
the React app uses it (CSRF checks switched on), plus awkward real-world files.
"""
import datetime
import json

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

from apps.analytics.services.pipeline import run_analysis
from apps.datasets.csv_parser import parse_csv
from apps.datasets.models import AnalysisResult, Dataset
from tests.conftest import FIXTURES, SAMPLE_FILES

RESULT_KINDS = ["dashboard", "inventory", "forecast", "bundles", "pricing"]


class Browser:
    """A test client that behaves like the React app: CSRF cookie + X-CSRFToken header."""

    def __init__(self):
        self.client = Client(enforce_csrf_checks=True)
        assert self.client.get("/api/auth/csrf/").status_code == 200

    def _token(self):
        return self.client.cookies["csrftoken"].value

    def get(self, path):
        return self.client.get(path)

    def post_json(self, path, body=None):
        return self.client.post(path, body or {}, content_type="application/json", HTTP_X_CSRFTOKEN=self._token())

    def upload(self, name, content, **fields):
        file = SimpleUploadedFile(name, content, content_type="text/csv")
        return self.client.post("/api/datasets/", {"file": file, **fields}, HTTP_X_CSRFTOKEN=self._token())

    def delete(self, path):
        return self.client.delete(path, HTTP_X_CSRFTOKEN=self._token())


@pytest.fixture
def browser(db):
    b = Browser()
    r = b.post_json("/api/auth/register/", {"name": "Siti", "email": "siti@shop.my", "password": "kopi-susu-2025!"})
    assert r.status_code == 201
    return b


def as_json(value):
    """What a value looks like after a round trip through JSON (dates become strings)."""
    return json.loads(json.dumps(value, default=str))


# ── The full workflow, for every sample file ─────────────────────────────

@pytest.mark.parametrize("name", SAMPLE_FILES)
def test_upload_to_results_workflow(browser, name):
    content = (FIXTURES / name).read_bytes()

    # 1. Upload
    r = browser.upload(name, content)
    assert r.status_code == 201, r.content
    dataset = r.json()["dataset"]

    # 2. It appears in the dataset list
    listed = browser.get("/api/datasets/").json()["datasets"]
    assert [d["id"] for d in listed] == [dataset["id"]]

    # 3. Every result equals what the real algorithms produce for the same file,
    #    so the pages show genuine analysis, not placeholders.
    expected = as_json(run_analysis(parse_csv(name, content).rows))
    for kind in RESULT_KINDS:
        r = browser.get(f"/api/datasets/{dataset['id']}/{kind}/")
        assert r.status_code == 200, kind
        assert r.json()[kind] == expected[kind], kind

    # 4. Promo simulation on the first product
    sku = expected["pricing"]["items"][0]["sku"]
    r = browser.post_json(f"/api/datasets/{dataset['id']}/promo-simulation/", {"sku": sku, "discount_pct": 10})
    assert r.status_code == 200
    assert r.json()["simulation"]["break_even_volume_increase_pct"] == 33.3

    # 5. Delete, then everything for it is gone
    assert browser.delete(f"/api/datasets/{dataset['id']}/").status_code == 204
    assert not Dataset.objects.exists() and not AnalysisResult.objects.exists()

    # 6. Log out; the API is closed again
    assert browser.post_json("/api/auth/logout/").status_code == 204
    assert browser.get("/api/datasets/").status_code == 403


def test_changing_requests_without_csrf_token_are_refused(browser):
    content = (FIXTURES / "data_beauty.csv").read_bytes()
    file = SimpleUploadedFile("data_beauty.csv", content, content_type="text/csv")
    assert browser.client.post("/api/datasets/", {"file": file}).status_code == 403
    assert not Dataset.objects.exists()


# ── Awkward real-world files ──────────────────────────────────────────────

HEADER = "OrderID,Date,SKU,Quantity,UnitPrice\n"


def weeks_of_rows(weeks=10, price=lambda w: 10, units=lambda w: 3):
    """One sale per day for `weeks` full weeks; price and units can change per week."""
    start = datetime.date(2025, 1, 6)
    lines = []
    for day in range(weeks * 7):
        w = day // 7
        lines.append(f"O{day},{start + datetime.timedelta(days=day)},A,{units(w)},{price(w)}")
    return HEADER + "\n".join(lines) + "\n"


def named(cases):
    """Give each test case a short name instead of its (possibly huge) file content."""
    return [pytest.param(*case, id=case[0]) for case in cases]


@pytest.mark.parametrize("label, content, expected_rows", named([
    ("excel_bom_and_crlf", "﻿OrderID,Date,SKU,Quantity,UnitPrice\r\nO1,2025-01-01,A,2,10\r\n".encode("utf-8"), 1),
    ("quoted_commas", (HEADER + 'O1,2025-01-01,"Tee, Large",1,"1,200.00"\n').encode(), 1),
    ("latin1_names", (HEADER + "O1,2025-01-01,Café Crème,1,10\n").encode("latin-1"), 1),
    ("padded_headers", b" OrderID , Date ,SKU, Quantity ,UnitPrice\nO1,2025-01-01,A,1,10\n", 1),
    ("datetime_values", (HEADER + "O1,2025-01-01 13:45:00,A,1,10\n").encode(), 1),
    ("single_row", (HEADER + "O1,2025-01-01,A,1,10\n").encode(), 1),
    ("one_day_only", (HEADER + "O1,2025-01-01,A,1,10\nO2,2025-01-01,B,2,5\n").encode(), 2),
    ("blank_lines", (HEADER + "\nO1,2025-01-01,A,1,10\n\n\nO2,2025-01-02,A,1,10\n").encode(), 2),
]))
def test_unusual_but_valid_files_are_analysed(browser, label, content, expected_rows):
    r = browser.upload(f"{label}.csv", content)
    assert r.status_code == 201, (label, r.content)
    ds = r.json()["dataset"]
    assert ds["row_count"] == expected_rows
    for kind in RESULT_KINDS:
        assert browser.get(f"/api/datasets/{ds['id']}/{kind}/").status_code == 200, (label, kind)


def test_tiny_dataset_gives_honest_empty_results(browser):
    ds = browser.upload("tiny.csv", (HEADER + "O1,2025-01-01,A,1,10\n").encode()).json()["dataset"]
    forecast = browser.get(f"/api/datasets/{ds['id']}/forecast/").json()["forecast"]
    bundles = browser.get(f"/api/datasets/{ds['id']}/bundles/").json()["bundles"]
    pricing = browser.get(f"/api/datasets/{ds['id']}/pricing/").json()["pricing"]
    assert forecast["status"] == "insufficient_data" and forecast["series"] == []
    assert bundles["status"] == "insufficient_data" and bundles["pairs"] == []
    assert pricing["items"][0]["status"] == "insufficient_data" and pricing["items"][0]["ped"] is None


def test_zero_byte_file_is_rejected_by_form_validation(browser):
    r = browser.upload("empty.csv", b"")
    assert r.status_code == 400
    assert r.json()["error"]["details"]["file"] == ["The submitted file is empty."]


def test_semicolon_separated_file_with_decimal_commas_is_accepted(browser):
    content = b"OrderID;Date;SKU;Quantity;UnitPrice\nO1;2025-01-01;A;2;10,50\nO2;2025-01-02;B;1;1.250,00\n"
    r = browser.upload("european.csv", content)
    assert r.status_code == 201, r.content
    assert r.json()["dataset"]["row_count"] == 2
    metrics = browser.get(f"/api/datasets/{r.json()['dataset']['id']}/dashboard/").json()["dashboard"]["metrics"]
    assert metrics["revenue"] == 2 * 10.5 + 1250.0


def test_tab_separated_file_is_accepted(browser):
    content = b"OrderID\tDate\tSKU\tQuantity\tUnitPrice\nO1\t2025-01-01\tA\t2\t1,000.50\n"
    r = browser.upload("export.csv", content)
    assert r.status_code == 201, r.content
    metrics = browser.get(f"/api/datasets/{r.json()['dataset']['id']}/dashboard/").json()["dashboard"]["metrics"]
    assert metrics["revenue"] == 2001.0


def test_constant_sales_with_changing_price_does_not_break_storage(browser):
    """Same units every week at different prices: R² is undefined (0/0) and must not crash saving."""
    content = weeks_of_rows(weeks=10, price=lambda w: [8, 10, 12][w % 3], units=lambda w: 3).encode()
    r = browser.upload("flat.csv", content)
    assert r.status_code == 201, r.content
    item = browser.get(f"/api/datasets/{r.json()['dataset']['id']}/pricing/").json()["pricing"]["items"][0]
    assert item["status"] == "estimated"
    assert item["ped"] == 0
    assert item["r_squared"] is None          # 0/0: stored as "unknown", not as NaN
    assert item["reliability"] == "weak"
    assert item["recommendation"] == "no_recommendation"
    assert "None" not in item["plain_explain"]


def test_results_never_contain_nan_or_infinity():
    from apps.analytics.services.pipeline import json_safe
    cleaned = json_safe({"a": float("nan"), "b": [1.5, float("inf")], "c": {"d": -float("inf"), "e": "text"}})
    assert cleaned == {"a": None, "b": [1.5, None], "c": {"d": None, "e": "text"}}


@pytest.mark.parametrize("label, content, error_type", named([
    ("binary_image", b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10" * 50, None),
    ("header_only", HEADER.encode(), "empty_file"),
    ("not_a_table", b"Hello, this is a letter.\nRegards, Ali\n", "missing_columns"),
    ("all_values_invalid", (HEADER + "O1,yesterday,A,many,free\nO2,,B,-3,nan\n").encode(), "no_valid_rows"),
    ("infinite_and_nan", (HEADER + "O1,2025-01-01,A,1,inf\nO2,2025-01-01,A,nan,10\n").encode(), "no_valid_rows"),
    ("huge_field", (HEADER + "O1,2025-01-01," + "A" * 200_000 + ",1,10\n").encode(), "parse_error"),
]))
def test_broken_files_are_rejected_with_clear_errors(browser, label, content, error_type):
    r = browser.upload(f"{label}.csv", content)
    assert r.status_code == 422, (label, r.status_code, r.content[:200])
    err = r.json()["error"]
    assert err["message"]
    if error_type:
        assert err["type"] == error_type
    assert "Traceback" not in r.content.decode(errors="ignore")
    assert not Dataset.objects.exists()
