import { Link } from "react-router-dom";
import { useDatasets } from "../hooks/useDatasets";
import { useResult } from "../hooks/useResult";
import { formatDate, formatNumber } from "../services/format";
import { EmptyState, ErrorState, LoadingState } from "./States";

/**
 * Page frame shared by every analysis page: handles "no dataset yet",
 * loading and error states, then renders children(data).
 * While a different dataset loads, the previous result stays visible but faded.
 * `before` renders between the header and the result (the dashboard's next steps).
 */
export default function ResultPage({ kind, title, intro, before, children }) {
  const { current, status: listStatus, error: listError, refresh } = useDatasets();
  const { status, data, error, reload } = useResult(kind);

  let body;
  if (listStatus === "loading") body = <LoadingState message="Loading your datasets…" />;
  else if (listStatus === "error") body = <ErrorState error={listError} onRetry={refresh} />;
  else if (!current) {
    body = (
      <EmptyState title="No data yet" action={<Link className="btn btn-primary" to="/upload">Upload a CSV file</Link>}>
        Upload your sales export first. Results appear here as soon as it has been analysed.
      </EmptyState>
    );
  } else if (status === "error") body = <ErrorState error={error} onRetry={reload} />;
  else if (!data) body = <LoadingState message="Loading results…" />;
  else {
    body = (
      <div className="stack-lg" aria-busy={status === "loading"} style={{ opacity: status === "loading" ? 0.5 : 1 }}>
        {children(data, current)}
      </div>
    );
  }

  return (
    <>
      <header className="page-header">
        {current && (
          <p className="eyebrow">
            {current.original_filename} · {formatDate(current.date_start)} – {formatDate(current.date_end)} ·{" "}
            {formatNumber(current.row_count)} rows
          </p>
        )}
        <h1>{title}</h1>
        {intro && <p className="page-intro">{intro}</p>}
      </header>
      {current && before}
      {body}
    </>
  );
}
