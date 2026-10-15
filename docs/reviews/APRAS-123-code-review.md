# APRAS-123 — Code review

Reviewed: `git -C /Users/heitor/workspace/apras/.claude/worktrees/agent-a0c62ad5b030903eb diff --cached`
Base: `2124432`. Diff size: **3 files, 826 insertions, 0 deletions** —
`AGENTS.md` (+9), `docs/frontend/contrast-provenance.md` (+164, new),
`frontend/src/__tests__/docsColourProvenance.test.ts` (+653, new).
Nothing else is staged. The worktree's working tree carries only two untracked
files, `docs/tasks/APRAS-123-spec.md` and `docs/reviews/APRAS-123-implementation.md`.

Every number below was produced by executing code in this worktree, not by
reading the spec or the developer's report. All mutations were restored and
verified byte-identical with `shasum -a 256 -c`; the index was never touched.

---

## 1. The four canonical values, derived by execution

I wrote a throwaway node-environment probe that imports `contrast.ts` directly
and calls `parseOklch` / `oklchToHex` / `contrastRatio` / `isInGamut`, taking the
`--card` and `--destructive` operands out of `frontend/src/index.css` rather than
from any document. Probe deleted afterwards.

```
light ring/primary: oklch(0.62 0.15 160) -> #009f68  inGamut=false
light destructive:  oklch(0.58 0.24 27)  -> #e60018  inGamut=false
dark ring:          oklch(0.65 0.15 160) -> #00aa6f  inGamut=false
ratio light ring on card:        3.4054
ratio light ring on destructive: 1.4117
ratio dark ring on card:         6.4180
ratio dark ring on destructive:  1.8021
```

`#009f68`, `#e60018`, 3.4054, 1.4117, 6.4180, 1.8021 — all six confirmed
independently. The provenance document and `AGENTS.md` publish exactly these,
and nothing else as a derived figure.

## 2. The guard runs green, and the counts are re-derived

`npx vitest run src/__tests__/docsColourProvenance.test.ts` → **14 passed**.

To re-derive the internal counts without touching the staged file I copied it to
a temporary `zzMeasure.test.ts`, appended one reporting assertion, ran it, and
deleted the copy. Measured with the untracked spec present, then with the spec
temporarily moved to the scratchpad (committed-tree equivalent) and moved back
with its checksum verified:

| measurement | spec present | spec absent (= committed tree) | floor asserted |
|---|---|---|---|
| documents read | 127 | **126** | ≥ 100 |
| contributing documents | 10 | **9** | ≥ 8 |
| claims checked | 28 | **20** | ≥ 17 |
| anchored ratio markers | 4 | **4** | ≥ 4 |
| sentinel `oklch(0.62 0.15 160)`/`#009f68` hits | 9 | **4** | ≥ 2 |
| anchored ignore markers | 0 | **0** | exact `[]` |
| inventory rows, document side | 19 | **19** | ≥ 19 |
| inventory rows, `index.css` side | 19 | **19** | ≥ 19 |
| `docs/tasks/APRAS-90-mock.html` claims | 5 | **5** | ≥ 5 |
| `docs/tasks/APRAS-76-mock.html` claims | 4 | **4** | ≥ 4 |

Both states are fully green. The developer's reported 126 / 9 / 20 / 4 markers /
4 sentinel hits / 19-and-19 against the committed tree, and 127 / 10 / 28 with
the spec present, are **exact**. R5 holds against the committed tree, not merely
against a working tree padded with untracked drafts.

Claim distribution on the committed-equivalent tree: `APRAS-90-mock.html` 5,
`APRAS-76-mock.html` 4, `contrast-provenance.md` 3, `APRAS-87-mock.html` 2,
`APRAS-87-spec.md` 2, and one each in `APRAS-68-mock.html`, `APRAS-68-spec.md`,
`APRAS-76-spec.md`, `APRAS-88-spec.md`.

## 3. Five mutations, each reproduced and each failing by the claimed mechanism

### 3.1 `docs/tasks/APRAS-90-mock.html:16`, `#009f68` → `#00a166`

```
FAIL  the colour claims published under docs/ > re-derives every published hex from its oklch with contrast.ts
+   "docs/tasks/APRAS-90-mock.html:16 publishes #00a166 as the paint of oklch(0.62 0.15 160), but contrast.ts derives #009f68"
```

Names the file, the **1-based** line (16, which is where the declaration sits),
the published hex and the derived hex. 1 failed / 13 passed.

### 3.2 A ratio marker set to the clip value, `3.4054` → `3.3564`

```
FAIL  the anchored markers > re-derives every anchored ratio marker, and fails rather than skipping a malformed one
+   "docs/frontend/contrast-provenance.md:89 publishes oklch(0.62 0.15 160) on oklch(1 0 0) at 3.3564, but contrast.ts derives 3.4054"
```

The comparison in source is `contrastRatio(...).toFixed(4) === body[3]`, with
`body[3]` matched by `-?\d+\.\d{4}` — four-decimal string equality, not
`toBeCloseTo`. Failure is by that mechanism.

### 3.3 One inventory hex, `:root`/`--primary` → `#00a166` — both halves verified

```
FAIL  the out-of-gamut inventory > agrees exactly with src/index.css
+   "onlyInDocument":   [":root | --primary | oklch(0.62 0.15 160) | #00a166"]
+   "onlyInStylesheet": [":root | --primary | oklch(0.62 0.15 160) | #009f68"]
```

**1 failed / 13 passed.** The failure is by set inequality against `index.css`
and names the row on both sides. The hex-claim scan stayed **green**, confirming
the developer's precise claim: a Markdown row carries no connector, so shape C
does not see it and the table is guarded solely by the parse. Both halves of
that claim hold.

### 3.4 The import pin (R10) — three separate probes

- A fourth static import (`import { existsSync } from "node:os";`) →
  `FAIL … imports nothing outside the closed set` / `expected [ 'node:os' ] to deeply equal []`.
- `// const extra = await import("colorjs.io");` written **inside a comment** →
  `FAIL … reaches no module dynamically`. Comment-ness is genuinely never
  consulted.
- `const legacy = require("node:fs");` → same assertion fires.

### 3.5 The anchored ignore list (R9)

Inserting `<!-- contrast-guard: ignore — review probe -->` alone on a line at
`docs/tasks/APRAS-90-mock.html:16`:

```
FAIL  the anchored markers > suppresses nothing, and says so by exact list
+   "docs/tasks/APRAS-90-mock.html:16"
FAIL  the positive control > finds the named sentinels, all of them committed
```

Caught **twice** — by the exact-list assertion and by the `APRAS-90-mock.html ≥ 5`
sentinel, because suppressing a claim drops that file from 5 to 4. That is the
payoff of leaving the named sentinels sitting exactly at the measurement, and it
is directly relevant to escalation 1 below.

Restoration after every cycle:

```
docs/tasks/APRAS-90-mock.html: OK
docs/frontend/contrast-provenance.md: OK
frontend/src/__tests__/docsColourProvenance.test.ts: OK
```

`git status --short` after all five is byte-for-byte the state I started in, and
`git diff --cached --stat` is unchanged at 3 files / 826 insertions.

## 4. The self-reference attacks — where the previous four rounds died

### R10: does the file pass for the stated reason?

The two patterns are written as bare regex literals, verbatim, at lines 650–651:

```
650:    expect(/await\s+import\s*\(/.test(source)).toBe(false);
651:    expect(/\brequire\s*\(/.test(source)).toBe(false);
```

- **No concatenation device.** The literals are whole; there is no string
  building anywhere near them.
- **No excision.** `source` is `readFileSync(fileURLToPath(import.meta.url), "utf8")`
  — the entire file, unmodified, with no slicing and no line filtering.
- **No comment exclusion.** Proven by probe 3.4: a dynamic import written inside
  a `//` comment fails the assertion. If a comment exclusion existed, it would
  have passed.
- **No path exclusion.** There is only one path read, its own.

So the file passes because `\s+` and `\(` do not match themselves — the spec's
argument, and it holds mechanically rather than by construction trick. This is
the first round where the self-referential instrument is genuinely
self-consistent.

### R8: the sentinel exemption

I parsed all 19 rows out of the provenance document and searched the test source
for each row's `oklch()` and each row's hex independently:

```
rows parsed: 19
HIT :root --primary: oklch_in_test=True hex_in_test=True  (oklch(0.62 0.15 160) / #009f68)
HIT :root --ring:    oklch_in_test=True hex_in_test=True  (oklch(0.62 0.15 160) / #009f68)
```

Those two hits are the **same pair** — the one pair the spec exempts because
`:root`/`--primary` and `:root`/`--ring` both carry it and the sentinel
assertion must hold it literally. No other row's `oklch()` and no other row's
hex occurs anywhere in the test file. Exhaustively, the only colour literals in
the 653-line test are:

```
oklch literals: oklch(0.56 0.13 160.15), oklch(0.62 0.15 160), oklch(0.68 0.14 237.32)
hex literals:   #008a5a, #009f68, #0ea5e9
```

`oklch(0.56 0.13 160.15)`/`#008a5a` and `#0ea5e9` are the APRAS-68
negative-control references, and notably `#0ea5e9` appears only in a
`.not.toBe()` and `oklch(0.68 0.14 237.32)` only as the *input* being located —
the test nowhere asserts a derived hex against a hard-coded expectation. There
is no inline oracle. R8 is satisfied under the strict reading (one hit on any
other row would be a failure; there are none).

### R9: the anchored lists

Every occurrence of either marker in the scanned set:

```
docs/tasks/APRAS-123-spec.md:110,115,326,556   — all inside backticks, prose beside
docs/frontend/contrast-provenance.md:36        — inside backticks, prose beside
docs/tasks/APRAS-123-spec.md:128,204,505       — ratio template, backticked
docs/frontend/contrast-provenance.md:45        — ratio template, backticked
docs/frontend/contrast-provenance.md:89,93,97,101 — the four real markers
```

A grep for lines whose entire trimmed content is the anchored ignore marker
returns nothing across `docs/tasks/` and `docs/frontend/`. Detection runs on the
raw trimmed line (`extractMarkers`), so a leading backtick defeats the `^<!--`
anchor: the documented occurrences, including the spec's own §2 and the
provenance document's template, are genuinely not counted. Measured ignore
markers: **0**, matching the exact empty list. Measured ratio markers: **4**, so
the four backticked templates are excluded and the four real ones are not.

### R5: floors against the committed tree

Verified in §2 by removing the one untracked document from the scanned set. The
`≥ 100` / `≥ 8` / `≥ 17` aggregates and all four tight floors hold at 126 / 9 /
20. No floor depends on an untracked file.

## 5. The negative controls and the inventory derivation

- `docs/tasks/APRAS-68-spec.md:235` (hex-first), `:477` and
  `docs/tasks/APRAS-92-spec.md:717` are asserted absent from the claim set, and
  are absent. Shape C has no hex-first alternative at all — the exclusion is
  structural, not a special case.
- `docs/tasks/APRAS-68-mock.html:93` is found as exactly one claim on
  `oklch(0.68 0.14 237.32)`, and asserted not to compare against the brand input
  `#0ea5e9`.
- `index.css` carries **58** `oklch(` occurrences, all 58 on a line that also
  carries a `--token:` declaration — I checked for any occurrence outside one and
  found none, so the line-anchored per-declaration derivation is honest. Block
  openers are `@theme`, `:root`, `.dark`, `*`, `body`, `#root`, `*::after`; only
  `:root` and `.dark` contribute, which is why the document's two block labels
  are correct. `problems` is empty on both sides, so no occurrence and no row is
  silently skipped.
- `≠` discipline in the provenance document: `#00a166`, `#e60016` and `#019f68`
  are each written with `≠`; the clip ratios 3.3564 / 1.4252 / 6.4408 / 1.8085
  and the grid artefact 3.4078 sit in bare prose outside any connector and any
  marker. Empirically the document contributes exactly **3** claims — its three
  intended connector hexes and nothing else — so the page explaining the wrong
  values does not fail its own guard.

## 6. Scope and configuration checks

| check | result |
|---|---|
| `frontend/vitest.config.ts` | unchanged vs `HEAD`. Its `fs.allow: [".", "../backend/tests/data"]` and `coverage.include: ["src/**/*"]` are pre-existing; no `test.include` exists |
| `frontend/src/lib/contrast.ts` | unchanged vs `HEAD` |
| `backend/app/core/branding.py` | unchanged vs `HEAD` |
| `frontend/src/index.css` | unchanged vs `HEAD` — no value altered |
| new exceptions JSON | none. The two JSONs under `__tests__/` are pre-existing and not staged |
| committed repairs to other tasks' documents | none (0 mismatches, as predicted) |
| `AGENTS.md` sub-section | heading + blank + 6 prose lines = 8 lines, plus the blank separating it from `## Infrastructure`. Within the ≤ 8 limit |
| conversion arithmetic in the guard | none. No `0.2126` / `0.7152` / `0.0722` / `12.92` / `1.055` / `0.04045` / `0.0031308` / `Math.cbrt` / `** (1/2.4)`. The only decimals in the file are the three oklch literals above |
| imports | five, all single-line, all inside the closed set, `../lib/contrast` present |

## 7. Suite, build, lint

- `npm test` → **191 files / 2543 tests passed**. Matches the report.
- `npm run build` (`tsc -b && vite build`) → green, exit 0. The new file
  typechecks under `tsc -b`, so the `node:` references and
  `/// <reference types="node" />` are sound.
- Lint. I measured with the JSON formatter to get exact totals rather than
  parsing the human summary:

  ```
  cd <worktree>/frontend && npx eslint . -f json
  → 370 errors / 2 warnings / 66 files with problems   (463 files linted → 464 with the new file)
  ```

  **I confirm 370 / 2 / 66, and the new guard file contributes zero problems of
  its own** — it is present in the lint run and absent from the problem list, so
  base and post-change totals are identical. The spec's remembered "~375 across
  64" is wrong and the developer is right to correct it. On the **377/2/66**
  figure reported earlier in the week: I cannot reproduce 377 here with the
  invocation above on base `2124432`. The likely difference is invocation, not
  tree — `npm run lint` is bare `eslint .`, so the count depends on the cwd and
  on what untracked lintable files exist in the checkout at the time; the main
  checkout holds untracked files that this worktree does not. I would treat
  370/2/66 from `npx eslint . -f json` inside the worktree's `frontend/` as the
  authoritative figure for this branch and note that any future baseline should
  record the exact invocation alongside the number.

## 8. The three escalations

### 8.1 Not raising the aggregate positive-control floors — **agree**

The developer's reasoning is sound and my mutation 3.5 is the evidence for it.
The floors that actually provide sensitivity are the four tight ones
(`APRAS-90 ≥ 5`, `APRAS-76 ≥ 4`, `ratios ≥ 4`, `rows ≥ 19`) plus the exact empty
ignore list, and all five sit exactly at the measurement. When I suppressed a
single claim, the `APRAS-90 ≥ 5` sentinel fired alongside the ignore list — the
aggregate floors would not have noticed, and raising them to 126/9/20 would not
have made them notice a one-claim loss either.

The aggregates guard a different failure: a scan that collapses (wrong root,
wrong extension list, an exclusion that swallows the tree). That failure takes
the count to 0 or near it, not from 126 to 119, so 100/8/17 catches it exactly as
reliably as 126/9/20 would. Meanwhile a tight aggregate is actively fragile in
*this* `docs/` tree, which many agents write concurrently and which legitimately
loses documents: a `≥ 126` floor converts an ordinary docs prune into a red CI
run with a misleading message. Do not raise them.

One real gap the aggregates do leave, which I have put in Suggestions rather than
blocking on: the provenance document's three connector hexes are worth exactly
3 claims and the claim floor has 3 of slack, so losing all three would still
pass. The figures themselves cannot drift unnoticed — five inventory rows carry
the same values under set equality — so only the connector-form demonstration
could be silently lost. Cheap to close with one more named sentinel.

### 8.2 The R8 sentinel improvement — **my recommendation: decline it, keep the literal**

Keep `SENTINEL_OKLCH` / `SENTINEL_HEX` as literals. Deriving them from the
`:root`/`--primary` row the guard already parses would be the wrong trade, and
the decisive reason is not the one the developer gave.

**The tradeoff.** Deriving buys: the literal disappears, R8's exemption
disappears with it, and the checkable grep form in the spec becomes "no
inventory pair appears at all" instead of "exactly one, and it is this one". The
cost is independence. A positive control exists to prove the scan found a real,
known claim; if its expected value is computed from the table parse, then the
control becomes a function of the artefact it is controlling. Edit the document
so `:root`/`--primary` carries a different pair and the sentinel assertion
silently re-targets to the new pair and keeps passing — the assertion can no
longer tell you that the scan found *the claim you meant*, only that it found
whatever the document currently says. That is precisely the failure class this
task exists to kill, and the one that killed all four earlier spec rounds: an
instrument whose expectation is drawn from the text it is examining. The
set-equality assertion would still catch a document/stylesheet divergence, but
the positive control would have stopped being a second, independent witness.

Against that, the cost of keeping the literal is small and fully visible: two
named constants, a documented exemption, and a grep form I verified mechanically
in §4 in a few seconds. The literal also demonstrably earns its keep — under
mutation 3.5 it was the second assertion to fire, and under mutation 3.1 its
count fell 4 → 3 while correctly still passing, behaviour that is easy to reason
about precisely because the expected value is fixed.

The developer's own arguments (coupling, degraded failure message) point the same
way but are secondary. The operator should decline the improvement on
independence grounds.

### 8.3 Leaving `docs/tasks/APRAS-123-spec.md` unstaged — **right, and verified harmless**

Verified both arms directly. With the spec present: 127 documents / 10
contributing / 28 claims, 14/14 green, no floor change needed. With it absent:
126 / 9 / 20, 14/14 green. The count shift is +1 document, +1 contributing
document and +8 claims, and it is fully understood: the spec writes eight
connector-form claims, all of which are correct values and all of which pass;
its §6 inventory table carries no connectors and so contributes nothing; and its
marker documentation is backticked and so is not counted. Nothing in the guard is
contingent on the file's presence, because every assertion against it is a floor
or an exact-empty list, and neither flips.

Leaving it unstaged is right: it matches APRAS-97/98/111, and a spec is not part
of the deliverable. If the operator later commits it, nothing breaks — it simply
becomes one more guarded document, which is the desirable direction.

---

## Suggestions

1. **Name the provenance document as a third sentinel.** The claim floor is
   `≥ 17` and the measurement is 20, with the provenance document contributing
   exactly 3. All three of its connector-form hexes could be de-connectored or
   deleted and the aggregate floor would still pass, quietly removing the only
   mechanical check that the authoritative page's three published hexes are
   written in guarded form. One line in
   `it("finds the named sentinels…")` —
   `expect(inFile("docs/frontend/contrast-provenance.md")).toBeGreaterThanOrEqual(3)` —
   closes it by exact analogy with the two existing named sentinels, at no
   fragility cost. (The figures themselves are still protected by the inventory
   set equality, which is why this is a suggestion and not a finding.)
2. **`it("scans no document that an exclusion rule names")` is a tautology
   today.** `SCANNED_DIRECTORIES` is an allowlist of `docs/tasks` and
   `docs/frontend`, and none of the five `EXCLUDED_PATHS` lives under either, so
   the assertion cannot fail as currently configured. It is not pointless — it
   is a tripwire that becomes meaningful the moment someone broadens the scanned
   set to `docs/` — but after APRAS-111's audit of tests that prove nothing, the
   comment above it should say that explicitly, so the next reader does not
   mistake it for live protection of the review-document exclusion. The
   exclusion of `docs/reviews/**` is in fact achieved structurally by the
   allowlist.
3. **`flatten` strips `_` and `*` and collapses `<…>` spans, which can only hide
   a claim, never invent one.** Worth one sentence in the `flatten` doc comment:
   a prose `<` … `>` pair (an inequality, a placeholder) swallows the text
   between them, so a legitimate claim written inside such a span would go
   unguarded. False-negative direction only, so it is a documentation gap rather
   than a defect.
4. **`AGENTS.md` slightly over-claims scope.** It says the provenance page is
   the only permitted source "for a hex or a contrast ratio quoted anywhere in
   this repository", while the guard reaches only `docs/tasks/` and
   `docs/frontend/`, and the page itself names `themeContrast.test.ts` as a
   standing exception and `backend/tests/test_branding.py` holds figures of its
   own. The sentence would be truer as "anywhere in this repository's
   documentation", leaving the mechanical reach to the sentence that follows it.

---

VERDICT: APPROVED

Blocking findings: None.
