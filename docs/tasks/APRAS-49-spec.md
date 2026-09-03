# APRAS-49 — IAM F5: rename groups to `role`, drop the `user.role` enum and `allowed_menus`

> **Recommended split (one Meridian task, two commits on one branch, in this
> order).** This slice is two separable deliverables and should be reviewed as
> two commits: **(A) the rename** — `user_type` → `role` across backend, frontend,
> API and i18n, zero behaviour change, migration `0032`; **(B) the enum drop** —
> the 15 F5-marked role reads re-expressed, the backfill/refuse-guard/drop
> migration `0033`, `LEGACY_ROLE_PERMISSIONS` deleted, `seed.py` rewritten,
> `AGENTS.md`. A is ~90 mechanical files and no decisions; B is ~25 files and
> every decision. Landing B on top of A keeps the interesting diff readable.
> The Expected Results below are satisfiable only by the **union**, so the task
> stays one task and one PR is acceptable if the reviewer prefers it.

Slice 5 (last) of the IAM chain: F1 `APRAS-45` → F2 `APRAS-46` → F3 `APRAS-47`
→ F4 `APRAS-48` → **F5 this**.

F1 built the vocabulary. F2 swapped enforcement onto it. F3 made
`is_superuser` mean "the whole catalogue". F4 built the UI that authors groups
and gated menus and routes on permissions. **F5 removes the scaffolding**: the
`UserRole` enum, `UserType.allowed_menus`, the `LEGACY_ROLE_PERMISSIONS`
bridge, and the `user_type` name.

---

## 0. Preconditions, and how to read this spec against a moving tree

**Contracts, not files.** APRAS-46 is being implemented *in this worktree*
right now (`git status --short -- backend/` is 30+ files at the time of
writing) and 47/48 are approved but unimplemented. This spec is written
against:

1. **F1's landed code** at `02c2025` — `app/core/permissions.py`
   (`PERMISSIONS`, `ROUTE_PERMISSIONS`, `UNGUARDED_ROUTES`,
   `LEGACY_ROLE_PERMISSIONS`, `_LEGACY_ROLES_BY_PERMISSION`),
   `deps.get_effective_permissions`, `deps.get_effective_user_type_ids`,
   migration `0030_add_user_type_permissions`.
2. **F2's approved spec** `docs/tasks/APRAS-46-spec.md` — `deps.has_permission`
   / `deps.require_permission`; catalogue **156** strings / **26** modules;
   `permissions` on the user-type write/read schemas;
   `user_type_service.assert_can_grant` / `assert_can_assign_user_types`; the
   1080-cell parity matrix (`tests/matrix_world.py`,
   `tests/data/parity_matrix_baseline.json`, `_meta.merge_base_sha = 02c2025…`);
   and the two exact-match allowlists in `tests/test_permission_enforcement.py`
   (`ROLE_READS_COMPARE`, `ROLE_READS_NON_COMPARE`).
3. **F3's approved spec** `docs/tasks/APRAS-47-spec.md` — `user.is_superuser`
   (migration `0031`), `deps.get_current_superuser`, the `User.__init__`
   transitional default, `SUPERUSER_ONLY_PERMISSIONS`, and the post-F3
   allowlists: **`ROLE_READS_COMPARE` = 8 entries** and
   **`ROLE_READS_NON_COMPARE` = 7 reads in 5 functions**, every one marked
   `slice="F5"`.
4. **F4's approved spec** `docs/tasks/APRAS-48-spec.md` —
   `GET /api/v1/permissions/` and `GET /api/v1/permissions/me`
   (`{tenant_id, permissions[]}`, tenant-scoped); the frontend access model
   (`AccessRule`, `ROUTE_ACCESS`, `usePermissionSet` / `useEffectivePermissionSet`,
   `useCanAccess` / `useCanShowMenu`, `ProtectedRoute`'s single `requiredAccess`
   prop); `/admin/groups` + `/admin/groups/:groupId`; and the **six-item F4→F5
   hand-off list** in §11, all marked `TRANSITIONAL (IAM F4 -> F5)`.

**Dependency.** `APRAS-48` must be merged first. Every measured number in §12 is
measured **at F4's merge commit**, in a clean worktree, and quoted in the PR
body next to the number this spec predicts.

**If a name landed differently** in F2/F3/F4 — a renamed constant, a hook in a
different module — apply the edit **by role, not by name**, and record the
deviation in the PR body.

**Line numbers are never load-bearing.** Every site below is named by
`module::function`; locate it with `grep -n 'def <name>'`.

---

## 1. Scope

**In scope**

1. The rename: `UserType` → `Role` everywhere — model, table, link table,
   schemas, service, endpoint module, URL prefix, permission module,
   frontend types/hooks/components, i18n (§2), plus migration `0032`.
2. Re-expressing the **15 F5-marked role reads** (8 Rule-C + 7 Rule-N) plus the
   **five** reads outside the allowlists, on three new catalogue permissions (§3).
3. Deleting the `allowed_menus` menu gate — column, `MenuKey`,
   `deps.assert_menu_access`, its 12 call sites, and the frontend's
   `useMenuAccess` (§4). The behaviour delta is enumerated and pinned.
4. Migration `0033`: run the **pre**-condition refuse-guard (§7.0), open the
   downgrade journal, create the missing role rows, backfill legacy bundles into
   `role.permissions`, backfill **explicit** memberships, rewrite the document
   folder ACL, add `role.landing_path`, run the **post**-condition refuse-guard
   (§7.3), then drop `user.role`, `role.allowed_menus`, `role.role`, the index
   and the Postgres `userrole` type (§5, §6, §7).
5. Deleting `LEGACY_ROLE_PERMISSIONS`, `_LEGACY_ROLES_BY_PERMISSION` and
   `ADMIN_GAP_PERMISSIONS`'s role framing (§8). F3 §5.1 **deletes**
   `TENANT_ADMIN_PERMISSIONS` outright, so normally there is nothing left to do;
   if it survived F3 for any reason it is a *production* constant carrying the
   three `user_types:*` strings, and both they and its
   `test_permission_registry.py` pin move with the §2.1 rename sweep — the first
   §2.2 grep sees the strings, but nothing renames the pin's test name for you.
6. `app/seed.py` rewritten on the new model, three demo profiles, and the
   nexdom migrate/restore runbook (§9).
7. The frontend death of `UserRole` — all 30 non-test files, the landing
   redirects re-expressed as `role.landing_path` data, simulation re-expressed
   on role ids (§10).
8. The parity story's ending: the 1080-cell matrix re-keyed on **profiles**
   with the golden file left **byte-identical**, plus the migration-level
   permission-set equality pin (§11).
9. `AGENTS.md` rewritten to describe the model that exists (§13).

**Explicitly NOT in scope**

* **No new authorization semantics.** Every replacement below is chosen so its
  legacy role set is *exactly* the set the comparison it replaces expressed.
  The exceptions are enumerated, justified and tested individually: the menu
  gate's widening (§4.2), the self-guard's narrowing (§8.5) and the three
  frontend deltas (§10.5). One further widening — the one the backfill would
  cause for a user **explicitly linked to a legacy role row that is not their
  enum role** — is **refused**, not accepted: `0033` stops before it writes
  anything and names the users (§7.0). `0033` is therefore
  effective-set-preserving for **every** user it lets through, not merely for
  the users §11.2 happens to seed.
* **No `is_superuser` grant *UI*.** F3 shipped one transitional *writer* — the
  `update_user` role-change mirror of §3.3 #5, marked
  `TRANSITIONAL (IAM F3 -> F5)` — and handed the question here; the earlier
  claim that "F3 shipped none deliberately" was simply wrong about the sibling
  spec this one declares as a precondition. F5 deletes that mirror and
  **replaces** it with one explicit, superuser-only API route (§8.4), so the
  grant *and the revoke* keep a home. F5 ships **no frontend control** for it:
  `UserRead` deliberately does not carry the flag (§8.3) and an admin table
  cannot render a column it cannot read. The operator uses the route or SQL.
* **No per-user loose permissions and no role nesting** — the board's standing
  decisions, unchanged.
* **No `/api/v1/user-types` compatibility alias.** The rename is a breaking
  API change; both clients ship in the same commit and there is no documented
  third-party consumer (§2.4).
* **No pagination/search redesign of `GET /users/`** (F4 §6.4's recorded
  caveat stands).
* **No change to `Task.visible_to` as a concept.** It keeps targeting role
  rows; only the *predicate that decides who is scoped by it* changes (§3.2).
* **No deletion of `ResidentRelationship`, `LotAssociationType`, `TaskStatus`,
  `TaskPriority`** or any other enum. Only `UserRole` and `MenuKey` die.

---

## 2. The rename

### 2.1 The naming table (the whole of deliverable A)

| Today | After |
|---|---|
| `app/models/user_type.py` → `class UserType`, `__tablename__ = "user_type"` | `app/models/role.py` → `class Role`, `__tablename__ = "role"` |
| `app/models/user_type_link.py` → `UserUserTypeLink`, table `user_user_type_link`, column `user_type_id` | `app/models/role_link.py` → `UserRoleLink`, table `user_role_link`, column `role_id` |
| `task_visible_to_link.user_type_id` | `task_visible_to_link.role_id` |
| indexes `ix_user_type_tenant_name`, `ix_user_type_tenant_role` | `ix_role_tenant_name`; the second is **dropped** (§7.3) |
| `app/schemas/user_type.py` → `UserTypeCreate/Update/Read` | `app/schemas/role.py` → `RoleCreate/RoleUpdate/RoleRead` |
| `app/services/user_type_service.py` → `assert_can_grant`, `assert_can_assign_user_types` | `app/services/role_service.py` → `assert_can_grant`, `assert_can_assign_roles` |
| `app/api/v1/endpoints/user_types.py`, prefix `/api/v1/user-types` | `app/api/v1/endpoints/roles.py`, prefix `/api/v1/roles` |
| path param `{user_type_id}` | `{role_id}` |
| permissions `user_types:read|create|update|delete` | `roles:read|create|update|delete` |
| `deps.get_effective_user_type_ids` | `deps.get_effective_role_ids` |
| `User.user_types` relationship | `User.roles` |
| `UserRead.user_types`, `UserUpdate.user_type_ids` | `UserRead.roles`, `UserUpdate.role_ids` |
| `TenantService.ROLE_TYPE_NAMES` / `ensure_role_types` | `LEGACY_ROLE_NAMES` / `ensure_legacy_roles` (§9.2) |
| TS `interface UserType`, `useUserTypes`, `UserTypeMultiSelect`, `userTypeIds` | `interface Role`, `useRoles`, `RoleMultiSelect`, `roleIds` |
| i18n `admin.userTypes*`, `simulation.userTypes*`, `nav.groups`, `groups.*` (F4) | `admin.roles*`, `simulation.roles*`, `nav.roles`, `roles.*` |

**"Grupo" disappears from the UI too.** F4 shipped `/admin/groups`,
`GroupsAdminPage`, `GroupDetailPage`, `GroupMembersPanel` and a `groups.*` i18n
namespace. ER-1 says the entity is called **role** in the API *and in the UI*,
so those become `/admin/roles`, `RolesAdminPage`, `RoleDetailPage`,
`RoleMembersPanel`, `roles.*`. The pt-BR display word is **"Papel" / "Papéis"**
(the word the six legacy rows already use: `"Diretor (papel)"`); en is
**"Role" / "Roles"**.

### 2.2 The mechanical greps that define "done"

Run from the repository root; all three must return **nothing**:

```
grep -rn "user_type\|UserType\|user-types\|userType" backend/app frontend/src
grep -rn "UserRole\|allowed_menus\|MenuKey\|LEGACY_ROLE_PERMISSIONS" backend/app frontend/src
grep -rni "\bgrupo\b\|\bgroups\?\b" frontend/src/i18n frontend/src/features/user-administration --include='*.ts' --include='*.tsx' --include='*.json'
```

The third has one permitted exception: the word "group" inside a
`<fieldset>`/`role="group"` ARIA attribute or a CSS class. The PR body quotes
each grep's output.

Measured today (`02c2025` + the in-flight F2 tree), as the size the implementer
should expect: **22** backend production files and **23** backend test modules
match the first grep; **20** frontend non-test files and **41** test files match
it; **19** backend production files and **30** frontend non-test files match
bare `UserRole`. Re-measure every one of these at F4's merge base; the PR body
quotes baseline and final.

### 2.3 Migration `0032_rename_user_type_to_role`

* `revision = "0032_rename_user_type_to_role"` — **29 characters**
  (`python -c 'print(len("0032_rename_user_type_to_role"))'` → `29`), inside the
  `alembic_version VARCHAR(32)` limit. `down_revision = "0031_add_user_is_superuser"`.
* `upgrade()`, in order:
  1. `op.rename_table("user_type", "role")`
  2. `op.rename_table("user_user_type_link", "user_role_link")`
  3. `op.alter_column("user_role_link", "user_type_id", new_column_name="role_id")`
  4. `op.alter_column("task_visible_to_link", "user_type_id", new_column_name="role_id")`
  5. `op.execute('ALTER INDEX ix_user_type_tenant_name RENAME TO ix_role_tenant_name')`
     and the same for `ix_user_type_tenant_role` → `ix_role_tenant_role`
     (dropped by `0033`; renamed here so `0032` is self-consistent and
     independently reversible).
  6. Foreign-key and primary-key constraint names: Postgres carries them from
     the renamed table automatically for `rename_table`; **the implementer must
     verify** with `\d role` / `\d user_role_link` on the throwaway database and
     rename any constraint whose name still says `user_type`, quoting the
     `pg_constraint` listing in the PR body.
* `downgrade()` is the exact inverse, step for step. **`0032` is fully and
  losslessly reversible** — it moves no data and drops nothing.
* No data statement of any kind. `alembic heads` reports `0032…` after it.

### 2.4 The API break

`/api/v1/user-types` becomes `/api/v1/roles` with no alias and no deprecation
window. Justification, recorded so it is not rediscovered: the only client is
`frontend/`, shipped from the same commit; the four routes are administrative;
and an alias would double the matrix rows, the `ROUTE_PERMISSIONS` keys and
the guard surface for one release. `docs/`, `AGENTS.md`'s endpoint table and
`frontend/src/api/` move together.

---

## 3. The 15 F5-marked survivors, and the three permissions that replace them

### 3.0 The three new catalogue permissions

`PERMISSIONS` goes **156 → 159**; modules stay **26** (`user_types` → `roles`).

| New permission | Meaning | Legacy holders (backfilled by `0033`) |
|---|---|---|
| `tasks:read_all` | see every task regardless of its `visible_to` targets, and author tasks without target defaulting | `{A, D, R, P}` |
| `tasks:update_any` | edit a task that is assigned to someone else | `{A, D, R, P}` |
| `occurrences:read_assigned` | see occurrences assigned to me even without `occurrences:manage_all` | `{M}` |

They are **grants, not restrictions** — holding more is never less access —
which is what makes them expressible in a model with no negative permissions.
Each is added to `PERMISSIONS` with a docstring naming the F5-marked site it
replaces, and none is added to `ROUTE_PERMISSIONS`: they are in-code object
predicates, exactly like `occurrences:manage_all` and `gate:checkin`, which F2
introduced the same way.

`MANAGER` deliberately does **not** get `tasks:read_all` / `tasks:update_any`
and `A/D/R/P` deliberately do **not** get `occurrences:read_assigned`: those
two facts *are* the legacy tiers, now stored as data instead of compiled into
`if` statements.

### 3.1 Rule-C survivors (8) — the conversion table

| # | Site (`module::function`) | Today | After |
|---|---|---|---|
| 1 | `api/deps.py::assert_manager_can_see_task` | `if current_user.role == UserRole.MANAGER:` then the `visible_to` intersection | `if not has_permission(current_user, session, "tasks:read_all"):` — same body, same `TaskNotFoundError` |
| 2 | `api/deps.py::assert_can_edit_task` | `if current_user.role == UserRole.MANAGER:` then own/unassigned | `if not has_permission(current_user, session, "tasks:update_any"):` — same body, same `ForbiddenError("Managers can only edit unassigned or self-assigned tasks")` (message kept verbatim; §13 records it as legacy wording) |
| 3 | `api/deps.py::get_effective_user_type_ids` | explicit ids ∪ `select(Role).where(Role.role == user.role)` | renamed `get_effective_role_ids`; body becomes `{r.id for r in user.roles if r.tenant_id == tenant_id}`. **The role-implicit membership becomes explicit at migration time** (§7.2), so the resolved set is unchanged for every existing user. `session` stays in the signature — it is what resolves the acting tenant. |
| 4 | `api/v1/endpoints/tasks.py::list_tasks` | `if current_user.role == UserRole.MANAGER:` then the `or_(~has_any_target, has_matching_target)` filter | `if not api_deps.has_permission(current_user, session, "tasks:read_all"):` — identical query construction |
| 5 | `services/task_service.py::create_task` | `if current_user.role == UserRole.MANAGER and not visible_to_ids:` | `if not visible_to_ids and not has_permission(current_user, session, "tasks:read_all"):` — identical defaulting (explicit roles first, effective set as fallback) |
| 6 | `services/task_service.py::update_task` | `if visible_to_ids is not None and current_user.role == UserRole.MANAGER:` | `if visible_to_ids is not None and not has_permission(current_user, session, "tasks:read_all"):` — identical subset rule and message |
| 7 | `services/occurrence_service.py::_check_user_access` | `if current_user.role == UserRole.MANAGER:` (assigned-to-me ∨ reported-by-me ∨ public) | collapses one tier: `reporter == me or is_public or (has_permission(…, "occurrences:read_assigned") and assigned_to_id == me)` |
| 8 | `services/occurrence_service.py::get_occurrences` | the same tier as a query filter | one `or_(...)` whose `Occurrence.assigned_to_id == current_user.id` term is included **iff** `has_permission(…, "occurrences:read_assigned")` |

Sites 1/4/5/6 all key on **one** permission, which is the point: the four
places that spell "MANAGER is scoped by `visible_to`" become four reads of one
fact.

**Why the conversion is exact, GUEST included.** `tasks:read_all` is legacy
`{A,D,R,P}` = `holders(tasks:read) - {M}`, so for every actor that can *reach*
sites 1, 2, 4, 5 and 6, `not has_permission(..., "tasks:read_all")` is
equivalent to `role == UserRole.MANAGER`. The single actor for which the two
predicates differ is GUEST (`role != MANAGER`, and no `tasks:read_all`), and a
GUEST holds none of `tasks:read` / `tasks:create` / `tasks:update` (all
`{A,D,M,R,P}`), so `require_permission` refuses before any of these lines runs:
**the divergent state is unreachable**. This is the backend twin of §10.5 (b)'s
argument for `TaskForm`, and it is the load-bearing one — §10.5 (b) only guards
a form. Sites 7 and 8 need no such argument at all: `occurrences:read_assigned`
is legacy `{M}` *exactly*, so they are literal rewrites.

### 3.2 Rule-N survivors (7 reads, 5 functions)

| Site | Today | After |
|---|---|---|
| `services/document_service.py::get_accessible_folder_ids` (3 reads on one line) | `role_str = user.role.value if hasattr(...)`; matched against `folder.allowed_roles_json` | the folder ACL becomes **role ids**: `accessible = {f.id for f in folders if set(json.loads(f.allowed_role_ids_json)) & {str(i) for i in effective_role_ids}}` (§6) |
| `api/deps.py::get_effective_permissions` | `LEGACY_ROLE_PERMISSIONS.get(user.role, frozenset())` seeds `granted` | **deleted**. `granted` starts empty and is filled from the user's roles only (plus F3's superuser / tenant_admin short-circuits, untouched) |
| `api/v1/endpoints/lots.py::link_user_to_lot` | `UserSummaryRead(…, role=user.role)` | `roles=[r.name for r in user.roles]` (§8.2) |
| `services/lot_service.py::get_lot_detail` | idem | idem |
| `services/tenant_service.py::_to_member_read` | `TenantMemberRead(…, role=user.role)` | `roles=[…]` (§8.2) |

### 3.3 The five reads outside both allowlists — named because an exact-match test cannot see them

F2's AST walkers only count reads whose base `Name` is in `ACTOR_NAMES`, and
skip `app/models/`, `app/schemas/` and `app/seed.py`. These five are real and
die here anyway. Only #1's base name defeats the walker; #2, #3 and #5 are
reads of the **payload** (`user_in` / `update_data`), which no actor-name walker
was ever going to see, and #4 lives in an excluded package:

1. `api/v1/endpoints/residents.py::…` — `role=resident.user.role` into
   `ResidentUserRead` (base name `resident`). → `roles=[…]` (§8.2).
2. `api/v1/endpoints/users.py::update_user` — `user_in.role == UserRole.ADMINISTRATOR`
   (the "tenant admins cannot grant the ADMINISTRATOR role" rule). **Deleted**:
   there is no role to grant, and `is_superuser` stops being writable through
   `PATCH /users/{user_id}` at all — it moves to its own superuser-only route
   (§8.4), which no tenant admin can call. This *closes* the escalation hole
   APRAS-46 §12.5 recorded as inherited (§8.3).
3. `api/v1/endpoints/users.py::update_user` — the self-guard
   `user_in.role is not None and user_in.role != db_user.role` → becomes
   `"role_ids" in update_data and set(role_ids) != {r.id for r in db_user.roles}`
   with the same 400 and a new detail `"Administrators cannot change their own roles"`.
   This **extends** the guard's reach — today `user_type_ids` is not
   self-guarded — and is enumerated as the fourth behaviour delta in §8.5.
4. `app/models/user.py::__init__` — F3's transitional `is_superuser` default.
   **Deleted with the enum**, together with F3's
   `test_the_superuser_default_is_the_only_administrator_literal_in_models`.
5. `api/v1/endpoints/users.py::update_user` — F3 §7.3's role-change mirror,
   shipped marked `TRANSITIONAL (IAM F3 -> F5)`:

   ```python
   if update_data.get("role") is not None:
       db_user.is_superuser = update_data["role"] == UserRole.ADMINISTRATOR
   ```

   F3 shipped it so that **demoting** an administrator would not strand
   `is_superuser` set — its own words: "a privilege-retention hole this slice
   would have created" — and called it "what lets F5 drop the enum without
   losing or stranding a grant". Deleting it along with `UserUpdate.role` would
   delete the only API **revoke** path with it and leave a demoted
   administrator holding the whole catalogue in every tenant, SQL being the
   only cure. So it is **deleted and replaced**, not merely deleted: §8.4 gives
   the grant *and* the revoke an explicit, superuser-only home, and §8.4's
   zero-superuser guard is strictly stronger than what the mirror provided.

---

## 4. The menu gate: deleted, not translated

### 4.1 What goes

`UserType.allowed_menus` (column + schema field on all three schemas),
`MenuKey`, `deps.assert_menu_access`, its **12** call sites
(`endpoints/tasks.py` ×8, `endpoints/categories.py` ×4), and on the frontend
F4's `legacyMenu` field on the two `ROUTE_ACCESS` entries, the three lines in
`useCanAccess`, `context/useMenuAccess.ts` and its two test files
(`useMenuAccess.test.tsx`, `useMenuAccess.crossTenant.test.tsx`) — F4's
six-item hand-off list, which is F4 **§11** (F4 §11.1 is that spec's two greps).
Hand-off item 5 is the one a grep almost misses and is therefore named here:
the `allowed_menus` derivation in F4's group-editor **save payload**
(`RoleDetailPage`'s submit handler, née `GroupDetailPage`) goes with the column
— the editor stops sending the field and `RoleUpdate` stops accepting it. Only
ER-6's `allowed_menus` grep would otherwise catch it.

`has_admin_capability` loses its only caller and is **deleted** with it
(F3 §5.1 #3 already noted `assert_menu_access` is its sole consumer).
`is_acting_tenant_admin` stays: `get_effective_permissions` still calls it.

### 4.2 The one deliberate behaviour delta, stated so it is not rediscovered as a bug

The gate was a **coarse AND** in front of the permission check, on 12 handlers.
Removing it widens access for exactly one population:

> a user who holds `tasks:read` (legacy `{A,D,M,R,P}`) or `categories:read`
> (all roles) but **none** of whose roles carries the corresponding
> `allowed_menus` key, and who is not admin-capable.

Why it is not translated:

* Folding the gate into each role's bundle **per role** would strip `tasks:*`
  from all six legacy rows (they are all seeded `allowed_menus = []`, migration
  `0018`), locking every non-superuser out of Tarefas. Catastrophic narrowing.
* Folding it **per user** is not expressible: permissions live on roles, and
  the board has ruled out per-user permissions. Manufacturing one
  `(role × menu-profile)` row per combination would create up to 24
  machine-generated rows per tenant and contradict "no system groups".
* The gate's job — "who sees Tarefas" — is now done, and done *finer*, by
  `tasks:read` in a role. Keeping both would be two sources of truth for one
  question, which is the drift this chain exists to remove.

The operator's replacement lever is stated in `AGENTS.md`: remove `tasks:*`
from the role. The delta is pinned by
`tests/test_menu_gate_removal.py::test_a_user_without_the_legacy_menu_key_now_reaches_tasks`
and `…::test_a_user_without_tasks_read_is_still_refused`, and quoted in the PR
body.

**It is invisible to the parity matrix by construction**, and that is correct
rather than convenient: `matrix_world` gives every actor a menu-granting type
precisely so the matrix measures permissions and not menus (F2 §6.2). The
matrix therefore still proves the 1080 authorization outcomes are unchanged
(§11), and this section carries the one thing it cannot see.

---

## 5. Migration plan — two migrations, and why not one

| | `0032_rename_user_type_to_role` | `0033_drop_user_role_and_menus` |
|---|---|---|
| Moves data | no | yes (backfill) |
| Drops data | no | yes (`user.role`, `allowed_menus`, `role.role`) |
| Reversible | **exactly** | **schema-exact; every write journalled and restored exactly; only the two dropped columns are lossy** (§7.5) |

One migration would make the exactly-reversible half hostage to the lossy half:
a `downgrade -1` from head would be forced to un-rename *and* re-invent role
values in one step, and the operator would lose the ability to back out the
semantic change while keeping the rename. `alembic heads` reports the single
head `0033_drop_user_role_and_menus` at the end (ER-2).

`revision = "0033_drop_user_role_and_menus"` — **29 characters**
(`python -c 'print(len("0033_drop_user_role_and_menus"))'` → `29`).
`down_revision = "0032_rename_user_type_to_role"`.

**`0033` imports nothing from `app/`.** A migration is a historical artefact; if
it read `app.core.permissions`, its behaviour would change every time the
catalogue changes. The legacy bundle is **inlined as a literal** in the
migration file and its correctness is pinned against a recorded artefact
(§7.6).

---

## 6. The document-folder ACL

`DocumentFolder.allowed_roles_json` stores a JSON list of `UserRole` **strings**.
It is a per-object, data-driven ACL and it is the one place the enum leaked into
user data. **Two different defaults carry the same literal and must not be
confused**: `app/models/document.py` gives the field a *Python-side*
`default='["ADMINISTRATOR", "DIRECTOR", "MANAGER", "RESIDENT"]'` (applied by
SQLModel on insert), and migration `0010_add_document_tables` gave the *column* a
`server_default` with the same string (applied by Postgres). This slice moves
both, and `downgrade()` restores both (§7.5).

**Decision: it becomes a list of role *ids*, and the column is renamed** to
`allowed_role_ids_json`. Renaming rather than reusing the name is deliberate —
the *content type* changes, and a reader that was not updated must fail loudly
instead of silently matching nothing.

**All four field sites move, and only one of them is grep-visible.** The column
rename is caught by ER-1's `user_type` grep only by accident; the *schema* fields
are named `allowed_roles`, which matches none of §2.2's or ER-6's greps. Named
here so none is missed:

| Site | Today | After |
|---|---|---|
| `app/models/document.py::DocumentFolder` | `allowed_roles_json: str`, Python `default=` the four-value literal | `allowed_role_ids_json: str`, Python `default='[]'` |
| `app/schemas/document.py::DocumentFolderCreate` | `allowed_roles: list[str]` with the four-value default | `allowed_role_ids: list[str]` — **required** (`Field(...)`) |
| `app/schemas/document.py::DocumentFolderUpdate` | `allowed_roles: list[str] \| None = None` | `allowed_role_ids: list[str] \| None = None` |
| `app/schemas/document.py::DocumentFolderRead` (and `DocumentFolderTreeRead`, which inherits it) | `allowed_roles: list[str] = []` | `allowed_role_ids: list[str] = []` |

`document_service.py` writes and reads that field at six sites
(`create_folder`, `update_folder`, `get_folder_tree`, `list_folders`, and the two
read serialisations); all six move with the rename, and
`test_document_folder_acl.py` (§12.1) covers create/update/read as well as the
access predicate.

* **The join key is `role.role`, never `role.name` — in both directions.**
  `allowed_roles_json` stores `UserRole` **values** (`"DIRECTOR"`); the legacy
  rows' `name` is the pt-BR label (`"Diretor (papel)"`). Nothing is named
  `"DIRECTOR"`, so a name join matches nothing forward, and a name written back
  on downgrade is compared by the restored `get_accessible_folder_ids` against
  `user.role.value` and matches nothing backward — the first empties every
  folder ACL in every tenant, the second denies every non-staff user, and both
  do it silently. The `role.role` column is still present at this point in
  `0033` (§7.4 drops it strictly later, and that ordering is load-bearing), and
  it is the only correct key.
* `0033` rewrites every row: each legacy role string maps to the id of the role
  row of **that folder's tenant** whose `role` column equals that string
  (`document_folder` carries `tenant_id`; the mapping is per tenant, and the row
  is guaranteed to exist because §7.1 creates the missing ones first).
* **No silent drop-and-log for legacy values.** A string that *is* a `UserRole`
  value and finds no row in the folder's tenant is an assertion failure —
  `raise RuntimeError` naming the folder id, the tenant id and the value —
  because §7.1 makes it impossible, and a fallback there is precisely what
  would swallow the name-vs-value mistake above. A string that is **not** a
  `UserRole` value (hand-edited or foreign data) is still dropped and logged in
  the migration's output, with a count in the summary line.
* Every folder whose ACL is rewritten is journaled (§7.0), so `downgrade()`
  restores the **original bytes** of `allowed_roles_json` rather than
  reconstructing them. The round trip is pinned by
  `test_migrations_postgres.py::test_0033_document_folder_acl_round_trips`
  (ER-2): the set of `(folder id, allowed roles)` pairs read **pre-`0033`**, the
  same set **post-`0033`** with the ids mapped back through `role.role`, and the
  set read **post-`alembic downgrade -1`** are all three **identical**, over a
  fixture with two tenants and four folders — the seeded default ACL, a
  single-role ACL, an empty ACL, and one carrying an unknown string (which
  survives pre→post→down through the journal even though the forward rewrite
  drops it from the id list).
* **Both defaults become `'[]'`.** Neither can name the four role ids: a
  `server_default` is a constant expression and role ids differ per tenant and
  per install. So `0033` sets the column's `server_default` to `'[]'`
  (`op.alter_column(..., server_default="'[]'")` on the renamed column), the
  model's Python-side `default=` becomes `'[]'`, and
  `DocumentFolderCreate.allowed_role_ids` becomes a **required** field on the
  create schema — a folder created without an explicit ACL would otherwise be
  invisible to everyone, so the caller is made to say. `downgrade()` renames the
  column back **and** restores `0010`'s `server_default` string verbatim
  (§7.5 step 2). The frontend's `FolderFormModal`
  already renders a checkbox list; it now renders it from `useRoles()` instead
  of the hard-coded `ALL_ROLES` constant, which is a straight improvement (a
  folder can now be scoped to any role, not only the six legacy ones).
* `get_accessible_folder_ids` keeps its staff bypass
  (`has_permission(user, session, "documents:folder_create")`) verbatim and
  intersects `allowed_role_ids_json` with `get_effective_role_ids(user, session)`.
* `downgrade()` restores journaled folders byte-for-byte. A folder created
  **after** `0033` has no journal row; for it each id maps back to that role
  row's `role` **value**, and an id whose row has `role IS NULL` — an ordinary,
  non-legacy role — is dropped. `downgrade()` therefore renames the column back
  and repopulates `role.role` **before** it touches the folder ACL contents
  (§7.5's order is explicit about both).

Frontend: `types/document.ts` `allowed_roles: string[]` → `allowed_role_ids:
string[]`; `DocumentCenter.test.tsx` and `api/__tests__/documents.test.ts`
fixtures move from role strings to ids (§12.2).

---

## 7. Migration `0033` — the whole of it, in order

### 7.0 Before anything is written: the pre-condition refuse-guard, and the journal

#### (a) Refuse the one widening the backfill would otherwise cause

Today the six legacy rows carry `permissions = []` — `app/models/user_type.py`
says so in as many words ("NOTHING seeds this") — and
`get_effective_permissions` seeds `granted` from
`LEGACY_ROLE_PERMISSIONS[user.role]`. So an **explicit** membership in
`Diretor (papel)` grants a legacy MANAGER *nothing* today; it only widens the id
set `Task.visible_to` intersects. After §7.2 step 1 that same row carries
DIRECTOR's full bundle, and that user would silently acquire the whole director
set — including `tasks:read_all` and `tasks:update_any`, i.e. they would stop
being scoped by `visible_to` and could edit other-assigned tasks.

The state is reachable through the shipped API — `endpoints/users.py::_assign_user_types`
accepts **any** row of the acting tenant (it filters on `tenant_id`, then runs
`assert_can_assign_user_types`, which passes trivially on an empty bundle) — and
through F4's group editor. "Add the manager to `Diretor (papel)` so he sees
director-targeted tasks" is a natural operator action, so this population is not
hypothetical.

`0033` **refuses** it rather than accepting it, as its very first statement,
before a single write:

```sql
SELECT u.email, r.name AS role_name, r.role AS legacy_role, t.name AS tenant
FROM user_role_link l
JOIN "user"  u ON u.id = l.user_id
JOIN role    r ON r.id = l.role_id
JOIN tenant  t ON t.id = r.tenant_id
WHERE r.role IS NOT NULL
  AND r.role <> u.role
ORDER BY u.email, t.name, r.name
```

(post-`0032` names; the table is `role` and the link column `role_id` by the
time `0033` runs.) Non-empty ⇒ `raise RuntimeError` listing one
`email — role_name (tenant)` per line, plus the remediation below. Because it is
a **pre**-condition, a refusing install has **no row written and no column
dropped**; on an `alembic upgrade head` from `0031` it is left at **`0032`**
(the rename is a separate, already-committed migration), which is exactly what
§9.3's runbook assumes when it says "fix and re-run".

Two remediations are printed, and **both preserve today's effective permission
set exactly**:

1. **Drop the link** — `DELETE FROM user_role_link WHERE user_id = '…' AND role_id = '…';`
   Permissions are unchanged (the row grants nothing today); the user stops
   matching tasks targeted at that legacy row.
2. **Move the targeting off the legacy row** — create an ordinary role in that
   tenant with `permissions = []` (e.g. `"Visibilidade — diretoria"`), link the
   affected users to it, add it to the `visible_to` of the tasks that need them,
   then drop the legacy link. Preserves permissions **and** targeting.

There is deliberately **no override flag**. An env var would let the widening
ship silently, which is the single thing this guard exists to prevent, and the
state is always resolvable with the SQL the guard itself prints.

Two neighbouring cases are explicitly **not** refused, and must not be:

* a link to a **non-legacy** row (`role IS NULL` — `Diretor Comercial`, any
  F4-authored group). §7.2 step 1 updates only the six legacy rows, so those
  bundles are untouched and the user's effective set is unchanged by
  construction.
* a link to the legacy row that **matches** the user's enum (a MANAGER in
  `Gerente (papel)`). The row gains exactly the bundle the enum already granted
  that user, so it is not a widening; `r.role <> u.role` lets it through and
  §7.2 step 2 then skips it as already present.

On nexdom the query returns **0 rows**; the PR body quotes the run.

#### (b) Open the downgrade journal

```sql
CREATE TABLE f5_backfill_journal (
    id      SERIAL PRIMARY KEY,
    kind    VARCHAR NOT NULL,   -- 'role_permissions' | 'user_role_link' | 'folder_acl'
    ref_id  VARCHAR NOT NULL,
    ref_id2 VARCHAR NULL,
    payload VARCHAR NOT NULL    -- the pre-backfill value, as JSON text
)
```

`upgrade()` writes one journal row immediately **before** each write it makes
(§7.2 steps 1–3); `downgrade()` replays it by **descending `id`** and drops the
table (§7.5 step 5). It is what turns "best-effort" into "exact" for everything
this migration *writes*.

**The journal is mandatory for `downgrade -1`, not best-effort.** Its very first
statement is `SELECT to_regclass('f5_backfill_journal')`; if that is NULL,
`downgrade()` raises

> `RuntimeError: f5_backfill_journal is missing; 0033 cannot be reversed without it. Restore the table from a backup, or stay at head.`

**before it changes a single thing** — no column is recreated, no rename is
undone, so a refusing downgrade leaves the database at head, untouched, exactly
as §7.0 (a) leaves a refusing upgrade at `0032`. The alternative (reconstructing
bundles and links from a literal) would silently produce a *different* install
from the one that existed before `0033` and call it a rollback; refusing is the
honest option, and the operator is told up front (§13) that dropping the table is
a one-way door.

**The journal is invisible to SQLModel's metadata.** It is created by raw DDL in
`0033` and has no model class, so `alembic revision --autogenerate` at head would
propose `op.drop_table("f5_backfill_journal")`. No workflow in this repository
runs `--autogenerate` (every migration in `alembic/versions/` is hand-written),
so this is a **note, not a task**: it is recorded here and in §13 so that whoever
first reaches for autogenerate does not delete the rollback path by accident.

Its scope is exactly the three things `0033` writes, and deliberately **not**
the two things `0033` drops: `role.allowed_menus` and `user.role` values are not
journaled. Journaling `user.role` would make §7.5's precedence rule dead code
and hide a data-model change behind a byte restore; journaling `allowed_menus`
would preserve a column whose meaning this slice deletes.

The table **persists at head** — that is what makes `0033` reversible — and is
dropped by `downgrade()`. `AGENTS.md` records it, and records that
`DROP TABLE f5_backfill_journal` is safe **only** once the operator is certain
they will never downgrade past `0033`: after that, `alembic downgrade -1` refuses
by name rather than degrading.

### 7.1 Create the missing legacy role rows

`0018` seeded **five** role-linked rows in the default tenant
(`tests/test_migrations_postgres.py::test_user_type_role_seeds_five_rows`);
`PORTEIRO` arrived later (`0020`) and only ever appears through
`TenantService.ensure_role_types`, so a production tenant can be missing it.
For every `(tenant, legacy role)` pair with no row, insert one with the
`LEGACY_ROLE_NAMES` name, `permissions = []`, `allowed_menus = []`. Idempotent
by the `(tenant_id, role)` unique index that still exists at this point.

**These inserts are deliberately not journaled and not reversed**, which is the
one qualification on §7.5's "restores everything `0033` wrote". A row created
here is an empty legacy role in a tenant that was missing it; it survives
`downgrade -1` (with its `role` value recomputed by §7.5 step 3, since its name
is a `LEGACY_ROLE_NAMES` name), so the restored `get_effective_user_type_ids`
resolves it implicitly for `Task.visible_to` purposes. That grants **no
permission** — the row's `permissions` is `[]`, and after the journal replay it
is `[]` again — and `TenantService.ensure_role_types` would have created the same
row on the tenant's next touch anyway. Deleting them on downgrade would be the
more surprising behaviour, so they stay, said out loud here rather than left as a
gap in §7.5's word "everything".

### 7.2 Backfill: bundles, then memberships

1. For each of the six legacy rows in **every** tenant: journal
   (`kind='role_permissions'`, `ref_id=role.id`, `payload=` the row's current
   `permissions`), then `UPDATE role SET permissions = <current ∪ literal[legacy_role]>`,
   where the literal is the inlined `LEGACY_ROLE_PERMISSIONS[r] ∪ NEW_TIER[r]`
   (§3.0, §7.6). Rows whose `permissions` is already non-empty (an operator
   edited a legacy row through F4's UI) are **unioned, never replaced** — the
   same additive-only discipline F4 §2.3 applied to `allowed_menus`, for the
   same reason: this migration must not be able to revoke.
2. `INSERT INTO user_role_link (user_id, role_id)` one row per
   `(user, tenant the user is linked to)` pair, joining **only** the legacy role
   row of that tenant whose `role` equals the user's `user.role` — never any
   other legacy row — skipping pairs that already exist, and journaling each
   insert (`kind='user_role_link'`, `ref_id=user_id`, `ref_id2=role_id`,
   `payload='{}'`). **This is the whole of the "implicit becomes explicit"
   decision**: after it, `get_effective_role_ids` needs no role column, and
   every user's effective permission set is reproduced from data.

   Linking strictly per the enum value is what makes the backfill
   effective-set-preserving. Combined with §7.0 (a) — which has already refused
   every user whose explicit links point at a *different* legacy row — and with
   the fact that non-legacy bundles are untouched, **every user the migration
   lets through leaves §7.2 with exactly the effective set they entered with,
   plus that role's `NEW_TIER` entries, and nothing else.** That is the sentence
   §11.2 and ER-3 assert, and it now holds for the whole population rather than
   for the cases §11.2 happens to seed.
3. `document_folder` ACL rewrite (§6), journaling each rewritten folder
   (`kind='folder_acl'`, `ref_id=folder.id`, `payload=` the pre-rewrite
   `allowed_roles_json`) before it writes.
4. `ALTER TABLE role ADD COLUMN landing_path VARCHAR NULL`, then
   `UPDATE role SET landing_path = '/gate' WHERE role = 'PORTEIRO'` and
   `= '/welcome' WHERE role = 'GUEST'`. This is the slice's **only additive
   schema**, and §10.4 is its whole justification.

### 7.3 The second refuse-guard (ER-3), as a **post**-condition

The migration has two guards. §7.0 (a) is a **pre**-condition and refuses a
widening; this one is a **post**-condition and refuses a *narrowing* — a user
the backfill left with no way in. Run **after** the backfill, before any drop:

```sql
SELECT u.email
FROM "user" u
WHERE u.is_active
  AND NOT u.is_superuser
  AND NOT EXISTS (SELECT 1 FROM user_role_link l WHERE l.user_id = u.id)
  AND NOT EXISTS (SELECT 1 FROM user_tenant_link t
                  WHERE t.user_id = u.id AND t.is_tenant_admin)
ORDER BY u.email
```

Non-empty ⇒ `raise RuntimeError` whose message lists every email, one per line,
plus the remediation: *"give the user a tenant membership and re-run, or set
`is_superuser = true`"*.

A pre-condition guard would be satisfied by luck (the enum is NOT NULL, so
every user trivially has a role); as a **post**-condition it asserts the
backfill was complete, and it is genuinely reachable: a user with zero
`user_tenant_link` rows gets zero memberships from §7.2 step 2 and trips it.
That is exactly the state the Postgres test constructs (§12.1).

### 7.4 The drops

In this order:

1. `op.drop_index("ix_role_tenant_role", table_name="role")`
2. `op.drop_column("role", "role")`
3. `op.drop_column("role", "allowed_menus")`
4. `op.drop_column("user", "role")` (quoted — reserved word)
5. `op.execute("DROP TYPE userrole")` — Postgres only; guarded by
   `if op.get_bind().dialect.name == "postgresql":`, the pattern `0012`/`0020`
   already use for enum DDL.

### 7.5 The reversibility contract, stated explicitly

`downgrade()` restores the **schema** exactly, restores everything `0033`
*wrote* exactly (from the journal, §7.0 (b), with the one stated exception of
§7.1's empty role rows), and restores what `0033` *dropped* best-effort. All
three statements go into the migration's docstring and into `AGENTS.md`.

**The order below is load-bearing and was got wrong once.** Two steps read state
that another step destroys: the `user.role` recompute reads memberships that the
journal replay deletes, and the folder-ACL restore reads `role.role` and a column
name that step 1/2 have to put back first. The steps are therefore numbered, and
each one that depends on a predecessor says so.

0. **Refuse if the journal is gone** (§7.0 (b)) — `to_regclass` check, raise,
   change nothing;
1. recreates `userrole` with its six labels, `role.role`, `role.allowed_menus`
   (`server_default '[]'`), `ix_role_tenant_role`, and `user.role`
   (`NOT NULL server_default 'GUEST'`);
2. renames `document_folder.allowed_role_ids_json` back to `allowed_roles_json`
   and restores `0010`'s `server_default`
   (`'["ADMINISTRATOR", "DIRECTOR", "MANAGER", "RESIDENT"]'`) on it. Nothing has
   touched the *contents* yet — the column still holds role ids at this point,
   and step 5 is what makes it hold role strings again. **Must precede step 5**,
   which writes to a column that does not exist under that name until now;
3. recomputes `role.role` by matching `role.name` against the frozen
   `LEGACY_ROLE_NAMES` literal embedded in the migration; a renamed row comes
   back with `role = NULL`, i.e. as an ordinary role. **Must precede steps 4
   and 5**: step 4 keys the precedence order on `role.role`, and the folder-ACL
   restore for post-`0033` folders maps ids back through `role.role` (§6);
4. **recomputes `user.role` from the POST-backfill memberships** — i.e. *before*
   the journal replay of step 5 removes them. `ADMINISTRATOR` if `is_superuser`
   (the flag survives `0033` untouched; §11.2's tenth persona is the fixture for
   this clause); otherwise the highest-precedence legacy role the user is a
   member of **in any tenant** — the column is global and memberships are per
   tenant, and inventing a per-tenant answer for a global column is not an
   option — under the fixed order
   `ADMINISTRATOR > DIRECTOR > MANAGER > PORTEIRO > RESIDENT > GUEST`; otherwise
   `GUEST` (least privilege, chosen over the model's `DIRECTOR` default on
   purpose).

   **Why this must run before step 5, not after.** §7.2 step 2 is precisely the
   step that turned the *implicit* role-linked membership into a row: before
   `0033` an ordinary `DIRECTOR` had **no** `user_role_link` row at all, because
   `get_effective_user_type_ids` computed the membership from
   `select(Role).where(Role.role == user.role)`. So the link to `Diretor (papel)`
   is backfill-created for the whole ordinary population, and it is journaled.
   Reading memberships *after* the replay would see an empty set for every one of
   them and write `GUEST` — demoting every non-superuser
   `DIRECTOR`/`MANAGER`/`RESIDENT`/`PORTEIRO` in the install on the rollback
   path. Read *before* the replay, every pre-`0033` user is linked to the legacy
   row of exactly their own enum value (§7.2 step 2 links strictly per the enum,
   and §7.0 (a) has already refused every user whose *pre-existing* explicit link
   pointed at a different legacy row), so the precedence order returns the value
   they had. Non-legacy rows have `role IS NULL` and contribute nothing to the
   order. **Every user that existed before `0033` therefore comes back with the
   role they had — the link-less ordinary majority as well as the handful who
   carried an explicit link.** Users created after `0033` get the precedence
   answer over whatever memberships they have; a user with no legacy membership
   at all gets `GUEST`;
5. **replays the journal by descending `id`, then drops it.** Descending `id` is
   the only total order available across the three `kind`s and is the exact
   inverse of the write order, which matters because the `folder_acl` and
   `role_permissions` restores are not commutative with a row that was rewritten
   more than once. Each `folder_acl` row restores
   `document_folder.allowed_roles_json` (renamed back in step 2) to its
   pre-`0033` bytes; each `user_role_link` row `DELETE`s the link `0033` created,
   so **backfill-created links go and pre-existing links stay**; each
   `role_permissions` row restores that role's `permissions` to its pre-backfill
   value, so **the backfilled bundles are emptied** without discarding
   permissions an operator had granted a legacy row through F4's UI before the
   migration. Rows created *after* `0033` have no journal entry and take the
   fallbacks of §6 and step 3. Finally `DROP TABLE f5_backfill_journal`;
6. `role.allowed_menus` comes back `[]` for every row — **the pre-drop values
   are not recoverable**, deliberately not journaled (§7.0 (b)), and that is now
   the *whole* of the loss;
7. `role.landing_path` is dropped.

"Reversível" in ER-2 therefore means: `alembic downgrade -1` runs clean; the
schema is identical to the pre-`0033` schema (including
`document_folder.allowed_roles_json` and its `0010` `server_default`);
`f5_backfill_journal` is gone; every folder ACL, every pre-existing role bundle
and every pre-existing link is **byte-identical to pre-`0033`**; every
pre-existing user comes back with the role they had, whether or not they ever had
an explicit link; and `allowed_menus` is `[]` everywhere. Pinned by
`test_0033_downgrade_restores_the_schema_and_recomputes_roles` and
`test_0033_document_folder_acl_round_trips` (§12.1).

**The downgrade test's role fixtures are named, because the bug this ordering
fixes is invisible to a fixture that only carries explicit links.**
`test_0033_downgrade_restores_the_schema_and_recomputes_roles` seeds and asserts
at minimum:

| Persona at `0031` | Pre-`0033` links | Reads back after `downgrade -1` |
|---|---|---|
| an **ordinary** `DIRECTOR` (§11.2 persona 2) | **none** — the membership is implicit | `DIRECTOR` |
| an ordinary `MANAGER`, `RESIDENT`, `PORTEIRO`, `GUEST` | none | their own value |
| a `MANAGER` with a **pre-existing** explicit link to `Gerente (papel)` (§11.2 persona 8) | one, pre-existing | `MANAGER`, **and the link is still there** |
| a superuser (§11.2 persona 10) | any | `ADMINISTRATOR`, by the `is_superuser` clause |
| a user created **after** `0033` with one legacy membership | n/a | that role's value, by precedence |

and, for the whole population, that no user reads back as `GUEST` who was not a
`GUEST` before.

### 7.6 The recorded legacy bundle (`tests/data/legacy_role_bundles.json`)

Generated **before** `LEGACY_ROLE_PERMISSIONS` is deleted, by
`tests/tools/record_legacy_bundles.py` (a sibling of F2's
`record_parity_baseline.py`), and committed with a `_meta` block carrying
`merge_base_sha`, `generator` and a `regenerate` command, exactly like the
parity baseline. Shape: `{"_meta": {...}, "bundles": {"<ROLE>": ["<perm>", …]}}`,
six keys, sorted.

It is the **only** surviving statement of what the enum used to mean, and it is
what lets three otherwise-impossible tests exist after the map is deleted:
`0033`'s literal is correct (§12.1), the migration's effect on effective
permissions is exactly `pre ∪ NEW_TIER` (§11.2), and the matrix's six profiles
are the legacy ones (§11.1).

---

## 8. Schemas, serialisation and the escalation surface

### 8.1 `RoleRead` after the drop

`{id, name, permissions, landing_path, tenant_id?}` — `allowed_menus` and
`role` are gone. `RoleCreate` / `RoleUpdate` gain `landing_path: str | None`
(validated against a small allowlist of in-app paths: `/dashboard`, `/gate`,
`/welcome`, `/announcements`, `/occurrences` — an open string would be an
open redirect the moment `RootRedirect` consumes it, and that is a security
property, not a nicety).

### 8.2 The three (four) `role` serialisation fields

`UserSummaryRead` (`schemas/lot.py`), `TenantMemberRead` (`schemas/tenant.py`)
and `ResidentUserRead` (`schemas/resident.py`) each carry `role: UserRole`.
All three become **`roles: list[str]`** — the user's role names in the acting
tenant, sorted. One shape, one i18n treatment (join with `", "`), no new
nested model. `UserRead.role` is deleted; `UserRead.roles` is the renamed
`user_types`.

### 8.3 `PATCH /api/v1/users/{user_id}` — the last escalation hole closes

`UserUpdate` loses `role`. The three F3-era escalation rules become two
(§3.3 #2 deletes the first), and the **only** way to widen a target's
permissions becomes `role_ids`, which F2's `assert_can_assign_roles` already
guards. APRAS-46 §12.5 recorded this as inherited by F5; it is discharged
here, and pinned by
`test_permission_escalation.py::test_a_tenant_admin_cannot_widen_a_user_beyond_their_own_set`.

`UserBase.role` and its `UserRole.DIRECTOR` default go; `/auth/signup` stops
forcing `GUEST` and creates the user with **zero roles** and
`is_active = False` — the same practical result (no permissions until an
administrator acts), now expressed once instead of twice.

`UserMeRead` gains **`is_superuser: bool`** — the caller's own flag, on the
caller's own record. F3 §8 deferred the question and F4 §2.4 deleted
`useAdminCapability` without needing it; §10.4 names the one remaining consumer
(`resolveActingTenantId`, which runs before an acting tenant exists and so
cannot use `/permissions/me`). `UserRead` still does **not** carry it: exposing
who the superusers are to every authenticated caller of `GET /users/` is a leak,
and F3's reasoning stands — which is also why §8.4 ships no UI.

### 8.4 `PATCH /api/v1/users/{user_id}/superuser` — where the grant *and the revoke* live

`UserUpdate` losing `role` also strands F3 §7.3's role-change mirror (§3.3 #5),
and with it the only API way to **revoke** `is_superuser`. Deleting both would
leave a demoted administrator holding the entire catalogue in every tenant with
SQL as the only cure — a privilege-retention hole, created by the slice whose
headline is that it creates none. So the mirror is replaced by an explicit
route.

* **Route.** `PATCH /api/v1/users/{user_id}/superuser`, in
  `app/api/v1/endpoints/users.py`. Body: `SuperuserUpdate {is_superuser: bool}`
  (a new one-field schema in `app/schemas/user.py`, so the flag never rides on
  `UserUpdate` again). Response model is this route's own
  **`SuperuserRead {id, email, is_superuser}`** — deliberately not `UserRead`,
  so `UserRead` keeps *not* carrying the flag (§8.3) while the caller still gets
  a confirmation of what it just wrote.
* **Guard.** `Depends(api_deps.get_current_superuser)` — F3's dependency,
  unchanged. Not a catalogue permission, not grantable to a role, not reachable
  by a tenant admin. 403 detail is F3's verbatim
  `"The user doesn't have enough privileges"`.
* **The one refusal.** A request that sets `is_superuser = false` is refused
  with **400** and detail `"The last superuser cannot be demoted"` when it would
  leave **zero** active superusers, i.e. when
  `SELECT count(*) FROM "user" WHERE is_superuser AND is_active` would become 0.
  The rule is stated over the whole table rather than over `user_id == me`, so
  it subsumes self-demotion *and* the equally fatal case of one superuser
  demoting the only other one. It is the exact mirror
  of §7.3's post-condition guard — "never leave the install with no way in" —
  now enforced online instead of at migration time.
* **Idempotence.** Setting the flag to the value it already holds is a 200
  no-op and never trips the refusal (the count does not change).
* **404** for an unknown `user_id`, unchanged from the sibling routes.

**Route accounting — the constants this moves, counted from the F4 merge base.**
The route is guarded by `get_current_superuser`, not by `require_permission`, so
it maps to **no catalogue permission** and goes into **`UNGUARDED_ROUTES`** with
the comment `# superuser-only, guarded by deps.get_current_superuser`. It is the
**only** entry this slice adds, and the **only** route this slice adds:

| Constant | Landed tree (`aa8953d`, pre-F4) | **F4 merge base** (APRAS-48 §3.3) | **After F5** |
|---|---|---|---|
| `len(UNGUARDED_ROUTES)` | 10 | **12** | **13** |
| total routes | 190 | **192** | **193** |
| `len(ROUTE_PERMISSIONS)` | 180 | **180** | **180** — unchanged |
| `len(PERMISSIONS)` | 156 | 156 | **159** (§3.0) |

§0 makes `APRAS-48` a precondition, and APRAS-48 §3.3 adds **two** unguarded
entries (`GET /api/v1/permissions/`, `GET /api/v1/permissions/me`), renaming
`test_unguarded_allowlist_is_ten_routes` → `..._is_twelve_routes` and recording
the post-F4 tree as **192/180/12**. The pre-F4 numbers `10`/`190` are therefore
**not** the base this slice starts from and appear nowhere in F5's code; they are
in the table only so the arithmetic is checkable.

**The invariant, which outranks the constants.** What this slice guarantees is
`len(UNGUARDED_ROUTES) == <F4 merge base> + 1` and
`total routes == <F4 merge base> + 1`, with `len(ROUTE_PERMISSIONS)` unchanged.
The predicted constants are **13** and **193**. If the merge base has moved by
the time F5 lands — a sixth slice, a hotfix, a route added in review — the
implementer re-measures at the actual merge base, lands base + 1, and **quotes
both the measured base and the final value in the PR body** next to the numbers
this spec predicts. `ROUTE_PERMISSIONS` staying at 180 is the part that must hold
unconditionally, because it is what keeps the parity matrix at `6 × 180 = 1080`
cells and `tests/data/parity_matrix_baseline.json` byte-identical (§11.1, ER-6).

Three test sites hard-code the allowlist length and all three move in the same
commit (§12.2): `test_permission_registry.py` (three literals plus the
`192/180/12` docstring APRAS-48 leaves there),
`test_permission_parity_matrix.py::test_the_twelve_unguarded_routes_are_the_only_ones_excluded`
(the name APRAS-48 renames it to → `..._thirteen_...`, and its
`assert len(UNGUARDED_ROUTES) == 12`), and `tests/matrix_world.py`'s module
docstring at ~l.15, which needs **a wording change and not only a number**: the
superuser route *does* make an authorization decision, it simply does not make a
**role-dimension, catalogue-permission** one, which is the property that
justifies excluding it from the matrix.

**Tenant-route classification (`tests/test_tenant_route_scope.py`).** That module
asserts every route either depends transitively on `deps.get_current_tenant` or
sits in `GLOBAL_ROUTES` (18 entries at the landed tree; APRAS-48 §3.3 keeps it at
18). The new route lives in `app/api/v1/endpoints/users.py`, and
`api.py` mounts that router with `dependencies=TENANT_SCOPED`, so the route
inherits `get_current_tenant` **at mount time** and is classified **scoped**
automatically: `GLOBAL_ROUTES` stays **18** and that module needs no edit.

That is deliberate, and it is the opposite call from APRAS-43's
`PATCH /tenants/{tenant_id}/members/{user_id}`, so the difference is recorded:
APRAS-43 is global because `is_tenant_admin` is a *per-tenant* capability and
making the route global means "on a route with no acting tenant the capability is
not even readable, so a tenant admin cannot grant it to themselves". Here the
capability is `is_superuser`, a **global** flag that only a superuser can write;
there is no self-grant to prevent by hiding the acting tenant, and moving the
route out of the `users` router purely to reach `GLOBAL_SCOPED` would cost a new
router and a new mount for one handler. The practical consequence is stated so it
is not discovered in a 400: **the caller must send the tenant header**, like
every other `/api/v1/users/*` route; the acting tenant plays no part in the
decision or in what is written. Pinned by
`test_superuser_grant.py::test_the_superuser_route_is_tenant_scoped_like_the_rest_of_the_users_router`
(the route is **not** in `GLOBAL_ROUTES`, `len(GLOBAL_ROUTES)` is unchanged, and
a call without the header behaves exactly as `PATCH /users/{user_id}` does).

This is deliberately *not* F3's `SUPERUSER_ONLY_PERMISSIONS` pattern. That set
exists to contain five **pre-existing** `ROUTE_PERMISSIONS` entries F3 inherited
on superuser-guarded routes and chose not to remove; its entire job is to make
`assert_can_grant` refuse permissions that do nothing. Minting a *new* catalogue
string whose only purpose is to be refused by the grant path — and paying six
new baseline cells for it — would be the wrong trade. If the implementer finds
that F3 landed the opposite convention, follow F3 (§0's "by role, not by name"),
record the deviation, and expect the baseline to move by exactly six cells with
the diff quoted.

**Tests — `tests/test_superuser_grant.py`:**

| Case | Assertion |
|---|---|
| `a superuser can grant is_superuser` | 200; the target's flag is true; `/permissions/me` for the target returns the whole catalogue |
| `a superuser can revoke is_superuser` | 200; flag false; the target's `/permissions/me` falls back to their roles' union |
| `a tenant admin cannot call the route` | 403, F3's detail |
| `an ordinary user cannot call the route` | 403 |
| `an unauthenticated caller cannot call the route` | 401 |
| `the last active superuser cannot demote themselves` | 400, `"The last superuser cannot be demoted"`; the flag is unchanged in the database |
| `the last active superuser cannot be demoted by anyone` | same, with a second superuser as the caller and the target being the only *active* one |
| `a superuser may demote themselves while another active superuser exists` | 200; the caller's subsequent calls 403 |
| `setting the flag to its current value is a no-op` | 200, no state change, no refusal even for the last superuser |
| `the route is unguarded by permission and superuser-guarded` | `("PATCH", "/api/v1/users/{user_id}/superuser") in UNGUARDED_ROUTES` and `not in ROUTE_PERMISSIONS`; the handler's dependency is `get_current_superuser`; `len(UNGUARDED_ROUTES)` is the F4 merge base + 1 (**13** as predicted) while `len(ROUTE_PERMISSIONS) == 180` |
| `the superuser route is tenant scoped like the rest of the users router` | the route is **not** in `test_tenant_route_scope.GLOBAL_ROUTES`, `len(GLOBAL_ROUTES)` is unchanged (**18**), and it depends transitively on `deps.get_current_tenant` through the router mount |
| `UserRead still does not expose is_superuser` | the `GET /users/` payload has no `is_superuser` key (§8.3) |

`tests/test_permission_escalation.py` gains one case:
`test_a_tenant_admin_cannot_grant_is_superuser_by_any_route` — the tenant admin
tries `PATCH /users/{id}` with an `is_superuser` key (ignored: not a
`UserUpdate` field), then `PATCH /users/{id}/superuser` (403).

**Not in scope:** any frontend surface for this route. `UserRead` does not carry
the flag, so the users table cannot render it, and inventing a superuser column
would undo §8.3's leak decision. `AGENTS.md` §13 documents the route with a
`curl` next to the SQL it replaces.

### 8.5 The fourth behaviour delta: the self-guard grows to cover `role_ids`

§3.3 #3 re-expresses the self-guard on `role_ids`. Today the guard covers only
`UserUpdate.role`: an administrator may freely change **their own**
`user_type_ids` and is blocked only from changing their own `role`. After F5 the
same guard blocks self-changes to `role_ids`, which is where all authority now
lives.

It is a **narrowing**, and it is intended: the guard's whole purpose is "you may
not edit your own authority", and `role_ids` is the only thing left that edits
it. It is named here rather than discovered later because §1 promises every
delta is enumerated. Pinned by
`test_user_admin.py::test_an_administrator_cannot_change_their_own_role_ids`
(400, detail `"Administrators cannot change their own roles"`) and
`…::test_an_administrator_can_still_change_another_users_role_ids` (200), and
the delta is quoted in the PR body next to §4.2's and §10.5's.

---

## 9. `app/seed.py`, the demo profiles, and the nexdom runbook

### 9.1 The rewrite

`seed.py` currently constructs four users with `role=UserRole.X` and relies on
the role-implicit membership for their permissions. After F5 a user's power is
**only** its role memberships, so the seed must create them.

* `TRUNCATE` list gains `user_role_link` (it already truncates `user_type`,
  which is now `role`).
* Create the six legacy roles for the default tenant via
  `TenantService.ensure_legacy_roles` **first**, and set their `permissions`
  from `tests/data/legacy_role_bundles.json`… **no**: `app/` must not read a
  test fixture. The seed instead sets the three demo roles' bundles from a
  small literal in `seed.py` itself, documented as "the dev demo's opinion,
  not a product default" (F1's no-seeds decision binds `ensure_legacy_roles`
  and the migrations, not the dev seed script).
* Three profiles (ER-4), equivalent to today's:

  | Email | Role memberships | Extra |
  |---|---|---|
  | `admin@apras.com` | `Administrador (papel)` | `is_superuser=True` |
  | `diretor1@apras.com` | `Diretor (papel)` + `Diretor Comercial` | — |
  | `gerente1@apras.com` | `Gerente (papel)` + `Gerente Operacional` | — |

  `diretor2@apras.com` stays as a second director so the task fixtures keep
  two assignees; "3 perfis" in ER-4 means three *profiles*, not three users.
* Every seeded user still gets an explicit `UserTenantLink` to the default
  tenant (unchanged).
* `python -m app.seed` prints the per-profile role list, so the operator can
  see the model at a glance.

### 9.2 `ensure_legacy_roles`

`TenantService.ensure_role_types` keys its idempotency on the `role` column,
which is gone. It becomes `ensure_legacy_roles`, keyed on **name** against the
`LEGACY_ROLE_NAMES` literal (which moves from a `dict[UserRole, str]` to a
plain `tuple[str, ...]` of the six names).

**Its docstring is rewritten, not renamed.** Today it explains the retired model
in prose — "*a non-`ADMINISTRATOR` member has an empty effective-UserType set
and is 403'd by `assert_menu_access` on every gated menu*" — a sentence that
survives every grep in §2.2 and ER-6 (it names neither `UserRole` nor
`allowed_menus` nor `MenuKey`) and would read as current. The replacement says
what the method now does: it inserts the six historically-named rows a tenant is
missing, with `permissions = []`, and grants nobody anything. Same for the
module docstring of `app/services/tenant_service.py` if it repeats the claim.
The method still inserts with
`permissions = []` — F1's no-seeds decision is unchanged and
`test_effective_permissions.py::test_a_fresh_tenant_has_no_role_with_permissions`
keeps passing with `allowed_menus` removed from its assertions.

### 9.3 The nexdom runbook (goes into `AGENTS.md`, §13)

```bash
# 1. back up first — 0033 is not byte-reversible (§7.5)
pg_dump -h localhost -p 5436 -U postgres nexdom > /tmp/nexdom-pre-f5.sql

# 2. migrate
cd backend && POSTGRES_URL=postgresql://postgres:postgres@localhost:5436/nexdom \
  .venv/bin/alembic upgrade head

# 3. if the guard refuses, it prints the emails; fix and re-run:
#    UPDATE "user" SET is_superuser = true WHERE email = '...';
#    or INSERT INTO user_tenant_link (user_id, tenant_id) VALUES (...);

# 4. full reset instead (destroys demo data):
cd backend && .venv/bin/python -m app.seed
```

The single nexdom administrator carries `is_superuser = true` from `0031`, so
the guard passes on the first run; the PR body quotes the actual run
(`alembic upgrade head` output plus the post-migration
`SELECT email, count(l.role_id) FROM "user" …` listing).

**`tests/test_migrations_postgres.py` still wipes whatever `TEST_POSTGRES_URL`
points at** (`DROP SCHEMA public CASCADE`, F1 §7.5). Point it at a throwaway
container, not at 5436, and reseed if you do not:

```bash
docker run -d --rm -p 55432:5432 -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=apras_test postgres:16-alpine
cd backend && TEST_POSTGRES_URL=postgresql://postgres:postgres@localhost:55432/apras_test \
  SECRET_KEY=test .venv/bin/python -m pytest tests/test_migrations_postgres.py -q
```

---

## 10. Frontend: the death of `UserRole`

### 10.1 The grep that defines done

```
grep -rn "UserRole" frontend/src
```

**No output.** Today bare `UserRole` matches **30** non-test files and **45**
test files. F4's ER-2 speaks about a *different, narrower* grep —
`grep -rln "UserRole\." frontend/src | grep -v __tests__`, which matches **24**
today and which F4 reduces to **22**. The two numbers are not comparable and the
contract here is the bare grep: 30 non-test files today, **0** after this slice.
§1 item 7's "all 30 non-test files" is the same 30.
`export const UserRole` and `export type UserRole` are deleted from
`src/types/auth.ts`; `User.role` goes with them.

### 10.2 The 14 feature components — the exact permission for each

Every replacement below was chosen because its legacy holder set (read from
`_LEGACY_ROLES_BY_PERMISSION`, measured today) **equals** the role set the
comparison expressed. All read the *effective* (simulation-aware) set through
F4's `useEffectivePermissionSet()`, because every one of them is display-level
element visibility.

| File | Today | Permission | Legacy set |
|---|---|---|---|
| `announcement-feed/AnnouncementCard.tsx` | `isPublisher` A\|D | `announcements:create` | AD ✓ |
| `announcement-feed/AnnouncementFeedPage.tsx` | `isPublisher` A\|D | `announcements:create` | AD ✓ |
| `announcement-feed/CommentThread.tsx` | `isPublisher` A\|D | `announcements:create` | AD ✓ |
| `announcement-feed/CommentThread.tsx` | `isGuest` G | `!has("announcements:comment")` | ✗ **{G, P}** — see §10.5 (a) |
| `assembly-voting/AssemblyVotingPage.tsx` | `isBoard` A\|D | `assemblies:create` | AD ✓ |
| `assembly-voting/AssemblyVotingPage.tsx` | `canCreatePoll` A\|D\|M | `votes:create` | ADM ✓ |
| `assembly-voting/LotVotingAdminPanel.tsx` | `isBoard` A\|D | `assemblies:create` | AD ✓ |
| `asset-management/AssetsInventoryPage.tsx` | A\|D | `assets:create` | AD ✓ |
| `feedback-management/FeedbackChannelPage.tsx` | `isManagement` A\|D | `feedback:respond` | AD ✓ |
| `lot-management/LotsPage.tsx` | `canWrite` A\|D / `canDelete` A | `lots:update` / `lots:delete` | AD ✓ / A ✓ |
| `purchase-management/PurchaseRequestDetailModal.tsx` | A\|D | `purchases:decide` | AD ✓ |
| `purchase-management/PurchaseRequestsPage.tsx` | A\|D | `purchases:decide` | AD ✓ |
| `space-reservation-management/ReservableSpacesPage.tsx` | `canWrite` A\|D | `spaces:update` | AD ✓ |
| `space-reservation-management/SpaceBookingPage.tsx` | `isGuest` G / `isStaff` A\|D | `!has("reservations:create")` / `reservations:approve` | G ✓ / AD ✓ |
| `task-management/CategoriesPage.tsx` | `canWrite` A\|D | `categories:create` | AD ✓ |
| `task-management/TaskForm.tsx` | `role !== MANAGER` (the `visible_to` editor) | `tasks:read_all` | ✗ **excludes G** — see §10.5 (b) |
| `task-management/utils/simulatedPermissions.ts` | GUEST / MANAGER task visibility & edit | `tasks:read`, `tasks:read_all`, `tasks:update`, `tasks:update_any` | exact mirror of §3.1 sites 1–2 |
| `user-administration/Navbar.tsx` | `role === ADMINISTRATOR` gating `<SimulationControls/>` | `roles:update` | A ✓ |
| `hooks/useUsers.ts` | `useAssignableUsers` excludes ADMINISTRATORs | exclusion **dropped** | ✗ — see §10.5 (c) |
| `context/tenantState.ts` | `role === ADMINISTRATOR` keeps a stored tenant id | `user.is_superuser` from `/auth/me` (§8.3, §10.4) | ✓ exact |
| `components/SimulationControls.tsx` | a hard-coded `SIMULATABLE_ROLES` array | the rows from `useRoles()` | ✓ (strictly more) |
| `App.tsx` `RootRedirect` | 3-way role switch | `landing_path` (§10.4) | ✓ exact |
| `components/ProtectedRoute.tsx` | F4's two `landingRedirect` role comparisons | `landing_path` (§10.4) | ✓ exact |
| `pages/AdminUserDashboard.tsx` | F4's read-only "Cargo (legado)" column | **column removed** | n/a |

### 10.3 Simulation, after the enum

`SimulationContext`'s `simulatedRole` field is deleted; `simulatedUserTypeIds`
becomes `simulatedRoleIds`. `useEffectiveIdentity` returns `{roleIds}` only.
`SimulationBanner`'s `simulation.bannerLabel` loses its `{{role}}`
interpolation and becomes `"Visualizando como: {{roles}}"` (the role names,
joined).

F4 preserved APRAS-35's real-vs-simulated split verbatim and kept
`useEffectiveIdentity.test.tsx` untouched as proof. **That file is rewritten
here** — honestly, and this is the last slice where a "byte-identical" claim is
made about it. The *invariant* is preserved and re-pinned:
`ProtectedRoute.permissions.test.tsx::keeps route access on the real permission
set while simulating` (F4 §8.1) must keep passing unchanged, and it is the
mechanical statement that authorization still reads the real set.

### 10.4 `role.landing_path` — why the landings must become data

Today (F4 §2.4) `/dashboard` and `/categories` redirect a GUEST to `/welcome`
and a PORTEIRO to `/gate`, on the **effective** role. F4 recorded these as
role-shaped and un-expressible in permissions, and it was right: a PORTEIRO
holds `tasks:read` and `gate:checkin`, and so do A/D/M, so no predicate over
the catalogue separates "pin the gatekeeper to the gate" from "the board can
also open the gate". Landing is a **preference**, not authorization.

So it becomes data on the role row (§7.2 step 4), read back through
`GET /api/v1/permissions/me`, whose F4 body `{tenant_id, permissions[]}` gains
`landing_path: str | null` = the first non-null `landing_path` among the
caller's roles in the acting tenant, ordered by role name for determinism.

* `RootRedirect` navigates to `landing_path ?? "/dashboard"`.
* `ProtectedRoute`, on a route whose `AccessRule` carries `landingRedirect`,
  navigates to `landing_path` when it is non-null and not the current path.
* Backfilled to `/gate` and `/welcome` for exactly the two legacy rows, so
  `RootRedirect.test.tsx`, `ProtectedRoute.guestWelcome.test.tsx` and
  `ProtectedRoute.porteiroGate.test.tsx` keep asserting the same navigations
  with role-shaped fixtures replaced by `landing_path` fixtures.
* It is operator-editable in the role editor, which is the feature the old
  hard-coded switch never had.

**Multi-role users, and simulation.** "First non-null, ordered by role name" is
total and deterministic, but it is only *identical* to the old enum switch for
users with one landing-carrying role. A user holding both `Administrador
(papel)` and `Porteiro (papel)` lands on `/gate`, where the enum switch (keyed
on the single `user.role`) sent them to `/dashboard`. That is a deliberate,
defensible answer — the gatekeeper role is the one that carries an opinion about
where to land — and §10.2's "✓ exact" for `RootRedirect` / `ProtectedRoute`
should be read as *exact for single-role users*. Pinned by
`test_landing_path.py::test_a_user_with_two_landing_carrying_roles_gets_the_first_by_name`
and `RootRedirect.test.tsx::lands a multi-role user on the first landing_path by
role name`.

`landing_path` follows the **effective** (simulation-aware) identity, because
`/permissions/me` is already the effective-set endpoint (F4) and landing is a
preference, not authorization: simulating a porteiro should show you the
porteiro's landing. This is the one place where a simulated value drives
navigation, and it is safe precisely because §10.3's invariant keeps *route
access* on the real set. Pinned by
`ProtectedRoute.permissions.test.tsx` (F4's invariant, unchanged) plus
`test_landing_path.py::test_permissions_me_landing_path_follows_the_simulated_roles`.

### 10.5 The three frontend deltas, each with its own test

(a) **`CommentThread`'s comment box.** `isGuest` hid it from GUEST only;
`!has("announcements:comment")` also hides it from PORTEIRO. `announcements:comment`
is legacy `{A,D,M,R}`, so the **backend already 403s a PORTEIRO's comment**:
this removes a UI that promised something the API refuses. Pinned by
`CommentThread.test.tsx::hides the comment box from a user without announcements:comment`.

(b) **`TaskForm`'s `visible_to` editor.** `role !== MANAGER` also showed it to
GUEST; `tasks:read_all` does not. A GUEST holds no `tasks:create`/`tasks:update`
and cannot reach the form at all, so the state is unreachable. Recorded, not
tested.

(c) **`useAssignableUsers`.** The admin exclusion is dropped, because after F5
the frontend cannot know who is an administrator without leaking `is_superuser`
on `UserRead` (§8.3) — and being assignable a task is not a privilege. An
administrator with at least one role now appears in the assignee dropdown; the
`u.roles?.length > 0` clause is kept. Pinned by
`useUsers.test.ts::includes a superuser with roles in the assignable list`.

---

## 11. The parity story ends here

### 11.1 The matrix survives, re-keyed on **profiles**, with the golden file byte-identical

The 1080-cell matrix is `6 × 180`: six `UserRole` values × 180 mapped routes.
With the enum gone the six keys stop naming an enum and start naming **the six
legacy profiles** — a user whose only role membership is the correspondingly
named legacy row, carrying the backfilled bundle.

* `matrix_world.py`: `CELLS` is built from a new module constant
  `PARITY_PROFILES: tuple[str, ...]` = **the six `UserRole` *value* strings,
  verbatim** — `("ADMINISTRATOR", "DIRECTOR", "GUEST", "MANAGER", "PORTEIRO",
  "RESIDENT")`, in the same sorted order the file uses today. Verbatim is not a
  style point: the baseline's top-level keys *are* those strings, so
  byte-identity depends on them surviving the enum's death unchanged while the
  actor behind each becomes a role membership. `PARITY_PROFILES` is what the
  enum leaves behind in the test tree, and nothing else. `_seed_world` builds each actor as a user with
  **zero** enum, `roles=[legacy_role_row]`, and — for the `ADMINISTRATOR`
  profile only — `is_superuser=True` (F3 already routed every A decision
  through the flag). The `menu_type` actor role disappears with the gate; the
  spare non-role type stays as what `{role_id}` binds to. Its **module
  docstring** (~l.15) also moves: post-F4 it says "the twelve `UNGUARDED_ROUTES`
  are excluded because none of them makes a role-dimension authorization
  decision", and F5 makes it **thirteen** *and* re-words the justification —
  §8.4's route very much makes an authorization decision, it just does not make a
  **role-dimension, catalogue-permission** one, which is the property that
  earns exclusion from the matrix (§8.4).
* The legacy rows' `permissions` are set from
  `tests/data/legacy_role_bundles.json` ∪ `NEW_TIER`, i.e. from the same
  recorded artefact `0033` is checked against — **not** from a second literal.
* `tests/data/parity_matrix_baseline.json` is **not modified**:
  `git diff --stat -- backend/tests/data/parity_matrix_baseline.json` is empty
  after this slice. The four renamed paths are handled by a declared literal in
  the test, not by re-recording:

  ```python
  # tests/test_permission_parity_matrix.py
  F5_PATH_RENAMES = {
      "/api/v1/user-types/": "/api/v1/roles/",
      "/api/v1/user-types/{user_type_id}": "/api/v1/roles/{role_id}",
  }
  ```

  applied to the baseline's keys before comparison. There are **4**
  `(method, path)` entries in total across those two path strings
  (`GET`/`POST` on the collection, `PATCH`/`DELETE` on the item), so
  `4 × 6 profiles = ` **24** cells are re-keyed, values untouched. Leaving the golden file untouched, with its
  `_meta.merge_base_sha = 02c2025…`, is the strongest available evidence: the
  1080 answers recorded before a single guard was converted are still the 1080
  answers after the enum is gone.
* `_meta.cell_count` stays 1080. §8.4's new route does **not** move it: it goes
  into `UNGUARDED_ROUTES`, and the matrix is `6 × len(ROUTE_PERMISSIONS)`. If F4
  or a later slice adds a `ROUTE_PERMISSIONS` entry, the baseline moves for
  **that** reason and the PR body says so, quoting the diff.

### 11.2 The migration-level pin (the one the board's ER-3 is really asking for)

`tests/test_migrations_postgres.py::test_effective_permissions_are_unchanged_by_0033`:

1. at `0031`, seed **ten** users:

   | # | Persona | `is_superuser` |
   |---|---|---|
   | 1–6 | one per legacy role — `ADMINISTRATOR`, `DIRECTOR`, `MANAGER`, `PORTEIRO`, `RESIDENT`, `GUEST` — with **no explicit link** (the ordinary, implicit-membership shape) | **false** |
   | 7 | carries an extra **non-legacy** role with `permissions = ["finance:read"]` | **false** |
   | 8 | explicitly linked to the legacy row that **matches** its own enum (a MANAGER in `Gerente (papel)`) | **false** |
   | 9 | explicitly linked to a legacy row of a **second** tenant that also matches its enum | **false** |
   | 10 | a **superuser** (`ADMINISTRATOR` enum, flag set) — the fixture §7.5 step 4 and ER-2 refer to | **true** |

   Personas 8 and 9 exist because §7.0 (a) lets exactly those two shapes through
   and §7.2 step 2 must skip rather than duplicate them. Personas 1–6 are the
   *link-less* majority, and they are also the personas §7.5's downgrade test
   reuses.

   **`is_superuser` is set explicitly on all ten, and nine of them get `false`.**
   This is not boilerplate: `0031` (F3 §3.2) runs
   `UPDATE "user" SET is_superuser = true WHERE role = 'ADMINISTRATOR'` and F3's
   `User.__init__` defaults the flag the same way, so an `ADMINISTRATOR` seeded
   "around `0031`" is genuinely ambiguous, and F3 added a superuser
   **short-circuit** to `get_effective_permissions`. The fixture therefore writes
   the flag with explicit SQL *after* `0031` has run, and the test asserts the
   seeded values before it upgrades;

2. compute `pre` for each from `legacy_role_bundles.json` ∪ their explicit
   roles' bundles — which, for users 7–9, is what the code computes today
   because the legacy rows carry `permissions = []` before the migration;
3. `alembic upgrade head`;
4. open a `Session` on the migrated database, enter
   `acting_tenant_scope(session, DEFAULT_TENANT_ID)`, call
   `deps.get_effective_permissions` for each user;
5. assert, **exactly**:
   * for personas **1–9** (flag `false`), `post == pre | NEW_TIER[legacy_role]`.
     For persona 1 that is the 155-string `ADMINISTRATOR` bundle ∪
     `{tasks:read_all, tasks:update_any}` = **157** strings — deliberately *not*
     the whole catalogue, because with the flag unset the equality measures the
     **bundle** path, which is the one `0033` is responsible for;
   * for persona **10** (flag `true`), `post == set(PERMISSIONS)` — the whole
     **159**-string catalogue, by F3's short-circuit, which is a different
     statement from `pre | NEW_TIER` (it also carries `packages:my_lots_read`,
     absent from the legacy `ADMINISTRATOR` bundle, and
     `occurrences:read_assigned`). Asserting it here is what keeps ER-3's
     "exactly" true of every user the test names, and it is the same fixture
     §7.5 step 4's `ADMINISTRATOR if is_superuser` clause and ER-2's "a superuser
     reads back as `ADMINISTRATOR`" are checked against;
   * persona 8 has exactly **one** `user_role_link` row to `Gerente (papel)`
     (the backfill skipped, not duplicated).

The explicitly-linked-to-a-*different*-legacy-row case is not in this list
because `0033` **refuses** it (§7.0 (a)); it is covered instead by
`test_0033_refuses_a_user_explicitly_linked_to_a_foreign_legacy_role`, which
seeds a MANAGER linked to `Diretor (papel)`, runs `alembic upgrade head`,
asserts it fails with that user's **email and the role name** in the message and
that **nothing was written** (`role.permissions` still `[]`, no
`f5_backfill_journal` table, `user.role` still present), then drops the link and
asserts the re-run succeeds and that user's post-migration set equals
`pre | NEW_TIER["MANAGER"]`.

Together, these are the sentence the whole slice rests on: *after the migration,
every user's permissions come from data and equal what the code used to
compute — and any user for whom that would not hold stops the migration by
name.*

### 11.3 What retires

* `LEGACY_ROLE_PERMISSIONS`, `_LEGACY_ROLES_BY_PERMISSION` and
  `tests/test_legacy_role_permissions.py` — replaced by the recorded artefact
  (§7.6), which is generated from them one last time in the same PR.
* `ROLE_READS_COMPARE` / `ROLE_READS_NON_COMPARE` and the AST walkers in
  `tests/test_permission_enforcement.py`. **The walkers do not die** — they are
  retargeted: both mappings must now be **empty**, over `app/` *including*
  `app/models/`, `app/schemas/` and `app/seed.py` (F2's three exclusions are
  removed, since the reason for them — the enum — is gone).
  `test_role_read_arithmetic_closes` becomes
  `test_no_actor_role_read_survives`: `RULE_C_BASELINE - CONVERTED_COMPARE == 0`
  with `CONVERTED_COMPARE = 100`, `RULE_N_BASELINE - CONVERTED_NON_COMPARE == 0`
  with `CONVERTED_NON_COMPARE = 7`. The two historical baselines (`100`, `7`,
  measured at `02c2025`) **still do not change** — they were true statements
  about the F1 tree and remain so. The ledger closes at zero, which is the
  arithmetic ending of the chain.

---

## 12. Tests

### 12.1 New backend test modules

| File | Cases (names are the contract) |
|---|---|
| `tests/test_role_rename.py` | `the roles router is mounted at /api/v1/roles`; `no route path contains user-types`; `ROUTE_PERMISSIONS uses the roles module`; `the catalogue has 159 permissions in 26 modules`; `the three new tier permissions exist and are not route-mapped` |
| `tests/test_superuser_grant.py` | the twelve cases of §8.4, including the two registry cases (allowlist membership and the tenant-scope classification) |
| `tests/test_menu_gate_removal.py` | `assert_menu_access no longer exists`; `MenuKey no longer exists`; `a user without the legacy menu key now reaches tasks` (§4.2); `a user without tasks:read is still refused`; `no handler calls a menu gate` (AST walk of `app/api/v1/endpoints/`) |
| `tests/test_task_visibility_permissions.py` | `a user without tasks:read_all is scoped by visible_to on list`; `…on get`; `a user with tasks:read_all sees every task`; `a user without tasks:update_any cannot edit an other-assigned task`; `create defaults visible_to for a scoped author only`; `update rejects targets outside a scoped author's roles` |
| `tests/test_occurrence_visibility_permissions.py` | `occurrences:read_assigned adds assigned occurrences and nothing else`; `without it the tier is reporter-or-public`; `manage_all still short-circuits` |
| `tests/test_document_folder_acl.py` | `folder access intersects allowed_role_ids with the caller's roles`; `documents:folder_create still bypasses`; `a folder scoped to a non-legacy role admits its members`; `allowed_role_ids is required on create` |
| `tests/test_landing_path.py` | `permissions/me returns the first non-null landing_path`; `null when no role carries one`; `RoleCreate rejects a landing_path outside the allowlist`; `a user with two landing carrying roles gets the first by name` (§10.4); `permissions me landing path follows the simulated roles` (§10.4) |

### 12.2 Pre-existing test modules that legitimately change — by category, with exact lists

The byte-identical era ends here; this section is the honest enumeration the
dispatch asks for. Every count is **measured today** on the F2 working tree and
must be re-measured at F4's merge base; the PR body quotes both.

**Category 1 — mechanical rename only (`user_type` → `role`), no assertion
changes.** Produced by `grep -rl "user_type\|UserType\|user-types" backend/tests`
→ **23** modules today: `conftest.py`, `matrix_world.py`, `test_auth_me_tenants.py`,
`test_effective_permissions.py`, `test_guest_rbac.py`,
`test_legacy_role_permissions.py`, `test_menu_access.py`,
`test_migrations_postgres.py`, `test_permission_enforcement.py`,
`test_permission_escalation.py`, `test_permission_registry.py`,
`test_role_type_permissions.py`, `test_task_visible_to_multi_target.py`,
`test_tasks_coverage.py`, `test_tasks_rbac.py`, `test_tenant_admin.py`,
`test_tenant_isolation.py`, `test_tenant_models.py`,
`test_tenant_no_behaviour_change.py`, `test_user_contact_info.py`,
`test_user_directory_scope.py`, `test_user_types.py` (→ `test_roles.py`),
`test_permission_parity_matrix.py`.

**Category 2 — user construction moves from an enum to a role membership.**
`grep -rl "role=UserRole" backend/tests/*.py` → **36** modules today. To keep
this a one-line substitution per site rather than 36 bespoke rewrites,
`conftest.py` gains **one** helper:

```python
def make_user(session, *, profile: str, **kwargs) -> User:
    """A user whose only role is the legacy `profile` row of the default tenant."""
```

and every `User(..., role=UserRole.X, ...)` becomes
`make_user(session, profile="X", ...)`. The helper seeds the six legacy rows
with the recorded bundles on first use, from `legacy_role_bundles.json`.
`test_conftest_profiles.py::test_every_profile_grants_exactly_the_recorded_bundle`
pins the helper itself, so the 36 modules inherit one proof instead of 36.

**Category 3 — assertions genuinely change.**

| Module | What changes | What must **not** |
|---|---|---|
| `test_migrations_postgres.py` | the four `userrole`-enum cases (`…contains_resident`, `…contains_porteiro`, `…insert_with_porteiro`, `…insert_with_resident`) are **rewritten** to assert the type is **absent** at head and **present** after `downgrade -1`; `test_user_type_role_seeds_five_rows` becomes `test_legacy_roles_exist_in_every_tenant`; +8 new cases for `0032`/`0033` (rename round-trip; backfill; the **pre**-condition refuse-guard on a user linked to a foreign legacy row, §7.0 (a)/§11.2; the **post**-condition refuse-guard on a membership-less active user, §7.3; the drops; `test_0033_document_folder_acl_round_trips`, §6; `test_0033_downgrade_restores_the_schema_and_recomputes_roles` including the journal replay, the §7.5 persona table — an ordinary **link-less** `DIRECTOR` that reads back as `DIRECTOR`, the pre-existing-linked `MANAGER` whose link survives, and the superuser — and `f5_backfill_journal` being gone; the refusal when the journal has been dropped, §7.0 (b); and §11.2's **ten**-persona parity case) | every `0028`/`0029`/`0030`/`0031` case, verbatim |
| `test_menu_access.py` | **deleted** — its entire subject is `allowed_menus`. Its two genuinely-permission-shaped cases move to `test_menu_gate_removal.py` | — |
| `test_legacy_role_permissions.py` | **deleted**, after generating §7.6's artefact | — |
| `test_role_type_permissions.py` | rewritten as `test_role_permissions.py`: the role-implicit-membership cases become explicit-membership cases | the effective-set assertions themselves |
| `test_permission_enforcement.py` | both allowlists become empty; the walkers gain `app/models`, `app/schemas`, `app/seed.py`; §11.3's renamed arithmetic test | the walker implementations |
| `test_permission_registry.py` | catalogue size `156` → `159`, module `user_types` → `roles`, the four route keys, and — counted from the **F4 merge base**, not from the pre-F4 tree — `UNGUARDED_ROUTES` **12 → 13** and total routes **192 → 193** for §8.4's superuser route (three literals plus the `192/180/12` docstring APRAS-48 leaves at l.135–136; F4 also renamed the case to `..._is_twelve_routes`, which becomes `..._is_thirteen_routes`) | `ROUTE_PERMISSIONS`'s count (**180**) and every other unguarded entry |
| `test_permission_parity_matrix.py` | `F5_PATH_RENAMES` (§11.1), `PARITY_PROFILES` in place of `UserRole`, **and** the second hard-coded allowlist length: `assert len(UNGUARDED_ROUTES) == 12` → `== 13` inside `test_the_twelve_unguarded_routes_are_the_only_ones_excluded` → `test_the_thirteen_unguarded_routes_are_the_only_ones_excluded` (§8.4) | the byte-identical baseline file, `EXPECTED_CELL_COUNT == 1080` |
| `test_user_admin.py`, `test_user_directory_scope.py`, `test_permission_escalation.py` | the `role=` payload cases become `role_ids=` cases; §8.3's closed hole gains a case; §8.5's two self-guard cases; `test_a_tenant_admin_cannot_grant_is_superuser_by_any_route` (§8.4) | the 404-vs-403 visibility assertions |
| `test_porteiro_role.py`, `test_gatekeeper.py`, `test_guest_rbac.py` | construction only (Category 2) — F2 already converted their subjects to `gate:*` permissions | **every assertion**, verbatim. These three are the mechanical proof that the PORTEIRO gate world and the GUEST refusals survive the enum's death |
| `test_packages_rbac.py`, `test_residents_rbac.py`, `test_visitors_rbac.py`, `test_authorizations.py`, `test_lots_rbac.py` | construction only | **every assertion**, verbatim — the RESIDENT lot world is `UserLotLink`, not the enum, and this is where that is proven |
| `test_models.py`, `test_schemas.py` | the `role` field cases become `roles` / `role_ids` cases | the rest |

**Frontend.** The complete list is produced by
`grep -rl "UserRole\|user_type\|userType\|allowed_menus" frontend/src` — **90**
files today: **37** non-test (of which 2 are the locale JSONs) + **53** test.
The earlier "77 = 30 + 45 + 2" mixed the bare-`UserRole` counts (30 + 45 = 75)
with a guess at the other three terms; they add 15 files, not 2. The PR body
pastes the list.
Named individually because their *assertions* move, not only their fixtures:
`useEffectiveIdentity.test.tsx` (rewritten, §10.3), `useMenuAccess.test.tsx` +
`useMenuAccess.crossTenant.test.tsx` (**deleted**, §4.1),
`simulatedPermissions.test.ts` (rewritten on the four task permissions),
`CommentThread.test.tsx` (+1 case, §10.5 a), `useUsers.test.ts` (+1 case,
§10.5 c), `RootRedirect.test.tsx` / `ProtectedRoute.guestWelcome.test.tsx` /
`ProtectedRoute.porteiroGate.test.tsx` (fixtures move to `landing_path`,
navigations unchanged), `DocumentCenter.test.tsx` +
`api/__tests__/documents.test.ts` (folder ACL ids, §6),
`AdminUserDashboard.test.tsx` (the "Cargo (legado)" column case is deleted),
`i18n/__tests__/parity.test.ts` (must keep passing across the whole namespace
rename — it is what proves pt and en moved together).

---

## 13. `AGENTS.md`

Three sections are **wrong** after this slice and must be rewritten, not
patched: **UserRole (RBAC)** (the four-tier table), **UserType**, and the
`allowed_menus` sentences inside **Tenant** and **User**. The endpoint table
row `/api/v1/user-types` becomes `/api/v1/roles` and `/api/v1/permissions` is
added (F4). The replacement describes what exists:

* **Permissions are in code** — `app/core/permissions.py`, 159 strings in 26
  modules, `<module>:<action>`; `ROUTE_PERMISSIONS` maps 180 routes,
  `UNGUARDED_ROUTES` the rest; a route with neither fails
  `test_permission_registry.py`.
* **Roles are data** — one `role` row per tenant, a name, a flat `permissions`
  list, an optional `landing_path`. No nesting, no per-user permissions. Six
  rows per tenant carry the pre-F5 bundles because migration `0033` put them
  there; they are **ordinary, editable, deletable roles** — there are no system
  roles and nothing is seeded with permissions by any migration or by
  `ensure_legacy_roles`. Deleting `Diretor (papel)` strips every director, and
  that is the operator's prerogative.
* **`is_superuser`** — a global flag on `user`, granting the whole catalogue in
  every tenant. It has exactly **one** API surface,
  `PATCH /api/v1/users/{user_id}/superuser` with body `{"is_superuser": bool}`,
  callable only by a superuser and refusing any revoke that would leave zero
  active superusers (§8.4); there is **no UI** for it, because `UserRead`
  deliberately does not expose who the superusers are. Documented with a `curl`
  next to the `UPDATE "user" SET is_superuser = …` it replaces.
  `is_tenant_admin` is the same power inside one tenant (APRAS-43), granted by
  `PATCH /tenants/{id}/members/{user_id}`.
* **Object and visibility rules are permissions too** — `tasks:read_all`,
  `tasks:update_any`, `occurrences:read_assigned`, `occurrences:manage_all`,
  `gate:checkin`, `visitors:manage_any_lot`, `residents:read_any_lot`,
  `packages:my_lots_read` — plus the two things that were never roles:
  `UserLotLink` per-lot narrowing and per-object ownership.
* **What is gone** — `UserRole`, `allowed_menus`, the menu gate,
  `LEGACY_ROLE_PERMISSIONS`, and the doctrine of "role-linked types that cannot
  be deleted or renamed". The word "user type" no longer names anything.
* **Migrating an existing install** — §9.3's runbook and §7.5's reversibility
  contract, verbatim, plus §7.0's two refusals: `0033` stops **before writing**
  if any user is explicitly linked to a legacy role row that is not their enum
  role (printing the users and the two remediations), and stops **after the
  backfill, before the drops** if any active user would be left with no way in.
* **`f5_backfill_journal`** — the table `0033` leaves at head so its downgrade
  can restore role bundles, backfill-created links and folder ACLs exactly. It
  is dropped by `alembic downgrade -1`. It is **required** by that downgrade,
  not merely helpful: with the table missing, `alembic downgrade -1` refuses by
  name (`RuntimeError: f5_backfill_journal is missing; …`) and changes nothing,
  so `DROP TABLE f5_backfill_journal` is a **one-way door** — safe only once the
  operator is certain they will never downgrade past `0033` (§7.0 (b), §7.5
  step 0). The table has **no SQLModel model** and is invisible to
  `Base.metadata`, so `alembic revision --autogenerate` at head would propose
  dropping it; no workflow here runs autogenerate (every migration in
  `alembic/versions/` is hand-written), and this line exists so that stays a
  known fact rather than a lost rollback.

No sentence may describe the old model as current. Pinned by
`tests/test_docs_agents_md.py::test_agents_md_does_not_describe_the_retired_model`,
a grep over `AGENTS.md` for `UserRole`, `allowed_menus`, `user_type`,
`UserType` and `menu gate` that permits them **only** inside the section headed
`### What is gone` and the runbook block.

---

## 14. Gates, baselines and the PR body

| Metric | Gate | Requirement |
|---|---|---|
| `pytest` (backend) | `--cov-fail-under=90` | green, ≥ 90 |
| `npm run test` | — | all pass; the file/test count moves and the PR body says by how much |
| Vitest statements / branches / functions / lines | 80 / 76 / 78 / 80 | ≥ gate, and **≥ the F4 merge-base measurement** for each |
| `npm run lint` | — | **≤ the F4 merge-base problem count**, and **0** new findings in non-test `src/**` |
| `npm run build` | — | passes |
| `ruff check backend` | — | **0** new findings |
| `alembic heads` | — | exactly one: `0033_drop_user_role_and_menus` |
| `len(UNGUARDED_ROUTES)` | pinned | **F4 merge base + 1** — predicted **13** (the base is **12** after APRAS-48 §3.3, not the pre-F4 10); §8.4's superuser route is the only entry added |
| total routes | pinned | **F4 merge base + 1** — predicted **193** (base **192**) |
| `len(ROUTE_PERMISSIONS)` | pinned | **180**, unchanged — which is what keeps the parity baseline byte-identical |

F4's spec measured the frontend at its own merge base (1066 tests; statements
87.66 %, branches 79.93 %, functions 83.38 %, lines 88.59 %; 467 lint problems).
Those are **F3-tip** numbers; re-measure at F4's tip and quote baseline vs.
final for every row.

**The PR body must carry:** the three §2.2 greps' (empty) output; the §10.1
grep's (empty) output; `git diff --stat -- backend/tests/data/parity_matrix_baseline.json`
(empty); the `alembic heads` output; the real `alembic upgrade head` run against
5436/nexdom with **both** refuse-guards' outcomes (§7.0 (a)'s query returning 0
rows, and §7.3's) and the post-migration membership listing; the
`pg_constraint` listing proving `0032` left no `user_type`-named constraint; the
§4.2 widening delta; the §8.5 narrowing delta; the three §10.5 deltas; the
`UNGUARDED_ROUTES` 12 → 13 and total-routes 192 → 193 movement from §8.4 — with
the **measured** F4 merge-base values quoted next to the predicted ones, so the
`base + 1` invariant is checkable if the base moved — next to the unchanged
`len(ROUTE_PERMISSIONS) == 180` and the unchanged `len(GLOBAL_ROUTES) == 18`; the before/after for every gate
row; and any name deviation from F2/F3/F4 (§0).

---

## Expected Results

- [ ] **ER-1 — the entity is `role` in the API, the UI and the database, and
      `user_type` is gone.** `/api/v1/roles` serves list/create/patch/delete
      with `{role_id}` path params and `RoleRead {id, name, permissions,
      landing_path}`; the frontend administers them at `/admin/roles` and
      `/admin/roles/:roleId` with pt "Papel/Papéis" and en "Role/Roles"; tables
      `role`, `user_role_link(role_id)` and `task_visible_to_link.role_id`
      exist in Postgres after `alembic upgrade head`; `alembic downgrade -1`
      from `0032` restores every old name. From the repository root,
      `grep -rn "user_type\|UserType\|user-types\|userType" backend/app frontend/src`
      returns **no output**, and `backend/tests/test_role_rename.py` passes.
- [ ] **ER-2 — `user.role`, `user_type.role`, `allowed_menus` and the
      `userrole` type are dropped by a reversible migration, applied to a real
      Postgres, and `alembic heads` reports one head.** After
      `alembic upgrade head` on the throwaway database:
      `SELECT column_name FROM information_schema.columns WHERE table_name='user'`
      contains no `role`; the same query on `role` contains neither `role` nor
      `allowed_menus`; `SELECT 1 FROM pg_type WHERE typname='userrole'` returns
      no row; `alembic heads` prints exactly `0033_drop_user_role_and_menus`.
      After `alembic downgrade -1`, all three columns and the six-label
      `userrole` type are back; `document_folder`'s column is named
      `allowed_roles_json` again and carries `0010`'s `server_default`; the six
      legacy rows' `permissions` are back to their pre-`0033` values; every link
      `0033` created is gone while every pre-existing link remains; and
      `SELECT to_regclass('f5_backfill_journal')` returns NULL.
      **Roles read back for the link-less majority, not only for the linked
      few** — over the §7.5 fixture personas: an **ordinary, pre-`0033`,
      link-less** `DIRECTOR` (no `user_role_link` row before the migration, the
      membership having been implicit) reads back as `DIRECTOR`; a `MANAGER` with
      a **pre-existing** explicit link to `Gerente (papel)` reads back as
      `MANAGER` **and keeps that link**; a link-less `RESIDENT`, `PORTEIRO` and
      `GUEST` read back as themselves; §11.2's persona 10 (`is_superuser = true`)
      reads back as `ADMINISTRATOR`; and no user reads back as `GUEST` who was
      not a `GUEST` before.
      The document-folder ACL round-trips: `document_folder` is renamed to
      `allowed_role_ids_json` holding **role ids** after `alembic upgrade head`
      (`SELECT allowed_role_ids_json FROM document_folder` parses as a JSON list
      of ids that exist in `role`, of that folder's tenant), and the
      `(folder, allowed roles)` pairs read pre-`0033`, mapped-back post-`0033`
      and read post-`downgrade -1` are **identical**.
      `tests/test_migrations_postgres.py` passes with `TEST_POSTGRES_URL` set
      (and skips wholesale without it), including
      `test_0033_downgrade_restores_the_schema_and_recomputes_roles` and
      `test_0033_document_folder_acl_round_trips`; and
      `tests/test_document_folder_acl.py` passes.
- [ ] **ER-3 — the migration refuses by name in both directions — no user
      widened, no user locked out — and when it runs clean, permissions are
      unchanged and the legacy map is gone.**
      `test_migrations_postgres.py::test_0033_refuses_a_user_explicitly_linked_to_a_foreign_legacy_role`
      seeds a legacy MANAGER with an explicit link to `Diretor (papel)`, runs
      `alembic upgrade head`, and asserts it fails with that user's **email and
      the role name in the error message** and that **nothing was written**
      (the legacy rows' `permissions` are still `[]`,
      `to_regclass('f5_backfill_journal')` is NULL, `user.role` still exists);
      with the link removed it succeeds.
      `test_0033_refuses_when_an_active_user_has_no_role_and_no_flag`
      seeds an active, non-superuser, non-tenant-admin user with no
      `user_tenant_link`, runs `alembic upgrade head`, and asserts it fails with
      that user's **email in the error message**; with the membership restored
      it succeeds.
      `test_effective_permissions_are_unchanged_by_0033` asserts that for the
      **ten** seeded users of §11.2 — one per legacy role (link-less), one with
      an extra non-legacy role, one explicitly linked to the legacy row matching
      its own enum, one so linked in a second tenant, all nine seeded
      `is_superuser = false`, plus a tenth persona seeded
      `is_superuser = true` — `get_effective_permissions` after the migration
      equals, **exactly**: for the nine, the recorded pre-migration bundle union
      `{tasks:read_all, tasks:update_any, occurrences:read_assigned}` restricted
      to that role (157 strings for the `ADMINISTRATOR` persona); and for the
      tenth, the **whole 159-string catalogue** via the superuser short-circuit.
      It also asserts the backfill created no duplicate `user_role_link` row.
      `grep -rn "LEGACY_ROLE_PERMISSIONS\|_LEGACY_ROLES_BY_PERMISSION" backend/app`
      returns no output.
- [ ] **ER-4 — seed, signup and dev-login work on the new model, and the demo
      comes up with three working profiles.** `python -m app.seed` against a
      migrated database exits 0 and creates `admin@apras.com` (`is_superuser`,
      member of `Administrador (papel)`), `diretor1@apras.com` (`Diretor
      (papel)` + `Diretor Comercial`) and `gerente1@apras.com` (`Gerente
      (papel)` + `Gerente Operacional`), each with a default-tenant membership
      and **no** role column in sight; `POST /api/v1/auth/dev-login` for each of
      the three returns 200 and the token's `/api/v1/permissions/me` returns the
      profile's bundle; `POST /api/v1/auth/signup` creates an inactive user with
      **zero** roles and an empty permission set.
      `tests/test_seed.py::test_the_three_demo_profiles_have_the_recorded_bundles`
      passes.
- [ ] **ER-5 — `AGENTS.md` describes the model that exists and no longer
      presents the old one as current.** It documents: permissions in code
      (159 strings, 26 modules, `ROUTE_PERMISSIONS` / `UNGUARDED_ROUTES`);
      roles as data (one flat `permissions` list per row, no nesting, no
      per-user permissions, no system roles, nothing seeded with permissions);
      `is_superuser`, its one API surface
      `PATCH /api/v1/users/{user_id}/superuser` and its relationship to
      `is_tenant_admin`; the object-level permissions that replaced the role
      tiers; the `f5_backfill_journal` table and when it is safe to drop; both
      of `0033`'s refusals; a `### What is gone` section; and the
      migrate/restore runbook of §9.3.
      `tests/test_docs_agents_md.py::test_agents_md_does_not_describe_the_retired_model`
      passes: `UserRole`, `allowed_menus`, `user_type`, `UserType` and
      "menu gate" appear in `AGENTS.md` only inside `### What is gone` or the
      runbook block.
- [ ] **ER-6 — every gate is green, the isolation and parity proofs hold, and
      the enum is grep-clean.** `pytest` passes at ≥ 90 % backend coverage;
      `npm run test`, `npm run build` and `npm run lint` pass with each Vitest
      threshold ≥ its gate **and** ≥ the F4 merge-base measurement, and no new
      non-test lint finding; `ruff check backend` adds no finding.
      `tests/test_permission_parity_matrix.py` passes with
      `backend/tests/data/parity_matrix_baseline.json` **byte-identical**
      (`git diff --stat` on that path is empty), the four route paths re-keyed
      only through the declared `F5_PATH_RENAMES` literal.
      `tests/test_tenant_isolation.py`, `test_porteiro_role.py`,
      `test_gatekeeper.py`, `test_packages_rbac.py`, `test_residents_rbac.py`,
      `test_visitors_rbac.py` and `test_authorizations.py` pass with **their
      assertions unchanged** (construction-only edits).
      `tests/test_permission_enforcement.py::test_no_actor_role_read_survives`
      asserts both allowlists are empty over all of `app/`.
      `grep -rn "UserRole\|allowed_menus\|MenuKey" backend/app frontend/src`
      returns **no output**.
- [ ] **ER-7 — `is_superuser` keeps a grant *and* a revoke path, superuser-only,
      and the last superuser cannot be demoted.**
      `PATCH /api/v1/users/{user_id}/superuser` with body `{"is_superuser": true|false}`
      returns **200** and `{id, email, is_superuser}` for a superuser caller and
      flips the target's flag in the database; returns **403** (detail
      `"The user doesn't have enough privileges"`) for a tenant admin and for an
      ordinary user, and **401** unauthenticated; returns **400** with detail
      `"The last superuser cannot be demoted"` — leaving the flag unchanged —
      when the revoke would leave zero active superusers, including when the
      caller is demoting themselves.
      `("PATCH", "/api/v1/users/{user_id}/superuser")` is in
      `UNGUARDED_ROUTES` and **not** in `ROUTE_PERMISSIONS`. It is the only route
      and the only allowlist entry this slice adds, so — counted **from the
      APRAS-48 merge base, which is 192 routes / 180 mapped / 12 unguarded per
      APRAS-48 §3.3, not the pre-F4 190/180/10** —
      `len(UNGUARDED_ROUTES) == merge base + 1 == 13` and
      total routes `== merge base + 1 == 193`, while
      `len(ROUTE_PERMISSIONS) == 180` is unchanged and the parity baseline stays
      byte-identical (ER-6). If the merge base has moved when F5 lands, the
      `base + 1` invariant and the unchanged 180 are what must hold, and the PR
      body quotes the measured base next to the predicted 13/193.
      The route is classified **tenant-scoped** — it is mounted inside the
      `users` router, which carries `Depends(get_current_tenant)` — so it is
      **not** in `tests/test_tenant_route_scope.GLOBAL_ROUTES` and
      `len(GLOBAL_ROUTES) == 18` is unchanged.
      `UserUpdate` has no `role` and no `is_superuser` field, and
      `GET /api/v1/users/` payloads carry no `is_superuser` key.
      `tests/test_superuser_grant.py` passes with all twelve cases of §8.4, and
      `tests/test_permission_escalation.py::test_a_tenant_admin_cannot_grant_is_superuser_by_any_route`
      passes.
