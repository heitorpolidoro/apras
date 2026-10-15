# APRAS-127 — spec review, round 2 (findings-only)

Spec: `docs/tasks/APRAS-127-spec.md`, 367 lines, untracked. Base `4be622b`.
Scope of this round: verify round 1's five blocking findings are resolved, plus
a consistency pass over the sections the author changed. I re-ran the probes
that carry weight rather than accepting the new numbers. Probes in
`.../scratchpad/reviewer-127/`.

## Round 1's five findings

### Finding 1 — resolved structurally, and I confirmed the clause closes the path

I rebuilt the three pieces exactly as decision 3 specifies (locked reader;
installed reader with root as a parameter; pure comparison), plus two bad
harnesses, and pointed them at a three-package fixture holding `eslint` at a
deliberately wrong `9.39.4` (lock pins `10.11.0`), `axios` at a matching
`1.20.0`, and no `jsdom` (`reviewer-127/guard.mjs`). Over a locked map
restricted to those three:

```
correct reader   -> [{mismatch eslint locked 10.11.0 installed 9.39.4}, {absent jsdom}]
LOCKFILE-BUG     -> []                      <= 0 findings: control CATCHES it
MISREPORT reader -> [{mismatch eslint installed "0.0.0-unknown"},
                     {mismatch axios  installed "0.0.0-unknown"}, {absent jsdom}]
fixture's own eslint version on disk: 9.39.4
```

Both halves of the load-bearing clause bite, measured:

- The harness I described in round 1 — installed versions resolved out of the
  lockfile object already in hand — produces **0 findings** at the fixture root
  and so fails "exactly one mismatch and one absence". **My path is closed.**
- The "fails for the wrong reason" half is not decorative either: a reader that
  genuinely touches disk but reports a placeholder version fails both the count
  (2 mismatches, not 1) *and* the clause requiring the reported installed value
  to equal the fixture's own string (`0.0.0-unknown` ≠ `9.39.4`).

Making the root parameter a *specification* requirement, so that a hard-wired
reader is unspecifiable rather than merely untested, is the right structural
move and not gratuitous generality — I demonstrated it is the only way a
committed test reaches the disk-read path.

Two defects remain *inside* this fix; they are the two blocking findings below.

### Finding 2 — resolved

The count assertion is gone, and the reasoning is preserved under
"Deliberately not required" with both the tautology and the
nested-leniency-contradiction stated, so the next reader does not re-add it.
The empty-set throw stays, correctly scoped to "a broken predicate is loud".
The fixture control is named as the anti-vacuity device, which — per the probe
above — it now actually is.

### Finding 3 — resolved, and the call is right

The citations are correct: `ci.yml:338` is `npm ci`, `ci.yml:348` is
`npm run test:coverage`, which is `vitest run --coverage` over the whole suite,
so the guard runs in CI unavoidably. The spec now says so plainly, says the
earlier draft got it wrong, and states that in CI the assertion proves nothing.
That is the honesty the finding asked for.

I priced the decision myself (`reviewer-127/cost.mjs`, node, three runs per
tree): reading all 335 entries takes **28–71 ms warm** and **370–500 ms on a
cold cache**. So the author's 125 ms is the right order of magnitude, and under
*any* of these numbers the cost against a 2.55-minute job is noise. **I rule
for keeping it in the suite.** An `exclude` rule or env-gated skip is a second
mechanism with its own rot surface, and the author's sharper argument is the
decisive one: an exclusion would make the one place the guard is not exercised
the only place anyone reads a red suite. There is also a benefit the spec
undersells — the CI run is the only thing that keeps the guard from bit-rotting
into a file nobody executes.

(Nit, not blocking: the 125 ms is attributed to "the 316 present entries", which
is the *pre*-reinstall count — I measured 316 present on the real tree and 335
on the reconciled one. In CI, after `npm ci`, all 335 are present. Give the
figure with its cache state, or as an order of magnitude.)

### Finding 4 — resolved, and I re-ran the audit

Both rows corrected and both guarded by the same code path. I re-derived the
whole frontend stack table against the lockfile rather than spot-checking:

```
react              lock=19.3.0    AGENTS "19"    agrees
vite               lock=8.3.1     AGENTS "8"     agrees
tailwindcss        lock=4.3.3     AGENTS "4"     agrees
@tanstack/..query  lock=5.104.0   AGENTS "5"     agrees
react-router-dom   lock=7.18.4    AGENTS "7"     agrees
typescript         lock=6.0.3     AGENTS "~6.0"  agrees
vitest             lock=5.0.3     AGENTS "4"     STALE
eslint             lock=10.11.0   AGENTS "9"     STALE
```

`Testing` and `Linting` are indeed the only stale rows. Recording that in the
spec so the audit need not be repeated is good practice.

### Finding 5 — resolved

Keying on the row label rather than on `Vitest`/`ESLint` is the correct anchor
choice: it survives a tool rename and does not survive the row vanishing, which
is exactly the asymmetry the finding was about. No-match is now a failure with
a message naming the label it looked for; the two failure modes are required to
be distinguishable; and there is a committed control asserting the **no-match**
mode specifically. That closes "disagrees never covered silence". See the
suggestion about duplicate row labels, which does not reopen it.

## New surface the author added, verified

- **The 7 absent nested entries, enumerated — exact.** My derivation returns
  precisely those seven paths: `@asamuzakjp/css-color/node_modules/lru-cache`,
  `@asamuzakjp/dom-selector/node_modules/lru-cache`,
  `@vitest/mocker/node_modules/magic-string`,
  `vitest/node_modules/magic-string`, `jsdom/node_modules/whatwg-url`,
  `vite/node_modules/lightningcss`, `qified/node_modules/hookified`. All seven
  are duplicate transitive copies, so the characterisation and the acceptance
  of the leniency's cost are both accurate. 335 = 321 top-level + 14 nested
  confirmed; 12 top-level absent confirmed.
- **Six majors, complete.** `@eslint/js` 9.39.4 → 10.0.1 and `@types/node`
  24.12.2 → 26.6.3 are the two that were missing; my round-1 enumeration finds
  exactly six and no seventh.
- **The `EBADENGINE` asymmetry — record-not-fix is acceptable, and does not
  block the reconciliation.** Confirmed: jsdom 30.1.1 declares
  `^22.22.2 || ^24.15.0 || >=26.0.0`, local node is v24.13.0, CI pins
  `node-version: 24`. The question is whether a documented divergence is
  enough, and the evidence says yes: I ran the full suite on this machine at
  v24.13.0 under the lockfile's versions and got 198 files / 2594 tests green
  with coverage exiting 0 at 91.64%. The engine range is a declaration, not a
  gate, and nothing in the seven results depends on it. Raising local node is
  an operator action on a machine, so a repository change could not fix it
  anyway. Giving it its own section rather than burying it is the right
  handling.
- **Results 4 and 5 as a before/after delta — an improvement, and more
  verifiable, not less.** The absolute figures were the fragile part given
  thirteen unpushed commits in this checkout; the delta (no passing file lost;
  exactly the two named findings gained, none lost) is both durable and
  mechanically checkable from the recorded pair. Demoting 198/2594/370 to
  provenance is correct.

## Blocking findings

### 1. The fixture control's locked set is unspecified, and under the spec's literal wording the control is unsatisfiable

§"Mutation proof" says "The guard, pointed at that root, must report exactly one
mismatch and one absence", and expected result 2 repeats it. But the guard
derives its set from the real lockfile — 335 entries — while the fixture holds
three packages, so 332 entries are missing from the fixture root. I measured
exactly this with the spec-conformant pieces:

```
### Reading A: 'the guard, pointed at that root' with its REAL 335-entry set
   total findings: 320  | of which absent: 319  mismatch: 1
```

320 findings, not "exactly one mismatch and one absence". The control only
behaves as described when the *locked map is also restricted* to the three
fixture packages (my Reading B, which produces exactly the two findings the
spec wants) — and the spec never says that. Decision 3 parameterises only the
**root**; the reader's stated contract reads `<root>/<path>/package.json` with
no statement of where the path set comes from, so nothing in the spec makes the
restriction visible.

This matters beyond pedantry for two reasons. The seven results are the
contract QA judges against, and result 2 as written says the guard "reports the
deliberately-wrong package ... plus the absent package, and reports nothing for
the matching one" — a guard emitting 318 additional absences satisfies every
clause of that sentence while being a useless control, because the one finding
that matters is buried in 319 that do not. And the whole point of this control
is that it be read closely; a control whose expected output is wrong by two
orders of magnitude will be "fixed" by relaxing the assertion.

Fix is one sentence plus a tightened result: state that the disk-read control
composes the installed reader and the comparison over a locked map **restricted
to the three fixture entries** (their real locked versions, taken from the
lockfile), and have result 2 require the finding list to be **exactly** those
two items and nothing else.

### 2. The committed fixture cannot be committed: a bare `node_modules` pattern in `frontend/.gitignore` ignores it at any depth, and `.gitignore` is outside the spec's "Nothing else"

`frontend/.gitignore:10` is the bare pattern `node_modules` (and the root
`.gitignore:99` is `node_modules/`). A bare pattern with no slash matches at
every depth, so the fixture the spec's central control depends on is ignored.
Measured on the real repository, read-only:

```
$ git check-ignore -v frontend/src/__tests__/fixtures/node_modules/eslint/package.json
frontend/.gitignore:10:node_modules   frontend/src/__tests__/fixtures/node_modules/eslint/package.json
```

The consequence is the worst available one: the fixture exists on the
implementer's disk, the guard is green locally, and the directory is absent from
the repository — so in CI the reader finds nothing and the control either goes
red for a reason unrelated to the property or, if written to tolerate a missing
fixture root, passes vacuously. That is this repository's eighth vacuous check,
arriving by a route nobody looked at, in the control whose entire job is to
prevent exactly that.

The trap is sharper than it looks, which is why the spec must name the remedy
rather than leave it to be discovered. I tested both candidate fixes in a
throwaway repository (`reviewer-127/gp1`):

```
A: 'node_modules' + '!src/__tests__/fixtures/node_modules/**'
   -> STILL IGNORED (git does not descend into an excluded directory)
B: 'node_modules' + '!src/__tests__/fixtures/node_modules/'
                  + '!src/__tests__/fixtures/node_modules/**'
   -> not ignored
```

The obvious one-line negation **does not work**; the directory itself must be
re-included before its contents can be. I also confirmed the deeper
`frontend/.gitignore` negation overrides the root pattern, so the root
`.gitignore` needs no change.

So the spec must either (a) add the layered two-line negation to
`frontend/.gitignore`, list that file under "Files touched" — which currently
ends "Nothing else" and does not include it — and require QA to assert the
fixture files are **tracked** (`git ls-files` naming them), not merely present;
or (b) avoid the literal `node_modules` path segment in the fixture by having
the installed reader resolve a package's subpath under a configurable
directory name, and say so. (a) is simpler and keeps the reader's contract as
specified. Either way, "the fixture is tracked" has to be an asserted
property, because its absence is silent.

## Suggestions (non-blocking)

1. **`AGENTS.md` has two rows labelled `Testing` and two labelled `Linting`.**
   The backend stack table carries `| Linting | Ruff 0.16.5 ... |` at line 362
   and `| Testing | pytest + pytest-cov, httpx |` at line 363, *before* the
   frontend rows at 380/381. Decision 5 scopes the anchor to "AGENTS.md's
   frontend stack table" but does not say how the guard finds that table (the
   `## Frontend` heading? the `| Category | Technology |` header?), and the
   three controls supply markdown as an input, so none of them would catch a
   guard that latches onto the backend row on the real file. I am not blocking
   on it: the backend rows state no vitest/eslint major, so a mis-anchored
   guard fails the no-match check loudly, and result 4 requires the suite green
   on the reconciled tree, which exercises the real file. It will cost an
   implementation round rather than ship broken — but naming the table anchor
   in one clause avoids that round.
2. **Price the CI cost with its cache state**, per the note under finding 3:
   28–71 ms warm, 370–500 ms cold, over 335 entries post-reinstall rather than
   the 316 present today.
3. **CI's `node-version: 24` is a floating major**, so the `EBADENGINE`
   asymmetry can reappear from CI's side as well as the operator's. One clause
   in the new section noting that CI resolves 24.x at run time would make the
   divergence's two moving parts explicit. Pre-existing and out of scope to
   change.

## Things I could not verify

None. Every new figure in the revision was re-derived here: the seven nested
absences by name, 335/321/14/12, the six majors, the complete stack-table
audit, the local node version against jsdom's declared range, the CI line
numbers, and the guard's behaviour under three harnesses at a real on-disk
fixture. The real `frontend/node_modules` was never installed into:
`git status --porcelain frontend/ .gitignore AGENTS.md` is empty after my
probes, and `frontend/node_modules/eslint` is still 9.39.4.

VERDICT: REJECTED

1. The disk-read fixture control does not specify that the locked map is
   restricted to the three fixture packages, so under the spec's literal
   wording — the guard's real 335-entry set pointed at a 3-package root — it
   reports 320 findings (319 absent, 1 mismatch), measured, not the "exactly
   one mismatch and one absence" required. State the restriction, and have
   expected result 2 require the finding list to be exactly those two items
   and nothing else.
2. `frontend/.gitignore:10` is a bare `node_modules` pattern, which
   `git check-ignore` confirms ignores
   `frontend/src/__tests__/fixtures/node_modules/.../package.json` at any
   depth, so the fixture the central control depends on cannot be committed —
   and `.gitignore` sits outside the spec's "Files touched ... Nothing else".
   The one-line negation does not work (git will not descend into an excluded
   directory); only a layered `!.../node_modules/` plus `!.../node_modules/**`
   does, verified. Name the remedy, list the file, and make "the fixture files
   are tracked" an asserted property, since their absence is silent and turns
   the anti-vacuity control into the vacuous check it exists to prevent.
