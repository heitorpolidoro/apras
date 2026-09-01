# APRAS-45 — IAM F1: permission catalogue, the `user_type.permissions` column, and the transitional legacy-role map

> **The board title is stale.** It says *"com backfill dos roles atuais"*. The
> user's final decision is the opposite: **nothing is seeded, ever** — not the
> six mirror roles, not a default bundle. Transitional compatibility lives in a
> **code** map (`LEGACY_ROLE_PERMISSIONS`) that dies in F5. This spec
> implements the decision, not the title.

Slice 1 of the GCP-style IAM chain: **fine permissions in code → roles
(permission bundles) as data → users N:N roles**. This slice builds the
vocabulary and the plumbing. It changes **no** authorization outcome.

---

## 1. Scope

**In scope**

1. `backend/app/core/permissions.py` — the permission registry: the frozen
   catalogue of permission strings (§4), the `(method, path) → permission`
   route map, the `UNGUARDED_ROUTES` allowlist, and the transitional
   `LEGACY_ROLE_PERMISSIONS` map (§6).
2. `backend/tests/test_permission_registry.py` — the "a new router without
   declared permissions fails CI" test (§5).
3. `backend/tests/test_legacy_role_permissions.py` — the parity test proving
   each legacy set equals that role's capabilities *today*, derived from the
   live production guards, not from a hand copy (§6.3).
4. `UserType.permissions` (JSON, NOT NULL, `server_default='[]'`) on the model
   plus Alembic migration `0030_add_user_type_permissions` on head
   `0029_add_is_tenant_admin` (§7).
5. `deps.get_effective_permissions(user, session)` — union of the user's roles'
   permissions in the acting tenant and the legacy fallback (§8).
6. Migration-gated Postgres tests appended to `tests/test_migrations_postgres.py`
   (§7.3), and a "nothing is seeded" test (§7.4).

**Explicitly NOT in scope**

* **No enforcement.** Not one guard, router, service or `Depends` changes
  behaviour. `get_effective_permissions` has exactly **zero** production call
  sites in this slice; it is exercised by tests only. Enforcement is F4.
* **No `is_superuser` / no `is_tenant_admin` shortcut** inside
  `get_effective_permissions`. Those arrive in F3 (the user's decision). A
  tenant_admin's permissions in this slice are exactly what their roles and
  their `user.role` legacy set give them.
* **No API surface change.** No request or response schema gains
  `permissions`; no roles-management endpoint; `UserTypeCreate` /
  `UserTypeUpdate` / `UserTypeRead` are untouched (asserted in §9.3). Writing
  permissions onto a role is a later slice.
* **No seeding, no backfill, no data migration.** `0030` adds a column and
  nothing else. `app/seed.py` is not touched.
* **No frontend.** Zero files under `frontend/`.
* **No role nesting and no per-user loose permissions** — neither is
  representable by anything this slice adds.
* **No change to the UserType `allowed_menus` menu gate**, to `Task.visible_to`
  filtering, to per-lot linkage, ownership or authorship rules. §6.2 defines
  precisely why the catalogue models the *role dimension only*.

**Dependency.** APRAS-38 (staged frontend tenant switcher + `auth/me` tenants)
lands first. Nothing here depends on it semantically; it is a merge-order fact.
Baseline for this task is the tree **with 38 applied** (§10.1).

---

## 2. Files touched

| File | Change |
|---|---|
| `backend/app/core/permissions.py` | **new** — registry (pure data + pure functions; no DB, no FastAPI imports) |
| `backend/app/models/user_type.py` | `permissions` JSON column |
| `backend/alembic/versions/0030_add_user_type_permissions.py` | **new** |
| `backend/app/api/deps.py` | `get_effective_permissions(user, session)` |
| `backend/tests/test_permission_registry.py` | **new** |
| `backend/tests/test_legacy_role_permissions.py` | **new** |
| `backend/tests/test_effective_permissions.py` | **new** |
| `backend/tests/test_migrations_postgres.py` | **the only pre-existing file edited** — append the `0030` section at EOF, **plus a two-line head-pin update**: `0030` moves the Alembic head, so the two existing `== "0029_add_is_tenant_admin"` assertions become `== "0030_add_user_type_permissions"`. Those two lines are the only change inside any pre-existing test function (§9.1) |

Nothing else. In particular: no endpoint module, no service module.

---

## 3. Naming convention

```
<module>:<action>        e.g. tasks:read, purchases:decide, gate:checkin
```

* `^[a-z][a-z0-9_]*:[a-z][a-z0-9_]*$` — asserted by a test over the whole
  catalogue. Exactly one colon; `snake_case` on both sides.
* The four verbs `read` / `create` / `update` / `delete` are used whenever the
  route is plain CRUD on the module's main resource.
* Everything else gets a **named domain action** (`purchases:decide`,
  `votes:close`, `gate:checkin`, `packages:pickup`, `assemblies:close`,
  `finance:invoice_upload`, …). Sub-resource CRUD is a named action carrying
  the sub-resource (`projects:milestone_create`, `documents:folder_delete`),
  never a second colon.
* The module segment is the **domain that owns the guard**, which is not always
  the URL prefix. `GET|POST|DELETE /api/v1/lots/{lot_id}/voter-eligibility` is
  guarded by `voting_service._assert_can_manage_eligibility`, so its
  permissions are `votes:eligibility_*`, not `lots:*`. This is a deliberate,
  documented deviation and there are exactly three such routes.

---

## 4. The catalogue (complete enumeration)

Every string below is a member of `PERMISSIONS: frozenset[str]`. Columns:

* **Legacy roles** — the roles that hold the permission in
  `LEGACY_ROLE_PERMISSIONS` today. `A`=ADMINISTRATOR, `D`=DIRECTOR,
  `M`=MANAGER, `G`=GUEST, `R`=RESIDENT, `P`=PORTEIRO. `ALL` = all six.
* **Source** — the live production object the parity test derives that set
  from (§6.3). `unguarded` = the route has no role gate at all today.

F2 builds its parity matrix from this table; it is exhaustive by construction
(§5 fails CI if a route is missing from it).

### 4.1 tasks — `/api/v1/tasks` (8 routes, menu-gated by `MenuKey.TASKS`)

| Permission | Routes | Legacy roles | Source |
|---|---|---|---|
| `tasks:read` | `GET /tasks/`, `GET /tasks/{id}/history`, `GET /tasks/{id}/comments` | A D M R P | **composite** — guard `deps.assert_manager_can_see_task` (GUEST → `TaskNotFoundError`) ∧ literal for the inline `role == GUEST → []` in `list_tasks` (§6.3 `Composite`) |
| `tasks:create` | `POST /tasks/` | A D M R P | **literal** — inline `role == GUEST` in `endpoints/tasks.py::create_task`; one of only two sanctioned inline-gate literals (§6.3) |
| `tasks:update` | `PATCH /tasks/{id}` | A D M R P | guard `deps.assert_can_edit_task` |
| `tasks:delete` | `DELETE /tasks/{id}` | A | guard `deps.get_current_tenant_admin` (role dimension: ADMINISTRATOR) |
| `tasks:comment` | `POST /tasks/{id}/comments`, `PATCH /tasks/{id}/comments/{cid}` | A D M R P | guard `deps.assert_can_edit_task` |

### 4.2 categories — `/api/v1/categories` (4 routes, menu-gated by `MenuKey.CATEGORIES`)

| Permission | Routes | Legacy roles | Source |
|---|---|---|---|
| `categories:read` | `GET /categories/` | ALL | unguarded (menu gate only, not a role gate) |
| `categories:create` | `POST /categories/` | A D | role set `endpoints.categories._CATEGORY_WRITE_ROLES` |
| `categories:update` | `PATCH /categories/{id}` | A D | same |
| `categories:delete` | `DELETE /categories/{id}` | A D | same |

### 4.3 users — `/api/v1/users` (3 routes)

| Permission | Routes | Legacy roles | Source |
|---|---|---|---|
| `users:read` | `GET /users/` | ALL | unguarded (tenant-scoped directory, no role gate) |
| `users:update` | `PATCH /users/{id}` | A | guard `deps.get_current_tenant_admin` |
| `users:update_contact` | `PATCH /users/{id}/contact-info` | A M | guard `deps.get_current_tenant_admin_or_manager` |

### 4.4 user_types — `/api/v1/user-types` (4 routes)

| Permission | Routes | Legacy roles | Source |
|---|---|---|---|
| `user_types:read` | `GET /user-types/` | ALL | unguarded |
| `user_types:create` | `POST /user-types/` | A | guard `deps.get_current_tenant_admin` |
| `user_types:update` | `PATCH /user-types/{id}` | A | same |
| `user_types:delete` | `DELETE /user-types/{id}` | A | same |

### 4.5 tenants — `/api/v1/tenants` (8 routes, globally scoped)

| Permission | Routes | Legacy roles | Source |
|---|---|---|---|
| `tenants:read` | `GET /tenants`, `GET /tenants/{id}` | ALL | unguarded (visibility narrowed per role inside `TenantService`) |
| `tenants:create` | `POST /tenants` | A | guard `deps.get_current_active_admin` |
| `tenants:update` | `PATCH /tenants/{id}` | A | same |
| `tenants:members_read` | `GET /tenants/{id}/members` | ALL | unguarded |
| `tenants:members_manage` | `POST /tenants/{id}/members`, `DELETE /tenants/{id}/members/{uid}` | A | guard `deps.get_current_active_admin` |
| `tenants:members_set_admin` | `PATCH /tenants/{id}/members/{uid}` | A | same |

### 4.6 lots — `/api/v1/lots` (11 routes; 3 of them belong to `votes:*`, §4.13)

| Permission | Routes | Legacy roles | Source |
|---|---|---|---|
| `lots:read` | `GET /lots/`, `GET /lots/{id}` | A D M P | role set `endpoints.lots._LOT_READ_ROLES` |
| `lots:create` | `POST /lots/` | A D | role set `endpoints.lots._LOT_WRITE_ROLES` |
| `lots:update` | `PUT /lots/{id}` | A D | same |
| `lots:delete` | `DELETE /lots/{id}` | A | guard `deps.get_current_tenant_admin` |
| `lots:link_user` | `POST /lots/{id}/users` | A D | role set `_LOT_WRITE_ROLES` |
| `lots:unlink_user` | `DELETE /lots/{id}/users/{uid}` | A D | same |
| `lots:set_delinquency` | `PATCH /lots/{id}/delinquency` | A D | role set `voting_service.BOARD_ROLES` |

### 4.7 residents — `/api/v1/lots/{lot_id}/residents`, `/api/v1/residents` (7 routes)

| Permission | Routes | Legacy roles | Source |
|---|---|---|---|
| `residents:read` | `GET /lots/{id}/residents`, `GET /residents/{id}` | ALL | guard `resident_service.ResidentService._check_lot_access` (A/D/M pass unconditionally; every other role passes when linked to the lot — §6.2) |
| `residents:create` | `POST /lots/{id}/residents` | A D | guard `endpoints.residents.assert_admin_or_director` |
| `residents:update` | `PUT /residents/{id}` | A D | same |
| `residents:delete` | `DELETE /residents/{id}` | A D | same |
| `residents:link_user` | `POST /residents/{id}/link-user` | A D | same |
| `residents:unlink_user` | `POST /residents/{id}/unlink-user` | A D | same |

### 4.8 visitors — `/api/v1/visitors` (4 routes)

| Permission | Routes | Legacy roles | Source |
|---|---|---|---|
| `visitors:read` | `GET /visitors`, `GET /visitors/{id}` | ALL | unguarded — **there is no role gate on the visitor directory today** |
| `visitors:create` | `POST /visitors` | ALL | unguarded |
| `visitors:update` | `PUT /visitors/{id}` | ALL | unguarded |

### 4.9 authorizations — `/api/v1/lots/{lot_id}/authorizations`, `/api/v1/authorizations` (5 routes)

| Permission | Routes | Legacy roles | Source |
|---|---|---|---|
| `authorizations:read` | `GET /lots/{id}/authorizations` | A D M G R | **single** `Guard` on `endpoints.authorizations._assert_not_porteiro` |
| `authorizations:create` | `POST /lots/{id}/authorizations` | A D M G R | same |
| `authorizations:revoke` | `PUT /authorizations/{id}/revoke` | A D M G R | same |
| `authorizations:gate_lookup` | `GET /authorizations/{id}`, `GET /authorizations/{id}/qr-code` | ALL | `Guard` on `VisitorService.get_authorization_for_user` (PORTEIRO is *deliberately* allowed here — it is the gate's lookup) |

These four routes pass through **two** checks in production —
`_assert_not_porteiro` and `VisitorService._check_lot_access` — but the parity
source for the first three is a **single `Guard`**, not a third `Composite`.
`_check_lot_access` is an **object-dimension** narrowing (is the caller linked
to this lot?), which §6.2 leaves in code and §6.5 neutralises by seeding the
link for all six roles; it refuses no role in the most favourable object
situation, so it contributes nothing to the intersection and adding it as a
`Composite` part would say nothing while implying that it does. `Composite` is
reserved for the two genuinely heterogeneous **role-dimension** gates of §6.3
(`tasks:read`, `announcements:comment`) — there are exactly two, and §4.9 is not
a third. `authorizations:gate_lookup` is a `Guard` on the higher-level
`get_authorization_for_user`, which contains the PORTEIRO bypass that is the
whole point of the row; it needs a persisted authorization row (§6.5(b)).

### 4.10 gate — `/api/v1/access-logs` (3 routes)

| Permission | Routes | Legacy roles | Source |
|---|---|---|---|
| `gate:checkin` | `POST /access-logs/check-in` | A D M P | guard `endpoints.access_logs._assert_gatekeeper_access` |
| `gate:checkout` | `POST /access-logs/check-out` | A D M P | same |
| `gate:logs_read` | `GET /access-logs` | ALL | guard `VisitorService.get_access_logs` — **filter, not refusal** (see below) |

`gate:logs_read` is **all six roles**, and the asymmetry with its two siblings is
real, not a typo. `endpoints.access_logs.list_access_logs` — unlike
`check_in_visitor` and `check_out_visitor` — does **not** call
`_assert_gatekeeper_access`; the only role logic on that path is inside
`VisitorService.get_access_logs` (`app/services/visitor_service.py:452-487`),
which for a non-A/D/M caller *narrows the query* to
`get_user_linked_lot_ids(...)` and raises `ForbiddenError` only when an
**explicit foreign `lot_id`** was requested. Called in the most favourable
object situation of §6.2 — `lot_id=None` — no role raises, so under §6.3's
`Guard` semantics ("granted" == "did not raise") every role is granted. This is
the same filter-not-refuse shape already recorded for `feedback:read` (narrowed
to own rows) and `tenants:read` (narrowed inside `TenantService`); the per-lot
narrowing is an **object-dimension** restriction that §6.2 explicitly leaves in
code. A PORTEIRO-only reading of this route would be a tightening, and this
slice must not tighten (§11.4).

### 4.11 occurrences — `/api/v1/occurrences` (5 routes)

| Permission | Routes | Legacy roles | Source |
|---|---|---|---|
| `occurrences:read` | `GET /occurrences`, `GET /occurrences/{id}` | A D M G R | guard `endpoints.occurrences._assert_not_porteiro` |
| `occurrences:create` | `POST /occurrences` | A D M G R | same |
| `occurrences:update_status` | `PUT /occurrences/{id}/status` | A D M G R | same |
| `occurrences:add_note` | `POST /occurrences/{id}/timeline` | A D M G R | same |

### 4.12 documents — `/api/v1/documents` (9 routes)

| Permission | Routes | Legacy roles | Source |
|---|---|---|---|
| `documents:read` | `GET /documents` | A D M G R | guard `endpoints.documents._assert_not_porteiro` (+ per-folder `allowed_roles_json`, §6.2) |
| `documents:create` | `POST /documents` | A D | guard `document_service._check_admin_or_director` |
| `documents:delete` | `DELETE /documents/{id}` | A D | same |
| `documents:download` | `POST /documents/{id}/download` | A D M G R | guard `_assert_not_porteiro` |
| `documents:version_create` | `POST /documents/{id}/versions` | A D | guard `document_service._check_admin_or_director` |
| `documents:folder_read` | `GET /documents/folders` | A D M G R | guard `_assert_not_porteiro` |
| `documents:folder_create` | `POST /documents/folders` | A D | guard `document_service._check_admin_or_director` |
| `documents:folder_update` | `PUT /documents/folders/{id}` | A D | same |
| `documents:folder_delete` | `DELETE /documents/folders/{id}` | A D | same |

### 4.13 votes & assemblies — `/api/v1/votes`, `/api/v1/assemblies`, 3 `/lots/…/voter-eligibility` routes (20 routes)

| Permission | Routes | Legacy roles | Source |
|---|---|---|---|
| `assemblies:read` | `GET /assemblies/`, `GET /assemblies/{id}` | A D M R | guard `endpoints.voting._require_voting_access` |
| `assemblies:create` | `POST /assemblies/` | A D | guard `voting_service._assert_board` |
| `assemblies:update` | `PATCH /assemblies/{id}` | A D | same |
| `assemblies:close` | `POST /assemblies/{id}/close` | A D | same |
| `assemblies:minutes_read` | `GET /assemblies/{id}/minutes` | A D | same |
| `assemblies:minutes_save` | `POST /assemblies/{id}/minutes/save` | A D | same |
| `votes:read` | `GET /votes/`, `GET /votes/{id}` | A D M R | guard `_require_voting_access` |
| `votes:create` | `POST /votes/` | A D M | guard `voting_service._assert_can_create_vote` bound to `VoteKind.ENQUETE` (assembly-kind votes additionally require the board — a payload-dependent narrowing that stays in code, §6.2) |
| `votes:update` | `PATCH /votes/{id}` | A D M | same |
| `votes:close` | `POST /votes/{id}/close` | A D M | same |
| `votes:cast` | `POST /votes/{id}/ballots` | A D M R | **`RoleSetComplement`** of `voting_service.NON_VOTING_ROLES` (`= (GUEST, PORTEIRO)`) — §6.3 |
| `votes:retract` | `POST /votes/{id}/ballots/retract` | A D M R | same |
| `votes:tally_read` | `GET /votes/{id}/tally` | A D M R | guard `voting_service._assert_can_view_tally` |
| `votes:my_ballot_read` | `GET /votes/{id}/my-ballot` | A D M R | guard `_require_voting_access` |
| `votes:eligible_lots_read` | `GET /votes/{id}/eligible-lots` | A D M R | same |
| `votes:eligibility_read` | `GET /lots/{id}/voter-eligibility` | A D M | guard `voting_service._assert_can_manage_eligibility` |
| `votes:eligibility_manage` | `POST /lots/{id}/voter-eligibility`, `DELETE /lots/{id}/voter-eligibility/{uid}` | A D M | same |

### 4.14 finance — `/api/v1/finance` (18 routes)

| Permission | Routes | Legacy roles | Source |
|---|---|---|---|
| `finance:read` | `GET /finance/categories`, `/budget-lines`, `/transactions`, `/transactions/{id}`, `/balance`, `/statement`, `/budget-vs-actual`, `/budget-vs-actual/{cid}/transactions` | A D M R | role set `endpoints.finance._FINANCE_READ_ROLES` |
| `finance:category_create` | `POST /finance/categories` | A D | role set `_FINANCE_ADMIN_ROLES` |
| `finance:category_update` | `PUT /finance/categories/{id}` | A D | same |
| `finance:budget_create` | `POST /finance/budget-lines` | A D | same |
| `finance:budget_update` | `PUT /finance/budget-lines/{id}` | A D | same |
| `finance:budget_delete` | `DELETE /finance/budget-lines/{id}` | A D | same |
| `finance:transaction_create` | `POST /finance/transactions` | A D M | role set `_FINANCE_WRITE_ROLES` |
| `finance:transaction_update` | `PUT /finance/transactions/{id}` | A D M | same (MANAGER additionally limited to own transactions by `_require_transaction_edit_permission`, §6.2) |
| `finance:transaction_delete` | `DELETE /finance/transactions/{id}` | A D | role set `_FINANCE_ADMIN_ROLES` |
| `finance:invoice_upload` | `POST /finance/transactions/{id}/invoice` | A D M | role set `_FINANCE_WRITE_ROLES` |
| `finance:invoice_delete` | `DELETE /finance/transactions/{id}/invoice` | A D M | same |

`GET /finance/categories?include_inactive=true` narrows to `_FINANCE_ADMIN_ROLES`
inside the handler. That is a **query-parameter** narrowing of one route, not a
second permission; it stays in code and is called out here so F2 does not
mistake it for a gap.

### 4.15 projects — `/api/v1/projects` (10 routes)

| Permission | Routes | Legacy roles | Source |
|---|---|---|---|
| `projects:read` | `GET /projects`, `GET /projects/{id}` | A D M R | role set `endpoints.projects._PROJECT_READ_ROLES` |
| `projects:create` | `POST /projects` | A D | role set `_PROJECT_ADMIN_ROLES` |
| `projects:update` | `PUT /projects/{id}` | A D | same |
| `projects:delete` | `DELETE /projects/{id}` | A D | same |
| `projects:milestone_create` | `POST /projects/{id}/milestones` | A D | same |
| `projects:milestone_update` | `PUT /projects/{id}/milestones/{mid}` | A D | same |
| `projects:milestone_delete` | `DELETE /projects/{id}/milestones/{mid}` | A D | same |
| `projects:update_create` | `POST /projects/{id}/updates` | A D M | role set `_PROJECT_UPDATE_ROLES` |
| `projects:update_delete` | `DELETE /projects/{id}/updates/{uid}` | A D | role set `_PROJECT_ADMIN_ROLES` |

### 4.16 announcements — `/api/v1/announcements` (12 routes)

| Permission | Routes | Legacy roles | Source |
|---|---|---|---|
| `announcements:read` | `GET /announcements`, `GET /announcements/{id}`, `GET /announcements/{id}/comments` | A D M G R | guard `endpoints.announcements._assert_not_porteiro` |
| `announcements:create` | `POST /announcements` | A D | guard `announcement_service._check_publisher` |
| `announcements:update` | `PUT /announcements/{id}` | A D | same |
| `announcements:delete` | `DELETE /announcements/{id}` | A D | same |
| `announcements:media_upload` | `POST /announcements/{id}/media` | A D | same |
| `announcements:media_delete` | `DELETE /announcements/{id}/media/{mid}` | A D | same |
| `announcements:comment` | `POST /announcements/{id}/comments` | A D M R | **composite** — guard `endpoints.announcements._assert_not_porteiro` (denies PORTEIRO) ∧ literal for the inline GUEST rejection in `announcement_service.add_comment` (§6.3 `Composite`) |
| `announcements:comment_delete` | `DELETE /announcements/comments/{cid}` | A D M G R | guard `_assert_not_porteiro` (author-or-publisher narrowing in code) |
| `announcements:mark_read` | `POST /announcements/{id}/read` | A D M G R | same |
| `announcements:read_receipts_read` | `GET /announcements/{id}/read-receipts` | A D | guard `announcement_service._check_publisher` |

### 4.17 feedback — `/api/v1/feedback` (4 routes)

| Permission | Routes | Legacy roles | Source |
|---|---|---|---|
| `feedback:read` | `GET /feedback`, `GET /feedback/{id}` | ALL | unguarded (non-A/D callers are narrowed to their own rows) |
| `feedback:create` | `POST /feedback` | ALL | unguarded |
| `feedback:respond` | `PUT /feedback/{id}/respond` | A D | guard `feedback_service.respond_to_feedback` role gate |

### 4.18 spaces & reservations — `/api/v1/reservable-spaces`, `/api/v1/space-reservations` (10 routes)

| Permission | Routes | Legacy roles | Source |
|---|---|---|---|
| `spaces:read` | `GET /reservable-spaces/` | ALL | unguarded |
| `spaces:create` | `POST /reservable-spaces/` | A D | role set `endpoints.reservations._SPACE_WRITE_ROLES` |
| `spaces:update` | `PATCH /reservable-spaces/{id}` | A D | same |
| `spaces:deactivate` | `DELETE /reservable-spaces/{id}` | A D | same |
| `reservations:read` | `GET /space-reservations/`, `GET /space-reservations/{id}` | A D M R P | guard `endpoints.reservations._require_non_guest` |
| `reservations:create` | `POST /space-reservations/` | A D M R P | same |
| `reservations:approve` | `POST /space-reservations/{id}/approve` | A D | role set `reservation_service._STAFF_ROLES` |
| `reservations:reject` | `POST /space-reservations/{id}/reject` | A D | same |
| `reservations:cancel` | `POST /space-reservations/{id}/cancel` | A D M R P | guard `_require_non_guest` (owner-or-staff narrowing in code) |

### 4.19 packages — `/api/v1/packages` (6 routes)

| Permission | Routes | Legacy roles | Source |
|---|---|---|---|
| `packages:read` | `GET /packages`, `GET /packages/{id}` | A D M R P | guard `PackageService._assert_lot_access` (GUEST refused even when linked) |
| `packages:create` | `POST /packages` | A D M P | guard `PackageService._assert_gatekeeper_role` |
| `packages:pickup` | `POST /packages/{id}/pickup` | A D M R P | guard `PackageService._assert_lot_access` |
| `packages:queue_read` | `GET /packages/queue` | A D M P | guard `PackageService._assert_gatekeeper_role` |
| `packages:my_lots_read` | `GET /packages/my-lots` | **R** | guard `PackageService.get_my_lots` role gate (**inverted gate** — see below) |

`packages:my_lots_read` is **RESIDENT only**, and it is the one permission in
this catalogue that ADMINISTRATOR does *not* hold. `PackageService.get_my_lots`
(`app/services/package_service.py:203-211`) is an **inverted** gate: it raises
`PackageAccessForbiddenError` when the caller's role is in
`PackageService._GATEKEEPER_ROLES` (`ADMINISTRATOR`, `DIRECTOR`, `MANAGER`,
`PORTEIRO` — "Use /packages/queue para ver encomendas de todos os lotes.") and
again when the role is `GUEST`. Six roles minus those five leaves `{RESIDENT}`.
The route is a *personal* view, deliberately routed away from staff towards
`GET /packages/queue` (`packages:queue_read`, A/D/M/P), so the two together
still cover every role. This is recorded as-is; §6.3 assertion 6 carries the
consequence, and §11.5 records why it is not "fixed" here.

### 4.20 assets & inventory — `/api/v1/assets`, `/api/v1/inventory-movements` (8 routes)

| Permission | Routes | Legacy roles | Source |
|---|---|---|---|
| `assets:read` | `GET /assets`, `GET /assets/{id}` | A D M | role set `asset_service._VIEW_ROLES` |
| `assets:summary_read` | `GET /assets/summary` | A D M | same |
| `assets:create` | `POST /assets` | A D | role set `asset_service._STAFF_ROLES` |
| `assets:update` | `PUT /assets/{id}` | A D | same |
| `assets:delete` | `DELETE /assets/{id}` | A D | same |
| `assets:movement_record` | `POST /assets/{id}/movements` | A D M | role set `_VIEW_ROLES` (MANAGER restricted to a movement-type subset in code) |
| `inventory:movements_read` | `GET /inventory-movements` | A D M | same |

### 4.21 purchases — `/api/v1/purchase-requests` (11 routes)

| Permission | Routes | Legacy roles | Source |
|---|---|---|---|
| `purchases:read` | `GET /purchase-requests`, `GET /purchase-requests/{id}` | A D M | role set `purchase_service._VIEW_ROLES` |
| `purchases:summary_read` | `GET /purchase-requests/summary` | A D M | same |
| `purchases:create` | `POST /purchase-requests` | A D M | role set `purchase_service._WRITE_ROLES` |
| `purchases:update` | `PUT /purchase-requests/{id}` | A D M | same (MANAGER limited to own open requests in code) |
| `purchases:delete` | `DELETE /purchase-requests/{id}` | A D M | same |
| `purchases:quote_create` | `POST /purchase-requests/{id}/quotes` | A D M | same |
| `purchases:quote_update` | `PUT /purchase-requests/{id}/quotes/{qid}` | A D M | same |
| `purchases:quote_delete` | `DELETE /purchase-requests/{id}/quotes/{qid}` | A D M | same |
| `purchases:decide` | `POST /purchase-requests/{id}/decision` | A D | role set `purchase_service._DECIDE_ROLES` |
| `purchases:cancel` | `POST /purchase-requests/{id}/cancel` | A D | same — **cancel is a decide-level action today**, not a write-level one |

### 4.22 uploads (media) — `/api/v1/uploads` (6 routes)

| Permission | Routes | Legacy roles | Source |
|---|---|---|---|
| `uploads:photo_create` | `POST /uploads/photo` | ALL | unguarded (A/D/M auto-approve, everyone else lands PENDING) |
| `uploads:photo_read` | `GET /uploads/photos/{id}` | ALL | unguarded |
| `uploads:pending_read` | `GET /uploads/photos/pending` | A D | guard `MediaService.list_pending_photos` role gate |
| `uploads:approve` | `PUT /uploads/photos/{id}/approve` | A D | guard `MediaService.approve_photo` role gate |
| `uploads:reject` | `PUT /uploads/photos/{id}/reject` | A D | guard `MediaService.reject_photo` role gate |
| `uploads:delete` | `DELETE /uploads/photos/{id}` | ALL | guard `MediaService.delete_photo` (owner-or-A/D) |

### 4.23 access_control — `/api/v1/access-control` (7 guarded routes, plus `POST /access-control/webhook/verification`, which is device-authenticated and therefore in `UNGUARDED_ROUTES`, §4.24)

| Permission | Routes | Legacy roles | Source |
|---|---|---|---|
| `access_control:devices_read` | `GET /access-control/devices` | A D M | guard `access_control_service._assert_admin_director_or_manager` |
| `access_control:device_create` | `POST /access-control/devices` | A D | guard `access_control_service._assert_admin_or_director` |
| `access_control:device_update_status` | `PUT /access-control/devices/{id}/status` | A D | same |
| `access_control:device_regenerate_key` | `POST /access-control/devices/{id}/regenerate-key` | A D | same |
| `access_control:facial_template_read` | `GET /access-control/residents/{id}/facial-template` | A D M | guard `_assert_admin_director_or_manager` |
| `access_control:facial_template_sync` | `POST /access-control/residents/{id}/facial-template/sync` | A D | guard `_assert_admin_or_director` |
| `access_control:events_read` | `GET /access-control/events` | A D M | guard `_assert_admin_director_or_manager` |

### 4.24 `UNGUARDED_ROUTES` — the 10 routes that map to no permission

```
("GET",  "/")                                     # liveness
("GET",  "/api/v1/health")                        # liveness
("POST", "/api/v1/auth/login")                    # unauthenticated
("POST", "/api/v1/auth/signup")                   # unauthenticated
("POST", "/api/v1/auth/forgot-password")          # unauthenticated
("POST", "/api/v1/auth/reset-password")           # unauthenticated
("GET",  "/api/v1/auth/dev-users")                # unauthenticated dev helper
("POST", "/api/v1/auth/dev-login")                # unauthenticated dev helper
("GET",  "/api/v1/auth/me")                       # strictly self-scoped
("POST", "/api/v1/access-control/webhook/verification")  # X-Device-Key, no user
```

Each entry carries an inline reason comment, exactly like
`test_tenant_route_scope.GLOBAL_ROUTES`. Growing this list is a reviewable
decision, and §5 asserts its exact length.

---

## 5. `app/core/permissions.py` and the "undeclared router fails CI" test

### 5.1 Module contents

```python
PERMISSIONS: frozenset[str]                          # §4, the whole catalogue
ROUTE_PERMISSIONS: dict[tuple[str, str], str]        # (METHOD, path) -> permission
UNGUARDED_ROUTES: frozenset[tuple[str, str]]         # §4.24
LEGACY_ROLE_PERMISSIONS: dict[UserRole, frozenset[str]]   # §6, TRANSITIONAL
LEGACY_MAP_REMOVAL_SLICE: str = "IAM F5"             # the marker, asserted in §6.4
```

Plus two pure helpers:

```python
def permission_for_route(method: str, path: str) -> str | None: ...
def module_of(permission: str) -> str: ...
```

The module imports **only** `app.models.enums.UserRole`. No FastAPI, no
SQLModel, no session: it must stay importable from Alembic, from a script and
from a test that has no database.

`ROUTE_PERMISSIONS` keys use the FastAPI **route template** path exactly as
`APIRoute.path` yields it (`/api/v1/tasks/{task_id}`), which is the same key
shape `test_tenant_route_scope.py` already uses.

### 5.2 `backend/tests/test_permission_registry.py`

Mirrors `test_tenant_route_scope.py` deliberately — same file layout, same
`_api_routes()` walk — because that is the pattern this repo already reviews
and trusts.

1. `test_every_route_is_declared_or_unguarded` — for every `APIRoute` in
   `app.main.app`, every `(method, path)` key is in `ROUTE_PERMISSIONS` **xor**
   in `UNGUARDED_ROUTES`. **This is the test that fails when a new router ships
   without declared permissions.** Failure message lists the offending keys.
2. `test_no_stale_registry_entries` — every key of `ROUTE_PERMISSIONS` and every
   member of `UNGUARDED_ROUTES` names a route that exists.
3. `test_every_declared_permission_is_in_the_catalogue` —
   `set(ROUTE_PERMISSIONS.values()) <= PERMISSIONS`.
4. `test_every_catalogue_permission_is_reachable` — `PERMISSIONS ==
   set(ROUTE_PERMISSIONS.values())`. No dead vocabulary; F2's matrix is exactly
   the route surface.
5. `test_permission_strings_follow_the_convention` — regex of §3 over
   `PERMISSIONS`.
6. `test_unguarded_allowlist_is_ten_routes` — `len(UNGUARDED_ROUTES) == 10`.
7. `test_route_count_is_fully_accounted_for` — `len(ROUTE_PERMISSIONS) +
   len(UNGUARDED_ROUTES)` equals the total number of `(method, path)` keys, and
   the two sets are disjoint. Measured on the APRAS-38 staged tree for this
   spec: **190** total, hence `len(ROUTE_PERMISSIONS) == 180` and
   `len(UNGUARDED_ROUTES) == 10`. The test recomputes the total from
   `app.main.app` rather than hard-coding 190, so it stays true if the baseline
   shifts; 190/180/10 is the number to expect on first green run, and a
   surprise here means a router moved.
8. `test_every_router_module_has_at_least_one_permission` — group routes by
   their first tag; every tag has at least one mapped permission or is entirely
   inside `UNGUARDED_ROUTES` (`auth`, `health`).

Test 1 is the ER-bearing one; 2–8 keep it from rotting.

---

## 6. `LEGACY_ROLE_PERMISSIONS` — the transitional map

### 6.1 Shape

```python
# TRANSITIONAL (IAM F1 -> F5). Delete this map, and every reference to it,
# in slice F5. It exists so that F1..F4 can compute permissions for users who
# hold no role rows at all, because NOTHING is seeded: a fresh tenant's roles
# carry no permissions, by the user's explicit decision.
LEGACY_ROLE_PERMISSIONS: dict[UserRole, frozenset[str]] = { ... }
LEGACY_MAP_REMOVAL_SLICE = "IAM F5"
```

One entry per `UserRole` member — all six, including `RESIDENT` and `PORTEIRO`.
Values are the §4 "Legacy roles" column, transposed.

### 6.2 What the map deliberately does **not** model

`LEGACY_ROLE_PERMISSIONS[role]` answers exactly one question: *can a user whose
only relevant attribute is `role` pass the **role-dimension** gate of this
operation, in the most favourable object situation?* It is a coarse upper
bound, and the code keeps every narrowing it has today:

* the `UserType.allowed_menus` menu gate (tasks, categories);
* `Task.visible_to` filtering and the "unassigned or self-assigned" edit rule;
* per-lot linkage (`UserLotLink`, `Resident.user_id`) for residents,
  authorizations, packages, visitors' lots;
* ownership/authorship (own feedback, own occurrence, own announcement comment,
  own reservation, own photo, own purchase request, own transaction);
* per-folder `DocumentFolder.allowed_roles_json`;
* payload-dependent narrowings (`VoteKind.ASSEMBLEIA` needs the board;
  `include_inactive=true` on finance categories needs A/D; MANAGER's movement
  types on assets).

This boundary is what makes the map *decidable* — and it is the reason F4's
enforcement must be **additive** (`role gate AND permission`), never a
replacement, until F5 removes the role gates one module at a time.

A consequence worth stating loudly, because F2 will see it: counted off the §4
tables, **17 permissions resolve to all six roles**, and they arrive by four
different mechanisms. The four groups below are disjoint and sum to 17;
`test_all_six_role_permissions_are_the_documented_seventeen` (§6.3 assertion 9)
pins the set by exact match.

* **13 unguarded** (§11.4) — no role logic exists on the path at all:
  `visitors:read`, `visitors:create`, `visitors:update`, `users:read`,
  `user_types:read`, `tenants:read`, `tenants:members_read`, `categories:read`,
  `feedback:read`, `feedback:create`, `spaces:read`, `uploads:photo_create`,
  `uploads:photo_read`. Two of these are additionally *filter-not-refuse*
  inside the service (`feedback:read` narrows to own rows, `tenants:read`
  narrows inside `TenantService`) — that narrowing is an object-dimension one
  and does not move them into another group. (Note `feedback:respond` is *not*
  in this set — the module-wildcard shorthand used in earlier drafts was
  imprecise; it is an A/D guard, §4.17.)
* **1 filter-not-refuse at the route** — `gate:logs_read`: role logic exists in
  `VisitorService.get_access_logs` but narrows the query to the caller's linked
  lots instead of refusing, and raises only on an explicit foreign `lot_id`, so
  at `lot_id=None` no role is refused (§4.10).
* **2 lot-linkage guards that refuse nobody once the link exists** —
  `residents:read` (`ResidentService._check_lot_access`: A/D/M pass
  unconditionally, every other role passes when linked, §4.7) and
  `authorizations:gate_lookup` (`VisitorService.get_authorization_for_user`:
  PORTEIRO bypasses the lot check outright, everyone else passes when linked,
  §4.9). Both are all-six **only** under §6.5's seeded linkage; probe them
  unlinked and they collapse to `{A, D, M}` and `{P}` respectively, which is
  why §6.5 specifies the object graph rather than leaving it to the
  implementer. Note the contrast with `packages:read`/`packages:pickup`, whose
  guard keeps an explicit GUEST branch and therefore stays A/D/M/R/P even when
  linked (§4.19).
* **1 owner-or-staff guard whose owner branch admits every role** —
  `uploads:delete` (`MediaService.delete_photo`, §4.22).

None of this is a modelling error; those routes genuinely impose no
**role-dimension** restriction today. Tightening them is a product decision for
a later slice, and this task must **not** tighten them.

### 6.3 The parity test (`tests/test_legacy_role_permissions.py`)

The map must be *derived from* the live guards, not typed twice. Each catalogue
permission gets exactly one **parity source**, declared in the test module as a
**lazy builder** over the fixture world of §6.5 (several `Guard` probes need
database rows, so a `Source` cannot be constructed at import time):

```python
PARITY_SOURCES: dict[str, Callable[["ParityWorld"], Source]] = { ... }

class RoleSet:              # expected == set(obj), obj is the PRODUCTION object
    roles_obj: Collection[UserRole]
class RoleSetComplement:    # expected == set(UserRole) - set(obj)
    roles_obj: Collection[UserRole]    # the PRODUCTION *exclusion* tuple
class Guard:                # expected == {r for r in UserRole if not raises(probe, r)}
    probe: Callable[[User], None]      # the PRODUCTION guard, args pre-bound
class Composite:            # expected == intersection of the parts' expected sets
    parts: tuple[Source, ...]
class Literal:              # expected == roles; only where no callable/constant exists
    roles: frozenset[UserRole]
    reason: str                        # must be non-empty; names file + function
```

`Source = RoleSet | RoleSetComplement | Guard | Composite | Literal`, and every
form except `Literal` reads a live production object, so editing production
breaks the parity test.

* **`RoleSetComplement` exists because two permissions are defined by exclusion.**
  `votes:cast` and `votes:retract` are gated by `if user.role in
  voting_service.NON_VOTING_ROLES: raise` (`voting_service.py:113`, `:341`) with
  `NON_VOTING_ROLES = (GUEST, PORTEIRO)`. Their legacy set is the *complement*,
  `A D M R`, which `RoleSet` cannot express — pointing a `RoleSet` at
  `NON_VOTING_ROLES` would assert the exact inverse of the truth. The complement
  is computed against `set(UserRole)` at test time, so adding a seventh role
  changes both forms consistently. (An `exclude=True` flag on `RoleSet` is an
  acceptable equivalent; what is not acceptable is a hand-written literal
  `{A, D, M, R}`, which drifts silently when `NON_VOTING_ROLES` changes.)
* **`Composite` exists for heterogeneous gates** — routes whose role outcome is
  the conjunction of two different mechanisms, so neither part alone is the
  source. Exactly two permissions need it:
  * `tasks:read` = `Guard(deps.assert_manager_can_see_task)` ∧
    `Literal(all but GUEST, reason="inline `role == GUEST` returns [] in
    endpoints/tasks.py::list_tasks")`. The guard denies GUEST via
    `TaskNotFoundError`; the inline branch denies GUEST by returning an empty
    list. Both parts are declared, and the expected set is their intersection.
  * `announcements:comment` = `Guard(endpoints.announcements._assert_not_porteiro)`
    ∧ `Literal(all but GUEST, reason="inline GUEST rejection in
    announcement_service.add_comment")`. PORTEIRO is denied by the callable,
    GUEST by the inline statement; the intersection is `A D M R`, which is the
    §4.16 row.

  A `Composite` whose parts are all `Literal` is forbidden — that is a hand copy
  wearing a costume. `test_composite_sources_have_a_live_part` asserts every
  `Composite` contains at least one `RoleSet`/`RoleSetComplement`/`Guard` part.

* `RoleSet` sources import the actual module-level constant
  (`asset_service._STAFF_ROLES`, `endpoints.finance._FINANCE_READ_ROLES`,
  `voting_service.BOARD_ROLES`, …). Editing that constant in production
  immediately breaks the parity test.
* `Guard` sources call the **production function** with a `User` carrying only
  the role under test, and count "did not raise" as granted. Extra arguments
  (session, lot, vote, task, an object owned by the caller) are bound with
  `functools.partial` — **by keyword**, because the guards do not agree on
  argument order (`ResidentService._check_lot_access(session, lot_id,
  current_user)` vs `deps.assert_manager_can_see_task(current_user, task,
  session)`) — against the *most favourable* object situation of §6.2, which
  **§6.5 specifies row by row instead of leaving to the implementer**. That
  section is normative: for `residents:read`, `authorizations:gate_lookup`,
  `packages:*`, `votes:tally_read`, `tasks:*`, `feedback:respond` and
  `uploads:*` the binding *is* the answer, and a different binding produces a
  different §4 table. Two probes still deserve their binding restated here,
  being the two whose result reads as a surprise:
  * `gate:logs_read` → `partial(VisitorService.get_access_logs, session,
    lot_id=None)`. `lot_id=None` is the most favourable object situation (§6.2);
    no role raises, so the expected set is all six (§4.10). Binding a foreign
    `lot_id` instead would encode an object-dimension denial as a role-dimension
    one and is wrong.
  * `packages:my_lots_read` → `partial(PackageService.get_my_lots, session)`.
    Five of six roles raise `PackageAccessForbiddenError`; the expected set is
    `{RESIDENT}` (§4.19). No favourable binding exists that changes this — the
    gate reads `role` and nothing else.
* **`Literal` is bounded, not a general escape hatch.** It is permitted only
  where production offers neither a role-set constant nor a callable to probe:
  1. the **13 unguarded permissions** of §11.4 — `categories:read`, `users:read`,
     `user_types:read`, `tenants:read`, `tenants:members_read`, `visitors:read`,
     `visitors:create`, `visitors:update`, `feedback:read`, `feedback:create`,
     `spaces:read`, `uploads:photo_create`, `uploads:photo_read` — each
     `Literal(all six, reason="no role gate on <file>::<handler>")`;
  2. the **inline gates** named in §4: `tasks:create` (`role == GUEST` inside
     `endpoints/tasks.py::create_task`), plus the `Literal` halves of the two
     `Composite` sources above (`list_tasks`, `add_comment`).

  That is the complete permitted list. `test_literal_sources_are_allowlisted`
  (§6.3 assertion 7) pins it: any *other* permission carrying a `Literal` fails
  CI, which is what stops a future author from silencing a parity mismatch by
  downgrading a `Guard` to a hand-typed set. `reason` stays mandatory and names
  file + function.

Assertions:

1. `test_every_permission_has_a_parity_source` — `PARITY_SOURCES.keys() ==
   PERMISSIONS`. A new permission without a source fails.
2. `test_legacy_map_matches_the_live_guards` — for every permission and every
   `UserRole`: `perm in LEGACY_ROLE_PERMISSIONS[role]` **iff** the source says
   the role is granted. One assertion, ~`len(PERMISSIONS) * 6` checks, reported
   as a sorted diff of `(permission, role)` mismatches.
3. `test_role_set_sources_are_production_objects` — every `RoleSet.roles_obj`
   and every `RoleSetComplement.roles_obj` `is` the attribute currently held by
   its production module (guards against a copy-pasted literal drifting).
4. `test_literal_sources_carry_a_reason` — non-empty `reason` on every
   `Literal`.
5. `test_every_role_has_an_entry` — keys of `LEGACY_ROLE_PERMISSIONS` ==
   `set(UserRole)`; every value `<= PERMISSIONS`.
6. `test_administrator_is_a_superset_of_every_other_role_except_the_documented_gaps`
   — for every permission **not** in the module-level constant
   `ADMIN_GAP_PERMISSIONS`, `perm in LEGACY_ROLE_PERMISSIONS[ADMINISTRATOR]`
   whenever any other role holds it. The unqualified superset claim is **false
   against production** and must not be asserted: `packages:my_lots_read` is
   held by RESIDENT and denied to ADMINISTRATOR by the inverted gate in
   `PackageService.get_my_lots` (§4.19).

   ```python
   # Permissions ADMINISTRATOR does NOT hold. Every entry needs a comment
   # naming the production gate that excludes it.
   ADMIN_GAP_PERMISSIONS: frozenset[str] = frozenset({
       # PackageService.get_my_lots raises for _GATEKEEPER_ROLES (incl.
       # ADMINISTRATOR): staff use GET /packages/queue instead.
       "packages:my_lots_read",
   })
   ```

   The constant is asserted **tight**, not merely respected:
   `test_admin_gap_list_is_exact` checks
   `ADMIN_GAP_PERMISSIONS == {p for p in PERMISSIONS if p not in
   LEGACY_ROLE_PERMISSIONS[ADMINISTRATOR] and any(p in
   LEGACY_ROLE_PERMISSIONS[r] for r in UserRole)}` — so a *new* admin gap fails
   CI until it is listed and justified, and a gap that gets closed in production
   fails CI until it is removed. Together the pair still documents the shape F3
   turns into `is_superuser`, while recording the one place that shape does not
   hold today.
7. `test_literal_sources_are_allowlisted` — the set of permissions whose source
   is (or contains) a `Literal` equals the 13 unguarded permissions plus
   `tasks:create`, `tasks:read` and `announcements:comment`, exactly as
   enumerated above. Nothing else may use `Literal`.
8. `test_composite_sources_have_a_live_part` — every `Composite` contains at
   least one `RoleSet` / `RoleSetComplement` / `Guard` part, and there are
   exactly **two** `Composite` sources (`tasks:read`, `announcements:comment`).
9. `test_all_six_role_permissions_are_the_documented_seventeen` — the set
   `{p for p in PERMISSIONS if all(p in LEGACY_ROLE_PERMISSIONS[r] for r in
   UserRole)}` equals, by exact match, the **17** permissions enumerated in
   §6.2. A route that quietly widens to every role, or a §6.5 binding that
   accidentally narrows one (an unseeded lot link would drop `residents:read`
   and `authorizations:gate_lookup` out of this set), fails CI with a named
   diff rather than passing as a plausible number.

### 6.4 Transitional marker

`test_legacy_map_is_marked_transitional` asserts
`permissions.LEGACY_MAP_REMOVAL_SLICE == "IAM F5"` and that the string
`TRANSITIONAL` appears in the source of `app/core/permissions.py` above the map
(read the file, assert the banner precedes the assignment). Cheap, and it makes
deleting the marker a test failure rather than a silent inheritance.

### 6.5 The parity fixture contract — normative

For a dozen permissions **the binding is the answer**, so the fixture is
specified here rather than left to the implementer. Probe
`ResidentService._check_lot_access` with an unlinked user and `residents:read`
collapses from `ALL` (§4.7) to `{A, D, M}`; probe
`VisitorService.get_authorization_for_user` with an id that resolves to nothing
and `authorizations:gate_lookup` collapses to `∅`, because the row lookup runs
**before** the role check. Two implementers reading this spec must produce the
same expected set for every §4 row that ER-3/ER-4 pin; (a)-(c) below are what
makes that true.

#### (a) Session source and scope

* **Sources are lazy.** `PARITY_SOURCES` maps each permission to a
  `Callable[[ParityWorld], Source]`, not to a `Source`:

  ```python
  PARITY_SOURCES: dict[str, Callable[["ParityWorld"], Source]] = {
      "assets:create":  lambda w: RoleSet(asset_service._STAFF_ROLES),
      "residents:read": lambda w: Guard(
          partial(ResidentService._check_lot_access, session=w.session, lot_id=w.lot.id)
      ),
      ...
  }
  ```

  A module-level `Guard(partial(..., session, ...))` would need a database at
  import time. `PARITY_SOURCES.keys()` is still the flat set of permission
  strings §6.3 assertion 1 compares to `PERMISSIONS`, so no assertion changes
  shape; only the value is called with the world before use.
* **The session is the existing `session` fixture from `tests/conftest.py`** —
  function-scoped in-memory sqlite (`create_engine("sqlite://", …,
  poolclass=StaticPool)`, `SQLModel.metadata.create_all`, `drop_all` on
  teardown), with the autouse `default_tenant` row already seeded. **No new
  session fixture is defined**, matching §7.3's "do not invent new fixtures"
  rule on the Postgres side.
* **The session is never made request-scoped and never given an acting
  tenant.** This is load-bearing, not incidental: `deps.is_acting_tenant_admin`
  deliberately has *no* `DEFAULT_TENANT_ID` fallback ("an unresolved session
  must grant nothing", `deps.py:140-156`), so on this session
  `has_admin_capability(user, session)` reduces exactly to
  `user.role == ADMINISTRATOR` — the role dimension and nothing else. That is
  what makes `get_current_tenant_admin` come out `{A}` (§4.1 `tasks:delete`,
  §4.3 `users:update`, §4.4) and `get_current_tenant_admin_or_manager` come out
  `{A, M}` (§4.3 `users:update_contact`) deterministically, with no tenant_admin
  grant leaking into a role-dimension measurement.
* **Parametrisation is per permission, not per (permission, role).** One
  function-scoped `parity_world` per catalogue permission (≈130 worlds, each a
  fresh in-memory database); the six roles are probed inside it. This is also
  the isolation mechanism of (c).

#### (b) `ParityWorld` — the most favourable object graph, enumerated

A frozen dataclass built by the `parity_world` fixture. Every row below exists
so that **the only remaining denial is the role denial being measured**.

| Attribute | Rows seeded | Why — which probe needs it |
|---|---|---|
| `session` | the conftest sqlite session | every `Guard` |
| `tenant` | the autouse `default_tenant` row | the inert `_tenant` argument of `get_current_tenant_admin` / `_or_manager`; the parameter is unused by the body (it exists to force `get_current_tenant` to run in production) and must simply be *a* `Tenant` |
| `users: dict[UserRole, User]` | six active users, one per role, each with `UserTenantLink(tenant_id=DEFAULT_TENANT_ID, is_tenant_admin=False)` | every probe. `is_tenant_admin=False` keeps the capability dimension out of the measurement even if a future change gives the session an acting tenant |
| `lot: Lot` + **per user** a `UserLotLink(start_date=None, end_date=None)` **and** an active `Resident(user_id=…, lot_id=lot.id, is_active=True)` | both linkage paths satisfied for all six roles | `ResidentService._check_lot_access` (⇒ `residents:read` = ALL, §4.7); `VisitorService._check_lot_access` (`authorizations:read/create/revoke`); `PackageService._assert_lot_access` (⇒ `packages:read`/`packages:pickup` = A/D/M/R/P — GUEST still refused by that guard's own explicit GUEST branch, §4.19); `VisitorService.get_user_linked_lot_ids` (`gate:logs_read`); `voting_service._active_lot_ids` (`votes:tally_read`). Open-ended dates are what make `_is_link_active` true *now* |
| `visitor: Visitor` + `authorization: VisitorAuthorization` on `lot` (active, not revoked) | one row, shared (read-only probe) | `authorizations:gate_lookup`: `get_authorization_for_user` resolves the row via `get_authorization_by_id` **before** any role check; with no row every role raises NotFound and the expected set is `∅` instead of `ALL` |
| `vote: Vote(kind=VoteKind.ENQUETE, open)` | one row | `votes:tally_read`: `_assert_can_view_tally` takes the `_active_lot_ids` branch for `ENQUETE`, satisfied by the lot links, so RESIDENT is granted and only `NON_VOTING_ROLES` are refused ⇒ `A D M R` (§4.13). An `ASSEMBLEIA` vote would additionally demand `voter_eligibility` rows and would encode an object-dimension denial as a role one. `_assert_can_create_vote` is bound to `VoteKind.ENQUETE` for the same reason (§4.13) and needs no rows |
| `task: Task(visible_to=[], assigned_to_id=None)` | one row | `assert_manager_can_see_task` (empty `visible_to` is visible to every MANAGER) and `assert_can_edit_task` (unassigned ⇒ MANAGER may edit). Any other task silently drops M from `tasks:read`, `tasks:update` and `tasks:comment` |
| `new_feedback()` | **factory**, fresh row per probed role | `feedback:respond`: `FeedbackService.respond_to_feedback` raises `FeedbackNotFoundError` **before** the role check (so a missing row denies everyone), and **commits** on the A/D path |
| `new_media_asset(role)` | **factory**, fresh `PENDING` row per probed role, `uploaded_by_id == users[role].id`, non-empty `file_path` | `uploads:delete`: `delete_photo` resolves the asset first (missing ⇒ everyone denied) and grants on `is_owner or A/D` — the owner branch is exactly what makes this permission all-six (§4.22), so ownership must match the probed role. `uploads:approve` / `uploads:reject`: the role check comes first, but A/D then resolve the asset and would raise `MediaAssetNotFoundError`, misreading as a denial. All three mutate and commit |

Every other `Guard` in §4 is a pure role predicate needing no rows
(`_assert_not_porteiro` ×4, `_require_voting_access`, `_require_non_guest`,
`_assert_gatekeeper_access`, `residents.assert_admin_or_director`,
`document_service._check_admin_or_director`,
`announcement_service._check_publisher`, `voting_service._assert_board` /
`_assert_can_manage_eligibility`, `access_control_service._assert_*`,
`PackageService._assert_gatekeeper_role` / `get_my_lots`,
`MediaService.list_pending_photos`, `deps.get_current_active_admin`), and every
`RoleSet` / `RoleSetComplement` needs none at all.

#### (c) Isolation of the side-effecting probes

Three probe families write: `respond_to_feedback` (commits),
`approve_photo` / `reject_photo` (commit), `delete_photo` (deletes the row,
commits, and calls `storage_provider.delete_file`). Isolation is achieved **by
construction, not by savepoint** — several probes call `session.commit()`
themselves, so a savepoint wrapped around a probe cannot be relied on to undo
them:

1. **one fresh world per parametrised permission** — function-scoped fixture,
   fresh in-memory database, so no permission can be affected by another;
2. **within a world, every mutable object comes from a per-role factory**
   (`w.new_feedback()`, `w.new_media_asset(role)`), so no probe ever sees an
   object another probe changed and the six roles are order-independent;
3. **`w.session.rollback()` after every probe**, granted or denied, to drop the
   uncommitted state a raising probe may have left behind;
4. **the storage provider is faked** — the media probes use
   `MediaService(storage_provider=_NullStorage())`, i.e. the production class
   and the production method, with a no-op `save_file`/`delete_file` double
   injected through the constructor parameter that already exists for it
   (`media_service.py:29-30`). The module-level `media_service` singleton (a
   `LocalStorageProvider`) is never used, so the parity test touches no file
   system. The `Guard` still reads live production logic; only the storage side
   effect is stubbed, and `test_role_set_sources_are_production_objects` is
   unaffected (it constrains `RoleSet`, not `Guard`).

The `parity_world` fixture asserts on teardown, for every case, that its
invariant core survived: the six users and their lot links still resolve, the
`Lot`, `Task`, `Vote` and `VisitorAuthorization` rows are still present, and
`task.visible_to == []`, `task.assigned_to_id is None` and the authorization is
still un-revoked. A probe that mutated the shared graph instead of its own
factory row therefore fails the case that caused it, by name.

---

## 7. `user_type.permissions` and migration `0030`

### 7.1 Model

`backend/app/models/user_type.py`, immediately after `allowed_menus`, and
deliberately identical in shape to it:

```python
    # A role's permission bundle (IAM F1). Portable JSON, NOT a Postgres
    # ARRAY, for the same reason `allowed_menus` is: tests/conftest.py builds
    # the schema with SQLModel.metadata.create_all() on sqlite://.
    # NOTHING seeds this: every row - including the six role-linked rows
    # TenantService.ensure_role_types creates - starts and stays [].
    permissions: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, server_default="[]"),
    )
```

### 7.2 Migration

`backend/alembic/versions/0030_add_user_type_permissions.py`

```python
revision = "0030_add_user_type_permissions"      # 30 chars, under the 32-char limit
down_revision = "0029_add_is_tenant_admin"
```

`upgrade()` = one `op.add_column("user_type", sa.Column("permissions",
sa.JSON(), nullable=False, server_default="[]"))`, copied field-for-field from
`0017_add_user_type_allowed_menus.py`. `downgrade()` = one `op.drop_column`.
**No `INSERT`, no `UPDATE`, no seeding** — the migration is exactly reversible,
which is also why it can be re-run by the §7.3 tests.

**`0030` moves the Alembic head, and two existing assertions encode the old
one.** `tests/test_migrations_postgres.py` pins the revision reached by
`upgrade head` in two places — line 859 in `test_downgrade_removes_tenant_schema`
and line 888 in `test_is_tenant_admin_column_shape_and_backfill`, both
`assert _current_revision(...) == "0029_add_is_tenant_admin"`. With `0030`
present, `upgrade head` lands on `0030` and both assertions fail. **Each of the
two string literals changes to `"0030_add_user_type_permissions"` and nothing
else in either function changes** — no new assertion, no fixture change, no
restructuring. This is exactly what every migration slice before this one did to
the same two-ish lines (`86c038d`, APRAS-43, last moved them from `0028` to
`0029`), and §9.1 records it as a named, bounded exception rather than a
violation. A head-agnostic helper (reading `alembic heads` at runtime) was
considered and rejected: it would rewrite two working tests to weaken what they
assert, in a slice whose whole discipline is not touching existing tests.

### 7.3 Postgres tests (appended to `tests/test_migrations_postgres.py`)

New section header `# 0030_add_user_type_permissions (APRAS-45) — the role
permission bundle`, using the existing `isolated_pg_engine` / `pg_engine_at_0027`
fixtures (do not invent new ones):

* `test_permissions_column_shape_and_backfill(pg_engine_at_0027)` — insert a
  `user_type` row before `0030`, `upgrade head`, then assert via
  `information_schema.columns`: `data_type == "json"`, `is_nullable == "NO"`,
  `column_default` is the `'[]'` literal; and the pre-existing row now reads
  `[]`. Then `downgrade 0029_add_is_tenant_admin`, assert the column is gone,
  then `upgrade head` again (the fixture teardown assumes a clean head, exactly
  as the `0029` test does).
* `test_no_user_type_row_has_permissions_after_migration(isolated_pg_engine)` —
  at head, `SELECT count(*) FROM user_type WHERE permissions::text <> '[]'` is
  `0`. Nothing is seeded, including by any earlier migration's seeded rows.

### 7.4 The "nothing is seeded" test (sqlite, `tests/test_effective_permissions.py`)

* `test_a_fresh_tenant_has_no_role_with_permissions` — `POST /api/v1/tenants`
  as an ADMINISTRATOR, then read every `UserType` of the new tenant: the six
  role-linked rows exist (APRAS-42 §7.2 requires them for the menu gate) and
  **every one of them has `permissions == []`**; no row in the tenant has a
  non-empty bundle. This is the operative reading of "a fresh tenant's role list
  comes back empty": *empty of permissions*, see §11.1.
* `test_seed_creates_no_permissions` — `TenantService.ensure_role_types` on a
  new tenant returns rows whose `permissions` are all `[]`.

### 7.5 Running the migration tests — READ THIS BEFORE YOU RUN THEM

```bash
cd backend
TEST_POSTGRES_URL=postgresql://postgres:postgres@localhost:5436/nexdom \
  .venv/bin/python -m pytest tests/test_migrations_postgres.py -q
```

**The local Postgres on 5436 is the developer's demo database and it holds live
demo data.** The `isolated_pg_engine` / `pg_engine_at_0027` fixtures
`DROP SCHEMA public CASCADE` on setup *and* teardown: running this file **wipes
that data**. That is expected and unavoidable — it is how APRAS-41/42/43 were
verified. Afterwards, restore the dev database with:

```bash
cd backend && .venv/bin/python -m app.seed
```

Do not skip the reseed, and do not point `TEST_POSTGRES_URL` at anything you
are not willing to lose. Without `TEST_POSTGRES_URL` the whole module skips —
**18 skipped before this task, 20 after**, since §7.3 adds two cases — so
`pytest` on its own is safe.

**This run also re-executes the `0028`/`0029` cases against a schema that now
includes `0030`.** `isolated_pg_engine` resets to `head` and `pg_engine_at_0027`
drives `upgrade head` itself, so every pre-existing case in the module migrates
one revision further than it used to. Two consequences to expect, and neither is
a regression: (i) the two head-pin assertions must already carry the `0030`
string or the older cases fail first (§7.2, §9.1); (ii) `0030` runs inside the
`0028`→`0029`→`0030` chain on a database holding the rows those older cases
seed, which is the real proof that `add_column ... NOT NULL server_default '[]'`
back-fills existing `user_type` rows rather than erroring. If a `0028`/`0029`
case fails for any reason **other** than the two-line head pin, `0030` is at
fault — stop and fix it there, do not edit the older case.

---

## 8. `get_effective_permissions`

In `backend/app/api/deps.py`, immediately after `get_effective_user_type_ids`:

```python
def get_effective_permissions(user: User, session: Session) -> frozenset[str]:
    """Every permission `user` holds in the session's acting tenant.

    Union of two sources, and only two:
      1. the `permissions` of the user's effective roles in the acting tenant
         (`get_effective_user_type_ids`, so a role change is immediate and a
         role of another tenant never composes into this answer);
      2. LEGACY_ROLE_PERMISSIONS[user.role] - the TRANSITIONAL fallback that
         keeps F1..F4 meaningful while no role carries any permission.

    No nesting (a role's permissions are a flat list), no per-user loose
    permission, and deliberately NO is_superuser / is_tenant_admin shortcut:
    those arrive in F3.
    """
```

* Acting tenant is read from the session, exactly as
  `get_effective_user_type_ids` does — see §11.2 for why the signature is
  `(user, session)` and not `(user, tenant)`.
* Returns `frozenset[str]`. Unknown strings stored in a role's `permissions`
  (a hand-edited row, or a permission deleted by a later slice) are **kept as
  is**, not filtered against `PERMISSIONS`: silently dropping them would hide a
  data bug that F2's UI must be able to show. A test pins this.
* Placement rationale: this is a resolver over a `Session`, and
  `app/core/permissions.py` must stay database-free (§5.1). `deps.py` is where
  `get_effective_user_type_ids` and `has_admin_capability` already live, and
  where F3's `is_superuser` shortcut will land.

Tests (`tests/test_effective_permissions.py`):

1. a user with no roles gets exactly `LEGACY_ROLE_PERMISSIONS[user.role]` — one
   case per `UserRole` (6 parametrised cases);
2. a user whose `UserType` in the acting tenant carries
   `["assets:create", "votes:close"]` gets those **plus** the legacy set;
3. a user whose role-bundle permission is already in the legacy set gets it once
   (it is a set union, not a list);
4. permissions from a `UserType` belonging to **another** tenant are excluded —
   dual-tenant user, acting tenant A, role rows in B carry
   `["finance:transaction_delete"]`, result must not contain it (this is the
   APRAS-43 §5.2 relationship-load trap);
5. unknown strings in a role's `permissions` survive into the result;
6. the acting tenant's role-linked `UserType` (the implicit one from APRAS-9)
   contributes its permissions when it has any;
7. a `Session` with no acting tenant resolves to `DEFAULT_TENANT_ID`, exactly
   like `get_effective_user_type_ids` (unit-test/seed path) — pinned so F3 does
   not have to rediscover it.

---

## 9. Non-regression obligations

1. **No existing test file is edited, with exactly two named exceptions, both
   in `tests/test_migrations_postgres.py` and nowhere else:**

   1. **the additive `0030` section appended at the end of the file** (§7.3) —
      appended after the last existing test, adding only new functions and
      reusing the existing `isolated_pg_engine` / `pg_engine_at_0027` fixtures
      without redefining them (the APRAS-41 precedent for extending this
      module);
   2. **the two head-pin assertions** (§7.2) — in
      `test_downgrade_removes_tenant_schema` (line 859) and
      `test_is_tenant_admin_column_shape_and_backfill` (line 888), the expected
      revision is updated from `"0029_add_is_tenant_admin"` to
      `"0030_add_user_type_permissions"`. **Two string literals, one per
      function. Nothing else inside those two functions changes** — same
      fixtures, same other assertions, same order. This is forced: `0030` is on
      head, so `upgrade head` reaches it, and every migration slice before this
      one made the same two-line edit (`86c038d` last did it for `0029`).

   So the diff of `tests/test_migrations_postgres.py` is a pure-insertion hunk at
   EOF **plus exactly two single-line replacements**, and `git diff --stat` on
   that file shows a small, reviewable count of changed lines rather than an
   insertion-only hunk. Any *third* changed line in that file, and any changed
   line in any other pre-existing test file, is out of contract.

   Every other existing test file — `tests/test_tasks_rbac.py`,
   `test_guest_rbac.py`, `test_porteiro_role.py`, every `test_*_rbac.py`,
   `test_menu_access.py`, `test_tenant_admin.py`, all of them — is untouched.
   Not one line. If any of them needs a change, the slice has leaked enforcement
   and the change is wrong. Mechanically: `git diff --stat -- backend/tests/`
   against the §10.1 baseline shows only the three new files of §2 plus
   `test_migrations_postgres.py`, and `git diff -- backend/tests/test_migrations_postgres.py`
   shows the EOF insertion plus the two head-pin lines of (2) above — nothing
   else.
2. No file under `backend/app/api/v1/endpoints/` or `backend/app/services/`
   appears in this task's diff. **Diff base matters here:** the §10.1 baseline is
   the tree with APRAS-38 *staged*, and APRAS-38 itself modifies
   `backend/app/api/v1/endpoints/auth.py` and
   `backend/app/services/tenant_service.py` (plus `app/schemas/tenant.py` and
   `app/schemas/user.py`). Those are 38's, not 45's. Compare against the staged
   baseline (`git diff` on the unstaged working tree, or `git diff <baseline-ref>`
   where the baseline ref is the APRAS-38 merge) — **not** against
   `master`/`HEAD`, which would falsely flag 38's files as this task's.
3. `test_permission_registry.py` includes
   `test_user_type_schemas_are_unchanged`, pinning all three schemas in
   `app/schemas/user_type.py` to the exact field sets they have today (read off
   the file for this spec, not guessed):

   ```python
   assert set(UserTypeCreate.model_fields) == {"name", "allowed_menus"}
   assert set(UserTypeRead.model_fields)   == {"id", "name", "allowed_menus", "role"}
   assert set(UserTypeUpdate.model_fields) == {"name", "allowed_menus"}
   ```

   `permissions` must **not** appear in any of the three. This is what
   mechanically enforces "no API surface change" while the column exists: the
   model gains the field, the wire format does not.
4. `ruff check` clean on every touched file (the repo carries ~1200 pre-existing
   findings elsewhere; touched files must add none). `select = ["ALL"]`,
   line-length 88, and `app/core/**` already ignores `E501`/`INP001`.

---

## 10. Verification commands

### 10.1 Measured baseline (this working tree, APRAS-38 staged, run for this spec)

```
$ cd backend && .venv/bin/python -m pytest -q --cov=app --cov-report=term
1052 passed, 18 skipped, 20276 warnings in 477.60s
Required test coverage of 90% reached. Total coverage: 98.31%   (7649 stmts, 129 missed)
```

1070 collected. These are the floors, measured — not the `1064 / 98.31%` figure
from `86c038d`, which predates APRAS-38's `test_auth_me_tenants.py`.

### 10.2 After the change

```bash
cd backend
.venv/bin/python -m pytest -q --cov=app --cov-report=term        # ~8 min
ruff check app/core/permissions.py app/models/user_type.py app/api/deps.py \
           alembic/versions/0030_add_user_type_permissions.py tests/test_permission_registry.py \
           tests/test_legacy_role_permissions.py tests/test_effective_permissions.py \
           tests/test_migrations_postgres.py
TEST_POSTGRES_URL=postgresql://postgres:postgres@localhost:5436/nexdom \
  .venv/bin/python -m pytest tests/test_migrations_postgres.py -q   # then: python -m app.seed
git diff --stat -- frontend/                                        # must be empty
```

---

## 11. Decisions and ER refinements

### 11.1 "the roles list of a fresh tenant comes back empty" — refined

The repo contradicts the literal wording. `TenantService.create_tenant` **must**
seed six role-linked `UserType` rows (`ensure_role_types`, APRAS-42 §7.2):
without them a non-ADMINISTRATOR member of a new tenant has an empty effective
UserType set and is 403'd by `assert_menu_access` on every gated menu. Deleting
that seeding would be an APRAS-42 regression, not an IAM decision.

What the user's decision *forbids* is seeding **permissions**. The verifiable
form, and the one this spec implements and the refined ER states: a freshly
created tenant has **no role carrying any permission — every `user_type` row in
it has `permissions == []`**, and no code path anywhere writes a non-empty
bundle (§7.3, §7.4).

### 11.2 `get_effective_permissions(user, tenant)` → `(user, session)`

Since APRAS-42 the acting tenant is a property of the request session
(`tenant_context.acting_tenant_id(session)`), and no resolver in this codebase
takes a `Tenant` parameter — `get_effective_user_type_ids(user, session)`,
`is_acting_tenant_admin(user, session)` and `has_admin_capability(user, session)`
all read it from the session. A `tenant` parameter would introduce a second,
divergeable source of truth for "which tenant am I acting in", which is exactly
what APRAS-42 §3 exists to prevent. The semantics the ER asks for are unchanged:
the union is computed **in the acting tenant**.

### 11.3 Cancel is a decide-level action

`PurchaseService.cancel_request` calls `_assert_can_decide`, so
`purchases:cancel` is A/D — *not* A/D/M as its sibling write routes are. It
reads like an inconsistency in the current product, but this slice records
capabilities as they are; changing it is a product decision.

### 11.4 Routes with no role gate at all — the 13

`visitors:read`, `visitors:create`, `visitors:update`, `users:read`,
`user_types:read`, `tenants:read`, `tenants:members_read`, `categories:read`,
`feedback:read`, `feedback:create`, `spaces:read`, `uploads:photo_create`,
`uploads:photo_read` — **13 permissions**, open to every authenticated role
today. They are catalogued as such (`ALL`) and they are exactly the permissions
allowed to carry a `Literal` parity source (§6.3), because there is no
production constant or callable to derive them from. Recording them truthfully
is the point of the exercise: F2's matrix will make these visible for the first
time, which is where the tightening decision belongs.

`gate:logs_read` is deliberately **not** in this list even though it also
resolves to all six: it has a live callable (`VisitorService.get_access_logs`)
and therefore a `Guard` source, not a `Literal` one (§4.10).

### 11.5 `packages:my_lots_read` is RESIDENT-only, and stays that way

`GET /packages/my-lots` is the one route in the catalogue that **excludes
ADMINISTRATOR** (§4.19). `PackageService.get_my_lots` refuses all four
`_GATEKEEPER_ROLES` and `GUEST`, pointing staff at `GET /packages/queue`
instead. It reads as an inconsistency next to the "admin can do everything"
assumption F3 will encode as `is_superuser`, and it is precisely why §6.3's
superset assertion is qualified by `ADMIN_GAP_PERMISSIONS` rather than stated
absolutely. Whether an ADMINISTRATOR *should* be able to see their own linked
lots through this endpoint is a product decision; this slice records
capabilities as they are, exactly as §11.3 does for `purchases:cancel`. F3 must
decide it explicitly — the exact-match test on `ADMIN_GAP_PERMISSIONS` makes
that decision unavoidable rather than accidental.

### 11.6 Enforcement stays off

`get_effective_permissions` having zero production callers is intentional and
should be read as a feature of this slice, not an oversight. A reviewer looking
for "where is this used?" should find: tests only.

### 11.7 The two head-pin lines are an accepted cost, not a leak

§9.1's "no existing test is edited" and ER-2's "`0030` is on head" are jointly
satisfiable only if the two `_current_revision(...) == "0029_add_is_tenant_admin"`
assertions move with the head. They are not enforcement, not behaviour and not
this slice's semantics: they are a constant naming the newest migration, which
by definition changes in every migration slice — `86c038d` (APRAS-43) moved them
last, from `0028` to `0029`. Recording them as a bounded exception (two string
literals, two named functions, nothing else) keeps the discipline meaningful:
the rule "no existing test file is edited" exists to catch *enforcement leaking
into F1*, and a head constant is not that. The alternative — a head-agnostic
helper reading `alembic heads` at runtime — was rejected because it rewrites two
working tests to assert less, in the one slice whose defining constraint is not
touching them.

---

## Expected Results

- [ ] **ER-1 — the registry.** `backend/app/core/permissions.py` exists and
      exports `PERMISSIONS`, `ROUTE_PERMISSIONS`, `UNGUARDED_ROUTES` and
      `LEGACY_ROLE_PERMISSIONS`; every permission string matches
      `^[a-z][a-z0-9_]*:[a-z][a-z0-9_]*$`, uses `read`/`create`/`update`/`delete`
      for plain CRUD and named domain actions otherwise (`purchases:decide`,
      `votes:close`, `gate:checkin`, `packages:pickup`, `assemblies:close`, …).
      `tests/test_permission_registry.py::test_every_route_is_declared_or_unguarded`
      passes and **fails when a route is added without a declared permission**.
      Route accounting is pinned to measured totals: the app exposes **190**
      `(method, path)` keys, so `len(UNGUARDED_ROUTES) == 10`,
      `len(ROUTE_PERMISSIONS) == 180`, and
      `len(ROUTE_PERMISSIONS) + len(UNGUARDED_ROUTES) == 190` with the two sets
      disjoint. (If the merged APRAS-38 baseline moves the total, the test
      recomputes it from `app.main.app` and the three numbers move together —
      the invariant, not the constant, is the requirement.)
- [ ] **ER-2 — the column and migration.** `user_type` gains a `permissions`
      JSON column, NOT NULL, `server_default '[]'`, via
      `0030_add_user_type_permissions` (30-char revision id, under Alembic's
      32-char limit) on head `0029_add_is_tenant_admin`; `alembic upgrade head`
      and `downgrade 0029_add_is_tenant_admin` both succeed against Postgres on
      5436, and **the whole of `tests/test_migrations_postgres.py` passes with
      `TEST_POSTGRES_URL` set** — the two new `0030` cases *and* every
      pre-existing case, which now migrate one revision further. Because `0030`
      moves the Alembic head, exactly two pre-existing lines change with it:
      the expected revision in `test_downgrade_removes_tenant_schema` (line 859)
      and in `test_is_tenant_admin_column_shape_and_backfill` (line 888) goes
      from `"0029_add_is_tenant_admin"` to `"0030_add_user_type_permissions"`,
      and **nothing else in either function changes** (§7.2, §9.1 — the same
      two-line edit `86c038d` made for `0029`). **Nothing is seeded**: after
      creating a tenant, every `user_type` row in it — including the six
      role-linked rows — has `permissions == []`, and `SELECT count(*) FROM
      user_type WHERE permissions::text <> '[]'` returns `0` at head.
- [ ] **ER-3 — the legacy map is derived, not typed.**
      `LEGACY_ROLE_PERMISSIONS` maps all six `UserRole` values to frozen
      permission sets, is marked transitional (`LEGACY_MAP_REMOVAL_SLICE ==
      "IAM F5"` plus a `TRANSITIONAL` banner above the assignment), and
      `tests/test_legacy_role_permissions.py` passes: every catalogue permission
      has exactly one parity source, and for every (permission, role) pair
      membership in the map equals what production decides today.
      **Source discipline is bounded explicitly:** each source is a `RoleSet`,
      `RoleSetComplement`, `Guard` or `Composite` reading the live production
      constant or callable — `RoleSetComplement` (or an equivalent `exclude`
      form) is required for `votes:cast` and `votes:retract`, whose gate is the
      complement of `voting_service.NON_VOTING_ROLES`, and `Composite` for the
      heterogeneous gates on `tasks:read` and `announcements:comment`.
      `Literal` is **permitted only** for the 13 unguarded permissions of §11.4
      and the inline gates enumerated in §4 (`tasks:create`, plus the `Literal`
      halves of those two `Composite` sources); every other permission must use
      `RoleSet` / `RoleSetComplement` / `Guard` / `Composite`, enforced by
      `test_literal_sources_are_allowlisted` and
      `test_composite_sources_have_a_live_part` (exactly two `Composite`
      sources; §4.9's authorizations rows are a **single** `Guard`, not a
      third). Every expected set is computed under the §6.5 fixture contract
      (ER-7), so the parity result is reproducible rather than
      binding-dependent.
- [ ] **ER-4 — the catalogue matches production, including its asymmetries.**
      The parity test passes against the live guards with these three
      independently checked rows, each verified against production for this
      spec: `gate:logs_read` → **all six roles** (`GET /access-logs` has no
      `_assert_gatekeeper_access`; `VisitorService.get_access_logs` narrows to
      linked lots and raises only on an explicit foreign `lot_id`, so no role is
      refused at `lot_id=None`); `packages:my_lots_read` → **`{RESIDENT}` only**
      (`PackageService.get_my_lots` raises for all four `_GATEKEEPER_ROLES` and
      for `GUEST`); and, in consequence, ADMINISTRATOR is a superset of every
      other role **for every permission except those listed in
      `ADMIN_GAP_PERMISSIONS`**, which equals exactly
      `{"packages:my_lots_read"}` — asserted by exact match, so a new admin gap
      or a closed one fails CI rather than passing silently. No unqualified
      "administrator is a superset" assertion appears in the suite.
      `test_all_six_role_permissions_are_the_documented_seventeen` additionally
      pins by exact match the **17** permissions that resolve to all six roles —
      the 13 unguarded of §11.4, plus `gate:logs_read`, `uploads:delete`,
      `residents:read` and `authorizations:gate_lookup` — so a binding that
      silently narrows one of the two lot-linkage rows (§6.5) fails CI with a
      named diff.
- [ ] **ER-5 — the resolver.** `deps.get_effective_permissions(user, session)`
      returns the union of the permissions of the user's roles in the acting
      tenant and `LEGACY_ROLE_PERMISSIONS[user.role]`, with no nesting, no
      per-user permission and no `is_superuser`/`is_tenant_admin` shortcut;
      `tests/test_effective_permissions.py` proves the no-role case equals the
      legacy set for each of the six roles, that role bundles are added, that
      unknown stored strings survive, and that a role belonging to another
      tenant contributes nothing.
- [ ] **ER-6 — nothing else moves.** Measured against the **APRAS-38 staged
      baseline** (not `master`/`HEAD`: the staged 38 tree already modifies
      `app/api/v1/endpoints/auth.py`, `app/services/tenant_service.py`,
      `app/schemas/tenant.py` and `app/schemas/user.py`, and those are 38's
      changes, not this task's) — no file under `app/api/v1/endpoints/` or
      `app/services/` is modified by APRAS-45; **no existing test file is edited
      except `tests/test_migrations_postgres.py`, whose diff is exactly the
      additive `0030` section appended at EOF (APRAS-41 precedent) plus the two
      head-pin string literals of ER-2 — a third changed line in that file, or
      any changed line in any other pre-existing test file, fails this ER**; the
      `UserType` schemas keep exactly
      their current fields — `set(UserTypeCreate.model_fields) == {"name",
      "allowed_menus"}`, `set(UserTypeRead.model_fields) == {"id", "name",
      "allowed_menus", "role"}`, `set(UserTypeUpdate.model_fields) == {"name",
      "allowed_menus"}`, none containing `permissions`; and
      `git diff -- frontend/` is empty. The full backend suite is green with
      ≥ 1070 tests collected, 0 failures and total coverage ≥ 98.31% (measured
      baseline: 1052 passed / 18 skipped / 98.31%; after this task the default
      run skips **20**, the two new Postgres cases joining the 18 that already
      skip without `TEST_POSTGRES_URL`); `ruff check` is clean on every touched
      file.

- [ ] **ER-7 — the parity fixture is specified, shared and side-effect free.**
      `tests/test_legacy_role_permissions.py` implements §6.5: `PARITY_SOURCES`
      holds lazy builders `Callable[[ParityWorld], Source]` (no `Source` is
      constructed at import time); the session is the existing
      `tests/conftest.py::session` fixture, never request-scoped and never given
      an acting tenant, so `has_admin_capability` reduces to
      `role == ADMINISTRATOR` and `get_current_tenant_admin` resolves to `{A}`;
      one function-scoped `parity_world` per catalogue permission seeds the
      enumerated graph — six role users with `is_tenant_admin=False`, a `Lot`
      with a `UserLotLink` **and** an active `Resident` for every one of the six,
      a `VisitorAuthorization`, an `ENQUETE` `Vote`, a `Task` with
      `visible_to=[]` and `assigned_to_id=None` — plus per-role factories
      `new_feedback()` and `new_media_asset(role)` for the probes that mutate.
      The three writing families are isolated by construction: fresh world per
      permission, fresh factory object per role, `session.rollback()` after every
      probe, and `MediaService(storage_provider=_NullStorage())` so no file
      system is touched. The `parity_world` teardown asserts its invariant core
      survived the case (six users and links resolve; `Lot`, `Task`, `Vote` and
      `VisitorAuthorization` present; `task.visible_to == []`,
      `task.assigned_to_id is None`, authorization un-revoked), so a probe that
      mutated the shared graph fails the case by name. Consequence, and the
      point of the ER: the expected sets pinned by ER-3/ER-4 — `residents:read`
      = ALL, `authorizations:gate_lookup` = ALL, `packages:read`/`packages:pickup`
      = A/D/M/R/P, `votes:tally_read` = A/D/M/R, `tasks:read`/`tasks:update`/
      `tasks:comment` including M, `feedback:respond` = A/D, `uploads:delete` =
      ALL — are reproducible by any implementer following §6.5, not artefacts of
      one author's binding choices.
