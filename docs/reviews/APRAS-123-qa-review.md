# APRAS-123 — QA verification

**Task**: Guard the hex and ratio comments in docs/tasks mocks against the clip method
**Verified at**: worktree `/Users/heitor/workspace/apras/.claude/worktrees/agent-a0c62ad5b030903eb`,
branch `worktree-agent-a0c62ad5b030903eb`, on top of `master` = `2124432`.
Staged paths: `AGENTS.md` (M), `docs/frontend/contrast-provenance.md` (A),
`frontend/src/__tests__/docsColourProvenance.test.ts` (A). Nothing unstaged.

**VERDICT: APPROVED**

---

## Method notes

### Canonical values derived by execution, not by reasoning

Before reading any figure in the document under review, I wrote a throwaway
vitest probe that imports `frontend/src/lib/contrast.ts` and prints its output,
and ran it from the worktree's `frontend/`. Everything below that claims a
"canonical" value is that probe's output. The probe was deleted afterwards.

```
HEX oklch(0.62 0.15 160)    => #009f68  inGamut=false
HEX oklch(0.58 0.24 27)     => #e60018  inGamut=false
HEX oklch(0.65 0.15 160)    => #00aa6f  inGamut=false
HEX oklch(0.56 0.13 160.15) => #008b5a  inGamut=false
HEX oklch(0.68 0.14 237.32) => #23a3e3  inGamut=true
HEX oklch(0.5 0.15 20)      => #a8353e  inGamut=TRUE   (--status-canceled-fg)
HEX oklch(0.5 0.15 70)      => #8b5600  inGamut=false  (--status-blocked-fg)

RATIO oklch(0.62 0.15 160) on oklch(1 0 0)          => 3.4054
RATIO oklch(0.62 0.15 160) on oklch(0.58 0.24 27)   => 1.4117
RATIO oklch(0.65 0.15 160) on oklch(0.16 0.01 160)  => 6.4180
RATIO oklch(0.65 0.15 160) on oklch(0.55 0.22 25)   => 1.8021
```

I also re-derived the whole out-of-gamut inventory from `frontend/src/index.css`
with my own independent walker (not the test's) — `isInGamut` false, painted
with `oklchToHex`. It produced exactly 19 rows, 16 in `:root` and 3 in `.dark`,
identical token-for-token and hex-for-hex to the table published in
`docs/frontend/contrast-provenance.md`. 58 lines of `index.css` carry an
`oklch()`; all 58 were readable as `--token: oklch(L C H)`.

### The "committed tree" measurement for R5

The main checkout and the worktree both carry many untracked documents under
`docs/`. To measure the floors against the state that will actually land, I
exported `git archive HEAD` into the scratchpad and overlaid the three staged
blobs (`git show :<path>`), producing a faithful landing tree with no untracked
drafts. All counts reported for R5 are from that tree. The guard passes there:
**14 tests, 14 passed.**

### Mutations

All R12/R7/R8/R9/R10 mutations were performed on that scratchpad landing-tree
export rather than on the worktree, so the worktree was never edited at all.
Each pristine file was copied aside, mutated, run, restored, and `cmp`-verified.
Final worktree state is byte-identical to how I found it: the same three staged
paths, `git diff --stat` empty, and the same two untracked files
(`docs/reviews/APRAS-123-implementation.md`, `docs/tasks/APRAS-123-spec.md`)
that were present on arrival.

---

## Expected results checked

### R1 — file exists, imports, node env, passes — PASS

`frontend/src/__tests__/docsColourProvenance.test.ts` exists. Line 2 is
`// @vitest-environment node`. Line 9 imports `readdirSync, readFileSync` from
`node:fs`; line 13 imports `contrastRatio, isInGamut, oklchToHex, parseOklch`
from `../lib/contrast`. Subjects are read with `readFileSync`/`readdirSync`.
Run in the worktree and in the committed-tree export: 14/14 pass.

### R2 — three claim shapes, re-derivation, failure message — PASS

All three shapes are implemented and all three are **exercised by real
documents today**, which I confirmed by dumping the scan's claim list:

- Shape A, gloss first — `docs/tasks/APRAS-90-mock.html:16`
  `--primary: #009f68;       /* oklch(0.62 0.15 160) */` (5 claims in that file).
- Shape A, declaration first — not present in the corpus today, so I planted
  `--ring: oklch(0.62 0.15 160); /* #00a166 */` in a *subdirectory*
  (`docs/tasks/qaprobe/probe.md`) and the guard caught it:
  `docs/tasks/qaprobe/probe.md:1 publishes #00a166 as the paint of oklch(0.62 0.15 160), but contrast.ts derives #009f68`.
  This also proves `collectFiles` recurses into subdirectories as `**` requires.
- Shape B, tuple — `docs/tasks/APRAS-76-mock.html:177,178,188,189`,
  e.g. `["--muted-foreground", "oklch(0.55 0.02 160)", "#68756e"],`.
- Shape C, connector — `=` at `docs/tasks/APRAS-68-spec.md:98` and
  `docs/tasks/APRAS-76-spec.md:96`; `→` at `docs/tasks/APRAS-87-spec.md:23` and
  `:24` (inside a Markdown table row, pipes and backticks stripped) and at
  `docs/tasks/APRAS-88-spec.md:26`; `≈` **across a line break with `<code>`
  tags** at `docs/tasks/APRAS-68-mock.html:93`.

Scanned set is `docs/tasks/**/*.{md,html}` and `docs/frontend/**/*.md`
(`SCANNED_DIRECTORIES`, lines 50–56). Failure message names file, 1-based line,
published hex and derived hex — verified verbatim in R12 below.

### R3 — hex-first direction is not a paint claim — PASS, each site checked individually

All four named sites were checked one at a time against the dumped claim list,
and all four files *are* in the scanned set (so none passes by exclusion —
`APRAS-68-spec.md` itself contributes a claim at line 98).

| Site | Raw content | Why it is not a claim | In claim list? |
|---|---|---|---|
| `docs/tasks/APRAS-68-spec.md:235` | `` illegible**, e.g. `#008a5a` → `oklch(0.56 0.13 160.15)` measured **4.5129**, `` | hex-first: shape C requires the `oklch()` *before* the connector | no |
| `docs/tasks/APRAS-68-spec.md:477` | `` 83.88)` over `oklch(0.98 0 0)` at 4.596, and `#0ea5e9` as accent is pinned `` | one `oklch()` and one hex on the line with **no connector between them** | no |
| `docs/tasks/APRAS-92-spec.md:717` | `` body contains `oklch(0.58 0.22 27.33)` and contains none of `#174b40`, `` | same — connector anchoring alone excludes it | no |
| `docs/tasks/APRAS-68-mock.html:93` | `` <code>--secondary</code>: <code>#0ea5e9</code> emite <code>oklch(0.68 0.14 237.32)</code> ≈ `` + next line `` <code>#23a3e3</code> `` | **is** a claim, read in the correct direction | yes, exactly one: `oklch(0.68 0.14 237.32) -> #23a3e3` |

I independently confirmed the arithmetic: `oklch(0.56 0.13 160.15)` round-trips
to `#008b5a`, one 8-bit step from the published `#008a5a` — so reading :235 as a
paint claim would indeed be a false mismatch. And `oklch(0.68 0.14 237.32)`
derives `#23a3e3`, not the brand input `#0ea5e9` that shares the line. The test
pins all four sites explicitly at lines 479–504, including
`expect(mock[0].hex).not.toBe("#0ea5e9")`.

### R4 — `docs/reviews/**` and `docs/suggestions-log.md` excluded, reason named — PASS

`EXCLUDED_PATHS` (lines 70–76) lists both, under a doc comment (lines 58–69)
that names the reason explicitly: reviews are *records of a conversation* that
quote wrong values in order to condemn them, and it names
`docs/reviews/APRAS-98-spec-review-round3.md` as the case in point. I confirmed
that file really does carry the arrow-connected clip claim it is excused for:

```
/Users/heitor/workspace/apras/docs/reviews/APRAS-98-spec-review-round3.md:27
| `--ring` light `oklch(0.62 0.15 160)` → `#00a166` | — | `#00a166` ✓ |
```

That is shape C with a clip hex, and the suite is green, so it does not fail.

### R5 — positive control, non-vacuous, floors hold on the committed tree — PASS

Measured on the landing tree (`HEAD` + the three staged blobs; **no untracked
drafts**):

| Floor | Required | Committed tree | Working tree |
|---|---|---|---|
| documents read | >= 100 | **126** | 128 |
| documents contributing a claim | >= 8 | **9** | 9 |
| claims checked | >= 17 | **20** | 20 |
| `docs/tasks/APRAS-90-mock.html` | >= 5 | **5** | 5 |
| `docs/tasks/APRAS-76-mock.html` | >= 4 | **4** | 4 |
| `oklch(0.62 0.15 160)`/`#009f68` pairs | >= 2 | **4** | 4 |

Contributing documents on the committed tree: `contrast-provenance.md` (3),
`APRAS-68-mock.html` (1), `APRAS-68-spec.md` (1), `APRAS-76-mock.html` (4),
`APRAS-76-spec.md` (1), `APRAS-87-mock.html` (2), `APRAS-87-spec.md` (2),
`APRAS-88-spec.md` (1), `APRAS-90-mock.html` (5). Even discounting the
provenance document itself, 8 documents contribute, so the floor holds without
the new document propping it up. Every floor is met with margin >= 0 and no
floor depends on an untracked file.

### R6 — four marked ratios re-derived — PASS

`ANCHORED_RATIO_MARKER` + `RATIO_MARKER_BODY` (lines 143–147) require exactly
four decimals; comparison is `contrastRatio(first, second).toFixed(4)` against
the marker figure by `===` (line 571), and line 580 asserts
`SCAN.ratios.length >= 4`. The scan finds exactly 4 anchored markers, all in
`docs/frontend/contrast-provenance.md` (lines 89, 93, 97, 101), and all 4 match
the ratios I derived myself. A malformed marker fails rather than being skipped
— verified in R9.

### R7 — the provenance document's content — PASS

`docs/frontend/contrast-provenance.md` exists, is in the scanned set (it
contributes 3 claims), and contains:

- The four markers with **3.4054, 1.4117, 6.4180, 1.8021** — all four match my
  independent `contrastRatio` output exactly.
- The three hexes in **connector form** so shape C re-derives them (lines 65–67:
  `oklch(0.62 0.15 160)` → `#009f68`, `oklch(0.58 0.24 27)` → `#e60018`,
  `oklch(0.65 0.15 160)` → `#00aa6f`). All three match my own derivation.
  Replacing each in turn fails the suite:
  - line 65 → `#00a166`: `docs/frontend/contrast-provenance.md:65 publishes #00a166 as the paint of oklch(0.62 0.15 160), but contrast.ts derives #009f68`
  - line 66 → `#e60016`: `docs/frontend/contrast-provenance.md:66 publishes #e60016 as the paint of oklch(0.58 0.24 27), but contrast.ts derives #e60018`
  - line 67 → `#00ab70`: `docs/frontend/contrast-provenance.md:67 publishes #00ab70 as the paint of oklch(0.65 0.15 160), but contrast.ts derives #00aa6f`
    (the clip value for this one *is* `#00aa6f`, so a neighbouring wrong hex was
    used; the point — that shape C really re-derives the third hex too — is made.)
- The convention that `contrast.ts` is the only permitted source (blockquote,
  lines 16–21).
- The "Agreement is not evidence of method" section (lines 74–80), stating that
  dark `--ring`'s `#00aa6f` is produced by both the gamut map and the clip, so
  agreement proves nothing about method.
- Every figure `contrast.ts` does **not** produce is inert: `#00a166` and
  `#e60016` with `≠` (lines 69–70); the four clip ratios 3.3564 / 1.4252 /
  6.4408 / 1.8085 in bare prose with no marker (lines 103–106); the
  `themeContrast.test.ts` exception's `#019f68` with `≠` and 3.4078 in bare
  prose (lines 159–160). The suite is green with all of them present, which is
  the mechanical proof that none is anchored.
- One sentence stating the rule for future authors — "### How to quote a figure
  this module does not produce", line 34: *"One sentence, and it is the whole
  rule: to quote a figure `contrast.ts` does not produce, write it with `≠`, or
  suppress the claim with an anchored `<!-- contrast-guard: ignore — reason -->`
  line … and never place either marker alone on a line when you are documenting
  the marker rather than using it."*

### R8 — the table is the single authoritative copy, parsed not duplicated — PASS

**Set equality against `index.css`.** `parsePublishedInventory` reads the table
rows as `(block, token, oklch, hex)` tuples (lines 372–412);
`deriveStylesheetInventory` builds the other side from `frontend/src/index.css`
with `isInGamut` + `oklchToHex` (lines 423–457); the comparison at lines 605–612
asserts `{ onlyInDocument: [], onlyInStylesheet: [] }`, which reports the rows
present on one side and absent on the other.

**No duplicated row.** I grepped the test source for each of the 19 rows'
`oklch()` and `#rrggbb` literals:

```
oklch(0.62 0.15 160) #009f68  -> 1 hit each   (the sentinel)
oklch(0.58 0.24 27)  #e60018  -> 0 / 0
oklch(0.96 0.05 85)  #fff0d1  -> 0 / 0
oklch(0.5 0.12 85)   #7e5d00  -> 0 / 0
oklch(0.93 0.06 240) #ceedff  -> 0 / 0
oklch(0.4 0.15 240)  #004d7d  -> 0 / 0
oklch(0.95 0.08 70)  #ffebd2  -> 0 / 0
oklch(0.5 0.15 70)   #8b5600  -> 0 / 0
oklch(0.94 0.1 160)  #b3ffd6  -> 0 / 0
oklch(0.4 0.15 160)  #005931  -> 0 / 0
oklch(0.95 0.04 20)  #ffe7e6  -> 0 / 0
oklch(0.38 0.1 210)  #004d58  -> 0 / 0
oklch(0.94 0.1 25)   #ffdfda  -> 0 / 0
oklch(0.65 0.15 160) #00aa6f  -> 0 / 0
```

The complete set of colour literals in the test file is
`oklch(0.62 0.15 160)`, `oklch(0.56 0.13 160.15)`, `oklch(0.68 0.14 237.32)`,
`#009f68`, `#008a5a`, `#0ea5e9` — i.e. the single sentinel pair R5 requires,
plus the four R3 negative-control values. **Zero** hits on any non-sentinel
inventory pair.

**Both sides carry >= 19.** Lines 601–602 assert `>= 19` on each side. My own
independent walk of `index.css` produced 19 rows, and the parse of the document
produced 19. Deleting the table from the document fails three ways:

```
docs/frontend/contrast-provenance.md carries no out-of-gamut inventory table: no
"| block | token | oklch | hex |" header row was found, so the set equality would
compare against nothing
```
plus both `>= 19` floors and the set equality — so empty-equals-empty cannot pass.

**An unparsable `oklch()` cell fails naming the row**, never skipped:

```
docs/frontend/contrast-provenance.md:124 has an oklch cell "oklch(0.5 0.12 eighty-five)"
that parseOklch cannot read, so the row :root | --status-pending-fg |
oklch(0.5 0.12 eighty-five) | #7e5d00 could not be checked
```

**Today's set** is exactly as stated: 16 `:root` (`--primary`, `--destructive`,
`--ring`, the five `--status-*-bg`, four `--status-*-fg`, `--priority-medium-fg`,
`--priority-high-bg`, `--priority-high-fg`, `--priority-urgent-bg`) and 3 `.dark`
(`--primary`, `--primary-text`, `--ring`) — my own derivation, matching.

**The asymmetry claim is true.** I derived it independently:
`--status-canceled-fg: oklch(0.5 0.15 20)` → `inGamut=true` (would paint
`#a8353e`), `--status-blocked-fg: oklch(0.5 0.15 70)` → `inGamut=false` →
`#8b5600`. The document states exactly this in "### The missing
`--status-canceled-fg` is not a miscount" (lines 142–151).

### R9 — both marker forms are line-anchored and cannot be neutralised invisibly — PASS

- The exact-list assertion is `expect(located).toEqual([])` plus
  `expect(SCAN.suppressed).toEqual([])` (lines 550–552) — the list is **empty at
  landing**, confirmed by `ignores: 0` in the scan dump.
- Planting a real anchored ignore marker **turns the suite red**, so the escape
  cannot spread silently:
  `AssertionError: expected [ 'docs/frontend/contrast-provenance.md:166' ] to deeply equal []`.
- A marker inside a prose sentence / inside backticks is **not** counted:
  appending `` See the `<!-- contrast-guard: ignore — reason -->` marker in prose here. ``
  left the suite at 14/14. The document's own two documentary occurrences
  (lines 36 and 45, both inside backticks with prose beside them) are likewise
  uncounted — `ignores: 0`, `ratios: 4`.
- A malformed anchored ratio marker **fails naming file and line** rather than
  being skipped:
  ```
  docs/frontend/contrast-provenance.md:166 is an anchored ratio marker whose body
  "oklch(0.62 0.15 wat) on oklch(1 0 0) = 3.4054" is not "oklch(L C H) on
  oklch(L C H) = N.NNNN" with exactly 4 decimal digits
  ```

### R10 — no conversion arithmetic; import pin holds for the stated reason — PASS

The assertion reads its own source with `readFileSync(fileURLToPath(import.meta.url))`
(line 629) and matches real imports on an `^` anchor
(`/^[ \t]*import\b[^\n]*?from\s*["']([^"']+)["']/gm`), against the closed set
`node:fs`, `node:path`, `node:url`, `vitest`, `../lib/contrast`, with
`toContain("../lib/contrast")`.

I probed all three failure modes:

1. **A sixth real import** (`import { tmpdir } from "node:os";`) fails:
   `AssertionError: expected [ 'node:os' ] to deeply equal []`.
2. **A dynamic import planted inside a `//` comment** fails:
   `FAIL … > reaches no module dynamically … AssertionError: expected true to be false`.
3. **A `require()` planted inside a `/* */` block comment** fails the same way.

Probes 2 and 3 are the decisive ones: comment-ness is **never consulted**, so
the assertion is not passing because of a comment exclusion. Nor is it passing
by concatenation or excision — the two needles are written as literal regexes
on lines 650–651 (`/await\s+import\s*\(/` and `/\brequire\s*\(/`) and the file
is scanned whole; they pass because a regex literal's own text (`\s+`, `\(`)
does not match the pattern it expresses. No path exclusion is involved — the
source read is `import.meta.url`, the file itself.

`frontend/src/lib/contrast.ts` and `backend/app/core/branding.py` are
unchanged: `git diff HEAD --stat --` on both paths is empty.

### R11 — `vitest.config.ts` unchanged; thresholds intact — PASS

`git diff HEAD -- frontend/vitest.config.ts` is empty. The pre-existing
`server.fs.allow: [".", "../backend/tests/data"]` (APRAS-68) is untouched and no
entry was added; `test.include` is still absent (unchanged). Thresholds remain
`lines: 80, functions: 78, branches: 76, statements: 80`. `npm run test:coverage`
in the worktree: `All files | 91.52 | 85.21 | 87.86 | 92.24` (stmts/branch/funcs/lines),
2543 tests passed, no threshold error.

### R12 — the guard is proven to fail, three ways, by the named mechanism — PASS

Run 1 — `docs/tasks/APRAS-90-mock.html:16` `#009f68` → `#00a166` (clip value).
Fails **the hex-claim scan**:
```
FAIL  src/__tests__/docsColourProvenance.test.ts > the colour claims published under docs/
      > re-derives every published hex from its oklch with contrast.ts
AssertionError: expected [ Array(1) ] to deeply equal []
+   "docs/tasks/APRAS-90-mock.html:16 publishes #00a166 as the paint of oklch(0.62 0.15 160), but contrast.ts derives #009f68",
      Tests  1 failed | 13 passed (14)
```

Run 2 — the marker at `contrast-provenance.md:89` set to the clip ratio
`3.3564`. Fails **the ratio re-derivation**:
```
FAIL  src/__tests__/docsColourProvenance.test.ts > the anchored markers
      > re-derives every anchored ratio marker, and fails rather than skipping a malformed one
AssertionError: expected [ Array(1) ] to deeply equal []
+   "docs/frontend/contrast-provenance.md:89 publishes oklch(0.62 0.15 160) on oklch(1 0 0) at 3.3564, but contrast.ts derives 3.4054",
      Tests  1 failed | 13 passed (14)
```

Run 3 — one inventory row's hex (`contrast-provenance.md:124`,
`--status-pending-fg`) set to `#00a166`. Fails **by set inequality against
`index.css`, naming the row**, and — as required — the hex-claim scan stays
**green**, because the table is guarded solely by the parse:
```
FAIL  src/__tests__/docsColourProvenance.test.ts > the out-of-gamut inventory
      > agrees exactly with src/index.css
AssertionError: expected { …(2) } to deeply equal { onlyInDocument: [], …(1) }
+   "onlyInDocument": [
+     ":root | --status-pending-fg | oklch(0.5 0.12 85) | #00a166",
+   ],
+   "onlyInStylesheet": [
+     ":root | --status-pending-fg | oklch(0.5 0.12 85) | #7e5d00",
+   ],
      Tests  1 failed | 13 passed (14)
```
Both halves verified: exactly one test failed, and it was the set-equality one —
not the claim scan, not the ratio check.

Every mutation was made on the scratchpad landing-tree export, restored, and
`cmp`-verified. Nothing was committed; the worktree was never edited.

### R13 — no exceptions JSON, no `index.css` change, zero document repairs — PASS

Staged tree is exactly three paths: `AGENTS.md`,
`docs/frontend/contrast-provenance.md`,
`frontend/src/__tests__/docsColourProvenance.test.ts`. No JSON file of any kind
is added. `git diff HEAD -- frontend/src/index.css` is empty — no value changed.
**Zero** lines of any existing `docs/tasks/` document were repaired (no
`docs/tasks/` path is staged or modified), against a budget of three and an
expectation of zero. The guard passes on the committed landing tree: 14/14.

### R14 — `AGENTS.md` sub-section — PASS

Added sub-section "### Colour figures: one source, one page" (9 inserted lines
including the blank separator; the sub-section proper is heading + blank + 6
prose lines = 8 lines, 7 of them non-blank). It names
`docs/frontend/contrast-provenance.md` as the **only permitted source** for a
hex or contrast ratio, names `frontend/src/lib/contrast.ts` as the only code
permitted to produce one, states the clip prohibition with the CSS Color 4 §13
reason, and points at the guard. Within the 8-line limit on the natural reading
(the extra inserted line is the blank separating it from the preceding section).

### R15 — test, build, lint — PASS

- `cd frontend && npm test` → **191 test files, 2543 tests, all passed.**
- `cd frontend && npm run build` (`tsc -b && vite build`) → **green**,
  `✓ 2295 modules transformed`, `✓ built in 436ms`. The only warning is the
  pre-existing chunk-size notice.
- `cd frontend && npm run lint` → **identical to baseline.** I measured the base
  by running the same lint over an export of `HEAD` with the new test file
  removed. Both runs: **370 errors, 2 warnings**, exit 0. The new file
  `docsColourProvenance.test.ts` itself contributes **0 errors, 0 warnings**.
  Lint is not worse than baseline; it is byte-for-byte the same tally.

---

## Blocking findings

None.

## Suggestions (non-blocking)

1. **`EXCLUDED_PATHS` is documentary, not operative.** The scan is allow-listed
   by directory (`docs/tasks`, `docs/frontend`), so `docs/reviews` and the other
   four entries can never be collected in the first place; the test
   `"scans no document that an exclusion rule names"` is therefore structurally
   vacuous — it cannot fail without a change to `SCANNED_DIRECTORIES`. That is
   the safe direction (the reviews are excluded twice over, and R4 is satisfied
   both by the named rule and by the behaviour), but a future author who widens
   the scan to `docs/` should know the exclusion list is what will start doing
   real work at that moment, and the vacuity means it is currently untested.

2. **`deriveStylesheetInventory` reads at most one declaration per line.** The
   `declaration` regex is non-global and `exec`s once per line, so two
   `--token: oklch(...)` declarations on one line would silently measure only
   the first. `index.css` has one per line today (all 58 `oklch()` lines parsed,
   `problems` empty), and a line with an `oklch()` that is *not* a readable
   declaration already fails loudly — so this is latent rather than live. A
   global match, or an assertion that no line carries two `oklch(`, would close
   it.

3. **`APRAS-76-spec.md:96` is now a guarded claim** (`oklch(0.62 0.14 160)` =
   `#019f68`, which `contrast.ts` does produce for chroma 0.14). Worth noting
   only because `#019f68` is also the `themeContrast.test.ts` grid artefact for
   chroma 0.15 named in the provenance document's exception section; the two
   are unrelated and both correct, but the collision of the same hex string in
   two different roles is a reader trap.

VERDICT: APPROVED
