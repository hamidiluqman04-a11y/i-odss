import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { toChartData } from "../charts/ForecastChart";
import { CurrencyProvider } from "../hooks/useCurrency";
import { api, ApiError } from "../services/api";
import { Bundles } from "./BundlesPage";
import { Forecast } from "./ForecastPage";
import { Inventory } from "./InventoryPage";
import { Pricing, suggestionLabel } from "./PricingPage";

vi.mock("../services/api", async (importOriginal) => {
  const real = await importOriginal();
  return { ...real, api: { simulatePromo: vi.fn() } };
});
afterEach(() => vi.clearAllMocks());

const show = (ui) => render(<CurrencyProvider>{ui}</CurrencyProvider>);

// ── Forecast ───────────────────────────────────────────────────────────

const FORECAST = {
  status: "ok", model: "SARIMA(1,1,1)(1,1,0)[7] on daily sales", model_type: "sarima", sku: null, horizon_weeks: 2,
  series: [
    { label: "Wk 1", week_start: "2025-01-03", actual: 40, forecast: null, lower: null, upper: null },
    { label: "Wk 2", week_start: "2025-01-10", actual: 46, forecast: null, lower: null, upper: null },
    { label: "Wk 3 (F)", week_start: "2025-01-17", actual: null, forecast: 49.7, lower: 41.1, upper: 58.6 },
    { label: "Wk 4 (F)", week_start: "2025-01-24", actual: null, forecast: 51.0, lower: 38.5, upper: 63.9 },
  ],
  evaluation: { holdout_weeks: 4, mape: 13.6, mae: 3.6, baseline_mape: 14.5, baseline_mae: 3.9,
    actual: [26, 28, 25, 29], predicted: [23.2, 23.9, 22.9, 23.0] },
  summary: { n_weeks: 10, excluded_days: 6, avg_weekly: 25.1, recent_avg_weekly: 27, forecast_avg_weekly: 28.1,
    forecast_change_pct: 4.2, trend: "Stable" },
  notes: ["The last 6 day(s) do not make a full week and were left out."],
  plain_explain: "Based on 10 weeks of sales, I-ODSS expects about 28 units per week.",
};

describe("Forecast", () => {
  it("shows the forecast, measured accuracy and notes", () => {
    show(<Forecast data={FORECAST} />);
    const tile = screen.getByText("Expected units per week").closest(".tile");
    expect(within(tile).getByText("28")).toBeInTheDocument();
    expect(screen.getByText("13.6% error")).toBeInTheDocument();
    expect(screen.getByText(/at least as accurate as simply averaging/)).toBeInTheDocument();
    expect(screen.getByText(/expects about 28 units per week/)).toBeInTheDocument();
    expect(screen.getByText(/do not make a full week/)).toBeInTheDocument();
  });

  it("says accuracy is not measurable when there was no test", () => {
    show(<Forecast data={{ ...FORECAST, evaluation: null }} />);
    expect(screen.getByText("Not measurable")).toBeInTheDocument();
    expect(screen.getByText(/not have enough weeks for a fair test/)).toBeInTheDocument();
  });

  it("warns when a simple average beat SARIMA", () => {
    show(<Forecast data={{ ...FORECAST, evaluation: { ...FORECAST.evaluation, mape: 20, baseline_mape: 10 } }} />);
    expect(screen.getByText(/simple 4-week average was more accurate/)).toBeInTheDocument();
  });

  it("explains when there is too little history", () => {
    show(<Forecast data={{ status: "insufficient_data", series: [], notes: [], plain_explain: "Your file covers only 9 day(s) of sales." }} />);
    expect(screen.getByRole("heading", { name: "Not enough history to forecast" })).toBeInTheDocument();
    expect(screen.getByText(/only 9 day/)).toBeInTheDocument();
  });

  it("joins the forecast line to the last actual week", () => {
    const points = toChartData(FORECAST.series);
    expect(points[1]).toMatchObject({ actual: 46, forecast: 46, range: [46, 46] });
    expect(points[2]).toMatchObject({ actual: null, forecast: 49.7, range: [41.1, 58.6], isForecast: true });
    expect(points[0].range).toBeNull();
  });
});

// ── Bundles ────────────────────────────────────────────────────────────

const PAIR = {
  sku_a: "SKU-005", sku_b: "SKU-007", product_a: "Webcam 1080p", product_b: "Ring Light", orders_together: 30,
  support: 0.25, confidence: 1, confidence_reverse: 1, lift: 4, price_a: 215, price_b: 89,
  suggested_discount_pct: 16, bundle_price: 289.76, break_even_uplift_pct: 66.7,
  plain_explain: "Out of every order that included Webcam 1080p...", xai: "FP-Growth pair",
};
const BUNDLES = {
  status: "ok", pairs: [PAIR], total_orders: 120, multi_item_orders: 107, margin_assumption: 0.4, message: null,
  thresholds: { min_orders_together: 2, min_lift: 1.2, min_confidence: 0.25 },
};

describe("Bundles", () => {
  it("shows each pair with its numbers, offer and break-even", () => {
    show(<Bundles data={BUNDLES} />);
    const card = screen.getByRole("heading", { name: "Webcam 1080p + Ring Light" }).closest("section");
    expect(within(card).getByText("30 orders")).toBeInTheDocument();
    expect(within(card).getByText("4.00×")).toBeInTheDocument();
    expect(within(card).getByText("RM 289.76")).toBeInTheDocument();
    expect(within(card).getByText("67% more")).toBeInTheDocument();
  });

  it("explains when there are not enough multi-product orders", () => {
    show(<Bundles data={{ ...BUNDLES, status: "insufficient_data", pairs: [], multi_item_orders: 0,
      message: "Only 0 of your 150 orders contain more than one product." }} />);
    expect(screen.getByRole("heading", { name: "Not enough multi-product orders" })).toBeInTheDocument();
    expect(screen.getByText(/Only 0 of your 150 orders/)).toBeInTheDocument();
  });

  it("warns when the discount is larger than the margin", () => {
    show(<Bundles data={{ ...BUNDLES, pairs: [{ ...PAIR, break_even_uplift_pct: null }] }} />);
    expect(screen.getByText(/loses money on every bundle/)).toBeInTheDocument();
  });
});

// ── Pricing ────────────────────────────────────────────────────────────

const FIXED_PRICE = {
  sku: "SKU-001", product: "Mechanical Keyboard", category: "Peripherals", current_price: 189, price_min: 189,
  price_max: 189, weeks_with_sales: 8, status: "insufficient_price_variation", ped: null, ped_ci_low: null,
  ped_ci_high: null, p_value: null, r_squared: null, reliability: null, recommendation: "no_recommendation",
  test_change_pct: 0, test_price: null, projection: null, margin_assumption: 0.4,
  plain_explain: "'Mechanical Keyboard' was always sold at about the same price.", xai: "Not estimated",
};
const ESTIMATED = {
  ...FIXED_PRICE, sku: "SKU-002", product: "Mouse Pad", price_min: 8, price_max: 12, current_price: 10,
  status: "estimated", ped: -0.4, ped_ci_low: -0.5, ped_ci_high: -0.3, p_value: 0.001, r_squared: 0.98,
  reliability: "strong", recommendation: "test_increase", test_change_pct: 5, test_price: 10.5,
  projection: { weekly_units_now: 100, weekly_units_new: 98, weekly_revenue_now: 1000, weekly_revenue_new: 1029,
    weekly_profit_now: 400, weekly_profit_new: 441 },
  plain_explain: "In weeks when 'Mouse Pad' cost 1% more, about 0.4% fewer units were sold.",
};
const PRICING = { items: [ESTIMATED, FIXED_PRICE], margin_assumption: 0.4, estimated_count: 1, min_weeks_with_sales: 6 };

describe("Pricing", () => {
  it("labels every kind of suggestion, including why there is none", () => {
    expect(suggestionLabel(ESTIMATED)).toBe("Test a 5% price increase");
    expect(suggestionLabel({ ...ESTIMATED, recommendation: "test_decrease", test_change_pct: -5 })).toBe("Test a 5% price cut");
    expect(suggestionLabel({ ...ESTIMATED, recommendation: "hold" })).toBe("Keep current price");
    expect(suggestionLabel(FIXED_PRICE)).toBe("No advice — price never changed");
    expect(suggestionLabel({ ...FIXED_PRICE, status: "insufficient_data" })).toBe("No advice — too few weeks of sales");
    expect(suggestionLabel({ ...ESTIMATED, recommendation: "no_recommendation", reliability: "weak" })).toBe("No advice — no clear pattern");
  });

  it("shows no PED for fixed-price products and explains why", () => {
    show(<Pricing data={{ ...PRICING, items: [FIXED_PRICE], estimated_count: 0 }} datasetId={1} />);
    expect(screen.getByText(/did not change enough to measure price sensitivity/)).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "—" })).toBeInTheDocument();
  });

  it("opens the explanation and projection for a product", async () => {
    show(<Pricing data={PRICING} datasetId={1} />);
    const user = userEvent.setup();
    const row = screen.getByRole("cell", { name: /Mouse Pad/ }).closest("tr");
    await user.click(within(row).getByRole("button", { name: "Why?" }));
    expect(screen.getByText(/about 0.4% fewer units were sold/)).toBeInTheDocument();
    expect(screen.getByText("RM 400.00 → RM 441.00")).toBeInTheDocument();
  });

  it("runs the promotion simulator with the chosen values", async () => {
    api.simulatePromo.mockResolvedValue({
      original_price: 189, discounted_price: 170.1, break_even_volume_increase_pct: 33.3, volume_change_pct: null,
      projection: null, plain_explain: "A 10% discount only pays off if you sell at least 33% more units.",
    });
    show(<Pricing data={PRICING} datasetId={7} />);
    const user = userEvent.setup();
    await user.selectOptions(screen.getByLabelText("Product"), "SKU-001");
    await user.clear(screen.getByLabelText("Discount (%)"));
    await user.type(screen.getByLabelText("Discount (%)"), "10");
    await user.clear(screen.getByLabelText("Gross margin (%)"));
    await user.type(screen.getByLabelText("Gross margin (%)"), "35");
    await user.click(screen.getByRole("button", { name: "Simulate" }));
    expect(api.simulatePromo).toHaveBeenCalledWith(7, { sku: "SKU-001", discount_pct: 10, margin: 0.35 });
    expect(await screen.findByText("+33.3%")).toBeInTheDocument();
    expect(screen.getByText("Unknown")).toBeInTheDocument();
    expect(screen.getByText(/only pays off if you sell at least 33% more/)).toBeInTheDocument();
  });

  it("checks the discount before calling the server", async () => {
    show(<Pricing data={PRICING} datasetId={7} />);
    const user = userEvent.setup();
    await user.clear(screen.getByLabelText("Discount (%)"));
    await user.type(screen.getByLabelText("Discount (%)"), "95");
    await user.click(screen.getByRole("button", { name: "Simulate" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("between 1% and 80%");
    expect(api.simulatePromo).not.toHaveBeenCalled();
  });

  it("shows server errors from the simulator", async () => {
    api.simulatePromo.mockRejectedValue(new ApiError(404, "sku_not_found", "SKU 'X' is not in this dataset."));
    show(<Pricing data={PRICING} datasetId={7} />);
    await userEvent.setup().click(screen.getByRole("button", { name: "Simulate" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("is not in this dataset");
  });
});

// ── Inventory ──────────────────────────────────────────────────────────

const ITEM = {
  sku: "A", product: "Serum", category: "Skincare", stock: null, stock_source: "unknown", rop: 37, lead: 6,
  velocity: 5, safety_stock: 7, status: "unknown", revenue: 100, total_sold: 10, reorder_qty: null,
  avg_rating: null, return_rate: null, days_until_stockout: null,
  plain_explain: "Your file has no stock column, so I-ODSS cannot tell.", xai: "ROP=37",
};

describe("Inventory", () => {
  it("separates calculated reorder points from missing stock data", () => {
    show(<Inventory data={{ items: [ITEM], critical_count: 0, stock_data_available: false }} />);
    expect(screen.getByText(/has no stock levels/)).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "Not in file" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "37.0" })).toBeInTheDocument();
    expect(screen.getAllByText("Unknown")).toHaveLength(2);
  });

  it("filters by status and shows status as text, not colour alone", async () => {
    const items = [
      { ...ITEM, sku: "A", product: "Serum", stock: 12, stock_source: "csv", status: "critical", reorder_qty: 48, days_until_stockout: 2.4 },
      { ...ITEM, sku: "B", product: "Toner", stock: 100, stock_source: "csv", status: "ok", reorder_qty: 0, days_until_stockout: 100 },
    ];
    show(<Inventory data={{ items, critical_count: 1, stock_data_available: true }} />);
    expect(screen.getByText("Reorder now", { selector: ".status-pill" })).toBeInTheDocument();
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Healthy (1)" }));
    expect(screen.queryByText("Serum")).not.toBeInTheDocument();
    expect(screen.getByText("Toner")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "All (2)" }));
    expect(screen.getByText("Serum")).toBeInTheDocument();
  });

  it("shows the explanation for a product", async () => {
    show(<Inventory data={{ items: [ITEM], critical_count: 0, stock_data_available: false }} />);
    await userEvent.setup().click(screen.getByRole("button", { name: "Why?" }));
    expect(screen.getByText("Your file has no stock column, so I-ODSS cannot tell.")).toBeInTheDocument();
    expect(screen.getByText(/average rating not in file/)).toBeInTheDocument();
  });
});
