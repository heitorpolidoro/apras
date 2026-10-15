# APRAS-122 — code review

Reviewed: `git -C /Users/heitor/workspace/apras/.claude/worktrees/agent-a2d841ad072d9b6da diff a33f26a HEAD`
— 5 files, 1101 insertions, 4 deletions (`ci.yml` +13/-3, `migrate.yml` +6/-1,
`AGENTS.md` +25, `backend/tests/test_workflow_actions.py` +532 new,
`docs/tasks/APRAS-122-action-audit.md` +525 new).

Round 1. Verdict: **APPROVED**.

---

## 1. The fix itself (ER-1)

Derived from the tree, not from the spec's list:

```
.github/workflows/ci.yml:55       uses: astral-sh/setup-uv@v8.1.0
.github/workflows/ci.yml:160      uses: astral-sh/setup-uv@v8.1.0
.github/workflows/ci.yml:221      uses: astral-sh/setup-uv@v8.1.0
.github/workflows/migrate.yml:17  - uses: astral-sh/setup-uv@v8.1.0
```

All four carry `version: "0.12.19"` (ci.yml:63, 164, 225; migrate.yml:24) with
`enable-cache: false` immediately after. `grep -rn 'pyproject-file'
.github/workflows/ | wc -l` → **0**. `grep -rn 'version-file'` → **0**. Only the
four `with:` blocks changed in the two workflow files; no other action, no
`timeout-minutes`, no step reordering. Key order was not treated as a criterion
by me, per §D1 and ER-1.

`a33f26a`'s `timeout-minutes` work is intact: `ci.yml` has exactly five jobs
(`backend` 45, `backend-migrations` 20, `backend-lint` 10, `frontend` 15,
`sonarcloud` 15) — none added, none renamed, every one still carrying a
`timeout-minutes`. `tests/test_suite_hygiene.py` passes unmodified, which is the
mechanical form of that claim.

## 2. The pre-landing gate (ER-4), verified independently with `gh`

Everything the developer reported holds, checked against the API rather than the
document:

```
gh api repos/:owner/:repo/actions/runs/37315213778
  → {"id":37315213778,"run_attempt":1,"event":"workflow_dispatch",
     "conclusion":"success","head_branch":"tmp-apras-122-uv-pin-gate",
     "head_sha":"40d40a2bc4ccc490df9f65adfc94ead9b645d0bc",
     "path":".github/workflows/ci.yml"}
```

| Claim | Verified |
| --- | --- |
| run id `37315213778`, `workflow_dispatch`, `run_attempt` 1 | yes |
| `head_sha` == `40d40a2bc4ccc490df9f65adfc94ead9b645d0bc` | yes, exactly |
| `111780127073` Backend Tests | `success` |
| `111780126776` Backend Migration Tests (Postgres) | `success` |
| `111780127158` Backend Lint (ruff) | `success` |
| ref gone from `git ls-remote --heads origin` | yes, no `tmp-apras-*` ref |
| pull requests on that sha (`gh api .../commits/40d40a2/pulls`) | `0` |

Per-job log checks (`gh run view --job <id> --log`), all three jobs:

```
Backend Tests                      Successfully installed uv version 0.12.19
Backend Migration Tests (Postgres) Successfully installed uv version 0.12.19
Backend Lint (ruff)                Successfully installed uv version 0.12.19
grep -c 'Falling back to latest' → 0   (each job)
grep -c 'Unexpected input'      → 0   (each job)
```

The operator authorisation is a record, not prose: `.meridian/tasks.jsonl`
entry `q-1790947582472-122`, `by: "Agent"`, `answer: "yes"`, `answered_at:
2026-10-02T13:33:08.907Z` — matching §3 of the audit verbatim, including the
timestamp. The escape branch of ER-4 is correctly *not* taken.

Bonus evidence the document does not lean on but which matters: the Backend
Tests log of that same run shows `tests/test_workflow_actions.py ...............`
and `4178 passed, 38 skipped` — so the new guard and the whole suite were green
on 0.12.19 in CI, on the pin commit, not merely locally.

## 3. Escalation 1 — two commits, and whether ER-4's equality is satisfied

**It is satisfied.** This was the finding I read hardest, and I come down on the
developer's side.

ER-4 demands that the dispatched run's `head_sha` "is recorded alongside the sha
`master` landed and the two are **equal**". It never says *tip*. §D4's rationale
clause names the thing being guarded against exactly: "A dispatched run on 'the
pin commit' that was then amended before landing is not evidence for the landed
commit." The hazard is an observed artefact differing from the landed artefact.
Here `git diff 40d40a2 HEAD --stat` is one file, `docs/tasks/APRAS-122-action-audit.md`,
525 insertions, nothing else — no file any CI job reads, so the landed pin is
bit-for-bit the pin that was observed green and the equality ER-4 asks for is
checkable and true.

The tip reading makes the spec internally contradictory rather than strict: ER-2,
ER-3 and ER-10 all require the audit document to *record* the run on the landing
commit, and a committed document cannot record a run on the commit that contains
it. Under the tip reading the only exit is to not commit the document, which
ER-2/3/10 forbid. A reading that leaves no satisfying implementation is the wrong
reading; the ancestor reading preserves every property the spec was protecting
and is mechanically verifiable in one command. §3's closing paragraph states the
shape plainly rather than hoping nobody notices, which is the right handling.

One wording nit, in Suggestions: the §3 table row labelled "The sha `master`
lands" is, read alone, imprecise now that the tip is `c597527`.

## 4. Escalation 2 — ER-5 is incomplete, and cannot be otherwise pre-landing

Agreed, and marking it outstanding is the right handling. `migrate.yml` declares
only `on: push: branches: [ master ]` and no `workflow_dispatch`, so its run is
fired *by* the landing push: there is no pre-landing observation available, and
the gate's whole design depends on that (it is why a throwaway ref cannot reach
production).

§4's `migrate.yml` subsection does what is available to do: it states that
`migrate.yml` is **covered, not excluded**, with the reason (it is the only job
holding `POSTGRES_URL_NON_POOLING` and the only one running `alembic upgrade
head` against production), names the two exact commands, and names the four
values to fill in — `Run DB Migrations` job id, `conclusion: success`, the
`0.12.19` line, no `Falling back to latest`, `grep -c 'Unexpected input'` at 0.
It does not pretend to have them.

Stated plainly, for the orchestrator: **this task cannot reach a complete ER-5
until the operator pushes to `master`.** ER-5 is an open item that must be filled
in from the post-push `migrate.yml` run, in a docs-only follow-up commit, before
the task is `done`. That is not a defect in the change under review.

## 5. Escalation 3 — the spec's §D6 inventory figure

I verified the history claim myself in the worktree:

```
$ git ls-tree --name-only 2cb0d48 .github/workflows/
.github/workflows/ci.yml
.github/workflows/migrate.yml
.github/workflows/release.yml
$ git log --all --oneline -- '.github/workflows/gemini*'        → no output
$ git log --all --oneline -S'actions/github-script' -- .github/ → no output
```

The `gemini-*.yml` files and both `actions/github-script` refs have **never**
existed in this repository, on any ref. The derived scan is 6 distinct refs
across 3 files, 21 `uses:` occurrences — which I reproduced exactly
(`checkout@v6` ×8, `setup-uv@v8.1.0` ×4, `setup-node@v6` ×4,
`upload-artifact@v7` ×2, `download-artifact@v8` ×2, `sonarqube-scan-action@v7`
×1). Every file/line/occurrence pairing in the §6 table checks out against
`grep -n 'uses:'` **except** the third `setup-uv` step's line number (see
Suggestions).

Recording the divergence in §6 rather than quietly reconciling it was right, and
is the stronger of the two options. The spec itself framed the 12-refs figure as
"an illustration of today's tree, not as the criterion" and required the row set
to be derived with no count hard-coded, so the derived answer of 6 satisfies
ER-10 on its own terms. Silently producing 6 rows while the spec says 12 would
leave a reader unable to tell a correct derivation from a missed file — exactly
the failure mode a derived criterion exists to prevent. Naming it also records
that the spec's inventory was describing some other repository, which is useful
to whoever writes the next workflow spec. ER-10's `github-script@ed59741` /
`@60a0d83` two-row clause is **vacuous here, not skipped**, and §6 says so in
those words.

## 6. Escalation 4 — the 88-char `AGENTS.md` line

Right call. There is no line-length rule on Markdown anywhere in this repository:
`backend/tests/test_docs_agents_md.py` asserts claim strings and retired-model
absence, never width, and `ruff` does not read `.md`. So the long line
(`AGENTS.md`, the "Instead the signal is the local `UV_PIN`" line, 88 chars) is
purely cosmetic prose wrapping. Fixing it means editing a file that is part of
`40d40a2`, which means amending the commit the gate ran on and diverging from the
`head_sha` ER-4 asserts — trading a hard, externally-witnessed guarantee for a
reflow. Leaving it is correct, and it can be reflowed in any later commit at zero
cost.

## 7. The guard module (ER-6, ER-7, ER-8)

`backend/tests/test_workflow_actions.py`, 532 lines, 15 tests, no new dependency.

**ER-7 — offline, verified by reading.** Imports are `ast`, `pathlib`, `re`,
`dataclasses` and nothing else. No `subprocess`, no network client, no `uv`
invocation, no reference to `backend/scripts/export_requirements.sh` anywhere in
the module. The module additionally proves this about *itself* by AST — three
tests parse its own source and assert no forbidden import
(`test_this_module_imports_nothing_that_could_reach_the_network`), no forbidden
attribute call (`test_this_module_makes_no_subprocess_or_network_call`), and that
every `read_text` receiver is one of `{path, AGENTS_MD, THIS_MODULE}`
(`test_this_module_reads_only_the_workflows_and_agents_md`), plus a runtime half
asserting `workflow_files()` cannot return a path outside `.github/workflows/`.
That last one is the good kind of self-check: it has a "this check has stopped
checking" assertion (line 526) guarding against the receiver set going empty.

**ER-8 — the anti-vacuity module. This is where I looked hardest, and it holds.**

1. *Derived count* (line 283). `scanned_occurrence_count()` is a dumb
   `str.count(SETUP_UV)` over the same files, compared to `len(discovered_steps())`.
   No literal count anywhere in the module — I grepped; the only numeric literal
   in an assertion is `len(entry) == 24` for the allow-list, which is the runner's
   own input count, not a step count. The `scanned > 0` guard (line 291) is the
   part that matters: without it, zero-equals-zero would pass.
2. *Both spellings* (line 305). Asserts `"ci.yml" in sources` **and**
   `"migrate.yml" in sources`. Since `ci.yml` is `- name:` + unprefixed `uses:`
   and `migrate.yml` is a bare `- uses:`, both branches of `_content_column` are
   exercised by the real-tree scan, not by a fixture.
3. *Non-empty mapping with `enable-cache`* (line 319), with an explicit
   `assert steps` first and a message that names the real failure cause ("the
   parser is reading the wrong block").
4. *Inline fixture negative test* (line 334) — **and it calls the real entry
   point.** `test_the_parser_flags_an_undeclared_input_in_the_inline_fixture`
   calls `parse_setup_uv_steps(FAKE_WORKFLOW_WITH_UNDECLARED_INPUT, ...)`, and
   `discovered_steps()` at line 224 calls `parse_setup_uv_steps(path.read_text(...), path.name)`.
   One function, both paths — I checked that the module defines no second
   text-parsing helper the fixture could be satisfied through
   (`_parse_with_block` is a private sub-step of the same function, not an
   alternative entry point; `parse_setup_uv_steps` is the only `text -> steps`
   function and has exactly those two callers). The fixture also asserts the
   whole parsed mapping by equality, including `pyproject-file`, so a parser that
   extracted only `version`/`enable-cache` fails here. That is precisely the
   refactor-survivable property §D3.4 asks for.

**I tried to make the parser find zero steps, and something fails.** Narrowing
`_USES_SETUP_UV` so it matches nothing is caught three ways at once: the
`scanned > 0` / count-equality assertion, `assert steps` in the non-empty-mapping
test, and `len(steps) == 1` in the fixture test. Removing the `scanned > 0` guard
alone does not open the hole, because the other two remain. There is no
configuration of an empty discovery that leaves all 15 tests green.

**ER-6 — the allow-list.** Keyed by exact ref, 24 names, provenance comment
citing run `36924174723` and the three job ids (lines 71–84), and
`REDERIVE_COMMAND` quoted into the unknown-ref failure message. `checksum` is
present (so APRAS-121's step passes unchanged) and `pyproject-file` is absent,
both asserted explicitly at line 358.

## 8. ER-9 — I reproduced all four mutations in the worktree

Each applied **alone** to `ci.yml`'s first `setup-uv` step, module run, file
restored from a scratchpad copy and `cmp`-verified byte-identical afterwards
(`RESTORED-OK` on all four). No `git stash`, no `git checkout`, no staging.

| Mutation | Test that failed | Mechanism |
| --- | --- | --- |
| `pyproject-file: backend/pyproject.toml` re-added | `test_no_setup_uv_step_passes_an_input_its_ref_does_not_declare` | `ci.yml:55: setup-uv@v8.1.0 does not declare ['pyproject-file']` — 1 failed, 6 passed |
| `version` → `"0.12.21"` on one step | `test_all_setup_uv_version_literals_are_the_same_string` | `the version: literals disagree: {...}`, `assert 2 == 1` — 1 failed, 9 passed |
| `version:` line deleted | `test_every_setup_uv_step_pins_a_literal_version` | `ci.yml:55: no version: input`, `assert 'version' in {'enable-cache': 'false'}` — 1 failed, 8 passed |
| ref → `astral-sh/setup-uv@v9.0.0` | `test_no_setup_uv_step_passes_an_input_its_ref_does_not_declare` | unknown-ref branch, message naming `gh api repos/astral-sh/setup-uv/contents/action.yml?ref=v9.0.0 --jq '.content' \| base64 -d` and `DECLARED_INPUTS` — 1 failed, 6 passed |

Every one failed by the named test and the named mechanism. Final clean run after
restoration: **15 passed**, and `git status --porcelain` in the worktree is empty.

The one discrepancy: the pasted outputs in §5.2 report the third step at
`ci.yml:225`, while the committed tree puts its `uses:` line at **221** (225 is
that step's `version:` line). Reproducing the mutation gives
`{'ci.yml:55', 'ci.yml:160', 'ci.yml:221', 'migrate.yml:17'}`. The shift is 4
lines, which is exactly the length the second step's comment block lost between
capture and commit — so the evidence was captured on a transient tree state and
not re-run after the comments were trimmed. The mechanism and the failing test
are unaffected and I have re-observed all four against the committed tree; it is
a stale number in a document, not a guard that does not bite. Recorded as a
suggestion with the exact fix, since the audit lives in the docs-only commit
`c597527` and can be corrected without going near `40d40a2`.

## 9. ER-12 — the `AGENTS.md` claims

The added paragraph states all five required things, and the module asserts seven
claim strings verbatim against a whitespace-collapsed read (line 436–458, so a
reflow is not a red test — correct choice):

- "uv is pinned by a literal `version:` on every `astral-sh/setup-uv` step"
- "`pyproject-file` is not an input of `astral-sh/setup-uv`"
- "One literal is shared by every step for two reasons: the agreement assertion compares literals"
- "one uv version in CI is one thing to reason about"
- "The pin is bumped deliberately by the maintainer, in one commit that edits every `version:` literal together"
- "No bot does it"
- "the signal is the local `UV_PIN` refusal"

The two reasons asserted are the agreement-assertion-compares-literals reason and
the one-version-to-reason-about reason — **and nothing about re-resolution**. I
read the full added block for leakage of §D1's unmeasured hypothesis: there is
none. No mention of `uv sync --all-groups`, `--frozen`, `--locked`, lock format
or in-job re-resolution anywhere in `AGENTS.md` or in the claim tuple. That is
the discipline ER-12 asks for and it was followed.

## 10. ER-13 — nothing else moved

`git diff a33f26a HEAD --name-only` is exactly five paths:

```
.github/workflows/ci.yml
.github/workflows/migrate.yml
AGENTS.md
backend/tests/test_workflow_actions.py
docs/tasks/APRAS-122-action-audit.md
```

So `backend/pyproject.toml`, `backend/uv.lock`, `backend/requirements.txt`,
`backend/tests/test_suite_hygiene.py`, `backend/tests/test_requirements_export.py`
and `backend/tests/test_docs_agents_md.py` are all unmodified, and nothing under
`frontend/` is touched. No new test dependency.

## 11. ER-14 — gates re-run

| Gate | Result |
| --- | --- |
| `uv run pytest tests/test_workflow_actions.py -q --no-cov -p no:randomly` | **15 passed** |
| `uv run pytest tests/test_suite_hygiene.py tests/test_lint_hygiene.py tests/test_docs_agents_md.py tests/test_workflow_actions.py` | **39 passed** |
| `uv run ruff check .` | `[]` — zero findings |
| `uv run ruff format --check .` | `302 files already formatted` |
| `NOQA_CAP` | `72` in `test_lint_hygiene.py`, file unmodified by this diff — not raised |

(The worktree has no `.env`; I ran pytest with throwaway `POSTGRES_URL` /
`SECRET_KEY` values in the environment rather than copying a secrets file in. I
did not re-run the full 4178-test suite locally — CI ran it on `40d40a2` and the
log shows `4178 passed, 38 skipped`, which is the stronger evidence, and the
docs-only commit on top cannot affect it.)

## 12. Architecture, style, security

Matches the conventions the suite already establishes: a focused
`tests/test_*.py` module, module-level `#:`-commented constants, `REPO_ROOT` via
`pathlib.Path(__file__).resolve().parents[2]` as the other doc tests do, claim
strings asserted against a whitespace-collapsed read as
`test_docs_agents_md.py` does. New file rather than an edit to
`test_suite_hygiene.py` or `test_requirements_export.py`, which is the §D3
coexistence answer and keeps this change conflict-free against APRAS-119 and
APRAS-121. No duplication of APRAS-121's `UV_PIN`.

Security: no secret, no credential, no network, no subprocess, no shell. The
change *reduces* supply-chain exposure — the privileged `migrate` job that holds
`POSTGRES_URL_NON_POOLING` no longer installs whatever uv happens to be latest at
run time. Failure modes are fail-closed, as §4 of the audit argues. The guard
fails loudly on an unknown ref rather than passing, which is the right default
for a security-adjacent allow-list.

Test quality: assertions are specific and carry messages that name the file,
line, and what to do. No test asserts a tautology. The fixture test asserts the
whole parsed mapping by equality rather than a membership check, which is what
makes it a real negative test.

---

## Suggestions

1. `docs/tasks/APRAS-122-action-audit.md` — the third `setup-uv` step's line
   number is stale in two places: §6's table row reads `ci.yml` ×3 (55, 160,
   **225**) and §5.2's pasted pytest output reads `'ci.yml:225': '"0.12.19"'`.
   The committed tree puts that step's `uses:` line at **221** (225 is its
   `version:` line); reproducing mutation 2 against the committed tree yields
   `{'ci.yml:55', 'ci.yml:160', 'ci.yml:221', 'migrate.yml:17'}`. The capture
   predates the trimming of the second step's comment block by exactly 4 lines.
   Fix both occurrences to `221` — or re-run the four mutations and re-paste — in
   a docs-only amendment to `c597527`. This touches **only** the document, never
   `40d40a2`, so the gate sha is unaffected. Worth doing before QA, which will
   otherwise re-derive 221 and see a document that disagrees with the tree.
2. `docs/tasks/APRAS-122-action-audit.md` §3 — the table row labelled "The sha
   `master` lands" reads as a claim about the tip, which is `c597527`. The
   paragraph below the table explains the two-commit shape correctly; relabel the
   row to match it, e.g. "The pin sha `master` lands (parent of the docs-only
   tip; `git diff 40d40a2 HEAD --stat` is one file under `docs/`)". Pure wording,
   same docs-only commit as suggestion 1.
3. `AGENTS.md` — the UV_PIN sentence points at
   `backend/scripts/export_requirements.sh`, which does not exist yet
   (APRAS-121 has not landed; `grep -rn UV_PIN backend/` finds only this task's
   own test module). The claim string is mandated verbatim by ER-12, so this is
   correct as written, but it is a forward reference that will read as a broken
   one until APRAS-121 lands. Either leave it and let APRAS-121 resolve it, or
   add four words marking it as APRAS-121's. No action required.
4. `backend/tests/test_workflow_actions.py:205` — `_parse_with_block` matches any
   `key: value` line below `with:` at any depth, so a nested or block-scalar
   input value (`cache-dependency-glob: |` with `key: value`-shaped content
   under it) could contribute a spurious key to `inputs` and trip the
   undeclared-input guard. No step in this repository has such a value and the
   failure direction is conservative (loud false positive, never a silent pass),
   so this is a note for whoever adds the first multi-line input, not a defect.
5. `backend/tests/test_workflow_actions.py` — `discovered_steps()` re-reads and
   re-parses every workflow file in each of the seven tests that call it. Four
   small files, immeasurable cost; a module-scoped fixture or `functools.cache`
   would be tidier if the module grows.
6. For the orchestrator, not the developer: ER-5 is an open item by construction.
   After the push to `master`, fill in §4's `migrate.yml` subsection with the run
   id, the `Run DB Migrations` job id, `conclusion: success`, the `0.12.19` line,
   zero `Falling back to latest` and `grep -c 'Unexpected input'` at 0, in a
   docs-only follow-up commit, before the task reaches `done`. And §7's
   sha-pinning / dependabot-ecosystem follow-up needs to reach the task report
   and the operator, per ER-11.

---

VERDICT: APPROVED

Blocking findings: None
