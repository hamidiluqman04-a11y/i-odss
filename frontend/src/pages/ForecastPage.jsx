import ForecastChart from "../charts/ForecastChart";
import { Answer, Method } from "../components/Answer";
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
      <Answer headline={`Plan for about ${formatNumber(s.forecast_avg_weekly, 0)} units a week`}>
        {data.plain_explain}
      </Answer>

      <div className="tiles">
        <Tile label="Expected units per week" value={formatNumber(s.forecast_avg_weekly, 0)}
          note={`Next ${data.horizon_weeks} weeks, all products`} />
        <Tile label="Compared with last 4 weeks" value={change === null ? "—" : `${change > 0 ? "+" : ""}${formatNumber(change, 1)}%`}
          note={TREND_TEXT[s.trend]} />
        <Tile label="Forecast accuracy (MAPE)" value={ev?.mape != null ? `${formatNumber(ev.mape, 1)}% error` : "Not measurable"}
          note={ev ? `Tested on your last ${ev.holdout_weeks} weeks` : "Needs more history to test"} />
      </div>

      <ChartCard
        title="Weekly units: actual and forecast"
        subtitle="Solid line is what you sold; dashed line and shading are the forecast and its likely range"
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

      <section className="card stack">
        <div>
          <h2>Next {forecastRows.length} weeks</h2>
          <p className="small secondary">Order enough for the forecast; the likely range shows how far it could swing.</p>
        </div>
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

      <Method hint={`${data.model_type === "sarima" ? "SARIMA" : "Moving average"} on ${s.n_weeks} full weeks of history · measured accuracy`}>
        <p className="small secondary"><strong>Model:</strong> {data.model}</p>
        <Accuracy evaluation={ev} modelType={data.model_type} />
        <Notes notes={data.notes} />
      </Method>
    </>
  );
}

function Accuracy({ evaluation: ev, modelType }) {
  if (!ev) {
    return (
      <div className="stack">
        <h3>How accurate is it?</h3>
        <p className="secondary small">
          To test accuracy, I-ODSS hides your last 4 weeks, forecasts them from the earlier weeks, and compares.
          Your file does not have enough weeks for a fair test yet, so no accuracy figure is shown.
        </p>
      </div>
    );
  }
  const weeks = ev.actual.map((a, i) => ({ week: i + 1, actual: a, predicted: ev.predicted[i] }));
  // Benchmarks: a 4-week average, and "repeat last week" (seasonal naive). Older saved results lack the second.
  const benchmarks = [
    { name: "averaging the last 4 weeks", mape: ev.baseline_mape },
    { name: "repeating last week", mape: ev.seasonal_naive_mape ?? null },
  ].filter((b) => b.mape != null);
  const better = ev.mape != null ? benchmarks.filter((b) => b.mape < ev.mape) : [];
  return (
    <div className="stack">
      <h3>How accurate is it?</h3>
      <p className="secondary small">
        I-ODSS hid your last {ev.holdout_weeks} weeks, forecast them from the weeks before, and compared the result
        with what you really sold.
      </p>
      <div className="metric-row">
        <div><span>Average error (MAPE)</span><strong>{ev.mape != null ? `${formatNumber(ev.mape, 1)}%` : "n/a"}</strong></div>
        <div><span>Average error (units)</span><strong>{formatNumber(ev.mae, 1)}</strong></div>
        {modelType === "sarima" && (
          <div><span>4-week average's error</span><strong>{ev.baseline_mape != null ? `${formatNumber(ev.baseline_mape, 1)}%` : "n/a"}</strong></div>
        )}
        {ev.seasonal_naive_mape !== undefined && (
          <div><span>"Repeat last week" error</span><strong>{ev.seasonal_naive_mape != null ? `${formatNumber(ev.seasonal_naive_mape, 1)}%` : "n/a"}</strong></div>
        )}
      </div>
      {ev.mape != null && benchmarks.length > 0 && (
        <p className="small secondary">
          {better.length === 0
            ? `The forecast was at least as accurate as simply ${benchmarks.map((b) => b.name).join(" or ")}.`
            : `Simply ${better.map((b) => b.name).join(" or ")} was more accurate here — treat the forecast with caution.`}
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
    </div>
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
