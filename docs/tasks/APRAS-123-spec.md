# APRAS-123 — Guard the hex and ratio comments in docs/tasks mocks against the clip bug

## Scope

A mechanical guard that re-derives, from `frontend/src/lib/contrast.ts`, every
`#rrggbb` a document under `docs/tasks/` publishes **as the paint of** an
`oklch(...)` value, plus a published provenance document that makes a quoted
colour figure traceable to the one implementation that may produce it.

The defect this closes is not an arithmetic slip. Across APRAS-98's five spec
rounds a generator computed every contrast figure with a per-channel sRGB clip,
reported it as independently re-derived, and a reviewer blessed it — three
passes reproducing the **same wrong method**, while the correct values were
already published in `docs/tasks/APRAS-87-spec.md`, `docs/tasks/APRAS-90-mock.html`
and `backend/tests/test_branding.py`. Independence of agent is not independence
of method, so the remedy is not another reviewer: it is that the only way to
write a colour figure into this repository is to let `contrast.ts` produce it,
and that a figure disagreeing with `contrast.ts` fails a test. That promise binds
this task's own deliverable first: the provenance document's inventory is the
only authoritative copy of those figures and the guard parses it, so the document
cannot drift out of agreement with `index.css` without turning CI red (§6).

**In scope:** one new node-environment Vitest guard; one new document under
`docs/frontend/`; a short pointer to it from `AGENTS.md`.

**Not in scope:** changing any colour, token, ratio or stylesheet; changing
`frontend/src/lib/contrast.ts` or `backend/app/core/branding.py`;
`frontend/src/__tests__/themeContrast.test.ts`, whose independent oracle is
deliberate (see §6); and the backend, which this task does not touch at all.

## Approach

### 1. Behaviour — what the guard asserts

A new node-environment test walks a fixed document set, finds every published
**equivalence claim** between an `oklch(L C H)` and a `#rrggbb`, and fails when
`oklchToHex(parseOklch(oklch))` does not equal the published hex, naming the
file, the 1-based line, the published hex and the derived one.

`contrast.ts` takes **parsed `Oklch` objects, not strings** —
`parseOklch(value: string): Oklch | null`, then `oklchToHex(colour: Oklch)`,
`contrastRatio(first: Oklch, second: Oklch)`, `isInGamut(colour: Oklch)`.
Passing a string yields `NaN`, silently.

**Three claim shapes, and only three.** Each is anchored on a syntactic form
that already exists in the tree, so the guard matches what authors already
write rather than demanding a new dialect:

- **A — declaration and its gloss**, either order:
  `--ring: oklch(0.62 0.15 160); /* #009f68 */` or
  `--primary: #009f68; /* oklch(0.62 0.15 160) */`.
- **B — tuple row**: `["--muted-foreground", "oklch(0.53 0.02 160)", "#627068"]`,
  the shape `docs/tasks/APRAS-76-mock.html` uses to drive a mock's swatch table.
- **C — equivalence connector**: an `oklch(...)` followed by nothing but
  whitespace and inline markup and then one of `=`, `==`, `→`, `->`, `≈`, then a
  `#rrggbb`. Shape C must be matched **across line breaks** on text with HTML
  tags and Markdown emphasis/backtick/pipe characters stripped:
  `docs/tasks/APRAS-68-mock.html:93` ends a line with `≈` and carries its hex on
  the next, and `docs/tasks/APRAS-87-spec.md:23` writes the claim inside a
  Markdown table row.

**The oklch must come first in shape C, and the hex-first direction is
excluded.** `oklch(...) → #rrggbb` is a paint claim and is exact.
`#rrggbb → oklch(...)` is a *derivation* claim through a 2dp-rounded emitted
string, and legitimately lands one 8-bit step away —
`docs/tasks/APRAS-68-spec.md:235` writes `#008a5a → oklch(0.56 0.13 160.15)`,
whose round trip is `#008b5a`. A guard that treated that as a mismatch would be
wrong, and the task must not "fix" that line.

**A naive same-line "one oklch and one hex" scan is not acceptable** and the
reviewer should reject it: run over today's tree it reports four mismatches, all
four false, and all four are named here because the weakest two are the stronger
argument:

- `docs/tasks/APRAS-68-mock.html:93` — the hex on the line is the brand *input*
  `#0ea5e9`, while the emitted `oklch(0.68 0.14 237.32)` paints `#23a3e3`.
- `docs/tasks/APRAS-68-spec.md:235` — a hex-first derivation claim, legitimate
  and excluded by the ordering rule below.
- `docs/tasks/APRAS-68-spec.md:477` — an unrelated `oklch()` and an unrelated
  hex inside one sentence; no colour claim at all.
- `docs/tasks/APRAS-92-spec.md:717` — a hex sitting inside a "contains none of"
  assertion; again no colour claim.

The last two are excluded by **nothing** in the ordering rule: only connector
anchoring keeps them out, which is why shape C is defined as narrowly as it is.
A looser naive scan — *first* oklch and *first* hex on the line, which is what
an implementer is most likely to write — reports 15 mismatches on the same tree,
all false.

### 2. Document set, and the exclusions that are load-bearing

Scanned: `docs/tasks/**/*.{md,html}` and `docs/frontend/**/*.md`.

Excluded, with the reason stated in the test's own comment:
`docs/reviews/**` and `docs/suggestions-log.md` are **records of a
conversation** and quote wrong values precisely in order to condemn them —
`docs/reviews/APRAS-98-spec-review-round3.md` contains
the clip value `#00a166`, written as the paint of `oklch(0.62 0.15 160)` with an
arrow connector, as the finding against it.
Guarding a review would require rewriting the evidence. Also excluded:
`docs/features_planning_and_questions.md`, `docs/obras-fonte/**`,
`docs/superpowers/**`.

**A specification that must quote a wrong value writes it with `≠`.** The
connector set is equality-only, so `oklch(0.62 0.15 160) ≠ #00a166` is both
true prose and mechanically inert. This spec uses that form.

**One further escape exists and only one, and it is line-anchored.** A line
whose entire content, ignoring only leading and trailing whitespace, is
`<!-- contrast-guard: ignore — <reason> -->` suppresses the next claim found
after it. Marker detection runs on the **raw** line: no HTML tags, backticks,
emphasis or pipes are stripped (unlike shape C), so an occurrence wrapped in
backticks, or with any prose before or after it on the line, is documentation of
the marker and not a use of it. The previous sentence is itself such an
occurrence, and `grep -rn 'contrast-guard' docs/` finding this spec is therefore
expected and inert. The rule the implementer must honour, and the provenance
document must repeat: **documentation of either marker may never place the
marker alone on a line.** The test asserts that the set of anchored ignore
markers across the scanned set equals an exact inline list which is **empty** at
landing, so the escape cannot spread without a visible diff.

**The ratio marker is anchored identically, and an anchored marker whose
operands do not parse is a failure, never a skip.** `parseOklch` returns `null`
for anything that is not a literal `oklch(L C H)` and §1 notes the module then
yields `NaN` silently, so a guard that skipped unparsable markers would let a
typo disable its own check. When an anchored ratio marker's two operands do not
both parse, or its figure is not four decimal digits, the test fails naming the
file and the 1-based line. The template form `<!-- ratio: oklch(L C H) on
oklch(L C H) = N.NNNN -->`, whose placeholders cannot parse, is published inline
in prose for exactly this reason — never on a line of its own.

### 3. Where the test lives, and why no config changes

`frontend/src/__tests__/docsColourProvenance.test.ts`, beside
`themeContrast.test.ts` and `themeTokenCompile.test.ts`, which are the existing
node-environment file-reading guards.

- **It is collected.** `frontend/vitest.config.ts` sets no `test.include`, so
  Vitest's default glob applies and is resolved relative to the project root
  `frontend/`. A test file placed outside `frontend/` would be silently not
  collected; the subjects live outside, the test does not.
- **It reads with `node:fs`, never with `?raw` or `import.meta.glob`.** Those
  two are Vite-resolved: `import.meta.glob("/docs/**")` is root-relative to
  `frontend/` and matches nothing, and a `?raw` import outside the root is
  refused by `server.fs.allow`. `node:fs` is subject to neither, so
  **`frontend/vitest.config.ts` is not modified** — no `fs.allow` entry, no
  `include` change. The file carries `/// <reference types="node" />` and
  `// @vitest-environment node`, exactly as `themeContrast.test.ts` does, so
  `import.meta.url` is a `file:` URL and `npm run build`'s `tsc -b` typechecks it.
- **Coverage is unaffected.** `coverage.include` is `["src/**/*"]` and
  `**/*.test.ts` is excluded, so the guard enters no numerator and no
  denominator; the 80/78/76/80 thresholds are untouched, and the task adds no
  production source.

### 4. The positive control (result 4) — measured against the **committed** tree

A walk that matched nothing would pass every assertion, so the test asserts
floors. The floors must hold in CI, where **untracked files do not exist**:
`docs/tasks/APRAS-98-mock.html` and `docs/tasks/APRAS-98-spec.md` contribute 14
of today's 31 working-tree claims and are not committed. Measured on the
committed tree at `2cb0d48`, the three shapes yield **17 claims across 8 files**
out of **125** tracked documents in the scanned set — 98 `.md` (96 under
`docs/tasks/`, 2 under `docs/frontend/`) and 27 `.html`.

Asserted floors — the implementer may raise them to whatever the landing commit
measures, and may not lower them. They should be **re-measured at landing, not
copied from here**: this task's own `docs/frontend/contrast-provenance.md` enters
the scanned set, adding one document to the read count and at least the three
connector-form hexes §6 requires of it to the claim count. The 19 inventory rows
add **nothing** to these floors — a Markdown row with no connector yields no
claim under any of the three shapes, which is exactly why §6 guards the table by
parsing it rather than by leaving it to the scan — and the four ratio markers are
counted by §5's own `≥ 4`, not here. Three of
the floors below sit exactly at the committed measurement, which is correct for
a floor and means a concurrent edit to either named sentinel turns CI red — that
is what naming them is for. **Expected post-landing measurement, for comparison:
126 documents read, 9 contributing, 20 claims** — the committed figures plus this
task's own provenance document and its three connector hexes. A re-measurement
that comes out *below* those numbers is a defect to investigate, not a lower
floor to assert.

- ≥ 100 documents read;
- ≥ 8 documents contributing at least one claim;
- ≥ 17 claims checked in total;
- named sentinels, all committed: `docs/tasks/APRAS-90-mock.html` yields ≥ 5
  shape-A claims, `docs/tasks/APRAS-76-mock.html` ≥ 4 shape-B claims, and the
  pair `oklch(0.62 0.15 160)` / `#009f68` appears at least twice across the set.

### 5. Ratios (result 2) — the escape is taken, deliberately

**Contrast ratios as they appear in prose are out of mechanical reach, and this
task does not pretend to locate them.** A ratio is written as `3.4054`,
`3.41:1`, `≥ 4.5:1`, `6,96:1`, as a bare table cell, and as a bold figure inside
a sentence; its two operands are named as token names, as hexes, as `oklch()`
strings, or by role ("the ring on the card"), in either order, often in a
different clause or a table header. There is no form a scanner can anchor on
without either false positives on every number in the document or a
token-resolution engine for both light and dark blocks of `index.css` — which is
a second deliverable, not this one.

What the task does instead, so ratios are not left unguarded forever:

- **An opt-in locatable form is defined** and checked wherever it appears:
  `<!-- ratio: oklch(L C H) on oklch(L C H) = N.NNNN -->`, a single-line HTML
  comment valid in both Markdown and HTML, self-contained because both operands
  are literal `oklch()` strings and need no token resolution. The guard
  re-derives it with `contrastRatio` and compares as **rounding equality on four
  decimals**: `derived.toFixed(4)` must string-equal the marker's figure, which
  must itself carry exactly four decimal digits. Not `toBeCloseTo`, which
  differs at the boundary.
- **The mechanism is seeded, so it is not vacuous.** `docs/frontend/contrast-provenance.md`
  publishes the four figures this investigation derived, each carrying its
  marker, and the test asserts it finds **≥ 4** markers and that all pass:
  light `--ring` on `--card` **3.4054**, light `--ring` on `--destructive`
  **1.4117**, dark `--ring` on `--card` **6.4180**, dark `--ring` on
  `--destructive` **1.8021**.
- **Residual risk, stated plainly:** an unmarked ratio in prose remains
  unguarded, and the clip method would produce 3.3564 / 1.4252 / 6.4408 /
  1.8085 for those same four pairs — differences in the second decimal that no
  reader can spot. Only the convention in §6 covers that gap, and a convention
  is weaker than a test. A follow-up task may add token resolution and make the
  marker mandatory; this task does not.

### 6. Provenance: a convention, and a criterion for the part that can be checked

The defect was three agents reproducing one method, so the principle is stated
where an author will meet it, not only enforced where a scanner can reach.

`docs/frontend/contrast-provenance.md` (new) states, as a **convention**:

> `frontend/src/lib/contrast.ts` is the only permitted source of a colour
> figure in this repository. A document that quotes a hex or a ratio records
> **how** it was derived — the function called and the input given — so a
> reader can tell a measurement from a recollection. A figure with no recorded
> provenance is a recollection and may not be relied on. A per-channel sRGB
> clip is not an approximation of the gamut map; it is a different colour.

and carries, as **content**:

- the four marked ratios from §5, and the hexes `#009f68` (light `--ring` and
  `--primary`), `#e60018` (light `--destructive`), `#00aa6f` (dark `--ring`);
- the **out-of-gamut inventory** (result 5): the **19** `oklch()` tokens in
  `frontend/src/index.css` for which `isInGamut` is false — **16 light, 3
  dark** — the only tokens where a clip and a gamut map can differ at all. Each
  entry carries its `oklch()` value and its `oklchToHex` result:

  | block | token | oklch | hex |
  |---|---|---|---|
  | `:root` | `--primary` | `oklch(0.62 0.15 160)` | `#009f68` |
  | `:root` | `--destructive` | `oklch(0.58 0.24 27)` | `#e60018` |
  | `:root` | `--ring` | `oklch(0.62 0.15 160)` | `#009f68` |
  | `:root` | `--status-pending-bg` | `oklch(0.96 0.05 85)` | `#fff0d1` |
  | `:root` | `--status-pending-fg` | `oklch(0.5 0.12 85)` | `#7e5d00` |
  | `:root` | `--status-in-progress-bg` | `oklch(0.93 0.06 240)` | `#ceedff` |
  | `:root` | `--status-in-progress-fg` | `oklch(0.4 0.15 240)` | `#004d7d` |
  | `:root` | `--status-blocked-bg` | `oklch(0.95 0.08 70)` | `#ffebd2` |
  | `:root` | `--status-blocked-fg` | `oklch(0.5 0.15 70)` | `#8b5600` |
  | `:root` | `--status-completed-bg` | `oklch(0.94 0.1 160)` | `#b3ffd6` |
  | `:root` | `--status-completed-fg` | `oklch(0.4 0.15 160)` | `#005931` |
  | `:root` | `--status-canceled-bg` | `oklch(0.95 0.04 20)` | `#ffe7e6` |
  | `:root` | `--priority-medium-fg` | `oklch(0.38 0.1 210)` | `#004d58` |
  | `:root` | `--priority-high-bg` | `oklch(0.95 0.08 70)` | `#ffebd2` |
  | `:root` | `--priority-high-fg` | `oklch(0.5 0.15 70)` | `#8b5600` |
  | `:root` | `--priority-urgent-bg` | `oklch(0.94 0.1 25)` | `#ffdfda` |
  | `.dark` | `--primary` | `oklch(0.65 0.15 160)` | `#00aa6f` |
  | `.dark` | `--primary-text` | `oklch(0.65 0.15 160)` | `#00aa6f` |
  | `.dark` | `--ring` | `oklch(0.65 0.15 160)` | `#00aa6f` |

- the **asymmetry warning**, printed next to that table because the inventory
  looks like a miscount and is not: there are five `--status-*-bg` entries but
  only **four** `--status-*-fg`, because `--status-canceled-fg:
  oklch(0.5 0.15 20)` is **in** gamut while the structurally identical
  `--status-blocked-fg: oklch(0.5 0.15 70)` is **out**. At L 0.5 / C 0.15, hue
  20 is inside sRGB while hues 70, 160 and 240 are not — hue alone flips it. A
  reader who "restores" the symmetry by adding `--status-canceled-fg` breaks the
  exact-set assertion, and the document says so;
- the **coincidence warning**: dark `--ring` `oklch(0.65 0.15 160)` paints
  `#00aa6f` under *both* methods, so `docs/tasks/APRAS-98-mock.html:52` was
  right by accident while every other figure around it was wrong. A hex that
  agrees is not evidence the method was right. By contrast, light `--ring`
  `oklch(0.62 0.15 160)` paints `#009f68` and `≠ #00a166`, and light
  `--destructive` `oklch(0.58 0.24 27)` paints `#e60018` and `≠ #e60016`.
- the **named exception**: `frontend/src/__tests__/themeContrast.test.ts` is a
  deliberate second oracle for the stylesheet (APRAS-76), reduces chroma on a
  0.01 grid rather than by bisection, and therefore reports `#019f68` and
  3.4078 where `contrast.ts` reports `#009f68` and 3.4054. It is **not** a
  source for a published figure and is not touched by this task.

**The document's table is the authority, and the test parses it out of the
document.** Of the two ways to close this, the spec picks parsing — not a
connector form on every row — because it leaves exactly one *authoritative* copy
of the figure in the repository. The guard reads `docs/frontend/contrast-provenance.md`, parses
every row of the inventory table — `| <block> | <token> | oklch(L C H) |
#rrggbb |`, with surrounding backticks and padding whitespace stripped — into a
set of `(block, token, oklch, hex)` tuples; derives the same set from
`frontend/src/index.css` by keeping the declarations for which `isInGamut` is
false and painting each with `oklchToHex`; and asserts the two sets are
**equal**, failing with the rows present on one side and absent on the other.

**The test carries no inline copy of those 19 rows**, with the single exception
of the sentinel pair `oklch(0.62 0.15 160)`/`#009f68` that §4 requires it to
count, which rows `:root`/`--primary` and `:root`/`--ring` also carry. That is the point: the
document is the only copy the guard trusts, which is what makes the stated
consequence true — a
token added, moved out of gamut or repainted fails until **the document** is
updated, and a row that drifts (a future edit leaving `#00a166` in the `:root`
`--primary` row) fails too. Anti-vacuity, since set equality is satisfied by two
empty sets: both sides must have **≥ 19** members, so a table the parser fails to
locate cannot pass as empty-equals-empty. The 19 is a floor on the parse, never
the authority; the authority is `index.css` through `isInGamut` and `oklchToHex`.

**What in that document is guarded, and what is prose.** Guarded mechanically:
the 19 table rows, by the set equality above; the four ratio figures, by §5's
anchored `<!-- ratio: … -->` marker check (`contrastRatio`, four-decimal string
equality) — already covered, stated here so the next reader need not re-derive
it; and the three loose hexes of result 7, which the document must therefore
write in **shape-C connector form** — `light --ring oklch(0.62 0.15 160) →
#009f68`, `light --destructive oklch(0.58 0.24 27) → #e60018`, `dark --ring
oklch(0.65 0.15 160) → #00aa6f` — because `docs/frontend/**/*.md` is in the
scanned set of §2 and a hex written with no connector is unguarded prose.
Deliberately prose: the convention paragraph, the asymmetry explanation and the
coincidence explanation.

**The document states the rule for future authors, in one sentence of its own:**
to quote a figure `contrast.ts` does not produce, write it with `≠`, or suppress
the claim with an anchored `<!-- contrast-guard: ignore — <reason> -->` line,
which also requires editing this guard's exact list — and never place either
marker alone on a line when documenting it. That sentence is required content,
because `AGENTS.md` sends every author to this page and nowhere else.

**Every figure in that document that `contrast.ts` does not produce is written
with `≠`**, per §2's equality-only connector set: the clip values `#00a166` and
`#e60016`, the clip ratios 3.3564 / 1.4252 / 6.4408 / 1.8085, and the named
exception's `oklch(0.62 0.15 160) ≠ #019f68` with its 3.4078 kept outside any
marker. A connector or an anchored marker on any of those would make the guard
fail on the very document that explains why they differ.

The derivation is per-declaration and line-anchored: every
`oklch()` in that file sits on a line that also carries a `--token:`
declaration, there is no `oklch()` inside a gradient, a `color-mix()` or a
shorthand, and `parseOklch` returns non-null for all 58 occurrences, so nothing
is silently skipped. If any occurrence fails to parse, the test fails rather
than skipping it. The same intolerance applies to the document side: a table row
whose `oklch()` cell does not parse is a failure naming the row, never a skip.

`AGENTS.md` gains one short sub-section (≤ 8 lines) pointing at the new
document as the only permitted source for a colour figure, because the failure
mode was a generator that did not know the published values existed.

### 7. The guard adds no arithmetic of its own — pinned by imports, not by needles

The test imports `parseOklch`, `oklchToHex`, `contrastRatio` and `isInGamut`
from `../lib/contrast` and contains **no conversion arithmetic**: no WCAG weight
(`0.2126`, `0.7152`, `0.0722`), no Ottosson matrix coefficient, no sRGB transfer
constant (`12.92`, `1.055`, `0.04045`, `0.0031308`), no `Math.cbrt`, no
`** (1 / 2.4)`.

**A self-scan for those literals is not the mechanism, because it cannot work.**
An assertion that names its needles and reads its own source finds its own
needles and fails; every way out of that — needles built by concatenation,
excising the needle declaration before scanning — is an unspecified device two
implementers would choose differently. It is also a weak net: `0.2126` written
as `2126 / 10000`, the matrix to fewer digits, or
`import Color from "colorjs.io"` passes every needle.

**The mechanism is an import pin instead.** An assertion in the same file reads
its own source with `node:fs`, collects the module specifier of every line
matching an `^\s*import\b … from "<specifier>"` anchor — a real import
statement, never a string inside an array literal — and asserts two things:
every specifier is a member of the closed set `node:fs`, `node:path`,
`node:url`, `vitest`, `../lib/contrast`, and `../lib/contrast` is present. A
subset-plus-required-member check rather than exact equality, so the guard may
use `node:path` or not without the pin becoming a style rule; anything else at
all, including a second colour library, fails.

**The pin is static-import-only, and the anchor assumes one import per line.**
Two residual holes, stated rather than papered over: `const C = await
import("colorjs.io")` is a fourth dependency the `^\s*import` anchor does not
reject (a bare side-effect `import "x";` escapes the `from` clause too, but binds
nothing and so can carry no arithmetic), and a multi-line
`import { … }\nfrom "../lib/contrast";` would defeat the required-member half.
The implementer therefore (a) also fails the test if its own source matches
either of the **regex literals** `/await\s+import\s*\(/` and
`/\brequire\s*\(/` — and these are the required form precisely because a regex
literal's own source text is not what the pattern matches (`\s+` and `\(` do not
match themselves), so the assertion needs no concatenation, no excision and no
notion of comment-ness: it may be written literally, read its own source, and
still pass on a correct file — and (b) writes each import on a
single line, which the anchor requires — this repository has no Prettier config
and existing source carries single-line imports well past 300 characters, so
nothing reformats them. With those two clauses the pin is stronger than the
needle list in every case that matters; without them it is stronger only against
static imports.
This is not self-referential: the assertion's own expected set lives in an array
literal, which the `^\s*import` anchor does not match. It is strictly stronger
than the needle list, because any arithmetic the guard could reimplement must
either come from a fourth dependency, which the pin rejects, or be written
inline — and inline arithmetic has no imports to hide behind and is what code
review looks for. The absence of the arithmetic literals above remains a stated
property of the file, checked by the reviewer reading it, not by the file
reading itself.

APRAS-100's `0.2126` guard, if that task has landed, excludes `*.test.ts` under
`**/__tests__/**` by rule; this file is both, so it is excluded by the rule and
needs no special case there.

### 8. The already-wrong mocks (decision 3) — none, and no exception file

Measured with `contrast.ts`: on the committed tree at `2cb0d48`, **17 claims
across 8 documents, 0 mismatches**; over the whole working tree, including the
untracked APRAS-98 documents, ~31 claims across 10 documents, **0 mismatches**. APRAS-98's mock and spec now carry `#009f68`,
`#e60018` and `#00aa6f`, all three correct. **The guard ships green and
`frontend/src/__tests__/` gains no exceptions JSON.** The
`themeTokenMigration.exceptions.json` shape is deliberately **not** adopted:
there is nothing to record in it, and an empty exception file is an invitation.

If the implementer's run finds a mismatch — a mock landed by a concurrent task
between this spec and the implementation — the rule is: **fix the figure, do
not except it**, citing the derived value. This is the **only** circumstance in
which a committed value in another task's document may change (result 11's
proven-to-fail edits are temporary and restored), it is capped at **three
lines total**, and every such repair must be listed in the implementation report
with its file, line, published value and derived value. At the 0 mismatches
measured above the expected number of repairs is **zero**; result 12 is written
to allow exactly this cap and nothing more. If more than three lines would need
editing, stop and report rather than editing many documents other agents are
actively writing.

### 9. Files touched

- `frontend/src/__tests__/docsColourProvenance.test.ts` — **new.** The whole
  guard: the three claim shapes, the two anchored markers, the positive-control
  floors, the out-of-gamut set equality **parsed from
  `docs/frontend/contrast-provenance.md`** (no inline copy of the 19 rows beyond
  §4's sentinel pair), the
  import pin with its static-import clause.
- `docs/frontend/contrast-provenance.md` — **new,** and the only **guarded and
  authoritative** copy of the inventory figure (§6's table in this spec is a
  record of the authoring-time measurement, not a source). The convention, the four
  marked ratios, the three published hexes in connector form, the 19-token
  out-of-gamut inventory table parsed by the guard, with
  its derived hexes and the `--status-canceled-fg` asymmetry warning, the
  coincidence warning, the `themeContrast.test.ts` exception, and the one-sentence
  `≠`-or-ignore-marker rule for future authors.
- `AGENTS.md` — one new sub-section (≤ 8 lines) pointing at that document.
- `docs/tasks/APRAS-123-spec.md` — this spec.
- `frontend/vitest.config.ts` — **unchanged**, by the decision in §3.

### 10. Test criteria

- `cd frontend && npx vitest run src/__tests__/docsColourProvenance.test.ts`
  green.
- **Proven to fail (result 3).** The implementer temporarily edits one claim in
  the working tree to the clip value — `docs/tasks/APRAS-90-mock.html:16`
  `--primary: #009f68; /* oklch(0.62 0.15 160) */` becomes `#00a166` — records
  the failure message verbatim in the implementation report, and restores the
  file. The message must name the file, the line, `#00a166` and `#009f68`. The
  same is done once for the ratio marker (`3.4054` → `3.3564`), and once for one
  hex of one row of `docs/frontend/contrast-provenance.md`'s inventory table,
  which must fail by set inequality against `index.css` and name the row. No
  edit is committed; `git status` for `docs/tasks/` and `docs/frontend/` is back
  to its prior state afterwards.
- `cd frontend && npm test` green; `cd frontend && npm run build`
  (`tsc -b && vite build`) green.
- `cd frontend && npm run lint` **no worse than base**: ~375 pre-existing
  errors across 64 files, so the criterion is a comparison against `master`,
  never zero, and the new file contributes none of its own.
- The backend is untouched, so `backend/` needs no run.

## Expected Results

- [ ] `frontend/src/__tests__/docsColourProvenance.test.ts` exists, imports
      `parseOklch`, `oklchToHex`, `contrastRatio` and `isInGamut` from
      `src/lib/contrast.ts`, reads its subjects with `node:fs` under
      `// @vitest-environment node`, and passes.
- [ ] It re-derives every `#rrggbb` published as the paint of an `oklch(...)`
      across `docs/tasks/**/*.{md,html}` and `docs/frontend/**/*.md` in the
      three claim shapes (declaration-plus-gloss either order; `"--token",
      "oklch(...)", "#hex"` tuple; `oklch(...)` followed by `=`/`==`/`→`/`->`/`≈`
      and then a hex, matched across line breaks with HTML tags and Markdown
      emphasis stripped), and fails on disagreement with a message naming the
      file, the 1-based line, the published hex and the derived hex.
- [ ] The hex-first derivation direction (`#rrggbb → oklch(...)`) is **not**
      treated as a paint claim, so `docs/tasks/APRAS-68-spec.md:235`
      (`#008a5a → oklch(0.56 0.13 160.15)`, round-tripping to `#008b5a`) passes
      unchanged, and `docs/tasks/APRAS-68-mock.html:93` passes by deriving
      `#23a3e3` from `oklch(0.68 0.14 237.32)` rather than comparing against the
      brand input `#0ea5e9` on the same line. `docs/tasks/APRAS-68-spec.md:477`
      and `docs/tasks/APRAS-92-spec.md:717`, which a naive scan also flags,
      likewise pass: neither is a colour claim, and only connector anchoring
      excludes them.
- [ ] `docs/reviews/**` and `docs/suggestions-log.md` are excluded by an
      explicit rule whose comment names the reason, so
      `docs/reviews/APRAS-98-spec-review-round3.md`'s deliberate
      arrow-connected claim that `oklch(0.62 0.15 160)` paints the clip value
      `#00a166` does not fail the suite.
- [ ] The positive control passes and cannot pass vacuously: ≥ 100 documents
      read, ≥ 8 documents contributing a claim, ≥ 17 claims checked,
      `docs/tasks/APRAS-90-mock.html` contributing ≥ 5 and
      `docs/tasks/APRAS-76-mock.html` ≥ 4, with the pair
      `oklch(0.62 0.15 160)`/`#009f68` found at least twice. Every floor holds
      against the **committed** tree, not only the working tree.
- [ ] Four marked ratios are pinned and re-derived, and unmarked prose ratios
      are declared out of reach rather than silently claimed: the opt-in form
      `<!-- ratio: oklch(L C H) on oklch(L C H) = N.NNNN -->` is re-derived with
      `contrastRatio` wherever it appears anchored, compared as
      `derived.toFixed(4)` string-equality against the marker's four-decimal
      figure, the test asserts it found **≥ 4** such markers and that all pass,
      and the spec states in §5 that ratios written in prose remain unguarded
      and names the follow-up that would change that.
- [ ] `docs/frontend/contrast-provenance.md` exists and carries those four
      markers with the values 3.4054, 1.4117, 6.4180 and 1.8021; the hexes
      `#009f68`, `#e60018` and `#00aa6f`, each written in **connector form**
      after its `oklch()` (`oklch(0.62 0.15 160) → #009f68` and so on) so that
      shape C re-derives all three — the document is in the scanned set, and
      replacing any of the three with the clip value fails the suite; the
      convention that `contrast.ts` is the only permitted source and that a
      quoted figure records how it was derived; and the note that dark
      `--ring`'s `#00aa6f` is produced by both methods, so agreement is not
      evidence of method. Every figure in the document that `contrast.ts` does
      not produce — `#00a166`, `#e60016`, the clip ratios, and the
      `themeContrast.test.ts` exception's `#019f68` and 3.4078 — is written with
      `≠` or inside no connector and no marker, so the document that explains
      the wrong values does not fail on them. The document also carries one
      sentence telling future authors that rule: quote a non-derived figure with
      `≠`, or suppress it with an anchored ignore line, and never place either
      marker alone on a line when documenting it.
- [ ] The table in `docs/frontend/contrast-provenance.md` is the **only guarded
      and authoritative** copy of the out-of-gamut inventory, and the **test
      parses that document** rather than duplicating it: it reads the
      table's rows as `(block, token, oklch, hex)` tuples and asserts the parsed
      set is **equal** to the set derived from `frontend/src/index.css` by
      `isInGamut` plus `oklchToHex`, failing with the rows present on one side
      and absent on the other. Checkable form: grepping
      `frontend/src/__tests__/docsColourProvenance.test.ts` for each of the 19
      rows' `oklch()`/`#rrggbb` pairs finds **no pair other than the single
      sentinel pair `oklch(0.62 0.15 160)`/`#009f68`** that result 5 requires the
      test to count — that one pair is exempt because rows `:root`/`--primary`
      and `:root`/`--ring` carry it and the sentinel assertion must hold it
      literally; **one** hit on any other row's pair is a failure, not only two.
      (The identical table in §6 of `docs/tasks/APRAS-123-spec.md` is a
      record of the measurement at authoring time, not a source and not guarded;
      finding it is expected and does not fail this result.) Both sides carry
      **≥ 19** rows, so an empty parse cannot pass as empty-equals-empty, and a
      row whose `oklch()` cell does not parse fails naming the row. Today the
      set is 16 light (`--primary`, `--destructive`, `--ring`, the five
      `--status-*-bg`, the four `--status-*-fg`, `--priority-medium-fg`,
      `--priority-high-bg`, `--priority-high-fg`, `--priority-urgent-bg`) and 3
      dark (`--primary`, `--primary-text`, `--ring`). The document also states
      that `--status-canceled-fg: oklch(0.5 0.15 20)` is **in** gamut while
      `--status-blocked-fg: oklch(0.5 0.15 70)` is out, which is why there are
      five `--status-*-bg` rows but only four `--status-*-fg`.
- [ ] Both marker forms are **line-anchored and cannot be neutralised
      invisibly**: the test asserts that the set of lines across the scanned set
      whose entire trimmed raw content is
      `<!-- contrast-guard: ignore — <reason> -->` equals an exact inline list,
      and that list is **empty** at landing, so no document in `docs/tasks/` or
      `docs/frontend/` suppresses a claim; occurrences of either marker inside a
      prose sentence or inside backticks — including this spec's own §2 and the
      provenance document's template — are documentation and are not counted;
      and an anchored ratio marker whose operands do not parse fails the test
      naming file and line rather than being skipped.
- [ ] No conversion arithmetic is added: an assertion in the same file reads its
      own source with `node:fs` and asserts that every module specifier of its
      real `import` statements (matched on an `^\s*import` anchor, so strings in
      array literals are not matched) is a member of the closed set `node:fs`,
      `node:path`, `node:url`, `vitest`, `../lib/contrast`, with
      `../lib/contrast` present — so no second colour library and no
      reimplemented conversion can enter. The same assertion also fails if that
      source matches the regex literals `/await\s+import\s*\(/` or
      `/\brequire\s*\(/`, written literally in the test (a regex literal's own
      source text does not match these patterns, so the assertion passes on a
      correct file without any excision or concatenation device, and
      comment-ness is never consulted). Meanwhile `frontend/src/lib/contrast.ts` and
      `backend/app/core/branding.py` are unchanged; and if APRAS-100 has landed
      its `0.2126` guard still passes, the new file being excluded by its
      `*.test.ts` / `**/__tests__/**` rule rather than by a special case.
- [ ] `frontend/vitest.config.ts` is unchanged — no `server.fs.allow` entry and
      no `test.include` change — and the coverage thresholds (80/78/76/80) are
      neither lowered nor breached.
- [ ] The guard is proven to fail, three ways: the implementation report records
      a run with `docs/tasks/APRAS-90-mock.html`'s `#009f68` replaced by the clip
      value `#00a166`, a run with a ratio marker set to the clip value `3.3564`,
      and a run with one hex of one row of the provenance document's inventory
      table set to `#00a166` — the last failing by **set inequality against
      `index.css`**, naming that row. Each failure message is quoted verbatim;
      every file is restored and no such edit is committed.
- [ ] No exceptions JSON is added for this guard, and the guard passes on the
      tree as committed with no value in `frontend/src/index.css` changed at
      all. The **only** permitted *committed* edit to an existing
      `docs/tasks/` document is
      §8's repair of a figure that disagrees with `contrast.ts` and was landed by
      a concurrent task: at most **three lines in total**, each listed in the
      implementation report with file, line, published and derived value, and
      zero such repairs expected at the 0 mismatches measured at `2cb0d48`. Any
      fourth line means stop and report, not edit.
- [ ] `AGENTS.md` gains a sub-section of at most 8 lines naming
      `docs/frontend/contrast-provenance.md` as the only permitted source for a
      colour figure.
- [ ] `cd frontend && npm test` and `npm run build` (`tsc -b && vite build`)
      both green, and `npm run lint` no worse than `master`'s measured base of
      ~375 errors across 64 files.

## Out of Scope

- Any change to `frontend/src/lib/contrast.ts`,
  `backend/app/core/branding.py`, `frontend/src/index.css` or
  `backend/tests/data/contrast_fixtures.json`.
- `frontend/src/__tests__/themeContrast.test.ts`'s independent oracle, which is
  a deliberate second implementation for the stylesheet and is recorded as a
  named exception rather than unified here.
- Token resolution for ratios — resolving `--ring on --card` against the light
  and dark blocks of `index.css`, and making the ratio marker mandatory. That
  is the follow-up §5 names.
- Guarding `docs/reviews/**`, `docs/suggestions-log.md` or any document outside
  `docs/tasks/` and `docs/frontend/`.
- Rewriting the inventory table's 19 rows into connector form so the ordinary
  shape-C scan catches them — the alternative to §6's parse, rejected because it
  would leave the test and the document each holding a copy of the figure.
- Fixing figures in other tasks' documents beyond the three-line cap in §8, and
  any change at all to `frontend/src/index.css`.
