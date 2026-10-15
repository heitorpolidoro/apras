# APRAS-102 — Show the report's balance cylinder and planned-vs-actual bar in the internal project view

> Line references below were read at `25e9dc6` and are stated as
> `function @ line`. **Line numbers in this repository go stale fast** — if a
> number disagrees with the tree, trust the function name, which is stable.

## Scope

The public obras report already draws two figures the síndico reads first: the
**balance cylinder** (a tank filled to the remaining-budget percentage, beside
four money lines) and the **planned-vs-actual physical-progress bar**
(`previsto até hoje` × `realizado`). Both are rendered server-side as HTML
strings by `backend/app/services/project_report_service.py` and exist nowhere
in the internal construction tracker, which today shows only a financial
execution bar (`BudgetVsActualProgressBar`) and a physical-progress gauge with
no plan to compare against.

This task brings both figures into the internal project view as React
components, exposes the one input the API does not yet return
(`planned_progress_json`), and pins the frontend's arithmetic to the backend's
through the committed report baseline, so the two implementations cannot
drift.

**Not in scope:** any change to `project_report_service.py` or to the public
report's output; any change to `BudgetVsActualProgressBar.tsx` (see §6 — editing
it is cheap to start and expensive to finish); the report's stage-detail
accordion, bulletins or masthead; writing `planned_progress_json` through the
API (it stays SQL/seed-written, as `models/project.py` records); the
`ProjectSummaryCard` list tiles; and the report's own in-tank label defect
recorded in `_cylinder_svg`'s docstring.

## 1. The arithmetic, and where it comes from

### 1a. The backend, read first

`_budget_html @ 1402` computes **exactly five figures** and nothing else:

- `total = project.total_budget or ZERO`, `executed = project.executed_budget or ZERO`
- `balance = total - executed`
- `executed_pct = float(executed / total * 100) if total else 0.0` — the
  zero-budget guard, which is why result 1 can promise "never a division by
  zero and never NaN"
- `remaining_pct = 100.0 - executed_pct`

It prints `total`, `executed`, `balance` through `_brl @ 523` (pt-BR
`R$ 1.234,56`), `executed_pct` with **one** decimal (`:.1f`) and
`remaining_pct` with **none** (`:.0f`), and passes `remaining_pct` to
`_cylinder_svg @ 869`, which clamps it to `0..100` and fills a 120-unit-tall
tank from the bottom. **`_budget_html` itself never clamps**: at
`executed > total` it prints a negative `remaining_pct` (`-20%`) beside a tank
the clamp has emptied.

`_one_bar @ 822` prints both of its percentages with `:.0f`, and the baseline
shows why that matters: `physical_progress_pct = 42.5` prints **`42%`**.

### 1a-bis. Rounding mode — the one divergence this task must close

Python's `format` rounds **half to even**; JavaScript's `Number.toFixed` and
`Intl.NumberFormat` round **half away from zero**. Measured, not assumed:

| value | format spec | Python | naive JS |
| --- | --- | --- | --- |
| `56.5` | `:.0f` | `56` | `57` |
| `2.5` | `:.0f` | `2` | `3` |
| `42.5` | `:.0f` | `42` | `43` |
| `42.25` | `:.1f` | `42.2` | `42.3` |
| `57.5` | `:.0f` | `58` | `58` (agree) |

So a real obra with `total = 400000`, `executed = 174000` has
`remaining_pct = 56.5` and the public report prints `56%` while a `toFixed(0)`
frontend prints `57%` — the same obra, the same day, two numbers. The baseline
fixture's own values (`42.5` executed-%, `57.5` remaining-%) are exactly the
two cases where both modes agree, so the parity test cannot see this on the
budget figures alone.

**The rule, therefore:** both new components format every percentage through
one shared helper exported from `budgetFigures.ts` —
`formatPercent(value, decimals)` — that rounds **half to even**, so it mirrors
`format` for every input and not merely for the fixture's. The two modes differ
*only* at an exact binary tie, so the helper must decide on the exact decimal
expansion of the double (what `toFixed(20)` yields) rather than scaling and
re-rounding; `2.675` with one `:.2f`-equivalent decimal must still give `2.67`,
as Python does, because the stored double is below the tie.

Money is unaffected in practice — `_brl` formats a `Decimal` already quantised
to two places, and both runtimes agree there — but currency still goes through
the existing `frontend/src/features/project-management/utils/currency.ts` and
nothing else (see §5; the full path matters because an unrelated second
`formatCurrency` exists in `purchase-management/utils/formatters.ts`), and no
second currency formatter is written anywhere in this task.

`_stages_html @ 1430` feeds the bar: `planned = planned_to_date(project.planned_progress_json)`
and `realized = float(project.physical_progress_pct or 0.0)`, rendered by
`_one_bar @ 822`. `planned_to_date @ 681` is the rule the frontend must mirror:
the `pct` of the **latest point whose `month` is `<=` the current month**,
`0.0` when every point is in the future, and `None` — *no curve*, so the bar
draws the realized segment alone and the plan tag reads `—` — for a `null`
payload, an empty list, a non-list, or **any single malformed point** (strict:
one bad point invalidates the whole curve).

### 1b. The frontend, pinned to it

Two pure helpers, each the single definition of its arithmetic, each with the
backend function named in its docstring:

- `frontend/src/features/project-management/lib/budgetFigures.ts` — mirrors
  `_budget_html`'s five figures, including the `total === 0 → executedPct = 0`
  branch; **no clamping**, because `_budget_html` does not clamp (at
  `executed > total` it returns a negative `remainingPct`, and a mirror that
  silently clamped would stop being one). Money is formatted through the
  existing `features/project-management/utils/currency.ts`; percentages through this module's own
  `formatPercent` (§1a-bis). The clamp lives in the component, where
  `_cylinder_svg` has it.
- `frontend/src/features/project-management/lib/plannedProgress.ts` — mirrors
  `planned_to_date`, with the same strictness and the same three return cases.

**The one place the two languages could disagree on time, and the decision.**
`planned_to_date` compares `"YYYY-MM"` strings against
`clock.today_utc().strftime("%Y-%m")` — a **UTC** calendar month
(`clock.py @ 104` is explicit that this is deliberate). The frontend helper
must therefore read the current month from `getUTCFullYear()`/`getUTCMonth()`,
**not** from the local calendar: in a negative-offset zone the local month lags
UTC for a few hours at every month boundary, and in that window a local-month
cursor would select a different curve point from the one the report printed —
breaking result 5 intermittently and unreproducibly. This is deliberately
*not* the APRAS-120 contract (`schemas/base.py`, commit `25e9dc6`): that
contract governs **instants** returned with an explicit offset and rendered in
the browser's zone, and neither of these two components renders any date or
instant at all. `planned_progress_json`'s `month` values are plain
`"YYYY-MM"` strings in a JSON column, carry no offset and get none; the four
money lines carry no date.

**The `today` contract, stated precisely, because an injected `Date` is exactly
where a local-calendar read slips back in.** The helper's signature is
`plannedProgress(payload: unknown, today: Date = new Date()): number | null`.
A `Date` is an instant, not a calendar date: the parameter carries **no**
calendar of its own, and the helper may read it only through
`getUTCFullYear()`/`getUTCMonth()` (or an equivalently UTC-only path such as
`toISOString().slice(0, 7)`). `getFullYear`, `getMonth`, `toLocaleDateString`
and any `Intl.DateTimeFormat` are forbidden in both new modules. §5 requires
two boundary cases that **fail** if a local accessor is used, in either sign of
offset, so the rule is enforced and not merely written down.

### 1c. The API field

`planned_progress_json` is exposed on **`ProjectDetailRead` only**
(`backend/app/schemas/project.py`), typed as a nullable list of objects, and
filled **explicitly** in `ProjectService.get_project_detail`
(`backend/app/services/project_service.py @ 115`). Explicitly, because that
method builds its payload as `ProjectDetailRead(**base_read.model_dump(), ...)`
— a field declared there but not passed would answer `null` from the detail
route forever, which is the exact trap the `cover_photo_display_url` comment
already in that method records.

It is **not** added to `ProjectBase`, `ProjectRead`, `ProjectCreate` or
`ProjectUpdateSchema`: the write schemas must stay unable to set it, and the
list route must not start shipping a curve per row. The frontend mirror is a
new `PlannedProgressPoint` on `ProjectDetail` (not on `ConstructionProject`) in
`frontend/src/types/project.ts`.

## 2. Behaviour

**Balance cylinder** (`components/ProjectBudgetCylinder.tsx`) — rendered in the
selected project's detail region of `ConstructionTrackerPage.tsx`, at the site
where `BudgetVsActualProgressBar` is rendered today (~line 417). A tank whose
filled height is `remainingPct` clamped to `0..100`, beside four labelled
lines: `orçamento previsto`, `executado`, `saldo`, `% executado` (one decimal).
`total === 0` fills the tank completely (0 % executed, 100 % remaining) and
prints `0.0%`.

**Which number the text shows, and where the clamp is.** The *geometry* — the
filled height of the tank — is `remainingPct` clamped to `0..100` inside the
component, so no SVG coordinate is ever negative or past the rim. The *text*
shows the **unclamped** `remainingPct`, exactly as `_budget_html` does: at
`executed > total` the report prints `-20%`, and so does this card, in
`text-destructive`, because an over-budget obra reading `0%` would hide the one
fact the síndico needs. So the division of labour is: `budgetFigures` never
clamps; the component clamps geometry only; the printed percentage is the
helper's own number. The remaining percentage is printed as text so the figure
is readable with no colour and no SVG (WCAG 1.4.1 — the same reason
`_budget_html` prints the balance beside the gauge).

**Planned-vs-actual bar**
(`components/PhysicalProgressPlannedVsActualBar.tsx`) — the report's figure,
and it has **four** parts, not three (`_one_bar` + the pinned stylesheet's
`.one .seg.a`, `.one .seg.b`, `.one .seg.b.behind`, `.one .mark`):

1. the **realized** segment, from `0` to `min(planned, realized)`;
2. the **gap** segment, from `min` to `max` — the distance between plan and
   reality, and it carries the status: the stylesheet paints it `--brand-alt`
   normally and `#c0392b` at opacity `.7` when `realized < planned`. The
   baseline's own bar is in that second state
   (`<div class="seg b behind" style="left:42%;width:22%">`), so this is not a
   rare branch — it is what a late obra looks like, which is most of them;
3. the **planned marker**, a rule at `planned`;
4. the two labels `previsto` / `realizado`, each with its percentage, formatted
   by `formatPercent(value, 0)` (§1a-bis — `42.5` must print `42%`).

**Behind is never signalled by colour alone.** Besides the gap's colour, the
plan label carries a short text state when `realized < planned` — a new i18n
key rendering as `abaixo do previsto` / `below plan` — and the track's
`aria-label` names both numbers and the state. WCAG 1.4.1 again: the two
components must be readable in greyscale.

With no curve (`plannedProgress` returns `null`) the realized segment is drawn
alone — **no gap, no marker**, matching `_one_bar`'s documented branch — the
plan label reads `—`, and nothing throws: `planned_progress_json` `null`, `[]`,
`{}`, `[{}]` and `[{"month":"nope","pct":1}]` all land there. In every one of
those cases the realized segment is still **present and rendered**; "throws
nothing" is not satisfied by rendering nothing.

**One deliberate divergence from the report, named so it is not mistaken for a
defect:** the report's `.one .mark` is a `--card`-coloured hairline, which is
near-invisible on a light card; here the marker is `bg-foreground`. The parity
pin of §5 covers the **numbers**, never the pixels, and this is the only
appearance difference the spec sanctions *as written*.

**One further divergence, pre-sanctioned so answer A to open question 2 cannot
contradict this section later.** `_cylinder_svg` prints the **clamped**
`{filled:.0f}%` *inside* its tank, while this card prints the **unclamped**
percentage (`-20%`) wherever that number lives. If the operator answers **A**
(number inside the tank), that in-tank number is still the unclamped one — the
over-budget fact outranks pixel parity, and §2's rule above is hereby read as
sanctioning this second divergence too. Under **B** (the current pick) the
question does not arise, because the report prints no number outside its tank.
Either way `budgetFigures` never clamps and the geometry always does.

Both components take plain numbers and the raw curve as props and issue no
request; the page already holds `useProjectDetail`'s payload.

## 3. Tokens and contrast (result 4)

Checked against `frontend/src/index.css`; every one of these exists in the
`@theme` block, so **no new token and no new
`themeTokenMigration.exceptions.json` entry is needed** (it stays at 882
entries):

| Element | Class |
| --- | --- |
| Card surface / border | `bg-card`, `border-border` |
| Tank body (unfilled) / bar track | `fill-muted`, `stroke-border` / `bg-muted` |
| Tank fill + bar realized segment | `fill-primary` / `bg-primary` |
| Bar gap segment, **ahead** (`realized >= planned`) | `bg-primary/30` |
| Bar gap segment, **behind** (`realized < planned`) | `bg-destructive/70` (mirrors the report's `#c0392b` at `.7`) |
| Bar planned marker | `bg-foreground` (a rule, not a tint) |
| Labels | `text-foreground`, `text-muted-foreground` |
| Behind-plan label + negative remaining-% | `text-destructive` |

**Why the gap is a primary tint and not a second hue.** The report's ahead-gap
rides `--brand-alt` (a gold). This theme has no gold: `--secondary`, `--accent`
and `--muted` are all `oklch(0.96 0.01 160)` in `:root`, so a `bg-secondary` gap
would be invisible against a `bg-muted` track. `bg-primary/30` is a tint of the
realized segment's own colour, which reads as "the same work, not done yet", and
is legal here: `brandTextOpacity.test.ts` forbids an opacity modifier on brand
**text** (`text-primary/NN`), not on a background. `bg-destructive/70` follows
the same shape and the same precedent as the existing `bg-destructive/10` sites.
Neither segment's colour is load-bearing for comprehension — the two labels
print both numbers and the behind state is also text — so no new contrast ratio
is claimed for them. **The ahead gap is expected to look faint:** `bg-primary/30`
composited over the `bg-muted` track differs from it by roughly `1.3–1.4:1`, by
design — it is an "ahead of plan" grace band, not a value the síndico reads off
the pixels. A reviewer should not read that faintness as a missing fill.

**Two repo-wide pins the new files must respect**, both enforced by tests:

1. `text-primary-text` is pinned to **`ConstructionTrackerPage.tsx` and no
   other file** (`src/__tests__/themeTokenMigration.test.ts`, the
   `characters(...)` case). A new component using it fails the suite.
2. A bare `text-primary` anywhere in the tree needs an entry in
   `GRAPHICAL_PRIMARY_SITES` (`src/__tests__/brandTextRole.test.ts`). Avoid it:
   `-primary` is a **surface** colour here and fails AA as text.

**Contrast readings**, taken from the measured values `index.css` and
`brandTextRole.test.ts` already record, so no new measurement is invented:
`--primary` as text on `--card` is **3.4054:1** (fails AA) — which is why no
label is set in `--primary`. If the percentage is drawn *inside* the fill
(option A in the mock), its only AA-clean fill is `--primary-foreground`, at
**5.7588:1** on `--primary`. Outside the tank, on `--card`, `--foreground` is
near-black and `--muted-foreground` measures **4.6684:1** on `--muted`. No new
grey is introduced anywhere — the recorded case of a mock's own grey failing AA
and needing to be darkened is avoided by using only tokens that are already
measured.

If `fill-primary` / `fill-muted` / `stroke-border` do not compile under this
Tailwind 4 setup (they are the colour namespace, so they should), the
sanctioned fallback is an inline `style={{ fill: "var(--primary)" }}` — never a
hex literal and never a palette class, both of which the guard's grammar
catches.

## 4. Files touched

- `backend/app/schemas/project.py` — `planned_progress_json` on `ProjectDetailRead`.
- `backend/app/services/project_service.py` — pass it explicitly in `get_project_detail`.
- `frontend/src/types/project.ts` — `PlannedProgressPoint`; the field on `ProjectDetail`.
- `frontend/src/features/project-management/lib/budgetFigures.ts` — **new**, the five figures.
- `frontend/src/features/project-management/lib/plannedProgress.ts` — **new**, `planned_to_date`'s mirror.
- `frontend/src/features/project-management/components/ProjectBudgetCylinder.tsx` — **new**.
- `frontend/src/features/project-management/components/PhysicalProgressPlannedVsActualBar.tsx` — **new**.
- `frontend/src/features/project-management/components/ConstructionTrackerPage.tsx` — two imports and the two render sites.
- `frontend/src/i18n/locales/pt.json`, `.../en.json` — the new labels in **both**
  (`src/i18n/__tests__/parity.test.ts` fails on a key present in one only).
- `frontend/src/__tests__/themeTokenMigration.test.ts` — see §6, line-number bump only.
- `frontend/src/features/project-management/__tests__/…` — the tests of §5.
- `backend/tests/test_projects.py` — the detail-payload case of §5.

## 5. Test criteria

**The parity test (result 5) is the design, not an afterthought.** The figures
are computed twice, in two languages, and the only thing that stops them
diverging is that the frontend's expectations are *bytes the backend produced*.
They are: `backend/tests/data/report_page_null_detail_baseline.html` is the
single real `div.page` the backend renders for a declared fixture project
(`backend/tests/test_project_stage_detail.py` — `null_detail_project()`, and
`test_the_all_null_page_renders_the_committed_baseline` pins the file byte for
byte, with a documented regeneration command). The frontend already imports
that file with `?raw` in
`frontend/src/features/project-management/__tests__/fixtures/obraReportFixture.ts`, and
`vitest.config.ts` already allows that one directory outside the frontend root
(APRAS-118's precedent), so no config change is needed.

So the new Vitest case:

1. parses the baseline with `DOMParser` and reads `.budget-col .budget-row`
   and `.cyl .txt strong`;
2. takes the **inputs** from the first two rows — `Orçamento previsto`
   (`R$ 480.000,00`) and `Executado` (`R$ 204.000,00`) — parsed back to
   numbers, and feeds *those* to `budgetFigures` and to the rendered component;
3. **guards against degeneracy before comparing anything.** This is the one way
   this design rots: if a selector stops matching, or the pt-BR parse yields
   `""`/`0`/`NaN`, the comparison becomes trivially true and the test keeps
   passing while the figures diverge. So the case asserts, as preconditions,
   that it read exactly **five** nodes — the four `.budget-col .budget-row`
   rows **and** the one `.cyl .txt strong` — each matching exactly once, that the two parsed
   inputs are `480000` and `204000` (both `> 0`, both finite), and that each of
   the three expected strings read out of the baseline is non-empty and contains
   a digit. Only then does it compare;
4. asserts the rendered `saldo`, `% executado` and remaining percentage equal
   the baseline's own `Saldo` (`R$ 276.000,00`), `% executado` (`42.5%`) and
   `Saldo restante` (`58%`) strings.

**The space in `R$ 276.000,00` is not the same space on both sides, and the
comparison must say so.** `_brl` builds `"R$ " + …` with U+0020; `formatCurrency`
is `Intl.NumberFormat('pt-BR', { style: 'currency' })`, which emits U+00A0 —
verified: the rendered string's first three code points are `52 24 A0`. A
literal `toBe` therefore fails. The sanctioned resolution, so that it is read as
a stated normalisation and not a loosened assertion: both sides pass through one
named helper in the test file, e.g. `normaliseSpaces`, that replaces U+00A0 and
U+202F with U+0020 and nothing else. Digits, thousands separators, the decimal
comma and the `R$` prefix are still compared character for character. Writing a
second currency formatter to dodge the NBSP is explicitly **not** the way out —
`features/project-management/utils/currency.ts` stays the single formatter.

The three asserted values are **derived** by the backend and not re-derivable
from the two parsed inputs without doing the arithmetic, so neither side's
expectation is hand-written and a hardcode-both-sides pass is impossible. The
test throws a named error if any of those five nodes is missing — the
`.cyl .txt strong` cylinder label included, since it is what supplies the
`58%` — so a backend
rename fails loudly instead of yielding a vacuous fixture (again the
`obraReportFixture.ts` pattern).

**A rounding case the baseline cannot supply (§1a-bis).** The fixture's `42.5`
and `57.5` are the two halves where both rounding modes agree, so the parity
case above cannot see a half-away-from-zero frontend. A separate unit case
therefore pins `formatPercent` directly against Python's measured output:
`(56.5, 0) → "56"`, `(2.5, 0) → "2"`, `(42.5, 0) → "42"`, `(57.5, 0) → "58"`,
`(42.25, 1) → "42.2"`, `(2.675, 2) → "2.67"` and — because the cylinder now
prints negative percentages — the negative tie `(-20.5, 0) → "-20"`, which is
what `format(-20.5, '.0f')` gives where `toFixed(0)` gives `-21`. The four
`:.0f` positives and the negative are stated as the figures `f"{v:.0f}"` prints,
with that formula in the test's comment; `toFixed` fails **five of the seven**
(only `57.5` and `2.675` agree). A second case drives the whole card at
`total = 400000, executed = 174000` and asserts the printed remaining percentage
is `56%`.

For the bar, the same baseline carries `.pv .tag.plan b` = `64%` and
`.pv .tag.real b` = `42%`. The curve that produced it is
`test_project_stage_detail.PLANNED_CURVE` — three points, all in **2020**, so
the latest-past-point selection has the same **forward stability** the backend
claims for itself, and the pin cannot rot with the calendar. The frontend test
restates that curve as its input (citing the backend module) and asserts
`plannedProgress` returns the baseline's `64`, and that the component renders
`42%` for `physical_progress_pct = 42.5` — which is itself a rounding
discriminator, since `toFixed(0)` yields `43`.

Other cases:

- `formatPercent`: the seven pairs above, plus its **domain**: the
  `toFixed(20)` reading is sound for percentages because the ULP of any value in
  `-100..100` is ≈ 1e-14, far above the 20th decimal, so no true non-tie can be
  flattened into one. Defensively (expected result 2 already forbids `NaN`
  reaching it from `budgetFigures`), the helper must not emit garbage for
  `NaN`/`±Infinity` — whose `toFixed(20)` has no `"."`, so index arithmetic over
  the decimal expansion **throws** on them unless they are guarded first. The
  guard is stated here rather than left to the implementer: a non-finite input
  returns Python’s own literal for it — `"nan"`, `"inf"`, `"-inf"`
  (`format(float("nan"), ".0f")` is `nan`) — which keeps the helper a mirror of
  `format` across its whole domain. The reference implementation in
  `APRAS-102-mock.html` carries that guard as its first two lines; the test pins
  all three outputs. `decimals` is documented as `0..2`.
- `budgetFigures` (helper, no geometry): `total = 0` → `executedPct = 0`,
  `remainingPct = 100`, `Number.isNaN` false for every returned field;
  `executed > total` → `remainingPct` is **negative** and `balance` is negative,
  because the helper mirrors an unclamped backend; `saldo = total − executed`
  asserted on a value where a sign error would show.
- `ProjectBudgetCylinder` (component, where the clamp lives) — **the clamp
  assertion, stated against the strings the figure actually emits.** The tank
  mirrors `_cylinder_svg @ 869`, whose closing stroke is a *relative* upward
  vertical, so the outline's own `d` legitimately contains `v-120` and the
  emptied fill's contains `v-0.0`. A scan for `/-\d/` over rendered attribute
  values therefore fails on a **correct** mirror and must not be used; relative
  command operands are not coordinates. What is asserted instead is the thing
  being clamped.

  **The two nodes the test reads are named, because neither is unique by tag.**
  The figure renders **two** `path` nodes (outline and fill) and **two**
  `ellipse` nodes (the liquid surface at `cy = fy`, the rim at `cy = 20`), so
  "the fill path" and "the liquid-surface ellipse" are not selectable by tag:
  picking the outline or the rim makes the assertion read `20` where it expects
  `140` and fails on a *correct* component. The component must therefore expose
  two hooks, which the reference implementation in `APRAS-102-mock.html` already
  carries: `data-testid="cylinder-fill"` on the fill `path` and
  `data-testid="cylinder-surface"` on the liquid-surface `ellipse`. The test
  selects by those ids and nothing else.

  The test asserts, **as a precondition**, that `cylinder-fill` matched exactly
  one node and `cylinder-surface` matched exactly one node, before parsing
  either — otherwise a never-rendered fill fails by throwing inside the `d`
  parse instead of by a stated assertion, which is a crash rather than a
  report. It then parses the fill's `d` and reads `yStart` (the move-to's `y`)
  and `h` (the first vertical operand, the fill height). With the tank's
  `top = 20`, `bottom = 140`:
  - `executed > total` → `yStart === bottom` (`140`) and `h === 0` — an empty
    tank — and `cylinder-surface`'s `cy === 140`;
  - `total = 0` → `yStart === top` (`20`) and `h === 120` — a full tank;
  - in both cases the **two absolute y coordinates the test reads** — `yStart`
    and `cylinder-surface`'s `cy` — both lie in `20..140`, hence inside the
    `0 0 120 165` viewBox. No other number in the markup is asserted on: the
    fill's move-to `x` is `10` and the arc's `rx 50 ry 12` are absolute lengths
    outside that range, by design, and relative command operands (the outline's
    own `v-120`) are not coordinates at all.

  Checked against the literal output of the reference implementation in
  `APRAS-102-mock.html` (`cylinderCard`): at `executed > total` the fill `d` is
  `"M10 140.0 v0.0 a50 12 0 0 0 100 0 v-0.0"`, at `total = 0` it is
  `"M10 20.0 v120.0 a50 12 0 0 0 100 0 v-120.0"`, and at the baseline's
  `480000/204000` it is `"M10 71.0 v69.0 a50 12 0 0 0 100 0 v-69.0"`; the
  outline is `"M10 20 v120 a50 12 0 0 0 100 0 v-120"` in all three. An
  implementation that forgot the clamp yields `yStart = 164` and `h = -24` at
  `executed > total`, so all three assertions fail — the criterion is true in
  exactly the clamped cases and false otherwise. Numbers are parsed and
  compared numerically, so no particular `toFixed` precision is imposed.

  The printed text at `executed > total` reads the unclamped negative
  percentage and carries `text-destructive`.
- `plannedProgress`: `null`, `[]`, non-list, a point with a bad `month`, a
  point with a boolean or string `pct`, all future months → `0`, and a mixed
  past/future curve → the latest past point. Each assertion mutates the input
  and checks the mutation changes the output, so no case passes vacuously.
- **Two UTC-boundary cases, which are the only ones that can tell `getUTCMonth`
  from `getMonth`.** Every case listed above returns the same value under
  either, so without these the hazard §1b calls "intermittent and
  unreproducible" ships unguarded. The test file sets `process.env.TZ` before
  constructing any `Date` (Node re-reads it) and runs both signs of offset, so
  it discriminates whatever zone CI happens to use. It also **restores** `TZ`
  (`vi.stubEnv`, or an `afterAll` putting back the prior value): the default
  Vitest pool isolates files today, so nothing leaks, but this tree has many
  TZ-sensitive date suites (`DueDateBadge`,
  `purchase-management/utils/formatters.test.ts`, `TaskCard`) and no existing
  `process.env.TZ` precedent, so the restore is what keeps a future
  `isolate: false` from failing somewhere else entirely. The cases:
  - `TZ=America/Sao_Paulo` (UTC−3), `today = new Date("2020-03-01T00:30:00Z")`,
    curve `PLANNED_CURVE` → **`64`**. A local read sees `2020-02-29` and returns
    `31.5`, so the assertion is `expect(...).toBe(64)` with `31.5` named in a
    comment as the value a local-calendar bug produces.
  - `TZ=Europe/Berlin` (UTC+2), `today = new Date("2020-03-31T23:30:00Z")`,
    curve `PLANNED_CURVE` plus a trailing `{ month: "2020-04", pct: 80 }` →
    **`64`**. A local read sees April and returns `80`.
- The bar component, for each of `planned_progress_json` = `null`, `[]`, `{}`
  and `[{ "month": "nope", "pct": 1 }]`: nothing throws, the realized segment is
  **present** in the output with a non-zero width for a non-zero
  `physical_progress_pct`, the plan label reads `—`, and no gap segment and no
  marker is rendered.
- The bar's **ahead and behind** states: with `planned = 64, realized = 42.5`
  the gap segment is rendered with the behind class (`bg-destructive/70`) and
  the below-plan text is present; with `planned = 42, realized = 64` the same
  gap is rendered with `bg-primary/30` and that text is absent. Both assert the
  gap element's inline `style.left` and `style.width` are the percent strings
  for `min` and `max − min` — so at the behind case above
  (`planned = 64, realized = 42.5`) they are `left: "42.5%"` and
  `width: "21.5%"`, the raw numbers and not the rounded labels. (The baseline's
  own `seg b behind` carries `left:42%;width:22%` because the backend's
  stylesheet writes the `:.0f` figures; the frontend positions on the
  unrounded values, and only the two labels go through `formatPercent`.) This
  pins the positioning unit so it is not left to the implementer.
- `ConstructionTrackerPage` renders both new elements after a project is
  selected, with the detail payload's figures.
- Backend: `GET /api/v1/projects/{id}` returns the stored curve and `null` for
  a project without one; `GET /api/v1/projects` items carry **no**
  `planned_progress_json` key; `PUT /api/v1/projects/{id}` with a
  `planned_progress_json` body in it answers **`200`** (the unknown key is
  ignored, not rejected — a 422 would mean the write schema had grown the
  field), and a re-read of the project shows the column **unchanged** from its
  seeded value.
- Result 6: `backend/app/services/project_report_service.py` appears in **no
  hunk** of this task's diff, `report_page_null_detail_baseline.html` is
  byte-identical, and `uv run pytest tests/test_project_stage_detail.py
  tests/test_project_report.py` is green.
- Result 7: the whole `npm test` suite passes and coverage stays above the gate
  `frontend/vitest.config.ts` actually configures — **`lines: 80`,
  `functions: 78`, `branches: 76`, `statements: 80`** (ratcheted by APRAS-36;
  there is no 75 % anywhere in this repository, and a run at 77 % lines fails
  `npm test`). `npm run lint` carries ~375 pre-existing errors
  across 64 files — the criterion is **no worse than base**, measured before
  and after, never "zero".

## 6. Two collateral hazards, named so review does not discover them

1. **The theme guard pins palette occurrences by line number.**
   `themeTokenMigration.test.ts` pins `ConstructionTrackerPage.tsx` at lines
   **240, 313, 314, 359**. Adding import lines at the top of that file shifts
   all four. Bump them by exactly the number of lines inserted above them and
   add a one-line comment naming APRAS-102 — the class **sets** must stay
   identical, which is what makes the bump a bookkeeping change. APRAS-104 did
   the same thing and left its comment in place as the precedent.
2. **`BudgetVsActualProgressBar.tsx` is not touched.** It holds 11
   grandfathered palette exceptions and is pinned in the guard at lines 23–46.
   Deleting or editing it drags both the exceptions file and that ledger into
   this PR. See the open question below.

## Expected Results

- [ ] `GET /api/v1/projects/{id}` returns `planned_progress_json` (the stored
      curve, or `null`); `GET /api/v1/projects` items carry no such key; and
      `PUT /api/v1/projects/{id}` sent a `planned_progress_json` body answers
      `200` with the stored curve unchanged on re-read.
- [ ] Selecting a project in the internal construction tracker shows a balance
      cylinder whose filled proportion is the remaining-budget percentage
      (`100 − executed/total × 100`, and `0 %` executed when the total budget is
      `0`). A unit test of the `budgetFigures` helper covers `total = 0` and
      `executed > total`, asserts no returned field is `NaN`, and asserts the
      helper returns a **negative** `remainingPct` when `executed > total`
      (it mirrors an unclamped backend). A separate component test asserts the
      clamp on two named nodes the component exposes —
      `data-testid="cylinder-fill"` (the fill `path`) and
      `data-testid="cylinder-surface"` (the liquid-surface `ellipse`) — since
      the figure renders two `path` nodes and two `ellipse` nodes and neither is
      selectable by tag. The test first asserts each of those two ids matched
      **exactly one** node, then parses the fill’s `d` and reads its move-to `y`
      (`yStart`) and first vertical operand (`h`, the fill height), with the
      tank’s `top = 20` and `bottom = 140`: at `executed > total`
      `yStart === 140` and `h === 0` (empty tank) and `cylinder-surface`’s
      `cy === 140`; at `total = 0` `yStart === 20` and `h === 120` (full tank);
      and in both cases the two absolute y coordinates the test reads — `yStart`
      and `cylinder-surface`’s `cy` — both lie in `20..140`. No other number in
      the markup is asserted on: the fill’s move-to `x` is `10` and the arc’s
      `rx 50 ry 12` are absolute lengths outside that range by design, and
      relative command operands (the outline’s own `v-120`) are not coordinates
      at all. The printed percentage shows the unclamped negative value in
      `text-destructive`.
- [ ] The same view shows four labelled money lines — `orçamento previsto`,
      `executado`, `saldo`, `% executado` — with `saldo = total − executed` and
      the percentage to one decimal place.
- [ ] Percentages are formatted half-to-even, mirroring Python's `format`: a
      unit test of `formatPercent` asserts `(56.5, 0) → "56"`, `(2.5, 0) → "2"`,
      `(42.5, 0) → "42"`, `(57.5, 0) → "58"`, `(42.25, 1) → "42.2"`,
      `(2.675, 2) → "2.67"` and `(-20.5, 0) → "-20"` (`toFixed` gives `-21`);
      the same test pins the non-finite guard — `NaN → "nan"`, `Infinity → "inf"`,
      `-Infinity → "-inf"`, Python's own literals — which the helper must apply
      before touching the decimal expansion, since `NaN.toFixed(20)` has no `"."`;
      and a card-level test at `total = 400000,
      executed = 174000` renders the remaining percentage as `56%` (not `57%`).
- [ ] The same view shows a planned-vs-actual physical-progress bar driven by
      `planned_progress_json`, with a realized segment, a gap segment between
      plan and reality, a planned marker and the `previsto` / `realizado`
      labels. The gap carries the status: a test with `planned = 64,
      realized = 42.5` renders it with `bg-destructive/70` plus a visible
      below-plan text and the gap’s inline `left: "42.5%"` / `width: "21.5%"`
      (the unrounded values, not the rounded labels), and a test with
      `planned = 42, realized = 64` renders it with `bg-primary/30` and without
      that text.
- [ ] The bar selects the latest curve point whose month is `<=` the current
      **UTC** month, proved by two boundary cases that fail under a local
      calendar: with `TZ=America/Sao_Paulo` and
      `today = new Date("2020-03-01T00:30:00Z")` the helper returns `64` (a
      local read returns `31.5`), and with `TZ=Europe/Berlin` and
      `today = new Date("2020-03-31T23:30:00Z")` over the same curve plus
      `{ month: "2020-04", pct: 80 }` it returns `64` (a local read returns
      `80`).
- [ ] For each of `planned_progress_json` = `null`, `[]`, `{}` and
      `[{"month":"nope","pct":1}]` the bar renders without throwing **and**
      positively: the realized segment is present with a non-zero width for a
      non-zero `physical_progress_pct`, the plan label reads `—`, and no gap
      segment and no marker is rendered.
- [ ] A Vitest case parses `backend/tests/data/report_page_null_detail_baseline.html`,
      feeds the baseline's own `Orçamento previsto` and `Executado` into the new
      helper and components, and asserts the rendered `saldo`, `% executado` and
      remaining percentage equal the baseline's `R$ 276.000,00`, `42.5%` and
      `58%` — compared after a named whitespace normalisation that maps U+00A0
      and U+202F to U+0020 and changes nothing else, since `Intl` emits an NBSP
      where `_brl` emits a space. The case first asserts its own
      non-degeneracy: all **five** nodes it reads — the four
      `.budget-col .budget-row` rows and the one `.cyl .txt strong` that carries
      the `58%` — each matched exactly once, the two parsed inputs are `480000`
      and `204000`, and each expected string is non-empty and contains a digit;
      it fails with a named error if any of those five is absent. A second case
      asserts the planned-to-date helper returns the baseline's `64` for `test_project_stage_detail.PLANNED_CURVE`,
      and that the bar renders `42%` for `physical_progress_pct = 42.5`.
- [ ] Both new components are React components using only semantic theme tokens:
      no raw palette class (`bg-emerald-600`, `text-slate-500`, …) is added, no
      new entry appears in `themeTokenMigration.exceptions.json` (it stays at 882),
      and `themeTokenMigration.test.ts`, `brandTextRole.test.ts` and
      `themeContrast.test.ts` all pass — with the pinned
      `ConstructionTrackerPage.tsx` line numbers bumped by the inserted import
      lines and their class sets unchanged.
- [ ] `backend/app/services/project_report_service.py` appears in no hunk of the
      diff, `backend/tests/data/report_page_null_detail_baseline.html` is
      byte-identical, and `backend/tests/test_project_stage_detail.py` and
      `test_project_report.py` pass.
- [ ] New UI labels — including the below-plan state label — exist in both
      `pt.json` and `en.json` and `src/i18n/__tests__/parity.test.ts` passes.
- [ ] The whole frontend test suite passes with coverage at or above every
      threshold `frontend/vitest.config.ts` configures (`lines: 80`,
      `functions: 78`, `branches: 76`, `statements: 80`), and `npm run lint`
      reports no more errors than the pre-task baseline (~375 across 64 files).

## Open questions for the operator

Both are visual and both are drawn, side by side and labelled **A** and **B**,
in `docs/tasks/APRAS-102-mock.html` on the real screen they affect. One letter
each is a complete answer.

1. **The existing "Acompanhamento Orçamentário" card.** The internal view
   already has a green financial-execution bar with three money tiles. The new
   cylinder shows the same money, better. **A** keeps both cards (nothing is
   deleted, but the screen states the budget twice). **B** lets the cylinder
   replace that card. The spec currently picks **A**, only because **B** also
   means deleting 11 grandfathered palette exceptions and their ledger entries
   in this same PR. See the mock, section *"Orçamento: um cartão ou dois"*.
2. **Where the remaining-balance percentage is printed.** **A** puts the big
   number inside the tank, on the green fill. **B** puts it beside the tank, on
   the white of the card. Both are legible as drawn (inside the tank the number
   is near-black `--primary-foreground` on green, 5.7588:1). The one difference
   is what happens at a nearly spent budget: in **A** the number is positioned
   relative to the liquid level, so under roughly 8 % remaining it sits below the
   tank's bottom edge and lands on the card; in **B** it never moves. The spec
   currently picks **B**. See the mock, section *"O número do saldo"* — drag the
   slider to 5 % and judge both.
