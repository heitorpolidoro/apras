# APRAS-128 — Group coupled modules so they are switched on and off together

## Scope
Reverts APRAS-39's "the 28 modules toggle independently" decision for the pairs that are genuinely coupled. A **module bundle** is a set of modules that is always entirely on or entirely off for a tenant, a plan and a courtesy grant. Module names and permission strings are untouched; `deps.get_effective_permissions`, `deps.disabled_modules` and `permissions.filter_by_modules` do not change (`tenant.disabled_modules` stays the only input).

Not covered: one-way dependencies (`lots` -> residents/packages/infractions/reservations/visitors, `occurrences` -> `infractions`, `projects` -> `documents`) and the independent modules. They stay ordinary modules. No UI warning is added for them (see Decisions). Per-module plan prices are unchanged (a bundle's price is the sum of its members).

## Decisions
1. **Bundles** (declared once, `MODULE_BUNDLES` in `backend/app/core/permissions.py`): `tasks`+`categories`; `reservations`+`spaces`; `assets`+`inventory`; `visitors`+`authorizations`+`gate`. `access_control` is NOT in the visitors bundle (no shared FK; independent per the task review).
2. **`assemblies`+`votes`: not a bundle.** `vote.assembly_id` is nullable, so standalone voting is a supported use, and an assembly without voting is a legitimate minutes-only use. Both directions are usable alone, so a bundle would remove a real configuration. AGENTS.md lists them as independent.
3. **`uploads`: stays a normal toggleable module, no bundle, not CORE.** Making it CORE would change `CORE_MODULES` semantics (never billable), its plan price and existing tenants' billing for a cross-cutting concern; a bundle would tie it to four unrelated features. It leaves the "access" presentation group for an "infrastructure" group and is documented as a one-way dependency of occurrences, announcements, infractions and access_control.
4. **Enforcement: 400, not expansion.** A request whose resulting module set splits a bundle is refused with a 400 domain error (`ModuleBundleSplitError`, naming the bundle and the missing members), keeping every PUT declarative. Applies to: `PUT /tenants/{id}/modules` (validated on the requested enabled set = `MODULES - disabled`), `PUT /subscription/modules` (validated on the resulting active set, `requested | preserved`), `PUT /tenants/{id}/subscription/courtesy` (two checks, see below), and plan create/update `included_modules` (the submitted list). For courtesy the request is refused when EITHER set splits a bundle: (a) the entitled set `included | requested courtesy` (the plan's modules plus the submitted list), and (b) the resulting active set, computed exactly as `set_courtesy` does today (`(active_before | granted) - (revoked - included)`, i.e. what `tenant.disabled_modules` will become). The courtesy list alone is never the test: `courtesy=[tasks]` while the plan includes `categories` passes (a) but answers 400 under (b) when `categories` is off in `active_before`, and passes both (200) when `categories` is already on. A whole-bundle courtesy list answers 200 only if (b) is whole too; after the migration `active_before` never splits a bundle, so a whole-bundle grant or revoke always passes. Nothing is written when either check fails. Core modules are never in a bundle; the declaration is validated against `MODULES` and `CORE_MODULES` at import and by a test.
5. **Existing split state: backfill upward (ON) by default** by a new Alembic migration (next free number): for every tenant, plan and courtesy list holding part of a bundle, the missing members are switched ON (`disabled_modules` loses them; `included_modules` and `courtesy_modules` gain them). Rationale: a tenant using `tasks` today is better off gaining `categories` than losing `tasks`; only one real tenant exists. No `role.permissions` row is touched. Downgrade is a no-op (data is not re-split). This is operator question 1 (ON vs OFF for existing split tenants; option A, ON, recommended); the spec is implemented as A unless the operator answers B.

   **If the operator answers B (OFF, downward):** only the migration and its test change. The migration instead switches the PRESENT members OFF: for a tenant with a partial bundle, every member is added to `disabled_modules`; for a plan or courtesy list with a partial bundle, the present members are removed from `included_modules` / `courtesy_modules`. Everything else (decisions 1-4, 6, 7, the writers, the UI) is identical. Expected result 6 then reads: the migration turns a pre-existing split into a fully OFF (tenant) / fully absent (plan, courtesy) bundle, and the test asserts a tenant with `tasks` on / `categories` off ends with both in `disabled_modules` (not both on). Whole bundles stay untouched and the migration is idempotent in both directions.
6. **API exposure:** `GET /tenants/{id}/modules` and `GET /subscription` each module row gains `bundle: str | null` (the bundle key, from the backend definition). No new endpoint.
7. **UI:** `/admin/modules` and `/subscription` render one checkbox per bundle (label lists members), toggling all members through the existing PUT bodies. Modules with `bundle: null` render as today, including a module added later and named in no presentation group (`groupsCovering` "other" behaviour stays). `MODULE_GROUPS` stays as presentation headings only and its comment is rewritten; it no longer encodes coupling. See `docs/tasks/APRAS-128-mock.html`.

## Approach
Files touched:
- `backend/app/core/permissions.py`: `MODULE_BUNDLES` plus a pure `bundle_of(module)` and `split_bundles(active)` helper; import-time validation.
- `backend/app/services/tenant_service.py`, `subscription_service.py`, `plan_service.py`: call the split check in the four writers; new domain error mapped to 400 where the other module errors are mapped.
- `backend/app/schemas/tenant.py`, `schemas/subscription.py`: add `bundle` to the module row schemas.
- `backend/alembic/versions/<next>_module_bundles_backfill.py`: upward backfill for tenants, plans, courtesy.
- `frontend/src/features/user-administration/access/moduleGroups.ts`, `pages/TenantModulesPage.tsx`, `pages/SubscriptionPage.tsx`, API types: bundle-aware rendering.
- `AGENTS.md`: replace the "Companion modules (operator documentation, not code)" paragraph with the bundles, the independent assemblies/votes and uploads decisions, and the one-way dependencies left out.

Test criteria:
- `tests/test_module_bundles.py`: every member in `MODULES`, no module in two bundles, no bundle containing a CORE module, no bundle of fewer than two members.
- One test per writer (modules, subscription modules, courtesy, plan create and update): a splitting set answers 400, a whole-bundle set answers 200 and stores exactly what was submitted. Courtesy has extra cases: `courtesy=[tasks]` with the plan including `categories` and `categories` off answers 400 and writes nothing; the same with `categories` on answers 200; a whole-bundle list answers 200 with a whole resulting `disabled_modules`; revoking one member of a courtesy-granted bundle answers 400.
- Existing-permission tests prove `get_effective_permissions` output and `role.permissions` are unchanged (no source diff to deps.py).
- Migration test on SQLite/Postgres fixture: a tenant with `tasks` on / `categories` off ends with both on; a whole-off or whole-on bundle is untouched; idempotent.
- Vitest: one checkbox per bundle, toggling sends all members; a module with `bundle: null` and in no group still renders.

## Expected Results
- [ ] `MODULE_BUNDLES` is defined once in `permissions.py` and a test proves members exist in `MODULES`, no module is in two bundles, and no bundle contains a `CORE_MODULES` member.
- [ ] Bundles are exactly tasks+categories, reservations+spaces, assets+inventory, visitors+authorizations+gate; assemblies+votes and uploads are documented in this spec as not bundled, with reasons.
- [ ] `PUT /api/v1/tenants/{id}/modules`, `PUT /api/v1/subscription/modules`, `PUT /api/v1/tenants/{id}/subscription/courtesy` and plan create/update each answer 400 for a set that splits a bundle and 200 for a whole bundle, one test per route.
- [ ] `deps.py` and `filter_by_modules` have no diff, and no permission string or `role.permissions` row changes.
- [ ] `/admin/modules` and `/subscription` render one checkbox per bundle from the backend `bundle` field, and a module with no bundle or presentation group still renders.
- [ ] The migration turns a pre-existing split (tenant, plan, courtesy) into a whole bundle, leaves whole bundles unchanged, and a test covers it.
- [ ] `AGENTS.md` no longer says "operator documentation, not code" and describes the bundles and the left-out one-way dependencies.
- [ ] `cd backend && uv run pytest` (90% gate), `uv run ruff check .`, `ruff format --check .`, and `cd frontend && npx vitest run` (75% gate) pass.

## Out of Scope
One-way dependency mechanism or UI warnings; renaming permissions; per-bundle pricing; changing `get_effective_permissions`.
