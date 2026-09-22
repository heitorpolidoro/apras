# APRAS-70 — Add superuser-only condominium creation screen

Part 1 of the APRAS-67 split. Design: `docs/superpowers/specs/2026-09-21-tenant-onboarding-and-branded-entry-design.md`, Deliverable 2.

## Scope

A **frontend-only** screen at `/admin/tenants` that lists every condominium and
creates a new one through the **existing** `POST /api/v1/tenants`, showing the
slug the backend derived (APRAS-66).

**Not in scope, and no line of it is written here:** any backend file, any
schema change, any new endpoint, **no Alembic revision at all** (this task
needs no migration — it touches no column and no table; `0002_tenant_slug`
stays the newest revision as far as this task is concerned, and the
`0003_tenant_brand_color` proposed by APRAS-68 is untouched), any change to
`ROUTE_PERMISSIONS` / `UNGUARDED_ROUTES` / any parity-matrix baseline, the
administrator invitation (APRAS-71 + APRAS-72), deactivating or renaming a
condominium, editing the slug, and per-tenant modules/subscription (which have
their own screens already).

## Decisions

**D1 — the create form asks for the name, and nothing else.** Name is required,
1–120 characters, matching `TenantCreate`. There is **no slug input**:
`TenantCreate` has no `slug` field, so honouring a typed one would require the
backend change this task excludes.

**D2 — no client-side slug preview.** `app/core/slug.py` plus
`TenantService.generated_slug` are the single derivation authority, including
the `-2` collision suffix, and a JS reimplementation would be a second
authority that can silently disagree. The form says in helper text that the
address is derived from the name and may receive a numeric suffix if taken; the
**authoritative** slug is read from the `201` response body (`TenantRead.slug`)
and shown in a success panel with a copy button, and in the list row from then
on.

**D3 — the slug is edited afterwards, not at creation.** The list states, next
to the slug, that changing it is done on the condominium's own profile screen
(`/admin/tenant-profile`, `tenants:profile_update`, APRAS-66) after switching to
that condominium in the tenant switcher. This screen offers no slug edit and no
automatic tenant switch.

**D4 — the list shows name, address (slug), status and creation date, and is
not paginated.** `GET /api/v1/tenants` accepts no `skip`/`limit` and returns
every tenant ordered by name, so a pager would be a fiction over an
already-complete payload. Instead: a client-side text filter matching name or
slug (case-insensitive, accent-insensitive not required) and an
all / active / inactive status filter, plus a result count. If the install ever
outgrows one payload, paginating `GET /tenants` is a backend task of its own.

**D5 — `is_active` is read-only here.** Creation always produces an active
condominium (the body omits `is_active`; the backend defaults it to `true`), the
list renders a status badge from it, and the status filter reads it. **No write
to `is_active`**: deactivation is `PATCH /api/v1/tenants/{id}`, an operator act
with different consequences (the tenant disappears from nobody's data, only from
use) and it belongs to a screen for editing an existing condominium, which this
task does not build.

**D6 — a duplicate name is a 409, shown inline.** `TenantService.create_tenant`
refuses an existing `tenant.name` with `TenantAlreadyExistsError` → **409**. The
form renders a translated message under the name field (not the backend's
English detail string), keeps every typed value, leaves the dialog open and does
**not** invalidate the list. A 422 (empty/too-long name) and any other failure
fall back to `parseApiError` with the page's generic key.

**D7 — where APRAS-72 attaches**, named now so the screen is not redesigned
then: (a) an **Administrator** column in the list table, empty in this task,
which will show the invitation state (pending / accepted / expired); (b) a
per-row **actions** cell, empty in this task, which will carry "Invite
administrator"; (c) the post-create success panel, whose secondary slot is
reserved for "Invite the administrator now". The mock renders all three as
disabled placeholders labelled *APRAS-72*, so the layout already accounts for
them.

**D8 — `routeAccess.test.ts`'s count assertion is restated, not bumped.** The
test `it("NAV_GROUPS covers all 31 NAV_ITEMS …")` hard-codes `31` three times
(`navItemPaths` length, `allGroupPaths` length, `uniqueGroupPaths.size`), so
adding a 32nd nav item fails it. The literal is **not** load-bearing for what
the test is named after: the omission/duplicate invariant is carried by the
final `expect([...allGroupPaths].sort()).toEqual([...navItemPaths].sort())`
together with the two lengths being *equal to each other*; `31` only encodes
"the board has exactly this many screens today", which every new screen must
remember to bump (this is the second hard-coded-count tripwire the project has
hit). The three literals therefore become `NAV_ITEMS.length`, and the
accidental-deletion guard the literal did provide is kept explicitly and
monotonically as `expect(navItemPaths.length).toBeGreaterThanOrEqual(31)` —
which passes at 32 without a bump and still fails if items are removed. The
test title and the stale `// 30 before APRAS-61` comment are updated to name
the invariant rather than a number. `expect(NAV_GROUPS).toHaveLength(7)` stays
as it is: the group set is a design decision, not a running total, and this
task adds no group.

**D9 — the creation date comes from `created_at`, formatted date-only.**
`TenantRead` already returns `created_at` (and `updated_at`) as ISO-8601, but
the frontend `Tenant` interface omits both, so the list column needs the field
added. Only `created_at` is added — `updated_at` is displayed nowhere here.
Rendering is `new Date(tenant.created_at).toLocaleDateString(i18n.language)`:
the date alone, no time component, matching `DueDateBadge.tsx`'s existing
locale-from-i18n convention.

**Vocabulary.** The UI word for a tenant is **"Condomínio"** (pt) /
**"Condominium"** (en). The person APRAS-72 will invite is the condominium's
**administrator in the system** (`is_tenant_admin`); the word *síndico* appears
nowhere in the strings this task adds.

## Approach

### Behavior

- A **superuser** opening `/admin/tenants` sees: a header, the filter row, the
  condominium table, and a "New condominium" button that opens the create form
  (inline panel or modal — the mock shows a modal).
- A **non-superuser** opening the same path sees `RestrictedAccessMessage` **in
  place**, with no redirect, exactly as `/admin/modules` does. The rule is
  `{ superuser: true }` read from the **real** auth user, so a "view-as"
  simulation never opens it. The sidebar entry follows the same rule object.
- Loading, error and empty states: a spinner while the query is pending, an
  error message on failure, and an empty-state row when no condominium matches
  the filters.
- Submitting the form calls `POST /api/v1/tenants` with `{ name }`. On `201`
  the form closes, a success panel shows the created name and its slug, and the
  TanStack key **`["tenants"]`** is invalidated — the same key
  `TenantContext` already uses, so the tenant switcher gains the new
  condominium with no reload.
- The submit button is disabled while the mutation is pending and for an empty
  name.

### Files touched

- `frontend/src/types/auth.ts` — add `slug: string` **and**
  `created_at: string` (ISO-8601, as `TenantRead` serialises it) to the
  `Tenant` interface; both are already on the payload (`slug` since APRAS-66,
  `created_at` since APRAS-41) and both are non-optional because every
  `GET /tenants` and `POST /tenants` body carries them. `updated_at` is not
  added — nothing renders it.
- `frontend/src/features/user-administration/__tests__/TenantSwitcher.test.tsx`
  — the only two existing `Tenant`-annotated fixtures (`TENANT_A`, `TENANT_B`)
  gain `slug` and `created_at` values, which the two now-required fields make
  necessary for `tsc -b`. No assertion in that file changes.
- `frontend/src/api/tenants.ts` — add `createTenant({ name })`, `POST /tenants`
  with no trailing slash, returning `Tenant`.
- `frontend/src/hooks/useTenants.ts` *(new)* — `useTenants()` on `["tenants"]`
  (same key and fetcher as `TenantContext`) and `useCreateTenant()` invalidating
  it.
- `frontend/src/features/user-administration/pages/TenantsAdminPage.tsx`
  *(new)* — the screen: filters, table, create form, success panel, the two
  reserved APRAS-72 slots.
- `frontend/src/features/user-administration/access/routeAccess.ts` — a
  `ROUTE_ACCESS["/admin/tenants"] = { superuser: true }` entry with the
  `/admin/modules` comment convention, `/admin/tenants` added to the
  `administration` `NAV_GROUPS` entry, and a `NAV_ITEMS` entry
  (`labelKey: "nav.tenants"`, `iconName: "Hotel"`).
- `frontend/src/features/user-administration/__tests__/routeAccess.test.ts` —
  per D8: the three `31` literals in the `NAV_GROUPS covers …` test become
  `NAV_ITEMS.length`, one `expect(navItemPaths.length).toBeGreaterThanOrEqual(31)`
  is added as the deletion guard, and the test title plus the stale
  `// 30 before APRAS-61` comment are reworded to name the invariant instead
  of a count. Every other assertion in the file is untouched and keeps passing.
- `frontend/src/features/user-administration/components/Sidebar.tsx` — import
  the chosen lucide icon and add it to `ICON_MAP` (any existing key may be
  reused instead; the map must contain whatever `iconName` names).
- `frontend/src/App.tsx` — the lazy/direct import plus the `/admin/tenants`
  `<Route>` wrapped in `ProtectedRoute requiredAccess={ROUTE_ACCESS["/admin/tenants"]}`,
  copying the `/admin/plans` block.
- `frontend/src/i18n/locales/en.json`, `frontend/src/i18n/locales/pt.json` —
  `nav.tenants` and a `tenantsAdmin.*` block (title, subtitle, columns, filters,
  form labels and helper text, success, `duplicateName`, `validationError`,
  `genericError`, the two APRAS-72 placeholders). Both files get the same key
  set.
- `frontend/src/features/user-administration/__tests__/TenantsAdminPage.test.tsx`
  *(new)* — the tests below.

### Test criteria

`TenantsAdminPage.test.tsx`, with the API module mocked:

1. renders one row per tenant with its name, its slug and its creation date
   (the `created_at` fixture rendered as
   `new Date(created_at).toLocaleDateString(i18n.language)`, date only), and
   the status badge for an inactive one;
2. the text filter narrows by name **and** by slug; the status filter narrows to
   inactive only;
3. submitting the form calls `createTenant` with the typed name and, on
   resolution, shows the slug from the response and invalidates `["tenants"]`;
4. a rejected create with `response.status === 409` renders the translated
   duplicate-name message, leaves the typed name in the field, and does not
   call the list query again;
5. a pending create disables the submit button.

Access, in the existing suites' style (extend them rather than duplicating
`ProtectedRoute` machinery): a superuser renders the page at `/admin/tenants`
and a non-superuser renders `RestrictedAccessMessage` in place.
`routeAccess.test.ts` already asserts every `NAV_ITEMS` entry's rule **is** its
`ROUTE_ACCESS` entry; that assertion must keep passing with no edit. Its
`NAV_GROUPS covers …` test is the one exception and is edited exactly as D8
describes — it must pass with 32 nav items *without* any `32` appearing in the
file.

Gates: `tsc -b` clean; Vitest thresholds **80 lines / 78 functions / 76 branches
/ 80 statements**; ESLint diff-scoped against the baseline of **375 errors +
2 warnings across 64 files** — the new files add none.

## Expected Results

- [ ] `ROUTE_ACCESS["/admin/tenants"]` is exactly `{ superuser: true }`, `/admin/tenants` is listed in the `administration` `NAV_GROUPS` entry and has a `NAV_ITEMS` entry whose `iconName` exists in `Sidebar.tsx`'s `ICON_MAP`.
- [ ] `routeAccess.test.ts` passes with the 32 nav items, and its `NAV_GROUPS covers …` test expresses the count as `NAV_ITEMS.length`: `grep -n "32" frontend/src/features/user-administration/__tests__/routeAccess.test.ts` returns nothing, and the only remaining numeric literals in that test are `toHaveLength(7)` for `NAV_GROUPS` and one `toBeGreaterThanOrEqual(31)` deletion guard. No other assertion in the file is edited.
- [ ] A superuser at `/admin/tenants` renders the condominium table; a non-superuser renders `RestrictedAccessMessage` in place at the same path with no navigation (asserted by test).
- [ ] The table renders one row per tenant from `GET /api/v1/tenants` showing name, slug, an active/inactive badge and the creation date; the `Tenant` interface in `frontend/src/types/auth.ts` carries `slug: string` and `created_at: string` (ISO-8601) and the date cell renders `new Date(created_at).toLocaleDateString(i18n.language)` — the date only, with no time component; an inactive tenant's badge differs (asserted by test).
- [ ] The text filter matches on name and on slug, and the status filter restricts to active or inactive (asserted by test).
- [ ] Submitting the create form calls `POST /api/v1/tenants` with `{ name }` only; on success the slug from the response body is displayed and the `["tenants"]` query key is invalidated (asserted by test).
- [ ] A 409 from the create call renders a translated duplicate-name message inline, preserves the typed name and leaves the dialog open (asserted by test).
- [ ] `git diff --name-only` for the task contains **no** path under `backend/` and **no** file under `backend/alembic/versions/`.
- [ ] Every user-visible string on the screen comes from `en.json` and `pt.json`, both carrying the identical new key set, and none of them contains "síndico"/"sindico".
- [ ] `docs/tasks/APRAS-70-mock.html` exists and opens standalone.
- [ ] `npx tsc -b` reports no error; `npm run test -- --coverage` meets 80 lines / 78 functions / 76 branches / 80 statements; ESLint reports no finding beyond the 375 errors + 2 warnings baseline.

## Out of Scope

The administrator invitation and its acceptance page (APRAS-71, APRAS-72);
editing a condominium's name, slug or `is_active` from this screen; pagination
of `GET /tenants`; automatic switching of the acting tenant after creation;
branding/theme fields (APRAS-68); anything under `backend/`.
