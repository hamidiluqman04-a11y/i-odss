import { Area, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useChartColors } from "../hooks/useChartColors";
import { formatNumber } from "../services/format";

/**
 * Prepares the API series for the chart. The last real week is copied into the
 * forecast line so the dashed forecast starts where the history ends.
 */
export function toChartData(series) {
  const lastActual = series.findLastIndex((p) => p.actual !== null);
  return series.map((p, i) => ({
    label: p.label,
    week_start: p.week_start,
    actual: p.actual,
    forecast: i === lastActual ? p.actual : p.forecast,
    range: p.forecast !== null ? [p.lower, p.upper] : i === lastActual ? [p.actual, p.actual] : null,
    lower: p.lower,
    upper: p.upper,
    isForecast: p.forecast !== null,
  }));
}

function ForecastTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div className="chart-tooltip">
      <div className="label">{p.label} · week of {p.week_start}</div>
      {p.isForecast ? (
        <>
          <strong>Forecast: {formatNumber(p.forecast, 1)} units</strong>
          <div className="label">Likely range {formatNumber(p.lower, 1)} – {formatNumber(p.upper, 1)}</div>
        </>
      ) : (
        <strong>Actual: {formatNumber(p.actual)} units</strong>
      )}
    </div>
  );
}

/** Actual weekly units (solid) followed by the forecast (dashed) and its 90% range (shaded). */
export default function ForecastChart({ series }) {
  const c = useChartColors();
  const data = toChartData(series);
  return (
    <>
      <div className="chart-legend" aria-hidden="true">
        <span>
          <svg width="24" height="8"><line x1="0" y1="4" x2="24" y2="4" stroke={c["chart-actual"]} strokeWidth="2" /></svg>
          Actual units sold
        </span>
        <span>
          <svg width="24" height="8"><line x1="0" y1="4" x2="24" y2="4" stroke={c["chart-forecast"]} strokeWidth="2" strokeDasharray="6 4" /></svg>
          Forecast
        </span>
        <span>
          <svg width="16" height="12"><rect width="16" height="12" rx="3" fill={c["chart-band"]} /></svg>
          Likely range (90%)
        </span>
      </div>
      <ResponsiveContainer width="100%" height={300}>
        <ComposedChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: 0 }}>
          <CartesianGrid stroke={c["chart-grid"]} vertical={false} />
          <XAxis dataKey="label" tick={{ fill: c["chart-axis"], fontSize: 12 }} axisLine={{ stroke: c["chart-grid"] }} tickLine={false} />
          <YAxis tick={{ fill: c["chart-axis"], fontSize: 12 }} axisLine={false} tickLine={false} width={44} domain={[0, "auto"]} />
          <Tooltip content={<ForecastTooltip />} cursor={{ stroke: c["chart-axis"], strokeWidth: 1 }} />
          <Area dataKey="range" stroke="none" fill={c["chart-band"]} fillOpacity={1} isAnimationActive={false} connectNulls={false} />
          <Line dataKey="actual" stroke={c["chart-actual"]} strokeWidth={2} dot={false}
            activeDot={{ r: 5, stroke: c.canvas, strokeWidth: 2, fill: c["chart-actual"] }} isAnimationActive={false} connectNulls={false} />
          <Line dataKey="forecast" stroke={c["chart-forecast"]} strokeWidth={2} strokeDasharray="6 4" dot={false}
            activeDot={{ r: 5, stroke: c.canvas, strokeWidth: 2, fill: c["chart-forecast"] }} isAnimationActive={false} connectNulls={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </>
  );
}
