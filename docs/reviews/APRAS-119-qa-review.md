# APRAS-119 — QA verification

VERDICT: APPROVED

Verified independently against the 22 expected results only, in the worktree
`/Users/heitor/workspace/apras/.claude/worktrees/agent-a768c37eeecc47980`
(fast-forwarded to `6be21c8`, six paths staged). Every published figure that
could be re-derived was re-derived from the GitHub API, the job log, or a local
run; every assertion the task ships was mutation-tested. The worktree was left
exactly as found: six paths staged, nothing unstaged, `backend/.env` in place,
no stray processes.

## Expected Results Checked

- [x] **R1 — census query, timestamp, counts, detector, `filter=all`, non-`null` step.**
  Verified by re-running the document's own query. `gh run list --workflow=ci.yml
  --limit 300 --created '>=2026-08-01'` returns **189 runs — 87 success, 92
  failure, 10 cancelled**, and **102 non-success**, matching the document's
  census block exactly. The per-run call is stated in the required form
  (`gh api 'repos/:owner/:repo/actions/runs/<id>/jobs?filter=all&per_page=100'`),
  census timestamp `2026-10-05T10:40:20Z` recorded, and the detector is stated
  as "`Backend Tests` conclusion `cancelled` **and** `Run tests with coverage`
  step conclusion neither `success` nor `failure`". `filter=all` necessity
  reproduced: without it run `36638362231` returns only job `109661776896`
  (attempt 2); with it, `109644454563` (attempt 1) **and** `109661776896`. The
  `null`-only objection reproduced: job `109628456192`'s pytest step conclusion
  is `cancelled`, so a `null`-only test loses it — my own detector, run both
  ways, returns **15 with the stated test and 13 with a `null`-only test**.

- [x] **R2 — one row per occurrence, total ≥ 15, ≥ 8 refs, three `master` pushes, all ten cancelled runs.**
  I re-implemented the detector from scratch over all 102 non-success runs. It
  returned **15 occurrences**, and every field of every row — job id, run id,
  run conclusion, `started_at`→`completed_at`, measured span, pytest step
  conclusion, branch, sha — matches the document's table row for row, including
  the 55m00s/55m01s split and `109628456192`'s 45m58s. Distinct refs: **8**
  (`master`, `apras-117-pin-report-escaping`, `apras-118-print-selector`,
  two `dependabot/uv/backend/*`, `types/node-26.6.3`, `jsdom-30.1.1`, `imgbot`);
  13 distinct shas; three `master` pushes `e2ccb45b`, `37e3f608`, `eb4b67c4`.
  All ten run-level `cancelled` runs appear as occurrences, and the four
  `failure`-level occurrences are exactly `110405490008`, `110014916546`,
  `109628456192`, `109627574082`.

- [x] **R3 — post-`68f249a` set, derived by `git merge-base --is-ancestor`.**
  `git show -s 68f249a` → `2026-09-30T13:40:31-03:00` = **16:40:31Z** as stated.
  Ran `git merge-base --is-ancestor 68f249a <sha>` over all 13 shas: exit 0 for
  `a347f9ce` and `5ed64ac5` only — **exactly two post-fix occurrences**, jobs
  `110014916546` and `110405490008`, both `pull_request` on
  `dependabot/uv/backend/backend-version-updates-2c543e60b5`. `gh pr view 42`
  → `createdAt 2026-09-30T17:36:53Z`, `closedAt 2026-10-01T14:33:17Z` (~21 h),
  verbatim. Both jobs' pytest steps never complete. The document states the
  hang recurred with the fix in the tree and names the four `failure`-level
  occurrences as the reason absence of run-level cancellation is not evidence
  of absence.

- [x] **R4 — per-occurrence evidence, and the 365-minute occurrence.**
  Log availability re-measured with `gh api -i --method HEAD .../logs`:
  `110405490008` 33 957 937 B, `110014916546` 33 956 695 B, `109628456192`
  41 475 B, `108767062588` 8 055 090 B — all four byte-identical to the
  document's table — and `404 The specified blob does not exist.` on the
  sampled one of the other eleven. The 365-minute occurrence is cited as run
  `36370971185` / job `108767062588` on `e2ccb45b`; I measured the span from the
  API as **365.00 min** (02:45:04Z → 08:50:04Z). "Suite finished before the
  freeze? Yes" is independently confirmed from the log: the last progress line
  is `tests/test_voting_rbac.py ...... [100%]` at `03:02:36.871Z` with no
  `FAILED`/`ERROR` anywhere before the warnings-summary header (log line 441,
  `03:02:36.871Z`), i.e. green at 17m26s after the step's `02:45:10Z` start.
  `unknown` is recorded with its reason for the eleven logless occurrences and
  for `109628456192`.
  *Observation, not a finding:* the jobs API no longer returns **any** steps for
  job `108767062588` (`steps = []` on both the run-jobs and single-job
  endpoints), so the document's description of that job's step record
  (`in_progress`/`null`, later steps `pending`) is no longer reproducible — the
  job is the only one in the set older than seven days, and every 2026-09-29
  job still carries full step data, which points at GitHub step-detail
  retention rather than at an inaccurate claim. The load-bearing evidence for
  that occurrence is its published log, which I verified directly.

- [x] **R5 — the non-occurrence, and the named annotations command.**
  `gh api repos/:owner/:repo/actions/jobs/110381880180` → step 6
  `Run tests with coverage` **failure**, `13:04:35Z → 13:34:43Z` = **30m08s**,
  later steps skipped. `gh api repos/:owner/:repo/check-runs/110381880180/annotations`
  — the exact command the document names — returns
  `failure / line 358780 / Process completed with exit code 124.`, verbatim.
  Summary line confirmed as
  `=========== 36 skipped, 1 warning, 2299 errors in 1798.11s (0:29:58) ===========`
  with `sqlalchemy.exc.StatementError` and 4 598 `INSERT INTO tenant`
  occurrences. `content-length` of the log is **31 766 243**, matching the
  document, which states it did not download it.
  *QA disclosure:* my attempt to read only the tail of that log via a `Range`
  header was not honoured by `gh`, so the 31 MB blob was transferred once on
  the QA side (and deleted). That is a QA-side cost, not a defect in the work.

- [x] **R6 — the 55-minute spans as platform behaviour.**
  Independently confirmed on all 15 jobs:
  `gh api repos/:owner/:repo/check-runs/<job>/annotations` returns
  `The job has exceeded the maximum execution time of 45m0s` on **each of the
  14** post-`62a136c` occurrences, and `… of 6h0m0s` on `108767062588`. Spans
  re-measured: 13 at 55m00s–55m01s plus `109628456192` at **45m58s** with step
  conclusion `cancelled`, exactly as cited. The document states the 55m figure
  is 45m plus GitHub's grace window, is not evidence of overshoot, and that no
  conclusion rests on it; §3 explicitly rests the §4a argument on the step
  contrast instead.

- [x] **R7 — which reading the evidence supports, and the two withdrawals.**
  §7 states both withdrawals explicitly ("byte-identical backend tree" and
  "two trees, one error storm") and derives its answer from the measured refs.
  I checked the measured premises: the three bot refs touch **frontend only** —
  `git diff --name-only $(git merge-base <sha> master) <sha>` returns only
  `frontend/...` paths for `3d0f00eb`, `59908a6b` and `350d029c` — the four
  consecutive `apras-117` occurrences and three `master` pushes are in my own
  census rows, and the four refs that wedged between `21:26:26Z` and
  `21:28:56Z` on 2026-09-29 are too. The conclusion (tree-**constant** cause,
  volume-driven by bytes on one line, not an error storm) is supported.

- [x] **R8 — the suspect table.**
  Six rows, one per required suspect, each with a verdict and the command that
  produced it. `untestable without a recurrence` appears on the
  `runner-or-image` row only; every other row carries a measurement. Spot-checks
  of the measurements: the `ResourceWarning` command (R11 below), the
  non-daemon-thread clear (`grep -c "non-daemon thread"` over my own full-suite
  output: **0**, i.e. the hook's no-lingering-thread path — and the same hook
  *does* fire when there is something to report, which I reproduced in R15),
  and the output-volume confirmation (R20 below).

- [x] **R9 — the coverage-writer row brackets the real window.**
  Verified against the installed plugin source,
  `backend/.venv/lib/python3.13/site-packages/pytest_cov/plugin.py`: the quoted
  comment is verbatim at lines 322–323 (`# we need to wrap pytest_runtestloop.
  by the time pytest_sessionfinish / # runs, it's too late to set testsfailed`),
  the `@pytest.hookimpl(wrapper=True) def pytest_runtestloop` follows, and
  `cov_controller.finish()`, `self.cov_controller.summary(self.cov_report)` (the
  `coverage.xml` write) and `should_fail_under(...)` all sit after the
  `result = yield`. Whole-process durations are recorded with coverage, with
  `-p no:cov`, and with the coverage phase isolated — with the honest statement
  that the isolated phase is below this machine's noise, and the row settled
  instead by the in-process figure (`coverage.xml` mtime − arming point =
  3.43 s). No post-summary-line interval is used.

- [x] **R10 — the §4a signal-propagation probe.**
  Recorded verbatim in both forms. I re-ran both:
  `/opt/homebrew/bin/timeout --signal=INT --kill-after=2s 3s uv run python -c
  "import time; time.sleep(600)" | cat > out.txt` → `KeyboardInterrupt`,
  **exit 124**, returned after **3.229 s** (document: 3.221 s), `pgrep -f
  'time.sleep(600)'` no match, `pgrep -x cat` no match. Form 2 (`timeout`
  inside `uv run`) → exit 124, no grandchild. `pgrep` after both: nothing left.
  The document's verdict is `cleared`, it states that the probe runs on darwin
  against an ubuntu fault so a local clear does not clear the CI case, and it
  records the two counter-indications (job `109628456192`'s
  `Terminate orphan process … (uv) / (pytest)` lines, and `uv run` not
  `exec`ing). Because the verdict is `cleared`, R10's conditional does not
  require a signal-propagation fix in `ci.yml`, and none is present — the
  `ci.yml` comment instead records the probe and its limit.

- [x] **R11 — `-W error::ResourceWarning`.**
  Re-run: `100 passed, 105 warnings in 5.29s` with `FAIL Required test coverage
  of 90% not reached. Total coverage: 53.33%` (the gate over one module). Zero
  `ResourceWarning` of any kind in the output with the filter promoted to an
  error, so no fixture needs naming. The document records the same outcome
  (coverage reads 53.32% there vs 53.33% now — master has moved).

- [x] **R12 — one local reproduction attempt.**
  Recorded with wall clock **368.70 s** and armed-window latency **12.95 s**,
  naming §5's preferred self-contained protocol. The protocol is verifiable in
  the code: `conftest.py` takes `time.monotonic()` in the arming hook and
  subtracts it inside an `atexit`-registered callback in the same process — no
  monotonic-minus-shell-clock figure, and the window starts at the arming point,
  not at the summary line (the document explicitly records and discards the
  shell reading). "The hang did not reproduce" is stated explicitly, with the
  reason it cannot reproduce on a laptop.

- [x] **R13 — the watchdog's shape and the grace arithmetic.**
  Read from `backend/tests/conftest.py`: `@pytest.hookimpl(wrapper=True,
  trylast=True)` on `pytest_runtestloop`; `result = yield` first, then
  `armed_at = time.monotonic()`, `atexit.register(...)`,
  `faulthandler.dump_traceback_later(SHUTDOWN_GRACE_SECONDS, exit=True)`, and
  `return result` at the end — the wrapper returns what it received from
  `yield`. `SHUTDOWN_GRACE_SECONDS = 150`, and both the measurement (12.95 s)
  and the arithmetic (12.95 > 12 → 10 × 12.95 = 129.5 → next 30 s = 150) are
  recorded in the document **and** in the constant's own comment. The empirical
  arming-order check is recorded (`coverage.xml present=False` at arming, mtime
  +3.427 s), and I observed the same marker live: my own full run printed
  `[APRAS-119] shutdown watchdog armed at … grace 150s`.
  *Observation:* the armed-window latency is machine-load dependent — my runs
  measured 5.91 s (full suite) and 1.22 s (single module), below the 12 s
  threshold, where the rule would have selected 120 s. The document records two
  readings (12.95 s and 14.33 s), both of which select 150 s under the rule, and
  flags the proximity to the threshold itself. 150 s is the conservative side of
  the rule and the number is justified as the rule requires, so this is noise in
  the input, not a defect.

- [x] **R14 — a healthy run is unchanged; last clause pending, and marked pending.**
  The before/after table records exit code **0 in both** and `coverage.xml` root
  `line-rate` **0.9431 in both**, with an explicit statement that bytes were not
  compared and why (the `timestamp` attribute). My own full run reproduces
  `line-rate = 0.9431` and exit 0. The first-CI-run clause is recorded as
  **"The first CI run after the watchdog lands: pending"** with the reason (the
  task triggers no CI run) and what the next person must fill in — present and
  labelled, not omitted. As the dispatch directs, this clause cannot be
  satisfied before the commit exists and is **not** counted as a failure.

- [x] **R15 — the watchdog fires, and the wedge is not committed.**
  Independently reproduced. I created a throwaway non-daemon-thread wedge test,
  ran it, and got the documented shape: the `1 non-daemon thread(s) still alive`
  report, `1 passed`, then `Timeout (0:02:30)!` with the wedged thread's stack
  **and** the main thread parked in `threading.py … 1543 in _shutdown`, exit
  code **1** at **151.0 s** wall. My probe file was deleted; `git status` after
  shows the six staged paths and nothing else, and no `wedge`/`apras119` file
  exists under `backend/tests/`. No process was left behind (`pgrep` clean).

- [x] **R16 — five anchored `timeout-minutes`, each justified.**
  `grep -cE '^[[:space:]]+timeout-minutes:' .github/workflows/ci.yml` → **5**.
  Parsing the file by job: `backend: 45`, `backend-migrations: 20`,
  `backend-lint: 10`, `frontend: 15`, `sonarcloud: 15` — the three new ones are
  exactly the required jobs, and each carries an in-file justification against
  that job's measured steady state (median/p90/worst over the 41 successful
  runs), with `sonarcloud`'s 15m explained by its third-party dependency.

- [x] **R17 — the `backend` job comment no longer over-claims.**
  The staged `ci.yml` diff replaces the unconditional claim with: the wrapper
  "turns *some* hangs into a failing step … it worked on job 110381880180 (step
  failed at 30m08s, exit code 124, log published) and it did **not** work on
  jobs 110014916546 and 110405490008", plus the grace-window note. Exactly the
  three job ids R17 requires, in the required polarity.

- [x] **R18 — the armed-call assertion, the all-jobs assertion, and the removal.**
  `test_the_shutdown_watchdog_is_armed_from_the_hook_that_brackets_coverage`
  matches by AST: the `pytest_runtestloop` function node, its decorator
  (`wrapper=True` and `trylast=True`), the
  `faulthandler.dump_traceback_later` **call node** reached from that hook, its
  `exit=True` keyword, and the yield→return contract. Not a module mention — I
  proved that by mutation (below).
  `test_every_ci_job_carries_a_timeout_minutes_declaration` parses `ci.yml` by
  job and asserts `backend` is present by name before sweeping every job.
  `test_the_backend_job_still_carries_its_job_level_backstop` is **gone** from
  the suite — the only remaining occurrences of the name are a docstring
  reference explaining the replacement and a stale `.pytest_cache` nodeid file.
  `uv run pytest tests/test_suite_hygiene.py` → **11 passed**.

- [x] **R19 — the two mutations, reproduced.**
  Each applied to a scratchpad-backed copy, run, restored, and verified with
  `cmp`.
  (a) armed call deleted from `conftest.py` →
  `test_the_shutdown_watchdog_is_armed_from_the_hook_that_brackets_coverage`
  fails with the document's pasted text verbatim, at
  `tests/test_suite_hygiene.py:323`.
  (b) `sonarcloud`'s `timeout-minutes: 15` deleted →
  `test_every_ci_job_carries_a_timeout_minutes_declaration` fails with
  `these ci.yml jobs carry no timeout-minutes: ['sonarcloud']`, verbatim.
  Neither mutation is in the tree (`git diff` empty after restore).
  **Four extra mutations I added, all caught** — so the assertion is not
  paperwork: `exit=True` removed → fail; `return result` removed → fail;
  `trylast=True` removed → fail; the armed call turned into a *comment*
  mentioning `faulthandler` → fail. And deleting `backend`'s own
  `timeout-minutes: 45` → fail, naming `['backend']`.

- [x] **R20 — branch (a): root cause confirmed, with a test that fails on revert.**
  Exactly one branch present: the document has no `## Not found` section and
  §8 is the confirmed-cause branch.
  *The measurement re-derived.* I reverted the `ids=` keyword on a
  scratchpad-backed copy and ran a real collection: longest collected node id
  **2 097 259 characters** — the document's load-bearing figure, to the
  character — collection output **2 525 096 B** at **4 201** items, which is
  precisely the tree-dependent figure the document predicts for the tree as it
  stands. With the fix in place: longest id **286**, output **427 725 B** at
  4 201 items, again the documented figures.
  *The guard falsifies.* With `ids=` reverted,
  `test_no_collected_node_id_can_carry_a_payload` **fails** with the document's
  pasted output verbatim (`2097259 chars: …`, `tests/test_suite_hygiene.py:433`);
  with `ids=` restored it passes. The guard collects in a subprocess and carries
  a `MIN_COLLECTED = 4000` vacuity floor, so a broken collection cannot pass it.
  *The cost re-derived.* I downloaded only job `108767062588`'s own 8 MB log and
  parsed the runner timestamps, handling the BOM that follows each 2 MiB line.
  All five gaps round exactly as published:
  `15595→15596 4126.850 s = 68.7808 → 68.78`;
  `15596→15597 4127.926 s = 68.7988 → 68.80`;
  `15597→15602 4126.136 s = 68.7689 → 68.77`;
  `15602→15603 4125.872 s = 68.7645 → 68.76`;
  `15603→15608 4125.881 s = 68.7647 → 68.76`.
  Range **68.76–68.80 min** as stated, spread 2.06 s (document: 2.05 s), and
  lines 15596/15602/15608 are each 2 097 288 B + newline = **2 097 289 B**
  beginning `tests/test_project_report_brand…`, inside the warnings-summary
  section that opens at line 441 (`03:02:36.871Z`). The two code comments that
  quote `~68.8 minutes` and `68.76–68.80` are therefore accurate.

- [x] **R21 — gates.**
  `cd backend && uv run pytest` → exit **0**,
  `4163 passed, 38 skipped, 6341 warnings in 250.40s`,
  `Required test coverage of 90% reached. Total coverage: 94.30%`.
  `uv run ruff check .` → `All checks passed!` (exit 0);
  `uv run ruff format --check .` → `301 files already formatted` (exit 0).
  (The document records 4 159 cases; the tree has since gained APRAS-102's
  tests on `master`, hence 4 163. Not a discrepancy in the work.)

- [x] **R22 — no `frontend/` file modified.**
  `git diff --cached --name-only` lists exactly `.github/workflows/ci.yml`,
  `AGENTS.md`, `backend/tests/conftest.py`,
  `backend/tests/test_project_report_branding.py`,
  `backend/tests/test_suite_hygiene.py`, `docs/tasks/APRAS-119-findings.md`.
  Zero paths under `frontend/`.

## The unnamed staged file: `AGENTS.md`

`AGENTS.md` is staged and is named by no expected result. I read the change
against the findings document and against my own measurements. It is accurate
and proportionate:

- It softens "GitHub publishes **no logs for a cancelled job**" to "*usually*
  publishes no logs" and states 11 of 15 published none while 4 did — which I
  verified byte-for-byte via the logs `HEAD` requests, and which is the claim
  that mattered, since the root cause was read out of one of those four logs.
- It drops "a commit whose backend tree was byte-identical to one that had just
  passed in 10m57s" as the framing of the hang — the same withdrawal §7 makes,
  and the census shows 8 refs and 13 shas.
- It stops asserting that the `timeout` wrapper unconditionally turns a hang
  into a failing step with a log, naming the one job where it held and the two
  where it did not — the same three job ids R17 requires, and all three verified.
- It adds the fourth guard (the watchdog) with its known capture-teardown limit,
  and points at `test_no_collected_node_id_can_carry_a_payload` with the correct
  1024-character threshold.

Every number it states — 2 097 259 characters, ~68.8 minutes, 11 of 15, 4 of 15,
exit 124 on job 110381880180, `timeout = 300` with `timeout_method = thread` —
is supported by the findings document and, where re-derivable, by my own
measurements. It asserts nothing the document does not support.

## Blocking Findings

None.

## Suggestions

- The jobs API has stopped returning step records for job `108767062588` (the
  365-minute occurrence, now eight days old) while 2026-09-29 jobs still carry
  theirs. The document's per-occurrence step evidence for that one job is
  therefore no longer reproducible from the API, though its log — the evidence
  that actually carries §8 — is. A one-line note that step detail appears to
  age out, next to that row, would save the next reader a false alarm.
- §2's short-line byte column reads "≤ 218" while the raw log lines around the
  2 MiB entries measure 219 bytes including the 3-byte BOM that follows the
  oversized line. The figure is right under one convention and off by one under
  another; stating which (BOM excluded, newline included) would close it.
- The armed-window latency sits close to the rule's 12 s threshold and moves
  with machine load — I measured 5.91 s on an idle machine, which the rule would
  have answered with 120 s. The committed 150 s is the safe side and the
  document says so, but once the first CI run lands (R14's pending clause), it
  would be worth recording the runner's own latency next to the two laptop
  readings, since that is the number the grace period actually has to cover.
- `backend/.pytest_cache/v/cache/nodeids` still carries the removed
  `test_the_backend_job_still_carries_its_job_level_backstop` entry. Harmless and
  gitignored; noted only so a future grep for the name is not misread.

## What I exercised

Re-ran the full census query and a from-scratch reimplementation of the detector
over all 102 non-success runs (15 occurrences, every field matching); verified
`filter=all` and the non-`null` step test by differential query; re-derived all
five per-line gap figures from job `108767062588`'s own 8 MB log with BOM-aware
parsing; confirmed log availability and sizes by `HEAD`; confirmed exit 124 and
the timeout annotations on all 15 jobs; re-derived the 2 097 259-character node
id by reverting `ids=` on a scratchpad-backed copy and confirmed
`test_no_collected_node_id_can_carry_a_payload` fails on revert and passes with
the fix; ran six mutations (the two required plus four of my own) against the
two hygiene assertions, each caught; reproduced the watchdog firing on a
deliberate wedge (`Timeout (0:02:30)!`, exit 1 at 151 s) and deleted the probe;
re-ran the §4a signal probe in both forms; re-ran `-W error::ResourceWarning`;
and ran the full suite, the hygiene module and both ruff gates green. Worktree
restored and verified with `cmp` and `git diff` after every cycle.
