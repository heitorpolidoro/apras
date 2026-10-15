# APRAS-123 — spec review (round 1)

VERDICT: NEEDS_REVISION

Spec: `docs/tasks/APRAS-123-spec.md`. Tree: `master` at `2cb0d48`.
No `parent`, so `NEEDS_SPLIT` was available; it is not warranted (see "Scope").

Everything below that is stated as measured was measured by importing
`frontend/src/lib/contrast.ts` directly (Node 24 native type stripping, scripts
in the session scratchpad, nothing written under `frontend/`, nothing staged).

---

## 0. The out-of-gamut inventory — the operator's count is right, the spec's is wrong

**The true count is 19: 16 light, 3 dark.** Derived by parsing every
`--token: oklch(...)` declaration in `frontend/src/index.css` and applying
`isInGamut`:

```
:root --primary              oklch(0.62 0.15 160) -> #009f68   (line 39)
:root --destructive          oklch(0.58 0.24 27)  -> #e60018   (line 62)
:root --ring                 oklch(0.62 0.15 160) -> #009f68   (line 66)
:root --status-pending-bg     oklch(0.96 0.05 85)  -> #fff0d1  (line 69)
:root --status-pending-fg     oklch(0.5 0.12 85)   -> #7e5d00  (line 70)
:root --status-in-progress-bg oklch(0.93 0.06 240) -> #ceedff  (line 71)
:root --status-in-progress-fg oklch(0.4 0.15 240)  -> #004d7d  (line 72)
:root --status-blocked-bg     oklch(0.95 0.08 70)  -> #ffebd2  (line 73)
:root --status-blocked-fg     oklch(0.5 0.15 70)   -> #8b5600  (line 74)
:root --status-completed-bg   oklch(0.94 0.1 160)  -> #b3ffd6  (line 75)
:root --status-completed-fg   oklch(0.4 0.15 160)  -> #005931  (line 76)
:root --status-canceled-bg    oklch(0.95 0.04 20)  -> #ffe7e6  (line 77)
:root --priority-medium-fg    oklch(0.38 0.1 210)  -> #004d58  (line 83)
:root --priority-high-bg      oklch(0.95 0.08 70)  -> #ffebd2  (line 84)
:root --priority-high-fg      oklch(0.5 0.15 70)   -> #8b5600  (line 85)
:root --priority-urgent-bg    oklch(0.94 0.1 25)   -> #ffdfda  (line 86)
.dark --primary               oklch(0.65 0.15 160) -> #00aa6f  (line 97)
.dark --primary-text          oklch(0.65 0.15 160) -> #00aa6f  (line 103)
.dark --ring                  oklch(0.65 0.15 160) -> #00aa6f  (line 114)
```

**The crude scan was adequate for this file, and the method is on record.**
I checked the assumptions rather than the result: the file has exactly one
`@theme`, one `:root` and one `.dark`; there are 58 `oklch(...)` occurrences
(38 in `:root`, 20 in `.dark`, 0 in `@theme`, 0 outside a block); **all 58 sit
on a line that also carries a `--token:` declaration** — there is no `oklch()`
inside a gradient, a `color-mix()`, a shorthand or a second value; and
`parseOklch` returns non-null for all 58, so none is silently skipped. A
line-anchored per-declaration scan therefore cannot miss one here. No token was
missed.

**No token is missing from the operator's list, and the spec's own enumerations
agree with it.** §6 lists 16 light + 3 dark = 19 while the prose says "the 20
`oklch()` tokens"; expected result 8 enumerates "light `--primary`,
`--destructive`, `--ring`, the five `--status-*-bg`, the four `--status-*-fg`,
`--priority-medium-fg`, `--priority-high-bg`, `--priority-high-fg`,
`--priority-urgent-bg`; dark `--primary`, `--primary-text`, `--ring`" =
16 + 3 = 19, while saying "the 20 `(block, token)` pairs". Only the numeral is
wrong, in three places (§6, §9, result 8). This matters because result 8 demands
the derived set equal **"an exact inline list of the 20 pairs"**: an
implementation that correctly derives 19 fails a literal reading of the
criterion. See finding B1.

**Where the off-by-one probably came from, and why the document must say so.**
`--status-canceled-fg: oklch(0.5 0.15 20)` is **in** gamut, while the
structurally identical `--status-blocked-fg: oklch(0.5 0.15 70)` and
`--priority-high-fg: oklch(0.5 0.15 70)` are out. Same L, same C, different
hue — hue 20 at L 0.5 C 0.15 is inside sRGB, hue 70 is not. Five
`--status-*-bg` are out but only four `--status-*-fg`, and the one missing
`-fg` is the one a reader scanning for symmetry will "restore". The provenance
document should state that asymmetry explicitly next to the inventory.

---

## 1. The three findings the spec reports — all three check out

### 1a. The naive scan does report exactly four false mismatches

Run over today's working tree (`docs/tasks/**/*.{md,html}` +
`docs/frontend/**/*.md`, 141 files), with "naive" read as *exactly one
`oklch(L C H)` and exactly one `#rrggbb` on the line* and
`docs/tasks/APRAS-123-spec.md` itself set aside (it did not exist when the
spec's measurement was taken): **34 claims, 4 mismatches, all four false.**

```
docs/tasks/APRAS-68-mock.html:93  pub #0ea5e9 der #23a3e3   brand *input*, not the paint
docs/tasks/APRAS-68-spec.md:235   pub #008a5a der #008b5a   hex-first derivation, legitimate
docs/tasks/APRAS-68-spec.md:477   pub #0ea5e9 der #f8f8f8   unrelated oklch and hex, one sentence
docs/tasks/APRAS-92-spec.md:717   pub #174b40 der #df2224   hex inside a "contains none of" assertion
```

The two the spec names are correct, and I confirmed both round trips:
`oklch(0.56 0.13 160.15)` → `#008b5a` (so `#008a5a →` genuinely lands one
8-bit step away) and `oklch(0.68 0.14 237.32)` → `#23a3e3`.

A looser naive scan — *first* oklch and *first* hex on the line, which is what
an implementer might actually write — gives **15** mismatches on the same tree,
all false. The spec's rejection of the naive shape is, if anything,
understated. It names only two of the four; `:477` and `:717` are the more
instructive pair, because neither is a colour claim in any sense and no
ordering rule excludes them — only the connector anchoring does. Naming all
four would make the rejection harder for a future implementer to argue with.

### 1b. The `docs/reviews/**` exclusion is load-bearing, and it is narrow enough

Confirmed: `docs/reviews/APRAS-98-spec-review-round3.md:27` is

```
| `--ring` light `oklch(0.62 0.15 160)` → `#00a166` | — | `#00a166` ✓ |
```

oklch-first, `→` connector, hex — a textbook shape-C match that derives
`#009f68` and would fail. Guarding reviews would mean rewriting the finding
that caught the bug.

**Judged narrow enough.** The decisive point is that the document set is
defined *positively* (`docs/tasks/**/*.{md,html}` and `docs/frontend/**/*.md`);
`docs/reviews/**`, `docs/suggestions-log.md`, `docs/features_planning_and_questions.md`,
`docs/obras-fonte/**` and `docs/superpowers/**` are not carve-outs from the
scanned set, they are simply outside it, documented so a reader does not add
them later. A mock cannot hide behind the rule: a mock is
`docs/tasks/<id>-mock.html` by this repo's own convention, which is inside the
scanned set. The residual risk — someone moves a figure out of `docs/tasks/`
to escape the guard — is a visible rename in a diff, and acceptable.
`docs/suggestions-log.md` sits at `docs/` root and is already outside the
positive set, so listing it is redundant but harmless.

### 1c. There are no already-wrong documents — 0 mismatches, so "no exceptions JSON" is right

I implemented the three shapes independently (shape A as a per-line
declaration-plus-gloss in either order; shape B as the quoted tuple; shape C on
text with HTML tags, backticks, asterisks and pipes stripped, oklch-first,
connector `=`/`==`/`→`/`->`/`≈`, matched across line breaks) and ran it on both
trees.

| | docs read | claims | contributing docs | mismatches |
|---|---|---|---|---|
| committed `2cb0d48` | 125 | **17** | **8** | **0** |
| working tree | 141 | 33 (29 excl. this spec) | 11 (10 excl. this spec) | **0** |

The committed-tree numbers reproduce the spec's §4 exactly: 17 claims across 8
files. The working-tree numbers are within my approximation's error of the
spec's "31 across 10" (I get 29 across 10 once this spec's own 4 self-matches
are removed; the 2-claim delta is in `APRAS-98-mock.html`, where my shape-C gap
rule is stricter than the spec's). **The conclusion the spec draws is sound:
nothing in the tree is wrong, so the guard ships green and no exceptions file
is justified.** I endorse the explicit refusal to adopt the
`themeTokenMigration.exceptions.json` shape.

Shape C in isolation, on the committed tree under the strict reading (gap must
be whitespace only after stripping), yields 6 claims, 0 mismatches, and
includes both hard cases the spec names — `APRAS-68-mock.html:93`, whose `≈`
ends a line and whose hex is on the next inside `<code>`, and
`APRAS-87-spec.md:23`, inside a Markdown table row. The across-line-breaks and
strip-markup requirements are both genuinely necessary, not decoration.

---

## 2. The floors do hold against the committed tree

Checked with `git ls-tree` / `git show` at `2cb0d48`, never against disk:

- **≥ 100 documents read** — 125 committed documents in the scanned set
  (96 `docs/tasks/*.md`, 27 `docs/tasks/*.html`, 2 `docs/frontend/*.md`). Holds
  with margin.
- **≥ 8 documents contributing a claim** — exactly 8.
- **≥ 17 claims** — exactly 17.
- **`APRAS-90-mock.html` ≥ 5 shape-A** — exactly 5. `--primary: #009f68; /* oklch(0.62 0.15 160) */`
  is at line 16, as §10 states.
- **`APRAS-76-mock.html` ≥ 4 shape-B** — exactly 4.
- **`oklch(0.62 0.15 160)`/`#009f68` at least twice** — 3 times committed
  (7 in the working tree).

The decision to measure on the committed tree is correct and the reasoning is
right: `docs/tasks/APRAS-98-mock.html` and `-spec.md` are untracked and carry
12 of my 29 working-tree claims (the spec says 14 of 31), so floors calibrated
on disk would pass locally and fail on a clean CI checkout. Three of the six
floors sit **exactly** at the measurement with zero margin — correct for a
floor, but worth knowing: any concurrent edit to `APRAS-90-mock.html` or
`APRAS-76-mock.html` turns CI red, which is the point of naming them.

---

## 3. The ratio escape — the four figures are exact; the control is a regression pin, not coverage

All four marked ratios re-derive exactly, to 4dp, with `contrastRatio`:

```
light --ring on --card        3.4054  (claimed 3.4054)
light --ring on --destructive 1.4117  (claimed 1.4117)
dark  --ring on --card        6.4180  (claimed 6.4180)
dark  --ring on --destructive 1.8021  (claimed 1.8021)
```

and the three published hexes: `oklch(0.62 0.15 160)` → `#009f68`,
`oklch(0.58 0.24 27)` → `#e60018`, `oklch(0.65 0.15 160)` → `#00aa6f`.

**Is an opt-in marker worth anything?** Partly, and the spec is honest about
which part. Nothing compels a future author to use it, so it buys no coverage
over prose ratios — §5 says exactly that, quantifies the gap (the clip method
would read 3.3564 / 1.4252 / 6.4408 / 1.8085, second-decimal differences no
reader catches), and defers mandatory marking plus token resolution to a named
follow-up. That is the right call: token resolution across the light and dark
blocks is a second deliverable, and pretending to locate prose ratios would
produce exactly the unfalsifiable criterion this task exists to prevent.
Declaring something out of reach, with the residual risk named, is better spec
discipline than a criterion that cannot fail.

**Is "seeded with 4" + "assert ≥ 4" a tautology?** It is not a control over
future authors, and the spec should not be read as claiming it is. It is a
**regression pin**: the four figures are stated independently of the code, and
if `contrast.ts` ever changes behaviour or someone edits one of the four
numbers, the test goes red. That is real value, and it also keeps the
marker-parsing code path exercised rather than dead. What it is not is evidence
that the mechanism will be adopted. Result 6's wording ("Contrast ratios are
handled by the declared escape and not left as an aspiration") is a little
generous about this; see suggestion S4. Not blocking.

---

## 4. The no-arithmetic self-check — sound idea, impossible as written

The literal list is the right list *for the implementation it guards*: every
needle is present in `frontend/src/lib/contrast.ts` (`0.2126`/`0.7152`/`0.0722`
in `WCAG_WEIGHTS`, `4.0767416621` and `0.4122214708` in the Ottosson matrices,
`12.92`, `1.055`, `0.04045` as `SRGB_KNEE`, `0.0031308` as `LINEAR_KNEE`,
`Math.cbrt` in `linearToOklab`, `channel ** (1 / 2.4)` in `linearToSrgb`), so
a copy-paste of the module's arithmetic into the test is caught. The APRAS-100
cross-reference is also accurate: `docs/tasks/APRAS-100-spec.md:504` and its
result at :645 do exclude `**/__tests__/**` and `*.test.ts` by rule, so this
file needs no special case there.

Two problems, one fatal.

**Fatal: the assertion as specified cannot pass.** The file must contain the
needles in order to assert them, and it reads *its own source*. See finding B2.

**The list is a weak net, as the operator says.** A reimplementation with
differently-written constants (`0.2126` as `2126/10000`, the matrix to fewer
digits), or `import Color from "colorjs.io"`, passes every needle. The cheap
close is mechanical and belongs in the same assertion: pin the file's import
list. See suggestion S3.

---

## 5. `themeContrast.test.ts` — verified, and leaving it alone is consistent

Verified by reconstructing its 0.01-grid mapper and measuring with the module's
own `isInGamut`:

```
grid-mapped light --ring = oklch(0.62 0.14 160) -> #019f68, ratio on --card 3.4078
contrast.ts  light --ring = oklch(0.62 0.15 160) -> #009f68, ratio on --card 3.4054
```

exactly the figures §6 reports. It is a genuine second implementation —
`CHROMA_STEP = 0.01`, its own `RED_WEIGHT = 0.2126` at line 62, its own
Ottosson matrix at line 87 — and it already **documents its own disagreement**
in-file at lines 326-335, pinning `3.0448` where the mapping document publishes
contrast.ts's `3.0427`, with the reason: "an oracle silently agreeing with the
module it exists to cross-check would be worth nothing."

**Consistent with result 6.** Result 6 is "no conversion arithmetic is
**added**". The oracle is pre-existing, is not a source for any published
figure, and is recorded as a named exception rather than quietly tolerated.
Unifying it would destroy the only independent check on `contrast.ts` — and
"independence of agent is not independence of method" is this very spec's
thesis. The one thing the provenance document must do, and §6 says it does, is
state that `#019f68`/`3.4078` may never be quoted; otherwise the next generator
finds a second published value for the same token and picks whichever it meets
first. That is the actual hazard, and it is addressed.

---

## 6. Scope, split, language

One new test file, one new document, one ≤ 8-line `AGENTS.md` sub-section,
`vitest.config.ts` deliberately unchanged, no production source, no colour
moved. Single PR-sized deliverable in one subsystem; the spec's refusal to
split is correct and `NEEDS_SPLIT` would be wrong. English throughout. §3's
reasoning about collection (`node:fs` rather than `?raw`/`import.meta.glob`,
default Vitest glob relative to `frontend/`, `// @vitest-environment node`) is
right and matches how `themeContrast.test.ts` already works. Coverage reasoning
is right: `coverage.include` is `["src/**/*"]` with `**/*.test.ts` excluded, so
the guard is in neither numerator nor denominator.

---

## Blocking Findings

- **B1 — The out-of-gamut inventory is 19 tokens, not 20, and expected result 8
  as written fails on a correct implementation.** I re-derived the set by
  importing `isInGamut`: **16 light, 3 dark, 19 total**. §6's own enumeration
  lists 19 items and result 8's own enumeration ("the five `--status-*-bg`, the
  four `--status-*-fg`, …") also resolves to 19, so only the numeral "20" is
  wrong — but result 8 demands the derived set equal "an exact inline list of
  the **20** `(block, token)` pairs", and a correct implementation derives 19.
  This is the defect class the task exists to prevent, inside the task that
  prevents it. Fix the numeral in §6, §9 and result 8. Separately, the document
  must state the asymmetry that produced the miscount:
  `--status-canceled-fg: oklch(0.5 0.15 20)` is **in** gamut while
  `--status-blocked-fg: oklch(0.5 0.15 70)` is out, so the inventory carries
  five `--status-*-bg` but only four `--status-*-fg` — otherwise the next
  reader "restores" the symmetry.

- **B2 — The no-arithmetic self-scan contradicts itself and cannot pass.** §7
  and expected result 10 require an assertion *in the same file* that reads
  *its own source* and asserts it "contains none of `0.2126`, `0.7152`,
  `0.0722`, `4.0767`, `0.4122`, `12.92`, `1.055`, `0.04045`, `0.0031308`,
  `Math.cbrt` or `** (1 / 2.4)`". The needles must appear in the file for the
  assertion to name them, so the assertion finds them and fails. A literal
  implementation is red on arrival; a working one requires an unspecified
  device (needles built by concatenation or char code, or the needle
  declaration excised from the source before scanning), and two implementers
  will choose differently. The spec must state the device and how the
  assertion's own needle list is excluded from its own scan.

- **B3 — The ignore-escape assertion is falsified by this spec itself.** §2
  states "a line carrying `<!-- contrast-guard: ignore — <reason> -->`
  suppresses the next claim. The test asserts the set of such markers equals an
  inline list which is **empty** at landing." `docs/tasks/APRAS-123-spec.md:90`
  is inside the scanned set (`docs/tasks/**/*.md`) and carries that literal
  marker text, as documentation of the syntax —
  `grep -rn 'contrast-guard' docs/` returns exactly that one line. So the set
  at landing is `{APRAS-123-spec.md:90}`, not empty, and the assertion fails
  unless the spec says the marker must be line-anchored (`^\s*<!-- contrast-guard:`),
  or the documenting occurrence is named as the sole permitted member of the
  inline list. §2's phrase "a line **carrying**" reads as line-level, not
  line-anchored, so the ambiguity is real. The same self-reference hazard
  applies to the ratio marker: `docs/frontend/contrast-provenance.md` will
  publish the template `<!-- ratio: oklch(L C H) on oklch(L C H) = N.NNNN -->`,
  for which `parseOklch` returns `null` — and §1 warns that the module yields
  `NaN` silently on bad input. The spec must say whether a marker whose
  operands do not parse is skipped or is a failure.

- **B4 — The one mechanism that can neutralise the whole guard has no expected
  result.** The `contrast-guard: ignore` escape appears only in §2; no entry in
  Expected Results mentions it. `meridian:qa` receives only
  `expected_results`, so an implementation that ships the guard with ignore
  markers sprinkled across the documents satisfies every listed result. Add a
  result asserting that the set of ignore markers found across the scanned set
  equals the exact inline list the test declares, and that the list's contents
  at landing are named.

- **B5 — §8 and expected result 12 give the implementer contradictory
  instructions.** §8: "If the implementer's run finds a mismatch … the rule is:
  **fix the figure**, do not except it" — up to three lines across other tasks'
  documents, and Out of Scope restates the cap. Result 12: "the guard passes on
  the tree as committed, with **no** colour, token or ratio value changed
  anywhere in `frontend/src/index.css` or in any existing `docs/tasks/`
  document." The condition does not fire today (I measured 0 mismatches, so
  both are currently satisfiable), but a concurrent task landing a wrong figure
  before implementation makes the two unsatisfiable together. Result 12 should
  carve out §8's three-line repair allowance explicitly.

## Suggestions

- **S1** — §4's "123 tracked documents (96 `.md`, 27 `.html`)" counts
  `docs/tasks/` only. The scanned set also includes `docs/frontend/**/*.md`,
  which at `2cb0d48` holds `theme-token-mapping.md` and `unmapped-colours.md`:
  the true figure is **125 (98 `.md`, 27 `.html`)**. The `≥ 100` floor holds
  either way, but a measurement-provenance slip inside a spec about measurement
  provenance is worth correcting on principle.
- **S2** — "compares to **4 decimal places**" is implementable two ways:
  `derived.toFixed(4) === marker` (rounding equality) or
  `toBeCloseTo(marker, 4)` (|diff| < 5e-5). They differ at the boundary. Name
  one. All four seeded figures pass under either, so this is not blocking.
- **S3** — Close the hole B2's needle list leaves open by pinning the guard's
  imports in the same assertion: the file's `import` specifiers are exactly
  `node:fs`, `node:url` (or `node:path`), `vitest` and `../lib/contrast`. That
  catches both a reimplementation with differently-written constants and
  `import Color from "colorjs.io"`, neither of which any needle sees, and it is
  as mechanical as the needle scan.
- **S4** — Reword result 6 so it does not overclaim. The `≥ 4` marker assertion
  is a regression pin on four stated figures, not coverage of prose ratios;
  §5's body is honest about this but the result reads as though ratios are now
  handled. Say "four marked ratios are pinned and re-derived; unmarked prose
  ratios remain unguarded, per §5".
- **S5** — §2 names only two of the four naive false positives. Name the other
  two as well: `docs/tasks/APRAS-68-spec.md:477` pairs an unrelated `oklch()`
  with an unrelated hex inside one sentence, and
  `docs/tasks/APRAS-92-spec.md:717` carries the hex inside a "contains none of"
  assertion. Neither is excluded by the ordering rule — only by connector
  anchoring — so they are the stronger argument against the naive shape.
- **S6** — Three floors sit exactly at the committed measurement (8 contributing
  documents, 17 claims, 5 shape-A in `APRAS-90-mock.html`, 4 shape-B in
  `APRAS-76-mock.html`). Correct for floors, and the spec already permits
  raising them to the landing commit's figures — worth noting in §4 that the
  new provenance document's own inventory and markers will raise the real count
  well above 17, so the landing figures should be re-measured rather than
  copied from §4.
- **S7** — The provenance document should carry the derived hex beside each of
  the 19 inventory entries (result 8 already asks for this); the list in §0 of
  this review is the measured set and can be used verbatim.
