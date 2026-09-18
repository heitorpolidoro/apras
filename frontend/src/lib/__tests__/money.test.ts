import { describe, expect, it } from "vitest";

import { limitDecimals, MONEY_DECIMALS, RATIO_DECIMALS } from "../money";

describe("limitDecimals", () => {
  it("exposes the two scales the forms use", () => {
    expect(MONEY_DECIMALS).toBe(2);
    expect(RATIO_DECIMALS).toBe(4);
  });

  it.each([
    // [raw, places, expected]
    ["2.675", 2, "2.67"],
    ["2,675", 2, "2,67"],
    ["2.6", 2, "2.6"],
    ["1200", 2, "1200"],
    ["", 2, ""],
    ["2.", 2, "2."],
    ["2,", 2, "2,"],
    ["-", 2, "-"],
    ["0.129", 4, "0.129"],
    ["0.12345", 4, "0.1234"],
  ])("limitDecimals(%o, %o) === %o", (raw, places, expected) => {
    expect(limitDecimals(raw as string, places as number)).toBe(expected);
  });

  it("truncates and never rounds", () => {
    // 2.999 rounded to two places would be 3.00; the field must show 2.99.
    expect(limitDecimals("2.999", 2)).toBe("2.99");
    expect(limitDecimals("0.99999", 4)).toBe("0.9999");
  });

  it("keeps the separator the user typed", () => {
    expect(limitDecimals("1234,5678", 2)).toBe("1234,56");
    expect(limitDecimals("1234.5678", 2)).toBe("1234.56");
  });

  it("leaves a negative or partly typed value alone", () => {
    expect(limitDecimals("-12.3", 2)).toBe("-12.3");
    expect(limitDecimals("-12.345", 2)).toBe("-12.34");
  });
});
