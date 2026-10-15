# APRAS-93 — code review, round 3

Reviewer: Meridian code reviewer. Date: 2026-10-05.
Worktree: `/Users/heitor/workspace/apras/.claude/worktrees/agent-a7a31a09fc3ca4bf4`.
Answering the round-3 developer report against my own round-2 review.

## How this round was reviewed

This task ships no production code, so "review the code" was again read as:
execute the harness and check every published figure against what the harness
actually produces. Nothing below is taken from the developer's round-3 report.
I made roughly **71 harness invocations** in this session, and every number
marked "measured" is from one of them.

Two rounds of non-reproducing figures means prior acceptance is not evidence, so
I re-derived the byte columns, the statement columns, the citations and the
arithmetic from scratch rather than carrying forward my own round-2 pass.

### Worktree state, confirmed myself

```
git rev-parse HEAD    -> bc78696d029e5813f2b1ed393440ed030d3fc69e
git rev-parse master  -> bc78696d029e5813f2b1ed393440ed030d3fc69e
git diff --cached --name-only -> docs/tasks/APRAS-93-spec.md   (1 file, 1184 insertions)
git diff --name-only  -> (empty)
git status --porcelain -> A  docs/tasks/APRAS-93-spec.md   (and nothing else)
git stash list        -> (empty)
```

`HEAD` equals `master` equals `bc78696`, so the fast-forward the dispatch
describes did happen and nothing diverged. Exactly one staged path, nothing
unstaged, nothing committed. Re-checked at the end: unchanged. I ran no `stash`,
no `add`, no `commit`, no `push`, and touched no other worktree.

### No production code ships — verified by hashing

`git show HEAD:<path> | shasum -a 256` against `shasum -a 256 < <path>`:

| path | result |
|---|---|
| `backend/app/api/v1/endpoints/public_projects.py` | **IDENTICAL** |
| `backend/app/services/project_report_service.py` | **IDENTICAL** |
| `backend/app/core/limiter.py` | **IDENTICAL** |
| `backend/pyproject.toml` | **IDENTICAL** |
| `backend/requirements.txt` | **IDENTICAL** |

`git status --porcelain backend/` is empty. ER13 holds.

Before running anything I confirmed no script reaches a remote host: in-memory
SQLite throughout, `run.sh`'s synthetic `POSTGRES_URL` is never connected to,
`t_logo.py` reads one local file, `t_route.py`/`t_sweep.py` use `TestClient`
in-process. No production database, no credentialled call.

### A note on load, which conditions everything below

The dispatch is right that this changes how every figure must be read, mine
included. Load average during my session ranged from **3.8 to 23.0**. I recorded
it alongside every run and I have grouped my measurements by it, because the
grouping turns out to matter more than any single number.

---

## The two blocking findings from round 2: both corrections reproduce

### Finding 1 — warm at 200, and the in-process split. RESOLVED.

The retraction was correct and the replacement reproduces.

**Warm, own process, 18 runs at `200 40 60 8 warm`:** 39.31, 39.97, 39.86,
39.59, 39.47, 40.69, **44.94**, 40.19, 40.46, 40.73, 41.83, 39.57, 40.28, 39.36,
39.79, 40.54, 39.49, 39.98 ms. Span **39.3–44.9 ms**, 1,738,448 B every run.
Nothing near 63.51. The published fast-mode figure of **41.72 ms** sits inside
this span.

**The in-process split at 200.** This is where load discipline matters, so I
report both groups:

| group | load avg | split (warm/cold), per run |
|---|---|---|
| 8 combined runs, quieter machine | 4.6–8.1 | 9.9 / 10.4 / 9.1 / 9.6 / 10.1 / 9.2 / 9.7 / **9.1%** |
| 5 combined runs, busy machine | 8.7–23.0 | 6.3 / 10.1 / 13.2 / 7.0 / **4.7%** |

Under comparable load the eight quiet runs give **9.1–10.4%, median 9.65%**,
against the published 9.5% and published span 8.1–9.6%. **The 9.5% headline
reproduces.** The arms in those runs were cold 391.9–450.2 ms (published 439.26),
eager 355.5–427.5 ms (published 396.84), warm 39.4–42.4 ms (published 41.72) —
all three bracket their published values.

So: the 15% figure and the clause "not the 11% draft 2 reported" were correctly
withdrawn, 9.5% is what the harness produces, and the Expected Results tick at
`:1120-1122` now carries both sizes labelled within-process. Verified.

### Finding 2 — the 779.5 ms artefact. RESOLVED.

I tested this the way it should be tested — **interleaved**, so load cannot land
on one configuration:

| pair | load | own-process eager | combined (`cold,eager,warm`) eager |
|---|---|---|---|
| 1 | 6.70 | 379.54 ms | 369.54 ms |
| 2 | 6.49 | 376.11 ms | 356.21 ms |
| 3 | 5.56 | 366.74 ms | 371.21 ms |
| 4 | 4.65 | 369.92 ms | 369.91 ms |
| 5 | 3.76 | 369.58 ms | 371.01 ms |

Agreement within ~3%, with the combined arm marginally *faster* on balance. No
artefact in either direction, in 5 of 5 interleaved pairs. The figure and the
"which is why" sentence are both gone from the document, and §1.3's figures are
now taken in one process so the warm/cold ratio is within-process. The reversal
is the right call and `§1.3.1:421-440` states it as a retraction rather than
re-justifying it. Verified.

### The new assertion at `t_states.py:79` — mutation-proven independently

I did not take the reported exit code on trust. I copied the harness to
`scratchpad/rev93mut_r3/`, repointed its `sys.path` inserts, and mutated
`dh._eager_acting_projects` to return `.all()[:-1]`.

**The mutation took effect, visibly** — the eager arm's byte count moved to
176,941 against the other two states' 185,567 on the same fixture, printed
before the assertion ran:

```
  cold: median    33.89 ms  stmts   42  bytes 185567
 eager: median    28.28 ms  stmts    4  bytes 176941
  warm: median     5.01 ms  stmts    2  bytes 185567
AssertionError: {176941, 185567}
mutant real exit=1
```

**Control, unmutated, same fixture:** all three states 185,567 B,
`byte-identical across the 3 measured state(s): [185567]`, **exit 0**.

The assertion is real, it fails when it should and passes when it should, and my
output matches the developer's reported output figure-for-figure including both
byte counts. `dh.py:249`'s paired assertion I had already mutation-proven in
round 2. Verified.

---

## Every figure I re-derived this round

**Exact — zero drift.** These are the load-immune columns and they did not move
by one unit.

- **§1.1 (`t_sizes`)**: 13,061 / 20,109 / 50,897 / 171,507 / 530,607 /
  1,738,448 B; statements 2 / 4 / 12 / 42 / 122 / 402; per-project slope
  13,061 → 20,109 → 27,161 → 34,213 (+7,048 / +7,052 / +7,052). All exact.
- **The shell law (`fixture_probe`)**: 13,031 / 13,039 / 13,050 / 13,061 B at
  tenant names of 1 / 9 / 20 / 31 chars. Sensitivities exact: project
  description +1, bulletin body +3, photo URL +9, milestone title +6, bulletin
  title +3, milestone description 0, contractor 0.
- **§1.2 (`t_route`)**: 2 / 4 / 6 / 12 / 42 / 122 / 402 at N = 0/1/2/5/20/60/200
  — `2N + 2` at all seven, through the real route. The six-statement trace at
  N = 2 matches the document in order and kind.
- **§1.3 byte identity**: 171,507 B in all three states at 20/20/20/6 and
  1,738,448 B in all three at 200/40/60/8, now by assertion, in every run.
- **§1.3 statement counts**: cold 42 / warm 2 / eager 4 at 20; 402 / 2 / 4 at 200.
- **§1.5 (`t_dims`)**: 19,540 / 19,655 / 20,115 / 25,255 / 43,005 / 66,805 B;
  slopes 115.0 / 115.0 / 116.6 / 117.9 / 118.5; 4 statements every row.
  Dimension two 20,976 / 31,309 / 54,070 / 168,471 B; B/leaf 129.2 / 82.7 / 73.7.
  168,471 / 171,507 = **0.9823**, so the 0.98× stands.
- **§1.6 (`t_logo`)**: 108,018 B on disk; base64 144,024; `data:` URI 144,046;
  2,796,226 B at the 2 MiB ceiling; 699,074 at 512 KiB;
  `LOGO_MAX_FILE_SIZE = 2097152`; 9,859 regular / 8,090 embeddable, largest
  108,018 B, zero over 512 KiB; `_logo_html` 0 B without `logo_url` and 108 B
  with it (20,109 → 20,217, 0.53%), no `data:` in the tag; historical embed share
  144,046 / 164,155 = **87.7%**. Every figure exact.
- **§5 (`t_sweep`)**: 160 statements on both arms in all nine trials I ran;
  684,180 B equal to the byte on all eighteen arms. The unit label now reads
  `MiB/s` (`t_sweep.py:55`) — round-2 suggestion 3 fixed.
- **§1.7**: `anyio` 4.14.2; `current_default_thread_limiter().total_tokens` =
  **40**; 40 / 0.0232 = 1,724/s; 40 / 0.6 = 67/s. Both handlers are `def`.
- **Arithmetic**: 20 / 0.0815 = 245.4 reports/s; 684,180 / 0.0815 = 8.39 MB/s =
  8.01 MiB/s; loaded 20 / 0.5693 and 20 / 0.4897 = 35.1 and 40.8/s, matching the
  document's "~35–41"; 42 × 0.219 / 23.2 = **0.40×**.
- `dh.py:45` now comments `CONTRACTOR` as 26 chars;
  `len("Empreiteira Sintetica Ltda")` = 26. Round-2 suggestion 4 fixed.
- §3.1 now quotes the cover docstring's disclaimer beside the principle it
  borrows. The quoted text is verbatim at `public_projects.py:45-46` (cited as
  `44-46`, a range that contains it). Round-2 suggestion 5 addressed.
- The harness inventory at `:65-74` lists `t_warmdist.py`. Round-2 suggestion 6:
  my mutant copy is outside the repo at `scratchpad/rev93mut_r3/`; `dev93/` is
  unmodified.

**Reproduced as a conclusion.**

- **§1.3's paired cold-vs-eager — the headline comparison, and it is solid.**
  `p200.py`: at 200, **12 / 12 to eager, +11.4%** (cold 415.3, eager 367.9,
  median paired diff +40.4 ms, range +14.8 … +71.7). At 20, **12 / 12, +42.9%**
  (cold 22.1, eager 12.6, diff +9.3 ms, range +8.3 … +10.4). Both inside the
  published bands (8.9–15.9% at 200; 41–47% at 20). This is the figure §1.3.2
  claims survives load, and it does.
- **§1.3.1's blocked design (`blocked.py`, 12 trials, mine)**: +7.2, +6.8, +12.1,
  +9.2, **−10.8**, **−28.0**, +5.5, +23.6, +4.6, +7.9, +10.9, +12.6%. **2 sign
  reversals in 12 trials** and a magnitude spread (+4.6% to +23.6%, plus the
  reversals) far wider than the ~10% effect. The claim reproduces, and the table
  is now correctly labelled "a record of one session, not a published constant"
  — round-2 suggestion 2 adopted.
- **§5's sweep comparison**: the sign flips between my trials too (same-slug
  85.3 / 77.3 / 75.1 / 74.7 / 73.7 / 87.6 / 77.0 / 75.7 / 96.2 ms against
  distinct-slug 80.0 / 73.7 / 73.9 / 75.7 / 79.1 / 89.3 / 81.1 / 102.9 /
  91.1 ms), and the within-arm spread again exceeds the between-arm gap. The
  non-finding reproduces.
- **§1.3's 20-project triple** (carried forward, not re-measured by the
  developer). I re-measured it: 8 runs at `20 20 20 6` gave cold 21.82–27.53,
  warm 3.08–3.73, eager 13.56–14.54 ms, split **13.2–15.9%**. The published
  triple (23.23 / 3.44 / 13.59) sits inside all three spans and the ~14–15%
  headline holds.
- **The size-dependence claim.** Compared like-for-like under quiet load, 20
  projects gives 13.2–15.9% and 200 gives 9.1–10.4% — **the direction and the
  non-overlap both hold.** The claim is substantiated. (Both published ranges are
  narrower than what I reproduce; see Suggestions.)

**§1.3.2's drift disclosure is honest, and if anything understates one row.** Its
headline — "an absolute wall clock here can be off by a factor of several if the
machine is busy, and no band stated in advance covers that" — is exactly what I
independently measured: cold spanned 391.9 → 997.7 ms and eager 355.5 → 782.4 ms
across my thirteen combined runs. Withdrawing the ±15% band, relabelling §5's
245 reports/s and §1.7's 1,700 renders/s as best-case with loaded figures beside
them, and reducing the surviving evidence to counts, within-process ratios and
the paired design are all the right calls, and the unprompted self-correction is
to the developer's credit. Two of the table's rows do not hold up (Suggestions 1
and 2), but the section's thesis does.

**Not re-derived this round, and why.** §1.4's 0.219 ms loopback anchor — still
labelled "measured once, not re-verified", nothing is listening on 5432 / 5433 /
55432, and substituting a production call is forbidden. Its derived figures are
internally consistent (0.40× re-checked above). The citations and line references
I re-derived exhaustively in round 2 I spot-checked rather than re-walked this
round: `public_projects.py:45-46`, `t_states.py:79`, `dh.py:249`, `dh.py:45`,
`t_sweep.py:55`, and the §1.3.2 / correction-5 / correction-6 / correction-7 and
Expected Results passages. The ~30 citations in §4, §6.1 and §1.5 are carried
forward on round 2's check. Next reader: that is the one area of this document
where my round-3 coverage is thinner than round 2's.

---

## What my own round-2 figures look like in this light

The dispatch asked, and the honest answer is unflattering to me.

In round 2 I reported warm at 41.4–42.4 ms and eager at 394.4–396.1 ms with
tight spreads, and I wrote: *"This is not machine drift … in the same sessions
the cold arm reproduced at 441.7–451.8 ms and the eager arm at 394.4–396.1,
… Only the warm arm is off, by a factor the other two arms rule out as drift."*
I did not record load average.

This round the same scripts gave cold 391.9–997.7 ms and eager 355.5–782.4 ms. So
my round-2 session was evidently a quiet one, and the step where I inferred
*"cold and eager reproduced, therefore drift is excluded"* was weaker than I
presented it — two arms behaving in one session does not establish that a third
arm's excursion has a non-load cause. That is the same inference pattern I am
flagging below. My round-2 **conclusions** stand: warm really is ~41 ms, the
split really is ~9.5%, and 63.51 ms really is unreproducible — all three now
confirmed by 26 further runs across two load regimes. But my round-2
*reasoning* about drift should be read as one session's observation, and I
should have recorded load then.

I raise it because the document inherited that reasoning. §1.3.2's "it is also
not machine load alone" rests on the same move, and my data now runs against it.

---

## Blocking Findings

### 1. `docs/tasks/APRAS-93-spec.md:481-489` — the warm arm's bimodality does not reproduce, and the claim is internally inconsistent with the one figure it exists to explain.

The document publishes, in §1.3.2's table and prose:

> `t_states` warm at 200, 14 runs | 63.51 ms | 41.0-44.9 ms, **or** 72.2-128.2 ms | **bimodal**

> "Across fourteen measurements the warm median was either 41.0-44.9 ms (nine
> runs) or 72.2-128.2 ms (five runs), **with nothing in between**; the mode is
> fixed when the process builds its pinned object graph **and does not change
> within the process**."

Three separate problems, each checkable:

**(a) I measured values inside the claimed empty gap.** Two of my thirteen
combined runs gave warm medians of **54.31 ms** and **69.99 ms**. Both sit
squarely in the 45–72 ms region the document says is empty.

**(b) `t_warmdist.py`'s own per-repetition output contradicts "does not change
within the process".** In six runs of the probe, otherwise-fast processes
contained individual repetitions at **47.7, 50.5, 51.7, 52.0 and 55.4 ms** —
again inside the claimed gap, and varying *within* a single process whose mode
the document says is fixed at graph-build time. The distribution I measure is
not two modes with a void between them; it is a hard floor near 39–41 ms with a
load-dependent right tail.

**(c) The explanation contradicts itself on its own numbers.** §1.3.2 says the
bimodality is "where draft 3's 63.51 ms came from", and correction 5 at `:132`
says "The 63.51 ms came from the slow mode of a bimodal measurement". But
**63.51 is in neither published mode** — it is not in 41.0–44.9 and it is not in
72.2–128.2. By the document's own table, 63.51 falls in the "nothing in between"
region that the document asserts is empty. The figure the bimodality is invoked
to explain is excluded by the bimodality as stated.

**(d) The sample counts do not match the evidence.** §1.3, correction 5 and the
§1.3.2 table all say **fourteen** measurements, split nine fast / five slow. The
round-3 developer report tabulates the underlying data explicitly as "own
process … **9 runs**" plus "inside `cold,eager,warm` … **9 runs**" — **18**
warm medians, of which 13 are fast and 5 slow. The published count understates
its own sample and misstates the breakdown. Separately, §1.3 at `:300` says
"the **seven** trials in which the warm arm stayed in its fast mode" against
§1.3.2's "nine runs" for the same thing.

My own observations of 54.31 and 69.99 ms would in fact explain 63.51 ms
naturally, as an ordinary draw from a loaded right tail. The fix is contained and
makes the document stronger: describe the warm arm as a floor near 40 ms with a
load-dependent tail, which covers 63.51 without a special mechanism, and
reconcile the counts with the evidence file.

### 2. `docs/tasks/APRAS-93-spec.md:486-492` — "It is **not** the garbage collector" is asserted as settled fact on evidence that cannot establish it.

The document states flatly: *"It is **not** the garbage collector: a probe
(`t_warmdist.py`) … found the same distribution in both regimes, in two trials."*

**The probe's design cannot separate the hypotheses.** `t_warmdist.py:35-50`
runs the `gc`-enabled and `gc`-disabled blocks **inside the same process**, on
the same pinned object graph built once at `:31-32`. The document asserts two
sentences earlier that the mode "is fixed when the process builds its pinned
object graph and does not change within the process". If that premise is true,
both `gc` regimes inherit the process's mode **by construction**, and the probe's
result is predetermined regardless of whether the collector is involved. The
developer's own two trials show exactly that signature — slow in both regimes,
or fast in both regimes. A test whose outcome is fixed by the hypothesis it
assumes cannot be evidence against a competing cause. Separating them needs the
regime varied *across* processes, one `gc` setting per process, over enough
processes to see both modes.

**Secondary design problems.** `gc.disable()` suppresses only the *cyclic*
collector, leaving reference counting, allocator behaviour and page-fault cost
untouched — several plausible causes of a 1.7 MB string rendered 13 times
survive it. And the `gc`-off arm runs immediately after an explicit
`gc.collect()` at `:39`, so it starts from a cleaned heap the `gc`-on arm never
had: the two arms differ in more than the one variable.

**Sample size.** "Two trials", of which **one** was in the slow mode. Ruling out
a candidate cause from a single observation of the phenomenon is precisely the
inference strength this document identifies as its own recurring failure at
`:149-157`.

**In my hands the probe exercised the hypothesis zero times.** All six of my
`t_warmdist` runs landed in the fast mode (medians 39.49 / 39.82 / 41.09 / 39.49
/ 39.93 / 41.26 `gc` on; 39.66 / 40.31 / 41.78 / 39.67 / 40.94 / 45.14 off; byte
identity asserted and held at 1,738,448 B in all of them). I never saw a slow
process, so I could not test the claim even sympathetically.

The evidence supports "the probe **failed to implicate** the collector". It does
not support "it is **not** the collector". That is a one-word fix, and the
document's own standard at `:443-447` — "A figure that cannot be resolved that
way is to be labelled unresolved, with what would settle it" — prescribes it.

**The adjacent claim has the same problem and my data runs against it.** §1.3.2
also says *"It is also not machine load alone: twice the warm arm came out at
87.6 and 94.4 ms in processes whose cold and eager arms were simultaneously
clean."* In my session, **all 18 warm-only runs and all 8 quiet combined runs
were fast**, and the only intermediate or slow warm medians I observed (54.31 and
69.99 ms) came from the two busiest combined runs, at load **16.90** and
**14.18**. Load is the best available predictor of the slow warm arm in my data.
Two observations of a clean cold arm beside a slow warm arm do not exclude load,
because the three arms differ in how load reaches them — the warm arm is the only
one that skips `gc.collect()` between repetitions and so accumulates state across
them.

Neither finding moves §3's decision, and I want that on the record for the next
reader: the decision rests on the statement count and the byte size, every one of
which reproduced exactly, and the §1.3 figures those two findings sit beside
(41.72 ms, 9.5%, the paired table) all reproduced. What fails is a mechanism
claim stated more strongly than its evidence, in the one section whose purpose is
to be honest about exactly that.

---

## Suggestions

1. **§1.3.2's eager row understates the drift it is cataloguing.** The table
   gives `t_states` eager at 200 as "392.1-398.6 ms, spread **1.02×**",
   presenting eager as the stable arm. Across my thirteen combined runs eager
   spanned **355.5–782.4 ms, a 2.2× spread**, and my quiet-run minimum (355.5)
   is below the published range floor. The row is one session's observation
   presented as a measured stability property. The section's headline is right;
   this row invites the reader to trust an absolute figure the headline tells
   them not to trust.
2. **"Ratios taken inside one process" are more robust than absolute clocks, but
   not immune, and (b) is stated as though they were.** My five busy combined
   runs gave within-process splits of 4.7 / 6.3 / 7.0 / 10.1 / 13.2% — a **2.8×
   spread** on the ratio the document lists among the things that survive drift.
   Worth qualifying as "substantially more robust" rather than "survives", with
   the caveat that the warm and cold arms do not absorb load proportionally.
3. **Both published split ranges are narrower than what re-measurement gives.**
   The document publishes 8.1–9.6% at 200 and 14.0–14.8% at 20; I measured
   9.1–10.4% (8 quiet runs) and 13.2–15.9% (8 runs). The conclusion and the
   non-overlap are safe either way, but quoting three-significant-figure bounds
   from one session's trials is the habit that produced findings 1 and 2. A
   half-point of rounding would make them durable.
4. `t_warmdist.py`'s docstring states the hypothesis it was built to test
   ("a generational pass can land inside a timed repetition") but the file does
   not record that the result refuted it, nor that the within-process design
   cannot separate `gc` from a per-process mode. A comment at `:35` would stop
   the next reader drawing the conclusion §1.3.2 draws.
5. §3.1 cites the cover docstring's disclaimer as `public_projects.py:44-46`; the
   quoted sentence begins on line 45. The range contains the quote and line 44
   opens the sentence it belongs to, so this is defensible — noted only because
   every other line reference in this document is exact.
6. My mutant harness copy is left outside the repository at
   `scratchpad/rev93mut_r3/` as evidence. `dev93/` was not modified.

---

## Verdict

Both round-2 blocking findings are **resolved**, and resolved the right way — by
retraction and re-measurement rather than re-justification. I reproduced the
corrected warm figure (39.3–44.9 ms over 18 runs), the corrected 9.5% split
(9.1–10.4% over 8 quiet runs), and the absence of the 779.5 ms artefact (5 of 5
interleaved pairs agreeing within 3%). The new assertion at `t_states.py:79` is
real, and I mutation-proved it myself rather than trusting the reported exit
code. The paired cold-vs-eager table, which was round 1's subject, reproduced at
12/12 and 12/12. Every byte count, statement count, slope and piece of
arithmetic I re-derived came out exact. The unprompted withdrawal of the ±15%
band is the most creditable thing in this round, and §1.3.2's central thesis is
one I independently confirmed from the other side.

But §1.3.2 also introduces two new claims that repeat the document's own
diagnosed failure mode. The warm arm's bimodality does not reproduce — I measured
values inside the gap the document says is empty, the probe's own per-repetition
output varies within processes the document says are fixed, the published sample
counts contradict the evidence file, and the 63.51 ms figure the bimodality
exists to explain lies outside both of its published modes. And the collector is
declared ruled out by a probe that, on the document's own premise, could not have
implicated it. Under this document's standard — a figure the harness does not
reproduce, and a claim stated more strongly than its evidence — that is what has
to send it back. Both fixes are contained and neither disturbs §3's decision.

VERDICT: REJECTED

1. `docs/tasks/APRAS-93-spec.md:481-489` — the warm arm's bimodality does not
   reproduce and is internally inconsistent. Published as "41.0-44.9 ms (nine
   runs) or 72.2-128.2 ms (five runs), **with nothing in between**", the mode
   "fixed when the process builds its pinned object graph and does not change
   within the process". I measured warm medians of **54.31** and **69.99 ms**
   inside that gap, and `t_warmdist.py`'s own per-repetition output shows reps at
   **47.7 / 50.5 / 51.7 / 52.0 / 55.4 ms** varying *within* otherwise-fast
   processes. Decisively, **63.51 ms — the draft-3 figure the bimodality is
   invoked to explain at `:483` and at correction 5, `:132` — belongs to neither
   published mode**, so the explanation excludes its own subject. The sample
   counts also contradict the evidence: the document says fourteen measurements,
   nine fast / five slow, while the round-3 report tabulates 9 + 9 = **18** warm
   medians, 13 fast / 5 slow; and §1.3 at `:300` says "seven trials" in the fast
   mode where §1.3.2 says nine.
2. `docs/tasks/APRAS-93-spec.md:486-492` — "It is **not** the garbage collector"
   is not supported by `t_warmdist.py`. The probe runs both `gc` regimes **inside
   one process** on a graph built once (`t_warmdist.py:31-32`, `:35-50`), so under
   the document's own premise that the mode is fixed per process, both regimes
   inherit it by construction and the outcome is predetermined — the developer's
   two trials show exactly that signature (slow throughout, or fast throughout).
   `gc.disable()` suppresses only cyclic collection, and the `gc`-off arm runs
   after a `gc.collect()` at `:39`, so the arms differ in more than one variable.
   The claim rests on **one** observation of the slow mode. In six runs of the
   probe I never reached the slow mode, so it exercised the hypothesis zero
   times. The evidence supports "failed to implicate", not "ruled out". The
   adjacent "it is also not machine load alone" has the same defect and my data
   opposes it: all 18 warm-only and all 8 quiet combined runs were fast, while
   both of my non-fast warm medians came from the two busiest runs (load 16.90
   and 14.18).
