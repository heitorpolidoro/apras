# APRAS-93 — Decide how to make the public obras report cheap to serve without going stale

*(The heading now matches the Meridian card verbatim. The first draft ended
"without going **private**"; the card reads "without going **stale**", and the
card is the operator's. Both themes are covered — staleness by the binding
constraint below, exposure by §5 — but only one of the two titles is canonical.)*

**Type: decision document.** It produces no production code. Its deliverable is
the decision in §3 and the measurements that justify it.
`GET /api/v1/public/tenants/{slug}/projects/report` is live, unauthenticated,
with no rate limit, no cache and no `ETag`, by three explicit operator decisions
(D1, D2, D3). This document is the first time that code existed to be measured
instead of estimated.

**Measurement environment, stated once.** Every figure below was produced on
2026-10-05 against commit `ea37e9a`, on an Apple M1 Pro (Darwin 25.6.0 arm64),
Python 3.13.13 in `backend/.venv`, with a throwaway in-memory SQLite database
built from `SQLModel.metadata.create_all()` — the same shape
`tests/conftest.py` uses. Synthetic fixtures only: **nothing read the production
database and nothing called the production API.** SQL statements were counted by
observation, with a SQLAlchemy `before_cursor_execute` event listener on the
engine, never by reading the code and reasoning about what it would issue. Wall
clocks are medians of 9–11 repetitions after 2 discarded warm-up renders. The
one figure taken against a real TCP Postgres (§1.4) is a read-only `SELECT 1`
against a local development container, never production — and that container is
no longer running, so §1.4 records that figure as measured once and **not
re-verified since the revision round**, rather than silently re-asserting it.

**The fixture's text, pinned — because row counts alone do not fix a byte
count.** Every absolute byte figure below scales with the *length* of the
strings, not only with how many rows there are, so the generator's text is part
of the measurement and is recorded here:

| field | value in the fixture | length |
|---|---|---|
| tenant name | `Condominio Sintetico de Medicao` | 31 chars |
| tenant slug | `sintetico` | 9 chars |
| project title | `Obra sintetica numero {i}` | 22 + `len(str(i))` |
| project description | `'d' * 160` | 160 chars |
| contractor name | `Empreiteira Sintetica Ltda` | 26 chars |
| milestone title | `Frente {m} · Etapa de execucao numero {m}` | 35 chars / **36 B** + 2·`len(str(m))` (the `·` is two bytes) |
| milestone description | `'x' * 80` | 80 chars |
| bulletin title | `Boletim informativo numero {b}` | 27 + `len(str(b))` |
| bulletin body | `'c' * 420` | 420 chars |
| photo URL | `https://exemplo.test/uploads/foto-{j}.jpg` | 38 + `len(str(j))` |

Budgets are `1000000.00` / `400000.00`, physical progress `42.0`, start
`2026-01-01`, estimated completion `2026-12-01`, status `IN_PROGRESS`.
The sensitivity is measurable and small per character but not negligible in
total: at the 1-project shape one extra character of milestone title adds 6 B,
of bulletin body 3 B, of photo URL 9 B, of project description 1 B; the document
shell fits **13,030 B + `len(tenant name)`** exactly at the four name lengths
measured — 13,031 / 13,039 / 13,050 / 13,061 B at 1 / 9 / 20 / 31 characters —
which is a fit on four points and not a proof of linearity at every length. The
absolute `<img>` base URL matters for the same reason and is pinned too:
`PUBLIC_API_BASE_URL` was unset and no `VERCEL_*` variable was present, so
`app.core.urls.public_api_base_url()` fell through to its last rung,
`http://localhost:8000` (`app/core/urls.py:38-56`).

**The harness is kept, not described.** Every figure in this document comes from
a script under
`/private/tmp/claude-501/-Users-heitor-workspace-apras/06230b8a-d0ef-40dd-929b-83bb4eb6abbf/scratchpad/dev93/`:
`dh.py` (fixture generator, statement counter, the paired timer, the eager
variant of `_acting_projects`), `run.sh` (the runner, with a synthetic
`POSTGRES_URL` that is never connected to), `t_sizes.py` (§1.1), `t_route.py`
(§1.2), `t_states.py` (§1.3's three states), `p200.py` (§1.3's paired
cold-vs-eager), `blocked.py` (the discredited blocked design, kept as evidence),
`t_dims.py` (§1.5), `t_logo.py` (§1.6), `t_sweep.py` (§5), `fixture_probe.py`
(the per-character sensitivities above), `t_warmdist.py` (§1.3.2's per-repetition
warm distribution, with the cyclic collector set once per process from the
command line), `gcpair.sh` (interleaves `t_warmdist.py`'s two collector regimes
across processes under induced CPU contention) and `loadpair.sh` (§1.3.2's paired
quiet-versus-contended warm measurement, which since round 5 also asserts each
arm's byte count against the expected literal). Run the Python scripts as
`run.sh <script> [args]`, with an absolute path to the script; the two `.sh`
drivers run directly and take the competitor count in `HOGS`.

**The byte-equality checks in the harness are assertions, all four have been
mutation-tested, and the places where no check bites are named rather than left
for a reader to discover**:

- `dh.py:249` (`assert b_cold == b_eager`, on every pair including warm-ups) —
  fails when the eager arm drops one project, with both byte counts in the
  message, where the unmutated run exits 0;
- `t_states.py:79` (`assert len(b) == 1`) — compares the byte counts of the
  states measured **in one process**, so it bites on the default
  `cold,eager,warm` list and is **structurally vacuous in a single-state run**,
  where the set holds one element by construction (the file says so at `:76-78`).
  Mutation-proven in both directions: three-state runs die as above, and a
  single-state run with *every* render mutated 11 bytes short printed
  `bytes 171496` and **exited 0**. It also checks agreement *between* states and
  never against an expected value, so a uniform mutation passes it.
- `t_warmdist.py:80` (`assert len(sizes) == 1`) — every one of the 13
  repetitions inside one process must render the same byte count.
  Mutation-proven during round-4 code review, which made one repetition render
  11 bytes short and got `AssertionError: {171496, 171507}` and exit 1 against
  the unmutated run's exit 0 (`docs/reviews/APRAS-93-code-review-round4.md`).
  It too compares arms with each other rather than against an expected value.
- `loadpair.sh:29-35,57-67` — added in round 5 precisely because its arms are
  single-state runs, so the `t_states.py:79` point above applies to them. It keeps the byte
  column instead of discarding it, compares **every** arm against the literal
  1,738,448 B, additionally requires all arms to agree, and exits non-zero
  otherwise. Mutation-proven: with `render()` made to emit a document 11 bytes
  short, all arms printed `bytes 1738437`, the driver printed `BYTE MISMATCH` on
  each and **exited 1**; the unmutated control printed 1,738,448 B on all 12 arms
  and exited 0. Note the mutation was uniform, so the arms agreed with each
  other — the comparison against the expected literal is what caught it, and an
  arm-versus-arm comparison alone would not have.

These are the checks that keep "the two arms produce the same document" from
being a prose claim. **Where no such check ran, the document now says the byte
count was *printed and observed*, not *asserted*** — the two places are §5's
sweep (`t_sweep.py` asserts only the HTTP status, at `:49`) and the 24
contention pairs taken before round 5 (§1.3.2). §1.1, §1.5 and §1.6 report
single-arm byte counts, which compare nothing and so have nothing to assert.

**Where the earlier drafts of this document were wrong**, recorded because
APRAS-111's audit (`docs/audits/APRAS-111-test-suite-audit.md`) is about exactly
this failure mode. The list is cumulative and nothing is deleted from it: a
correction that hides its own predecessor is how the third error gets made.

*Against draft 1 (still standing):*

1. The logo is **no longer embedded as a `data:` URI** at all (APRAS-105 removed
   that rung, citing this document's own measurement), so the
   89%-of-the-response figure is historical. §1.6.
2. String assembly is **~14%** of the render at 20 projects, not 10% — and
   **~9.5%** at 200, because its share shrinks as hydration work grows. Draft 1's
   10% was the right order; the claim it got wrong was that assembly mattered.
   §1.3.

*Against draft 2 — this is a correction of a correction, and the earlier claim
it overturned was right all along:*

3. Draft 2 claimed `selectinload` is **not** faster at 200 projects ("eager
   437.7 ms against cold 402.9 ms, slightly *worse*"), retracting draft 1's
   claim that it is faster. **That retraction was itself wrong and is hereby
   retracted.** Re-measured with a paired interleaved design, eager is faster at
   200 projects by **8.9-15.9%** across five independent runs (median paired
   difference **+41.5 to +86.3 ms**, eager winning **55 of 60** paired
   repetitions, and **91 of 96** once code review's three independent runs are
   counted). Draft 1's sign
   was correct. §1.3 gives the figures and §1.3.1 explains why draft 2's design
   could not see them: draft 2 timed all the cold repetitions and then all the
   eager ones — a **blocked** design, which on this machine cannot resolve a
   difference of this size against run-to-run drift. Draft 2's causal story
   ("two `IN (…)` queries cost at least as much as 400 small ones") was built on
   that artefact and is withdrawn with it.
4. Draft 2's absolute **byte** figures came from a fixture whose text lengths
   were never recorded and whose generator was not kept, so they were
   reproducible only in slope. Every byte figure below has been re-measured from
   the pinned fixture above with a harness that is kept; the §1.1 figures move by
   **2.3–5.5%** (the per-row figures are given there; draft 4 said "4–7%", which
   no §1.1 row matches) and no statement count, slope or byte-equality changes.
   **One comparison
   does change in kind and is not buried:** §1.5's "a single project outweighs the
   whole 20-project report" falls from draft 2's 1.12× to **0.98×** on this
   fixture, because which side of 1.0 that ratio lands on depends on the
   fixture's text lengths. It is restated there as the order-of-magnitude claim
   it can actually support.

*Against draft 3 — two figures published as corrections, both of which failed to
reproduce. This is the second consecutive round in which that happened, and the
pattern is the point:*

5. Draft 3 published the warm arm at 200 projects as **63.51 ms** and concluded
   "string assembly ~15% here too, **not the 11% draft 2 reported**". **Both are
   withdrawn.** 139 re-measurements across three sessions put the warm arm's floor
   at about 40 ms, and 23 in-process trials put the split at **8.1-10.4%** — so
   draft 3 retracted draft 2's 11% in favour of a 15% that was *further* from the
   truth than what it replaced. The 63.51 ms is an ordinary draw from the warm
   arm's CPU-contention tail, which reproduces on demand (§1.3.2). The split is
   also not size-invariant,
   which is what "here too" assumed: it falls from ~14% at 20 projects to ~9.5%
   at 200. §1.3.
6. Draft 3 published a **779.5 ms** eager measurement said to show "a 2× error
   from arm order alone", and used it as the stated reason for taking each state's
   figure in its own process. **The figure does not exist and the methodology it
   justified has been reversed.** Twelve trials across two sessions found
   in-process and own-process eager agreeing within 2%. §1.3's figures are now
   taken in **one** process precisely so the warm/cold ratio is a within-process
   comparison, which §1.3.2 shows is the only way a ratio of wall clocks is safe
   here. §1.3.1.
7. Draft 3 told the reader to treat the 200-project wall clocks as **±15%** and
   claimed the three-state byte identity was "asserted in the harness" when the
   harness only printed it. The band is withdrawn — the same measurement varied by
   **4.5×** between runs under load — and the check is now a real assertion,
   mutation-tested. §1.3.2, §1.3.

*Against draft 4 — a mechanism named on evidence that could not name it. One
round, one lesson, and it is the same lesson:*

8. Draft 4 explained the warm arm as **bimodal between processes** ("41.0-44.9 ms
   or 72.2-128.2 ms, with nothing in between", the mode fixed at graph-build time
   and unchanging within a process) and declared the cause **not** the garbage
   collector and **not** machine load alone. **All three claims are withdrawn.**
   The gap is not empty — re-measurement found warm medians throughout it, and
   the probe's own per-repetition output varied *within* processes the claim said
   were fixed. The bimodality excluded **63.51 ms**, the very figure it was
   invoked to explain, which belonged to neither of its modes. The collector was
   "ruled out" by a probe that ran both `gc` regimes in one process on one graph,
   a design whose outcome the claim's own premise predetermined, from a single
   observation of the phenomenon. And "not machine load alone" was the reverse of
   what the data said. §1.3.2 now publishes the pooled distribution, demonstrates
   by a paired interleaved experiment that CPU contention is **sufficient** to
   produce the whole tail, and says in as many words that no mechanism was
   isolated and that the collector was not ruled out. The sample counts are
   reconciled there against the evidence file. §1.3.2.

*Against draft 5 — no conclusion moved, but six checkable statements were
stronger than their evidence, so all six are corrected and the whole document was
then swept for the same defect:*

9. Draft 5 justified "a tail and not a second mode" with "**no gap in that
   sequence exceeds 10 ms**". Four gaps in its own published list exceed it, the
   largest **28.7 ms**. The bound is withdrawn and replaced by what holds — dense
   and gap-bounded to 97.7 ms, too sparse above it for spacing to mean anything —
   with the dose-response carrying the conclusion instead. In the same round:
   (b) draft 5 said `t_warmdist.py` applies the `gc` regime "before the object
   graph is built", which it does not (`:51-54` then `:59-60`); the sentence was
   wrong, the code is right and is unchanged. (c) The byte identity of the 24
   contention pairs was called "**asserted**" when `t_states.py:79` is vacuous in
   a single-state run and `loadpair.sh` discarded the byte column — **correction
   7's own error, re-committed**; the check now exists in the driver, is
   mutation-proven, and the earlier pairs are described as printed-and-observed.
   (d) §1.3's mutation counts (176,941 / 185,567 B) were attributed to
   20/20/20/6, which renders 171,507 B; they come from 20/40/60/8, and the
   assertion is proven at both. (e) The contention medians were called
   "monotone"; they are monotone only from 6 competitors upward. (f) The
   eight-competitor median was said to be "within half a millisecond" of
   63.51 ms; four invocations gave 63.1 / 53.7 / 60.8 / 60.3 ms, so the band
   stands and the precision does not. §1.3, §1.3.2.

**What these five rounds have in common, stated plainly because it is the most
useful thing this document can tell its next reader:** every figure that failed to
reproduce was a *wall clock*, a ratio of wall clocks, or a **mechanism inferred
from one**, and every figure that held was a byte count, a statement count, a
slope, a line reference, or a paired difference. Across five rounds on five
different machine loads, the byte and statement columns have never moved by one
unit. The fourth round adds one rule to the three: **prefer the weaker true
sentence.** "Failed to implicate" is publishable where "ruled out" is not, and
every claim this document has had to retract was stated exactly one notch
stronger than its evidence.

**The fifth round adds a second rule, because by then the defect was no longer in
the measurements at all: every claim must name the evidence that would check it,
and a claim whose evidence is elsewhere must say where.** All six of round 5's
corrections were sentences, not experiments — a bound that failed on the
document's own published list, a description of a file the file contradicts, a
"print" called an "assert", mutation counts attached to the wrong fixture, a
"monotone" refuted by the numbers printed in the same sentence, a precision that
moved by 5 ms on re-measurement. None of them needed a new measurement to find, which means a
reader could have found all six, which means they should never have shipped. Round
5 therefore re-read **every** qualified sentence in this document — every
"asserted", "every run", "never", "no", "exactly", "monotone", "within X of",
"rules out", "cannot" — and either tightened it to what its evidence supports or
named that evidence inline. A mechanical split on that word list returns on the
order of 130 sentence-units, and the sweep is reported as a count of changes
rather than a coverage percentage, because the denominator depends on how one
splits sentences and would be a precise-looking number resting on nothing. The
resulting edit has three parts: the six corrections listed above, **seven claims
deleted outright**, and the remaining qualified sentences tightened or given
their evidence inline. **Where a claim could be made neither true by editing nor
supported by evidence in hand it was deleted, rather than weakened into
vagueness** — and the seven are named here, because a tightened sentence is
visible in the document while a deleted one is visible nowhere: the
10 ms gap bound and the "tail, not a second mode" conclusion it carried; the
half-millisecond agreement; the word "asserted" for the 24 pre-round-5 contention
pairs; "contention reproduces every warm value anyone has observed"; "each
losing pair is a single scheduling spike, not a crossover"; "no drift can move
the warm/cold ratio by more than a point or two"; and "the per-front cost is
proportional to title length, so a different style moves the constant and not the
shape". The decision in §3 rests on the
statement count and the byte size, not on any millisecond figure, and that is why
it has survived all four rounds of corrections unchanged.

## The operator's binding constraint

A freshly published bulletin must be visible immediately. No mechanism that can
serve a stale report to an associate is acceptable. A plain `Cache-Control`
max-age was rejected for exactly that reason: it puts a copy in each visitor's
browser that cannot be invalidated on demand. Everything below is filtered
through that constraint first and cost second.

## 1. The measured cost of one render

### 1.1 Four render sizes, measured

Rendered through `project_report_service.get_report_html` inside
`tenant_context.acting_tenant_scope`, cold each repetition (`expire_all()` +
`gc.collect()`), median of 11 reps.

| projects | milestones/project | bulletins/project | photos/bulletin | median wall clock | response size | SQL statements |
|---|---|---|---|---|---|---|
| 1 | 6 | 3 | 3 | **2.07 ms** | **20,109 B (19.6 KiB)** | 4 |
| 5 | 12 | 8 | 4 | **5.88 ms** | **50,897 B (49.7 KiB)** | 12 |
| 20 | 20 | 20 | 6 | **22.39 ms** | **171,507 B (167.5 KiB)** | 42 |
| 60 | 40 | 60 | 8 | **107.26 ms** | **530,607 B (518.2 KiB)** | 122 |
| 200 | 40 | 60 | 8 | **440.16 ms** | **1,738,448 B (1.66 MiB)** | 402 |

(`t_sizes.py`. Draft 2 published 19,659 / 48,653 / 162,609 / 503,909 /
1,649,451 B here, from the unrecorded fixture of correction 4; the wall clocks
were 2.0 / 5.9 / 23.0 / 103.0 / 406.7 ms. The rows are larger with the pinned
fixture by **+2.3 / +4.6 / +5.5 / +5.3 / +5.4%** row by row — the 1-project row
moves least because the fixed shell dominates it — and otherwise identical,
statement counts included.)

**The byte and statement columns are constants; the wall-clock column is not.**
Every byte count and every statement count above reproduced exactly — in code
review on an independent session, and three further times on re-measurement,
including the per-project slope to the byte. The wall clocks reproduced at
438.80 ms for the 200-project row in one of those three runs and at 1258.18 and
1990.87 ms in the other two, on a machine then at a load average of 21.9. Read
the millisecond column as an order of magnitude on an idle laptop and nothing
finer; §1.3.2 gives the full drift picture and explains which of this document's
figures survive it.

The fixed cost of a render, isolated by rendering a tenant with **zero**
projects: **13,061 B** and **1.20 ms** — that is the stylesheet and the document
shell. Each project of the 1/6/3/3 shape then adds about **7,050 B**
(13,061 → 20,109 → 27,161 → 34,213 B at 0, 1, 2 and 3 projects, i.e. +7,048,
+7,052, +7,052). The shell figure is the one place the two fixtures can be
reconciled exactly: the shell fits `13,030 B + len(tenant name)` at the four
lengths measured, so draft 2's 13,062 B is consistent with a 32-character tenant
name where this one is 31. That fit is what lets the shell be predicted on
another fixture — and the prediction it makes for draft 2's fixture is the fifth
point that holds.

Bulletins and photos are capped in code, so they do not scale the response:
`_updates_html` renders only `updates[:3]` and only `decode_photos(...)[:3]` of
each (`project_report_service.py:1271-1296`), so a project with 60 bulletins and
one with 3 produce the same bytes. Photos are referenced by URL and never
embedded. **That is read off the cap, not isolated in the table above** — those
rows vary bulletin and photo counts jointly with project and milestone counts, so
they are consistent with the cap rather than a measurement of it; §1.5's
dimension-two rows, which hold the project count at one, are where a single
dimension is varied alone.

**No plausible tenant is expensive.** A condominium with 20 simultaneous
construction projects is already implausible; that render is 22 ms of CPU and
168 KiB. The 200-project row is a synthetic ceiling, not a forecast. What would
settle the real row counts, to the same standard §2 names for the instance
count: one `select count(*) … group by tenant_id` over `construction_project`,
`project_milestone` and `project_update` against production, which the operator
can run and this task cannot.

### 1.2 The statement count, measured end to end, and its formula

**The measured count is `2N + 2`** in the number of projects `N`. Measured
through the real HTTP route with FastAPI's `TestClient` — not just the service
function — `GET /api/v1/public/tenants/{slug}/projects/report` issues:

| projects `N` | statements | `2N + 2` |
|---|---|---|
| 0 | 2 | 2 |
| 1 | 4 | 4 |
| 2 | 6 | 6 |
| 5 | 12 | 12 |
| 20 | 42 | 42 |
| 60 | 122 | 122 |
| 200 | 402 | 402 |

The six statements of the `N = 2` case, as the listener saw them:

1. `SELECT tenant.…` — `TenantService.get_by_slug` in the handler;
2. `SELECT construction_project.…` — `_acting_projects`;
3. `SELECT project_update.…` — project 1's `.updates` lazy load;
4. `SELECT project_milestone.…` — project 1's `.milestones` lazy load;
5. `SELECT project_update.…` — project 2;
6. `SELECT project_milestone.…` — project 2.

Worth recording because it is counter-intuitive: the handler's slug lookup does
**not** add a statement on top of the renderer's. `_acting_tenant`
(`project_report_service.py:1500-1510`) calls `session.get(Tenant, …)` for a row
the handler's `get_by_slug` has already put in the identity map, so it is a cache
hit. The route's count and the renderer's count are the same `2N + 2`.

### 1.3 Cold, warm and eager on one fixed render — and what dominates

The experiment that decides whether the fix belongs in caching or in query
shape. One shape, 20 projects / 20 milestones / 20 bulletins / 6 photos, and
**all three states render byte-identical output: 171,507 B** — asserted in the
harness, not eyeballed (`t_states.py:79`, `assert len(b) == 1, b`). That
assertion is mutation-tested at two fixtures, and **each fixture's numbers are
named with the fixture they came from**, because draft 5 attached one pair of
counts to the wrong one: making the eager arm render one project fewer kills the
run with `AssertionError: {163584, 171507}` at this section's 20/20/20/6 fixture
and with `AssertionError: {176941, 185567}` at 20/40/60/8 (20 projects carrying
the 200-row fixture's milestone, bulletin and photo shape), both with exit code 1
where the unmutated run exits 0. Drafts 4 and 5 quoted the 20/40/60/8 pair as
being "on the same fixture" as the 171,507 B above; it is not, and a reader who
tried to reproduce 185,567 B at 20/20/20/6 would have failed. The assertion is
proven at both fixtures; only the attribution was wrong. (Draft 3 only *printed*
this check, so it could not fail a run; code review caught that and it is now an
assertion.)

| state | statements | median |
|---|---|---|
| cold — `expire_all()` + `gc.collect()` each rep | 42 | **23.23 ms** |
| warm — every row hydrated and strongly referenced across the timed render | 2 | **3.44 ms** |
| eager — `selectinload` on `.milestones`/`.updates` inside `_acting_projects`, cold each rep | 4 | **13.59 ms** |

**At this size string assembly is ~15% of the render; ORM data access is the
dominant ~85%.** The warm state issues 2 statements and still produces the same
171,507 B, so 3.44 ms of the cold 23.23 ms is everything that is not data access:
statement construction, `with_loader_criteria` application and row hydration for
the `2N + 2` lazy loads account for the other 19.8 ms. **ORM data access
dominates: 3.44 / 23.23 = 14.8%, so 85.2% on this triple, and 84.1-86.8% across
the twenty trials pooled below.** (Draft 2 put the same split at 16 / 84 on its own fixture,
the independent re-measurement during code review at 14.8 / 85.2, and three
further in-process trials at **14.0 / 14.3 / 14.8%** — cold 23.54-24.95 ms, warm
3.30-3.59 ms, eager 13.85-14.28 ms. All of them agree to about a point and move
the conclusion the same way.) **The ~15% is a figure for this fixture, not for
the route**: it falls to ~9.5% at 200 projects, for the reason given below. Only
the *direction* — data access dominant — is claimed at every size.

Why the warm state is not a production option, and why this matters: SQLAlchemy's
identity map is **weakly** referenced. After a render, only the last project's
`.milestones`/`.updates` survive, held by the loop variable; everything else is
unloaded again, so a re-render that holds no strong reference re-issues all 42
statements. The warm row above had to pin every hydrated row by hand. **A
zero-SQL render of this route requires holding the object graph alive across
requests, which the §2 deployment model does not provide**: each request may land
in a different serverless instance and nothing in the handler retains the graph
between requests. That is an argument from the weak-reference behaviour measured
here plus §2's deployment model, not a measurement of production.
The warm figure is therefore a *floor on string assembly*, not an achievable
state — which is precisely what makes it the right instrument for the
assembly-versus-data-access split.

The same experiment at 200 projects / 40 / 60 / 8 (**1,738,448 B in all three
states**, again asserted) gives cold **439.26 ms** / 402 statements, warm
**41.72 ms** / 2, eager **396.84 ms** / 4 — **string assembly 9.5% of the render
at this size, ORM data access 90.5%.** Those three come from one process running
all three states, so the ratio is a within-process comparison. The split is
computable only in runs of that shape whose warm arm was at its floor, because a
contended warm arm inflates the numerator (§1.3.2); there were **seven** such
runs in the session that published the triple, giving 8.1-9.6%, and across all
three sessions there are **23** — eight more in code review and eight in the
revision round — giving **8.1-10.4%, median 9.6%**. Read the headline as
**about 9.5-10%**; the three-figure bounds earlier drafts published were one
session's trials dressed as a constant. The arms in those runs spanned cold
391.9-450.2 ms, eager 355.5-427.5 ms, warm 37.7-42.7 ms. **Do not read the
cold-versus-eager comparison off these numbers** — that comparison is the
paired measurement below, for the reason §1.3.1 gives.

**The split falls as the fixture grows, and draft 2 was nearer than draft 3.**
**13.2-15.9%** at 20 projects against **8.1-10.4%** at 200 is a real,
reproducible difference, not drift: the two ranges do not overlap, each was
measured within a single process, and both are pooled over three sessions —
twenty trials at 20 projects and twenty-three at 200. (Earlier drafts published
14.0-14.8% and 8.1-9.6%, each from one session's trials. The conclusion is
unaffected; the bounds are widened to what re-measurement actually gives.) It is
the expected direction —
hydration work grows from 400 milestones and 400 bulletins to 8,000 and 12,000,
while string assembly grows only with output bytes, so assembly's *share* must
shrink. **Draft 3 of this document published warm at 63.51 ms at 200 projects
and concluded "string assembly ~15% here too, not the 11% draft 2 reported".
Both halves of that were wrong and are withdrawn.** The 63.51 ms figure is an
ordinary draw from the warm arm's contention tail (§1.3.2): the warm arm run
against eight CPU-bound competitors gave 50.6-74.4 ms over four invocations in
three sessions, a band that brackets 63.51 ms (and three of the four bracket it
on their own), and the warm arm's floor, across 139
measurements in three sessions, is about 40 ms. And draft
2's 11% was *closer* to the 9.5% that
reproduces than draft 3's 15% was, so draft 3 retracted a figure better than its
replacement. The headline — ORM data access dominates — survives at both sizes
and is the only part of this paragraph §3 depends on.

**Why the warm/cold ratio may be taken as a ratio while the eager/cold one may
not.** It is a question of whether the design can resolve the difference it
claims. Warm against cold is **6.8-10.5×** (3.44 ms against 23.23 ms at 20
projects, 41.72 against 439.26 at 200) — an effect of **+575% to +953%**, which
is far larger than any drift measured here, so its *direction and order of
magnitude* survive drift that flips the eager/cold sign. **Its value does not
survive to a point or two**, and the earlier drafts' claim that it did is
withdrawn: code review's five runs on a busy machine put the same within-process
split between **4.7% and 13.2%** (§1.3.2), a 2.8× spread, which is why §1.3
above reads the split only off runs whose warm arm was at its floor. Eager
against cold is **1.1×**, which sits inside the drift at any sampling. The first
is safe to read off medians as a direction; the second is not safe to read off
them at all, and reading it off them anyway is exactly what draft 2 did.

**Note the sign: eager *is* faster, at both sizes.** Draft 2 of this document
said the opposite at 200 projects and it was wrong. The comparison is a
difference of roughly 10% between two arms measured on a laptop, which no blocked design
can resolve, so it is measured **paired and interleaved**: the two arms alternate
inside one loop, order swapped on every pair (ABBA) so neither arm always gets
the first slot, `expire_all()` + `gc.collect()` before each arm, 12 counted pairs
after 2 discarded, byte-equality of the two arms asserted each pair (`p200.py`).

| run | cold median | eager median | median paired diff (cold − eager) | eager faster by | eager wins |
|---|---|---|---|---|---|
| 200 projects, run 1 | **466.1 ms** (412.4–1035.9) | **391.9 ms** (372.8–828.7) | **+66.1 ms** (−10.1 … +236.6) | 15.9% | **10 / 12** |
| 200 projects, run 2 | **400.2 ms** (382.6–453.7) | **358.5 ms** (343.5–427.8) | **+41.8 ms** (−18.8 … +81.5) | 10.4% | **11 / 12** |
| 200 projects, run 3 | **407.7 ms** (390.8–449.9) | **362.6 ms** (352.7–389.0) | **+41.5 ms** (+18.0 … +69.7) | 11.1% | **12 / 12** |
| 200 projects, run 4 | **508.5 ms** (437.9–2862.0) | **463.1 ms** (415.9–1132.4) | **+42.9 ms** (−7.5 … +1729.6) | 8.9% | **11 / 12** |
| 200 projects, run 5 (re-measured) | **495.5 ms** (472.9–1215.9) | **432.2 ms** (392.0–637.5) | **+86.3 ms** (−21.2 … +578.3) | 12.8% | **11 / 12** |
| 20 projects (control) | **22.4 ms** (21.0–23.6) | **13.2 ms** (12.6–13.9) | **+9.1 ms** (+7.2 … +10.5) | 41.3% | **12 / 12** |
| 20 projects (control, re-measured) | **28.6 ms** (26.6–31.7) | **15.1 ms** (14.3–18.3) | **+13.3 ms** (+10.2 … +16.2) | 47.1% | **12 / 12** |

**Eager is faster at 200 projects in every one of five independent runs, by
8.9–15.9%, winning 55 of 60 paired repetitions; at 20 projects it is faster by
41–47%, 24 of 24.** Code review measured the same thing independently — 12 / 12
and 12 / 12 at 200 projects, eager faster by 11.3% and 13.4%, plus 12 / 12 at 20
by 45.2% — and round-4 code review ran it once more, 12 / 12 at 200 by 11.1%
with a paired diff median of +46.1 ms
(`docs/reviews/APRAS-93-code-review-round4.md`), so the sign now stands on
**91 of 96 paired repetitions at 200 across eight runs in four sessions, and
36 of 36 at 20**. This is the one comparison in
the document that held its sign and rough magnitude through the load excursions
§1.3.2 records, which is the property the paired design was adopted for.
Every pair was asserted byte-identical as it was timed —
1,738,448 B at 200 projects, 171,507 B at 20 — so the two arms are doing the same
work and producing the same document.

**Runs 1, 4 and 5 are the argument for pairing, not noise to be apologised for.**
This machine was busy during all three (cold maxima of 1,036 ms, 2,862 ms and
1,216 ms against medians near 400 ms), and the *absolute* medians duly wander from
400 to 508 ms — a 27% swing between runs, more than twice the effect being
measured. The paired difference does not wander with it: +41.5, +41.8, +42.9,
+66.1 and +86.3 ms, with the sign never reversing in any run. That is precisely
the property a blocked design throws away — and §1.3.2 shows the swing is in fact
much worse than 27% for scripts that do not pair, up to 4.5× on the same
measurement. The five losing pairs out of 60 are all small — the four that were
recorded individually are −7.5, −10.1, −18.8 and −21.2 ms, against winning
differences of tens of milliseconds; the fifth is in run 1 and its value was not
retained, which is a gap in the evidence file and is recorded as one. **No claim
is made here about what caused them**: earlier drafts called each "a single
scheduling spike inside the eager arm, not a crossover of the two
distributions". `p200.py:38-41` does print both arms of every pair, so the raw
material exists, but none of it was transcribed into this document and no
analysis of it is published here — so the claim rested on nothing a reader could
check, and calling a single slow repetition a "scheduling spike" would be a
mechanism named from one observation, which is the error corrections 5 and 8
record. What the data published here supports is the size comparison, and that
is all that is claimed.

So the causal story has to run the other way round from draft 2's. **The 400
small statements are not free: each one carries statement construction,
`with_loader_criteria` application, cursor setup and a result-set teardown, and
two bulk `IN (…)` queries pay that fixed cost twice instead of four hundred
times.** That is why eager wins at *both* sizes rather than only the small one,
and why the win shrinks from 41% to ~11% as the hydration work — 8,000 milestones
and 12,000 bulletins, identical in both arms — grows to dominate the fixed
per-statement cost it removes. `selectinload` buys statement *count*, which is
worth a great deal once a statement costs a round trip (§1.4), **and** it buys
CPU at every size measured here.

### 1.3.1 Why draft 2 got the sign wrong, and what the design rule is

Recorded rather than quietly overwritten, because the only thing holding this
document up is that its figures can be re-derived, and because the same mistake
is available to the next person who times two code paths on a laptop.

Draft 2 used a **blocked** design: all the cold repetitions, then all the eager
repetitions, and it compared the two medians. Both arms then sit in different
slices of wall-clock time, so anything that drifts between them — CPU thermal
state, background load, and in this program the heap the first arm leaves
behind — lands entirely in the difference. The effect being measured is ~10%; the
drift is of the same order or larger. The design cannot separate them, and what
it reports is whichever happened to be bigger.

That is not an argument from theory; `blocked.py` reproduces it on this machine,
four trials of the very same two code paths at 200 projects:

| blocked trial | cold | eager | verdict it reports |
|---|---|---|---|
| 1 | 409.9 ms | 368.0 ms | eager faster, +10.2% |
| 2 | 424.7 ms | 380.2 ms | eager faster, +10.5% |
| 3 | 409.8 ms | **433.1 ms** | **cold faster, −5.7%** — draft 2's sign |
| 4 | 416.5 ms | 394.6 ms | eager faster, +5.3% |

One trial in four reports the opposite conclusion, and the magnitudes range over
16 points. **That table is a record of one session, not a published constant.**
The sign reversal is intermittent and the magnitudes are not reproducible: across
three sessions of the identical script the flip rate was 1 in 4 (above), 1 in 8
during code review — with one further trial off by +76 points and one by −178 —
and 0 in 8 on re-measurement, where eight trials spanned **+6.9% to +19.1%**, a
12-point range with no reversal. **2 reversals in 20 trials, and a magnitude
spread wider than the effect, is the finding**; any particular row above is not.
The paired design, on the same machine and the same fixture, answers the same
question 91 times out of 96 the same way across eight runs in four sessions, and
never once reverses the sign of a run.

**A claim withdrawn here.** Draft 3 of this document asserted that running cold,
then eager, then warm in one process "reports eager at **779.5 ms**, against
396.45 ms for the identical eager measurement in its own process — a 2× error
from arm order alone, **which is why** the three single-state figures above are
taken one process each". **The figure and the inference it carried are both
withdrawn.** Code review ran exactly that configuration three times and got eager
at 395.37 / 394.37 / 396.12 ms against 395.34 ms own-process; re-measurement ran
it nine more times and got 392.1-398.6 ms in-process against 396.8-400.8 ms
own-process. Twelve trials, agreement within 2%, no artefact of any size in
either direction. Nothing was measured that the 779.5 ms figure describes.

This matters beyond the number, because the methodology it was offered as the
reason for has now been reversed: the §1.3 figures above are taken **one process
running all three states**, precisely so that the warm/cold ratio is a
within-process comparison. There is no measured penalty for doing so, and there
is a measured cost to the alternative — §1.3.2 shows that absolute wall clocks on
this machine drift enough between processes to make any cross-process ratio
unsafe. One process per state remains available for isolating a single arm, but as
hygiene, not because of a 2× error that does not exist.

**The rule this document now holds itself to.** Any A-versus-B figure here must
come from a design that can resolve the difference it claims: paired,
interleaved, order-alternating, with the per-pair differences and the win count
published and not just two medians. Single-state figures (§1.1, §1.5) are
unaffected — they compare nothing — and they reproduced on an independent fixture
during code review. §5's two sweep rows *are* a comparison, so they are held to
the same rule: three alternating trials, reported in full, with the explicit
finding that the sign flips between them (§5). **Every absolute wall clock in this
document is subject to §1.3.2's drift and none of them is a published constant;
the byte counts and statement counts are.**

A figure that cannot be resolved that way is to be
labelled unresolved, with what would settle it, exactly as §1.4 does for
production RTT and §2 for the instance count — never replaced by another
unresolvable figure.

### 1.3.2 How far the wall clocks drift, and which figures survive it

Draft 3 told the reader to treat the 200-project wall clocks as **±15%**. That
band is too narrow and is withdrawn. Re-measured on the same fixture — the first
three rows in one session under a load average of 21.9, the `t_states` rows
pooled over all three measuring sessions, each row labelled with its sample — the
same scripts produced:

| measurement | published | observed on re-measurement | spread |
|---|---|---|---|
| `t_sizes` render at N = 200, 3 runs | 440.16 ms | 438.80 / 1258.18 / **1990.87 ms** | **4.5×** |
| `t_sizes` byte count at N = 200, 3 runs | 1,738,448 B | 1,738,448 B every run | **0** |
| `t_states` cold at 200, 30 in-process runs, 3 sessions | 428.30 ms | 391.9-997.7 ms | **2.5×** |
| `t_states` eager at 200, 30 in-process runs, 3 sessions | 396.45 ms | 355.5-782.4 ms | **2.2×** |
| `t_states` warm at 200, 139 runs, 3 sessions | 63.51 ms | 37.7-192.4 ms; 37.7-44.9 ms in 104 of them, dense to 97.7 ms and sparse above | **5.1×** |
| `t_sweep` 20 requests, total | 80.9 ms | 489.7-569.3 ms | **6-7×** |

So the honest statement is not a percentage band at all: **an absolute wall clock
here can be off by a factor of several if the machine is busy, and no band stated
in advance covers that.** What survives is (a) every byte count and statement
count, which were identical in every run of every script at every size, in all
three sessions; (b) ratios taken between arms measured *inside one process*,
which is why §1.3 now takes them that way — **substantially** more robust, not
immune: code review's five runs under a busy machine gave within-process splits
of 4.7 / 6.3 / 7.0 / 10.1 / 13.2%, a 2.8× spread, because the warm and cold arms
do not absorb contention proportionally, so these ratios are only trustworthy
when the run was quiet and the document says which runs were; and (c) the paired
design of §1.3's cold-versus-eager table, which re-measured at **+12.8%, eager
winning 11 of 12** at 200 and **+47.1%, 12 of 12** at 20 — the sign and rough
magnitude held under exactly the load that moved `t_sweep` by 6×. The reader
should take
conclusions from (a), (b) and (c), and treat every bare millisecond figure as an
order-of-magnitude anchor.

#### The warm arm: a hard floor, a dose-responsive tail, and no isolated mechanism

**Draft 4 of this document claimed the warm arm was *bimodal between processes* —
41.0-44.9 ms or 72.2-128.2 ms "with nothing in between", the mode "fixed when the
process builds its pinned object graph and does not change within the process" —
and claimed the cause was neither the garbage collector nor machine load alone.
All of that is withdrawn.** Each half failed on its own evidence. Code review
measured warm medians of **54.31** and **69.99 ms** inside the gap declared
empty, and `t_warmdist.py`'s own per-repetition output showed single repetitions
at **47.7 / 50.5 / 51.7 / 52.0 / 55.4 ms** *within* processes that were otherwise
at the floor, which contradicts "does not change within the process" directly.
Worst of all, **63.51 ms — the draft-3 figure the bimodality existed to explain —
belonged to neither published mode**, so the explanation excluded its own
subject. The two modes were an artefact of fourteen samples, and the stated
sample count was itself wrong: see the reconciliation at the end of this section.

What 139 pooled warm medians across three sessions show is a **dense floor** —
**no measurement of the 139 fell below 37.7 ms**, and 104 of them sit at
37.7-44.9 ms — followed by progressively sparser values up to 192.4 ms. The
floor itself drifts a little between sessions: 41.0-43.7 ms in the session that
published 41.72, 39.3-44.9 ms in code review's, 37.7-39.9 ms across 54 quiet runs
in the revision round, and 38.6-39.8 ms across the six quiet arms re-measured in
round 5. The remaining **35**, sorted, are 54.3 / 54.7 / 57.5 / 61.8 / 64.4 /
65.0 / 70.0 / 72.2 / 72.5 / 73.7 / 74.9 / 78.2 / 80.2 / 80.4 / 82.0 / 82.6 /
84.1 / 85.1 / 85.3 / 85.6 / 87.6 / 89.4 / 89.8 / 92.5 / 94.4 / 96.3 / 97.7 /
114.3 / 128.2 / 156.9 / 158.3 / 166.0 / 167.3 / 190.6 / 192.4 ms.

**Read as spacing, the sequence behaves differently below and above 97.7 ms, and
draft 5's single-bound description of it was false.** Draft 5 wrote "no gap in that
sequence exceeds 10 ms, so it is a tail and not a second mode". **That bound is
withdrawn**: four gaps exceed it — 97.7→114.3 (16.6 ms), 114.3→128.2 (13.9 ms),
128.2→156.9 (**28.7 ms**, nearly three times the asserted bound) and
167.3→190.6 (23.3 ms). What is true, and is all that is true:

- **up to 97.7 ms the sequence is dense and gap-bounded.** 27 of the 35 lie at
  54.3-97.7 ms; the largest gap anywhere at or below 97.7 ms is **9.4 ms** (the
  44.9 ms floor ceiling to the first value, 54.3), and the largest gap *within*
  54.3-97.7 ms is **5.0 ms** (65.0 → 70.0). Two further readings at 43.7 ms (see
  the contention table below) sit just above the floor.
- **above 97.7 ms the sample is too thin for its spacing to mean anything.**
  Eight values spread over 78 ms will have gaps of tens of milliseconds whatever
  the underlying distribution, so **no claim about modes is made from this
  region in either direction** — neither that it is continuous nor that it is
  separate. The shape of the distribution above 97.7 ms is **not established by
  this document.**

**What replaces the gap argument, and does not depend on it, is the dose-response
below.** **Seven of those eight** upper values came out of the contention table
itself, produced on demand by raising the competitor count: 114.3 ms at 16
competitors and 156.9 / 158.3 / 166.0 / 167.3 / 190.6 / 192.4 ms at 24, with the
quiet arm of the same pairs at 38.3-39.9 ms throughout. The eighth, **128.2 ms,
is a draft-4 observation and was not reproduced at any competitor count** — it
sits between the 16- and 24-competitor bands and nothing in this document
accounts for it beyond that. So the upper region is largely accounted for by how
much contention the arm met, which is a measured input, rather than by a property
of the process — and that is the argument that the retracted bimodality needed
and never had. No dose populated 45-54 ms — the full list of stretches no dose
reached is given under "What that does not establish" below — and that is where
code review's within-process repetitions (47.7 / 50.5 / 51.7 / 52.0 / 55.4 ms)
fall, in it and just above it.

**63.51 ms therefore needs no special mechanism**, and that conclusion rests on
the eight-competitor band below, which brackets it across four invocations in
three independent sessions, **not** on any statement about gaps.

**Concurrent CPU contention is sufficient to produce warm values across the whole
observed range, 63.51 ms among them.** This is
the one claim in this subsection taken by a design that can carry weight, so it
is reported in full. `loadpair.sh` measures the warm arm twice per pair — once on
the idle machine, once while *N* CPU-bound competitor processes run — alternating
which arm goes first, on an 8-core machine:

| competitors | warm median, contended arm | warm median, quiet arm of the same pairs |
|---|---|---|
| 1 / 2 / 4 | 38.4 / 39.0, 37.8 / 39.0, 38.4 / 39.4 ms | 38.0-38.9 ms |
| 6 | 43.7 / 43.7 ms | 38.8 / 38.8 ms |
| **8** (= cores) | 54.7 / 57.5 / 61.8 / 64.4 / 65.0 / 72.5 ms | 38.2-38.7 ms |
| 12 | 85.3 / 96.3 ms | 39.1 / 39.3 ms |
| 16 | 92.5 / 114.3 ms | 39.3 / 39.3 ms |
| 24 | 156.9 / 158.3 / 166.0 / 167.3 / 190.6 / 192.4 ms | 38.3-39.9 ms |

The contended arm was slower in **18 of 18 pairs at or above 6 competitors and in
0 of 6 pairs below it**. The per-group medians are 38.7 / 38.4 / 38.9 / 43.7 /
**63.1** / 90.8 / 103.4 / 166.6 ms for 1 / 2 / 4 / 6 / 8 / 12 / 16 / 24
competitors — **monotone from 6 competitors upward**, which is also the only
range in which any effect was seen at all; the first three are 38.7 → 38.4 → 38.9
and are not monotone in either direction, which is what three groups drawn from
the same quiet floor look like. (Draft 5 called the whole sequence monotone,
beside the numbers that refute it; that word is corrected here.) The 12- and
16-competitor bands overlap; their medians do not.

**The eight-competitor group is the row the argument rests on, so its
reproducibility is reported in full rather than summarised.** Four independent
invocations at 8 competitors, three sessions:

| invocation | contended band | group median | contended arm slower |
|---|---|---|---|
| the table above | 54.7-72.5 ms | 63.1 ms | 6 / 6 |
| code review, run 1 | 50.6-61.6 ms | 53.7 ms | 6 / 6 |
| code review, run 2 | 53.2-74.4 ms | 60.8 ms | 6 / 6 |
| round 5, re-measured | 58.1-65.5 ms | 60.3 ms | 6 / 6 |

**What reproduces is the direction and the band: 24 of 24 pairs across four
invocations, a pooled band of 50.6-74.4 ms that brackets 63.51 ms, and a pooled
median of 59.6 ms over 24 pairs.** Three of the four invocations bracket 63.51 ms
on their own; code review's run 1 topped out at 61.6 ms, **1.9 ms below it**, and
is reported here rather than dropped. What does **not**
reproduce is the precision draft 5 claimed for it. It said the
group median "is within half a millisecond of" 63.51 ms; the session-to-session
medians are 63.1 / 53.7 / 60.8 / 60.3 ms, a 9.4 ms spread, so **the
half-millisecond agreement was a one-session artefact and is withdrawn.** The
conclusion needs only the band: a value of 63.51 ms is an ordinary draw at this
competitor count, which is what the retracted bimodality was invoked to explain.
The quiet arms moved between sessions too — 38.2-38.7 ms here, 38.4-40.1 in code
review's two runs, 38.6-39.8 in round 5's — and the contended band moves with the
floor, so a reader measuring on a faster-floored machine should expect a lower
band and not read that as a failure to reproduce.

**The byte count, stated as what was actually checked.** Every arm printed
1,738,448 B, and in round 5 that is **asserted per arm by the driver**:
`loadpair.sh` keeps the byte column and compares it against the literal, mutation
proven (see the harness-assertions list at the top of this document). Round 5's
re-measurement passed that check on **all 12 of its arms**. For the 24 pairs
taken in earlier rounds the figure was **printed and observed, not asserted** —
each arm is a single-state run, where `t_states.py:79` is vacuous, and the
driver of the day discarded the byte column. Draft 5 called those runs
"asserted", which re-committed correction 7's exact error; that word is withdrawn
for them and the check now exists for runs taken from here on.

**What that does not establish.** Sufficiency is not exclusivity: we have shown
contention *can* produce the tail, not that nothing else does, and no other
candidate was eliminated. The cause of any *particular* historical slow reading
is not recoverable. The claim is also bounded by what was sampled: the
competitor counts tried were 1 / 2 / 4 / 6 / 8 / 12 / 16 / 24, and between them —
with `gcpair.sh`'s twelve 12-competitor processes added — the doses produced warm
medians in **37.8-39.4, 43.7, 54.7-72.5, 74.9-97.7, 114.3 and 156.9-192.4 ms**.
**Nothing was produced in 39.4-43.7, in 43.7-54.7, in 97.7-114.3 or in
114.3-156.9 ms.** So the observed *range* is spanned by a dose at each end and in
the middle, but not every value inside it was reproduced, and the four
unpopulated stretches above the floor are stated rather than smoothed over.

Note also that the
**one-minute load average is a poor instrument here** — the quiet arms above
stayed at 38.0-39.9 ms at reported load averages from 3.3 to 39.3, and round 5's
quiet arms stayed at 38.6-39.8 ms while the reported average climbed from 8.2 to
17.8, so the reading does not track the contention the arm actually met. The
usual explanation is that a one-minute average lags; this document measured the
mismatch and did not measure the lag. Draft 4's "it is also not machine load alone"
rested on two readings of a clean cold arm beside a slow warm arm; the cold arm
takes 13 collected renders over ten times the wall clock and averages contention
the warm arm meets head-on, so that comparison was never evidence. Contention is
the live and only demonstrated hypothesis.

**The cyclic collector: not implicated, not ruled out, and the tail does not need
it.** `t_warmdist.py` was **rewritten in round 4** because the previous design
could not have implicated the collector, and so could not exonerate it: it ran
both `gc` regimes inside one process on a graph built once, which under draft 4's
own "fixed per process" premise predetermined the outcome, and its `gc`-off arm
ran after a `gc.collect()` the `gc`-on arm never had. **The probe now takes the
regime from the command line, so one process measures exactly one regime; the
regime is applied once, before the timed section begins, immediately after a
single `gc.collect()` that both arms run at the same point.** That ordering is
stated precisely because draft 5 stated it wrongly: it said the regime
is applied "before the object graph is built", and it is not — `t_warmdist.py`
seeds and pins the graph at `:51-54`, runs the shared `gc.collect()` at `:58` and
applies the regime at `:59-60`, **after** both. The code is correct as it stands
and is deliberately not changed:
moving `gc.disable()` above `seed()` would leave one arm carrying the seeding
garbage and reintroduce the second variable the rewrite removed. It is the
sentence that was wrong, and the part that answers the previous round — one
regime per process, one shared collect, one variable — is what the code does.
`gcpair.sh` then interleaves the two regimes *across* processes under induced
contention, because a regime comparison taken only at the floor says nothing
about the tail. Twelve processes under 12 competitors, six pairs, all
twelve in the tail: `gc` enabled **74.9 / 78.2 / 80.2 / 80.4 / 82.0 / 89.4 ms**,
disabled **82.6 / 84.1 / 85.1 / 85.6 / 89.8 / 97.7 ms**. So **the tail is present
in six processes that had cyclic collection switched off for their whole timed
section** — cyclic collection is not *necessary* to produce it, which is the one
conclusion this probe carries. The paired difference ran opposite to the
hypothesis — disabled slower in 5 of 6 pairs, median +6.4 ms — **but note the
lists above are sorted, so the pairing is not recoverable from them and a reader
cannot re-derive that 5 of 6 from what is published here**; it is reported as a
summary of the run log, not as something this document lets you check. An
independent `gcpair.sh` invocation during round-4 code review
(`docs/reviews/APRAS-93-code-review-round4.md`) put it at off-slower in 4 of 6
with a paired median of +3.3 ms and two sign reversals, again with all twelve
processes in the tail. Either way the within-arm spread, 74.9-89.4 ms on the
enabled arm, is as wide as the gap, so this is **no detectable effect**, not a
reversal. At the floor no difference was resolvable either: four interleaved
pairs gave 38.7-39.5 ms enabled against 38.7-39.1 ms disabled, which is four
pairs — enough to say nothing was seen, not enough to bound an effect. And
`gc.disable()` suppresses only the
*cyclic* collector — reference counting, allocator behaviour and page-fault cost
are untouched — so "the garbage collector" in the broad sense was never under
test at all. **The supportable statement is that the probe failed to implicate
cyclic collection and that the tail survives without it. Nothing here rules the
collector out**, and the one-word difference is the whole point: draft 4 wrote
"ruled out" on a probe that could not have ruled anything in.

**So the published 41.72 ms is a floor figure, and the floor is all it is.** It is
the floor on string assembly that §1.3 needs, it is not an achievable production
state for the reason §1.3 gives, and it carries about two significant figures:
read it as "about 40 ms". Every conclusion §1.3 draws from it is a ratio or a
direction, and §3's decision rests on the statement count and the byte size,
neither of which has moved by one unit in four rounds.

**Sample counts, reconciled against the evidence file** — because a count that
moves between paragraphs means the figure was not re-derived. The publishing
session took **18** warm medians at 200/40/60/8, 13 at the floor and 5 in the
tail; draft 4's "fourteen measurements, nine fast / five slow" undercounted its
own evidence and is corrected here and in correction 5. Code review took **31**
(18 warm-only, all at the floor, plus 13 in-process). The revision round took
**90** (54 quiet, 36 under induced contention), giving the 139 pooled above.
**Round 5's 12 further warm medians — 6 quiet at 38.6-39.8 ms and 6 contended at
58.1-65.5 ms — are reported in the eight-competitor table above and are
deliberately *not* folded into the 139**, which stays the three-session pool the
distribution figures are computed from; folding them in silently is how a count
stops matching its own evidence file. One further
12-process `gcpair.sh` invocation in the revision round was discarded
unanalysed, because a
parsing fault in the driver lost one arm of every pair; its surviving `gc`-off
medians, 76.5-87.7 ms, fall inside the band reported above, and it is excluded
from the 90 rather than quietly folded in. §1.3's "seven trials" are a different
and narrower set, now said in those words there: the
seven combined `cold,eager,warm` runs whose warm arm was at the floor, which are
the only runs in which the within-process split is computable at all.

### 1.4 Round trips are a multiplier on the dominant term

The `2N + 2` lazy loads re-execute on **every render that does not hold the
previous render's object graph behind a strong reference** — which is every
production render, because the identity map is weakly referenced (§1.3) and
nothing in the handler retains the graph between requests. §1.3's 2-statement
warm arm is the only measured exception and it needed a manual pin. Each lazy
load carries a round trip to Neon.
So production wall clock is `CPU + (2N + 2) × RTT`, where the second term
multiplies the part that already dominates locally.

What was measured: a read-only `SELECT 1` against a real TCP Postgres on
loopback, 400 samples through SQLAlchemy — **median 0.219 ms** (p90 0.272 ms),
with a bare TCP connect to the same socket at 0.154 ms. That is a measured
**floor** on what one statement costs when it has to leave the process. At the
20-project case it puts the round-trip term at 42 × 0.219 = **9.2 ms against
23.2 ms of CPU, i.e. 0.40×** the CPU term — on loopback.

**Status of that 0.219 ms anchor at revision time: measured once, not
re-verified.** Nothing is listening on `localhost:5432`, `5433` or `55432` on
this machine now, so the local development Postgres that produced it is down and
the figure could not be taken again in the revision round or in round 5; the
independent re-measurement
during code review hit the same wall. Production was not substituted and no
credentialled call was made. It is an anchor and not load-bearing — the 27×
below already rests on an assumption that is labelled as one — but it is recorded
here as *unverified since it was taken* rather than quietly re-asserted. What would
settle it: `docker compose up` the development Postgres (`polidoro-runner` owns
the shared services) and re-run the 400-sample `SELECT 1`; the figure to beat is
0.219 ms median, 0.272 ms p90, with a bare TCP connect at 0.154 ms.

**The production round-trip latency itself was not measured.** Production
database reads were not available to this task and no credentialled call was
made. What follows from the statement counts alone is the *shape*: the term is
linear in `2N + 2`, so at a managed-Postgres WAN latency of the order of 15 ms
the 20-project case is 42 × 15 ms ≈ **0.6 s of round trips against 23 ms of
CPU — about 27×** the term actually measured here. **That 27× rests on an
assumed 15 ms RTT, not a measured one.** What would settle it: a timed trivial
query from a deployed function against the production database (a `SELECT 1` in
a health route, reported), or Vercel's function-duration telemetry for
`apras-back` compared against the CPU figures above. Either is available to the
operator and to neither this task nor this machine.

### 1.5 The response dimensions nothing caps

**Dimension one: simultaneously open fronts on a single project.**
`_select_milestones` (`backend/app/services/project_report_service.py:935-952`)
caps `DONE` at three and returns everything else **uncapped and deliberately** —
the comment on line 950-951 says truncating "would hide one". `_groups_html`
(`project_report_service.py:1089-1106`) then renders the `IN_PROGRESS` list
through `_stage_items_html` with no cap of its own. (`NEXT_STEPS` is no longer
unbounded in the response: since APRAS-113 the cap moved to the card, which
fills three slots and prints a remainder line, so `_next_steps_html` bounds its
own output.)

Measured on **one** project, 3 bulletins, 3 photos, all milestones `IN_PROGRESS`:

| open fronts | response size | median wall clock | statements | B per extra front |
|---|---|---|---|---|
| 1 | 19,540 B | 2.14 ms | 4 | — |
| 2 | 19,655 B | 2.74 ms | 4 | 115.0 |
| 6 | 20,115 B | 2.15 ms | 4 | 115.0 |
| 50 | 25,255 B | 2.86 ms | 4 | 116.6 |
| 200 | 43,005 B | 4.46 ms | 4 | 117.9 |
| 400 | 66,805 B | 6.88 ms | 4 | 118.5 |

Linear at **115 B per extra open front, rising to 118.5 B** as the front index
gains digits, with this fixture's titles (`Frente {m} · Etapa de execucao numero
{m}`, 36 B plus two copies of the index — see the pinned fixture above); the
per-front cost moves with title length at the measured sensitivity of **+6 B per
character** (pinned fixture above, measured at the 1-project shape), so a
different title style moves the constant. Whether the *shape* stays linear at
other title styles was not measured; what was measured is that it is linear in
the number of fronts at this one. 400 open fronts on one project is 65 KiB and
6.9 ms — unbounded, but gently sloped. The statement count is **4 at every row**,
which is what makes this dimension pure string growth. (`t_dims.py`. Draft 2's
bytes ran ~450 B lower from the unrecorded fixture; its per-front slope,
115 → 119 B, is the same.)

**Dimension two, and the larger one: stage-detail leaves.**
`_stage_detail_html` (`project_report_service.py:1204-1268`) renders "every one
whose `detail_json` decodes, regardless of `MilestoneStatus`", with no cap on
the milestones *or* on each stage's `leaves` tuple. Measured on **one** project
with 20 milestones, varying the leaves per milestone:

| leaves per milestone | total leaves | response size | median wall clock | B per leaf |
|---|---|---|---|---|
| 0 (the reported production state today — see below) | 0 | 20,976 B | 2.11 ms | — |
| 4 | 80 | 31,309 B | 3.16 ms | 129.2 |
| 20 | 400 | 54,070 B | 6.46 ms | 82.7 |
| 100 | 2,000 | 168,471 B | 23.00 ms | 73.7 |

About **74–83 B per leaf** at the larger sizes (the 129 B at 80 leaves is the
per-milestone wrapper amortised over too few leaves). At 20 × 100, **one project
reaches the size of the entire 20-project report of §1.1** — 168,471 B against
171,507 B, i.e. **0.98×** the whole report on a single obra.

**Which way that ratio falls is fixture-dependent, and the honest claim is the
order of magnitude, not the inequality.** Draft 2 measured 181,369 B against
162,609 B (1.12×) and the independent re-measurement during code review measured
167,166 B against 145,825 B (1.15×); this fixture's longer bulletin bodies
inflate the 20-project report faster than they inflate the one-project one, and
it lands at 0.98×. All three agree that **one obra's stage detail alone is the
same size as a whole twenty-project report**, which is the finding; whether it is
2% under or 15% over depends on how long the fixture's titles and bulletin bodies
are. Stated as an inequality it would be a figure a reader cannot reproduce.

This dimension is reported as dormant today, and that is the only reason it is
not the headline — but **the production rows were not inspected, so say where
that claim comes from.** Two things are checkable here: no tracked code path
writes `detail_json` (`git grep detail_json -- backend` reaches the model field
at `project.py:112`, the 0007 migration, **three** code reads in
`project_report_service.py` — `:1006`, `:1060` and `:1248`, each a
`decode_stage_detail(milestone.detail_json)` — and four prose mentions of the
column in that file's docstrings and comments, `:721`, `:944`, `:1219` and
`:1227`; no writer anywhere), and the production docstring at
`project_report_service.py:1227-1229` records that "Every production row's `detail_json` is NULL until the operator
re-runs the sync by hand". The only writer is
`backend/scripts/sync_obras_from_drive.py`, which is untracked and
operator-run. **That the column is in fact NULL in production today is therefore
operator-reported, not measured — this task has no production database access
(§1.4) — and nothing in §3 depends on it.** It is recorded in §6 as a reopening
condition with a threshold precisely because it is a reported state that can
change without a code change.

### 1.6 The logo, measured — and no longer embedded

`_logo_html` (`project_report_service.py:1304-1339`) **no longer embeds the
logo**. Since APRAS-105 §E it emits either an `<img src>` naming the absolute
public logo route, or nothing at all; the `data:` URI rung is gone, and its own
docstring cites this document's earlier measurement as the reason. So the
figures below split into *what is true today* and *what the embed cost*, and the
second set is historical.

Measured today, on a 1-project / 6 / 3 / 3 render:

- `logo_url` absent → `_logo_html` returns **0 B**, response **20,109 B**;
- `logo_url` set → `_logo_html` returns **108 B**, response **20,217 B**. The
  logo is **0.53%** of the response.

**That 108 B is not a constant of the system**, and draft 2's 109 B was quoted as
though it were. The emitted tag is, verbatim from the harness:

```
<img src="http://localhost:8000/api/v1/public/tenants/sintetico/logo" alt="Condominio Sintetico de Medicao">
```

so its length is a fixed **47 B** of markup — `<img src="`, the fixed path
`/api/v1/public/tenants/`, `/logo" alt="`, `">` — plus the base URL (21 B here),
the slug (9 B) and the `alt` text, which is the tenant name (31 B):
47 + 21 + 9 + 31 = **108**. The base URL is the
last rung of `app.core.urls.public_api_base_url()` and in production is the
Vercel host instead, a few bytes longer. **The claim that survives any of those
substitutions is the one that matters: ~100 bytes, well under 1% of the
response.** Draft 2's 109 B is the same measurement with a 32-character tenant
name, which also explains its 13,062 B shell (§1.1).

The real logo file inspected by path,
`/Users/heitor/workspace/apras/backend/static/uploads/asvi-logo.png` (an
operator upload; `backend/static/uploads/` is gitignored, so the file is on the
machine and not in the tree):

- **108,018 B (105.5 KiB)** on disk;
- base64 payload **144,024 B**; with the 22-byte `data:image/png;base64,`
  prefix, the `data:` URI is **144,046 B (140.7 KiB)**. Measured by encoding the
  file, not computed from the 4/3 ratio.
- Worst-case response contribution at the **current 2 MiB `TenantService.
  LOGO_MAX_FILE_SIZE` ceiling** (`tenant_service.py:572`): **2,796,204 B** of
  base64, **2,796,226 B (2.67 MiB)** with the prefix.
- Worst-case contribution at a **512 KiB** ceiling: **699,052 B** of base64,
  **699,074 B (683 KiB)** with the prefix.
- Uploads inspected under `backend/static/uploads/`, **both counts, because the
  filter is the whole difference**: **9,859** regular files in total, of which
  **8,090** are embeddable images — suffix in `.png .jpg .jpeg .gif .webp .svg
  .bmp .ico`, lower-cased, recursive. Largest file in either set **108,018 B**;
  number over 512 KiB in either set: **zero**. Draft 2 quoted the 8,090 without
  saying it was filtered, which is why the code review counted 9,859 and could
  not reconcile it. The two load-bearing figures are the same in both counts.
  (The directory is gitignored and operator-managed, so the totals also move
  between runs; the largest-file and over-512-KiB figures are what the argument
  uses.)

Had the embed survived, that one real logo would have been **144,046 of
164,155 B — 87.7%** — of a single-project response, on every render of a route
with no cache. It did not survive, so today the logo is ~108 bytes and the 2 MiB
ceiling contributes nothing to this route at all.

**The 88% / 89% discrepancy, reconciled by name.** Four figures exist for this
one quantity and they differ only in the denominator's fixture: `_logo_html`'s
own docstring (`project_report_service.py:1321`) says **89%**, citing APRAS-93;
draft 2 of this document said **88%**; this fixture measures **87.7%** and the
independent re-measurement during code review measured **88.5%**. All four are
the same calculation — `data:` URI bytes over (response − tag + `data:` URI) —
over single-project responses of slightly different size, and none is wrong about
anything load-bearing. **The figure to quote is "about 88%", or "nearly nine
tenths".** The production docstring carries the earlier rounding of 89% and this
task may not touch that file (ER13); reconciling it is listed with Task A in §6.2
so that the citation and its source stop disagreeing.

### 1.7 The synchronous render, resolved

Both report handlers — `get_public_projects_report`
(`backend/app/api/v1/endpoints/public_projects.py:101-131`) and the internal
`get_projects_report` — are declared `def`, not `async def`. Starlette therefore
already runs them in its threadpool, so the render does **not** block the event
loop and `run_in_threadpool` (the upgrade path APRAS-94 and APRAS-96 record,
which concern `async def` handlers) is redundant on this route. The real bound
is threadpool occupancy, and the ceiling is measured rather than assumed:
`anyio.to_thread.current_default_thread_limiter().total_tokens` is **40** on
anyio 4.14.2 as installed. At the measured 23.2 ms per 20-project render, 40
threads absorb ~1,700 renders/second of CPU before queueing — a best-case figure
on an idle machine, since it divides by a wall clock, and §1.3.2 shows those move
by multiples under load; it is quoted to establish that **CPU is not the bound**,
which holds at any of the measured render times. A thread is
held for the *whole* wall clock, round trips included, so at the §1.4 figure of
~0.6 s per render the same 40 threads absorb only ~67 renders/second. That
second number inherits §1.4's unmeasured RTT. This input is closed, not
deferred.

## 2. How many instances the backend runs as in production

**Deployment model: a Vercel serverless function.** The repository file that
establishes it is **`backend/vercel.json`** (tracked), which routes `"/(.*)"` to
`index.py`; `backend/index.py` (tracked) is three lines re-exporting
`app.main:app`. The `Dockerfile` in `backend/` is the development container —
its `CMD` ends in `--reload --reload-dir app` — and not the production runtime.

**Whether the number of concurrently live instances can be determined from the
repository: no, it cannot.** Nothing committed pins a region, a `maxDuration`,
a memory size or a concurrency setting; `vercel.json` carries a single `routes`
entry mapping `"/(.*)"` to `index.py` and nothing else. **The evidence is a
grep, so it is named:** `git grep -E 'maxDuration|"regions"|"memory"|"functions"'`
over tracked `backend/` returns nothing, which bounds what the *repository*
pins and says nothing about what is configured in the Vercel dashboard — that
being exactly the point of the paragraph. `backend/.vercel/project.json` is untracked and
`backend/.env.local` is gitignored, so even the project id and plan tier are
operator-reported rather than cited, and nothing below depends on them. What
would settle the instance count: the Vercel observability panel for
`apras-back` (concurrent executions and invocation counts) or `vercel logs` —
either of which the operator can read and this task cannot.

The consequence is decisive for §3: **any in-process state is per-instance.** A
render cache populated in instance A is invisible to instance B, and an
invalidation executed by the instance that served a write does not reach the
instance holding a stale copy. That is precisely the failure the binding
constraint forbids.

## 3. The decision

**Chosen mechanism — exactly one: a per-IP rate limit on the public report
route**, `@limiter.limit("30/minute")`, the ceiling `public_branding` already
uses.

### 3.1 Why, on the measurements

No single render is expensive: 2.1 to 22.4 ms of CPU on an idle machine (§1.3.2
for how far that drifts; the conclusion needs only the order of magnitude) and
**20 to 168 KiB**, which is exact, across the five fixture shapes §1.1 measured
— shapes chosen to bracket what a condominium plausibly has, with the
20-project row already called implausible there and the 200-project row a
synthetic ceiling (§1.1). That
verdict is about **CPU, measured locally**;
§1.4's round-trip term makes the same 20-project render far slower in production,
and the two sections measure different things rather than disagreeing.

What *is* unbounded is **repetition**, and the measurement that settles the
choice of lever is §5's sweep: **20 requests for 20 distinct slugs cost the same
as 20 requests for one slug** — 160 statements either way, which is exact and
reproduced in every trial, and wall clocks that no trial could tell apart in two
sessions at absolute scales 6× apart (§5), measured through the real route. The
statement equality is the exact half of that; the wall-clock half is a
non-finding, which is what §5 reports it as. A per-tenant cache removes the first number
and leaves the second untouched. A limit bounds both, and is structurally
incapable of serving a stale byte because it holds no copy of anything. When it
degrades under several instances it degrades by **allowing more requests** —
each instance counts to 30 independently, so the effective ceiling is
`instances × 30/min` — never by publishing an outdated report. **Every cache on
§3.2's list that holds a copy degrades the other way**; the one item that does
not hold a copy, an `ETag` that revalidates on every request, is rejected there
for a different reason — it saves nothing server-side and nothing at all against
a sweeper. 30/minute is **judged** generous enough to be invisible to residents
sharing one NAT address — that is a judgement about expected usage, not a
measurement; nothing here measured how many report requests a shared address
makes per minute, and the per-NAT rate is what would settle it. It is the one
legitimate reason to dislike a per-IP limit here, so it is named rather than
assumed away.

There is a second, structural argument, from code rather than from timing, and
it is the strongest single point in favour. **The sibling route in the same
module is already limited.** `get_public_project_cover`
(`public_projects.py:139`) carries `@limiter.limit("300/minute")`, landed by
APRAS-104 after D3 was taken, and that module's own docstring argues the
principle: "a route strictly more amplifying than one that is limited cannot be
unlimited on the limited one's reasoning." **That same docstring is explicit that
it is not making this document's argument** — "That does **not** reverse D3 and it
does not claim the report route's policy, which is 'no limiter'"
(`public_projects.py:45-46`). The principle is borrowed; the application to the
report route is this document's own, and §6.1 is where it is defended as a
reversal of D3 rather than smuggled in as a consequence of APRAS-104. One report
view costs one report
request plus **one cover request per project** — twelve on the report APRAS-104
sized its limiter for (`public_projects.py:56-58`: "the largest report to plan
for carries **12 obras**, and since nothing on this surface sets
``Cache-Control`` a reload repeats all twelve"), and **uncapped in general**, because `_hero_html`
(`project_report_service.py:1353-1384`, the cover `<img>` built at lines
1379-1384 from `ProjectService.cover_display_url`) emits one `<img src>` per
project with no cap of its own, so a 20-project report fans out to twenty. Twelve is APRAS-104's
*planning* figure, not a measured bound, and it is named as such here rather than
quoted as a property of the system. Metering the fan-out while leaving the single
parent request unmetered is a limiter a sweeper walks straight past: pulling
report HTML alone — which is where the budget figures are — is unmetered today,
and the real fan-out being `N` rather than 12 only sharpens that.

### 3.2 Rejected, by name

- **`ETag` with revalidation on every request.** It is the only cache-shaped
  option that does *not* violate the constraint (`no-cache` forces
  revalidation, so a new bulletin appears on the next request). It loses on
  measured value: the saving only reaches a visitor who *already has* the
  document, and it does nothing about a sweeper, who never sends
  `If-None-Match` — which is what settles it, given §5's sweep measurement. The
  version-computation cost cuts both ways and should not be overstated: a
  `MAX(updated_at)` design adds a query to the hot path of every request, while
  hashing the already-rendered HTML adds no query and also no server-side saving,
  since the 22 ms has already been spent by then. Either way it helps only
  repeat visitors of the same slug.
- **Server-side cache of the rendered HTML, keyed per tenant, invalidated on
  writes to `ConstructionProject`, `ProjectMilestone` and `ProjectUpdate`.**
  Rejected on §2: in a serverless function the cache is per-instance and the
  invalidation lands in one instance only, so a bulletin published through
  instance A leaves instance B serving the old report for as long as B lives.
  That is the forbidden outcome. Making it correct means a shared store, i.e.
  new infrastructure, to save a measured 22 ms of CPU.
- **CDN cache with purge-on-write.** Rejected on the constraint, and the
  rejection holds on the weaker of two readings. **The platform claim, labelled
  as unverified:** Vercel's on-demand invalidation primitives are understood to
  be Next.js ISR features, leaving a Python serverless function with `s-maxage`
  and `stale-while-revalidate` and no per-path purge API. **That was not verified
  against a cited source or tried on the deployment**, and what would
  settle it is Vercel's own documentation for Python runtimes or one attempted
  purge against `apras-back`. **Why the rejection does not depend on settling
  it:** without a purge API the option is a TTL, which is the rejected
  `Cache-Control` wearing a different hat — a window in which a published
  bulletin is invisible — and *with* one it is still a cache that holds a copy in
  an invalidation path the operator's constraint makes safety-critical, i.e. the
  §3.2 server-side-cache objection one layer out. Either way it loses to a
  mechanism that holds no copy.
- **A lower logo embed ceiling (512 KiB, falling back to linking).** Rejected
  because **there is no embed left to lower.** §1.6 measured it: `_logo_html`
  emits a ~108-byte `<img src>`, the logo is 0.53% of the response, and the 2 MiB
  ceiling contributes zero bytes to this route. Lowering
  `TenantService.LOGO_MAX_FILE_SIZE` would change the *upload* rule and not one
  byte of a report, while degrading a future tenant with a large logo. A
  one-constant change with no measurable effect on this route and a regression
  surface elsewhere is not worth taking. Recorded so it is not re-derived.
- **`(logo_url, ETag)` with `If-None-Match`.** Same per-instance objection if
  the tag is held in process, and it is a strictly smaller version of the `ETag`
  option above. Moot for the same reason as the previous item: the logo is no
  longer in the response.
  **Read the scope of that rejection exactly, so this bullet is not mis-cited.**
  What is rejected here is an `ETag` over **this route's HTML**, keyed partly on
  the logo, back when the logo's bytes were inside that HTML. It says nothing
  whatever about caching `GET /api/v1/public/tenants/{slug}/logo`, the separate
  route that now serves those bytes — **that question is APRAS-124's and this
  document neither pre-empts nor declines it.** If anything §1.6 is the argument
  *for* it: de-embedding moved ~140 KiB per render onto a route the browser
  fetches once, which is precisely what makes caching that route worth doing, and
  `_logo_html`'s own docstring already says so ("The browser now fetches the image
  once and caches it on its own terms").
- **Doing nothing.** The closest runner-up, and defensible on the numbers: the
  CPU cost is small (§1.1), the exposure was chosen deliberately (D1, D2), and
  the measurements genuinely do **not** show an expensive route. It loses on
  §3.1's structural point — the amplifying child route is already metered while
  its unmetered parent is the cheaper thing to sweep — and on cost of adoption:
  one decorator, one import, one parameter, with a precedent in the same file.

## 4. Does the chosen mechanism need new infrastructure?

**No.** In the words the question asks for: **no**, the chosen mechanism does
not require a new dependency in `backend/pyproject.toml`, and **no**, it does
not require a new shared storage backend for `app/core/limiter.py`.

`slowapi>=0.1.10` is already a dependency (`backend/pyproject.toml:20`),
`app/core/limiter.py` already constructs `Limiter(key_func=get_remote_address)`,
`app/main.py` already wires `app.state.limiter`, and there are five
`@limiter.limit` call sites in production today — `auth.py:115`,
`invitations.py:130`, `invitations.py:156`, `public_branding.py:65`,
`public_branding.py:103` — plus `public_projects.py:139` on this very module's
cover route. Nothing is added to `pyproject.toml`; `requirements.txt` is
generated from it and also does not move.

The honest caveat, stated once: that `Limiter` has **no shared storage
backend**, so the limit is in-memory and per-instance, and the effective ceiling
is `instances × 30/min` rather than 30/min. Making it strict would require a
shared counter — Redis/Upstash, or a Postgres table — and that is **new
infrastructure and out of scope**. The approximation is accepted here because it
fails open (more requests allowed), can never go stale, and is the same
approximation six live call sites already run on in production.

## 5. What this closes, and what it does not

**No mechanism chosen here makes the report private, and neither would any
cache.** The slug is guessable by operator decision (D1) and the budget figures
are published at full parity with the internal report (D2). A caller who knows
or guesses one slug is entitled, by those decisions, to that condominium's
entire construction report.

The sweep, measured. Twenty tenants, each with a 3-project report, requested
through the real route:

| sequence | statements | wall clock | mean/request | bytes |
|---|---|---|---|---|
| the same slug, 20 times | 160 | 80.9 ms | 4.04 ms | 684,180 B |
| 20 **distinct** slugs, once each | 160 | 81.5 ms | 4.07 ms | 684,180 B |

160 = 20 × (2·3 + 2), both rows. The two are indistinguishable, which is the
measurement behind the two statements that follow. **Indistinguishable is a
comparative claim, so it is not asserted from one pair of numbers:** the two
sequences were run three times alternately in one process (`t_sweep.py`), giving
same-slug 80.9 / 81.4 / 127.5 ms against distinct-slug 81.5 / 86.9 / 101.9 ms —
the sign flips between trials and the spread within one arm (80.9 → 127.5) is far
wider than any gap between the arms, which is exactly what "no cache-shaped
signal" looks like. **Re-measured under load (§1.3.2) the absolute times were
6-7× higher — same-slug 510.0 / 569.3 / 489.7 ms against distinct-slug 429.8 /
504.2 / 491.9 ms — and the finding was unchanged**: the sign flipped again (the
distinct arm was *faster* in two trials of three), and the within-arm spread
again exceeded the between-arm gap. The wall clocks in the table above are
therefore an anchor for a quiet machine and nothing more; the *comparison* is what
reproduces, twice, at two very different absolute scales. The byte totals were
**equal to the byte** in every trial of both sessions, 684,180 B on all twelve
arms — **printed and observed, not asserted**: `t_sweep.py` asserts only that
every response was a 200 (`:49`), so unlike §1.3's arms this equality is an
observation a re-run could contradict without failing. It is expected to hold
because all twenty tenant names in this fixture are the same length; draft 2 saw a
+70 B difference from names of differing length, which is the same non-finding
with a noisier fixture.

- **A sweep across distinct tenant slugs is unaffected by any cache, because
  every key is cold.** A per-tenant cache would turn the first row into one
  render plus nineteen hits and would leave the second row exactly as it is:
  twenty cold keys, twenty full renders. Caching is therefore the wrong tool for
  the risk it is most often proposed against.
- What the limit closes: unbounded *repetition* from one address — including the
  sweep, because the limiter keys on the caller's address and not on the slug.
  Unthrottled, one process served 20 full reports in 81.5 ms — **~245
  reports/second, 684,180 B in 0.0815 s = ~8.4 MB/s (8.0 MiB/s)** of report
  bytes — from a single address with nothing in the way. **This is a
  best-observed rate on an idle machine, and it is the one figure here that
  drift cuts rather than inflates**: the same script under load served the same
  20 reports in 489.7-569.3 ms, i.e. ~35-41 reports/second and ~1.2-1.4 MB/s
  (§1.3.2). The argument needs only that an unmetered caller gets *tens to
  hundreds* of full reports per second from one address, which both measurements
  give; the 245/s figure should not be quoted as a capacity number. (Draft 2 wrote
  "~5.5 MiB/s" for a figure that was 5.54 **MB**/s, i.e. 5.28 MiB/s: a unit slip,
  corrected here and the base-2 and base-10 figures now both given.)
  That the route is unmetered today is proved structurally, not by prose:
  `tests/test_public_project_report.py::test_the_thirty_first_request_inside_a_minute_is_still_a_200`
  asserts over the handler's parsed decorator list, because `conftest.py`
  disables the limiter suite-wide and a bare request loop would prove nothing.
- What it does **not** close: **exposure.** Every slug remains readable by
  anyone who guesses it, at the rate the limit allows. The only mechanism that
  would close exposure is D1's rejected alternative, an unguessable per-link
  token. Reopening that is a product decision, not a performance one, and is
  not proposed here.

## 6. The prior decision this reverses, and the follow-up tasks

### 6.1 D3, stated fairly, and the reversal

The prior operator decision that declined a per-IP rate limit on this route is
**`D3` — "No rate limit, no cache"**, recorded at
**`docs/tasks/APRAS-92-spec.md:73-84`**. It decided that the route stays
unguarded, tenant-resolved from the slug and rendered fresh on every request. A
per-IP limiter — APRAS-74's `@limiter.limit("30/minute")`, the same decorator and
the same ceiling recommended here — was considered there and **declined**.

**The reason D3 gave for declining**, in its own terms: `backend/pyproject.toml`
and `backend/requirements.txt` contain no cache dependency and
`backend/app/core/limiter.py` builds `Limiter(key_func=get_remote_address)`
**with no `storage_uri`** — it has no shared storage backend — so a limit "would
be per-process on Vercel's serverless runtime and would behave inconsistently
between instances." The same decision is carried in production code: the module
docstring of `backend/app/api/v1/endpoints/public_projects.py` (lines 32-41)
records that the route carries **no** `@limiter.limit` and sets no
`Cache-Control` or `ETag`, "deliberately and not by omission," and names
APRAS-93 as the owner of any revisit.

**This document's recommendation reverses D3.** D3 was not wrong about the
mechanism: §2 and §4 confirm the limit really is per-instance, and nothing here
claims otherwise. What changed is the measurement.

**The measurement that justifies the reversal is §5's sweep**: 20 distinct slugs
cost the same as 20 repeats of one slug — 160 statements exactly, both rows, and
~81 ms on a quiet machine with no difference any trial could resolve — from
which it follows that *a cache cannot bound a distinct-slug sweep, because every
key in one is cold*. Repetition is the only unbounded property §1 found, the
sweep is its cheapest form, and that leaves the per-IP limit as the available
lever. D3 declined the limiter and the cache together, on one shared objection;
§5 shows the two are not symmetrical. A cache that disagrees between instances
serves an outdated bulletin — the forbidden outcome — while a limiter that
disagrees between instances merely allows more requests than its number
suggests. That asymmetry is what the operator is asked to accept, and it is the
only respect in which this document departs from D3.

**Where the measurements do *not* support the reversal, said plainly.** D3 also
rested implicitly on there being nothing expensive to protect, and on that point
§1 **agrees with D3, not with this recommendation**: every plausible render is
2–22 ms of CPU and under 170 KiB, and the single most expensive thing in the
response when D3 was taken — the embedded logo, about 88% of a small report — has
since been removed by APRAS-105 and is now ~108 bytes. On cost alone, "do
nothing" survives §1 intact. The reversal therefore rests on §5 (a cache cannot
bound a sweep, so the lever has to be a limit) and on §3.1's structural point
(the amplifying cover route is already metered at 300/minute while its cheaper,
unmetered parent is the better thing to sweep) — not on the route being
expensive. **That last step is a judgement about acceptable exposure, not a
measurement, and it is the one thing here that needs the operator's signature.**
An operator who weighs it the other way can reaffirm D3 without contradicting a
single figure in this document.

### 6.2 Should this become implementation tasks? **Yes, two.**

Neither may be created before the operator has signed off the §6.1 reversal.

**The §1.3 correction does not move this answer, and that was checked rather than
assumed.** The eager-versus-cold sign feeds exactly one place in the argument:
Task B's *supporting* justification. It does not touch §3's choice of mechanism,
because that choice turns on §5's sweep (a cache cannot bound a distinct-slug
sweep) and on §3.1's structural point (a metered child beside an unmetered
parent) — neither of which mentions query shape, and both of which reproduced
unchanged. It does not touch §6.1's reversal, which rests on the same two legs. It
does not change Task B's headline claim either: "constant statement count" was and
remains the right primary justification, because the round-trip term is what
production pays. **What it does change is that Task B is worth more than draft 2
said** — it carries a measured 9–47% CPU win as well, 9–16% at 200 projects and
41–47% at 20 — and the document says so
rather than staying conservative out of inertia. The count of tasks, their
boundaries and their must-not-touch lists are unaffected.

**Task A — the rate limit.** Add `@limiter.limit("30/minute")` to
`get_public_projects_report`.

- Touches: `backend/app/api/v1/endpoints/public_projects.py` (the decorator,
  the `request: Request` parameter slowapi matches by name with the same
  `# noqa: ARG001` comment the six existing call sites carry, and the module
  docstring paragraph at lines 32-41 that currently records the absence of a
  limit "deliberately and not by omission" — it must be rewritten to record this
  decision instead); `backend/tests/test_public_project_report.py` (the existing
  `test_the_thirty_first_request_inside_a_minute_is_still_a_200` inverts, and the
  test must re-enable the limiter around itself and restore it, because
  `conftest.py` disables it suite-wide).
- **One documentation discrepancy, assigned rather than left loose.**
  `_logo_html`'s docstring (`project_report_service.py:1321`) says the embed was
  "about **89%**" of a single-project report and cites APRAS-93 as its source,
  while APRAS-93 says about 88% (§1.6 reconciles all four figures). Neither this
  task nor Task A may touch `project_report_service.py`, so the fix belongs to
  **Task B**, which edits that file anyway: one word, in a docstring, so a
  citation stops disagreeing with the document it cites. Nothing depends on the
  rounding.
- Must **not** touch: `backend/app/services/project_report_service.py`,
  `backend/app/core/limiter.py`, `backend/pyproject.toml`,
  `backend/requirements.txt`. No cache, no `ETag`, no `Cache-Control`, no
  dependency, no shared limiter store.

**Task B — `selectinload` on the report's queries.** Separate, because it
touches the service and the tenant-isolation boundary while Task A touches one
endpoint, and because the two bound different things (cost per render versus
unbounded repetition). It does not replace Task A.

- Touches: `backend/app/services/project_report_service.py` — add
  `selectinload(ConstructionProject.milestones)` and
  `selectinload(ConstructionProject.updates)` to the `select()` in
  `_acting_projects` (lines 1513-1528), and amend that function's docstring,
  which currently explains that milestones and bulletins are reached "only
  through these rows' relationships"; `backend/tests/test_project_report.py` —
  a test that the statement count is constant in the project count (the
  `before_cursor_execute` listener this document used is the right instrument)
  and, **critically**, a test that tenant isolation still holds, since the two
  relationships carry no `tenant_id` and are reached only through already
  narrowed parent rows.
- Must **not** touch: `backend/app/api/v1/endpoints/public_projects.py`,
  `backend/app/core/limiter.py`, `backend/pyproject.toml`. No change to the
  rendered bytes — §1.3 measured all three states at 171,507 B (and at
  1,738,448 B at the 200-project size) and that equality is the acceptance
  criterion.
- **Scope it on the corrected evidence, which is stronger than draft 2 claimed.**
  The headline justification does not change and should not: **`selectinload`
  turns `2N + 2` statements into a constant 4**, which collapses the §1.4
  round-trip term — linear in the number of projects today, flat afterwards — and
  that is the real prize, because the round-trip term is the one that production
  pays and this machine does not. It is the right primary claim whatever the CPU
  figures say.
  **What changes is the supporting fact, and it changes in Task B's favour.**
  Draft 2 said "not a CPU win at 200 projects: 437.7 ms eager against 402.9 ms
  cold, i.e. slightly worse", and narrowed the pitch to statement count because of
  it. That figure was an artefact of a blocked timing design (§1.3.1). Measured
  paired and interleaved, **eager is faster at every size measured: −41 to −47%
  at 20 projects (13.2 ms against 22.4 ms, 36/36 paired reps over three runs) and
  −9 to −16% at 200 projects (91/96 paired reps over eight runs in four sessions,
  median paired difference +41.5 to +86.3 ms)**. So the CPU win
  is real at both ends and Task B carries a measured CPU improvement *as well as*
  the constant statement count. The narrowing was conservatism inherited from a
  bad measurement, not a finding, and it is withdrawn.
  **What has not changed, and must not be overstated in Task B's place:** none of
  this makes the route expensive (§1.1), so Task B remains an optimisation of a
  cheap route and an insurance policy against the round-trip term — not a fix for
  a cost problem. Its acceptance criteria stay the statement count, the byte
  equality and the tenant-isolation test.

Not in either task, and recorded here so they are not smuggled in: the logo
ceiling (§3.2, rejected and now moot), a shared limiter backend (§4, new
infrastructure), `run_in_threadpool` (§1.7, redundant on a `def` handler), and
any cap on the two uncapped dimensions of §1.5.

**One question this document does not answer and must not leave ownerless: the
cover route's `Cache-Control`.** `public_projects.py:76-78` assigns it to
APRAS-93 — "The real answer is `Cache-Control` plus server-side resizing, both
out of scope here and both belonging with **APRAS-93**, where a cache changes the
arithmetic." APRAS-93 scoped itself to the **report** route and took no decision
about the **cover** route's response headers, so when this task closes that
pointer dangles. It is not folded into Task A or Task B: Task A touches only the
report handler's decorator, and caching an image route is a different question
from rate-limiting an HTML one (an image's bytes are immutable for a given
`cover_display_url`, so it does not meet the binding constraint the way an HTML
report does — which is why it is plausibly *easier*, not harder). **Recommended
home: APRAS-124**, which already owns caching the public logo route, the exact
sibling case, and would then own both public image routes' caching as one
coherent piece of work. Whoever reassigns it should also amend the
`public_projects.py:76-78` comment so the code stops pointing at a closed task.

### 6.3 Conditions that would reopen this decision

- A measured production RTT (§1.4) that leaves `2N + 2` round trips dominant
  even after Task B lands — the answer would be to fix the query pattern
  further, not to add a cache.
- A tenant appearing with more than ~50 concurrent construction projects.
- A tenant appearing with a project carrying more than ~200 simultaneously open
  (`IN_PROGRESS`) milestones — §1.5's first uncapped dimension, measured at
  43,005 B and 4.46 ms at exactly 200.
- **`detail_json` ceasing to be `NULL` in production.** §1.5's second uncapped
  dimension is the one with real teeth: 20 milestones × 100 leaves on a *single*
  project measured 168,471 B and 23.0 ms, the size of the whole 20-project
  report. The threshold to watch is a single project exceeding ~500 decoded
  leaves in total (~36 KiB of stage detail at the measured 73.7 B/leaf); past that,
  a cap in `_stage_detail_html` becomes a better lever than anything in §3.
- A decision to stop publishing budget figures, which would change the exposure
  question rather than the cost one.

## Out of Scope

Any production code change; the `run_in_threadpool` migration; a shared
rate-limit store; implementing the `selectinload` on the report's queries (§6.2
recommends it as a separate task; this task writes no code for it); revisiting
D1's guessable slug or D2's budget parity; `docs/suggestions-log.md`; any
mockup — there is no UI.

## Expected Results

- [x] `docs/tasks/APRAS-93-spec.md` exists and reports, for at least four
      different render sizes, a measured median wall-clock time and a measured
      response size in bytes, each row naming the project, milestone-per-project,
      bulletin-per-project and photo-per-bulletin counts used. — §1.1, five rows.
- [x] The document states the measured number of SQL statements one render
      issues and expresses it as a formula in the number of projects. — §1.2,
      `2N + 2`, measured at seven values of `N` through the real route.
- [x] For one fixed render whose output byte size it states, the document
      reports a median wall-clock time and a SQL statement count for each of
      three states: cold (identity map expired), warm (every row hydrated and
      strongly referenced), and eager (relationships loaded with
      `selectinload`); and it states which of string assembly or ORM data access
      the numbers make dominant, as a percentage. — §1.3, 171,507 B in all three
      states; ORM data access dominant at **85%** (string assembly 14.8%) at 20
      projects and at **90.5%** (string assembly 9.5%) at 200 projects, both
      measured within one process, and both reproduced across three sessions
      (string assembly 13.2-15.9% at 20 over twenty trials, 8.1-10.4% at 200
      over twenty-three). §1.3.2 records how far the wall clocks drift and which
      figures survive it.
- [x] The document identifies at least one response dimension that is not
      capped in code, names the file and line range of the function that leaves
      it uncapped, and reports measured response sizes in bytes for at least two
      different values of that dimension. — §1.5, two dimensions:
      `_select_milestones` at `project_report_service.py:935-952` (six measured
      values) and `_stage_detail_html` at `project_report_service.py:1204-1268`
      (four measured values).
- [x] The document states, as a number, how large the database round-trip term
      is relative to the CPU term it measured, and states explicitly that the
      round-trip latency itself was not measured. — §1.4: 0.40× on a measured
      loopback round trip of 0.219 ms, ~27× at an assumed 15 ms WAN RTT, with
      the production latency stated as not measured and what would settle it
      named.
- [x] The document states the byte size of a real logo file it inspected by path
      and the byte size of the `data:` URI that file inflates to in the
      response, plus the worst-case response contribution at the current 2 MiB
      logo ceiling and at a 512 KiB ceiling. — §1.6: 108,018 B on disk,
      144,046 B as a `data:` URI, 2,796,226 B at 2 MiB, 699,074 B at 512 KiB —
      and the finding that the embed no longer exists, the logo now costing
      ~108 B.
- [x] The document names the production deployment model of the backend, cites
      the repository file that establishes it, and states explicitly whether the
      number of concurrently live instances can be determined from the
      repository; if it cannot, it names what would settle it. — §2: Vercel
      serverless function, `backend/vercel.json`, cannot be determined, settled
      by the Vercel observability panel or `vercel logs`.
- [x] The document names exactly one chosen mechanism and rejects by name, each
      with a stated reason, at least: an `ETag` with revalidation on every
      request; a server-side render cache keyed per tenant and invalidated on
      writes to `ConstructionProject`, `ProjectMilestone` and `ProjectUpdate`; a
      CDN cache with purge-on-write; a lower logo embed ceiling; and doing
      nothing. — §3 chooses the per-IP limit; §3.2 rejects all five by name.
- [x] The document names the prior operator decision that declined a per-IP rate
      limit on this route: it states that decision's identifier (`D3`) and the
      document and line range where it is recorded, states the reason that
      decision gave for declining (that the limiter has no shared storage backend
      and is therefore per-process on a serverless runtime, behaving
      inconsistently between instances), states explicitly that this document's
      recommendation **reverses** that decision, and names the measurement that
      justifies the reversal. — §6.1: `D3` at
      `docs/tasks/APRAS-92-spec.md:73-84`, reversed, justified by §5's sweep,
      with the limits of that justification stated.
- [x] The document answers yes or no, in those words, to whether the chosen
      mechanism requires a new dependency in `backend/pyproject.toml` or a new
      shared storage backend for `app/core/limiter.py`. — §4: **no** to both.
- [x] The document states that no mechanism it chooses makes the report private,
      and states that a sweep across distinct tenant slugs is unaffected by any
      cache because every key is cold. — §5, both stated and the sweep measured.
- [x] The document states whether follow-up implementation tasks should be
      created, and for **each** task it recommends lists the file paths that task
      would touch and what it must not touch; if it recommends none, it states
      the condition that would reopen the decision. — §6.2, two tasks, each with
      touches / must-not-touch; §6.3 lists the reopening conditions anyway.
- [x] This task adds no production code. Each of
      `backend/app/api/v1/endpoints/public_projects.py`,
      `backend/app/services/project_report_service.py`,
      `backend/app/core/limiter.py` and `backend/pyproject.toml` is byte-identical
      to its committed content: `git status --porcelain
      backend/app/api/v1/endpoints/public_projects.py
      backend/app/services/project_report_service.py
      backend/app/core/limiter.py backend/pyproject.toml` prints nothing.
