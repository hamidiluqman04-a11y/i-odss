import datetime

import numpy as np
import pytest

from apps.analytics.services import forecasting
from apps.analytics.services.forecasting import daily_series, forecast_demand
from tests.conftest import SAMPLE_FILES, load_sample

START = datetime.date(2025, 1, 6)
WEEKLY_PATTERN = [5, 5, 6, 6, 9, 14, 11]   # busier towards the weekend


def make_rows(daily_units, sku="A", start=START):
    """Rows in the same shape the CSV parser produces (days with 0 sales have no row)."""
    return [
        {"date": start + datetime.timedelta(days=i), "qty": int(q), "sku": sku}
        for i, q in enumerate(daily_units) if q > 0
    ]


def pattern_days(weeks, growth_per_week=0.0):
    return [round(WEEKLY_PATTERN[d % 7] * (1 + growth_per_week * (d // 7))) for d in range(weeks * 7)]


# ── SARIMA on data with a clear pattern ───────────────────────────────────

def test_sarima_learns_a_clear_weekly_pattern():
    history = pattern_days(20, growth_per_week=0.02)
    future = pattern_days(24, growth_per_week=0.02)[20 * 7:]
    result = forecast_demand(make_rows(history))

    assert result["status"] == "ok"
    assert result["model_type"] == "sarima"
    assert result["evaluation"]["mape"] < 5          # measured on held-back weeks
    true_weeks = np.asarray(future).reshape(4, 7).sum(axis=1)
    predicted = [s["forecast"] for s in result["series"] if s["forecast"] is not None]
    assert np.allclose(predicted, true_weeks, rtol=0.05)


def test_prediction_interval_contains_forecast_and_is_not_negative():
    rng = np.random.default_rng(1)
    noisy = [max(0, q + rng.integers(-3, 4)) for q in pattern_days(12)]
    for week in forecast_demand(make_rows(noisy))["series"][-4:]:
        assert 0 <= week["lower"] <= week["forecast"] <= week["upper"]


def test_same_data_gives_same_result():
    rows = make_rows(pattern_days(10, growth_per_week=0.05))
    assert forecast_demand(rows) == forecast_demand(rows)


# ── Accuracy is measured, not hardcoded ───────────────────────────────────

def test_mape_is_calculated_from_the_held_back_weeks():
    rng = np.random.default_rng(2)
    noisy = [max(1, q + rng.integers(-4, 5)) for q in pattern_days(12)]
    ev = forecast_demand(make_rows(noisy))["evaluation"]
    actual, predicted = np.array(ev["actual"]), np.array(ev["predicted"])
    assert ev["mape"] == pytest.approx(np.mean(np.abs(predicted - actual) / actual) * 100, abs=0.2)
    assert ev["mae"] == pytest.approx(np.mean(np.abs(predicted - actual)), abs=0.2)
    assert ev["holdout_weeks"] == 4


def test_mape_differs_between_datasets():
    rng = np.random.default_rng(3)
    clean = pattern_days(12)
    noisy = [max(1, q + rng.integers(-6, 7)) for q in clean]
    assert forecast_demand(make_rows(clean))["evaluation"]["mape"] != forecast_demand(make_rows(noisy))["evaluation"]["mape"]


def test_mape_not_reported_when_a_test_week_sold_nothing():
    days = pattern_days(12)
    days[-14:-7] = [0] * 7            # one held-back week with zero sales
    result = forecast_demand(make_rows(days))
    assert result["evaluation"]["mape"] is None
    assert result["evaluation"]["mae"] > 0
    assert any("MAPE cannot be calculated" in n for n in result["notes"])


def test_samples_get_real_measured_results():
    """Legacy reported MAPE 4.2 for every file; now it depends on the data."""
    mapes = []
    for name in SAMPLE_FILES:
        result = forecast_demand(load_sample(name).rows)
        assert result["status"] == "ok"
        expected = "sarima" if result["summary"]["n_weeks"] >= 8 else "moving_average"
        assert result["model_type"] == expected
        if result["evaluation"]:
            mapes.append(result["evaluation"]["mape"])
    assert len(set(mapes)) > 1
    assert 4.2 not in mapes


# ── Short or unusual histories ────────────────────────────────────────────

def test_short_history_uses_labelled_moving_average():
    days = pattern_days(5)
    result = forecast_demand(make_rows(days))
    assert result["model_type"] == "moving_average"
    assert result["model"] == "4-week moving average"
    last_four_weeks = np.asarray(days).reshape(5, 7).sum(axis=1)[-4:]
    assert all(s["forecast"] == round(last_four_weeks.mean(), 1) for s in result["series"][-4:])
    assert result["evaluation"] is None              # 5 weeks: too few to hold back 4
    assert any("moving average" in n for n in result["notes"])


def test_moving_average_is_evaluated_with_six_weeks():
    assert forecast_demand(make_rows(pattern_days(6)))["evaluation"] is not None


def test_less_than_two_weeks_gives_no_forecast():
    result = forecast_demand(make_rows([3] * 10))
    assert result["status"] == "insufficient_data"
    assert result["series"] == []
    assert "At least 2 full weeks" in result["plain_explain"]


def test_unfinished_last_week_is_left_out():
    days = pattern_days(8) + [500, 500, 500]          # 3 extra days, unusually high
    result = forecast_demand(make_rows(days))
    assert result["summary"]["excluded_days"] == 3
    history = [s for s in result["series"] if s["actual"] is not None]
    assert len(history) == 8
    assert max(s["actual"] for s in history) < 100


def test_days_without_sales_count_as_zero():
    rows = make_rows([4, 0, 0, 2])
    assert list(daily_series(rows)) == [4.0, 0.0, 0.0, 2.0]


def test_week_labels_and_start_dates():
    series = forecast_demand(make_rows(pattern_days(8)))["series"]
    assert (series[0]["label"], series[0]["week_start"]) == ("Wk 1", "2025-01-06")
    assert (series[8]["label"], series[8]["week_start"]) == ("Wk 9 (F)", "2025-03-03")


# ── Filtering and failure handling ────────────────────────────────────────

def test_forecast_for_one_sku():
    rows = make_rows(pattern_days(8), sku="A") + make_rows([50] * 56, sku="B")
    only_a = forecast_demand(rows, sku="A")
    assert only_a["sku"] == "A"
    assert only_a["series"][0]["actual"] == sum(WEEKLY_PATTERN)


def test_unknown_sku_raises():
    with pytest.raises(ValueError, match="not found"):
        forecast_demand(make_rows(pattern_days(8)), sku="NOPE")


def test_falls_back_to_moving_average_if_sarima_fails(monkeypatch):
    def broken_fit(values):
        raise np.linalg.LinAlgError("singular matrix")

    monkeypatch.setattr(forecasting, "_fit_sarima", broken_fit)
    result = forecast_demand(make_rows(pattern_days(10)))
    assert result["model_type"] == "moving_average"
    assert any("could not be fitted" in n for n in result["notes"])


def test_explanation_is_cautious():
    text = forecast_demand(make_rows(pattern_days(12)))["plain_explain"]
    assert "not a guarantee" in text
    assert "off by about" in text


# ── Seasonal-naive benchmark ──────────────────────────────────────────────

def test_seasonal_naive_baseline_is_measured():
    rng = np.random.default_rng(4)
    days = [max(1, q + rng.integers(-3, 4)) for q in pattern_days(12)]
    ev = forecast_demand(make_rows(days))["evaluation"]
    # Hand check: it predicts every held-back week = the last training week's total.
    train_last_week = sum(days[-28 - 7:-28])
    actual = np.array(ev["actual"])
    expected_mape = np.mean(np.abs(train_last_week - actual) / actual) * 100
    assert ev["seasonal_naive_mape"] == pytest.approx(expected_mape, abs=0.2)
    assert ev["seasonal_naive_mae"] == pytest.approx(np.mean(np.abs(train_last_week - actual)), abs=0.2)


def test_seasonal_naive_is_perfect_on_a_repeating_week():
    """A pure weekly pattern is exactly what 'repeat last week' captures."""
    ev = forecast_demand(make_rows(pattern_days(12)))["evaluation"]
    assert ev["seasonal_naive_mape"] == 0.0


def test_explanation_names_the_baseline_that_did_better(monkeypatch):
    rows = make_rows(pattern_days(12))
    real = forecasting.evaluate

    def worse_model(values, model_type):
        ev = real(values, model_type)
        return {**ev, "mape": 50.0}

    monkeypatch.setattr(forecasting, "evaluate", worse_model)
    text = forecast_demand(rows)["plain_explain"]
    # Both benchmarks score 0% on a perfectly repeating week; either may be named.
    assert ("simply repeating last week did better (0%)" in text
            or "simply averaging the last 4 weeks did better (0%)" in text)


def test_best_baseline_picks_the_lowest_error():
    assert forecasting.best_baseline({"baseline_mape": 12.0, "seasonal_naive_mape": 8.0}) == ("seasonal_naive", 8.0)
    assert forecasting.best_baseline({"baseline_mape": 5.0, "seasonal_naive_mape": 8.0}) == ("baseline", 5.0)
    assert forecasting.best_baseline({"baseline_mape": None, "seasonal_naive_mape": None}) is None


# ── Gaps: "no data" versus "no sales" ─────────────────────────────────────

def test_long_run_without_sales_is_flagged_as_possible_missing_data():
    days = pattern_days(10)
    days[21:31] = [0] * 10                      # 10 empty days in weeks 4-5
    result = forecast_demand(make_rows(days))
    assert result["summary"]["gaps"] == [{"start": "2025-01-27", "end": "2025-02-05", "days": 10}]
    assert result["summary"]["zero_sales_days"] == 10
    assert any("export may be missing data" in n for n in result["notes"])


def test_short_quiet_spells_are_not_flagged():
    days = pattern_days(10)
    days[21:27] = [0] * 6                       # 6 days: below the 7-day threshold
    result = forecast_demand(make_rows(days))
    assert result["summary"]["gaps"] == []
    assert result["summary"]["zero_sales_days"] == 6
    assert not any("missing data" in n for n in result["notes"])
