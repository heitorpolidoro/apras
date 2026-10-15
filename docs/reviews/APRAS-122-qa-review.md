# APRAS-122 — QA verification

VERDICT: NEEDS_REVISION (= REJECTED)

Scope note: the dispatch brief told me to verify eleven of fourteen results and
to report R2, R3, R5 as `PENDING THE PUSH` and R4 as pending-and-time-ordered.
**That briefing was wrong about three of those four.** The pre-landing
dispatched run it believed did not exist **does exist** (`37315213778`), its
`head_sha` **is** the landing sha, and I read its job conclusions and logs
directly. So I was able to verify **thirteen of fourteen**: R1–R4 and R6–R14.
Only **R5** is genuinely pending the push. Details under "Pending the push".

The single blocking failure is **R10**.

---

## Verification environment

- Main checkout `/Users/heitor/workspace/apras` at `04eabec`, read-only.
- All mutation work done in a namespaced scratch tree,
  `…/scratchpad/qa122_opus5/tree`, built by copying `.github/workflows/*.yml`,
  `AGENTS.md` and `backend/tests/test_workflow_actions.py` into a
  `<root>/backend/tests/` layout so the module's `parents[2]` `REPO_ROOT`
  resolves inside the scratch tree. Baseline there: `15 passed`.
- After every mutation the file was restored from the main checkout and the
  restore verified with `cmp`. Final state: `cmp` clean on all six copied
  files, and `git status --porcelain -- .github/ AGENTS.md backend/tests/` in
  the main checkout is **empty**. Nothing was staged, committed, pushed or
  dispatched; no branch was created; `backend/scripts/sync_obras_from_drive.py`
  was not touched.
- GitHub access was `gh` **reads** only (`gh run view`, `gh api … /jobs`,
  `gh api … /branches`). No `curl`.

---

## Expected Results Checked

- [x] **R1** — verified by `grep -rn 'astral-sh/setup-uv' .github/workflows/`
  plus reading each step. Five occurrences on today's tree, exactly the five the
  brief names: `ci.yml:55`, `ci.yml:224`, `ci.yml:285`, `migrate.yml:17`,
  `requirements-export.yml:106`. Every one passes `version: "0.12.19"` and
  `enable-cache: false`; `requirements-export.yml` additionally passes
  `checksum:` (declared at `v8.1.0`, see R6). No step passes `version-file:` —
  `grep -rn 'version-file' .github/workflows/` returns nothing.
  `grep -rn 'pyproject-file' .github/workflows/ | wc -l` printed **`0`**. The
  set was derived from the tree, not from the audit's list. Key order not
  judged.

- [x] **R2** — verified against GitHub, both sides.
  **Before**, run `36924174723` (`push`, head `25e9dc6`): the audit records run
  id, the `gh api …/jobs` command, the five job rows and the three uv-using job
  ids. I re-ran `gh api repos/:owner/:repo/actions/runs/36924174723/jobs` and
  got the same five rows, and pulled each of `110577272457` / `110577272946` /
  `110577272967` with `gh run view --job <id> --log`. Each logs
  `Could not determine uv version from uv.toml or pyproject.toml. Falling back
  to latest.` and `Successfully installed uv version 0.12.21`. The audit's
  statement that `grep -c 'Unexpected input'` returned **2** per job (main step
  + post step) is correct and is *not* papered over.
  **After**, run `37315213778`, whose `head_sha` is
  `40d40a2bc4ccc490df9f65adfc94ead9b645d0bc` — the landing commit. I pulled all
  three uv-using job logs: each prints `Successfully installed uv version
  0.12.19`, `grep -c 'Falling back to latest'` is **0**, and
  `grep -c 'Unexpected input'` is **0**. R2 says "a CI run on the landing
  commit", not "the run the push to master fires", and this run is literally on
  the landing commit. **Met.** If the operator intended the narrower reading
  (the push-triggered run on `master`), see "Pending the push".

- [x] **R3** — verified via
  `gh api repos/:owner/:repo/actions/runs/37315213778/jobs --jq '.jobs[] |
  "\(.id) \(.name) \(.conclusion) attempt=\(.run_attempt)"'`:
  ```
  111780126776 Backend Migration Tests (Postgres) success attempt=1
  111780127073 Backend Tests success attempt=1
  111780127158 Backend Lint (ruff) success attempt=1
  111780127391 Frontend Tests success attempt=1
  111782465849 SonarCloud Scan success attempt=1
  ```
  All three uv-using jobs are `success`; none is `failure`, `cancelled` or
  `skipped`. `gh api …/runs/37315213778 --jq '.run_attempt'` returns `1`, so no
  later-attempt escape clause is being leaned on and the audit's attempt-1
  claim holds. `requirements-export.yml` had no job because APRAS-121 had not
  landed, which the audit states — the "if present" condition is satisfied
  vacuously and correctly.

- [x] **R4 — MET by the first path, not pending.** The brief assumed the
  dispatched run did not exist. It does:
  `gh run view 37315213778 --json headSha,event,headBranch,conclusion` returns
  `{"conclusion":"success","event":"workflow_dispatch",
  "headBranch":"tmp-apras-122-uv-pin-gate",
  "headSha":"40d40a2bc4ccc490df9f65adfc94ead9b645d0bc"}`.
  Checked against every clause of the first path:
  - `workflow_dispatch` of `ci.yml`: yes, `event: workflow_dispatch`.
  - on a ref other than `master`: yes, `tmp-apras-122-uv-pin-gate`.
  - started before the pin commit reached `master`: yes — created
    `2026-10-05T13:13:58Z`, and local `master` has still not been pushed at all,
    so the ordering is unconditional.
  - recorded in `docs/tasks/APRAS-122-action-audit.md` by run id, with the three
    named jobs at `conclusion: success` on 0.12.19: yes, §3 and §4.
  - `head_sha` recorded alongside the sha `master` landed, and equal: yes, §3
    carries both as `40d40a2bc4ccc490df9f65adfc94ead9b645d0bc` and marks them
    equal; I confirmed `40d40a2` is the pin commit on local `master`.
  The audit correctly declines the second path rather than misusing it: §3
  records `q-1790947582472-122`, `answered_at 2026-10-02T13:33:08.907Z`, answer
  **`yes`**, and states in as many words "no refusal is being quoted". That
  matches the brief's own reading that `yes` is not a refusal. The throwaway ref
  was deleted — `gh api repos/:owner/:repo/git/ref/heads/tmp-apras-122-uv-pin-gate`
  returns 404 and it is absent from `gh api repos/:owner/:repo/branches`.
  The brief asked me to quote the result's sentence about a missing dispatched
  run: *"A missing dispatched run while that entry carries no refusal is a
  failure, not an outstanding item."* That sentence does not bite here, because
  the dispatched run is not missing.

- [ ] **R5 — pending the push.** See the dedicated section.

- [x] **R6** — verified by two of my own mutations plus a provenance
  cross-check.
  *Undeclared input.* I added `python-versions: "3.13"` (a near-miss of the
  declared `python-version`) to the `requirements-export.yml` step, confirmed it
  on disk with `grep -n`, then ran the module:
  ```
  AssertionError: requirements-export.yml:106: `setup-uv@v8.1.0` does not declare
  ['python-versions']; GitHub ignores undeclared inputs with a warning rather than
  failing, so the step quietly does something other than what it reads as
  ```
  `1 failed, 14 passed`. Restored, `cmp` clean.
  *Unknown ref.* I bumped `migrate.yml`'s ref to `v8.1.0 → v8.2.0`:
  ```
  AssertionError: migrate.yml:17: `setup-uv` ref 'v8.2.0' has no allow-list entry,
  so nothing here knows what it declares. Re-derive its inputs with:
      gh api repos/astral-sh/setup-uv/contents/action.yml?ref=v8.2.0 --jq '.content' | base64 -d
  and add the entry to DECLARED_INPUTS in test_workflow_actions.py.
  ```
  The message names the ref **and** the `gh api …?ref=<ref>` re-derivation
  command, as required. Restored, `cmp` clean.
  *Provenance.* I extracted the `valid inputs are [...]` list from job
  `110577272457`'s own log and diffed it against `DECLARED_INPUTS["v8.1.0"]`:
  24 names on each side, `only in runner: []`, `only in allow-list: []`.
  `checksum` is present — which is what lets APRAS-121's step pass. Run
  `36924174723` is cited as the provenance in the module's comment at lines
  73–79.

- [x] **R7** — verified by mutation and by reading.
  Deleting `version:` from `migrate.yml` alone:
  `AssertionError: migrate.yml:17: no 'version:' input, so this step installs
  floating-latest uv` — `2 failed, 13 passed`.
  Changing one literal alone (`ci.yml:285` → `0.12.20`):
  `the version: literals disagree: {'ci.yml:55': '"0.12.19"', 'ci.yml:224':
  '"0.12.19"', 'ci.yml:285': '"0.12.20"', 'migrate.yml:17': '"0.12.19"',
  'requirements-export.yml:106': '"0.12.19"'} … assert 2 == 1`.
  Swapping `version:` for `version-file:` on `migrate.yml` also goes red, so the
  pin cannot be converted back to a file input quietly.
  *Offline / scope.* The module imports only `ast`, `pathlib`, `re`,
  `dataclasses`. `grep` for `subprocess|socket|urllib|http|requests|httpx|
  urlopen|export_requirements` finds exactly one hit — the `FORBIDDEN_CALLS`
  literal itself. `workflow_files()` iterates `WORKFLOWS_DIR` only, and three
  self-checking AST tests enforce it. `backend/scripts/export_requirements.sh`
  is never read. The module also reads `AGENTS.md` and its own source, which is
  required by R12 and by the AST self-checks, so I read R7's "only files under
  `.github/workflows/`" as targeting the export script and the network, both of
  which are clean.

- [x] **R8** — all four anti-vacuity assertions verified, and the anti-vacuity
  clause itself attacked.
  1. *Derived count.* `scanned_occurrence_count()` sums
     `path.read_text().count("astral-sh/setup-uv@")` over `workflow_files()`;
     no literal appears anywhere in the assertion. I tested the number is really
     derived **in both directions**:
     - adding a **genuine sixth** `setup-uv` step to `migrate.yml` kept the
       module **green** (`15 passed`) — so no count is hard-coded;
     - adding a **comment line** `# prose about astral-sh/setup-uv@v8.1.0 and
       nothing else` to `release.yml` turned it **red**:
       `parser found 5 setup-uv steps but a plain substring scan found 6
       occurrences … assert 5 == 6`.
       **Comment prose cannot satisfy this assertion** — it breaks it. This is
       the specific vacuity the brief warned about and it does not apply here.
  2. *Both spellings.* Crippling the step regex to drop the `(?:-\s+)?` branch
     (blinding it to `migrate.yml`'s bare `- uses:`) produced three red tests
     including `test_both_step_spellings_in_this_repository_are_exercised`.
  3. *Non-empty mapping with `enable-cache`.* Deleting `enable-cache` from
     `ci.yml`'s first step:
     `ci.yml:55: expected 'enable-cache: false', got None` — `2 failed`.
  4. *Shared entry point.* `test_the_parser_flags_an_undeclared_input_in_the_
     inline_fixture` calls `parse_setup_uv_steps(...)` — the same named function
     `discovered_steps()` calls on the real tree; there is no fixture-only
     helper. Removing `pyproject-file:` from the inline fixture string turns it
     red, so the fixture's undeclared key is load-bearing, not decoration.

- [x] **R9** — the audit §5.1–5.4 records exactly the four required mutations
  (`pyproject-file:` re-added, one literal changed, one `version:` deleted,
  unknown ref) with pytest output pasted. I did not re-run those four; I built
  eight of my own instead (above) covering all four classes plus three extra,
  and every one went red with a message of the same shape. The pasted outputs
  are consistent with what the module actually produces, including the line
  numbers of the assertions (`:381`, `:414`, `:401`, `:374`), which match the
  committed file.

- [ ] **R10 — FAILED.** See Blocking Findings. In short: I redid the census and
  the tree yields **12 distinct third-party refs across 10 files** (9 excluding
  `requirements-export.yml`, which introduces no new ref) — exactly the figure
  R10 sanctions. The audit lists **6 rows** and justifies the gap with a
  recorded scan whose output does not reproduce.

- [x] **R11** — verified via `git show 40d40a2 -- .github/workflows/ci.yml
  .github/workflows/migrate.yml`: the only changed lines are the four
  `-        pyproject-file: backend/pyproject.toml` removals, four
  `+        version: "0.12.19"` additions and explanatory comments. Nothing else
  in `.github/workflows/` changed, and no action other than `setup-uv` was
  modified. §7 `Follow-ups` carries one entry with a proposed title ("Decide
  whether third-party action refs should be sha-pinned, or a `github-actions`
  dependabot ecosystem added") and a one-line scope.
  *Caveat, dependent on R10, not a second blocker:* the audit reports **zero**
  findings outside `setup-uv`, but six refs were never examined, so "zero" is
  currently a statement about an incomplete census rather than about the tree.
  Whether every finding also appears "in the task report" I could not check —
  I was given only the expected results, not the report.

- [x] **R12** — `AGENTS.md` lines 247–271 state all five things: the literal
  pin on every `setup-uv` step; that `pyproject-file` is not an input of
  `astral-sh/setup-uv`; the **two** reasons for one shared literal (the
  agreement assertion compares literals; one uv version in CI is one thing to
  reason about) and **nothing about re-resolution** — §D1's unmeasured
  hypothesis is absent, as required; and the deliberate one-commit bump with
  "No bot does it" and the local `UV_PIN` refusal as the signal.
  `AGENTS_MD_CLAIMS` in the test module holds those seven strings and
  `test_agents_md_documents_the_pin_and_its_bump_ritual` asserts them
  whitespace-collapsed. Two mutations confirm the assertion bites:
  rewording `No bot does it:` → `AGENTS.md is missing these claims verbatim:
  ['No bot does it']`; rewording "one uv version in CI is one thing" →
  `… ['one uv version in CI is one thing to reason about']`. Both restored,
  `cmp` clean.

- [x] **R13** — verified against **this task's own diffs**, which is the reading
  the brief asked me to apply and the one I agree with:
  `git diff --name-only 40d40a2~1 ea37e9a` yields exactly five paths —
  `.github/workflows/ci.yml`, `.github/workflows/migrate.yml`, `AGENTS.md`,
  `backend/tests/test_workflow_actions.py`,
  `docs/tasks/APRAS-122-action-audit.md`. None of
  `backend/pyproject.toml`, `backend/uv.lock`, `backend/requirements.txt`,
  `backend/tests/test_suite_hygiene.py`, `backend/tests/test_requirements_export.py`,
  `backend/tests/test_docs_agents_md.py` is among them, and nothing under
  `frontend/` is. No new test dependency was added — the module's hand-rolled
  parser exists precisely to avoid `pyyaml`.
  *On the other reading:* "unmodified in the tree since some earlier point"
  would fail, because APRAS-121 (`04eabec`) later rewrote
  `backend/requirements.txt` and `backend/tests/test_requirements_export.py`. I
  reject that reading — R13's purpose is to bound **this** task's blast radius,
  and holding APRAS-122 responsible for a commit that landed four days after it
  would make the result unsatisfiable by any means available to its author. If
  the operator wants the tree-state reading enforced, it belongs on APRAS-121,
  not here.

- [x] **R14** — run, not taken on report.
  `cd backend && uv run pytest tests/test_workflow_actions.py -v` → **15 passed**.
  `uv run ruff check .` → `[]` (zero findings).
  `uv run ruff format --check .` → `303 files already formatted`.
  `uv run pytest tests/test_lint_hygiene.py -q` → **4 passed**; `NOQA_CAP` is
  still `72` in `backend/tests/test_lint_hygiene.py` and was not raised by this
  task (that file is not in either commit's diff).

---

## Blocking Findings

1. **R10 — the action census is incomplete, and the recorded scan that justifies
   the omission does not reproduce.**

   R10 requires one row per distinct third-party `uses:` ref in
   `.github/workflows/`, derived from a recorded scan, and names a sanctioned
   outcome of 12 refs across 9 files (or 13 if `requirements-export.yml` adds a
   fourth `actions/checkout` ref). It further requires
   `actions/github-script@ed59741` and `actions/github-script@60a0d83` to appear
   as **two separate rows**.

   My own scan of the directory (python, one row per `uses:` after dropping
   `./` reusable calls) yields **12 distinct refs across 10 files, 43
   occurrences** — i.e. exactly the sanctioned 12, across 9 files once
   `requirements-export.yml` (which introduces no new ref, only
   `actions/checkout@v6` and `astral-sh/setup-uv@v8.1.0`) is set aside. So the
   tree gives the **first** sanctioned outcome, not the 13-ref one, and
   `requirements-export.yml` did **not** add a fourth `checkout` ref — there are
   three: `@v6`, `@v4`, `@8e8c483db84b4bee98b60c0593521ed34d9990e8`.

   The audit's §6 lists **6 rows**. Six refs have no row at all:

   | Missing ref | Files (occurrences) |
   | --- | --- |
   | `actions/create-github-app-token@29824e69f54612133e76f7eaac726eef6c875baf` | `gemini-dispatch.yml` ×2, `gemini-invoke.yml`, `gemini-plan-execute.yml`, `gemini-review.yml`, `gemini-scheduled-triage.yml`, `gemini-triage.yml` |
   | `actions/github-script@ed597411d8f924073f98dfc5c65a23a2325f34cd` | `gemini-scheduled-triage.yml` ×2, `gemini-triage.yml` ×2 |
   | `actions/github-script@60a0d83039c74a4aee543508d2ffcb1c3799cdea` | `gemini-dispatch.yml` ×1 |
   | `actions/checkout@v4` | `gemini-invoke.yml`, `gemini-plan-execute.yml` |
   | `actions/checkout@8e8c483db84b4bee98b60c0593521ed34d9990e8` | `gemini-review.yml` |
   | `google-github-actions/run-gemini-cli@v0` | 5 gemini files |

   Note that the two missing `github-script` refs are **precisely the two R10
   singled out by sha prefix** (`ed59741…`, `60a0d83…`) and demanded as separate
   rows. That R10 could name those prefixes at all is strong evidence its
   12-ref figure was derived from this directory, not from an imagined one.

   The audit does not merely omit them — it argues they do not exist:

   > **Those files do not exist in this repository and never have:**
   > ```
   > $ ls -1 .github/workflows/ | wc -l
   > 3
   > ```
   > …the derived answer is 6. There is consequently no `actions/github-script`
   > ref to give two rows to — a requirement that is vacuous here rather than
   > skipped.

   `ls -1 .github/workflows/ | wc -l` prints **10** today, and printed 9 at
   landing time. The six `gemini-*.yml` files are present in the working tree
   with mtimes of **2026-05-14**, five months before this task. They are
   untracked only because `.gitignore:132` carries `.github/workflows/gemini-*.yml`
   — which `git check-ignore -v` confirms. So the audit's `git ls-tree` and
   `git log --all` evidence is *true but off-target*: it proves the files are
   not **committed**, not that they are not **there**. The `ls` output recorded
   beside it is not reproducible and cannot have been produced by that command
   in this directory.

   There is a defensible substantive argument the author could have made — a
   gitignored workflow never reaches GitHub, so it never runs and cannot suffer
   the undeclared-input defect. I would have accepted that as an **explicit,
   reasoned exclusion**, in the same spirit as the reusable-workflow exclusion
   R10 does sanction. What is not acceptable is reaching the smaller row set by
   asserting the files never existed, on the strength of a command output that
   contradicts the directory.

   **Cheapest fix, author's choice of two:**
   (a) add the six missing rows, with `with:` keys, verdict and the `gh api
   action.yml` method per row — the two `github-script` refs as two rows; or
   (b) keep six rows but replace the "never have" paragraph with an honest
   exclusion: these six files are gitignored (`.gitignore:132`), have never been
   pushed, and therefore never execute on GitHub, so the defect class cannot
   occur in them — and correct the `ls -1 … | wc -l` transcript, which currently
   reads `3` against an actual `10`.
   Either way the census count in §6 must be re-derived from a scan that
   reproduces.

---

## Suggestions

- `AGENTS.md:266` reads "so the action ref moves only by a human edit either."
  — the trailing "either" is a leftover from an edit and makes the sentence
  ungrammatical. Not asserted by any claim string, so it is free to fix.
- §6's `setup-uv` row cites `ci.yml` lines `55, 160, 221`; those were correct at
  the landing commit but are `55, 224, 285` today, and the row has no
  `requirements-export.yml` entry. Both are legitimate under "at landing time",
  but if §6 is being revised for R10 anyway, re-deriving the line numbers and
  adding the fifth occurrence would make the document readable against `master`.
- §4's heading, "After — the same run, `37315213778`, on the landing commit",
  is doing double duty as both the gate (§3) and the after-state (R2/R3). It is
  correct, but a sentence saying explicitly "this run's `head_sha` is the
  landing commit, which is why one run serves as both the pre-landing gate and
  the after-state" would have saved a reviewer the inference — and would have
  prevented the orchestrator's briefing from concluding the run did not exist.

---

## Pending the push

- **R5 — genuinely pending.** `migrate.yml` runs only `on: push: branches:
  [ master ]`, so no run of it can exist while local `master` is twelve commits
  ahead of unpushed `origin/master` (`25e9dc6`). It needs, after the operator
  pushes: the `migrate.yml` run id; its `Run DB Migrations` job id and
  `conclusion: success` from `gh api repos/:owner/:repo/actions/runs/<run_id>/jobs`;
  and that job's log showing `Successfully installed uv version 0.12.19`, zero
  `Falling back to latest` lines and `grep -c 'Unexpected input'` at 0.
  The audit's §4 sub-section "`migrate.yml` is covered, not excluded" already
  states the coverage and the reason (it is the only job holding
  `POSTGRES_URL_NON_POOLING` and the only one running `alembic upgrade head`
  against production) and names the two commands to fill in, so only the
  observed values are missing.

- **R2 — verified, with one narrower reading left open.** Met as written ("a CI
  run on the landing commit"), by run `37315213778`. If the operator's intent
  was specifically the `push`-triggered `ci.yml` run on `master`, that run does
  not exist yet and would need the same three log checks on its three uv-using
  jobs. I did not treat this as a failure.

- **R3 — verified, same caveat.** All five jobs of `37315213778` are
  `conclusion: success` at `run_attempt` 1, recorded with ids. Under the
  narrower push-triggered reading it would need the job list of the `master`
  run, which would also then include `requirements-export.yml`'s job — a job
  that did not exist at landing time.

- **R4 — verified, not pending.** The first path is satisfied: dispatched
  `workflow_dispatch` run `37315213778` on `tmp-apras-122-uv-pin-gate`,
  `head_sha` `40d40a2` equal to the landing sha, three named jobs `success` on
  0.12.19, all recorded in §3/§4 with both shas and the equality stated. The
  second path is correctly not used, since `q-1790947582472-122` answers `yes`,
  which is not a refusal. The run predates any push to `master` because
  `master` has never been pushed, so the time-ordering holds unconditionally.
  No action is needed before the push to preserve R4.

---

VERDICT: REJECTED (NEEDS_REVISION) — on thirteen of fourteen results verified (R1–R4,
R6–R14); R5 alone is pending the push.
