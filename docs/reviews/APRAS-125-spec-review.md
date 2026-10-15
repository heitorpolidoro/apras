# APRAS-125 — spec review, round 1

Spec under review: `/Users/heitor/workspace/apras/docs/tasks/APRAS-125-spec.md` (279 lines, untracked).
Tree: `/Users/heitor/workspace/apras`, local `master` = `4be622b`. Nothing staged, nothing
committed, nothing in the tree mutated by this review (all probes ran in
`/private/tmp/claude-501/-Users-heitor-workspace-apras/06230b8a-d0ef-40dd-929b-83bb4eb6abbf/scratchpad/specrev125`).

**VERDICT: REJECTED** (four blocking findings). The core idea is sound and I verified
it escapes the APRAS-110 trap. What fails is that the spec's central emission premise
was measured against the wrong Tailwind — the one stale in `node_modules`, not the one
the lockfile pins and CI installs — and under the pinned version the checker as written
matches **0 of 59** tokens.

---

## 1. What I verified by execution

### 1a. The design does escape the APRAS-110 trap (claim confirmed)

`compiler.build(candidates)` takes the candidate list as an argument and Tailwind
does **not** read the filesystem for candidates. With a freshly constructed compiler:

| probe | result |
|---|---|
| `build(["dark:bg-foreground"])` | `.dark\:bg-foreground` rule present |
| `build(["dark:bg-red-500"])` | `.dark\:bg-foreground` **ABSENT** |
| `build([])` | sheet 7380 bytes, no utility rules at all |

Confirmed on both 4.2.4 and 4.3.3. So the suite's "scanned set" really is its own
construction, a literal in a test file cannot keep a rule alive here, and the APRAS-110
defeat (the test file's own literal propping up the sheet) does not apply. This is the
most important claim in the spec and it holds.

With one caveat that the spec does not close — see blocking finding 3.

### 1b. Every counted number in the spec is exactly right

Re-implemented the spec's scanner and extractor verbatim:

- scanned files: **276** (`src/test/setup.ts` and `src/__tests__/**` excluded by the
  `test` / `__tests__` segment rules);
- distinct tokens: **59**, of which **8** stacked (`dark:hover:bg-white/10`,
  `dark:hover:text-emerald-400`, …), 58 palette + `dark:bg-foreground`;
- provenance of `dark:bg-foreground`: **exactly**
  `features/user-administration/components/TenantHeaderLogo.tsx`;
- `grep -c 'dark:bg-foreground' .../TenantHeaderLogo.tsx` → **2** (line 91 `className`,
  line 85 doc comment), and `1` in
  `src/features/user-administration/__tests__/TenantHeaderLogo.test.tsx`;
- the grammar does reject the non-utility `dark:` occurrences; the `dark:` fragments it
  drops are the `dark:/g` one and 14 `dark:border-*` / `dark:divide-*` classes, i.e.
  exactly the declared out-of-scope families and nothing a `bg`/`text` guard wants.

Baseline measured for R5: `npx vitest run` in `frontend/` is **198 files / 2594 tests,
all passing, exit 0**.

eslint claims confirmed: `npx eslint --version` → **9.39.4**; `package-lock.json` pins
**10.11.0**; `tailwindcss` installed is **4.2.4** while the lock pins **4.3.3**.

### 1c. The comment-occurrence worry is *not* an instance of the repo's failure mode

I expected to find the historical shape here ("a guard satisfied by comment prose in
the asserted file") and it is not. The doc comment at `TenantHeaderLogo.tsx:85` is a
*legitimate* candidate source: Tailwind's production scan reads comment text, so if the
`className` were assembled but the comment literal remained, the class **would still be
emitted** and the plate **would still paint**. The property the guard asserts — "the
token's text is present in shipped source and compiles to paint" — is therefore the
true property, not a proxy for it, and the spec's §1 "what this guard still cannot
prove" reasoning is correct. Its demand that the mutation proof remove *both* literals
is right for the same reason: removing one does not change the painted result.

The gap that remains (token present but on the wrong element) is covered by
`TenantHeaderLogo.test.tsx`'s class-list equality, as the spec says. I accept the pairing
argument.

---

## 2. Blocking finding 1 — the emission premise is false on the version CI installs

The spec states as verified fact (§1 "R1's selector, and the nesting surprise", and
"verified against `tailwindcss` 4.3.3" twice) that `compile()` emits nested CSS and that
R1 must compose outer + nested selector. I measured both versions against the real
`src/index.css`:

```
4.2.4 (installed in this checkout):
  .dark\:bg-foreground { &:is(.dark *) { background-color: var(--color-foreground); } }

4.3.3 (what package-lock.json pins):
  .dark\:bg-foreground:is(.dark *) { background-color: var(--color-foreground); }
```

4.3.3 **flattens** the `@custom-variant dark (&:is(.dark *))` into the parent selector.
Consequences, measured:

- the spec's checker step 2 — "find the rule whose selector **equals** `"." + escape(t)`"
  — matches **0 of 59** tokens under 4.3.3 (I ran the spec's own rules: `59 failures,
  all "NO RULE"`). Under 4.2.4 it matches 59/59.
- R1 as specified is unimplementable under 4.3.3: there is no nested block to compose,
  the outer selector already *is* `.dark\:bg-foreground:is(.dark *)`.
- additionally, under 4.3.3 the 8 stacked tokens' rules sit **inside**
  `@media (hover: hover)`, and the moved `rules()` reader flattens only `@layer`, so
  those rules are not even top-level entries.

`.github/workflows/ci.yml` runs `npm ci` (line 338 → installs 4.3.3) and
`npm run test:coverage` (line 348). So the file the spec describes would be **green on
this developer tree and red in CI**. The spec's probes were evidently run against the
stale 4.2.4 `node_modules` while the spec attributes them to 4.3.3 — the identical
mistake the spec itself calls out for eslint in §R6, made for Tailwind.

The spec is salvageable and the repair is cheap. I verified a shape-agnostic checker
passes **59/59 on both 4.2.4 and 4.3.3**:

- collect rules with an *effective selector*: descend into at-rules
  (`@layer`, `@media`, `@supports`) carrying the parent selector through, and substitute
  `&` with the parent when a nested rule has one;
- match a token by effective selector `"." + esc(t)` **or** anything starting
  `"." + esc(t) + ":"`;
- `esc` must escape `:`, `/` and `.`;
- collect declarations at any depth, **discarding at-rule preludes at the `{`** (this is
  what stops `@supports (color: color-mix(in lab, red, red))` from ever being harvested
  as a `color` declaration);
- as a free bonus the same resolution lets the suite assert `:is(.dark *)` is present in
  the matched effective selector **for all 59 tokens** (I measured `dark-gated 59` on
  both versions). Today only R1's single token checks the gate at all; the other 58
  cases never verify the rule is dark-gated. That assertion should be in the per-token
  case.

The spec must also say which Tailwind the implementer is to run against, and tell them
to run `npm ci` or at least print `node -p "require('tailwindcss/package.json').version"`
before quoting results — the same instruction §R6 already gives for eslint. And ER1 must
stop pinning the nested shape.

For the record, the version drift is confined to `dark:` variants: `bg-primary/90` emits
byte-identically on 4.2.4 and 4.3.3, which is why `themeTokenCompile.test.ts` is green on
both and nobody noticed.

## 3. Blocking finding 2 — no negative control: nothing proves the checker can fail

The anti-vacuity section has three devices and none of them is a negative control:
`it.each` naming tokens proves cases ran, the floor proves the inputs are not empty, the
empty-list throw proves the guard refuses an empty list. All three are satisfied by a
checker that **returns true unconditionally**. A one-line bug (matching substring instead
of equality, defaulting `want` wrongly, `.some()` over an empty array negated) passes all
six expected results. Compile A is explicitly a *positive* control on the harness.

This repository's governing failure mode is precisely "a check that could not have
failed". A spec whose purpose is to remedy that must assert its own discriminating power.
Add a case feeding the checker a candidate known to compile **without** the expected
property and asserting it is rejected. Two measured candidates:

- `dark:text-sm` → rule exists, declarations are `font-size` + `line-height` only; the
  checker must reject it (the spec already names this case in §2 as a future hazard —
  make it a live assertion instead of a comment);
- `dark:bg-[url('/x.png')]` → no rule emitted at all; exercises the missing-rule branch.

Both must be fixture-only candidates (same disjointness rule as Compile A).

## 4. Blocking finding 3 — candidate accumulation across `build()` calls is unasserted, and defeats the disjointness claim

§"Why the obvious guard does not work" rests the whole design on "Compile A's array is
never merged into [Compile B]", and promises "the disjointness is itself asserted". The
spec never says *how* disjointness is achieved, and the mechanism it needs is
non-obvious: **one compiler instance accumulates candidates across `build()` calls.**
Measured on both versions:

```
const c = await compile(indexCss, {...});
c.build(["dark:bg-foreground"]);
c.build(["dark:bg-red-500"]).includes(".dark\\:bg-foreground")  // → true, both 4.2.4 and 4.3.3
```

`compileIndexCss(candidates): Promise<string>` is an obvious thing to memoize (the
compile is the slow part, and two compiles per run invite exactly that), and a memoized
compiler silently re-creates the APRAS-110 leak: the fixture's literal
`dark:bg-foreground` would keep the rule alive in the scanned sheet. R3's provenance
assertion is text-based and would still kill the headline mutant, so the guard does not
become fully vacuous — but the per-token compile assertions would be passing for the
wrong reason, which is the same disease one stage milder.

The spec must (a) mandate a **fresh `compile()` instance per candidate list** — stated as
a contract of `compileIndexCss`, since the helper is shared with
`themeTokenCompile.test.ts` — and (b) assert it, not just assert the file-list exclusion:
put a sentinel token in the fixture array that exists nowhere in `src` (e.g.
`dark:bg-fuchsia-300`, absent from the 59) and assert the **scanned** sheet does not
contain its rule. That single assertion is the mechanical proof of the disjointness the
spec currently only asserts in prose.

## 5. Blocking finding 4 — the "verbatim move" does not exist as a unit, and `escape` is undefined

§1 and §3 mandate moving `compileIndexCss`, `rules` and `declarations` "unchanged in
behaviour" / "verbatim" out of `themeTokenCompile.test.ts`. Reading that file, two
implementers would produce materially different refactors:

- there is no `compileIndexCss`. There is `build(candidates): Promise<Sheet>` at line 409,
  which inlines `loadStylesheet`, does the `compile()`, **and** builds the `Sheet`
  (`rule`/`variable`/`colourOf`, the `:root`-selection logic with its two documented
  requirements). Extracting "the compile part" is a split of a function, not a move, and
  the spec does not say where the seam is.
- `HERE`, `SRC` and `FRONTEND_ROOT` are derived from `import.meta.url` and **must change**
  when the code moves one directory deeper (`path.resolve(HERE, "..")` → `"../.."`). A
  literal move is impossible; the spec should say the helper derives its own paths and
  exports them, or takes them as arguments.
- the checker's step 2 says `"." + escape(t)` and never defines `escape`. The nearest
  existing implementation, `escapeClass` (line 406), escapes `/` and `.` but **not `:`** —
  reused as-is it fails every single `dark:` token. It fails loudly rather than silently,
  so this is a round-burner rather than a vacuity hole, but it is an avoidable one.
- interaction with finding 1: once `rules()` must descend into `@media`/`@supports`, the
  move is **no longer behaviour-preserving**, and `themeTokenCompile.test.ts` depends on
  `rules()`'s current output shape (it filters for the *last* unqualified `:root` rule
  declaring `--primary`; adding newly-descended rules can change which one is last). My
  ruling on the arguable decision: **keep the reuse, reject the "pure move" framing.**
  Move `compileIndexCss` and `declarations` (depth-0, untouched), and add `rulesDeep` /
  `declarationsDeep` as **new** readers beside the existing `rules()` rather than
  changing it. "`themeTokenCompile.test.ts` stays green" is then a meaningful proof
  instead of a proof about a function the new guard no longer uses.

---

## 6. Expected results, one by one

Six results on the board; QA sees only these.

1. **R1 (fixture compile, composed selector)** — mechanically checkable, but **wrong as
   written**: it pins the nested emission and is unsatisfiable on the pinned Tailwind
   (finding 1). Must be reworded to assert the token's *effective* selector equals
   `.dark\:bg-foreground:is(.dark *)` however the version nests it.
2. **R2 (exclusions + provenance)** — checkable, and I confirmed both halves hold today.
   Two refinements: the spec says "among its files" in §1/R3 but "names only" /
   "lists exactly" in §1/R2 and in ER2. Both are consistent as two cases, but the
   exactness form encodes an accident — a second legitimate call site reddens it for no
   defect. The property actually wanted is "no file in this token's provenance is an
   excluded/test path", which is non-brittle and is the real evidence. Also ER2 says
   `src/test/**` is excluded while §1's rule achieves that via the `test` path segment —
   state it once.
3. **R3 (mutation proof)** — checkable, well specified, and the six numbered outputs with
   the `grep -c 2 → 0 → 2` bracket are the right shape. `git checkout -- <one path>` with
   the no-stash warning is correct for this tree. Keep.
4. **R4 (per-token cases, floors, empty-list throw)** — checkable, but it is the result
   that most needs finding 2's negative control; as written it is satisfiable by a
   checker that cannot fail. On the floors: **≥200 files is right** (276 today, and the
   count only grows); **≥25 tokens is too slack to notice a broken extractor** — dropping
   the `(?:[a-z-]+:)*` group silently loses exactly the 8 stacked tokens (59→51), and
   dropping `text` loses 31 (59→28); both still clear 25. Replace the bare count with
   structural floors that bite: at least one `dark:bg-*`, at least one `dark:text-*`, at
   least one stacked token, and `dark:bg-foreground` present. Those catch grammar
   regressions a count cannot, and they survive the palette→token migration the spec is
   right to worry about.
5. **R5 (`npx vitest run` green, `npm run build` 0)** — checkable, and the baseline is
   fully green (198 files / 2594 tests), so "no newly failing file" is decidable. Pin
   those two numbers in the spec so QA has an absolute. More importantly, **CI runs
   `npm run test:coverage`, not `npx vitest run`**, and `vitest.config.ts` has
   `coverage.include: ["src/**/*"]` with excludes that cover `src/test/**` and
   `**/*.test.ts` but **not** `src/__tests__/helpers/**`. The moved helper therefore
   becomes coverage-instrumented code for the first time (it is currently inside a
   `.test.ts` and excluded). The thresholds are 80/78/76/80 and the helper will be almost
   fully executed, so the risk is small — but the spec should name CI's command, not a
   weaker one, and say the thresholds must still pass.
6. **R6 (eslint baseline)** — checkable, honest about the two-version mess, and a `≤`
   bound so either reading is safe. Verified both version facts. Keep as is; it is the
   model the Tailwind claim should have followed.

## 7. Scope, YAGNI, and the arguable decision

- **The `bg`/`text` cut is right.** They are the families that degrade invisibly, the
  two `docs/frontend/theme-token-mapping.md` §1b–1e migrates, and the only ones with
  theme-token call sites. The 14 `dark:border-*` / `dark:divide-*` classes in the tree
  are all palette values with no token behind them, so there is nothing for the guard to
  protect there yet.
- **The "one-character widening" claim is inaccurate.** Adding `border` to the
  alternation also requires a `border-color` entry in the per-prefix property map (which
  §2 half-admits two sentences later). Say "a line in the alternation and a line in the
  property map", not one character — an understated extension cost is how a guard stops
  being extended.
- **One silent coverage hole worth naming in Out of Scope**: arbitrary-value tokens.
  `dark:bg-[#fff]` / `dark:bg-[var(--x)]` are not matched by the grammar (the `[` is
  outside the character class), so such a class is never guarded and no floor notices.
  None exists today; the spec should say so explicitly rather than leave it implied.
- **Over-engineering**: the design is proportionate for a guard that has to survive this
  repo's vacuity history. The two-compile structure costs ~15 lines and earns the harness
  control; the provenance map is genuinely sharper evidence than the path-exclusion
  assertion and I would keep it. The one piece I would *not* have mandated is the
  674-line-file refactor — but duplicating a brace scanner is worse, so I uphold the
  author's call, subject to finding 4's reframing.

## 8. Language

Spec is in English throughout, per the project policy. No issue.

## Suggestions (non-blocking)

- Assert `:is(.dark *)` in the matched effective selector for **all** tokens, not just
  the one fixture token (free once finding 1's resolution is in place; verified 59/59).
- Replace ER2's "names only `TenantHeaderLogo.tsx`" with "no excluded/test path appears
  in this token's provenance" — same evidence, not brittle to a second call site.
- Pin the vitest baseline (198 files / 2594 tests) and name `npm run test:coverage`.
- State the Tailwind version the figures were measured against, and have the implementer
  print it before quoting, exactly as §R6 does for eslint.
- Say in §1 that `declarationsDeep` discards at-rule preludes at the `{`; left
  unspecified, a prelude such as `@supports (color: color-mix(...))` is a plausible
  source of a bogus `color` declaration for a `text-*` token.
- Add `dark:bg-[...]`-style arbitrary values to Out of Scope.

---

VERDICT: REJECTED

1. The spec's central emission premise is false on the Tailwind the lockfile pins. Measured: 4.2.4 (stale in this `node_modules`) emits nested `&:is(.dark *)`; 4.3.3 (lockfile, installed by CI's `npm ci`) emits the flattened `.dark\:bg-foreground:is(.dark *)`. Under 4.3.3 the checker's "selector **equals** `"." + escape(t)`" rule matches **0 of 59** tokens and R1 has no nested block to compose, so the suite as specified is green on this tree and red in CI. The spec must resolve selectors shape-agnostically (descend into `@media`/`@supports` carrying the parent selector, substitute `&`, match `.esc(t)` or `.esc(t):…`), reword ER1 off the nested shape, and state/verify the Tailwind version the way §R6 does for eslint. I verified a shape-agnostic checker passes 59/59 on both versions.
2. Nothing in the spec proves the checker can fail. `it.each` naming, the ≥25/≥200 floor and the empty-list throw are all satisfied by a checker that returns true unconditionally; Compile A is explicitly a positive control. Add a negative control asserting a candidate that compiles without the expected property is rejected — measured candidates: `dark:text-sm` (emits `font-size`/`line-height` only) and `dark:bg-[url('/x.png')]` (emits no rule).
3. The disjointness the design rests on is neither mechanised nor asserted. One compiler instance **accumulates** candidates across `build()` calls — verified on 4.2.4 and 4.3.3: after `build(["dark:bg-foreground"])`, a later `build(["dark:bg-red-500"])` still contains `.dark\:bg-foreground`. `compileIndexCss` is an obvious memoization target, and a memoized compiler re-creates the APRAS-110 leak. The spec must mandate a fresh `compile()` per candidate list and assert it with a fixture-only sentinel token asserted absent from the scanned sheet.
4. The mandated "verbatim move" does not exist as a unit and leaves the refactor ambiguous: `themeTokenCompile.test.ts` has `build(): Promise<Sheet>`, not `compileIndexCss`, with `loadStylesheet` inlined and the `Sheet`/`:root` logic attached; `HERE`/`SRC`/`FRONTEND_ROOT` must change when the file moves a directory deeper; `escape` is never defined and the existing `escapeClass` does not escape `:`, so a reuse fails every `dark:` token; and finding 1 forces `rules()` to change behaviour, which breaks the "stays green" proof. Specify the seam, define `escape`, and add `rulesDeep`/`declarationsDeep` as new readers beside the untouched `rules()`/`declarations()`.
