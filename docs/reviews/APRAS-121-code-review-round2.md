# APRAS-121 — Code review, round 2

Reviewer: code-review agent. Date: 2026-10-09. Round 1:
`docs/reviews/APRAS-121-code-review.md`.

Worktree: `/Users/heitor/workspace/apras/.claude/worktrees/agent-ae6a8748df8e73027`.

## State verified before reviewing anything

- `HEAD` is `848725867b3b802f0f346c35c1c9b4d5e52bf7a8` = local `master`; `git status --porcelain`
  shows exactly the eight staged paths plus the untracked `docs/reviews/APRAS-121-developer-report.md`;
  `git diff --stat` is **empty**, so there is no unstaged modification anywhere in the tree.
  `backend/pyproject.toml` is clean and untracked-by-this-task, as reported.
- Diff size reviewed: 8 files, **2,316 insertions, 8 deletions** (round 1: 1,567/8).
  `backend/tests/test_requirements_export.py` is now 1,527 lines (+741 over round 1).
- **What actually changed since round 1**, byte-checked with `diff -u` against my round-1 copy:
  `.github/workflows/requirements-export.yml` and `.github/workflows/ci.yml` are **identical**;
  `backend/scripts/export_requirements.sh` gained **only** the eight-line comment that round-1
  suggestion 5 asked for; everything else is the test module. So my round-1 security review of the
  shipped workflow stands unchanged and did not need redoing — which also means the fixes were made
  where the findings were, in the assertions, and not by quietly moving the workflow.
- `gh secret list` still returns only `POSTGRES_URL_NON_POOLING`, `SECRET_KEY`, `SONAR_TOKEN`,
  `VERCEL_TOKEN`. `REQUIREMENTS_EXPORT_TOKEN` does not exist. R9 remains legitimately pending by the
  spec's own second pass condition. I created no secret, no branch, no commit, no PR.
- `ruff check` and `ruff format --check` on the new module and the script: clean.
- APRAS-122's repo-wide `backend/tests/test_workflow_actions.py`: 0 failures against this tree.
- No shadowed duplicates remain: an AST pass over every module-level `FunctionDef`/`ClassDef`/
  `Assign` name reports **no** duplicate, so the round-1 shadowing (two definitions of
  `test_the_export_workflow_pins_the_scripts_uv_version`, only the later one ever running) was the
  only instance and it is gone.
- Worktree left exactly as found; `git stash` never invoked; nothing staged, unstaged, committed or
  pushed.

## How I tested, round 2

I did not re-run any of the developer's 45 mutations. I made a **fresh** private copy under a
uniquely-named scratchpad directory (not the round-1 path, given the reported collision), wrote a
new harness, and ran **66 mutants of my own**, each applied alone, each confirmed to have landed on
disk, each reverted and the revert verified byte-for-byte before the next.

Baseline on the unmutated copy: **42 tests collected, 0 failures** — matching the reported count.

**60 of my 66 mutants are caught.** Of the 6 that are not, 3 are my own bad mutants (two inert, one
semantics-preserving) and 3 are genuine but non-blocking gaps, listed as suggestions. Full results:

### Round 1 finding 1 is fixed, and fixed in the form that matters

| # | Mutation | Result |
|---|---|---|
| 9 | `on: pull_request_target:` → `on: pull_request:` | CAUGHT `test_the_workflow_triggers_only_on_pull_request_target` |
| 10 | `permissions: contents: write` → `permissions: write-all` | CAUGHT `test_the_workflow_grants_contents_write_and_nothing_else` |
| 11 | `id-token: write` added alongside | CAUGHT, same |
| 12 | a **duplicate** top-level `permissions:` block appended with `actions: write` | CAUGHT, same |
| 13 | `paths: ['backend/**']` → `['**']` | CAUGHT `..._triggers_only_on_pull_request_target` |
| 14 | `paths:` filter deleted | CAUGHT, same |
| 15 | `cancel-in-progress: true` → `false` | CAUGHT `test_the_workflow_serialises_runs_per_pull_request` |
| 16 | `concurrency:` key renamed away | CAUGHT, same |

All four mutants that were green in round 1 (trigger, `write-all`, `+id-token`, and by extension the
comment-satisfaction class) are now red. A comment genuinely cannot satisfy a parsed mapping.

### Round 1 finding 2 is fixed, including semantic weakenings that preserve every literal

This is the part I pushed hardest on, because an exact-set assertion can still be fooled by a change
that keeps both strings.

| # | Mutation | Result |
|---|---|---|
| 1 | `&&` → `\|\|` between the two gate conjuncts — both literals intact, gate now satisfiable by a **fork** PR with a dependabot-shaped branch | CAUGHT `test_the_job_gate_is_the_branch_prefix_and_the_same_repository_only` |
| 2 | fork conjunct → `head.repo.full_name != ''` (attacker-satisfiable, same shape) | CAUGHT, same |
| 3 | the whole `if:` gate deleted | CAUGHT, same |
| 4 | branch prefix widened `'dependabot/uv/'` → `'dependabot/'` | CAUGHT, same |
| 5 | `persist-credentials: false` **line deleted** (the realistic regression) | CAUGHT `test_the_head_checkout_is_a_sha_and_carries_no_credential` |
| 6 | `ref: head.sha` → `ref: ${{ github.head_ref }}` | CAUGHT, same |
| 7 | `with:` rewritten with `persist-credentials` dropped and `ref` requoted | CAUGHT, same |
| 8 | `fetch-depth: 1` → `0` | CAUGHT, same |
| 17 | `checksum:` deleted | CAUGHT `test_the_setup_uv_step_pins_the_version_and_the_artefact_checksum` |
| 18 | `checksum:` altered by one character | CAUGHT, same |
| 19 | `enable-cache: false` → `true` | CAUGHT, same |
| 20 | `version-file: backend/pyproject.toml` added (head file choosing the toolchain) | CAUGHT, same |
| 21 | push token moved from the step `env:` to a job-level `env:` (all steps see it) | CAUGHT `test_the_export_workflow_fails_when_the_push_token_is_absent` |
| 22 | `set -x` added to the push step | CAUGHT `test_the_export_workflow_carries_nothing_forbidden` |
| 23 | push step `set -euo pipefail` → `set -uo pipefail` | CAUGHT `test_every_shell_step_fails_fast` |
| 27 | token moved onto the `git push` command line (visible in `ps`) | CAUGHT `test_the_export_workflow_carries_every_fixed_form` |

The developer's argument that an **exact mapping** is the only form in which *deleting*
`persist-credentials: false` fails is correct, and mutant 5 is the proof. Mutant 1 is the one I most
expected to slip through; it does not, because `gate.split("&&")` yields a single conjunct whose text
matches neither expected member.

### The `ci.yml` gap the sweep found (section 5b) — verified, including a real relocation

| # | Mutation | Result |
|---|---|---|
| 28 | the regenerate-and-diff step **deleted** (round-1 MISS, R4's own subject) | CAUGHT ×2 |
| 29 | `git diff --exit-code` → `git diff` (no longer fails on a diff) | CAUGHT |
| 30 | the diff no longer path-restricted | CAUGHT |
| 31 | the `uv lock --check` step deleted | CAUGHT ×2 |
| 32 | `uv lock --check` → `uv lock` (mutating instead of asserting) | CAUGHT |
| 33 | dry run redirected at `backend/.venv` | CAUGHT `test_the_dry_run_is_isolated_from_the_projects_own_virtualenv` |
| 34 | `--python 3.13` replaced by `$(cat backend/.python-version)` | CAUGHT, same |
| 35 | `continue-on-error: true` on the dry-run step | CAUGHT, same |
| 36 | dry run reads `uv.lock` instead of `requirements.txt` | CAUGHT, same |
| **37** | **a genuine relocation**: all three steps cut and re-inserted *after* the pytest step, file length identical | CAUGHT `test_the_three_export_checks_run_in_order_before_pytest` |
| **37b** | the same, moving only the regenerate-and-diff step | CAUGHT, same |

**On the O6 honesty note**: I accept it, and I verified the underlying property rather than the
account. 37 and 37b are real relocations built by cutting and re-inserting the text at a different
index (not a no-op insertion), and both are caught. "My mutant was wrong" was, in this case, true.

### The hand-rolled parser — the trade-off, judged

**I accept it.** Two reasons, one of which I checked rather than assumed.

First, the `pyyaml` rationale is not a rationalisation. The spec's own "Decision on the `dev` group"
keeps the dev group **in** the export, and I confirmed that on disk: `backend/requirements.txt`
currently pins `pytest==9.1.1`, `ruff==0.16.9` and `coverage==7.13.5`. So a `pyyaml` added even as a
dev dependency really would land in the file this task exists to keep honest, and in the Vercel
install. Declining it is right.

Second, and this is what makes a 130-line parser acceptable as load-bearing test infrastructure:
every structural assertion compares against an **exact** expected value, so parser information loss
or mis-parsing makes the **clean tree red**, never silently green. I mutated the parser itself to
check that, and the four declared anti-vacuity tests are not the only thing standing behind it:

| # | Parser/helper mutation | Result |
|---|---|---|
| 44 | parser silently drops `false`-valued keys | CAUGHT ×2 (clean tree goes red) |
| 45 | every `with:` mapping parsed as `{}` | CAUGHT ×4 |
| 46b | block-scalar key renamed, which is the branch the `if:` gate actually uses | CAUGHT `..._job_gate_...` |
| 46c | block-scalar bodies always empty | CAUGHT ×9 |
| 46d | block-scalar keys silently skipped | CAUGHT ×10 |
| 47 | `code_text` neutered to return its input (would restore the round-1 finding) | CAUGHT `test_the_code_text_helper_drops_comments_and_only_comments` + the ci.yml locator |
| 48 | `code_text` blanks everything | CAUGHT ×11 |
| 49 | the "dumb scan" the parser is compared against disarmed | CAUGHT `test_the_parser_finds_every_step_a_dumb_scan_finds` |

And fed shapes it does not support, it refuses or fails loudly — never guesses into a pass:

| # | Unsupported/adversarial YAML | Result |
|---|---|---|
| 52 | `on: [pull_request_target]` in flow style | CAUGHT (safe direction) |
| 53 | `run: \|` → `run: >` in the push step | CAUGHT ×2 |
| 54 | a `uses: actions/cache@v4` step inserted at a deeper indent (a parser confusion attempt) | CAUGHT ×15, including the file-wide forbidden sweep |
| 55 | a second job added to `jobs:` | CAUGHT ×11 |
| 57 | a YAML anchor introduced on `persist-credentials` | CAUGHT |

`WorkflowParseError` subclassing `AssertionError` is the right call: a refusal surfaces as a test
failure rather than as an error someone might read as environmental. The decision to capture a
`run:` body as one raw scalar is also right, and is itself measured (mutant 53).

### The round-1 suggestions that were taken

- **Suggestion 1 (the `--directory` hole).** The needle now admits dash-led global options with an
  optional value. Mutant **58** (`uv --directory backend export ...`, the exact form that was MISSED
  in round 1), **59** (`uv -q export ...`) and **60** (`uv --project backend export ...` planted in
  `AGENTS.md` prose) are all CAUGHT. The widening did not cost precision: the real `ci.yml` now
  contains `uv pip install --dry-run --python "$RUNNER_TEMP/export-check"` and
  `uv venv --python 3.13 "$RUNNER_TEMP/export-check"` — both contain the word `export` and neither
  matches, because the token in the subcommand slot is `pip`/`venv`, and the clean tree is green.
  The "widening caught a comment of my own" note is consistent with what I see: the needle is now
  strict enough to bite prose, which is the intended behaviour inside the three guarded locations.
- **Suggestion 2 (comment-satisfiable required fragments).** `REQUIRED_FRAGMENTS` and
  `FORBIDDEN_FRAGMENTS` now match against `code_text`, and `code_text` is itself guarded (mutants 47,
  48). Commenting out the refspec is now a failure.
- **Suggestions 5, 7, 8** taken as written: the `--frozen` comment is now precise about what the
  frozen path still reads (and the stronger claim is explicitly disclaimed); the bare `exit 1` is
  scoped to the base-sha step's own body; `PERMITTED_READ_RECEIVERS` is bare names only, and it still
  bites — mutant **61** (a `Path("/etc/hosts").read_text()` added) and **62** (`import subprocess`)
  are both CAUGHT.

### The declines — accepted

I accept all three, for the reasons given, which were mine: Actions log masking does cover 3 and 6,
and 4 (sha-pinning `actions/checkout`/`setup-uv`) would contradict the tag convention APRAS-122 has
just settled across every workflow. A cross-workflow hardening task is the right home for them, and
suggestions 1 and 2 below belong in that same task rather than here.

## Suggestions (none blocking)

1. **The summary line can claim a push that did not happen.** Mutant **24**: moving
   `echo "base $BASE_SHA: export regenerated; pushed $pushed_sha" >> "$GITHUB_STEP_SUMMARY"` to
   *before* `git push` leaves all 42 tests green. With `set -e` the step still fails, so the run is
   red and the operator is not misled about the outcome — but the summary, which exists precisely to
   be the run's one readable verdict, would be a lie on that red run. Asserting that the push line
   precedes the summary line within the step body would close it, and the step body is already parsed
   as one scalar, so the ordering is available.
2. **`continue-on-error` is unasserted on the privileged job.** Mutant **25**: adding
   `continue-on-error: true` to the push step is green. The job would then be green while nothing was
   pushed and — because `set -e` kills the step before the `echo` — **no summary line was written**,
   which is the "ran and did nothing, indistinguishable from never ran" shape spec §2 is built
   against. `_ci_step_run` already asserts `continue-on-error is None` for the three `ci.yml` steps;
   the same one-line check over `regenerate_steps()` would cover this. Spec §2 mandates that every
   failure path fail the job, so this is the strongest of my suggestions.
3. **`timeout-minutes: 10` is unasserted** (mutant 26, green). Minor, and not spec-mandated for this
   workflow, but AGENTS.md's "a hung run must not be a silent one" rule makes it a cheap addition.
4. **The script's own two guards are asserted nowhere.** Mutants **40** (`if [ ! -f
   backend/pyproject.toml ]` → `if false`) and **41** (the version comparison neutered) are both
   green. I re-verified by execution that both guards do currently fire — with fake `uv` shims on
   `PATH`, a wrong version from the repo root produces the `UV_PIN=0.12.19 ... reports 0.12.18`
   refusal and exit 1, and the out-of-tree copy run from a temp cwd produces the repo-root refusal
   and exit 1 — so the behaviour is real. I am not blocking on it because, unlike round 1's fork
   gate, both have an asserted second line of defence: the cwd guard fails closed (uv exits non-zero
   with "No pyproject.toml found" without it), and a neutered version guard produces a
   differently-headed export that `Backend Tests`' regenerate-and-diff step — now asserted by
   section 5b — turns red on the PR. R3 names the refusal as an expected result, so it is QA's to
   exercise. A text assertion in the shape the rest of the module uses (the comparison plus an
   `exit 1` in the same block) would still be worth having, since the module cannot shell out by its
   own offline contract.
5. **Dead branch in `_consume_block_scalar`.** The return is
   `joiner.join(dedented).strip() if joiner == " " else "\n".join(dedented) + "\n"`, so the `joiner`
   variable is only ever used when it equals `" "` and the `|` path re-hardcodes `"\n"`. Mutating
   `joiner` for the folded style is therefore inert (that is what made my mutant 46e a false
   negative rather than a finding). Branching on `style` instead of on the joiner's value would say
   what is meant. Behaviour today is correct.
6. **Half the decoy is self-guarded, half is not.** Mutant **64**: emptying the decoy's `run:` body
   of the planted properties is green, because the test's `assert needle in FAKE_WORKFLOW...` loop
   only covers the comment-planted needles. Mutant 63 (emptying the *comment* plant) is correctly
   caught. One extra membership loop over the run-body plants would make the whole fixture
   self-guarding.
7. **Step names are now locators** (`step_named`, `_ci_step_index`), so renaming a step is a red
   test. That is the right trade here — a renamed step should be a deliberate act — but it is worth a
   line in the module docstring, because the failure will land on someone editing prose.
8. Mutant **56** (renaming the push step to `Push`) is green and that is **correct**: the push step
   is located by which step carries the secret in its `env:`, not by its name, and no spec
   requirement fixes the name. Recorded so the green is not mistaken for a gap.

## The claims I was asked to weigh

- **"All 94 round-1 assertions audited, 31 changed in five classes."** I did not re-audit the
  classification, but I spot-checked the three classes that matter most and each holds: the
  comment-satisfiable class is now structural (mutants 9–16, 5–8), `ci.yml`'s raw-text job locator
  now blanks comments and proves it (`test_the_backend_job_locator_really_lands_on_the_backend_job`
  asserts no comment lines survive in the block, and mutant 47 turns it red), and the
  export-invocation guard is correctly left reading comments on purpose — it is the one sweep whose
  subject is text, and mutants 50, 51, 58–60 show it fails safe in that direction.
- **The scratchpad-collision account.** I did not rely on it. I built a fresh copy in a
  uniquely-named directory, ran my own harness, and verified the staged content on its own terms:
  `git diff --stat` empty, the two workflow files byte-identical to my round-1 copies, the script
  differing by one comment block, `backend/pyproject.toml` clean, and exactly eight staged paths
  before and after my work. The staged content is sound independently of how it was produced.

## Round 1's blocking findings, closed

1. `test_the_export_workflow_exists_and_is_read_as_one_file` is gone; the trigger and the permission
   set are each asserted against the parsed document. **Closed** (mutants 9, 10, 11, 12).
2. The negative-form-only guards are gone; the gate, the checkout inputs and the `setup-uv` inputs
   are asserted as exact sets/mappings, and the five properties that were silently removable in
   round 1 are each red now. **Closed** (mutants 1–8, 17–20).

VERDICT: APPROVED

Blocking findings: None.
