# APRAS-127 — spec review, round 3 (findings-only)

Spec: `docs/tasks/APRAS-127-spec.md`, 431 lines, untracked. Base `4be622b`.
Scope: verify round 2's two blocking findings are resolved, plus a consistency
pass over the sections changed to fix them. Probes in
`.../scratchpad/reviewer-127/`.

## Round 2's two findings

### Finding 1 — resolved, and result 2 now does the work it claims

The arithmetic the author re-derived is right, and I re-measured it rather than
checking it on paper: with the unrestricted 335-entry locked map pointed at a
three-package fixture root, the guard emits **320 findings — 319 absences and 1
mismatch**. The decomposition also holds: 321 top-level entries, the fixture
supplies two of them, 321 − 2 = 319, and the 14 nested entries are skipped.

The fix is the right one — making the locked map a parameter *for its own
stated reason*, distinct from the root's — and I verified the control it enables
discriminates in all four directions that matter (`reviewer-127/r3guard.mjs`,
locked versions read from the real `package-lock.json`):

```
locked map restricted to the three: {eslint 10.11.0, axios 1.20.0, jsdom 30.1.1}

=== fixture root present ===
  conformant   findings=2  exactly-two-and-nothing-else=PASS
       {mismatch eslint locked 10.11.0 installed 9.39.4}
       {absent jsdom}
  LOCKBUG      findings=0  FAIL
  MISREPORT    findings=3  FAIL   (installed "0.0.0-unknown" on eslint and axios)

=== fixture root MISSING ===
  conformant   findings=3  FAIL   (all three absent)
```

So, to the question asked: **"exactly two and nothing else" is satisfiable by a
conformant implementation and unsatisfiable by both bad harnesses** — measured,
not reasoned. Each clause earns its place. The count kills the
lockfile-resolving reader, the installed-value clause kills the reader that
fails for the wrong reason, and "nothing else" closes the flood. Binding the
mismatch's *locked* side to the real lockfile rather than an invented number is
a good touch: it keeps the control anchored to this repository, so a fixture
that drifts from the lockfile fails rather than silently testing nothing.

### Finding 2 — resolved, both halves reproduced

`git check-ignore -v` on the real repository still names
`frontend/.gitignore:10:node_modules` for the fixture path. And I re-ran the
three-form table in a throwaway repository by the author's stronger criterion —
whether git *discovers* the file, not merely what `check-ignore` says:

```
form 1: node_modules                                    ls-files=0 status-uall=0  -> NO
form 2: + !<path>/node_modules/**                       ls-files=0 status-uall=0  -> NO
form 3: + !<path>/node_modules/ AND !.../node_modules/** ls-files=1 status-uall=1  -> yes
```

The table in the spec is exactly right, including the trap: the single-line
negation does not work because git will not descend into an excluded directory.
Specifying both lines with that reason, and listing `frontend/.gitignore` under
Files touched with "that one path and nothing broader", resolves the finding.

### The `node_modules` name retention — I accept the trade

I raised the rename as an option and the author declined it with an argument I
find stronger than mine. The lockfile's keys *are* `node_modules/`-prefixed —
confirmed, including nested keys that carry the segment internally, e.g.
`node_modules/vitest/node_modules/magic-string` — and the reader resolves
`<root>/<lock key>` verbatim. A differently-named fixture directory would
require rewriting the key's leading segment, a transformation the production
run never performs, so the control would exercise a path construction that
differs from the one it exists to protect. For a disk-read control whose entire
purpose is fidelity to the real path construction, that is a real loss for a
cosmetic gain. Two `.gitignore` lines and an asserted trackedness check are the
cheaper side of the trade. **Ruling: keep the segment, as specified.**

### The correction to my reasoning — the author is right, and I was too strong

I checked this directly. With the fixture root absent and the locked map
restricted, all three packages read as absent, so the control reports three
findings and fails "exactly two" (output above). Fixture absence is therefore
**not silent** once result 2 demands exactness — my round-2 wording overstated
it. What remains true is the author's sharper point: the failure is red with a
*misdiagnosis*, because a reader bug and an untracked fixture are
indistinguishable in that signal. Asserting trackedness through
`git ls-files --error-unmatch` to turn the second into a named failure is the
proportionate response, and failing rather than skipping when git is
unavailable is the correct default — a skip is how this check would quietly
stop existing.

## Additional verification I ran, since it is load-bearing and the spec does not mention it

Result 1 runs `npm ci` and result 2 depends on the fixture being on disk, so I
checked that the two do not collide: I planted the three-package fixture at
`frontend/src/__tests__/fixtures/node_modules/` in a scratch clone and ran
`npm ci` over it. **`npm ci` exits 0 and the nested fixture survives
untouched** — npm cleans only the package-root `node_modules`. The risk is
foreclosed. I then removed the fixture and re-verified the clone is back to 0
mismatches / 0 absences and byte-identical to the repository's sources.

I also tested a hazard I had been about to raise and found it does not exist:
if the fixture were placed without an intermediate segment, at
`frontend/src/__tests__/node_modules/`, I expected the stub packages to shadow
real ones for the 12 real test files sitting in that directory. They do not —
node's resolution finds the stub directory, fails to load it (no `main`, no
`index.js`) and **falls through to the real package**. I verified this with
`require.resolve`. I am recording it so the point is not raised again in a
later round; the spec's own examples use `fixtures/` anyway.

## Judgement on the eight results

Eight is at the cap but not over it, and each is a single mechanically
verifiable sentence. I re-checked all eight for verifiability and found no
gap: 1 and 2 I have measured directly, 3 is `check-ignore` plus
`ls-files --error-unmatch`, 4 is three supplied-prose cases, 5 and 6 are
before/after deltas on the implementation's own tree, 7 is a read of
`AGENTS.md`, 8 is a byte comparison plus recorded QA notes.

One remaining looseness turns out to be harmless, which is worth stating
because it is the right way to specify: decision 3 still does not say where the
installed reader gets its path set. But result 2's exactness makes both
candidate implementations correct — whether the reader enumerates all 335 paths
or only the restricted three, the comparison iterates the locked map and the
finding count is two either way. An assertion that pins the observable
behaviour has made the unstated detail irrelevant, so it needs no further
words.

**On merging results 2 and 3 if a ninth is ever needed: I agree, and that is
the right pair.** Trackedness exists only to disambiguate result 2's failure
mode, so they are one property with two clauses rather than two properties.
Result 3's three sub-clauses are mildly over-specified as it stands —
`check-ignore` reporting not-ignored and `ls-files --error-unmatch` succeeding
are nearly the same assertion — so the merge would lose nothing.

## Suggestions (non-blocking, none affects a result)

1. **"produces one finding, not two" is wrong by one; it produces zero.**
   Measured: a lockfile-resolving reader yields **0 findings**, not 1, because
   the same bug that reports the mismatching package as matching also hands the
   *absent* package a version out of the lockfile, so the absence disappears
   too. The conclusion — that it fails "exactly two" — is unaffected and the
   control still kills it. But in a spec whose authority rests on "measured
   rather than quoted", that word should be `zero`.
2. **The 125 ms figure still carries the pre-reinstall count** (round 2's note,
   unaddressed): 316 is what is present *today*; in CI, after `npm ci`, all 335
   are present. My measurement is 28–71 ms warm and 370–500 ms cold. The
   conclusion is unchanged under any of those numbers.
3. **Decision 5 still does not say how the frontend stack table is located**
   (round 2's note, unaddressed). `AGENTS.md:362-363` carries a backend
   `| Linting |` and `| Testing |` row ahead of the frontend pair at 380-381,
   and the four `AGENTS.md` controls supply markdown as an input, so none would
   catch a guard that anchors on the backend row. Still not blocking for the
   same reason as before: the backend rows state no vitest/eslint major, so a
   mis-anchored guard trips the no-match failure loudly against the real file,
   which result 5 exercises. One clause naming the anchor would save that round.
4. **Consider recording that `npm ci` leaves the nested fixture intact**, since
   result 1 runs `npm ci` and result 2 depends on the fixture surviving it. I
   verified it does; a clause saves the implementer the same check.

## Things I could not verify

None. Everything load-bearing in this revision was re-measured here: the 320 =
319 + 1 arithmetic, the four-way discrimination of result 2's exactness clause,
the three-form ignore table by discovery, the missing-fixture failure shape,
`npm ci`'s indifference to the nested fixture, and the module-resolution
question I raised against myself.

The real tree was not written to. After my probes `git status --porcelain
frontend/` is empty and `frontend/node_modules/eslint` is still 9.39.4. I did
not edit `frontend/.gitignore`. The author's scratch clone was mutated for the
`npm ci` probe and restored: the fixture is removed, its sources are
byte-identical to the repository's, and it re-measures 0 mismatches / 0 absent.
(`frontend/src/docs/superpowers/` exists in the real checkout as an empty
directory tree, invisible to git and not mine — I left it alone.)

VERDICT: APPROVED

None.
