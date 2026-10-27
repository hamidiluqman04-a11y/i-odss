"""
Pricing: price elasticity of demand (PED) and a promotion simulator.

Replaces the legacy /api/pricing and /api/simulate/promo (approved decision D2).

The legacy app did not measure elasticity. It took a fixed number per
category (e.g. Skincare = 0.75), nudged it by sales speed, and presented the
result as the product's PED, with a guaranteed-sounding revenue gain. Now:

  - PED is ESTIMATED from the seller's own data, per product, only when the
    price actually changed over time. Sales are grouped by week and a
    log-log regression is fitted:  ln(units) = a + PED × ln(price).
    PED = -1.5 means "a 1% higher price went with about 1.5% fewer units".
  - The estimate comes with a 95% range and a p-value. If the link between
    price and sales is not clear (p ≥ 0.05) no price advice is given.
  - Products whose price never changed get "insufficient price variation"
    and no PED at all. (The legacy category numbers have no stated source,
    so they are not shown.)
  - Advice is limited to a small (5%) price TEST, chosen by its estimated
    effect on PROFIT at an assumed margin, with revenue shown alongside.
  - The promo simulator uses correct profit maths: the legacy formula
    multiplied discounted revenue by (margin − discount), which is wrong.

Known limitation: price changes often happen together with promotions,
seasons or ads, so a regression on sales history shows association, not
proof of cause. The explanations say this.
"""
import math

import numpy as np
import statsmodels.api as sm

from .kpis import count_days

DEFAULT_MARGIN = 0.40          # legacy assumption: 40% gross margin
TEST_CHANGE = 0.05             # suggested price test: ±5%
MIN_WEEKS_WITH_SALES = 6
MIN_PRICE_RANGE = 0.03         # max and min weekly price must differ by ≥ 3% of the average
SIGNIFICANCE = 0.05


def _check_margin(margin):
    if not 0 < margin < 1:
        raise ValueError("Margin must be between 0 and 1 (e.g. 0.40 for 40%).")


def _weekly_price_and_units(rows, first_day, complete_weeks):
    """
    Per week (counted from the first date in the whole file): average price paid
    and units sold. An unfinished final week is left out, because its low unit
    count would look like a reaction to whatever the price was that week.
    """
    weeks = {}
    for r in rows:
        week = (r["date"] - first_day).days // 7
        if week >= complete_weeks:
            continue
        w = weeks.setdefault(week, [0.0, 0])
        w[0] += r["qty"] * r["price"]
        w[1] += r["qty"]
    return [(revenue / units, units) for _, (revenue, units) in sorted(weeks.items())]


def estimate_ped(weekly):
    """
    Fit ln(units) = a + b·ln(price) on (price, units) pairs.
    Returns (status, estimate dict or None).
    """
    if len(weekly) < MIN_WEEKS_WITH_SALES:
        return "insufficient_data", None
    prices = np.array([p for p, _ in weekly])
    units = np.array([u for _, u in weekly], dtype=float)
    if len(np.unique(np.round(prices, 2))) < 2 or (prices.max() - prices.min()) / prices.mean() < MIN_PRICE_RANGE:
        return "insufficient_price_variation", None

    fit = sm.OLS(np.log(units), sm.add_constant(np.log(prices))).fit()
    low, high = fit.conf_int(alpha=0.05)[1]
    p_value = float(fit.pvalues[1]) if math.isfinite(fit.pvalues[1]) else 1.0
    return "estimated", {
        "ped": round(float(fit.params[1]), 2),
        "ped_ci_low": round(float(low), 2),
        "ped_ci_high": round(float(high), 2),
        "p_value": round(p_value, 4),
        "r_squared": round(float(fit.rsquared), 3),
        "reliability": "strong" if p_value < SIGNIFICANCE else "weak",
    }


def project(weekly_units, price, ped, margin, change):
    """
    Estimated weekly revenue and profit if the price changes by `change`
    (e.g. -0.10 for 10% off), assuming the elasticity stays constant.
    Unit cost is taken as (1 - margin) × current price.
    """
    cost = (1 - margin) * price
    new_price = price * (1 + change)
    new_units = weekly_units * (1 + change) ** ped
    return {
        "weekly_units_now":    round(weekly_units, 2),
        "weekly_units_new":    round(new_units, 2),
        "weekly_revenue_now":  round(weekly_units * price, 2),
        "weekly_revenue_new":  round(new_units * new_price, 2),
        "weekly_profit_now":   round(weekly_units * (price - cost), 2),
        "weekly_profit_new":   round(new_units * (new_price - cost), 2),
    }


def _sku_groups(rows):
    groups = {}
    for r in rows:
        groups.setdefault(r["sku"], []).append(r)
    return groups


def _baseline(sku_rows, days):
    """Current price (latest sale date) and average units per calendar week."""
    latest = max(r["date"] for r in sku_rows)
    latest_rows = [r for r in sku_rows if r["date"] == latest]
    current_price = sum(r["qty"] * r["price"] for r in latest_rows) / sum(r["qty"] for r in latest_rows)
    weekly_units = sum(r["qty"] for r in sku_rows) / days * 7
    return current_price, weekly_units


def _explain(item, n_weeks):
    name = item["product"]
    status = item["status"]
    if status == "insufficient_data":
        return (
            f"'{name}' sold in only {n_weeks} different week(s). At least {MIN_WEEKS_WITH_SALES} are "
            f"needed to see how price affects its sales."
        )
    if status == "insufficient_price_variation":
        return (
            f"'{name}' was always sold at about the same price, so your data cannot show how buyers "
            f"react to a price change. Try a small, planned price test to collect this evidence."
        )
    ped, low, high = item["ped"], item["ped_ci_low"], item["ped_ci_high"]
    if item["reliability"] == "weak":
        return (
            f"'{name}' was sold at different prices, but its sales did not move in a clear pattern with "
            f"price (PED {ped}, could be anywhere from {low} to {high}). No price change is suggested."
        )
    if ped >= 0:
        return (
            f"For '{name}', sales were higher in weeks when the price was higher (PED {ped}). That is "
            f"unusual and probably caused by something else, such as a season or advertising, so no "
            f"price change is suggested."
        )
    text = (
        f"In weeks when '{name}' cost 1% more, about {abs(ped):.1f}% fewer units were sold "
        f"(PED {ped}, likely between {low} and {high}). "
        + ("Buyers are not very sensitive to price. " if ped > -1 else "Buyers are price-sensitive. ")
    )
    proj, change = item["projection"], item["test_change_pct"]
    if change:
        verb = "raising" if change > 0 else "lowering"
        text += (
            f"Based on this, {verb} the price by {abs(change):.0f}% to {item['test_price']:.2f} is estimated to "
            f"change weekly revenue from {proj['weekly_revenue_now']:.2f} to {proj['weekly_revenue_new']:.2f} "
            f"and weekly profit from {proj['weekly_profit_now']:.2f} to {proj['weekly_profit_new']:.2f} "
            f"(at a {item['margin_assumption'] * 100:.0f}% margin). "
        )
    else:
        text += "Neither a 5% increase nor a 5% decrease is estimated to raise profit, so keep the current price. "
    return text + "This is based on past sales and is not guaranteed — test the change and watch the results."


def pricing_analysis(rows, margin=DEFAULT_MARGIN):
    """PED estimate and a cautious price-test suggestion for every product."""
    _check_margin(margin)
    first_day = min(r["date"] for r in rows)
    days = count_days(rows)
    items = []
    for sku, sku_rows in _sku_groups(rows).items():
        weekly = _weekly_price_and_units(sku_rows, first_day, days // 7)
        status, est = estimate_ped(weekly)
        current_price, weekly_units = _baseline(sku_rows, days)
        prices = [r["price"] for r in sku_rows]
        item = {
            "sku": sku,
            "product": sku_rows[-1]["product"],
            "category": sku_rows[-1]["category"],
            "current_price": round(current_price, 2),
            "price_min": round(min(prices), 2),
            "price_max": round(max(prices), 2),
            "weeks_with_sales": len(weekly),
            "status": status,
            "ped": None, "ped_ci_low": None, "ped_ci_high": None,
            "p_value": None, "r_squared": None, "reliability": None,
            "recommendation": "no_recommendation",
            "test_change_pct": 0, "test_price": None,
            "projection": None,
            "margin_assumption": margin,
        }
        if est:
            item.update(est)
            if est["reliability"] == "strong" and est["ped"] < 0:
                options = {
                    change: project(weekly_units, current_price, est["ped"], margin, change)
                    for change in (TEST_CHANGE, -TEST_CHANGE)
                }
                best = max(options, key=lambda c: options[c]["weekly_profit_new"])
                if options[best]["weekly_profit_new"] > options[best]["weekly_profit_now"]:
                    item["recommendation"] = "test_increase" if best > 0 else "test_decrease"
                    item["test_change_pct"] = round(best * 100)
                    item["test_price"] = round(current_price * (1 + best), 2)
                    item["projection"] = options[best]
                else:
                    item["recommendation"] = "hold"
                    item["projection"] = project(weekly_units, current_price, est["ped"], margin, 0.0)
        item["plain_explain"] = _explain(item, len(weekly))
        item["xai"] = (
            f"Weekly log-log OLS over {len(weekly)} weeks: ln(units) = a + PED·ln(price). "
            + (f"PED={item['ped']} (95% CI {item['ped_ci_low']} to {item['ped_ci_high']}), "
               f"p={item['p_value']}, R²={item['r_squared']}." if est else f"Not estimated: {status}.")
        )
        items.append(item)

    order = {"test_increase": 0, "test_decrease": 0, "hold": 1, "no_recommendation": 2}
    items.sort(key=lambda i: (order[i["recommendation"]], i["sku"]))
    return {
        "items": items,
        "margin_assumption": margin,
        "estimated_count": sum(1 for i in items if i["status"] == "estimated"),
        "min_weeks_with_sales": MIN_WEEKS_WITH_SALES,
    }


def promo_inputs(rows):
    """
    The per-product summary the promo simulator needs: current price, average
    weekly units and the PED estimate. Saving this (instead of the raw rows)
    lets promotions be simulated later without keeping the uploaded file.
    """
    first_day = min(r["date"] for r in rows)
    days = count_days(rows)
    inputs = {}
    for sku, sku_rows in _sku_groups(rows).items():
        current_price, weekly_units = _baseline(sku_rows, days)
        status, est = estimate_ped(_weekly_price_and_units(sku_rows, first_day, days // 7))
        inputs[sku] = {
            "product": sku_rows[-1]["product"],
            "current_price": current_price,
            "weekly_units": weekly_units,
            "ped_status": status,
            "ped": est["ped"] if est else None,
            "reliability": est["reliability"] if est else None,
        }
    return inputs


def simulate_promo(rows, sku, discount_pct, margin=DEFAULT_MARGIN):
    """Promo simulation straight from the clean rows (see simulate_promo_from)."""
    inputs = promo_inputs(rows).get(sku)
    if inputs is None:
        raise LookupError(f"SKU '{sku}' not found in the uploaded data.")
    return simulate_promo_from(sku, inputs, discount_pct, margin)


def simulate_promo_from(sku, inputs, discount_pct, margin=DEFAULT_MARGIN):
    """
    What a discount on one product would do to weekly revenue and profit.
    `inputs` is one product's entry from promo_inputs().
    The break-even volume increase is always exact; the projected volume
    change is only given when PED could be estimated reliably from the data.
    """
    _check_margin(margin)
    if isinstance(discount_pct, bool) or not isinstance(discount_pct, (int, float)) or not 1 <= discount_pct <= 80:
        raise ValueError("Discount must be a number between 1 and 80 (%).")

    d = discount_pct / 100
    current_price, weekly_units = inputs["current_price"], inputs["weekly_units"]
    ped, reliability, name = inputs["ped"], inputs["reliability"], inputs["product"]

    # Profit per unit falls from margin×p to (margin−d)×p, so units must rise by d/(margin−d).
    break_even = round(d / (margin - d) * 100, 1) if d < margin else None
    result = {
        "sku": sku, "product": name, "discount_pct": discount_pct,
        "original_price": round(current_price, 2),
        "discounted_price": round(current_price * (1 - d), 2),
        "margin_assumption": margin,
        "break_even_volume_increase_pct": break_even,
        "ped_status": inputs["ped_status"], "ped": ped, "reliability": reliability,
        "projection": None, "volume_change_pct": None, "is_profitable_estimate": None,
    }

    if break_even is None:
        explain = (
            f"A {discount_pct}% discount is larger than your assumed {margin * 100:.0f}% margin, so every "
            f"unit of '{name}' would be sold at a loss, however many more you sell."
        )
    else:
        explain = (
            f"With a {margin * 100:.0f}% margin, a {discount_pct}% discount on '{name}' only pays off if "
            f"you sell at least {break_even:.0f}% more units than now. "
        )
        if reliability == "strong" and ped < 0:
            proj = project(weekly_units, current_price, ped, margin, -d)
            volume_change = round((proj["weekly_units_new"] / proj["weekly_units_now"] - 1) * 100, 1)
            profitable = proj["weekly_profit_new"] > proj["weekly_profit_now"]
            result.update(projection=proj, volume_change_pct=volume_change, is_profitable_estimate=profitable)
            explain += (
                f"Your past sales (PED {ped}) suggest about {volume_change:.0f}% more units, so this "
                f"promotion is estimated to {'raise' if profitable else 'lower'} weekly profit "
                f"({proj['weekly_profit_now']:.2f} → {proj['weekly_profit_new']:.2f}). This is an estimate, "
                f"not a guarantee."
            )
        else:
            explain += (
                "Your data does not show reliably how buyers of this product react to price, so I-ODSS "
                "cannot predict whether that will happen."
            )
    result["plain_explain"] = explain
    return result
