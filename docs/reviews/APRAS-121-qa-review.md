# APRAS-121 — QA verification

**Task:** Make dependabot's uv runs regenerate requirements.txt with the lock
**Worktree:** `/Users/heitor/workspace/apras/.claude/worktrees/agent-ae6a8748df8e73027` at `8487258`
**Date:** 2026-10-09
**Local uv:** `0.12.19` (Homebrew), which matches the pin under verification — so the pinned path is the path that actually ran.

VERDICT: APPROVED

---

## Method summary

Everything behavioural was executed, not read. Scratch harnesses live under
`/private/tmp/claude-501/-Users-heitor-workspace-apras/06230b8a-d0ef-40dd-929b-83bb4eb6abbf/scratchpad/qa121/`
(`r4mutant.sh`, `r2r3.sh`, `r3mut.sh`, `r6mut.sh`, `r6b.sh`, `r6c.sh`, `r5.sh`, `r5lock.sh`, `r8.sh`, `nouv.sh`, `extract.py`).

Baseline: `tests/test_requirements_export.py` — **42 passed**. `tests/test_requirements_export.py` + `tests/test_workflow_actions.py` — **57 passed**. Full backend suite collects cleanly (**4256 tests collected**); the DB-backed remainder was not executed (no local Postgres), and none of the eleven results depends on it.

Fifteen mutants were built and run. Every one went red, and in each case the mutation was confirmed present on disk before pytest ran. Every mutated file was restored and the restore verified with `cmp`.

---

## Expected Results Checked

### R1 — the script is the only definition of the export command
- [x] **Verified** via `grep -rn` for the invocation across `.github/`, `backend/tests/`, `AGENTS.md`, `backend/scripts/`.
- Exactly one hit, tree-wide: `backend/scripts/export_requirements.sh:96`. No workflow, no test module and not `AGENTS.md` spells one of its own.
- The two documented exclusions were respected: `backend/requirements.txt`'s generated header does carry the text (line 2), and `docs/**` was not searched.
- The script exists, is a file, and is executable: working-tree mode `755`, **and the staged index mode is `100755`** — so the exec bit survives the commit, not just the local filesystem.

### R2 — fixed argument list, `--frozen`, invocation-site-independent
- [x] **Verified** by reading the argv construction and then regenerating from two different absolute paths.
- The single top-level invocation (line 96) is:
  `uv export --format requirements-txt --no-hashes --frozen -o requirements.txt`
  `--frozen` present; no `--directory`; no `$`, no backtick, no `{{` — nothing taken from the environment; no conditional flags (one unconditional `uv` line in the file, confirmed by the test's `_script_invocation` assertion of exactly one).
- Line 2 of the committed export, comment marker stripped, is byte-equal to that line.
- **Site-independence executed:** regenerating from a throwaway repository at a completely different absolute path (`.../qa121/sim`) produced a `requirements.txt` byte-identical to the committed one (`cmp` clean). Run from `backend/` instead of the repository root the script refuses and writes nothing (`exit 1`, message naming `backend/pyproject.toml`), so there is no second site that produces a different header.

### R3 — one uv version for every consumer
- [x] **Verified** by inspection plus four mutants.
- `UV_PIN="0.12.19"` is in the script. `.github/workflows/requirements-export.yml` passes `version: "0.12.19"`; `ci.yml`'s `backend` job (`name: Backend Tests`) passes `version: "0.12.19"`.
- `pyproject-file:` appears nowhere under `.github/` (grep exit 1), so `Backend Tests`' `setup-uv` no longer passes it.
- `backend/pyproject.toml` has no `[tool.uv]` table at all, hence no `required-version` (grep exit 1); the file is not even in this task's staged set.
- **Refusal executed.** With a stub `uv` on `PATH` reporting `0.13.0`: `exit 1`, message `error: this script is pinned to uv UV_PIN=0.12.19, but uv --version reports 0.13.0.` — it names `UV_PIN` and the found version, as required. With `uv` absent from `PATH` entirely: `exit 1`, `error: uv is not on PATH; this script needs uv 0.12.19.`, and the committed export was left unchanged (`cmp` clean) — it fails closed rather than writing a wrong-headed file.
- **Each of the three literals mutated alone** (to `0.12.20`), suite re-run each time:

  | mutant | result |
  |---|---|
  | script `UV_PIN` | **3 failed** (`..._ci_backend_job_pins...`, `..._setup_uv_step_pins...`, `..._export_workflow_pins...`) |
  | `ci.yml` backend-job `version:` | **1 failed** (`..._ci_backend_job_pins_the_scripts_uv_version`) |
  | `requirements-export.yml` `version:` | **2 failed** (`..._setup_uv_step_pins...`, `..._export_workflow_pins...`) |

- **Comment-satisfaction attack run, as instructed.** I mutated the real `ci.yml` literal to `0.12.20` *and* added a decoy comment line `# version: "0.12.19"` immediately below it. The suite still went red (`test_the_ci_backend_job_pins_the_scripts_uv_version`). The locator (`_job_block`) blanks comment-only lines by default and `test_the_backend_job_locator_really_lands_on_the_backend_job` asserts that stripping happened, so prose cannot satisfy this assertion. This is the specific defect class flagged for this repository, and it is closed here.

### R4 — regeneration is byte-exact, and the diff step is not vacuous
- [x] **Verified by execution.**
- Deleted `backend/requirements.txt` (absence confirmed by `ls`), ran `bash backend/scripts/export_requirements.sh` from the repository root (`exit 0`). The regenerated file hashed `752b72ce87eecf61b254870ea2926dbcdba76a67e30f895f7ef29dcadd6a1111`, identical to the pre-deletion copy; `cmp` clean.
- `git diff --exit-code -- backend/requirements.txt` on `master` in the worktree: **exit 0**, clean.
- **Mutant, in a throwaway repository** (necessary: the CI step compares the work tree against the *index*, so the hand edit has to be the committed one, and I may not touch the staged content). Committed `qrcode==8.1` in place of `8.2`, confirmed via `git show HEAD:backend/requirements.txt`, then ran the step verbatim:
  `bash backend/scripts/export_requirements.sh && git diff --exit-code -- backend/requirements.txt` → **exit 1**, diff showing `-qrcode==8.1 / +qrcode==8.2`.
- Additionally, two in-worktree parity mutants: a hand-edited pin failed `test_every_export_pin_matches_the_locked_version`; a removed pin failed `test_every_locked_package_is_pinned_in_the_export`. Both restored, both restores verified.

### R5 — dry-run isolation, the `cd8de18` failure, and lock freshness
- [x] **Verified by execution.**
- The step's text uses `uv venv --python 3.13 "$RUNNER_TEMP/export-check"` — `3.13` written out literally, not read from `backend/.python-version` (which also says `3.13`; the point is that the step does not depend on it) — and `uv pip install --dry-run --python "$RUNNER_TEMP/export-check" -r backend/requirements.txt`, so it is independent of `backend/.venv`.
- I created that interpreter for real under a temp `$RUNNER_TEMP`: `Using CPython 3.13.13`, fresh venv, `Python 3.13.13`.
- Dry-run of the **committed** export in it: **exit 0**, full resolution.
- Dry-run of the export from **`cd8de18`** (`pydantic==2.13.5` beside `pydantic-core==2.49.0`) in the same interpreter: **exit 1** —
  `error: No solution found when resolving dependencies ... Because pydantic==2.13.5 depends on pydantic-core==2.46.5 ... your requirements are unsatisfiable.`
  So the check really does catch the historical breakage.
- `uv lock --check` is a step in the **same job** and **precedes** the dry-run (order in `ci.yml`: lock-check → regenerate-and-diff → dry-run).
- **Staleness executed** in a throwaway copy of `backend/pyproject.toml` + `backend/uv.lock`: adding `"rich>=13"` to `dependencies` and leaving the lock alone made `uv lock --check` **exit 1** (`error: The lockfile at `uv.lock` needs to be updated, but `--check` was provided.`). In the real worktree, unmutated, it exits 0.

### R6 — the guard test's shape, its non-vacuity, and its offline contract
- [x] **(a) Verified.** The module holds no contiguous `uv export` literal — the tree-wide grep in R1 found zero hits in it — and the needle is assembled at run time from `_NEEDLE_TOOL` / `_NEEDLE_OPTIONS` / `_NEEDLE_GAP` / `_NEEDLE_SUBCOMMAND`. `test_the_guard_pattern_is_not_spelled_out_in_this_file` enforces this against the module's own source, with no `__file__` carve-out.
- [x] **(b) Verified by four plants, each caught:**

  | plant | detected as |
  |---|---|
  | real `run:` line inside existing `.github/workflows/ci.yml` | `.github/workflows/ci.yml:69` |
  | brand-new file `.github/workflows/zz-qa-probe.yml` | `.github/workflows/zz-qa-probe.yml:5` |
  | string literal appended to `backend/tests/test_workflow_actions.py` | `backend/tests/test_workflow_actions.py:535` |
  | comment-only line in `.github/workflows/ci.yml` | `.github/workflows/ci.yml:66` |

  All four failed `test_the_export_script_is_the_only_definition_of_the_command`. Note the guard is deliberately *stricter* than comment-blind: a commented-out second definition is also a failure, which is the right direction for an absence assertion. On the comment question raised for this repository: a comment cannot *rescue* a failing assertion here (shown under R3), and it cannot *hide* a planted definition either.
  Anti-vacuity of the detector itself: breaking `_NEEDLE_SUBCOMMAND` to a nonsense string turned `test_the_generated_header_still_carries_an_invocation` red, so the pattern cannot silently decay into one that matches nothing.
- [x] **(c) Verified.** With the generated header in place the suite is green, and `test_the_generated_header_still_carries_an_invocation` positively asserts the header matches on line 2 *and* that `backend/requirements.txt` is outside `_guarded_files()` — so the exclusion is pinned rather than assumed.
- [x] **Read-set / no-subprocess / no-network verified by inspection and by mutation.** The module imports only `ast`, `re`, `tomllib`, `pathlib` — no `subprocess`, `socket`, `urllib`, `http`, `requests`, `httpx`. `_guarded_files()` yields only `.github/workflows/*`, `backend/tests/*.py` and `AGENTS.md`; parity reads only `backend/requirements.txt` and `backend/uv.lock`. All reads are working-tree files; no `uv` subprocess is invoked anywhere in the module. Three self-contract tests enforce this via AST, and I confirmed they are not vacuous:
  - adding `import subprocess` + a `subprocess.check_output(["uv","--version"])` call → **2 failed** (`..._imports_nothing_that_could_reach_the_network`, `..._makes_no_subprocess_or_network_call`);
  - adding a `Path("/etc/hosts").read_text()` → **1 failed** (`..._reads_only_files_in_the_working_tree`).
  Both restored and verified.

### R7 — the privileged workflow's shape (all eight clauses)
- [x] **1. Base-sha fetch.** `git fetch --no-tags --depth=1 origin "$BASE_SHA"` present verbatim, with `BASE_SHA: ${{ github.event.pull_request.base.sha }}` in the step's `env:`.
- [x] **2. Base-sha read.** `git show "$BASE_SHA":backend/scripts/export_requirements.sh > "$RUNNER_TEMP/export_requirements.sh"` present verbatim.
- [x] **3. Not relying on head history or a second checkout.** Exactly **one** `uses: actions/checkout` in the file (the other three `actions/checkout` grep hits are comment lines). Proven at run time: in my simulated **Path C** the base sha was an *orphan* commit with no ancestry relationship to the head at all, and the explicit fetch still retrieved it in a `--depth=1` checkout — which is precisely the case a reliance on head history would have failed.
- [x] **4. Invocation form.** `bash "$RUNNER_TEMP/export_requirements.sh"` present verbatim; executed that way in the simulation.
- [x] **5. Missing-script failure names the path.** Executed (Path C): **exit 1** with
  `::error::backend/scripts/export_requirements.sh does not exist at base sha <sha>, so the regeneration mechanism is not on the base branch yet...`
- [x] **6. Push refspec.** `git push origin HEAD:refs/heads/"$HEAD_REF"` present verbatim; executed successfully against a local stand-in remote from a detached, shallow head.
- [x] **7. No `uv lock` in any form.** `grep -n "uv lock"` on the file returns **zero** matches, code or comment.
- [x] **8. No cache.** `enable-cache: false` is passed to `setup-uv`; `actions/cache` appears **zero** times as a step (the only `actions/cache` grep hits are none — `actions/checkout` comment hits aside, there is no cache step).

### R8 — what a run actually does
- [x] **Verified by executing the workflow's shell under a simulated runner.** I extracted the three `run:` bodies programmatically from the staged YAML (`extract.py`) and ran them unmodified against a local bare repository standing in for `origin`, with a temp `$RUNNER_TEMP` and a temp `$GITHUB_STEP_SUMMARY`. The **single** deviation from verbatim: the `git remote set-url` target was redirected from `https://x-access-token:...@github.com/${GITHUB_REPOSITORY}.git` to the local bare path, since nothing may be pushed to GitHub. The diff between verbatim and executed text is one line and is recorded in the harness output.

  | path | summary lines | content | job outcome |
  |---|---|---|---|
  | **A** regenerate + push | **exactly 1** | `base 913e2452...: export regenerated; pushed 80db3a73...` | exit 0 |
  | **B** re-run after that push (no-op) | **exactly 1** | `base 913e2452...: export already matches the lock; nothing to push` | exit 0, branch head unmoved |
  | **C** base sha lacks the script | 0 | — | **exit 1** (job fails) |
  | **D1** token unset | 0 | — | **exit 1** (job fails) |
  | **D2** token set but empty | 0 | — | **exit 1** (job fails) |

  Line counts were counted, not eyeballed (`wc -l`). Path A's line was confirmed to contain both the base sha and the pushed sha by `grep -c`. A no-op run (B, one line) is therefore visibly distinct from no run at all (C/D, zero lines *and* a red job) — which is the property R8 is about. Paths C and D reach no summary line but fail the job, exactly as R8 requires; D1/D2 fail *after* the export was regenerated and before anything is committed or pushed, so there is no silent skip.

### R9 — the live demonstration, or its recorded pendency
- [x] **Passes by its second branch.** `gh secret list` for this repository returns exactly:
  `POSTGRES_URL_NON_POOLING`, `SECRET_KEY`, `SONAR_TOKEN`, `VERCEL_TOKEN` — **no `REQUIREMENTS_EXPORT_TOKEN`**. So the "missing demonstration while the secret exists" failure mode does not apply.
- The task records the demonstration as pending that operator-minted secret: `docs/tasks/APRAS-121-spec.md` (the file the card's `spec_path` points at) carries a dedicated section **"Operator prerequisite (blocks expected result 9 only)"** stating the fine-grained PAT the operator must mint, that it must be a repository *Actions* secret named `REQUIREMENTS_EXPORT_TOKEN`, that "Results 1–8, 10 and 11 are fully implementable and verifiable without this credential. Result 9 is the only one gated on it", and that the task may be reviewed and QA'd before the operator mints it. Result 9 is also left unchecked (`- [ ]`) in the spec's own checklist.
- I created no pull request, pushed no branch or commit, and created or requested no secret.
- Independently corroborating that the demonstration *cannot* be run now even with the secret: a `pull_request_target` workflow is taken from the base ref, so neither the workflow nor the base copy of the script exists until this lands on `master` — and the simulated Path C is exactly that failure, firing loudly rather than silently.
- Worth flagging as a non-blocking gap (see Suggestions): the pendency is recorded in the spec, not in the card's own fields (`last_review_findings` and `questions` are both `[]`).

### R10 — the two documentation corrections
- [x] **Verified** against the staged diff.
- `.github/dependabot.yml`: the old claim "`uv` updates `pyproject.toml`, `uv.lock` and the export together" is **gone**. The replacement states "What `uv` does *not* do is regenerate the export", explains the line-by-line bump with no resolver, cites `cd8de18`, and names the regenerating workflow `.github/workflows/requirements-export.yml`. It also documents the force-push side effect.
- `AGENTS.md`: new bullet states "`backend/requirements.txt` is never hand-edited" and names `backend/scripts/export_requirements.sh` as "the only way to regenerate it — the only place the export command is written down, and the only thing allowed to write the file."

### R11 — no frontend change
- [x] **Verified.** `git diff --cached --name-only | grep '^frontend/'` → no matches. `git status --porcelain frontend/` → empty. No file under `frontend/` is staged, modified or untracked by this task.

---

## Blocking Findings

None.

## Suggestions

1. **R9's pendency lives in the spec, not on the card.** The card's `last_review_findings` and `questions` are both `[]`, and nothing in the card's fields mentions `REQUIREMENTS_EXPORT_TOKEN`. R9's second branch is satisfied — the spec is the task's own document and states the gating plainly — but a reader scanning the board sees a `done` task with no visible outstanding item. A one-line note on the card ("result 9 demonstration pending operator-minted `REQUIREMENTS_EXPORT_TOKEN`") would make the outstanding work survive the spec file going unread. Board writes are the orchestrator's, not mine.
2. **The guard flags commented-out invocations too.** `_invocations_in` scans raw lines, so `# uv export ...` anywhere under `.github/workflows/` or `backend/tests/` is a failure. That is the safe direction for an absence assertion and I am not asking for it to change, but it does mean a future author cannot write about the command in a workflow comment. If that ever bites, the fix is to narrow the exclusion deliberately rather than to switch the sweep to `code_text`, which would open the commented-out-second-definition hole.
3. **The dry-run step's single retry is unconditional on cause.** `if ! dry_run; then sleep 20; dry_run; fi` retries a genuinely unsatisfiable pin set too, costing 20s and a second resolution before the real failure surfaces. Harmless, and the second failure is honest; mentioned only because the step is the one place in the job that touches PyPI.

---

## State left behind

The worktree is exactly as found: the same **eight staged paths** with unchanged blob hashes (including `backend/scripts/export_requirements.sh` at mode `100755`), **no unstaged tracked changes**, and the one untracked `docs/reviews/APRAS-121-developer-report.md` (which I did not read). Every mutated file was restored and each restore verified with `cmp` or an empty `git diff`. My probe file `.github/workflows/zz-qa-probe.yml` was removed and its absence confirmed. All harnesses and simulated repositories are namespaced under `scratchpad/qa121/`. Nothing was committed, pushed, unstaged or staged; no branch, PR or secret was created; `backend/scripts/sync_obras_from_drive.py` was not touched; no `git stash` was ever run; the production database and API were not contacted. Final re-run of the module after all mutations: **42 passed**.

I did not execute the DB-backed remainder of the backend suite (no local Postgres); full-suite collection is clean at 4256 tests, and none of the eleven expected results depends on the DB-backed tests.

VERDICT: APPROVED
