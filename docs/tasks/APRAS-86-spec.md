# APRAS-86 — Build the load-reproduction harness and fix the failures it reproduces

> **Rename proposed** (round 2). The original title, "Fix the timing-flaky
> invitation tests that fail only under load", names the one file this task does
> not repair. The original symptom is preserved in Scope below.

## Scope

Make the frontend suite's load-sensitive failures **reproducible on demand from a
committed artefact**, then repair the ones that are genuine test defects and
record, without fixing, the ones that are pure CPU starvation.

The reported symptom was a failure in
`frontend/src/features/user-administration/__tests__/TenantsAdminPage.invitations.test.tsx`
at a `findAllByRole`. Round 2 **reproduced it** (see Evidence 4). What the
capture rules out is a race: nothing resolved out of order (Evidence 5). What it
showed positively is CPU starvation — but "starvation, therefore nothing to fix"
claimed more than was measured, because a third lever, the poll's own cost, was
never measured against it (operator decision 2). The invitation file is
therefore hardened here for a defect of its own, and D3's three-point table is
what settles how much of the rate starvation actually owns.

Covers: a committed load harness at two pinned levels; the repair of the
duration-bound brand-palette tests; a render-order hardening in the invitation
file; a recorded red-before/green-after pair and a recorded unchanged baseline.

Does **not** cover: backend code or tests, Alembic revisions, the route registry,
CI workflow changes, any raising of any timeout, and any production component
change unless the report argues one was necessary (default: tests + scripts only).

## Evidence (measured; do not redo, extend)

HEAD `8a915d4`, Darwin arm64, **8 physical cores**, vitest 4.1.5, node 24.13.0.
Vitest 4 rejects `--poolOptions.*` and `--minWorkers`; the working spelling is
`--pool=threads --max-workers=N`.

1. **The double-wait hypothesis is dead.** Paren-matched scans by two agents
   agree: **0** nested `findBy*` in **519** `waitFor` bodies across 84 files.
   `@testing-library/dom/dist/query-helpers.js:83-90` shows `makeFindQuery` *is*
   `waitFor(() => getter(...))`, so the reported frame was the library's own.
2. **The side-car, not the vitest flags, selects the failure set.** Oversubscription
   alone on an idle machine is green.
3. **Level A — 12 hogs, 1 suite, 16 workers**: exactly one failure, 10/10 runs
   (reviewer) and 3/3 (generator):
   `TenantProfilePage.brand.test.tsx > … > sends the authored dark palette when the checkbox is cleared`,
   `Test timed out in 5000ms`.
4. **Level B — 24 hogs, 2 concurrent suites, trap-based cleanup.** Two
   independent samples of **6 suite instances each** (n=6; spec round 2, and
   review round 2 on the same commit and machine):

   | Test | spec | review |
   |---|---|---|
   | `brand > sends the authored dark palette when the checkbox is cleared` | 6/6 | 4/6 |
   | `brand > keeps the save enabled for a palette every pair of which clears AA` | 6/6 | 4/6 |
   | `Navbar.permissions > shows a morador exactly the links their permissions allow` | 6/6 | 4/6 |
   | `RoleMembersPanel > lists the role's members` | 4/6 | 2/6 |
   | `invitations > posts { tenant_id, email } from the row action…` | **3/6** | **3/6** |
   | `brand > sends the two colours as typed…` | 2/6 | 4/6 |
   | `invitations > sends the optional full name…` | 0/6 | 1/6 |
   | `invitations > opens the same dialog with the freshly created condominium…` | 0/6 | 1/6 |
   | `AcceptInvitationPage > refuses mismatched passwords` | 0/6 | 1/6 |

   **Read these as noisy, not as a property of the code.** Only the invitation
   rate agrees across samples; the others move by about ±2 of 6, and three tests
   appear in one sample and not the other at 1/6. At n=6 a rate is worth roughly
   ±2; membership at 1/6 is worth nothing at all. The one thing both samples do
   agree on is the originally reported failure, same test and same query.
5. **Its mechanism is now known, from the captured DOM.** At failure the page
   still reads `Carregando os condomínios...`; the stack is
   `wait-for.js:163 → query-helpers.js:86 → invitations.test.tsx:198`. The tenants
   query had not resolved inside **Testing Library's 1000 ms default**, a second
   and stricter deadline than vitest's 5000 ms that nobody chose. Nothing resolved
   out of order. There is no race in that file.

## The two categories, and why they are treated differently

- **Category A — the test does too much work.** `TenantProfilePage.brand.test.tsx`.
  `BRAND_AUTHORED_KEYS` has **13** entries (the array of that name in `src/api/tenantProfile.ts` — cited by symbol, since APRAS-88 is editing that file and will move the line numbers, though it does not touch this array); the
  failing test loops all 13 and adds `dark-primary` — **14 fields × 7 chars ≈ 98
  keystrokes**, each preceded by `user.clear`, each driven per-character by
  `userEvent.type`. The discriminator against its 13-field neighbour: with
  derive-dark cleared the page renders **26** hex inputs, not 13, so every one of
  those ~98 keystrokes re-renders roughly twice the tree — and `TenantBrandColors`
  (23,889 bytes) contains no `useMemo`, `useCallback` or `React.memo`, so
  `contrastRatio` recomputes across the palette on each change. Fields and
  cost-per-field both doubled, against a fixed 5000 ms `testTimeout`. **This is a
  real defect and is fixed here.**
- **Category B — the test is starved.** Invitation, `Navbar.permissions`,
  `RoleMembersPanel`, and — named here so it is not mistaken later for new
  breakage — `AcceptInvitationPage > refuses mismatched passwords`. Small tests
  whose mocked promise simply does not get CPU within Testing Library's 1000 ms.
  There is no *rendering* work to remove and no wait to re-order. Three levers
  remain: the machine's oversubscription, the library deadline — moving which is
  the prohibited timeout raise — and **the poll's own cost, which is work the
  test itself spends inside that deadline, and therefore work that can be
  removed. It is unmeasured, and if it moves the rate then "starvation" was
  never the whole account (see D3).** These are recorded as a baseline and their
  rates are not otherwise addressed here.

## Approach

**D1 — Commit the harness, including the load.** Add `frontend/scripts/load-test.sh`
(committed, executable) that owns the CPU side-car and the vitest invocation, with
`trap`-based cleanup on `EXIT INT TERM` collecting hog PIDs in an array — not
zsh `jobs -p`, which is empty in a non-interactive script and orphaned 12 `yes`
processes during review, poisoning a measurement set that had to be discarded. Two
pinned levels, both in the script, neither in prose:

- `npm run test:load` → **level A**: 12 hogs, 1 suite, `--pool=threads --max-workers=16`.
  This is the **gate**.
- `npm run test:load:max` → **level B**: 24 hogs, 2 concurrent suites. **Diagnostic
  only, never a gate** — at this level category-B starvation dominates and a green
  run measures the machine, not the diff.

Hog count, worker count and target path are literals in the script. The report
must state the machine's core count, since 12 hogs on 8 cores is not 12 hogs on 16.

**D2 — Fix category A, in the shared helper.** `typeHex`
(`TenantProfilePage.brand.test.tsx:160-170`, ~10 call sites) is where the work is.
Fix it there, not in the one test: the same three lines also repair
`keeps the save enabled for a palette every pair of which clears AA`, which is
6/6 red at level B, and every call site benefits. Try in this order and **record
which one was enough**:
1. `userEvent.setup({ delay: null })` at the file's setup sites. Smallest diff,
   preserves per-character semantics exactly (which the `#GGG` invalid-hex test at
   :378 depends on), and is not a timeout raise. Note `delay` is a v14 *setup*
   option, not a `type()` option.
2. If level A is not 10/10 green with (1), make `typeHex` enter the value in one
   shot (`fireEvent.change`), keeping the per-character path for the invalid-hex
   test.

**D3 — Harden the invitation file for its own defect, and measure what that does
to the flake rather than pre-judging it.** The deadline is provably identical
(`@testing-library/dom/dist/config.js:15` sets `asyncUtilTimeout: 1000`, read at
`wait-for.js:16`, and `frontend/src` calls `configure()` nowhere), so it is
tempting to conclude the scoping changes nothing. **That does not follow, and the
spec does not assert it.** Identical deadline is not identical outcome, because
**the poll's own cost competes with the render it is waiting for**: a
`findAllByRole` with a name option recomputes accessible names across the whole
document on every one of roughly twenty polls inside that second, while
`findByTestId` does one attribute match. That is a third lever, and it is
unmeasured. The spec's *prediction* is that the rate will not move; the
deliverable is the measurement, not the prediction. Make the change on its own
merits: `(await screen.findAllByRole("button", { name:
t("invitations.dialog.title") }))[0]` picks the assertion's subject by **render
order**, and twelve lines later the test asserts `toHaveBeenCalledWith({ tenant_id:
AURORA.id })`. If the page ever sorts differently that test goes green while
asserting about the wrong tenant. The button is inside `tenant-row-${tenant.id}`
(`TenantsAdminPage.tsx:432`, button at :459-466), so `within(await
screen.findByTestId(…))` needs no production change.

**Measure at three points, not two.** A two-point before/after cannot answer the
question it is asked, because one diff containing D2 and D3 confounds them: D2
removes ~98 keystrokes across 26 un-memoised re-rendering inputs at ~10 call
sites, and the brand file runs **in the same worker pool on the same eight cores**
as the invitation file at level B, whose failure mode is exactly "did not get CPU
within 1000 ms". Less contention from D2 lowers the invitation rate without D3
doing anything. So take the level-B table at:

1. **HEAD** — unmodified;
2. **HEAD + D2** — the `typeHex`/setup fix only;
3. **HEAD + D2 + D3** — the scoping added.

That is D2-then-D3, the order the work is already done in, so it costs no
reordering. **Only the (2)→(3) delta licenses any claim about poll cost.** The
(1)→(2) delta is a finding in its own right — it quantifies how much of one
file's flakiness is another file's CPU appetite — and must not be read as
evidence about D3. And note what a drop at (2) is *not*: a rate that falls
because contention fell is still starvation, merely less of it. The sentence
"category B was never purely starvation" may be written **only** if the (2)→(3)
delta carries it.

**D4 — Prohibitions a reviewer can grep for.** No `testTimeout` change; no
`timeout:` option added to any `waitFor`/`findBy*`; no `asyncUtilTimeout`; no
vitest positional per-test timeout in any spelling (`it("…", fn, 10000)`,
`it("…", namedFn, 10000)`, `}, 10_000);`, `}, TIMEOUT_MS);`); no `retry` in
config and no `--retry` on any command; and **no test or block silenced or
narrowed** — `it`/`test`/`describe` with `.skip`, `.todo` or `.only`, and the
`xit`/`xdescribe` spellings.

The silencing ban needs more than a grep, because a grep can be spelled around
and **a count cannot be**. Two counts are therefore pinned as results: the brand
file's **25** tests and the target directory's **483 tests across 50 files**
(both measured on HEAD `8a915d4`). Without them, `describe.skip` on the brand
file's `a condominium that already authored a palette` block would satisfy every
other result in this spec — a skipped test is not a failed one, it appears in no
failure list, and `vitest.config.ts:39-40` records 88.26 / 83.37 / 79.16 / 87.41
against thresholds of 80 / 78 / 76 / 80, so roughly 3.2 points of branch headroom
absorbs two or three skipped tests without tripping coverage.

Each hides the
mechanism and makes the eventual failure slower and less legible; in CI a spurious
red blocks a merge and a spurious green is worse.

**D5 — Proof: a pair, not a streak.** Ten greens alone are satisfiable by accident
at the wrong load — eight hogs passes on an unfixed tree. The bar is:
1. **Red before**: `test:load` on a stash-free clean checkout of HEAD, showing the
   named category-A test failing, output pasted.
2. **Green after**: ten consecutive `test:load` runs with the fix, each command
   line and result line pasted.
3. **Level-B three-point table**: `test:load:max` run over the same literal
   instance count (≥6) at each of HEAD, HEAD+D2 and HEAD+D2+D3, recorded as a
   per-test red count, not as a set. The **only failing condition** is that either
   category-A test still appears after the fix — that is attributable to the diff.
   Every other membership or rate change is **reportable, not failing**: at n=6 a
   rate carries about ±2 and a 1/6 appearance carries nothing, so a "the set must
   not grow" gate would block or wave through a developer on the weather. The
   thresholds that do earn a sentence of explanation are the ones pinned in
   expected result #4, which is their authoritative statement: a test newly at
   ≥4/6 after the fix, **or at ≥3/6 when it was 0 before** — 3/6 being the one
   rate that replicated exactly across two independent samples, so it is not
   noise. "Cannot rule it out" counts as failing.

**Files touched**
- `frontend/scripts/load-test.sh` — new; both levels, trap cleanup, pinned counts.
- `frontend/package.json` — `test:load` and `test:load:max` scripts.
- `frontend/src/features/user-administration/__tests__/TenantProfilePage.brand.test.tsx` — `typeHex` / `userEvent.setup` per D2.
- `frontend/src/features/user-administration/__tests__/TenantsAdminPage.invitations.test.tsx` — four `findAllByRole(...)[0]` lookups scoped to `tenant-row-${AURORA.id}`.
- `docs/tasks/APRAS-86-spec.md` — this file.

**Test criteria**: the red-before/green-after pair of D5; no assertion deleted or
weakened in either edited test file; `git diff --stat` shows nothing under
`frontend/src/**` outside `__tests__/`, nothing in `backend/**` or `alembic/**`.

## Expected Results

- [ ] `frontend/scripts/load-test.sh` exists, is executable, pins hog count and worker count as literals, cleans up its hogs through a `trap ... EXIT INT TERM` over collected PIDs, and offers two levels; `npm run test:load` and `npm run test:load:max` invoke it. No load parameter lives only in report prose.
- [ ] The report states the machine's core count and pastes, for the named category-A test, a **red** `test:load` result on unmodified HEAD and a **green** one after the fix.
- [ ] Ten consecutive `test:load` (level A) runs are recorded green, each with its command line and result line.
- [ ] The report carries a level-B **per-test red-count table at three points — HEAD, HEAD+D2, HEAD+D2+D3 — over the same stated instance count (≥6 each)**. Both `sends the authored dark palette when the checkbox is cleared` and `keeps the save enabled for a palette every pair of which clears AA` read 0 in the final column; that is the only failing condition. Other changes are observations, **except** a test newly at ≥4/6, or at ≥3/6 when it was 0 before (3/6 is the one rate that replicated exactly across two independent samples, so it is not noise): each gets a sentence saying whether the diff could plausibly have caused it, and "cannot rule it out" counts as failing.
- [ ] The report's mechanism sentence states the **deadline that was crossed and the work that crossed it** — for category A, vitest's 5000 ms `testTimeout` against ~98 per-character keystrokes over 14 fields while 26 un-memoised hex inputs re-render; for category B, Testing Library's 1000 ms default while the query was still pending (DOM showed `Carregando os condomínios...`). It must not describe either as an out-of-order await, because neither is.
- [ ] The report states the audit result — 0 nested `findBy*` in 519 `waitFor` bodies — and that the reported nesting was `makeFindQuery`'s own `waitFor` frame.
- [ ] The report names which of D2's two options was sufficient, with the measurement that decided it.
- [ ] The four `findAllByRole("button", { name: invitations.dialog.title })[0]` lookups in `TenantsAdminPage.invitations.test.tsx` are scoped to `tenant-row-${AURORA.id}` and the file still contains 16 passing tests. The report states the level-B red count of `posts { tenant_id, email }…` at all three points of result #4 and reads only the **(2)→(3)** delta as evidence about poll cost — it neither asserts an unmeasured no-effect result nor credits D3 with a drop that D2's reduced contention could explain. The report also states that the change's justification is render-order correctness, independent of whatever the rate does.
- [ ] Both commands below, run over **added lines only**, print nothing. The narrowing is deliberate: both edited files already contain `retry: false` (`invitations.test.tsx:148`, `brand.test.tsx:132`) — the *opposite* of the banned evasion — plus a prose "retry" at `invitations.test.tsx:597`, and all three must survive. Validated in round 4 against a synthetic diff carrying `describe.skip`, `test.skip`, `describe.only`, `it.only`, `xit`, `xdescribe`, `it("name", myNamedFn, 10000)`, `}, 10_000);`, `}, TIMEOUT_MS);`, `it.todo`, `configure({ asyncUtilTimeout })` and a multi-line `waitFor(…, { timeout: 4000 })`: all twelve flagged, and 0 false positives across the full text of both edited files.
  ```sh
  # Scoped to this task's own paths: APRAS-88 is live in this tree and its
  # lines must not be scanned. `grep '^+'` is a literal plus on purpose —
  # `^\+` is invalid in the basic-regex engine on this machine (ugrep).
  git diff -U0 -- frontend/src/features/user-administration/__tests__ \
                  frontend/scripts frontend/package.json | grep '^+' | grep -vE '^\+\+\+' | grep -nE \
    'testTimeout|asyncUtilTimeout|timeout[[:space:]]*:|retry[[:space:]]*:[[:space:]]*(true|[0-9])|--retry|\b(it|test|describe)\.(skip|todo|only)\b|\bx(it|describe)\b|\bconfigure\('
  # the positional per-test timeout, in every spelling: on the closing line, or
  # inline after a named function, with a numeric, separated or CONSTANT value.
  git diff -U0 -- frontend/src/features/user-administration/__tests__ \
                  frontend/scripts frontend/package.json | grep '^+' | grep -vE '^\+\+\+' | grep -nE \
    '^\+[[:space:]]*\}[[:space:]]*,[[:space:]]*([0-9_]+|[A-Z_][A-Z0-9_]*)[[:space:]]*\)[[:space:]]*;?[[:space:]]*$|^\+.*\b(it|test)(\.(each|concurrent))?\([^)]*,[[:space:]]*([0-9_]+|[A-Z_][A-Z0-9_]*)[[:space:]]*\)'
  ```
- [ ] **The counts are pinned, because a count cannot be spelled around.** `npx vitest run src/features/user-administration/__tests__/TenantProfilePage.brand.test.tsx` reports **25 passed (25)**, and `npx vitest run src/features/user-administration` reports **483 passed (483)** across **50** test files — both unchanged from HEAD `8a915d4`, both pasted into the report. A silenced `describe` passes every grep in this spec and every other result in it; only these two numbers catch it.
- [ ] `git diff --name-only` is confined to `frontend/src/**/__tests__/`, `frontend/scripts/`, `frontend/package.json` and `docs/**`; any exception is argued explicitly in the report.
- [ ] `npx tsc -b` clean; `npx vitest run --coverage` green at 80 lines / 78 functions / 76 branches / 80 statements; eslint re-measured on the touched files and repository-wide against the 375 errors + 2 warnings across 64 files baseline, with the new totals stated.

## Out of Scope

- **The category-B set** (`Navbar.permissions > shows a morador…`, `RoleMembersPanel > lists the role's members`, `invitations > posts { tenant_id, email }…`, `AcceptInvitationPage > refuses mismatched passwords`). Recorded by D5.3, not fixed. CI is not at risk today — `ubuntu-latest`, 2 vCPU, no pinned `maxWorkers`, so it never oversubscribes the way level B does. But the flake that created this task was seen in a **real** run, so "starvation, therefore not a defect" is too comfortable a conclusion to close on. The follow-up task inherits an open question, not a verdict: **does reducing the poll's own cost (D3's third lever) move the rate?** D3's three-point table (D5.3) is the first datum it gets, and only its (2)→(3) delta speaks to that question.
- Making `TenantBrandColors` cheaper to render (memoisation). A component that cannot be driven deterministically is arguably the real defect, but that is a production change and a separate task.
- Adding the harness to a CI workflow.

## Operator decisions taken while you were asleep (veto on waking)

1. **Rename**, per the title above: the old one names the only file not repaired.
2. **The invitation flake is diagnosed, not fixed** — it misses Testing Library's 1000 ms while the tenants query is still pending, under CPU starvation. Round 1 called it "unverified", which was one load notch early (Evidence 4-5); round 2 then called it starvation *with no work to remove*, which claimed more than was measured. What remains open is D3's third lever, the poll's own cost, and the three-point table is what settles it.
3. **The gate runs at level A, level B is diagnostic.** This is what reconciles "ten greens" with "other tests are red": at level B four or more tests in the harness's own target directory are reproducibly red for reasons this diff does not address, so a green bar there would be unreachable and a red one uninformative.
4. **The category-A fix goes in the shared `typeHex`/setup**, not in the one test, because it also clears a sibling that is 6/6 red at level B.
