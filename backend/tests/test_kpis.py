import datetime

from apps.analytics.services import kpis
from apps.analytics.services.inventory import inventory_report
from apps.datasets.csv_parser import parse_csv


def rows_of(text):
    return parse_csv("t.csv", text.encode()).rows


# ── Compared with the legacy outputs for every sample file ────────────────

def test_metrics_match_legacy(sample):
    parsed, legacy = sample
    metrics = kpis.dashboard_metrics(parsed.rows, inventory_report(parsed.rows))
    for key in ("revenue", "orders", "units", "aov", "skus_count", "days_of_data"):
        assert metrics[key] == legacy["metrics"][key], key
    # Samples have no stock column, so at-risk cannot be known (legacy simulated it).
    assert metrics["at_risk"] is None


def test_weekly_sales_match_legacy(sample):
    parsed, legacy = sample
    assert kpis.weekly_sales(parsed.rows) == legacy["sales-trend"]["data"]


def test_category_and_region_totals_match_legacy(sample):
    parsed, legacy = sample
    assert kpis.category_breakdown(parsed.rows) == legacy["category-breakdown"]["data"]
    assert kpis.regional_breakdown(parsed.rows) == legacy["regional"]["data"]


def test_top_products_match_legacy_but_show_product_names(sample):
    parsed, legacy = sample
    top = kpis.top_products(parsed.rows)
    assert [(t["sku"], t["revenue"]) for t in top] == [(t["sku"], t["revenue"]) for t in legacy["top-skus"]["data"]]
    names = {r["sku"]: r["product"] for r in parsed.rows}
    assert all(t["name"] == names[t["sku"]] and t["name"] != t["sku"] for t in top)


# ── Hand-checked small cases ──────────────────────────────────────────────

def test_metrics_on_tiny_dataset():
    rows = rows_of(
        "OrderID,Date,SKU,Quantity,UnitPrice\nO1,2025-01-01,A,2,10\nO1,2025-01-01,B,1,5\nO2,2025-01-03,A,1,10\n"
    )
    m = kpis.dashboard_metrics(rows, inventory_report(rows))
    assert m == {"revenue": 35.0, "orders": 2, "units": 4, "aov": 17.5,
                 "skus_count": 2, "days_of_data": 3, "at_risk": None}


def test_days_of_data_counts_calendar_days_not_sale_days():
    # Sales on 5 separate days spread over 30 calendar days.
    rows = rows_of("Date,SKU,Quantity,UnitPrice\n" + "".join(
        f"2025-01-{d:02d},A,2,10\n" for d in (1, 8, 15, 22, 30)
    ))
    assert kpis.count_days(rows) == 30            # legacy app counted 5


def test_single_day_of_data_counts_as_one():
    assert kpis.count_days(rows_of("Date,SKU,Quantity,UnitPrice\n2025-01-01,A,1,10\n")) == 1


def test_at_risk_counts_critical_items_when_stock_known():
    rows = rows_of("Date,SKU,Quantity,UnitPrice,Stock\n2025-01-01,A,5,10,1\n2025-01-01,B,1,10,500\n")
    assert kpis.dashboard_metrics(rows, inventory_report(rows))["at_risk"] == 1


def test_weekly_sales_includes_empty_weeks():
    rows = rows_of("Date,SKU,Quantity,UnitPrice\n2025-01-01,A,3,10\n2025-01-20,A,5,10\n")
    assert kpis.weekly_sales(rows) == [
        {"week": "Wk 1", "units": 3}, {"week": "Wk 2", "units": 0}, {"week": "Wk 3", "units": 5},
    ]


def test_sku_summary_uses_latest_row_for_stock():
    rows = rows_of("Date,SKU,Quantity,UnitPrice,Stock\n2025-01-05,A,1,10,7\n2025-01-01,A,1,10,30\n")
    assert rows[0]["date"] == datetime.date(2025, 1, 5)
    assert kpis.sku_summary(rows)["A"]["stock"] == 7
