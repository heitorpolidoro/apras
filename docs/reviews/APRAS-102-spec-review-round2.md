# APRAS-102 — spec review, round 2 (findings-only)

VERDICT: NEEDS_REVISION

Reviewed `docs/tasks/APRAS-102-spec.md` and `docs/tasks/APRAS-102-mock.html`
against the seven blocking findings of round 1. Scope of this pass: the seven
findings, plus a consistency check limited to the sections the revision
changed. Nothing was staged, committed or edited; no test suite was run; no
`npm install` / `uv sync`.

## What was verified, and how

### B1 — rounding mode (resolved)

`formatPercent`'s reference implementation now lives in the mock
(`APRAS-102-mock.html`, lines 364–400). I ran it in Node 24 against 18 probes
and compared every one against `python3 -c "format(v, '.Nf')"`:

| value | dec | Python | mock helper | `toFixed` |
| --- | --- | --- | --- | --- |
| 56.5 | 0 | 56 | 56 | 57 |
| 2.5 | 0 | 2 | 2 | 3 |
| 42.5 | 0 | 42 | 42 | 43 |
| 57.5 | 0 | 58 | 58 | 58 |
| 42.25 | 1 | 42.2 | 42.2 | 42.3 |
| 2.675 | 2 | 2.67 | 2.67 | 2.67 |
| 99.95 | 1 | 100.0 | 100.0 | 100.0 |
| 9.95 | 1 | 9.9 | 9.9 | 9.9 |
| −20.5 | 0 | −20 | −20 | −21 |
| −0.5 | 0 | −0 | −0 | −1 |

Plus 0/100/42.5@1/58/5/1e-9 — all agree with Python. So the mock's helper is a
correct reference, the `2.675` case does discriminate the naive
scale-and-re-round variant (the exact expansion is `2.67499…`, and the helper
reads it via `toFixed(20)`), and the pinned set in §5 / expected result 4
discriminates `toFixed` on four of its six pairs. The §1a-bis rule is stated
precisely enough — "decide on the exact decimal expansion of the double (what
`toFixed(20)` yields) rather than scaling and re-rounding" — that an
implementer who follows it, or copies the mock, lands on the right one.

One prose slip, non-blocking: §5 says "`toFixed` fails three of the six". It
fails **four** (56.5, 2.5, 42.5, 42.25); only 57.5 and 2.675 agree. No
criterion depends on the count.

### B2 — NBSP (resolved)

`Intl.NumberFormat('pt-BR', {style:'currency',currency:'BRL'}).format(276000)`
yields code points `52 24 A0 32` — confirmed NBSP. `_brl` uses U+0020. The
`normaliseSpaces` resolution (U+00A0 and U+202F → U+0020, nothing else) is a
stated normalisation that still compares digits, separators and the `R$`
prefix character for character, and the spec explicitly forbids a second
formatter. `frontend/src/features/project-management/utils/currency.ts` is the
single `Intl` formatter in this feature (there is a second, unrelated
`formatCurrency` in `purchase-management/utils/formatters.ts`; the spec's bare
"`utils/currency.ts`" resolves unambiguously from the new modules' location,
but naming the full path would remove the last doubt).

### B3 — behind-plan signal (resolved)

- `--secondary`, `--accent` and `--muted` are each `oklch(0.96 0.01 160)` in
  `frontend/src/index.css` `:root` (lines 53, 55, 60). The spec's claim holds,
  so a second hue genuinely is unavailable and a `bg-secondary` gap would be
  invisible on a `bg-muted` track.
- The opacity modifier is legal here. `src/__tests__/brandTextOpacity.test.ts`
  (APRAS-90) grammars brand **text** tokens only (`text-primary-text`,
  `text-primary`, `text-indigo-<scale>`), with `-` excluded on both sides; a
  `bg-` utility is outside it. Precedent for opacity-modified semantic
  backgrounds exists and is pinned in the migration guard: `bg-foreground/70`,
  `bg-card/70`, and `bg-destructive/10` at nine sites.
- The non-colour signal is specified concretely, not gestured at: a new i18n
  key (`abaixo do previsto` / `below plan`) on the plan label, both locales
  (parity test), the state in the track's `aria-label`, and a test asserting
  the text is present at `planned = 64, realized = 42.5` and absent at
  `planned = 42, realized = 64`. That is mechanically checkable and satisfies
  1.4.1.

### B4 — clamp unit and the printed percentage (NOT resolved; see blocking)

The unit confusion is fixed: `budgetFigures` never clamps, the component
clamps geometry only, and the printed text is the unclamped number. Mirroring
the backend's `-20%` is the right call for an internal operator view — the
report's `_budget_html` prints it, the figure is the one fact an over-budget
obra must not hide, and the spec pins it in `text-destructive` with the text
present independent of the SVG. It is a deliberate mirror of a *documented*
backend behaviour (`_budget_html` never clamps; only `_cylinder_svg` does), not
a quirk adopted by accident.

The assertion chosen to prove the geometry clamp, however, cannot pass — see
the blocking finding.

### B5 — UTC month (resolved)

Both boundary cases check out arithmetically against
`backend/tests/test_project_stage_detail.PLANNED_CURVE`
(`2020-01→8.0`, `2020-02→31.5`, `2020-03→64.0`):

- `TZ=America/Sao_Paulo`, `2020-03-01T00:30:00Z`: UTC month `2020-03` → `64`;
  local is `2020-02-29 21:30` (UTC−3 in March 2020) → `2020-02` → `31.5`. ✓
- `TZ=Europe/Berlin`, `2020-03-31T23:30:00Z`, curve + `{2020-04, 80}`: UTC
  month `2020-03` → `64`; local is `2020-04-01 01:30` (CEST) → `80`. ✓
  Confirmed in Node 24: with `process.env.TZ = "Europe/Berlin"` set at runtime
  that Date reports `getMonth()+1 === 4` and `getUTCMonth()+1 === 3`.

Reliability: Node ≥ 16 re-reads `process.env.TZ` on assignment (verified
live — the change took effect after a prior local-date read). `vitest.config.ts`
sets neither `pool` nor `isolate`, so Vitest 5's defaults (forks, isolate
true) give each test file its own process and the assignment cannot leak into
the many TZ-sensitive suites in this tree (`DueDateBadge`,
`purchase-management/utils/formatters.test.ts`, `TaskCard`, …). There is no
existing `process.env.TZ` precedent in `frontend/src`, which is why restoring
it is worth stating — see suggestions.

### B6 — "throws nothing" (resolved)

§2 and expected result 7 both now require the realized segment to be
*present with a non-zero width* for a non-zero `physical_progress_pct`, in each
of `null`, `[]`, `{}`, `[{"month":"nope","pct":1}]`, plus plan label `—` and no
gap/marker. Rendering nothing no longer satisfies it. The helper semantics
match `planned_to_date @ 681` exactly, including bool-`pct` rejection and
strict whole-curve invalidation.

### B7 — coverage gate (resolved)

`frontend/vitest.config.ts` configures `lines: 80, functions: 78,
branches: 76, statements: 80`; the spec now quotes exactly those in §5 and in
expected result 12, with the lint criterion as "no worse than base (~375)".

### Other factual claims spot-checked

- `themeTokenMigration.exceptions.json` has **882** entries. ✓
- The guard references `ConstructionTrackerPage.tsx` at **313, 314, 359**
  (class sets match the file verbatim) and at **240** via
  `matchesOn("ConstructionTrackerPage.tsx", 240)` in the `bg-background` case.
  The §6 bump instruction is accurate and complete.
- `characters("ConstructionTrackerPage.tsx")` is pinned to length 2 and 0
  everywhere else — the §3 warning about `text-primary-text` is real.
- `--primary-foreground` on `--primary` is **5.7588:1** (recorded in three
  contrast suites); `--primary` as text on `--card` is **3.4054:1** and
  `--muted-foreground` on `--muted` **4.6684:1** (both recorded in
  `index.css`). No invented measurement.
- `frontend/src/features/project-management/__tests__/fixtures/obraReportFixture.ts`
  **exists** and already imports the baseline with `?raw`; `vitest.config.ts`
  already allows `../backend/tests/data`. No config change needed, as claimed.
- Baseline bytes: `R$ 480.000,00`, `R$ 204.000,00`, `R$ 276.000,00`,
  `42.5%`, `58%`, `previsto 64%`, `realizado 42%`, `seg b behind` at
  `left:42%;width:22%`, four `budget-row` nodes. Every asserted value in §5
  and expected result 8 matches the committed file.
- `formatPercent(57.5,0) = "58"` and `formatPercent(42.5,1) = "42.5"` — the
  parity assertions are satisfiable as written.

### The mock

Token values in `:root` (lines 12–24) were compared line by line against
`frontend/src/index.css` `:root`: `--background 0.99 0 0`, `--foreground
0.14 0.01 160`, `--card 1 0 0`, `--primary 0.62 0.15 160`,
`--primary-foreground 0.15 0.02 160`, `--primary-text 0.52 0.11 160`,
`--muted 0.96 0.01 160`, `--muted-foreground 0.53 0.02 160`, `--accent
0.96 0.01 160`, `--border 0.92 0.01 160`, `--destructive 0.58 0.24 27`. All
eleven are exact. No wrong-hue repeat of the sibling task's `--ring` defect.

Question 1: host A = legacy card + cylinder, host B = cylinder only, both
cylinders rendered by the identical `cylinderCard(figures, false)` call — the
cards differ in exactly one card. Question 2: A2 = `labelInside true`,
B2 = `labelInside false`, identical otherwise — differ in exactly where the
number is printed, and the drawn behaviour matches the prose (`labelY =
max(fy + 22, top + 30)`; at 8 % remaining `fy = 130.4`, so `labelY = 152.4`,
below the tank's `bottom = 140` — the same off-tank slide `_cylinder_svg`'s
docstring records). Question 2's wording argues for neither option: it states
the one behavioural difference and names the spec's current pick. Both
questions are answerable with one letter, and the slider instructions tell the
operator how to see each difference.

## Blocking Findings

- **§5, bullet "`ProjectBudgetCylinder` (component, where the clamp lives)",
  and expected result 2: "no rendered attribute value matches `/-\d/`" cannot
  pass against the geometry this spec sanctions.** The tank is a path mirroring
  `_cylinder_svg @ 869`, whose closing stroke is a *relative upward* vertical:
  the committed baseline contains `d="M10 20 v120 a50 12 0 0 0 100 0 v-120"`
  (and `v-69.0` for the fill), and the spec's own reference implementation in
  `APRAS-102-mock.html` (lines 455–458) emits exactly that shape. I ran it at
  `executed > total`: the two `d` attributes are
  `"M10 20 v120 a50 12 0 0 0 100 0 v-120"` and
  `"M10 140.0 v0.0 a50 12 0 0 0 100 0 v-0.0"`, and `/-\d/` matches **both**
  (`-120`, and `-0` in the clamped case). So the criterion fails on a correct
  implementation, and the only way to satisfy it is to rewrite the path in
  absolute commands — i.e. to diverge from the figure being mirrored, which §2
  forbids outside the one sanctioned marker divergence. Because this wording is
  in `expected_results`, QA sees it with no access to the spec or the diff and
  has no way to resolve the contradiction. Replace it with an assertion on what
  is actually being clamped — e.g. the fill path's `y` start equals `bottom`
  (fill height `0`) and every *coordinate* (as opposed to every relative
  command operand) lies in `0..165`, or assert on the derived `filled` value
  the component computes — and state it the same way in §5 and in expected
  result 2.

## Suggestions

- §5: "`toFixed` fails three of the six" should read **four** (56.5, 2.5, 42.5,
  42.25 differ; 57.5 and 2.675 agree). The spec's credibility rests on its
  measured numbers; this one is off by one.
- `formatPercent`'s domain is unstated. The `toFixed(20)` approach is sound for
  percentages (the ULP of any value in `0..100` is ≥ ~1e-14, far above the
  20th decimal, so no true non-tie can be flattened into a tie), but it is
  worth saying so, and worth saying what the helper does for `NaN`,
  `±Infinity` and `decimals` outside `0..2` — `Math.abs(NaN).toFixed(20)` has
  no `"."`, and the mock's index arithmetic would silently produce garbage.
  Expected result 2 already forbids `NaN` reaching it from `budgetFigures`, so
  this is defensive only.
- The pinned rounding pairs are all positive, yet the cylinder now prints
  negative percentages. `format(-20.5, '.0f')` is `-20` and `toFixed` gives
  `-21`; the mock already matches Python (`-20`, and `-0` for `-0.5`). Pinning
  one negative tie, e.g. `(-20.5, 0) → "-20"`, would guard the sign path the
  new unclamped text actually exercises.
- B5's test should restore `process.env.TZ` (an `afterAll`, or `vi.stubEnv`).
  The default Vitest pool isolates files today, so nothing leaks, but this
  tree has many TZ-sensitive date suites and no `process.env.TZ` precedent —
  the day someone sets `isolate: false` for speed, the failure appears
  somewhere else entirely.
- §5's bar bullets assert the gap's `left`/`width` "equal `min` and
  `max − min`" without saying in what unit or attribute (the mock uses
  `style.left`/`style.width` in `%`). Naming the percent-string form would
  remove the last implementation choice.
- The `bg-primary/30` ahead-gap composites to roughly a 1.3–1.4:1 difference
  against the `bg-muted` track. The spec correctly argues no contrast minimum
  applies (both numbers are printed and the marker is `bg-foreground`), but it
  is worth a sentence confirming the ahead gap is *expected* to be faint, so a
  reviewer of the implementation does not read it as a missing fill.
- If the operator answers **A** to question 2, the in-tank number would print
  the *unclamped* percentage, whereas `_cylinder_svg` prints the clamped
  `{filled:.0f}%` inside the tank — a second appearance divergence beyond the
  marker, which §2 says is the only one. Worth naming now so answer A does not
  silently contradict §2. Relatedly, in the mock's A2 card the "Saldo restante"
  caption is left with no number beneath it, which makes option A look
  defective in a way the real component would not be.
