# APRAS-127 — spec review, round 1

Spec under review: `docs/tasks/APRAS-127-spec.md` (233 lines, untracked).
Reviewed against local `master` = `4be622b`. Everything below was measured,
not quoted. My probes live in
`/private/tmp/claude-501/-Users-heitor-workspace-apras/06230b8a-d0ef-40dd-929b-83bb4eb6abbf/scratchpad/reviewer-127/`.

## What I verified, and how

### The author's central claim is correct in every digit

I wrote my own derivation (`reviewer-127/derive.py`) rather than reading the
author's logs: it parses `frontend/package-lock.json`, filters entries that
carry a `version` and are not `optional`, and reads
`<root>/<lock path>/package.json` for each, against both the real tree and the
author's `npm ci`-ed scratch clone.

| | real tree | scratch after `npm ci` | spec says |
|---|---|---|---|
| non-optional lock entries with a version | 335 | 335 | 335 ✓ |
| version mismatches | 129 | 0 | 129 / 0 ✓ |
| non-optional **top-level** absent | 12 | 0 | 12 / 0 ✓ |
| non-optional **nested** absent | 7 | 0 | not stated |
| optional entries absent | 52 | 51 | 51 ✓ |

321 of the 335 are top-level, 14 nested — matching the spec's decision 3
exactly. 38 direct dependencies are declared; **30 are at the wrong version**
in the real tree, as claimed.

I confirmed both manifests in the scratch clone are byte-identical to the real
ones (`diff -q`, rc=0), and that the scratch's `frontend/` tree excluding
`node_modules` is byte-identical to the repository's (`diff -rq`, empty), as
is `backend/tests/data` and `AGENTS.md`. So a measurement taken there is a
measurement of this repository's sources under the lockfile's versions. That
mattered: the author's own `test10.log` and `test10b.log` show 6 failing files
caused by the scratch clone initially missing out-of-`frontend` fixtures
imported with `?raw`, not by the version bump. I did not take the final log on
trust.

### The behavioural claims hold — I re-ran all three myself

In the scratch clone (never the real `node_modules`):

- `npx vitest run` → **`Test Files 198 passed (198)` / `Tests 2594 passed
  (2594)`, exit 0**. Crossing a vitest major (4.1.11 → 5.0.3) and a jsdom
  major (29.1.1 → 30.1.1) with zero test changes is surprising, and it is
  nonetheless what happens.
- `npm run build` → **exit 0** (vite 8.3.1, 2299 modules).
- `npm run test:coverage` → **exit 0**, `All files | 91.64 | 85.52 | 87.91 |
  92.35`. The 91.64% figure is exact.

### The eslint delta is exactly as described

I re-ran `npx eslint . -f json` on both trees and diffed the findings as a set
of `(file, ruleId, line, severity)` tuples:

```
eslint 9 (installed): errors=368 warnings=2 filesWithFindings=64 totalFilesLinted=476
eslint 10 (lockfile): errors=370 warnings=2 filesWithFindings=66 totalFilesLinted=476

only in 10 (new):
  + ('src/features/user-administration/__tests__/TenantsAdminPage.invitations.test.tsx', 'no-useless-assignment', 517, 2)
  + ('src/features/user-administration/context/SidebarContext.tsx', 'react-refresh/only-export-components', 96, 2)
only in 9 (disappeared):
  (none)
```

368/2/64 versus 370/2/66, nothing disappears, and the entire delta is the two
findings at the two lines the spec names. Verified.

### The mechanism reasoning is sound

`frontend/package.json` asks `eslint: ^10.11.0`, `vitest: ^5.0.3`,
`jsdom: ^30.1.1`, `@vitest/coverage-v8: ^5.0.3`. So the installed tree really
does violate the manifest's own ranges, as the spec says. `npm ci` exited 0 on
byte-identical copies (`added 340 packages`), and `npm ci` does refuse when
`package.json` and the lockfile are out of sync — so the spec's inference that
no range needs to move, and that eslint 10 is *adopted* rather than chosen, is
correct. Decision 1 is approved.

### The two folded-in findings check out

`frontend/src/__tests__/themeTokenCompile.test.ts:12` reads "What is available
is Tailwind 4.2.4's own `compile()`", and that is the only occurrence of
`4.2.4` anywhere under `frontend/src` or in `AGENTS.md`. Deleting the number
rather than asserting it is the right call in a repository that has twice
shipped a guard satisfiable by comment prose in its own asserted file.

The Tailwind shape claim is real: the 4.3.3 build I produced contains
`dark\:border-amber-800:is(.dark *)` — the flattened form. APRAS-125's guard
written against the nested 4.2.4 shape would indeed have been green locally
and red in CI.

### Decisions I rule in the author's favour

- **Decision 2 (record the eslint delta, do not fix or suppress).** Approved.
  Fixing 2 of 370 while 368 stand is arbitrary scope, `npm run lint` is
  genuinely not a CI gate (`ci.yml` runs only `npm run build` and
  `npm run test:coverage`), and suppression would hide two true findings.
- **Decision 4 (no backend generalisation).** Approved, and the distinction
  drawn is the right one: `UV_PIN` guards the version of a tool that produces
  a committed artifact; here there is no generated artifact, only a cache
  lagging a committed lockfile, for which `npm ci` is already the remedy.
  Reusing APRAS-121/122's *shape* rather than its mechanism is correct.
- **Not asserting the count 370 anywhere.** This is the judgement call the
  brief flagged, and I agree with the author. A count assertion over a 476-file
  lint run goes red on commits that have nothing to do with it and gets bumped
  reflexively; that is demonstrably how 368 went stale. The command that
  re-derives it, plus the provenance commit, is the durable form. The one-time
  measurement belongs in QA (expected result 5), which is where the spec puts
  it.
- **Deriving the set of 335 rather than hand-listing it.** Approved, and
  measured to be exactly green after `npm ci` and loudly red before (129 + 12).
  This is not over-engineering: a hand-list is the failure mode the spec is
  trying to end.

## Scope

Single PR-sized: one `npm ci`, one new test file, one `AGENTS.md` table row,
one header comment. Not a split candidate. No YAGNI problem — nothing in the
spec is built for a future caller.

## Blocking findings

### 1. The negative control covers the pure function but not the disk read, and that leaves a concrete path by which the guard passes while the property fails

The brief asked me to say concretely whether such a path exists. It does.

The spec's committed controls are: an exported pure comparison function over
(locked versions, installed versions) fed a divergent pair; a case for a
reported-absent top-level entry; a throw on empty input; and a compared-count
assertion. Every one of those exercises the *comparison*. None exercises the
*acquisition* of the installed-version map.

So consider a harness whose installed-version lookup is wrong in the ordinary
copy-paste way — it resolves each entry's version out of the lockfile object it
already has in hand instead of reading `node_modules/<path>/package.json` off
disk. Then:

- the pure function is correct, so both negative controls pass;
- the derived set is 335 entries, so the empty-input throw does not fire;
- the compared count is 335, so that assertion passes;
- and the guard reports 0 mismatches **on today's real tree, which has 129**.

Green guard, false property, every stated control satisfied. This is APRAS-125's
lesson re-instantiated one layer up: the apparatus is a negative control for the
half of the guard that was already easy to get right.

The spec's second mutation bullet — the by-hand end-to-end run in a throwaway
copy — *does* catch this, because a lockfile-reading harness stays green when an
installed `version` is overwritten on disk. But that run is performed once, by
hand, and recorded in QA notes; it commits nothing. The committed suite
therefore carries no defence of the disk-read path, and a later refactor
reintroduces the bug silently.

The fix is cheap and must be specified: make the installed-version reader take a
root directory as a parameter, and commit a case that points it at a small
on-disk fixture tree whose `package.json` holds a known-wrong version, asserting
the guard reports a failure naming that package. That puts the disk read itself
under a committed negative control.

### 2. The "compared count" vacuity control is either a tautology or a contradiction of decision 3

The spec requires the test to assert "the compared count equals the lockfile's
own count of non-optional entries — derived from the lockfile, not hardcoded."
Both sides of that comparison are produced from `package-lock.json` by the same
predicate (`has version` and `not optional`), which makes it
`assert len(x) == len(x)` — a check that cannot fail, in the spec whose whole
subject is checks that cannot fail.

The only reading under which it is not a tautology is that "compared count"
means entries actually version-compared, i.e. excluding nested entries skipped
as absent. But decision 3 deliberately tolerates exactly those skips ("a nested
entry is compared only when present, because its path is a function of npm's
hoisting"), so under that reading the assertion fires precisely in the scenario
the leniency exists for. It happens to pass today only because all 14 nested
entries are present after `npm ci` (I measured 0 nested absent in the scratch
tree) — and 7 of them are absent in the real tree right now, so the situation is
not hypothetical.

An implementer can satisfy this sentence two incompatible ways. The spec must
define "compared count", and either give it an anchor that is not the same
derivation from the same file, or drop it and say that the negative control is
the anti-vacuity device (which, once finding 1 is addressed, it is).

### 3. Decision 3's refusal to add a CI step is contradicted by where the guard is placed

Decision 3 argues at length that no CI step is added because CI installs with
`npm ci`, so a CI assertion of parity would be "green by tautology — the eighth
vacuous check in a repository that already has seven."

But `.github/workflows/ci.yml:338-348` runs `npm ci`, then `npm run build`,
then `npm run test:coverage`, and `test:coverage` is `vitest run --coverage`
over the whole suite. A new test file under `frontend/src/__tests__/` is
therefore executed in CI unavoidably. The spec does not add a CI *step*; it
nonetheless ships the tautologically-green CI assertion it says it is refusing,
and additionally makes every CI run open 335 `package.json` files.

I am not asking for the guard to be moved — the local value is real and the CI
cost is trivial. I am asking the spec to stop making an argument its own
implementation does not deliver, because an implementer reading decision 3
literally has to choose whether to exclude the file from the CI run
(`exclude` in the vitest config, an env guard, a `describe.skipIf`) or not, and
those are two different deliverables. State explicitly that the guard runs
inside the existing CI suite and that this is accepted as a harmless no-op, or
specify the exclusion.

### 4. `AGENTS.md:380` asserts "Vitest 4", which the same lockfile falsifies, and the spec leaves it stale while fixing its neighbour

The spec's premise for decision 5 is that `AGENTS.md:381` ("ESLint 9 +
typescript-eslint") states a major the lockfile contradicts. The line
immediately above it says:

```
| Testing              | Vitest 4 + @testing-library/react + jsdom           |
```

The lockfile pins `vitest` at **5.0.3**. This is the same file, the same table,
the same drift, and the same class of error — and the spec edits line 381 while
leaving line 380 holding a known-false claim. The guard already derives one
major from `package-lock.json`; deriving two is the same code path and the same
assertion. Either correct and guard both, or state in Does-not-cover why a
falsehood the task demonstrably knows about is being left in the file it is
correcting.

(I checked the neighbours: `Vite 8` matches 8.3.1 and `Tailwind CSS 4` matches
4.3.3, so these two rows are the only stale majors.)

### 5. The `AGENTS.md` major check has no defined behaviour when the prose matches nothing

The claim the guard checks lives in a markdown table cell —
`| Linting              | ESLint 9 + typescript-eslint                        |`
— with no machine-readable anchor and no delimiter. The spec says the guard
"fails if `AGENTS.md` states a different one", and is silent on the case where
`AGENTS.md` states *no* major because the row was reworded, the table became a
list, or the section moved. Under the natural implementation (regex for
`ESLint (\d+)`, compare when found) a no-match yields nothing to compare and
the test passes.

That is, verbatim, the first of this repository's seven vacuous checks: a text
search on text that had moved. The spec must require that absence of a match is
itself a failure, name the anchor the guard keys on, and put this check under a
committed negative control of its own — the existing two controls cover only the
version-pair comparison, and expected result 6 ("fails when `AGENTS.md`
disagrees") does not reach silence, because silence is not disagreement.

## Suggestions (non-blocking)

1. **"Four major-version gaps" is six.** My derivation finds, among the 30
   wrong direct dependencies, these major gaps: `eslint` 9.39.4 → 10.11.0,
   `vitest` 4.1.11 → 5.0.3, `@vitest/coverage-v8` 4.1.11 → 5.0.3, `jsdom`
   29.1.1 → 30.1.1, and additionally **`@eslint/js` 9.39.4 → 10.0.1** and
   **`@types/node` 24.12.2 → 26.6.3**. In a spec whose opening promise is
   "measured rather than quoted", the enumeration should be complete or
   explicitly partial.
2. **Report the 7 absent nested entries too.** The real tree has 12 absent
   top-level *and* 7 absent non-optional nested entries. The spec's table omits
   the latter, and the guard will not report them by design. Stating the number
   makes the leniency's cost explicit instead of invisible.
3. **Expected results 4 and 5 hardcode figures that drift under concurrent
   work.** `198 files / 2594 tests` and `370 / 2 / 66` are exact today (I
   measured both), but thirteen unpushed commits and several live tasks sit in
   this checkout; a single test file or lint-affecting change landing before QA
   runs turns a correct implementation red. The durable claim in result 5 is the
   *delta* — the two named findings and nothing disappearing — so consider
   phrasing both results against the implementation tree with the delta as the
   asserted part, as decision 5 already argues for the count.
4. **`npm ci` emits `EBADENGINE` for jsdom 30 on this machine.** jsdom 30.1.1
   requires node `^22.22.2 || ^24.15.0 || >=26.0.0`; local node is **v24.13.0**.
   The suite is green anyway (I ran it), so nothing is broken, but the
   reconciliation introduces a fresh local/CI asymmetry — CI pins
   `node-version: 24`, which resolves to a 24.x that satisfies the range, while
   the local tree does not. That is the same class of divergence this task
   exists to remove, and it is worth one sentence in `AGENTS.md` beside the
   re-derivation command.

## Things I could not verify

None. Every quantitative claim in the spec was re-derived or re-run here. The
real `frontend/node_modules` was never installed into: after my probes,
`git status --porcelain frontend/` is empty, no `.eslintcache` was created, and
`frontend/node_modules/eslint` is still 9.39.4.

VERDICT: REJECTED

1. The committed negative controls cover the pure comparison function but not
   the acquisition of installed versions from disk, leaving a concrete path —
   a harness that resolves versions out of the lockfile instead of
   `node_modules` — on which every stated control passes while the guard
   reports 0 mismatches on a tree that has 129. Require a committed case that
   points the reader at an on-disk fixture tree holding a known-wrong version
   and asserts a failure naming that package.
2. The "compared count equals the lockfile's own count of non-optional
   entries" control compares two results of the same predicate over the same
   file, making it unfailable; the only non-tautological reading contradicts
   decision 3's deliberate tolerance of absent nested entries, 7 of which
   exist in the real tree today. Define "compared count" and give it an
   independent anchor, or drop it.
3. Decision 3 refuses a CI step on the ground that CI parity is green by
   tautology, but `ci.yml:338-348` runs `npm ci` then `npm run test:coverage`
   over the whole suite, so a test under `frontend/src/__tests__/` ships that
   tautology anyway. State that the guard runs in the existing CI suite and is
   accepted as a no-op there, or specify the exclusion.
4. `AGENTS.md:380` claims "Vitest 4" where the lockfile pins 5.0.3 — the same
   file, table, and drift the spec exists to correct one line below. Correct
   and guard both majors, or state why a known falsehood is being left behind.
5. The `AGENTS.md` major check is undefined when the prose matches no pattern:
   the claim sits in an unanchored markdown table cell, and a reworded row
   leaves nothing to compare, so the guard passes. Require no-match to fail,
   name the anchor, and negative-control this check too — expected result 6's
   "disagrees" does not cover silence.
