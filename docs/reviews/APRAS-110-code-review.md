# APRAS-110 — Code Review

**Task**: Show the acting condominium's logo in the header
**Subject**: `git -C /Users/heitor/workspace/apras/.claude/worktrees/agent-a51db4f2b8aa8ad65 diff --cached`
**Base**: `ea37e9a` (worktree `HEAD` verified `ea37e9adbaa50c92f5d1aed524450d05551d8069` before and after review)
**Diff size**: 9 paths, 1556 insertions / 11 deletions. Frontend code: `TenantHeaderLogo.tsx` (+136), `Navbar.tsx` (+5 −11), `TenantHeaderLogo.test.tsx` (+371), four `Navbar*.test.tsx` (+27 each). Docs: `APRAS-110-spec.md` (+620), `APRAS-110-mock.html` (+316). No file under `backend/`.

**VERDICT: APPROVED**

---

## 0. Integrity of the review itself

Every mutation below was applied to the *working tree only*, never the index, and restored with `cmp` immediately afterwards. The mutation harness refused no-ops (it `cmp`s against a pristine backup before running and aborts if the patch did not change the file), so no "mutant" reported here is a patch that silently failed to apply.

Final state, re-verified after the last cycle:

```
git diff --stat                 → empty (no unstaged changes)
git diff --cached --stat        → byte-identical to the pre-review capture
git stash list | wc -l          → 0   (never touched; no stash command was ever run)
cmp backup/<7 frontend files>   → all identical
git show :<path> | cmp - <path> → ok for all 9 staged paths
git -C <main checkout> status --short frontend/ → clean
```

The main checkout's `frontend/` was linted read-only and otherwise left alone. No other worktree was touched.

---

## 1. The two criteria the task turns on

### 1a. The plate's class list, as a sorted-set equality in two renders

`TenantHeaderLogo.tsx:88-91`:

```tsx
<span
  data-testid="tenant-header-logo-plate"
  className="inline-flex items-center px-1 rounded-md dark:bg-foreground"
>
```

Asserted at `TenantHeaderLogo.test.tsx:288-307`, with `PLATE_TOKENS` declared once (line 280) and compared against **both** renders plus a final `darkTokens === lightTokens`. The `.dark` wrapper is an *ancestor* (`navbarTree`, line 108), which is what the project's `@custom-variant dark (&:is(.dark *))` requires. `img.parentElement === plate` is asserted in both halves (lines 293, 300). Correct in every particular.

### 1b. All five deliberate wrong implementations reproduced

Each was built, run against the real 18-case file, and confirmed to fail **by the named mechanism** — not merely to fail.

| # | Mutation | Result | Failing assertion | Mechanism confirmed |
|---|---|---|---|---|
| 1 | `dark:bg-foreground` → `bg-foreground` | 1 failed / 17 passed | `test.tsx:295` (light render) | `AssertionError: ... − "dark:bg-foreground" + "bg-foreground"`. Exactly as claimed. |
| 2 | `cn("inline-flex items-center px-1 rounded-md", document.querySelector(".dark") ? "bg-foreground" : undefined)` | 1 failed / 17 passed | `test.tsx:295` | `expected [ 'inline-flex', 'items-center', …(2) ]` — **four** tokens in the light render. Exactly as claimed. |
| 3 | plate wrapped around the fallback too (unconditional card) | **4 failed** / 14 passed | `test.tsx:313`, `:320`, `:327`, `:334` | All four absence cases rejected it. Exactly as claimed, with one nuance — see §1c. |
| 4 | React `key` removed **and** `url: event.currentTarget.src` | 1 failed / 17 passed | `test.tsx:266` = `expect(second).not.toBe(first)` | Rejected on `first === second`. Exactly as claimed. |
| 5a | `const shouldRetry = false` (never recovers) | 1 failed / 17 passed | `test.tsx:244` = `const retried = banner().getByRole("img")` | Step **(b)** failed. Exactly as claimed. |
| 5b | `shouldRetry = current?.suppressed === true` + attempt count not advanced (unbounded retry) | 1 failed / 17 passed | `test.tsx:252` = `expect(queryByRole("img")).toBeNull()` | Step **(c)** failed. Exactly as claimed. |

All five developer claims hold verbatim. These guards have now been watched to fail.

### 1c. One nuance on mutant 3, worth recording

Mutant 3's fourth failure landed at `test.tsx:334` — the **light** half of *"renders no card once the bytes fail, including in the dark scheme"*. The dark-ancestor half at line 339 is never reached, because Vitest stops the case at the first failed assertion. So the developer's phrasing *"all four absence cases rejected it, including the one inside a `.dark` ancestor"* is true of the four **cases** but the dark-ancestor **assertion** itself is not exercised by that mutant. This is not a hole: the plate's existence is scheme-independent by construction (the element always renders on the logo branch; only its paint is `dark:`-gated), so no realistic mutant can make line 339 disagree with line 334. Recorded for accuracy, not as a finding.

### 1d. The mandatory pair

`test.tsx:309-340` asserts `queryByTestId("tenant-header-logo-plate")` is `null` in all four fallback states: `logo_url: null`, `isPending`, `isError`, and post-`fireEvent.error` (the last twice, light and dark). Mutant 3 proves the pair is load-bearing.

---

## 2. The dynamic-token hole — confirmed open, and not exploited

I built the exact attack the spec reviewer named:

```tsx
className={`inline-flex items-center px-1 rounded-md dark:bg-${"foreground"}`}
```

Result: **18/18 passed.** The class-list equality is satisfied, and nothing in the repository notices. I additionally ran this mutant against the three nearest guards — `themeTokenMigration.test.ts`, `themeTokenCompile.test.ts`, `brandTextRole.test.ts` — and got **292/292 passed**. The hole is real, open, and reachable.

The implementation does **not** take it. `TenantHeaderLogo.tsx:91` is a single literal string on a `className` attribute: no template literal, no `cn`, no fragment concatenation, no interpolation. (`cn` *is* imported and used, but only on the fallback branch at line 118, where the three-way `md:hidden` rule genuinely needs a conditional — and there every token is still a literal.)

**Is the literal-string discipline enforced anywhere? No — it is only observed.** I checked:

- `themeTokenMigration.test.ts` scans source text for *palette* classes (§3b grammar). `dark:bg-${"foreground"}` is not a palette class, so it is invisible to the guard. Confirmed empirically above.
- `themeTokenCompile.test.ts` compiles a *fixture* built from the mapping table, not from the source tree. It cannot see a call site at all — its own header says so.
- No ESLint rule in the project constrains `className` to literals.

So the only thing standing between this call site and a no-CSS plate is the author's choice and this review. The spec reviewer judged that acceptable and I do not overturn it — but I verified end-to-end that the *real* token does compile, which is also the shape the missing guard would take. From `npm run build` output:

```
.dark\:bg-foreground:is(.dark *){background-color:var(--color-foreground)}
```

That is the real browser rule, present in `dist/assets/*.css`. See §Suggestions for the cheap guard.

---

## 3. The three cases that passed before the component existed

The developer's report is accurate, and I pushed on it both ways.

**Are they vacuous?** Individually, yes, against a component that renders nothing. I built that mutant (fallback branch replaced by `return null`): the three card-absence cases **do not** catch it (0 of 3 fail), while **seven** sibling cases do — `shows the fallback ... when no logo is configured`, `... while the profile is pending`, `... when the profile read failed`, `suppresses the image and shows the fallback`, `recovers by itself once`, `hides the fallback on desktop`, `keeps the fallback on desktop`. 7 failed / 11 passed.

**Are they worthless?** No. Mutant 3 (§1b) is the realistic failure mode these three exist to catch — an unconditionally rendered card — and all three reject it. Each of the three also sits in the same file as a sibling case covering the identical state with a *positive* assertion on the fallback, so no state is left unasserted.

**Judgement: the developer's call is correct, and the documentation of it is the right behaviour.** The spec explicitly frames these as a pair whose job is to give the presence assertion meaning, and that is exactly what they do. Leaving them in while naming their vacuity is better than deleting them (which would re-open mutant 3) and better than silently shipping them as if they stood alone. I would still strengthen them one line each — non-blocking, §Suggestions.

---

## 4. The four escalations

### 4.1 Staged `docs/tasks/` copies — verified byte-identical, and policy-consistent

Both directions checked, including the staged blob rather than just the working file:

```
cmp  <worktree>/docs/tasks/APRAS-110-spec.md  <main>/docs/tasks/APRAS-110-spec.md   → identical
git show :docs/tasks/APRAS-110-spec.md | cmp - <main>/docs/tasks/APRAS-110-spec.md  → identical
sha256 both: ede79e44c3d13e6ca9e256d3dda16152bde8a5d96d745d35ee542446396d999a

cmp  <worktree>/docs/tasks/APRAS-110-mock.html <main>/docs/tasks/APRAS-110-mock.html → identical
git show :docs/tasks/APRAS-110-mock.html | cmp - <main>/...                          → identical
sha256 both: 4978cb838d461c2c2b554a5a043d57151d4d5fca471960679e8705987218ad0b
```

I compared against the main checkout as it stands *now*, after the pre-dispatch edit, rather than trusting the claim. Both are byte-identical, staged blob included.

`git check-ignore -v docs/tasks/APRAS-110-spec.md` → no match; `docs/tasks/` is **not** gitignored. `git ls-files docs/tasks | wc -l` → **125** tracked against **19** untracked. (The developer said 124; it is 125 today. Immaterial.) Committing these two is the project's existing practice, not a new policy. **Correct call.**

Two expected results (§Expected Results, the `-spec.md` content result and the `-mock.html` result) do assert on these files' content, so they have to be in the tree for the criteria to be checkable. I verified both results independently: the spec carries the `### The cost of the logo bytes (decided: accept, bounded, degrade)` heading naming `30/minute` per-IP, the absent `Cache-Control`/`ETag`, "one logo request per full document load per user … at most one retry … zero per in-app navigation", the explicit accept decision, and `APRAS-124` by id (5 occurrences); state 5 names `429`. The mock draws five state cards for the six states and both question sections with an A and a B card each, and needs no build step (it uses the same two CDN `<script>` tags as 23 of the repository's 28 existing mocks).

### 4.2 The lint baseline — the developer is right, the spec is stale, and the cause is a stale `node_modules`

This one had a trap in it. The two checkouts do not run the same linter:

```
<worktree>/frontend/node_modules/.bin/eslint --version → v10.11.0
<main>/frontend/node_modules/.bin/eslint --version     → v9.39.4
```

`package.json` declares `"eslint": "^10.11.0"` and `package-lock.json` pins `node_modules/eslint → 10.11.0`. `package.json` and `package-lock.json` are byte-identical between the two checkouts. So the **worktree** matches the lockfile and the **main checkout's install is stale** — which is where the spec's figure came from.

Measured, not inferred. I reverted the worktree's working tree to `ea37e9a` content for all seven frontend paths (index untouched, both new files moved aside) and ran `npx eslint .` under the lockfile's eslint:

| Measurement | Result |
|---|---|
| `ea37e9a`, worktree, eslint 10.11.0 (**true baseline**) | **372 problems (370 errors, 2 warnings)** |
| `ea37e9a` + the change, worktree, eslint 10.11.0 | **372 problems (370 errors, 2 warnings)** |
| `ea37e9a`, main checkout, eslint 9.39.4 (stale install) | 370 problems (368 errors, 2 warnings) |

**The developer's `372 (370 errors, 2 warnings)` is right on `ea37e9a`.** The spec's `370 (368 errors, 2 warnings)` is the figure eslint 9.39.4 produces — it is not an earlier *base*, it is an earlier *linter*. The two extra errors under eslint 10 are in files this task does not touch: `TenantsAdminPage.invitations.test.tsx:517 no-useless-assignment` and `SidebarContext.tsx:96 react-refresh/only-export-components`.

**The change's delta is exactly zero.** I diffed the two full outputs: they are identical except that the 24 pre-existing `no-explicit-any` errors in `Navbar.test.tsx` shifted down by 27 lines — precisely the 27 lines the `vi.mock` block adds. Same count, same rules, same file. Nothing new, nothing fixed. The criterion ("no more errors than the baseline") is satisfied under either figure.

One factual correction to the developer's own report: the file count is **79** files carrying problems, not 66 (and not the spec's 64). `grep -cE "^/Users" | sort -u` on both runs gives 79.

**The spec's expected result should be corrected before landing**, to `372 problems (370 errors, 2 warnings)` across 79 files, with a note that the figure is only reproducible against a `node_modules` that matches the lockfile. As written it will mislead the next person who measures it on a stale install and concludes the change *added* two errors — which is exactly the wrong turn I nearly took. Non-blocking: the criterion is "not worse", and it is not worse.

### 4.3 The `getByRole("link", { name: "APRAS" })` expected result — double match is real

Verified by mutation rather than by reading. I replaced the scoped query at `test.tsx:190` with the spec's literal unscoped `screen.getByRole("link", { name: "APRAS" })` and ran the file:

```
× shows the fallback and keeps the appName name when no logo is configured
TestingLibraryElementError: Found multiple elements with the role "link" and name "APRAS"
Tests  1 failed | 17 passed (18)
```

The double match is real and Testing Library throws on it. The spec's wording is literally unsatisfiable by **any** implementation.

The developer's resolution is the right one and is stronger than the spec asked for: `banner().getByRole("link", { name: "APRAS" })` is asserted `.toBe(screen.getByTestId("tenant-header-fallback"))`, which pins the *identity* of the matched element rather than merely its existence. It also matches the spec's own stated intent — the result says this is `Navbar.test.tsx`'s existing *"exposes exactly one link in the banner, the appName logo pointing at /"* case passing unmodified, and that case (`Navbar.test.tsx:1022-1028`) is itself banner-scoped: `expect(banner.getByRole("link", { name: "APRAS" })).toBe(links[0])`. The spec's shorthand `screen.` contradicts the sentence it sits in.

**Yes, the spec's wording should be corrected** to `within(screen.getByRole("banner")).getByRole("link", { name: "APRAS" })`, exactly as the sibling result two bullets above it already does for `getAllByRole("link")`. The comment left at `test.tsx:188-189` documents it adequately in the meantime. Non-blocking.

### 4.4 `frontend/.vitest/json/output.json`

Confirmed **not staged**: `git diff --cached --name-only` lists nine paths and this is not among them; `git status --short` shows it as `??`. Confirmed **not ignored**: `git check-ignore -v` matches `frontend/.gitignore:11 → dist` and `frontend/.gitignore:25 → coverage` but returns no match for `frontend/.vitest/json/output.json`. It reappeared during my own `vitest run` invocations and remains untracked.

**Yes, `frontend/.vitest/` belongs in `frontend/.gitignore`, as a separate chore.** It is a reporter artifact of the project's own `vitest.config.ts`, in the same category as the already-ignored `dist` and `coverage`, and every agent or developer who runs the suite will keep tripping over it. It must not ride along in this task's commit — the diff is clean and should stay that way. Handling it correctly by leaving it alone was the right call.

---

## 5. Implementation checks

| Check | Result |
|---|---|
| Plate is the image's parent | `img.parentElement === plate` asserted in both renders (`test.tsx:293`, `:300`). The `<img>` is the `<span>`'s only child in the source. ✅ |
| Image class list exactly `h-7 w-auto max-w-32 object-contain` | Sorted-set equality in light and dark (`test.tsx:160-178`). `grep -nE "invert\|filter\|dark:"` on the component returns only line 85 (a comment) and line 91 (the plate). No `dark:`, no `invert`, no `filter` on the image. ✅ |
| `dark:bg-foreground` is semantic and survives `themeTokenMigration.test.ts` | Verified by mutation. Real implementation: **179/179 passed**. Swapped to `dark:bg-white`: **4 failed**, with the guard naming the exact site — `TenantHeaderLogo.tsx:91 still carries "dark:bg-white"; migrate it to the token its row names ...`. The claim is proven, not asserted. ✅ |
| Latch's `url` is the render's value, never `event.currentTarget.src` | `onError={() => { setFailure({ url: logoUrl, ... }) }}` — the handler takes **no event parameter at all**, so `currentTarget` is not merely unused, it is unreachable. Mutant 4 confirms the test catches the alternative. ✅ |
| Retry fires only when `failures === 1` | `const shouldRetry = current?.suppressed === true && current.failures === 1;` (line 64). Mutants 5a/5b bracket it from both sides. ✅ |
| Timer cleared on unmount and on URL change | `return () => clearTimeout(timer)` with deps `[shouldRetry, logoUrl]` (lines 66-73). A slug change changes `logoUrl` → cleanup runs. Unmount → React runs cleanup. ✅ (not directly asserted — see §Suggestions) |
| Stale-failure reset across tenants | `const current = failure?.url === logoUrl ? failure : null;` (line 60) — a failure recorded against another URL is structurally not this URL's failure. No extra wiring, no effect. Clean. ✅ |
| `md:hidden` three-way rule keeps the mark on desktop after a latched failure | `logoUrl === null && "md:hidden"` (line 123) — so a *promised* logo whose bytes failed keeps the mark at every breakpoint. All three directions asserted (`test.tsx:343-370`). ✅ |
| Logo branch's `Link` carries no `aria-label` | Lines 76-79: `to` and `className` only. Accessible name therefore comes from the image's `alt`, i.e. `data.name` — proven by `getByRole("link", { name: "Residencial Vila Nova" })` resolving (`test.tsx:146`). The component's header comment explains *why* the link lives here rather than in `Navbar`, which is the right place for that reasoning. ✅ |
| Fallback keeps `aria-label={t("common.appName")}` and gains the testid | Lines 116-117. ✅ |
| Every timer advance wrapped in `act()` | Three advances at `test.tsx:236-238`, `241-243`, `249-251`, all inside `act()`. ✅ |
| `vi.mock` implementation inside the factory | All four Navbar files use `vi.mock(path, () => ({ useTenantProfile: vi.fn(() => ({...})) }))` — the implementation is in the factory, so it survives `Navbar.tenantAdmin.test.tsx`'s `vi.restoreAllMocks()`. The default is the **no-logo** answer, which is why all 45 pre-existing cases stand unchanged. Verified green. ✅ |
| No colour value or contrast ratio anywhere in the diff, comments included | `grep -inE "#[0-9a-fA-F]{3,8}\|oklch\|rgba?\(\|hsl\(\|contrast\|luminance\|[0-9]+\.[0-9]+ *: *1\|white\|black\|slate-\|gray-\|zinc-"` over the added lines of the frontend diff → **no match**. Same scan over the whole component file → no match. The only paint reference in the file is the token name. ✅ |

### Architecture, KISS/YAGNI/DRY, security

- **Module boundaries.** The component sits in `features/user-administration/components/` beside `Navbar.tsx`, reads data through the existing `hooks/useTenantProfile` and builds its URL through the existing `api/publicBranding.tenantLogoUrl`. No new API module, no second definition of where the API lives, no duplicated URL assembly. `Navbar.tsx` shrinks by 11 lines and gains one child — the slot's whole concern, link included, moved into one file. This is the right decomposition and the header comment states the reason (the accessible-name rule has to live where the `Link` is).
- **`useTenantProfile()` with no `enabled`.** Correct, and the comment's justification checks out against the hook: `enabled` exists for exactly one caller (`TenantBrandTheme`, mounted app-wide including the login screen); this component only mounts inside `Navbar`'s authenticated branch. The shared `["tenantProfile"]` key means **no new JSON request** — only the image bytes, which is precisely the cost §"The cost of the logo bytes" accounts for. The same key is also reset by `setActingTenant`'s `resetQueries` predicate on a tenant switch, which is what makes the slug-change path work without the component knowing about tenants at all.
- **`data &&` in the guard is not redundant.** `logoUrl` is derived from `data?.logo_url`, and TypeScript cannot narrow `data` from `logoUrl !== null`; the conjunct is what makes `data.name` safe at line 97. Not a DRY violation.
- **State shape.** One `useState` holding `{ url, failures, suppressed }` and one `useEffect`. No reducer, no context, no custom hook, no abstraction for a single call site. `RETRY_DELAY_MS` is a named constant with its reason (wider than the route's one-minute limiter window) recorded next to it. Appropriately small.
- **Security.** `src` comes from `tenantLogoUrl(data.slug)` → `/public/tenants/${encodeURIComponent(slug)}/logo`, so the slug is escaped and cannot break out of the path. `alt={data.name}` is a React text attribute, escaped by the renderer. No `dangerouslySetInnerHTML`, no `innerHTML`, no user-controlled URL scheme (the base comes from `apiClient.defaults.baseURL`, not from the profile). The retry is bounded at one attempt per URL, which is what keeps a 429 from becoming a request loop — the amplification risk the spec names is genuinely closed, and mutant 5b proves the bound is tested. No secrets, no logging of profile data. Nothing to raise.
- **Comment quality.** The comments explain *why* (why the key is derived from the attempt count, why the plate is a wrapper and not a token on the image, why `url` is the render's value, why `enabled` is absent) rather than restating the code. They are the reason this review could check intent against behaviour.

---

## 6. Re-run evidence

Everything the developer reported, re-run rather than accepted:

| Claim | Re-run result |
|---|---|
| 198 files / 2594 tests passing | `npx vitest run` → **Test Files 198 passed (198), Tests 2594 passed (2594)** ✅ |
| `npm run build` exit 0 | `npx tsc -b --noEmit` exit 0; `npm run build` → `✓ built in 452ms`, exit 0 (only the pre-existing >500 kB chunk-size advisory) ✅ |
| Four Navbar files at 45 tests | **Test Files 4 passed (4), Tests 45 passed (45)** ✅ |
| `TenantHeaderLogo.tsx` 100% on all four metrics | `Statements 100% (20/20)`, `Branches 100% (19/19)`, `Functions 100% (5/5)`, `Lines 100% (18/18)` ✅ |
| `TenantHeaderLogo.test.tsx` passes | **18 passed (18)**; 4 + 3 + 3 + 5 + 3 cases across the five describes, at least one per state ✅ |
| No file under `backend/` | `git diff --cached --name-only | grep -c "^backend/"` → **0** ✅ |
| `grep -c "size-3.5" Navbar.tsx` prints `0` | **0** ✅ |

I did not re-verify the "35 of 45 failed before the `vi.mock` was added" figure, since the predicted `QueryClientProvider` breakage is a counterfactual about a state that no longer exists and nothing turns on its exact count. The mechanism is sound and the 45 stand green now, before and after.

---

## Suggestions

These are non-blocking. None of them should hold the task.

1. **Close the dynamic-token hole with one assertion, in a follow-up.** The hole is real — I confirmed `` `dark:bg-${"foreground"}` `` passes all 18 cases and all three theme guards. The cheap fix is not a lint rule but a CSS-output check: Tailwind's own `compile()` is already a dependency and already used by `src/__tests__/themeTokenCompile.test.ts`. A case that compiles `src/index.css` over a fixture containing the plate's literal class list and asserts the emitted sheet contains `.dark\:bg-foreground:is(.dark *)` with a non-empty `background-color` would fail for any assembled token, because an assembled token never reaches Tailwind's scanner. (The real build already emits exactly that rule — I pulled it out of `dist/assets/*.css`.) Worth a task of its own; it would protect every `dark:`-gated paint token in the tree, not just this one.

2. **Add `frontend/.vitest/` to `frontend/.gitignore`** as a standalone chore, next to the existing `dist` and `coverage` entries. Keep it out of this commit.

3. **Correct the spec's lint figure to `372 problems (370 errors, 2 warnings)` across 79 files**, and say that the figure requires a `node_modules` matching `package-lock.json` (eslint `10.11.0`). The current figure is what a stale eslint `9.39.4` install produces and will read as "this change added two errors" to the next person who measures it.

4. **Correct the spec's `logo_url: null` expected result** to `within(screen.getByRole("banner")).getByRole("link", { name: "APRAS" })`. As written it is unsatisfiable by any implementation, and it contradicts the sentence it sits in, which points at a banner-scoped existing case.

5. **Strengthen the three card-absence cases by one line each.** Adding `expect(screen.getByTestId("tenant-header-fallback")).toBeInTheDocument();` to *"renders no card when no logo is configured"*, *"... while the profile is pending"* and *"... when the profile read failed"* would make each of them assert that its subject rendered at all, so none of the 18 would be vacuously true in isolation. They already discriminate against the realistic mutant (mutant 3) and seven siblings catch the render-nothing mutant, so this buys tidiness rather than coverage — but given this repository's shipped audit of tests that pass while their subject is absent (`e1d19f2`), three self-identified vacuous cases are worth one line each to retire.

6. **Consider asserting the unmount cleanup.** `clearTimeout` on unmount is correct by construction but is the one branch of the latch no case exercises; a stray timer would surface as a React warning rather than a failure. A case that errors the image, unmounts, advances 120 s and asserts no warning (or simply that `setFailure` was not called again) would pin it. Low value — the window is 60 s and the consequence is a console warning — so only if a future task touches this effect.

7. **Record the Meridian/spec drift.** `.meridian/tasks/APRAS-110.json` carries 18 `expected_results` and **none** of them is the card criterion, while `docs/tasks/APRAS-110-spec.md` specifies the plate in full (§"Theming and contrast", plus two dedicated expected results). The spec is clearly the later and authoritative document — the operator's question-2 decision landed there after the detail file was written. QA should review against the spec, not the detail file, or the two card criteria will go unchecked. This is an orchestrator-side write, which is why I am only reporting it.

---

## Blocking Findings

None.

**VERDICT: APPROVED**
