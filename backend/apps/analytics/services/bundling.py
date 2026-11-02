"""
Product bundling: finds pairs of products that are often bought in the same order.

Replaces the legacy /api/bundles (approved decision D2):

  - Uses the real FP-Growth algorithm (mlxtend) on order "baskets", then
    association rules for support, confidence and lift.
  - Support, confidence and lift are measured against ALL orders. The legacy
    app counted items only in multi-item orders but divided by all orders,
    which inflated lift and pushed confidence to 1.0.
  - The legacy "co-occurrence fallback" invented pair counts when no order
    had two products. It is removed: with too few multi-item orders the
    result is an honest "not enough data" message and no pairs.
  - The legacy "is_profitable" badge and "cross-PED" value were not based on
    any evidence. Instead each bundle shows a break-even figure: how many
    more of the second product the bundle must sell, at an assumed margin,
    for the discount to pay for itself.
  - The bundle price now discounts only the second product, matching the
    explanation text (the legacy price discounted both).
"""
import pandas as pd
from mlxtend.frequent_patterns import association_rules, fpgrowth

MIN_MULTI_ITEM_ORDERS = 5     # fewer than this: no basket analysis possible
MIN_ORDERS_TOGETHER = 2       # a pair seen in only one order is not a pattern
MIN_LIFT = 1.2                # legacy threshold
MIN_CONFIDENCE = 0.25         # legacy threshold
MAX_DISCOUNT_PCT = 20
DEFAULT_MARGIN = 0.40         # legacy assumption: 40% gross margin
MAX_PAIRS = 8


def build_baskets(rows):
    """One set of SKUs per order."""
    baskets = {}
    for r in rows:
        baskets.setdefault(r["order_id"], set()).add(r["sku"])
    return baskets


def _basket_table(baskets):
    """True/False table: one row per order, one column per SKU (what FP-Growth expects)."""
    skus = sorted({s for b in baskets.values() for s in b})
    return pd.DataFrame([[s in b for s in skus] for b in baskets.values()], columns=skus)


def _frequent_pairs(table, total_orders):
    """Run FP-Growth and turn the rules into one row per product pair."""
    min_support = MIN_ORDERS_TOGETHER / total_orders
    itemsets = fpgrowth(table, min_support=min_support, use_colnames=True, max_len=2)
    if itemsets.empty or not (itemsets["itemsets"].apply(len) == 2).any():
        return []

    rules = association_rules(itemsets, num_itemsets=total_orders, metric="lift", min_threshold=MIN_LIFT)
    pairs = {}
    for _, rule in rules.iterrows():
        (a,), (b,) = tuple(rule["antecedents"]), tuple(rule["consequents"])
        key = frozenset((a, b))
        pair = pairs.setdefault(key, {"support": rule["support"], "lift": rule["lift"], "confidence": {}})
        pair["confidence"][(a, b)] = rule["confidence"]

    result = []
    for key, pair in pairs.items():
        # Lead with the direction that has the higher confidence ("buyers of A also buy B").
        # Ties are broken alphabetically so results are always the same.
        (a, b), conf = min(pair["confidence"].items(), key=lambda kv: (-kv[1], kv[0]))
        if conf < MIN_CONFIDENCE:
            continue
        reverse = pair["confidence"].get((b, a))
        result.append({
            "sku_a": a, "sku_b": b,
            "orders_together": int(round(pair["support"] * total_orders)),
            "support": round(float(pair["support"]), 4),
            "confidence": round(float(conf), 3),
            "confidence_reverse": round(float(reverse), 3) if reverse is not None else None,
            "lift": round(float(pair["lift"]), 2),
        })
    return result


def _bundle_offer(pair, names, prices, margin):
    a, b = pair["sku_a"], pair["sku_b"]
    price_a, price_b = prices[a], prices[b]
    discount = min(MAX_DISCOUNT_PCT, round(pair["lift"] * 4))   # legacy rule of thumb
    d = discount / 100
    # Break-even: customers who already buy both now pay d less for B. Each EXTRA B
    # sold earns (margin - d) x price. Extra sales needed = d / (margin - d) of current.
    break_even = round(d / (margin - d) * 100, 1) if d < margin else None
    name_a, name_b = names[a], names[b]

    explain = (
        f"Out of every order that included {name_a}, {pair['confidence'] * 100:.0f}% also included "
        f"{name_b} — {pair['lift']}× more often than if the two were unrelated "
        f"(seen together in {pair['orders_together']} orders). "
        f"A bundle at {price_a + price_b * (1 - d):.2f} ({discount}% off {name_b}) could raise your "
        f"average order value. "
    )
    if break_even is None:
        explain += f"With a {margin * 100:.0f}% margin, a {discount}% discount would lose money on every bundle."
    else:
        explain += (
            f"With a {margin * 100:.0f}% margin, it only pays off if it sells at least "
            f"{break_even:.0f}% more {name_b} than you sell now — past data cannot promise that."
        )

    return {
        **pair,
        "product_a": name_a, "product_b": name_b,
        "price_a": round(price_a, 2), "price_b": round(price_b, 2),
        "suggested_discount_pct": discount,
        "bundle_price": round(price_a + price_b * (1 - d), 2),
        "break_even_uplift_pct": break_even,
        "plain_explain": explain,
        "xai": (
            f"FP-Growth pair {{{a}, {b}}}: support={pair['support']} ({pair['orders_together']} of all orders), "
            f"confidence({a}→{b})={pair['confidence']}, lift={pair['lift']}. "
            f"Discount rule: min({MAX_DISCOUNT_PCT}, round(lift×4)) = {discount}%. "
            f"Break-even uplift = d/(margin−d) = "
            + (f"{break_even}%." if break_even is not None else "n/a (discount ≥ margin).")
        ),
    }


def bundle_recommendations(rows, margin=DEFAULT_MARGIN):
    """Frequently-bought-together pairs with bundle suggestions."""
    if not 0 < margin < 1:
        raise ValueError("Margin must be between 0 and 1 (e.g. 0.40 for 40%).")

    baskets = build_baskets(rows)
    total_orders = len(baskets)
    multi = sum(1 for b in baskets.values() if len(b) > 1)
    response = {
        "status": "ok",
        "pairs": [],
        "total_orders": total_orders,
        "multi_item_orders": multi,
        "thresholds": {
            "min_orders_together": MIN_ORDERS_TOGETHER, "min_lift": MIN_LIFT,
            "min_confidence": MIN_CONFIDENCE,
        },
        "margin_assumption": margin,
        "message": None,
    }

    if multi < MIN_MULTI_ITEM_ORDERS:
        response["status"] = "insufficient_data"
        response["message"] = (
            f"Only {multi} of your {total_orders} orders contain more than one product. At least "
            f"{MIN_MULTI_ITEM_ORDERS} multi-item orders (with an order ID column) are needed to find "
            f"products that are bought together."
        )
        return response

    names, price_lists = {}, {}
    for r in rows:
        names[r["sku"]] = r["product"]
        price_lists.setdefault(r["sku"], []).append(r["price"])
    prices = {sku: sum(p) / len(p) for sku, p in price_lists.items()}

    pairs = _frequent_pairs(_basket_table(baskets), total_orders)
    pairs.sort(key=lambda p: (-p["lift"], -p["orders_together"], p["sku_a"], p["sku_b"]))
    response["pairs"] = [_bundle_offer(p, names, prices, margin) for p in pairs[:MAX_PAIRS]]

    if not pairs:
        response["status"] = "no_strong_pairs"
        response["message"] = (
            "No two products are bought together noticeably more often than chance "
            f"(needs lift ≥ {MIN_LIFT}, confidence ≥ {MIN_CONFIDENCE:.0%}, and at least "
            f"{MIN_ORDERS_TOGETHER} shared orders)."
        )
    elif multi < 30:
        response["message"] = f"Based on only {multi} multi-item orders — treat these pairs as early signals."
    return response
