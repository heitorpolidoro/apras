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

The set of steps is derived from the tree, not from a list in a document.
**Every scan in this document is anchored to a named commit**, because a bare
`grep` over the working tree stops reproducing the moment another task lands —
which is exactly what happened to the first version of this document (§9).

At the pin commit `40d40a2`, read out of git rather than out of the working
tree, so it still reproduces today:

```bash
$ git grep -n 'astral-sh/setup-uv@' 40d40a2 -- .github/workflows/
40d40a2:.github/workflows/ci.yml:55:      uses: astral-sh/setup-uv@v8.1.0
40d40a2:.github/workflows/ci.yml:160:      uses: astral-sh/setup-uv@v8.1.0
40d40a2:.github/workflows/ci.yml:221:      uses: astral-sh/setup-uv@v8.1.0
40d40a2:.github/workflows/migrate.yml:17:    - uses: astral-sh/setup-uv@v8.1.0
$ git grep -o 'astral-sh/setup-uv@' 40d40a2 -- .github/workflows/ | wc -l
       4
```

**4 steps** at the pin commit: `ci.yml` (`backend`, `backend-migrations`,
`backend-lint`) and `migrate.yml` (`migrate`).

APRAS-121 landed **after** the pin, at `04eabec`, adding
`.github/workflows/requirements-export.yml` with a fifth `setup-uv` step. The
guard covers it with no edit, because both sides of its count assertion are
derived from the same scan. On the current tree:

```bash
$ grep -rn 'astral-sh/setup-uv@' .github/workflows/
.github/workflows/requirements-export.yml:106:      uses: astral-sh/setup-uv@v8.1.0
.github/workflows/migrate.yml:17:    - uses: astral-sh/setup-uv@v8.1.0
.github/workflows/ci.yml:55:      uses: astral-sh/setup-uv@v8.1.0
.github/workflows/ci.yml:224:      uses: astral-sh/setup-uv@v8.1.0
.github/workflows/ci.yml:285:      uses: astral-sh/setup-uv@v8.1.0
$ grep -rno 'astral-sh/setup-uv@' .github/workflows/ | wc -l
       5
```

`ci.yml`'s two later steps moved from lines 160/221 to 224/285 between
`40d40a2` and `04eabec` — APRAS-110, APRAS-119 and APRAS-121 all edited that
file. The **`uses:` set itself is unchanged** in all three tracked workflows,
which is what the inventory in §6 depends on:

```bash
$ for f in ci.yml migrate.yml release.yml; do \
    diff <(git show 40d40a2:.github/workflows/$f | grep -o 'uses: *[^ ]*') \
         <(grep -o 'uses: *[^ ]*' .github/workflows/$f) \
      && echo "$f: same uses set"; done
ci.yml: same uses set
migrate.yml: same uses set
release.yml: same uses set
```

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

`requirements-export.yml` has no job in this run because it did not exist at
`40d40a2`: APRAS-121 landed it afterwards, at `04eabec`. Its `setup-uv` step
holds the same `0.12.19` literal and is covered by the guard with no edit (§2,
§6 row 4).

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

**Recorded.** The push of `master` to `origin` fired `migrate.yml` run
`38268256257` (head `99a3d2d`, the first push after the pin landed at `40d40a2`,
which carried the pin plus the commits above it up to `4be622b`):

| Job | id | `conclusion` | uv version logged | `Falling back` / `Unexpected input` lines |
| --- | --- | --- | --- | --- |
| Run DB Migrations | `114875844696` | `success` | `Successfully installed uv version 0.12.19` | 0 / 0 |

What was known beforehand: the step is byte-identical in shape to the
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

**These four are dated observations, anchored at the pin commit `40d40a2`**, and
the `ci.yml:55` / `:160` / `:221` line numbers in them are that commit's — §2
shows those two later numbers have since moved to 224 and 285 as APRAS-110,
APRAS-119 and APRAS-121 edited the file. The anchoring is checkable without
re-applying any mutation:

```bash
$ git grep -n 'astral-sh/setup-uv@' 40d40a2 -- .github/workflows/ci.yml
40d40a2:.github/workflows/ci.yml:55:      uses: astral-sh/setup-uv@v8.1.0
40d40a2:.github/workflows/ci.yml:160:      uses: astral-sh/setup-uv@v8.1.0
40d40a2:.github/workflows/ci.yml:221:      uses: astral-sh/setup-uv@v8.1.0
```

Re-running them against today's tree would print 224/285 instead and would
require editing a workflow file, which is out of this document's scope.

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

### What is in `.github/workflows/`, and the correction this section carries

**The first version of this section was wrong, and it was wrong in the worst
available way: it reached a smaller row set through a recorded command
transcript that does not reproduce.** It printed

```
$ ls -1 .github/workflows/ | wc -l
3
```

That command prints **10** today and printed **9** at the pin commit. On the
strength of that transcript the section asserted that the `gemini-*.yml`
workflows "do not exist in this repository and never have", and omitted six
refs. The `git ls-tree` / `git log --all` evidence offered alongside it is
true but answers a different question — it proves the files are **not
committed**, not that they are **not there**. They are there, and they are
untracked only because `.gitignore` ignores them:

```bash
$ ls -1 .github/workflows/
ci.yml
gemini-dispatch.yml
gemini-invoke.yml
gemini-plan-execute.yml
gemini-review.yml
gemini-scheduled-triage.yml
gemini-triage.yml
migrate.yml
release.yml
requirements-export.yml
$ ls -1 .github/workflows/ | wc -l
      10
$ grep -n 'gemini-\*\.yml' .gitignore
132:.github/workflows/gemini-*.yml
$ git ls-tree --name-only HEAD .github/workflows/
.github/workflows/ci.yml
.github/workflows/migrate.yml
.github/workflows/release.yml
.github/workflows/requirements-export.yml
$ git status --porcelain .github/workflows/
(no output -- the four tracked files are unmodified, so the working tree
 equals 04eabec for everything git tracks here)
```

The six `gemini-*.yml` files have been in the working tree since 2026-05-14
(`ls -lT` mtime) and are ignored by `.gitignore:132`.

**They are audited anyway, not excluded.** A reasoned exclusion was available —
they are gitignored, have never been pushed, and therefore never execute on
GitHub — and that fact is recorded below as context on their rows. But the
exclusion is not taken, for two reasons. It is the same shrinking move the
broken transcript was used to justify, and a census is cheaper to trust when it
is complete: these files *are* authored in this repository, a future commit
could un-ignore them, and auditing them costs six `gh api` calls.

The evidence that they do not execute today, since the rows cite it:

```bash
$ gh api 'repos/:owner/:repo/contents/.github/workflows?ref=master' --jq '.[].name'
ci.yml
migrate.yml
release.yml
```

(`requirements-export.yml` is absent there too: local `master` is twelve
commits ahead of `origin/master` and nothing has been pushed.)

### The scan

Row set and count are derived from a scan of the tree; nothing here is a
hard-coded number. The `sed` strips the surrounding quotes the `gemini-*.yml`
files put around their `uses:` values, and `grep -v '^\./'` drops the
reusable-workflow calls excluded below.

```bash
$ grep -rhno "uses: *[^ ]*" .github/workflows/ \
    | sed "s/.*uses: *//; s/^['\"]//; s/['\"]$//" \
    | grep -v '^\./' | sort | uniq -c | sort -rn
   9 actions/checkout@v6
   7 actions/create-github-app-token@29824e69f54612133e76f7eaac726eef6c875baf
   5 google-github-actions/run-gemini-cli@v0
   5 astral-sh/setup-uv@v8.1.0
   4 actions/setup-node@v6
   4 actions/github-script@ed597411d8f924073f98dfc5c65a23a2325f34cd
   2 actions/upload-artifact@v7
   2 actions/download-artifact@v8
   2 actions/checkout@v4
   1 actions/github-script@60a0d83039c74a4aee543508d2ffcb1c3799cdea
   1 actions/checkout@8e8c483db84b4bee98b60c0593521ed34d9990e8
   1 SonarSource/sonarqube-scan-action@v7
$ grep -rhno "uses: *[^ ]*" .github/workflows/ \
    | sed "s/.*uses: *//; s/^['\"]//; s/['\"]$//" | grep -v '^\./' | sort -u | wc -l
      12
$ grep -rhno "uses: *[^ ]*" .github/workflows/ \
    | sed "s/.*uses: *//; s/^['\"]//; s/['\"]$//" | grep -v '^\./' | wc -l
      43
$ grep -rln "uses: *[^ ]*" .github/workflows/ | wc -l
      10
```

**12 distinct third-party refs across 10 workflow files, 43 occurrences.**

The same scan with `requirements-export.yml` removed — i.e. the tree as it stood
at the pin commit `40d40a2`, which §2 showed has an identical `uses:` set in the
three tracked files — gives the same **12** refs across **9** files, 41
occurrences:

```bash
$ grep -rhno "uses: *[^ ]*" .github/workflows/ \
    --exclude=requirements-export.yml \
    | sed "s/.*uses: *//; s/^['\"]//; s/['\"]$//" | grep -v '^\./' | sort -u | wc -l
      12
$ grep -rhno "uses: *[^ ]*" .github/workflows/ \
    --exclude=requirements-export.yml \
    | sed "s/.*uses: *//; s/^['\"]//; s/['\"]$//" | grep -v '^\./' | wc -l
      41
```

So APRAS-121's file **introduces no new ref** — its two steps are
`actions/checkout@v6` and `astral-sh/setup-uv@v8.1.0`, both already present:

```bash
$ grep -n 'uses:' .github/workflows/requirements-export.yml
99:      uses: actions/checkout@v6
106:      uses: astral-sh/setup-uv@v8.1.0
```

The ref count is therefore **12**, not the 13 the spec's §D6 allowed for the
case where that file had introduced a fourth `actions/checkout` ref. It did
not.

Reusable-workflow calls (`uses: './.github/workflows/*.yml'`) are **excluded**,
because their inputs are declared in this repository and GitHub validates a
call against the local `workflow_call` block — the defect class being audited
cannot occur there. The exclusion is **not** empty, contrary to what the first
version of this section recorded:

```bash
$ grep -rn "uses: *['\"]\?\./" .github/workflows/
.github/workflows/gemini-dispatch.yml:132:    uses: './.github/workflows/gemini-review.yml'
.github/workflows/gemini-dispatch.yml:146:    uses: './.github/workflows/gemini-triage.yml'
.github/workflows/gemini-dispatch.yml:160:    uses: './.github/workflows/gemini-invoke.yml'
.github/workflows/gemini-dispatch.yml:174:    uses: './.github/workflows/gemini-plan-execute.yml'
$ grep -rn "uses: *['\"]\?\./" .github/workflows/ | wc -l
       4
```

### The rows

Twelve rows, one per distinct ref, in the order the scan above printed them.
`with:` keys are the union of the keys passed at every occurrence of that ref;
where occurrences differ, the per-occurrence breakdown is given. Line numbers
are the current tree (`04eabec` plus the six ignored files); for `setup-uv`,
`40d40a2`'s numbers are given too, since the mutation transcripts in §5 cite
them.

The two `actions/github-script` refs are **two separate rows**, as the spec
requires: they are separately pinned shas, carrying `ratchet:` comments for
`v8.0.0` and `v7` respectively.

| # | Ref | Files (occurrences) | `with:` keys passed | Undeclared key? | Method |
| --- | --- | --- | --- | --- | --- |
| 1 | `actions/checkout@v6` | `ci.yml` ×5 (50, 221, 282, 326, 367), `release.yml` ×2 (18, 41), `migrate.yml` ×1 (15), `requirements-export.yml` ×1 (99) — **9** | `fetch-depth` on `ci.yml` 50/326/367; `ref`, `persist-credentials`, `fetch-depth` on `requirements-export.yml` 99; none on the other five | **No** — all three are declared | `action.yml` at `v6`, 21 inputs |
| 2 | `actions/create-github-app-token@29824e69f54612133e76f7eaac726eef6c875baf` | `gemini-dispatch.yml` ×2 (76, 203), `gemini-invoke.yml` (32), `gemini-plan-execute.yml` (34), `gemini-review.yml` (33), `gemini-scheduled-triage.yml` (156), `gemini-triage.yml` (117) — **7** | `app-id`, `private-key`, `permission-contents`, `permission-issues`, `permission-pull-requests` (identical at all seven) | **No** — all five declared | `action.yml` at `29824e6`, 56 inputs |
| 3 | `google-github-actions/run-gemini-cli@v0` | `gemini-invoke.yml` (45), `gemini-plan-execute.yml` (47), `gemini-review.yml` (45), `gemini-scheduled-triage.yml` (95), `gemini-triage.yml` (62) — **5** | union of 18: `gcp_location`, `gcp_project_id`, `gcp_service_account`, `gcp_workload_identity_provider`, `gemini_api_key`, `gemini_cli_version`, `gemini_debug`, `gemini_model`, `google_api_key`, `use_gemini_code_assist`, `use_vertex_ai`, `upload_artifacts`, `workflow_name`, `settings`, `prompt`, `github_pr_number` (invoke/plan-execute/review), `github_issue_number` (invoke/plan-execute/scheduled-triage/triage), `extensions` (review only) | **No** — all 18 declared | `action.yml` at `v0`, 21 inputs |
| 4 | `astral-sh/setup-uv@v8.1.0` | `ci.yml` ×3 (55, 224, 285 — `40d40a2`: 55, 160, 221), `migrate.yml` ×1 (17), `requirements-export.yml` ×1 (106) — **5** | `version`, `enable-cache`; plus `checksum` on `requirements-export.yml` 106 (APRAS-121's). **No `pyproject-file`** | **No** — all three declared; the undeclared input this task removed is gone | `action.yml` at `v8.1.0`, 24 inputs — **and** run log, run `36924174723`, jobs `110577272457` / `110577272946` / `110577272967` |
| 5 | `actions/setup-node@v6` | `ci.yml` ×1 (331), `release.yml` ×3 (20, 43, 68) — **4** | `node-version` | **No** — declared | `action.yml` at `v6`, 12 inputs |
| 6 | `actions/github-script@ed597411d8f924073f98dfc5c65a23a2325f34cd` | `gemini-scheduled-triage.yml` ×2 (43, 168), `gemini-triage.yml` ×2 (34, 130) — **4** | `script` at 43/34; `script`, `github-token` at 168/130 | **No** — both declared | `action.yml` at `ed59741`, 9 inputs |
| 7 | `actions/upload-artifact@v7` | `ci.yml` ×2 (165, 351) — **2** | `name`, `path` | **No** — both declared | `action.yml` at `v7`, 8 inputs |
| 8 | `actions/download-artifact@v8` | `ci.yml` ×2 (372, 378) — **2** | `name`, `path` | **No** — both declared | `action.yml` at `v8`, 10 inputs |
| 9 | `actions/checkout@v4` | `gemini-invoke.yml` (41), `gemini-plan-execute.yml` (43) — **2** | none | **No** — nothing passed, nothing to be undeclared | `action.yml` at `v4`, 21 inputs |
| 10 | `actions/github-script@60a0d83039c74a4aee543508d2ffcb1c3799cdea` | `gemini-dispatch.yml` ×1 (86) — **1** | `script` | **No** — declared | `action.yml` at `60a0d83`, 9 inputs |
| 11 | `actions/checkout@8e8c483db84b4bee98b60c0593521ed34d9990e8` | `gemini-review.yml` ×1 (42) — **1** | none | **No** — nothing passed | `action.yml` at `8e8c483`, 20 inputs |
| 12 | `SonarSource/sonarqube-scan-action@v7` | `ci.yml` ×1 (384) — **1** | none — configured by `env:` (`GITHUB_TOKEN`, `SONAR_TOKEN`) | **No** — nothing passed | `action.yml` at `v7`, 5 inputs |

Occurrence counts sum to 9+7+5+5+4+4+2+2+2+1+1+1 = **43**, matching the scan.

Rows 2, 3, 6, 9, 10 and 11 are the six refs the first version of this section
omitted. All six live only in the `gemini-*.yml` files, which are gitignored
(`.gitignore:132`), have never been committed, and are absent from
`origin/master` — so **none of them executes on GitHub today**. That is context,
not an exclusion: their verdicts are given on the same footing as every other
row.

**One spec claim corrected.** §D6 says the two `actions/github-script` refs
"are separately pinned shas … and their declared inputs are not the same set".
The first half is right; the second is **false**. Both refs declare the
identical nine inputs, and the only difference between the two `action.yml`
files is the runtime:

```bash
$ diff <(gh api "repos/actions/github-script/contents/action.yml?ref=ed597411d8f924073f98dfc5c65a23a2325f34cd" --jq '.content' | base64 -d) \
       <(gh api "repos/actions/github-script/contents/action.yml?ref=60a0d83039c74a4aee543508d2ffcb1c3799cdea" --jq '.content' | base64 -d)
39c39
<   using: node24
---
>   using: node20
```

They still get separate rows, because the row set is one row per distinct ref
and because the equality is a finding of this audit rather than an assumption
of it. The same holds for `actions/checkout@v4` and `@v6`, whose input sets are
also identical (21 names each; `using: node20` vs `node24`) while `@8e8c483`
declares **20**, lacking `allow-unsafe-pr-checkout`. That sha is
`actions/checkout` **`v6.0.1`**:

```bash
$ gh api repos/actions/checkout/git/refs/tags --jq '.[] | "\(.ref) \(.object.sha)"' \
    | grep 8e8c483db84b4bee98b60c0593521ed34d9990e8
refs/tags/v6.0.1 8e8c483db84b4bee98b60c0593521ed34d9990e8
```

— so the floating `@v6` tag this repository's own workflows use has **moved
past `v6.0.1` and gained an input** since that sha was cut. Nothing in
`.github/workflows/` passes `allow-unsafe-pr-checkout`, so this is not a
finding; it is a measured instance of the drift the first follow-up in §7 is
about, and worth recording as such rather than as an abstraction.

### The two methods, and which row may use which

**`gh api` on `action.yml` at the pinned ref — every row, `setup-uv` included
(the spec requires it for every row *except* `setup-uv`; it was run on
`setup-uv` as well, as a cross-check against the run-log warning, and the two
agree on all 24 names).**

```bash
gh api "repos/actions/checkout/contents/action.yml?ref=v6"                                                     --jq '.content' | base64 -d
gh api "repos/actions/checkout/contents/action.yml?ref=v4"                                                     --jq '.content' | base64 -d
gh api "repos/actions/checkout/contents/action.yml?ref=8e8c483db84b4bee98b60c0593521ed34d9990e8"               --jq '.content' | base64 -d
gh api "repos/actions/setup-node/contents/action.yml?ref=v6"                                                   --jq '.content' | base64 -d
gh api "repos/actions/upload-artifact/contents/action.yml?ref=v7"                                              --jq '.content' | base64 -d
gh api "repos/actions/download-artifact/contents/action.yml?ref=v8"                                            --jq '.content' | base64 -d
gh api "repos/SonarSource/sonarqube-scan-action/contents/action.yml?ref=v7"                                    --jq '.content' | base64 -d
gh api "repos/actions/create-github-app-token/contents/action.yml?ref=29824e69f54612133e76f7eaac726eef6c875baf" --jq '.content' | base64 -d
gh api "repos/actions/github-script/contents/action.yml?ref=ed597411d8f924073f98dfc5c65a23a2325f34cd"          --jq '.content' | base64 -d
gh api "repos/actions/github-script/contents/action.yml?ref=60a0d83039c74a4aee543508d2ffcb1c3799cdea"          --jq '.content' | base64 -d
gh api "repos/google-github-actions/run-gemini-cli/contents/action.yml?ref=v0"                                 --jq '.content' | base64 -d
gh api "repos/astral-sh/setup-uv/contents/action.yml?ref=v8.1.0"                                               --jq '.content' | base64 -d
```

The `inputs:` names each returned, in full, so the verdicts above can be
re-checked without re-fetching. Keys this repository actually passes are
**bold**.

- `actions/checkout@v6` (21): `repository`, **`ref`**, `token`, `ssh-key`,
  `ssh-known-hosts`, `ssh-strict`, `ssh-user`, **`persist-credentials`**,
  `path`, `clean`, `filter`, `sparse-checkout`, `sparse-checkout-cone-mode`,
  **`fetch-depth`**, `fetch-tags`, `show-progress`, `lfs`, `submodules`,
  `set-safe-directory`, `github-server-url`, `allow-unsafe-pr-checkout`
- `actions/checkout@v4` (21): identical names to `@v6` (see the `diff` above).
  Nothing is passed at either occurrence.
- `actions/checkout@8e8c483` (20): the `@v6` list minus
  `allow-unsafe-pr-checkout`. Nothing is passed.
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
- `actions/create-github-app-token@29824e6` (56): **`app-id`**,
  **`private-key`**, `owner`, `repositories`, `skip-token-revoke`,
  `github-api-url`, then 50 `permission-*` names, among them
  **`permission-contents`**, **`permission-issues`** and
  **`permission-pull-requests`**.
- `actions/github-script@ed59741` (9): **`script`**, **`github-token`**,
  `debug`, `user-agent`, `previews`, `result-encoding`, `retries`,
  `retry-exempt-status-codes`, `base-url`
- `actions/github-script@60a0d83` (9): the same nine names; **`script`** is the
  only one passed.
- `google-github-actions/run-gemini-cli@v0` (21): **`gcp_location`**,
  **`gcp_project_id`**, **`gcp_service_account`**,
  **`gcp_workload_identity_provider`**, `gcp_token_format`,
  `gcp_access_token_scopes`, **`gemini_api_key`**, **`gemini_cli_version`**,
  **`gemini_debug`**, **`gemini_model`**, **`google_api_key`**, **`prompt`**,
  **`settings`**, **`use_gemini_code_assist`**, **`use_vertex_ai`**,
  **`extensions`**, **`upload_artifacts`**, `use_pnpm`, **`workflow_name`**,
  **`github_pr_number`**, **`github_issue_number`**
- `astral-sh/setup-uv@v8.1.0` (24): **`version`**, `version-file`,
  `python-version`, `activate-environment`, `venv-path`, `no-project`,
  `working-directory`, **`checksum`**, `github-token`, **`enable-cache`**,
  `cache-dependency-glob`, `restore-cache`, `save-cache`, `cache-suffix`,
  `cache-local-path`, `prune-cache`, `cache-python`,
  `ignore-nothing-to-cache`, `ignore-empty-workdir`, `tool-dir`,
  `tool-bin-dir`, `manifest-file`, `add-problem-matchers`,
  `resolution-strategy` — **the same 24 names, in the same order, as the
  runner's `Unexpected input(s)` warning quoted in §1**, which is what makes
  that warning usable as the guard's provenance.

**The run-log `Unexpected input` method — the `setup-uv` row only.** The absence
of that warning is evidence *only for the specific jobs whose logs were read*.
The logs in hand are the three uv-using jobs of run `36924174723`
(`110577272457`, `110577272946`, `110577272967`) and the three of run
`37315213778`. Those jobs never run `actions/setup-node@v6`,
`actions/download-artifact@v8` or `SonarSource/sonarqube-scan-action@v7` — the
`frontend` and `sonarcloud` jobs do — never run `release.yml`'s,
`migrate.yml`'s or `requirements-export.yml`'s `actions/checkout@v6`, and never
run anything in the `gemini-*.yml` files, which do not execute at all. So every
other row is settled by `action.yml`, and the run log appears on the `setup-uv`
row *in addition* to it.

**Verdict across all twelve rows: zero undeclared inputs.** Every `with:` key
this repository passes, at every one of the 43 occurrences, is declared at the
exact pinned ref — now that `pyproject-file` is gone.

---

## 7. Follow-ups

**Nothing outside `setup-uv` was modified by this task, and nothing outside
`setup-uv` needed to be.** The audit found **zero** undeclared-input findings on
the other eleven refs: every `with:` key this repository passes is declared at
the exact pinned ref.

Two adjacent observations, recorded as proposed follow-ups rather than acted on.
Both are **outside** the defect class this audit was scoped to (an undeclared
input), so neither is a finding of the table above:

- **Decide whether third-party action refs should be sha-pinned, or a
  `github-actions` dependabot ecosystem added.** Eight of the twelve refs are
  mutable tags (`@v0`, `@v4`, `@v6`, `@v7`, `@v8`, `@v8.1.0`), so the code they
  run can change under this repository with no commit here;
  `.github/dependabot.yml` declares only `uv` and `npm`, so nothing proposes
  bumps either. The other four are already sha-pinned
  (`actions/checkout@8e8c483`, `actions/create-github-app-token@29824e6`, the
  two `actions/github-script` shas), which is the `gemini-*.yml` files'
  convention and not this repository's — so the two halves of
  `.github/workflows/` disagree about pinning policy. The options pull in
  opposite directions (sha pins are reproducible but need a bumper; an
  ecosystem keeps tags moving but adds PR traffic) and the choice is the
  operator's, which is why this is a task and not an edit.
- **Decide what the six gitignored `gemini-*.yml` workflows are for, and either
  commit them or delete them.** They have sat untracked in
  `.github/workflows/` since 2026-05-14, ignored by `.gitignore:132`, absent
  from `origin/master`, and therefore never executed — while carrying a
  `create-github-app-token` step with `contents`, `issues` and `pull-requests`
  write permissions, and a `gemini-dispatch.yml` that calls four of them as
  reusable workflows. Untracked-but-present is the state that broke the first
  version of this audit's census, and it will break the next reader the same
  way. Either state is fine; the ambiguity is not.

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

---

## 9. Every recorded transcript in this document, re-run

A `$ command` → output block in a document is a **claim**, and the defect that
sent this document back for rework was not the six missing inventory rows — it
was that the transcript used to justify omitting them did not reproduce. So
every command block in this document has been re-executed and the result
recorded here. Twenty-two blocks; eighteen re-runnable under this round's
constraints; **six corrected.**

| # | § | Transcript | Re-ran? | Result |
| --- | --- | --- | --- | --- |
| 1 | 1 | `gh api .../runs/36924174723/jobs --jq ...` | yes | **reproduces** — same five job ids, names and `success` conclusions |
| 2 | 1 | `gh run view --job 110577272457/946/967 --log \| grep -E ...` | yes | **reproduces** — same warning, same `Falling back to latest`, same `0.12.21`, same timestamps `20:47:47.2103370Z` / `20:47:46.0495934Z` / `20:48:08.8191969Z` |
| 3 | 1 | prose: `grep -c 'Unexpected input'` returned 2 per job | yes | **reproduces** — 2, 2, 2 (main step + post step) |
| 4 | 2 | `grep -rn 'pyproject-file' .github/workflows/ \| wc -l` → `0` | yes | **reproduces** — still 0, over all ten files |
| 5 | 2 | `grep -rc 'astral-sh/setup-uv@' .github/workflows/` → 3 lines | yes | **CORRECTED** — printed three files; prints ten today. Replaced with a `git grep` anchored at `40d40a2` plus the current-tree scan |
| 6 | 2 | `grep -rno 'astral-sh/setup-uv@' ... \| wc -l` → `4` | yes | **CORRECTED** — 5 today (APRAS-121's fifth step). Both values now recorded, each against its commit |
| 7 | 3 | `gh run view 37315213778 --json headSha,attempt,event,headBranch,conclusion` | yes | **reproduces** — byte-identical JSON, `headSha` `40d40a2bc4ccc490df9f65adfc94ead9b645d0bc`, `attempt` 1, `conclusion` `success` |
| 8 | 3 | quoted `questions` entry `q-1790947582472-122`, `answer` `yes`, `answered_at` `2026-10-02T13:33:08.907Z` | yes | **reproduces** — matches the task record in `.meridian/tasks.jsonl` exactly, including `by: "Agent"` |
| 9 | 4 | `gh api .../runs/37315213778/jobs --jq ...` | yes | **reproduces** — same five job ids and `success` conclusions |
| 10 | 4 | `gh run view --job 111780127073/126776/127158 --log \| grep -E ...` | yes | **reproduces** — one `Successfully installed uv version 0.12.19` per job, `grep -c 'Falling back to latest'` 0, `grep -c 'Unexpected input'` 0, same timestamps |
| 11 | 5.1 | mutation `m1-pyproject-file-readded` pytest output | no | dated observation at `40d40a2`; re-running needs a workflow edit, out of scope. Its `ci.yml:55` anchor **verified** by `git grep` at that commit |
| 12 | 5.2 | mutation `m2-one-version-literal-changed` pytest output | no | same; its `ci.yml:55/160/221` anchors **verified** at `40d40a2` |
| 13 | 5.3 | mutation `m3-one-version-input-deleted` pytest output | no | same; `ci.yml:55` anchor **verified** |
| 14 | 5.4 | mutation `m4-unknown-setup-uv-ref` pytest output | no | same; `ci.yml:55` anchor **verified** |
| 15 | 5 | prose: `.github/dependabot.yml` declares only `uv` and `npm` | yes | **reproduces** — `grep -n 'package-ecosystem' .github/dependabot.yml` → `26: "uv"`, `60: "npm"`; no `github-actions` |
| 16 | 6 | `ls -1 .github/workflows/ \| wc -l` → `3` | yes | **CORRECTED** — prints `10`. This is the finding that sent the round back; the full listing and `.gitignore:132` now stand in its place |
| 17 | 6 | `grep -rhno 'uses: ...' \| sort \| uniq -c \| sort -rn` → 6 rows | yes | **CORRECTED** — 12 rows. The old `sed` also failed to strip the quotes the `gemini-*.yml` files put around `uses:` values; the replacement strips them |
| 18 | 6 | `grep ... \| sort -u \| wc -l` → `6` | yes | **CORRECTED** — `12` distinct refs, 43 occurrences, 10 files |
| 19 | 6 | `grep -rn "uses: *['\"]\?\./" ... \| wc -l` → `0` ("the exclusion is empty in practice") | yes | **CORRECTED** — `4`. `gemini-dispatch.yml` calls four local reusable workflows at lines 132, 146, 160, 174 |
| 20 | 6 | `git ls-tree --name-only 2cb0d48 .github/workflows/` → 3 files | yes | **reproduces**, but its *conclusion* was wrong and has been withdrawn: it proves the `gemini-*.yml` files are not **committed**, not that they are not **there** |
| 21 | 6 | `git log --oneline --all -- '.github/workflows/gemini*'` → no output | yes | **reproduces**, same withdrawn conclusion |
| 22 | 6 | `gh api .../contents/action.yml?ref=<ref>` ×5, with their `inputs:` name lists | yes | **all five reproduce** — `checkout@v6` 21, `setup-node@v6` 12, `upload-artifact@v7` 8, `download-artifact@v8` 10, `sonarqube-scan-action@v7` 5. Seven more refs fetched this round to complete the census |

Two further claims that are not transcripts were checked and one was wrong:

- the spec's "[the two `github-script` refs'] declared inputs are not the same
  set" — **false**, corrected in §6 with the `diff` that shows it;
- `requirements-export.yml` introduces no new ref — **true**, derived in §6
  rather than taken on trust.

**What changed in method, and why it should hold.** Every scan in this document
is now either anchored to a commit (`git grep <sha>`, `git show <sha>:<path>`)
or stated as a working-tree scan whose tree is identified by sha plus the named
untracked files, with `git status --porcelain .github/workflows/` recorded to
show the tracked half is unmodified. An unanchored `grep` over a working tree
that other tasks are landing into is not evidence a later reader can check, and
that is precisely how six rows went missing.
