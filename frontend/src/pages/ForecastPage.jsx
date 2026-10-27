import ForecastChart from "../charts/ForecastChart";
import ChartCard from "../components/ChartCard";
import ResultPage from "../components/ResultPage";
import { Tile } from "../components/Tile";
import { formatNumber } from "../services/format";

export default function ForecastPage() {
  return (
    <ResultPage
      kind="forecast"
      title="Demand forecast"
      intro="How many units you are likely to sell in each of the next 4 weeks (all products together), based on your past weekly sales."
    >
      {(data) => <Forecast data={data} />}
    </ResultPage>
  );
}

const TREND_TEXT = { Upward: "Rising", Downward: "Falling", Stable: "About the same", Unknown: "Unknown" };

export function Forecast({ data }) {
  if (data.status === "insufficient_data") {
    return (
      <div className="card stack">
        <h2>Not enough history to forecast</h2>
        <p className="secondary">{data.plain_explain}</p>
        <Notes notes={data.notes} />
      </div>
    );
  }

  const s = data.summary;
  const ev = data.evaluation;
  const forecastRows = data.series.filter((p) => p.forecast !== null);
  const change = s.forecast_change_pct;

  return (
    <>
      <div className="tiles">
        <Tile label="Expected units per week" value={formatNumber(s.forecast_avg_weekly, 0)}
          note={`Next ${data.horizon_weeks} weeks, all products`} />
        <Tile label="Compared with last 4 weeks" value={change === null ? "—" : `${change > 0 ? "+" : ""}${formatNumber(change, 1)}%`}
          note={TREND_TEXT[s.trend]} />
        <Tile label="Forecast accuracy (MAPE)" value={ev?.mape != null ? `${formatNumber(ev.mape, 1)}% error` : "Not measurable"}
          note={ev ? `Tested on your last ${ev.holdout_weeks} weeks` : "Needs more history to test"} />
        <Tile label="Method" value={data.model_type === "sarima" ? "SARIMA" : "Moving average"}
          note={`${s.n_weeks} full weeks of history`} />
      </div>

      <div className="explain">
        <strong>What this means: </strong>{data.plain_explain}
      </div>

      <ChartCard
        title="Weekly units: actual and forecast"
        subtitle={data.model}
        columns={[
          { key: "label", label: "Week" },
          { key: "week_start", label: "Week starting" },
          { key: "actual", label: "Actual units", numeric: true, format: (v) => (v === null ? "—" : formatNumber(v)) },
          { key: "forecast", label: "Forecast", numeric: true, format: (v) => (v === null ? "—" : formatNumber(v, 1)) },
          { key: "lower", label: "Low (5%)", numeric: true, format: (v) => (v === null ? "—" : formatNumber(v, 1)) },
          { key: "upper", label: "High (95%)", numeric: true, format: (v) => (v === null ? "—" : formatNumber(v, 1)) },
        ]}
        rows={data.series}
      >
        <ForecastChart series={data.series} />
      </ChartCard>

      <div className="grid-2">
        <section className="card stack">
          <h2>Next {forecastRows.length} weeks</h2>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Week starting</th><th className="num">Forecast</th><th className="num">Likely range</th></tr></thead>
              <tbody>
                {forecastRows.map((p) => (
                  <tr key={p.label}>
                    <td>{p.week_start}</td>
                    <td className="num">{formatNumber(p.forecast, 0)}</td>
                    <td className="num">{formatNumber(p.lower, 0)} – {formatNumber(p.upper, 0)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
        <Accuracy evaluation={ev} modelType={data.model_type} />
      </div>

      <Notes notes={data.notes} />
    </>
  );
}

function Accuracy({ evaluation: ev, modelType }) {
  if (!ev) {
    return (
      <section className="card stack">
        <h2>How accurate is it?</h2>
        <p className="secondary">
          To test accuracy, I-ODSS hides your last 4 weeks, forecasts them from the earlier weeks, and compares.
          Your file does not have enough weeks for a fair test yet, so no accuracy figure is shown.
        </p>
      </section>
    );
  }
  const weeks = ev.actual.map((a, i) => ({ week: i + 1, actual: a, predicted: ev.predicted[i] }));
  const beatsBaseline = ev.mape != null && ev.baseline_mape != null && ev.mape <= ev.baseline_mape;
  return (
    <section className="card stack">
      <h2>How accurate is it?</h2>
      <p className="secondary small">
        I-ODSS hid your last {ev.holdout_weeks} weeks, forecast them from the weeks before, and compared the result
        with what you really sold.
      </p>
      <div className="metric-row">
        <div><span>Average error (MAPE)</span><strong>{ev.mape != null ? `${formatNumber(ev.mape, 1)}%` : "n/a"}</strong></div>
        <div><span>Average error (units)</span><strong>{formatNumber(ev.mae, 1)}</strong></div>
        {modelType === "sarima" && (
          <div><span>Simple average's error</span><strong>{ev.baseline_mape != null ? `${formatNumber(ev.baseline_mape, 1)}%` : "n/a"}</strong></div>
        )}
      </div>
      {modelType === "sarima" && ev.mape != null && ev.baseline_mape != null && (
        <p className="small secondary">
          {beatsBaseline
            ? "The SARIMA model was at least as accurate as simply averaging the last 4 weeks."
            : "A simple 4-week average was more accurate here — treat the forecast with caution."}
        </p>
      )}
      <div className="table-wrap">
        <table>
          <thead><tr><th>Test week</th><th className="num">Actual</th><th className="num">Predicted</th></tr></thead>
          <tbody>
            {weeks.map((w) => (
              <tr key={w.week}><td>{w.week}</td><td className="num">{formatNumber(w.actual)}</td><td className="num">{formatNumber(w.predicted, 1)}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function Notes({ notes }) {
  if (!notes?.length) return null;
  return (
    <div className="alert alert-info">
      <strong>Notes</strong>
      <ul>{notes.map((n, i) => <li key={i}>{n}</li>)}</ul>
    </div>
  );
}
