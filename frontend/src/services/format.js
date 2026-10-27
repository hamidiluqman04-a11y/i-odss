const DASH = "—";

export function formatNumber(value, decimals = 0) {
  if (value === null || value === undefined || Number.isNaN(value)) return DASH;
  return Number(value).toLocaleString("en-MY", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

export function formatMoney(value, symbol = "RM") {
  if (value === null || value === undefined || Number.isNaN(value)) return DASH;
  return `${symbol} ${formatNumber(value, 2)}`;
}

/** Short money for chart axes: RM 12.5k */
export function formatMoneyShort(value, symbol = "RM") {
  const abs = Math.abs(value);
  if (abs >= 1e6) return `${symbol} ${(value / 1e6).toFixed(1)}M`;
  if (abs >= 1e3) return `${symbol} ${(value / 1e3).toFixed(1)}k`;
  return `${symbol} ${formatNumber(value)}`;
}

/** "2025-01-03" -> "3 Jan 2025" (dates from the API have no time zone). */
export function formatDate(iso) {
  if (!iso) return DASH;
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}

export function formatDateTime(iso) {
  if (!iso) return DASH;
  return new Date(iso).toLocaleString("en-GB", {
    day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit",
  });
}
