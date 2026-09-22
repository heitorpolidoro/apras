# APRAS-75 — Serve a public landing page at `/` to anonymous visitors

Child 2 of the APRAS-69 split (reasoning: `.meridian/reports/APRAS-69-backlog-1.md`).
Deliverable 3 of `docs/superpowers/specs/2026-09-21-tenant-onboarding-and-branded-entry-design.md`,
landing half only. Carries APRAS-69's ER-1.

## Scope

`/` stops being wrapped in `ProtectedRoute`. An anonymous visitor gets a new
public `LandingPage`; an authenticated visitor keeps today's behaviour at `/`,
byte-for-byte. The page's **structure** is specified here — hero, exactly four
capability blocks, an "entrar" CTA to `/login`, a footer. Its **copy is not**:
what APRAS does, for whom, and the selling argument are an operator input that
does not exist yet, and inventing it is out of bounds.

### Implementation precondition — the operator's copy

**This task cannot start until the operator supplies the landing copy.** That
is a listed input, not a risk to be managed during implementation, and the
delay is deliberate. `LANDING_COPY_TODO` is a tripwire, not a shipping state:
a PR that still carries the marker in any locale value is **not done** (ER-6).
The implementer writes the operator's strings into `pt.json` and `en.json`,
and the marker test is green in the PR that closes this task. There is no
third outcome: the task does not ship with the marker and does not weaken or
skip the test.

Not covered: the branding endpoint, `/c/<slug>`, the branded login and the
tenant switch (all APRAS-74, which this task is blocked by because both edit
`App.tsx`'s route table and the landing's CTAs link at routes APRAS-74 adds);
white-label theming (APRAS-68); any change to the other 38 routes; any change
to `Navbar` or `AppLayoutContent`; any backend change.

## Approach

### Behavior

1. **The route.** The `/` route in `frontend/src/App.tsx` (today lines 441-448,
   `<Route path="/" element={<ProtectedRoute><RootRedirect /></ProtectedRoute>} />`)
   loses its `ProtectedRoute` wrapper and becomes
   `<Route path="/" element={<RootRedirect />} />`. No other route is touched.

2. **The branch lives inside `RootRedirect`** (`App.tsx:65-71`), not around it.
   `RootRedirect` additionally reads `useAuth()`:
   - `isLoading` → the existing `<Spinner />`;
   - `!isAuthenticated` → `<LandingPage />`;
   - authenticated → today's body verbatim: `<Spinner />` while
     `usePermissionSet()` is loading, then `<GeneralDashboardPage />`.

   `usePermissionSet()` is a hook and must still be called unconditionally, at
   the top of the component, before any of the three returns.

3. **No redirect is introduced anywhere.** AGENTS.md's "no route ever bounces a
   caller" invariant holds: no `<Navigate>`, no `navigate()`, no
   `window.location` assignment is added by this task. The anonymous visitor
   stays on `/` and sees the landing; only the CTA, on click, navigates.

4. **Chrome.** `Navbar` returns `null` when `!isAuthenticated` and
   `AppLayoutContent` already omits the sidebar offset on the same condition,
   so the landing renders chrome-free with no change to either file. Do not
   edit them.

5. **Page structure** (`LandingPage`), in DOM order:
   - a hero: product name, a headline, a sub-headline, and the primary CTA;
   - **exactly four** capability blocks, each a heading plus one short
     paragraph, each with a Lucide icon, all four inside a single
     `<section data-testid="landing-capabilities">`;
   - a repeat-CTA band below that section, whose heading **is an `<h2>`** and
     is deliberately **outside** `landing-capabilities`;
   - an "entrar" CTA rendered as a react-router `<Link to="/login">`, present
     in the hero and repeated once in that band;
   - a footer line.

   Semantics are load-bearing for the tests: one `<h1>` in the hero, one
   `<h2>` per capability block, `<footer>` for the footer. The page therefore
   contains five `<h2>` elements in total, but **exactly four within
   `[data-testid="landing-capabilities"]`** — every capability assertion is
   scoped to that section (`within(screen.getByTestId("landing-capabilities"))`),
   never to the document. The page is responsive
   (single column below `md`) and uses the existing Tailwind/shadcn tokens
   (`bg-background`, `text-foreground`, `--primary`) — no new colour literals,
   so APRAS-68's runtime theme override applies to it for free later.

6. **Every string is an operator input.** Every visible string comes from
   `useTranslation()` under a new `landing.*` namespace in both
   `src/i18n/locales/pt.json` and `src/i18n/locales/en.json`. Until the
   operator supplies copy, **every one of those values is the exact single
   token `LANDING_COPY_TODO`**, in both locales — not lorem ipsum, not a
   plausible-sounding draft, not an English string parked in the pt file. The
   two locales carry the identical key set, as `i18n/__tests__/parity.test.ts`
   already enforces. No hard-coded user-visible string in the TSX.

7. **The marker cannot ship.** A test in
   `frontend/src/i18n/__tests__/parity.test.ts` asserts, in one place, both
   halves: (a) **negative** — no value in either locale file contains
   `LANDING_COPY_TODO`; (b) **positive** — the flattened `landing.*` key set
   is non-empty, holds the expected number of keys, and is identical in pt and
   en, in the style the file already uses for module/action counts. The
   positive half is what stops (a) from passing vacuously by never adding the
   namespace at all. Because the copy is an implementation precondition
   (see Scope), that test is **green in the delivered PR**. Skipping it is not
   an escape hatch — the repo forbids skipped tests
   (`backend/scripts/assert_no_skips.py` on the backend, same discipline on
   the frontend).

### Files touched

- `frontend/src/App.tsx` — drop `ProtectedRoute` from the `/` route only; add
  the `useAuth()` branch and the `LandingPage` import inside `RootRedirect`.
- `frontend/src/features/public-site/pages/LandingPage.tsx` — new; the page
  described above. `frontend/src/features/public-site/` is the agreed
  directory name for anonymous-facing screens (today `frontend/src/features/`
  has none); if APRAS-74 landed first it must already exist — reuse it, and
  do not mint a second public directory under another name.
- `frontend/src/i18n/locales/pt.json` — new `landing` namespace, all values
  `LANDING_COPY_TODO` until copy arrives.
- `frontend/src/i18n/locales/en.json` — same keys, same rule.
- `frontend/src/__tests__/RootRedirect.test.tsx` — the file holds **four**
  cases today (lines 63, 79, 88, 99), all four authenticated: three dashboard
  cases and "holds a spinner while the query is still settling", which is a
  `usePermissionSet()` loading case (`useMyPermissions` → `isPending: true`,
  `useAuth` → `isAuthenticated: true`). **All four stay exactly as they are
  and keep passing.** Two cases are *added*:
  - **anonymous**: `useAuth()` → `{ isAuthenticated: false, isLoading: false }`
    renders the landing;
  - **auth-loading**: `useAuth()` → `{ isLoading: true }` renders the spinner
    and not the landing. This is a *new, distinct* case — it exercises the
    `useAuth` loading branch, not the pre-existing `usePermissionSet` one, and
    must not be folded into or replace the case at line 99.
- `frontend/src/__tests__/AppRouting.smoke.test.tsx` — the case at line 136,
  `it("redirects an unauthenticated visit to / onto the login form", ...)`,
  asserts the behaviour this task deliberately reverses. It is **rewritten,
  not deleted**: same position, renamed to describe the landing, asserting
  `window.location.pathname === "/"`, a landing-only element present, and no
  login form (`screen.queryByLabelText("E-mail")` is null). The sibling cases
  at line 118 (`/dashboard`) and line 127 (`/tasks`) are **not touched and
  must stay green** — they are the mechanical proof that only `/` lost its
  guard.
- `frontend/src/features/public-site/__tests__/LandingPage.test.tsx` — new.
- `frontend/src/i18n/__tests__/parity.test.ts` — add the marker assertion.

### Test criteria

- `RootRedirect` with `useAuth()` → `{isAuthenticated: false, isLoading: false}`
  renders the landing (asserted by a landing-only element) and renders neither
  `GeneralDashboardPage` nor any routed destination — proving no redirect.
- `RootRedirect` with `useAuth()` → `{ isLoading: true }` renders the spinner
  (`container.querySelector(".animate-spin")`) and not the landing.
- All **four** pre-existing `RootRedirect` cases (lines 63, 79, 88, 99),
  including the `usePermissionSet` loading case, still pass unmodified.
- `AppRouting.smoke.test.tsx`: the rewritten case at line 136 shows `/`
  unauthenticated rendering the landing with `window.location.pathname === "/"`
  and no login form; the `/dashboard` and `/tasks` cases still pass unmodified.
- `LandingPage` renders exactly one `<h1>`, exactly four `<h2>` elements
  **within `[data-testid="landing-capabilities"]`**, at least one
  `<a href="/login">`, and a `<footer>`.
- Locale parity: the `landing.*` key set is non-empty and identical in pt and
  en; no value in `pt.json` or `en.json` contains `LANDING_COPY_TODO`.

### Gates

No Alembic migration — this task is presentational frontend and stores nothing.
No backend route: `UNGUARDED_ROUTES` and `GLOBAL_ROUTES` are untouched here
(that `+1` collision belongs to APRAS-74). `backend/scripts/assert_no_skips.py`
holds `MIN_CASES`, compared by **equality** in `test_assert_no_skips.py` — it
must still match if the case count moves. Frontend: `tsc -b` clean; vitest
coverage thresholds 80 lines / 78 functions / 76 branches / 80 statements;
eslint diff-scoped against the baseline of 375 errors + 2 warnings across 64
files.

### Mockup

![Landing structure mockup](APRAS-75-mock.html) — `docs/tasks/APRAS-75-mock.html`.
It shows the **structure** with visibly placeholder copy. The placeholder text
in the mock is not a copy proposal and must not be lifted into the code.

## Expected Results

- [ ] Visiting `/` while unauthenticated renders the landing page at URL `/`,
      with no redirect and no login form.
- [ ] Visiting `/` while authenticated still renders `GeneralDashboardPage`,
      after a spinner while the permission set settles.
- [ ] `/` is the only route whose definition changes; no `ProtectedRoute` is
      removed from any other route, and no `<Navigate>` or `navigate()` call is
      added anywhere by this task.
- [ ] `LandingPage` renders exactly one `<h1>`, exactly four `<h2>` elements
      inside `[data-testid="landing-capabilities"]` (the repeat-CTA band's
      `<h2>` sits outside that section and is not counted), at least one link
      to `/login`, and a `<footer>`.
- [ ] `frontend/src/__tests__/AppRouting.smoke.test.tsx`: the `/` case is
      rewritten to assert the landing at `window.location.pathname === "/"`
      with no login form, and the `/dashboard` and `/tasks` unauthenticated
      redirect cases pass unmodified.
- [ ] Every user-visible string on the landing page resolves through
      `useTranslation()` from the `landing.*` namespace, present with an
      identical key set in both `pt.json` and `en.json`.
- [ ] A test asserts both that no value in either locale file contains
      `LANDING_COPY_TODO` and that the `landing.*` key set is non-empty and
      identical in pt and en, and that test passes — i.e. operator-supplied
      copy is in the locale files.
- [ ] `frontend/src/__tests__/RootRedirect.test.tsx` adds a `useAuth`
      anonymous case and a `useAuth` `isLoading: true` case, and its four
      pre-existing cases (lines 63, 79, 88, 99) pass unmodified.
- [ ] `npx tsc -b` is clean and `npm run test:coverage` passes the 80 lines /
      78 functions / 76 branches / 80 statements thresholds.
- [ ] `npx eslint .` in `frontend/` reports no new violation against the
      baseline of 375 errors + 2 warnings across 64 files.
- [ ] `backend/tests/test_assert_no_skips.py` passes, i.e. `MIN_CASES` still
      equals the collected case count.
- [ ] No Alembic migration is added; `UNGUARDED_ROUTES` and `GLOBAL_ROUTES`
      counts are unchanged by this task.

## Out of Scope

- The public branding endpoint, `/c/<slug>`, the branded login, the tenant
  switch and the no-access panel (APRAS-74).
- White-label theming and `build_theme` (APRAS-68).
- Any change to `Navbar`, `AppLayoutContent`, `ProtectedRoute`, `ROUTE_ACCESS`
  or `NAV_ITEMS`.
- Subdomain-based tenant entry (recorded future study, D2).
- Writing the marketing copy. It is the operator's input; this task provides
  the slots and the mechanism that refuses to ship without it.
