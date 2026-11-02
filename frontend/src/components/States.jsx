import { detailLines } from "../services/api";

export function LoadingState({ message = "Loading…" }) {
  return (
    <div className="state" role="status" aria-live="polite">
      <div className="spinner" aria-hidden="true" />
      <p className="secondary">{message}</p>
    </div>
  );
}

export function ErrorMessage({ error, title = "Something went wrong" }) {
  if (!error) return null;
  const lines = detailLines(error.details);
  return (
    <div className="alert alert-error" role="alert">
      <strong>{title}</strong>
      <p>{error.message}</p>
      {lines.length > 0 && (
        <ul>
          {lines.map((line, i) => (
            <li key={i}>{line}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function ErrorState({ error, onRetry }) {
  return (
    <div className="stack">
      <ErrorMessage error={error} />
      {onRetry && (
        <div>
          <button className="btn" onClick={onRetry}>
            Try again
          </button>
        </div>
      )}
    </div>
  );
}

export function EmptyState({ title, children, action }) {
  return (
    <div className="card state">
      <h2>{title}</h2>
      <p className="secondary">{children}</p>
      {action}
    </div>
  );
}
