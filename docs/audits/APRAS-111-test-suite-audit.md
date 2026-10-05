# APRAS-111 — Test-suite audit: tests that prove nothing

**Measured on 2026-10-02**, on `master` at local `HEAD` `2cb0d48`, in the
worktree `/Users/heitor/workspace/apras`. Session scratchpad:
`/private/tmp/claude-501/-Users-heitor-workspace-apras/06230b8a-d0ef-40dd-929b-83bb4eb6abbf/scratchpad`
(written below as `<scratchpad>`).

This audit **changed no test file and no production file**. It is the deliberate
sweep for the defect this project has hit nineteen times one accident at a time:
a test whose prose claims a guarantee no assertion holds. It also sweeps for a
second species — a test that reddens when the code moves in the direction its
own contract allows (an *over-pin*).

183 mutations were performed under the seven-step protocol, across 84 step-0
baseline runs. Every row carries its own line-scoped read-back, its step-0
baseline, the cases it reddened against that baseline, and a restore checksum
pair. There were **zero aborts**, **zero `cmp` mismatches** and **zero files
skipped for uncommitted work**.

This audit is **manual and targeted**. It adopts no mutation-testing tool
(`mutmut`, Stryker); adopting one is its own deliverable and is listed as a
follow-up.

---

## Census and method

### Totals collected

| Suite | Command | Collected |
|---|---|---|
| backend | `cd backend && SECRET_KEY=test uv run pytest --collect-only -q --no-cov` | **4195 tests collected in 0.50s** |
| frontend | `cd frontend && npx vitest list` | **188 files / 2503 cases** |

The spec recorded 4181 backend cases and 188 files / 2496 frontend cases as
measured on 2026-10-01. The counts above are this audit's own measurement, one
day later: +14 backend cases and +7 frontend cases, from other tasks' work in
this shared worktree.

### Versions and the plugin banner

`cd backend && SECRET_KEY=test uv run pytest --version --version` — the doubled
flag, because a single `--version` prints only `pytest 9.1.1` and no banner at
all:

```
This is pytest version 9.1.1, imported from /Users/heitor/workspace/apras/backend/.venv/lib/python3.13/site-packages/pytest/__init__.py
registered third-party plugins:
  pytest-cov-7.1.0 at /Users/heitor/workspace/apras/backend/.venv/lib/python3.13/site-packages/pytest_cov/plugin.py
  pytest-timeout-2.4.0 at /Users/heitor/workspace/apras/backend/.venv/lib/python3.13/site-packages/pytest_timeout.py
  anyio-4.14.2 at /Users/heitor/workspace/apras/backend/.venv/lib/python3.13/site-packages/anyio/pytest_plugin.py
```

Three registered third-party plugins — `pytest-cov`, `pytest-timeout`, `anyio`
— and **no order randomiser**. `-p no:randomly` is therefore harmless here and
is carried on every backend ledger row anyway, as the spec requires; no
`--randomly-seed` is recorded because no randomiser is active.

Vitest version line, from `cd frontend && npx vitest --version`:

```
vitest/4.1.11 darwin-arm64 node-v24.13.0
```

### Why every backend ledger command carries `--no-cov`

`backend/pytest.ini` line 4 is `addopts = --cov=app --cov-fail-under=90`. A
narrow per-module run inherits it and ends
`FAIL Required test coverage of 90% not reached. Total coverage: …`, exiting
non-zero **whatever the tests did** — which would make the exit code, the thing
a ledger reads as "reddened", meaningless. Every backend ledger command in this
document therefore carries `--no-cov`. The only exception is the full-suite
baseline in *Coverage and lint baselines*, which keeps the gate because
measuring it is the point.

The canonical backend ledger shape used throughout is

```
cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf <path>
```

`-q --tb=no -rf` are reporting flags only: `-rf` is what makes the ledger able
to quote a *pass/fail set* rather than a count, which is what "reddened relative
to the step-0 baseline" is computed from.

Frontend rows pin a single spec path (or, where stated, one directory) and are
run as

```
cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/<row>.json <path>
```

### Environment

`uv pip freeze` (read-only) finds **`passlib==1.7.4` installed in
`backend/.venv`**, and `backend/pyproject.toml` does not declare it: the
bcrypt 5 bump removed the dependency and this local venv was never resynced.
CI does a fresh `uv sync --all-groups` and is green. This is **local
environment drift, not a repository defect**, and it is the cause of the one
case this checkout fails before the audit touches anything:

```
cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_bcrypt_cost.py
FAILED tests/test_bcrypt_cost.py::test_passlib_is_not_installed - AssertionError
1 failed, 9 passed, 1 warning in 1.93s
```

`test_passlib_is_not_installed` **is** among the pre-mutation failures. Its
cause is stated above: `passlib 1.7.4` installed in `backend/.venv` while not
declared in `backend/pyproject.toml` — local environment drift, CI green. The
`passlib` line of `freeze.before` reads `passlib==1.7.4`. Repairing the drift is
**follow-up FU-01**, not part of this audit: the case is excluded from the
evidence of every row whose baseline shows it, and no row uses it to support any
finding.

Complete list of cases found failing or not-green pre-mutation, over the 84
baseline runs:

| Case / module | Command that showed it | Attributed cause |
|---|---|---|
| `tests/test_bcrypt_cost.py::test_passlib_is_not_installed` | `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_bcrypt_cost.py` | declared-dependency drift (`passlib` installed, undeclared); CI green |
| `tests/test_migrations_postgres.py` — **all 38 cases skipped**, baseline summary line `38 skipped, 1 warning in 0.07s` | `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_migrations_postgres.py` | `pytestmark = pytest.mark.skipif(...)` at line 109: no live Postgres on this machine. Not green ⇒ not examinable; substituted per the selection rule |

No other case failed in any step-0 baseline.

**The audit ran no `uv sync`, no `uv pip install`, no `uv pip uninstall`, no
`npm install` and no `npm ci`.** One unavoidable qualification, recorded because
the spec's own detection mechanism caught it: the *first* `uv run pytest` of the
session — a command the spec mandates — caused `uv` to re-sync one package to
the lockfile pin on its own:

```
$ diff <scratchpad>/freeze.before <scratchpad>/freeze.chk1
40c40
< sqlmodel==0.0.38
---
> sqlmodel==0.0.47
```

This happened **before the first mutation**, and `uv run` is the invocation the
spec prescribes; the audit did not choose it. A stabilised capture was then
taken as `freeze.before2`, which is the capture every ledger row is measured
against, and every subsequent `uv run` left it unchanged. All 84 baseline-run
freeze fingerprints are byte-identical to it.

**Which capture is the reference, and where the one delta falls.**
`freeze.before` was taken before that re-sync, so it predates the `sqlmodel`
upgrade and is the *only* capture in this audit that reads
`sqlmodel==0.0.38`. `freeze.before2` is the post-upgrade capture, taken after
the re-sync and **before the first mutation**; it reads `sqlmodel==0.0.47`, and
it is the capture every ledger row — its step-0 baseline fingerprint
`freeze.B-NN` and its interim reuse capture `freeze.iNN` alike — is measured
against. The entire difference between the two captures is the single line
quoted above:

```
40c40
< sqlmodel==0.0.38
---
> sqlmodel==0.0.47
```

That delta therefore lies **outside** every row's measured window: it had
already happened when `freeze.before2` was taken, and no row's window opens
earlier than `freeze.before2`. This is why no row is marked `baseline stale —
environment changed mid-audit` even though a dependency did change during the
session: the rule marks a row stale when a comparison inside its own window is
non-empty, and every such comparison here is empty against `freeze.before2`
(all 183 captures in `<scratchpad>/freezes/` carry the one fingerprint
`cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`, and
`freeze.before2` and `freeze.after` are byte-identical). Measured against
`freeze.before` instead, every one of those 183 captures differs by exactly the
line above — which is what the staleness rule would have fired on had the
re-sync landed after any baseline rather than before all of them.

### Dependency-set snapshot

```
$ shasum -a 256 <scratchpad>/freeze.before2 <scratchpad>/freeze.after
cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75  <scratchpad>/freeze.before2
cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75  <scratchpad>/freeze.after

$ diff <scratchpad>/freeze.before2 <scratchpad>/freeze.after
$ echo $?
0
```

**The diff is empty.** That is the positive record the spec asks for: every row
was measured against the one installed dependency set step 0 measured. No row is
marked `baseline stale — environment changed mid-audit`.

Per-baseline-run fingerprints: each of the **84** baseline runs captured its own
read-only `cd backend && uv pip freeze` into `<scratchpad>/freezes/freeze.B-NN`
and recorded its `shasum -a 256`. **All 84 are
`cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`** — one
distinct fingerprint across the whole audit, so no two consecutive baseline runs
differ and no row is marked stale on that ground either. **99** interim
captures (`freeze.i01` … `freeze.i99`) were taken at reuse time, one per
baseline-reusing row, each compared against `freeze.before2`; every comparison
came back empty, and each row names its own capture.

`freeze.before2`, quoted in full as the record of what was installed:

```
alembic==1.20.0            annotated-doc==0.0.4        annotated-types==0.7.0
anyio==4.14.2              bcrypt==5.0.0               certifi==2026.2.25
click==8.3.2               coverage==7.13.5            deprecated==1.3.1
dnspython==2.8.0           email-validator==2.3.0      fastapi==0.141.1
h11==0.16.0                httpcore==1.0.9             httpx==0.28.1
idna==3.18                 iniconfig==2.3.0            limits==5.8.0
mako==1.3.12               markupsafe==3.0.3           packaging==26.1
passlib==1.7.4             pillow==12.3.0              pluggy==1.6.0
psycopg2-binary==2.9.13    pydantic==2.13.3            pydantic-core==2.46.3
pydantic-settings==2.15.0  pygments==2.20.0            pyjwt==2.15.0
pytest==9.1.1              pytest-cov==7.1.0           pytest-timeout==2.4.0
python-dotenv==1.2.2       python-multipart==0.0.32    qrcode==8.2
ruff==0.16.9               slowapi==0.1.10             sqlalchemy==2.0.49
sqlmodel==0.0.47           starlette==1.3.1            typing-extensions==4.15.0
typing-inspection==0.4.2   uvicorn==0.54.0             wrapt==2.1.2
zxing-cpp==3.1.1
```

(One package per line in the file; reflowed into columns here for width only.)

### The tree-safety contract, and its result

```
$ git status --porcelain --untracked-files=all > <scratchpad>/porcelain.before   # before the first mutation
$ git status --porcelain --untracked-files=all > <scratchpad>/porcelain.after    # after the last restore
$ diff <scratchpad>/porcelain.before <scratchpad>/porcelain.after
$ echo $?
0
$ comm -13 <(sort <scratchpad>/porcelain.before) <(sort <scratchpad>/porcelain.after) | grep -E "backend/|frontend/"
$ echo $?
1
```

**The diff is empty, and no entry under `backend/` or `frontend/` appears in the
second capture that was absent from the first.** `porcelain.before` and
`porcelain.after` are byte-identical, 43 lines each:

```
 M docs/suggestions-log.md
?? backend/scripts/sync_obras_from_drive.py
?? docs/reviews/APRAS-102-spec-review-round2.md
?? docs/reviews/APRAS-102-spec-review-round3.md
?? docs/reviews/APRAS-102-spec-review-round4.md
?? docs/reviews/APRAS-102-spec-review.md
?? docs/reviews/APRAS-102-spec-revision-round3.md
?? docs/reviews/APRAS-121-spec-review-round2.md
?? docs/reviews/APRAS-121-spec-review-round3.md
?? docs/reviews/APRAS-121-spec-review-round4.md
?? docs/reviews/APRAS-121-spec-review.md
?? docs/reviews/APRAS-121-spec-revision-round3.md
?? docs/reviews/APRAS-122-spec-review-round2.md
?? docs/reviews/APRAS-122-spec-review-round3.md
?? docs/reviews/APRAS-122-spec-review-round4.md
?? docs/reviews/APRAS-122-spec-review-round5.md
?? docs/reviews/APRAS-122-spec-review.md
?? docs/reviews/APRAS-123-spec-review-round2.md
?? docs/reviews/APRAS-123-spec-review-round3.md
?? docs/reviews/APRAS-123-spec-review-round4.md
?? docs/reviews/APRAS-123-spec-review-round5.md
?? docs/reviews/APRAS-123-spec-review.md
?? docs/reviews/APRAS-91-qa-review.md
?? docs/reviews/APRAS-97-spec-review.md
?? docs/reviews/APRAS-98-spec-review-round3.md
?? docs/reviews/APRAS-98-spec-review-round4.md
?? docs/reviews/APRAS-98-spec-review-round5.md
?? docs/tasks/APRAS-100-mock.html
?? docs/tasks/APRAS-100-spec.md
?? docs/tasks/APRAS-102-mock.html
?? docs/tasks/APRAS-102-spec.md
?? docs/tasks/APRAS-111-spec.md
?? docs/tasks/APRAS-118-mock.html
?? docs/tasks/APRAS-118-spec.md
?? docs/tasks/APRAS-119-spec.md
?? docs/tasks/APRAS-121-spec.md
?? docs/tasks/APRAS-122-spec.md
?? docs/tasks/APRAS-123-spec.md
?? docs/tasks/APRAS-82-mock.html
?? docs/tasks/APRAS-93-spec.md
?? docs/tasks/APRAS-97-spec.md
?? docs/tasks/APRAS-98-mock.html
?? docs/tasks/APRAS-98-spec.md
```

`?? backend/scripts/sync_obras_from_drive.py` is present in **both** captures.
It is deliberately never committed and was not touched. The uncommitted
`docs/tasks/*`, `docs/reviews/*` and `docs/suggestions-log.md` entries belong to
other tasks and are recorded here, as the spec requires, without failing the
check. This document itself (`docs/audits/APRAS-111-test-suite-audit.md`) is
written after `porcelain.after` was captured and so is the one expected new
`docs/` entry.

`git stash`, `git checkout`, `git restore` and line-numbered `sed` restores were
**not used at any point**. Every restore was a `cp` back from a scratchpad copy,
`cmp`-verified, with the checksum pair recorded on the row.

### The mutation protocol as executed

Seven steps (0–6) per mutation, all seven recorded on every row:

0. **Pre-mutation baseline.** The *same* order-pinned command, on the unmutated
   file, with its full pass/fail set recorded, plus its own read-only
   `uv pip freeze` fingerprint. **"Reddened" means green in step 0 and failing
   in step 3, and nothing else.** A case already failing in step 0 is recorded
   under *Not examined — already failing pre-mutation* with its failure line
   quoted, and is never evidence for or against any finding.
1. Assert `git status --porcelain -- <file>` is empty, then snapshot by `cp`
   into `<scratchpad>/snap/` and record the pristine copy's `shasum -a 256`.
2. **Verify the mutation took, line-scoped.** `sed -n '<line>p'` on the pristine
   scratchpad copy and on the file on disk; both outputs quoted on the row; the
   two must differ and the second must equal the intended text. The driver
   aborts the row before running anything if they do not. **No file-scoped
   emptiness assertion appears anywhere in this ledger** — it would be
   unsatisfiable for a correct mutation whenever the mutated text recurs
   elsewhere in the file, which is the common case in S3.
3. Run the narrowest order-pinned command covering the case under examination
   **plus its module**, so that a mutation reddening a *neighbour* instead of
   the named case shows up.
4. Record which mutation, which command, the step-0 set, what reddened against
   it, and whether the case under examination was among them.
5. Restore by `cp` back and verify byte-identity with `cmp`; record the
   checksum pair.
6. On a `cmp` mismatch: abort, do not re-restore. **No mismatch occurred.**

**Baseline reuse.** 99 of the 183 rows reuse a baseline run within the same
module in the same session. Each such row names the run it reuses (`B-NN`) and
re-asserts the three conditions: its own `git status --porcelain -- <file>` was
empty at snapshot; every `cmp` since that baseline came back clean; and an
**interim** read-only `cd backend && uv pip freeze` taken at reuse time
(`freeze.iNN`, named on the row) compared empty against `freeze.before2`. No row
pastes shared baseline text without naming the run.

**Two carried rules.** Where a test names a field, the field's value was mutated
as well as the guard (S2-BE-04/-04b, S2-BE-11, S1 equality pins). Every S1
threshold-subset member carries **both** a weakening and a strengthening
mutation.

### How a frontend row's run summary is counted — and a correction to it

Every frontend ledger row (and every frontend baseline run) is driven by
`npx vitest run --reporter=json --outputFile=<scratchpad>/runs/<id>.json <spec>`,
and the row's summary `N tests: P passed, F failed (files M)` is read out of that
JSON file. The three case figures come from `numTotalTests`, `numPassedTests` and
`numFailedTests`. **`M` is `len(testResults)`** — the number of spec *files* the
run collected, which is the figure `npx vitest run` prints as
`Test Files M passed (M)`.

**The figure originally recorded for `M` was wrong, and this section records the
defect rather than hiding the repair.** The first version of this ledger read `M`
from the JSON reporter's **`numTotalTestSuites`**, which counts `describe`
blocks, not files. The two are unrelated numbers that happen to coincide only for
a single-file spec with no `describe` nesting. Measured on
`src/features/user-administration/__tests__/Navbar.test.tsx`:

```
numTotalTestSuites : 3   <- describe blocks
len(testResults)   : 1   <- spec files
numTotalTests      : 30
```

and on the F-13 directory run (`S2-FE-10b` / baseline `B-47`):
`numTotalTestSuites = 134` against `len(testResults) = 51`, while the same path
re-run without the JSON reporter prints

```
$ cd frontend && npx vitest run src/features/user-administration/__tests__
 Test Files  51 passed (51)
      Tests  513 passed (513)
```

So the figure was wrong by 2.6× on that row. No finding's class, verdict or
evidence depended on it — the case counts, which carry every "reddened" claim,
were read from the correct fields and are unchanged — but the mislabel broke the
one property this deliverable is proved by: a reviewer re-running a row could not
tell a mislabelled column from a row that fails to reproduce.

**What was re-derived, and how.** Every one of the 186 frontend run summaries in
the ledger (93 step-0 baseline quotations and 93 step-3 mutated runs) had its `M`
recomputed from `len(testResults)` in that row's own retained
`<scratchpad>/runs/<id>.json`, matched to the row by id and to the baseline by
the `B-NN` it names. Before rewriting, each line's three case figures were
checked against `numTotalTests` / `numPassedTests` / `numFailedTests` in the same
JSON, so the row-to-artefact mapping is proved rather than assumed: **all 186
matched exactly**, and all 186 printed `M` equalled that JSON's
`numTotalTestSuites`, confirming the single mechanical cause. 183 figures
changed; 3 were already correct (`S4-FE-04`, `-08`, `-10`, whose invalidated runs
collected one file and zero cases). **No mutation was repeated** to recompute a
column that was already captured, and no row's recorded command changed — so
every row still reproduces, now against a figure that is what the runner prints.
Three rows were additionally re-run bare as an independent check of the retained
artefacts:

```
$ cd frontend && npx vitest run src/__tests__/themeContrast.test.ts
 Test Files  1 passed (1)
      Tests  12 passed (12)
$ cd frontend && npx vitest run src/lib/__tests__/contrast.test.ts
 Test Files  1 passed (1)
      Tests  36 passed (36)
$ cd frontend && npx vitest run src/features/access-control/__tests__/AccessControlPage.test.tsx
 Test Files  1 passed (1)
      Tests  4 passed (4)
```

matching rows `S1-FE-MINIMUM_*` (`files 1`, 12 cases), `B-15`/
`S1-FE-MINIMUM_CONTRAST_RATIO-*` (`files 1`, 36 cases) and `B-80`/`S4-FE-04r`
(`files 1`, 4 cases), where the ledger previously printed `files 3`, `files 11`
and `files 2`. Every frontend row's command pins exactly one spec path, which is
why `M = 1` on all of them; the two exceptions are the directory-wide `S2-FE-10b`
and its baseline `B-47`, at `M = 51`.

**`numTotalTestSuites` is now used nowhere in this document.** Describe-block
counts are not quoted on any row, because no claim here is about describe blocks
and a second count beside the file count is exactly what caused the confusion.
It appears only in this subsection, labelled as describe blocks, as the record of
what the superseded figure measured.

The suite-wide **188 files** figure elsewhere in this document is *not* affected:
it comes from `npx vitest list` and from `Test Files 188 passed (188)`, both of
which count files.

### Strata, enumeration, budgets, strides, remainder

Every enumeration command below is reproduced **verbatim from the spec** and was
run from the repository root under `LC_ALL=C`, piped through `LC_ALL=C sort`.

#### S1 — named thresholds, floors, caps and limits (exhaustive over a printed denominator)

```
LC_ALL=C grep -rnE '\b[A-Z][A-Z0-9_]{3,}\b[[:space:]]*(=|==|>=|<=)[[:space:]]*[0-9]+' \
  backend/tests --include='*.py' | LC_ALL=C sort
LC_ALL=C grep -rnE '\b[A-Z][A-Z0-9_]{3,}\b[[:space:]]*(=|==|>=|<=|:)[[:space:]]*[0-9]+' \
  frontend/src --include='*.ts' --include='*.tsx' | LC_ALL=C sort
```

Candidate-set sizes **as measured by this audit**: backend **62** lines (spec
recorded 60 on 2026-10-01), frontend **50** lines (spec recorded 50). Plus the
config-declared thresholds, enumerated by file: `backend/pytest.ini`
(`--cov-fail-under` at line 4, `timeout` at line 17) and
`frontend/vitest.config.ts` (`test.coverage.thresholds` at lines 41–46).

The triage tables below reduce each candidate set to its **threshold subset**;
every excluded line carries a reason. "Exhaustive" means exactly this: the
candidate set from the commands above, minus the printed exclusions.

- backend: N = 62 → threshold subset **19**, excluded **43**
- frontend: N = 50 → threshold subset **21**, excluded **29**
- config: 3 declarations → **2** mutated (`pytest.ini`'s two), **1** judged
  read-only and not mutated: `frontend/vitest.config.ts`'s
  `test.coverage.thresholds`, excluded because expected result 14 of this task
  requires that `frontend/vitest.config.ts` is not modified. Read-only
  judgement: `LC_ALL=C grep -rln "vitest.config" frontend/src` returns two files
  (`src/features/user-administration/__tests__/Navbar.test.tsx` and
  `src/features/project-management/__tests__/fixtures/obraReportFixture.ts`),
  both mentioning the filename in prose and neither parsing the file, so **no
  case pins the frontend coverage thresholds**. With no mutation behind it this
  is not listed as a finding; it is handed to **FU-02**.

Anonymous numeric assertions — **counted, not mutated**, and deferred by name to
**FU-03**:

```
$ LC_ALL=C grep -rnE '^[[:space:]]*assert .*(==|>=|<=|<|>)[[:space:]]*[0-9]+' \
    backend/tests --include='*.py' | wc -l
1674
$ LC_ALL=C grep -rnE 'toBe(GreaterThan|LessThan|GreaterThanOrEqual|LessThanOrEqual)?(Equal)?\([0-9]+\)|toHaveLength\([0-9]+\)' \
    frontend/src --include='*.ts' --include='*.tsx' | wc -l
454
```

`backend/tests/test_bcrypt_cost.py` is a mandatory S1 member and is in the
subset. As the spec requires, this audit does **not** describe its source anchor
or its floor assertion as defects: as of 2026-10-01 the anchor is
`assert f"BCRYPT_ROUNDS = {security.BCRYPT_ROUNDS}" in code` and the ratchet is
`>= PRODUCTION_FLOOR`, not an equality on 12. What the audit did instead is
prove the ratchet ratchets — row `S1-BE-BCRYPT_ROUNDS-prod-13` raises
`app/core/security.py`'s `BCRYPT_ROUNDS` from 12 to 13 and the module stays
green. See *Over-pins*.

##### S1 backend triage table
| # | candidate `file:line` | text | in threshold subset? | reason if excluded |
|---|---|---|---|---|
| 1 | `backend/tests/test_assert_no_skips.py:40` | `SUBPROCESS_TIMEOUT = 120` | no | subprocess plumbing timeout for the harness's own `uv run` child, not a product bound |
| 2 | `backend/tests/test_assert_no_skips.py:41` | `CLI_TIMEOUT = 60` | no | CLI plumbing timeout, same reason |
| 3 | `backend/tests/test_bcrypt_cost.py:54` | `PRODUCTION_FLOOR = 12` | **yes** | — |
| 4 | `backend/tests/test_bcrypt_cost.py:57` | `TEST_ROUNDS = 4` | no | fixture cost for this process, not a bound |
| 5 | `backend/tests/test_clock.py:113` | `DATED_COLUMN_FLOOR = 100` | **yes** | — |
| 6 | `backend/tests/test_clock.py:62` | `TOLERANCE_SECONDS = 1` | no | comparison tolerance on a clock read, not a ratcheted bound |
| 7 | `backend/tests/test_infractions.py:1196` | ``NewInfractionModal.tsx` exports `LOT_SELECT_LIMIT = 100` and asks` | no | prose inside a docstring quoting a frontend constant; not a declaration |
| 8 | `backend/tests/test_lint_hygiene.py:122` | `assert NOQA_CAP <= 108, "APRAS-54's ceiling; a rise needs its own task"` | **yes** | — |
| 9 | `backend/tests/test_lint_hygiene.py:57` | `NOQA_CAP = 72` | **yes** | — |
| 10 | `backend/tests/test_permission_alignment.py:152` | `EXPECTED_DEPENDENCY_FORM = 56` | no | exact census count (`EXPECTED_*_FORM`), an equality over a measured population rather than a bound |
| 11 | `backend/tests/test_permission_alignment.py:154` | `EXPECTED_SUPERUSER_FORM = 5` | no | exact census count |
| 12 | `backend/tests/test_permission_alignment.py:156` | `EXPECTED_MEMBERSHIP_FORM = 3` | no | exact census count |
| 13 | `backend/tests/test_permission_alignment.py:158` | `EXPECTED_SERVICE_FORM = 5` | no | exact census count |
| 14 | `backend/tests/test_permission_alignment.py:160` | `EXPECTED_IN_HANDLER_FORM = 141` | no | exact census count |
| 15 | `backend/tests/test_permission_enforcement.py:513` | `assert RULE_C_BASELINE == 100` | no | census equality re-asserted (`RULE_C_BASELINE`), not a bound |
| 16 | `backend/tests/test_permission_enforcement.py:514` | `assert RULE_N_BASELINE == 7` | no | census equality re-asserted, not a bound |
| 17 | `backend/tests/test_permission_enforcement.py:515` | `assert CONVERTED_COMPARE == 100` | no | census equality re-asserted, not a bound |
| 18 | `backend/tests/test_permission_enforcement.py:516` | `assert CONVERTED_NON_COMPARE == 7` | no | census equality re-asserted, not a bound |
| 19 | `backend/tests/test_permission_enforcement.py:517` | `assert RULE_C_BASELINE - CONVERTED_COMPARE == 0` | no | arithmetic identity between two census counts, not a bound |
| 20 | `backend/tests/test_permission_enforcement.py:518` | `assert RULE_N_BASELINE - CONVERTED_NON_COMPARE == 0` | no | arithmetic identity between two census counts, not a bound |
| 21 | `backend/tests/test_permission_enforcement.py:74` | `RULE_C_BASELINE = 100` | no | census count declaration, not a bound |
| 22 | `backend/tests/test_permission_enforcement.py:75` | `RULE_N_BASELINE = 7` | no | census count declaration, not a bound |
| 23 | `backend/tests/test_permission_enforcement.py:79` | `CONVERTED_COMPARE = 100` | no | census count declaration, not a bound |
| 24 | `backend/tests/test_permission_enforcement.py:81` | `CONVERTED_NON_COMPARE = 7` | no | census count declaration, not a bound |
| 25 | `backend/tests/test_permission_parity_matrix.py:103` | `F2_CELL_COUNT = 1080` | no | cell-count census (`F2_CELL_COUNT`), an exact size of a recorded matrix |
| 26 | `backend/tests/test_permission_parity_matrix.py:1046` | `assert meta["cell_count"] == APRAS_60_CELL_COUNT == 12` | no | cell-count census re-asserted |
| 27 | `backend/tests/test_permission_parity_matrix.py:104` | `APRAS_40_CELL_COUNT = 18` | no | cell-count census |
| 28 | `backend/tests/test_permission_parity_matrix.py:105` | `APRAS_44_CELL_COUNT = 108` | no | cell-count census |
| 29 | `backend/tests/test_permission_parity_matrix.py:1109` | `assert meta["cell_count"] == APRAS_61_CELL_COUNT == 18` | no | cell-count census re-asserted |
| 30 | `backend/tests/test_permission_parity_matrix.py:112` | `APRAS_51_CELL_COUNT = 150` | no | cell-count census |
| 31 | `backend/tests/test_permission_parity_matrix.py:115` | `APRAS_60_CELL_COUNT = 12` | no | cell-count census |
| 32 | `backend/tests/test_permission_parity_matrix.py:1163` | `assert meta["cell_count"] == APRAS_63_CELL_COUNT == 12` | no | cell-count census re-asserted |
| 33 | `backend/tests/test_permission_parity_matrix.py:120` | `APRAS_61_CELL_COUNT = 18` | no | cell-count census |
| 34 | `backend/tests/test_permission_parity_matrix.py:1238` | `assert meta["cell_count"] == APRAS_104_CELL_COUNT == 12` | no | cell-count census re-asserted |
| 35 | `backend/tests/test_permission_parity_matrix.py:126` | `APRAS_63_CELL_COUNT = 12` | no | cell-count census |
| 36 | `backend/tests/test_permission_parity_matrix.py:131` | `APRAS_104_CELL_COUNT = 12` | no | cell-count census |
| 37 | `backend/tests/test_permission_parity_matrix.py:1334` | `assert meta["cell_count"] == APRAS_51_CELL_COUNT == 150` | no | cell-count census re-asserted |
| 38 | `backend/tests/test_permission_parity_matrix.py:1416` | `assert len(overridden) == APRAS_51_CELL_COUNT == 150` | no | cell-count census re-asserted |
| 39 | `backend/tests/test_permission_parity_matrix.py:279` | `EXPECTED_REQUEST_BODY_COUNT = 104` | no | request-body census count, not a bound |
| 40 | `backend/tests/test_permission_parity_matrix.py:452` | `MAX_NON_ROLE_403 = 40` | **yes** | — |
| 41 | `backend/tests/test_permission_parity_matrix.py:453` | `MAX_PERMITTED_422 = 15` | **yes** | — |
| 42 | `backend/tests/test_permission_parity_matrix.py:873` | `assert meta["cell_count"] == F2_CELL_COUNT == 1080` | no | cell-count census re-asserted |
| 43 | `backend/tests/test_permission_parity_matrix.py:906` | `assert meta["cell_count"] == APRAS_40_CELL_COUNT == 18` | no | cell-count census re-asserted |
| 44 | `backend/tests/test_permission_parity_matrix.py:946` | `assert meta["cell_count"] == APRAS_44_CELL_COUNT == 108` | no | cell-count census re-asserted |
| 45 | `backend/tests/test_project_report_bar_geometry.py:124` | `MAX_GROWTH_MM = 6.0` | **yes** | — |
| 46 | `backend/tests/test_project_report_bar_geometry.py:75` | `PX_PER_MM = 96 / 25.4` | no | unit conversion (px per mm), a physical constant |
| 47 | `backend/tests/test_project_report_bar_geometry.py:76` | `PX_PER_PT = 96 / 72` | no | unit conversion (px per pt), a physical constant |
| 48 | `backend/tests/test_project_report_branding.py:100` | `GRAPHIC_FLOOR = 3.0` | **yes** | — |
| 49 | `backend/tests/test_project_report_branding.py:99` | `TEXT_FLOOR = 4.5` | **yes** | — |
| 50 | `backend/tests/test_project_report_escaping.py:182` | `ANALYSER_RULE_CASES = 12` | no | rule-count census of the analyser, not a bound |
| 51 | `backend/tests/test_project_report_escaping.py:187` | `ANALYSER_DISPATCH_RULES = 7` | no | dispatch-rule census, not a bound |
| 52 | `backend/tests/test_public_project_report.py:54` | `REQUESTS_PAST_THE_DECLINED_LIMIT = 31` | **yes** | — |
| 53 | `backend/tests/test_purchase_quote_attachment.py:482` | `assert PurchaseService.ATTACHMENT_MAX_FILE_SIZE == 5 * 1024 * 1024, (` | **yes** | — |
| 54 | `backend/tests/test_slug.py:92` | `assert SLUG_MIN_LENGTH == 3` | **yes** | — |
| 55 | `backend/tests/test_slug.py:93` | `assert SLUG_MAX_LENGTH == 64` | **yes** | — |
| 56 | `backend/tests/test_storage_blob.py:1093` | `assert storage_service.BLOB_MAX_READ_BYTES == 2 * 1024 * 1024` | **yes** | — |
| 57 | `backend/tests/test_storage_blob.py:1243` | `STRADDLE_OFFSET = 498` | no | fixture byte offset used to straddle a chunk boundary, not a bound |
| 58 | `backend/tests/test_storage_blob.py:1426` | `assert storage_service.BLOB_LOG_BODY_MAX_BYTES == 512` | **yes** | — |
| 59 | `backend/tests/test_suite_hygiene.py:293` | `DATED_SCHEMA_FLOOR = 70` | **yes** | — |
| 60 | `backend/tests/test_suite_hygiene.py:55` | `MAX_PER_TEST_TIMEOUT = 600` | **yes** | — |
| 61 | `backend/tests/test_tenant_profile.py:1166` | `assert TenantService.LOGO_MAX_FILE_SIZE == 2 * 1024 * 1024, (` | **yes** | — |
| 62 | `backend/tests/test_uploads.py:259` | `assert media_service_module.MAX_FILE_SIZE == 5 * 1024 * 1024, (` | **yes** | — |

Threshold subset (19 members), each with both directions in the ledger:
`test_bcrypt_cost.py:54 PRODUCTION_FLOOR`, `test_clock.py:113
DATED_COLUMN_FLOOR`, `test_lint_hygiene.py:57 NOQA_CAP`, `test_lint_hygiene.py:122`
(the ceiling on `NOQA_CAP`), `test_permission_parity_matrix.py:452
MAX_NON_ROLE_403`, `:453 MAX_PERMITTED_422`,
`test_project_report_bar_geometry.py:124 MAX_GROWTH_MM`,
`test_project_report_branding.py:99 TEXT_FLOOR`, `:100 GRAPHIC_FLOOR`,
`test_public_project_report.py:54 REQUESTS_PAST_THE_DECLINED_LIMIT`,
`test_purchase_quote_attachment.py:482 ATTACHMENT_MAX_FILE_SIZE`,
`test_slug.py:92 SLUG_MIN_LENGTH`, `:93 SLUG_MAX_LENGTH`,
`test_storage_blob.py:1093 BLOB_MAX_READ_BYTES`, `:1426
BLOB_LOG_BODY_MAX_BYTES`, `test_suite_hygiene.py:293 DATED_SCHEMA_FLOOR`, `:55
MAX_PER_TEST_TIMEOUT`, `test_tenant_profile.py:1166 LOGO_MAX_FILE_SIZE`,
`test_uploads.py:259 MAX_FILE_SIZE`.

##### S1 frontend triage table
| # | candidate `file:line` | text | in threshold subset? | reason if excluded |
|---|---|---|---|---|
| 1 | `frontend/src/__tests__/brandTextOpacity.test.ts:40` | `const DECIMALS = 3;` | no | rounding precision for the comparison, not a bound |
| 2 | `frontend/src/__tests__/brandTextOpacity.test.ts:42` | `const DELETED_ALPHA = 0.8;` | no | declared alpha of a specific token, a value under test rather than a bound |
| 3 | `frontend/src/__tests__/brandTextRole.test.ts:55` | `const DECIMALS = 3;` | no | rounding precision, not a bound |
| 4 | `frontend/src/__tests__/themeContrast.test.ts:172` | `const MINIMUM_PAIRS = 23;` | **yes** | — |
| 5 | `frontend/src/__tests__/themeContrast.test.ts:53` | `const MINIMUM_RATIO = 4.5;` | **yes** | — |
| 6 | `frontend/src/__tests__/themeContrast.test.ts:55` | `const EMITTED_SCALE = 100;` | no | emitted-percentage scale factor, an arithmetic constant |
| 7 | `frontend/src/__tests__/themeContrast.test.ts:58` | `const GAMUT_TOLERANCE = 1e-4;` | no | numeric tolerance for a gamut check, not a bound |
| 8 | `frontend/src/__tests__/themeContrast.test.ts:60` | `const CHROMA_STEP = 0.01;` | no | search step of the chroma walk, an algorithm parameter |
| 9 | `frontend/src/__tests__/themeContrast.test.ts:61` | `const LUMINANCE_OFFSET = 0.05;` | no | WCAG luminance offset, a formula constant |
| 10 | `frontend/src/__tests__/themeContrast.test.ts:62` | `const RED_WEIGHT = 0.2126;` | no | WCAG channel weight, a formula constant |
| 11 | `frontend/src/__tests__/themeContrast.test.ts:63` | `const GREEN_WEIGHT = 0.7152;` | no | WCAG channel weight, a formula constant |
| 12 | `frontend/src/__tests__/themeContrast.test.ts:64` | `const BLUE_WEIGHT = 0.0722;` | no | WCAG channel weight, a formula constant |
| 13 | `frontend/src/__tests__/themeContrast.test.ts:66` | `const RATIO_DECIMALS = 4;` | no | rounding precision, not a bound |
| 14 | `frontend/src/__tests__/themeTokenCompile.test.ts:47` | `const TOLERANCE = 0.1;` | no | numeric tolerance, not a bound |
| 15 | `frontend/src/api/purchases.ts:26` | `export const QUOTE_ATTACHMENT_MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024;` | **yes** | — |
| 16 | `frontend/src/api/tenantProfile.ts:139` | `export const SLUG_MIN_LENGTH = 3;` | **yes** | — |
| 17 | `frontend/src/api/tenantProfile.ts:140` | `export const SLUG_MAX_LENGTH = 64;` | **yes** | — |
| 18 | `frontend/src/api/tenantProfile.ts:145` | `const SLUG_MAX_BASE_LENGTH = 60;` | **yes** | — |
| 19 | `frontend/src/api/tenantProfile.ts:176` | `export const TENANT_LOGO_MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024;` | **yes** | — |
| 20 | `frontend/src/api/uploads.ts:28` | `export const UPLOAD_MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024;` | **yes** | — |
| 21 | `frontend/src/features/__tests__/documentOccurrenceContrast.test.ts:31` | `const GRAPHICAL_CONTRAST_RATIO = 3;` | **yes** | — |
| 22 | `frontend/src/features/__tests__/financePurchasesAccessContrast.test.ts:33` | `const GRAPHICAL_CONTRAST_RATIO = 3;` | **yes** | — |
| 23 | `frontend/src/features/__tests__/mediaFeedbackAnnouncementsPackagesContrast.test.ts:44` | `const GRAPHICAL_CONTRAST_RATIO = 3;` | **yes** | — |
| 24 | `frontend/src/features/__tests__/projectAssetContrast.test.ts:31` | `const GRAPHICAL_CONTRAST_RATIO = 3;` | **yes** | — |
| 25 | `frontend/src/features/access-control/components/GateMonitorPage.tsx:7` | `const LIVE_POLL_INTERVAL_MS = 5000;` | no | poll interval, a timing parameter rather than a contract bound |
| 26 | `frontend/src/features/infraction-management/__tests__/lotSelectContract.test.tsx:57` | `const DOCUMENTED_ROUTE_CEILING = 100;` | **yes** | — |
| 27 | `frontend/src/features/infraction-management/__tests__/uploadContract.test.tsx:60` | `const DOCUMENTED_MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024;` | **yes** | — |
| 28 | `frontend/src/features/infraction-management/components/NewInfractionModal.tsx:25` | `export const LOT_SELECT_LIMIT = 100;` | **yes** | — |
| 29 | `frontend/src/features/infraction-management/pages/InfractionsPage.tsx:33` | `const PAGE_SIZE = 20;` | no | pagination page size, not a bound |
| 30 | `frontend/src/features/public-site/__tests__/LandingPageStatusTints.test.ts:42` | `const DECIMALS = 3;` | no | rounding precision, not a bound |
| 31 | `frontend/src/features/purchase-management/components/PurchaseRequestFormModal.tsx:15` | `export const MAX_REQUEST_ITEMS = 50;` | **yes** | — |
| 32 | `frontend/src/features/purchase-management/components/QuoteFormModal.tsx:18` | `export const MAX_EXTRA_FIELDS = 20;` | **yes** | — |
| 33 | `frontend/src/features/purchase-management/components/QuoteFormModal.tsx:21` | `export const MAX_QUOTE_ITEMS = 50;` | **yes** | — |
| 34 | `frontend/src/features/purchase-management/components/SelectQuoteModal.tsx:11` | `export const MIN_JUSTIFICATION_LENGTH = 10;` | **yes** | — |
| 35 | `frontend/src/features/task-management/components/TaskFilterBar.tsx:38` | `const SEARCH_DEBOUNCE_MS = 200;` | no | debounce interval, a timing parameter |
| 36 | `frontend/src/features/user-administration/pages/TenantSubscriptionsPage.tsx:51` | `const HISTORY_PAGE_SIZE = 20;` | no | pagination page size, not a bound |
| 37 | `frontend/src/features/visitor-management/__tests__/visitorManagementContrast.test.ts:33` | `const GRAPHICAL_CONTRAST_RATIO = 3;` | **yes** | — |
| 38 | `frontend/src/features/visitor-management/__tests__/visitorManagementContrast.test.ts:35` | `const DECIMALS = 3;` | no | rounding precision, not a bound |
| 39 | `frontend/src/features/visitor-management/__tests__/visitorManagementContrast.test.ts:37` | `const COMPOSITED_ALPHA = 0.8;` | no | declared composite alpha, a value under test rather than a bound |
| 40 | `frontend/src/lib/contrast.ts:214` | `const LINEAR_KNEE = 0.0031308;` | no | sRGB transfer-function knee, a formula constant |
| 41 | `frontend/src/lib/contrast.ts:50` | `export const MINIMUM_CONTRAST_RATIO = 4.5;` | **yes** | — |
| 42 | `frontend/src/lib/contrast.ts:74` | `const GAMUT_TOLERANCE = 1e-4;` | no | numeric tolerance, not a bound |
| 43 | `frontend/src/lib/contrast.ts:78` | `const BISECTION_EPSILON = 1e-5;` | no | bisection epsilon, an algorithm parameter |
| 44 | `frontend/src/lib/contrast.ts:79` | `const SRGB_KNEE = 0.04045;` | no | sRGB transfer-function knee, a formula constant |
| 45 | `frontend/src/lib/contrast.ts:80` | `const MAX_CHANNEL = 255;` | no | 8-bit channel maximum, a domain constant not a policy bound |
| 46 | `frontend/src/lib/contrast.ts:81` | `const FULL_TURN = 360;` | no | degrees in a turn, a domain constant |
| 47 | `frontend/src/lib/contrast.ts:82` | `const LUMINANCE_OFFSET = 0.05;` | no | WCAG luminance offset, a formula constant |
| 48 | `frontend/src/lib/contrast.ts:84` | `const DECIMALS = 2;` | no | rounding precision, not a bound |
| 49 | `frontend/src/lib/money.ts:18` | `export const MONEY_DECIMALS = 2;` | no | currency minor-unit precision, a domain constant |
| 50 | `frontend/src/lib/money.ts:25` | `export const RATIO_DECIMALS = 4;` | no | rounding precision, not a bound |

Threshold subset (21 members), each with both directions in the ledger:
`themeContrast.test.ts:172 MINIMUM_PAIRS`, `:53 MINIMUM_RATIO`,
`lib/contrast.ts:50 MINIMUM_CONTRAST_RATIO`, `api/purchases.ts:26
QUOTE_ATTACHMENT_MAX_FILE_SIZE_BYTES`, `api/tenantProfile.ts:139
SLUG_MIN_LENGTH`, `:140 SLUG_MAX_LENGTH`, `:145 SLUG_MAX_BASE_LENGTH`, `:176
TENANT_LOGO_MAX_FILE_SIZE_BYTES`, `api/uploads.ts:28
UPLOAD_MAX_FILE_SIZE_BYTES`, the five `GRAPHICAL_CONTRAST_RATIO = 3`
declarations (`features/__tests__/documentOccurrenceContrast.test.ts:31`,
`financePurchasesAccessContrast.test.ts:33`,
`mediaFeedbackAnnouncementsPackagesContrast.test.ts:44`,
`projectAssetContrast.test.ts:31`,
`visitor-management/__tests__/visitorManagementContrast.test.ts:33`),
`lotSelectContract.test.tsx:57 DOCUMENTED_ROUTE_CEILING`,
`uploadContract.test.tsx:60 DOCUMENTED_MAX_FILE_SIZE_BYTES`,
`NewInfractionModal.tsx:25 LOT_SELECT_LIMIT`, `PurchaseRequestFormModal.tsx:15
MAX_REQUEST_ITEMS`, `QuoteFormModal.tsx:18 MAX_EXTRA_FIELDS`, `:21
MAX_QUOTE_ITEMS`, `SelectQuoteModal.tsx:11 MIN_JUSTIFICATION_LENGTH`.

For the nine subset members that are **production** constants rather than test
constants, the step-3 command is the spec (or specs) that name the constant,
found with
`LC_ALL=C grep -rl "<CONST>" frontend/src --include='*.test.ts' --include='*.test.tsx'`,
or — where no spec names it — the spec of the component that declares it. Five
members are named by **no** spec at all:
`SLUG_MAX_BASE_LENGTH`, `MAX_REQUEST_ITEMS`, `MAX_EXTRA_FIELDS`,
`MAX_QUOTE_ITEMS`, `MIN_JUSTIFICATION_LENGTH`. That is a read-only observation;
the mutations in the ledger are what turn four of the five into findings.

**On "weakening" versus "strengthening" for an equality pin.** Several subset
members are pinned by an equality (`assert X == 5 * 1024 * 1024`), not an
inequality. An equality pin has **no slack direction**: both the lower and the
higher mutation must redden, and both do. Those rows are labelled *lower* and
*higher* rather than *weak* and *strong*, and the *Over-pins* section states for
each whether a direction the contract permits exists at all.

#### S2 — prose claims (budget: ≥ 12 per suite, ≥ 24 total)

```
LC_ALL=C grep -rniE 'must never|never |is what keeps|proves that|guarantee' \
  backend/tests --include='*.py' | LC_ALL=C sort
LC_ALL=C grep -rniE 'must never|never |is what keeps|proves that|guarantee' \
  frontend/src --include='*.ts' --include='*.tsx' | LC_ALL=C sort
```

| suite | `N` (measured) | `N` (spec, 2026-10-01) | `k` | stride | mutated |
|---|---|---|---|---|---|
| backend | 287 | 281 | 12 | `ceil(i * 287 / 12)` → 24, 48, 72, 96, 120, 144, 168, 192, 216, 240, 264, 287 | **16** (12 stride + 4 supplementary) |
| frontend | 315 | 312 | 12 | `ceil(i * 315 / 12)` → 27, 53, 79, 105, 132, 158, 184, 210, 237, 263, 289, 315 | **15** (12 stride + 3 supplementary) |

One stride **per suite**, `N` and `k` per suite, never a combined list against a
combined budget.

Backend selected `file:line` list, in stride order:

| i | idx | candidate |
|---|---|---|
| 1 | 24 | `backend/tests/matrix_world.py:63` |
| 2 | 48 | `backend/tests/test_clock.py:253` |
| 3 | 72 | `backend/tests/test_mail.py:128` |
| 4 | 96 | `backend/tests/test_occurrences.py:218` |
| 5 | 120 | `backend/tests/test_permission_parity_matrix.py:122` |
| 6 | 144 | `backend/tests/test_project_report.py:1210` |
| 7 | 168 | `backend/tests/test_project_report_branding.py:19` |
| 8 | 192 | `backend/tests/test_project_stage_detail.py:9` |
| 9 | 216 | `backend/tests/test_role_permissions.py:128` |
| 10 | 240 | `backend/tests/test_subscription_ceiling.py:435` |
| 11 | 264 | `backend/tests/test_tenant_isolation.py:705` |
| 12 | 287 | `backend/tests/tools/record_parity_baseline.py:57` |

Frontend selected `file:line` list, in stride order:

| i | idx | candidate |
|---|---|---|
| 1 | 27 | `frontend/src/__tests__/themeTokenMigration.test.ts:3010` |
| 2 | 53 | `frontend/src/api/publicProjects.ts:21` |
| 3 | 79 | `frontend/src/features/__tests__/mediaFeedbackAnnouncementsPackagesContrast.test.ts:12` |
| 4 | 105 | `frontend/src/features/infraction-management/components/ContestationForm.tsx:12` |
| 5 | 132 | `frontend/src/features/project-management/components/ProjectFormModal.tsx:149` |
| 6 | 158 | `frontend/src/features/task-management/components/AssigneePicker.tsx:62` |
| 7 | 184 | `frontend/src/features/user-administration/__tests__/BrandedEntryLogin.integration.test.tsx:322` |
| 8 | 210 | `frontend/src/features/user-administration/__tests__/TenantsAdminPage.invitations.test.tsx:367` |
| 9 | 237 | `frontend/src/features/user-administration/components/TenantBrandColors.tsx:237` → text at `:357` |
| 10 | 263 | `frontend/src/features/user-administration/pages/SubscriptionPage.tsx:88` |
| 11 | 289 | `frontend/src/lib/brandPalettePaste.ts:9` |
| 12 | 315 | `frontend/src/types/subscription.ts:51` |

**Substitution log, S2: none.** Every selected candidate's file was clean at
snapshot time and no selected module was failing pre-mutation, so the stride
needed no substitution in either suite. No shortfall is declared: both suites
reached `k` = 12 and exceeded it.

Each selected case got **the mutation its prose names** — the mutation is stated
verbatim on each ledger row.

##### S2 mandatory modules, mutated by path (added **above** the stride, not in place of a stride slot)

| mandatory path | ledger rows |
|---|---|
| `backend/tests/test_project_report_escaping.py` | `S2-MAND-BE-escaping` |
| `backend/tests/test_branding.py` | `S2-MAND-BE-branding`, `-b`, `-c`, `-d` |
| `backend/tests/test_infraction_escalation.py` | `S2-MAND-BE-escalation` |
| `backend/tests/test_assets_rbac.py` | `S2-MAND-BE-assets-rbac`, `-b`, `-c` |
| `frontend/src/__tests__/themeContrast.test.ts` | `S2-MAND-FE-themeContrast` |
| `frontend/src/features/infraction-management/__tests__/access.test.ts` | `S2-MAND-FE-access` |
| `frontend/src/features/media-management/__tests__/MediaAssets.test.tsx` | `S2-MAND-FE-media` |

Note on `backend/tests/test_assets_rbac.py`: it returns **no** match for the S2
enumeration regex, so it is not a member of the candidate set. It is mutated
anyway because the spec names it by path; its claim is the one its filename
carries (RBAC parity), and that is what was mutated.

#### S3 — vacuous absence (budget: ≥ 20 per suite, ≥ 40 total)

```
LC_ALL=C grep -rnE 'assert not |not in ' backend/tests --include='*.py' | LC_ALL=C sort
LC_ALL=C grep -rnE 'toHaveLength\(0\)|not\.toBeInTheDocument|toBeNull\(\)' \
  frontend/src --include='*.ts' --include='*.tsx' | LC_ALL=C sort
```

| suite | `N` (measured) | `N` (spec) | `k` | stride | mutated |
|---|---|---|---|---|---|
| backend | 577 | 563 | 20 | `ceil(i * 577 / 20)` → 29, 58, 87, 116, 145, 174, 202, 231, 260, 289, 318, 347, 376, 404, 433, 462, 491, 520, 549, 577 | **22** (20 stride incl. 1 substitution + 1 skipped-and-recorded + 1 supplementary) |
| frontend | 551 | 551 | 20 | `ceil(i * 551 / 20)` → 28, 56, 83, 111, 138, 166, 193, 221, 248, 276, 304, 331, 359, 386, 414, 441, 469, 496, 524, 551 | **20** |

**Why the per-suite floor is 20 rather than 10** (restated here so the follow-up
sweep is sized from evidence, not from the spec's arithmetic): S3 has the largest
candidate set of any stratum — 577 + 551 = 1128 lines measured here, against
S2's 287 + 315 = 602 — *and* the cheapest defect to create by accident. An
absence assertion passes when the subject is never constructed, when a selector
typo means nothing was ever searched for, or when the fixture arrived empty, so a
vacuous pass needs no mistake in the assertion itself. A floor of 10 per suite
would have sampled 1.7% of the largest and most defect-dense candidate set, a
smaller per-candidate rate than S2's 4.2%; 20 per suite brings it to 3.5% and
3.6%, comparable to S2's.

**Substitution log, S3 backend** (one substitution):

```
skipped backend/tests/test_migrations_postgres.py:1478 (module skipped pre-mutation — 38 skipped, `pytest.mark.skipif` at line 109, no live Postgres) → substituted backend/tests/test_module_gating.py:115
```

The skipped candidate's own row (`S3-BE-03`) is retained in the ledger and in
*Not examined — already failing pre-mutation* for transparency; the substitute
(`S3-BE-03sub`) is what counts toward `k`. The substitute is the first non-
`test_migrations_postgres.py` entry in sorted order after index 87 — indices
88–98 all fall inside the same skipped module. No shortfall is declared: the
usable candidate set is far larger than `k`.

**Substitution log, S3 frontend: none.**

**The S3 mutation form, stated once.** The mutation makes the forbidden thing
*present at the population the assertion scans*, with the assertion itself left
byte-identical:

- `assert X not in Y` → `assert X not in (Y + [X])` / `{**Y, X: …}` / `… | {X}`;
- `assert not EXPR` → the forbidden member is appended to `EXPR`'s population;
- `expect(screen.queryBy…(T)).not.toBeInTheDocument()` and `.toBeNull()` →
  `expect(screen.queryBy…(T) ?? document.body)…`, i.e. when the query finds
  nothing, something that **is** in the document is substituted;
- `expect(X).toHaveLength(0)` → `expect([...X, "APRAS-111"]).toHaveLength(0)`.

A case that was green in step 0 and **stays** green under that mutation is a
finding: the assertion did not run, or never reached the population it claims to
scan. **Stated limitation**, carried to **FU-04**: this form detects an
assertion that never executes and an assertion whose population it can reach; it
does not by itself distinguish "the fixture arrived empty" from "the fixture
arrived full and contained nothing forbidden", because both are green before and
red after. Separating those two needs a per-case positive control, which is a
different and larger piece of work.

#### S4 — self-mocking frontend tests (budget: ≥ 10, frontend only, one stride)

```
LC_ALL=C grep -rn 'vi\.mock(' frontend/src --include='*.ts' --include='*.tsx' | LC_ALL=C sort
```

Raw `N` = **269** (spec recorded 269). The spec restricts selection, before the
stride, to candidates where the mocked specifier also appears in the test's own
name or describe block. Applying that filter — the mocked specifier's basename,
case-insensitively, against every `describe(`/`it(`/`test(` title string in the
same file — leaves **`N` = 44**, which is the denominator the stride runs over.
`k` = 10, stride `ceil(i * 44 / 10)` → 5, 9, 14, 18, 22, 27, 31, 36, 40, 44.

| i | idx | candidate | mocked specifier | real module broken |
|---|---|---|---|---|
| 1 | 5 | `src/api/__tests__/finance.test.ts:5` | `../client` | `src/api/client.ts` |
| 2 | 9 | `src/api/__tests__/packages.test.ts:5` | `../client` | `src/api/client.ts` |
| 3 | 14 | `src/api/__tests__/residents.test.ts:5` | `../client` | `src/api/client.ts` |
| 4 | 18 | `src/features/access-control/__tests__/AccessControlPage.test.tsx:7` | `../../../api/accessControl` | `src/api/accessControl.ts` |
| 5 | 22 | `src/features/document-management/__tests__/DocumentCenter.test.tsx:27` | `../../../api/documents` | `src/api/documents.ts` |
| 6 | 27 | `src/features/infraction-management/__tests__/Infractions.test.tsx:27` | `../../../api/infractions` | `src/api/infractions.ts` |
| 7 | 31 | `src/features/lot-management/__tests__/LotsPage.test.tsx:41` | `../../../api/lots` | `src/api/lots.ts` |
| 8 | 36 | `src/features/purchase-management/__tests__/PurchaseRequestDetailModal.test.tsx:26` | `../../../api/purchases` | `src/api/purchases.ts` |
| 9 | 40 | `src/features/user-administration/__tests__/TenantProfilePage.brand.test.tsx:28` | `../../../api/client` | `src/api/client.ts` |
| 10 | 44 | `src/features/visitor-management/__tests__/useVisitors.test.tsx:8` | `../../../api/visitors` | `src/api/visitors.ts` |

**Substitution log, S4: none.** 13 mutations are in the ledger: 10 selected, of
which three (`S4-FE-04`, `-08`, `-10`) were **invalidated and re-run**
(`-04r`, `-08r`, `-10r`) because the first attempt replaced the opening line of a
multi-line call expression and left the file syntactically invalid — those runs
collected **0 tests at exit 1** and therefore measured nothing about the test.
Both the invalidated and the valid rows are in the ledger; only the `r` rows
carry evidence.

#### S5 — unhandled-error survivors

Swept **suite-wide, not sampled**: it is answerable by instrumented runs rather
than per-test mutation. See *Unhandled errors*.

#### Per-stratum accounting, measured

| stratum / suite | collected | candidate set `N` | budget `k` | mutated | read-only judged | remainder (not examined) | realised per-candidate rate |
|---|---|---|---|---|---|---|---|
| S1 backend | 4195 cases | 62 lines (+2 config declarations) | exhaustive over subset | 43 | 43 excluded lines, each with a printed reason | 0 candidate lines unjudged | 19 of 62 lines mutated, both directions |
| S1 frontend | 2503 cases | 50 lines (+1 config declaration) | exhaustive over subset | 42 | 29 excluded lines + `vitest.config.ts` thresholds | 0 candidate lines unjudged | 21 of 50 lines mutated, both directions |
| S2 backend | 4195 cases | 287 lines | ≥ 12 | 16 stride-and-supplementary + 9 mandatory = **25** | 0 | 275 candidate lines | 12 of 287 = 4.2% |
| S2 frontend | 2503 cases | 315 lines | ≥ 12 | 15 stride-and-supplementary + 3 mandatory = **18** | 0 | 303 candidate lines | 12 of 315 = 3.8% |
| S3 backend | 4195 cases | 577 lines | ≥ 20 | 22 | 0 | 557 candidate lines | 20 of 577 = 3.5% |
| S3 frontend | 2503 cases | 551 lines | ≥ 20 | 20 | 0 | 531 candidate lines | 20 of 551 = 3.6% |
| S4 frontend | 2503 cases | 269 raw → 44 after the spec's filter | ≥ 10 | 13 (10 selected, 3 re-run) | 225 raw candidates excluded by the filter | 34 filtered candidates | 10 of 44 = 22.7% |
| S5 frontend | 2503 cases | not sampled — 188 files / 2503 cases instrumented | n/a | 0 mutations; 1 transient probe | 2503 cases observed | 0 | 100% of the suite instrumented |

Every number above is a **measured count**. No percentage anywhere in this
document is an estimate made in advance; the four percentages shown are
`mutated / N` computed after the fact.

Not covered by any stratum, as a measured count: the backend suite's 4195
collected cases minus the cases touched by the 90 backend mutation rows' modules,
and the frontend suite's 2503 minus the specs touched by the 93 frontend rows.
The remainder column above states this per stratum in the unit the enumeration
uses (candidate lines), which is the unit a follow-up sweep would be sized in.

---

## Mutation ledger

183 rows. The conventions:

- `<scratchpad>` is the session scratchpad path given at the top of this
  document.
- **Reddened** always means *failing in step 3 and green in step 0*, computed as
  a set difference against the named baseline's pass/fail set.
- Where a row does not carry an explicit **Case under examination** note, the
  case under examination is the one named by the candidate in the *Mutation*
  line and it is the case listed under *Reddened* for that row.
- Backend commands all carry `-p no:randomly` and `--no-cov`. No randomiser is
  active (see the plugin banner), so no `--randomly-seed` is recorded.

### Aborted mutations

**None.** No post-restore `cmp` returned a mismatch, so step 6 never fired.
Across all 183 rows the restore checksum pair is identical and `cmp` produced no
output.

### Not examined — uncommitted work present

**None.** `git status --porcelain -- <file>` was empty at snapshot time for every
one of the 183 rows. No file was skipped on this ground.

### Not examined — already failing pre-mutation

- `tests/test_bcrypt_cost.py::test_passlib_is_not_installed` — failure line
  quoted: `FAILED tests/test_bcrypt_cost.py::test_passlib_is_not_installed - AssertionError`.
  It appears in the step-0 baseline of every `test_bcrypt_cost.py` row
  (`S1-BE-PRODUCTION_FLOOR-weak`, `-strong`, `S1-BE-BCRYPT_ROUNDS-prod-13`) and
  is excluded from the evidence of each. Cause: declared-dependency drift, handed
  to **FU-01**. It is not used to support any finding or any "stays green"
  classification.
- `backend/tests/test_migrations_postgres.py` — **the whole module**, 38 cases,
  all skipped pre-mutation. Baseline `B-56` summary line:
  `38 skipped, 1 warning in 0.07s`. The module is gated by
  `pytestmark = pytest.mark.skipif(...)` at line 109 and there is no live
  Postgres on this machine, so none of its cases is green and none is
  examinable. Row `S3-BE-03` is retained in the ledger as the record of the
  attempt; the stride substituted `backend/tests/test_module_gating.py:115`
  (`S3-BE-03sub`). Sweeping this module needs a Postgres-backed run and is
  **FU-05**.

### Rows

#### `S1-BE-PRODUCTION_FLOOR-weak`

- **File:line** `backend/tests/test_bcrypt_cost.py:54`
- **Mutation** — S1 backend / PRODUCTION_FLOOR / weakening (loosen the bound)
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '54p' <scratchpad>/snap/S1-BE-PRODUCTION_FLOOR-weak.test_bcrypt_cost.py
  PRODUCTION_FLOOR = 12
  $ sed -n '54p' backend/tests/test_bcrypt_cost.py
  PRODUCTION_FLOOR = 11
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_bcrypt_cost.py`
- **Step-0 baseline** run **B-01** (own run, same command on the unmutated file) — `1 failed, 9 passed, 1 warning in 1.96s`; failing pre-mutation: `tests/test_bcrypt_cost.py::test_passlib_is_not_installed`; exit 1; `uv pip freeze` captured as `freeze.B-01`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `1 failed, 9 passed, 1 warning in 1.67s`; exit 1
- **Reddened vs that baseline** none
- **Case under examination** `tests/test_bcrypt_cost.py::test_the_production_floor_constant_is_a_ratchet`
- **Was it among the reddened?** no — and that is the correct outcome for a weakening move on a floor: 12 >= 11 still holds
- **Step-5 restore** pristine copy `shasum -a 256` = `c1838fb8c8602c1aced0b8f3c1de64d0730d8da3987726cb0511a1f5e37b25b3`; restored file `shasum -a 256` = `c1838fb8c8602c1aced0b8f3c1de64d0730d8da3987726cb0511a1f5e37b25b3`; `cmp <scratchpad>/snap/S1-BE-PRODUCTION_FLOOR-weak.test_bcrypt_cost.py backend/tests/test_bcrypt_cost.py` → clean (no output).

#### `S1-BE-PRODUCTION_FLOOR-strong`

- **File:line** `backend/tests/test_bcrypt_cost.py:54`
- **Mutation** — S1 backend / PRODUCTION_FLOOR / strengthening (tighten the bound)
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '54p' <scratchpad>/snap/S1-BE-PRODUCTION_FLOOR-strong.test_bcrypt_cost.py
  PRODUCTION_FLOOR = 12
  $ sed -n '54p' backend/tests/test_bcrypt_cost.py
  PRODUCTION_FLOOR = 99
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_bcrypt_cost.py`
- **Step-0 baseline** reused run **B-01** — `1 failed, 9 passed, 1 warning in 1.96s`; failing pre-mutation: `tests/test_bcrypt_cost.py::test_passlib_is_not_installed`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/tests/test_bcrypt_cost.py` was empty at snapshot; (b) every `cmp` since B-01 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i01`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `4 failed, 5 passed, 1 warning, 1 error in 1.19s`; exit 1
- **Reddened vs that baseline** (3) — `tests/test_bcrypt_cost.py::test_environment_cannot_lower_the_production_cost`, `tests/test_bcrypt_cost.py::test_the_constant_is_the_cost_actually_used`, `tests/test_bcrypt_cost.py::test_the_production_floor_constant_is_a_ratchet`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `c1838fb8c8602c1aced0b8f3c1de64d0730d8da3987726cb0511a1f5e37b25b3`; restored file `shasum -a 256` = `c1838fb8c8602c1aced0b8f3c1de64d0730d8da3987726cb0511a1f5e37b25b3`; `cmp <scratchpad>/snap/S1-BE-PRODUCTION_FLOOR-strong.test_bcrypt_cost.py backend/tests/test_bcrypt_cost.py` → clean (no output).

#### `S1-BE-DATED_COLUMN_FLOOR-weak`

- **File:line** `backend/tests/test_clock.py:113`
- **Mutation** — S1 backend / DATED_COLUMN_FLOOR / weakening (loosen the bound)
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '113p' <scratchpad>/snap/S1-BE-DATED_COLUMN_FLOOR-weak.test_clock.py
  DATED_COLUMN_FLOOR = 100
  $ sed -n '113p' backend/tests/test_clock.py
  DATED_COLUMN_FLOOR = 1
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_clock.py`
- **Step-0 baseline** run **B-02** (own run, same command on the unmutated file) — `12 passed, 10 warnings in 0.54s`; exit 0; `uv pip freeze` captured as `freeze.B-02`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `12 passed, 10 warnings in 0.56s`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `tests/test_clock.py::test_every_datetime_column_is_naive_unless_the_ledger_says_otherwise`
- **Was it among the reddened?** no — correct for a weakening move on a vacuity floor
- **Step-5 restore** pristine copy `shasum -a 256` = `493b2bd097c655bfa85e2232899ff7eb6847e14c292cd5aa9677d270774f1203`; restored file `shasum -a 256` = `493b2bd097c655bfa85e2232899ff7eb6847e14c292cd5aa9677d270774f1203`; `cmp <scratchpad>/snap/S1-BE-DATED_COLUMN_FLOOR-weak.test_clock.py backend/tests/test_clock.py` → clean (no output).

#### `S1-BE-DATED_COLUMN_FLOOR-strong`

- **File:line** `backend/tests/test_clock.py:113`
- **Mutation** — S1 backend / DATED_COLUMN_FLOOR / strengthening (tighten the bound)
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '113p' <scratchpad>/snap/S1-BE-DATED_COLUMN_FLOOR-strong.test_clock.py
  DATED_COLUMN_FLOOR = 100
  $ sed -n '113p' backend/tests/test_clock.py
  DATED_COLUMN_FLOOR = 100000
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_clock.py`
- **Step-0 baseline** reused run **B-02** — `12 passed, 10 warnings in 0.54s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/tests/test_clock.py` was empty at snapshot; (b) every `cmp` since B-02 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i02`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `1 failed, 11 passed, 10 warnings in 0.56s`; exit 1
- **Reddened vs that baseline** (1) — `tests/test_clock.py::test_every_datetime_column_is_naive_unless_the_ledger_says_otherwise`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `493b2bd097c655bfa85e2232899ff7eb6847e14c292cd5aa9677d270774f1203`; restored file `shasum -a 256` = `493b2bd097c655bfa85e2232899ff7eb6847e14c292cd5aa9677d270774f1203`; `cmp <scratchpad>/snap/S1-BE-DATED_COLUMN_FLOOR-strong.test_clock.py backend/tests/test_clock.py` → clean (no output).

#### `S1-BE-NOQA_CAP-weak`

- **File:line** `backend/tests/test_lint_hygiene.py:57`
- **Mutation** — S1 backend / NOQA_CAP / weakening (loosen the bound)
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '57p' <scratchpad>/snap/S1-BE-NOQA_CAP-weak.test_lint_hygiene.py
  NOQA_CAP = 72
  $ sed -n '57p' backend/tests/test_lint_hygiene.py
  NOQA_CAP = 10000
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_lint_hygiene.py`
- **Step-0 baseline** run **B-03** (own run, same command on the unmutated file) — `4 passed, 1 warning in 0.11s`; exit 0; `uv pip freeze` captured as `freeze.B-03`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `1 failed, 3 passed, 1 warning in 0.10s`; exit 1
- **Reddened vs that baseline** (1) — `tests/test_lint_hygiene.py::test_noqa_count_is_within_the_cap`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `7df7f27f9cea4f781ef96517b9c964a2b9085a366ca2ac4171ba1aeb3845ed5e`; restored file `shasum -a 256` = `7df7f27f9cea4f781ef96517b9c964a2b9085a366ca2ac4171ba1aeb3845ed5e`; `cmp <scratchpad>/snap/S1-BE-NOQA_CAP-weak.test_lint_hygiene.py backend/tests/test_lint_hygiene.py` → clean (no output).

#### `S1-BE-NOQA_CAP-strong`

- **File:line** `backend/tests/test_lint_hygiene.py:57`
- **Mutation** — S1 backend / NOQA_CAP / strengthening (tighten the bound)
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '57p' <scratchpad>/snap/S1-BE-NOQA_CAP-strong.test_lint_hygiene.py
  NOQA_CAP = 72
  $ sed -n '57p' backend/tests/test_lint_hygiene.py
  NOQA_CAP = 0
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_lint_hygiene.py`
- **Step-0 baseline** reused run **B-03** — `4 passed, 1 warning in 0.11s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/tests/test_lint_hygiene.py` was empty at snapshot; (b) every `cmp` since B-03 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i03`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `1 failed, 3 passed, 1 warning in 0.10s`; exit 1
- **Reddened vs that baseline** (1) — `tests/test_lint_hygiene.py::test_noqa_count_is_within_the_cap`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `7df7f27f9cea4f781ef96517b9c964a2b9085a366ca2ac4171ba1aeb3845ed5e`; restored file `shasum -a 256` = `7df7f27f9cea4f781ef96517b9c964a2b9085a366ca2ac4171ba1aeb3845ed5e`; `cmp <scratchpad>/snap/S1-BE-NOQA_CAP-strong.test_lint_hygiene.py backend/tests/test_lint_hygiene.py` → clean (no output).

#### `S1-BE-NOQA_CAP_CEILING-weak`

- **File:line** `backend/tests/test_lint_hygiene.py:122`
- **Mutation** — S1 backend / NOQA_CAP_CEILING / weakening (loosen the bound)
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '122p' <scratchpad>/snap/S1-BE-NOQA_CAP_CEILING-weak.test_lint_hygiene.py
      assert NOQA_CAP <= 108, "APRAS-54's ceiling; a rise needs its own task"
  $ sed -n '122p' backend/tests/test_lint_hygiene.py
      assert NOQA_CAP <= 100000, "APRAS-54's ceiling; a rise needs its own task"
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_lint_hygiene.py`
- **Step-0 baseline** reused run **B-03** — `4 passed, 1 warning in 0.11s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/tests/test_lint_hygiene.py` was empty at snapshot; (b) every `cmp` since B-03 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i04`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `4 passed, 1 warning in 0.10s`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `tests/test_lint_hygiene.py::test_noqa_count_is_within_the_cap`
- **Was it among the reddened?** no — correct: the ceiling on the cap is slack upward
- **Step-5 restore** pristine copy `shasum -a 256` = `7df7f27f9cea4f781ef96517b9c964a2b9085a366ca2ac4171ba1aeb3845ed5e`; restored file `shasum -a 256` = `7df7f27f9cea4f781ef96517b9c964a2b9085a366ca2ac4171ba1aeb3845ed5e`; `cmp <scratchpad>/snap/S1-BE-NOQA_CAP_CEILING-weak.test_lint_hygiene.py backend/tests/test_lint_hygiene.py` → clean (no output).

#### `S1-BE-NOQA_CAP_CEILING-strong`

- **File:line** `backend/tests/test_lint_hygiene.py:122`
- **Mutation** — S1 backend / NOQA_CAP_CEILING / strengthening (tighten the bound)
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '122p' <scratchpad>/snap/S1-BE-NOQA_CAP_CEILING-strong.test_lint_hygiene.py
      assert NOQA_CAP <= 108, "APRAS-54's ceiling; a rise needs its own task"
  $ sed -n '122p' backend/tests/test_lint_hygiene.py
      assert NOQA_CAP <= 1, "APRAS-54's ceiling; a rise needs its own task"
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_lint_hygiene.py`
- **Step-0 baseline** reused run **B-03** — `4 passed, 1 warning in 0.11s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/tests/test_lint_hygiene.py` was empty at snapshot; (b) every `cmp` since B-03 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i05`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `1 failed, 3 passed, 1 warning in 0.10s`; exit 1
- **Reddened vs that baseline** (1) — `tests/test_lint_hygiene.py::test_noqa_count_is_within_the_cap`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `7df7f27f9cea4f781ef96517b9c964a2b9085a366ca2ac4171ba1aeb3845ed5e`; restored file `shasum -a 256` = `7df7f27f9cea4f781ef96517b9c964a2b9085a366ca2ac4171ba1aeb3845ed5e`; `cmp <scratchpad>/snap/S1-BE-NOQA_CAP_CEILING-strong.test_lint_hygiene.py backend/tests/test_lint_hygiene.py` → clean (no output).

#### `S1-BE-MAX_NON_ROLE_403-weak`

- **File:line** `backend/tests/test_permission_parity_matrix.py:452`
- **Mutation** — S1 backend / MAX_NON_ROLE_403 / weakening (loosen the bound)
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '452p' <scratchpad>/snap/S1-BE-MAX_NON_ROLE_403-weak.test_permission_parity_matrix.py
  MAX_NON_ROLE_403 = 40
  $ sed -n '452p' backend/tests/test_permission_parity_matrix.py
  MAX_NON_ROLE_403 = 100000
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_permission_parity_matrix.py`
- **Step-0 baseline** run **B-04** (own run, same command on the unmutated file) — `1330 passed, 1273 warnings in 11.39s`; exit 0; `uv pip freeze` captured as `freeze.B-04`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `1330 passed, 1273 warnings in 10.17s`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `tests/test_permission_parity_matrix.py::test_non_role_403_is_bounded`
- **Was it among the reddened?** no — correct for a weakening move on a cap
- **Step-5 restore** pristine copy `shasum -a 256` = `3a8ec4a11e539247dae2fb131d4da64b940111abdbff5ec972cdf1a76501da94`; restored file `shasum -a 256` = `3a8ec4a11e539247dae2fb131d4da64b940111abdbff5ec972cdf1a76501da94`; `cmp <scratchpad>/snap/S1-BE-MAX_NON_ROLE_403-weak.test_permission_parity_matrix.py backend/tests/test_permission_parity_matrix.py` → clean (no output).

#### `S1-BE-MAX_NON_ROLE_403-strong`

- **File:line** `backend/tests/test_permission_parity_matrix.py:452`
- **Mutation** — S1 backend / MAX_NON_ROLE_403 / strengthening (tighten the bound)
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '452p' <scratchpad>/snap/S1-BE-MAX_NON_ROLE_403-strong.test_permission_parity_matrix.py
  MAX_NON_ROLE_403 = 40
  $ sed -n '452p' backend/tests/test_permission_parity_matrix.py
  MAX_NON_ROLE_403 = 0
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_permission_parity_matrix.py`
- **Step-0 baseline** reused run **B-04** — `1330 passed, 1273 warnings in 11.39s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/tests/test_permission_parity_matrix.py` was empty at snapshot; (b) every `cmp` since B-04 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i06`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `1 failed, 1329 passed, 1273 warnings in 9.80s`; exit 1
- **Reddened vs that baseline** (1) — `tests/test_permission_parity_matrix.py::test_non_role_403_is_bounded`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `3a8ec4a11e539247dae2fb131d4da64b940111abdbff5ec972cdf1a76501da94`; restored file `shasum -a 256` = `3a8ec4a11e539247dae2fb131d4da64b940111abdbff5ec972cdf1a76501da94`; `cmp <scratchpad>/snap/S1-BE-MAX_NON_ROLE_403-strong.test_permission_parity_matrix.py backend/tests/test_permission_parity_matrix.py` → clean (no output).

#### `S1-BE-MAX_PERMITTED_422-weak`

- **File:line** `backend/tests/test_permission_parity_matrix.py:453`
- **Mutation** — S1 backend / MAX_PERMITTED_422 / weakening (loosen the bound)
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '453p' <scratchpad>/snap/S1-BE-MAX_PERMITTED_422-weak.test_permission_parity_matrix.py
  MAX_PERMITTED_422 = 15
  $ sed -n '453p' backend/tests/test_permission_parity_matrix.py
  MAX_PERMITTED_422 = 100000
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_permission_parity_matrix.py`
- **Step-0 baseline** reused run **B-04** — `1330 passed, 1273 warnings in 11.39s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/tests/test_permission_parity_matrix.py` was empty at snapshot; (b) every `cmp` since B-04 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i07`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `1330 passed, 1273 warnings in 9.88s`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `tests/test_permission_parity_matrix.py::test_permitted_422_is_bounded`
- **Was it among the reddened?** no — correct for a weakening move on a cap
- **Step-5 restore** pristine copy `shasum -a 256` = `3a8ec4a11e539247dae2fb131d4da64b940111abdbff5ec972cdf1a76501da94`; restored file `shasum -a 256` = `3a8ec4a11e539247dae2fb131d4da64b940111abdbff5ec972cdf1a76501da94`; `cmp <scratchpad>/snap/S1-BE-MAX_PERMITTED_422-weak.test_permission_parity_matrix.py backend/tests/test_permission_parity_matrix.py` → clean (no output).

#### `S1-BE-MAX_PERMITTED_422-strong`

- **File:line** `backend/tests/test_permission_parity_matrix.py:453`
- **Mutation** — S1 backend / MAX_PERMITTED_422 / strengthening (tighten the bound)
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '453p' <scratchpad>/snap/S1-BE-MAX_PERMITTED_422-strong.test_permission_parity_matrix.py
  MAX_PERMITTED_422 = 15
  $ sed -n '453p' backend/tests/test_permission_parity_matrix.py
  MAX_PERMITTED_422 = -1
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_permission_parity_matrix.py`
- **Step-0 baseline** reused run **B-04** — `1330 passed, 1273 warnings in 11.39s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/tests/test_permission_parity_matrix.py` was empty at snapshot; (b) every `cmp` since B-04 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i08`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `1 failed, 1329 passed, 1273 warnings in 14.22s`; exit 1
- **Reddened vs that baseline** (1) — `tests/test_permission_parity_matrix.py::test_permitted_422_is_bounded`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `3a8ec4a11e539247dae2fb131d4da64b940111abdbff5ec972cdf1a76501da94`; restored file `shasum -a 256` = `3a8ec4a11e539247dae2fb131d4da64b940111abdbff5ec972cdf1a76501da94`; `cmp <scratchpad>/snap/S1-BE-MAX_PERMITTED_422-strong.test_permission_parity_matrix.py backend/tests/test_permission_parity_matrix.py` → clean (no output).

#### `S1-BE-MAX_GROWTH_MM-weak`

- **File:line** `backend/tests/test_project_report_bar_geometry.py:124`
- **Mutation** — S1 backend / MAX_GROWTH_MM / weakening (loosen the bound)
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '124p' <scratchpad>/snap/S1-BE-MAX_GROWTH_MM-weak.test_project_report_bar_geometry.py
  MAX_GROWTH_MM = 6.0
  $ sed -n '124p' backend/tests/test_project_report_bar_geometry.py
  MAX_GROWTH_MM = 1000.0
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_project_report_bar_geometry.py`
- **Step-0 baseline** run **B-05** (own run, same command on the unmutated file) — `50 passed, 1 warning in 0.14s`; exit 0; `uv pip freeze` captured as `freeze.B-05`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `50 passed, 1 warning in 0.16s`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `tests/test_project_report_bar_geometry.py::test_the_close_case_bar_grows_by_at_most_six_millimetres`
- **Was it among the reddened?** no — correct for a weakening move on a growth cap
- **Step-5 restore** pristine copy `shasum -a 256` = `8650be2122fca8c0d961442414d656738b1c22bea0c963ac806509c47e01cf39`; restored file `shasum -a 256` = `8650be2122fca8c0d961442414d656738b1c22bea0c963ac806509c47e01cf39`; `cmp <scratchpad>/snap/S1-BE-MAX_GROWTH_MM-weak.test_project_report_bar_geometry.py backend/tests/test_project_report_bar_geometry.py` → clean (no output).

#### `S1-BE-MAX_GROWTH_MM-strong`

- **File:line** `backend/tests/test_project_report_bar_geometry.py:124`
- **Mutation** — S1 backend / MAX_GROWTH_MM / strengthening (tighten the bound)
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '124p' <scratchpad>/snap/S1-BE-MAX_GROWTH_MM-strong.test_project_report_bar_geometry.py
  MAX_GROWTH_MM = 6.0
  $ sed -n '124p' backend/tests/test_project_report_bar_geometry.py
  MAX_GROWTH_MM = 0.0
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_project_report_bar_geometry.py`
- **Step-0 baseline** reused run **B-05** — `50 passed, 1 warning in 0.14s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/tests/test_project_report_bar_geometry.py` was empty at snapshot; (b) every `cmp` since B-05 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i09`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `1 failed, 49 passed, 1 warning in 0.16s`; exit 1
- **Reddened vs that baseline** (1) — `tests/test_project_report_bar_geometry.py::test_the_close_case_bar_grows_by_at_most_six_millimetres`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `8650be2122fca8c0d961442414d656738b1c22bea0c963ac806509c47e01cf39`; restored file `shasum -a 256` = `8650be2122fca8c0d961442414d656738b1c22bea0c963ac806509c47e01cf39`; `cmp <scratchpad>/snap/S1-BE-MAX_GROWTH_MM-strong.test_project_report_bar_geometry.py backend/tests/test_project_report_bar_geometry.py` → clean (no output).

#### `S1-BE-TEXT_FLOOR-weak`

- **File:line** `backend/tests/test_project_report_branding.py:99`
- **Mutation** — S1 backend / TEXT_FLOOR / weakening (loosen the bound)
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '99p' <scratchpad>/snap/S1-BE-TEXT_FLOOR-weak.test_project_report_branding.py
  TEXT_FLOOR = 4.5
  $ sed -n '99p' backend/tests/test_project_report_branding.py
  TEXT_FLOOR = 1.0
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_project_report_branding.py`
- **Step-0 baseline** run **B-06** (own run, same command on the unmutated file) — `39 passed, 11 warnings in 1.68s`; exit 0; `uv pip freeze` captured as `freeze.B-06`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `39 passed, 11 warnings in 1.41s`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `tests/test_project_report_branding.py::test_every_text_pair_clears_aa_for_every_brand`
- **Was it among the reddened?** no — correct for a weakening move on a contrast floor
- **Step-5 restore** pristine copy `shasum -a 256` = `6ed8af6f0040578cd1ff686306fb0f71cfc30d4936e4c2c22b8f1474e7ff4f4f`; restored file `shasum -a 256` = `6ed8af6f0040578cd1ff686306fb0f71cfc30d4936e4c2c22b8f1474e7ff4f4f`; `cmp <scratchpad>/snap/S1-BE-TEXT_FLOOR-weak.test_project_report_branding.py backend/tests/test_project_report_branding.py` → clean (no output).

#### `S1-BE-TEXT_FLOOR-strong`

- **File:line** `backend/tests/test_project_report_branding.py:99`
- **Mutation** — S1 backend / TEXT_FLOOR / strengthening (tighten the bound)
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '99p' <scratchpad>/snap/S1-BE-TEXT_FLOOR-strong.test_project_report_branding.py
  TEXT_FLOOR = 4.5
  $ sed -n '99p' backend/tests/test_project_report_branding.py
  TEXT_FLOOR = 21.0
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_project_report_branding.py`
- **Step-0 baseline** reused run **B-06** — `39 passed, 11 warnings in 1.68s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/tests/test_project_report_branding.py` was empty at snapshot; (b) every `cmp` since B-06 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i10`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `5 failed, 34 passed, 11 warnings in 1.39s`; exit 1
- **Reddened vs that baseline** (5) — `tests/test_project_report_branding.py::test_every_text_pair_clears_aa_for_every_brand[#059669]`, `tests/test_project_report_branding.py::test_every_text_pair_clears_aa_for_every_brand[#2563eb]`, `tests/test_project_report_branding.py::test_every_text_pair_clears_aa_for_every_brand[#7c3aed]`, `tests/test_project_report_branding.py::test_every_text_pair_clears_aa_for_every_brand[#dc2626]`, `tests/test_project_report_branding.py::test_every_text_pair_clears_aa_for_every_brand[#facc15]`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `6ed8af6f0040578cd1ff686306fb0f71cfc30d4936e4c2c22b8f1474e7ff4f4f`; restored file `shasum -a 256` = `6ed8af6f0040578cd1ff686306fb0f71cfc30d4936e4c2c22b8f1474e7ff4f4f`; `cmp <scratchpad>/snap/S1-BE-TEXT_FLOOR-strong.test_project_report_branding.py backend/tests/test_project_report_branding.py` → clean (no output).

#### `S1-BE-GRAPHIC_FLOOR-weak`

- **File:line** `backend/tests/test_project_report_branding.py:100`
- **Mutation** — S1 backend / GRAPHIC_FLOOR / weakening (loosen the bound)
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '100p' <scratchpad>/snap/S1-BE-GRAPHIC_FLOOR-weak.test_project_report_branding.py
  GRAPHIC_FLOOR = 3.0
  $ sed -n '100p' backend/tests/test_project_report_branding.py
  GRAPHIC_FLOOR = 1.0
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_project_report_branding.py`
- **Step-0 baseline** reused run **B-06** — `39 passed, 11 warnings in 1.68s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/tests/test_project_report_branding.py` was empty at snapshot; (b) every `cmp` since B-06 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i11`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `9 failed, 30 passed, 11 warnings in 1.37s`; exit 1
- **Reddened vs that baseline** (9) — `tests/test_project_report_branding.py::test_the_graphical_pairs_below_three_are_asserted_not_skipped[#059669-#059669-brand-brand-alt-1.0]`, `tests/test_project_report_branding.py::test_the_graphical_pairs_below_three_are_asserted_not_skipped[#059669-#059669-brand-line-2.9478]`, `tests/test_project_report_branding.py::test_the_graphical_pairs_below_three_are_asserted_not_skipped[#059669-#c6a04a-brand-alt-card-2.4952]`, `tests/test_project_report_branding.py::test_the_graphical_pairs_below_three_are_asserted_not_skipped[#059669-#c6a04a-brand-brand-alt-1.4911]`, `tests/test_project_report_branding.py::test_the_graphical_pairs_below_three_are_asserted_not_skipped[#2563eb-#facc15-brand-alt-card-1.5338]`, `tests/test_project_report_branding.py::test_the_graphical_pairs_below_three_are_asserted_not_skipped[#facc15-#facc15-brand-alt-card-1.5338]`, `tests/test_project_report_branding.py::test_the_graphical_pairs_below_three_are_asserted_not_skipped[#facc15-#facc15-brand-alt-line-1.2111]`, `tests/test_project_report_branding.py::test_the_graphical_pairs_below_three_are_asserted_not_skipped[#facc15-#facc15-brand-card-1.5338]`, `tests/test_project_report_branding.py::test_the_graphical_pairs_below_three_are_asserted_not_skipped[#facc15-#facc15-brand-line-1.2111]`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `6ed8af6f0040578cd1ff686306fb0f71cfc30d4936e4c2c22b8f1474e7ff4f4f`; restored file `shasum -a 256` = `6ed8af6f0040578cd1ff686306fb0f71cfc30d4936e4c2c22b8f1474e7ff4f4f`; `cmp <scratchpad>/snap/S1-BE-GRAPHIC_FLOOR-weak.test_project_report_branding.py backend/tests/test_project_report_branding.py` → clean (no output).

#### `S1-BE-GRAPHIC_FLOOR-strong`

- **File:line** `backend/tests/test_project_report_branding.py:100`
- **Mutation** — S1 backend / GRAPHIC_FLOOR / strengthening (tighten the bound)
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '100p' <scratchpad>/snap/S1-BE-GRAPHIC_FLOOR-strong.test_project_report_branding.py
  GRAPHIC_FLOOR = 3.0
  $ sed -n '100p' backend/tests/test_project_report_branding.py
  GRAPHIC_FLOOR = 21.0
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_project_report_branding.py`
- **Step-0 baseline** reused run **B-06** — `39 passed, 11 warnings in 1.68s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/tests/test_project_report_branding.py` was empty at snapshot; (b) every `cmp` since B-06 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i12`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `39 passed, 11 warnings in 1.49s`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `tests/test_project_report_branding.py::test_the_graphical_pairs_below_three_are_asserted_not_skipped`
- **Was it among the reddened?** no — see Findings F-01: GRAPHIC_FLOOR is only ever read as an upper bound (`ratio < GRAPHIC_FLOOR`), so raising it to 21.0 cannot redden anything; no case asserts any graphic pair *clears* 3.0
- **Step-5 restore** pristine copy `shasum -a 256` = `6ed8af6f0040578cd1ff686306fb0f71cfc30d4936e4c2c22b8f1474e7ff4f4f`; restored file `shasum -a 256` = `6ed8af6f0040578cd1ff686306fb0f71cfc30d4936e4c2c22b8f1474e7ff4f4f`; `cmp <scratchpad>/snap/S1-BE-GRAPHIC_FLOOR-strong.test_project_report_branding.py backend/tests/test_project_report_branding.py` → clean (no output).

#### `S1-BE-DECLINED_LIMIT-weak`

- **File:line** `backend/tests/test_public_project_report.py:54`
- **Mutation** — S1 backend / DECLINED_LIMIT / weakening (loosen the bound)
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '54p' <scratchpad>/snap/S1-BE-DECLINED_LIMIT-weak.test_public_project_report.py
  REQUESTS_PAST_THE_DECLINED_LIMIT = 31
  $ sed -n '54p' backend/tests/test_public_project_report.py
  REQUESTS_PAST_THE_DECLINED_LIMIT = 1
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_public_project_report.py`
- **Step-0 baseline** run **B-07** (own run, same command on the unmutated file) — `13 passed, 7 warnings in 0.97s`; exit 0; `uv pip freeze` captured as `freeze.B-07`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `13 passed, 7 warnings in 0.88s`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `tests/test_public_project_report.py::test_the_thirty_first_request_inside_a_minute_is_still_a_200`
- **Was it among the reddened?** no — see Examined and kept EK-01
- **Step-5 restore** pristine copy `shasum -a 256` = `34c3dab273d4b573c64aa736bed0bf58a28e5585a9926e4e36c86b8e163fd649`; restored file `shasum -a 256` = `34c3dab273d4b573c64aa736bed0bf58a28e5585a9926e4e36c86b8e163fd649`; `cmp <scratchpad>/snap/S1-BE-DECLINED_LIMIT-weak.test_public_project_report.py backend/tests/test_public_project_report.py` → clean (no output).

#### `S1-BE-DECLINED_LIMIT-strong`

- **File:line** `backend/tests/test_public_project_report.py:54`
- **Mutation** — S1 backend / DECLINED_LIMIT / strengthening (tighten the bound)
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '54p' <scratchpad>/snap/S1-BE-DECLINED_LIMIT-strong.test_public_project_report.py
  REQUESTS_PAST_THE_DECLINED_LIMIT = 31
  $ sed -n '54p' backend/tests/test_public_project_report.py
  REQUESTS_PAST_THE_DECLINED_LIMIT = 61
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_public_project_report.py`
- **Step-0 baseline** reused run **B-07** — `13 passed, 7 warnings in 0.97s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/tests/test_public_project_report.py` was empty at snapshot; (b) every `cmp` since B-07 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i13`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `13 passed, 7 warnings in 2.15s`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `tests/test_public_project_report.py::test_the_thirty_first_request_inside_a_minute_is_still_a_200`
- **Was it among the reddened?** no — see Examined and kept EK-01
- **Step-5 restore** pristine copy `shasum -a 256` = `34c3dab273d4b573c64aa736bed0bf58a28e5585a9926e4e36c86b8e163fd649`; restored file `shasum -a 256` = `34c3dab273d4b573c64aa736bed0bf58a28e5585a9926e4e36c86b8e163fd649`; `cmp <scratchpad>/snap/S1-BE-DECLINED_LIMIT-strong.test_public_project_report.py backend/tests/test_public_project_report.py` → clean (no output).

#### `S1-BE-ATTACHMENT_MAX-weak`

- **File:line** `backend/tests/test_purchase_quote_attachment.py:482`
- **Mutation** — S1 backend / ATTACHMENT_MAX / weakening (loosen the bound)
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '482p' <scratchpad>/snap/S1-BE-ATTACHMENT_MAX-weak.test_purchase_quote_attachment.py
      assert PurchaseService.ATTACHMENT_MAX_FILE_SIZE == 5 * 1024 * 1024, (
  $ sed -n '482p' backend/tests/test_purchase_quote_attachment.py
      assert PurchaseService.ATTACHMENT_MAX_FILE_SIZE == 4 * 1024 * 1024, (
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_purchase_quote_attachment.py`
- **Step-0 baseline** run **B-08** (own run, same command on the unmutated file) — `28 passed, 186 warnings in 1.78s`; exit 0; `uv pip freeze` captured as `freeze.B-08`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `1 failed, 27 passed, 186 warnings in 1.74s`; exit 1
- **Reddened vs that baseline** (1) — `tests/test_purchase_quote_attachment.py::test_the_attachment_contract_matches_the_frontend_client`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `b2079ab9bba9f16cbd4466c1696626de738e33949d53f0a203260c0f2b5bb27b`; restored file `shasum -a 256` = `b2079ab9bba9f16cbd4466c1696626de738e33949d53f0a203260c0f2b5bb27b`; `cmp <scratchpad>/snap/S1-BE-ATTACHMENT_MAX-weak.test_purchase_quote_attachment.py backend/tests/test_purchase_quote_attachment.py` → clean (no output).

#### `S1-BE-ATTACHMENT_MAX-strong`

- **File:line** `backend/tests/test_purchase_quote_attachment.py:482`
- **Mutation** — S1 backend / ATTACHMENT_MAX / strengthening (tighten the bound)
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '482p' <scratchpad>/snap/S1-BE-ATTACHMENT_MAX-strong.test_purchase_quote_attachment.py
      assert PurchaseService.ATTACHMENT_MAX_FILE_SIZE == 5 * 1024 * 1024, (
  $ sed -n '482p' backend/tests/test_purchase_quote_attachment.py
      assert PurchaseService.ATTACHMENT_MAX_FILE_SIZE == 6 * 1024 * 1024, (
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_purchase_quote_attachment.py`
- **Step-0 baseline** reused run **B-08** — `28 passed, 186 warnings in 1.78s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/tests/test_purchase_quote_attachment.py` was empty at snapshot; (b) every `cmp` since B-08 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i14`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `1 failed, 27 passed, 186 warnings in 1.84s`; exit 1
- **Reddened vs that baseline** (1) — `tests/test_purchase_quote_attachment.py::test_the_attachment_contract_matches_the_frontend_client`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `b2079ab9bba9f16cbd4466c1696626de738e33949d53f0a203260c0f2b5bb27b`; restored file `shasum -a 256` = `b2079ab9bba9f16cbd4466c1696626de738e33949d53f0a203260c0f2b5bb27b`; `cmp <scratchpad>/snap/S1-BE-ATTACHMENT_MAX-strong.test_purchase_quote_attachment.py backend/tests/test_purchase_quote_attachment.py` → clean (no output).

#### `S1-BE-SLUG_MIN-weak`

- **File:line** `backend/tests/test_slug.py:92`
- **Mutation** — S1 backend / SLUG_MIN / weakening (loosen the bound)
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '92p' <scratchpad>/snap/S1-BE-SLUG_MIN-weak.test_slug.py
      assert SLUG_MIN_LENGTH == 3
  $ sed -n '92p' backend/tests/test_slug.py
      assert SLUG_MIN_LENGTH == 2
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_slug.py`
- **Step-0 baseline** run **B-09** (own run, same command on the unmutated file) — `74 passed, 1 warning in 0.36s`; exit 0; `uv pip freeze` captured as `freeze.B-09`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `1 failed, 73 passed, 1 warning in 0.39s`; exit 1
- **Reddened vs that baseline** (1) — `tests/test_slug.py::test_the_fallback_base_is_itself_valid_and_inside_the_column`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `9bb00777de45549dec01f18bb7f040778d29e2c2b42b5de631303f07f095d2c7`; restored file `shasum -a 256` = `9bb00777de45549dec01f18bb7f040778d29e2c2b42b5de631303f07f095d2c7`; `cmp <scratchpad>/snap/S1-BE-SLUG_MIN-weak.test_slug.py backend/tests/test_slug.py` → clean (no output).

#### `S1-BE-SLUG_MIN-strong`

- **File:line** `backend/tests/test_slug.py:92`
- **Mutation** — S1 backend / SLUG_MIN / strengthening (tighten the bound)
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '92p' <scratchpad>/snap/S1-BE-SLUG_MIN-strong.test_slug.py
      assert SLUG_MIN_LENGTH == 3
  $ sed -n '92p' backend/tests/test_slug.py
      assert SLUG_MIN_LENGTH == 4
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_slug.py`
- **Step-0 baseline** reused run **B-09** — `74 passed, 1 warning in 0.36s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/tests/test_slug.py` was empty at snapshot; (b) every `cmp` since B-09 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i15`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `1 failed, 73 passed, 1 warning in 0.39s`; exit 1
- **Reddened vs that baseline** (1) — `tests/test_slug.py::test_the_fallback_base_is_itself_valid_and_inside_the_column`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `9bb00777de45549dec01f18bb7f040778d29e2c2b42b5de631303f07f095d2c7`; restored file `shasum -a 256` = `9bb00777de45549dec01f18bb7f040778d29e2c2b42b5de631303f07f095d2c7`; `cmp <scratchpad>/snap/S1-BE-SLUG_MIN-strong.test_slug.py backend/tests/test_slug.py` → clean (no output).

#### `S1-BE-SLUG_MAX-weak`

- **File:line** `backend/tests/test_slug.py:93`
- **Mutation** — S1 backend / SLUG_MAX / weakening (loosen the bound)
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '93p' <scratchpad>/snap/S1-BE-SLUG_MAX-weak.test_slug.py
      assert SLUG_MAX_LENGTH == 64
  $ sed -n '93p' backend/tests/test_slug.py
      assert SLUG_MAX_LENGTH == 63
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_slug.py`
- **Step-0 baseline** reused run **B-09** — `74 passed, 1 warning in 0.36s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/tests/test_slug.py` was empty at snapshot; (b) every `cmp` since B-09 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i16`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `1 failed, 73 passed, 1 warning in 0.42s`; exit 1
- **Reddened vs that baseline** (1) — `tests/test_slug.py::test_the_fallback_base_is_itself_valid_and_inside_the_column`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `9bb00777de45549dec01f18bb7f040778d29e2c2b42b5de631303f07f095d2c7`; restored file `shasum -a 256` = `9bb00777de45549dec01f18bb7f040778d29e2c2b42b5de631303f07f095d2c7`; `cmp <scratchpad>/snap/S1-BE-SLUG_MAX-weak.test_slug.py backend/tests/test_slug.py` → clean (no output).

#### `S1-BE-SLUG_MAX-strong`

- **File:line** `backend/tests/test_slug.py:93`
- **Mutation** — S1 backend / SLUG_MAX / strengthening (tighten the bound)
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '93p' <scratchpad>/snap/S1-BE-SLUG_MAX-strong.test_slug.py
      assert SLUG_MAX_LENGTH == 64
  $ sed -n '93p' backend/tests/test_slug.py
      assert SLUG_MAX_LENGTH == 65
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_slug.py`
- **Step-0 baseline** reused run **B-09** — `74 passed, 1 warning in 0.36s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/tests/test_slug.py` was empty at snapshot; (b) every `cmp` since B-09 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i17`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `1 failed, 73 passed, 1 warning in 0.43s`; exit 1
- **Reddened vs that baseline** (1) — `tests/test_slug.py::test_the_fallback_base_is_itself_valid_and_inside_the_column`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `9bb00777de45549dec01f18bb7f040778d29e2c2b42b5de631303f07f095d2c7`; restored file `shasum -a 256` = `9bb00777de45549dec01f18bb7f040778d29e2c2b42b5de631303f07f095d2c7`; `cmp <scratchpad>/snap/S1-BE-SLUG_MAX-strong.test_slug.py backend/tests/test_slug.py` → clean (no output).

#### `S1-BE-BLOB_MAX_READ-weak`

- **File:line** `backend/tests/test_storage_blob.py:1093`
- **Mutation** — S1 backend / BLOB_MAX_READ / weakening (loosen the bound)
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '1093p' <scratchpad>/snap/S1-BE-BLOB_MAX_READ-weak.test_storage_blob.py
      assert storage_service.BLOB_MAX_READ_BYTES == 2 * 1024 * 1024
  $ sed -n '1093p' backend/tests/test_storage_blob.py
      assert storage_service.BLOB_MAX_READ_BYTES == 1 * 1024 * 1024
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_storage_blob.py`
- **Step-0 baseline** run **B-10** (own run, same command on the unmutated file) — `107 passed, 5 warnings in 0.94s`; exit 0; `uv pip freeze` captured as `freeze.B-10`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `1 failed, 106 passed, 5 warnings in 1.09s`; exit 1
- **Reddened vs that baseline** (1) — `tests/test_storage_blob.py::test_the_default_ceiling_is_the_logo_ceiling`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `242d874ed642217158d183a7b56f0337d51730e99fdaa008a6e8095ac0f27d5f`; restored file `shasum -a 256` = `242d874ed642217158d183a7b56f0337d51730e99fdaa008a6e8095ac0f27d5f`; `cmp <scratchpad>/snap/S1-BE-BLOB_MAX_READ-weak.test_storage_blob.py backend/tests/test_storage_blob.py` → clean (no output).

#### `S1-BE-BLOB_MAX_READ-strong`

- **File:line** `backend/tests/test_storage_blob.py:1093`
- **Mutation** — S1 backend / BLOB_MAX_READ / strengthening (tighten the bound)
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '1093p' <scratchpad>/snap/S1-BE-BLOB_MAX_READ-strong.test_storage_blob.py
      assert storage_service.BLOB_MAX_READ_BYTES == 2 * 1024 * 1024
  $ sed -n '1093p' backend/tests/test_storage_blob.py
      assert storage_service.BLOB_MAX_READ_BYTES == 3 * 1024 * 1024
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_storage_blob.py`
- **Step-0 baseline** reused run **B-10** — `107 passed, 5 warnings in 0.94s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/tests/test_storage_blob.py` was empty at snapshot; (b) every `cmp` since B-10 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i18`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `1 failed, 106 passed, 5 warnings in 1.02s`; exit 1
- **Reddened vs that baseline** (1) — `tests/test_storage_blob.py::test_the_default_ceiling_is_the_logo_ceiling`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `242d874ed642217158d183a7b56f0337d51730e99fdaa008a6e8095ac0f27d5f`; restored file `shasum -a 256` = `242d874ed642217158d183a7b56f0337d51730e99fdaa008a6e8095ac0f27d5f`; `cmp <scratchpad>/snap/S1-BE-BLOB_MAX_READ-strong.test_storage_blob.py backend/tests/test_storage_blob.py` → clean (no output).

#### `S1-BE-BLOB_LOG_BODY_MAX-weak`

- **File:line** `backend/tests/test_storage_blob.py:1426`
- **Mutation** — S1 backend / BLOB_LOG_BODY_MAX / weakening (loosen the bound)
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '1426p' <scratchpad>/snap/S1-BE-BLOB_LOG_BODY_MAX-weak.test_storage_blob.py
      assert storage_service.BLOB_LOG_BODY_MAX_BYTES == 512
  $ sed -n '1426p' backend/tests/test_storage_blob.py
      assert storage_service.BLOB_LOG_BODY_MAX_BYTES == 511
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_storage_blob.py`
- **Step-0 baseline** reused run **B-10** — `107 passed, 5 warnings in 0.94s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/tests/test_storage_blob.py` was empty at snapshot; (b) every `cmp` since B-10 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i19`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `2 failed, 105 passed, 5 warnings in 0.96s`; exit 1
- **Reddened vs that baseline** (2) — `tests/test_storage_blob.py::test_a_long_refusal_body_is_bounded_in_bytes_and_marked[ascii]`, `tests/test_storage_blob.py::test_a_long_refusal_body_is_bounded_in_bytes_and_marked[multibyte]`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `242d874ed642217158d183a7b56f0337d51730e99fdaa008a6e8095ac0f27d5f`; restored file `shasum -a 256` = `242d874ed642217158d183a7b56f0337d51730e99fdaa008a6e8095ac0f27d5f`; `cmp <scratchpad>/snap/S1-BE-BLOB_LOG_BODY_MAX-weak.test_storage_blob.py backend/tests/test_storage_blob.py` → clean (no output).

#### `S1-BE-BLOB_LOG_BODY_MAX-strong`

- **File:line** `backend/tests/test_storage_blob.py:1426`
- **Mutation** — S1 backend / BLOB_LOG_BODY_MAX / strengthening (tighten the bound)
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '1426p' <scratchpad>/snap/S1-BE-BLOB_LOG_BODY_MAX-strong.test_storage_blob.py
      assert storage_service.BLOB_LOG_BODY_MAX_BYTES == 512
  $ sed -n '1426p' backend/tests/test_storage_blob.py
      assert storage_service.BLOB_LOG_BODY_MAX_BYTES == 513
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_storage_blob.py`
- **Step-0 baseline** reused run **B-10** — `107 passed, 5 warnings in 0.94s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/tests/test_storage_blob.py` was empty at snapshot; (b) every `cmp` since B-10 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i20`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `2 failed, 105 passed, 5 warnings in 0.98s`; exit 1
- **Reddened vs that baseline** (2) — `tests/test_storage_blob.py::test_a_long_refusal_body_is_bounded_in_bytes_and_marked[ascii]`, `tests/test_storage_blob.py::test_a_long_refusal_body_is_bounded_in_bytes_and_marked[multibyte]`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `242d874ed642217158d183a7b56f0337d51730e99fdaa008a6e8095ac0f27d5f`; restored file `shasum -a 256` = `242d874ed642217158d183a7b56f0337d51730e99fdaa008a6e8095ac0f27d5f`; `cmp <scratchpad>/snap/S1-BE-BLOB_LOG_BODY_MAX-strong.test_storage_blob.py backend/tests/test_storage_blob.py` → clean (no output).

#### `S1-BE-DATED_SCHEMA_FLOOR-weak`

- **File:line** `backend/tests/test_suite_hygiene.py:293`
- **Mutation** — S1 backend / DATED_SCHEMA_FLOOR / weakening (loosen the bound)
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '293p' <scratchpad>/snap/S1-BE-DATED_SCHEMA_FLOOR-weak.test_suite_hygiene.py
  DATED_SCHEMA_FLOOR = 70
  $ sed -n '293p' backend/tests/test_suite_hygiene.py
  DATED_SCHEMA_FLOOR = 1
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_suite_hygiene.py`
- **Step-0 baseline** run **B-11** (own run, same command on the unmutated file) — `9 passed, 1 warning in 0.95s`; exit 0; `uv pip freeze` captured as `freeze.B-11`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `9 passed, 1 warning in 0.86s`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `tests/test_suite_hygiene.py::test_every_dated_schema_class_inherits_api_model`
- **Was it among the reddened?** no — correct for a weakening move on a vacuity floor
- **Step-5 restore** pristine copy `shasum -a 256` = `58794265e4b69896790d3e1f0468b5588b1e74424253c7ada69936cf0463aecf`; restored file `shasum -a 256` = `58794265e4b69896790d3e1f0468b5588b1e74424253c7ada69936cf0463aecf`; `cmp <scratchpad>/snap/S1-BE-DATED_SCHEMA_FLOOR-weak.test_suite_hygiene.py backend/tests/test_suite_hygiene.py` → clean (no output).

#### `S1-BE-DATED_SCHEMA_FLOOR-strong`

- **File:line** `backend/tests/test_suite_hygiene.py:293`
- **Mutation** — S1 backend / DATED_SCHEMA_FLOOR / strengthening (tighten the bound)
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '293p' <scratchpad>/snap/S1-BE-DATED_SCHEMA_FLOOR-strong.test_suite_hygiene.py
  DATED_SCHEMA_FLOOR = 70
  $ sed -n '293p' backend/tests/test_suite_hygiene.py
  DATED_SCHEMA_FLOOR = 100000
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_suite_hygiene.py`
- **Step-0 baseline** reused run **B-11** — `9 passed, 1 warning in 0.95s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/tests/test_suite_hygiene.py` was empty at snapshot; (b) every `cmp` since B-11 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i21`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `1 failed, 8 passed, 1 warning in 0.84s`; exit 1
- **Reddened vs that baseline** (1) — `tests/test_suite_hygiene.py::test_every_dated_schema_class_inherits_api_model`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `58794265e4b69896790d3e1f0468b5588b1e74424253c7ada69936cf0463aecf`; restored file `shasum -a 256` = `58794265e4b69896790d3e1f0468b5588b1e74424253c7ada69936cf0463aecf`; `cmp <scratchpad>/snap/S1-BE-DATED_SCHEMA_FLOOR-strong.test_suite_hygiene.py backend/tests/test_suite_hygiene.py` → clean (no output).

#### `S1-BE-MAX_PER_TEST_TIMEOUT-weak`

- **File:line** `backend/tests/test_suite_hygiene.py:55`
- **Mutation** — S1 backend / MAX_PER_TEST_TIMEOUT / weakening (loosen the bound)
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '55p' <scratchpad>/snap/S1-BE-MAX_PER_TEST_TIMEOUT-weak.test_suite_hygiene.py
  MAX_PER_TEST_TIMEOUT = 600
  $ sed -n '55p' backend/tests/test_suite_hygiene.py
  MAX_PER_TEST_TIMEOUT = 100000
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_suite_hygiene.py`
- **Step-0 baseline** reused run **B-11** — `9 passed, 1 warning in 0.95s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/tests/test_suite_hygiene.py` was empty at snapshot; (b) every `cmp` since B-11 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i22`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `9 passed, 1 warning in 0.94s`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `tests/test_suite_hygiene.py::test_pytest_ini_caps_a_single_test`
- **Was it among the reddened?** no — correct for a weakening move on a ceiling-on-a-ceiling
- **Step-5 restore** pristine copy `shasum -a 256` = `58794265e4b69896790d3e1f0468b5588b1e74424253c7ada69936cf0463aecf`; restored file `shasum -a 256` = `58794265e4b69896790d3e1f0468b5588b1e74424253c7ada69936cf0463aecf`; `cmp <scratchpad>/snap/S1-BE-MAX_PER_TEST_TIMEOUT-weak.test_suite_hygiene.py backend/tests/test_suite_hygiene.py` → clean (no output).

#### `S1-BE-MAX_PER_TEST_TIMEOUT-strong`

- **File:line** `backend/tests/test_suite_hygiene.py:55`
- **Mutation** — S1 backend / MAX_PER_TEST_TIMEOUT / strengthening (tighten the bound)
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '55p' <scratchpad>/snap/S1-BE-MAX_PER_TEST_TIMEOUT-strong.test_suite_hygiene.py
  MAX_PER_TEST_TIMEOUT = 600
  $ sed -n '55p' backend/tests/test_suite_hygiene.py
  MAX_PER_TEST_TIMEOUT = 1
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_suite_hygiene.py`
- **Step-0 baseline** reused run **B-11** — `9 passed, 1 warning in 0.95s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/tests/test_suite_hygiene.py` was empty at snapshot; (b) every `cmp` since B-11 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i23`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `1 failed, 8 passed, 1 warning in 0.92s`; exit 1
- **Reddened vs that baseline** (1) — `tests/test_suite_hygiene.py::test_pytest_ini_caps_a_single_test`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `58794265e4b69896790d3e1f0468b5588b1e74424253c7ada69936cf0463aecf`; restored file `shasum -a 256` = `58794265e4b69896790d3e1f0468b5588b1e74424253c7ada69936cf0463aecf`; `cmp <scratchpad>/snap/S1-BE-MAX_PER_TEST_TIMEOUT-strong.test_suite_hygiene.py backend/tests/test_suite_hygiene.py` → clean (no output).

#### `S1-BE-LOGO_MAX-weak`

- **File:line** `backend/tests/test_tenant_profile.py:1166`
- **Mutation** — S1 backend / LOGO_MAX / weakening (loosen the bound)
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '1166p' <scratchpad>/snap/S1-BE-LOGO_MAX-weak.test_tenant_profile.py
      assert TenantService.LOGO_MAX_FILE_SIZE == 2 * 1024 * 1024, (
  $ sed -n '1166p' backend/tests/test_tenant_profile.py
      assert TenantService.LOGO_MAX_FILE_SIZE == 1 * 1024 * 1024, (
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_tenant_profile.py`
- **Step-0 baseline** run **B-12** (own run, same command on the unmutated file) — `66 passed, 175 warnings in 3.38s`; exit 0; `uv pip freeze` captured as `freeze.B-12`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `1 failed, 65 passed, 175 warnings in 4.22s`; exit 1
- **Reddened vs that baseline** (1) — `tests/test_tenant_profile.py::test_the_profile_contract_matches_the_frontend_client`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `b934535b623d535058120679ece570350752ca016f154d8d50ae29e9df4ef9c5`; restored file `shasum -a 256` = `b934535b623d535058120679ece570350752ca016f154d8d50ae29e9df4ef9c5`; `cmp <scratchpad>/snap/S1-BE-LOGO_MAX-weak.test_tenant_profile.py backend/tests/test_tenant_profile.py` → clean (no output).

#### `S1-BE-LOGO_MAX-strong`

- **File:line** `backend/tests/test_tenant_profile.py:1166`
- **Mutation** — S1 backend / LOGO_MAX / strengthening (tighten the bound)
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '1166p' <scratchpad>/snap/S1-BE-LOGO_MAX-strong.test_tenant_profile.py
      assert TenantService.LOGO_MAX_FILE_SIZE == 2 * 1024 * 1024, (
  $ sed -n '1166p' backend/tests/test_tenant_profile.py
      assert TenantService.LOGO_MAX_FILE_SIZE == 3 * 1024 * 1024, (
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_tenant_profile.py`
- **Step-0 baseline** reused run **B-12** — `66 passed, 175 warnings in 3.38s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/tests/test_tenant_profile.py` was empty at snapshot; (b) every `cmp` since B-12 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i24`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `1 failed, 65 passed, 175 warnings in 3.36s`; exit 1
- **Reddened vs that baseline** (1) — `tests/test_tenant_profile.py::test_the_profile_contract_matches_the_frontend_client`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `b934535b623d535058120679ece570350752ca016f154d8d50ae29e9df4ef9c5`; restored file `shasum -a 256` = `b934535b623d535058120679ece570350752ca016f154d8d50ae29e9df4ef9c5`; `cmp <scratchpad>/snap/S1-BE-LOGO_MAX-strong.test_tenant_profile.py backend/tests/test_tenant_profile.py` → clean (no output).

#### `S1-BE-UPLOAD_MAX-weak`

- **File:line** `backend/tests/test_uploads.py:259`
- **Mutation** — S1 backend / UPLOAD_MAX / weakening (loosen the bound)
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '259p' <scratchpad>/snap/S1-BE-UPLOAD_MAX-weak.test_uploads.py
      assert media_service_module.MAX_FILE_SIZE == 5 * 1024 * 1024, (
  $ sed -n '259p' backend/tests/test_uploads.py
      assert media_service_module.MAX_FILE_SIZE == 4 * 1024 * 1024, (
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_uploads.py`
- **Step-0 baseline** run **B-13** (own run, same command on the unmutated file) — `8 passed, 23 warnings in 0.65s`; exit 0; `uv pip freeze` captured as `freeze.B-13`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `1 failed, 7 passed, 23 warnings in 0.54s`; exit 1
- **Reddened vs that baseline** (1) — `tests/test_uploads.py::test_the_upload_contract_matches_the_infraction_uploader`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `71231cab302a3ea9f0aade846a07597a4ba6d1ad6b84bd3d1314753387434626`; restored file `shasum -a 256` = `71231cab302a3ea9f0aade846a07597a4ba6d1ad6b84bd3d1314753387434626`; `cmp <scratchpad>/snap/S1-BE-UPLOAD_MAX-weak.test_uploads.py backend/tests/test_uploads.py` → clean (no output).

#### `S1-BE-UPLOAD_MAX-strong`

- **File:line** `backend/tests/test_uploads.py:259`
- **Mutation** — S1 backend / UPLOAD_MAX / strengthening (tighten the bound)
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '259p' <scratchpad>/snap/S1-BE-UPLOAD_MAX-strong.test_uploads.py
      assert media_service_module.MAX_FILE_SIZE == 5 * 1024 * 1024, (
  $ sed -n '259p' backend/tests/test_uploads.py
      assert media_service_module.MAX_FILE_SIZE == 6 * 1024 * 1024, (
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_uploads.py`
- **Step-0 baseline** reused run **B-13** — `8 passed, 23 warnings in 0.65s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/tests/test_uploads.py` was empty at snapshot; (b) every `cmp` since B-13 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i25`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `1 failed, 7 passed, 23 warnings in 0.55s`; exit 1
- **Reddened vs that baseline** (1) — `tests/test_uploads.py::test_the_upload_contract_matches_the_infraction_uploader`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `71231cab302a3ea9f0aade846a07597a4ba6d1ad6b84bd3d1314753387434626`; restored file `shasum -a 256` = `71231cab302a3ea9f0aade846a07597a4ba6d1ad6b84bd3d1314753387434626`; `cmp <scratchpad>/snap/S1-BE-UPLOAD_MAX-strong.test_uploads.py backend/tests/test_uploads.py` → clean (no output).

#### `S1-BE-BCRYPT_ROUNDS-prod-13`

- **File:line** `backend/app/core/security.py:27`
- **Mutation** — S1 over-pin probe / production BCRYPT_ROUNDS raised 12 -> 13 (the direction the ratchet allows)
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '27p' <scratchpad>/snap/S1-BE-BCRYPT_ROUNDS-prod-13.security.py
  BCRYPT_ROUNDS = 12
  $ sed -n '27p' backend/app/core/security.py
  BCRYPT_ROUNDS = 13
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_bcrypt_cost.py`
- **Step-0 baseline** reused run **B-01** — `1 failed, 9 passed, 1 warning in 1.96s`; failing pre-mutation: `tests/test_bcrypt_cost.py::test_passlib_is_not_installed`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/app/core/security.py` was empty at snapshot; (b) every `cmp` since B-01 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i26`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `1 failed, 9 passed, 1 warning in 2.36s`; exit 1
- **Reddened vs that baseline** none
- **Case under examination** `tests/test_bcrypt_cost.py::test_the_production_floor_constant_is_a_ratchet`
- **Was it among the reddened?** no — and this is the Over-pins answer the spec asks for by name: raising the production cost to 13 keeps the module green, so the ratchet genuinely ratchets and the module is **not** an over-pin
- **Step-5 restore** pristine copy `shasum -a 256` = `7f9ff25e27959c23eeff9fcd31b3f36c7316cecb1944c4c0d9ffa9a3685b17c9`; restored file `shasum -a 256` = `7f9ff25e27959c23eeff9fcd31b3f36c7316cecb1944c4c0d9ffa9a3685b17c9`; `cmp <scratchpad>/snap/S1-BE-BCRYPT_ROUNDS-prod-13.security.py backend/app/core/security.py` → clean (no output).

#### `S1-FE-MINIMUM_PAIRS-lower`

- **File:line** `frontend/src/__tests__/themeContrast.test.ts:172`
- **Mutation** — S1 frontend / MINIMUM_PAIRS / lower
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '172p' <scratchpad>/snap/S1-FE-MINIMUM_PAIRS-lower.themeContrast.test.ts
  const MINIMUM_PAIRS = 23;
  $ sed -n '172p' frontend/src/__tests__/themeContrast.test.ts
  const MINIMUM_PAIRS = 1;
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S1-FE-MINIMUM_PAIRS-lower.json src/__tests__/themeContrast.test.ts`
- **Step-0 baseline** run **B-14** (own run, same command on the unmutated file) — `12 tests: 12 passed, 0 failed (files 1)`; exit 0; `uv pip freeze` captured as `freeze.B-14`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `12 tests: 12 passed, 0 failed (files 1)`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `src/__tests__/themeContrast.test.ts > src/index.css derives every light pair from the file`
- **Was it among the reddened?** no — correct for a weakening move on a minimum-count floor
- **Step-5 restore** pristine copy `shasum -a 256` = `9b02be579c3fd3b04a2064bc60bd059bf5ed5f64b8fc622e19889923d92d1f57`; restored file `shasum -a 256` = `9b02be579c3fd3b04a2064bc60bd059bf5ed5f64b8fc622e19889923d92d1f57`; `cmp <scratchpad>/snap/S1-FE-MINIMUM_PAIRS-lower.themeContrast.test.ts frontend/src/__tests__/themeContrast.test.ts` → clean (no output).

#### `S1-FE-MINIMUM_PAIRS-higher`

- **File:line** `frontend/src/__tests__/themeContrast.test.ts:172`
- **Mutation** — S1 frontend / MINIMUM_PAIRS / higher
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '172p' <scratchpad>/snap/S1-FE-MINIMUM_PAIRS-higher.themeContrast.test.ts
  const MINIMUM_PAIRS = 23;
  $ sed -n '172p' frontend/src/__tests__/themeContrast.test.ts
  const MINIMUM_PAIRS = 10000;
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S1-FE-MINIMUM_PAIRS-higher.json src/__tests__/themeContrast.test.ts`
- **Step-0 baseline** reused run **B-14** — `12 tests: 12 passed, 0 failed (files 1)`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- frontend/src/__tests__/themeContrast.test.ts` was empty at snapshot; (b) every `cmp` since B-14 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i27`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `12 tests: 9 passed, 3 failed (files 1)`; exit 1
- **Reddened vs that baseline** (3) — `src/index.css declares both schemes`, `src/index.css derives every dark pair from the file`, `src/index.css derives every light pair from the file`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `9b02be579c3fd3b04a2064bc60bd059bf5ed5f64b8fc622e19889923d92d1f57`; restored file `shasum -a 256` = `9b02be579c3fd3b04a2064bc60bd059bf5ed5f64b8fc622e19889923d92d1f57`; `cmp <scratchpad>/snap/S1-FE-MINIMUM_PAIRS-higher.themeContrast.test.ts frontend/src/__tests__/themeContrast.test.ts` → clean (no output).

#### `S1-FE-MINIMUM_RATIO-lower`

- **File:line** `frontend/src/__tests__/themeContrast.test.ts:53`
- **Mutation** — S1 frontend / MINIMUM_RATIO / lower
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '53p' <scratchpad>/snap/S1-FE-MINIMUM_RATIO-lower.themeContrast.test.ts
  const MINIMUM_RATIO = 4.5;
  $ sed -n '53p' frontend/src/__tests__/themeContrast.test.ts
  const MINIMUM_RATIO = 1.0;
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S1-FE-MINIMUM_RATIO-lower.json src/__tests__/themeContrast.test.ts`
- **Step-0 baseline** reused run **B-14** — `12 tests: 12 passed, 0 failed (files 1)`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- frontend/src/__tests__/themeContrast.test.ts` was empty at snapshot; (b) every `cmp` since B-14 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i28`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `12 tests: 11 passed, 1 failed (files 1)`; exit 1
- **Reddened vs that baseline** (1) — `the measurement measures the pair APRAS-88 repaired at its stated ratios`
- **Case under examination** `src/__tests__/themeContrast.test.ts > src/index.css meets WCAG AA on every light pair`
- **Was it among the reddened?** no — the move reddened a *neighbour* (`the measurement measures the pair APRAS-88 repaired at its stated ratios`) and not the AA cases. Recorded as a neighbour-only reddening; it is not a finding, because the neighbour is a legitimate second consumer of the constant and the AA cases are correctly slack downward
- **Step-5 restore** pristine copy `shasum -a 256` = `9b02be579c3fd3b04a2064bc60bd059bf5ed5f64b8fc622e19889923d92d1f57`; restored file `shasum -a 256` = `9b02be579c3fd3b04a2064bc60bd059bf5ed5f64b8fc622e19889923d92d1f57`; `cmp <scratchpad>/snap/S1-FE-MINIMUM_RATIO-lower.themeContrast.test.ts frontend/src/__tests__/themeContrast.test.ts` → clean (no output).

#### `S1-FE-MINIMUM_RATIO-higher`

- **File:line** `frontend/src/__tests__/themeContrast.test.ts:53`
- **Mutation** — S1 frontend / MINIMUM_RATIO / higher
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '53p' <scratchpad>/snap/S1-FE-MINIMUM_RATIO-higher.themeContrast.test.ts
  const MINIMUM_RATIO = 4.5;
  $ sed -n '53p' frontend/src/__tests__/themeContrast.test.ts
  const MINIMUM_RATIO = 21.0;
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S1-FE-MINIMUM_RATIO-higher.json src/__tests__/themeContrast.test.ts`
- **Step-0 baseline** reused run **B-14** — `12 tests: 12 passed, 0 failed (files 1)`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- frontend/src/__tests__/themeContrast.test.ts` was empty at snapshot; (b) every `cmp` since B-14 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i29`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `12 tests: 10 passed, 2 failed (files 1)`; exit 1
- **Reddened vs that baseline** (2) — `src/index.css meets WCAG AA on every dark pair`, `src/index.css meets WCAG AA on every light pair`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `9b02be579c3fd3b04a2064bc60bd059bf5ed5f64b8fc622e19889923d92d1f57`; restored file `shasum -a 256` = `9b02be579c3fd3b04a2064bc60bd059bf5ed5f64b8fc622e19889923d92d1f57`; `cmp <scratchpad>/snap/S1-FE-MINIMUM_RATIO-higher.themeContrast.test.ts frontend/src/__tests__/themeContrast.test.ts` → clean (no output).

#### `S1-FE-MINIMUM_CONTRAST_RATIO-lower`

- **File:line** `frontend/src/lib/contrast.ts:50`
- **Mutation** — S1 frontend / MINIMUM_CONTRAST_RATIO / lower
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '50p' <scratchpad>/snap/S1-FE-MINIMUM_CONTRAST_RATIO-lower.contrast.ts
  export const MINIMUM_CONTRAST_RATIO = 4.5;
  $ sed -n '50p' frontend/src/lib/contrast.ts
  export const MINIMUM_CONTRAST_RATIO = 1.0;
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S1-FE-MINIMUM_CONTRAST_RATIO-lower.json src/lib/__tests__/contrast.test.ts`
- **Step-0 baseline** run **B-15** (own run, same command on the unmutated file) — `36 tests: 36 passed, 0 failed (files 1)`; exit 0; `uv pip freeze` captured as `freeze.B-15`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `36 tests: 33 passed, 3 failed (files 1)`; exit 1
- **Reddened vs that baseline** (3) — `auditHexPalette names every pair of black text on a near-black background`, `auditScheme names the failing pair and its measured ratio`, `contrast.ts against the shared fixture pins the same minimum the backend does`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `2949bba8c67b2c518d1267f2ba35b1debf69048780acc0041c94abae43ad2895`; restored file `shasum -a 256` = `2949bba8c67b2c518d1267f2ba35b1debf69048780acc0041c94abae43ad2895`; `cmp <scratchpad>/snap/S1-FE-MINIMUM_CONTRAST_RATIO-lower.contrast.ts frontend/src/lib/contrast.ts` → clean (no output).

#### `S1-FE-MINIMUM_CONTRAST_RATIO-higher`

- **File:line** `frontend/src/lib/contrast.ts:50`
- **Mutation** — S1 frontend / MINIMUM_CONTRAST_RATIO / higher
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '50p' <scratchpad>/snap/S1-FE-MINIMUM_CONTRAST_RATIO-higher.contrast.ts
  export const MINIMUM_CONTRAST_RATIO = 4.5;
  $ sed -n '50p' frontend/src/lib/contrast.ts
  export const MINIMUM_CONTRAST_RATIO = 21.0;
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S1-FE-MINIMUM_CONTRAST_RATIO-higher.json src/lib/__tests__/contrast.test.ts`
- **Step-0 baseline** reused run **B-15** — `36 tests: 36 passed, 0 failed (files 1)`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- frontend/src/lib/contrast.ts` was empty at snapshot; (b) every `cmp` since B-15 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i30`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `36 tests: 28 passed, 8 failed (files 1)`; exit 1
- **Reddened vs that baseline** (8) — `auditHexPalette drops a malformed value rather than guessing at a colour`, `auditHexPalette returns nothing for the readable preset`, `auditScheme names the failing pair and its measured ratio`, `auditScheme returns nothing for a scheme every pair of which clears AA`, `auditScheme skips a pair it cannot parse rather than inventing a ratio`, `auditScheme skips a pair whose surface key is absent altogether`, `auditScheme skips a pair whose text key is absent altogether`, `contrast.ts against the shared fixture pins the same minimum the backend does`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `2949bba8c67b2c518d1267f2ba35b1debf69048780acc0041c94abae43ad2895`; restored file `shasum -a 256` = `2949bba8c67b2c518d1267f2ba35b1debf69048780acc0041c94abae43ad2895`; `cmp <scratchpad>/snap/S1-FE-MINIMUM_CONTRAST_RATIO-higher.contrast.ts frontend/src/lib/contrast.ts` → clean (no output).

#### `S1-FE-QUOTE_ATTACHMENT_MAX-lower`

- **File:line** `frontend/src/api/purchases.ts:26`
- **Mutation** — S1 frontend / QUOTE_ATTACHMENT_MAX / lower
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '26p' <scratchpad>/snap/S1-FE-QUOTE_ATTACHMENT_MAX-lower.purchases.ts
  export const QUOTE_ATTACHMENT_MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024;
  $ sed -n '26p' frontend/src/api/purchases.ts
  export const QUOTE_ATTACHMENT_MAX_FILE_SIZE_BYTES = 4 * 1024 * 1024;
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S1-FE-QUOTE_ATTACHMENT_MAX-lower.json src/features/purchase-management/__tests__/quoteAttachmentContract.test.ts`
- **Step-0 baseline** run **B-16** (own run, same command on the unmutated file) — `3 tests: 3 passed, 0 failed (files 1)`; exit 0; `uv pip freeze` captured as `freeze.B-16`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `3 tests: 2 passed, 1 failed (files 1)`; exit 1
- **Reddened vs that baseline** (1) — `the quote-attachment contract pins the cap, the accepted set and the derived accept attribute`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `12d1035f58d9161391e1d444d5218589a9d5abf144dc640825e5b93a50e8433e`; restored file `shasum -a 256` = `12d1035f58d9161391e1d444d5218589a9d5abf144dc640825e5b93a50e8433e`; `cmp <scratchpad>/snap/S1-FE-QUOTE_ATTACHMENT_MAX-lower.purchases.ts frontend/src/api/purchases.ts` → clean (no output).

#### `S1-FE-QUOTE_ATTACHMENT_MAX-higher`

- **File:line** `frontend/src/api/purchases.ts:26`
- **Mutation** — S1 frontend / QUOTE_ATTACHMENT_MAX / higher
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '26p' <scratchpad>/snap/S1-FE-QUOTE_ATTACHMENT_MAX-higher.purchases.ts
  export const QUOTE_ATTACHMENT_MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024;
  $ sed -n '26p' frontend/src/api/purchases.ts
  export const QUOTE_ATTACHMENT_MAX_FILE_SIZE_BYTES = 6 * 1024 * 1024;
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S1-FE-QUOTE_ATTACHMENT_MAX-higher.json src/features/purchase-management/__tests__/quoteAttachmentContract.test.ts`
- **Step-0 baseline** reused run **B-16** — `3 tests: 3 passed, 0 failed (files 1)`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- frontend/src/api/purchases.ts` was empty at snapshot; (b) every `cmp` since B-16 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i31`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `3 tests: 2 passed, 1 failed (files 1)`; exit 1
- **Reddened vs that baseline** (1) — `the quote-attachment contract pins the cap, the accepted set and the derived accept attribute`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `12d1035f58d9161391e1d444d5218589a9d5abf144dc640825e5b93a50e8433e`; restored file `shasum -a 256` = `12d1035f58d9161391e1d444d5218589a9d5abf144dc640825e5b93a50e8433e`; `cmp <scratchpad>/snap/S1-FE-QUOTE_ATTACHMENT_MAX-higher.purchases.ts frontend/src/api/purchases.ts` → clean (no output).

#### `S1-FE-FE_SLUG_MIN_LENGTH-lower`

- **File:line** `frontend/src/api/tenantProfile.ts:139`
- **Mutation** — S1 frontend / FE_SLUG_MIN_LENGTH / lower
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '139p' <scratchpad>/snap/S1-FE-FE_SLUG_MIN_LENGTH-lower.tenantProfile.ts
  export const SLUG_MIN_LENGTH = 3;
  $ sed -n '139p' frontend/src/api/tenantProfile.ts
  export const SLUG_MIN_LENGTH = 2;
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S1-FE-FE_SLUG_MIN_LENGTH-lower.json src/features/user-administration/__tests__/TenantProfilePage.test.tsx`
- **Step-0 baseline** run **B-17** (own run, same command on the unmutated file) — `22 tests: 22 passed, 0 failed (files 1)`; exit 0; `uv pip freeze` captured as `freeze.B-17`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `22 tests: 21 passed, 1 failed (files 1)`; exit 1
- **Reddened vs that baseline** (1) — `TenantProfilePage — the slug (APRAS-66) mirrors the server's rule, and only mirrors it`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `716b4cd3ef8328cff33e8013a8aa836e6eca86ce0924ff4b78f97a0ec27bf257`; restored file `shasum -a 256` = `716b4cd3ef8328cff33e8013a8aa836e6eca86ce0924ff4b78f97a0ec27bf257`; `cmp <scratchpad>/snap/S1-FE-FE_SLUG_MIN_LENGTH-lower.tenantProfile.ts frontend/src/api/tenantProfile.ts` → clean (no output).

#### `S1-FE-FE_SLUG_MIN_LENGTH-higher`

- **File:line** `frontend/src/api/tenantProfile.ts:139`
- **Mutation** — S1 frontend / FE_SLUG_MIN_LENGTH / higher
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '139p' <scratchpad>/snap/S1-FE-FE_SLUG_MIN_LENGTH-higher.tenantProfile.ts
  export const SLUG_MIN_LENGTH = 3;
  $ sed -n '139p' frontend/src/api/tenantProfile.ts
  export const SLUG_MIN_LENGTH = 4;
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S1-FE-FE_SLUG_MIN_LENGTH-higher.json src/features/user-administration/__tests__/TenantProfilePage.test.tsx`
- **Step-0 baseline** reused run **B-17** — `22 tests: 22 passed, 0 failed (files 1)`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- frontend/src/api/tenantProfile.ts` was empty at snapshot; (b) every `cmp` since B-17 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i32`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `22 tests: 21 passed, 1 failed (files 1)`; exit 1
- **Reddened vs that baseline** (1) — `TenantProfilePage — the slug (APRAS-66) mirrors the server's rule, and only mirrors it`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `716b4cd3ef8328cff33e8013a8aa836e6eca86ce0924ff4b78f97a0ec27bf257`; restored file `shasum -a 256` = `716b4cd3ef8328cff33e8013a8aa836e6eca86ce0924ff4b78f97a0ec27bf257`; `cmp <scratchpad>/snap/S1-FE-FE_SLUG_MIN_LENGTH-higher.tenantProfile.ts frontend/src/api/tenantProfile.ts` → clean (no output).

#### `S1-FE-FE_SLUG_MAX_LENGTH-lower`

- **File:line** `frontend/src/api/tenantProfile.ts:140`
- **Mutation** — S1 frontend / FE_SLUG_MAX_LENGTH / lower
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '140p' <scratchpad>/snap/S1-FE-FE_SLUG_MAX_LENGTH-lower.tenantProfile.ts
  export const SLUG_MAX_LENGTH = 64;
  $ sed -n '140p' frontend/src/api/tenantProfile.ts
  export const SLUG_MAX_LENGTH = 63;
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S1-FE-FE_SLUG_MAX_LENGTH-lower.json src/features/user-administration/__tests__/TenantProfilePage.test.tsx`
- **Step-0 baseline** reused run **B-17** — `22 tests: 22 passed, 0 failed (files 1)`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- frontend/src/api/tenantProfile.ts` was empty at snapshot; (b) every `cmp` since B-17 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i33`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `22 tests: 21 passed, 1 failed (files 1)`; exit 1
- **Reddened vs that baseline** (1) — `TenantProfilePage — the slug (APRAS-66) mirrors the server's rule, and only mirrors it`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `716b4cd3ef8328cff33e8013a8aa836e6eca86ce0924ff4b78f97a0ec27bf257`; restored file `shasum -a 256` = `716b4cd3ef8328cff33e8013a8aa836e6eca86ce0924ff4b78f97a0ec27bf257`; `cmp <scratchpad>/snap/S1-FE-FE_SLUG_MAX_LENGTH-lower.tenantProfile.ts frontend/src/api/tenantProfile.ts` → clean (no output).

#### `S1-FE-FE_SLUG_MAX_LENGTH-higher`

- **File:line** `frontend/src/api/tenantProfile.ts:140`
- **Mutation** — S1 frontend / FE_SLUG_MAX_LENGTH / higher
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '140p' <scratchpad>/snap/S1-FE-FE_SLUG_MAX_LENGTH-higher.tenantProfile.ts
  export const SLUG_MAX_LENGTH = 64;
  $ sed -n '140p' frontend/src/api/tenantProfile.ts
  export const SLUG_MAX_LENGTH = 65;
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S1-FE-FE_SLUG_MAX_LENGTH-higher.json src/features/user-administration/__tests__/TenantProfilePage.test.tsx`
- **Step-0 baseline** reused run **B-17** — `22 tests: 22 passed, 0 failed (files 1)`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- frontend/src/api/tenantProfile.ts` was empty at snapshot; (b) every `cmp` since B-17 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i34`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `22 tests: 21 passed, 1 failed (files 1)`; exit 1
- **Reddened vs that baseline** (1) — `TenantProfilePage — the slug (APRAS-66) mirrors the server's rule, and only mirrors it`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `716b4cd3ef8328cff33e8013a8aa836e6eca86ce0924ff4b78f97a0ec27bf257`; restored file `shasum -a 256` = `716b4cd3ef8328cff33e8013a8aa836e6eca86ce0924ff4b78f97a0ec27bf257`; `cmp <scratchpad>/snap/S1-FE-FE_SLUG_MAX_LENGTH-higher.tenantProfile.ts frontend/src/api/tenantProfile.ts` → clean (no output).

#### `S1-FE-SLUG_MAX_BASE_LENGTH-lower`

- **File:line** `frontend/src/api/tenantProfile.ts:145`
- **Mutation** — S1 frontend / SLUG_MAX_BASE_LENGTH / lower
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '145p' <scratchpad>/snap/S1-FE-SLUG_MAX_BASE_LENGTH-lower.tenantProfile.ts
  const SLUG_MAX_BASE_LENGTH = 60;
  $ sed -n '145p' frontend/src/api/tenantProfile.ts
  const SLUG_MAX_BASE_LENGTH = 59;
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S1-FE-SLUG_MAX_BASE_LENGTH-lower.json src/features/user-administration/__tests__/TenantProfilePage.test.tsx`
- **Step-0 baseline** reused run **B-17** — `22 tests: 22 passed, 0 failed (files 1)`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- frontend/src/api/tenantProfile.ts` was empty at snapshot; (b) every `cmp` since B-17 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i35`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `22 tests: 22 passed, 0 failed (files 1)`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `no case names it — see Findings F-02`
- **Was it among the reddened?** no
- **Step-5 restore** pristine copy `shasum -a 256` = `716b4cd3ef8328cff33e8013a8aa836e6eca86ce0924ff4b78f97a0ec27bf257`; restored file `shasum -a 256` = `716b4cd3ef8328cff33e8013a8aa836e6eca86ce0924ff4b78f97a0ec27bf257`; `cmp <scratchpad>/snap/S1-FE-SLUG_MAX_BASE_LENGTH-lower.tenantProfile.ts frontend/src/api/tenantProfile.ts` → clean (no output).

#### `S1-FE-SLUG_MAX_BASE_LENGTH-higher`

- **File:line** `frontend/src/api/tenantProfile.ts:145`
- **Mutation** — S1 frontend / SLUG_MAX_BASE_LENGTH / higher
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '145p' <scratchpad>/snap/S1-FE-SLUG_MAX_BASE_LENGTH-higher.tenantProfile.ts
  const SLUG_MAX_BASE_LENGTH = 60;
  $ sed -n '145p' frontend/src/api/tenantProfile.ts
  const SLUG_MAX_BASE_LENGTH = 61;
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S1-FE-SLUG_MAX_BASE_LENGTH-higher.json src/features/user-administration/__tests__/TenantProfilePage.test.tsx`
- **Step-0 baseline** reused run **B-17** — `22 tests: 22 passed, 0 failed (files 1)`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- frontend/src/api/tenantProfile.ts` was empty at snapshot; (b) every `cmp` since B-17 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i36`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `22 tests: 22 passed, 0 failed (files 1)`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `no case names it — see Findings F-02`
- **Was it among the reddened?** no
- **Step-5 restore** pristine copy `shasum -a 256` = `716b4cd3ef8328cff33e8013a8aa836e6eca86ce0924ff4b78f97a0ec27bf257`; restored file `shasum -a 256` = `716b4cd3ef8328cff33e8013a8aa836e6eca86ce0924ff4b78f97a0ec27bf257`; `cmp <scratchpad>/snap/S1-FE-SLUG_MAX_BASE_LENGTH-higher.tenantProfile.ts frontend/src/api/tenantProfile.ts` → clean (no output).

#### `S1-FE-TENANT_LOGO_MAX-lower`

- **File:line** `frontend/src/api/tenantProfile.ts:176`
- **Mutation** — S1 frontend / TENANT_LOGO_MAX / lower
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '176p' <scratchpad>/snap/S1-FE-TENANT_LOGO_MAX-lower.tenantProfile.ts
  export const TENANT_LOGO_MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024;
  $ sed -n '176p' frontend/src/api/tenantProfile.ts
  export const TENANT_LOGO_MAX_FILE_SIZE_BYTES = 1 * 1024 * 1024;
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S1-FE-TENANT_LOGO_MAX-lower.json src/features/user-administration/__tests__/TenantProfilePage.test.tsx`
- **Step-0 baseline** reused run **B-17** — `22 tests: 22 passed, 0 failed (files 1)`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- frontend/src/api/tenantProfile.ts` was empty at snapshot; (b) every `cmp` since B-17 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i37`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `22 tests: 21 passed, 1 failed (files 1)`; exit 1
- **Reddened vs that baseline** (1) — `the /admin/tenant-profile gate states the same four facts the backend pins from its side`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `716b4cd3ef8328cff33e8013a8aa836e6eca86ce0924ff4b78f97a0ec27bf257`; restored file `shasum -a 256` = `716b4cd3ef8328cff33e8013a8aa836e6eca86ce0924ff4b78f97a0ec27bf257`; `cmp <scratchpad>/snap/S1-FE-TENANT_LOGO_MAX-lower.tenantProfile.ts frontend/src/api/tenantProfile.ts` → clean (no output).

#### `S1-FE-TENANT_LOGO_MAX-higher`

- **File:line** `frontend/src/api/tenantProfile.ts:176`
- **Mutation** — S1 frontend / TENANT_LOGO_MAX / higher
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '176p' <scratchpad>/snap/S1-FE-TENANT_LOGO_MAX-higher.tenantProfile.ts
  export const TENANT_LOGO_MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024;
  $ sed -n '176p' frontend/src/api/tenantProfile.ts
  export const TENANT_LOGO_MAX_FILE_SIZE_BYTES = 3 * 1024 * 1024;
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S1-FE-TENANT_LOGO_MAX-higher.json src/features/user-administration/__tests__/TenantProfilePage.test.tsx`
- **Step-0 baseline** reused run **B-17** — `22 tests: 22 passed, 0 failed (files 1)`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- frontend/src/api/tenantProfile.ts` was empty at snapshot; (b) every `cmp` since B-17 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i38`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `22 tests: 21 passed, 1 failed (files 1)`; exit 1
- **Reddened vs that baseline** (1) — `the /admin/tenant-profile gate states the same four facts the backend pins from its side`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `716b4cd3ef8328cff33e8013a8aa836e6eca86ce0924ff4b78f97a0ec27bf257`; restored file `shasum -a 256` = `716b4cd3ef8328cff33e8013a8aa836e6eca86ce0924ff4b78f97a0ec27bf257`; `cmp <scratchpad>/snap/S1-FE-TENANT_LOGO_MAX-higher.tenantProfile.ts frontend/src/api/tenantProfile.ts` → clean (no output).

#### `S1-FE-UPLOAD_MAX_BYTES-lower`

- **File:line** `frontend/src/api/uploads.ts:28`
- **Mutation** — S1 frontend / UPLOAD_MAX_BYTES / lower
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '28p' <scratchpad>/snap/S1-FE-UPLOAD_MAX_BYTES-lower.uploads.ts
  export const UPLOAD_MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024;
  $ sed -n '28p' frontend/src/api/uploads.ts
  export const UPLOAD_MAX_FILE_SIZE_BYTES = 4 * 1024 * 1024;
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S1-FE-UPLOAD_MAX_BYTES-lower.json src/features/infraction-management/__tests__/uploadContract.test.tsx`
- **Step-0 baseline** run **B-18** (own run, same command on the unmutated file) — `13 tests: 13 passed, 0 failed (files 1)`; exit 0; `uv pip freeze` captured as `freeze.B-18`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `13 tests: 12 passed, 1 failed (files 1)`; exit 1
- **Reddened vs that baseline** (1) — `the five server facts, pinned from this side declares media_service.MAX_FILE_SIZE`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `6c970828520bb87dd1c9f63f51438f394acd0003feba1aabc2d61622c200abb8`; restored file `shasum -a 256` = `6c970828520bb87dd1c9f63f51438f394acd0003feba1aabc2d61622c200abb8`; `cmp <scratchpad>/snap/S1-FE-UPLOAD_MAX_BYTES-lower.uploads.ts frontend/src/api/uploads.ts` → clean (no output).

#### `S1-FE-UPLOAD_MAX_BYTES-higher`

- **File:line** `frontend/src/api/uploads.ts:28`
- **Mutation** — S1 frontend / UPLOAD_MAX_BYTES / higher
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '28p' <scratchpad>/snap/S1-FE-UPLOAD_MAX_BYTES-higher.uploads.ts
  export const UPLOAD_MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024;
  $ sed -n '28p' frontend/src/api/uploads.ts
  export const UPLOAD_MAX_FILE_SIZE_BYTES = 6 * 1024 * 1024;
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S1-FE-UPLOAD_MAX_BYTES-higher.json src/features/infraction-management/__tests__/uploadContract.test.tsx`
- **Step-0 baseline** reused run **B-18** — `13 tests: 13 passed, 0 failed (files 1)`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- frontend/src/api/uploads.ts` was empty at snapshot; (b) every `cmp` since B-18 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i39`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `13 tests: 12 passed, 1 failed (files 1)`; exit 1
- **Reddened vs that baseline** (1) — `the five server facts, pinned from this side declares media_service.MAX_FILE_SIZE`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `6c970828520bb87dd1c9f63f51438f394acd0003feba1aabc2d61622c200abb8`; restored file `shasum -a 256` = `6c970828520bb87dd1c9f63f51438f394acd0003feba1aabc2d61622c200abb8`; `cmp <scratchpad>/snap/S1-FE-UPLOAD_MAX_BYTES-higher.uploads.ts frontend/src/api/uploads.ts` → clean (no output).

#### `S1-FE-GCR_documentOccurrence-lower`

- **File:line** `frontend/src/features/__tests__/documentOccurrenceContrast.test.ts:31`
- **Mutation** — S1 frontend / GCR_documentOccurrence / lower
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '31p' <scratchpad>/snap/S1-FE-GCR_documentOccurrence-lower.documentOccurrenceContrast.test.ts
  const GRAPHICAL_CONTRAST_RATIO = 3;
  $ sed -n '31p' frontend/src/features/__tests__/documentOccurrenceContrast.test.ts
  const GRAPHICAL_CONTRAST_RATIO = 1;
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S1-FE-GCR_documentOccurrence-lower.json src/features/__tests__/documentOccurrenceContrast.test.ts`
- **Step-0 baseline** run **B-19** (own run, same command on the unmutated file) — `53 tests: 53 passed, 0 failed (files 1)`; exit 0; `uv pip freeze` captured as `freeze.B-19`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `53 tests: 53 passed, 0 failed (files 1)`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `src/features/__tests__/documentOccurrenceContrast.test.ts > the tokens this task paints with clears the 3:1 graphical floor`
- **Was it among the reddened?** no — correct for a weakening move
- **Step-5 restore** pristine copy `shasum -a 256` = `dbb971673f7d0fbde09dbb41c35c0fd5a3eb095bb41a04fae1b002cfda04216a`; restored file `shasum -a 256` = `dbb971673f7d0fbde09dbb41c35c0fd5a3eb095bb41a04fae1b002cfda04216a`; `cmp <scratchpad>/snap/S1-FE-GCR_documentOccurrence-lower.documentOccurrenceContrast.test.ts frontend/src/features/__tests__/documentOccurrenceContrast.test.ts` → clean (no output).

#### `S1-FE-GCR_documentOccurrence-higher`

- **File:line** `frontend/src/features/__tests__/documentOccurrenceContrast.test.ts:31`
- **Mutation** — S1 frontend / GCR_documentOccurrence / higher
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '31p' <scratchpad>/snap/S1-FE-GCR_documentOccurrence-higher.documentOccurrenceContrast.test.ts
  const GRAPHICAL_CONTRAST_RATIO = 3;
  $ sed -n '31p' frontend/src/features/__tests__/documentOccurrenceContrast.test.ts
  const GRAPHICAL_CONTRAST_RATIO = 21;
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S1-FE-GCR_documentOccurrence-higher.json src/features/__tests__/documentOccurrenceContrast.test.ts`
- **Step-0 baseline** reused run **B-19** — `53 tests: 53 passed, 0 failed (files 1)`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- frontend/src/features/__tests__/documentOccurrenceContrast.test.ts` was empty at snapshot; (b) every `cmp` since B-19 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i40`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `53 tests: 42 passed, 11 failed (files 1)`; exit 1
- **Reddened vs that baseline** (10) — `declared sub-AA, none of it introduced by this task 'NewOccurrenceModal.tsx:158 kept text-…' measures as declared`, `declared sub-AA, none of it introduced by this task 'graphical --primary on --accent/--mut…' measures as declared`, `declared sub-AA, none of it introduced by this task 'kept text-emerald-600 on bg-emerald-50' measures as declared`, `the graphical pairs APRAS-82 changes brand icons, indigo-500 on a card clears the 3:1 floor before and after`, `the graphical pairs APRAS-82 changes brand icons, indigo-600 on a card clears the 3:1 floor before and after`, `the graphical pairs APRAS-82 changes inline glyphs on a neutral fill clears the 3:1 floor before and after`, `the graphical pairs APRAS-82 changes tile glyphs on a brand tint clears the 3:1 floor before and after`, `the tokens this task paints with clears the 3:1 graphical floor: --primary on --accent`, `the tokens this task paints with clears the 3:1 graphical floor: --primary on --card`, `the tokens this task paints with clears the 3:1 graphical floor: --primary on --muted`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `dbb971673f7d0fbde09dbb41c35c0fd5a3eb095bb41a04fae1b002cfda04216a`; restored file `shasum -a 256` = `dbb971673f7d0fbde09dbb41c35c0fd5a3eb095bb41a04fae1b002cfda04216a`; `cmp <scratchpad>/snap/S1-FE-GCR_documentOccurrence-higher.documentOccurrenceContrast.test.ts frontend/src/features/__tests__/documentOccurrenceContrast.test.ts` → clean (no output).

#### `S1-FE-GCR_financePurchasesAccess-lower`

- **File:line** `frontend/src/features/__tests__/financePurchasesAccessContrast.test.ts:33`
- **Mutation** — S1 frontend / GCR_financePurchasesAccess / lower
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '33p' <scratchpad>/snap/S1-FE-GCR_financePurchasesAccess-lower.financePurchasesAccessContrast.test.ts
  const GRAPHICAL_CONTRAST_RATIO = 3;
  $ sed -n '33p' frontend/src/features/__tests__/financePurchasesAccessContrast.test.ts
  const GRAPHICAL_CONTRAST_RATIO = 1;
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S1-FE-GCR_financePurchasesAccess-lower.json src/features/__tests__/financePurchasesAccessContrast.test.ts`
- **Step-0 baseline** run **B-20** (own run, same command on the unmutated file) — `59 tests: 59 passed, 0 failed (files 1)`; exit 0; `uv pip freeze` captured as `freeze.B-20`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `59 tests: 58 passed, 1 failed (files 1)`; exit 1
- **Reddened vs that baseline** (1) — `declared sub-AA or unmeasurable, none of it introduced by this task names every pair it leaves below AA and no more`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `c64f8091d18659054179c01a20286bbf2600cd3ed251e443b87163cf1eeb29c2`; restored file `shasum -a 256` = `c64f8091d18659054179c01a20286bbf2600cd3ed251e443b87163cf1eeb29c2`; `cmp <scratchpad>/snap/S1-FE-GCR_financePurchasesAccess-lower.financePurchasesAccessContrast.test.ts frontend/src/features/__tests__/financePurchasesAccessContrast.test.ts` → clean (no output).

#### `S1-FE-GCR_financePurchasesAccess-higher`

- **File:line** `frontend/src/features/__tests__/financePurchasesAccessContrast.test.ts:33`
- **Mutation** — S1 frontend / GCR_financePurchasesAccess / higher
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '33p' <scratchpad>/snap/S1-FE-GCR_financePurchasesAccess-higher.financePurchasesAccessContrast.test.ts
  const GRAPHICAL_CONTRAST_RATIO = 3;
  $ sed -n '33p' frontend/src/features/__tests__/financePurchasesAccessContrast.test.ts
  const GRAPHICAL_CONTRAST_RATIO = 21;
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S1-FE-GCR_financePurchasesAccess-higher.json src/features/__tests__/financePurchasesAccessContrast.test.ts`
- **Step-0 baseline** reused run **B-20** — `59 tests: 59 passed, 0 failed (files 1)`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- frontend/src/features/__tests__/financePurchasesAccessContrast.test.ts` was empty at snapshot; (b) every `cmp` since B-20 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i41`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `59 tests: 41 passed, 18 failed (files 1)`; exit 1
- **Reddened vs that baseline** (18) — `declared sub-AA or unmeasurable, none of it introduced by this task 'graphical --primary on --accent/--mut…' measures as declared`, `declared sub-AA or unmeasurable, none of it introduced by this task 'graphical --primary on --background, …' measures as declared`, `declared sub-AA or unmeasurable, none of it introduced by this task 'kept text-amber-600 on bg-amber-50' measures as declared`, `declared sub-AA or unmeasurable, none of it introduced by this task 'kept text-emerald-600 on bg-emerald-50' measures as declared`, `declared sub-AA or unmeasurable, none of it introduced by this task 'kept text-red-500 on white' measures as declared`, `declared sub-AA or unmeasurable, none of it introduced by this task 'kept text-red-600 on bg-red-50' measures as declared`, `the graphical pairs APRAS-83 changes brand icons on a card clears the 3:1 floor before and after`, `the graphical pairs APRAS-83 changes measures the Award glyph on the lowest-price column too`, `the graphical pairs APRAS-83 changes page-header brand icons clears the 3:1 floor before and after`, `the graphical pairs APRAS-83 changes the Award control glyph clears the 3:1 floor before and after`, `the graphical pairs APRAS-83 changes the FileText glyph on a card clears the 3:1 floor before and after`, `the graphical pairs APRAS-83 changes the inline glyph on a neutral cell clears the 3:1 floor before and after`, `the graphical pairs APRAS-83 changes the six delete glyphs clears the 3:1 floor before and after`, `the graphical pairs APRAS-83 changes the tile glyph on a brand tint clears the 3:1 floor before and after`, `the tokens this task paints with clears the 3:1 graphical floor: --primary on --accent`, `the tokens this task paints with clears the 3:1 graphical floor: --primary on --background`, `the tokens this task paints with clears the 3:1 graphical floor: --primary on --card`, `the tokens this task paints with clears the 3:1 graphical floor: --primary on --muted`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `c64f8091d18659054179c01a20286bbf2600cd3ed251e443b87163cf1eeb29c2`; restored file `shasum -a 256` = `c64f8091d18659054179c01a20286bbf2600cd3ed251e443b87163cf1eeb29c2`; `cmp <scratchpad>/snap/S1-FE-GCR_financePurchasesAccess-higher.financePurchasesAccessContrast.test.ts frontend/src/features/__tests__/financePurchasesAccessContrast.test.ts` → clean (no output).

#### `S1-FE-GCR_mediaFeedback-lower`

- **File:line** `frontend/src/features/__tests__/mediaFeedbackAnnouncementsPackagesContrast.test.ts:44`
- **Mutation** — S1 frontend / GCR_mediaFeedback / lower
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '44p' <scratchpad>/snap/S1-FE-GCR_mediaFeedback-lower.mediaFeedbackAnnouncementsPackagesContrast.test.ts
  const GRAPHICAL_CONTRAST_RATIO = 3;
  $ sed -n '44p' frontend/src/features/__tests__/mediaFeedbackAnnouncementsPackagesContrast.test.ts
  const GRAPHICAL_CONTRAST_RATIO = 1;
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S1-FE-GCR_mediaFeedback-lower.json src/features/__tests__/mediaFeedbackAnnouncementsPackagesContrast.test.ts`
- **Step-0 baseline** run **B-21** (own run, same command on the unmutated file) — `73 tests: 73 passed, 0 failed (files 1)`; exit 0; `uv pip freeze` captured as `freeze.B-21`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `73 tests: 69 passed, 4 failed (files 1)`; exit 1
- **Reddened vs that baseline** (4) — `declared sub-AA or unmeasurable, and which are this task's names every pair it leaves below AA and no more`, `§7 — the zoom slider, the one design change this child carries clears the track's 3:1 floor in five themes and fails it in the pale one`, `§7 — the zoom slider, the one design change this child carries measures what the rejected candidates would have given the thumb`, `§7 — the zoom slider, the one design change this child carries repairs the track, which failed 1.4.11 before`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `91eed3d929375eb78c5607325541d20f2a12562e20fae6ddc8763ee25c45b91c`; restored file `shasum -a 256` = `91eed3d929375eb78c5607325541d20f2a12562e20fae6ddc8763ee25c45b91c`; `cmp <scratchpad>/snap/S1-FE-GCR_mediaFeedback-lower.mediaFeedbackAnnouncementsPackagesContrast.test.ts frontend/src/features/__tests__/mediaFeedbackAnnouncementsPackagesContrast.test.ts` → clean (no output).

#### `S1-FE-GCR_mediaFeedback-higher`

- **File:line** `frontend/src/features/__tests__/mediaFeedbackAnnouncementsPackagesContrast.test.ts:44`
- **Mutation** — S1 frontend / GCR_mediaFeedback / higher
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '44p' <scratchpad>/snap/S1-FE-GCR_mediaFeedback-higher.mediaFeedbackAnnouncementsPackagesContrast.test.ts
  const GRAPHICAL_CONTRAST_RATIO = 3;
  $ sed -n '44p' frontend/src/features/__tests__/mediaFeedbackAnnouncementsPackagesContrast.test.ts
  const GRAPHICAL_CONTRAST_RATIO = 21;
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S1-FE-GCR_mediaFeedback-higher.json src/features/__tests__/mediaFeedbackAnnouncementsPackagesContrast.test.ts`
- **Step-0 baseline** reused run **B-21** — `73 tests: 73 passed, 0 failed (files 1)`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- frontend/src/features/__tests__/mediaFeedbackAnnouncementsPackagesContrast.test.ts` was empty at snapshot; (b) every `cmp` since B-21 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i42`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `73 tests: 52 passed, 21 failed (files 1)`; exit 1
- **Reddened vs that baseline** (21) — `declared sub-AA or unmeasurable, and which are this task's 'CommentThread.tsx\'s delete glyph, --…' measures as declared`, `declared sub-AA or unmeasurable, and which are this task's 'graphical --primary on --accent/--mut…' measures as declared`, `declared sub-AA or unmeasurable, and which are this task's 'graphical --primary on --card, 3 sites' measures as declared`, `declared sub-AA or unmeasurable, and which are this task's 'kept text-emerald-600 on --card' measures as declared`, `declared sub-AA or unmeasurable, and which are this task's 'kept text-emerald-600 on bg-emerald-50' measures as declared`, `declared sub-AA or unmeasurable, and which are this task's 'kept text-white on bg-rose-500' measures as declared`, `the graphical pairs APRAS-84 changes brand icons on a card clears the 3:1 floor before and after`, `the graphical pairs APRAS-84 changes measures the carousel's active dot against its own container`, `the graphical pairs APRAS-84 changes the Eye glyph on a card clears the 3:1 floor before and after`, `the graphical pairs APRAS-84 changes the PDF glyph clears the 3:1 floor before and after`, `the graphical pairs APRAS-84 changes the delete glyph on a card clears the 3:1 floor before and after`, `the graphical pairs APRAS-84 changes the inline glyph on a neutral fill clears the 3:1 floor before and after`, `the graphical pairs APRAS-84 changes the tile glyphs on a brand tint clears the 3:1 floor before and after`, `the tokens this task paints with clears the 3:1 graphical floor: --primary on --accent`, `the tokens this task paints with clears the 3:1 graphical floor: --primary on --card`, `the tokens this task paints with clears the 3:1 graphical floor: --primary on --muted`, `§7 — the zoom slider, the one design change this child carries clears the track's 3:1 floor in five themes and fails it in the pale one`, `§7 — the zoom slider, the one design change this child carries holds the thumb above AA in all six themes, which is more than it needs`, `§7 — the zoom slider, the one design change this child carries improves the thumb, measured against its own track`, `§7 — the zoom slider, the one design change this child carries measures what the rejected candidates would have given the thumb`, `§7 — the zoom slider, the one design change this child carries repairs the track, which failed 1.4.11 before`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `91eed3d929375eb78c5607325541d20f2a12562e20fae6ddc8763ee25c45b91c`; restored file `shasum -a 256` = `91eed3d929375eb78c5607325541d20f2a12562e20fae6ddc8763ee25c45b91c`; `cmp <scratchpad>/snap/S1-FE-GCR_mediaFeedback-higher.mediaFeedbackAnnouncementsPackagesContrast.test.ts frontend/src/features/__tests__/mediaFeedbackAnnouncementsPackagesContrast.test.ts` → clean (no output).

#### `S1-FE-GCR_projectAsset-lower`

- **File:line** `frontend/src/features/__tests__/projectAssetContrast.test.ts:31`
- **Mutation** — S1 frontend / GCR_projectAsset / lower
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '31p' <scratchpad>/snap/S1-FE-GCR_projectAsset-lower.projectAssetContrast.test.ts
  const GRAPHICAL_CONTRAST_RATIO = 3;
  $ sed -n '31p' frontend/src/features/__tests__/projectAssetContrast.test.ts
  const GRAPHICAL_CONTRAST_RATIO = 1;
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S1-FE-GCR_projectAsset-lower.json src/features/__tests__/projectAssetContrast.test.ts`
- **Step-0 baseline** run **B-22** (own run, same command on the unmutated file) — `49 tests: 49 passed, 0 failed (files 1)`; exit 0; `uv pip freeze` captured as `freeze.B-22`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `49 tests: 49 passed, 0 failed (files 1)`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `src/features/__tests__/projectAssetContrast.test.ts > the tokens this task paints with clears the 3:1 graphical floor`
- **Was it among the reddened?** no — correct for a weakening move
- **Step-5 restore** pristine copy `shasum -a 256` = `cd3876b3b489d898e63ca257e2c3d46035d8222579145e3b8d6b6983dbc08e4b`; restored file `shasum -a 256` = `cd3876b3b489d898e63ca257e2c3d46035d8222579145e3b8d6b6983dbc08e4b`; `cmp <scratchpad>/snap/S1-FE-GCR_projectAsset-lower.projectAssetContrast.test.ts frontend/src/features/__tests__/projectAssetContrast.test.ts` → clean (no output).

#### `S1-FE-GCR_projectAsset-higher`

- **File:line** `frontend/src/features/__tests__/projectAssetContrast.test.ts:31`
- **Mutation** — S1 frontend / GCR_projectAsset / higher
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '31p' <scratchpad>/snap/S1-FE-GCR_projectAsset-higher.projectAssetContrast.test.ts
  const GRAPHICAL_CONTRAST_RATIO = 3;
  $ sed -n '31p' frontend/src/features/__tests__/projectAssetContrast.test.ts
  const GRAPHICAL_CONTRAST_RATIO = 21;
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S1-FE-GCR_projectAsset-higher.json src/features/__tests__/projectAssetContrast.test.ts`
- **Step-0 baseline** reused run **B-22** — `49 tests: 49 passed, 0 failed (files 1)`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- frontend/src/features/__tests__/projectAssetContrast.test.ts` was empty at snapshot; (b) every `cmp` since B-22 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i43`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `49 tests: 37 passed, 12 failed (files 1)`; exit 1
- **Reddened vs that baseline** (12) — `declared sub-AA or unmeasurable, none of it introduced by this task 'AssetSummaryCards.tsx:88 kept text-em…' measures as declared`, `declared sub-AA or unmeasurable, none of it introduced by this task 'ProjectUpdateFeed.tsx:92 --destructiv…' measures as declared`, `declared sub-AA or unmeasurable, none of it introduced by this task 'graphical --primary on --accent/--mut…' measures as declared`, `the graphical pairs APRAS-81 changes brand icons on a card clears the 3:1 floor before and after`, `the graphical pairs APRAS-81 changes delete icon on a card clears the 3:1 floor before and after`, `the graphical pairs APRAS-81 changes progress fill on a neutral track clears the 3:1 floor before and after`, `the graphical pairs APRAS-81 changes spinners on the page root clears the 3:1 floor before and after`, `the graphical pairs APRAS-81 changes tile glyph on a brand tint clears the 3:1 floor before and after`, `the tokens this task paints with clears the 3:1 graphical floor: --primary on --accent`, `the tokens this task paints with clears the 3:1 graphical floor: --primary on --background`, `the tokens this task paints with clears the 3:1 graphical floor: --primary on --card`, `the tokens this task paints with clears the 3:1 graphical floor: --primary on --muted`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `cd3876b3b489d898e63ca257e2c3d46035d8222579145e3b8d6b6983dbc08e4b`; restored file `shasum -a 256` = `cd3876b3b489d898e63ca257e2c3d46035d8222579145e3b8d6b6983dbc08e4b`; `cmp <scratchpad>/snap/S1-FE-GCR_projectAsset-higher.projectAssetContrast.test.ts frontend/src/features/__tests__/projectAssetContrast.test.ts` → clean (no output).

#### `S1-FE-GCR_visitorManagement-lower`

- **File:line** `frontend/src/features/visitor-management/__tests__/visitorManagementContrast.test.ts:33`
- **Mutation** — S1 frontend / GCR_visitorManagement / lower
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '33p' <scratchpad>/snap/S1-FE-GCR_visitorManagement-lower.visitorManagementContrast.test.ts
  const GRAPHICAL_CONTRAST_RATIO = 3;
  $ sed -n '33p' frontend/src/features/visitor-management/__tests__/visitorManagementContrast.test.ts
  const GRAPHICAL_CONTRAST_RATIO = 1;
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S1-FE-GCR_visitorManagement-lower.json src/features/visitor-management/__tests__/visitorManagementContrast.test.ts`
- **Step-0 baseline** run **B-23** (own run, same command on the unmutated file) — `44 tests: 44 passed, 0 failed (files 1)`; exit 0; `uv pip freeze` captured as `freeze.B-23`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `44 tests: 44 passed, 0 failed (files 1)`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `src/features/visitor-management/__tests__/visitorManagementContrast.test.ts > the pairs APRAS-80 moves`
- **Was it among the reddened?** no — correct for a weakening move
- **Step-5 restore** pristine copy `shasum -a 256` = `9fbad9a7d7b54ee0bd960437ea955351ffdd49f56fbfa584fec13b802bc2589c`; restored file `shasum -a 256` = `9fbad9a7d7b54ee0bd960437ea955351ffdd49f56fbfa584fec13b802bc2589c`; `cmp <scratchpad>/snap/S1-FE-GCR_visitorManagement-lower.visitorManagementContrast.test.ts frontend/src/features/visitor-management/__tests__/visitorManagementContrast.test.ts` → clean (no output).

#### `S1-FE-GCR_visitorManagement-higher`

- **File:line** `frontend/src/features/visitor-management/__tests__/visitorManagementContrast.test.ts:33`
- **Mutation** — S1 frontend / GCR_visitorManagement / higher
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '33p' <scratchpad>/snap/S1-FE-GCR_visitorManagement-higher.visitorManagementContrast.test.ts
  const GRAPHICAL_CONTRAST_RATIO = 3;
  $ sed -n '33p' frontend/src/features/visitor-management/__tests__/visitorManagementContrast.test.ts
  const GRAPHICAL_CONTRAST_RATIO = 21;
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S1-FE-GCR_visitorManagement-higher.json src/features/visitor-management/__tests__/visitorManagementContrast.test.ts`
- **Step-0 baseline** reused run **B-23** — `44 tests: 44 passed, 0 failed (files 1)`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- frontend/src/features/visitor-management/__tests__/visitorManagementContrast.test.ts` was empty at snapshot; (b) every `cmp` since B-23 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i44`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `44 tests: 39 passed, 5 failed (files 1)`; exit 1
- **Reddened vs that baseline** (5) — `the pairs APRAS-80 moves AuthorizationFormModal:117, AuthorizationQrModal:61, QrScannerModal:61, GatekeeperDashboard:170,240,266,305 icons (§1k) — text-indigo-600 -> text-primary on --card clears its floor after the migration`, `the pairs APRAS-80 moves GatekeeperDashboard:129, VisitorAuthPage:58 page-shell icons (§1k) — text-indigo-600 -> text-primary on --background clears its floor after the migration`, `the pairs APRAS-80 moves GatekeeperDashboard:145 Users glyph in the counter card (§1k) — text-indigo-600 on bg-indigo-50 -> text-primary on bg-accent clears its floor after the migration`, `the pairs APRAS-80 moves leaves nothing it moves undeclared`, `the pairs APRAS-80 moves routes brand text to --primary-text and brand glyphs to --primary`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `9fbad9a7d7b54ee0bd960437ea955351ffdd49f56fbfa584fec13b802bc2589c`; restored file `shasum -a 256` = `9fbad9a7d7b54ee0bd960437ea955351ffdd49f56fbfa584fec13b802bc2589c`; `cmp <scratchpad>/snap/S1-FE-GCR_visitorManagement-higher.visitorManagementContrast.test.ts frontend/src/features/visitor-management/__tests__/visitorManagementContrast.test.ts` → clean (no output).

#### `S1-FE-DOCUMENTED_ROUTE_CEILING-lower`

- **File:line** `frontend/src/features/infraction-management/__tests__/lotSelectContract.test.tsx:57`
- **Mutation** — S1 frontend / DOCUMENTED_ROUTE_CEILING / lower
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '57p' <scratchpad>/snap/S1-FE-DOCUMENTED_ROUTE_CEILING-lower.lotSelectContract.test.tsx
  const DOCUMENTED_ROUTE_CEILING = 100;
  $ sed -n '57p' frontend/src/features/infraction-management/__tests__/lotSelectContract.test.tsx
  const DOCUMENTED_ROUTE_CEILING = 99;
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S1-FE-DOCUMENTED_ROUTE_CEILING-lower.json src/features/infraction-management/__tests__/lotSelectContract.test.tsx`
- **Step-0 baseline** run **B-24** (own run, same command on the unmutated file) — `6 tests: 6 passed, 0 failed (files 1)`; exit 0; `uv pip freeze` captured as `freeze.B-24`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `6 tests: 5 passed, 1 failed (files 1)`; exit 1
- **Reddened vs that baseline** (1) — `the lot select's contract with GET /api/v1/lots/ requests a limit the route's documented Query bound accepts`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `2ee53ea3a3375ffa3ab5d3d3e485206e8c46ec99689a9d0e56e2ad699ba3ca12`; restored file `shasum -a 256` = `2ee53ea3a3375ffa3ab5d3d3e485206e8c46ec99689a9d0e56e2ad699ba3ca12`; `cmp <scratchpad>/snap/S1-FE-DOCUMENTED_ROUTE_CEILING-lower.lotSelectContract.test.tsx frontend/src/features/infraction-management/__tests__/lotSelectContract.test.tsx` → clean (no output).

#### `S1-FE-DOCUMENTED_ROUTE_CEILING-higher`

- **File:line** `frontend/src/features/infraction-management/__tests__/lotSelectContract.test.tsx:57`
- **Mutation** — S1 frontend / DOCUMENTED_ROUTE_CEILING / higher
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '57p' <scratchpad>/snap/S1-FE-DOCUMENTED_ROUTE_CEILING-higher.lotSelectContract.test.tsx
  const DOCUMENTED_ROUTE_CEILING = 100;
  $ sed -n '57p' frontend/src/features/infraction-management/__tests__/lotSelectContract.test.tsx
  const DOCUMENTED_ROUTE_CEILING = 101;
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S1-FE-DOCUMENTED_ROUTE_CEILING-higher.json src/features/infraction-management/__tests__/lotSelectContract.test.tsx`
- **Step-0 baseline** reused run **B-24** — `6 tests: 6 passed, 0 failed (files 1)`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- frontend/src/features/infraction-management/__tests__/lotSelectContract.test.tsx` was empty at snapshot; (b) every `cmp` since B-24 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i45`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `6 tests: 6 passed, 0 failed (files 1)`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `src/features/infraction-management/__tests__/lotSelectContract.test.tsx > requests a limit the route's documented Query bound accepts`
- **Was it among the reddened?** no — correct: raising the *documented* ceiling above the requested limit keeps the inequality true
- **Step-5 restore** pristine copy `shasum -a 256` = `2ee53ea3a3375ffa3ab5d3d3e485206e8c46ec99689a9d0e56e2ad699ba3ca12`; restored file `shasum -a 256` = `2ee53ea3a3375ffa3ab5d3d3e485206e8c46ec99689a9d0e56e2ad699ba3ca12`; `cmp <scratchpad>/snap/S1-FE-DOCUMENTED_ROUTE_CEILING-higher.lotSelectContract.test.tsx frontend/src/features/infraction-management/__tests__/lotSelectContract.test.tsx` → clean (no output).

#### `S1-FE-DOCUMENTED_MAX_FILE_SIZE_BYTES-lower`

- **File:line** `frontend/src/features/infraction-management/__tests__/uploadContract.test.tsx:60`
- **Mutation** — S1 frontend / DOCUMENTED_MAX_FILE_SIZE_BYTES / lower
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '60p' <scratchpad>/snap/S1-FE-DOCUMENTED_MAX_FILE_SIZE_BYTES-lower.uploadContract.test.tsx
  const DOCUMENTED_MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024;
  $ sed -n '60p' frontend/src/features/infraction-management/__tests__/uploadContract.test.tsx
  const DOCUMENTED_MAX_FILE_SIZE_BYTES = 4 * 1024 * 1024;
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S1-FE-DOCUMENTED_MAX_FILE_SIZE_BYTES-lower.json src/features/infraction-management/__tests__/uploadContract.test.tsx`
- **Step-0 baseline** reused run **B-18** — `13 tests: 13 passed, 0 failed (files 1)`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- frontend/src/features/infraction-management/__tests__/uploadContract.test.tsx` was empty at snapshot; (b) every `cmp` since B-18 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i46`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `13 tests: 12 passed, 1 failed (files 1)`; exit 1
- **Reddened vs that baseline** (1) — `the five server facts, pinned from this side declares media_service.MAX_FILE_SIZE`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `b630d7449529b2c21c43ace9523647d190afde9e54d7ec92aa0f0ddba82a1f85`; restored file `shasum -a 256` = `b630d7449529b2c21c43ace9523647d190afde9e54d7ec92aa0f0ddba82a1f85`; `cmp <scratchpad>/snap/S1-FE-DOCUMENTED_MAX_FILE_SIZE_BYTES-lower.uploadContract.test.tsx frontend/src/features/infraction-management/__tests__/uploadContract.test.tsx` → clean (no output).

#### `S1-FE-DOCUMENTED_MAX_FILE_SIZE_BYTES-higher`

- **File:line** `frontend/src/features/infraction-management/__tests__/uploadContract.test.tsx:60`
- **Mutation** — S1 frontend / DOCUMENTED_MAX_FILE_SIZE_BYTES / higher
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '60p' <scratchpad>/snap/S1-FE-DOCUMENTED_MAX_FILE_SIZE_BYTES-higher.uploadContract.test.tsx
  const DOCUMENTED_MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024;
  $ sed -n '60p' frontend/src/features/infraction-management/__tests__/uploadContract.test.tsx
  const DOCUMENTED_MAX_FILE_SIZE_BYTES = 6 * 1024 * 1024;
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S1-FE-DOCUMENTED_MAX_FILE_SIZE_BYTES-higher.json src/features/infraction-management/__tests__/uploadContract.test.tsx`
- **Step-0 baseline** reused run **B-18** — `13 tests: 13 passed, 0 failed (files 1)`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- frontend/src/features/infraction-management/__tests__/uploadContract.test.tsx` was empty at snapshot; (b) every `cmp` since B-18 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i47`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `13 tests: 12 passed, 1 failed (files 1)`; exit 1
- **Reddened vs that baseline** (1) — `the five server facts, pinned from this side declares media_service.MAX_FILE_SIZE`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `b630d7449529b2c21c43ace9523647d190afde9e54d7ec92aa0f0ddba82a1f85`; restored file `shasum -a 256` = `b630d7449529b2c21c43ace9523647d190afde9e54d7ec92aa0f0ddba82a1f85`; `cmp <scratchpad>/snap/S1-FE-DOCUMENTED_MAX_FILE_SIZE_BYTES-higher.uploadContract.test.tsx frontend/src/features/infraction-management/__tests__/uploadContract.test.tsx` → clean (no output).

#### `S1-FE-LOT_SELECT_LIMIT-lower`

- **File:line** `frontend/src/features/infraction-management/components/NewInfractionModal.tsx:25`
- **Mutation** — S1 frontend / LOT_SELECT_LIMIT / lower
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '25p' <scratchpad>/snap/S1-FE-LOT_SELECT_LIMIT-lower.NewInfractionModal.tsx
  export const LOT_SELECT_LIMIT = 100;
  $ sed -n '25p' frontend/src/features/infraction-management/components/NewInfractionModal.tsx
  export const LOT_SELECT_LIMIT = 99;
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S1-FE-LOT_SELECT_LIMIT-lower.json src/features/infraction-management/__tests__/lotSelectContract.test.tsx`
- **Step-0 baseline** reused run **B-24** — `6 tests: 6 passed, 0 failed (files 1)`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- frontend/src/features/infraction-management/components/NewInfractionModal.tsx` was empty at snapshot; (b) every `cmp` since B-24 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i48`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `6 tests: 6 passed, 0 failed (files 1)`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `src/features/infraction-management/__tests__/lotSelectContract.test.tsx > requests a limit the route's documented Query bound accepts`
- **Was it among the reddened?** no — correct: 99 <= 100 still holds
- **Step-5 restore** pristine copy `shasum -a 256` = `e933171514f1dfe144f6124883365327fd9c84efc34c3b0deafda3064aa3f07b`; restored file `shasum -a 256` = `e933171514f1dfe144f6124883365327fd9c84efc34c3b0deafda3064aa3f07b`; `cmp <scratchpad>/snap/S1-FE-LOT_SELECT_LIMIT-lower.NewInfractionModal.tsx frontend/src/features/infraction-management/components/NewInfractionModal.tsx` → clean (no output).

#### `S1-FE-LOT_SELECT_LIMIT-higher`

- **File:line** `frontend/src/features/infraction-management/components/NewInfractionModal.tsx:25`
- **Mutation** — S1 frontend / LOT_SELECT_LIMIT / higher
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '25p' <scratchpad>/snap/S1-FE-LOT_SELECT_LIMIT-higher.NewInfractionModal.tsx
  export const LOT_SELECT_LIMIT = 100;
  $ sed -n '25p' frontend/src/features/infraction-management/components/NewInfractionModal.tsx
  export const LOT_SELECT_LIMIT = 101;
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S1-FE-LOT_SELECT_LIMIT-higher.json src/features/infraction-management/__tests__/lotSelectContract.test.tsx`
- **Step-0 baseline** reused run **B-24** — `6 tests: 6 passed, 0 failed (files 1)`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- frontend/src/features/infraction-management/components/NewInfractionModal.tsx` was empty at snapshot; (b) every `cmp` since B-24 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i49`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `6 tests: 5 passed, 1 failed (files 1)`; exit 1
- **Reddened vs that baseline** (1) — `the lot select's contract with GET /api/v1/lots/ requests a limit the route's documented Query bound accepts`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `e933171514f1dfe144f6124883365327fd9c84efc34c3b0deafda3064aa3f07b`; restored file `shasum -a 256` = `e933171514f1dfe144f6124883365327fd9c84efc34c3b0deafda3064aa3f07b`; `cmp <scratchpad>/snap/S1-FE-LOT_SELECT_LIMIT-higher.NewInfractionModal.tsx frontend/src/features/infraction-management/components/NewInfractionModal.tsx` → clean (no output).

#### `S1-FE-MAX_REQUEST_ITEMS-lower`

- **File:line** `frontend/src/features/purchase-management/components/PurchaseRequestFormModal.tsx:15`
- **Mutation** — S1 frontend / MAX_REQUEST_ITEMS / lower
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '15p' <scratchpad>/snap/S1-FE-MAX_REQUEST_ITEMS-lower.PurchaseRequestFormModal.tsx
  export const MAX_REQUEST_ITEMS = 50;
  $ sed -n '15p' frontend/src/features/purchase-management/components/PurchaseRequestFormModal.tsx
  export const MAX_REQUEST_ITEMS = 49;
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S1-FE-MAX_REQUEST_ITEMS-lower.json src/features/purchase-management/__tests__/PurchaseRequestFormModal.test.tsx`
- **Step-0 baseline** run **B-25** (own run, same command on the unmutated file) — `13 tests: 13 passed, 0 failed (files 1)`; exit 0; `uv pip freeze` captured as `freeze.B-25`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `13 tests: 13 passed, 0 failed (files 1)`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `no case names it — see Findings F-03`
- **Was it among the reddened?** no
- **Step-5 restore** pristine copy `shasum -a 256` = `9ec698ce17ceccbc9c636f9468d36a5fa2796349b934a434c1e4be94aabae1b7`; restored file `shasum -a 256` = `9ec698ce17ceccbc9c636f9468d36a5fa2796349b934a434c1e4be94aabae1b7`; `cmp <scratchpad>/snap/S1-FE-MAX_REQUEST_ITEMS-lower.PurchaseRequestFormModal.tsx frontend/src/features/purchase-management/components/PurchaseRequestFormModal.tsx` → clean (no output).

#### `S1-FE-MAX_REQUEST_ITEMS-higher`

- **File:line** `frontend/src/features/purchase-management/components/PurchaseRequestFormModal.tsx:15`
- **Mutation** — S1 frontend / MAX_REQUEST_ITEMS / higher
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '15p' <scratchpad>/snap/S1-FE-MAX_REQUEST_ITEMS-higher.PurchaseRequestFormModal.tsx
  export const MAX_REQUEST_ITEMS = 50;
  $ sed -n '15p' frontend/src/features/purchase-management/components/PurchaseRequestFormModal.tsx
  export const MAX_REQUEST_ITEMS = 51;
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S1-FE-MAX_REQUEST_ITEMS-higher.json src/features/purchase-management/__tests__/PurchaseRequestFormModal.test.tsx`
- **Step-0 baseline** reused run **B-25** — `13 tests: 13 passed, 0 failed (files 1)`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- frontend/src/features/purchase-management/components/PurchaseRequestFormModal.tsx` was empty at snapshot; (b) every `cmp` since B-25 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i50`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `13 tests: 13 passed, 0 failed (files 1)`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `no case names it — see Findings F-03`
- **Was it among the reddened?** no
- **Step-5 restore** pristine copy `shasum -a 256` = `9ec698ce17ceccbc9c636f9468d36a5fa2796349b934a434c1e4be94aabae1b7`; restored file `shasum -a 256` = `9ec698ce17ceccbc9c636f9468d36a5fa2796349b934a434c1e4be94aabae1b7`; `cmp <scratchpad>/snap/S1-FE-MAX_REQUEST_ITEMS-higher.PurchaseRequestFormModal.tsx frontend/src/features/purchase-management/components/PurchaseRequestFormModal.tsx` → clean (no output).

#### `S1-FE-MAX_EXTRA_FIELDS-lower`

- **File:line** `frontend/src/features/purchase-management/components/QuoteFormModal.tsx:18`
- **Mutation** — S1 frontend / MAX_EXTRA_FIELDS / lower
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '18p' <scratchpad>/snap/S1-FE-MAX_EXTRA_FIELDS-lower.QuoteFormModal.tsx
  export const MAX_EXTRA_FIELDS = 20;
  $ sed -n '18p' frontend/src/features/purchase-management/components/QuoteFormModal.tsx
  export const MAX_EXTRA_FIELDS = 19;
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S1-FE-MAX_EXTRA_FIELDS-lower.json src/features/purchase-management/__tests__/QuoteFormModal.test.tsx`
- **Step-0 baseline** run **B-26** (own run, same command on the unmutated file) — `22 tests: 22 passed, 0 failed (files 1)`; exit 0; `uv pip freeze` captured as `freeze.B-26`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `22 tests: 21 passed, 1 failed (files 1)`; exit 1
- **Reddened vs that baseline** (1) — `QuoteFormModal stops adding extra fields at twenty rows`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `765b01d809887f76059a7004a39e5e74a2c7f992d0201f03f24e71214b32e453`; restored file `shasum -a 256` = `765b01d809887f76059a7004a39e5e74a2c7f992d0201f03f24e71214b32e453`; `cmp <scratchpad>/snap/S1-FE-MAX_EXTRA_FIELDS-lower.QuoteFormModal.tsx frontend/src/features/purchase-management/components/QuoteFormModal.tsx` → clean (no output).

#### `S1-FE-MAX_EXTRA_FIELDS-higher`

- **File:line** `frontend/src/features/purchase-management/components/QuoteFormModal.tsx:18`
- **Mutation** — S1 frontend / MAX_EXTRA_FIELDS / higher
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '18p' <scratchpad>/snap/S1-FE-MAX_EXTRA_FIELDS-higher.QuoteFormModal.tsx
  export const MAX_EXTRA_FIELDS = 20;
  $ sed -n '18p' frontend/src/features/purchase-management/components/QuoteFormModal.tsx
  export const MAX_EXTRA_FIELDS = 21;
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S1-FE-MAX_EXTRA_FIELDS-higher.json src/features/purchase-management/__tests__/QuoteFormModal.test.tsx`
- **Step-0 baseline** reused run **B-26** — `22 tests: 22 passed, 0 failed (files 1)`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- frontend/src/features/purchase-management/components/QuoteFormModal.tsx` was empty at snapshot; (b) every `cmp` since B-26 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i51`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `22 tests: 21 passed, 1 failed (files 1)`; exit 1
- **Reddened vs that baseline** (1) — `QuoteFormModal stops adding extra fields at twenty rows`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `765b01d809887f76059a7004a39e5e74a2c7f992d0201f03f24e71214b32e453`; restored file `shasum -a 256` = `765b01d809887f76059a7004a39e5e74a2c7f992d0201f03f24e71214b32e453`; `cmp <scratchpad>/snap/S1-FE-MAX_EXTRA_FIELDS-higher.QuoteFormModal.tsx frontend/src/features/purchase-management/components/QuoteFormModal.tsx` → clean (no output).

#### `S1-FE-MAX_QUOTE_ITEMS-lower`

- **File:line** `frontend/src/features/purchase-management/components/QuoteFormModal.tsx:21`
- **Mutation** — S1 frontend / MAX_QUOTE_ITEMS / lower
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '21p' <scratchpad>/snap/S1-FE-MAX_QUOTE_ITEMS-lower.QuoteFormModal.tsx
  export const MAX_QUOTE_ITEMS = 50;
  $ sed -n '21p' frontend/src/features/purchase-management/components/QuoteFormModal.tsx
  export const MAX_QUOTE_ITEMS = 49;
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S1-FE-MAX_QUOTE_ITEMS-lower.json src/features/purchase-management/__tests__/QuoteFormModal.test.tsx`
- **Step-0 baseline** reused run **B-26** — `22 tests: 22 passed, 0 failed (files 1)`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- frontend/src/features/purchase-management/components/QuoteFormModal.tsx` was empty at snapshot; (b) every `cmp` since B-26 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i52`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `22 tests: 22 passed, 0 failed (files 1)`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `no case names it — see Findings F-04`
- **Was it among the reddened?** no
- **Step-5 restore** pristine copy `shasum -a 256` = `765b01d809887f76059a7004a39e5e74a2c7f992d0201f03f24e71214b32e453`; restored file `shasum -a 256` = `765b01d809887f76059a7004a39e5e74a2c7f992d0201f03f24e71214b32e453`; `cmp <scratchpad>/snap/S1-FE-MAX_QUOTE_ITEMS-lower.QuoteFormModal.tsx frontend/src/features/purchase-management/components/QuoteFormModal.tsx` → clean (no output).

#### `S1-FE-MAX_QUOTE_ITEMS-higher`

- **File:line** `frontend/src/features/purchase-management/components/QuoteFormModal.tsx:21`
- **Mutation** — S1 frontend / MAX_QUOTE_ITEMS / higher
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '21p' <scratchpad>/snap/S1-FE-MAX_QUOTE_ITEMS-higher.QuoteFormModal.tsx
  export const MAX_QUOTE_ITEMS = 50;
  $ sed -n '21p' frontend/src/features/purchase-management/components/QuoteFormModal.tsx
  export const MAX_QUOTE_ITEMS = 51;
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S1-FE-MAX_QUOTE_ITEMS-higher.json src/features/purchase-management/__tests__/QuoteFormModal.test.tsx`
- **Step-0 baseline** reused run **B-26** — `22 tests: 22 passed, 0 failed (files 1)`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- frontend/src/features/purchase-management/components/QuoteFormModal.tsx` was empty at snapshot; (b) every `cmp` since B-26 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i53`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `22 tests: 22 passed, 0 failed (files 1)`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `no case names it — see Findings F-04`
- **Was it among the reddened?** no
- **Step-5 restore** pristine copy `shasum -a 256` = `765b01d809887f76059a7004a39e5e74a2c7f992d0201f03f24e71214b32e453`; restored file `shasum -a 256` = `765b01d809887f76059a7004a39e5e74a2c7f992d0201f03f24e71214b32e453`; `cmp <scratchpad>/snap/S1-FE-MAX_QUOTE_ITEMS-higher.QuoteFormModal.tsx frontend/src/features/purchase-management/components/QuoteFormModal.tsx` → clean (no output).

#### `S1-FE-MIN_JUSTIFICATION_LENGTH-lower`

- **File:line** `frontend/src/features/purchase-management/components/SelectQuoteModal.tsx:11`
- **Mutation** — S1 frontend / MIN_JUSTIFICATION_LENGTH / lower
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '11p' <scratchpad>/snap/S1-FE-MIN_JUSTIFICATION_LENGTH-lower.SelectQuoteModal.tsx
  export const MIN_JUSTIFICATION_LENGTH = 10;
  $ sed -n '11p' frontend/src/features/purchase-management/components/SelectQuoteModal.tsx
  export const MIN_JUSTIFICATION_LENGTH = 9;
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S1-FE-MIN_JUSTIFICATION_LENGTH-lower.json src/features/purchase-management/__tests__/SelectQuoteModal.test.tsx`
- **Step-0 baseline** run **B-27** (own run, same command on the unmutated file) — `18 tests: 18 passed, 0 failed (files 1)`; exit 0; `uv pip freeze` captured as `freeze.B-27`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `18 tests: 18 passed, 0 failed (files 1)`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `no case names it — see Findings F-05`
- **Was it among the reddened?** no
- **Step-5 restore** pristine copy `shasum -a 256` = `5009ff01ac5f93647dc55c12e6285aa3a44a99cb21c0c926ad4a48325e8c396f`; restored file `shasum -a 256` = `5009ff01ac5f93647dc55c12e6285aa3a44a99cb21c0c926ad4a48325e8c396f`; `cmp <scratchpad>/snap/S1-FE-MIN_JUSTIFICATION_LENGTH-lower.SelectQuoteModal.tsx frontend/src/features/purchase-management/components/SelectQuoteModal.tsx` → clean (no output).

#### `S1-FE-MIN_JUSTIFICATION_LENGTH-higher`

- **File:line** `frontend/src/features/purchase-management/components/SelectQuoteModal.tsx:11`
- **Mutation** — S1 frontend / MIN_JUSTIFICATION_LENGTH / higher
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '11p' <scratchpad>/snap/S1-FE-MIN_JUSTIFICATION_LENGTH-higher.SelectQuoteModal.tsx
  export const MIN_JUSTIFICATION_LENGTH = 10;
  $ sed -n '11p' frontend/src/features/purchase-management/components/SelectQuoteModal.tsx
  export const MIN_JUSTIFICATION_LENGTH = 11;
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S1-FE-MIN_JUSTIFICATION_LENGTH-higher.json src/features/purchase-management/__tests__/SelectQuoteModal.test.tsx`
- **Step-0 baseline** reused run **B-27** — `18 tests: 18 passed, 0 failed (files 1)`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- frontend/src/features/purchase-management/components/SelectQuoteModal.tsx` was empty at snapshot; (b) every `cmp` since B-27 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i54`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `18 tests: 18 passed, 0 failed (files 1)`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `no case names it — see Findings F-05`
- **Was it among the reddened?** no
- **Step-5 restore** pristine copy `shasum -a 256` = `5009ff01ac5f93647dc55c12e6285aa3a44a99cb21c0c926ad4a48325e8c396f`; restored file `shasum -a 256` = `5009ff01ac5f93647dc55c12e6285aa3a44a99cb21c0c926ad4a48325e8c396f`; `cmp <scratchpad>/snap/S1-FE-MIN_JUSTIFICATION_LENGTH-higher.SelectQuoteModal.tsx frontend/src/features/purchase-management/components/SelectQuoteModal.tsx` → clean (no output).

#### `S1-CFG-pytest_timeout-weak`

- **File:line** `backend/pytest.ini:17`
- **Mutation** — S1 config / pytest.ini timeout / weakening (raise the per-test cap past MAX_PER_TEST_TIMEOUT)
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '17p' <scratchpad>/snap/S1-CFG-pytest_timeout-weak.pytest.ini
  timeout = 300
  $ sed -n '17p' backend/pytest.ini
  timeout = 601
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_suite_hygiene.py`
- **Step-0 baseline** reused run **B-11** — `9 passed, 1 warning in 0.95s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/pytest.ini` was empty at snapshot; (b) every `cmp` since B-11 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i55`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `1 failed, 8 passed, 1 warning in 0.92s`; exit 1
- **Reddened vs that baseline** (1) — `tests/test_suite_hygiene.py::test_pytest_ini_caps_a_single_test`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `9a07d9cded340f66e8a1dffa1ddf3353b7a04f6d70b448c4710872eaeadaf229`; restored file `shasum -a 256` = `9a07d9cded340f66e8a1dffa1ddf3353b7a04f6d70b448c4710872eaeadaf229`; `cmp <scratchpad>/snap/S1-CFG-pytest_timeout-weak.pytest.ini backend/pytest.ini` → clean (no output).

#### `S1-CFG-pytest_timeout-strong`

- **File:line** `backend/pytest.ini:17`
- **Mutation** — S1 config / pytest.ini timeout / strengthening (lower the per-test cap to 1s)
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '17p' <scratchpad>/snap/S1-CFG-pytest_timeout-strong.pytest.ini
  timeout = 300
  $ sed -n '17p' backend/pytest.ini
  timeout = 1
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_suite_hygiene.py`
- **Step-0 baseline** reused run **B-11** — `9 passed, 1 warning in 0.95s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/pytest.ini` was empty at snapshot; (b) every `cmp` since B-11 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i56`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `9 passed, 1 warning in 0.92s`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `tests/test_suite_hygiene.py::test_pytest_ini_caps_a_single_test`
- **Was it among the reddened?** no — the case is a one-sided ceiling (`timeout <= MAX_PER_TEST_TIMEOUT`), so lowering the declaration to 1s is slack. Recorded in Over-pins as the measured asymmetry, not as a finding
- **Step-5 restore** pristine copy `shasum -a 256` = `9a07d9cded340f66e8a1dffa1ddf3353b7a04f6d70b448c4710872eaeadaf229`; restored file `shasum -a 256` = `9a07d9cded340f66e8a1dffa1ddf3353b7a04f6d70b448c4710872eaeadaf229`; `cmp <scratchpad>/snap/S1-CFG-pytest_timeout-strong.pytest.ini backend/pytest.ini` → clean (no output).

#### `S1-CFG-cov_fail_under-weak`

- **File:line** `backend/pytest.ini:4`
- **Mutation** — S1 config / pytest.ini --cov-fail-under / weakening (90 -> 1)
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '4p' <scratchpad>/snap/S1-CFG-cov_fail_under-weak.pytest.ini
  addopts = --cov=app --cov-fail-under=90
  $ sed -n '4p' backend/pytest.ini
  addopts = --cov=app --cov-fail-under=1
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_suite_hygiene.py`
- **Step-0 baseline** reused run **B-11** — `9 passed, 1 warning in 0.95s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/pytest.ini` was empty at snapshot; (b) every `cmp` since B-11 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i57`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `9 passed, 1 warning in 0.88s`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `no case reads it — see Findings F-06`
- **Was it among the reddened?** no
- **Step-5 restore** pristine copy `shasum -a 256` = `9a07d9cded340f66e8a1dffa1ddf3353b7a04f6d70b448c4710872eaeadaf229`; restored file `shasum -a 256` = `9a07d9cded340f66e8a1dffa1ddf3353b7a04f6d70b448c4710872eaeadaf229`; `cmp <scratchpad>/snap/S1-CFG-cov_fail_under-weak.pytest.ini backend/pytest.ini` → clean (no output).

#### `S1-CFG-cov_fail_under-strong`

- **File:line** `backend/pytest.ini:4`
- **Mutation** — S1 config / pytest.ini --cov-fail-under / strengthening (90 -> 100)
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '4p' <scratchpad>/snap/S1-CFG-cov_fail_under-strong.pytest.ini
  addopts = --cov=app --cov-fail-under=90
  $ sed -n '4p' backend/pytest.ini
  addopts = --cov=app --cov-fail-under=100
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_suite_hygiene.py`
- **Step-0 baseline** reused run **B-11** — `9 passed, 1 warning in 0.95s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/pytest.ini` was empty at snapshot; (b) every `cmp` since B-11 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i58`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `9 passed, 1 warning in 1.17s`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `no case reads it — see Findings F-06`
- **Was it among the reddened?** no
- **Step-5 restore** pristine copy `shasum -a 256` = `9a07d9cded340f66e8a1dffa1ddf3353b7a04f6d70b448c4710872eaeadaf229`; restored file `shasum -a 256` = `9a07d9cded340f66e8a1dffa1ddf3353b7a04f6d70b448c4710872eaeadaf229`; `cmp <scratchpad>/snap/S1-CFG-cov_fail_under-strong.pytest.ini backend/pytest.ini` → clean (no output).

#### `S2-BE-01`

- **File:line** `backend/tests/matrix_world.py:1466`
- **Mutation** — S2 be i=1 idx=24 matrix_world.py:63 prose 'the world is never rebuilt / every write undone': drop join_transaction_mode=create_savepoint
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '1466p' <scratchpad>/snap/S2-BE-01.matrix_world.py
      session = Session(bind=connection, join_transaction_mode="create_savepoint")
  $ sed -n '1466p' backend/tests/matrix_world.py
      session = Session(bind=connection)
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_permission_parity_matrix.py`
- **Step-0 baseline** reused run **B-04** — `1330 passed, 1273 warnings in 11.39s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/tests/matrix_world.py` was empty at snapshot; (b) every `cmp` since B-04 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i59`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `1330 passed, 1273 warnings in 11.35s`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `tests/test_permission_parity_matrix.py (the whole 1330-cell module, which matrix_world.py:63's prose is about)`
- **Was it among the reddened?** no — see Findings F-07
- **Step-5 restore** pristine copy `shasum -a 256` = `80b67b3fde15889390a4f023eff1f1648a3e89675869c9f112dcf7e65fabfc7d`; restored file `shasum -a 256` = `80b67b3fde15889390a4f023eff1f1648a3e89675869c9f112dcf7e65fabfc7d`; `cmp <scratchpad>/snap/S2-BE-01.matrix_world.py backend/tests/matrix_world.py` → clean (no output).

#### `S2-BE-02`

- **File:line** `backend/tests/test_clock.py:255`
- **Mutation** — S2 be i=2 idx=48 test_clock.py:253 prose 'the assertion would never reach the column': remove session.expire_all()
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '255p' <scratchpad>/snap/S2-BE-02.test_clock.py
      session.expire_all()
  $ sed -n '255p' backend/tests/test_clock.py
      pass  # APRAS-111 mutation: session.expire_all() removed
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_clock.py`
- **Step-0 baseline** reused run **B-02** — `12 passed, 10 warnings in 0.54s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/tests/test_clock.py` was empty at snapshot; (b) every `cmp` since B-02 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i60`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `12 passed, 10 warnings in 0.49s`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `tests/test_clock.py::test_purchase_request_created_at_is_stored_naive`
- **Was it among the reddened?** no — and this mutation does **not** discriminate the claim: the comment asserts the test would pass *vacuously* without `expire_all()`, and a vacuous pass and a real pass are both green. The discriminating run is S2-BE-02b
- **Step-5 restore** pristine copy `shasum -a 256` = `493b2bd097c655bfa85e2232899ff7eb6847e14c292cd5aa9677d270774f1203`; restored file `shasum -a 256` = `493b2bd097c655bfa85e2232899ff7eb6847e14c292cd5aa9677d270774f1203`; `cmp <scratchpad>/snap/S2-BE-02.test_clock.py backend/tests/test_clock.py` → clean (no output).

#### `S2-BE-03`

- **File:line** `backend/app/core/mail.py:121`
- **Mutation** — S2 be i=3 idx=72 test_mail.py:128 prose 'never one of the condominium's own elected offices': put the pt-BR office name in the copy
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '121p' <scratchpad>/snap/S2-BE-03.mail.py
          f"<p>Você foi convidado para ser o <strong>administrador</strong> do "
  $ sed -n '121p' backend/app/core/mail.py
          f"<p>Você foi convidado para ser o <strong>síndico</strong> do "
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_mail.py`
- **Step-0 baseline** run **B-28** (own run, same command on the unmutated file) — `7 passed, 1 warning in 0.08s`; exit 0; `uv pip freeze` captured as `freeze.B-28`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `1 failed, 6 passed, 1 warning in 0.08s`; exit 1
- **Reddened vs that baseline** (1) — `tests/test_mail.py::test_the_two_templates_carry_their_url_and_no_raw_credential_elsewhere`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `8950c693fcdb359459c4615130ce8c79cb5438e15654504c70ab7d01d13613d9`; restored file `shasum -a 256` = `8950c693fcdb359459c4615130ce8c79cb5438e15654504c70ab7d01d13613d9`; `cmp <scratchpad>/snap/S2-BE-03.mail.py backend/app/core/mail.py` → clean (no output).

#### `S2-BE-04`

- **File:line** `backend/app/schemas/occurrence.py:92`
- **Mutation** — S2 be i=4 idx=96 test_occurrences.py:218 prose 'answers [], never null': make the field default to null
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '92p' <scratchpad>/snap/S2-BE-04.occurrence.py
      infraction_ids: list[UUID] = Field(default_factory=list)
  $ sed -n '92p' backend/app/schemas/occurrence.py
      infraction_ids: list[UUID] | None = None
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_occurrences.py`
- **Step-0 baseline** run **B-29** (own run, same command on the unmutated file) — `6 passed, 6 warnings in 0.41s`; exit 0; `uv pip freeze` captured as `freeze.B-29`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `6 passed, 6 warnings in 0.39s`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `tests/test_occurrences.py::test_occurrence_detail_read_carries_infraction_ids_and_defaults_to_empty`
- **Was it among the reddened?** no — see Findings F-09
- **Step-5 restore** pristine copy `shasum -a 256` = `67657b783d97a42a46c91778c2babbc4044236ed420f6ba529b660e65a4bf1d8`; restored file `shasum -a 256` = `67657b783d97a42a46c91778c2babbc4044236ed420f6ba529b660e65a4bf1d8`; `cmp <scratchpad>/snap/S2-BE-04.occurrence.py backend/app/schemas/occurrence.py` → clean (no output).

#### `S2-BE-05`

- **File:line** `backend/app/services/purchase_service.py:997`
- **Mutation** — S2 be i=5 idx=120 parity_matrix:122 prose 'they mint no permission -- both reuse purchases:quote_update': give one attachment route its own permission
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '997p' <scratchpad>/snap/S2-BE-05.purchase_service.py
          cls._assert_can_view(current_user, session, "purchases:quote_update")
  $ sed -n '997p' backend/app/services/purchase_service.py
          cls._assert_can_view(current_user, session, "purchases:quote_update_MUTATED")
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_permission_parity_matrix.py`
- **Step-0 baseline** reused run **B-04** — `1330 passed, 1273 warnings in 11.39s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/app/services/purchase_service.py` was empty at snapshot; (b) every `cmp` since B-04 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i61`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `3 failed, 1327 passed, 1273 warnings in 11.56s`; exit 1
- **Reddened vs that baseline** (3) — `tests/test_permission_parity_matrix.py::test_cell_matches_the_recorded_baseline[ADMINISTRATOR-DELETE-/api/v1/purchase-requests/{request_id}/quotes/{quote_id}/attachment]`, `tests/test_permission_parity_matrix.py::test_cell_matches_the_recorded_baseline[DIRECTOR-DELETE-/api/v1/purchase-requests/{request_id}/quotes/{quote_id}/attachment]`, `tests/test_permission_parity_matrix.py::test_the_matrix_has_zero_divergence`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `a5607c3db3f9707330330de01d45745f8beae0cdfd7dcfb4be6ebea6e2b69fa5`; restored file `shasum -a 256` = `a5607c3db3f9707330330de01d45745f8beae0cdfd7dcfb4be6ebea6e2b69fa5`; `cmp <scratchpad>/snap/S2-BE-05.purchase_service.py backend/app/services/purchase_service.py` → clean (no output).

#### `S2-BE-06`

- **File:line** `backend/app/services/project_report_service.py:697`
- **Mutation** — S2 be i=6 idx=144 test_project_report.py:1210 prose 'means app.core.clock, never date.today()': read the system clock instead
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '697p' <scratchpad>/snap/S2-BE-06.project_report_service.py
      current = (today or clock.today_utc()).strftime("%Y-%m")
  $ sed -n '697p' backend/app/services/project_report_service.py
      current = (today or _dt.date.today()).strftime("%Y-%m")
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_project_report.py`
- **Step-0 baseline** run **B-30** (own run, same command on the unmutated file) — `100 passed, 105 warnings in 2.92s`; exit 0; `uv pip freeze` captured as `freeze.B-30`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `100 passed, 105 warnings in 2.82s`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `tests/test_project_report.py::test_planned_to_date_defaults_to_the_projects_clock`
- **Was it among the reddened?** no — see Findings F-10
- **Step-5 restore** pristine copy `shasum -a 256` = `d12d1a84bc47954ed3bbf1f34a831b1f3cecd6f2933c74f917120ba6df06d4d3`; restored file `shasum -a 256` = `d12d1a84bc47954ed3bbf1f34a831b1f3cecd6f2933c74f917120ba6df06d4d3`; `cmp <scratchpad>/snap/S2-BE-06.project_report_service.py backend/app/services/project_report_service.py` → clean (no output).

#### `S2-BE-07`

- **File:line** `backend/app/services/project_report_service.py:1339`
- **Mutation** — S2 be i=7 idx=168 test_project_report_branding.py:19 prose §B 'the logo ... named absolutely': emit a relative src
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '1339p' <scratchpad>/snap/S2-BE-07.project_report_service.py
      return f'<img src="{_e(public_tenant_logo_url(slug))}" alt="{tenant_name}">'
  $ sed -n '1339p' backend/app/services/project_report_service.py
      return f'<img src="{_e(public_tenant_logo_url(slug).replace("http://testserver", ""))}" alt="{tenant_name}">'
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_project_report_branding.py`
- **Step-0 baseline** reused run **B-06** — `39 passed, 11 warnings in 1.68s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/app/services/project_report_service.py` was empty at snapshot; (b) every `cmp` since B-06 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i62`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `39 passed, 11 warnings in 1.34s`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `tests/test_project_report_branding.py (§B, the module docstring's own claim at :19-24)`
- **Was it among the reddened?** no — see Findings F-11
- **Step-5 restore** pristine copy `shasum -a 256` = `d12d1a84bc47954ed3bbf1f34a831b1f3cecd6f2933c74f917120ba6df06d4d3`; restored file `shasum -a 256` = `d12d1a84bc47954ed3bbf1f34a831b1f3cecd6f2933c74f917120ba6df06d4d3`; `cmp <scratchpad>/snap/S2-BE-07.project_report_service.py backend/app/services/project_report_service.py` → clean (no output).

#### `S2-BE-08`

- **File:line** `backend/app/services/project_report_service.py:769`
- **Mutation** — S2 be i=8 idx=192 test_project_stage_detail.py:9 prose 'every malformed payload decodes to no detail, never to a partial read': give `leaves` a default so an absent key partially decodes
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '769p' <scratchpad>/snap/S2-BE-08.project_report_service.py
      leaves: tuple[StageLeaf, ...]
  $ sed -n '769p' backend/app/services/project_report_service.py
      leaves: tuple[StageLeaf, ...] = ()
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_project_stage_detail.py`
- **Step-0 baseline** run **B-31** (own run, same command on the unmutated file) — `62 passed, 1 warning in 0.07s`; exit 0; `uv pip freeze` captured as `freeze.B-31`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `1 failed, 61 passed, 1 warning in 0.07s`; exit 1
- **Reddened vs that baseline** (1) — `tests/test_project_stage_detail.py::test_an_absent_leaves_key_is_no_detail`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `d12d1a84bc47954ed3bbf1f34a831b1f3cecd6f2933c74f917120ba6df06d4d3`; restored file `shasum -a 256` = `d12d1a84bc47954ed3bbf1f34a831b1f3cecd6f2933c74f917120ba6df06d4d3`; `cmp <scratchpad>/snap/S2-BE-08.project_report_service.py backend/app/services/project_report_service.py` → clean (no output).

#### `S2-BE-09`

- **File:line** `backend/app/api/deps.py:185`
- **Mutation** — S2 be i=9 idx=216 test_role_permissions.py:128 prose 'a role of another tenant never composes': drop the acting-tenant narrowing
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '185p' <scratchpad>/snap/S2-BE-09.deps.py
      return {role.id for role in user.roles if role.tenant_id == tenant_id}
  $ sed -n '185p' backend/app/api/deps.py
      return {role.id for role in user.roles}
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_role_permissions.py`
- **Step-0 baseline** run **B-32** (own run, same command on the unmutated file) — `11 passed, 15 warnings in 0.52s`; exit 0; `uv pip freeze` captured as `freeze.B-32`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `1 failed, 10 passed, 15 warnings in 0.57s`; exit 1
- **Reddened vs that baseline** (1) — `tests/test_role_permissions.py::test_effective_ids_are_narrowed_to_the_acting_tenant`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `1ee2c977d54f724248890e2cec41e2e446c76928c6e0d6dcab1abe4455a4e4a5`; restored file `shasum -a 256` = `1ee2c977d54f724248890e2cec41e2e446c76928c6e0d6dcab1abe4455a4e4a5`; `cmp <scratchpad>/snap/S2-BE-09.deps.py backend/app/api/deps.py` → clean (no output).

#### `S2-BE-10`

- **File:line** `backend/tests/test_subscription_ceiling.py:450`
- **Mutation** — S2 be i=10 idx=240 test_subscription_ceiling.py:435 prose 'over the AST, never over source text': make the scan count source text too
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '450p' <scratchpad>/snap/S2-BE-10.test_subscription_ceiling.py
              if hit:
  $ sed -n '450p' backend/tests/test_subscription_ceiling.py
              if hit or name in path.read_text(encoding="utf-8"):
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_subscription_ceiling.py`
- **Step-0 baseline** run **B-33** (own run, same command on the unmutated file) — `15 passed, 45 warnings in 1.38s`; exit 0; `uv pip freeze` captured as `freeze.B-33`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `1 failed, 14 passed, 45 warnings in 5.74s`; exit 1
- **Reddened vs that baseline** (1) — `tests/test_subscription_ceiling.py::test_included_modules_has_at_most_four_homes`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `d932b01bc990b1ec743ed6026ecbc30d13c9f1f061bb8f6cbb550e181d17825e`; restored file `shasum -a 256` = `d932b01bc990b1ec743ed6026ecbc30d13c9f1f061bb8f6cbb550e181d17825e`; `cmp <scratchpad>/snap/S2-BE-10.test_subscription_ceiling.py backend/tests/test_subscription_ceiling.py` → clean (no output).

#### `S2-BE-11`

- **File:line** `backend/app/services/task_service.py:230`
- **Mutation** — S2 be i=11 idx=264 test_tenant_isolation.py:705 prose 'the response cannot expose the other tenant's category': expose the unresolved id
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '230p' <scratchpad>/snap/S2-BE-11.task_service.py
          task_data["category_name"] = category.name if category else None
  $ sed -n '230p' backend/app/services/task_service.py
          task_data["category_name"] = category.name if category else str(db_task.category_id)
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_tenant_isolation.py`
- **Step-0 baseline** run **B-34** (own run, same command on the unmutated file) — `170 passed, 411 warnings in 18.98s`; exit 0; `uv pip freeze` captured as `freeze.B-34`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `1 failed, 169 passed, 411 warnings in 18.97s`; exit 1
- **Reddened vs that baseline** (1) — `tests/test_tenant_isolation.py::test_cross_tenant_fk_on_create_does_not_resolve`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `2e292ca25a55b679430933e078d0cde77ceb4881e53a8f302e4d5dc77737ab41`; restored file `shasum -a 256` = `2e292ca25a55b679430933e078d0cde77ceb4881e53a8f302e4d5dc77737ab41`; `cmp <scratchpad>/snap/S2-BE-11.task_service.py backend/app/services/task_service.py` → clean (no output).

#### `S2-BE-12`

- **File:line** `backend/tests/tools/record_parity_baseline.py:58`
- **Mutation** — S2 be i=12 idx=287 record_parity_baseline.py:57 prose 'relative, never absolute: the _meta block must not leak a path': make it absolute
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '58p' <scratchpad>/snap/S2-BE-12.record_parity_baseline.py
  GENERATOR = "tests/tools/record_parity_baseline.py"
  $ sed -n '58p' backend/tests/tools/record_parity_baseline.py
  GENERATOR = "/Users/heitor/workspace/apras/backend/tests/tools/record_parity_baseline.py"
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_permission_parity_matrix.py`
- **Step-0 baseline** reused run **B-04** — `1330 passed, 1273 warnings in 11.39s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/tests/tools/record_parity_baseline.py` was empty at snapshot; (b) every `cmp` since B-04 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i63`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `1330 passed, 1273 warnings in 11.52s`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `tests/test_permission_parity_matrix.py::test_the_apras_61_baseline_carries_no_absolute_path_and_no_timestamp`
- **Was it among the reddened?** no — see Findings F-12
- **Step-5 restore** pristine copy `shasum -a 256` = `ebc9aaac3576328860413acba1097c62c850c1df3d11b863e056c073a8f6ff1c`; restored file `shasum -a 256` = `ebc9aaac3576328860413acba1097c62c850c1df3d11b863e056c073a8f6ff1c`; `cmp <scratchpad>/snap/S2-BE-12.record_parity_baseline.py backend/tests/tools/record_parity_baseline.py` → clean (no output).

#### `S2-BE-02b`

- **File:line** `backend/tests/test_clock.py:256`
- **Mutation** — S2 be i=2 supplementary: the discriminating mutation for the vacuity claim at test_clock.py:252-254 -- assert against the in-memory object instead of a re-read row
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '256p' <scratchpad>/snap/S2-BE-02b.test_clock.py
      stored = session.get(PurchaseRequest, read.id)
  $ sed -n '256p' backend/tests/test_clock.py
      stored = read  # APRAS-111 mutation: never re-read the column
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_clock.py`
- **Step-0 baseline** reused run **B-02** — `12 passed, 10 warnings in 0.54s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/tests/test_clock.py` was empty at snapshot; (b) every `cmp` since B-02 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i64`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `12 passed, 10 warnings in 1.22s`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `tests/test_clock.py::test_purchase_request_created_at_is_stored_naive`
- **Was it among the reddened?** no — see Findings F-08: the assertion is satisfied by the in-memory object, so the case does not reach the stored column
- **Step-5 restore** pristine copy `shasum -a 256` = `493b2bd097c655bfa85e2232899ff7eb6847e14c292cd5aa9677d270774f1203`; restored file `shasum -a 256` = `493b2bd097c655bfa85e2232899ff7eb6847e14c292cd5aa9677d270774f1203`; `cmp <scratchpad>/snap/S2-BE-02b.test_clock.py backend/tests/test_clock.py` → clean (no output).

#### `S2-BE-06b`

- **File:line** `backend/app/services/project_report_service.py:697`
- **Mutation** — S2 be i=6 supplementary: the same date.today() mutation measured against tests/test_lint_hygiene.py (the candidate for class 2, 'already asserted elsewhere')
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '697p' <scratchpad>/snap/S2-BE-06b.project_report_service.py
      current = (today or clock.today_utc()).strftime("%Y-%m")
  $ sed -n '697p' backend/app/services/project_report_service.py
      current = (today or _dt.date.today()).strftime("%Y-%m")
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_lint_hygiene.py`
- **Step-0 baseline** reused run **B-03** — `4 passed, 1 warning in 0.11s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/app/services/project_report_service.py` was empty at snapshot; (b) every `cmp` since B-03 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i65`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `1 failed, 3 passed, 1 warning in 0.19s`; exit 1
- **Reddened vs that baseline** (1) — `tests/test_lint_hygiene.py::test_clock_py_is_the_only_clock_in_app`
- **Case under examination** `tests/test_lint_hygiene.py::test_clock_py_is_the_only_clock_in_app`
- **Was it among the reddened?** yes — which is what makes F-10 class 2 (already asserted elsewhere) rather than an unprotected contract
- **Step-5 restore** pristine copy `shasum -a 256` = `d12d1a84bc47954ed3bbf1f34a831b1f3cecd6f2933c74f917120ba6df06d4d3`; restored file `shasum -a 256` = `d12d1a84bc47954ed3bbf1f34a831b1f3cecd6f2933c74f917120ba6df06d4d3`; `cmp <scratchpad>/snap/S2-BE-06b.project_report_service.py backend/app/services/project_report_service.py` → clean (no output).

#### `S2-BE-07b`

- **File:line** `backend/app/services/project_report_service.py:1339`
- **Mutation** — S2 be i=7 supplementary: the relative-src mutation measured against tests/test_project_report.py, which the branding module's docstring names as the authenticated half of the claim
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '1339p' <scratchpad>/snap/S2-BE-07b.project_report_service.py
      return f'<img src="{_e(public_tenant_logo_url(slug))}" alt="{tenant_name}">'
  $ sed -n '1339p' backend/app/services/project_report_service.py
      return f'<img src="{_e(public_tenant_logo_url(slug).replace("http://testserver", ""))}" alt="{tenant_name}">'
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_project_report.py`
- **Step-0 baseline** reused run **B-30** — `100 passed, 105 warnings in 2.92s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/app/services/project_report_service.py` was empty at snapshot; (b) every `cmp` since B-30 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i66`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `100 passed, 105 warnings in 3.04s`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `tests/test_project_report.py (named by the branding module's docstring as the authenticated half of the claim)`
- **Was it among the reddened?** no — confirms F-11 is class 1
- **Step-5 restore** pristine copy `shasum -a 256` = `d12d1a84bc47954ed3bbf1f34a831b1f3cecd6f2933c74f917120ba6df06d4d3`; restored file `shasum -a 256` = `d12d1a84bc47954ed3bbf1f34a831b1f3cecd6f2933c74f917120ba6df06d4d3`; `cmp <scratchpad>/snap/S2-BE-07b.project_report_service.py backend/app/services/project_report_service.py` → clean (no output).

#### `S2-BE-04b`

- **File:line** `backend/app/schemas/occurrence.py:92`
- **Mutation** — S2 be i=4 supplementary: the null-default mutation measured against tests/test_infractions.py, the other module that reads the promotion link
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '92p' <scratchpad>/snap/S2-BE-04b.occurrence.py
      infraction_ids: list[UUID] = Field(default_factory=list)
  $ sed -n '92p' backend/app/schemas/occurrence.py
      infraction_ids: list[UUID] | None = None
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_infractions.py`
- **Step-0 baseline** run **B-35** (own run, same command on the unmutated file) — `34 passed, 336 warnings in 3.17s`; exit 0; `uv pip freeze` captured as `freeze.B-35`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `34 passed, 336 warnings in 3.17s`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `tests/test_infractions.py (the other reader of the promotion link)`
- **Was it among the reddened?** no — confirms F-09 is class 1 and not class 2
- **Step-5 restore** pristine copy `shasum -a 256` = `67657b783d97a42a46c91778c2babbc4044236ed420f6ba529b660e65a4bf1d8`; restored file `shasum -a 256` = `67657b783d97a42a46c91778c2babbc4044236ed420f6ba529b660e65a4bf1d8`; `cmp <scratchpad>/snap/S2-BE-04b.occurrence.py backend/app/schemas/occurrence.py` → clean (no output).

#### `S2-FE-01`

- **File:line** `frontend/src/features/package-management/components/PackageStatusPage.tsx:26`
- **Mutation** — S2 fe i=1 idx=27 themeTokenMigration.test.ts:3010 prose 'carries no `dark:` occurrence before or after, so §1g never fires': add a dark: class to a PACKAGES component
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '26p' <scratchpad>/snap/S2-FE-01.PackageStatusPage.tsx
        <div className="flex items-center gap-3 bg-card p-6 rounded-xl border border-border shadow-sm">
  $ sed -n '26p' frontend/src/features/package-management/components/PackageStatusPage.tsx
        <div className="flex items-center gap-3 bg-card dark:bg-card p-6 rounded-xl border border-border shadow-sm">
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S2-FE-01.json src/__tests__/themeTokenMigration.test.ts`
- **Step-0 baseline** run **B-36** (own run, same command on the unmutated file) — `179 tests: 179 passed, 0 failed (files 1)`; exit 0; `uv pip freeze` captured as `freeze.B-36`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `179 tests: 178 passed, 1 failed (files 1)`; exit 1
- **Reddened vs that baseline** (1) — `APRAS-84's ledger arithmetic carries no `dark:` occurrence before or after, so §1g never fires`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `050e78050d17f1c7828fcbcb0d17f7b7071248a113d5432adbab161264721940`; restored file `shasum -a 256` = `050e78050d17f1c7828fcbcb0d17f7b7071248a113d5432adbab161264721940`; `cmp <scratchpad>/snap/S2-FE-01.PackageStatusPage.tsx frontend/src/features/package-management/components/PackageStatusPage.tsx` → clean (no output).

#### `S2-FE-02`

- **File:line** `frontend/src/api/publicProjects.ts:26`
- **Mutation** — S2 fe i=2 idx=53 publicProjects.ts:21 prose 'the path is written exactly as FastAPI mounts it, with no trailing slash': add the trailing slash
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '26p' <scratchpad>/snap/S2-FE-02.publicProjects.ts
    `/public/tenants/${encodeURIComponent(slug)}/projects/report`;
  $ sed -n '26p' frontend/src/api/publicProjects.ts
    `/public/tenants/${encodeURIComponent(slug)}/projects/report/`;
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S2-FE-02.json src/api/__tests__/publicProjects.test.ts`
- **Step-0 baseline** run **B-37** (own run, same command on the unmutated file) — `5 tests: 5 passed, 0 failed (files 1)`; exit 0; `uv pip freeze` captured as `freeze.B-37`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `5 tests: 2 passed, 3 failed (files 1)`; exit 1
- **Reddened vs that baseline** (3) — `the public obras report client (APRAS-92) builds the print link off the shared client's base URL`, `the public obras report client (APRAS-92) calls the route exactly as FastAPI mounts it, with no trailing slash`, `the public obras report client (APRAS-92) percent-encodes a slug that would otherwise break the path`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `8ef901d011b88bdc4f0f28b06e6407caae56b76ffa8b8cb701e92b025be9fc06`; restored file `shasum -a 256` = `8ef901d011b88bdc4f0f28b06e6407caae56b76ffa8b8cb701e92b025be9fc06`; `cmp <scratchpad>/snap/S2-FE-02.publicProjects.ts frontend/src/api/publicProjects.ts` → clean (no output).

#### `S2-FE-03`

- **File:line** `frontend/src/lib/contrast.ts:210`
- **Mutation** — S2 fe i=3 idx=79 mediaFeedbackAnnouncementsPackagesContrast.test.ts:12 prose 'the arithmetic is never reimplemented -- importing contrastRatio from src/lib/contrast.ts': halve the imported function's result, which a reimplemented copy would survive
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '210p' <scratchpad>/snap/S2-FE-03.contrast.ts
      (luminances[1] + LUMINANCE_OFFSET) / (luminances[0] + LUMINANCE_OFFSET)
  $ sed -n '210p' frontend/src/lib/contrast.ts
      (luminances[1] + LUMINANCE_OFFSET) / (luminances[0] + LUMINANCE_OFFSET) * 0.5
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S2-FE-03.json src/features/__tests__/mediaFeedbackAnnouncementsPackagesContrast.test.ts`
- **Step-0 baseline** reused run **B-21** — `73 tests: 73 passed, 0 failed (files 1)`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- frontend/src/lib/contrast.ts` was empty at snapshot; (b) every `cmp` since B-21 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i67`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `73 tests: 2 passed, 71 failed (files 1)`; exit 1
- **Reddened vs that baseline** (71) — `declared sub-AA or unmeasurable, and which are this task's 'AvatarWithFallback.tsx\'s avatar fill…' measures as declared`, `declared sub-AA or unmeasurable, and which are this task's 'CommentThread.tsx\'s delete glyph, --…' measures as declared`, `declared sub-AA or unmeasurable, and which are this task's 'graphical --primary on --accent/--mut…' measures as declared`, `declared sub-AA or unmeasurable, and which are this task's 'graphical --primary on --card, 3 sites' measures as declared`, `declared sub-AA or unmeasurable, and which are this task's 'kept text-emerald-600 on --card' measures as declared`, `declared sub-AA or unmeasurable, and which are this task's 'kept text-emerald-600 on bg-emerald-50' measures as declared`, `declared sub-AA or unmeasurable, and which are this task's 'kept text-white on bg-amber-500' measures as declared`, `declared sub-AA or unmeasurable, and which are this task's 'kept text-white on bg-rose-500' measures as declared`, `declared sub-AA or unmeasurable, and which are this task's clears AA at the kept status pairs the spec quotes above the floor`, `declared sub-AA or unmeasurable, and which are this task's measures each declared pair's *before* ratio too`, `every kept text foreground whose surface migrates still clears AA text-gray-700 is unchanged to the digit when bg-white becomes --card`, `every kept text foreground whose surface migrates still clears AA text-gray-700, was on bg-gray-100`, `every kept text foreground whose surface migrates still clears AA text-gray-800 is unchanged to the digit when bg-white becomes --card`, `every kept text foreground whose surface migrates still clears AA text-gray-800, was on bg-gray-100`, `every kept text foreground whose surface migrates still clears AA text-gray-800, was on bg-gray-50`, `every kept text foreground whose surface migrates still clears AA text-gray-800, was on bg-slate-50`, `every kept text foreground whose surface migrates still clears AA text-slate-700 is unchanged to the digit when bg-white becomes --card`, `every kept text foreground whose surface migrates still clears AA text-slate-700, was on bg-slate-200`, `every kept text foreground whose surface migrates still clears AA text-slate-800 is unchanged to the digit when bg-white becomes --card`, `the graphical pairs APRAS-84 changes brand icons on a card clears the 3:1 floor before and after`, `the graphical pairs APRAS-84 changes measures the carousel's active dot against its own container`, `the graphical pairs APRAS-84 changes the Eye glyph on a card clears the 3:1 floor before and after`, `the graphical pairs APRAS-84 changes the PDF glyph clears the 3:1 floor before and after`, `the graphical pairs APRAS-84 changes the delete glyph on a card clears the 3:1 floor before and after`, `the graphical pairs APRAS-84 changes the inline glyph on a neutral fill clears the 3:1 floor before and after`, `the graphical pairs APRAS-84 changes the tile glyphs on a brand tint clears the 3:1 floor before and after`, `the measurement is the repository's own reproduces --muted-foreground on --card`, `the measurement is the repository's own reproduces --muted-foreground on --muted`, `the measurement is the repository's own reproduces --primary on --accent`, `the measurement is the repository's own reproduces --primary on --background`, `the measurement is the repository's own reproduces --primary on --card`, `the measurement is the repository's own reproduces --primary-foreground on --primary`, `the measurement is the repository's own reproduces --primary-text on --accent`, `the measurement is the repository's own reproduces --primary-text on --card`, `the text pairs APRAS-84 changes "Ver Detalhes" control holds AA after, and its before ratio is measured too`, `the text pairs APRAS-84 changes approve buttons holds AA after, and its before ratio is measured too`, `the text pairs APRAS-84 changes confirm-reject button holds AA after, and its before ratio is measured too`, `the text pairs APRAS-84 changes crop-adjust link holds AA after, and its before ratio is measured too`, `the text pairs APRAS-84 changes headings holds AA after, and its before ratio is measured too`, `the text pairs APRAS-84 changes primary button holds AA after, and its before ratio is measured too`, `the text pairs APRAS-84 changes repairs the twelve text-*-400 sites, which failed AA before`, `the text pairs APRAS-84 changes repairs the two approve buttons, which failed AA before`, `the text pairs APRAS-84 changes secondary, gray-500 holds AA after, and its before ratio is measured too`, `the text pairs APRAS-84 changes secondary, gray-600 holds AA after, and its before ratio is measured too`, `the text pairs APRAS-84 changes secondary, slate-500 holds AA after, and its before ratio is measured too`, `the text pairs APRAS-84 changes secondary, slate-600 holds AA after, and its before ratio is measured too`, `the text pairs APRAS-84 changes table head on bg-gray-50 holds AA after, and its before ratio is measured too`, `the tokens this task paints with clears the 3:1 graphical floor: --primary on --accent`, `the tokens this task paints with clears the 3:1 graphical floor: --primary on --card`, `the tokens this task paints with clears the 3:1 graphical floor: --primary on --muted`, `the tokens this task paints with holds AA as text: --destructive on --card`, `the tokens this task paints with holds AA as text: --destructive-foreground on --destructive`, `the tokens this task paints with holds AA as text: --foreground on --card`, `the tokens this task paints with holds AA as text: --muted-foreground on --card`, `the tokens this task paints with holds AA as text: --muted-foreground on --muted`, `the tokens this task paints with holds AA as text: --primary-foreground on --primary`, `the tokens this task paints with holds AA as text: --primary-text on --accent`, `the tokens this task paints with holds AA as text: --primary-text on --card`, `the tokens this task paints with leaves --destructive-foreground on --destructive as the tightest text pair`, `§7 — the zoom slider, the one design change this child carries '#059669 — a síndico types the green' measures its track and thumb as the spec records`, `§7 — the zoom slider, the one design change this child carries '#2563eb' measures its track and thumb as the spec records`, `§7 — the zoom slider, the one design change this child carries '#7c3aed' measures its track and thumb as the spec records`, `§7 — the zoom slider, the one design change this child carries '#dc2626' measures its track and thumb as the spec records`, `§7 — the zoom slider, the one design change this child carries '#facc15 — the pale brand, an expected…' measures its track and thumb as the spec records`, `§7 — the zoom slider, the one design change this child carries 'the product default (the shipped them…' measures its track and thumb as the spec records`, `§7 — the zoom slider, the one design change this child carries clears the track's 3:1 floor in five themes and fails it in the pale one`, `§7 — the zoom slider, the one design change this child carries holds the thumb above AA in all six themes, which is more than it needs`, `§7 — the zoom slider, the one design change this child carries improves the thumb, measured against its own track`, `§7 — the zoom slider, the one design change this child carries measures what the rejected candidates would have given the thumb`, `§7 — the zoom slider, the one design change this child carries records the thumb against the panel the native widget overhangs`, `§7 — the zoom slider, the one design change this child carries repairs the track, which failed 1.4.11 before`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `2949bba8c67b2c518d1267f2ba35b1debf69048780acc0041c94abae43ad2895`; restored file `shasum -a 256` = `2949bba8c67b2c518d1267f2ba35b1debf69048780acc0041c94abae43ad2895`; `cmp <scratchpad>/snap/S2-FE-03.contrast.ts frontend/src/lib/contrast.ts` → clean (no output).

#### `S2-FE-04`

- **File:line** `frontend/src/features/infraction-management/components/ContestationForm.tsx:32`
- **Mutation** — S2 fe i=4 idx=105 ContestationForm.tsx:12 prose 'a closed deadline is a 409 the resident should never have to discover by submitting': make the form open when the deadline is absent too
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '32p' <scratchpad>/snap/S2-FE-04.ContestationForm.tsx
      defenseDueOn !== null &&
  $ sed -n '32p' frontend/src/features/infraction-management/components/ContestationForm.tsx
      defenseDueOn !== null ||
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S2-FE-04.json src/features/infraction-management/__tests__/MyInfractions.test.tsx`
- **Step-0 baseline** run **B-38** (own run, same command on the unmutated file) — `8 tests: 8 passed, 0 failed (files 1)`; exit 0; `uv pip freeze` captured as `freeze.B-38`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `8 tests: 7 passed, 1 failed (files 1)`; exit 1
- **Reddened vs that baseline** (1) — `ContestationForm is disabled with an explanatory message outside the deadline`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `c7569bf420d3c7edf1506a46a74112964fd7fbc3b76cac38580555a52acbec97`; restored file `shasum -a 256` = `c7569bf420d3c7edf1506a46a74112964fd7fbc3b76cac38580555a52acbec97`; `cmp <scratchpad>/snap/S2-FE-04.ContestationForm.tsx frontend/src/features/infraction-management/components/ContestationForm.tsx` → clean (no output).

#### `S2-FE-05`

- **File:line** `frontend/src/features/project-management/components/ProjectFormModal.tsx:157`
- **Mutation** — S2 fe i=5 idx=132 ProjectFormModal.tsx:149 prose 'a refused file never reaches the network and never becomes part of the intent': keep the refused file in the intent
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '157p' <scratchpad>/snap/S2-FE-05.ProjectFormModal.tsx
        cover.setFile(null);
  $ sed -n '157p' frontend/src/features/project-management/components/ProjectFormModal.tsx
        cover.setFile(picked);
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S2-FE-05.json src/features/project-management/__tests__/ProjectsFeature.test.tsx`
- **Step-0 baseline** run **B-39** (own run, same command on the unmutated file) — `11 tests: 11 passed, 0 failed (files 1)`; exit 0; `uv pip freeze` captured as `freeze.B-39`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `11 tests: 11 passed, 0 failed (files 1)`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `src/features/project-management/__tests__/ProjectsFeature.test.tsx`
- **Was it among the reddened?** no — but S2-FE-05b shows the claim *is* asserted, by a named sibling spec, so this is not a finding (see Examined and kept EK-02)
- **Step-5 restore** pristine copy `shasum -a 256` = `517ae175a8adf8c961b443eaa92c4e2d6498b7d41f97292825c9cdb350cbcec0`; restored file `shasum -a 256` = `517ae175a8adf8c961b443eaa92c4e2d6498b7d41f97292825c9cdb350cbcec0`; `cmp <scratchpad>/snap/S2-FE-05.ProjectFormModal.tsx frontend/src/features/project-management/components/ProjectFormModal.tsx` → clean (no output).

#### `S2-FE-06`

- **File:line** `frontend/src/features/task-management/components/AssigneePicker.tsx:63`
- **Mutation** — S2 fe i=6 idx=158 AssigneePicker.tsx:62 prose 'the no-assignee option is always last, and is never filtered out': drop it from the option count
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '63p' <scratchpad>/snap/S2-FE-06.AssigneePicker.tsx
    const optionCount = matches.length + 1;
  $ sed -n '63p' frontend/src/features/task-management/components/AssigneePicker.tsx
    const optionCount = matches.length;
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S2-FE-06.json src/features/task-management/components/__tests__/AssigneePicker.test.tsx`
- **Step-0 baseline** run **B-40** (own run, same command on the unmutated file) — `20 tests: 20 passed, 0 failed (files 1)`; exit 0; `uv pip freeze` captured as `freeze.B-40`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `20 tests: 18 passed, 2 failed (files 1)`; exit 1
- **Reddened vs that baseline** (2) — `AssigneePicker wraps around with ArrowUp from the first option`, `AssigneePicker wraps past the last option back to the first`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `4097e74e3d1563e101414fb04b0a544b2174e1111816a2f0b178f8da13c38203`; restored file `shasum -a 256` = `4097e74e3d1563e101414fb04b0a544b2174e1111816a2f0b178f8da13c38203`; `cmp <scratchpad>/snap/S2-FE-06.AssigneePicker.tsx frontend/src/features/task-management/components/AssigneePicker.tsx` → clean (no output).

#### `S2-FE-07`

- **File:line** `frontend/src/features/user-administration/__tests__/BrandedEntryLogin.integration.test.tsx:312`
- **Mutation** — S2 fe i=7 idx=184 BrandedEntryLogin.integration.test.tsx:322 prose 'the acting tenant was resolved from it. Measured here, never before': stop clearing the acting tenant before the run, so a stale value satisfies the settle
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '312p' <scratchpad>/snap/S2-FE-07.BrandedEntryLogin.integration.test.tsx
        clearActingTenantId();
  $ sed -n '312p' frontend/src/features/user-administration/__tests__/BrandedEntryLogin.integration.test.tsx
        // APRAS-111 mutation: clearActingTenantId() removed
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S2-FE-07.json src/features/user-administration/__tests__/BrandedEntryLogin.integration.test.tsx`
- **Step-0 baseline** run **B-41** (own run, same command on the unmutated file) — `3 tests: 3 passed, 0 failed (files 1)`; exit 0; `uv pip freeze` captured as `freeze.B-41`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `3 tests: 3 passed, 0 failed (files 1)`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `src/features/user-administration/__tests__/BrandedEntryLogin.integration.test.tsx > shows the no-access panel to an anonymous non-member`
- **Was it among the reddened?** no — the mutation does not discriminate; see S2-FE-07b and Examined and kept EK-03
- **Step-5 restore** pristine copy `shasum -a 256` = `ff344e2ce8c829143f38f60742c1bad036c475b2ecb9b996ce6558d1bb0e18b7`; restored file `shasum -a 256` = `ff344e2ce8c829143f38f60742c1bad036c475b2ecb9b996ce6558d1bb0e18b7`; `cmp <scratchpad>/snap/S2-FE-07.BrandedEntryLogin.integration.test.tsx frontend/src/features/user-administration/__tests__/BrandedEntryLogin.integration.test.tsx` → clean (no output).

#### `S2-FE-08`

- **File:line** `frontend/src/hooks/useInvitations.ts:33`
- **Mutation** — S2 fe i=8 idx=210 TenantsAdminPage.invitations.test.tsx:367 prose 'fills the whole column with ONE unfiltered call, never one per row': pass an argument to the list call
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '33p' <scratchpad>/snap/S2-FE-08.useInvitations.ts
      queryFn: () => listInvitations(),
  $ sed -n '33p' frontend/src/hooks/useInvitations.ts
      queryFn: () => listInvitations(undefined),
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S2-FE-08.json src/features/user-administration/__tests__/TenantsAdminPage.invitations.test.tsx`
- **Step-0 baseline** run **B-42** (own run, same command on the unmutated file) — `16 tests: 16 passed, 0 failed (files 1)`; exit 0; `uv pip freeze` captured as `freeze.B-42`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `16 tests: 15 passed, 1 failed (files 1)`; exit 1
- **Reddened vs that baseline** (1) — `TenantsAdminPage — the per-tenant invitation panel fills the whole column with ONE unfiltered call, never one per row`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `684b243892521be05e59c8e3223d2c9f799443b968710828cecfe9c3e343940b`; restored file `shasum -a 256` = `684b243892521be05e59c8e3223d2c9f799443b968710828cecfe9c3e343940b`; `cmp <scratchpad>/snap/S2-FE-08.useInvitations.ts frontend/src/hooks/useInvitations.ts` → clean (no output).

#### `S2-FE-09`

- **File:line** `frontend/src/features/user-administration/components/TenantBrandColors.tsx:382`
- **Mutation** — S2 fe i=9 idx=237 TenantBrandColors.tsx:357 prose 'it never closes by itself': close the paste dialog on any keydown, not only Escape
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '382p' <scratchpad>/snap/S2-FE-09.TenantBrandColors.tsx
        if (event.key === "Escape") onClose();
  $ sed -n '382p' frontend/src/features/user-administration/components/TenantBrandColors.tsx
        onClose();
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S2-FE-09.json src/features/user-administration/__tests__/TenantProfilePage.brand.test.tsx`
- **Step-0 baseline** run **B-43** (own run, same command on the unmutated file) — `44 tests: 44 passed, 0 failed (files 1)`; exit 0; `uv pip freeze` captured as `freeze.B-43`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `44 tests: 42 passed, 2 failed (files 1)`; exit 1
- **Reddened vs that baseline** (2) — `pasting an advanced palette cycles Tab and Shift+Tab inside the dialog`, `pasting an advanced palette wraps Shift+Tab from the textarea round to the dialog's last control`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `0e83e57297a70e0f556398e3b4e278d04a03a91761aa605114cd37f07e0d273f`; restored file `shasum -a 256` = `0e83e57297a70e0f556398e3b4e278d04a03a91761aa605114cd37f07e0d273f`; `cmp <scratchpad>/snap/S2-FE-09.TenantBrandColors.tsx frontend/src/features/user-administration/components/TenantBrandColors.tsx` → clean (no output).

#### `S2-FE-10`

- **File:line** `frontend/src/features/user-administration/pages/SubscriptionPage.tsx:97`
- **Mutation** — S2 fe i=10 idx=263 SubscriptionPage.tsx:88 prose 'courtesy and override modules ... are never sent': send OVERRIDE rows too
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '97p' <scratchpad>/snap/S2-FE-10.SubscriptionPage.tsx
        .filter((row) => !row.is_core && row.in_plan && row.source !== "OVERRIDE")
  $ sed -n '97p' frontend/src/features/user-administration/pages/SubscriptionPage.tsx
        .filter((row) => !row.is_core && row.in_plan)
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S2-FE-10.json src/features/user-administration/__tests__/SubscriptionPage.test.tsx`
- **Step-0 baseline** run **B-44** (own run, same command on the unmutated file) — `9 tests: 9 passed, 0 failed (files 1)`; exit 0; `uv pip freeze` captured as `freeze.B-44`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `9 tests: 9 passed, 0 failed (files 1)`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `src/features/user-administration/__tests__/SubscriptionPage.test.tsx`
- **Was it among the reddened?** no — see Findings F-13
- **Step-5 restore** pristine copy `shasum -a 256` = `de518997e320d2b30c92ac82143d12bf41618251f14f576591cf0f6683444ca0`; restored file `shasum -a 256` = `de518997e320d2b30c92ac82143d12bf41618251f14f576591cf0f6683444ca0`; `cmp <scratchpad>/snap/S2-FE-10.SubscriptionPage.tsx frontend/src/features/user-administration/pages/SubscriptionPage.tsx` → clean (no output).

#### `S2-FE-11`

- **File:line** `frontend/src/lib/brandPalettePaste.ts:113`
- **Mutation** — S2 fe i=11 idx=289 brandPalettePaste.ts:9 prose 'this module validates; it never normalises and never derives': lowercase every value on the way out
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '113p' <scratchpad>/snap/S2-FE-11.brandPalettePaste.ts
        BRAND_AUTHORED_KEYS.map((key) => [key, candidate[key] as string]),
  $ sed -n '113p' frontend/src/lib/brandPalettePaste.ts
        BRAND_AUTHORED_KEYS.map((key) => [key, (candidate[key] as string).toLowerCase()]),
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S2-FE-11.json src/lib/__tests__/brandPalettePaste.test.ts`
- **Step-0 baseline** run **B-45** (own run, same command on the unmutated file) — `40 tests: 40 passed, 0 failed (files 1)`; exit 0; `uv pip freeze` captured as `freeze.B-45`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `40 tests: 38 passed, 2 failed (files 1)`; exit 1
- **Reddened vs that baseline** (2) — `the JSON grammar accepts arbitrary whitespace, any key order and uppercase hex`, `the thirteen-key rule, identical in both grammars carries the values as typed, never lowercasing them`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `b07819ebb80ffdb2a5d7ce9dc4f16f71920a164ef62e341d00d947799d6892c5`; restored file `shasum -a 256` = `b07819ebb80ffdb2a5d7ce9dc4f16f71920a164ef62e341d00d947799d6892c5`; `cmp <scratchpad>/snap/S2-FE-11.brandPalettePaste.ts frontend/src/lib/brandPalettePaste.ts` → clean (no output).

#### `S2-FE-12`

- **File:line** `frontend/src/types/subscription.ts:54`
- **Mutation** — S2 fe i=12 idx=315 types/subscription.ts:51 prose 'exactly "the contracting PUT would accept this module", never looser': make the field optional in the declared contract
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '54p' <scratchpad>/snap/S2-FE-12.subscription.ts
    can_contract: boolean;
  $ sed -n '54p' frontend/src/types/subscription.ts
    can_contract?: boolean;
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S2-FE-12.json src/features/user-administration/__tests__/SubscriptionPage.test.tsx`
- **Step-0 baseline** reused run **B-44** — `9 tests: 9 passed, 0 failed (files 1)`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- frontend/src/types/subscription.ts` was empty at snapshot; (b) every `cmp` since B-44 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i68`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `9 tests: 9 passed, 0 failed (files 1)`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `src/features/user-administration/__tests__/SubscriptionPage.test.tsx`
- **Was it among the reddened?** no — structurally unpinnable; see Findings F-14
- **Step-5 restore** pristine copy `shasum -a 256` = `d8e17b48d95dbb82f423cdfd197eff2b5814e96fea0460fa69aa48e0782bd72a`; restored file `shasum -a 256` = `d8e17b48d95dbb82f423cdfd197eff2b5814e96fea0460fa69aa48e0782bd72a`; `cmp <scratchpad>/snap/S2-FE-12.subscription.ts frontend/src/types/subscription.ts` → clean (no output).

#### `S2-FE-05b`

- **File:line** `frontend/src/features/project-management/components/ProjectFormModal.tsx:157`
- **Mutation** — S2 fe i=5 supplementary: the same refused-file mutation measured against ProjectCoverPhoto.test.tsx, the other spec that names UPLOAD_MAX_FILE_SIZE_BYTES
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '157p' <scratchpad>/snap/S2-FE-05b.ProjectFormModal.tsx
        cover.setFile(null);
  $ sed -n '157p' frontend/src/features/project-management/components/ProjectFormModal.tsx
        cover.setFile(picked);
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S2-FE-05b.json src/features/project-management/__tests__/ProjectCoverPhoto.test.tsx`
- **Step-0 baseline** run **B-46** (own run, same command on the unmutated file) — `9 tests: 9 passed, 0 failed (files 1)`; exit 0; `uv pip freeze` captured as `freeze.B-46`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `9 tests: 8 passed, 1 failed (files 1)`; exit 1
- **Reddened vs that baseline** (1) — `the obra cover photo is chosen as a file refuses a non-image locally, naming the accepted formats`
- **Case under examination** `src/features/project-management/__tests__/ProjectCoverPhoto.test.tsx > the obra cover photo is chosen as a file refuses a non-image locally`
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `517ae175a8adf8c961b443eaa92c4e2d6498b7d41f97292825c9cdb350cbcec0`; restored file `shasum -a 256` = `517ae175a8adf8c961b443eaa92c4e2d6498b7d41f97292825c9cdb350cbcec0`; `cmp <scratchpad>/snap/S2-FE-05b.ProjectFormModal.tsx frontend/src/features/project-management/components/ProjectFormModal.tsx` → clean (no output).

#### `S2-FE-10b`

- **File:line** `frontend/src/features/user-administration/pages/SubscriptionPage.tsx:97`
- **Mutation** — S2 fe i=10 supplementary: the same OVERRIDE mutation measured against the whole src/features/user-administration/__tests__ directory, to test for class 2
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '97p' <scratchpad>/snap/S2-FE-10b.SubscriptionPage.tsx
        .filter((row) => !row.is_core && row.in_plan && row.source !== "OVERRIDE")
  $ sed -n '97p' frontend/src/features/user-administration/pages/SubscriptionPage.tsx
        .filter((row) => !row.is_core && row.in_plan)
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S2-FE-10b.json src/features/user-administration/__tests__`
- **Step-0 baseline** run **B-47** (own run, same command on the unmutated file) — `513 tests: 513 passed, 0 failed (files 51)`; exit 0; `uv pip freeze` captured as `freeze.B-47`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `513 tests: 513 passed, 0 failed (files 51)`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `the whole src/features/user-administration/__tests__ directory (513 cases, 51 files)`
- **Was it among the reddened?** no — which confirms F-13 is class 1 and not class 2
- **Step-5 restore** pristine copy `shasum -a 256` = `de518997e320d2b30c92ac82143d12bf41618251f14f576591cf0f6683444ca0`; restored file `shasum -a 256` = `de518997e320d2b30c92ac82143d12bf41618251f14f576591cf0f6683444ca0`; `cmp <scratchpad>/snap/S2-FE-10b.SubscriptionPage.tsx frontend/src/features/user-administration/pages/SubscriptionPage.tsx` → clean (no output).

#### `S2-FE-07b`

- **File:line** `frontend/src/features/user-administration/context/AuthContext.tsx:39`
- **Mutation** — S2 fe i=7 supplementary: the discriminating mutation -- clear the acting tenant before resolving it, so the settle at line 325 can only pass if the resolution really ran
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '39p' <scratchpad>/snap/S2-FE-07b.AuthContext.tsx
        setActingTenantId(
  $ sed -n '39p' frontend/src/features/user-administration/context/AuthContext.tsx
        setActingTenantId(null) ?? setActingTenantId(
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S2-FE-07b.json src/features/user-administration/__tests__/BrandedEntryLogin.integration.test.tsx`
- **Step-0 baseline** reused run **B-41** — `3 tests: 3 passed, 0 failed (files 1)`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- frontend/src/features/user-administration/context/AuthContext.tsx` was empty at snapshot; (b) every `cmp` since B-41 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i69`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `3 tests: 3 passed, 0 failed (files 1)`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `same case`
- **Was it among the reddened?** no — the resolution genuinely runs, so the settle at :325 is real. Not a finding
- **Step-5 restore** pristine copy `shasum -a 256` = `d76d0971c1fdd252c9a6ffab7f632988ccdf5ba962d62bee034922633fcd3d4b`; restored file `shasum -a 256` = `d76d0971c1fdd252c9a6ffab7f632988ccdf5ba962d62bee034922633fcd3d4b`; `cmp <scratchpad>/snap/S2-FE-07b.AuthContext.tsx frontend/src/features/user-administration/context/AuthContext.tsx` → clean (no output).

#### `S2-MAND-BE-escaping`

- **File:line** `backend/app/core/branding.py:698`
- **Mutation** — S2 mandatory module backend/tests/test_project_report_escaping.py -- prose at :199-209 'its values never pass through _e ... _emit rebuilds every value through format_oklch under a :.2f spec, so no stored byte reaches <style>': stop rebuilding through format_oklch
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '698p' <scratchpad>/snap/S2-MAND-BE-escaping.branding.py
      return {key: format_oklch(scheme[key]) for key in EMITTED_KEYS}
  $ sed -n '698p' backend/app/core/branding.py
      return {key: str(scheme[key]) for key in EMITTED_KEYS}
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_project_report_escaping.py`
- **Step-0 baseline** run **B-48** (own run, same command on the unmutated file) — `48 passed, 1 warning in 2.15s`; exit 0; `uv pip freeze` captured as `freeze.B-48`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `1 failed, 47 passed, 1 warning in 2.14s`; exit 1
- **Reddened vs that baseline** (1) — `tests/test_project_report_escaping.py::test_a_hostile_brand_theme_never_reaches_the_style_block`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `d18dbf5c863933cdf09bf362c7d91abaf6488b08c7f76493dfeccc7117efb667`; restored file `shasum -a 256` = `d18dbf5c863933cdf09bf362c7d91abaf6488b08c7f76493dfeccc7117efb667`; `cmp <scratchpad>/snap/S2-MAND-BE-escaping.branding.py backend/app/core/branding.py` → clean (no output).

#### `S2-MAND-BE-branding`

- **File:line** `backend/app/core/branding.py:168`
- **Mutation** — S2 mandatory module backend/tests/test_branding.py -- prose at :451-455 'it is what alarms if _STEP, _LIGHT_MUTED or _LIGHT_ACCENT_LIGHTNESS ever moves ... there is no cushion anywhere on this lattice': move _LIGHT_ACCENT_LIGHTNESS
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '168p' <scratchpad>/snap/S2-MAND-BE-branding.branding.py
  _LIGHT_ACCENT_LIGHTNESS = 0.96
  $ sed -n '168p' backend/app/core/branding.py
  _LIGHT_ACCENT_LIGHTNESS = 0.90
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_branding.py`
- **Step-0 baseline** run **B-49** (own run, same command on the unmutated file) — `116 passed, 1 warning in 8.46s`; exit 0; `uv pip freeze` captured as `freeze.B-49`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `3 failed, 113 passed, 1 warning in 8.74s`; exit 1
- **Reddened vs that baseline** (3) — `tests/test_branding.py::test_accent_stays_the_pale_hover_tint_of_the_accent_hue`, `tests/test_branding.py::test_the_default_brand_derives_the_stylesheets_own_primary_text`, `tests/test_branding.py::test_the_two_zero_margin_witnesses_are_pinned_to_the_float`
- **Case under examination** `tests/test_branding.py::test_primary_text_clears_aa_on_every_text_surface_over_the_lattice`
- **Was it among the reddened?** **no — neighbour-only reddening.** Three neighbours reddened; the case whose docstring claims to be 'what alarms if _STEP, _LIGHT_MUTED or _LIGHT_ACCENT_LIGHTNESS ever moves' did not. See Findings F-15
- **Step-5 restore** pristine copy `shasum -a 256` = `d18dbf5c863933cdf09bf362c7d91abaf6488b08c7f76493dfeccc7117efb667`; restored file `shasum -a 256` = `d18dbf5c863933cdf09bf362c7d91abaf6488b08c7f76493dfeccc7117efb667`; `cmp <scratchpad>/snap/S2-MAND-BE-branding.branding.py backend/app/core/branding.py` → clean (no output).

#### `S2-MAND-BE-escalation`

- **File:line** `backend/app/services/infraction_service.py:1111`
- **Mutation** — S2 mandatory module backend/tests/test_infraction_escalation.py -- prose at :789-791 'staff always have the explicit-fine_amount escape, which is what keeps §6.4's "the ladder is not a gate on staff judgement" true': remove the escape
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '1111p' <scratchpad>/snap/S2-MAND-BE-escalation.infraction_service.py
              if stage_in.fine_amount is not None:
  $ sed -n '1111p' backend/app/services/infraction_service.py
              if False:  # APRAS-111 mutation: remove the explicit fine_amount escape
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_infraction_escalation.py`
- **Step-0 baseline** run **B-50** (own run, same command on the unmutated file) — `22 passed, 293 warnings in 3.29s`; exit 0; `uv pip freeze` captured as `freeze.B-50`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `1 failed, 21 passed, 293 warnings in 3.18s`; exit 1
- **Reddened vs that baseline** (1) — `tests/test_infraction_escalation.py::test_an_explicit_multa_on_an_unpriced_multiple_rung_is_still_409`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `31a6483274e6a2bdf4a26bd4822e56ed642f5be74fe437652e22e7df3757acd9`; restored file `shasum -a 256` = `31a6483274e6a2bdf4a26bd4822e56ed642f5be74fe437652e22e7df3757acd9`; `cmp <scratchpad>/snap/S2-MAND-BE-escalation.infraction_service.py backend/app/services/infraction_service.py` → clean (no output).

#### `S2-MAND-BE-assets-rbac`

- **File:line** `backend/app/core/permissions.py:258`
- **Mutation** — S2 mandatory module backend/tests/test_assets_rbac.py -- the RBAC-parity claim its name carries: drop assets:delete from the bundle
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '258p' <scratchpad>/snap/S2-MAND-BE-assets-rbac.permissions.py
              "assets:delete",
  $ sed -n '258p' backend/app/core/permissions.py
              # "assets:delete",  # APRAS-111 mutation
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_assets_rbac.py`
- **Step-0 baseline** run **B-51** (own run, same command on the unmutated file) — `5 passed, 64 warnings in 0.83s`; exit 0; `uv pip freeze` captured as `freeze.B-51`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `5 passed, 64 warnings in 0.72s`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `tests/test_assets_rbac.py::test_blocked_roles_cannot_access_any_asset_endpoints`
- **Was it among the reddened?** no — but the mutation was mis-aimed: PERMISSIONS at permissions.py:254-259 is the permission *catalogue*, not a profile bundle. Re-aimed in S2-MAND-BE-assets-rbac-b; covered elsewhere per S2-MAND-BE-assets-rbac-c. Not a finding
- **Step-5 restore** pristine copy `shasum -a 256` = `82d6371c327586546f6bc2c9d6a90d1dd14912025219f93725fe163bb4863402`; restored file `shasum -a 256` = `82d6371c327586546f6bc2c9d6a90d1dd14912025219f93725fe163bb4863402`; `cmp <scratchpad>/snap/S2-MAND-BE-assets-rbac.permissions.py backend/app/core/permissions.py` → clean (no output).

#### `S2-MAND-FE-themeContrast`

- **File:line** `frontend/src/index.css:52`
- **Mutation** — S2 mandatory module frontend/src/__tests__/themeContrast.test.ts -- lighten the light-scheme --primary-text so it can no longer clear AA
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '52p' <scratchpad>/snap/S2-MAND-FE-themeContrast.index.css
    --primary-text: oklch(0.52 0.11 160);
  $ sed -n '52p' frontend/src/index.css
    --primary-text: oklch(0.80 0.11 160);
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S2-MAND-FE-themeContrast.json src/__tests__/themeContrast.test.ts`
- **Step-0 baseline** reused run **B-14** — `12 tests: 12 passed, 0 failed (files 1)`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- frontend/src/index.css` was empty at snapshot; (b) every `cmp` since B-14 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i70`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `12 tests: 11 passed, 1 failed (files 1)`; exit 1
- **Reddened vs that baseline** (1) — `src/index.css meets WCAG AA on every light pair`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `ed91f82638fb10f9d1479436106836f7b1fbac5975568562ba511cf87c8c4a5f`; restored file `shasum -a 256` = `ed91f82638fb10f9d1479436106836f7b1fbac5975568562ba511cf87c8c4a5f`; `cmp <scratchpad>/snap/S2-MAND-FE-themeContrast.index.css frontend/src/index.css` → clean (no output).

#### `S2-MAND-FE-access`

- **File:line** `frontend/src/features/user-administration/access/routeAccess.ts:93`
- **Mutation** — S2 mandatory module frontend/src/features/infraction-management/__tests__/access.test.ts -- prose at :83 'a resident reaches only their own view -- never the management list', with the regression a `{ module }` rule would introduce stated explicitly at :87-88: make /infractions exactly that `{ module }` rule
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '93p' <scratchpad>/snap/S2-MAND-FE-access.routeAccess.ts
    "/infractions": { anyOf: ["infractions:read"] },
  $ sed -n '93p' frontend/src/features/user-administration/access/routeAccess.ts
    "/infractions": { module: "infractions" },
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S2-MAND-FE-access.json src/features/infraction-management/__tests__/access.test.ts`
- **Step-0 baseline** run **B-52** (own run, same command on the unmutated file) — `6 tests: 6 passed, 0 failed (files 1)`; exit 0; `uv pip freeze` captured as `freeze.B-52`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `6 tests: 3 passed, 3 failed (files 1)`; exit 1
- **Reddened vs that baseline** (3) — `infraction route access a resident reaches only their own view -- never the management list`, `infraction route access a rules-only holder reaches the catalogue and not the management list`, `infraction route access declares a rule for each of the three routes`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `9e4c5ab45d43c92461e2b62aa3156b83b7c75bacff1561cdef31610590fe87f5`; restored file `shasum -a 256` = `9e4c5ab45d43c92461e2b62aa3156b83b7c75bacff1561cdef31610590fe87f5`; `cmp <scratchpad>/snap/S2-MAND-FE-access.routeAccess.ts frontend/src/features/user-administration/access/routeAccess.ts` → clean (no output).

#### `S2-MAND-FE-media`

- **File:line** `frontend/src/features/media-management/__tests__/MediaAssets.test.tsx:109`
- **Mutation** — S2 mandatory module frontend/src/features/media-management/__tests__/MediaAssets.test.tsx -- 'allows file selection and triggers upload': make the mocked upload reject, so the case's own claim that an upload is triggered and succeeds is put under load
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '109p' <scratchpad>/snap/S2-MAND-FE-media.MediaAssets.test.tsx
        vi.mocked(uploadsApi.uploadPhoto).mockResolvedValue(mockMediaAsset);
  $ sed -n '109p' frontend/src/features/media-management/__tests__/MediaAssets.test.tsx
        vi.mocked(uploadsApi.uploadPhoto).mockRejectedValue(new Error('APRAS-111 mutation'));
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S2-MAND-FE-media.json src/features/media-management/__tests__/MediaAssets.test.tsx`
- **Step-0 baseline** run **B-53** (own run, same command on the unmutated file) — `8 tests: 8 passed, 0 failed (files 1)`; exit 0; `uv pip freeze` captured as `freeze.B-53`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `8 tests: 7 passed, 1 failed (files 1)`; exit 1
- **Reddened vs that baseline** (1) — `Media Asset Components & Workflow PhotoUploadModal Component allows file selection and triggers upload`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `fae79b0bab060df8c0fee500fe7b99168024e433db4ab06becaeddb374c01ba7`; restored file `shasum -a 256` = `fae79b0bab060df8c0fee500fe7b99168024e433db4ab06becaeddb374c01ba7`; `cmp <scratchpad>/snap/S2-MAND-FE-media.MediaAssets.test.tsx frontend/src/features/media-management/__tests__/MediaAssets.test.tsx` → clean (no output).

#### `S2-MAND-BE-assets-rbac-b`

- **File:line** `backend/app/services/asset_service.py:263`
- **Mutation** — S2 mandatory module backend/tests/test_assets_rbac.py (second, properly targeted RBAC mutation) -- weaken the DELETE /assets/{asset_id} guard from assets:delete to assets:read, which MANAGER holds
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '263p' <scratchpad>/snap/S2-MAND-BE-assets-rbac-b.asset_service.py
          if not has_permission(current_user, session, "assets:delete"):
  $ sed -n '263p' backend/app/services/asset_service.py
          if not has_permission(current_user, session, "assets:read"):
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_assets_rbac.py`
- **Step-0 baseline** reused run **B-51** — `5 passed, 64 warnings in 0.83s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/app/services/asset_service.py` was empty at snapshot; (b) every `cmp` since B-51 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i71`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `1 failed, 4 passed, 60 warnings in 0.66s`; exit 1
- **Reddened vs that baseline** (1) — `tests/test_assets_rbac.py::test_manager_permissions`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `79bb0e2fb5d2265b2ea2ecd6389d2e6b7bf8eabd5e232b54d69e311fa26b356a`; restored file `shasum -a 256` = `79bb0e2fb5d2265b2ea2ecd6389d2e6b7bf8eabd5e232b54d69e311fa26b356a`; `cmp <scratchpad>/snap/S2-MAND-BE-assets-rbac-b.asset_service.py backend/app/services/asset_service.py` → clean (no output).

#### `S2-MAND-BE-assets-rbac-c`

- **File:line** `backend/app/core/permissions.py:258`
- **Mutation** — S2 mandatory module supplementary -- the PERMISSIONS-catalogue mutation measured against tests/test_permission_parity_matrix.py, the class-2 candidate
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '258p' <scratchpad>/snap/S2-MAND-BE-assets-rbac-c.permissions.py
              "assets:delete",
  $ sed -n '258p' backend/app/core/permissions.py
              # "assets:delete",  # APRAS-111 mutation
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_permission_parity_matrix.py`
- **Step-0 baseline** reused run **B-04** — `1330 passed, 1273 warnings in 11.39s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/app/core/permissions.py` was empty at snapshot; (b) every `cmp` since B-04 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i72`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `2 failed, 1328 passed, 1273 warnings in 13.48s`; exit 1
- **Reddened vs that baseline** (2) — `tests/test_permission_parity_matrix.py::test_cell_matches_the_recorded_baseline[ADMINISTRATOR-DELETE-/api/v1/assets/{asset_id}]`, `tests/test_permission_parity_matrix.py::test_the_matrix_has_zero_divergence`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `82d6371c327586546f6bc2c9d6a90d1dd14912025219f93725fe163bb4863402`; restored file `shasum -a 256` = `82d6371c327586546f6bc2c9d6a90d1dd14912025219f93725fe163bb4863402`; `cmp <scratchpad>/snap/S2-MAND-BE-assets-rbac-c.permissions.py backend/app/core/permissions.py` → clean (no output).

#### `S3-BE-01`

- **File:line** `backend/tests/test_document_folder_acl.py:319`
- **Mutation** — S3 backend i=1 idx=29 put the forbidden folder name into the population the assertion scans
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '319p' <scratchpad>/snap/S3-BE-01.test_document_folder_acl.py
      assert "Corrompida" not in _folder_names(client, world["member"])
  $ sed -n '319p' backend/tests/test_document_folder_acl.py
      assert "Corrompida" not in (list(_folder_names(client, world["member"])) + ["Corrompida"])
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_document_folder_acl.py`
- **Step-0 baseline** run **B-54** (own run, same command on the unmutated file) — `14 passed, 47 warnings in 0.92s`; exit 0; `uv pip freeze` captured as `freeze.B-54`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `1 failed, 13 passed, 45 warnings in 0.87s`; exit 1
- **Reddened vs that baseline** (1) — `tests/test_document_folder_acl.py::test_a_malformed_acl_denies_rather_than_raises`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `e3112a5585f054b2f531f854f25e6405c6d61fab5573e1acf2e744f767f794ac`; restored file `shasum -a 256` = `e3112a5585f054b2f531f854f25e6405c6d61fab5573e1acf2e744f767f794ac`; `cmp <scratchpad>/snap/S3-BE-01.test_document_folder_acl.py backend/tests/test_document_folder_acl.py` → clean (no output).

#### `S3-BE-02`

- **File:line** `backend/tests/test_invitations.py:245`
- **Mutation** — S3 backend i=2 idx=58 put a `token` key into the body the assertion scans
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '245p' <scratchpad>/snap/S3-BE-02.test_invitations.py
      assert "token" not in body
  $ sed -n '245p' backend/tests/test_invitations.py
      assert "token" not in {**body, "token": "APRAS-111"}
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_invitations.py`
- **Step-0 baseline** run **B-55** (own run, same command on the unmutated file) — `31 passed, 53 warnings in 1.59s`; exit 0; `uv pip freeze` captured as `freeze.B-55`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `1 failed, 30 passed, 53 warnings in 1.71s`; exit 1
- **Reddened vs that baseline** (1) — `tests/test_invitations.py::test_preview_returns_the_condominium_and_the_inviter`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `d90ea5f7c8f5c61da215997b1209b50165d045dc519a7bc23d4f979821818490`; restored file `shasum -a 256` = `d90ea5f7c8f5c61da215997b1209b50165d045dc519a7bc23d4f979821818490`; `cmp <scratchpad>/snap/S3-BE-02.test_invitations.py backend/tests/test_invitations.py` → clean (no output).

#### `S3-BE-03`

- **File:line** `backend/tests/test_migrations_postgres.py:1478`
- **Mutation** — S3 backend i=3 idx=87 put a disagreement into the population
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '1478p' <scratchpad>/snap/S3-BE-03.test_migrations_postgres.py
      assert not disagreements, (
  $ sed -n '1478p' backend/tests/test_migrations_postgres.py
      assert not {**disagreements, "APRAS-111.col": "x"}, (
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_migrations_postgres.py`
- **Step-0 baseline** run **B-56** (own run, same command on the unmutated file) — `(no pass/fail summary line; see below)`; exit 0; `uv pip freeze` captured as `freeze.B-56`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `(no summary line; see Not examined)`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `tests/test_migrations_postgres.py::test_every_timestamp_column_agrees_with_the_metadata`
- **Was it among the reddened?** not examined — the whole module is skipped pre-mutation (38 skipped, no Postgres). Substituted per the selection rule: see S3-BE-03sub
- **Step-5 restore** pristine copy `shasum -a 256` = `879be08db98963c5dfe042291f586210bed77e60d73180d276d4204370c8efce`; restored file `shasum -a 256` = `879be08db98963c5dfe042291f586210bed77e60d73180d276d4204370c8efce`; `cmp <scratchpad>/snap/S3-BE-03.test_migrations_postgres.py backend/tests/test_migrations_postgres.py` → clean (no output).

#### `S3-BE-04`

- **File:line** `backend/tests/test_permission_alignment.py:555`
- **Mutation** — S3 backend i=4 idx=116 put a member into the intersection the assertion forbids
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '555p' <scratchpad>/snap/S3-BE-04.test_permission_alignment.py
      assert not (set(MEMBERSHIP_GATED) & set(dependency_form()))
  $ sed -n '555p' backend/tests/test_permission_alignment.py
      assert not ((set(MEMBERSHIP_GATED) & set(dependency_form())) | {"APRAS-111"})
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_permission_alignment.py`
- **Step-0 baseline** run **B-57** (own run, same command on the unmutated file) — `321 passed, 316 warnings in 4.88s`; exit 0; `uv pip freeze` captured as `freeze.B-57`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `1 failed, 320 passed, 316 warnings in 4.54s`; exit 1
- **Reddened vs that baseline** (1) — `tests/test_permission_alignment.py::test_membership_gated_is_exactly_three_with_a_reason_each`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `e778fde09cd1ada03903ca19c6b75ee16f853077dbdf128ba28579bb496d712e`; restored file `shasum -a 256` = `e778fde09cd1ada03903ca19c6b75ee16f853077dbdf128ba28579bb496d712e`; `cmp <scratchpad>/snap/S3-BE-04.test_permission_alignment.py backend/tests/test_permission_alignment.py` → clean (no output).

#### `S3-BE-05`

- **File:line** `backend/tests/test_permission_parity_matrix.py:1121`
- **Mutation** — S3 backend i=5 idx=145 put the absolute path into the text the assertion scans
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '1121p' <scratchpad>/snap/S3-BE-05.test_permission_parity_matrix.py
      assert str(BACKEND_ROOT) not in raw
  $ sed -n '1121p' backend/tests/test_permission_parity_matrix.py
      assert str(BACKEND_ROOT) not in (raw + str(BACKEND_ROOT))
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_permission_parity_matrix.py`
- **Step-0 baseline** reused run **B-04** — `1330 passed, 1273 warnings in 11.39s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/tests/test_permission_parity_matrix.py` was empty at snapshot; (b) every `cmp` since B-04 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i73`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `1 failed, 1329 passed, 1273 warnings in 11.25s`; exit 1
- **Reddened vs that baseline** (1) — `tests/test_permission_parity_matrix.py::test_the_apras_61_baseline_carries_no_absolute_path_and_no_timestamp`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `3a8ec4a11e539247dae2fb131d4da64b940111abdbff5ec972cdf1a76501da94`; restored file `shasum -a 256` = `3a8ec4a11e539247dae2fb131d4da64b940111abdbff5ec972cdf1a76501da94`; `cmp <scratchpad>/snap/S3-BE-05.test_permission_parity_matrix.py backend/tests/test_permission_parity_matrix.py` → clean (no output).

#### `S3-BE-06`

- **File:line** `backend/tests/test_permission_parity_matrix.py:1483`
- **Mutation** — S3 backend i=6 idx=174 put an overlap into the forbidden intersection
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '1483p' <scratchpad>/snap/S3-BE-06.test_permission_parity_matrix.py
      assert not (sixty & sixty_three), "the APRAS-60 and APRAS-63 baselines overlap"
  $ sed -n '1483p' backend/tests/test_permission_parity_matrix.py
      assert not ((sixty & sixty_three) | {"APRAS-111"}), "the APRAS-60 and APRAS-63 baselines overlap"
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_permission_parity_matrix.py`
- **Step-0 baseline** reused run **B-04** — `1330 passed, 1273 warnings in 11.39s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/tests/test_permission_parity_matrix.py` was empty at snapshot; (b) every `cmp` since B-04 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i74`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `1 failed, 1329 passed, 1273 warnings in 13.45s`; exit 1
- **Reddened vs that baseline** (1) — `tests/test_permission_parity_matrix.py::test_the_three_baselines_partition_route_permissions_exactly`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `3a8ec4a11e539247dae2fb131d4da64b940111abdbff5ec972cdf1a76501da94`; restored file `shasum -a 256` = `3a8ec4a11e539247dae2fb131d4da64b940111abdbff5ec972cdf1a76501da94`; `cmp <scratchpad>/snap/S3-BE-06.test_permission_parity_matrix.py backend/tests/test_permission_parity_matrix.py` → clean (no output).

#### `S3-BE-07`

- **File:line** `backend/tests/test_permission_parity_matrix.py:771`
- **Mutation** — S3 backend i=7 idx=202 make every required query param count as unbound, so `missing` is non-empty
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '771p' <scratchpad>/snap/S3-BE-07.test_permission_parity_matrix.py
              if required and key not in QUERY_PARAMS:
  $ sed -n '771p' backend/tests/test_permission_parity_matrix.py
              if required or key not in QUERY_PARAMS:
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_permission_parity_matrix.py`
- **Step-0 baseline** reused run **B-04** — `1330 passed, 1273 warnings in 11.39s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/tests/test_permission_parity_matrix.py` was empty at snapshot; (b) every `cmp` since B-04 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i75`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `1 failed, 1329 passed, 1273 warnings in 12.94s`; exit 1
- **Reddened vs that baseline** (1) — `tests/test_permission_parity_matrix.py::test_every_required_query_parameter_has_a_binding`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `3a8ec4a11e539247dae2fb131d4da64b940111abdbff5ec972cdf1a76501da94`; restored file `shasum -a 256` = `3a8ec4a11e539247dae2fb131d4da64b940111abdbff5ec972cdf1a76501da94`; `cmp <scratchpad>/snap/S3-BE-07.test_permission_parity_matrix.py backend/tests/test_permission_parity_matrix.py` → clean (no output).

#### `S3-BE-08`

- **File:line** `backend/tests/test_project_report.py:1252`
- **Mutation** — S3 backend i=8 idx=231 put the forbidden marker into the markup the assertion scans
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '1252p' <scratchpad>/snap/S3-BE-08.test_project_report.py
      assert "close" not in markup
  $ sed -n '1252p' backend/tests/test_project_report.py
      assert "close" not in (markup + "close")
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_project_report.py`
- **Step-0 baseline** reused run **B-30** — `100 passed, 105 warnings in 2.92s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/tests/test_project_report.py` was empty at snapshot; (b) every `cmp` since B-30 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i76`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `1 failed, 99 passed, 105 warnings in 3.32s`; exit 1
- **Reddened vs that baseline** (1) — `tests/test_project_report.py::test_a_gap_of_eight_or_more_keeps_both_tags_above`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `0364d44124da6748c90a395b33815db73679f507478d4a532b48f24bf6d5d7eb`; restored file `shasum -a 256` = `0364d44124da6748c90a395b33815db73679f507478d4a532b48f24bf6d5d7eb`; `cmp <scratchpad>/snap/S3-BE-08.test_project_report.py backend/tests/test_project_report.py` → clean (no output).

#### `S3-BE-09`

- **File:line** `backend/tests/test_project_report.py:334`
- **Mutation** — S3 backend i=9 idx=260 put the other tenant's photo marker into the body
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '334p' <scratchpad>/snap/S3-BE-09.test_project_report.py
      assert "foto-alheia" not in body
  $ sed -n '334p' backend/tests/test_project_report.py
      assert "foto-alheia" not in (body + "foto-alheia")
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_project_report.py`
- **Step-0 baseline** reused run **B-30** — `100 passed, 105 warnings in 2.92s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/tests/test_project_report.py` was empty at snapshot; (b) every `cmp` since B-30 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i77`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `1 failed, 99 passed, 105 warnings in 3.00s`; exit 1
- **Reddened vs that baseline** (1) — `tests/test_project_report.py::test_the_report_never_leaks_another_tenants_rows`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `0364d44124da6748c90a395b33815db73679f507478d4a532b48f24bf6d5d7eb`; restored file `shasum -a 256` = `0364d44124da6748c90a395b33815db73679f507478d4a532b48f24bf6d5d7eb`; `cmp <scratchpad>/snap/S3-BE-09.test_project_report.py backend/tests/test_project_report.py` → clean (no output).

#### `S3-BE-10`

- **File:line** `backend/tests/test_project_report_branding.py:261`
- **Mutation** — S3 backend i=10 idx=289 put an unreferenced role into the population
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '261p' <scratchpad>/snap/S3-BE-10.test_project_report_branding.py
      assert not missing, f"declared but never referenced: {missing}"
  $ sed -n '261p' backend/tests/test_project_report_branding.py
      assert not (missing + ["APRAS-111"]), f"declared but never referenced: {missing}"
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_project_report_branding.py`
- **Step-0 baseline** reused run **B-06** — `39 passed, 11 warnings in 1.68s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/tests/test_project_report_branding.py` was empty at snapshot; (b) every `cmp` since B-06 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i78`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `1 failed, 38 passed, 11 warnings in 1.37s`; exit 1
- **Reddened vs that baseline** (1) — `tests/test_project_report_branding.py::test_every_named_variable_is_actually_referenced_by_the_document`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `6ed8af6f0040578cd1ff686306fb0f71cfc30d4936e4c2c22b8f1474e7ff4f4f`; restored file `shasum -a 256` = `6ed8af6f0040578cd1ff686306fb0f71cfc30d4936e4c2c22b8f1474e7ff4f4f`; `cmp <scratchpad>/snap/S3-BE-10.test_project_report_branding.py backend/tests/test_project_report_branding.py` → clean (no output).

#### `S3-BE-11`

- **File:line** `backend/tests/interpolation_audit.py:343`
- **Mutation** — S3 backend i=11 idx=318 delete `_param_holds`'s public clause, the live false SAFE the selected docstring at test_project_report_escaping.py:702 describes
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '343p' <scratchpad>/snap/S3-BE-11.interpolation_audit.py
          if not function.startswith("_"):
  $ sed -n '343p' backend/tests/interpolation_audit.py
          if False:  # APRAS-111 mutation: delete the public clause
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_project_report_escaping.py`
- **Step-0 baseline** reused run **B-48** — `48 passed, 1 warning in 2.15s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/tests/interpolation_audit.py` was empty at snapshot; (b) every `cmp` since B-48 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i79`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `1 failed, 47 passed, 1 warning in 1.87s`; exit 1
- **Reddened vs that baseline** (1) — `tests/test_project_report_escaping.py::test_the_audit_distrusts_a_public_functions_parameter`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `c7e4b9c7df24224621e3a13c8291053322612ff65c9f0b29b59382330d99addb`; restored file `shasum -a 256` = `c7e4b9c7df24224621e3a13c8291053322612ff65c9f0b29b59382330d99addb`; `cmp <scratchpad>/snap/S3-BE-11.interpolation_audit.py backend/tests/interpolation_audit.py` → clean (no output).

#### `S3-BE-12`

- **File:line** `backend/tests/test_project_stage_detail.py:638`
- **Mutation** — S3 backend i=12 idx=347 put the forbidden separator into the block
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '638p' <scratchpad>/snap/S3-BE-12.test_project_stage_detail.py
      assert TITLE_SEPARATOR not in block
  $ sed -n '638p' backend/tests/test_project_stage_detail.py
      assert TITLE_SEPARATOR not in (block + TITLE_SEPARATOR)
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_project_stage_detail.py`
- **Step-0 baseline** reused run **B-31** — `62 passed, 1 warning in 0.07s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/tests/test_project_stage_detail.py` was empty at snapshot; (b) every `cmp` since B-31 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i80`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `1 failed, 61 passed, 1 warning in 0.11s`; exit 1
- **Reddened vs that baseline** (1) — `tests/test_project_stage_detail.py::test_the_all_null_frame_survives_the_card_rewrite`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `63bdd1198467f4a03a9d32661c3474eb154529a7bfc9b43e04e41c17e501b4bc`; restored file `shasum -a 256` = `63bdd1198467f4a03a9d32661c3474eb154529a7bfc9b43e04e41c17e501b4bc`; `cmp <scratchpad>/snap/S3-BE-12.test_project_stage_detail.py backend/tests/test_project_stage_detail.py` → clean (no output).

#### `S3-BE-13`

- **File:line** `backend/tests/test_public_project_report.py:158`
- **Mutation** — S3 backend i=13 idx=376 put an Authorization header into the population
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '158p' <scratchpad>/snap/S3-BE-13.test_public_project_report.py
      assert "Authorization" not in response.request.headers
  $ sed -n '158p' backend/tests/test_public_project_report.py
      assert "Authorization" not in {**dict(response.request.headers), "Authorization": "x"}
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_public_project_report.py`
- **Step-0 baseline** reused run **B-07** — `13 passed, 7 warnings in 0.97s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/tests/test_public_project_report.py` was empty at snapshot; (b) every `cmp` since B-07 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i81`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `1 failed, 12 passed, 7 warnings in 0.97s`; exit 1
- **Reddened vs that baseline** (1) — `tests/test_public_project_report.py::test_an_anonymous_caller_gets_the_document`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `34c3dab273d4b573c64aa736bed0bf58a28e5585a9926e4e36c86b8e163fd649`; restored file `shasum -a 256` = `34c3dab273d4b573c64aa736bed0bf58a28e5585a9926e4e36c86b8e163fd649`; `cmp <scratchpad>/snap/S3-BE-13.test_public_project_report.py backend/tests/test_public_project_report.py` → clean (no output).

#### `S3-BE-14`

- **File:line** `backend/tests/test_purchase_quote_attachment.py:351`
- **Mutation** — S3 backend i=14 idx=404 actually create the file the assertion forbids, then assert its absence
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '351p' <scratchpad>/snap/S3-BE-14.test_purchase_quote_attachment.py
      assert not _stored_path(storage, stored["attachment_url"]).exists()
  $ sed -n '351p' backend/tests/test_purchase_quote_attachment.py
      assert not ((p := _stored_path(storage, stored["attachment_url"])).parent.mkdir(parents=True, exist_ok=True) or p.write_bytes(b"x") and p.exists())
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_purchase_quote_attachment.py`
- **Step-0 baseline** reused run **B-08** — `28 passed, 186 warnings in 1.78s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/tests/test_purchase_quote_attachment.py` was empty at snapshot; (b) every `cmp` since B-08 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i82`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `1 failed, 27 passed, 184 warnings in 1.94s`; exit 1
- **Reddened vs that baseline** (1) — `tests/test_purchase_quote_attachment.py::test_delete_clears_both_columns_removes_the_file_and_is_idempotent`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `b2079ab9bba9f16cbd4466c1696626de738e33949d53f0a203260c0f2b5bb27b`; restored file `shasum -a 256` = `b2079ab9bba9f16cbd4466c1696626de738e33949d53f0a203260c0f2b5bb27b`; `cmp <scratchpad>/snap/S3-BE-14.test_purchase_quote_attachment.py backend/tests/test_purchase_quote_attachment.py` → clean (no output).

#### `S3-BE-15`

- **File:line** `backend/tests/test_slug.py:72`
- **Mutation** — S3 backend i=15 idx=433 give the derived slug the trailing hyphen it forbids
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '72p' <scratchpad>/snap/S3-BE-15.test_slug.py
      assert not derived.endswith("-")
  $ sed -n '72p' backend/tests/test_slug.py
      assert not (derived + "-").endswith("-")
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_slug.py`
- **Step-0 baseline** reused run **B-09** — `74 passed, 1 warning in 0.36s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/tests/test_slug.py` was empty at snapshot; (b) every `cmp` since B-09 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i83`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `1 failed, 73 passed, 1 warning in 0.43s`; exit 1
- **Reddened vs that baseline** (1) — `tests/test_slug.py::test_a_long_name_is_truncated_to_sixty_and_never_ends_in_a_hyphen`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `9bb00777de45549dec01f18bb7f040778d29e2c2b42b5de631303f07f095d2c7`; restored file `shasum -a 256` = `9bb00777de45549dec01f18bb7f040778d29e2c2b42b5de631303f07f095d2c7`; `cmp <scratchpad>/snap/S3-BE-15.test_slug.py backend/tests/test_slug.py` → clean (no output).

#### `S3-BE-16`

- **File:line** `backend/tests/test_subscription_ceiling.py:488`
- **Mutation** — S3 backend i=16 idx=462 put `build_read` into the name set the assertion scans
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '488p' <scratchpad>/snap/S3-BE-16.test_subscription_ceiling.py
      assert "build_read" not in {
  $ sed -n '488p' backend/tests/test_subscription_ceiling.py
      assert "build_read" not in {"build_read"} | {
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_subscription_ceiling.py`
- **Step-0 baseline** reused run **B-33** — `15 passed, 45 warnings in 1.38s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/tests/test_subscription_ceiling.py` was empty at snapshot; (b) every `cmp` since B-33 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i84`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `1 failed, 14 passed, 45 warnings in 1.50s`; exit 1
- **Reddened vs that baseline** (1) — `tests/test_subscription_ceiling.py::test_included_modules_has_at_most_four_homes`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `d932b01bc990b1ec743ed6026ecbc30d13c9f1f061bb8f6cbb550e181d17825e`; restored file `shasum -a 256` = `d932b01bc990b1ec743ed6026ecbc30d13c9f1f061bb8f6cbb550e181d17825e`; `cmp <scratchpad>/snap/S3-BE-16.test_subscription_ceiling.py backend/tests/test_subscription_ceiling.py` → clean (no output).

#### `S3-BE-17`

- **File:line** `backend/tests/test_superuser_grant.py:379`
- **Mutation** — S3 backend i=17 idx=491 put the forbidden key into each payload
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '379p' <scratchpad>/snap/S3-BE-17.test_superuser_grant.py
          assert "is_superuser" not in payload
  $ sed -n '379p' backend/tests/test_superuser_grant.py
          assert "is_superuser" not in {**payload, "is_superuser": True}
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_superuser_grant.py`
- **Step-0 baseline** run **B-58** (own run, same command on the unmutated file) — `16 passed, 30 warnings in 1.00s`; exit 0; `uv pip freeze` captured as `freeze.B-58`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `1 failed, 15 passed, 30 warnings in 0.92s`; exit 1
- **Reddened vs that baseline** (1) — `tests/test_superuser_grant.py::test_user_read_still_does_not_expose_is_superuser`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `3b5e2db0d7a4604a0c157132ab235e95a5ae0f0b1f8157b662bdec9f7adda610`; restored file `shasum -a 256` = `3b5e2db0d7a4604a0c157132ab235e95a5ae0f0b1f8157b662bdec9f7adda610`; `cmp <scratchpad>/snap/S3-BE-17.test_superuser_grant.py backend/tests/test_superuser_grant.py` → clean (no output).

#### `S3-BE-18`

- **File:line** `backend/tests/test_tenant_models.py:272`
- **Mutation** — S3 backend i=18 idx=520 put `tenant_id` into the column name population
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '272p' <scratchpad>/snap/S3-BE-18.test_tenant_models.py
      assert "tenant_id" not in user_table.columns
  $ sed -n '272p' backend/tests/test_tenant_models.py
      assert "tenant_id" not in (list(user_table.columns.keys()) + ["tenant_id"])
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_tenant_models.py`
- **Step-0 baseline** run **B-59** (own run, same command on the unmutated file) — `11 passed, 1 warning in 0.27s`; exit 0; `uv pip freeze` captured as `freeze.B-59`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `1 failed, 10 passed, 1 warning in 0.28s`; exit 1
- **Reddened vs that baseline** (1) — `tests/test_tenant_models.py::test_user_stays_global`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `8460049dab763e42b91bb1aca866772ed995ce8bbac02390ed551a48201dd0c0`; restored file `shasum -a 256` = `8460049dab763e42b91bb1aca866772ed995ce8bbac02390ed551a48201dd0c0`; `cmp <scratchpad>/snap/S3-BE-18.test_tenant_models.py backend/tests/test_tenant_models.py` → clean (no output).

#### `S3-BE-19`

- **File:line** `backend/tests/test_uploads.py:345`
- **Mutation** — S3 backend i=19 idx=549 put a thumb_ file into the written population
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '345p' <scratchpad>/snap/S3-BE-19.test_uploads.py
      assert not any(path.name.startswith("thumb_") for path in written)
  $ sed -n '345p' backend/tests/test_uploads.py
      assert not any(path.name.startswith("thumb_") for path in (written + [type(written[0])("thumb_x.png")]))
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_uploads.py`
- **Step-0 baseline** reused run **B-13** — `8 passed, 23 warnings in 0.65s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/tests/test_uploads.py` was empty at snapshot; (b) every `cmp` since B-13 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i85`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `1 failed, 7 passed, 23 warnings in 0.78s`; exit 1
- **Reddened vs that baseline** (1) — `tests/test_uploads.py::test_a_hostile_photo_name_cannot_choose_either_stored_extension`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `71231cab302a3ea9f0aade846a07597a4ba6d1ad6b84bd3d1314753387434626`; restored file `shasum -a 256` = `71231cab302a3ea9f0aade846a07597a4ba6d1ad6b84bd3d1314753387434626`; `cmp <scratchpad>/snap/S3-BE-19.test_uploads.py backend/tests/test_uploads.py` → clean (no output).

#### `S3-BE-20`

- **File:line** `backend/tests/voting_helpers.py:43`
- **Mutation** — S3 backend i=20 idx=577 invert the pool guard so the helper returns a CPF that is already used
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '43p' <scratchpad>/snap/S3-BE-20.voting_helpers.py
          if cpf not in used:
  $ sed -n '43p' backend/tests/voting_helpers.py
          if cpf in used:
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_voting.py`
- **Step-0 baseline** run **B-60** (own run, same command on the unmutated file) — `19 passed, 1 warning in 1.14s`; exit 0; `uv pip freeze` captured as `freeze.B-60`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `19 passed, 1 warning in 1.12s`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `tests/test_voting.py (every case that draws a CPF from the pool)`
- **Was it among the reddened?** no — see Findings F-16
- **Step-5 restore** pristine copy `shasum -a 256` = `6efc2ba3bcbc6ef75e6fcf5c6fc3b444a7c1b9f0c285ec81271ba40e62fdec16`; restored file `shasum -a 256` = `6efc2ba3bcbc6ef75e6fcf5c6fc3b444a7c1b9f0c285ec81271ba40e62fdec16`; `cmp <scratchpad>/snap/S3-BE-20.voting_helpers.py backend/tests/voting_helpers.py` → clean (no output).

#### `S3-BE-03sub`

- **File:line** `backend/tests/test_module_gating.py:115`
- **Mutation** — S3 backend i=3 substitution idx=99 (skipped backend/tests/test_migrations_postgres.py:1478, module skipped pre-mutation -> substituted backend/tests/test_module_gating.py:115): put a member into the intersection the assertion forbids
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '115p' <scratchpad>/snap/S3-BE-03sub.test_module_gating.py
      assert not (after & FINANCE_PERMISSIONS)
  $ sed -n '115p' backend/tests/test_module_gating.py
      assert not ((after & FINANCE_PERMISSIONS) | {"APRAS-111"})
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_module_gating.py`
- **Step-0 baseline** run **B-61** (own run, same command on the unmutated file) — `11 passed, 29 warnings in 0.80s`; exit 0; `uv pip freeze` captured as `freeze.B-61`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `1 failed, 10 passed, 29 warnings in 0.81s`; exit 1
- **Reddened vs that baseline** (1) — `tests/test_module_gating.py::test_a_disabled_modules_permissions_leave_the_effective_set`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `49b29f1b05277cc62e27f0e31626b0f21b2d6005d5cc29435776a42ba7f932ac`; restored file `shasum -a 256` = `49b29f1b05277cc62e27f0e31626b0f21b2d6005d5cc29435776a42ba7f932ac`; `cmp <scratchpad>/snap/S3-BE-03sub.test_module_gating.py backend/tests/test_module_gating.py` → clean (no output).

#### `S3-BE-20b`

- **File:line** `backend/tests/voting_helpers.py:43`
- **Mutation** — S3 backend i=20 supplementary: the same pool-guard inversion measured against the other two voting modules, the class-2 candidates
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '43p' <scratchpad>/snap/S3-BE-20b.voting_helpers.py
          if cpf not in used:
  $ sed -n '43p' backend/tests/voting_helpers.py
          if cpf in used:
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_voting_edge_cases.py tests/test_voting_rbac.py`
- **Step-0 baseline** run **B-62** (own run, same command on the unmutated file) — `51 passed, 111 warnings in 3.07s`; exit 0; `uv pip freeze` captured as `freeze.B-62`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `51 passed, 111 warnings in 3.09s`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `tests/test_voting_edge_cases.py + tests/test_voting_rbac.py (51 cases)`
- **Was it among the reddened?** no — confirms F-16 is class 1 across all three voting modules
- **Step-5 restore** pristine copy `shasum -a 256` = `6efc2ba3bcbc6ef75e6fcf5c6fc3b444a7c1b9f0c285ec81271ba40e62fdec16`; restored file `shasum -a 256` = `6efc2ba3bcbc6ef75e6fcf5c6fc3b444a7c1b9f0c285ec81271ba40e62fdec16`; `cmp <scratchpad>/snap/S3-BE-20b.voting_helpers.py backend/tests/voting_helpers.py` → clean (no output).

#### `S3-FE-01`

- **File:line** `frontend/src/__tests__/themeTokenMigration.test.ts:2149`
- **Mutation** — S3 frontend i=1 idx=28 candidate line 2150 `).toHaveLength(0);`, mutated line 2149: put a forbidden `dark:` match into the population the assertion counts
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '2149p' <scratchpad>/snap/S3-FE-01.themeTokenMigration.test.ts
          .flatMap((file) => [...file.source.matchAll(/\bdark:/g)]),
  $ sed -n '2149p' frontend/src/__tests__/themeTokenMigration.test.ts
          .flatMap((file) => [...file.source.matchAll(/\bdark:/g), "APRAS-111"]),
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S3-FE-01.json src/__tests__/themeTokenMigration.test.ts`
- **Step-0 baseline** reused run **B-36** — `179 tests: 179 passed, 0 failed (files 1)`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- frontend/src/__tests__/themeTokenMigration.test.ts` was empty at snapshot; (b) every `cmp` since B-36 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i86`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `179 tests: 178 passed, 1 failed (files 1)`; exit 1
- **Reddened vs that baseline** (1) — `APRAS-81's ledger arithmetic deletes every dark: sibling of a migrated base and keeps exactly 57`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `0ff3cb34ed019b26d01d65c33258fe5ac11f400c90714ff4d41a54e0975b4272`; restored file `shasum -a 256` = `0ff3cb34ed019b26d01d65c33258fe5ac11f400c90714ff4d41a54e0975b4272`; `cmp <scratchpad>/snap/S3-FE-01.themeTokenMigration.test.ts frontend/src/__tests__/themeTokenMigration.test.ts` → clean (no output).

#### `S3-FE-02`

- **File:line** `frontend/src/features/announcement-feed/__tests__/AnnouncementFeed.test.tsx:454`
- **Mutation** — S3 frontend i=2 idx=56 substitute a present element when the query finds nothing
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '454p' <scratchpad>/snap/S3-FE-02.AnnouncementFeed.test.tsx
      expect(screen.queryByLabelText("Excluir comunicado")).not.toBeInTheDocument();
  $ sed -n '454p' frontend/src/features/announcement-feed/__tests__/AnnouncementFeed.test.tsx
      expect(screen.queryByLabelText("Excluir comunicado") ?? document.body).not.toBeInTheDocument();
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S3-FE-02.json src/features/announcement-feed/__tests__/AnnouncementFeed.test.tsx`
- **Step-0 baseline** run **B-63** (own run, same command on the unmutated file) — `19 tests: 19 passed, 0 failed (files 1)`; exit 0; `uv pip freeze` captured as `freeze.B-63`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `19 tests: 18 passed, 1 failed (files 1)`; exit 1
- **Reddened vs that baseline** (1) — `AnnouncementCard hides edit/delete controls for residents`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `ac2ac05504d69c190da6a24036e3445eab643a886c91a405ebcdf58ee7141519`; restored file `shasum -a 256` = `ac2ac05504d69c190da6a24036e3445eab643a886c91a405ebcdf58ee7141519`; `cmp <scratchpad>/snap/S3-FE-02.AnnouncementFeed.test.tsx frontend/src/features/announcement-feed/__tests__/AnnouncementFeed.test.tsx` → clean (no output).

#### `S3-FE-03`

- **File:line** `frontend/src/features/asset-management/__tests__/AssetTable.test.tsx:103`
- **Mutation** — S3 frontend i=3 idx=83 substitute a present element when the query finds nothing
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '103p' <scratchpad>/snap/S3-FE-03.AssetTable.test.tsx
      expect(screen.queryByTitle("Excluir")).not.toBeInTheDocument();
  $ sed -n '103p' frontend/src/features/asset-management/__tests__/AssetTable.test.tsx
      expect(screen.queryByTitle("Excluir") ?? document.body).not.toBeInTheDocument();
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S3-FE-03.json src/features/asset-management/__tests__/AssetTable.test.tsx`
- **Step-0 baseline** run **B-64** (own run, same command on the unmutated file) — `3 tests: 3 passed, 0 failed (files 1)`; exit 0; `uv pip freeze` captured as `freeze.B-64`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `3 tests: 2 passed, 1 failed (files 1)`; exit 1
- **Reddened vs that baseline** (1) — `AssetTable component hides edit and delete buttons when canManage is false`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `2b84b2bb3b2e381c10048dddfbb403b529f03e753b322394262249e54d4c30a6`; restored file `shasum -a 256` = `2b84b2bb3b2e381c10048dddfbb403b529f03e753b322394262249e54d4c30a6`; `cmp <scratchpad>/snap/S3-FE-03.AssetTable.test.tsx frontend/src/features/asset-management/__tests__/AssetTable.test.tsx` → clean (no output).

#### `S3-FE-04`

- **File:line** `frontend/src/features/infraction-management/__tests__/AttachmentUploader.test.tsx:217`
- **Mutation** — S3 frontend i=4 idx=111 substitute a present element when the query finds nothing
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '217p' <scratchpad>/snap/S3-FE-04.AttachmentUploader.test.tsx
      expect(screen.queryByTestId("attachment-unavailable")).not.toBeInTheDocument();
  $ sed -n '217p' frontend/src/features/infraction-management/__tests__/AttachmentUploader.test.tsx
      expect(screen.queryByTestId("attachment-unavailable") ?? document.body).not.toBeInTheDocument();
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S3-FE-04.json src/features/infraction-management/__tests__/AttachmentUploader.test.tsx`
- **Step-0 baseline** run **B-65** (own run, same command on the unmutated file) — `13 tests: 13 passed, 0 failed (files 1)`; exit 0; `uv pip freeze` captured as `freeze.B-65`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `13 tests: 12 passed, 1 failed (files 1)`; exit 1
- **Reddened vs that baseline** (1) — `AttachmentUploader shows the loading placeholder and neither branch while /permissions/me is pending`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `89916299c7ac220e00500bc69aea3f5279a0eb3941d1bec47130b4af2af0d100`; restored file `shasum -a 256` = `89916299c7ac220e00500bc69aea3f5279a0eb3941d1bec47130b4af2af0d100`; `cmp <scratchpad>/snap/S3-FE-04.AttachmentUploader.test.tsx frontend/src/features/infraction-management/__tests__/AttachmentUploader.test.tsx` → clean (no output).

#### `S3-FE-05`

- **File:line** `frontend/src/features/infraction-management/__tests__/uploadContract.test.tsx:295`
- **Mutation** — S3 frontend i=5 idx=138 put a forbidden upload call into the population
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '295p' <scratchpad>/snap/S3-FE-05.uploadContract.test.tsx
      expect(uploadCalls()).toHaveLength(0);
  $ sed -n '295p' frontend/src/features/infraction-management/__tests__/uploadContract.test.tsx
      expect([...uploadCalls(), "APRAS-111"]).toHaveLength(0);
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S3-FE-05.json src/features/infraction-management/__tests__/uploadContract.test.tsx`
- **Step-0 baseline** reused run **B-18** — `13 tests: 13 passed, 0 failed (files 1)`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- frontend/src/features/infraction-management/__tests__/uploadContract.test.tsx` was empty at snapshot; (b) every `cmp` since B-18 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i87`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `13 tests: 12 passed, 1 failed (files 1)`; exit 1
- **Reddened vs that baseline** (1) — `the infraction uploader's contract with POST /api/v1/uploads/photo denies the control on creation without uploads:photo_create, and posts nothing`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `b630d7449529b2c21c43ace9523647d190afde9e54d7ec92aa0f0ddba82a1f85`; restored file `shasum -a 256` = `b630d7449529b2c21c43ace9523647d190afde9e54d7ec92aa0f0ddba82a1f85`; `cmp <scratchpad>/snap/S3-FE-05.uploadContract.test.tsx frontend/src/features/infraction-management/__tests__/uploadContract.test.tsx` → clean (no output).

#### `S3-FE-06`

- **File:line** `frontend/src/features/project-management/__tests__/ConstructionTrackerPage.handlers.test.tsx:409`
- **Mutation** — S3 frontend i=6 idx=166 candidate line 410 `).toBeNull();`, mutated line 409: substitute a present element
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '409p' <scratchpad>/snap/S3-FE-06.ConstructionTrackerPage.handlers.test.tsx
        screen.queryByRole('button', { name: /Gerar relatório/i })
  $ sed -n '409p' frontend/src/features/project-management/__tests__/ConstructionTrackerPage.handlers.test.tsx
        screen.queryByRole('button', { name: /Gerar relatório/i }) ?? document.body
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S3-FE-06.json src/features/project-management/__tests__/ConstructionTrackerPage.handlers.test.tsx`
- **Step-0 baseline** run **B-66** (own run, same command on the unmutated file) — `19 tests: 19 passed, 0 failed (files 1)`; exit 0; `uv pip freeze` captured as `freeze.B-66`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `19 tests: 18 passed, 1 failed (files 1)`; exit 1
- **Reddened vs that baseline** (1) — `ConstructionTrackerPage report actions hides "Gerar relatório" without projects:read`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `7c3e35b99a2400ab6f4c49e7861a492710a57d3019245ebd42d2adacf3649dba`; restored file `shasum -a 256` = `7c3e35b99a2400ab6f4c49e7861a492710a57d3019245ebd42d2adacf3649dba`; `cmp <scratchpad>/snap/S3-FE-06.ConstructionTrackerPage.handlers.test.tsx frontend/src/features/project-management/__tests__/ConstructionTrackerPage.handlers.test.tsx` → clean (no output).

#### `S3-FE-07`

- **File:line** `frontend/src/features/purchase-management/__tests__/PurchaseRequestDetailModal.test.tsx:306`
- **Mutation** — S3 frontend i=7 idx=193 put a forbidden control into the population
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '306p' <scratchpad>/snap/S3-FE-07.PurchaseRequestDetailModal.test.tsx
      expect(screen.queryAllByTitle("Editar Orçamento")).toHaveLength(0);
  $ sed -n '306p' frontend/src/features/purchase-management/__tests__/PurchaseRequestDetailModal.test.tsx
      expect([...screen.queryAllByTitle("Editar Orçamento"), "APRAS-111"]).toHaveLength(0);
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S3-FE-07.json src/features/purchase-management/__tests__/PurchaseRequestDetailModal.test.tsx`
- **Step-0 baseline** run **B-67** (own run, same command on the unmutated file) — `17 tests: 17 passed, 0 failed (files 1)`; exit 0; `uv pip freeze` captured as `freeze.B-67`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `17 tests: 16 passed, 1 failed (files 1)`; exit 1
- **Reddened vs that baseline** (1) — `PurchaseRequestDetailModal hides quote editing once the request is decided`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `c501dc87c15cbaec115acaa8cec97f65f704a4954109f7f54785d81529b54922`; restored file `shasum -a 256` = `c501dc87c15cbaec115acaa8cec97f65f704a4954109f7f54785d81529b54922`; `cmp <scratchpad>/snap/S3-FE-07.PurchaseRequestDetailModal.test.tsx frontend/src/features/purchase-management/__tests__/PurchaseRequestDetailModal.test.tsx` → clean (no output).

#### `S3-FE-08`

- **File:line** `frontend/src/features/purchase-management/__tests__/QuoteFormModal.test.tsx:419`
- **Mutation** — S3 frontend i=8 idx=221 substitute a present element when the query finds nothing
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '419p' <scratchpad>/snap/S3-FE-08.QuoteFormModal.test.tsx
      expect(screen.queryByText(/decim/i)).not.toBeInTheDocument();
  $ sed -n '419p' frontend/src/features/purchase-management/__tests__/QuoteFormModal.test.tsx
      expect(screen.queryByText(/decim/i) ?? document.body).not.toBeInTheDocument();
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S3-FE-08.json src/features/purchase-management/__tests__/QuoteFormModal.test.tsx`
- **Step-0 baseline** reused run **B-26** — `22 tests: 22 passed, 0 failed (files 1)`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- frontend/src/features/purchase-management/__tests__/QuoteFormModal.test.tsx` was empty at snapshot; (b) every `cmp` since B-26 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i88`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `22 tests: 21 passed, 1 failed (files 1)`; exit 1
- **Reddened vs that baseline** (1) — `QuoteFormModal money input (APRAS-64, Decision 5) never lets a third decimal into a line price, typed or pasted`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `aa57403a8f4ebd87be7723f84022d458fdeadbfe33e81124f64ec2b6ff9495cb`; restored file `shasum -a 256` = `aa57403a8f4ebd87be7723f84022d458fdeadbfe33e81124f64ec2b6ff9495cb`; `cmp <scratchpad>/snap/S3-FE-08.QuoteFormModal.test.tsx frontend/src/features/purchase-management/__tests__/QuoteFormModal.test.tsx` → clean (no output).

#### `S3-FE-09`

- **File:line** `frontend/src/features/task-management/components/__tests__/CategoriesPage.test.tsx:146`
- **Mutation** — S3 frontend i=9 idx=248 substitute a present element when the query finds nothing
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '146p' <scratchpad>/snap/S3-FE-09.CategoriesPage.test.tsx
      expect(screen.queryByPlaceholderText("Nome da categoria")).not.toBeInTheDocument();
  $ sed -n '146p' frontend/src/features/task-management/components/__tests__/CategoriesPage.test.tsx
      expect(screen.queryByPlaceholderText("Nome da categoria") ?? document.body).not.toBeInTheDocument();
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S3-FE-09.json src/features/task-management/components/__tests__/CategoriesPage.test.tsx`
- **Step-0 baseline** run **B-68** (own run, same command on the unmutated file) — `27 tests: 27 passed, 0 failed (files 1)`; exit 0; `uv pip freeze` captured as `freeze.B-68`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `27 tests: 26 passed, 1 failed (files 1)`; exit 1
- **Reddened vs that baseline** (1) — `CategoriesPage hides form when cancel is clicked`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `bd1c8b4e0d956d5cdb9081b0aacf3ab0e3db6181c3bda6b879acd92457dbf708`; restored file `shasum -a 256` = `bd1c8b4e0d956d5cdb9081b0aacf3ab0e3db6181c3bda6b879acd92457dbf708`; `cmp <scratchpad>/snap/S3-FE-09.CategoriesPage.test.tsx frontend/src/features/task-management/components/__tests__/CategoriesPage.test.tsx` → clean (no output).

#### `S3-FE-10`

- **File:line** `frontend/src/features/task-management/components/__tests__/TaskCard.test.tsx:72`
- **Mutation** — S3 frontend i=10 idx=276 candidate line 73 `).not.toBeInTheDocument();`, mutated line 72: substitute a present element
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '72p' <scratchpad>/snap/S3-FE-10.TaskCard.test.tsx
        screen.queryByText(/\d{1,2}\/\d{1,2}\/\d{4}/),
  $ sed -n '72p' frontend/src/features/task-management/components/__tests__/TaskCard.test.tsx
        screen.queryByText(/\d{1,2}\/\d{1,2}\/\d{4}/) ?? document.body,
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S3-FE-10.json src/features/task-management/components/__tests__/TaskCard.test.tsx`
- **Step-0 baseline** run **B-69** (own run, same command on the unmutated file) — `25 tests: 25 passed, 0 failed (files 1)`; exit 0; `uv pip freeze` captured as `freeze.B-69`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `25 tests: 24 passed, 1 failed (files 1)`; exit 1
- **Reddened vs that baseline** (1) — `TaskCard does not render due date when it is missing`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `995e18e72c921743daf05b29d6c2962820ffa8d50947d0bd2dbf5e899ddf8b2d`; restored file `shasum -a 256` = `995e18e72c921743daf05b29d6c2962820ffa8d50947d0bd2dbf5e899ddf8b2d`; `cmp <scratchpad>/snap/S3-FE-10.TaskCard.test.tsx frontend/src/features/task-management/components/__tests__/TaskCard.test.tsx` → clean (no output).

#### `S3-FE-11`

- **File:line** `frontend/src/features/task-management/components/__tests__/TaskFilterBar.test.tsx:181`
- **Mutation** — S3 frontend i=11 idx=304 candidate line 182 `).not.toBeInTheDocument();`, mutated line 181: substitute a present element
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '181p' <scratchpad>/snap/S3-FE-11.TaskFilterBar.test.tsx
        screen.queryByRole("button", { name: /em atraso/ }),
  $ sed -n '181p' frontend/src/features/task-management/components/__tests__/TaskFilterBar.test.tsx
        screen.queryByRole("button", { name: /em atraso/ }) ?? document.body,
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S3-FE-11.json src/features/task-management/components/__tests__/TaskFilterBar.test.tsx`
- **Step-0 baseline** run **B-70** (own run, same command on the unmutated file) — `15 tests: 15 passed, 0 failed (files 1)`; exit 0; `uv pip freeze` captured as `freeze.B-70`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `15 tests: 14 passed, 1 failed (files 1)`; exit 1
- **Reddened vs that baseline** (1) — `TaskFilterBar hides the overdue counter when nothing is overdue`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `c134b51899d82ac923c3de50e33c7441080f0bed304a9498e9bdd2b905c0c2b9`; restored file `shasum -a 256` = `c134b51899d82ac923c3de50e33c7441080f0bed304a9498e9bdd2b905c0c2b9`; `cmp <scratchpad>/snap/S3-FE-11.TaskFilterBar.test.tsx frontend/src/features/task-management/components/__tests__/TaskFilterBar.test.tsx` → clean (no output).

#### `S3-FE-12`

- **File:line** `frontend/src/features/user-administration/__tests__/AcceptInvitationPage.test.tsx:254`
- **Mutation** — S3 frontend i=12 idx=331 candidate line 255 `).toBeNull();`, mutated line 254: substitute a present element
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '254p' <scratchpad>/snap/S3-FE-12.AcceptInvitationPage.test.tsx
        screen.queryByLabelText(t("acceptInvitation.newAccount.passwordLabel")),
  $ sed -n '254p' frontend/src/features/user-administration/__tests__/AcceptInvitationPage.test.tsx
        screen.queryByLabelText(t("acceptInvitation.newAccount.passwordLabel")) ?? document.body,
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S3-FE-12.json src/features/user-administration/__tests__/AcceptInvitationPage.test.tsx`
- **Step-0 baseline** run **B-71** (own run, same command on the unmutated file) — `21 tests: 21 passed, 0 failed (files 1)`; exit 0; `uv pip freeze` captured as `freeze.B-71`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `21 tests: 18 passed, 3 failed (files 1)`; exit 1
- **Reddened vs that baseline** (3) — `AcceptInvitationPage — the preview comes first renders its own terminal state and no form for a 404 preview`, `AcceptInvitationPage — the preview comes first renders its own terminal state and no form for a 409 preview`, `AcceptInvitationPage — the preview comes first renders its own terminal state and no form for a 410 preview`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `99ff11820a45818e5abb592271aa580379a80a5aa484cc17f786177528ad2f8b`; restored file `shasum -a 256` = `99ff11820a45818e5abb592271aa580379a80a5aa484cc17f786177528ad2f8b`; `cmp <scratchpad>/snap/S3-FE-12.AcceptInvitationPage.test.tsx frontend/src/features/user-administration/__tests__/AcceptInvitationPage.test.tsx` → clean (no output).

#### `S3-FE-13`

- **File:line** `frontend/src/features/user-administration/__tests__/BrandedEntryLogin.integration.test.tsx:287`
- **Mutation** — S3 frontend i=13 idx=359 substitute a present element when the query finds nothing
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '287p' <scratchpad>/snap/S3-FE-13.BrandedEntryLogin.integration.test.tsx
      expect(screen.queryByText(/404/)).toBeNull();
  $ sed -n '287p' frontend/src/features/user-administration/__tests__/BrandedEntryLogin.integration.test.tsx
      expect(screen.queryByText(/404/) ?? document.body).toBeNull();
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S3-FE-13.json src/features/user-administration/__tests__/BrandedEntryLogin.integration.test.tsx`
- **Step-0 baseline** reused run **B-41** — `3 tests: 3 passed, 0 failed (files 1)`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- frontend/src/features/user-administration/__tests__/BrandedEntryLogin.integration.test.tsx` was empty at snapshot; (b) every `cmp` since B-41 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i89`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `3 tests: 2 passed, 1 failed (files 1)`; exit 1
- **Reddened vs that baseline** (1) — `anonymous login at /c/<slug> (real providers) shows the no-access panel to an anonymous non-member, with no navigation`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `ff344e2ce8c829143f38f60742c1bad036c475b2ecb9b996ce6558d1bb0e18b7`; restored file `shasum -a 256` = `ff344e2ce8c829143f38f60742c1bad036c475b2ecb9b996ce6558d1bb0e18b7`; `cmp <scratchpad>/snap/S3-FE-13.BrandedEntryLogin.integration.test.tsx frontend/src/features/user-administration/__tests__/BrandedEntryLogin.integration.test.tsx` → clean (no output).

#### `S3-FE-14`

- **File:line** `frontend/src/features/user-administration/__tests__/Navbar.modules.test.tsx:165`
- **Mutation** — S3 frontend i=14 idx=386 substitute a present element when the query finds nothing
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '165p' <scratchpad>/snap/S3-FE-14.Navbar.modules.test.tsx
      expect(screen.queryByText(t("nav.subscription"))).toBeNull();
  $ sed -n '165p' frontend/src/features/user-administration/__tests__/Navbar.modules.test.tsx
      expect(screen.queryByText(t("nav.subscription")) ?? document.body).toBeNull();
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S3-FE-14.json src/features/user-administration/__tests__/Navbar.modules.test.tsx`
- **Step-0 baseline** run **B-72** (own run, same command on the unmutated file) — `5 tests: 5 passed, 0 failed (files 1)`; exit 0; `uv pip freeze` captured as `freeze.B-72`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `5 tests: 4 passed, 1 failed (files 1)`; exit 1
- **Reddened vs that baseline** (1) — `Navbar and a disabled module shows the /subscription link to a billing:read holder and hides it otherwise`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `fb65d2465be2a14541ebe935b12dc0af1a242e119578ea2eba691c1b4c5ee19c`; restored file `shasum -a 256` = `fb65d2465be2a14541ebe935b12dc0af1a242e119578ea2eba691c1b4c5ee19c`; `cmp <scratchpad>/snap/S3-FE-14.Navbar.modules.test.tsx frontend/src/features/user-administration/__tests__/Navbar.modules.test.tsx` → clean (no output).

#### `S3-FE-15`

- **File:line** `frontend/src/features/user-administration/__tests__/Navbar.test.tsx:656`
- **Mutation** — S3 frontend i=15 idx=414 substitute a present element when the query finds nothing
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '656p' <scratchpad>/snap/S3-FE-15.Navbar.test.tsx
      expect(screen.queryByText("Informações de Contato")).toBeNull();
  $ sed -n '656p' frontend/src/features/user-administration/__tests__/Navbar.test.tsx
      expect(screen.queryByText("Informações de Contato") ?? document.body).toBeNull();
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S3-FE-15.json src/features/user-administration/__tests__/Navbar.test.tsx`
- **Step-0 baseline** run **B-73** (own run, same command on the unmutated file) — `30 tests: 30 passed, 0 failed (files 1)`; exit 0; `uv pip freeze` captured as `freeze.B-73`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `30 tests: 29 passed, 1 failed (files 1)`; exit 1
- **Reddened vs that baseline** (1) — `Navbar shows PORTEIRO the links its permissions allow and no administration`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `c776c1e8762a426dcfd695426dabef13818a1a09bef642c94ac740e56895a89b`; restored file `shasum -a 256` = `c776c1e8762a426dcfd695426dabef13818a1a09bef642c94ac740e56895a89b`; `cmp <scratchpad>/snap/S3-FE-15.Navbar.test.tsx frontend/src/features/user-administration/__tests__/Navbar.test.tsx` → clean (no output).

#### `S3-FE-16`

- **File:line** `frontend/src/features/user-administration/__tests__/ProtectedRoute.test.tsx:292`
- **Mutation** — S3 frontend i=16 idx=441 substitute a present element when the query finds nothing
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '292p' <scratchpad>/snap/S3-FE-16.ProtectedRoute.test.tsx
      expect(screen.queryByText("Tasks Content")).toBeNull();
  $ sed -n '292p' frontend/src/features/user-administration/__tests__/ProtectedRoute.test.tsx
      expect(screen.queryByText("Tasks Content") ?? document.body).toBeNull();
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S3-FE-16.json src/features/user-administration/__tests__/ProtectedRoute.test.tsx`
- **Step-0 baseline** run **B-74** (own run, same command on the unmutated file) — `10 tests: 10 passed, 0 failed (files 1)`; exit 0; `uv pip freeze` captured as `freeze.B-74`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `10 tests: 9 passed, 1 failed (files 1)`; exit 1
- **Reddened vs that baseline** (1) — `ProtectedRoute renders the restricted-access message (no redirect) when the permission is absent`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `321c691c613e12501f9b9fe2f99da7baad5305f2f1ba324a6ad032056776a105`; restored file `shasum -a 256` = `321c691c613e12501f9b9fe2f99da7baad5305f2f1ba324a6ad032056776a105`; `cmp <scratchpad>/snap/S3-FE-16.ProtectedRoute.test.tsx frontend/src/features/user-administration/__tests__/ProtectedRoute.test.tsx` → clean (no output).

#### `S3-FE-17`

- **File:line** `frontend/src/features/user-administration/__tests__/Sidebar.test.tsx:294`
- **Mutation** — S3 frontend i=17 idx=469 substitute a present element when the query finds nothing
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '294p' <scratchpad>/snap/S3-FE-17.Sidebar.test.tsx
      expect(screen.queryByRole("button", { name: "Fechar" })).toBeNull();
  $ sed -n '294p' frontend/src/features/user-administration/__tests__/Sidebar.test.tsx
      expect(screen.queryByRole("button", { name: "Fechar" }) ?? document.body).toBeNull();
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S3-FE-17.json src/features/user-administration/__tests__/Sidebar.test.tsx`
- **Step-0 baseline** run **B-75** (own run, same command on the unmutated file) — `10 tests: 10 passed, 0 failed (files 1)`; exit 0; `uv pip freeze` captured as `freeze.B-75`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `10 tests: 9 passed, 1 failed (files 1)`; exit 1
- **Reddened vs that baseline** (1) — `Sidebar component handles mobile off-canvas drawer closing on link click`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `d5e699382d6032385a1279817a0bad5b5fc44bc18acdacb2a557bb2abd7da25e`; restored file `shasum -a 256` = `d5e699382d6032385a1279817a0bad5b5fc44bc18acdacb2a557bb2abd7da25e`; `cmp <scratchpad>/snap/S3-FE-17.Sidebar.test.tsx frontend/src/features/user-administration/__tests__/Sidebar.test.tsx` → clean (no output).

#### `S3-FE-18`

- **File:line** `frontend/src/features/user-administration/__tests__/TenantProfilePage.brand.test.tsx:971`
- **Mutation** — S3 frontend i=18 idx=496 substitute a present element when the query finds nothing
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '971p' <scratchpad>/snap/S3-FE-18.TenantProfilePage.brand.test.tsx
      expect(screen.queryByTestId("brand-paste-dialog")).not.toBeInTheDocument();
  $ sed -n '971p' frontend/src/features/user-administration/__tests__/TenantProfilePage.brand.test.tsx
      expect(screen.queryByTestId("brand-paste-dialog") ?? document.body).not.toBeInTheDocument();
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S3-FE-18.json src/features/user-administration/__tests__/TenantProfilePage.brand.test.tsx`
- **Step-0 baseline** reused run **B-43** — `44 tests: 44 passed, 0 failed (files 1)`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- frontend/src/features/user-administration/__tests__/TenantProfilePage.brand.test.tsx` was empty at snapshot; (b) every `cmp` since B-43 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i90`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `44 tests: 43 passed, 1 failed (files 1)`; exit 1
- **Reddened vs that baseline** (1) — `pasting an advanced palette keeps an applied palette when Escape closes the dialog`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `0f80cdff16087d9c46bf49b3a2efe40d0039b56d3a2a9082a913cbf353d047ad`; restored file `shasum -a 256` = `0f80cdff16087d9c46bf49b3a2efe40d0039b56d3a2a9082a913cbf353d047ad`; `cmp <scratchpad>/snap/S3-FE-18.TenantProfilePage.brand.test.tsx frontend/src/features/user-administration/__tests__/TenantProfilePage.brand.test.tsx` → clean (no output).

#### `S3-FE-19`

- **File:line** `frontend/src/features/user-administration/__tests__/TenantsAdminPage.test.tsx:168`
- **Mutation** — S3 frontend i=19 idx=524 substitute a present element when the query finds nothing
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '168p' <scratchpad>/snap/S3-FE-19.TenantsAdminPage.test.tsx
      expect(screen.queryByTestId(`tenant-row-${AGUAS.id}`)).toBeNull();
  $ sed -n '168p' frontend/src/features/user-administration/__tests__/TenantsAdminPage.test.tsx
      expect(screen.queryByTestId(`tenant-row-${AGUAS.id}`) ?? document.body).toBeNull();
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S3-FE-19.json src/features/user-administration/__tests__/TenantsAdminPage.test.tsx`
- **Step-0 baseline** run **B-76** (own run, same command on the unmutated file) — `12 tests: 12 passed, 0 failed (files 1)`; exit 0; `uv pip freeze` captured as `freeze.B-76`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `12 tests: 11 passed, 1 failed (files 1)`; exit 1
- **Reddened vs that baseline** (1) — `TenantsAdminPage list filters by name and by slug, and narrows by status`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `447bddffa9aef2d3b5521ffabf001fcee17c0e4b68db1578e3b281ef15b99c53`; restored file `shasum -a 256` = `447bddffa9aef2d3b5521ffabf001fcee17c0e4b68db1578e3b281ef15b99c53`; `cmp <scratchpad>/snap/S3-FE-19.TenantsAdminPage.test.tsx frontend/src/features/user-administration/__tests__/TenantsAdminPage.test.tsx` → clean (no output).

#### `S3-FE-20`

- **File:line** `frontend/src/lib/__tests__/contrast.test.ts:292`
- **Mutation** — S3 frontend i=20 idx=551 make the forbidden value (null) the asserted one, after evaluating the real call
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '292p' <scratchpad>/snap/S3-FE-20.contrast.test.ts
      expect(parseOklch(scheme.muted)).not.toBeNull();
  $ sed -n '292p' frontend/src/lib/__tests__/contrast.test.ts
      expect(((parseOklch(scheme.muted)), null)).not.toBeNull();
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S3-FE-20.json src/lib/__tests__/contrast.test.ts`
- **Step-0 baseline** reused run **B-15** — `36 tests: 36 passed, 0 failed (files 1)`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- frontend/src/lib/__tests__/contrast.test.ts` was empty at snapshot; (b) every `cmp` since B-15 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i91`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `36 tests: 35 passed, 1 failed (files 1)`; exit 1
- **Reddened vs that baseline** (1) — `hexPaletteToScheme emits the same oklch strings the backend does, at 2dp`
- **Case under examination** the case named by the candidate (above); it is the case listed under *Reddened* for this row.
- **Was it among the reddened?** yes
- **Step-5 restore** pristine copy `shasum -a 256` = `e54b1aaecb01c23328daa780701ad96eee93685e19d2e9309532d48ae1389a6a`; restored file `shasum -a 256` = `e54b1aaecb01c23328daa780701ad96eee93685e19d2e9309532d48ae1389a6a`; `cmp <scratchpad>/snap/S3-FE-20.contrast.test.ts frontend/src/lib/__tests__/contrast.test.ts` → clean (no output).

#### `S4-FE-01`

- **File:line** `frontend/src/api/client.ts:9`
- **Mutation** — S4 i=1 idx=5 candidate src/api/__tests__/finance.test.ts:5 vi.mock("../client") -- break the real module: make constructing the real axios client throw
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '9p' <scratchpad>/snap/S4-FE-01.client.ts
  const apiClient = axios.create({
  $ sed -n '9p' frontend/src/api/client.ts
  const apiClient = (() => { throw new Error("APRAS-111 mutation: the real client module was evaluated"); })() as never || axios.create({
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S4-FE-01.json src/api/__tests__/finance.test.ts`
- **Step-0 baseline** run **B-77** (own run, same command on the unmutated file) — `22 tests: 22 passed, 0 failed (files 1)`; exit 0; `uv pip freeze` captured as `freeze.B-77`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `22 tests: 22 passed, 0 failed (files 1)`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `the mocked specifier's own behaviour, as named in the spec's titles`
- **Was it among the reddened?** no — expected: the specifier is replaced by `vi.mock`, so the real module is never reached. Adjudicated in Findings / Examined and kept per candidate
- **Step-5 restore** pristine copy `shasum -a 256` = `ee2013061fc1b67a44bc58b9ebd4d0544327da1ce74f7564e04e845caa60c740`; restored file `shasum -a 256` = `ee2013061fc1b67a44bc58b9ebd4d0544327da1ce74f7564e04e845caa60c740`; `cmp <scratchpad>/snap/S4-FE-01.client.ts frontend/src/api/client.ts` → clean (no output).

#### `S4-FE-02`

- **File:line** `frontend/src/api/client.ts:9`
- **Mutation** — S4 i=2 idx=9 candidate src/api/__tests__/packages.test.ts:5 vi.mock("../client") -- break the real module: make constructing the real axios client throw
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '9p' <scratchpad>/snap/S4-FE-02.client.ts
  const apiClient = axios.create({
  $ sed -n '9p' frontend/src/api/client.ts
  const apiClient = (() => { throw new Error("APRAS-111 mutation: the real client module was evaluated"); })() as never || axios.create({
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S4-FE-02.json src/api/__tests__/packages.test.ts`
- **Step-0 baseline** run **B-78** (own run, same command on the unmutated file) — `7 tests: 7 passed, 0 failed (files 1)`; exit 0; `uv pip freeze` captured as `freeze.B-78`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `7 tests: 7 passed, 0 failed (files 1)`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `the mocked specifier's own behaviour, as named in the spec's titles`
- **Was it among the reddened?** no — expected: the specifier is replaced by `vi.mock`, so the real module is never reached. Adjudicated in Findings / Examined and kept per candidate
- **Step-5 restore** pristine copy `shasum -a 256` = `ee2013061fc1b67a44bc58b9ebd4d0544327da1ce74f7564e04e845caa60c740`; restored file `shasum -a 256` = `ee2013061fc1b67a44bc58b9ebd4d0544327da1ce74f7564e04e845caa60c740`; `cmp <scratchpad>/snap/S4-FE-02.client.ts frontend/src/api/client.ts` → clean (no output).

#### `S4-FE-03`

- **File:line** `frontend/src/api/client.ts:9`
- **Mutation** — S4 i=3 idx=14 candidate src/api/__tests__/residents.test.ts:5 vi.mock("../client") -- break the real module: make constructing the real axios client throw
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '9p' <scratchpad>/snap/S4-FE-03.client.ts
  const apiClient = axios.create({
  $ sed -n '9p' frontend/src/api/client.ts
  const apiClient = (() => { throw new Error("APRAS-111 mutation: the real client module was evaluated"); })() as never || axios.create({
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S4-FE-03.json src/api/__tests__/residents.test.ts`
- **Step-0 baseline** run **B-79** (own run, same command on the unmutated file) — `8 tests: 8 passed, 0 failed (files 1)`; exit 0; `uv pip freeze` captured as `freeze.B-79`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `8 tests: 8 passed, 0 failed (files 1)`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `the mocked specifier's own behaviour, as named in the spec's titles`
- **Was it among the reddened?** no — expected: the specifier is replaced by `vi.mock`, so the real module is never reached. Adjudicated in Findings / Examined and kept per candidate
- **Step-5 restore** pristine copy `shasum -a 256` = `ee2013061fc1b67a44bc58b9ebd4d0544327da1ce74f7564e04e845caa60c740`; restored file `shasum -a 256` = `ee2013061fc1b67a44bc58b9ebd4d0544327da1ce74f7564e04e845caa60c740`; `cmp <scratchpad>/snap/S4-FE-03.client.ts frontend/src/api/client.ts` → clean (no output).

#### `S4-FE-04` — **INVALIDATED RUN, MEASURED NOTHING**

> **!! INVALIDATED — THIS ROW IS NOT AN ADJUDICATION. IT MEASURED NOTHING.**
> The mutation replaced `frontend/src/api/accessControl.ts:22`, the opening line of a
> multi-line call, which left the file syntactically invalid. The run therefore
> **collected 0 cases** (`0 tests: 0 passed, 0 failed (files 1)`, exit 1) and
> could not have reddened anything: there was nothing green to turn red. This row
> is **not** evidence for or against any finding, supports **no** class, and is
> **not** counted toward S4's budget of 10 (the valid rows carry that floor — see
> *Strata, enumeration, budgets, strides, remainder* and EK-15). The mutation that
> actually measured this candidate is **`S4-FE-04r`** below, which breaks
> `listDevices` at its `return` instead. It is kept here, beside its re-run,
> because deleting a failed attempt would hide a window in which
> `frontend/src/api/accessControl.ts` was briefly invalid, and because the
> re-run's line number is only explicable with it. **A row that collected nothing
> looks, in a summary, exactly like a row whose mutation nothing caught** — that
> is this audit's own F-class reasoning, and this banner is here so the two cannot
> be confused in this ledger either.

- **File:line** `frontend/src/api/accessControl.ts:22`
- **Mutation** — S4 i=4 idx=18 candidate src/features/access-control/__tests__/AccessControlPage.test.tsx:7 vi.mock("../../../api/accessControl") -- break the real module: make listDevices throw before it reaches the client
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '22p' <scratchpad>/snap/S4-FE-04.accessControl.ts
    const response = await apiClient.get<PaginatedAccessDeviceRead>(
  $ sed -n '22p' frontend/src/api/accessControl.ts
    throw new Error("APRAS-111 mutation: the real module was exercised");
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S4-FE-04.json src/features/access-control/__tests__/AccessControlPage.test.tsx`
- **Step-0 baseline** run **B-80** (own run, same command on the unmutated file) — `4 tests: 4 passed, 0 failed (files 1)`; exit 0; `uv pip freeze` captured as `freeze.B-80`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `0 tests: 0 passed, 0 failed (files 1)`; exit 1 — **the file did not parse, so no case ran**
- **Reddened vs that baseline** **not measurable.** Not "none": every one of the baseline's cases went from *passing* to *not collected*, which is neither green nor reddened. There is no pass/fail set here to subtract the step-0 set from, so no case can be said to have reddened or to have stayed green.
- **Case under examination** none was examined by this run
- **Was it among the reddened?** **question does not apply — invalidated run.** The candidate's verdict comes from the re-run named in the banner above, not from this row. Nothing here is carried into *Findings*, *Over-pins* or *Examined and kept*.
- **Step-5 restore** pristine copy `shasum -a 256` = `38e5ced847d4d02e297456b98cc5148e9b173d17580a5b95235f890ce8918e96`; restored file `shasum -a 256` = `38e5ced847d4d02e297456b98cc5148e9b173d17580a5b95235f890ce8918e96`; `cmp <scratchpad>/snap/S4-FE-04.accessControl.ts frontend/src/api/accessControl.ts` → clean (no output).

#### `S4-FE-05`

- **File:line** `frontend/src/api/documents.ts:15`
- **Mutation** — S4 i=5 idx=22 candidate src/features/document-management/__tests__/DocumentCenter.test.tsx:27 vi.mock("../../../api/documents") -- break the real module: make getDocumentFolders throw before it reaches the client
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '15p' <scratchpad>/snap/S4-FE-05.documents.ts
    const response = await apiClient.get<DocumentFolderTree[]>("/documents/folders");
  $ sed -n '15p' frontend/src/api/documents.ts
    throw new Error("APRAS-111 mutation: the real module was exercised");
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S4-FE-05.json src/features/document-management/__tests__/DocumentCenter.test.tsx`
- **Step-0 baseline** run **B-81** (own run, same command on the unmutated file) — `7 tests: 7 passed, 0 failed (files 1)`; exit 0; `uv pip freeze` captured as `freeze.B-81`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `7 tests: 7 passed, 0 failed (files 1)`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `the mocked specifier's own behaviour, as named in the spec's titles`
- **Was it among the reddened?** no — expected: the specifier is replaced by `vi.mock`, so the real module is never reached. Adjudicated in Findings / Examined and kept per candidate
- **Step-5 restore** pristine copy `shasum -a 256` = `5ed2f77f5746becd0525a4df7254caead5954bdede0440c7cf3f17bffc929058`; restored file `shasum -a 256` = `5ed2f77f5746becd0525a4df7254caead5954bdede0440c7cf3f17bffc929058`; `cmp <scratchpad>/snap/S4-FE-05.documents.ts frontend/src/api/documents.ts` → clean (no output).

#### `S4-FE-06`

- **File:line** `frontend/src/api/infractions.ts:30`
- **Mutation** — S4 i=6 idx=27 candidate src/features/infraction-management/__tests__/Infractions.test.tsx:27 vi.mock("../../../api/infractions") -- break the real module: make getInfractionRules throw before it reaches the client
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '30p' <scratchpad>/snap/S4-FE-06.infractions.ts
    const response = await apiClient.get<InfractionRule[]>("/infraction-rules");
  $ sed -n '30p' frontend/src/api/infractions.ts
    throw new Error("APRAS-111 mutation: the real module was exercised");
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S4-FE-06.json src/features/infraction-management/__tests__/Infractions.test.tsx`
- **Step-0 baseline** run **B-82** (own run, same command on the unmutated file) — `23 tests: 23 passed, 0 failed (files 1)`; exit 0; `uv pip freeze` captured as `freeze.B-82`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `23 tests: 23 passed, 0 failed (files 1)`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `the mocked specifier's own behaviour, as named in the spec's titles`
- **Was it among the reddened?** no — expected: the specifier is replaced by `vi.mock`, so the real module is never reached. Adjudicated in Findings / Examined and kept per candidate
- **Step-5 restore** pristine copy `shasum -a 256` = `51561a3adc873be03b54de7cb2a2517853e0c956661e1ce2a57f71bbba6052e8`; restored file `shasum -a 256` = `51561a3adc873be03b54de7cb2a2517853e0c956661e1ce2a57f71bbba6052e8`; `cmp <scratchpad>/snap/S4-FE-06.infractions.ts frontend/src/api/infractions.ts` → clean (no output).

#### `S4-FE-07`

- **File:line** `frontend/src/api/lots.ts:19`
- **Mutation** — S4 i=7 idx=31 candidate src/features/lot-management/__tests__/LotsPage.test.tsx:41 vi.mock("../../../api/lots") -- break the real module: make getLots throw before it reaches the client
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '19p' <scratchpad>/snap/S4-FE-07.lots.ts
    const response = await apiClient.get<PaginatedLotRead>("/lots/", { params });
  $ sed -n '19p' frontend/src/api/lots.ts
    throw new Error("APRAS-111 mutation: the real module was exercised");
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S4-FE-07.json src/features/lot-management/__tests__/LotsPage.test.tsx`
- **Step-0 baseline** run **B-83** (own run, same command on the unmutated file) — `7 tests: 7 passed, 0 failed (files 1)`; exit 0; `uv pip freeze` captured as `freeze.B-83`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `7 tests: 7 passed, 0 failed (files 1)`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `the mocked specifier's own behaviour, as named in the spec's titles`
- **Was it among the reddened?** no — expected: the specifier is replaced by `vi.mock`, so the real module is never reached. Adjudicated in Findings / Examined and kept per candidate
- **Step-5 restore** pristine copy `shasum -a 256` = `bebcff27af3107847cba7af2943defabd10e5eadfe3ac622deda5f7db315b24a`; restored file `shasum -a 256` = `bebcff27af3107847cba7af2943defabd10e5eadfe3ac622deda5f7db315b24a`; `cmp <scratchpad>/snap/S4-FE-07.lots.ts frontend/src/api/lots.ts` → clean (no output).

#### `S4-FE-08` — **INVALIDATED RUN, MEASURED NOTHING**

> **!! INVALIDATED — THIS ROW IS NOT AN ADJUDICATION. IT MEASURED NOTHING.**
> The mutation replaced `frontend/src/api/purchases.ts:66`, the opening line of a
> multi-line call, which left the file syntactically invalid. The run therefore
> **collected 0 cases** (`0 tests: 0 passed, 0 failed (files 1)`, exit 1) and
> could not have reddened anything: there was nothing green to turn red. This row
> is **not** evidence for or against any finding, supports **no** class, and is
> **not** counted toward S4's budget of 10 (the valid rows carry that floor — see
> *Strata, enumeration, budgets, strides, remainder* and EK-15). The mutation that
> actually measured this candidate is **`S4-FE-08r`** below, which breaks
> `getPurchaseRequestById` at its `return` instead. It is kept here, beside its re-run,
> because deleting a failed attempt would hide a window in which
> `frontend/src/api/purchases.ts` was briefly invalid, and because the
> re-run's line number is only explicable with it. **A row that collected nothing
> looks, in a summary, exactly like a row whose mutation nothing caught** — that
> is this audit's own F-class reasoning, and this banner is here so the two cannot
> be confused in this ledger either.

- **File:line** `frontend/src/api/purchases.ts:66`
- **Mutation** — S4 i=8 idx=36 candidate src/features/purchase-management/__tests__/PurchaseRequestDetailModal.test.tsx:26 vi.mock("../../../api/purchases") -- break the real module: make getPurchaseRequestById throw before it reaches the client
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '66p' <scratchpad>/snap/S4-FE-08.purchases.ts
    const response = await apiClient.get<PurchaseRequestDetail>(
  $ sed -n '66p' frontend/src/api/purchases.ts
    throw new Error("APRAS-111 mutation: the real module was exercised");
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S4-FE-08.json src/features/purchase-management/__tests__/PurchaseRequestDetailModal.test.tsx`
- **Step-0 baseline** reused run **B-67** — `17 tests: 17 passed, 0 failed (files 1)`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- frontend/src/api/purchases.ts` was empty at snapshot; (b) every `cmp` since B-67 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i92`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `0 tests: 0 passed, 0 failed (files 1)`; exit 1 — **the file did not parse, so no case ran**
- **Reddened vs that baseline** **not measurable.** Not "none": every one of the baseline's cases went from *passing* to *not collected*, which is neither green nor reddened. There is no pass/fail set here to subtract the step-0 set from, so no case can be said to have reddened or to have stayed green.
- **Case under examination** none was examined by this run
- **Was it among the reddened?** **question does not apply — invalidated run.** The candidate's verdict comes from the re-run named in the banner above, not from this row. Nothing here is carried into *Findings*, *Over-pins* or *Examined and kept*.
- **Step-5 restore** pristine copy `shasum -a 256` = `12d1035f58d9161391e1d444d5218589a9d5abf144dc640825e5b93a50e8433e`; restored file `shasum -a 256` = `12d1035f58d9161391e1d444d5218589a9d5abf144dc640825e5b93a50e8433e`; `cmp <scratchpad>/snap/S4-FE-08.purchases.ts frontend/src/api/purchases.ts` → clean (no output).

#### `S4-FE-09`

- **File:line** `frontend/src/api/client.ts:9`
- **Mutation** — S4 i=9 idx=40 candidate src/features/user-administration/__tests__/TenantProfilePage.brand.test.tsx:28 vi.mock("../../../api/client") -- break the real module: make constructing the real axios client throw
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '9p' <scratchpad>/snap/S4-FE-09.client.ts
  const apiClient = axios.create({
  $ sed -n '9p' frontend/src/api/client.ts
  const apiClient = (() => { throw new Error("APRAS-111 mutation: the real client module was evaluated"); })() as never || axios.create({
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S4-FE-09.json src/features/user-administration/__tests__/TenantProfilePage.brand.test.tsx`
- **Step-0 baseline** reused run **B-43** — `44 tests: 44 passed, 0 failed (files 1)`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- frontend/src/api/client.ts` was empty at snapshot; (b) every `cmp` since B-43 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i93`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `44 tests: 44 passed, 0 failed (files 1)`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `the mocked specifier's own behaviour, as named in the spec's titles`
- **Was it among the reddened?** no — expected: the specifier is replaced by `vi.mock`, so the real module is never reached. Adjudicated in Findings / Examined and kept per candidate
- **Step-5 restore** pristine copy `shasum -a 256` = `ee2013061fc1b67a44bc58b9ebd4d0544327da1ce74f7564e04e845caa60c740`; restored file `shasum -a 256` = `ee2013061fc1b67a44bc58b9ebd4d0544327da1ce74f7564e04e845caa60c740`; `cmp <scratchpad>/snap/S4-FE-09.client.ts frontend/src/api/client.ts` → clean (no output).

#### `S4-FE-10` — **INVALIDATED RUN, MEASURED NOTHING**

> **!! INVALIDATED — THIS ROW IS NOT AN ADJUDICATION. IT MEASURED NOTHING.**
> The mutation replaced `frontend/src/api/visitors.ts:21`, the opening line of a
> multi-line call, which left the file syntactically invalid. The run therefore
> **collected 0 cases** (`0 tests: 0 passed, 0 failed (files 1)`, exit 1) and
> could not have reddened anything: there was nothing green to turn red. This row
> is **not** evidence for or against any finding, supports **no** class, and is
> **not** counted toward S4's budget of 10 (the valid rows carry that floor — see
> *Strata, enumeration, budgets, strides, remainder* and EK-15). The mutation that
> actually measured this candidate is **`S4-FE-10r`** below, which breaks
> `searchVisitors` at its `return` instead. It is kept here, beside its re-run,
> because deleting a failed attempt would hide a window in which
> `frontend/src/api/visitors.ts` was briefly invalid, and because the
> re-run's line number is only explicable with it. **A row that collected nothing
> looks, in a summary, exactly like a row whose mutation nothing caught** — that
> is this audit's own F-class reasoning, and this banner is here so the two cannot
> be confused in this ledger either.

- **File:line** `frontend/src/api/visitors.ts:21`
- **Mutation** — S4 i=10 idx=44 candidate src/features/visitor-management/__tests__/useVisitors.test.tsx:8 vi.mock("../../../api/visitors") -- break the real module: make searchVisitors throw before it reaches the client
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '21p' <scratchpad>/snap/S4-FE-10.visitors.ts
    const response = await apiClient.get<PaginatedVisitorRead>("/visitors", {
  $ sed -n '21p' frontend/src/api/visitors.ts
    throw new Error("APRAS-111 mutation: the real module was exercised");
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S4-FE-10.json src/features/visitor-management/__tests__/useVisitors.test.tsx`
- **Step-0 baseline** run **B-84** (own run, same command on the unmutated file) — `9 tests: 9 passed, 0 failed (files 1)`; exit 0; `uv pip freeze` captured as `freeze.B-84`, `shasum -a 256` = `cb629948d2092d3edaa2ff115c6743f37d5c83191e12c91ac6485b31796e6e75`.
- **Step-3 mutated run** — `0 tests: 0 passed, 0 failed (files 1)`; exit 1 — **the file did not parse, so no case ran**
- **Reddened vs that baseline** **not measurable.** Not "none": every one of the baseline's cases went from *passing* to *not collected*, which is neither green nor reddened. There is no pass/fail set here to subtract the step-0 set from, so no case can be said to have reddened or to have stayed green.
- **Case under examination** none was examined by this run
- **Was it among the reddened?** **question does not apply — invalidated run.** The candidate's verdict comes from the re-run named in the banner above, not from this row. Nothing here is carried into *Findings*, *Over-pins* or *Examined and kept*.
- **Step-5 restore** pristine copy `shasum -a 256` = `47ac72a0505ff48e6e11f2162b5705f4133fe683436a4fe619a8cd46168caddf`; restored file `shasum -a 256` = `47ac72a0505ff48e6e11f2162b5705f4133fe683436a4fe619a8cd46168caddf`; `cmp <scratchpad>/snap/S4-FE-10.visitors.ts frontend/src/api/visitors.ts` → clean (no output).

#### `S4-FE-04r`

- **File:line** `frontend/src/api/accessControl.ts:25`
- **Mutation** — S4 i=4 idx=18 RE-RUN (the first attempt replaced line 22, the opening line of a multi-line call, which left the file syntactically invalid: 0 tests collected, exit 1 -- that run measured nothing and is recorded as invalidated). Break listDevices at its return instead.
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '25p' <scratchpad>/snap/S4-FE-04r.accessControl.ts
    return response.data;
  $ sed -n '25p' frontend/src/api/accessControl.ts
    throw new Error("APRAS-111 mutation: the real module was exercised");
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S4-FE-04r.json src/features/access-control/__tests__/AccessControlPage.test.tsx`
- **Step-0 baseline** reused run **B-80** — `4 tests: 4 passed, 0 failed (files 1)`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- frontend/src/api/accessControl.ts` was empty at snapshot; (b) every `cmp` since B-80 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i94`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `4 tests: 4 passed, 0 failed (files 1)`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `the mocked specifier's own behaviour, as named in the spec's titles`
- **Was it among the reddened?** no — expected: the specifier is replaced by `vi.mock`, so the real module is never reached. Adjudicated in Findings / Examined and kept per candidate
- **Step-5 restore** pristine copy `shasum -a 256` = `38e5ced847d4d02e297456b98cc5148e9b173d17580a5b95235f890ce8918e96`; restored file `shasum -a 256` = `38e5ced847d4d02e297456b98cc5148e9b173d17580a5b95235f890ce8918e96`; `cmp <scratchpad>/snap/S4-FE-04r.accessControl.ts frontend/src/api/accessControl.ts` → clean (no output).

#### `S4-FE-08r`

- **File:line** `frontend/src/api/purchases.ts:69`
- **Mutation** — S4 i=8 idx=36 RE-RUN (first attempt at line 66 left the file syntactically invalid: 0 tests collected, exit 1, invalidated). Break getPurchaseRequestById at its return instead.
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '69p' <scratchpad>/snap/S4-FE-08r.purchases.ts
    return response.data;
  $ sed -n '69p' frontend/src/api/purchases.ts
    throw new Error("APRAS-111 mutation: the real module was exercised");
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S4-FE-08r.json src/features/purchase-management/__tests__/PurchaseRequestDetailModal.test.tsx`
- **Step-0 baseline** reused run **B-67** — `17 tests: 17 passed, 0 failed (files 1)`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- frontend/src/api/purchases.ts` was empty at snapshot; (b) every `cmp` since B-67 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i95`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `17 tests: 17 passed, 0 failed (files 1)`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `the mocked specifier's own behaviour, as named in the spec's titles`
- **Was it among the reddened?** no — expected: the specifier is replaced by `vi.mock`, so the real module is never reached. Adjudicated in Findings / Examined and kept per candidate
- **Step-5 restore** pristine copy `shasum -a 256` = `12d1035f58d9161391e1d444d5218589a9d5abf144dc640825e5b93a50e8433e`; restored file `shasum -a 256` = `12d1035f58d9161391e1d444d5218589a9d5abf144dc640825e5b93a50e8433e`; `cmp <scratchpad>/snap/S4-FE-08r.purchases.ts frontend/src/api/purchases.ts` → clean (no output).

#### `S4-FE-10r`

- **File:line** `frontend/src/api/visitors.ts:24`
- **Mutation** — S4 i=10 idx=44 RE-RUN (first attempt at line 21 left the file syntactically invalid: 0 tests collected, exit 1, invalidated). Break searchVisitors at its return instead.
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '24p' <scratchpad>/snap/S4-FE-10r.visitors.ts
    return response.data;
  $ sed -n '24p' frontend/src/api/visitors.ts
    throw new Error("APRAS-111 mutation: the real module was exercised");
  ```
- **Order-pinned command** `cd frontend && npx vitest run --reporter=json --outputFile=<scratchpad>/runs/S4-FE-10r.json src/features/visitor-management/__tests__/useVisitors.test.tsx`
- **Step-0 baseline** reused run **B-84** — `9 tests: 9 passed, 0 failed (files 1)`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- frontend/src/api/visitors.ts` was empty at snapshot; (b) every `cmp` since B-84 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i96`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `9 tests: 9 passed, 0 failed (files 1)`; exit 0
- **Reddened vs that baseline** none
- **Case under examination** `the mocked specifier's own behaviour, as named in the spec's titles`
- **Was it among the reddened?** no — expected: the specifier is replaced by `vi.mock`, so the real module is never reached. Adjudicated in Findings / Examined and kept per candidate
- **Step-5 restore** pristine copy `shasum -a 256` = `47ac72a0505ff48e6e11f2162b5705f4133fe683436a4fe619a8cd46168caddf`; restored file `shasum -a 256` = `47ac72a0505ff48e6e11f2162b5705f4133fe683436a4fe619a8cd46168caddf`; `cmp <scratchpad>/snap/S4-FE-10r.visitors.ts frontend/src/api/visitors.ts` → clean (no output).

#### `S2-MAND-BE-branding-b`

- **File:line** `backend/app/core/branding.py:168`
- **Mutation** — S2 mandatory module backend/tests/test_branding.py -- complementary direction: the first mutation (0.96 -> 0.90) reddened three neighbours but NOT test_primary_text_clears_aa_on_every_text_surface_over_the_lattice, the case whose docstring claims to be what alarms when _LIGHT_ACCENT_LIGHTNESS moves. 0.99 moves it the other way (a lighter accent, lower contrast).
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '168p' <scratchpad>/snap/S2-MAND-BE-branding-b.branding.py
  _LIGHT_ACCENT_LIGHTNESS = 0.96
  $ sed -n '168p' backend/app/core/branding.py
  _LIGHT_ACCENT_LIGHTNESS = 0.99
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_branding.py`
- **Step-0 baseline** reused run **B-49** — `116 passed, 1 warning in 8.46s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/app/core/branding.py` was empty at snapshot; (b) every `cmp` since B-49 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i97`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `1 failed, 115 passed, 1 warning in 7.92s`; exit 1
- **Reddened vs that baseline** (1) — `tests/test_branding.py::test_the_default_brand_derives_the_stylesheets_own_primary_text`
- **Case under examination** `tests/test_branding.py::test_primary_text_clears_aa_on_every_text_surface_over_the_lattice`
- **Was it among the reddened?** no — the opposite direction also leaves it green (F-15)
- **Step-5 restore** pristine copy `shasum -a 256` = `d18dbf5c863933cdf09bf362c7d91abaf6488b08c7f76493dfeccc7117efb667`; restored file `shasum -a 256` = `d18dbf5c863933cdf09bf362c7d91abaf6488b08c7f76493dfeccc7117efb667`; `cmp <scratchpad>/snap/S2-MAND-BE-branding-b.branding.py backend/app/core/branding.py` → clean (no output).

#### `S2-MAND-BE-branding-c`

- **File:line** `backend/app/core/branding.py:141`
- **Mutation** — S2 mandatory module backend/tests/test_branding.py -- the same docstring's second named constant: move _STEP
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '141p' <scratchpad>/snap/S2-MAND-BE-branding-c.branding.py
  _STEP = 0.01
  $ sed -n '141p' backend/app/core/branding.py
  _STEP = 0.02
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_branding.py`
- **Step-0 baseline** reused run **B-49** — `116 passed, 1 warning in 8.46s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/app/core/branding.py` was empty at snapshot; (b) every `cmp` since B-49 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i98`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `8 failed, 108 passed, 1 warning in 7.57s`; exit 1
- **Reddened vs that baseline** (8) — `tests/test_branding.py::test_857046_light_is_pinned_at_its_exact_emitted_pair`, `tests/test_branding.py::test_both_walks_converging_prefers_the_darker_value`, `tests/test_branding.py::test_every_emitted_colour_is_in_gamut_and_two_decimals[#0000ff]`, `tests/test_branding.py::test_the_accent_lands_on_secondary_at_full_chroma`, `tests/test_branding.py::test_the_brand_and_tint_repairs_move_the_non_text_side`, `tests/test_branding.py::test_the_default_brand_derives_the_stylesheets_own_primary_text`, `tests/test_branding.py::test_the_two_zero_margin_witnesses_are_pinned_to_the_float`, `tests/test_branding.py::test_the_upward_walk_is_taken_when_only_it_converges`
- **Case under examination** `tests/test_branding.py::test_primary_text_clears_aa_on_every_text_surface_over_the_lattice`
- **Was it among the reddened?** no — eight neighbours reddened on `_STEP`; the claimant case did not (F-15)
- **Step-5 restore** pristine copy `shasum -a 256` = `d18dbf5c863933cdf09bf362c7d91abaf6488b08c7f76493dfeccc7117efb667`; restored file `shasum -a 256` = `d18dbf5c863933cdf09bf362c7d91abaf6488b08c7f76493dfeccc7117efb667`; `cmp <scratchpad>/snap/S2-MAND-BE-branding-c.branding.py backend/app/core/branding.py` → clean (no output).

#### `S2-MAND-BE-branding-d`

- **File:line** `backend/app/core/branding.py:165`
- **Mutation** — S2 mandatory module backend/tests/test_branding.py -- the docstring's third named constant: move _LIGHT_MUTED
- **Step-2 read-back (line-scoped)**

  ```
  $ sed -n '165p' <scratchpad>/snap/S2-MAND-BE-branding-d.branding.py
  _LIGHT_MUTED = (0.96, 0.01)
  $ sed -n '165p' backend/app/core/branding.py
  _LIGHT_MUTED = (0.88, 0.01)
  ```
- **Order-pinned command** `cd backend && SECRET_KEY=test uv run pytest -p no:randomly --no-cov -q --tb=no -rf tests/test_branding.py`
- **Step-0 baseline** reused run **B-49** — `116 passed, 1 warning in 8.46s`; freeze fingerprint `cb629948d2092d3e…`. Three reuse conditions re-asserted at this mutation: (a) `git status --porcelain -- backend/app/core/branding.py` was empty at snapshot; (b) every `cmp` since B-49 came back clean; (c) interim read-only `cd backend && uv pip freeze` captured as `freeze.i99`, compared against `freeze.before2`: **empty**.
- **Step-3 mutated run** — `3 failed, 113 passed, 1 warning in 8.30s`; exit 1
- **Reddened vs that baseline** (3) — `tests/test_branding.py::test_the_default_brand_derives_the_stylesheets_own_primary_text`, `tests/test_branding.py::test_the_muted_foreground_repair_moves_the_text_side_in_both_schemes`, `tests/test_branding.py::test_the_two_zero_margin_witnesses_are_pinned_to_the_float`
- **Case under examination** `tests/test_branding.py::test_primary_text_clears_aa_on_every_text_surface_over_the_lattice`
- **Was it among the reddened?** no — three neighbours reddened on `_LIGHT_MUTED`; the claimant case did not (F-15)
- **Step-5 restore** pristine copy `shasum -a 256` = `d18dbf5c863933cdf09bf362c7d91abaf6488b08c7f76493dfeccc7117efb667`; restored file `shasum -a 256` = `d18dbf5c863933cdf09bf362c7d91abaf6488b08c7f76493dfeccc7117efb667`; `cmp <scratchpad>/snap/S2-MAND-BE-branding-d.branding.py backend/app/core/branding.py` → clean (no output).


---

## Findings

Every entry below has a **verified-present mutation** behind it (the `sed` pair
is on the named ledger row) and a **green step-0 baseline** for the case it
judges. Nothing is listed here on the strength of reading alone.

The closed list of classes:

1. **asserts nothing** — no mutation of the code it names reddens it;
2. **already asserted elsewhere** — and the other test is named;
3. **mocks the behaviour it claims to exercise**;
4. **stays green while the code it exercises raises**;
5. **over-pin** — reddens when the pinned value moves in the direction its own
   contract allows (yields a *rewrite* proposal, never a deletion).

**Slowness, verbosity and age are never grounds for anything**, and no entry
below rests on them.

**This audit proposes zero deletions.** Classes 1–4 are the only grounds on
which a deletion may be offered, and several findings below carry class 1 or 2 —
but in each case the right remedy is to *add or repair* an assertion, not to
remove a case: the cases concerned also hold assertions that are load-bearing
(proved by the neighbours that did redden), or the finding is a missing test
rather than a worthless one. Because nothing is proposed for deletion, there is
no "which production lines is this test the sole cover for" analysis to report;
*Coverage and lint baselines* explains what replaces it.

### F-01 — `GRAPHIC_FLOOR` names a floor that no case enforces · class 1 · rewrite

`backend/tests/test_project_report_branding.py:100`, commented "WCAG 2.1 AA for
normal text, and the 1.4.11 floor for a meaningful graphic". The only read of it
in the whole module is `assert ratio < GRAPHIC_FLOOR` at line 406's sibling,
line 449 — an **upper** bound on the exception list, not a floor on compliant
graphics.

Evidence: `S1-BE-GRAPHIC_FLOOR-strong` raises it from 3.0 to **21.0** — a value
no colour pair on earth can clear — and the module stays green
(`39 passed, 11 warnings`), with `test_the_graphical_pairs_below_three_are_asserted_not_skipped`
among the passes. `S1-BE-GRAPHIC_FLOOR-weak` lowers it to 1.0 and reddens nine
parametrised cases, confirming the upper-bound reading. `LC_ALL=C grep -n
"GRAPHIC_FLOOR" backend/tests/test_project_report_branding.py` returns exactly
lines 100 and 449.

So the constant's own comment claims a guarantee the module does not hold: **no
case asserts that any graphical pair clears 3:1.** Remedy (FU-07): add the
complementary assertion over the graphical pairs *not* on the declared
sub-three list, or restate the comment to say the constant is the boundary of
the accepted-risk list and nothing else.

### F-02 — `SLUG_MAX_BASE_LENGTH` is pinned by nothing · class 1 · rewrite (add a case)

`frontend/src/api/tenantProfile.ts:145`. `S1-FE-SLUG_MAX_BASE_LENGTH-lower`
(60 → 59) and `-higher` (60 → 61) both leave
`src/features/user-administration/__tests__/TenantProfilePage.test.tsx` and its
three sibling files at `22 tests: 22 passed, 0 failed`.
`LC_ALL=C grep -rl "SLUG_MAX_BASE_LENGTH" frontend/src --include='*.test.ts' --include='*.test.tsx'`
returns nothing. The 60-character truncation base that keeps
`<base>-<n>` inside a 64-character column has no test. Remedy: FU-07.

### F-03 — `MAX_REQUEST_ITEMS` is pinned by nothing · class 1 · rewrite (add a case)

`frontend/src/features/purchase-management/components/PurchaseRequestFormModal.tsx:15`.
`S1-FE-MAX_REQUEST_ITEMS-lower` (50 → 49) and `-higher` (50 → 51) both leave
`PurchaseRequestFormModal.test.tsx` at `13 tests: 13 passed`. No spec names the
constant. Remedy: FU-07.

### F-04 — `MAX_QUOTE_ITEMS` is pinned by nothing · class 1 · rewrite (add a case)

`frontend/src/features/purchase-management/components/QuoteFormModal.tsx:21`.
`S1-FE-MAX_QUOTE_ITEMS-lower` (50 → 49) and `-higher` (50 → 51) both leave
`QuoteFormModal.test.tsx` at `22 tests: 22 passed`. Note the contrast with its
sibling two lines above: `MAX_EXTRA_FIELDS` **is** pinned — both of its
mutations redden `QuoteFormModal stops adding extra fields at twenty rows`. The
quote-item cap has no equivalent. Remedy: FU-07.

### F-05 — `MIN_JUSTIFICATION_LENGTH` is pinned by nothing · class 1 · rewrite (add a case)

`frontend/src/features/purchase-management/components/SelectQuoteModal.tsx:11`.
`S1-FE-MIN_JUSTIFICATION_LENGTH-lower` (10 → 9) and `-higher` (10 → 11) both
leave `SelectQuoteModal.test.tsx` at `18 tests: 18 passed`. The minimum length a
quote-selection justification must reach — a validation rule a user meets or
does not — is unpinned. Remedy: FU-07.

### F-06 — the backend coverage gate is pinned by nothing · class 1 · rewrite (add a case)

`backend/pytest.ini:4`, `--cov-fail-under=90`. `S1-CFG-cov_fail_under-weak`
(90 → 1) and `-strong` (90 → 100) both leave
`tests/test_suite_hygiene.py` at `9 passed, 1 warning`. The module *does* pin
`pytest.ini`'s `timeout` (`S1-CFG-pytest_timeout-weak` reddens
`test_pytest_ini_caps_a_single_test`) and its `timeout_method`, but nothing reads
`--cov-fail-under`. The 90% gate could be lowered to 1 in a commit and no test
would say so. Remedy: FU-08.

### F-07 — `matrix_world.py`'s isolation claim is pinned by nothing · class 1 · rewrite

`backend/tests/matrix_world.py:63` — "every write. The world is never rebuilt",
resting (per lines 58–63) on a `join_transaction_mode="create_savepoint"`
session. `S2-BE-01` removes that argument at line 1466 and the whole
1330-cell matrix stays green (`1330 passed, 1273 warnings in 11.35s`). The
harness's stated isolation mechanism can be deleted without a single case
noticing. Remedy: FU-09 — a dedicated case that writes in one cell and asserts
the next cell cannot see it.

### F-08 — `test_purchase_request_created_at_is_stored_naive` does not reach the column · class 1 · rewrite

`backend/tests/test_clock.py:242-259`. Its own comment at lines 252–254 says that
without `session.expire_all()` "`get` can hand back the very object that was just
written, and the assertion would never reach the column it is about."

`S2-BE-02` removes `session.expire_all()`: green — which, as that row records,
**does not discriminate** the claim, because a vacuous pass and a real pass are
both green. `S2-BE-02b` is the discriminating mutation: it replaces
`stored = session.get(PurchaseRequest, read.id)` with `stored = read`, so the
assertions run against the in-memory object and never touch the stored row at
all. The module stays green (`12 passed, 10 warnings`).

So the case proves the *service return value* is naive, not that the *column*
stores naive — which is what its name and its §4.4 reference claim. Remedy:
FU-09 — assert over a value read back on a fresh session, or over the column
type, so the mutation above reddens.

### F-09 — "answers `[]`, never `null`" is not asserted · class 1 · rewrite

`backend/tests/test_occurrences.py:218`. The case asserts the field exists and
`is_required() is False`, and nothing more.
`S2-BE-04` changes `app/schemas/occurrence.py:92` from
`infraction_ids: list[UUID] = Field(default_factory=list)` to
`infraction_ids: list[UUID] | None = None`: `tests/test_occurrences.py` stays
green (`6 passed`). `S2-BE-04b` runs the same mutation against
`tests/test_infractions.py`, the other reader of the promotion link: also green
(`34 passed`). The claim "the frontend needs no guard" rests on nothing.
Remedy: FU-09.

### F-10 — `test_planned_to_date_defaults_to_the_projects_clock` cannot tell the two clocks apart · class 2 · rewrite

`backend/tests/test_project_report.py:1209-1211`: "No `today` argument means
`app.core.clock`, never `date.today()`", asserted as
`planned_to_date([{"month": "1970-01", "pct": 7.0}]) == 7.0`. Every value of
"today" at or after 1970-01 gives 7.0, so the assertion cannot discriminate.
`S2-BE-06` swaps `clock.today_utc()` for `_dt.date.today()` at
`app/services/project_report_service.py:697`: `tests/test_project_report.py`
stays green at `100 passed`.

**The other test is named**: `S2-BE-06b` runs the identical mutation against
`tests/test_lint_hygiene.py` and reddens
`tests/test_lint_hygiene.py::test_clock_py_is_the_only_clock_in_app`. The
contract *is* protected — structurally, repository-wide — just not by the case
whose name claims it. Class 2, not class 1. Remedy: FU-09 — either make the case
discriminate (pass a date far in the past as the curve's month and assert the
clock-dependent branch) or have its docstring name
`test_clock_py_is_the_only_clock_in_app` as the half that holds the claim.

### F-11 — `test_project_report_branding.py`'s §B docstring is both unasserted and stale · class 1 · rewrite

Lines 19–24 claim "**§B — the logo is bytes, not a URL, whenever it can be read
locally.** Three rungs, in order: a `data:` URI when the storage provider can
read its own object back, today's `<img src>` for an absolute `http(s)` value,
and no `<img>` at all otherwise."

Two defects, one measured and one read:

1. *Unasserted.* The surviving half of the claim is "named **absolutely**"
   (`app/services/project_report_service.py:1310`). `S2-BE-07` makes
   `_logo_html` emit a relative `src` at line 1339;
   `tests/test_project_report_branding.py` stays green (`39 passed`). `S2-BE-07b`
   runs it against `tests/test_project_report.py` — the module the branding
   docstring names at lines 12–13 as "the authenticated half of that claim" —
   and that stays green too (`100 passed`). Neither module pins the absoluteness
   the production docstring calls load-bearing for the `<iframe srcDoc>` case.
2. *Stale.* `_logo_html`'s own docstring at lines 1307 and 1319 says "Two
   outcomes, not three (APRAS-105 §E)" and "The `data:` URI rung is gone, and
   with it this function's storage read" (APRAS-93's byte-size measurement). The
   test module still documents three rungs and a `data:` URI. This half is a
   read-only observation and is reported as such, not as a mutation-backed
   finding.

Remedy: FU-09 — assert the emitted `src` starts with a scheme, and bring the
module docstring to two rungs.

### F-12 — `record_parity_baseline.py`'s "Relative, never absolute" is pinned only through a committed artefact · class 1 · rewrite

`backend/tests/tools/record_parity_baseline.py:57`. `S2-BE-12` makes `GENERATOR`
an absolute path; `tests/test_permission_parity_matrix.py` stays green at
`1330 passed`. The reason is structural: the parity module asserts
`str(BACKEND_ROOT) not in raw` over the **committed** baseline JSON
(`S3-BE-05` proves that assertion is live — injecting the path reddens
`test_the_apras_61_baseline_carries_no_absolute_path_and_no_timestamp`), and no
case re-runs the generator. A regression in the generator is caught only the
next time an operator regenerates and commits. Remedy: FU-09 — call the
generator's `_meta` builder in-process and assert over its output.

### F-13 — `SubscriptionPage`'s "courtesy and override modules … are never sent" is asserted nowhere · class 1 · rewrite

`frontend/src/features/user-administration/pages/SubscriptionPage.tsx:88`.
`S2-FE-10` drops `row.source !== "OVERRIDE"` from the payload filter at line 97:
`SubscriptionPage.test.tsx` stays green (`9 tests: 9 passed`). `S2-FE-10b` runs
the same mutation against **the whole**
`src/features/user-administration/__tests__` directory — `513 tests: 513 passed,
0 failed (files 51)`, reproducible as `Test Files 51 passed (51)` / `Tests 513
passed (513)` — so it is class 1, not class 2. The docstring names the
two failure modes it exists to prevent ("a permanent 400" and "silently killing
an operator override"); neither is pinned. Remedy: FU-10.

### F-14 — a prose contract inside a type declaration is unpinnable by any runtime test · class 1 · rewrite

`frontend/src/types/subscription.ts:51-53` — `can_contract` is "exactly 'the
contracting PUT would accept this module', never looser". `S2-FE-12` makes the
field optional (`can_contract?: boolean;`) and `SubscriptionPage.test.tsx` stays
green (`9 tests: 9 passed`). This is green **by construction**: Vitest transpiles
without type-checking, so no runtime case can observe a change to an `interface`.
Recorded because it is a real gap with a real mutation behind it, and because it
tells the next auditor that `.d`-shaped prose needs `tsc`, not Vitest. Remedy:
FU-11 — a `tsc --noEmit` gate in CI, or a runtime assertion over a fixture that
the backend's own contract test also reads.

### F-15 — `test_primary_text_clears_aa_on_every_text_surface_over_the_lattice` is not what alarms · class 2 · rewrite · **neighbour-only reddening**

`backend/tests/test_branding.py:450-455`. Its docstring says: "It is what alarms
if `_STEP`, `_LIGHT_MUTED` or `_LIGHT_ACCENT_LIGHTNESS` ever moves: the two
witnesses below stop at **exactly** 4.5, so there is no cushion anywhere on this
lattice."

Four mutations, all three named constants, both directions on one of them:

| row | mutation | reddened | was the claimant case among them? |
|---|---|---|---|
| `S2-MAND-BE-branding` | `_LIGHT_ACCENT_LIGHTNESS` 0.96 → 0.90 | `test_accent_stays_the_pale_hover_tint_of_the_accent_hue`, `test_the_default_brand_derives_the_stylesheets_own_primary_text`, `test_the_two_zero_margin_witnesses_are_pinned_to_the_float` | **no** |
| `S2-MAND-BE-branding-b` | `_LIGHT_ACCENT_LIGHTNESS` 0.96 → 0.99 | `test_the_default_brand_derives_the_stylesheets_own_primary_text` | **no** |
| `S2-MAND-BE-branding-c` | `_STEP` 0.01 → 0.02 | eight cases, including `test_the_two_zero_margin_witnesses_are_pinned_to_the_float` | **no** |
| `S2-MAND-BE-branding-d` | `_LIGHT_MUTED` (0.96, 0.01) → (0.88, 0.01) | `test_the_default_brand_derives_the_stylesheets_own_primary_text`, `test_the_muted_foreground_repair_moves_the_text_side_in_both_schemes`, `test_the_two_zero_margin_witnesses_are_pinned_to_the_float` | **no** |

Every one of the four mutations reddened **neighbours** and never the case that
claims to be the alarm. The alarm is real — `test_the_two_zero_margin_witnesses_are_pinned_to_the_float`
and `test_the_default_brand_derives_the_stylesheets_own_primary_text` are what
fire — so this is class 2, "already asserted elsewhere", with those two named.
Per the spec, a mutation that reddens only a neighbour is a finding in its own
right, and this is that finding. Remedy: FU-09 — move the claim into the
docstrings of the two witnesses, or make the lattice case assert the zero-margin
property it says it has (e.g. assert the lattice minimum **equals** 4.5 rather
than only clearing it).

### F-16 — `voting_helpers`' CPF-pool guard is pinned by nothing · class 1 · rewrite

`backend/tests/voting_helpers.py:43`, `if cpf not in used:` — the guard that
stops the helper handing out a CPF another user already holds. `S3-BE-20`
inverts it to `if cpf in used:` and `tests/test_voting.py` stays green
(`19 passed`). `S3-BE-20b` runs the same inversion against
`tests/test_voting_edge_cases.py` and `tests/test_voting_rbac.py`: also green
(`51 passed`). Across all 70 voting cases, the pool's uniqueness guard is not
load-bearing. That is a latent flake rather than a live bug: today the pool is
large enough that the first entry is usually unused, so inverting the guard
still happens to produce a workable CPF. Remedy: FU-09 — a direct case over the
helper, asserting it never returns a CPF already in `User.cpf`.

---

## Over-pins

**No class-5 over-pin was found.** The table below lists **every** member of the
S1 threshold subset — 19 backend, 21 frontend, 2 config declarations — and
states, for each, whether moving it in the direction its own contract allows
keeps the suite green.

`backend/tests/test_bcrypt_cost.py` is covered by name, and so is the evidence
the spec asks for: `S1-BE-BCRYPT_ROUNDS-prod-13` raises
`app/core/security.py:27` from `BCRYPT_ROUNDS = 12` to `BCRYPT_ROUNDS = 13` —
the direction the ratchet exists to permit — and the module **stays green**
(`1 failed, 9 passed`, the one failure being the pre-existing
`test_passlib_is_not_installed`, excluded as evidence). The ratchet ratchets;
the module is not an over-pin. As the spec requires, this audit does **not**
describe that module's source anchor or floor assertion as defects: the anchor is
`assert f"BCRYPT_ROUNDS = {security.BCRYPT_ROUNDS}" in code` and the ratchet is
`>= PRODUCTION_FLOOR`, and both are correct.

| S1 threshold-subset member | `file:line` | shape | direction its contract allows | moving it that way keeps the suite green? | evidence |
|---|---|---|---|---|---|
| PRODUCTION_FLOOR | `backend/tests/test_bcrypt_cost.py:54` | floor (`>= PRODUCTION_FLOOR`) | the production cost may rise | **yes** | `S1-BE-PRODUCTION_FLOOR-weak` → no case reddened; opposite direction `S1-BE-PRODUCTION_FLOOR-strong` → reddened 3 case(s) |
| BCRYPT_ROUNDS (production) | `backend/app/core/security.py:27` | the value the floor protects | upward (12 → 13) | **yes** | `S1-BE-BCRYPT_ROUNDS-prod-13` → no case reddened |
| DATED_COLUMN_FLOOR | `backend/tests/test_clock.py:113` | vacuity floor | the real count may rise | **yes** | `S1-BE-DATED_COLUMN_FLOOR-weak` → no case reddened; opposite direction `S1-BE-DATED_COLUMN_FLOOR-strong` → reddened 1 case(s) |
| NOQA_CAP | `backend/tests/test_lint_hygiene.py:57` | cap (`total <= NOQA_CAP`) | the count may fall | **no — reddens** | `S1-BE-NOQA_CAP-weak` → reddened `tests/test_lint_hygiene.py::test_noqa_count_is_within_the_cap`; opposite direction `S1-BE-NOQA_CAP-strong` → reddened 1 case(s) |
| NOQA_CAP ceiling (108) | `backend/tests/test_lint_hygiene.py:122` | cap on the cap | the cap may fall | **yes** | `S1-BE-NOQA_CAP_CEILING-weak` → no case reddened; opposite direction `S1-BE-NOQA_CAP_CEILING-strong` → reddened 1 case(s) |
| MAX_NON_ROLE_403 | `backend/tests/test_permission_parity_matrix.py:452` | cap | the count may fall | **yes** | `S1-BE-MAX_NON_ROLE_403-weak` → no case reddened; opposite direction `S1-BE-MAX_NON_ROLE_403-strong` → reddened 1 case(s) |
| MAX_PERMITTED_422 | `backend/tests/test_permission_parity_matrix.py:453` | cap | the count may fall | **yes** | `S1-BE-MAX_PERMITTED_422-weak` → no case reddened; opposite direction `S1-BE-MAX_PERMITTED_422-strong` → reddened 1 case(s) |
| MAX_GROWTH_MM | `backend/tests/test_project_report_bar_geometry.py:124` | cap | growth may shrink | **yes** | `S1-BE-MAX_GROWTH_MM-weak` → no case reddened; opposite direction `S1-BE-MAX_GROWTH_MM-strong` → reddened 1 case(s) |
| TEXT_FLOOR | `backend/tests/test_project_report_branding.py:99` | floor (`ratio >= TEXT_FLOOR`) | ratios may rise | **yes** | `S1-BE-TEXT_FLOOR-weak` → no case reddened; opposite direction `S1-BE-TEXT_FLOOR-strong` → reddened 5 case(s) |
| GRAPHIC_FLOOR | `backend/tests/test_project_report_branding.py:100` | read only as an **upper** bound (`ratio < GRAPHIC_FLOOR`) | **none in the floor sense** — see F-01 | **no — reddens** | `S1-BE-GRAPHIC_FLOOR-weak` → reddened `tests/test_project_report_branding.py::test_the_graphical_pairs_below_three_are_asserted_not_skipped[#059669-#059669-brand-brand-alt-1.0]`, `tests/test_project_report_branding.py::test_the_graphical_pairs_below_three_are_asserted_not_skipped[#059669-#059669-brand-line-2.9478]` …; opposite direction `S1-BE-GRAPHIC_FLOOR-strong` → no case reddened |
| REQUESTS_PAST_THE_DECLINED_LIMIT | `backend/tests/test_public_project_report.py:54` | loop count, not a bound | either — see EK-01 | **yes** | `S1-BE-DECLINED_LIMIT-weak` → no case reddened; opposite direction `S1-BE-DECLINED_LIMIT-strong` → no case reddened |
| ATTACHMENT_MAX_FILE_SIZE | `backend/tests/test_purchase_quote_attachment.py:482` | equality pin | **none** — an equality pin has no slack side | **no — reddens** | `S1-BE-ATTACHMENT_MAX-weak` → reddened `tests/test_purchase_quote_attachment.py::test_the_attachment_contract_matches_the_frontend_client`; opposite direction `S1-BE-ATTACHMENT_MAX-strong` → reddened 1 case(s) |
| SLUG_MIN_LENGTH | `backend/tests/test_slug.py:92` | equality pin | **none** | **no — reddens** | `S1-BE-SLUG_MIN-weak` → reddened `tests/test_slug.py::test_the_fallback_base_is_itself_valid_and_inside_the_column`; opposite direction `S1-BE-SLUG_MIN-strong` → reddened 1 case(s) |
| SLUG_MAX_LENGTH | `backend/tests/test_slug.py:93` | equality pin | **none** | **no — reddens** | `S1-BE-SLUG_MAX-weak` → reddened `tests/test_slug.py::test_the_fallback_base_is_itself_valid_and_inside_the_column`; opposite direction `S1-BE-SLUG_MAX-strong` → reddened 1 case(s) |
| BLOB_MAX_READ_BYTES | `backend/tests/test_storage_blob.py:1093` | equality pin | **none** | **no — reddens** | `S1-BE-BLOB_MAX_READ-weak` → reddened `tests/test_storage_blob.py::test_the_default_ceiling_is_the_logo_ceiling`; opposite direction `S1-BE-BLOB_MAX_READ-strong` → reddened 1 case(s) |
| BLOB_LOG_BODY_MAX_BYTES | `backend/tests/test_storage_blob.py:1426` | equality pin, plus a `<=` guard two lines above | **none** | **no — reddens** | `S1-BE-BLOB_LOG_BODY_MAX-weak` → reddened `tests/test_storage_blob.py::test_a_long_refusal_body_is_bounded_in_bytes_and_marked[ascii]`, `tests/test_storage_blob.py::test_a_long_refusal_body_is_bounded_in_bytes_and_marked[multibyte]`; opposite direction `S1-BE-BLOB_LOG_BODY_MAX-strong` → reddened 2 case(s) |
| DATED_SCHEMA_FLOOR | `backend/tests/test_suite_hygiene.py:293` | vacuity floor | the real count may rise | **yes** | `S1-BE-DATED_SCHEMA_FLOOR-weak` → no case reddened; opposite direction `S1-BE-DATED_SCHEMA_FLOOR-strong` → reddened 1 case(s) |
| MAX_PER_TEST_TIMEOUT | `backend/tests/test_suite_hygiene.py:55` | cap on `pytest.ini`'s `timeout` | the declaration may fall | **yes** | `S1-BE-MAX_PER_TEST_TIMEOUT-weak` → no case reddened; opposite direction `S1-BE-MAX_PER_TEST_TIMEOUT-strong` → reddened 1 case(s) |
| LOGO_MAX_FILE_SIZE | `backend/tests/test_tenant_profile.py:1166` | equality pin | **none** | **no — reddens** | `S1-BE-LOGO_MAX-weak` → reddened `tests/test_tenant_profile.py::test_the_profile_contract_matches_the_frontend_client`; opposite direction `S1-BE-LOGO_MAX-strong` → reddened 1 case(s) |
| media_service.MAX_FILE_SIZE | `backend/tests/test_uploads.py:259` | equality pin | **none** | **no — reddens** | `S1-BE-UPLOAD_MAX-weak` → reddened `tests/test_uploads.py::test_the_upload_contract_matches_the_infraction_uploader`; opposite direction `S1-BE-UPLOAD_MAX-strong` → reddened 1 case(s) |
| pytest.ini `timeout` | `backend/pytest.ini:17` | value under a cap | may fall | **yes** | `S1-CFG-pytest_timeout-strong` → no case reddened; opposite direction `S1-CFG-pytest_timeout-weak` → reddened 1 case(s) |
| pytest.ini `--cov-fail-under` | `backend/pytest.ini:4` | gate value, pinned by nothing | either — see F-06 | **yes** | `S1-CFG-cov_fail_under-weak` → no case reddened; opposite direction `S1-CFG-cov_fail_under-strong` → no case reddened |
| MINIMUM_PAIRS | `frontend/src/__tests__/themeContrast.test.ts:172` | vacuity floor | the real count may rise | **yes** | `S1-FE-MINIMUM_PAIRS-lower` → no case reddened; opposite direction `S1-FE-MINIMUM_PAIRS-higher` → reddened 3 case(s) |
| MINIMUM_RATIO | `frontend/src/__tests__/themeContrast.test.ts:53` | floor | ratios may rise | **no — reddens** | `S1-FE-MINIMUM_RATIO-lower` → reddened `the measurement measures the pair APRAS-88 repaired at its stated ratios`; opposite direction `S1-FE-MINIMUM_RATIO-higher` → reddened 2 case(s) |
| MINIMUM_CONTRAST_RATIO | `frontend/src/lib/contrast.ts:50` | floor, shared with the backend | ratios may rise | **no — reddens** | `S1-FE-MINIMUM_CONTRAST_RATIO-lower` → reddened `auditHexPalette names every pair of black text on a near-black background`, `auditScheme names the failing pair and its measured ratio` …; opposite direction `S1-FE-MINIMUM_CONTRAST_RATIO-higher` → reddened 8 case(s) |
| QUOTE_ATTACHMENT_MAX_FILE_SIZE_BYTES | `frontend/src/api/purchases.ts:26` | equality pin against the server | **none** | **no — reddens** | `S1-FE-QUOTE_ATTACHMENT_MAX-lower` → reddened `the quote-attachment contract pins the cap, the accepted set and the derived accept attribute`; opposite direction `S1-FE-QUOTE_ATTACHMENT_MAX-higher` → reddened 1 case(s) |
| SLUG_MIN_LENGTH (frontend) | `frontend/src/api/tenantProfile.ts:139` | equality pin against the server | **none** | **no — reddens** | `S1-FE-FE_SLUG_MIN_LENGTH-lower` → reddened `TenantProfilePage — the slug (APRAS-66) mirrors the server's rule, and only mirrors it`; opposite direction `S1-FE-FE_SLUG_MIN_LENGTH-higher` → reddened 1 case(s) |
| SLUG_MAX_LENGTH (frontend) | `frontend/src/api/tenantProfile.ts:140` | equality pin against the server | **none** | **no — reddens** | `S1-FE-FE_SLUG_MAX_LENGTH-lower` → reddened `TenantProfilePage — the slug (APRAS-66) mirrors the server's rule, and only mirrors it`; opposite direction `S1-FE-FE_SLUG_MAX_LENGTH-higher` → reddened 1 case(s) |
| SLUG_MAX_BASE_LENGTH | `frontend/src/api/tenantProfile.ts:145` | truncation bound | either — pinned by nothing, see F-02 | **yes** | `S1-FE-SLUG_MAX_BASE_LENGTH-lower` → no case reddened; opposite direction `S1-FE-SLUG_MAX_BASE_LENGTH-higher` → no case reddened |
| TENANT_LOGO_MAX_FILE_SIZE_BYTES | `frontend/src/api/tenantProfile.ts:176` | equality pin against the server | **none** | **no — reddens** | `S1-FE-TENANT_LOGO_MAX-lower` → reddened `the /admin/tenant-profile gate states the same four facts the backend pins from its side`; opposite direction `S1-FE-TENANT_LOGO_MAX-higher` → reddened 1 case(s) |
| UPLOAD_MAX_FILE_SIZE_BYTES | `frontend/src/api/uploads.ts:28` | equality pin against the server | **none** | **no — reddens** | `S1-FE-UPLOAD_MAX_BYTES-lower` → reddened `the five server facts, pinned from this side declares media_service.MAX_FILE_SIZE`; opposite direction `S1-FE-UPLOAD_MAX_BYTES-higher` → reddened 1 case(s) |
| GRAPHICAL_CONTRAST_RATIO (documentOccurrence) | `frontend/src/features/__tests__/documentOccurrenceContrast.test.ts:31` | floor | ratios may rise | **yes** | `S1-FE-GCR_documentOccurrence-lower` → no case reddened; opposite direction `S1-FE-GCR_documentOccurrence-higher` → reddened 10 case(s) |
| GRAPHICAL_CONTRAST_RATIO (financePurchasesAccess) | `frontend/src/features/__tests__/financePurchasesAccessContrast.test.ts:33` | floor **and** the boundary of the declared sub-AA list | neither, in practice | **no — reddens** | `S1-FE-GCR_financePurchasesAccess-lower` → reddened `declared sub-AA or unmeasurable, none of it introduced by this task names every pair it leaves below AA and no more`; opposite direction `S1-FE-GCR_financePurchasesAccess-higher` → reddened 18 case(s) |
| GRAPHICAL_CONTRAST_RATIO (mediaFeedback…) | `frontend/src/features/__tests__/mediaFeedbackAnnouncementsPackagesContrast.test.ts:44` | floor **and** the boundary of the declared sub-AA list | neither, in practice | **no — reddens** | `S1-FE-GCR_mediaFeedback-lower` → reddened `declared sub-AA or unmeasurable, and which are this task's names every pair it leaves below AA and no more`, `§7 — the zoom slider, the one design change this child carries clears the track's 3:1 floor in five themes and fails it in the pale one` …; opposite direction `S1-FE-GCR_mediaFeedback-higher` → reddened 21 case(s) |
| GRAPHICAL_CONTRAST_RATIO (projectAsset) | `frontend/src/features/__tests__/projectAssetContrast.test.ts:31` | floor | ratios may rise | **yes** | `S1-FE-GCR_projectAsset-lower` → no case reddened; opposite direction `S1-FE-GCR_projectAsset-higher` → reddened 12 case(s) |
| GRAPHICAL_CONTRAST_RATIO (visitorManagement) | `frontend/src/features/visitor-management/__tests__/visitorManagementContrast.test.ts:33` | floor | ratios may rise | **yes** | `S1-FE-GCR_visitorManagement-lower` → no case reddened; opposite direction `S1-FE-GCR_visitorManagement-higher` → reddened 5 case(s) |
| DOCUMENTED_ROUTE_CEILING | `frontend/src/features/infraction-management/__tests__/lotSelectContract.test.tsx:57` | ceiling the request must fit under | the documented ceiling may rise | **yes** | `S1-FE-DOCUMENTED_ROUTE_CEILING-higher` → no case reddened; opposite direction `S1-FE-DOCUMENTED_ROUTE_CEILING-lower` → reddened 1 case(s) |
| DOCUMENTED_MAX_FILE_SIZE_BYTES | `frontend/src/features/infraction-management/__tests__/uploadContract.test.tsx:60` | equality pin against the server | **none** | **no — reddens** | `S1-FE-DOCUMENTED_MAX_FILE_SIZE_BYTES-lower` → reddened `the five server facts, pinned from this side declares media_service.MAX_FILE_SIZE`; opposite direction `S1-FE-DOCUMENTED_MAX_FILE_SIZE_BYTES-higher` → reddened 1 case(s) |
| LOT_SELECT_LIMIT | `frontend/src/features/infraction-management/components/NewInfractionModal.tsx:25` | value under the documented ceiling | downward | **yes** | `S1-FE-LOT_SELECT_LIMIT-lower` → no case reddened; opposite direction `S1-FE-LOT_SELECT_LIMIT-higher` → reddened 1 case(s) |
| MAX_REQUEST_ITEMS | `frontend/src/features/purchase-management/components/PurchaseRequestFormModal.tsx:15` | cap | either — pinned by nothing, see F-03 | **yes** | `S1-FE-MAX_REQUEST_ITEMS-lower` → no case reddened; opposite direction `S1-FE-MAX_REQUEST_ITEMS-higher` → no case reddened |
| MAX_EXTRA_FIELDS | `frontend/src/features/purchase-management/components/QuoteFormModal.tsx:18` | cap, pinned by an exact behavioural case | **none** — the case pins 'stops at twenty rows' | **no — reddens** | `S1-FE-MAX_EXTRA_FIELDS-lower` → reddened `QuoteFormModal stops adding extra fields at twenty rows`; opposite direction `S1-FE-MAX_EXTRA_FIELDS-higher` → reddened 1 case(s) |
| MAX_QUOTE_ITEMS | `frontend/src/features/purchase-management/components/QuoteFormModal.tsx:21` | cap | either — pinned by nothing, see F-04 | **yes** | `S1-FE-MAX_QUOTE_ITEMS-lower` → no case reddened; opposite direction `S1-FE-MAX_QUOTE_ITEMS-higher` → no case reddened |
| MIN_JUSTIFICATION_LENGTH | `frontend/src/features/purchase-management/components/SelectQuoteModal.tsx:11` | floor | either — pinned by nothing, see F-05 | **yes** | `S1-FE-MIN_JUSTIFICATION_LENGTH-lower` → no case reddened; opposite direction `S1-FE-MIN_JUSTIFICATION_LENGTH-higher` → no case reddened |

Members whose slack-direction move **reddens** (candidate over-pins), and the adjudication:
- **NOQA_CAP** (`backend/tests/test_lint_hygiene.py:57`) — `S1-BE-NOQA_CAP-weak` reddened `tests/test_lint_hygiene.py::test_noqa_count_is_within_the_cap`.
- **GRAPHIC_FLOOR** (`backend/tests/test_project_report_branding.py:100`) — `S1-BE-GRAPHIC_FLOOR-weak` reddened `tests/test_project_report_branding.py::test_the_graphical_pairs_below_three_are_asserted_not_skipped[#059669-#059669-brand-brand-alt-1.0]`, `tests/test_project_report_branding.py::test_the_graphical_pairs_below_three_are_asserted_not_skipped[#059669-#059669-brand-line-2.9478]`, `tests/test_project_report_branding.py::test_the_graphical_pairs_below_three_are_asserted_not_skipped[#059669-#c6a04a-brand-alt-card-2.4952]`.
- **ATTACHMENT_MAX_FILE_SIZE** (`backend/tests/test_purchase_quote_attachment.py:482`) — `S1-BE-ATTACHMENT_MAX-weak` reddened `tests/test_purchase_quote_attachment.py::test_the_attachment_contract_matches_the_frontend_client`.
- **SLUG_MIN_LENGTH** (`backend/tests/test_slug.py:92`) — `S1-BE-SLUG_MIN-weak` reddened `tests/test_slug.py::test_the_fallback_base_is_itself_valid_and_inside_the_column`.
- **SLUG_MAX_LENGTH** (`backend/tests/test_slug.py:93`) — `S1-BE-SLUG_MAX-weak` reddened `tests/test_slug.py::test_the_fallback_base_is_itself_valid_and_inside_the_column`.
- **BLOB_MAX_READ_BYTES** (`backend/tests/test_storage_blob.py:1093`) — `S1-BE-BLOB_MAX_READ-weak` reddened `tests/test_storage_blob.py::test_the_default_ceiling_is_the_logo_ceiling`.
- **BLOB_LOG_BODY_MAX_BYTES** (`backend/tests/test_storage_blob.py:1426`) — `S1-BE-BLOB_LOG_BODY_MAX-weak` reddened `tests/test_storage_blob.py::test_a_long_refusal_body_is_bounded_in_bytes_and_marked[ascii]`, `tests/test_storage_blob.py::test_a_long_refusal_body_is_bounded_in_bytes_and_marked[multibyte]`.
- **LOGO_MAX_FILE_SIZE** (`backend/tests/test_tenant_profile.py:1166`) — `S1-BE-LOGO_MAX-weak` reddened `tests/test_tenant_profile.py::test_the_profile_contract_matches_the_frontend_client`.
- **media_service.MAX_FILE_SIZE** (`backend/tests/test_uploads.py:259`) — `S1-BE-UPLOAD_MAX-weak` reddened `tests/test_uploads.py::test_the_upload_contract_matches_the_infraction_uploader`.
- **MINIMUM_RATIO** (`frontend/src/__tests__/themeContrast.test.ts:53`) — `S1-FE-MINIMUM_RATIO-lower` reddened `the measurement measures the pair APRAS-88 repaired at its stated ratios`.
- **MINIMUM_CONTRAST_RATIO** (`frontend/src/lib/contrast.ts:50`) — `S1-FE-MINIMUM_CONTRAST_RATIO-lower` reddened `auditHexPalette names every pair of black text on a near-black background`, `auditScheme names the failing pair and its measured ratio`, `contrast.ts against the shared fixture pins the same minimum the backend does`.
- **QUOTE_ATTACHMENT_MAX_FILE_SIZE_BYTES** (`frontend/src/api/purchases.ts:26`) — `S1-FE-QUOTE_ATTACHMENT_MAX-lower` reddened `the quote-attachment contract pins the cap, the accepted set and the derived accept attribute`.
- **SLUG_MIN_LENGTH (frontend)** (`frontend/src/api/tenantProfile.ts:139`) — `S1-FE-FE_SLUG_MIN_LENGTH-lower` reddened `TenantProfilePage — the slug (APRAS-66) mirrors the server's rule, and only mirrors it`.
- **SLUG_MAX_LENGTH (frontend)** (`frontend/src/api/tenantProfile.ts:140`) — `S1-FE-FE_SLUG_MAX_LENGTH-lower` reddened `TenantProfilePage — the slug (APRAS-66) mirrors the server's rule, and only mirrors it`.
- **TENANT_LOGO_MAX_FILE_SIZE_BYTES** (`frontend/src/api/tenantProfile.ts:176`) — `S1-FE-TENANT_LOGO_MAX-lower` reddened `the /admin/tenant-profile gate states the same four facts the backend pins from its side`.
- **UPLOAD_MAX_FILE_SIZE_BYTES** (`frontend/src/api/uploads.ts:28`) — `S1-FE-UPLOAD_MAX_BYTES-lower` reddened `the five server facts, pinned from this side declares media_service.MAX_FILE_SIZE`.
- **GRAPHICAL_CONTRAST_RATIO (financePurchasesAccess)** (`frontend/src/features/__tests__/financePurchasesAccessContrast.test.ts:33`) — `S1-FE-GCR_financePurchasesAccess-lower` reddened `declared sub-AA or unmeasurable, none of it introduced by this task names every pair it leaves below AA and no more`.
- **GRAPHICAL_CONTRAST_RATIO (mediaFeedback…)** (`frontend/src/features/__tests__/mediaFeedbackAnnouncementsPackagesContrast.test.ts:44`) — `S1-FE-GCR_mediaFeedback-lower` reddened `declared sub-AA or unmeasurable, and which are this task's names every pair it leaves below AA and no more`, `§7 — the zoom slider, the one design change this child carries clears the track's 3:1 floor in five themes and fails it in the pale one`, `§7 — the zoom slider, the one design change this child carries measures what the rejected candidates would have given the thumb`.
- **DOCUMENTED_MAX_FILE_SIZE_BYTES** (`frontend/src/features/infraction-management/__tests__/uploadContract.test.tsx:60`) — `S1-FE-DOCUMENTED_MAX_FILE_SIZE_BYTES-lower` reddened `the five server facts, pinned from this side declares media_service.MAX_FILE_SIZE`.
- **MAX_EXTRA_FIELDS** (`frontend/src/features/purchase-management/components/QuoteFormModal.tsx:18`) — `S1-FE-MAX_EXTRA_FIELDS-lower` reddened `QuoteFormModal stops adding extra fields at twenty rows`.

### Adjudication of the twenty members whose slack-direction move reddens

Nineteen of the twenty are **equality pins or deliberate two-sided pins**, for
which the table already records "direction its contract allows: **none**". An
equality pin that reddens in both directions is doing exactly its job and is not
an over-pin. Specifically:

- The nine cross-language contract pins (`ATTACHMENT_MAX_FILE_SIZE`,
  `SLUG_MIN_LENGTH`/`SLUG_MAX_LENGTH` on both sides, `BLOB_MAX_READ_BYTES`,
  `BLOB_LOG_BODY_MAX_BYTES`, `LOGO_MAX_FILE_SIZE`, `media_service.MAX_FILE_SIZE`,
  `QUOTE_ATTACHMENT_MAX_FILE_SIZE_BYTES`, `TENANT_LOGO_MAX_FILE_SIZE_BYTES`,
  `UPLOAD_MAX_FILE_SIZE_BYTES`, `DOCUMENTED_MAX_FILE_SIZE_BYTES`) exist so that
  changing one side without the other fails. Their failure message says so. The
  product may change the number; the test is the thing that forces both sides to
  change together. Not over-pins.
- `NOQA_CAP`: the mutation labelled *weak* raises the cap to 10000, which reddens
  because line 122 holds a ceiling of 108 on the cap itself. Raising a ratchet's
  cap is the direction the contract **forbids** — the docstring at line 112 says
  "this suite may lower it, never raise it silently" — so the label is the one
  that was wrong, not the test. `S1-BE-NOQA_CAP-strong` (cap → 0) also reddens,
  which is the ratchet working. Not an over-pin.
- `MINIMUM_RATIO` and `MINIMUM_CONTRAST_RATIO`: lowering the floor reddens
  `the measurement measures the pair APRAS-88 repaired at its stated ratios` and
  `contrast.ts against the shared fixture pins the same minimum the backend
  does`. Those are deliberate equality pins on the constant's **value** as a
  cross-language contract, named as such in their own titles. Not over-pins.
- `GRAPHICAL_CONTRAST_RATIO` in `financePurchasesAccessContrast.test.ts` and
  `mediaFeedbackAnnouncementsPackagesContrast.test.ts`: lowering it reddens
  `names every pair it leaves below AA and no more`, because a pair declared
  sub-AA stops being sub-AA when the threshold drops. That is the declared-list
  exactness working in both directions, by design. Not over-pins.
- `MAX_EXTRA_FIELDS`: both directions redden `QuoteFormModal stops adding extra
  fields at twenty rows`, a case whose title pins the number exactly. Not an
  over-pin.
- `GRAPHIC_FLOOR` is the one member whose reddening is informative, and the
  finding there is the **opposite** of an over-pin: the direction that should
  have reddened (raising the floor past anything achievable) does not. See F-01.

One measured asymmetry worth recording even though it is not a finding:
`S1-CFG-pytest_timeout-strong` lowers `pytest.ini`'s `timeout` from 300 to **1**
and `tests/test_suite_hygiene.py` stays green at `9 passed`. The module holds a
ceiling (`timeout <= MAX_PER_TEST_TIMEOUT`) and no floor, so a commit that set
the per-test timeout to 1 second — which would make the suite unrunnable — would
pass this guard. Handed to **FU-08** together with F-06.

---

## Unhandled errors

### The named instance

`frontend/src/features/media-management/__tests__/MediaAssets.test.tsx`'s
**"allows file selection and triggers upload"** is the known instance and the
reason this stratum exists: on the jsdom 30 branch (PR #34)
`URL.createObjectURL` raised inside the handler the case exercises and the case
still **passed** — the run only went red because Vitest reports unhandled errors
separately from assertion failures.

**On `master` today it does not leak.** The instrumented suite-wide run below
covers it and recorded nothing against it, and `S2-MAND-FE-media` shows the case
is not inert either: making the mocked `uploadsApi.uploadPhoto` reject reddens
exactly that case (`8 tests: 7 passed, 1 failed`). So the case is load-bearing
and the leak was a property of the jsdom 30 branch, not of this tree.

**Would the suite have noticed without Vitest's separate report?** For the
historical instance: **no** — the case passed. That is the whole of ER7, and the
probe below measures it on today's shipped configuration directly.

### The transient probe (created, run, deleted)

Created at `frontend/src/test/__audit_probe__/leak.test.ts` — a directory already
excluded from coverage by `coverage.exclude: ["src/test/**"]`, so it cannot move
the coverage baseline. Two cases: one throws inside a DOM `click` listener the
case itself dispatches; one leaves a `Promise.reject` unhandled. Both end with an
assertion that holds.

Both invocations were run **from `frontend/`, against the shipped
`vitest.config.ts` and the shipped `test` script, unchanged**:

```
$ npm run test -- src/test/__audit_probe__/leak.test.ts
…
 Test Files  1 passed (1)
      Tests  2 passed (2)
     Errors  2 errors
exit=1

$ npx vitest run src/test/__audit_probe__/leak.test.ts
…
 Test Files  1 passed (1)
      Tests  2 passed (2)
     Errors  2 errors
exit=1
```

Collected counts proving the probe really was collected: **1 file / 2 cases**
(`Test Files 1 passed (1)`, `Tests 2 passed (2)`). The second invocation
cross-checks that `npm` is not masking the runner's code: both are **exit 1**.

**The answer to ER8, measured.** The shipped configuration *fails the run* on a
leaked error, and **passes the case that leaked it**. `Tests 2 passed (2)`
alongside `Errors 2 errors` is exactly the shape that let the PR #34 instance
through: a reader of the per-case report sees green.

The error text Vitest printed for the rejection, quoted because it is the
evidence that the error was attributed to a *file* and only guessed at a case:

```
⎯⎯⎯⎯ Unhandled Rejection ⎯⎯⎯⎯⎯
Error: APRAS-111 probe: unhandled rejection
 ❯ src/test/__audit_probe__/leak.test.ts:19:25
…
This error originated in "src/test/__audit_probe__/leak.test.ts" test file. It doesn't mean the error was thrown inside the file itself, but while it was running.
The latest test that might've caused the error is "leaks an unhandled promise rejection". It might mean one of the following:
- The error was thrown, while Vitest was running this test.
- If the error occurred after the test had been completed, this was the last documented test before it was thrown.
```

### The proposed configuration, and the probe re-run under it

Because the run does **not** fail the case that leaked, a configuration is
proposed. It is **described, not committed**: implementing it in
`frontend/vitest.config.ts` is **FU-12**.

The proposal is one extra setup file appended to `setupFiles`. Its whole content
(proved in `<scratchpad>/fail-on-leak.setup.ts`):

```ts
import { afterEach, beforeEach } from "vitest";

let leaked: string[] = [];
const push = (what: unknown) => {
  leaked.push(String((what as { message?: string })?.message ?? what));
};

if (typeof window !== "undefined") {
  window.addEventListener("error", (event) => push(event.error ?? event.message));
  window.addEventListener("unhandledrejection", (event) =>
    push((event as PromiseRejectionEvent).reason),
  );
}
process.on("uncaughtException", push);
process.on("unhandledRejection", push);

beforeEach(() => {
  leaked = [];
});

afterEach(() => {
  if (leaked.length === 0) return;
  const seen = leaked.join("; ");
  leaked = [];
  throw new Error(
    `this case leaked ${seen.split("; ").length} unhandled error(s): ${seen}`,
  );
});
```

Proof it works — the same probe, under a scratchpad config carrying it
(`<scratchpad>/vitest.proposal.config.ts`, which is the shipped config plus that
one setup file):

```
$ cd frontend && npx vitest run --config <scratchpad>/vitest.proposal.config.ts src/test/__audit_probe__/leak.test.ts
 ❯ src/test/__audit_probe__/leak.test.ts (2 tests | 2 failed) 17ms
     × leaks a synchronous error out of a DOM event handler 4ms
     × leaks an unhandled promise rejection 11ms

 FAIL  src/test/__audit_probe__/leak.test.ts > APRAS-111 leak probe > leaks a synchronous error out of a DOM event handler
Error: this case leaked 1 unhandled error(s): APRAS-111 probe: leaked from a click handler

 FAIL  src/test/__audit_probe__/leak.test.ts > APRAS-111 leak probe > leaks an unhandled promise rejection
Error: this case leaked 1 unhandled error(s): APRAS-111 probe: unhandled rejection

 Test Files  1 failed (1)
      Tests  2 failed (2)
exit=1
```

`Tests 2 failed (2)`, each failure naming the case that leaked. That is the
behaviour ER8 asks for. **One caveat FU-12 must carry:** the handlers consume the
errors, so Vitest's own separate `Errors 2 errors` report no longer appears. The
information is not lost — it has moved into the case failure — but the proposal
must be adopted knowingly, and a `--reporter` that surfaced the old block would
no longer show it.

### Removal of the probe — verified absence

The probe was created twice (once for the shipped-config and proposal runs, once
as the recorder's positive control) and deleted both times. Its restore rule is
**deletion, not `cmp`**: the audit authored the file, so there is no pristine
copy to compare against and step 5 of the mutation protocol does not apply.

```
$ rm -f frontend/src/test/__audit_probe__/leak.test.ts && rmdir frontend/src/test/__audit_probe__
$ test -e frontend/src/test/__audit_probe__ && echo "STILL PRESENT" || echo "verified absent"
verified absent
$ git status --porcelain -- frontend/src/test/
$ echo "porcelain-lines=$(git status --porcelain -- frontend/src/test/ | wc -l)"
porcelain-lines=0
```

The parent directory `frontend/src/test/__audit_probe__/` was created by the
audit and was removed too. The porcelain diff in *Census and method* is the
backstop: `porcelain.after` is byte-identical to `porcelain.before` and carries
no `frontend/src/test/__audit_probe__` entry. **This file is deleted even on an
abort** — the step-6 abort rule exists to protect work the audit did not author,
and this file is nobody else's work; if deletion itself had failed, that would
have been reported as the abort with the path named. It did not fail.

### The instrumented suite-wide run

`frontend/vitest.config.ts` was **not modified**. The instrumented run uses
`<scratchpad>/vitest.audit.config.ts`, which imports the shipped file and
`mergeConfig`s exactly one change.

Diff against the shipped file — the single delta:

```
  test: {
-   setupFiles: "./src/test/setup.ts",
+   setupFiles: [
+     "./src/test/setup.ts",
+     "<scratchpad>/audit-recorder.setup.ts",
+   ],
  }
```

plus `root: "/Users/heitor/workspace/apras/frontend"`, which the spec prescribes
because the config lives outside the project.

#### The bare load: observed, not assumed

The spec asserts neither outcome and requires the audit to record what its own
environment produced. **Note first:** this scratchpad is shared across sessions
and already contained a `node_modules` symlink and a `{"type":"module"}`
`package.json` dated 2026-10-01 17:02, left by an earlier session. Both were
moved to `<scratchpad>/preexisting/` before the bare attempt, so that the attempt
really was bare.

**Attempt 1 — no symlink, no `package.json`. It failed.** Verbatim:

```
$ cd frontend && npx vitest list --config <scratchpad>/vitest.audit.config.ts
…/scratchpad/vitest.audit.config.ts (3:42) [UNRESOLVED_IMPORT] Could not resolve 'vitest/config' in …/scratchpad/vitest.audit.config.ts
 3 │ import { defineConfig, mergeConfig } from "vitest/config";
   │                                           ───────┬───────
   │                                                  ╰───────── Module not found, treating it as an external dependency

failed to load config from /private/tmp/.../scratchpad/vitest.audit.config.ts

⎯⎯⎯⎯⎯⎯⎯ Collect Error ⎯⎯⎯⎯⎯⎯⎯⎯
Error: Cannot find module 'vitest/config'
Require stack:
- /private/tmp/.../scratchpad/vitest.audit.config.ts
- /Users/heitor/workspace/apras/frontend/node_modules/vite/dist/node/chunks/node.js
  code: 'MODULE_NOT_FOUND',
list-exit=1
```

**Remedy 1, created because that error forced it** — a resolution failure, which
is the first of the two remedies the spec names:

```
$ ln -s /Users/heitor/workspace/apras/frontend/node_modules <scratchpad>/node_modules
```

**Attempt 2 — symlink, still no `package.json`. It failed differently.**
Verbatim:

```
failed to load config from /private/tmp/.../scratchpad/vitest.audit.config.ts

⎯⎯⎯⎯⎯⎯⎯ Collect Error ⎯⎯⎯⎯⎯⎯⎯⎯
TypeError: (0 , _Users_heitor_workspace_apras_frontend_node_modules__tailwindcss_vite_dist_index_mjs.default) is not a function
    at Object.<anonymous> (/private/tmp/.../scratchpad/vitest.audit.config.ts:32:212)
    at Module._compile (node:internal/modules/cjs/loader:1761:14)
    at _require.extensions.<computed> [as .js] (file:///Users/heitor/workspace/apras/frontend/node_modules/vite/dist/node/chunks/node.js:35016:42)
list-exit=1
```

**Remedy 2, created because that error forced it** — a CJS-interop failure, the
second remedy the spec names:

```
$ printf '{"type": "module"}' > <scratchpad>/package.json
```

**Attempt 3 — both remedies present. It loaded**, `list-exit=0`, 2505 output
lines (which at that moment still included the probe file).

So in this environment the bare load does **not** work and both remedies were
needed; each is recorded above together with the quoted error that forced it.
Neither is a counterfactual.

#### Honoured-config proof

The appended recorder was made to `throw` once at module scope, and the run
reported that error with its source line:

```
$ cd frontend && npx vitest run --config <scratchpad>/vitest.audit.config.ts src/lib/__tests__/contrast.test.ts
Error: APRAS-111 honoured-config proof: this setup file was loaded
 ❯ <scratchpad>/audit-recorder.setup.ts:41:7
     41| throw new Error("APRAS-111 honoured-config proof: this setup file was …
 Test Files  1 failed (1)
      Tests  no tests
exit=1
```

The throw was then removed and the file `cmp`-verified identical to the copy
taken before it was added. The derived config is genuinely honoured, not silently
ignored.

#### Parity gate — run before any conclusion is drawn

Both from `frontend/`, with the probe absent:

| invocation | collected files | collected cases |
|---|---|---|
| `npx vitest list` | **188** | **2503** |
| `npx vitest list --config <scratchpad>/vitest.audit.config.ts` | **188** | **2503** |

**Verdict: match.** The sorted file lists are also byte-identical
(`diff` of the two `awk`-extracted file columns produced no output). The spec
records 188 / 2496 as measured on 2026-10-01; the case count here is 2503, seven
higher, from other tasks' work in the intervening day — and crucially it is the
*same* on both sides, which is what the gate asks. The instrumented results below
are therefore reported as statements about the **shipped** configuration.

#### The instrumented run, and the positive control that makes its result meaningful

```
$ cd frontend && APRAS_111_LEAK_LOG=<scratchpad>/leaks.jsonl \
    npx vitest run --config <scratchpad>/vitest.audit.config.ts
 Test Files  188 passed (188)
      Tests  2503 passed (2503)
   Duration  31.60s
exit=0
$ wc -l <scratchpad>/leaks.jsonl
wc: …/leaks.jsonl: open: No such file or directory      # the recorder never appended a line
```

**Zero further instances.** Across all 188 files and 2503 cases, no error reached
`window.onerror` or `unhandledrejection`, and the run reported no `Errors` block
of its own either.

A zero result from an instrument is exactly the kind of claim this task exists to
distrust, so the recorder carries a **positive control**. The probe was
re-created and run under the identical instrumented config:

```
$ cd frontend && APRAS_111_LEAK_LOG=<scratchpad>/leaks.control.jsonl \
    npx vitest run --config <scratchpad>/vitest.audit.config.ts src/test/__audit_probe__/leak.test.ts
 Test Files  1 passed (1)
      Tests  2 passed (2)
$ cat <scratchpad>/leaks.control.jsonl
{"file":"…/src/test/__audit_probe__/leak.test.ts","case":"APRAS-111 leak probe > leaks a synchronous error out of a DOM event handler","leaked":["APRAS-111 probe: leaked from a click handler"]}
{"file":"…/src/test/__audit_probe__/leak.test.ts","case":"APRAS-111 leak probe > leaks an unhandled promise rejection","leaked":["APRAS-111 probe: unhandled rejection"]}
```

The recorder writes, and attributes each leak to the **case** that caused it. The
zero on the full suite is a measurement, not a silent failure.

| instance | would the suite have noticed without Vitest's separate unhandled-error report? |
|---|---|
| `MediaAssets.test.tsx` > "allows file selection and triggers upload" — the historical PR #34 leak | **No.** The case passed; only the separate `Errors` block turned the run red. Does not reproduce on `master` today. |
| any further instance | **None found.** 188 files / 2503 cases instrumented, zero leaks recorded, with the recorder's positive control above proving the instrument fires. |

---

## Examined and kept

Tests examined and kept despite looking redundant, vacuous or self-mocking, each
with the reason and the row that measured it.

### EK-01 — `test_the_thirty_first_request_inside_a_minute_is_still_a_200`

`backend/tests/test_public_project_report.py:356`. Both mutations of
`REQUESTS_PAST_THE_DECLINED_LIMIT` (`S1-BE-DECLINED_LIMIT-weak`, 31 → 1;
`-strong`, 31 → 61) leave the module green at `13 passed`. **Kept**: the case's
own comment at lines 371–378 states that the loop proves nothing — "`conftest.py`
sets `app.state.limiter.enabled = False` for the whole suite, so it would pass
unchanged if a `@limiter.limit` were added to this route tomorrow" — and the
load-bearing half is an AST assertion over the handler's decorators, scoped to
that handler since APRAS-104. The number is documentation; the test says so
itself. Nothing to repair.

### EK-02 — `ProjectsFeature.test.tsx` and the refused-file claim

`S2-FE-05` keeps a refused cover photo in the intent
(`cover.setFile(picked)` in the invalid-format branch) and
`ProjectsFeature.test.tsx` stays green at `11 tests: 11 passed`. **Kept**: the
claim *is* asserted, by a named sibling. `S2-FE-05b` runs the same mutation
against `src/features/project-management/__tests__/ProjectCoverPhoto.test.tsx`
and reddens `the obra cover photo is chosen as a file refuses a non-image
locally, naming the accepted formats`. The prose at `ProjectFormModal.tsx:149` is
protected; the stride simply landed on the module that is not the one protecting
it.

### EK-03 — `BrandedEntryLogin.integration.test.tsx`'s settle comment

`S2-FE-07` removes `clearActingTenantId()` from the per-run reset: green. That
mutation **does not discriminate** the comment's claim ("the acting tenant was
resolved from it. Measured here, never before"), because a stale value and a
resolved value are the same value here. `S2-FE-07b` is the discriminating run:
it clears the acting tenant immediately *before* `resolveActingTenantId` in
`AuthContext.tsx:39`, so the settle at line 325 can only pass if the resolution
really ran — and it stays green (`3 tests: 3 passed`). **Kept**: the resolution
runs, the settle is real.

### EK-04 — `test_clock.py`'s `session.expire_all()`

`S2-BE-02` is kept in the ledger as a non-discriminating mutation and is
explicitly labelled as such on its row. The discriminating result is F-08. The
`expire_all()` call itself is **kept**: removing it does not break anything
today, but it is the only thing standing between the case and the identity map
once the case is repaired per F-08.

### EK-05 to EK-14 — all ten S4 candidates

Every one of the ten S4 mutations stayed green, which is the **expected** outcome:
`vi.mock` replaces the specifier, so breaking the real module cannot be observed.
None is classified class 3, and the reason is the same in all ten cases — the
mocked module is a **seam**, not the subject:

| row | spec | mocked | why it is kept |
|---|---|---|---|
| `S4-FE-01` | `src/api/__tests__/finance.test.ts` | `../client` | subject is `api/finance.ts`; `api/client.ts` is the HTTP seam. `describe("finance api client")` names the subject, not the mock |
| `S4-FE-02` | `src/api/__tests__/packages.test.ts` | `../client` | same shape |
| `S4-FE-03` | `src/api/__tests__/residents.test.ts` | `../client` | same shape |
| `S4-FE-04r` | `AccessControlPage.test.tsx` | `api/accessControl` | subject is the page's rendering and gating; the api module is the data seam |
| `S4-FE-05` | `DocumentCenter.test.tsx` | `api/documents` | titles are all about rendering, filtering and role gating; no title claims the api module's behaviour |
| `S4-FE-06` | `Infractions.test.tsx` | `api/infractions` | same shape |
| `S4-FE-07` | `LotsPage.test.tsx` | `api/lots` | same shape |
| `S4-FE-08r` | `PurchaseRequestDetailModal.test.tsx` | `api/purchases` | same shape; this spec's own comment at line 26 already discusses what the automock covers |
| `S4-FE-09` | `TenantProfilePage.brand.test.tsx` | `api/client` | subject is the brand-colour section; `api/client.ts` is the HTTP seam |
| `S4-FE-10r` | `useVisitors.test.tsx` | `api/visitors` | titles such as `useCreateVisitor calls createVisitor API` claim the **call**, and verifying the call against the mock is exactly what they do — the claim is honest |

**What this stratum did find** is that the spec's pre-stride filter is noisy: it
matches on the mocked specifier's basename appearing anywhere in any title, so
`client` matches `describe("finance api client")` and `documents` matches
`"renders DocumentCenterPage with folders and documents table"`. A sharper filter
— the basename appearing in a title *as the grammatical object of a verb like
"exercises"/"calls"/"uses"*, or the mocked module being the one the spec file is
named after — is handed to **FU-06**.

### EK-15 — the three invalidated S4 rows

`S4-FE-04`, `-08` and `-10` are **kept in the ledger** rather than deleted from
it, even though they measured nothing (0 tests collected, exit 1, because the
mutation left the file syntactically invalid). Keeping them is the point: a row
that collected nothing looks, in a summary, exactly like a row whose mutation
nothing caught. Their replacements are `-04r`, `-08r`, `-10r`.

Because that is exactly the confusion they exist to warn about, each of the three
row bodies carries its own **`!! INVALIDATED`** banner in the *Rows* section, and
each has its *Reddened* / *Was it among the reddened?* fields replaced by **not
measurable** and **question does not apply**, so the row cannot be read as an
adjudication by anyone who arrives at it directly rather than through this entry
or through the `r` suffix on its sibling. None of the three supports a class, and
none counts toward S4's budget of 10.

---

## Coverage and lint baselines

From exactly these commands, with their output summary lines:

**`cd backend && SECRET_KEY=test uv run pytest`** — the full-suite command, which
keeps `pytest.ini`'s inherited `--cov=app --cov-fail-under=90` because measuring
it is the point (this is the sole exception to the `--no-cov` rule):

```
TOTAL                                         11716    668    94%
Required test coverage of 90% reached. Total coverage: 94.30%
==== 1 failed, 4156 passed, 38 skipped, 6332 warnings in 235.18s (0:03:55) =====
exit=1
```

The one failure is `FAILED tests/test_bcrypt_cost.py::test_passlib_is_not_installed`,
the environment drift documented under *Environment*; the 38 skips are
`test_migrations_postgres.py`. **Backend coverage baseline: 94.30%** (11716
statements, 668 missed).

**`cd frontend && npm run test:coverage`**:

```
 Test Files  188 passed (188)
      Tests  2503 passed (2503)
All files          |    91.5 |    85.28 |   87.83 |   92.21 |
exit=0
```

**Frontend coverage baseline: 91.5% statements / 85.28% branches / 87.83%
functions / 92.21% lines**, against `vitest.config.ts` thresholds of 80 / 76 / 78
/ 80.

**`cd frontend && npm run lint`** — error and file counts only:

```
✖ 370 problems (368 errors, 2 warnings)
exit=1
```

**Lint baseline: 368 errors and 2 warnings across 77 files** (counted as file
headers in the output). The spec recorded ~375 errors across 64 files on
2026-10-01; this is the audit's own measurement. Every follow-up below inherits
**"no worse than this base"**, never "zero repo-wide".

**Because this task changes no test, there is no "after" to report here.** The
rule is carried into the follow-ups instead: each proposal below quotes this
baseline and requires the same three commands be re-run after its change, with
any drop explained **line by line** rather than accepted as a side effect.

**Per proposed deletion, which production lines is the test the sole cover for?**
**Not applicable — this audit proposes no deletions** (see the preamble to
*Findings*). Three of the sixteen findings are the reverse case: production code
with *no* cover at all (`SLUG_MAX_BASE_LENGTH`, `MAX_REQUEST_ITEMS`,
`MAX_QUOTE_ITEMS`, `MIN_JUSTIFICATION_LENGTH`), where the follow-up **adds**
cover and the baselines can only rise.

---

## Follow-up proposals

Every proposal below must report against the baseline quoted in *Coverage and
lint baselines* — backend 94.30%, frontend 91.5 / 85.28 / 87.83 / 92.21, lint 368
errors / 2 warnings / 77 files — and must explain any drop **line by line**.

**Sizing the remainder sweep from the hit rate S3 actually observed.** S3 mutated
20 candidates per suite and found **one** finding in 40 (F-16, in the backend
suite), a realised hit rate of **1 in 40 = 2.5%**. Extrapolated over the 1088
unexamined S3 candidate lines (557 backend + 531 frontend) that is an expected
**~27 further findings**, which is far too many to carry as a single task.
FU-13 therefore proposes the remainder sweep in **four parts of ~270 candidate
lines each**, sized so that each part's expected yield (~7 findings) fits one
PR-sized remediation. S2's observed rate is higher — 10 findings in 24 stride
mutations plus mandatory modules — so FU-14 sizes the S2 remainder more
conservatively.

| id | proposal | tests / code it covers | class | baseline it must report against |
|---|---|---|---|---|
| **FU-01** | Resync `backend/.venv` so the undeclared `passlib 1.7.4` is removed, and make `test_passlib_is_not_installed` green locally as it already is in CI. Repairing the environment is explicitly a follow-up, not part of this audit. | `tests/test_bcrypt_cost.py::test_passlib_is_not_installed` | n/a — environment drift, not a test defect | all three |
| **FU-02** | Pin `frontend/vitest.config.ts`'s `test.coverage.thresholds` from a test, the way `test_suite_hygiene.py` pins `pytest.ini`'s `timeout`. Measured gap: no spec parses the file. | `frontend/vitest.config.ts:41-46` | 1 (no mutation taken — ER14 forbids editing the file, so this is read-only evidence) | all three |
| **FU-03** | Sweep the deferred **anonymous numeric assertions**: 1674 backend lines and 454 frontend lines, counted by the two pinned commands in *Census and method*. They are the `assert … == 7` / `toHaveLength(7)` shape that S1 deliberately excluded. | the two counted populations | mixed; to be determined per case | all three |
| **FU-04** | Build a per-case **positive control** for absence assertions, so an S3 sweep can tell "the fixture arrived empty" from "the fixture arrived full and contained nothing forbidden" — the limitation this audit states under the S3 mutation form. | S3 methodology | n/a | all three |
| **FU-05** | Re-run the S3 sweep over `backend/tests/test_migrations_postgres.py` on a Postgres-backed runner. 38 cases were skipped here and are unexamined; candidate indices 87–98 of the backend S3 list all fall inside it. | `test_migrations_postgres.py` (38 cases) | unknown — not examinable without Postgres | all three |
| **FU-06** | Sharpen the S4 pre-stride filter. The basename filter admits `client` matching `describe("finance api client")`; all ten selected candidates proved to be legitimate seams. Re-sweep the 44 filtered candidates (and the 225 excluded) under a filter that looks for a title claiming the mocked module's *behaviour*. | the 269 `vi.mock(` sites | 3, where any are found | all three |
| **FU-07** | Add the four missing threshold tests and repair the one mis-named constant: `SLUG_MAX_BASE_LENGTH`, `MAX_REQUEST_ITEMS`, `MAX_QUOTE_ITEMS`, `MIN_JUSTIFICATION_LENGTH`, and `GRAPHIC_FLOOR`'s unenforced floor. | F-01, F-02, F-03, F-04, F-05 | 1 (F-01–F-05) | all three; coverage can only rise, so any drop is a defect in the change |
| **FU-08** | Pin `backend/pytest.ini`'s `--cov-fail-under` from `test_suite_hygiene.py`, and add the missing **floor** on its `timeout` so a commit cannot set the per-test cap to 1 second. | F-06, plus the `S1-CFG-pytest_timeout-strong` asymmetry | 1 | all three |
| **FU-09** | Repair the six backend prose claims whose named case does not hold them: `matrix_world.py`'s isolation mechanism, `test_clock.py`'s stored-column claim, `test_occurrences.py`'s `[]`-never-`null`, `test_project_report.py`'s clock default, `test_project_report_branding.py`'s §B (including bringing the docstring to two rungs), `record_parity_baseline.py`'s relative-path invariant, `test_branding.py`'s alarm claim, and `voting_helpers.py`'s CPF-pool guard. | F-07, F-08, F-09, F-10, F-11, F-12, F-15, F-16 | 1 (F-07, F-08, F-09, F-11, F-12, F-16); 2 (F-10, F-15) | all three |
| **FU-10** | Pin `SubscriptionPage`'s payload contract: courtesy and override rows are never sent and never dropped. 513 cases across 51 files currently miss it. | F-13 | 1 | all three |
| **FU-11** | Add a `tsc --noEmit` gate so prose contracts inside type declarations are checkable at all; Vitest transpiles without type-checking, so no runtime case can observe a change to an `interface`. | F-14 | 1 | all three; expect new lint/type findings, to be reported against the 368/2/77 base |
| **FU-12** | Implement the ER8 configuration in `frontend/vitest.config.ts`: the `fail-on-leak` setup file quoted in *Unhandled errors*, proved there against the transient probe. Must carry the stated caveat that the handlers consume the errors and Vitest's separate `Errors` block no longer appears. | the whole frontend suite | n/a — a harness change | all three; the suite is green today, so the change must leave it green |
| **FU-13** | Sweep the **S3 remainder** in four parts of ~270 candidate lines each (557 backend + 531 frontend unexamined), sized from the 2.5% hit rate this audit observed. | the S3 remainder | 1, expected | all three |
| **FU-14** | Sweep the **S2 remainder**: 275 backend + 303 frontend candidate lines unexamined. Sized more conservatively than FU-13 because S2's observed rate was higher. | the S2 remainder | 1 and 2, expected | all three |
| **FU-15** | Adopt a mutation-testing tool (`mutmut` for the backend, Stryker for the frontend) so this sweep does not have to be manual again. This audit is deliberately manual and targeted; adopting a tool is its own deliverable. | both suites | n/a | all three |
| **FU-16** | Answer the backend analogue of the frontend unhandled-error question: a pytest `filterwarnings` / `-W error` policy. The full-suite baseline run emits **6332 warnings**; none of them fails anything. | the backend suite | n/a | all three |

---

## What this audit did not cover

Stated verbatim from the spec's "Not in scope", so the next auditor does not
assume it was done:

- **Any lasting edit to a test file or to production code.** Mutations and probe
  files are temporary and removed; the audit's own lasting diff is the new
  document only.
- **Every case outside the strata, and every stratum candidate not selected by
  the sampling rule.** These get no mutation and no judgement. They are reported
  in *Census and method* as **counts measured during the audit** — collected
  total, candidate-set size, mutated, read-only judged, remainder — never as a
  percentage estimated in advance.
- **Exhaustive duplicate detection.** Redundancy is only judged where a stratum
  already put two tests side by side.
- **Anonymous numeric literals in assertions** (the `assert … == 7` /
  `toHaveLength(7)` shape). S1 covers *named* thresholds only; the anonymous
  population is counted by a pinned command (1674 backend, 454 frontend) and
  handed to a follow-up (FU-03).
- **A backend analogue of the frontend unhandled-error question** (pytest
  `filterwarnings`/`-W error` policy). The audit notes it (FU-16); sweeping it is
  a separate task.
- **Mutation-testing tooling** (`mutmut`, Stryker). Adopting a tool is its own
  deliverable; this audit is manual and targeted (FU-15).
- **Any production database or credentialed API call.** None was made. The one
  Postgres-dependent module in the suite was skipped by its own marker and is
  recorded as not examined.

Three further gaps this audit discovered about itself, recorded in the same
spirit:

- The S3 mutation form detects an absence assertion that never executes or never
  reaches its population. It does **not** separate "the fixture arrived empty"
  from "the fixture arrived full and held nothing forbidden" (FU-04).
- `frontend/vitest.config.ts`'s coverage thresholds were judged **read-only**,
  with no mutation behind the judgement, because expected result 14 of this task
  forbids editing that file (FU-02).
- `backend/tests/test_migrations_postgres.py`'s 38 cases are unexamined for want
  of a Postgres instance (FU-05).

---

## Appendix — final tree verification

Re-run after this document was written and staged, with the staging visible:

```
$ git status --porcelain --untracked-files=all > <scratchpad>/porcelain.final2
$ diff <scratchpad>/porcelain.before <scratchpad>/porcelain.after
$ echo $?
0
$ diff <scratchpad>/porcelain.before <scratchpad>/porcelain.final2
0a1
> A  docs/audits/APRAS-111-test-suite-audit.md
$ comm -13 <(sort <scratchpad>/porcelain.before) <(sort <scratchpad>/porcelain.final2) | grep -E "backend/|frontend/"
NONE
$ git status --porcelain --untracked-files=all -- backend frontend
?? backend/scripts/sync_obras_from_drive.py
```

`porcelain.before` and `porcelain.after` — the pair the tree-safety contract is
computed over, captured before the first mutation and after the last restore —
are **byte-identical**. The one entry that appears after the document was written
is the document itself. The only entry under `backend/` or `frontend/` is
`?? backend/scripts/sync_obras_from_drive.py`, which is present in
`porcelain.before` too, is deliberately never committed, and was not touched.
