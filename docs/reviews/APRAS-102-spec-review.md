# APRAS-102 — spec review (round 1)

Reviewed: `docs/tasks/APRAS-102-spec.md`, `docs/tasks/APRAS-102-mock.html`
Tree: `25e9dc6`, working copy as dispatched. Nothing staged, nothing edited.

**VERDICT: NEEDS_REVISION**

---

## 1. Premise verification (all independently checked, not taken from the spec)

### 1.1 The baseline already carries every figure the parity test needs — TRUE

`backend/tests/data/report_page_null_detail_baseline.html` (4,593 bytes, one line):

```
<div class="budget-col">
  <div class="budget-row total"><small>Orçamento previsto</small><strong>R$ 480.000,00</strong></div>
  <div class="budget-row"><small>Executado</small><strong>R$ 204.000,00</strong></div>
  <div class="budget-row"><small>Saldo</small><strong>R$ 276.000,00</strong></div>
  <div class="budget-row"><small>% executado</small><strong>42.5%</strong></div>
</div>
<div class="cyl">…<div class="txt"><small>Saldo restante</small><strong>58%</strong>…
…<div class="pv">…<div class="tag plan" style="left:64%"><span>previsto</span><b>64%</b></div>
   <div class="tag real" style="left:42%"><span>realizado</span><b>42%</b></div>
```

Every selector the spec names resolves:

| Selector | Matches | Value |
| --- | --- | --- |
| `.budget-col .budget-row` | 4 (the first is `budget-row total`, still matched) | in document order: previsto, executado, saldo, % executado |
| `.cyl .txt strong` | 1 | `58%` |
| `.pv .tag.plan b` | 1 | `64%` |
| `.pv .tag.real b` | 1 | `42%` |

The fixture project (`test_project_stage_detail.null_detail_project`) is
`total_budget=480000.00`, `executed_budget=204000.00`,
`physical_progress_pct=42.50`, `planned_progress_json=PLANNED_CURVE`.
`test_the_all_null_page_renders_the_committed_baseline` compares
`render_null_detail_page() == baseline` — a true byte pin.

### 1.2 `PLANNED_CURVE` is all-2020 — TRUE, and the backend's own comment is more precise than the spec's

```python
PLANNED_CURVE = [
    {"month": "2020-01", "pct": 8.0},
    {"month": "2020-02", "pct": 31.5},
    {"month": "2020-03", "pct": 64.0},
]
```
with the comment: *"Every month is in the past. `planned_to_date` does read the
clock, so this is not clock-independence — it is **forward stability**."*
The spec calls it "date-independent"; the effect is the same (64 forever), the
wording is looser than the source it cites. Non-blocking.

### 1.3 Frontend already imports the baseline with `?raw` — TRUE

`frontend/src/features/project-management/__tests__/fixtures/obraReportFixture.ts`
line: `import baselinePage from "../../../../../../backend/tests/data/report_page_null_detail_baseline.html?raw";`
and `frontend/vitest.config.ts` has `server.fs.allow: [".", "../backend/tests/data"]`.
No config change needed. Confirmed.
(The spec writes the fixture path as `__tests__/fixtures/obraReportFixture.ts`;
the real path is under `features/project-management/`. §4 is right, §5 is loose.)

### 1.4 Line references — ALL FIVE CORRECT at `25e9dc6`

```
project_report_service.py:523  def _brl
project_report_service.py:681  def planned_to_date
project_report_service.py:822  def _one_bar
project_report_service.py:869  def _cylinder_svg
project_report_service.py:1402 def _budget_html
project_report_service.py:1430 def _stages_html
```
`clock.today_utc` is at **104**, not 105 (the docstring runs to 111). Trivial.
`ConstructionTrackerPage.tsx`: `BudgetVsActualProgressBar` imported at line 24,
rendered at line 417 — both as the spec states; file is 619 lines.

### 1.5 `planned_progress_json` is model-only and the explicit-pass trap is real — TRUE

`grep -rn planned_progress_json backend/app frontend/src` returns exactly three
hits: `models/project.py:51` (the column), `models/project.py:103` (a comment),
`project_report_service.py:1431`. On no schema, in no frontend file.

`ProjectService.get_project_detail` ends:
```python
base_read = ProjectRead.model_validate(project).model_copy(update={...})
return ProjectDetailRead(**base_read.model_dump(), milestones=..., updates=...)
```
preceded by the `cover_photo_display_url` comment the spec cites, verbatim about
"an unfilled field would answer `null` from the detail route forever". The trap
and the remedy are both as described.

`ApiModel` carries no `extra="forbid"`, so pydantic's default `ignore` applies:
a `PUT` body containing `planned_progress_json` is silently dropped and the
column is untouched. Result 1's write-schema criterion is therefore checkable
as written (though the expected status code is unstated — see Suggestions).

### 1.6 The theme-guard pins — TRUE

`themeTokenMigration.test.ts` pins `ConstructionTrackerPage.tsx` at **313, 314,
359** in the exceptions ledger and reads line **240** in the `bg-background`
case. The APRAS-104 precedent the spec invokes is present in the file:

> `// +42 since APRAS-104: … The three sets themselves are untouched -- same file, same classes -- only the pinned line numbers moved.`

`text-primary-text` pin: `expect(characters("ConstructionTrackerPage.tsx")).toHaveLength(2)`
and `toHaveLength(0)` for every other file — confirmed, a new component using it
fails. Bare `text-primary` is counted per-file against `GRAPHICAL_PRIMARY_SITES`
in `brandTextRole.test.ts` — confirmed. Exceptions count 882 — confirmed by the
literals throughout `themeTokenMigration.test.ts`.

All six named tokens exist in the `@theme` block of `index.css`
(`--color-foreground`, `--color-card`, `--color-primary`, `--color-muted`,
`--color-muted-foreground`, `--color-border`, plus `--color-destructive`), so
`fill-*` / `stroke-*` / `bg-*` / `text-*` all generate. `themeTokenCompile.test.ts`
drives off a static `ROWS` table and does not scan source, so a new `fill-primary`
does not disturb it.

### 1.7 The UTC claim — TRUE on both halves

`planned_to_date` line 697: `current = (today or clock.today_utc()).strftime("%Y-%m")`,
and `clock.today_utc`'s docstring is explicit ("Deliberately UTC and not the
local calendar… instead of drifting by a day every evening in a negative-offset
zone"). Neither component renders a date or instant: the cylinder prints four
money strings and two percentages; the bar prints two percentages and two
static labels. `month` values are plain `"YYYY-MM"` strings in a JSON column.
So the spec is right that APRAS-120's offset contract does not reach here, and
right that the local/UTC distinction is real. See blocking finding 5 for why
stating it is not enough.

---

## 2. The four weighed questions

### 2.1 Result 5 — does the parity test actually pin the arithmetic?

**Structurally, yes.** Inputs (`R$ 480.000,00`, `R$ 204.000,00`) and expectations
(`R$ 276.000,00`, `42.5%`, `58%`) are *different bytes* of a file the backend
produced and `test_the_all_null_page_renders_the_committed_baseline` pins byte
for byte. The three asserted values are not re-derivable from the two inputs
without performing the arithmetic under test. A sign error in `balance`, a
missing `/total*100`, a wrong decimal count — each fails. This is a genuinely
better design than the hand-written fixtures this repo has been burned by.

**On regeneration:** if the fixture project's numbers change, both sides move
together and the test still passes — and that is *correct*: the test is an
arithmetic-parity test, not a value pin, and the value pin already exists on the
backend side. Regeneration is a deliberate, reviewed act guarded by its own
byte test. So "silently follows the new numbers" is the intended and right
behaviour, with one caveat worth closing (Suggestion S1): a regeneration to a
*degenerate* fixture (executed = 0, executed = total, a round 50 %) would
silently hollow the test out, and the spec asks for no non-degeneracy guard on
the parsed inputs.

**But the parity is incomplete in the one dimension the fixture cannot see:
rounding mode.** See blocking finding 1. And as literally specified, the `saldo`
assertion cannot pass at all. See blocking finding 2.

### 2.2 The UTC-month claim

Both halves verified (§1.7). It is specified in §1b and carried into recorded
result 4 ("the current **UTC** month"), which is where it bites. The defect is
that nothing *tests* it — every listed `plannedProgress` case passes identically
under a local-month implementation. Blocking finding 5.

### 2.3 The line-number bump

**Sound, not laundering.** The ledger entry is a triple
`(file, line, classSet)`; the guard's purpose is that *these* palette classes
appear at *these* sites and nowhere else, and that no new palette class is
introduced. Shifting a line number while holding the class set byte-identical
preserves all of that: the same three sets remain pinned in the same file, the
`characters(...)` and `brandTextRole` counts are untouched (an `import` line
carries no utility class), and the 882/1,197 ledger totals do not move. A
*wrong* bump fails loudly rather than silently widening the guard, because the
set must be found at the stated line. Only pins *after* the insertion point
shift, and all four of this file's pins (240, 313, 314, 359) precede the render
site at 417, so the delta is exactly the number of import lines. The repository
has done this once already, with the reasoning left in place. No finding.

### 2.4 The robustness cases

`plannedProgress`'s list is tight and the "each assertion mutates the input and
checks the mutation changes the output" clause is exactly the right answer to
this project's nineteen no-op tests. Two defects:

- `budgetFigures`' cases are mis-assigned. The helper mirrors `_budget_html`,
  which does **not** clamp (`remaining_pct = 100.0 - executed_pct`, negative
  when `executed > total`; the clamp lives in `_cylinder_svg`). Result 2 asks a
  *unit test* to assert "no geometry value is negative" of a helper that
  returns no geometry and must return a negative `remainingPct` to stay a
  mirror. Blocking finding 4.
- "throws nothing" is correctly *not* left alone in §5 (which also requires the
  `—` plan label), but the **recorded** result 4 drops that half, and QA sees
  only the recorded list. Blocking finding 6.

### 2.5 The mock's two A/B questions

**Question 1 (one card or two): answerable, and the pair is clean.** Both hosts
render `cylinderCard(figures, false)` — byte-identical cylinders — and A adds
the legacy "Acompanhamento Orçamentário" card above it while B shows the
cylinder alone. The only difference is the stated variable. Both are driven by
the same live sliders, so the operator sees the duplication argument directly.

**Question 2 (number inside or beside): answerable, and the pair is clean.**
`cylinderCard(figures, true)` vs `(figures, false)`; the toggle both inserts the
in-tank `<text>` and removes the beside-tank figure, and leaves the "Saldo
restante" caption and the balance sentence in place in both. One variable.
The "drag to 5 %" demonstration works: at ~4 % remaining `fy = 135`,
`labelY = max(157, 50) = 157`, below the tank bottom (140) but inside the
`0 0 120 165` viewBox, so the number visibly falls out of the tank onto the
card exactly as the prose promises.

One honest-rendering caveat (Suggestion S2): in the *app's* token set
`--primary-foreground` is `oklch(0.15 0.02 160)` — near-black — so when A's
number escapes onto the white card it stays perfectly readable. The report's
version of the defect is unreadable because the report's `--brand-ink` is
near-white (~1.05:1, as `_cylinder_svg`'s docstring records). The mock's prose
("é o defeito que o relatório público já tem hoje") imports the report's
severity into a context where only the *layout* is wrong, which tilts the
operator toward B. The rendering is truthful; the sentence is not. Worth one
clause, not a revision round by itself.

### 2.6 Scope / split

Declining the split is correct. Two backend lines, one type, two pure helpers,
two components, two render sites in one existing page, i18n keys, and their
tests — one feature slice inside `project-management`, one subsystem, one PR,
comfortably inside the iteration budget. No `NEEDS_SPLIT`.

---

## 3. Blocking findings (detail)

### B1 — Python's and JavaScript's rounding modes differ, and the chosen fixture cannot see it (§1b, §5, result 5)

The spec's thesis is that "the two implementations cannot drift". `_budget_html`
formats with `f"{executed_pct:.1f}"` and `f"{remaining_pct:.0f}"`; Python's
`format` is **round-half-to-even**. `Number.toFixed` and `Intl.NumberFormat` are
**round-half-away-from-zero**. Measured on this machine:

| value | Python `:.0f` | JS `toFixed(0)` | Python `:.1f` | JS `toFixed(1)` |
| --- | --- | --- | --- | --- |
| 57.5 | `58` | `58` | — | — |
| **56.5** | **`56`** | **`57`** | — | — |
| 2.5 | `2` | `3` | — | — |
| 0.5 | `0` | `1` | — | — |
| **42.25** | — | — | **`42.2`** | **`42.3`** |

The fixture's own values (`executed_pct = 42.5`, `remaining_pct = 57.5`) are the
two half-way cases where the two modes happen to **agree**, so the parity test
passes while the implementations differ. A real obra at `total = 400.000`,
`executed = 174.000` gives `remaining_pct = 56.5`: the public report prints
`56%`, the internal view prints `57%`, for the same obra on the same day.

The spec must state the rounding rule the frontend uses and require a test case
that discriminates it (e.g. assert the helper's formatter on `56.5 → "56"` and
`42.25 → "42.2"`, citing Python's `format` semantics), or explicitly accept the
divergence in writing. As it stands the one drift the task exists to prevent is
both unspecified and untestable by the specified test.

### B2 — The `saldo` assertion, as specified, cannot pass: NBSP vs space (§1b, §5, result 5)

The spec requires the helper to format "through the existing
`utils/currency.ts`" *and* requires the test to assert the rendered `saldo`
"equal the baseline's own `Saldo` (`R$ 276.000,00`)". Those two cannot both hold:

- `_brl` builds its string by hand — `"R$ " + …` — with **U+0020**.
- `formatCurrency` is `Intl.NumberFormat('pt-BR', {style:'currency'})`, which
  emits **U+00A0**: `52 24 a0 32 37 36 2e 30 30 30 2c 30 30`.

A literal `toBe`/`toHaveTextContent` comparison fails. The implementer then has
two ways out, and the spec does not choose: normalise `  →  ` before
comparing (fine, and it must be written down so it is not mistaken for a
loosened assertion), or abandon `currency.ts` and hand-roll a `_brl` mirror
(a second currency formatter in the tree, worse). Ambiguity implementable two
ways, on the task's headline criterion. Name the normalisation explicitly in
§5 and in result 5.

### B3 — The bar loses the backend figure's "behind plan" signal, and the mock draws a segment the spec does not tokenise (§2, §3, result 4)

`_one_bar` and the pinned report stylesheet carry **three** track elements and a
semantic state, not two:

```
.one .seg.a        { left:0; background:var(--brand); }      /* realized   */
.one .seg.b        { background:var(--brand-alt); }          /* the gap    */
.one .seg.b.behind { background:#c0392b; opacity:.7; }       /* behind plan */
.one .mark         { background:var(--card); }               /* the marker  */
```

and the baseline's own bar is in that state:
`<div class="seg b behind" style="left:42%;width:22%">`.

§2 of the spec describes only "one track with the realized segment, the planned
marker and the two labels". §3's token table has no row for the gap segment and
no row for the behind-plan state. The mock does render a gap — but with
`color-mix(in oklch, var(--primary) 25%, var(--muted))`, a derived colour that
is neither a token nor listed in §3, and it renders it the same whether the
obra is ahead or behind. So the figure most load-bearing distinction for the
síndico — *am I behind schedule* — is silently dropped, and the implementer is
left to invent a colour for an element the spec never names. Result 4 is
satisfiable with the signal absent.

Either specify the gap segment and the behind state with tokens
(`bg-destructive` is already in §3's table for "over-budget emphasis") and add a
test case asserting the behind state renders differently from the ahead state,
or state in "Not in scope" that the internal bar deliberately omits it and
remove the gap from the mock so the mock and the spec agree.

### B4 — Result 2's clamp assertions are on the wrong unit, and the printed remaining-% is unspecified for `executed > total` (§1a, §2, result 2)

`budgetFigures` mirrors `_budget_html`, which does not clamp: at
`executed > total` it *must* return a negative `remainingPct` to stay a mirror,
with the clamp in the component as `_cylinder_svg` has it. Result 2 nonetheless
says "a unit test covers `total = 0` and `executed > total` and asserts no
returned field is `NaN` and no geometry value is negative" — a helper that
returns no geometry, and whose faithful output *is* negative there. As written
an implementer can satisfy it by clamping inside the helper, which breaks the
mirror the whole design rests on.

Compounding it: §2 says the tank's fill is "`remainingPct` clamped to `0..100`"
and "the remaining percentage is **also** printed as text", without saying
whether the *text* is clamped. The report prints it **unclamped**
(`{remaining_pct:.0f}%` → `-20%`); the mock prints it **clamped**
(`filled.toFixed(0)` → `0%`). Two implementations, both defensible, in a task
whose premise is that the two views agree. Split the criterion: NaN-freedom and
the unclamped mirror on the helper; clamped, non-negative geometry on the
component; and say which number the text shows.

### B5 — Result 4 mandates UTC-month selection and no specified test can tell UTC from local (§5, result 4)

Every listed `plannedProgress` case — the all-2020 curve, `null`, `[]`,
non-list, bad `month`, bad `pct`, all-future, mixed past/future — produces an
identical result under `getUTCMonth()` and under `getMonth()`. The hazard the
spec itself identifies as "breaking result 5 intermittently and unreproducibly"
therefore ships unguarded, and `getUTCMonth` vs `getMonth` is a one-character
regression away forever after.

The spec already provides the hook — the optional `today` argument. Require a
case that passes a `today` straddling a month boundary in a negative-offset zone
(e.g. `2020-03-01T00:30:00Z`, whose local date in `America/Sao_Paulo` is
`2020-02-29`) against a curve with a `2020-03` point, asserting `64` and not
`31.5`. Also fix the argument's contract: §1b says the helper reads
`getUTCFullYear()`/`getUTCMonth()` but does not say what `today` *is* (a `Date`?
a `"YYYY-MM"` string?), and a `Date` injected by a test is the exact place a
local-calendar read slips back in.

### B6 — Recorded result 4's "throws nothing" is satisfiable by rendering nothing (result 4)

§5 gets this right ("renders with `null` and `[]` without throwing, **and shows
the `—` plan label**"). The recorded result 4 says only "renders with no plan
segment and throws nothing". A component wrapped in a `try` that swallows and
returns `null` satisfies it, as does an early `return null`. QA receives only
the recorded list. Add the positive artefact to the recorded result: in all four
payload cases the realized segment is present and the plan label reads `—`.

### B7 — The coverage gate is not 75 % (§5 result 7, result 9)

`frontend/vitest.config.ts`:

```ts
thresholds: { lines: 80, functions: 78, branches: 76, statements: 80 },
```

ratcheted by APRAS-36. There is no 75 % anywhere. Both the spec body ("coverage
stays above the configured gate (75 %)") and recorded result 9 ("coverage above
the configured 75 % gate") state a number that does not exist, and the recorded
result is the only thing QA reads: a run at 77 % lines satisfies the recorded
criterion and fails `npm test`. State the four thresholds, or say "the
thresholds configured in `vitest.config.ts`" and let the suite be the check.

---

## 4. Suggestions (non-blocking)

- **S1 — guard the parity fixture against degeneracy.** The test is a parity
  test, so it rightly follows a regenerated baseline. Add an assertion that the
  parsed inputs are discriminating — `total > 0`, `0 < executed < total`,
  `executedPct` not in `{0, 50, 100}` — so a future regeneration to a round or
  degenerate fixture fails loudly instead of quietly turning result 5 into a
  tautology. Cheap, and it is the one way this design can rot.
- **S2 — mock question 2's prose overstates A's cost.** In the app's palette
  `--primary-foreground` is near-black, so A's escaped number stays readable on
  the card; only the layout is wrong. The report's unreadability comes from its
  near-white `--brand-ink`. Trim the sentence to the layout claim so the A/B
  choice is not tilted by a severity that does not apply here.
- **S3 — the marker colour diverges from the report without saying so.**
  `.one .mark` is `var(--card)` (a light hairline *over* the fill); §3 specifies
  `bg-foreground`. Probably the right call on a white card, but in a
  parity-driven spec the divergence deserves the same one-line justification the
  rest of §3 gets.
- **S4 — `clock.py @ 105` is `@ 104`**; the `today_utc` `def` is at 104. The
  spec's own "trust the function name" preamble covers it.
- **S5 — the fixture path in §5** is written as `__tests__/fixtures/obraReportFixture.ts`;
  it lives at `frontend/src/features/project-management/__tests__/fixtures/`.
  §4 is correct.
- **S6 — name the expected status for the write-schema case.** `ApiModel` does
  not set `extra="forbid"`, so a `PUT` carrying `planned_progress_json` is
  silently ignored and answers `200`. The criterion holds either way, but
  stating `200` plus an unchanged column is stronger than "leaves the column
  untouched", which a `422` would also satisfy.
- **S7 — §1.2 wording.** The backend's own comment distinguishes forward
  stability from clock-independence; the spec says "date-independent". Same
  outcome, looser claim than the source it cites.

---

## 5. What is good here, for the record

The parity-through-the-committed-baseline design is the right instinct and is
executed carefully: inputs and expectations are different bytes of a
backend-produced, byte-pinned file; a missing selector throws a named error
rather than yielding a vacuous fixture; the "each assertion mutates the input
and checks the mutation changes the output" clause is the correct remedy for
this repository's recorded no-op tests; §6 names both collateral hazards before
review could find them; and the token work is grounded in measurements already
in the tree rather than invented. The blocking findings are gaps in that design,
not objections to it.
