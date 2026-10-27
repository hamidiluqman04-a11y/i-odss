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
  critical: { label: "Reorder now", color: "var(--critical)", ink: "var(--critical-ink)", icon: "!" },
  warning: { label: "Order soon", color: "var(--warning)", ink: "var(--warning-ink)", icon: "~" },
  ok: { label: "Healthy", color: "var(--good)", ink: "var(--good-ink)", icon: "✓" },
  unknown: { label: "Stock unknown", color: "var(--axis)", ink: "var(--text-secondary)", icon: "?" },
};

/** Status is always shown as symbol + word + colour, never colour alone. */
export function StatusPill({ status }) {
  const s = STATUS[status] ?? STATUS.unknown;
  return (
    <span className="status-pill" style={{ color: s.ink }}>
      <span className="status-icon" style={{ background: s.color }} aria-hidden="true">{s.icon}</span>
      {s.label}
    </span>
  );
}

export const STATUS_LABELS = Object.fromEntries(Object.entries(STATUS).map(([k, v]) => [k, v.label]));
