# APRAS-61 — Condominium profile with logo upload

## Scope

A tenant-side **"Perfil do condomínio"** screen and the API behind it, so the
condominium's system administrator (`is_tenant_admin`, or any role granted the
new permission) can read the condominium's basic data and **upload its logo**
instead of an operator running SQL against `tenant.logo_url`.

**In scope**

- One new **tenant-scoped** router, `/api/v1/tenant-profile`, with four routes
  (read, rename, upload logo, remove logo).
- One new catalogue permission, `tenants:profile_update`.
- Logo bytes stored through the existing `LocalStorageProvider.save_file`;
  the public URL written to the existing `tenant.logo_url` column.
- The frontend page, its route/menu entry, i18n `pt`/`en`, and the API module.
- Registry, alignment, parity-baseline and `AGENTS.md` bookkeeping the new
  routes and the new permission force.

**Not in scope**

- **No migration.** `tenant.logo_url` already exists (`0037`); no column, no
  table, no backfill, and `backend/tests/test_migrations_postgres.py` is
  untouched.
- **No change to `app/services/project_report_service.py`.** It already reads
  `tenant.logo_url`; the report picking up the uploaded logo is a consequence,
  not an edit.
- **No `MediaAsset` row, no thumbnail, no photo-moderation flow.** A logo is a
  property of the tenant, not a moderated user upload.
- **No change to `PATCH /api/v1/tenants/{tenant_id}`, to
  `SUPERUSER_ONLY_PERMISSIONS`, or to the meaning of `tenants:update`.**
- **No slug**: `Tenant` has no `slug` column (`app/models/tenant.py`), so the
  screen shows name + tenant id.
- **No logo in the Sidebar/Navbar** (see D4), and no non-local storage
  provider (`VercelBlob`/`S3`/`Cloudinary` stay `NotImplementedError` stubs).

## Decisions

**D1 — Option (a), with one correction to the path shape.** The routes are a
new router mounted `TENANT_SCOPED` with **no `{tenant_id}` in the path**, not
`PUT /api/v1/tenants/{id}/logo`. The `tenants` router is mounted
`GLOBAL_SCOPED` (`app/api/v1/api.py`), so it resolves no acting tenant; with no
acting tenant `get_effective_role_ids` is empty and the `is_tenant_admin`
short-circuit is structurally absent, so a `require_permission` guard there
would answer 403 to every tenant role **and** to every tenant admin. This is
exactly why `app/api/v1/endpoints/subscription.py` exists as a tenant-side
router beside the superuser `/tenants/{id}/…` block, and this task copies that
precedent verbatim. It also gives ER-4 for free: the subject is always the
acting tenant, so there is no id in the body or path to forge.

**D2 — Accepted types: `image/png`, `image/jpeg`, `image/webp`. SVG is OUT.**
An SVG is active content (script, `foreignObject`, external references) that
would be served same-origin from `/static/uploads/` and embedded in the
printable works report, which a browser renders; accepting it without a
sanitiser is a stored-XSS surface, and a sanitiser is a task of its own. The
accepted set is deliberately the same three strings as
`media_service.ALLOWED_MIME_TYPES`, which the works report already renders.

**D3 — Maximum size: 2 MiB** (`2 * 1024 * 1024`), deliberately below the
5 MiB photo cap: the logo is embedded in every printed document. The bytes are
additionally opened with Pillow, and a file that does not decode is refused
even when its declared MIME type is accepted.

**D4 — The Sidebar/Navbar do NOT display the logo in this task.** Every
sidebar render would need either a new per-page fetch or `logo_url` added to
`GET /api/v1/auth/me`, which is a **global** route and deliberately answers
nothing tenant-relative beyond the membership summary. It is one deliverable
of its own, and this task ships the write path plus the surface that already
consumes it. Follow-up task suggestion: "show the tenant logo in the sidebar
header".

**D5 — A refused file is 422**, through two new `DomainError` subclasses
registered in the 422 branch of `app/core/exception_handlers.py`. The existing
`PhotoFileTooLargeError` / `InvalidPhotoFormatError` are mapped to **400** and
are the media pipeline's published contract; reusing them would contradict the
task's stated result.

**D6 — The read route is unguarded, the three writes carry the permission.**
`GET /api/v1/tenant-profile` is authenticated and self-scoped to the acting
tenant and returns data the caller already sees (`/auth/me` carries the tenant
name; the logo URL is a public static asset), so it joins `UNGUARDED_ROUTES`
under the `/permissions/me` precedent. The page's own gate is the permission,
so a caller without it never loads the screen.

**D7 — `tenants:profile_update` is an ordinary, grantable permission.** It is
**not** added to `SUPERUSER_ONLY_PERMISSIONS`, so a tenant admin can tick it
for a role in the role editor; `is_tenant_admin` and `is_superuser` hold it
through the existing whole-catalogue short-circuits, **with no special case in
any handler**. Its module is `tenants`, which is core, so APRAS-39's strip can
never remove it.

## Approach

### Behavior — backend

`app/api/v1/endpoints/tenant_profile.py`, a new router mounted in
`app/api/v1/api.py` at prefix `/tenant-profile` with `TENANT_SCOPED`, four
routes, all acting on the `Tenant` returned by `deps.get_current_tenant`:

| Route | Guard | Answers |
|---|---|---|
| `GET /api/v1/tenant-profile` | authenticated (`UNGUARDED_ROUTES`) | 200 `TenantProfileRead` |
| `PATCH /api/v1/tenant-profile` | `require_permission("tenants:profile_update")` | 200; 409 on a name already taken; 422 on an empty/over-long name |
| `PUT /api/v1/tenant-profile/logo` (multipart `file`) | same | 200 with the new `logo_url`; 422 on type/size/undecodable |
| `DELETE /api/v1/tenant-profile/logo` | same | 200 with `logo_url: null`, idempotent when already null |

- `TenantProfileRead` = `{id, name, is_active, logo_url}`;
  `TenantProfileUpdate` = `{name: str | None}` (1–120 chars), reusing
  `TenantUpdate`'s bounds. `is_active` is **not** writable here — deactivating
  a condominium stays a superuser act.
- The rename reuses `TenantService.update_tenant`'s uniqueness check and its
  existing `TenantAlreadyExistsError` (409). `tenant.updated_at` is refreshed
  on every write, through `app.core.clock.db_now`.
- Business logic goes on `TenantService` as classmethods taking the already
  resolved `Tenant` (`update_profile`, `set_logo`, `clear_logo`) — no new
  service module, no second definition of the uniqueness rule.
- `set_logo` validates size, then MIME, then Pillow-decodability; only then
  calls `LocalStorageProvider.save_file`, assigns the returned public URL to
  `tenant.logo_url` and commits. A refused upload writes **no** file and
  **no** column.
- **Replacement deletes the previous file, best-effort.** The old value is
  mapped back to a path only when it starts with `/static/uploads/` (strip the
  leading `/`); any other value — an externally hosted or hand-written URL — is
  left alone. A failed delete never fails the request (`delete_file` already
  swallows).
- A caller acting in another tenant, or sending `X-Tenant-Id` of a tenant they
  do not belong to, is refused by `deps._resolve_from_header` with the existing
  403 `"Not a member of the requested tenant"` before any handler runs.

### Registry bookkeeping (the part a reviewer must check line by line)

- `app/core/permissions.py`: `PERMISSIONS` **174 → 175** (adds
  `tenants:profile_update`); `MODULES` stays **28**; `ROUTE_PERMISSIONS`
  **203 → 206**; `UNGUARDED_ROUTES` **23 → 24**; total **226 → 230**.
- `tests/test_permission_registry.py`: the `203`/`23`/`226` literals move.
- `tests/test_permission_alignment.py`: `EXPECTED_DEPENDENCY_FORM`
  **53 → 56** (the three new guarded routes are route-level `Depends`), the
  other four form counts unchanged.
- `tests/test_module_vocabulary.py`, `tests/test_role_rename.py`,
  `tests/test_superuser_grant.py`: the `174` literals move to `175`.
- `tests/test_permission_parity_matrix.py`: new `APRAS_61_ROUTES` (the three
  guarded routes), folded into `ADDITIVE_ROUTES`, `APRAS_61_CELL_COUNT = 18`
  added to `EXPECTED_CELL_COUNT`, recorded into the **new additive**
  `tests/data/parity_matrix_baseline_61.json` with
  `uv run python -m tests.tools.record_parity_baseline`. All six files already
  in `backend/tests/data/` stay **byte-identical**, by name:
  `parity_matrix_baseline.json`, `parity_matrix_baseline_40.json`,
  `parity_matrix_baseline_44.json`, `parity_matrix_baseline_51.json`,
  `parity_matrix_baseline_60.json` and `legacy_role_bundles.json`. Only two of
  them carry a pinned digest in the suite (`F2_BASELINE_SHA256`,
  `LEGACY_BUNDLES_SHA256`), so the other four must be confirmed unchanged with
  `git status --porcelain backend/tests/data/`, which must list
  `parity_matrix_baseline_61.json` as the single (untracked) entry.
- `AGENTS.md`: the machine-checked prose (`tests/test_docs_agents_md.py`) —
  `174` → `175`, the route counts, `places all 206 in exactly one`,
  `sweeps the other 198`, `56 route-level` — plus a short paragraph under
  *Tenant* describing the profile surface and D1/D2/D3/D4/D7.

### Behavior — frontend

- Route `/admin/tenant-profile`, rule `{ anyOf: ["tenants:profile_update"] }`
  in `ROUTE_ACCESS`, with the matching `NAV_ITEMS` entry (`labelKey:
  "nav.tenantProfile"`, `iconName: "Landmark"`) added to the
  `administration` group — the group whose pt title is already "Sistema".
- The page shows the current logo (or a placeholder block), the condominium
  name in an editable field, the tenant id read-only, a file picker, a
  "Salvar"/"Enviar logo" action and a "Remover logo" action. It refuses a file
  client-side, before any request, when the type is outside the accepted set
  or the size exceeds the cap, showing a translated message; a backend refusal
  shows a translated fallback message keyed on the status.
- Constants and the permission string live in `src/api/tenantProfile.ts` and
  are exported (`TENANT_LOGO_MAX_FILE_SIZE_BYTES`,
  `TENANT_LOGO_ALLOWED_MIME_TYPES`, `TENANT_LOGO_ACCEPT`,
  `TENANT_PROFILE_PERMISSION`) — the two-sided-pin shape `src/api/uploads.ts`
  established, with a backend case asserting the same four facts and naming
  this file.
- TanStack key `["tenantProfile"]`, invalidated by all three mutations; the key
  does not start with `"tenants"`, matching the tenant-switch eviction rules
  already documented for `["me","permissions"]`.

### Files touched

**Backend**
- `app/core/permissions.py` — one catalogue string, three `ROUTE_PERMISSIONS`
  entries, one `UNGUARDED_ROUTES` entry.
- `app/core/exceptions.py` — `TenantLogoInvalidFormatError`,
  `TenantLogoTooLargeError`.
- `app/core/exception_handlers.py` — both in the 422 branch.
- `app/schemas/tenant.py` — `TenantProfileRead`, `TenantProfileUpdate`.
- `app/services/tenant_service.py` — `update_profile`, `set_logo`,
  `clear_logo`, the accepted-MIME/size constants.
- `app/api/v1/endpoints/tenant_profile.py` — new, four routes.
- `app/api/v1/api.py` — one `include_router(..., TENANT_SCOPED)`.
- `tests/test_tenant_profile.py` — new.
- `tests/test_permission_registry.py`, `tests/test_permission_alignment.py`,
  `tests/test_permission_parity_matrix.py`, `tests/test_module_vocabulary.py`,
  `tests/test_role_rename.py`, `tests/test_superuser_grant.py` — counts.
- `tests/data/parity_matrix_baseline_61.json` — new, recorded.
- `AGENTS.md` — the counts and one paragraph.

**Frontend**
- `src/api/tenantProfile.ts` — new.
- `src/features/user-administration/pages/TenantProfilePage.tsx` — new.
- `src/features/user-administration/access/routeAccess.ts` — rule, nav item,
  group membership.
- `src/features/user-administration/components/Sidebar.tsx` — one icon import
  and `ICON_MAP` entry.
- `src/App.tsx` — one protected route.
- `src/i18n/locales/pt.json`, `en.json` — `nav.tenantProfile`, the
  `tenantProfile.*` block, `permissions.actions.profile_update`.
- `src/i18n/__tests__/parity.test.ts` — action count 94 → 95.
- `src/features/user-administration/__tests__/TenantProfilePage.test.tsx` —
  new.

### Test criteria

`backend/tests/test_tenant_profile.py` proves, with a real request each:

1. `GET` answers 200 with the acting tenant's `name` and `logo_url`.
2. A holder of `tenants:profile_update` renames the tenant (200) and a caller
   without it gets **403** on all three writes; a name already used by another
   tenant is **409**.
3. `PUT /logo` with a valid PNG answers 200, `tenant.logo_url` is non-null and
   starts with `/static/uploads/`, and the file exists on disk.
4. A second upload replaces it: the column holds a different URL and the
   previous file no longer exists on disk.
5. `image/svg+xml`, `text/plain`, a 3 MiB payload and a valid-MIME but
   undecodable body each answer **422**, and leave `logo_url` unchanged.
6. `DELETE /logo` answers 200 with `logo_url: null`, removes the file, and a
   second `DELETE` is still 200.
7. A user who is a member of tenant B, sending `X-Tenant-Id` of tenant A, gets
   **403** on `PUT /logo`, and A's `logo_url` is unchanged.
8. An `is_tenant_admin` member holding **no role permissions** reaches all
   three writes.
9. `GET /api/v1/projects/report` for a tenant whose logo was uploaded through
   this route contains that exact URL inside the masthead `<img src=…>`.
10. The four-fact contract case naming `frontend/src/api/tenantProfile.ts`
    (accepted MIME set, max size, permission string, route path).

`frontend/.../TenantProfilePage.test.tsx` proves: the logo renders when
`logo_url` is set and a placeholder when it is null; selecting an
`image/svg+xml` or a 3 MiB file shows the translated error and issues **no**
request; a successful upload calls `PUT /tenant-profile/logo` with
`multipart/form-data` and re-renders the returned URL; the page renders
`RestrictedAccessMessage` for a caller without `tenants:profile_update`.

## Expected Results

- [ ] `/admin/tenant-profile` renders "Perfil do condomínio" for a holder of
      `tenants:profile_update` (and for every `is_tenant_admin`), showing the
      condominium name and either the current logo or a placeholder; a caller
      without the permission sees `RestrictedAccessMessage` and no upload
      control, and the nav entry is hidden.
- [ ] `PUT /api/v1/tenant-profile/logo` with a `image/png`, `image/jpeg` or
      `image/webp` file up to 2 MiB answers 200, stores the bytes through
      `LocalStorageProvider`, sets `tenant.logo_url` to the returned
      `/static/uploads/...` URL and returns it.
- [ ] A second upload replaces the logo: the column holds the new URL and the
      previously stored local file no longer exists on disk.
- [ ] `DELETE /api/v1/tenant-profile/logo` answers 200 with `logo_url: null`
      and is idempotent.
- [ ] `PATCH /api/v1/tenant-profile` renames the acting tenant (200) and
      answers 409 for a name another tenant already holds.
- [ ] An unsupported type (`image/svg+xml` included), a file over 2 MiB, and a
      body Pillow cannot decode each answer **422** and leave `logo_url`
      unchanged; the frontend refuses the same files before sending and shows a
      pt/en translated message.
- [ ] Every write answers **403** for a caller without
      `tenants:profile_update`, and **403** for a user acting with
      `X-Tenant-Id` of a tenant they do not belong to, with that tenant's
      `logo_url` unchanged.
- [ ] `GET /api/v1/projects/report` renders the uploaded logo in the masthead
      with **no diff** in `backend/app/services/project_report_service.py`.
- [ ] The three guarded routes are in `ROUTE_PERMISSIONS` (203 → 206) and the
      read in `UNGUARDED_ROUTES` (23 → 24); `PERMISSIONS` is 175;
      `test_permission_registry.py`, `test_permission_alignment.py`
      (`EXPECTED_DEPENDENCY_FORM` 56) and `test_docs_agents_md.py` pass, and
      the 18 new parity cells live in the new additive
      `backend/tests/data/parity_matrix_baseline_61.json`, while
      `parity_matrix_baseline.json`, `parity_matrix_baseline_40.json`,
      `parity_matrix_baseline_44.json`, `parity_matrix_baseline_51.json`,
      `parity_matrix_baseline_60.json` and `legacy_role_bundles.json` all stay
      byte-identical (`git status --porcelain backend/tests/data/` lists only
      the new `parity_matrix_baseline_61.json`).
- [ ] `backend`: `uv run pytest` green with the 90% gate, `uv run ruff check .`
      and `ruff format --check .` report zero findings, and `NOQA_CAP` is not
      raised. `frontend`: `tsc -b`, `vitest` (75% gate) and `eslint` green,
      with `permissions.actions.profile_update` and the `tenantProfile.*` block
      present and equal-keyed in `pt.json` and `en.json`.

## Out of Scope

Any database migration; SVG support and an SVG sanitiser; a logo in the
Sidebar/Navbar (D4); cropping, resizing or thumbnailing; a `MediaAsset` record
or photo moderation; `slug`, `is_active` or any other tenant field beyond
`name` and `logo_url`; changing `tenants:update` or
`SUPERUSER_ONLY_PERMISSIONS`; non-local storage providers.

![Mockup](APRAS-61-mock.html)
