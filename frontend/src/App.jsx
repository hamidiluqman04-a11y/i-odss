import { Link, Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import { EmptyState, ErrorState, LoadingState } from "./components/States";
import { useAuth } from "./hooks/useAuth";
import { DatasetProvider } from "./hooks/useDatasets";
import DashboardPage from "./pages/DashboardPage";
import LoginPage from "./pages/LoginPage";
import UploadPage from "./pages/UploadPage";

function RequireLogin({ children }) {
  const { user } = useAuth();
  return user ? children : <Navigate to="/login" replace />;
}

export default function App() {
  const { status, error, retry } = useAuth();

  if (status === "loading") return <LoadingState message="Connecting to I-ODSS…" />;
  if (status === "error") {
    return (
      <div className="auth-page">
        <div className="auth-card">
          <ErrorState error={error} onRetry={retry} />
        </div>
      </div>
    );
  }

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <RequireLogin>
            <DatasetProvider>
              <Layout />
            </DatasetProvider>
          </RequireLogin>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="upload" element={<UploadPage />} />
        <Route
          path="*"
          element={
            <EmptyState title="Page not found" action={<Link className="btn" to="/">Go to dashboard</Link>}>
              This page does not exist.
            </EmptyState>
          }
        />
      </Route>
    </Routes>
  );
}
