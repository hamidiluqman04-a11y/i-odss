import json

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from apps.datasets.models import AnalysisResult, Dataset
from tests.conftest import FIXTURES

RESULT_KINDS = ["dashboard", "inventory", "forecast", "bundles", "pricing"]


def make_user(email):
    return get_user_model().objects.create_user(username=email, email=email, password="a-strong-test-pass-123")


@pytest.fixture
def seller(db):
    return make_user("seller@example.com")


@pytest.fixture
def api(client, seller):
    client.force_login(seller)
    return client


def csv_file(name="sales.csv", content=None):
    if content is None:
        content = (FIXTURES / name).read_bytes()
    return SimpleUploadedFile(name, content, content_type="text/csv")


def upload(api, name="data_bundling_test.csv", content=None, **fields):
    return api.post("/api/datasets/", {"file": csv_file(name, content), **fields})


@pytest.fixture
def dataset_id(api):
    return upload(api).json()["dataset"]["id"]


# ── Upload: success ───────────────────────────────────────────────────────

def test_upload_returns_201_and_saves_metadata_and_results(api, seller):
    r = upload(api)
    assert r.status_code == 201
    body = r.json()
    ds = body["dataset"]
    assert (ds["original_filename"], ds["row_count"], ds["sku_count"]) == ("data_bundling_test.csv", 227, 8)
    assert (ds["date_start"], ds["date_end"]) == ("2025-01-03", "2025-03-05")
    assert ds["analysis_settings"] == {"margin": 0.4, "lead_times": {}}
    assert body["warning_count"] == 0
    saved = Dataset.objects.get(pk=ds["id"])
    assert saved.owner == seller
    assert set(saved.results.values_list("kind", flat=True)) == set(AnalysisResult.Kind.values)


def test_upload_with_custom_margin_and_lead_times(api):
    r = upload(api, margin="0.3", lead_times=json.dumps({"Peripherals": 12}))
    assert r.status_code == 201
    ds_id = r.json()["dataset"]["id"]
    inventory = api.get(f"/api/datasets/{ds_id}/inventory/").json()["inventory"]
    assert all(i["lead"] == 12 for i in inventory["items"] if i["category"] == "Peripherals")
    assert api.get(f"/api/datasets/{ds_id}/bundles/").json()["bundles"]["margin_assumption"] == 0.3


def test_upload_reports_skipped_rows(api):
    content = b"OrderID,Date,SKU,Quantity,UnitPrice\nO1,2025-01-01,A,2,10\nO2,bad,A,1,10\n"
    body = upload(api, "mixed.csv", content).json()
    assert body["dataset"]["row_count"] == 1
    assert body["dataset"]["skipped_row_count"] == 1
    assert body["warnings"][0].startswith("Row 3:")


# ── Upload: failures ──────────────────────────────────────────────────────

@pytest.mark.parametrize("name, content, error_type", [
    ("data.xlsx", b"whatever", "file_type_error"),
    ("empty.csv", b"OrderID,Date,SKU,Quantity,UnitPrice\n", "empty_file"),
    ("cols.csv", b"OrderID,Date,Colour\nO1,2025-01-01,Red\n", "missing_columns"),
    ("rows.csv", b"OrderID,Date,SKU,Quantity,UnitPrice\nO1,2025-01-01,A,0,10\n", "no_valid_rows"),
])
def test_invalid_files_give_422_and_save_nothing(api, name, content, error_type):
    r = upload(api, name, content)
    assert r.status_code == 422
    assert r.json()["error"]["type"] == error_type
    assert r.json()["error"]["message"]
    assert not Dataset.objects.exists()


def test_missing_columns_lists_detected_headers(api):
    err = upload(api, "cols.csv", b"OrderID,Date,Colour\nO1,2025-01-01,Red\n").json()["error"]
    assert err["detected_headers"] == ["OrderID", "Date", "Colour"]
    assert len(err["details"]) == 3


def test_upload_without_file_is_400(api):
    r = api.post("/api/datasets/", {})
    assert r.status_code == 400
    assert "file" in r.json()["error"]["details"]


@pytest.mark.parametrize("fields", [
    {"margin": "1.5"}, {"margin": "abc"},
    {"lead_times": '{"Skincare": 0}'}, {"lead_times": "[1, 2]"}, {"lead_times": "not json"},
])
def test_invalid_settings_are_400(api, fields):
    r = upload(api, **fields)
    assert r.status_code == 400
    assert r.json()["error"]["type"] == "validation_error"


@override_settings(FILE_UPLOAD_MAX_MEMORY_SIZE=1024)
def test_file_over_size_limit_is_413(api):
    r = upload(api)                                   # the sample is ~14 KB
    assert r.status_code == 413
    assert r.json()["error"]["type"] == "file_too_large"


def test_upload_requires_login(client, db):
    assert client.post("/api/datasets/", {"file": csv_file("data_beauty.csv")}).status_code == 403


# ── Privacy (decision D1) ─────────────────────────────────────────────────

def test_no_raw_transactions_are_stored(api, dataset_id):
    """Order IDs appear in every row of the file; none may reach the database."""
    stored = json.dumps([r.data for r in AnalysisResult.objects.all()])
    stored += json.dumps(list(Dataset.objects.values()), default=str)
    order_ids = {line.split(",")[0] for line in (FIXTURES / "data_bundling_test.csv").read_text().splitlines()[1:]}
    assert not any(oid in stored for oid in order_ids)


def test_uploads_are_handled_in_memory_only(settings):
    assert settings.FILE_UPLOAD_HANDLERS == ["django.core.files.uploadhandler.MemoryFileUploadHandler"]


# ── Listing, detail, delete, ownership ────────────────────────────────────

def test_list_shows_only_own_datasets(api, dataset_id, client):
    other = make_user("other@example.com")
    Dataset.objects.create(owner=other, original_filename="theirs.csv", row_count=1, sku_count=1,
                           date_start="2025-01-01", date_end="2025-01-01")
    names = [d["original_filename"] for d in api.get("/api/datasets/").json()["datasets"]]
    assert names == ["data_bundling_test.csv"]


def test_other_users_dataset_is_404_everywhere(api, dataset_id, client):
    client.force_login(make_user("other@example.com"))
    for path in ["", *[f"{k}/" for k in RESULT_KINDS]]:
        r = client.get(f"/api/datasets/{dataset_id}/{path}")
        assert r.status_code == 404, path
        assert r.json() == {"error": {"type": "not_found", "message": "Not found."}}
    assert client.delete(f"/api/datasets/{dataset_id}/").status_code == 404
    assert client.post(f"/api/datasets/{dataset_id}/promo-simulation/", {"sku": "SKU-001", "discount_pct": 10},
                       content_type="application/json").status_code == 404
    assert Dataset.objects.filter(pk=dataset_id).exists()


def test_detail_and_delete(api, dataset_id):
    assert api.get(f"/api/datasets/{dataset_id}/").json()["dataset"]["id"] == dataset_id
    assert api.delete(f"/api/datasets/{dataset_id}/").status_code == 204
    assert not AnalysisResult.objects.exists()
    assert api.get(f"/api/datasets/{dataset_id}/").status_code == 404


# ── Result endpoints ──────────────────────────────────────────────────────

def test_each_result_endpoint_returns_its_analysis(api, dataset_id):
    for kind in RESULT_KINDS:
        r = api.get(f"/api/datasets/{dataset_id}/{kind}/")
        assert r.status_code == 200, kind
        assert r.json()["dataset_id"] == dataset_id
        assert kind in r.json()


def test_result_contents(api, dataset_id):
    get = lambda kind: api.get(f"/api/datasets/{dataset_id}/{kind}/").json()[kind]
    dash = get("dashboard")
    assert set(dash) == {"metrics", "weekly_sales", "top_products", "categories", "regions"}
    assert dash["metrics"]["orders"] == 120
    assert get("forecast")["model_type"] == "sarima"
    assert get("bundles")["status"] == "ok" and len(get("bundles")["pairs"]) == 4
    assert all(i["status"] == "insufficient_price_variation" for i in get("pricing")["items"])
    assert get("inventory")["stock_data_available"] is False


def test_results_require_login(client, dataset_id):
    client.logout()
    assert client.get(f"/api/datasets/{dataset_id}/dashboard/").status_code == 403


def test_unknown_dataset_is_404(api):
    assert api.get("/api/datasets/99999/forecast/").status_code == 404


# ── Promo simulation ──────────────────────────────────────────────────────

def promo(api, dataset_id, **body):
    return api.post(f"/api/datasets/{dataset_id}/promo-simulation/", body, content_type="application/json")


def test_promo_simulation_uses_saved_inputs(api, dataset_id):
    r = promo(api, dataset_id, sku="SKU-001", discount_pct=10)
    assert r.status_code == 200
    sim = r.json()["simulation"]
    assert sim["product"] == "Mechanical Keyboard"
    assert sim["break_even_volume_increase_pct"] == 33.3
    assert sim["ped_status"] == "insufficient_price_variation"
    assert sim["projection"] is None


def test_promo_margin_defaults_to_dataset_and_can_be_overridden(api, dataset_id):
    assert promo(api, dataset_id, sku="SKU-001", discount_pct=10).json()["simulation"]["margin_assumption"] == 0.4
    assert promo(api, dataset_id, sku="SKU-001", discount_pct=10, margin=0.5).json()["simulation"][
        "break_even_volume_increase_pct"] == 25.0


@pytest.mark.parametrize("body", [
    {"sku": "SKU-001", "discount_pct": 0}, {"sku": "SKU-001", "discount_pct": 90},
    {"sku": "SKU-001"}, {"discount_pct": 10}, {"sku": "SKU-001", "discount_pct": 10, "margin": 2},
])
def test_promo_validation_errors(api, dataset_id, body):
    r = promo(api, dataset_id, **body)
    assert r.status_code == 400
    assert r.json()["error"]["type"] == "validation_error"


def test_promo_unknown_sku_is_404(api, dataset_id):
    r = promo(api, dataset_id, sku="NOPE", discount_pct=10)
    assert r.status_code == 404
    assert r.json()["error"]["type"] == "sku_not_found"


# ── Error handling ────────────────────────────────────────────────────────

def test_unexpected_error_hides_details(api, monkeypatch):
    def explode(*args, **kwargs):
        raise RuntimeError("secret internal detail at C:\\path\\file.py")

    monkeypatch.setattr("apps.datasets.views.run_analysis", explode)
    r = upload(api)
    assert r.status_code == 500
    assert r.json() == {"error": {"type": "server_error",
                                  "message": "Something went wrong on the server. Please try again."}}
    assert not Dataset.objects.exists()


def test_wrong_method_is_405(api, dataset_id):
    r = api.put(f"/api/datasets/{dataset_id}/forecast/")
    assert r.status_code == 405
    assert r.json()["error"]["type"] == "method_not_allowed"
