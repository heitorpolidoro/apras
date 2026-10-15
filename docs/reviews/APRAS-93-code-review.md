# APRAS-93 — Code Review

**Task:** Decide how to make the public obras report cheap to serve without going private
**Reviewed:** staged worktree `/Users/heitor/workspace/apras/.claude/worktrees/agent-a7a31a09fc3ca4bf4`, branch at `a33f26a`
**Diff reviewed:** one staged path, `docs/tasks/APRAS-93-spec.md`, 652 insertions / 0 deletions
**Date:** 2026-10-05

This task ships no production code, so this review is a review of an argument and of
the measurements under it. I re-measured independently. The developer's harness was
**not** in the session scratchpad (only `ci.yml.orig` and three CI job logs are there,
and the other two session scratchpads are empty), so I wrote my own from scratch:
`/private/tmp/claude-501/-Users-heitor-workspace-apras/06230b8a-d0ef-40dd-929b-83bb4eb6abbf/scratchpad/rev93/`
(`rh.py` plus `t1`–`t9`). In-memory SQLite, `SQLModel.metadata.create_all()`,
synthetic fixtures only. Nothing read the production database and nothing called the
production API. Same machine class as the document (M1, Darwin 25.6.0, Python 3.13.13
in `backend/.venv`).

An independent harness is a stronger instrument than a re-run of theirs, but it has one
consequence worth stating before the numbers: my fixture's **text content** differs from
theirs (title, description and bulletin-body lengths), so absolute byte figures differ
by a constant factor while *slopes*, *statement counts* and *ratios* are directly
comparable. Where that matters I say so.

---

## 1. Verdict summary

The document is of unusually high quality. It measures what it claims to measure, it
separates measurement from judgement where almost nothing does, and it volunteers the
weakest link in its own argument instead of hiding it. Twelve of the thirteen expected
results are satisfied as written, and the hard boundary of ER13 is clean.

One blocking finding: **the `selectinload`-at-200-projects figure is wrong, and it is
wrong in the one place the document presents as a correction of a previous error.** My
measurement says the previous draft was right and the correction is the regression.
Details in §4.

---

## 2. What reproduced

### 2.1 `2N + 2`, through the real HTTP route — reproduced exactly

Measured with a `before_cursor_execute` listener on the engine, through FastAPI's
`TestClient` against `GET /api/v1/public/tenants/{slug}/projects/report`, cold
(`expire_all()` + `gc.collect()`) before the counted request. Not by reading code.

| projects `N` | document | **my count** | `2N + 2` |
|---|---|---|---|
| 0 | 2 | **2** | 2 |
| 1 | 4 | **4** | 4 |
| 2 | 6 | **6** | 6 |
| 5 | 12 | **12** | 12 |
| 20 | 42 | **42** | 42 |
| 60 | 122 | **122** | 122 |
| 200 | 402 | **402** | 402 |

Seven for seven. The `N = 2` statement sequence my listener saw, in order:

1. `SELECT tenant.id, tenant.name, tenant.slug, tenant.is_active, …`
2. `SELECT construction_project.id, construction_project.tenant_id, …`
3. `SELECT project_update.…`
4. `SELECT project_milestone.…`
5. `SELECT project_update.…`
6. `SELECT project_milestone.…`

Identical to the document's list, including the update-before-milestone ordering within
each project.

**The non-obvious finding is confirmed.** There is exactly **one** `SELECT tenant` in
the trace, not two. `_acting_tenant` (`project_report_service.py:1500-1510`, verified —
`session.get(Tenant, acting_tenant_id(session) or DEFAULT_TENANT_ID)`) adds no
statement, because the handler's `TenantService.get_by_slug`
(`public_projects.py:116`) has already put that row in the identity map. The decisive
evidence is the `N = 0` row: **2** statements, not 3. Had `_acting_tenant` issued its
own query, `N = 0` would be 3 and the formula would be `2N + 3` for the route and
`2N + 2` for the renderer. It is `2N + 2` for both. Verified by observation, as asked.

### 2.2 The render-size table — statement counts and wall clocks reproduced

| N / mi / bu / ph | doc ms | **my ms** | doc stmts | **my stmts** |
|---|---|---|---|---|
| 0 | 0.97 | **0.91** | — | **2** |
| 1 / 6 / 3 / 3 | 2.0 | **1.95** | 4 | **4** |
| 5 / 12 / 8 / 4 | 5.9 | **6.00** | 12 | **12** |
| 20 / 20 / 20 / 6 | 23.0 | **23.92** | 42 | **42** |
| 60 / 40 / 60 / 8 | 103.0 | **102.78** | 122 | **122** |
| 200 / 40 / 60 / 8 | 406.7 | **390.76** | 402 | **402** |

Wall clocks agree within noise at every size. The fixed render cost reproduced almost
exactly: **13,039 B** against the document's 13,062 B — a 23-byte gap fully explained by
tenant-name length, and a good sign, because the shell is the one figure that does not
depend on my fixture's project text.

Byte figures for the project rows are lower than the document's (18,804 / 44,460 /
145,825 / 453,605 / 1,481,826 against 19,659 / 48,653 / 162,609 / 503,909 / 1,649,451),
entirely from shorter synthetic strings. Per-project increment: mine 5,769 B, theirs
6,597 B. Same shape, different constant. See Suggestions.

Also confirmed in code: `_updates_html` (`project_report_service.py:1271-1296`) does
render only `updates[:3]` and `decode_photos(...)[:3]` (lines 1281-1282), and photos are
referenced by URL (`<img … src="{_e(url)}">`, line 1285), never embedded — so the
document is right that bulletin and photo counts do not scale the response.

### 2.3 The 84 / 16 split — reproduced as 85.2 / 14.8

Paired design, cold and warm alternating inside one loop, 12 counted reps each, 20
projects / 20 / 20 / 6:

| state | doc stmts | **my stmts** | doc median | **my median** |
|---|---|---|---|---|
| cold | 42 | **42** | 23.1 ms | **22.52 ms** |
| warm | 2 | **2** | 3.7 ms | **3.33 ms** |
| eager | 4 | **4** | 14.1 ms | **13.3 ms** |

- **All three states byte-identical: confirmed.** My harness asserted it directly —
  cold, warm and eager all produced **145,825 B** exactly. This is the acceptance
  criterion §6.2 pins Task B to, and it holds.
- Split: **string assembly 14.8%, ORM data access 85.2%** (document: 16% / 84%).
- At 200 projects: cold 407.20 ms / warm 39.20 ms → string assembly **9.6%**
  (document: 11%). Warm statement count 2 at both sizes.

The document's 84% is accurate to within ~1.2 points, and my figure moves it in the
*conservative* direction — ORM data access dominates slightly harder than claimed. The
conclusion this percentage exists to support ("the fix belongs in query shape, not in
caching") is therefore not merely intact but marginally strengthened. The load-bearing
claim survives re-measurement.

The weak-reference argument also reproduced: every cold rep re-issued all 42 statements
after `expire_all()` + `gc.collect()`, and the warm state only reached 2 statements
once I pinned every project, milestone list and update list behind a strong reference by
hand. The document's characterisation of the warm figure as "a floor on string assembly,
not an achievable state" is correct.

### 2.4 The sweep — reproduced exactly in every load-bearing property

Twenty tenants, each a 3-project report, through the real route, after warming the app:

| sequence | doc stmts | **my stmts** | doc ms | **my ms** | doc bytes | **my bytes** |
|---|---|---|---|---|---|---|
| same slug ×20 | 160 | **160** | 123.1 | **87.1 / 86.0** | 661,680 | **606,600** |
| 20 distinct slugs | 160 | **160** | 119.5 | **86.0 / 88.2** | 661,750 | **606,640** |

This is the measurement the whole mechanism choice rests on, and it reproduces in all
three respects that matter:

1. **160 statements on both rows**, exactly. `20 × (2·3 + 2) = 160` — arithmetic
   correct.
2. **The two rows are indistinguishable in wall clock.** In my trial 1 the distinct-slug
   sweep was marginally *faster* (86.0 vs 87.1 ms); in trial 2 marginally slower (88.2
   vs 86.0). The document reports the same relationship with the same sign in its
   primary run (119.5 vs 123.1). There is no cache-shaped signal here, which is the point.
3. **The byte delta has the same sign and the same cause**: distinct slugs are a few tens
   of bytes larger (mine +40 B, theirs +70 B), from varying tenant-name lengths.

My absolute wall clock is lower and my bytes smaller, for the fixture reason above. The
*comparison* — which is the entirety of §5's argument — is confirmed. **No cache can
bound a distinct-slug sweep, because every key is cold.** That claim is measured, not
asserted.

### 2.5 The logo arithmetic — reproduced to the byte

Measured by actually encoding the file, as the document says it did:

| quantity | document | **my measurement** |
|---|---|---|
| `asvi-logo.png` on disk | 108,018 B (105.5 KiB) | **108,018 B (105.5 KiB)** |
| base64 payload | 144,024 B | **144,024 B** |
| `data:` URI with the 22-byte prefix | 144,046 B (140.7 KiB) | **144,046 B (140.7 KiB)** |
| worst case at the 2 MiB ceiling | 2,796,226 B (2.67 MiB) | **2,796,226 B (2.67 MiB)** |
| worst case at a 512 KiB ceiling | 699,074 B (683 KiB) | **699,074 B** |
| largest upload under `static/uploads/` | 108,018 B | **108,018 B** |
| uploads over 512 KiB | zero | **zero** |

Exact on every figure. `TenantService.LOGO_MAX_FILE_SIZE` verified at
`tenant_service.py:572` = `2 * 1024 * 1024` = 2,097,152. Not computed from the 4/3 ratio
— I encoded the bytes, and 144,024 is what `base64.b64encode` returns.

**Correction 1 confirmed: the logo is no longer embedded.** `_logo_html`
(`project_report_service.py:1304-1339`) returns, at line 1339,
`f'<img src="{_e(public_tenant_logo_url(slug))}" alt="{tenant_name}">'`. I asserted
`'data:' not in` the emitted HTML — **False**, no `data:` URI. With `logo_url` absent it
returns `0 B` (line 1336). The old figure is marked historical rather than deleted:
§1.6's closing paragraph keeps it as "Had the embed survived … **88%**", and the
intro's correction list names it. That is the right treatment.

My re-derivation of the historical figure: 144,046 of 162,850 B = **88.5%**, against the
document's 88%. Confirmed. (The production docstring still says 89% — see Suggestions.)

### 2.6 Both uncapped dimensions — reproduced, including the escalation

**Dimension one, open fronts on one project.** The slope is the claim, and the slope is
exact:

| open fronts | doc bytes | **my bytes** | **my B/front** | stmts |
|---|---|---|---|---|
| 1 | 19,090 | 18,235 | — | **4** |
| 2 | 19,205 | 18,350 | **115** | **4** |
| 6 | 19,665 | 18,810 | **115** | **4** |
| 50 | 24,807 | 23,950 | **117** | **4** |
| 200 | 42,559 | 41,700 | **118** | **4** |
| 400 | 66,359 | 65,500 | **119** | **4** |

My bytes sit a constant ~855-859 B below the document's at every row, and the
per-front increment is **identical** (115 → 119 B, converging on the document's "about
119 B per extra open front"). Statement count constant at 4 throughout, confirming this
dimension is pure string growth. `_select_milestones`
(`project_report_service.py:935-952`) verified: `DONE` capped at `[:3]` (line 949),
everything else returned uncapped (line 952), with the comment at **lines 950-951**
reading "truncating it would hide one" — cited correctly. `_groups_html`
(`project_report_service.py:1089-1106`) verified, renders `_stage_items_html` with no cap
of its own (line 1102).

**Dimension two, stage-detail leaves — the escalation.** My first attempt showed no
growth at all, because `decode_stage_detail` (line 776) is genuinely strict and my
payload was rejected; `StageDetail` requires `pct`, `start` and a `leaves` tuple of
`StageLeaf` objects each needing `name` and `pct`. With a payload that actually decodes
(verified: `decode_stage_detail(probe) is not None`):

| leaves/milestone | total leaves | doc bytes | **my bytes** | doc ms | **my ms** | **my B/leaf** |
|---|---|---|---|---|---|---|
| 0 | 0 | 20,532 | **19,671** | 2.8 | **2.11** | — |
| 4 | 80 | 31,687 | **30,004** | 3.6 | **3.22** | 129.2 |
| 20 | 400 | 56,548 | **52,765** | 7.3 | **6.42** | 82.7 |
| 100 | 2,000 | 181,369 | **167,166** | 26.8 | **22.86** | **73.7** |

The ~80 B/leaf figure is fair (mine lands between 73.7 and 82.7 at the larger sizes).

**The headline claim is confirmed.** One project at 20 milestones × 100 leaves produced
**167,166 B** against **145,825 B** for my entire 20-project report — the single project
outweighs the whole report by 1.15×. The document measures 181,369 vs 162,609, a ratio
of 1.12×. Same finding, same magnitude, independently reproduced. `_stage_detail_html`
verified at `project_report_service.py:1204-1268`, and its docstring does say "every one
whose `detail_json` decodes, regardless of `MilestoneStatus`" (lines 1219-1220) with no
cap on milestones or on `leaves`. The dormancy claim is also in the code: lines
1227-1229, "Every production row's `detail_json` is NULL until the operator re-runs the
sync by hand."

My judgement on whether this should be promoted to a task is in §6.

### 2.7 §1.7, the synchronous render — confirmed

- `get_public_projects_report` is `def`, not `async def` (`public_projects.py:102`), and
  so is the internal `get_projects_report` (`projects.py:130`). Starlette therefore runs
  both in the threadpool and `run_in_threadpool` is indeed redundant here.
- `anyio.to_thread.current_default_thread_limiter().total_tokens` = **40**, on
  **anyio 4.14.2** as installed. Exactly as documented. (It raises `NoEventLoopError`
  outside a loop; I read it inside one.)
- Arithmetic checks: 40 / 23 ms = 1,739/s ≈ "~1,700"; 40 / 0.6 s = 66.7 ≈ "~67". The
  document correctly flags that the second number inherits §1.4's unmeasured RTT.

### 2.8 §2, the deployment model — confirmed

`backend/vercel.json` is **tracked** (`git ls-files` confirms) and contains exactly one
`routes` entry mapping `"/(.*)"` → `index.py`, and nothing else — no region, no
`maxDuration`, no memory size, no concurrency setting. `backend/index.py` is tracked and
is a three-line re-export of `app.main:app`. `backend/Dockerfile`'s `CMD` does end in
`--reload --reload-dir app`, supporting the claim that it is the development container.
The conclusion that the concurrent instance count cannot be determined from the
repository is correct as stated.

### 2.9 The D3 legs, verified individually

| claim | verification |
|---|---|
| `D3` recorded at `docs/tasks/APRAS-92-spec.md:73-84` | **Exact.** Lines 73-84 are precisely the "**D3 — No rate limit, no cache.**" paragraph, first line to last. |
| D3's stated reason | **Verbatim.** Lines 83-84: "so both a cache and a limit would be per-process on Vercel's serverless runtime and would behave inconsistently between instances." The document's paraphrase is faithful, including the `no storage_uri` detail (line 82-83). |
| `get_public_project_cover` carries `@limiter.limit("300/minute")` at `public_projects.py:139` | **Exact line.** Decorator at 139, handler at 140-141 with the `request: Request  # noqa: ARG001` parameter. |
| It landed **after** D3 | **Confirmed.** APRAS-92 (D3) shipped `642e23d`, 2026-09-27. APRAS-104 (the cover limiter) shipped `9d4cf24`, 2026-09-29. Two days later. |
| The module docstring the document quotes | **Verbatim.** `public_projects.py:54-56`: "a route strictly more amplifying than one that is limited cannot be unlimited on the limited one's reasoning." |
| The docstring records the absence "deliberately and not by omission" at lines 32-41 | **Exact range.** The D3 paragraph runs 32-41, ending "**APRAS-93** owns any revisit; do not add one here without it." |
| Twelve covers per view | **Partly — see Suggestions.** The *source* is real: `public_projects.py:60-61` says "the largest report to plan for carries **12 obras**" and "a reload repeats all twelve", and the 20 × 12 = 240 → 300 arithmetic is there at lines 60-62. But twelve is APRAS-104's **planning figure**, not a cap in code: `_project_hero` emits one cover `<img src>` per project (lines 1379-1392, via `ProjectService.cover_display_url`), so the real fan-out is one per project and uncapped. |
| Budget figures live in the unmetered HTML | **Confirmed.** D2 (`APRAS-92-spec.md:70-71`) establishes full budget parity, and the report HTML comes from the unmetered route. `public_projects.py:79-80` says so outright: "the report HTML itself still renders, because it comes from the unmetered route above." |

### 2.10 §4's infrastructure answer — confirmed

- `slowapi>=0.1.10` at **`pyproject.toml:20`**, exact line. `requirements.txt:97` pins
  `slowapi==0.1.10`. Nothing needs adding.
- `app/core/limiter.py` is six lines and builds `Limiter(key_func=get_remote_address)`
  with **no `storage_uri`** — the honest caveat is honest.
- Five existing production `@limiter.limit` call sites, all cited correctly:
  `auth.py:115`, `invitations.py:130`, `invitations.py:156`, `public_branding.py:65`,
  `public_branding.py:103` — **plus** `public_projects.py:139`, giving the six the
  document claims. Every line number exact.
- `public_branding.py:65` and `:103` are both `30/minute`, so "the ceiling
  `public_branding` already uses" is accurate.

### 2.11 Corrections 2 and 4

- **Correction 2 (16%, not 10%)**: the direction is right and my 14.8% confirms the old
  10% was wrong. Reproduced.
- **Correction 4 (stale line references; `NEXT_STEPS`)**: every line reference in the
  document now checks out — I verified all of `935-952`, `950-951`, `1089-1106`,
  `1204-1268`, `1271-1296`, `1304-1339`, `1500-1510`, `1513-1528`, `101-131`, `139`,
  `32-41`, `572`, `20`, the five slowapi sites and `APRAS-92-spec.md:73-84`. Not one is
  off by a line. The `NEXT_STEPS` correction is also right:
  `_select_milestones`'s docstring (lines 940-944) states "`NEXT_STEPS` is uncapped
  since APRAS-113: the cap moved to the card", and `_next_steps_html`
  (`1042`-) bounds its own output with three slots plus a remainder line. §1.5's
  parenthetical describes this accurately.
- The cited test exists and does what the document says: 
  `tests/test_public_project_report.py:356`,
  `test_the_thirty_first_request_inside_a_minute_is_still_a_200`, asserts over
  `ast.parse(inspect.getsource(public_projects))` scoped to this handler's decorators,
  precisely because `conftest.py:28` sets `app.state.limiter.enabled = False`
  suite-wide. The document's description is exact.

### 2.12 ER13, the hard boundary — clean

From the worktree:

```
$ git status --porcelain backend/app/api/v1/endpoints/public_projects.py \
    backend/app/services/project_report_service.py \
    backend/app/core/limiter.py backend/pyproject.toml
(no output)

$ git status --porcelain
A  docs/tasks/APRAS-93-spec.md

$ git diff --cached --numstat
652	0	docs/tasks/APRAS-93-spec.md
```

I also compared SHA-256 of each of the four working-tree files against
`git show HEAD:<path>`: **all four identical.** One staged path, 652 insertions, zero
deletions, zero production code. ER13 satisfied.

### 2.13 ER8 and ER10 — complete

ER8 — exactly one chosen mechanism (§3: "**Chosen mechanism — exactly one**: a per-IP
rate limit"), and all five named alternatives rejected by name with a stated reason:

| alternative | §3.2 | reason given |
|---|---|---|
| `ETag` with revalidation | bullet 1 | saves only for a visitor who already holds the document; a sweeper never sends `If-None-Match` |
| per-tenant server-side render cache invalidated on writes to `ConstructionProject`, `ProjectMilestone`, `ProjectUpdate` | bullet 2 (all three models named) | per-instance on serverless; invalidation lands in one instance; forbidden staleness |
| CDN cache with purge-on-write | bullet 3 | no per-path purge API for a Python function; reduces to a TTL, i.e. the rejected `Cache-Control` |
| a lower logo embed ceiling | bullet 4 | there is no embed left to lower; changes the upload rule, not one report byte |
| doing nothing | bullet 6 | closest runner-up; loses on the structural point and on cost of adoption |

A sixth, `(logo_url, ETag)` with `If-None-Match`, is rejected at bullet 5. Complete.

ER10 — §4 gives the literal words: "**No.**… **no**, the chosen mechanism does not
require a new dependency in `backend/pyproject.toml`, and **no**, it does not require a
new shared storage backend for `app/core/limiter.py`." Both literal "no". Satisfied.

### 2.14 The three undeclarable figures — all three properly declared

| unmeasurable | declared? | what would settle it |
|---|---|---|
| production RTT to Neon | **Yes**, §1.4: "**The production round-trip latency itself was not measured**", and "**That 27× rests on an assumed 15 ms RTT, not a measured one**" | a timed `SELECT 1` from a deployed function, or Vercel function-duration telemetry for `apras-back` |
| concurrent instance count | **Yes**, §2: "**no, it cannot**" be determined from the repository | the Vercel observability panel for `apras-back`, or `vercel logs` |
| production row counts per tenant | **Yes**, §1.1 | `select count(*) … group by tenant_id` over the three tables, "which the operator can run and this task cannot" |

All three are admissions in writing with a named remedy, which is the correct outcome
for ER5 and ER7. The derived arithmetic is also correctly flagged as derived:
42 × 0.219 = 9.2 ms → 0.40× of 23.0 ms (checks out), and 42 × 15 ms = 630 ms → 27.4×
(checks out, and labelled as resting on the assumption).

**I could not re-verify the 0.219 ms loopback anchor**: nothing is listening on
localhost:5432 on this machine, so there is no local dev Postgres to run a read-only
`SELECT 1` against. I did not substitute production, and I did not treat the gap as a
defect — the figure is an anchor, not load-bearing, and the document already labels the
27× that depends on it. I record it as unverified rather than confirmed.

**Did I find any other estimate wearing the clothes of a measurement?** Essentially no.
The document is scrupulous about this — it labels the 15 ms assumption, the ~67
renders/second inheritance, the synthetic 200-project ceiling ("not a forecast"), and the
threshold figures in §6.3 as thresholds. The one place where an inherited assumption is
presented without its provenance is the "up to twelve cover requests" figure in §3.1
(see §2.9 and Suggestions) — and it understates rather than overstates, so it carries no
decision risk.

---

## 3. Escalation 1 — adding an untracked spec to the repository

**Flagged, and I believe the repository already settles it in favour of staging.**

`docs/tasks/APRAS-93-spec.md` does not exist at `master`:

```
$ git cat-file -e master:docs/tasks/APRAS-93-spec.md
fatal: path 'docs/tasks/APRAS-93-spec.md' exists on disk, but not in 'master'
```

So staging it is an addition, correctly identified. But the convention is not actually
unsettled:

- `docs/tasks/` is **not** gitignored (`git check-ignore` finds no rule).
- **124** files under `docs/tasks/` are tracked.
- **19** are untracked — and they are all recent: APRAS-100, 102, 110, 111, 118, 121,
  122, 123 and 93.

A 124-to-19 split where the 19 are the newest files is a *commit lag*, not a policy
question. The project's settled practice is that specs live in the repository; the
untracked ones are simply work that has not been committed yet. Staging this one follows
the convention rather than departing from it.

I am not treating this as a finding. The operator should know it is an add rather than a
modify, which is now on the record, and may wish to sweep the other 18 in at some point.

---

## 4. Blocking finding — the `selectinload`-at-200-projects figure is reversed

The document presents three corrections to a previous draft. Correction 3 says:

> `selectinload` is **not** faster at 200 projects — it is faster at 20 and within
> noise, slightly slower, at 200.

and §1.3 commits to the sign explicitly:

> **Note the sign:** eager is *not* faster here. Across three runs, cold was
> 402.9 / 410.3 / 469.5 ms and eager 437.7 / 436.6 / 454.9 ms. On a zero-latency
> database, two `IN (…)` queries that hydrate 8,000 milestones and 12,000 bulletins in
> one go cost at least as much as 400 small ones.

and §6.2 repeats it: "It is **not** a CPU win at 200 projects: measured 437.7 ms eager
against 402.9 ms cold, i.e. slightly *worse*."

**This does not reproduce. My measurement says the opposite, unambiguously.**

The document's own figures are two overlapping ranges (cold 402.9–469.5, eager
436.6–454.9) gathered in **blocked** runs — all the cold reps, then all the eager reps.
That design is confounded by thermal drift and background load on a laptop, and I
reproduced the document's sign with it: in one blocked trial I got eager 577.7 vs cold
459.5. In two other blocked trials of the same code I got the reverse (336.1 vs 881.5;
336.7 vs 436.8). The blocked design simply cannot resolve a 10% difference here.

So I used a **paired, interleaved** design: cold and eager alternating within one loop,
same session, same fixture, `expire_all()` + `gc.collect()` before each, 12 counted
paired reps after 2 discarded. Two independent runs:

| run | cold median | eager median | eager wins |
|---|---|---|---|
| 200 projects, run 1 | **406 ms** (min 400, max 420) | **350 ms** (min 345, max 363) | **12 / 12** |
| 200 projects, run 2 | **406 ms** (min 396, max 741) | **350 ms** (min 344, max 396) | **12 / 12** |
| 20 projects (control) | **22.5 ms** | **13.3 ms** | **12 / 12** |

**`selectinload` is faster at 200 projects: 350 ms against 406 ms, a 14% CPU
improvement, winning every one of 24 paired repetitions.** The variance is tight and
the two distributions do not overlap at the median.

Three reasons I am confident this is the document's error and not my harness's:

1. **My cold figure matches theirs to within 1%** — 406 ms against their 402.9 ms. The
   harness is measuring the same thing on the same machine class. It is only the eager
   figure that diverges, and it diverges by 25%.
2. **The 20-project control matches theirs closely too** — my 22.5 / 13.3 against their
   23.1 / 14.1. Same code path, same monkeypatched `_acting_projects` using
   `selectinload(ConstructionProject.milestones)` and
   `selectinload(ConstructionProject.updates)`, and the output was byte-identical to cold
   at 1,481,826 B, so the eager path is genuinely doing the same work.
3. **The causal story in §1.3 is wrong as stated.** "Two `IN (…)` queries … cost at least
   as much as 400 small ones" is the claim, and 400 round trips of per-statement
   overhead — statement construction, `with_loader_criteria` application, cursor setup —
   is exactly what two bulk queries avoid. The scaling argument runs the other way, which
   is why eager wins at *both* sizes rather than only the small one.

**Why this is blocking rather than a suggestion.** The decision in §3 does not depend on
it — I want to be clear that the chosen mechanism is unaffected, and §6.2's *recommendation*
is conservatively worded ("the claim to make is 'constant statement count', not 'faster at
every size'"), so Task B survives and a 14% CPU win only strengthens it. The reason it
blocks is narrower and, I think, unavoidable:

- The document's entire value is the accuracy of its figures. It is the artefact a future
  reader will cite instead of re-measuring — and the `_logo_html` docstring already
  demonstrates that happening, citing this document's logo figure as its own
  justification.
- This specific figure is published as a **correction of a previous error**, in a section
  the document opens by invoking APRAS-111's test-suite audit as "about exactly this
  failure mode". The previous draft was right; the correction is the regression. A
  document that mis-corrects itself in the section about mis-stating things is the one
  thing that cannot be waved through.
- It is cheap to fix: re-measure with a paired design and amend three sites.

**What to change:**

1. §1.3's "**Note the sign:** eager is *not* faster here" paragraph — the figures and the
   `IN (…)` reasoning both need replacing. If the author's own paired re-run disagrees
   with mine, publish the paired figures and the design; if it agrees, the honest
   statement is "eager is faster at both sizes, by ~39% at 20 projects and ~14% at 200".
2. The intro's correction list, bullet 3 — it currently asserts the previous draft was
   wrong about this. On my measurement it was right, and the retraction should be
   retracted.
3. §6.2 Task B's "It is **not** a CPU win at 200 projects: measured 437.7 ms eager
   against 402.9 ms cold, i.e. slightly *worse*." The narrowed headline claim ("constant
   statement count") can stay — it is the right primary justification regardless — but
   the supporting sentence states a false fact.

Note that fixing this makes the document's case *stronger*, not weaker. Nothing else in
it needs to move.

---

## 5. Recommendation on the D3 reversal

**My verdict: adopt the reversal. Add `@limiter.limit("30/minute")` to
`get_public_projects_report`.**

I reviewed the three legs separately, as the document asks, because they are not of
equal strength and the document is right to have refused to blend them.

### 5.1 The mechanism leg is sound, and it is the one that actually reopens D3

D3's text (`APRAS-92-spec.md:73-84`, verified verbatim) declines a cache and a limiter
together, on **one shared premise**: `limiter.py` has no `storage_uri`, therefore "both a
cache and a limit would be per-process on Vercel's serverless runtime and would behave
inconsistently between instances."

The premise is true — I confirmed `app/core/limiter.py` builds
`Limiter(key_func=get_remote_address)` with no storage backend, and §2's conclusion that
any in-process state is per-instance is correct. But the inference is valid for one
mechanism and invalid for the other, because "behaves inconsistently between instances"
denotes two different things:

- For a **cache**, inconsistency means instance B serves a report that instance A has
  already invalidated. That is stale data — a direct violation of the operator's binding
  constraint that a freshly published bulletin must be visible immediately. Fatal.
- For a **limiter**, inconsistency means the effective ceiling is `instances × 30/min`
  instead of `30/min`. The guard is less precise than its number suggests, and it fails
  **open**. It cannot serve a stale byte, because it holds no copy of anything. A degraded
  limiter is still a limiter.

So D3 declined the limiter on a reason that does not apply to the limiter. That is a
logical defect in the prior decision, established from code and from §5's measurement
rather than from taste, and it is sufficient grounds to reopen regardless of cost.

§5's sweep is what closes the other half: I reproduced 160 statements and
indistinguishable wall clocks on both rows, so a cache provably cannot bound the only
unbounded property of this route. D3's premise "a cache and a limit are in the same boat"
is false in both directions — the cache cannot help even if it worked, and the limiter
works even though it is approximate. With the cache eliminated on correctness and the
limiter's sole objection shown to be inapplicable, the per-IP limit is the only lever
left standing.

I also note the approximation is not novel: six live call sites already run on exactly
this per-process limiter in production, including the two `public_branding` routes at the
same `30/minute`. Accepting it here adds no new class of risk.

### 5.2 The cost leg genuinely fails, and the document is right to concede it

I verified this rather than taking it on trust. A 20-project render is **22.5 ms** of CPU
and ~146 KB (their fixture: 23.0 ms, 163 KB); a 1-project render is **1.95 ms** and
~19 KB. The logo — the single biggest item in the response when D3 was taken, at a
measured **88.5%** of a small report — is now **86-109 bytes**, because APRAS-105 deleted
the embed. The route got *cheaper* since D3, not more expensive.

**On cost alone, "do nothing" wins.** §6.1 says so in those words and §3.2's sixth bullet
calls it "the closest runner-up, and defensible on the numbers". Both are accurate. I
want to underline that this is the correct reading of the evidence and not excessive
modesty: there is no measurement in this document that shows this route is expensive.

### 5.3 The structural leg is a judgement, and it is the one I find persuasive

Every factual component checks out:

- The cover route carries `@limiter.limit("300/minute")` at `public_projects.py:139`.
- It landed **after** D3: APRAS-92 at `642e23d` on 2026-09-27, APRAS-104 at `9d4cf24` on
  2026-09-29.
- The module's own docstring argues the governing principle, verbatim at lines 54-56:
  "a route strictly more amplifying than one that is limited cannot be unlimited on the
  limited one's reasoning."
- The budget figures are in the unmetered HTML, by D2's parity decision — and the
  docstring concedes the consequence at lines 79-80: "the report HTML itself still
  renders, because it comes from the unmetered route above."

The asymmetry is real and, I think, hard to defend once seen. APRAS-104 already committed
this project to metering this public surface. It metered the *derivative* half — the
images — and left the half that carries the data unmetered. An adversary who wants the
budget figures of every condominium never requests a cover at all: they pull the HTML,
which is cheaper for them and unlimited. A limiter whose principal bypass is "ask for the
valuable thing instead of the bulky thing" is doing less work than its presence implies.

Against that: the cost of adoption is one decorator, one import already present, one
`request: Request` parameter with six in-repo precedents for the exact `# noqa: ARG001`
form, and no change to `pyproject.toml`. The only real downside is a 429 for residents
behind a shared NAT, and 30/minute against the document's modelled ~20 views/minute for
a condominium office leaves headroom. Low cost, low risk, removes a visible inconsistency.

### 5.4 Could an operator reaffirm D3 without contradicting any figure?

**Yes. The developer's claim is correct, and I want to state it as plainly as they did.**

Nothing in this document shows the route is expensive. §1.1 shows the opposite at every
plausible size; the largest item at D3 time is gone; §5's sweep measures throughput but
does not establish that the throughput is harmful. The reversal rests entirely on (a) the
logical defect in D3's reasoning and (b) a judgement that an unmetered parent beside a
metered child is an unacceptable exposure. (a) is an argument about D3's internal
consistency, not a new fact about cost; (b) is explicitly a value judgement.

A coherent reaffirmation of D3 runs: the slug is guessable by D1, the budget figures are
published at full parity by D2, so the data on this route was *deliberately given away*.
A rate limit does not protect it — §5 says so, "What it does **not** close: **exposure**."
Metering a route whose contents are intentionally public is ceremony; the cover limiter
exists for a different reason (paid Blob egress, per the docstring's "fan-out guard, not
an egress budget"), and that reason does not transfer to an HTML route with no egress
bill. Therefore: no limiter, revisit if a cost signal ever appears.

That position contradicts **no figure in the document**. It weighs §3.1's structural
point differently, which is a matter of judgement, not of measurement. §6.1's closing
sentence — "An operator who weighs it the other way can reaffirm D3 without contradicting
a single figure in this document" — is true, and splitting the justification instead of
burying it is the single best decision in this document. It should be read as the
strength it is.

### 5.5 Where I come down

Adopt, on §5.1 primarily and §5.3 secondarily. The decisive consideration for me is not
exposure but **coherence**: D3 declined the limiter for a reason that applies to caches
and not to limiters, and that defect is demonstrable rather than arguable. Once the
mechanism objection falls, the project is choosing between an unmetered parent and a
metered child in the same module on the same reasoning, and it has already chosen to
meter. The cost of making the two consistent is one line.

But this needs the operator's signature, exactly as §6.1 says, and the operator should
sign it knowing they are endorsing a judgement about acceptable exposure and not
ratifying a measured cost problem. I would not want this adopted on the mistaken
impression that the numbers forced it. They did not.

---

## 6. Escalation 3 — should `_stage_detail_html` become a task?

**My judgement: yes, promote it to a low-priority backlog task. Not blocking.**

The measurement is real — I reproduced it independently at **167,166 B for one project**
at 20 milestones × 100 leaves, against **145,825 B** for my entire 20-project report, at
~74-83 B/leaf. A single obra outweighing the whole report is a genuine finding, and
`_stage_detail_html` (`project_report_service.py:1204-1268`) caps neither the milestones
nor each stage's `leaves` tuple.

The document's reasoning for recording it as a §6.3 reopening condition rather than a
task is defensible: `detail_json` is `NULL` on every production row, so the dimension is
dormant, and the code says so at lines 1227-1229. Deferring dormant work is usually right.

Two things push me the other way:

1. **A reopening condition with no detector is indistinguishable from no condition.** The
   threshold is "a single project exceeding ~500 decoded leaves". Nothing in the system
   measures leaves per project, nothing alerts on response size, and no test asserts a
   bound. The condition will be noticed when a report is slow or a page is heavy — which
   is the same moment it would have been noticed without the condition written down. The
   document has done the measurement; what is missing is anything that fires.
2. **The dormancy is one operator command from ending.** The document correctly names
   `backend/scripts/sync_obras_from_drive.py` as the only writer of `detail_json`. That
   script is sitting **untracked in the working tree right now** and is an operator tool
   in active use. "Dormant until the operator re-runs the sync by hand" is a weaker
   guarantee than it sounds when the operator runs that sync as part of normal work. The
   gap between dormant and live is a single invocation, with no cap in the path.

What I would create: a low-priority task to put a bound in `_stage_detail_html` — or, at
minimum, a test that asserts a measured ceiling on stage-detail bytes per project so the
threshold becomes something that fails rather than something that was foreseen. The
measurements in §1.5 are sufficient input; no new investigation is needed.

I am keeping this out of the blocking list because the document did record the dimension,
with a measured threshold and a named mechanism, which is a defensible disposition of a
dormant risk. It belongs in the operator's hands as a backlog decision, not as a gate on
this document.

---

## 7. APRAS-124 — no conflict

APRAS-124 ("Cache the public tenant logo route so repeat page loads do not re-fetch the
bytes") exists on the board in `backlog`. I checked whether anything in this document
supersedes or pre-empts it.

**Nothing does.** The document's only logo-cache statement is §3.2's fifth bullet,
`(logo_url, ETag)` with `If-None-Match`, and it is scoped to *this* route — it concerns
an `ETag` over the **report** response back when the logo was embedded in it, and it is
dismissed as "Moot for the same reason as the previous item: the logo is no longer in the
response." That says nothing about caching the separate
`GET /api/v1/public/tenants/{slug}/logo` route, which is APRAS-124's subject.

If anything the two agree: `_logo_html`'s docstring (lines 1322-1323) already anticipates
APRAS-124's premise — "The browser now fetches the image once and caches it on its own
terms" — and the de-embedding measured in §1.6 is precisely what makes a logo-route cache
worth having. One clarification is worth adding so a future reader does not mis-cite
§3.2 as having rejected it; see Suggestions.

Separately, and for the operator's awareness rather than as a finding:
`public_projects.py:77-79` assigns `Cache-Control` **for the cover route** to APRAS-93
("The real answer is ``Cache-Control`` plus server-side resizing, both out of scope here
and both belonging with **APRAS-93**, where a cache changes the arithmetic"). This
document scopes itself to the report route and does not take that question up. That is a
reasonable scope choice, but it leaves the cover route's caching question unowned now
that APRAS-93 is concluding. Worth a follow-up, and APRAS-124 may be the natural home.

---

## Suggestions

- **Pin the fixture's text lengths, not just its row counts.** The "Measurement
  environment" paragraph fixes projects / milestones / bulletins / photos, but every
  absolute byte figure also scales with title, description and bulletin-body length. My
  independent fixture reproduced every *slope* exactly (115→119 B/front against the
  document's 115→119; 13,039 B shell against 13,062 B) while landing 5-10% low on
  absolute response sizes. Recording the generator's string lengths — or the one-line
  fixture recipe — would make the absolute figures reproducible rather than merely
  directionally reproducible.
- **The 109 B / 0.55% logo figure depends on an unstated base URL.** I measured
  `_logo_html` at **86 B** and 0.46%, because the emitted
  `<img src="http://localhost:8000/api/v1/public/tenants/sintetico/logo" alt="Sintetico">`
  varies with the configured public base URL and the tenant name, neither of which the
  environment paragraph pins. The claim that matters — well under 1% of the response —
  is robust either way; consider stating it as "~100 bytes, under 1%" with the URL
  dependency noted.
- **`_logo_html`'s docstring says 89%, this document now says 88%.** I measured **88.5%**.
  The docstring (`project_report_service.py:1321`) cites this document as its source, so
  the two should not disagree. Since ER13 forbids touching the service file here, the
  cleanest fix is a note in §1.6 that the production docstring carries the earlier
  rounding, and a line in Task A or a follow-up to reconcile it.
- **Attribute the "twelve cover requests" figure.** §3.1 says "One report view costs one
  report request and up to twelve cover requests" as though it were a property of the
  system. It is APRAS-104's *planning* figure ("the largest report to plan for carries
  12 obras", `public_projects.py:60`); in code `_project_hero` emits one cover per
  project, uncapped, so a 20-project report triggers twenty. The real fan-out is `N`.
  This understates rather than overstates, so it carries no decision risk — but a
  measurement document should not let an inherited assumption read as a measured bound.
  Suggest: "one per project — twelve on the report APRAS-104 sized its limiter for, and
  uncapped in general".
- **The upload inventory count does not reproduce.** §1.6 reports "Embeddable uploads
  inspected under `backend/static/uploads/`: **8,090**"; I count **9,859** files there
  now. The load-bearing figures match exactly (largest 108,018 B; zero over 512 KiB), and
  the gap is probably either the "embeddable" filter (mine was unfiltered) or growth in a
  gitignored, operator-managed directory. Stating the filter would settle it.
- **§5's "~5.5 MiB/s" is 5.5 MB/s.** 661,750 B / 0.1195 s = 5.54 **MB**/s = 5.28 MiB/s.
  Trivial unit slip in an otherwise scrupulous document.
- **The H1 and the board title disagree.** The document's heading ends "without going
  **private**"; the Meridian card reads "without going **stale**". Both themes are
  covered (§5 for exposure, the binding constraint for staleness), but the titles should
  match whichever the operator considers canonical.
- **Add one sentence so §3.2 is not mis-cited against APRAS-124.** The
  `(logo_url, ETag)` bullet rejects an `ETag` over the *report* response, not caching of
  the public logo *route*. A clause noting that the logo route's own caching is out of
  scope here and now owned by APRAS-124 would prevent a future reader citing this
  document as having declined it.
- **The cover route's `Cache-Control` question is about to be unowned.**
  `public_projects.py:77-79` assigns it to APRAS-93; this document does not address it.
  Worth explicitly reassigning in §6.2's "not in either task" list, so it does not fall
  through when APRAS-93 closes.
- **Consider promoting the `_stage_detail_html` dimension to a backlog task**, per §6 —
  a reopening condition with no detector and a one-command path out of dormancy.
- **Use paired/interleaved timing for any future A-vs-B figure in this document.** The
  blocked design (all A reps, then all B reps) is what produced the reversed
  `selectinload` sign; it cannot resolve differences under ~20% on this machine. The
  single-state figures (§1.1, §1.5, the sweep) are unaffected and reproduced well.

---

VERDICT: REJECTED

1. `docs/tasks/APRAS-93-spec.md:141-146` (and `:28-29`, `:537-543`) — the claim that
   `selectinload` is *not* faster at 200 projects does not reproduce and its sign is
   reversed. Under a paired interleaved design (12 counted paired reps, two independent
   runs) eager measured **350 ms against cold 406 ms, winning 12/12 paired reps in both
   runs** — a 14% CPU improvement — with my cold figure matching the document's 402.9 ms
   to within 1% and my 20-project control matching its 23.1/14.1 ms closely. The document
   publishes this as a *correction* of a previous draft, so a correct earlier figure has
   been replaced with an incorrect one, in the section that opens by invoking APRAS-111's
   audit as being "about exactly this failure mode". The supporting causal claim at
   `:143-146` ("two `IN (…)` queries … cost at least as much as 400 small ones") is also
   wrong, since avoided per-statement overhead is what makes eager win at both sizes.
   Fix three sites: §1.3's "Note the sign" paragraph and its figures, the intro's
   correction bullet 3 (which retracts a correct claim), and §6.2 Task B's "not a CPU win
   at 200 projects" sentence. §6.2's narrowed headline ("constant statement count") and
   the §3 decision are unaffected — correcting this strengthens the document's case.
