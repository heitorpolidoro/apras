# APRAS-119 — Find why the backend test job hangs after the tests have already passed

## Scope

An **investigation** into the recorded `Backend Tests` hangs — a set that is
**derived from a stated query, never from a list carried in this spec** (§1a) —
plus the small amount of CI/test-harness work that makes the investigation's
outcome durable either way.

Covers: deriving the occurrence set with a job-keyed census over every
non-success `ci.yml` run (§1a); reading the evidence for each occurrence (§1);
testing each named suspect and recording a verdict with evidence (§3, §4, §4a);
one local reproduction attempt (§5); closing the remaining blind spot in the
instrumentation (the **post-test-loop window** — everything after the last test:
the coverage write, the summaries, `sessionfinish`, and interpreter shutdown —
the part of the recorded signature that `68f249a` still cannot produce a stack
for, and the only backstop that works from inside the process) (§6); amending
`ci.yml`'s pytest step if §4a shows the wrapper's signals never reach pytest;
and giving `backend-lint`, `frontend` and `sonarcloud` the `timeout-minutes`
they lack (§7).

Does **not** cover: re-specifying anything `68f249a` already landed (see
"Evidence the next hang now produces"); the `sqlmodel` 0.0.47 naive-datetime
failure (that is APRAS-120; PR #36's 30m19s run and run `36866106559`'s 30m08s
exit-124 run are explicitly **not** occurrences of this hang); and any
speculative rewrite of a fixture that the investigation has not first shown to
be implicated.

**Two prior rounds of review each found the occurrence set larger than the spec
asserted it was.** The lesson is structural, and this revision builds it in:
**this spec states no occurrence count as fact and carries no frozen list.** It
states a query, a detector, and the measurement that query returned at a named
timestamp as a **floor** (§1a). Every downstream reading — §2's framing, §4's
verdicts, the `## Not found` branch — is derived from the set the implementer
measures when they run the query, not from the numbers printed here.

**The subject has recurred with `68f249a` in the tree**, and the step-level
`timeout --signal=INT --kill-after=60s 30m` did not end the step at 30m on
those runs. So the question is no longer only **why the process wedges** but
**why the wedge is not killable**, and §4a adds that as a suspect with a probe
that can be run today. A narrowing without a root cause is still a *completed*
task with verifiable output; the last expected result stays split accordingly.

## Approach

### Behavior

**1a. The occurrence set is derived, not enumerated.** This is the first step of
the task and everything else is downstream of it.

**The query.** For every `ci.yml` run since **2026-08-01** whose conclusion is
**not** `success`:

```
gh run list --workflow=ci.yml --limit 300 --created '>=2026-08-01' \
  --json databaseId,conclusion,headBranch,headSha,createdAt,event
gh api 'repos/:owner/:repo/actions/runs/<id>/jobs?filter=all&per_page=100'
```

Three properties of that query are load-bearing and must not be narrowed:

- **It covers `failure` runs as well as `cancelled` ones, on both sides of
  `68f249a`.** A run whose `Backend Tests` job is cancelled by
  `timeout-minutes` still concludes `failure` at run level, so a run-keyed
  census is blind to this hang. Pre-fix `failure` runs are *also* in the blind
  spot, which is why the window opens at 2026-08-01 and not at `68f249a`:
  runs `36633293755` and `36633543003` both concluded `failure` **before**
  `68f249a` with a cancelled `Backend Tests` job.
- **`filter=all` is required.** Without it the API returns only the latest
  attempt, and run `36638362231` has two attempts whose `Backend Tests` jobs
  (`109644454563`, `109661776896`) are each a separate occurrence. A census
  without `filter=all` silently under-counts re-run runs.
- **The detector is a step that did not *complete*, not a step that is
  `null`.** An occurrence is a `Backend Tests` job whose `conclusion` is
  `cancelled` **and** whose `Run tests with coverage` step conclusion is **not
  `success` and not `failure`** — i.e. `null` *or* `cancelled`. Job
  `109628456192`'s step carries `conclusion: cancelled`; a `null`-only detector
  classifies it as an ordinary failure and loses it.

**What the query returned.** Run as of `cd8de18` (2026-10-01 17:24Z) over 184
runs (84 `success`, 90 `failure`, 10 `cancelled`), it returned **15
occurrences**, spanning **8 distinct refs** including **three pushes to
`master`**:

| job | run | run concl. | span | step concl. | branch | created |
|---|---|---|---|---|---|---|
| `110405490008` | `36873076533` | failure | 55m01s | null | dependabot 2c54 | 2026-10-01 14:01Z |
| `110014916546` | `36752659497` | failure | 55m00s | null | dependabot 2c54 | 2026-09-30 17:37Z |
| `109926009179` | `36726903030` | cancelled | 55m00s | null | **master** `eb4b67c4` | 2026-09-30 14:09Z |
| `109712407577` | `36659990810` | cancelled | 55m00s | null | apras-117 | 2026-09-30 02:28Z |
| `109702819710` | `36656817008` | cancelled | 55m00s | null | apras-117 | 2026-09-30 01:48Z |
| `109690533619` | `36652795228` | cancelled | 55m00s | null | apras-117 | 2026-09-30 00:58Z |
| `109682771349` | `36650344899` | cancelled | 55m00s | null | apras-117 | 2026-09-30 00:27Z |
| `109661776896` | `36638362231` | cancelled | 55m00s | null | apras-118 `7cbe5c52` | 2026-09-29 23:10Z |
| `109644454563` | `36638362231` | cancelled | 55m00s | null | apras-118 `7cbe5c52` | 2026-09-29 22:14Z |
| `109628456192` | `36633543003` | failure | 45m58s | **cancelled** | dependabot 2ed8 | 2026-09-29 21:29Z |
| `109627607918` | `36633304578` | cancelled | 55m01s | null | types/node-26.6.3 | 2026-09-29 21:27Z |
| `109627574082` | `36633293755` | failure | 55m00s | null | jsdom-30.1.1 | 2026-09-29 21:27Z |
| `109627479498` | `36633264240` | cancelled | 55m00s | null | imgbot | 2026-09-29 21:26Z |
| `109515466160` | `36600250329` | cancelled | 55m01s | null | **master** `37e3f608` | 2026-09-29 16:47Z |
| `108767062588` | `36370971185` | cancelled | 365m00s | null | **master** `e2ccb45b` | 2026-09-28 02:45Z |

**How that table is to be used.** It is a **floor and a cross-check, not the
set.** The implementer re-runs the query, reports the set it returns **as of
their own census timestamp**, and states that timestamp. If their set is
smaller than 15, the census is wrong and must be fixed before anything is
derived from it. New rows are expected: the window is open-ended and runs
accrue hourly.

Two facts the census already settles, so no round is spent re-deriving them:

- **All ten run-level `cancelled` runs in the window are occurrences.** Not one
  is a superseded push. Any instruction to classify them as `superseded push`
  or `other` is withdrawn.
- **Of the 15, exactly two are post-`68f249a`** (which landed 2026-09-30
  16:40Z): jobs `110014916546` and `110405490008`. `git merge-base
  --is-ancestor 68f249a <sha>` is **false** for every other occurrence's sha.
  Those two are `pull_request` runs on
  `dependabot/uv/backend/backend-version-updates-2c543e60b5` (PR #42, open
  2026-09-30T17:36:53Z → 2026-10-01T14:33:17Z, ~21 hours).

**1. Evidence, read rather than assumed.** For each occurrence the census
returns, record what the job log and the jobs API do and do not show, via
`gh run view` / `gh api`. The expected answer from the *log* is "nothing: a
cancelled job publishes no logs"; record that as the finding rather than
inferring a phase, and take the phase evidence from the jobs API's per-step
`conclusion`/`completed_at`. Then state, per occurrence, **whether the suite had
finished when the freeze began**, and say "unknown" where the evidence cannot
support an answer — for every occurrence without a published log it cannot, and
"unknown" is the required answer there.

The one occurrence with a published phase reading is run `36370971185` / job
`108767062588` on `e2ccb45b` (**not** "the commit before `13868f7`" — that is
`bd9bd11b`, which has no CI run): tests green in 17m26s, then frozen 0.5 s into
the pytest warnings summary, killed at **365.00 min** by GitHub's six-hour
default. Cite run and job ids for every occurrence, as the table does.

Record, as a separate row and explicitly **not** as an occurrence, run
`36866106559` / job `110381880180` (2026-10-01 13:04Z, PR #42): its step failed
at **30m08s with exit code 124**, the `timeout` wrapper firing exactly as
designed, and its log is published — summary line
`36 skipped, 1 warning, 2299 errors in 1798.11s (0:29:58)`, the errors being
`sqlalchemy.exc.StatementError` on `INSERT INTO tenant`, i.e. APRAS-120's
sqlmodel 0.0.47 naive-datetime fault with the half hour spent formatting
tracebacks. It is cited as **evidence that `68f249a`'s wrapper works when the
process is killable**. Do **not** download that log: it is 31 MB / 359 085
lines. The exit code is verifiable without it —
`gh api repos/:owner/:repo/check-runs/110381880180/annotations` returns
`Process completed with exit code 124.`, and that is the command the findings
document cites.

**1b. The recurrence detector going forward** is the §1a detector, stated once
in the findings document: **a `Backend Tests` job whose conclusion is
`cancelled` and whose pytest step did not complete with `success` or
`failure`** — never "a cancelled run", and never "step conclusion is `null`".
The findings document states that absence of run-level cancellation is not
evidence of absence, and gives the **four** `failure`-concluding occurrences in the
measured set as the proof — jobs `110405490008`, `110014916546`,
`109628456192` and `109627574082`, i.e. the 15 occurrences minus the 11
contributed by the ten run-level `cancelled` runs.

**2. What the measured set does and does not support.** Still eliminated: the
dependency bumps as such (master at `ef44295`, carrying APRAS-116's `anyio`
4.13.0 → 4.14.2, ran green in 7m49s). The spec forbids spending a round
re-measuring that.

Two earlier framings are **withdrawn**, and the investigation must not lean on
either:

- "repetition on a byte-identical backend tree, therefore the runner or the
  image" — the set spans 8 refs, so the identical-tree argument is gone as an
  *argument*;
- "the occurrence set spans two backend trees, one of which was emitting an
  error storm, so the wedge may be **volume-triggered**" — the measured set does
  not support this. Occurrences sit on three `master` pushes, on
  `apras-117` four times in a row, and on three **frontend-only / imgbot**
  refs whose backend tree is unchanged and whose suites emit no error storm.
  **Four** distinct refs wedged within **two and a half minutes** of each other
  on 2026-09-29 — imgbot 21:26:26Z, types/node 21:27:27Z, jsdom 21:27:47Z,
  dependabot 2ed8 21:28:56Z, a 2m30s window of which the first three fall inside
  1m21s. Only one occurrence (`110405490008`, and arguably
  `110014916546`) is on a branch where an error storm is known to exist.

The reading the measured set favours is a **tree-independent fault** — runner,
image, or CI-side resource — because the backend tree, the branch and the
suite's output volume all vary across the set while the signature does not,
and because the 2026-09-29 cluster is a *time* correlation rather than a tree
one. The findings document must state which reading the evidence supports, or
that it cannot discriminate, and must examine the clustering in time (the
2026-09-29 21:26–21:29Z cluster of four, the `apras-117` run of four) as evidence in its
own right. **The `runner-or-image` row in §4 is therefore the row most likely to
move, and `output volume` is demoted to a row the set no longer points at.**

**3. First suspect — the leaked SQLite engine (APRAS-109) — is now a
verification, not an investigation.** `backend/tests/conftest.py`'s `session`
fixture already disposes its engine in a `finally`, and
`test_suite_hygiene.py::test_every_engine_built_in_the_test_tree_is_disposed`
pins that by AST for the whole test tree; both landed in `68f249a`. So the work
here is to **confirm the measurement is gone**: run
`tests/test_project_report.py` (the module that emitted 108
`ResourceWarning: unclosed database`) with `-W error::ResourceWarning` and
record the count. A zero is a suspect *cleared by fix*, and must be reported as
such — "cleared" here does not mean "was never the cause", and the findings
document must not claim the cause was found merely because the leak is gone.
A non-zero is the strongest possible lead and takes priority over everything
else in this spec.

**4. Each remaining suspect gets a verdict with the evidence that produced it.**
Each as *confirmed* / *cleared* / *untestable without a recurrence*, never as a
list of hypotheses. `untestable without a recurrence` is admissible for
**runner-or-image alone**; on any other row it is a finding that the prescribed
probe was not run:

- a **non-daemon thread** keeping the interpreter alive after pytest returns.
  Probe: run the full suite locally and record `pytest_sessionfinish`'s thread
  report verbatim. *Cleared* iff it names no non-daemon thread; any name it
  prints is *confirmed* and takes the lead.
- the **coverage writer** — `--cov=app --cov-report=xml:coverage.xml` plus
  `--cov-fail-under=90`. **Where it actually runs is settled, not assumed:**
  `pytest_cov/plugin.py` does it in a `pytest_runtestloop` **wrapper**, with the
  source comment saying why (*"we need to wrap pytest_runtestloop. by the time
  pytest_sessionfinish runs, it's too late to set testsfailed"*);
  `cov_controller.finish()`, `summary(self.cov_report)` — the `coverage.xml`
  write — and `should_fail_under` all complete **before any
  `pytest_sessionfinish` implementation runs**, and `pytest_terminal_summary`
  only prints. An earlier draft had this backwards and measured an interval the
  coverage write is not in, which cleared the suspect by construction. Probe,
  corrected: time the **whole process**, to exit, with coverage enabled and
  again with `-p no:cov`, *and* separately time the post-test-loop coverage
  phase by comparing `--cov-report=xml:coverage.xml` against
  `--cov=app --cov-report=` on the same tree; record all three numbers.
  *Cleared* iff the coverage phase is bounded and measured in seconds. See §6
  for the window the watchdog covers, which is **not** this one.
- **output volume** — occurrence `108767062588` froze 0.5 s into the warnings
  summary, and a ~2 MB log line has choked a process in this repository's
  history before. §2 **removed** this row's second support: the measured set is
  mostly refs with no error storm, including frontend-only ones. Probe: record
  the suite's warning count (the summary's own tally), the total byte size of
  captured stdout (`uv run pytest … > out.txt; wc -c out.txt`) and the largest
  single line (`awk '{ if (length > m) m = length } END { print m }'`).
  *Cleared* iff no single line exceeds ~1 MB and the total is of the order of a
  few MB.
- the **runner or image**, which no local run can clear, and which §2 now makes
  the leading row rather than the default one. This is the one row for which
  `untestable without a recurrence` is the correct verdict. The findings
  document says what the next occurrence would have to show to confirm it (see
  the decision rule below) and records the measured support it now has: 8 refs,
  three `master` pushes, three frontend-only refs, and a four-ref cluster
  inside two and a half minutes.

**4a. New suspect, created by the measured 30m overshoot: the wedge is not
killable from outside.** On the two post-`68f249a` occurrences the 30m step
wrapper ended nothing: the step started and never completed, and no log was
published — while on job `110381880180`, same branch, same wrapper, the wrapper
fired at 30m08s with exit 124 and a published log. **That contrast is this
section's whole evidentiary basis, and it stands on its own.**

**The job-timeout half of the old "both backstops overshot" claim is
withdrawn.** `timeout-minutes: 45` landed in `62a136c` (2026-09-28 18:43Z), and
every occurrence after it except one has a span of **55m00s or 55m01s** — 45m
plus GitHub's fixed post-cancellation grace. Uniformity that tight across 13
jobs, 7 refs and three days is a **platform constant**, not a backstop being
resisted: the timeout fired on schedule at 45m and the job record closed when
the grace window expired. The single exception confirms it from the other side —
job `109628456192` completed at **45m58s** (2758 s) with its pytest step at
`conclusion: cancelled`, i.e. a job where the cancellation reached the step
promptly and the grace window was not needed. The findings document must state
this interpretation explicitly: **the 55m spans are not evidence of the job
timeout overshooting**, and no conclusion in the document may rest on them as
if they were.

One mechanism for the *step-level* overshoot is worth **testing, not
asserting**: `timeout` signals its direct child, and that child is `uv`, not
pytest. SIGINT and then SIGKILL delivered to `uv` would leave the pytest
grandchild orphaned and running, holding the step's stdout pipe open — and a
step whose output pipe never closes does not complete however the wrapper
exited. That predicts a fix (`exec` into pytest, process-group signalling via
`timeout --foreground`/`setsid` + `kill -- -PGID`, or applying `timeout` inside
the `uv run` invocation).

Probe, locally, with no production code changed. GNU `timeout` is present at
`/opt/homebrew/bin/timeout`, so the probe is runnable:

```
/opt/homebrew/bin/timeout --signal=INT --kill-after=2s 3s \
  uv run python -c "import time; time.sleep(600)" | cat > out.txt
```

Record (i) `timeout`'s exit status and when it returned; (ii) whether a
`python` grandchild is still alive afterwards (`pgrep -f 'time.sleep(600)'`);
(iii) **whether the downstream reader saw EOF**, measured concretely as whether
the `cat` process exited — check with `pgrep -f 'cat > out.txt'` (or the shell's
job status) immediately after `timeout` returns, and record which. Repeat with
the predicted fix shape (e.g. `uv run` replaced by a form that `exec`s, or
`timeout` moved inside). *Confirmed* iff the grandchild survives or `cat` is
still alive in the first form and both are fixed in the second; *cleared* iff
`uv` propagates the signal and the grandchild dies. Kill any survivor.

**The probe runs on darwin against an ubuntu fault.** A `cleared` verdict here
does **not** clear the CI case, and the findings document must say so in those
words: process-group and signal semantics differ, and a local pass is evidence
about `uv`'s signal handling, not about the runner. A `confirmed` verdict is the
stronger result. If confirmed, the containment fix lands in
`.github/workflows/ci.yml` under this task with the probe output as its proof,
and that is the one amendment to `68f249a` this spec permits.

**5. One local reproduction attempt, reported either way.** Full suite under the
CI invocation (`--cov=app --cov-report=xml --junitxml=...`), timed, with the
**armed-window latency** measured separately from the test duration. That
latency is defined as **the §6 arming point → process exit**, not "after the
summary line": arming precedes the warnings summary, the short summary and the
stats, and §4's output-volume suspect is precisely the hypothesis that *those*
are the expensive part.

**The measurement protocol, stated so the two readings are on one clock.** Do
**not** subtract a `time.monotonic()` value from a shell wall clock — its epoch
is arbitrary and the difference is meaningless. Use exactly one of:

- **(preferred, self-contained)** the arming hook stores
  `t0 = time.monotonic()` and a `pytest_unconfigure` hook — or an
  `atexit`-registered callback, which runs later still — takes a second
  `time.monotonic()` reading and prints `t1 - t0` itself. Both readings come
  from the same clock inside the same process, and nothing outside has to be
  correlated.
- **(alternative, cross-process but commensurable)** the arming hook prints
  `time.time()` (epoch seconds, same basis as the shell's), and the invocation
  is wrapped so the shell captures `date +%s.%N` **immediately after the
  process exits**; the difference of those two epoch readings is the latency.

Report it in seconds to two decimals and name which protocol was used. The
local steady state is 5m35s against CI's ~11m, so a negative reproduction
result is the expected one; if it does not reproduce, say so plainly and say
what that implies — a hang confined to the runner is a different investigation
from one that reproduces on a laptop, and §2 already points that way.

**6. The shutdown-window probe.** The gap `68f249a` leaves: `pytest-timeout`
caps *one test*, and the `timeout` wrapper fails the step with whatever was
already printed — neither produces a **stack** for a process wedged after the
last test, which is precisely the recorded signature. Arm a `faulthandler`
watchdog that dumps every thread's stack if the process has not exited within a
bounded grace period after the session ends. Three parameters are load-bearing
and the spec fixes all three:

- **Hook: a `pytest_runtestloop` wrapper in `backend/tests/conftest.py`, armed
  on the way out, registered `trylast` so it is the innermost wrapper.** Not
  `pytest_sessionfinish`, not `pytest_unconfigure`, not `atexit`. `pytest-cov`
  writes `coverage.xml` and evaluates `--cov-fail-under` inside its **own
  `pytest_runtestloop` wrapper**, after the yield, so arming at `sessionfinish`
  would **exclude** the coverage write that §4 names as a suspect. pytest calls
  later-registered hookimpls first, so a plain conftest wrapper would be the
  *outer* one; `@pytest.hookimpl(wrapper=True, trylast=True)` moves it last in
  the call order, i.e. innermost, so its post-yield code runs **first** — after
  the last test, before the coverage write. The armed window is then exactly
  *everything after the last test*: coverage write, `--cov-fail-under`,
  terminal summary, warnings summary, `sessionfinish`, `unconfigure`,
  interpreter shutdown.

  **`wrapper=True` is new-style and the wrapper must `return` the value it
  received from `yield`.** A new-style wrapper that falls off the end makes the
  hook result `None`. It is harmless for `pytest_runtestloop` specifically, but
  the implementation must return the yielded value regardless, and the hygiene
  assertion in §6b is free to pin it.

  **The ordering is already verified empirically** and the prescription stands:
  at the arming point `coverage.xml` did not yet exist, its mtime fell 6 ms
  after the arming timestamp, and `pytest_sessionfinish` saw the file present.
  The implementer reproduces that check — file mtime against the timestamp
  printed at arming, on a full local run — and records it in the findings
  document. If it cannot be reproduced, the fallback is to arm at
  `pytest_sessionfinish` and state **plainly, in both `conftest.py`'s comment
  and the findings document**, that the coverage write lies outside the
  watchdog's window, together with §4's separately measured coverage-phase
  duration as the compensating evidence.
- **Grace period: 120 seconds, unless §5's measured latency forces a larger
  one.** 120 s is chosen so it cannot fire on a healthy run: the whole backend
  pytest step is capped at 30m by `68f249a`'s wrapper, so 120 s is ~7% of the
  budget. Its floor is checked against §5's **armed-window latency**, measured
  by one of §5's two protocols, on the same clock the watchdog runs on. **One
  rule, not two:** if that latency exceeds **12 s** (i.e. 120 s is less than
  10× it), the committed grace period is `10 × latency` rounded up to the next
  30 s, and `conftest.py` carries **that** value rather than 120; otherwise it
  carries 120. Either way the findings document records the measured latency and
  the arithmetic that selected the committed number. The window includes the
  coverage write and the warnings summary, so a raise is a live possibility,
  not a formality. The CI runner being roughly 2× slower than the laptop is
  already inside the 10× cushion.
- **Exit: yes** — `exit=True`, so the dump is followed by process termination
  rather than leaving the job to be cancelled with the stack trapped in an
  unpublished log. `faulthandler`'s timer is a daemon thread in C: a healthy run
  that exits before the deadline never fires it, so arming it cannot change a
  healthy run's exit status. It is also the **only** backstop §4a's mechanism
  cannot defeat: it acts from *inside* the pytest process and does not depend on
  a signal reaching pytest through `uv`. If §4a is confirmed, this watchdog —
  not the step wrapper — is what will produce the next occurrence's evidence,
  and the findings document must say so.

It is armed unconditionally (locally as well as in CI — that is what makes §6b's
mutation experiment real), and must not interfere with the coverage artefact.
"Unchanged `coverage.xml`" is **not** byte-identity: the file carries a
`timestamp` attribute. What is compared is the run's **exit code** (0) and the
**overall line rate** read from `coverage.xml`'s root `line-rate` attribute,
before and after the watchdog is added; both must be identical. This is the
spec's shipped probe and it lands whether or not the cause is found — it is
deliberately *not* the answer to the `## Not found` branch of the last expected
result, which must name a probe this task has not already built.

**6b. The watchdog and the job timeouts are pinned by mutation, not by markup.**
A `test_suite_hygiene.py` assertion that greps `conftest.py` for the string
`faulthandler` passes against a comment; this repository has nineteen recorded
tests that asserted nothing, and that is exactly how they got there. The
assertion must match the **armed call** — the AST node for
`faulthandler.dump_traceback_later(...)` reached from the arming hook §6 selects
(`pytest_runtestloop`, or `pytest_sessionfinish` on the stated fallback), with
its `exit` keyword — not a mention of the module. And the implementer must
actually perform two mutations and record what happened: delete the armed call,
run the hygiene module, paste the failure; restore it, delete one
`timeout-minutes:` declaration from `ci.yml`, run the hygiene module, paste the
failure; restore it. Neither mutation is committed.

The pre-existing `test_the_backend_job_still_carries_its_job_level_backstop` is
**replaced**, not kept alongside: it passes as long as any one
`timeout-minutes:` declaration exists anywhere in the file, so it would survive
mutation (b) and adds nothing once the per-job assertion exists. The new
assertion must therefore check that **the `backend` job specifically** carries a
`timeout-minutes` declaration, as part of checking every job, so no coverage is
lost in the replacement.

**7. `timeout-minutes` on the three jobs that lack it.** `backend-lint`,
`frontend` and `sonarcloud` carry none and can each still burn GitHub's
six-hour default. Give each a value justified by its observed steady state (all
three are single-digit minutes today), or record in the findings why a given job
should not have one.

Count **declarations, not occurrences**, when checking this. `ci.yml` today has
two `timeout-minutes` declarations but *five* occurrences of the word — three
are prose inside comments, and `68f249a`'s comments will keep accumulating. The
anchored form `grep -cE '^[[:space:]]+timeout-minutes:' .github/workflows/ci.yml`
returns `2` on `cd8de18` and must return `5` after this task.

### Evidence the next hang now produces (what `68f249a` already did — do not re-specify)

Read `git show 68f249a`. It makes the next occurrence diagnosable; it finds
nothing. Concretely, the next hang now yields what the earlier ones could not —
**when the process is killable**, which the two post-fix occurrences show it is
not always:

- a **failed step instead of a cancelled job**, because
  `timeout --signal=INT --kill-after=60s 30m` wraps the backend pytest
  invocation (15m for `backend-migrations`) — and a failed step keeps its log,
  where a cancelled job publishes none. **This holds conditionally, not
  generally:** it worked on job `110381880180` (step failed at 30m08s, exit 124,
  log published) and failed on jobs `110014916546` and `110405490008` (step
  never completed, no log). `ci.yml`'s comment asserting it unconditionally is
  overstated, and §4a is the suspect for why;
- the **summary line pytest had reached**, so the suite-finished-or-not question
  answers itself next time;
- **every thread's stack** if a *single test* is the one stuck, via
  `pytest.ini`'s `timeout = 300` with `timeout_method = thread`;
- the **names of any non-daemon threads still alive** when the last test ends,
  printed by `conftest.py`'s `pytest_sessionfinish`;
- a bounded failure instead of a wedged parent for any `subprocess.run` in the
  test tree.

It also gives a **decision rule**, which this task must use in a **corrected
three-branch form**: if the next occurrence fails the *step* at 30m, the hang is
inside the pytest process; if the step *completes* and the job is still
cancelled, the hang is the runner or a post-step (artefact upload); and if the
step **never completes** — the measured signature of the two post-fix
occurrences — the wedge is unkillable from outside and §4a is the live
hypothesis. Note, per §4a, that the job's 55m span is **not** a branch
discriminator: it is 45m plus a platform-constant grace window. The one thing
the rule still cannot show is a stack for the shutdown window — §6's watchdog
closes exactly that.

### Files touched

- `docs/tasks/APRAS-119-findings.md` — new. The investigation's output: the
  §1a query stated verbatim with its census timestamp and the occurrence set it
  returned (one row per job, with run id, run conclusion, job span, pytest step
  conclusion, branch and sha); the per-occurrence reading of what each log and
  jobs-API record did and did not show; the suspect table with one verdict and
  its measurement per row, including §4a's signal-propagation probe and its
  darwin caveat; the 55m-span interpretation; the local reproduction result with
  the armed-window latency and the protocol used; the arming-order verification
  against `coverage.xml`'s mtime; the watchdog's before/after exit code and
  `line-rate`, its wedge stack dump, and the two mutation experiments; and
  either the root cause with its proof, or the narrowing plus a next probe
  distinct from the shipped watchdog.
- `.github/workflows/ci.yml` — `timeout-minutes` on `backend-lint`, `frontend`
  and `sonarcloud`; a correction to the `backend` job's comment, which currently
  asserts unconditionally that the `timeout` wrapper "turns the next hang into a
  failing step with a readable log"; and, **only if §4a is confirmed**, the
  signal-propagation fix to the pytest step. Nothing else unless the
  investigation implicates it.
- `backend/tests/conftest.py` — the post-test-loop `faulthandler` watchdog armed
  per §6 (a `trylast` `pytest_runtestloop` wrapper returning the yielded value,
  or `pytest_sessionfinish` with the exclusion stated), with the grace period's
  justification and the arming-point rationale in the comment, plus the §5
  latency instrumentation if the self-contained protocol is used.
- `backend/tests/test_suite_hygiene.py` — assertions pinning the watchdog and
  the three new job timeouts, alongside the existing CI/pytest-config guards.
- Plus, **only if a root cause is confirmed**, the file that carries the fix and
  the test that guards it.

### Test criteria

`cd backend && uv run pytest tests/test_suite_hygiene.py -v` passes, including
the new assertions. The full backend suite stays green with its 90% coverage
gate, and `uv run ruff check . && uv run ruff format --check .` over `backend/`
stays at zero findings. No frontend source file is touched, so `npm run lint`'s
~375 pre-existing errors must be **no worse than base** — expected delta zero.
The watchdog is demonstrated to fire by a deliberate, discarded local experiment
(a wedged non-daemon thread), with the stack dump quoted in the findings
document. Two further mutation experiments — the armed `dump_traceback_later`
call deleted, and one `ci.yml` `timeout-minutes:` declaration deleted — must
each be observed failing the hygiene module, with the failure output recorded.

## Expected Results

- [ ] `docs/tasks/APRAS-119-findings.md` exists and states the §1a census
      **query verbatim** — every `ci.yml` run since 2026-08-01 whose conclusion
      is not `success`, each fetched with
      `gh api 'repos/:owner/:repo/actions/runs/<id>/jobs?filter=all&per_page=100'`
      — together with its **census timestamp**, the run counts it covered as of
      that timestamp (184 runs / 84 success / 90 failure / 10 cancelled as of
      `cd8de18`), and the detector it applied: a `Backend Tests` job whose
      conclusion is `cancelled` and whose `Run tests with coverage` step
      conclusion is **neither `success` nor `failure`**. The document states
      explicitly that `filter=all` is required (run `36638362231` contributes
      two occurrences, jobs `109644454563` and `109661776896`) and that a
      `null`-only step test would lose job `109628456192`, whose step conclusion
      is `cancelled`.
- [ ] The census result is presented as one row per occurrence the query
      returned at that timestamp — job id, run id, run conclusion, job
      `started_at`→`completed_at` span, pytest step conclusion, branch, sha —
      and the stated total is **at least 15**, the number the same query
      returned as of `cd8de18`. A smaller total is a failed census. The document
      states, from its own rows, that occurrences appear on at least 8 distinct
      refs including **three pushes to `master`** (`e2ccb45b`, `37e3f608`,
      `eb4b67c4`), and that **all ten** run-level `cancelled` runs in the window
      are occurrences — none is a superseded push.
- [ ] The findings document states which occurrences are post-`68f249a` (which
      landed 2026-09-30 16:40Z), derived by `git merge-base --is-ancestor`:
      exactly two, jobs `110014916546` and `110405490008`, both `pull_request`
      runs on `dependabot/uv/backend/backend-version-updates-2c543e60b5`
      (PR #42, open 2026-09-30T17:36:53Z → 2026-10-01T14:33:17Z, ~21 hours),
      both with the pytest step never completing. It records that the hang
      therefore recurred with the fix in the tree, and that **four** occurrences in
      the set — jobs `110405490008`, `110014916546`, `109628456192` and
      `109627574082` — concluded `failure` at run level — so absence of run-level
      cancellation is not evidence of absence, and the going-forward recurrence
      detector is the job-level one above.
- [ ] For each occurrence the census returned, the findings document records
      what the job log and the jobs API did and did not show, and states whether
      the suite had finished before the freeze or `unknown` with the reason the
      evidence cannot say. The 365-minute occurrence is cited as run
      `36370971185` / job `108767062588` on `e2ccb45b` — **not** "the commit
      before `13868f7`" — with its measured span of 365.00 min.
- [ ] The findings document cites run `36866106559` / job `110381880180` as a
      **non-occurrence** and as evidence the `timeout` wrapper works when the
      process is killable: step failed at 30m08s, exit code 124, log published,
      summary line
      `36 skipped, 1 warning, 2299 errors in 1798.11s (0:29:58)` with
      `sqlalchemy.exc.StatementError` on `INSERT INTO tenant`. The exit code is
      evidenced by `gh api repos/:owner/:repo/check-runs/110381880180/annotations`
      returning `Process completed with exit code 124.`, and that command is
      named in the document. The 31 MB log is not downloaded.
- [ ] The findings document records the **55m-span interpretation** explicitly:
      `timeout-minutes: 45` landed in `62a136c` (2026-09-28 18:43Z) and every
      post-`62a136c` occurrence but one spans 55m00s–55m01s, i.e. 45m plus
      GitHub's fixed post-cancellation grace, so **the uniform spans are
      platform behaviour and are not evidence that the job timeout overshot**;
      job `109628456192` (span 45m58s, pytest step `conclusion: cancelled`) is
      cited as the case where cancellation reached the step promptly. No
      conclusion in the document rests on the 55m spans as a backstop failure,
      and the §4a hypothesis is supported instead by the 30m step wrapper
      producing no completed step on jobs `110014916546`/`110405490008` while
      producing exit 124 on job `110381880180`.
- [ ] The findings document states which reading of the measured set the
      evidence supports — **tree-independent runner/image fault** vs
      **volume-triggered wedge** — or that it cannot discriminate, and the
      statement is derived from the measured refs: three `master` pushes, three
      frontend-only/imgbot refs with an unchanged backend tree, four consecutive
      occurrences on `apras-117`, and **four** distinct refs wedging inside two
      and a half minutes on 2026-09-29 (imgbot 21:26:26Z, types/node 21:27:27Z,
      jsdom 21:27:47Z, dependabot 2ed8 21:28:56Z). It records that both the
      "byte-identical backend tree" argument and the "two trees, one error
      storm" argument are **withdrawn**, and that `runner-or-image` is now the
      row most likely to move while `output volume` has lost most of its
      support.
- [ ] The findings document carries a suspect table with one row per suspect —
      leaked SQLite engine / APRAS-109, non-daemon thread, coverage writer,
      output volume, runner-or-image, **and unkillable wedge / signal
      propagation (§4a)** — each with a verdict of `confirmed` or `cleared` and
      the command whose output produced it, recorded verbatim.
      `untestable without a recurrence` is admissible on the `runner-or-image`
      row only; the other rows each carry a measurement: APRAS-109 the
      `-W error::ResourceWarning` count, non-daemon thread the
      `pytest_sessionfinish` thread report from a full local run, output volume
      the suite's warning count plus the byte size of captured stdout and of its
      largest single line.
- [ ] The **coverage-writer** row's measurement brackets the span the coverage
      write is actually in: the findings document states that `pytest-cov`
      performs `cov_controller.finish()`, the `coverage.xml` write and
      `should_fail_under` inside its `pytest_runtestloop` wrapper — quoting the
      plugin's own comment, *"we need to wrap pytest_runtestloop. by the time
      pytest_sessionfinish runs, it's too late to set testsfailed"* — and
      records three numbers: whole-process duration with coverage, whole-process
      duration with `-p no:cov`, and the coverage phase isolated by comparing
      `--cov-report=xml:coverage.xml` against `--cov=app --cov-report=`. A
      post-summary-line interval is **not** accepted as this row's measurement.
- [ ] The findings document records §4a's signal-propagation probe verbatim:
      `/opt/homebrew/bin/timeout --signal=INT --kill-after=2s 3s uv run python -c "import time; time.sleep(600)" | cat > out.txt`,
      reporting (i) `timeout`'s exit status and return time, (ii) whether a
      `python` grandchild survived (`pgrep -f 'time.sleep(600)'`), (iii) whether
      the `cat` reader exited, checked by `pgrep`; then the same probe in the
      predicted-fix shape. The row's verdict is `confirmed` or `cleared` on that
      evidence, the hypothesis is stated as a hypothesis, any surviving process
      is killed, and the document states that the probe runs on darwin against
      an ubuntu fault so **a local `cleared` does not clear the CI case**. If
      `confirmed`, `.github/workflows/ci.yml`'s pytest step carries the
      signal-propagation fix and the findings document pastes the probe output
      that justified it.
- [ ] `cd backend && uv run pytest tests/test_project_report.py -W error::ResourceWarning`
      is run and its outcome recorded verbatim in the findings document; if any
      `ResourceWarning: unclosed database` remains, the findings document names
      the fixture that emits it.
- [ ] The findings document records one full-suite local reproduction attempt
      with its wall-clock time and the **armed-window latency** — measured from
      the §6 arming point to process exit, in seconds to two decimals — and
      names which of §5's two protocols produced it: either two
      `time.monotonic()` readings taken inside the process (arming hook and
      `pytest_unconfigure`/`atexit`) with the process printing the difference
      itself, or `time.time()` printed at arming compared against
      `date +%s.%N` captured immediately after the process exits. A figure
      obtained by subtracting a `time.monotonic()` value from a shell wall clock
      is **not** accepted, nor is a latency measured from the summary line. The
      document states explicitly whether the hang reproduced.
- [ ] `backend/tests/conftest.py` arms `faulthandler.dump_traceback_later` with
      `exit=True` from a `pytest_runtestloop` wrapper declared
      `@pytest.hookimpl(wrapper=True, trylast=True)` and armed after the yield,
      with the wrapper **returning the value it received from `yield`**, so the
      armed window contains the `coverage.xml` write, the `--cov-fail-under=90`
      evaluation, the terminal and warnings summaries, `sessionfinish`,
      `unconfigure` and interpreter shutdown. The grace period it carries is
      **120 seconds if the measured armed-window latency is ≤ 12 s, otherwise
      `10 × latency` rounded up to the next 30 s**, and the findings document
      records the measured latency and the arithmetic that selected the
      committed number. The findings document also records the empirical check
      that arming precedes the `coverage.xml` write (its mtime against the
      timestamp printed at arming). If that ordering could not be established,
      arming at `pytest_sessionfinish` is accepted **only** with an explicit
      statement, in both the `conftest.py` comment and the findings document,
      that the coverage write lies outside the window, plus the isolated
      coverage-phase duration as compensating evidence.
- [ ] Arming the watchdog changes nothing about a healthy run: the findings
      document records, for a full local suite run immediately before and
      immediately after the watchdog was added, the pytest **exit code** (0 in
      both) and the `line-rate` attribute of `coverage.xml`'s root `<coverage>`
      element (identical in both). Byte comparison of `coverage.xml` is not
      accepted, because the file carries a `timestamp` attribute. The findings
      document additionally records the **first CI run after the watchdog
      lands** — its run id, its `Backend Tests` job conclusion, and whether the
      90% coverage gate passed — as the evidence that the grace period does not
      fire spuriously on a slower, loaded runner.
- [ ] The findings document quotes the stack dump produced by a deliberate,
      discarded local wedge (a non-daemon thread parked past the grace period),
      proving the watchdog fires; the wedge is not committed.
- [ ] `grep -cE '^[[:space:]]+timeout-minutes:' .github/workflows/ci.yml` returns
      `5` (it returns `2` on `cd8de18`), the three new declarations being on
      `backend-lint`, `frontend` and `sonarcloud`, each with its value justified
      in the findings document against that job's observed steady-state
      duration. If a job is deliberately left without one, the findings document
      says why per job and the expected count drops by one per such job, stated
      explicitly.
- [ ] `.github/workflows/ci.yml`'s `backend` job comment no longer asserts
      unconditionally that the `timeout` wrapper turns the next hang into a
      failing step with a readable log: it records that this held on job
      `110381880180` and failed on jobs `110014916546` and `110405490008`.
- [ ] `backend/tests/test_suite_hygiene.py` gains a named assertion that matches
      the **armed call** — the `faulthandler.dump_traceback_later(...)` call node
      reached from the arming hook `conftest.py` actually uses, including its
      `exit` keyword — and not merely a mention of the `faulthandler` module,
      plus a named assertion that every `ci.yml` job — `backend` included —
      carries a `timeout-minutes` declaration, **replacing** the pre-existing
      `test_the_backend_job_still_carries_its_job_level_backstop`, which would
      survive mutation (b) and is therefore removed rather than kept. `cd backend && uv run pytest
      tests/test_suite_hygiene.py` passes.
- [ ] The findings document records **two** mutation experiments by test name
      with the observed failure output pasted: (a) the armed
      `dump_traceback_later` call deleted from `conftest.py`, and (b) one
      `timeout-minutes:` declaration deleted from `ci.yml`. Each must show the
      corresponding hygiene test failing. Neither mutation appears in the
      committed tree.
- [ ] **Either** the root cause is confirmed, the fix is implemented, and a
      named test or CI assertion fails when the fix is reverted — and the
      findings document names that test and pastes the reverted-state failure;
      **or** the findings document contains a section `## Not found` stating the
      narrowing reached and **the single next probe, which must not be the
      shutdown watchdog this task already ships**. That section must be derived
      from the census's measured occurrence set — not from "five known
      occurrences", not from any frozen list — and must name the three-branch
      decision rule in its corrected form (step fails at 30m = inside the pytest
      process; step completes and job cancelled = runner or post-step; **step
      never completes = unkillable wedge, the measured signature of the two
      post-fix occurrences**), noting that the 55m job span is a platform
      constant and not a discriminator, and state which branch the next
      occurrence must land in to confirm the narrowing. Exactly one of the two
      branches is present.
- [ ] `cd backend && uv run pytest` is green with the 90% coverage gate, and
      `uv run ruff check . && uv run ruff format --check .` reports zero
      findings over `backend/`.
- [ ] No file under `frontend/` is modified, so the `npm run lint` error count
      is identical to the count on `cd8de18`.

## Out of Scope

- APRAS-120 (`sqlmodel` 0.0.47 rejecting naive datetimes). PR #36's 30m19s
  failure produced 2186 setup errors, and run `36866106559` / job
  `110381880180` produced 2299 on PR #42 and died at 30m08s with exit 124; both
  spent the half hour formatting tracebacks. That is a different fault and must
  not be offered as this hang's cause. §2 found that the measured occurrence set
  does not support an error-storm trigger, so the storm is in scope only as a
  hypothesis the findings document may record as unsupported.
- Re-implementing or tuning anything in `68f249a` — `pytest.ini`'s
  `timeout`/`timeout_method`, the `subprocess.run` timeouts, the
  `pytest_sessionfinish` thread report, or the engine-dispose guard. **One
  exception**, created by the measured step-level overshoot: if §4a's probe
  confirms that `timeout`'s signals do not reach pytest through `uv`, the
  step-level invocation in `ci.yml` is amended under this task, with the probe
  output as its proof. No other tuning of `68f249a` is permitted, and the 30m
  wrapper budget itself does not change.
- Changing `timeout-minutes: 45` on `backend` or `20` on `backend-migrations`.
- Any performance work on the suite. An 11-minute CI run against a 5m35s local
  one is a known gap and not this task's subject.
