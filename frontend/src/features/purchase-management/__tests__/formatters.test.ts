import { describe, expect, it } from "vitest";
import { formatCurrency, formatDateTime } from "../utils/formatters";

describe("purchase formatters", () => {
  it("formats a number as BRL currency", () => {
    expect(formatCurrency(2400)).toContain("2.400,00");
    expect(formatCurrency(0)).toContain("0,00");
  });

  it("renders a dash for a missing amount", () => {
    expect(formatCurrency(null)).toBe("—");
    expect(formatCurrency(undefined)).toBe("—");
  });

  it("formats an ISO timestamp as a pt-BR date", () => {
    expect(formatDateTime("2026-08-03T12:00:00Z")).toBe("03/08/2026");
  });

  it("renders a dash for a missing or unparsable timestamp", () => {
    expect(formatDateTime(null)).toBe("—");
    expect(formatDateTime(undefined)).toBe("—");
    expect(formatDateTime("not-a-date")).toBe("—");
  });
});
