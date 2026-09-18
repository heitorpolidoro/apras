/**
 * Money input constraints (APRAS-64, Decision 5).
 *
 * The screen prevents a third decimal from ever being typed, pasted or sent.
 * The backend stays the tolerant layer -- it still accepts a third decimal
 * from curl or an older client and quantizes it half-up -- so this is a
 * constraint on the form, never a change to the API contract.
 *
 * Why a guard and not the native `step`: `step` is consulted only by native
 * constraint validation, and every one of these modals submits through an
 * `onClick` handler rather than a native `<form>` submit, so a step violation
 * blocks nothing. `step` never prevents a character from being typed either.
 * It is kept as the widget hint that drives the spinner and the mobile
 * keypad; this helper is what enforces the rule.
 */

/** Two decimal places: every amount in reais. */
export const MONEY_DECIMALS = 2;

/**
 * Four decimal places: `fine_fee_multiplier` is a ratio stored
 * `NUMERIC(8, 4)`, so a bylaw can say 12,5% of the condo fee (`0.125`).
 * Limiting it to two would truncate that to a whole percent.
 */
export const RATIO_DECIMALS = 4;

/**
 * Cut the fractional part of `raw` to at most `places` digits.
 *
 * **Truncates, never rounds**: `"2.999"` becomes `"2.99"`, not `"3.00"`.
 * Rounding mid-keystroke would be hostile -- the user is still typing, and a
 * digit they have not finished entering must not change the digits to its
 * left. (The backend rounds half-up, but the two rules never observe the same
 * event: one runs per keystroke, the other once on a submitted value.)
 *
 * Both `.` and `,` are accepted as the decimal separator and the one the user
 * typed is preserved. A value with no separator, with too few fractional
 * digits, or half typed (`""`, `"2."`, `"-"`, `"2,"`) is returned unchanged,
 * so a value is never destroyed mid-keystroke.
 */
export function limitDecimals(raw: string, places: number): string {
  const separatorIndex = Math.max(raw.indexOf("."), raw.indexOf(","));
  if (separatorIndex < 0) return raw;

  const fraction = raw.slice(separatorIndex + 1);
  if (fraction.length <= places) return raw;

  return raw.slice(0, separatorIndex + 1 + places);
}
