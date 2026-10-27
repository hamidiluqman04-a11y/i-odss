import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import HorizontalBarChart from "../charts/HorizontalBarChart";
import WeeklySalesChart from "../charts/WeeklySalesChart";
import ChartCard from "../components/ChartCard";
import { EmptyState, ErrorState, LoadingState } from "../components/States";
import { useCurrency } from "../hooks/useCurrency";
import { useDatasets } from "../hooks/useDatasets";
import { api } from "../services/api";
import { formatDate, formatMoneyShort, formatNumber } from "../services/format";

export default function DashboardPage() {
  const { current, status: listStatus, error: listError, refresh } = useDatasets();
  const [data, setData] = useState(null);
  const [state, setState] = useState("idle"); // idle | loading | ready | error
  const [error, setError] = useState(null);

  const load = useCallback(async (id) => {
    setState("loading");
    setError(null);
    try {
      setData(await api.getResult(id, "dashboard"));
      setState("ready");
    } catch (err) {
      setError(err);
      setState("error");
    }
  }, []);

  useEffect(() => {
    if (current) load(current.id);
    else setData(null);
  }, [current, load]);

  if (listStatus === "loading") return <LoadingState message="Loading your datasets…" />;
  if (listStatus === "error") return <ErrorState error={listError} onRetry={refresh} />;
  if (!current) {
    return (
      <EmptyState title="No data yet" action={<Link className="btn btn-primary" to="/upload">Upload a CSV file</Link>}>
        Upload your sales export to see revenue, best sellers, forecasts and recommendations.
      </EmptyState>
    );
  }

  return (
    <div className="stack">
      <div className="page-header">
        <div>
          <h1>Dashboard</h1>
          <p className="secondary">
            {current.original_filename} · {formatDate(current.date_start)} – {formatDate(current.date_end)} ·{" "}
            {formatNumber(current.row_count)} rows
          </p>
        </div>
      </div>
      {state === "loading" && !data && <LoadingState message="Loading results…" />}
      {state === "error" && <ErrorState error={error} onRetry={() => load(current.id)} />}
      {data && (
        <div className="stack" style={{ opacity: state === "loading" ? 0.5 : 1 }}>
          <Dashboard data={data} />
        </div>
      )}
    </div>
  );
}

export function Dashboard({ data }) {
  const { money, symbol } = useCurrency();
  const m = data.metrics;
  const partialDays = m.days_of_data % 7;

  const top = data.top_products.map((p) => ({ label: p.name, sku: p.sku, value: p.revenue }));
  const categories = [...data.categories]
    .sort((a, b) => b.revenue - a.revenue)
    .map((c) => ({ label: c.category, value: c.revenue, units: c.units }));
  const regions = [...data.regions].sort((a, b) => b.revenue - a.revenue);
  const shortMoney = (v) => formatMoneyShort(v, symbol);

  return (
    <>
      <div className="tiles">
        <Tile label="Revenue" value={money(m.revenue)} />
        <Tile label="Orders" value={formatNumber(m.orders)} />
        <Tile label="Units sold" value={formatNumber(m.units)} />
        <Tile label="Average order value" value={money(m.aov)} />
        <Tile label="Products (SKUs)" value={formatNumber(m.skus_count)} />
        <Tile label="Days of data" value={formatNumber(m.days_of_data)} />
        <AtRiskTile value={m.at_risk} />
      </div>

      <ChartCard
        title="Units sold per week"
        subtitle="Week 1 starts on the first date in your file"
        note={partialDays ? `The last week only covers ${partialDays} day(s), so it looks lower than a full week.` : null}
        columns={[{ key: "week", label: "Week" }, { key: "units", label: "Units sold", numeric: true, format: formatNumber }]}
        rows={data.weekly_sales}
      >
        <WeeklySalesChart data={data.weekly_sales} />
      </ChartCard>

      <div className="grid-2">
        <ChartCard
          title="Top products by revenue"
          subtitle={`Best ${top.length} of ${formatNumber(m.skus_count)} products`}
          columns={[
            { key: "label", label: "Product" }, { key: "sku", label: "SKU" },
            { key: "value", label: "Revenue", numeric: true, format: money },
          ]}
          rows={top}
        >
          <HorizontalBarChart data={top} formatValue={money} formatTick={shortMoney} />
        </ChartCard>
        <ChartCard
          title="Revenue by category"
          columns={[
            { key: "label", label: "Category" }, { key: "units", label: "Units", numeric: true, format: formatNumber },
            { key: "value", label: "Revenue", numeric: true, format: money },
          ]}
          rows={categories}
        >
          <HorizontalBarChart data={categories} formatValue={money} formatTick={shortMoney} />
        </ChartCard>
      </div>

      <section className="card">
        <div className="card-header"><h2>Revenue by region</h2></div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>Region</th><th className="num">Orders</th><th className="num">Revenue</th><th className="num">Share</th></tr>
            </thead>
            <tbody>
              {regions.map((r) => (
                <tr key={r.region}>
                  <td>{r.region}</td>
                  <td className="num">{formatNumber(r.orders)}</td>
                  <td className="num">{money(r.revenue)}</td>
                  <td className="num">{formatNumber((r.revenue / m.revenue) * 100, 1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}

function Tile({ label, value, note }) {
  return (
    <div className="card tile">
      <div className="tile-label">{label}</div>
      <div className="tile-value">{value}</div>
      {note && <div className="tile-note">{note}</div>}
    </div>
  );
}

function AtRiskTile({ value }) {
  if (value === null || value === undefined) {
    return <Tile label="Products to restock" value="Unknown" note="Your file has no stock column" />;
  }
  const color = value > 0 ? "var(--critical)" : "var(--good)";
  return (
    <div className="card tile">
      <div className="tile-label">Products to restock</div>
      <div className="tile-value">{formatNumber(value)}</div>
      <span className="status-pill" style={{ color: value > 0 ? "var(--critical-ink)" : "var(--good-ink)" }}>
        <span className="dot" style={{ background: color }} aria-hidden="true" />
        {value > 0 ? "Below reorder point" : "All above reorder point"}
      </span>
    </div>
  );
}
