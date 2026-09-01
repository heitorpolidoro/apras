# APRAS-38 — Integrate multi-tenancy end to end: tenant switcher UI and tenant_admin experience

Fourth and final slice of the multi-tenant chain
`APRAS-41 → APRAS-42 → APRAS-43 → APRAS-38`.

Baselines measured on `master` @ `86c038d` while writing this spec:
frontend `npm run test` = **101 files / 1020 tests passed**, 19.8 s.
Backend measured on the same commit: **1064 tests collected** by
`uv run pytest --collect-only -q`, ≥ 90 % coverage, single Alembic head
`0029_add_is_tenant_admin`.

---

## 1. Scope

The frontend half of multi-tenancy, plus one deliberately small backend
addition that the frontend cannot do without (§3).

**In scope**

1. A tenant switcher in the Navbar, listing the tenants the logged-in user may
   act in (all tenants for an `ADMINISTRATOR`, own memberships otherwise).
2. `X-Tenant-Id` attached to every request by the Axios client, read from a
   selection that survives a page reload.
3. Deterministic pre-selection at boot **plus a gate that keeps tenant-scoped
   queries from firing before that selection exists**, so a user with 2+
   memberships never hits the APRAS-42 `400 X-Tenant-Id header is required`
   ladder (§2.2, §4.10).
4. Eviction of every cached tenant-scoped payload on switch, so no row of the
   previous tenant can be rendered after the switch.
5. `tenant_admin` experience: `/admin/users` and its Navbar entry visible when
   the user holds the capability **in the acting tenant**, hidden when acting
   elsewhere, with the backend 403 already surfaced as a handled error.
6. `ADMINISTRATOR` global vision: every tenant in the dropdown, and switching
   into any of them shows that tenant's data.

**Not in scope** — see §8 for the full list with reasons. Headlines: no tenant
CRUD/membership-management UI, no invite flow, no per-component action-button
re-gating (task delete, lot delete, user-type buttons), no change to role
simulation, no change to the `/auth/me` `user_types` cross-tenant composition
(deferred residual, §2.4), no `/static/uploads` change (deferred residual,
§2.5).

---

## 2. Residuals handed to this slice

### 2.1 Source of truth for memberships and `is_tenant_admin` — **resolved**

What exists today (verified by reading the code, not the specs):

| Route | Scope | Returns |
|---|---|---|
| `GET /api/v1/auth/me` | global (`use_global_tenant_scope`) | `UserRead`: id, email, full_name, role, is_active, cpf, phone, address, `user_types`, computed `username`. **No memberships, no `is_tenant_admin`.** |
| `GET /api/v1/tenants` | global | `list[TenantRead]` = `{id, name, is_active, created_at, updated_at}`, **all** tenants for `ADMINISTRATOR`, own memberships otherwise, ordered by name. **No `is_tenant_admin`.** |
| `GET /api/v1/tenants/{id}/members` | global | `list[TenantMemberRead]`, which *does* carry `is_tenant_admin` — but it is the whole member roster of one tenant, one call per tenant. |

Decision, in two parts:

* **Dropdown options come from `GET /api/v1/tenants`.** It already implements
  exactly the required rule — global vision for `ADMINISTRATOR`, own
  memberships for everyone else — and it is a global route, so it can be
  called before any tenant is selected. No backend change.
* **The `is_tenant_admin` capability comes from `GET /api/v1/auth/me`**, which
  gains a `tenants` array of the caller's own memberships (§3). Rejected
  alternatives: putting a caller-relative `is_tenant_admin` on `TenantRead`
  (that schema is also the response of `POST`/`PATCH`/`GET {id}`, where a
  caller-relative field is a category error); and having the frontend call
  `GET /tenants/{id}/members` per tenant (N requests, and it hands a plain
  member the full roster of every tenant just to render a dropdown).

Two global GETs at boot, both already needed: `/auth/me` (already called by
`AuthContext`) and `/tenants` (new, `useQuery(["tenants"])`).

### 2.2 Bootstrap for multi-membership users (the APRAS-42 400) — **resolved**

Two parts: *when* the acting tenant is decided, and *what stops tenant-scoped
traffic until it is*. The second part is not free — it is a real code change
(§4.10), because the obvious argument that "nothing scoped can mount before
`user` is set" is **false in this codebase**:

* `Navbar.tsx:18-19` calls `useMenuAccess` **above** its
  `if (!isAuthenticated) return null;`.
* `ProtectedRoute.tsx:38` calls `useMenuAccess` **above** the `isLoading`
  spinner return (deliberately — rules of hooks).
* `useMenuAccess` → `useUserTypes` is a plain `useQuery` on the tenant-scoped
  `GET /user-types/` with **no `enabled` guard**, and returning `null` from the
  component does not cancel a query that has already subscribed.

Measured on `86c038d`: mounting the real `App` at `/dashboard` with a token in
`localStorage` and `apiClient.get` recording every URL produces
`["/user-types/","/auth/me"]` — the tenant-scoped request leaves **first**.
For a dual-membership user with no stored `actingTenantId` (the state on the
first load after this ships, and after every `logout()`, which clears it) that
request carries no `X-Tenant-Id`, the APRAS-42 resolver answers
`400 X-Tenant-Id header is required`, `useUserTypes` has no data,
`useMenuAccess` returns `false` for every key, the Navbar loses its links and
`/dashboard` renders `RestrictedAccessMessage` — with no refetch after
`setUser`, because the query is not stale, it is *errored*.

**Part 1 — when.** The acting tenant is resolved **synchronously inside
`AuthContext.fetchUser`, from the `/auth/me` response, before `setUser` is
called** (§4.4). So the invariant `user !== null ⇒ acting tenant decided`
holds, and `AuthContext.isLoading === false` marks the boundary: either the
boot fetch finished (tenant decided) or there is no token at all (nothing to
decide).

**Part 2 — what stops traffic.** `useUserTypes` — the *only* tenant-scoped
query in the app that can subscribe above an auth guard — gains
`enabled: useActingTenantReady()`, a one-line hook whose value is
`!useAuth().isLoading` (§4.10). Every other tenant-scoped query lives inside a
`ProtectedRoute` child and therefore already mounts only after the spinner
clears. The same probe with that gate in place produces `["/auth/me"]`: the
scoped request is no longer issued before the acting tenant is resolved. Pinned
by a test, ER 17.

The dropdown option list (`/tenants`) may arrive later; it only affects what is
*offered*, never what is *sent*.

**Part 3 — how React consumers observe the decision.** Writing the mirror before
`setUser` fixes *what is sent*; it does not by itself fix *what components see*.
If `TenantContext` copied the mirror into `useState` and re-synced it in an
effect, there would be exactly one commit in which `user` is set, `isLoading`
is false and `actingTenantId` is still the pre-boot value — and `ProtectedRoute`
would evaluate `requiredCapability` in that commit and redirect a `tenant_admin`
straight off `/admin/users` (children's passive effects flush before their
parents', so the `<Navigate>` commits before any provider-level re-sync could
run). That would fire on the first load after this ships and after every
`logout()`. §4.5 therefore makes the context value **be** the mirror, read
through `useSyncExternalStore`, so no commit can observe a divergence between
the header that would be sent and the capability that is judged. Pinned by
ER 18.

Pre-selection ladder, in order:

1. A stored `actingTenantId` that is one of the caller's **active**
   memberships → keep it.
2. A stored `actingTenantId` when `user.role === "ADMINISTRATOR"` → keep it
   (an administrator may legitimately act in a tenant they are not a member
   of; the backend validates it, and §4.5 reconciles it if it is stale).
3. Otherwise the **first active membership** in `/auth/me`'s `tenants`
   (ordered by tenant name server-side, so it is deterministic).
4. Otherwise **no header at all** — the zero-membership user keeps today's
   `_resolve_without_header` default-tenant fallback.

Step 4 covers two different users. A plain member with zero memberships stays
there permanently: `GET /tenants` returns `[]` for them, so nothing ever
selects a tenant on their behalf and the backend fallback keeps serving them.
A **zero-membership `ADMINISTRATOR`** is different — `GET /tenants` returns
*every* tenant to them — so the §4.5 reconciliation effect promotes them out of
step 4 by selecting the first option as soon as the list loads. That is the one
gesture-free selection this spec allows, and it is safe precisely because the
`enabled` gate above guarantees no scoped query ran under the null selection.

### 2.3 How the frontend learns `tenant_admin` and re-evaluates on switch — **resolved**

A **capability check**, not `requiredRoles`. `ProtectedRoute` gains a
`requiredCapability?: "admin"` prop backed by a new `useAdminCapability()`
hook that mirrors the backend's `deps.has_admin_capability`:
`user.role === ADMINISTRATOR || isTenantAdmin(actingTenantId)`. Because
`TenantContext` exposes the acting tenant as a `useSyncExternalStore` snapshot
of the `tenantState` mirror (§4.5), every consumer re-renders on a switch with
no extra plumbing, and — unlike a `useState` copy re-synced in an effect — no
commit can observe a capability computed from a stale acting tenant (§2.2
part 3). `requiredRoles` is kept for the ~15 routes that
are genuinely role-based; `requiredCapability` is added to exactly two routes
(§4.7).

The AuthContext/ProtectedRoute/useEffectiveIdentity split of APRAS-35 is
preserved verbatim: **route gating uses the real user**, **Navbar uses the
effective (possibly simulated) identity**. Two exported hooks, §4.6.

### 2.4 `/auth/me` `user_types` cross-tenant composition — **deferred, with the practical risk closed**

`/auth/me` is global and returns the caller's `user_types` from every tenant
(APRAS-42/43 named residual). Making it tenant-aware is a backend change with
no acting tenant to filter by, and is not attempted here.

The practical risk — a tenant-B UserType granting a menu while acting in
tenant A — is already closed by construction and must be **proved by a test**
(§6, `useMenuAccess.crossTenant.test.tsx`): `useMenuAccess` intersects
`userTypeIds` with the rows returned by `useUserTypes()`, and
`GET /api/v1/user-types/` is tenant-scoped, so a tenant-B id matches no row and
grants nothing.

The one *visible* remnant — the Navbar's identity block printing
`user.user_types.map(name).join(", ")` across tenants — is deferred (§8): the
fix would change the displayed text for existing `Navbar.test.tsx` fixtures
(one of which has a `user_types` entry with no `id` at all), and it is cosmetic.

### 2.5 `/static/uploads` static mount — **deferred**

Named by APRAS-42 as a backend residual (a static mount serves files with no
tenant check). No frontend surface of this task reads it, and fixing it means
routing uploads through an authenticated, tenant-scoped handler — a backend
task of its own. Explicitly out of scope.

---

## 3. Backend delta (the one non-trivial-to-avoid change)

Three files plus one new test module. No migration, no model change, no new
route, no change to any existing route's guard or path.

### 3.1 `backend/app/schemas/tenant.py`

```python
class TenantMembershipSummary(BaseModel):
    """One membership of the *calling* user, for `GET /api/v1/auth/me`."""

    tenant_id: UUID
    name: str
    is_active: bool
    is_tenant_admin: bool
```

Distinct from `TenantMemberRead` (which describes *another* user's membership
of a named tenant and carries their email/role) and from `TenantRead` (which
describes the tenant entity and must stay caller-independent).

### 3.2 `backend/app/services/tenant_service.py`

```python
@staticmethod
def list_memberships(session: Session, user: User) -> list[TenantMembershipSummary]
```

Joins `UserTenantLink` to `Tenant` for `user.id`, ordered by `Tenant.name`
(the same order as `list_tenants`, which is what makes "first membership"
deterministic in §2.2). Returns `[]` for a user with no memberships — never an
error, and **not** a synthesised default-tenant entry: a zero-membership user
must keep the backend's own fallback, not a client-invented one.
`UserTenantLink` is outside `TENANT_SCOPED_MODELS`, so this query is unaffected
by the ambient filter and works on a global route.

### 3.3 `backend/app/schemas/user.py`

```python
class UserMeRead(UserRead):
    """`GET /api/v1/auth/me` only: identity + the caller's own memberships."""

    tenants: list[TenantMembershipSummary] = []
```

Additive subclass, so `UserRead` — the response model of `/users/`,
`/auth/signup`, `/auth/dev-users` and every admin user route — is untouched
and the membership graph is not exposed through the user directory.

### 3.4 `backend/app/api/v1/endpoints/auth.py`

`read_user_me` gains `session: Annotated[Session, Depends(get_session)]` and
`response_model=UserMeRead`, returning
`UserMeRead(**UserRead.model_validate(current_user).model_dump(), tenants=TenantService.list_memberships(session, current_user))`
(exact construction is the implementer's; the JSON must be today's `/auth/me`
body plus `tenants`).

The route stays on `GLOBAL_SCOPED` and stays in
`tests/test_tenant_route_scope.py::GLOBAL_ROUTES` unchanged — adding a session
dependency does not add `get_current_tenant`, so that module needs **no edit**.

`GET /api/v1/auth/dev-users` stays `UserRead` and is **not** extended: it is a
development login list, not an identity source.

### 3.5 Backend tests — `backend/tests/test_auth_me_tenants.py` (new)

* `test_me_returns_single_membership` — a default-tenant user gets exactly one
  entry, `is_tenant_admin=False`.
* `test_me_returns_both_memberships_ordered_by_name` — a dual-membership user
  gets 2 entries in tenant-name order.
* `test_me_reports_is_tenant_admin_per_membership` — a user who is
  `is_tenant_admin` in A and a plain member of B gets `True` for A and `False`
  for B in one response.
* `test_me_returns_empty_tenants_for_user_without_memberships` — `[]`, 200.
* `test_me_keeps_existing_fields` — `email`, `role`, `user_types`, `username`
  unchanged from today's payload.
* `test_me_ignores_tenant_header` — sending `X-Tenant-Id` of tenant B while a
  member of A and B returns the same body (the route is global).

No other backend test module is modified.

---

## 4. Frontend design

### 4.1 Types — `src/types/auth.ts`

```ts
export interface TenantMembership {
  tenant_id: string;
  name: string;
  is_active: boolean;
  is_tenant_admin: boolean;
}

export interface Tenant {
  id: string;
  name: string;
  is_active: boolean;
}
```
and `User` gains `tenants?: TenantMembership[]` (optional, so every existing
`User` fixture in the 101 test files keeps type-checking).

### 4.2 `src/features/user-administration/context/tenantState.ts` (new)

A module-level mirror + storage helpers, following the existing
`simulationState.ts` pattern verbatim (React context cannot be read from the
Axios interceptor).

* Storage key `"actingTenantId"`, written to `localStorage` when the token is
  in `localStorage` and to `sessionStorage` otherwise — i.e. the selection
  lives exactly as long as the JWT it was chosen under.
* `getActingTenantId(): string | null` — returns the mirror, lazily
  initialised from `sessionStorage.getItem("actingTenantId") ?? localStorage.getItem("actingTenantId")`
  (the same precedence `client.ts` already uses for `accessToken`), so a page
  reload has the right header on the very first request.
* `setActingTenantId(id: string | null): void` — updates the mirror and the
  storage that currently holds the token; `null` clears both.
* `clearActingTenantId(): void` — clears mirror + both storages.
* `subscribeActingTenantId(listener: () => void): () => void` — registers a
  listener, returns its unsubscribe. **Every** mirror write
  (`setActingTenantId`, `clearActingTenantId`) notifies all listeners *after*
  the mirror and the storage have been updated, so a listener that calls
  `getActingTenantId()` synchronously observes the new value. This is the store
  half of the `useSyncExternalStore` in §4.5. Two constraints the implementer
  must respect: `subscribeActingTenantId` and `getActingTenantId` are
  module-level constants (stable identities across renders), and
  `getActingTenantId` returns the cached primitive `string | null` itself —
  never a freshly allocated wrapper object — or React re-subscribes on every
  render / loops on snapshot inequality.
* `resolveActingTenantId(memberships, role, stored)` — the pure §2.2 ladder,
  exported for direct unit testing.

### 4.3 `src/api/client.ts`

In the existing request interceptor, after the `Authorization` block:

```ts
const actingTenantId = getActingTenantId();
if (actingTenantId) {
  config.headers["X-Tenant-Id"] = actingTenantId;
}
```

Unconditional on the route: the header is inert on the global routes
(`/auth/*`, `/tenants*` do not declare it) and required on every scoped one.
CORS already allows it (`allow_headers=["*"]`). No response interceptor is
added — see §8.

### 4.4 `src/features/user-administration/context/AuthContext.tsx`

`fetchUser` becomes:

```ts
const response = await apiClient.get<User>("/auth/me");
setActingTenantId(
  resolveActingTenantId(response.data.tenants ?? [], response.data.role, getActingTenantId()),
);   // BEFORE setUser: closes the window in which a scoped query could fire headerless
setUser(response.data);
```

This ordering is **necessary but not sufficient** on its own — see §2.2 part 2
and §4.10 for the gate that makes it sufficient.

`logout` additionally calls `clearActingTenantId()`. The `catch` branch (bad
token) clears it too, alongside the tokens it already removes.

`AuthContextType` is otherwise unchanged — no new field, so
`AuthContext.test.tsx` and the ~20 modules that `vi.spyOn(AuthHook, "useAuth")`
keep compiling untouched.

### 4.5 `src/features/user-administration/context/TenantContext.tsx` (new)

```ts
interface TenantContextValue {
  tenants: Tenant[];          // dropdown options (active ones only)
  actingTenantId: string | null;
  actingTenant: Tenant | null;
  isActingTenantAdmin: boolean;
  isLoading: boolean;
  setActingTenant: (id: string) => void;
}
```

* Options:
  ```ts
  useQuery({
    queryKey: ["tenants"],
    queryFn: async () => (await apiClient.get<Tenant[]>("/tenants")).data,
    enabled: isAuthenticated,
  });
  ```
  Note the `.data` unwrap — `apiClient.get` resolves to an `AxiosResponse`, and
  caching the envelope instead of the array is the classic way to end up with
  `tenants.filter is not a function`.
  **`"/tenants"` with no trailing slash** — the route is mounted at `""`, and a
  trailing slash costs a 307.
  The query result is filtered to `is_active === true`: `_resolve_from_header`
  answers 403 "Tenant is inactive" for everyone including administrators, so an
  inactive tenant is never a selectable option.
* `isActingTenantAdmin` = `user?.tenants?.some(m => m.tenant_id === actingTenantId && m.is_tenant_admin) ?? false`.
  It is derived from `/auth/me`, so it is per-membership and re-evaluates on
  every switch for free.
* `actingTenantId` is **not** React state and is **not** synchronised by an
  effect. The provider reads it straight off the §4.2 mirror with
  `useSyncExternalStore` (from `react`; React 19 is in use):
  ```ts
  const actingTenantId = useSyncExternalStore(
    subscribeActingTenantId, // store subscription (§4.2)
    getActingTenantId,       // client snapshot
    getActingTenantId,       // server snapshot — same primitive, no SSR here
  );
  ```
  React re-reads `getSnapshot` during **every** render of the provider and
  re-renders it if the value differs from the committed snapshot, so the
  context value equals the mirror in **every** commit — including the commit
  in which `AuthContext` sets `user` and clears `isLoading`, because §4.4
  writes the mirror *before* `setUser`. There is therefore no commit in which
  `user` is set, `isLoading` is false and `actingTenantId` is still the
  pre-boot value, and the capability gate of §4.7 can never see a stale `null`
  and redirect a `tenant_admin` off `/admin/users` on a load with no stored
  selection (§2.2 part 3, ER 18). A `useState` + `useEffect(…, [user])`
  re-sync has exactly that one-commit lag and is rejected for it. The
  `subscribe` arm exists for the writes that do not originate from a React
  render at all: the switcher gesture below, and `clearActingTenantId()` in
  `logout`.
* `setActingTenant(id)` does exactly, **in this order**:
  1. `setActingTenantId(id)` — mirror + storage first, so any refetch triggered
     below already carries the new header. That write notifies the §4.2
     subscribers, which is what re-renders every `useTenant()` consumer: there
     is no second copy of the selection in React state, so nothing can disagree
     with the header the interceptor is about to send;
  2. **evict every cached tenant-scoped payload, but not `["tenants"]`**:
     ```ts
     queryClient.removeQueries({
       predicate: (query) => query.queryKey[0] !== "tenants",
     });
     ```
     Eviction, not `invalidateQueries`, because invalidation leaves the stale
     rows readable while the refetch is in flight and ER 7 forbids a stale row
     appearing at any point. Targeted, not a bare `queryClient.clear()`,
     because `clear()` also evicts `["tenants"]` — the dropdown's own option
     list — so the `<select>` would empty and re-render mid-gesture, dropping
     the switcher below the 2-option threshold of §4.8 and resetting its
     `value` while the refetch is in flight. `["tenants"]` is a global-route
     payload and is unaffected by the switch, so keeping it is also correct,
     not merely convenient. (Any equivalent that evicts every scoped key and
     preserves `["tenants"]` is acceptable; the observable in §6/ER 7 is what
     is being specified.)
* **Reconciliation effect**: once `tenants` has loaded and is non-empty, if
  `actingTenantId` is `null`, or is set but is not the id of any option, call
  `setActingTenant(firstOption.id)`. The `null` arm is the §2.2 step-4
  placeholder for a **zero-membership `ADMINISTRATOR`** (all tenants offered,
  none of them a membership); the mismatch arm recovers from a stored id
  pointing at a tenant that was deactivated or whose membership was revoked.
  A plain member with zero memberships has an empty option list, so neither arm
  fires and the backend fallback keeps serving them. This effect is the only
  place a selection changes without a user gesture, and it can only run after
  `/tenants` has answered — i.e. after `/auth/me`, so it never races the §4.10
  gate.
* `useTenant()` **returns a zero value** (`{tenants: [], actingTenantId: null,
  actingTenant: null, isActingTenantAdmin: false, isLoading: false,
  setActingTenant: noop}`) when no provider is mounted, instead of throwing
  like `useAuth` does. Deliberate, for two reasons: it is fail-closed (no
  provider ⇒ no capability ⇒ no admin UI), and it keeps every one of the
  existing `Navbar.test.tsx` / `ProtectedRoute*.test.tsx` renders — which mount
  components bare in a `MemoryRouter` — passing **unmodified**. Documented in a
  docstring on the hook.

`TenantProvider` is mounted in `App.tsx` **inside `AuthProvider`, outside
`SimulationProvider`/`BrowserRouter`**. It uses `useQueryClient`, which is
satisfied because `App` is always rendered inside a `QueryClientProvider`
(`main.tsx`, `App.test.tsx`, `AppRouting.smoke.test.tsx`).

### 4.6 `src/features/user-administration/context/useAdminCapability.ts` (new)

```ts
/** Real-identity capability: mirrors backend deps.has_admin_capability.
 *  Used by ProtectedRoute — route gating must never follow a simulated role
 *  (APRAS-35), so an administrator can always end a simulation. */
export const useAdminCapability = (): boolean =>
  user?.role === UserRole.ADMINISTRATOR || isActingTenantAdmin;

/** Simulation-aware capability, for menu visibility only. */
export const useEffectiveAdminCapability = (): boolean =>
  effectiveRole === UserRole.ADMINISTRATOR ||
  (!isSimulating && isActingTenantAdmin);
```

The `!isSimulating` guard keeps today's behaviour exactly: a real administrator
simulating `DIRECTOR` still sees no admin link.

### 4.7 `ProtectedRoute` and routes

`ProtectedRouteProps` gains `requiredCapability?: "admin"`. Semantics, added
after the existing `requiredRole`/`requiredRoles` checks:

* `requiredCapability` alone → allowed iff `useAdminCapability()`.
* `requiredCapability` **together with** `requiredRoles` → allowed iff
  `useAdminCapability() || requiredRoles.includes(user.role)` (an explicit OR;
  the existing `requiredRoles`-only branch must be skipped when
  `requiredCapability` is also present, otherwise the two AND together).
* Denial redirects to `/dashboard`, identical to `requiredRole` today.

`useAdminCapability()` reads `isActingTenantAdmin` from `useTenant()`, whose
`actingTenantId` is the `useSyncExternalStore` snapshot of §4.5. So in any
commit where `ProtectedRoute` evaluates `requiredCapability`, the acting tenant
it judges against is exactly the value the Axios interceptor would put on the
wire at that instant. Consequently **no third "acting tenant not yet synced"
state is added to `ProtectedRoute`**: the lag that would have required one does
not exist. `ProtectedRoute` keeps exactly its two pre-existing early returns
ahead of the capability check — the `isLoading` spinner and the
`!isAuthenticated` redirect — and `useActingTenantReady()` (§4.10) stays what it
is today, a query gate, not a routing gate.

`App.tsx` route changes — exactly two:

| Route | Before | After |
|---|---|---|
| `/admin/users` | `requiredRole={UserRole.ADMINISTRATOR}` | `requiredCapability="admin"` |
| `/users/contact-info` | `requiredRoles={[ADMINISTRATOR, MANAGER]}` | `requiredRoles={[UserRole.MANAGER]} requiredCapability="admin"` |

Both are strict supersets of today's access (an `ADMINISTRATOR` passes via the
capability; a `MANAGER` via the role), so no existing routing test changes
meaning. They are the two UI surfaces of the seven tenant-scoped admin routes
APRAS-43 opened to a tenant_admin (users list/patch, contact-info).

### 4.8 `Navbar.tsx`

* **Switcher.** Rendered in the right-hand cluster, immediately before
  `SimulationControls`, **only when `tenants.length >= 2`**. A native
  `<select>` (not Radix) with `aria-label={t("tenant.switcherLabel")}`, one
  `<option value={t.id}>{t.name}</option>` per option, `value={actingTenantId ?? ""}`,
  `onChange={e => setActingTenant(e.target.value)}`. Native, because it gives a
  stable `getByRole("combobox")` / `selectOptions` surface in jsdom, where
  Radix Select needs pointer-event shims.

  `tenants.length >= 2` is the **only** render condition, and the Navbar has
  exactly two states: switcher, or nothing. With one option the control is not
  rendered and that tenant is already the pre-selection (§2.2 step 3) —
  "defaults sanely when the user has exactly one tenant". With **zero** options
  the Navbar renders nothing either — no message, no placeholder, no
  `tenant.noAccess`. That is deliberate: `tenants.length === 0` is not only the
  rare zero-membership state, it is also the state of every bare
  `Navbar.test.tsx` / `ProtectedRoute*.test.tsx` render (the zero-value
  `useTenant` of §4.5 returns `[]`) and of `AppRouting.smoke.test.tsx` (its
  `/tenants` query rejects). Rendering anything at all in that state would put
  new text into pre-existing snapshots and `getByText` scans and break the
  hard constraint of ER 15. Consequently `tenant.noAccess` does **not** exist
  (§5).
* **Admin entry.** `{effectiveRole === UserRole.ADMINISTRATOR && ...}` around
  the `/admin/users` link becomes `{hasEffectiveAdminCapability && ...}`.
* **Contact-info entry.** `(effectiveRole === ADMINISTRATOR || effectiveRole === MANAGER)`
  becomes `(hasEffectiveAdminCapability || effectiveRole === UserRole.MANAGER)`.
* Nothing else in the Navbar changes — no other link's condition, no
  `SimulationControls` gating (still `user?.role === ADMINISTRATOR`, §8).

### 4.9 403 handling

`AdminUserDashboard` already renders `t("admin.errorLoadingUsers")` when its
`useUsers()` query errors (`AdminUserDashboard.tsx`, the `if (error)` branch),
so a backend 403 after a switch into a tenant where the capability is absent is
already a handled error, not a crash. No code change; §6 adds the test that
pins it. No global Axios response interceptor is introduced — a 403 must not
log the user out or auto-switch tenants (§8).

### 4.10 Gating tenant-scoped queries on the resolved acting tenant

The mechanism promised by §2.2 part 2. **One** mechanism is specified, not a
menu of them:

`src/features/user-administration/context/TenantContext.tsx` exports

```ts
/** True once the acting tenant for the current identity is decided:
 *  AuthContext resolves it from /auth/me *before* setUser (§4.4), so
 *  `!isLoading` means either "boot finished, tenant decided" or "no token,
 *  nothing to decide". Gates every tenant-scoped query that can subscribe
 *  above an auth guard (§2.2). */
export const useActingTenantReady = (): boolean => !useAuth().isLoading;
```

and `src/hooks/useUserTypes.ts` becomes

```ts
export const useUserTypes = () => {
  const isReady = useActingTenantReady();
  return useQuery({
    queryKey: ["user-types"],
    enabled: isReady,
    queryFn: async () => (await apiClient.get<UserType[]>("/user-types/")).data,
  });
};
```

Rejected alternatives, for the record: **deferring inside the Axios request
interceptor** (turns a synchronous interceptor into an awaited one for every
request in the app, and a promise that must never deadlock on the logged-out
path — far more blast radius than one `enabled`); **AuthContext ordering
alone** (already in §4.4, and empirically insufficient — the probe in §2.2
shows the request leaving before `/auth/me`); **an `enabled` on every scoped
hook** (~30 modules, and unnecessary: the rest are already behind the
`ProtectedRoute` spinner).

Three consequences to be explicit about:

1. `useUserTypes` now calls `useAuth()`, so it requires an `AuthProvider`
   above it. Verified against the whole suite: with this exact change applied
   to `useUserTypes.ts` on `86c038d`, `npm run test` is **101 files / 1020
   tests passed** — no pre-existing test renders a `useUserTypes` consumer
   outside an `AuthProvider` without mocking the hook module.
2. **`useMenuAccess.test.tsx` does not change and does not need to.** It
   `vi.mock`s `"../../../hooks/useUserTypes"` wholesale (line 17), as do
   `Navbar.test.tsx` (line 29), `ProtectedRoute.test.tsx` (line 24) and
   `useEffectiveIdentity.test.tsx` (line 17). The gate lives *inside* the
   mocked module, so it is invisible to every one of them. ER 15's
   "passes unmodified" therefore stands; `useUserTypes.ts` is a **source**
   file, and its change is named in ER 15 so the two ERs cannot be read as
   contradicting each other.
3. While `isLoading` is true the hook returns `data: undefined`, exactly as it
   does today before the request resolves — `useMenuAccess` already handles
   that (`if (!userTypes) return false`), and `ProtectedRoute` never reaches
   the `hasMenuAccess` branch during `isLoading` because the spinner returns
   first. When the gate opens, TanStack Query fetches, and the header is
   already on the request because §4.4 wrote the mirror before `setUser`.

---

## 5. i18n

**Exactly one** new key, in both `src/i18n/locales/pt.json` and `en.json`,
under a new top-level `tenant` object:

| key | pt | en |
|---|---|---|
| `tenant.switcherLabel` | `Condomínio` | `Building` |

There is deliberately **no `tenant.noAccess`**. An earlier draft had one as a
fallback for "authenticated user, zero tenants", but per §4.8 the Navbar
renders *nothing* in that state — and that state is the one every bare
pre-existing Navbar/`ProtectedRoute` test and the routing smoke test render in,
so any string there would be new text inside those trees. A key nothing renders
is dead weight, so it is not added. No other locale key is added, renamed or
removed.

---

## 6. Test plan (all new files unless stated)

**Frontend**

1. `src/api/__tests__/client.tenantHeader.test.ts`
   * `attaches X-Tenant-Id from the acting-tenant mirror`
   * `omits X-Tenant-Id when no acting tenant is set`
   * `keeps the Authorization header alongside X-Tenant-Id`
2. `src/features/user-administration/__tests__/tenantState.test.ts`
   * `persists the selection in localStorage when the token is in localStorage`
   * `persists the selection in sessionStorage when the token is in sessionStorage`
   * `restores the selection from storage on a fresh module read (page reload)`
   * `resolveActingTenantId keeps a stored id that is an active membership`
   * `resolveActingTenantId falls back to the first active membership for a multi-membership user`
   * `resolveActingTenantId keeps a stored non-membership id for an ADMINISTRATOR`
   * `resolveActingTenantId returns null for a user with no memberships`
3. `src/features/user-administration/__tests__/TenantContext.test.tsx`
   * `lists every tenant returned by GET /tenants for an ADMINISTRATOR`
   * `filters inactive tenants out of the options`
   * `reports isActingTenantAdmin only for the acting membership`
   * `reconciles a stored tenant id that is no longer an option`
   * `useTenant returns the fail-closed zero value without a provider`
4. `src/features/user-administration/__tests__/TenantSwitcher.test.tsx`
   * `renders the switcher with one option per tenant for a two-tenant user`
   * `does not render the switcher for a single-tenant user`
   * `renders no switcher and no message for a user with zero tenants`
     (asserts `queryByRole("combobox", {name: /condom/i})` is null and that the
     Navbar's rendered text is unchanged from the single-tenant case)
   * `defines tenant.switcherLabel in both pt and en, and defines no tenant.noAccess`
5. `src/features/user-administration/__tests__/TenantSwitch.integration.test.tsx`
   — Navbar + `TaskDashboard` under a real `TenantProvider` and
   `QueryClientProvider`, with `apiClient.get` mocked to answer `/tasks/`
   **from `getActingTenantId()`** (tenant A ⇒ `Tarefa A`, tenant B ⇒
   `Tarefa B`); combined with test 1 this proves the header the backend
   receives.
   * `shows only the acting tenant's tasks after switching, with no stale rows`
     — asserts `Tarefa A` present / `Tarefa B` absent, `selectOptions` the
     other tenant, then `findByText("Tarefa B")` **and**
     `expect(queryByText("Tarefa A")).toBeNull()`.
   * `an ADMINISTRATOR can switch into a tenant they are not a member of and sees its data`
     (global vision).
6. `src/features/user-administration/__tests__/useAdminCapability.test.tsx`
   * `grants the capability to a global ADMINISTRATOR in any tenant`
   * `grants it to a tenant_admin only in the tenant that granted it`
   * `withholds the effective capability while a simulation is active`
7. `src/features/user-administration/__tests__/ProtectedRoute.capability.test.tsx`
   * `renders /admin/users for a tenant_admin acting in the granting tenant`
   * `redirects a tenant_admin acting in another tenant to /dashboard`
   * `still renders /admin/users for a global ADMINISTRATOR`
   * `requiredCapability ORs with requiredRoles (MANAGER passes contact-info without the capability)`
8. `src/features/user-administration/__tests__/Navbar.tenantAdmin.test.tsx`
   * `shows the Administração entry to a tenant_admin acting in the granting tenant`
   * `hides it when the same user acts in the other tenant`
9. `src/features/user-administration/__tests__/AdminUserDashboard.forbidden.test.tsx`
   * `renders the error message and does not crash when /users/ returns 403`
10. `src/features/user-administration/__tests__/useMenuAccess.crossTenant.test.tsx`
    (§2.4) * `a UserType from another tenant grants no menu in the acting tenant`
11. `src/__tests__/TenantBootstrapOrder.test.tsx` (§2.2 / §4.5 / §4.10) —
    mounts the **real `App`** with a token in `localStorage` and **nothing**
    stored under `actingTenantId` in either storage, mocking only
    `src/api/client`, whose `get` records
    `{url, actingTenantId: getActingTenantId()}` for every call, answers
    `/tenants` with tenants A and B, and answers `/auth/me` with the per-case
    fixture below. Three cases; the first two mount at `/dashboard`, the third
    at `/admin/users`.
    * `issues no tenant-scoped request before the acting tenant is resolved` —
      fixture: a **dual-membership** user (tenants A and B). Asserts the
      **first** recorded URL is `/auth/me`, and that **every** recorded call to
      a tenant-scoped path (`/user-types/`, and anything not in
      `["/auth/me", "/auth/dev-users", "/tenants"]`) has a non-null
      `actingTenantId` at the moment it was issued. On `86c038d` without the
      §4.10 gate this test fails with a first URL of `/user-types/` and a null
      `actingTenantId` — verified by running exactly that probe.
    * `renders the dashboard links for a dual-membership user on first load` —
      the regression the gate exists for. So that it cannot pass vacuously, the
      fixture is a **non-`ADMINISTRATOR`** (a `RESIDENT` whose single
      `user_types` entry is what grants the `tasks` menu, so the link genuinely
      depends on `useUserTypes` returning rows), and the mocked client
      **rejects `/user-types/` with a 400 whenever `getActingTenantId()` is
      `null` at call time** — the APRAS-42 header ladder reproduced in the
      mock. Asserts the `nav.tasks` link is present and
      `common.restrictedAccess` absent; without the §4.10 gate the request
      leaves headerless, is rejected, and this fails.
    * `renders /admin/users for a tenant_admin with no stored acting tenant` —
      the §2.2 part 3 / §4.5 regression. Fixture: a **non-`ADMINISTRATOR`**
      user with a single membership in tenant A carrying
      `is_tenant_admin: true`, and no stored `actingTenantId`, mounted at
      `/admin/users`. Asserts `AdminUserDashboard` renders, and that the router
      **never** reaches `/dashboard` — the harness registers a sentinel element
      on the `/dashboard` route and asserts it never appears at any point, so a
      redirect that happened and was later undone still fails the test. With
      the rejected `useState` + `useEffect` design this fails on the one-commit
      lag; with the `useSyncExternalStore` of §4.5 no such commit exists.

Frontend total: **11 new files, 35 named cases**.

**Pre-existing modules that must keep passing unmodified** (the zero-value
`useTenant` of §4.5, the zero-render Navbar of §4.8 and the fact that all four
of them `vi.mock` the `useUserTypes` module are what buy this): `Navbar.test.tsx`,
`ProtectedRoute.test.tsx`, `ProtectedRoute.guestWelcome.test.tsx`,
`ProtectedRoute.porteiroGate.test.tsx`,
`ProtectedRoute.porteiroRouteGating.test.tsx`, `AuthContext.test.tsx`,
`AdminUserDashboard.test.tsx`, `useEffectiveIdentity.test.tsx`,
`useMenuAccess.test.tsx`, `client.test.ts`, `App.test.tsx` and — the hard
constraint — `src/__tests__/AppRouting.smoke.test.tsx`, which mocks **only**
`src/api/client` (all verbs rejecting) and must still reach the real login,
signup, forgot-password and reset-password forms with `TenantProvider` mounted
and its `/tenants` query failing.

If any of these must change, the change must be named in the PR description
with its reason; none is anticipated. Measured: applying the §4.10 `enabled`
gate to `useUserTypes.ts` on `86c038d` and running `npm run test` gives
101 files / 1020 tests passed, unchanged from baseline.

**Backend**: `backend/tests/test_auth_me_tenants.py` only (§3.5).

---

## 7. Expected Results

- [ ] `GET /api/v1/auth/me` returns today's body plus a `tenants` array of the
      caller's own memberships — `{tenant_id, name, is_active, is_tenant_admin}`,
      ordered by tenant name; a dual-membership user who is `is_tenant_admin`
      in A and a plain member of B gets `true` for A and `false` for B in one
      response, and a user with no memberships gets `[]` with status 200
      (`backend/tests/test_auth_me_tenants.py`, all 6 cases).
- [ ] `UserRead` is unchanged: `GET /api/v1/users/`, `POST /api/v1/auth/signup`
      and `GET /api/v1/auth/dev-users` responses contain **no** `tenants` key,
      and `backend/tests/test_tenant_route_scope.py` passes unmodified with
      `("GET", "/api/v1/auth/me")` still in `GLOBAL_ROUTES`.
- [ ] The Axios request interceptor (`frontend/src/api/client.ts`) sets
      `X-Tenant-Id` to the stored acting tenant on every request and omits it
      when none is set, without disturbing `Authorization`
      (`src/api/__tests__/client.tenantHeader.test.ts`, 3 cases; existing
      `client.test.ts` passes unmodified).
- [ ] The selection survives a page reload: it is written to `localStorage`
      when the JWT is in `localStorage` and to `sessionStorage` otherwise under
      the key `actingTenantId`, and a fresh read of `tenantState` picks it up
      before the first request (`tenantState.test.ts`, 3 persistence cases).
- [ ] Pre-selection is deterministic and never leaves a multi-membership user
      headerless: `resolveActingTenantId` keeps a valid stored id, otherwise
      picks the first active membership, keeps a stored non-membership id for
      an `ADMINISTRATOR`, and returns `null` only for a user with zero
      memberships (`tenantState.test.ts`, 4 ladder cases); `AuthContext`
      applies it before `setUser`.
- [ ] The Navbar renders a tenant `<select>` labelled `tenant.switcherLabel`
      with exactly one option per active tenant when, and only when, the user
      has 2+ options: with exactly 1 option it renders no switcher, and with 0
      options it renders **neither a switcher nor any message** — no
      `tenant.noAccess`, no placeholder, no added text
      (`TenantSwitcher.test.tsx`, 3 render cases).
- [ ] Switching tenant swaps the dashboard task list with no stale row:
      `TenantSwitch.integration.test.tsx::"shows only the acting tenant's tasks
      after switching, with no stale rows"` asserts `Tarefa A` visible then,
      after `selectOptions` on the switcher, `Tarefa B` visible **and**
      `queryByText("Tarefa A") === null`.
- [ ] An `ADMINISTRATOR`'s dropdown lists every tenant returned by
      `GET /api/v1/tenants` (including tenants they are not a member of, minus
      inactive ones) and switching into one shows that tenant's data
      (`TenantContext.test.tsx::"lists every tenant … for an ADMINISTRATOR"`,
      `…::"filters inactive tenants out of the options"`,
      `TenantSwitch.integration.test.tsx::"an ADMINISTRATOR can switch into a
      tenant they are not a member of and sees its data"`).
- [ ] `useAdminCapability()` mirrors `deps.has_admin_capability`: true for a
      global `ADMINISTRATOR` in any tenant, true for a tenant_admin only in the
      granting tenant, and the effective variant is false while a simulation is
      active (`useAdminCapability.test.tsx`, 3 cases).
- [ ] Route + menu gating follows the capability, per tenant: with
      `/admin/users` on `requiredCapability="admin"`, a tenant_admin acting in
      the granting tenant renders `AdminUserDashboard` and sees the
      `nav.administration` entry; the same user acting in the other tenant is
      redirected to `/dashboard` and the entry is gone; a global
      `ADMINISTRATOR` still renders it
      (`ProtectedRoute.capability.test.tsx` 3 cases,
      `Navbar.tenantAdmin.test.tsx` 2 cases).
- [ ] `requiredCapability` ORs with `requiredRoles`: on
      `/users/contact-info`, a `MANAGER` without the capability still renders
      the page (`ProtectedRoute.capability.test.tsx::"requiredCapability ORs
      with requiredRoles"`).
- [ ] A forced `403` from `GET /api/v1/users/` renders
      `t("admin.errorLoadingUsers")` and throws no uncaught error
      (`AdminUserDashboard.forbidden.test.tsx`).
- [ ] A `UserType` belonging to another tenant grants no menu in the acting
      tenant (`useMenuAccess.crossTenant.test.tsx`), closing the practical risk
      of the deferred `/auth/me` `user_types` residual.
- [ ] `tenant.switcherLabel` exists in both `src/i18n/locales/pt.json` and
      `src/i18n/locales/en.json`, and `tenant.noAccess` exists in **neither**,
      asserted by `TenantSwitcher.test.tsx::"defines tenant.switcherLabel in
      both pt and en, and defines no tenant.noAccess"`; no existing key is
      renamed or removed.
- [ ] `frontend/src/__tests__/AppRouting.smoke.test.tsx` passes **unmodified**
      with `TenantProvider` mounted (it mocks only `src/api/client`, so the
      `/tenants` query rejects and the Navbar renders no switcher and no
      message), and so do `Navbar.test.tsx`, `ProtectedRoute*.test.tsx`,
      `AuthContext.test.tsx`, `AdminUserDashboard.test.tsx`,
      `useEffectiveIdentity.test.tsx`, `useMenuAccess.test.tsx`,
      `client.test.ts` and `App.test.tsx` — including across the §4.10 change
      to the **source** file `src/hooks/useUserTypes.ts`, which is invisible to
      the four of them that `vi.mock` that module. `useUserTypes.ts`,
      `client.ts`, `AuthContext.tsx`, `ProtectedRoute.tsx`, `Navbar.tsx` and
      `App.tsx` are the six pre-existing source files this task edits; no
      pre-existing **test** module changes, and any that does is named in the
      PR description with its reason.
- [ ] Full pipeline green: `npm run test:coverage` passes the 80/78/76/80
      gates with **at least 112 files / 1055 tests** passed (baseline measured
      on `86c038d`: 101 files / 1020 tests; this task adds 11 files and 35
      named cases); `npm run build` (`tsc -b && vite build`) succeeds;
      `npm run lint` reports **no more than the baseline measured on `86c038d`:
      467 problems (465 errors, 2 warnings)**, and none of them in a file this
      task creates; `uv run pytest` is green with ≥ 90 % coverage and at least
      **1070** passed (baseline measured on `86c038d` with
      `uv run pytest --collect-only -q`: **1064 collected**, plus the 6 cases
      of §3.5); `ruff check` is clean; `alembic heads` still reports the single
      head `0029_add_is_tenant_admin` with no new migration.
- [ ] No tenant-scoped request is issued before the acting tenant is resolved:
      with the real `App` mounted at `/dashboard` for a **dual-membership,
      non-`ADMINISTRATOR`** user holding a stored token and **no** stored
      `actingTenantId`, the first request is `GET /auth/me` and every request
      to a tenant-scoped path (`/user-types/` included) is issued with a
      non-null acting tenant; and with the mocked client **rejecting
      `/user-types/` with a 400 whenever the acting tenant is null at call
      time**, that user's dashboard still renders the `nav.tasks` link rather
      than `common.restrictedAccess`
      (`src/__tests__/TenantBootstrapOrder.test.tsx`, first 2 cases). The gate
      is `enabled: useActingTenantReady()` on `useUserTypes` (§4.10); on
      `86c038d` without it the same probe records
      `["/user-types/","/auth/me"]`.
- [ ] The capability gate never observes a stale acting tenant at boot: the
      real `App` mounted at **`/admin/users`** for a **non-`ADMINISTRATOR`**
      user who is `is_tenant_admin` in tenant A, holding a stored token and
      **no** stored `actingTenantId`, renders `AdminUserDashboard` and
      **never** navigates to `/dashboard` (a sentinel rendered by the
      `/dashboard` route is asserted never to appear at any point)
      (`src/__tests__/TenantBootstrapOrder.test.tsx`, third case). The
      mechanism is `TenantContext` reading `actingTenantId` through
      `useSyncExternalStore(subscribeActingTenantId, getActingTenantId,
      getActingTenantId)` over the `tenantState` mirror (§4.2, §4.5), so the
      context value **is** the mirror in every commit and no
      `useState`/`useEffect` re-sync lag exists.

---

## 8. Out of Scope / Non-goals

- **Tenant and membership management UI.** No create/rename/deactivate tenant
  screen, no add/remove member, no grant/revoke `is_tenant_admin` UI — those
  routes are `ADMINISTRATOR`-only and deserve their own task and spec.
- **Invite / cross-tenant signup.** `POST /auth/signup` still links to the
  default tenant only (APRAS-42 §8.1).
- **`/auth/me` `user_types` tenant filtering** — deferred backend residual
  (§2.4); its practical risk is pinned by a test instead.
- **Filtering the Navbar's displayed UserType names to the acting tenant** —
  cosmetic remnant of the same residual, deferred because it would change the
  rendered text of existing `Navbar.test.tsx` fixtures (§2.4).
- **`/static/uploads`** — deferred backend residual (§2.5).
- **Per-component action-button re-gating for a tenant_admin**: task delete,
  lot delete, and the UserType create/patch/delete controls inside
  `AdminUserDashboard` keep their current role conditions. The backend enforces
  the capability on all seven routes, and a mismatch surfaces as a handled
  error (§4.9). Widening them is a follow-up.
- **Role simulation is unchanged**: `SimulationControls` stays gated on
  `user?.role === ADMINISTRATOR`. Letting a tenant_admin simulate roles inside
  their tenant is a separate decision.
- **No global Axios response interceptor** for 401/403, no auto-logout, no
  auto-switch on 403. A 403 from a scoped route is data, not a session event;
  turning it into a redirect would make the tenant_admin gating unreviewable.
- **No tenant branding, theming, per-tenant settings, subdomain/host-based
  resolution, or tenant-aware cache keys.** Cache correctness is achieved by
  eviction on switch (§4.5), not by keying every query on the tenant id —
  which would mean touching ~30 hook modules.
- **Query-cache eviction on login/logout.** `setActingTenant` evicts scoped
  queries (§4.5); `logout()` does not, exactly as today. A second user logging
  in within the same SPA session can therefore see the previous user's cached
  rows for the instant before TanStack Query refetches on mount. That is
  pre-existing behaviour, unchanged in either direction by this task, and
  fixing it means deciding what `login` should do to the cache — its own task.
- **Gating tenant-scoped queries other than `useUserTypes`.** Every other
  scoped hook mounts inside a `ProtectedRoute` child, i.e. after the spinner
  and after `user` is set, so it needs no `enabled` (§4.10). If a future
  component calls a scoped hook above an auth guard it must add the same gate;
  this task does not add a lint rule or an abstraction to enforce that.
- **No backend guard, route, model or migration change** beyond §3.
