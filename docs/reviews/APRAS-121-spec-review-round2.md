# APRAS-121 — spec review, round 2 (findings-only)

VERDICT: NEEDS_REVISION

Spec reviewed: `/Users/heitor/workspace/apras/docs/tasks/APRAS-121-spec.md`
Round 1 report: `/Users/heitor/workspace/apras/docs/reviews/APRAS-121-spec-review.md`
Mode: findings-only re-review of the eight round-1 blocking findings, plus a
consistency pass over the sections the generator changed to fix them (§1 guard
rules, §2 in full, §3's isolation/network paragraphs, §4, the new "Operator
prerequisite" section, `Files touched`, `Expected Results`).

Task has no `parent`; `NEEDS_SPLIT` was available. Round 1's scope judgement is
unchanged: one deliverable, one subsystem, one reviewable PR. Not a split.

## What I did

- Read the revised spec in full and the round-1 report.
- Re-read `.github/workflows/ci.yml` (all four jobs), `.github/dependabot.yml`,
  `backend/pyproject.toml`, `backend/.python-version`,
  `backend/tests/test_requirements_export.py`, `backend/requirements.txt`'s
  header, `backend/scripts/` listing, `.github/workflows/` listing.
- Re-queried ruleset `16257354` (`gh api`), this time including `bypass_actors`.
- Checked commit attribution for `heitor.polidoro@gmail.com` via
  `gh api repos/:owner/:repo/commits/25e9dc6` (`.author.login`).
- Checked `enable-cache` / `actions/cache` / `setup-uv` usage across all
  workflows, and whether any `[tool.uv]` / `required-version` pin exists.
- Checked base-sha/head-sha ancestry on the two open dependabot `uv` PRs
  (#50, #51) to test the prescribed `git show <base.sha>:…` construction.
- Wrote nothing but this report. Staged nothing, created no branch or PR,
  triggered no workflow, ran no `uv sync` / `npm install`, ran no `git stash`.

## The eight round-1 findings: all resolved

- **B1 — resolved.** §2's "Which ref is checked out, and which code executes"
  states the split as two distinct rules, names `git show <base.sha>:…` into
  `$RUNNER_TEMP` as the executed copy, says the head's copy is never executed or
  sourced, and closes the action-selection hole by requiring an explicit
  `version:` on `setup-uv` instead of `pyproject-file:`. The head tree at
  `head.sha` with `persist-credentials: false` is correctly justified (the commit
  must sit on the PR's own tree) and the lock/manifest are correctly described as
  data. Two residual execution paths remain open — see N5 and N6 — so B1's
  *intent* is not yet fully discharged by the prescribed construction, but the
  omission B1 named is gone.
- **B2 — resolved.** `--frozen` is mandatory and argued from the build-backend
  hazard; plain `uv lock` is forbidden; the job fails rather than re-resolves on
  a stale lock; no `uv sync`, no install, no tests, no other secret. (The
  freshness assertion it introduces has its own problem — N5.)
- **B3 — resolved.** Result 1 now excludes the `uv`-generated header and `docs/`
  explicitly, and §1 states the exclusions as deliberate with reasons.
- **B4 — resolved, and well.** The decision is made in one direction (pattern,
  assembled from fragments at runtime, no `__file__` exclusion), the needle is
  specified as `uv` + whitespace + `export`, and result 5(a) restates it. The
  existing literal at `backend/tests/test_requirements_export.py:85` is covered
  by §1's "failure message names the script instead", so the guard will not trip
  on the file it lives in.
- **B5 — resolved.** `uv venv --python 3.13 "$RUNNER_TEMP/export-check"`, with
  "must not use `backend/.venv`" stated as a prohibition and the reason given.
- **B6 — resolved.** Secret named (`REQUIREMENTS_EXPORT_TOKEN`, Actions list,
  not Dependabot list), scope stated (single repo, Contents: Read and write,
  nothing else), owner stated (operator), result 6 explicitly gated, and the
  commit identity fixed. I verified the attribution premise: GitHub resolves
  `heitor.polidoro@gmail.com` to login `heitorpolidoro` on `25e9dc6`, so a
  commit with that author/committer is attributed to a GitHub account and the
  spec's reading of `require_extra_approval_for_unattributed_changes` is
  plausible. Existing master commits are `verification.verified: false`, so the
  rule evidently does not key on signature in this repository's practice — and
  result 6 records post-push mergeability, which is the right way to settle it
  empirically. The App-vs-PAT reasoning is sound as written; the part it does not
  weigh is blast radius (N5).
- **B7 — resolved.** `## Expected Results` is present with eight `- [ ]`
  entries; the `(expected result 4)` dangling heading reference is gone.
- **B8 — resolved.** `backend/requirements.txt` is listed in `Files touched`
  with the reason (header predates `--frozen`).

## New blocking findings

All six are in sections the round-2 revision rewrote, and each is introduced by
one of the fixes above rather than carried over from round 1.

### N1 — the byte-identity gate has no pinned producer, and the two jobs are now specified to use *different* uv versions

§2 requires the pushing job to pin uv by an explicit `version:` on `setup-uv`
(correctly, per B1). §3 adds the regenerate-and-diff step to `Backend Tests`,
whose `setup-uv` is `astral-sh/setup-uv@v8.1.0` with
`pyproject-file: backend/pyproject.toml` — and `backend/pyproject.toml` has no
`[tool.uv]` section at all, so no `required-version`, so that job installs
whatever uv is latest at run time. Meanwhile results 2 and 3 demand a
**byte-identical** export including the `uv`-written header, and result 6 demands
`Backend Tests` succeed on the sha the pushing job created.

So as specified: job A produces the export with pinned uv X, job B re-runs the
script with floating uv Y and asserts `git diff --exit-code`. The header line,
the `# via …` annotations, ordering and marker rendering are all uv-version
artefacts. The first time Y ≠ X changes any of them, the bot's own push turns
`Backend Tests` red with no code cause — the exact failure mode the task exists
to remove — and a developer running the script locally (uv 0.12.19 here) is a
third producer.

The spec must name one pinned uv version and state where every consumer of the
script gets it. Note the pin cannot be `[tool.uv] required-version` *for the
privileged job*, because that file is head-controlled and B1's own rule forbids a
head file choosing the toolchain; so the pin has to be the same literal
`version:` in both `.github/workflows/requirements-export.yml` and
`.github/workflows/ci.yml`, with the local story stated (and, if
`required-version` is also added for local runs, it must be described as
advisory for the privileged job only).

### N2 — §2's `uv export --locked` alternative violates §1's own guard

§2 offers the freshness assertion as "`uv lock --check`, or equivalently
`uv export --locked`". §1's guard forbids any file under `.github/workflows/`
from containing `uv` + whitespace + `export`, and result 5(b) requires the test
to fail when such a line is added to a workflow. An implementer who takes the
second branch writes a workflow that fails results 1 and 5 on the same commit
that creates it. Two of the round-1 findings (B3, B4) were the same class of
self-tripping rule, so this is worth fixing properly rather than trusting the
implementer to read ahead.

Decide it: require `uv lock --check` in the workflow, or put the freshness
assertion inside the base-ref script (`backend/scripts/`, outside the guard's
scope) — and say which, because the two differ in where the failure surfaces and
in whether `Backend Tests` runs the same assertion.

### N3 — §4's demonstration can be killed by §2's new freshness gate, and result 6 then cannot be distinguished from a broken mechanism

§2 now requires the job to **exit non-zero before regenerating** when the head's
lock is stale with respect to its `pyproject.toml`. §4 requires a demo PR whose
single commit "changes `backend/uv.lock` **and** `backend/requirements.txt`" and
says nothing about how the lock change is produced. A hand-edited lock is the
obvious reading, and a hand-edited lock is exactly what `uv lock --check` is
designed to reject — so the demo job exits non-zero, pushes nothing, and result
6 is unreachable for a reason that looks identical to "the mechanism does not
work".

§4 must say that the demo lock is produced by a real `uv lock` /
`uv lock --upgrade` so the freshness assertion passes, and that *only*
`backend/requirements.txt` is hand-edited (line-by-line pin bumps mimicking
`cd8de18`, including the pair the resolver rejects). That construction also keeps
the two properties §4 already wants: export above the locked version, and an
unsatisfiable pin pair.

### N4 — caching is unspecified in a `pull_request_target` job, where the cache scope is `master`'s

Every other `setup-uv` in this repository passes `enable-cache: false`; the spec
tells the implementer to write this one's `setup-uv` block differently (pinned
`version:`, no `pyproject-file:`) and then says nothing about the cache. A
`pull_request_target` run executes in base context, so anything it saves —
`setup-uv`'s `~/.cache/uv`, or any `actions/cache` step — lands in the
**base-branch cache scope**, which `master`'s own runs are allowed to restore,
with a key influenced by head-controlled `uv.lock`. That is a write path from a
PR branch into master's CI inputs, and it is not covered by "the job executes no
PR code".

The spec must require `enable-cache: false` and no `actions/cache` in the new
workflow, in the same voice it already uses for `permissions:` and for the
secret's step scope.

### N5 — the freshness assertion's "invokes no build backend" claim is not unconditionally true, and the credential chosen makes the blast radius `master`

§2 asserts the freshness assertion "performs no resolution and invokes no build
backend". That holds for this tree as it stands (`backend/pyproject.toml`
declares static `[project].dependencies`, no `dynamic`, no `[tool.uv.sources]`,
no custom `build-system`) — but the file the assertion reads is the **head's**,
and the head can add `dynamic = ["dependencies"]`, a `[tool.uv.sources]` path
entry, or a `[build-system]` with an in-tree `backend-path`, any of which makes
uv obtain project metadata through a PEP 517 backend from the head tree. The
metadata-free path is `uv export --frozen` alone; the freshness check is the one
step in the job that can need metadata, and it is the step the revision added.

This matters more here than it would elsewhere, which §2 does not weigh: ruleset
`16257354` carries `bypass_actors: [{actor_type: RepositoryRole, actor_id: 5,
bypass_mode: always}]`, i.e. the admin role bypasses the master ruleset
unconditionally. A fine-grained PAT owned by the maintainer therefore pushes to
`master` directly, past the nine required checks and the review rule — so code
execution in *any* step of that job is a master compromise, not merely a
tampered PR branch. The gates (same-repo `dependabot/uv/` branch) keep the
exploit to accounts that already have push access, which is a real mitigation
and the reason this is a design gap rather than an open door; but the spec's own
standard is that the job executes no PR code, and it should hold to it.

Resolve it one of these ways and say which: drop the freshness assertion from
the privileged job entirely (a stale head lock then yields an export that
matches that lock, which `Backend Tests` on the PR already judges with a
read-only token and no secrets); move the assertion into `Backend Tests`; or keep
it in the privileged job and first assert that the head's
`[build-system]`, `[project].dynamic` and `[tool.uv]*` are byte-identical to the
base's, failing closed otherwise.

### N6 — the prescribed `git show <base.sha>:…` is not guaranteed to resolve in the prescribed checkout

§2 prescribes one checkout at `head.sha` with `fetch-depth: 0` "so the base sha
is present". `actions/checkout` given an explicit sha fetches the history **of
that commit**, not every branch, so `base.sha` is present only while it is an
ancestor of `head.sha`. `pull_request.base.sha` in the payload is the base
branch tip at event time: on the two open dependabot `uv` PRs (#50, #51) it is
an ancestor today (both branch directly off `25e9dc6`), but the moment `master`
advances while a PR is open, the next `synchronize` — including the one fired by
this workflow's **own push** — carries a `base.sha` that is not an ancestor, and
`git show <base.sha>:backend/scripts/export_requirements.sh` fails. The job then
fails closed, which is safe but means the mechanism intermittently does not fire,
which is the inert half of round-1 B1 returning by another route.

Specify a construction that is guaranteed: a second `actions/checkout@v6` at
`github.event.pull_request.base.sha` (with `persist-credentials: false`) into a
path outside the work tree, or an explicit `git fetch --no-tags --depth=1 origin
$BASE_SHA` before the `git show`. State the behaviour when the base sha predates
the script's existence (it must fail with a message naming the script, not with
a bare git error) — that is the state of `master` until this task lands.

## Checks the dispatch asked for that came back clean

- **`.gitattributes` / hooks in the head tree.** No `.gitattributes` exists, and
  neither path is reachable anyway: clean/smudge filter *drivers* must be defined
  in git config, which a PR cannot write, and `actions/checkout` clones fresh so
  there are no repository-supplied hooks in `.git/hooks`. `git show <rev>:<path>`
  emits the raw blob, so the base copy of the script is not filtered either. Not
  a finding.
- **Actions pinned by a head file.** The only one was `setup-uv`'s
  `pyproject-file:`, and §2 closes it. No other action in the prescribed workflow
  takes input from the head tree.
- **A `uv` subcommand that resolves despite `--frozen`.** `uv export --frozen`
  reads the lock and does not resolve; the hazard is the freshness assertion, not
  the export — hence N5 rather than a finding against `--frozen`.
- **`github.actor` / `pull_request.user` / `triggering_actor` ban.** Stated in
  §2 as an absolute, which is what makes §4's dependabot-shaped PR exercise the
  production path. Strongest part of the design, unchanged from round 1.
- **The push credential's step scope and `permissions: contents: write` and
  nothing else.** Both stated, both minimal. The explicit "fails with a message
  naming the secret if absent or empty, must not skip silently" closes the
  `SONAR_TOKEN`-shaped trap.
- **Termination.** The no-op-on-identical argument is correct and sufficient:
  the second run regenerates, finds no diff, pushes nothing.
- **Re-triggering the required checks.** `ci.yml` triggers on
  `pull_request: branches: [master]`, so a non-`GITHUB_TOKEN` push to the PR
  branch does produce fresh `Backend Tests`, `Frontend Tests` and
  `SonarCloud Code Analysis` runs on the new head sha, which is what
  `strict_required_status_checks_policy: true` needs. Premise holds.

## The two questions the dispatch put directly

**Is the operator-gated result 6 well-formed on this task?** Yes, as written. The
prerequisite is in the spec under its own heading, result 6 carries the gate
inline, and the spec states plainly which results do not depend on it (1–5, 7,
8). An implementer can therefore complete and be QA'd on seven of eight results
and report result 6 as blocked on a named, single, operator-owned action — which
is better than discovering the gap mid-implementation, and better than a
follow-up task, because the mechanism's *only* end-to-end evidence is result 6;
split onto its own task it would be a task whose spec is "run the thing the other
task built", with the demo PR construction duplicated. Keep it here. The one
thing I would add is a sentence saying the task may be QA'd with result 6
outstanding, so the gate does not read as a blocker on the whole task.

**Result 5's "offline".** It is true — the guard test reads files from the
working tree and the parity test reads `uv.lock`; nothing in either needs the
network, including clause (c) about the generated header, which is one more file
read. But it is not *checkable from the result*: no step anywhere runs the suite
without network (CI has it), so "offline" as phrased is an assertion about the
test's construction rather than an observation anyone makes. It is salvageable
without weakening it — phrase it as a property of the test's inputs ("the guard
and parity tests read only `backend/requirements.txt`, `backend/uv.lock` and
files in the tree; neither performs network I/O nor invokes `uv`"), which is
mechanically checkable by reading the test. This is a suggestion, not a blocking
finding: the claim is true and the existing APRAS-120 test already establishes
the property.

## Suggestions

- Say that the whole mechanism only exists once this task's commit is on
  `master`, because `pull_request_target` takes the workflow from the base ref —
  i.e. results 1–5, 7, 8 land first, and result 6 is demonstrated against
  `master` afterwards. Implied by the repository's land-on-master habit, never
  stated.
- Dependabot stops force-pushing a branch it detects as modified by another
  author. That is harmless here (the PR is reviewed and merged, not re-driven),
  but a line in §2 saying so would stop a later reader from reading the bot push
  as interference with dependabot's own updates.
- Require the `$RUNNER_TEMP` copy to be invoked as `bash "$RUNNER_TEMP/…"` (or
  `chmod +x` then execute by absolute path) so nothing resolves the script name
  through `PATH` or the work tree.
- `uv venv --python 3.13` reads `backend/.python-version` (`3.13`) when run from
  `backend/`; harmless, but the explicit `--python 3.13` the spec already
  prescribes is what keeps it so. Worth one clause saying the version is
  explicit and not inherited.
- Rephrase result 5's "offline" per the question above.
- Result 2's "line 2 of the committed export quotes the script's command
  exactly" is true only because `uv` writes its argv verbatim. Add that the
  script must therefore pass a fixed argument list with no conditional flags and
  no `--directory`, or the header differs by invocation site and result 3's
  byte-for-byte claim becomes environment-dependent (related to N1, but a
  distinct cause).
