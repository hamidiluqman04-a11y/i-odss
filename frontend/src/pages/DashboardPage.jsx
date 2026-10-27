import HorizontalBarChart from "../charts/HorizontalBarChart";
import WeeklySalesChart from "../charts/WeeklySalesChart";
import ChartCard from "../components/ChartCard";
import ResultPage from "../components/ResultPage";
import { Tile } from "../components/Tile";
import { useCurrency } from "../hooks/useCurrency";
import { formatMoneyShort, formatNumber } from "../services/format";

export default function DashboardPage() {
  return (
    <ResultPage kind="dashboard" title="Dashboard">
      {(data) => <Dashboard data={data} />}
    </ResultPage>
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
