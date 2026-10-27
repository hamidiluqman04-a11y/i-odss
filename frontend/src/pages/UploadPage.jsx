import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ErrorMessage } from "../components/States";
import { useDatasets } from "../hooks/useDatasets";
import { api, ApiError } from "../services/api";
import { formatDate, formatDateTime, formatNumber } from "../services/format";

export const MAX_UPLOAD_MB = 10; // same limit as the backend

const SAMPLE_FILES = [
  { file: "data_bundling_test.csv", note: "120 orders, many with several products (best for bundles)" },
  { file: "data_electronics.csv", note: "150 single-item orders, 11 weeks" },
  { file: "data_fashion.csv", note: "100 single-item orders, 7 weeks" },
  { file: "data_beauty.csv", note: "100 single-item orders, 7 weeks" },
];

const FIELD_LABELS = {
  order_id: "Order ID", sku: "SKU", product_name: "Product name", date: "Date", qty: "Quantity",
  price: "Unit price", category: "Category", region: "Region", rating: "Rating", returns: "Returns", stock: "Stock",
};

/** Checks we can do before sending anything to the server. Returns an error message or null. */
export function checkFile(file) {
  if (!file) return "Choose a CSV file first.";
  if (!file.name.toLowerCase().endsWith(".csv")) return `"${file.name}" is not a CSV file. Export your orders as .csv and try again.`;
  if (file.size === 0) return "This file is empty.";
  if (file.size > MAX_UPLOAD_MB * 1024 * 1024) return `This file is larger than ${MAX_UPLOAD_MB} MB.`;
  return null;
}

export default function UploadPage() {
  const { datasets, added, remove, select } = useDatasets();
  const navigate = useNavigate();
  const inputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [marginPct, setMarginPct] = useState("40");
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [deleting, setDeleting] = useState(null);
  const [deleteError, setDeleteError] = useState(null);

  const choose = (chosen) => {
    setFile(chosen ?? null);
    setResult(null);
    setError(null);
  };

  const submit = async (e) => {
    e.preventDefault();
    const problem = checkFile(file);
    const margin = Number(marginPct) / 100;
    if (problem) return setError(new ApiError(0, "client_check", problem));
    if (!(margin > 0 && margin < 1)) return setError(new ApiError(0, "client_check", "Gross margin must be between 1% and 99%."));

    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const response = await api.uploadDataset(file, { margin });
      added(response.dataset);
      setResult(response);
      setFile(null);
      if (inputRef.current) inputRef.current.value = "";
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async (dataset) => {
    if (!window.confirm(`Delete the results for "${dataset.original_filename}"? This cannot be undone.`)) return;
    setDeleting(dataset.id);
    setDeleteError(null);
    try {
      await remove(dataset.id);
      if (result?.dataset.id === dataset.id) setResult(null);
    } catch (err) {
      setDeleteError(err);
    } finally {
      setDeleting(null);
    }
  };

  const open = (id) => {
    select(id);
    navigate("/");
  };

  return (
    <div className="stack">
      <div className="page-header">
        <div>
          <h1>Upload sales data</h1>
          <p className="secondary">
            Export your orders from Shopee, Lazada, TikTok Shop or any shop as a CSV file. I-ODSS checks every row,
            then runs all analyses at once.
          </p>
        </div>
      </div>

      <div className="upload-grid">
        <form className="card stack" onSubmit={submit}>
          <div
            className={`dropzone${dragging ? " dragging" : ""}`}
            role="button"
            tabIndex={0}
            aria-label="Choose a CSV file"
            onClick={() => inputRef.current?.click()}
            onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), inputRef.current?.click())}
            onDragOver={(e) => (e.preventDefault(), setDragging(true))}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragging(false);
              choose(e.dataTransfer.files[0]);
            }}
          >
            <p><strong>{file ? file.name : "Drop your CSV file here, or click to choose"}</strong></p>
            <p className="muted small">
              {file ? `${formatNumber(file.size / 1024, 1)} KB` : `CSV only, up to ${MAX_UPLOAD_MB} MB`}
            </p>
          </div>
          <input
            ref={inputRef}
            type="file"
            accept=".csv,text/csv"
            className="visually-hidden"
            data-testid="file-input"
            onChange={(e) => choose(e.target.files[0])}
          />

          <div className="field">
            <label htmlFor="margin">Your typical gross margin (%)</label>
            <input
              id="margin" className="input" type="number" min="1" max="99" step="1"
              value={marginPct} onChange={(e) => setMarginPct(e.target.value)} style={{ maxWidth: 140 }}
            />
            <span className="help">
              Used to estimate profit for price tests, promotions and bundles. If you are unsure, 40% is a common
              starting point — it is an assumption, not a measured value.
            </span>
          </div>

          <ErrorMessage error={error} title={errorTitle(error)} />
          {error?.extra?.detected_headers && (
            <p className="small secondary">Columns found in your file: {error.extra.detected_headers.join(", ")}</p>
          )}

          <div className="row">
            <button className="btn btn-primary" type="submit" disabled={busy || !file}>
              {busy ? "Checking and analysing…" : "Upload and analyse"}
            </button>
            {busy && <span className="muted small">This usually takes a few seconds.</span>}
          </div>
          <p className="small muted">
            Privacy: the file is analysed in memory and then discarded. Only summary results (totals per product,
            week, category and region) are saved to your account.
          </p>
        </form>

        <div className="card stack">
          <h2>What the file needs</h2>
          <ul className="secondary small" style={{ margin: 0, paddingLeft: 18 }}>
            <li><strong>Required:</strong> date, SKU or product name, quantity, unit price.</li>
            <li><strong>Recommended:</strong> order ID (needed for bundles), product name, category.</li>
            <li><strong>Optional:</strong> region, rating, returns, stock on hand (enables restock alerts).</li>
          </ul>
          <h2>Demo data</h2>
          <p className="small secondary">Made-up sample files for trying I-ODSS. They are not real sales.</p>
          <ul className="small" style={{ margin: 0, paddingLeft: 18 }}>
            {SAMPLE_FILES.map((s) => (
              <li key={s.file}>
                <a href={`/samples/${s.file}`} download>{s.file}</a> <span className="muted">— {s.note}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {result && <UploadSummary result={result} onOpen={() => open(result.dataset.id)} />}

      <section className="card">
        <div className="card-header">
          <h2>Your datasets</h2>
        </div>
        <ErrorMessage error={deleteError} title="Could not delete" />
        {datasets.length === 0 ? (
          <p className="secondary">Nothing uploaded yet.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>File</th><th>Period</th><th className="num">Rows</th><th className="num">Products</th>
                  <th>Uploaded</th><th><span className="visually-hidden">Actions</span></th>
                </tr>
              </thead>
              <tbody>
                {datasets.map((d) => (
                  <tr key={d.id}>
                    <td>{d.original_filename}</td>
                    <td>{formatDate(d.date_start)} – {formatDate(d.date_end)}</td>
                    <td className="num">{formatNumber(d.row_count)}</td>
                    <td className="num">{formatNumber(d.sku_count)}</td>
                    <td>{formatDateTime(d.created_at)}</td>
                    <td>
                      <div className="row" style={{ justifyContent: "flex-end", flexWrap: "nowrap" }}>
                        <button className="btn btn-small" onClick={() => open(d.id)}>Open</button>
                        <button className="btn btn-small btn-danger" onClick={() => handleDelete(d)} disabled={deleting === d.id}>
                          {deleting === d.id ? "Deleting…" : "Delete"}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

function errorTitle(error) {
  if (!error) return "";
  if (error.type === "client_check") return "Please check the file";
  if (error.status === 422) return "The file could not be analysed";
  return "Upload failed";
}

function UploadSummary({ result, onOpen }) {
  const d = result.dataset;
  return (
    <section className="card stack" aria-live="polite">
      <div className="alert alert-success">
        <strong>Upload complete.</strong> {formatNumber(d.row_count)} rows from {d.original_filename} were analysed
        ({formatNumber(d.sku_count)} products, {formatDate(d.date_start)} – {formatDate(d.date_end)}).
      </div>
      {result.warning_count > 0 && (
        <div className="alert alert-warning">
          <strong>{formatNumber(d.skipped_row_count)} row(s) were skipped</strong> because of problems
          ({formatNumber(result.warning_count)} issue(s) in total). Fix them in your file and upload again to include them.
          <ul>
            {result.warnings.map((w, i) => <li key={i}>{w}</li>)}
          </ul>
          {result.warning_count > result.warnings.length && (
            <p className="small">…and {result.warning_count - result.warnings.length} more.</p>
          )}
        </div>
      )}
      <div>
        <h2>How your columns were read</h2>
        <div className="table-wrap">
          <table>
            <thead><tr><th>I-ODSS field</th><th>Column in your file</th></tr></thead>
            <tbody>
              {Object.entries(d.column_mapping).map(([field, header]) => (
                <tr key={field}><td>{FIELD_LABELS[field] ?? field}</td><td>{header}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div><button className="btn btn-primary" onClick={onOpen}>Open dashboard</button></div>
    </section>
  );
}
