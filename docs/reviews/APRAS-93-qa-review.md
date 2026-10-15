# APRAS-93 — QA verification report

VERDICT: APPROVED

Task: "Decide how to make the public obras report cheap to serve without going stale".
Worktree: `/Users/heitor/workspace/apras/.claude/worktrees/agent-a7a31a09fc3ca4bf4` at `bc78696`.
Harness: `/private/tmp/claude-501/-Users-heitor-workspace-apras/06230b8a-d0ef-40dd-929b-83bb4eb6abbf/scratchpad/dev93/`.

Verified against the 13 expected results only. The five code reviews and the
developer reports under the harness directory were deliberately not read.

## Method and machine conditions

Everything below was re-derived by running the harness, re-reading the cited
repository files at the cited line numbers, and building my own mutants. No
figure was accepted off the page.

Machine conditions during verification, stated because they bound what the
wall-clock judgements can mean: `uptime` reported one-minute load averages of
**16.2 → 45.1** across the session (other work was live on this laptop
throughout). Every absolute millisecond figure I measured is therefore inflated
relative to the document's published figures, by factors of 1.3× to 1.9×. The
document discloses exactly this hazard up front (measurement-environment
paragraph; §1.3.2's 4.5× spread table) and names the date, commit, interpreter,
database and fixture its own figures were taken under. Per the brief, R1/R3/R5
are judged on reproducibility-within-disclosed-variability and on the honesty of
that disclosure, not on decimal agreement.

Nothing read the production database and nothing called the production API. All
measurements were in-memory SQLite via `run.sh`, whose `POSTGRES_URL` is a
synthetic string that is never connected to (`run.sh:8`). `curl` was not used.

## Expected Results Checked

- [x] **R1 — four+ render sizes with measured median wall clock, measured bytes,
      and all four fixture counts per row.**
      Verified via `run.sh t_sizes.py`. §1.1 publishes **five** rows, each naming
      projects / milestones-per-project / bulletins-per-project /
      photos-per-bulletin, a median wall clock and a byte size.
      My re-run, byte column first:

      | row | published B | my B | published stmts | my stmts | published ms | my ms |
      |---|---|---|---|---|---|---|
      | 1/6/3/3 | 20,109 | **20,109** | 4 | **4** | 2.07 | 3.42 |
      | 5/12/8/4 | 50,897 | **50,897** | 12 | **12** | 5.88 | 8.10 |
      | 20/20/20/6 | 171,507 | **171,507** | 42 | **42** | 22.39 | 41.93 |
      | 60/40/60/8 | 530,607 | **530,607** | 122 | **122** | 107.26 | 201.56 |
      | 200/40/60/8 | 1,738,448 | **1,738,448** | 402 | **402** | 440.16 | 588.55 |

      Every byte count and every statement count reproduced **exactly**. The
      zero-project shell reproduced at **13,061 B** and the per-project slope at
      **+7,048 / +7,052 / +7,052 B** — both exact. `fixture_probe.py` also
      reproduced the shell fit at all four tenant-name lengths exactly
      (13,031 / 13,039 / 13,050 / 13,061 at 1 / 9 / 20 / 31 chars) and the
      per-character sensitivities exactly (+6 B per milestone-title char,
      +3 B bulletin body, +9 B photo URL, +1 B project description).
      The wall clocks are 1.5–1.9× the published ones at load average ~16; the
      document publishes its conditions and tells the reader in §1.1 to read the
      millisecond column "as an order of magnitude on an idle laptop and nothing
      finer". Reproducible within the disclosed variability. **PASS.**

- [x] **R2 — measured statement count, expressed as a formula in the project count.**
      Verified via `run.sh t_route.py`, which counts through the real HTTP route
      with `TestClient` and a `before_cursor_execute` listener. `2N + 2`
      reproduced exactly at all seven values of `N`:
      `0→2, 1→4, 2→6, 5→12, 20→42, 60→122, 200→402`.
      The document's six-statement breakdown of the `N = 2` case also reproduced
      in the same order the listener saw it: `tenant`, `construction_project`,
      `project_update`, `project_milestone`, `project_update`,
      `project_milestone` — confirming §1.2's counter-intuitive point that the
      handler's `get_by_slug` costs no extra statement (`_acting_tenant`'s
      `session.get(Tenant, …)` is an identity-map hit). **PASS.**

- [x] **R3 — one fixed render, byte size stated, with median wall clock and
      statement count for cold / warm / eager, plus the dominance percentage.**
      Verified via `run.sh t_states.py 20 20 20 6` and `… 200 40 60 8`.
      At 20/20/20/6 (control run): **cold 42 stmts, eager 4 stmts, warm 2 stmts,
      all three arms 171,507 B** — identical to the published statement counts and
      byte count. At 200/40/60/8: **402 / 4 / 2 statements, all three arms
      1,738,448 B** — again exact.
      The percentage: the document states ORM data access dominant at ~85% (20
      projects) and ~90.5% (200 projects), with disclosed pooled ranges of
      13.2–15.9% and 8.1–10.4% for the assembly share. My runs:
      **15.3% at 20 projects** (warm 4.87 / cold 31.88 ms) and **8.2% at 200
      projects** (warm 41.93 / cold 513.77 ms) — both inside the disclosed bands.
      One earlier 20-project run gave 23.8%, outside the band; its warm arm was
      9.28 ms, far above the ~3.3–3.6 ms floor, and §1.3 states the precondition
      explicitly ("computable only in runs of that shape whose warm arm was at
      its floor"), so that run is excluded by the document's own stated rule
      rather than by a convenient one. Direction (data access dominant) held in
      every run. **PASS.**

- [x] **R4 — an uncapped response dimension, the file and line range of the
      function that leaves it uncapped, and measured bytes at two+ values.**
      Verified via `run.sh t_dims.py` plus direct reading of the cited code.
      Both cited functions are real and genuinely uncapped at the cited lines:
      `_select_milestones` is defined at `project_report_service.py:935` and its
      final `return sorted(rows, key=_stage_sort_key)` at `:952` applies no slice
      — the `[:3]` applies only to `DONE` — with the comment at `:950-951`
      ("truncating it would hide one") present as described;
      `_stage_detail_html` is defined at `:1204` and no `[:n]` slice appears
      anywhere in `:1204-1268`.
      Measured sizes reproduced to the byte at **every one of ten** rows:
      dimension one 19,540 / 19,655 / 20,115 / 25,255 / 43,005 / 66,805 B with
      B-per-front 115.0 / 115.0 / 116.6 / 117.9 / 118.5, and **4 statements at
      every row**; dimension two 20,976 / 31,309 / 54,070 / 168,471 B with
      B-per-leaf 129.2 / 82.7 / 73.7. The `0.98×` ratio against §1.1's
      171,507 B re-derives from my own numbers (168,471 / 171,507 = 0.982), and
      the document labels that ratio as fixture-dependent rather than asserting
      the inequality. **PASS.**

- [x] **R5 — the round-trip term as a number relative to the measured CPU term,
      and an explicit statement that the round-trip latency was not measured.**
      §1.4 states **0.40×** (42 × 0.219 ms loopback against 23.2 ms of CPU) and
      **~27×** at an assumed 15 ms WAN RTT. Both numbers re-derive:
      42 × 0.219 / 23.2 = 0.396; 42 × 15 / 23.2 = 27.2. The 27× is explicitly
      labelled as resting on an assumed RTT.
      The required explicit statement is present verbatim: "**The production
      round-trip latency itself was not measured.**", with "Production database
      reads were not available to this task and no credentialled call was made"
      and a named settling procedure (a timed trivial query from a deployed
      function, or Vercel function-duration telemetry).
      The 0.219 ms loopback anchor I did **not** re-measure, and the document
      does not claim I could: it labels it "measured once, not re-verified",
      names what would settle it, and says the figure is not load-bearing. See
      Suggestions — the precondition it cites has since changed. **PASS.**

- [x] **R6 — real logo file's byte size by path, the `data:` URI size it inflates
      to, and worst cases at 2 MiB and 512 KiB.**
      Verified by `run.sh t_logo.py` and independently by my own
      `base64.b64encode` of the file. Every figure reproduced **exactly**:
      `/Users/heitor/workspace/apras/backend/static/uploads/asvi-logo.png` is
      **108,018 B**; base64 payload **144,024 B**; `data:` URI **144,046 B**
      (22-byte prefix); worst case at 2 MiB **2,796,204 B** base64 /
      **2,796,226 B** with prefix; at 512 KiB **699,052 B** / **699,074 B**.
      `TenantService.LOGO_MAX_FILE_SIZE = 2 * 1024 * 1024` confirmed at
      `tenant_service.py:572`. The incidental figures also reproduced exactly:
      the emitted tag is 108 B with no `data:` substring, 0.53% of a 20,217 B
      response, the hypothetical embed share 87.7%, and the uploads inventory
      9,859 files / 8,090 embeddable / largest 108,018 B / **zero** over
      512 KiB. `_logo_html` is at `:1304` and its docstring's "**89%**" is at
      `:1321` as stated. **PASS.**

- [x] **R7 — production deployment model, the repository file that establishes it,
      and an explicit statement on whether the instance count is determinable.**
      §2 names a **Vercel serverless function** and cites **`backend/vercel.json`**.
      I confirmed `vercel.json` is tracked (`git ls-files`) and contains exactly
      one `routes` entry mapping `"/(.*)"` to `index.py`, and that
      `backend/index.py` is tracked. The `Dockerfile`'s `--reload --reload-dir app`
      marks it as the development container, as stated.
      The explicit answer is present: "**Whether the number of concurrently live
      instances can be determined from the repository: no, it cannot.**" Its cited
      evidence is a grep, and the grep reproduces: `git grep -E
      'maxDuration|"regions"|"memory"|"functions"'` over tracked `backend/`
      returns **nothing** (exit 1). What would settle it is named: the Vercel
      observability panel for `apras-back`, or `vercel logs`. **PASS.**

- [x] **R8 — exactly one chosen mechanism; five named rejections, each with a reason.**
      Counted mechanically. §3 line 1132: "**Chosen mechanism — exactly one: a
      per-IP rate limit on the public report route**, `@limiter.limit("30/minute")`".
      One chosen mechanism, no second.
      §3.2 carries **six** `- **…**` rejection bullets, each with a stated reason;
      all five required ones are present by name:
      1. `ETag` with revalidation on every request — reason: the saving reaches
         only a visitor who already holds the document and does nothing against a
         sweeper, who never sends `If-None-Match`.
      2. Server-side cache of the rendered HTML, keyed per tenant, invalidated on
         writes to `ConstructionProject`, `ProjectMilestone` and `ProjectUpdate`
         (all three models named) — reason: per-instance in a serverless
         function, so the invalidation lands in one instance only and another
         serves the old report, which is the forbidden outcome.
      3. CDN cache with purge-on-write — reason: without a purge API it is a TTL
         (the rejected `Cache-Control` renamed); with one it still holds a copy in
         a safety-critical invalidation path. The platform claim is labelled
         unverified and the rejection is shown not to depend on it.
      4. A lower logo embed ceiling (512 KiB, falling back to linking) — reason:
         there is no embed left to lower; §1.6 measures the ceiling's contribution
         to this route at zero bytes, and lowering it only degrades uploads.
      5. Doing nothing — reason: loses on §3.1's structural point (the amplifying
         child route is metered while its cheaper parent is not) and on cost of
         adoption.
      The sixth, `(logo_url, ETag)` with `If-None-Match`, also carries a reason.
      No bullet is listed without a reason. **PASS.**

- [x] **R9 — names D3, its location, the reason it gave, states the reversal,
      names the justifying measurement.** Read adversarially; I located D3 myself.
      - Identifier and location: §6.1 gives **`D3` — "No rate limit, no cache"**
        at **`docs/tasks/APRAS-92-spec.md:73-84`**. Checked: `grep -n` puts
        "**D3 — No rate limit, no cache.**" at line **73**, and the D3 block runs
        to line **84**, with line 85 blank and 86 starting the next heading. The
        line range is exact, not approximate.
      - The reason, checked against the actual text rather than the
        characterisation: APRAS-92 line 82-84 reads "`backend/app/core/limiter.py`
        builds `Limiter(key_func=get_remote_address)` with no `storage_uri`, so
        both a cache and a limit would be per-process on Vercel's serverless
        runtime and would behave inconsistently between instances." The
        document's rendering — no shared storage backend, therefore per-process
        on a serverless runtime, therefore inconsistent between instances — is
        accurate and quotes the operative clause verbatim. It does not overstate:
        D3 raised that objection against the cache **and** the limiter jointly,
        and the document says so in as many words ("D3 declined the limiter and
        the cache together, on one shared objection") rather than pretending the
        objection was limiter-specific. It also correctly reports D3's separate
        `Cache-Control` ground. I found no misquotation.
      - The reversal, explicitly: "**This document's recommendation reverses D3.**"
        Present, in those words and bolded. It further concedes "D3 was not wrong
        about the mechanism" and that on cost alone "do nothing" survives §1 intact.
      - The justifying measurement, named: "**The measurement that justifies the
        reversal is §5's sweep**". I re-ran it (`run.sh t_sweep.py`): **160
        statements for the same slug twenty times and 160 statements for twenty
        distinct slugs, in all three trials**, with 684,180 B on all six arms —
        exact. The wall-clock half reproduced as the non-finding the document
        reports it as (same-slug 86.9 / 95.7 / 87.8 ms against distinct-slug
        101.1 / 88.5 / 90.8 ms: the sign flipped between trials, and the
        within-arm spread exceeded the between-arm gap).
      - Corroborating code read: `public_projects.py:32-41` does record "no
        `@limiter.limit`… deliberately and not by omission" and names APRAS-93 as
        the owner of any revisit; `:45-46` does say the cover limiter "does
        **not** reverse D3"; `:139` does carry `@limiter.limit("300/minute")`;
        `:56-58` does give APRAS-104's "12 obras" planning figure. The document
        is careful to call 12 a planning figure and not a measured bound.
        **PASS.**

- [x] **R10 — yes or no, in those words.** §4 states "**No.**" and then, "In the
      words the question asks for: **no**, the chosen mechanism does not require a
      new dependency in `backend/pyproject.toml`, and **no**, it does not require
      a new shared storage backend for `app/core/limiter.py`." The words are
      literally present, once per clause.
      I checked the answer is **true** rather than merely stated, by reading both
      files: `backend/pyproject.toml:20` is `"slowapi>=0.1.10"`, so the dependency
      already exists; `app/core/limiter.py` is six lines and already constructs
      `Limiter(key_func=get_remote_address)`, so adding `@limiter.limit("30/minute")`
      to one handler touches neither file. The six existing call sites the
      document enumerates all exist exactly where named — `auth.py:115`,
      `invitations.py:130`, `invitations.py:156`, `public_branding.py:65`,
      `public_branding.py:103`, `public_projects.py:139` — each with the
      `request: Request  # noqa: ARG001` parameter the document says Task A would
      copy. The honest caveat is in the same section: the limiter has no shared
      storage, so the effective ceiling is `instances × 30/min`, and making it
      strict *would* need new infrastructure, which is placed out of scope.
      That caveat is what makes the "no" true rather than evasive. **PASS.**

- [x] **R11 — report not made private; distinct-slug sweep unaffected by any cache
      because every key is cold.** Both statements present in §5, the first as
      "**No mechanism chosen here makes the report private, and neither would any
      cache.**" and the second as "**A sweep across distinct tenant slugs is
      unaffected by any cache, because every key is cold.**" with the mechanism
      spelled out (a per-tenant cache turns row one into one render plus nineteen
      hits and leaves row two at twenty cold keys and twenty full renders). The
      supporting sweep reproduced exactly as recorded under R9. The section also
      correctly flags that its byte equality is **printed and observed, not
      asserted** (`t_sweep.py:49` asserts only the 200 status) — which I confirmed
      by reading the script. **PASS.**

- [x] **R12 — whether follow-up tasks should be created, with per-task touches and
      must-not-touch lists.** §6.2 answers "**Yes, two.**"
      *Task A — the rate limit*: touches `backend/app/api/v1/endpoints/public_projects.py`
      (decorator, `request: Request` parameter, docstring paragraph at 32-41) and
      `backend/tests/test_public_project_report.py`. Must not touch:
      `project_report_service.py`, `app/core/limiter.py`, `backend/pyproject.toml`,
      `backend/requirements.txt`.
      *Task B — `selectinload`*: touches `backend/app/services/project_report_service.py`
      (`_acting_projects`, lines 1513-1528, plus docstring) and
      `backend/tests/test_project_report.py`. Must not touch:
      `public_projects.py`, `app/core/limiter.py`, `backend/pyproject.toml`.
      Both tasks list both halves; neither list is empty or implied. The cited
      line ranges check out — `_acting_projects` is defined at `:1513` with its
      `select(ConstructionProject).order_by(…)` inside, and `_acting_tenant` at
      `:1500` with the `session.get(Tenant, …)` at `:1510`. §6.3 additionally
      gives five reopening conditions although R12 only requires them in the
      recommend-none case. The exclusion list ("Not in either task…") is also
      present. **PASS.**

- [x] **R13 — no production code; four paths byte-identical to committed content.**
      The exact command the result names was run in the worktree:
      `git status --porcelain backend/app/api/v1/endpoints/public_projects.py
      backend/app/services/project_report_service.py backend/app/core/limiter.py
      backend/pyproject.toml` → **printed nothing**, exit 0.
      Independently hashed each path against `git show HEAD:<path>` with
      `shasum -a 256`: all four **SAME**. `git diff --cached --name-only` shows
      exactly one staged path, `docs/tasks/APRAS-93-spec.md`, staged as `A`.
      `git stash list` is empty. HEAD is `bc78696`. **PASS.**

## Harness non-vacuity — mutants I built myself

The brief's central demand. For each of the four byte-equality assertions the
document advertises, I wrote my own mutant, confirmed the mutation reached the
rendered output (by reading the byte count the run printed), and compared exit
codes against an unmutated control run of the same invocation. I did not re-run
any mutation described in the document.

My mutants inject by patching `dh.render` before `runpy.run_path` loads the
probe, so the probe's own `from dh import render` picks up the patched callable.
Nothing in `dev93/` was edited; the original harness is unmodified.

1. **`t_states.py:79` (`assert len(b) == 1, b`) — bites in the three-state
   configuration.** Mutant: shorten the output by 11 bytes **only while the eager
   arm is active** (detected by `project_report_service._acting_projects is
   dh._eager_acting_projects`). Result: the run printed `eager: … bytes 171496`
   against `cold`/`warm` at `171507` — so the mutation demonstrably took effect —
   and died with `AssertionError: {171496, 171507}` at `t_states.py:79`,
   **exit 1**. Unmutated control of the identical invocation: **exit 0**,
   `byte-identical across the 3 measured state(s): [171507]`.

2. **The two vacuity properties the document discloses are real, and I confirmed
   both independently.** (a) Single-state run, **every** render mutated 11 bytes
   short: printed `warm: … bytes 171496` and `byte-identical across the 1
   measured state(s): [171496]`, **exit 0** — vacuous, exactly as the document
   says at its lines 86-92 and as `t_states.py:76-78` says in the file.
   (b) Three-state run with the **same uniform** mutation: all three arms printed
   `171496` and the run **exited 0** — confirming the document's statement that
   the check compares arms with each other and never against an expected value,
   so a uniform mutation passes it. The document names both of these weaknesses
   itself rather than leaving them for a reader to find, which is why they are
   reported here as confirmed disclosure and not as findings.

3. **`dh.py:249` (`assert b_cold == b_eager`, inside `paired`) — bites.** Mutant:
   same eager-only 11-byte truncation, run through `p200.py 20 20 20 6`. Result:
   `AssertionError: (171507, 171496)` at `dh.py:249`, **exit 1**. Unmutated
   control: **exit 0**, `byte-identical: True (cold 171507 B, eager 171507 B)`,
   `cold: stmts=42 bytes=171507` / `eager: stmts=4 bytes=171507`. The control run
   also reproduced the paired finding's sign and rough magnitude — eager faster
   by **47.5%**, winning **11/12** paired reps at 20 projects, against the
   published 41–47% — under a load average of ~20.

4. **`loadpair.sh:29-35,57-67` — bites, and bites on the case an arm-versus-arm
   comparison would miss.** This is the one that matters most, because its arms
   are single-state runs where check 1 is vacuous. Three invocations, one pair
   each (`PAIRS="1"`), with `HOGS=0` so no contention was induced and no process
   was left behind:
   - *Control* (`loadpair.sh`): both arms `bytes=1738448`, `byte identity
     asserted on all 2 arms`, **exit 0**.
   - *Uniform render mutation* (a copy of the driver pointed at my uniformly
     −11 B render, otherwise byte-identical to `loadpair.sh` — verified by
     `diff`, one line differs): both arms printed `bytes=1738437`, so the arms
     **agreed with each other** and the `k != 1` arm-versus-arm test would have
     passed; the comparison against the literal printed `BYTE MISMATCH` on each
     arm and the driver **exited 1**. This independently confirms the document's
     claim at its lines 106-108 that the expected-literal comparison, not the
     arm-versus-arm one, is what catches a uniform mutation.
   - *Mutated compared value* (`EXPECT_BYTES=1738449`): `BYTE MISMATCH` on both
     arms, **exit 1**.

5. **`t_warmdist.py:80` (`assert len(sizes) == 1, sizes`) — bites.** Mutant:
   shorten **only repetition 5** of the 13. Result: `AssertionError: {171496,
   171507}` at `t_warmdist.py:80`, **exit 1**. Unmutated control: **exit 0**,
   `byte-identical across all reps: [171507]`.

6. **The document's round-5 self-correction about `t_warmdist.py`'s ordering is
   accurate.** It says the `gc` regime is applied *after* the graph is seeded and
   pinned and after the shared `gc.collect()`, correcting draft 5's claim that it
   happens before the graph is built. Read directly: `seed(…)` at `:51`,
   `pinned`/`held` at `:53-54`, `gc.collect()` at `:58`, `if regime == "off":
   gc.disable()` at `:59-60`. The document's description matches the file; draft
   5's did not.

7. **`t_sweep.py` asserts only the HTTP status**, at `:49` (`assert
   r.status_code == 200`). The document says exactly this and labels §5's byte
   equality "printed and observed, not asserted" rather than claiming otherwise.
   Confirmed by reading the file.

## Other citations spot-checked (not required by any result, all correct)

`_updates_html`'s two caps are at `updates[:3]` and `decode_photos(...)[:3]`
inside `:1271-1296`; the report handler at `public_projects.py:101` is declared
`def`, not `async def`, as §1.7 requires for its argument;
`anyio.to_thread.current_default_thread_limiter().total_tokens` is **40** on
**anyio 4.14.2** as installed, exactly as §1.7 publishes; `detail_json` has
exactly the **three** code reads §1.5 names (`project_report_service.py:1006`,
`:1060`, `:1248`, each a `decode_stage_detail(...)`);
`tests/test_public_project_report.py:356` contains
`test_the_thirty_first_request_inside_a_minute_is_still_a_200` as §5 cites.
Every file/line reference I checked — fifteen of them — resolved to what the
document says is there. Across the whole session, **not one** byte count,
statement count, slope, per-character sensitivity or line reference differed
from the published value by a single unit; the only figures that differed were
wall clocks and the ratios of wall clocks, which is precisely the split the
document's own closing lesson predicts.

## Blocking Findings

None.

## Suggestions

1. **§1.4's disclosed precondition has expired.** The document states "Nothing is
   listening on `localhost:5432`, `5433` or `55432` on this machine now, so the
   local development Postgres that produced it is down and the figure could not
   be taken again". As of this verification a Docker Postgres **is** listening on
   `*:5432` (`com.docke`, pid 43160). The 0.219 ms loopback anchor is therefore
   re-verifiable now by the exact procedure §1.4 names. This is not a defect —
   the document labels the figure unverified, calls it not load-bearing, and
   names what would settle it, which is the correct handling — but a reader
   following its instructions today will find the stated condition false. Worth a
   one-line note that the condition is as-of its measurement date.

2. **§1.3's 20-project split band is quotable without its precondition.** §1.3
   publishes "13.2-15.9% at 20 projects" and states the warm-arm-at-floor
   precondition for the 200-project band in the adjacent paragraph, but the
   20-project band's sentence does not carry it inline. My first run gave 23.8%
   with a warm arm at 9.28 ms (well above floor) — outside the published band, and
   correctly excluded by the precondition once applied. Attaching the precondition
   to the 20-project band as explicitly as it is attached to the 200-project one
   would close the last gap a reader could fall into. This is the document's own
   round-5 rule ("every claim must name the evidence that would check it") applied
   to one more sentence.

3. **§1.6's 89%/88% docstring discrepancy** is already assigned to Task B with a
   reason, which is the right disposition under R13. No action here.

## Worktree state on exit

Unchanged from how I found it: `git status --porcelain` in the worktree prints
exactly `A  docs/tasks/APRAS-93-spec.md`, the stash is empty, HEAD is `bc78696`.
Nothing was staged, unstaged, committed or pushed; no other worktree was
touched; `dev93/` is unmodified (my mutants live in the scratchpad above it).
`ps` confirms no CPU-hog process was left behind — `loadpair.sh` was run only
with `HOGS=0`, so none was ever spawned. Nothing was written to the Meridian
board.

VERDICT: APPROVED
