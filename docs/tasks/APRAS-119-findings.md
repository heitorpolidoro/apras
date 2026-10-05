# APRAS-119 — findings

Why the `Backend Tests` job hangs after the tests have already passed.

**Outcome: the root cause is confirmed.** A `parametrize` case with no `ids=`
put a 2 MiB payload into a pytest node id, and a single 2 MiB line takes
**~68.8 minutes** to clear the GitHub Actions log pipeline. See
[§8](#8-root-cause-confirmed). The last expected result's two branches are
exclusive, and this document carries the first one — the confirmed-cause branch
— so the narrowing branch is deliberately absent rather than written alongside
it.

---

## 1a. The occurrence set, derived from a query

### The query, verbatim

Every `ci.yml` run since **2026-08-01** whose conclusion is **not** `success`:

```
gh run list --workflow=ci.yml --limit 300 --created '>=2026-08-01' \
  --json databaseId,conclusion,headBranch,headSha,createdAt,event
```

and then, for each such run:

```
gh api 'repos/:owner/:repo/actions/runs/<id>/jobs?filter=all&per_page=100'
```

### The census timestamp and what the window held

- **Census timestamp: `2026-10-05T10:40:20Z`.**
- Runs returned in the window: **189** — **87 `success`, 92 `failure`,
  10 `cancelled`**. (As of `cd8de18` the same query covered 184 runs / 84
  success / 90 failure / 10 cancelled; five `success`/`failure` runs have
  accrued since, and the ten `cancelled` runs are unchanged.)
- Non-success runs fetched for jobs: **102**.

### The detector

An occurrence is a **`Backend Tests` job whose `conclusion` is `cancelled` and
whose `Run tests with coverage` step conclusion is neither `success` nor
`failure`** — i.e. `null` *or* `cancelled`.

Two properties of the query are load-bearing and were not narrowed:

- **`filter=all` is required.** Without it the API returns only the latest
  attempt. Run `36638362231` has two attempts and both of their `Backend Tests`
  jobs are occurrences — `109644454563` (attempt 1) and `109661776896`
  (attempt 2). A census without `filter=all` silently under-counts re-run runs.
- **The step test is "did not complete", not "is `null`".** Job
  `109628456192`'s `Run tests with coverage` step carries
  `conclusion: cancelled`, not `null`. A `null`-only test classifies it as an
  ordinary failure and **loses it**.

The run window deliberately opens at 2026-08-01 and not at `68f249a`, because a
`Backend Tests` job cancelled by `timeout-minutes` makes the *run* conclude
`failure`, so a run-keyed census is blind to this hang on both sides of the fix.

---

## 2. The census result — 15 occurrences

One row per occurrence the query returned at the census timestamp.

| job | run | run concl. | `started_at` → `completed_at` (span) | pytest step | branch | sha | log |
|---|---|---|---|---|---|---|---|
| `110405490008` | `36873076533` (att 1) | failure | 2026-10-01T14:01:19Z → 2026-10-01T14:56:20Z (55m01s) | `null` | `dependabot/uv/backend/backend-version-updates-2c543e60b5` | `a347f9ce` | published (34.0 MB) |
| `110014916546` | `36752659497` (att 1) | failure | 2026-09-30T17:37:02Z → 2026-09-30T18:32:02Z (55m00s) | `null` | `dependabot/uv/backend/backend-version-updates-2c543e60b5` | `5ed64ac5` | published (34.0 MB) |
| `109926009179` | `36726903030` (att 1) | cancelled | 2026-09-30T14:09:01Z → 2026-09-30T15:04:01Z (55m00s) | `null` | **`master`** | `eb4b67c4` | 404, none |
| `109712407577` | `36659990810` (att 1) | cancelled | 2026-09-30T02:28:20Z → 2026-09-30T03:23:20Z (55m00s) | `null` | `apras-117-pin-report-escaping` | `eb4b67c4` | 404, none |
| `109702819710` | `36656817008` (att 1) | cancelled | 2026-09-30T01:47:51Z → 2026-09-30T02:42:51Z (55m00s) | `null` | `apras-117-pin-report-escaping` | `42b38fa7` | 404, none |
| `109690533619` | `36652795228` (att 1) | cancelled | 2026-09-30T00:57:35Z → 2026-09-30T01:52:35Z (55m00s) | `null` | `apras-117-pin-report-escaping` | `4dcbc8c5` | 404, none |
| `109682771349` | `36650344899` (att 1) | cancelled | 2026-09-30T00:26:33Z → 2026-09-30T01:21:33Z (55m00s) | `null` | `apras-117-pin-report-escaping` | `29df5d4f` | 404, none |
| `109661776896` | `36638362231` (att 2) | cancelled | 2026-09-29T23:10:19Z → 2026-09-30T00:05:19Z (55m00s) | `null` | `apras-118-print-selector` | `7cbe5c52` | 404, none |
| `109644454563` | `36638362231` (att 1) | cancelled | 2026-09-29T22:14:22Z → 2026-09-29T23:09:22Z (55m00s) | `null` | `apras-118-print-selector` | `7cbe5c52` | 404, none |
| `109628456192` | `36633543003` (att 1) | failure | 2026-09-29T21:28:56Z → 2026-09-29T22:14:54Z (**45m58s**) | **`cancelled`** | `dependabot/uv/backend/backend-version-updates-2ed82b0eb7` | `1283085e` | published (41 475 B) |
| `109627574082` | `36633293755` (att 1) | failure | 2026-09-29T21:27:47Z → 2026-09-29T22:22:47Z (55m00s) | `null` | `dependabot/npm_and_yarn/frontend/jsdom-30.1.1` | `350d029c` | 404, none |
| `109627607918` | `36633304578` (att 1) | cancelled | 2026-09-29T21:27:27Z → 2026-09-29T22:22:28Z (55m01s) | `null` | `dependabot/npm_and_yarn/frontend/types/node-26.6.3` | `59908a6b` | 404, none |
| `109627479498` | `36633264240` (att 1) | cancelled | 2026-09-29T21:26:26Z → 2026-09-29T22:21:26Z (55m00s) | `null` | `imgbot` | `3d0f00eb` | 404, none |
| `109515466160` | `36600250329` (att 1) | cancelled | 2026-09-29T16:47:13Z → 2026-09-29T17:42:14Z (55m01s) | `null` | **`master`** | `37e3f608` | 404, none |
| `108767062588` | `36370971185` (att 1) | cancelled | 2026-09-28T02:45:04Z → 2026-09-28T08:50:04Z (**365m00s**) | `null` | **`master`** | `e2ccb45b` | published (8.1 MB) |

**Total: 15.** That matches the floor the same query returned as of `cd8de18`;
a smaller total would have been a failed census.

Read off those rows:

- **8 distinct refs** (13 distinct shas), including **three pushes to `master`**
  — `e2ccb45b`, `37e3f608`, `eb4b67c4`.
- **All ten** run-level `cancelled` runs in the window are occurrences:
  `36370971185`, `36600250329`, `36633264240`, `36633304578`, `36638362231`,
  `36650344899`, `36652795228`, `36656817008`, `36659990810`, `36726903030`.
  Not one is a superseded push.
- Those ten runs contribute **11** occurrences (`36638362231` contributes two),
  so **four** occurrences concluded `failure` at run level: jobs
  `110405490008`, `110014916546`, `109628456192` and `109627574082`.

### 1b. The recurrence detector going forward

**A `Backend Tests` job whose conclusion is `cancelled` and whose pytest step
did not complete with `success` or `failure`.** Never "a cancelled run", and
never "step conclusion is `null`". **Absence of run-level cancellation is not
evidence of absence**, and the four `failure`-concluding occurrences above are
the proof.

### Which occurrences are post-`68f249a` — exactly two

`68f249a` landed **2026-09-30 16:40Z**. Derived with
`git merge-base --is-ancestor 68f249a <sha>` over every occurrence's sha
(exit 0 = post-fix):

- `110405490008` (`a347f9ce`) — exit 0, **post-fix**
- `110014916546` (`5ed64ac5`) — exit 0, **post-fix**
- the other 13 shas — exit 1, pre-fix

So **exactly two**, both `pull_request` runs on
`dependabot/uv/backend/backend-version-updates-2c543e60b5` (PR #42, open
**2026-09-30T17:36:53Z → 2026-10-01T14:33:17Z, ~21 hours**), both with the
pytest step **never completing**. **The hang therefore recurred with the fix in
the tree**, which is why §4a exists at all.

---

## 1. What each occurrence's evidence does and does not show

A correction to the spec's expectation first, because it changes four rows: the
spec expected "nothing: a cancelled job publishes no logs" everywhere. That is
true for **11** of the 15, but **four occurrences do publish a log**. Measured
with `gh api -i --method HEAD repos/:owner/:repo/actions/jobs/<id>/logs`:

| job | log | `content-length` |
|---|---|---|
| `110405490008` | `HTTP/1.1 200 OK` | 33 957 937 |
| `110014916546` | `HTTP/1.1 200 OK` | 33 956 695 |
| `109628456192` | `HTTP/1.1 200 OK` | 41 475 |
| `108767062588` | `HTTP/1.1 200 OK` | 8 055 090 |
| the other 11 | `HTTP/1.1 404 The specified blob does not exist.` | — |

Per occurrence:

- **`108767062588`** (run `36370971185`, `master` `e2ccb45b`, span **365.00
  min**). Log published. The jobs API shows the pytest step
  `in_progress`/`conclusion: null`, `started_at 2026-09-28T02:45:10Z`, no
  `completed_at`; steps 7 and onward `pending`. The log shows the suite green
  and `=== warnings summary ===` at `02:45:10Z + 17m26s = 03:02:36.871Z`, then
  the output pattern that is this investigation's answer (§8). **Had the suite
  finished before the freeze? Yes** — this is the one occurrence where the
  evidence says so, and it is cited as run `36370971185` / job `108767062588`
  on `e2ccb45b`, **not** as "the commit before `13868f7`".
- **`110014916546`** and **`110405490008`** (the two post-fix ones). Logs
  published, 34 MB each, 401 344 and 402 549 lines, longest line 523 bytes. Both
  are the APRAS-120 `sqlmodel` 0.0.47 error storm —
  `sqlalchemy.exc.StatementError … INSERT INTO tenant` repeated across the
  whole suite. Output stops abruptly: `110014916546`'s last line is
  `2026-09-30T18:07:18.2521440Z`, **30m07s** after the step started
  (`17:37:11Z`); `110405490008`'s last line is `2026-10-01T14:31:31.3072833Z`,
  **30m07s** after its step started (`14:01:24Z`). `110014916546`'s log even
  contains `KeyboardInterrupt` twice at `18:07:16.244Z`. So the 30-minute
  `timeout --signal=INT` **did fire and SIGINT did reach pytest** — and the
  step still never completed: the jobs API shows
  `Run tests with coverage … in_progress / null`, no `completed_at`, and
  everything after it `pending`, until `timeout-minutes` closed the job 25
  minutes later. **Had the suite finished before the freeze? No** — it was
  still in its error storm. These two are a different fault from the other 13
  (see §7 and §8).
- **`109628456192`** (span **45m58s**, step `conclusion: cancelled`). Log
  published but only 41 475 bytes / 476 lines: it is the runner's own
  bookkeeping, with **no pytest output at all**, because this is a pre-`68f249a`
  tree where the pytest step was unwrapped and its output was never flushed.
  Its last four lines are the most informative thing in the whole census:

  ```
  2026-09-29T22:14:51.4562547Z ##[error]The operation was canceled.
  2026-09-29T22:14:51.7742488Z Cleaning up orphan processes
  2026-09-29T22:14:51.8056210Z Terminate orphan process: pid (2355) (uv)
  2026-09-29T22:14:51.8086413Z Terminate orphan process: pid (2359) (pytest)
  ```

  **Had the suite finished before the freeze? `unknown`** — no pytest output was
  published, so the evidence cannot say.
- **The other 11 occurrences.** `gh api … /logs` returns
  `HTTP/1.1 404 The specified blob does not exist.`; `gh run view --log` has
  nothing to show for the same reason. The jobs API shows, identically on all
  11: `Run tests with coverage` `status: in_progress`, `conclusion: null`,
  a `started_at` and no `completed_at`, and every later step `pending`. **Had
  the suite finished before the freeze? `unknown` on all 11, and `unknown` is
  the required answer**: a cancelled job publishes no log, so there is no
  summary line, no progress output and no phase marker to read. That is the
  whole reason this investigation needed the one occurrence that *did* publish.

### A non-occurrence, recorded as one: run `36866106559` / job `110381880180`

2026-10-01 13:04Z, PR #42, same branch as the two post-fix occurrences. Its
`Run tests with coverage` step **failed at 30m08s** (`13:04:35Z → 13:34:43Z`),
**exit code 124**, and **its log is published**. The summary line is
`36 skipped, 1 warning, 2299 errors in 1798.11s (0:29:58)`, the errors being
`sqlalchemy.exc.StatementError` on `INSERT INTO tenant` — APRAS-120's sqlmodel
0.0.47 naive-datetime fault, with the half hour spent formatting tracebacks.

This is **not** an occurrence of this hang. It is cited as **evidence that
`68f249a`'s wrapper works when the process is killable**. The exit code is
evidenced without the log, by

```
gh api repos/:owner/:repo/check-runs/110381880180/annotations
```

which returns `Process completed with exit code 124.` (annotation level
`failure`, line 358780). **The 31 MB log was not downloaded** — only a
`--method HEAD` request for its `content-length` (31 766 243).

---

## 3. The 55-minute spans are a platform constant, not a backstop failure

`timeout-minutes: 45` landed in **`62a136c` (2026-09-28 18:43Z)**. Every
post-`62a136c` occurrence **but one** spans **55m00s or 55m01s**: 13 jobs,
7 refs, three days. That is **45 minutes plus GitHub's fixed post-cancellation
grace window**, and uniformity that tight is platform behaviour, not a timeout
being resisted.

It is not an inference. `gh api repos/:owner/:repo/check-runs/<job>/annotations`
returns, on **every one of those 14 jobs**:

```
The job has exceeded the maximum execution time of 45m0s
```

and on `108767062588`, the one occurrence that predates `62a136c`:

```
The job has exceeded the maximum execution time of 6h0m0s
```

So `timeout-minutes` **fired on schedule** in every case; the job record simply
closed when the grace window expired. The single exception confirms it from the
other side: job **`109628456192` spans 45m58s** (2758 s) with its pytest step at
`conclusion: cancelled` — a job where cancellation reached the step promptly and
the grace window was not needed.

**No conclusion in this document rests on the 55m spans as a backstop failure.**
The §4a hypothesis is supported instead by the contrast in the *step* wrapper:
the 30-minute wrapper produced **no completed step** on jobs `110014916546` and
`110405490008`, while producing **exit 124 and a published log** on job
`110381880180`.

---

## 7. What the measured set does and does not support

Two earlier framings are **withdrawn** and nothing here leans on either:

- **"repetition on a byte-identical backend tree, therefore the runner or the
  image"** — withdrawn as an *argument*. The set spans 8 refs and 13 shas.
- **"two backend trees, one of which was emitting an error storm, so the wedge
  may be volume-triggered"** — withdrawn as stated. Occurrences sit on three
  `master` pushes, four times in a row on `apras-117-pin-report-escaping`, and
  on three frontend-only/imgbot refs (`imgbot` `3d0f00eb`,
  `types/node-26.6.3` `59908a6b`, `jsdom-30.1.1` `350d029c`) whose backend tree
  is unchanged and whose suites emit no error storm. **Four distinct refs wedged
  inside two and a half minutes** on 2026-09-29: imgbot `21:26:26Z`,
  types/node `21:27:27Z`, jsdom `21:27:47Z`, dependabot 2ed8 `21:28:56Z` — the
  first three inside 1m21s. Only `110405490008` (and arguably `110014916546`)
  sits on a branch where an error storm is known to exist.

### Which reading the evidence supports

**Neither of the two framings the spec offered, and the evidence discriminates
between them cleanly enough to say why.**

- It is **not** a *tree-independent* runner/image fault. The measured set is
  consistent with something that varies with neither branch nor runner, and §8
  identifies it: a **tree-constant** property — a 2 MiB node id present in
  *every* tree in the set, including the three frontend-only refs, since the
  payload lives in `backend/tests/` and those refs touch only `frontend/src`.
  "The backend tree is unchanged on a frontend-only ref" was read in the spec as
  *removing* support from a volume explanation; it does the opposite. The
  constant is the backend test tree, and the constant is the cause.
- It **is** volume-driven, but not by an *error storm*. The spec's
  volume-triggered framing looked for a flood of lines and was right to be
  withdrawn; what the evidence shows is a flood of **bytes on one line**.
- The **time** clustering is explained, not left dangling. The 2026-09-29
  21:26–21:29Z cluster of four is four bot PRs opened within three minutes of
  each other, each running the same suite on the same backend tree, and the
  four consecutive `apras-117` occurrences are four pushes to one branch over
  two hours. Neither is a runner-fleet correlation; both are "the same suite,
  run again".
- What explains the **intermittency** on a byte-identical tree — the thing none
  of the earlier framings could — is that the 2 MiB line is printed only when
  that specific case appears in a *per-item* warnings-summary group, and before
  `68f249a` the `ResourceWarning: unclosed database` flood was a function of
  **garbage-collection timing**, which is why `7cbe5c52` could wedge twice and a
  near-identical tree pass in 10m57s.

**The spec's own reading, recorded as it stated it, because this document
departs from it.** The spec's §2 concluded that `runner-or-image` was *the row
most likely to move* and that `output volume` had *lost most of its support*.
That is recorded here verbatim and then contradicted on evidence: §8's
measurement reverses the two. The step the spec's reasoning was missing is that
"the backend tree is unchanged" makes a tree-resident cause *more* likely, not
less, and that a volume problem can be one line rather than many.

`runner-or-image` was the row the spec expected to move. It did not: it is
`untestable without a recurrence` and now has *less* support than it did,
because a tree-constant cause accounts for the same 8 refs without invoking the
fleet. `output volume` was the row the spec demoted, and it is the row that
turned out to be right — in a shape its prescribed probe could not see (§4).

---

## 4. The suspect table

| suspect | verdict | the command whose output produced it |
|---|---|---|
| leaked SQLite engine / APRAS-109 | **cleared** (by `68f249a`'s fix) | `cd backend && uv run pytest tests/test_project_report.py -W error::ResourceWarning` |
| non-daemon thread | **cleared** | `cd backend && uv run pytest --cov=app --cov-report=xml:coverage.xml --junitxml=test-results.xml tests/` |
| coverage writer | **cleared** | `uv run pytest -o addopts= --cov=app --cov-report= tests/` vs `uv run pytest -o addopts= --cov=app --cov-report=xml:coverage.xml tests/` vs `uv run pytest -p no:cov -o addopts= tests/` |
| output volume | **confirmed** — in the shape of a 2 MiB *node id*, not of a flood of lines | `cd backend && uv run pytest --collect-only -q -o addopts=` piped through `awk '{ if (length > m) m = length } END { print m }'` |
| runner or image | **untestable without a recurrence** | — |
| unkillable wedge / signal propagation (§4a) | **cleared** on darwin, and *not* cleared for the CI case | `/opt/homebrew/bin/timeout --signal=INT --kill-after=2s 3s uv run python -c "import time; time.sleep(600)" \| cat > out.txt` |

### Leaked SQLite engine / APRAS-109 — cleared by fix

```
$ cd backend && uv run pytest tests/test_project_report.py -W error::ResourceWarning
…
====================== 100 passed, 105 warnings in 5.29s =======================
FAIL Required test coverage of 90% not reached. Total coverage: 53.32%
exit=1
```

`grep -c "ResourceWarning" ` over that run's output: **0**. Not one
`ResourceWarning: unclosed database` and not one `ResourceWarning` of any kind —
with `-W error::ResourceWarning` in force, so any would have been an error. The
module that used to emit 108 of them emits none, and no fixture needs naming.
The non-zero exit status is the `--cov-fail-under=90` gate evaluated over one
module (53.32%), not a warning.

**"Cleared" here means "the measurement is gone", not "this was never the
cause".** It is in fact part of the cause: §8 explains that the flood is what
*printed* the 2 MiB line, and removing the flood is why the 55-minute
occurrences stopped on 2026-09-30 without anyone finding out why.

### Non-daemon thread — cleared

`conftest.py`'s `pytest_sessionfinish` thread report, from the full local run
under the CI invocation (4157 passed, 38 skipped, 6332 warnings in 289.41 s):
**the section was not printed at all.** `grep -n "non-daemon thread"` over the
captured output returns nothing, which is the hook's "no lingering thread"
path — it returns early when `threading.enumerate()` holds nothing but the main
thread and daemons. It therefore names no non-daemon thread, which is the
spec's condition for *cleared*.

(The same hook *does* fire when there is something to report: see §6's wedge
experiment, where it printed
`1 non-daemon thread(s) still alive … 'apras119-deliberate-wedge' (alive=True)`.
So the clear is a measurement, not a silent hook.)

### Coverage writer — cleared

**Where it runs is read from the installed source, not assumed.**
`backend/.venv/lib/python3.13/site-packages/pytest_cov/plugin.py:322-324`:

```python
    # we need to wrap pytest_runtestloop. by the time pytest_sessionfinish
    # runs, it's too late to set testsfailed
    @pytest.hookimpl(wrapper=True)
    def pytest_runtestloop(self, session):
```

and after the `result = yield` on line 348: `self.cov_controller.finish()`
(line 352), `self.cov_total = self.cov_controller.summary(self.cov_report)` —
the `coverage.xml` write — (line 363) and `should_fail_under(...)` (line 373).
All three complete **before any `pytest_sessionfinish` implementation runs**;
`pytest_terminal_summary` only prints. So the interval that brackets the
coverage write is the post-yield half of `pytest_runtestloop`, and a
post-summary-line interval would have cleared this suspect by construction.

Three numbers, whole-process, to exit:

| invocation | whole-process wall | pytest's own "in …" |
|---|---|---|
| `--cov=app --cov-report=xml:coverage.xml --junitxml=… tests/` | **316.28 s** | 289.41 s |
| `-p no:cov -o addopts= --junitxml=… tests/` | **186.19 s** | 162.63 s |
| `-o addopts= --cov=app --cov-report=` (pass 1 / pass 2) | **268.83 s** / 328.44 s | 248.86 s / 270.84 s |
| `-o addopts= --cov=app --cov-report=xml:coverage.xml` (pass 1 / pass 2) | **262.80 s** / 440.68 s | 239.07 s / 383.00 s |

Coverage as a whole costs ~130 s (316.28 − 186.19), and it is spent on
**tracing during the tests**, not on the write. The isolated coverage phase —
`--cov-report=xml:coverage.xml` minus `--cov-report=` — comes out at
**−6.03 s on pass 1 and +112.24 s on pass 2**, i.e. *not measurable by this
comparison*: the same invocation on the same tree varied between 239.07 s and
383.00 s of test time on this machine (several worktrees share it), and the
run-to-run noise is an order of magnitude larger than the quantity. Reported as
measured rather than cherry-picked.

The number that does settle the row is measured **inside** the process, over
exactly the window the coverage write is in: the **armed-window latency of
12.95 s** (§5), of which the `coverage.xml` write accounts for **3.43 s** —
`coverage.xml`'s mtime minus the arming timestamp. Bounded, and measured in
seconds. **Cleared.**

### Output volume — confirmed, in a shape the prescribed probe could not see

The prescribed measurements, on the current post-`68f249a` tree:

- the suite's own warning tally: **6332 warnings**
  (`4157 passed, 38 skipped, 6332 warnings in 289.41s (0:04:49)`);
- total captured stdout: **31 998 bytes** over 508 lines
  (`uv run pytest … > out.txt; wc -c out.txt`);
- largest single line: **289 bytes**
  (`awk '{ if (length > m) m = length } END { print m }'`).

By the spec's own rule — *cleared iff no single line exceeds ~1 MB and the total
is of the order of a few MB* — that is a clear. **It is not, and the reason the
probe missed it is worth stating plainly: the 2 MiB line is not in the suite's
stdout on a green run. It is in the suite's node ids.**

```
$ cd backend && uv run pytest --collect-only -q -o addopts= > collect.txt
4195 tests collected in 0.66s
$ wc -c collect.txt;  awk '{ if (length($0) > m) m = length($0) } END { print m }' collect.txt
 2524431
 2097259
```

**One collected node id was 2 097 259 characters long** — 83% of the entire
collection output on one line:

```
tests/test_project_report_branding.py::test_a_logo_the_product_would_not_accept_is_never_served[logo.png-xxxxxxxx…]
```

Verdict: **confirmed**. See §8 for the mechanism and the cost.

### Runner or image — untestable without a recurrence

No local run can clear it, and this is the one row for which that verdict is
correct. What the next occurrence would have to show to confirm it: **the pytest
step completing and the job still being cancelled** — the middle branch of the
decision rule in §9. The measured support it had (8 refs, three `master` pushes,
three frontend-only refs, four refs inside two and a half minutes) is now better
explained by a tree-*constant* cause (§7), so this row has lost support rather
than gained it.

### 4a. Unkillable wedge / signal propagation

**The hypothesis, stated as a hypothesis.** `timeout` signals its direct child,
and that child is `uv`, not pytest. If SIGINT and then SIGKILL were delivered to
`uv` alone, the pytest grandchild would be left orphaned and running, holding
the step's stdout pipe open — and a step whose output pipe never closes does not
complete however the wrapper exited. That would account for jobs `110014916546`
and `110405490008`, whose step started and never completed.

**The probe, verbatim:**

```
/opt/homebrew/bin/timeout --signal=INT --kill-after=2s 3s \
  uv run python -c "import time; time.sleep(600)" | cat > out.txt
```

Form 1 — the recorded shape:

```
Traceback (most recent call last):
  File "<string>", line 1, in <module>
    import time; time.sleep(600)
                 ~~~~~~~~~~^^^^^
KeyboardInterrupt
--- (i) timeout's exit status and return time
timeout exit status=124 returned after 3.221266000s
--- (ii) python grandchild alive? pgrep -f 'time.sleep(600)'
no match -- grandchild is gone
--- (iii) cat reader alive? pgrep -f 'cat > out.txt' and pgrep -x cat
pgrep -f 'cat > out.txt': no match (the shell never passes '>' to cat)
pgrep -x cat: no match -- the reader saw EOF and exited
--- the cat reader's own pid (80993), checked with kill -0
cat (pid 80993) has exited -- the reader saw EOF
--- cleanup
nothing to kill
```

Form 2 — the predicted-fix shape, `timeout` moved inside the `uv run`
invocation so its direct child *is* the python process
(`uv run -- /opt/homebrew/bin/timeout --signal=INT --kill-after=2s 3s python -c …`):

```
Traceback (most recent call last):
  File "<string>", line 1, in <module>
    import time; time.sleep(600)
                 ~~~~~~~~~~^^^^^
KeyboardInterrupt
--- (i) timeout's exit status and return time
timeout exit status=124 returned after 3.690772000s
--- (ii) python grandchild alive? pgrep -f 'time.sleep(600)'
no match -- grandchild is gone
--- (iii) cat reader alive? pgrep -f 'cat > out.txt' and pgrep -x cat
pgrep -x cat: no match -- the reader saw EOF and exited
--- the cat reader's own pid (81068), checked with kill -0
cat (pid 81068) has exited -- the reader saw EOF
```

Residue check after both forms: `no 'time.sleep(600)' process left`,
`no stray cat left`. **Nothing was left behind.**

**Verdict: `cleared`** — `uv` propagates SIGINT, the grandchild dies, and the
reader sees EOF, in both forms. So `ci.yml`'s pytest step carries **no**
signal-propagation fix: the one amendment to `68f249a` the spec permitted was
conditional on `confirmed`, and it is not confirmed.

**The probe runs on darwin against an ubuntu fault, so a local `cleared` does
not clear the CI case.** Process-group and signal semantics differ between the
two, and what this measures is `uv`'s signal *handling*, not the runner. Two
pieces of CI-side evidence point the other way and are recorded here rather than
suppressed:

- job `109628456192`'s log ends with
  `Terminate orphan process: pid (2355) (uv)` and
  `Terminate orphan process: pid (2359) (pytest)` — on ubuntu, both processes
  outlived the step and had to be swept by the runner;
- `uv run` does **not** `exec`: during the local full-suite run, `pgrep -fl
  pytest` showed two processes, `uv run pytest …` and
  `.venv/bin/python .venv/bin/pytest …`. The grandchild the hypothesis needs
  does exist.

What this means for the two post-fix occurrences specifically: SIGINT *did*
reach pytest on `110014916546` (its log prints `KeyboardInterrupt` at
`18:07:16.244Z`, 30m05s into the step), and the step still never completed. So
the step-level overshoot is real and unexplained by signal delivery alone. It is
also **not this hang**: both of those runs are APRAS-120's error storm, still
running at the 30-minute mark rather than wedged after a green suite, and
APRAS-120 is out of scope here. The backstop that cannot be defeated by any
variant of this mechanism is §6's watchdog, which acts from inside the pytest
process.

---

## 5. One local reproduction attempt

Full suite under the CI invocation, on the tree with the watchdog armed:

```
cd backend && uv run pytest --cov=app --cov-report=xml:coverage.xml \
  --junitxml=test-results.xml tests/
```

- exit code **0**
- wall clock **368.70 s** (6m08.70s); pytest's own figure
  `4157 passed, 38 skipped, 6332 warnings in 323.78s (0:05:23)`
- **armed-window latency: 12.95 s**

**The hang did not reproduce.** That is the expected result — local steady state
is 5–6 minutes against CI's ~11 — and §8 says why it cannot reproduce on a
laptop: the 68.8 minutes per 2 MiB line is a property of the GitHub Actions log
pipeline, not of the pytest process. A laptop writes the same 2 MiB line to a
pipe in milliseconds.

**Protocol used: §5's preferred, self-contained one.** Two `time.monotonic()`
readings taken inside the process — one in the arming hook, one in an
`atexit`-registered callback, which runs later than `pytest_unconfigure` — with
the process printing the difference itself:

```
[APRAS-119] shutdown watchdog armed at 1791200736.225 epoch s, grace 150s; coverage.xml present=False
========= 4157 passed, 38 skipped, 6332 warnings in 323.78s (0:05:23) ==========
[APRAS-119] armed-window latency: 12.95s (grace period 150s)
```

No monotonic reading was subtracted from a shell wall clock, and the latency is
**not** measured from the summary line: it starts at the arming point, which
precedes the coverage write, the terminal summary and the warnings summary.
(The shell's own `date +%s.%N` immediately after exit, `1791200778.969`, is
recorded for completeness — 42.74 s after the arming epoch reading — but it is
*not* the reported figure, because the two clocks are different and because that
interval includes `uv`'s own teardown outside the Python process.)

---

## 6. The shutdown watchdog

`backend/tests/conftest.py` arms `faulthandler.dump_traceback_later(
SHUTDOWN_GRACE_SECONDS, exit=True)` from a
`@pytest.hookimpl(wrapper=True, trylast=True)` `pytest_runtestloop` wrapper,
**after the yield**, and the wrapper returns the value it received from `yield`.
The armed window is therefore everything after the last test: the
`coverage.xml` write, the `--cov-fail-under=90` evaluation, the terminal and
warnings summaries, `sessionfinish`, `unconfigure` and interpreter shutdown.

### The arming order, checked empirically

From the full local run above:

```
armed at (epoch s)             = 1791200736.225
coverage.xml present at arming = False
coverage.xml mtime (epoch s)   = 1791200739.652
coverage.xml mtime - armed     = +3.427 s
```

`coverage.xml` did not exist at the arming point and was written **3.427 s
after** it. The ordering the spec prescribes is reproduced, so the
`pytest_sessionfinish` fallback is not used and no exclusion statement is
needed.

### The grace period, and the arithmetic that selected it

The rule: **120 s if the measured armed-window latency is ≤ 12 s, otherwise
`10 × latency` rounded up to the next 30 s.**

- measured armed-window latency: **12.95 s**
- 12.95 **> 12**, so the rule bites
- 10 × 12.95 = **129.5 s**
- rounded up to the next multiple of 30 s = **150 s**

`conftest.py` therefore carries `SHUTDOWN_GRACE_SECONDS = 150`, **not** 120.
150 s is 11.6× the measured latency and ~8% of `ci.yml`'s 30-minute step budget,
with the CI runner roughly 2× slower than this laptop — comfortably inside the
cushion.

A caveat on the measurement, recorded rather than smoothed: 12.95 s is close to
the 12 s threshold and was measured on a machine that was not idle (several
worktrees share it; the same invocation varied 239–383 s of test time across the
day). The rule was applied to the measured number as written, which errs on the
side of the larger grace period.

### Arming the watchdog changes nothing about a healthy run

| | exit code | `coverage.xml` root `line-rate` |
|---|---|---|
| full local suite immediately **before** the watchdog was added | **0** | **0.9431** |
| full local suite immediately **after** | **0** | **0.9431** |

Identical. Compared this way and not by bytes, because `coverage.xml` carries a
`timestamp` attribute (`1791197873010` on the before run) that differs by
construction on every run.

**The first CI run after the watchdog lands: pending.** This task deliberately
triggers no CI run, so the run id, the `Backend Tests` job conclusion and
whether the 90% coverage gate passed are to be filled in by whoever lands it —
that observation is the evidence that a 150 s grace period does not fire
spuriously on a slower, loaded runner, and it cannot be made before the commit
exists.

### The watchdog fires — a deliberate, discarded local wedge

A throwaway `backend/tests/test_apras119_wedge_probe.py` started a non-daemon
thread parked on `time.sleep(600)`, which is the recorded shape exactly:
CPython's interpreter shutdown joins non-daemon threads, so the process runs its
tests, prints its summary, writes its coverage — and never exits. The file was
deleted afterwards and **is not committed**.

```
$ uv run pytest tests/test_apras119_wedge_probe.py -o addopts= -q
.[APRAS-119] shutdown watchdog armed at 1791200977.012 epoch s, grace 150s; coverage.xml present=True
                                                                         [100%]
====================== 1 non-daemon thread(s) still alive ======================
The interpreter joins these on the way out, so a run that appears to
hang after its summary is almost certainly waiting on one of them:
  - 'apras119-deliberate-wedge' (alive=True)
…
1 passed, 1 warning in 0.02s
Timeout (0:02:30)!
Thread 0x000000017079f000 (most recent call first):
  File ".../backend/tests/test_apras119_wedge_probe.py", line 15 in <lambda>
  File ".../lib/python3.13/threading.py", line 995 in run
  File ".../lib/python3.13/threading.py", line 1044 in _bootstrap_inner
  File ".../lib/python3.13/threading.py", line 1015 in _bootstrap

Thread 0x00000001ee662180 (most recent call first):
  File ".../lib/python3.13/threading.py", line 1543 in _shutdown
exit=1
wall=151.393805000
```

`Timeout (0:02:30)!` is the 150 s grace period expiring; both stacks are
dumped — including the main thread parked in `threading._shutdown`, which is
precisely the frame no other guard could produce — and `exit=True` ends the
process with status 1 at 151.39 s instead of leaving the job to be cancelled.
`pgrep -fl 'apras119'` afterwards: `no wedge process left`.

One known limit of the watchdog, recorded in `conftest.py`'s comment as well:
`faulthandler` resolves `sys.stderr` to a file descriptor, and pytest's default
capture is fd-level, so a dump that fires *before* capture is torn down lands in
the capture buffer and dies with the process. The dump above fired at
interpreter shutdown, past capture teardown, and reached the real stderr — which
is the recorded signature's shape.

---

## 6b / R19. Mutation experiments

Three mutations, each applied, run, and restored. **None appears in the
committed tree** — `git status --short` after the experiments shows only the four
intended files as modified.

### (a) the armed `dump_traceback_later` call deleted from `conftest.py`

Test: `tests/test_suite_hygiene.py::test_the_shutdown_watchdog_is_armed_from_the_hook_that_brackets_coverage`

```
E       AssertionError: `pytest_runtestloop` does not call `faulthandler.dump_traceback_later(...)`. Nothing else in the suite can produce a stack for a process that passes its tests and then never exits: `pytest-timeout` caps one *test*, and `ci.yml`'s `timeout` wrapper fails the step with whatever was printed, which on jobs 110014916546 and 110405490008 was not even a completed step.
E       assert []

tests/test_suite_hygiene.py:323: AssertionError
FAILED tests/test_suite_hygiene.py::test_the_shutdown_watchdog_is_armed_from_the_hook_that_brackets_coverage
1 failed, 1 warning in 0.06s
```

### (b) one `timeout-minutes:` declaration deleted from `ci.yml`

The `sonarcloud` job's `timeout-minutes: 15` was removed. Test:
`tests/test_suite_hygiene.py::test_every_ci_job_carries_a_timeout_minutes_declaration`

```
E       AssertionError: these ci.yml jobs carry no `timeout-minutes`: ['sonarcloud']. Each one can still burn GitHub's six-hour default, and a job killed that way is *cancelled*, which publishes no logs at all.
E       assert not ['sonarcloud']

tests/test_suite_hygiene.py:259: AssertionError
FAILED tests/test_suite_hygiene.py::test_every_ci_job_carries_a_timeout_minutes_declaration
1 failed, 1 warning in 0.06s
```

The pre-existing `test_the_backend_job_still_carries_its_job_level_backstop`
would have **passed** against this mutation — it searched the whole file for one
anchored `timeout-minutes:` line and four remained — which is why it is
*removed* rather than kept alongside. Its coverage is not lost: the replacement
asserts `"backend" in jobs` by name before sweeping every job.

### (c) the root-cause fix reverted

The `ids=` keyword deleted from the `parametrize` in
`tests/test_project_report_branding.py`. Test:
`tests/test_suite_hygiene.py::test_no_collected_node_id_can_carry_a_payload`

```
E       AssertionError: these collected node ids exceed 1024 characters, so pytest built them out of their parameters instead of out of a name: ['2097259 chars: tests/test_project_report_branding.py::test_a_logo_the_product_would_not_accept_...']
E       assert not ['2097259 chars: tests/test_project_report_branding.py::test_a_logo_the_product_would_not_accept_...']

tests/test_suite_hygiene.py:433: AssertionError
FAILED tests/test_suite_hygiene.py::test_no_collected_node_id_can_carry_a_payload
1 failed, 1 warning in 2.28s
```

---

## 8. Root cause, confirmed

### The chain

1. **A `parametrize` case put a 2 MiB payload into a node id.**
   `backend/tests/test_project_report_branding.py`'s
   `test_a_logo_the_product_would_not_accept_is_never_served` parametrised
   `("logo.png", b"x" * (TenantService.LOGO_MAX_FILE_SIZE + 1))` — 2 097 153
   bytes — with no `ids=`, so pytest built the case's id out of the payload
   itself. Measured on the pre-fix tree:
   **the longest collected node id was 2 097 259 characters.**

2. **Any output that names the case emits that id as a single ~2 MiB line.**
   Observed, not theorised: line 15 596 of job `108767062588`'s log is exactly
   that line, **2 097 289 bytes**, inside the `warnings summary` section.

3. **On the GitHub Actions runner, one 2 MiB line costs ~68.8 minutes.** From
   the same log, the timestamps the runner stamped as it read each line:

   | log line | timestamp | bytes | gap from previous |
   |---|---|---|---|
   | 15 595 (short) | 2026-09-28T03:02:37.383Z | 30 | — |
   | 15 596 (**2 MiB**) | 2026-09-28T04:11:24.233Z | 2 097 289 | **68.78 min** |
   | 15 597–15 601 (short) | 2026-09-28T05:20:12.159Z | ≤ 218 | **68.80 min** |
   | 15 602 (**2 MiB**) | 2026-09-28T06:28:58.295Z | 2 097 289 | **68.77 min** |
   | 15 603–15 607 (short) | 2026-09-28T07:37:44.167Z | ≤ 218 | **68.76 min** |
   | 15 608 (**2 MiB**) | 2026-09-28T08:46:30.048Z | 2 097 289 | **68.76 min** |

   Five consecutive gaps of 68.76–68.80 minutes, alternating 2 MiB line and
   short-line group — i.e. ~137.5 minutes of runner time per 2 MiB line, in two
   stages of ~68.8. The five gaps span only 2.05 s of each other, which is what
   a per-byte platform constant looks like and not what a variable load looks
   like. Everything before line 15 596 arrived at normal speed:
   15 595 lines in the 17m26s the tests took plus the first 0.5 s of the
   warnings summary. **The mechanism inside the runner's log processor is a
   hypothesis** (per-line scanning for workflow commands and secret masking,
   apparently superlinear in line length); **the cost is a measurement.**

4. **That is "hangs after the tests have already passed", exactly.** On
   `108767062588`: suite green in 17m26s, warnings summary begins, three 2 MiB
   lines emerge over the next six hours, and GitHub's six-hour default cancels
   the job at **365.00 min**. After `62a136c` the same shape is cancelled by
   `timeout-minutes: 45` roughly 27 minutes into the *first* 2 MiB line — which
   is why 13 of the 15 occurrences have a pytest step that started, produced
   nothing further, and never completed.

5. **The intermittency is explained too.** pytest's warnings summary groups by
   location and collapses to the module when many items share a warning; it
   prints the full node id when a location belongs to one item. Before
   `68f249a`, the `ResourceWarning: unclosed database` flood was emitted
   wherever the garbage collector happened to close a leaked `StaticPool`
   connection — a different item each run. So whether the 2 MiB node id reached
   the warnings summary was a function of **GC timing**, which is how a
   byte-identical backend tree could pass in 10m57s and wedge twice on
   `7cbe5c52`.

6. **And the apparent cure on 2026-09-30 is explained.** `68f249a` disposed the
   per-test engine, the flood stopped, the per-item warnings groups stopped, and
   the 2 MiB line stopped being printed. The last occurrence of the 13 is
   `109926009179` at 2026-09-30 14:09Z, two and a half hours before `68f249a`
   landed at 16:40Z. The only two occurrences after it are jobs
   `110014916546` and `110405490008` — APRAS-120's error storm on PR #42, still
   *running* at the 30-minute mark rather than wedged after a green suite, and a
   different fault (§4a).

**The hazard was still live on `cd8de18`.** The flood is gone, but the 2 MiB node
id was not: `uv run pytest --collect-only -q` on today's tree produced it, and
any failure header, `-v` run or per-item warnings group naming that case would
have printed it again.

### The fix

`ids=["an-svgs-active-content", "an-untyped-suffix", "past-the-size-ceiling"]`
on that `parametrize`. The payload stays exactly what it was — the test still
stores 2 MiB + 1 bytes and still asserts the product refuses it — only the
*identifier* stops carrying it.

Measured after the fix:

| | longest collected node id | collection output |
|---|---|---|
| before | **2 097 259 chars** | 2 524 431 B |
| after | **286 chars** | 427 396 B |

The two byte figures in the right-hand column come from different tree
snapshots, so only the character figures are directly comparable. `2 524 431 B`
was read before this change added its own tests, when the suite collected 4195
items; reverting only the `ids=` line on the tree as it stands gives
`2 525 096 B` at 4201 items. The whole 665-byte difference is accounted for by
node ids and output that did not exist at the earlier reading: 175 bytes net
from the three hygiene tests added here less the one removed, 161 bytes from the
two `[APRAS-119]` watchdog diagnostic lines `conftest.py` now prints, and 329
bytes from four `test_projects.py` ids added by APRAS-102. A reader who cannot
reproduce `2 524 431` on a later tree has not failed to reproduce it — the
figure is tree-dependent by construction, and so is the `427 396 B` beside it,
which reads `427 725 B` at 4201 items. The load-bearing figure,
**2 097 259 characters**, is not: it reproduces exactly on both snapshots.

### The test that fails when the fix is reverted

`backend/tests/test_suite_hygiene.py::test_no_collected_node_id_can_carry_a_payload`.
It collects the whole suite in a subprocess — the id that matters is the one
pytest actually builds, and only pytest builds it — and fails if any node id
exceeds `MAX_NODE_ID = 1024` characters, with a vacuity floor of
`MIN_COLLECTED = 4000` so a broken collection cannot pass by finding no
offenders. The reverted-state failure is pasted in mutation **(c)** above.

---

## 9. The decision rule for the next occurrence

Stated in its corrected three-branch form, and derived from this census's
measured 15-occurrence set rather than from any frozen list:

- **the step fails at 30m** → the hang is inside the pytest process (job
  `110381880180`'s shape: exit 124, log published);
- **the step completes and the job is still cancelled** → the runner or a
  post-step, e.g. artefact upload;
- **the step never completes** → the wedge is unkillable from outside. This is
  the **measured signature of the two post-fix occurrences**, jobs
  `110014916546` and `110405490008`.

**The job's 55m span is not a discriminator**: it is 45 minutes plus a
platform-constant grace window, evidenced by the
`The job has exceeded the maximum execution time of 45m0s` annotation on every
one of those jobs (§3).

For the narrowing in §8 to be confirmed rather than merely consistent, the next
occurrence must land in the **first** branch — the step failing with a published
log — and that log must show an oversized line. With `ids=` in place and
`test_no_collected_node_id_can_carry_a_payload` guarding it, the prediction is
that there is no next occurrence of this shape at all; a recurrence in the
**third** branch would instead reopen §4a, which this document leaves cleared
only for darwin.

---

## 7b. `timeout-minutes` on the three jobs that lacked it

`grep -cE '^[[:space:]]+timeout-minutes:' .github/workflows/ci.yml` returns
**5** (it returns `2` on `cd8de18`; the five *occurrences* of the word there are
three prose mentions inside comments plus the two declarations, which is why the
anchored form is the one counted). No job is deliberately left without one.

Each value is justified against that job's observed steady state, measured over
the **41 successful `ci.yml` runs** in the census window:

| job | median | p90 | worst observed | declared | ratio to worst |
|---|---|---|---|---|---|
| `backend-lint` | 0.17m | 0.28m | 1.85m | **10m** | 5.4× |
| `frontend` | 2.55m | 2.80m | 3.37m | **15m** | 4.5× |
| `sonarcloud` | 1.17m | 2.03m | 2.32m | **15m** | 6.5× |

`sonarcloud` gets 15m rather than 10m because it is the one job that waits on a
third party — the scanner uploads to SonarCloud and retries — so its tail is not
governed by this repository. `backend` (45m) and `backend-migrations` (20m) are
unchanged, as the spec requires.

`ci.yml`'s `backend` job comment no longer asserts unconditionally that the
`timeout` wrapper turns the next hang into a failing step with a readable log:
it now records that this **held on job `110381880180`** and **failed on jobs
`110014916546` and `110405490008`**, and that the ~55m span is platform
behaviour rather than this backstop overshooting.

---

## 10. Gate readings

- `cd backend && uv run pytest` — green with the 90% coverage gate. See §11.
- `cd backend && uv run ruff check . && uv run ruff format --check .` — zero
  findings. See §11.
- `cd backend && uv run pytest tests/test_suite_hygiene.py` — passes
  (11 passed in 6.58 s).
- **No file under `frontend/` is modified**, so `npm run lint`'s error count is
  identical to the count on `cd8de18`. `git status --short` lists exactly
  `.github/workflows/ci.yml`, `backend/tests/conftest.py`,
  `backend/tests/test_project_report_branding.py` and
  `backend/tests/test_suite_hygiene.py`, plus this document.

## 11. Final gate output

```
$ cd backend && uv run pytest
[APRAS-119] shutdown watchdog armed at 1791201733.376 epoch s, grace 150s; coverage.xml present=True
Required test coverage of 90% reached. Total coverage: 94.31%
========= 4159 passed, 38 skipped, 6332 warnings in 559.82s (0:09:19) ==========
[APRAS-119] armed-window latency: 14.33s (grace period 150s)
exit=0
wall=640.503533000

$ cd backend && uv run ruff check .
All checks passed!
exit=0

$ cd backend && uv run ruff format --check .
301 files already formatted
exit=0
```

4159 cases where the pre-task tree collected 4157: three assertions added
(`test_the_shutdown_watchdog_is_armed_from_the_hook_that_brackets_coverage`,
`test_every_ci_job_carries_a_timeout_minutes_declaration`,
`test_no_collected_node_id_can_carry_a_payload`) and one removed
(`test_the_backend_job_still_carries_its_job_level_backstop`).

The `line-rate` is unchanged at 0.9431 (94.31%), as §6's before/after table
records.

**A second reading of the armed-window latency, for the grace period's
robustness.** This final run — nine minutes of test time rather than five, on a
busy machine — reported **14.33 s**. The rule applied to that figure gives
10 × 14.33 = 143.3 s, rounded up to the next 30 s = **150 s**: the same
committed value. The selected grace period therefore satisfies the rule on both
measurements taken, which is worth more than the single reading the spec
required.
