# APRAS-122 — spec review, round 4 (findings-only re-review)

Spec: `/Users/heitor/workspace/apras/docs/tasks/APRAS-122-spec.md`
Tree: `master` @ `2cb0d48`. Task record: `status: spec_review`, `spec_iterations: 3`, no `parent`.

VERDICT: NEEDS_REVISION

## Scope of this round

Round 3 returned one blocking finding: result 4's escape branch was unconditioned,
and §D4's justification for having an escape at all rested on the false premise
that `workflow_dispatch` needs something the operator's branch policy forbids.

The second half of that finding is **fully resolved**. §D4 now states the premise
correction outright ("the policy forbids a *pull request* … `workflow_dispatch`
needs only a **pushed ref** — no PR"), names the four verified facts at `2cb0d48`,
and specifies the five-step procedure (throwaway branch, `gh workflow run ci.yml
--ref <branch>`, read three conclusions, fast-forward, delete). I re-checked the
two workflow facts I needed for the procedure's shape rather than its premise:
`migrate.yml` has `on: push` only and its job is literally named `Run DB
Migrations` (l.9); `ci.yml`'s job names `Backend Tests` (l.19), `Backend Migration
Tests (Postgres)` (l.91), `Backend Lint (ruff)` (l.180) and the three `setup-uv`
lines 45/135/188 all match what the results quote. No name or line number in the
spec is wrong.

The first half — the escape's gate — is **not resolved**, for one specific and
narrow reason, below.

## Blocking Findings

- **The escape's "recorded operator refusal" lives only in a document the
  implementer writes, so QA still cannot check it, and no round-3 defect is
  closed by moving self-certified prose from result 4 into the audit file.**
  Result 4's second branch passes when "the audit document quotes a **recorded
  operator refusal of the throwaway ref**, with the date it was given, under a
  heading naming the post-hoc risk". Traced as QA must trace it — holding the
  results list and nothing else — every one of those conjuncts is satisfied by
  text the implementing agent types into `docs/tasks/APRAS-122-action-audit.md`
  in the same commit that skips the dispatch. There is no second place the
  refusal has to exist, so there is nothing for the quote to be checked
  *against*: the escape remains selectable at will, exactly as in round 3, with
  a longer required sentence. That is the difference from APRAS-121's result 9,
  which the round-3 finding named as the shape to copy: `gh secret list` is
  re-derivable by QA independently of anything the implementer wrote.

  The anchor this spec needs does exist, and it is the one the spec already
  gestures at. Meridian tasks carry a `questions` array (schema
  `/Users/heitor/.claude/plugins/cache/meridian/meridian/0.4.2/references/schema.md`,
  "The questions array"): one entry per exchange, with `by`, `question`,
  `answer` and `answered_at`, where an operator refusal is **operator-authored
  text with a server-side timestamp**, outside the implementer's authorship.
  Result 4 should require the quoted refusal to be the text of a named
  `questions` entry on APRAS-122 — entry `id`, the `by`/`answer` text quoted
  verbatim, and `answered_at` as the date — so QA compares the audit document's
  quote against the task record and the branch is binary: the entry exists and
  refuses, or the hard gate applies.

  Two facts make this blocking rather than pedantic at round 4. First,
  APRAS-122's `questions` array is **empty today**, so the spec's own sentence
  "The question has been put to the operator and no answer had been received
  when this spec was written" is not corroborated anywhere a reader or QA can
  look — the escape is currently not merely uncheckable but un-anchored.
  Second, this escape is the only thing standing between the task and the
  outcome §D4 itself calls the most exposed in the repository: the first run of
  `alembic upgrade head` against production on a uv version nothing in this
  repository has ever run.

  The fix is one clause in §D4 and the same clause in result 4. Nothing else in
  the spec moves.

## Judged on the merits, as asked

### 1. Is the gate hard? (see the blocking finding)

The *default* branch is now genuinely hard, and well built: result 4 states
"this result passes in exactly one of two ways and in no other", requires the
dispatched run's id, requires all three conclusions at `success`, requires the
run to have started before the pin reached `master`, and closes with "A missing
dispatched run while no such refusal is recorded is a failure, not an
outstanding item." Held against only the results list, a QA agent can execute
that branch end to end with `gh run view`. The defect is confined to the second
branch's anchoring.

### 2. The `head_sha` equality requirement

Sound, and the stated procedure does produce the equality.

- Step 4's "fast-forward … no amend, no rebase, no squash" preserves the commit
  object, so the sha `master` ends up at is the sha the dispatched run reported
  as `head_sha`.
- The operator's actual landing path, `git push origin <sha>:master` from a
  worktree, **preserves it too**: that pushes the existing commit object by its
  own sha and moves the remote ref to it; it creates no new object and no merge
  commit. It is in fact the strictest possible form of step 4 — it cannot
  silently become a merge or a rebase the way `git merge` into a stale local
  `master` could.
- The one case that breaks the equality is `master` advancing between the
  dispatch and the landing, which makes the fast-forward impossible. The spec's
  no-rebase clause plus the recorded-equality requirement makes that
  **self-enforcing rather than a hole**: any reconciliation that changes the sha
  makes result 4's two recorded values differ, and the result fails. A new
  dispatch on the new commit is then the only way through. Worth saying in the
  spec, but it is a suggestion, not a gap in the gate.
- `gh run view <run_id> --json headSha` is the right source and is readable by
  QA after the fact, including after the throwaway branch is deleted (step 5),
  since run records survive ref deletion.

### 3. Result 12's out-of-round edit — the right call, keep it

The previous claim string required `AGENTS.md` to commit the sentence "one uv
resolves `backend/uv.lock` one way", which is precisely the proposition §D1
labels "**reasoned, not observed: it is unmeasured**" and strips of any expected
result. Committing it as an asserted string in `AGENTS.md`, enforced by a test,
would have made the repository's own convention file state as settled fact a
claim the spec that introduced it declines to stand behind — and the test would
have locked it in.

The replacement, "one uv version in CI is one thing to reason about", is honest:
it is a statement about the maintenance surface, not about resolver behaviour,
and it is true independently of the unmeasured hypothesis. Result 12 stays
checkable — the strings are literal, and the module asserts their presence in
`AGENTS.md`, unchanged in mechanism. The parenthetical "the claim strings assert
those two reasons only, not the unmeasured re-resolution hypothesis of §D1" is
the clarification that makes the result unambiguous about what must *not* appear.

Flagging it rather than hiding it was also correct, and I would not revert it.
One small wording note (non-blocking): §D1's structure is "argument one carries
the decision on its own", where argument one is the literal-comparing agreement
assertion; result 12's second reason is a corollary of argument one rather than a
third argument, so "those two reasons" reads as two independent arguments where
§D1 has one plus a restatement. Harmless for checkability.

### 4. Whole-spec pass

No other blocking issue. Spot checks that held:

- Every line number, job name and run/job id the results quote matches the tree
  and the quoted log.
- Results 1, 8 and 10 keep every count derived (`grep -c` over the tree, 4-or-5,
  12-or-13) with no literal asserted, which is what keeps the spec correct under
  either APRAS-121 landing order.
- §D3's four anti-vacuity assertions, including the shared `text → steps` entry
  point behind both the fixture and the real-tree scan, remain the strongest part
  of the spec: they close the vacuous-pass path a text parser otherwise leaves
  open.
- §D1's ownership split with APRAS-121 is stated in both landing orders and
  result 13 pins the files that must stay unmodified, so the three concurrent
  tasks remain file-disjoint.
- The spec is in English throughout.

## Suggestions

- Add one sentence to §D4 step 4: if `master` has advanced and the fast-forward
  is no longer possible, the dispatch is repeated on the new commit — the sha
  equality is not to be reconciled by rebasing. This makes explicit what the
  equality requirement already enforces implicitly, and matches the operator's
  `git push origin <sha>:master` landing path.
- §D4 could name `git push origin <sha>:master` as the concrete form of step 4,
  since that is how these commits are actually landed here and it satisfies
  "no amend, no rebase, no squash" by construction.
- Result 12: consider "for one reason, with one consequence" phrasing rather than
  "those two reasons", to match §D1's one-argument-carries-it structure.
