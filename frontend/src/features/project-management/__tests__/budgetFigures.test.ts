/**
 * The frontend mirror of the report's budget arithmetic (APRAS-102).
 *
 * `backend/app/services/project_report_service.py::_budget_html` computes five
 * figures and prints them; this suite pins the TypeScript copy against that
 * one, including the rounding mode, which is the one place the two languages
 * genuinely disagree.
 */
import { describe, expect, it } from "vitest";

import { budgetFigures, formatPercent } from "../lib/budgetFigures";

describe("budgetFigures", () => {
  it("mirrors _budget_html's five figures on a normal obra", () => {
    const figures = budgetFigures(480000, 204000);

    expect(figures.total).toBe(480000);
    expect(figures.executed).toBe(204000);
    // `saldo = total - executed`, asserted on a value where a sign error or a
    // swapped operand order would show (276000 vs -276000).
    expect(figures.balance).toBe(276000);
    expect(figures.executedPct).toBeCloseTo(42.5, 10);
    expect(figures.remainingPct).toBeCloseTo(57.5, 10);
  });

  it("defines a zero budget as 0 % executed instead of dividing", () => {
    // `executed_pct = float(executed / total * 100) if total else 0.0` -- the
    // guard that lets the backend promise "never a division by zero and never
    // a NaN". The mirror must have it too, and on a *non-zero* executed, which
    // is the shape a division would blow up on.
    const figures = budgetFigures(0, 1000);

    expect(figures.executedPct).toBe(0);
    expect(figures.remainingPct).toBe(100);
    for (const [name, value] of Object.entries(figures)) {
      expect(Number.isNaN(value), `${name} is NaN`).toBe(false);
      expect(Number.isFinite(value), `${name} is not finite`).toBe(true);
    }
  });

  it("returns a negative remainingPct over budget, because the backend does", () => {
    // `_budget_html` itself never clamps: at `executed > total` it prints
    // `-20%` beside a tank `_cylinder_svg` has emptied. A mirror that silently
    // clamped here would stop being one, and would hide the single fact the
    // síndico needs. The clamp lives in the component's geometry.
    const figures = budgetFigures(100000, 120000);

    expect(figures.remainingPct).toBeLessThan(0);
    expect(figures.remainingPct).toBeCloseTo(-20, 10);
    expect(figures.balance).toBe(-20000);
    expect(figures.executedPct).toBeCloseTo(120, 10);
    for (const [name, value] of Object.entries(figures)) {
      expect(Number.isNaN(value), `${name} is NaN`).toBe(false);
    }
  });
});

describe("formatPercent", () => {
  it("rounds half to even, as Python's format does and toFixed does not", () => {
    // Each expectation is what `f"{v:.Nf}"` prints, measured in CPython.
    // `toFixed` fails five of the seven: only `57.5` and `2.675` agree.
    expect(formatPercent(56.5, 0)).toBe("56"); // toFixed -> "57"
    expect(formatPercent(2.5, 0)).toBe("2"); // toFixed -> "3"
    expect(formatPercent(42.5, 0)).toBe("42"); // toFixed -> "43"
    expect(formatPercent(57.5, 0)).toBe("58"); // both agree
    expect(formatPercent(42.25, 1)).toBe("42.2"); // toFixed -> "42.3"
    // Not a tie at all: the stored double is 2.67499999999999982..., below the
    // tie, so Python rounds down. A scale-then-round implementation turns it
    // into one and prints "2.68".
    expect(formatPercent(2.675, 2)).toBe("2.67");
    // The cylinder prints negative percentages over budget, so the negative
    // tie is in the domain: `format(-20.5, '.0f')` is '-20', `toFixed` -21.
    expect(formatPercent(-20.5, 0)).toBe("-20");
  });

  it("guards the non-finite inputs before expanding any decimals", () => {
    // `NaN.toFixed(20)` is "NaN" -- no ".", so index arithmetic over the
    // expansion throws or silently reads garbage. The guard must therefore come
    // first, and it returns Python's own literals so the helper stays a mirror
    // of `format` across its whole domain.
    expect(formatPercent(Number.NaN, 0)).toBe("nan");
    expect(formatPercent(Number.POSITIVE_INFINITY, 0)).toBe("inf");
    expect(formatPercent(Number.NEGATIVE_INFINITY, 0)).toBe("-inf");
    expect(formatPercent(Number.NaN, 2)).toBe("nan");
  });

  it("agrees with toFixed everywhere that is not an exact tie", () => {
    // The domain note of the spec: the ULP of any value in -100..100 is about
    // 1e-14, far above the 20th decimal, so no true non-tie is flattened into
    // one. This case is what would catch a half-to-even implementation that
    // broke the ordinary cases while fixing the ties.
    for (const value of [0, 1, 42.4, 42.6, 99.99, 100, -0.4, 63.7, 8]) {
      for (const decimals of [0, 1, 2] as const) {
        expect(formatPercent(value, decimals)).toBe(value.toFixed(decimals));
      }
    }
  });
});
