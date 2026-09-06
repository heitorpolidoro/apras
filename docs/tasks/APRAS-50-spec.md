# APRAS-50 — Rodar os testes de migração em Postgres real no CI

An infrastructure task, not a feature: `backend/tests/test_migrations_postgres.py`
(53 cases) has never executed on CI, and this makes it execute, keeps it
executing, and proves — with one green CI run and one deliberately red one,
both before the task merges — that the guard works.

**No file under `backend/app/` changes.** Nothing about the product changes.

**Where the evidence lives.** This project does not ship through GitHub pull
requests — every Meridian-era task landed as a local merge or a direct commit on
`master`, and the last non-dependabot PR is #28 (2026-06-12). So nothing in this
spec asks for a "PR body".

**The one checkable artifact is
`.meridian/reports/APRAS-50-inprogress-0.md`.** Every run URL, duration, skip
count and justification this spec calls for is recorded there, and that file is
what the Expected Results name. It is the only record that exists at the moment
the ERs are checked: the pipeline commits *after* QA approves, so no commit,
message body or tag is available to any check this task can state.

**The commit body is a hand-off, not a condition.** Because `.meridian/` is
gitignored and the reports directory is trimmed to its 50 most recent files, the
durable copy of that evidence belongs in the body of the task's commit message.
Writing it there is the **orchestrator's** obligation when it commits the
approved work — it carries the report's `Proof of failure` section and the A/B/C
durations across into the commit body, exceptionally for this task, since the
pipeline's default commit is a bare subject line. No Expected Result depends on
it, and QA is never asked to look for it.

Where a section below says "record X", it means: in
`.meridian/reports/APRAS-50-inprogress-0.md`, which the orchestrator then carries
into the commit body.

---

## 0. What is broken today, and the evidence

`backend/tests/test_migrations_postgres.py` opens with a module-level

```python
pytestmark = pytest.mark.skipif(not TEST_POSTGRES_URL, reason=...)
```

and `.github/workflows/ci.yml` has **no `services:` block** and never sets
`TEST_POSTGRES_URL`. So on every push and every PR since APRAS-27 the module
has silently reported *53 skipped* inside an otherwise green
`Backend Tests` job. A skip is invisible in a green check.

What that cost, concretely: three APRAS-40 blockers — a tenant-scoped table not
registered in the scoped-table set, an unnamed FK, a stale `PERMISSIONS` pin —
were caught **only because a reviewer ran the module by hand**. Recorded in
`docs/suggestions-log.md` (entry `(code review r2, backlog)`, 2026-09-03; it
says 45 cases, the module has since grown to 53).

The module is well built for this: every fixture (`migrated_pg_engine`,
`isolated_pg_engine`, `pg_engine_at_0018`, `pg_engine_at_0027`,
`pg_engine_at_0031`) does `DROP SCHEMA public CASCADE` / `CREATE SCHEMA public`
and re-runs the Alembic chain, so it needs nothing but an empty, disposable,
UTF-8 Postgres it is allowed to destroy. Supplying exactly that is the whole
task.

---

## 1. The workflow change

### 1.1 A separate job, not a bigger `backend` job

Add one job to `.github/workflows/ci.yml`, alongside `backend` and `frontend`:

| | |
|---|---|
| id | `backend-migrations` |
| name | `Backend Migration Tests (Postgres)` |
| runs | `tests/test_migrations_postgres.py` only, against the service Postgres |

Why a separate job rather than adding `services:` to `backend`:

1. **ER-4's budget.** Each `isolated_pg_engine` case re-runs the whole 36-step
   chain **twice** (setup and teardown), each run a fresh `alembic` subprocess.
   Roughly 30 of the 53 cases do this. Folding it into `backend` would add that
   entire cost to the job every change waits on; as its own job it runs in
   parallel and the `Backend Tests` job's duration is unchanged by
   construction.
2. **A legible signal.** "Backend Migration Tests (Postgres) ✗" names the
   failure class before anyone opens a log.
3. **The coverage gate and Sonar stay untouched.** `pytest.ini` carries
   `addopts = --cov=app --cov-fail-under=90`; a run of one Postgres-only module
   cannot meet 90 % and must not be asked to. The `backend` job keeps producing
   the single `coverage.xml` / `test-results.xml` pair the `sonarcloud` job
   downloads.

`sonarcloud`'s `needs: [backend, frontend]` is **not** extended — the new job
feeds it nothing, and gating the scan on it would only slow the scan down.

The new helper of §2 is invisible to Sonar by construction:
`sonar-project.properties` sets `sonar.sources=backend/app,frontend/src`, so
`backend/scripts/assert_no_skips.py` is neither analysed nor counted against the
new-code coverage gate. It is a CI helper, not product code, and "a new
uncovered Python file" is not an objection that applies to it.

### 1.2 The manual trigger

`ci.yml` currently triggers only on `push` and `pull_request` against `master`,
which means no run can be produced on any other ref. Add a third trigger:

```yaml
on:
  push:
    branches: [ master ]
  pull_request:
    branches: [ master ]
  workflow_dispatch:
```

This is a **deliverable of this task in its own right**, not scaffolding for the
proof: it makes `gh workflow run ci.yml --ref <branch>` possible for every future
task in a repository that does not open PRs, at the cost of one line and no
change to when CI runs by itself. Nothing else in the `on:` block changes — in
particular the `push` filter stays `[ master ]`, so merging this does not start
running CI on every branch.

**No workflow in `.github/workflows/` triggers on a push to a non-`master`
branch**, so nothing in this task — and nothing in §4's throwaway branch — can
fire a production migration or any other automatic run. All nine files were
checked, not sampled: `ci.yml` and `migrate.yml` are `push`/`pull_request` on
`[ master ]`; `release.yml` is `release: types: [published]`;
`gemini-invoke.yml`, `gemini-plan-execute.yml`, `gemini-review.yml` and
`gemini-triage.yml` are `workflow_call`; `gemini-dispatch.yml` is
`pull_request_review*` / issue-comment shaped; `gemini-scheduled-triage.yml` is
`schedule` plus `pull_request` on `main` / `release/**`, branches this repository
does not have. Re-verify `migrate.yml`'s single `push: branches: [ master ]` line
before pushing anything, and record the check.

### 1.3 The service container

```yaml
  backend-migrations:
    name: Backend Migration Tests (Postgres)
    runs-on: ubuntu-latest
    timeout-minutes: 20
    env:
      SECRET_KEY: "test-secret-key-for-ci"
      TEST_POSTGRES_URL: "postgresql://postgres:postgres@localhost:5432/apras_test"
      POSTGRES_URL: "postgresql://postgres:postgres@localhost:5432/apras_test"

    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: apras_test
          POSTGRES_INITDB_ARGS: "--encoding=UTF8 --locale=C"
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U postgres -d apras_test"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
```

Every element of that block is load-bearing:

- **`postgres:16-alpine`** — the *same image tag* as `docker-compose.yml`'s `db`
  service and the same major as AGENTS.md's "PostgreSQL 16" (Vercel Postgres in
  production). Testing migrations on a major the project does not run would
  prove the wrong thing. If one of those three moves, all three move together.
- **`POSTGRES_INITDB_ARGS: "--encoding=UTF8 --locale=C"`** — the database must
  be UTF-8. Migration `0028_add_tenant_and_membership` seeds
  `DEFAULT_TENANT_NAME = "Condomínio Padrão"` (line 77), a non-ASCII literal;
  on a non-UTF-8 cluster it is a corruption or an error rather than a seed, and
  the whole chain is unusable from `0028` on. The `postgres:16-alpine` image
  already sets `ENV LANG en_US.utf8` so that its `initdb` defaults to UTF8, so
  this argument is not repairing a broken default — it **states the requirement
  in the workflow instead of inheriting it from an image tag**, and survives an
  image whose `LANG` changes. `--locale=C` is paired with it so collation is
  fixed and independent of which locales the image happens to carry, rather than
  varying with the base image. The `SHOW server_encoding` step below makes the
  whole question self-checking rather than a matter of belief.
- **`ports: - 5432:5432`** — the job's steps run on the runner host, not inside
  a container, so the service must be reachable on `localhost`.
- **health check** — `pg_isready` gates the first step on the server accepting
  connections. Without it the module's `create_engine(...)` fails, the
  `migrated_pg_engine` fixture calls `pytest.skip("Could not reach
  TEST_POSTGRES_URL ...")`, and the job goes **green with 53 skips** — exactly
  today's bug, reintroduced by a race. §2's guard is the second line of defence
  against precisely this.
- **`SECRET_KEY`** — `tests/conftest.py` imports the app, whose settings require
  it. Same value as the `backend` job.
- **`POSTGRES_URL`** — `app/db.py` builds an engine from `settings.database_url`
  at import time (it never connects during this module). Pointing it at the
  same throwaway database rather than at the `backend` job's non-existent
  `.../nexdom` means any accidental connection lands somewhere harmless.
  `tests/test_migrations_postgres.py::_alembic` overrides `POSTGRES_URL` with
  `TEST_POSTGRES_URL` for every subprocess anyway, so the two values being
  equal keeps that override a no-op instead of a surprise.

### 1.4 The steps

```yaml
    steps:
    - name: Checkout code
      uses: actions/checkout@v6

    - name: Set up uv
      uses: astral-sh/setup-uv@v8.1.0
      with:
        enable-cache: false
        pyproject-file: backend/pyproject.toml

    - name: Set up Python 3.13
      run: uv python install 3.13

    - name: Install dependencies
      run: |
        cd backend
        uv sync --all-groups

    - name: Verify the throwaway database is UTF-8
      run: |
        enc=$(psql "$TEST_POSTGRES_URL" -tAc "SHOW server_encoding")
        echo "server_encoding=$enc"
        test "$enc" = "UTF8"

    - name: Run Postgres migration tests
      run: |
        cd backend
        uv run pytest tests/test_migrations_postgres.py -v --durations=15 \
          --junitxml=migration-test-results.xml -o addopts=

    - name: Assert every migration case actually ran
      if: always()
      run: |
        cd backend
        uv run python scripts/assert_no_skips.py migration-test-results.xml
```

Notes on the steps, in order:

- **`checkout@v6` without `fetch-depth: 0`.** The other jobs need full history
  for Sonar; this one does not.
- **`uv sync --all-groups`** installs `alembic>=1.18.4` and `psycopg2-binary`
  into `backend/.venv`. The module resolves the CLI as
  `os.path.dirname(sys.executable) + "/alembic"`, which under `uv run pytest`
  is `backend/.venv/bin/alembic` — present after this step, deliberately not
  `python -m alembic` (the repo's own `alembic/` package shadows the library).
- **`psql`** is pre-installed on `ubuntu-latest`. This step is the mechanical
  half of ER-1: the log carries `server_encoding=UTF8`, and a cluster that is
  anything else fails the job here instead of failing obscurely inside `0028`.
- **`-o addopts=`** neutralises `pytest.ini`'s `--cov=app --cov-fail-under=90`
  for this run only. This is verified on the pinned pytest, not assumed:
  `cd backend && SECRET_KEY=test uv run pytest tests/test_migrations_postgres.py
  -q -o addopts=` produces `53 skipped`, no coverage output, exit 0. Use it as
  written; there is no fallback form to choose between, and the gate in
  `pytest.ini` is not to be lowered.
- **`--durations=15`** puts the per-case timing in the log, which is the
  evidence base for §3.
- **`-v`** makes the per-case `PASSED` lines and the final
  `53 passed in Ns` visible, which is ER-2's "verificável no log do job".

---

## 2. The 0-skipped guard

A run in which the module skips everything exits **0**. Green. That is the
failure mode this whole task exists to end, so the workflow must assert it away
rather than trust the setup.

Add `backend/scripts/assert_no_skips.py` (a CI helper, not a test — it is not
under `tests/`, `pytest.ini`'s `testpaths = tests` excludes it, and it is not
collected):

```python
"""Fail the job if the Postgres migration module did not really run.

`tests/test_migrations_postgres.py` self-skips when `TEST_POSTGRES_URL` is
unset or unreachable, and a fully-skipped pytest run exits 0. Between
APRAS-27 and APRAS-50 that is how 53 cases stayed invisible inside a green
check. This reads the JUnit XML the job just produced and refuses a run in
which the module was collected-but-skipped, or not collected at all.
"""
```

Behaviour:

1. If the file named in `argv[1]` does not exist, print a one-line message
   saying the pytest step produced no JUnit XML — which under `if: always()`
   means a collection or environment error before any case ran — and exit
   non-zero. It must not die with a bare `FileNotFoundError` traceback.
2. Parse the JUnit XML.
3. Select `testcase` elements whose `classname` is exactly
   `tests.test_migrations_postgres` — that is the literal attribute pytest
   writes for this module, verified against a real run of it. Do not match on
   `test_migrations_postgres.py` or on a bare module name; a selector that
   matches nothing reports `collected=0` and fails closed, but the wasted CI
   round trip is avoidable.
4. Print `collected=<n> skipped=<m>` (log evidence for ER-2).
5. Exit non-zero when `n < MIN_CASES` (**53**, the count at `e188866`) or when
   `m > 0`, naming the skipped cases and, when `n` is 0, saying that the module
   was not collected at all.

`MIN_CASES = 53` is a floor, not an equality: a later task that adds a case
must not have to touch this file, while a task that deletes the module or
silences it cannot pass. Carry that reasoning in a `#:` comment on the
constant, in the module's house style.

`if: always()` on the step is required — without it a green-but-empty pytest
run would still be green, since the guard would run only after a *failing*
pytest.

---

## 3. Timing, and what to do if it blows the budget

**Measure, do not estimate.** Record three numbers, from `gh run list` / the
Actions UI, in `.meridian/reports/APRAS-50-inprogress-0.md`:

| | |
|---|---|
| A | `Backend Tests` duration on the **master baseline** run |
| B | `Backend Tests` duration on §4's **green run** (§4.2 push 1; expected: A ± noise, the job is untouched) |
| C | `Backend Migration Tests (Postgres)` duration on that **same green run** |

C is measured on the green run and on no other. §4's red run has ~16 failing
cases, several of them aborting a chain part-way, so its duration is not the
steady-state cost the budget is about.

ER-4's budget is about the workflow's wall clock: the jobs run in parallel, so
the pipeline grows by `max(0, C − max(A, frontend))`. **That growth must be
≲ 3 min.** `--durations=15` in the log shows where C goes if it is large.

If C blows the budget, the levers are *not* in this task's scope — the cost is
structural (two full chain re-runs per `isolated_pg_engine` case, ~60 chain
runs total) and lives in the test module's fixtures, which **Out of Scope**
excludes. So:

- do **not** silence, deselect or shard cases to fit;
- record the measured C in `.meridian/reports/APRAS-50-inprogress-0.md` and add a
  line to `docs/suggestions-log.md` proposing the follow-up (the obvious one:
  `CREATE DATABASE ... TEMPLATE` or a `pg_dump` snapshot restored per case
  instead of re-running the chain);
- flag it to the operator as an accepted deviation rather than quietly
  shipping a 12-minute gate.

`timeout-minutes: 20` on the job is a backstop against a hung `alembic`
subprocess holding a runner for six hours; it is not the budget.

---

## 4. The two proof runs (ER-2 and ER-3)

A job nobody has seen pass is unproven, and a guard nobody has seen fail is a
guess. Before the task merges, produce **both** runs — one green, one red — on a
**throwaway branch that is deleted afterwards**, so nothing temporary ever lives
on the task branch or on `master`.

The task branch itself produces no run: §1.2 keeps `ci.yml`'s `push` filter at
`[ master ]`, and `workflow_dispatch` is not offered until the merged `ci.yml`
reaches the default branch (see §4.3). The throwaway branch is therefore the only
place a pre-merge run of the new job can exist, and it has to carry both
outcomes.

### 4.1 Who does what, and in what order

**The developer agent does not push branches and does not dispatch workflows.**
It produces the task branch (workflow change, guard script, AGENTS.md), writes
`.meridian/reports/APRAS-50-inprogress-0.md`, stages its changes, and stops. Its
job here is to make both runs *reproducible* — to state exactly which commits
produce them — not to run them.

The **orchestrator** performs everything in §4.2: both pushes, the run capture
and the branch deletion. It then **appends** the `Proof of failure (throwaway
branch, deleted)` section of §4.5 to the developer's already-closed
`.meridian/reports/APRAS-50-inprogress-0.md`, and only then dispatches QA. The
order is load-bearing: QA sees only the Expected Results, and the ERs name that
report, so the section must be in the file before QA runs. If the pipeline
returns to the developer for a revision round, the appended section stays — the
developer adds to the report, never truncates it.

### 4.2 The procedure (orchestrator)

Two pushes on the same branch, in this order:

1. Branch `apras-50-proof` from the task branch.
2. **Push 1 — the trigger-only commit.** One commit carrying nothing but the
   temporary push-filter line of §4.3:

   ```yaml
     push:
       branches: [ master, apras-50-proof ]
   ```

   Everything else in the tree is the task's real state — the real `ci.yml`
   job, the real guard, no break anywhere. Commit message:
   `ci(APRAS-50): TEMPORARY branch trigger — do not merge`.
   Push it. The run this fires **must be green**: `Backend Migration Tests
   (Postgres)` reports `53 passed`, and the guard step prints
   `collected=53 skipped=0`. This run is **ER-2's artifact** and the source of
   §3's durations **B** and **C**. If it is red, that is a genuine finding —
   §7 governs what happens next; do not proceed to push 2 until it is resolved
   or the task is escalated.
3. **Push 2 — the break commit, on top.** One further commit that removes the
   recidivism-index creation from
   `backend/alembic/versions/0036_add_infraction_tables.py` — the
   `op.create_index("ix_infraction_recidivism", ...)` at line 226 that
   `test_0036_creates_the_recidivism_index` (l.2617) asserts. Commit message:
   `test(APRAS-50): TEMPORARY proof of failure — do not merge`. Push it. The
   run this fires **must be red**, as §4.4 describes. This run is **ER-3's
   artifact**.
4. Capture both run URLs (`gh run list --workflow=ci.yml
   --branch=apras-50-proof`) and the evidence listed in §4.4 and §4.5. Keep the
   two URLs distinguishable — each ER names its own run.
5. Delete the branch: `git push origin --delete apras-50-proof` and drop the
   local ref. Neither temporary commit exists anywhere afterwards.
6. Append the §4.5 section to `.meridian/reports/APRAS-50-inprogress-0.md`, then
   dispatch QA.

Under no circumstance is either temporary commit pushed to `master`, and the task
is never merged early to make a trigger work.

### 4.3 Why a temporary push-filter line and not `workflow_dispatch`

`workflow_dispatch` is added to `ci.yml` by this task (§1.2) and is a deliverable
in its own right, but it cannot produce these two runs. **Known GitHub
constraint:** the dispatch API resolves a workflow by its *default-branch*
definition; `--ref` then selects which ref's file executes. `master`'s `ci.yml`
does not declare `workflow_dispatch` yet, so `gh workflow run ci.yml --ref
apras-50-proof` is refused with `Workflow does not have 'workflow_dispatch'
trigger` until this task merges. It becomes the normal mechanism for every task
*after* this one.

The push-filter line works today and is deterministic: for `push` events GitHub
evaluates the workflow file **from the pushed commit**, so a branch whose own
`ci.yml` lists `apras-50-proof` fires immediately, with nothing needed on the
default branch.

That line must never appear on the task branch. The mechanical check for this is
**ER-1**'s "its `push`/`pull_request` filters stay `[ master ]`", read off the
merged `.github/workflows/ci.yml` — not ER-3's diff check, whose pathspec is
`backend/app backend/alembic` and cannot see a workflow file at all.

### 4.4 What the red run must show

- `Backend Migration Tests (Postgres)` **fails**, and among the failures is
  `test_0036_creates_the_recidivism_index`.
- **Expect roughly sixteen failures, and at minimum two.** The upgrade path
  survives a missing index, so the cascade comes from two places:
  - **Downgrades.** `0036`'s `downgrade()` at line 447 is
    `op.drop_index("ix_infraction_recidivism", table_name="infraction")` with no
    `if_exists`, so *every* case that downgrades from `head` past `0036` fails.
    There are 17 `_run_alembic("downgrade", ...)` call sites; the two that start
    below `0036` (l.348 under `pg_engine_at_0018`, l.379 after a reset to
    `0020`) are unaffected, leaving **15** — a set that already includes
    `test_0036_round_trips` (l.2654, whose `downgrade -1` at l.2658 asserts
    `returncode == 0`).
  - **The model-metadata comparison.** `app/models/infraction.py` l.166 still
    declares `ix_infraction_recidivism`, so with the migration's `create_index`
    removed, `test_0036_matches_the_model_metadata` (l.2671) fails as well.

  That is 15 + `test_0036_creates_the_recidivism_index` +
  `test_0036_matches_the_model_metadata` ≈ 17 cases, and it is **expected, not
  an environment problem** — do not go hunting for one. The count is
  approximate by design; ER-3 asks only for the named case plus at least one
  cascade failure.
- `Backend Tests` in the **same run** stays **green** — SQLite never sees the
  index, which is exactly why the old CI could not have caught it.
- Neither job errors before collection, i.e. the failures are assertions and
  non-zero alembic exits, not a missing service.
- The `sonarcloud` job will also run on that branch, on both pushes, and may
  register a branch analysis in SonarCloud. That is accepted noise; do not add
  `if:` conditions to suppress it.

**Fallback break**, only if the chosen one aborts the chain before any case can
report (it should not — the upgrade path is unaffected): temporarily point
`HEAD_REVISION` in the test module at a wrong revision. This is weaker evidence
(it proves the module runs, not that it catches migration bugs), so prefer the
migration break, and say in the report which was used.

### 4.5 Where the proof is recorded

The orchestrator appends this to `.meridian/reports/APRAS-50-inprogress-0.md`,
under the heading `Proof of failure (throwaway branch, deleted)`, **before QA is
dispatched**:

- **the green run** (push 1): its URL, the `53 passed` line, the guard's
  `collected=53 skipped=0` line, and durations B and C from §3;
- **the red run** (push 2): its URL, the failing test ids with one assertion
  excerpt, and the outcome of `Backend Tests` in that same run (green);
- the shas of both temporary commits and confirmation that `apras-50-proof` no
  longer exists on `origin` (`git ls-remote --heads origin apras-50-proof`
  returns nothing).

This report is the artifact ER-2, ER-3 and ER-4 name and QA reads. The
orchestrator then carries the same section into the task commit's message body
when it commits the approved work — a durability hand-off, not a check anyone
performs. There is no PR and no PR body; do not invent one.

### 4.6 The pre-merge diff check

On the branch state submitted for merge, this must print nothing:

```bash
git diff --name-only origin/master...HEAD -- backend/app backend/alembic
```

`backend/tests` is deliberately **not** in that pathspec — §7 allows
environment-only fixes to `tests/test_migrations_postgres.py`, and each one is
accounted for by being listed and justified in
`.meridian/reports/APRAS-50-inprogress-0.md` instead.

---

## 5. The auto-skip stays

Do **not** remove or weaken `pytestmark = pytest.mark.skipif(not
TEST_POSTGRES_URL, ...)`, and do not turn the module's
`pytest.skip("Could not reach TEST_POSTGRES_URL ...")` into a failure. A
contributor without Postgres must still be able to run `uv run pytest` and get
a green suite; CI is where the module is *required* to run, and §2's guard is
what makes "required" true there instead of hoping.

The unchanged local contract, which ER-4 checks:

```bash
cd backend && SECRET_KEY=test uv run pytest
# -> the whole suite green, exactly 53 skips, all from
#    tests/test_migrations_postgres.py, --cov-fail-under=90 satisfied
```

Run it once **with `TEST_POSTGRES_URL` unset** on the final branch state and
quote the skip count in `.meridian/reports/APRAS-50-inprogress-0.md`.

---

## 6. AGENTS.md (ER-5)

Three edits, all documentation.

AGENTS.md is itself test-guarded by `backend/tests/test_docs_agents_md.py`,
which forbids `UserRole`, `allowed_menus`, `MenuKey`, `user_type`, `UserType`
and "menu gate" outside `### What is gone` and
`### Migrating an existing install`. None of the text below trips it — keep it
that way, and re-run that module after editing.

**6.1 — `## CI/CD` (≈ line 146), add one bullet after the `ci.yml` line:**

> - **Migration tests** — `ci.yml`'s `backend-migrations` job runs
>   `backend/tests/test_migrations_postgres.py` against a throwaway
>   **Postgres 16 (UTF-8)** service container. The module self-skips wherever
>   `TEST_POSTGRES_URL` is unset, so **CI is the source of truth** for it; a
>   guard step fails the job if the module reports any skip or fewer than 53
>   cases, because a fully-skipped run exits 0. `ci.yml` also accepts
>   `workflow_dispatch`, so any branch can be run manually with
>   `gh workflow run ci.yml --ref <branch>`.

**6.2 — a new subsection right after `## Data Layer` (≈ line 145):**

> ### Running the Postgres migration tests locally
>
> `backend/tests/test_migrations_postgres.py` needs a real Postgres it is
> allowed to destroy: every fixture runs `DROP SCHEMA public CASCADE` and
> re-runs the Alembic chain. **Never point `TEST_POSTGRES_URL` at the dev
> database on 5436** — it will be emptied. The database must be **UTF-8**:
> migration `0028` seeds `Condomínio Padrão`.
>
> **initdb (no Docker needed — the dev machine's Docker disk is often full):**
>
> ```bash
> export PGDATA=/tmp/apras-pgtest PGPORT=55432
> initdb -U postgres -E UTF8 --locale=C "$PGDATA"
> pg_ctl -D "$PGDATA" -o "-p $PGPORT" -l /tmp/apras-pgtest.log start
> createdb -h localhost -p "$PGPORT" -U postgres apras_test
>
> cd backend && TEST_POSTGRES_URL=postgresql://postgres@localhost:55432/apras_test \
>   SECRET_KEY=test uv run pytest tests/test_migrations_postgres.py -v
>
> pg_ctl -D "$PGDATA" stop && rm -rf "$PGDATA"
> ```
>
> **Docker, when it has disk:**
>
> ```bash
> docker run -d --rm -p 55432:5432 \
>   -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=apras_test \
>   -e POSTGRES_INITDB_ARGS="--encoding=UTF8 --locale=C" postgres:16-alpine
>
> cd backend && TEST_POSTGRES_URL=postgresql://postgres:postgres@localhost:55432/apras_test \
>   SECRET_KEY=test uv run pytest tests/test_migrations_postgres.py -v
> ```
>
> Check what you got with `psql "$TEST_POSTGRES_URL" -tAc "SHOW server_encoding"`
> — it must print `UTF8`. Two known divergences, both deliberate: Homebrew's
> `initdb` on this machine is **PostgreSQL 14** while CI and `docker-compose.yml`
> are **16**; and the CI job and both recipes above use `--locale=C`, while
> `docker-compose.yml`'s `db` sets no `POSTGRES_INITDB_ARGS` and so gets
> `en_US.utf8` collation. Nothing in the module asserts a collation-dependent
> ordering today, but a test that starts to must account for the difference.
> For anything that turns on version- or collation-specific catalog behaviour,
> use the Docker recipe (or `brew install postgresql@16`) and treat the CI job
> as the source of truth.

**6.3 — Directory Structure (≈ line 308):** amend the `ci.yml` comment to
`# Main CI pipeline (tests, coverage gates, Postgres migration job)`, and add
`backend/scripts/assert_no_skips.py` to the tree if the surrounding block
enumerates `backend/` files at that depth (match the existing style; do not
restructure the block).

Nothing else in AGENTS.md changes: no domain section, no route map, no table.

---

## 7. If the module goes red on real Postgres 16

Likely, and *fine* — it would be the task paying for itself on day one. The
module has only ever been run by hand against a local PG14/16 dev database.

**Environment-only fixes are in scope**: a hardcoded port or DSN, a missing
env var, a path assumption that holds on macOS but not on the runner, a
`pytest.skip` reason that misreports the cause. This carve-out is why §4.6's
diff check covers `backend/app` and `backend/alembic` but not `backend/tests`.
Its price is bookkeeping: **each such edit must be listed individually** in
`.meridian/reports/APRAS-50-inprogress-0.md`, with the file, the lines, and the
reasoning for why it changes no assertion. An unlisted edit under
`backend/tests/` is a review finding.

**Silencing is never in scope.** Do not `xfail`, `skip`, deselect, loosen or
delete a case to get the job green. Shipping this task with a case switched off
would recreate the exact hole it closes.

**If a case fails because the code or a migration is genuinely wrong on PG16,
this task cannot be completed as specified, and that is its terminal state.**
The fix would live under `backend/app/` or `backend/alembic/versions/`, which
Out of Scope excludes and ER-5 mechanically forbids, while ER-2 still requires
`53 passed` — no developer round can reconcile those, so do not spend one
trying. Instead: record the failing case, the assertion, and the run URL in
`.meridian/reports/APRAS-50-inprogress-0.md`; add the finding to
`docs/suggestions-log.md`; and **escalate to the operator with the task moved to
`blocked`**, naming the follow-up task that must fix the migration and land
before APRAS-50 can pass. A real bug found this way is the task paying for
itself, not a failure of the task — but it is a stop, not an iteration.

---

## Expected Results

- [ ] **ER-1 — CI brings up a UTF-8 Postgres 16, hands it to pytest, and can be
      run manually on any branch.** `.github/workflows/ci.yml` declares the job
      `backend-migrations` ("Backend Migration Tests (Postgres)") with a
      `services:` container on `postgres:16-alpine` (the same major as
      `docker-compose.yml` and AGENTS.md), a `pg_isready` health check
      (`--health-interval 10s --health-retries 5`),
      `POSTGRES_INITDB_ARGS: "--encoding=UTF8 --locale=C"`, `ports: 5432:5432`,
      `timeout-minutes`, and job-level
      `TEST_POSTGRES_URL=postgresql://postgres:postgres@localhost:5432/apras_test`
      exported before the pytest step; a step before pytest prints
      `server_encoding=UTF8` from `psql "$TEST_POSTGRES_URL" -tAc "SHOW
      server_encoding"` and fails the job on any other value, because migration
      `0028` seeds the non-ASCII `Condomínio Padrão`. The workflow's `on:` block
      gains `workflow_dispatch:` while its `push`/`pull_request` filters stay
      `[ master ]`, so `gh workflow run ci.yml --ref <branch>` is possible and
      no new automatic runs are introduced.
- [ ] **ER-2 — the job is shown running all 53 cases green in CI, and cannot
      silently go back to skipping.** `.meridian/reports/APRAS-50-inprogress-0.md`
      carries, under `Proof of failure (throwaway branch, deleted)`, the URL of
      the **green run** — the first of two pushes on the throwaway branch
      `apras-50-proof`, whose only temporary content is the branch's own
      `push:` trigger line — together with that run's `53 passed` (0 skipped,
      0 failed) summary line for `Backend Migration Tests (Postgres)` and the
      guard step's `collected=53 skipped=0` line. In the merged workflow, that
      guard step runs with `if: always()` and invokes
      `backend/scripts/assert_no_skips.py` on the job's
      `migration-test-results.xml`, selecting `testcase` elements whose
      `classname` is `tests.test_migrations_postgres`, printing
      `collected=<n> skipped=<m>`, and exiting non-zero when `n < 53`, when
      `m > 0`, or when the XML file is absent (with a legible message rather
      than a traceback) — so a run in which the service is unreachable and every
      case self-skips fails instead of passing green.
- [ ] **ER-3 — the guard is shown failing on the same throwaway branch, and
      nothing temporary survives.** A second push on `apras-50-proof`, adding
      one commit that removes the `ix_infraction_recidivism` creation from
      migration `0036`, produces a **red run** in which `Backend Migration Tests
      (Postgres)` fails — `test_0036_creates_the_recidivism_index` among the
      failures, plus at least one expected cascade failure (a downgrade case or
      `test_0036_matches_the_model_metadata`) — while `Backend Tests` in that
      same run passes. `.meridian/reports/APRAS-50-inprogress-0.md` carries,
      under the same heading and distinguishable from the green run, that red
      run's URL, the failing test ids with an assertion excerpt, the green
      `Backend Tests` outcome, both temporary commits' shas, and confirmation
      that `apras-50-proof` no longer exists on `origin`. On the branch state
      submitted for merge,
      `git diff --name-only origin/master...HEAD -- backend/app backend/alembic`
      prints nothing.
- [ ] **ER-4 — local runs without Postgres stay green, and CI does not get
      ~3 min slower.** On the final branch, `cd backend && SECRET_KEY=test uv
      run pytest` with `TEST_POSTGRES_URL` unset passes with exactly 53 skips,
      all from `tests/test_migrations_postgres.py`, and satisfies
      `--cov-fail-under=90`; the `skipif` marker and the unreachable-database
      `pytest.skip` are unchanged. `.meridian/reports/APRAS-50-inprogress-0.md`
      quotes three durations — `Backend Tests` on the master baseline run,
      `Backend Tests` on ER-2's green run (unchanged within noise), and
      `Backend Migration Tests (Postgres)` on that same green run — and shows
      the workflow's wall clock growing ≲ 3 min; or, if it does not, records the
      excess in that report and in `docs/suggestions-log.md` rather than
      absorbing it by disabling cases.
- [ ] **ER-5 — AGENTS.md documents both local paths and names CI as the source
      of truth, and no production file moves.** AGENTS.md gains the
      `backend-migrations` bullet under `## CI/CD` (mentioning the guard and
      `workflow_dispatch`) and a "Running the Postgres migration tests locally"
      subsection containing the `initdb -E UTF8` recipe, the Docker recipe, the
      `SHOW server_encoding` check, the `DROP SCHEMA public CASCADE` warning
      against pointing `TEST_POSTGRES_URL` at the dev database on 5436, and the
      divergence caveats (local PG14 vs CI PG16; CI's `--locale=C` vs
      `docker-compose.yml`'s `en_US.utf8`); `backend/tests/test_docs_agents_md.py`
      still passes. `git diff --name-only origin/master...HEAD` lists no path
      under `backend/app/` and no file in `backend/alembic/versions/`.

---

## Out of Scope

- **Any change under `backend/app/`, `backend/alembic/versions/`, or
  `backend/pyproject.toml` dependencies.** No new migration, no product
  behaviour, no new package.
- **Changing what any test asserts.** `tests/test_migrations_postgres.py` is
  not edited except for environment-only fixes the first real CI run forces
  (§7), each listed and justified in
  `.meridian/reports/APRAS-50-inprogress-0.md`. Weakening,
  `xfail`-ing, deselecting or deleting a case is excluded outright.
- **Making the rest of the suite run on Postgres.** `tests/conftest.py` stays
  SQLite in-memory; this task adds a second execution environment for one
  module, not a database swap.
- **Speeding up the module's fixtures** (template databases, dump/restore
  snapshots, `pytest-xdist`). If §3's measurement calls for it, it becomes a
  follow-up task with its own spec.
- **Broadening CI's automatic triggers.** `workflow_dispatch:` is added; the
  `push` and `pull_request` branch filters stay `[ master ]`. The
  `push: branches: [..., apras-50-proof]` line of §4.3 exists only on the
  throwaway branch and is deleted with it.
- **Other workflows.** `migrate.yml`, `release.yml` and the `gemini-*.yml`
  files are untouched; `sonarcloud`'s `needs:` list is untouched; the backend
  coverage gate and the artifacts Sonar consumes are untouched.
- **Repository settings.** Adding `Backend Migration Tests (Postgres)` to the
  branch-protection required checks is a GitHub-settings change, not a code
  change; note it in `.meridian/reports/APRAS-50-inprogress-0.md` as a manual
  follow-up for the operator.
- **Rewriting `docs/suggestions-log.md`'s originating entry.** It is history;
  it stays as written (including its "45 casos", true when it was recorded).
