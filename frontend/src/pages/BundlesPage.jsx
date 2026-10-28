import ResultPage from "../components/ResultPage";
import { Tile } from "../components/Tile";
import { useCurrency } from "../hooks/useCurrency";
import { formatNumber } from "../services/format";

export default function BundlesPage() {
  return (
    <ResultPage
      kind="bundles"
      title="Product bundles"
      intro="Pairs of products that customers often buy in the same order (found with the FP-Growth algorithm), with a suggested bundle offer for each."
    >
      {(data) => <Bundles data={data} />}
    </ResultPage>
  );
}

const pct = (v) => `${formatNumber(v * 100, 0)}%`;

export function Bundles({ data }) {
  const t = data.thresholds;
  return (
    <>
      <div className="tiles">
        <Tile label="Orders analysed" value={formatNumber(data.total_orders)} />
        <Tile label="Orders with 2+ products" value={formatNumber(data.multi_item_orders)}
          note={data.total_orders ? `${pct(data.multi_item_orders / data.total_orders)} of orders` : null} />
        <Tile label="Strong pairs found" value={formatNumber(data.pairs.length)} />
        <Tile label="Assumed margin" value={pct(data.margin_assumption)} note="Set when uploading" />
      </div>

      {data.status !== "ok" && (
        <div className="card stack">
          <h2>{data.status === "insufficient_data" ? "Not enough multi-product orders" : "No strong pairs"}</h2>
          <p className="secondary">{data.message}</p>
          {data.status === "insufficient_data" && (
            <p className="small muted">
              Tip: export your orders with an order ID column, so items bought together share the same ID.
            </p>
          )}
        </div>
      )}
      {data.status === "ok" && data.message && <div className="alert alert-warning">{data.message}</div>}

      {data.pairs.length > 0 && (
        <div className="pair-grid">
          {data.pairs.map((p) => <PairCard key={`${p.sku_a}-${p.sku_b}`} pair={p} margin={data.margin_assumption} />)}
        </div>
      )}

      <p className="small muted">
        A pair is shown only if it was bought together in at least {t.min_orders_together} orders, with lift of at
        least {t.min_lift} and confidence of at least {pct(t.min_confidence)}.
        Lift = how many times more often the two are bought together than if they were unrelated.
      </p>
    </>
  );
}

function PairCard({ pair: p, margin }) {
  const { money } = useCurrency();
  return (
    <section className="card stack">
      <h2>{p.product_a} + {p.product_b}</h2>
      <div className="metric-row">
        <div><span>Bought together</span><strong>{formatNumber(p.orders_together)} orders</strong></div>
        <div><span>Of {p.product_a} buyers</span><strong>{pct(p.confidence)} add it</strong></div>
        <div><span>Lift</span><strong>{formatNumber(p.lift, 2)}×</strong></div>
      </div>
      <div className="table-wrap">
        <table>
          <tbody>
            <tr><td>{p.product_a}</td><td className="num">{money(p.price_a)}</td></tr>
            <tr><td>{p.product_b} ({p.suggested_discount_pct}% off)</td><td className="num">{money(p.price_b * (1 - p.suggested_discount_pct / 100))}</td></tr>
            <tr><td><strong>Suggested bundle price</strong></td><td className="num"><strong>{money(p.bundle_price)}</strong></td></tr>
          </tbody>
        </table>
      </div>
      <p className="small">
        {p.break_even_uplift_pct === null ? (
          <span style={{ color: "var(--negative-deep)", fontWeight: 600 }}>
            At a {pct(margin)} margin this discount loses money on every bundle.
          </span>
        ) : (
          <>Break-even: the bundle must sell <strong>{formatNumber(p.break_even_uplift_pct, 0)}% more</strong> {p.product_b} than you sell now.</>
        )}
      </p>
      <p className="secondary small">{p.plain_explain}</p>
      <details className="tech">
        <summary>Technical details</summary>
        <p>{p.xai}</p>
        <p>Support {formatNumber(p.support * 100, 1)}% · confidence {p.product_b} → {p.product_a}: {p.confidence_reverse === null ? "n/a" : pct(p.confidence_reverse)}</p>
      </details>
    </section>
  );
}
