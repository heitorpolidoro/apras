# APRAS-125 — code review, round 2

Reviewed: the four staged paths in
`/Users/heitor/workspace/apras/.claude/worktrees/agent-a5fc01175acc9159a`
at `4be622b`, now `1264 insertions / 102 deletions over 4 files`
(`darkVariantCompile.test.ts` grew 407 → 531 lines; `tailwindSheet.ts` changed
only in a doc comment; `themeTokenCompile.test.ts` and the spec are byte-identical
to round 1). Nothing committed, staged, unstaged or pushed; the worktree is
exactly as found (four staged paths plus the untracked developer report,
SHA-verified against pre-review copies).

Scratch namespace `…/scratchpad/reviewer-125`. No `npm ci` / `npm install` in the
repository or any worktree; Tailwind 4.3.3 remained in my scratch install.

## Round 1's blocking finding — fixed, and the fix is real

I did not re-run the developer's mutations. I rebuilt the attack from scratch:
**14 fresh mutants on the round-2 tree**, each applied on disk, run, reverted,
with `git diff --quiet` verified after every one.

The exclusion oracle is now `SCANNER_EXPECTATIONS`, a literal 22-row table
asserted through the named `isScanned()` predicate (`darkVariantCompile.test.ts:160-172,
216-283, 422-430`). Every arm I could delete or widen now reddens a *named* row:

| my mutant | round 1 | round 2 |
|---|---|---|
| drop the `test` segment arm | 75/75 **green** | `testing/helpers.ts` row red |
| drop `\.(test\|spec)\.[^/]+$` | 75/75 **green** | `lib/focusTrap.test.ts` + `lib/focusTrap.spec.tsx` rows red |
| drop `\.stories\.tsx$` | 75/75 **green** | `components/ui/button.stories.tsx` row red |
| drop `\.d\.ts$` | 75/75 **green** | `vite-env.d.ts` + `lib/schema.d.ts` rows red |
| drop `__mocks__` | not tried | `api/__mocks__/client.ts` row red |
| drop `__fixtures__` | not tried | `lib/__fixtures__/palette.ts` row red |
| segment → bare substring | not tried | `lib/latest.ts` **and** `testing/helpers.ts` rows red |
| segment arm loses its trailing `/` | not tried | `testing/helpers.ts` row red |
| `SCANNABLE` loses `css` | not tried | `index.css` row + the on-disk wiring case red |
| wiring stops calling the predicate | — | 7 red, incl. the on-disk case and the sentinel |
| wiring diverges from the predicate for one untabled path (`isScanned(f) \|\| f.startsWith("__tests__/themeToken")`) | — | `keeps token-bearing test files out of every token's provenance` red |

All three of my round-1 deletions are dead, and the predicate/wiring split is
itself guarded: a table that passed while the real filter did something else is
caught by `excludes the real test, helper and setup paths on disk` (`:432-447`),
which re-checks the existing rows against `SCANNED_FILES` membership. One
mutant was **equivalent**, not surviving: unanchoring `SCANNABLE` to
`/\.(ts|tsx|css)/` changes no verdict because no file under `src` contains
`.ts`/`.tsx`/`.css` other than as a suffix (measured: zero such paths).

### Synthetic rows: acceptable here, and they do exercise their arms

`src` really holds no `__mocks__`, no `__fixtures__`, no `*.stories.tsx` and no
`*.d.ts` (I checked each of the 22 rows for existence on disk — ten are synthetic,
twelve real). The four synthetic rows are the right call, not a weakness:

- `isScanned` is a **pure predicate**, so a hand-written input table is the
  normal and strongest form of test for it. The oracle is stated intent, which
  is precisely what round 1 lacked.
- I verified each synthetic row bites: deleting `__mocks__`, `__fixtures__`,
  `\.stories\.tsx$` and `\.d\.ts$` from `EXCLUDED` each turns exactly its own
  row(s) red. They are not decoration.
- Dropping those arms instead would be worse. `*.d.ts` returns the moment anyone
  restores `vite-env.d.ts` or vendors a types file; `*.stories.tsx` the moment
  Storybook lands; and an un-excluded declaration or story file is exactly the
  APRAS-110 leak vector, a literal written for a tool rather than for a user.
  An arm guarded by a synthetic row costs one line and fails loudly; an arm
  deleted "because nothing exercises it" has to be rediscovered after it breaks.
- The near-miss keepers (`lib/latest.ts`, `testing/helpers.ts`, `lib/spectrum.ts`,
  `lib/stories.tsx`, `lib/schema.ts`) do the job they were added for: they are
  the only thing that catches the segment→substring widening, which I confirmed
  by running it.

The one thing worth saying plainly: the synthetic rows test the predicate, not
the tree. That is fine because the wiring case covers the tree for every row
that exists, and `expect(SCANNED_FILES).not.toContain("test/setup.ts")` /
`…not.toContain("__tests__/darkVariantCompile.test.ts")` (`:445-447`) are real
on-disk assertions.

### The provenance hardening — the reasoning is right

`TOKEN_BEARING_AND_UNSCANNED` (`:276-283`, asserted at `:465-487`) now requires
each named file to **exist** and to **actually match `TOKEN`** before asserting
its absence from the scanned set and from all provenance. That reasoning is
correct and worth stating as a rule: `not.toContain(path)` is satisfied by a
path that was renamed, by a path that never carried a token, and by a typo —
three ways to pass for a reason that has nothing to do with the property. The
existence + token-count preconditions convert the absence from "nothing happens
to be there" to "something that would have been caught is being kept out". My
`wiring-sneak-tests-helper` mutant (the filter admits `__tests__/themeToken*`
while the predicate still says no) is red on exactly this case — so the
hardening is load-bearing, not ceremonial.

### The sentinel — the sweep's own find, verified

I mutated the sentinel to `dark:bg-fuchsia-3000` everywhere it appears
(candidate array and both assertions). Round 2 goes **red** on
`never sees the fixture's sentinel in the scanned sheet`, because the new
`expect(verdict(fixtureSheet, "dark:bg-fuchsia-300")).toBe("painted")` half
(`:515-521`) fails: a misspelt sentinel is not a utility at all, so `no-rule` in
the scanned sheet proved nothing. This is the same shape as my round-1 finding —
an assertion satisfied for the wrong reason — and the developer found it
unprompted. On the round-1 tree that mutation was green. The sweep was real.

### The §6 helper violation

`tailwindSheet.ts:214-215` no longer names a stacked token, and
`keeps the shared helper free of any paint-token literal` (`:450-463`) asserts
`[...helper.matchAll(TOKEN)]` is empty. I reintroduced a `dark:bg-foreground`
into a helper doc comment: red. Also correct that this is the comment-prose
mechanism again — Tailwind's real scan reads comments, so a token literal in a
file the guard excludes is a latent leak the moment an exclusion arm moves.

## Everything from round 1 that had to stay true, re-verified

- `rules` / `declarations` still byte-identical to `HEAD`'s copies;
  `themeTokenCompile.test.ts` byte-identical to round 1 and still importing only
  the two old readers. 80 cases green.
- **The mandatory R6 mutation, re-run by me against the restructured suite**:
  `grep -c` **2 → 0 → 2** across `git checkout -- <that one path>` (no stash),
  the new suite **red** on `keeps token-bearing test files out of every token's
  provenance` (the `REQUIRED_LITERALS` half) and on `clears the structural
  floors`, case count 97 → 96, while **APRAS-110's suite stayed green at 18/18**
  on the same mutant. The hole is still closed after the restructure.
- **Tailwind 4.3.3, re-measured in my scratch install** against the round-2
  helper and extractor: 276 files, 59 tokens, 8 stacked, bg 33 / text 26,
  **59/59 gated and painted**, `R1 exact selector matches: 1`, all controls
  identical to 4.2.4. The dual-version contract holds on the version CI
  installs.
- Gates, all re-run by me: `npm run test:coverage` **exit 0**,
  `Test Files 199 passed (199)`, `Tests 2691 passed (2691)` (2594 + 97), coverage
  **91.73 / 85.67 / 87.95 / 92.44** against 80/78/76/80; `tailwindSheet.ts`
  98.37 / 89.28 / 100 / 100 with the same three moved-code gaps;
  `npm run build` **exit 0**; `npx eslint --version` → **v9.39.4**,
  `npm run lint` → `370 problems (368 errors, 2 warnings)` with **zero**
  occurrences of any of the three touched files in the output.

Security, architecture and style unchanged from round 1 and clean: pure
filesystem reads under `frontend/src`, no new dependency, no network, no
secrets, the helper still on the spec's named seam, the family alternation and
the paint map still adjacent.

## Suggestions (none blocking)

1. **The coordinator's summary is one item ahead of the tree**: §5's figure was
   corrected in the test comment (`:493`, "loses 26") but **not** in the staged
   spec — `docs/tasks/APRAS-125-spec.md:247` still reads "dropping `text` loses
   31 (59→28)". My independent measurement on 4.3.3 is bg 33 / text 26. Since the
   spec is being added by this very commit, the one-word fix keeps the shipped
   document honest.
2. **An exclusion arm that swallows a whole token-bearing directory is still
   silent.** Adding `|^features\/lot-management\//` to `EXCLUDED` drops 11 files
   and **14 of the 59 guarded tokens**, and the suite is 83/83 green: the ≥200
   file floor (265 left), the ≥1 bg / text / stacked floors and
   `REQUIRED_LITERALS` all still hold. This is the structural-floor design the
   spec chose over count floors, and no assertion claims otherwise, so it is not
   a vacuity — but a cheap hardening exists: assert that every immediate
   `features/*` directory contributes at least one scanned file, or floor the
   token count near today's 59 rather than at 1. Worth a follow-up line in the
   spec's "what this guard cannot prove" rather than silence.
3. Carried over, still open, still non-blocking: `darkVariantCompile.test.ts:362`
   credits the unconditional-`true` prior art to **APRAS-127**, which on the
   board is "Reconcile frontend node_modules with package-lock.json" — wrong id
   in a shipped comment.
4. Carried over: the `value.trim().length > 0` clause (`:131`) and the
   `toBeGreaterThan(0)` at `:309` remain unfalsifiable on this corpus
   (weakening them to `value !== undefined` leaves the suite green); and
   `declarationsDeep`'s prelude-discard comment still overstates its necessity
   (a flushed prelude yields the name `@supports (color`, never `color`), while
   its own comment strip is dead because `rulesDeep` already stripped. All three
   are defensive code with accurate behaviour and inaccurate or unexercised
   justification — fix when convenient.
5. Carried over: `verdicts()` (`:138-146`) is still called only by the case that
   asserts it throws; the empty-extraction property is really carried by the
   floors case. Route the per-token path through it or drop it.

VERDICT: APPROVED

None.
