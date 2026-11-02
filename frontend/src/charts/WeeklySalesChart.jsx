import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useChartColors } from "../hooks/useChartColors";
import { formatNumber } from "../services/format";
import { weeklySalesSummary } from "./summaries";

function WeekTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tooltip">
      <div className="label">{label}</div>
      <strong>{formatNumber(payload[0].value)} units</strong>
    </div>
  );
}

/** Units sold per week: one series, so no legend — the card title names it. */
export default function WeeklySalesChart({ data }) {
  const c = useChartColors();
  return (
    <div role="img" aria-label={weeklySalesSummary(data)}>
    <ResponsiveContainer width="100%" height={260}>
      <AreaChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: 0 }}>
        <CartesianGrid stroke={c["chart-grid"]} vertical={false} />
        <XAxis dataKey="week" tick={{ fill: c["chart-axis"], fontSize: 12 }} axisLine={{ stroke: c["chart-grid"] }} tickLine={false} />
        <YAxis
          tick={{ fill: c["chart-axis"], fontSize: 12 }} axisLine={false} tickLine={false} width={44}
          allowDecimals={false}
        />
        <Tooltip content={<WeekTooltip />} cursor={{ stroke: c["chart-axis"], strokeWidth: 1 }} />
        <Area
          type="linear" dataKey="units" stroke={c["chart-actual"]} strokeWidth={2}
          fill={c["chart-band"]} fillOpacity={1}
          activeDot={{ r: 5, stroke: c.canvas, strokeWidth: 2, fill: c["chart-actual"] }} isAnimationActive={false}
        />
      </AreaChart>
    </ResponsiveContainer>
    </div>
  );
}
