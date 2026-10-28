/** A headline number. Use this instead of a chart when the story is one value. */
export function Tile({ label, value, note }) {
  return (
    <div className="card tile">
      <div className="tile-label">{label}</div>
      <div className="tile-value">{value}</div>
      {note && <div className="tile-note">{note}</div>}
    </div>
  );
}

const STATUS = {
  critical: { label: "Reorder now", icon: "!" },
  warning: { label: "Order soon", icon: "~" },
  ok: { label: "Healthy", icon: "✓" },
  unknown: { label: "Stock unknown", icon: "?" },
};

/** Status is always shown as symbol + word + colour, never colour alone. */
export function StatusPill({ status, label }) {
  const key = STATUS[status] ? status : "unknown";
  return (
    <span className={`status-pill ${key}`}>
      <span className="status-icon" aria-hidden="true">{STATUS[key].icon}</span>
      {label ?? STATUS[key].label}
    </span>
  );
}

export const STATUS_LABELS = Object.fromEntries(Object.entries(STATUS).map(([k, v]) => [k, v.label]));
