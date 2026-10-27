import datetime

import pytest

from apps.analytics.services.pricing import pricing_analysis, project, simulate_promo
from tests.conftest import SAMPLE_FILES, load_legacy_snapshot, load_sample

START = datetime.date(2025, 1, 6)
PRICES_12_WEEKS = [10, 12, 9, 11, 8, 12, 10, 9, 11, 8, 12, 10]


def make_rows(weekly_prices, units_per_day, sku="A", name="Test Product", category="Skincare"):
    """
    One row per day. Each week has one price; daily units = units_per_day(price).
    Every week is complete, so all of them are used.
    """
    rows = []
    for week, price in enumerate(weekly_prices):
        for day in range(7):
            rows.append({
                "order_id": f"{sku}-{week}-{day}", "sku": sku, "product": name, "category": category,
                "date": START + datetime.timedelta(days=week * 7 + day),
                "qty": int(units_per_day(price)), "price": float(price),
            })
    return rows


def constant_elasticity(ped, units_at_10=500):
    """Daily units = units_at_10 × (price / 10)^PED, so every price sells plenty of units."""
    return lambda price: round(units_at_10 * (price / 10) ** ped)


def item_for(rows, **kwargs):
    return pricing_analysis(rows, **kwargs)["items"][0]


# ── Estimating PED from data ──────────────────────────────────────────────

@pytest.mark.parametrize("true_ped", [-0.4, -1.5, -3.0])
def test_recovers_known_elasticity(true_ped):
    item = item_for(make_rows(PRICES_12_WEEKS, constant_elasticity(true_ped)))
    assert item["status"] == "estimated"
    assert item["ped"] == pytest.approx(true_ped, abs=0.02)
    assert item["ped_ci_low"] <= item["ped"] <= item["ped_ci_high"]
    assert item["reliability"] == "strong"
    assert item["r_squared"] > 0.99


def test_fixed_price_gives_no_ped():
    item = item_for(make_rows([10] * 12, lambda p: 20))
    assert item["status"] == "insufficient_price_variation"
    assert item["ped"] is None
    assert item["recommendation"] == "no_recommendation"
    assert "always sold at about the same price" in item["plain_explain"]


def test_tiny_price_changes_do_not_count_as_variation():
    # 10.00 vs 10.20 is a 2% range, below the 3% minimum.
    item = item_for(make_rows([10, 10.2] * 6, constant_elasticity(-1.5)))
    assert item["status"] == "insufficient_price_variation"


def test_too_few_weeks_gives_no_ped():
    item = item_for(make_rows([10, 12, 9, 11, 8], constant_elasticity(-1.5)))
    assert item["status"] == "insufficient_data"
    assert "only 5 different week(s)" in item["plain_explain"]


def test_unclear_relationship_gives_no_advice():
    # Price and units are arranged so that they are completely unrelated.
    units = {0: 100, 1: 100, 2: 120, 3: 120}
    prices = [8, 12, 8, 12] * 3
    rows = make_rows(prices, lambda p: 0)
    for r in rows:
        r["qty"] = units[((r["date"] - START).days // 7) % 4]
    item = item_for(rows)
    assert item["status"] == "estimated"
    assert item["reliability"] == "weak"
    assert item["recommendation"] == "no_recommendation"
    assert "did not move in a clear pattern" in item["plain_explain"]


def test_sales_rising_with_price_gives_no_advice():
    item = item_for(make_rows(PRICES_12_WEEKS, constant_elasticity(+0.8)))
    assert item["ped"] > 0
    assert item["recommendation"] == "no_recommendation"
    assert "unusual" in item["plain_explain"]


def test_unfinished_last_week_is_ignored():
    rows = make_rows(PRICES_12_WEEKS, constant_elasticity(-1.5))
    rows.append({**rows[-1], "date": rows[-1]["date"] + datetime.timedelta(days=1), "qty": 1, "price": 30.0})
    item = item_for(rows)
    assert item["weeks_with_sales"] == 12
    assert item["ped"] == pytest.approx(-1.5, abs=0.02)


# ── Price-test suggestions use profit, not just revenue ───────────────────

def test_inelastic_product_suggests_testing_a_price_increase():
    item = item_for(make_rows(PRICES_12_WEEKS, constant_elasticity(-0.4)))
    assert item["recommendation"] == "test_increase"
    assert item["test_change_pct"] == 5
    assert item["test_price"] == round(item["current_price"] * 1.05, 2)
    proj = item["projection"]
    assert proj["weekly_revenue_new"] > proj["weekly_revenue_now"]
    assert proj["weekly_profit_new"] > proj["weekly_profit_now"]
    assert "not guaranteed" in item["plain_explain"]


def test_moderately_elastic_product_still_gains_profit_from_increase():
    # PED -1.5: revenue falls with a 5% rise, but at a 40% margin profit rises.
    proj = item_for(make_rows(PRICES_12_WEEKS, constant_elasticity(-1.5)))["projection"]
    assert proj["weekly_revenue_new"] < proj["weekly_revenue_now"]
    assert proj["weekly_profit_new"] > proj["weekly_profit_now"]


def test_very_elastic_product_suggests_testing_a_decrease():
    item = item_for(make_rows(PRICES_12_WEEKS, constant_elasticity(-4.0)))
    assert item["recommendation"] == "test_decrease"
    assert item["test_change_pct"] == -5


def test_hold_when_neither_direction_helps_profit():
    # The profit-maximising margin is 1/|PED|, so at PED -2.5 a 40% margin is already optimal.
    item = item_for(make_rows(PRICES_12_WEEKS, constant_elasticity(-2.5)), margin=0.4)
    assert item["recommendation"] == "hold"
    assert item["test_change_pct"] == 0


def test_projection_hand_calculated():
    # 100 units/week at price 10, PED -1.5, 40% margin (unit cost 6), +5% price:
    #   units = 100 × 1.05^-1.5 = 92.943, revenue = 92.943 × 10.5 = 975.90,
    #   profit = 92.943 × (10.5 − 6) = 418.24 (was 100 × 4 = 400)
    p = project(100, 10, -1.5, 0.40, 0.05)
    assert p == {
        "weekly_units_now": 100, "weekly_units_new": 92.94,
        "weekly_revenue_now": 1000, "weekly_revenue_new": 975.9,
        "weekly_profit_now": 400, "weekly_profit_new": 418.24,
    }


@pytest.mark.parametrize("bad", [0, 1, -0.1])
def test_invalid_margin_rejected(bad):
    with pytest.raises(ValueError):
        pricing_analysis(make_rows(PRICES_12_WEEKS, constant_elasticity(-1)), margin=bad)


# ── Sample files: no invented elasticity ──────────────────────────────────

def test_samples_have_no_price_variation_so_no_ped():
    """Legacy showed a PED for every product; the samples never change price."""
    for name in SAMPLE_FILES:
        legacy_peds = [i["ped"] for i in load_legacy_snapshot(name)["pricing"]["items"]]
        assert all(p is not None for p in legacy_peds)                 # what legacy did
        result = pricing_analysis(load_sample(name).rows)
        assert result["estimated_count"] == 0
        assert all(i["status"] == "insufficient_price_variation" and i["ped"] is None for i in result["items"])


# ── Promo simulator ───────────────────────────────────────────────────────

def test_promo_break_even_is_exact():
    rows = make_rows([10] * 12, lambda p: 20)
    result = simulate_promo(rows, "A", 10)
    # 10% off with a 40% margin: profit per unit 4 → 3, so 4/3 = 33.3% more units needed.
    assert result["break_even_volume_increase_pct"] == 33.3
    assert result["discounted_price"] == 9.0
    assert result["projection"] is None                          # no PED → no prediction
    assert "cannot predict" in result["plain_explain"]


def test_promo_projection_uses_estimated_ped_and_correct_profit():
    rows = make_rows(PRICES_12_WEEKS, constant_elasticity(-2.0))
    result = simulate_promo(rows, "A", 10)
    proj = result["projection"]
    expected = project(proj["weekly_units_now"], result["original_price"], result["ped"], 0.40, -0.10)
    assert proj == pytest.approx(expected, rel=1e-3)     # inputs above are already rounded
    # PED -2: units rise ~23%, below the 33% break-even, so profit falls.
    assert result["volume_change_pct"] == pytest.approx(23.5, abs=0.5)
    assert result["is_profitable_estimate"] is False


def test_promo_fixes_legacy_profit_formula():
    # 100 units at price 10, PED -2, 10% off, 40% margin → 123.46 units at 9, cost 6.
    p = project(100, 10, -2.0, 0.40, -0.10)
    assert p["weekly_profit_new"] == pytest.approx(123.46 * 3, abs=0.02)        # 370.37
    legacy_formula = p["weekly_revenue_new"] * (0.40 - 0.10)                     # 333.33
    assert abs(p["weekly_profit_new"] - legacy_formula) > 30


def test_promo_bigger_than_margin_always_loses():
    result = simulate_promo(make_rows([10] * 12, lambda p: 20), "A", 50)
    assert result["break_even_volume_increase_pct"] is None
    assert "sold at a loss" in result["plain_explain"]


@pytest.mark.parametrize("bad", [0, 0.5, 81, -5, "10", True, None])
def test_promo_rejects_invalid_discount(bad):
    with pytest.raises(ValueError):
        simulate_promo(make_rows([10] * 12, lambda p: 20), "A", bad)


def test_promo_unknown_sku():
    with pytest.raises(LookupError):
        simulate_promo(make_rows([10] * 12, lambda p: 20), "NOPE", 10)
