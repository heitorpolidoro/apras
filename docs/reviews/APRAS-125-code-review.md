# APRAS-125 — code review, round 1

Reviewed: the four staged paths in
`/Users/heitor/workspace/apras/.claude/worktrees/agent-a5fc01175acc9159a`
at `4be622b`, `1140 insertions / 102 deletions over 4 files`
(`docs/tasks/APRAS-125-spec.md` new, `frontend/src/__tests__/darkVariantCompile.test.ts`
new, `frontend/src/__tests__/helpers/tailwindSheet.ts` new,
`frontend/src/__tests__/themeTokenCompile.test.ts` modified). Nothing was
committed, unstaged or restaged; the worktree was left in exactly the state it
was found in (four staged paths plus the untracked developer report, SHA-verified
against pre-review copies at the end).

Scratch namespace: `…/scratchpad/reviewer-125`. No `npm ci` / `npm install` was
run in the repository or any worktree; Tailwind 4.3.3 was installed into the
scratch directory only.

## Environment, printed before any figure below

```
$ node -p "require('tailwindcss/package.json').version"   # worktree frontend/
4.2.4
$ npx eslint --version
v9.39.4
$ lockfile pins
tailwindcss 4.3.3, eslint 10.11.0
```

So every in-repo emission figure below is on **Tailwind 4.2.4** (nesting shape).
4.3.3 figures come from my own scratch install, stated as such.

## Gates — all re-run, all reproduce

| gate | claimed | measured |
|---|---|---|
| `npm run test:coverage` | exit 0, 199 files / 2669 tests | **exit 0, `Test Files 199 passed (199)`, `Tests 2669 passed (2669)`** |
| coverage | 91.73 / 85.67 / 87.95 / 92.44 vs 80/78/76/80 | **identical, gate met** |
| `tailwindSheet.ts` coverage | 98.37 / 89.28 / 100 / 100, uncovered 51-53, 133-134, 139 | **identical** |
| `npm run build` | exit 0 | **exit 0** |
| `npm run lint` | `370 problems (368 errors, 2 warnings)` on eslint 9.39.4 | **identical; none of the three touched files appears anywhere in the lint output, so the task adds zero findings** |
| new suite | "74 tests" | **75 tests passing** — see Suggestion 1; the 2669 total (2594 + 75) is the consistent figure |

`themeTokenCompile.test.ts` is green with **80** cases, and green *for the right
reason*: I extracted `rules` and `declarations` from `HEAD:…/themeTokenCompile.test.ts`
and from the new helper and `diff`-ed them — **byte-identical**, and the suite
imports only those two (`grep` for `rulesDeep|declarationsDeep|escape(` in that
file hits a comment and nothing else). So its greenness is a proof about code
this task did not change, as the spec's §6 seam requires. The `Rule` interface
moved unchanged too, and the `build()` seam sits exactly before
`const parsed = rules(css)`.

## The 4.3.3 substitute — judged adequate, and I closed the gap directly

The developer could not install 4.3.3 and pinned it instead with a case that
feeds `rulesDeep` both literal emission shapes. That substitute is sound as far
as it goes, but it only proves the *reader*, not the corpus. I installed
`tailwindcss@4.3.3` into my scratch directory and ran the implementation's own
reader (`rulesDeep` / `declarationsDeep` / `escape`, imported from a copy of the
shipped helper with the `tailwindcss` import repointed) plus a transcription of
the suite's extractor and `verdict()` against the real 4.3.3 engine and its own
`index.css`:

```
files 276 tokens 59
stacked 8 bg 33 text 26
non-painted tokens: []
R1 exact selector matches: 1
  control dark:bg-foreground        => painted
  control dark:text-sm              => wrong-property
  control dark:bg-[url('/x.png')]   => wrong-property
  control dark:bg-nosuchcolour      => no-rule
  control bg-foreground             => not-gated
sentinel in scanned sheet: no-rule
--- raw emission ---
.dark\:bg-foreground:is(.dark *) { background-color: var(--color-foreground); }
```

So on the version CI actually installs: the flattened shape is confirmed, the
exact string `.dark\:bg-foreground:is(.dark *)` resolves, **59/59 tokens are
gated and painted**, all five fixture controls return the same verdicts as on
4.2.4, and the sentinel stays absent. The dual-version contract holds in fact,
not only by substitute. The implementation has no version branch, which is why
this works.

## My own mutants — 17 built independently of the developer's eleven

Each was applied on disk, run, reverted, and the worktree re-verified clean
(`git diff --quiet`) after every single one.

Killed (the check that caught it in brackets):

1. `verdict` returns `"painted"` unconditionally — **6 red** [all four §4
   controls, the ungated control, the same-rule control, the sentinel]. The
   checker is demonstrably not satisfiable by an unconditional `true`.
2. gate filter deleted (`const gated = matched`) — **2 red** [ungated
   `bg-foreground`, same-rule].
3. paint read from `matched` instead of `gated` — **1 red** [same-rule control].
4. `escape` stops escaping `:` — 63 red.
5. `escape` stops escaping `[ ] ( ) ' #` — 1 red [the `url('/x.png')` control].
6. `rulesDeep` comment strip removed — 1 red [the comment case].
7. `rulesDeep` stops treating `@`-preludes as at-rules — 60+ red.
8. `rulesDeep` `&`→parent substitution removed — 60+ red.
9. `rulesDeep` descendant join removed — 1 red [the descendant case].
10. matcher narrowed to selector equality — 60+ red (§0's green-on-dev /
    red-in-CI failure).
11. `declarationsDeep` made shallow — exactly the 8 stacked tokens red.
12. `compileIndexCss` memoised on a module-global compiler — **1 red** [the
    sentinel case]. R3's no-caching contract is mechanically enforced.
13. grammar: stacked-variant group dropped (59→51) — 1 red [structural floors].
14. grammar: `text` dropped (59→33) — 1 red [structural floors].
15. **The mandatory R6 mutation, run myself.** Line-91 literal replaced with
    `` className={`… dark:bg-${"foreground"}`} `` *and* the line-85 doc-comment
    literal removed. `grep -c` printed **2 → 0 → 2** across
    `git checkout -- <that one path>` (no stash, ever). The new suite went
    **red** on `keeps the suite's own literals out of every token's provenance`
    (the `REQUIRED_LITERALS` case) and on `clears the structural floors`, while
    **APRAS-110's own suite stayed green at 18/18 on the same mutant**. That is
    the hole this task exists to close, and it is closed.

Survived, i.e. the implementation is strictly stronger than anything asserted:

16. `value.trim().length > 0` weakened to `value !== undefined` — **75/75
    green** (Suggestion 3).
17. `declarationsDeep`'s prelude discard replaced by a `flush()` — **green**; and
    its comment strip removed — **green** (Suggestions 4 and 5).

**The two spec assertions the developer reported as unfalsifiable: diagnosis
confirmed, and both controls confirmed to kill.** My mutants 2 and 3 are exactly
the deletions in question, built without reference to the developer's M5/M11. I
also re-ran them with the two added controls removed in spirit by checking which
case fails: mutant 2 fails *only* `rejects an ungated bg-foreground` and the
same-rule case, mutant 3 fails *only* `never takes the gate from one rule and the
paint from another`. So yes — as the spec was written in round 2, both the gate
filter and the same-rule requirement were deletable with all per-token cases
green, and the two controls the developer added (the `bg-foreground` candidate
and the hand-written mixed sheet) are each the sole thing standing between the
guard and that vacuity. The strengthening is correct, minimal and in the right
place.

## Blocking finding

### 1. The exclusion case cannot fail for a wrong exclusion set — it compares `SCANNED_FILES` against the very regex that built it

`frontend/src/__tests__/darkVariantCompile.test.ts:344-349` (and the same
pattern at `:363-367`):

```ts
const SCANNED_FILES = … .filter((file) => SCANNABLE.test(file) && !EXCLUDED.test(file) && …)
…
it("excludes every test, mock, story and declaration path", () => {
  for (const file of SCANNED_FILES) {
    expect(file, `${file} must not be in the scanned set`).not.toMatch(EXCLUDED);
  }
```

Every element of `SCANNED_FILES` was selected by `!EXCLUDED.test(file)`, so
`not.toMatch(EXCLUDED)` is true by construction. This is mechanism #3 of this
repository's vacuity family — a comparison between a thing and itself. It can
fail only if the *filter* stops calling the constant (which is what the
developer's M6 mutated, and why M6 looked like a kill); it cannot fail for any
error **in** the constant, which is where the risk actually lives. Measured, on
the shipped tree:

- drop the `test` segment from `EXCLUDED` → `src/test/setup.ts`,
  `src/test/classTokens.ts`, `src/test/permissionFixtures.ts` enter the scanned
  set (276 → 279 files) and the suite is **75/75 green**, including the case
  titled "excludes every test, mock, story and declaration path";
- drop the `\.(test|spec)\.[^/]+$` arm → **75/75 green** (every co-located test
  file in this tree happens to sit inside a `__tests__` directory, so the other
  arm masks it);
- drop the `\.stories\.tsx$|\.d\.ts$` arms → **75/75 green**.

Three of the four arms of R2's exclusion are therefore deletable in silence, and
the one that is protected (`__tests__`) is protected by the *sentinel* case, not
by the case that claims to test exclusion. The practical consequence is the
APRAS-110 leak re-opening quietly: the whole design rests on no test-authored
literal entering the candidate list, and `src/test/` is precisely where a future
shared class-token fixture would live (`src/test/classTokens.ts` exists and
documents that another sweep already has to tiptoe around it).

The fix is a few lines and needs no new mechanism — assert the *predicate*
against a literal table instead of asserting the output against the predicate,
e.g.

```ts
it.each([
  "test/setup.ts",
  "__tests__/darkVariantCompile.test.ts",
  "__tests__/helpers/tailwindSheet.ts",
  "features/user-administration/__tests__/TenantHeaderLogo.test.tsx",
  "features/x/Foo.test.tsx",
  "features/x/Foo.spec.ts",
  "components/Foo.stories.tsx",
  "types/vite-env.d.ts",
  "__mocks__/server.ts",
  "__fixtures__/x.ts",
])("%s is excluded", (file) => { expect(EXCLUDED.test(file)).toBe(true); });
```

plus one kept-path control (`features/…/TenantHeaderLogo.tsx`, `index.css`) and,
cheapest of all, `expect(SCANNED_FILES).not.toContain("test/setup.ts")` and
`…not.toContain("__tests__/darkVariantCompile.test.ts")`, which are real
assertions because those paths exist. With that table in place each of the three
deletions above becomes red. Everything else in the suite can stay as it is.

## Suggestions

1. `darkVariantCompile.test.ts` runs **75** cases, not the 74 the developer
   report states (5 harness + 7 controls + 2 scanned-list + 2 token-set + 59
   per-token). The coverage total (2594 + 75 = 2669) is right, so this is a
   report arithmetic slip only, but QA will diff it.
2. `darkVariantCompile.test.ts:284` credits the "satisfied by a checker
   returning `true` unconditionally" prior art to **APRAS-127**, which on the
   board is "Reconcile frontend node_modules with package-lock.json". Wrong id
   in a shipped comment; point it at the task that actually demonstrated it.
3. The `value.trim().length > 0` clause in `verdict()` (`:131`) and the
   `toBeGreaterThan(0)` in R1 (`:231`) are unfalsifiable on this corpus —
   weakening them to `value !== undefined` leaves 75/75 green. Not the same
   class of problem as the blocking finding (no assertion claims that property
   and fails to check it), but if you want it live, a hand-written sheet with
   `background-color: ;` in the gated rule is a two-line control in the same
   place as the same-rule sheet.
4. `declarationsDeep`'s prelude-discard comment (`tailwindSheet.ts:220-223`)
   overstates its own necessity. Flushing the prelude instead of discarding it
   cannot produce a bogus `color` pair, because the harvested name would be
   `@supports (color`, never `color` — the discard is defensive, not
   load-bearing, and the "@supports trap" the developer listed as unverifiable is
   in fact unreachable rather than merely unexercised. Worth rewording so a
   future reader does not go looking for the trap.
5. `declarationsDeep`'s own comment strip (`:263`) is dead in practice: every
   caller feeds it a body that `rulesDeep` already stripped, and removing it
   leaves the suite green. Harmless duplication; mention it or drop it.
6. `escape`'s `#` arm is never exercised (no candidate carries `#`), consistent
   with §6's named arbitrary-value hole. Fine as disclosed.
7. `verdicts()` (`:138-146`) is dead except for the case that asserts it throws:
   the per-token path calls `verdict()` directly, so the empty-list guard never
   actually guards this suite. The property is covered anyway by the floors case
   (`toContain("dark:bg-foreground")` reddens on an empty extraction). Either
   route the per-token cases through `verdicts(scannedSheet, TOKENS)` so the
   throw is live, or delete it and let the floors carry the property.
8. The spec ships **in this diff**, and §5's "dropping `text` loses 31" is wrong:
   I measured **bg 33 / text 26** independently on 4.3.3 (33 + 26 = 59). The
   developer disclosed it rather than correcting it; since the document is being
   added by this commit, correcting the figure costs nothing.

Architecture, KISS/YAGNI/DRY and security are otherwise clean: the helper lands
exactly on the spec's named seam with `SRC` derived two levels up from its own
`import.meta.url`, the deep readers are genuinely new functions beside untouched
ones, `escape` is new rather than a reuse of `escapeClass` (and escapes
`: / . [ ] ( ) ' #`), the family alternation and the paint map sit adjacent as
specified, there is no new dependency, no network or database access, no secret
handling, and the only filesystem reads are `readdirSync`/`readFileSync` under
`frontend/src` with no path coming from outside the tree.

Nothing I could not verify: the two items the developer listed as blocked by the
`npm ci` prohibition, I resolved for Tailwind 4.3.3 by scratch install (above);
eslint 10.11.0 I did **not** install, and I note it the same way the developer
did — the 9.39.4 reading is reported as a 9.39.4 reading, and since none of the
three touched files produces any lint finding at all, the delta against the
10.11.0 baseline is zero regardless of which engine measures it.

VERDICT: REJECTED

1. `frontend/src/__tests__/darkVariantCompile.test.ts:344-349` (same pattern at
   `:363-367`) — the exclusion case asserts `SCANNED_FILES` against the same
   `EXCLUDED` constant that produced it, so it cannot fail for a wrong exclusion
   set. Demonstrated: dropping the `test` segment (3 test-support files enter the
   scanned set), dropping the `\.(test|spec)\.[^/]+$` arm, and dropping the
   `\.stories\.tsx$|\.d\.ts$` arms each leave the suite 75/75 green. Assert the
   predicate against a literal table of paths (one per arm, plus a kept-path
   control), or at minimum `expect(SCANNED_FILES).not.toContain("test/setup.ts")`
   and `…not.toContain("__tests__/darkVariantCompile.test.ts")`.
