# APRAS-91 — Cover Navbar's own active markup, which no test reaches

## Scope

Test-only task. It adds coverage for the state-driven markup that
`frontend/src/features/user-administration/components/Navbar.tsx` renders
**itself**, and it relocates the assertions that only ever reached `Sidebar`
through it.

Nothing under `frontend/src/` outside `__tests__/` and `src/test/` changes. No
production component, hook, style or locale file is touched. The three
assertions APRAS-87 renamed are not rewritten — they are either deleted as a
duplicate or moved verbatim (see §4).

### What Navbar owns, read from the component

Verified against the current tree (line numbers below are today's):

| Navbar's own element | State it carries |
| --- | --- |
| `<header>` (`:65`) — the tree's only `banner` | `md:ml-64` when the sidebar is expanded, `md:ml-20` when collapsed, from `useSidebar().isCollapsed` |
| Mobile hamburger `<button>` (`:73`) | `aria-label`/`title` = `nav.openMenu`, calls `toggleMobile` |
| Mobile logo `<Link to="/">` (`:84`) | `aria-label` = `common.appName`; the only link inside the banner |
| Tenant `<select>` (`:105`) | rendered only when `tenants.length >= 2` |
| `<SimulationControls />` (`:127`) | rendered only when the **real** permission set holds `roles:update` |
| Language `<button>` ×2 (`:130`) | **active**: `bg-primary text-primary-foreground`; **inactive**: `text-muted-foreground hover:text-foreground` |
| Username `<span>` (`:145`) | `user.full_name` |
| Role subtitle `<span>` (`:149`) | three exclusive branches: simulating → `text-amber-600 dark:text-amber-400 font-semibold`; superuser → `text-primary-text font-semibold`; otherwise → `text-muted-foreground`. Navbar's **only** brand-text call site |
| Logout `<button>` (`:164`) | calls `logout` |

Delegated to `<Sidebar />` at `:64`, and therefore **not** Navbar's: every nav
link and its active highlight, the `APRAS` brand text, the group accordions,
the desktop collapse toggle, the mobile drawer.

### What "active" means for the language buttons

`currentLang = i18n.resolvedLanguage ?? i18n.language`; a button is active when
`currentLang.startsWith(lang.code)`. Three distinct facts follow, all
assertable: `resolvedLanguage` wins over `language`; a regional tag such as
`pt-BR` still activates `PT`; exactly one of the two buttons is active at a
time. The repository-wide `react-i18next` mock in `src/test/setup.ts` supplies
`language: "pt"` and **no** `resolvedLanguage`, so the default fixture already
exercises the `??` fallback with `PT` active and `EN` inactive; the inverse
branch needs a per-test `useTranslation` stub.

## Approach

### 1. Query strategy: `within(screen.getByRole("banner"))`

Every new assertion resolves its element from the banner, never from `screen`
directly:

```
const header = screen.getByRole("banner");
within(header).getByRole("button", { name: "PT" });
```

`Navbar.tsx:65` is the only `<header>` in the rendered tree — `Sidebar` renders
`<aside aria-label="Menu principal">` and a plain `<div>` drawer — so `banner`
is unambiguous, and probing the real tree confirms it resolves to `HEADER` with
exactly one link inside. Scoping this way is what makes the new assertions
structurally incapable of the APRAS-87 failure: an element that lives in
`Sidebar` cannot satisfy a `within(header)` query, whatever its text.

`Sidebar` is deliberately **not** mocked. Wholesale mocking is what hid this
gap in the first place, and two of the behaviours under test — the header's
`md:ml-*` margin and its response to collapsing — only exist because the real
`Sidebar` and the real `SidebarProvider` are both in the tree. No
`data-testid` is introduced; the project has no precedent for it here.

### 2. New cases in `Navbar.test.tsx` (all banner-scoped)

- **Active/inactive language tokens, default fixture.** `PT` carries
  `bg-primary` and `text-primary-foreground`; `EN` carries
  `text-muted-foreground` and neither of those two. Read through
  `classTokens` from `src/test/classTokens.ts`, never a raw `className`
  substring.
- **Inverse branch.** With a per-test `useTranslation` stub returning
  `{ resolvedLanguage: "en", language: "pt" }`, `EN` is the active one and `PT`
  the inactive one — which also pins `resolvedLanguage`'s precedence over
  `language`.
- **Regional tag.** With `resolvedLanguage: "pt-BR"`, `PT` is active.
- **Click contract.** Clicking `EN` calls the stub's `changeLanguage` exactly
  once with `"en"`. This replaces the present
  `"fires language change when a language button is clicked"`, whose only
  assertion is that a Sidebar label is still on screen.
- **Role subtitle, superuser branch.** The subtitle span inside the banner
  carries `text-primary-text` and **not** bare `text-primary` — the §1k
  character-site contract, at Navbar's only brand-text call site.
- **Role subtitle, simulating branch.** With `isSimulating: true`, the same
  span carries `text-amber-600` and neither `text-primary-text` nor
  `text-primary`.
- **Role subtitle, plain-user branch.** A non-superuser, non-simulating user's
  subtitle carries `text-muted-foreground` and no brand token. The fixture's
  `user.roles` must be **non-empty** (e.g. the existing
  `[{ id: "profile-guest", name: "GUEST" }]`): `roleSubtitle` is `null` for a
  non-superuser with no roles, and the span is then not rendered at all, so an
  empty-roles fixture makes the assertion fail for the wrong reason.
- **Header margin tracks the sidebar.** Rendered inside `SidebarProvider`, with
  the collapsed flag explicitly at its expanded value (see the persistence note
  below), the banner carries `md:ml-64`; after clicking the real Sidebar's
  `Recolher menu` button it carries `md:ml-20` and no longer `md:ml-64`.
- **Mobile logo link.** The banner's single link has `href="/"` and the
  accessible name `common.appName`.

#### Test-order hazards this file already has

`vitest.config.ts` sets neither `restoreMocks` nor `clearMocks`, and
`Navbar.test.tsx`'s `beforeEach` clears no storage (unlike
`Sidebar.test.tsx:77`). Three consequences bind the new cases:

1. **`useTranslation`.** A per-test stub overrides the module mock installed in
   `src/test/setup.ts`, so the file must capture the setup implementation once
   and restore it in `afterEach`. The stub must also keep setup's `t`: the real
   `Sidebar` is in the tree and calls `useTranslation().t`, so a stub returning
   only `{ i18n: { resolvedLanguage, language } }` crashes the render. Note too
   that setup's factory builds a **fresh** `changeLanguage` spy on every call,
   so the "exactly once" click assertion is only assertable against a per-test
   stub that owns its own spy.
2. **`useSimulation`.** `../context/SimulationContext` is mocked at module
   level and the existing simulation case overrides it with no restore,
   surviving only because it happens to be the file's last case. The new
   simulating-subtitle case takes the same capture-and-restore discipline as
   `useTranslation`, or it poisons every case after it.
3. **`localStorage`.** `SidebarProvider` persists `apras_sidebar_collapsed` and
   seeds `isCollapsed` from it, and the existing `"renders hamburger toggle"`
   case clicks `Recolher menu`, writing `"true"`. `md:ml-64` is therefore
   **not** unconditional: the header-margin case must call
   `localStorage.clear()` (or `setItem("apras_sidebar_collapsed", "false")`)
   before rendering, otherwise it starts collapsed and fails depending on test
   order. Adding the clear to the file's `beforeEach` is the preferred fix.

### 3. Class-token assertions only

All class assertions go through `classTokens(element)`. `toContain` on a raw
`className` string is forbidden in the new code: it is what let
`toContain("text-primary")` pass against `text-primary-text` and is the reason
this task exists.

### 4. The three renamed tests move (two of them)

- `"renders the Sidebar Tarefas label with the brand text token on /tasks"` is
  **deleted**: `Sidebar.test.tsx`'s `"highlights the active link with
  text-primary-text"` already asserts exactly that, at the same route, through
  the same helper.
- `"...Categorias... on /categories"` and `"...Administração... on
  /admin/users"` **move to `Sidebar.test.tsx`**, rendered through its existing
  `renderSidebar(permissions, route, isSuperuser)` helper —
  `["categories:read"], "/categories"` and `["users:update"], "/admin/users"`
  respectively, `users:update` being what `routeAccess.ts` requires for that
  item. The element lookup adopts that file's convention,
  `findByRole("link", { name })`, which resolves the anchor rather than the
  label `<span>` the old `getByText` reached. Both are asserted, so nothing is
  lost: `classTokens(link)` **and**
  `classTokens(within(link).getByText("Categorias"))` (resp. `"Administração"`)
  must each carry `text-primary-text` and not bare `text-primary`. Keeping the
  span assertion matters because those two moved `getByText` lookups were the
  only tests touching the label span's own token; `brandTextRole.test.ts`
  statically forbids a regression to bare `text-primary` there, but a silent
  removal of the token would otherwise go unnoticed.

They move because a Sidebar assertion living in `Navbar.test.tsx` is the very
confusion APRAS-87 diagnosed; renaming labelled it, moving it ends it, and
`Sidebar.test.tsx` is where a future reader will look for Sidebar's active
highlight.

### 5. Proving the new assertions are non-vacuous

Before handing over, mutate the component, watch a **named** test go red, and
revert — the method this project already uses:

| Mutation in `Navbar.tsx` | Must fail |
| --- | --- |
| swap the two branches of the language-button ternary | the active/inactive token cases |
| `text-primary-text` → `text-primary` on the subtitle | the superuser-subtitle case |
| swap `md:ml-20` and `md:ml-64` | the header-margin case |

The mutations are not committed. `git diff` must be empty for every file
outside `__tests__/`.

### Files touched

- `frontend/src/features/user-administration/__tests__/Navbar.test.tsx` — adds
  the banner-scoped cases above, deletes the `/tasks` duplicate, removes the
  two cases that move, replaces the weak language-click test, and hardens the
  file's hooks: `localStorage.clear()` in `beforeEach`, plus `afterEach`
  restores for the `useTranslation` and `useSimulation` module mocks.
- `frontend/src/features/user-administration/__tests__/Sidebar.test.tsx` —
  receives the Categorias and Administração active-highlight cases.

### Gates

`npx tsc -b` exits 0. `npx vitest run --coverage` passes at or above
80 lines / 78 functions / 76 branches / 80 statements. `npx eslint .` stays at
or below its 375-error / 2-warning baseline.

## Out of Scope

- Any change to `Navbar.tsx` or any other production file.
- The tenant `<select>`, `SimulationControls` internals and the hamburger
  button: Navbar's, but already covered (`TenantSwitcher.test.tsx`,
  `SimulationControls.test.tsx`, and the existing hamburger test).
- **Defect found and deliberately left alone, tracked as APRAS-97.** The active
  language button signals its state by colour alone: no `aria-pressed`, no
  `aria-current`, and the two buttons also lack `type="button"`. That WCAG 1.4.1
  (Use of Color) gap in production markup is APRAS-97's; this task asserts the
  classes as they are today and does not fix it.

## Expected Results

- [ ] `Navbar.test.tsx` asserts that the `PT` language button inside the
      `banner` carries the class tokens `bg-primary` and
      `text-primary-foreground`, while the `EN` button carries
      `text-muted-foreground` and neither of those two.
- [ ] `Navbar.test.tsx` asserts the inverse: with `i18n.resolvedLanguage` set
      to `"en"` (and `language` still `"pt"`), the `EN` button carries
      `bg-primary`/`text-primary-foreground` and `PT` carries
      `text-muted-foreground` — pinning that `resolvedLanguage` takes
      precedence over `language`.
- [ ] `Navbar.test.tsx` asserts that a regional tag `"pt-BR"` still renders the
      `PT` button as the active one.
- [ ] `Navbar.test.tsx` asserts that clicking the `EN` button calls
      `i18n.changeLanguage` exactly once with `"en"`, using a per-test
      `useTranslation` stub that owns that spy (the repository-wide mock in
      `frontend/src/test/setup.ts` returns a fresh spy on every call, so a
      call-count assertion is not possible against it).
- [ ] Every per-test `useTranslation` stub in `Navbar.test.tsx` still returns a
      working `t` function (the repository-wide one from
      `frontend/src/test/setup.ts`), and the file restores the original
      `useTranslation` implementation after each case that overrides it, so no
      override leaks into later tests.
- [ ] `Navbar.test.tsx` asserts that the role-subtitle `<span>` inside the
      `banner` carries the class token `text-primary-text` and does **not**
      carry the bare token `text-primary`, for a superuser.
- [ ] `Navbar.test.tsx` asserts the subtitle's other two branches:
      `text-amber-600` while simulating, and `text-muted-foreground` for a
      plain (non-superuser, non-simulating) user whose `user.roles` fixture is
      non-empty — neither branch carrying any brand token. The case that
      overrides the `useSimulation` module mock restores the original
      implementation afterwards, so it does not leak into later tests.
- [ ] `Navbar.test.tsx` asserts that the `banner` carries `md:ml-64` while the
      sidebar is expanded and `md:ml-20` (and not `md:ml-64`) after the real
      Sidebar collapse button is clicked. That case does not depend on test
      order: `apras_sidebar_collapsed` is cleared from `localStorage` (or set to
      `"false"`) before the render, so a previous case having collapsed the
      sidebar cannot change its outcome. Running
      `npx vitest run Navbar.test.tsx` and re-running it with
      `--sequence.shuffle --sequence.seed=20260927` both pass. The seed is pinned so a
      failure is reproducible: an unseeded shuffle that goes red once and green
      on the retry tells the next reader nothing about which order broke it.
- [ ] `Navbar.test.tsx` asserts that the only link inside the `banner` points
      at `/` and is named by `common.appName`.
- [ ] Every class assertion added by this task reads the element through
      `classTokens` from `frontend/src/test/classTokens.ts`; no new assertion
      applies `toContain` to a raw `className` string.
- [ ] Every element asserted by an assertion **added to
      `Navbar.test.tsx`** by this task is resolved with
      `within(screen.getByRole("banner"))`, not from `screen` directly, and
      `Sidebar` is not mocked in `Navbar.test.tsx`. This applies only to
      `Navbar.test.tsx`; the assertions added to `Sidebar.test.tsx` render no
      `<header>` and use that file's own `findByRole`/`within(link)` lookups.
- [ ] `Navbar.test.tsx` no longer contains any assertion about a Sidebar nav
      label's active classes: the `/tasks` Tarefas case is gone (already
      covered in `Sidebar.test.tsx`), and the Categorias and Administração
      cases now live in `Sidebar.test.tsx`, asserting `text-primary-text` and
      not bare `text-primary` on **both** the active anchor and the label
      `<span>` inside it, at `/categories` and `/admin/users`.
- [ ] No file under `frontend/src/` outside `__tests__/` and `src/test/` is
      modified by this task.
- [ ] `npx tsc -b` exits 0; `npx vitest run --coverage` passes with coverage at
      or above 80 lines / 78 functions / 76 branches / 80 statements;
      `npx eslint .` reports no more than 375 errors and 2 warnings.
