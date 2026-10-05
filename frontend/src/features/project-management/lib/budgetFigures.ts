/**
 * The report's budget arithmetic, mirrored for the internal tracker (APRAS-102).
 *
 * The backend is the definition and this module is the mirror. Its counterpart
 * is `_budget_html` in `backend/app/services/project_report_service.py`, which
 * computes exactly five figures: `total`, `executed`, `balance`,
 * `executed_pct` (`0.0` for a zero budget, never a division) and
 * `remaining_pct = 100 - executed_pct`.
 *
 * **Nothing here clamps.** `_budget_html` does not: at `executed > total` it
 * prints a negative `remaining_pct` (`-20%`) beside a tank `_cylinder_svg` has
 * emptied. The clamp therefore belongs to the component's geometry, where the
 * backend has it, and a mirror that clamped here would stop being one.
 *
 * Money is formatted by `../utils/currency.ts` and nothing else; percentages by
 * `formatPercent` below and nothing else.
 */

/** The five figures `_budget_html` computes, and no sixth. */
export interface BudgetFigures {
  total: number;
  executed: number;
  /** `total - executed`; negative when the obra is over budget. */
  balance: number;
  /** `executed / total * 100`, or `0` for a zero total budget. */
  executedPct: number;
  /** `100 - executedPct`; **negative** over budget, as the report prints it. */
  remainingPct: number;
}

/**
 * Mirror of `_budget_html`'s five figures.
 *
 * The `total > 0` guard is the backend's `if total else 0.0` branch: it is what
 * lets both implementations promise that no figure is ever a `NaN` and no
 * division by zero is ever attempted.
 */
export const budgetFigures = (
  total: number,
  executed: number,
): BudgetFigures => {
  const executedPct = total > 0 ? (executed / total) * 100 : 0;
  return {
    total,
    executed,
    balance: total - executed,
    executedPct,
    remainingPct: 100 - executedPct,
  };
};

/**
 * Format a percentage the way Python's `format` does: **half to even**.
 *
 * `Number.toFixed` and `Intl.NumberFormat` round half **away from zero**, so
 * they disagree with the report at every exact binary tie: `56.5` prints `56`
 * in Python and `57` through `toFixed`, and the report's own `42.5` physical
 * progress prints `42`, not `43`. The same obra on the same day would show two
 * different numbers on the public report and in the internal tracker.
 *
 * The two modes differ *only* at an exact tie, so the decision is taken on the
 * exact decimal expansion of the double (`toFixed(20)`) rather than by scaling
 * and re-rounding, which would turn a near-tie into one: `2.675` is stored as
 * `2.67499999999999982...` and Python prints `2.67`, which this does too. The
 * reading is sound over the whole percentage domain because the ULP of any
 * value in `-100..100` is about `1e-14`, far above the 20th decimal, so no true
 * non-tie can be flattened into one.
 *
 * `decimals` is documented as `0..2` — the two precisions the report uses.
 *
 * @param value the percentage; non-finite values are answered with Python's own
 *   literals (`nan`, `inf`, `-inf`), **before** any decimal expansion, because
 *   `NaN.toFixed(20)` contains no `"."` and the index arithmetic below would
 *   read past the end of it.
 */
export const formatPercent = (value: number, decimals: number): string => {
  if (Number.isNaN(value)) {
    return "nan";
  }
  if (!Number.isFinite(value)) {
    return value > 0 ? "inf" : "-inf";
  }

  const negative = value < 0;
  const exact = Math.abs(value).toFixed(20);
  const dot = exact.indexOf(".");
  const digits = exact.replace(".", "");
  // Index of the last digit that survives the requested precision.
  const cut = dot - 1 + decimals;
  const kept = digits.slice(0, cut + 1).split("");
  const rest = digits.slice(cut + 1);
  const first = rest.charCodeAt(0) - 48;
  const tailHasValue = /[1-9]/.test(rest.slice(1));
  const lastKept = kept[cut].charCodeAt(0) - 48;
  // Half to even: a bare tie rounds up only when the surviving digit is odd.
  const roundUp =
    first > 5 || (first === 5 && (tailHasValue || lastKept % 2 === 1));

  if (roundUp) {
    for (let index = cut; index >= 0; index -= 1) {
      if (kept[index] === "9") {
        kept[index] = "0";
        if (index === 0) {
          kept.unshift("1");
        }
        continue;
      }
      kept[index] = String(kept[index].charCodeAt(0) - 48 + 1);
      break;
    }
  }

  const joined = kept.join("");
  // `kept` holds one digit per integer place plus `decimals` of them, and the
  // integer part of `toFixed(20)` is never empty ("0.5" expands to "0.50…"), so
  // this length is at least 1 and the integer slice is never the empty string.
  const integerLength = joined.length - decimals;
  const unsigned =
    decimals === 0
      ? joined
      : `${joined.slice(0, integerLength)}.${joined.slice(integerLength)}`;
  // Back through `toFixed` only to normalise a leading zero or a carried digit;
  // the rounding decision was already taken above, and this cannot change it.
  return (negative ? "-" : "") + Number(unsigned).toFixed(decimals);
};
