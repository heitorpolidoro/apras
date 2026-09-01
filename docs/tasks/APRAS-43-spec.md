# APRAS-43 — Add a `tenant_admin` capability composed with the existing RBAC layers

Third slice of the multi-tenant chain `APRAS-41 → APRAS-42 → APRAS-43 → APRAS-38`.
APRAS-41 (`6628ffb`) shipped the tenant schema and membership table; APRAS-42 (`e102660`)
shipped request-scoped resolution (`get_current_tenant`) and default-on query isolation
(`app/core/tenant_context.py`). Both slices deliberately left RBAC **global**: an
`ADMINISTRATOR` is an administrator of every tenant, and nobody else is an administrator of
anything.

This slice adds the missing middle: **administrator-level permission restricted to one
tenant**. It is a *capability layered on top of* the existing model, not a replacement —
`UserRole`, `UserType.allowed_menus`, `get_effective_user_type_ids` and the per-lot
`UserLotLink` scoping all keep working exactly as they do, and the new capability composes
with them at two precisely-named points (§4, §5).

It also closes the four security residuals APRAS-42's reviews handed forward (§7), because
each one of them stops being theoretical the moment a non-`ADMINISTRATOR` can reach an
admin endpoint.

---

## 1. Scope

**In scope**

1. `UserTenantLink.is_tenant_admin` + Alembic `0029_add_is_tenant_admin` (§2).
2. Grant/revoke through the membership API: `PATCH /api/v1/tenants/{tenant_id}/members/{user_id}`,
   plus the flag on the create/read membership schemas (§3).
3. The capability helpers and the two new guards in `backend/app/api/deps.py`, and the
   swap of `get_current_active_admin` on **every tenant-scoped route that has it** (§4).
4. Composition with the `allowed_menus` menu gate and with `get_effective_user_type_ids`
   (§5).
5. Tenant-scoping the user directory — `GET /api/v1/users/`, `PATCH /api/v1/users/{id}`,
   `PATCH /api/v1/users/{id}/contact-info` (§6), which is APRAS-42's headline residual.
6. The privilege-escalation guards that scoping a *global* identity table under a
   *tenant-local* administrator makes mandatory (§6.3).
7. The remaining named residuals: the inactive-tenant message oracle, the silently-dropped
   foreign `user_type_ids`, and the role-type re-seed path (§7).
8. Tests: two new modules plus two named, justified edits to pre-existing modules (§8).

**Explicitly NOT in scope** — full list in §10. Headlines: no frontend of any kind
(APRAS-38); no change to the ~20 domain-service role sets (`announcement_service`,
`finance`, `occurrence_service`, …); no change to `Task.visible_to` filtering, to
`assert_can_edit_task`, or to per-lot `UserLotLink` access; tenant_admin cannot manage
memberships or tenants.

---

## 2. The capability lives on the membership, not on `UserRole`

### 2.1 Decision and justification

`is_tenant_admin: bool` is a column on `user_tenant_link`. It is **not** a new `UserRole`
value and **not** a column on `user`. Four reasons, in order of weight:

1. **A user is one global identity in many tenants.** `user.role` is a single global value;
   a síndico who administers condominium A and merely lives in condominium B needs
   *different* answers per tenant. Only a per-membership row can carry that. This is the
   exact shape APRAS-41 anticipated when it gave `UserTenantLink` a surrogate `id` PK
   "because APRAS-43 will add an `is_tenant_admin` column to this row"
   (`app/models/tenant.py` docstring).
2. **A new `UserRole` value would be a schema-wide behaviour change.** `UserRole` is a
   Postgres enum referenced by 54 role comparisons across 22 service modules and by
   `user_type.role` (one seeded `UserType` per role, unique per tenant). Adding
   `TENANT_ADMIN` would silently alter every one of those role sets and require a seventh
   role-linked `UserType` per tenant. The capability is orthogonal to the role, so it must
   not be encoded in the role.
3. **Grant/revoke is already a membership operation.** `POST`/`DELETE
   /api/v1/tenants/{id}/members/...` exists; the flag belongs on the same resource and
   inherits its `ADMINISTRATOR`-only guard for free.
4. **Fail-closed by construction.** The capability is only readable when an acting tenant
   is resolved (§4.1). On a global-scope route — which is every `/api/v1/tenants` route —
   there is no acting tenant, so the capability is structurally absent rather than
   guarded-against. ER-2 falls out of the design instead of out of a check somebody must
   remember.

### 2.2 Model

```python
# backend/app/models/tenant.py — UserTenantLink
is_tenant_admin: bool = Field(
    default=False,
    nullable=False,
    sa_column_kwargs={"server_default": text("false")},
)
```

The `server_default` mirrors what `tenant_id_field()` does for the same reason: the SQLite
schema built by `SQLModel.metadata.create_all()` in the test harness and the Postgres schema
built by Alembic must agree, and no pre-existing writer of `UserTenantLink`
(`app/seed.py`, `POST /auth/signup`, migration `0028`) passes the field.

### 2.3 Migration `0029_add_is_tenant_admin`

* `revision = "0029_add_is_tenant_admin"` (24 chars, under the 32-char limit),
  `down_revision = "0028_add_tenant_and_membership"`. Single head after it.
* `upgrade`: `op.add_column("user_tenant_link", sa.Column("is_tenant_admin", sa.Boolean(),
  nullable=False, server_default=sa.text("false")))`. Every existing membership row —
  including the ones `0028` backfilled for every pre-existing user — becomes a plain
  member, which is the correct and only safe default.
* `downgrade`: `op.drop_column("user_tenant_link", "is_tenant_admin")`. Genuinely
  reversible; no data migration in either direction.
* Verified against the local Postgres on **5436** (`TEST_POSTGRES_URL=…:5436/nexdom`), left
  at head, with `alembic heads` reporting exactly one head.

---

## 3. Granting and revoking

### 3.1 Schemas (`backend/app/schemas/tenant.py`)

```python
class TenantMemberCreate(BaseModel):
    user_id: UUID
    is_tenant_admin: bool = False        # new, optional: link + grant in one call

class TenantMemberUpdate(BaseModel):     # new
    is_tenant_admin: bool

class TenantMemberRead(BaseModel):
    ...
    is_tenant_admin: bool                # new, always present
```

`TenantMemberUpdate` has exactly one field on purpose: this route grants a capability and
must never become a general membership editor.

### 3.2 Route

```
PATCH /api/v1/tenants/{tenant_id}/members/{user_id}   -> 200 TenantMemberRead
```

Mounted on the existing `tenants.router`, which is `GLOBAL_SCOPED`, behind
`deps.get_current_active_admin` exactly like its `POST`/`DELETE` siblings. Consequences,
all asserted in §9:

* `ADMINISTRATOR` → **200**, body carries the new value; `GET /tenants/{id}/members`
  reflects it.
* Any other role → **403**, *including a `tenant_admin` of that very tenant*: on a global
  route the capability is not even readable (§2.1.4).
* Unknown tenant, unknown user, or a user with no membership in that tenant → **404**
  (`TenantMembershipNotFoundError`, already mapped). No new exception type.

`TenantService.set_member_admin(session, tenant_id, user_id, is_tenant_admin)` implements
it, next to `add_member`/`remove_member`, and `_to_member_read` gains the field.
Revocation is `{"is_tenant_admin": false}`; `DELETE .../members/{user_id}` still removes the
membership outright and therefore the capability with it.

---

## 4. The guard layer

### 4.1 Two helpers in `backend/app/api/deps.py`

```python
def is_acting_tenant_admin(user: User, session: Session) -> bool:
    """True when the session's acting tenant grants `user` the capability."""
    tenant_id = tenant_context.acting_tenant_id(session)
    if tenant_id is None:
        return False                      # global / unresolved scope: fail closed
    link = session.exec(
        select(UserTenantLink).where(
            UserTenantLink.user_id == user.id,
            UserTenantLink.tenant_id == tenant_id,
        )
    ).first()
    return bool(link and link.is_tenant_admin)


def has_admin_capability(user: User, session: Session) -> bool:
    return user.role == UserRole.ADMINISTRATOR or is_acting_tenant_admin(user, session)
```

Two deliberate choices:

* **No `DEFAULT_TENANT_ID` fallback**, unlike `get_effective_user_type_ids` (§5.2). That
  function falls back so a *unit-test* session resolves deterministically; this one grants
  power, so an unresolved session must grant nothing. A `Session(engine)` in `app/seed.py`,
  in Alembic or in a unit test therefore never carries the capability.
* **No signature change and no new parameter**: the acting tenant is read from
  `session.info`, exactly as APRAS-42 established for `get_effective_user_type_ids`, so
  every existing call site keeps its shape. `UserTenantLink` is excluded from
  `TENANT_SCOPED_MODELS`, so this query is not itself filtered — verified in
  `app/core/tenant_context.py::_discover_scoped_models`.

### 4.2 Two new dependencies

```python
def get_current_tenant_admin(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    _tenant: Annotated[Tenant, Depends(get_current_tenant)],
) -> User: ...            # 403 "The user doesn't have enough privileges" otherwise

def get_current_tenant_admin_or_manager(...) -> User: ...
```

`get_current_tenant_admin` passes when `has_admin_capability(current_user, session)`;
`get_current_tenant_admin_or_manager` passes when that **or** `role == MANAGER`. Both keep
the existing 403 detail string, so no existing 403 assertion changes.

Declaring `Depends(get_current_tenant)` inside the guard is deliberate rather than relying
on the router-level dependency having run first. **Measured** on a minimal FastAPI app:
router-level dependencies resolve *before* the endpoint's own, and a sub-dependency shared
between the two is called **once** per request (`['tenant', 'guard', 'handler']`,
`tenant_calls == 1`). So the guard is self-sufficient *and* free — and it cannot be mounted
on an unscoped router by accident, because there the acting tenant would resolve twice with
no header semantics behind it. §9's route test forbids that combination outright.

### 4.3 Which routes swap — the whole set, mechanically

Walking `app.routes` on `master` (`e102660`), exactly **11** routes carry an admin guard:

| Route | Guard | tenant-scoped? | After |
|---|---|---|---|
| `DELETE /api/v1/tasks/{task_id}` | admin | yes | `get_current_tenant_admin` |
| `PATCH /api/v1/users/{user_id}` | admin | yes | `get_current_tenant_admin` |
| `POST /api/v1/user-types/` | admin | yes | `get_current_tenant_admin` |
| `PATCH /api/v1/user-types/{user_type_id}` | admin | yes | `get_current_tenant_admin` |
| `DELETE /api/v1/user-types/{user_type_id}` | admin | yes | `get_current_tenant_admin` |
| `DELETE /api/v1/lots/{lot_id}` | admin | yes | `get_current_tenant_admin` |
| `PATCH /api/v1/users/{user_id}/contact-info` | admin-or-manager | yes | `get_current_tenant_admin_or_manager` |
| `POST /api/v1/tenants` | admin | **no** | unchanged |
| `PATCH /api/v1/tenants/{tenant_id}` | admin | **no** | unchanged |
| `POST /api/v1/tenants/{tenant_id}/members` | admin | **no** | unchanged |
| `DELETE /api/v1/tenants/{tenant_id}/members/{user_id}` | admin | **no** | unchanged |

The rule is therefore one sentence a reviewer can check: **`get_current_active_admin`
survives only on the global `/api/v1/tenants` router; every tenant-scoped use of it becomes
the tenant-aware guard.** `get_current_active_admin` itself is *not* modified — a
role-only guard remains available and remains correct for the tenant surface.

The table above is the **`master` snapshot**. This task also *adds* one route on the global
`/api/v1/tenants` router behind the same guard (§3.2), so the **post-task** set of routes
depending on `get_current_active_admin` is **five**, all of them writes on that router:

1. `POST /api/v1/tenants`
2. `PATCH /api/v1/tenants/{tenant_id}`
3. `POST /api/v1/tenants/{tenant_id}/members`
4. `DELETE /api/v1/tenants/{tenant_id}/members/{user_id}`
5. `PATCH /api/v1/tenants/{tenant_id}/members/{user_id}` *(new in this task)*

That enumeration — not the count in the snapshot table — is what the structural test of §9
asserts.

`DELETE /api/v1/tasks/{id}` and `DELETE /api/v1/lots/{id}` are included even though the ERs
only demanded users and user-types: leaving two of the seven behind would make the rule
"some admin routes, decided case by case", which is exactly the property that lets the next
route be forgotten. Both are already tenant-filtered by APRAS-42, so a tenant_admin can only
delete their own tenant's rows (a foreign id is a 404 through the ambient filter, not a
403).

---

## 5. Composition with the two existing permission layers

### 5.1 The `allowed_menus` menu gate

`assert_menu_access` today short-circuits on `role == ADMINISTRATOR`. It becomes:

```python
    if has_admin_capability(current_user, session):
        return
    effective_ids = get_effective_user_type_ids(current_user, session)
    ...                                    # unchanged from here down
```

Exactly the composition the task asks for: **within the acting tenant** a tenant_admin is
exempt from the menu gate precisely as an `ADMINISTRATOR` is; acting anywhere else the
short-circuit does not fire and the ordinary `UserType`/`allowed_menus` path decides. This
is one line, and it is the only place the gate changes — the fine-grained rules the gate
sits in front of (`Task.visible_to` filtering, `assert_can_edit_task`, category write roles)
are untouched, per APRAS-8's own framing of the gate as "an additional coarse gate, not a
replacement".

`AGENTS.md` currently states that `ADMINISTRATOR` is "the only role unconditionally exempt
from the UserType menu gate". That sentence becomes false and is updated in the same commit
(§8.3).

### 5.2 `get_effective_user_type_ids` — scope the explicit types too

APRAS-42 made the *role-linked* lookup tenant-aware but left `explicit_ids = {ut.id for ut
in user.user_types}` alone, and relationship loads are exempt from the ambient filter
(APRAS-42 §4.2). So a dual-tenant user's tenant-B `UserType` rows currently compose into a
tenant-A permission decision. Fix, in the same function, with no extra query:

```python
    tenant_id = tenant_context.acting_tenant_id(session) or DEFAULT_TENANT_ID
    explicit_ids = {ut.id for ut in user.user_types if ut.tenant_id == tenant_id}
```

The `DEFAULT_TENANT_ID` fallback is the one APRAS-42 already established, and every
`UserType` built by a pre-existing test defaults to `DEFAULT_TENANT_ID`, so
`tests/test_role_type_permissions.py` (7 direct calls) and
`tests/test_tenant_no_behaviour_change.py` (2 direct calls) keep passing **unmodified**.
The three production callers (`assert_menu_access`, `assert_manager_can_see_task`,
`TaskService`) and `endpoints/tasks.py:88` all run on a resolved request session and simply
stop seeing foreign types.

### 5.3 What deliberately does **not** compose here

`UserLotLink` per-lot scoping, `assert_manager_can_see_task`, `assert_can_edit_task`, the
category write-role set, and the ~20 role sets in the domain services
(`_STAFF_ROLES`, `_DECIDE_ROLES`, `BOARD_ROLES`, …) are **unchanged**. A tenant_admin whose
role is `RESIDENT` therefore gains the admin *surface* (users, user-types, task/lot
deletion, the menu gate) but not, for example, announcement publication.

This is a scope decision, not an oversight. Each of those sets is a distinct role matrix
with its own test module and its own notion of "staff"; broadening them is dozens of
behaviour changes with no single reviewable rule, and none of them is required for the
capability to exist or to be safe. Recorded as the follow-up
**"extend `tenant_admin` to the domain-service role sets"**, to be captured as its own task.

---

## 6. The user directory becomes tenant-scoped (APRAS-42's headline residual)

### 6.1 Why it must happen in this slice

`GET /api/v1/users/` returns *every* user in the install to any authenticated caller —
names, emails, roles. APRAS-42 recorded it as an accepted residual because scoping it needed
"the membership-aware admin model of APRAS-43". That model is now here, and the residual
is no longer tolerable: a tenant_admin of condominium B could otherwise enumerate
condominium A's residents, and `PATCH /users/{id}` would let them *edit* one.

### 6.2 The visibility rule

A user is visible in the acting tenant `T` when:

* they have a `UserTenantLink` to `T`; **or**
* they have **no** `UserTenantLink` at all and `T` is the default tenant.

The second clause is not a loophole, it is the *same* rule APRAS-42's resolution ladder
already applies in the opposite direction: a caller with zero memberships acts in the
default tenant (`deps._resolve_without_header`). Saying they are also *visible* there is the
only consistent reading, and it is what keeps ~70 pre-existing test modules — whose fixtures
build `User(...)` rows directly with no membership — passing unmodified, together with the
production reality that migration `0028` gave every real user exactly one membership.

New `backend/app/services/user_service.py` (there is no user service today; the endpoints
are thin and this logic is shared by three routes):

```python
class UserService:
    @staticmethod
    def visible_users_statement(tenant_id: UUID):
        linked = select(UserTenantLink.user_id).where(UserTenantLink.tenant_id == tenant_id)
        statement = select(User)
        if tenant_id == DEFAULT_TENANT_ID:
            return statement.where(
                or_(User.id.in_(linked), User.id.not_in(select(UserTenantLink.user_id)))
            )
        return statement.where(User.id.in_(linked))

    @classmethod
    def get_visible_user(cls, session, user_id, tenant_id) -> User | None: ...
    @staticmethod
    def membership_tenant_ids(session, user_id) -> set[UUID]: ...
```

**Measured** against the real models on sqlite with four users (no link / A only / B only /
both): tenant A yields `[orphan, ua, uab]`, tenant B yields `[uab, ub]`. `User` carries no
`tenant_id`, so the ambient filter neither helps nor interferes here.

Applied to all three user routes:

| Route | Change |
|---|---|
| `GET /api/v1/users/` | statement becomes `visible_users_statement(acting_tenant.id)`; the `is_active` filter still composes |
| `PATCH /api/v1/users/{id}` | `session.get(User, …)` → `get_visible_user(...)`; **404** when not visible |
| `PATCH /api/v1/users/{id}/contact-info` | same |

**The filter is uniform for every caller, `ADMINISTRATOR` included, and it is the ONLY rule
in this task that applies to an administrator.** There is no role-conditional branch in
`visible_users_statement` or `get_visible_user`, and none in the three routes' lookup step.
Stated as the single rule an implementer follows:

> On `GET /api/v1/users/`, `PATCH /api/v1/users/{id}` and
> `PATCH /api/v1/users/{id}/contact-info`, the target set is the users visible in the acting
> tenant (§6.2) — for every role. A user not visible in the acting tenant is **404**, and a
> global `ADMINISTRATOR` is **not** exempt: acting in tenant A, an administrator gets 404 for
> a B-only user exactly as a tenant_admin of A does.

This is not a restriction of administrator power, it is a *relocation* of it: the
administrator reaches any tenant's user by sending that tenant's `X-Tenant-Id`, which is
precisely the global-vision mechanism APRAS-42 established — "global vision is a property of
*sending* `X-Tenant-Id`, not of the role" — and `_resolve_from_header` already lets an
`ADMINISTRATOR` act in **any** active tenant without a membership (verified in
`app/api/deps.py::_resolve_from_header`, where `is_admin` short-circuits the membership
check). An administrator with no header acts in their single membership's tenant, or in the
default tenant when they have none; to act elsewhere they send the header. A role-conditional
filter would instead give the directory two behaviours to reason about and would keep exactly
the leak this section exists to close for the most powerful caller.

The escalation rules of §6.3 are the *complement* of this: they are checked **only** for a
caller that is not a global `ADMINISTRATOR`, and they never fire for one.

Additionally, `UserRead.user_types` is a relationship load and therefore filter-exempt, so
the three routes above serialise through a small helper that keeps only the acting tenant's
`UserType` rows in the response body. `GET /api/v1/auth/me` is a global route returning the
caller's *own* identity and is deliberately left alone (§10).

### 6.3 Privilege-escalation guards `PATCH /api/v1/users/{id}` now needs

`user.role`, `user.is_active` and `user.cpf` are **global** fields. Handing that endpoint to
a tenant-local administrator without guards would let a tenant_admin of condominium B mint a
global `ADMINISTRATOR`, i.e. compromise every condominium.

The endpoint therefore runs the checks below **in this order**, and each states exactly who
it applies to. There is deliberately no second visibility rule here: rule 0 *is* §6.2's rule,
restated only so the ordering is unambiguous.

0. **Every caller, `ADMINISTRATOR` included** — target not visible in the acting tenant →
   **404** (§6.2). This is the lookup itself (`get_visible_user`), not an added check.
1. **Only a caller that is not a global `ADMINISTRATOR`** —
   `user_in.role == UserRole.ADMINISTRATOR` → **403** `"Tenant administrators cannot grant
   the ADMINISTRATOR role"`.
2. **Only a caller that is not a global `ADMINISTRATOR`** —
   `db_user.role == UserRole.ADMINISTRATOR` → **403** `"Tenant administrators cannot modify
   an administrator"`.
3. **Only a caller that is not a global `ADMINISTRATOR`** — the target holds a membership in
   any tenant other than the acting one → **403** `"This user belongs to another tenant"` —
   because every writable field on this route is global, so editing a shared user would reach
   across the boundary.

So for a global `ADMINISTRATOR`, rules 1–3 are skipped entirely and rule 0 is the whole of
this task's new behaviour: acting in tenant `T`, they may `PATCH` any user visible in `T`
(200), including one whose role is or becomes `ADMINISTRATOR` and one who holds memberships
in several tenants; and they get **404** — not 200 — for a user with no membership in `T`,
reaching that user instead by sending `X-Tenant-Id` for a tenant the user does belong to.

`PATCH /api/v1/users/{id}/contact-info` follows the same split: rule 0 applies to every
caller (`get_visible_user`, 404 when not visible), and it gains none of rules 1–3, since its
schema exposes no `role`, no `is_active` and no `user_type_ids`.

Rule 3 is intentionally blunt (it also blocks a harmless `user_type_ids` change on a shared
user). Multi-tenant users are rare, the failure mode is a clear 403 rather than a silent
cross-tenant write, and per-tenant roles are not in this chain. Recorded as a follow-up.

The existing self-protection checks (an administrator cannot deactivate themselves or change
their own role) are untouched and apply to every caller.

---

## 7. The remaining named residuals from APRAS-42

| Residual | Decision |
|---|---|
| **Global user directory** | **Resolved** — §6. |
| **`user.user_types` composes across tenants** | **Resolved** — §5.2. |
| **Inactive-tenant 403 is an existence oracle** | **Resolved.** In `deps._resolve_from_header`, the membership check moves *before* the `is_active` check for non-administrators: a non-member gets `403 "Not a member of the requested tenant"` whether or not the tenant is active, so the two 403 messages stop distinguishing "inactive tenant exists" from "no such tenant". A member (and any `ADMINISTRATOR`) of an inactive tenant still gets `403 "Tenant is inactive"` — `tests/test_tenant_isolation.py::test_inactive_tenant_is_403_even_for_an_administrator` uses an `ADMINISTRATOR` and passes **unmodified** (verified). |
| **`PATCH /users/{id}` silently drops foreign `user_type_ids`** | **Resolved as 422.** When `user_type_ids` is supplied, every id must resolve to a `UserType` in the acting tenant; any that does not → **422** `"Unknown user_type_ids: …"`. A silent 200 that discards half the payload is exactly the shape that hides a cross-tenant mistake. Additionally, the assignment now *preserves* the target's `UserType` rows from other tenants (`keep = [ut for ut in db_user.user_types if ut.tenant_id != acting]`) instead of wiping them — replacing the whole collection while acting in one tenant was itself a cross-tenant write. No pre-existing test sends a `user_type_ids` value on this route (verified: the only hit is `test_user_contact_info.py`, on the *contact-info* schema, which has no such field). |
| **Tenants created before APRAS-42 have no role-linked `UserType` rows** | **Resolved without a data migration.** The seeding block inside `TenantService.create_tenant` is extracted into an idempotent `TenantService.ensure_role_types(session, tenant_id)` that inserts only the missing `(tenant, role)` rows, and `app/seed.py` calls it for **every** tenant it finds. `python -m app.seed` is therefore the documented dev recovery path. Deliberately *not* a backfill inside `0029`: no production install can be in that state (the only tenant in production is the default one, whose role types migration `0018`/`0020` seeded), and an `INSERT` into `user_type` for every tenant would add an irreversible data step to an otherwise perfectly reversible migration. |

---

## 8. Files touched

### 8.1 Application

* `app/models/tenant.py` — `is_tenant_admin` column + docstring hand-off note updated.
* `alembic/versions/0029_add_is_tenant_admin.py` — new.
* `app/schemas/tenant.py` — `TenantMemberUpdate`, two field additions.
* `app/services/tenant_service.py` — `set_member_admin`, `ensure_role_types`,
  `_to_member_read`.
* `app/api/v1/endpoints/tenants.py` — the `PATCH …/members/{user_id}` route.
* `app/api/deps.py` — `is_acting_tenant_admin`, `has_admin_capability`,
  `get_current_tenant_admin`, `get_current_tenant_admin_or_manager`; `assert_menu_access`
  short-circuit; `get_effective_user_type_ids` explicit-type filter; `_resolve_from_header`
  ordering.
* `app/services/user_service.py` — new.
* `app/api/v1/endpoints/users.py` — visibility, escalation guards, 422, response filtering.
* `app/api/v1/endpoints/user_types.py`, `tasks.py`, `lots.py` — guard swap only.
* `app/seed.py` — `ensure_role_types` for every tenant.

### 8.2 Tests

**New**

* `backend/tests/test_tenant_admin.py` — grant/revoke API, the capability matrix over the 7
  swapped routes, the menu-gate composition, the `/tenants` 403s, the route-level structural
  assertion, and `is_acting_tenant_admin` unit tests (unresolved session → `False`).
* `backend/tests/test_user_directory_scope.py` — §6 in full: listing, by-id 404, the
  escalation guards, the 422, the preserved foreign `UserType` links, and the response-body
  `user_types` filtering.

Both reuse APRAS-42's `tenant_client` / `raw_session` / `tenant_b` conftest fixtures, whose
per-request-session contract is what makes the by-id 404s real. **`conftest.py` needs no
change** — the new fixtures (a tenant_admin user, a dual-membership user) are local to the
two new modules.

**Pre-existing modules that legitimately change — exactly two, both mechanical**

1. `backend/tests/test_tenant_route_scope.py` — one entry added to `GLOBAL_ROUTES`:
   `("PATCH", "/api/v1/tenants/{tenant_id}/members/{user_id}")`. The module's own
   "no stale allowlist entries" assertion is what forces this to be deliberate.
2. `backend/tests/test_migrations_postgres.py` — `test_downgrade_removes_tenant_schema`
   currently does `_run_alembic("downgrade", "-1")` and asserts it lands on
   `0027_add_purchase_quotation`, then re-upgrades and asserts head is
   `0028_add_tenant_and_membership`. With `0029` on top, `-1` undoes the wrong migration.
   Change the downgrade target to the explicit `"0027_add_purchase_quotation"` (the module
   already flags `-1` as drift-prone in its own comment) and the landing assertion to
   `"0029_add_is_tenant_admin"`; the body of the test is otherwise untouched. A new case in
   the same module asserts `user_tenant_link.is_tenant_admin` is `boolean NOT NULL DEFAULT
   false` after `upgrade head` and absent after downgrading to `0028`.

No other pre-existing test module may be edited. If one appears to need editing — in
particular any of `test_user_admin.py`, `test_missing_coverage.py`,
`test_user_contact_info.py`, `test_tenants.py`, `test_tenants_rbac.py`,
`test_role_type_permissions.py`, `test_tenant_no_behaviour_change.py`,
`test_tenant_isolation.py` — the visibility rule of §6.2 or the fallback of §5.2 is wrong;
fix the rule, not the test.

### 8.3 Docs

`AGENTS.md`: a **Tenant administrator** paragraph under Domain Concepts, and the correction
of "the only role unconditionally exempt from the UserType menu gate" in the `UserRole`
table.

---

## 9. Expected Results

- [ ] `PATCH /api/v1/tenants/{tenant_id}/members/{user_id}` with `{"is_tenant_admin": true}`
      returns **200** with `is_tenant_admin: true` to an `ADMINISTRATOR`, the same value
      appears for that user in `GET /api/v1/tenants/{tenant_id}/members`, and
      `{"is_tenant_admin": false}` returns **200** with `is_tenant_admin: false`; the route
      returns **404** for an unknown tenant, an unknown user, or a user with no membership
      in that tenant.
- [ ] The same `PATCH` returns **403** to every non-`ADMINISTRATOR` caller, *including a
      user holding `is_tenant_admin` on that very tenant*, and `POST /api/v1/tenants`,
      `PATCH /api/v1/tenants/{id}`, `POST /api/v1/tenants/{id}/members` and
      `DELETE /api/v1/tenants/{id}/members/{user_id}` also return **403** to a
      `tenant_admin`.
- [ ] A non-`ADMINISTRATOR` user (role `RESIDENT`) holding `is_tenant_admin` on tenant A and
      acting in A passes every admin-gated tenant-scoped route: `GET /api/v1/users/` **200**,
      `PATCH /api/v1/users/{id_of_an_A_user}` **200**,
      `PATCH /api/v1/users/{id_of_an_A_user}/contact-info` **200**,
      `POST /api/v1/user-types/` **201**, `PATCH /api/v1/user-types/{A_type_id}` **200**,
      `DELETE /api/v1/user-types/{A_non_role_type_id}` **204**,
      `DELETE /api/v1/tasks/{A_task_id}` **204**, `DELETE /api/v1/lots/{A_lot_id}` **204**.
- [ ] The same user acting in a tenant where they are a plain member (`X-Tenant-Id: B`)
      gets **403** on `PATCH /api/v1/users/{id}`, `PATCH /api/v1/users/{id}/contact-info`,
      `POST /api/v1/user-types/`, `PATCH`/`DELETE /api/v1/user-types/{id}`,
      `DELETE /api/v1/tasks/{id}` and `DELETE /api/v1/lots/{id}`; and a plain member of A
      with no grant gets **403** on those same routes while acting in A.
- [ ] Acting in tenant A, that tenant_admin never receives tenant-B data:
      `PATCH /api/v1/users/{id_of_a_user_whose_only_membership_is_B}` → **404**,
      `PATCH /api/v1/user-types/{B_type_id}` → **404**, and `GET /api/v1/users/` returns
      exactly the users visible in A (linked to A, or link-less when A is the default
      tenant) and no B-only user.
- [ ] `GET /api/v1/users/` applies the same membership filter to an `ADMINISTRATOR`: acting
      in the default tenant it excludes a B-only user, and the same administrator sending
      `X-Tenant-Id: <B>` receives that user and **200**. Every `UserRead.user_types` array
      returned by `GET /api/v1/users/`, `PATCH /api/v1/users/{id}` and
      `PATCH /api/v1/users/{id}/contact-info` contains only `UserType` rows of the acting
      tenant.
- [ ] A tenant_admin of tenant A, **acting in A**, is refused every privilege escalation on
      `PATCH /api/v1/users/{id}` against targets that are visible in A: body
      `{"role": "ADMINISTRATOR"}` → **403**; a target whose role is `ADMINISTRATOR` →
      **403**; a target that also holds a membership in another tenant → **403**.
- [ ] An `ADMINISTRATOR` sending `X-Tenant-Id: <A>` — so that each target is visible in the
      acting tenant — performs those same three `PATCH /api/v1/users/{id}` requests and gets
      **200** on all three (the `ADMINISTRATOR`-role target being a *second* administrator,
      not the caller, so the pre-existing self-protection **400**s stay out of the way and
      remain unchanged): the escalation rules never fire for a global `ADMINISTRATOR`.
      `backend/tests/test_user_admin.py` passes unmodified.
- [ ] The visibility 404 applies to a global `ADMINISTRATOR` too: an `ADMINISTRATOR` sending
      `X-Tenant-Id: <A>` gets **404** on both `PATCH /api/v1/users/{id_of_a_B_only_user}` and
      `PATCH /api/v1/users/{id_of_a_B_only_user}/contact-info`, and the same administrator
      sending `X-Tenant-Id: <B>` gets **200** on both.
- [ ] `PATCH /api/v1/users/{id}` with a `user_type_ids` entry that does not exist in the
      acting tenant returns **422** (it returns **200**, silently dropping it, on `master`);
      with valid acting-tenant ids it returns **200**, and a `UserType` link the target held
      in another tenant is still present in the database afterwards.
- [ ] Within their tenant a tenant_admin is exempt from the `allowed_menus` gate exactly as
      an `ADMINISTRATOR` is: a `RESIDENT` tenant_admin whose effective `UserType`s contain
      no `"tasks"` menu gets **200** from `GET /api/v1/tasks/` acting in that tenant, and
      **403** with detail `"Not enough privileges to access tasks"` acting in a tenant where
      they hold no grant.
- [ ] `get_effective_user_type_ids` returns only the acting tenant's `UserType` ids for a
      user holding explicit types in two tenants (role-linked and explicit alike), and
      `is_acting_tenant_admin` returns `False` on a session with no acting tenant even for a
      user holding the flag; `backend/tests/test_role_type_permissions.py` and
      `backend/tests/test_tenant_no_behaviour_change.py` pass **unmodified**.
- [ ] A non-member non-`ADMINISTRATOR` sending `X-Tenant-Id` for an **inactive** tenant gets
      **403** with detail `"Not a member of the requested tenant"` — byte-identical to the
      answer for an active tenant they are not a member of — while a member of that inactive
      tenant still gets **403** `"Tenant is inactive"`, and
      `tests/test_tenant_isolation.py` passes **unmodified**.
- [ ] A test walking `app.routes` asserts that **no** route depending on
      `get_current_tenant` also depends on `get_current_active_admin` or
      `get_current_admin_or_manager`, and that the routes still depending on
      `get_current_active_admin` are exactly these **five** writes on the global
      `/api/v1/tenants` router and no others: `POST /api/v1/tenants`,
      `PATCH /api/v1/tenants/{tenant_id}`, `POST /api/v1/tenants/{tenant_id}/members`,
      `DELETE /api/v1/tenants/{tenant_id}/members/{user_id}` and
      `PATCH /api/v1/tenants/{tenant_id}/members/{user_id}`.
- [ ] `TenantService.ensure_role_types` is idempotent (a second call on the same tenant
      inserts nothing) and fills a tenant that has none; `POST /api/v1/tenants` still seeds
      one role-linked `UserType` per `UserRole` in the new tenant, and `python -m app.seed`
      runs clean against the local Postgres on port 5436 and leaves every tenant with a
      complete role-type set.
- [ ] Alembic: exactly one head, `0029_add_is_tenant_admin`; after `upgrade head`
      `user_tenant_link.is_tenant_admin` is `boolean NOT NULL DEFAULT false` and every row
      backfilled by `0028` reads `false`; after downgrading to `0028` the column is gone;
      `backend/tests/test_migrations_postgres.py` passes against Postgres on 5436 with only
      the two named assertion changes in `test_downgrade_removes_tenant_schema`.
- [ ] `uv run pytest` is green with coverage ≥ 90 % on `--cov=app` (measured baseline on
      `master` @ `e102660`: **995 passed, 17 skipped, 98.21 % coverage, 445 s**), `ruff check` is clean,
      and the only pre-existing test modules modified are
      `backend/tests/test_tenant_route_scope.py` (one allowlist entry) and
      `backend/tests/test_migrations_postgres.py` (§8.2). The passing count is at least the
      pre-task baseline plus the new cases — a decrease means an existing test was dropped
      or skipped (baseline: 995 passed / 17 skipped).
- [ ] Nothing under `frontend/` is modified; `npm run build` and `npm run test:coverage`
      (75 % gate) still pass and `npm run lint` reports no new findings.

---

## 10. Out of Scope / Non-goals

- **Frontend: nothing at all.** No tenant switcher, no admin-menu change, no i18n keys —
  APRAS-38. It reads the flag from `GET /api/v1/tenants/{id}/members`, which a member may
  already call for their own tenant; if it wants a cheaper per-caller signal, adding one to
  `/auth/me` or `TenantRead` is a one-field follow-up, deliberately not pre-built here.
- **No new `UserRole` value**, no per-tenant role, no per-tenant `is_active` for a user.
- **Domain-service role sets unchanged** (§5.3) — announcements, finance, occurrences,
  documents, voting, packages, reservations, assets, purchases, access control, residents,
  visitors. A tenant_admin does not inherit `DIRECTOR`-level powers there.
- **Per-lot `UserLotLink` scoping, `Task.visible_to` filtering and `assert_can_edit_task`
  unchanged.** A tenant_admin who is a `MANAGER` still sees only the tasks their effective
  `UserType`s allow.
- **tenant_admin cannot manage tenants or memberships** — not `POST /tenants`, not
  `PATCH /tenants/{id}`, not add/remove/grant members. Delegating membership management to a
  tenant_admin is a deliberate follow-up, not a silent extension.
- **`GET /api/v1/auth/me` stays global and unfiltered**: it returns the caller's own
  identity on a route with no acting tenant, so there is no tenant to filter its
  `user_types` by. Named residual, carried to APRAS-38.
- **No cross-tenant user creation or invite flow.** `POST /auth/signup` still links to the
  default tenant only (APRAS-42 §8.1).
- No change to `get_current_active_admin` itself, to `get_current_user`, to the JWT, or to
  rate limiting; no tenant-aware caching; no audit log of grant/revoke.
