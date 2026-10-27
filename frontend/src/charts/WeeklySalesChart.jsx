import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useChartColors } from "../hooks/useChartColors";
import { formatNumber } from "../services/format";

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
    <ResponsiveContainer width="100%" height={260}>
      <AreaChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: 0 }}>
        <defs>
          <linearGradient id="weekly-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={c["series-1"]} stopOpacity={0.18} />
            <stop offset="100%" stopColor={c["series-1"]} stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke={c.grid} vertical={false} />
        <XAxis dataKey="week" tick={{ fill: c["text-muted"], fontSize: 12 }} axisLine={{ stroke: c.axis }} tickLine={false} />
        <YAxis
          tick={{ fill: c["text-muted"], fontSize: 12 }} axisLine={false} tickLine={false} width={44}
          allowDecimals={false}
        />
        <Tooltip content={<WeekTooltip />} cursor={{ stroke: c.axis, strokeWidth: 1 }} />
        <Area
          type="linear" dataKey="units" stroke={c["series-1"]} strokeWidth={2}
          fill="url(#weekly-fill)" activeDot={{ r: 5, stroke: c.surface, strokeWidth: 2 }} isAnimationActive={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
