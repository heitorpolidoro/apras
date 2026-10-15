# APRAS-121 — Code review, round 1

Reviewer: code-review agent. Date: 2026-10-09.

Worktree: `/Users/heitor/workspace/apras/.claude/worktrees/agent-ae6a8748df8e73027`.

## What I verified about the base and the environment

- `git rev-parse HEAD` in the worktree is `848725867b3b802f0f346c35c1c9b4d5e52bf7a8`, which is local
  `master`. `origin/master` is `25e9dc60a8bd4d44f24d3fd21bf27576bb39e933`. Base confirmed as
  described in the dispatch.
- `git status --porcelain` shows exactly eight staged paths (`M .github/dependabot.yml`,
  `M .github/workflows/ci.yml`, `A .github/workflows/requirements-export.yml`, `M AGENTS.md`,
  `M backend/requirements.txt`, `A backend/scripts/export_requirements.sh`,
  `M backend/tests/test_requirements_export.py`, `A docs/tasks/APRAS-121-spec.md`) plus the
  untracked `docs/reviews/APRAS-121-developer-report.md`. Nothing committed.
- Diff size reviewed: `git diff --cached --stat` = 8 files, 1,567 insertions, 8 deletions.
- `gh secret list` returns only `POSTGRES_URL_NON_POOLING`, `SECRET_KEY`, `SONAR_TOKEN`,
  `VERCEL_TOKEN`. `REQUIREMENTS_EXPORT_TOKEN` does **not** exist. I created nothing, pushed
  nothing, opened no pull request, and requested no secret. R9 is legitimately pending the
  operator-minted secret, by the spec's own second pass condition.
- I left the worktree exactly as found. All mutation work was done on a copy under the session
  scratchpad (`scratchpad/mut/`), never in the worktree, and `git stash` was never invoked.

## How I tested the assertions

I did **not** re-run the developer's M1–M7. I copied the relevant tree into the scratchpad and
built 30 mutants of my own, each applied independently and reverted afterwards, each with an
on-disk confirmation that the mutation actually landed before the module was re-executed. The
test module was executed by importing it from the mutated copy and calling every `test_*` function
(it is pure stdlib — no fixtures, no conftest dependency), so the pass/fail set is exact.

Baseline on the unmutated copy: 27 tests, 0 failures.

### Mutants that the suite correctly catches

| # | Mutation | Failing test |
|---|---|---|
| A | `uv<TAB>export --format requirements-txt -o requirements.txt` planted as a comment in `ci.yml` | `test_the_export_script_is_the_only_definition_of_the_command` |
| B | `uv<3 spaces>export --no-hashes` planted in the docstring of the real `backend/tests/test_lint_hygiene.py` | same sweep |
| D | `--no-annotate` added to the script's argv, export not regenerated | `test_the_generated_header_quotes_the_scripts_own_command` |
| E | `--frozen` dropped from the script | `..._header_quotes...` + `test_the_invocation_is_frozen_and_takes_nothing_from_its_caller` |
| F | `-o "${EXPORT_TARGET:-requirements.txt}"` (env value into argv) | same two |
| G | `UV_PIN` bumped alone to `0.12.33` | both pin tests |
| H | `requirements-export.yml`'s `version:` bumped alone to `0.12.18` | `test_the_export_workflow_pins_the_scripts_uv_version` only |
| I | privileged script taken from the **head** tree (`cp backend/scripts/...`) instead of `git show "$BASE_SHA":...` | `test_the_export_workflow_carries_every_fixed_form` |
| J | push refspec redirected to `refs/heads/master` | same |
| K | empty-token guard replaced with `if false; then` | `test_the_export_workflow_fails_when_the_push_token_is_absent` |
| L | a third `$GITHUB_STEP_SUMMARY` write added | `test_every_reachable_path_writes_exactly_one_summary_line` |
| M | `uses: actions/cache@v4` added | `test_the_export_workflow_carries_nothing_forbidden` |
| N | gate extended with `github.actor == 'dependabot[bot]'` | same |
| O | a second `actions/checkout@v6` step added | `test_the_export_workflow_uses_a_second_checkout_for_nothing` |
| AB | the push secret also exposed in the export step's `env:` | `test_the_export_workflow_fails_when_the_push_token_is_absent` |

These are real, non-vacuous checks, and each fires in the one test whose name claims the property.
The guard needle (`\buv[ \t]+export\b`, assembled from fragments) genuinely matches the whitespace
variants it must catch — I confirmed tab and multi-space forms in two *real* guarded files, not in
a fixture — and genuinely does not match `setup-uv` followed by a shell `export` on a later line,
nor `uv exporter`. The fragment assembly works: the module holds no contiguous literal and is not
exempt from its own sweep. The "one definition" sweep is not so loose that it matches prose in any
file currently under its reach; it is strict by design (any prose spelling in `.github/workflows/`,
`backend/tests/` or `AGENTS.md` is red), which is what the spec asked for.

I also ran APRAS-122's repo-wide `backend/tests/test_workflow_actions.py` against the implementation
copy: 0 failures. The new `setup-uv` step therefore satisfies APRAS-122's R1 as dispatched —
`version: "0.12.19"`, `enable-cache: false`, no `pyproject-file:`, no `version-file:` (confirmed
also by reading the step). `checksum:` **is** a declared input of `astral-sh/setup-uv@v8.1.0` — I
pulled `action.yml` at tag `v8.1.0` via `gh api` and `checksum` appears in its `inputs:` block — so
the workflow comment's claim about checksum validation is accurate and is not a repeat of the
`pyproject-file` mistake.

### The script's guards, exercised for real

With fake `uv` shims on `PATH`, from the copy:

1. no `uv` on `PATH` → `error: uv is not on PATH; this script needs uv 0.12.19.`, exit 1.
2. `uv 0.12.18`, from the repo root → the `UV_PIN=0.12.19 ... reports 0.12.18` refusal, exit 1.
3. `uv 0.12.19`, from a directory that is **not** the repo root → `error: run this from the
   repository root; backend/pyproject.toml is not under <cwd>`, exit 1.
4. `uv 0.12.19`, from the repo root → reaches the export line, exit 0.
5. the script **copied out of the tree** (simulating `$RUNNER_TEMP`) and run from the repo root →
   exit 0; the same copy run from the temp directory itself → the cwd refusal, exit 1.

So the divergence the developer flagged behaves exactly as claimed, and the guard fires when its
precondition is violated. The workflow's precondition holds: both `run:` steps that invoke the
script (`bash "$RUNNER_TEMP/export_requirements.sh"` in `requirements-export.yml`, and
`bash backend/scripts/export_requirements.sh` in `ci.yml`) use the step default working directory,
which is `$GITHUB_WORKSPACE` — the repository root — and neither step `cd`s first. The
`$BASH_SOURCE` approach would indeed have failed in `$RUNNER_TEMP`; the replacement is correct and
is the simpler of the two. Accepted.

## Security review of `requirements-export.yml`

This is the part I weighted most heavily, and the implementation is sound.

- **Executed code comes from the base.** The workflow file itself is base-provided under
  `pull_request_target`. The script is fetched by `git fetch --no-tags --depth=1 origin "$BASE_SHA"`
  and read with `git show "$BASE_SHA":backend/scripts/export_requirements.sh` into `$RUNNER_TEMP`,
  then invoked by absolute path through `bash`. The head's copy is never executed and never sourced.
  Mutant I (swapping in the head copy) is caught by the suite.
- **No template injection.** `grep '\${{'` over the whole file returns six hits and **none** is
  inside a `run:` body: `concurrency.group`, the checkout `ref:`, and four `env:` values. Every
  untrusted value (`github.head_ref`, `base.sha`) enters through `env:` and is used double-quoted
  (`"$BASE_SHA"`, `"$HEAD_REF"`). PR title, body, author and head file *contents* are never
  referenced at all. There is no `set -x`.
- **Refspec cannot be redirected.** `git push origin HEAD:refs/heads/"$HEAD_REF"` with `$HEAD_REF`
  quoted; the job gate requires the `dependabot/uv/` prefix, and git ref names cannot contain `..`,
  so the reachable target set is confined to `refs/heads/dependabot/uv/*`. `master` is not reachable
  through this refspec.
- **The fork gate is present and correct.** `github.event.pull_request.head.repo.full_name ==
  github.repository` is what stops a fork PR from reaching a job that holds the push token — a
  fork can trivially name its branch `dependabot/uv/anything`, so the branch-name gate alone is
  attacker-satisfiable and the same-repo condition is the load-bearing control. It is in the file.
  Creating such a branch in this repository requires push access.
- **Token handling.** The secret is referenced in exactly one step's `env:`, used in exactly one
  place, and checked for empty before any use. Nothing echoes it. It lands in `.git/config` via
  `git remote set-url`; registered secrets are masked in Actions logs, so a failing `git push` that
  prints the remote URL emits `***`. Acceptable; see suggestion 3 for the tighter form.
- **`permissions: contents: write` and nothing else**, `timeout-minutes: 10`, `concurrency` keyed on
  the PR number with `cancel-in-progress`, `paths: backend/**`, `fetch-depth: 1`,
  `persist-credentials: false`. The trigger and permission set are the narrowest that work:
  `pull_request` cannot work here (read-only token, no secrets on a dependabot PR), and the spec
  reasons that out explicitly.
- **No PEP 517 reachability.** `--frozen` is enforced by the script and asserted by the suite; the
  job runs no `uv lock`, no `uv sync`, installs nothing, runs no tests.

I found nothing that would let a fork PR run privileged code or move the token. The shipped
workflow is, as written, safe. **Both blocking findings below are about the test module's ability to
keep it that way**, which is precisely the mandate of this review.

## Blocking findings

### 1. `test_the_export_workflow_exists_and_is_read_as_one_file` cannot fail for either of the two properties it asserts

`backend/tests/test_requirements_export.py:551-556`:

```python
def test_the_export_workflow_exists_and_is_read_as_one_file() -> None:
    """Anti-vacuity for section 5: every sweep below reads this text."""
    text = export_workflow_text()
    assert "pull_request_target" in text, text[:200]
    assert "contents: write" in text, text[:200]
```

Both needles are already satisfied by **comment prose** inside the workflow, independently of the
structural keys:

- `pull_request_target` appears at `.github/workflows/requirements-export.yml:22` and `:47` (in the
  security-model comment), besides `:61` where it is the trigger.
- `contents: write` appears at `.github/workflows/requirements-export.yml:158` ("`GITHUB_TOKEN`
  would be the wrong credential even with `contents: write`"), besides `:69` where it is the
  permission.

Proven, with my own mutants, mutation confirmed on disk each time:

- **W**: `on:\n  pull_request_target:` → `on:\n  pull_request:` — the whole module stays **green**
  (0 failures). The mechanism would be silently dead: a `pull_request` run on a dependabot PR gets a
  read-only token and no Actions secrets, which is the exact failure the spec's §2 calls out.
- **X**: `permissions:\n  contents: write` → `permissions: write-all` — **green**.
- **X2**: `id-token: write` added alongside `contents: write` — **green**.

So the one test that calls itself the anti-vacuity anchor for the privileged workflow's whole
section cannot detect the trigger being downgraded or the permission set being widened to
`write-all`. Spec §2 fixes both as requirements ("`permissions:` is `contents: write` and nothing
else"), and this is the project's established failure mode verbatim: an assertion whose failing
direction is the one that cannot occur in practice (nobody deletes the words from the comment)
while the direction that matters passes.

Fix shape (cheap, local): assert the structural forms, e.g. `"\non:\n  pull_request_target:\n" in
text` and `"\npermissions:\n  contents: write\n\n" in text`, or strip comment lines before matching,
or parse the YAML and assert on the mapping.

### 2. The security-mandated properties of the privileged workflow are asserted only in negative forms that the realistic regression does not take

`backend/tests/test_requirements_export.py:514-540` (`REQUIRED_FRAGMENTS` / `FORBIDDEN_FRAGMENTS`).

`FORBIDDEN_FRAGMENTS` carries `"persist-credentials: true": "the head checkout must carry no
credential"` — but nobody writes that line explicitly. The regression is **deleting**
`persist-credentials: false`, after which `actions/checkout` defaults to persisting the workflow
`GITHUB_TOKEN` (here `contents: write`) into `.git/config` of a tree built from head data.

Proven, mutation confirmed on disk, module stays **green** in every case:

- **S**: the `persist-credentials: false` line deleted → green. (Spec §2 mandates it.)
- **P**: `&& github.event.pull_request.head.repo.full_name == github.repository` deleted → green.
  This is the one control that keeps a fork PR out of the job holding the push token, and its
  removal is invisible to the suite.
- **Q**: `startsWith(github.head_ref, 'dependabot/uv/')` deleted → green.
- **R**: `ref: ${{ github.event.pull_request.head.sha }}` → `ref: ${{ github.head_ref }}` → green
  (a mutable-ref checkout; spec §2 fixes the sha form).
- **T**: the `checksum:` pin deleted → green (spec §1 requires it for this job specifically).
- Lower severity, same class, also green: **Y** `paths:` filter removed, **Z** `concurrency:`
  removed, **AC** `commit -- backend/requirements.txt` → `commit -a` (spec: "the commit contains
  **only** `backend/requirements.txt`").

Note that this is not an overclaim by the module's docstring — section 5's prose enumerates exactly
four properties (base-sha fetch, out-of-tree copy, no lock command, no cache) and those four are
genuinely asserted (mutants I, J, M and the `uv lock` entry). The spec's R7 likewise does not
enumerate the gate. But the developer chose to assert the workflow's shape, the module is the only
backstop these properties have, and the fix is adding strings to a tuple that already exists:
`'persist-credentials: false'`, `'github.event.pull_request.head.repo.full_name == github.repository'`,
`"startsWith(github.head_ref, 'dependabot/uv/')"`, `'ref: ${{ github.event.pull_request.head.sha }}'`,
and the `checksum:` literal. Shipping a `pull_request_target` job with a `master`-capable PAT whose
fork gate no test defends is not a trade worth taking when the fix is five lines.

## Judgements requested

### R6's read-set parenthetical — the developer's argument holds

R6 ends "(`backend/requirements.txt`, `backend/uv.lock`, `.github/workflows/*`, `AGENTS.md`)". The
module additionally reads `backend/scripts/export_requirements.sh`, `backend/tests/*.py`,
`backend/pyproject.toml` and `.github/dependabot.yml`. Read as binding, that list is **self-
contradictory with the same spec**, on at least four counts:

- R6(b) requires the guard to fail when a `uv export` line is added to any file under
  `backend/tests/` — unsatisfiable without reading `backend/tests/*.py`;
- R3 requires a test that fails when the script's `UV_PIN` literal is changed alone — unsatisfiable
  without reading the script;
- R3 also requires `backend/pyproject.toml` to gain no `[tool.uv] required-version`;
- R10 requires `.github/dependabot.yml`'s comment to be checked.

The binding content of R6's final clause is the property it names — *only files in the working
tree, no network I/O, no `uv` subprocess* — and every extra file is in the working tree. The module
asserts that property by AST (`test_this_module_imports_nothing_that_could_reach_the_network`,
`..._makes_no_subprocess_or_network_call`, `..._reads_only_files_in_the_working_tree`), all three
pass, and the third also carries a runtime half over `_guarded_files()`. The parenthetical should
be read as illustrative. Divergence accepted, no change requested. Consequence worth recording for
future specs: write the invariant ("only files in the working tree"), not an enumeration that a
later requirement in the same document will contradict.

### The implementation divergence (`$BASH_SOURCE` → `cd backend` behind a guard)

Accepted, and verified end to end — see cases 3, 5 and 6 above. The guard fires with a readable
message when the precondition is violated, and both workflow call sites satisfy the precondition.

### The spec being staged into this worktree

Correct, and I would have asked for it otherwise. `docs/tasks/*-spec.md` is tracked content in this
repository (`8487258` is a `docs(APRAS-93)` commit of exactly that kind), and a mechanism whose
rationale lives only in an uncommitted file is one nobody can review later. No objection.

## Suggestions

1. **The "one definition" needle has a documented hole.** Mutant **C**: planting
   `uv --directory backend export --format requirements-txt --no-hashes --frozen -o requirements.txt`
   into `ci.yml` is **not** caught — `\buv[ \t]+export\b` requires adjacency. The script's own argv
   is forbidden from using `--directory` (asserted), but a *second* definition elsewhere may use it
   and escape the sweep. The spec fixed the pattern, so this is not a deviation; worth either
   widening the needle to `\buv\b(?:[ \t]+-{1,2}\S+(?:[ \t]+\S+)?)*[ \t]+export\b` or recording the
   hole in the module docstring.
2. **`REQUIRED_FRAGMENTS` is substring-based, so a required literal survives being commented out.**
   Mutant **V**: commenting out `git push origin HEAD:refs/heads/"$HEAD_REF"` and adding
   `git push --mirror origin` on the next line leaves the module green. Stripping `#`-leading lines
   before matching would harden this and finding 1 with one helper.
3. **Token in `.git/config`.** `git -c http.extraheader="Authorization: Basic $(printf 'x-access-token:%s' "$GIT_PUSH_TOKEN" | base64 -w0)" push ...`
   keeps the credential out of the on-disk config entirely. The current form is acceptable given
   Actions log masking; this is the tighter version if you want it.
4. **Mutable action tags in a privileged job.** `actions/checkout@v6` and `astral-sh/setup-uv@v8.1.0`
   are tags, and a tag can move. In the one job that holds a `master`-capable PAT, sha-pinning both
   is the hardened form. Repository convention is tags and APRAS-122 just settled the `setup-uv`
   pins, so this is a separate-task suggestion, not a request here.
5. **Keep the `--frozen` comment from hardening into "reads no head file".** `uv export --frozen`
   still reads head-controlled `backend/pyproject.toml` (and would read `backend/uv.toml`) for
   project/workspace discovery and `[tool.uv]` configuration. The spec analysed this, concluded no
   PEP 517 backend is reachable on the frozen path, and recorded the `required-version` residual as
   fail-closed — I agree. The script's header comment is slightly stronger than that analysis;
   a half-sentence would keep it honest.
6. **A token echoed into the step summary is not caught** (mutant AA stays green). Actions masking
   covers it in practice; I would not add an assertion for this.
7. **Minor, `backend/tests/test_requirements_export.py:605`**: the trailing
   `assert "exit 1" in text` in `test_the_export_workflow_names_the_script_when_the_base_lacks_it`
   is near-vacuous on its own (the file holds several `exit 1`s); the preceding `::error::`
   assertion is what carries the test. Harmless, but it reads as more than it is.
8. **Minor, YAGNI, `PERMITTED_READ_RECEIVERS`**: four quoting variants of the `dependabot.yml` path
   and two of `pyproject.toml` are enumerated for receivers that appear once each. The runtime half
   of the same test is the real guard; the variants could collapse.
9. Everything else in the diff is clean: `ci.yml`'s three new steps are in the spec's required order
   ahead of the wrapped pytest step with the single retry and no `continue-on-error`;
   `dependabot.yml`, `AGENTS.md` and the regenerated header match R10 and R2; no file under
   `frontend/` is touched; the script is executable (asserted) and `set -euo pipefail`.

## Claims I could not verify, and why

- **R9's live demonstration.** Not verifiable and not expected to be: `gh secret list` confirms
  `REQUIREMENTS_EXPORT_TOKEN` does not exist, which is the spec's own second pass condition. I did
  not create a secret, a branch, a commit or a PR.
- **R4's byte-for-byte reproduction** (delete `requirements.txt`, re-run the script under uv
  0.12.19) and **R5's dry-run/`uv lock --check` behaviour**. These need a real uv invocation and a
  network resolve; they are QA's expected results, not static review. What I did establish
  statically is that line 2 of the committed export equals the script's invocation exactly, which
  is the property R2 names, and that the three pin literals agree.

VERDICT: REJECTED

1. `backend/tests/test_requirements_export.py:551-556` —
   `test_the_export_workflow_exists_and_is_read_as_one_file`, the declared anti-vacuity anchor for
   the privileged workflow, cannot fail for either property it asserts: `"pull_request_target"` and
   `"contents: write"` are both satisfied by comment prose at
   `.github/workflows/requirements-export.yml:22`/`:47` and `:158`. Mutating the trigger to
   `pull_request:` and the permissions to `write-all` (and to `contents: write` + `id-token: write`)
   each leaves all 27 tests green.
2. `backend/tests/test_requirements_export.py:514-540` — the workflow's security-mandated properties
   are guarded only in forms the realistic regression does not take, so deleting
   `persist-credentials: false` (`.github/workflows/requirements-export.yml:102`), deleting the fork
   gate `github.event.pull_request.head.repo.full_name == github.repository`
   (`.github/workflows/requirements-export.yml:84`), deleting the `dependabot/uv/` branch gate
   (`:83`), swapping `ref: ${{ github.event.pull_request.head.sha }}` for `github.head_ref` (`:101`),
   and deleting the `checksum:` pin (`:121`) each leave all 27 tests green. The fork gate is the
   single control that keeps a fork PR out of a job holding a `master`-capable PAT.
