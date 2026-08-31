# APRAS-42 — Enforce request-scoped tenant resolution and per-tenant query isolation across the backend

Second slice of the multi-tenant chain `APRAS-41 → APRAS-42 → APRAS-43 → APRAS-38`.
APRAS-41 (commit `6628ffb`) shipped the data layer: `Tenant`, `UserTenantLink`, a NOT NULL
`tenant_id` on 27 directly-scoped tables (20 child tables inherit through their parent),
tenant-composite uniques, and admin-only `/api/v1/tenants`. Today **every write still lands
in the default tenant and no read is filtered**.

This slice adds the two halves that make the boundary real:

1. **Resolution** — an *acting tenant* per request, derived server-side.
2. **Isolation** — every read filtered by, and every write stamped with, that acting tenant.

The failure mode this slice exists to kill is precise: *a query that forgets its tenant
filter silently returns another condominium's data*. The design below therefore refuses to
rely on 22 service files each remembering to pass a `tenant_id`. Enforcement is **central
and default-on**; the per-file work is limited to the handful of queries that provably
cannot be reached by the central mechanism, and each one of those is enumerated in §6.

---

## 1. Scope

**In scope**

1. `get_current_tenant` in `backend/app/api/deps.py` — the `X-Tenant-Id` header, its
   fallbacks, and its 400/403/404 semantics (§3).
2. `backend/app/core/tenant_context.py` — the session-level read filter, the write stamp,
   and the fail-closed guard (§4).
3. A classification of all 189 routes into *tenant-scoped* and *global*, applied at
   `include_router` level in `backend/app/api/v1/api.py` and asserted by a test that walks
   `app.routes` (§5).
4. The named query fixes for inherited (child) tables and for the seven queries that read a
   child table with no scoped entity in the statement — including the two `FacialTemplate`
   sites that leak across tenants today (§6.1, §6.2, §6.4).
5. Per-tenant role-linked `UserType` seeding on `POST /api/v1/tenants`, and making
   `get_effective_user_type_ids` tenant-aware **without changing its signature** (§7).
6. Signup / dev-login / seed-script compatibility (§8).
7. `backend/tests/test_tenant_isolation.py` (+ two small sibling modules) automating the
   cross-tenant matrix (§9).

**Explicitly NOT in scope** — see §11 for the full list. Headlines: no `is_tenant_admin`
and no per-tenant RBAC (APRAS-43); no frontend work of any kind (APRAS-38); no new Alembic
migration; no change to which users a tenant's administrator can *see* (`GET /api/v1/users`
stays global — §5.3, a named residual).

---

## 2. The mechanism in one paragraph

Every route is classified once, at router-include time. A tenant-scoped route depends on
`get_current_tenant`, which resolves the acting tenant and writes it into
`session.info["acting_tenant_id"]`. Two SQLAlchemy session events do the rest, for all 27
scoped models at once:

* `do_orm_execute` appends a `with_loader_criteria(Model, Model.tenant_id == acting)`
  option per scoped model, so **SELECTs, `Session.get()`, aggregates, joins and ORM-enabled
  UPDATE/DELETE are all filtered** (measured — §4.4).
* `before_flush` **overwrites** `tenant_id` on every pending scoped instance with the acting
  tenant, so a create can neither forget the stamp nor honour a forged one.

A session with no `acting_tenant_id` in `session.info` behaves exactly as it does today —
which is what keeps the ~70 existing test modules, `app/seed.py` and Alembic working
untouched. To stop that "no key = no filter" property from becoming a silent leak on a
route someone forgets to classify, sessions created by the request dependency
`get_session` are additionally marked `request_scoped`, and a *request-scoped* session that
queries a scoped model before its scope is resolved raises (§4.3) — and a static test over
`app.routes` catches the same mistake in CI, before it can ever run (§5.2).

---

## 3. Resolution — `get_current_tenant`

New dependency in `backend/app/api/deps.py`:

```python
TENANT_HEADER = "X-Tenant-Id"

def get_current_tenant(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    x_tenant_id: Annotated[str | None, Header(alias=TENANT_HEADER)] = None,
) -> Tenant:
```

It returns a `Tenant`, and as its *only* side effect calls
`tenant_context.set_acting_tenant(session, tenant.id)`.

### 3.1 Header present

| Condition | Result |
|---|---|
| value is not a valid UUID (or empty string) | **400** `"Invalid X-Tenant-Id header"` |
| tenant id unknown, caller is `ADMINISTRATOR` | **404** `"Tenant not found"` |
| tenant id unknown, caller is any other role | **403** `"Not a member of the requested tenant"` (never confirm existence) |
| tenant exists but `is_active is False` | **403** `"Tenant is inactive"` — for every role, including `ADMINISTRATOR`. This is the first consumer of the flag APRAS-41 defined and deliberately left inert |
| caller is `ADMINISTRATOR` | **200**, acting tenant = requested tenant (global vision; no membership needed) |
| caller has a `UserTenantLink` to the tenant | **200**, acting tenant = requested tenant |
| otherwise | **403** `"Not a member of the requested tenant"` |

### 3.2 Header absent — the backward-compatibility ladder

The frontend does not send the header until APRAS-38, and no existing test does either.
Hard-400ing a missing header would break every current caller, so **400 is reserved for
genuine ambiguity**:

| Caller's memberships | Result |
|---|---|
| exactly one | that tenant (**200**) |
| zero | the **default tenant** `00000000-0000-0000-0000-000000000001` (**200**). If that row is missing or inactive → **400** `"X-Tenant-Id header is required"` |
| two or more | **400** `"X-Tenant-Id header is required: user belongs to multiple tenants"` |

Consequences, all intended and all checkable:

* **Production / dev today**: migration `0028` gave every existing user exactly one
  membership (the default tenant), so *every* existing caller lands on branch one and the
  API behaves exactly as it does now.
* **Existing tests**: fixtures build `User` rows directly with no `UserTenantLink`, so they
  land on branch two — the default tenant — where all their data already lives. No existing
  test module needs to learn that tenants exist.
* **Multi-membership** only arises when an administrator explicitly links a user to a second
  tenant (`POST /tenants/{id}/members`, APRAS-41). Such a user must send the header; that is
  precisely what APRAS-38 will do, and 400 with an actionable message is the correct answer
  in the interim.
* The rule is uniform across roles. An `ADMINISTRATOR` without a header gets the same
  ladder; global vision is a property of *sending a header*, not of skipping it.

### 3.3 Two sibling dependencies

* `use_global_tenant_scope(session)` — marks the session resolved with **no** acting tenant.
  Used by the global routes of §5.3 so the §4.3 guard does not fire on them.
* `use_default_tenant_scope(session)` — sets the acting tenant to `DEFAULT_TENANT_ID`
  without consulting a user. Used by `POST /api/v1/auth/signup` only (§8.1).

---

## 4. Isolation — `backend/app/core/tenant_context.py`

A new module (deliberately *not* `app/db.py`, which `[tool.coverage.run] omit` excludes from
coverage — this code must be covered). `app/db.py` imports it so the listeners register
whenever anything imports the session dependency.

### 4.1 The scoped-model registry is derived, not written by hand

```python
def _discover_scoped_models() -> tuple[type[SQLModel], ...]:
    return tuple(
        m.class_ for m in SQLModel._sa_registry.mappers
        if "tenant_id" in m.local_table.c and m.class_ is not UserTenantLink
    )

TENANT_SCOPED_MODELS = _discover_scoped_models()
```

Verified: this returns exactly **27** classes today, matching APRAS-41's `_TENANT_SCOPED_TABLES`
(28 tables carry `tenant_id`; `user_tenant_link` is the membership table, not a scoped
entity). Deriving it means a table added by a future task is filtered the day it gets a
`tenant_id`, with nobody having to remember a list. A test asserts
`{m.__tablename__ for m in TENANT_SCOPED_MODELS} == set(_TENANT_SCOPED_TABLES)` so the two
sources can never drift.

### 4.2 Read filter

```python
@event.listens_for(Session, "do_orm_execute")
def _apply_tenant_filter(state):
    if state.is_column_load or state.is_relationship_load:
        return
    tenant_id = state.session.info.get(ACTING_TENANT_KEY)
    if tenant_id is not None:
        state.statement = state.statement.options(*_options_for(tenant_id))
```

`_options_for` memoises the 27 `with_loader_criteria(model, model.tenant_id == tenant_id,
include_aliases=True)` options per tenant id in a module-level dict; rebuilding them per
query costs 0.48 ms vs 0.24 ms memoised vs 0.06 ms unfiltered on the sqlite bench
(§4.4) — the memoised form is required, the numbers are recorded so a reviewer can
re-measure.

Measured behaviour of this listener against the real models (evidence in the task report):

| Query form | Filtered? |
|---|---|
| `session.exec(select(Task))` | yes |
| `session.exec(select(Task.title))` (column-only) | yes |
| `select(func.count(Task.id))` / `select(func.count()).select_from(Task)` | yes |
| `session.get(Task, id_from_other_tenant)` | yes — returns `None` |
| `select(TaskComment).join(Task)` | yes (through the join) |
| ORM `update(Task).where(...)` / `delete(Task).where(...)` | yes — `rowcount == 0` cross-tenant |
| `select(TaskComment).where(TaskComment.task_id == <other tenant's task>)` | **no** — §6 |
| relationship lazy load (`announcement.media`) | not filtered by design; the parent was already filtered |

Two known, accepted limitations, both stated here so they are decisions rather than
oversights:

* **Identity map.** `with_loader_criteria` rewrites SQL; it does **not** evict the identity
  map. An object already present in a session's identity map stays reachable through
  `session.get()` on that session even after the acting tenant is set, and even after
  `expire_all()` — the refresh that follows an expiry is a *column load*, which the listener
  above deliberately skips. Measured on the real models:

  ```
  same session, acting tenant = A, tenant-B Task previously added through it:
      select(Task)                 -> []            # filtered
      session.get(Task, b_id)      -> Task(B)       # NOT None
      expire_all(); get(Task,b_id) -> Task(B)       # still not None
  fresh Session on the same engine, acting tenant = A:
      session.get(Task, b_id)      -> None          # filtered
      select(Task)                 -> []
  ```

  **In production this cannot happen**: `get_session` yields a *new* `Session` per request,
  FastAPI resolves `get_current_tenant` before the handler body, and the only
  pre-resolution query is `get_current_user`'s `session.get(User, …)` on the global `user`
  table. **In the test harness it certainly can**, because `conftest.py` today shares one
  `Session` across every request of a test. That is not a property of the mechanism, it is a
  property of the harness, and §8.4 therefore fixes the harness rather than the mechanism.
  Nothing in `app/` may be changed to compensate for it — in particular, **no service may
  grow a manual `tenant_id` equality check to make a by-id 404 appear**; that would dismantle
  the central design this slice exists to establish. If a by-id 404 does not appear, the
  harness is wrong.
* **Relationship loads** are exempt (`state.is_relationship_load`). Filtering them would
  break lazy loads on already-filtered parents. The only path this leaves open is
  `user.user_types` on a user who is a member of two tenants — visible on `/auth/me` and
  `/users`, which are global routes in this slice anyway (§5.3).

### 4.3 Write stamp and the fail-closed guard

```python
@event.listens_for(Session, "before_flush")
def _stamp_tenant_on_write(session, flush_context, instances):
    tenant_id = session.info.get(ACTING_TENANT_KEY)
    if tenant_id is None:
        return
    for obj in session.new:
        if isinstance(obj, TENANT_SCOPED_MODELS):
            obj.tenant_id = tenant_id            # overwrite: never trust an inbound value
    for obj in session.dirty:
        if isinstance(obj, TENANT_SCOPED_MODELS) and obj.tenant_id != tenant_id:
            raise CrossTenantWriteError(type(obj).__name__)
```

* Verified: an instance created with the model default *and* an instance created with an
  explicit foreign `tenant_id` both end up stamped with the acting tenant.
* `CrossTenantWriteError` is a new `DomainError` mapped to **403** in
  `app/core/exception_handlers.py`.
* Belt and braces on ER-2: **no `*Create` / `*Update` schema in `app/schemas/` declares a
  `tenant_id` field today** (verified: zero occurrences of `tenant_id` under
  `backend/app/schemas/`), so a `tenant_id` in a request body is dropped by Pydantic before
  it reaches a model. A test asserts this stays true for every schema class, so the stamp
  and the schema surface cannot drift apart.

The guard, in the same `do_orm_execute` listener:

```python
    if state.session.info.get(REQUEST_SCOPED_KEY) and not state.session.info.get(SCOPE_RESOLVED_KEY):
        for desc in state.statement.column_descriptions:
            if desc.get("entity") in TENANT_SCOPED_MODELS:
                raise TenantScopeNotResolvedError(desc["entity"].__name__)
```

`get_session` (`app/db.py`) sets `session.info[REQUEST_SCOPED_KEY] = True`; `set_acting_tenant`
and `use_global_tenant_scope` both set `SCOPE_RESOLVED_KEY`. So a route that queries a
scoped model without being classified fails loudly (500, `TenantScopeNotResolvedError`)
instead of returning every tenant's rows. Sessions built directly (`Session(engine)` in
`app/seed.py`, in Alembic, in every existing test) carry neither key and are untouched —
verified.

The guard only inspects top-level `column_descriptions`; it is defence in depth, not the
primary mechanism. The primary mechanism is the static route test of §5.2, which cannot be
reached at runtime at all.

### 4.4 Public helpers

```python
set_acting_tenant(session, tenant_id)      # sets acting + resolved
use_global_scope(session)                  # sets resolved, acting = None
acting_tenant_id(session) -> UUID | None
@contextmanager acting_tenant_scope(session, tenant_id)   # swap and restore
```

`acting_tenant_scope` exists for exactly one production caller — seeding a *new* tenant's
role-linked `UserType` rows from inside a request acting in a *different* tenant (§7.2).
Any second caller needs a review comment justifying it.

Measured overhead (sqlite, `select(Task)` returning one row, 500 iterations):
unfiltered `0.060 ms`, memoised filter `0.238 ms`, rebuilt-per-query `0.475 ms`. Against a
Postgres round trip this is noise; it is recorded because it is the one cost of the central
design.

---

## 5. Route classification

### 5.1 Applied at include time, not per handler

189 routes exist. Rather than edit ~170 handler signatures, the dependency is attached where
the routers are mounted, in `backend/app/api/v1/api.py`:

```python
TENANT_SCOPED = [Depends(deps.get_current_tenant)]
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"], dependencies=TENANT_SCOPED)
```

Every `include_router` call gets `dependencies=TENANT_SCOPED` **except** the global ones of
§5.3. This is one reviewable diff in one file, and it makes "is this route scoped?" a
property of the mount, not of the author's memory.

One structural change is required: `POST /api/v1/access-control/webhook/verification` is
authenticated by an `X-Device-Key` header, not a JWT, so it cannot inherit a
`get_current_tenant` that depends on `get_current_user`. Split it out of
`access_control.py`'s `router` into a `webhook_router` in the same module, mounted
separately without the scoped dependency; the remaining 7 access-control routes stay on the
scoped `router`. The webhook resolves its own tenant from the device (§6.4).

### 5.2 The test that makes this mechanical

`backend/tests/test_tenant_route_scope.py`:

```python
GLOBAL_ROUTES: frozenset[tuple[str, str]] = frozenset({...})  # 17 entries, listed in §5.3
```

For every `APIRoute` in `app.routes`, walk `route.dependant` recursively and assert:

1. `("GET", "/api/v1/tasks/")`-style key is in `GLOBAL_ROUTES` **xor** `get_current_tenant`
   appears among its (transitive) dependencies.
2. Every entry in `GLOBAL_ROUTES` corresponds to a route that actually exists (no stale
   allowlist entries).
3. `len(app.routes)` accounted for: scoped + global == every `APIRoute`.

A new route is therefore either scoped or a deliberate, reviewed allowlist addition. This
test is the answer to "how do we know nobody forgot?".

### 5.3 The global allowlist — 17 routes, and why each is global

| Route | Scope | Reason |
|---|---|---|
| `GET /` | none | root banner, no session |
| `GET /api/v1/health` | none | no session |
| `POST /api/v1/auth/login` | global | `user` is a global identity; a login predates any tenant choice |
| `GET /api/v1/auth/me` | global | returns the caller's own global identity |
| `GET /api/v1/auth/dev-users` | global | dev-only bypass, `user` table only |
| `POST /api/v1/auth/dev-login` | global | dev-only bypass, `user` table only |
| `POST /api/v1/auth/forgot-password` | global | `user` table only |
| `POST /api/v1/auth/reset-password` | global | `user` table only |
| `POST /api/v1/auth/signup` | **default tenant** | not global: it calls `ResidentService.auto_link_user`, which queries `resident` (scoped). See §8.1 |
| `GET /api/v1/tenants` … (7 routes) | global | `tenant` and `user_tenant_link` are unscoped tables; these routes *are* the tenant surface. `POST /tenants` seeds the new tenant's role types under `acting_tenant_scope` (§7.2) |
| `POST /api/v1/access-control/webhook/verification` | device-resolved | §6.4 |

`/api/v1/users/*` (3 routes) is **tenant-scoped**, not global, because `PATCH /users/{id}`
resolves `user_type_ids` through `select(UserType)` — a scoped table — and must only accept
UserTypes from the acting tenant. `GET /users/` continues to return *all* users, because
`user` is a global identity table with no `tenant_id`; scoping the user directory needs the
membership-aware admin model of APRAS-43. **This is a named residual leak of this slice**
(names/emails/roles are visible across tenants to any authenticated user) and must be
carried into APRAS-43's inputs. It is not a data leak of any tenant-scoped *record*, which
is what this slice's expected results cover.

Everything else — 172 routes across tasks, categories, user-types, lots, residents,
visitors, authorizations, access-logs, occurrences, documents, uploads, access-control,
projects, announcements, finance, feedback, reservable-spaces, space-reservations, packages,
assemblies, votes, assets, inventory-movements, purchase-requests and users — is
tenant-scoped.

`PORTEIRO` needs no special case: it has no `UserLotLink` rows, but its condo-wide flows
(packages, access logs, visitors, authorizations, gatekeeper) read scoped tables, so the
ambient filter confines them to the porteiro's own tenant and leaves the existing
lot-independent RBAC untouched. `backend/tests/test_porteiro_role.py` must pass unmodified.

---

## 6. Queries the central filter cannot reach

The filter constrains a statement only when a *scoped* entity appears in it. Two families
escape, and both are enumerated exhaustively below. Nothing else does: there is **no raw
SQL anywhere in `app/services/` or `app/api/`** (verified: zero `text(` / `.execute(`
occurrences), so every other read is an ORM statement over a scoped entity.

### 6.1 Child (inherited) tables fetched by their own id

APRAS-41 deliberately gave the 20 child tables no `tenant_id`; they are protected *through
their scoped parent*. That protection is real only where the parent is actually loaded
through the filtered session. Audited every `session.get(<child>, …)` in the codebase — six
sites:

| Site | Parent loaded through the filtered session? | Action |
|---|---|---|
| `endpoints/tasks.py:245` `update_comment` → `TaskComment` | **yes** — `session.get(Task, task_id)` two lines above | none |
| `services/announcement_service.py:251` `delete_media` → `AnnouncementMedia` | **no** — only compares `media.announcement_id != announcement_id`, both attacker-supplied | load `Announcement` first, 404 if `None` |
| `services/announcement_service.py:300` `delete_comment` → `AnnouncementComment` | **no**, and no parent id in the path at all (`DELETE /announcements/comments/{comment_id}`) | join to `Announcement`: `select(AnnouncementComment).join(Announcement).where(AnnouncementComment.id == comment_id)` |
| `services/project_service.py:230` `update_milestone` → `ProjectMilestone` | **no** | load `ConstructionProject` first, 404 if `None` |
| `services/project_service.py:259` `delete_milestone` → `ProjectMilestone` | **no** | same |
| `services/project_service.py:326` `delete_project_update` → `ProjectUpdate` | **no** | same |

The other child-table access paths (`voting_service` ballots/options/rejections,
`purchase_service._get_quote_or_404`, `announcement_service` media/receipts/comments
listings, `lot_service` links) all load their scoped parent — `Vote`, `Assembly`,
`PurchaseRequest`, `Announcement`, `Lot` — through the session first, so the filter already
404s the cross-tenant case. Ballots and
ballot rejections in particular are unreachable without their `Vote`, which is scoped: that
is the whole reason APRAS-41 refused to denormalise `tenant_id` onto them, and this slice
must not add one.

**`FacialTemplate` is the exception and must not be lumped in with them.** It is an
inherited table (no `tenant_id`) read at three sites, and only **one** of the three is
gated by its scoped `Resident` parent:

| Site | Parent load | Status |
|---|---|---|
| `access_control_service.py:134` `sync_facial_template` | `session.get(Resident, resident_id)` then `raise ResidentNotFoundError` | already safe — the ambient filter makes the cross-tenant case a 404 |
| `access_control_service.py:175-181` `get_facial_template` | **none at all** | **live cross-tenant read today** — fixed in §6.2 |
| `access_control_service.py:210-218` `process_verification_webhook` | `session.get(Resident, …)` *is* called, but its result does **not** gate the template query | **live cross-tenant read** — fixed in §6.2 and §6.4 |

### 6.2 Statements with no scoped entity at all

Seven queries read a child table with neither a scoped entity in the statement nor a
preceding filtered parent load that gates them:

| Site | Today | Fix |
|---|---|---|
| `purchase_service.py:327` `get_summary` | `select(PurchaseQuote)` — every tenant's quotes | `.where(PurchaseQuote.purchase_request_id.in_(request_ids))`, `request_ids` taken from the already-filtered `requests` list on line 322 |
| `purchase_service.py:329` `get_summary` | `select(PurchaseQuoteDecision)` — same | same treatment |
| `access_control_service.py:250` `list_events` | `select(FacialAccessEvent)` with optional device/resident filters | `.join(AccessDevice)` so the scoped device constrains it |
| `voting_service.py:180` `get_user_eligible_lot_ids` | `select(LotVoterEligibility).where(user_id == user.id)` — a multi-tenant user's eligibilities from every tenant | `.join(Lot)` |
| `access_control_service.py:175-181` `get_facial_template` | `select(FacialTemplate).where(resident_id == resident_id)` with no parent load, behind `GET /access-control/residents/{resident_id}/facial-template` — a tenant-A admin/director/manager reads a tenant-B resident's template and gets **200** | load the parent first: `resident = session.get(Resident, resident_id)` (ambient-filtered) and `raise ResidentNotFoundError(resident_id)` when it is `None`, exactly as `sync_facial_template` already does; then query the template by `resident.id` |
| `access_control_service.py:210-218` `process_verification_webhook` | same unfiltered `select(FacialTemplate)`, so a tenant-A device posting a tenant-B `resident_id` matches on a foreign template | gate the template query on the already-loaded `resident`: only run it when `resident is not None` — §6.4 |
| `voting_service.py:942-950` `list_lot_voter_eligibility` | `select(LotVoterEligibility).where(lot_id == lot_id)` with **no** `Lot` load, behind `GET /api/v1/lots/{lot_id}/voter-eligibility` — found while verifying the §9.1 route names, same family as the two above | `.join(Lot)`, so the scoped `Lot` constrains it. `.join(Lot)` rather than a `get_lot_by_id` 404 keeps the current `200 []` answer for an unknown lot id and leaves `tests/test_voting_rbac.py:605-625` passing unmodified; the cross-tenant answer becomes `200` with zero rows instead of a leak |

The `get_facial_template` fix carries one deliberate behaviour change, stated here so it is
a decision: `GET /access-control/residents/{resident_id}/facial-template` for a
**non-existent** resident id goes from `200 null` to `404`, matching the sibling
`.../facial-template/sync` route, which already 404s that case. `ResidentNotFoundError` is
already mapped to 404 in `app/core/exception_handlers.py:108`. The one existing test of this
route, `tests/test_access_control.py::test_get_facial_template_status`, uses an **existing**
resident and asserts `200` with a `null` body before sync and `200 SYNCED` after — both
paths are unaffected, so `test_access_control.py` still passes **unmodified**. No existing
test requests a template for an unknown resident id (verified).

Same treatment, defensively and for uniformity, on the `UserLotLink` queries keyed only by
`user_id` — `voting_service.py:138` `_active_lot_ids`, `voting_service.py:171`
`get_user_eligible_lot_ids`, `voting_service.py:199` `_co_resident_user_ids`,
`resident_service.py:38` and `visitor_service.py:72` `_check_lot_access`: add `.join(Lot)`.
These are not exploitable today (a caller with no membership in tenant B has no link rows
there) but they become wrong the moment a user is a member of two tenants, which APRAS-41
made a first-class state.

### 6.3 The regression that keeps this list honest

`test_tenant_isolation.py::test_inherited_table_queries_are_reviewed` greps
`app/services/*.py` and `app/api/v1/endpoints/*.py` for `select(<InheritedModel>)` and
`session.get(<InheritedModel>,` and asserts the set of `file:function` call sites equals a
frozen allowlist carrying a one-line justification each. A new unreviewed child-table query
fails CI. The 20 inherited model names come from APRAS-41's `test_tenant_models.py`
partition, not from a fresh hand-written list.

### 6.4 The gatekeeper / device flow

`POST /access-control/webhook/verification` authenticates a *device*, and `access_device`
is scoped. `AccessControlService.process_verification_webhook` must therefore:

1. look up the device by `X-Device-Key` while the session is in global scope (device keys
   are globally unique on purpose — APRAS-41 §2.3);
2. immediately call `set_acting_tenant(session, device.tenant_id)`;
3. **gate the facial-template lookup on the resident it already loads.** This is a real code
   change, not "proceed unchanged": today the `select(FacialTemplate)` runs off
   `payload.resident_id` regardless of whether `session.get(Resident, …)` returned anything,
   and `FacialTemplate` is an inherited table the ambient filter cannot constrain (§6.2).

```python
    if payload.resident_id is not None:
        resident = session.get(Resident, payload.resident_id)   # ambient-filtered → None cross-tenant
        if resident is not None:                                # <-- the new gate
            template = session.exec(
                select(FacialTemplate).where(
                    FacialTemplate.resident_id == resident.id,
                    FacialTemplate.sync_status == FacialTemplateSyncStatus.SYNCED,
                )
            ).first()
            if template:
                matched = True
                if resident.is_active:
                    access_granted = True

    event = FacialAccessEvent(
        device_id=device.id,
        resident_id=resident.id if resident is not None else None,   # never a foreign FK
        ...
    )
```

**The webhook's response contract does not change, and ER-8 is written to the contract the
code can actually produce.** `process_verification_webhook` has never raised for an unknown
resident: it returns an event with `matched=False, access_granted=False` and the endpoint
answers **201** (`status_code=status.HTTP_201_CREATED`), which
`tests/test_access_control.py::test_webhook_unmatched_face` pins today. A device is an
unauthenticated-by-JWT integration client; making a *foreign* resident id 404 while an
*unknown* one returns 201 would turn the webhook into an existence oracle for other
condominiums' resident ids. So the decision is explicit:

| Case | Before | After |
|---|---|---|
| `resident_id: null` | 201, `matched=false`, `access_granted=false` | **unchanged** (`test_webhook_unmatched_face` passes unmodified) |
| resident in the device's tenant, template `SYNCED`, active | 201, `matched=true`, `access_granted=true` | **unchanged** (`test_webhook_matched_and_granted`) |
| resident in the device's tenant, template `SYNCED`, inactive | 201, `matched=true`, `access_granted=false` | **unchanged** (`test_webhook_matched_but_resident_inactive`) |
| resident id unknown anywhere | 201, `matched=true` if some template exists, else `false` | 201, `matched=false`, `access_granted=false`, `resident_id=null` on the event |
| **resident id belongs to another tenant** | 201, `matched=true` off a foreign template, event written with a cross-tenant `resident_id` FK | **201, `matched=false`, `access_granted=false`, `resident_id=null`** — indistinguishable from an unmatched face |

In every case the `FacialAccessEvent` is stamped by §4.3 with the **device's** `tenant_id`.
`tests/test_access_control.py` therefore passes **unmodified**; no pre-existing test module
is a legitimately-modified module under this slice, and §8.4's "conftest is the only
pre-existing test file that changes" stands.

This still closes the hole it set out to close — a device in condominium A can no longer
grant access to, or record a match against, a resident of condominium B — it just closes it
with a denial rather than with a 404.

QR/authorization flows need no special handling: `visitor_authorization` is directly scoped,
so `GET /authorizations/{id}` and `/qr-code` 404 cross-tenant through the ambient filter.

---

## 7. `UserType` resolution becomes tenant-aware

### 7.1 `get_effective_user_type_ids` — no signature change

APRAS-41 handed this over explicitly. The function does
`select(UserType).where(UserType.role == user.role)).first()`. Change the lookup to filter
on a resolved tenant:

```python
tenant_id = tenant_context.acting_tenant_id(session) or DEFAULT_TENANT_ID
role_type = session.exec(
    select(UserType).where(UserType.role == user.role, UserType.tenant_id == tenant_id)
).first()
```

Reading the tenant from `session.info` rather than adding a parameter is deliberate:

* the three production callers (`assert_menu_access`, `assert_manager_can_see_task`,
  `TaskService`) always run on a resolved request session, so they get the acting tenant;
* the **`DEFAULT_TENANT_ID` fallback makes the unit-test path deterministic** —
  `tests/test_role_type_permissions.py` (7 direct calls) and
  `tests/test_tenant_no_behaviour_change.py` (2 direct calls) pass a plain session and build
  their `UserType` rows with the model default, so they resolve exactly the row they
  resolve today, even once §7.2 makes multiple role rows per role exist. **Both modules stay
  unmodified.** A "no filter at all" fallback would make `.first()` order-dependent and
  break them.

### 7.2 A new tenant gets its own role-linked `UserType` rows

APRAS-41 deliberately did *not* seed role types on `POST /tenants`, because with a
tenant-blind `.first()` that would have been non-deterministic. Now that resolution is
tenant-scoped, the opposite is true: without them, a non-`ADMINISTRATOR` member of a new
tenant has an empty effective-UserType set and is 403'd by `assert_menu_access` on every
gated menu.

`TenantService.create_tenant` therefore seeds one `UserType` per `UserRole` value for the
new tenant — same names and empty `allowed_menus` as migration `0018`, inside
`with acting_tenant_scope(session, new_tenant.id):` so the §4.3 stamp writes the *new*
tenant's id while the request itself acts elsewhere. `ix_user_type_tenant_role` (APRAS-41)
guarantees at most one row per `(tenant, role)`.

This is additive to `/tenants` behaviour: `test_tenants.py` and `test_tenants_rbac.py`
assert status codes and payload fields of the tenant resources themselves, not the
`user_type` table, and must pass unmodified.

---

## 8. Compatibility of the non-request paths

### 8.1 `POST /auth/signup`

Public, unauthenticated, and it touches a scoped table (`auto_link_user` → `resident`).
It gets `use_default_tenant_scope`: the acting tenant is always the default tenant and any
`X-Tenant-Id` header is **ignored** — an unauthenticated caller must not be able to place
itself in an arbitrary tenant by guessing a UUID. Signup additionally creates a
`UserTenantLink` to the default tenant so new users have an explicit membership rather than
relying on the zero-membership fallback of §3.2. Resident auto-linking consequently only
matches residents of the default tenant; invite-based signup into a chosen tenant is
APRAS-43/38 work and is recorded as a follow-up.

Check while implementing: `test_tenants.py::test_list_tenants_returns_empty_list_for_member_less_non_admin`
builds its user directly (not via signup), so the new link does not affect it.

### 8.2 `dev-users` / `dev-login`

Both query only `user`. Global scope, no behaviour change; `test_e2e_flow.py` and the auth
tests must pass unmodified.

### 8.3 `app/seed.py`

Uses `Session(engine)` directly → no `request_scoped` marker → no filter, no guard, no
stamp; rows keep landing in the default tenant through the model default. The only change
is additive: insert a `UserTenantLink` to the default tenant for each seeded user, so the
dev environment matches what migration `0028` produced for real installs.
`python -m app.seed` (or the documented invocation) must run clean against the local
Postgres on 5436.

### 8.4 `backend/tests/conftest.py` — the one existing test file that must change

The existing `client` fixture overrides `get_session` with a **single shared `Session`**
reused by every request of a test. For the ~70 existing modules that is harmless: all their
data is in the default tenant, so the ambient filter is a no-op for them. For the isolation
suite it is fatal, for the identity-map reason measured in §4.2 — a tenant-B row seeded
through the shared session remains reachable via `session.get()` on that session even with
the acting tenant set to A, so **every by-id 404 of ER-5 and ER-7 would return 200 for a
reason that does not exist in production**, where each request gets its own `Session`.

Three edits, and the third is a contract the implementer may not reinterpret:

1. `get_session_override` sets `session.info[REQUEST_SCOPED_KEY] = True` on the shared test
   session, so routes exercised by the existing `TestClient` go through the same resolution
   and guard as production. Without it the new machinery would be dead code under test.
2. New fixtures for the isolation suite: `tenant_b`, `user_in_tenant_a`, `user_in_tenant_b`,
   `member_admin`.
3. **The harness contract for the isolation suite** — three named rules:

   **(a) `tenant_client` gives each request its own `Session`.** A second client fixture,
   used *only* by `test_tenant_isolation.py`, overrides `get_session` with a generator that
   opens a fresh `Session` on the same `StaticPool` engine per request — which is precisely
   what production does:

   ```python
   @pytest.fixture(name="tenant_client")
   def tenant_client_fixture(session: Session):
       engine = session.get_bind()
       def get_session_override():
           with Session(engine) as request_session:
               request_session.info[REQUEST_SCOPED_KEY] = True
               yield request_session
       app.dependency_overrides[get_session] = get_session_override
       client = TestClient(app)
       yield client
       app.dependency_overrides.clear()
   ```

   Verified end-to-end against the real `app` on the real `StaticPool` sqlite engine: login,
   `POST /api/v1/categories/` → 201, `GET /api/v1/categories/` → 200 with the row, **four
   requests, four distinct `Session` objects**, and the seeding session sees the committed
   row after `expire_all()`. `StaticPool` keeps one underlying connection, so there is a
   single shared in-memory database and no visibility problem — the constraint it imposes is
   ordering, covered by (b).

   **(b) `raw_session` is a *separate* `Session`, never a request session.** It is opened on
   `session.get_bind()`, carries neither `REQUEST_SCOPED_KEY` nor `acting_tenant_id` (so it
   is unfiltered and unstamped, exactly like `app/seed.py`), and is used to seed tenant-B
   rows and to assert persisted `tenant_id` values. It **must commit before any API call**,
   and a test must call `raw_session.expire_all()` before re-reading a row an API request
   wrote. It is *not* the shared `session` fixture with `acting_tenant_id` popped — that was
   the design the identity map defeats, and it is explicitly rejected here.

   **(c) The request session must never have held the tenant-B instance.** Because each
   request under `tenant_client` gets a fresh `Session`, this is automatic and needs no
   `expunge_all()` anywhere: tenant-B rows enter `raw_session`'s identity map, never a
   request's. This also means ER-6's admin-with-`X-Tenant-Id: B` requests cannot poison a
   later tenant-A 404 assertion, since the two run on different sessions.

   A **harness self-test** in `test_tenant_isolation.py` makes this contract testable rather
   than aspirational — `test_harness_gives_each_request_its_own_session`: record the `id()`
   of each yielded session in the override, drive two requests, assert the two ids differ,
   and assert that a tenant-B row seeded through `raw_session` is absent from the request
   session's identity map. If this test fails, every 404 in the module is meaningless and it
   says so in its docstring.

Under this contract ER-5's `GET`/`PATCH`/`PUT`/`DELETE`-by-id 404s and ER-7's child-table
404s are **genuinely exercised**: the request session issues a real `SELECT` that the loader
criteria constrains, `session.get()` returns `None`, and the service raises its existing
`*NotFoundError` → 404. No service in `app/` acquires a manual `tenant_id` check to make
these pass; if an implementer finds themselves adding one, the harness is wrong (§4.2).

No other pre-existing test module may be edited. If one appears to need editing, the
resolution ladder of §3.2 is wrong — fix the ladder, not the test.

---

## 9. Tests

### 9.1 `backend/tests/test_tenant_isolation.py` (the ER-4 module)

Structure: seed one row of each scoped entity in tenant A (the default tenant) and one in
tenant B via `raw_session` (§8.4b), then drive the API through `tenant_client` (§8.4a).
Every path below was taken from a live walk of `app.routes`, not from memory.

0. **Harness self-test** — §8.4's `test_harness_gives_each_request_its_own_session`. It runs
   first and its docstring states that the rest of the module is void if it fails.
1. **List matrix** — parametrised over at least these 28 collection endpoints, all verified
   to exist:
   `/api/v1/tasks/`, `/api/v1/categories/`, `/api/v1/user-types/`, `/api/v1/lots/`,
   `/api/v1/visitors`, `/api/v1/access-logs`, `/api/v1/occurrences`, `/api/v1/documents`,
   `/api/v1/documents/folders`, `/api/v1/uploads/photos/pending`,
   `/api/v1/access-control/devices`, `/api/v1/access-control/events`, `/api/v1/projects`,
   `/api/v1/announcements`, `/api/v1/finance/categories`, `/api/v1/finance/transactions`,
   `/api/v1/finance/budget-lines`, `/api/v1/feedback`, `/api/v1/reservable-spaces/`,
   `/api/v1/space-reservations/`, `/api/v1/packages`, `/api/v1/packages/queue`,
   `/api/v1/assemblies/`, `/api/v1/votes/`, `/api/v1/assets`,
   `/api/v1/inventory-movements`, `/api/v1/purchase-requests`.
   As `user_in_tenant_a`: **200**, and no returned id belongs to a tenant-B row.
   The two aggregate endpoints `/api/v1/assets/summary` and
   `/api/v1/purchase-requests/summary` return no ids and are asserted on their *values* in
   item 6, not here.

   **`/api/v1/residents` does not exist** — the residents router is mounted with *no*
   prefix (`api.py:48`) and its listing route is `GET /api/v1/lots/{lot_id}/residents`
   (verified against a live walk of `app.routes`). Because it is keyed by a scoped `lot_id`,
   its isolation assertion is a different shape and gets its own test rather than a row in
   the parametrised matrix:
   `GET /api/v1/lots/{tenant_b_lot_id}/residents` as `user_in_tenant_a` → **404**
   (`get_residents_by_lot` calls `LotService.get_lot_by_id` first, which the ambient filter
   makes raise `LotNotFoundError`), and `GET /api/v1/lots/{tenant_a_lot_id}/residents` →
   **200** listing only tenant-A residents. Two sibling lot-keyed collections behave the
   same way and are asserted alongside it:
   `GET /api/v1/lots/{b_lot}/authorizations` → **404** (`get_lot_authorizations` does
   `session.get(Lot, …)` before its access check), while
   `GET /api/v1/lots/{b_lot}/voter-eligibility` → **200 with zero rows** after the §6.2
   `.join(Lot)` fix — 200-empty, not 404, because that route never loaded its `Lot` and the
   fix deliberately preserves its current answer for an unknown lot id.
2. **By-id matrix** — `GET`/`PATCH`(or `PUT`)/`DELETE` of a tenant-B resource as
   `user_in_tenant_a`: **404** for every scoped resource that exposes those verbs. These are
   the assertions that depend on the §8.4 harness contract: each request runs on its own
   `Session`, so the handler's `session.get(...)` issues a real filtered `SELECT` and returns
   `None`. Under the old shared-session harness every one of them would return **200**.
3. **Admin global vision** — the same list endpoints with `X-Tenant-Id: <B>` as
   `ADMINISTRATOR`: **200** and every row is a tenant-B row.
4. **Create stamping** — `POST /api/v1/categories/` (and one more scoped create) as an actor
   in tenant B: **201** and the persisted row's `tenant_id == B`; the same request with
   `"tenant_id": "<A>"` in the body still persists `tenant_id == B`.
5. **Cross-tenant FK on create** — `POST /api/v1/tasks/` with a tenant-B `category_id` as a
   tenant-A caller does not create a task pointing across the boundary (4xx, or the FK is
   rejected as unresolvable).
6. **Child tables and aggregates** — every path below verified to exist:
   `DELETE /api/v1/announcements/comments/{tenant_b_comment}` → **404**;
   `DELETE /api/v1/announcements/{b}/media/{b_media}` → **404**;
   `PUT /api/v1/projects/{b}/milestones/{b_milestone}` → **404**;
   `DELETE /api/v1/projects/{b}/updates/{b_update}` → **404**;
   `GET /api/v1/votes/{tenant_b_vote}/tally` → **404** (ballots are unreachable through a
   foreign `Vote`; note the route is `/tally`, there is no `/results` route);
   `GET /api/v1/purchase-requests/summary` excludes tenant-B quote and decision values;
   `GET /api/v1/assets/summary` excludes tenant-B asset values;
   `GET /api/v1/access-control/events` excludes tenant-B events;
   `GET /api/v1/lots/{b_lot}/voter-eligibility` → **200** with zero rows (§6.2).
7. **Gatekeeper / `FacialTemplate`** — the two §6.2 sites, asserted against the contract §6.4
   fixes:
   * `GET /api/v1/access-control/residents/{tenant_b_resident}/facial-template` as a
     tenant-A administrator → **404** (this returns **200** with the tenant-B template body
     on `master` today — the test must fail before the fix and pass after);
   * webhook with a tenant-A device key and a tenant-B `resident_id` → **201** with
     `matched=false` and `access_granted=false`, and the persisted `FacialAccessEvent` has
     `tenant_id == tenant A` (the device's) and `resident_id is None` — **not** a 404, and
     not distinguishable from an unmatched face (§6.4);
   * webhook with a tenant-A device key and a tenant-A resident holding a `SYNCED` template
     → **201**, `matched=true`, and the `FacialAccessEvent` row carries the device's
     `tenant_id`;
   * the tenant-B `FacialTemplate` row still exists in the database afterwards (asserted
     through `raw_session`), proving the 404/`matched=false` came from the tenant boundary
     and not from the template being absent.
8. **PORTEIRO** — a porteiro in tenant A registering a package for a tenant-B lot: **404**;
   listing `/packages/queue` returns only tenant-A packages.
9. **Header semantics** — the full §3 table: malformed → 400; unknown + admin → 404;
   unknown + non-admin → 403; non-member → 403; inactive tenant → 403; member → 200;
   no header + one membership → that tenant; no header + zero memberships → default tenant;
   no header + two memberships → 400.
10. **`tenant_id` is never accepted from a client** — no `*Create`/`*Update` schema declares
    a `tenant_id` field.
11. **Reviewed child-query allowlist** — §6.3.

### 9.2 `backend/tests/test_tenant_route_scope.py`

The §5.2 walk over `app.routes` plus the `GLOBAL_ROUTES` allowlist assertions.

### 9.3 `backend/tests/test_tenant_context.py`

Unit tests for the machinery itself, independent of HTTP: registry equals APRAS-41's 27
tables; filter applies to select / `session.get` / count / ORM update / ORM delete; stamp
overwrites both a defaulted and a forged `tenant_id`; `CrossTenantWriteError` on a dirty
cross-tenant object; `TenantScopeNotResolvedError` on a request-scoped unresolved session
touching a scoped model, and *not* on a global model; a plain `Session(engine)` is entirely
unaffected; `acting_tenant_scope` restores the previous value including on exception. Plus
one test that pins the §4.2 identity-map limitation as *known*, so a future reader does not
mistake it for a bug in the filter: on a session that already holds a tenant-B instance,
`select(Model)` is filtered while `session.get(Model, b_id)` is not, and on a fresh session
both are filtered.

### 9.4 Gates

* `uv run pytest` green, ≥ 90 % coverage on `--cov=app` (the project gate). Baseline
  measured on `master` at `6628ffb` before this task:
  **800 passed, 17 skipped, total coverage 98.14 %, 311 s**. The suite must still be
  800-passed-plus-the-new-cases; a *reduction* in the passing count means an existing test
  was silently dropped or skipped.
* `ruff check` clean.
* **No new Alembic migration.** This slice changes no schema: `tenant_id`, its
  `server_default` and the model-side `DEFAULT_TENANT_ID` default all stay (the model
  default is what keeps ~70 test modules and `seed.py` working; dropping the
  `server_default` is a later cleanup, not this slice's business). `alembic heads` must
  still report exactly one head, `0028_add_tenant_and_membership`, and
  `backend/tests/test_migrations_postgres.py` must pass **unmodified** against the local
  Postgres on port 5436:
  `TEST_POSTGRES_URL=postgresql://postgres:postgres@localhost:5436/nexdom SECRET_KEY=test uv run pytest tests/test_migrations_postgres.py -v`.
* Frontend untouched: `npm run build` and `npm run test:coverage` (75 % gate) keep passing
  with zero files changed under `frontend/`. `npm run lint` has never passed on this repo
  (~465 pre-existing errors); the bar is **no new findings**, which is automatic since
  nothing frontend changes.

---

## 10. Expected Results

- [ ] `backend/app/api/deps.py` exposes `get_current_tenant`; on a tenant-scoped route it
      returns **400** for a malformed/empty `X-Tenant-Id`, **403** for a non-`ADMINISTRATOR`
      sending a tenant they are not a member of, **403** for any role sending an inactive
      tenant, **404** for an `ADMINISTRATOR` sending an unknown tenant id, and **200** for
      an `ADMINISTRATOR` sending any existing active tenant.
- [ ] With **no** `X-Tenant-Id` header: a caller with exactly one membership acts in that
      tenant (**200**), a caller with zero memberships acts in the default tenant
      `00000000-0000-0000-0000-000000000001` (**200**), and a caller with two or more
      memberships gets **400**.
- [ ] Every create endpoint stamps `tenant_id` server-side: `POST /api/v1/categories/` by an
      actor in tenant B persists a row with `tenant_id == B` (**201**) even when the request
      body contains `"tenant_id": "<tenant A>"`; and no `*Create`/`*Update` schema in
      `backend/app/schemas/` declares a `tenant_id` field.
- [ ] For a user who is a member of tenant A only, with data seeded in both tenants, every
      tenant-scoped collection endpoint returns **200** with zero tenant-B rows — at minimum
      `GET /api/v1/tasks/`, `/api/v1/categories/`, `/api/v1/user-types/`, `/api/v1/lots/`,
      `/api/v1/announcements`, `/api/v1/documents`, `/api/v1/documents/folders`,
      `/api/v1/occurrences`, `/api/v1/packages`, `/api/v1/packages/queue`,
      `/api/v1/space-reservations/`, `/api/v1/reservable-spaces/`, `/api/v1/projects`,
      `/api/v1/purchase-requests`, `/api/v1/assets`, `/api/v1/inventory-movements`,
      `/api/v1/finance/categories`, `/api/v1/finance/transactions`,
      `/api/v1/finance/budget-lines`, `/api/v1/visitors`, `/api/v1/access-logs`,
      `/api/v1/access-control/devices`, `/api/v1/access-control/events`, `/api/v1/feedback`,
      `/api/v1/assemblies/` and `/api/v1/votes/`.
- [ ] The residents collection is **`GET /api/v1/lots/{lot_id}/residents`** (there is no
      `GET /api/v1/residents` route): for that tenant-A caller,
      `GET /api/v1/lots/{tenant_b_lot_id}/residents` returns **404** and
      `GET /api/v1/lots/{tenant_a_lot_id}/residents` returns **200** with only tenant-A
      residents. Likewise `GET /api/v1/lots/{tenant_b_lot_id}/authorizations` → **404**, and
      `GET /api/v1/lots/{tenant_b_lot_id}/voter-eligibility` → **200** with zero rows.
- [ ] `GET`, `PATCH`/`PUT` and `DELETE` by id of a tenant-B resource by that same tenant-A
      caller return **404** on every scoped resource exposing those verbs — exercised against
      a harness in which **each request gets its own SQLAlchemy `Session`** (as production
      does), so the 404 comes from the tenant filter and not from a shared session's identity
      map; `backend/tests/test_tenant_isolation.py` contains a self-test proving two
      consecutive requests ran on two distinct sessions.
- [ ] An `ADMINISTRATOR` sending `X-Tenant-Id: <tenant B>` receives **200** and tenant-B rows
      on those same list endpoints.
- [ ] Child tables are protected through their scoped parent:
      `DELETE /api/v1/announcements/comments/{tenant_b_comment_id}` → **404**,
      `DELETE /api/v1/announcements/{b}/media/{b_media_id}` → **404**,
      `PUT /api/v1/projects/{b}/milestones/{b_milestone_id}` → **404**,
      `GET /api/v1/votes/{tenant_b_vote_id}/tally` → **404**,
      `GET /api/v1/purchase-requests/summary` counts no tenant-B quote or decision, and
      `GET /api/v1/access-control/events` returns no tenant-B event.
- [ ] `GET /api/v1/access-control/residents/{tenant_b_resident_id}/facial-template` returns
      **404** to a tenant-A administrator (it returns **200** with the tenant-B template on
      `master` today), while the same route for a tenant-A resident with no template still
      returns **200** with a `null` body.
- [ ] `POST /api/v1/access-control/webhook/verification` resolves its tenant from the device
      and never confirms a foreign resident's existence: a tenant-A device key posting a
      tenant-B `resident_id` returns **201** with `matched=false` and `access_granted=false`
      — identical to an unmatched face, not a 404 — and persists a `FacialAccessEvent` whose
      `tenant_id` is the device's tenant A and whose `resident_id` is `null`, while the
      tenant-B `FacialTemplate` row still exists in the database. A tenant-A device posting a
      tenant-A resident with a `SYNCED` template still returns **201** with `matched=true`.
- [ ] `backend/tests/test_tenant_isolation.py` exists and automates the cross-tenant matrix
      above; it fails if any covered endpoint returns a tenant-B row to a tenant-A caller.
- [ ] `backend/tests/test_tenant_route_scope.py` asserts that every `APIRoute` in
      `app.routes` either depends (transitively) on `get_current_tenant` or is one of the 17
      allowlisted global routes, and that every allowlist entry names a route that exists.
- [ ] A `PORTEIRO` in tenant A keeps working within its tenant — `/api/v1/packages/queue`
      returns **200** with only tenant-A packages — and registering a package for a tenant-B
      lot returns **404**; `backend/tests/test_porteiro_role.py` passes unmodified.
- [ ] `POST /api/v1/tenants` seeds one role-linked `UserType` per `UserRole` in the new
      tenant, and `get_effective_user_type_ids` resolves the role-type of the acting tenant
      (falling back to the default tenant when no tenant is resolved), with
      `backend/tests/test_role_type_permissions.py` and
      `backend/tests/test_tenant_no_behaviour_change.py` passing unmodified.
- [ ] `backend/tests/conftest.py` is the only pre-existing test module modified — in
      particular `backend/tests/test_access_control.py` passes **unmodified**, including
      `test_webhook_unmatched_face`, `test_webhook_matched_and_granted`,
      `test_webhook_matched_but_resident_inactive` and `test_get_facial_template_status`;
      the whole suite passes with `uv run pytest` and coverage stays ≥ 90 % on `--cov=app`;
      `ruff check` is clean.
- [ ] No new Alembic migration: `alembic heads` still reports the single head
      `0028_add_tenant_and_membership`, and `backend/tests/test_migrations_postgres.py`
      passes unmodified against Postgres on port 5436.
- [ ] Nothing under `frontend/` is modified; `npm run build` and `npm run test:coverage`
      (75 % gate) still pass, and `npm run lint` reports no new findings.

---

## 11. Out of Scope / Non-goals

- **Frontend: nothing at all.** No `X-Tenant-Id` sending, no tenant switcher, no context, no
  i18n keys. That is APRAS-38. CORS already allows the header (`allow_headers=["*"]` in
  `app/main.py`), so no backend CORS change is needed either.
- **No `is_tenant_admin`, no per-tenant RBAC composition** — APRAS-43. Role checks stay
  global: an `ADMINISTRATOR` is an administrator of every tenant it can act in.
- **`GET /api/v1/users/` stays global** (§5.3) — scoping the user directory by membership is
  APRAS-43, and doing it here would break every existing test module, whose users have no
  membership rows. Named residual, carried forward.
- **No schema change, no migration, no dropping of `tenant_id`'s `server_default` or model
  default.** Both remain the compatibility mechanism for direct-session writers.
- No tenant-aware caching, no per-tenant rate limiting, no subdomain/host-based tenant
  resolution, no tenant settings/branding/billing.
- No change to invite/signup semantics beyond §8.1: a user cannot self-select a tenant at
  signup.
- No denormalisation of `tenant_id` onto any of the 20 inherited tables — APRAS-41's
  partition stands, and `test_tenant_models.py` must keep passing unmodified.
