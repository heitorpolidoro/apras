# APRAS-93 — code review, round 2

Reviewer: Meridian code reviewer. Date: 2026-10-05.
Worktree: `/Users/heitor/workspace/apras/.claude/worktrees/agent-a7a31a09fc3ca4bf4`.

## What was reviewed, and how

This task ships no production code, so "review the code" was read as: execute the
harness and check every published figure against what the harness actually
produces. Nothing below is taken from the developer's round-2 report; every
number marked "measured" is from a run I made in this session.

### Worktree state, confirmed

```
git log --oneline -1   -> ea37e9a docs(APRAS-122): record the uv-pin evidence and the action audit
git merge-base HEAD master -> ea37e9a...   git rev-parse master -> ea37e9a...
git diff --cached --name-only -> docs/tasks/APRAS-93-spec.md   (994 insertions, 1 file)
git diff --name-only -> (empty)
git status --porcelain -> A  docs/tasks/APRAS-93-spec.md   (and nothing else)
```

The worktree is at `ea37e9a`, no longer behind at `a33f26a`; `merge-base` equals
`master` equals `HEAD`, so the fast-forward happened and nothing diverged.
Exactly one staged path, nothing unstaged, nothing committed. Re-checked at the
end of the review: unchanged. `git stash list` is empty and I ran no `stash`,
no `add`, no `commit`.

### No production code ships — verified by hashing

`git show HEAD:<path> | shasum -a 256` against `shasum -a 256 < <path>`:

| path | result |
|---|---|
| `backend/app/api/v1/endpoints/public_projects.py` | IDENTICAL |
| `backend/app/services/project_report_service.py` | IDENTICAL |
| `backend/app/core/limiter.py` | IDENTICAL |
| `backend/pyproject.toml` | IDENTICAL |
| `backend/requirements.txt` | IDENTICAL (checked although ER13 does not name it) |

`git status --porcelain` over those four paths is empty. The only path in the
index is the spec. ER13 holds.

### Everything the harness reproduced

Run through `run.sh` (in-memory SQLite, synthetic `POSTGRES_URL` never
connected to; I confirmed no script reaches a remote host before running any of
them — `t_logo.py` reads one local file, `t_route.py`/`t_sweep.py` use
`TestClient` in-process).

**§1.1 (`t_sizes.py`) — byte figures exact, statement counts exact.**

| N | doc bytes | my bytes | doc stmts | my stmts | doc ms | my ms |
|---|---|---|---|---|---|---|
| 0 | 13,061 | **13,061** | 2 | **2** | 1.20 | 1.03 |
| 1 | 20,109 | **20,109** | 4 | **4** | 2.07 | 2.16 |
| 5 | 50,897 | **50,897** | 12 | **12** | 5.88 | 6.47 |
| 20 | 171,507 | **171,507** | 42 | **42** | 22.39 | 25.67 |
| 60 | 530,607 | **530,607** | 122 | **122** | 107.26 | 112.16 |
| 200 | 1,738,448 | **1,738,448** | 402 | **402** | 440.16 | 447.66 |

Per-project slope reproduced exactly: 13,061 → 20,109 → 27,161 → 34,213 B,
i.e. +7,048 / +7,052 / +7,052. Wall clocks run 0–15% above the document's,
inside the ±15% band §1.3.1 declares for itself.

**The shell law (`fixture_probe.py`).** 13,031 / 13,039 / 13,050 / 13,061 B for
tenant names of 1 / 9 / 20 / 31 characters — all four exact, so
`13,030 B + len(tenant name)` holds. Per-character sensitivities exact too:
project description +1, bulletin body +3, photo URL +9, milestone title +6 B.

**§1.2 (`t_route.py`).** 2 / 4 / 6 / 12 / 42 / 122 / 402 statements at
N = 0/1/2/5/20/60/200 — `2N + 2` at all seven values, through the real route,
HTTP 200 asserted. The six-statement trace at N = 2 matches the document's list
in order and in kind (tenant, construction_project, project_update,
project_milestone, project_update, project_milestone), so the "the handler's
slug lookup adds no statement" observation reproduces.

**§1.3 byte identity.** 171,507 B in all three states at 20 projects and
1,738,448 B in all three at 200 — reproduced, including in a single process
running `cold,eager,warm` where the set is genuinely three-element.

**§1.3 statement counts per state.** cold 42 / warm 2 / eager 4 at 20; cold 402
/ warm 2 / eager 4 at 200. Exact.

**§1.3's paired cold-vs-eager — the round-1 finding is resolved.** Two
independent 200-project runs and one 20-project control, each 12 counted pairs
after 2 discarded, ABBA-interleaved:

| run | cold median | eager median | median paired diff | eager faster by | eager wins |
|---|---|---|---|---|---|
| 200, mine (reviewA) | 447.4 ms (436.1–488.2) | 396.7 ms (386.2–437.2) | **+49.7 ms** (+32.1 … +92.5) | **11.3%** | **12 / 12** |
| 200, mine (reviewB) | 458.7 ms (437.1–504.8) | 397.2 ms (388.0–447.6) | **+57.8 ms** (+15.9 … +96.5) | **13.4%** | **12 / 12** |
| 20, mine (control) | 27.0 ms (25.1–29.3) | 14.8 ms (14.0–17.1) | **+11.7 ms** (+9.8 … +14.6) | **45.2%** | **12 / 12** |

The sign the document now publishes is the sign I measure, the magnitude falls
inside its published 8.9–15.9% band at 200, and the 20-project control is in the
same place (45% against the document's 41%). **The round-1 blocking finding — the
sign-reversed `selectinload` correction — is resolved.** 24 of 24 paired
repetitions at 200 projects went to eager in my runs, on top of the developer's
44 of 48.

**§1.3.1's blocked design does flip the sign (`blocked.py`, 8 trials, mine):**

| trial | cold | eager | reported verdict |
|---|---|---|---|
| 1 | 440.3 | 390.4 | eager faster +11.3% |
| 2 | 435.9 | 388.8 | eager faster +10.8% |
| 3 | 440.6 | 417.4 | eager faster +5.3% |
| 4 | 482.9 | **1342.2** | **COLD faster, −177.9%** |
| 5 | **1835.1** | 441.4 | eager faster +75.9% |
| 6 | 445.0 | 395.3 | eager faster +11.2% |
| 7 | 440.2 | 388.7 | eager faster +11.7% |
| 8 | 435.1 | 391.5 | eager faster +10.0% |

8 trials, 1 sign reversal, and a second trial off by +76 points. The claim that a
blocked design cannot resolve this effect and will occasionally publish the
opposite conclusion **reproduces**, and more violently on my machine than on the
developer's. §1.3.1's design rule stands on executed evidence.

**§1.5 (`t_dims.py`) — byte figures exact.** Dimension one: 19,540 / 19,655 /
20,115 / 25,255 / 43,005 / 66,805 B at 1 / 2 / 6 / 50 / 200 / 400 open fronts,
slopes 115.0 / 115.0 / 116.6 / 117.9 / 118.5 B, statement count 4 at every row.
Dimension two: 20,976 / 31,309 / 54,070 / 168,471 B at 0 / 4 / 20 / 100 leaves
per milestone, B/leaf 129.2 / 82.7 / 73.7. 168,471 / 171,507 = **0.982**, so the
0.98× the document publishes (and the restraint of calling it an
order-of-magnitude claim rather than an inequality) is correct.

**§1.6 (`t_logo.py`) — every figure exact.** 108,018 B on disk; base64 144,024 B;
`data:` URI 144,046 B; worst case 2,796,226 B at the 2 MiB ceiling and 699,074 B
at 512 KiB; `LOGO_MAX_FILE_SIZE = 2097152`; uploads 9,859 regular files / 8,090
embeddable, largest 108,018 B in both, zero over 512 KiB in both. `_logo_html`
emits 0 B without `logo_url` and 108 B with it (20,109 → 20,217 B response,
0.53%); the emitted tag is verbatim what the document prints, contains no
`data:`, and 47 + 21 + 9 + 31 = 108 checks. The historical embed share comes out
at 144,046 of 164,155 B = **87.7%**, matching.

**§1.7 — verified directly.** `importlib.metadata.version("anyio")` = 4.14.2;
`current_default_thread_limiter().total_tokens` = **40**. Both handlers are
`def`: `public_projects.py:102 def get_public_projects_report` (no `request`
parameter) and `projects.py:130 def get_projects_report`. The arithmetic checks:
40 / 0.0232 = 1,724/s and 40 / 0.6 = 67/s.

**§5 (`t_sweep.py`).** 160 statements on both arms in all three trials
(= 20 × (2·3 + 2)); 684,180 B equal to the byte on every arm of every trial; the
sign flips between my trials too (same-slug 105.6 / 105.5 / 107.3 ms against
distinct-slug 105.6 / 115.3 / 104.3 ms). The finding — no cache-shaped signal,
and the comparison is not asserted from one pair of numbers — reproduces. My
absolute times run ~105 ms where the document reports 80.9 ms, inside the
80.9 → 127.5 ms spread the document itself publishes; the derived ~245
reports/s and 8.4 MB/s are correct arithmetic on the document's own 81.5 ms
(684,180 / 0.0815 = 8.39 MB/s = 8.00 MiB/s, both given, unit slip corrected).

**§1.4's honesty check.** The document says nothing is listening on
`localhost:5432`, `5433` or `55432`, so the 0.219 ms loopback anchor is
"measured once, not re-verified this round". I probed all three with a Python
socket: `ConnectionRefusedError` on each. The label is accurate, no production
call was substituted, and the derived numbers are internally consistent
(42 × 0.219 / 23.2 = 0.40×; 42 × 15 ms = 630 ms; 630 / 23 = 27×). Labelling it
unverified rather than re-asserting it is the correct behaviour under the
document's own rule.

**Citations and line references — spot-checked, all accurate.** `pyproject.toml:20`
is `"slowapi>=0.1.10"`; `limiter.py:6` is `Limiter(key_func=get_remote_address)`
with no `storage_uri`; the five `@limiter.limit` sites are exactly `auth.py:115`,
`invitations.py:130`, `invitations.py:156`, `public_branding.py:65`,
`public_branding.py:103`, plus `public_projects.py:139` at `300/minute` — six, as
§4 says. `public_projects.py:32-41`, `:56-58` ("12 obras"), `:76-78` (the
dangling APRAS-93 pointer) are verbatim. The amplification sentence §3.1 quotes
is verbatim at `public_projects.py:51-52`. D3 is at
`docs/tasks/APRAS-92-spec.md:73-84` and its stated reason matches word for word,
including that it declined the cache and the limit on one shared objection.
`tenant_service.py:572` is the 2 MiB constant. `urls.py`'s last rung returns the
local base URL. `project_report_service.py` 935-952 / 1089 / 1204 / 1271-1296
(`updates[:3]`, `decode_photos(...)[:3]`) / 1304 / 1321 (the "**89%**" docstring)
/ 1353-1384 / 1500 / 1513 all land on what the document says they do.
`test_the_thirty_first_request_inside_a_minute_is_still_a_200` exists at
`test_public_project_report.py:356` and does assert structurally over the parsed
module, with its own comment explaining why the request loop alone proves nothing.

### The byte-equality assertions — mutation-tested

I copied the harness to `scratchpad/rev93mut/`, repointed its `sys.path`
inserts, and mutated `dh._eager_acting_projects` to return `…all()[:-1]` so the
eager arm renders one project fewer and the two arms **must** differ.

**The mutation took effect**, visibly: the eager arm's byte count moved from
171,507 to **163,584** (one project's 7,923 B), printed before any timing began.

**`p200.py` / `dh.paired` asserts for real.** The mutated run died on the first
pair, warm-ups included, exactly as `dh.py:247-249`'s comment claims:

```
[MUTANT] cold : stmts=42 bytes=171507
[MUTANT] eager: stmts=4 bytes=163584
  File ".../dh.py", line 249, in paired
    assert b_cold == b_eager, (b_cold, b_eager)
AssertionError: (171507, 163584)
```

So the document's sentence "Every pair was asserted byte-identical as it was
timed" is true, and the 1,738,448 B / 171,507 B figures beside it are not
vacuous. This is the one place the project's documented failure mode would have
hurt most, and it holds.

**`t_states.py` does not assert — it prints.** Same mutation, same fixture:

```
  cold: median    24.37 ms  stmts   42  bytes 171507
 eager: median    14.13 ms  stmts    4  bytes 163584
byte-identical across the measured states: False -> {163584, 171507}
exit=0
```

The check cannot fail a run. It is not vacuous — a non-empty difference reads as
`False` and a two-element set, loudly and in the right direction — but it is a
printed boolean a human must read, which is precisely what §1.3 line 199 calls
"asserted in the harness, not eyeballed". Recorded under Suggestions rather than
as blocking, because the figure it guards does reproduce and the cold-vs-eager
half of the same claim is genuinely asserted in `p200.py`.

### The D3 reversal, judged on its own merits

Independent of whose idea it was, the reasoning stands, and I could check both
halves of it against code rather than prose.

D3's text really does decline the cache and the limiter on **one** premise:
"both a cache and a limit would be per-process on Vercel's serverless runtime and
would behave inconsistently between instances"
(`APRAS-92-spec.md:81-84`). That premise is true of both mechanisms and I
confirmed the mechanism — `Limiter(key_func=get_remote_address)`, no
`storage_uri`, so in-memory per process. But "inconsistent between instances"
cashes out differently on each side, and the difference is a property of the
code, not of the argument: a per-instance render cache holds a body, so an
invalidation that lands in instance A leaves instance B serving an old bulletin —
the one outcome the binding constraint forbids. A per-instance limiter holds no
body at all, so its only failure is under-counting, i.e. admitting more requests
than its nominal 30/min. It cannot go stale because there is nothing to go
stale. The document states this asymmetry plainly, does **not** claim D3 was
wrong about the mechanism, and notes that six live production call sites already
run on the same approximation — which I verified is literally six.

What makes §6.1 creditable rather than merely clever is §6.1's last paragraph:
it says outright that §1 **agrees with D3** that nothing here is expensive, that
"do nothing" survives §1 intact, that the reversal therefore rests only on §5
(a cache cannot bound a distinct-slug sweep) and §3.1 (a metered child beside an
unmetered parent), and that the final step is a judgement about acceptable
exposure needing the operator's signature. §5's sweep reproduced in my runs and
§3.1's structural fact is in the code (the cover route is limited at 300/minute;
`_hero_html` emits one `<img src>` per project with no cap, so the fan-out is
`N`, not 12). The reversal is argued from two legs that both hold, with its own
weakest point named. I would sign this reasoning.

## Blocking Findings

**1. `docs/tasks/APRAS-93-spec.md:229` — the warm figure at 200 projects, and the
15/85 split it derives, do not reproduce; the sentence "corrects" draft 2 in the
wrong direction.**

The document publishes warm **63.51 ms** at 200 projects and concludes "string
assembly ~15% here too, **not the 11% draft 2 reported**". The Expected Results
tick at `:933` carries the same 15/85 split.

I measured the warm arm at 200 projects five times — three in its own process
(as §1.3 prescribes) and twice inside a single `cold,eager,warm` process:

| configuration | warm median | cold median | warm / cold |
|---|---|---|---|
| own process, trial 1 | 42.42 ms | — | — |
| own process, trial 2 | 41.42 ms | — | — |
| own process, trial 3 | 41.59 ms | — | — |
| own process (earlier) | 42.42 ms | 451.81 ms | 9.4% |
| combined, trial 1 | 41.65 ms | 441.67 ms | **9.4%** |
| combined, trial 2 | 42.42 ms | 446.57 ms | **9.5%** |

Five independent measurements span 41.4–42.4 ms. None is near 63.51 ms; the
document's figure is ~50% high. `t_states.py` prints the split itself, so this is
the harness's own verdict and not my arithmetic: *"string assembly 9.4% of cold;
ORM data access 90.6%"*.

This is not machine drift, and the document's own ±15% licence does not cover it:
in the same sessions the **cold** arm reproduced at 441.7–451.8 ms against the
published 428.30 (+3 to +5%) and the **eager** arm at 394.4–396.1 against the
published 396.45 (−0.5%). Only the warm arm is off, by a factor the other two
arms rule out as drift. The warm path is also deterministic — it pins every
hydrated row behind a strong reference and issues 2 statements, and it produced
the same 1,738,448 B every time.

The consequence is not cosmetic. At 200 projects the split is **9.4–9.5%**, which
is *nearer draft 2's 11%* than the document's 15% is, so the clause "not the 11%
draft 2 reported" retracts a figure that was closer to reproducible than its
replacement. The 20-project split does reproduce (3.40 / 24.80 = 13.7%, against
the published 3.44 / 23.23 = 14.8%), so the headline "ORM data access dominates"
is safe at both sizes and the decision in §3 does not move — but a published
figure, a published correction of a prior draft, and an Expected Results tick all
rest on a number the harness does not produce.

**2. `docs/tasks/APRAS-93-spec.md:314-319` — the 779.5 ms "2× error from arm
order alone" does not reproduce in 3 of 3 trials, and it is the stated
justification for a methodological choice.**

The document says: *"running cold, then eager, then warm **in one process**
(`t_states.py` with all three states) reports eager at **779.5 ms**, against
**396.45 ms** for the identical eager measurement in its own process — a 2× error
from arm order alone, which is why the three single-state figures above are taken
one process each."*

I ran exactly that configuration — `t_states.py 200 40 60 8 cold,eager,warm`,
which is also the script's default state list — three times:

| run | eager median | own-process eager, same session |
|---|---|---|
| combined, run 1 | **395.37 ms** | 395.34 ms |
| combined, run 2 | **394.37 ms** | — |
| combined, run 3 | **396.12 ms** | — |

The in-process eager figure agrees with the own-process eager figure to within
0.5%. There is no 2× error, no measurable error of any size, in 3 of 3 trials.
Unlike `blocked.py` — whose intermittency I did reproduce, 1 flip in 8 — this
claim produced nothing in its direction at all, so "it did not flip in my trials"
is not the right reading: the two configurations were indistinguishable.

The figure is load-bearing twice over. It is published as "a sharper version of
the same artefact", with no label marking it as a one-off observation, and the
sentence containing it is the reason given for taking the three single-state
figures one process each (`:230-232`, `:317-319`). As it stands, a methodological
rule in a document whose thesis is that claims must be re-derivable rests on a
figure I cannot re-derive. The *pairing* rule survives this intact, because
`blocked.py` independently justifies it — this finding is confined to the
one-process-per-state corollary and the 779.5 ms number.

Note that findings 1 and 2 are adjacent: both concern §1.3's handling of the
200-project single-state runs, and both would be settled by re-running those
three states and republishing what comes out. Everything else in §1.3 — the byte
identity, the statement counts, the cold and eager medians, and the whole paired
table that was round 1's subject — reproduced.

## Suggestions

1. `:199` says the three-state byte identity is "asserted in the harness, not
   eyeballed (`t_states.py`)". `t_states.py:73-74` computes a set and prints
   `byte-identical across the measured states: …`; it exits 0 on a mismatch, as I
   confirmed by mutation. One line — `assert len(b) == 1, b` — would make the
   sentence true. Note also that in the per-state runs the printed set has a
   single element by construction, so the line is trivially `True` there; today
   the only executed cross-state equality check at 200 projects is `p200.py`'s,
   which covers cold against eager and not warm.
2. `:304-309`'s blocked table is a record of one session, not a reproducible
   figure, and is not labelled as such. My 8 trials ranged from −177.9% to
   +75.9% where the document's four span −5.7% to +10.5%. The *claim* reproduces
   and the table is evidence rather than a published constant, so a half-sentence
   ("one recorded session; the magnitudes are not reproducible, the
   intermittency is") would protect it from the next reader who re-runs it.
3. `t_sweep.py:55` prints `total/1024/1024/(dt/1000)` under a header reading
   `MB/s` — that value is MiB/s. §5's prose gets this right and gives both units,
   which makes the harness label the only place the slip survives, but it is the
   same slip §5 corrects draft 2 for.
4. `dh.py:45` comments `CONTRACTOR` as "25 chars"; it is 26, which is what the
   spec's pinned-fixture table says. Harness comment only; the measured figures
   are unaffected.
5. §3.1 quotes the cover docstring's amplification principle accurately, but that
   same docstring (`public_projects.py:44-46`) explicitly says it "does **not**
   reverse D3 and it does not claim the report route's policy". The document is
   entitled to borrow the principle and §6.1 is candid that it is reversing D3,
   so nothing is wrong — but quoting the disclaimer beside the principle would
   make §3.1's strongest point unimpeachable.
6. The harness copy I mutated is left at
   `scratchpad/rev93mut/` as evidence; it is outside the repository and the
   original `dev93/` was not modified.

## Verdict

The round-1 blocking finding is **resolved**: the `selectinload` sign is now
correct and I reproduced it independently, 24 of 24 paired repetitions at 200
projects across two runs plus 12 of 12 at 20, with the byte-equality assertion
proven real by mutation. Of roughly forty published figures I re-derived, every
byte count, every statement count, every citation and every line reference came
out exact. Two figures did not reproduce, both in §1.3/§1.3.1's treatment of the
200-project single-state runs, and both carry a published conclusion — one of
them an Expected Results tick, the other a methodological rule. Under this
document's own standard, that is what has to send it back.

VERDICT: REJECTED

1. `docs/tasks/APRAS-93-spec.md:229` (and the Expected Results tick at `:933`):
   warm at 200 projects is published as **63.51 ms**, giving "string assembly
   ~15% here too, not the 11% draft 2 reported". Five independent runs of
   `t_states.py 200 40 60 8` — three single-state, two inside the combined
   process — measured warm at **41.4–42.4 ms** and the harness printed the split
   itself as **9.4–9.5%**, while cold (+3 to +5%) and eager (−0.5%) reproduced in
   the same sessions, which rules out drift. The retracted 11% was nearer
   reproducible than its replacement.
2. `docs/tasks/APRAS-93-spec.md:314-319`: the claim that running
   `cold,eager,warm` in one process "reports eager at **779.5 ms**, against
   396.45 ms for the identical eager measurement in its own process — a 2× error
   from arm order alone, **which is why** the three single-state figures above are
   taken one process each". Three runs of exactly that configuration reported
   eager at **395.37 / 394.37 / 396.12 ms**, against 395.34 ms own-process in the
   same session — agreement to 0.5%, no artefact of any size. The pairing rule
   itself is unaffected (`blocked.py` reproduced, 1 sign flip in 8 trials); the
   one-process-per-state corollary and the 779.5 ms figure are what lack support.
