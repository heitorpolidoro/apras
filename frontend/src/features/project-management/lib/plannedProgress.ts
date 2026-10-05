/**
 * The planned physical progress as of the current month (APRAS-102).
 *
 * Mirror of `planned_to_date` in
 * `backend/app/services/project_report_service.py`: the `pct` of the **latest**
 * point whose `month` is `<=` the current month, `0` when every point is still
 * in the future, and `null` — *no curve* — for a `null` payload, an empty list,
 * a non-list or **any** single malformed point. Strict on purpose, and the
 * backend docstring says why: a partially-read schedule would silently under-
 * or over-state the plan, which is the one number the síndico compares the
 * measurement against.
 *
 * **The month is read in UTC, and that is deliberate.** `planned_to_date`
 * compares against `clock.today_utc().strftime("%Y-%m")`, and `clock.py` is
 * explicit that the UTC calendar is the contract. A local-calendar read here
 * would lag UTC for a few hours at every month boundary in a negative-offset
 * zone, and in that window this helper would pick a different curve point from
 * the one the public report printed — an intermittent, unreproducible
 * disagreement between two views of the same obra.
 *
 * This is *not* the APRAS-120 instant contract (`schemas/base.py`): that
 * governs instants returned with an explicit offset and rendered in the
 * browser's zone. A `"YYYY-MM"` string in a JSON column carries no offset and
 * gets none, and this module renders no date at all.
 *
 * @param payload the raw `planned_progress_json` value, judged here and
 *   nowhere else — this is the single place that decides whether a stored curve
 *   is usable.
 * @param today an **instant**, not a calendar date: it carries no calendar of
 *   its own and is read only through `getUTCFullYear`/`getUTCMonth`.
 *   `getFullYear`, `getMonth`, `toLocaleDateString` and `Intl.DateTimeFormat`
 *   are forbidden in this module.
 */
export const plannedProgress = (
  payload: unknown,
  today: Date = new Date(),
): number | null => {
  if (!Array.isArray(payload) || payload.length === 0) {
    return null;
  }

  const current = `${today.getUTCFullYear()}-${String(
    today.getUTCMonth() + 1,
  ).padStart(2, "0")}`;

  let best: number | null = null;
  let bestMonth = "";

  for (const point of payload) {
    if (!point || typeof point !== "object") {
      return null;
    }
    const { month, pct } = point as { month?: unknown; pct?: unknown };
    if (typeof month !== "string" || !/^\d{4}-\d{2}$/.test(month)) {
      return null;
    }
    // `typeof true` is `"boolean"`, so a boolean `pct` is refused here rather
    // than coerced into 1; `NaN` is a number and must be refused explicitly.
    if (typeof pct !== "number" || Number.isNaN(pct)) {
      return null;
    }
    // Zero-padded `"YYYY-MM"` strings order lexicographically exactly as
    // months order, which is what lets both languages compare them as strings.
    if (month <= current && month >= bestMonth) {
      best = pct;
      bestMonth = month;
    }
  }

  // Every point in the future: the plan exists and says zero so far, which the
  // bar draws as a marker at 0 — distinct from `null`, which draws no marker.
  return best === null ? 0 : best;
};
