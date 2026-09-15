# APRAS-57 — Remove `landing_path` from the role model

## Scope

Delete the role landing preference from the product, end to end: the column's
Python model field, its write/read schemas and allowlist, its exposure on
`GET /api/v1/permissions/me`, the frontend consumption chain
(`RootRedirect`, `ProtectedRoute`'s `landingRedirect` bounce, `ROUTE_ACCESS`'s
`landingRedirect` flag, the TS types, the fixtures), the i18n strings, and the
tests that exist only to pin that behaviour. The role editor stops sending the
field in its `PATCH`.

After this task, `/` renders `GeneralDashboardPage` for **every** authenticated
caller and no route ever bounces a caller to a role-configured landing.

**Not in scope:**

* **No Alembic migration.** The `role.landing_path` column stays in the
  database and is dropped by APRAS-58's consolidated migration. The field
  simply disappears from the model; the leftover nullable column is inert
  (nothing selects or writes it, and no test compares `role` against
  `SQLModel.metadata` — `test_0036_matches_the_model_metadata` covers only the
  `infraction%` tables).
* **`backend/alembic/versions/0033_drop_user_role_and_menus.py` is not
  edited** — frozen history — and neither are the three assertions in
  `backend/tests/test_migrations_postgres.py` that describe 0033's own additive
  step (`test_0033_drops_the_columns_the_index_and_the_type`,
  `test_0033_sets_the_two_landing_paths`, `_assert_pre_0033_schema_is_back`).
  They remain true until APRAS-58 drops the column, and updating them is
  APRAS-58's job.
* The role-name changes currently uncommitted in the working tree (APRAS-58)
  are not part of this task. Where this spec touches the same file
  (`RoleDetailPage.tsx` / `RoleDetailPage.test.tsx`), the requirement is only
  the **end state**: no `landing_path` anywhere in it.
* Historical documents under `docs/` (specs, `suggestions-log.md`) keep their
  references.

## Approach

### Behavior

1. `Role` no longer has a `landing_path` attribute; `RoleCreate`, `RoleUpdate`
   and `RoleRead` no longer declare the field and the `LANDING_PATHS`
   allowlist and its validator are gone. `create_role` stops passing it and
   `update_role` loses the `model_fields_set` branch that wrote it — the only
   reason that branch existed disappears with the field.
2. A `PATCH /api/v1/roles/{id}` body that still carries `landing_path` is
   accepted (Pydantic's default `extra="ignore"`; this project sets no
   `extra="forbid"` on these schemas) and persists nothing; the response body
   does not contain the key.
3. `GET /api/v1/permissions/me` answers exactly
   `{tenant_id, permissions, disabled_modules}`. `landing_path_for()` and the
   `MyPermissionsRead.landing_path` field are deleted.
4. `RootRedirect` renders `GeneralDashboardPage` for every authenticated
   caller (the loading spinner window is unchanged); it issues no `Navigate`.
   `useCanOpenPath` survives — `GeneralDashboardPage` still uses it — but
   `App.tsx` and `ProtectedRoute.tsx` stop calling it.
5. `ProtectedRoute` loses the landing-redirect block entirely; its remaining
   behaviour (permission gate, module-off variant, in-place
   `RestrictedAccessMessage`) is unchanged, and it no longer reads
   `useMyPermissions` for landing purposes.
6. `AccessRule` loses the `landingRedirect` member, and `/tasks`,
   `/dashboard`, `/categories` lose the flag in `ROUTE_ACCESS`.
7. The role editor's save sends a body of exactly `{name, permissions}`.

### Files touched

Backend:

* `backend/app/models/role.py` — drop the `landing_path` field and its comment.
* `backend/app/schemas/role.py` — drop `LANDING_PATHS`,
  `_validate_landing_path`, and the field on the three schemas.
* `backend/app/schemas/permission.py` — drop `MyPermissionsRead.landing_path`
  and its docstring paragraph.
* `backend/app/api/v1/endpoints/permissions.py` — delete `landing_path_for`
  and its use in `read_my_permissions`.
* `backend/app/api/v1/endpoints/roles.py` — drop the create argument and the
  `model_fields_set` update branch.
* `backend/tests/conftest.py` — drop `landing_path=` from the profile-role
  fixture.
* `backend/tests/test_conftest_profiles.py` — drop the three landing
  assertions.
* `backend/tests/test_permission_registry.py` — `test_role_schemas_expose_permissions`
  now asserts the three exact field sets without `landing_path`.
* `backend/tests/test_role_permissions.py` — the `RoleRead` shape assertion
  becomes `{id, name, permissions}`.
* `backend/tests/test_landing_path.py` — **deleted**.

Frontend:

* `frontend/src/App.tsx` — `RootRedirect` reduced to spinner + dashboard;
  `useMyPermissions`/`useCanOpenPath` imports dropped if unused.
* `frontend/src/features/user-administration/components/ProtectedRoute.tsx` —
  landing-redirect block and now-unused hooks removed.
* `frontend/src/features/user-administration/access/routeAccess.ts` — flag and
  its comment removed from the three entries.
* `frontend/src/features/user-administration/access/useCanAccess.ts` — the
  landing paragraphs in `useCanOpenPath`'s docstring reworded (the hook stays).
* `frontend/src/features/user-administration/context/useEffectiveIdentity.ts` —
  docstring mention removed.
* `frontend/src/types/permissions.ts` — `landing_path` off `MyPermissions`,
  `landingRedirect` off `AccessRule`'s three arms.
* `frontend/src/types/auth.ts` — `landing_path` off `Role`.
* `frontend/src/features/user-administration/hooks/useRoleMutations.ts` —
  `landing_path` off the update body type.
* `frontend/src/features/user-administration/pages/RoleDetailPage.tsx` — the
  save payload is `{name, permissions}`.
* `frontend/src/test/permissionFixtures.ts` — fixture field and builder
  parameter removed (call sites in `Sidebar.test.tsx`,
  `Navbar.modules.test.tsx`, `PurchasesRouteGating.test.tsx`,
  `useCanAccess.superuser.test.tsx`, `ProtectedRoute.*.test.tsx` updated).
* `frontend/src/i18n/locales/en.json`, `pt.json` — remove
  `roles.landingPath`, `roles.landingPathNone`, `roles.landingPathHint` from
  both, keeping the two files key-identical.
* Tests deleted: `frontend/src/__tests__/RootRedirect.landing.test.tsx`,
  `frontend/src/features/user-administration/__tests__/ProtectedRoute.porteiroGate.test.tsx`,
  `frontend/src/features/user-administration/__tests__/ProtectedRoute.guestWelcome.test.tsx`
  (its one non-landing case — "a GUEST without `tasks:*` sees the restricted
  message" — is kept by moving it into `ProtectedRoute.permissions.test.tsx`
  if it is not already covered there).
* Tests edited: `frontend/src/__tests__/RootRedirect.test.tsx` (the landing
  cases become one case asserting the dashboard renders for a caller that
  previously carried `/gate`), `routeAccess.test.ts` (the `landingRedirect`
  case becomes an assertion that no rule carries the key),
  `frontend/src/types/__tests__/auth.test.ts`,
  `frontend/src/features/user-administration/__tests__/RoleDetailPage.test.tsx`.

Docs:

* `AGENTS.md` — the `landing_path` paragraphs under *Frontend (React SPA)*,
  the `landingRedirect` paragraph after the route map, *Roles are data*
  ("an optional `landing_path`") and the `/permissions/me` body in *The two
  permission reads* are rewritten to describe the post-removal behaviour.
* `docs/tasks/APRAS-57-mock.html` — the role editor and `/` after the removal.

### Test criteria

* `backend/tests/test_permission_registry.py::test_role_schemas_expose_permissions`
  and the `RoleRead` shape case in `test_role_permissions.py` pin the exact
  field sets, so a re-added field fails CI.
* A backend case (in `test_roles.py`) asserts that a `PATCH /api/v1/roles/{id}`
  whose body carries `landing_path` answers **200** and that the response has
  no such key.
* A backend case (in `test_effective_permissions.py` or
  `test_permissions_me.py`, wherever `/permissions/me` is already exercised)
  asserts the response keys are exactly
  `{tenant_id, permissions, disabled_modules}`.
* A vitest case asserts `RootRedirect` renders the general dashboard and issues
  no navigation for a caller whose role formerly carried `/gate`.
* A vitest case asserts the role editor's `PATCH` body is exactly
  `{name, permissions}`.
* `routeAccess.test.ts` asserts no `ROUTE_ACCESS` entry carries
  `landingRedirect`.
* The two new/kept tests that must still name the literal key —
  `test_roles.py`'s ignored-extra-key case and `routeAccess.test.ts`'s negative
  assertion — together with `test_migrations_postgres.py` form the complete
  allowlist for the repo-wide grep; every other occurrence is removed.
* The full gates: backend `pytest` (≥90% coverage), `ruff check .`,
  `ruff format --check .`; frontend `tsc -b`, `vitest run` (≥75% coverage),
  `eslint`.

## Expected Results

- [ ] Production sources are clean: `grep -rn 'landing_path\|landingPath\|LANDING_PATHS\|landingRedirect' backend/app frontend/src --exclude-dir=__tests__ --exclude-dir=test` returns **zero** matches.
- [ ] In the test trees, `grep -rln 'landing_path\|landingPath\|LANDING_PATHS\|landingRedirect' backend/tests frontend/src/test frontend/src/**/__tests__` matches **only** the three allowlisted files, each for a stated reason: `backend/tests/test_migrations_postgres.py` (0033's frozen-history assertions), `backend/tests/test_roles.py` (the case proving an extra `landing_path` key in a `PATCH` body is ignored), `frontend/src/features/user-administration/__tests__/routeAccess.test.ts` (the negative assertion that no rule carries `landingRedirect`). The literal key appears verbatim in those tests — obfuscating it by string concatenation is not acceptable.
- [ ] `GET /api/v1/permissions/me` returns a JSON object whose keys are exactly `tenant_id`, `permissions`, `disabled_modules`.
- [ ] `GET /api/v1/roles/` and `PATCH /api/v1/roles/{id}` return role objects whose keys are exactly `id`, `name`, `permissions`; a `PATCH` body containing `landing_path` answers **200**, stores nothing and echoes no such key.
- [ ] `test_role_schemas_expose_permissions` asserts `RoleCreate`/`RoleUpdate` fields `= {name, permissions}` and `RoleRead` fields `= {id, name, permissions}`.
- [ ] `backend/tests/test_landing_path.py`, `frontend/src/__tests__/RootRedirect.landing.test.tsx` and `frontend/src/features/user-administration/__tests__/ProtectedRoute.porteiroGate.test.tsx` no longer exist.
- [ ] A vitest case shows `RootRedirect` renders `GeneralDashboardPage` — no `Navigate` — for a caller whose role formerly carried `/gate`.
- [ ] A vitest case shows the role editor's save issues a `PATCH` whose body is exactly `{name, permissions}`.
- [ ] `routeAccess.test.ts` asserts no entry of `ROUTE_ACCESS` carries `landingRedirect`, and `AccessRule` no longer declares it.
- [ ] `roles.landingPath`, `roles.landingPathNone` and `roles.landingPathHint` are absent from both `en.json` and `pt.json`, which stay key-identical.
- [ ] No file is added under `backend/alembic/versions/`; the Alembic head is unchanged and `backend/alembic/versions/0033_drop_user_role_and_menus.py` is byte-identical.
- [ ] Backend `uv run pytest` passes with the 90% coverage gate; `uv run ruff check .` and `uv run ruff format --check .` report zero findings.
- [ ] Frontend `npx tsc -b`, `npm run test` (75% coverage gate) and `npm run lint` all pass.
- [ ] `AGENTS.md` contains no occurrence of `landing_path` or `landingRedirect`.

## Out of Scope

- Dropping the `role.landing_path` database column (APRAS-58).
- Any change to permission resolution, module gating, or the role-name work in
  the uncommitted working tree.
