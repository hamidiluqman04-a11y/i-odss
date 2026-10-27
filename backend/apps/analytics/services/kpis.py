"""
Dashboard numbers: KPIs, weekly sales, top products, category and region totals.

Ported from legacy/backend/main.py (sku_summary, count_days, weekly_series,
/api/metrics, /api/top-skus, /api/category-breakdown, /api/regional).
Every function takes the clean rows produced by apps.datasets.csv_parser.
"""
from collections import defaultdict


def sku_summary(rows):
    """Totals per SKU. Category, product name and stock come from the latest row."""
    skus = {}
    for r in sorted(rows, key=lambda r: r["date"]):
        s = skus.setdefault(r["sku"], {
            "qty": 0, "revenue": 0.0, "orders": set(), "prices": [],
            "ratings": [], "returns": 0, "has_returns": False, "stock": None,
        })
        s["qty"] += r["qty"]
        s["revenue"] += r["qty"] * r["price"]
        s["orders"].add(r["order_id"])
        s["prices"].append(r["price"])
        s["category"] = r["category"]
        s["product"] = r["product"]
        if r["rating"] is not None:
            s["ratings"].append(r["rating"])
        if r["returns"] is not None:
            s["returns"] += r["returns"]
            s["has_returns"] = True
        if r["stock"] is not None:
            s["stock"] = r["stock"]
    return skus


def count_days(rows):
    """
    Number of distinct days that have at least one sale (legacy behaviour).

    Known limitation: days with zero sales are not counted, so daily demand is
    overstated when sales are sparse. Kept unchanged until a decision is made.
    """
    return max(len({r["date"] for r in rows}), 1)


def dashboard_metrics(rows, inventory):
    """Headline KPIs. `inventory` is the result of inventory.inventory_report()."""
    revenue = sum(r["qty"] * r["price"] for r in rows)
    orders = len({r["order_id"] for r in rows})
    return {
        "revenue":      round(revenue, 2),
        "orders":       orders,
        "units":        sum(r["qty"] for r in rows),
        "aov":          round(revenue / orders, 2) if orders else 0,
        "skus_count":   len({r["sku"] for r in rows}),
        "days_of_data": count_days(rows),
        # Same number the inventory page shows (the legacy app used a second,
        # slightly different formula here). None when no stock data exists.
        "at_risk":      inventory["critical_count"] if inventory["stock_data_available"] else None,
    }


def weekly_sales(rows):
    """
    Units sold per week, counting weeks from the first sale date.
    Weeks with no sales are included as 0 (the legacy app skipped them,
    which squeezed the timeline together).
    """
    first = min(r["date"] for r in rows)
    weeks = defaultdict(int)
    for r in rows:
        weeks[(r["date"] - first).days // 7 + 1] += r["qty"]
    return [{"week": f"Wk {w}", "units": weeks[w]} for w in range(1, max(weeks) + 1)]


def top_products(rows, limit=6):
    skus = sku_summary(rows)
    ranked = sorted(
        ({"sku": k, "name": v["product"], "revenue": round(v["revenue"], 2)} for k, v in skus.items()),
        key=lambda x: x["revenue"], reverse=True,
    )
    return ranked[:limit]


def category_breakdown(rows):
    cats = defaultdict(lambda: {"revenue": 0.0, "units": 0})
    for r in rows:
        cats[r["category"]]["revenue"] += r["qty"] * r["price"]
        cats[r["category"]]["units"] += r["qty"]
    return [{"category": k, "revenue": round(v["revenue"], 2), "units": v["units"]} for k, v in cats.items()]


def regional_breakdown(rows):
    regions = defaultdict(lambda: {"revenue": 0.0, "orders": set()})
    for r in rows:
        regions[r["region"]]["revenue"] += r["qty"] * r["price"]
        regions[r["region"]]["orders"].add(r["order_id"])
    return [
        {"region": k, "revenue": round(v["revenue"], 2), "orders": len(v["orders"])}
        for k, v in regions.items()
    ]
