import { useEffect, useRef, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { CURRENCY_SYMBOLS, useCurrency } from "../hooks/useCurrency";
import { useDatasets } from "../hooks/useDatasets";
import { formatDate } from "../services/format";
import Icon from "./Icons";

// The five analysis areas. Phones show them as a bottom bar with the short labels.
const AREAS = [
  { to: "/", end: true, icon: "dashboard", label: "Overview", short: "Overview" },
  { to: "/forecast", icon: "forecast", label: "Demand forecast", short: "Forecast" },
  { to: "/bundles", icon: "bundles", label: "Product bundles", short: "Bundles" },
  { to: "/pricing", icon: "pricing", label: "Pricing", short: "Pricing" },
  { to: "/inventory", icon: "inventory", label: "Inventory", short: "Stock" },
];

export default function Layout() {
  const { datasets, current, select } = useDatasets();
  const location = useLocation();

  return (
    <div className="shell">
      <a className="skip-link" href="#main-content">Skip to content</a>
      <aside className="sidebar">
        <Link className="brand" to="/">
          <strong>I-ODSS</strong>
          <span>Seller decision support</span>
        </Link>
        <nav aria-label="Main">
          <p className="eyebrow nav-label">Your results</p>
          <div className="nav">
            {AREAS.map((a) => (
              <NavLink key={a.to} to={a.to} end={a.end}><Icon name={a.icon} />{a.label}</NavLink>
            ))}
            <NavLink to="/upload"><Icon name="upload" />Upload data</NavLink>
          </div>
        </nav>
        <p className="sidebar-note">
          <Icon name="lock" />
          <span>Your CSV is analysed in memory and not stored. Only summary results are saved.</span>
        </p>
      </aside>

      <div className="main">
        <header className="topbar">
          <Link className="topbar-brand" to="/">I-ODSS</Link>
          <div className="dataset-switch">
            <label htmlFor="dataset-picker" className="eyebrow">Viewing dataset</label>
            <select
              id="dataset-picker"
              className="select"
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
          </div>
          <span className="spacer" />
          {location.pathname !== "/upload" && (
            <Link className="btn btn-primary btn-small topbar-upload" to="/upload" aria-label="Upload data">
              <Icon name="upload" />
              <span className="topbar-upload-label">Upload data</span>
            </Link>
          )}
          <AccountMenu key={location.pathname} />
        </header>

        <main className="content" id="main-content" tabIndex={-1}>
          <Outlet />
        </main>

        <nav className="bottom-nav" aria-label="Main (mobile)">
          {AREAS.map((a) => (
            <NavLink key={a.to} to={a.to} end={a.end}>
              <span className="pill"><Icon name={a.icon} /></span>
              <span>{a.short}</span>
            </NavLink>
          ))}
        </nav>
      </div>
    </div>
  );
}

/** Name, currency symbol and log out, behind the avatar. Closes on outside click or Escape. */
function AccountMenu() {
  const { user, logout } = useAuth();
  const { symbol, setSymbol } = useCurrency();
  const navigate = useNavigate();
  const ref = useRef(null);
  const [loggingOut, setLoggingOut] = useState(false);
  const name = user.name || user.email;

  useEffect(() => {
    const close = (e) => {
      const menu = ref.current;
      if (!menu?.open) return;
      if (e.type === "keydown" && e.key === "Escape") {
        menu.open = false;
        menu.querySelector("summary")?.focus();
      } else if (e.type === "pointerdown" && !menu.contains(e.target)) {
        menu.open = false;
      }
    };
    document.addEventListener("pointerdown", close);
    document.addEventListener("keydown", close);
    return () => {
      document.removeEventListener("pointerdown", close);
      document.removeEventListener("keydown", close);
    };
  }, []);

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
    <details className="account" ref={ref}>
      <summary aria-label={`Account: ${name}`}>
        <span className="avatar" aria-hidden="true">{name[0].toUpperCase()}</span>
        <span className="account-name">{name}</span>
        <Icon name="chevron" />
      </summary>
      <div className="account-menu">
        <div className="who">
          <strong>{user.name || "Your account"}</strong>
          <span>{user.email}</span>
        </div>
        <div className="field">
          <label htmlFor="currency-picker">Currency symbol</label>
          <select id="currency-picker" className="select" value={symbol} onChange={(e) => setSymbol(e.target.value)}>
            {CURRENCY_SYMBOLS.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          <span className="help">Changes the label only. Amounts are never converted.</span>
        </div>
        <button className="btn btn-secondary" type="button" onClick={handleLogout} disabled={loggingOut}>
          {loggingOut ? "Logging out…" : "Log out"}
        </button>
      </div>
    </details>
  );
}
