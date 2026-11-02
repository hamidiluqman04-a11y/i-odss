import { describe, expect, it } from "vitest";
import { formatDate, formatMoney, formatMoneyShort, formatNumber } from "./format";

describe("format helpers", () => {
  it("formats numbers and money", () => {
    expect(formatNumber(1234.567, 1)).toBe("1,234.6");
    expect(formatMoney(51409, "RM")).toBe("RM 51,409.00");
    expect(formatMoney(12.5, "$")).toBe("$ 12.50");
  });
  it("shows a dash for missing values", () => {
    expect(formatNumber(null)).toBe("—");
    expect(formatMoney(undefined)).toBe("—");
    expect(formatDate(null)).toBe("—");
  });
  it("shortens axis money", () => {
    expect(formatMoneyShort(12500, "RM")).toBe("RM 12.5k");
    expect(formatMoneyShort(2_300_000, "Rp")).toBe("Rp 2.3M");
    expect(formatMoneyShort(950, "RM")).toBe("RM 950");
  });
  it("formats API dates without time-zone shifts", () => {
    expect(formatDate("2025-01-03")).toBe("3 Jan 2025");
  });
});
