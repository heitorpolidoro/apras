# APRAS-102 — QA review

**Task:** Show the report's balance cylinder and planned-vs-actual bar in the internal construction tracker
**Commit under test:** `6be21c8`, on top of `ab54bf8` (current `master`), in worktree
`/Users/heitor/workspace/apras/.claude/worktrees/agent-a42d9bcf75171b79e`
**Diff:** 18 files, +1650 / −9 (confirmed via `git show --stat HEAD`)
**Date:** 2026-10-05

VERDICT: APPROVED

---

## How this was verified

Everything below was observed in the worktree. Each mutation followed the
prescribed cycle: pristine file copied to the scratchpad, mutated, suite run,
file restored, restoration confirmed with `cmp`. The worktree ends at `HEAD`
`6be21c8`, `git diff HEAD --stat` empty, `git status --porcelain` showing only
the developer's own untracked `docs/reviews/APRAS-102-developer-report.md`.
No `git stash`, no staging, no commit, no rebase. The baseline HTML was never
edited — tampering was done on throwaway copies (`__qa_tamper_a.html`,
`__qa_tamper_b.html`) which were deleted, and the original verified byte-equal
afterwards with `cmp`.

---

## Expected Results Checked

### R1 — `planned_progress_json` on the detail payload only, unwritable

- [x] **Verified** via the four new cases in `backend/tests/test_projects.py`,
  which drive the real ASGI app through `TestClient`, plus a non-vacuity
  mutation of my own.
  - `uv run pytest tests/test_projects.py tests/test_project_stage_detail.py tests/test_project_report.py -q`
    → **194 passed**.
  - `GET /api/v1/projects/{id}` with a seeded curve returns it verbatim
    (`test_project_detail_returns_the_stored_planned_curve`); with no curve the
    key is **present and `null`**
    (`test_project_detail_returns_null_for_a_project_without_a_curve`).
  - `GET /api/v1/projects` items carry no such key
    (`test_project_list_items_carry_no_planned_curve`) — structurally guaranteed
    because the field is declared on `ProjectDetailRead`, not `ProjectRead`.
  - `PUT /api/v1/projects/{id}` with `{"planned_progress_json": [{"month":"2099-01","pct":100.0}]}`
    answers **200**, and both the ORM re-read (after `session.expire_all()`) and
    the HTTP re-read still show the seeded curve.
  - **Non-vacuity mutation:** removed the explicit
    `planned_progress_json=project.planned_progress_json` pass from
    `ProjectService.get_project_detail`. Result:
    `test_project_detail_returns_the_stored_planned_curve` and
    `test_put_ignores_a_planned_curve_body_and_leaves_the_column_unchanged`
    both **failed**; the `null` case correctly still passed. So the explicit
    pass is load-bearing and the tests notice its absence. Restored, `cmp` clean.

### R2 — balance cylinder, clamp on two named nodes, unclamped printed percentage

- [x] **Verified** via `ConstructionTrackerPage.figures.test.tsx` (full page,
  clicks "Ver Detalhes"), `ProjectBudgetCylinder.test.tsx`,
  `budgetFigures.test.ts`, and three mutations.
  - Page-level: after selecting a project, `cylinder-fill` and
    `cylinder-surface` are both in the document; the `% executado` row reads
    `42.5%` and the cylinder prints `58%` for 480000/204000.
  - Filled proportion is the remaining-budget percentage:
    `filled = clamp(0,100, 100 − executed/total×100)`, and `total === 0` yields
    `executedPct === 0` (the backend's `if total else 0.0` branch), hence a full
    tank.
  - **Helper clause**: `budgetFigures(100000, 120000).remainingPct` is asserted
    `toBeLessThan(0)` **and** `toBeCloseTo(-20, 10)` — a genuinely negative
    value, mirroring the unclamped backend. At `total = 0, executed = 1000`
    every returned field is asserted non-`NaN` **and** finite, iterated over
    `Object.entries(figures)` so a newly added field is covered too.
  - **Exactly-one assertions**: the test collects
    `container.querySelectorAll('[data-testid="…"]')` for both ids and asserts
    `toHaveLength(1)` *before* parsing anything.
    - Mutation: renamed `cylinder-surface` → `cylinder-liquid`. Both geometry
      cases **failed** with `expected [] to have a length of 1 but got +0`.
    - Mutation: duplicated the fill `path`. Both cases **failed** the other way:
      `expected [ …(2) ] to have a length of 1 but got 2`.
  - **Clamp**: mutation replacing `Math.max(0, Math.min(100, remainingPct))`
    with the raw `remainingPct` made the over-budget case **fail** with
    `expected 164 to be 140` — exactly the predicted unclamped `yStart`.
  - **Coordinates**: at `executed > total`, `yStart === 140`, `h === 0`,
    `cylinder-surface`'s `cy === 140`. At `total = 0`, `yStart === 20`,
    `h === 120`. Both cases range-check `20..140` over
    `for (const y of [yStart, surfaceCy])` — **only** those two values. `h` is
    asserted exactly but not range-checked; the move-to `x` (`10`) and the arc's
    `rx 50 ry 12` are never asserted. The assertion is as narrow as R2 requires,
    not widened.
  - **Printed percentage**: `screen.getByText("-20%")` and
    `printed.getAttribute("class")` contains `text-destructive`. The test reads
    `getAttribute("class")` rather than `.className` precisely because on an SVG
    node the latter is an `SVGAnimatedString` and a `toContain` over it would
    assert nothing — a correct and non-obvious detail.

### R3 — four labelled money lines

- [x] **Verified** via `ProjectBudgetCylinder.test.tsx` ("shows the four
  labelled money lines, with saldo and one decimal"): all of
  `orçamento previsto`, `executado`, `saldo`, `% executado` resolve via
  `screen.getByText`; `saldo` for 480000/204000 renders `276.000,00` (not
  `-276.000,00`, so a swapped operand order would fail); `% executado` renders
  `42.5%` — one decimal, via `formatPercent(executedPct, 1)`. The page-level
  test reads `% executado` through its own row's label, because the physical
  gauge on the same screen also prints `42.5%` and an unscoped query would match
  both — correctly scoped.

### R4 — half-to-even percentage formatting

- [x] **Verified** via `budgetFigures.test.ts`, two mutations, and an
  independent CPython cross-check.
  - All seven values asserted: `(56.5,0)→"56"`, `(2.5,0)→"2"`, `(42.5,0)→"42"`,
    `(57.5,0)→"58"`, `(42.25,1)→"42.2"`, `(2.675,2)→"2.67"`, `(-20.5,0)→"-20"`.
    I re-derived all seven in CPython 3 (`format(v, '.Nf')`) and every one
    matches the asserted string.
  - Non-finite guard asserted: `NaN→"nan"`, `Infinity→"inf"`,
    `-Infinity→"-inf"` (plus `NaN` at `decimals = 2`), and CPython's
    `format(float('nan'),'.0f')` is indeed `nan`/`inf`/`-inf`.
  - **Mutation A** — moved the non-finite guard from the top of `formatPercent`
    to just before the `if (roundUp)` block, i.e. after the decimal expansion.
    "guards the non-finite inputs before expanding any decimals" **failed
    loudly** with `TypeError: Cannot read properties of undefined (reading
    'charCodeAt')` — `NaN.toFixed(20)` is `"NaN"`, so `indexOf(".")` is `-1` and
    the index arithmetic reads past the end. The guard's position is pinned.
  - **Mutation B** — replaced the whole body with `value.toFixed(decimals)`.
    "rounds half to even…" **failed** at `expected '57' to be '56'`, and the
    non-finite case **failed** at `expected 'NaN' to be 'nan'`. Vitest stops at
    the first failing `expect` inside an `it`, so I verified the remaining named
    divergences directly in Node: `56.5→"57"`, `2.5→"3"`, `42.5→"43"`,
    `-20.5→"-21"` and `42.25→"42.3"` all diverge from the asserted values
    (`57.5` and `2.675` agree, as the test's own comments say). All four named
    cases would therefore fail.
  - **Card level**: `ProjectBudgetCylinder.test.tsx` renders
    `total = 400000, executed = 174000` (remaining 56.5) and asserts
    `getByText("56%")` present **and** `queryByText("57%")` absent.

### R5 — planned-vs-actual bar

- [x] **Verified** via `PhysicalProgressPlannedVsActualBar.test.tsx` and
  `ConstructionTrackerPage.figures.test.tsx`.
  - Page-level: the bar is driven by `selectedProjectDetail.planned_progress_json`
    straight off `useProjectDetail`'s payload; the planned label reads `64%`,
    realized `42%`, the gap carries `bg-destructive/70` and the below-plan text
    is present.
  - `planned = 64, realized = 42.5`: gap `className` contains
    `bg-destructive/70`, `gap.style.left === "42.5%"`,
    `gap.style.width === "21.5%"` — unrounded, as required — realized segment
    width `42.5%`, marker `left: 64%`, and `getByText("abaixo do previsto")`
    present. The track's `aria-label` also names the state.
  - `planned = 42, realized = 64`: gap contains `bg-primary/30`, explicitly
    **not** `bg-destructive/70`, and `queryByText("abaixo do previsto")` absent.
  - All four parts (realized segment, gap, marker, `previsto`/`realizado`
    labels) asserted present.

### R6 — UTC month selection

- [x] **Verified** via `plannedProgress.test.ts` and the prescribed mutation.
  - Both boundary cases assert the zone is really in effect first
    (`today.getMonth()` vs `today.getUTCMonth()`), so neither is vacuous on a
    box that ignored `TZ`.
  - **Mutation**: replaced `getUTCFullYear`/`getUTCMonth` with
    `getFullYear`/`getMonth`. **Both** cases failed, with exactly the predicted
    values:
    - `America/Sao_Paulo`, `2020-03-01T00:30:00Z` →
      `AssertionError: expected 31.5 to be 64`
    - `Europe/Berlin`, `2020-03-31T23:30:00Z` →
      `AssertionError: expected 80 to be 64`
    - All 5 other cases in the file passed under the mutation, confirming these
      two are the only guards and that they are the right ones.
  - Restored, `cmp` clean. The suite also restores `TZ` in `afterEach` via
    `vi.unstubAllEnvs()`, so no zone leaks into other date-sensitive suites.

### R7 — four degenerate payloads render positively

- [x] **Verified** via the `it.each` block over `null`, `[]`, `{}` and
  `[{"month":"nope","pct":1}]`, and the prescribed mutation.
  - Each row asserts the realized segment is present **with a non-zero width**
    (`"42.5%"` for `physical_progress_pct = 42.5`), the plan label is `"—"`, and
    `progress-gap` and `progress-marker` are both absent (plus the below-plan
    text absent).
  - **Mutation**: made the realized segment conditional on `hasCurve`. **All
    four** rows failed with
    `TestingLibraryElementError: Unable to find an element by: [data-testid="progress-realized"]`.
    The vacuous "renders without throwing" form is ruled out.
  - Restored, `cmp` clean.

### R8 — baseline HTML parity pin

- [x] **Verified** via `reportFigureParity.test.tsx` and three mutations on
  throwaway copies.
  - The case parses `backend/tests/data/report_page_null_detail_baseline.html`
    (imported `?raw` through the `../backend/tests/data` fs allowance already in
    `vitest.config.ts`), parses the baseline's own
    `Orçamento previsto` / `Executado` into `480000` / `204000`, renders
    `ProjectBudgetCylinder` from those two numbers, and compares the rendered
    `saldo` and `% executado` against the baseline's own strings, pinned to
    `R$ 276.000,00` and `42.5%`; the remaining percentage from
    `.cyl .txt strong` is pinned to `58%` and asserted present in the render.
  - **Non-degeneracy, asserted before any comparison**: `BUDGET_ROWS` has
    length 4; each of the four rows has exactly one `strong`;
    `.cyl .txt strong` matches exactly 1 — five nodes, each exactly once. The
    four labels are asserted by position, the two parsed inputs are asserted
    `480000` and `204000`, and each of the three expected strings is asserted
    non-empty and `toMatch(/\d/)`.
  - **Tamper A** (copy with the cylinder's `<strong>58%</strong>` removed):
    the file **errored at module load** with the *named* error —
    `report_page_null_detail_baseline.html matched 0 nodes for `.cyl .txt strong`,
    expected exactly 1; the APRAS-102 parity pin cannot read the baseline's
    figures.` — and reported "no tests". Not a vacuous pass.
  - **Tamper B** (copy with the `Saldo` row's `strong` removed): the
    non-degeneracy case **failed** (`expected  to have a length of 1 but got +0`)
    and the comparison case **failed** with the other named error
    `… has no `strong` in budget row 2; the APRAS-102 parity pin cannot read the
    baseline's figures.`
  - **Whitespace normalisation is load-bearing**: on a copy of the test with
    `normaliseSpaces` reduced to the identity, the comparison **failed** with
    `expected 'R$ 276.000,00' to be 'R$ 276.000,00'` — the invisible NBSP vs
    space difference, exactly as predicted. Reading the implementation, the
    mapping is only U+00A0→U+0020 and U+202F→U+0020, built from code points, and
    changes nothing else: digits, thousands separators, decimal comma and the
    `R$` prefix are still compared character for character.
  - **Second case**: `plannedProgress(PLANNED_CURVE)` (the restated
    `test_project_stage_detail.PLANNED_CURVE`) equals the baseline's
    `.pv .tag.plan b` → `64%`; and the bar rendered at
    `physical_progress_pct = 42.5` reports `42%`, compared against the
    baseline's own `.pv .tag.real b`.
  - The real baseline was never edited: `cmp` against a pre-run copy clean, and
    its blob id is unchanged (see R10). Both tampered HTML copies and both
    throwaway test files were deleted.

### R9 — semantic theme tokens only

- [x] **Verified** by reading both new components and by running the guards.
  - Every class in `ProjectBudgetCylinder.tsx` and
    `PhysicalProgressPlannedVsActualBar.tsx` is a semantic token:
    `bg-card`, `border-border`, `text-foreground`, `text-muted-foreground`,
    `fill-muted`, `stroke-border`, `fill-primary`, `stroke-primary-foreground`,
    `text-primary-foreground`, `text-destructive`, `bg-muted`, `bg-primary`,
    `bg-destructive/70`, `bg-primary/30`, `bg-foreground`. No raw palette class.
  - `themeTokenMigration.exceptions.json` is **not in the diff at all**
    (confirmed against the 18-file stat) and still holds **882** entries
    (counted with `json.load`).
  - `npx vitest run src/__tests__/themeTokenMigration.test.ts
    src/__tests__/brandTextRole.test.ts src/__tests__/themeContrast.test.ts` (run
    together with the parity and provenance guards): **5 files passed, 246 tests
    passed**.
  - The only `themeTokenMigration.test.ts` changes are bookkeeping: the
    projects-directory file census 10→12 and total 16→18, and three pinned line
    numbers in `ConstructionTrackerPage.tsx` shifted by +3 for the three added
    import lines. No class sets changed.

### R10 — the report service and the baseline are untouched

- [x] **Verified** straight from the commit.
  - `git show HEAD --stat | grep report_service` → no match;
    `backend/app/services/project_report_service.py` appears in no hunk, and its
    blob id is identical at `ab54bf8` and `6be21c8`
    (`79b1ca139f1a4ce895f9420fba08a2e11fd0cfc7`).
  - `backend/tests/data/report_page_null_detail_baseline.html` blob id identical
    at both commits (`cdee25b07a10bc2797d3ce01a2921c543c9b29f3`) — byte-identical.
  - `uv run pytest tests/test_projects.py tests/test_project_stage_detail.py
    tests/test_project_report.py -q` → **194 passed**, which includes
    `test_project_stage_detail.py` and `test_project_report.py`.

### R11 — i18n parity

- [x] **Verified** via the locale diff and `parity.test.ts`.
  - Both `pt.json` and `en.json` gain the same two blocks with the same keys:
    `projects.cylinder.{title,total,executed,balance,executedPct,remaining,remainingNote,ariaLabel}`
    and
    `projects.plannedBar.{title,planned,realized,behind,start,finish,ariaLabel,ariaLabelBehind,ariaLabelNoCurve}`.
  - The below-plan state label is present in both: `behind` →
    `"abaixo do previsto"` (pt) / `"below plan"` (en).
  - `src/i18n/__tests__/parity.test.ts` **passes** (part of the 5-file run above
    and of the full suite).

### R12 — full suite, coverage thresholds, lint not regressed

- [x] **Verified**, including the interaction with the new `ab54bf8` guard.
  - `npm run test:coverage` run **three times** from the worktree's `frontend/`.
    Every run: exit `0`, **197 test files passed (197)**, **2576 tests passed
    (2576)**, **0 failed**.
  - Coverage, identical across runs: Statements **91.62%** (≥80), Branches
    **85.48%** (≥76), Functions **87.88%** (≥78), Lines **92.33%** (≥80). All
    four thresholds in `frontend/vitest.config.ts` met with wide margin.
  - **The `ab54bf8` guard**: `frontend/src/__tests__/docsColourProvenance.test.ts`
    is present at `HEAD` and passes, both inside the three full runs and in a
    targeted run alongside `themeTokenMigration`, `brandTextRole`,
    `themeContrast` and `i18n/parity`. **No interaction with this change** was
    observed. That is consistent with the change's nature: it publishes no
    colour figure, adds no entry to the exceptions ledger, and touches
    `themeTokenMigration.test.ts` only for line-number and file-census
    bookkeeping.
  - **Lint, measured myself, same invocation on both commits** — `npx eslint . -f json`
    run from `frontend/`, totals summed over the JSON with Python:
    - **base `ab54bf8`**: tree extracted with
      `git archive ab54bf8 frontend | tar -x` into the scratchpad, the
      worktree's `node_modules` symlinked in → **370 errors, 2 warnings, 66
      files with findings**, 466 files linted.
    - **HEAD `6be21c8`**: → **370 errors, 2 warnings, 66 files with findings**,
      474 files linted.
    - Equal, so no regression. The 8 extra linted files are exactly the new
      sources and suites, and each of the twelve APRAS-102-touched frontend
      files reports **0 errors / 0 warnings** individually — so the identical
      total is genuinely "nothing added", not a cancellation.
    - `npm run lint` is literally `eslint .` in `package.json`, i.e. the same
      invocation; running it confirmed the same result.

---

## The reported lone-failure flake

Asked about explicitly, so recorded explicitly. I ran `npm run test:coverage`
**three** times in full. All three reported `Test Files 197 passed (197)` /
`Tests 2576 passed (2576)` with exit `0` and byte-identical coverage figures.
I also ran the task's own suites individually many times over the course of the
mutation cycles (each restored run green). **The `1 failed | 2561 passed`
observation did not reproduce for me at all**, and the test count has since moved
(2561 → 2576) because this change and the rebase onto `ab54bf8` both added tests,
so the earlier observation was on a different tree. I am not waving it away: it
remains an unexplained single observation on an older tree, worth watching in CI.
It is not attributable to this change on the evidence available, and nothing I
ran reproduced it, so it does not block.

---

## Blocking Findings

None.

---

## Suggestions

1. `ProjectBudgetCylinder` emits the fill `d` and the surface `cy` through
   `toFixed(1)`, so at `total = 0` the surface `cy` is the string `"20.0"` and
   the geometry assertions pass through `Number(...)`. That is fine, but the two
   coordinates are produced by two independent `toFixed(1)` calls on the same
   `surfaceY`; a single precomputed string would make it structurally impossible
   for the fill and the surface to ever disagree. Cosmetic.
2. The `labelY = Math.max(surfaceY + 22, TOP + 30)` rule that keeps the printed
   number off the rim is not asserted anywhere. It is presentation only and
   carries no figure, so it is not a gap in the expected results — but a single
   assertion that `labelY` stays within the `viewBox` would stop a future
   geometry edit from pushing the number out of the SVG unnoticed.
3. `formatPercent` documents `decimals` as `0..2` but does not enforce it. A
   caller passing `3` would read one digit past where the `toFixed(20)` expansion
   is still meaningful for values near `100`. Both current call sites pass `0` or
   `1`, so this is latent only.

---

**VERDICT: APPROVED**

Blocking failures: None
