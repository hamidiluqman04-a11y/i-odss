import datetime
from itertools import combinations

import pytest

from apps.analytics.services.bundling import build_baskets, bundle_recommendations
from tests.conftest import SAMPLE_FILES, load_legacy_snapshot, load_sample

PRICES = {"A": 10.0, "B": 20.0, "C": 15.0, "D": 5.0, "E": 8.0, "F": 12.0}


def rows_from_orders(orders):
    """orders: list of SKU lists, one list per order."""
    return [
        {"order_id": f"O{i + 1}", "sku": sku, "product": f"Product {sku}", "price": PRICES.get(sku, 10.0),
         "qty": 1, "date": datetime.date(2025, 1, 1)}
        for i, skus in enumerate(orders) for sku in skus
    ]


# Hand-checked example, 10 orders:
#   A is in 5 orders, B in 4, C in 3, D in 2; {A,B} together in 3.
#   support(A,B) = 3/10 = 0.3
#   confidence(A→B) = 3/5 = 0.6,  confidence(B→A) = 3/4 = 0.75
#   lift = 0.3 / (0.5 × 0.4) = 1.5
#   {A,C}, {C,D}, {E,F} appear together only once → not a pattern.
HAND_CHECKED = [
    ["A", "B"], ["A", "B"], ["A", "B"], ["A"], ["C"],
    ["C", "D"], ["B"], ["D"], ["A", "C"], ["E", "F"],
]


def test_hand_calculated_support_confidence_lift():
    result = bundle_recommendations(rows_from_orders(HAND_CHECKED))
    assert result["status"] == "ok"
    assert (result["total_orders"], result["multi_item_orders"]) == (10, 6)
    assert len(result["pairs"]) == 1
    pair = result["pairs"][0]
    # The stronger direction leads: 75% of B buyers also bought A.
    assert (pair["sku_a"], pair["sku_b"]) == ("B", "A")
    assert pair["orders_together"] == 3
    assert pair["support"] == 0.3
    assert pair["confidence"] == 0.75
    assert pair["confidence_reverse"] == 0.6
    assert pair["lift"] == 1.5


def test_bundle_price_and_break_even():
    pair = bundle_recommendations(rows_from_orders(HAND_CHECKED))["pairs"][0]
    # discount = min(20, round(1.5 × 4)) = 6% off the SECOND product (A, price 10)
    assert pair["suggested_discount_pct"] == 6
    assert pair["bundle_price"] == 20 + 10 * 0.94          # 29.4
    # break-even = 0.06 / (0.40 − 0.06) = 17.6% more A sales needed
    assert pair["break_even_uplift_pct"] == 17.6
    assert "past data cannot promise that" in pair["plain_explain"]
    assert "is_profitable" not in pair and "cross_ped" not in pair


def test_discount_at_or_above_margin_has_no_break_even():
    pair = bundle_recommendations(rows_from_orders(HAND_CHECKED), margin=0.05)["pairs"][0]
    assert pair["break_even_uplift_pct"] is None
    assert "lose money" in pair["plain_explain"]


@pytest.mark.parametrize("bad", [0, 1, -0.2, 1.5])
def test_invalid_margin_rejected(bad):
    with pytest.raises(ValueError):
        bundle_recommendations(rows_from_orders(HAND_CHECKED), margin=bad)


def test_common_products_with_low_lift_are_not_recommended():
    # A and B are in almost every order, so seeing them together says nothing (lift ≈ 0.97).
    orders = [["A", "B"]] * 5 + [["A"], ["B"]]
    result = bundle_recommendations(rows_from_orders(orders))
    assert result["status"] == "no_strong_pairs"
    assert result["pairs"] == []
    assert "lift" in result["message"]


def test_single_item_orders_give_no_invented_pairs():
    orders = [["A"], ["B"], ["C"], ["A"], ["B"], ["A", "B"]] * 3   # only 3 multi-item orders
    result = bundle_recommendations(rows_from_orders(orders))
    assert result["status"] == "insufficient_data"
    assert result["pairs"] == []
    assert "Only 3 of your 18 orders" in result["message"]


def test_samples_without_multi_item_orders_report_insufficient_data():
    """Legacy invented bundle pairs for these files (its 'co-occurrence fallback')."""
    for name in SAMPLE_FILES:
        if name == "data_bundling_test.csv":
            continue
        legacy = load_legacy_snapshot(name)["bundles"]
        assert legacy["total_baskets"] == 0 and len(legacy["pairs"]) > 0   # what legacy did
        result = bundle_recommendations(load_sample(name).rows)
        assert result["status"] == "insufficient_data"
        assert result["pairs"] == []


def test_bundling_sample_finds_same_pairs_as_legacy_with_same_counts():
    rows = load_sample("data_bundling_test.csv").rows
    result = bundle_recommendations(rows)
    legacy = load_legacy_snapshot("data_bundling_test.csv")["bundles"]
    assert result["multi_item_orders"] == legacy["total_baskets"]
    assert result["total_orders"] == legacy["total_orders"]

    ours = {frozenset((p["sku_a"], p["sku_b"])): p for p in result["pairs"]}
    theirs = {frozenset((p["sku_a"], p["sku_b"])): p for p in legacy["pairs"]}
    assert ours.keys() == theirs.keys()
    for key, old in theirs.items():
        assert ours[key]["orders_together"] == old["count"]
        assert ours[key]["support"] == old["support"]
    # Product names are shown instead of SKU codes.
    assert all(not p["product_a"].startswith("SKU-") for p in result["pairs"])


def test_metrics_match_independent_count_on_bundling_sample():
    """Cross-check mlxtend's numbers with a plain Python count over all orders."""
    rows = load_sample("data_bundling_test.csv").rows
    baskets = list(build_baskets(rows).values())
    n = len(baskets)
    item = {s: sum(s in b for b in baskets) for s in {s for b in baskets for s in b}}
    for p in bundle_recommendations(rows)["pairs"]:
        a, b = p["sku_a"], p["sku_b"]
        both = sum(a in bk and b in bk for bk in baskets)
        assert p["support"] == round(both / n, 4)
        assert p["confidence"] == round(both / item[a], 3)
        assert p["confidence_reverse"] == round(both / item[b], 3)
        assert p["lift"] == round((both / n) / ((item[a] / n) * (item[b] / n)), 2)


def test_every_qualifying_pair_is_found():
    """No pair that meets all thresholds is missed (checked by brute force)."""
    rows = load_sample("data_bundling_test.csv").rows
    baskets = list(build_baskets(rows).values())
    n = len(baskets)
    item = {s: sum(s in b for b in baskets) for s in {s for b in baskets for s in b}}
    expected = set()
    for a, b in combinations(sorted(item), 2):
        both = sum(a in bk and b in bk for bk in baskets)
        lift = (both / n) / ((item[a] / n) * (item[b] / n))
        if both >= 2 and lift >= 1.2 and max(both / item[a], both / item[b]) >= 0.25:
            expected.add(frozenset((a, b)))
    found = {frozenset((p["sku_a"], p["sku_b"])) for p in bundle_recommendations(rows)["pairs"]}
    assert found == expected


def test_pairs_sorted_by_lift_and_limited_to_eight():
    # 10 separate product pairs; pair i is bought together twice, and its first
    # product also i times alone, so each pair has a different lift.
    orders = []
    for i in range(10):
        x, y = f"X{i}", f"Y{i}"
        orders += [[x, y], [x, y]] + [[x]] * i
    result = bundle_recommendations(rows_from_orders(orders))
    lifts = [p["lift"] for p in result["pairs"]]
    assert len(lifts) == 8
    assert lifts == sorted(lifts, reverse=True)
    assert len(set(lifts)) == 8


def test_same_input_same_output():
    rows = rows_from_orders(HAND_CHECKED)
    assert bundle_recommendations(rows) == bundle_recommendations(rows)
