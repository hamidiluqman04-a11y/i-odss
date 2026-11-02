import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "../hooks/useAuth";
import { CurrencyProvider } from "../hooks/useCurrency";
import { DatasetProvider } from "../hooks/useDatasets";
import { api, ApiError } from "../services/api";
import { Dashboard } from "./DashboardPage";
import LoginPage from "./LoginPage";
import UploadPage, { checkFile } from "./UploadPage";

vi.mock("../services/api", async (importOriginal) => {
  const real = await importOriginal();
  return {
    ...real,
    api: {
      csrf: vi.fn(), me: vi.fn(), login: vi.fn(), register: vi.fn(), logout: vi.fn(),
      listDatasets: vi.fn(), uploadDataset: vi.fn(), deleteDataset: vi.fn(), getResult: vi.fn(),
    },
  };
});

beforeEach(() => {
  api.csrf.mockResolvedValue({});
  api.me.mockRejectedValue(new ApiError(403, "not_authenticated", "Not logged in"));
  api.listDatasets.mockResolvedValue({ datasets: [] });
  try { localStorage.clear(); } catch { /* ignore */ }
});
afterEach(() => vi.clearAllMocks());

function renderWithProviders(ui, { datasets = false } = {}) {
  const content = datasets ? <DatasetProvider>{ui}</DatasetProvider> : ui;
  return render(
    <MemoryRouter>
      <AuthProvider>
        <CurrencyProvider>{content}</CurrencyProvider>
      </AuthProvider>
    </MemoryRouter>,
  );
}

// ── Login ──────────────────────────────────────────────────────────────

describe("LoginPage", () => {
  it("shows the server's message when login fails", async () => {
    api.login.mockRejectedValue(new ApiError(401, "invalid_credentials", "Invalid email or password."));
    renderWithProviders(<LoginPage />);
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText("Email"), "seller@example.com");
    await user.type(screen.getByLabelText("Password"), "wrong-password");
    await user.click(screen.getByRole("button", { name: "Log in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid email or password.");
    expect(api.login).toHaveBeenCalledWith("seller@example.com", "wrong-password");
  });

  it("shows field errors from registration", async () => {
    api.register.mockRejectedValue(
      new ApiError(400, "validation_error", "Some of the submitted values are invalid.", {
        password: ["This password is too common."],
      }),
    );
    renderWithProviders(<LoginPage />);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("tab", { name: "Create account" }));
    await user.type(screen.getByLabelText("Your name"), "Ali");
    await user.type(screen.getByLabelText("Email"), "ali@shop.my");
    await user.type(screen.getByLabelText("Password"), "password123");
    await user.click(screen.getByRole("button", { name: "Create account" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("password: This password is too common.");
  });
});

// ── Upload ─────────────────────────────────────────────────────────────

describe("checkFile", () => {
  it("rejects missing, non-CSV, empty and oversized files", () => {
    expect(checkFile(null)).toMatch(/Choose a CSV/);
    expect(checkFile(new File(["x"], "sales.xlsx"))).toMatch(/not a CSV/);
    expect(checkFile(new File([], "sales.csv"))).toMatch(/empty/);
    const big = new File(["x"], "big.csv");
    Object.defineProperty(big, "size", { value: 11 * 1024 * 1024 });
    expect(checkFile(big)).toMatch(/larger than 10 MB/);
    expect(checkFile(new File(["a,b"], "ok.CSV"))).toBeNull();
  });
});

describe("UploadPage", () => {
  async function chooseFile(name, content = "a,b\n1,2") {
    const user = userEvent.setup({ applyAccept: false });
    await user.upload(await screen.findByTestId("file-input"), new File([content], name, { type: "text/csv" }));
    return user;
  }

  it("does not send a non-CSV file to the server", async () => {
    renderWithProviders(<UploadPage />, { datasets: true });
    const user = await chooseFile("orders.xlsx");
    await user.click(screen.getByRole("button", { name: "Upload and analyse" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("is not a CSV file");
    expect(api.uploadDataset).not.toHaveBeenCalled();
  });

  it("shows the validation errors returned by the server", async () => {
    api.uploadDataset.mockRejectedValue(
      new ApiError(422, "missing_columns", "Your CSV is missing 1 required column(s).",
        ["Cannot find column for 'price'"], { detected_headers: ["Date", "SKU", "Qty"] }),
    );
    renderWithProviders(<UploadPage />, { datasets: true });
    const user = await chooseFile("orders.csv");
    await user.click(screen.getByRole("button", { name: "Upload and analyse" }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("The file could not be analysed");
    expect(alert).toHaveTextContent("Cannot find column for 'price'");
    expect(screen.getByText(/Columns found in your file: Date, SKU, Qty/)).toBeInTheDocument();
  });

  it("uploads with the chosen margin and shows the summary and skipped rows", async () => {
    api.uploadDataset.mockResolvedValue({
      dataset: {
        id: 7, original_filename: "orders.csv", row_count: 99, skipped_row_count: 1, sku_count: 5,
        date_start: "2025-01-01", date_end: "2025-02-01", column_mapping: { qty: "Quantity" },
        created_at: "2025-02-02T10:00:00Z",
      },
      warnings: ["Row 4: 'Date' has unrecognised date format 'soon'"],
      warning_count: 1,
    });
    renderWithProviders(<UploadPage />, { datasets: true });
    const user = await chooseFile("orders.csv");
    await user.clear(screen.getByLabelText(/gross margin/));
    await user.type(screen.getByLabelText(/gross margin/), "30");
    await user.click(screen.getByRole("button", { name: "Upload and analyse" }));

    expect(await screen.findByText(/Upload complete/)).toBeInTheDocument();
    expect(api.uploadDataset.mock.calls[0][1]).toEqual({ margin: 0.3 });
    expect(screen.getByText(/1 row\(s\) were skipped/)).toBeInTheDocument();
    expect(screen.getByText("Row 4: 'Date' has unrecognised date format 'soon'")).toBeInTheDocument();
    const list = screen.getByRole("heading", { name: "Your datasets" }).closest("section");
    expect(within(list).getByText("orders.csv")).toBeInTheDocument();
  });

  it("deletes a dataset after confirmation", async () => {
    api.listDatasets.mockResolvedValue({
      datasets: [{ id: 3, original_filename: "old.csv", row_count: 10, sku_count: 2,
        date_start: "2025-01-01", date_end: "2025-01-10", created_at: "2025-01-11T00:00:00Z" }],
    });
    api.deleteDataset.mockResolvedValue(null);
    renderWithProviders(<UploadPage />, { datasets: true });
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Delete" }));
    expect(api.deleteDataset).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Delete dataset", hidden: true }));
    expect(api.deleteDataset).toHaveBeenCalledWith(3);
    await waitFor(() => expect(screen.queryByText("old.csv")).not.toBeInTheDocument());
  });
});

// ── Dashboard ──────────────────────────────────────────────────────────

const DASHBOARD = {
  metrics: { revenue: 51409, orders: 120, units: 300, aov: 428.41, skus_count: 8, days_of_data: 62, at_risk: null },
  weekly_sales: [{ week: "Wk 1", units: 40 }, { week: "Wk 2", units: 45 }],
  top_products: [{ sku: "SKU-005", name: "Webcam 1080p", revenue: 12900 }],
  categories: [{ category: "Electronics", revenue: 30000, units: 120 }, { category: "Peripherals", revenue: 21409, units: 180 }],
  regions: [{ region: "Selangor", revenue: 20000, orders: 50 }],
};

describe("Dashboard", () => {
  it("shows KPI tiles from the API result", async () => {
    renderWithProviders(<Dashboard data={DASHBOARD} />);
    expect(await screen.findByText("RM 51,409.00")).toBeInTheDocument();
    expect(screen.getByText("120")).toBeInTheDocument();
    expect(screen.getByText("RM 428.41")).toBeInTheDocument();
  });

  it("says restock status is unknown when the file has no stock column", async () => {
    renderWithProviders(<Dashboard data={DASHBOARD} />);
    expect(await screen.findByText("Unknown")).toBeInTheDocument();
    expect(screen.getByText("Your file has no stock column")).toBeInTheDocument();
  });

  it("explains a partial last week", async () => {
    renderWithProviders(<Dashboard data={DASHBOARD} />);
    expect(await screen.findByText(/last week only covers 6 day\(s\)/)).toBeInTheDocument();
  });

  it("can show each chart as a table", async () => {
    renderWithProviders(<Dashboard data={DASHBOARD} />);
    const user = userEvent.setup();
    const card = (await screen.findByRole("heading", { name: "Top products by revenue" })).closest("section");
    await user.click(within(card).getByRole("button", { name: "Table" }));
    expect(within(card).getByRole("cell", { name: "Webcam 1080p" })).toBeInTheDocument();
    expect(within(card).getByRole("cell", { name: "RM 12,900.00" })).toBeInTheDocument();
  });

  it("gives every chart a text alternative for screen readers", async () => {
    renderWithProviders(<Dashboard data={DASHBOARD} />);
    expect(await screen.findByRole("img", {
      name: "Line chart of units sold per week over 2 weeks. Highest: Wk 2, 45 units. Lowest: Wk 1, 40 units. Most recent: Wk 2, 45 units.",
    })).toBeInTheDocument();
    expect(screen.getByRole("img", {
      name: "Bar chart of top products by revenue, 1 bar. Highest: Webcam 1080p, RM 12,900.00. Lowest: Webcam 1080p, RM 12,900.00.",
    })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /^Bar chart of revenue by category, 2 bars\. Highest: Electronics/ })).toBeInTheDocument();
  });

  it("shows region revenue share", async () => {
    renderWithProviders(<Dashboard data={DASHBOARD} />);
    expect(await screen.findByRole("cell", { name: "38.9%" })).toBeInTheDocument();
  });
});
