import { Fragment, useState } from "react";
import { Answer, Method } from "../components/Answer";
import ResultPage from "../components/ResultPage";
import { StatusPill, STATUS_LABELS, Tile } from "../components/Tile";
import { formatNumber } from "../services/format";

export default function InventoryPage() {
  return (
    <ResultPage
      kind="inventory"
      title="Inventory"
      intro="Which products to reorder, and when. Reorder points come from your daily sales; stock levels come only from your file."
    >
      {(data) => <Inventory data={data} />}
    </ResultPage>
  );
}

const FILTERS = ["all", "critical", "warning", "ok", "unknown"];

export function Inventory({ data }) {
  const [filter, setFilter] = useState("all");
  const [open, setOpen] = useState(null);
  const counts = Object.fromEntries(FILTERS.map((f) => [f, f === "all" ? data.items.length : data.items.filter((i) => i.status === f).length]));
  const visible = data.items.filter((i) => filter === "all" || i.status === filter);

  const urgent = counts.critical > 0 ? "critical" : counts.warning > 0 ? "warning" : null;

  return (
    <>
      {data.stock_data_available && (
        <Answer
          headline={counts.critical > 0
            ? `Reorder ${counts.critical === 1 ? "1 product" : `${formatNumber(counts.critical)} products`} now`
            : counts.warning > 0
              ? `Order ${counts.warning === 1 ? "1 product" : `${formatNumber(counts.warning)} products`} soon`
              : "Every product has enough stock for now"}
        >
          {urgent
            ? <>Use the <strong>{STATUS_LABELS[urgent]}</strong> filter below to see the list with a suggested order quantity for each.</>
            : "All stock levels in your file are above their reorder points. Check again after your next upload."}
        </Answer>
      )}

      <div className="tiles">
        <Tile label="Products" value={formatNumber(data.items.length)} />
        <Tile label="Reorder now" value={data.stock_data_available ? formatNumber(counts.critical) : "Unknown"}
          note={data.stock_data_available ? "Stock below reorder point" : "No stock column in file"} />
        <Tile label="Order soon" value={data.stock_data_available ? formatNumber(counts.warning) : "Unknown"}
          note={data.stock_data_available ? "Within 30% of reorder point" : "No stock column in file"} />
      </div>

      {!data.stock_data_available && (
        <div className="alert alert-info">
          <strong>Your file has no stock levels, so I-ODSS cannot tell what needs restocking.</strong>
          <p className="small" style={{ marginTop: 4 }}>
            The reorder points below are still calculated from your sales. To get restock alerts, add a column such
            as <em>Stock</em> or <em>Stock on hand</em> with the quantity you had on each date, and upload again.
          </p>
        </div>
      )}

      <section className="card">
        <div className="card-header">
          <h2>Reorder points</h2>
          <span className="spacer" />
          <div className="pill-filters" role="group" aria-label="Filter by status">
            {FILTERS.filter((f) => f === "all" || counts[f] > 0).map((f) => (
              <button key={f} type="button" aria-pressed={filter === f} onClick={() => setFilter(f)}>
                {f === "all" ? "All" : STATUS_LABELS[f]} ({counts[f]})
              </button>
            ))}
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Product</th>
                <th>Status</th>
                <th className="num">Stock <span className="th-note">(your file)</span></th>
                <th className="num">Reorder point <span className="th-note">(calculated)</span></th>
                <th className="num">Sold per day</th>
                <th className="num">Lead time</th>
                <th className="num">Suggested order</th>
                <th className="num">Days left</th>
                <th><span className="visually-hidden">Details</span></th>
              </tr>
            </thead>
            <tbody>
              {visible.map((i) => (
                <Fragment key={i.sku}>
                  <tr className={open === i.sku ? "row-open" : undefined}>
                    <td>{i.product}<span className="cell-sub">{i.sku} · {i.category}</span></td>
                    <td><StatusPill status={i.status} /></td>
                    <td className="num">{i.stock === null ? "Not in file" : formatNumber(i.stock)}</td>
                    <td className="num">{formatNumber(i.rop, 1)}</td>
                    <td className="num">{formatNumber(i.velocity, 2)}</td>
                    <td className="num">{i.lead} days</td>
                    <td className="num">{i.reorder_qty === null ? "—" : formatNumber(i.reorder_qty)}</td>
                    <td className="num">{i.days_until_stockout === null ? "—" : formatNumber(i.days_until_stockout, 1)}</td>
                    <td>
                      <button className="link-button small" onClick={() => setOpen(open === i.sku ? null : i.sku)}
                        aria-expanded={open === i.sku}>
                        {open === i.sku ? "Hide" : "Why?"}
                      </button>
                    </td>
                  </tr>
                  {open === i.sku && (
                    <tr className="detail-row">
                      <td colSpan={9}>
                        <div className="stack" style={{ gap: "var(--space-sm)" }}>
                          <p>{i.plain_explain}</p>
                          <p className="small secondary">
                            Safety stock {formatNumber(i.safety_stock, 1)} units · {formatNumber(i.total_sold)} sold in total ·
                            average rating {i.avg_rating === null ? "not in file" : formatNumber(i.avg_rating, 1)} ·
                            return rate {i.return_rate === null ? "not in file" : `${formatNumber(i.return_rate, 1)}%`}
                          </p>
                          <details className="tech"><summary>Technical details</summary><p>{i.xai}</p></details>
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>

      </section>

      <Method hint="Reorder point = daily demand × lead time + safety stock">
        <p className="small secondary">
          Reorder point = daily sales × supplier lead time + safety stock. Lead times are typical defaults for each
          category, not your real supplier times. Stock levels and restock status come only from the stock column in
          your file; I-ODSS never estimates stock on hand. Open <strong>Why?</strong> on a product for its safety stock,
          ratings and returns.
        </p>
      </Method>
    </>
  );
}
