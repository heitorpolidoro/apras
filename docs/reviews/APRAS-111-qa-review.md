# APRAS-111 — QA verification report

**Verified on 2026-10-05**, independently, against the staged document
`docs/audits/APRAS-111-test-suite-audit.md` (5551 lines) and the live repository
at `master` / `2cb0d48`. I received only the expected results; I did not read the
spec, the developer's report or the code review.

Everything below that says "re-ran" means I executed the command myself and
compared numbers. Where I used the audit's retained scratchpad artefacts
(`runs/`, `snap/`, `freezes/`, `freeze.*`, `probe.out`, `leaks.control.jsonl`),
I say so, and I treated them as the audit's own claims to be *cross-checked*,
not as evidence in themselves.

`<scratchpad>` below is
`/private/tmp/claude-501/-Users-heitor-workspace-apras/06230b8a-d0ef-40dd-929b-83bb4eb6abbf/scratchpad`,
which is the same path the document names — this QA session inherited the audit's
scratchpad, so its retained artefacts were directly inspectable.

---

## What I re-ran from scratch

| command | document says | I measured |
|---|---|---|
| `cd backend && SECRET_KEY=test uv run pytest --collect-only -q --no-cov` | 4195 collected | **4195 collected in 0.57s** ✔ |
| `cd backend && SECRET_KEY=test uv run pytest --version --version` | banner with `pytest-cov-7.1.0`, `pytest-timeout-2.4.0`, `anyio-4.14.2`, no randomiser | **byte-identical banner** ✔ |
| `cd backend && SECRET_KEY=test uv run pytest --version` (single flag) | prints only `pytest 9.1.1`, no banner | **`pytest 9.1.1`** ✔ |
| `cd frontend && npx vitest list` | 188 files / 2503 cases | **188 / 2503** ✔ |
| `cd frontend && npx vitest --version` | `vitest/4.1.11 darwin-arm64 node-v24.13.0` | identical ✔ |
| `cd backend && uv pip freeze \| grep passlib` | `passlib==1.7.4` | identical ✔ |
| `… pytest … tests/test_bcrypt_cost.py` | `1 failed, 9 passed, 1 warning`, `FAILED …::test_passlib_is_not_installed` | identical ✔ |
| S1 backend enumeration (verbatim) | N = 62 | **62** ✔ |
| S1 frontend enumeration (verbatim) | N = 50 | **50** ✔ |
| S2 backend / frontend enumeration | 287 / 315 | **287 / 315** ✔ |
| S3 backend / frontend enumeration | 577 / 551 | **577 / 551** ✔ |
| S4 enumeration | 269 | **269** ✔ |
| `cd frontend && npm run lint` | `370 problems (368 errors, 2 warnings)` | **identical, exit 1** ✔ |
| `cd frontend && npm run test:coverage` | 188 / 2503 passed, `91.5 / 85.28 / 87.83 / 92.21`, exit 0 | **identical, exit 0, no `Errors` block** ✔ |
| `cd backend && SECRET_KEY=test uv run pytest` (full, gate on) | `TOTAL 11716 668 94%`, `94.30%`, `1 failed, 4156 passed, 38 skipped, 6332 warnings`, exit 1 | `TOTAL 11716 **667** 94%`, `94.3**1**%`, `1 failed, 4156 passed, 38 skipped, 6332 warnings`, exit 1 — see note 1 |
| six step-0 baseline commands (`test_clock`, `test_lint_hygiene`, `test_slug`, `test_suite_hygiene`, `test_branding`, `test_assets_rbac`) | `12 passed, 10 warnings` / `4 passed, 1 warning` / `74 passed` / `9 passed` / `116 passed` / `5 passed, 64 warnings` | **all six reproduce exactly, warning counts included** ✔ |
| R15 parity gate — `npx vitest list --config <scratchpad>/vitest.audit.config.ts` vs plain `npx vitest list`, both from `frontend/` | 188 / 2503 both sides, file lists byte-identical | **188 / 2503 both sides; `diff` of the two sorted file columns empty** ✔ |

Note 1: the backend coverage figure differs by **one statement** (667 vs 668
missed, 94.31% vs 94.30%). Test counts, skip counts, warning count and exit code
are identical. This is single-statement run-to-run variance in a 11 716-statement
measurement, not a misreport, and the baseline is used only as a floor. Not a
blocking finding; recorded as a suggestion.

## Mechanical checks over the document

Run with a parser over the `### Rows` section, not by eye:

- **183 rows**, matching the header's claim. Every one of the 183 carries all
  nine required bullets (`File:line`, `Mutation`, `Step-2 read-back`,
  `Order-pinned command`, `Step-0 baseline`, `Step-3 mutated run`, `Reddened vs
  that baseline`, `Was it among the reddened?`, `Step-5 restore`) — **0 rows
  missing anything**.
- **Every backend ledger command carries both `-p no:randomly` and `--no-cov`** —
  0 exceptions over 90 backend rows. The only `pytest` command in the document
  without `--no-cov` is the full-suite baseline in *Coverage and lint baselines*,
  which is the stated exception. R3's last clause holds.
- **Read-back fidelity, the strongest check I ran.** For each of the 183 rows I
  took the `File:line` and the *first* `sed -n '<line>p'` output (the pristine
  scratchpad copy) and compared it to the live file's content at that line
  number. **183 / 183 match.** This simultaneously proves the mutations were
  line-accurate, the quoted pristine text was not invented, and every file is
  byte-restored today.
- **Reddened sets recomputed from artefacts.** For all 90 backend rows I parsed
  `FAILED` lines out of `<scratchpad>/runs/base-B-NN.txt` and
  `<scratchpad>/runs/<row>.txt` and computed `step3_failures − step0_failures`
  myself. **90 / 90 agree with the row's `Reddened` list and its count**, `none`
  included. 89 / 90 quoted step-0 summary lines appear verbatim in the retained
  baseline file; the one that does not is `S3-BE-03`, which legitimately has no
  pass/fail summary (all-skipped module) and says so.
- **Frontend run summaries.** For all 93 frontend step-3 rows I read
  `numTotalTests` / `numPassedTests` / `numFailedTests` / `len(testResults)` out
  of that row's own `<scratchpad>/runs/<row>.json`. **93 / 93 match the row's
  `N tests: P passed, F failed (files M)` exactly**, including the corrected
  `files M = len(testResults)`. The document's self-reported mislabel repair is
  therefore real and complete, not asserted.
- **No file-scoped emptiness assertion in the ledger.** Searched the ledger for
  `grep -c`, `grep -q`, `grep -n`, `wc -l`, "no longer appears", "absent from the
  file", "does not appear", "zero hits": **0 hits each**. Positive control first:
  the same search machinery returns `sed -n` → 366 (exactly 2 per row), `cmp ` →
  183 (exactly 1 per row), `shasum` → 450. The zero is a real zero.
  Two hits for "returns nothing" are both *test case titles*, not assertions.
- **No estimated percentage.** All 19 `N%` occurrences in the document are either
  tool output (`94%`, `94.30%`, `91.5`, the `90%` gate text) or arithmetic over
  measured counts. I recomputed each: 12/287 = 4.2, 12/315 = 3.8, 20/577 = 3.5,
  20/551 = 3.6, 10/44 = 22.7, 10/577 = 1.7, 1/40 = 2.5. All correct.

## Expected results, one by one

**R1 — PASS.** All nine `##` sections present: *Census and method*, *Mutation
ledger*, *Findings*, *Over-pins*, *Unhandled errors*, *Examined and kept*,
*Coverage and lint baselines*, *Follow-up proposals*, *What this audit did not
cover* (plus an appendix). 16 findings; each names its ledger row, its mutation
and the observed green/red outcome. Every finding's row exists in the ledger and
its `sed` pair verified present by the 183/183 read-back check above. I
additionally re-derived four findings read-only: F-01 (`grep -n GRAPHIC_FLOOR
backend/tests/test_project_report_branding.py` → exactly `100` and `449`, the
latter `assert ratio < GRAPHIC_FLOOR` — an upper bound, as claimed), F-02
(`grep -rl SLUG_MAX_BASE_LENGTH` over frontend specs → nothing, exit 1), F-06
(no `cov-fail-under` read in `test_suite_hygiene.py`, exit 1), F-10 (the
assertion at `test_project_report.py:1210` is verbatim
`assert report.planned_to_date([{"month": "1970-01", "pct": 7.0}]) == 7.0`,
which indeed cannot discriminate any "today" at or after 1970-01).

**R2 — PASS.** *Census and method* reports collected totals per suite with the
command, states the spec's 4181 / 188-2496 figures *and* its own measurement
(4195 / 188-2503, both of which I reproduced), and explains the delta as one
day's work by other tasks in the shared worktree — which R2 explicitly permits
("or the counts its own run measures"). The *Per-stratum accounting, measured*
table gives, per suite and per stratum S1–S5: collected, candidate-set `N`,
budget, mutated, read-only judged, remainder as a measured count of candidate
lines, and realised rate. Every enumeration command is quoted; I re-ran all five
and all five counts match. No percentage is estimated (see above).

**R3 — FAIL.** Everything in R3 holds except one clause, and it fails uniformly
across 99 rows. Detail under *Blocking findings* below. What does hold:
order-pinned commands with both flags (90/90), line-scoped `sed` read-back pairs
as command output with no y/n and no file-scoped emptiness assertion anywhere,
step-0 baselines either own-run-with-pass/fail-set (84 distinct `B-NN`) or a
named reused run (99 rows, each naming its `B-NN` and re-asserting the three
conditions — no row pastes shared baseline text anonymously), reddened sets
computed as a set difference and independently recomputable (90/90 backend),
`Case under examination` plus `Was it among the reddened?` on every row, a
neighbour-only reddening raised as a finding in its own right (F-15), "reddened"
restricted to green-in-0-and-failing-in-3, and the already-failing case
(`test_passlib_is_not_installed`) quarantined in its own subsection with its
failure line quoted and excluded from every row's evidence.

**R4 — PASS.** The `Environment` subsection names both pre-mutation
not-green populations, the command that showed each, and the cause.
`test_bcrypt_cost.py::test_passlib_is_not_installed` **is** among them and the
cause is stated as `passlib 1.7.4` installed in `backend/.venv` while undeclared
in `backend/pyproject.toml` — local environment drift, CI green. I confirmed all
three legs: `uv pip freeze` shows `passlib==1.7.4`; `pyproject.toml` does not
declare it; the module fails exactly `1 failed, 9 passed` on my own run. The
second population (`test_migrations_postgres.py`, 38 skipped, `skipif` at line
109, no local Postgres) is also named with its command and cause. The document
states it ran no `uv sync`, `uv pip install`/`uninstall`, `npm install` or
`npm ci`, and discloses the one `uv run`-triggered re-sync of `sqlmodel`
(0.0.38 → 0.0.47) that happened before the first mutation.

**R5 — PASS (with the R3 defect noted separately).** The `before`/`after` pair
the staleness rule is computed over is `freeze.before2` (post-stabilisation,
taken before the first mutation) and `freeze.after`. I checksummed both myself:
`cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75` for each,
`diff` empty — the document's positive record is true. Each baseline run records
its own `shasum`: I checksummed all 183 files in `<scratchpad>/freezes/` and
**every one is that same single fingerprint**, so no two consecutive baseline
runs differ and no row can be stale on that ground. The 96-vs-99 count error in
this subsection is folded into the blocking finding.

**R6 — PASS.** Exhaustive over a printed denominator, and I re-derived the
denominator. The two `grep` commands return **62** and **50** on my run, matching
the stated `N`. The backend triage table has **exactly 62 numbered rows** and the
frontend **exactly 50**, with a reason on every excluded line; `**yes**` appears
**19** times backend and **21** times frontend, matching the stated subsets. The
three config declarations are enumerated by file (`pytest.ini` lines 4 and 17;
`vitest.config.ts` lines 41–46), two mutated and the third judged read-only with
its reason (ER14 forbids editing the file) and its evidence (`grep -rln
"vitest.config" frontend/src` → two prose mentions, neither parsing the file),
handed to FU-02 with no finding claimed behind an unmutated judgement. I then
grouped all 81 S1 ledger rows by target: **43 distinct `file:line` targets**,
and every one of the 19 + 21 subset members carries **both** a weakening and a
strengthening (or lower/higher) row — no member with only one direction. The
anonymous numeric-assertion populations are counted by pinned command (1674
backend, 454 frontend) and deferred by name to FU-03.

**R7 — PASS.** Row counts by stratum, parsed from the ledger: S2 backend **16**,
S2 frontend **15** (floor 12 each, ≥ 24 total ✔); S3 backend **22**, S3 frontend
**20** (floor 20 each, ≥ 40 total ✔); S4 **13**, of which 10 valid selections
(floor 10 ✔). `N` and `k` are stated per suite, never combined. I recomputed
every stride from `ceil(i·N/k)` — all four stride lists are arithmetically
correct — and then re-derived the *selections themselves* from the live
enumeration:
- S2 backend: all **12 / 12** selected `file:line` match my own indexed
  enumeration exactly.
- S2 frontend: **12 / 12** match (slot 9's "`:237` → text at `:357`" notation is
  index-237-selects-line-357, which my enumeration confirms).
- S3 backend: **20 / 20** match. Slot 11 initially looked wrong until I read the
  row: it records `i=11 idx=318`, names the selected docstring at
  `test_project_report_escaping.py:702`, and applies the mutation to the subject
  (`interpolation_audit.py:343`) while running the selected module — correct
  method, fully disclosed.
- S3 frontend: **20 / 20** match; five entries differ by one line from the grep
  hit and each such row states the candidate line and the mutated line
  explicitly (e.g. `S3-FE-01`: "candidate line 2150 `).toHaveLength(0);`,
  mutated line 2149"), which is the multi-line-expression care the S4
  invalidations taught.
- S4: raw 269 confirmed; filtered `N = 44` with `k = 10` and a correct stride.

Substitution logging: the one substitution is logged in the required form
(`skipped backend/tests/test_migrations_postgres.py:1478 (…) → substituted
backend/tests/test_module_gating.py:115`), and I confirmed index 87 of my own
sorted S3 backend enumeration **is** `test_migrations_postgres.py:1478`. No
shortfall is declared and the document says why. S3's floor-of-20 reasoning is
stated from its own measured candidate set (577 + 551 against S2's 287 + 315) and
the cheapness of a vacuous absence; realised per-candidate rates are reported per
stratum; FU-13 sizes the remainder sweep from the 1-in-40 rate S3 actually
observed, in four parts.

**R8 — PASS.** All seven mandatory paths appear, each as the step-3 target of a
dedicated `S2-MAND-*` row, and the mutation lands on the subject the claim is
about (production code), which is the only way the claim is testable:
`test_project_report_escaping.py` (`S2-MAND-BE-escaping`), `test_branding.py`
(`-branding`, `-b`, `-c`, `-d`), `test_infraction_escalation.py` (`-escalation`),
`test_assets_rbac.py` (`-assets-rbac`, `-b`, `-c`), `themeContrast.test.ts`,
`infraction-management/__tests__/access.test.ts`,
`media-management/__tests__/MediaAssets.test.tsx`. I confirmed each
`Order-pinned command` names the mandatory module. The 12 mandatory rows are
additional to the full 12-slot stride in each suite (`S2-BE-01…12`,
`S2-FE-01…12` all present), so they are above the stride, not in place of a slot.
`test_assets_rbac.py` returning no match for the S2 regex is disclosed, with the
reason it was mutated anyway.

**R9 — PASS.** 16 findings, each heading carrying **exactly one** class token
(14 × class 1, 2 × class 2) from the closed five-class list, which is printed.
Every remedy is a *rewrite*; the document states explicitly that it proposes
**zero deletions** and that classes 1–4 are the only grounds on which a deletion
may be offered. "Slowness, verbosity and age are never grounds for anything" is
stated, and no entry rests on them.

**R10 — PASS.** *Examined and kept* holds EK-01 … EK-15, each naming the test or
row and its reason: EK-01 (the limiter loop, kept because the case documents its
own vacuity and the load-bearing half is an AST assertion), EK-02 and EK-03
(claim asserted by a named sibling, with the discriminating `-b` mutation that
reddens it), EK-04, EK-05–EK-14 (all ten S4 seams, with a per-row reason table
and the finding that the pre-stride filter is noisy → FU-06), EK-15 (the three
invalidated S4 rows kept deliberately, each carrying an `!! INVALIDATED` banner
and `not measurable` in place of a verdict — which I confirmed is how those three
row bodies actually read).

**R11 — PASS, verified against the live repository, not only the document.**
`git status --porcelain --untracked-files=all` right now shows exactly one entry
under `backend/` or `frontend/`: `?? backend/scripts/sync_obras_from_drive.py`,
the deliberately-never-committed operator tool, present in the document's quoted
`porcelain.before` too. `git diff -- backend frontend` is **empty**.
`git diff --cached --stat` shows **one** staged file: the audit document, 5551
insertions. `comm -13` of the document's quoted 43-line `porcelain.before`
against today's capture yields only `docs/` entries and `sync-obras.sh` — all
accumulated after `porcelain.after`, none under `backend/` or `frontend/`.
Independently of the captures, the 183/183 pristine-line read-back check above
proves every mutated line is byte-restored. Both captures and the diff/`comm`
commands are quoted in the document. All three required subsections exist:
*Aborted mutations* (none — and every row's restore checksum pair is identical,
which I confirmed by the read-back check), *Not examined — uncommitted work
present* (none, consistent with the quoted `porcelain.before`), *Not examined —
already failing pre-mutation* (two entries with failure/summary lines quoted).
`frontend/src/test/__audit_probe__/` is absent from the tree.

**R12 — PASS.** All three baselines are quoted from exactly the named commands.
`npm run lint` → `370 problems (368 errors, 2 warnings)`, which I reproduced
byte-for-byte. `npm run test:coverage` → `188 passed / 2503 passed`,
`91.5 | 85.28 | 87.83 | 92.21`, which I reproduced byte-for-byte, and I confirmed
the quoted `vitest.config.ts` thresholds (80 statements / 76 branches / 78
functions / 80 lines). The backend summary reproduces on test counts, skips,
warnings and exit code, with the one-statement coverage drift noted above. Every
one of the 16 follow-ups carries a "baseline it must report against" column, the
preamble repeats the three numbers, and the line-by-line explanation of any drop
is required. The "which production lines is this test the sole cover for"
question is answered as not-applicable with the reason (zero deletions proposed).

**R13 — PASS.** The named instance is called out by path and title —
`frontend/src/features/media-management/__tests__/MediaAssets.test.tsx` >
"allows file selection and triggers upload" — with the PR #34 / jsdom 30 history,
the measurement that it does not leak on `master` today, and the
`S2-MAND-FE-media` row proving the case is not inert (mocked `uploadPhoto`
rejection reddens exactly that case, `8 tests: 7 passed, 1 failed`, which I
confirmed against the row's retained JSON). Further instances: **none found**
over 188 files / 2503 cases, with a positive control proving the instrument
fires. I corroborated the zero independently: my own full `npm run test:coverage`
run printed no `Errors` block at all. The per-instance "would the suite have
noticed without Vitest's separate report" answer is given for both table rows
("No" for the historical case; "none found" for the sweep).

**R14 — PASS, with one honest limitation.** The section records both invocations
from `frontend/` against the shipped `vitest.config.ts` and shipped `test`
script, both `Test Files 1 passed (1)` / `Tests 2 passed (2)` / `Errors 2 errors`
/ exit 1 — the collected counts that prove the probe was collected — and states
the configuration was unchanged. The retained `<scratchpad>/probe.out` contains
both invocations with exactly those four lines each, in that order. Removal is
recorded as *verified absence* of `frontend/src/test/__audit_probe__/` rather
than a `cmp` against a non-existent pristine copy, with the reason stated, and
the deletion-even-on-abort rule is stated. I confirmed the directory is absent
and `git status --porcelain -- frontend/src/test/` is empty. Because the shipped
run passes the leaking case, a configuration is proposed, quoted in full, and the
probe is re-run under a scratchpad config carrying it: `Tests 2 failed (2)`, each
failure naming its case, with the consume-the-error caveat disclosed.
`<scratchpad>/fail-on-leak.setup.ts` and `vitest.proposal.config.ts` exist as
described, and `leaks.control.jsonl` holds exactly the two quoted JSON lines
while `leaks.jsonl` is absent, as the document says. **Limitation:** I could not
re-execute the probe myself — doing so requires writing a file under
`frontend/src/`, which my own hard constraints forbid. I verified it as far as
read-only verification allows: the removal, the coverage-exclusion claim
(`coverage.exclude` really does contain `"src/test/**"` in the shipped config),
every retained artefact, and the surrounding configuration claims. Nothing I
could check diverged.

**R15 — PASS.** `frontend/vitest.config.ts` is unmodified (`git diff` empty).
`<scratchpad>/vitest.audit.config.ts` imports the shipped file and `mergeConfig`s
exactly one delta — `setupFiles` becomes a two-element array adding the
scratchpad recorder — plus `root`; I read both files and confirmed the diff is
that and nothing else. The bare-load outcome is recorded as observed, not
asserted: attempt 1 (no symlink, no `package.json`) failed with
`Cannot find module 'vitest/config'` / `UNRESOLVED_IMPORT`, quoted verbatim;
attempt 2 (symlink only) failed with the `@tailwindcss/vite` default-not-a-function
CJS-interop `TypeError`, quoted verbatim; attempt 3 loaded. Each remedy artefact
is named with the error that forced it, and both exist on disk with exactly the
described content (`node_modules` → `frontend/node_modules` symlink;
`package.json` = `{"type": "module"}`, 18 bytes), alongside
`<scratchpad>/preexisting/` holding the pre-existing copies the audit moved
aside, as described. I corroborated remedy 1 as genuinely load-bearing:
`require.resolve('vitest/config', {paths: [<scratchpad>/…]})` resolves through
the symlink, and the same call one directory above the scratchpad fails
`MODULE_NOT_FOUND` — which is the quoted attempt-1 error. The honoured-config
proof is recorded (the appended setup file made to throw; the run reporting that
error at `audit-recorder.setup.ts:41`; the throw then removed and the file
`cmp`-verified). The parity gate is recorded before any conclusion and **I ran it
myself**: 188 / 2503 on both invocations, and `diff` of the two sorted collected
file columns is empty. The spec's 188 / 2496 is cited alongside the audit's own
2503 with the explanation, and the verdict is an explicit "match", so the
instrumented findings are correctly reported as statements about the shipped
configuration.

**R16 — PASS.** The *Over-pins* table has **exactly 43 data rows**, which I
cross-checked against the 43 distinct S1 ledger targets: all 19 backend subset
members, all 21 frontend subset members, both `pytest.ini` declarations, and
`backend/app/core/security.py:27`. "Every member" is literally every member.
`backend/tests/test_bcrypt_cost.py` is covered by name, and the required
evidence is there: `S1-BE-BCRYPT_ROUNDS-prod-13` raises `BCRYPT_ROUNDS` from 12
to 13 and the module stays green, with the pre-existing `passlib` failure
excluded as evidence. The document explicitly declines to call that module's
source anchor or floor assertion defects, and I verified both statements against
the live source: `backend/app/core/security.py:27` is `BCRYPT_ROUNDS = 12`,
`test_bcrypt_cost.py:245` is
`assert f"BCRYPT_ROUNDS = {security.BCRYPT_ROUNDS}" in code`, and the ratchets at
lines 198 and 228 are `>= PRODUCTION_FLOOR`. The twenty members whose
slack-direction move reddens are listed (I counted 20 bullets) and each is
adjudicated — nineteen as equality or deliberate two-sided pins doing their job,
`GRAPHIC_FLOOR` as the one informative case, pointing at F-01 rather than at an
over-pin. The `S1-CFG-pytest_timeout-strong` asymmetry is recorded as a measured
observation and handed to FU-08.

**R17 — PASS.** The doubled-flag banner is quoted and I reproduced it
byte-for-byte, including all three plugin lines (`pytest-cov-7.1.0`,
`pytest-timeout-2.4.0`, `anyio-4.14.2`) and their paths. The document's stated
reason for the doubled flag is correct: a single `--version` prints only
`pytest 9.1.1` on my run, with no banner. The Vitest version line
(`vitest/4.1.11 darwin-arm64 node-v24.13.0`) also reproduces. The absence of an
order randomiser is read off that banner and used to justify carrying
`-p no:randomly` with no `--randomly-seed`, which is consistent.

**R18 — PASS.** 16 proposals, one per remediation cluster, each naming the tests
or code it covers, their class, and the baseline it must report against (and the
preamble repeats the three baseline numbers plus the line-by-line rule). The
three specifically required members are present: **FU-03** for the deferred
anonymous-numeric-assertion population (1674 + 454, by the pinned commands),
**FU-12** for the ER8 configuration change, and **FU-01** for the environment
drift found by the `Environment` subsection, which the proposal text states
explicitly is a follow-up and not part of this audit. No finding is left without
a follow-up: F-01–F-16 map onto FU-07 through FU-11.

---

## Blocking findings

### 1. (R3) All 99 baseline-reusing rows record a dependency comparison whose stated command does not produce the stated output

R3 requires that a reused baseline's row "names the interim `uv pip freeze`
capture taken at reuse time **and its comparison against `freeze.before`**". All
99 reuse rows do name the capture, and all 99 report the comparison like this
(`S1-BE-PRODUCTION_FLOOR-strong`, and 98 others verbatim):

```
(c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i01`,
compared against `freeze.before`: **empty**.
```

`grep -c 'compared against `freeze.before`: \*\*empty\*\*'` → **99**.
`grep -c 'compared against `freeze.before2`'` → **0**.

Run against the audit's own retained captures, that comparison is **not empty**,
for every single one:

```
$ diff <scratchpad>/freeze.before <scratchpad>/freezes/freeze.i01
40c40
< sqlmodel==0.0.38
---
> sqlmodel==0.0.47

$ shasum -a 256 <scratchpad>/freeze.before <scratchpad>/freeze.before2
3a41fd8afa5091cecd57851f0976ba0a7c99466ddb5b4f99433cf561f5b986b7  …/freeze.before
cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75  …/freeze.before2
```

I checked all 99: **99 / 99 interim captures differ from `freeze.before`** and
**0 / 99 differ from `freeze.before2`**. The correct reference is
`freeze.before2` — which the document's own `Environment` subsection designates:
"A stabilised capture was then taken as `freeze.before2`, which is the capture
every ledger row is measured against." So the ledger rows contradict the
method section, 99 times, and the contradiction is in the direction that makes a
non-empty diff read as empty.

Why this is blocking rather than cosmetic. This deliverable's entire subject is
an evidence line that does not hold up when you run it. Here the evidence line is
`diff <scratchpad>/freeze.before <scratchpad>/freezes/freeze.iNN` → empty, and it
is false on every row that carries it. R5's staleness mechanism is driven by
exactly that comparison ("a non-empty diff marks every row whose step-0 baseline
predates the observed change as `baseline stale`"), so a row asserting emptiness
against a reference that is genuinely non-empty misreports the one guard that
decides whether its own baseline is usable.

I want to be precise about what is **not** wrong, because the remedy is small.
The substantive conclusion is correct and independently verified: all 183 freeze
captures in `<scratchpad>/freezes/` carry the single fingerprint
`cb629948…6e6e75`, `freeze.before2` and `freeze.after` are byte-identical, and
the one `sqlmodel` re-sync happened before the first mutation and before every
baseline, so no row is stale. Nothing in the ledger's measurements is affected
and no finding depends on this. The fix is to name `freeze.before2` on the 99
rows (or to keep `freeze.before` and record the known one-line `sqlmodel` delta
instead of "empty").

Two counting errors travel with it and should be fixed in the same pass:

- Line 167–168: "**96** interim captures (`freeze.i01` … `freeze.i96`)". There
  are **99**: `ls <scratchpad>/freezes/freeze.i*` → 99 files, `freeze.i01`
  through `freeze.i99`, each referenced by exactly one row and none unreferenced.
- Line 298: "**96** of the 183 rows reuse a baseline run". It is **99**. The
  arithmetic also only closes at 99: 84 own-baseline rows + 99 reuse rows = 183
  rows, and there are exactly 84 `freeze.B-NN` files and 84 distinct `B-NN`
  identifiers.

---

## Suggestions (non-blocking)

1. The backend coverage figure in *Coverage and lint baselines* reads
   `TOTAL 11716 668 94%` / `94.30%`; my own run of the same command gave
   `11716 667 94%` / `94.31%`, with identical test, skip, warning and exit
   results. One statement in ~11.7k is run-to-run variance, but since every
   follow-up must report against this number, it would be worth noting that the
   figure is ±1 statement rather than exact.
2. S2 and S4 print a selected `file:line` table; S3 prints `N`, `k` and the
   stride but leaves the 40 selections to be read off the ledger rows. They are
   all there and I reproduced 40/40 from the enumeration, so reproducibility is
   not actually impaired — but a short S3 selection table would make the three
   strata symmetric and spare the next reader the parse I had to write.
3. The S2 frontend stride table writes slot 9 as
   `…/TenantBrandColors.tsx:237` → text at `:357`. Since `237` there is the
   stride *index* and every other cell in that column is a `file:line`, the
   notation invites exactly the misreading I made on first pass. `idx 237 →
   TenantBrandColors.tsx:357` would read unambiguously.

---

## What I could not verify

One item, stated plainly: I did not re-execute the transient leak probe's two
shipped-config invocations (R14), because creating
`frontend/src/test/__audit_probe__/leak.test.ts` would modify the working tree,
which my instructions forbid. I verified everything around it instead — the
probe's verified absence today, `git status --porcelain -- frontend/src/test/`
empty, the `coverage.exclude: ["src/test/**"]` claim against the shipped config,
the retained `<scratchpad>/probe.out` containing both invocations with exactly
the quoted `Test Files 1 passed (1)` / `Tests 2 passed (2)` / `Errors 2 errors` /
`exit=1` shape, `leaks.control.jsonl` matching its two quoted lines verbatim, and
`leaks.jsonl` absent as documented. Nothing diverged, but the two runs themselves
rest on the audit's artefacts rather than on my own execution.

Everything else in the eighteen expected results was checked by observation of
the live system, by re-running the document's commands, or by a parser over the
document cross-checked against the repository and the retained artefacts.

---

VERDICT: REJECTED

1. **R3** — All 99 baseline-reusing ledger rows state
   "interim … `freeze.iNN`, compared against `freeze.before`: **empty**", but
   `diff <scratchpad>/freeze.before <scratchpad>/freezes/freeze.iNN` is non-empty
   for 99/99 (one line: `sqlmodel==0.0.38` → `sqlmodel==0.0.47`); the comparison
   is empty only against `freeze.before2`, which the document's own `Environment`
   subsection names as the reference every row is measured against. The stated
   command does not produce the stated output, on every row that carries it.
   Travelling with it: the prose count of interim captures and baseline-reusing
   rows is given as **96** at lines 167–168 and 298, but there are **99** of each
   (84 own-baseline + 99 reuse = the 183 rows). No measurement or finding is
   affected — all 183 freeze captures share one fingerprint and
   `freeze.before2` == `freeze.after` — so the repair is to rename the reference
   (or record the known one-line delta) and correct 96 → 99.
