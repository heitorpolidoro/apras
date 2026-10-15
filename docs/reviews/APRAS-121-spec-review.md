# APRAS-121 — spec review

VERDICT: NEEDS_REVISION

Spec reviewed: `/Users/heitor/workspace/apras/docs/tasks/APRAS-121-spec.md`
Round: 1 (full review). Task has no `parent`, so `NEEDS_SPLIT` was available
and was considered — see "Scope" below.

## What I did

- Read the spec in full.
- Read `.github/dependabot.yml`, `.github/workflows/ci.yml` (all jobs),
  `backend/tests/test_requirements_export.py`, `backend/requirements.txt`
  header, `backend/scripts/` listing.
- Queried ruleset `16257354` via `gh api repos/:owner/:repo/rulesets/16257354`.
- Grepped the repository for literal `uv export` occurrences.
- Counted the `## Expected Results` convention across `docs/tasks/*-spec.md`.
- Wrote nothing, staged nothing, created no branch/PR, triggered no workflow,
  ran no `uv sync`/`npm install`.

## Premise verification

**Ruleset `16257354` (`master-protection`, target `branch`, conditions
`ref_name.include = ["~DEFAULT_BRANCH"]`) — all three claims confirmed:**

- `required_status_checks`: `strict_required_status_checks_policy: true`,
  `do_not_enforce_on_create: true`, contexts = `GitGuardian Security Checks`,
  `DeepSource: Docker`, `DeepSource: JavaScript`, `DeepSource: Python`,
  `DeepSource: Code Formatters`, `SonarCloud Code Analysis`,
  `DeepSource: Secrets`, `Backend Tests`, `Frontend Tests`.
- `pull_request`: `required_approving_review_count: 1`,
  `dismiss_stale_reviews_on_push: true`, `require_code_owner_review: true`,
  `required_review_thread_resolution: true`,
  `require_extra_approval_for_unattributed_changes: true`,
  `require_last_push_approval: false`, `allowed_merge_methods: ["squash"]`.

So the spec's reasoning holds: with `strict` on, a head sha that never got a
run for the nine required contexts is permanently unmergeable, and a
`GITHUB_TOKEN` push produces exactly that (GitHub's documented suppression of
workflow events for `GITHUB_TOKEN` pushes). I did not and could not test the
suppression empirically without pushing, which the constraints forbid; it is
documented behaviour and the spec's conclusion from it is sound. Note that all
three Actions-produced required contexts (`Backend Tests`, `Frontend Tests`,
`SonarCloud Code Analysis` — the last is the `sonarcloud` job in `ci.yml`,
`needs: [backend, frontend]`) are inside `ci.yml`, so all three are suppressed
together. The ruleset targets the default branch only, confirming §2's claim
that pushing onto a PR branch is not ruleset-governed.

`pull_request_target` running in base context with access to Actions secrets
(whereas a `pull_request` run on a dependabot-authored PR is scoped to the
Dependabot secrets list and a read-only token) is correct and consistent with
this repository's own `SONAR_TOKEN` history, which `ci.yml`'s `sonarcloud` job
corroborates (`SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}`).

The central premise was given as established and the repository bears it out:
`backend/requirements.txt` line 2 still reads
`#    uv export --format requirements-txt --no-hashes -o requirements.txt`
while `alembic==1.20.0` sits at the top, i.e. the file claims a provenance it
does not have.

**One premise worth recording that the spec does not use:** the existing
`backend/tests/test_requirements_export.py` already asserts bidirectional
pin-level parity against `uv.lock`, offline. So pin drift is *already* gated in
`Backend Tests` as of APRAS-120. The new regenerate-and-diff step adds only
byte-level properties (comment header, ordering, markers), and the dry-run adds
installability. That is still worth having, but the spec should say so (see
Suggestions) or a later reader will delete the step as redundant.

## Scope — why not NEEDS_SPLIT

One deliverable: regenerate the export reliably. Six files, one subsystem
(`.github/` + `backend/scripts` + one test + two doc lines), one coherent
reviewable PR. The demonstration in §4 is evidence for the same deliverable,
not a second one. None of the three split criteria apply.

## Blocking findings

### B1 — §2 never says which ref the workflow checks out, and both readings are wrong as written

This is the single most load-bearing implementation detail in the design and
the spec is silent on it. Under `pull_request_target`, `actions/checkout`
defaults to the **base** ref. A workflow that follows the spec literally would
regenerate the *base branch's* export, find no diff, and never push — the
mechanism silently never fires, and §4's demonstration would "pass" by
producing nothing. The other reading, `ref: github.event.pull_request.head.sha`,
checks out and then **executes** head-controlled `backend/scripts/export_requirements.sh`
with a Contents:write token in scope, which is the classic `pull_request_target`
pwn.

The spec's own safety argument — "`uv export` reading `uv.lock` executes no PR
code" — is not the whole surface: the *script* is a PR-controlled file too, as
are `pyproject.toml` and `uv.lock`.

The spec must state the split explicitly: workflow **and** script taken from the
base ref (e.g. a second checkout at `github.event.pull_request.base.sha` into a
separate path, or `git fetch` of the head's `backend/uv.lock`/`pyproject.toml`
into a base checkout), with only the head's lock/manifest data entering the
export. Until that is written down, the task is implementable two ways, one
inert and one unsafe.

### B2 — `--frozen` is left optional, but under `pull_request_target` it is a security requirement

§1 says "The developer may add flags (e.g. `--frozen`)". For the CI parity step
that is a free choice; for the `pull_request_target` job it is not. A non-frozen
`uv export` is allowed to re-resolve and update the lock, which means reading
head-controlled `pyproject.toml` and, for anything needing metadata from a
source distribution, invoking a **head-controlled build backend** — arbitrary
code execution in a job holding a Contents:write push credential. The gates in
§2 (`dependabot/uv/` prefix, `head.repo.full_name == github.repository`) restrict
*who* can create such a branch to accounts that already have push access, which
is a genuine mitigation but not a substitute: the whole point of §2's third
bullet is that the job must not execute PR code, and without mandatory
`--frozen` it may.

Make `--frozen` (or `--locked`, with the behaviour on a stale lock specified)
mandatory in the script, and say in §2 that the job must fail rather than
re-resolve if the head's lock is not up to date.

### B3 — Expected result 1 is false by construction

Result 1 requires the script be "the only place in the repository containing a
literal `uv export --format requirements-txt` invocation". `backend/requirements.txt`
line 2 contains that literal and always will, because `uv` writes the invocation
it was given into the header — a property §1 itself relies on. As recorded, the
criterion fails on day one. Scope it to the places that can diverge: workflow
files, test files, and docs, explicitly excluding the generated header.

### B4 — §1 and expected result 5 contradict each other on the guard test

§1: "No workflow and no test may contain a literal `uv export --format
requirements-txt` of its own." Result 5: a test "fails if any file under
`.github/workflows/` or `backend/tests/` hard-codes the export command". The
guard test must contain the needle it searches for, so a naive implementation
trips on itself — and the fix (splitting the literal, or excluding `__file__`)
is a behavioural decision the spec should make, not leave to discovery. Also
settle whether the needle is the exact string or a pattern, since §1's wording
(`uv export --format requirements-txt`) and the real header
(`uv export --format requirements-txt --no-hashes -o requirements.txt`) differ.

### B5 — "clean Python 3.13 environment" contradicts "a step of the Backend Tests job"

Result 4 demands the dry-run resolve run "against a clean Python 3.13
environment" *and* "as a step of the `Backend Tests` job". By the time any new
step runs there, `uv sync --all-groups` has already populated `backend/.venv`
with the lock's full contents — the opposite of clean. `uv pip install
--dry-run -r requirements.txt` against that venv is a materially weaker and
differently-behaving check than against a fresh interpreter, and nothing in §3
says which is intended. Specify the isolation (e.g. `uv venv` into a scratch
dir and `--python` at it), or drop the word "clean" from the criterion — but not
leave both.

### B6 — the push credential is unspecified, un-owned, and the two options differ in outcome

§2 says the push "uses a fine-grained PAT or GitHub App installation token with
Contents: write, read from Actions secrets". Three gaps:

- **No secret name and no scope statement**, so the workflow cannot be written
  and `AGENTS.md`/`dependabot.yml` cannot document it.
- **No owner for provisioning.** The credential has to be minted and stored by
  the operator; an implementing agent cannot create it. Expected result 6
  (automatic commit on a real PR) is therefore unreachable until that happens,
  and the spec does not say so. This belongs in the spec as an explicit operator
  prerequisite, or as an operator question.
- **The two options are not interchangeable under this ruleset.** With
  `require_extra_approval_for_unattributed_changes: true` and a single
  maintainer, a commit attributed to a GitHub App bot and one authored by the
  maintainer's own fine-grained PAT can land on different sides of the
  "unattributed" test — i.e. one choice can leave the PR needing a second
  approval that nobody can give. Pick one, and state the commit author/committer
  identity the push must use.

### B7 — no `## Expected Results` section, and the spec cross-references the list it omits

89 of 100 specs in `docs/tasks/` carry `## Expected Results` inline, so the
convention is clear, but the blocking part is internal: the spec's own heading
reads "## Decision on the `dev` group (expected result 4)", and §§1–5 refer to
"(3)" and "(4)". Those references resolve to nothing inside the document. A
reader — developer, code reviewer, or a later round of this review — cannot
check behaviour against criteria without a second source. Add the eight results
as `- [ ]` lines in the spec, matching the board record verbatim.

### B8 — `Files touched` omits `backend/requirements.txt`

If the script's flag set differs in any way from the current header (and B2
requires adding `--frozen`, which does change it), the committed export must be
regenerated and committed in this task, or result 1's byte-for-byte criterion
and result 3's `git diff --exit-code` both fail immediately. Name the file.

## Judgements the dispatch asked for explicitly

**Is `pull_request_target` safe as specified?** The *choice* is justified — the
Dependabot-secrets scoping makes `pull_request` unable to hold a push
credential, and the base-context requirement is real. The *gates* are also
right, and notably better than an `actor` gate: restricting to
`head.repo.full_name == github.repository` means the branch can only be created
by an account with push access, which is what makes the branch-name gate
tolerable. But the design is **not** safe as written, because §2 omits the two
things that actually contain the hazard: which ref is executed (B1) and whether
the export may re-resolve (B2). `permissions: contents: write` and nothing else
is the correct minimal surface for a job whose only side effect is a push; keep
it, and add that the PAT must not be exposed to any step other than the push
step.

**Does result 6's branch-name gate close the trap it is for?** Yes, and this is
the strongest part of the spec. Because the gate reads `github.head_ref` and
repo identity only, a hand-made `dependabot/uv/backend/*` branch is
indistinguishable from dependabot's own to the workflow, so the demonstration
exercises the production path with nothing relaxed. Two residual ways the paths
could still diverge, which the spec should close: a `paths:` filter means a demo
commit must touch `backend/**` (it does, by construction), and if B1 is resolved
by any means that depends on the PR *author* (e.g. a token whose push to the
branch is governed differently for a dependabot-owned ref), the equivalence
breaks. State that nothing in the workflow may read `github.actor`,
`github.event.pull_request.user`, or `github.triggering_actor`.

**The `dev`-group decision.** Sound, and well argued: the alternative really
does require `test_every_locked_package_is_pinned_in_the_export` to compute a
marker-aware dev closure from `uv.lock`, which is a resolver, and
`scripts/assert_no_skips.py` does forbid the conditional-skip escape. I read the
test and it derives its expectation from every non-virtual `[[package]]` in the
lock, so the spec's description of the obstacle is accurate. Deferring to its
own task behind a deploy-side runtime check is the right sequencing. The weak
point is not the decision but the gate built on it (B5): a dev-inclusive
dry-run resolve is a larger, network-dependent resolution, so its stability
depends entirely on the isolation question B5 leaves open.

**Adding work to `Backend Tests`.** Keeping the two steps inside an
already-required job is correct — `Backend Lint (ruff)` and
`Backend Migration Tests (Postgres)` are *not* in the ruleset's required list,
so putting the gate there would not block a merge, and the spec rightly refuses
to touch the required-check list. But the job is the one that hung fifteen
times, APRAS-119 is still unapproved, and the new dry-run step introduces a
fresh PyPI network dependency into the repository's most fragile required check.
Mitigation is cheap and should be specified rather than left to chance — see
Suggestions.

## Suggestions

- Place the regenerate-and-diff and dry-run steps **before** the 30-minute
  wrapped pytest step in `Backend Tests`. They are seconds-to-a-minute of work
  and, placed first, they still report when the known hang recurs. Say so in
  §3, and cross-reference APRAS-119 so the two tasks do not conflict over that
  job's step order.
- State in §3 that the dry-run's network dependency is accepted, and whether a
  retry is wanted. A PyPI blip currently becomes a red required check with no
  code cause.
- Say explicitly in §2 that the job is a no-op when the regenerated export is
  byte-identical to the committed one, and that this is what makes the
  `synchronize` event its own push fires terminate. Also consider a
  `concurrency` group keyed on the PR number with
  `cancel-in-progress: true`.
- Add to §4 that the demonstration PR is **closed and its branch deleted**, never
  merged: its committed export is deliberately unsatisfiable.
- Add one sentence to §3 naming what the regenerate-and-diff step adds over the
  existing `test_requirements_export.py` parity assertions (header, ordering,
  markers — i.e. byte-level rather than pin-level), so the step is not later
  removed as duplicated coverage.
- Result 8's "~375 errors" baseline is a moving number for a task that touches
  no frontend file. Consider replacing it with the stricter and more stable "no
  file under `frontend/` is modified" alone.

## Note, unrelated to this spec

`backend/tests/test_bcrypt_cost.py::test_passlib_is_not_installed` fails on this
checkout because `passlib 1.7.4` is present in `backend/.venv` though not
declared — local venv drift, as the dispatch stated. Not a finding against
APRAS-121, but it is the kind of drift the dry-run step in result 4 would not
catch, since it compares the export against a resolution and not against what
is installed.
