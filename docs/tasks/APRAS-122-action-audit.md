# APRAS-122 — the uv pin, and a one-off audit of every action `.github/workflows/` uses

`astral-sh/setup-uv@v8.1.0` does not declare a `pyproject-file` input. All four
`setup-uv` steps in this repository passed it. GitHub does not fail a step for
an undeclared input — it prints `##[warning]Unexpected input(s)` and carries on
— so the pin that was *written* in the workflow pinned nothing, and every job
installed floating-latest uv.

This document is the evidence: the uv version read out of run logs on both
sides of the fix, the pre-landing gate that proved the backwards pin safe
before it could reach production, the four mutations the new guard was watched
failing, and a one-off inventory of every third-party action this repository
uses, checked for the same class of defect.

---

## 1. Before — run `36924174723`

Head `25e9dc60a8bd4d44f24d3fd21bf27576bb39e933`, event `push`, `run_attempt` 1,
2026-10-01.

Jobs, from:

```bash
gh api repos/:owner/:repo/actions/runs/36924174723/jobs \
  --jq '.jobs[] | "\(.id) \(.name) \(.conclusion)"'
```

```
110577272457 Backend Lint (ruff) success
110577272821 Frontend Tests success
110577272946 Backend Tests success
110577272967 Backend Migration Tests (Postgres) success
110579676913 SonarCloud Scan success
```

Logs, for each of the three uv-using jobs:

```bash
gh run view --job 110577272457 --log \
  | grep -E "Successfully installed uv version|Falling back to latest|Unexpected input"
gh run view --job 110577272946 --log | grep -E ...   # same pattern
gh run view --job 110577272967 --log | grep -E ...   # same pattern
```

Each of the three printed the same three things. `110577272457` (Backend Lint),
verbatim and trimmed only of the `job<TAB>step<TAB>` prefix `gh` adds:

```
2026-10-01T20:47:47.2103370Z ##[warning]Unexpected input(s) 'pyproject-file', valid inputs are ['version', 'version-file', 'python-version', 'activate-environment', 'venv-path', 'no-project', 'working-directory', 'checksum', 'github-token', 'enable-cache', 'cache-dependency-glob', 'restore-cache', 'save-cache', 'cache-suffix', 'cache-local-path', 'prune-cache', 'cache-python', 'ignore-nothing-to-cache', 'ignore-empty-workdir', 'tool-dir', 'tool-bin-dir', 'manifest-file', 'add-problem-matchers', 'resolution-strategy']
2026-10-01T20:47:47.3968370Z Could not determine uv version from uv.toml or pyproject.toml. Falling back to latest.
2026-10-01T20:47:48.0291292Z Successfully installed uv version 0.12.21
```

`110577272946` (Backend Tests) at `20:47:46`/`20:47:47` and `110577272967`
(Backend Migration Tests) at `20:48:08`/`20:48:09` printed the identical three
lines — same warning, same fall-back, same `0.12.21`.

`grep -c 'Unexpected input'` returned **2** for each of the three jobs: the
action emits the warning once on the main step and once on its post step.

Two things to take from the warning beyond the defect itself. It installed
**0.12.21** while the development machine runs **0.12.19**. And it
**enumerates the action's declared inputs for the exact pinned ref** — 24 names
— which is a better provenance for the guard's allow-list than any
transcription of `action.yml`, and is cited as such in
`backend/tests/test_workflow_actions.py`.

`backend/pyproject.toml` carries no `[tool.uv]` and no `required-version`, and
there is no root `pyproject.toml` or `uv.toml`, so a *declared* file-based
input would have pinned nothing here either. The fix is a literal.

---

## 2. The fix

Every `setup-uv` step now passes `version: "0.12.19"` and keeps
`enable-cache: false`. The undeclared input is gone:

```bash
$ grep -rn 'pyproject-file' .github/workflows/ | wc -l
0
```

The set of steps is derived from the tree, not from a list in a document:

```bash
$ grep -rc 'astral-sh/setup-uv@' .github/workflows/
.github/workflows/release.yml:0
.github/workflows/migrate.yml:1
.github/workflows/ci.yml:3
$ grep -rno 'astral-sh/setup-uv@' .github/workflows/ | wc -l
4
```

**4 steps** at landing time: `ci.yml` (`backend`, `backend-migrations`,
`backend-lint`) and `migrate.yml` (`migrate`). APRAS-121's
`requirements-export.yml` has **not** landed, so there is no fifth step yet;
when it lands the guard covers it with no edit, because both sides of its
count assertion are derived from the same scan.

One literal across all four steps, for two reasons. The agreement assertion is
the pin's only backstop and it **compares literals**, so it means something
only if every step holds the same string. And one uv version in CI is one thing
to reason about rather than two groups that can drift apart. `0.12.19` and not
CI's current `0.12.21` because APRAS-121 needs the uv that *produces*
`backend/requirements.txt` to be the developer's.

Key order inside `with:` is not a criterion anywhere — `version:` is written
first for readability and nothing asserts that.

---

## 3. The pre-landing gate — dispatched run `37315213778`

The pin moves CI **backwards**, from the 0.12.21 it had been floating to, and
nothing in this repository had ever run the suite on 0.12.19 in CI. `ci.yml`
and `migrate.yml` fire on the same push to `master`, in parallel and with no
ordering, so landing the pin unobserved would mean the first suite run on
0.12.19 happening at the same moment `migrate.yml` ran `alembic upgrade head`
against production on 0.12.19. The gate exists so production is **gated, not
witnessed**.

Pushing even a throwaway remote branch is the operator's call. It was asked and
answered: `questions` entry **`q-1790947582472-122`** on Meridian task
APRAS-122, `answered_at` `2026-10-02T13:33:08.907Z`, answer **`yes`**. So the
dispatched-run branch of the gate is the one taken, and no refusal is being
quoted.

```bash
git push origin 40d40a2bc4ccc490df9f65adfc94ead9b645d0bc:refs/heads/tmp-apras-122-uv-pin-gate
gh workflow run ci.yml --ref tmp-apras-122-uv-pin-gate
gh run view 37315213778 --json headSha,attempt,event,headBranch,conclusion
```

```json
{"attempt":1,"conclusion":"success","event":"workflow_dispatch",
 "headBranch":"tmp-apras-122-uv-pin-gate",
 "headSha":"40d40a2bc4ccc490df9f65adfc94ead9b645d0bc"}
```

| | |
| --- | --- |
| Dispatched run | `37315213778`, `workflow_dispatch`, `run_attempt` 1 |
| Its `head_sha` | `40d40a2bc4ccc490df9f65adfc94ead9b645d0bc` |
| The sha `master` lands | `40d40a2bc4ccc490df9f65adfc94ead9b645d0bc` |
| Equal? | **yes** — same object, pushed by its own sha and never amended |

The commit was pushed by sha (`<sha>:refs/heads/<branch>`), which creates no new
object, and `master` takes it by fast-forward, so the landing sha is
bit-for-bit the sha that was observed green. No pull request was opened, and the
throwaway ref was deleted as soon as the run had been read:

```bash
git push origin --delete tmp-apras-122-uv-pin-gate
```

No ordering risk to production from the dispatch itself: `migrate.yml` declares
only `on: push: branches: [ master ]` and **no** `workflow_dispatch`, so a
throwaway ref cannot reach it.

**One thing for the reader to know about this document's own commit.** A
committed document cannot record a CI run on the commit that contains it. So
the pin — `ci.yml`, `migrate.yml`, `AGENTS.md` and
`backend/tests/test_workflow_actions.py` — is commit
`40d40a2bc4ccc490df9f65adfc94ead9b645d0bc`, the commit the gate ran on and the
commit whose sha is recorded above; this document is a **docs-only** commit on
top of it, adding one file under `docs/tasks/` and changing nothing any CI job
reads. `git diff 40d40a2 HEAD --stat` touches `docs/` and nothing else.

---

## 4. After — the same run, `37315213778`, on the landing commit

```bash
gh api repos/:owner/:repo/actions/runs/37315213778/jobs \
  --jq '.jobs[] | "\(.id) \(.name) \(.conclusion)"'
```

```
111780126776 Backend Migration Tests (Postgres) success
111780127073 Backend Tests success
111780127158 Backend Lint (ruff) success
111780127391 Frontend Tests success
111782465849 SonarCloud Scan success
```

```bash
gh run view --job 111780127073 --log \
  | grep -E "Successfully installed uv version|Falling back to latest|Unexpected input"
gh run view --job 111780126776 --log | grep -E ...   # same pattern
gh run view --job 111780127158 --log | grep -E ...   # same pattern
```

| Job | id | `conclusion` (attempt 1) | uv version logged | `Falling back` lines | `grep -c 'Unexpected input'` |
| --- | --- | --- | --- | --- | --- |
| Backend Tests | `111780127073` | `success` | `Successfully installed uv version 0.12.19` | 0 | **0** |
| Backend Migration Tests (Postgres) | `111780126776` | `success` | `Successfully installed uv version 0.12.19` | 0 | **0** |
| Backend Lint (ruff) | `111780127158` | `success` | `Successfully installed uv version 0.12.19` | 0 | **0** |

`requirements-export.yml` has no job here because APRAS-121 has not landed.

The lines themselves, trimmed of `gh`'s `job<TAB>step<TAB>` prefix:

```
Backend Tests                      2026-10-05T13:14:10.0552552Z Successfully installed uv version 0.12.19
Backend Migration Tests (Postgres) 2026-10-05T13:14:26.5351168Z Successfully installed uv version 0.12.19
Backend Lint (ruff)                2026-10-05T13:14:09.4210950Z Successfully installed uv version 0.12.19
```

**Why the `conclusion` column is here and not just the log lines.** All three
log checks are satisfiable by a run whose job *failed*: `setup-uv` logs its
version long before `pytest` or `alembic` runs. CI had been green on 0.12.21 and
had never run this suite on 0.12.19, so "it logged the right string" would not
have told us the backwards pin was safe. Every conclusion above is
`run_attempt` **1** — nothing was re-run, and no later attempt is being leaned
on.

### `migrate.yml` is covered, not excluded

`migrate.yml`'s `setup-uv` step is one of the four this task pins, and its
`migrate` job is the **most exposed** of all of them: it is the only one
holding `POSTGRES_URL_NON_POOLING` and the only one running
`alembic upgrade head` against production. Excluding it would mean leaving uv
floating in exactly the place where a surprise costs the most.

Its run is fired by the push to `master` and therefore cannot be observed from
before that push. It is **outstanding on this document at the moment of
landing**, to be recorded with the same four values the table above carries —
`Run DB Migrations` job id, `conclusion: success`,
`Successfully installed uv version 0.12.19`, no `Falling back to latest` line
and `grep -c 'Unexpected input'` at 0 — from:

```bash
gh api repos/:owner/:repo/actions/runs/<run_id>/jobs \
  --jq '.jobs[] | "\(.id) \(.name) \(.conclusion)"'
gh run view --job <job_id> --log \
  | grep -E "Successfully installed uv version|Falling back to latest|Unexpected input"
```

What is already known about it: the step is byte-identical in shape to the
three observed above, on the same ref and the same literal, and the failure
mode is fail-closed — a `uv sync` that will not complete on 0.12.19 fails the
step before `alembic` runs, and an alembic failure leaves the schema at the last
applied revision.

---

## 5. The guard, and the four mutations it was watched failing

`backend/tests/test_workflow_actions.py`. Offline by construction: it reads
workflow text and `AGENTS.md`, and nothing else — no network, no `subprocess`,
no `uv` invocation, and in particular never
`backend/scripts/export_requirements.sh`, which is APRAS-121's. Three of its
assertions check that about the module's own source by AST.

It parses the workflow text by hand, because `pyyaml` is not a dependency here
and adding one would move `backend/pyproject.toml`, `backend/uv.lock` *and*
`backend/requirements.txt`. That makes one failure mode load-bearing — a parser
that discovers nothing, or an empty `with:` mapping, would make every other
assertion pass while guarding nothing — so four anti-vacuity assertions carry
the module:

1. the discovered step count equals a plain substring scan of the same files
   (**derived both sides, no literal count**);
2. the discovered steps include at least one from `ci.yml` **and** one from
   `migrate.yml`, so both spellings this repository uses are exercised —
   `- name:` then `uses:`, and a bare `- uses:`;
3. no step's parsed `with:` mapping is empty, and each contains `enable-cache`;
4. an **inline fake-workflow fixture** carrying `pyproject-file:` must be
   *flagged*, through the **same `parse_setup_uv_steps` entry point** the
   real-tree scan calls. Assertions 1–3 are all satisfiable by a parser that
   only ever extracts `version` and `enable-cache`, which would pass the
   undeclared-input guard vacuously; this is what rules that out permanently,
   and it survives a refactor in a way a one-off mutation record does not.

Each mutation below was applied **alone** to `.github/workflows/ci.yml`, the
module was run, and the file was restored. Run with
`-q --no-cov -p no:randomly -x`; output pasted as produced.

### 5.1 `pyproject-file:` re-added to one step

```
===== m1-pyproject-file-readded (exit 1) =====
......F
=================================== FAILURES ===================================
________ test_no_setup_uv_step_passes_an_input_its_ref_does_not_declare ________
E           AssertionError: ci.yml:55: `setup-uv@v8.1.0` does not declare ['pyproject-file']; GitHub ignores undeclared inputs with a warning rather than failing, so the step quietly does something other than what it reads as
E           assert not {'pyproject-file'}

tests/test_workflow_actions.py:381: AssertionError
=========================== short test summary info ============================
FAILED tests/test_workflow_actions.py::test_no_setup_uv_step_passes_an_input_its_ref_does_not_declare
1 failed, 6 passed, 1 warning in 0.06s
```

(`-x` stopped the run there; `test_no_workflow_passes_pyproject_file_to_anything`
is a second, independent assertion that also fails on this mutation.)

### 5.2 One `version:` literal changed

```
===== m2-one-version-literal-changed (exit 1) =====
.........F
=================================== FAILURES ===================================
____________ test_all_setup_uv_version_literals_are_the_same_string ____________
E       AssertionError: the `version:` literals disagree: {'ci.yml:55': '"0.12.21"', 'ci.yml:160': '"0.12.19"', 'ci.yml:221': '"0.12.19"', 'migrate.yml:17': '"0.12.19"'}. One uv version in CI is one thing to reason about, and this comparison is the pin's only backstop -- bump every literal in the same commit
E       assert 2 == 1
E        +  where 2 = len({'"0.12.19"', '"0.12.21"'})

tests/test_workflow_actions.py:414: AssertionError
=========================== short test summary info ============================
FAILED tests/test_workflow_actions.py::test_all_setup_uv_version_literals_are_the_same_string
1 failed, 9 passed, 1 warning in 0.05s
```

### 5.3 One `version:` input deleted

```
===== m3-one-version-input-deleted (exit 1) =====
........F
=================================== FAILURES ===================================
_______________ test_every_setup_uv_step_pins_a_literal_version ________________
E           AssertionError: ci.yml:55: no `version:` input, so this step installs floating-latest uv
E           assert 'version' in {'enable-cache': 'false'}
E            +  where {'enable-cache': 'false'} = SetupUvStep(source='ci.yml', line=55, ref='v8.1.0', inputs={'enable-cache': 'false'}).inputs

tests/test_workflow_actions.py:401: AssertionError
=========================== short test summary info ============================
FAILED tests/test_workflow_actions.py::test_every_setup_uv_step_pins_a_literal_version
1 failed, 8 passed, 1 warning in 0.05s
```

### 5.4 The `setup-uv` ref changed to one the allow-list does not know

```
===== m4-unknown-setup-uv-ref (exit 1) =====
......F
=================================== FAILURES ===================================
________ test_no_setup_uv_step_passes_an_input_its_ref_does_not_declare ________
E               AssertionError: ci.yml:55: `setup-uv` ref 'v9.0.0' has no allow-list entry, so nothing here knows what it declares. Re-derive its inputs with:
E                   gh api repos/astral-sh/setup-uv/contents/action.yml?ref=v9.0.0 --jq '.content' | base64 -d
E               and add the entry to DECLARED_INPUTS in test_workflow_actions.py.

tests/test_workflow_actions.py:374: AssertionError
=========================== short test summary info ============================
FAILED tests/test_workflow_actions.py::test_no_setup_uv_step_passes_an_input_its_ref_does_not_declare
1 failed, 6 passed, 1 warning in 0.05s
```

### Why an allow-list, and how it does not rot

Keyed by the exact `uses:` ref. A ref the map does not know is itself a
failure — 5.4 — carrying the command to re-derive that ref's inputs. Since
`.github/dependabot.yml` declares **no** `github-actions` ecosystem (its only
two ecosystems are `uv` and `npm`), a `uses:` ref moves only by a deliberate
human edit, so the staleness window is exactly the commit that does the bump and
the test is red inside it.

It is not a network fetch at test time: this suite is offline by construction
(`scripts/assert_no_skips.py` leaves no legitimate "network unavailable"
escape), and a guard that can go red with no change in this repository is a
guard someone deletes. It is not a vendored `action.yml` either: a large
third-party file needing the same bump ritual, for no extra strength.

Two bounded ways the map can be wrong, stated rather than hidden. An input the
action *removed* at the pinned ref stays listed — a false negative, whose
backstop is the runner's own `Unexpected input` warning, which §4 turns into a
checked after-state. And an input the action *added* later is rejected until
someone updates the entry — a false positive on a legitimate new input, which
costs one edit in the commit that introduces it.

---

## 6. Inventory of every third-party action used in `.github/workflows/`

### The scan

Row set and count are derived from the tree at landing time; nothing here is a
hard-coded number.

```bash
$ ls -1 .github/workflows/ | wc -l
3
$ grep -rhno 'uses: *[^ ]*' .github/workflows/ | sed 's/.*uses: *//' | sort | uniq -c | sort -rn
   8 actions/checkout@v6
   4 astral-sh/setup-uv@v8.1.0
   4 actions/setup-node@v6
   2 actions/upload-artifact@v7
   2 actions/download-artifact@v8
   1 SonarSource/sonarqube-scan-action@v7
$ grep -rhno 'uses: *[^ ]*' .github/workflows/ | sed 's/.*uses: *//' | sort -u | wc -l
6
```

**6 distinct refs across 3 workflow files**, 21 occurrences.

Reusable-workflow calls (`uses: './.github/workflows/*.yml'`) are **excluded**,
because their inputs are declared in this repository and GitHub validates a
call against the local `workflow_call` block — the defect class being audited
cannot occur there. The exclusion is empty in practice:

```bash
$ grep -rn "uses: *['\"]\?\./" .github/workflows/ | wc -l
0
```

**A divergence from the spec worth naming.** The spec's §D6 offers, *as an
illustration and explicitly not as the criterion*, "12 distinct refs across 9
workflow files", including `gemini-*.yml` files and two
`actions/github-script` refs that would need separate rows. **Those files do
not exist in this repository and never have:**

```bash
$ git ls-tree --name-only 2cb0d48 .github/workflows/
.github/workflows/ci.yml
.github/workflows/migrate.yml
.github/workflows/release.yml
$ git log --oneline --all -- '.github/workflows/gemini*'
(no output)
```

So the illustration was wrong about this tree, in a way the criterion
anticipated: the row set is derived from a recorded scan and no count is
hard-coded, and the derived answer is 6. There is consequently no
`actions/github-script` ref to give two rows to — a requirement that is vacuous
here rather than skipped.

### The rows

`with:` keys are **as of the landing commit**, post-fix. Method per row below
the table.

| Ref | Files (occurrences) | `with:` keys passed | Undeclared key? | Method |
| --- | --- | --- | --- | --- |
| `astral-sh/setup-uv@v8.1.0` | `ci.yml` ×3 (55, 160, 221), `migrate.yml` ×1 (17) | `version`, `enable-cache` | **No** — both declared; `pyproject-file` is gone | run log, run `36924174723`, jobs `110577272457` / `110577272946` / `110577272967` |
| `actions/checkout@v6` | `ci.yml` ×5 (50, 157, 218, 262, 303), `release.yml` ×2 (18, 41), `migrate.yml` ×1 (15) | `fetch-depth` on `ci.yml` 50 / 262 / 303; none on the other five | **No** — `fetch-depth` is declared | `action.yml` at `v6`, 21 inputs |
| `actions/setup-node@v6` | `release.yml` ×3 (20, 43, 68), `ci.yml` ×1 (267) | `node-version` | **No** — declared | `action.yml` at `v6`, 12 inputs |
| `actions/upload-artifact@v7` | `ci.yml` ×2 (101, 287) | `name`, `path` | **No** — both declared | `action.yml` at `v7`, 8 inputs |
| `actions/download-artifact@v8` | `ci.yml` ×2 (308, 314) | `name`, `path` | **No** — both declared | `action.yml` at `v8`, 10 inputs |
| `SonarSource/sonarqube-scan-action@v7` | `ci.yml` ×1 (320) | none — it is configured by `env:` (`GITHUB_TOKEN`, `SONAR_TOKEN`) | **No** — nothing passed, nothing to be undeclared | `action.yml` at `v7`, 5 inputs |

### The two methods, and which row may use which

**`gh api` on `action.yml` at the pinned ref — every row except `setup-uv`.**

```bash
gh api "repos/actions/checkout/contents/action.yml?ref=v6"              --jq '.content' | base64 -d
gh api "repos/actions/setup-node/contents/action.yml?ref=v6"            --jq '.content' | base64 -d
gh api "repos/actions/upload-artifact/contents/action.yml?ref=v7"       --jq '.content' | base64 -d
gh api "repos/actions/download-artifact/contents/action.yml?ref=v8"     --jq '.content' | base64 -d
gh api "repos/SonarSource/sonarqube-scan-action/contents/action.yml?ref=v7" --jq '.content' | base64 -d
```

The `inputs:` block each returned, in full, so the verdicts above can be
re-checked without re-fetching:

- `actions/checkout@v6` (21): `repository`, `ref`, `token`, `ssh-key`,
  `ssh-known-hosts`, `ssh-strict`, `ssh-user`, `persist-credentials`, `path`,
  `clean`, `filter`, `sparse-checkout`, `sparse-checkout-cone-mode`,
  **`fetch-depth`**, `fetch-tags`, `show-progress`, `lfs`, `submodules`,
  `set-safe-directory`, `github-server-url`, `allow-unsafe-pr-checkout`
- `actions/setup-node@v6` (12): **`node-version`**, `node-version-file`,
  `architecture`, `check-latest`, `registry-url`, `scope`, `token`, `cache`,
  `package-manager-cache`, `cache-dependency-path`, `mirror`, `mirror-token`
- `actions/upload-artifact@v7` (8): **`name`**, **`path`**,
  `if-no-files-found`, `retention-days`, `compression-level`, `overwrite`,
  `include-hidden-files`, `archive`
- `actions/download-artifact@v8` (10): **`name`**, `artifact-ids`, **`path`**,
  `pattern`, `merge-multiple`, `github-token`, `repository`, `run-id`,
  `skip-decompress`, `digest-mismatch`
- `SonarSource/sonarqube-scan-action@v7` (5): `args`, `projectBaseDir`,
  `scannerVersion`, `scannerBinariesUrl`, `skipSignatureVerification`

**The run-log `Unexpected input` method — the `setup-uv` row only.** The absence
of that warning is evidence *only for the specific jobs whose logs were read*.
The logs in hand are the three uv-using jobs of run `36924174723`
(`110577272457`, `110577272946`, `110577272967`) and the three of run
`37315213778`. Those jobs never run `actions/setup-node@v6`,
`actions/download-artifact@v8` or `SonarSource/sonarqube-scan-action@v7` — the
`frontend` and `sonarcloud` jobs do — and never run `release.yml`'s or
`migrate.yml`'s `actions/checkout@v6`. So every other row is settled by
`action.yml`, and the run log appears on the `setup-uv` row *in addition* to it.

---

## 7. Follow-ups

**Nothing outside `setup-uv` was modified by this task, and nothing outside
`setup-uv` needed to be.** The audit found **zero** undeclared-input findings on
the other five refs: every `with:` key this repository passes is declared at the
exact pinned ref.

One adjacent observation, recorded as a proposed follow-up rather than acted on
— it is **outside** the defect class this audit was scoped to (an undeclared
input), so it is not a finding of the table above:

- **Decide whether third-party action refs should be sha-pinned, or a
  `github-actions` dependabot ecosystem added.** Five of the six refs are
  floating major tags (`@v6`, `@v7`, `@v8`), so the code they run can change
  under this repository with no commit here; `.github/dependabot.yml` declares
  no `github-actions` ecosystem, so nothing proposes bumps either. The two
  options pull in opposite directions (sha pins are reproducible but need a
  bumper; an ecosystem keeps tags moving but adds PR traffic) and the choice is
  the operator's, which is why this is a task and not an edit.

---

## 8. Who bumps the pin, on what signal

Nothing bumps it automatically. Dependabot does not update a `version:` string
input, and with no `github-actions` ecosystem declared it would not move the
action ref either.

The pin is bumped **deliberately by the maintainer, in one commit** that edits
every `version:` literal in `.github/workflows/` together with APRAS-121's
`UV_PIN`. Editing one alone is a red test — §5.2 — which is the whole point of
the agreement assertion. The recurring human signal is APRAS-121's local
refusal: a developer who upgrades uv gets `export_requirements.sh` exiting
non-zero and naming `UV_PIN`, and that is what prompts the bump commit.

A stale pin is safe to sit on. uv is a build tool; what actually ships is
pinned by `backend/uv.lock` and `backend/requirements.txt`, so a stale uv
cannot ship a vulnerable library. This is written into `AGENTS.md`, and
`backend/tests/test_workflow_actions.py` asserts those claim strings are there.
