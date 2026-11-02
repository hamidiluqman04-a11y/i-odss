"""
Demand forecasting: predicts units sold per week for the next 4 weeks.

Replaces the legacy /api/forecast (approved decision D2). The legacy app was
labelled "SARIMA (1,1,1)(1,1,0)[7]" but actually drew a straight trend line
plus a sine wave, and always reported MAPE = 4.2%. Here:

  - A real SARIMA(1,1,1)(1,1,0)[7] model (statsmodels) is fitted to DAILY
    sales, so the [7] means a weekly shopping pattern (e.g. busy weekends).
    Daily forecasts are added up into weekly totals for display.
  - Accuracy is MEASURED: the model is re-fitted without the last 4 weeks,
    asked to predict them, and compared with what really happened (MAPE).
    Two simple benchmarks are scored the same way: a 4-week average and a
    seasonal-naive forecast (repeat the last week, the standard baseline for
    a weekly pattern).
  - Long runs of days with no sales are reported as possible missing data,
    because a sales export cannot tell "nothing sold" from "rows missing".
  - With too little history, a clearly labelled 4-week moving average is
    used instead, and with almost no history no forecast is given at all.
  - An unfinished final week is left out, because its low total would look
    like a sudden drop in demand.
"""
import warnings

import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX

HORIZON_WEEKS = 4
HORIZON_DAYS = HORIZON_WEEKS * 7
SARIMA_ORDER = (1, 1, 1)
SARIMA_SEASONAL_ORDER = (1, 1, 0, 7)
SARIMA_LABEL = "SARIMA(1,1,1)(1,1,0)[7] on daily sales"
MOVING_AVERAGE_LABEL = "4-week moving average"

MIN_WEEKS_ANY = 2          # below this: no forecast at all
MIN_WEEKS_SARIMA = 8       # below this: moving average instead of SARIMA
MIN_TRAIN_WEEKS = {"sarima": MIN_WEEKS_SARIMA - 2, "moving_average": 2}  # needed before the 4 test weeks
INTERVAL = (5, 95)         # 90% prediction interval
SIMULATIONS = 1000
STABLE_BAND_PCT = 5


# ── Building the series ───────────────────────────────────────────────────

def daily_series(rows):
    """Units sold per calendar day (0 on days without sales), as a pandas Series."""
    units = pd.Series([r["qty"] for r in rows], index=pd.to_datetime([r["date"] for r in rows]))
    daily = units.groupby(level=0).sum()
    full_range = pd.date_range(daily.index.min(), daily.index.max(), freq="D")
    return daily.reindex(full_range, fill_value=0).astype(float)


def _weekly_totals(values):
    """Turn a daily array (length divisible by 7) into weekly totals."""
    return np.asarray(values, dtype=float).reshape(-1, 7).sum(axis=1)


# ── Models ────────────────────────────────────────────────────────────────

def _fit_sarima(daily_values):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # statsmodels warns a lot on short series
        model = SARIMAX(daily_values, order=SARIMA_ORDER, seasonal_order=SARIMA_SEASONAL_ORDER)
        return model.fit(disp=False)


def _sarima_forecast(daily_values, with_interval):
    """Returns (weekly point forecasts, lower, upper, converged)."""
    result = _fit_sarima(daily_values)
    point = _weekly_totals(np.clip(result.forecast(HORIZON_DAYS), 0, None))
    lower = upper = None
    if with_interval:
        # Simulate many possible futures, add them up per week, take the 5th-95th percentile.
        sims = result.simulate(
            HORIZON_DAYS, repetitions=SIMULATIONS, anchor="end", random_state=np.random.default_rng(0)
        )
        sims = np.clip(np.asarray(sims).reshape(HORIZON_DAYS, -1), 0, None)
        weekly_sims = sims.reshape(HORIZON_WEEKS, 7, -1).sum(axis=1)
        lower, upper = np.percentile(weekly_sims, INTERVAL, axis=1)
    converged = bool(result.mle_retvals.get("converged", True)) if result.mle_retvals else True
    return point, lower, upper, converged


def _moving_average_forecast(daily_values, with_interval):
    """Every future week = average of the last (up to) 4 complete weeks."""
    recent = _weekly_totals(daily_values)[-4:]
    point = np.full(HORIZON_WEEKS, recent.mean())
    lower = upper = None
    if with_interval:
        spread = 1.645 * recent.std(ddof=1) if len(recent) > 1 else 0.0  # rough 90% band
        lower, upper = np.clip(point - spread, 0, None), point + spread
    return point, lower, upper, True


def _seasonal_naive_forecast(daily_values):
    """
    Benchmark only: every future day sells the same as that weekday in the last
    week, so each future week equals the last full week. This is the standard
    baseline for data with a weekly pattern; a model that cannot beat it adds nothing.
    """
    return np.full(HORIZON_WEEKS, float(np.sum(daily_values[-7:])))


MODELS = {"sarima": _sarima_forecast, "moving_average": _moving_average_forecast}
BASELINE_LABELS = {"baseline": "averaging the last 4 weeks", "seasonal_naive": "repeating last week"}


# ── Data gaps ─────────────────────────────────────────────────────────────

MIN_GAP_DAYS = 7   # this many days in a row with no sales may mean missing data, not zero demand


def find_gaps(daily):
    """
    Runs of at least MIN_GAP_DAYS consecutive days with no sales, inside the data's date range.
    A sales export cannot tell "shop closed / nothing sold" apart from "rows missing from
    the export", so these days are counted as zero but reported so the seller can check.
    """
    gaps, start = [], None
    for day, units in daily.items():
        if units == 0 and start is None:
            start = day
        elif units != 0 and start is not None:
            if (day - start).days >= MIN_GAP_DAYS:
                gaps.append((start, day - pd.Timedelta(days=1)))
            start = None
    return [{"start": s.date().isoformat(), "end": e.date().isoformat(), "days": (e - s).days + 1} for s, e in gaps]


# ── Accuracy check ────────────────────────────────────────────────────────

def _errors(predicted, actual):
    mae = float(np.mean(np.abs(predicted - actual)))
    # MAPE divides by the actual value, so it cannot be used when a week sold 0.
    mape = float(np.mean(np.abs(predicted - actual) / actual) * 100) if np.all(actual > 0) else None
    return mae, mape


def evaluate(daily_values, model_type):
    """
    Hold back the last 4 weeks, forecast them from the earlier data, compare.
    Returns None when there is not enough history to do this fairly.
    """
    weeks = len(daily_values) // 7
    if weeks < HORIZON_WEEKS + MIN_TRAIN_WEEKS[model_type]:
        return None
    train, test = daily_values[:-HORIZON_DAYS], daily_values[-HORIZON_DAYS:]
    actual = _weekly_totals(test)
    predicted = MODELS[model_type](train, with_interval=False)[0]
    baseline = _moving_average_forecast(train, with_interval=False)[0]
    seasonal = _seasonal_naive_forecast(train)
    mae, mape = _errors(predicted, actual)
    baseline_mae, baseline_mape = _errors(baseline, actual)
    seasonal_mae, seasonal_mape = _errors(seasonal, actual)
    r = lambda v: round(v, 1) if v is not None else None
    return {
        "holdout_weeks":       HORIZON_WEEKS,
        "mape":                r(mape),
        "mae":                 r(mae),
        "baseline_mape":       r(baseline_mape),        # simple 4-week average
        "baseline_mae":        r(baseline_mae),
        "seasonal_naive_mape": r(seasonal_mape),        # repeat last week
        "seasonal_naive_mae":  r(seasonal_mae),
        "actual":              [round(float(v), 1) for v in actual],
        "predicted":           [round(float(v), 1) for v in predicted],
    }


def best_baseline(evaluation):
    """The baseline with the lowest error, as (key, mape) — or None when MAPE is unavailable."""
    candidates = [(k, evaluation.get(f"{k}_mape")) for k in ("baseline", "seasonal_naive")]
    candidates = [(k, m) for k, m in candidates if m is not None]
    return min(candidates, key=lambda c: c[1]) if candidates else None


# ── Public entry point ────────────────────────────────────────────────────

def forecast_demand(rows, sku=None):
    """
    Forecast weekly units for the next 4 weeks, for all products or one SKU.
    Raises ValueError if the SKU is not in the data.
    """
    if sku is not None:
        rows = [r for r in rows if r["sku"] == sku]
        if not rows:
            raise ValueError(f"SKU '{sku}' not found in the uploaded data.")

    daily = daily_series(rows)
    gaps = find_gaps(daily)
    total_days = len(daily)
    complete_weeks = total_days // 7
    excluded_days = total_days - complete_weeks * 7
    daily = daily.iloc[: complete_weeks * 7]
    notes = []
    if excluded_days:
        notes.append(f"The last {excluded_days} day(s) do not make a full week and were left out.")
    for g in gaps:
        notes.append(
            f"No sales were recorded from {g['start']} to {g['end']} ({g['days']} days). These days are counted "
            f"as zero sales; if your shop was open then, the export may be missing data and the forecast will be too low."
        )

    if complete_weeks < MIN_WEEKS_ANY:
        return {
            "status": "insufficient_data", "model": None, "model_type": None, "sku": sku,
            "series": [], "evaluation": None,
            "summary": {"n_weeks": complete_weeks, "excluded_days": excluded_days, "gaps": gaps},
            "notes": notes,
            "plain_explain": (
                f"Your file covers only {total_days} day(s) of sales. At least {MIN_WEEKS_ANY} full weeks "
                f"are needed before I-ODSS can forecast demand."
            ),
        }

    values = daily.to_numpy()
    model_type = "sarima" if complete_weeks >= MIN_WEEKS_SARIMA else "moving_average"
    if model_type == "moving_average":
        notes.append(
            f"Only {complete_weeks} full weeks of history: SARIMA needs at least {MIN_WEEKS_SARIMA}, "
            f"so a simple 4-week moving average is used."
        )

    converged = True
    try:
        point, lower, upper, converged = MODELS[model_type](values, with_interval=True)
        evaluation = evaluate(values, model_type)
    except Exception:  # numerical failure inside statsmodels
        if model_type != "sarima":
            raise
        notes.append("The SARIMA model could not be fitted to this data, so a 4-week moving average is used.")
        model_type = "moving_average"
        point, lower, upper, converged = _moving_average_forecast(values, with_interval=True)
        evaluation = evaluate(values, model_type)
    if not converged:
        notes.append("The SARIMA fitting did not fully converge; treat this forecast with extra caution.")
    if evaluation is None:
        notes.append("Not enough history to hold back 4 weeks and measure accuracy.")
    elif evaluation["mape"] is None:
        notes.append("MAPE cannot be calculated because a test week had zero sales; see MAE instead.")

    history = _weekly_totals(values)
    first_day = daily.index[0]
    series = [
        {"label": f"Wk {i + 1}", "week_start": (first_day + pd.Timedelta(weeks=i)).date().isoformat(),
         "actual": round(float(v), 1), "forecast": None, "lower": None, "upper": None}
        for i, v in enumerate(history)
    ]
    for i in range(HORIZON_WEEKS):
        w = complete_weeks + i
        series.append({
            "label": f"Wk {w + 1} (F)", "week_start": (first_day + pd.Timedelta(weeks=w)).date().isoformat(),
            "actual": None, "forecast": round(float(point[i]), 1),
            "lower": round(float(lower[i]), 1), "upper": round(float(upper[i]), 1),
        })

    recent_avg = float(history[-4:].mean())
    forecast_avg = float(point.mean())
    change = (forecast_avg - recent_avg) / recent_avg * 100 if recent_avg else None
    trend = (
        "Unknown" if change is None
        else "Stable" if abs(change) < STABLE_BAND_PCT
        else "Upward" if change > 0 else "Downward"
    )
    summary = {
        "n_weeks":             complete_weeks,
        "excluded_days":       excluded_days,
        "avg_weekly":          round(float(history.mean()), 1),
        "recent_avg_weekly":   round(recent_avg, 1),
        "forecast_avg_weekly": round(forecast_avg, 1),
        "forecast_change_pct": round(change, 1) if change is not None else None,
        "trend":               trend,
        "zero_sales_days":     int((values == 0).sum()),
        "gaps":                gaps,
    }
    return {
        "status": "ok",
        "model": SARIMA_LABEL if model_type == "sarima" else MOVING_AVERAGE_LABEL,
        "model_type": model_type,
        "sku": sku,
        "horizon_weeks": HORIZON_WEEKS,
        "series": series,
        "evaluation": evaluation,
        "summary": summary,
        "notes": notes,
        "plain_explain": _explain(summary, evaluation, lower, upper),
    }


def _explain(summary, evaluation, lower, upper):
    text = (
        f"Based on {summary['n_weeks']} weeks of sales, I-ODSS expects about "
        f"{summary['forecast_avg_weekly']:.0f} units per week over the next {HORIZON_WEEKS} weeks "
        f"(most likely between {float(np.mean(lower)):.0f} and {float(np.mean(upper)):.0f})."
    )
    if summary["forecast_change_pct"] is not None:
        if summary["trend"] == "Stable":
            text += " That is about the same as your last 4 weeks."
        else:
            direction = "more" if summary["forecast_change_pct"] > 0 else "less"
            text += f" That is about {abs(summary['forecast_change_pct']):.0f}% {direction} than your last 4 weeks."
    if evaluation and evaluation["mape"] is not None:
        text += (
            f" When tested on your last {HORIZON_WEEKS} weeks of known sales, the forecast was off by "
            f"about {evaluation['mape']:.0f}% on average"
        )
        best = best_baseline(evaluation)
        if best and best[1] < evaluation["mape"]:
            text += f" — simply {BASELINE_LABELS[best[0]]} did better ({best[1]:.0f}%), so be cautious"
        text += "."
    else:
        text += " There is not yet enough history to test how accurate this forecast is."
    return text + " Treat this as a guide for planning, not a guarantee."
