import pytest

from apps.analytics.services.inventory import inventory_report
from apps.datasets.csv_parser import parse_csv

ROP_FIELDS = ("rop", "lead", "velocity", "safety_stock", "revenue", "total_sold", "avg_rating", "return_rate")


def by_sku(items):
    return {i["sku"]: i for i in items}


def rows_of(text):
    return parse_csv("t.csv", text.encode()).rows


# ── Compared with the legacy outputs for every sample file ────────────────

def test_rop_calculation_matches_legacy(sample):
    parsed, legacy = sample
    new = by_sku(inventory_report(parsed.rows)["items"])
    old = by_sku(legacy["inventory"]["items"])
    assert new.keys() == old.keys()
    for sku in old:
        for f in ROP_FIELDS:
            assert new[sku][f] == old[sku][f], (sku, f)


def test_without_stock_column_nothing_is_simulated(sample):
    parsed, _ = sample
    report = inventory_report(parsed.rows)
    assert report["stock_data_available"] is False
    assert report["critical_count"] == 0
    for item in report["items"]:
        assert item["stock"] is None
        assert item["stock_source"] == "unknown"
        assert item["status"] == "unknown"
        assert item["reorder_qty"] is None and item["days_until_stockout"] is None
        assert "no stock column" in item["plain_explain"]


def test_given_same_stock_as_legacy_status_and_reorder_match(sample):
    """Feed in the stock the legacy app simulated: its decisions must be reproduced exactly."""
    parsed, legacy = sample
    old = by_sku(legacy["inventory"]["items"])
    rows = [dict(r, stock=old[r["sku"]]["stock"]) for r in parsed.rows]
    report = inventory_report(rows)
    new = by_sku(report["items"])
    for sku in old:
        for f in ("stock", "status", "reorder_qty", "days_until_stockout"):
            assert new[sku][f] == old[sku][f], (sku, f)
        assert new[sku]["stock_source"] == "csv"
    assert report["critical_count"] == legacy["inventory"]["critical_count"]
    assert [i["status"] for i in report["items"]] == [i["status"] for i in legacy["inventory"]["items"]]


# ── Hand-checked cases with a real stock column ───────────────────────────

CSV_WITH_STOCK = (
    "Date,SKU,Category,Quantity,UnitPrice,Stock\n"
    "2025-01-01,A,Skincare,4,10,\n"
    "2025-01-02,A,Skincare,6,10,12\n"      # A: 10 units / 2 days = 5 per day
    "2025-01-01,B,Skincare,2,10,100\n"     # B: 2 units / 2 days = 1 per day
)


def test_rop_and_status_with_real_stock():
    items = by_sku(inventory_report(rows_of(CSV_WITH_STOCK))["items"])
    a = items["A"]
    # Skincare: lead 6, safety factor 1.4 -> SS = 5 x 1.4 = 7, ROP = 5 x 6 + 7 = 37
    assert (a["velocity"], a["safety_stock"], a["rop"]) == (5.0, 7.0, 37.0)
    # reorder = 5 x 6 x 2 - 12 = 48; days left = 12 / 5 = 2.4
    assert (a["stock"], a["status"], a["reorder_qty"], a["days_until_stockout"]) == (12, "critical", 48, 2.4)
    b = items["B"]
    assert (b["rop"], b["status"], b["reorder_qty"]) == (7.4, "ok", 0)


def test_warning_band_is_within_30_percent_above_rop():
    # velocity 1/day, Skincare -> ROP 7.4; "warning" while stock < 9.62
    csv = "Date,SKU,Category,Quantity,UnitPrice,Stock\n2025-01-01,A,Skincare,1,10,9\n"
    item = inventory_report(rows_of(csv))["items"][0]
    assert item["status"] == "warning"
    assert "reorder point of 7 units in roughly 2 days" in item["plain_explain"]


def test_daily_demand_uses_calendar_days_for_sparse_sales():
    # 10 units sold on 5 days of a 30-day period: 10 / 30 = 0.333/day (legacy: 10 / 5 = 2/day)
    csv = "Date,SKU,Category,Quantity,UnitPrice\n" + "".join(
        f"2025-01-{d:02d},A,Skincare,2,10\n" for d in (1, 8, 15, 22, 30)
    )
    item = inventory_report(rows_of(csv))["items"][0]
    # Skincare: SS = 0.333 x 1.4 = 0.5; ROP = 0.333 x 6 + 0.5 = 2.5 (legacy would give 14.8)
    assert (item["velocity"], item["safety_stock"], item["rop"]) == (0.333, 0.5, 2.5)


def test_critical_items_listed_first():
    statuses = [i["status"] for i in inventory_report(rows_of(CSV_WITH_STOCK))["items"]]
    assert statuses == ["critical", "ok"]


def test_lead_time_override_changes_rop():
    items = by_sku(inventory_report(rows_of(CSV_WITH_STOCK), lead_times={"Skincare": 10})["items"])
    assert (items["A"]["lead"], items["A"]["rop"]) == (10, 57.0)


def test_unknown_category_uses_default_settings():
    item = inventory_report(rows_of("Date,SKU,Quantity,UnitPrice\n2025-01-01,A,1,10\n"))["items"][0]
    assert (item["category"], item["lead"], item["safety_stock"], item["rop"]) == ("General", 7, 1.5, 8.5)


@pytest.mark.parametrize("bad", [0, -2, 400, 2.5, "7", True])
def test_invalid_lead_time_rejected(bad):
    with pytest.raises(ValueError):
        inventory_report(rows_of(CSV_WITH_STOCK), lead_times={"Skincare": bad})
