# APRAS-122 — spec review, round 2 (findings-only re-review)

Spec: `docs/tasks/APRAS-122-spec.md` (read in full)
Cross-read: `docs/tasks/APRAS-121-spec.md`, `.github/workflows/ci.yml`,
`.github/workflows/migrate.yml`, `backend/uv.lock` header, `uv --version` (0.12.19 locally).
No file was modified, nothing staged, no workflow triggered.

**VERDICT: NEEDS_REVISION** — two blocking findings, both introduced by this round's fixes.

---

## 1. Previous finding 4 — the backwards pin's justification and the green requirement

### 1a. Is the `uv.lock` argument true?

Partly, and more narrowly than the spec states. The spec (§D1, last-but-one bullet) says
"**`backend/uv.lock` is resolved by uv**: if `backend-lint`/`backend-migrations`/`migrate.yml`
ran a newer uv than the export step, a resolution difference would be visible in those jobs
and invisible in the exported `requirements.txt`".

What the three jobs actually run is `cd backend && uv sync --all-groups` (ci.yml lines ~52,
~140, ~193; migrate.yml line ~23) — **no `--frozen`, no `--locked`**. `uv sync` in that form
re-locks when it considers the committed lock out of date with `pyproject.toml` (or when the
lock format/revision is not one it will reuse: the committed lock is `version = 1`,
`revision = 3`). So there *is* a mechanism by which the uv version in those jobs changes what
gets installed, and it is invisible to the `--frozen` export step. The argument is therefore
not purely decorative.

But in the ordinary case — fresh lock, supported revision — `uv sync` only *reads* an
already-resolved lock, and the uv version then affects nothing about resolution. The spec's
flat phrasing ("`backend/uv.lock` is resolved by uv") overstates this, and the more precise
statement is the stronger one: *these jobs do not pass `--frozen`/`--locked`, so a newer uv
may re-resolve in-job, which the export step's `--frozen` run can never surface.* Note also
that APRAS-121's `uv lock --check` lands only in `Backend Tests` — `backend-lint`,
`backend-migrations` and `migrate.yml` keep the non-frozen `uv sync` with no freshness gate.

This is **not blocking**: the first argument (the agreement assertion compares literals; two
pin groups means two bump rituals and two drift paths) carries the decision on its own, and
the second argument is true in a bounded, nameable case. It should be reworded to the precise
claim rather than the general one — see suggestion S1.

### 1b. Does the green requirement close the hole?

Mostly, and the mechanical holes the dispatch asked about are not there:

- `migrate.yml` has `on: push: branches: [ master ]` and **no `paths:` filter**, so the push
  that lands this task always fires it. The "migrate.yml run fired by the push to master"
  clause is always satisfiable; it cannot be vacuous for want of a matching path.
- Result 3 excludes `skipped` explicitly, as well as `failure` and `cancelled`.
- The non-uv required checks (`frontend`, `sonarcloud`, …) are not in the set, which is
  correct: nothing in this task can change them, and `sonarcloud` consumes `Backend Tests`'
  artefacts, so a green `Backend Tests` is the relevant signal.

One real residual remains, and it is not closed by any result: **production is verified only
after the fact.** `ci.yml` and `migrate.yml` both fire on the same push to `master`, in
parallel — there is no ordering between them. So the first time anything in this repository
runs the suite on 0.12.19 is the same moment `migrate.yml` runs `alembic upgrade head`
against production on 0.12.19. Result 3 and the `migrate.yml` clause record that outcome;
they do not gate it.

I judged this **non-blocking**, for three reasons: the failure mode is fail-closed (a bad
`uv sync` or a lock revision 0.12.19 will not reuse fails the step before `alembic` runs, and
alembic's own failure leaves the schema at the last applied revision); 0.12.19 is the version
the maintainer runs locally against this exact lock every day, so it is the best-tested
combination that exists; and the status quo is *floating latest*, which is strictly less
predictable than any pin. It is still worth closing cheaply — see suggestion S2, which uses
the `workflow_dispatch` trigger `ci.yml` already carries.

## 2. Previous finding 3's fix has leaked into a file this task must not write — BLOCKING

§D1 now states: "To make the 'same bytes' claim true rather than hoped for, the key order
inside **every** `setup-uv` `with:` mapping is fixed: `version:` first, then any `checksum:`,
then `enable-cache:`", and expected result 1 turns that into a QA criterion over the
**derived** step set: "Every `astral-sh/setup-uv` step in `.github/workflows/` at landing time
passes `version: "0.12.19"` **as its first `with:` key** … plus `requirements-export.yml`'s if
APRAS-121 landed first — which this task does not edit, only covers."

`docs/tasks/APRAS-121-spec.md` **does not specify any key order** for that step. It specifies
the keys — `version: "0.12.19"` (§1 bullet 2 and §Behaviour 2), `checksum:` for the 0.12.19
artefact (§1 bullet 5), `enable-cache: false` (§Behaviour 2, "No caching"), `pyproject-file:`
absent — and its result 3 and result 7 assert only presence and value, never position. So if
APRAS-121 lands first and writes, say, `enable-cache: false` before `version:`, result 1 is
**unmet by a correct implementation of both specs**, and APRAS-122 is forbidden from fixing it:
§Files touched says "`requirements-export.yml` — **not touched**", and §Out of Scope repeats
"authoring or editing `.github/workflows/requirements-export.yml` … this task's guard covers
its `setup-uv` step but never writes it".

This is the same shape as round 1's finding 3 — a criterion that fails a correct
implementation — reintroduced by the fix for finding 4's byte-identity claim. The spec is also
internally inconsistent about what compliance means: §Files touched defines
`requirements-export.yml`'s step as "already compliant (same literal, `checksum:` declared)",
with no mention of order, while §D1 and result 1 require order.

Also note the committed guard asserts nothing about key order (result 6 compares literals,
result 7 checks non-emptiness and `enable-cache`), so the ordering claim has no mechanical
backstop at all — it exists only as a QA-read sentence.

Any one of three closes it: scope the first-key requirement in result 1 to the steps this task
edits (`ci.yml` ×3, `migrate.yml`) and say explicitly that `requirements-export.yml`'s key
order is APRAS-121's to choose; or drop the ordering claim and the byte-identity framing
altogether (the pin's correctness never depended on it); or have APRAS-121's spec fix the same
order, in which case this spec must say so and APRAS-121 needs the matching revision.

## 3. §D6's row count contradicts result 9, and result 9's `12` is a hard-coded literal — BLOCKING

Verified against the tree: `grep` over `.github/workflows/` yields exactly **12** distinct
third-party `uses:` refs across **9** files, and every occurrence count in the table checks out
(`checkout@v6` 8 = ci ×5 + migrate + release ×2; `setup-node@v6` 4 = ci + release ×3;
`create-github-app-token` 7; `github-script@ed59741` 4; `github-script@60a0d83` 1). The two
`github-script` shas have separate rows. Round 1's finding 1 is resolved on that axis.

But the parenthesis added in the fix says: "**12 distinct third-party refs across 9 workflow
files** on today's tree (**13 rows** once `requirements-export.yml` adds no new ref but a fifth
`setup-uv` occurrence — the *ref* count is unchanged by APRAS-121)". That sentence contradicts
itself: one row per ref plus no new ref is **12 rows**, with the `setup-uv` row's occurrence
count moving 4 → 5. Result 9 then says "**all 12 distinct third-party `uses:` refs** … as one
row each". An implementer following §D6 produces 13 rows; QA reading result 9 wants 12. Round
1 blocked on precisely a wrong count in this section.

The second half is worse than a typo. Result 9's `12` is a **literal**, not derived, and the
premise that keeps it true — "`requirements-export.yml` adds no new ref" — is a premise about
a file **another spec writes**. APRAS-121 names `actions/checkout` for that workflow
(`persist-credentials: false`, `fetch-depth: 1`) but **never pins which ref**, and this
repository already carries three different `checkout` pins (`@v6`, `@v4`, `@8e8c483`). If
APRAS-121's new file uses anything but `@v6`, the landing tree has 13 refs and result 9 fails a
correct implementation — the identical failure mode to round 1's "(4 as committed)".

Fix the same way the step count was fixed: derive the ref count from a scan of
`.github/workflows/` at landing time, state 12-on-today's-tree as an illustration rather than
as the criterion, and delete the "13 rows" parenthesis.

## 4. Previous finding 2 — resolved

§D6 now says the run-log method is available for the `setup-uv` row only, names the three jobs
whose logs were read (`110577272457`, `110577272946`, `110577272967` of run `36924174723`),
states which actions those jobs never execute (`setup-node@v6`, `download-artifact@v8`,
`sonarqube-scan-action@v7`, `release.yml`'s and `migrate.yml`'s `checkout@v6`, the gemini
workflows), and routes **every other row** through
`gh api .../contents/action.yml?ref=<ref>` with the method recorded per row. Result 9 carries
the same split. This matches what the absence of a warning can and cannot prove. Resolved.

## 5. The vacuous-parser hole (§D3.4)

The inline-fixture negative test does close the class the previous round worried about, rather
than moving it: a parser that extracted only `version` and `enable-cache` passes assertions
1–3 but **fails** the fixture assertion, because the fixture's only interesting key is
`pyproject-file:` and the test demands the detector flag it. It is committed, offline, needs no
dependency, and — unlike the one-off mutation record — survives a refactor.

One wording residual, non-blocking: §D3.4 and result 7 say "the detector", singular, but
neither says the fixture must go through **the same** parse-and-check entry point the
real-tree assertions use. A future refactor could satisfy the fixture test through a
string-parsing helper while the file-reading path diverges. Naming the shared function (the
module must expose text → steps, and both the tree scan and the fixture must call it) makes it
checkable. See S3.

## 6. Final pass — nothing else blocking

- The `v8.1.0` allow-list provenance (24 names from the runner's warning, with run and job ids
  in a comment) is sound and the stated false-positive/false-negative costs are honest; the
  "no `github-actions` dependabot ecosystem, so the staleness window is the bump commit" claim
  matches the repository.
- §D3's three-file disjointness against APRAS-119 and APRAS-121 holds; result 12 pins the
  unmodified files.
- The both-spellings assertion is real: `ci.yml` uses `- name:` + `uses:`, `migrate.yml` uses a
  bare `- uses:`. Confirmed in the tree.
- Language is English throughout. Scope is one PR (four workflow blocks, one new test module,
  one audit doc, one `AGENTS.md` paragraph) — not a `NEEDS_SPLIT` candidate.

---

## Blocking Findings

- **§D1 and expected result 1 impose a key order on a file this task is forbidden to write,
  and APRAS-121 does not specify that order.** Result 1 requires `version:` to be the *first*
  `with:` key on every derived `setup-uv` step, including `requirements-export.yml`'s if
  APRAS-121 landed first, while §Files touched and §Out of Scope forbid editing that file.
  `docs/tasks/APRAS-121-spec.md` specifies that step's keys but never their order, so a
  correct implementation of both specs can fail result 1 with no legal fix available. §Files
  touched also defines that step as "already compliant (same literal, `checksum:` declared)",
  contradicting §D1's order requirement, and no committed assertion covers key order at all.
- **§D6 says "13 rows" where result 9 says 12, and result 9's `12` is a hard-coded literal
  resting on a premise APRAS-121 does not guarantee.** One row per ref plus "adds no new ref"
  is 12 rows, not 13 — the parenthesis contradicts itself and result 9. Separately,
  APRAS-121's `requirements-export.yml` needs an `actions/checkout` whose ref that spec never
  pins, and this repository already carries `@v6`, `@v4` and `@8e8c483`; if it is not `@v6`
  the landing tree has 13 distinct refs and result 9 fails a correct implementation — the same
  defect as round 1's "(4 as committed)". Derive the ref count from the tree the way the step
  count now is.

## Suggestions

- **S1.** Reword §D1's second justification to the precise claim. `backend-lint`,
  `backend-migrations` and `migrate.yml` run `uv sync --all-groups` with **no
  `--frozen`/`--locked`**, so a newer uv there may re-lock and install something the
  `--frozen` export can never surface; in the ordinary fresh-lock case the uv version only
  affects *reading* the lock. "`backend/uv.lock` is resolved by uv" as written overstates it,
  and the precise version is the stronger argument. Worth adding that APRAS-121's
  `uv lock --check` lands only in `Backend Tests`, so the other three jobs keep an ungated
  non-frozen `uv sync`.
- **S2.** Close the post-hoc gap on production cheaply: `ci.yml` already declares
  `workflow_dispatch`, so a dispatched CI run on the pin commit *before* it lands on `master`
  would observe `Backend Tests`, `Backend Migration Tests (Postgres)` and `Backend Lint (ruff)`
  green on 0.12.19 while `migrate.yml` (which has no `workflow_dispatch` and no `paths:`
  filter, and fires on every push to `master`) has not yet run against production. Recording
  that pre-landing run id alongside the after-state would make the backwards pin verified
  rather than merely witnessed.
- **S3.** Have §D3.4 and result 7 name the shared entry point: the fixture test and the
  real-tree scan must call the same text → steps parser, so a later refactor cannot satisfy the
  fixture through a separate helper while the file-reading path drifts.
- **S4.** Result 3 is satisfiable by a re-run of a job that failed on its first attempt, which
  §D4's "not a flake to re-run away" forbids in prose only. Requiring the recorded conclusion
  to be from `run_attempt` 1 would make that mechanical.
- **S5.** §D6's table gives the `setup-uv` row's `with:` keys as `enable-cache`,
  `pyproject-file` — the **pre-fix** state, while the audit document lands *after* the fix,
  where the keys are `version`, `enable-cache` (plus `checksum` on APRAS-121's step). Say which
  state the inventory records, or give both.
