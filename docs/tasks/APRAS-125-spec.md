# APRAS-125 — Assert `dark:`-gated paint tokens reach Tailwind, not just the class list

Revision 2, after spec review round 1 (`docs/reviews/APRAS-125-spec-review.md`,
REJECTED on four findings). Every emission figure below has been re-measured
against **both** Tailwind 4.2.4 and 4.3.3 — see §0.

## Scope

APRAS-110 shipped `frontend/src/features/user-administration/components/TenantHeaderLogo.tsx`,
whose logo plate carries one paint token, `dark:bg-foreground`, inside a single
literal class string. Its suite asserts the plate's class list **equals** the
five expected classes, in a light render and inside a `.dark` ancestor. That
assertion is strong and still cannot do the job: replacing the literal with an
assembled token — `` `dark:bg-${"foreground"}` `` — keeps the class list
identical while generating **no CSS**, because Tailwind v4 finds utilities by
scanning **source text** and an assembled token never appears there. jsdom runs
no Tailwind, so no test in the frontend suite can tell the two renders apart.

This task adds a compile-time guard that can: it extracts the `dark:`-gated
paint tokens from the **shipped** sources on disk, compiles `src/index.css`
through Tailwind's own `compile()` over exactly those tokens, and asserts each
one yields a dark-gated rule with a real paint declaration.

**Out of scope.** No change to any component, to `src/index.css`, or to
`TenantHeaderLogo.test.tsx`'s existing 18 cases. No Playwright, Storybook or
computed-style testing. No new runtime dependency. No `dark:`-gated utility
family other than `bg-*` and `text-*` (§3). No arbitrary-value tokens (§6). No
UI: this task ships nothing visible, so **no `docs/tasks/APRAS-125-mock.html`
is warranted**.

## 0. Which Tailwind, and why this section exists at all

`frontend/node_modules` holds **tailwindcss 4.2.4**; `frontend/package-lock.json`
pins **4.3.3**, which is what `npm ci` installs and therefore what CI runs. The
two emit the `dark:` variant differently, and revision 1 of this spec measured
the stale one while attributing the result to the pinned one — the identical
mistake §8 documents for eslint:

```
4.2.4 (stale in this checkout)   .dark\:bg-foreground { &:is(.dark *) { background-color: … } }
4.3.3 (lockfile, CI)             .dark\:bg-foreground:is(.dark *) { background-color: … }
```

4.3.3 flattens `@custom-variant dark (&:is(.dark *))` into the parent selector;
4.2.4 nests it. A checker that matches a rule whose selector **equals**
`"." + escape(token)` matches 59/59 tokens on 4.2.4 and **0/59** on 4.3.3 — green
on a developer tree and red in CI. Under 4.2.4 the eight stacked tokens nest
their declarations inside `@media (hover: hover)` as well.

Therefore the guard **must not encode either emission shape** (§2), and:

- before quoting any emission result, the implementer and QA run
  `node -p "require('tailwindcss/package.json').version"` in `frontend/` and
  state what it printed, exactly as §8 requires for eslint;
- the figures in this spec were measured on **both** versions, with the
  resolution of §2, and hold on both: 59/59 tokens matched, 59/59 dark-gated,
  zero failures. The suite must be green on whichever of the two is installed.

## 1. Why the obvious guard does not work, and what replaces it

APRAS-110's review proposed compiling `src/index.css` and asserting the sheet
contains the `dark:bg-foreground` rule. APRAS-110's QA executed that and found
it **defeats itself**: the test file's own literal `dark:bg-foreground` is
inside Tailwind's scanned set, so the rule survives in the emitted sheet even
when the component assembles its token. The guard would pass on exactly the
mutant it exists to kill.

The repair is that **this suite never lets Tailwind scan anything.**
`compiler.build(candidates)` takes the candidate list as an argument and reads
no filesystem candidates, so the "scanned set" is entirely this suite's own
construction. Verified on both versions: with a freshly constructed compiler,
`build(["dark:bg-red-500"])` emits no `.dark\:bg-foreground` rule and
`build([])` emits no utility rules at all. The guard therefore runs **two
compiles over disjoint candidate sets**:

- **Compile A, the fixture compile.** Candidates are a literal array declared
  in the test file. It is the positive control on the harness (R1), the carrier
  of the negative controls (§4), and the carrier of the sentinel (§2). It says
  nothing about any component.
- **Compile B, the scanned compile.** Candidates are exactly the tokens the
  extractor found in the shipped source files. The test file is not in the
  scanned file list, and Compile A's array is never merged in.

This makes the guard deliberately **stricter than the production build**: the
real Vite build lets Tailwind auto-scan the whole project, test files included,
and is for that reason blind to the mutant. That asymmetry is the point.

### Disjointness is a mechanism, not a wish

One `compile()` instance **accumulates candidates across `build()` calls** —
measured on both 4.2.4 and 4.3.3: after `build(["dark:bg-foreground"])`, a later
`build(["dark:bg-red-500"])` on the same instance still contains
`.dark\:bg-foreground`. `compileIndexCss` is an obvious thing to memoize, the
compile being the slow part, and a memoized compiler silently re-creates the
APRAS-110 leak: the fixture's literal would prop up the rule in the scanned
sheet and the per-token assertions would pass for the wrong reason.

So: **`compileIndexCss` constructs a fresh `compile()` on every call and caches
nothing.** This is a stated contract of the helper, in a code comment, because
the helper is shared with `themeTokenCompile.test.ts`. And it is asserted, not
merely written down: the fixture array carries a **sentinel**,
`dark:bg-fuchsia-300`, which exists nowhere in `src` (confirmed: not among the
59), and a case asserts the **scanned** sheet contains no rule for it. That one
assertion is the mechanical proof of the disjointness the design rests on; it
holds today on both versions and fails the moment anything is cached.

## 2. The reader, shape-agnostic

**The scanned set.** Walk `frontend/src` recursively
(`readdirSync(SRC, { recursive: true })`, no new dependency). Keep a path only
if its extension is `.ts`, `.tsx` or `.css` **and** none of these hold:

- any path segment is `__tests__`, `test`, `__mocks__` or `__fixtures__` — the
  `test` segment is what excludes `src/test/setup.ts`, and `__tests__` is what
  excludes both `src/__tests__/**` and every co-located feature test directory;
- the basename matches `/\.(test|spec)\.(ts|tsx)$/`;
- the basename ends `.stories.tsx` or `.d.ts`.

That is **276** files today.

**The extractor.** Over each scanned file's text, match
`/dark:(?:[a-z-]+:)*(?:bg|text)-[A-Za-z0-9][A-Za-z0-9./_-]*/g` — a `dark:`
prefix, any further stacked variants, and a final `bg-*` or `text-*` utility,
opacity modifiers included. Build a **provenance map** token → sorted list of
the scanned files it was found in; the candidate list is that map's keys.
The grammar's shape matters: it rejects the non-utility `dark:` occurrences in
these sources (a `dark:/g` fragment in `src/lib/brandPalettePaste.ts`, prose
like `dark:-gated`) which would otherwise enter the candidate list and fail to
compile. Today the map holds **59** distinct tokens: 8 stacked
(`dark:hover:bg-white/10` and friends), 58 palette classes and one theme token,
`dark:bg-foreground`.

**Effective selectors.** The reader must find a token's rule on either emission
shape, so it resolves an *effective* selector rather than reading the sheet's
literal nesting:

1. strip `/* … */` comments **before** parsing, so a selector appearing in a
   comment can never match;
2. brace-scan; at every `{`, discard the prelude text accumulated since the
   last `;` or `}` if it begins with `@` — an at-rule (`@layer`, `@media`,
   `@supports`) contributes no selector, and its body is parsed with the
   **parent** selector carried through unchanged;
3. for a non-at-rule, the effective selector is its own text with `&` replaced
   by the parent selector, or the parent plus a descendant combinator when
   there is a parent and no `&`;
4. recurse into every rule body, so nested rules are emitted too.

A token `t` **matches** the rules whose effective selector equals
`"." + escape(t)` or starts with `"." + escape(t) + ":"`. `escape` escapes `:`,
`/`, `.`, and the `[ ] ( ) ' #` an arbitrary value would carry — note the
existing `escapeClass` in `themeTokenCompile.test.ts` does **not** escape `:`
and must not be reused here; it would fail every `dark:` token.

**The gate and the paint must be the same rule.** Of the matched rules, keep only
the **gated** ones: those whose effective selector **starts with**
`"." + escape(t) + ":is(.dark *)"` — i.e. the rule really is conditioned on a
`.dark` ancestor and not emitted unconditionally. The `startsWith` form rather
than equality, because a stacked token's selector continues past the gate
(`.dark\:hover\:bg-white\/10:is(.dark *):hover`). A token with no gated rule
fails. Measured 59/59 gated on both versions.

The paint declaration must then be found **inside the subtree of a gated rule**,
never anywhere in the token's matched set. Stated that way deliberately: a
token's matched set can hold several rules, and a checker that took the gate
from one and the paint from another would accept a token that is gated but
unpainted in the dark, or painted but ungated. The stricter form is one
`.filter()` and costs nothing — measured 59/59 with zero failures on both
versions, and the four §4 controls unchanged.

**"Compiles to a non-empty declaration"**, tight enough that nothing vacuous
satisfies it. For each **gated** rule, collect `declarationsDeep` — `name: value`
pairs at **any** nesting depth below it, with at-rule preludes discarded at the
`{` (this is what stops `@supports (color: color-mix(in lab, …))` from being
harvested as a bogus `color` declaration). Require at least one pair whose
property is **exactly** `background-color` for a `bg-` token or **exactly**
`color` for a `text-` token, and whose value has non-zero length after `trim()`.
The depth-blind harvest is required, not a convenience: on **both** versions the
eight stacked tokens keep their declaration below the gated rule inside
`@media (hover: hover)`, and a depth-0 reader fails all eight on 4.2.4. That the
same mechanism absorbs 4.2.4's `&:is(.dark *)` nesting for free is why the
dual-version contract needs no version check and no branch anywhere in the
implementation.

An empty rule, a zero-length value, a rule carrying only the other property, a
missing rule, an ungated rule, a paint that lives outside the gated subtree and
a match inside a comment all fail. **All 59 tokens pass on 4.2.4 and on 4.3.3.**

**R1's selector.** For the unstacked `dark:bg-foreground` the stronger form
holds on **both** versions: a matched effective selector **equals**
`.dark\:bg-foreground:is(.dark *)` — on 4.3.3 as the rule's own selector, on
4.2.4 as the nested `&:is(.dark *)` block resolved against its parent. So R1
keeps that exact string while pinning neither nesting shape.

## 3. Why `bg-*` and `text-*` only

A missing `dark:bg-*` or `dark:text-*` is **silently invisible**: the element
inherits and still renders. `bg` and `text` are also the two families
`docs/frontend/theme-token-mapping.md` §1b–1e migrates, and the only ones with
theme-token call sites — the 14 `dark:border-*` / `dark:divide-*` classes in the
tree are all palette values with nothing for the guard to protect.

Widening costs **a line in the alternation and a line in the per-prefix property
map** (`border-color` for `border-*`, and `divide-*` emits on a
`:where(… > :not(:last-child))` selector, which the effective-selector matcher
would also need to admit). Not one character. The alternation and the property
map are written adjacent to each other, with a comment saying both must move
together, because an understated extension cost is how a guard stops being
extended.

`text-*` is not purely a colour family: `dark:text-sm` compiles to
`font-size`/`line-height` and no `color`. No such token exists in the sources
today, and rather than leave that as a comment it is a **live negative
control** (§4).

## 4. The negative controls — proving the checker can fail

Naming every token in `it.each`, flooring the inputs and throwing on an empty
list are all satisfied by a checker that returns `true` unconditionally, and
Compile A is explicitly a *positive* control. This repository's governing
failure mode is "a check that could not have failed", so the guard must assert
its own discriminating power. The fixture compile therefore carries four
candidates whose outcomes are asserted individually, all four measured on both
Tailwind versions:

| candidate | emitted | checker must |
|---|---|---|
| `dark:bg-foreground` | `background-color: var(--color-foreground)` | **accept** |
| `dark:text-sm` | rule exists; `font-size` + `line-height` only | **reject** (wrong property) |
| `dark:bg-[url('/x.png')]` | rule exists; `background-image`, no `background-color` | **reject** (wrong property) |
| `dark:bg-nosuchcolour` | no rule at all | **reject** (missing rule) |

Correcting the review on one point of fact: `dark:bg-[url('/x.png')]` **does**
emit a rule on both 4.2.4 and 4.3.3, so it exercises the wrong-property branch,
not the missing-rule branch. `dark:bg-nosuchcolour` is the missing-rule control.
All four live only in the fixture array; none may be merged into the scanned
candidate list.

The empty-list behaviour stays as well: the checker is written to **throw** on
an empty token list, and a case asserts it throws.

## 5. Anti-vacuity floors

The per-token cases are `it.each(tokens)`, so the run output **names every token
checked** — but `it.each` over an empty array registers no cases and a suite with
no cases is green. A bare count floor is too slack to notice a broken grammar:
dropping the `(?:[a-z-]+:)*` group loses exactly the 8 stacked tokens (59→51)
and dropping `text` loses 26 (59→33), and both still clear any count a
palette→token migration would survive. So the floors are **structural**, and one
case asserts all of them:

- at least **200** scanned files (276 today, and the count only grows);
- at least one `dark:bg-*` token and at least one `dark:text-*` token;
- at least one **stacked** token (two or more `:` before the utility);
- `dark:bg-foreground` present in the extracted set.

These catch grammar regressions a count cannot, and they survive the
palette→token migration that will keep deleting `dark:text-slate-*` classes.

**R3's required literal.** A `REQUIRED_LITERALS` table, one entry today:
`dark:bg-foreground` must appear in the provenance map **with
`features/user-administration/components/TenantHeaderLogo.tsx` among its
files**, and must compile. This is what makes the assembled-token mutant red —
the mutant removes the token's text from the shipped sources, the extractor
stops finding it, and the provenance assertion fails. Without this table the
mutant would merely shrink the candidate list and nothing would notice.

**The exclusion, asserted.** One case asserts the scanned file list contains no
path with a `__tests__` / `test` / `__mocks__` / `__fixtures__` segment, none
matching `/\.(test|spec)\.tsx?$/`, no `*.stories.tsx` and no `*.d.ts`; and
positively that it contains `TenantHeaderLogo.tsx` and `index.css`. A second
asserts that **no file in any token's provenance is an excluded path** — stated
that way rather than "the provenance of `dark:bg-foreground` is exactly
`TenantHeaderLogo.tsx`", which encodes an accident and would redden for a second
legitimate call site. `dark:bg-foreground` also appears in
`TenantHeaderLogo.test.tsx`, so this is the direct evidence that the test
literal is outside the scanned set.

**What this guard still cannot prove.** That the literal sits in a `className`
rather than in a code comment — `TenantHeaderLogo.tsx` carries
`dark:bg-foreground` twice, at line 91 in the class string and at line 85 in a
doc comment. Tailwind's own extractor cannot tell them apart either: comment
text is a real candidate source in the production build, so a comment literal
genuinely emits the class and the plate genuinely paints. The property guarded —
"the token's text is present in shipped source and compiles to paint" — is
therefore the true property, not a proxy for it. The gap that remains (token
present but on the wrong element) is covered by `TenantHeaderLogo.test.tsx`'s
class-list equality. Neither suite is complete alone; the pair is.

## 6. Files touched

- `frontend/src/__tests__/helpers/tailwindSheet.ts` — **new**.
- `frontend/src/__tests__/themeTokenCompile.test.ts` — imports from the helper;
  its own cases unchanged.
- `frontend/src/__tests__/darkVariantCompile.test.ts` — **new**;
  `// @vitest-environment node`, the scanner, the extractor, the checker and the
  cases.

### The seam, stated exactly

Revision 1 called this a "verbatim move"; it is not one, and that framing is
withdrawn. `themeTokenCompile.test.ts` has no `compileIndexCss` — it has
`build(candidates): Promise<Sheet>` at line 409, which inlines `loadStylesheet`,
calls `compile()`, **and** constructs the `Sheet` (`rule`/`variable`/`colourOf`
and the `:root`-selection logic with its two documented requirements). The
helper exports:

- `SRC` and `FRONTEND_ROOT`, derived from the helper's own `import.meta.url` —
  the file sits one directory deeper than the current constants, so
  `path.resolve(HERE, "..", "..")` is `src` and its parent is `frontend`. A
  literal copy of the existing `HERE`/`SRC`/`FRONTEND_ROOT` lines would be
  wrong by one level.
- `compileIndexCss(candidates: readonly string[]): Promise<string>` — the
  `loadStylesheet` resolver, the `compile()` call and `compiler.build([...])`,
  lifted out of the first half of `build()` (lines 409–427), returning the CSS
  string. The seam is immediately before `const parsed = rules(css)`: everything
  from there down — `Sheet`, the `:root` selection, `variable`, `rule`,
  `colourOf` — **stays in `themeTokenCompile.test.ts`**. Contract, in a comment:
  a fresh `compile()` per call, no caching (§1).
- `rules(css)` and `declarations(body)` — moved **unchanged**, keeping the
  `@layer`-only flattening and the depth-0 declaration semantics that
  `themeTokenCompile.test.ts` §1i and its last-unqualified-`:root` selection
  depend on.
- `rulesDeep(css)`, `declarationsDeep(body)` and `escape(token)` — **new**
  readers placed beside the old ones, never modifications of them. The new guard
  uses only these three; `themeTokenCompile.test.ts` uses only the old two. That
  is what makes "`themeTokenCompile.test.ts` stays green" a meaningful proof
  rather than a proof about a function this task changed under it.

The helper must contain no `dark:bg-*` / `dark:text-*` literal. It is under
`__tests__`, so vitest's default `include` will not collect it as a suite and
§2's exclusion rules keep it out of the scanned set. It **is** inside
`vitest.config.ts`'s `coverage.include: ["src/**/*"]` and matches none of the
excludes (which cover `src/test/**`, `**/*.test.ts`, `**/*.test.tsx` but not
`src/__tests__/helpers/**`), so it becomes coverage-instrumented code for the
first time — see §7.

A new test file rather than more cases in `themeTokenCompile.test.ts`: that
file's subject is the ΔL/ΔE mapping table and it compiles one fixed candidate
set in a single `beforeAll`; this guard compiles two further disjoint sets, and
merging the `beforeAll`s is how a candidate list leaks from one into the other.

**Arbitrary-value tokens are a known, named hole.** `dark:bg-[#fff]`,
`dark:bg-[var(--x)]` and the like are not matched by the extractor's grammar
(`[` is outside the character class), so such a class would never be guarded and
no floor would notice. None exists in the tree today. Stated here rather than
left implied; widening the grammar to brackets is a separate task.

## 7. Test criteria

- `npx vitest run src/__tests__/darkVariantCompile.test.ts` green, listing one
  named case per extracted token.
- **CI's command, not a weaker one**: `npm run test:coverage` in `frontend/`
  (`.github/workflows/ci.yml` runs `npm ci` then `npm run test:coverage`) exits
  0 with the 80/78/76/80 thresholds still met. The baseline is **198 files /
  2594 tests, all passing**; the new helper is instrumented for the first time
  and is almost fully executed, so the thresholds should hold, but they are a
  gate and must be reported.
- `npm run build` exits 0.
- `npm run lint` within the §8 bound.
- Both Tailwind versions are acceptable, and the installed one is printed and
  reported before any emission figure is quoted (§0).

### The mutation proof, mandatory, with its six outputs reported

Six shipped checks in this repository have been vacuous — a `grep -c` on text
that had moved, a class-list equality with no CSS behind it,
`assert len(set) == 1` over a one-element set, a sweep asserting only an HTTP
status, a byte check in a single-state call, and twice a guard satisfied by
comment prose in the asserted file. This task is a remedy for that failure mode
and must not join it.

1. In `TenantHeaderLogo.tsx`, replace the line-91 literal with a template string
   built from a variable **and** remove the token's text from the line-85 doc
   comment — either literal alone keeps the token in the scanned set and the
   guard stays green, which would be misread as the guard being vacuous when in
   fact the mutation was incomplete.
2. `grep -c 'dark:bg-foreground' src/features/user-administration/components/TenantHeaderLogo.tsx`
   must print `0` — the mutation took effect on disk.
3. Run the new file: it must be **red**, and the report names which case failed
   (the `REQUIRED_LITERALS` provenance case).
4. Restore with `git checkout -- <that one path>` — never `git stash`, the
   worktrees hold uncommitted work and stash refs are repo-global.
5. The same `grep -c` must print `2` again.
6. Re-run the file: green.

## Expected Results

- [ ] A node-environment vitest case compiles `src/index.css` through a **fresh**
      Tailwind `compile()` over a fixture candidate list and asserts
      `dark:bg-foreground` resolves to an effective selector exactly
      `.dark\:bg-foreground:is(.dark *)` carrying a non-empty `background-color`,
      on whichever nesting shape the installed Tailwind emits.
- [ ] A case asserts the scanned file list excludes every `__tests__`, `test`,
      `__mocks__`, `*.test.*`, `*.spec.*`, `*.stories.tsx` and `*.d.ts` path, and
      a second asserts no file in any token's provenance is such a path while
      `dark:bg-foreground`'s provenance contains `TenantHeaderLogo.tsx`.
- [ ] `compileIndexCss` constructs a fresh `compile()` per call with no caching,
      proved by a case asserting the fixture-only sentinel `dark:bg-fuchsia-300`
      has no rule in the scanned sheet.
- [ ] Every extracted `dark:bg-*` / `dark:text-*` token gets its own named case
      asserting a gated rule whose effective selector starts
      `.<token>:is(.dark *)` and whose **own subtree** declares a non-empty
      `background-color` (or `color`), with structural floors of ≥200 scanned
      files, ≥1 `bg`, ≥1 `text`, ≥1 stacked token and `dark:bg-foreground`
      present.
- [ ] Cases prove the checker can fail: it rejects `dark:text-sm` and
      `dark:bg-[url('/x.png')]` for the wrong property, rejects
      `dark:bg-nosuchcolour` for having no rule, accepts `dark:bg-foreground` in
      that same fixture compile, and throws on an empty token list.
- [ ] Replacing both `dark:bg-foreground` literals in `TenantHeaderLogo.tsx`
      with an assembled token turns the new file red, with the mutation
      confirmed on disk by `grep -c` printing 2 → 0 → 2 across the restore.
- [ ] `npm run test:coverage` in `frontend/` exits 0 with the 80/78/76/80
      thresholds met and no newly failing file against the 198-file / 2594-test
      baseline, and `npm run build` exits 0.
- [ ] `npm run lint` reports no more errors than the eslint **10.11.0** baseline
      `372 problems, 370 errors, 2 warnings`.

## 8. The eslint baseline and which eslint produced it

The baseline is **372 problems, 370 errors, 2 warnings**, measured with eslint
**10.11.0** — the version `frontend/package-lock.json` pins and a clean
`npm ci` installs.

The main checkout's `node_modules` is stale at eslint **9.39.4**; running
`npm run lint` there today prints `370 problems (368 errors, 2 warnings)`, two
fewer errors in two fewer files on the same tree. This project has quoted the
two figures interchangeably for a week. So: run `npx eslint --version` and quote
the baseline that matches it. A `370/368/2` reading is not an improvement; it is
the older eslint. §0 applies the same discipline to Tailwind, whose drift this
spec's first revision fell into.

## Out of Scope

- Any production-code change. `TenantHeaderLogo.tsx` is edited only by the
  mutation proof and restored.
- `dark:border-*`, `dark:divide-*`, `dark:ring-*`, `dark:from-*` and the rest of
  the `dark:`-gated utilities (§3).
- Arbitrary-value tokens such as `dark:bg-[#fff]` or `dark:bg-[var(--x)]`, which
  the grammar does not match and no floor notices; none exists today (§6).
- Proving a token sits in a `className` rather than a comment, which Tailwind
  itself does not distinguish (§5).
- Upgrading `node_modules` to the lockfile, for Tailwind or eslint. The guard
  must pass on both installed versions; reconciling the tree is its own task.
- Computed-style assertions, visual regression, and any new dependency.
