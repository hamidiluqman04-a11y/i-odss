import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ConfirmDialog } from "../components/Answer";
import Icon from "../components/Icons";
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
  const [pendingDelete, setPendingDelete] = useState(null);
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

  const confirmDelete = async () => {
    const dataset = pendingDelete;
    if (!dataset) return;
    setDeleting(dataset.id);
    setDeleteError(null);
    try {
      await remove(dataset.id);
      if (result?.dataset.id === dataset.id) setResult(null);
    } catch (err) {
      setDeleteError(err);
    } finally {
      setDeleting(null);
      setPendingDelete(null);
    }
  };

  const open = (id) => {
    select(id);
    navigate("/");
  };

  const marginOk = Number(marginPct) > 0 && Number(marginPct) < 100;

  return (
    <>
      <header className="page-header">
        <h1>Upload sales data</h1>
        <p className="page-intro">
          Export your orders from Shopee, Lazada, TikTok Shop or any shop as a CSV file. I-ODSS checks every row,
          then runs every analysis at once.
        </p>
      </header>

      <div className="upload-grid">
        <form className="card stack-lg" onSubmit={submit} noValidate aria-label="Upload a sales file">
          <ol className="steps">
            <li className={`step${file ? " done" : ""}`}>
              <span className="step-num" aria-hidden="true">1</span>
              <div className="step-body">
                <h2 className="step-title">Choose your CSV file</h2>
                <div
                  className={`dropzone${dragging ? " dragging" : ""}${file ? " has-file" : ""}`}
                  role="button"
                  tabIndex={0}
                  aria-label={file ? `Selected file: ${file.name}. Choose a different file` : "Choose a CSV file"}
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
                  <Icon name={file ? "file" : "upload"} />
                  <p className="dropzone-name"><strong>{file ? file.name : "Drop your CSV file here, or click to choose"}</strong></p>
                  <p className="secondary small">
                    {file ? `${formatNumber(file.size / 1024, 1)} KB · click to choose a different file` : `CSV only, up to ${MAX_UPLOAD_MB} MB`}
                  </p>
                </div>
                <input
                  ref={inputRef}
                  type="file"
                  accept=".csv,text/csv"
                  className="visually-hidden"
                  data-testid="file-input"
                  tabIndex={-1}
                  onChange={(e) => choose(e.target.files[0])}
                />
              </div>
            </li>

            <li className={`step${marginOk ? " done" : ""}`}>
              <span className="step-num" aria-hidden="true">2</span>
              <div className="step-body">
                <h2 className="step-title">Set your margin</h2>
                <div className="field">
                  <label htmlFor="margin">Your typical gross margin (%)</label>
                  <input
                    id="margin" className="input input-short" type="number" min="1" max="99" step="1" inputMode="numeric"
                    value={marginPct} onChange={(e) => setMarginPct(e.target.value)} aria-describedby="margin-help"
                  />
                  <span className="help" id="margin-help">
                    Used to estimate profit for price tests, promotions and bundles. If you are unsure, 40% is a common
                    starting point — it is an assumption, not a measured value.
                  </span>
                </div>
              </div>
            </li>

            <li className="step">
              <span className="step-num" aria-hidden="true">3</span>
              <div className="step-body">
                <h2 className="step-title">Analyse</h2>
                <ErrorMessage error={error} title={errorTitle(error)} />
                {error?.extra?.detected_headers && (
                  <p className="small secondary">Columns found in your file: {error.extra.detected_headers.join(", ")}</p>
                )}
                <div className="row">
                  <button className="btn btn-primary" type="submit" disabled={busy || !file}>
                    {busy ? "Checking and analysing…" : "Upload and analyse"}
                  </button>
                  <span className="small secondary" aria-live="polite">
                    {busy ? "This usually takes a few seconds." : file ? "" : "Choose a file first."}
                  </span>
                </div>
              </div>
            </li>
          </ol>
          <p className="small secondary privacy-note">
            <Icon name="lock" />
            <span>
              The file is analysed in memory and then discarded. Only summary results (totals per product, week,
              category and region) are saved to your account.
            </span>
          </p>
        </form>

        <aside className="card stack">
          <h2>What the file needs</h2>
          <ul className="req-list small secondary">
            <li><strong>Required:</strong> date, SKU or product name, quantity, unit price.</li>
            <li><strong>Recommended:</strong> order ID (needed for bundles), product name, category.</li>
            <li><strong>Optional:</strong> region, rating, returns, stock on hand (enables restock alerts).</li>
          </ul>
          <h2>Try it with demo data</h2>
          <span className="demo-tag">Demo data — made up, not real sales</span>
          <ul className="sample-list">
            {SAMPLE_FILES.map((s) => (
              <li key={s.file}>
                <a href={`/samples/${s.file}`} download>
                  {s.file}
                  <span>{s.note}</span>
                </a>
              </li>
            ))}
          </ul>
        </aside>
      </div>

      {result && <UploadSummary result={result} onOpen={() => open(result.dataset.id)} />}

      <section className="card">
        <div className="card-header">
          <h2>Your datasets</h2>
        </div>
        <ErrorMessage error={deleteError} title="Could not delete" />
        {datasets.length === 0 ? (
          <p className="secondary">Nothing uploaded yet. Your uploads will be listed here.</p>
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
                    <td className="nowrap">{formatDate(d.date_start)} – {formatDate(d.date_end)}</td>
                    <td className="num">{formatNumber(d.row_count)}</td>
                    <td className="num">{formatNumber(d.sku_count)}</td>
                    <td className="nowrap">{formatDateTime(d.created_at)}</td>
                    <td>
                      <div className="row" style={{ justifyContent: "flex-end", flexWrap: "nowrap" }}>
                        <button className="btn btn-small" type="button" onClick={() => open(d.id)}>Open</button>
                        <button className="btn btn-small btn-danger" type="button" onClick={() => setPendingDelete(d)}
                          disabled={deleting === d.id}>
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

      <ConfirmDialog
        open={pendingDelete !== null}
        title="Delete this dataset?"
        confirmLabel="Delete dataset"
        busyLabel="Deleting…"
        busy={deleting !== null}
        onConfirm={confirmDelete}
        onCancel={() => setPendingDelete(null)}
      >
        The saved results for <strong>{pendingDelete?.original_filename}</strong> will be removed from your account.
        This cannot be undone.
      </ConfirmDialog>
    </>
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
    <section className="card stack" aria-live="polite" aria-label="Upload result">
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
      <div className="row">
        <button className="btn btn-primary" type="button" onClick={onOpen}>Open dashboard</button>
        <span className="small secondary">Every results page now shows this file.</span>
      </div>
      <details className="tech">
        <summary>How your columns were read</summary>
        <div className="table-wrap" style={{ marginTop: "var(--space-sm)" }}>
          <table>
            <thead><tr><th>I-ODSS field</th><th>Column in your file</th></tr></thead>
            <tbody>
              {Object.entries(d.column_mapping).map(([field, header]) => (
                <tr key={field}><td>{FIELD_LABELS[field] ?? field}</td><td>{header}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </section>
  );
}
