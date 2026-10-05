/**
 * The frontend mirror of `planned_to_date` (APRAS-102).
 *
 * Counterpart: `backend/app/services/project_report_service.py::planned_to_date`
 * — the `pct` of the latest point whose `month` is `<=` the current month, `0`
 * when every point is in the future, and `null` for *no curve*, which the
 * backend reaches for a `null` payload, an empty list, a non-list or **any**
 * single malformed point.
 *
 * The curve below is `tests/test_project_stage_detail.PLANNED_CURVE`, the one
 * that produced the committed report baseline. All three of its points are in
 * 2020, so the "latest past point" selection has the same forward stability the
 * backend claims for itself and this pin cannot rot with the calendar.
 */
import { afterEach, describe, expect, it, vi } from "vitest";

import { plannedProgress } from "../lib/plannedProgress";

/** `test_project_stage_detail.PLANNED_CURVE`, restated. */
const PLANNED_CURVE = [
  { month: "2020-01", pct: 8.0 },
  { month: "2020-02", pct: 31.5 },
  { month: "2020-03", pct: 64.0 },
];

/** Any month after the curve, so "latest past point" is the last one. */
const AFTER_THE_CURVE = new Date("2026-09-15T12:00:00Z");

describe("plannedProgress", () => {
  afterEach(() => {
    // The TZ cases below set `process.env.TZ`; the restore is what keeps a
    // future `isolate: false` from leaking a zone into this tree's other
    // date-sensitive suites (`DueDateBadge`, `TaskCard`, the purchase
    // formatters), none of which sets TZ itself.
    vi.unstubAllEnvs();
  });

  it("selects the latest point whose month has already passed", () => {
    expect(plannedProgress(PLANNED_CURVE, AFTER_THE_CURVE)).toBe(64);
    // The mutation, so the case cannot pass by accident: drop the last point
    // and the answer must move to the new latest one.
    expect(plannedProgress(PLANNED_CURVE.slice(0, 2), AFTER_THE_CURVE)).toBe(
      31.5,
    );
  });

  it("selects the latest past point out of a mixed past/future curve", () => {
    const mixed = [...PLANNED_CURVE, { month: "2099-01", pct: 100 }];

    expect(plannedProgress(mixed, AFTER_THE_CURVE)).toBe(64);
    // Mutating the future point changes nothing -- which is the claim. Mutating
    // it into a past one does change the answer.
    expect(
      plannedProgress([...PLANNED_CURVE, { month: "2099-01", pct: 7 }], AFTER_THE_CURVE),
    ).toBe(64);
    expect(
      plannedProgress([...PLANNED_CURVE, { month: "2021-01", pct: 77 }], AFTER_THE_CURVE),
    ).toBe(77);
  });

  it("returns 0 when every point is still in the future", () => {
    const future = [
      { month: "2099-01", pct: 10 },
      { month: "2099-02", pct: 20 },
    ];

    expect(plannedProgress(future, AFTER_THE_CURVE)).toBe(0);
    // Not `null`: `0` is "the plan says nothing has been scheduled yet", which
    // the bar draws as a marker at zero, where `null` draws no marker at all.
    expect(plannedProgress(future, AFTER_THE_CURVE)).not.toBeNull();
    // And the mutation: make the first point past and the answer leaves 0.
    expect(
      plannedProgress([{ month: "2020-01", pct: 10 }, future[1]], AFTER_THE_CURVE),
    ).toBe(10);
  });

  it("reads no curve out of a null, an empty list or a non-list", () => {
    expect(plannedProgress(null, AFTER_THE_CURVE)).toBeNull();
    expect(plannedProgress(undefined, AFTER_THE_CURVE)).toBeNull();
    expect(plannedProgress([], AFTER_THE_CURVE)).toBeNull();
    expect(plannedProgress({}, AFTER_THE_CURVE)).toBeNull();
    expect(plannedProgress("2020-01", AFTER_THE_CURVE)).toBeNull();
    expect(plannedProgress(42, AFTER_THE_CURVE)).toBeNull();
    // The mutation: the same container holding one good point is a curve.
    expect(plannedProgress([PLANNED_CURVE[0]], AFTER_THE_CURVE)).toBe(8);
  });

  it("lets one malformed point invalidate the whole curve", () => {
    // Strict on purpose, as the backend docstring says: a partially-read
    // schedule would silently under- or over-state the plan, which is the one
    // number the síndico compares the measurement against.
    const bad: unknown[] = [
      [...PLANNED_CURVE, { month: "nope", pct: 1 }],
      [...PLANNED_CURVE, { month: "2020-4", pct: 1 }],
      [...PLANNED_CURVE, { month: 202004, pct: 1 }],
      [...PLANNED_CURVE, { month: "2020-04" }],
      [...PLANNED_CURVE, { month: "2020-04", pct: "70" }],
      [...PLANNED_CURVE, { month: "2020-04", pct: true }],
      [...PLANNED_CURVE, { month: "2020-04", pct: Number.NaN }],
      [...PLANNED_CURVE, null],
      [...PLANNED_CURVE, "2020-04"],
      [{}],
    ];

    for (const payload of bad) {
      expect(plannedProgress(payload, AFTER_THE_CURVE), String(payload)).toBeNull();
    }
    // The mutation that proves the strictness is about the bad point and not
    // about the length: the same curve with a *well-formed* fourth point reads.
    expect(
      plannedProgress([...PLANNED_CURVE, { month: "2020-04", pct: 70 }], AFTER_THE_CURVE),
    ).toBe(70);
  });

  // ---------------------------------------------------------------------------
  // The two UTC-boundary cases. Every case above returns the same value under
  // `getMonth` as under `getUTCMonth`, so without these two the hazard ships
  // unguarded: in a negative-offset zone the local month lags UTC for a few
  // hours at every month boundary, and in that window a local-calendar cursor
  // picks a different curve point from the one the report printed.
  //
  // `planned_to_date` compares against `clock.today_utc().strftime("%Y-%m")`,
  // and `clock.py` is explicit that the UTC calendar is deliberate. This is not
  // the APRAS-120 instant contract: a `"YYYY-MM"` string carries no offset, and
  // neither of these components renders a date at all.
  // ---------------------------------------------------------------------------

  it("reads the UTC month in a negative-offset zone, not the local one", () => {
    vi.stubEnv("TZ", "America/Sao_Paulo"); // UTC-3
    const today = new Date("2020-03-01T00:30:00Z");

    // Sanity: the zone really is in effect and really does lag, so the case is
    // not vacuous on a CI box that ignored TZ.
    expect(today.getMonth()).toBe(1); // local February
    expect(today.getUTCMonth()).toBe(2); // UTC March

    // A local-calendar read sees 2020-02-29 and returns 31.5.
    expect(plannedProgress(PLANNED_CURVE, today)).toBe(64);
  });

  it("reads the UTC month in a positive-offset zone, not the local one", () => {
    vi.stubEnv("TZ", "Europe/Berlin"); // UTC+2 in summer time
    const today = new Date("2020-03-31T23:30:00Z");
    const curve = [...PLANNED_CURVE, { month: "2020-04", pct: 80 }];

    expect(today.getMonth()).toBe(3); // local April
    expect(today.getUTCMonth()).toBe(2); // UTC March

    // A local-calendar read sees April and returns 80.
    expect(plannedProgress(curve, today)).toBe(64);
  });
});
