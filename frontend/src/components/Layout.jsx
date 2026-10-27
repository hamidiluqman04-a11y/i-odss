import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { CURRENCY_SYMBOLS, useCurrency } from "../hooks/useCurrency";
import { useDatasets } from "../hooks/useDatasets";
import { formatDate } from "../services/format";

const icons = {
  dashboard: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <rect x="3" y="3" width="7" height="9" rx="1.5" /><rect x="14" y="3" width="7" height="5" rx="1.5" />
      <rect x="14" y="12" width="7" height="9" rx="1.5" /><rect x="3" y="16" width="7" height="5" rx="1.5" />
    </svg>
  ),
  upload: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path d="M12 16V4M7 9l5-5 5 5" /><path d="M4 16v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3" />
    </svg>
  ),
};

export default function Layout() {
  const { user, logout } = useAuth();
  const { datasets, current, select } = useDatasets();
  const { symbol, setSymbol } = useCurrency();
  const navigate = useNavigate();
  const [loggingOut, setLoggingOut] = useState(false);

  const handleLogout = async () => {
    setLoggingOut(true);
    try {
      await logout();
      navigate("/login");
    } finally {
      setLoggingOut(false);
    }
  };

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <strong>I-ODSS</strong>
          <span className="muted small">Seller decision support</span>
        </div>
        <nav className="nav" aria-label="Main">
          <NavLink to="/" end>{icons.dashboard}Dashboard</NavLink>
          <NavLink to="/upload">{icons.upload}Upload data</NavLink>
        </nav>
        <p className="sidebar-note">Your CSV is analysed in memory and not stored. Only summary results are saved.</p>
      </aside>

      <div className="main">
        <header className="topbar">
          <label htmlFor="dataset-picker">Dataset</label>
          <select
            id="dataset-picker"
            className="select dataset-picker"
            value={current?.id ?? ""}
            onChange={(e) => select(Number(e.target.value))}
            disabled={datasets.length === 0}
          >
            {datasets.length === 0 && <option value="">No data uploaded yet</option>}
            {datasets.map((d) => (
              <option key={d.id} value={d.id}>
                {d.original_filename} · {formatDate(d.date_start)} – {formatDate(d.date_end)}
              </option>
            ))}
          </select>
          <span className="spacer" />
          <label htmlFor="currency-picker" title="Changes the symbol only — amounts are not converted">
            Currency
          </label>
          <select id="currency-picker" className="select" value={symbol} onChange={(e) => setSymbol(e.target.value)}>
            {CURRENCY_SYMBOLS.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          <span className="user-chip">
            <span className="avatar" aria-hidden="true">{(user.name || user.email)[0].toUpperCase()}</span>
            <span>{user.name || user.email}</span>
          </span>
          <button className="btn btn-small" onClick={handleLogout} disabled={loggingOut}>
            {loggingOut ? "Logging out…" : "Log out"}
          </button>
        </header>
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
