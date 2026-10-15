# APRAS-123 — spec review, round 4 (findings-only re-review)

VERDICT: NEEDS_REVISION

Spec reviewed: `/Users/heitor/workspace/apras/docs/tasks/APRAS-123-spec.md` (working tree, untracked, at local HEAD `2cb0d48`).

Mode: findings-only. Round 3's two blocking findings were re-checked, plus the four
items the dispatch asked to be judged. No full re-application of the review
checklist against untouched sections.

## Status of round 3's two blocking findings

**Finding 1 (§7's dynamic-import clause) — resolved.** `grep -n 'outside a comment'`
returns nothing. §7 lines 374–391 now state the clause as two regex *literals*,
`/await\s+import\s*\(/` and `/\brequire\s*\(/`, with the escape made explicit:
a regex literal's own source text is not what the pattern matches. I re-verified
this independently rather than taking it on trust — in node, with
`src = String.raw`const A = /await\s+import\s*\(/; const B = /\brequire\s*\(/;``,
both `A.test(src)` and `B.test(src)` are `false`, because the source carries `\s+`
and `\(` where the pattern requires whitespace and a literal paren. So the
assertion can be written literally, read its own source, and pass on a correct
file, with no excision, no concatenation and no notion of comment-ness. The clause
is also now covered by an expected result (result 10), closing the "an implementer
who drops it still passes QA" half of the finding.

**Finding 2 (result 8's "exactly one place") — partly resolved, and the replacement
is still false of correct work.** The false claim about the landed tree is gone:
result 8 now says "the **only guarded and authoritative** copy", names
`frontend/src/__tests__/docsColourProvenance.test.ts` as the grep target (the
previously garbled sentence named the spec), and adds the parenthetical exempting
§6's table as "a record of the measurement at authoring time, not a source and not
guarded". But the rewritten checkable form contradicts result 5 — see the blocking
finding below. The fix relocated the "fails on correct work" property from the
spec's table to the test file; it did not remove it.

## Blocking Findings

- **Result 8's checkable form contradicts result 5's named sentinel: a correct
  test file contains one of the 19 rows' `oklch()`/`#rrggbb` pairs by
  requirement, so "finds **none**" fails on correct work — and "any two" is
  ambiguous about whether one hit is a failure.** Result 8 reads "grepping
  `frontend/src/__tests__/docsColourProvenance.test.ts` for any two of the 19
  rows' `oklch()`/`#rrggbb` pairs finds **none** — the test holds no inline copy."
  Result 5 (and §4's sentinel list) requires the test to assert "the pair
  `oklch(0.62 0.15 160)`/`#009f68` found at least twice" across the scanned set.
  To count occurrences of that pair the test must hold it literally, and that pair
  *is* row `:root | --primary` (and row `:root | --ring`) of the 19. So the grep a
  QA agent runs finds one of the 19 rows' pairs in the test file. Under the natural
  reading of the sentence ("for any two chosen, none is found") that is a failure
  on a correct implementation; under the looser reading ("no two of them") it
  passes, and the result does not say which. Two QA agents holding only this list
  decide differently, which is exactly what this result may not do, since it is
  the only mechanical handle on "the document is the only copy". The fix is one
  clause: exempt the sentinel by name — e.g. "finds no row's pair other than the
  single sentinel pair `oklch(0.62 0.15 160)`/`#009f68` that result 5 requires".

Everything else I was asked to judge came out clean; the detail is below so the
next round does not re-derive it.

## What I verified, item by item

### 1. Result 8's exemption, and whether the grep is well defined

Coherent as now written, with one blocking defect (above) and one non-blocking gap.

- The "guarded and authoritative" vs. "identical but expected" split is
  applicable: the grep target is the *test file*, so the markdown pipes and
  backticks of §6 and of the provenance table never enter the grep. The
  pipe/backtick concern the dispatch raised does not apply to the check as
  written — it would have applied to the round-3 wording that grepped the spec.
- Where QA obtains the 19 pairs is unstated: result 8 lists the 19 rows by token
  name only, and the values live in `docs/frontend/contrast-provenance.md`
  (required to exist by result 7). Workable, but a non-blocking imprecision — see
  Suggestions.
- Can §6's table drift from the provenance document with nothing failing? Yes, and
  it does not matter. §6 line 290 already says "The document's table is the
  authority, and the test parses it out of the document", and result 8 now says the
  spec's copy is unguarded. A landed spec is a historical record; the guard forces
  only the authoritative copy to track `index.css`. No finding.

### 2. The dynamic-import clause, and result 10's load

Complete enough to be non-blocking, with one real residual hole.

- `import("x")` without `await` (`const m = import("colorjs.io").then(…)`) is
  **not** caught: measured, `/await\s+import\s*\(/.test('const m = import("colorjs.io").then(f)')`
  is `false`. Non-blocking: §7 already frames the pin's residual holes as stated
  rather than closed, and the fallback argument ("inline arithmetic has no imports
  to hide behind and is what code review looks for") still holds. A one-token fix
  exists and is self-safe — see Suggestions.
- `createRequire` is already blocked, and not by these regexes: `import { createRequire } from "node:module"`
  yields the specifier `node:module`, which is not in the closed set
  `node:fs`/`node:path`/`node:url`/`vitest`/`../lib/contrast`, so the pin rejects
  it. Worth noting only because the dispatch asked.
- An `import()` split across lines is caught: the assertion reads the whole source
  as one string and `\s+` matches a newline, so `await\n  import(` matches.
- Result 10 does carry four distinct claims (import pin, dynamic-import regexes,
  two files unchanged, the conditional APRAS-100 interaction). Each is
  individually mechanically checkable, so this is a granularity suggestion, not a
  blocking finding.

### 3. Re-run of the scannable-claim check over the revised spec — clean

I implemented the three claim shapes and both anchored-marker rules as §1/§2
define them, loaded the real `frontend/src/lib/contrast.ts` (via `jiti`, read-only;
nothing under `frontend/` was modified and no script was left in the repository),
and ran them over the revised spec and over the whole committed scanned set.

Revised `docs/tasks/APRAS-123-spec.md`: **8 claims, 0 mismatches, 0 anchored
markers of either kind.**

| shape | line | oklch | published | derived |
|---|---|---|---|---|
| A | 50 | `oklch(0.62 0.15 160)` | `#009f68` | `#009f68` |
| A | 51 | `oklch(0.62 0.15 160)` | `#009f68` | `#009f68` |
| B | 52 | `oklch(0.53 0.02 160)` | `#627068` | `#627068` |
| C | 315 | `oklch(0.62 0.15 160)` | `#009f68` | `#009f68` |
| C | 316 | `oklch(0.58 0.24 27)` | `#e60018` | `#e60018` |
| C | 317 | `oklch(0.65 0.15 160)` | `#00aa6f` | `#00aa6f` |
| A | 452 | `oklch(0.62 0.15 160)` | `#009f68` | `#009f68` |
| C | 511 | `oklch(0.62 0.15 160)` | `#009f68` | `#009f68` |

The 19 inventory rows at lines 249–267 produce **no** claim under any shape, as
§4 asserts — a pipe-and-backtick row carries no connector, no `--token:`
declaration and no tuple quoting. The `≠` forms (lines 106, 282, 333) are inert.
No line's trimmed raw content is an anchored `contrast-guard: ignore` or `ratio:`
marker; every occurrence sits inside backticks and prose, including the wrapped
template at lines 128–130. So the spec does **not** ship a document its own guard
would flag.

Committed scanned set at `2cb0d48`, same scanner: **125 documents** (98 `.md`,
27 `.html`), **8 contributing**, **17 claims**, **0 mismatches**;
`docs/tasks/APRAS-90-mock.html` 5 claims, `docs/tasks/APRAS-76-mock.html` 4, the
pair `oklch(0.62 0.15 160)`/`#009f68` 3 times. Every §4 floor and every result-5
figure is confirmed against the committed tree, including the hex-first and
no-claim cases (`APRAS-68-spec.md:235`, `:477`, `APRAS-92-spec.md:717` yield
nothing).

The one arithmetic surprise is in the *post-landing* expectation, not in the
floors — see Suggestions.

### 4. Final pass

Nothing else blocking. §4's committed figures, §8's 0-mismatch claim and §5's four
ratio operand pairs (`isInGamut` false for all three `--ring`/`--primary`/
`--destructive` values, as §6 claims) hold. Language is English throughout.
Scope is one test file, one document and an `AGENTS.md` sub-section — PR-sized.

## Suggestions

- **§4's post-landing expectation undercounts by this spec's own 8 claims.** §4
  says "Expected post-landing measurement, for comparison: 126 documents read, 9
  contributing, 20 claims", reasoning only from
  `docs/frontend/contrast-provenance.md` entering the scanned set. But §9 lands
  `docs/tasks/APRAS-123-spec.md` too, and that file contributes 8 claims (table
  above). The expectation should read **127 documents, 10 contributing, 28
  claims** (17 committed + 3 from the provenance document + 8 from this spec).
  Non-blocking because no expected result asserts it, the floors (≥ 100 / ≥ 8 /
  ≥ 17) all still hold, and the spec tells the implementer to re-measure rather
  than copy. Worth fixing anyway: an implementer who measures 28 against an
  expected 20 has no guidance for a surplus and may go looking for a shape-C
  over-match that is not there.
- **Name where QA reads the 19 pairs from.** Result 8 lists the rows by token
  name; the `oklch()`/hex values live in `docs/frontend/contrast-provenance.md`.
  One clause ("read from the provenance document's table") makes the grep
  self-contained for an agent holding only the results.
- **Close the non-awaited dynamic import.** Replacing `/await\s+import\s*\(/`
  with `/import\s*\(/` catches `import("colorjs.io").then(…)` as well as the
  awaited form, and I verified it is still self-safe: `/import\s*\(/` does not
  match its own source text `import\s*\(` (the character after `import` is `\`,
  neither whitespace nor `(`), and it does not match `import.meta.url`, which §3
  requires the file to carry. If kept as-is, say in §7 that the non-awaited form
  is a third stated hole, so the list of admitted holes is complete.
- **Split result 10.** It covers the import pin, the two dynamic-import regexes,
  two files being unchanged, and a conditional interaction with APRAS-100's
  guard. Three results would each be verifiable on its own and would make a
  partial implementation visible.
