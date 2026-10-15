# APRAS-102 — spec review, round 4 (findings-only re-review)

VERDICT: APPROVED

Scope of this round: the single round-3 blocking finding (two halves), plus the
four specific judgements the dispatch asked for, plus a whole-document
consistency pass over the sections the revision touched. Read at `2cb0d48`.

Nothing was written or edited under `frontend/` or `backend/`; nothing staged.
Scratch scripts live in the session scratchpad only.

---

## 1. Round-3 finding, half 1 — the y-only clause. RESOLVED.

### Is the clause identical in §5 and in expected result 2?

Not byte-for-byte, but the delta is additive and does not change the
requirement. §5 (lines 437–441) and result 2 (lines 554–559) differ in exactly
two places:

- §5 appends `, hence inside the 0 0 120 165 viewBox` after `20..140`;
  result 2 stops at `20..140`.
- §5 writes `outside that range, by design,`; result 2 writes
  `outside that range by design,` (one comma).

The operative content — *which* numbers are claimed, the range, and the
exclusion list — is word-identical. More importantly, **the sweeping shape is
gone**: the clause no longer says "every absolute coordinate read from the
fill". It names the set in the result itself — "the two absolute y coordinates
the test reads — `yStart` and `cylinder-surface`'s `cy`" — followed by the
closing universal "No other number in the markup is asserted on", which is a
statement about the test and is checkable by reading the test. A QA agent
holding result 2 alone can enumerate the asserted values without the spec. That
is what round 3 asked for.

### Is the exclusion list complete against what the reference implementation emits?

I parsed the three `d` strings the reference implementation (`cylinderCard` in
the mock) actually produces, by running its geometry:

| case | `remainingPct` | fill `d` | `cylinder-surface` `cy` |
| --- | --- | --- | --- |
| `executed > total` (480000/576000) | `-20` | `M10 140.0 v0.0 a50 12 0 0 0 100 0 v-0.0` | `140.0` |
| `total = 0` | `100` | `M10 20.0 v120.0 a50 12 0 0 0 100 0 v-120.0` | `20.0` |
| baseline (480000/204000) | `57.5` | `M10 71.0 v69.0 a50 12 0 0 0 100 0 v-69.0` | `71.0` |

All three match the spec's quoted strings verbatim (§5 lines 444–448).
Unclamped, `executed > total` gives `fy = 164`, `h = -24` — also exactly as the
spec states, so all three assertions fail on a missing clamp and the criterion
discriminates in the right direction.

Full token census of the fill `d`, against the exclusion list:

- `10` — move-to `x`. Named and excluded. ✓
- `140.0` / `20.0` / `71.0` — move-to `y` = `yStart`. Asserted. ✓
- `0.0` / `120.0` / `69.0` — first `v` operand = `h`. **Relative**, asserted as
  a height, not as a coordinate. Covered by "relative command operands … are
  not coordinates at all". ✓
- `50 12` — `rx ry`. Named and excluded. ✓
- `0 0 0` — the arc's x-axis-rotation and the two arc flags. **Not named in the
  exclusion list.** They are an angle and two booleans, not coordinates of any
  kind, and the preceding sentence ("No other number in the markup is asserted
  on") already forecloses them. Harmless omission.
- `100 0` — the arc endpoint. Lowercase `a`, so **relative**; covered by the
  relative-operand clause. ✓
- `-69.0` / `-120.0` / `-0.0` — closing relative `v`. Covered. ✓

So nothing else in the emitted `d` can be read as an absolute y coordinate, and
the clause is neither vacuous nor false. The round-2 `/-\d/` failure mode and
the round-3 range failure mode are both closed.

### One residual factual error in the aside (non-blocking)

"the arc's `rx 50 ry 12` are absolute lengths **outside that range**" is false
for `rx`: `50` lies inside `20..140`. `ry = 12` is outside. This appears in both
§5 and result 2. It is not load-bearing — nothing is asserted on `rx`/`ry`, and
the operative sentence is the preceding "No other number in the markup is
asserted on" — so a QA agent cannot be misled into a wrong pass or a wrong fail
by it. Recorded as a suggestion, not a blocking finding, because the previous two
rounds burned on exactly this sentence and I do not want a third round spent on a
parenthetical that constrains no behaviour.

Also confirmed, independently: the **backend's own** baseline emits
`<path d="M10 71.0 v69.0 a50 12 0 0 0 100 0 v-69.0" fill="url(#g)"/>` and
`<ellipse cx="60" cy="71.0" rx="50" ry="12" …/>`. The spec's mirror is
byte-identical to the figure it claims to mirror, which is stronger evidence than
the spec itself offers.

## 2. Round-3 finding, half 2 — node identification. RESOLVED.

§5 lines 415–430 and result 2 both: name the two `data-testid`s, state *why*
tag selection is impossible (two `path`, two `ellipse`, the rim at `cy = 20`
being the wrong-pick trap round 3 named), require the exactly-one-node
precondition **before** the `d` parse, and say the test "selects by those ids and
nothing else". The `executed > total` → `cy === 140` and `total = 0` → `cy === 20`
pair is now unambiguous about which ellipse supplies the `cy`. The wrong-pick
failure on a correct component is no longer reachable.

## 3. The sweep for a fourth too-broad clause — CHECKED, NOT TRUSTED.

I read all twelve results independently of the generator's claim and classified
each universal quantifier. The three the generator reported safe are safe:

- R2 "no returned field is `NaN`" — `budgetFigures` returns five named fields
  (§1b, §5); enumerable from the return type without the spec.
- R8 "each expected string is non-empty and contains a digit" — the three
  expected strings (`R$ 276.000,00`, `42.5%`, `58%`) are named earlier in the
  same bullet; the five nodes are named too. Enumerable within the result.
- R12 thresholds — the result lists all four. **Verified against
  `frontend/vitest.config.ts`: `lines: 80, functions: 78, branches: 76,
  statements: 80`.** Exact.

The remaining candidates, and why none is blocking:

**(a) R4's headline, "Percentages are formatted half-to-even, mirroring
Python's `format`".** §5 narrows the domain (`decimals` documented as `0..2`;
the `toFixed(20)` soundness argument is scoped to `-100..100`); R4 repeats
neither. This is the exact shape the dispatch asked me to hunt for, so I tested
whether the sweeping claim is *false* anywhere a percentage could land rather
than reasoning about it. I ran the mock's `formatPercent` over 12,066 cases —
every multiple of `0.05` in `-100..100` at `decimals` 0, 1 and 2, plus
tie-edge values (`0.125`, `0.375`, `9.995`, `99.995`, `0.005`, `0.015`,
`0.025`, `±99.5`, `±0.5`, `±1.5`, `±100`, `1e-10`, `0.045`, `0.055`) — and
compared each against Python's `format(v, '.Nf')`.

**Zero divergences.** The sweeping clause is true on the whole percentage
domain, so it cannot produce a wrong QA verdict. The only divergence I could
construct is `|value| ≥ 1e21`, where `toFixed(20)` returns exponential
notation, has no `"."`, and the non-finite guard does not catch it — reachable
only by a value no percentage in this system can take (`Money` is
`NUMERIC(12, 2)`, `physical_progress_pct` is `ge=0.0, le=100.0`). Recorded as a
suggestion to repeat the `0..2` domain in R4.

All ten of R4's pins reproduce exactly under the reference implementation, and
all ten match Python measured here, including the three non-finite literals and
the negative tie:

```
56.5 d=0 -> "56"    2.5 d=0 -> "2"      42.5 d=0 -> "42"   57.5 d=0 -> "58"
42.25 d=1 -> "42.2" 2.675 d=2 -> "2.67" -20.5 d=0 -> "-20"
NaN -> "nan"        Infinity -> "inf"   -Infinity -> "-inf"
```

**(b) R2's lead clause** "a balance cylinder whose filled proportion is the
remaining-budget percentage" reads unclamped, while the clamp is the point of
the rest of the bullet. The narrowing is *inside the same result*, two sentences
later (`yStart === 140`, `h === 0` at `executed > total`), so QA reading result 2
alone sees both. Not the §5-only pattern. Suggestion at most.

**(c) R9's "using only semantic theme tokens"** against §3's sanctioned
`style={{ fill: "var(--primary)" }}` fallback. `var(--primary)` *is* a semantic
token and is not a palette class, so the fallback does not contradict the
result; and R9's actual mechanical criteria are the three named guard suites
passing plus the exceptions count. **Verified: `themeTokenMigration.exceptions.json`
is a list of exactly 882 entries**, and `themeContrast.test.ts`,
`brandTextRole.test.ts`, `themeTokenMigration.test.ts` all exist.

No fourth blocking clause. The remaining results (R1, R3, R5, R6, R7, R10, R11)
are enumerated or negative-over-named-elements and verifiable as written.

## 4. `data-testid` in production markup — right call.

**Precedent exists and is large.** 168 `data-testid` occurrences already live in
non-test `frontend/src` files (`InfractionDetailsView`, `CycleCloseModal`,
`NextStepPanel`, `InfractionStageTimeline`, …) against 491 `ByTestId` call sites
in the suites. These ids are a settled convention in this tree, not a new
intrusion introduced by this task.

**The alternatives are worse here.** `role`/`aria` cannot distinguish the two
`path` nodes (neither is an accessibility object); the `<svg>` carries the only
`role="img"`. Positional selection (`querySelectorAll('path')[1]`) re-introduces
the round-3 wrong-pick failure the moment a decorative node is added. Selecting
on `fill="var(--primary)"` would couple the clamp test to §3's token table and
break under §3's own sanctioned inline-style fallback. An explicit id is the
only selector that survives both.

**Will they be removed as noise?** Structurally, mostly protected: the ids are
named in expected result 2 (so they are part of the committed acceptance record),
§5 says the component "must therefore expose two hooks", and the test "selects by
those ids and nothing else" — so a removal fails the suite loudly. What is
missing is the in-file signal: §6 requires a comment naming APRAS-102 for the
line-number bump, but nothing requires one at the `data-testid` sites. Suggestion.

## 5. The non-finite guard in the mock's reference implementation.

The dispatch's concern — "mirroring Python faithfully and showing a user the
string `nan` are not obviously the same goal" — is the right question, and the
spec does answer it, though in one place only (§5, lines 393–400): the guard is
introduced *defensively*, its stated purpose is that the index arithmetic over
`toFixed(20)` would otherwise throw, and the choice of Python's literals is
justified as "keeps the helper a mirror of `format` across its whole domain".
So the spec says it means **mirror**, not **display policy**.

And the display question is moot, which I verified rather than assumed:

- `ProjectDetail extends ConstructionProject`, where `total_budget: number`,
  `executed_budget: number`, `physical_progress_pct: number` are all required
  and non-nullable (`frontend/src/types/project.ts`).
- Backend side: `Money` is `Annotated[Decimal, Field(max_digits=12,
  decimal_places=2, ge=0), MONEY_SER]` and `MONEY_SER` is
  `PlainSerializer(float, return_type=float, when_used="json")`
  (`backend/app/core/money.py`) — so the wire carries a JSON **number**, not the
  `"1200.00"` string that module's docstring warns about. `physical_progress_pct`
  is `float = Field(default=0.0, ge=0.0, le=100.0)`.
- The bar's other input goes through `plannedProgress`, which rejects a
  non-number or `NaN` `pct` before any formatting.

So no `"nan"`/`"inf"` string can reach the screen through a typed path, and R4's
three pins are unit-level pins on an unreachable branch — which is a legitimate
thing to pin, since without the guard the helper *throws*. Two residual gaps,
both suggestions: the spec never states in one sentence that these strings are
unreachable in the UI (so a later reader may "fix" the guard to render an em dash
and break a pinned test), and `formatPercent(undefined, 0)` silently returns
`"-inf"` under this guard's shape (`Number.isFinite(undefined)` is `false`,
`undefined > 0` is `false`) rather than throwing — closed by the types today, but
a trap if a consumer ever passes an optional field.

## 6. Whole-document pass — findings.

Everything load-bearing I could check mechanically, checked:

- **Baseline selectors are all unique as claimed.** In
  `report_page_null_detail_baseline.html`: one `budget-col`, exactly four
  `budget-row`, one `class="cyl"`, one `class="txt"` containing exactly one
  `<strong>58%</strong>`, one `tag plan` (`<b>64%</b>`), one `tag real`
  (`<b>42%</b>`), one `seg b behind` with `left:42%;width:22%`. §5's
  five-node precondition and R8 are both satisfiable exactly as written. Note
  `58%` occurs twice in the file (once inside the SVG `<text>`), which is why
  `.cyl .txt strong` rather than a text search is the correct selector — the
  spec picks the right one.
- **Money strings present verbatim:** `R$ 480.000,00`, `R$ 204.000,00`,
  `R$ 276.000,00` (U+0020 after `R$`, confirming §5's NBSP analysis is about the
  `Intl` side only).
- **`planned_to_date` mirror is exact.** Read the backend function: `not
  isinstance(payload, list) or not payload → None`; non-dict point → `None`;
  `month` failing `\d{4}-\d{2}` → `None`; `isinstance(pct, bool)` or non-numeric
  → `None`; `month <= current and month >= best_month` latest-wins; `0.0` when
  `best is None`. The mock's `plannedToDate` reproduces every branch, including
  the boolean rejection (via `typeof pct !== "number"`). §1a's prose is accurate.
- **`PLANNED_CURVE` is `[2020-01/8.0, 2020-02/31.5, 2020-03/64.0]`**, so both
  UTC-boundary cases are arithmetically correct as written: `2020-03-01T00:30:00Z`
  under `America/Sao_Paulo` (UTC−3) reads local `2020-02-29` → `31.5`, UTC →
  `64`; `2020-03-31T23:30:00Z` under `Europe/Berlin` reads local `2020-04-01`
  (CEST, UTC+2 since 2020-03-29) → `80`, UTC → `64`. Both discriminate
  `getUTCMonth` from `getMonth`, in opposite signs, as §5 claims.
- **The theme-guard pins are where §6 says.** `themeTokenMigration.test.ts`
  carries `ConstructionTrackerPage.tsx` at `313`, `314`, `359` (lines 1801–1812)
  and a `matchesOn("ConstructionTrackerPage.tsx", 240)` assertion (line 2058);
  `BudgetVsActualProgressBar.tsx` is pinned from line 1761 onward with its
  grandfathered palette classes. §6's two hazards are real and correctly
  described.
- **The render site is real:** `BudgetVsActualProgressBar` is imported at
  `ConstructionTrackerPage.tsx:24` and rendered at line `417`, matching §2's
  "~line 417".
- **No rounding-policy contradiction.** `MONEY_ROUNDING = ROUND_HALF_UP` in
  `core/money.py` (operator-confirmed, Q1 2026-09-18) governs money
  *quantisation*; §1a-bis's half-to-even governs *percentage display* through
  Python's `format`. Different quantities, and §1a-bis explicitly scopes itself
  ("Money is unaffected in practice"). Consistent.
- **Language:** the spec is in English throughout. The mock's user-facing copy is
  pt-BR, which is correct — it is the operator-facing artefact, not documentation.
- **Scope:** one PR. Two backend one-liners, two new helpers, two new components,
  one page wiring, i18n, tests. Not a split candidate.

No blocking finding. The two open questions are both visual, both drawn A/B in
the mock on the screen they affect, both answerable with one letter, and §2
pre-sanctions the consequence of answer A to question 2 so it cannot contradict
the spec later — which is the right shape.

---

## Blocking Findings

None.

## Suggestions

- §5 (line 440) and result 2 (line 557) both say "the arc's `rx 50 ry 12` are
  absolute lengths **outside that range**". `rx = 50` lies *inside* `20..140`;
  only `ry = 12` is outside. The sentence constrains no assertion, so it is not
  blocking, but it is the third round in a row that this one aside has carried a
  false statement. Replacing "outside that range, by design" with "lengths, not
  coordinates" removes the claim entirely rather than correcting it.
- Result 4 opens "Percentages are formatted half-to-even, mirroring Python's
  `format`" without the domain §5 states (`decimals` documented as `0..2`; the
  `toFixed(20)` soundness argument holds for `-100..100`). I verified the claim
  is true across 12,066 cases spanning that whole domain, so nothing fails today;
  the only constructible divergence is `|value| ≥ 1e21`, where `toFixed(20)` goes
  exponential and the non-finite guard does not catch it. Repeating "for
  `decimals` in `0..2`" in result 4 closes the last sweeping phrasing in the
  document.
- §5 is silent on whether `"nan"`/`"inf"`/`"-inf"` may ever reach the screen. They
  cannot — `ProjectDetail`'s three numeric fields are required and non-nullable,
  and `MONEY_SER` serialises `Decimal` to a JSON number — but one sentence saying
  so would stop a later reader from "fixing" the guard to render an em dash and
  breaking a pinned test.
- Under the guard's shape, `formatPercent(undefined, 0)` returns `"-inf"`
  (`Number.isFinite(undefined)` is `false`, `undefined > 0` is `false`) rather
  than throwing. The types close this today; a `Number.isFinite` precondition
  that distinguishes "not a number at all" from "±Infinity" would close it
  structurally.
- §6 requires a comment naming APRAS-102 at the bumped line-number pins, but
  nothing requires one at the two `data-testid` sites. A one-line comment naming
  the clamp test at each id would keep a future tidy-up from reading them as noise
  before it runs the suite. (The convention itself is well established — 168
  non-test `data-testid` occurrences already exist in `frontend/src`.)
- Result 2's lead clause, "a balance cylinder whose filled proportion is the
  remaining-budget percentage", reads unclamped two sentences before the bullet
  pins the clamp. Adding "clamped to `0..100`" to the lead would make the bullet
  self-consistent from its first line.
