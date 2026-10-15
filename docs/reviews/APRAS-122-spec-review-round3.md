# APRAS-122 — spec review, round 3 (findings-only re-review)

Spec: `docs/tasks/APRAS-122-spec.md`
Tree: `master` at `2cb0d48`
Mode: findings-only. Round 2's two blocking findings, plus the four points the
dispatcher asked to be judged, plus a bounded consistency pass over the sections
the generator changed to fix them.

VERDICT: NEEDS_REVISION

---

## Round 2 finding 1 — key order imposed on a file this task may not write

**Resolved.**

`§D1` now says, in as many words, "What must agree is the **`version:`
literal**, nothing else: the pin's correctness never depended on byte identity.
**No key order is required or asserted anywhere.**" and hands
`requirements-export.yml`'s key order to APRAS-121 "in both directions — this
task neither requires nor changes it". Result 1 carries the matching clause:
"**Key order within `with:` is not a criterion for any step**, here or in
`requirements-export.yml`: only the presence and value of `version:` are
checked." `§Files touched` says the same ("in any key order, which is
APRAS-121's to choose").

I checked that nothing else still depends on an order, and that byte-identity
has not survived as an unstated assumption:

- every remaining occurrence of "byte"/"identical" in APRAS-122 is either the
  disclaimer above (l.74–75) or the unrelated statement that the *export's
  bytes* are a uv-version artefact (l.106);
- in APRAS-121, every "byte-identical"/"byte for byte" is about
  `backend/requirements.txt` regeneration, not about workflow text;
- APRAS-121's agreement test is located **by job**, not by position: "it reads
  the `version:` input of the **`setup-uv` step of the `backend` job** in
  `ci.yml`" (l.144–147). Nothing in it can be broken by key order;
- APRAS-122's own assertions are presence/value and set-membership
  (`version:` present and equal, `with:` non-empty and containing
  `enable-cache`, keys ⊆ allow-list). None is order-sensitive;
- `§D1` keeps "`version:` is placed first" only as an explicitly
  consequence-free style note ("no expected result and no committed assertion
  behind it"), which is the correct way to retain it.

No incoherence found.

## Round 2 finding 2 — "13 rows" vs result 9's hard-coded 12

**Resolved.** `§D6` now states "**The row set is derived from the tree at
landing time, one row per distinct ref, and no count is hard-coded**", presents
12 as "an **illustration of today's tree, not as the criterion**", and names the
unpinned `actions/checkout` ref in APRAS-121 as exactly why 12-or-13 is
admissible. Result 9 matches: "either outcome satisfies this result".

Measured against the tree at `2cb0d48`:

```
8 actions/checkout@v6        7 create-github-app-token@29824e6   5 run-gemini-cli@v0
4 astral-sh/setup-uv@v8.1.0  4 actions/setup-node@v6             4 github-script@ed59741
2 actions/upload-artifact@v7 2 actions/download-artifact@v8      2 actions/checkout@v4
1 sonarqube-scan-action@v7   1 github-script@60a0d83             1 actions/checkout@8e8c483
```

12 distinct refs across 9 workflow files, three distinct `actions/checkout`
refs. The table's per-file occurrence counts also reconcile
(`checkout@v6`: ci×5 + migrate + release×2 = 8; `setup-node@v6`: ci + release×3
= 4). The table is accurate as an illustration and is no longer load-bearing.

---

## 1. The pre-landing gate (result 4) — the escape makes the gate decorative

This is the one blocking finding. Verbatim target, result 4:

> **or** a one-line statement of why no such dispatched run was available, under
> a heading naming the post-hoc risk it leaves

Two problems, and they compound.

**(a) The second branch is unconditioned, so the result cannot fail.** Nothing
constrains *when* the escape is admissible. The implementer selects the branch,
writes one sentence whose truth QA cannot check, and the result passes. Contrast
the same construction done correctly one spec over: APRAS-121's result 9 is also
an either/or, but its escape branch is gated on an **externally observable**
fact — "`gh secret list` for this repository contains no
`REQUIREMENTS_EXPORT_TOKEN`" — and it then says outright "A missing
demonstration while the secret *does* exist is a failure, not an outstanding
item." APRAS-122's escape has no such condition and no such sentence. Under the
`expected_results` gate this reviewer applies, the result is not mechanically
verifiable: a criterion satisfiable at will by prose is documentation, not a
gate. Since this is the only thing standing between a pinned-backwards uv and a
production `alembic upgrade head`, saying so plainly: as written, the gate is
decorative.

**(b) The stated reason for the escape rests on a false premise.** `§D4` says
the dispatched run "needs a ref the dispatch can name, which the operator's
branch policy may not permit for this task". The policy on record is *no PR for
local pipeline work* — land on `master`, branch-and-PR only for cloud
dispatches. A `workflow_dispatch` needs a **pushed ref**, not a pull request.
The satisfiable hard path, verified against the tree:

- `ci.yml` declares `workflow_dispatch:` (l.12) and its own comment already
  frames it as the way to get a run "on any ref but `master`";
- `workflow_dispatch` is not subject to the `branches: [ master ]` filters on
  `push`/`pull_request`, and `ci.yml` has no branch-conditional `if:` on any
  job (the only `if:` in the file is `if: always()` on the artefact upload at
  l.169), so `Backend Tests`, `Backend Migration Tests (Postgres)` and
  `Backend Lint (ruff)` all run on a dispatched non-`master` ref;
- `migrate.yml` has no `workflow_dispatch` and triggers only on
  `push: branches: [ master ]`, so pushing a throwaway ref touches production
  not at all.

So: push the pin commit to a throwaway remote branch, no PR; `gh workflow run
ci.yml --ref <branch>`; read the three conclusions; fast-forward `master` to
that same commit; delete the branch. The fourth criterion the generator feared
would be unsatisfiable is satisfiable, and under the policy as written.

**What would make this pass review.** Either of:

1. make the gate hard — require the dispatched run and name the throwaway-ref
   procedure above, with the additional requirement that the dispatched run's
   head sha **equal** the landing commit sha (otherwise the evidence is about a
   different tree than the one that reaches production); or
2. keep the either/or, but gate the escape on something a third party can
   check — e.g. the escape is admissible only when the task records the
   operator's explicit refusal of a throwaway ref (a recorded answer, by date),
   and add APRAS-121's closing sentence in the matching shape: *a missing
   dispatched run while a throwaway ref was permitted is a failure, not an
   outstanding item.*

The fail-closed argument in `§D4` is correct as far as it goes (a failing `uv
sync` precedes `alembic`, and a failed `alembic upgrade head` leaves the schema
at the last applied revision), so the residual exposure is a red production
migration run rather than a corrupted schema. That is why this is a
`NEEDS_REVISION` on the criterion's shape and not an architectural objection to
the plan.

## 2. Leftovers from dropping key order

Covered above: none. Both specs are consistent on this point, and no assertion
in either is order-sensitive.

## 3. The reworded `uv.lock` justification

Both factual halves verified against the tree.

- **`uv sync` without `--frozen`/`--locked`**: `ci.yml` l.56 (`backend`),
  l.146 (`backend-migrations`), the `backend-lint` job, and `migrate.yml`
  (`- run: cd backend && uv sync --all-groups`) each run bare
  `uv sync --all-groups`. True as stated.
- **Lock header**: `backend/uv.lock` begins `version = 1`, `revision = 3`,
  `requires-python = ">=3.13"`. True as stated. Local uv is
  `0.12.19 (Homebrew 2026-09-24)`, matching the pin.

What remains unverified is the *inference*, not the facts: whether a newer uv
(0.12.21) would actually re-resolve in-job on **this** lock. That cannot be
measured here — the available moves are forbidden (`uv sync`) or unavailable
(no 0.12.21 locally). The spec no longer rests anything on it: it says "**may**
re-resolve", concedes "In the ordinary fresh-lock case the uv version only
affects *reading* an already-resolved lock and changes nothing", and states that
"argument one carries the decision on its own". That is honest hedging on a
secondary argument, so it is not blocking. One nuance worth noting without
blocking: `uv lock --check` (APRAS-121, `Backend Tests`) gates the
*stale-against-`pyproject.toml`* branch only, not the lock-format branch, and
the spec's phrasing invites the reading that it gates both. Also, until
APRAS-121 lands, `Backend Tests` has the same ungated non-frozen `uv sync` as
the other three — which only strengthens the argument, so no contradiction.

## 4. `run_attempt` 1

**Checkable, and the right default.** The field is in the payload the result
already names — `gh api repos/:owner/:repo/actions/runs/<id>/jobs` returns
`run_attempt` per job (confirmed on run `36924174723`, which also reconciles the
spec's "before" evidence: jobs `110577272457` Backend Lint, `110577272946`
Backend Tests, `110577272967` Backend Migration Tests, all `success`,
`attempt=1`). `…/attempts/1/jobs` exists as a second route. QA can verify this
from the recorded command.

The rigidity the dispatcher flags is real: a genuine infrastructure flake on
attempt 1 makes the result unsatisfiable without a new landing commit. I judge
that acceptable and deliberate — the whole purpose of the result is to stop a
0.12.19 failure being re-run away, and "push a new commit" is an available, more
honest escape than a green attempt 2. See the suggestion below for a narrow
relaxation that does not reopen flake-washing.

## 5. Final pass

Nothing else blocking. English throughout. Scope is one PR (four workflow step
edits, one new test module, one audit doc, one `AGENTS.md` paragraph) and the
`NEEDS_SPLIT` criteria do not apply. The anti-vacuity set in `§D3`, the
ref-keyed allow-list with run-log provenance, the audit's per-row method split
(`action.yml` for every row but `setup-uv`), and the explicit
`migrate.yml`-is-covered statement all remain sound and verifiable. The
disjoint-file coexistence story with APRAS-119 and APRAS-121 still holds.

## Suggestions (non-blocking)

- Result 4, even in its preferred branch, does not require the dispatched run's
  head sha to equal the landing commit sha. Add that equality; "the pin commit"
  implies it but QA reads the sentence, not the implication.
- `§D1`'s second argument would survive the next round better with one clause
  marking it unmeasured — e.g. "not observed on today's lock; stated as a
  possibility the pin forecloses" — since the re-resolution path cannot be
  demonstrated under this task's constraints.
- `§D1` says `uv lock --check` leaves "those three jobs" with an ungated
  non-frozen `uv sync`. Note that it gates only the staleness branch, not the
  lock-format branch, so `Backend Tests` is not fully gated either.
- A narrow relaxation of `run_attempt` 1 that keeps the gate honest: allow a
  later attempt **only** when attempt 1's conclusion is also recorded, with the
  failing job, step and log excerpt, and an explicit statement of why the
  failure is not uv-related. Silence about attempt 1 stays inadmissible.
