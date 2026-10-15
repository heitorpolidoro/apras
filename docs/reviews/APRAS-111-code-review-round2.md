# APRAS-111 — code review, round 2

VERDICT: APPROVED

Reviewed: `docs/audits/APRAS-111-test-suite-audit.md`, the single staged path.
Staged diff: 5551 insertions (new file). Revision diff against the developer's
retained pre-edit copy `<scratchpad>/rev/audit.before-filecol.md`: 5407 → 5551
lines, 201 removed / 345 added across 105 hunks.

Round 1's single blocking finding is discharged. Nothing new blocks.

---

## 1. Is the re-derivation complete and self-consistent?

Yes, and mechanically so. I did not take the developer's validation script on
trust; I wrote my own (`<scratchpad>/rev/verify2.py`) and ran it against both the
staged document and the retained pre-edit copy.

**Method.** Linear scan of the document. Each
`- **Order-pinned command**` line yields the row's
`--outputFile=<scratchpad>/runs/<id>.json`. Each
`- **Step-3 mutated run**` summary is then compared against that JSON; each
`- **Step-0 baseline**` summary is compared against
`<scratchpad>/runs/base-<B-NN>.json`, resolved from the `B-NN` the line itself
names. The comparison is on all four figures at once:
`(numTotalTests, numPassedTests, numFailedTests, len(testResults))`.

**Result.**

```
checked: 186   ok: 186   bad: 0
```

186 is the whole frontend population and it reconciles three ways:
`grep -c '^- \*\*Step-0 baseline\*\*.*(files '` = 93,
`grep -c '^- \*\*Step-3 mutated run\*\*.*(files '` = 93, 93 + 93 = 186; and
`ls <scratchpad>/runs/*.json` = 144 = 93 mutated-run artefacts + 50 `base-B-NN`
artefacts + 1 ad-hoc. The document contains 190 `(files N)` strings in total; the
other four are the three new invalidation banners and the F-13 prose sentence, all
quotations of a row rather than rows themselves. So no frontend run summary
escaped the check, and the row-to-artefact mapping is proved by the case figures
matching, not assumed.

**The claimed cause is the actual cause.** I re-ran the identical script against
the pre-edit copy with `len(testResults)` swapped for `numTotalTestSuites`:

```
checked: 186   ok: 186   bad: 0
```

All 186 old values were describe-block counts; all 186 new values are file counts.
One mechanical cause, uniformly applied, no residue. Counting the delta directly:

```
case figures changed:  0
file figures changed:  183    unchanged: 3
```

That is exactly the developer's account — 183 moved, 3 were already right, and no
case figure was disturbed. The three unchanged are the step-3 lines of `S4-FE-04`,
`-08` and `-10`, whose invalid-file runs collected one file and zero cases, so
`numTotalTestSuites == len(testResults) == 1`. The developer's claim that these are
the three already-correct figures is therefore not a convenient assertion; it is
forced by the artefacts.

**Independent re-execution.** I re-ran seven specs with plain
`npx vitest run` (no JSON reporter), sampling all four strata, including the kind
of single-spec row that previously said `files 2` for one file, and a spec whose
row figure was already correct:

| spec | stratum / row | ledger | observed |
|---|---|---|---|
| `src/lib/__tests__/contrast.test.ts` | S1 `MINIMUM_CONTRAST_RATIO-*` (was `files 11`) | files 1, 36 | `Test Files 1 passed (1)` / `Tests 36 passed (36)` |
| `src/__tests__/themeTokenMigration.test.ts` | S2 `S2-FE-01` (was `files 15`) | files 1, 179 | `1 passed (1)` / `179 passed (179)` |
| `src/features/announcement-feed/__tests__/AnnouncementFeed.test.tsx` | S3 `S3-FE-02` (was `files 6`) | files 1, 19 | `1 passed (1)` / `19 passed (19)` |
| `src/features/access-control/__tests__/AccessControlPage.test.tsx` | S4 `B-80` / `S4-FE-04r` (was `files 2`) | files 1, 4 | `1 passed (1)` / `4 passed (4)` |
| `src/api/__tests__/finance.test.ts` | S4 `S4-FE-01` (was `files 6`) | files 1, 22 | `1 passed (1)` / `22 passed (22)` |
| `src/features/media-management/__tests__/MediaAssets.test.tsx` | S2 mandatory `S2-MAND-FE-media` (was `files 7`) | files 1, 8 | `1 passed (1)` / `8 passed (8)` |
| `src/features/user-administration/__tests__/Navbar.test.tsx` | the note's own worked example | files 1, 30 | `1 passed (1)` / `30 passed (30)` |

Seven for seven. The `AccessControlPage` row is the specific case round 1 named
(`S4-FE-04` said `files 2` where the real count is 1) and it now reads 1.

**No row disagrees with its own command.** Every frontend ledger command pins
exactly one spec path, so `M = 1` is the only value consistent with the command,
and 187 of the 190 `(files N)` strings now read `(files 1)`. The three
`(files 51)` strings all belong to the one directory-wide command,
`src/features/user-administration/__tests__` (`S2-FE-10b` and its baseline
`B-47`). I confirmed 51 is that directory's file count by the suite-wide list
below; the orchestrator re-ran the path directly. There is no longer any row whose
file figure contradicts the path its command names.

**Cross-references reconcile after the move.**

- Suite-wide figures are untouched and still correct. `npx vitest list` from
  `frontend/` gives 2503 lines over 188 distinct paths — exactly the
  `188 files / 2503 cases` the document reports at lines 33, 808, 5267 and 5291.
  The note at line 391 states explicitly that these come from `vitest list` and
  `Test Files 188 passed (188)` and are unaffected, which is true: no `188` in the
  document derives from a reporter suite count.
- The S4 valid-row floor holds. 13 `S4-FE-*` row headings exist; three carry the
  invalidation marker; `01, 02, 03, 05, 06, 07, 09` plus `04r, 08r, 10r` = 10
  valid rows against a floor of 10. The census row at line 807 reads
  `13 (10 selected, 3 re-run)` with a realised rate of `10 of 44 = 22.7%`, which
  is arithmetically right and does not depend on any file figure.
- The ledger-wide reconciliation still closes: 183 rows total (line 14,
  `across 84 step-0` baselines + 99), of which 93 are frontend (93 step-3 lines)
  and 90 backend; 96 of 183 reuse a baseline (line 298). None of these counts is
  derived from the file column, and none moved.
- The two prose occurrences that carried the wrong figure are both repaired and
  both now reconcile with the row they cite: F-13 at line 4780 reads
  `(files 51)`, `Test Files 51 passed (51)` / `Tests 513 passed (513)`; FU-10 at
  line 5476 reads `513 cases across 51 files`. `grep -n '134'` returns exactly one
  hit in the whole document — line 335, inside the methodology note, labelled as
  the superseded describe count. Zero stray `134`s remain.

## 2. The methodology note (lines 310–394; `numTotalTestSuites` at 323, 329, 335, 358, 385)

Keeping the mislabelled field name there is right, and it is correctly labelled.
Three things make it right rather than merely tolerable:

1. **It is what makes the correction falsifiable.** The note's load-bearing claim
   is "all 186 printed `M` equalled that JSON's `numTotalTestSuites`, confirming
   the single mechanical cause." That is a reproducible claim only if the
   superseded field is named — and I did reproduce it, by re-running my checker
   against the pre-edit copy with `numTotalTestSuites` substituted and getting
   186/186. Strip the field name and the sentence degrades to an unverifiable
   "we had a bug and fixed it," which is precisely the shape of claim this whole
   audit exists to reject. A document whose subject is unbacked prose assertions
   cannot itself make one.
2. **Every occurrence is annotated at the point of use**, never left bare:
   "which counts `describe` blocks, not files" (323), `<- describe blocks` in the
   worked example (329), set against `len(testResults) = 51` on the same line
   (335), "confirming the single mechanical cause" (358), and the scoping
   statement at 385.
3. **The scoping statement is true, and I checked it.** Line 385 —
   "`numTotalTestSuites` is now used nowhere in this document… It appears only in
   this subsection" — is confirmed by `grep -n`: all five hits fall between 323
   and 385, none in a ledger row, none in the census, none in a finding. The
   sentence is self-referential but immediately qualifies itself, so it does not
   read as contradicted by its own existence.

The worked example also checks out independently: the note quotes
`numTotalTestSuites : 3 / len(testResults) : 1 / numTotalTests : 30` for
`Navbar.test.tsx`, and exactly one retained artefact set carries that triplet
(`base-B-73.json`, `S3-FE-15.json`, `rev2-navbar.json`), with the spec itself
re-running today as `Test Files 1 passed (1)` / `Tests 30 passed (30)`.

The alternative — a note that says "the figure was wrong, it is now right" without
naming what it was — would be strictly worse: it would leave the next auditor
unable to tell whether the repair was uniform or spot-fixed, which is the one
question a 183-figure sweep raises.

## 3. The invalidation markers on `S4-FE-04`, `-08`, `-10`

Each of the three now carries an unmissable marker **in its own body**, not only
the `r` suffix on the sibling. Three layers per row:

- the heading itself: `#### \`S4-FE-04\` — **INVALIDATED RUN, MEASURED NOTHING**`
  (4268, 4365, 4422);
- a blockquote banner opening
  `> **!! INVALIDATED — THIS ROW IS NOT AN ADJUDICATION. IT MEASURED NOTHING.**`
  (4270, 4367, 4424), which names the exact mutated line, states the run collected
  0 cases at exit 1, states the row supports no class and counts toward no budget,
  names the replacement row, and says why the failed attempt is kept;
- the fields that previously read like a verdict are replaced. This goes beyond
  what round 1 asked for and is the part that actually matters:
  `Reddened vs that baseline` moved from `none` to
  **`not measurable.` Not "none": every one of the baseline's cases went from
  *passing* to *not collected*, which is neither green nor reddened**; and
  `Was it among the reddened?` moved from `no — expected: …` to
  **`question does not apply — invalidated run.`** The old `none` / `no` pair was
  the real hazard — under the spec's own definitions a non-collected run has no
  pass/fail set to subtract a baseline from, so `none` was not merely terse, it
  was a category error. It is now correct.

`EK-15` (5371–5385) was extended to state that each row body carries its own
banner and that the two fields are replaced, so the index entry and the rows agree
rather than the index carrying a claim the rows do not honour.

## 4. Did the 183-figure sweep disturb anything else?

No. I read all 105 hunks of the pre-edit-vs-staged diff. Every `<` line has a
matching `>` line differing only in the intended way; there is no deletion without
a replacement, no clipped line, no truncated table row, no orphaned list item. The
change set is exactly:

1. 183 `(files N)` figures inside `Step-0 baseline` / `Step-3 mutated run` lines
   (and nothing else on those lines — the freeze fingerprints, reuse-condition
   clauses (a)/(b)/(c), interim `freeze.iNN` names and exit codes all survive
   byte-for-byte, which I verified by inspecting the paired `<`/`>` text);
2. the two prose figures — F-13 at 4780 and FU-10 at 5476 — plus the matching
   restatement in `S2-FE-10b`'s `Case under examination` field at 3164
   (`513 cases, 134 files` → `513 cases, 51 files`), which round 1 did not
   enumerate but which is the same defect and had to move with them;
3. the methodology note, two inserted blocks at 310–348 and 350–394 (84 lines);
4. the three invalidation markers (heading, banner, two fields each) and the
   8-line EK-15 addition at 5378.

Nothing else. 5551 − 5407 = 144 added lines = 39 + 45 (note) + 3 × 17 (banners, 16
lines + blank) + 8 (EK-15) + 1 (F-13 sentence rewrapped onto two lines).

**Tree safety.** I made no backend run, so `uv` was never invoked and the
`cb629948…` freeze could not have moved. My frontend runs are read-only. Final
state:

```
$ git status --porcelain --untracked-files=all backend/ frontend/
?? backend/scripts/sync_obras_from_drive.py
```

— the single deliberately-uncommitted operator script, unchanged and untouched.
`git diff --name-only -- docs/audits` is empty, so the worktree copy is identical
to the staged copy. The index still holds exactly one path. I staged nothing,
unstaged nothing, mutated nothing, and left `docs/suggestions-log.md` and the
other tasks' uncommitted `docs/` files alone.

---

## Blocking Findings

None.

## Suggestions

1. **Numeric collision between "183 figures" and "183 rows."** Line 358 says
   "183 figures changed" while lines 14, 298, 824, 839 and 845 use 183 for the
   row count. The two are unrelated quantities that coincide. In a document whose
   entire subject is a number that was mistaken for a different number, a reader
   skimming the note may read line 358 as "every row changed." Disambiguating it
   — e.g. "183 of the 186 file figures changed" — would cost six words. Context
   makes it recoverable today, so this is not blocking.
2. **The note's population count could name its own denominator.** The note says
   "every one of the 186 frontend run summaries," which is right, but the document
   also contains four further `(files N)` strings (three banners, one prose
   sentence). A half-sentence noting that the quotations outside the ledger were
   updated with their sources would close the gap between "186 summaries" and the
   190 occurrences a reviewer's `grep` returns — which is the arithmetic I had to
   reconstruct to satisfy myself nothing had been missed.
3. Optional, for the follow-up sweeps: the per-row validation I ran is eight lines
   of Python over the retained `runs/*.json`. Retaining it beside the artefacts
   would let FU-13/FU-14 re-assert the row-to-artefact mapping without rebuilding
   the parser.
