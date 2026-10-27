/**
 * The only place the React app talks to the Django API.
 *
 * - Every request goes to /api/... (Vite forwards it to Django in development).
 * - Login is kept in Django's HttpOnly session cookie; JavaScript never sees it.
 * - Requests that change data (POST, DELETE) send the CSRF token from the
 *   "csrftoken" cookie in the X-CSRFToken header, as Django requires.
 * - Every failure becomes an ApiError with a message that can be shown to the user.
 */

export class ApiError extends Error {
  constructor(status, type, message, details = null, extra = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.type = type;
    this.details = details;
    this.extra = extra;
  }
}

function getCookie(name) {
  const match = document.cookie.split("; ").find((part) => part.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.split("=")[1]) : "";
}

async function request(path, { method = "GET", json, form } = {}) {
  const headers = { Accept: "application/json" };
  let body;
  if (method !== "GET") headers["X-CSRFToken"] = getCookie("csrftoken");
  if (form) {
    body = form; // the browser sets the multipart Content-Type itself
  } else if (json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(json);
  }

  let response;
  try {
    response = await fetch(`/api${path}`, { method, headers, body, credentials: "same-origin" });
  } catch {
    throw new ApiError(0, "network_error", "Cannot reach the I-ODSS server. Check that the backend is running.");
  }

  if (response.status === 204) return null;
  let data = null;
  try {
    data = await response.json();
  } catch {
    // Not JSON (e.g. Django's own CSRF failure page) — handled below.
  }
  if (!response.ok) {
    const err = data?.error;
    if (!err && response.status === 403) {
      throw new ApiError(403, "csrf_failed", "Your security token has expired. Please refresh the page and try again.");
    }
    const { type, message, details, ...extra } = err ?? {};
    throw new ApiError(
      response.status,
      type ?? "http_error",
      message ?? `The server returned an error (${response.status}).`,
      details ?? null,
      extra,
    );
  }
  return data;
}

export const api = {
  csrf: () => request("/auth/csrf/"),
  me: () => request("/auth/me/"),
  login: (email, password) => request("/auth/login/", { method: "POST", json: { email, password } }),
  register: (name, email, password) => request("/auth/register/", { method: "POST", json: { name, email, password } }),
  logout: () => request("/auth/logout/", { method: "POST" }),

  listDatasets: () => request("/datasets/"),
  uploadDataset: (file, { margin } = {}) => {
    const form = new FormData();
    form.append("file", file);
    if (margin !== undefined) form.append("margin", String(margin));
    return request("/datasets/", { method: "POST", form });
  },
  deleteDataset: (id) => request(`/datasets/${id}/`, { method: "DELETE" }),
  /** kind: "dashboard" | "inventory" | "forecast" | "bundles" | "pricing" */
  getResult: (id, kind) => request(`/datasets/${id}/${kind}/`).then((data) => data[kind]),
  simulatePromo: (id, body) =>
    request(`/datasets/${id}/promo-simulation/`, { method: "POST", json: body }).then((d) => d.simulation),
};

/** Turns DRF field errors {"email": ["..."]} into readable lines. */
export function detailLines(details) {
  if (!details) return [];
  if (Array.isArray(details)) return details.map(String);
  return Object.entries(details).flatMap(([field, msgs]) =>
    (Array.isArray(msgs) ? msgs : [msgs]).map((m) => (field === "non_field_errors" ? String(m) : `${field}: ${m}`)),
  );
}
