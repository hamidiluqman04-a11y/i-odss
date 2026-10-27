import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiError, detailLines } from "./api";

function mockFetch(status, body, { json = true } = {}) {
  const fn = vi.fn().mockResolvedValue({
    status,
    ok: status >= 200 && status < 300,
    json: json ? () => Promise.resolve(body) : () => Promise.reject(new Error("not json")),
  });
  globalThis.fetch = fn;
  return fn;
}

afterEach(() => {
  vi.restoreAllMocks();
  document.cookie = "csrftoken=; expires=Thu, 01 Jan 1970 00:00:00 GMT";
});

describe("api client", () => {
  it("sends JSON and the CSRF token on POST", async () => {
    document.cookie = "csrftoken=abc123";
    const fetchMock = mockFetch(200, { user: { email: "a@b.co" } });
    await api.login("a@b.co", "secret");
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/auth/login/");
    expect(options.method).toBe("POST");
    expect(options.headers["X-CSRFToken"]).toBe("abc123");
    expect(options.headers["Content-Type"]).toBe("application/json");
    expect(JSON.parse(options.body)).toEqual({ email: "a@b.co", password: "secret" });
  });

  it("does not send a CSRF header on GET", async () => {
    const fetchMock = mockFetch(200, { datasets: [] });
    await api.listDatasets();
    expect(fetchMock.mock.calls[0][1].headers["X-CSRFToken"]).toBeUndefined();
  });

  it("uploads the file as multipart form data with the margin", async () => {
    const fetchMock = mockFetch(201, { dataset: { id: 1 } });
    const file = new File(["a,b"], "sales.csv", { type: "text/csv" });
    await api.uploadDataset(file, { margin: 0.35 });
    const body = fetchMock.mock.calls[0][1].body;
    expect(body).toBeInstanceOf(FormData);
    expect(body.get("file").name).toBe("sales.csv");
    expect(body.get("margin")).toBe("0.35");
  });

  it("turns the API error format into an ApiError", async () => {
    mockFetch(422, {
      error: { type: "missing_columns", message: "Missing columns.", details: ["no price"], detected_headers: ["A"] },
    });
    const err = await api.uploadDataset(new File(["x"], "x.csv")).catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(422);
    expect(err.type).toBe("missing_columns");
    expect(err.message).toBe("Missing columns.");
    expect(err.details).toEqual(["no price"]);
    expect(err.extra.detected_headers).toEqual(["A"]);
  });

  it("explains a CSRF rejection (HTML 403 page)", async () => {
    mockFetch(403, null, { json: false });
    const err = await api.logout().catch((e) => e);
    expect(err.type).toBe("csrf_failed");
  });

  it("reports when the server cannot be reached", async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));
    const err = await api.me().catch((e) => e);
    expect(err.type).toBe("network_error");
    expect(err.message).toMatch(/Cannot reach/);
  });

  it("returns null for 204 No Content", async () => {
    mockFetch(204, null);
    expect(await api.deleteDataset(3)).toBeNull();
  });

  it("unwraps a saved result by kind", async () => {
    const fetchMock = mockFetch(200, { dataset_id: 3, forecast: { status: "ok" } });
    expect(await api.getResult(3, "forecast")).toEqual({ status: "ok" });
    expect(fetchMock.mock.calls[0][0]).toBe("/api/datasets/3/forecast/");
  });
});

describe("detailLines", () => {
  it("flattens field errors", () => {
    expect(detailLines({ email: ["Enter a valid email."], password: ["Required."] })).toEqual([
      "email: Enter a valid email.",
      "password: Required.",
    ]);
  });
  it("keeps list details and ignores empty ones", () => {
    expect(detailLines(["Row 3: bad date"])).toEqual(["Row 3: bad date"]);
    expect(detailLines(null)).toEqual([]);
  });
});
