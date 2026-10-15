# APRAS-91 — QA verification report

VERDICT: APPROVED

Scope verified: staged change in `/Users/heitor/workspace/apras`, branch `master` at
`25e9dc6`, 3 staged paths (`docs/tasks/APRAS-91-spec.md`,
`frontend/src/features/user-administration/__tests__/Navbar.test.tsx`,
`frontend/src/features/user-administration/__tests__/Sidebar.test.tsx`).

Method: read the test code and the production components, ran the suites, and
ran a mutation battery against `Navbar.tsx` and `Sidebar.tsx` to confirm each
new assertion fails when the behaviour it claims to pin regresses — and that it
is the *named* case that reddens, not a neighbour. Every mutation was applied by
exact-string replacement (occurrence count asserted), verified present on disk
before running the tests, then restored by file copy and `cmp`-verified. No
`sed` by line number, no `git stash`, nothing staged or unstaged.

Snapshots used for restore:
`/private/tmp/claude-501/-Users-heitor-workspace-apras/06230b8a-d0ef-40dd-929b-83bb4eb6abbf/scratchpad/snap/`.

## Baseline runs

- `npx vitest run <Navbar.test.tsx> <Sidebar.test.tsx>` → 2 files, 40 tests passed.
- `npx tsc -b` → `TypeScript: No errors found`, exit 0.
- `npx vitest run --coverage` → 188 files, 2503 tests passed. Coverage summary:
  Statements 91.5%, Branches 85.28%, Functions 87.83%, Lines 92.21%. Thresholds
  in `vitest.config.ts` are 80/78/76/80 (lines/functions/branches/statements);
  all exceeded, no threshold error emitted.
- eslint, measured by me at both ends with `--format json` and summed:
  - at `HEAD` (both test files replaced by `git show HEAD:` content, then
    restored from the snapshot and `cmp`-verified): **375 errors, 2 warnings**;
    `Navbar.test.tsx` 33 errors, `Sidebar.test.tsx` 0.
  - with the change: **368 errors, 2 warnings**; `Navbar.test.tsx` 26 errors,
    `Sidebar.test.tsx` 0.
  No new rule violations; the count is 7 below baseline.

## Mutation battery — `Navbar.tsx` (production, temporary, all restored)

Each line lists the mutation and the *complete* set of tests that failed under it.

| Mutation | Tests reddened |
|---|---|
| `resolvedLanguage ?? i18n.language` → `resolvedLanguage ?? "en"` | only "marks PT active and EN inactive with the default fixture" |
| `resolvedLanguage ?? i18n.language` → `i18n.language` (drop precedence) | only "marks EN active from resolvedLanguage even while language is still pt" |
| `currentLang.startsWith(lang.code)` → `currentLang === lang.code` | only "treats the regional tag pt-BR as PT active" |
| `changeLanguage(lang.code)` → `changeLanguage("pt")` | only "calls changeLanguage exactly once with 'en' when EN is clicked" |
| `onClick` calls `changeLanguage` twice | only the same "exactly once" case |
| superuser branch `text-primary-text` → `text-primary/90` | only "paints a superuser's role subtitle with the brand text token" |
| superuser branch `text-primary-text` → `text-primary` | only the same case |
| simulating branch `text-amber-600 dark:text-amber-400` → `text-primary-text` | only "paints the role subtitle amber while simulating" |
| plain branch `text-muted-foreground` → `text-foreground` | only "paints a plain user's role subtitle muted and with no brand token" |
| `isCollapsed ? "md:ml-20" : "md:ml-64"` → constant `"md:ml-64"` | only "tracks the sidebar width in the header's desktop margin" |
| the same ternary with its two values swapped | only the same margin case |
| logo `to="/"` → `to="/dashboard"` | only "exposes exactly one link in the banner…" |
| logo `aria-label={t("common.appName")}` → `t("nav.openMenu")` | only the same link case |
| an extra `<Link to="/extra">` added inside the banner | only the same link case |

Attribution is exact in all fourteen cases: no mutation reddened a case other
than the one whose name describes the mutated behaviour, and none survived.

## Mutation battery — `Sidebar.tsx` (supports results 12 and the moved cases)

| Mutation | Tests reddened in `Sidebar.test.tsx` |
|---|---|
| active anchor `bg-primary/10 text-primary-text` → `bg-primary/10 text-primary/90` (both call sites) | "highlights the active link with text-primary-text", "…Categorias and its label…", "…Administração and its label…", "renders Início link and highlights when on /" |
| active label `isActive && "text-primary-text"` removed (both call sites) | "…Categorias and its label…", "…Administração and its label…" |

So the `/tasks` coverage that result 12 relies on ("already covered elsewhere")
genuinely exists in `Sidebar.test.tsx` and genuinely fails when the highlight
regresses, and the two moved cases pin the label span as well as the anchor —
which the deleted Navbar versions did not separate.

## Expected results

- [x] **1. PT active / EN inactive with the default fixture** — read
  `Navbar.test.tsx:774-787`; assertions are `classTokens(pt)` contains
  `bg-primary` and `text-primary-foreground`, `classTokens(en)` contains
  `text-muted-foreground` and not the other two. Teeth: mutating the `??`
  fallback to `"en"` reddens this case and only this case (the other two
  language cases set `resolvedLanguage` explicitly, so they are unaffected —
  which is the right attribution).
- [x] **2. EN active from `resolvedLanguage` while `language` stays `pt`** —
  `Navbar.test.tsx:789-804`, via `stubI18n({ language: "pt", resolvedLanguage: "en" })`.
  Teeth: dropping `resolvedLanguage` from the precedence (`?? i18n.language` →
  `i18n.language`) reddens exactly this case.
- [x] **3. Regional tag `pt-BR` keeps PT active** — `Navbar.test.tsx:806-817`.
  Teeth: `startsWith` → `===` reddens exactly this case, leaving cases 1 and 2
  green. That is the precise behaviour the result names.
- [x] **4. Clicking EN calls `changeLanguage` once with `"en"`** —
  `Navbar.test.tsx:819-829`, with a per-test stub owning its own `vi.fn()` (the
  repository setup builds a fresh spy per call, so a count assertion is only
  possible this way). Teeth: wrong argument reddens it, and a double call
  reddens it too, so both halves of "exactly once with 'en'" are load-bearing.
- [x] **5. Every per-test `useTranslation` stub still returns a working `t`** —
  there is exactly one stub site, the `stubI18n` helper
  (`Navbar.test.tsx:71-84`); `grep useTranslation` confirms no other
  `mockImplementation`/`mockReturnValue` on it in the file. It captures the
  repository-wide implementation via
  `vi.mocked(useTranslation).getMockImplementation()` and spreads `...base`, so
  `t` is setup's `tMock`. Teeth: removing `...base` from the stub (leaving only
  `i18n`) reddens all three stubbed cases — the real `Sidebar` is in the tree
  and calls `t`, so the render crashes. The non-leak half also holds: `afterEach`
  reinstates both captured implementations, and three runs with
  `--sequence.shuffle.tests=true` passed 30/30 each, so the suite is
  order-independent as submitted. See the suggestion below for the one gap I
  found in how that restore is *pinned* — it does not make this result unmet,
  because a leaked stub still carries a working `t` and therefore still cannot
  break translation lookups, which is what the result claims.
- [x] **6. Role-subtitle `<span>` carries `text-primary-text`, not the tint** —
  `Navbar.test.tsx:831-848`: asserts `tagName === "SPAN"`, token
  `text-primary-text` present, and `text-primary` / `text-primary/90` absent.
  The negatives are meaningful because `classTokens` splits on whitespace rather
  than substring-matching the class string. Teeth: both the tint mutation
  (`text-primary/90`) and the bare-token mutation (`text-primary`) redden
  exactly this case.
- [x] **7. The other two subtitle branches** — amber while simulating
  (`Navbar.test.tsx:850-874`) and `text-muted-foreground` for a plain
  non-superuser (`876-894`). Teeth: replacing the amber branch reddens only the
  simulating case; replacing the plain branch's `text-muted-foreground` with
  `text-foreground` reddens only the plain-user case. Note the plain-user case
  deliberately gives the user a non-empty `roles`, otherwise `roleSubtitle` is
  `null` and the span never renders — the test would then pass/fail for the
  wrong reason; it does not.
- [x] **8. Banner margin tracks the sidebar** — `Navbar.test.tsx:896-910`:
  `md:ml-64` expanded, then the *real* `Sidebar`'s "Recolher menu" control is
  clicked and `md:ml-20` is present with `md:ml-64` absent. `beforeEach` clears
  `apras_sidebar_collapsed`, so the initial state does not depend on what an
  earlier case wrote. Teeth: pinning the margin to a constant reddens it, and
  swapping the two values reddens it — the second mutation is the one that
  proves the post-collapse half, not just the initial half.
- [x] **9. Exactly one link in the banner, `/` and named by `common.appName`** —
  `Navbar.test.tsx:912-919`: `getAllByRole("link")` has length 1, `href="/"`, and
  the accessible-name lookup resolves to that same element. Teeth: changing the
  href reddens it, changing the `aria-label` reddens it, and adding a second
  link inside the banner reddens it.
- [x] **10. All new class assertions go through `classTokens`** —
  `grep -n "toHaveClass\|\.className" Navbar.test.tsx` returns nothing; every
  added class assertion in the diff is `expect(classTokens(el))`. `classTokens`
  is imported from `src/test/classTokens.ts` (line 16) and is the whitespace
  split, which is what makes `not.toContain("text-primary")` meaningful next to
  `text-primary-text`.
- [x] **11. Added assertions resolve through `within(getByRole("banner"))`** —
  `renderBanner` returns `within(screen.getByRole("banner"))` and every added
  assertion resolves its element from that scope, with one necessary exception:
  the margin case (result 8) asserts on the banner element *itself*, which
  `within(banner)` cannot return. It uses `screen.getByRole("banner")` for the
  asserted element and `screen.getByRole("button", { name: "Recolher menu" })`
  for the Sidebar collapse control it clicks — a click, not an assertion, and
  the control is by definition outside the banner. The two results are coherent
  with each other: no assertion that *could* be banner-scoped is taken from
  `screen`, and `Navbar.tsx`'s `<header>` is the only `banner` in the tree
  (`Sidebar` renders an `<aside>` plus a `<div>` drawer), so the scope is
  unambiguous.
- [x] **12. No Sidebar nav-label active-class assertion left in `Navbar.test.tsx`** —
  the diff deletes all three (`/tasks`, `/categories`, `/admin/users`); a
  comment at `Navbar.test.tsx:223-228` records where they went. `/categories`
  and `/admin/users` are re-created in `Sidebar.test.tsx` (now asserting both
  the anchor and the inner label span), and `/tasks` is covered by the
  pre-existing `Sidebar.test.tsx:140` "highlights the active link with
  text-primary-text", which my `Sidebar.tsx` mutation confirms actually fails
  when the highlight regresses. Every remaining `classTokens` call in
  `Navbar.test.tsx` is banner-scoped Navbar markup.
- [x] **13. No production file touched** — `git diff -- frontend/src` is empty
  and `git status --porcelain` lists only the two `__tests__` files under
  `frontend/`. Confirmed after the whole mutation battery: all mutations were
  restored by file copy with a `cmp`/`filecmp` check, and the final
  `git diff -- frontend/src` is empty. The index still holds exactly the 3
  paths it held at the start.
- [x] **14. `tsc` / coverage / eslint** — see the baseline runs section above:
  `tsc -b` exit 0; full suite 2503/2503 with coverage well above every
  threshold; eslint 368 errors + 2 warnings against a HEAD baseline of 375 + 2.

## Blocking findings

None.

## Suggestions (non-blocking)

1. **The `afterEach` restore of `useTranslation` is not itself pinned.**
   Deleting the `if (setupUseTranslation) { … }` block from `afterEach`
   (`Navbar.test.tsx:140-142`) leaves the suite fully green: 30/30 still pass.
   The reason is declaration order — the only case that depends on *no*
   `resolvedLanguage` being set ("marks PT active … with the default fixture")
   runs before the three cases that call `stubI18n`, so a leaked
   `resolvedLanguage: "en"` has nothing left to corrupt. Under a different
   declaration order (or a future case appended after the stubbed ones that
   depends on the default `i18n`) the leak would bite, and nothing in the file
   would have warned. This does not make result 5 unmet: the stub always carries
   setup's `t`, so no leak can break a translation lookup — which is exactly
   what result 5 claims, and it is pinned (removing `...base` reddens three
   cases). The gap is narrower: the hygiene that keeps *`i18n` values* from
   leaking is correct but unenforced. Cheapest fix if you want it enforced:
   re-assert the default-fixture PT/EN state in a case declared *after* the
   stubbed ones, or enable `restoreMocks`/`clearMocks` in `vitest.config.ts` so
   the hand-rolled capture-and-restore is no longer load-bearing.
2. **A test that proved nothing was deleted — worth recording as such.** The
   removed case `"fires language change when a language button is clicked"`
   clicked `PT` and then asserted only
   `expect(screen.getByText("Tarefas")).toBeInTheDocument()` — it clicked the
   button and never looked at `changeLanguage`. Its replacement (result 4) does
   assert the call and the argument and the count. This is a genuine improvement
   and a candidate for `docs/suggestions-log.md` / the project's
   "tests that prove nothing" tally rather than a defect in this submission.
3. The `not.toContain("text-primary")` negatives would be slightly more robust
   spelled against the token list helper's intent if the brand-tint form were
   centralised (only one `text-primary/N` occurrence exists in `src` today,
   inside this very test). Purely cosmetic.
