"""
Known issues found in the Phase 1 audit.

Each test asserts the CURRENT (incorrect) behaviour so it is documented and
measurable. The Django rewrite fixes these on purpose; the matching new
tests will assert the corrected behaviour.
"""
import pytest

from conftest import upload_bytes, upload_sample


def test_mape_is_hardcoded(client):
    mapes = set()
    for name in ("data_beauty.csv", "data_electronics.csv"):
        upload_sample(client, name)
        mapes.add(client.get("/api/forecast").json()["summary"]["mape"])
    assert mapes == {4.2}  # same "accuracy" whatever the data


def test_fallback_invents_bundles_without_multi_item_orders(client):
    upload_sample(client, "data_electronics.csv")
    b = client.get("/api/bundles").json()
    assert b["total_baskets"] == 0          # no order has 2+ products...
    assert len(b["pairs"]) > 0              # ...yet bundle pairs are reported


def test_inventory_stock_is_simulated_as_8pct_of_sales(client):
    upload_sample(client, "data_beauty.csv")
    for item in client.get("/api/inventory").json()["items"]:
        assert item["stock"] == max(2, round(item["total_sold"] * 0.08))


def test_product_name_column_is_ignored(client):
    upload_sample(client, "data_bundling_test.csv")
    pair = client.get("/api/bundles").json()["pairs"][0]
    assert pair["product_a"].startswith("SKU-")  # shows code, not ProductName


def test_missing_rating_becomes_4_5(client):
    upload_bytes(client, "r.csv", b"OrderID,Date,SKU,Quantity,UnitPrice\nO1,2025-01-01,A,1,10\n")
    assert client.get("/api/inventory").json()["items"][0]["avg_rating"] == 4.5


def test_day_first_dates_crash_forecast(client):
    csv = b"OrderID,Date,SKU,Quantity,UnitPrice\nO1,15/01/2025,A,1,10\nO2,03/02/2025,A,2,10\n"
    r = upload_bytes(client, "dmy.csv", csv)
    assert r.json()["date_range"] == "03/02/2025 to 15/01/2025"  # reversed
    with pytest.raises(ValueError):
        client.get("/api/forecast")
