"""
Inventory: reorder point (ROP) and restock status per product.

Ported from legacy/backend/main.py (/api/inventory). The ROP formula and its
rounding are unchanged, except that daily demand now divides by calendar
days (first to last sale date) instead of days that had a sale:

    daily demand   = units sold / calendar days in the data
    safety stock   = daily demand × category safety factor
    reorder point  = daily demand × supplier lead time + safety stock

Deliberate change (approved decision D2): the legacy app had no stock data
and SIMULATED stock as 8% of units sold. Now:
  - if the CSV has a stock column, the latest value per product is used and
    the item is marked stock_source="csv";
  - otherwise stock is None, status is "unknown", and only the calculated
    ROP is shown (stock_source="unknown"). Nothing is invented.
Lead times can be overridden per category, because the defaults below are
general assumptions, not the seller's real supplier times.
"""
from .kpis import count_days, sku_summary

# Default supplier lead time (days) and safety factor per category (legacy values).
CATEGORY_SETTINGS = {
    "Electronics":  {"lead": 8, "safety": 1.8},
    "Peripherals":  {"lead": 5, "safety": 1.5},
    "Accessories":  {"lead": 4, "safety": 1.2},
    "Skincare":     {"lead": 6, "safety": 1.4},
    "Haircare":     {"lead": 6, "safety": 1.3},
    "Makeup":       {"lead": 5, "safety": 1.3},
    "Tops":         {"lead": 7, "safety": 1.4},
    "Bottoms":      {"lead": 7, "safety": 1.4},
    "Dresses":      {"lead": 7, "safety": 1.5},
    "Outerwear":    {"lead": 8, "safety": 1.6},
    "Footwear":     {"lead": 8, "safety": 1.5},
}
DEFAULT_SETTINGS = {"lead": 7, "safety": 1.5}

# A product is "warning" when stock is above the ROP but within 30% of it.
WARNING_MARGIN = 1.30
STATUS_ORDER = {"critical": 0, "warning": 1, "ok": 2, "unknown": 3}


def _validate_lead_times(lead_times):
    for category, days in lead_times.items():
        if isinstance(days, bool) or not isinstance(days, int) or not 1 <= days <= 365:
            raise ValueError(f"Lead time for '{category}' must be a whole number of days between 1 and 365.")


def _explain(status, vel, lead, stock, rop, days_left):
    if status == "unknown":
        return (
            f"This item sells about {vel:.1f} units/day. With a {lead}-day supplier lead time, "
            f"you should reorder when stock falls to about {rop:.0f} units. Your file has no "
            f"stock column, so I-ODSS cannot tell whether you are below that level yet."
        )
    if status == "critical":
        unit = "unit" if abs(vel - 1) < 0.5 else "units"
        return (
            f"This item sells at a velocity of {vel:.1f} {unit}/day. "
            f"Because your supplier takes {lead} days to ship new inventory, "
            f"you will run out of stock in about {days_left:.0f} day{'s' if days_left != 1 else ''} "
            f"if you do not reorder now."
        )
    if status == "warning":
        days_to_rop = (stock - rop) / vel if vel > 0 else 0
        return (
            f"At your current pace of {vel:.1f} units/day, this item will drop to its reorder "
            f"point of {rop:.0f} units in roughly {days_to_rop:.0f} days. Your supplier needs "
            f"{lead} days, so plan the next order soon."
        )
    return (
        f"You're selling {vel:.1f} units/day and have enough stock to last "
        f"~{days_left:.0f} days — well beyond your {lead}-day supplier lead time. "
        f"No action needed right now."
    )


def inventory_report(rows, lead_times=None):
    """
    Reorder point and status for every SKU.
    `lead_times` optionally overrides the supplier lead time per category, e.g. {"Skincare": 10}.
    """
    lead_times = lead_times or {}
    _validate_lead_times(lead_times)

    days = count_days(rows)
    items = []
    for sku, s in sku_summary(rows).items():
        settings = CATEGORY_SETTINGS.get(s["category"], DEFAULT_SETTINGS)
        lead = lead_times.get(s["category"], settings["lead"])
        vel = round(s["qty"] / days, 3)
        safety_stock = round(vel * settings["safety"], 1)
        rop = round(vel * lead + safety_stock, 1)
        stock = s["stock"]

        if stock is None:
            status, reorder_qty, days_left = "unknown", None, None
        else:
            if stock < rop:
                status = "critical"
            elif stock < rop * WARNING_MARGIN:
                status = "warning"
            else:
                status = "ok"
            reorder_qty = max(0, round(vel * lead * 2 - stock))
            days_left = round(stock / vel, 1) if vel > 0 else None

        state = (
            "stock unknown" if status == "unknown"
            else "BELOW ROP — reorder now." if status == "critical"
            else "near ROP — monitor." if status == "warning"
            else "healthy."
        )
        items.append({
            "sku":                 sku,
            "product":             s["product"],
            "category":            s["category"],
            "stock":               stock,
            "stock_source":        "unknown" if stock is None else "csv",
            "rop":                 float(rop),
            "lead":                int(lead),
            "velocity":            float(vel),
            "safety_stock":        float(safety_stock),
            "status":              status,
            "revenue":             round(s["revenue"], 2),
            "total_sold":          int(s["qty"]),
            "reorder_qty":         reorder_qty,
            "avg_rating":          round(sum(s["ratings"]) / len(s["ratings"]), 1) if s["ratings"] else None,
            "return_rate":         round(s["returns"] / max(s["qty"], 1) * 100, 1) if s["has_returns"] else None,
            "days_until_stockout": days_left,
            "plain_explain":       _explain(status, vel, lead, stock, rop, days_left),
            "xai": (
                f"ROP={rop}: daily demand {vel:.2f} u/day × lead {lead} days "
                f"+ safety stock {safety_stock} units. "
                + (f"Stock={stock} (from your file) → {state}" if stock is not None else "No stock data in file.")
            ),
        })

    items.sort(key=lambda x: STATUS_ORDER[x["status"]])
    return {
        "items": items,
        "critical_count": sum(1 for i in items if i["status"] == "critical"),
        "stock_data_available": any(i["stock"] is not None for i in items),
    }
