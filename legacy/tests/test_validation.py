"""Upload validation, auth, and error-handling behaviour of the legacy app."""
from conftest import upload_bytes, upload_sample

GOOD_HEADER = "OrderID,Date,SKU,Quantity,UnitPrice\n"


def test_rejects_non_csv_file(client):
    r = upload_bytes(client, "data.xlsx", b"whatever")
    assert r.status_code == 422
    assert r.json()["detail"]["type"] == "file_type_error"


def test_rejects_header_only_file(client):
    r = upload_bytes(client, "empty.csv", GOOD_HEADER.encode())
    assert r.status_code == 422
    assert r.json()["detail"]["type"] == "empty_file"


def test_reports_missing_required_columns(client):
    r = upload_bytes(client, "bad.csv", b"OrderID,Date,Colour\nO1,2025-01-01,Red\n")
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert detail["type"] == "missing_columns"
    assert len(detail["errors"]) == 3  # sku, qty, price


def test_maps_marketplace_header_variants(client):
    csv = "no pesanan,tarikh,nama produk,kuantiti,harga\nO1,2025-01-01,Tee,2,49.0\n"
    r = upload_bytes(client, "shopee_my.csv", csv.encode())
    assert r.status_code == 200
    assert set(r.json()["col_map"]) == {"order_id", "date", "sku", "qty", "price"}


def test_skips_invalid_rows_with_row_numbers(client):
    csv = GOOD_HEADER + "O1,2025-01-01,A,2,10\nO2,not-a-date,A,1,10\nO3,2025-01-02,A,-1,10\nO4,2025-01-03,A,1,abc\n"
    r = upload_bytes(client, "mixed.csv", csv.encode())
    body = r.json()
    assert r.status_code == 200
    assert body["rows"] == 1
    assert body["warning_count"] == 3
    assert body["warnings"][0].startswith("Row 3:")


def test_all_rows_invalid_returns_422(client):
    csv = GOOD_HEADER + "O1,2025-01-01,A,0,10\n"
    r = upload_bytes(client, "bad.csv", csv.encode())
    assert r.status_code == 422
    assert r.json()["detail"]["type"] == "no_valid_rows"


def test_analytics_require_upload_first(client):
    for ep in ("metrics", "inventory", "pricing", "bundles", "forecast"):
        assert client.get(f"/api/{ep}").status_code == 400


def test_promo_rejects_invalid_discount_and_unknown_sku(client):
    upload_sample(client, "data_beauty.csv")
    assert client.post("/api/simulate/promo", json={"sku": "SKU-B01", "discount_pct": 95}).status_code == 400
    assert client.post("/api/simulate/promo", json={"sku": "NOPE", "discount_pct": 10}).status_code == 404


def test_login(client):
    assert client.post("/api/login", json={"email": "seller@iodss.com", "password": "demo1234"}).status_code == 200
    assert client.post("/api/login", json={"email": "seller@iodss.com", "password": "wrong"}).status_code == 401
    assert client.post("/api/login", json={"email": "", "password": "x"}).status_code == 400


def test_html_pages_are_served(client):
    assert client.get("/").status_code == 200
    assert client.get("/dashboard").status_code == 200
    assert client.get("/static/samples/data_beauty.csv").status_code == 200
