import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { ErrorMessage } from "../components/States";
import { useAuth } from "../hooks/useAuth";

export default function LoginPage() {
  const { user, login, register } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState("login"); // login | register
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  if (user) return <Navigate to="/" replace />;

  const switchMode = (next) => {
    setMode(next);
    setError(null);
  };

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (mode === "login") await login(email, password);
      else await register(name, email, password);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };

  const isLogin = mode === "login";
  return (
    <div className="auth-page">
      <div className="card auth-card stack">
        <div>
          <h1>I-ODSS</h1>
          <p className="secondary">Decision support for e-commerce sellers: forecasts, bundles, pricing and stock.</p>
        </div>
        <div className="tabs" role="tablist" aria-label="Account">
          <button role="tab" aria-selected={isLogin} onClick={() => switchMode("login")} type="button">
            Log in
          </button>
          <button role="tab" aria-selected={!isLogin} onClick={() => switchMode("register")} type="button">
            Create account
          </button>
        </div>
        <form className="stack" onSubmit={submit} noValidate={false}>
          {!isLogin && (
            <div className="field">
              <label htmlFor="name">Your name</label>
              <input id="name" className="input" value={name} onChange={(e) => setName(e.target.value)} required autoComplete="name" />
            </div>
          )}
          <div className="field">
            <label htmlFor="email">Email</label>
            <input id="email" type="email" className="input" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" />
          </div>
          <div className="field">
            <label htmlFor="password">Password</label>
            <input
              id="password" type="password" className="input" value={password}
              onChange={(e) => setPassword(e.target.value)} required
              autoComplete={isLogin ? "current-password" : "new-password"}
            />
            {!isLogin && <span className="help">At least 8 characters, not too common, not only numbers.</span>}
          </div>
          <ErrorMessage error={error} title={isLogin ? "Could not log in" : "Could not create account"} />
          <button className="btn btn-primary" type="submit" disabled={busy}>
            {busy ? "Please wait…" : isLogin ? "Log in" : "Create account"}
          </button>
        </form>
      </div>
    </div>
  );
}
