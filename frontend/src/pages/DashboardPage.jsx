import { Link } from "react-router-dom";
import HorizontalBarChart from "../charts/HorizontalBarChart";
import WeeklySalesChart from "../charts/WeeklySalesChart";
import ChartCard from "../components/ChartCard";
import Icon from "../components/Icons";
import ResultPage from "../components/ResultPage";
import { StatusPill, Tile } from "../components/Tile";
import { useCurrency } from "../hooks/useCurrency";
import { useResult } from "../hooks/useResult";
import { formatMoneyShort, formatNumber } from "../services/format";
import { suggestionLabel } from "./PricingPage";

export default function DashboardPage() {
  return (
    <ResultPage
      kind="dashboard"
      title="Overview"
      intro="What your sales export says you should look at first, followed by the totals behind it."
      before={<NextSteps />}
    >
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
      <div className="stack">
        <div className="row" style={{ alignItems: "baseline" }}>
          <h2 className="section-title">Your sales at a glance</h2>
          <p className="dataset-facts">
            {formatNumber(m.units)} units sold · {formatNumber(m.skus_count)} products · {formatNumber(m.days_of_data)} days of data
          </p>
        </div>
        <div className="tiles">
          <Tile label="Revenue" value={money(m.revenue)} />
          <Tile label="Orders" value={formatNumber(m.orders)} />
          <Tile label="Average order value" value={money(m.aov)} />
          <AtRiskTile value={m.at_risk} />
        </div>
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
          <HorizontalBarChart data={top} formatValue={money} formatTick={shortMoney} label="Bar chart of top products by revenue" />
        </ChartCard>
        <ChartCard
          title="Revenue by category"
          columns={[
            { key: "label", label: "Category" }, { key: "units", label: "Units", numeric: true, format: formatNumber },
            { key: "value", label: "Revenue", numeric: true, format: money },
          ]}
          rows={categories}
        >
          <HorizontalBarChart data={categories} formatValue={money} formatTick={shortMoney} label="Bar chart of revenue by category" />
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
  return (
    <Tile label="Products to restock" value={formatNumber(value)}>
      <div className="tile-pill">
        <StatusPill status={value > 0 ? "critical" : "ok"} label={value > 0 ? "Below reorder point" : "All above reorder point"} />
      </div>
    </Tile>
  );
}

// ── What to do next ─────────────────────────────────────────────────────
// Each card reads one saved analysis and states its headline result. When the
// data cannot support a result, the card says what is missing instead.

const TREND_TEXT = { Upward: "rising", Downward: "falling", Stable: "about the same", Unknown: "unclear" };

function plural(n, one, many) {
  return `${formatNumber(n)} ${n === 1 ? one : many}`;
}

function forecastStep(d) {
  if (d.status === "insufficient_data") {
    return { tone: "gap", tag: "Needs more data", headline: "Not enough history to forecast yet", detail: "Upload a longer sales period to get a 4-week forecast." };
  }
  const s = d.summary;
  const change = s.forecast_change_pct;
  return {
    tone: "info",
    tag: "Plan ahead",
    headline: `About ${formatNumber(s.forecast_avg_weekly, 0)} units a week coming`,
    detail: change === null
      ? `Expected over the next ${d.horizon_weeks} weeks, all products together.`
      : `${change > 0 ? "+" : ""}${formatNumber(change, 1)}% against the last 4 weeks — demand is ${TREND_TEXT[s.trend] ?? "unclear"}.`,
  };
}

function bundlesStep(d) {
  if (d.status === "ok" && d.pairs.length > 0) {
    const p = d.pairs[0];
    return {
      tone: "act",
      tag: "Try this",
      headline: `Bundle ${p.product_a} + ${p.product_b}`,
      detail: `Bought together in ${plural(p.orders_together, "order", "orders")}. ${d.pairs.length > 1 ? `${plural(d.pairs.length - 1, "more pair", "more pairs")} found.` : ""}`,
    };
  }
  if (d.status === "insufficient_data") {
    return { tone: "gap", tag: "Needs more data", headline: "Too few orders with 2+ products", detail: "Bundles need an order ID column so items bought together can be matched." };
  }
  return { tone: "info", tag: "Nothing to do", headline: "No strong product pairs yet", detail: "No two products are bought together often enough to suggest a bundle." };
}

function pricingStep(d) {
  const tests = d.items.filter((i) => i.recommendation === "test_increase" || i.recommendation === "test_decrease");
  if (tests.length > 0) {
    const first = tests[0];
    return {
      tone: "act",
      tag: "Try this",
      headline: `${suggestionLabel(first)} on ${first.product}`,
      detail: tests.length > 1 ? `${plural(tests.length - 1, "other product has", "other products have")} a price test to try.` : "A small, reversible test — check the estimated profit first.",
    };
  }
  if (d.estimated_count === 0) {
    return { tone: "gap", tag: "Needs more data", headline: "Prices never changed enough to measure", detail: "Price advice needs sales at different prices. The promotion simulator still works." };
  }
  return { tone: "info", tag: "Nothing to do", headline: "Keep your current prices", detail: "No product showed a clear reason to test a different price." };
}

function inventoryStep(d) {
  if (!d.stock_data_available) {
    return { tone: "gap", tag: "Needs more data", headline: "Add stock levels to get restock alerts", detail: "Reorder points are ready; a stock column in your file shows what to reorder." };
  }
  const critical = d.items.filter((i) => i.status === "critical").length;
  const warning = d.items.filter((i) => i.status === "warning").length;
  if (critical > 0) {
    return {
      tone: "act",
      tag: "Act now",
      headline: `Reorder ${plural(critical, "product", "products")} now`,
      detail: warning > 0 ? `${plural(warning, "more needs", "more need")} ordering soon.` : "Stock is below the reorder point.",
    };
  }
  if (warning > 0) {
    return { tone: "act", tag: "Act soon", headline: `Order ${plural(warning, "product", "products")} soon`, detail: "Stock is close to the reorder point." };
  }
  return { tone: "info", tag: "Nothing to do", headline: "Stock is healthy", detail: "Every product is above its reorder point." };
}

const STEPS = [
  { kind: "inventory", area: "Inventory", icon: "inventory", to: "/inventory", link: "See reorder list", build: inventoryStep },
  { kind: "pricing", area: "Pricing", icon: "pricing", to: "/pricing", link: "See price advice", build: pricingStep },
  { kind: "bundles", area: "Product bundles", icon: "bundles", to: "/bundles", link: "See bundle offers", build: bundlesStep },
  { kind: "forecast", area: "Demand forecast", icon: "forecast", to: "/forecast", link: "See forecast", build: forecastStep },
];

function NextSteps() {
  return (
    <section className="next-steps" aria-labelledby="next-steps-title">
      <div className="next-steps-head">
        <h2 id="next-steps-title">What to do next</h2>
        <p className="small secondary">Estimates to test, not guarantees.</p>
      </div>
      <div className="next-grid">
        {STEPS.map((s) => <NextCard key={s.kind} step={s} />)}
      </div>
    </section>
  );
}

function NextCard({ step }) {
  const { status, data } = useResult(step.kind);
  let content;
  if (status === "error") {
    content = { tone: "info", tag: "Not loaded", headline: "This result could not be loaded", detail: "Open the page to try again." };
  } else if (!data) {
    return (
      <div className="next-card" aria-busy="true">
        <span className="next-area"><Icon name={step.icon} />{step.area}</span>
        <span className="skeleton wide" />
        <span className="skeleton" />
        <span className="visually-hidden">Loading {step.area}…</span>
      </div>
    );
  } else {
    content = step.build(data);
  }
  return (
    <Link className={`next-card tone-${content.tone}`} to={step.to}>
      <span className="next-area"><Icon name={step.icon} />{step.area}</span>
      <span className="next-tag">{content.tag}</span>
      <span className="next-headline">{content.headline}</span>
      <span className="next-detail">{content.detail}</span>
      <span className="next-link">{step.link}<Icon name="arrow" /></span>
    </Link>
  );
}
