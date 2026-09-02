# APRAS-48 — IAM F4: permission-group UI and permission-driven frontend gating

Slice 4 of the IAM chain (F1 `APRAS-45` → F2 `APRAS-46` → F3 `APRAS-47` →
**F4 this** → F5 `APRAS-49`).

F1 built the vocabulary (156 permissions, 26 modules). F2 swapped enforcement
onto it. F3 made `is_superuser` / `is_tenant_admin` mean "the whole
catalogue". **All three are backend-only: `git status --short -- frontend/`
is empty at F3's tip.** This slice is the frontend counterpart — the screens
that author permission groups, and the menus and routes that obey them —
plus the smallest possible additive backend surface that lets the browser
learn two things it cannot compute: *what permissions exist* and *which ones
I hold in the tenant I am acting in*.

---

## 0. Preconditions, and how to read this spec against a moving tree

**Contracts, not files.** APRAS-46 is being implemented concurrently in this
worktree and APRAS-47 is approved but unimplemented. This spec is written
against:

1. **F1's landed code** at `02c2025` — `app/core/permissions.py`
   (`PERMISSIONS` = 152 strings there, `ROUTE_PERMISSIONS`,
   `UNGUARDED_ROUTES` = 10, `module_of`, `permission_for_route`),
   `deps.get_effective_permissions`, `deps.get_effective_user_type_ids`,
   migration `0030_add_user_type_permissions`.
2. **F2's approved spec** `docs/tasks/APRAS-46-spec.md` — post-conditions
   used here as preconditions: `deps.has_permission` /
   `deps.require_permission`; `SCOPE_PERMISSIONS` (4) folded into
   `PERMISSIONS`, making the catalogue **156**; `permissions` on
   `UserTypeCreate` / `UserTypeUpdate` (`list[str] | None`, `None` = leave
   unchanged) / `UserTypeRead`; `user_type_service.assert_can_grant` and
   `assert_can_assign_user_types` wired on `POST /user-types/`,
   `PATCH /user-types/{id}` and the `user_type_ids` path of
   `PATCH /users/{id}`; the parity matrix (`tests/data/parity_matrix_baseline.json`,
   1080 cells = 180 mapped routes × 6 roles, `_meta.merge_base_sha = 02c2025`).
3. **F3's approved spec** `docs/tasks/APRAS-47-spec.md` — `user.is_superuser`
   (migration `0031`); `get_effective_permissions` returning the whole
   `PERMISSIONS` for a superuser and for an `is_tenant_admin` **in the
   granting tenant only**; `SUPERUSER_ONLY_PERMISSIONS` (the four
   `tenants:*` administration strings) rejected by `assert_can_grant`;
   `UserRead` **not** carrying `is_superuser`; `/auth/me` unchanged;
   `user.role` and `UserType.allowed_menus` still alive.

**Dependency.** `APRAS-47` must be merged first. Every measured number below
is measured **at F3's merge commit**, in a clean worktree, and quoted in the
PR body next to the number this spec predicts. Where this spec quotes a
number it measured *today* (F3 touches no frontend file, so the frontend
figures are already final) it says so.

**If a name landed differently** in F2/F3 — a renamed constant, a test in a
different module — apply the edit **by role, not by name**, and record the
deviation in the PR body. Every edit below is described by what it does.

---

## 1. Scope

**In scope**

1. Two new read-only backend routes — `GET /api/v1/permissions/` (the
   catalogue) and `GET /api/v1/permissions/me` (my effective permissions in
   the acting tenant) — plus their schemas, their two `UNGUARDED_ROUTES`
   entries and their tests (§3).
2. A single frontend access model: `AccessRule`, the `ROUTE_ACCESS` table,
   `useCanAccess` (authorization) / `useCanShowMenu` (display), consumed by
   `ProtectedRoute` and `Navbar` respectively, so a menu and its route are
   written from **one** rule and can disagree only during an active
   simulation, by design (§2.7, §4, §5).
3. `Navbar` and `App.tsx` re-gated on permissions; `ProtectedRoute`'s
   `requiredRole` / `requiredRoles` / `requiredCapability` / `requiredMenu`
   props replaced by one `requiredAccess` prop (§5).
4. The groups administration area: `/admin/groups` and
   `/admin/groups/:groupId` — list, create, clone, delete, per-module
   permission checkboxes, and membership editing **from the group side**;
   the existing user-edit modal keeps membership editing **from the user
   side** (§6).
5. `AdminUserDashboard`: the role `<Select>` removed, the inline user-type
   section replaced by a link to `/admin/groups`, the user-type checkbox list
   relabelled "Grupos" (§7).
6. Simulation ("view-as") re-expressed over permissions (§8).
7. i18n for 26 module names + 84 action names, pt/en, with a mechanical
   parity test (§9).

**Explicitly NOT in scope**

* **No migration.** `0031` is F3's; `alembic heads` still reports
  `0031_add_user_is_superuser` after this slice.
* **No change to `deps.py`**, to `get_effective_permissions`, to any guard,
  to `ROUTE_PERMISSIONS`, or to any existing route's authorization. This
  slice adds two routes and changes **zero** authorization outcomes on the
  180 mapped ones. The parity baseline stays **byte-identical** (§3.4).
* **No `/auth/me` change** and no new field on `UserRead` / `UserMeRead`
  (§2.1 says why, and why that does not weaken ER-2).
* **No removal of `user.role`, `UserType.allowed_menus`, `Task.visible_to`,
  `LEGACY_ROLE_PERMISSIONS` or `deps.assert_menu_access`.** F5 owns all of
  them. This slice names every surviving consumer (§2.3, §11).
* **No `is_superuser` grant UI** — F3 deliberately shipped no grant surface,
  and inventing one here would be a new privilege path in a frontend slice.
* **No per-user loose permissions and no role nesting** — the board's
  standing decisions. A user's permissions come from their groups (plus the
  transitional legacy-role bundle the backend still unions in).
* **No pagination or search redesign of `GET /users/`** (§6.4).

---

## 2. The eight open design questions, decided

### 2.1 Where the effective permissions come from — **not** `/auth/me`

The board's ER-2 says "`/auth/me` devolve as permissões efetivas do tenant
ativo". The intent — *the frontend has the acting tenant's effective
permissions from the API* — is honoured; the endpoint is not, and here is
why, in the exact terms of the code that exists:

* `GET /api/v1/auth/me` is on the **global** allowlist
  (`GLOBAL_ROUTES`, 18 entries in `tests/test_tenant_route_scope.py`;
  `("GET", "/api/v1/auth/me")` in `UNGUARDED_ROUTES`). Global scope means
  `tenant_context.acting_tenant_id(session)` is `None`, and
  `get_effective_user_type_ids` then falls back to `DEFAULT_TENANT_ID`.
  Computing permissions there would answer **the default tenant's** groups
  to a user acting in tenant B — silently wrong, and wrong in the direction
  of granting.
* Making `/auth/me` tenant-scoped is worse: `_resolve_without_header`
  answers **400 "X-Tenant-Id header is required"** to a multi-membership
  user who sends no header, and on a cold load the frontend *has* no header
  yet — `AuthContext.fetchUser` calls `/auth/me` **first** and only then
  runs `resolveActingTenantId` over the `tenants[]` it returns
  (`AuthContext.tsx`, `tenantState.resolveActingTenantId`). Scoping
  `/auth/me` bricks the bootstrap of exactly the users APRAS-38 exists for.
* Reading the header *leniently* inside the global handler would create a
  second, softer tenant-resolution ladder next to APRAS-42's strict one —
  two sources of truth for "which tenant am I in", the failure mode the
  whole tenant work was built to avoid.
* The Axios interceptor already attaches `X-Tenant-Id` to **every** request
  (`api/client.ts`), so a *scoped* route needs no plumbing at all: the
  acting tenant resolves through `get_current_tenant`, with the same errors
  and the same ladder as `/user-types/`.

**Decision.** `GET /api/v1/permissions/me`, mounted on a **tenant-scoped**
router, returns `{tenant_id, permissions[]}` for the acting tenant. The
frontend fetches it with TanStack Query under the key `["me","permissions"]`,
gated by `useActingTenantReady()` exactly as `useUserTypes` is. Re-resolution
on a tenant switch is then free and already tested machinery:
`TenantContext.setActingTenant` writes the mirror **first** and then
`resetQueries`/`removeQueries` every key whose `[0] !== "tenants"` — so the
permissions query is evicted and refetched under the new header, with no
reload (ER-3).

`/auth/me` keeps returning `tenants[]` and nothing new. ER-2 is restated in
§13 as "the API returns the effective permissions of the acting tenant",
naming the route.

### 2.2 What replaces `useMenuAccess`'s `allowed_menus` consultation

`hasModulePermission(module)` — `some(p => p.startsWith(module + ":"))` over
the set from `/permissions/me`. The permission-string prefix **is** the
module key; there is no second `MENU_KEYS` vocabulary and no mapping table
from menu key to module. `MenuKey` (`"tasks" | "categories"`) survives only
in the two places §2.3 names.

`allowed_menus` **stays in the backend** (column, schema field,
`deps.assert_menu_access`) until F5. The frontend stops consulting it for
**24 of the 26 modules** — see the one deliberate exception next.

### 2.3 The one place `allowed_menus` is still read — and why

`deps.assert_menu_access` is **still enforced** at F3's tip on 12 route
handlers: `app/api/v1/endpoints/tasks.py` (8 call sites) and
`app/api/v1/endpoints/categories.py` (4). F2 did not convert it; F5 will.

So for the two modules `tasks` and `categories`, and **only** those two, a
purely permission-derived menu would be a *broken* gate: `categories:read`
is `ALL_ROLES` in `LEGACY_ROLE_PERMISSIONS`, so every user would see
"Categorias" and every user whose groups lack the `categories` menu key
would be answered 403 by the backend on arrival. That is not "gating by
permission", it is showing a door that does not open.

**Decision.** `ROUTE_ACCESS` carries an optional `legacyMenu` field, set on
exactly **two** entries (`/dashboard` → `"tasks"`, `/categories` →
`"categories"`). `useCanAccess` ANDs `useMenuAccess(rule.legacyMenu)` when it
is present. `useMenuAccess.ts` is kept **unchanged** apart from a docstring
marking it `TRANSITIONAL (IAM F4 -> F5)` and naming
`deps.assert_menu_access` as the reason it survives; its two test files
(`useMenuAccess.test.tsx`, `useMenuAccess.crossTenant.test.tsx`) are kept
unchanged too.

Two mitigations make this cheap and self-healing:

1. The group editor **derives** `allowed_menus` from the selected
   permissions on every save — `tasks` iff the bundle contains any `tasks:*`,
   `categories` iff it contains any `categories:*` — and shows no menu
   checkboxes at all. A group authored or edited in the new UI therefore
   gains the menu its permissions imply, without a second checkbox to keep in
   sync (§6.3).

   **The derivation is additive, never subtractive**, and this is a
   correctness requirement, not a nicety. §7 deletes the only UI that can
   write `allowed_menus`, so if the save sent the derived list *verbatim*, a
   pre-existing group carrying `allowed_menus: ["tasks"]` and no `tasks:*`
   permission — the state of **every** operator-configured group today, since
   F1 seeds nothing — would silently lose backend menu access
   (`deps.assert_menu_access`, 12 handlers, §2.3) the first time anyone
   renamed it. That is the exact hazard §6.3 already protects *permissions*
   against. The payload is therefore
   `allowed_menus = sort(unique([...storedAllowedMenus, ...derived]))`:
   revoking a menu key is impossible from this UI until F5 deletes the column.
   Accepted consequence, stated so it is not rediscovered as a bug: a group
   whose `tasks:*` permissions are all unchecked keeps its `tasks` menu key,
   so the *backend* still admits it to the 12 menu-gated handlers. The
   *frontend* does not show the link, because `useCanAccess` ANDs the module
   rule with the menu rule (§4.3) — the shown door still opens, which is the
   invariant this exception exists to protect. Role-linked rows seed
   `allowed_menus = []` (migration `0018`), so the blast radius of the whole
   question is operator-configured groups only.
2. Deleting the exception in F5 is: remove the `legacyMenu` field from the
   two `ROUTE_ACCESS` entries and its three lines in `useCanAccess`, delete
   `useMenuAccess.ts` and its two test files. §11 records this as the F4→F5
   hand-off.

**This is a deliberate deviation from the dispatch note's "the frontend just
stops consulting it".** It is stated here so it can be overruled in one
edit: dropping the exception makes the two menus purely permission-derived
and hands the 403 to §6.5's friendly-error path.

### 2.4 What replaces `requiredRoles` / `requiredCapability` per route

One table, §5.2, covering all **23** protected routes (`grep -c "<ProtectedRoute"
src/App.tsx` → 23; plus 4 public routes and `/`) and the two new ones.
`requiredCapability="admin"` disappears entirely: under F3 an
`is_tenant_admin` of the acting tenant and an `is_superuser` both hold the
**whole catalogue**, so any permission rule they should pass, they pass.
`useAdminCapability.ts` (both hooks) and its test file are deleted; the
capability keeps being read from `/auth/me`'s `tenants[]` by
`TenantContext.isActingTenantAdmin`, which stays for the switcher.

The GUEST → `/welcome` and PORTEIRO → `/gate` redirects are **landing**
rules, not authorization: a PORTEIRO genuinely holds `tasks:read` in
`LEGACY_ROLE_PERMISSIONS`, so no permission predicate can express "pin the
gatekeeper to the gate". They stay role-shaped, on exactly the two routes
that have them today (`/dashboard`, `/categories` — the routes
`RootRedirect` can land on), expressed as a `landingRedirect: true` flag in
those two `ROUTE_ACCESS` entries and a `TRANSITIONAL (IAM F4 -> F5)` comment.
`RootRedirect` in `App.tsx` is unchanged. `RootRedirect.test.tsx`,
`ProtectedRoute.guestWelcome.test.tsx` and
`ProtectedRoute.porteiroGate.test.tsx` keep asserting the same behaviour.

**Denial is in place, not by redirect.** Today a `requiredRoles` failure
`Navigate`s to `/dashboard` while a `requiredMenu` failure renders
`RestrictedAccessMessage`. Unified: a `requiredAccess` failure renders
`RestrictedAccessMessage` and does not navigate. This removes a real
redirect-loop hazard (a user without `tasks:read` bounced to `/dashboard`,
which denies them too) and makes every route's denial assertable by the same
query, `getByText("Acesso restrito")`.

### 2.5 The user form and `user.role`

`UserBase.role` already has a default (`UserRole.DIRECTOR`) and
`UserUpdate.role` is already `| None`; there is **no** `POST /users/` at all
(user creation is `/auth/signup`, which forces `GUEST` and never reads a
role from the body). So "the form stops asking for cargo" needs **zero
backend change**: the frontend simply stops sending the field.

**Decision.** The role `<Select>` in `AdminUserDashboard` is **removed**
(the write surface is gone); the role is still **displayed**, read-only, in
a column headed `admin.colRoleLegacy` ("Cargo (legado)"), so an operator can
still diagnose a legacy bundle during the transition. No collapsed "legacy
role" editor: keeping a role writer would keep people granting power by role
in the one slice whose purpose is to prove groups can do it. The consequence
is stated in the PR body: **until F5, a role cannot be changed from the UI;
a new signup stays `GUEST` and is made functional by adding them to groups**
— which is exactly the workflow F1's justification asks to exercise
("os padrões serão criados sob demanda testando as telas").

### 2.6 The groups screens, and where membership comes from

Routes, components and hooks in §6. Endpoints: all four already exist
(`GET/POST /user-types/`, `PATCH`/`DELETE /user-types/{id}`) and carry
`permissions` after F2. **Clone** is `POST /user-types/` with the source
group's `permissions` (and derived `allowed_menus`) and an editable
pre-filled name — no new endpoint, and `assert_can_grant` applies to the
clone exactly as to a hand-built bundle.

**Members are a client-side join**, not a new endpoint: `GET /users/` is
already tenant-scoped, already returns `user_types[]` on every row, and is
already fetched by the admin area (`useUsers`, key `["users","ALL"]`).
Adding `GET /user-types/{id}/members` would be a second source of truth for
the same join plus a new route to guard, matrix-classify and test. Adding or
removing a member is `PATCH /users/{id}` with the recomputed
`user_type_ids` — the same call the user-side modal makes, so both
directions hit one mutation and one invalidation. Scale caveat, recorded
rather than solved: `GET /users/` is unpaginated today; if a tenant's
directory outgrows one response, a server-side `?user_type_id=` filter is a
later slice.

### 2.7 Simulation — authorization reads the **real** set, display reads the simulated one

APRAS-35 wrote the invariant into `useEffectiveIdentity.ts`'s docstring
(l.30–37) and this slice **preserves it verbatim**:

> "Route guards (`ProtectedRoute`) intentionally do NOT use this hook for
> requiredRole/requiredRoles checks — those must always reflect the real
> user's access so the admin can never get locked out of ending a simulation.
> The one exception is `requiredMenu` checks (via `useMenuAccess`), which
> intentionally DO use simulated identity…"

**Decision.** There are two permission sets, not one, and each consumer is
named:

| Set | Hook | Content while simulating | Consumers |
|---|---|---|---|
| **real** (non-simulated) | `usePermissionSet()` | the real user's `/permissions/me` payload, unchanged by the simulation | `useCanAccess` → `ProtectedRoute` (**every** authorization branch) |
| **effective** (simulated) | `useEffectivePermissionSet()` | union of the `permissions` arrays of the simulated `userTypeIds`, read from `useUserTypes()` (F2 put `permissions` on `UserTypeRead`) | `useCanShowMenu` → `Navbar`; `useMenuAccess` (unchanged); `RootRedirect`/landing redirects, via `useEffectiveIdentity().role` |

So the mapping onto today's code is one-to-one: what `requiredRoles` /
`requiredCapability` did with the real identity, `useCanAccess` does with the
real permission set; what `requiredMenu` and the GUEST/PORTEIRO landing
redirects did with `useEffectiveIdentity`, `useCanShowMenu` and the unchanged
`useMenuAccess` do with the effective one. **The documented exception stays
the exception**, including its legacy leg: `useCanAccess`'s `legacyMenu` AND
is `useMenuAccess(rule.legacyMenu)`, which is simulation-aware today and stays
so (§4.3) — this slice moves no behaviour there in either direction.

`useEffectiveIdentity.ts` itself is touched for **one docstring sentence
only** (§4.3), naming `requiredAccess` as the successor of
`requiredRole`/`requiredRoles` so the rule keeps referring to props that
exist. No line of its code changes; its test file is untouched.

**What this costs, and why it is the right cost.** A menu and its route now
*can* disagree — but only during an active simulation, and only in the
generous direction: the administrator sees the simulated user's menu and
still reaches the page. The alternative (simulating authorization too) locks
a simulating administrator out of essentially every gated page, because
`LEGACY_ROLE_PERMISSIONS` is **not** simulatable — it lives only in the
backend, so a simulated `DIRECTOR`'s set is whatever `DIRECTOR`'s *groups*
grant, which is empty until someone fills them. `SimulationBanner` being
outside `<Routes>` guarantees the *exit* is reachable; it does not make being
locked out of every page a usable operator tool. Outside a simulation the two
sets are identical by construction, so §5.2's single `ROUTE_ACCESS` table
remains the one place a rule is written for both.

`SimulationBanner` gains one sentence
(`simulation.permissionsPreviewNote`) saying that the preview shows the
simulated groups' menus and that the administrator's own route access is
unaffected. Pinned by
`ProtectedRoute.permissions.test.tsx::keeps route access on the real
permission set while simulating` (§8.1).

### 2.8 i18n for 156 labels

**Composition, not 156 keys.** A permission renders as a checkbox row inside
its module's group, so the row's label is the *action* and the group's
legend is the *module*:

* `permissions.modules.<module>` — **26** keys (also the section headings).
* `permissions.actions.<action>` — **84** keys (12 shared verbs +
  72 module-specific ones; counted from the catalogue, §9).
* `permissions.overrides.<module>.<action>` — optional, empty at merge,
  for the day one action needs a different word in one module.

Resolution order: override → action → humanized fallback
(`snake_case` → `Snake case`), so a permission added by a future slice
renders legibly instead of leaking a raw key. A module absent from the
display-order constant sorts last with its raw name as the legend. Every
checkbox also carries `data-permission="<module>:<action>"` and a `title`
with the raw string: the code is always visible, and tests target it
deterministically.

Totals: **110 keys × 2 languages = 220 strings**, versus 312 for the
per-permission scheme.

---

## 3. Backend surface — four source files, three test files, one doc

Every file justified; nothing else under `backend/` is touched.

| File | Change | Why it must be touched |
|---|---|---|
| `backend/app/schemas/permission.py` | **new** | the two response models (§3.1) |
| `backend/app/api/v1/endpoints/permissions.py` | **new** | the two handlers (§3.2) |
| `backend/app/api/v1/api.py` | +1 `include_router(..., dependencies=TENANT_SCOPED)` | a router must be mounted; TENANT_SCOPED is what resolves the acting tenant for `/me` |
| `backend/app/core/permissions.py` | +2 `UNGUARDED_ROUTES` entries | `test_every_route_is_declared_or_unguarded` fails otherwise (§3.3) |
| `backend/tests/test_permissions_api.py` | **new** | the slice's own module (§3.5) |
| `backend/tests/test_permission_registry.py` | **4 edits**: 1 test renamed, 3 literals `10` → `12` (l.128, l.141, l.142), **+1 tag in `FULLY_UNGUARDED_TAGS` (l.35)**, and the stale `190/180/10` docstring (l.135–136) → `192/180/12` | the allowlist grew and gained a fully-unguarded tag (§3.3) |
| `backend/tests/test_permission_parity_matrix.py` | 1 literal `10` → `12`, 1 test renamed, docstring | it re-asserts the same allowlist size (§3.4) |
| `AGENTS.md` | endpoint-table row + one paragraph | the repository's architecture doc must state the new surface |

`backend/tests/matrix_world.py` carries the phrase "The ten
``UNGUARDED_ROUTES``" in its module docstring at **line 15** — the only
occurrence of the word in the file, so no grep is needed. Updating it is
optional and **must not** change a line of code in that file (F3 requires it
byte-identical apart from comments; if the reviewer prefers, leave it and
note it in the PR body).

### 3.1 Schemas — `app/schemas/permission.py`

```python
class PermissionDescriptorRead(BaseModel):
    """One catalogue entry, pre-split so the UI needs no string surgery."""
    permission: str      # "finance:transaction_create"
    module: str          # "finance"      (deps-free: app.core.permissions.module_of)
    action: str          # "transaction_create"
    superuser_only: bool # in SUPERUSER_ONLY_PERMISSIONS (F3 §6.1)


class MyPermissionsRead(BaseModel):
    """The caller's effective permissions in the acting tenant."""
    tenant_id: UUID
    permissions: list[str]   # sorted
```

`superuser_only` is the field ER-4's "disabled checkbox" reads; it comes
from **F3's** `SUPERUSER_ONLY_PERMISSIONS`, which is why F3 is a hard
dependency of this slice rather than merely an earlier one.

### 3.2 Handlers — `app/api/v1/endpoints/permissions.py`

```python
router = APIRouter()

@router.get("/me", response_model=MyPermissionsRead)
def read_my_permissions(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
    tenant: Annotated[Tenant, Depends(api_deps.get_current_tenant)],
) -> MyPermissionsRead:
    """The caller's own effective permissions, in the acting tenant.

    Strictly self-scoped, exactly like `GET /api/v1/auth/me`, and therefore
    on the unguarded allowlist: there is no permission that could gate
    "tell me what I hold". The acting tenant is resolved by the same
    router-level `get_current_tenant` every scoped route uses, which is what
    makes the answer per-tenant (APRAS-42); re-declaring it here is free
    (one solve per request) and gives the body its `tenant_id`.
    """
    return MyPermissionsRead(
        tenant_id=tenant.id,
        permissions=sorted(api_deps.get_effective_permissions(current_user, session)),
    )


@router.get("/", response_model=list[PermissionDescriptorRead])
def read_permission_catalogue(
    current_user: Annotated[User, Depends(api_deps.get_current_user)],  # noqa: ARG001
) -> list[PermissionDescriptorRead]:
    """The whole catalogue, sorted, identical for every caller.

    Static vocabulary that lives in this repository's source; it carries no
    tenant data and no user data, so it is authenticated and unguarded. The
    group editor needs it to render the permissions the author does *not*
    hold as disabled rather than absent (ER-4).

    Sorted by ``permission`` ascending: the UI groups by module and the
    matrix must not reorder between two requests (test 1, §3.5).
    """
    return [
        PermissionDescriptorRead(
            permission=permission,
            module=module_of(permission),
            action=permission.split(":", 1)[1],
            superuser_only=permission in SUPERUSER_ONLY_PERMISSIONS,
        )
        for permission in sorted(PERMISSIONS)
    ]
```

`GET /permissions/me` is declared **before** `GET /permissions/`; neither
takes a path parameter, so no shadowing is possible either way.

### 3.3 Registry — two `UNGUARDED_ROUTES` entries, and why not `ROUTE_PERMISSIONS`

```python
        # Strictly self-scoped, like /auth/me: "what do I hold here".
        ("GET", "/api/v1/permissions/me"),
        # The static permission vocabulary. No tenant data, no user data;
        # identical for every authenticated caller (IAM F4).
        ("GET", "/api/v1/permissions/"),
```

Mapping the catalogue to `user_types:read` instead was considered and
rejected: it would add a 181st row to `ROUTE_PERMISSIONS`, which
`test_matrix_covers_every_permission_mapped_route` turns into **6 new parity
cells** that cannot be recorded at the baseline sha `02c2025` — the route
did not exist there. Keeping both routes unguarded keeps
`tests/data/parity_matrix_baseline.json` **byte-identical** and
`EXPECTED_CELL_COUNT` at **1080**, which is precisely the property F2 and F3
were built to preserve. The cost is honest and small: two authenticated,
data-free reads carry no permission.

Edits, exactly:

* `tests/test_permission_registry.py`:
  `test_unguarded_allowlist_is_ten_routes` → `..._is_twelve_routes`
  (`== 10` at l.128 → `== 12`); in `test_route_count_is_fully_accounted_for`,
  `len(UNGUARDED_ROUTES) == 10` (l.141) → `== 12` and
  `len(ROUTE_PERMISSIONS) == total - 10` (l.142) → `total - 12`. That test's
  docstring (l.135–136) still reads "190/180/10 is what to expect on the
  APRAS-38 tree this task was written against"; after this slice it is
  **192/180/12** — comment-only, but this chain has been careful about stale
  numbers, so update it and say so in the PR body.
* `tests/test_permission_parity_matrix.py::test_the_ten_unguarded_routes_are_the_only_ones_excluded`
  → `test_the_twelve_unguarded_routes_...`, `== 10` → `== 12`.
* `tests/test_permission_registry.py::test_every_router_module_has_at_least_one_permission`:
  the new tag `permissions` is entirely unguarded, so it **must** be added
  to `FULLY_UNGUARDED_TAGS` (`{"auth", "health", "<root>"}` →
  `{"auth", "health", "permissions", "<root>"}`); the test's own
  `by_tag[tag] <= UNGUARDED_ROUTES` assertion then proves both new routes
  are on the allowlist.

`tests/test_tenant_route_scope.py` needs **no** edit: both routes are
tenant-scoped, `GLOBAL_ROUTES` stays 18, and
`test_route_count_is_fully_accounted_for` there is computed, not pinned.

### 3.4 What must **not** move

* `tests/data/parity_matrix_baseline.json` — byte-identical
  (`git diff --stat` shows it absent).
* `EXPECTED_CELL_COUNT == 1080`, `set(ROUTE_PERMISSIONS)` unchanged at 180.
* `deps.py`, `user_type_service.py`, every existing endpoint module,
  every schema other than the new one, `alembic/versions/**`.
* `tests/test_permission_enforcement.py` — the seven route-level
  `PermissionRequired` mounts are untouched, because neither new route uses
  `require_permission`.

### 3.5 Backend tests — `tests/test_permissions_api.py`

| # | Test | Asserts |
|---|---|---|
| 1 | `test_catalogue_lists_every_permission_exactly_once` | `{r["permission"] for r in body} == PERMISSIONS`, `len(body) == len(PERMISSIONS)`, ascending order |
| 2 | `test_catalogue_marks_exactly_the_superuser_only_permissions` | `{r["permission"] for r in body if r["superuser_only"]} == SUPERUSER_ONLY_PERMISSIONS` |
| 3 | `test_catalogue_splits_module_and_action` | for every row, `f"{module}:{action}" == permission` and `module == module_of(permission)` |
| 4 | `test_me_returns_the_effective_permissions_of_the_acting_tenant` | user in tenants A and B, a group in A carrying `finance:read`: `X-Tenant-Id: A` ⇒ present, `X-Tenant-Id: B` ⇒ absent; `tenant_id` echoes the header |
| 5 | `test_me_for_a_tenant_admin_is_the_whole_catalogue_in_that_tenant_only` | F3 semantics through the wire: `== PERMISSIONS` in the granting tenant, strictly smaller in the other |
| 6 | `test_me_for_a_superuser_is_the_whole_catalogue` | `set(body["permissions"]) == PERMISSIONS` |
| 7 | `test_me_matches_get_effective_permissions` | the route adds nothing: body equals `sorted(get_effective_permissions(user, session))` for a fixture with a custom group |
| 8 | `test_both_routes_require_authentication` | 401 without a token, both routes |

Backend coverage gate is 90%; these eight cases execute every line of both
handlers and both schemas.

---

## 4. The frontend access model

### 4.1 Types — `src/types/permissions.ts`

```ts
export type PermissionKey = string;                    // "finance:read"
export interface PermissionDescriptor {
  permission: PermissionKey; module: string; action: string; superuser_only: boolean;
}
export interface MyPermissions { tenant_id: string; permissions: PermissionKey[] }

/** How a route or menu decides. Exactly two shapes, deliberately. */
export type AccessRule =
  | { module: string; legacyMenu?: MenuKey; landingRedirect?: boolean }
  | { anyOf: readonly PermissionKey[]; legacyMenu?: never; landingRedirect?: never };
```

`{ module }` is ER-2's rule — *any* permission of the module. `{ anyOf }` is
for the four places where one module backs two screens or where the module's
read is `ALL_ROLES` and would gate nothing (§5.2 names all of them).

### 4.2 Data — `src/api/permissions.ts`, `src/hooks/usePermissionQueries.ts`

**Named `usePermissionQueries.ts`, not `usePermissions.ts`**, so that it can
never be confused with the decision hook of §4.3 — two modules with the same
basename would make every `vi.mock("…/usePermissions")` in §8 ambiguous by
sight, and B1's fix requires tests to mock one of them by path.

```ts
useMyPermissions()        // ["me","permissions"],       enabled: useActingTenantReady()
usePermissionCatalogue()  // ["permissions","catalogue"], enabled: useActingTenantReady()
```

`enabled` mirrors `useUserTypes` for the reason its docstring already gives:
these hooks subscribe **above** the auth guard (`Navbar` and
`ProtectedRoute` both call them before their early returns), and a headerless
scoped request is a 400 that never refetches. Neither key starts with
`"tenants"`, so `setActingTenant`'s `resetQueries` evicts both — that is the
whole of ER-3's "sem reload".

Paths are written **exactly** as FastAPI mounts them — `/permissions/` (with
the trailing slash, like `/user-types/`) and `/permissions/me` (without) —
because a mismatch costs a 307 that drops the `Authorization` header on some
proxies; `TenantContext` already carries the same warning for `/tenants`.

The catalogue is fetched only where it is needed (the group editor) via
`usePermissionCatalogue`; `Navbar`/`ProtectedRoute` need only
`/permissions/me`, so an ordinary user's page load gains **one** request.

### 4.3 The decision hooks — `src/features/user-administration/access/useCanAccess.ts`

Named after the hook the rest of the codebase imports, and **not**
`usePermissions.ts`, to keep it distinct from §4.2's query module.

```ts
export interface PermissionSet {
  has(permission: PermissionKey): boolean;
  hasModule(module: string): boolean;
  isLoading: boolean;      // pending and not errored
  all: ReadonlySet<PermissionKey>;
}

/** The REAL user's permissions. Never simulated. Authorization reads this. */
export const usePermissionSet = (): PermissionSet

/** The simulated set while simulating, otherwise identical to usePermissionSet(). Display reads this. */
export const useEffectivePermissionSet = (): PermissionSet

/** Authorization. Consumed by ProtectedRoute. Reads the NON-SIMULATED set. */
export const useCanAccess = (rule?: AccessRule): { allowed: boolean; isLoading: boolean }

/** Display. Consumed by Navbar. Reads the effective (simulated) set. */
export const useCanShowMenu = (rule?: AccessRule): { allowed: boolean; isLoading: boolean }
```

* **`usePermissionSet` ignores the simulation, explicitly and by
  construction** (§2.7): its `all` is built from `useMyPermissions()`'s
  payload and it does **not** call `useSimulation` or
  `useEffectiveIdentity` at all — the absence of the import is the guarantee.
  `useCanAccess` therefore evaluates every `{module}` / `{anyOf}` rule against
  the real identity, which is exactly what `requiredRoles` /
  `requiredCapability` did before this slice.
* **`useEffectivePermissionSet`** is the one simulation arm: while
  `isSimulating`, `all` is the union of the `permissions` arrays of
  `useEffectiveIdentity().userTypeIds`, read from `useUserTypes()`. Outside a
  simulation it returns `usePermissionSet()` unchanged, so the two hooks are
  the same object in the ordinary case and §5.2's one table drives both.
* `useCanAccess` and `useCanShowMenu` share one pure evaluator
  `evaluate(rule, set, menuAllowed)`; only the set differs. A rule can
  therefore never be interpreted two ways.
* **The `legacyMenu` leg is simulation-aware in both**, deliberately: both
  hooks AND `useMenuAccess(rule.legacyMenu)` when it is present (§2.3), and
  `useMenuAccess` consults `useEffectiveIdentity` today. That is APRAS-35's
  documented "one exception" for `requiredMenu`, carried over untouched — this
  slice neither widens nor narrows it.
* **Loading**: `isLoading` is `isPending && !isError`. `ProtectedRoute`
  renders its existing spinner while loading and decides only afterwards —
  without this, `/admin/users` would flash "Acesso restrito" (or, with the
  old code, redirect) on every cold load, which is exactly the regression
  `TenantBootstrapOrder.test.tsx`'s `navigations` sentinel catches.
* **Errored**: fail closed — empty set, no spinner.
* Memoized on the `permissions` array identity, so `Navbar`'s ~20 calls cost
  one `Set` construction per render.

**`useEffectiveIdentity.ts` — one docstring sentence, zero code.** Its
existing rule ("Route guards intentionally do NOT use this hook for
requiredRole/requiredRoles checks…") is still true and still enforced, but it
names props that no longer exist. Append exactly one clarifying sentence,
e.g.: *"Since IAM F4 (APRAS-48) the single prop is `requiredAccess`, decided
by `useCanAccess` over the non-simulated permission set; the `requiredMenu`
exception survives as `AccessRule.legacyMenu`, still evaluated through
`useMenuAccess` and therefore still simulation-aware."* The file's code and
`useEffectiveIdentity.test.tsx` are otherwise **byte-identical**.

---

## 5. Routes and menus

### 5.1 `ProtectedRoute`

```ts
interface ProtectedRouteProps { children: React.ReactElement; requiredAccess?: AccessRule }
```

Order of decisions: `isLoading` (auth) → spinner; `!isAuthenticated` →
`Navigate("/login")`; `requiredAccess?.landingRedirect` and the **effective**
role is `GUEST` → `/welcome`, `PORTEIRO` → `/gate` (TRANSITIONAL, §2.4 —
these two keep reading `useEffectiveIdentity().role`, exactly as l.82/l.86 do
today); `useCanAccess(requiredAccess).isLoading` → spinner; `!allowed` →
`<RestrictedAccessMessage/>`; else `children`. No `requiredRole`,
`requiredRoles`, `requiredCapability` or `requiredMenu` remains — a route
that passes an unknown prop fails `tsc -b`.

`ProtectedRoute` calls **`useCanAccess`** and never `useCanShowMenu`: the
authorization branch reads the non-simulated set (§2.7). `Navbar` is the
mirror image (§5.3). After the slice,
`grep -rn "requiredRole=\|requiredRoles=\|requiredCapability=\|requiredMenu=" src`
must return **nothing** — today it returns `src/App.tsx` plus the seven test
files listed in §8.2.

### 5.2 `ROUTE_ACCESS` — the whole table

`src/features/user-administration/access/routeAccess.ts` exports
`ROUTE_ACCESS: Record<string, AccessRule>` and `NAV_ITEMS: readonly {path,
labelKey, access}[]`, where every `NAV_ITEMS` entry's `access` **is** the
`ROUTE_ACCESS` entry of its `path` (asserted by a test, so a menu can never
outlive its route's rule).

"Roles" columns are the role sets `LEGACY_ROLE_PERMISSIONS` yields **today**
for the rule (A=ADMINISTRATOR, D=DIRECTOR, M=MANAGER, G=GUEST, R=RESIDENT,
P=PORTEIRO); they are how the delta column was computed, not something the
code reads.

| Route | Rule | Rule ⇒ roles | Today | Delta |
|---|---|---|---|---|
| `/login` `/signup` `/forgot-password` `/reset-password` | public | — | — | — |
| `/dashboard` | `{module:"tasks", legacyMenu:"tasks", landingRedirect:true}` | ADMPR ∧ menu | menu gate | G with a `tasks` menu key loses the link (`tasks:*` has no G; the backend already 403s) |
| `/categories` | `{module:"categories", legacyMenu:"categories", landingRedirect:true}` | ALL ∧ menu | menu gate | none |
| `/welcome` | *(authenticated)* | — | — | none |
| `/lots` | `{module:"lots"}` | ADMP | ADMRG | R, G lose (`lots:read` is ADMP — 403 today); P gains (holds it) |
| `/authorizations` | `{anyOf:["authorizations:read"]}` | ADGMR | ADMRG | none *(module rule would add P via `gate_lookup`)* |
| `/gate` | `{anyOf:["gate:checkin"]}` | ADMP | ADMP | none *(module rule would add G/R via `gate:logs_read`)* |
| `/occurrences` | `{module:"occurrences"}` | ADGMR | ADMRG | none |
| `/feedback` | `{module:"feedback"}` | ALL | authenticated | none |
| `/documents` | `{module:"documents"}` | ADGMR | ADMRG | none |
| `/projects` | `{module:"projects"}` | ADMR | ADMRG | G loses (`projects:read` is ADMR — 403 today) |
| `/announcements` | `{module:"announcements"}` | ADGMR | ADMRG | none |
| `/finance` | `{module:"finance"}` | ADMR | ADMR | none |
| `/packages` | `{module:"packages"}` | ADMPR | ADMR | P gains (holds `packages:queue_read/create/pickup`) |
| `/reservations` | `{module:"reservations"}` | ADMPR | ADMRG | G loses (403 today); P gains (holds `reservations:read`) |
| `/spaces` | `{anyOf:["spaces:create","spaces:update","spaces:deactivate"]}` | AD | AD | none *(module rule would be ALL: `spaces:read` is ALL_ROLES)* |
| `/voting` | `{module:"votes"}` | ADMR | ADMR | none |
| `/assets` | `{module:"assets"}` | ADM | ADM | none |
| `/purchases` | `{module:"purchases"}` | ADM | ADM | none |
| `/gate-monitor` | `{anyOf:["access_control:events_read"]}` | ADM | ADM | none |
| `/admin/access-control` | `{anyOf:["access_control:device_create"]}` | AD | AD | none *(shares its module with `/gate-monitor`, hence `anyOf`)* |
| `/admin/photo-approvals` | `{anyOf:["uploads:pending_read"]}` | AD | D only | **A gains** — today `requiredRole={DIRECTOR}` locks out the administrator the Navbar already offers the link to; a pre-existing bug, corrected |
| `/admin/users` | `{anyOf:["users:update"]}` | A + every full-catalogue holder | capability | none (F3 makes tenant_admin/superuser hold it) |
| `/users/contact-info` | `{anyOf:["users:update_contact"]}` | AM + capability | AM + capability | none |
| `/admin/groups` **new** | `{anyOf:["user_types:create","user_types:update","user_types:delete"]}` | A + capability | — | new |
| `/admin/groups/:groupId` **new** | same | A + capability | — | new |
| `/` | `RootRedirect` (unchanged) | — | — | none |

Deltas total: 4 corrections (routes the backend already refuses), 3 accepted
widenings for PORTEIRO (routes the backend already permits), 1 bug fix. All
eight are listed in the PR body.

### 5.3 `Navbar`

The 20 hand-written `{condition && <Link/>}` blocks become one
`NAV_ITEMS.map(item => <NavLink …/>)` with **`useCanShowMenu(item.access)`**
per item — the display hook, so "view-as" keeps previewing the simulated
user's menu (§2.7) — plus the unchanged right-hand cluster (tenant switcher, simulation
controls, language, user, logout). The `/admin/groups` link is added. No
role comparison remains in `Navbar` except `user?.role === ADMINISTRATOR`
for `SimulationControls`, which stays, marked `TRANSITIONAL (IAM F4 -> F5)`:
"view-as" is an operator tool, not an authorization gate, and F3 exposes no
`is_superuser` to replace it.

Rules of hooks: `useCanShowMenu` is called from a small `<NavItem/>`
component, once per item, never inside a loop body of the parent.

`Navbar` now subscribes to `useMyPermissions()` (through
`useEffectivePermissionSet`), i.e. to a real TanStack `useQuery`. **Every test
that mounts `Navbar` must therefore provide a `QueryClientProvider`** — see
§8.2's general rule and the two files B1 found.

---

## 6. The groups administration area

### 6.1 Routes and components

| Path | Component | Contents |
|---|---|---|
| `/admin/groups` | `GroupsAdminPage.tsx` | table of groups: name, badge, permission count, member count, actions (Editar, Clonar, Excluir); "Novo grupo" form |
| `/admin/groups/:groupId` | `GroupDetailPage.tsx` | name field, `PermissionMatrix`, `GroupMembersPanel`, Salvar/Cancelar |

Supporting modules: `components/PermissionMatrix.tsx`,
`components/GroupMembersPanel.tsx`,
`hooks/useUserTypeMutations.ts` (create / update / delete / clone /
`useSetUserGroups`), `utils/permissionLabels.ts` (§2.8 resolution),
`utils/permissionErrors.ts` (§6.5).

### 6.2 Role-linked groups ("grupos de sistema") — the decision ER-1 asks for

Nothing is seeded (F1's final decision), but the **6 role-linked
`UserType` rows still exist per tenant** with a non-null `role`, and
`DELETE /user-types/{id}` answers **403 "Role-linked user types cannot be
deleted"** for them (`endpoints/user_types.py`, APRAS-9).

Presentation, exactly:

* a `<Badge>` reading `groups.roleLinkedBadge` — "Grupo de papel (legado)" /
  "Role group (legacy)" — with `title` = `groups.roleLinkedHint`;
* **no delete control** (mirrors the backend's 403, as today's `🔒` does);
* the name input is `readOnly` and the save sends the unchanged name. The
  API *does* permit renaming them, but the name is the only human trace of
  which legacy role the row serves and `get_effective_user_type_ids` matches
  on `role`, not name — a rename would confuse without enabling anything.
  This honours ER-1's "sem opção de deletar/renomear";
* **permissions are editable** — this is how an operator restores
  baseline-by-role access under the new model, and it is the main reason the
  rows are shown at all;
* **cloning is offered**: the clone has no `role` (the field is read-only in
  every write schema), so it is an ordinary group.

### 6.3 `PermissionMatrix`

* Renders one `<fieldset>` per module, ordered by `PERMISSION_MODULE_ORDER`
  (a display-order constant; unknown modules sort last, §2.8), legend =
  `permissions.modules.<module>`.
* One checkbox per permission; accessible name = the action label,
  `data-permission` = the raw key, `title` = the raw key.
* Per-module "marcar todos / desmarcar todos" affecting only the module's
  **enabled** boxes.
* **Disabled** iff `descriptor.superuser_only || !mySet.has(permission)` —
  the exact mirror of F3's `assert_can_grant` (`SUPERUSER_ONLY_PERMISSIONS`
  first, then "permissions you do not hold"), with `title` explaining which
  of the two applies (`permissions.disabledSuperuserOnly`,
  `permissions.disabledNotHeld`). A disabled box that is **already checked**
  in the stored bundle stays checked and disabled, and is resent unchanged
  on save — otherwise editing a group's name would silently strip
  permissions its author cannot grant.
* On save: `PATCH /user-types/{id}` with `{name, permissions,
  allowed_menus}`, where `allowed_menus` is **derived and unioned with the
  stored value** (§2.3), never replaced:

  ```ts
  const derived = [
    ...(permissions.some(p => p.startsWith("tasks:")) ? ["tasks"] : []),
    ...(permissions.some(p => p.startsWith("categories:")) ? ["categories"] : []),
  ];
  const allowed_menus = [...new Set([...(group.allowed_menus ?? []), ...derived])].sort();
  ```

  No menu checkboxes exist in the UI, so this is the only writer of the
  column, and it can only add. Pinned by
  `GroupDetailPage.test.tsx::derives allowed_menus from the selected permissions on save`
  and `…::never revokes a menu key the group already had` (§8.1).

### 6.4 `GroupMembersPanel` — both directions

* Members = `useUsers()` filtered by `u.user_types?.some(t => t.id === groupId)`.
* "Adicionar membro": a select of the tenant's non-member users →
  `PATCH /users/{id}` with `user_type_ids = [...current, groupId]`.
* "Remover": `PATCH /users/{id}` with the id filtered out.
* Both invalidate `["users"]` (all filters) and nothing else.
* The **user side** is the existing edit-user modal in `AdminUserDashboard`,
  relabelled `admin.editGroups` ("Grupos"), same `PATCH`, same payload
  shape. One mutation module (`useSetUserGroups`) serves both screens, so
  "os dois sentidos" is one code path with two entry points.
* `assert_can_assign_user_types` (F2 §9.3) can answer 403 on either side;
  §6.5 handles it identically in both.

### 6.5 The friendly 403 (ER-4)

`utils/permissionErrors.ts` exports the two backend prefixes as constants —
`"You cannot grant permissions you do not hold: "` (F2
`user_type_service.assert_can_grant`) and `"These permissions are granted by
is_superuser only: "` (F3 §6.2) — plus
`friendlyPermissionError(err, t): string`, which on a match renders
`permissions.errors.cannotGrant` / `permissions.errors.superuserOnly` with
the offending permissions **localised through the same label resolver as the
checkboxes**, and otherwise falls back to `parseApiError`. The 409 from a
duplicate group name maps to `groups.errors.nameTaken`. The function is
pure and unit-tested (five cases, including the fallback), which is also
where its branch coverage comes from.

---

## 7. `AdminUserDashboard`

* The role `<Select>` and `handleRoleSelect` are **deleted**; the "Cargo"
  column becomes a read-only muted badge headed `admin.colRoleLegacy`
  (§2.5). `admin.cannotChangeOwnRole` becomes unused and is removed from
  both locales.
* The inline "User Types" card (create form, edit-type modal,
  `allowed_menus` checkboxes, `ALL_MENU_KEYS`, the `MenuKey` import) is
  **deleted**; a `Button asChild` links to `/admin/groups`. The group
  editor now lives in one place.
* The edit-user modal keeps its checkbox list, relabelled `admin.editGroups`,
  and calls `useSetUserGroups`.
* Everything else — status filter, activate/deactivate, self-guard,
  `AlertModal` — is untouched.

---

## 8. Tests

### 8.1 New frontend test files

| File | Cases (names are the contract) |
|---|---|
| `src/features/user-administration/__tests__/useCanAccess.test.tsx` | `resolves the acting tenant's permissions from /permissions/me`; `is loading until the query settles`; `falls back to an empty set when the query errors`; `usePermissionSet ignores an active simulation`; `useEffectivePermissionSet unions the simulated groups' permissions while simulating`; `hasModule matches on the permission prefix` |
| `src/features/user-administration/__tests__/routeAccess.test.ts` | `every NAV_ITEMS entry reuses the ROUTE_ACCESS rule of its path`; `every protected path in App.tsx has a ROUTE_ACCESS entry`; `only /dashboard and /categories carry legacyMenu and landingRedirect` |
| `src/features/user-administration/__tests__/Navbar.permissions.test.tsx` | `shows a morador exactly the links their permissions allow`; `shows a porteiro the Portaria link and not Comunicados/Financeiro/Administração`; `hides Financeiro from a custom group with no finance permission`; `shows Grupos to a user holding user_types:update` |
| `src/features/user-administration/__tests__/ProtectedRoute.permissions.test.tsx` | `renders the page when the rule's module permission is held`; `renders "Acesso restrito" when it is not`; `renders the spinner while /permissions/me is pending`; `admits a tenant_admin holding the whole catalogue to /admin/users`; `admits an administrator to /admin/photo-approvals`; **`keeps route access on the real permission set while simulating`** — an administrator holding `user_types:update` and simulating `RESIDENT` (whose groups grant none of it) still renders `/admin/groups`, **and** in the same tree the Navbar shows the RESIDENT menu set, proving the two hooks of §4.3 read different sets from one `ROUTE_ACCESS` rule |
| `src/features/user-administration/__tests__/GroupsAdminPage.test.tsx` | `lists groups with their permission and member counts`; `marks role-linked groups and offers no delete control`; `creates a group`; `clones a group with its permission bundle pre-filled`; `shows a friendly message when the API answers 403` |
| `src/features/user-administration/__tests__/GroupDetailPage.test.tsx` | `groups the checkboxes by module`; `disables permissions the author does not hold`; `disables the four superuser-only permissions`; `keeps an already-granted permission the author cannot grant checked and resends it`; `derives allowed_menus from the selected permissions on save`; `never revokes a menu key the group already had` (§2.3: a group stored with `allowed_menus:["tasks"]` and zero `tasks:*` permissions is renamed; the PATCH body still carries `["tasks"]`); `blocks renaming a role-linked group` |
| `src/features/user-administration/__tests__/GroupMembersPanel.test.tsx` | `lists the group's members`; `adds a member through PATCH /users/{id}`; `removes a member`; `shows the anti-escalation 403 as a friendly message` |
| `src/features/user-administration/__tests__/permissionErrors.test.ts` | 5 pure cases incl. the `parseApiError` fallback |
| `src/features/user-administration/__tests__/permissionLabels.test.ts` | `prefers an override`; `falls back to the action label`; `humanizes an unknown action`; `never returns the raw key for a catalogue action` |
| `src/i18n/__tests__/parity.test.ts` | `en and pt have identical flattened key sets`; `every module and action key exists in both` |

### 8.2 Existing frontend tests that legitimately change

**The general rule, from which the table below is derived.** After §5.1 and
§5.3, `ProtectedRoute` calls `useCanAccess` and `Navbar` calls
`useCanShowMenu`, and both bottom out in `useMyPermissions()` — a real
TanStack `useQuery`. Therefore **every test that mounts `Navbar` or
`ProtectedRoute` must now either wrap the tree in a `QueryClientProvider`
with a `/permissions/me` fixture, or `vi.mock` the decision module
(`…/access/useCanAccess`)**. Mocking `useUserTypes` alone — today's habit in
several files — is no longer sufficient: a bare mount throws
`No QueryClient set, use QueryClientProvider to set one`. The two greps that
produce the complete list are
`grep -rln "requiredRole=\|requiredRoles=\|requiredCapability=\|requiredMenu=" src`
(8 files today: `src/App.tsx` + 7 test files) and
`grep -rln "components/Navbar" src --include='*.test.tsx'` (5 files today).
Every one of those files appears in the table below; if either grep returns a
file this table does not name, the implementer must add it and say so in the
PR body rather than leave the suite red.

| File | Change | What must **not** change |
|---|---|---|
| `src/__tests__/TenantBootstrapOrder.test.tsx` | a `/permissions/me` arm in `installClient` returning per-tenant permissions; the fixtures' `RESIDENT_TYPE` gains `permissions` | all three assertions, including the `navigations` sentinel — it now additionally proves the permission query does not cause a redirect |
| `src/__tests__/AppRouting.smoke.test.tsx` | none expected (only public routes; every request already rejects) | the whole file |
| `src/features/user-administration/__tests__/ProtectedRoute.test.tsx` | rewritten around `requiredAccess`; role cases become permission cases | the unauthenticated → `/login` case verbatim |
| `…/ProtectedRoute.capability.test.tsx` | rewritten: the capability holder is now "holds the catalogue" | the scenario (tenant_admin reaches `/admin/users`) |
| `…/ProtectedRoute.porteiroGate.test.tsx`, `…/ProtectedRoute.guestWelcome.test.tsx`, `…/ProtectedRoute.porteiroRouteGating.test.tsx` | `requiredMenu="tasks"` → `requiredAccess={ROUTE_ACCESS["/dashboard"]}` | every redirect assertion |
| `…/Navbar.test.tsx`, `…/Navbar.tenantAdmin.test.tsx` | driven by a permissions fixture instead of role/`allowed_menus` | the set of link names asserted |
| `…/AdminUserDashboard.test.tsx` | role-select and inline user-type cases removed; a `/admin/groups` link case added; type-assignment cases kept | the activate/deactivate and self-guard cases |
| `src/features/assembly-voting/__tests__/VotingRouteAccess.test.tsx` | `requiredRoles={VOTING_ROLES}` → `requiredAccess={{module:"votes"}}`, parametrised over permission fixtures | that A/D/M/R reach the page and P/G do not |
| `src/features/purchase-management/__tests__/PurchasesRouteGating.test.tsx` | **three separate breakages, all mandatory.** (a) l.63 renders `<ProtectedRoute requiredRoles={PURCHASES_ROLES}>` — a `tsc -b` error after §5.1; becomes `requiredAccess={ROUTE_ACCESS["/purchases"]}` (`{module:"purchases"}`). (b) the three `"redirects %s to /dashboard"` cases assert the **old** denial shape; §2.4 makes denial in-place, so they become `"denies %s with Acesso restrito"` asserting `getByText("Acesso restrito")` and the absence of `"Purchases Page"` — the `/dashboard` catch-all `<Route>` in `renderPurchasesRoute` goes with them. (c) the second `describe` (`navbar entry for purchase quotations`) mounts a **bare `<Navbar/>` in only a `MemoryRouter`**, mocking `SimulationContext` and `useUserTypes` and nothing else (l.25–31, l.99–104); it survives today only because nothing in `Navbar` queries. It gains a `QueryClientProvider` + `/permissions/me` fixture per the general rule above, and its six cases become permission-driven | **the gate itself**: `/purchases` and the "Cotações de Compra" link stay A/D/M-only and stay denied to R/P/G (§5.2 delta = none), and both `describe` blocks keep their `it.each` parametrisation over the same six roles. The exported `PURCHASES_ROLES` constant may stay as the fixture-selector for the parametrisation |
| `src/features/user-administration/__tests__/TenantSwitcher.test.tsx` | `renderNavbar()` (l.63–68) mounts a bare `<Navbar/>` in only a `MemoryRouter`, mocking `SimulationContext` and `useUserTypes` (l.12–28) — it **throws** `No QueryClient set` once `Navbar` calls `useMyPermissions()`. Wrap `renderNavbar` in a `QueryClientProvider` with a `/permissions/me` fixture. This is the file's **only** change | all four cases verbatim, including the third one's byte-comparison of the zero-tenant and single-tenant `container.textContent` (the permission fixture must be identical across the two renders inside it, or that assertion breaks for an unrelated reason) and the fourth one's pure i18n assertions on `tenant.switcherLabel` |
| `…/TenantSwitch.integration.test.tsx` | **+1 case**: `re-evaluates menus after a tenant switch without a reload` — tenant A returns `finance:read`, B does not; the Financeiro link disappears and no `window.location` assignment occurs | the existing cases |

Deleted: `useAdminCapability.ts` + `__tests__/useAdminCapability.test.tsx`.

Kept untouched: `useMenuAccess.ts` and its two test files (§2.3);
`simulatedPermissions.ts` and its test (object-level task visibility is F5's);
`useEffectiveIdentity.test.tsx` — its subject gains **one docstring sentence
and no code** (§4.3), so its seven cases must keep passing verbatim, which is
this slice's mechanical proof that APRAS-35's real-vs-simulated split was
preserved rather than reimplemented.

`src/__tests__/TenantBootstrapOrder.test.tsx` matches the first grep only in
prose, not as a JSX prop; it is listed above for its `/permissions/me` arm,
not for a prop rename.

---

## 9. i18n

New keys, both locales, identical structure:

* `permissions.modules.*` — 26 (the module list is the 26 prefixes of the
  catalogue: access_control, announcements, assemblies, assets,
  authorizations, categories, documents, feedback, finance, gate, inventory,
  lots, occurrences, packages, projects, purchases, reservations, residents,
  spaces, tasks, tenants, uploads, user_types, users, visitors, votes).
* `permissions.actions.*` — 84 (12 shared: approve, cancel, close, comment,
  create, delete, link_user, read, reject, summary_read, unlink_user,
  update; 72 module-specific).
* `permissions.overrides` — present and empty.
* `permissions.disabledSuperuserOnly`, `permissions.disabledNotHeld`,
  `permissions.errors.cannotGrant`, `permissions.errors.superuserOnly`.
* `groups.*` — title, new/clone/delete/save labels, `roleLinkedBadge`,
  `roleLinkedHint`, `members*`, `errors.nameTaken`, `cloneSuffix`.
* `nav.groups`, `admin.colRoleLegacy`, `admin.editGroups`,
  `simulation.permissionsPreviewNote`.

Removed from both: `admin.cannotChangeOwnRole`, `admin.allowedMenus`,
`admin.menuTasks`, `admin.menuCategories`, `admin.editTypeTitle`,
`admin.editTypeName`, `admin.newTypeName`, `admin.addType`,
`admin.confirmDeleteType`, `admin.errorCreatingType`,
`admin.errorDeletingType`, `admin.errorUpdatingType`, `admin.userTypes`,
`admin.noTypesYet` — **only if** `grep -rn "<key>" src/` returns nothing
after the edit; a key still referenced stays.

Baseline measured today: `en.json` and `pt.json` each hold **1093**
flattened keys with **zero** asymmetric keys. `src/i18n/__tests__/parity.test.ts`
makes that mechanical from now on.

---

## 10. Gates, baselines and the PR body

Measured **today** on this worktree (frontend untouched by F2/F3, so these
are the F3 merge-base figures; re-measure and quote both):

| Metric | Baseline | Gate | Requirement |
|---|---|---|---|
| `npm run test` | 112 files, **1066** tests, all pass | — | all pass |
| Statements | **87.66 %** (4313/4920) | 80 | ≥ 80 |
| Branches | **79.93 %** (2525/3159) | 76 | ≥ 76 |
| Functions | **83.38 %** (1475/1769) | 78 | ≥ 78 |
| Lines | **88.59 %** (4164/4700) | 80 | ≥ 80 |
| `npm run lint` | **467** problems (465 errors, 2 warnings; 427 in test files, 40 in `src/**` non-test; 445 are `@typescript-eslint/no-explicit-any`) | — | ≤ 467, and **0** new in non-test `src/**` |
| `npm run build` | passes | — | passes |
| Backend | `pytest` green, 90 % gate | 90 | green |

Branches is the tightest gate: at 2525/3159, adding *B* new branches at
coverage rate *r* keeps the gate iff `2525 + rB ≥ 0.76 × (3159 + B)`; for
`B = 300` that is `r ≥ 34.6 %`. The new files must nonetheless each reach
the four gates on their own — the named tests of §8.1 are sized for that.

PR body must carry: the eight route deltas of §5.2; the two `UNGUARDED_ROUTES`
additions and the four test literals they move; the confirmation that
`tests/data/parity_matrix_baseline.json` is untouched
(`git diff --stat` output); baseline vs. final for every row above; and any
name deviation from F2/F3 (§0).

---

## 11. Hand-off to F5 (`APRAS-49`)

Everything this slice leaves marked `TRANSITIONAL (IAM F4 -> F5)`, so F5
inherits a list rather than a search:

1. `ROUTE_ACCESS`'s `legacyMenu` field on two entries + the three lines in
   `useCanAccess` + `useMenuAccess.ts` + its two test files — deletable the
   moment `deps.assert_menu_access` goes.
2. `ROUTE_ACCESS`'s `landingRedirect` field + the two role comparisons in
   `ProtectedRoute` + `RootRedirect`'s three-way role switch.
3. `user?.role === ADMINISTRATOR` in `Navbar` (SimulationControls).
4. The read-only "Cargo (legado)" column in `AdminUserDashboard`.
5. The `allowed_menus` derivation in the group editor's save payload
   (§2.3) — additive-only, and deletable outright when the column goes.
6. `useEffectiveIdentity.ts`'s docstring rule about the `legacyMenu`
   exception (§4.3): when `useMenuAccess` dies, the sentence about it dies
   with it, and `useEffectivePermissionSet` collapses into
   `usePermissionSet` only if F5 also decides to stop simulating menus.

### 11.1 The two greps that pin the hand-off (measured today, at F3's tip)

Both are run from `frontend/` and both are quoted in the PR body.

**(a) The route/menu props are gone.**

```
grep -rn "requiredRole=\|requiredRoles=\|requiredCapability=\|requiredMenu=" src
```

Today: `src/App.tsx` (22 occurrences) plus the 7 test files of §8.2.
**After this slice: no output at all.** This is the sharp check — it proves
the four props were removed rather than merely stopped being read.

**(b) No *new* module reads the legacy role enum, and one is gone.**

```
grep -rln "UserRole\." src --include='*.tsx' --include='*.ts' | grep -v __tests__ | sort
```

Today this returns **24** files. After this slice it must return **exactly
these 22**, and nothing else:

```
src/App.tsx
src/features/announcement-feed/components/AnnouncementCard.tsx
src/features/announcement-feed/components/AnnouncementFeedPage.tsx
src/features/announcement-feed/components/CommentThread.tsx
src/features/assembly-voting/components/AssemblyVotingPage.tsx
src/features/assembly-voting/components/LotVotingAdminPanel.tsx
src/features/asset-management/components/AssetsInventoryPage.tsx
src/features/feedback-management/components/FeedbackChannelPage.tsx
src/features/lot-management/components/LotsPage.tsx
src/features/purchase-management/components/PurchaseRequestDetailModal.tsx
src/features/purchase-management/components/PurchaseRequestsPage.tsx
src/features/space-reservation-management/components/ReservableSpacesPage.tsx
src/features/space-reservation-management/components/SpaceBookingPage.tsx
src/features/task-management/components/CategoriesPage.tsx
src/features/task-management/components/TaskForm.tsx
src/features/task-management/utils/simulatedPermissions.ts
src/features/user-administration/components/Navbar.tsx
src/features/user-administration/components/ProtectedRoute.tsx
src/features/user-administration/components/SimulationControls.tsx
src/features/user-administration/context/tenantState.ts
src/features/user-administration/context/useMenuAccess.ts
src/hooks/useUsers.ts
```

The list is the 24 of today minus exactly two:

* `src/features/user-administration/context/useAdminCapability.ts` — **deleted** (§2.4);
* `src/features/user-administration/pages/AdminUserDashboard.tsx` — its only
  four `UserRole.` references are the `<option value={UserRole.X}>` lines
  (l.407–410) of the role `<select>` that §7 deletes; the read-only "Cargo
  (legado)" badge renders `{user.role}` and needs no enum. The now-unused
  `UserRole` import must go with them or `npm run lint` gains an error.

The remaining 22 are **deliberately unchanged by this slice**: `App.tsx` for
`RootRedirect`'s three-way switch (l.49–53) and nothing else,
`Navbar.tsx` for `user?.role === UserRole.ADMINISTRATOR` gating
`<SimulationControls/>` (l.390) and nothing else, `ProtectedRoute.tsx` for the
two `landingRedirect` comparisons, `useMenuAccess.ts`/`simulatedPermissions.ts`
/`tenantState.ts`/`SimulationControls.tsx`/`useUsers.ts` for the transitional
reasons named above, and the 14 feature components for **in-page** element
visibility (a button, a column, a tab) — object- and field-level visibility is
explicitly F5's scope, not this slice's, and none of them gates a route or a
menu.

---

## Expected Results

- [ ] **ER-1 — the groups administration area exists.** `/admin/groups`
      lists every group with its permission and member counts and offers
      create, clone and delete; `/admin/groups/:groupId` edits the name, the
      permission set as checkboxes grouped in one `<fieldset>` per module,
      and the members; role-linked groups (`role != null`) render the
      `groups.roleLinkedBadge` badge, expose **no** delete control and have
      a `readOnly` name input, while their permissions stay editable; a
      member can be added or removed **from the group screen** and the same
      groups can be assigned **from the user screen**, both through
      `PATCH /api/v1/users/{id}` with `user_type_ids`.
      `npx vitest run src/features/user-administration/__tests__/GroupsAdminPage.test.tsx src/features/user-administration/__tests__/GroupDetailPage.test.tsx src/features/user-administration/__tests__/GroupMembersPanel.test.tsx`
      passes, including `marks role-linked groups and offers no delete control`,
      `clones a group with its permission bundle pre-filled`,
      `disables permissions the author does not hold`,
      `adds a member through PATCH /users/{id}` and
      `never revokes a menu key the group already had` (saving a group stored
      with `allowed_menus: ["tasks"]` and zero `tasks:*` permissions still
      sends `allowed_menus` containing `"tasks"`).
- [ ] **ER-2 — the API returns the acting tenant's effective permissions and
      the frontend gates menus and routes on them.**
      `GET /api/v1/permissions/me` answers
      `{tenant_id, permissions[]}` equal to
      `sorted(deps.get_effective_permissions(user, session))` for the tenant
      in `X-Tenant-Id`, and `GET /api/v1/permissions/` returns all
      `len(PERMISSIONS)` catalogue entries with `module`, `action` and
      `superuser_only`; `backend/tests/test_permissions_api.py` passes, with
      `test_me_returns_the_effective_permissions_of_the_acting_tenant`
      proving the same user gets different sets in two tenants. In the
      frontend, a menu link and its route share one `ROUTE_ACCESS` rule
      (`routeAccess.test.ts::every NAV_ITEMS entry reuses the ROUTE_ACCESS
      rule of its path`) and a menu is shown iff the rule is satisfied by
      the fetched permission set; `Navbar.permissions.test.tsx` passes for a
      **morador**, a **porteiro** and a **custom group holding no permission
      of a module** (`hides Financeiro from a custom group with no finance
      permission`). Authorization is decided on the **real** (non-simulated)
      permission set while menus follow the simulated one:
      `ProtectedRoute.permissions.test.tsx::keeps route access on the real
      permission set while simulating` passes — an administrator holding
      `user_types:update`, while simulating a `RESIDENT` whose groups grant
      none of it, still renders `/admin/groups`, and the Navbar in the same
      tree shows the RESIDENT menu set.
      Finally, run from `frontend/`:
      `grep -rn "requiredRole=\|requiredRoles=\|requiredCapability=\|requiredMenu=" src`
      produces **no output**, and
      `grep -rln "UserRole\." src --include='*.tsx' --include='*.ts' | grep -v __tests__ | sort`
      produces **exactly these 22 lines and no others**:
      `src/App.tsx`,
      `src/features/announcement-feed/components/AnnouncementCard.tsx`,
      `src/features/announcement-feed/components/AnnouncementFeedPage.tsx`,
      `src/features/announcement-feed/components/CommentThread.tsx`,
      `src/features/assembly-voting/components/AssemblyVotingPage.tsx`,
      `src/features/assembly-voting/components/LotVotingAdminPanel.tsx`,
      `src/features/asset-management/components/AssetsInventoryPage.tsx`,
      `src/features/feedback-management/components/FeedbackChannelPage.tsx`,
      `src/features/lot-management/components/LotsPage.tsx`,
      `src/features/purchase-management/components/PurchaseRequestDetailModal.tsx`,
      `src/features/purchase-management/components/PurchaseRequestsPage.tsx`,
      `src/features/space-reservation-management/components/ReservableSpacesPage.tsx`,
      `src/features/space-reservation-management/components/SpaceBookingPage.tsx`,
      `src/features/task-management/components/CategoriesPage.tsx`,
      `src/features/task-management/components/TaskForm.tsx`,
      `src/features/task-management/utils/simulatedPermissions.ts`,
      `src/features/user-administration/components/Navbar.tsx`,
      `src/features/user-administration/components/ProtectedRoute.tsx`,
      `src/features/user-administration/components/SimulationControls.tsx`,
      `src/features/user-administration/context/tenantState.ts`,
      `src/features/user-administration/context/useMenuAccess.ts`,
      `src/hooks/useUsers.ts`
      — i.e. today's 24 minus the deleted
      `src/features/user-administration/context/useAdminCapability.ts` and
      minus `src/features/user-administration/pages/AdminUserDashboard.tsx`,
      whose only `UserRole.` uses are the deleted role `<select>`'s options.
- [ ] **ER-3 — the user form asks for groups, not for cargo, and a tenant
      switch re-evaluates without a reload.** `AdminUserDashboard` contains
      no role `<select>` and never sends `role` in
      `PATCH /api/v1/users/{id}` (the backend needs no change: `UserUpdate.role`
      is already optional and there is no `POST /users/`); the edit modal's
      group list is headed `admin.editGroups`.
      `TenantSwitch.integration.test.tsx::re-evaluates menus after a tenant
      switch without a reload` passes: switching from a tenant whose
      permissions include `finance:read` to one that does not removes the
      Financeiro link with no page reload.
- [ ] **ER-4 — anti-escalation is visible in the UI and the 403 is
      friendly.** In the group editor a permission is rendered `disabled`
      iff it is `superuser_only` or absent from the author's own set — the
      mirror of `assert_can_grant` — while an already-granted permission the
      author cannot grant stays checked and is resent unchanged
      (`GroupDetailPage.test.tsx::keeps an already-granted permission the
      author cannot grant checked and resends it`); a 403 from
      `POST/PATCH /user-types/` or `PATCH /users/{id}` renders a localised
      message naming the offending permissions by their labels, never the
      raw backend sentence (`permissionErrors.test.ts`, 5 cases,
      including the `parseApiError` fallback).
- [ ] **ER-5 — the gates are green and nothing else moved.**
      `npm run build`, `npm run lint` (≤ **467** problems, 0 new outside
      test files) and `npm run test:coverage` (≥ 80 statements / 78
      functions / 76 branches / 80 lines) all pass;
      `src/__tests__/AppRouting.smoke.test.tsx` passes unmodified and
      `src/__tests__/TenantBootstrapOrder.test.tsx` passes with its three
      assertions unchanged. The **whole** frontend suite is green, including
      the two files that mount a bare `Navbar` and would otherwise throw
      `No QueryClient set`:
      `npx vitest run src/features/purchase-management/__tests__/PurchasesRouteGating.test.tsx src/features/user-administration/__tests__/TenantSwitcher.test.tsx src/features/user-administration/__tests__/useEffectiveIdentity.test.tsx`
      passes, with `/purchases` and its "Cotações de Compra" link still
      granted to ADMINISTRATOR/DIRECTOR/MANAGER and denied to
      RESIDENT/PORTEIRO/GUEST, all four `TenantSwitcher` cases unchanged, and
      all seven `useEffectiveIdentity` cases unchanged (its subject gains a
      docstring sentence and no code).
      `src/i18n/__tests__/parity.test.ts` proves
      `en.json` and `pt.json` have identical flattened key sets;
      `pytest` is green with the backend's 90 % gate, `alembic heads`
      still reports the single head `0031_add_user_is_superuser` (no
      migration in this slice) and
      `git diff --stat backend/tests/data/parity_matrix_baseline.json` is
      empty.

---

*(End of Expected Results. Nothing below this line is an acceptance criterion.)*
