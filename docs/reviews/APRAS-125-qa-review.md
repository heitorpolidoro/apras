# APRAS-125 — QA verification

**Task**: Assert `dark:`-gated paint tokens reach Tailwind, not just the class list
**Worktree**: `/Users/heitor/workspace/apras/.claude/worktrees/agent-a5fc01175acc9159a` at `4be622b`
**Date**: 2026-10-11

## Environment, printed before any count is quoted

| Thing | Version observed |
|---|---|
| `node` | v24.13.0 |
| `tailwindcss` in `frontend/node_modules` | **4.2.4** (lock pins 4.3.3) |
| `npx eslint --version` in `frontend/` | **v9.39.4** (lock pins 10.11.0) |
| `eslint` installed in my own scratch dir | **v10.11.0** |
| `tailwindcss` installed in my own scratch dir | **4.3.3** |
| vitest | 4.1.11 |

No `npm ci` / `npm install` was run in the repository or any worktree. The 4.3.3
and 10.11.0 installs live only in
`/private/tmp/.../scratchpad/qa125/tw433` and `.../qa125/es10`.

VERDICT: APPROVED

## Expected Results Checked

- [x] **R1** — node-environment case, fresh `compile()`, exact gated selector, both shapes.
  - The suite carries `// @vitest-environment node`. I did not take that on
    faith: I temporarily inserted a probe case asserting
    `typeof globalThis.window === "undefined"` and
    `typeof globalThis.document === "undefined"`. It passed (100 tests with the
    probe), under a project default of `jsdom`. Probe removed, file hash
    restored.
  - "the harness, on the fixture compile > resolves dark:bg-foreground to a
    gated rule carrying background-color" filters the fixture sheet for a rule
    whose **effective** selector equals `.dark\:bg-foreground:is(.dark *)`,
    asserts exactly one, and asserts a non-empty `background-color` in it.
    Green on the installed 4.2.4.
  - Shape-agnosticism confirmed against real compilers, not only against the
    suite's two literal fixtures. I compiled `src/index.css` over
    `["dark:bg-foreground"]` with each compiler and printed the emission:
    - 4.2.4: `.dark\:bg-foreground { &:is(.dark *) { background-color: var(--color-foreground); } }`
    - 4.3.3: `.dark\:bg-foreground:is(.dark *) { background-color: var(--color-foreground); }`
    I then ran the whole suite with `tailwindcss` aliased to the scratch 4.3.3
    build through a throwaway vitest config: **99 passed**. I proved the alias
    was live by pointing it at a non-existent file and watching the run die
    with `Cannot find module …/NOPE.mjs`. Throwaway config deleted.

- [x] **R2** — exclusion set and provenance.
  - `SCANNER_EXPECTATIONS` is a hand-written table of 22 paths asserted through
    `isScanned`, one entry per exclusion arm plus near-miss keepers
    (`lib/latest.ts`, `lib/spectrum.ts`, `lib/stories.tsx`, `testing/helpers.ts`).
    The oracle is the table, not `EXCLUDED`.
  - Mutants I built, each confirmed on disk before vitest ran and restored by
    hash afterwards:
    | mutant | result |
    |---|---|
    | drop `__mocks__` and `__fixtures__` arms | 2 named cases red |
    | drop the `\.d\.ts$` arm | 2 named cases red (`vite-env.d.ts`, `lib/schema.d.ts`) |
    | drop the `__tests__` arm | 2 cases red (helper path + the on-disk wiring case) |
    | widen the segment arm to a bare substring | 2 keeper cases red (`lib/latest.ts`, `testing/helpers.ts`) |
    | **swallow** `features/lot-management/` | "scans every source directory under src/features" red |
    | **swallow** `features/dashboard/` | same case red |
    | narrow `SCANNABLE` to `.css` only | 10+ cases red including the directory-coverage ones |
    Both directions are covered: widening is caught by the keeper rows,
    swallowing by the independent directory-coverage oracle (which consults
    `SCANNABLE` and a literal directory-name list, never `EXCLUDED`).
  - The provenance case asserts, for each of three token-bearing test files,
    that the file still exists, that it still carries a matching token, that it
    is absent from `SCANNED_FILES` and absent from the union of all provenance;
    then that `dark:bg-foreground`'s provenance contains
    `features/user-administration/components/TenantHeaderLogo.tsx`. Both halves
    of the "absence proves nothing" problem are closed.

- [x] **R3** — fresh `compile()` per call, proved by the sentinel.
  - I memoised the compiler in `tailwindSheet.ts` (`cachedCompiler ??= await compile(...)`)
    and re-ran: "never sees the fixture's sentinel in the scanned sheet" went
    red with `expected 'painted' to be 'no-rule'` — the exact accumulation leak
    the design claims to exclude. Helper restored, hash verified.
  - The case also asserts the sentinel is `painted` in the fixture compile
    first, so a misspelt sentinel cannot satisfy `no-rule` for the wrong reason.

- [x] **R4** — per-token named cases, same-rule gate and paint, structural floors.
  - 59 named cases (`grep -c "compiles to a gated, painted rule"` on the verbose
    reporter = 59), one per extracted token.
  - I re-derived the token set independently in Python from the shipped sources:
    **276 scanned files, 59 tokens, 33 `bg`, 26 `text`, 8 stacked,
    `dark:bg-foreground` present** — matching the suite exactly. A broader
    `dark:*` sweep found no `dark:` paint token the suite's regex misses (the
    only "extra" hits were trailing quote characters).
  - Floors fire for real: the `.css`-only `SCANNABLE` mutant reddens the
    directory-coverage and scanner cases; the swallow mutants redden directory
    coverage. The ≥200/≥1/≥1/≥1 floors are as R4 specifies.
  - **Same-rule gate and paint**, the clause R4 singles out, is independently
    defended. Mutant H changed the paint scan from `gated.some(...)` to
    `matched.some(...)` — gate from one rule, paint from another — and "never
    takes the gate from one rule and the paint from another" went red. Mutant G
    deleted the gate filter entirely: that case plus "rejects an ungated
    bg-foreground" went red.

- [x] **R5** — the checker can fail, and is not decoration.
  - All four rejections and the accept pass as written on the installed
    Tailwind: `dark:text-sm` → `wrong-property`, `dark:bg-[url('/x.png')]` →
    `wrong-property`, `dark:bg-nosuchcolour` → `no-rule`, `bg-foreground` →
    `not-gated`, `dark:bg-foreground` → `painted`, empty list → throws.
  - I tried to defeat them. A checker that returns a verdict without reading the
    sheet (`if (sheet.length >= 0) return "painted";` at the top of `verdict`)
    turned **6 cases red**: all four rejections, the hand-written gate/paint
    sheet, and the sentinel. Making the paint check ignore the property name
    turned 3 red. Deleting the empty-list throw turned "throws on an empty token
    list" red. The negative controls bite.

- [x] **R6** — the mutation that proves the task. Run by me, not read about.
  - `grep -c "dark:bg-foreground" TenantHeaderLogo.tsx` → **2** (line 85 doc
    comment, line 91 `className`).
  - I replaced **both** with the assembled form
    (`className={\`… dark:bg-${"foreground"}\`}` and the same inside the
    comment). `grep -c` → **0**, confirmed before vitest ran.
  - New suite went **red**, two named cases:
    - "keeps token-bearing test files out of every token's provenance" —
      `expected [] to include 'features/user-administration/components/…'`
    - "clears the structural floors" —
      `expected [ 'dark:bg-amber-500/20', …(57) ] to include 'dark:bg-foreground'`
  - **APRAS-110's own `TenantHeaderLogo.test.tsx` stayed green at 18/18 against
    the identical mutant.** That is the whole point of this task, observed
    directly: the class-list render assertion cannot distinguish a token that
    reaches Tailwind from one that does not, and the new suite can.
  - Extra probe I ran beyond the brief: mutating **only** the `className` and
    restoring the comment leaves the guard green (99 passed, `grep -c` = 1).
    That is correct, not a hole — Tailwind's scan reads comment text, so with
    the comment literal present the production sheet really does still carry
    the rule and the plate really is still painted. The guard tracks the
    production fact rather than the source form, which is the right semantics.
  - Restored from a pre-mutation copy; `grep -c` → **2** and
    `shasum` back to `ec6b5aefd9fec867b0a06913dfbdc0c34dcaea73`, `git diff` for
    the file empty.

- [x] **R7** — `npm run test:coverage` exits 0, thresholds met, no newly failing file; `npm run build` exits 0.
  - `npm run test:coverage` → **EXIT=0**, `Test Files 199 passed (199)`,
    `Tests 2693 passed (2693)`. Against the 198/2594 baseline that is exactly
    +1 file and +99 tests — the new suite and nothing else. Zero failures, so no
    newly failing file.
  - Coverage summary: statements 91.73%, branches 85.67%, functions 87.95%,
    lines 92.44% — all above the configured 80/78/76/80 thresholds, and vitest
    emitted no threshold error (it would have made the exit non-zero).
  - `npm run build` → **EXIT=0** (only the pre-existing >500 kB chunk advisory).

- [x] **R8** — lint reports no more errors than the baseline.
  - Installed linter is **eslint v9.39.4**, not the 10.11.0 the lock pins. Its
    figure: **370 problems (368 errors, 2 warnings)**.
  - Because R8 names a 10.11.0 baseline, I installed **eslint 10.11.0 into my own
    scratch directory** and ran it against the same tree. Its figure is
    identical: **370 problems (368 errors, 2 warnings)**.
  - So: 368 errors on both linters, against a stated baseline of 370 errors —
    two **fewer**, and the condition "no more errors than the baseline" holds on
    the version the baseline names.
  - Neither `darkVariantCompile.test.ts` nor `helpers/tailwindSheet.ts` appears
    anywhere in either lint log: the new files contribute zero problems. I also
    checked the two-error gap is not caused by this change — I wrote the HEAD
    version of `themeTokenCompile.test.ts` back to its path and linted it with
    10.11.0: clean, zero problems, same as the staged version. The gap is
    elsewhere in the tree and predates this task. File restored and verified
    byte-identical.

## Blocking Findings

None.

## Suggestions

- The quoted 372/370/2 lint baseline is two errors stale against both linters on
  this tree. Worth re-measuring whenever APRAS-127 reconciles the lockfile, so
  the next task does not inherit a baseline it cannot reproduce.
- `verdict`'s `matched` filter accepts `rule.selector === selector ||
  startsWith(selector + ":")`. A hypothetical Tailwind that emitted the variant
  as a descendant or attribute join rather than a pseudo-class suffix would fall
  out of `matched` and read as `no-rule` — a loud failure rather than a silent
  pass, so this is a note for a future version bump, not a defect.
- The `≥1 bg / ≥1 text / ≥1 stacked` floors are very loose on their own; what
  actually guards against a shrinking token set is the directory-coverage case.
  That is sound and documented in the suite, but the floors read stronger than
  they are.

## Environment left as found

`git status --short` in the worktree is unchanged: four staged paths plus the
untracked developer report. `git diff` against the index is empty. Every file I
mutated (`TenantHeaderLogo.tsx`, `tailwindSheet.ts`, `darkVariantCompile.test.ts`,
`themeTokenCompile.test.ts`) was restored from a pre-mutation copy and verified
by `shasum`. The one file I created in the worktree
(`frontend/vitest.qa125.config.ts`, for the 4.3.3 alias run) was deleted. No
board write, no staging, no commit, no `npm install` in the repository.
