# APRAS-69 — Landing page pública e /c/<slug> com login da marca do condomínio

## Status at HEAD: this is a closure task, not a build task

APRAS-69 is the **parent** of APRAS-74 and APRAS-75, both `done`. Most of the
card's seven original results are already in `master`. This spec exists to
(a) record, result by result, what delivered each one, (b) specify the single
behavioural clause that is **not** actually proven by any test at HEAD, and
(c) correct `AGENTS.md`, which still documents a product with no public
surface at all.

### The seven original results, quoted, and what delivered each

The card's `expected_results` as originally captured, verbatim, numbered:

1. "/ serves a public landing page to an anonymous visitor and keeps today's
   RootRedirect behaviour for an authenticated one; this is the only change to
   existing routing."
2. "/c/<slug> renders a login screen carrying the condominium's name, logo and
   colours, from a new public endpoint that returns ONLY those fields - never
   user counts, active modules, or anything describing the condominium
   internally."
3. "That endpoint is rate-limited per IP using the project's existing slowapi
   limiter, and a test proves the limit engages."
4. "An anonymous visitor who logs in at /c/<slug> lands inside that tenant; a
   signed-in user who belongs to it switches to it and continues; one who does
   not belong sees 'você não tem acesso a este condomínio' - not a 404."
5. "An unknown slug takes a code path comparable to the no-access case, so
   response timing does not reinstate the existence oracle the copy avoids."
6. "The slug feeds X-Tenant-Id rather than replacing it: the frontend resolves
   slug to id and keeps sending the header, so the backend contract is
   unchanged."
7. "Backend pytest green with the 90% gate, ruff clean; frontend tsc -b, vitest
   (80/78/76/80) and diff-scoped eslint pass; pt.json and en.json stay
   key-identical."

Accounting, per number:

* **1 — delivered by APRAS-75, commit `2c58a76`.** Detailed below.
* **2 — delivered by APRAS-74, commit `0232c4e`.** Detailed below.
* **3 — delivered by APRAS-74, commit `0232c4e`.** Detailed below.
* **4 — partially delivered by APRAS-74, commit `0232c4e`.** The two
  signed-in halves are covered; the **anonymous** half is the gap this task
  closes (see "Result 4 — the one real gap").
* **5 — delivered by APRAS-74, commit `0232c4e`**, and extended here across
  the login continuation (see "Result 5, stated honestly").
* **6 — delivered by APRAS-74, commit `0232c4e`.** Detailed below.
* **7 — discharged by no child, and by no sibling.** It was never given to
  APRAS-74 or APRAS-75 as a result of theirs: it is a gate on **this** card's
  own delivery — the repository-wide green state that must hold when APRAS-69
  is closed. It is therefore carried forward unchanged as expected result 7
  below, and this task must satisfy it with its own diff in the tree.

### Result 1 — public landing at `/`

**Delivered in full by APRAS-75, commit `2c58a76`.** `frontend/src/App.tsx:484`
routes `/` to `RootRedirect` with no `ProtectedRoute` wrapper; `RootRedirect`
(`App.tsx:74`) renders `LandingPage` for an anonymous visitor and reproduces
the previous behaviour — spinner until the permission set settles, then
`GeneralDashboardPage` — for an authenticated one. `RootRedirect.test.tsx` and
`AppRouting.smoke.test.tsx` pin both branches. **This task builds nothing for
result 1 and must not touch the root route.** Its only remaining cost is the
statement that `/` is untouched, which expected result 1 below makes checkable
by diff scope.

### Results 2, 3, 5, 6 — the public endpoint, its rate limit, the oracle, the header

**Delivered by APRAS-74, commit `0232c4e`**, on top of APRAS-66's slug column.

* `GET /api/v1/public/tenants/{slug}/branding`
  (`backend/app/api/v1/endpoints/public_branding.py`) is mounted `GLOBAL_SCOPED`
  and unguarded, and returns `PublicTenantBrandingRead`.
* **The public allowlist is exactly four fields** (`backend/app/schemas/tenant.py`,
  `PublicTenantBrandingRead`), and this task neither adds nor removes one:
  `slug` (str), `name` (str), `logo_url` (str | null), `theme`
  (`build_theme(tenant.brand_theme)`, or null). Everything else on the row is
  **excluded by decision**: `id`, `is_active`, `disabled_modules`,
  `brand_theme` (the raw stored object), `created_at`, `updated_at`, plus every
  count, plan, module and member fact. The schema is declared standalone —
  never as a subset of `TenantProfileRead` or of the `Tenant` model — and
  `backend/tests/test_public_branding.py::test_the_body_carries_exactly_four_keys`
  asserts the key set as an **equality**, so a fifth field fails CI.
* The rate limit is the project's own `slowapi` limiter
  (`app.core.limiter.limiter`, `key_func=get_remote_address`), applied as
  `@limiter.limit("30/minute")` under the `request: Request` parameter slowapi
  requires by name — the same shape `auth.py` and `invitations.py` use.
  `test_the_thirty_first_request_inside_a_minute_is_429` proves it engages.
* `X-Tenant-Id` is untouched (result 6): the slug is resolved to an id on the
  client and fed to `setActingTenant`, and `src/api/client.ts:50` keeps
  attaching the header. `BrandedEntryPage.tenantHeader.test.tsx` asserts the
  next request carries the resolved id.

### No migration

`tenant.slug` already exists — `backend/app/models/tenant.py` (`VARCHAR(64)`,
`NOT NULL`, unique, indexed) with revision
`backend/alembic/versions/0002_tenant_slug.py` already applied in production.
**This task adds no Alembic revision and must not edit `0001`.**

### Result 4 — the one real gap

The signed-in halves of result 4 are proven: `BrandedEntryPage.test.tsx`
covers member→switch→`/` and non-member→panel. The **anonymous** half —
"an anonymous visitor who logs in at `/c/<slug>` lands inside that tenant" —
is not. `BrandedEntryPage.test.tsx` mocks `useAuth` and `useTenant` wholesale,
so its login test stops at `expect(mockLogin).toHaveBeenCalled()`: the
continuation that actually delivers the promise (token accepted →
`isAuthenticated` flips → `["tenants"]` query runs → readiness gate reopens →
`setActingTenant(id)` → `/`) has no coverage anywhere, because every link in
that chain is a mock in that file. That chain is this task's deliverable.

## Scope

**In scope:** one new frontend integration test file exercising the
anonymous-login continuation at `/c/<slug>` against the *real* `AuthProvider`
and `TenantProvider`, and the `AGENTS.md` correction.

**Out of scope:** any backend change; any Alembic revision; any change to `/`,
to `RootRedirect`, to `LandingPage`, to `BrandedEntryPage`, to
`public_branding.py`, to the four-field allowlist, to the rate limit, or to
`pt.json` / `en.json`. No new i18n key. No UI is introduced or redesigned, so
this task ships **no** `docs/tasks/APRAS-69-mock.html`; APRAS-74's and
APRAS-75's mocks remain the visual record of the two screens.

## Approach

### Behavior

Prove the anonymous→inside-the-tenant path end to end, and prove the
no-access path survives the same continuation, without changing product code.

### Files touched

* `frontend/src/features/user-administration/__tests__/BrandedEntryLogin.integration.test.tsx`
  — new. Follows the harness of `frontend/src/__tests__/TenantBootstrapOrder.test.tsx`
  in kind: mock **only** `src/api/client`, recording each request's URL
  together with the acting-tenant mirror value read at issue time (the same
  module-level mirror the real Axios interceptor reads to build `X-Tenant-Id`;
  the mocked client builds no headers, so the assertion is on the recorded
  mirror value, not on a header object); nothing under `src/features/**` is
  mocked. Unlike `TenantBootstrapOrder.test.tsx`, which renders the real
  `App`, this file declares its own `MemoryRouter` route table with exactly two
  routes: `/c/:slug` → the real `BrandedEntryPage`, and `/` → the **real
  `RootRedirect`** from `src/App.tsx` (not a sentinel), so the landing
  destination is observable and the post-login render matches production.
  Because `RootRedirect` calls `usePermissionSet()`, the mocked client must
  answer `GET /permissions/me` as well, or the test hangs.
* `AGENTS.md` — route-map rows for `/` (public landing for an anonymous
  visitor, `GeneralDashboardPage` for an authenticated one) and `/c/:slug`
  (public, `BrandedEntryPage`); an endpoints-table row for the `/api/v1/public`
  prefix → `backend/app/api/v1/endpoints/public_branding.py`; and correction of
  the paragraph at **`AGENTS.md:58-64`**, whose current text says `/` "renders
  the general dashboard for **every** authenticated caller" and describes no
  anonymous branch at all.
* `docs/tasks/APRAS-69-spec.md` — this file.

### Test criteria

Three cases in the new file, all driven from the anonymous state:

1. **Member.** `GET /public/tenants/<slug>/branding` → the four-field body;
   the visitor fills and submits the branded `LoginForm`;
   `POST /auth/login` → a token; `GET /auth/me`, `GET /tenants` (a membership
   list containing that slug) and `GET /permissions/me` answer. Assert: the
   acting-tenant mirror ends holding that condominium's **id**; the first
   tenant-scoped request issued afterwards records that id (the value the
   interceptor sends as `X-Tenant-Id`, result 6 held across the login, not only
   from a signed-in start); the rendered location is `/`.
2. **Non-member.** Same flow, membership list without that slug. Assert the
   panel reading exactly `Você não tem acesso a este condomínio`, that the
   location is still `/c/<slug>`, and that no 404 surface renders.
3. **Unknown slug.** Same flow, branding read 404s and the slug is in no
   membership list. Assert that **after the login continuation settles** the
   rendered HTML is **equal** to case 2's and the recorded request URL list is
   **equal** to case 2's.

### Result 5, stated honestly

A constant-time guarantee is **not achievable and not assertable** here: the
page runs in a browser over a network, and any wall-clock assertion in Vitest
would be flaky and meaningless. The property this task tests instead is
**structural indistinguishability after authentication**: once the login
continuation settles, the unknown-slug and non-member branches execute the same
component code (the resolution is a pure array lookup over `useTenant().tenants`
— no request decides it), have issued the **same set of requests**, and render
the **same HTML**. Case 3 asserts exactly that, as equality, at that point.

This is deliberately narrower than "denies the existence oracle", and the
difference matters. **Before** login the two branches are plainly
distinguishable, by design: a known slug returns 200 and renders the branded
form with the condominium's name and logo
(`BrandedEntryPage.test.tsx:139-155`), an unknown slug 404s and falls back to
the unbranded form (`BrandedEntryPage.test.tsx:184`). That 200/404 branding
read **is** an existence oracle, and it was published knowingly under APRAS-74's
decision D3 — slug existence is public, because that is what a branded login
page is, and the only mitigation bought for it is the per-IP rate limit. What
case 3 buys is that the post-authentication no-access panel introduces **no
second oracle** beyond the one D3 already accepted. On the backend the matching
property is already held in one `if`: an unknown slug and a deactivated
condominium both answer the ordinary 404
(`test_an_unknown_slug_is_404_with_the_ordinary_error_body`,
`test_an_inactive_condominium_is_404_as_well`).

## Expected Results

- [ ] `docs/tasks/APRAS-69-spec.md` quotes all seven of the card's original expected results verbatim and states, per number, what delivered each — naming commit `2c58a76` for result 1, commit `0232c4e` for results 2, 3, 5 and 6 and for the signed-in halves of result 4, and stating that result 7 was discharged by no child and is a delivery gate on APRAS-69 itself. Additionally, the set of files this task changes contains only `AGENTS.md`, files under `docs/`, and files under `frontend/src/**/__tests__/**` — no file under `backend/`, none under `frontend/src/` outside `__tests__`, and none under `backend/alembic/versions/`. Determine that set from this task's own commits: `git log --format='%H %s' | grep -E '^[0-9a-f]{40} [a-z]+\(APRAS-69\):'`, then `git show --stat <commit>` for each (equivalently, diff from the parent of the earliest such commit). Do **not** use `git diff master...HEAD` (empty — this project lands on `master`) and do **not** use `git merge-base HEAD origin/master` (local `master` runs ahead of the remote, so that base is ~19 commits and ~187 files back).
- [ ] A new file `frontend/src/features/user-administration/__tests__/BrandedEntryLogin.integration.test.tsx` exists, mocks only `src/api/client` (nothing under `src/features/**` is mocked), routes `/` to the real `RootRedirect` component imported from `src/App.tsx`, and passes: an anonymous visitor at `/c/<slug>` submits the login form and, once the token, the membership list and `GET /permissions/me` resolve, the module-level acting-tenant mirror that `src/api/client.ts` reads holds that condominium's id, the next request the stubbed client records was issued with that same mirror value (this is the value the real interceptor would send as `X-Tenant-Id`; the mocked client builds no header object, so assert on the recorded mirror value), and the rendered router location is `/`.
- [ ] In the same file, a visitor who authenticates at `/c/<slug>` for a condominium absent from their membership list ends on a panel whose text is exactly `Você não tem acesso a este condomínio`, the router location is still `/c/<slug>`, and no navigation and no 404 page occurs.
- [ ] In the same file, the unknown-slug case and the non-member case are asserted **equal** to each other on both the rendered HTML — compared as the render result's `container.innerHTML`, not `document.body.innerHTML` — and the list of request URLs issued, measured after the login continuation has settled (not before it) — and no timing or wall-clock assertion of any kind is used.
- [ ] `backend/app/schemas/tenant.py`'s `PublicTenantBrandingRead` still declares exactly the four fields `slug`, `name`, `logo_url`, `theme`, and `backend/tests/test_public_branding.py::test_the_body_carries_exactly_four_keys` and `::test_the_thirty_first_request_inside_a_minute_is_429` both pass unchanged.
- [ ] `AGENTS.md` contains a route-map row for `/` describing the anonymous landing page and the authenticated dashboard, a route-map row for `/c/:slug` marked public, and an endpoint row for the `/api/v1/public` prefix pointing at `backend/app/api/v1/endpoints/public_branding.py`; and the paragraph currently at `AGENTS.md:58-64` — which reads that root `/` "renders the general dashboard for **every** authenticated caller" — no longer claims `/` is reachable only by an authenticated caller: `grep -n "every\*\* authenticated caller" AGENTS.md` returns nothing.
- [ ] Backend `pytest` passes with the existing 90% coverage gate and `ruff check` is clean; frontend `tsc -b` passes, `vitest` coverage meets 80/78/76/80, ESLint is clean on the files this task changed, and `pt.json` and `en.json` remain key-identical with no key added or removed by this task.

## Out of Scope

Slug history / redirects for a renamed condominium (explicitly declined on
APRAS-66), any new public field, any second public endpoint, any change to the
branded screen's visual design, and any behaviour change to `/`.
