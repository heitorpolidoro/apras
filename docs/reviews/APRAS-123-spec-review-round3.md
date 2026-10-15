# APRAS-123 — spec review, round 3 (findings-only)

VERDICT: NEEDS_REVISION

Spec reviewed: `/Users/heitor/workspace/apras/docs/tasks/APRAS-123-spec.md`
Working tree: `/Users/heitor/workspace/apras`, branch `master`, HEAD `2cb0d48`.
Mode: findings-only re-review of round 2's single blocking finding plus a
consistency pass over the sections changed to fix it (§4, §6, §7, §9, §10,
results 7/8/11/12).

Nothing under `frontend/` was modified. All scripts were written to the
session scratchpad
(`/private/tmp/claude-501/-Users-heitor-workspace-apras/06230b8a-d0ef-40dd-929b-83bb4eb6abbf/scratchpad/`)
and import `frontend/src/lib/contrast.ts` through `jiti` from the existing
`node_modules`; no install was run, nothing was staged or committed.

## 1. Round 2's blocking finding is resolved

The finding was that the provenance document's own 19 hexes were published
behind no check, because a Markdown row matches none of the three claim
shapes and the out-of-gamut assertion compared `index.css` against the
*test's* inline list.

Option 1 is now in the file and it genuinely closes the loop. §6 lines
285–303: the guard reads `docs/frontend/contrast-provenance.md`, parses every
row `| <block> | <token> | oklch(L C H) | #rrggbb |` with backticks and
padding stripped into `(block, token, oklch, hex)` tuples, derives the same
set from `index.css` via `isInGamut` + `oklchToHex`, and asserts **set
equality**, failing with the rows present on one side and absent on the other.
The anti-vacuity clause (`≥ 19` on both sides) rules out empty-equals-empty;
an unparsable cell is a failure naming the row, never a skip; the test is
asserted to carry no inline copy of the rows; and result 11 adds a third
proven-to-fail run that edits one table hex and must fail *by set inequality*.
The authority is `index.css`, the 19 is a floor on the parse — that is the
right direction, and §3 of "Out of Scope" records why the connector-form
alternative was rejected. The unguarded copy is not relocated: with set
equality against `index.css`, a stale row is red, not silent.

I verified the substance of the new table against the implementation, not just
the prose:

- 58 `oklch()` occurrences in `frontend/src/index.css`, **0** unparsable by
  `parseOklch`, **0** on a line without a `--token:` declaration — §6's
  closing paragraph holds exactly.
- `isInGamut` is false for exactly **19** declarations, **16 under `:root`,
  3 under `.dark`**, and the derived set is **byte-identical** to the spec's
  19-row table (set diff empty in both directions), tokens and hexes included.
- `--status-canceled-fg: oklch(0.5 0.15 20)` is **in** gamut (paints
  `#a8353e`) while `--status-blocked-fg: oklch(0.5 0.15 70)` is **out** — the
  asymmetry warning in §6 is correct, including the five-bg/four-fg count.
- The four ratio figures re-derive exactly: light `--ring` on `--card`
  **3.4054**, light `--ring` on `--destructive` **1.4117**, dark `--ring` on
  `--card` **6.4180**, dark `--ring` on `--destructive` **1.8021**
  (`contrastRatio(...).toFixed(4)`).
- `frontend/src/__tests__/themeContrast.test.ts` does reduce chroma on a
  `CHROMA_STEP = 0.01` grid (line 60, commented at 101 and 326), so the named
  exception in §6 describes a real second oracle.

## 2. Re-run of the generator's self-scan (priority 2)

I re-implemented the three shapes from §1 independently (shape A either order
on one line; shape B tuple; shape C across line breaks on text with HTML tags
and `` ` `` `*` `_` `|` stripped, oklch-first only, connector set
`=`/`==`/`→`/`->`/`≈`) and ran it twice.

**Working tree** (`docs/tasks/**/*.{md,html}` + `docs/frontend/**/*.md`):
141 documents, 11 contributing, **39 claims, 0 mismatches**.

**Committed tree at `2cb0d48`** (`git ls-tree`, contents via `git show`):
**125** documents — 98 `.md` (96 under `docs/tasks/`, 2 under
`docs/frontend/`) and 27 `.html` — **8** contributing, **17 claims, 0
mismatches**, with `docs/tasks/APRAS-90-mock.html` at 5 and
`docs/tasks/APRAS-76-mock.html` at 4. Every figure in §4 reproduces to the
digit, and every floor in §4 and result 5 holds on the committed tree.

**The spec file itself**: 8 claims, **0 mismatches**, **0 anchored markers**
(neither `contrast-guard: ignore` nor `ratio:` appears as the entire trimmed
content of any line in the scanned set). My count is 8 rather than the
generator's 4 because I also count §1's three shape examples (lines 50–52) and
§10's proven-to-fail line 433; all four derive correctly, so the difference is
in what each scan counts, not in correctness. The three new connector examples
at lines 310–312 (`oklch(0.62 0.15 160) → #009f68`,
`oklch(0.58 0.24 27) → #e60018`, `oklch(0.65 0.15 160) → #00aa6f`) and result
7's line 492 all derive correctly. The `≠` occurrences (lines 106, 278, 320)
produce no claim, and line 278's `oklch(0.62 0.15 160)` paints … and
`≠ #00a166` is kept out of shape C by the intervening prose as well as by the
connector set. The spec does **not** trip its own guard this round.

Also confirmed: the 19 table rows contribute **0** claims under all three
shapes, so §4's statement that they add nothing to the floors is correct, and
after landing the floors still hold (126 documents, 9 contributing, 20 claims
once the provenance document's three connector hexes enter).

## 3. Blocking findings

### B1 — §7's dynamic-import clause mandates the very self-scan §7 declares unworkable, and as written the assertion fails on a correct file

§7 (lines 344–350) rejects a literal self-scan in terms that are exactly
right: "An assertion that names its needles and reads its own source finds its
own needles and fails; every way out of that — needles built by concatenation,
excising the needle declaration before scanning — is an unspecified device two
implementers would choose differently."

Lines 362–372 then require precisely that: the implementer "also fails the
test if its own source contains `await import(` or `require(` outside a
comment". The assertion's needles must live in the file it scans, outside a
comment, so the straightforward implementation —
`expect(source).not.toContain("await import(")` — **fails on a correct
file**. One escape happens to be clean (a spacing-tolerant regex literal:
`/await\s+import\(/` and `/\brequire\s*\(/`, whose source text is not what it
matches), and the others are the concatenation and excision devices the same
section condemns. Which one an implementer picks is a coin flip, and one of
the outcomes is red CI on correct work — the exact failure class this task
exists to eliminate.

Two further defects in the same clause:

- **"outside a comment" is not implementable as stated by text scan.**
  Deciding comment-ness needs tokenisation: stripping `//` to end of line and
  `/* … */` blocks misfires on those sequences inside string literals and
  regex literals, which this file will contain by the dozen. Worse, the
  exemption is useless for the only occurrences that will actually exist —
  under the clean regex-literal implementation the needles are *not* in a
  comment, so the qualifier buys nothing and only invites a parser nobody
  specified.
- **No expected result covers it.** Result 10 (lines 531–540) requires only
  the import pin. An implementer who silently drops clause (a) passes QA while
  the spec text says they must not — a divergence between the two documents of
  the kind §6 was just revised to remove.

Fix, any one of: (i) specify the needle form that cannot match itself and say
so in one sentence, dropping "outside a comment" entirely, e.g. "matched by
`/await\s+import\s*\(/` and `/\brequire\s*\(/`, whose own source text these
patterns do not match, so no excision or concatenation device is needed"; or
(ii) demote clause (a) back to a stated residual hole, as the rest of §7
already does for multi-line imports, and delete the requirement; or
(iii) keep it and add it to result 10 so the gate matches the spec. Options
(i) and (iii) together are the strongest.

### B2 — result 8's "exists in exactly one place in the repository" is false of the landed tree, and the sentence naming the real check is garbled

Result 8 opens: "The out-of-gamut inventory exists in exactly **one** place in
the repository — the table in `docs/frontend/contrast-provenance.md`". §9
repeats it: `docs/frontend/contrast-provenance.md` — "the repository's single
copy of the inventory figure". Both are contradicted by §6 lines 245–263 of
this very spec, which hold a byte-identical copy of all 19 rows, and
`docs/tasks/APRAS-123-spec.md` is a committed file in the repository and in
the scanned set. A QA agent holding only the expected results and grepping
`--status-pending-bg` + `oklch(0.96 0.05 85)` finds two copies and marks the
result failed on correct work.

The next sentence, which carries the check that is actually mechanical, is
garbled to the point of naming the wrong subject: "`docs/tasks/APRAS-123-spec.md`
grep'd for the 19 rows finds no inline copy inside
`frontend/src/__tests__/docsColourProvenance.test.ts`." As written the grep
target is the spec; the intended subject is the test file.

This is a wording fix, not a design change — the design is right, and the
authority genuinely is `index.css` through the set equality. Scope the
uniqueness claim to what is true and checkable: the **only guarded and
authoritative** copy is the provenance document's table, the test file carries
no inline copy (grep the test file for any two of the 19 rows), and the copy
in this spec is a record of the measurement at authoring time, not a source.
§9's "single copy" phrasing needs the same narrowing.

## 4. Suggestions (non-blocking)

- **The `≠`-or-no-connector rule is load-bearing and lives only in this
  spec.** §2 line 104 and §6 lines 317–322 state it, but neither
  `docs/frontend/contrast-provenance.md`'s required content (§6, §9) nor the
  `AGENTS.md` sub-section is required to mention it. A future author writing
  `oklch(0.62 0.15 160) → #00a166` inside a document that *explains* the clip
  bug turns CI red on a correct document. I judge the trap acceptable rather
  than blocking: the failure is a **false red**, loud and self-describing
  (the message names file, line, published and derived hex), not a silent
  false green, and the documented line-anchored `contrast-guard: ignore`
  escape resolves it with a visible diff to the test's exact list. But the
  cost of closing it is one sentence in the provenance document, which is the
  page `AGENTS.md` sends every author to: "to quote a figure `contrast.ts`
  does not produce, write it with `≠`, or suppress the claim with an anchored
  `<!-- contrast-guard: ignore — <reason> -->` line, which also edits this
  guard's exact list." Worth adding.
- **The other figures in the provenance document are accounted for, and §6's
  audit of them is accurate.** The four ratios are covered by §5's anchored
  marker check (I re-derived all four); the three loose hexes are covered by
  shape C in connector form (I derived all three); the convention paragraph,
  the asymmetry explanation and the coincidence explanation are declared prose
  and genuinely contain no mechanical claim. Nothing else in the document
  carries a figure. No gap here.
- Results 11/12 and §8 reconcile cleanly. Result 12's cap is explicitly on
  *committed* edits to an existing `docs/tasks/` document; result 11's three
  edits are temporary and restored, and §8 line 401 says so parenthetically.
  The third proven-to-fail run is genuinely distinct: it exercises the set
  equality against `index.css`, a different assertion from the claim scan
  (run 1) and the ratio marker (run 2), and because a table row carries no
  connector it cannot be caught by shape C — so the run proves the parse path
  specifically. Note that the edited file there is the new provenance
  document, not another task's document, so it does not touch result 12's cap
  at all.
- §4's floors sit exactly at the committed measurement for three of the four
  items, which the spec acknowledges; since the implementer is told to
  re-measure at landing, consider stating the post-landing expectation
  explicitly (126 read, 9 contributing, 20 claims) so a re-measurement that
  comes out *below* it is visibly wrong rather than merely a lower floor.
