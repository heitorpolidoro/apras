# APRAS-121 — spec review, round 3 (findings-only)

VERDICT: NEEDS_REVISION

Spec reviewed: `/Users/heitor/workspace/apras/docs/tasks/APRAS-121-spec.md`
Previous reports: `docs/reviews/APRAS-121-spec-review.md` (round 1),
`docs/reviews/APRAS-121-spec-review-round2.md` (round 2).
Mode: findings-only re-review of the six round-2 blocking findings (N1–N6),
plus a consistency pass limited to the sections the revision rewrote (§1's pin
and needle paragraphs, §2 in full, §3's `setup-uv` and `uv lock --check`
paragraphs, §4's "How each of the two files is produced", `Files touched`, the
renumbered `Expected Results`, and the operator-prerequisite section).

Task has no `parent`; `NEEDS_SPLIT` remains available and remains the wrong
verdict — one deliverable, one subsystem, one reviewable PR. Unchanged from
rounds 1 and 2.

## What I did

- Read the revised spec in full and the round-2 report.
- Verified `uv 0.12.19` is a real published release
  (`gh api repos/astral-sh/uv/releases/tags/0.12.19` → published
  `2026-09-25`, `prerelease: false`); latest is `0.12.21` (`2026-09-29`).
  Local `uv --version` is `0.12.19` (Homebrew), matching the spec's claim.
- Read `astral-sh/setup-uv@v8.1.0`'s `action.yml`, `src/utils/inputs.ts`,
  `src/download/download-version.ts`, `src/download/checksum/checksum.ts` and
  `src/download/checksum/known-checksums.ts` from the tag, to settle what
  `version:` accepts, what `pyproject-file:` does, and what the cache and
  checksum behaviour are.
- Re-read all three `setup-uv` blocks in `.github/workflows/ci.yml`,
  `.github/workflows/migrate.yml`, `backend/pyproject.toml`,
  `backend/.python-version`, `backend/requirements.txt`'s header,
  `backend/scripts/` listing, `AGENTS.md` and
  `backend/tests/test_requirements_export.py` for existing `uv export`
  literals.
- Confirmed repository visibility (`PUBLIC`) to test the `git fetch` variant of
  the N6 fix, and re-queried ruleset `16257354` (`bypass_actors` still
  `RepositoryRole 5 / always`, nine-ish rule set intact).
- Listed Actions and Dependabot secrets: `REQUIREMENTS_EXPORT_TOKEN` is absent
  from both today (Actions has `POSTGRES_URL_NON_POOLING`, `SECRET_KEY`,
  `SONAR_TOKEN`, `VERCEL_TOKEN`; Dependabot has `SONAR_TOKEN` only).
- Wrote nothing but this report. Staged nothing, created no branch or PR,
  triggered no workflow, ran no `uv sync` / `npm install`, ran no `git stash`,
  touched nothing under `frontend/` and nothing belonging to another task.

## The six round-2 findings

### N1 — resolved, and the premise checks out

`0.12.19` is real, current (two patch releases behind latest on the day of
review) and is the version in use locally, so the pin does not immediately
require anyone to change toolchains. `setup-uv@v8.1.0`'s `action.yml` declares
`version` as "The version of uv to install e.g., `0.5.0`", so
`version: "0.12.19"` is exactly the prescribed form.

The dispatch asked whether dropping `pyproject-file:` from `Backend Tests`
costs anything else. It does not, and for a sharper reason than the spec gives:
**`setup-uv@v8.1.0` has no `pyproject-file` input at all.** The declared inputs
are `version`, `version-file`, `python-version`, … ; `src/utils/inputs.ts`
reads `core.getInput("version-file")` and, when empty, searches
`["uv.toml", "pyproject.toml"]` relative to `working-directory`
(default `github.workspace`). The repository has no root `uv.toml` and no root
`pyproject.toml`, so every current `setup-uv` step in this repository installs
**latest** and has been emitting an unrecognised-input warning for
`pyproject-file:`. That confirms N1's floating-latest diagnosis exactly, and
makes the removal a pure no-op beyond silencing the warning. §1/§3's prose
reads as though `pyproject-file:` were doing something; harmless, but see
suggestions.

The deliberate non-touch of the other `setup-uv` uses is correct as written
(§1 says only "the other `setup-uv` uses … do not run the script"). For the
record, the three in `ci.yml` are `Backend Tests`, `Backend Migration Tests
(Postgres)` and `Backend Lint (ruff)` — not Frontend/Sonar — plus
`migrate.yml`. None runs the script.

Rejecting `[tool.uv] required-version` as the pin is right for the privileged
job, and `backend/pyproject.toml` has no `[tool.uv]` section today, so nothing
contradicts it.

### N2 — resolved

`uv lock --check` is chosen by name, `uv export --locked` is rejected by name
with the reason, and §1's needle paragraph now states that the needle matches
only the `export` subcommand so `uv lock --check` is outside the guard. No
self-tripping rule remains. (One false-positive hazard in how the needle is
specified is a suggestion below, not a finding.)

### N3 — resolved

§4 now requires `backend/uv.lock` to be the output of a real
`uv lock` / `uv lock --upgrade`, says only `backend/requirements.txt` is
hand-edited, and states the diagnosis motive ("a failed demo must be
diagnosable as the mechanism failing"). The construction also still yields both
properties §4 wants. I checked the demo's full path: the bot regenerates the
export from the real lock, so on the pushed sha `uv lock --check`,
regenerate-and-diff and the dry-run all pass, which is what result 8's
`Backend Tests: success` needs. The pre-push red run on the original head sha
is expected and does not conflict with result 8's wording.

### N4 — resolved

`enable-cache: false` is required, `actions/cache` and "any other cache action"
are forbidden, and the reason is stated in the base-scope terms the finding
used. Worth recording that the finding's premise is confirmed by the action
itself: `enable-cache` defaults to `"auto"`, and the default
`cache-dependency-glob` includes `**/uv.lock` and `**/pyproject.toml` — i.e.
head-controlled files would have keyed a base-scope cache entry. The explicit
`false` is load-bearing, not decorative.

### N5 — resolved, by the removal I would have preferred

The freshness assertion is out of the privileged job and in `Backend Tests`;
§2 states the blast radius explicitly (ruleset `16257354`,
`bypass_mode: always`, "code execution in *any* step of this job is a `master`
compromise"), names `uv export --frozen` as the only metadata-free path,
and says in so many words that the job "runs **nothing else that could need
project metadata**". The deliberate consequence — a stale head lock yields an
export matching that lock, and the staleness is reported by `Backend Tests`
with a read-only token — is stated and is the right trade.

I re-swept the privileged job for head-controlled execution after the move, as
the dispatch asked, and found nothing that reaches head code:

- **The `$RUNNER_TEMP` script copy** comes from the base sha, is invoked as
  `bash "$RUNNER_TEMP/export_requirements.sh"` by absolute path, so neither
  `PATH` nor the work tree selects it. The head's copy is explicitly never
  executed or sourced.
- **`uv export --frozen`** reads `uv.lock` and does not re-resolve; with
  `--frozen` it does not validate the lock against `pyproject.toml` and does
  not obtain metadata through a PEP 517 backend. The residual head influence is
  a **denial of service, not execution**: a head `[tool.uv] required-version`,
  or malformed TOML, makes uv refuse and the job fail closed. That is benign
  (the PR simply stays unregenerated) but it is one more reason not to treat a
  job failure as a mechanism failure during the demo.
- **The uv binary download** is driven by the base-provided action at a pinned
  tag with `github-token` defaulting to `github.token`; no head input selects
  it now that `pyproject-file:` is gone. See the checksum suggestion below.
- **`.gitattributes` / hooks**: round 2's clearance holds — filter *drivers*
  require git config a PR cannot write, and `actions/checkout` clones fresh, so
  there are no repository-supplied hooks. The one residual is cosmetic and
  non-executing: a head `.gitattributes` with `eol=crlf` or
  `working-tree-encoding` on `*.txt` could make the bytes git stores differ
  from the bytes the script wrote. It needs push access to arrange, lands only
  on the PR branch, and `Backend Tests` on that branch judges the result, so it
  is not a finding.
- **The push step** runs `git add`/`commit`/`push` with the PAT scoped to that
  step's `env`; no hook, no config and no action input in it is head-provided.

So the security half is sound as specified. The design is **not** unsafe; my
two blocking findings below are a construction that cannot be implemented as
written and an unverifiable result, not a hole.

### N6 — resolved in substance, but the prescribed construction cannot be implemented literally — see B1

The right mechanism is named (second checkout at `base.sha`, or an explicit
`git fetch --no-tags --depth=1 origin "$BASE_SHA"`), reliance on the head
checkout's history is forbidden, `fetch-depth: 0` is dropped, and the
"base sha predates the script" case has a named failure message. I confirmed
the `git fetch` variant is viable here: the repository is **public**, so an
unauthenticated fetch-by-sha works even though `persist-credentials: false`
has removed the checkout's `http.extraheader`. (Had the repository been
private, that variant would have failed and only the second checkout would
work — worth knowing if visibility ever changes.)

What does not work is the parenthetical constraint on the second checkout. See
B1.

## New blocking findings

Both are consequences of the round-2 fixes, so both are in scope for a
findings-only round.

### B1 — the prescribed second checkout cannot be placed where §2 requires, and the layout it actually needs is unstated

§2 requires "a **second `actions/checkout@v6`** at
`github.event.pull_request.base.sha` (`persist-credentials: false`,
`fetch-depth: 1`, `path:` outside the head work tree)". `actions/checkout`'s
`path:` is documented as "Relative path under `$GITHUB_WORKSPACE`" and the
action rejects a path resolving outside the workspace. The head checkout, as
every other job in this repository writes it, is at the workspace root — so
**every legal `path:` is inside the head work tree** and the instruction is
unsatisfiable as written. The implementer must deviate, and the two deviations
differ materially:

- *Head at the workspace root, base at e.g. `path: base-ref/`.* Works, but the
  base tree then sits inside the head work tree as an untracked directory, and
  **checkout order becomes load-bearing**: `actions/checkout` cleans its target
  directory (`git clean -ffdx`), so a base checkout written *before* the head
  checkout is deleted by it, the `cp` into `$RUNNER_TEMP` then fails, and the
  mechanism is inert again — the same silent-inertness class as round-1 B1 and
  round-2 N6, arrived at a third way. It fails closed, so it is a reliability
  problem rather than a safety one, but it is the exact failure this finding
  chain keeps producing.
- *Head into `path: head/`, base into `path: base/`.* Honours the wording, but
  relocates every path in the workflow — the `cd backend` the shared script
  does, the `git add backend/requirements.txt`, the push's work tree — and the
  spec says nothing about it, while §3 runs the same script from the repository
  root.

Decide it: either name the layout and the order ("the head checkout is the
first step and is at the workspace root; the base checkout follows it at
`path: <name>`, which is inside the work tree and is not added to the commit"),
or — cleaner, and now known to work because the repository is public — drop the
second checkout and require the `git fetch --no-tags --depth=1 origin
"$BASE_SHA"` form, with `git show "$BASE_SHA":backend/scripts/export_requirements.sh`
redirected into `$RUNNER_TEMP`. Either way the result-7 wording ("via a second
`actions/checkout@v6` at that sha (or an explicit `git fetch …`)") inherits
whatever is decided and should name the path or the fetch, so QA can check it
by reading the workflow.

### B2 — result 8's "may be QA'd with this result outstanding" leaves QA no way to tell *outstanding* from *unmet*

Result 8's pass branch is fully mechanical (branch name, one commit touching
only `backend/requirements.txt`, the author identity, the secret used, nine
checks on the new head sha, `Backend Tests: success`, the no-op re-run, four
recorded facts, PR closed and branch deleted). The gate is not. QA receives
**only** the `expected_results`, and what result 8 tells it is "*(Gated on the
operator prerequisite above …; the task may be QA'd with this result
outstanding.)*" — a reference to a section QA cannot see, and a licence to pass
the result with no evidence and no stated condition. The two states QA must
distinguish are "the operator has not minted the PAT" and "the mechanism was
built and the demo did not work", and nothing in the result separates them.
Since result 8 is the task's *only* end-to-end evidence, that is the one result
whose verification must not be left to inference.

The fix is cheap, because the outstanding branch is itself observable: the
secret's absence is a one-command check (`gh secret list` today returns
`POSTGRES_URL_NON_POOLING`, `SECRET_KEY`, `SONAR_TOKEN`, `VERCEL_TOKEN` — no
`REQUIREMENTS_EXPORT_TOKEN`). Phrase the result as two checkable branches
inside the result text itself, without relying on the prose section: either the
full demonstration evidence is recorded on the task, **or** the repository's
Actions secret list contains no `REQUIREMENTS_EXPORT_TOKEN` and the task
records that the demonstration is pending that secret. Then QA can decide pass
or fail from the result alone, in both states, and a demo that was attempted
and failed cannot be filed as "outstanding".

## The renumbering, and whether anything should merge

Nothing was lost. Mapping round 2's eight onto round 3's ten: old 1→1, 2→2,
3→4, 4→5, 5→6, 6→8, 7→9, 8→10, with two genuinely new entries — 3 (the uv pin,
from N1) and 7 (the privileged workflow's construction: base-sha script
acquisition, `bash "$RUNNER_TEMP/…"`, named failure, no `uv lock`,
`enable-cache: false`, no `actions/cache`, from N4/N5/N6). Old result 4's
dry-run clause and the new `uv lock --check` clause are correctly folded into
one result (5), which is where N2/N5 put the assertion.

All in-prose cross-references resolve: §1's "result 2's 'line 2 quotes the
script's command exactly'" and "result 4's byte-for-byte claim" both land on
the right entries; §3's "result 6(b)" matches result 6's clause (b); §4's
"result 8 requires `Backend Tests` to reach `success`" matches; the
"Results 1–7, 9 and 10" formula is used consistently in all three places it
appears. No dangling reference of the kind round 1's B7 found.

On merging: results 1 and 6 overlap — 1 asserts the single-definition property,
6 asserts the test that enforces it — and results 1 and 2 are both properties
of the same script. Both overlaps are deliberate and harmless (one states the
repository property, the other the test), and each is independently checkable,
so I would not force a merge. Ten results for a task with two new workflow
surfaces, a new script, two tests and a doc change is not padding.

## Suggestions

- §1/§3 describe dropping `pyproject-file:` as if the input were selecting a uv
  version. In `setup-uv@v8.1.0` it is not a declared input at all (the input is
  `version-file`), so the current steps install **latest** and log an
  unrecognised-input warning. Saying that is strictly stronger than the current
  wording and removes a wrong mental model for whoever next reads the pin.
- The pin test's locator needs narrowing. `ci.yml` has three `setup-uv` blocks
  and only `Backend Tests` gains `version:`; it also contains
  `node-version: 24`, which a naive search for `version:` matches. Say the test
  reads the `version:` input of the `setup-uv` step in the `backend` job (the
  test is N1's whole backstop, so its locator should not be left to taste).
- Give the needle a word boundary and keep it line-scoped. "`uv`, whitespace,
  `export`" matched loosely across newlines false-positives on
  `astral-sh/setup-uv` followed by a shell `export FOO=…` line — plausible in
  exactly the two workflows this task writes. `\buv[ \t]+export\b` per line
  keeps the intent and cannot collide.
- Consider pinning `checksum:` alongside `version:` on the privileged job's
  `setup-uv`, or using a `setup-uv` release that knows `0.12.19`. With the
  default manifest, `download-version.ts` validates only against user input or
  the baked `KNOWN_CHECKSUMS` table, and `validateChecksum` **returns silently**
  (debug-level log) when neither has an entry. `v8.1.0` was published
  `2026-04-16` and `uv 0.12.19` on `2026-09-25`, so the table has no entry: the
  pin names a version but not bytes. This is the repository's existing ambient
  baseline for every other `setup-uv` step, so it is not a regression and not
  blocking — but this is the one job holding a push credential.
- Say who bumps the pin. `uv` ships roughly weekly, dependabot does not update
  a `version:` string input, and a stale pin is safe but silently ages; one
  sentence ("the pin is bumped deliberately, by editing the three literals
  together") closes the question before someone reads the red pin test as a
  bug.
- §2 could note the head's remaining influence on the privileged job for
  completeness: a head `[tool.uv] required-version` (or malformed
  `pyproject.toml`) makes uv refuse to run, so the job fails closed and the
  export is not regenerated. Harmless, and knowing it is a *possible* failure
  mode keeps it from being mistaken for a broken mechanism during the §4 demo.
- Spell out the push refspec. The head checkout is detached at `head.sha`
  (and, with `fetch-depth: 0` now dropped, shallow), so the push must be
  `git push origin HEAD:refs/heads/"$HEAD_REF"`; a bare `git push` on a
  detached HEAD fails. Pushing from a depth-1 clone is fine against GitHub, so
  dropping `fetch-depth: 0` costs nothing else.
- Record in §2 that the repository being **public** is what makes the
  `git fetch --no-tags --depth=1 origin "$BASE_SHA"` variant work with
  `persist-credentials: false`. If visibility ever changes, that variant stops
  working and only the checkout form remains.
