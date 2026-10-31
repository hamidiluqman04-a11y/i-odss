import { Fragment, useState } from "react";
import { Answer, Method } from "../components/Answer";
import ResultPage from "../components/ResultPage";
import { ErrorMessage } from "../components/States";
import { Tile } from "../components/Tile";
import { useCurrency } from "../hooks/useCurrency";
import { api, ApiError } from "../services/api";
import { formatNumber } from "../services/format";

export default function PricingPage() {
  return (
    <ResultPage
      kind="pricing"
      title="Pricing"
      intro="How sales of each product reacted when its price changed, measured from your own data — plus a simulator to check a promotion before you run it."
    >
      {(data, dataset) => <Pricing data={data} datasetId={dataset.id} />}
    </ResultPage>
  );
}

/** Short label for what I-ODSS suggests, including why there is no advice. */
export function suggestionLabel(item) {
  switch (item.recommendation) {
    case "test_increase": return `Test a ${item.test_change_pct}% price increase`;
    case "test_decrease": return `Test a ${Math.abs(item.test_change_pct)}% price cut`;
    case "hold": return "Keep current price";
    default:
      if (item.status === "insufficient_price_variation") return "No advice — price never changed";
      if (item.status === "insufficient_data") return "No advice — too few weeks of sales";
      if (item.reliability === "weak") return "No advice — no clear pattern";
      return "No advice — unusual pattern";
  }
}

const pct = (v) => `${formatNumber(v * 100, 0)}%`;

export function Pricing({ data, datasetId }) {
  const { money } = useCurrency();
  const [open, setOpen] = useState(null);
  const total = data.items.length;
  const advised = data.items.filter((i) => ["test_increase", "test_decrease", "hold"].includes(i.recommendation)).length;

  const tests = data.items.filter((i) => i.recommendation === "test_increase" || i.recommendation === "test_decrease");

  return (
    <>
      {data.estimated_count > 0 && (
        <Answer
          headline={tests.length > 0
            ? `${formatNumber(tests.length)} of ${formatNumber(total)} products have a price test worth trying`
            : "No price change is clearly worth testing yet"}
        >
          {tests.length > 0
            ? <>Each test is a small change chosen by estimated profit. Open <strong>Why?</strong> next to a product to see what is expected to happen to its weekly revenue and profit.</>
            : "Your sales did not show a clear, reliable reaction to price. Keep current prices, or use the simulator below to check a promotion."}
        </Answer>
      )}

      {data.estimated_count === 0 && (
        <div className="alert alert-info">
          <strong>Your prices did not change enough to measure price sensitivity.</strong>
          <p className="small" style={{ marginTop: 4 }}>
            I-ODSS only estimates PED when a product was sold at noticeably different prices (at least 3% apart)
            across at least {data.min_weeks_with_sales} weeks. It does not guess. To collect this evidence, try a
            small planned price change for a few weeks and upload the new data. The promotion simulator below still
            shows the exact break-even point for any discount.
          </p>
        </div>
      )}

      <section className="card">
        <div className="card-header">
          <div>
            <h2>Price advice by product</h2>
            <p className="small secondary">Price sensitivity (PED) −1.5 means: when the price was 1% higher, about 1.5% fewer units were sold.</p>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Product</th><th>Suggestion</th><th className="num">Current price</th>
                <th className="num">Price range seen</th><th className="num">PED</th><th><span className="visually-hidden">Details</span></th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((item) => (
                <Fragment key={item.sku}>
                  <tr className={open === item.sku ? "row-open" : undefined}>
                    <td>{item.product}<span className="cell-sub">{item.sku} · {item.category}</span></td>
                    <td><strong>{suggestionLabel(item)}</strong></td>
                    <td className="num">{money(item.current_price)}</td>
                    <td className="num">{item.price_min === item.price_max ? money(item.price_min) : `${money(item.price_min)} – ${money(item.price_max)}`}</td>
                    <td className="num">
                      {item.ped === null ? "—" : formatNumber(item.ped, 2)}
                      {item.reliability === "weak" && <span className="cell-sub">unreliable</span>}
                    </td>
                    <td>
                      <button className="link-button small" onClick={() => setOpen(open === item.sku ? null : item.sku)}
                        aria-expanded={open === item.sku}>
                        {open === item.sku ? "Hide" : "Why?"}
                      </button>
                    </td>
                  </tr>
                  {open === item.sku && (
                    <tr className="detail-row">
                      <td colSpan={6}><PricingDetail item={item} /></td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <PromoSimulator items={data.items} datasetId={datasetId} defaultMargin={data.margin_assumption} />

      <Method hint="Price elasticity (PED) from a weekly log-log regression per product">
        <div className="tiles">
          <Tile label="Products" value={formatNumber(total)} />
          <Tile label="PED measured" value={`${formatNumber(data.estimated_count)} of ${formatNumber(total)}`}
            note="Needs price changes over time" />
          <Tile label="With price advice" value={formatNumber(advised)} note="Clear, reliable pattern only" />
          <Tile label="Assumed margin" value={pct(data.margin_assumption)} note="Set when uploading" />
        </div>
        <p className="small secondary">
          PED is estimated only for products sold at prices at least 3% apart across at least {data.min_weeks_with_sales} weeks
          with sales. Advice is limited to a small price test and is given only when the pattern is statistically clear.
          Open <strong>Why?</strong> on a product for its confidence range, p-value and R².
        </p>
      </Method>
    </>
  );
}

function PricingDetail({ item }) {
  const { money } = useCurrency();
  const p = item.projection;
  return (
    <div className="stack" style={{ gap: "var(--space-md)" }}>
      <p>{item.plain_explain}</p>
      {item.ped !== null && (
        <p className="small secondary">
          Likely PED range {formatNumber(item.ped_ci_low, 2)} to {formatNumber(item.ped_ci_high, 2)} · based on{" "}
          {item.weeks_with_sales} weeks · p-value {formatNumber(item.p_value, 3)} · R² {formatNumber(item.r_squared, 2)}
        </p>
      )}
      {p && item.test_change_pct !== 0 && (
        <div className="metric-row">
          <div><span>Weekly revenue</span><strong>{money(p.weekly_revenue_now)} → {money(p.weekly_revenue_new)}</strong></div>
          <div><span>Weekly profit (est.)</span><strong>{money(p.weekly_profit_now)} → {money(p.weekly_profit_new)}</strong></div>
          <div><span>Units per week</span><strong>{formatNumber(p.weekly_units_now, 1)} → {formatNumber(p.weekly_units_new, 1)}</strong></div>
        </div>
      )}
      <details className="tech"><summary>Technical details</summary><p>{item.xai}</p></details>
    </div>
  );
}

function PromoSimulator({ items, datasetId, defaultMargin }) {
  const { money } = useCurrency();
  const [sku, setSku] = useState(items[0]?.sku ?? "");
  const [discount, setDiscount] = useState("10");
  const [margin, setMargin] = useState(String(Math.round(defaultMargin * 100)));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const run = async (e) => {
    e.preventDefault();
    const d = Number(discount);
    const m = Number(margin);
    if (!(d >= 1 && d <= 80)) return setError(new ApiError(0, "client_check", "Discount must be between 1% and 80%."));
    if (!(m >= 1 && m <= 99)) return setError(new ApiError(0, "client_check", "Margin must be between 1% and 99%."));
    setBusy(true);
    setError(null);
    try {
      setResult(await api.simulatePromo(datasetId, { sku, discount_pct: d, margin: m / 100 }));
    } catch (err) {
      setError(err);
      setResult(null);
    } finally {
      setBusy(false);
    }
  };

  const p = result?.projection;
  return (
    <section className="card stack">
      <div>
        <h2>Promotion simulator</h2>
        <p className="small secondary">Check what a discount on one product would do to your weekly profit, before you run it.</p>
      </div>
      <form className="sim-form" onSubmit={run} noValidate>
        <div className="field field-wide">
          <label htmlFor="promo-sku">Product</label>
          <select id="promo-sku" className="select" value={sku} onChange={(e) => setSku(e.target.value)}>
            {items.map((i) => <option key={i.sku} value={i.sku}>{i.product}</option>)}
          </select>
        </div>
        <div className="field">
          <label htmlFor="promo-discount">Discount (%)</label>
          <input id="promo-discount" className="input" type="number" min="1" max="80" step="1" value={discount}
            onChange={(e) => setDiscount(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="promo-margin">Gross margin (%)</label>
          <input id="promo-margin" className="input" type="number" min="1" max="99" step="1" value={margin}
            onChange={(e) => setMargin(e.target.value)} />
        </div>
        <button className="btn btn-primary" type="submit" disabled={busy || !sku}>{busy ? "Calculating…" : "Simulate"}</button>
      </form>
      <ErrorMessage error={error} title="Could not simulate" />
      {result && (
        <div className="stack" aria-live="polite" style={{ gap: "var(--space-md)" }}>
          <div className="metric-row">
            <div><span>Price</span><strong>{money(result.original_price)} → {money(result.discounted_price)}</strong></div>
            <div>
              <span>Break-even sales increase</span>
              <strong>{result.break_even_volume_increase_pct === null ? "Not possible" : `+${formatNumber(result.break_even_volume_increase_pct, 1)}%`}</strong>
            </div>
            <div>
              <span>Expected sales increase</span>
              <strong>{result.volume_change_pct === null ? "Unknown" : `+${formatNumber(result.volume_change_pct, 1)}%`}</strong>
            </div>
            {p && (
              <div><span>Weekly profit (est.)</span><strong>{money(p.weekly_profit_now)} → {money(p.weekly_profit_new)}</strong></div>
            )}
          </div>
          <div className="explain"><strong>Result: </strong>{result.plain_explain}</div>
        </div>
      )}
    </section>
  );
}
