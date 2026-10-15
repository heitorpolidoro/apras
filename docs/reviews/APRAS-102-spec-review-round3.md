# APRAS-102 — spec review, round 3 (findings-only)

VERDICT: NEEDS_REVISION

Scope of this pass: round 2's single blocking finding (the clamp assertion), the
sections the revision changed to fix it, and the five items the dispatch asked to
be verified rather than taken from the document. Nothing was staged, committed or
edited; no frontend file was touched; no `npm install` / `uv sync`; no test suite
run.

## 1. The replacement clamp assertion — ran the reference implementation

I extracted the mock's `formatPercent` / `budgetFigures` / `cylinderCard`
verbatim (`docs/tasks/APRAS-102-mock.html`, the `<script>` block) into a scratch
module and ran it in Node 24 at four inputs. Literal emitted strings:

| case | `remainingPct` | outline `d` | fill `d` | ellipse `cy` | printed |
| --- | --- | --- | --- | --- | --- |
| `100000/120000` (over budget) | −20 | `M10 20 v120 a50 12 0 0 0 100 0 v-120` | `M10 140.0 v0.0 a50 12 0 0 0 100 0 v-0.0` | `140.0`, `20` | `-20%` |
| `0/50000` (`total = 0`) | 100 | same | `M10 20.0 v120.0 a50 12 0 0 0 100 0 v-120.0` | `20.0`, `20` | `100%` |
| `480000/204000` (baseline) | 57.5 | same | `M10 71.0 v69.0 a50 12 0 0 0 100 0 v-69.0` | `71.0`, `20` | `58%` |
| `400000/174000` (normal) | 56.5 | same | `M10 72.2 v67.8 a50 12 0 0 0 100 0 v-67.8` | `72.2`, `20` | `56%` |

Every literal string §5 quotes is exact, and the baseline's own committed figure
(`backend/tests/data/report_page_null_detail_baseline.html`) carries
`d="M10 71.0 v69.0 a50 12 0 0 0 100 0 v-69.0"` — the mirror is faithful byte for
byte at the fixture's inputs.

So the substance of the new assertion is sound and discriminating:

- `yStart`/`h` as defined (move-to `y`; first vertical operand) read `140`/`0`
  at `executed > total` and `20`/`120` at `total = 0`, exactly as §5 and expected
  result 2 state. Numerically compared, `"140.0" → 140` and `"0.0" → 0`, so no
  `toFixed` precision is imposed, as the spec says.
- A missing clamp gives `fy = bottom - 120 × (-20)/100 = 164` and `h = -24`, so
  all three assertions fail. The criterion is true in the clamped cases and false
  otherwise.
- `h === 0` does distinguish a clamped empty tank from a component that rendered
  no fill at all, but only indirectly: with no fill node there is no `d` to
  parse, so the test errors rather than passing. The companion `total = 0` case
  (`h === 120`) makes a never-rendered fill fail twice. Adequate; see suggestions
  for the one line that would make it airtight.

What is **not** sound is the sweeping clause that survived into expected result 2
and the identification of the two nodes being read — see the blocking finding.

## 2. The sixth/seventh pinned rounding pair, and §5's count

Measured both runtimes (not taken from the document):

| value | dec | Python `format` | mock helper | `toFixed` |
| --- | --- | --- | --- | --- |
| 56.5 | 0 | 56 | 56 | 57 ✗ |
| 2.5 | 0 | 2 | 2 | 3 ✗ |
| 42.5 | 0 | 42 | 42 | 43 ✗ |
| 57.5 | 0 | 58 | 58 | 58 (agrees) |
| 42.25 | 1 | 42.2 | 42.2 | 42.3 ✗ |
| 2.675 | 2 | 2.67 | 2.67 | 2.67 (agrees) |
| −20.5 | 0 | −20 | −20 | −21 ✗ |

All seven pinned pairs match Python exactly, and `toFixed` differs on five.
§5's "`toFixed` fails **five of the seven** (only `57.5` and `2.675` agree)" is
now correct — the round-2 off-by-one is gone and the added negative tie is
counted.

## 3. The §2 answer-A contradiction

Resolved. §2 now carries "One further divergence, pre-sanctioned so answer A to
open question 2 cannot contradict this section later", which states that under
**A** the in-tank number is the unclamped one, that this is sanctioned as a
second appearance divergence, and that under **B** the question does not arise.
The preceding marker paragraph is correspondingly qualified ("the only appearance
difference the spec sanctions *as written*"). An **A** answer no longer
contradicts §2. The mock's A2 caption was also fixed ("Saldo restante (no
tanque)"), so option A no longer looks defective.

## 4. The mock's tokens and hexes

- `:root` drift: none. I parsed the mock's eleven `--token: oklch(...)`
  declarations and compared each against `frontend/src/index.css` `:root`
  programmatically — all eleven identical (`--background 0.99 0 0`,
  `--foreground 0.14 0.01 160`, `--card 1 0 0`, `--primary 0.62 0.15 160`,
  `--primary-foreground 0.15 0.02 160`, `--primary-text 0.52 0.11 160`,
  `--muted 0.96 0.01 160`, `--muted-foreground 0.53 0.02 160`,
  `--accent 0.96 0.01 160`, `--border 0.92 0.01 160`,
  `--destructive 0.58 0.24 27`).
- `#rrggbb` comments: the mock contains exactly **one** hex, `#c0392b` at line
  83, and it is not a token conversion — it is the public report's own
  behind-schedule colour, confirmed at
  `backend/app/services/project_report_service.py:417`
  (`.one .seg.b.behind { background:#c0392b; opacity:.7; }`). So the APRAS-98
  hazard (a hand-rolled per-channel sRGB clip standing in for the CSS Color 4
  chroma reduction) has nothing to bite on here: the mock publishes no derived
  hex at all.
- I nonetheless imported `frontend/src/lib/contrast.ts` (copied to the
  scratchpad, run under `node --experimental-strip-types`; no file under
  `frontend/` was modified and nothing was left in the repo) and re-derived the
  figures the spec publishes:
  - `--primary` as text on `--card` = **3.4054:1** ✓ (spec's figure)
  - `--primary-foreground` on `--primary` = **5.7588:1** ✓
  - `--muted-foreground` on `--muted` = **4.6684:1** ✓
  - `--primary-text` on `--card` = 5.2096:1 (matches `index.css`'s comment)
  - out-of-gamut set, per `isInGamut`: exactly `--primary` (`#009f68`) and
    `--destructive` (`#e60018`) among the mock's eleven, i.e. the light
    primary/ring and light destructive the dispatch names. No other mock token is
    out of gamut.
  - extra check, not claimed by the spec but newly load-bearing because the
    cylinder now prints a negative percentage in `text-destructive`:
    `--destructive` as text on `--card` is **4.8073:1** and on `--background`
    **4.6713:1** — both clear AA, so the new destructive text introduces no
    contrast defect.

## 5. Result 5's non-degeneracy preconditions

They do catch the rot they are aimed at. If a backend class name changes and a
selector stops matching, the pt-BR parse of the two inputs yields `NaN`, and the
precondition "the two parsed inputs are `480000` and `204000`" fails; if the
cylinder's `58%` node disappears, the expected string is `""` and the
"non-empty and contains a digit" precondition fails. A selector that silently
yields empty strings therefore cannot make the comparison trivially true. The
baseline bytes were re-read and still carry `R$ 480.000,00`, `R$ 204.000,00`,
`R$ 276.000,00`, `42.5%` and `58%` in a four-node `.budget-col .budget-row` block
plus `.cyl .txt strong`.

One soft spot, non-blocking: there are **five** value-bearing nodes
(four `.budget-row` rows plus `.cyl .txt strong`), and the cardinality
precondition and the named-error clause both say "the four selectors". The fifth
read is covered only by the digit check. Saying "five" would close it; the
substance is already guarded.

## 6. Gap colours, below-plan label, i18n

- §3's table still reads `bg-primary/30` (ahead) and `bg-destructive/70`
  (behind), unchanged from what round 2 accepted, with the "expected to look
  faint" sentence added. The mock implements them as
  `color-mix(in oklch, var(--primary) 30%, transparent)` and
  `color-mix(in oklch, var(--destructive) 70%, transparent)`, so the drawing and
  the prose agree.
- The non-colour below-plan signal is still specified in §2, §3, §5, expected
  result 5 and expected result 11, and is drawn in the mock
  (`<span class="behindtext">abaixo do previsto</span>`, shown only when
  `realized < planned`).
- The keys are new, so they do not exist in the locales yet — correct for a spec.
  The enforcing test does exist: `frontend/src/i18n/__tests__/parity.test.ts`, so
  expected result 11's criterion is mechanically checkable.
- §5's new unit pinning for the gap matches the reference exactly: the mock sets
  `gap.style.left = low + "%"` and `gap.style.width = high - low + "%"`, giving
  `left: "42%"`, `width: "22%"` at `planned = 64, realized = 42` — the baseline's
  own `seg b behind` values.

## Blocking Findings

- **Expected result 2's "every absolute coordinate read from the fill lies in
  `20..140`" is still false on the sanctioned geometry under one legal reading,
  and the two nodes it reads are not identifiable in the markup the spec
  sanctions.** Round 2 asked for the assertion to be "stated the same way in §5
  and in expected result 2". §5 makes the sweeping clause safe by enumerating the
  set — "every **absolute coordinate** read from the fill (`yStart`, the
  ellipse's `cy`)" — but expected result 2 drops that parenthetical, and QA reads
  expected result 2 with no access to §5. Read literally, the absolute
  coordinates of the fill path are the move-to pair, and the reference
  implementation emits `M10 140.0 …` / `M10 20.0 …`: the x coordinate is **10**,
  which is not in `20..140` (and the `a` command's `rx 50 ry 12` are absolute
  lengths, one of them also below 20). So the clause is either vacuous (a
  restatement of `yStart`, which the same sentence already asserts) or false on a
  correct mirror — the same failure mode as round 2's `/-\d/`, one size smaller.
  Fix by making it an explicit, enumerated, y-only clause in **both** places,
  e.g. "the two absolute y coordinates the test reads — `yStart` and the liquid
  surface's `cy` — both lie in `20..140`". Second, the test cannot find its nodes
  as described: the component renders **two** `path` nodes (outline and fill) and
  **two** `ellipse` nodes (liquid surface at `cy = fy`, rim at `cy = 20`), none
  carrying a name, so "the single fill `path` node" and "the liquid-surface
  `ellipse`" are under-determined — and picking the outline or the rim makes the
  assertion fail at `executed > total` on a correct component (`20` instead of
  `140`). Name the hook the component must expose (a `data-testid`, or "the
  second `path` / the `ellipse` whose `cy` tracks the fill"), in §5 and in
  expected result 2, so two implementers select the same nodes.

## Suggestions

- §5 and expected result 9 say "the four selectors" where five nodes are read
  (four `.budget-row` rows plus `.cyl .txt strong`). The cylinder's `58%` node is
  outside the cardinality precondition and outside the named-error clause; the
  digit check still catches its disappearance, so this is wording only.
- Add an explicit presence precondition to the clamp case, in the same spirit as
  result 5's: "exactly one fill node matched". Today a never-rendered fill fails
  by erroring during the parse rather than by a stated assertion, which is right
  but accidental.
- The mock's `formatPercent` **throws** on `NaN` and `Infinity`
  (`kept[cut]` is `undefined` because `Math.abs(NaN).toFixed(20)` has no `"."`),
  while §5 requires the helper to "not emit garbage" for those and to have the
  test pin whatever it returns. An implementer who copies the reference inherits
  a throw. Worth one line in §5 (or a guard in the mock) saying the reference
  implementation deliberately omits that guard.
- §5's behind-state bullet uses `planned = 64, realized = 42.5` while its
  `left`/`width` example uses `realized = 42`; at `42.5` the strings are
  `left: "42.5%"`, `width: "21.5%"`. Harmless, but stating the `42.5` pair
  alongside the example would stop an implementer from pinning `"42%"` there.
