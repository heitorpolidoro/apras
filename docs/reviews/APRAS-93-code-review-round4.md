# APRAS-93 — code review, round 4

Reviewer: Meridian code reviewer. Date: 2026-10-08.
Worktree: `/Users/heitor/workspace/apras/.claude/worktrees/agent-a7a31a09fc3ca4bf4`.
Answering the round-4 developer report against my own round-3 review.

## How this round was reviewed

This task ships no production code, so "review the code" was again read as:
execute the harness and check every published figure against what the harness
actually produces. Nothing below is taken from the developer's round-4 report —
every number marked "measured" came out of a run I made in this session.

Three rounds of non-reproducing figures means prior acceptance is not evidence,
so I re-derived the load-immune columns from scratch again rather than carrying
forward round 3's pass. That decision paid for itself: **one of this round's
blocking findings is in text that I myself accepted in round 3** (finding 4).

### Worktree state, confirmed at start and at end

```
git rev-parse HEAD            -> bc78696 (= master)
git diff --cached --name-only -> docs/tasks/APRAS-93-spec.md
git diff --name-only          -> (empty)
git status --porcelain        -> A  docs/tasks/APRAS-93-spec.md   (and nothing else)
git diff --cached --stat      -> 1 file changed, 1336 insertions(+)
git stash list                -> (empty)
```

Exactly one staged path, nothing unstaged, nothing committed, stash empty.
Re-checked at the end of the session: **identical**. I ran no `stash`, no `add`,
no `commit`, no `push`, and touched no other worktree. My mutant harness copy
lives outside the repository at `scratchpad/rev93mut_r4/`; `dev93/` was read from
and executed but never written to (mtimes unchanged through my session).

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

Before running anything I re-confirmed no script reaches a remote host:
in-memory SQLite throughout, `run.sh`'s synthetic `POSTGRES_URL` is never
connected to, `t_logo.py` reads one local file, `t_route.py`/`t_sweep.py` use
`TestClient` in-process. No production database, no credentialled call.

### Contention discipline

`loadpair.sh` and `gcpair.sh` induce CPU contention. I ran each at **its own
default competitor count** and raised nothing: `loadpair.sh` at `HOGS=8` on an
8-core machine (twice), `gcpair.sh` at `HOGS=12` (once). Both scripts reap their
competitors through an `EXIT`/`INT`/`TERM` trap, and I verified with
`pgrep -fl 'while True: pass'` after every invocation that **no hog survived**.
Final `ps` sweep: clean.

---

## The two blocking findings from round 3: both resolved, and resolved well

### Finding 1 — the warm arm's bimodality. RESOLVED by withdrawal.

The claim is gone, and gone properly. §1.3.2:533-544 opens with the retraction
and names all three of my disproofs by figure (the 54.31 / 69.99 ms medians in
the "empty" gap, the within-process repetitions at 47.7-55.4 ms, and the decisive
one — that 63.51 ms belonged to neither published mode). Correction 8 at :158-172
records it in the cumulative draft history. **I grepped the whole document for
surviving traces** of `bimodal`, `two modes`, `second mode`, `nothing in
between`, `does not change within the process`, `fixed when the process`,
`slow mode`, `fast mode` and `per process`. Every single hit is inside a
retraction, a draft-history entry, or the sentence that explains why the old
design was invalid. `fast mode` and `slow mode` no longer occur at all. **No
dependent inference survives** — I specifically checked §1.3's handling of
63.51 ms (:350-353) and the §1.3.2 drift table row (:511), and both now describe
a floor with a continuous tail rather than a mode.

This is the hard part of a retraction and it was done completely.

### Finding 2 — "not the garbage collector" / "not machine load alone". RESOLVED by withdrawal.

Both claims are gone. `grep -i "not the garbage collector"` returns nothing;
`not machine load alone` survives only at :168 and :594, both times as the
subject of a retraction. The surviving published sentence is the weak one, and it
is the right one:

> "The supportable statement is that the probe failed to implicate cyclic
> collection and that the tail survives without it. Nothing here rules the
> collector out"

"Failed to implicate" is publishable. The document also correctly notes that
`gc.disable()` suppresses only cyclic collection, so "the garbage collector" in
the broad sense was never under test, and it labels contention as **sufficient,
explicitly not exclusive** (:588-598). The "What that does not establish"
paragraph is exactly the honest-but-incomplete posture that should pass review.

---

## The load-bearing new claim: `loadpair.sh`

I read the script before trusting its output, because a blocked version of this
experiment is what produced round 1's sign reversal.

**The design is genuinely paired and interleaved.** `loadpair.sh:28-35`
alternates on pair parity — odd pairs run quiet-then-loaded, even pairs
loaded-then-quiet — so neither arm owns a position. Competitors are spawned
immediately before the contended arm (`:17-25`) and reaped immediately after
(`:26`), so the quiet arm is genuinely quiet. Load average is sampled before and
after each timed arm. This is the opposite of `blocked.py`, which runs all of one
configuration and then all of the other; the contrast is the right one and the
script is correctly built. **This design criticism does not apply.**

**Two independent invocations at 8 competitors, mine:**

| pair | order | quiet | contended |
|---|---|---|---|
| run 1 p1 | quiet first | 38.53 | 51.80 |
| run 1 p2 | loaded first | 38.70 | 54.51 |
| run 1 p3 | quiet first | 39.00 | 50.61 |
| run 1 p4 | loaded first | 39.12 | 52.94 |
| run 1 p5 | quiet first | 38.62 | 57.46 |
| run 1 p6 | loaded first | 38.55 | 61.62 |
| run 2 p1 | quiet first | 40.06 | 64.50 |
| run 2 p2 | loaded first | 39.69 | 59.73 |
| run 2 p3 | quiet first | 38.36 | 74.36 |
| run 2 p4 | loaded first | 38.88 | 61.82 |
| run 2 p5 | quiet first | 38.43 | 53.24 |
| run 2 p6 | loaded first | 39.09 | 58.97 |

**The contended arm was slower in 12 of 12 pairs**, in both orders, at every
quiet-arm value between 38.36 and 40.06 ms. The pooled eight-competitor band is
**50.61-74.36 ms, which brackets 63.51 ms.** The central claim — that contention
reproduces 63.51 ms on demand, so it needs no special mechanism — **reproduces,
and robustly.** This is the strongest piece of evidence in the document and it
holds up.

What does *not* reproduce is the stated precision. My eight-competitor medians
were **53.73** (run 1) and **60.78** (run 2), **58.22** pooled over 12 pairs,
against the published 63.1 — see finding 6. The conclusion survives; the
half-millisecond coincidence does not.

I did not re-run the 1/2/4/6/12/16/24-competitor groups, because the dispatch
forbids raising the competitor count above what the scripts themselves use and
`loadpair.sh`'s own default is 8. That part of the table is carried on the
developer's measurement, and I say so rather than implying coverage I do not
have.

## `gcpair.sh` and the rewritten `t_warmdist.py`

**The probe rewrite fixes two of the three things I flagged.** Reading
`t_warmdist.py`:

- **One regime per process: fixed.** The regime comes from `argv[5]` (`:43`) and
  one process measures exactly one regime. The round-3 defect — both regimes in
  one process on one graph — is genuinely gone.
- **One variable, symmetric heap: fixed.** A single `gc.collect()` at `:55` runs
  on both arms at the same point, *before* the regime is applied at `:56-57`. The
  asymmetric collect I flagged is gone.
- **"Applied before the object graph is built": NOT fixed, and the document says
  it is.** See finding 2. The graph is seeded and pinned at `:48-51`; the regime
  is applied at `:56-57`, i.e. **after**.

**`gcpair.sh` is correctly interleaved across processes** (`:18` alternates which
regime runs first on pair parity) and holds the competitors up for the whole
pair, so both regimes meet the same contention. Run at its default `HOGS=12`:

| pair | gc on | gc off | off − on |
|---|---|---|---|
| 1 | 89.71 | 89.98 | +0.27 |
| 2 | 87.61 | 101.63 | +14.02 |
| 3 | 90.57 | 96.89 | +6.32 |
| 4 | 92.32 | 79.60 | −12.72 |
| 5 | 98.17 | 93.19 | −4.98 |
| 6 | 88.55 | 97.20 | +8.65 |

**All twelve processes landed in the tail (79.60-101.63 ms)**, so the probe
reached the phenomenon this time — in round 3 it never did. The supportable
negative holds: **six processes had cyclic collection off for their whole timed
section and were all in the tail**, so cyclic collection is not necessary to
produce it. And "no detectable effect, not a reversal" is if anything better
supported by my data than by the developer's: I get off-slower in **4 of 6**
(they report 5 of 6) with a paired median of **+3.3 ms** and two sign reversals,
against a within-arm spread of 10.6 ms on the enabled arm. The published
conclusion is correctly weaker than the data.

## Assertions: mutation-proven, not taken on trust

**`t_warmdist.py:77` is real.** In my mutant copy I made one of the thirteen
repetitions render 11 bytes short. The mutation took effect visibly and the
assertion fired:

```
AssertionError: {171496, 171507}
mutant exit = 1
```

Control, unmutated: `byte-identical across all reps: [171507]`, exit 0.

**`t_states.py:79` is real, and I reproduced the document's own mutation output
figure-for-figure.** Mutating `dh._eager_acting_projects` to return `.all()[:-1]`:

```
at 20 40 60 8 :  AssertionError: {176941, 185567}   exit 1
at 20 20 20 6 :  AssertionError: {163584, 171507}   exit 1
unmutated     :  byte-identical ... exit 0
```

The first line matches §1.3's published mutation evidence exactly — but it comes
from a fixture the document does not name. See finding 4.

**The single-state assertion is vacuous, and that matters for `loadpair.sh`.**
`t_states.py:73-79` builds `b` from `out.values()`; with one state in `states`
the set holds one element by construction, which the file's own comment at
`:76-78` admits. I proved the consequence rather than arguing it — with *every*
render mutated 11 bytes short:

```
$ run.sh t_states.py 20 20 20 6 warm
  warm: median 3.26 ms  stmts 2  bytes 171496
byte-identical across the 1 measured state(s): [171496]
single-state mutant exit = 0
```

A wrong byte count passes. See finding 3.

---

## Every figure I re-derived this round

**Exact — zero drift, re-derived from scratch, not carried forward.**

- **§1.1 (`t_sizes`)**: 13,061 / 20,109 / 50,897 / 171,507 / 530,607 /
  1,738,448 B; statements 2 / 4 / 12 / 42 / 122 / 402; per-project slope
  13,061 → 20,109 → 27,161 → 34,213 (+7,048 / +7,052 / +7,052). All exact.
- **The shell law (`fixture_probe`)**: 13,031 / 13,039 / 13,050 / 13,061 B at
  tenant names of 1 / 9 / 20 / 31 chars. Sensitivities exact: project
  description +1, project title +1, bulletin body +3, photo URL +9, milestone
  title +6, bulletin title +3, milestone description 0, contractor 0.
- **§1.2 (`t_route`)**: 2 / 4 / 6 / 12 / 42 / 122 / 402 at N = 0/1/2/5/20/60/200
  — `2N + 2` at all seven, through the real route. The six-statement trace at
  N = 2 matches the document in order and kind.
- **§1.3 at 200, 4 combined runs**: statements 402 / 4 / 2 and 1,738,448 B in all
  three states every run, asserted non-vacuously. Splits **9.8 / 9.7 / 9.5 /
  9.7%**, inside the published **8.1-10.4%**; arms cold 405.1-417.0, eager
  365.6-369.4, warm 39.1-39.8 ms, all inside the published spans.
- **§1.3 at 20, 6 combined runs**: statements 42 / 4 / 2 and 171,507 B every run.
  Splits 14.3 / 14.0 / 14.4 / 14.6 / 13.2% on the five floor runs, inside the
  published **13.2-15.9%**. (A sixth run gave 16.4% with warm at 3.75 ms, above
  the 3.06-3.29 ms floor — excluded by the document's own stated rule that the
  split is computable only when the warm arm is at its floor. The rule earns its
  keep; see Suggestion 3.)
- **§1.3's paired cold-vs-eager (`p200.py`) at 200**: **12/12 to eager, +11.1%**,
  paired diff median +46.1 ms (min +34.0, max +49.8), byte equality asserted and
  true. Inside the published 8.9-15.9%. The headline comparison is solid for the
  third consecutive round.
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
- **§5 (`t_sweep`)**: 160 statements on both arms in all three trials; 684,180 B
  equal on all six arms; unit label `MiB/s`. The sign flips between my trials
  (same-slug 82.7 / 80.6 / 82.5 against distinct-slug 83.4 / 79.4 / 87.7 ms) and
  the within-arm spread again exceeds the between-arm gap, so the **non-finding
  reproduces**.
- **§1.7**: `anyio` **4.14.2**; `current_default_thread_limiter().total_tokens`
  = **40**; both handlers are `def` (`public_projects.py:102`, `:140`).
- **Arithmetic**: 20 / 0.0815 = 245.4 reports/s; 684,180 / 0.0815 = 8.39 MB/s =
  8.01 MiB/s; 40 / 0.0232 = 1,724/s; 40 / 0.6 = 67/s; 42 × 0.219 / 23.2 =
  **0.40×**. All exact.
- **Sample-count reconciliation**: 18 + 31 + 90 = **139** ✓; 104 + 35 = **139** ✓;
  7 + 8 + 8 = **23** ✓; the 35 tail values are correctly sorted. The counts now
  agree between §1.3, §1.3.2, correction 5 and correction 8 — round 3's
  count-mismatch sub-finding is resolved.
- **Citations**: `public_projects.py:45-46` — the quoted sentence "That does
  **not** reverse D3 and it does not claim the report route's policy, which is
  'no limiter'" begins on line 45 and ends on line 46. **Exact.** Round-3
  suggestion 5 properly adopted. The unnumbered quote at :906-907 ("a route
  strictly more amplifying than one that is limited cannot be unlimited on the
  limited one's reasoning") is verbatim at `public_projects.py:51-53`.
  `public_projects.py:139` carries `@limiter.limit("300/minute")` ✓.
- **Harness inventory** at :63-74 lists `t_warmdist.py`, `gcpair.sh` and
  `loadpair.sh`, and its one-line description of the probe ("the cyclic collector
  set once per process from the command line") is **accurate** — it does not
  repeat the error in finding 2.

**Not re-derived this round, so the next reader knows my coverage.**

- §1.4's **0.219 ms loopback anchor** — still labelled "measured once, not
  re-verified"; nothing is listening locally and substituting a production call
  is forbidden. Its derived figures are internally consistent (0.40× re-checked).
- `loadpair.sh`'s **1 / 2 / 4 / 6 / 12 / 16 / 24-competitor rows** — the dispatch
  forbids raising the competitor count past the script's own default of 8. Only
  the 8-competitor row is mine, and it is the row the argument rests on.
- The **`t_sweep` loaded figures** (489.7-569.3 ms) and the §1.3.2 drift-table
  `t_sizes` row (438.80 / 1258.18 / 1990.87 ms) — one-session observations of a
  loaded machine, which the table labels as such; I did not attempt to recreate
  a 21.9 load average.
- `blocked.py`'s 12 trials — reproduced at 2 sign reversals in round 3; not
  re-run.
- The ~30 citations in §4 and §6.1 — carried forward on round 2's exhaustive
  walk and round 3's spot-check. **This remains the thinnest area of coverage
  across all four rounds.**

---

## Blocking Findings

### 1. `docs/tasks/APRAS-93-spec.md:552-556` — "no gap in that sequence exceeds 10 ms" is false on the document's own published numbers. Four gaps exceed it, the largest by 2.9×.

This is the arithmetic that carries the replacement claim. §1.3.2 lists the 35
tail medians and then concludes:

> "— **no gap in that sequence exceeds 10 ms**, so it is a tail and not a second
> mode."

I sorted the published sequence and computed the 35 gaps (the floor ceiling of
44.9 ms to the first tail value, then each successive pair). **Four exceed
10 ms:**

| from | to | gap |
|---|---|---|
| 97.7 | 114.3 | **16.6 ms** |
| 114.3 | 128.2 | **13.9 ms** |
| 128.2 | 156.9 | **28.7 ms** |
| 167.3 | 190.6 | **23.3 ms** |

The largest is **28.7 ms, nearly three times the asserted bound.** This is not a
rounding artefact: the underlying full-precision values (97.71, 114.34, 128.2,
156.94, 167.25, 190.60) give the same gaps to the decimal.

This matters because the sentence is the document's *entire stated justification*
for "a tail and not a second mode" — the one conclusion that replaced the
retracted bimodality. The conclusion is almost certainly still right, and my own
data supports it: the dense region really is dense, and the gaps all sit in the
sparse upper tail where there are only a handful of samples, which is what a tail
looks like. **But the published arithmetic does not hold, and this is the fourth
consecutive round in which a checkable number in this document did not survive
being checked.**

The fix is contained and makes the claim true: the gap bound holds up to 97.7 ms
(max gap 9.4 ms, from the floor ceiling to 54.3; max gap *within* 54.3-97.7 is
5.0 ms), and above that the sample thins. Say that, or drop the numeric bound and
argue continuity from the dense region plus the demonstrated contention
dose-response, which is the stronger argument anyway.

### 2. `docs/tasks/APRAS-93-spec.md:606-607` and `t_warmdist.py:17-18` — the probe does not apply the regime before the object graph is built. It applies it after.

Both the document and the rewritten file's own docstring state:

> "The probe now takes the regime from the command line and applies it **before**
> the object graph is built, so one process measures one regime"

The code does the opposite order:

```
t_warmdist.py:48   seed(s, n_projects=n, milestones=mi, bulletins=bu, photos=ph)
t_warmdist.py:50   pinned = list(s.exec(select(ConstructionProject)).all())
t_warmdist.py:51   held = [(p, list(p.milestones), list(p.updates)) for p in pinned]
t_warmdist.py:55   gc.collect()
t_warmdist.py:56   if regime == "off":
t_warmdist.py:57       gc.disable()
```

The graph is seeded and pinned at `:48-51`; `gc.disable()` runs at `:57`,
**after**. The clause "so one process measures one regime" is true and is the
part that actually answers round 3; the "before the object graph is built"
antecedent is a false statement about the harness, in the very sentence that
justifies the rewrite, repeated in the file that was rewritten. A reader checking
the probe against its description finds them disagreeing.

Note I am *not* asking for the code to change — moving `gc.disable()` above
`seed()` would leave the seeding garbage uncollected on one arm and reintroduce a
second variable, which is worse. The honest fix is the sentence: the regime is
applied once per process, before the timed section begins, after a collect that
both arms share. That is accurate and it is sufficient to answer round 3.

### 3. `docs/tasks/APRAS-93-spec.md:583-585` — the byte-identity control claimed for the `loadpair.sh` runs does not exist. The assertion is vacuous in that mode and the driver discards the byte count.

§1.3.2 says of the 24 contention pairs:

> "The byte count was 1,738,448 B in every one of these runs, **asserted**, so
> every arm rendered the same document."

Two independent reasons that is not supported:

**(a) The assertion cannot bite in a single-state run.** `loadpair.sh:14` invokes
`t_states.py ... warm` — one state. `t_states.py:73-79` builds `b` from
`out.values()`, so with one state the set has one element by construction and
`assert len(b) == 1` is a tautology. The file's own comment at `:76-78` says
exactly this. I proved the consequence rather than asserting it: with every
render mutated 11 bytes short, the single-state run printed `bytes 171496`,
reported "byte-identical across the 1 measured state(s)" and **exited 0**.

**(b) The driver never looks at the byte count anyway.**
`loadpair.sh:14` keeps only field 3 of the `warm:` line —
`awk '/warm:/{print $3}'` — which is the median. The byte column is field 8 and
is thrown away. Nothing in the 24 pairs recorded, compared or checked a byte
count.

The substance is fine — I ran the same invocation and the byte count *is*
1,738,448 — but what the document calls an asserted control is an unexamined
print behind a tautological assert. This is the same defect as correction 7, in
which draft 3 claimed the three-state byte identity was "asserted in the harness"
when the harness only printed it. Having the document re-commit the error it
catalogues, in the paragraph presenting its best new evidence, is what makes this
blocking rather than cosmetic.

Either state it as what it is ("the byte count printed 1,738,448 B on the arms I
inspected; the single-state assertion is structurally vacuous"), or make it real
— capture field 8 in `loadpair.sh` and compare it against 1,738,448.

Separately, and worth knowing even though no published sentence turns on it: the
three-state assertion checks *agreement between states*, never the expected
value. My uniformly-mutated three-state run reported "byte-identical across the 3
measured state(s): [171496]" and exited 0.

### 4. `docs/tasks/APRAS-93-spec.md:286-291` — §1.3's mutation evidence is attached to the wrong fixture. The cited byte counts cannot be reproduced at the fixture the sentence is about.

§1.3 establishes the 20-project fixture and its byte count, then offers the
mutation proof in the next breath:

> "all three states render byte-identical output: **171,507 B** … That assertion
> is mutation-tested: making the eager arm render one project fewer moves its
> output to 176,941 B against the other two states' **185,567 B on the same
> fixture**"

185,567 B is not what that fixture renders. I scanned the fixture space to find
what does:

```
20 20 20 6 -> 171507      <- the fixture the sentence is about
21 20 20 6 -> 179430
22 20 20 6 -> 187353
20 40 60 8 -> 185567      <- where the cited numbers come from
19 40 60 8 -> 176941      <- "one project fewer", same shape
```

The mutation evidence was taken at **20 / 40 / 60 / 8** — 20 projects carrying
the 200-fixture's milestone, bulletin and photo shape — not at 20 / 20 / 20 / 6.
Confirmed by running the document's own mutation at both:

```
20 40 60 8 :  AssertionError: {176941, 185567}   exit 1   <- matches the document
20 20 20 6 :  AssertionError: {163584, 171507}   exit 1   <- the actual same fixture
```

So "on the same fixture" is false, and a reader who tries to reproduce 185,567 at
the fixture named three lines earlier will fail. The assertion itself is
genuinely mutation-proven — I proved it at *both* fixtures — so the fix is to
name the fixture the numbers came from, or to requote the mutation at
20/20/20/6 as `{163584, 171507}`.

I flag this with no pleasure: **I reproduced 185,567 B in round 3 and wrote "on
the same fixture" in my own review**, carrying the error forward instead of
catching it. It is the clearest evidence in this file for the dispatch's
instruction to re-derive figures I had already accepted.

### 5. `docs/tasks/APRAS-93-spec.md:578-580` — "the per-group medians are monotone in the number of competitors" is contradicted by the sequence printed in the same sentence.

> "the per-group medians are **monotone** in the number of competitors:
> 38.7 / 38.4 / 38.9 / 43.7 / 63.1 / 90.8 / 103.4 / 166.6 ms"

38.7 → **38.4** → 38.9 is not monotone in either direction. I recomputed all
eight group medians from the published table and they are right as medians
(38.7 / 38.4 / 38.9 / 43.7 / 63.1 / 90.8 / 103.4 / 166.65); it is the adjective
that is wrong. The sequence **is** monotone from 6 competitors upward, which is
also the range over which the document claims an effect at all — the same
sentence says the contended arm was slower in "0 of 6 pairs below" 6 competitors.

This is a one-word fix ("monotone from six competitors upward") and it is
non-load-bearing. I am listing it as blocking rather than as a suggestion for
consistency: I cannot reject finding 1 for arithmetic that does not hold and then
wave through a second false statement about published data eighteen lines away.
The parenthetical about the 12- and 16-competitor bands shows the author was
already thinking about monotonicity, which makes the oversight the easier to fix.

### 6. `docs/tasks/APRAS-93-spec.md:582` — "its median of 63.1 ms is within half a millisecond of it" does not reproduce. The coincidence is a one-session artefact presented as a result.

The eight-competitor median is stated to three significant figures and its
agreement with 63.51 ms to **half a millisecond**. In two independent `loadpair.sh`
invocations at the same competitor count on the same machine I measured
eight-competitor medians of **53.73 ms** and **60.78 ms**, pooling to **58.22 ms**
over 12 pairs — **5 ms from the published figure, ten times the claimed
agreement**, with 7 ms of spread between my own two invocations.

The underlying conclusion is unaffected and I want that stated clearly: the band
reproduces (50.6-74.4 ms in my hands, 54.7-72.5 in the developer's), it brackets
63.51 ms in both sessions, and the contended arm was slower in 12 of 12 of my
pairs. **Contention being sufficient to produce 63.51 ms is established.** What is
not established is that the group median *lands on* 63.51 — that is a draw from a
distribution whose session-to-session median moves by 7 ms, dressed as a
near-identity.

This is the exact pattern the document itself names at :178-182 — "every claim
this document has had to retract was stated exactly one notch stronger than its
evidence" — and the pattern my own round-3 suggestion 3 asked to be fixed by
widening bounds. State the band and that it brackets 63.51; drop the half
millisecond.

---

## Suggestions

1. **The eight-competitor row would be more durable with the quiet arm's own
   drift beside it.** My quiet arms spanned 38.36-40.06 ms where the developer's
   spanned 38.22-38.67; the contended band moves with the floor. A sentence
   saying the tail scales with the floor would pre-empt the next reviewer
   measuring a lower band than the one published.
2. **Record `loadpair.sh`'s own default in the table.** The table spans 1 to 24
   competitors, but the script's `HOGS` default is 8, so a reviewer following the
   dispatch's "do not raise the competitor count" instruction can only reproduce
   one row. Naming which rows need a non-default `HOGS` would make the other
   seven reproducible by someone with permission to run them.
3. **The floor-run exclusion rule works, and deserves to be stated as a
   numeric threshold.** One of my six 20-project runs gave a 16.4% split, above
   the published 13.2-15.9%, purely because its warm arm sat at 3.75 ms against a
   3.06-3.29 ms floor. The document's rule correctly excludes it, but the rule is
   prose. "Runs whose warm arm exceeded its floor by more than ~10% are excluded"
   would let the next reader apply it the same way the author did.
4. **§1.3.2's drift-table `t_sweep` row (489.7-569.3 ms) and `t_sizes` row
   (438.80 / 1258.18 / 1990.87 ms) are single-session observations on a 21.9
   load average**, and the table labels the session but not the fact that nobody
   has re-derived them since. A "not re-verified" tag like §1.4's would be
   consistent with how the rest of the document handles this.
5. **§4 and §6.1's ~30 citations have not been fully re-walked since round 2.**
   Three rounds of findings have all landed in §1.3/§1.3.2, which is where the
   measurement is — but it means the citation-heavy sections have the least
   recent coverage. Worth one exhaustive pass before this ships.
6. My mutant harness copy is left outside the repository at
   `scratchpad/rev93mut_r4/` as evidence. `dev93/` was not modified; no
   competitor process survived any run.

---

## Verdict

**Both round-3 blocking findings are resolved, and resolved the right way.** The
bimodality is withdrawn completely — I grepped for eight separate traces of it
and every hit is inside a retraction, with no dependent inference left standing,
which is the failure mode I was most worried about. "Not the garbage collector"
and "not machine load alone" are both gone, and the sentence that survived is the
weak one: "failed to implicate … nothing here rules the collector out." The
probe was genuinely rebuilt so it *could* have implicated the collector, and
`gcpair.sh` finally drove it into the tail where the phenomenon lives — all
twelve of my processes landed there, against zero of six in round 3. Contention
is labelled sufficient and explicitly not exclusive. **`loadpair.sh` is a real
experiment, correctly paired and interleaved, and its central result reproduced
in my hands at 12 of 12 pairs with a band that brackets 63.51 ms.** That converts
the figure that started this argument from an anomaly into an ordinary draw, which
is exactly what the document needed. Every byte count, statement count, slope,
citation and piece of arithmetic I re-derived — and I re-derived nearly all of
them from scratch — came out exact, the splits reproduced inside their newly
widened ranges, `p200.py` went 12/12 for the third round running, and both live
assertions are mutation-proven.

I want to be unambiguous that **the honest-but-incomplete posture of §1.3.2 is a
pass, not a finding.** Variance measured, cause not isolated, nothing ruled out,
sufficiency distinguished from exclusivity — that is the document doing its job,
and the new rule it adds to its own lesson list ("prefer the weaker true
sentence") is well earned. Nothing in this review asks for a stronger claim, and
nothing here touches §3's decision, which rests on the statement count and the
byte size — neither of which has moved by one unit in four rounds.

What sends it back is narrower and, I think, undeniable: **six checkable
statements in §1.3 and §1.3.2 do not survive being checked.** One is the
arithmetic that carries the entire replacement claim — "no gap exceeds 10 ms",
against four gaps that do, the largest 28.7 ms. One is a description of the
rewritten probe that the rewritten probe contradicts, in the sentence justifying
the rewrite. One claims an asserted byte-identity control that I proved vacuous
by mutation, re-committing the precise error the document logs as correction 7.
One attaches mutation figures to a fixture that cannot produce them — an error I
carried forward from my own round-3 review. One calls a sequence monotone beside
the numbers that refute it. One states a half-millisecond agreement that moved by
5 ms when I re-measured it.

None of these requires new measurement, no experiment needs redesigning, and no
conclusion in the document has to change — every one is a sentence that overstates
a result the harness already supports, plus one arithmetic claim that needs its
true bound. The document is *close*, and it is much better than it was three
rounds ago. But I cannot approve a document whose stated justification for its
central claim is arithmetic that fails on its own published list, in a review
whose entire standard for three rounds has been that checkable numbers must check
out.

VERDICT: REJECTED

1. `docs/tasks/APRAS-93-spec.md:552-556` — "no gap in that sequence exceeds
   10 ms" is false on the document's own 35 published tail values. Four gaps
   exceed it: 97.7→114.3 (**16.6 ms**), 114.3→128.2 (**13.9 ms**), 128.2→156.9
   (**28.7 ms**, 2.9× the asserted bound) and 167.3→190.6 (**23.3 ms**). This is
   the sole stated justification for "a tail and not a second mode", the claim
   that replaced the retracted bimodality. The bound does hold below 97.7 ms
   (max gap 9.4 ms from the floor ceiling, 5.0 ms within 54.3-97.7).
2. `docs/tasks/APRAS-93-spec.md:606-607` and `t_warmdist.py:17-18` — both state
   the probe "applies [the regime] **before** the object graph is built". It does
   not: the graph is seeded and pinned at `t_warmdist.py:48-51` and
   `gc.disable()` runs at `:56-57`, after. The part that answers round 3 — one
   regime per process, one shared `gc.collect()`, one variable — is correctly
   implemented; only the stated ordering is wrong, and the fix is the sentence,
   not the code.
3. `docs/tasks/APRAS-93-spec.md:583-585` — "The byte count was 1,738,448 B in
   every one of these runs, **asserted**" is unsupported for the 24 contention
   pairs. `loadpair.sh:14` invokes `t_states.py` with a **single** state, where
   `assert len(b) == 1` (`t_states.py:79`) is a tautology over a one-element set
   — the file's own comment at `:76-78` says so, and I proved it: with every
   render mutated 11 bytes short the run printed `bytes 171496` and **exited 0**.
   `loadpair.sh:14` also keeps only `$3` (the median) and discards the byte
   column entirely, so nothing in those runs recorded or compared a byte count.
   This repeats correction 7's own error.
4. `docs/tasks/APRAS-93-spec.md:286-291` — the mutation evidence "176,941 B
   against the other two states' 185,567 B **on the same fixture**" is not on the
   fixture the sentence is about. 20/20/20/6 renders **171,507 B**; 185,567 B and
   176,941 B come from **20/40/60/8** and 19/40/60/8, which I confirmed by
   fixture scan and by running the document's mutation at both — it gives
   `{176941, 185567}` at 20/40/60/8 and `{163584, 171507}` at 20/20/20/6, both
   exit 1. The assertion is genuinely mutation-proven at both fixtures; only the
   attribution is wrong. (I carried this error forward in my own round-3 review.)
5. `docs/tasks/APRAS-93-spec.md:578-580` — "the per-group medians are
   **monotone** in the number of competitors" is contradicted by the sequence in
   the same sentence: 38.7 → **38.4** → 38.9. The medians are correctly computed;
   the sequence is monotone only from 6 competitors upward, which is also the
   only range over which the sentence claims an effect ("0 of 6 pairs below it").
6. `docs/tasks/APRAS-93-spec.md:582` — "its median of **63.1 ms** is within half
   a millisecond of it" does not reproduce. Two `loadpair.sh` invocations at the
   same 8 competitors on the same machine gave eight-competitor medians of
   **53.73** and **60.78 ms**, pooling to **58.22 ms** over 12 pairs — 5 ms off,
   ten times the claimed agreement, with 7 ms of spread between my own two runs.
   The band and the 12/12 direction do reproduce and the sufficiency conclusion
   stands; it is the half-millisecond precision that is a one-session artefact.
