# APRAS-122 — Pin uv in CI: setup-uv has no `pyproject-file` input, so every job floats to latest

## The observed behaviour, from a run log

`astral-sh/setup-uv@v8.1.0` does not declare a `pyproject-file` input. All four
`setup-uv` steps in this repository pass it — `.github/workflows/ci.yml` lines
45, 135, 188 and `.github/workflows/migrate.yml` line 17 — so the action ignores
it and installs floating-latest uv. The runner says so in as many words. From
run `36924804570`'s predecessor, run **36924174723** (head `25e9dc6`,
2026-10-01), each of the three uv-using jobs (`110577272457` Backend Lint,
`110577272946` Backend Tests, `110577272967` Backend Migration Tests) logs:

```
##[warning]Unexpected input(s) 'pyproject-file', valid inputs are ['version',
 'version-file', 'python-version', 'activate-environment', 'venv-path',
 'no-project', 'working-directory', 'checksum', 'github-token', 'enable-cache',
 'cache-dependency-glob', 'restore-cache', 'save-cache', 'cache-suffix',
 'cache-local-path', 'prune-cache', 'cache-python', 'ignore-nothing-to-cache',
 'ignore-empty-workdir', 'tool-dir', 'tool-bin-dir', 'manifest-file',
 'add-problem-matchers', 'resolution-strategy']
Could not determine uv version from uv.toml or pyproject.toml. Falling back to latest.
Downloading uv from ".../download/0.12.21/uv-x86_64-unknown-linux-gnu.tar.gz"
Successfully installed uv version 0.12.21
```

Three facts follow, and the task is built on them. CI ran uv **0.12.21** on
2026-10-01 while the development machine runs **0.12.19**. The warning line
**enumerates the action's declared inputs for the exact pinned ref**, which is a
better provenance for the guard's allow-list than any file in this repository.
And `backend/pyproject.toml` carries no `[tool.uv]` and no `required-version`,
and there is no root `pyproject.toml` or `uv.toml`, so a *declared* file-based
input would have pinned nothing either.

## Scope

Covers: a literal `version:` pin on every `setup-uv` step in
`.github/workflows/`, removal of the undeclared `pyproject-file:` input from all
of them, a committed test that fails when a `setup-uv` step passes an input the
pinned ref does not declare or when the pin literals disagree, run-log evidence
of the uv version before and after **plus a green conclusion for every uv-using
job on the landing commit**, a one-off audit of every third-party action used in
`.github/workflows/` for the same class of defect, and the documented bump
ritual.

The set of `setup-uv` steps is **derived from the tree at landing time**, not a
fixed list: four on today's `master`, five if APRAS-121's
`requirements-export.yml` has landed (§D1).

Does not cover: fixing anything the audit finds outside `setup-uv` (each finding
becomes its own follow-up), `checksum:` pinning (APRAS-121 owns that for the one
job that holds a push credential; the four steps this task edits hold none, and
`checksum:` on APRAS-121's step is accepted by the guard because it is a
declared input of `v8.1.0`), pinning the
Python patch version that `uv python install 3.13` resolves, adding a
`github-actions` dependabot ecosystem, any change to `backend/pyproject.toml`,
`backend/uv.lock` or `backend/requirements.txt`, and any new test dependency.

## Decisions this task makes rather than defers

### D1 — Which task owns the pin, and what the loser does

APRAS-121 (at `spec_approval`) already specifies `version: "0.12.19"` on the
`setup-uv` step of the `Backend Tests` job, `pyproject-file:` dropped, plus
`UV_PIN="0.12.19"` inside `backend/scripts/export_requirements.sh` and the same
literal on a **fifth `setup-uv` step**, in a **new workflow file**
`.github/workflows/requirements-export.yml` (`version: "0.12.19"`, `checksum:`
for the 0.12.19 artefact, `enable-cache: false`). The overlap is therefore *two*
things, not one: the `Backend Tests` block in `ci.yml`, and a new file inside
this task's guard scope.

- **APRAS-122 owns the workflow-side pin for every `setup-uv` step in
  `.github/workflows/`** and adopts APRAS-121's literal **`0.12.19` verbatim**,
  not CI's current floating `0.12.21`. What must agree is the **`version:`
  literal**, nothing else: the pin's correctness never depended on byte
  identity. **No key order is required or asserted anywhere.** On the four
  steps this task writes, `version:` is placed first for readability, and that
  placement is a style preference with no expected result and no committed
  assertion behind it. `requirements-export.yml`'s key order is **APRAS-121's
  to choose** and is out of scope here in both directions — this task neither
  requires nor changes it.
- **The guard's universe is derived, never literal.** The step count is whatever
  `grep -c 'astral-sh/setup-uv@'` over `.github/workflows/` yields at landing
  time — 4 on today's tree, **5** once `requirements-export.yml` exists. No
  assertion, and no expected result, hard-codes 4. APRAS-121's step is
  **governed by this task's guard even though this task does not write it**: it
  must hold the same `version:` literal (it does), and its `checksum:` key is a
  **declared input of `v8.1.0`** (it is one of the 24 names quoted above), so it
  passes the undeclared-input guard unchanged.
- **If APRAS-122 lands first:** APRAS-121 finds its `Backend Tests` edit already
  done, must not re-edit the block, and still delivers `UV_PIN`,
  `requirements-export.yml` and its three-literal agreement test. That test
  reads the `version:` of the `backend` job's `setup-uv` step, which will
  already hold `0.12.19` — it passes unchanged.
- **If APRAS-121 lands first:** APRAS-122 changes the remaining three steps
  (`backend-migrations`, `backend-lint`, `migrate.yml`) and leaves
  `requirements-export.yml`'s step untouched, but its guard then covers five
  steps, not three: the discovered-count assertion, the agreement assertion and
  the undeclared-input check all include `requirements-export.yml`. Nothing else
  here is affected.
- APRAS-122 does **not** own, touch or restate `UV_PIN` or
  `backend/scripts/export_requirements.sh`. The two test *modules* are disjoint
  files; their *inputs* overlap (both read `ci.yml`), which is harmless because
  both read the same `version:` value and expect the same literal — so neither
  module needs editing when the other lands.
- **Why `0.12.19` for all five steps, and not just for the export step.** The
  constraint is real on one step only: the export's bytes are a uv-version
  artefact and `export_requirements.sh` refuses when the local uv differs, so
  the producing uv must be the developer's 0.12.19. One literal is then carried
  to the other four for two reasons, both checkable rather than aesthetic.
  First, **the agreement assertion is the pin's only backstop and it compares
  literals** — it is meaningful only if every step holds the *same* string;
  partitioning the pin would mean two allow-list/agreement groups, two bump
  rituals and two ways to drift, for no gain. Second — and this argument is
  **reasoned, not observed: it is unmeasured**, because the re-resolution path
  cannot be demonstrated under this task's constraints (no local `uv sync`, no
  dispatched experiment on a second uv build), so it is a bounded hypothesis
  carrying no expected result. More narrowly than a flat "uv resolves the lock"
  would claim: `backend-lint`,
  `backend-migrations` and `migrate.yml` run `uv sync --all-groups` with **no
  `--frozen` and no `--locked`**, so a newer uv in those jobs **may re-resolve
  in-job** — when it judges the committed lock stale against `pyproject.toml`,
  or when it will not reuse the lock's format (`version = 1`, `revision = 3`)
  — and install something the export step's `--frozen` run can never surface.
  In the ordinary fresh-lock case the uv version only affects *reading* an
  already-resolved lock and changes nothing. APRAS-121's `uv lock --check`
  lands only in `Backend Tests`, and it gates only the **staleness** branch of
  that pair: a lock stale against `pyproject.toml` becomes a red `Backend
  Tests` in the same run, though still not inside those three jobs. It gates
  **nothing** in the **lock-format** branch — `uv lock --check` says nothing
  about whether a given uv build will reuse `version = 1` / `revision = 3` — so
  the lock-format branch is ungated everywhere. That bounded, unmeasured case
  is the whole of this second argument,
  and argument one carries the decision on its own. One uv version in CI is
  one thing to reason about. The cost is that this pins **backwards** from the
  0.12.21 CI is currently floating to, so §D4 requires the uv-using jobs to be
  observed **green on 0.12.19**, not merely to log the string.
- **`version:` and not `version-file:`.** `version-file:` would require a
  `required-version` in a project file, which APRAS-121 explicitly declined:
  that file is head-controlled and must not choose the toolchain for its
  privileged job. A literal in the workflow keeps both specs consistent.

### D2 — How the guard enumerates the action's declared inputs

**Chosen: an allow-list committed in the test, keyed by the exact `uses:` ref.**
Not a network fetch of `action.yml` at test time, and not a vendored copy.

- A fetch makes a red test possible with no change in this repository, and this
  repository's test suite is offline by construction (`assert_no_skips.py`
  forbids skipping, so there is no legitimate "network unavailable" escape).
  A guard that fails for a reason outside this repository is a guard someone
  deletes.
- A vendored `action.yml` is a large third-party file needing the same bump
  ritual as an allow-list, for no extra strength.
- **Why the allow-list does not rot silently:** it is keyed by ref. A ref the
  map does not know is itself a failure, with a message naming the new ref and
  the command to re-derive its inputs
  (`gh api repos/astral-sh/setup-uv/contents/action.yml?ref=<ref> --jq '.content' | base64 -d`).
  `.github/dependabot.yml` declares **no `github-actions` ecosystem**, so a
  `uses:` ref changes only by a deliberate human edit — the staleness window is
  exactly the commit that does the bump, and the test is red inside it.
- **The costs, stated.** The map can be wrong in two bounded ways: an input the
  action *removed* at the pinned ref stays listed (a false negative), and an
  input the action *added* later is rejected until someone updates the entry (a
  false positive on a legitimate new input). The backstop for the first is the
  run log — the runner's own `Unexpected input(s)` warning — which §D4 turns
  into a checked after-state.
- **Provenance of the `v8.1.0` entry** is the 24 names in the warning quoted
  above, with the run and job ids recorded in a comment beside the map, because
  that list comes from the runner for that exact ref.

### D3 — Where the guard lives, and how it coexists

A **new module, `backend/tests/test_workflow_actions.py`**. It does not touch
`backend/tests/test_suite_hygiene.py`, which **APRAS-119 is rewriting** (it
replaces a hygiene assertion and adds `timeout-minutes` coverage there), nor
`backend/tests/test_requirements_export.py`, which APRAS-121 is editing. A new
file is the coexistence answer: three concurrent tasks, three disjoint files, no
merge conflict and no test one task deletes while another is asserting it.

**No new dependency**, so `pyyaml` is out. Adding it would move
`backend/pyproject.toml`, `backend/uv.lock` *and* `backend/requirements.txt`,
colliding head-on with APRAS-121. The module parses the workflow text, which
makes one failure mode load-bearing: a parser that silently finds an empty
`with:` mapping makes the guard pass vacuously. Four anti-vacuity assertions are
therefore mandatory:

1. the number of steps the parser discovers equals the count of
   `astral-sh/setup-uv@` occurrences in `.github/workflows/` — **derived from a
   scan of the tree, not compared against a literal** (§D1);
2. the discovered steps include at least one from `ci.yml` **and** at least one
   from `migrate.yml`, so both step spellings present in this repository are
   exercised (`- name:` followed by `uses:` in `ci.yml`, a bare `- uses:` in
   `migrate.yml`) — the count equality alone cannot catch a parser that misses
   one spelling, because both of its sides derive from the same text;
3. every discovered step's parsed mapping is non-empty and contains
   `enable-cache`;
4. **a committed negative test over an inline fixture string** — a few lines of
   fake workflow text declaring a `setup-uv` step whose `with:` carries
   `pyproject-file:` — asserts the detector *flags* that key. The module must
   expose **one shared `text → steps` parse entry point**, and both the
   real-tree scan (assertions 1–3 and the undeclared-input guard) and this
   fixture test must call **that same function**: the fixture proves nothing if
   a later refactor can satisfy it through a separate string-parsing helper
   while the file-reading path drifts. Assertions 1–3 do
   not require the parser to ever see a key outside the allow-list, so a parser
   that extracted only `version` and `enable-cache` would satisfy all three and
   pass the undeclared-input guard vacuously. Today the only thing catching that
   would be the one-off mutation record in the audit document, which does not
   survive a refactor; the fixture test does, and needs no dependency and no
   network.

The same module also asserts the literal `AGENTS.md` claim strings from §D5,
following the convention `backend/tests/test_docs_agents_md.py` already
establishes. The assertion lives **here**, not in that module, so this task adds
no edit to a file another concurrent task may own.

### D4 — The after-state is read from a run log, and the run must be green

The step's own output is where the installed version appears. Reading it:

```bash
gh api repos/:owner/:repo/actions/runs/<run_id>/jobs \
  --jq '.jobs[] | "\(.id) \(.name) \(.conclusion)"'
gh run view --job <job_id> --log \
  | grep -E "Successfully installed uv version|Falling back to latest|Unexpected input"
```

**Before** is run `36924174723`, quoted at the top of this spec. **After** must
show, for every uv-using job of the CI run on the landing commit: one
`Successfully installed uv version 0.12.19` line, **no** `Falling back to
latest` line, and **zero** `Unexpected input` lines.

**Log lines are not enough, and this is the check that makes a backwards pin
safe.** CI has been green on floating 0.12.21; nothing in this repository has
ever run the suite on 0.12.19 in CI. All three log checks above are satisfiable
by a run in which the job *failed* — a `setup-uv` step logs its version long
before `pytest` or `alembic` runs. So the after-state additionally requires
**`conclusion: success`**, recorded with the job id, for every uv-using job of
the CI run on the landing commit (`Backend Tests`, `Backend Migration Tests
(Postgres)`, `Backend Lint (ruff)`, plus `requirements-export.yml`'s job if
APRAS-121 has landed) **and** for the `Run DB Migrations` job of the
`migrate.yml` run the push to `master` fires. `migrate.yml` is **covered, not
excluded**, and is the most exposed step because it is the only one holding
`POSTGRES_URL_NON_POOLING` and running `alembic upgrade head` against
production. A red job on 0.12.19 means the pin is wrong and the task is not
done — it is not a flake to re-run away, so the recorded `conclusion` is that of
**`run_attempt` 1** by default. A later attempt is admissible **only** when the
document records, together, attempt 1's `conclusion`, the name of the job and of
the step that failed in it, a log excerpt of that failure, and an explicit
statement that the failure is not uv-related (so an infrastructure flake — a
runner loss, a Postgres service that never came up, a PyPI timeout — does not
make the evidence inadmissible). Without all four of those, a `run_attempt` > 1
conclusion does not satisfy this spec.

**Gate production, do not witness it. This is a hard requirement, not a
preference.** `ci.yml` and `migrate.yml` both fire on the same push to `master`,
in parallel and with no ordering, so if the pin first reaches `master`
unobserved, the first suite run on 0.12.19 happens at the same moment
`migrate.yml` runs `alembic upgrade head` against production on 0.12.19.

The gate is available and the procedure is named here, because the objection
that stood in its way is false: the operator's policy on record forbids a
**pull request** for local pipeline work, and `workflow_dispatch` needs only a
**pushed ref** — no PR. Verified at `2cb0d48`: `ci.yml` declares
`workflow_dispatch:` at line 12, with its own comment framing it as the way to
get a run on a ref other than `master`; `workflow_dispatch` ignores the
`branches: [ master ]` filters on `push`/`pull_request`; `ci.yml` carries no
branch-conditional `if:` on any job (its only `if:` is `if: always()` at line
169), so all three uv-using jobs do run on a dispatched throwaway ref; and
`migrate.yml` declares **no** `workflow_dispatch` and fires only on push to
`master`, so a throwaway ref cannot touch production.

**The procedure, in order:**

1. push the pin commit to a throwaway remote branch, opening **no** pull
   request;
2. `gh workflow run ci.yml --ref <branch>`;
3. read the `conclusion` of `Backend Tests`, `Backend Migration Tests
   (Postgres)` and `Backend Lint (ruff)` from that run; all three must be
   `success`;
4. fast-forward `master` to **that same commit** — no amend, no rebase, no
   squash, so the landing sha is bit-for-bit the sha that was observed green.
   `git push origin <sha>:master` from the worktree is the strictest form of
   this step: it pushes the existing commit object by its own sha and creates
   no new object. The only case that breaks the fast-forward is `master` having
   advanced meanwhile, and that case is self-enforcing — any reconciliation
   that changes the sha makes result 4's two recorded values differ, so the
   result fails rather than passing on stale evidence;
5. delete the throwaway branch.

The dispatched run's **`head_sha` must equal the sha that `master` lands**, and
the document records both values so the equality is checkable rather than
implied. A dispatched run on "the pin commit" that was then amended before
landing is not evidence for the landed commit.

**The escape, and what it is gated on.** Pushing even a throwaway remote branch
is the operator's call, not the implementer's. So this gate has exactly one
escape, and it is gated on **a record the implementer does not author**: the
`answer` of the named `questions` entry **`q-1790947582472-122`** on Meridian
task APRAS-122, which asks the operator whether the throwaway ref may be pushed.
That entry exists with an empty `answer` and `by: "Agent"`; if a refusal comes,
it arrives as that entry's `answer`, with an `answered_at` timestamp the
implementer did not write. To take the escape, the audit document quotes that
`answer` **verbatim**, cites the entry's `id` and its `answered_at` as the date,
and the quote must match the task record — so QA compares the document against
the board and the branch is binary, in the same spirit as APRAS-121's
`gh secret list` citation. An **empty or absent `answer`** on that entry is not
a refusal: **a missing dispatched run while that entry carries no refusal is a
failure, not an outstanding item.** The escape never becomes free.

**Why the escape names a record and not a conversation.** A question an agent
only asks in conversation — in a report, a prompt, a chat turn — is invisible to
both QA and the board, so an escape anchored on it reduces to text the
implementer types into its own audit document and is selectable at will. An
escape gated on an operator decision must therefore name the record that
decision lives in; here that record is the `questions` entry above. The
implementer does not write to the `questions` array — the orchestrator owns task
state — it only reads and quotes it.

When the escape is taken, the audit document records the quoted refusal under a
heading naming the post-hoc risk it leaves (`ci.yml` and `migrate.yml` fire in
parallel on the same push, so production is witnessed rather than gated), and
the after-the-fact `master` evidence stands alone. The failure mode is
fail-closed either way: a `uv sync` 0.12.19 will not complete fails the step
before `alembic` runs, and an alembic failure leaves the schema at the last
applied revision.

### D5 — Who bumps the pin, on what signal

Nothing bumps it automatically: dependabot does not update a `version:` string
input, and there is no `github-actions` ecosystem to bump the action ref either.
The pin is bumped **deliberately by the maintainer, in one commit** that edits
every `version:` literal in `.github/workflows/` together with APRAS-121's
`UV_PIN` — editing one alone is a red test, which is the whole point of the
agreement assertion. The recurring human signal is APRAS-121's local refusal:
a developer who upgrades uv gets `export_requirements.sh` exiting non-zero and
naming `UV_PIN`, which is what prompts the bump commit. A stale pin is safe to
sit on — uv is a build tool, and the dependencies that actually ship are pinned
by `uv.lock` and `backend/requirements.txt`, so a stale uv cannot ship a
vulnerable library. This paragraph's substance goes into `AGENTS.md`.

### D6 — The third-party action audit is an inventory, not a repair

The inventory is produced by a grep over `uses:` lines in `.github/workflows/`
and is already finite. **The row set is derived from the tree at landing time, one
row per distinct ref, and no count is hard-coded** — exactly as the `setup-uv`
step count is (§D1). The derivation is a scan of `uses:` lines over
`.github/workflows/` with reusable-workflow calls excluded; the audit document
records the command it used and the count that scan yielded.

As an **illustration of today's tree, not as the criterion**, that scan yields
**12 distinct refs across 9 workflow files**, listed below.
APRAS-121's `requirements-export.yml` moves the `setup-uv` row's occurrence
count from 4 to 5; whether it changes the *ref* count depends on an
`actions/checkout` ref **that spec does not pin**, and this repository already
carries `@v6`, `@v4` and `@8e8c483d…`. The landing tree therefore has 12 rows
if that step reuses `@v6` and 13 if it introduces a fourth `checkout` ref —
which is precisely why the number is derived and never asserted as a literal.

The table records the **pre-fix** `with:` keys, as observed on today's tree.
The audit document records the **post-fix** state of the landing commit, so its
`setup-uv` row reads `version`, `enable-cache` (plus `checksum` on APRAS-121's
step) and no `pyproject-file`; every other row is unchanged by this task.

Reusable-workflow calls (`uses: './.github/workflows/gemini-*.yml'`) are
excluded, with the reason recorded: their inputs are declared in this repository
and GitHub validates them against the local `workflow_call` block.

| Ref | Files (occurrences) | `with:` keys passed |
| --- | --- | --- |
| `astral-sh/setup-uv@v8.1.0` | `ci.yml` ×3, `migrate.yml` | `enable-cache`, `pyproject-file` |
| `actions/checkout@v6` | `ci.yml` ×5, `migrate.yml`, `release.yml` ×2 | `fetch-depth`, or none |
| `actions/checkout@v4` | `gemini-invoke.yml`, `gemini-plan-execute.yml` | none |
| `actions/checkout@8e8c483` | `gemini-review.yml` | none |
| `actions/setup-node@v6` | `ci.yml`, `release.yml` ×3 | `node-version` |
| `actions/upload-artifact@v7` | `ci.yml` ×2 | `name`, `path` |
| `actions/download-artifact@v8` | `ci.yml` ×2 | `name`, `path` |
| `SonarSource/sonarqube-scan-action@v7` | `ci.yml` | none |
| `actions/create-github-app-token@29824e6` | `gemini-dispatch.yml` ×2, `gemini-invoke.yml`, `gemini-plan-execute.yml`, `gemini-review.yml`, `gemini-scheduled-triage.yml`, `gemini-triage.yml` | `app-id`, `private-key`, `permission-contents`, `permission-issues`, `permission-pull-requests` |
| `actions/github-script@ed59741` | `gemini-triage.yml` ×2, `gemini-scheduled-triage.yml` ×2 | `script`, `github-token` |
| `actions/github-script@60a0d83` | `gemini-dispatch.yml` | `script`, `github-token` |
| `google-github-actions/run-gemini-cli@v0` | `gemini-invoke.yml`, `gemini-plan-execute.yml`, `gemini-review.yml`, `gemini-scheduled-triage.yml`, `gemini-triage.yml` | 16–17 `gemini_*`/`gcp_*` keys |

The two `github-script` refs get **separate rows and separate verdicts**: they
are separately pinned shas (`v8.0.0` and `v7` per their `ratchet:` comments) and
their declared inputs are not the same set.

**The run-log method is available for the `setup-uv` row and nothing else.** The
absence of an `Unexpected input` warning is evidence only for the specific jobs
whose logs were read, and the logs in hand are three jobs of run `36924174723`
— `110577272457` Backend Lint, `110577272946` Backend Tests, `110577272967`
Backend Migration Tests. Those three jobs never run `actions/setup-node@v6`,
`actions/download-artifact@v8` or `SonarSource/sonarqube-scan-action@v7` (the
`frontend` and `sonarcloud` jobs do), never run `release.yml`'s or
`migrate.yml`'s `actions/checkout@v6`, and never run anything in the gemini
workflows. For **every row other than `setup-uv`**, the verdict is produced by
`gh api repos/<owner>/<repo>/contents/action.yml?ref=<ref> --jq '.content' |
base64 -d`, comparing each `with:` key against the `inputs:` block at that exact
ref, and the row records `action.yml` as its method. The `setup-uv` row may cite
the run-log warning *in addition*, naming run `36924174723` and the three job
ids. **Nothing outside `setup-uv` is fixed here**;
findings are written up as named follow-ups with a one-line scope each, in the
audit document and in the task report, and creating the tasks is the operator's
step. This boundary is what keeps result 4 from making the task unbounded.

## Files touched

- `.github/workflows/ci.yml` — the three `setup-uv` blocks (lines 45, 135, 188): `version: "0.12.19"` added, `pyproject-file:` removed, `enable-cache: false` kept. Key order is unconstrained (§D1); `version:` first is this task's style choice, not a requirement. No other line changes; the `timeout-minutes` and step ordering that APRAS-119 and APRAS-121 touch are left alone.
- `.github/workflows/migrate.yml` — the same two edits on its one `setup-uv` step (line 17, bare `- uses:` form).
- `.github/workflows/requirements-export.yml` — **not touched.** If APRAS-121 has landed, its `setup-uv` step is already compliant — same `version:` literal, and `checksum:` is a declared input of `v8.1.0` — in any key order, which is APRAS-121's to choose. The guard simply covers it.
- `backend/tests/test_workflow_actions.py` — new. The ref-keyed declared-input allow-list with its run-log provenance comment, the undeclared-input guard, the pin-agreement assertion, the four anti-vacuity assertions of §D3 (including the inline-fixture negative test), and the `AGENTS.md` claim-string assertions. Offline: no network, no subprocess, no `uv` invocation.
- `docs/tasks/APRAS-122-action-audit.md` — new. The before/after run-log evidence with run and job ids, the exact `gh` commands, and the `conclusion` of every uv-using job; the pre-landing dispatched run's id and `head_sha` beside the landed sha (or the quoted operator refusal, per §D4); the third-party action inventory with a verdict and a method per row; the named follow-ups.
- `AGENTS.md` — the CI/CD section: uv is pinned by a literal `version:` on every `setup-uv` step, `pyproject-file` is not an input of that action, and D5's bump ritual. One paragraph, independent of the one-line export-script edit APRAS-121 makes elsewhere in the same file.

## Test criteria

`cd backend && uv run pytest tests/test_workflow_actions.py -v` passes on the
committed tree, and each of these mutations, applied alone, must be **observed**
failing it with the failure output pasted into the audit document: adding
`pyproject-file: backend/pyproject.toml` back to any one step; changing one
`version:` literal to a different value; deleting one `version:` input; and
changing a `uses: astral-sh/setup-uv@` ref to one the allow-list does not know.
The inline-fixture negative test (§D3.4) covers the first of those four
permanently, so a later parser refactor cannot regress it silently.
`cd backend && uv run ruff check . && uv run ruff format --check .` stays at
zero findings, and `backend/tests/test_lint_hygiene.py`'s `NOQA_CAP` is not
raised.

## Expected Results

- [ ] Every `astral-sh/setup-uv` step in `.github/workflows/` at landing time passes `version: "0.12.19"` and keeps `enable-cache: false`; none passes `version-file:`; and `grep -rn 'pyproject-file' .github/workflows/ | wc -l` is `0`. The set of steps is **derived from the tree**, not a fixed list: the three in `ci.yml` (lines 45, 135, 188) and the one in `migrate.yml` on today's `master`, plus `requirements-export.yml`'s if APRAS-121 landed first — which this task does not edit, only covers. **Key order within `with:` is not a criterion for any step**, here or in `requirements-export.yml`: only the presence and value of `version:` are checked.
- [ ] `docs/tasks/APRAS-122-action-audit.md` records the uv version from run logs on both sides, with run id, job ids and the exact `gh api .../jobs` + `gh run view --job <id> --log` commands used: **before**, run `36924174723` jobs `110577272457`/`110577272946`/`110577272967` each logging `Could not determine uv version from uv.toml or pyproject.toml. Falling back to latest.` and `Successfully installed uv version 0.12.21`; **after**, a CI run on the landing commit in which every uv-using job logs `Successfully installed uv version 0.12.19`, no job logs `Falling back to latest`, and `grep -c 'Unexpected input'` over each job's log returns 0.
- [ ] The same after-run is recorded as **green on the pinned version**: every uv-using job of the CI run on the landing commit (`Backend Tests`, `Backend Migration Tests (Postgres)`, `Backend Lint (ruff)`, and `requirements-export.yml`'s job if present) is listed with its job id and `conclusion: success` from `gh api repos/:owner/:repo/actions/runs/<run_id>/jobs --jq '.jobs[] | "\(.id) \(.name) \(.conclusion)"'`. No uv-using job is `failure`, `cancelled` or `skipped`. Each recorded conclusion is that of `run_attempt` 1; a conclusion from a later attempt is admissible only when the document records, together, attempt 1's `conclusion`, the failing job name, the failing step name, a log excerpt of that failure, and an explicit statement that the failure is not uv-related.
- [ ] The pre-landing gate is satisfied **by default by evidence, and this result passes in exactly one of two ways and in no other.** Either: a `workflow_dispatch` CI run of `ci.yml` on a ref other than `master`, started *before* the pin commit reached `master`, is recorded in `docs/tasks/APRAS-122-action-audit.md` by run id, with `Backend Tests`, `Backend Migration Tests (Postgres)` and `Backend Lint (ruff)` each at `conclusion: success` on 0.12.19, **and** that run's `head_sha` (from `gh run view <run_id> --json headSha`) is recorded alongside the sha `master` landed and the two are **equal**. Or: the audit document quotes, **verbatim, the `answer` of the `questions` entry `q-1790947582472-122` on Meridian task APRAS-122** — the operator's refusal of the throwaway ref — citing that entry's `id` and its `answered_at` as the date, with the quote matching the task record, under a heading naming the post-hoc risk it leaves (`ci.yml` and `migrate.yml` fire in parallel on the same push, so production is witnessed rather than gated). An **empty or absent `answer`** on that entry is not a refusal. **A missing dispatched run while that entry carries no refusal is a failure, not an outstanding item.**
- [ ] The `migrate.yml` run fired by the push to `master` is recorded with the same three log checks (`0.12.19`, no fall-back line, no `Unexpected input` line) **and** with its `Run DB Migrations` job id and `conclusion: success`; the document states that `migrate.yml` is covered rather than excluded, with the reason.
- [ ] `backend/tests/test_workflow_actions.py` fails when any `setup-uv` step in `.github/workflows/` passes an input not in the allow-list entry for that step's pinned ref, and fails with a message naming the ref and the `gh api repos/astral-sh/setup-uv/contents/action.yml?ref=<ref>` re-derivation command when the ref has no entry. The `v8.1.0` entry holds exactly the 24 names the runner printed — including `checksum`, which APRAS-121's step passes — with run id `36924174723` cited in a comment as their provenance.
- [ ] The same module asserts every `setup-uv` step passes a `version:` input and that all such literals are the same string, and it fails when one literal is changed or deleted alone. It reads only files under `.github/workflows/`, never `backend/scripts/export_requirements.sh`, and performs no network I/O, no `subprocess` call and no `uv` invocation.
- [ ] The module's parser cannot pass vacuously, via four assertions: the number of `setup-uv` steps discovered equals the number of `astral-sh/setup-uv@` occurrences found by scanning `.github/workflows/` (**derived, with no literal count hard-coded — 4 on today's tree, 5 once `requirements-export.yml` exists**); the discovered steps include at least one from `ci.yml` and at least one from `migrate.yml`, so both the `- name:`+`uses:` and bare `- uses:` spellings are exercised; every discovered step's parsed `with:` mapping is non-empty and contains `enable-cache`; and a committed negative test over an inline fake-workflow fixture string carrying `pyproject-file:` asserts the detector flags that key, calling **the same named `text` → steps parse function** the real-tree scan calls (one shared entry point, not a fixture-only helper).
- [ ] Four mutations are each observed failing the module, with the failure output pasted into the audit document: `pyproject-file:` re-added to one step; one `version:` literal changed; one `version:` input deleted; the `setup-uv` ref changed to one the allow-list does not know.
- [ ] `docs/tasks/APRAS-122-action-audit.md` lists **every distinct third-party `uses:` ref in `.github/workflows/` at landing time** as one row each, with the row set and its count **derived from a recorded scan of the tree and no count hard-coded** (that scan yields 12 refs across 9 files at `2cb0d48`; it yields 13 if APRAS-121's `requirements-export.yml` introduces a fourth `actions/checkout` ref, and either outcome satisfies this result) — with `actions/github-script@ed59741` and `actions/github-script@60a0d83` as **two separate rows** — giving for each the file(s) and occurrence counts, the `with:` keys passed **as of the landing commit (post-fix, so the `setup-uv` row reads `version`, `enable-cache` and no `pyproject-file`)**, a verdict on whether any key is undeclared at that ref, and the method behind that verdict. The method is `gh api` on `action.yml` at the pinned ref for **every row except `setup-uv`**; the run-log `Unexpected input` method is used only on the `setup-uv` row, where it cites run `36924174723` and job ids `110577272457`/`110577272946`/`110577272967`. Reusable-workflow `uses: './.github/workflows/*.yml'` entries are excluded with the reason stated.
- [ ] No action other than `setup-uv` is modified by this task: every finding in the audit outside `setup-uv` appears under a `Follow-ups` heading with a proposed title and one-line scope, and in the task report, and nothing else in `.github/workflows/` changes.
- [ ] `AGENTS.md` states that uv is pinned by a literal `version:` on every `setup-uv` step, that `pyproject-file` is not an input of that action, that one literal is used for all steps because the agreement assertion compares literals and because one uv version in CI is one thing to reason about (the claim strings assert those two reasons only, not the unmeasured re-resolution hypothesis of §D1), and that the pin is bumped deliberately by the maintainer in one commit editing every literal together — no bot does it, and the signal is the local `UV_PIN` refusal. `backend/tests/test_workflow_actions.py` asserts those claim strings are present in `AGENTS.md`.
- [ ] `backend/pyproject.toml`, `backend/uv.lock` and `backend/requirements.txt` are unmodified (no new test dependency); `backend/tests/test_suite_hygiene.py`, `backend/tests/test_requirements_export.py` and `backend/tests/test_docs_agents_md.py` are unmodified; and no file under `frontend/` is modified.
- [ ] `cd backend && uv run pytest tests/test_workflow_actions.py -v` passes, `uv run ruff check . && uv run ruff format --check .` report zero findings over `backend/`, and `NOQA_CAP` in `backend/tests/test_lint_hygiene.py` is not raised.

## Out of Scope

Fixing any audit finding outside `setup-uv`; `checksum:` pinning (APRAS-121's,
for the one job holding a push credential); pinning the Python patch version
`uv python install 3.13` resolves; adding a `github-actions` dependabot
ecosystem; `[tool.uv] required-version` in `backend/pyproject.toml` (declined by
APRAS-121 and not revisited here); `backend/scripts/export_requirements.sh` and
`UV_PIN` (APRAS-121's); authoring or editing
`.github/workflows/requirements-export.yml` (APRAS-121's file — this task's
guard covers its `setup-uv` step but never writes it); and any
`timeout-minutes` or step-ordering change in `ci.yml` (APRAS-119's and
APRAS-121's).
