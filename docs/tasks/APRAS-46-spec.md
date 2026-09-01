# APRAS-46 — IAM F2: enforcement by permission, with an exhaustive parity matrix

Slice 2 of the IAM chain (F1 `APRAS-45` → **F2 this** → F3 `APRAS-47` →
F4 `APRAS-48` → F5 `APRAS-49`). F1 built the vocabulary and changed no
authorization outcome. **This slice is the enforcement swap**: every
role-dimension authorization decision in the backend stops reading
`user.role` and starts reading a permission, and a mechanically generated
`role × route × verb` matrix proves the swap changed **no** status code.

> **Numbering note, read this first.** The F1 spec says in §1, §6.2 and
> §11.6 that "enforcement is F4" and that F4's enforcement "must be additive
> (role gate AND permission), never a replacement". That is F1's own
> numbering, written before the board chain was fixed; on the board, **F4 is
> `APRAS-48` (the frontend groups UI)** and enforcement is this task. Where
> this spec and F1's forward-looking prose disagree about *which slice*
> enforces, the board wins. Where they disagree about *how* (additive vs
> replacement), §4.1 argues the replacement is exactly equivalent and says
> why. Nothing in F1's own deliverables (catalogue, column, migration,
> resolver) is contradicted.

---

## 1. Scope

**In scope**

1. `deps.require_permission(...)` — the route-level guard — plus
   `deps.has_permission(user, session, permission)`, the in-code predicate
   every other call site uses (§3).
2. The `is_tenant_admin` bridge inside `get_effective_permissions` (§3.3),
   and the explicit answer for `user.role == ADMINISTRATOR` (§3.2).
3. **The swap**: of the **100** actor-role comparisons and **7**
   non-comparison actor-role reads that exist in `app/` at this task's merge
   base (Rule C / Rule N of §8.2, measured — §5), **85 comparisons are
   converted** to permission checks and the remaining **22 reads** (15
   comparisons + 7 non-comparisons) land in one of the three declared,
   reasoned allowlists of §5.3. The per-module subtraction is §5.4.
4. Four **scope permissions** (§4.2) — the only new vocabulary — and the two
   consequent amendments to F1's registry test (§7.1).
5. `tests/matrix_world.py` (the shared harness), `tests/tools/record_parity_baseline.py`
   (the committed generator), `tests/test_permission_parity_matrix.py` and the
   recorded baseline `tests/data/parity_matrix_baseline.json` (§6) — the star
   test and the machinery that makes its baseline **reproducible** rather than
   merely historical.
6. `tests/test_permission_enforcement.py` — the route-walk structural test
   and the AST role-read allowlist test (§8).
7. Anti-escalation on both grant surfaces, plus `permissions` on the three
   `UserType` schemas (§9).
8. Retirement of F1's derived-parity module `tests/test_legacy_role_permissions.py`
   down to its production-independent assertions (§7.2) — forced, and the
   reason is the whole point of the slice.

**Explicitly NOT in scope**

* **No frontend.** Zero files under `frontend/`. `UserTypeRead` gains a key;
  TypeScript interfaces ignore extra keys, and no frontend file is edited.
* **No migration.** `0030_add_user_type_permissions` is F1's and already
  carries the column. `alembic heads` still reports the single head
  `0030_add_user_type_permissions`, and no file is added under
  `alembic/versions/` (next free number would be `0031`; nothing here needs
  DDL). `tests/test_migrations_postgres.py` is **not** touched.
* **No `is_superuser`.** The ADMINISTRATOR-shaped role reads keep their
  **five** surviving sites (`deps.has_admin_capability`,
  `deps._resolve_from_header`, `endpoints/users.py::update_user`,
  `tenant_service::list_tenants`, `tenant_service::get_visible_tenant`), plus
  the two role-only guards `deps.get_current_active_admin` and
  `deps.get_current_admin_or_manager` — the 7 entries of §5.3-A; F3 replaces
  them all. The board's ER-1 carve-out
  ("except those marked for is_superuser") is exactly that allowlist.
* **No widening of `is_tenant_admin` to "all permissions in the tenant"** —
  that is F3's headline (`APRAS-47`), and doing it here would be a real
  divergence for capability holders. §3.3 and §12.1 argue this at length.
* **No group-management UI, no roles endpoint, no per-user loose
  permissions, no role nesting.** Groups become *editable* here (the
  anti-escalation ER requires it); they get a UI in F4.
* **No removal of `allowed_menus`, of `Task.visible_to`, of per-lot linkage
  or of any ownership rule.** Those are object/visibility dimensions, kept in
  code verbatim (§5.2), and F5 owns them.
* **No tightening.** Every route that admits all six roles today still does
  (F1 §11.4's 13 unguarded + the 4 filter-not-refuse ones). The matrix would
  fail if one were tightened.
* **No new domain endpoints, no schema change other than `permissions` on the
  three `UserType` schemas.**

**Dependency.** `APRAS-45` (F1) must be merged first: this slice imports
`PERMISSIONS`, `ROUTE_PERMISSIONS`, `UNGUARDED_ROUTES`,
`LEGACY_ROLE_PERMISSIONS`, `ADMIN_GAP_PERMISSIONS` and
`deps.get_effective_permissions`. `APRAS-38` is already staged in the tree
and is F1's baseline; it is transitively this task's baseline too.

**F1-implementation expectations** (things F2 needs that F1's spec does not
literally promise — flagged here rather than assumed silently):

| # | Expectation | F1 status |
|---|---|---|
| E1 | `ADMIN_GAP_PERMISSIONS` is importable from **production** code, not only from the test module | F1 §6.3 declares it "module-level" inside `tests/test_legacy_role_permissions.py`. **F2 moves it to `app/core/permissions.py`** and the F1 test imports it from there. One-line move, named in §11. |
| E2 | `ROUTE_PERMISSIONS` keys are `(METHOD, APIRoute.path)` with exactly one method per route | Verified on this tree: 190 routes, 190 `(method, path)` keys, no multi-method route. |
| E3 | `get_effective_permissions` tolerates a session with **no** acting tenant (falls back to `DEFAULT_TENANT_ID`) | F1 §8 test 7 pins it. F2 relies on it only for unit-level calls; every production call site runs under `get_current_tenant`. |
| E4 | `PERMISSIONS == set(ROUTE_PERMISSIONS.values())` is an *invariant of F1*, not of the system | F2 amends it to admit `SCOPE_PERMISSIONS` (§7.1). |

---

## 2. Files touched

| File | Change |
|---|---|
| `backend/app/core/permissions.py` | `SCOPE_PERMISSIONS` (4 strings) folded into `PERMISSIONS`; `ADMIN_GAP_PERMISSIONS` moved in from the F1 test (E1); `TENANT_ADMIN_PERMISSIONS` (7 strings, TRANSITIONAL → F3); the 4 scope permissions added to the affected `LEGACY_ROLE_PERMISSIONS` role sets |
| `backend/app/api/deps.py` | `has_permission`, `require_permission` (class `PermissionRequired`); `get_effective_permissions` gains the tenant-admin bridge; `assert_manager_can_see_task` / `assert_can_edit_task` GUEST branches become permission checks (and gain `session` where missing); `get_current_tenant_admin` and `get_current_tenant_admin_or_manager` **deleted** (zero references after the swap) |
| `backend/app/api/v1/endpoints/*.py` (**13 converted**) | every `_assert_*` / `_require_*` helper gains `session` + the permission of the calling route; role-set constants deleted (§5.1). `endpoints/users.py` is edited for §9 but its one role read is **allowlisted**, not converted; `endpoints/user_types.py` has no role read and is edited only for §9 |
| `backend/app/services/*.py` (**13 converted + 2 allowlisted**) | §5.1 names every converted module. `services/task_service.py` (2 reads) and `services/tenant_service.py` (2 reads) carry **only** allowlisted reads (§5.3) and are **not edited at all** |
| `backend/app/schemas/user_type.py` | `permissions` on `UserTypeCreate` / `UserTypeRead` / `UserTypeUpdate` (§9.1) |
| `backend/app/services/user_type_service.py` | **new** — `assert_can_grant` (anti-escalation), used by the user-type routes and by `_assign_user_types` |
| `backend/app/api/v1/endpoints/user_types.py`, `users.py` | wire the anti-escalation check and the `permissions` field |
| `backend/tests/matrix_world.py` | **new** — `MatrixWorld`, `CELLS`, `PATH_PARAMS`, `REQUEST_BODIES` and `run_cell()`; not a test module (pytest does not collect it) so both the test and the recorder import the *same* harness |
| `backend/tests/tools/__init__.py`, `backend/tests/tools/record_parity_baseline.py` | **new** — the committed generator (§6.4); `python -m tests.tools.record_parity_baseline` |
| `backend/tests/test_permission_parity_matrix.py` | **new** — the star test (§6) |
| `backend/tests/data/parity_matrix_baseline.json` | **new** — generated by the recorder at the named merge-base sha (§6.4) |
| `backend/tests/test_permission_enforcement.py` | **new** — structural route walk + AST allowlist (§8) |
| `backend/tests/test_permission_escalation.py` | **new** — anti-escalation (§9.4) |
| `backend/tests/test_permission_registry.py` | **edited (F1 module)** — reachability amended for `SCOPE_PERMISSIONS`; the schema pin updated for `permissions` (§7.1) |
| `backend/tests/test_legacy_role_permissions.py` | **edited (F1 module)** — derived-parity machinery retired, production-independent assertions kept (§7.2) |
| `backend/tests/test_effective_permissions.py` | **edited (F1 module), additive only** — 3 new cases for the bridge (§3.3) |

No other pre-existing test file is edited (§11). No file under `alembic/`.
No file under `frontend/`.

---

## 3. The enforcement primitive

### 3.1 Two shapes, one predicate

```python
# app/api/deps.py

def has_permission(user: User, session: Session, permission: str) -> bool:
    """True when `user` holds `permission` in the session's acting tenant."""
    return permission in get_effective_permissions(user, session)


class PermissionRequired:
    """FastAPI dependency: 403 unless the caller holds `permission`.

    Depends on `get_current_tenant` for the same reason
    `get_current_tenant_admin` did (APRAS-43 §4.2): the acting tenant must be
    resolved before permissions are, router-level dependencies resolve first,
    and a shared sub-dependency is solved once per request, so this is
    self-sufficient and free.
    """

    def __init__(self, permission: str) -> None:
        self.permission = permission

    def __call__(
        self,
        session: Annotated[Session, Depends(get_session)],
        current_user: Annotated[User, Depends(get_current_user)],
        _tenant: Annotated[Tenant, Depends(get_current_tenant)],
    ) -> User:
        if not has_permission(current_user, session, self.permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The user doesn't have enough privileges",
            )
        return current_user


def require_permission(permission: str) -> PermissionRequired: ...
```

`PermissionRequired` is a **class**, not a closure, so §8's route walk can
read `.permission` off `route.dependant` and compare it to
`ROUTE_PERMISSIONS`. It returns the `User`, so a handler signature
`current_user: Annotated[User, Depends(api_deps.get_current_tenant_admin)]`
becomes `Annotated[User, Depends(api_deps.require_permission("users:update"))]`
with no other edit, and the 403 detail is byte-identical to the one it
replaces.

**Where each shape is used, and why it matters.**

* `require_permission` is used on **exactly the 7 routes whose current gate is
  already a route-level `Depends`** (`get_current_tenant_admin` ×6,
  `get_current_tenant_admin_or_manager` ×1). There, and only there, moving the
  check into the dependency tree preserves ordering: FastAPI solves
  sub-dependencies **before** it raises body-validation errors, so a gate that
  is a dependency today must stay a dependency, and a gate that runs *inside*
  the handler today must stay inside the handler — otherwise a denied caller
  sending an invalid body flips `422 → 403`, and a denied caller naming a
  missing object flips `404 → 403`. Both are divergences the matrix of §6
  would catch, and both are avoided by construction.
* `has_permission` is used everywhere else, **in place**, under the rule of
  §4.1: same function, same line, same exception class, same detail string —
  only the condition changes.

Placement: both live in `app/api/deps.py`, beside
`get_effective_permissions` and `get_effective_user_type_ids`.
`app/core/permissions.py` must stay database-free (F1 §5.1), and services
already import from `app.api.deps` (`task_service` imports
`get_effective_user_type_ids`), so no new import direction is created and no
cycle is possible (`deps` imports no service).

**No caching.** `get_effective_permissions` runs 1–2 SELECTs and a route may
call it 2–4 times. A request-scoped memo is tempting and is deliberately
*not* added: the `client` fixture reuses one `Session` across requests, so a
`session.info` cache would go stale the moment a test edits a group and
re-requests. Correctness first. **No suite-runtime ceiling is imposed by this
spec** — a wall-clock number measured on one machine is not a reviewable
acceptance criterion, and the only structure that could plausibly blow the
runtime up (a rebuilt world per matrix cell) is forbidden outright by §6.2,
which pins exactly one isolation mechanism and offers no fallback.

### 3.2 `user.role == ADMINISTRATOR` needs no short-circuit at all

This is the one place where F1 did more work than it advertised.
`LEGACY_ROLE_PERMISSIONS[ADMINISTRATOR]` is already *exactly*
`PERMISSIONS - ADMIN_GAP_PERMISSIONS` — every permission except
`packages:my_lots_read`, which `PackageService.get_my_lots` denies to
administrators on purpose (F1 §4.19, §11.5). So:

* an ADMINISTRATOR resolves, through the ordinary union in
  `get_effective_permissions`, to precisely the set that reproduces today's
  behaviour, **including the one gap**;
* a hand-written `if user.role == ADMINISTRATOR: return PERMISSIONS`
  short-circuit would be a *widening* — it would grant
  `packages:my_lots_read` to ADMINISTRATOR (and, once the same shortcut is
  reused, to DIRECTOR/MANAGER/PORTEIRO through the gatekeeper branch), turning
  today's 403 on `GET /packages/my-lots` into a 200. The matrix cell
  `(ADMINISTRATOR, GET /api/v1/packages/my-lots)` is the test that fails.

Therefore **F2 adds no ADMINISTRATOR branch**. The legacy map *is* the
short-circuit, and it is the correct one. F3 replaces the map's
ADMINISTRATOR row with `is_superuser` and must decide the
`packages:my_lots_read` gap explicitly — which is exactly what F1's
`test_admin_gap_list_is_exact` was built to force.

The five residual ADMINISTRATOR reads that are *not* about permissions —
tenant visibility (**two** sites: `list_tenants` and `get_visible_tenant`),
header resolution (`_resolve_from_header`), the `PATCH /users/{id}` escalation
rules (`update_user`) and `has_admin_capability` — survive in the §5.3-A
allowlist, together with the two role-only guards that no permission can
replace on a global route: 7 entries in all.

### 3.3 The `is_tenant_admin` bridge — narrow on purpose

`get_effective_permissions` gains one branch, and F1's ER-5 ("no
`is_tenant_admin` shortcut") is explicitly superseded here — without it a
RESIDENT holding the capability loses `DELETE /lots/{id}` and
`tests/test_tenant_admin.py::test_tenant_admin_passes_every_admin_gated_route_in_their_tenant`
fails.

```python
# app/core/permissions.py
# TRANSITIONAL (IAM F2 -> F3). Exactly the seven tenant-scoped admin routes
# APRAS-43 swapped to `get_current_tenant_admin` / `_or_manager`. F3 replaces
# this constant with "every permission of the acting tenant".
TENANT_ADMIN_PERMISSIONS: frozenset[str] = frozenset({
    "tasks:delete", "lots:delete",
    "users:update", "users:update_contact",
    "user_types:create", "user_types:update", "user_types:delete",
})
```

```python
# app/api/deps.py, inside get_effective_permissions
if is_acting_tenant_admin(user, session):
    permissions |= TENANT_ADMIN_PERMISSIONS
```

* It reads the **capability**, never a role, so it adds no role read.
* It is bounded by `is_acting_tenant_admin`, which has no
  `DEFAULT_TENANT_ID` fallback: on a global route (`/api/v1/tenants`), in
  `app/seed.py` or in a unit-test `Session` it grants nothing. That is what
  keeps `test_every_tenant_write_is_403_for_a_tenant_admin` green.
* It is **not** "all permissions in the tenant". Making it so here would let
  a RESIDENT tenant_admin `POST /finance/categories` (403 today), which is a
  divergence for capability holders even though the six-role matrix cannot
  see it. F3 is the slice whose title is that widening; when it lands, the
  one-line change is `permissions |= PERMISSIONS - ADMIN_GAP_PERMISSIONS` (or
  whatever F3 decides about the gap), and the anti-escalation rule of §9
  widens with it automatically because it is expressed in terms of the
  author's *effective* permissions. See §12.1 for the argument against doing
  it now.
* `test_tenant_admin_permissions_are_exactly_the_apras43_routes` asserts
  `TENANT_ADMIN_PERMISSIONS == {ROUTE_PERMISSIONS[k] for k in APRAS43_ADMIN_ROUTES}`
  over the seven `(method, path)` keys spelled out in the test, so the
  constant cannot drift from the routes it is meant to reproduce.

Three additive cases land in `tests/test_effective_permissions.py`: the
capability adds exactly those seven; it adds nothing on a session with no
acting tenant; it adds nothing in a tenant that did not grant it. No existing
case in that module changes (F1's cases use users with no capability).

---

## 4. The conversion rule

### 4.1 Swap the predicate, keep the shape

For every converted site:

```python
-    if current_user.role not in _FINANCE_ADMIN_ROLES:
+    if not has_permission(current_user, session, permission):
         raise FinanceAccessForbiddenError(
             "Only ADMINISTRATOR and DIRECTOR can perform this action"
         )
```

Same function, same position in the function, same exception class, same
message, same resulting status code. The helper gains `session` and a
`permission` parameter; each call site passes **its own route's permission**
from `ROUTE_PERMISSIONS` — which is why a helper shared by twelve routes
(`documents._assert_not_porteiro`) does not collapse twelve permissions into
one.

**Why replacement is exact, and why "additive" (role AND permission) is not
needed.** For every converted site, F1 proved
`perm ∈ LEGACY_ROLE_PERMISSIONS[role] ⟺ role passes that gate` (its parity
test, green at the merge base). `get_effective_permissions` returns
`LEGACY_ROLE_PERMISSIONS[user.role] ∪ (role-bundle permissions) ∪ (bridge)`.
Nothing seeds a bundle (F1 §7.4 asserts every `user_type.permissions` is
`[]`), so at merge time the union collapses to the legacy set and the new
condition is *pointwise identical* to the old one. The union can only ever
widen, and only after an administrator deliberately writes permissions onto a
group — which is the feature. An additive `role AND permission` would be
indistinguishable today and would keep `user.role` load-bearing, which is the
one thing this slice exists to end.

### 4.2 `SCOPE_PERMISSIONS` — the only new vocabulary, and why four

Most object-dimension staff bypasses map onto a route permission whose legacy
role set is *already exactly right*, and those are reused rather than
invented (§5.1: `purchases:decide`, `reservations:approve`, `feedback:respond`,
`announcements:create`, `documents:folder_create`, `uploads:approve`,
`packages:queue_read`, `gate:checkin`, `assets:update`,
`finance:transaction_delete`). Four bypasses have **no** route permission
with the right role set in the right module, and forcing one (gating
"see every lot's residents" on `assets:read` because both happen to be
`{A,D,M}`) would be nonsense that silently breaks the day someone edits
`assets:read`:

| Scope permission | Legacy roles | Replaces |
|---|---|---|
| `residents:read_any_lot` | A D M | `ResidentService._check_lot_access` staff bypass |
| `visitors:manage_any_lot` | A D M | `VisitorService._check_lot_access`, `get_user_linked_lot_ids`, `revoke_authorization`, `get_access_logs` staff bypasses (one predicate, four sites, all the same `{A,D,M}` tuple today) |
| `occurrences:manage_all` | A D | `occurrence_service` A/D branches: see every occurrence, see internal-only timeline entries, unmask anonymous reporters, update status without being assigned |
| `uploads:auto_approve` | A D M | `MediaService.upload_photo`'s auto-approval branch — a real privilege (publishing without review), not a display rule |

They are **not** route-mapped, which is exactly why F1's
`test_every_catalogue_permission_is_reachable` must be amended (§7.1) rather
than quietly satisfied. Each carries an inline comment naming the production
site it replaces, and each gets a `LEGACY_ROLE_PERMISSIONS` entry (A and D get
all four; M gets all but `occurrences:manage_all`).

Deliberately **not** introduced: a `{PORTEIRO}` permission for the gate
carve-out (§5.1 shows `gate:checkin` reproduces it exactly), a
`{MANAGER}` permission for any own-row narrowing (each is expressed as
"lacks the staff permission", which is exact because the enclosing gate has
already excluded everyone below MANAGER), and any `occurrences:read_assigned`
for the MANAGER visibility tier (that tier is a *visibility model*, §5.2).

---

## 5. The complete inventory of role reads

### 5.0 The measured baseline

The counting rule is defined **once**, in §8.2 (Rule C for comparison reads,
Rule N for non-comparison reads, with the exact AST node classes, the operand
shape and the module scope). Every number in this section is that rule, run by
the walker of §8.2, and nothing else. Run it yourself with:

```bash
cd backend && python3 - <<'PY'
import ast, pathlib
ACTORS = {"current_user", "user", "admin_user"}
def is_actor_role(n):
    return (isinstance(n, ast.Attribute) and n.attr == "role"
            and isinstance(n.value, ast.Name) and n.value.id in ACTORS)
c = n = 0
for p in sorted(pathlib.Path("app").rglob("*.py")):
    rel = p.relative_to("app").as_posix()
    if rel.startswith(("models/", "schemas/")) or rel == "seed.py":
        continue
    tree = ast.parse(p.read_text())
    in_cmp = set()
    for x in ast.walk(tree):
        if isinstance(x, ast.Compare):
            hits = [m for m in ast.walk(x) if is_actor_role(m)]
            if hits:
                c += 1
            in_cmp.update(id(m) for m in hits)
    n += sum(1 for x in ast.walk(tree) if is_actor_role(x) and id(x) not in in_cmp)
print("Rule C:", c, "Rule N:", n, "total:", c + n)
PY
```

**Measured at this task's merge base** (the tree with `APRAS-38` and
`APRAS-45` present — i.e. the sha this branch is cut from):

```
Rule C: 100   Rule N: 7   total: 107
```

The same command against `git show fdd79a2` (APRAS-38 alone, before F1) gives
`Rule C: 100, Rule N: 6`: **F1 adds exactly one** actor-role read,
`deps.get_effective_permissions`'s `LEGACY_ROLE_PERMISSIONS.get(user.role, …)`
(Rule N), and **no** comparison. The Rule-C baseline is therefore stable across
the F1 merge, which is what lets §5.4's arithmetic be checked against either
tree.

Earlier drafts of this spec quoted "110". That number was wrong and is
retracted; 100/7 is what the stated rule measures, and §5.4 itemises the
subtraction so `baseline − converted == survivors` is checkable arithmetic
rather than a claim.

Every one of the 107 is classified below: 85 Rule-C reads are converted
(§5.1), 15 Rule-C reads and all 7 Rule-N reads survive in the three allowlists
of §5.3, and §5.2 names the *object*-dimension logic that is preserved
verbatim. §8.2's AST test asserts the survivors are *exactly* §5.3 — a new
read fails, a removed read fails.

### 5.1 Converted — route gates and staff bypasses

**Route-level `Depends` → `require_permission` (7 routes, the only use of the dependency form)**

| Route | Was | Becomes |
|---|---|---|
| `DELETE /api/v1/tasks/{task_id}` | `get_current_tenant_admin` | `require_permission("tasks:delete")` |
| `DELETE /api/v1/lots/{lot_id}` | idem | `require_permission("lots:delete")` |
| `PATCH /api/v1/users/{user_id}` | idem | `require_permission("users:update")` |
| `POST /api/v1/user-types/` | idem | `require_permission("user_types:create")` |
| `PATCH /api/v1/user-types/{id}` | idem | `require_permission("user_types:update")` |
| `DELETE /api/v1/user-types/{id}` | idem | `require_permission("user_types:delete")` |
| `PATCH /api/v1/users/{id}/contact-info` | `get_current_tenant_admin_or_manager` | `require_permission("users:update_contact")` |

Both deleted guards then have zero references and are removed from `deps.py`.
`get_current_active_admin` (5 global `/api/v1/tenants` writes) and
`get_current_admin_or_manager` (no route) **stay**, untouched — the
is_superuser carve-out of §5.3-A, which is also what keeps
`tests/test_tenant_admin.py` §9 passing unmodified.

**Endpoint-module helpers → `has_permission` with the calling route's permission**

`n` is the number of **Rule-C** reads (§8.2) the row removes, at the source
lines named. The column sums to 22 for this table and is reconciled per module
in §5.4.

| Module | Helper(s) deleted/converted | n | Permission per call site |
|---|---|---|---|
| `endpoints/categories.py` | `_require_category_write_permission` (l.23), `_CATEGORY_WRITE_ROLES` | 1 | `categories:create` / `:update` / `:delete` |
| `endpoints/lots.py` | `_require_lot_read_permission` (l.35), `_require_lot_write_permission` (l.44), `_LOT_READ_ROLES`, `_LOT_WRITE_ROLES` | 2 | `lots:read`, `lots:create`/`:update`/`:link_user`/`:unlink_user` |
| `endpoints/finance.py` | `_require_read_permission` (l.50), `_require_admin_permission` (l.55), `_require_write_permission` (l.62), `_FINANCE_*_ROLES` | 3 | `finance:read`; `finance:category_create`/`:category_update`/`:budget_*`/`:transaction_delete`; `finance:transaction_create`/`:invoice_upload`/`:invoice_delete` |
| `endpoints/finance.py` | `_require_transaction_edit_permission` (l.71, l.74) | 2 | `has_permission("finance:transaction_delete")` (A/D) **or** `transaction.created_by_id == user.id` — the MANAGER own-row narrowing, now expressed as "lacks the finance-admin permission", exact because the route already excluded everyone below MANAGER |
| `endpoints/finance.py` | `include_inactive=true` narrowing in `list_categories` (l.97) | **0** | reads no role of its own — it *calls* `_require_admin_permission`, so it converts to `finance:category_create` for free. Listed because it is a behaviour a reviewer will look for, not because it is a read |
| `endpoints/projects.py` | `_require_read_permission` (l.45), `_require_admin_permission` (l.52), `_require_update_permission` (l.59), `_PROJECT_*_ROLES` | 3 | `projects:read`/`:summary`… per route (`projects:create`, `:update`, `:delete`, `:milestone_*`, `:update_create`, `:update_delete`) |
| `endpoints/reservations.py` | `_require_space_write_permission` (l.34), `_require_non_guest` (l.43), `_SPACE_WRITE_ROLES` | 2 | `spaces:create`/`:update`/`:deactivate`; `reservations:read`/`:create`/`:cancel` |
| `endpoints/residents.py` | `assert_admin_or_director` (l.28) | 1 | `residents:create`/`:update`/`:delete`/`:link_user`/`:unlink_user` |
| `endpoints/access_logs.py` | `_assert_gatekeeper_access` (l.26) | 1 | `gate:checkin` / `gate:checkout` |
| `endpoints/voting.py` | `_require_voting_access` (l.44), `_NO_ACCESS_ROLES` | 1 | `assemblies:read`, `votes:read`, `votes:my_ballot_read`, `votes:eligible_lots_read` per route |
| `endpoints/documents.py` (l.26), `announcements.py` (l.31), `occurrences.py` (l.28), `authorizations.py` (l.30) | the four `_assert_not_porteiro` copies | 4 | the route's own permission (`documents:read`, `:download`, `:folder_read`, …; `announcements:read`, `:comment_delete`, `:mark_read`, …; `occurrences:read`, `:create`, `:update_status`, `:add_note`; `authorizations:read`, `:create`, `:revoke`) |
| `endpoints/tasks.py` | inline `role == GUEST` in `create_task` (l.30) | 1 | `tasks:create`, same `ForbiddenError("Guests cannot create tasks")` |
| `endpoints/tasks.py` | inline `role == GUEST` in `list_tasks` (l.52) | 1 | `if not has_permission(..., "tasks:read"): return []` — **the `return []` shape is kept**; turning it into a 403 is a divergence the matrix rejects |
| | **total** | **22** | |

**Service-module gates**

Same `n` column. It sums to 63 for this table (60 in `app/services/`, 3 in
`app/api/deps.py`); 22 + 63 = **85 converted**.

| Module | Site | n | Permission |
|---|---|---|---|
| `services/asset_service.py` | `_STAFF_ROLES` ×3 (`create_asset` l.42, `update_asset` l.222, `delete_asset` l.255), `_VIEW_ROLES` ×5 (`list_assets` l.95, `get_asset_summary` l.143, `get_asset_by_id` l.174, `record_movement` l.275, `list_inventory_movements` l.356) | 8 | `assets:create`/`:update`/`:delete`; `assets:read`/`:summary_read`/`:movement_record`/`inventory:movements_read` |
| `services/asset_service.py` | MANAGER movement-type restriction (l.278) | 1 | `not has_permission("assets:update")` and `movement_type in {AJUSTE_INVENTARIO, BAIXA_PATRIMONIAL}` — exact: the enclosing `_VIEW_ROLES` gate leaves only `{A,D,M}`, minus `assets:update`'s `{A,D}` = `{M}` |
| `services/purchase_service.py` | `_assert_can_view` (l.56), `_assert_can_decide` (l.63), `_WRITE_ROLES` ×2 (`create_request` l.215, `add_quote` l.511) | 4 | `purchases:read`/`:summary_read`; `purchases:decide` (and `purchases:cancel`, decide-level today — F1 §11.3); `purchases:create`/`:quote_create` |
| `services/purchase_service.py` | `_assert_can_write_request` (l.72, l.74) / `_assert_can_write_quote` (l.89, l.91) — the decide-level short-circuit **and** the MANAGER branch in each | 4 | `has_permission("purchases:decide")` short-circuit, else own-row + OPEN-status narrowing, messages verbatim |
| `services/reservation_service.py` | `_STAFF_ROLES` ×4 (`list_reservations` l.241, `get_reservation` l.282, `decide_reservation` l.298, `cancel_reservation` l.337) | 4 | `reservations:approve` |
| `services/feedback_service.py` | A/D ×4 (`_build_feedback_read` l.23, `list_feedback` l.97, `get_feedback` l.129, `respond_to_feedback` l.162) | 4 | `feedback:respond` |
| `services/announcement_service.py` | `_check_publisher` (l.49); the inline `is_publisher = user.role in (A, D)` **in `delete_comment`** (l.320) — there is no `is_publisher` *function*; the GUEST branch in `add_comment` (l.287) | 3 | `announcements:create`/`:update`/`:delete`/`:media_*`/`:read_receipts_read` per call site; `announcements:create` for the comment-delete publisher branch; `announcements:comment` for the GUEST branch |
| `services/document_service.py` | `_check_admin_or_director` (l.29), A/D bypass in `get_accessible_folder_ids` (l.35) | 2 | `documents:create`/`:delete`/`:version_create`/`:folder_create`/`:folder_update`/`:folder_delete`; `documents:folder_create` for the all-folders bypass. **The `role_str` line (l.39) is not touched** — it is the per-folder ACL and survives under Rule N, §5.3-B |
| `services/media_service.py` | `list_pending_photos` (l.146), `approve_photo` (l.174), `reject_photo` (l.196), `delete_photo` (l.223) | 4 | `uploads:pending_read`, `uploads:approve`, `uploads:reject`, `uploads:approve` (delete-any branch, owner branch unchanged) |
| `services/media_service.py` | auto-approve branch in `upload_photo` (l.108) | 1 | `uploads:auto_approve` (§4.2) |
| `services/access_control_service.py` | `_assert_admin_or_director` (l.37), `_assert_admin_director_or_manager` (l.42) | 2 | `access_control:device_create`/`:device_update_status`/`:device_regenerate_key`/`:facial_template_sync`; `access_control:devices_read`/`:facial_template_read`/`:events_read` |
| `services/voting_service.py` | `_assert_board` (l.88), `BOARD_ROLES` | 1 | `assemblies:create`/`:update`/`:close`/`:minutes_read`/`:minutes_save`, `lots:set_delinquency` per call site |
| `services/voting_service.py` | `_assert_can_create_vote` (l.97, `TALLY_STAFF_ROLES`; the `ASSEMBLEIA` arm delegates to `_assert_board` and reads nothing of its own) | 1 | `votes:create` (also `:update`, `:close`) for `ENQUETE`; `assemblies:create` for `ASSEMBLEIA` — the payload-dependent narrowing stays in code |
| `services/voting_service.py` | `_assert_can_manage_eligibility` (l.105) | 1 | `votes:eligibility_read` / `votes:eligibility_manage` |
| `services/voting_service.py` | `_assert_can_view_tally` staff branch (l.111) + `NON_VOTING_ROLES` branch (l.113) | 2 | `votes:tally_read` for the staff short-circuit; the non-voting refusal becomes `not has_permission("votes:cast")`; the eligible-lot branches stay |
| `services/voting_service.py` | `NON_VOTING_ROLES` in `_assert_can_cast` (l.341) — **one** site, not two: `retract` reaches it through the same call (l.451, `is_retraction=True`) | 1 | `votes:cast` for the cast path and `votes:retract` for the retraction path, chosen from `is_retraction`; the `BallotRejection` row is still written |
| `services/visitor_service.py` | `_check_lot_access` (l.63), `get_user_linked_lot_ids` (l.100), `revoke_authorization` (l.298), `get_access_logs` (l.464) staff bypasses | 4 | `visitors:manage_any_lot` (§4.2) |
| `services/visitor_service.py` | `role != PORTEIRO` in `get_authorization_for_user` (l.287) | 1 | `not has_permission("gate:checkin")` — exact and *better*: `gate:checkin` is `{A,D,M,P}`, and A/D/M were already bypassing inside `_check_lot_access`, so the composed outcome is unchanged while one branch disappears |
| `services/resident_service.py` | `_check_lot_access` staff bypass (l.29) | 1 | `residents:read_any_lot` (§4.2) |
| `services/package_service.py` | `_assert_gatekeeper_role` (l.78) | 1 | `packages:create` / `packages:queue_read` per call site |
| `services/package_service.py` | `_assert_lot_access` gatekeeper bypass (l.86) + GUEST branch (l.88) | 2 | `packages:queue_read` for the bypass; the GUEST refusal becomes `not has_permission(<route permission>)` (`packages:read` or `packages:pickup`), keeping the empty-detail `PackageAccessForbiddenError()` |
| `services/package_service.py` | `get_my_lots` inverted gate (l.205, l.209) | 2 | `has_permission("packages:queue_read")` → the "Use /packages/queue…" message; then `not has_permission("packages:my_lots_read")` → the bare refusal. Both messages preserved, both branches role-free |
| `services/occurrence_service.py` | A/D branches ×**6** of the module's 8 reads: `_build_occurrence_read` (l.41), `_check_user_access` (l.100), `get_occurrences` (l.171), `get_occurrence_by_id` (l.234), `update_occurrence_status` (l.289), `add_timeline_note` (l.361). The two MANAGER-tier reads (l.102, l.172) **survive**, §5.3-B | 6 | `occurrences:manage_all` (§4.2) |
| `deps.assert_manager_can_see_task` (l.308) / `assert_can_edit_task` (l.332) | GUEST branches only; the MANAGER branches at l.310 / l.334 survive (§5.3-B) | 2 | `tasks:read` / `tasks:update` (the functions gain `session` where they lack it) |
| `deps.get_current_tenant_admin_or_manager` (l.478) | the whole guard is **deleted** (§5.1 route table) | 1 | — |
| | | **63** | |

### 5.2 Preserved verbatim — object and visibility dimensions

Not converted, not touched, and *named* so a reviewer can see they were
considered: `UserType.allowed_menus` (`assert_menu_access`),
`Task.visible_to` filtering and the unassigned/self-assigned edit rule,
`UserLotLink` / `Resident` per-lot narrowing, every ownership/authorship
check (own feedback, own occurrence, own comment, own reservation, own photo,
own purchase request, own transaction), `DocumentFolder.allowed_roles_json`,
and the payload-dependent narrowings (`VoteKind.ASSEMBLEIA`,
`include_inactive`, MANAGER movement types). F1 §6.2 excluded all of these
from the catalogue on purpose; F5 owns them.

**This is what "special scopes preserved" means mechanically**: a RESIDENT
still reaches `GET /packages` only for their linked lots, because
`_assert_lot_access` still calls `get_user_linked_lot_ids` after the
permission check; a PORTEIRO is still condo-wide at the gate, because
`gate:checkin` (its own permission) is what now bypasses the lot check in
`get_authorization_for_user`, and `_assert_gatekeeper_access` still admits it
on check-in/check-out. `tests/test_packages_rbac.py`, `test_packages.py`,
`test_gatekeeper.py`, `test_porteiro_role.py`, `test_visitors_rbac.py`,
`test_authorizations.py` and `test_residents_rbac.py` pass **unmodified**.

### 5.3 The three allowlists — role reads that survive

Two module-level literals in `tests/test_permission_enforcement.py`, each
mapping `"<path relative to app/>::<function>"` → `(count, slice, reason)`:

* `ROLE_READS_COMPARE` — must equal the **Rule C** walk exactly (15 reads,
  15 functions);
* `ROLE_READS_NON_COMPARE` — must equal the **Rule N** walk exactly (7 reads,
  5 functions).

A new read fails, a removed read fails, a moved read fails. Every entry
carries a non-empty `reason`; `test_every_allowlisted_role_read_has_a_reason`
enforces that, and `slice` must be `"F3"` or `"F5"`.

Line numbers below are as at this task's merge base (APRAS-38 + APRAS-45); the
tests key on `module::function`, never on a line, so an unrelated edit above a
site does not break them.

**A. is_superuser-marked / global scope (F3 replaces them)** — 7 entries, 7 Rule-C reads:

| Site | n | Why it survives |
|---|---|---|
| `api/deps.py::get_current_active_admin` (l.105) | 1 | still guards the 5 global `/api/v1/tenants` writes; no acting tenant exists there, so no permission is resolvable. F3. |
| `api/deps.py::get_current_admin_or_manager` (l.128) | 1 | no route uses it; kept so `test_tenant_admin.py::test_the_role_only_guards_stay_available_and_unchanged` stays unmodified. F3 removes both together. |
| `api/deps.py::has_admin_capability` (l.183) | 1 | feeds the menu gate and the §3.3 bridge. F3. |
| `api/deps.py::_resolve_from_header` (l.367) | 1 | "an ADMINISTRATOR may act in any tenant" + the 404/403 existence oracle (APRAS-42). F3. |
| `api/v1/endpoints/users.py::update_user` (l.101) | 1 | the three escalation rules for non-global-administrators (APRAS-43 §6.3). The *target*-role reads (`user_in.role`, `db_user.role`) are payload/target reads and are outside both rules by construction — the operand's base `Name` is not in `ACTOR_NAMES`. F3 for the actor read; F5 for the target ones. |
| `services/tenant_service.py::list_tenants` (l.138) | 1 | tenant visibility on the global `GET /api/v1/tenants` list. F3. |
| `services/tenant_service.py::get_visible_tenant` (l.196) | 1 | the same rule for `GET /api/v1/tenants/{id}` — **this is the second tenant-visibility site.** Earlier drafts named `get_tenant_for_user`, which does not exist in `tenant_service.py`; it is `get_visible_tenant`. F3. |

**B. Object / visibility dimension (F5 owns)** — 7 entries, 7 Rule-C reads:

| Site | n | Why it survives |
|---|---|---|
| `api/deps.py::assert_manager_can_see_task` (l.310) | 1 | the MANAGER `visible_to` tier. Its GUEST branch (l.308) is converted. |
| `api/deps.py::assert_can_edit_task` (l.334) | 1 | the MANAGER own/unassigned-task rule. Its GUEST branch (l.332) is converted. |
| `api/v1/endpoints/tasks.py::list_tasks` (l.87) | 1 | the MANAGER `visible_to` query filter. Its GUEST branch (l.52) is converted. |
| `services/task_service.py::create_task` (l.36) | 1 | MANAGER `visible_to` defaulting. Module **not edited** by this slice. |
| `services/task_service.py::update_task` (l.75) | 1 | MANAGER `visible_to` subset rule. Module **not edited** by this slice. |
| `services/occurrence_service.py::_check_user_access` (l.102) | 1 | the MANAGER visibility tier between "all" and "own+public". Its A/D branch (l.100) is converted. |
| `services/occurrence_service.py::get_occurrences` (l.172) | 1 | the same tier as a query filter. Its A/D branch (l.171) is converted. |

**C. Non-comparison reads (Rule N)** — 5 entries, 7 reads, all F5:

| Site | n | Why it survives |
|---|---|---|
| `services/document_service.py::get_accessible_folder_ids` (l.39) | **3** | one physical line — `role_str = user.role.value if hasattr(user.role, "value") else str(user.role)` — contains **three** actor-role attribute nodes, and Rule N counts nodes, not lines. `role_str` is matched against the folder's stored `allowed_roles_json`: a data-driven per-folder ACL, the object dimension of §5.2. F5. |
| `api/deps.py::get_effective_permissions` (l.251) | 1 | `LEGACY_ROLE_PERMISSIONS.get(user.role, …)` — **F1's own resolver**, and the single read F1 added. It is not an authorization decision; it is the transitional map that *produces* permissions. F5 deletes it with the legacy map. |
| `api/v1/endpoints/lots.py::link_user_to_lot` (l.153) | 1 | serialisation only: `UserSummaryRead(…, role=user.role)`. No branch, no decision. F5 (dies when `User.role` dies). |
| `services/lot_service.py::get_lot_detail` (l.111) | 1 | same serialisation into `UserSummaryRead`. F5. |
| `services/tenant_service.py::_to_member_read` (l.329) | 1 | same serialisation into `TenantMemberRead`. F5. |

These three serialisation reads are in the allowlist not because they are
interesting but because an *exact-match* test cannot have an "obviously fine"
category. They are cheap to carry and they make the walker's rule uniform.

**D. The one read that is neither A nor B: `deps.get_effective_user_type_ids`** —
1 entry, 1 Rule-C read, F5:

| Site | n | Why it survives |
|---|---|---|
| `api/deps.py::get_effective_user_type_ids` (l.213) | 1 | `select(UserType).where(UserType.role == user.role, …)` — the **role-implicit `UserType` resolution** that `get_effective_permissions` itself is built on. Converting it is impossible and would be circular: it is what turns a role into the group whose `permissions` are read. It is not an authorization decision and is not is_superuser-shaped, so it belongs to neither A nor B; it is retired in **F5**, when `User.role` stops existing and group membership becomes explicit. Earlier drafts omitted it entirely, which is why their exact-match test could not have passed. |

`app/seed.py`, `app/models/` and `app/schemas/` are excluded from the walk
(§8.2); none is an authorization path.

### 5.4 The subtraction, per module

`baseline − converted == survivors`, module by module, under Rule C. Every
number is produced by the §5.0 command; the `converted` column is the `n`
column of §5.1 aggregated per module.

| Module | Rule-C baseline | converted (§5.1) | survivors (§5.3) |
|---|---:|---:|---:|
| `api/deps.py` | 10 | 3 | 7 (A×4, B×2, D×1) |
| `api/v1/endpoints/access_logs.py` | 1 | 1 | 0 |
| `api/v1/endpoints/announcements.py` | 1 | 1 | 0 |
| `api/v1/endpoints/authorizations.py` | 1 | 1 | 0 |
| `api/v1/endpoints/categories.py` | 1 | 1 | 0 |
| `api/v1/endpoints/documents.py` | 1 | 1 | 0 |
| `api/v1/endpoints/finance.py` | 5 | 5 | 0 |
| `api/v1/endpoints/lots.py` | 2 | 2 | 0 |
| `api/v1/endpoints/occurrences.py` | 1 | 1 | 0 |
| `api/v1/endpoints/projects.py` | 3 | 3 | 0 |
| `api/v1/endpoints/reservations.py` | 2 | 2 | 0 |
| `api/v1/endpoints/residents.py` | 1 | 1 | 0 |
| `api/v1/endpoints/tasks.py` | 3 | 2 | 1 (B) |
| `api/v1/endpoints/users.py` | 1 | 0 | 1 (A) |
| `api/v1/endpoints/voting.py` | 1 | 1 | 0 |
| `services/access_control_service.py` | 2 | 2 | 0 |
| `services/announcement_service.py` | 3 | 3 | 0 |
| `services/asset_service.py` | 9 | 9 | 0 |
| `services/document_service.py` | 2 | 2 | 0 |
| `services/feedback_service.py` | 4 | 4 | 0 |
| `services/media_service.py` | 5 | 5 | 0 |
| `services/occurrence_service.py` | 8 | 6 | 2 (B) |
| `services/package_service.py` | 5 | 5 | 0 |
| `services/purchase_service.py` | 8 | 8 | 0 |
| `services/reservation_service.py` | 4 | 4 | 0 |
| `services/resident_service.py` | 1 | 1 | 0 |
| `services/task_service.py` | 2 | 0 | 2 (B) |
| `services/tenant_service.py` | 2 | 0 | 2 (A) |
| `services/visitor_service.py` | 5 | 5 | 0 |
| `services/voting_service.py` | 6 | 6 | 0 |
| **total** | **100** | **85** | **15** |

Rule N is untouched by this slice: **7 baseline − 0 converted == 7 survivors**
(§5.3-C). Grand total of surviving actor-role reads: **22**.

`test_role_read_arithmetic_closes` asserts exactly this in code:
`rule_c_baseline_constant == 100`, `sum(ROLE_READS_COMPARE.values()) == 15`,
`sum(ROLE_READS_NON_COMPARE.values()) == 7`, and the walked totals equal the
allowlists. The `100` is a module constant with the merge-base sha beside it,
so if a *future* slice changes the baseline the constant has to be changed
deliberately.

---

## 6. The parity matrix — the star test

`backend/tests/matrix_world.py` (harness),
`backend/tests/tools/record_parity_baseline.py` (generator) and
`backend/tests/test_permission_parity_matrix.py` (the assertions). The harness
lives in its own non-test module precisely so the generator and the test run
**identical** code; a baseline produced by a second implementation of the
world would prove nothing.

### 6.1 Generation

Mechanical, from `app.main.app` and `ROUTE_PERMISSIONS`:

```python
CELLS = [
    (role, method, path)
    for (method, path) in sorted(ROUTE_PERMISSIONS)      # 180 keys
    for role in sorted(UserRole, key=lambda r: r.value)  # 6 roles
]                                                        # 1080 cells
```

The 10 `UNGUARDED_ROUTES` are excluded, with the reason spelled out in the
module docstring: eight are unauthenticated (`/`, `/health`, login, signup,
forgot/reset-password, the two dev helpers), `GET /auth/me` is strictly
self-scoped, and the device webhook authenticates an `X-Device-Key` and no
user — none of them makes a role-dimension authorization decision.
`test_matrix_covers_every_permission_mapped_route` asserts
`{(m, p) for _, m, p in CELLS} == set(ROUTE_PERMISSIONS)` and
`len(CELLS) == 6 * len(ROUTE_PERMISSIONS)`, so the matrix cannot silently
shrink.

Two mechanical completeness tests keep the harness honest:

* `test_every_path_parameter_has_a_binding` — every `{name}` appearing in any
  matrix path has an entry in `PATH_PARAMS`, bound to a `MatrixWorld` id.
* `test_every_write_route_has_a_request_body` — every **POST / PUT / PATCH**
  cell has an entry in `REQUEST_BODIES`. Measured on `ROUTE_PERMISSIONS`, the
  180 keys are `GET 67, POST 58, PUT 19, PATCH 12, DELETE 24` — **113 non-GET,
  of which 89 are POST/PUT/PATCH**. The 24 DELETE routes take no body and are
  explicitly excluded from this test (sending one to a `DELETE` handler that
  declares no body model is harmless but pointless; requiring one would make
  the test unsatisfiable). **A missing body is not allowed to default to
  `{}`**: an invalid body produces a 422 that would mask the authorization
  answer for the *allowed* roles and make the baseline meaningless.
  `test_request_bodies_covers_exactly_the_write_routes` asserts
  `set(REQUEST_BODIES) == {(m, p) for (m, p) in ROUTE_PERMISSIONS if m in {"POST", "PUT", "PATCH"}}`
  and `len(REQUEST_BODIES) == 89`, so the map can neither miss a route nor
  carry a stale one.

**If a harness gap is found mid-implementation, re-record — never hand-edit.**
A missing or wrong `REQUEST_BODIES` entry, a missing `PATH_PARAMS` binding or a
`MatrixWorld` object that turns out to be needed is a *harness* defect, and it
is fixed the same way whether it surfaces before or after the swap: fix
`tests/matrix_world.py`, then **re-run `_meta.regenerate`** (§6.4) — which
records against a clean worktree at the unchanged `merge_base_sha` with only
the new harness copied in — and take its output as the new committed baseline.
Hand-editing the JSON, relaxing an assertion, or letting a cell answer `422`
because the body map was incomplete are all forbidden: the file must stay a
pure function of the harness and the merge-base tree.

### 6.2 `MatrixWorld` — every non-role dimension neutralised

The direct descendant of F1's `ParityWorld` (§6.5), extended from "the guard
takes no arguments that could deny" to "the HTTP request has no reason to
fail other than the permission":

* six users, one per `UserRole`, active, each with
  `UserTenantLink(tenant_id=DEFAULT_TENANT_ID, is_tenant_admin=False)`;
* **each with a `UserType` carrying `allowed_menus=["tasks","categories"]`**
  — this is new relative to `ParityWorld` and is load-bearing: without it the
  menu gate 403s every tasks/categories cell for five of six roles and the
  matrix measures `allowed_menus`, not permissions;
* every role-linked `UserType` present, all with `permissions == []` (the
  swap must be proven while bundles are empty — that is what makes the union
  collapse to the legacy set, §4.1);
* one `Lot`, with a `UserLotLink(start_date=None, end_date=None)` **and** an
  active `Resident` for each of the six users (F1 §6.5(b), verbatim);
* one row of every object a matrix path parameter names: `Task`
  (`visible_to=[]`, `assigned_to_id=None`), `Category`, non-role `UserType`,
  `Tenant` B, `Resident`, `Visitor`, `VisitorAuthorization` (active),
  `AccessLog`, `Occurrence` (public), `Document` + `DocumentFolder`,
  `Announcement` + comment, `Feedback`, `ReservableSpace` +
  `SpaceReservation`, `Package`, `Vote` (`ENQUETE`, open) + `Assembly`,
  `Asset` + `InventoryMovement`, `PurchaseRequest` + `PurchaseQuote`,
  `MediaAsset`, `AccessDevice`, `Project` + milestone + update, finance
  category + budget line + `FinancialTransaction`;
* `MediaService(storage_provider=_NullStorage())` is *not* reachable through
  HTTP, so the upload cells post a small in-memory file and the test module
  points `settings`' upload directory at `tmp_path` (asserted empty-safe on
  teardown).

**Every datetime is relative.** The baseline is a committed golden file, so a
cell whose status depends on wall-clock time would rot into a red CI run that
has nothing to do with permissions — and at least one such path exists
(`reservation_service.py:345` branches on
`reservation.start_time <= datetime.utcnow()`). Therefore: **every datetime
written into `MatrixWorld` or `REQUEST_BODIES` is computed as an offset from
`datetime.utcnow()` at build time; no absolute date is hard-coded anywhere in
either.** The `SpaceReservation` starts `+2 days`, the `VisitorAuthorization`
is valid `−1 day … +30 days`, the `Vote`/`Assembly` window is
`−1 hour … +7 days`, and every "created at" is `now`.
`test_no_absolute_datetime_in_the_harness` parses `tests/matrix_world.py` and
asserts no `datetime(...)`/`date(...)` call with literal year arguments and no
ISO-date string literal appears in it.

**Isolation — one mechanism, no fallback.** Cells mutate (24 DELETE and 89
POST/PUT/PATCH routes). The mechanism is fixed:

1. the module creates **one** SQLite file database under
   `tmp_path_factory.mktemp("matrix")` and **one** engine (module-scoped
   fixture) — a file, not `:memory:`, so a second connection sees the same
   data without `StaticPool` tricks;
2. it creates the schema and **seeds `MatrixWorld` exactly once**, committing
   it, *before* any cell runs. The world is never rebuilt: 1080 cells, one
   world;
3. each cell then opens its own `Connection`, begins an outer transaction, and
   the `get_session` dependency override yields
   `Session(bind=connection, join_transaction_mode="create_savepoint")`
   (SQLAlchemy 2.0.49 is present, `backend/uv.lock:739`), so a handler's
   `commit()` releases a savepoint and the cell's closing `rollback()` undoes
   every write. The committed world survives; the cell's mutations do not.

There is **no sanctioned fallback**. Rebuilding the world per cell is
forbidden: it would make the runtime a function of the world's size, and it
would let a cell see a *different* world than the one the baseline was
recorded against, which silently breaks the golden file. If some route cannot
be isolated by savepoint, that is a finding to report in the PR body (with the
route named), not a licence to change the harness — because the same harness
produced the committed baseline (§6.4) and changing it invalidates the file.

### 6.3 The oracle

Each cell issues one real HTTP request through a `TestClient` with the
role's bearer token and `X-Tenant-Id: DEFAULT_TENANT_ID`, and records the
**status code**. The assertion is:

```
recorded_status(role, method, path) == BASELINE[role][method][path]
```

for all 1080 cells, reported as a sorted diff of `(role, method, path,
expected, actual)` — not as a bare count.

### 6.4 Where the baseline comes from, and the proof chain

The baseline must be provably **pre-swap**. The obvious way to show that —
"commit the JSON in its own commit before touching production code" — is not
available here and must not be specified: this task ships through a pipeline
in which the developer *stages* and never commits, and the whole task lands as
a single commit after code review and QA approve. A chronological requirement
would be unfollowable by the implementer, unverifiable by QA after the squash,
and actively dangerous in this shared tree (an intermediate commit would sweep
a concurrent lane's uncommitted files).

So the proof is **reproducibility, not chronology**. Three artefacts:

**(1) A committed generator.** `backend/tests/tools/record_parity_baseline.py`
imports the §6.2 harness from `tests/matrix_world.py`, runs all 1080 cells and
writes the JSON. It is production-independent by construction: it reads only
`app.main.app`, `ROUTE_PERMISSIONS` and the world. Usage:

```bash
cd backend
uv run python -m tests.tools.record_parity_baseline --out tests/data/parity_matrix_baseline.json
```

It refuses to overwrite an existing file unless `--overwrite` is passed.

It also **refuses to run at all when the production tree is dirty**: before
building the world it shells out to `git status --porcelain -- app/` (from
`backend/`) and, if the output is non-empty, prints the offending paths and
exits `2` without writing anything. This is the mechanical half of "the
baseline is pre-swap": the recorder physically cannot be run once a single
`app/` file has been edited or staged, so the implementation order of §6.4 is
enforced rather than merely requested, and the regeneration worktree (which
copies in only `tests/` files) still passes the check. There is no
`--allow-dirty` flag. `test_recorder_refuses_a_dirty_production_tree` calls the
recorder's `assert_clean_production_tree(run_git=...)` with a stub returning a
non-empty string and asserts `SystemExit(2)`, and with `""` asserts it returns
normally.

**(2) The merge-base sha, embedded.** The JSON is

```json
{
  "_meta": {
    "merge_base_sha": "<40-hex>",
    "generator": "tests/tools/record_parity_baseline.py",
    "harness": "tests/matrix_world.py",
    "cell_count": 1080,
    "regenerate": "git worktree add /tmp/apras-parity <merge_base_sha> && cp -R backend/tests/matrix_world.py backend/tests/tools /tmp/apras-parity/backend/tests/ && (cd /tmp/apras-parity/backend && uv run python -m tests.tools.record_parity_baseline --out /tmp/regen.json) && diff /tmp/regen.json backend/tests/data/parity_matrix_baseline.json"
  },
  "cells": { "<role>": { "<METHOD>": { "<path>": <status:int> } } }
}
```

`merge_base_sha` is `git rev-parse HEAD` **at record time**, which — since the
recorder is run before the swap — is the commit this branch was cut from, i.e.
the commit that landed `APRAS-45`. It is quoted in the PR body and in
`tests/test_legacy_role_permissions.py`'s docstring (§7.2), so one sha anchors
the whole chain.

`_meta` carries **no timestamp, no hostname and no absolute path**: the file
must be a pure function of the tree at `merge_base_sha`. The recorded value of
a cell is the integer status code and nothing else — no ids, no bodies, no
timings — which is what makes byte-identity achievable even though the world's
UUIDs are random each run. Serialisation is
`json.dumps(payload, indent=2, sort_keys=True) + "\n"`.

**(3) A regeneration ER that QA can execute.** Running the `regenerate`
command above must produce a file **byte-identical** to the committed
`tests/data/parity_matrix_baseline.json` (`diff` exits 0). That command copies
*only* the harness and the recorder — never any production file — into a clean
worktree at `merge_base_sha`, so what it measures is unswapped production.
This survives squashing, is immune to the concurrent lane, and is decidable by
anyone holding nothing but the ER text.

Tests over the file itself, in `test_permission_parity_matrix.py`:

* `test_baseline_file_exists` — **fails, never skips**, when
  `tests/data/parity_matrix_baseline.json` is missing. A deleted baseline must
  not turn into a green run. `pytest.skip` does not appear anywhere in the
  module (asserted by the AST of the module itself in
  `test_the_matrix_module_never_skips`).
* `test_baseline_declares_its_provenance` — `_meta` has exactly the five keys
  above; `merge_base_sha` matches `^[0-9a-f]{40}$`; `generator` and `harness`
  name files that exist in the tree; `cell_count == len(CELLS) == 1080`.
* `test_baseline_covers_exactly_the_matrix` —
  `{(r, m, p) for the JSON's cells} == set(CELLS)`, so the golden file can
  neither miss a cell nor carry a retired one.

Implementation order follows from this, and is fixed:

1. land F1;
2. write `tests/matrix_world.py` + `tests/tools/record_parity_baseline.py` +
   the assertions, green against **unswapped** code (the two oracle tests
   below already pass — they describe the legacy map, which F1 proved);
3. run the recorder and stage the JSON, **before** editing a production file;
4. do the swap; the same harness must now reproduce the file exactly.

That is the literal reading of the board's ER-2: same status code, measured
before and after, no old code kept. The **semantic** half — that those status
codes are the *role gate* and not incidental noise — is the chain the F1
work bought, and it is asserted by two further tests over the same JSON:

* `test_every_denied_cell_is_denied_in_the_baseline` — for every cell where
  `ROUTE_PERMISSIONS[(m,p)] ∉ LEGACY_ROLE_PERMISSIONS[role]`, the recorded
  status is `403`, unless the **cell** is in `DENIAL_SHAPE_OVERRIDES`. That
  map is keyed by `(role, method, path)`, not by route, and it is pinned
  **exactly**:

  ```python
  DENIAL_SHAPE_OVERRIDES: dict[tuple[str, str, str], tuple[int, str]] = {
      ("GUEST", "GET",   "/api/v1/tasks/"): (200, "documented empty-list refusal, endpoints/tasks.py list_tasks"),
      ("GUEST", "PATCH", "/api/v1/tasks/{task_id}"): (404, "assert_manager_can_see_task raises TaskNotFoundError for GUEST"),
      ("GUEST", "GET",   "/api/v1/tasks/{task_id}/history"): (404, "idem"),
      ("GUEST", "GET",   "/api/v1/tasks/{task_id}/comments"): (404, "idem"),
      ("GUEST", "POST",  "/api/v1/tasks/{task_id}/comments"): (404, "idem"),
      ("GUEST", "PATCH", "/api/v1/tasks/{task_id}/comments/{comment_id}"): (404, "idem"),
  }
  ```

  **Exactly six entries, all GUEST**, and that is derivable rather than
  asserted by fiat: `tasks:read`, `tasks:update` and `tasks:comment` are each
  `{A, D, M, R, P}` in `LEGACY_ROLE_PERMISSIONS`, so GUEST is the only denied
  role on the six task routes that reach `assert_manager_can_see_task` or the
  `list_tasks` early return. Every other denial in the matrix raises a
  `403`-mapped exception (`TallyNotAvailableError` included — it is in the
  403 tuple at `app/core/exception_handlers.py:157`, so
  `GET /api/v1/votes/{id}/tally` needs **no** override; an earlier draft
  wrongly listed it).

  Three guards keep the map from becoming a dumping ground:
  `test_denial_shape_overrides_is_exactly_six` (`len == 6`);
  `test_every_denial_shape_override_is_needed` — every declared entry must in
  fact be a denied cell whose recorded status is the declared non-403 value,
  so a stale or speculative entry **fails**; and
  `test_every_denial_shape_override_has_a_reason`.

  **Deviation clause — same rule as the isolation failures of §6.2.** The six
  entries are derived above from `LEGACY_ROLE_PERMISSIONS` and the production
  code, so the recorded baseline is expected to need exactly them. If it does
  not — a seventh denied cell recorded as non-403, or one of the six recorded
  with a different status — that is a **finding to report in the PR body**,
  naming the cell, the recorded status and the production line that produces
  it, not a licence to pad the map. Only then may the entry be added (with its
  reason) and `test_denial_shape_overrides_is_exactly_six` renamed to
  `..._is_exactly_<N>`; the count in the test name must always be a literal, so
  the map can never grow silently.
* `test_no_permitted_cell_is_403_in_the_baseline` — for every cell where the
  permission **is** held, the recorded status is not `403`, unless the cell is
  in `NON_ROLE_403`. Its entries are the object-dimension refusals of §5.2
  (ownership, per-lot linkage, the role-linked `UserType` row, …), which the
  six-role matrix cannot avoid crossing. It is bounded the same way:

  * exact set equality — the set of cells the test excuses **is**
    `NON_ROLE_403`, so nothing is silently absorbed;
  * `test_every_non_role_403_is_needed` — a declared cell that is not
    permitted-and-403 in the baseline **fails**, so the list cannot be padded;
  * `test_every_non_role_403_has_a_reason` — each entry's reason must name the
    §5.2 dimension responsible (ownership / per-lot linkage / payload
    narrowing / role-linked row), non-empty;
  * `test_non_role_403_is_bounded` — `len(NON_ROLE_403) <= 40`. There are
    ~700 permitted cells; a list that could grow past 40 would stop being an
    enumeration of known object-dimension refusals and start being a way to
    silence the test. The measured length is quoted in the PR body.

  Unlike `DENIAL_SHAPE_OVERRIDES`, the exact membership of `NON_ROLE_403`
  cannot be derived by reading the code — it depends on which `MatrixWorld`
  object each cell touches — so it is pinned by construction (record it,
  freeze it, and let the three guards above stop it drifting) rather than
  enumerated here. Note that this list constrains only the *semantic* oracle;
  ER-3's parity assertion covers all 1080 cells regardless.
* `test_no_cell_is_5xx_in_the_baseline` — **no recorded status is ≥ 500, for
  any cell, with no allowlist and no exception.** A 5xx is never an
  authorization answer: it means the harness handed a route an object it could
  not process (or the route is broken), and freezing it into the golden file
  would turn a crash into a "parity" the swap is then required to reproduce.
  The remedy is always to fix `MatrixWorld`/`REQUEST_BODIES` and re-record
  (§6.1), never to record around it. This test runs against the committed JSON,
  so it fails at record time *and* forever after.
* `test_no_permitted_cell_is_422_in_the_baseline` — for every cell whose
  permission **is** held, the recorded status is not `422`, unless the cell is
  in `PERMITTED_422`. `422` is request-shape validation, never authorization:
  a permitted cell answering `422` means the harness sent an incomplete
  request, and the *first* remedy is to fix it — bind the missing body field in
  `REQUEST_BODIES`, or, when the route declares a **required query parameter**
  the matrix does not send, add a `QUERY_PARAMS` map alongside `PATH_PARAMS`
  with the same "bound to a `MatrixWorld` id" discipline — and then re-record
  via `_meta.regenerate`. `PERMITTED_422` is the last resort for cells whose
  request cannot be completed from the world at all, and it is bounded exactly
  like `NON_ROLE_403`: exact set equality, `test_every_permitted_422_is_needed`
  (a declared cell that is not permitted-and-422 in the baseline fails),
  `test_every_permitted_422_has_a_reason` (each reason must name the missing
  parameter or field, non-empty) and `test_permitted_422_is_bounded`
  (`len(PERMITTED_422) <= 15`, with the measured length quoted in the PR body —
  the expected length is **0**, and any non-zero length is a harness limitation
  the PR body must state).

Together: `post-swap behaviour == BASELINE == pre-swap production`, and
`BASELINE`'s denial structure `== LEGACY_ROLE_PERMISSIONS`, which F1 already
proved `== the production guards`. Zero divergence, provable without keeping
a line of the old code.

---

## 7. What happens to F1's two test modules

### 7.1 `tests/test_permission_registry.py` — two amendments

1. `test_every_catalogue_permission_is_reachable` becomes
   `PERMISSIONS == set(ROUTE_PERMISSIONS.values()) | SCOPE_PERMISSIONS`, plus
   a new `test_scope_permissions_are_not_route_mapped`
   (`SCOPE_PERMISSIONS & set(ROUTE_PERMISSIONS.values()) == frozenset()`) and
   `test_scope_permissions_are_exactly_four` pinning the four strings by
   exact match. F1's intent — no dead vocabulary — survives: a scope
   permission is dead unless it appears in the enforcement code, which §8.2's
   allowlist makes visible.
2. `test_user_type_schemas_are_unchanged` becomes
   `test_user_type_schemas_expose_permissions`:
   `set(UserTypeCreate.model_fields) == {"name", "allowed_menus", "permissions"}`,
   `set(UserTypeUpdate.model_fields) == {"name", "allowed_menus", "permissions"}`,
   `set(UserTypeRead.model_fields) == {"id", "name", "allowed_menus", "role", "permissions"}`.
   F1's ER-6 pinned these schemas *in F1*; this is the declared handoff, and
   the assertion stays exact so a future field still fails CI.

Route accounting (190 / 180 / 10) is untouched.

### 7.2 `tests/test_legacy_role_permissions.py` — the derived-parity machinery is retired

F1's parity test derives each expected role set from a **live production
object**: `RoleSet(asset_service._STAFF_ROLES)`,
`RoleSetComplement(voting_service.NON_VOTING_ROLES)`,
`Guard(deps.get_current_tenant_admin)`, and so on. This slice **deletes those
objects** — that is the deliverable. `_LOT_READ_ROLES`, `_FINANCE_*_ROLES`,
`BOARD_ROLES`, `NON_VOTING_ROLES`, `_GATEKEEPER_ROLES`,
`get_current_tenant_admin` and the rest stop existing, so `PARITY_SOURCES`
cannot be evaluated at all.

Keeping them alive as dead constants purely to feed the test would be worse
than deleting it: the test would then assert "the map equals a tuple nobody
consults", which is true and meaningless.

So F2 **rewrites the module down to its production-independent assertions**
and deletes `PARITY_SOURCES`, `ParityWorld`, `RoleSet`,
`RoleSetComplement`, `Guard`, `Composite` and `Literal`.

**Exactly which tests retire, and the collected-case arithmetic.** The module
collects **162** cases at the merge base (measured:
`uv run pytest --collect-only -q tests/test_legacy_role_permissions.py`). Six
test functions — **157 collected cases** — evaluate `PARITY_SOURCES` or the
source-shape classes and therefore cannot survive the deletion of the
production objects they read:

| Retired test | Cases | Why it cannot survive |
|---|---:|---|
| `test_legacy_map_matches_the_live_guards` | **152** | parametrised over `sorted(PARITY_SOURCES)`; each case builds a `ParityWorld` and calls a `RoleSet` / `Guard` / `Composite` source against a deleted constant or a deleted guard |
| `test_every_permission_has_a_parity_source` | 1 | asserts `set(PARITY_SOURCES) == PERMISSIONS`; `PARITY_SOURCES` is gone |
| `test_role_set_sources_are_production_objects` | 1 | asserts each `RoleSet` source *is* the live module attribute — the attributes are deleted by §5.1 |
| `test_composite_sources_have_a_live_part` | 1 | same, for `Composite` |
| `test_literal_sources_are_allowlisted` | 1 | same, for `Literal` |
| `test_literal_sources_carry_a_reason` | 1 | same |
| | **157** | |

One case is **added** (`test_every_scope_permission_has_a_legacy_entry`), so
the module goes **162 → 6**, a net **−156** collected cases. That number is not
a side effect to be absorbed quietly: it is the arithmetic ER-9's floor is
built on, and the two must agree. The proof those 157 cases carried does not
disappear — it moves to the recorded matrix of §6.4, which is why the module
docstring must name the merge-base sha at which they were last green.

* kept (5 cases): `test_every_role_has_an_entry`,
  `test_administrator_is_a_superset_...` and `test_admin_gap_list_is_exact`
  (now importing `ADMIN_GAP_PERMISSIONS` from `app/core/permissions.py`, E1),
  `test_all_six_role_permissions_are_the_documented_seventeen` (the four
  scope permissions are not all-six, so the seventeen are unchanged),
  `test_legacy_map_is_marked_transitional`;
* added (1 case): `test_every_scope_permission_has_a_legacy_entry`;
* the module docstring gains a paragraph recording **why** the derivation was
  retired and where the proof moved (§6.4), naming the merge-base commit at
  which the derived parity test was last green. That sha is
  `_meta.merge_base_sha` in `tests/data/parity_matrix_baseline.json` — one sha,
  written in exactly two places, anchoring the whole chain — and it must be
  quoted in the PR body.

`tests/test_effective_permissions.py` is edited **additively only** (3 new
bridge cases, §3.3); no existing case changes.

---

## 8. The structural tests

`backend/tests/test_permission_enforcement.py`, built on the `_depends_on` /
`_api_routes` walk that `test_tenant_route_scope.py` and
`test_tenant_admin.py` §9 already use — deliberately the same shape, because
it is the pattern this repo reviews and trusts.

### 8.1 Route walk

1. `test_no_route_depends_on_a_tenant_admin_role_guard` — no `APIRoute`'s
   dependant tree reaches `deps.get_current_tenant_admin` or
   `deps.get_current_tenant_admin_or_manager` (both are gone; the test also
   asserts the attributes no longer exist on `deps`, so re-adding them is a
   failure).
2. `test_get_current_active_admin_is_still_exactly_the_five_tenant_writes` —
   the is_superuser carve-out, duplicated here from `test_tenant_admin.py` so
   the F2 module states its own boundary; the original test keeps passing
   unmodified.
3. `test_every_route_level_permission_matches_the_registry` — for every
   `PermissionRequired` instance found in any route's dependant tree,
   `instance.permission == ROUTE_PERMISSIONS[(method, path)]`; and the set of
   routes carrying one equals the seven of §5.1.
4. `test_every_route_is_still_tenant_classified` — re-asserts the APRAS-42
   invariant after the dependency changes (`get_current_tenant` reachable, or
   allowlisted), so a `require_permission` mounted on a global router is
   caught here rather than by a leak.

### 8.2 AST walk — the in-code proof

**The counting rule, stated once.** Every count in this spec — §5.0's
baseline, §5.1's `n` columns, §5.3's allowlists, §5.4's subtraction and ER-2 —
is this rule and nothing else.

*Scope.* Every `*.py` reachable under `backend/app/`, **except** anything
under `app/models/` or `app/schemas/`, and except `app/seed.py`. (That is the
whole application minus the declarative layer and the seeder; `app/db.py`,
`app/main.py` and `app/core/**` are in scope and simply contain no actor-role
read.)

*Actor-role attribute.* An `ast.Attribute` node `n` such that
`n.attr == "role"` **and** `isinstance(n.value, ast.Name)` **and**
`n.value.id in {"current_user", "user", "admin_user"}` — the three actor names
this codebase uses. Nothing else qualifies: `user_in.role`, `db_user.role`,
`resident.user.role`, `UserType.role` and `folder.allowed_roles_json` are
payloads, targets, columns or data, and are outside the rule **by
construction** because the attribute's `.value` is not a bare actor `Name`.

*Rule C — comparison reads.* One count for each `ast.Compare` node whose
subtree (`ast.walk`) contains at least one actor-role attribute. One `Compare`
node is one read regardless of how many operands or operators it has, so
`user.role in (A, D)` is 1 and `a == user.role == b` is 1, while
`user.role == A or user.role == D` is 2 (two `Compare` nodes under a
`BoolOp`).

*Rule N — non-comparison reads.* One count for each actor-role attribute node
that is **not** inside any `ast.Compare`. This counts *nodes*, so the attribute
chain `user.role.value` contributes 1 (the `.role` access; the `.value` access
on top of it is not itself an actor-role attribute), and one physical line
containing three separate `user.role` accesses contributes 3 — which is
exactly the `document_service.py:39` case of §5.3-C.

Rule C ∪ Rule N is a partition of all actor-role attribute reads in scope:
every such node is either inside a `Compare` or it is not. Nothing is
double-counted and nothing is missed.

*Attribution.* Each read is keyed `"<path relative to app/>::<function>"`,
where the function is the innermost enclosing `FunctionDef`/`AsyncFunctionDef`
(module-level reads would key as `::<module>`; there are none). Keying on
`module::function` rather than on a line number keeps the allowlist stable
under unrelated edits while still failing on a real change.

**The tests.**

* `test_no_authorization_check_reads_user_role` — the Rule-C walk's
  `{key: count}` mapping equals `ROLE_READS_COMPARE` (§5.3 A + B + D)
  **exactly**: 15 reads in 15 functions.
* `test_non_comparison_role_reads_are_allowlisted` — the Rule-N walk's mapping
  equals `ROLE_READS_NON_COMPARE` (§5.3-C) **exactly**: 7 reads in 5
  functions.
* `test_every_allowlisted_role_read_has_a_reason` — every entry of both maps
  carries a `slice` in `{"F3", "F5"}` and a non-empty `reason`.
* `test_role_read_arithmetic_closes` (§5.4) — `RULE_C_BASELINE == 100`,
  `RULE_N_BASELINE == 7`, `sum(ROLE_READS_COMPARE) == 15`,
  `sum(ROLE_READS_NON_COMPARE) == 7`, and therefore
  `RULE_C_BASELINE - CONVERTED_COMPARE == 15` with `CONVERTED_COMPARE == 85`.
  Both baseline constants sit beside the merge-base sha in a comment, so a
  future slice must change them deliberately.

This is the mechanical form of the board's "no authorization check reads
`user.role` at the end of the slice": **107 reads in (100 Rule C + 7 Rule N),
22 out (15 + 7)** — of which the only *authorization* reads are the 7
is_superuser-marked (F3) and the 7 object/visibility ones (F5); the remaining
8 are the resolver plumbing and three serialisation sites that decide nothing.
Every one of the 22 is named, counted and assigned to a later slice.

---

## 9. Anti-escalation

### 9.1 Schemas

```python
class UserTypeCreate(BaseModel):
    name: str
    allowed_menus: list[MenuKey] = []
    permissions: list[str] = []          # validated against PERMISSIONS -> 422

class UserTypeUpdate(BaseModel):
    name: str
    allowed_menus: list[MenuKey] = []
    permissions: list[str] | None = None  # None => leave the bundle unchanged

class UserTypeRead(BaseModel):
    ...
    permissions: list[str] = []
```

`UserTypeUpdate.permissions` is **optional with a `None` sentinel**, unlike
its two siblings, and that asymmetry is deliberate: `update_user_type`
overwrites `allowed_menus` unconditionally, so a plain `list[str] = []` would
silently wipe a group's bundle on every save from the current frontend (which
does not send the field until F4). A field validator rejects any string not
in `PERMISSIONS` with a 422; F1's resolver keeps tolerating unknown strings
already stored in a row (a hand-edited row must stay visible, not vanish).

### 9.2 The rule

`app/services/user_type_service.py`:

```python
def assert_can_grant(session, author: User, permissions: Iterable[str]) -> None:
    """The author may only put permissions they themselves hold into a group."""
    missing = sorted(set(permissions) - get_effective_permissions(author, session))
    if missing:
        raise ForbiddenError(
            "You cannot grant permissions you do not hold: " + ", ".join(missing)
        )
```

* Applied to the **resulting** set, not the delta — the board's wording is
  "granting/editing a group *containing* a permission the author does not
  hold", and the resulting-set reading also closes "author edits a group that
  already carries X and keeps X while renaming it".
* When `permissions is None` on update, no check runs: the bundle is
  unchanged and the author gains nothing.
* `is_tenant_admin` needs no special case: the author's *effective* set
  already includes the §3.3 bridge, so a capability holder can grant exactly
  what they hold — and when F3 widens the bridge to the whole tenant, this
  rule widens with it, with no edit here.
* An ADMINISTRATOR holds `PERMISSIONS - ADMIN_GAP_PERMISSIONS`, so the only
  string they cannot put in a group is `packages:my_lots_read` — a real,
  documented consequence of F1 §11.5, asserted by a test so F3 has to decide
  it rather than inherit it.

### 9.3 Both grant surfaces

1. **Creating/editing a group** — `POST /api/v1/user-types/` and
   `PATCH /api/v1/user-types/{id}` call `assert_can_grant` before writing.
2. **Assigning a group to a user** — `PATCH /api/v1/users/{id}` with
   `user_type_ids`: `_assign_user_types` calls `assert_can_grant` with the
   union of the target groups' `permissions`. Without this, an author who
   cannot *create* a group carrying `finance:category_create` could still
   hand an existing one to a confederate.

Both are **behaviour-neutral at parity time**: nothing seeds a bundle, so
every group's `permissions` is `[]` and the check is vacuous — which is
precisely why it is safe to introduce in the slice that must not diverge.
The matrix cells for the three user-type routes and `PATCH /users/{id}` prove
it.

### 9.4 Tests (`tests/test_permission_escalation.py`)

1. **The board's named case.** An author holding `user_types:create` /
   `user_types:update` (the board's "groups:manage") through the tenant-admin
   bridge, and **not** holding `finance:category_create` (the board's
   "finance:manage"), gets `403` from
   `POST /api/v1/user-types/ {"name": "...", "permissions": ["finance:category_create"]}`,
   and the response body names the missing permission. No `user_type` row is
   created (asserted by a follow-up `GET`).
2. The same author **succeeds** creating a group carrying only permissions
   they hold (`user_types:update`), and the stored row reads back with that
   bundle — the positive control, without which case 1 could pass for the
   wrong reason.
3. `PATCH /api/v1/user-types/{id}` adding `finance:category_create` → `403`;
   with `permissions` omitted → `200` and the bundle unchanged.
4. `PATCH /api/v1/users/{id}` with `user_type_ids` naming a group that
   carries a permission the author lacks → `403`; the user's group list is
   unchanged.
5. An ADMINISTRATOR may grant any permission except
   `packages:my_lots_read`, which returns `403` (F1 §11.5, made observable).
6. An unknown permission string → `422`, and a row that already contains one
   still resolves through `get_effective_permissions` (F1's tolerance rule).
7. **Escalation is not reachable by self-assignment either**: a
   tenant_admin's own effective set is unchanged after step 3's 403 (a
   regression guard against a partial write).

---

## 10. Ordering for the implementer

The matrix is the safety net, so it comes first; after step 3 every
subsequent step is verified by re-running one module.

1. `tests/matrix_world.py` (harness + `MatrixWorld` + `REQUEST_BODIES` +
   `PATH_PARAMS`), `tests/tools/record_parity_baseline.py`, and
   `tests/test_permission_parity_matrix.py`, green against **unswapped** code
   (the two oracle tests of §6.4 will already pass — they describe the legacy
   map, which F1 proved).
2. Run the recorder and **stage** `tests/data/parity_matrix_baseline.json`
   before editing a single production file, with `_meta.merge_base_sha` set
   from `git rev-parse HEAD`. Do **not** commit: this pipeline's developer
   stages and stops, and the tree is shared with a concurrent lane. The proof
   that the baseline is pre-swap is §6.4's regeneration command, not a commit
   boundary — and the recorder enforces the *ordering* itself: it exits `2`
   if `git status --porcelain -- app/` is non-empty, so step 2 physically
   cannot be run after step 3 has begun.
3. `deps`: `has_permission`, `require_permission`, the bridge; the 7 route
   swaps. Re-run the matrix + `test_tenant_admin.py`.
4. One module per commit, endpoints then services, in the §5.1 order.
   Re-run the matrix after each; a red cell names the module you just
   touched.
5. `SCOPE_PERMISSIONS` and the F1 registry amendments (§7.1) land with the
   first module that needs them (`resident_service`).
6. Retire the derived-parity module (§7.2) **last**, when the production
   objects it probes are gone — not before, so the intermediate commits stay
   green. Record `162 → 6` for that module and the whole-suite collected count
   at the same moment; ER-9's floor is stated in terms of that subtraction.
7. Anti-escalation + schemas (§9).
8. Structural tests (§8) — written last, because the allowlist is only
   knowable once the swap is complete; the AST test tells you what you
   forgot.

---

## 11. Pre-existing tests: what changes, what must not

**Edited — exactly three modules, all of them F1's own:**

| Module | Edit | Why forced |
|---|---|---|
| `tests/test_legacy_role_permissions.py` | derived-parity machinery removed, production-independent assertions kept; **162 → 6 collected cases**, net −156 (§7.2's table itemises the 157 retired and the 1 added) | the production objects it probes are deleted by this slice (§7.2); the −156 is what ER-9's floor subtracts |
| `tests/test_permission_registry.py` | 2 assertions amended (§7.1) | `SCOPE_PERMISSIONS` exists; the `UserType` schemas gain `permissions` — the declared F1→F2 handoff |
| `tests/test_effective_permissions.py` | **additive only**, 3 new cases | the tenant-admin bridge (§3.3) |

**Must pass unmodified — asserted by `git status --short -- backend/tests/`**
(equivalently `git diff --stat HEAD -- backend/tests/`; this task stages and
never commits, so a worktree-only `git diff` would show nothing)**:**
`test_tenant_isolation.py`, `test_tenant_route_scope.py`,
`test_tenant_admin.py`, `test_tenant_no_behaviour_change.py`,
`test_tenant_context.py`, `test_menu_access.py`,
`test_role_type_permissions.py`, `test_migrations_postgres.py`, and every
`test_*_rbac.py` (tasks, guest, assets, documents, feedback, finance, lots,
occurrences, packages, projects, purchases, residents, tenants, uploads,
visitors) plus `test_porteiro_role.py`, `test_gatekeeper.py`,
`test_packages.py`, `test_authorizations.py`, `test_voting*.py`,
`test_user_admin.py`, `test_user_types.py`, `test_user_contact_info.py`,
`test_user_directory_scope.py`.

**Two expectations from the dispatch that the code walk contradicts, stated
so the reviewer can check them rather than trust them:**

* `tests/test_tenant_route_scope.py` **does not need to change.** Its
  allowlist is about tenant *scope*, and `PermissionRequired` depends on
  `get_current_tenant` exactly as `get_current_tenant_admin` did, so every
  route's classification is byte-identical. `GLOBAL_ROUTES` stays 18 entries.
* `tests/test_tenant_admin.py` §9 **does not need to change either**: its
  structural assertions name `get_current_active_admin` and
  `get_current_admin_or_manager`, both of which survive untouched (§5.3-A),
  and `ADMIN_ONLY_ROUTES` is still exactly the five global tenant writes.
  Its behavioural tests (the seven admin-gated routes, the 403s in the
  non-granting tenant) are what the §3.3 bridge exists to keep green.

If either does turn out to need an edit, that is a design regression in this
spec, not a licence: the edit must be reported with its cause.

---

## 12. Decisions

### 12.1 The tenant_admin bridge is narrow (7 permissions), not "everything in the tenant"

The dispatch describes the end state as "`is_tenant_admin` short-circuits:
all permissions in-tenant". That is `APRAS-47`'s headline
("*is_tenant_admin como todas-as-permissões do tenant*"), and doing it here
would be a **widening**: a RESIDENT tenant_admin would gain
`finance:category_create`, `documents:create`, `assets:delete` and ~170 more,
none of which they can reach today. The six-role matrix cannot see it (the
capability is not a role), which is exactly why it must be decided
deliberately rather than discovered later. This slice's contract is zero
divergence, so the bridge reproduces precisely the seven routes APRAS-43
granted, pinned to those routes by a test, marked `TRANSITIONAL (F2 -> F3)`,
and F3 widens it with a one-line change that the anti-escalation rule follows
automatically. If the user wants the widening now, it is a one-constant edit
plus new cases in `test_tenant_admin.py` — and it should be recorded as an
intentional behaviour change, not smuggled in under a parity ER.

### 12.2 Replacement, not `role AND permission`

Argued in §4.1. Additive enforcement would be observationally identical today
(bundles are empty) while keeping `user.role` load-bearing, which is the one
thing the board's ER-1 forbids ("*nenhum check de autorização o lê ao final
da fatia*"). F1's contrary sentence is addressed in the header note.

### 12.3 No migration

The `permissions` column arrives with F1's `0030`. This slice adds no DDL,
no data migration and no seeding: every `user_type.permissions` stays `[]`
until an administrator writes one through §9's API. `alembic heads` still
reports the single head `0030_add_user_type_permissions`.
`tests/test_migrations_postgres.py` is untouched, and the Postgres run on
5436 (which wipes the demo database, F1 §7.5) is **not** required for this
task.

### 12.4 `groups` vs `user_type`

The board's ER-3 says "groups:manage" and "finance:manage"; neither string
exists. Groups **are** `user_type` rows until F5 renames them, so
"groups:manage" is `user_types:create` + `user_types:update` and
"finance:manage" is instantiated as `finance:category_create` in §9.4's named
test. The ER below states the concrete strings so the check is unambiguous.

### 12.5 Changing a target's *role* remains a wider grant surface than any bundle

§9 closes both **permission-bundle** grant surfaces. It does not close — and
must not close here — the older one: `PATCH /api/v1/users/{id}` can still
change a target's `role`, and a role carries a legacy bundle, so a
tenant_admin holding `users:update` can promote a user to DIRECTOR and thereby
hand out permissions the author does not hold. That is pre-existing APRAS-43
behaviour, it is guarded only by the three escalation rules in
`endpoints/users.py::update_user` (the §5.3-A allowlisted read), and changing
it here would be a divergence the matrix would catch. It is recorded so F3
(which replaces the role reads) and F5 (which retires `User.role`) inherit the
question rather than rediscover it.

### 12.6 `/auth/me` is not touched

Its `tenants` array is APRAS-38's and lands with it. `GET /auth/me` is in
`UNGUARDED_ROUTES`, outside the matrix, and no permission gates it. Exposing
the caller's effective permissions there is F4's job, not this slice's.

---

## Expected Results

- [ ] **ER-1 — the guard exists and no route depends on a role guard.**
      `deps.require_permission(permission)` returns a `PermissionRequired`
      dependency that 403s with the detail `"The user doesn't have enough
      privileges"` and is mounted on exactly the seven routes of §5.1
      (`DELETE /tasks/{task_id}`, `DELETE /lots/{lot_id}`,
      `PATCH /users/{user_id}`, `PATCH /users/{user_id}/contact-info`,
      `POST /user-types/`, `PATCH /user-types/{user_type_id}`,
      `DELETE /user-types/{user_type_id}`).
      `tests/test_permission_enforcement.py` passes: `deps` no longer defines
      `get_current_tenant_admin` or `get_current_tenant_admin_or_manager` and
      no `APIRoute` reaches either; every `PermissionRequired` found on a
      route declares `ROUTE_PERMISSIONS[(method, path)]`;
      `deps.get_current_active_admin` is reachable from exactly the five
      `/api/v1/tenants` writes (the is_superuser carve-out F3 may adjust) and
      from nothing else.
- [ ] **ER-2 — no authorization check reads `user.role`, and the arithmetic
      closes.** The AST walker of §8.2 runs over all of `backend/app/` except
      `app/models/`, `app/schemas/` and `app/seed.py`, under the rule stated
      once in §8.2: **Rule C** = one count per `ast.Compare` node containing an
      `ast.Attribute(attr="role")` whose `.value` is an `ast.Name` in
      `{current_user, user, admin_user}`; **Rule N** = one count per such
      attribute node *outside* any `Compare`. Measured at the merge base
      (command in §5.0): **Rule C = 100, Rule N = 7**.
      `test_no_authorization_check_reads_user_role` asserts the Rule-C
      `{module::function: count}` mapping equals `ROLE_READS_COMPARE`
      **exactly — 15 reads in 15 functions**: 7 is_superuser-marked (F3:
      `deps.get_current_active_admin`, `deps.get_current_admin_or_manager`,
      `deps.has_admin_capability`, `deps._resolve_from_header`,
      `endpoints/users.py::update_user`, `tenant_service::list_tenants`,
      `tenant_service::get_visible_tenant`), 7 object/visibility-dimension
      (F5: `deps.assert_manager_can_see_task`, `deps.assert_can_edit_task`,
      `endpoints/tasks.py::list_tasks`, `task_service::create_task`,
      `task_service::update_task`,
      `occurrence_service::_check_user_access`,
      `occurrence_service::get_occurrences`) and 1 resolver-plumbing read
      (F5: `deps.get_effective_user_type_ids`, the role-implicit `UserType`
      lookup `get_effective_permissions` is built on, which cannot be
      converted without circularity).
      `test_non_comparison_role_reads_are_allowlisted` asserts the Rule-N
      mapping equals `ROLE_READS_NON_COMPARE` **exactly — 7 reads in 5
      functions** (`document_service::get_accessible_folder_ids` ×3 on one
      line, `deps.get_effective_permissions`,
      `endpoints/lots.py::link_user_to_lot`,
      `lot_service::get_lot_detail`, `tenant_service::_to_member_read`), all
      F5. Every entry of both maps carries `slice ∈ {"F3","F5"}` and a
      non-empty reason. `test_role_read_arithmetic_closes` asserts
      `100 − 85 == 15` and `7 − 0 == 7`, with the 85 itemised per module in
      §5.4; the two baseline constants sit beside the merge-base sha. A new
      unlisted read, a listed read that disappears, or a subtraction that
      stops closing, fails CI.
- [ ] **ER-3 — the exhaustive parity matrix is green with zero divergence.**
      `tests/test_permission_parity_matrix.py` generates
      `6 × len(ROUTE_PERMISSIONS) == 1080` cells mechanically from
      `app.main.app` and `ROUTE_PERMISSIONS` (180 permission-mapped keys of
      the app's 190; the 10 `UNGUARDED_ROUTES` are excluded with the reason
      stated in the module docstring), issues one real HTTP request per cell
      against `MatrixWorld`, and asserts each recorded status code equals
      `tests/data/parity_matrix_baseline.json` — **1080/1080 identical**,
      failures reported as a sorted `(role, method, path, expected, actual)`
      diff. `test_matrix_covers_every_permission_mapped_route`,
      `test_every_path_parameter_has_a_binding` and
      `test_every_write_route_has_a_request_body`
      (`set(REQUEST_BODIES)` == the **89** POST/PUT/PATCH keys of
      `ROUTE_PERMISSIONS`; the 24 DELETE routes take no body) all pass, so no
      cell can be silently dropped and no write cell can be answered by a 422.
      The harness lives in `tests/matrix_world.py`, is imported unchanged by
      both the test and the recorder, seeds `MatrixWorld` **once** before any
      cell and isolates each cell with an outer transaction plus a
      `join_transaction_mode="create_savepoint"` session — one mechanism, no
      fresh-engine fallback — and contains no absolute datetime (every date is
      an offset from `datetime.utcnow()`).
- [ ] **ER-4 — the baseline is provably pre-swap, by regeneration.**
      `backend/tests/tools/record_parity_baseline.py` is committed and is the
      **only** producer of `tests/data/parity_matrix_baseline.json`; it
      **refuses to run when `git status --porcelain -- app/` is non-empty**,
      exiting `2` and writing nothing (no `--allow-dirty` escape), so the
      baseline cannot be recorded after a production file has been edited or
      staged — `test_recorder_refuses_a_dirty_production_tree` pins both
      branches of that check. Any harness gap found later is fixed by fixing
      `tests/matrix_world.py` and **re-recording via `_meta.regenerate`**, never
      by hand-editing the JSON. The JSON
      carries a `_meta` block with exactly
      `merge_base_sha` (40 hex, the sha this branch is cut from — the commit
      that landed `APRAS-45`), `generator`, `harness`, `cell_count == 1080`
      and `regenerate`, and **no timestamp, hostname or absolute path**, so
      the file is a pure function of the tree at that sha (only integer status
      codes are recorded). Executing the `_meta.regenerate` command — which
      creates `git worktree add /tmp/apras-parity <merge_base_sha>`, copies in
      **only** `tests/matrix_world.py` and `tests/tools/`, runs
      `python -m tests.tools.record_parity_baseline` there and `diff`s the
      result — produces a file **byte-identical** to the committed baseline
      (`diff` exits 0). No chronological claim is made and none is needed: the
      task lands as one commit and the proof survives squashing.
      `test_baseline_file_exists` **fails, never skips**, when the JSON is
      missing (`test_the_matrix_module_never_skips` asserts `pytest.skip` does
      not appear in the module at all); `test_baseline_declares_its_provenance`
      and `test_baseline_covers_exactly_the_matrix` pass.
- [ ] **ER-5 — the baseline is the legacy map, so the chain closes.**
      Over the same JSON, `test_every_denied_cell_is_denied_in_the_baseline`
      asserts that every cell whose permission is **not** in
      `LEGACY_ROLE_PERMISSIONS[role]` recorded a `403`, unless the **cell** is
      in `DENIAL_SHAPE_OVERRIDES` — which is **exactly six entries, all
      GUEST**: `GET /api/v1/tasks/` → 200, and
      `PATCH /api/v1/tasks/{task_id}`,
      `GET /api/v1/tasks/{task_id}/history`,
      `GET /api/v1/tasks/{task_id}/comments`,
      `POST /api/v1/tasks/{task_id}/comments`,
      `PATCH /api/v1/tasks/{task_id}/comments/{comment_id}` → 404. (`GET
      /api/v1/votes/{id}/tally` is **not** among them: `TallyNotAvailableError`
      maps to 403 at `app/core/exception_handlers.py:157`.)
      `test_denial_shape_overrides_is_exactly_six`,
      `test_every_denial_shape_override_is_needed` (a declared entry that is
      not actually a denied cell with that recorded status fails) and
      `test_every_denial_shape_override_has_a_reason` pass. If the recorded
      baseline needs a seventh entry, or a different status for one of the six,
      that deviation and the production line that causes it are **named in the
      PR body** (same clause as the §6.2 isolation failures) and the test is
      renamed to the new literal count.
      `test_no_cell_is_5xx_in_the_baseline` asserts **no** recorded status is
      `>= 500`, with no allowlist, so a broken world cannot freeze into the
      golden file; `test_no_permitted_cell_is_422_in_the_baseline` asserts no
      cell whose permission **is** held recorded a `422` outside
      `PERMITTED_422`, which is pinned by exact set equality and bounded by
      `test_every_permitted_422_is_needed`,
      `test_every_permitted_422_has_a_reason` (naming the unsent body field or
      required query parameter) and `test_permitted_422_is_bounded`
      (`len <= 15`; expected `0`, measured value quoted in the PR body).
      `test_no_permitted_cell_is_403_in_the_baseline` asserts no cell whose
      permission **is** held recorded a `403` outside `NON_ROLE_403`, which is
      itself pinned by exact set equality, by
      `test_every_non_role_403_is_needed`, by
      `test_every_non_role_403_has_a_reason` (each naming a §5.2 dimension)
      and by `test_non_role_403_is_bounded` (`len <= 40`, measured value
      quoted in the PR body). Combined with F1's derived-parity test — green
      at the merge-base commit named in `_meta.merge_base_sha` and quoted in
      the PR body — this establishes
      `post-swap == baseline == pre-swap production` and
      `baseline denials == LEGACY_ROLE_PERMISSIONS`.
- [ ] **ER-6 — the two short-circuits behave as specified.**
      `get_effective_permissions` contains **no** `role == ADMINISTRATOR`
      branch: an ADMINISTRATOR resolves through `LEGACY_ROLE_PERMISSIONS`,
      which is `PERMISSIONS - ADMIN_GAP_PERMISSIONS`, so
      `GET /api/v1/packages/my-lots` still returns its current status for an
      ADMINISTRATOR (matrix cell). It **does** union
      `TENANT_ADMIN_PERMISSIONS` when `is_acting_tenant_admin` is true;
      `test_tenant_admin_permissions_are_exactly_the_apras43_routes` pins that
      constant to the seven APRAS-43 routes via `ROUTE_PERMISSIONS`, and
      `tests/test_effective_permissions.py` gains 3 cases (bridge grants the
      seven; grants nothing without an acting tenant; grants nothing in a
      tenant that did not grant the capability) with no existing case changed.
      `tests/test_tenant_admin.py` passes **unmodified**, including
      `test_tenant_admin_passes_every_admin_gated_route_in_their_tenant`
      (8 assertions, 200/200/200/201/200/204/204/204) and the two `[403]*7`
      matrices.
- [ ] **ER-7 — anti-escalation on both grant surfaces.**
      `UserTypeCreate`/`UserTypeUpdate`/`UserTypeRead` carry `permissions`
      (`list[str] | None = None` on Update, so an omitted field leaves the
      bundle untouched), validated against `PERMISSIONS` with a 422 on an
      unknown string. `user_type_service.assert_can_grant` runs on
      `POST /user-types/`, `PATCH /user-types/{id}` and on the
      `user_type_ids` path of `PATCH /users/{id}`, and
      `tests/test_permission_escalation.py` passes all 7 cases of §9.4 —
      notably: an author holding `user_types:create`/`user_types:update` and
      not `finance:category_create` gets **403** from
      `POST /api/v1/user-types/` with `"permissions": ["finance:category_create"]`,
      the body names the missing permission, and no row is created; the same
      author creating a group with only permissions they hold gets **201**
      and the bundle reads back; assigning an over-privileged existing group
      through `PATCH /users/{id}` is **403**.
- [ ] **ER-8 — special scopes preserved, existing suites unmodified.**
      A RESIDENT still sees only their linked lots' packages and a PORTEIRO is
      still condo-wide at the gate, proven by the *unmodified* suites:
      `git status --short -- backend/tests/` (equivalently
      `git diff --stat HEAD -- backend/tests/`; this task **stages and never
      commits**, so the worktree-only `git diff -- backend/tests/` an earlier
      draft named goes blank as soon as the files are staged and proves
      nothing) lists **only** these seven new files — three new test modules
      (`test_permission_parity_matrix.py`, `test_permission_enforcement.py`,
      `test_permission_escalation.py`), two new support modules
      (`matrix_world.py`, `tools/record_parity_baseline.py`), the new
      `tools/__init__.py`, and one new **data file**
      (`data/parity_matrix_baseline.json`, which is not a module) —
      plus the three F1 modules of §11 — `test_legacy_role_permissions.py`,
      `test_permission_registry.py` (2 amended assertions) and
      `test_effective_permissions.py` (additive only). In particular
      `test_tenant_isolation.py`, `test_tenant_route_scope.py`,
      `test_tenant_admin.py`, `test_menu_access.py`,
      `test_role_type_permissions.py`, `test_migrations_postgres.py`,
      `test_porteiro_role.py`, `test_gatekeeper.py`, `test_packages*.py` and
      every `test_*_rbac.py` are byte-identical to the merge base and pass.
- [ ] **ER-9 — nothing else moves, and the suite is green.**
      `git status --short -- frontend/` is empty (the same stage-aware form as
      ER-8); no file is added under
      `backend/alembic/versions/` and `alembic heads` still reports the single
      head `0030_add_user_type_permissions`; the four `SCOPE_PERMISSIONS`
      (`residents:read_any_lot`, `visitors:manage_any_lot`,
      `occurrences:manage_all`, `uploads:auto_approve`) are the only new
      permission strings, are not route-mapped, and each has a
      `LEGACY_ROLE_PERMISSIONS` entry.
      `uv run pytest --cov=app` is green with **0 failures**, and the
      collected-test count is **at least `M − R + 1080 + 30`**, where:
      `M` is `uv run pytest --collect-only -q | tail -1` run in a clean
      worktree at `_meta.merge_base_sha`
      (`git worktree add /tmp/apras-mb <merge_base_sha>`) — **measured
      `M = 1260`** on the merge-base tree (APRAS-38 + APRAS-45; **not**
      inherited from F1's `1052 passed / 18 skipped`);
      `R = 156` is the **net retirement §7.2 forces** in
      `tests/test_legacy_role_permissions.py`, which goes **162 → 6** collected
      cases (157 deleted — the 152-case `test_legacy_map_matches_the_live_guards`
      parametrisation plus the five source-shape tests that evaluate
      `PARITY_SOURCES`, itemised in §7.2's table — and 1 added), because this
      slice deletes the production role-set constants and guards those cases
      read; `1080` is one parametrised case per matrix cell; and `30` is a
      deliberately loose integer floor for the new structural, oracle,
      provenance, 5xx/422 and escalation cases (this spec names roughly forty
      such cases, so the floor is a floor and not a target).
      With the measured values the floor is **≥ 2214**. Two mechanical
      cross-checks accompany it:
      `uv run pytest --collect-only -q tests/test_legacy_role_permissions.py`
      reports exactly **6**, and no *other* pre-existing test module's
      collected count decreases (per-module collection compared against the
      same merge-base worktree). `M`, `R`, the post-change count and
      `merge_base_sha` are quoted in the PR body. Total coverage
      is **≥ 90 %** and no more than 0.5 pp below the merge-base total, with
      both measured numbers quoted in the PR body. `ruff check` is clean on every file this task touches.

---

## Out of scope

`is_superuser` (F3), the tenant_admin widening to all in-tenant permissions
(F3), the groups management UI and permission-based frontend gating (F4),
renaming groups to roles and dropping `user.role` / `allowed_menus` (F5),
seeding any default bundle (never — the user's standing decision), per-user
loose permissions, role nesting, tightening any of the 17 all-six
permissions, and exposing permissions on `GET /auth/me`.
