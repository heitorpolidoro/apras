# APRAS-122 — spec review (round 1)

VERDICT: NEEDS_REVISION

Spec reviewed: `docs/tasks/APRAS-122-spec.md`. Working tree `master` @ `2cb0d48`.
No `parent`, so `NEEDS_SPLIT` was available and considered; rejected (see
"Scope" below).

## What I verified myself

- **`.github/dependabot.yml` has no `github-actions` ecosystem.** Only `uv`
  (`/backend`) and `npm` (`/frontend`). §D2's staleness argument therefore
  holds as written: a `uses:` ref moves only by a deliberate human edit, the
  staleness window is the bump commit, and the guard is not a recurring
  bot-driven red. This was the failure mode the design was asked to avoid and
  it does avoid it.
- **The 24 input names are complete and correct.** I fetched
  `repos/astral-sh/setup-uv/contents/action.yml?ref=v8.1.0` and parsed its
  `inputs:` block: exactly 24 names, in the same order, identical to the list
  the spec quotes from the truncated warning line. Provenance-by-warning-line
  is sound here and the entry is right. No finding.
- **The four steps exist as described**: `ci.yml:45` / `:135` / `:188`
  (`- name: Set up uv` + `uses:`), `migrate.yml:17` (bare `- uses:`), all four
  with `enable-cache: false` + `pyproject-file: backend/pyproject.toml`.
- **The no-`pyyaml` rationale holds.** `yaml` appears nowhere in
  `backend/uv.lock`, `backend/requirements.txt` or `backend/pyproject.toml`, so
  adding it really would move all three files into APRAS-121's territory.
- **Hand parsing is an established convention here.**
  `backend/tests/test_suite_hygiene.py` already hand-parses `ci.yml` (`CI_YML`,
  the `run: |` block extractor behind
  `test_every_ci_pytest_invocation_is_wrapped_in_timeout`). A text parser is
  the right trade, not an improvisation.
- **The coexistence claim holds.** `test_suite_hygiene.py` and
  `test_requirements_export.py` both exist and are owned by APRAS-119 and
  APRAS-121 respectively; a new `test_workflow_actions.py` collides with
  neither. `pytest.ini`'s `--cov=app --cov-fail-under=90` is unaffected by a
  new test module.
- **Third-party ref count: 12, not 10.** Distinct refs under
  `.github/workflows/`: `astral-sh/setup-uv@v8.1.0`, `actions/checkout@v6`,
  `actions/checkout@v4`, `actions/checkout@8e8c483…`, `actions/setup-node@v6`,
  `actions/upload-artifact@v7`, `actions/download-artifact@v8`,
  `SonarSource/sonarqube-scan-action@v7`,
  `actions/create-github-app-token@29824e6…`, `actions/github-script@ed59741…`,
  `actions/github-script@60a0d83…`, `google-github-actions/run-gemini-cli@v0`.
  Nine workflow files, all of which use at least one third-party action (the
  "9 workflow files" half of the claim is right).

## Blocking Findings

1. **§D6 and expected result 8 state the wrong ref count.** The prose says
   "**10** distinct third-party refs across 9 workflow files" and result 8
   says "(10 refs as committed)"; the real number is **12**, and the spec's own
   table is internally inconsistent with both figures — 11 rows, one of which
   (`actions/github-script@ed59741` / `@60a0d83`) silently covers two distinct
   refs. A QA agent holding only result 8 would check the inventory against 10
   and either fail a correct audit or pass one missing two refs. The count in
   result 8 must be 12, and the table must give `github-script@ed59741` and
   `@60a0d83` their own rows since they are separately pinned refs needing
   separate verdicts.

2. **§D6's run-log shortcut does not cover the rows it is claimed to cover.**
   "For the four actions that run in CI, the audit's verdict is already
   evidenced: run `36924174723` emits an `Unexpected input` warning for
   `setup-uv` **and for nothing else**." The evidence quoted comes from three
   jobs only — `110577272457` Backend Lint, `110577272946` Backend Tests,
   `110577272967` Backend Migration Tests. Those jobs never run
   `actions/setup-node@v6`, `actions/download-artifact@v8`,
   `SonarSource/sonarqube-scan-action@v7` (frontend and Sonar jobs), nor
   `migrate.yml`'s `actions/checkout@v6`. "The four actions that run in CI" is
   also undefined — six distinct third-party refs run in `ci.yml`. As written,
   result 8 lets a developer stamp `run-log` as the method on a row no log
   covers, and QA cannot detect it: the absence of a warning is evidence only
   for the specific jobs whose logs were read. The spec must either name, per
   row, the job id whose log is the evidence, or restrict the run-log method to
   the `setup-uv` row and require `gh api` on `action.yml` for every other row.

3. **§D1's "that one `ci.yml` block is the whole overlap" is false, and the
   `APRAS-121`-first land order breaks two of this task's own results.**
   APRAS-121 introduces a *new file under `.github/workflows/`* —
   `requirements-export.yml` — carrying a **fifth** `setup-uv` step
   (`version: "0.12.19"`, `checksum:`, `enable-cache: false`). That step falls
   squarely inside APRAS-122's guard scope, which is defined as "every
   `setup-uv` step in `.github/workflows/`". Consequences the spec does not
   handle:
   - result 1 enumerates the universe as "the three in `ci.yml` … and the one
     in `migrate.yml`", which is then incomplete;
   - result 6 asserts the discovered-step count equals the
     `astral-sh/setup-uv@` occurrence count "**(4 as committed)**", which
     becomes 5; a QA agent holding result 6 must fail a correct
     implementation;
   - §D1's `APRAS-121`-first rule says only "APRAS-122 changes only the
     remaining three steps", and says nothing about its own guard now
     governing a fifth step it did not write.
   The spec must state that the step count is derived, not literal, that the
   guard covers any `setup-uv` step present at landing time including
   APRAS-121's, and that `checksum:` is a declared input of `v8.1.0` (it is —
   I confirmed it in the 24) so that step passes the undeclared-input guard.

4. **Nothing in the task verifies the suite is green on the version it pins.**
   CI has been running **0.12.21** and the suite is green on it; this task
   pins **backwards** to 0.12.19, including on `migrate.yml`, the only step
   that holds `POSTGRES_URL_NON_POOLING` and runs `alembic upgrade head`
   against production. Results 2 and 3 check *only* log lines — the installed
   version string, the absence of `Falling back to latest`, the absence of
   `Unexpected input`. Both are satisfiable by a run in which `Backend Tests`,
   `Backend Migration Tests`, `Backend Lint` or the migration job **failed**.
   Results 2 and 3 must additionally require each uv-using job, and the
   `migrate.yml` run on `master`, to reach `conclusion: success` on the
   landing commit, recorded with the job ids. This is the one check that makes
   a backwards pin safe rather than asserted.

## Suggestions

- **Justify the literal, don't only inherit it.** §D1 explains *which task
  owns* the pin but never why **0.12.19** rather than CI's current 0.12.19↔
  0.12.21 delta. The real reason lives in APRAS-121 (the export's bytes are a
  uv-version artefact and the local script refuses on mismatch, so the
  producing uv must be the developer's). That reason applies to the `Backend
  Tests` step only — `backend-lint`, `backend-migrations` and `migrate.yml` do
  not produce the export, and the spec gives no reason for them to track the
  export's version rather than the newest. One sentence saying "one literal
  everywhere, because the agreement assertion is only meaningful if all four
  are the same string" would close it.
- **"Both specs write the same bytes" is not guaranteed.** Neither spec fixes
  the key order inside the `with:` mapping, so one may produce
  `enable-cache` → `version` and the other `version` → `enable-cache`.
  Harmless (the land-order rules mean only one of them writes the block), but
  the byte-identity claim should either be dropped or made true by fixing the
  key order for all four blocks.
- **§D1's "disjoint inputs" claim is inaccurate.** APRAS-121's agreement test
  reads `ci.yml` too, so the two tests' *inputs* overlap; what is disjoint is
  the two test *modules*. The conclusion ("neither needs editing when the other
  lands") still holds because both read the same value and expect the same
  literal — just state it that way.
- **Make the four mutations committed tests, not a one-time record.** The two
  anti-vacuity assertions in §D3 are adequate as far as they go: a parser that
  returns empty mappings fails the `enable-cache`/non-empty check, and one that
  misses `migrate.yml`'s bare `- uses:` form fails the count equality. But
  neither assertion requires the parser to ever *see* an input outside the
  allow-list — a parser that extracts only `version` and `enable-cache` passes
  both and passes the undeclared-input guard vacuously. Today the only thing
  that catches that is the manual mutation observation in the audit document,
  which does not survive a later refactor. A negative test over an inline
  fixture string (a four-line fake step carrying `pyproject-file:`, asserting
  the detector flags it) needs no dependency and no network, and converts the
  strongest part of the design into something the suite re-checks forever.
  Given this repository's recorded history of guards that passed while
  examining nothing, this is the change I would most like to see.
- **The count-equality assertion is partly self-referential** — both sides are
  derived from the same grep over the same text. Asserting that the discovered
  steps include at least one from `ci.yml` *and* one from `migrate.yml` (i.e.
  both spellings exercised) is cheap and catches the one regression the
  equality cannot.
- **Result 1's `grep -rc 'pyproject-file'`** counts matches in comments too and
  its exit status is nonzero when nothing matches, which makes it awkward as a
  pass condition; `grep -rn … | wc -l` equal to 0 is less surprising to QA.
- **Result 10's `AGENTS.md` claims** are prose assertions with no committed
  check, while this repository already has the convention for exactly that
  (`backend/tests/test_docs_agents_md.py` asserts literal claim strings).
  Optional, but the convention exists.
- **The third-party audit could be its own task.** It is the one part of
  APRAS-122 that is a separate, independently shippable deliverable (a
  document inventorying 12 refs, each verified via `gh api`). It is bounded
  and read-only, so it does not make the task un-reviewable — which is why
  this is a suggestion and not `NEEDS_SPLIT`.

## Scope

Not a `NEEDS_SPLIT`. The deliverable is one workflow edit across two files,
one new test module, one new document and one `AGENTS.md` paragraph, all
converging on a single defect. The audit is the only part that could ship
separately, and §D6's "inventory, not a repair" boundary keeps it finite.
