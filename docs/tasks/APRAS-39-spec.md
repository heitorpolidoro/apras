# APRAS-39 — Modularizar features com ativação por tenant controlada pelo admin global

One deliverable, one PR: **a per-tenant module switch that composes with the
post-F5 permission model by *stripping* the disabled modules' permissions out
of the effective set**, plus the superuser screen that operates it.

Read this against the post-IAM world (F1 `APRAS-45` → F2 `APRAS-46` →
F3 `APRAS-47` → F4 `APRAS-48` → F5 `APRAS-49`), **not** against the tree this
spec was written on.

---

## 0. Preconditions, and how to read this spec against a moving tree

**Contracts, not files.** This spec was written at `aa8953d` (F2 landed) with
**F3 in flight in the same worktree** (`git status --short -- backend/` shows
`deps.py`, `permissions.py`, `endpoints/tenants.py`, `models/user.py`,
`services/tenant_service.py` modified) and F4/F5 approved but unimplemented.
It is specified against:

1. **Landed code** — `app/core/permissions.py` (`PERMISSIONS`,
   `ROUTE_PERMISSIONS`, `UNGUARDED_ROUTES`, `SCOPE_PERMISSIONS`, `module_of`),
   `app/api/deps.py` (`get_effective_permissions`, `has_permission`,
   `require_permission` / `PermissionRequired`, `get_current_tenant`,
   `get_current_superuser`, `is_acting_tenant_admin`),
   `app/core/tenant_context.py` (`ACTING_TENANT_KEY`, `acting_tenant_id`,
   `TENANT_SCOPED_MODELS`), `app/models/tenant.py` (`Tenant`,
   `UserTenantLink`, `DEFAULT_TENANT_ID`), `app/api/v1/endpoints/tenants.py`.
2. **`docs/tasks/APRAS-47-spec.md`** — `user.is_superuser`;
   `get_effective_permissions` short-circuits to the whole catalogue for a
   superuser and for an acting tenant_admin; every `/api/v1/tenants` write
   behind `deps.get_current_superuser` with detail
   `"The user doesn't have enough privileges"`.
3. **`docs/tasks/APRAS-48-spec.md`** — `GET /api/v1/permissions/me`
   (`MyPermissionsRead`), `GET /api/v1/permissions/`, both on
   `UNGUARDED_ROUTES`; `src/types/permissions.ts` (`AccessRule`,
   `MyPermissions`), `src/api/permissions.ts`,
   `src/hooks/usePermissionQueries.ts` (`useMyPermissions`),
   `src/features/user-administration/access/useCanAccess.ts`
   (`usePermissionSet`, `useEffectivePermissionSet`, `useCanAccess`,
   `useCanShowMenu`, the shared `evaluate`), `.../access/routeAccess.ts`
   (`ROUTE_ACCESS`, `NAV_ITEMS`), `ProtectedRoute` with the single
   `requiredAccess` prop and `RestrictedAccessMessage`.
4. **`docs/tasks/APRAS-49-spec.md`** — roles are data at `/api/v1/roles`
   (table `role`, link `user_role_link`); **no `UserRole` enum, no
   `allowed_menus`, no `assert_menu_access`, no `MenuKey`**; `PERMISSIONS` =
   **159** strings in **26** modules (`user_types` → `roles`);
   `ROUTE_PERMISSIONS` = **180**; `UNGUARDED_ROUTES` = **13**; total routes =
   **193**; `GLOBAL_ROUTES` = **18**; `MyPermissionsRead` = `{tenant_id,
   permissions[], landing_path}`; `UserMeRead.is_superuser`; head migration
   `0033_drop_user_role_and_menus`; `tests/data/parity_matrix_baseline.json`
   byte-identical at **1080** cells; `F5_PATH_RENAMES` in
   `tests/test_permission_parity_matrix.py`.

**By role, not by name.** If F3/F4/F5 landed a different *name* for something
named here (`get_effective_role_ids`, `role_service.py`, `RolesAdminPage`, …),
follow the landed name, record the deviation in the PR body, and change
nothing else. If a landed **number** differs (routes, permissions, coverage),
re-measure at the actual merge base, apply the deltas this spec states as
*deltas*, and quote measured-base + final in the PR body. The invariants that
outrank every constant here are: **`len(ROUTE_PERMISSIONS)` does not move**,
and `tests/data/parity_matrix_baseline.json` stays byte-identical.

**Concurrency.** APRAS-47's developer lane runs in this worktree now; 48 and 49
land before this task. Nothing in this spec edits a file that F3/F4/F5 delete.

---

## 1. Scope

**In.**

1. A module vocabulary derived from the permission catalogue: `MODULES` (26),
   `CORE_MODULES` (3, never disable-able), `TOGGLEABLE_MODULES` (23) in
   `app/core/permissions.py` (§2).
2. `tenant.disabled_modules` — one portable JSON column, `server_default
   '[]'`, migration `0034_add_tenant_modules` (§3, §4).
3. **One** enforcement point: `get_effective_permissions` strips the disabled
   modules' permissions from every non-superuser answer (§5). Route guards,
   in-handler `has_permission` checks, service-level checks, the frontend
   menu and the frontend routes all follow from it, with no second mechanism
   and no per-route registration. The **anti-escalation grant checks are the
   one deliberate exception**: `assert_can_grant` /
   `assert_can_assign_user_types` compare against the author's *unstripped*
   authority through `get_grantable_permissions` (§5.5), so the strip governs
   what a user may **do**, never who may administer roles.
4. Superuser-only `GET` / `PUT /api/v1/tenants/{tenant_id}/modules` (§6).
5. `GET /api/v1/permissions/me` gains `disabled_modules: list[str]` (§7).
6. Frontend: the superuser screen `/admin/modules`, an `AccessRule` shape for
   superuser-only routes, the simulation arm's intersection with the active
   modules, `RootRedirect`'s fallback when the landing route is not
   accessible, and the "module not enabled" variant of the restricted-access
   message (§10). pt/en i18n parity, mechanically asserted (§11).

**Out** — each with its reason, and none of them needed by any Expected
Result:

* **Plans / billing / entitlements.** `APRAS-40` makes plans govern which
  modules a tenant gets. Here the switch is manual and superuser-driven, and
  the default for a new tenant is **all modules on**. `APRAS-40` will write
  `disabled_modules` from a plan; this task deliberately builds the mechanism
  it will drive, and no plan table.
* **A module dependency graph.** The 26 modules toggle independently. Some are
  natural companions (`assets`/`inventory`, `reservations`/`spaces`,
  `visitors`/`authorizations`/`gate`/`access_control`, `tasks`/`categories`);
  the incoherent configurations they allow are *safe* (every endpoint of a
  disabled module refuses; a user can at worst reach a page whose companion
  data is empty) and reversible in one click. §2.3 documents the couplings
  and §10.3 groups the checklist by them, which is presentation, not
  machinery. Modelling `requires` edges would be a second authorization
  concept for an operator error that costs one checkbox to fix.
* **Per-sub-panel gating inside a page.** `LotsPage`'s residents panel calls
  `GET /api/v1/residents/…` unconditionally today; with `lots` on and
  `residents` off it renders its existing error state. Making every sub-panel
  permission-aware is a separate, larger sweep.
* **A distinct backend error message for "module disabled".** Rejected on
  purpose — see §5.4.
* **Role-editor decoration.** F4's editor already renders a permission the
  author does not hold as a *disabled* checkbox, and after §5 the author does
  not hold a disabled module's permissions, so ER-4's "inert" is already
  visible with zero code — and because the editor **resends** an already
  granted permission unchanged (APRAS-48 ER-4) and the API validates the
  resulting bundle against the *unstripped* set (§5.5), saving that role still
  answers 200. A "módulo não ativo" badge is a nicety for a later task.
* **`disabled_modules` on `TenantRead` or `TenantCreate`.** One write path
  (§6), one read path for the operator (§6) and one for the user (§7).

---

## 2. The module vocabulary

### 2.1 Modules are the catalogue's modules, derived and not hand-listed

```python
# app/core/permissions.py, after `module_of`

#: Every module named by the catalogue. Derived, never hand-listed: a module
#: introduced by a future task is toggleable (and active) the day its first
#: permission exists, with nobody having to remember a second list.
MODULES: frozenset[str] = frozenset(module_of(p) for p in PERMISSIONS)

#: The modules a tenant can never turn off: identity, membership and the
#: authorization vocabulary itself. Disabling any of them would make the
#: tenant unadministrable from inside — no user list, no role editor, no
#: tenant switcher — and would strip the very permissions the operator needs
#: to turn it back on from the tenant side.
CORE_MODULES: frozenset[str] = frozenset({"tenants", "users", "roles"})

#: The 23 billable features.
TOGGLEABLE_MODULES: frozenset[str] = MODULES - CORE_MODULES


def filter_by_modules(
    permissions: Iterable[str], disabled: Collection[str]
) -> frozenset[str]:
    """`permissions` minus every string whose module is in `disabled`.

    Pure and session-free, like everything else in this module. Strings whose
    module is not a catalogue module (a hand-edited row) are *kept*: the
    filter removes only what an operator explicitly turned off, which is what
    preserves `get_effective_permissions`'s documented "unknown strings are
    kept as is" property.
    """
    return frozenset(p for p in permissions if module_of(p) not in disabled)
```

`MODULES` is **26** and `CORE_MODULES ⊆ MODULES`; both are asserted
(§12.1). Post-F5 the identity module is named `roles`, not `user_types` — if
F5 landed a different name for it, `CORE_MODULES` follows the landed name and
the test that asserts `CORE_MODULES <= MODULES` catches a typo.

### 2.2 The enumeration, and what each module gates

Core (3) — always active, `PUT` refuses to disable them:

| Module | Perms | Why core |
|---|---|---|
| `tenants` | 6 | Tenant read/membership: the acting tenant, the switcher, the member list. |
| `users` | 3 | The user directory and contact info. |
| `roles` | 4 | The role editor — the surface that grants every other module's permissions. |

Toggleable (23) — the billable features, with the surface each removes:

| Module | Perms | Frontend surface removed when off |
|---|---|---|
| `tasks` | 7 | `/dashboard` (task board) |
| `categories` | 4 | `/categories` |
| `lots` | 7 | `/lots` |
| `residents` | 7 | the residents panel of `/lots` (no menu of its own) |
| `announcements` | 10 | `/announcements` |
| `documents` | 9 | `/documents` |
| `occurrences` | 6 | `/occurrences` |
| `feedback` | 3 | `/feedback` |
| `projects` | 9 | `/projects` |
| `finance` | 11 | `/finance` |
| `purchases` | 10 | `/purchases` |
| `assets` | 6 | `/assets` |
| `inventory` | 1 | the movements tab of `/assets` |
| `reservations` | 5 | `/reservations` |
| `spaces` | 4 | `/spaces` |
| `packages` | 5 | `/packages` |
| `visitors` | 4 | the visitor registry behind `/authorizations` and `/gate` |
| `authorizations` | 4 | `/authorizations` |
| `gate` | 3 | `/gate` |
| `access_control` | 7 | `/gate-monitor`, `/admin/access-control` |
| `assemblies` | 6 | the assembly half of `/voting` |
| `votes` | 11 | the poll half of `/voting` |
| `uploads` | 7 | `/admin/photo-approvals` and photo publishing |

23 + 3 = 26; the permission counts sum to 159 (`sum` asserted in §12.1 so a
future catalogue edit cannot silently drift this table out of date — the test
asserts the *totals*, not the table).

### 2.3 Companion modules (operator documentation, not code)

`assets` ↔ `inventory`; `reservations` ↔ `spaces`; `visitors` ↔
`authorizations` ↔ `gate` ↔ `access_control`; `tasks` → `categories`;
`assemblies` ↔ `votes`; `lots` → `residents`, `packages`. Turning one off
without its companion is legal and safe. The `/admin/modules` checklist is
grouped by these clusters (§10.3) so the operator sees them together, and
`AGENTS.md` records the list.

---

## 3. Storage: a JSON column on `tenant`, not a `tenant_module` table

**Decision: `tenant.disabled_modules: list[str]`**, portable `sa.JSON`,
`nullable=False`, `server_default "[]"` — copied field for field from
`user_type.permissions` (migration `0030`) and `user_type.allowed_menus`
(`0017`), for the reason both of them record: `ARRAY` does not compile against
SQLite and `backend/tests/conftest.py` builds the schema with
`SQLModel.metadata.create_all()` on `sqlite://` for every test in the suite.

Why not `tenant_module(tenant_id, module, is_enabled)`:

1. **The tenancy machinery would have to be taught about it.**
   `tenant_context._discover_scoped_models()` picks up *every* mapped class
   with a `tenant_id` column and excludes exactly one class by name
   (`UserTenantLink`). A `tenant_module` table would be auto-filtered by the
   acting tenant — fatal, because the superuser writes it on a **global**
   route for an *arbitrary* tenant — so the exclusion tuple would have to
   grow, `_stamp_tenant_on_write` would have to be reasoned about, and
   `tests/test_tenant_models.py`'s mechanical partition
   (`27 direct + 20 inherited + 3 unscoped == 50 tables`, exhaustive against
   `SQLModel.metadata`) would need a fourth classification. That is three
   invariants moved for one boolean per (tenant, module).
2. **Negative storage is free of backfill.** `[]` means "everything on", so
   the migration's `server_default` *is* the backfill for every existing
   tenant, a new tenant is all-on with no seeding, and a module added by a
   future task is on everywhere with no data step. A row-per-module table
   needs 23 inserts per tenant at creation time and a backfill for every
   future module.
3. **The read is free.** `deps.get_current_tenant` already does
   `session.get(Tenant, tenant_id)` on every scoped request, so the `Tenant`
   is in the session's identity map and reading `tenant.disabled_modules`
   inside `get_effective_permissions` costs **zero** additional SQL. A
   `tenant_module` read is one query per permission evaluation — and
   `has_permission` is called several times per request.
4. **The write is whole-state.** The API is a declarative `PUT` of the
   complete desired set (§6), which is exactly a column assignment and needs
   no diffing, no upsert and no delete.

What the column gives up, stated so it is not rediscovered: no per-toggle
audit row (who turned finance off, when) and no efficient "which tenants have
`finance` on" query. Neither is required by any Expected Result; both belong
to `APRAS-40`'s plan model, which will own the commercial history.

Model edit — `app/models/tenant.py`:

```python
class Tenant(SQLModel, table=True):
    ...
    # Modules explicitly turned off for this tenant (APRAS-39). Negative
    # storage on purpose: `[]` is "every module active", so the column's
    # server_default backfills every existing tenant, a new tenant is all-on
    # without seeding, and a module a future task adds is active everywhere
    # with no data step. Portable JSON, not a Postgres ARRAY, for the reason
    # `user_type.permissions` records: the test harness builds this schema on
    # sqlite:// with SQLModel.metadata.create_all().
    disabled_modules: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, server_default="[]"),
    )
```

`tenant` is already in `test_tenant_models.UNSCOPED_TABLES`; the table count
stays **50** and that module needs **no** edit.

---

## 4. Migration `0034_add_tenant_modules`

* `revision = "0034_add_tenant_modules"` — **23** characters, inside the
  32-char `alembic_version.version_num` limit.
* `down_revision = "0033_drop_user_role_and_menus"` (F5's head). **Read
  `alembic heads` at the merge base first** and use what it reports; if F5
  landed a different id or a sixth slice landed after it, chain onto the
  actual single head and say so in the PR body.
* `upgrade()`: one statement.

```python
def upgrade() -> None:
    op.add_column(
        "tenant",
        sa.Column("disabled_modules", sa.JSON(), nullable=False,
                  server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("tenant", "disabled_modules")
```

* **No data statement in either direction**, which is what makes it exactly
  reversible: the `server_default` is the all-on backfill for every existing
  tenant, including `DEFAULT_TENANT_ID`.
* `alembic heads` reports exactly one head, `0034_add_tenant_modules`, after
  it.
* Run it for real against the throwaway Postgres at port **5436** and quote
  `alembic upgrade head`, `alembic downgrade -1`, `alembic upgrade head` and
  the `\d tenant` listing in the PR body. **`nexdom` is protected — never
  point a migration run at it.**

---

## 5. Enforcement: strip the disabled modules out of the effective set

### 5.1 The change

```python
# app/api/deps.py

def disabled_modules(session: Session) -> frozenset[str]:
    """The modules the session's acting tenant has turned off.

    Empty when no acting tenant is resolved (a global route, `app/seed.py`,
    Alembic, a bare unit-test `Session`) and empty when the acting tenant row
    is absent, because a module switch must never be the reason a session
    that resolves no tenant grants nothing *extra*: the permissions that
    matter on those paths are the caller's own, and `get_current_tenant`
    guarantees the row exists on every request that has an acting tenant.

    `CORE_MODULES` is subtracted here rather than trusted from the row: the
    API refuses to write them (§6.3), and a hand-edited row must not be able
    to lock a condominium out of its own user and role administration.
    """
    tenant_id = tenant_context.acting_tenant_id(session)
    if tenant_id is None:
        return frozenset()
    tenant = session.get(Tenant, tenant_id)      # identity-map hit: 0 SQL
    if tenant is None:
        return frozenset()
    return frozenset(tenant.disabled_modules) - CORE_MODULES


def _resolve_permissions(user: User, session: Session) -> frozenset[str]:
    """The user's authority in the acting tenant, **before** the module strip.

    Exactly today's `get_effective_permissions` body, moved verbatim: the
    superuser short-circuit, the roles' bundles, the acting-tenant_admin
    whole-catalogue branch. Nothing here knows that modules exist.
    """
    # A superuser holds every permission there is, in every tenant, and with
    # no acting tenant at all.
    if user.is_superuser:
        return PERMISSIONS
    granted: set[str] | frozenset[str] = <roles' bundles, unchanged>
    # Administrator-level power inside one tenant (APRAS-43/F3).
    if is_acting_tenant_admin(user, session):
        granted = PERMISSIONS
    return frozenset(granted)


def get_effective_permissions(user: User, session: Session) -> frozenset[str]:
    """What the user may **do** here: authority ∩ the tenant's active modules.

    Every existing caller keeps this signature and this meaning. A superuser
    is deliberately unfiltered (§5.3) — `_resolve_permissions` returns
    `PERMISSIONS` and `disabled_modules` is subtracted from it only for
    non-superusers, which the `if user.is_superuser` short-circuit inside
    `_resolve_permissions` cannot express on its own, so the exemption is
    re-stated here explicitly.
    """
    resolved = _resolve_permissions(user, session)
    if user.is_superuser:
        return resolved
    return filter_by_modules(resolved, disabled_modules(session))


def get_grantable_permissions(user: User, session: Session) -> frozenset[str]:
    """What the user may **hand to somebody else**: authority, unstripped.

    The module switch is commercial packaging, not an authority boundary
    (§5.5). It must not freeze a tenant's role and membership administration,
    so the two anti-escalation guards — and nothing else in the codebase —
    read this function instead of `get_effective_permissions`.
    """
    return _resolve_permissions(user, session)
```

Three properties this shape buys, and they are the whole justification for
choosing it over a separate route gate:

* **ER-3 becomes nearly free.** Route-level `require_permission`, in-handler
  `has_permission`, every service-level check and `GET /permissions/me` —
  hence the frontend menu and the frontend routes — all read one function.
  There is exactly one place where "is this module active here" is decided,
  and no registry mapping routes to modules that a future endpoint could
  forget to join. The grant surface is the single, named, tested exception
  (§5.5).
* **ER-4's "composição" is literally an intersection.** *Access* requires
  `permission ∈ role bundles` **and** `module_of(permission) ∉ disabled` —
  neither replaces the other, and the module switch can only ever *narrow*
  what a user may do.
* **Toggling is non-destructive.** Nothing is deleted: `role.permissions`
  rows are untouched, so re-enabling a module restores exactly the previous
  access, with no data migration and no re-authoring. "Inertes" is exactly
  what the strip produces.

### 5.2 The rejected alternative: a separate route gate

A `ModuleRequired` dependency (or a `ROUTE_MODULES` map) would gate HTTP
routes only, and would therefore need a *second*, parallel answer for: the
in-handler `has_permission` calls F2 left inside handlers, the object-level
`SCOPE_PERMISSIONS` predicates (`residents:read_any_lot`,
`visitors:manage_any_lot`, `occurrences:manage_all`, `uploads:auto_approve`),
and `/permissions/me`. It also adds a
per-route registration a new endpoint can forget. The strip has none of those
seams. Recorded here so the choice is not relitigated in review.

### 5.3 The four actor classes

| Actor | Filtered? | Why |
|---|---|---|
| ordinary user (role bundles) | **yes** | the feature is not contracted for their condominium |
| acting tenant_admin | **yes** | the capability means "everything *this tenant* has", never more than the tenant has |
| **superuser** | **no** | the global operator is the one who *sets* the switch and must be able to inspect and repair a tenant whose module they just turned off. The flag is answered before any tenant is resolved (F3), and the module switch is a commercial packaging control over a tenant's users, not a data boundary. |
| any user, on a global route (no acting tenant) | **no** | nothing to strip: `/api/v1/tenants/*` and `/api/v1/auth/*` are core-module surfaces |

The superuser exemption is pinned by a named test
(`test_a_superuser_keeps_a_disabled_modules_permissions`) so it reads as a
decision rather than an oversight.

### 5.4 The refusal is byte-identical to any other permission refusal

A disabled module produces exactly the 403 the missing permission produces —
`"The user doesn't have enough privileges"` from `PermissionRequired`, or the
handler's/service's own `ForbiddenError` message. **No error-path code is
touched at all.**

Adding a distinct detail (`"This module is not enabled…"`) was considered and
rejected: it would only be reachable on the seven route-level guards — every
in-handler and service-level refusal has its own domain message — so it would
be a *partially* applied convention, and it would put a second module concept
into the error layer. The client that needs to distinguish gets
`disabled_modules` from `/permissions/me` (§7), which is complete and does not
depend on parsing a string. The operator diagnoses with
`GET /api/v1/tenants/{id}/modules`.

Consequence, stated: **no existing 403 assertion in the suite moves**, because
every existing test runs with `disabled_modules == []`.

### 5.5 The grant surface reads the **unstripped** set

**Decision (orchestrator, review round 1): the module strip governs what a
user may DO — route access, `has_permission`, `/permissions/me`, menus. The
anti-escalation GRANT validation compares against the author's UNSTRIPPED
effective set.**

*Why this has to be decided at all.* F2's guard validates the **whole
resulting bundle**, not the delta:

```python
# app/services/user_type_service.py:53 (post-F5: role_service.py, same shape)
missing = sorted(set(permissions) - get_effective_permissions(author, session))
```

and it is called with the *full* `PATCH` replacement list
(`endpoints/user_types.py:40`, `:81`) and, through
`assert_can_assign_user_types` (`endpoints/users.py:208`), with the **union of
the assigned roles' bundles**. Post-`0033` the seeded catalogue gives
`finance:read` to four of the six seeded roles (`ROLE_PERMISSIONS`'s
`"finance:read": frozenset({A, D, M, R})` — ADMINISTRATOR, DIRECTOR, MANAGER,
RESIDENT). If the guard read the *stripped* set, then in a tenant with
`finance` off:

* renaming any of those four roles would 403 — the editor resends
  `finance:read` (APRAS-48 ER-4 pins the resend), and the author no longer
  holds it;
* assigning any user to any of those four roles would 403 for the same reason;
* i.e. **role and membership administration in that tenant would freeze**,
  contradicting §1's "safe, reversible in one click".

And the tempting client-side workaround — the editor submitting only the
permissions the author currently holds — would silently **delete**
`finance:read` from the role row, destroying the non-destructiveness §5.1
sells and ER-4 pins.

*The mechanism.* `get_grantable_permissions(user, session)` (§5.1) returns
`_resolve_permissions` unfiltered. Exactly two call sites change, both inside
the guard module — the endpoints are untouched:

```python
# app/services/user_type_service.py  (post-F5: role_service.py)
-from app.api.deps import get_effective_permissions
+from app.api.deps import get_grantable_permissions
 ...
-    missing = sorted(set(permissions) - get_effective_permissions(author, session))
+    # APRAS-39 §5.5: the author's authority ignoring the tenant's module
+    # switch. A disabled module must not freeze role administration, and the
+    # grant is harmless: the strings are inert until the operator re-enables
+    # the module, at which point the author holds them too.
+    missing = sorted(set(permissions) - get_grantable_permissions(author, session))
```

`assert_can_assign_user_types` delegates to `assert_can_grant`, so it inherits
the change with no edit of its own. The `SUPERUSER_ONLY_PERMISSIONS` branch
runs **first** and is untouched: those four strings stay un-grantable to
everybody, superuser included.

*Why this does not escalate anything* — the invariant to check the design
against: **a grant can never exceed what the author holds with every module
on, which is exactly what the author will hold if the operator re-enables the
module.** So:

* an author who lacks `finance:category_create` even unstripped is still
  refused, module on or off (F2's pin, unchanged);
* an author who holds it unstripped could grant it anyway the moment the
  operator flips the module back on, and in the meantime the grantee's copy is
  inert — the strip is applied to the *grantee's* reads exactly as to
  everybody's;
* the superuser is unaffected: `_resolve_permissions` short-circuits to
  `PERMISSIONS` for them on both functions.

*The asymmetry between API and UI is deliberate.* The role editor enables its
checkboxes from `/permissions/me`, which **is** stripped, so an author cannot
*newly tick* a disabled module's permission through the UI, while the API
would accept it. Conservative UI, permissive API, no ER depends on the
missing direction, and the only thing the asymmetry protects is the
already-granted-string path that must keep working.

*Grep-pinned.* `get_grantable_permissions` has exactly one definition and
exactly two references in `backend/app/**` (both in the guard module), pinned
by `test_the_unstripped_resolver_is_used_only_by_the_escalation_guards`
(§12.1) so a later endpoint cannot quietly adopt it as a strip bypass.

---

## 6. The API — `GET` / `PUT /api/v1/tenants/{tenant_id}/modules`

### 6.1 Schemas — `app/schemas/tenant.py`

```python
class ModuleStateRead(BaseModel):
    """One module's state in one tenant."""
    module: str        # "finance"
    is_core: bool      # in CORE_MODULES: cannot be disabled
    is_active: bool    # not in tenant.disabled_modules


class TenantModulesRead(BaseModel):
    tenant_id: UUID
    modules: list[ModuleStateRead]   # all 26, sorted by `module`


class TenantModulesUpdate(BaseModel):
    """The complete desired state, declaratively."""
    disabled_modules: list[str]
```

`TenantModulesRead` answers ER-1's "cada tenant tem o seu conjunto de módulos
ativos" positively (the active set is enumerable per tenant) while storage
stays negative (§3).

### 6.2 Handlers — `app/api/v1/endpoints/tenants.py`

```python
@router.get("/{tenant_id}/modules", response_model=TenantModulesRead)
def get_tenant_modules(
    tenant_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    _: Annotated[User, Depends(api_deps.get_current_superuser)],
) -> TenantModulesRead:
    """Every module and its state in one tenant. Superuser only."""
    return TenantService.get_modules(session=session, tenant_id=tenant_id)


@router.put("/{tenant_id}/modules", response_model=TenantModulesRead)
def set_tenant_modules(
    tenant_id: UUID,
    modules_in: TenantModulesUpdate,
    session: Annotated[Session, Depends(get_session)],
    _: Annotated[User, Depends(api_deps.get_current_superuser)],
) -> TenantModulesRead:
    """Replace the tenant's disabled-module set. Superuser only."""
    return TenantService.set_modules(
        session=session, tenant_id=tenant_id, modules_in=modules_in
    )
```

`PUT`, not `PATCH`: the body is the *complete* desired state, so the operation
is idempotent, has no partial-update ambiguity, and matches the "one checkbox
list, one Save" screen of §10.3. The response is the same body `GET` returns,
so the client re-renders from the server's answer.

`TenantService.set_modules` writes
`tenant.disabled_modules = sorted(set(payload))`, `tenant.updated_at =
utcnow()`, commits, and returns the read model. Unknown `tenant_id` →
`TenantNotFoundError` (404, existing class and handler).

### 6.3 Validation — two new domain errors, both 400

```python
class UnknownModuleError(DomainError):
    """A module string that is not in the catalogue."""
    # "Unknown module: 'financee'"

class CoreModuleCannotBeDisabledError(DomainError):
    """A core module was listed as disabled."""
    # "Core modules cannot be disabled: roles, users"
```

**Where the two validations live:** inside `TenantService.set_modules`
(`app/services/tenant_service.py`, next to `update_tenant` /
`set_member_admin`), raised **before** the column assignment and before any
`commit`, so a rejected `PUT` leaves the row untouched. Explicitly **not** a
Pydantic `field_validator` on `TenantModulesUpdate`: a schema-level rejection
is answered by FastAPI's `RequestValidationError` handler as **422**, and ER-2
pins **400** for both cases. The schema validates *shape* (a list of strings);
the service validates *vocabulary* (catalogue membership, core-ness), which is
where the catalogue lives.

Both are plain `DomainError` subclasses and appear in none of
`exception_handlers.domain_exception_handler`'s 403/404/409/413/422 tuples, so
they fall through to its `status_code = 400` initialisation: **the handler
module needs no edit.** Duplicates in the payload are collapsed silently
(`set`), and an empty list is the legal "everything on" state.

### 6.4 Route accounting

Both routes are guarded by `deps.get_current_superuser` and map to **no**
catalogue permission — the convention APRAS-49 §8.4 established for
`PATCH /api/v1/users/{user_id}/superuser`, for its reason: minting catalogue
strings whose only purpose is to be refused by `assert_can_grant` would cost
**12** new parity cells (2 routes × 6 profiles) that cannot exist at the
baseline sha, and would move `tests/data/parity_matrix_baseline.json`.

| Constant | F5 merge base (predicted) | After this task |
|---|---|---|
| `len(PERMISSIONS)` | 159 | **159** — unchanged |
| `len(ROUTE_PERMISSIONS)` | 180 | **180** — unchanged |
| `len(UNGUARDED_ROUTES)` | 13 | **15** (+2) |
| total routes | 193 | **195** (+2) |
| `len(GLOBAL_ROUTES)` (`tests/test_tenant_route_scope.py`) | 18 | **20** (+2) |
| `len(ADMIN_ONLY_ROUTES)` (`tests/test_permission_enforcement.py`) | 5 | **7** (+2) |
| `len(ADMIN_ONLY_ROUTES)` (`tests/test_tenant_admin.py`, independent copy) | 5 | **7** (+2) |
| matrix cells | 1080 | **1080** — unchanged, baseline byte-identical |

`UNGUARDED_ROUTES` entries, with the comment the file's style requires:

```python
        # Per-tenant module activation: superuser-only, guarded by
        # deps.get_current_superuser (APRAS-39 §6.4).
        ("GET", "/api/v1/tenants/{tenant_id}/modules"),
        ("PUT", "/api/v1/tenants/{tenant_id}/modules"),
```

`GLOBAL_ROUTES` entries — the tenants router carries `GLOBAL_SCOPED`, not
`TENANT_SCOPED`:

```python
# app/api/v1/api.py:39,44,58
TENANT_SCOPED = [Depends(deps.get_current_tenant)]
GLOBAL_SCOPED = [Depends(deps.use_global_tenant_scope)]
...
api_router.include_router(tenants.router, prefix="/tenants", tags=["tenants"], dependencies=GLOBAL_SCOPED)
```

so both new routes inherit `use_global_tenant_scope`, depend on **no**
`get_current_tenant`, resolve no acting tenant, and are classified global
automatically (and `test_tenant_admin.test_no_tenant_scoped_route_keeps_a_global_admin_guard`
stays green for free). The allowlist grows by the two pairs with the comment
*"the module switch is a property of the tenant, written from outside it: a
tenant_admin must not be able to reach it by acting in their own tenant."*

**The `get_current_superuser` surface grows by exactly two, in two places.**
Two independent test modules pin that surface as an *exact set* over the
routes that depend on `deps.get_current_superuser`:
`tests/test_permission_enforcement.py` (`ADMIN_ONLY_ROUTES` +
`test_get_current_superuser_is_exactly_the_five_tenant_writes`) and its
deliberate duplicate in `tests/test_tenant_admin.py`. Both constants gain the
same two pairs and both case names are renamed
`..._is_exactly_the_five_tenant_writes` → `..._is_exactly_the_seven_tenant_routes`
(no longer only writes — one of the two is a `GET`):

```python
        # APRAS-39: the per-tenant module switch, read and write. Superuser
        # only, on the global tenants router.
        ("GET", "/api/v1/tenants/{tenant_id}/modules"),
        ("PUT", "/api/v1/tenants/{tenant_id}/modules"),
```

**FORBIDDEN, explicitly:** implementing the guard as an in-handler
`if not user.is_superuser: raise ...` (or any other hand-rolled check) to keep
those pins at five. Both routes **must** declare
`Depends(api_deps.get_current_superuser)` in their signature, exactly as §6.2
writes them, because the enforcement walkers
(`test_permission_enforcement.py`, `test_tenant_admin.py`,
`test_tenant_route_scope.py`) discover guards by traversing
`route.dependant`; an inlined check is invisible to all three and would leave
the two routes unaccounted for by every structural test in the repository.
The pins move by +2; they are not to be dodged.

**The invariant that outranks the constants:** `len(UNGUARDED_ROUTES) ==
base + 2`, `total routes == base + 2`, `len(GLOBAL_ROUTES) == base + 2`,
`len(ADMIN_ONLY_ROUTES) == base + 2` **in both copies**,
`len(ROUTE_PERMISSIONS)` and `len(PERMISSIONS)` **unchanged**. Quote the
measured base next to the final value for every row.

---

## 7. `GET /api/v1/permissions/me` gains `disabled_modules`

```python
class MyPermissionsRead(BaseModel):
    tenant_id: UUID
    permissions: list[str]        # sorted; already stripped by §5
    landing_path: str | None      # APRAS-49 §10.4
    disabled_modules: list[str]   # sorted; APRAS-39
```

Additive: one field, one line in the handler
(`disabled_modules=sorted(api_deps.disabled_modules(session))`), no new route,
no new permission, no change to `UNGUARDED_ROUTES`.

Two consumers, and they are the reason the field exists rather than being
derivable client-side:

1. `useEffectivePermissionSet`'s **simulation arm** builds its set from the
   role rows' `permissions` arrays (`useRoles()`), not from `/permissions/me`,
   so without this field a "view-as" preview would show menus for modules the
   tenant does not have (§10.2).
2. The **"module not enabled"** restricted-access variant (§10.4).

`permissions` is already stripped, so gating never reads this field —
which is what keeps a superuser (unstripped, §5.3) fully functional in a
tenant that has modules off, while still being *told* which ones are off.

Disclosure: every authenticated member of a tenant learns which modules that
tenant has. That is already inferable from the menu, and it is the tenant's
own configuration, not another tenant's.

---

## 8. Isolation

* `disabled_modules(session)` reads **only** the acting tenant's row. Tenant
  A's configuration can no more reach tenant B than A's roles can: the acting
  tenant comes from `session.info` (APRAS-42), and the same user acting in A
  and in B gets two different answers from `/permissions/me` with nothing but
  the `X-Tenant-Id` header changing. Pinned by
  `test_module_isolation_between_tenants`.
* The tenant_admin whole-catalogue short-circuit is filtered **by the tenant
  that granted it** — a síndico of A acting in B never reaches the branch at
  all (F3), and in A is bounded by A's modules.
* The superuser is unfiltered (§5.3) and writes the switch from a global
  route, so the capability to change it is structurally outside every tenant.

---

## 9. The matrix and the baseline

`tests/matrix_world.py` seeds its tenants through the ordinary model
constructors, so every tenant it builds has `disabled_modules == []`: **the
1080-cell world runs with all 26 modules active**, every cell keeps its
current answer, and `tests/data/parity_matrix_baseline.json` is
**byte-identical** (`git diff --stat` shows it absent from the PR).
`EXPECTED_CELL_COUNT` stays 1080 and `F5_PATH_RENAMES` is untouched — this
task renames no path.

That is asserted rather than assumed, by one new case in
`tests/test_permission_parity_matrix.py`:
`test_the_matrix_world_runs_with_every_module_active` — for every tenant the
world creates, `tenant.disabled_modules == []`, and
`filter_by_modules(PERMISSIONS, deps.disabled_modules(session)) ==
PERMISSIONS`. A future task that turns a module off in a fixture then fails
*this* test with a clear message instead of producing a mysterious baseline
diff.

The two edits that module *does* need are the allowlist-length ones (§6.4):
`test_the_thirteen_unguarded_routes_are_the_only_ones_excluded` →
`..._fifteen_...` with `== 13` → `== 15` (names as F5 leaves them).

---

## 10. Frontend

### 10.1 Types — `src/types/permissions.ts`

```ts
export interface MyPermissions {
  tenant_id: string;
  permissions: PermissionKey[];
  landing_path: string | null;
  disabled_modules: string[];       // APRAS-39
}

export type AccessRule =
  | { module: string; legacyMenu?: never; landingRedirect?: boolean }
  | { anyOf: readonly PermissionKey[]; landingRedirect?: never }
  | { superuser: true };            // APRAS-39
```

The third shape is the smallest honest extension of F4's "exactly two shapes":
`/admin/modules` is the first frontend surface for a **superuser-only backend
route**, and by §6.4's convention such routes carry no catalogue permission —
so no `{anyOf}` rule can express it. `{anyOf:["tenants:update"]}` is
specifically wrong: `tenants:update` is in `SUPERUSER_ONLY_PERMISSIONS` but an
acting tenant_admin still holds it through the whole-catalogue short-circuit,
so the rule would offer the menu to a user the API answers 403.

`evaluate` gains one branch: `"superuser" in rule` → the caller-supplied
superuser flag. **The flag is passed in as an argument, never read inside
`evaluate`** — F4 specifies `evaluate` as a pure function, and calling
`useAuth()` from it would make it a hook and break every direct unit test:

```ts
// F4: evaluate(rule, permissions, …) -> boolean, pure
export function evaluate(
  rule: AccessRule,
  permissions: ReadonlySet<PermissionKey>,
  isSuperuser = false,            // APRAS-39, defaulted so no call site breaks
): boolean {
  if ("superuser" in rule) return isSuperuser;
  ...
}
```

`useCanAccess` / `useCanShowMenu` read `is_superuser` from `useAuth()` (F5 §8.3
puts it on `UserMeRead`) and pass it down. It is **never** simulated: both
hooks take the flag from the real auth user, never from the simulated identity,
so "view-as" cannot open an operator screen.

### 10.2 The simulation arm intersects with the active modules

`useEffectivePermissionSet`, while simulating, builds `all` from the union of
the simulated roles' `permissions` arrays. It now intersects that union with
the tenant's active modules:

```ts
const disabled = new Set(myPermissions?.disabled_modules ?? []);
all = new Set([...union].filter((p) => !disabled.has(p.split(":", 1)[0])));
```

Without this, an operator simulating a role in a tenant with `finance` off
would preview a menu the real user cannot have. `usePermissionSet` (the
authorization arm) needs **no** change: its payload is already stripped by
§5.

### 10.3 The superuser screen — `/admin/modules`

* Route: `ROUTE_ACCESS["/admin/modules"] = { superuser: true }`; `NAV_ITEMS`
  gains the matching entry (`nav.modules`), so F4's "every nav item's access
  *is* its route's rule" test keeps passing.
* Page: `src/features/user-administration/pages/TenantModulesPage.tsx` — the
  same directory as the other tenant/administration surfaces
  (`AdminUserDashboard`, `TenantContext`).
* Data: `src/api/tenants.ts` (**new**) — `listTenants()`,
  `getTenantModules(tenantId)`, `putTenantModules(tenantId, disabled)`;
  `src/hooks/useTenantModules.ts` (**new**) — `useTenantModules(tenantId)`
  (`queryKey: ["tenants", tenantId, "modules"]`, `enabled: !!tenantId`) and
  `useSetTenantModules(tenantId)` invalidating that key **and**
  `["me","permissions"]`. The key starts with `"tenants"`, so
  `setActingTenant`'s `resetQueries` predicate
  (`queryKey[0] !== "tenants"`) deliberately preserves it: this data is keyed
  by an explicit tenant id and does not depend on the acting tenant.
* UI: a tenant `<select>` (from `GET /tenants`, which returns every tenant to
  a superuser) + a checkbox list of the 26 modules **grouped by the §2.3
  clusters**, core modules rendered checked and `disabled` with a "core"
  badge, a Save button that `PUT`s the derived `disabled_modules`, and the
  standard loading/error/success states. Optimistic updates are not used —
  the response body is the new state.
* Paths are written exactly as FastAPI mounts them (`/tenants`,
  `/tenants/{id}/modules`, no trailing slash), for the 307-drops-the-header
  reason `api/client.ts` already documents.

### 10.4 The tenant user's experience

* **Menu**: nothing to do. `NAV_ITEMS` is gated by `useCanShowMenu` over the
  (stripped) permission set, so a disabled module's item is absent. ER-3's
  first half is satisfied by §5 alone.
* **Direct URL**: `ProtectedRoute` renders `RestrictedAccessMessage`, again
  with no code change. It gains one **presentational** branch: when the
  route's rule names a module (`{module}` shape, or the first `anyOf`
  entry's module) that is in `disabled_modules`, it renders
  `t("common.moduleUnavailable")` /
  `t("common.moduleUnavailableMessage")` instead of the generic restricted
  copy. Same component, same 0 network calls, different two strings.
* **`RootRedirect`**: `landing_path ?? "/dashboard"` (F5 §10.4) can now point
  at a route the user cannot open — a tenant with `tasks` off strands
  everyone on a restricted `/dashboard`. `RootRedirect` therefore falls back,
  in order: `landing_path` if the user can access its route → `/dashboard` if
  accessible → the first `NAV_ITEMS` entry `useCanShowMenu` allows →
  `/welcome`. Pinned by `RootRedirect.test.tsx::lands on the first accessible
  nav item when the landing module is disabled`.

  **Determinism:** "the first entry" means the first in `NAV_ITEMS`
  *declaration order*, which is a module-level array literal and therefore
  stable across renders, reloads and machines. The chain is written as a
  `.find()` over that array — never over a `Set`, an object's `Object.keys`,
  or a filtered map — so two users with the same permission set always land on
  the same path, and reordering `NAV_ITEMS` is the only thing that can change
  a landing. The test asserts the specific path, so a reorder is caught.

* **The empty-set terminal is real, and `/welcome` already exists.** The
  fallback's last step is not decorative: `ROLE_PERMISSIONS` gives PORTEIRO 14
  permissions spanning exactly five modules — `gate`, `lots`, `packages`,
  `reservations`, `tasks` — **all five toggleable**. A tenant that buys only
  the finance package (all five off) leaves its porteiros with an empty
  effective set: no nav item passes `useCanShowMenu`, `landing_path` and
  `/dashboard` both fail, and the chain terminates at `/welcome`. GUEST is the
  same case (its four modules — `announcements`, `authorizations`,
  `documents`, `occurrences` — are all toggleable). `/welcome` is
  `GuestWelcomePage` (`src/App.tsx:98`, already the GUEST terminal and
  `ProtectedRoute.tsx:83`'s redirect target) and is reachable with **no**
  permission at all, so this is a landing, not a redirect loop. No new page,
  no new route, no copy change — only the guarantee that the chain ends
  somewhere renderable, pinned by a second `RootRedirect.test.tsx` case
  (`lands on /welcome when every module the user's role covers is disabled`).

---

## 11. i18n

New keys, added to **both** `en.json` and `pt.json`:

* `nav.modules` — "Modules" / "Módulos".
* `common.moduleUnavailable`, `common.moduleUnavailableMessage` —
  "Module not enabled" / "Módulo não contratado" and a sentence pointing at
  the administrator.
* `modules.title`, `modules.tenantLabel`, `modules.save`, `modules.saved`,
  `modules.saveError`, `modules.coreBadge`, `modules.coreHint`,
  `modules.groups.*` (the §2.3 cluster headings).
* `modules.names.<module>` — **26** labels, e.g.
  `modules.names.finance` = "Finanças" / "Finance",
  `modules.names.access_control` = "Controle de acesso" / "Access control".

Parity is asserted mechanically, which the repository does not do today:
`src/i18n/__tests__/index.test.ts` gains
`it("has identical key sets for en and pt")` — a recursive key-path
comparison of the two resource trees, `expect(onlyInEn).toEqual([])` and
`expect(onlyInPt).toEqual([])`, plus
`it("labels every module in both languages")` asserting
`modules.names` has exactly the 26 module keys in each language. The 26 keys
are listed in the test from a local constant, so a catalogue module added
later without a label fails the test.

**Measured safe before specifying it.** The parity test is a *pin*, not a fix:
`src/i18n/locales/en.json` and `pt.json` already have **identical** key sets
today — 1093 leaf paths each, `onlyInEn == []` and `onlyInPt == []` (measured
at the spec sha with a recursive key-path diff; the same computation the test
performs). So the new case is green on arrival and its only cost is that this
task's ~40 new keys, and every future key, must be added to both files.
Re-measure at the merge base and quote the count in the PR body; if F4/F5
landed an asymmetry, **fix the asymmetry** rather than weakening the
assertion — an `expect.arrayContaining` or an allowlist of known-missing keys
is not acceptable here.

---

## 12. Tests

### 12.1 New backend test modules

**`backend/tests/test_module_vocabulary.py`**

| Test | Asserts |
|---|---|
| `test_modules_are_derived_from_the_catalogue` | `MODULES == {module_of(p) for p in PERMISSIONS}`, `len(MODULES) == 26` |
| `test_core_modules_are_three_and_real` | `CORE_MODULES == {"tenants","users","roles"}` and `CORE_MODULES <= MODULES` |
| `test_toggleable_modules_partition_the_catalogue` | `TOGGLEABLE_MODULES | CORE_MODULES == MODULES`, disjoint, `len == 23` |
| `test_filter_by_modules_removes_exactly_one_module` | `filter_by_modules(PERMISSIONS, {"finance"})` drops the 11 `finance:*` and nothing else |
| `test_filter_by_modules_keeps_uncatalogued_strings` | `"legacy:thing"` survives a filter that disables `finance` |
| `test_every_permission_belongs_to_a_declared_module` | `{module_of(p) for p in PERMISSIONS} <= MODULES`; total `len(PERMISSIONS) == 159` |

**`backend/tests/test_tenant_modules_api.py`**

| Test | Asserts |
|---|---|
| `test_get_lists_every_module_with_its_state` | 200; 26 rows sorted by `module`; `is_core` true for exactly the three; all `is_active` for a fresh tenant |
| `test_put_disables_and_get_reflects_it` | `PUT {"disabled_modules":["finance"]}` → 200 with `finance.is_active is False`; a follow-up `GET` agrees |
| `test_put_is_declarative_and_reenables` | `PUT {"disabled_modules":[]}` after the above → every module active again |
| `test_put_rejects_an_unknown_module` | 400, detail names the string; the row is unchanged |
| `test_put_rejects_a_core_module` | 400 for each of `tenants`, `users`, `roles`; the row is unchanged |
| `test_put_deduplicates_and_sorts` | `["finance","finance","assets"]` stores `["assets","finance"]` |
| `test_a_tenant_admin_cannot_read_or_write_the_switch` | 403 `"The user doesn't have enough privileges"` on both routes, including for the tenant they administer |
| `test_an_ordinary_user_cannot_read_or_write_the_switch` | 403 on both |
| `test_an_unauthenticated_caller_gets_401` | 401 on both |
| `test_unknown_tenant_is_404` | 404 on both |
| `test_a_new_tenant_starts_with_every_module_active` | `POST /api/v1/tenants` then `GET .../modules` → 26 active, `tenant.disabled_modules == []` |
| `test_the_routes_are_unguarded_and_global` | both pairs in `UNGUARDED_ROUTES` and in `test_tenant_route_scope.GLOBAL_ROUTES`, neither in `ROUTE_PERMISSIONS`; `len(ROUTE_PERMISSIONS) == 180`; the counts of §6.4 |
| `test_the_switch_writes_only_the_named_tenant` | writing A leaves B's `disabled_modules` empty (the `tenant_id_field` default cannot apply: `tenant` is not a scoped model, but the assertion is cheap and closes the class of bug) |

**`backend/tests/test_module_gating.py`** — the composition, at the wire:

| Test | Asserts |
|---|---|
| `test_a_disabled_modules_permissions_leave_the_effective_set` | `finance` off ⇒ no `finance:*` in `get_effective_permissions` for a user whose role carries `finance:read`; every other permission survives |
| `test_a_disabled_module_endpoint_refuses_a_permitted_user` | that user gets **403** on `GET /api/v1/finance/transactions` (in-handler check) and on `DELETE /api/v1/lots/{id}` with `lots` off (route-level `require_permission`) |
| `test_permissions_me_omits_the_disabled_modules_permissions` | `GET /api/v1/permissions/me` lacks every `finance:*` and lists `"finance"` in `disabled_modules` |
| `test_a_tenant_admin_is_bounded_by_the_tenants_modules` | tenant_admin of A with `finance` off: `/permissions/me` == `PERMISSIONS` minus the 11 `finance:*`; 403 on the finance route |
| `test_a_superuser_keeps_a_disabled_modules_permissions` | superuser in the same tenant: `/permissions/me` == `PERMISSIONS`; 200 on the finance route (§5.3) |
| `test_core_modules_cannot_be_stripped_even_by_a_hand_edited_row` | a row written directly with `["users","roles"]` still yields every `users:*`/`roles:*` |
| `test_re_enabling_restores_access_with_no_data_change` | disable → 403; re-enable → 200. **Non-destructiveness is asserted against the database, not the API**: capture `list(role.permissions)` before, then after the toggle cycle `session.expire_all()` and re-read the row with a direct `session.exec(select(Role).where(Role.id == role_id))` (post-F5 name), asserting the list is **byte-identical** — same strings, same order, same length. Reading it back through `GET /api/v1/roles/{id}` would prove nothing: that response is assembled from the same ORM object and would hide a rewrite that happened to round-trip |
| `test_module_isolation_between_tenants` | one user, member of A (finance off) and B (finance on): `X-Tenant-Id: A` ⇒ 403 + stripped `/permissions/me`; `X-Tenant-Id: B` ⇒ 200 + `finance:read` present; B's row untouched |
| `test_no_acting_tenant_strips_nothing` | a bare `Session` with no acting tenant, and a global route: `disabled_modules(session) == frozenset()` |
**`backend/tests/test_module_gating_grants.py`** — §5.5, the grant surface.
This module is the one that would have caught the frozen-administration bug,
so it is separate and named for it:

| Test | Asserts |
|---|---|
| `test_renaming_a_role_that_carries_a_disabled_modules_permission_still_works` | tenant A, `finance` off; a tenant_admin `PATCH`es a seeded role that carries `finance:read` (four of the six do) with the editor's full resend — new `name`, **identical** `permissions` list → **200**, and the row still carries `finance:read` afterwards (direct SELECT) |
| `test_assigning_a_user_to_a_role_carrying_a_disabled_modules_permission_still_works` | same tenant; assigning that role to a user (`assert_can_assign_user_types`) → **200**; the assignee's `GET /permissions/me` then contains **no** `finance:*` — granted and inert in the same test |
| `test_a_disabled_modules_permission_can_still_be_added_by_an_author_who_holds_it_unstripped` | the author holds `finance:read` unstripped; adding it to a second role while `finance` is off → 200, `finance:read` present in the row, absent from every reader's effective set |
| `test_an_over_privileged_grant_is_still_refused_with_the_module_off` | the F2 pin, restated under a module switch: an author who lacks `finance:category_create` **even unstripped** is still **403** with F2's message `"You cannot grant permissions you do not hold: finance:category_create"` — module off *and* module on. The switch must not become a grant loophole |
| `test_an_over_privileged_assignment_is_still_refused_with_the_module_off` | the same for `assert_can_assign_user_types` (`endpoints/users.py:208`) |
| `test_superuser_only_permissions_are_still_ungrantable_with_the_module_off` | the `SUPERUSER_ONLY_PERMISSIONS` branch runs first and is untouched: 403 with its own message, for every author including a superuser |
| `test_the_grant_guard_reads_the_unstripped_set` | unit-level: with `finance` off, `get_effective_permissions(author, session)` lacks `finance:read` while `get_grantable_permissions(author, session)` contains it, for the same user and session |
| `test_the_unstripped_resolver_is_used_only_by_the_escalation_guards` | a source scan of `backend/app/**/*.py`: `get_grantable_permissions` appears exactly once as a `def`, and is *referenced* only in the guard module (its import + the one call) — a later endpoint cannot adopt it as a strip bypass without turning this test red |

**`backend/tests/test_migrations_postgres.py`** — one new section (see §12.2).

### 12.2 Pre-existing test modules that legitimately change

| Module | Change | Must not change |
|---|---|---|
| `tests/test_permission_registry.py` | `len(UNGUARDED_ROUTES)` `13 → 15` and the case name `..._is_thirteen_routes` → `..._is_fifteen_routes`; total routes `193 → 195` in `test_route_count_is_fully_accounted_for` and in its docstring (`193/180/13` → `195/180/15`) | `len(ROUTE_PERMISSIONS) == 180`; every other entry |
| `tests/test_permission_parity_matrix.py` | `test_the_thirteen_unguarded_routes_are_the_only_ones_excluded` → `..._fifteen_...`, `== 13` → `== 15`; **new** `test_the_matrix_world_runs_with_every_module_active` (§9) | `EXPECTED_CELL_COUNT == 1080`; `F5_PATH_RENAMES`; the golden file, byte-identical |
| `tests/test_tenant_route_scope.py` | `GLOBAL_ROUTES` gains the two module routes with their comment (18 → 20) | its computed accounting test |
| `tests/test_permission_enforcement.py` | `ADMIN_ONLY_ROUTES` gains `("GET", "/api/v1/tenants/{tenant_id}/modules")` and `("PUT", …)` (5 → 7), and `test_get_current_superuser_is_exactly_the_five_tenant_writes` → `..._is_exactly_the_seven_tenant_routes` (§6.4). This is an **exact-set** assertion over `_depends_on(route.dependant, deps.get_current_superuser)`, so it fails unless the guard is a real dependency — see §6.4's prohibition on inlining the check | `ROUTE_PERMISSIONS_*` allowlists, `GLOBAL_PREFIXES`/`GLOBAL_EXTRA`, every other case in the module |
| `tests/test_tenant_admin.py` | the **independent duplicate** of `ADMIN_ONLY_ROUTES` and of `test_get_current_superuser_is_exactly_the_five_tenant_writes`: the identical two-entry addition and the identical rename. The duplication is deliberate (the module states its own boundary), so both copies must move or the suite is red | `test_no_tenant_scoped_route_keeps_a_global_admin_guard` (green unchanged: the new routes carry `GLOBAL_SCOPED`, not `get_current_tenant`); every membership/role-seeding case |
| `tests/test_effective_permissions.py` | new cases for the strip: the superuser exemption, the tenant_admin bound, the no-acting-tenant no-op, and `get_grantable_permissions == get_effective_permissions` whenever `disabled_modules == []`. Every existing case runs with `disabled_modules == []` and its assertions are unchanged | every existing assertion |
| `tests/test_permission_escalation.py`, `tests/test_legacy_role_permissions.py` | **none** — they run with `disabled_modules == []`, where the stripped and unstripped sets are equal by construction, so §5.5's swap is invisible to them | every escalation assertion and message, verbatim |
| `tests/test_permissions_api.py` (F4) | the `/permissions/me` body gains `disabled_modules`; two cases assert it (`[]` by default; `["finance"]` after a `PUT`) | the catalogue cases |
| `tests/test_migrations_postgres.py` | the head-revision literals `"0033_drop_user_role_and_menus"` → `"0034_add_tenant_modules"` (the module pins the head in several places); a new `0034` section: the column exists `NOT NULL DEFAULT '[]'`, every pre-existing tenant reads `[]` after upgrade, `downgrade -1` drops it and `upgrade` re-applies cleanly | every earlier revision's assertions |
| `tests/test_tenant_models.py` | **none** — `tenant` is already in `UNSCOPED_TABLES`, the table count stays 50 | the 27/20/3 partition |

### 12.3 Frontend tests

| File | Case |
|---|---|
| `TenantModulesPage.test.tsx` (**new**) | renders the 26 modules grouped, core ones checked+disabled; unchecking `finance` and saving `PUT`s `{"disabled_modules":["finance"]}`; the error state on a 400; the tenant `<select>` refetches |
| `ProtectedRoute.modules.test.tsx` (**new**) | with `disabled_modules:["finance"]` and no `finance:*`, `/finance` renders `common.moduleUnavailable` (not the generic copy); with `finance` active but the permission missing, it renders the generic copy |
| `Navbar.modules.test.tsx` (**new**) | the `/finance` link is absent when `finance:*` is absent from `/permissions/me`, present otherwise |
| `useCanAccess.superuser.test.tsx` (**new**) | `{superuser:true}` allows a superuser, refuses a tenant_admin, and is **not** simulated |
| `RootRedirect.test.tsx` | two new cases: lands on the first accessible nav item (declaration order, asserted by path) when `landing_path`'s route is not accessible; and lands on `/welcome` when the effective set is empty (the all-modules-off PORTEIRO of §10.4) |
| the role-editor test file (F4/F5 name) | new case: with `finance` off, the finance permissions render checked-and-disabled, and **saving the role still succeeds** — the request body still carries `finance:read` and the mocked API answers 200 (§5.5's UI half; the string is never dropped from the payload) |
| `useCanAccess.test.tsx` / `useEffectiveIdentity.test.tsx` (F4/F5 names) | the simulation arm intersects with `disabled_modules` |
| `src/i18n/__tests__/index.test.ts` | the two parity cases of §11 |

Every test that mounts a component reading `useMyPermissions` provides a
`QueryClientProvider` and a payload carrying the new field (F4 §8.2's rule).

---

## 13. `AGENTS.md`

A **Módulos por tenant** subsection under *Domain Concepts*, next to *Tenant*:
the 26 modules and the 3 core ones; `tenant.disabled_modules` as negative
storage with `[]` = all on; the single enforcement point
(`get_effective_permissions` strips, therefore routes, services and menus all
follow) **and its single exception — the grant guards read
`get_grantable_permissions`, unstripped, so a disabled module never freezes
role or membership administration (§5.5)**; the superuser exemption and why;
the two superuser routes with a `curl`; the companion-module list (§2.3); and
the sentence that toggling is non-destructive — role bundles are never edited,
so re-enabling restores exactly the previous access. The endpoint table gains
the two routes.

---

## 14. Gates, baselines and the PR body

| Metric | Gate | Requirement |
|---|---|---|
| `pytest` (backend) | `--cov-fail-under=90` | green, ≥ 90 and ≥ the F5 merge-base measurement |
| `npm run test` | — | all pass; the PR body says how the file/test count moved |
| Vitest statements / branches / functions / lines | 80 / 76 / 78 / 80 | ≥ gate **and** ≥ the F5 merge-base measurement for each |
| `npm run lint` | — | ≤ the F5 merge-base problem count; **0** new findings in non-test `src/**` |
| `npm run build` | — | passes (`tsc -b` included) |
| `ruff check backend` | — | **0** new findings |
| `alembic heads` | — | exactly one: `0034_add_tenant_modules` |
| `len(PERMISSIONS)` / `len(ROUTE_PERMISSIONS)` | pinned | **unchanged** (predicted 159 / 180) |
| `len(UNGUARDED_ROUTES)` / total routes / `len(GLOBAL_ROUTES)` | pinned | **base + 2** each (predicted 15 / 195 / 20) |
| `ADMIN_ONLY_ROUTES` (both copies) | pinned | **base + 2** each (predicted 7 / 7), with the guard as a real `Depends`, never inlined |
| `tests/data/parity_matrix_baseline.json` | pinned | absent from `git diff --stat` |

**The PR body must carry:** the measured F5 merge-base value next to the final
value for every row above; `git diff --stat -- backend/tests/data/parity_matrix_baseline.json`
(empty); `alembic heads`; a real `alembic upgrade head` / `downgrade -1` /
`upgrade head` cycle against the throwaway Postgres on **5436** (never
`nexdom`) with the `\d tenant` listing; the §5.3 superuser-exemption decision
and the §5.5 unstripped-grant decision each restated in one line; the two
`ADMIN_ONLY_ROUTES` copies quoted at 5 → 7 with their renamed test; the i18n
parity test output (with the measured en/pt key count); and any name deviation
from F3/F4/F5 (§0).

---

## Expected Results

- [ ] **ER-1 — modules are declared, and every tenant has an enumerable
  active set.** `app/core/permissions.py` exports `MODULES` (derived from
  `PERMISSIONS`, **26**), `CORE_MODULES` (**3**: `tenants`, `users`, `roles`)
  and `TOGGLEABLE_MODULES` (**23**), asserted by
  `tests/test_module_vocabulary.py`. `GET /api/v1/tenants/{tenant_id}/modules`
  as a superuser returns **200** with 26 `{module, is_core, is_active}` rows
  sorted by `module`; a tenant created by `POST /api/v1/tenants` returns 26
  rows all `is_active: true` and stores `disabled_modules == []`.
- [ ] **ER-2 — the global superuser, and only the superuser, toggles a module
  for one tenant.** `PUT /api/v1/tenants/{tenant_id}/modules`
  `{"disabled_modules":["finance"]}` returns 200 with `finance.is_active
  false`, and `{"disabled_modules":[]}` restores it. The same call returns
  **403** `"The user doesn't have enough privileges"` for an ordinary user and
  for the tenant_admin of that very tenant, **401** unauthenticated, **404**
  for an unknown tenant, and **400** for an unknown module string or for any
  of the three core modules. Pinned by `tests/test_tenant_modules_api.py`.
- [ ] **ER-3 — a disabled module disappears from the navigation *and* its
  endpoints refuse.** With `finance` disabled in tenant A, a user whose role
  carries `finance:read`: (a) `GET /api/v1/permissions/me` contains no
  `finance:*` and lists `"finance"` in `disabled_modules`; (b) `GET
  /api/v1/finance/transactions` answers **403**, and `DELETE
  /api/v1/lots/{id}` answers 403 with `lots` disabled — i.e. both the
  in-handler and the route-level guard refuse; (c) Vitest: the `/finance` nav
  link is absent and navigating directly to `/finance` renders the
  `common.moduleUnavailable` message. Pinned by
  `tests/test_module_gating.py`, `Navbar.modules.test.tsx` and
  `ProtectedRoute.modules.test.tsx`.
- [ ] **ER-4 — activation composes with permissions and never replaces
  them, and never freezes role administration.** *Access* requires the module
  active **and** the permission held: a user without `finance:read` still gets
  403 while `finance` is active; an acting tenant_admin's whole-catalogue set
  equals `PERMISSIONS` minus exactly the 11 `finance:*` strings while
  `finance` is off. The disabled module's permissions are **inert, not
  deleted**: after a disable → re-enable cycle the role row's `permissions`
  list is **byte-identical** — asserted by a direct `SELECT` on the role row
  after `session.expire_all()`, not through the API — and re-enabling restores
  200 with no data step. *Granting* is deliberately **not** stripped
  (§5.5): with `finance` off in tenant A, a tenant_admin renaming a seeded
  role that carries `finance:read` gets **200** (the editor's full resend,
  `permissions` unchanged in the row), assigning a user to that role gets
  **200** while that user's `/permissions/me` still contains no `finance:*`,
  and adding `finance:read` to another role succeeds for an author who holds
  it unstripped — because `assert_can_grant` /
  `assert_can_assign_user_types` compare against
  `get_grantable_permissions` (unstripped) while everything else reads
  `get_effective_permissions` (stripped). The escalation pins still hold with
  the module off: an author who lacks `finance:category_create` even
  unstripped is still 403 with F2's message, on both the grant and the
  assignment surface, and `SUPERUSER_ONLY_PERMISSIONS` stays un-grantable to
  everyone. Pinned by `tests/test_module_gating.py` and
  `tests/test_module_gating_grants.py`, whose
  `test_the_unstripped_resolver_is_used_only_by_the_escalation_guards`
  asserts `get_grantable_permissions` is referenced nowhere else in
  `backend/app/**`.
- [ ] **ER-5 — isolation, and the deliberate superuser exemption.** One user
  who is a member of tenants A (`finance` off) and B (`finance` on) gets a
  403 with `X-Tenant-Id: A` and a 200 with `X-Tenant-Id: B` on the same
  endpoint, with no other request difference, and B's `disabled_modules` stays
  `[]`. A **superuser** is not filtered: `/permissions/me` returns the whole
  **159**-string catalogue and the finance endpoint answers 200 in tenant A.
  A session with no acting tenant strips nothing. Pinned by
  `test_module_isolation_between_tenants`,
  `test_a_superuser_keeps_a_disabled_modules_permissions` and
  `test_no_acting_tenant_strips_nothing`.
- [ ] **ER-6 — one small, reversible migration, all-on backfill.**
  `alembic heads` reports exactly one head, `0034_add_tenant_modules`; against
  a real throwaway Postgres, `upgrade head` adds `tenant.disabled_modules`
  `JSON NOT NULL DEFAULT '[]'`, every pre-existing tenant (including
  `00000000-0000-0000-0000-000000000001`) reads `[]`, `downgrade -1` drops the
  column and a re-`upgrade` succeeds. No data statement in either direction.
  Pinned by the new `0034` section of `tests/test_migrations_postgres.py`.
- [ ] **ER-7 — the parity world and the enforcement surface do not move.**
  `tests/data/parity_matrix_baseline.json` is byte-identical (absent from
  `git diff --stat`), `EXPECTED_CELL_COUNT == 1080`,
  `len(ROUTE_PERMISSIONS)` and `len(PERMISSIONS)` are unchanged from the F5
  merge base (predicted 180 / 159), and
  `test_the_matrix_world_runs_with_every_module_active` asserts every
  matrix-world tenant has `disabled_modules == []`. `len(UNGUARDED_ROUTES)`,
  the total route count and `len(GLOBAL_ROUTES)` are each **merge base + 2**
  (predicted 15 / 195 / 20), with the measured base quoted in the PR body.
  **Both** exact-set pins on the `deps.get_current_superuser` surface grow by
  the same two pairs and stay green — `ADMIN_ONLY_ROUTES` in
  `tests/test_permission_enforcement.py` **and** its independent duplicate in
  `tests/test_tenant_admin.py`, 5 → **7** in each, with
  `test_get_current_superuser_is_exactly_the_five_tenant_writes` renamed
  `..._is_exactly_the_seven_tenant_routes` in both — and both new routes
  satisfy them by **declaring `Depends(api_deps.get_current_superuser)`**: an
  inlined `if not user.is_superuser` that keeps the pins at five is a
  rejection, not an implementation.
- [ ] **ER-8 — gates green and i18n at parity.** `pytest` ≥ 90 % and
  `ruff check backend` with zero new findings; `npm run build` passes; Vitest
  statements/branches/functions/lines ≥ 80/76/78/80 and ≥ the F5 merge-base
  measurement; `npm run lint` with no new non-test findings; and
  `src/i18n/__tests__/index.test.ts` asserts the `en`/`pt` key sets are
  identical and that `modules.names` carries all **26** module labels in both
  languages.

---

## Out of Scope

Plans/billing driving the switch (`APRAS-40`); a module dependency graph;
per-sub-panel permission gating inside a page; a distinct backend error detail
for a disabled module (§5.4); an audit trail of who toggled what;
`disabled_modules` on `TenantRead`/`TenantCreate`; role-editor decoration for
inactive modules; any change to `ROUTE_PERMISSIONS`, `PERMISSIONS`, the parity
baseline, or the tenant-scoping partition of `tests/test_tenant_models.py`.
