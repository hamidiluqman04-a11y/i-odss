import { Link, Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import { EmptyState, ErrorState, LoadingState } from "./components/States";
import { useAuth } from "./hooks/useAuth";
import { DatasetProvider } from "./hooks/useDatasets";
import BundlesPage from "./pages/BundlesPage";
import DashboardPage from "./pages/DashboardPage";
import ForecastPage from "./pages/ForecastPage";
import InventoryPage from "./pages/InventoryPage";
import LoginPage from "./pages/LoginPage";
import PricingPage from "./pages/PricingPage";
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
      <div className="auth-page centered">
        <div className="card auth-card">
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
        <Route path="forecast" element={<ForecastPage />} />
        <Route path="bundles" element={<BundlesPage />} />
        <Route path="pricing" element={<PricingPage />} />
        <Route path="inventory" element={<InventoryPage />} />
        <Route path="upload" element={<UploadPage />} />
        <Route
          path="*"
          element={
            <EmptyState title="Page not found" action={<Link className="btn btn-primary" to="/">Go to overview</Link>}>
              This page does not exist.
            </EmptyState>
          }
        />
      </Route>
    </Routes>
  );
}
