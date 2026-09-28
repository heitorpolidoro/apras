# APRAS-106 — Render the public obras report without the app chrome, signed in or not

## Scope

`frontend/src/App.tsx` wraps **every** route in `<Navbar />` and
`<AppLayoutContent>` (lines 122–126). Both are authenticated chrome:

- `Navbar` returns `null` when `isAuthenticated` is false and renders
  `<Sidebar />` plus a sticky `<header>` when it is true;
- `AppLayoutContent` applies `isAuthenticated && (isCollapsed ? "md:ml-20" :
  "md:ml-64")`, a horizontal offset for a sidebar that only exists for a
  signed-in visitor.

So `/c/:slug/obras` — public by decision (APRAS-92 D1), reachable by slug,
outside `ProtectedRoute`, with no `ROUTE_ACCESS`, `NAV_ITEMS` or `NAV_GROUPS`
entry — is correct in a private window and wrong in the operator's own
session: navigation the report should never carry, and the report pushed right
by a sidebar's width. The routing is right; the layout is wrong.

This task moves the chrome from "around every route" to "around the
authenticated routes only", and pins the result with tests.

**In scope, and this is the part the operator is being asked to approve
explicitly:** the same treatment is applied to `/c/:slug`
(`BrandedEntryPage`) and to the five other routes that already sit outside
`ProtectedRoute` (`/login`, `/signup`, `/forgot-password`, `/reset-password`,
`/invite`). Reasoning in **Approach → which routes leave the chrome**. The
visible consequence for a signed-in visitor: the branded entry page's
"no access" panel and the auth forms lose the navbar and the sidebar offset.
For an anonymous visitor nothing on those routes changes at all — `Navbar`
already rendered `null` and the offset was already off.

**Out of scope:** the backend; the report document itself; `ROUTE_ACCESS`,
`NAV_ITEMS`, `NAV_GROUPS`; any change to who may read the report; `/`
(`RootRedirect`), which is auth-dependent by design and stays inside the
chrome; any new page copy or i18n key.

## Approach

### The shape: a nested layout route (decided)

**Decided by the operator: the nested layout route.** The chrome becomes the
element of a pathless `<Route>`, the authenticated routes become its children,
and the public routes are its siblings. "Public routes have no chrome" is then
a fact of the route table rather than a condition someone must remember to
apply when the next public route is added; putting a route in the wrong group
becomes a visible, reviewable act. The cost is accepted: every authenticated
`<Route>` is re-indented one level, a mechanical diff with no logic in it.

Recorded so a future reader sees it was considered: the alternative was a path
check inside the chrome components (`useLocation()` against a `PUBLIC_PATHS`
list, consulted by both `Navbar` and `AppLayoutContent`). It is a much smaller
diff, and it was rejected because it puts the rule in a place nobody visits
when adding a route — the next public route would land in the table, inherit
the chrome silently, and reproduce this exact defect — and because the list
would have to stay in step across two components.

Shape, in `App.tsx`:

- keep `<div className="App min-h-screen bg-background">` and `<Routes>` where
  they are — a page background is not auth-dependent chrome. Add
  `text-foreground` to that `div` so a public route rendered outside
  `AppLayoutContent` does not lose the default text colour that
  `AppLayoutContent` supplied. Both are tokens, not palette classes.
- add one component beside `AppLayoutContent` (same file — this is where
  `AppLayoutContent` already lives, and a new file buys nothing) that renders
  `<Navbar />`, `<AppLayoutContent>` and, inside it, react-router's `<Outlet />`
  in place of `children`. `AppLayoutContent` keeps its current signature and
  behaviour; nothing about the offset or `SimulationBanner` changes for the
  routes that keep the chrome.
- the seven public routes stay direct children of `<Routes>`; every other
  route, including `/` and the `/dashboard` redirect, becomes a child of the
  pathless chrome route.

### Which routes leave the chrome

The set is exactly the routes already outside `ProtectedRoute`:
`/login`, `/signup`, `/forgot-password`, `/reset-password`, `/invite`,
`/c/:slug`, `/c/:slug/obras`.

Drawing the line anywhere else reintroduces the ambiguity the shape is meant to
remove: with four public routes inside the chrome and three outside, "does this
route get chrome?" is again a question with no answer in the route table.
`/` is the one route that is public *and* authenticated, so it stays in the
chrome group — where the chrome is invisible to an anonymous visitor anyway.

On `/c/:slug` specifically, the operator asked only about the report, and the
honest answer is that the two screens differ: `/c/:slug` is deliberately
auth-aware (a signed-in member is redirected to `/`; a signed-in non-member
sees a "no access" panel), so the "identical in both states" property this task
imposes on the report does **not** apply to it and is not asserted for it. What
does apply is the defect itself — a public entry page offset by an absent
sidebar and fronted by app navigation — and the panel is self-sufficient
without the navbar: it already carries its own "my condominiums" and "sign out"
buttons. Fixing the report and leaving its sibling broken would be hard to
justify to the next reader of either file. Recommended, and called out in Scope
so it is approved and not smuggled.

### Files touched

- `frontend/src/App.tsx` — add the chrome layout component beside
  `AppLayoutContent`; import `Outlet`; regroup the route table into the seven
  public siblings and the pathless chrome route holding the rest; add
  `text-foreground` to the `div.App` class list. No route path, no
  `ProtectedRoute`, no `requiredAccess` value changes.
- `frontend/src/__tests__/PublicRouteChrome.test.tsx` — new; the tests below.

Nothing else. In particular no page component, no `routeAccess.ts`, no
navigation config, no i18n resource.

### How the tests must be written

`BrandedEntryPage.test.tsx` mocks `AuthContext`, `useTenant` and `useNavigate`
so completely that the integration it claims to prove is simulated — APRAS-69
exists because of it. The subject here is *how the app composes layout around a
route*, so mocking the router, the auth context or the layout would prove
nothing at all.

The new file therefore follows `src/__tests__/AppRouting.smoke.test.tsx`
exactly: mount the real `App` (real `BrowserRouter`, real `AuthProvider`,
`TenantProvider`, `SidebarProvider`, real page modules), and mock **only**
`src/api/client`. No `vi.mock` of anything under `src/features/**`, of
`react-router-dom`, or of `src/App`. A test in this file that mocks a context
or the router should be rejected in review.

The two auth states are produced through the same seam and no other:

- *anonymous* — no `accessToken` in `localStorage`/`sessionStorage`; the mocked
  client rejects `/auth/me`;
- *signed in* — seed `localStorage.accessToken`, and have the mocked client
  resolve `GET /auth/me` with a user payload (with a `tenants` array, so
  `TenantContext` settles) and resolve the report path with the fixture HTML.
  `AuthProvider` reads the token and calls `/auth/me` itself; the test asserts
  `isAuthenticated` indirectly, by the chrome appearing on a non-public route.

Both states resolve `GET /public/tenants/<slug>/projects/report` with the
**same** fixture string, so any difference in the rendered tree comes from the
layout and not from the data.

### What the tests assert

1. **No chrome, anonymous.** At `/c/<slug>/obras`, after the report frame
   (`data-testid="public-obras-report-frame"`) appears: no `<header>`, no
   `<aside>`, and no element whose `class` attribute contains `md:ml-64` or
   `md:ml-20`.
2. **No chrome, signed in.** Identical assertions in the signed-in state.
3. **The two renderings are equivalent, and equivalence is defined
   concretely.** Render at `/c/<slug>/obras` in each state, await the report
   frame, capture the render root's `innerHTML` in each, and assert the two
   strings are equal. Equality of the serialized markup is the definition —
   nothing is normalised away, because there is nothing non-deterministic to
   normalise: the fixture is a constant, the copy comes from the static i18n
   resources, and the page renders no time or id. The same assertion carries
   two guards without which it is worthless: the captured HTML must be
   non-empty and must contain `public-obras-report-frame`, so two failed or
   empty renders cannot pass by being equal to each other.
4. **The chrome is still there where it belongs.** Signed in at `/welcome` (a
   `ProtectedRoute` with no `requiredAccess`, so it needs no permission
   fixture): a `<header>` and an `<aside>` are present, and an element carrying
   the sidebar offset class exists. Without this, a change that deleted the
   navigation everywhere would satisfy every other assertion in this task.
5. **No redirect, either way.** In both states, after the route settles,
   `window.location.pathname` is `/c/<slug>/obras` — not `/login`, not `/`.
6. **`/c/<slug>`**, which is three screens, not two: anonymous gets the
   branded sign-in screen, a signed-in non-member gets the no-access panel,
   and a signed-in member is redirected to `/`. Chrome absence is asserted for
   the first two only -- they are the states that stay on this route. For the
   third, only the redirect is asserted: `/` is a chrome-bearing route, so the
   header, the aside and the offset class are expected there, and asserting
   their absence would fail a correct implementation (behaviour unchanged, chrome
   gone). No cross-state HTML equality is asserted here — the screen is
   auth-aware by design.

### Guards

`src/__tests__/themeTokenMigration.test.ts` pins `src/App.tsx` by name and
asserts `matchesIn("src/App.tsx", …)` is `[]`; the file carries **zero**
palette-class occurrences and **zero** rows in
`themeTokenMigration.exceptions.json` today (verified). Editing it therefore
does not move the ledger, provided the edit introduces no palette class — and
it introduces none: `bg-background` and `text-foreground` are tokens. The
per-directory count assertions in that suite cover
`src/features/lot-management/components/` and
`src/features/visitor-management/components/`, neither of which is touched.
The guard's file list is an independently computed walk, so it would pin a new
source file automatically; the new file here is a test, which the walk
excludes.

`docs/frontend/unmapped-colours.md`, `themeTokenMigration.exceptions.json` and
`src/__tests__/brandTextRole.test.ts` are not to be edited. If the
implementation needs any of them edited to pass, the implementation is wrong.

### Allowed paths

Only these may be created or modified:

- `frontend/src/App.tsx`
- `frontend/src/__tests__/PublicRouteChrome.test.tsx` (new)
- `frontend/src/__tests__/AppRouting.smoke.test.tsx` (only if an existing
  assertion in it becomes false; no new coverage belongs here)
- `docs/tasks/APRAS-106-spec.md`, `docs/tasks/APRAS-106-mock.html`

Anything else — page components, `routeAccess.ts`, navigation config, i18n
resources, the guard tests, the exceptions ledger, `docs/frontend/*`, the
backend — is out of bounds for this task.

## Expected Results

- [ ] Mounting the real `App` at `/c/<slug>/obras` with an authenticated
      session renders no `<header>`, no `<aside>`, and no element whose class
      list contains `md:ml-64` or `md:ml-20`.
- [ ] The same three assertions hold for an anonymous visit to the same path.
- [ ] A test renders `/c/<slug>/obras` in both auth states with the same report
      fixture and asserts the two render roots' `innerHTML` are string-equal,
      and additionally asserts that HTML is non-empty and contains
      `public-obras-report-frame`.
- [ ] Signed in at `/welcome`, a `<header>` and an `<aside>` render and an
      element carries the sidebar offset class.
- [ ] `window.location.pathname` is still `/c/<slug>/obras` after the route
      settles in both auth states — no redirect to `/login` or `/`.
- [ ] Visiting `/c/<slug>` **anonymously** renders no `<header>`, no `<aside>`
      and no element whose class list contains `md:ml-64` or `md:ml-20`, and the
      branded sign-in screen still renders.
- [ ] Visiting `/c/<slug>` **signed in as a user who is not a member of that
      condominium** renders no `<header>`, no `<aside>` and no element whose
      class list contains `md:ml-64` or `md:ml-20`, and the no-access panel with
      its own buttons still renders.
- [ ] Visiting `/c/<slug>` **signed in as a member of that condominium** still
      redirects: `window.location.pathname` is `/` once the route settles. No
      assertion is made about chrome in this case -- `/` is a chrome-bearing
      route, so the header, the aside and the offset class are expected there.
- [ ] In `frontend/`, `npm test` and `npm run build` pass, and `npx tsc -b`
      exits 0. `npm run lint` is **not** expected to exit 0: the repository
      carries a pre-existing baseline of lint errors in files unrelated to
      this task, so the check is instead that `npx eslint` reports **zero
      errors and zero warnings for each file this task creates or modifies**,
      and that the repo-wide error count is no higher than at the task's base
      commit.
- [ ] `docs/frontend/unmapped-colours.md`,
      `frontend/src/__tests__/themeTokenMigration.exceptions.json`,
      `frontend/src/__tests__/themeTokenMigration.test.ts` and
      `frontend/src/__tests__/brandTextRole.test.ts` are byte-identical to
      their state at the task's base commit, and every file this task creates
      or modifies lies within `frontend/src/App.tsx`,
      `frontend/src/__tests__/PublicRouteChrome.test.tsx`,
      `frontend/src/__tests__/AppRouting.smoke.test.tsx` and
      `docs/tasks/APRAS-106-*`. The working tree separately carries
      pre-existing uncommitted work belonging to other tasks -- among them
      `docs/suggestions-log.md`, which this project's own workflow appends to
      during a task's pipeline -- which is expected to be present, must be left
      untouched, and must not be counted against this result by a verifier
      reading `git status`.

## Mockup

`docs/tasks/APRAS-106-mock.html` — a before/after, not a composition: the task
removes chrome rather than designing anything, so what is worth seeing is the
report as a signed-in visitor gets it today against the report they will get,
and the same pair for `/c/<slug>`'s no-access panel, which is the one screen
whose appearance visibly changes for a signed-in user.
