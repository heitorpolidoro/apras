# APRAS-93 — code review, round 5 (final round before the iteration cap)

Date: 2026-10-08. Reviewer worktree:
`/Users/heitor/workspace/apras/.claude/worktrees/agent-a7a31a09fc3ca4bf4` at
`bc78696` (= `master`). Reviewing `docs/tasks/APRAS-93-spec.md` (staged, 1,616
lines) against `docs/reviews/APRAS-93-code-review-round4.md` (my round 4,
REJECTED, six findings).

**VERDICT: APPROVED.** No blocking findings. Two non-blocking items under
`## Suggestions`.

---

## 1. Worktree and production-code state

`git status --porcelain` → exactly `A  docs/tasks/APRAS-93-spec.md`.
`git diff --name-only` → empty. `git diff --cached --name-only` →
`docs/tasks/APRAS-93-spec.md` only. `git stash list` → 0 entries. HEAD `bc78696`.

The five production paths hashed against `git show HEAD:<path>`
(`shasum -a 256` both sides):

| path | result |
|---|---|
| `backend/app/api/v1/endpoints/public_projects.py` | IDENTICAL |
| `backend/app/services/project_report_service.py` | IDENTICAL |
| `backend/app/core/limiter.py` | IDENTICAL |
| `backend/pyproject.toml` | IDENTICAL |
| `backend/requirements.txt` | IDENTICAL |

**ER13 holds: no production code ships.** I made no change to the worktree; it
is as I found it, one staged path.

---

## 2. The six round-4 findings

### Finding 1 — the 10 ms gap bound. RESOLVED by deletion, and the replacement arithmetic is exact.

I recomputed the whole distribution from the 35 sorted values the document
publishes (spec:679-681) plus the 44.9 ms floor ceiling:

```
n = 35;  <= 97.7 ms: 27;  > 97.7 ms: 8          (spec says 27 / 8)          OK
max gap at or below 97.7 ms : 9.4  (44.9 -> 54.3)                           OK
max gap within 54.3-97.7 ms : 5.0  (65.0 -> 70.0)                           OK
gaps > 10 ms: 16.6, 13.9, 28.7, 23.3 — exactly four                         OK
upper span 192.4 - 114.3 = 78.1 ms              (spec says "over 78 ms")    OK
```

Every replacement figure is correct. The bound **and** the "tail and not a second
mode" conclusion are both gone from the body; the only surviving occurrences of
"second mode" / "no gap" (spec:214, 267, 684-685) are the withdrawal narrative
itself, which quotes the dead claim and marks it `**That bound is withdrawn**`.
Spec:694-700 states in as many words that "the shape of the distribution above
97.7 ms is **not established by this document**", with no modal claim in either
direction. The §1.3.2 summary row (spec:636) was updated in step to "dense to
97.7 ms and sparse above" — no dependent sentence left standing, which was this
document's established failure mode.

**The dose-response does carry what the bound used to carry, and it does not
over-reach.** Spec:702-711 states seven of the eight upper values came out of the
contention table (114.3 at 16 competitors; 156.9 / 158.3 / 166.0 / 167.3 / 190.6
/ 192.4 at 24), and that **128.2 ms "is a draft-4 observation and was not
reproduced at any competitor count"**. I grepped every occurrence of `128.2`:
spec:194 and 659 (quotes of the withdrawn bimodality), 681 (the sorted list),
686-687 (the gap arithmetic), 706 (the explicit non-reproduction). **Nothing in
the document leans on the unreproduced value.** The four unpopulated stretches
(39.4-43.7, 43.7-54.7, 97.7-114.3, 114.3-156.9) are named at spec:791-795, and
spec:716 pins the conclusion to the eight-competitor band "**not** on any
statement about gaps" — which is the right dependency.

### Finding 2 — "before the object graph is built". RESOLVED; citations re-grepped and exact.

Verified against the post-edit `t_warmdist.py`: `seed()` at `:51`, the pin at
`:53-54`, the shared `gc.collect()` at `:58`, `if regime == "off": gc.disable()`
at `:59-60`. The spec's citations `:51-54` / `:58` / `:59-60` (spec:820-821) are
exact. The docstring now states the true ordering ("after the graph is seeded and
pinned, after the single `gc.collect()` that both regimes share, and before the
timed section begins"). The spec explains why the code is deliberately
*not* changed (moving `gc.disable()` above `seed()` leaves seeding garbage on one
arm only) — a correct reason, and `t_warmdist.py` is harness, not production.

### Finding 3 — the vacuous byte assertion. RESOLVED, and I re-proved it with my own mutation rather than trusting the reported exit codes.

The fix is real: `loadpair.sh` now captures the byte column (`awk '{print $3, $8}'`),
compares **every** arm against the literal `EXPECT_BYTES=1738448`, additionally
requires all arms to agree, and exits 1 on either failure.

**Control** (`PAIRS="1 2"`, default `HOGS=8`, my machine):

```
pair1 quiet  warm=43.31 bytes=1738448 | pair1 loaded warm=90.11 bytes=1738448
pair2 loaded warm=116.06 bytes=1738448 | pair2 quiet warm=42.21 bytes=1738448
byte identity asserted on all 4 arms: every arm rendered 1738448 B
CONTROL EXIT=0
```

**My own mutation**, built independently at
`scratchpad/rev93r5_mut/` — a *7*-byte truncation (not the developer's 11), so
this is not a replay: `render()` → `get_report_html(session, None)[:-7]`.

```
pair1 quiet  warm=49.17 bytes=1738441
BYTE MISMATCH: pair1 quiet  rendered '1738441' B, expected 1738448 B
pair1 loaded warm=93.88 bytes=1738441
BYTE MISMATCH: pair1 loaded rendered '1738441' B, expected 1738448 B
loadpair.sh FAILED its byte-identity check
MUTANT EXIT=1
```

**The mutation demonstrably took effect** (1738441 = 1738448 − 7) **and the check
fired.** This is a live assertion, not the round-4 vacuity. Note my mutation was
uniform too, so the arms agreed with each other — the comparison against the
literal is what caught it, confirming the developer's reason for implementing
both halves rather than only the paired comparison I suggested. Nothing was left
running: `pgrep -fl 'while True: pass'` → no hog alive, checked after each
invocation and at the end. `HOGS` was never raised above the script default.

The word "asserted" is correctly withdrawn for the 24 earlier pairs
(spec:778-783: "**printed and observed, not asserted**", with the reason —
single-state run, `t_states.py:79` vacuous, driver of the day discarded the
column — and correction 7's repetition named). The surviving "asserted" at
spec:382-383 is the *three*-state run where `assert len(b) == 1` genuinely does
bite; that distinction is correct.

The top-of-document assertion list (spec:78-111) is the strongest part of this
round. All four citations verified exact: `dh.py:249` = `assert b_cold == b_eager`;
`t_states.py:79` = `assert len(b) == 1, b`; `t_warmdist.py:80` =
`assert len(sizes) == 1, sizes`; `loadpair.sh:29-35,57-67`. It volunteers two
limits a reader would otherwise have to find: that `t_states.py:79` is
"**structurally vacuous in a single-state run**", and that both it and
`t_warmdist.py:80` "compare arms with each other rather than against an expected
value, so a uniform mutation passes". That is the honest end state.

### §5 label — checked and honest.

`t_sweep.py:49` is `assert r.status_code == 200, (sl, r.status_code)`. The byte
total is accumulated into `total` and printed in the f-string; **nothing asserts
it**. The spec's label (spec:111-115) — "§5's sweep (`t_sweep.py` asserts only
the HTTP status, at `:49`)" — is accurate, as is the companion note that §1.1,
§1.5 and §1.6 report single-arm counts that "compare nothing and so have nothing
to assert".

### Finding 4 — mutation counts on the wrong fixture. RESOLVED.

Spec:384-394 now names both pairs with their own fixture: `{163584, 171507}` at
20/20/20/6 and `{176941, 185567}` at 20/40/60/8, both exit 1 against an unmutated
exit 0, and records that drafts 4 and 5 said "on the same fixture" when it was
not. 171,507 B matches §1.1's 20/20/20/6 row exactly, and 185,567 ≠ 171,507 is
itself sufficient proof the two came from different fixtures. The attribution is
settled; I ran both mutations last round, so re-running was not required.

### Finding 5 — "monotone". RESOLVED.

I recomputed all eight group medians from the published table: 38.7 / 38.4 /
38.9 / 43.7 / 63.1 / 90.8 / 103.4 / 166.6 ms. Correct as medians. Monotone from
6 competitors upward (43.7 → 63.1 → 90.8 → 103.4 → 166.6); the first three
(38.7 → 38.4 → 38.9) are monotone in neither direction. Spec:739-744 says exactly
that, prints the three refuting values with the reason (three groups drawn from
the same quiet floor), and records the corrected word. The pair counts check:
18 pairs at or above 6 competitors (2+6+2+2+6) and 6 below (2+2+2).

### Finding 6 — the half-millisecond. RESOLVED, and the pooled statistics are exact.

I pooled the 24 contended values from the four invocations, taking runs 1 and 2
per-pair from my own round-4 table (review:123-134):

```
run 1 : band 50.6-61.6  median 53.72   (spec: 50.6-61.6, 53.7)   OK
run 2 : band 53.2-74.4  median 60.77   (spec: 53.2-74.4, 60.8)   OK
table : band 54.7-72.5  median 63.10   (spec: 54.7-72.5, 63.1)   OK
round5: band 58.1-65.5  median 60.27   (spec: 58.1-65.5, 60.3)   OK
pooled: n=24  band 50.6-74.4  median 59.620  -> "59.6 over 24 pairs"  OK
brackets 63.51: True;  run 1 shortfall 63.51 - 61.62 = 1.89 -> "1.9 ms"  OK
```

Every published figure holds, including the self-reported detail that my own run 1
fails to bracket 63.51 on its own — reported at spec:760-762 "rather than
dropped". The half-millisecond precision is withdrawn as a one-session artefact
(spec:763-767) with the 9.4 ms spread given. The added caveat that "the contended
band moves with the floor, so a reader measuring on a faster-floored machine
should expect a lower band" was borne out in my own control: my quiet arms came
in at 42-43 ms against their 38-39, and my contended arms at 90 / 116 ms, above
their band. The document anticipates its own non-reproduction on a different
machine, correctly and in advance.

---

## 3. The sweep — spot-check

I cannot re-derive ~60 claims, so I sampled **20 distinct claims**, weighted
toward sections the six findings did not touch, and checked each against its
cited evidence. Results:

| # | claim | section | result |
|---|---|---|---|
| 1 | fixture deltas +2.3 / 4.6 / 5.5 / 5.3 / 5.4% | §1.1 | **exact** (recomputed from both byte lists) |
| 2 | shell fits `13,030 B + len(name)`, stated as a fit at four lengths | §1.1 | holds; 13,061 ↔ 31 chars, draft 2's 13,062 ↔ 32 |
| 3 | per-project slope +7,048 / +7,052 / +7,052 B | §1.1 | **exact** |
| 4 | bulletins/photos capped, `updates[:3]` / `decode_photos(...)[:3]` at `project_report_service.py:1271-1296` | §1.1 | citation exact; properly hedged as "read off the cap, not isolated in the table" |
| 5 | "20 to 168 KiB across the five fixture shapes §1.1 measured" | §3.1 | holds (19.6 → 167.5 KiB), scope correctly narrowed |
| 6 | 3.44 / 23.23 = 14.8%, so 85.2% | §1.3 | **exact** (14.81%); ER checkbox harmonised to 85% / 14.8% |
| 7 | 91 of 96 paired reps over eight runs in four sessions; 36/36 at 20; 9–47% | §1.3/§6.2 | **reconciles** (5×12 + 12 + 12 + 12 = 96, 5 losses); 8.9–15.9% → "9–16%", 41–47% |
| 8 | "statement count is 4 at every row" | §1.5 | holds in the published table |
| 9 | title length: "moves the constant"; shape "not measured" | §1.5 | deletion 7 correctly implemented — the "not the shape" half is gone and labelled unmeasured |
| 10 | logo would have been 144,046 of 164,155 B = 87.7% | §1.6 | **exact** |
| 11 | `backend/vercel.json` carries a single `routes` entry and nothing else | §2 | verified by reading the file |
| 12 | the named grep `maxDuration\|"regions"\|"memory"\|"functions"` over tracked `backend/` returns nothing | §2 | **ran it — returns only this spec's own prose**; scope correctly bounded to "what the repository pins" |
| 13 | `backend/index.py` is three lines re-exporting `app.main:app` | §2 | holds (4 lines incl. a comment; substantively a re-export) |
| 14 | "Every cache on §3.2's list **that holds a copy** degrades the other way", with the revalidating `ETag` exception named and rejected for its own reason | §3.1 | contradiction with §3.2 genuinely removed, not papered over |
| 15 | 30/min vs shared NAT labelled "**judged**… not a measurement", with what would settle it | §3.1 | honest |
| 16 | no cache dependency in `pyproject.toml` / `requirements.txt`; `Limiter(key_func=get_remote_address)` with no `storage_uri` | §3.2/§6.1 | verified: `limiter.py:6`, no redis/cachetools/aiocache/diskcache/memcache/fastapi-cache |
| 17 | no tracked code writes `detail_json`; docstring at `project_report_service.py:1227-1229`; live NULL-ness "**operator-reported, not measured**" | §1.5 | the docstring quote is verbatim; no tracked writer exists; the unverifiable half is correctly labelled and nothing in §3 depends on it |
| 18 | six `@limiter.limit` call sites; `slowapi>=0.1.10` at `pyproject.toml:20`; cover route decorator at `public_projects.py:139` | §3/§6 | all three exact (the decorator is on line 139, the `def` on 140) |
| 19 | sample counts 18 + 31 + 90 = 139; round 5's 12 deliberately not folded in | §1.3.2 | **reconciles exactly**; the discarded `gcpair.sh` invocation is excluded and said to be |
| 20 | the losing-pair mechanism ("a single scheduling spike… not a crossover") | §1.3 | **properly withdrawn** — spec:528-537 now says "**No claim is made here about what caused them**" and explains that the raw material exists but was never transcribed |

**19 of 20 clean; 1 off-by-one in a non-load-bearing count** (item 17, detailed
under Suggestions). The sweep appears to have worked. The pattern I was looking
for — a deleted claim leaving a dependent sentence standing — I did not find in
any of the twenty, nor in the targeted greps for "second mode", "no gap", "tail",
"asserted", "monotone", "within half", "every render", "every cache", "every
production row", "on demand", "crossover", "point or two" and "proportional".
Every hit outside the correction history resolved to a corrected, narrowed, or
explicitly withdrawn sentence.

---

## 4. Harness and housekeeping

`sh -n loadpair.sh` clean. Nothing remote: `run.sh` cds into the worktree backend
and uses in-memory SQLite with a `POSTGRES_URL` that is never connected to and a
synthetic `SECRET_KEY`; no script I ran reaches a host. No production database
or credentialed API call. No hog processes left alive. No Meridian write, no
commit, no stage, no stash, no other worktree touched.

---

## Suggestions

Both non-blocking. Neither changes a conclusion; neither is worth a sixth round.

1. **`docs/tasks/APRAS-93-spec.md:994` — "four read sites" is three.**
   `git grep detail_json -- backend` reaches three actual code reads in
   `project_report_service.py` (`:1006`, `:1060`, `:1248`); the other hits in that
   file are docstring prose (`:721`, `:944`, `:1219`, `:1227`). The load-bearing
   half of the sentence — "**and no writer**" — I verified independently and it is
   true: no tracked assignment to `detail_json` exists anywhere under `backend/`
   outside tests and the model `Field(...)` declaration. Since round 5 explicitly
   swept for stale internal counts, this one appears to have survived the sweep.
   A reader checking it finds the conclusion intact and the tally one too high.

2. **`docs/tasks/APRAS-93-spec.md:794-795` — leftover edit artefact.** The text
   reads "and the three four unpopulated stretches above the floor are stated
   rather than smoothed over" — "three" was evidently superseded by "four" and not
   removed. The count **four** is the correct one and is enumerated explicitly in
   the preceding sentence, so this is a typo and not an arithmetic error.

---

## Why this is an approval and not a sixth rejection

I went in expecting to find a dependent sentence left standing, because that is
what rounds 1 through 4 all found. I did not find one. What I checked instead:

- every replacement number in findings 1, 5 and 6 recomputes **exactly** —
  9.4 / 5.0 ms, 27/8, 78.1 ms, the eight group medians, the pooled band
  50.6-74.4 and the pooled median 59.620 over 24 pairs;
- the byte check is live under **my own** independently constructed mutation,
  with the mutation visibly taking effect and a non-zero exit;
- the one claim the deleted gap bound used to carry is now carried by the
  dose-response, which states its own hole (128.2 ms never reproduced, four
  unpopulated stretches) and is not leaned on anywhere else;
- the §5 vacuity the developer found on its own, unprompted, is real and is
  labelled correctly.

The document now says "not established", "operator-reported, not measured",
"unverified", "carried forward", "judged", "enough to say nothing was seen, not
enough to bound an effect", and "no claim is made here about what caused them" —
in each place where the evidence stops. Per the review standard for this round,
that is honest incompleteness and the correct end state, not a defect: the
four previous rounds were all about claiming *more* than the evidence supports,
and a document that claims less is the fix. My two findings are a miscount of
citation sites and a typo; neither is a claim the evidence contradicts, neither
is a vacuous check, and neither is an inference depending on something withdrawn.
Blocking on either would be blocking on a suggestion.

ER13 holds, no production code ships, and the worktree is exactly as I found it.

**VERDICT: APPROVED**

Blocking findings: None
