# APRAS-119 — code review

**Reviewer:** peer code review agent
**Subject:** `git -C /Users/heitor/workspace/apras/.claude/worktrees/agent-a768c37eeecc47980 diff --cached`
**Diff size:** 5 files, +1339 / −13 (`ci.yml` +41/−7, `conftest.py` +104, `test_project_report_branding.py` +14, `test_suite_hygiene.py` +233/−6, `docs/tasks/APRAS-119-findings.md` +947 new)
**Spec:** `docs/tasks/APRAS-119-spec.md` (735 lines, present only in the main checkout)
**Date:** 2026-10-05

---

## 0. Worktree position — report, not a finding

The worktree is on `25e9dc6` (`fix(APRAS-120): keep datetime columns naive and
serialise the API in UTC`), branch `worktree-agent-a768c37eeecc47980`.

```
$ git rev-list --left-right --count master...HEAD
5	0
```

**It is 5 commits behind `master` (`ab54bf8`) and 0 ahead.** The missing commits
are `ab54bf8` (APRAS-123), `2124432` (APRAS-98), `e1d19f2` (APRAS-111),
`1f0079b` (APRAS-97), `2cb0d48` (APRAS-91).

Per instruction I did not rebase. The risk here is low and worth stating
precisely, because it is not the usual one: none of the five commits touches
`.github/workflows/ci.yml`, `backend/tests/conftest.py`,
`backend/tests/test_suite_hygiene.py` or
`backend/tests/test_project_report_branding.py`. The one overlap that matters is
indirect and benign — `e1d19f2` (APRAS-111's "tests that prove nothing" audit)
adds `docs/audits/APRAS-111-test-suite-audit.md`, which the new hygiene test's
docstring cites by path. That citation is to a file that exists on `master`, so
it resolves after a rebase. The staged work should still be rebased onto
`ab54bf8` before it lands, and the full suite re-run there, because the node-id
guard collects the **whole** tree in a subprocess and five unmerged commits of
test changes shift the collected count (my collection sees 4197; `MIN_COLLECTED`
is 4000, so there is ample headroom — but the figure is tree-dependent by
construction).

---

## 1. The headline claim — verified from primary evidence, not from the document

This is the part I spent most of the review on, and it holds up to an unusually
high standard. I reproduced every load-bearing number myself.

### 1.1 The node id, measured on both sides of the fix

Post-fix, a real collection on the staged tree:

```
$ cd backend && uv run python -m pytest --collect-only -q -p no:cacheprovider -o addopts=
$ wc -c  → 427396
$ awk '{if(length>m)m=length}END{print m}'  → 286
$ grep -c '^tests/'  → 4197
```

**427 396 bytes and 286 characters — both exactly as the findings document
claims.**

I then copied `test_project_report_branding.py` to the scratchpad, deleted the
`ids=` line, and re-collected:

```
$ wc -c  → 2524767
$ awk '{if(length>m)m=length}END{print m}'  → 2097259
```

**2 097 259 characters — exact.** The collection byte figure differs from the
document's `2 524 431` by 336 bytes; see Suggestion 2 for why, and why it is not
a defect.

File restored and verified with `cmp` (identical).

### 1.2 The 2 MiB line exists in the real log, in the warnings summary

I fetched job `108767062588`'s published log (8 055 084 bytes — the document's
`content-length: 8 055 090` is the HTTP header for the gzip-free blob, and I
confirmed that header separately) and measured it directly:

```
total lines: 15608
longest lines (bytes, 1-based lineno): [(2097288, 15608), (2097288, 15602), (2097288, 15596), (522, 130), (276, 3702)]
warnings summary at line 441: 2026-09-28T03:02:36.8711782Z ====== warnings summary ======
```

Lines **15 596, 15 602 and 15 608** are each 2 097 288 characters as
`splitlines()` reports them — i.e. **2 097 289 bytes with the line terminator,
exactly the document's figure** — and each one begins
`tests/test_project_report_branding.py::test_a_logo_the_product_would_no…`. They
are inside the `warnings summary` section, which opens at `03:02:36.871Z`.

Two independent cross-checks that I did not expect to line up as well as they do:

- the pytest step started at `02:45:10Z` (jobs API); the warnings summary opens
  at `03:02:36.871Z`, which is **17m26.9s** later — the document's "tests green
  in 17m26s, then frozen 0.5 s into the warnings summary", corroborated to under
  a second from a source independent of the summary line;
- the job ran `02:45:04Z → 08:50:04Z` = **exactly 365.00 min**, and the last
  2 MiB line is stamped `08:46:30.048Z`, 3m34s before the kill — i.e. the job
  died partway into the fourth such line. Coherent.

### 1.3 The 68.8-minute arithmetic

I recomputed all five gaps from the timestamps, which I also confirmed against
the real log (every one matches the log to the millisecond):

| gap | actual | document |
|---|---|---|
| 15 595 → 15 596 | 68.781 min | 68.78 ✓ |
| 15 596 → 15 597 | 68.799 min | 68.80 ✓ |
| 15 597 → 15 602 | 68.769 min | 68.77 ✓ |
| 15 602 → 15 603 | 68.765 min | **68.81 ✗** |
| 15 603 → 15 608 | 68.765 min | 68.77 ✓ |

**One cell is wrong:** `68.81` should be `68.76` (an error of 2.7 s on a
68.8-minute figure), and the stated range "68.77–68.81 minutes" should be
"**68.76–68.80**". The conclusion is unaffected and is in fact *tighter* than
claimed — all five gaps fall within 2.0 s of each other, which is a stronger
platform-constant signature than a 2.4 s spread. The wrong range is replicated
into two committed comments. Suggestion 1.

Total: 343.88 min of gaps + 17.45 min of tests = 361.3 min, against a 365.00 min
job. Internally consistent.

### 1.4 The intermittency — the load-bearing half, and it holds

This is the claim I was least willing to take on trust, since a mechanism that
explains the hang but not its on-again-off-again pattern is not a root cause. I
checked it against pytest's actual source in the worktree's venv
(`_pytest/terminal.py`).

`summary_warnings` groups warning reports **by message**, then:

```python
if len(locations) < 10:
    return "\n".join(map(str, locations))   # every location printed in full
counts_by_filename = Counter(str(loc).split("::", 1)[0] for loc in locations)
```

and `WarningReport.get_location` (terminal.py:367) returns **`self.nodeid`
first**, falling back to `fslocation` only when there is no nodeid.

So the chain is mechanically exactly as the document describes it: any warning
attributed to that test item prints its *full node id* — 2 MiB — provided fewer
than 10 locations share the warning's message. The pre-`68f249a`
`ResourceWarning: unclosed database` messages each embed a distinct
`sqlite3.Connection` repr, so each forms its own singleton group and is never
collapsed; and *which item* a leaked connection's warning lands on is decided by
when the garbage collector closes it. **GC timing therefore does decide whether
the 2 MiB line is printed**, which is precisely what a byte-identical tree
passing in 10m57s and wedging twice requires. Verified, not asserted.

The three 2 MiB lines in the log are three such singleton groups, consistent
with the mechanism.

### 1.5 The apparent cure on 2026-09-30

Last of the 13 pre-fix occurrences is job `109926009179` at `2026-09-30 14:09Z`;
`68f249a` landed `16:40Z`. **2h31m** — as stated. And the mechanism predicts the
cure rather than coinciding with it: no flood → no singleton per-item warning
groups → the id is never printed, while the id itself survived in the tree. The
document is explicit that the hazard was still live on `cd8de18`, which my own
reverted-tree collection confirms.

**Verdict on the root cause: confirmed.** It explains the signature, the
intermittency, the cure, the 8-ref spread (the payload lives in `backend/tests/`,
so it is present even on frontend-only refs) and the time clustering (four bot
PRs running the same tree). I could not find a fact in the census it fails to
account for.

---

## 2. The six escalations

### (1) The three spec contradictions — all three departures are right

**(i) §4a's "no log was published" is wrong, and demonstrably so.** I checked
the logs API myself rather than reading the document's quotes:

```
110014916546: log published, 33 956 695 bytes (32.4 MiB)
110405490008: log published, 33 957 937 bytes (32.4 MiB)
109628456192: log published, 41 473 bytes / 476 lines
108767062588: log published, 8 055 090 bytes
109926009179 / 109644454563 / 109712407577 → blob 404 "The specified blob does not exist."
```

Output stop points, by ranged read of the tails:

- `110014916546` last line `2026-09-30T18:07:18.2521440Z`, step started
  `17:37:11Z` → **30m07s** ✓
- `110405490008` last line `2026-10-01T14:31:31.3072833Z`, step started
  `14:01:24Z` → **30m07s** ✓

And the `KeyboardInterrupt` claim, which required a 12 MiB ranged read to reach
back far enough (the log is ~45 000 lines/second at that point):

```
2026-09-30T18:07:16.2442326Z KeyboardInterrupt
2026-09-30T18:07:16.2443132Z KeyboardInterrupt
```

**Twice, at 18:07:16.244Z, exactly as reported.** So SIGINT *did* reach pytest
and the step still never completed. The spec was wrong on a point of fact, the
developer measured it, wrote the measurement, and — correctly — did **not** land
a signal-propagation fix in `ci.yml`, because the spec made that amendment
conditional on §4a being *confirmed* and the evidence clears the hypothesis as
stated while explicitly declining to clear the CI case. I checked the staged
`ci.yml`: the pytest invocation is untouched; only comments and three
`timeout-minutes` were added. Right call.

I also confirmed the `109628456192` orphan-process lines verbatim (its log is
41 KB, so I read it in full rather than ranged) and that it contains **zero**
pytest output — the document's "unknown" verdict for that occurrence is the
honest one.

**(ii) Reversing §2's demotion of `output volume` is right**, and the argument is
the sharpest thing in the document: the spec reasoned that an unchanged backend
tree on a frontend-only ref *removes* support from a volume explanation, when a
tree-**constant** cause is exactly what a set spanning frontend-only refs
predicts. A 2 MiB payload on one line is a volume fault that the spec's
prescribed probe (captured stdout, largest line) structurally could not see,
because on a green run the id is not in stdout at all. The developer ran the
prescribed probe, recorded its `cleared` result, and then explained why the probe
was looking in the wrong place. That is the right way to disagree with a spec.

**(iii) Departing from R7's `runner-or-image` is right.** The document records the
spec's reading verbatim first, then reverses it on measurement, and leaves the
row at `untestable without a recurrence` with *less* support than before — the
only verdict that row is allowed to carry. Nothing is quietly dropped.

All three contradictions are correct. Per the dispatch instruction I say so
explicitly: **the spec is wrong in these three places and this change records it
as wrong.** None is a blocking finding.

### (2) `SHUTDOWN_GRACE_SECONDS = 150` — I would ship 150 too

R13's rule is mechanical and the developer applied it as written: 12.95 s > 12 s,
so `ceil(129.5 / 30) × 30 = 150`.

I agree, and not only on mechanics. The question "should a noisy measurement
0.95 s over a cliff drive the committed constant?" has a cheap answer here
because **both values are safe**: projected CI latency is ~26 s (2× the laptop),
so 120 s is 4.6× and 150 s is 5.8× it, against a 30-minute step budget either
way. When the difference is immaterial and the rule is written down, following
the rule beats re-litigating the threshold — and the alternative (round *down*
because the machine was loaded) biases toward the value that makes a green suite
fail. The document records the caveat rather than smoothing it, and
`conftest.py` prints the latency on every run so the next person re-measures for
free. **Ship 150.**

The residual risk is worth naming for QA: with `exit=True`, a post-test-loop
window exceeding 150 s on a loaded runner converts a green suite into exit 1.
That is the one thing the first CI run after this lands must confirm, and the
document correctly flags that observation as unavoidably pending.

### (3) The `faulthandler` capture limit — documenting is enough, and the watchdog is worth more than the escalation implies

The analysis is technically correct: `faulthandler` stores the *file descriptor*,
pytest's default capture is fd-level, so a dump firing before capture teardown
writes into the capture temp file and dies with the process, while one firing at
or after interpreter shutdown finds fd 2 restored and reaches the step log. The
demonstrated wedge is the latter shape, and the quoted dump includes the main
thread parked in `threading._shutdown` — the frame nothing else in this repo can
produce.

The gap is real and worth stating plainly: a wedge in the *early* part of the
armed window — the `coverage.xml` write or the warnings summary, which is where
the root cause actually lived — loses its stack. But it does **not** lose the
backstop. `exit=True` still terminates the process, so a six-hour silent
cancellation becomes a bounded failing step that keeps its log and its summary
line. The watchdog's primary value (turn an undiagnosable cancellation into a
diagnosable failure) survives the limit; only its secondary value (a stack for
the first ~0–2 s of the window) is conditional.

`capman.suspend_global_capture()` + `os.dup(2)` is real added complexity against
a window that is seconds long, in a task that already found and fixed the cause.
**Documenting is the right call here**, and the comment in `conftest.py` says it
rather than hiding it. I would track the engineered version as a low-priority
follow-up, not redo it now.

### (4) The nested whole-tree collection — right tradeoff

An AST-only check cannot measure the thing that matters. The 2 097 259-character
id is not a literal anywhere in the source; it is what *pytest* builds from
`b"x" * (LOGO_MAX_FILE_SIZE + 1)`, and only pytest builds it. An AST guard would
have to re-implement `idmaker`, and a guard that re-implements the thing it
guards is the failure mode APRAS-111 catalogued.

The cost is honest: I measured the subprocess collection at **2.5 s** wall
(`2.02s user`), against a ~290 s suite — under 1%. It follows
`test_assert_no_skips.py`'s established precedent in this same repo
(`subprocess.run` + bounded `timeout=`), the `timeout=300` is explained by a
comment that names the exact hazard (`capture_output=True` with no timeout blocks
until the pipes close — the hang this module exists to prevent), and
`MIN_COLLECTED = 4000` is a genuine vacuity floor, not decoration. Correct
choice, correctly bounded.

### (5) `AGENTS.md` — fix it here, not separately

I read the passage. `AGENTS.md:247–265` is now wrong in three ways, two of which
this change itself disproves:

- line 250–252 still says `Backend Tests` was "cancelled at 55m0s **twice in a
  row** (on a commit whose backend tree was **byte-identical** to one that had
  just passed in 10m57s)". The census found **15 occurrences on 8 refs**, and the
  spec withdrew the byte-identical framing outright;
- line 248–250 still asserts GitHub publishes "**no logs for a cancelled job**"
  as an absolute. The census measured 4 of 15 cancelled jobs publishing logs —
  including the 8 MB log this task's entire root cause rests on;
- guard 1 (lines 254–258) still asserts unconditionally that the `timeout`
  wrapper "fails a **step**, and a failed step keeps its log" — **the exact
  sentence R17 required be corrected in `ci.yml`**, left standing in the file
  agents actually read. `AGENTS.md` also does not mention the new watchdog at
  all, so its "three guards" list is stale.

My answer to the escalation: **fix it in this task.** The reasoning is not that
the spec permits it (it doesn't list the file) but that the stale text now
actively misdirects: an agent reading `AGENTS.md` after this lands is told the
hang is an undiagnosable runner mystery on a byte-identical tree, when the cause
is known, fixed and guarded. Correcting the same overstatement in `ci.yml` while
leaving it in the canonical doc is the inconsistency, and it is a few sentences
of work in the change that produced the knowledge.

I am **not blocking** on it: it is documentation accuracy, outside the spec's
"Files touched", and the developer escalated rather than deciding silently, which
is what should happen. It is Suggestion 3 so the orchestrator harvests it.

### (6) `backend/.env` — clean

```
$ git check-ignore -v backend/.env
backend/.gitignore:12:.env*	backend/.env
$ git diff --cached --name-only | grep .env   → (nothing)
$ cat backend/.env
SECRET_KEY=test-secret-key-for-ci
POSTGRES_URL=postgresql://postgres:password@localhost/apras
```

Genuinely gitignored (`.env*` in `backend/.gitignore`), **not staged**, and
contains no real credential: `SECRET_KEY` is verbatim the fake value from
`ci.yml`'s `env:` block, and the DSN points at `localhost` with the stock
`postgres:password`. No production host, no production secret. Left in place as
instructed. No finding.

---

## 3. The guards bite — three mutations reproduced, plus one of my own

Every mutation: pristine copy to the scratchpad first, mutate, run, restore,
`cmp`.

### (a) armed `dump_traceback_later` call deleted from `conftest.py`

```
FAILED tests/test_suite_hygiene.py::test_the_shutdown_watchdog_is_armed_from_the_hook_that_brackets_coverage
tests/test_suite_hygiene.py:323: AssertionError
1 failed, 10 passed
```

Fails by the named mechanism — line 323 is the `assert armed` on the **AST call
node**, not a string match. The comment block mentioning `faulthandler` by name
was left untouched by the mutation and the test still failed, which is the exact
property R18 demanded and the exact property the nineteen tests in APRAS-111's
audit lacked. Restored, `cmp` identical.

### (b) one `timeout-minutes:` deleted from `ci.yml`

```
E  AssertionError: these ci.yml jobs carry no `timeout-minutes`: ['frontend'].
FAILED tests/test_suite_hygiene.py::test_every_ci_job_carries_a_timeout_minutes_declaration
```

Fails **naming the job**. Restored, `cmp` identical.

### (b2) my own addition — `backend`'s own `timeout-minutes: 45` deleted

```
E  AssertionError: these ci.yml jobs carry no `timeout-minutes`: ['backend'].
```

I ran this because R18 requires that no coverage be lost in replacing the old
backend-specific test. It is not lost: the sweep catches `backend` by name.

### (c) the `ids=` fix deleted

```
E  AssertionError: these collected node ids exceed 1024 characters, so pytest built them
   out of their parameters instead of out of a name: ['2097259 chars:
   tests/test_project_report_branding.py::test_a_logo_the_product_would_not_accept_...'].
```

Fails **quoting the character count**, 2097259. One detail worth praising: the
whole failure output is **4 195 bytes**, because the message truncates the
offending id to 80 characters. A guard against a 2 MiB line that emitted a 2 MiB
line when it tripped would have reproduced the fault it exists to prevent. That
was thought about.

Restored, `cmp` identical.

### R18's removal requirement

```
$ grep -rn test_the_backend_job_still_carries_its_job_level_backstop backend/tests/
backend/tests/test_suite_hygiene.py:240:   This *replaces* `test_the_backend_job_still_carries_its_job_level_backstop`,
```

**Removed, not kept** — the only surviving mention is the explanatory comment in
its replacement. (It also appears in `backend/.pytest_cache/` and
`backend/test-results.xml`, both gitignored run artifacts, not source.) And the
removal is justified rather than asserted: the old assertion searched the whole
file for one `^\s*timeout-minutes:\s*\d+\s*$`, so with four declarations
remaining it would have passed mutation (b). Correct to delete.

---

## 4. R13's prescribed shape — checked line by line

```python
@pytest.hookimpl(wrapper=True, trylast=True)
def pytest_runtestloop(session):
    result = yield
    armed_at = time.monotonic()
    atexit.register(_report_armed_window_latency, armed_at)
    faulthandler.dump_traceback_later(SHUTDOWN_GRACE_SECONDS, exit=True)
    ...
    return result
```

- `wrapper=True, trylast=True` ✓
- armed **after** the yield ✓
- `exit=True` ✓
- **returns the value it received from `yield`** ✓ — `result = yield` … `return result`

And the hygiene test pins that last contract specifically rather than trusting
it: it collects the `Name` targets of `Assign` nodes whose value is a `Yield`,
collects the `Name`s of `Return` nodes, and asserts `set(yielded) <= set(returned)`.
A wrapper that swallowed the return value would fail. That is the line the
dispatch asked me to check, and it is both correct and guarded.

---

## 5. The remaining checks

| check | result |
|---|---|
| `grep -cE '^[[:space:]]+timeout-minutes:' .github/workflows/ci.yml` | **5** ✓ |
| the three new ones on `backend-lint`, `frontend`, `sonarcloud` | ✓ (10 / 15 / 15, lines 206 / 248 / 290) |
| each justified against observed duration | ✓ — `backend-lint` median 0.17m worst 1.85m → 10m; `frontend` worst 3.37m → 15m; `sonarcloud` worst 2.32m → 15m with a stated reason for 15 over 10 (third-party upload tail) |
| R17: `backend` comment no longer unconditional | ✓ — now "turns *some* hangs into a failing step… it is important not to overstate which", naming `110381880180` as the case that worked and `110014916546`/`110405490008` as the two that did not |
| branding test payload and assertions unchanged apart from `ids=` | ✓ — the diff is **purely additive** (+14/−0: a comment block and the `ids=` line). Payload is still `b"x" * (TenantService.LOGO_MAX_FILE_SIZE + 1)` and the test still asserts the product refuses it |
| the three ids map to the right cases | ✓ — `logo.svg`→`an-svgs-active-content`, `logo.bin`→`an-untyped-suffix`, oversized→`past-the-size-ceiling`, in parameter order |
| no signal-propagation fix in `ci.yml` | ✓ correct — §4a cleared, and the spec made the amendment conditional on `confirmed` |
| the deliberate wedge probe not committed | ✓ `backend/tests/` contains no `*wedge*` file |

### Gates I ran

| gate | result |
|---|---|
| `uv run pytest` (full suite) | **4159 passed, 0 failed, 38 skipped** ✓ |
| `coverage.xml` root `line-rate` | **0.9431** → 94.31% against the 90% gate ✓ |
| `uv run ruff check .` | `[]` — zero findings ✓ |
| `uv run ruff format --check .` | `301 files already formatted` ✓ |
| `uv run pytest tests/test_suite_hygiene.py` | **11 passed** ✓ |
| `uv run pytest tests/test_project_report_branding.py` | 39 passed ✓ |

I ran the full suite despite the ~5-minute cost, because the watchdog arms on
every run and I was not willing to approve an unconditionally-armed `exit=True`
timer on the developer's measurement alone. Every reported figure reproduced
exactly, including the 4159/38 split and the 0.9431 line rate.

### Worktree left as found

```
M  .github/workflows/ci.yml
M  backend/tests/conftest.py
M  backend/tests/test_project_report_branding.py
M  backend/tests/test_suite_hygiene.py
A  docs/tasks/APRAS-119-findings.md
```

Five paths staged, nothing unstaged, `backend/.env` in place. No stray probe
processes (`pgrep -fl 'time.sleep(600)|apras119'` → none). No `git stash` was
run; nothing was added, unstaged, committed or pushed; no CI run was triggered;
the other worktrees were not touched.

---

## 6. Code quality assessment

**Architecture and patterns.** The hygiene module's existing idioms are followed,
not reinvented: `_ci_jobs()` parses by indentation for the same stated reason
`_run_blocks` does (no YAML dependency in the backend), the subprocess collection
mirrors `test_assert_no_skips.py` including the bounded-timeout comment, and the
AST helpers match the module's existing style. Module boundaries are respected —
nothing under `app/` is touched, which is right for a fault that lived entirely
in test parametrisation.

**KISS/YAGNI.** The fix is a three-element `ids=` list. For a six-hour CI hang
across 15 jobs, that is as small as a root-cause fix gets, and the developer
resisted the available temptations: no fixture rewrite, no reduction of the 2 MiB
payload (which would have weakened a real boundary test), no speculative
signal-propagation change on a cleared hypothesis, no capture-suspension
machinery for a seconds-long window. The one piece of genuinely new machinery —
the watchdog — is mandated by the spec and lands "whether or not the cause is
found".

**Test quality.** This is the strongest part. Three guards, each verified by
mutation to fail by its named mechanism, each with a vacuity floor against the
way this kind of test usually rots: `MIN_COLLECTED = 4000` so a broken collection
cannot pass by finding no offenders; `assert "backend" in jobs` so a scan that
found no jobs cannot pass by sweeping an empty dict; AST call-node matching so a
comment cannot satisfy the watchdog assertion. Failure messages name the
offending job, the character count and the remedy. This is the opposite of the
nineteen tests APRAS-111 catalogued.

**Security.** Nothing touches auth, input validation, SQL or secrets. The one
new subprocess call has a fixed argument vector (no shell, no interpolation) and
a bounded timeout. `backend/.env` is gitignored and credential-free. No concerns.

**Comments.** Unusually good — every committed constant carries the measurement
and the arithmetic that produced it (`SHUTDOWN_GRACE_SECONDS`, all three new
`timeout-minutes`, `MAX_NODE_ID`), and the known limit of the watchdog is written
down in the code rather than only in the findings document. The `ci.yml` comments
replace an overstatement with a conditional claim plus the job ids that bound it.

**Spec compliance.** Every expected result I could check mechanically is met. One
is unavoidably deferred by construction — "the first CI run after the watchdog
lands" — and the document says so explicitly rather than inventing a figure.
Flagged for QA below.

---

## Suggestions

1. **Fix the one wrong gap figure.** `docs/tasks/APRAS-119-findings.md` §8's
   timestamp table gives the `15 602 → 15 603` gap as **68.81 min**; the log's own
   timestamps (`06:28:58.295Z → 07:37:44.167Z`) give **68.76 min**. The stated
   range "68.77–68.81 minutes" should be "**68.76–68.80 minutes**". The same wrong
   range is replicated in two committed comments — `.github/workflows/ci.yml`
   (backend pytest step, "five consecutive gaps of 68.77-68.81 min") and
   `backend/tests/test_project_report_branding.py`'s `ids=` comment. The
   conclusion is unaffected and in fact strengthened: all five gaps fall within
   2.0 s of each other. Worth correcting because APRAS-123 just set the precedent
   in this repo that published figures must be re-derivable.

2. **Note that the before/after collection byte figures are from different tree
   snapshots.** §8's table pairs `2 524 431 B` (before) with `427 396 B` (after).
   I reproduce `427 396` exactly but get `2 524 767` for the reverted tree — a
   336-byte difference, which is the two *net new* hygiene test node ids (three
   added, one removed) that did not exist when the pre-fix reading was taken: the
   document's own `4195 tests collected` against today's `4197`. Not a defect —
   the load-bearing figure (2 097 259 characters) is exact — but a one-line note
   that the pre-fix byte count predates the new hygiene tests would stop the next
   reader from thinking they had failed to reproduce it.

3. **Correct `AGENTS.md:247–265` in this task rather than tracking it
   separately.** Three claims there are now stale, two of them disproved by this
   very change: (a) line 250–252's "cancelled at 55m0s **twice in a row** on a
   commit whose backend tree was **byte-identical**" — the census found 15
   occurrences on 8 refs and the spec withdrew that framing; (b) line 248–250's
   absolute "GitHub publishes **no logs for a cancelled job**" — 4 of the 15
   publish logs, including the 8 MB one this root cause rests on; (c) guard 1's
   unconditional "It fails a **step**, and a failed step keeps its log", which is
   the exact sentence R17 required be corrected in `ci.yml` and which is left
   standing in the file agents actually read. `AGENTS.md`'s "three guards" list
   should also become four, naming the `faulthandler` shutdown watchdog, and
   could reference the node-id guard. Left as a suggestion only because it is
   documentation outside the spec's "Files touched" — but it should be fixed
   before this lands, not after, since an agent reading it post-merge is told the
   hang is an unsolved runner mystery.

4. **Rebase onto `ab54bf8` and re-run the full suite before landing.** The
   worktree is 5 commits behind. No commit touches any of the five staged paths,
   so a clean rebase is expected, but `test_no_collected_node_id_can_carry_a_payload`
   collects the whole tree and three of the five commits add tests — re-run the
   module (not just the full suite) after rebasing to confirm the collection
   count stays above `MIN_COLLECTED = 4000`. It sees 4197 today.

5. **Track the watchdog's capture-teardown gap as a low-priority follow-up.** A
   dump firing in the *early* armed window — the `coverage.xml` write or the
   warnings summary, which is where the root cause actually lived — lands in the
   fd-level capture buffer and is lost, so the stack is only guaranteed for the
   interpreter-shutdown shape. `exit=True` means the *backstop* still works in
   both cases (bounded failing step with a readable log), so this is a
   degradation of the secondary benefit only. The engineered fix is
   `capman.suspend_global_capture()` + `os.dup(2)`, which is not worth inlining
   here.

6. **For QA:** one expected result cannot be satisfied by this change — "the
   first CI run after the watchdog lands: its run id, its `Backend Tests` job
   conclusion, and whether the 90% coverage gate passed". The document records it
   as explicitly **pending** because the task deliberately triggers no CI run.
   That is the correct handling, but it means the 150 s grace period has never
   been exercised on a loaded ubuntu runner. Projected CI armed-window latency is
   ~26 s (2× the measured 12.95 s), giving 5.8× headroom, so the risk is low —
   but the findings document should be updated with that run's id once it exists,
   and a spurious `exit=1` on a green suite is the failure mode to watch for.

---

VERDICT: APPROVED

Blocking findings: None.
