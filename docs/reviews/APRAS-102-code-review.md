# APRAS-102 — code review (round 1)

Task: *Show the report's balance cylinder and planned-vs-actual bar in the
internal construction tracker.*

Subject: `git -C /Users/heitor/workspace/apras/.claude/worktrees/agent-a42d9bcf75171b79e diff --cached`
— **18 files, +1650 / −9**, on `worktree-agent-a42d9bcf75171b79e` rebased onto
`master` = `2124432`.

Spec: `docs/tasks/APRAS-102-spec.md`. Mock: `docs/tasks/APRAS-102-mock.html`.
Developer report: `<worktree>/docs/reviews/APRAS-102-developer-report.md`.
Contract reference read first:
`/Users/heitor/workspace/meridian/plugin/plugins/meridian/references/schema.md`
(no board write made by this review; the orchestrator owns every field).

Every conclusion below is from a run or a count, not from the developer's prose.
All mutations were done copy-first into the session scratchpad, run, restored,
and verified with `cmp`; the worktree ends byte-identical to how it was found
(`git diff --stat` empty, the only untracked path still the developer's own
report).

---

## 1. The one thing beyond what R9 authorised: the file census

R9 permits exactly one edit to the theme-token guard — the pinned
`ConstructionTrackerPage.tsx` line numbers bumped by the inserted import lines,
class sets unchanged — plus `themeTokenMigration.exceptions.json` gaining no
entry and staying at 882. The developer also moved a **file census** for
`project-management/components/`: `10 → 12` and `16 → 18`
(`frontend/src/__tests__/themeTokenMigration.test.ts:1648-1653`).

**Does the literal's own comment sanction it?** Yes, in so many words. The
comment at `themeTokenMigration.test.ts:1635-1640`, written when APRAS-92 and
APRAS-118 last moved it, ends:

> `// below is unchanged -- this literal is the file census, not a migration`
> `// figure, and it moves when a directory gains a file.`

That is not a reading I had to stretch for: the sentence names the exact event
(“a directory gains a file”), states the consequence (“it moves”), and
distinguishes the literal from the migration figures that must *not* move. Two
prior tasks are the precedent, and their own comment is still in place. The
developer added a comment naming APRAS-102 and the two files, in the same shape
as the precedent.

**Are the new numbers correct?** Counted by hand, not taken from the test:

- `frontend/src/features/project-management/components/` holds **12** files, all
  `.tsx`, no `__tests__` subdirectory inside it: `BudgetVsActualProgressBar`,
  `ConstructionTrackerPage`, `MilestoneFormModal`, `MilestoneTimeline`,
  `ObraPrintDialog`, `PhysicalProgressPlannedVsActualBar`,
  `ProjectBudgetCylinder`, `ProjectFormModal`, `ProjectSummaryCard`,
  `ProjectUpdateFeed`, `ProjectUpdateModal`, `PublicObrasReportPage`.
- `frontend/src/features/asset-management/components/` holds **6**, unchanged.
- `12 + 6 = 18`, which is the `files` assertion.

`pinnedFiles()`/`collect()` (`themeTokenMigration.test.ts:200-236`) counts
`.ts`/`.tsx` excluding `*.test.*` and excluding `__tests__` directories, so the
census is exactly the directory listing. Both figures are right.

**Verdict on the edit.** Accepted, and not treated as an overreach. R9's
operative guarantees are all intact — `exceptions.json` gains no entry, the
three class sets are the same classes in the same file three lines further
down, and the three named guard suites pass — and the census is a count that
*must* move the moment the directory gains a file, so the alternative to
bumping it is not adding the components. R9's enumeration simply did not
anticipate this literal; §6.1 of the spec names only the line-number pins. That
is a gap in the spec, not a liberty taken with it. A non-blocking suggestion on
the census's *form* is in §9.

**The three R9 facts, verified independently:**

- `git diff --cached --name-only` and `git diff HEAD --stat` both show
  `themeTokenMigration.exceptions.json` in **no hunk**; `json.load` counts
  **882** entries.
- `npx vitest run src/__tests__/themeTokenMigration.test.ts
  src/__tests__/brandTextRole.test.ts src/__tests__/themeContrast.test.ts
  src/i18n/__tests__/parity.test.ts` → **4 files passed, 232 tests passed**.
- Neither new component carries a palette class, a hex literal,
  `text-primary-text` or a bare `text-primary` (grepped). The only inline
  `style` uses are the three percentage positions the spec sanctions.

## 2. R10 — the hard boundary

- `git diff --name-only master` lists 18 paths;
  `backend/app/services/project_report_service.py` is **not** among them. It
  appears in the diff *text* only as prose references inside docstrings and in
  one `?raw` import of the baseline — no hunk on the file.
- `report_page_null_detail_baseline.html`: `git hash-object` in the worktree and
  `git rev-parse master:…` both give `cdee25b07a10bc2797d3ce01a2921c543c9b29f3`.
  **Byte-identical**, verified again after every mutation cycle.
- `cd backend && SECRET_KEY=test uv run pytest tests/test_project_stage_detail.py
  tests/test_project_report.py tests/test_projects.py` → **194 passed**.
- `uv run ruff check app tests` → *All checks passed!*;
  `ruff format --check` on the three touched Python files → *3 files already
  formatted*.

I deliberately did **not** mutate the baseline for the R8 check; see §5.

## 3. R6 — the UTC month, mutated

Mutated `lib/plannedProgress.ts:42-44` from `getUTCFullYear()`/`getUTCMonth()`
to `getFullYear()`/`getMonth()` and ran the suite:

```
× reads the UTC month in a negative-offset zone, not the local one
  AssertionError: expected 31.5 to be 64
× reads the UTC month in a positive-offset zone, not the local one
  AssertionError: expected 80 to be 64
Tests  2 failed | 5 passed (7)
```

**Both** boundary cases fail, with exactly the two values the spec names (`31.5`
and `80`), and the other five cases pass under the local read — which is the
point of R6. Restored, `cmp` clean.

The two cases also assert the zone is really in effect before making the claim
(`today.getMonth()` vs `today.getUTCMonth()`,
`plannedProgress.test.ts:134-135,146-147`), so a CI box that ignored
`process.env.TZ` fails loudly instead of vacuously. `TZ` is set with
`vi.stubEnv` and released in `afterEach`.

The helper is a faithful mirror of `planned_to_date`
(`project_report_service.py:681`): same `isinstance`/`typeof` ladder, same
`month <= current && month >= bestMonth` selection, same `0` vs `null`
distinction, same strictness. One narrow divergence noted as a suggestion in §9.

## 4. R4 — the guard order and half-to-even

**Guard order.** Moved the two non-finite returns from the top of
`formatPercent` to just before the `roundUp` decision (i.e. after the
`toFixed(20)` expansion):

```
× guards the non-finite inputs before expanding any decimals
  TypeError: Cannot read properties of undefined (reading 'charCodeAt')
Tests  1 failed | 5 passed (6)
```

The pinned cases fail, loudly, rather than silently producing something else —
`NaN.toFixed(20)` is `"NaN"`, so `dot === -1`, `kept` is empty and `kept[cut]`
is `undefined`. Restored.

**Half-to-even.** `npx eslint`-clean implementation; all seven pairs pass in the
suite. I then checked them against CPython directly rather than trusting the
table:

| value | decimals | CPython `format` | JS `toFixed` |
| --- | --- | --- | --- |
| 56.5 | 0 | `56` | `57` — diverges |
| 2.5 | 0 | `2` | `3` — diverges |
| 42.5 | 0 | `42` | `43` — diverges |
| 57.5 | 0 | `58` | `58` — agrees |
| 42.25 | 1 | `42.2` | `42.3` — diverges |
| 2.675 | 2 | `2.67` | `2.67` — agrees |
| −20.5 | 0 | `-20` | `-21` — diverges |

So a plain `toFixed` implementation fails five of seven, including all four the
review brief names. Replacing the whole body with `value.toFixed(decimals)`
fails the suite at the first assertion (`expected '57' to be '56'`) and also
fails the non-finite case (`expected 'NaN' to be 'nan'`).

Not asked for, but worth having: I differential-tested the real helper against
CPython over **19,206** cases — every quarter-step in `−500..500` (i.e. every
exact `.25/.5/.75` tie), every eighth-step in `−25..25`, and 2,000 random
values in `−100..100`, each at `decimals ∈ {0,1,2}`. **Zero mismatches.** Naive
`toFixed` mismatches 1,676 of the same cases. The mirror is real, not fitted to
the seven pins.

## 5. R2 and R8 — the non-degeneracy guards, fired rather than read

**R2's clamp preconditions** (`ProjectBudgetCylinder.test.tsx:62-65, 97-100`)
assert `toHaveLength(1)` for both ids before anything is parsed. Both halves
mutated:

- renamed `data-testid="cylinder-surface"` on the component → both geometry
  cases fail with `expected [] to have a length of 1 but got +0`;
- duplicated the fill `<path>` so the id matches twice → both fail with
  `expected [ …(2) ] to have a length of 1 but got 2`.

So the precondition fails at zero **and** at two, as a stated assertion rather
than a crash inside the `d` parse.

I also removed the clamp itself
(`const filled = Math.max(0, Math.min(100, …))` → `figures.remainingPct`) and
got exactly the failure the spec predicted: `expected 164 to be 140`.

**What the test reads is correctly narrow.** The regex at
`ProjectBudgetCylinder.test.tsx:27` extracts only the move-to `y` and the first
vertical operand; the range check at lines 76-79 and 107-110 is applied to
`yStart` and the surface's `cy` and to **nothing else** — not to `h` (a relative
operand), not to the move-to `x` (`10`), not to `rx 50 ry 12`. Neither of the
two historically wrong forms is present: there is no `/-\d/` scan, and no
assumption that every absolute coordinate lies in `20..140`. No widening.

**R8.** The brief asks for the guard to be fired by deleting one of the five
nodes — on a copy, because R10 forbids touching the baseline. I honoured that
literally: rather than editing
`backend/tests/data/report_page_null_detail_baseline.html`, I temporarily
mutated the *test file* so the module parsed a tampered **string** copy of the
imported bytes, then restored it. The baseline's blob hash is unchanged
(`cdee25b0…`) and `cmp` against the pristine copy is clean.

- Dropped the fourth `.budget-row` (`% executado`) from the copy → the
  non-degeneracy case fails `expected …(3) to have a length of 4 but got 3`
  **and** the comparison case fails with the named error
  `report_page_null_detail_baseline.html has no `strong` in budget row 3; the
  APRAS-102 parity pin cannot read the baseline's figures.`
- Renamed `class="cyl"` on the copy → the **whole file** fails at import with
  `report_page_null_detail_baseline.html matched 0 nodes for `.cyl .txt
  strong`, expected exactly 1; the APRAS-102 parity pin cannot read the
  baseline's figures.`

Both are the named error, not a vacuous pass. The suite's own
`fails loudly, not vacuously…` case already pins the 0-node and 2-node throws.

The five preconditions R8 requires are all present and run before any
comparison (`reportFigureParity.test.tsx:112-139`): four rows each with exactly
one `strong`, the one `.cyl .txt strong`, the four row **labels** pinned so the
positional read is anchored, the two parsed inputs `480000` and `204000`, and
each expected string non-empty and matching `/\d/`. The developer put them in a
sibling `it` rather than inside the comparison case; that is equivalent or
stronger here, because `exactlyOne` for the cylinder label runs at module scope
and takes the whole file down.

**The whitespace normalisation is the named one and nothing wider.**
`reportFigureParity.test.tsx:37-47` maps U+00A0 and U+202F to U+0020 by two
`split`/`join` pairs — no regex class, no `\s`, no trim. I no-oped it and the
comparison fails with the tell-tale
`expected 'R$ 276.000,00' to be 'R$ 276.000,00'` (identical to the eye, one
NBSP apart), so the normalisation is load-bearing in the direction the spec
describes and could not be hiding a digit difference.

## 6. R7 — the four degenerate inputs assert positively

`PhysicalProgressPlannedVsActualBar.test.tsx:72-96` is table-driven over `null`,
`[]`, `{}` and `[{ month: "nope", pct: 1 }]`, and each row asserts the positive
side: the realized segment is present **and** `style.width === "42.5%"`, the
plan label is `—`, no gap, no marker, no below-plan text. Not the vacuous
“renders without throwing” form.

Mutated the component to render the realized segment only when a curve exists
(the exact shape the vacuous form would miss) — **all four** rows fail with
`TestingLibraryElementError: Unable to find an element by:
[data-testid="progress-realized"]`. Restored.

## 7. R1, R3, R5, R11, R12

**R1** — `backend/tests/test_projects.py` adds four cases and all pass: the
detail route returns the stored curve verbatim; it returns a *present* `null`
for a project without one (the test asserts the key is present *and* `None`,
which is the right shape); list items carry no `planned_progress_json` key; and
a `PUT` carrying the field answers `200` with the column unchanged, asserted
both in the database (after `session.expire_all()`) and through a second `GET`.
The schema change is on `ProjectDetailRead` only and the service passes it
**explicitly** — which is exactly the `ProjectDetailRead(**base_read.model_dump(),
…)` trap the `cover_photo_display_url` comment already records, and the first
test is what makes the explicit pass load-bearing.

**R3** — four labelled rows (`orçamento previsto`, `executado`, `saldo`,
`% executado`), `balance: total - executed` in the helper, and the percentage at
one decimal (`formatPercent(executedPct, 1)` → `42.5%`). Asserted on `276000`,
where a swapped operand order would read `-276.000,00`.

**R5** — behind: `bg-destructive/70`, the below-plan text, `left: "42.5%"` /
`width: "21.5%"` (the unrounded figures, with the labels still `64%` / `42%`).
Ahead: `bg-primary/30`, asserted **not** to contain `bg-destructive/70`, text
absent. Both states also carried in the track's `aria-label`, so the status is
not colour-only.

**R11** — `projects.cylinder.*` and `projects.plannedBar.*` added to **both**
`pt.json` and `en.json`, including the below-plan label (`behind`:
`abaixo do previsto` / `below plan`); `src/i18n/__tests__/parity.test.ts`
passes.

**R12** — thresholds in `frontend/vitest.config.ts:41-46` are `lines: 80`,
`functions: 78`, `branches: 76`, `statements: 80`. Measured:

```
Statements   : 91.62%   Branches : 85.48%
Functions    : 87.88%   Lines    : 92.33%
```

— matching the developer's figures and clearing every gate. The four new
modules are at 100 % on all four metrics. `npm run build` (`tsc -b && vite
build`) succeeds.

**Suite totals.** `npx vitest run` → **196 files / 2562 tests passed**. I ran
the full suite six times (four of them with `--coverage`). Five runs were
clean; one `--coverage` run reported `1 failed | 2561 passed` and my output
filter swallowed the test name. It did not recur in five subsequent full runs,
nor in eight consecutive runs of the 13 files touched by this task (282 tests,
green every time). I could not attribute it to this diff and am not raising it
as a finding against the task — recorded in §9 so it is not lost.

## 8. Lint — exact invocation, and the 370 vs 377 discrepancy

**Invocation, run from `<worktree>/frontend`:**

```
npx eslint . -f json
```

(identical to `npm run lint`, whose script is literally `eslint .`), summed over
every result object:

| | errors | warnings | files with errors |
| --- | --- | --- | --- |
| after this task | **370** | **2** | **66** |

The developer's figure reproduces exactly.

On the unreconciled 377/2/66 reported earlier in the week: I can settle it
without re-linting an old base. **None of the 18 changed paths carries a single
eslint error** — `npx eslint` over `themeTokenMigration.test.ts`,
`ConstructionTrackerPage.tsx` and `types/project.ts` reports *No issues found*,
the six new files contribute zero, and the 66 error-carrying paths in the JSON
report intersect the changed set in **nothing**. ESLint's error counts are
per-file, so the base total on `2124432` is necessarily the same 370 as the
after total, and this task's delta is exactly **0**. The 377 figure therefore
belongs to a different base commit, not to a different invocation — `npm run
lint` and `npx eslint .` are the same command here, so invocation cannot
explain a 7-error gap. The criterion (“no worse than base”) is met either way,
and met per-file, not only in total.

## 9. Operator decisions, both settled correctly

**One card, not two.** `BudgetVsActualProgressBar` is imported nowhere on the
page; `ConstructionTrackerPage.tsx` has no other reference to `total_budget` or
`executed_budget` outside the cylinder's two props, and no other render site in
`frontend/src` renders that component (only `ProjectsFeature.test.tsx` renders
it directly, which keeps its two existing cases and its 11 grandfathered
exceptions out of this diff). The page test asserts the old card's **heading**
and its `budget-progress-fill` test id are both absent. The budget is stated
once on the screen.

**The balance number inside the tank.** An SVG `<text>` at `x=60`, riding
`labelY = max(surfaceY + 22, TOP + 30)`, `fontSize="16" fontWeight="700"` —
large, over the green — printing the **unclamped** percentage, in
`text-primary-foreground` normally and `text-destructive` when negative (at
which point the tank is empty and the label has already dropped onto the card,
exactly as the spec pre-sanctioned). The class is read in the test via
`getAttribute("class")`, not `.className`, which on an SVG element is an
`SVGAnimatedString` a `toContain` would have passed over vacuously — a nice
catch, and the comment says why.

---

VERDICT: APPROVED

## Blocking Findings

None.

## Suggestions

1. **Derive the file census instead of hand-bumping it**
   (`frontend/src/__tests__/themeTokenMigration.test.ts:1648-1653`). A count
   that must be edited by hand every time a directory gains a file costs a
   round of review attention each time (this is its third bump: APRAS-92,
   APRAS-118, now APRAS-102) while catching nothing a human bump would not
   simply absorb. Its real job is non-degeneracy — proving the two directories
   are actually being scanned, so a broken glob cannot make the whole suite
   vacuously green. That job is served better by a lower bound plus an identity
   check: `expect(projectsFiles.length).toBeGreaterThanOrEqual(10)` together
   with an assertion that a few known-pinned filenames
   (`ConstructionTrackerPage.tsx`, `BudgetVsActualProgressBar.tsx`,
   `AssetsInventoryPage.tsx`) are present. A broken glob still fails loudly; a
   new component does not. Same shape for the `FINANCE`/`PURCHASES` and
   `DOCUMENTS`/`OCCURRENCES` censuses in the same file, which carry the
   identical maintenance cost.
2. **`formatPercent(-0, d)` returns `"0"` where Python's `format(-0.0, '.0f')`
   is `"-0"`** (`lib/budgetFigures.ts:84`, `negative = value < 0` is `false`
   for `-0`). This is the only divergence my 19,206-case differential against
   CPython found, and it is unreachable through `budgetFigures` (`100 -
   executedPct` is never `-0`). Since the module's docstring claims to mirror
   `format` “across its whole domain”, either use `Object.is(value, -0)` in the
   sign test or add a sentence excluding signed zero from the claim.
3. **`plannedProgress` is stricter than `planned_to_date` on `pct: NaN`**
   (`lib/plannedProgress.ts:59` refuses it; the backend's
   `isinstance(pct, (int, float))` accepts it and would render `nan%`).
   Unreachable through a JSON column in practice, and the frontend's behaviour
   is the better one, but a module documented as a strict mirror should say
   where it deliberately differs. One line in the docstring.
4. **`decimals` is documented as `0..2` but not enforced**
   (`lib/budgetFigures.ts:69`). A negative or large `decimals` would walk the
   index arithmetic off the expansion. Both call sites pass `0` or `1`, so this
   is only a guard against a future caller: either narrow the parameter type to
   `0 | 1 | 2` or add a one-line clamp.
5. **The em dash for “no curve” as a literal constant** (`NO_CURVE_LABEL` in
   `PhysicalProgressPlannedVsActualBar.tsx:40`) is, in my view, right as it
   stands — it is a typographic placeholder, not prose, and it reads identically
   in both locales — so the developer's open question 5 can be closed as “leave
   it”. Raising it here only so the decision is recorded rather than re-asked.
6. **Record the one unreproduced flake.** One `npm run test:coverage` run
   reported `1 failed | 2561 passed`; it did not recur in five further full runs
   or in eight runs of this task's 13 files. Not attributable to this diff and
   not a finding against it, but if QA or CI sees a lone failure in a coverage
   run, this is a prior sighting and not a new regression.
