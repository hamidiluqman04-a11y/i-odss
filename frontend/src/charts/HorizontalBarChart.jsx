import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useChartColors } from "../hooks/useChartColors";

function BarTooltip({ active, payload, formatValue }) {
  if (!active || !payload?.length) return null;
  const item = payload[0];
  return (
    <div className="chart-tooltip">
      <div className="label">{item.payload.label}</div>
      <strong>{formatValue(item.value)}</strong>
    </div>
  );
}

/**
 * Ranked horizontal bars for one measure. All bars share one colour: the
 * categories (products, categories) have no natural order, and bar length
 * already shows size.
 * `data`: [{ label, value }]
 */
export default function HorizontalBarChart({ data, formatValue, formatTick }) {
  const c = useChartColors();
  const height = Math.max(120, data.length * 36 + 36);
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 16, bottom: 4, left: 0 }} barCategoryGap={8}>
        <CartesianGrid stroke={c["chart-grid"]} horizontal={false} />
        <XAxis
          type="number" tickFormatter={formatTick} tick={{ fill: c["chart-axis"], fontSize: 12 }}
          axisLine={{ stroke: c["chart-grid"] }} tickLine={false}
        />
        <YAxis
          type="category" dataKey="label" width={150} tickLine={false} axisLine={false}
          tick={{ fill: c.body, fontSize: 12 }}
          tickFormatter={(v) => (v.length > 22 ? `${v.slice(0, 21)}…` : v)}
        />
        <Tooltip content={<BarTooltip formatValue={formatValue} />} cursor={{ fill: c["chart-grid"], fillOpacity: 0.6 }} />
        <Bar dataKey="value" fill={c["chart-bar"]} radius={[0, 4, 4, 0]} maxBarSize={18} isAnimationActive={false} />
      </BarChart>
    </ResponsiveContainer>
  );
}
