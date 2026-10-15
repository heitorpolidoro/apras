# APRAS-111 — QA verification report, round 2

**Verified on 2026-10-05**, independently, against the staged document
`docs/audits/APRAS-111-test-suite-audit.md` (now **5581** lines; 5551 in round 1)
and the live repository at `master` / `1f0079b`.

Scope, stated plainly: this round verifies **the repair and only the repair**.
Round 1 passed R1, R2, R4, R6–R18 on evidence I gathered myself and the repair
could not reach most of it; I did not re-run the 183-row evidence battery in
full. Where I did re-check something outside the repair's reach, I say so. Where
I did not, I say that too — see *What I deliberately did not re-verify*.

`<scratchpad>` is
`/private/tmp/claude-501/-Users-heitor-workspace-apras/06230b8a-d0ef-40dd-929b-83bb4eb6abbf/scratchpad`,
the same path the document names; this session inherited the audit's scratchpad,
so every `freeze.*` artefact was directly inspectable.

**Method note, carried over from round 1's lesson.** Round 1's blocking finding
was a claim that read as verified and was not. Every zero-hit search below was
preceded by a positive control, and this paid off twice in this round:

- `grep -c 'Step-0 baseline reused run'` → **0**, on text that is present 99
  times. The document writes `- **Step-0 baseline** reused run **B-NN**`; the
  bolding sits mid-phrase. Had I trusted that zero I would have reported the 99
  reuse rows as missing.
- A strict `startswith('- **Step-2 read-back**')` parse reported the read-back
  bullet missing from all 183 rows. The actual label is
  `- **Step-2 read-back (line-scoped)**`. Both zeroes were artefacts of my
  pattern, not of the document.

All counting below is by parser over the whole file, never by sample.

---

## 1. The 99 reuse rows — both directions

Parsed the 183 `#### ` row blocks and classified every `- **Step-0 baseline**`
bullet.

| measurement | claimed | I measured |
|---|---|---|
| `- **Step-0 baseline**` bullets | 183 | **183** ✔ |
| of which `reused run` | 99 | **99** ✔ |
| of which own-baseline | 84 | **84** ✔ |
| lines carrying `(c) interim` | 99 | **99** ✔ |
| `(c) interim` lines that are **not** a reuse bullet | 0 | **0** ✔ |
| reuse bullets **without** `(c) interim` | 0 | **0** ✔ |
| own-baseline bullets carrying reuse/`compared against` text | 0 | **0** ✔ |
| reuse bullets missing ``compared against `freeze.before2`: **empty**`` | 0 | **0** ✔ |
| own-baseline bullets mentioning `freeze.before` at all | 0 | **0** ✔ |
| `compared against \`freeze.before2\`: **empty**` (fixed-string, whole file) | 99 | **99** ✔ |
| `compared against \`freeze.before\`: **empty**` (old text) | 0 | **0** ✔ |
| `compared against \`freeze.before\`` in any form | 0 | **0** ✔ |

Both directions therefore hold: **every** reuse row was changed, and **nothing
else acquired the text**. The 99 interim identifiers on those bullets are
`freeze.i01 … freeze.i99`, **99 distinct ids, no duplicates, none missing** —
one per reuse row, which is what makes 84 + 99 = 183 close. The 84 own-baseline
bullets carry **84 distinct `B-NN`** identifiers.

**PASS (item 1).**

## 2. Re-running the 99 diffs against both references

This is the check a repair cannot change. Over the 99 retained interim captures:

```
differ from freeze.before : 99 / 99
differ from freeze.before2:  0 / 99
```

Identical to round 1 — nothing in the scratchpad was disturbed. Supporting
measurements, all my own:

- `<scratchpad>/freezes/` holds **183** files: **84** `freeze.B-NN` + **99**
  `freeze.iNN`, exactly the ledger's split.
- `shasum -a 256` over all 183 → **one** distinct fingerprint,
  `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- `diff freeze.before2 freeze.after` → empty.
- `sqlmodel` line: `freeze.before` = `0.0.38`; `freeze.before2` = `0.0.47`;
  `freeze.after` = `0.0.47`. A `grep -rl 'sqlmodel==0.0.38'` across every
  `freeze*` artefact in the scratchpad returns **exactly one file**,
  `freeze.before` — so the paragraph's "only capture that reads `0.0.38`" is
  literally true.
- `diff freeze.before freeze.before2` and `diff freeze.before freeze.chk1` both
  yield **exactly** `line 40: sqlmodel==0.0.38 → sqlmodel==0.0.47`, which is the
  delta the document quotes in both places.

**PASS (item 2, empirical half).**

## 3. Is the new paragraph honest, or merely consistent?

The paragraph is at lines **146–176**, inside `Census and method` → `###
Environment`, titled **"Which capture is the reference, and where the one delta
falls."** I read it in full against the four things it has to do, and against
the harder question of whether renaming the reference buries the delta.

It does not bury it. Judged on substance:

1. It states that `freeze.before` **predates** the re-sync and is the *only*
   capture reading `sqlmodel==0.0.38` — verified above, exactly one file.
2. It states `freeze.before2` is the post-upgrade capture taken **before the
   first mutation**, reading `0.0.47` — verified.
3. It states every row is measured against `freeze.before2`, naming **both**
   `freeze.B-NN` and `freeze.iNN` explicitly. This matches the ledger: the 99
   reuse bullets now name `freeze.before2`, and the 84 own-baseline bullets
   record the `cb629948…` fingerprint, which **is** `freeze.before2`'s.
4. It **re-quotes the delta in full** (`40c40 / sqlmodel==0.0.38 /
   sqlmodel==0.0.47`) in the paragraph itself, then says the delta "lies
   **outside** every row's measured window … no row's window opens earlier than
   `freeze.before2`", and gives that as the reason no row is marked `baseline
   stale — environment changed mid-audit`.
5. Decisively, it closes with the counterfactual a reader needs in order to
   apply R5's rule rather than take it on trust: *"Measured against
   `freeze.before` instead, every one of those 183 captures differs by exactly
   the line above — which is what the staleness rule would have fired on had the
   re-sync landed after any baseline rather than before all of them."*

That last sentence is the disclosure my round-1 finding said was missing. A
reader can now see both **why** no row is stale and **what** would have made
them stale. The delta is stated three times in the subsection (the original
`freeze.chk1` evidence block at 133, the re-quote inside the paragraph, and the
counterfactual), not once and quietly. The renaming is a correction of the
reference, not a concealment of the diff.

**PASS (item 2, substance).**

## 4. The 96 → 99 prose correction, recounted independently

Round 1's finding was itself a wrong count, so I recounted from the artefacts
rather than reading the number.

- Line **197–198**: "**99** interim captures (`freeze.i01` … `freeze.i99`) were
  taken at reuse time, one per baseline-reusing row, each compared against
  `freeze.before2`". My own count of `<scratchpad>/freezes/freeze.i*` is **99**,
  lowest `freeze.i01`, highest `freeze.i99`, and the 99 ledger references are
  99 distinct ids with no duplicate and no gap. The range end and the count are
  both right, and the other `freeze.before` in that paragraph was renamed to
  `freeze.before2`.
- Line **328**: "**99** of the 183 rows reuse a baseline run…". My parse: 99
  reuse bullets, 84 own. 84 + 99 = 183. Correct.
- I enumerated **every** occurrence of the digit pair `96` in the file with 45
  characters of context either side. **None is a count.** They are: two
  `PX_PER_MM = 96 / 25.4` / `PX_PER_PT = 96 / 72` table cells, a stride list
  value, `1.96s` run durations, `0.96` mutation values, hex substrings inside
  `shasum` digests and test-case parameter ids, and one `freeze.i96`.
- That single `freeze.i96` (line 4542) is the **`S2-MAND-BE-branding-b` /
  `B-84` row's own capture reference**, not a range end — exactly the one
  legitimate survivor claimed. No `freeze.i96`-as-range-end remains.

**PASS (item 3).**

## 5. Remaining `freeze.before` mentions — is the list of four complete?

Regex `freeze\.before(?!2)` over the whole file returns **exactly four lines**,
and the list matches the claim:

| line | text | legitimate? |
|---|---|---|
| 111 | "The `passlib` line of `freeze.before` reads `passlib==1.7.4`" | yes — pre-existing R4 evidence; I confirmed `grep passlib freeze.before` → `passlib==1.7.4` |
| 133 | `$ diff <scratchpad>/freeze.before <scratchpad>/freeze.chk1` | yes — this is the `uv run` re-sync disclosure, and the diff genuinely is that one line |
| 147 | "`freeze.before` was taken before that re-sync…" | yes — inside the new paragraph |
| 172 | "Measured against `freeze.before` instead, every one of those 183 captures differs…" | yes — the counterfactual, inside the new paragraph |

Two in the new paragraph, two pre-existing and correct. The list is complete and
no stale reference survives anywhere in the ledger.

**PASS (item 4).**

## 6. The `68` → `90` correction (orchestrator's separate fix)

Line **845–847** now reads: "the backend suite's 4195 collected cases minus the
cases touched by the **90** backend mutation rows' modules, and the frontend
suite's 2503 minus the specs touched by the **93** frontend rows."

I derived both numbers two independent ways and they agree:

- **From the ledger.** 183 `Order-pinned command` bullets: **90** begin
  `cd backend`, **93** begin `cd frontend`. (All 90 backend commands still carry
  both `-p no:randomly` and `--no-cov` — 90/90, R3's last clause intact after
  the edit.)
- **From the per-stratum table.** Backend `mutated`: S1 **43** + S2 **25**
  (16 stride-and-supplementary + 9 mandatory) + S3 **22** = **90**. Frontend:
  S1 **42** + S2 **18** (15 + 3) + S3 **20** + S4 **13** = **93**.

So 90 is the right number, the old 68 was indeed S1+S2 only (43+25) with S3's 22
omitted, and the sentence is now internally consistent: both halves of the
same sentence are now row counts of the same kind, 90 against 93. The only
surviving `68` in the document is the filename `freeze.B-68`.

**PASS (item 5).**

## 7. Arithmetic and file integrity

- 84 own-baseline + 99 reuse = **183** ledger rows ✔ (183 `#### ` row blocks,
  183 `- **File:line**` bullets).
- 90 backend + 93 frontend = **183** order-pinned commands ✔.
- Per-stratum `mutated` column sums to **90 / 93** ✔ (above).
- Code fences: **440** lines whose stripped form opens a fence — 366 indented by
  two (exactly 2 per row × 183) + 74 at column 0 — and the total is **even**, so
  every fence closes. Matches the claim exactly.
- **All nine mandatory bullets present on all 183 rows, 0 missing**, once the
  two label patterns are corrected (`Step-2 read-back (line-scoped)`,
  `Reddened vs that baseline (N)`, `Step-5 restore …`).
- **Read-back fidelity re-run in full, 183 / 183.** For each row I took the
  `File:line` and the *first* `sed -n '<line>p'` output (the pristine scratchpad
  copy) and compared it against the live file's content at that line number. All
  183 match. This is the strongest available proof that the 99-row mechanical
  edit corrupted no row body and shifted no line, and that every mutated file is
  still byte-restored today.
- Nine `##` sections present and in order, plus the appendix — structure
  unchanged.
- Growth: 5581 lines against the 5551 I measured in round 1 = **+30**, and the
  new paragraph occupies lines 146–176. I note one limit on this specific claim:
  the document is staged as a **new** file (`A`), so there is no committed prior
  revision to byte-diff the two rounds against. "All 30 added lines are in the
  new paragraph" is therefore corroborated structurally — the line budget, the
  unchanged 183/84/99/90/93/440 counts, and the 183/183 read-back — rather than
  by a diff. Nothing I could measure is inconsistent with it.

**PASS (item 6).**

## 8. The working tree, checked against the repository

- `git diff -- backend frontend` → **empty**.
- `git status --porcelain --untracked-files=all` → the only entry under either
  tree is `?? backend/scripts/sync_obras_from_drive.py`, the
  deliberately-never-committed operator tool. Everything else is `docs/`,
  `docs/suggestions-log.md` (` M`) and `sync-obras.sh`.
- `git diff --cached --name-only` → **exactly one** file,
  `docs/audits/APRAS-111-test-suite-audit.md`.
- No mutation was run by me; this round was read-only over the document, the
  repository and the scratchpad.

**PASS (item 7).**

---

## The two expected results the repair touches

### R3 — PASS (was FAIL in round 1)

The single failing clause is repaired, and repaired correctly rather than by
assertion. R3 requires that a reused baseline's row name its interim
`uv pip freeze` capture **and its comparison against the reference capture**. All
99 reuse rows now read ``compared against `freeze.before2`: **empty**``, and
`freeze.before2` is the reference the method section designates — now stated
twice, at line 154 and again in the new paragraph. That comparison is **true**:
0 / 99 interim captures differ from `freeze.before2` on my own re-run. The
ledger no longer contradicts the method section anywhere; `compared against
freeze.before` occurs **zero** times in the file (zero confirmed against a
positive control).

Everything else R3 asks for, re-confirmed on the repaired file rather than
assumed: 183 rows each carrying all nine bullets (0 missing); 90/90 backend
order-pinned commands with both `-p no:randomly` and `--no-cov`; 183/183
line-scoped `sed` read-back pairs present as command output and matching the
live files; step-0 baselines either an own run (84 distinct `B-NN`) or a **named**
reused run (99, each naming its `B-NN` and re-asserting all three conditions, no
anonymous pasted baseline text); `Case under examination` and `Was it among the
reddened?` on every row.

### R5 — PASS (and strengthened)

The `before`/`after` pair the staleness rule is computed over is `freeze.before2`
→ `freeze.after`, and I checksummed both myself: identical,
`cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`, `diff`
empty. Each baseline run records its own `shasum`, and all **183** captures in
`<scratchpad>/freezes/` carry that one fingerprint, so no two consecutive
baseline runs differ and no row can be stale on that ground. The count error
that was folded into round 1's finding is gone: **99** interim captures,
`freeze.i01 … freeze.i99`, **99** reuse rows, 84 + 99 = 183, all recounted from
the artefacts.

R5 is in fact better served than before the repair. The rule — "a non-empty diff
marks every row whose step-0 baseline predates the observed change as `baseline
stale`" — can now be applied by a reader, because the document discloses both
that the one real environment change exists and that it falls outside every row's
window, *and* states what the rule would have fired on had it fallen inside. In
round 1 the rows asserted emptiness against a reference where the diff was
genuinely non-empty, which misreported the one guard deciding whether a baseline
was usable. That is no longer the case on any row.

---

## Was any other expected result disturbed?

No. Stated precisely, separating what I re-measured from what I did not:

**Re-measured this round, and unchanged:**
- R3's non-failing clauses and R5 in full (above).
- Document structure — nine `##` sections plus appendix, 183 rows, nine bullets
  per row, 440 balanced fence lines (R1 structural leg).
- The per-stratum `mutated` column and the 90 / 93 totals (R2, R7 arithmetic
  leg), which the `68 → 90` fix touches.
- 183/183 pristine-line read-back against the live files (R3, R11 restore leg) —
  this is also my corruption check on the 99-row edit.
- R11 in full against the live repository: `git diff -- backend frontend` empty,
  one `backend/` untracked entry, one staged file.
- R4's `freeze.before` / `passlib` evidence legs, because the repair renamed
  references inside the `Environment` subsection R4 is graded on. Line 111 and
  line 133 are intact and both verify.

**Not re-verified, because the edit could not reach it** — I am not implying I
re-checked these; I am relying on round 1, where each passed on my own evidence:
R1's findings content, R2's enumeration re-runs, R6, R7's stride re-derivations,
R8, R9, R10, R12's three baselines, R13, R14, R15's parity gate, R16's over-pin
table, R17's version banners, R18. The repair's only reach was 99 Step-0
baseline bullets, one new paragraph in `### Environment`, two prose counts in
that same subsection and at line 328, and one figure at line 845 — and the
183/183 read-back plus the unchanged structural counts bound the edit to exactly
that.

**Carried forward unresolved from round 1, non-blocking:**
- The backend coverage figure in *Coverage and lint baselines* reads
  `TOTAL 11716 668 94%` / `94.30%`; my round-1 run of the same command gave
  `667` / `94.31%`, identical on tests, skips, warnings and exit code. One
  statement in ~11.7k is run-to-run variance, not a misreport. I did not re-run
  the full backend suite this round.
- R14's two shipped-config probe invocations still rest on
  `<scratchpad>/probe.out` rather than on my own execution, because re-running
  them requires writing under `frontend/src/`, which my constraints forbid.

## Suggestions (non-blocking, all carried over)

1. Note that the backend coverage figure is ±1 statement rather than exact,
   since every follow-up must report against it.
2. A short S3 selection table would make S2/S3/S4 symmetric; the 40 selections
   are currently only readable off the ledger rows (I reproduced 40/40 in round
   1, so reproducibility is not impaired).
3. The S2 frontend stride table's slot 9, `…/TenantBrandColors.tsx:237` → text
   at `:357`, would read unambiguously as `idx 237 → TenantBrandColors.tsx:357`.

---

VERDICT: APPROVED

None.
