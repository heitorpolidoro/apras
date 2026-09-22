# APRAS-74 — Public tenant branding endpoint and `/c/<slug>` branded login

Child 1 of the APRAS-69 split (reasoning: `.meridian/reports/APRAS-69-backlog-1.md`).
Deliverable 3 of `docs/superpowers/specs/2026-09-21-tenant-onboarding-and-branded-entry-design.md`
(D2, D3, D5, D6), minus the landing page, which is APRAS-75.
Mockup: `docs/tasks/APRAS-74-mock.html`.

## Scope

One unauthenticated, rate-limited read that publishes a condominium's public
identity, and one public frontend route that uses it:

- `GET /api/v1/public/tenants/{slug}/branding` — returns `slug`, `name`,
  `logo_url`, `theme` and **nothing else**.
- `/c/:slug` — a public React route that renders the branded login for an
  anonymous visitor, switches a signed-in member into that condominium, and
  shows *"você não tem acesso a este condomínio"* to everybody else.

Not in scope: the public landing page at `/` (APRAS-75 — `/` keeps today's
`ProtectedRoute` + `RootRedirect` and is not touched here); any change to the
tenancy contract (`X-Tenant-Id` stays authoritative, D5); subdomain routing;
slug history or redirects; hardening the `/static/uploads` mount; any change
to the theme *derivation*, which is APRAS-68's and is only consumed here.

**No Alembic migration.** Nothing is stored. The slug column exists
(`0002_tenant_slug`) and the brand data is APRAS-68's revision. This task adds
no file to `backend/alembic/versions/` and does not depend on which revision is
head there — sibling tasks are already landing their own (`0003_tenant_invitation`
from APRAS-71 is in the tree).

## Decisions carried in (do not relitigate)

- **`/c/` prefix, never a bare `/<slug>`** (D2). Subdomains are out of scope.
- **Existence is not a secret** (D3). The branded login is public, slug
  enumeration is accepted, and the single mitigation is per-IP rate limiting.
- **A signed-in non-member sees a message, not a 404** (D3). An unknown slug
  *on the endpoint* is an ordinary 404, because the endpoint is the thing that
  publishes existence and uniforming it would buy nothing.
- **The slug feeds `X-Tenant-Id`, never replaces it** (D5).
- **No timing oracle** (D6): the signed-in decision is a pure array lookup over
  the membership list, with no network request in either branch, taken only
  **after** a readiness gate that is symmetric across both outcomes.
- **APRAS-68 is consumed, not redefined.** The `theme` value is whatever the
  branding module builds for this tenant; this task adds no second derivation
  and no TypeScript port.

## Approach

### Behaviour — backend

`GET /api/v1/public/tenants/{slug}/branding`, unauthenticated (no
`Authorization`, no `X-Tenant-Id`), on a **new** router mounted with prefix
`/public` and tag `public`, with `GLOBAL_SCOPED`
(`Depends(deps.use_global_tenant_scope)`) — never `TENANT_SCOPED`, because the
caller resolves no acting tenant and the fail-closed guard of
`app.core.tenant_context` must not fire. The `/public/` segment makes the
unauthenticated surface visible in the route table itself.

- **200 body, exactly four keys**: `slug`, `name`, `logo_url` (nullable),
  `theme` (nullable). No tenant UUID, no `is_active`, no `disabled_modules`,
  no counts, no plan, no member or user data. A dedicated response schema is
  declared with those four fields; the tenant model is never serialised whole.
- **`theme`** is produced by calling the branding module's theme builder
  (`app.core.branding.build_theme`) with this tenant's stored branding — the
  same call `GET /api/v1/tenant-profile` makes — and is passed through
  verbatim. This task treats the value as opaque JSON: it asserts that it is
  `null` when the tenant has no brand data and non-`null` when it has, and
  asserts nothing about its internal shape, so APRAS-68 may change that shape
  (simple vs. advanced colour modes) without touching this task. There is **no
  "APRAS-68 has not landed" fallback**: the task is `blockedBy` APRAS-68, the
  builder exists before this work starts, and a hard-coded `theme: null`
  delivery is a defect, not a degraded mode.
- **Lookup**: a new `TenantService.get_by_slug(session, slug) -> Tenant | None`
  (the service already owns every other slug operation). Slug matching is
  exact against the stored, normalised slug.
- **404** for an unknown slug, through the ordinary error body — no special
  casing, no uniform response.
- **404 for an inactive tenant as well.** `is_active` is not exposed, and
  `deps._resolve_from_header` refuses an inactive tenant to everyone including
  administrators, so a branded login into it could never succeed; answering
  200 would advertise a door that is nailed shut. Stated here because it is a
  judgement call, not a given.
- **Rate limit**: `@limiter.limit("30/minute")` from `app/core/limiter.py`
  (`get_remote_address` key func, already wired in `app/main.py` with a 429
  handler), following the `auth/login` `5/minute` decorator shape **including**
  the `request: Request  # noqa: ARG001  # slowapi's @limiter.limit requires
  this parameter by name` first parameter. 30/min is one branded login plus its
  reloads and makes a slug sweep expensive. Note that
  `backend/tests/conftest.py:24` disables the limiter for the whole suite
  (`app.state.limiter.enabled = False`), so the 429 case must re-enable it
  around itself and restore it in a `finally`, exactly as
  `backend/tests/test_rate_limit.py` already does.

### Behaviour — registries

- `UNGUARDED_ROUTES` **+1**: the route is unauthenticated and maps to no
  catalogue permission. Every `len(UNGUARDED_ROUTES) == N` assertion moves by
  one — currently `tests/test_permission_registry.py` (two sites),
  `tests/test_permission_parity_matrix.py`, `tests/test_superuser_grant.py`,
  `tests/test_tenant_modules_api.py`.
- `GLOBAL_ROUTES` **+1** in `tests/test_tenant_route_scope.py`, plus the
  allowlist entry itself and its reason comment.
- `FULLY_UNGUARDED_TAGS` in `tests/test_permission_registry.py` gains
  `"public"` (exact-set assertion).
- `test_permission_parity_matrix.py`'s
  `test_the_twenty_four_unguarded_routes_are_the_only_ones_excluded` is
  **renamed to the new count** and its per-task docstring gains one sentence for
  this route, following the convention already in that docstring — so the second
  of APRAS-71/74 to land does not leave a test name contradicting its own
  assertion. The new number is read from the tree at implementation time.
- `ROUTE_PERMISSIONS` gains nothing, no new permission string is minted, no
  parity cell moves, so `tests/data/parity_matrix_baseline.json` stays
  byte-identical and no additive baseline file is needed.
- **Counts are deltas, never absolutes.** APRAS-71 moves the same two
  constants. Whichever of the two lands second re-reads the numbers from the
  tree and adds **one** to what it finds; the same applies to the
  `FULLY_UNGUARDED_TAGS` textual collision (APRAS-71 adds `"invitations"`).

### Behaviour — frontend

`/c/:slug` is registered in `frontend/src/App.tsx` among the public routes
(next to `/login`, `/signup`, `/forgot-password`), with **no** `ProtectedRoute`
wrapper, no `requiredAccess` rule, no `ROUTE_ACCESS` and no `NAV_ITEMS` entry.
It renders a new `BrandedEntryPage`.

The page always issues the branding fetch, anonymous or not, and renders the
condominium's name and logo from it. While the fetch is in flight it shows the
existing spinner; if the fetch 404s or errors it falls back to the unbranded
form and copy (an unknown slug must not blank the screen).

**Readiness gate (the cold load is the main entry path).** A branded link is
normally opened by direct navigation, so on mount `useAuth().isLoading` is
`true`, `isAuthenticated` is `false` and `useTenant().tenants` is `[]`: the
membership list is a React Query subscription with `enabled: isAuthenticated`
(`TenantContext.tsx:52`) that cannot even start before `/auth/me` answers
(`AuthContext.tsx:27`). Resolving on mount would therefore show a legitimate
member the anonymous login, then the *"você não tem acesso"* panel, and only
then switch them. The page must not do that.

The page renders **nothing but the spinner** while

```
useAuth().isLoading || (useAuth().isAuthenticated && useTenant().isLoading)
```

— both flags are already on the context values (`useTenant.ts` exposes
`isLoading`; `AuthContext` exposes it at line 92). The same expression covers
the post-login path: `AuthContext.login` flips `isAuthenticated`, which enables
the `["tenants"]` query, which puts `useTenant().isLoading` back to `true`
until the memberships actually arrive. Resolution is therefore driven by the
current context values on every render (or an effect keyed on them), **never
by a one-shot mount effect**, so a list that arrives late still resolves.

The gate is **symmetric**: the same spinner, in the same place, for the same
duration, precedes *both* the unknown-slug panel and the not-a-member panel —
and the branding fetch runs underneath it identically in both cases. Without
that, the loading state would reinstate exactly the timing oracle D6 forbids.
An implementation may not gate one branch and not the other. If, at
implementation time, a commit is observed in which the gate has cleared but the
membership list has not settled, the fix is to widen the gate — never to render
a panel on an unsettled list.

**Signed-in resolution (ER: no oracle).** Once the gate has cleared, `slug → id`
is resolved by a pure array lookup over `useTenant()`'s `tenants` — the
`GET /tenants` payload the switcher already uses. **No network
request is issued in either branch**, so an unknown slug and a known slug the
user does not belong to execute literally the same code path and render the
same component; there is nothing to time because there is no I/O. The branding
fetch is issued identically in both cases and its result never feeds the
decision. Using the switcher's own option list is also what makes "`/c/<slug>`
opens" and "appears in the dropdown" structurally unable to disagree,
superusers included.

- Match, and it is **not** the acting tenant → `setActingTenant(id)` (the
  existing `TenantContext` function, unchanged: it evicts every non-`["tenants"]`
  query, exactly as a dropdown switch does) then
  `navigate("/", { replace: true })`.
- Match, and it **is** already the acting tenant → navigate without touching
  switcher state at all.
- No match → a `RestrictedAccessMessage`-shaped panel carrying the new
  `publicEntry.noAccess` string. Never a 404, never a redirect. The panel
  carries two actions: *"Ir para os meus condomínios"* (`navigate("/")`,
  rendered only when the signed-in user has at least one membership) and
  *"Sair"* (`AuthContext.logout`, after which the same route re-renders as the
  anonymous branded login). Both affordances depend solely on the **user's own**
  membership list, never on the slug, so they are byte-identical between the
  unknown-slug and the not-a-member branch and do not weaken D6.
- Anonymous → the branded login form. The submit path is **not duplicated**: a
  `LoginForm` component is extracted out of `LoginPage` — the email/password/
  remember-me fields, the error modal and `handleSubmit`'s
  `POST /auth/login` + `AuthContext.login` sequence — and both `LoginPage` and
  `BrandedEntryPage` render it. `LoginForm` takes the post-success behaviour as
  a prop (`onSuccess`, or an explicit redirect target) so `LoginPage` keeps its
  `location.state.from` navigation while `BrandedEntryPage` runs the slug
  resolution instead. The dev-users quick-login block, the page chrome and the
  signup/forgot links stay in `LoginPage`; only the form moves.
  **`LoginPage`'s existing tests must stay green through the extraction**
  (`LoginPage.test.tsx`, `LoginPage.navigation.test.tsx`,
  `LoginPage.devUsers.test.tsx`), unmodified except where a selector genuinely
  moved; they are the proof that the refactor changed no behaviour.

  After a successful branded login, `isAuthenticated` flips and the membership
  query starts, so the page re-enters the readiness gate above and resolves
  `slug → id` only once the memberships have arrived; a user who authenticates
  successfully but does not belong then sees the same no-access panel.
  `X-Tenant-Id` continues to be attached by the Axios interceptor from
  `tenantState` — the slug feeds it, never replaces it (D5).

**Theming the page.** The branded page injects the returned `theme` through the
same DOM injector APRAS-68 ships (the `<style>` element written into
`document.head`), under its own element id **`public-brand-theme`** (APRAS-68
owns `tenant-brand-theme`; the two ids must differ so each is assertable on its
own), mounted only while the page is rendered and removed on unmount. It injects **only when the visitor is
anonymous**, so the authenticated injector (which themes from the acting
tenant's profile) and this one can never fight over the same variables; a
signed-in visitor is either redirected out immediately or shown the no-access
panel, neither of which needs the branding. `theme: null` and an errored fetch both mean: inject nothing at all, render the
default palette.

`Tenant` in `frontend/src/types/auth.ts` gains `slug: string` — the only type
change; `TenantRead` already carries it (APRAS-66).

### Files touched

Backend
- `backend/app/api/v1/endpoints/public_branding.py` — new: the router, the
  rate-limited handler, the 404s, and a module docstring recording why it is
  `GLOBAL_SCOPED` and why existence is public.
- `backend/app/api/v1/api.py` — import and `include_router(prefix="/public", tags=["public"], dependencies=GLOBAL_SCOPED)`.
- `backend/app/schemas/tenant.py` — `PublicTenantBrandingRead` (four fields).
- `backend/app/services/tenant_service.py` — `get_by_slug`.
- `backend/app/core/permissions.py` — one `UNGUARDED_ROUTES` entry with its reason comment.
- `backend/tests/test_public_branding.py` — new.
- `backend/tests/test_permission_registry.py` — count +1 (two sites) and `FULLY_UNGUARDED_TAGS` gains `"public"`.
- `backend/tests/test_tenant_route_scope.py` — allowlist entry, comment, count +1.
- `backend/tests/test_permission_parity_matrix.py`, `backend/tests/test_superuser_grant.py`, `backend/tests/test_tenant_modules_api.py` — the remaining `len(UNGUARDED_ROUTES)` assertions, +1 each.

Frontend
- `frontend/src/api/publicBranding.ts` — new: the response type and the fetch (plain `apiClient` GET; the interceptor's header is harmless on a global route).
- `frontend/src/features/user-administration/pages/BrandedEntryPage.tsx` — new: the readiness gate plus the three visitor states.
- `frontend/src/features/user-administration/components/LoginForm.tsx` — new: the form fields, error modal and `POST /auth/login` + `AuthContext.login` submit, extracted from `LoginPage`, with the post-success behaviour as a prop.
- `frontend/src/features/user-administration/pages/LoginPage.tsx` — renders `LoginForm` in place of its inline form and `handleSubmit`; keeps the dev-users block, page chrome and links, and its existing tests.
- `frontend/src/App.tsx` — the `/c/:slug` route only.
- `frontend/src/types/auth.ts` — `Tenant.slug`.
- `frontend/src/i18n/locales/pt.json`, `frontend/src/i18n/locales/en.json` — a new `publicEntry.*` block, key-identical in both files.
- `frontend/src/features/user-administration/__tests__/BrandedEntryPage.test.tsx` — new.

### Test criteria

Backend (`test_public_branding.py`)
- 200 with **no** `Authorization` and **no** `X-Tenant-Id` header.
- The response key set **equals** `{"slug", "name", "logo_url", "theme"}` —
  asserted as an equality so a future field cannot leak in — and none of
  `id`, `is_active`, `disabled_modules`, `plan`, `brand_color` appears.
- Unknown slug → 404 with the ordinary error body.
- Inactive tenant → 404.
- `theme` is `null` for a tenant with no brand data and non-`null` for one that
  has it — both asserted, unconditionally, with no skip and no fallback.
- The 31st request from the same client inside a minute → 429 through the
  existing handler, with the limiter re-enabled around the case and restored in
  a `finally` (per `tests/test_rate_limit.py`) and its state reset so the case
  is order-independent.

Backend (registries)
- `test_permission_registry.py`, `test_tenant_route_scope.py` and the three
  other count assertions pass with the +1 values read from the tree at
  implementation time; `FULLY_UNGUARDED_TAGS` contains `"public"`;
  `tests/data/parity_matrix_baseline.json` is unchanged by `git diff`.

Frontend (`BrandedEntryPage.test.tsx`)
- **Cold load, member arriving before `/tenants` answers**: with
  `useAuth().isLoading === true` (and again with `isAuthenticated === true`,
  `useTenant().isLoading === true`, `tenants === []`), the page renders the
  spinner and **neither** the login form **nor** the no-access panel; when the
  membership list then resolves, `setActingTenant` is called and the page
  navigates. Asserted for a member, so the regression the gate exists to
  prevent is the case under test.
- **The gate is symmetric**: in the same loading states, a known-but-not-mine
  slug and an unknown slug render the identical spinner — the same query for
  the spinner matches in both, and no panel text is present in either.
- Anonymous: renders the branded login with the condominium's name and logo
  from a mocked branding response; submitting calls the login path.
- The anonymous form is the extracted `LoginForm` (the same component
  `LoginPage` renders), and `LoginPage.test.tsx`,
  `LoginPage.navigation.test.tsx` and `LoginPage.devUsers.test.tsx` all still
  pass.
- Signed-in member: `setActingTenant` is called with that tenant's id and the
  page navigates to `/` with `replace: true`.
- Signed-in, slug already the acting tenant: navigates without calling
  `setActingTenant`.
- Signed-in non-member **and** unknown slug: both render the *same* no-access
  message, and **no request is made in either case** for the resolution —
  asserted by the mocked client recording exactly the one branding call, the
  same call in both cases.
- `theme: null` → no `#public-brand-theme` element is added; a theme → exactly
  one is added and it is removed on unmount.

Gates
- Backend: pytest green at the 90% coverage gate, `ruff check` and
  `ruff format --check` clean. `assert_no_skips`' `MIN_CASES` covers
  `tests/test_migrations_postgres.py` only, and **this task adds no migration
  and no case to that module, so `MIN_CASES` must not move**; the equality
  check in `test_assert_no_skips.py` must still pass against the value in the
  tree (re-read it, do not assume 26 — APRAS-68/71 move it).
- Frontend: `tsc -b` clean; vitest thresholds **80 lines / 78 functions / 76
  branches / 80 statements**; eslint diff-scoped against the baseline of 375
  errors and 2 warnings across 64 files; `pt.json` and `en.json` key-identical.

## Expected Results

- [ ] `GET /api/v1/public/tenants/{slug}/branding` answers 200 with no `Authorization` and no `X-Tenant-Id` header, and its JSON key set equals exactly `{slug, name, logo_url, theme}` — no tenant id, `is_active`, `disabled_modules`, counts, plan or member data, asserted by an equality test.
- [ ] The endpoint answers 404 for an unknown slug and for an inactive tenant, and answers 429 on the 31st request from the same IP inside a minute via `@limiter.limit("30/minute")` on the existing slowapi limiter.
- [ ] The router is mounted `GLOBAL_SCOPED` under `/public` with tag `public`: `test_tenant_route_scope.py` passes with `GLOBAL_ROUTES` grown by exactly one, `UNGUARDED_ROUTES` grown by exactly one across all five count assertions, `FULLY_UNGUARDED_TAGS` containing `"public"`, `test_permission_parity_matrix.py`'s unguarded-count test renamed to the count it now asserts, and `tests/data/parity_matrix_baseline.json` byte-identical.
- [ ] `theme` is the value returned by the branding module's theme builder for that tenant, passed through unmodified, and is `null` when the tenant has no brand data; no colour derivation exists in this task's backend or frontend code.
- [ ] Visiting `/c/<slug>` while anonymous renders a login form carrying that condominium's name and logo; a successful login lands the user inside that condominium, with `X-Tenant-Id` still attached by the Axios interceptor.
- [ ] The branded login and `/login` render the **same** extracted `LoginForm` component — the `POST /auth/login` + `AuthContext.login` submit exists in exactly one file, greppable as one occurrence — and `LoginPage.test.tsx`, `LoginPage.navigation.test.tsx` and `LoginPage.devUsers.test.tsx` all pass after the extraction.
- [ ] A signed-in member who opens `/c/<slug>` before `GET /tenants` has answered sees only a spinner — never the anonymous login and never the no-access panel — and is switched into the condominium once the membership list resolves; a test drives the `useAuth().isLoading` and `useTenant().isLoading` states explicitly.
- [ ] The loading gate is symmetric: in those same pre-resolution states an unknown slug and a known slug the user does not belong to render the identical spinner, with no panel text in either, proven by one test asserting both branches.
- [ ] Visiting `/c/<slug>` while signed in as a member calls `setActingTenant` with that tenant's id and navigates to `/` with `replace: true`; when the slug is already the acting tenant it navigates without calling `setActingTenant`.
- [ ] A signed-in non-member and an unknown slug render the identical "você não tem acesso a este condomínio" panel — never a 404 and never a redirect — and a test proves both branches execute the same code path with no resolution request in either; the panel's actions ("Ir para os meus condomínios", "Sair") depend only on the user's own membership list and are identical across the two branches.
- [ ] `/c/:slug` is public: no `ProtectedRoute`, no `requiredAccess`, no `ROUTE_PERMISSIONS`, `ROUTE_ACCESS` or `NAV_ITEMS` entry, and no new permission string; `/` is untouched by this task.
- [ ] No Alembic revision is added and `MIN_CASES` in `backend/scripts/assert_no_skips.py` is unchanged, with `test_assert_no_skips.py`'s equality check still green.
- [ ] Gates pass: backend pytest at the 90% gate with ruff clean; frontend `tsc -b` clean, vitest at 80 lines / 78 functions / 76 branches / 80 statements, diff-scoped eslint against the 375 errors + 2 warnings baseline, and `pt.json`/`en.json` key-identical.

## Out of Scope

The public landing page at `/` (APRAS-75), subdomain routing, public
self-service tenant creation, slug history and redirects, static-upload access
control, and any change to how the theme is derived (APRAS-68).
