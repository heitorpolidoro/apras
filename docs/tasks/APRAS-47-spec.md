# APRAS-47 — IAM F3: `is_superuser` global, `is_tenant_admin` as every permission of the tenant

Slice 3 of the IAM chain (F1 `APRAS-45` → F2 `APRAS-46` → **F3 this** →
F4 `APRAS-48` → F5 `APRAS-49`).

F1 built the vocabulary. F2 swapped enforcement onto permissions and left
**exactly seven** `user.role == ADMINISTRATOR`-shaped reads alive, each marked
`F3` in its allowlist. **This slice converts all seven**: the ADMINISTRATOR
*role* stops being the source of global power, a real `user.is_superuser`
column takes over, and `is_tenant_admin` stops being a hand-listed bundle of
seven permissions and becomes *every* permission — inside the granting tenant
only.

It is the last slice before the role enum can die (F5). After it, the only
actor-role reads left in `backend/app/` are object/visibility rules and the
resolver plumbing — **none** of them is a global-power decision.

---

## 0. Preconditions, and how to read this spec against a moving tree

**Contracts, not files.** This spec was written while `APRAS-46` was being
implemented concurrently in the same worktree. It is specified against two
contracts:

1. **F1's landed code** at `02c2025` — `app/core/permissions.py`
   (`PERMISSIONS`, `ROUTE_PERMISSIONS`, `UNGUARDED_ROUTES`,
   `LEGACY_ROLE_PERMISSIONS`), `deps.get_effective_permissions`,
   `deps.get_effective_user_type_ids`, migration `0030_add_user_type_permissions`.
2. **F2's approved spec** `docs/tasks/APRAS-46-spec.md`. Its post-conditions
   are this slice's preconditions:
   * `deps.has_permission` / `deps.require_permission` (`PermissionRequired`);
   * `deps.get_current_tenant_admin` and `deps.get_current_tenant_admin_or_manager`
     **deleted**; `deps.get_current_active_admin` and
     `deps.get_current_admin_or_manager` **surviving, untouched**;
   * `ADMIN_GAP_PERMISSIONS` and `SCOPE_PERMISSIONS` in
     `app/core/permissions.py`; `TENANT_ADMIN_PERMISSIONS` there too, carrying
     the comment `TRANSITIONAL (IAM F2 -> F3)`;
   * `get_effective_permissions` containing the narrow bridge
     `if is_acting_tenant_admin(user, session): permissions |= TENANT_ADMIN_PERMISSIONS`;
   * `user_type_service.assert_can_grant`; `permissions` on the three
     `UserType` schemas;
   * `tests/matrix_world.py`, `tests/tools/record_parity_baseline.py`,
     `tests/data/parity_matrix_baseline.json`,
     `tests/test_permission_parity_matrix.py`,
     `tests/test_permission_enforcement.py` (with `ROLE_READS_COMPARE`,
     `ROLE_READS_NON_COMPARE`, `RULE_C_BASELINE`, `RULE_N_BASELINE`,
     `CONVERTED_COMPARE`), `tests/test_permission_escalation.py`;
   * 15 surviving Rule-C reads, 7 of them marked `F3`.

**If F2 landed a name differently** — a renamed constant, the
`TENANT_ADMIN_PERMISSIONS` pin test in `test_permission_registry.py` rather
than `test_effective_permissions.py`, a differently-named allowlist — apply
the edit **by role, not by name**, and record the deviation in the PR body.
Every edit this spec asks for is described by what it does, so a name change
is a mechanical translation, never a licence to skip the edit.

**Dependency.** `APRAS-46` must be merged first. This task's merge base is
F2's commit; every "measured" number below is measured **there**, in a clean
worktree (`git worktree add /tmp/apras-mb <F2_SHA>`), and quoted in the PR
body.

---

## 1. Scope

**In scope**

1. `User.is_superuser` — the column, migration `0031`, and the transitional
   creation-time default that keeps the column and the enum in lockstep until
   F5 (§3).
2. `get_effective_permissions`: `is_superuser` ⇒ the **whole catalogue**, in
   any tenant and with no tenant at all; `is_tenant_admin` ⇒ the whole
   catalogue **in the granting tenant only** (§4). `TENANT_ADMIN_PERMISSIONS`
   is deleted.
3. The conversion of **all seven** F3-marked Rule-C survivors (§5), the
   resulting allowlists, and the exact edits to F2's walker tests (§5.3).
4. The five global `/api/v1/tenants` writes gated on `is_superuser`
   (`get_current_active_admin` → `get_current_superuser`), and the deletion of
   the now-dead `get_current_admin_or_manager` (§5.1).
5. `SUPERUSER_ONLY_PERMISSIONS` — the four tenant-administration permission
   strings that may never enter a group, so "superuser is not grantable via
   the groups API" is mechanical rather than incidental (§6).
6. The escalation rules of `endpoints/users.py::update_user` re-expressed in
   terms of `is_superuser`, plus the role-change mirror that keeps the column
   truthful (§7).
7. `tests/test_superuser.py` (new) and the named edits to five pre-existing
   test modules (§9).
8. The `AGENTS.md` "Tenant administrator" section, amended in place so the
   repository's own architecture doc states what the capability now means and
   that a global superuser column exists (§12).

**Explicitly NOT in scope**

* **No frontend.** `git status --short -- frontend/` is empty. §8 proves the
  frontend needs nothing, rather than deferring the question.
* **No `/auth/me` change, no new field on `UserRead`.** §8.
* **No re-recording of the parity matrix.** `tests/matrix_world.py`,
  `tests/tools/**` and `tests/data/parity_matrix_baseline.json` are
  **byte-identical** to the merge base. §10 walks the one cell that could have
  moved and shows it does not.
* **No is_superuser grant/revoke API and no UI.** `UserUpdate` gains **no**
  `is_superuser` field. The only writers of the column are migration `0031`,
  the creation-time default and the role-change mirror of §7.3. A first-class
  grant surface belongs to F4/F5.
* **No dropping of `UserRole`**, of `LEGACY_ROLE_PERMISSIONS`, of
  `allowed_menus`, of `Task.visible_to`, of per-lot linkage or of any
  ownership rule. F5 owns all of them.
* **No change to `user_tenant_link.is_tenant_admin`** — not the column, not
  its migration `0029`, not its grant route. Only what the *capability means*
  changes.
* **No new endpoint, no new route, no change to `ROUTE_PERMISSIONS`,
  `UNGUARDED_ROUTES` or the route count (190 / 180 / 10).**
* **No tightening.** Every caller that passes a gate at the merge base still
  passes it, with the two deliberate, named exceptions of §4.3 (both of which
  are consequences of *widening* the tenant_admin capability, not of removing
  anything).

---

## 2. Files touched

| File | Change |
|---|---|
| `backend/alembic/versions/0031_add_user_is_superuser.py` | **new** — the column + the ADMINISTRATOR conversion (§3.2) |
| `backend/app/models/user.py` | `is_superuser` column; the transitional creation-time default (§3.3) |
| `backend/app/core/permissions.py` | `TENANT_ADMIN_PERMISSIONS` **deleted**; `SUPERUSER_ONLY_PERMISSIONS` added (§6.1) |
| `backend/app/api/deps.py` | `get_current_active_admin` → `get_current_superuser` reading the column; `get_current_admin_or_manager` **deleted**; `has_admin_capability`, `_resolve_from_header`, `get_effective_permissions` (§4, §5.1) |
| `backend/app/api/v1/endpoints/tenants.py` | the five `Depends(api_deps.get_current_active_admin)` become `Depends(api_deps.get_current_superuser)`; the module docstring updated |
| `backend/app/api/v1/endpoints/users.py` | `update_user` escalation rules 1–3 and the role-change mirror (§7) |
| `backend/app/services/tenant_service.py` | `list_tenants`, `get_visible_tenant` (§5.1) |
| `backend/app/services/user_type_service.py` | `assert_can_grant` rejects `SUPERUSER_ONLY_PERMISSIONS` (§6.2) |
| `backend/tests/test_superuser.py` | **new** — the slice's own module (§9.1) |
| `backend/tests/test_migrations_postgres.py` | **edited** — 3 head-pin literals + additive `0031` section (§9.2) |
| `backend/tests/test_permission_enforcement.py` | **edited (F2)** — allowlists, arithmetic, guard names, declarative-scope pins (§5.3) |
| `backend/tests/test_permission_escalation.py` | **edited (F2)** — the author of four cases, and case 5 (§9.2) |
| `backend/tests/test_effective_permissions.py` | **edited (F1/F2)** — the bridge case widened (§9.2) |
| `backend/tests/test_tenant_admin.py` | **edited** — three structural tests naming the two renamed/deleted guards (§9.2) |
| `AGENTS.md` | **edited** — the "Tenant administrator" section, amended to the widened capability and the new column (§12) |

`app/seed.py` is **not** edited: it builds its administrator with
`User(role=UserRole.ADMINISTRATOR, ...)`, so §3.3's default applies. No file
under `frontend/`. No file under `tests/tools/`, `tests/matrix_world.py` or
`tests/data/`.

---

## 3. The column

### 3.1 Model

```python
# app/models/user.py, on User
# Global, install-wide administrator. The counterpart of
# `user_tenant_link.is_tenant_admin`, which is the same power scoped to one
# tenant (APRAS-43). `server_default` mirrors `is_tenant_admin`'s, and for the
# same reason: the SQLite schema `SQLModel.metadata.create_all()` builds in
# `backend/tests/conftest.py` and the Postgres schema Alembic builds must
# agree, and no pre-existing writer of this row passes the field.
is_superuser: bool = Field(
    default=False,
    nullable=False,
    sa_column_kwargs={"server_default": text("false")},
)
```

Placed on `User` (global identity), **not** on `user_tenant_link`: that is the
whole distinction between the two flags, and it is what makes "in any tenant"
expressible at all.

### 3.2 Migration `0031_add_user_is_superuser`

* `revision = "0031_add_user_is_superuser"` — **26 characters**
  (`python -c 'print(len("0031_add_user_is_superuser"))'` → `26`), inside the
  `alembic_version VARCHAR(32)` limit that `903a4a6` was cut to fix. The
  invariant is `<= 32`; the count is quoted because the limit has bitten this
  repo before. (`0029_add_is_tenant_admin` is the 24-character one.)
* `down_revision = "0030_add_user_type_permissions"` — the current head.
  `alembic heads` reports the single head `0031_add_user_is_superuser`
  afterwards.
* `upgrade()`:

  ```python
  op.add_column(
      "user",
      sa.Column("is_superuser", sa.Boolean(), nullable=False,
                server_default=sa.text("false")),
  )
  # Every administrator that exists when this migration runs *is* the global
  # superuser today: `get_current_active_admin`, `_resolve_from_header`,
  # `TenantService.list_tenants` and `get_visible_tenant` all read
  # `role == ADMINISTRATOR` at 0030. Converting them is what makes the swap
  # in `deps` a no-op for existing installs.
  op.execute("""UPDATE "user" SET is_superuser = true """
             """WHERE role::text = 'ADMINISTRATOR'""")
  ```

  `"user"` is quoted (reserved word in Postgres) and `role` is cast with
  `::text` (it is the native `userrole` enum, extended by `0012`/`0020`).
* `downgrade()`: `op.drop_column("user", "is_superuser")`. Exactly reversible
  in the same sense as `0029` and `0030`: the column and the data it carries
  go together, so there is nothing to restore into and no asymmetry.
* **`user_tenant_link.is_tenant_admin` is not touched** — not added, not
  altered, not dropped. Asserted (§9.2).
* Nothing else is seeded, updated or deleted.

### 3.3 The creation-time default — the transitional bridge, stated openly

The sqlite suite builds its schema with `SQLModel.metadata.create_all()` and
never runs a migration, so `0031`'s conversion cannot reach it. Without a
code-side rule, the **19 `role=UserRole.ADMINISTRATOR` user constructions
across 8 pre-existing test modules** (`grep -rn 'role=UserRole.ADMINISTRATOR'
backend/tests/*.py` → 19 hits in `conftest.py`, `test_menu_access.py`,
`test_role_type_permissions.py`, `test_task_visible_to_multi_target.py`,
`test_tasks_coverage.py`, `test_tasks_rbac.py`, `test_tenant_isolation.py`,
`test_tenant_no_behaviour_change.py`; re-measure at the merge base and quote
it in the PR body) would produce non-superusers and the whole suite would go
red for a reason that has nothing to do with the change under test. More importantly, the same gap would exist in production for every
administrator created *after* `0031`.

```python
# app/models/user.py, on User
def __init__(self, **data: Any) -> None:
    """TRANSITIONAL (IAM F3 -> F5).

    While `User.role` still exists, creating a user with role ADMINISTRATOR
    defaults `is_superuser` to True — exactly the rule migration 0031 applies
    to the rows that predate it, so the two paths agree and the column is
    complete. An explicit `is_superuser=` always wins, and SQLAlchemy does
    **not** call `__init__` when loading a row, so the column stays the single
    source of truth for every reader: a row stored with role ADMINISTRATOR and
    `is_superuser=False` reads back as a non-superuser. F5 deletes this
    together with the enum.
    """
    if "is_superuser" not in data and data.get("role") == UserRole.ADMINISTRATOR:
        data["is_superuser"] = True
    super().__init__(**data)
```

Why `__init__` and not a `before_insert` mapper event: `__init__` also covers
users that are built in memory and never flushed (unit-level calls into
`deps`), and it is not reached on DB load, which is what keeps the negative
case of ER-3 (`role=ADMINISTRATOR, is_superuser=False` ⇒ 403) constructible.
`UserRole` is a `StrEnum`, so the comparison holds for the raw string too.

**This is a `UserRole.ADMINISTRATOR` literal inside `app/models/`, the one
directory F2's AST walker does not visit.** It is not smuggled: §5.3 adds a
test that walks `app/models/` and asserts this is the **only**
`UserRole.ADMINISTRATOR` reference there, in exactly this function. The
walker's scope exclusion stops being load-bearing.

**Not mirrored on update.** A `before_update`-style mirror would make
`is_superuser` a pure function of `role` and would make the negative case
above unwritable. Role *changes* are handled explicitly, in one place, in §7.3.

---

## 4. `get_effective_permissions` — the two short-circuits

```python
def get_effective_permissions(user: User, session: Session) -> frozenset[str]:
    # A superuser holds every permission there is, in every tenant, and with
    # no acting tenant at all: the flag is global, so it is answered before
    # any tenant is resolved.
    if user.is_superuser:
        return PERMISSIONS
    granted = set(LEGACY_ROLE_PERMISSIONS.get(user.role, frozenset()))
    ...role bundles, unchanged...
    # Administrator-level power inside one tenant (APRAS-43): every
    # permission, but only while acting in the tenant that granted it.
    # `is_acting_tenant_admin` has no DEFAULT_TENANT_ID fallback, so a global
    # route, `app/seed.py`, Alembic and a bare unit-test Session all grant
    # nothing.
    if is_acting_tenant_admin(user, session):
        return PERMISSIONS
    return frozenset(granted)
```

### 4.1 Why `PERMISSIONS` and not `PERMISSIONS - ADMIN_GAP_PERMISSIONS`

F1 built `test_admin_gap_list_is_exact` precisely to force this slice to
decide the gap explicitly. The decision is: **a superuser holds the whole
catalogue, `packages:my_lots_read` included.**

* `ADMIN_GAP_PERMISSIONS` is `{"packages:my_lots_read"}` and it exists because
  `PackageService.get_my_lots` refuses gatekeeper roles with
  *"Use /packages/queue para ver encomendas de todos os lotes."* — a **routing**
  message, not a privilege. Denying that string to an administrator protects
  nothing.
* It costs **zero** matrix cells: `get_my_lots` tests
  `has_permission("packages:queue_read")` **first**, and `packages:queue_read`
  is `{A, D, M, P}`, so the ADMINISTRATOR cell still refuses with the same
  message and the same 403 (§10).
* It has exactly one observable consequence: a superuser may now put
  `packages:my_lots_read` into a group. That is correct — a superuser should
  be able to author any group — and it is the single, named edit to F2's
  escalation case 5 (§9.2).
* `LEGACY_ROLE_PERMISSIONS` is **not** changed, so
  `test_admin_gap_list_is_exact` and
  `test_administrator_is_a_superset_...` stay green, unmodified. The gap
  survives as a property of the legacy map, which is exactly what it always
  was.

### 4.2 Why `is_tenant_admin` returns the same set, and why the return is early

`TENANT_ADMIN_PERMISSIONS` (F2's seven-string bundle, marked
`TRANSITIONAL (IAM F2 -> F3)`) is **deleted**, with the test that pinned it to
the seven APRAS-43 routes. The capability now means what its name says.

The branch **returns** rather than unions, for the same reason the superuser
branch does: `PERMISSIONS | anything == PERMISSIONS`, and an early return says
"this is a short-circuit" instead of "this is one more contributor".

Scoping is unchanged and is what stops leakage: `is_acting_tenant_admin` reads
the acting tenant from `session.info` and looks up **that** tenant's
`UserTenantLink`. A síndico of A acting in B resolves through their own role
bundle and nothing else.

### 4.3 The two deliberate consequences of the widening

Both are behaviour changes for **capability holders only** (never for a
role), invisible to the six-role matrix, and therefore stated here and pinned
by tests rather than discovered later:

1. **`GET /api/v1/packages/my-lots` for a RESIDENT tenant_admin flips
   `200 → 403`** with *"Use /packages/queue…"*. They gain
   `packages:queue_read`, and `get_my_lots`'s first branch refuses anyone who
   holds it. **No information is lost**: `/packages/queue` is a strict
   superset (every lot, including their own), and this is already exactly what
   an ADMINISTRATOR who lives in the condominium experiences today. Pinned by
   `test_a_resident_tenant_admin_is_routed_to_the_queue`.
2. **A tenant_admin's photo uploads auto-approve** (they gain
   `uploads:auto_approve`) instead of landing in the pending queue. That is
   what "administrator-level in this tenant" means; an ADMINISTRATOR behaves
   the same way today. Pinned by
   `test_a_tenant_admin_upload_is_auto_approved`.

Every other inverted gate F2 created (`finance:transaction_delete`,
`purchases:decide`, `assets:update`, `gate:checkin` in
`visitor_service.get_authorization_for_user`, `votes:cast`,
`occurrences:manage_all`, `announcements:create` in `delete_comment`) widens
monotonically — holding the permission grants strictly more — so no other cell
can move. The two above are the complete list of non-monotone consequences and
`get_my_lots` is the only refusal.

---

## 5. The seven F3-marked survivors: what each becomes

### 5.1 The conversion table

Each site is named by **module and function**, never by line number: F2
reflows `api/deps.py` and `endpoints/users.py`, so any line number quoted here
would be stale before the implementer read it. Locate each site with
`grep -n 'def <name>'`.

| # | Site (F2 §5.3-A) | F3 action |
|---|---|---|
| 1 | `api/deps.py::get_current_active_admin` | **Converted and renamed** to `get_current_superuser`. Body becomes `if not current_user.is_superuser:` with the 403 detail `"The user doesn't have enough privileges"` **byte-identical**. Still a role-free, tenant-free dependency, so the five global `/api/v1/tenants` writes keep resolving without an acting tenant. The five `Depends` in `endpoints/tenants.py` are updated. |
| 2 | `api/deps.py::get_current_admin_or_manager` | **Deleted.** Zero references in `app/` at the merge base (F2 deleted the last tenant-scoped user of the shape); it survived F2 only so `test_tenant_admin.py` stayed unmodified. Keeping a dead role guard alive one slice past its purpose is exactly the drift this chain removes. |
| 3 | `api/deps.py::has_admin_capability` | **Converted**: `return user.is_superuser or is_acting_tenant_admin(user, session)`. Name and docstring intent unchanged ("administrator-level power *here*"). Its only caller at the merge base is `assert_menu_access`; the menu gate itself is F5's. |
| 4 | `api/deps.py::_resolve_from_header` | **Converted**: `is_admin = current_user.is_superuser`, renamed to `is_superuser` locally. Both behaviours it drives are preserved verbatim: a superuser may act in any tenant, and the 404-vs-403 existence oracle of APRAS-42 answers 404 only to a superuser. |
| 5 | `api/v1/endpoints/users.py::update_user` | **Converted**: `if not current_user.is_superuser:` guards the three escalation rules. §7 details the rules themselves. |
| 6 | `services/tenant_service.py::list_tenants` | **Converted**: `if current_user.is_superuser:` selects every tenant; everyone else sees only their memberships. |
| 7 | `services/tenant_service.py::get_visible_tenant` | **Converted**: `if current_user.is_superuser: return tenant`; every non-superuser non-member still gets 404, never 403. |

Six convert; one (#2) dies. **No site keeps a role read**, and no new
in-scope actor-role read is introduced: `user.is_superuser` is a plain column
access whose attribute name is not `role`.

### 5.2 Not converted here

`endpoints/users.py::update_user`'s **target and payload** reads
(`user_in.role`, `db_user.role`) are outside both AST rules by construction
(`user_in` / `db_user` are not in `ACTOR_NAMES`). `db_user.role == ADMINISTRATOR`
becomes `db_user.is_superuser` anyway (§7.2) because it is a *superuser*
question; `user_in.role == ADMINISTRATOR` stays a role read of the **payload**
and dies with the enum in F5.

The seven object/visibility survivors (F2 §5.3-B) and the resolver-plumbing
read (F2 §5.3-D) are untouched — F5 owns them.

### 5.3 The post-F3 allowlists — the exact edits to `tests/test_permission_enforcement.py`

This module is F2's, and editing its constants is **this slice's legitimate
edit**; F2's ER-2 test is *designed* to fail until they are changed. The edits
are:

**(a) `ROLE_READS_COMPARE`: 15 entries → 8.** Delete the seven `slice="F3"`
entries (rows 1–7 of §5.1). What remains is exactly F2's §5.3-B + §5.3-D,
all `slice="F5"`:

| Key | n | slice |
|---|---:|---|
| `api/deps.py::assert_manager_can_see_task` | 1 | F5 |
| `api/deps.py::assert_can_edit_task` | 1 | F5 |
| `api/deps.py::get_effective_user_type_ids` | 1 | F5 |
| `api/v1/endpoints/tasks.py::list_tasks` | 1 | F5 |
| `services/task_service.py::create_task` | 1 | F5 |
| `services/task_service.py::update_task` | 1 | F5 |
| `services/occurrence_service.py::_check_user_access` | 1 | F5 |
| `services/occurrence_service.py::get_occurrences` | 1 | F5 |
| **total** | **8** | |

`test_every_allowlisted_role_read_has_a_reason` keeps passing; the `slice`
field's permitted values narrow to `{"F5"}` — **assert that literally**, so a
future slice cannot re-introduce an `"F3"` marker after F3 has shipped.

**(b) `ROLE_READS_NON_COMPARE`: unchanged — 7 reads in 5 functions.** F3 adds
no Rule-N read (`get_effective_permissions` keeps its
`LEGACY_ROLE_PERMISSIONS.get(user.role, …)` line, which F5 deletes) and
removes none.

**(c) `test_role_read_arithmetic_closes`: one constant moves.** The ledger is
cumulative across the chain and stays anchored to F1's tree:

```python
RULE_C_BASELINE = 100      # measured at APRAS-45's commit 02c2025
RULE_N_BASELINE = 7        # idem
CONVERTED_COMPARE = 92     # 85 in F2 (APRAS-46) + 7 in F3 (APRAS-47, <F2_SHA>)
```

and the assertion becomes `RULE_C_BASELINE - CONVERTED_COMPARE == 8`,
`sum(ROLE_READS_COMPARE.values()) == 8`,
`sum(ROLE_READS_NON_COMPARE.values()) == 7`, with the walked mappings equal to
the two literals. **`RULE_C_BASELINE` and `RULE_N_BASELINE` do not change** —
they are historical statements about the F1 tree and are still true. Only
`CONVERTED_COMPARE` moves, by exactly the 7 of §5.1, with F3's merge-base sha
added to the comment beside it.

**(d) The guard-name assertions.** `test_get_current_active_admin_is_still_exactly_the_five_tenant_writes`
becomes `test_get_current_superuser_is_exactly_the_five_tenant_writes`,
naming `deps.get_current_superuser` and the same five `(method, path)` keys.
`test_no_route_depends_on_a_tenant_admin_role_guard` additionally asserts
`not hasattr(deps, "get_current_active_admin")` and
`not hasattr(deps, "get_current_admin_or_manager")`, so neither name can come
back.

**(e) Two new pins that close the `app/models/` loophole (§3.3).**

* `test_the_declarative_layer_has_no_actor_role_read` — run F2's Rule-C and
  Rule-N walkers over `app/models/`, `app/schemas/` and `app/seed.py` (the
  three paths F2 excludes) and assert **both mappings are empty**. Measured at
  the merge base: `Rule C: 0, Rule N: 0`, and §3.3's default does not change
  that (it reads `data.get("role")`, a `Call`, not an actor attribute).
* `test_the_superuser_default_is_the_only_administrator_literal_in_models` —
  AST-walk `app/models/` for `ast.Attribute(value=Name("UserRole"), attr="ADMINISTRATOR")`
  and assert the `{module::function: count}` mapping is exactly
  `{"user.py::__init__": 1}`. This is what makes §3.3 a declared, single,
  named exception instead of a blind spot.

---

## 6. `is_superuser` is not grantable through the groups API

### 6.1 The four permissions that may never enter a group

`ROUTE_PERMISSIONS` maps the five superuser-guarded `/api/v1/tenants` writes
to four permission strings — `tenants:create`, `tenants:update`,
`tenants:members_manage`, `tenants:members_set_admin` — but those routes are
gated by `get_current_superuser`, not by `require_permission`. Left alone,
the catalogue would advertise four strings an administrator could put in a
group where they would grant **nothing**: dead vocabulary that reads like a
grant. F1's "no dead vocabulary" rule and the board's ER-4 point at the same
fix.

```python
# app/core/permissions.py
#: Permissions whose routes are gated by `deps.get_current_superuser` and not
#: by a permission. They stay in the catalogue because they still *name* those
#: routes: `test_permission_registry.py::test_every_catalogue_permission_is_reachable`
#: asserts `set(ROUTE_PERMISSIONS.values()) == PERMISSIONS`, so removing them
#: from the catalogue while their routes remain mapped would turn that test
#: red. They can never be put into a group: superuser is a column, not a
#: bundle.
SUPERUSER_ONLY_PERMISSIONS: frozenset[str] = frozenset({
    "tenants:create",
    "tenants:update",
    "tenants:members_manage",
    "tenants:members_set_admin",
})
```

Pinned by `test_superuser_only_permissions_are_exactly_the_four_tenant_permissions`,
which lives **unconditionally** in `tests/test_superuser.py` as §9.1 case 20
(four permission strings; the five routes collapse to four because
`POST /members` and `DELETE /members/{user_id}` share `tenants:members_manage`):

```python
assert SUPERUSER_ONLY_PERMISSIONS == {
    ROUTE_PERMISSIONS[key] for key in SUPERUSER_ROUTES
}
```

over the five `(method, path)` keys spelled out in the test — the same five
`ADMIN_ONLY_ROUTES` `test_tenant_admin.py` already carries. The constant
therefore cannot drift from the routes it describes.

`tenants:read` and `tenants:members_read` are **not** included: they are
`ALL_ROLES` in the legacy map and gate the two read routes every member
reaches. They stay ordinary, grantable (and inert) permissions.

### 6.2 The check

`user_type_service.assert_can_grant` gains one branch, **before** the
"permissions you do not hold" branch:

```python
forbidden = sorted(set(permissions) & SUPERUSER_ONLY_PERMISSIONS)
if forbidden:
    raise ForbiddenError(
        "These permissions are granted by is_superuser only: "
        + ", ".join(forbidden)
    )
```

* It applies to **every** author, superuser included: the point is that the
  group would be a lie, not that the author is untrusted.
* It runs on the same three surfaces F2 wired (`POST /user-types/`,
  `PATCH /user-types/{id}`, and the `user_type_ids` path of
  `PATCH /users/{id}`), so no new call site is added.
* It is behaviour-neutral at the merge base: nothing seeds a bundle, so no
  existing group carries any of the four.

The `permissions` field validator is untouched: the four strings are in
`PERMISSIONS`, so they are *valid* (422 is for unknown strings) and
*un-grantable* (403). Keeping the two answers distinct is what makes the error
message useful.

---

## 7. `PATCH /api/v1/users/{user_id}` — escalation, re-expressed

### 7.1 The actor test

`if current_user.role != UserRole.ADMINISTRATOR:` becomes
`if not current_user.is_superuser:`. Identical behaviour at the merge base
(§3.3 keeps role and column in lockstep for every user the app creates), and
now correct for a non-ADMINISTRATOR superuser as well.

### 7.2 The three rules

| # | At the merge base | After |
|---|---|---|
| 1 | `user_in.role == ADMINISTRATOR` → 403 *"Tenant administrators cannot grant the ADMINISTRATOR role"* | **unchanged.** A payload read, not an actor read; and with §7.3 it *is* the superuser grant, so it must stay closed. Dies with the enum in F5. |
| 2 | `db_user.role == ADMINISTRATOR` → 403 *"Tenant administrators cannot modify an administrator"* | `db_user.is_superuser` → 403, **same detail string, byte-identical**. Behaviour is identical for every ADMINISTRATOR target and now also protects a non-ADMINISTRATOR superuser. This is the board's "an is_tenant_admin cannot edit a superuser". |
| 3 | membership in another tenant → 403 *"This user belongs to another tenant"* | **unchanged.** |

The detail strings are kept verbatim on purpose:
`tests/test_user_directory_scope.py` asserts two of them literally, and F5 —
which retires the word "administrator" from the vocabulary — is the right
slice to reword them.

### 7.3 The role-change mirror

```python
# TRANSITIONAL (IAM F3 -> F5). While the enum still exists, ADMINISTRATOR and
# is_superuser must move together: promoting through this route is already
# superuser-only (rule 1), and *demoting* an administrator has always removed
# their global power immediately. Writing the column here is what keeps that
# true and what lets F5 drop the enum without losing or stranding a grant.
if update_data.get("role") is not None:
    db_user.is_superuser = update_data["role"] == UserRole.ADMINISTRATOR
```

placed after the `setattr` loop. The guard is `.get(...) is not None` and not
`"role" in update_data` so that an explicit `{"role": null}` in the body — which
`exclude_unset` keeps in `update_data` and which the `setattr` loop would refuse
against a NOT NULL column anyway — cannot be read as "demote to non-superuser".
Only a body that names a real role moves the column. Without it, demoting an administrator would
leave `is_superuser` set — a privilege-retention hole this slice would have
created — and promoting would produce a user the frontend shows admin UI to
and the backend refuses on `/api/v1/tenants`.

`update_data["role"]` is a payload read: outside both AST rules, no allowlist
entry. `is_superuser` itself remains **absent from `UserUpdate`**, so a body
carrying `{"is_superuser": true}` is ignored by Pydantic and changes nothing —
asserted directly (§9.1 case 12).

---

## 8. `/auth/me` and the frontend: a justified non-goal

`useAdminCapability` / `useEffectiveAdminCapability`
(`frontend/src/features/user-administration/context/useAdminCapability.ts`)
read `user?.role === UserRole.ADMINISTRATOR || isActingTenantAdmin`.

* `UserRead` still carries `role`, and `role == ADMINISTRATOR` still implies
  `is_superuser` for every user the application creates or edits: §3.3 sets it
  at creation, `0031` sets it for every pre-existing row, and §7.3 keeps the
  two in step across every role change the API permits. There is **no
  API-reachable state** in which the frontend's answer differs from the
  backend's.
* The only divergent state is one written directly in SQL
  (`role=ADMINISTRATOR, is_superuser=false`) — deliberately constructible for
  ER-3's negative test, and not something the product can produce.
* The tenant_admin half is unchanged: `isActingTenantAdmin` already comes from
  `/auth/me`'s `tenants` array (APRAS-38).

So: **no `is_superuser` on `UserRead`, no `/auth/me` change, no frontend file
touched.** Exposing the flag (and switching `useAdminCapability` onto it) is
F4's job, together with the permission-driven UI; doing it here would ship a
field with no consumer. `git status --short -- frontend/` is empty.

---

## 9. Tests

### 9.1 `backend/tests/test_superuser.py` (new)

The flag is the subject, so every case constructs it **explicitly** — a
`DIRECTOR` with `is_superuser=True`, an `ADMINISTRATOR` with
`is_superuser=False` — and never leans on §3.3's default. That is what makes
these assertions about `is_superuser` rather than about `role`.

*Resolution (ER-2)*

1. `get_effective_permissions(superuser, session) == PERMISSIONS`, for a
   `DIRECTOR`-role user with `is_superuser=True`, acting in tenant A.
2. …the same user acting in tenant **B**, of which they are not a member
   (reached by sending `X-Tenant-Id: B`, which §5.1 #4 allows): still
   `== PERMISSIONS`.
3. …and on a bare `Session(engine)` with no acting tenant: still
   `== PERMISSIONS` (the branch precedes every tenant lookup).
4. `get_effective_permissions(tenant_admin_of_A, session) == PERMISSIONS`
   while acting in A.
5. The same user acting in B: `== LEGACY_ROLE_PERMISSIONS[RESIDENT]`
   (their role bundle, nothing more) — **the non-leakage case**.
6. The same user on a session with **no** acting tenant:
   `== LEGACY_ROLE_PERMISSIONS[RESIDENT]`.

   Cases 5 and 6 assert **set equality**, so they are only meaningful if
   nothing else contributes: the fixture must give tenant B no
   `UserType` whose `role` is `RESIDENT` and no `UserType` linked to the user
   (`get_effective_user_type_ids` resolves both), or give them
   `permissions == []`. Assert that precondition in the test —
   `get_effective_user_type_ids(user, session_in_B) == []` and every
   `UserType` reachable in B has `permissions == []` — rather than relying on
   the fixture staying bare. Otherwise a later fixture that seeds a bundle in B
   turns the non-leakage case red for a reason unrelated to leakage, or (worse,
   if the assertion were `>=`) green while leaking.
7. `"packages:my_lots_read" in get_effective_permissions(superuser, session)`
   and `not in LEGACY_ROLE_PERMISSIONS[ADMINISTRATOR]` — §4.1's decision, made
   observable.

*The five global writes (ER-3)*

8. Each of the five `/api/v1/tenants` writes returns its documented success
   status for a `DIRECTOR`-role user with `is_superuser=True`.
9. Each returns **403** for an `ADMINISTRATOR`-role user stored with
   `is_superuser=False` — the proof that the column, not the enum, is what is
   read.
10. Each returns **403** for a tenant_admin of the target tenant (parity with
    `test_tenant_admin.py::test_every_tenant_write_is_403_for_a_tenant_admin`,
    duplicated here so this module states its own boundary).
11. `PATCH /api/v1/tenants/{id}/members/{user_id}` granting or revoking
    `is_tenant_admin` is 403 for a tenant_admin and 200 for a superuser.

*Not grantable (ER-4)*

12. `PATCH /api/v1/users/{id}` with `{"is_superuser": true}` from a superuser:
    **200**, and the target's `is_superuser` is still `False` (the field does
    not exist on `UserUpdate`).
13. `POST /api/v1/user-types/` with `{"permissions": ["tenants:create"]}` →
    **403**, body naming `tenants:create`; no row created. Same from a
    superuser author.
14. `PATCH /api/v1/user-types/{id}` adding `tenants:members_set_admin` → 403.
15. A tenant_admin cannot grant the ADMINISTRATOR role (403, rule 1) and
    cannot edit a superuser (403, rule 2, with the merge-base detail string) —
    including a **`DIRECTOR`-role superuser**, which the merge base did not
    protect.
16. Promoting a user to ADMINISTRATOR through `PATCH /users/{id}` (superuser
    author) sets `is_superuser=True`; demoting them to DIRECTOR sets it back
    to `False` (§7.3).

*The widening's two consequences (§4.3)*

17. `test_a_resident_tenant_admin_is_routed_to_the_queue` —
    `GET /api/v1/packages/my-lots` is 403 with the *"Use /packages/queue…"*
    detail for a RESIDENT tenant_admin acting in their tenant, and
    `GET /api/v1/packages/queue` is 200 for the same caller.
18. `test_a_tenant_admin_upload_is_auto_approved` — a photo uploaded by a
    RESIDENT tenant_admin is approved rather than pending.

*The model default (§3.3)*

19. `User(role=UserRole.ADMINISTRATOR, …).is_superuser is True`;
    `User(role=UserRole.ADMINISTRATOR, is_superuser=False, …).is_superuser is False`;
    `User(role=UserRole.DIRECTOR, …).is_superuser is False`; and a row stored
    with `role=ADMINISTRATOR, is_superuser=False` still reads `False` after
    `session.refresh()`.

*The constant (§6.1)*

20. `test_superuser_only_permissions_are_exactly_the_four_tenant_permissions`
    — §6.1's pin, and it lives **here, unconditionally**, not in
    `test_permission_registry.py`. It is a new assertion about a new constant,
    so it has no reason to depend on where F2 happened to put the
    `TENANT_ADMIN_PERMISSIONS` pin this slice deletes; homing it here keeps
    the "which modules changed" answer of ER-8 independent of that discovery.
    It asserts `SUPERUSER_ONLY_PERMISSIONS == {ROUTE_PERMISSIONS[k] for k in
    SUPERUSER_ROUTES}` over the five `(method, path)` keys spelled out in the
    test, and `SUPERUSER_ONLY_PERMISSIONS <= PERMISSIONS`.

### 9.2 Pre-existing test modules that legitimately change — the complete list

| Module | Edit | Why it is forced |
|---|---|---|
| `tests/test_migrations_postgres.py` | (i) the **three** `== "0030_add_user_type_permissions"` literals (located by grep, not by line number) become `"0031_add_user_is_superuser"`; (ii) an **additive** EOF section for `0031` | The established precedent: F1 moved the *two* head pins that existed then and appended its own section, which introduced the third. The exact count is `grep -c '== "0030_add_user_type_permissions"'` at the merge base — quote it in the PR body and change them all. The new section adds `test_is_superuser_column_shape_and_conversion` (boolean / NOT NULL / `false` default at head; a user inserted at `0027` with role ADMINISTRATOR reads `true` and one with role DIRECTOR reads `false`; `downgrade 0030` drops the column; `upgrade head` restores it) and `test_0031_does_not_touch_is_tenant_admin` (the `user_tenant_link.is_tenant_admin` column shape is identical before and after `0031`). |
| `tests/test_permission_enforcement.py` (F2) | `ROLE_READS_COMPARE` 15 → 8; `slice` values narrowed to `{"F5"}`; `CONVERTED_COMPARE` 85 → 92; the two guard-name assertions; the two new declarative-scope pins | §5.3. F2's ER-2 test asserts the allowlist **exactly**; converting seven of its entries *must* change it. This is the edit F2 §5.3-A declared in advance. |
| `tests/test_permission_escalation.py` (F2) | the author of cases 1, 3, 4 and 7 changes from "a tenant_admin holding `user_types:create` but not `finance:category_create`" to **a RESIDENT carrying a `UserType` whose `permissions` are `["user_types:create", "user_types:update"]`**; case 5 flips | §4.2 gives a tenant_admin every permission of their tenant, so the old author can no longer be missing one — the case would pass vacuously or invert. The replacement author is strictly better: it exercises the group mechanism the feature is about. Case 5 ("an ADMINISTRATOR may grant anything except `packages:my_lots_read`") becomes "a superuser may grant every catalogue permission **except** `SUPERUSER_ONLY_PERMISSIONS`" (§4.1, §6.2). |
| `tests/test_effective_permissions.py` (F1/F2) | F2's bridge case "the capability adds exactly those seven" becomes "the capability resolves to `PERMISSIONS`"; the two negative cases (no acting tenant; a non-granting tenant) keep their assertions | `TENANT_ADMIN_PERMISSIONS` no longer exists. Additive superuser cases live in `test_superuser.py`, not here. |
| `tests/test_tenant_admin.py` | `test_the_role_only_guards_stay_available_and_unchanged` → `test_the_superuser_guard_stays_available_and_unchanged` (drops `get_current_admin_or_manager`, calls `deps.get_current_superuser`, keeps the 403 detail assertion); `test_no_tenant_scoped_route_keeps_a_role_only_admin_guard` and `test_get_current_active_admin_is_exactly_the_five_tenant_writes` renamed onto `get_current_superuser`; `ADMIN_ONLY_ROUTES` **unchanged** | Three references to two symbols that are renamed and deleted by §5.1. Every *behavioural* test in the module — the seven admin-gated routes, both `[403]*7` matrices, the menu-gate pair, `test_has_admin_capability_is_true_for_an_administrator_anywhere` — passes **unmodified**. |
| `tests/test_permission_registry.py` *(conditional — deletion only)* | delete `test_tenant_admin_permissions_are_exactly_the_apras43_routes` **if and only if F2 landed it here** rather than in `test_effective_permissions.py`. Nothing is added to this module: `test_superuser_only_permissions_are_exactly_the_four_tenant_permissions` is §9.1 case 20, in `tests/test_superuser.py`. | The constant it pins is deleted. Locate it by name before editing; report the actual location in the PR body. If F2 landed the pin in `test_effective_permissions.py`, this module is **not** touched at all. |

**Must pass byte-identical** — asserted with `git status --short -- backend/tests/`
(this task stages and never commits): `tests/matrix_world.py`,
`tests/tools/**`, `tests/data/parity_matrix_baseline.json`,
`tests/test_permission_parity_matrix.py`, `tests/test_legacy_role_permissions.py`,
`tests/conftest.py`, `tests/test_tenant_isolation.py`,
`tests/test_tenant_route_scope.py`, `tests/test_tenant_no_behaviour_change.py`,
`tests/test_tenant_context.py`, `tests/test_menu_access.py`,
`tests/test_role_type_permissions.py`, `tests/test_user_directory_scope.py`,
`tests/test_user_admin.py`, `tests/test_user_types.py`,
`tests/test_user_contact_info.py`, `tests/test_auth_me_tenants.py`,
`tests/test_tenants.py`, `tests/test_porteiro_role.py`,
`tests/test_gatekeeper.py`, `tests/test_packages.py`,
`tests/test_packages_rbac.py` and every other `test_*_rbac.py`.

**`tests/conftest.py` is explicitly on that list.** If the implementation finds
itself editing a fixture to add `is_superuser=True`, §3.3's default is missing
or wrong — fix §3.3, not the fixture.

---

## 10. The matrix does not move, and the baseline is not re-recorded

The board's third design question. Walked cell by cell, for the only actor
whose effective set changes — `MatrixWorld`'s ADMINISTRATOR, who becomes a
superuser through §3.3 and so gains exactly one permission,
`packages:my_lots_read`:

* **`(ADMINISTRATOR, GET, /api/v1/packages/my-lots)` stays 403.** The route
  carries no route-level `require_permission` (F2 mounts the dependency on
  seven routes, and this is not one). `PackageService.get_my_lots` tests
  `has_permission("packages:queue_read")` **first**; `packages:queue_read` is
  `{A, D, M, P}`, so an ADMINISTRATOR — superuser or not — takes the first
  branch and raises `PackageAccessForbiddenError("Use /packages/queue para ver
  encomendas de todos os lotes.")`, which the handlers map to 403. The second
  branch, the only consumer of `packages:my_lots_read`, is unreachable for
  them. **The cell is unchanged.**
* **Every other ADMINISTRATOR cell** was already permitted and stays
  permitted: the set only grew, and the sole growth is the string above.
* **The five `/api/v1/tenants` writes**: the ADMINISTRATOR cell passes
  `get_current_superuser` (§3.3 ⇒ `is_superuser=True`) exactly as it passed
  `get_current_active_admin`; the other five roles are non-superusers and
  still get 403 with the same detail.
* **`GET /api/v1/tenants`, `GET /api/v1/tenants/{id}`**: `list_tenants` /
  `get_visible_tenant` take the same branch for the same user. Unchanged.
* **`PATCH /api/v1/users/{id}`**: the ADMINISTRATOR still skips the escalation
  block; the other five roles are refused by `require_permission("users:update")`
  before reaching it. §7.3's mirror runs only when the body carries `role`,
  and F2's `REQUEST_BODIES` entry decides that once, identically, before and
  after.
* **`X-Tenant-Id` resolution**: the matrix sends `DEFAULT_TENANT_ID` and all
  six users are members, so `_resolve_from_header`'s superuser branch is not
  on the path.
* **The tenant_admin widening touches nothing**: `MatrixWorld` creates all six
  memberships with `is_tenant_admin=False`, and the capability is not a role,
  so it has no cell.

Therefore: **`tests/data/parity_matrix_baseline.json` is NOT re-recorded, and
`tests/matrix_world.py` is NOT edited.** Both stay byte-identical to the merge
base, `_meta.merge_base_sha` keeps pointing at F1's commit, and F2's
`_meta.regenerate` command still reproduces the file exactly (it copies only
the harness and the recorder into a clean worktree at that sha, neither of
which this slice touches). `test_permission_parity_matrix.py` passes
unmodified, 1080/1080.

If **any** cell does move, that is a finding: name the cell, the recorded and
actual status, and the production line responsible, in the PR body — and stop.
It is not a licence to re-record.

---

## 11. Ordering for the implementer

1. Model column + §3.3 default + migration `0031`, and the
   `test_migrations_postgres.py` edits. Run the sqlite suite: it must be
   **entirely green with no other change** — that is the proof §3.3 is right
   and `tests/conftest.py` needs nothing.
2. `get_effective_permissions` (§4) and the deletion of
   `TENANT_ADMIN_PERMISSIONS`. Re-run `test_effective_permissions.py`,
   `test_tenant_admin.py`, `test_permission_parity_matrix.py`.
3. The six conversions + one deletion of §5.1, and the five `Depends` in
   `endpoints/tenants.py`. Re-run the matrix after each file.
4. §7 (`update_user`) and §6 (`SUPERUSER_ONLY_PERMISSIONS` +
   `assert_can_grant`).
5. `tests/test_superuser.py`.
6. The F2 test-module edits (§5.3, §9.2) **last**: the walker test tells you
   what you missed, so let it fail until step 3 is genuinely complete.
7. The `AGENTS.md` amendment (§12), written against the code as it actually
   landed.

---

## 12. The `AGENTS.md` amendment

`AGENTS.md`'s **"Tenant administrator"** section (the paragraph beginning
`user_tenant_link.is_tenant_admin` (APRAS-43) is a capability *layered on top
of* `UserRole`) is the repository's own statement of what this capability
means. This slice changes that meaning — from a hand-listed bundle to *every*
permission of the tenant — and adds a global column the section has no word
for. Leaving it unamended would make the doc actively misleading for two
slices, so the amendment lands **here**, with the change it describes.

The edit is bounded to that one section and is these five points:

1. **The meaning sentence.** "it grants administrator-level permission
   **inside one tenant only**" becomes explicit about the widening: it grants
   **every permission in the catalogue**, inside the granting tenant only —
   `deps.get_effective_permissions` returns `PERMISSIONS` for it, and returns
   only the user's own role/group bundles in every other tenant and with no
   acting tenant.
2. **The guard bullet.** The bullet naming
   `deps.get_current_tenant_admin` / `deps.get_current_tenant_admin_or_manager`
   is stale at this merge base — F2 deleted both. Rewrite it onto what actually
   gates those seven routes after F2: `deps.require_permission(...)` against
   the route's entry in `ROUTE_PERMISSIONS`. The menu-gate exemption sentence
   is unchanged.
3. **A new "Install superuser" paragraph**, adjacent, stating: `user.is_superuser`
   (APRAS-47, migration `0031`) is the global counterpart — every permission in
   **every** tenant and with no acting tenant; it is a column, not a role and
   not a group, so it is not grantable through the groups API
   (`SUPERUSER_ONLY_PERMISSIONS`) and not settable through `UserUpdate`; it
   gates the five global `/api/v1/tenants` writes via
   `deps.get_current_superuser`. Note the transitional rule of §3.3/§7.3 —
   while `UserRole` exists, ADMINISTRATOR and `is_superuser` are kept in
   lockstep — and mark it `TRANSITIONAL (IAM F3 -> F5)` in the same words the
   code uses.
4. **The escalation bullet.** "every caller that is not a global
   `ADMINISTRATOR`" becomes "every caller that is not a superuser", and
   "modify an `ADMINISTRATOR`" becomes "modify a superuser" — matching §7.2.
   The user-visible detail strings are **not** changed (§7.2), and the
   amendment says so, so the next reader does not "fix" the doc by renaming
   the strings.
5. **The "does not grant" bullet** — the one beginning *"It does **not** grant
   the domain-service role sets (announcements, finance, occurrences, voting,
   …), per-lot `UserLotLink` access, or any tenant/membership management"*
   (AGENTS.md l.333–337 at this merge base; locate it by its opening words, not
   by line number). Point 1 makes this bullet **false twice**, so leaving it is
   not an omission but a contradiction sitting four lines under the corrected
   sentence:
   * The domain-service clause **inverts**. The capability now grants every
     catalogue permission in the granting tenant, announcements, finance,
     occurrences and voting included. Delete that clause, or restate it as the
     positive it has become — *"it grants the domain-service permissions
     (announcements, finance, occurrences, voting, …) inside the granting
     tenant"*. Do not leave the negative standing.
   * The `UserLotLink` clause **survives, unchanged**: per-lot linkage is
     object ownership, not a permission, and §1 explicitly leaves it to F5.
   * The tenant/membership-management clause **survives, unchanged**: those
     five writes are superuser-only (§5.1, §6.1), which is exactly why they are
     the one thing a tenant_admin still cannot reach.
   * `ADMINISTRATOR` **only** at the end of the bullet becomes **superuser
     only**, naming `deps.get_current_superuser`, because after §5.1 the grant
     route reads the column and not the enum.

**Bounded.** No other section of `AGENTS.md` is touched: not the role table at
l.394 (its `ADMINISTRATOR` row describes object/visibility rules that F5 owns),
not the tenant-scoping sections, not the file map. The wholesale IAM rewrite —
roles becoming groups, the enum's removal, `allowed_menus` — is **F5's**, and
this amendment neither performs nor pre-empts it.

---

## Expected Results

- [ ] **ER-1 — the column and its migration.** `User.is_superuser` exists as
      `boolean NOT NULL DEFAULT false`.
      `backend/alembic/versions/0031_add_user_is_superuser.py` is the only new
      file under `alembic/versions/`, chains on
      `0030_add_user_type_permissions`, has a revision id of **26 characters**
      (the invariant is ≤ 32, the `alembic_version` column width), and
      `alembic heads` reports the single head
      `0031_add_user_is_superuser`. On a real Postgres (local 5436),
      `tests/test_migrations_postgres.py` passes with its three head-pin
      literals moved from `"0030_add_user_type_permissions"` to
      `"0031_add_user_is_superuser"` (the count is
      `grep -c '== "0030_add_user_type_permissions"'` at the merge base,
      quoted in the PR body) and an additive EOF section in which
      `test_is_superuser_column_shape_and_conversion` proves: the column is
      `boolean` / `is_nullable = NO` / `column_default = false` at head; a row
      inserted before the migration with `role = 'ADMINISTRATOR'` reads
      `is_superuser = true` afterwards and one with `role = 'DIRECTOR'` reads
      `false`; `alembic downgrade 0030_add_user_type_permissions` drops the
      column and `upgrade head` restores it. `test_0031_does_not_touch_is_tenant_admin`
      proves `user_tenant_link.is_tenant_admin` has the identical column shape
      before and after `0031`, and `git diff` shows no change to
      `0029_add_is_tenant_admin.py` or to the `is_tenant_admin` field.
- [ ] **ER-2 — the two short-circuits, proven on the flag and not on the
      role.** `deps.get_effective_permissions` returns `PERMISSIONS` (the whole
      catalogue, `packages:my_lots_read` included) whenever
      `user.is_superuser`, **before** any tenant is resolved; and returns
      `PERMISSIONS` when `deps.is_acting_tenant_admin(user, session)`.
      `app.core.permissions.TENANT_ADMIN_PERMISSIONS` no longer exists.
      `tests/test_superuser.py` cases 1–7 pass: a **`DIRECTOR`-role** user with
      `is_superuser=True` resolves to `PERMISSIONS` while acting in tenant A,
      while acting in tenant B of which they are not a member, and on a
      `Session` with no acting tenant; a RESIDENT tenant_admin of A resolves to
      `PERMISSIONS` acting in A and to exactly
      `LEGACY_ROLE_PERMISSIONS[UserRole.RESIDENT]` acting in B or with no
      acting tenant — **the non-leakage assertion**. `LEGACY_ROLE_PERMISSIONS`
      is unchanged, so `test_admin_gap_list_is_exact` still passes unmodified.
- [ ] **ER-3 — the five global writes read the column.** `deps` exposes
      `get_current_superuser` (403 detail `"The user doesn't have enough
      privileges"`, byte-identical to the guard it replaces) and no longer
      defines `get_current_active_admin` or `get_current_admin_or_manager`;
      the renamed structural tests in both `tests/test_tenant_admin.py` and
      `tests/test_permission_enforcement.py` show it is reachable from exactly
      `POST /api/v1/tenants`, `PATCH /api/v1/tenants/{tenant_id}`,
      `POST /api/v1/tenants/{tenant_id}/members`,
      `DELETE /api/v1/tenants/{tenant_id}/members/{user_id}`,
      `PATCH /api/v1/tenants/{tenant_id}/members/{user_id}` and from nothing
      else, and from no tenant-scoped route. On all five:
      a `DIRECTOR`-role user with `is_superuser=True` succeeds; an
      **`ADMINISTRATOR`-role user stored with `is_superuser=False`** gets
      **403**; a tenant_admin of the target tenant gets **403**. Granting and
      revoking `is_tenant_admin` via
      `PATCH /api/v1/tenants/{tenant_id}/members/{user_id}` is 403 for a
      tenant_admin and 200 for a superuser, and
      `tests/test_tenant_admin.py`'s behavioural tests — the seven admin-gated
      routes, both `[403]*7` matrices and the two menu-gate cases — pass
      **unmodified**.
- [ ] **ER-4 — superuser is not grantable, and a tenant_admin cannot reach
      it.** `UserUpdate` has **no** `is_superuser` field:
      `PATCH /api/v1/users/{id}` with `{"is_superuser": true}` from a superuser
      returns 200 and leaves the target's flag `False`.
      `app.core.permissions.SUPERUSER_ONLY_PERMISSIONS` equals
      `{ROUTE_PERMISSIONS[k] for k in the five keys above}` —
      `{"tenants:create", "tenants:update", "tenants:members_manage",
      "tenants:members_set_admin"}` — asserted by
      `test_superuser_only_permissions_are_exactly_the_four_tenant_permissions`, and
      `user_type_service.assert_can_grant` returns **403** (naming the offending
      strings) for any group containing one of them, on
      `POST /user-types/`, `PATCH /user-types/{id}` and the `user_type_ids`
      path of `PATCH /users/{id}`, **for every author including a superuser**;
      no row is created. A tenant_admin sending `{"role": "ADMINISTRATOR"}`
      gets 403 with the merge-base detail string, and editing **any** superuser
      (including a `DIRECTOR`-role one) gets 403 with the merge-base detail
      string `"Tenant administrators cannot modify an administrator"`.
      Promoting a user to ADMINISTRATOR through `PATCH /users/{id}` sets
      `is_superuser=True` and demoting them clears it (§7.3).
- [ ] **ER-5 — every F3-marked role read is gone, and the ledger closes.**
      `tests/test_permission_enforcement.py` passes with
      `ROLE_READS_COMPARE` reduced to the **8** entries of §5.3(a) — all
      carrying `slice == "F5"`, asserted literally so `"F3"` can never appear
      again — `ROLE_READS_NON_COMPARE` **unchanged at 7 reads in 5 functions**,
      and `test_role_read_arithmetic_closes` asserting
      `RULE_C_BASELINE (100) - CONVERTED_COMPARE (92) == 8` and
      `RULE_N_BASELINE (7) - 0 == 7`, with F3's merge-base sha beside the moved
      constant. The AST walkers, not a grep, are the acceptance criterion here:
      a textual scan of `backend/app/` for `role == UserRole.ADMINISTRATOR` and
      its siblings is a **PR-body observation** (quote the residual hits and why
      each is a data table, a payload read or a target read), never a pass/fail
      gate — it cannot distinguish an actor read from a payload read, which is
      the entire distinction this slice turns on. Two new pins hold the
      declarative layer:
      `test_the_declarative_layer_has_no_actor_role_read` (the Rule-C and
      Rule-N walks over `app/models/`, `app/schemas/` and `app/seed.py` are
      both **empty**) and
      `test_the_superuser_default_is_the_only_administrator_literal_in_models`
      (the `UserRole.ADMINISTRATOR` references under `app/models/` are exactly
      `{"user.py::__init__": 1}`).
- [ ] **ER-6 — the parity matrix is green against the SAME baseline, not a new
      one.** `tests/test_permission_parity_matrix.py` passes **unmodified**,
      1080/1080, and `git status --short -- backend/tests/` shows **no change**
      to `tests/matrix_world.py`, `tests/tools/**` or
      `tests/data/parity_matrix_baseline.json`. In particular the cell
      `(ADMINISTRATOR, GET, /api/v1/packages/my-lots)` is still the baseline's
      **403** — `PackageService.get_my_lots` refuses on
      `has_permission("packages:queue_read")` (`{A, D, M, P}`) before the
      `packages:my_lots_read` branch a superuser now holds is ever reached, so
      granting the whole catalogue moves no cell (§10). Running F2's
      `_meta.regenerate` command still produces a byte-identical file
      (`diff` exits 0).
- [ ] **ER-7 — the widening's two consequences are pinned, not discovered.**
      `test_a_resident_tenant_admin_is_routed_to_the_queue`: for a RESIDENT
      holding `is_tenant_admin` in the acting tenant,
      `GET /api/v1/packages/my-lots` returns **403** with the detail *"Use
      /packages/queue para ver encomendas de todos os lotes."* and
      `GET /api/v1/packages/queue` returns **200** — the same behaviour an
      ADMINISTRATOR living in the condominium already has, so no information is
      lost. `test_a_tenant_admin_upload_is_auto_approved`: a photo uploaded by
      the same caller is approved rather than pending. Both are named in the PR
      body as intended behaviour changes for capability holders.
- [ ] **ER-8 — nothing else moves, and the suite is green.**
      `git status --short -- frontend/` is empty; `UserRead` has no
      `is_superuser` field and `GET /api/v1/auth/me` is byte-identical
      (§8). The pre-existing test modules that change are **exactly** the five
      named in §9.2 (plus `tests/test_permission_registry.py` only if F2 landed
      the `TENANT_ADMIN_PERMISSIONS` pin there — report which); in particular
      `tests/conftest.py`, `tests/test_tenant_isolation.py`,
      `tests/test_menu_access.py`, `tests/test_role_type_permissions.py`,
      `tests/test_user_directory_scope.py`, `tests/test_legacy_role_permissions.py`
      and every `test_*_rbac.py` are byte-identical to the merge base and pass.
      `uv run pytest --cov=app` is green with **0 failures**; total coverage is
      **≥ 90 %** and no more than 0.5 pp below the merge-base total; the
      collected-case count is **≥ M − 8 + 15**, where `M` is
      `uv run pytest --collect-only -q | tail -1` measured in a clean worktree
      at F3's merge base (`git worktree add /tmp/apras-mb <F2_SHA>`), and `15`
      is a deliberately loose floor for §9.1's twenty new cases and §9.2's two
      migration cases. The `8` is a ceiling on the cases §9.2 **retires**,
      derived rather than guessed: the deleted `TENANT_ADMIN_PERMISSIONS` pin
      (1, or its parametrisations); F2's escalation cases 1, 3, 4, 5 and 7,
      which are rewritten rather than deleted but may collapse or split as
      their author changes (≤ 5); and `test_effective_permissions.py`'s bridge
      case, likewise rewritten (1) — 7, rounded to 8. A shortfall below
      `M − 8 + 15` means a case vanished that this spec did not authorise:
      name it in the PR body. The **exact** retired and added counts, not just
      the inequality, are quoted in the PR body.
      `M`, the post-change count, the coverage pair and `<F2_SHA>` are quoted
      in the PR body, together with `CONVERTED_COMPARE`'s old and new values.
      `ruff check` is clean on every file this task touches. The PR body also
      records, as a **note for F5 and not as work done here**, the prose
      references to the guards this slice renames or deletes that survive
      inside test files it does not otherwise touch — at this merge base
      `tests/test_menu_access.py:295` ("`get_current_active_admin` already
      403s them first", in a docstring) and `tests/test_tenants_rbac.py:4`
      ("behind the existing `deps.get_current_active_admin` guard", in the
      module docstring). Both are comments, both keep their modules
      byte-identical, and neither is edited here: rewriting a docstring in an
      untouched module would break the byte-identical list above for no
      behavioural gain. Locate them at the merge base with
      `grep -rn 'get_current_active_admin\|get_current_admin_or_manager'
      backend/tests/` and quote whatever the actual hits are.
- [ ] **ER-9 — the architecture doc tells the truth about the capability.**
      `AGENTS.md`'s "Tenant administrator" section states that
      `is_tenant_admin` grants **every** catalogue permission inside the
      granting tenant and nothing outside it; no longer names the deleted
      `deps.get_current_tenant_admin` / `deps.get_current_tenant_admin_or_manager`
      (`grep -c 'get_current_tenant_admin' AGENTS.md` → `0`); carries an
      adjacent paragraph documenting `user.is_superuser` (migration `0031`,
      `deps.get_current_superuser`, not grantable via the groups API, not
      settable via `UserUpdate`) marked `TRANSITIONAL (IAM F3 -> F5)`; and
      states that a caller who is not a superuser cannot grant ADMINISTRATOR or
      modify a superuser. **The section contains no sentence denying the
      widened meaning** (§12 point 5): the "does not grant the domain-service
      role sets" clause is gone —
      `grep -c 'not\*\* grant the domain-service' AGENTS.md` → `0` — while the
      same bullet's `UserLotLink` clause and its tenant/membership-management
      clause survive verbatim in `git diff`, and its closing `ADMINISTRATOR`
      **only** now reads **superuser only** and names
      `deps.get_current_superuser`. Every remaining `ADMINISTRATOR` hit inside
      the section — `sed` the section out and `grep -n ADMINISTRATOR` it — is
      enumerated in the PR body and is either the menu-gate exemption
      comparison or the *name of a role in a payload*; **none** is a statement
      about who holds global power, and none denies the tenant_admin a
      permission it now holds. `git diff -- AGENTS.md` touches **that section
      only** — no hunk outside it, in particular none in the role table or the
      file map — and `grep -c 'get_current_superuser' AGENTS.md` is ≥ 1.

---

## Out of scope

An `is_superuser` grant/revoke API or UI (F4/F5); exposing `is_superuser` or
effective permissions on `GET /auth/me` (F4); the groups-management UI and
permission-driven frontend gating (F4); dropping `User.role`,
`LEGACY_ROLE_PERMISSIONS`, `allowed_menus` or renaming groups to roles (F5);
converting the seven object/visibility role reads or the resolver-plumbing
read (F5); the wholesale rewrite of `AGENTS.md`'s IAM vocabulary — the role
table, `allowed_menus`, groups-as-roles — which F5 does once, against settled
names, rather than three times against moving ones (§12 amends one section and
stops); seeding any default bundle (never — the user's standing decision);
per-user loose permissions; role nesting; any change to
`user_tenant_link.is_tenant_admin`, to its migration, or to the route that
grants it.
