# APRAS-127 — Reconcile frontend node_modules with package-lock.json

## The observed state, measured rather than quoted

Every figure below was measured on `4be622b` on 2026-10-10. The lockfile's
side was measured by installing `frontend/package.json` and
`frontend/package-lock.json`, byte-identical copies, into a scratch clone of
the repository — never into the real `frontend/node_modules`.

`frontend/node_modules` is not the tree `frontend/package-lock.json`
describes, and the gap is far wider than the two packages that exposed it:

| | real tree | after `npm ci` |
|---|---|---|
| non-optional lock entries compared | 335 (321 top-level, 14 nested) | 335 |
| version mismatches | **129** | **0** |
| non-optional top-level packages absent | **12** | **0** |
| non-optional nested packages absent | **7** | **0** |

Thirty of the **38** packages `package.json` declares directly are at the
wrong version. The major-version gaps among those 38 are six, and this
enumeration is complete: `eslint` 9.39.4 → 10.11.0, `@eslint/js` 9.39.4 →
10.0.1, `vitest` 4.1.11 → 5.0.3, `@vitest/coverage-v8` 4.1.11 → 5.0.3,
`jsdom` 29.1.1 → 30.1.1, `@types/node` 24.12.2 → 26.6.3. The installed tree
also *violates `package.json`'s own declared ranges*: the manifest asks for
`eslint: ^10.11.0` and 9.39.4 is installed.

Two consequences have each cost a review round. `npx eslint .` reports
**368 errors / 2 warnings over 64 files** on the installed version and
**370 / 2 over 66** on the lockfile's, and that discrepancy was quoted
inconsistently across specs and reviews for a week, with a wrong diagnosis
written into `docs/suggestions-log.md` before an APRAS-110 reviewer settled
it. And `tailwindcss` 4.2.4 nests the dark variant where 4.3.3 flattens it to
`:is(.dark *)` — confirmed here by compiling the same input through both
installed copies, and by the project's own built CSS under 4.3.3 containing
`dark\:border-amber-800:is(.dark *)`. APRAS-125's spec was written against the
installed shape and would have shipped a suite green locally and red in CI,
where `.github/workflows/ci.yml` installs with `npm ci`.

That second one is why this is not tidiness. A stale `node_modules` makes
local measurement disagree with CI in a way that reads as a code defect. The
drift arises from bots: the two most recent commits touching the lockfile are
dependabot PRs (`6aaa61c`, `d064fe8`), which update it on a branch while no
local reinstall ever follows.

## Scope

Covers: a single `npm ci` in `frontend/`; adoption of the eslint 10 findings
delta as the recorded baseline; a committed vitest guard that fails when an
installed version diverges from the lockfile, with its disk read under a
committed fixture-tree control; correction of the two falsified majors in
`AGENTS.md`'s frontend stack table plus the lint figure recorded beside the
command that re-derives it; and removal of one hardcoded Tailwind version
from a test's header comment.

Does not cover: editing `frontend/package.json` or
`frontend/package-lock.json` (see below — verified unnecessary); fixing or
suppressing any eslint finding, the two new ones included; reducing the 370-error
lint debt; adding a lint step to CI; `docs/suggestions-log.md`, whose wrong
diagnosis is corrected by this spec's own text and whose file is concurrently
modified by another task; the backend's `uv` pinning story; and any dependency
*upgrade* — the lockfile's versions are adopted exactly as committed, none chosen.

## Decisions

**1. Mechanism: `npm ci` in `frontend/`, and neither manifest is edited.**
`npm ci` deletes and reinstalls `node_modules` from the lockfile. It was run
here on byte-identical copies of both manifests and exited 0, which proves
the two files are already mutually consistent and that no `package.json`
range needs to move — `npm ci` refuses to run when they disagree, and every
locked version already satisfies its declared range. The eslint 9 → 10 major
is therefore **adopted, not chosen**: the lockfile already pins 10.11.0 and
CI already runs it. Both manifests must be byte-identical to `4be622b` when
the task lands.

**2. The eslint 10 delta is recorded as the new baseline, not fixed and not
suppressed.** The full JSON findings of both versions were diffed per file,
per rule and per line. Nothing disappears, no rule semantics change, flat
config loads identically, and the entire delta is two errors in two files:

- `src/features/user-administration/__tests__/TenantsAdminPage.invitations.test.tsx:517`
  — `no-useless-assignment`, a core rule newly enabled in eslint 10's
  `js.configs.recommended`: "The value assigned to 'panel' is not used in
  subsequent statements."
- `src/features/user-administration/context/SidebarContext.tsx:96`
  — `react-refresh/only-export-components`, from
  `eslint-plugin-react-refresh` 0.5.2 → 0.5.7 rather than from eslint itself:
  "Fast refresh only works when a file only exports components."

Neither is fixed here. The tree already carries 368 unfixed errors, `npm run
lint` is not a CI gate (the `frontend` job runs `npm run build` and `npm run
test:coverage` only), and fixing two of 370 while leaving 368 is arbitrary
scope. Suppression is worse: it hides two true findings. They become part of
the recorded figure and a follow-up task owns the debt.

**3. The guard is one vitest case, split into three parts so the disk read is
testable.** A new node-environment test under `frontend/src/__tests__/` reads
`frontend/package-lock.json` and, for every entry carrying a `version` and
not marked `optional`, compares it to the installed
`node_modules/<path>/package.json`.

It must be built as three separable pieces, because the middle one is where
this guard can silently lie:

- a reader of **locked** versions, from a lockfile path;
- a reader of **installed** versions that takes a **root directory as a
  parameter** and reads `<root>/<path>/package.json` off disk, returning
  either a version string or a distinct *absent* marker — never `undefined`
  in a position where a comparison could read it as agreement;
- a pure comparison that takes **both maps as parameters** and returns
  findings.

Two parameters, two reasons, and neither is generality for its own sake. The
root is the only way a committed test can point the installed-version reader
at something other than the real `node_modules`; a reader hard-wired to one
path cannot be negative-controlled at all, which is how a harness that
resolves versions out of the lockfile object it already holds would pass every
other check in this spec while reporting 0 mismatches on a tree that has 129.
And the locked map must be a parameter because §"Mutation proof"'s fixture
control has to restrict *both* sides to the fixture's packages — restricting
the root alone leaves 319 irrelevant absences in the result, which is worked
out there.

Deliberately left to the implementer: where the installed reader gets its set
of paths — iterating the locked map it is handed, or taking the paths
separately. Both are correct, and they are indistinguishable *because*
result 2 pins the observable findings exactly rather than the mechanism. That
is the general lesson of this spec's three review rounds, and it is worth
stating once: an assertion tight enough on behaviour makes the unstated
internals harmless, while an assertion loose on behaviour makes every
unstated internal a place for a vacuous check to hide.

The set is **every non-optional lockfile entry — 335 of them — derived, never
hand-listed**, because a hand-list goes stale exactly the way the lint figure
did, and because the measurement above shows the strict comparison is
*exactly* green after `npm ci` (0 mismatches, 0 absent) and *loudly* red
before (129 + 12). Three rules make that set safe, and each has a measured
reason:

- `optional` entries are skipped: all 51 absent after `npm ci` are optional
  platform binaries (`@rolldown/binding-*`, `@tailwindcss/oxide-*`), so
  including them would be red on every machine and would teach people to
  ignore the guard.
- A *top-level* entry (one `node_modules/` path segment, 321 of the 335) that
  is absent is a failure.
- A *nested* entry (14 of the 335) is compared only when present, because its
  path is a function of npm's hoisting, not of the lockfile, and a different
  npm major could relocate it while the version is still correct. **This
  leniency has a measured cost: 7 of the 14 are absent on the real tree
  today**, and the guard will not report them. That is accepted — all 7 are
  duplicate transitive copies (`lru-cache`, `magic-string`, `whatwg-url`,
  `lightningcss`, `hookified`) whose absence is the hoister's business, and
  the alternative is a guard red on machines whose npm hoists differently.
  Where a nested entry *is* present, its version is compared like any other.

**No separate CI step is added, but the guard does run in CI, and that is
accepted.** The honest statement, since the earlier draft of this spec got it
wrong: `.github/workflows/ci.yml` installs with `npm ci` (line 338) and then
runs `npm run test:coverage` (line 348), which is `vitest run --coverage`
over the whole suite — so a test file under `frontend/src/__tests__/` is
executed in CI unavoidably. In CI the parity assertion is green by
construction and therefore proves nothing there. It is kept rather than
excluded because the cost is negligible and an exclusion is a liability:
reading the non-optional entries costs **28–71 ms warm and 370–500 ms cold**,
against a CI frontend job whose median is 2.55 minutes. (An earlier draft of
this spec said 125 ms for 316 entries; 316 is the count *present today, before
the reinstall*, and in CI after `npm ci` all 335 are present. The conclusion
is unchanged under any of those numbers, which is why the figure is quoted as
a range rather than a point.) Meanwhile
an `exclude` rule or an env-gated skip is a second mechanism that can rot,
can be copied to tests that need it less, and would make the one place the
guard is *not* exercised the only place anyone looks at a red suite. So: the
guard's value is local, its CI execution is a priced no-op, and no
`describe.skipIf`, env guard or vitest `exclude` is added for it.

**4. Frontend-scoped, and it does not generalise to the backend.**
`backend/`'s `UV_PIN` (APRAS-121) guards the version of a *tool that
generates a committed artifact*, where the wrong tool version produces a
wrong committed `requirements.txt`. The frontend has no generated committed
artifact; its failure is a local cache silently lagging a committed lockfile,
and npm already ships the remedy. Unifying "pin a tool" with "detect a stale
cache" would be one mechanism for two unrelated problems. What is reused from
APRAS-121/122 is their *shape*: a single derived source of truth, a committed
test that fails on divergence, and a claim in `AGENTS.md` whose agreement with
that source is itself checked.

**5. Two stale majors in `AGENTS.md`, not one, and the check fails on silence.**
The frontend stack table holds two claims the lockfile falsifies, in adjacent
rows:

```
| Testing              | Vitest 4 + @testing-library/react + jsdom           |   (line 380; lock pins 5.0.3)
| Linting              | ESLint 9 + typescript-eslint                        |   (line 381; lock pins 10.11.0)
```

Both are corrected. Leaving one while fixing its neighbour would ship a known
falsehood from the very task that exists to end this drift. I audited the rest
of that table mechanically against the lockfile: `React 19`/19.3.0,
`Vite 8`/8.3.1, `Tailwind CSS 4`/4.3.3, `TanStack Query 5`/5.104.0,
`react-router-dom 7`/7.18.4 and `TypeScript ~6.0`/6.0.3 all agree. **These two
are the only stale rows**, so the task corrects exactly two and guards exactly
two.

Line 381 additionally carries the single command that re-derives the lint
figure, the figure with the commit it was measured on, the warning that it is
only valid after `npm ci`, and one sentence on the node-engine asymmetry
below.

The guard **derives** both majors from `package-lock.json` and compares them
to the prose — a comparison between two files, red the next time a bot bumps
either and nobody edits the table. Its contract must be stated precisely,
because the loose version of it is this repository's **first** vacuous check
verbatim (a text search on text that had moved):

- The **anchor** is the table row keyed by its first cell: the row whose
  leading cell is `Testing`, and the row whose leading cell is `Linting`,
  inside `AGENTS.md`'s frontend stack table. The check keys on the row label,
  not on the words `Vitest` or `ESLint` — it must survive a tool being renamed
  and must not survive the row disappearing.
- **The frontend table must be located before the row is**, and the guard must
  say how: `AGENTS.md` carries a *backend* stack table with its own `Testing`
  and `Linting` rows at lines 362–363, ahead of the frontend pair at 380–381,
  so a guard keyed on the row label alone can anchor on the wrong table. It
  must scope the search to the table under the `## Frontend` heading. A
  mis-anchored guard is loud rather than silent — the backend rows name pytest
  and Ruff, so no vitest or eslint major is found and the no-match failure
  fires — but it fires with the wrong diagnosis, and one clause here spares
  the implementer that round.
- **No match is a failure.** If a keyed row is missing, or present but stating
  no major for the tool, the check fails with a message naming the row label
  it looked for and saying the row was reworded or moved. Silence is not
  agreement, and a reworded table must break this task's own guard rather than
  quietly stop guarding.
- The two failure modes — *stated a different major* and *stated no major* —
  must be distinguishable in the failure message, because §"Mutation proof"
  requires a committed case asserting each one separately.

The *count* 370 is deliberately **not** asserted anywhere: a count assertion
over a 476-file lint run is red on every unrelated lint-affecting commit and
gets bumped reflexively, which is how the 368 figure went stale in the first
place. R2 asks for a re-derivation command, and the command is the answer.

**6. One hardcoded version is deleted rather than asserted.**
`frontend/src/__tests__/themeTokenCompile.test.ts` — the one suite that calls
Tailwind's `compile()`, and so the one most exposed to this drift — opens by
claiming "Tailwind 4.2.4's own `compile()`". It is rephrased to name the
version the lockfile pins without quoting a number, so there is nothing left
to go stale. No test asserts that comment: this repository has twice shipped a
guard satisfiable by comment prose in the file it asserts.

## Mutation proof, as acceptance criteria

The guard is worthless unless its failure path is demonstrated. An apparatus
of naming, floors and empty-input throws was shown here once to be satisfied
by a checker that returned `true` unconditionally, because none of it was a
negative control. So:

**The controls must cover the disk read, not only the comparison.** This is
the finding that rejected the first draft, and it is worth stating why,
because the first draft's controls looked adequate. They exercised only the
pure comparison. A harness whose installed-version lookup resolves each
version out of the lockfile object it already holds — the ordinary
copy-paste error — would satisfy a divergent-pair control, an absent-entry
control and an empty-input throw, and would still report **0 mismatches on
today's tree, which has 129**. The comparison was never the hard half.

So the committed suite must contain all of:

- **A fixture-tree control over the installed-version reader — the one that
  matters.** A small committed fixture directory under
  `frontend/src/__tests__/`, holding a miniature `node_modules/<pkg>/package.json`
  layout for three packages that are real non-optional lockfile entries: one
  whose fixture version is deliberately **wrong**, one whose fixture version
  **matches** the lockfile, and one **absent** from the fixture.

  **Both inputs must be restricted to those three packages, not just the
  root.** The comparison therefore takes the locked map as a parameter too,
  and this control passes it a map restricted to the three fixture packages —
  with each one's **real version read from the real `package-lock.json`**, so
  the mismatch's *locked* side still binds to this repository rather than to
  an invented number. Restricting only the root does not work and the figure
  is known: the guard derives **335** entries while the fixture holds three,
  so pointing the reader at the fixture with the full locked map yields
  **320 findings — 319 absences and 1 mismatch**, which satisfies "reports a
  failure naming the package" while burying the one finding that matters
  among 319 that do not.

  With both inputs restricted, the control asserts the findings are
  **exactly two and nothing else**: a mismatch on the wrong package whose
  reported *installed* value equals **the fixture's own version string**, and
  an absence on the missing one — with nothing reported for the matching
  package. Each clause kills a different bad harness, and these counts are
  measured against conformant and deliberately-broken readers, not reasoned:
  a conformant implementation produces exactly the **two**; a
  lockfile-resolving reader produces **zero**, because the same bug that
  reports the mismatching package as matching also hands the *absent* package
  a version out of the lockfile, so the absence disappears too; a reader that
  fails for the wrong reason produces **three**, carrying a placeholder such
  as `0.0.0-unknown` in place of the fixture's string. "Nothing else" is what
  stops the control being satisfied by a flood, and it is also what makes the
  missing-fixture case loud rather than silent: with no fixture root at all, a
  conformant reader produces **three** absences and the control is red.

- **The fixture must be tracked, and a bare `node_modules` rule prevents it.**
  `frontend/.gitignore:10` is a bare `node_modules`, which ignores any fixture
  path containing that segment — confirmed with `git check-ignore -v`, which
  names that line for
  `frontend/src/__tests__/fixtures/node_modules/eslint/package.json`.

  The fixture nevertheless **keeps the `node_modules` segment**, because it is
  required rather than incidental: the lockfile's keys *are*
  `node_modules/`-prefixed paths, including nested ones that carry the segment
  internally, and the reader resolves `<root>/<lock key>` verbatim. A fixture
  under a differently-named directory would force a path rewrite that the
  production run never performs, so the control would exercise a different
  path construction than the one it exists to protect.

  The ignore rule is therefore un-ignored for that one path, and **only the
  layered two-line form works**. Measured in a throwaway repository, by
  whether git discovers the file at all rather than by `check-ignore` alone:

  | `frontend/.gitignore` | discovered by `status -uall` / `ls-files --others` |
  |---|---|
  | `node_modules` | **no** |
  | `node_modules` + `!<path>/node_modules/**` | **no** — still ignored |
  | `node_modules` + `!<path>/node_modules/` + `!<path>/node_modules/**` | **yes** |

  The single-line negation fails because git does not descend into an excluded
  directory, so the directory itself must be un-ignored before a pattern
  inside it can match. Both lines are required.

  **That the fixture files are tracked is an asserted property**, by a
  committed case that resolves the fixture paths through git — `git ls-files
  --error-unmatch` on each, exit 0 — and **fails rather than skips** when git
  is unavailable. The reason is not that absence would be silent: with the
  exactness above, a fixture missing in CI makes the control red anyway, since
  all three packages read as absent instead of one mismatch and one absence.
  The reason is that it would be red with a *misdiagnosis* — a reader bug and
  an untracked fixture look identical in that failure — and this check turns
  the second one into a named failure that says the fixture is not committed.

  **`npm ci` does not disturb the fixture**, which matters because expected
  result 1 reinstalls while result 2 needs the fixture on disk. Verified: with
  the fixture planted under `frontend/src/__tests__/`, `npm ci` exits 0 and
  leaves it byte-identical. `npm ci` deletes and repopulates `frontend/node_modules`,
  not every directory that happens to carry that name, and the fixture is not
  on any module resolution path the build uses. So the two results do not
  interact and no ordering between them is required.
- **In-memory controls over the comparison.** A divergent pair must be
  *reported*, naming the package — asserting a rejection, never merely
  accepting a match; and an absent non-optional top-level entry must be
  reported as a failure, distinguishable from a mismatch.
- **Three controls over the `AGENTS.md` check**, matching decision 5's
  contract, with the markdown text supplied as an input so no fixture file is
  needed: prose stating a *different* major fails; prose whose keyed row is
  *missing or reworded* fails, and the case asserts it is the **no-match**
  failure rather than the disagreement one; prose stating the lockfile's
  majors passes.
- **An empty-set throw.** The guard throws when its derived set of lockfile
  entries is empty, so a broken predicate is loud rather than vacuously green.
- **End-to-end mutation, by hand, once, in a throwaway copy.** Copy
  `frontend/` to a scratch directory, `npm ci` there, overwrite one installed
  package's `version`, confirm the divergence took effect by printing it back,
  confirm the guard goes red and names that package, restore, re-run, confirm
  green. Commands and output go in the QA notes. **Never in the real
  `frontend/node_modules`.**

**Deliberately not required: a "compared count equals the lockfile's count"
assertion.** The first draft asked for one. Both of its sides are produced
from `package-lock.json` by the same predicate, which makes it
`assert len(x) == len(x)` — unfailable, inside the spec whose subject is
checks that cannot fail. Its only non-tautological reading, counting entries
actually compared, contradicts decision 3's nested leniency and would fire on
the 7 nested absences that exist right now. The fixture-tree control is the
anti-vacuity device; a count is not.

## One asymmetry the reconciliation introduces, recorded not fixed

`npm ci` prints `EBADENGINE` for `jsdom` 30.1.1, which requires node
`^22.22.2 || ^24.15.0 || >=26.0.0`; local node is **v24.13.0**, while CI's
`node-version: 24` resolves to a 24.x that satisfies it. The suite is green
anyway — measured, 198/2594 under the lockfile's versions on v24.13.0 — so
nothing is broken, but this is a *fresh* local/CI divergence of the same
family the task exists to remove, created by the task itself. It is recorded
in one sentence in `AGENTS.md` beside the re-derivation command rather than
fixed here: raising the local node is an operator action on a machine, not a
repository change, and no expected result depends on it.

## Files touched

- `frontend/node_modules/` — reinstalled by `npm ci`; not tracked.
- `frontend/src/__tests__/` — one new test file: the locked-version reader,
  the root-parameterised installed-version reader, the pure comparison, the
  `AGENTS.md` major check, and the controls above.
- `frontend/src/__tests__/` fixture directory — the three-package miniature
  `node_modules` layout the disk-read control points at, which must end up
  **tracked**.
- `frontend/.gitignore` — the two-line layered negation that un-ignores that
  one fixture path, and nothing broader.
- `AGENTS.md` — the `Testing` and `Linting` rows corrected, the re-derivation
  command, the lint figure with its provenance commit, and the node-engine
  sentence.
- `frontend/src/__tests__/themeTokenCompile.test.ts` — header comment only,
  hardcoded `4.2.4` removed.

Nothing else. `frontend/package.json` and `frontend/package-lock.json` are
read, never written.

## Test criteria

All three of `npm run build`, `npx vitest run` and `npm run test:coverage`
were measured green under the lockfile's versions before this spec was
written — 198 files / 2594 tests, coverage 91.64% — so a failure in any of
them is a real regression and not an expected cost of the bump.

Those absolute figures are provenance, not the asserted property. The
**asserted** property is the *delta across the reinstall on the
implementation's own tree*: the implementer runs the suite and
`npx eslint . -f json` **before** `npm ci` and again after, on the same tree,
and records both. This matters because thirteen unpushed commits and several
live tasks sit in this checkout, so a hardcoded `2594` or `370` turns a
correct implementation red when an unrelated test file lands first. The
before/after pair is immune to that: whatever the counts are, the suite must
not lose a passing file, and the lint run must gain exactly the two named
findings and lose none. The new guard must be green on the reconciled tree
and red on every control above.

## Expected Results

- [ ] After `cd frontend && npm ci`, the new guard reports 0 version
      mismatches and 0 absent non-optional top-level packages over all 335
      non-optional `package-lock.json` entries, with `tailwindcss` at `4.3.3`
      and `eslint` at `10.11.0`.
- [ ] Pointed at the on-disk fixture tree with the locked map restricted to
      the same three packages, the guard reports **exactly two findings and
      nothing else**: a mismatch carrying **the fixture's own version string**
      as the installed value, and the absent package.
- [ ] The fixture files are tracked by git — `frontend/.gitignore` carries
      both the directory and the `/**` negation, `git check-ignore` reports
      the fixture path as not ignored, and a committed case fails (never
      skips) if they are untracked.
- [ ] The `AGENTS.md` major check fails both when a keyed row states a
      different major and when that row is missing or reworded, with the two
      failures distinguishable, and passes only on the lockfile's majors.
- [ ] `npm run build`, `npx vitest run` and `npm run test:coverage` all exit
      0 on the reconciled tree, with no test file failing that passed on the
      same tree before the reinstall.
- [ ] `npx eslint . -f json` on the reconciled tree gains exactly
      `no-useless-assignment` at `TenantsAdminPage.invitations.test.tsx:517`
      and `react-refresh/only-export-components` at `SidebarContext.tsx:96`
      against the same tree before the reinstall, and loses no finding.
- [ ] `AGENTS.md` states the `vitest` and `eslint` majors the lockfile pins
      (5 and 10), the command that re-derives the lint figure with its
      provenance commit, and the node-engine asymmetry.
- [ ] `frontend/package.json` and `frontend/package-lock.json` are
      byte-identical to `4be622b`, and the QA notes record the end-to-end
      mutation run in a throwaway copy — divergence confirmed in place, guard
      red naming that package, restore, guard green.

## Out of Scope

Fixing the 370 lint errors or the two new ones; a CI lint step; any
dependency upgrade beyond what the lockfile already pins; generalising the
guard to the backend; `docs/suggestions-log.md`.

No HTML mockup accompanies this task: it ships nothing visible and poses no
visual question.
