# APRAS-122 — spec review, round 5 (findings-only, final round before cap)

VERDICT: APPROVED

Spec reviewed: `/Users/heitor/workspace/apras/docs/tasks/APRAS-122-spec.md`
Task record: `/Users/heitor/workspace/apras/.meridian/tasks.jsonl` (APRAS-122) and
`/Users/heitor/workspace/apras/.meridian/tasks/APRAS-122.json` (expected_results)

## Scope of this round

Findings-only. Round 4 returned a single blocking finding: the escape from the
pre-landing dispatch gate was anchored only on prose the implementer writes, so
QA had nothing to compare the quoted refusal against. I verified (a) that the
finding is resolved, and (b) a consistency pass limited to the sections that
moved to resolve it (§D4's escape paragraphs, §D4 step 4, result 4). I did not
re-apply the full checklist to untouched sections.

Per the dispatch, I did not re-derive that the spec cites `q-1790947582472-122`
twice, mentions `answered_at` three times, or that the entry exists unanswered.
I read the sections rather than grepping for expected sentences.

## 1. Is the escape now binary for QA?

Yes.

Traced holding only `expected_results` (the detail file, which I read and which
matches the spec file verbatim), result 4 now passes in exactly one of two ways:

- Branch 1: a `workflow_dispatch` run of `ci.yml` on a non-`master` ref, started
  before landing, three named jobs at `conclusion: success`, and its `head_sha`
  recorded equal to the sha `master` landed. Every term is re-derivable with
  `gh`, independent of the implementer's prose.
- Branch 2: the audit document quotes **verbatim the `answer` of `questions`
  entry `q-1790947582472-122` on task APRAS-122**, cites that entry's `id` and
  `answered_at`, and "the quote matching the task record".

The anchor is outside the diff. I confirmed the state of the record:
`questions[0]` is `{"id": "q-1790947582472-122", "by": "Agent", "answer": "",
"created_at": "2026-10-02T13:26:22.000Z"}` — no `answered_at` key at all. So
today an implementer **cannot** satisfy branch 2: result 4 states that an empty
or absent `answer` is not a refusal, and that a missing dispatched run while
that entry carries no refusal is a failure, not an outstanding item. The gate is
therefore currently mandatory, which is the intended state. That is the round-4
defect closed: there is now a second place the refusal must exist, and it is a
place the implementing commit does not contain.

**Where QA reads it.** Result 4 names the record completely — board task id,
entry `id`, field `answer`, field `answered_at` — and "the task record" has
exactly one canonical location, described in the schema reference QA is given:
`<project>/.meridian/tasks.jsonl` (`questions` travels on the task line; only
`expected_results` lives in the per-id detail file). I checked both access
paths: the local Meridian API was not listening on 7421 during this review, and
the jsonl read succeeded, so a QA agent has a working read path even with the
server down. This is weaker in *form* than branch 1 and than APRAS-121's
`gh secret list` — those name a command, branch 2 names a record — but it is not
ambiguous: there is no second candidate location, no field to guess, and the
comparison ("quote matches `answer`") is a string equality. I judged this not to
be a repeat of the previous rounds' gap, which was the absence of any external
referent, not the absence of a command. See suggestion 1 for the cheap
improvement.

## 2. The new §D4 read-only rule — enforceable or merely stated?

Merely stated, and I accept it anyway. Honest assessment:

- Nothing in the tooling prevents an implementing agent from PUTting a
  `questions` entry's `answer`. The schema has no per-answer authorship field —
  `by` describes who *asked* (`"Agent"` here) — so no stronger anchor exists in
  the data model. A reviewer cannot require non-repudiation that the schema
  cannot express.
- The residual risk is bounded by who notices. If an implementer fabricated a
  refusal, the forged `answer` would appear on the operator's own card, under a
  question the operator never answered — detectable by exactly the one party who
  can know the truth, and detectable *without* reading the diff. Contrast round
  4, where the fabrication lived inside a document only the fabricating commit
  contained.
- It also fails closed in the direction that matters: the entry is empty, so the
  default path today is the dispatched run, and any deviation requires a
  deliberate, visible write to task state that the implementer's own dispatch
  contract forbids.

So the rule is a convention, not a lock — but the check it enables is binary and
externally visible, which is what round 4 asked for. Noted as suggestion 2
rather than a finding, because no available change to this spec can make it a
lock.

## 3. Step 4's `git push origin <sha>:master` reasoning

Holds, with one narrow wording exception that I treat as non-blocking.

Sound part: `git push origin <sha>:master` transmits the existing commit object
by its own sha and creates no new object, so the landed sha is bit-for-bit the
dispatched sha. If `master` has advanced, the push is rejected as a
non-fast-forward; any amend, rebase or squash reconciliation produces a
different sha, result 4's two recorded values then differ, and the result fails
rather than passing on stale evidence. That chain is correct.

The exception: a **merge** reconciliation does not change the pin commit's sha —
the pin commit still lands on `master` unchanged, while `master`'s *tip* becomes
a new merge commit. §D4 step 4 forbids this by saying "fast-forward `master` to
that same commit", so the compliant path is unaffected. But result 4's phrase
"the sha `master` landed" admits a reading under which the pin commit's sha is
what is recorded, and the equality then holds even though the tree `migrate.yml`
ran against is the merge tip, which no dispatched run gated. I did not make this
blocking because: (a) §D4 explicitly requires a fast-forward, so the reading
contradicts the spec's own procedure; (b) results 2, 3 and 5 still require the
landing commit's CI run and the `migrate.yml` run to be green and to log
`0.12.19`, so the final tree is covered post-hoc; and (c) the fix is one phrase,
offered as suggestion 3, and is not worth burning the task's last round.

## 4. Whole-spec pass

Facts I re-checked on the tree at `2cb0d48` (cheap, and load-bearing for the
gate):

- `ci.yml` declares `workflow_dispatch:` at line 12, with the comment the spec
  quotes; its only `if:` is `if: always()` at line 169, so no uv-using job is
  branch-conditional.
- `migrate.yml` declares `push: branches: [ master ]` and **no**
  `workflow_dispatch`, so a throwaway ref cannot reach production. It holds
  `POSTGRES_URL_NON_POOLING` and runs `alembic upgrade head`, as §D4 says.
- Four `setup-uv@v8.1.0` steps, all four passing `pyproject-file:`
  (`ci.yml` 45/135/188, `migrate.yml` 17), matching §D6's table and result 1.
- The `expected_results` detail file is in sync with the spec's Expected Results
  section, word for word — no drift between the two documents.

Everything else (§D1 ownership split with APRAS-121, §D2 allow-list provenance,
§D3's four anti-vacuity assertions plus the shared parse entry point, §D5's bump
ritual and its `AGENTS.md` claim strings, §D6's derived row set, the Out of
Scope list) is unchanged from round 4, where it was not blocking. All 14 results
are mechanically verifiable, all are in English, and all are covered by the
spec. Scope remains one PR: four workflow steps, one new test module, one audit
document, one `AGENTS.md` paragraph.

## Blocking Findings

None.

## Suggestions

- Result 4 names the record the refusal must live in but not a read path. One
  clause — "read from the task's `questions` array in
  `<project>/.meridian/tasks.jsonl` (or `GET /api/tasks/APRAS-122?project=apras`)"
  — would give branch 2 the same shape as branch 1's `gh run view … --json
  headSha`. Not blocking: the record is unambiguous and I confirmed the jsonl
  path works with the API down.
- The `questions` array is writable by any agent and the schema carries no
  per-answer authorship, so §D4's "the implementer reads but never writes
  `questions`" is a convention. If the orchestrator wants it harder, the lever
  is outside this spec: the operator confirming on dispatch that the entry was
  still unanswered, or the `work` skill snapshotting the entry before the
  developer runs.
- In result 4, "the sha `master` landed" would be tighter as "the sha at the tip
  of `master` after the push", which closes the merge-commit reading described
  in section 3 above.
