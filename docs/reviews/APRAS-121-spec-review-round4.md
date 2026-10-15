# APRAS-121 — spec review, round 4 (findings-only)

VERDICT: APPROVED

Spec reviewed: `/Users/heitor/workspace/apras/docs/tasks/APRAS-121-spec.md`
Tree: `master` at `2cb0d48` (note: `2cb0d48` is **not** pushed; `origin/master`
is at `25e9dc6`).

## Scope of this round

Findings-only re-review of the two blocking findings from round 3, a
consistency pass over the sections that changed to fix them (§2, the Files
touched entry for the workflow, results 7–9 and the renumbering of the
operator-prerequisite section), plus the independent verifications the dispatch
asked for and a fresh head-controlled-execution sweep of the privileged job.

## B1 — resolved

The second-checkout alternative is gone as a prescription. `actions/checkout`
appears five times in the spec (lines 214, 227–235, 242, 270, 329) and every
one is either an explanation of why a second checkout is **rejected** or a
reference to the single head checkout's own inputs (`ref:`,
`persist-credentials: false`, `fetch-depth: 1`). No `actions/checkout@v6` step
beyond the head checkout is required anywhere, and result 7 now names the
`git fetch` + `git show` form positively *and* excludes the alternative
explicitly ("rather than relying on the head checkout's history or on a second
`actions/checkout`"). The checkout-order hazard, which was the silent-inertness
class the finding was really about, is structurally absent: there is only one
checkout, so there is no order.

The mechanical argument the spec gives for rejecting the second checkout
(`path:` is workspace-relative, `git clean -ffdx` on the target, relocating the
head breaks the script's `cd backend`) is correct as written, and it is recorded
as reasoning rather than left implicit. The `--depth=1` base fetch and
`fetch-depth: 1` head checkout are both acknowledged in the push paragraph,
which is what the refspec discussion needs.

### Verification of the prescribed form

Run against the real remote from an empty repository with no credential helper
and `GIT_TERMINAL_PROMPT=0`, i.e. the `persist-credentials: false` condition:

- `gh repo view` → `heitorpolidoro/apras`, `visibility: PUBLIC`,
  `isPrivate: false`. The spec's stated dependency is real, and it is recorded
  in §2 as a dependency to revisit if the repository ever goes private.
- `git fetch --no-tags --depth=1 origin 25e9dc60…` (tip of `origin/master`) →
  `ok fetched (1 new refs)`, unauthenticated.
- `git fetch --no-tags --depth=1 origin cd8de18f…` (an **ancestor**, not a tip —
  the case that matters, since `base.sha` is `master`'s tip at event time and
  goes stale as `master` advances) → `ok fetched (1 new refs)`, unauthenticated.
- `git show cd8de18f…:backend/scripts/assert_no_skips.py` after that shallow
  fetch → file content returned. So `git show "$BASE_SHA":<path>` resolves after
  a `--depth=1` fetch-by-sha; the commit's tree and blobs come down with it.

One sharp edge found and worth recording: the fetch requires the **full 40-char
object id**. `git fetch --no-tags --depth=1 origin 2cb0d48d` failed with
`fatal: couldn't find remote ref 2cb0d48d`, while the full sha succeeded. This
is not a defect in the spec — `github.event.pull_request.base.sha` is always a
full sha — but it is the reason the spec's insistence on that expression rather
than any abbreviation is load-bearing, and it belongs in the implementer's head.

(My first attempt failed with `upload-pack: not our ref` against
`2cb0d489…`; that sha is the local, unpushed `master` tip, so the failure was
my test's, not the remote's. Repeated against pushed shas, both succeeded.)

### Push form

`git push origin HEAD:refs/heads/"$HEAD_REF"` is right for this job: the work
tree is detached at `head.sha`, so there is no upstream for a bare `git push`
to resolve, and `git push origin HEAD` would indeed create/target
`refs/heads/HEAD`. Pushing from a shallow clone is supported by git and by
GitHub's receive side (it is the ordinary `actions/checkout` + commit + push
pattern), and the commit being pushed is a direct child of `head.sha`, which
the remote branch already has — so the shallow boundary is never crossed. If
the branch advanced meanwhile the push is rejected non-fast-forward and the job
fails, which is the fail-closed direction; `concurrency` with
`cancel-in-progress: true` covers the common case of that race.

## B2 — resolved

Result 9 now carries both branches inside its own text: full evidence recorded,
**or** `gh secret list` showing no `REQUIREMENTS_EXPORT_TOKEN` plus the task
recording the demonstration as pending, with the closing sentence "A missing
demonstration while the secret *does* exist is a failure, not an outstanding
item." QA no longer needs §"Operator prerequisite" to tell *outstanding* from
*unmet*, which was the whole of the finding.

Verified the enumerated baseline is accurate today — `gh secret list` returns
exactly `POSTGRES_URL_NON_POOLING`, `SECRET_KEY`, `SONAR_TOKEN`,
`VERCEL_TOKEN`, matching the parenthetical in result 9 verbatim, and no
`REQUIREMENTS_EXPORT_TOKEN`. So the outstanding branch is observable with one
command and no judgement.

## The new observability result (result 8) — judged against the recurring defect

The dispatch asked three specific questions. Answers, in order.

**Does it cover "no run at all"?** No, and it does not claim to. Its subject is
"Every run … that reaches the export", and what it closes is the pair that was
genuinely indistinguishable before: *ran and found nothing to do* vs *ran and
silently did nothing*. A run that never starts — wrong event, branch gate
rejecting, `paths:` filter, the workflow not yet on the base ref — writes no
summary line and fails nothing. Result 8 as worded does not close that gap.

That gap matters, and it is closed elsewhere rather than here: result 9
exercises the trigger end to end on a real `dependabot/uv/backend/*` PR —
`opened` fires the regenerating run, the workflow's own push fires the
`synchronize` run, and that second run must record the `nothing to push` line.
A run existing at all on both events *is* the trigger proof, and `paths:` is
proven by construction because the demo commit touches `backend/**`.

The residual is narrow but real: in result 9's **outstanding** branch (no
operator secret), nothing in the task demonstrates that the workflow ever
triggers at all. Results 1–8, 10 and 11 are all static or `Backend Tests`
properties; the spec states they are "fully implementable and verifiable
without this credential", which is true, and the consequence is that the task
can reach done with the trigger, the branch gate and the base-script fetch
never once exercised. That is the recurring defect's last hiding place. It is
cheap to close without the secret — the spec already requires the job to **fail
loudly** when `REQUIREMENTS_EXPORT_TOKEN` is absent, so a dependabot-shaped
demo PR with no secret minted still produces a visible run that reaches the
export, writes nothing to push or regenerates, and then fails at the push step
naming the missing secret. That is trigger-plus-gate-plus-base-fetch proof with
no credential at all. I am filing it as a suggestion rather than a blocking
finding: it is not introduced by this round's fix, it does not make the design
unsafe, and result 9's primary branch does close it.

**Is "writes exactly one line" checkable by QA, and from where?** Yes, in two
places, both available to someone holding only the result text. Statically, in
`.github/workflows/requirements-export.yml`: there is one summary-writing step,
reachable on both outcome paths, with the two literal strings
`export regenerated; pushed` and `export already matches the lock; nothing to
push` and no third. Dynamically, from the run recorded under result 9 — the job
summary is visible on the run page, and result 9 independently requires the
re-run's `nothing to push` line to be recorded on the task. The one softness is
format rather than checkability: §2 says the line names "the base sha it
fetched and exactly one of two outcomes", while the two templates contain no
base-sha placeholder, so the assembled line's exact shape is not pinned. A
substring check for the template plus the sha works whatever the ordering, so
this costs QA nothing; see suggestion 3.

**Does the failing-rather-than-exiting-zero clause cover every unreachable
path?** §2's general sentence does — "Every failure path described in this
section (missing base script, absent secret) fails the job rather than exiting
zero" — and the other unreachable paths all land fail-closed for independent
reasons already written into the spec: a `UV_PIN` mismatch makes the base
script exit non-zero before exporting (§1); a head-added `[tool.uv]
required-version` makes `uv export --frozen` refuse, which §1 names explicitly
as fail-closed; a `git fetch` that cannot reach `$BASE_SHA` (force-pushed
`master`, repository turned private) exits non-zero; a rejected push exits
non-zero. Result 8's parenthetical names only two of these, but it is phrased
as an illustration of "a run that cannot proceed", not as an enumeration, so a
QA reading it alone still asks the right question. The one way back to silence
is a step that masks its own exit status — `continue-on-error: true` or
`|| true` — which §2 forbids nowhere (it is forbidden only for §3's dry-run
retry). Suggestion 2.

## uv pin claims — verified

- `0.12.19` is real and is the version in use locally:
  `uv 0.12.19 (Homebrew 2026-09-24 aarch64-apple-darwin)`.
- `version:` is a declared input of `astral-sh/setup-uv@v8.1.0`. Confirmed by
  reading `action.yml` at that tag.
- `pyproject-file:` is **not** a declared input at that tag. Confirmed: the
  input list is `version`, `version-file`, `python-version`,
  `activate-environment`, `venv-path`, `no-project`, `working-directory`,
  `checksum`, `github-token`, `enable-cache`, `cache-dependency-glob`,
  `restore-cache`, `save-cache`, `cache-suffix`, `cache-local-path`,
  `prune-cache`, `cache-python`, `ignore-nothing-to-cache`,
  `ignore-empty-workdir`, `tool-dir`, `tool-bin-dir`, `manifest-file`,
  `add-problem-matchers`, `resolution-strategy`. So the spec is right that the
  three steps passing it today are passing an undeclared input, that dropping
  it removes nothing, and that it is not an override. The spec's §1 rewrite
  states this accurately where round 3 called it "overridden".
- The downstream claim is also right: `working-directory` defaults to
  `${{ github.workspace }}`, and the repository root has neither `uv.toml` nor
  `pyproject.toml` (only `backend/pyproject.toml`), so with `pyproject-file:`
  ignored and no `version:`, every `setup-uv` step in this repository today
  resolves to floating-latest uv. Three such steps exist, all in `ci.yml`
  (lines 45, 135, 188), each with `enable-cache: false` and
  `pyproject-file: backend/pyproject.toml`; `migrate.yml` also uses `setup-uv`
  and is correctly excluded as not running the script.
- `checksum:` is a real input, so the privileged job's checksum pin is
  implementable as described.
- Supporting facts the spec leans on, all confirmed: `uv export` has `--frozen`,
  `--no-hashes` and `--format`; `uv lock --check` exists with exactly the
  documented meaning; `uv pip install` has `--dry-run` and `-p/--python`;
  `backend/requirements.txt`'s line 2 is
  `#    uv export --format requirements-txt --no-hashes -o requirements.txt`,
  i.e. it does lack `--frozen` and must be regenerated as §1 says;
  `backend/pyproject.toml` has no `[tool.uv]` section or `required-version`
  today; `backend/tests/test_requirements_export.py:85` holds the contiguous
  `uv export` literal the guard test must eliminate; and `ci.yml`'s job id is
  `backend` with `name: Backend Tests`, so the pin test's named locator ("the
  `setup-uv` step of the `backend` job") points at something that exists.
- Ruleset `16257354` checked: `master-protection`, one bypass actor —
  `RepositoryRole` id 5 (admin) with `bypass_mode: always` — and
  `strict_required_status_checks_policy: true`. Both premises of §2's
  threat-model paragraph and of the push-token argument hold.

## Head-controlled execution sweep of the privileged job, after the §2 rewrite

No path found. Step by step:

- **Head checkout.** `actions/checkout` at `head.sha` with
  `persist-credentials: false` executes nothing from the head tree; submodules
  are off by default, so no head `.gitmodules` is consulted.
- **`git fetch --no-tags --depth=1 origin "$BASE_SHA"`** runs in the head work
  tree but reads only `.git/config`, which `actions/checkout` wrote and the head
  cannot influence. `fetch.recurseSubmodules` is inert with no initialised
  submodules. `$BASE_SHA` is a 40-hex object id, so it cannot carry shell
  metacharacters regardless of how it reaches the step.
- **`git show "$BASE_SHA":backend/scripts/export_requirements.sh`** emits the
  raw blob. Smudge/clean filters are not applied by `git show` (that needs
  `git cat-file --filters`), and in any case a filter driver must be declared in
  git *config*, which a head `.gitattributes` cannot supply — a head
  `.gitattributes` alone can name an attribute but not a command. Same reasoning
  disposes of `diff=…`/textconv on the later `git diff`/`git commit`.
- **`bash "$RUNNER_TEMP/export_requirements.sh"`** executes a base-ref blob at
  an absolute path, so neither `PATH` nor the work tree resolves the name, and
  no exec bit has to survive. The head's copy is never executed or sourced.
- **The uv download.** `version: "0.12.19"` is a literal and `checksum:` is
  pinned, so no head file selects the toolchain and the artefact is validated
  against a caller-supplied digest rather than the action's stale baked table.
  With `version:` given, `working-directory` file discovery never happens.
- **`uv export --frozen`** reads `uv.lock` as data and resolves nothing, so no
  PEP 517 backend out of the head tree is invoked. The spec's decision to keep
  `uv lock --check` out of this job is the right one and the reasons it gives
  (`dynamic = ["dependencies"]`, `[tool.uv.sources]` path entries, a
  `[build-system]` with in-tree `backend-path`) are each sufficient on their
  own. A head-added `[tool.uv] required-version` — or, equivalently, a
  head-added `backend/uv.toml` carrying one — fails the export closed, which §1
  already records.
- **Hooks.** `.git/hooks` is the runner's, not the head's; `core.hooksPath` is
  not set by anything in the job.
- **No cache in either direction**, per §2: `enable-cache: false` and no cache
  action, so there is no write path from a PR branch into `master`'s cache
  scope.
- **The push** is the only step that sees `REQUIREMENTS_EXPORT_TOKEN`, and the
  commit is restricted to `backend/requirements.txt`.

The one remaining place head-controlled *text* reaches a shell is
`github.head_ref` in the push refspec. The spec writes the safe form —
`git push origin HEAD:refs/heads/"$HEAD_REF"`, a quoted shell variable — but
nowhere states that `github.head_ref` (and `base.sha`) reach the step through
`env:` rather than `${{ … }}` interpolation inside `run:`. Git ref names may
contain backticks, `$`, `(`, `)` and `;`, so the interpolated spelling inside
double quotes would be command injection. I do **not** consider the design
unsafe: the prescribed notation is the safe one, and the gate
(`dependabot/uv/` prefix plus `head.repo.full_name == github.repository`)
means only an actor who already holds push access can choose the branch name.
But the escalation it would buy such an actor is real — write access turning
into an admin-owned PAT push to `master` past all nine checks — so the one
sentence is worth adding, and code review must check it. Suggestion 1.

## Result count, merges, and NEEDS_SPLIT

Eleven results, grown 8 → 8 → 10 → 11. The growth is not padding: rounds 3 and
4 each converted a prose-only requirement into something QA can check, which is
exactly the direction the gate pushes. Nothing needs to merge for the list to
be verifiable. The one genuine overlap is result 1 (the property: no `uv export`
invocation outside the script) and result 6(b) (the test that enforces it);
they could be one entry without loss, and they are arguably clearer apart,
since 1 is a fact about the tree and 6 is a fact about the test's construction.
Results 7 and 8 both describe `requirements-export.yml` statically and could
also be merged, but 8 is this task's answer to the recurring defect and is
better off standing alone where it cannot be skimmed past. Result 11
(`frontend/` untouched) is a scope guard, cheap, keep.

`NEEDS_SPLIT` is still wrong, for the third time. The deliverable is one
mechanism — a single definition of the export command, the job that applies it,
the check that proves it, and the two doc lines that stop contradicting it —
touching seven files in one PR-sized change. The only part that ships
separately is the demonstration, and that is already modelled as a two-phase
landing gated on an operator secret rather than as a second task; splitting it
out would produce a child whose entire content is "open one PR and record four
fields". If the secret stays unminted long enough that the task would otherwise
sit in QA indefinitely, the right move is a follow-up task for result 9, which
is a scheduling decision for `meridian:pm`, not a decomposition of this spec.

## Blocking Findings

None.

## Suggestions

- State explicitly in §2 that `github.head_ref` and
  `github.event.pull_request.base.sha` reach the shell only through a step-level
  `env:` binding, never as `${{ … }}` interpolated inside a `run:` block. The
  spec already writes the safe form (`"$HEAD_REF"`, `"$BASE_SHA"`), but a git
  ref name may legally contain backticks and `$(…)`, so the interpolated
  spelling would be command injection in the one job holding a credential that
  can push to `master` past every required check. Exploiting it needs an actor
  who already has push access, which is why this is a suggestion and not a
  blocking finding — but it is the last head-controlled-text path into the
  privileged shell and code review must verify it.
- Broaden result 8's failure clause from the two named cases to the general one
  already stated in §2, and add that no step in
  `.github/workflows/requirements-export.yml` uses `continue-on-error` or
  otherwise masks a non-zero exit (`|| true`, a trailing `exit 0`). Every other
  unreachable path — `UV_PIN` mismatch, a head-added `required-version`, an
  unreachable `$BASE_SHA`, a rejected push — already fails closed on its own;
  a masked exit status is the only remaining way back to a green run that did
  nothing, and QA reading result 8 alone would not think to look for it.
- Give the summary line one full template rather than a sha plus two outcome
  fragments. §2 says the line names the base sha *and* one of the two outcomes,
  but neither template contains a base-sha placeholder, so its position is
  unspecified. A single written-out shape makes both the grep and any test
  exact.
- Consider requiring, in result 9's *outstanding* branch, a cheap trigger proof
  that needs no credential: a dependabot-shaped PR on which the run exists,
  reaches the export, and then fails at the push step naming the absent
  `REQUIREMENTS_EXPORT_TOKEN` — recording the run id. §2 already mandates that
  failure, so this costs one PR and closes the one case result 8 cannot see:
  the workflow never triggering at all. Without it, the no-secret path lets the
  task finish with the trigger, the branch gate and the base-script fetch never
  exercised.
- Line 118's parenthetical "(the declared inputs are `version` and
  `version-file`)" reads as a complete enumeration and is not one —
  `setup-uv@v8.1.0` declares two dozen inputs, including the `checksum:` this
  same section relies on. "the declared version-selection inputs" would be
  accurate. The load-bearing claim around it, that `pyproject-file:` is not an
  input at all, is correct.
- Record in §2 that the base fetch requires the full 40-character sha: an
  abbreviated id fails with `couldn't find remote ref`, not with anything that
  hints at the cause. `base.sha` is always full, so this is a note for whoever
  next edits that step rather than a change to it.
