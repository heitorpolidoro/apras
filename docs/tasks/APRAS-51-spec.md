# APRAS-51 — Alinhar guard e mapeamento de permissão em todas as rotas de `ROUTE_PERMISSIONS`

Merge base: `e188866` (APRAS-44). Everything measured below was measured at
that commit, with the tree clean, by running the walkers and the sweep
described in §3 against the real application. No number in this spec is an
estimate. Round-1 revision: §3's fix list was **re-measured after** the
spec review showed five of the original thirty routes already enforce their
mapped permission in the service layer, and every count that depends on the
list has been re-derived (§7).

## 1. Scope

`backend/app/core/permissions.py::ROUTE_PERMISSIONS` maps **201** routes to
one catalogue permission each. That map is the source of truth for three
things: the parity matrix (`tests/data/parity_matrix_baseline*.json`), the
frontend's derived menus and routes, and the role editor's checkboxes. On
**25** of those routes the mapped permission is never consulted anywhere in
the request, so the map claims a gate the code does not have.

This task:

1. adds the missing enforcement on those 25 routes;
2. adds a permanent, mechanical oracle that a mapped route cannot ship
   unenforced again — one **structural** walk over `route.dependant` and one
   **behavioural** sweep that pins the *shape* of the refusal, not merely its
   non-success (§4.3), so no AST heuristic and no unrelated 404 can stand in
   for the missing check;
3. records the resulting parity delta — exactly **3** cells — without
   touching the frozen IAM F2 golden file;
4. declares, and proves per route, the five routes whose gate legitimately
   lives in a **service** (§4.4), so "enforced" stops meaning "carries a
   `Depends`".

It does **not**: change `ROUTE_PERMISSIONS` (stays 201), `PERMISSIONS` (stays
174), `UNGUARDED_ROUTES` (stays 22), `tests/data/legacy_role_bundles.json`,
`parity_matrix_baseline.json`, `parity_matrix_baseline_40.json`,
`parity_matrix_baseline_44.json`, `tests/matrix_world.py`, or any frontend
production file. See §10.

## 2. The defect, stated precisely

QA of APRAS-49 found `GET /api/v1/roles/` and QA of APRAS-40 found
`GET /api/v1/tasks/`: both mapped (`roles:read`, `tasks:read`), both guarded
only by `get_current_user`. They are two instances of one class, and the class
is larger than two.

Since IAM F2 (APRAS-46) enforcement takes three legitimate forms:

* the **route-level dependency**, `Depends(require_permission(P))`, on 28
  routes today (APRAS-43's seven, APRAS-40's three, APRAS-44's eighteen);
* the **in-handler check**, `deps.has_permission(user, session, P)` — kept in
  the handler on purpose, because FastAPI solves sub-dependencies *before* body
  validation, so hoisting one would flip a denied caller's `422`/`404` into a
  `403`;
* the **service-level check**, where the handler delegates to a service that
  receives or names `P` and refuses — sometimes with an audit side effect that
  a route-level guard would skip (§4.4).

The defect is a route in **none** of the three. Nothing in CI notices, because:

* `test_permission_registry.py` only asserts every route is *classified*
  (mapped or unguarded) — never that a mapped route enforces its mapping;
* `test_permission_enforcement.py::test_every_route_level_permission_matches_the_registry`
  asserts the 28 dependency-form routes declare the right permission, and says
  nothing about the other 173;
* the parity matrix measures only the **six legacy profiles**, and 15 of the
  16 permissions involved are held by all six, so no cell could move. The one
  exception, `tasks:read`, is held by five and GUEST's 200 is a *documented*
  `DENIAL_SHAPE_OVERRIDES` entry.

  The votes nuance, since it is the reason §6.1 survives §3's shrunken list
  intact: `votes:cast`, `votes:retract` and `votes:tally_read` are **not** held
  by GUEST or PORTEIRO (checked against `tests.conftest.bundle`). Those cells
  do not move only because the baseline already records **403** for them —
  which is itself evidence that the votes gate is real (§4.4).

The dimension all three miss is a caller who simply does not hold the mapped
permission. Post-F5 that caller is ordinary: `TenantService.ensure_legacy_roles`
inserts role rows with `permissions = []`, and APRAS-40's subscription ceiling
strips whole modules, so "holds `tasks:read`" is not implied by "is logged in".
§9 states what that means on deploy.

## 3. The measurement (re-run at `e188866`, read-only)

Three independent probes were run. They disagree, and **each has a measured
false positive**; §4 specifies its oracle around both.

**(a) Structural, exact.** Walk `route.dependant` for `PermissionRequired`:
**28** routes carry the dependency form, all 28 declaring exactly their
registry permission (0 mismatches); **173** do not. A second walk for
`deps.get_current_superuser` finds **5** mapped routes whose permission is in
`SUPERUSER_ONLY_PERMISSIONS`.

**(b) Behavioural — the complement sweep.** One extra actor: a non-superuser,
non-tenant-admin member of the default tenant, linked to the world's lot and
carrying an active `Resident` row, whose single role's `permissions` is set,
per cell, to `sorted(PERMISSIONS - {P})` — *everything except the permission
under test*. 201 real requests. Distribution:
`Counter({403: 169, 200: 25, 201: 3, 404: 2, 204: 1, 400: 1})`; **29** routes
answered 2xx.

**(c) AST, over a name-resolved call graph** from each handler, looking for `P`
passed as an argument to any call: **29** routes never name their mapped
permission.

The two sets of 29 are not the same set, and neither is the answer:

* **(b) has three false positives beyond the §5 trio: the packages routes.**
  `PackageService._assert_lot_access` (`app/services/package_service.py:80-98`)
  *does* require the mapped permission — the comment at line 87 exists
  specifically to rule out "a lot-linked resident passes regardless". What let
  the sweep actor through is line 84, the gatekeeper short-circuit on
  `packages:queue_read`, which the actor holds **by construction** (it holds
  everything except the permission under test). The sweep cannot see past its
  own actor here; reading the code settles it.
* **(c) has two false positives: the ballot routes.**
  `voting_service._assert_can_cast` (`app/services/voting_service.py:352-359`)
  reads
  `has_permission(user, session, "votes:retract" if is_retraction else "votes:cast")`.
  The argument is an `IfExp`, not a `Constant`, so an AST walk looking for `P`
  as an argument cannot see it. Probe (b) does not flag these two: both answer
  **403** to the complement actor.
* **(b) also misses routes where a *different* dimension refuses first**, which
  is why (c) is kept: `PATCH /tasks/{id}/comments/{comment_id}` is 403 on
  authorship, so its missing `tasks:comment` check is invisible to (b).

**The fix list is the union of (b) and (c), minus the three global tenant reads
of §5 and minus the five service-enforced routes of §4.4: 25 routes.**

| Module | Routes | Mapped permission | Found by |
|---|---|---|---|
| tasks | `GET /api/v1/tasks/` | `tasks:read` | b |
| tasks | `POST /api/v1/tasks/{task_id}/comments` | `tasks:comment` | b, c |
| tasks | `PATCH /api/v1/tasks/{task_id}/comments/{comment_id}` | `tasks:comment` | c |
| categories | `GET /api/v1/categories/` | `categories:read` | b, c |
| roles | `GET /api/v1/roles/` | `roles:read` | b, c |
| users | `GET /api/v1/users/` | `users:read` | b, c |
| visitors | `GET /api/v1/visitors` | `visitors:read` | b, c |
| visitors | `GET /api/v1/visitors/{visitor_id}` | `visitors:read` | b, c |
| visitors | `POST /api/v1/visitors` | `visitors:create` | b, c |
| visitors | `PUT /api/v1/visitors/{visitor_id}` | `visitors:update` | b, c |
| gate | `GET /api/v1/access-logs` | `gate:logs_read` | b, c |
| authorizations | `GET /api/v1/authorizations/{authorization_id}` | `authorizations:gate_lookup` | b, c |
| authorizations | `GET /api/v1/authorizations/{authorization_id}/qr-code` | `authorizations:gate_lookup` | b, c |
| residents | `GET /api/v1/lots/{lot_id}/residents` | `residents:read` | b, c |
| residents | `GET /api/v1/residents/{resident_id}` | `residents:read` | b, c |
| feedback | `GET /api/v1/feedback` | `feedback:read` | b, c |
| feedback | `GET /api/v1/feedback/{id}` | `feedback:read` | b, c |
| feedback | `POST /api/v1/feedback` | `feedback:create` | b, c |
| spaces | `GET /api/v1/reservable-spaces/` | `spaces:read` | b, c |
| reservations | `POST /api/v1/space-reservations/{reservation_id}/cancel` | `reservations:cancel` | b, c |
| reservations | `POST /api/v1/space-reservations/{reservation_id}/reject` | `reservations:reject` | b, c |
| uploads | `GET /api/v1/uploads/photos/{photo_id}` | `uploads:photo_read` | b, c |
| uploads | `DELETE /api/v1/uploads/photos/{photo_id}` | `uploads:delete` | b, c |
| uploads | `POST /api/v1/uploads/photo` | `uploads:photo_create` | c |
| votes | `GET /api/v1/votes/{vote_id}/tally` | `votes:tally_read` | b, c |

All 25 are on **tenant-scoped** routers, so `require_permission`'s
`get_current_tenant` sub-dependency is already resolved for them and costs no
extra query.

The five routes that left the list in round 1 — `POST /votes/{vote_id}/ballots`,
`POST /votes/{vote_id}/ballots/retract`, `GET /packages`,
`GET /packages/{package_id}`, `POST /packages/{package_id}/pickup` — are §4.4's
`SERVICE_ENFORCED` form.

## 4. Approach

### 4.1 The fix: the dependency form, on all 25

Twenty-two of the 25 handlers swap

```python
current_user: Annotated[User, Depends(api_deps.get_current_user)]
```

for

```python
current_user: Annotated[User, Depends(api_deps.require_permission("<P>"))]
```

The three `uploads` routes are spelled the older way —
`current_user: User = Depends(get_current_active_user)`, with a module-level
`from app.api.deps import get_current_active_user, get_db` — so their edit is
`current_user: User = Depends(require_permission("<P>"))` with
`require_permission` added to that import. `get_current_active_user` is a
module-level alias of `get_current_user` (`app/api/deps.py:86`), so the
substitution is semantically identical; the import stays, because the three
photo-moderation routes in the same module keep using it.

`PermissionRequired.__call__` returns the `User`, so no other line of a handler
signature changes and no handler body changes — **except** one:

* `endpoints/tasks.py::list_tasks` — its
  `if not has_permission(..., "tasks:read"): return []` early return becomes
  dead and is **deleted**. This is the QA finding: the documented empty-list
  refusal becomes a 403. It is the only intentional refusal-shape change in
  this task, and it moves one parity cell (§6).

The correct general statement, replacing round 0's false one ("no other handler
holds a check for its own mapped permission"): **none of these 25 handlers, and
no service they call, consults its own mapped permission.** That is what puts
them on the list, and it was established by reading each of the 25 call chains
after the two probes disagreed — not by either probe alone. The five routes for
which the statement is false are in §4.4 and are not converted.

`PermissionRequired`'s class docstring ("used on **exactly** the seven routes
whose gate is already a route-level `Depends`… a gate that runs inside the
handler today must stay inside the handler") is amended: the rule it states is
about *moving an existing* gate, and it stands — §4.4 is the case where it
binds. What this task adds is a gate where there was none, and §6 proves
mechanically that only three cells move.

### 4.2 The proof, part 1 — the structural walk (ER-1)

New module `backend/tests/test_permission_alignment.py`. For every
`(method, path) -> P` in `ROUTE_PERMISSIONS`, the route must fall in exactly
one **declared enforcement form**:

| Form | Predicate | Count after this task |
|---|---|---|
| **D** dependency | `PermissionRequired(P)` in `route.dependant` | 53 |
| **S** superuser | `deps.get_current_superuser` in `route.dependant` **and** `P ∈ SUPERUSER_ONLY_PERMISSIONS` | 5 |
| **M** membership | in `MEMBERSHIP_GATED`, §5 | 3 |
| **E** service | in `SERVICE_ENFORCED`, §4.4 | 5 |
| **H** in-handler | none of the above; proven by §4.3, never by inspection | 135 |

53 + 5 + 3 + 5 + 135 = **201**, asserted as an equality against
`len(ROUTE_PERMISSIONS)` so the table cannot drift, and

```python
UNENFORCED: frozenset[tuple[str, str]] = frozenset()
```

**must be empty**, asserted by name (`test_no_mapped_route_is_unenforced`).
`UNENFORCED` is the allowlist ER-1 speaks of: a route that satisfies no form
*and* is not proven by the sweep. It ships empty and a future task may not grow
it without deleting an assertion.

`H` is **derived** (`set(ROUTE_PERMISSIONS) - D - S - M - E`), deliberately, and
not hand-listed. A hand list of 135 keys would give a future author a place to
type a new unenforced route into and call it declared; a derived bucket sends
every new route straight into §4.3's sweep, which cannot be satisfied by typing.
`D`, `S`, `M` and `E` are the four sets that *are* asserted as exact literals,
because each is small, and each addition to them is a reviewable decision. `E`
in particular costs its author a per-route behavioural test (§4.4) — it is not
a cheaper `UNENFORCED`.

The module also asserts, over the same walk, that no `PermissionRequired`
declares a permission other than its route's (today's
`test_every_route_level_permission_matches_the_registry`, which stays where it
is and keeps passing).

### 4.3 The proof, part 2 — the shaped complement sweep (ER-1, ER-2)

The oracle, in `backend/tests/test_permission_alignment.py`:

* **its own world.** The module declares its own module-scoped fixture that
  calls `matrix_world.matrix_engine(...)`, `matrix_world.seed_once(...)` and
  `matrix_world.neutralised_storage()` — **imported and unmodified** — and then
  seeds its own extra rows on its own `Session`. `matrix_world.py`,
  `build_world` and `test_permission_parity_matrix.matrix_run` are **not
  touched**, so `_meta.harness`'s sha stays byte-identical and the 1206-cell
  star test runs against exactly the world it recorded. Round 0's "no second
  world" is retracted: there *is* a second world, built from the same
  unmodified builder, and that is the point — the alternative (a seventh actor
  inside `build_world`) mutates the harness the frozen F2 file names;
* **one extra actor**, seeded by the new module: a non-superuser,
  non-tenant-admin `User` whose only role is a **new** `Role` row of the default
  tenant (never one of the six legacy profile rows), linked to `world.lot_id`
  with an open-ended `UserLotLink` and an active `Resident` row, holding a token
  from `create_access_token`;
* **one parametrised case per swept route** — `ROUTE_PERMISSIONS` minus the
  three `M` routes minus the five `E` routes, i.e. **193** cases. The excluded
  eight are not sweep exceptions: their form carries its own, stronger test
  (§4.4, §5), and the sweep's actor is provably the wrong instrument for the
  `packages` three (§3);
* before each request, the actor's role row is rewritten to
  `sorted(PERMISSIONS - {P})` **inside the cell's transaction**. The session
  handle is the one the module installs in `app.dependency_overrides[get_session]`
  (the same session `cell_client` yields its `TestClient` on), and the rewrite
  runs inside `tenant_context.acting_tenant_scope(session, DEFAULT_TENANT_ID)`
  — without arming the acting tenant first, `Role` is refused by the
  fail-closed `TenantScopeNotResolvedError` filter. Both details are stated
  because both were hit while measuring;
* **the assertion pins the refusal shape**, not merely non-success:

```python
#: Swept routes whose refusal of a non-holder is *not* a bare 403, with the
#: reason. Every other swept route must answer exactly 403.
REFUSAL_SHAPES: dict[tuple[str, str], tuple[int, str]] = {
    ("GET", "/api/v1/tasks/{task_id}/comments"): (
        404,
        "deps.assert_manager_can_see_task refuses a non-holder of tasks:read "
        "with TaskNotFoundError: the existence of the task is not information "
        "a non-holder is entitled to",
    ),
    ("GET", "/api/v1/tasks/{task_id}/history"): (404, "idem"),
}
```

  with three assertions: (i) every swept route answers `REFUSAL_SHAPES` if it
  has an entry and **403** otherwise; (ii) 2xx is never accepted; (iii) every
  `REFUSAL_SHAPES` key is a swept route, so a stale entry is a failure rather
  than dead prose — which is what "no entry that is not exercised" means here.

This is the round-1 correction. Measured at `e188866` the sweep's old
`not 2xx` assertion already passed on three routes whose mapped permission was
never consulted (`404 GET /tasks/{id}/comments`, `404 GET /tasks/{id}/history`,
`400 POST /uploads/photo`), so an empty exceptions dict was saying nothing. The
two survivors above are genuine: `assert_manager_can_see_task`
(`app/api/deps.py:408`) refuses on `tasks:read` itself and merely chooses 404
over 403 to avoid leaking existence.

**`POST /api/v1/uploads/photo` needs no reordering.** Its 400 is not body
validation: FastAPI accepts the multipart body, and
`media_service.upload_photo` raises `InvalidPhotoFormatError` at step 2/3
because the harness's `_FILE_BYTES` is not a decodable image. That check runs
*inside the handler*, and the handler has no permission check at all. Adding
`Depends(require_permission("uploads:photo_create"))` puts the guard in the
dependency tree, which FastAPI solves before it ever calls the handler, so the
answer becomes **403** and the route needs no `REFUSAL_SHAPES` entry. Nothing
about the upload validation order changes for a holder.

Two consequences worth stating so they are not rediscovered in review:

* **it cannot be satisfied by loosening a heuristic** — there is no heuristic;
  it issues the request, and it now pins what came back;
* **it is one-sided on purpose.** The complementary direction ("a holder is not
  refused") is what the 1206-cell parity matrix already measures for the six
  profiles, including the 31 `NON_ROLE_403` object-dimension refusals a
  two-sided sweep would have to re-litigate.

What the two oracles together prove, stated exactly (ER-1's wording): every
mapped route is in a declared enforcement form, and every swept route refuses,
in a declared shape, a caller who holds the entire catalogue except its mapped
permission. What they do not prove: that the refusal is *caused* by the mapped
permission on the 135 `H` routes — for those the sweep is a strong necessary
condition, and `REFUSAL_SHAPES` is what stops an unrelated refusal from passing
silently.

Runtime: 193 requests against one seeded SQLite world, i.e. one sixth of the
existing matrix module.

### 4.4 The five service-enforced routes (ER-2)

```python
#: Routes whose mapped permission is enforced in a service, not in the route
#: signature, because the service does something a route-level guard would
#: skip. Exactly five, each with a pinned behavioural test below.
SERVICE_ENFORCED: dict[tuple[str, str], str] = { ... }   # exactly 5
```

**The two ballot routes.** `POST /api/v1/votes/{vote_id}/ballots` and
`.../retract` reach `voting_service._assert_can_cast`, whose step 2 checks
exactly the mapped permission and, before raising
`ForbiddenError("Este perfil não vota")`, writes a
`BallotRejection(reason=ROLE_FORBIDDEN)` row. Both handlers
(`app/api/v1/endpoints/voting.py:303-307`, `:331-335`) carry a docstring saying
so: *"No role pre-filter here on purpose: the service chain must run so a
refused attempt is written to `BallotRejection` before the 403."* Converting
them would delete the audit row, replace a Portuguese user-facing message with
`PermissionRequired`'s generic detail (contradicting §11's i18n gate), and move
the role refusal ahead of `_assert_window_open`. APRAS-46's rule — a gate that
runs inside the handler today must stay inside the handler — binds here.

`test_ballot_routes_refuse_a_non_holder_in_the_service` asserts, per route, that
the §4.3 complement actor (holding the whole catalogue except `votes:cast`,
resp. `votes:retract`) receives **403**, that the response detail is
`"Este perfil não vota"`, and that exactly one `BallotRejection` row with
`reason == ROLE_FORBIDDEN` exists for that (vote, user) afterwards. The 403 is
the answer the sweep would have demanded — measured 403 at `e188866` — plus the
audit row the sweep cannot see, so excluding these two from §4.3 loses nothing.

**The three packages routes.** `GET /api/v1/packages`,
`GET /api/v1/packages/{package_id}` and `POST /api/v1/packages/{package_id}/pickup`
reach `PackageService._assert_lot_access(session, lot_id, current_user, P)` with
`P` the mapped permission (`packages:read`, `packages:read`, `packages:pickup`).
The gate is real, and it has a **documented alternative**: a holder of
`packages:queue_read` — the gatehouse role — passes without the mapped
permission and without a lot link, because the gatehouse hands packages to every
lot. A route-level `Depends` would delete that short-circuit and 403 the
gatehouse, and **no parity cell would move**, because all six legacy bundles
hold `packages:read` and `packages:pickup`: the matrix is structurally blind to
this regression, which is why it is called out here rather than left to QA.

`test_packages_routes_enforce_the_mapped_permission_in_the_service` asserts, per
route, three callers: a member holding neither `P` nor `packages:queue_read`
gets **403**; a member holding `packages:queue_read` but **not** `P` gets the
route's success code (the declared alternative, pinned so a future refactor
cannot drop it silently); a lot-linked member holding `P` gets the success code.

`test_service_enforced_is_exactly_five` asserts the literal, and every key must
also be in `ROUTE_PERMISSIONS` and absent from `D`, `S` and `M`.

### 4.5 The named routes (ER-2)

Beside the sweep, an explicit parametrised case over the 25 fixed routes,
asserting the four answers the board asked for:

| Caller | Expected |
|---|---|
| member, role with `permissions = []`, no flags | **403** |
| member, role carrying exactly the mapped permission | 2xx (the route's success code) |
| `is_superuser` | 2xx |
| `is_tenant_admin` in the acting tenant | 2xx |

The last two are free by construction — `_resolve_permissions` short-circuits
both to the whole catalogue — and are asserted anyway, because "the guard is a
permission and not a flag check" is the property APRAS-47 bought and this task
must not spend.

## 5. The three global tenant reads — the membership form

`GET /api/v1/tenants`, `GET /api/v1/tenants/{tenant_id}` and
`GET /api/v1/tenants/{tenant_id}/members` are mapped (`tenants:read`,
`tenants:read`, `tenants:members_read`) and gated by **membership**, not by the
permission. They may not be converted, for two independent reasons:

1. **The dependency form is structurally unavailable.** The tenants router is
   mounted `GLOBAL_SCOPED` (`api/v1/api.py`); `PermissionRequired` depends on
   `get_current_tenant`, which would arm the ambient tenant filter on a route
   whose whole job is to answer across tenants.
2. **The in-handler form would lock users out.** With no acting tenant,
   `get_effective_role_ids` falls back to `DEFAULT_TENANT_ID`, so a user whose
   only membership and only roles are in tenant B would resolve to the empty
   set and be refused their own tenant list — the list `TenantContext.tsx`
   fetches to render the switcher. The app would not boot for them.

So they take form **M**, declared as a three-entry literal with a reason each,
and proven **positively** rather than excused:

```python
MEMBERSHIP_GATED: dict[tuple[str, str], str] = { ... }   # exactly 3
```

`test_membership_gated_routes_gate_on_membership_and_not_on_the_permission`
uses two callers built by the new module's own world (§4.3), and asserts the
**exact** answers the handlers give — round 0's "403/404 on all three" was
wrong for the list route:

* an **outsider**: a member of `tenant_b` only, carrying a default-tenant role
  with the **whole** catalogue (a role row in the default tenant without a
  `UserTenantLink` to it — legal, and the configuration that makes the
  `DEFAULT_TENANT_ID` fallback resolve the whole catalogue at global scope, so
  the test is about membership and not about an empty permission set). It gets
  **200** on `GET /tenants` with a body that **excludes** the default tenant
  (`TenantService.list_tenants` filters by membership and "never an error"),
  and **404** on `GET /tenants/{default_tenant_id}` and
  `.../members` (`get_visible_tenant` raises `TenantNotFoundError` — 404, never
  403, APRAS-47 §5.1);
* a **member holding no permission at all** (the §4.3 complement actor with
  `permissions = []`): **200** on all three, with the default tenant present in
  the list body.

That is the documented equivalent of a guard: the mapped permission is not the
gate, membership is, and the test says so out loud instead of an allowlist
saying nothing. The module's own `world.outsider_user_id` is deliberately not
used: it is a `make_user(profile="GUEST")` actor whose only role is the shared
default-tenant GUEST row, which expresses neither "whole catalogue" nor
"outsider" without rewriting a row six other actors read.

**This leaves one honest inconsistency**: the map still names a permission that
gates nothing on those three routes. Correcting it means moving them to
`UNGUARDED_ROUTES` and retiring `tenants:read` and `tenants:members_read` from
the catalogue — which ER-4 forbids here (`UNGUARDED_ROUTES` unchanged) and
which is a catalogue decision with role-editor consequences. See §10.

## 6. Parity (ER-3)

### 6.1 What actually moves

Computed from `load_union()` (F2 + `_40` + `_44`, with `F5_PATH_RENAMES`
applied) and `tests.conftest.bundle`, over all 25 fixed routes × 6 profiles =
**150** cells, every one of which exists in the union: a cell moves only where
the profile does **not** hold the mapped permission and the recorded status is
not already 403. That is **three cells**:

| Profile | Route | Permission | Old | New |
|---|---|---|---|---|
| GUEST | `GET /api/v1/tasks/` | `tasks:read` | 200 | 403 |
| GUEST | `POST /api/v1/tasks/{task_id}/comments` | `tasks:comment` | 404 | 403 |
| GUEST | `PATCH /api/v1/tasks/{task_id}/comments/{comment_id}` | `tasks:comment` | 404 | 403 |

Re-measured after the round-1 shrink from 30 routes to 25: the delta is
**unchanged**, because all three cells are `tasks` routes and none of the five
removed routes had a moving cell (their non-holders — GUEST and PORTEIRO on the
two ballot routes, GUEST on the three packages routes — already record 403).

The other 147 cells are unchanged, because 15 of the 16 permissions involved
are held by **all six** legacy profiles — which is precisely why the matrix
could not have caught this defect and why a matrix re-record is not the
mechanism that finds it.

These three cells are three of the six `DENIAL_SHAPE_OVERRIDES` entries.
After this task `DENIAL_SHAPE_OVERRIDES` has **3** entries (the surviving 404s
of `PATCH /tasks/{task_id}`, `GET /tasks/{task_id}/history`,
`GET /tasks/{task_id}/comments`, all still raised by
`assert_manager_can_see_task`, all still GUEST), and
`test_denial_shape_overrides_is_exactly_six` becomes `…_is_exactly_three`.

### 6.2 The mechanism: a fourth, *overriding* baseline file

**The F2 file is not re-recorded.** `record_parity_baseline.refuse_the_frozen_baseline`
refuses to write it before it builds anything, `F2_BASELINE_SHA256` pins its
bytes, and APRAS-40 §9.2.1 states the reason in one sentence: a re-record moves
`_meta.merge_base_sha` off `02c2025…` and turns the star test of IAM F2 into a
tautology, silently. Nothing in this task is worth that.

Instead, `backend/tests/data/parity_matrix_baseline_51.json`:

* **150 cells** — the 25 corrected routes × the 6 profiles;
* recorded by the committed recorder, **after** the production change is
  committed (so `assert_clean_production_tree` passes), with
  `--merge-base <this task's branch point>` and one `--routes 'METHOD /path'`
  per corrected route, so `_meta.regenerate` is executable exactly as written;
* it is an **override**, not a partition: unlike `_40` and `_44` its cells
  already exist in the F2 file. `load_union()` gains an `OVERRIDDEN_CELLS` set
  and, for those keys only, the `_51` value wins; every other overlap stays the
  error it is today.

**Its provenance caveat is stronger than `_40`'s and `_44`'s, and the docstring
must say so.** For those two, running the `regenerate` recipe at
`merge_base_sha` fails loudly — `select_cells` exits 2, the routes do not exist
yet. For `_51` the 25 routes **do** exist at the branch point, so the recipe
*succeeds* and silently produces the **pre-fix** statuses. The docstring states
that the recipe is a description of how the file was made *after* the
production change, not a command that reproduces it from the merge base.

**`OVERRIDDEN_CELLS` is derived, not a literal**: it is the `_51` file's own
cell keys with `F5_PATH_RENAMES` applied, i.e. `cells_of(load_apras_51_baseline())`.
A 150-tuple literal is exactly the hand list §4.2 rejects, and deriving it is
safe because three other assertions bound it: `_meta.cell_count == 150`, the
route-set assertion of §7, and the exact three-cell delta below.

Three assertions make the override un-abusable:

1. `test_the_apras_51_baseline_differs_from_f2_in_exactly_three_cells` — the
   file is diffed against the F2 file cell by cell, **through `cells_of` /
   `load_union`'s keying, so `F5_PATH_RENAMES` is applied to both sides**
   (F2 records `GET /api/v1/user-types/`, the recorder writes the live
   `GET /api/v1/roles/`; six of the 150 cells would otherwise fail to
   key-match). The diff must equal the §6.1 table, spelled as an
   `APRAS_51_CELL_DELTA` literal with old and new. The other 147 superseded
   cells are therefore **proven** inert rather than assumed;
2. `test_every_apras_51_correction_only_restricts` — for each of the three, the
   new status is 403 and `holds(profile, method, path)` is False. An override
   can never turn a denial into a permission;
3. the existing hygiene and provenance cases are duplicated for the new file
   (`_meta` keys, no absolute path, no timestamp, integer statuses, its own
   `merge_base_sha` distinct from `_40`'s and `_44`'s).

`test_the_f2_baseline_is_untouched_by_apras_40`,
`test_the_f2_sha_anchors_still_agree_with_the_frozen_file`,
`F2_MERGE_BASE_SHA`, `F2_BASELINE_SHA256`, `LEGACY_BUNDLES_SHA256` and the two
additive files are **untouched**. The `02c2025…` prose anchors in
`test_permission_enforcement.py` and `test_permission_parity_matrix.py` do not
move, because nothing they describe moved.

The PR body lists the three cells with old → new.

## 7. Counts and modules to update (ER-4)

| Where | From | To |
|---|---|---|
| `test_permission_enforcement.PERMISSION_GUARDED_ROUTES` | 28 | **53** |
| `test_the_permission_guarded_routes_are_the_apras43_seven_plus_billing` | 3 groups | + a fourth, APRAS-51 group (25, listed) |
| `test_permission_parity_matrix.DENIAL_SHAPE_OVERRIDES` | 6 | 3 |
| `tests/data/` baseline files | 3 | 4 |
| `_51` cells | — | 150 (25 × 6) |
| swept routes in `test_permission_alignment` | — | 193 (201 − 3 M − 5 E) |
| `ROUTE_PERMISSIONS` / `PERMISSIONS` / `UNGUARDED_ROUTES` | 201 / 174 / 22 | **unchanged** |
| `EXPECTED_CELL_COUNT` / `CELLS` | 1206 | **unchanged** |

**`EXPECTED_CELL_COUNT` gains no addend.** It is
`F2_CELL_COUNT + APRAS_40_CELL_COUNT + APRAS_44_CELL_COUNT = 1080 + 18 + 108 =
1206`, and `_51` is an *override*: its 150 keys already belong to the F2 1080,
so `load_union()` must still return 1206 entries and no `APRAS_51_CELL_COUNT`
addend is introduced. `_meta.cell_count == 150` lives on the file and is
asserted there only. Adding an addend would turn
`test_matrix_covers_every_permission_mapped_route` and
`test_the_three_baselines_partition_route_permissions_exactly` red.

`test_the_three_baselines_partition_route_permissions_exactly` **passes
unmodified with a fourth file present**, which would leave `_51`'s route set
unasserted. It is extended with `fifty_one == APRAS_51_ROUTES` (the 25) and
`fifty_one <= f2`, and its docstring gains one sentence saying `_51` is
deliberately *not* part of the pairwise-disjointness clause, because it
overrides F2 rather than partitioning with it.

`PERMISSION_GUARDED_ROUTES`'s existing comment says the APRAS-43 seven "must
never grow" and that a new group goes *below*; this task adds its 25 as a
fourth group and keeps that ordering.

Test modules that pin the old, unguarded answers and must be updated with a
one-line reason each (found by running the suite; the known ones):
`test_guest_rbac.py` — the GUEST `200`/`[]` case on `GET /api/v1/tasks/` is at
**lines ~118-120** (the `200` at line 79/94 is inside the
`_director_creates_task` helper and is unrelated) —, `test_menu_gate_removal.py`,
`test_task_comments.py`, `test_tasks_api.py`, `test_visitors*.py`,
`test_feedback*.py`, `test_uploads*.py`, `test_categories.py`,
`test_roles.py`, `test_residents*.py`, `test_reservable_spaces.py`,
`test_space_reservations.py`. `test_packages*.py` and the voting modules are
**not** in this list: their routes are not converted (§4.4). **No test is
deleted to make this pass**: a case asserting an old 200 is rewritten to assert
the new 403 *and* keeps a sibling asserting the holder still gets 200.

## 8. Frontend (ER-5)

Checked at `e188866`, and the answer is **no production change**:

* `frontend/src/features/user-administration/access/routeAccess.ts` —
  `ROUTE_ACCESS` is the single place a route's rule is written and `NAV_ITEMS`
  reuses the same objects (APRAS-48). **None** of its rules names any of the 25
  permissions: the rules that touch these modules are `{ module: … }`
  (`/dashboard`, `/categories`, `/packages`, `/feedback`, `/reservations`) or
  name a *write* permission (`/spaces` → `spaces:create|update|deactivate`,
  `/admin/users` → `users:update`, `/admin/roles` →
  `roles:create|update|delete`, `/gate` → `gate:checkin`, `/authorizations` →
  `authorizations:read`).
* **`/packages` and the `packages:queue_read` alternative — checked.** §4.4
  makes the packages screens reachable by `packages:read` **or**
  `packages:queue_read`. `ROUTE_ACCESS["/packages"]` is `{ module: "packages" }`,
  which means "holds any `packages:*`" and therefore already admits **both**
  members of that `anyOf`, and admits the gatehouse's `packages:queue_read`
  holder that an `anyOf: ["packages:read"]` rule would wrongly hide. Narrowing
  it to `{ anyOf: ["packages:read", "packages:queue_read"] }` would be a
  production frontend change that removes nothing and forbids the screen's own
  create/queue flows (`packages:create`, the gatehouse queue) from opening it.
  The rule stays as it is, and this paragraph is the record that the `anyOf`
  question was asked and answered.
* A `{ module: X }` rule means "holds any `X:*`". A caller who reaches one of
  those screens therefore already holds a permission of that module, and the
  screen's list endpoint asks for the module's `read`. The one configuration
  where a menu could now lead to a 403 is a role holding, say, `feedback:create`
  but not `feedback:read` — a configuration the operator authored, that
  `RestrictedAccessMessage` already renders in place, and that the documented
  degenerate `/subscription` case (APRAS-40 §8.3) established as acceptable
  rather than special-cased.
* `useCanAccess` reads `/permissions/me`, which is unchanged: this task adds no
  permission, removes none, and does not touch `get_effective_permissions`.
* The 25 permission strings appear in `frontend/src/` only in
  `src/test/permissionFixtures.ts` (a fixture mirroring the six legacy bundles,
  all of which hold them) and in two **prose comments** —
  `frontend/src/App.tsx:69` and `routeAccess.ts:18`, both explaining a rule, no
  production logic. ER-5's diff check is unaffected.
* `TenantContext.tsx` fetches `/tenants` for the switcher; §5 is what keeps that
  working, and it is the reason the trio is not converted.

Deliverable: `npm run lint`, `npm run build`, `npm run test` green with
coverage ≥ the base run, and **zero** diff under `frontend/src/` outside test
files. If any vitest case turns red, the fix is in the test, and it must be
explained in the PR body — a red frontend test here would mean the menu layer
disagreed with the API layer, which is the thing APRAS-48 exists to prevent.

## 9. Production impact

**The access removal is intended, and it is the point of the task.** §6's
"exactly three cells" is a statement about six *legacy* fixture profiles, not
about live data, and it must not be read as "almost nothing changes".

Since IAM F5, `TenantService.ensure_legacy_roles` inserts role rows with
`permissions = []`, operators author their own roles in the role editor, and
APRAS-40's subscription ceiling strips whole modules from what a role can hold.
Consequently, **on deploy, every role in every live tenant that does not hold
the mapped permission loses access to the corresponding routes of §3's 25** —
including roles that reached those screens yesterday because the map claimed a
gate the code did not have. That is the defect being closed, not a side effect.

How it surfaces:

* the API answers **403** with `PermissionRequired`'s existing, byte-identical
  detail `"The user doesn't have enough privileges"` — no new string, no i18n
  key (§11);
* the frontend renders its existing friendly denial (`RestrictedAccessMessage`)
  in place rather than crashing or logging the user out;
* **the menus are mostly already hidden**, because `ROUTE_ACCESS` /`NAV_ITEMS`
  are module- or permission-scoped: a role holding no `X:*` never saw the
  entry to begin with. The residual case is §8's documented degenerate one — a
  role satisfying a `{ module: X }` rule through a *write* permission while the
  screen's list endpoint asks for `X:read`; that caller reaches the screen and
  the API refuses, exactly as `/subscription` does today (APRAS-40 §8.3).

What is **not** in this task: no backfill migration, no data change, no seeding
of permissions onto any role row (§10), and no operator communication or
release note beyond the PR body's statement of this section. Adjusting the demo
tenant's roles while exercising the screens is the operator's own action, not a
deliverable.

## 10. Out of scope

* **Retiring `tenants:read` / `tenants:members_read`.** The honest end state
  for §5's trio is to move them to `UNGUARDED_ROUTES` (like `/auth/me`:
  authenticated, self-scoped) and drop the two now-unroutable permissions from
  the catalogue. ER-4 pins `UNGUARDED_ROUTES` unchanged, the change shrinks the
  role editor's vocabulary, and it needs 18 F2 cells retired through a declared
  `RETIRED_CELLS` set. It is a follow-up task, and §5's `MEMBERSHIP_GATED`
  literal is where it starts.
* **Converting the five `SERVICE_ENFORCED` routes to the dependency form.**
  §4.4: it would delete a `BallotRejection` audit row, a Portuguese user-facing
  message, and the `packages:queue_read` gatehouse short-circuit, and the parity
  matrix is blind to all three.
* **Converting the 135 form-H routes to the dependency form.** Forbidden by
  APRAS-46: hoisting an in-handler gate flips `422`/`404` into `403` and would
  move parity cells wholesale. The shaped sweep proves them enforced; that is
  the contract, not the spelling.
* **Re-recording `parity_matrix_baseline.json`, `_40` or `_44`, or editing
  `tests/matrix_world.py`.** §4.3, §6.2.
* **Changing `legacy_role_bundles.json`.** It is a historical recording of what
  the retired enum meant; its sha stays pinned.
* **Seeding permissions onto any role row, or any backfill.** Post-F5 doctrine:
  nothing is seeded, and a role with `permissions = []` grants nothing on
  purpose. §9.
* **The object-dimension refusals** (`NON_ROLE_403`'s 31 entries) and the
  `ADMIN_GAP_PERMISSIONS` tier. Untouched.

## 11. Gates

* `cd backend && TEST_POSTGRES_URL=... uv run pytest` — whole suite green,
  coverage ≥ 90%. The postgres URL is required: `test_migrations_postgres.py`
  asserts against a live schema.
* `cd backend && uv run ruff check .` and `ruff format --check .`.
* `cd frontend && npm run lint && npm run build && npm run test`.
* i18n: no user-facing string is added or changed by this task — the 403 detail
  is `PermissionRequired`'s existing, byte-identical
  `"The user doesn't have enough privileges"`, and §4.4 is what keeps
  `"Este perfil não vota"` alive — so `en.json` and `pt.json` are untouched,
  and that is asserted by the diff being empty under `frontend/src/i18n/`.
* `AGENTS.md`: the *Permissions are in code* section keeps 174/201; a sentence
  is added recording that every mapped route is now proven enforced, by which
  test, that five routes are enforced in a service by design, and that the
  three global tenant reads are membership-gated by design. A case in
  `backend/tests/test_docs_agents_md.py` asserts that sentence is present, so
  the doc claim is machine-checked like the counts around it.

## Expected Results

- [ ] **ER-1 — Every mapped route is in a declared enforcement form, and the
  exception allowlist is empty.** `backend/tests/test_permission_alignment.py`
  walks all 201 `ROUTE_PERMISSIONS` entries and places each in exactly one
  declared form — `PermissionRequired(P)` in `route.dependant` (53),
  `get_current_superuser` + `P ∈ SUPERUSER_ONLY_PERMISSIONS` (5), the
  three-entry `MEMBERSHIP_GATED` (§5), the five-entry `SERVICE_ENFORCED` (§4.4),
  or the derived in-handler bucket (135) — asserting 53+5+3+5+135 == 201 and
  `UNENFORCED == frozenset()` by name; and the 193-case complement sweep
  asserts each swept route refuses a caller holding the whole catalogue except
  its mapped permission with **403**, or with the status its `REFUSAL_SHAPES`
  entry declares (exactly two entries, both the `assert_manager_can_see_task`
  404s), never a 2xx, with every `REFUSAL_SHAPES` key required to be a swept
  route. The new module builds its own world from the unmodified
  `matrix_world` helpers; `sha256(backend/tests/matrix_world.py)` is unchanged.
- [ ] **ER-2 — The revealed routes refuse a non-holder, and the five
  service-enforced routes keep their documented behaviour.**
  `GET /api/v1/roles/`, `GET /api/v1/tasks/` and the other 23 routes of §3
  answer **403** to an authenticated member whose role carries no permission
  and who holds neither flag, and answer their success code to a holder, to an
  `is_superuser`, and to an `is_tenant_admin` of the acting tenant. The two
  ballot routes answer 403 with detail `"Este perfil não vota"` **and** write a
  `BallotRejection(reason=ROLE_FORBIDDEN)` row for a non-holder; the three
  packages routes answer 403 to a caller holding neither the mapped permission
  nor `packages:queue_read`, and their success code to a `packages:queue_read`
  holder who lacks the mapped permission.
- [ ] **ER-3 — The parity delta is exactly three cells, and the frozen files
  do not move.** `backend/tests/data/parity_matrix_baseline_51.json` is
  recorded by the committed recorder at its own new `merge_base_sha` with 150
  cells (25 routes × 6 profiles) and overrides the F2 file for those keys via a
  derived `OVERRIDDEN_CELLS`; a test asserts its diff against
  `parity_matrix_baseline.json`, keyed through `cells_of`/`F5_PATH_RENAMES`, is
  exactly `{(GUEST, GET, /api/v1/tasks/): 200→403,
  (GUEST, POST, /api/v1/tasks/{task_id}/comments): 404→403,
  (GUEST, PATCH, /api/v1/tasks/{task_id}/comments/{comment_id}): 404→403}`,
  that every corrected cell is 403 and denied by `holds()`, and that
  `parity_matrix_baseline.json`, `_40` and `_44` are byte-identical (sha256
  pins unchanged).
- [ ] **ER-4 — The counts move deliberately, the production impact is on the
  record, and the suite is green.** `PERMISSION_GUARDED_ROUTES` is 53 (a
  fourth, APRAS-51 group of 25 below the existing three),
  `DENIAL_SHAPE_OVERRIDES` is 3, `EXPECTED_CELL_COUNT` and `len(load_union())`
  are still 1206 with no `APRAS_51_CELL_COUNT` addend,
  `test_the_three_baselines_partition_route_permissions_exactly` additionally
  asserts `fifty_one == APRAS_51_ROUTES` and `fifty_one <= f2`,
  `UNGUARDED_ROUTES` is still 22, `ROUTE_PERMISSIONS` still 201, `PERMISSIONS`
  still 174; `AGENTS.md` carries the enforcement sentence and
  `test_docs_agents_md.py` asserts it; the PR body reproduces §9's production
  impact statement (intended loss of access for post-F5 roles lacking the
  permission, 403 plus the existing friendly denial, no backfill and no
  operator communication) and the three parity cells with old → new;
  `cd backend && TEST_POSTGRES_URL=... uv run pytest` is green at ≥ 90%
  coverage and `ruff check`/`ruff format --check` are clean.
- [ ] **ER-5 — The frontend loses nothing and no legacy role changes.**
  `git diff --stat` is empty for `frontend/src/` outside test files and for
  `frontend/src/i18n/`; `npm run lint`, `npm run build` and `npm run test` are
  green with coverage ≥ the base run; `ROUTE_ACCESS` and `NAV_ITEMS` are
  unchanged — including `"/packages": { module: "packages" }`, which already
  admits both `packages:read` and `packages:queue_read` (§8) — and every test
  profile still reaches every screen it reached before;
  `sha256(backend/tests/data/legacy_role_bundles.json)` is unchanged.
