# APRAS-44 — Implementar gestão de infrações com regras e escalonamento configuráveis por condomínio

> **One deliverable.** A per-tenant rule catalogue with a per-rule escalation
> policy, an infraction process whose current stage is *derived* from an
> append-only stage history, a stated next-step suggestion algorithm, the
> resident-side view with written contestation, and manual recidivism-cycle
> closing. **No ledger entry, no adjudication workflow, no notification
> channel outside the app.**

---

## 0. Preconditions, and how to read this spec against a moving tree

**Contracts, not files.** This spec is written at master `4f952b0` (IAM F1/F2
landed, F3 in the same worktree). APRAS-44 is **last** in the build lane. It
composes with five approved-but-unlanded specs, and every symbol this document
borrows from them is cited to the section that introduces it.

| Task | Spec | What APRAS-44 consumes from it |
|---|---|---|
| `APRAS-47` (IAM F3) | `docs/tasks/APRAS-47-spec.md` | `user.is_superuser` (migration `0031`), `deps.get_current_superuser`, `is_tenant_admin` ⇒ the whole catalogue in the acting tenant |
| `APRAS-48` (IAM F4) | `docs/tasks/APRAS-48-spec.md` | `GET /api/v1/permissions/me`; `AccessRule` / `ROUTE_ACCESS` / `NAV_ITEMS` (§5.2); `useCanAccess` / `useCanShowMenu` (§4.3); `ProtectedRoute`'s single `requiredAccess` prop (§5.1); the permission-label i18n block (§2.8) |
| `APRAS-49` (IAM F5) | `docs/tasks/APRAS-49-spec.md` | roles as data (`role` table, `user_role_link`); **no `UserRole` enum, no `allowed_menus`, no `assert_menu_access`, no `MenuKey`, no `LEGACY_ROLE_PERMISSIONS`**; `tests/data/legacy_role_bundles.json` (§7.6) as the only surviving statement of the old tiers; migrations `0032`/`0033`; the no-seeds doctrine |
| `APRAS-39` | `docs/tasks/APRAS-39-spec.md` | `MODULES` / `CORE_MODULES` / `TOGGLEABLE_MODULES` and `filter_by_modules` (§2.1); `tenant.disabled_modules`; the single strip inside `get_effective_permissions` (§5); `/admin/modules` (§10.3); migration `0034` |
| `APRAS-40` | `docs/tasks/APRAS-40-spec.md` | migration `0035`; the **additive parity-baseline mechanism** (§9.2) this task mirrors; `POST_0028_SCOPED_TABLES` (§9.3); the recorder's `--routes` / `--merge-base` flags and its `FROZEN` guard (§9.2.3) |

**All five land before this task.** Nothing here may be implemented until 47,
48, 49, 39 and 40 are merged.

**Rules for the implementer when the tree disagrees with this document.**

1. **Follow the landed name, not the predicted one.** Every symbol, path and
   revision id borrowed above is what those specs *say* they will land. If the
   tree spells one differently, use the tree's spelling and record the
   deviation in the PR body. The most likely ones are `role` vs `user_type`,
   `role_service.py` vs `user_type_service.py`, and the exact revision id of
   APRAS-40's migration.
2. **Follow the invariant, not the constant.** Every count in §11 is written
   as *merge-base ± N*. The predicted absolute values are guidance; **the
   deltas are the contract.** Measure the base at the actual merge base and
   quote both numbers in the PR body for every row.
3. **Never relitigate a landed decision.** APRAS-39's negative module storage
   and single strip point, APRAS-40's frozen F2 baseline, APRAS-49's no-seeds
   doctrine: all are preconditions here, not open questions. **This task adds
   no line to the permission resolver.**

**Verified against the current tree** (`4f952b0`), and therefore real today:
`app/core/permissions.py` (`PERMISSIONS`, `ROUTE_PERMISSIONS`,
`UNGUARDED_ROUTES`, `SCOPE_PERMISSIONS`, `module_of`, the naming convention in
the module docstring); `app/api/deps.py` (`has_permission`,
`require_permission`, `get_effective_permissions`, `get_current_tenant`);
`app/core/tenant_context.py` (`TENANT_SCOPED_MODELS` discovered from the
presence of a `tenant_id` column, `with_loader_criteria`, `before_flush`
stamping); `app/models/tenant.py::tenant_id_field()` (NOT NULL, indexed, FK to
`tenant.id` `ondelete="RESTRICT"`, `server_default` = the default tenant);
`app/models/occurrence.py` (`Occurrence`, `OccurrenceTimeline`,
`photo_urls_json`); `app/models/resident.py`; `app/models/lot.py`;
`app/models/media_asset.py` + `EntityType`; `app/api/v1/api.py`
(`TENANT_SCOPED` / `GLOBAL_SCOPED` mount lists);
`app/api/v1/endpoints/packages.py` (the `/my-lots` route-ordering precedent);
`tests/matrix_world.py` (`CELLS`, `PATH_PARAMS`, `REQUEST_BODIES`, `run_cell`,
one seeded row per path parameter, per-cell savepoint rollback);
`tests/tools/record_parity_baseline.py`; `tests/test_purchase_isolation.py`
(the APRAS-37 AST + row-count isolation precedent ER-5 names);
`tests/test_tenant_models.py` (the exhaustive-partition arithmetic).

**Also verified, and load-bearing:** the codebase has **no condominium fee**
anywhere. `grep -rn "condo_fee\|monthly_fee\|taxa" backend/app/models/` returns
nothing, and `Lot.is_delinquent`'s own comment says so in as many words —
*"Kept by hand by ADMINISTRATOR/DIRECTOR: APRAS has no per-lot billing to
derive it from."* §5 therefore introduces the fee reference explicitly rather
than pretending to read one. **Money is `float`** in this codebase
(`FinancialTransaction.amount`, `BudgetLine.planned_amount`,
`PurchaseQuote.unit_price`) and **enums are stored as `sa.String()` with a
`server_default`**, never as a Postgres `ENUM` type (migration `0027`). This
task follows both; a `Numeric` column here would be the only one in the tree.

---

## 1. Scope

### 1.1 What this task delivers

* **A. The three-layer model.** `InfractionRule` (per-tenant catalogue),
  `InfractionPolicyStep` (the ordered escalation ladder of one rule),
  `Infraction` + `InfractionStage` (the process and its append-only history),
  `InfractionContestation`, `InfractionCycleClose`, `InfractionSettings`.
  Seven tables, one reversible migration (§9).
* **B. One toggleable feature module `infractions`** under APRAS-39, with
  **13** new catalogue permissions and **18** new `ROUTE_PERMISSIONS` entries,
  all tenant-scoped (§3, §4).
* **C. The suggestion algorithm**, stated as arithmetic (§6), driving
  `GET /api/v1/infractions/{id}/next-step`. Staff confirm or override; the
  system never advances a process by itself.
* **D. The occurrence bridge** — `POST /api/v1/infractions/from-occurrence/{occurrence_id}`
  and a navigable link in both directions (§7.4).
* **E. The frontend** — `/infraction-rules` (catalogue + policy editor),
  `/infractions` (list + detail with the history timeline and the next-step
  panel), `/my-infractions` (resident view with the contestation form), plus
  the "Promover a infração" action on the occurrence detail. Menus derived
  from permissions (F4/F5), pt/en parity mechanically asserted (§10).
* **F. Documentation** — an AGENTS.md *Infrações* domain subsection, two
  endpoint-table rows, one row in APRAS-39's module table, and the
  recommended-bundle table (§8.3).

### 1.2 What this task explicitly does NOT deliver

See §13. In one line: **no ledger, no adjudication, no notifications outside
the app, and no seeded rules or policies.**

---

## 2. The five product decisions this spec implements, and does not reopen

Taken with the user on 2026-08-31 and recorded in the board justification.
They are inputs, not choices available to the implementer.

1. **The fine is isolated from Financeiro.** Applying a MULTA records a value,
   a date and the person it was applied against. It creates **no**
   `FinancialTransaction`, touches no finance table and imports no finance
   module. ER-5 makes this mechanical, exactly as APRAS-37 did
   (`tests/test_infraction_isolation.py`, §12.1).
2. **An occurrence can be promoted, and an infraction can be born direct.**
   The link is navigable in both directions and is never required.
3. **Defense is registration only.** A `NOTIFICACAO` step carries a
   per-rule deadline in days; the notified unit attaches a written
   contestation inside the deadline. There is no accept/reject, no
   adjudicator, no state the contestation moves the process into.
4. **Recidivism is personal, not `propter rem`.** Counted per
   **(rule, responsible person)**, never per lot. This follows the legal
   addendum: punitive conduct fines bind the offender (CC art. 1337
   *"reiteradamente"* is a property of a person), unlike quotas and late
   fees, which are `propter rem` (CC art. 1345). A sale or a tenant change
   therefore resets the ladder **by construction** — new responsible, new
   count — while the lot's history stays whole and navigable. **There is no
   reset button.**
5. **The current stage is derived, never stored.** `Infraction` carries no
   `status` and no `current_stage` column; the current stage is the last row
   of `infraction_stage`. Pinned by a column-set assertion (§12.2), because a
   convenience column added later is exactly how an append-only history stops
   being the truth.

---

## 3. The vocabulary: one module, 13 permissions

### 3.1 Why one module and not two

The dispatch brief suggested both `infractions:*` and `infraction_rules:*`.
**This spec uses one module, `infractions`, for the whole surface**, and the
reason is APRAS-39 §2.1: `MODULES` is *derived* — `frozenset(module_of(p) for p
in PERMISSIONS)` — so a second module segment would produce a second
independently-toggleable feature. A tenant with `infractions` on and
`infraction_rules` off would have a module that cannot be configured, and a
tenant with the inverse would have a catalogue nothing consumes. The brief
also requires (correctly) that this be *one* toggleable module.

The catalogue's own naming rule already covers it, verbatim from
`app/core/permissions.py`: *"Sub-resource CRUD carries the sub-resource in the
action (`projects:milestone_create`), never a second colon."* The rule
catalogue is a sub-resource of the infractions module, so it is
`infractions:rule_create`, on the `projects:milestone_create` precedent.

### 3.2 The 13 permissions

Added to `PERMISSIONS` in `app/core/permissions.py` as a new `# §4.24
infractions (APRAS-44)` block, after `access_control`:

```python
        # §4.24 infractions (APRAS-44)
        "infractions:read",
        "infractions:create",
        "infractions:advance",
        "infractions:promote",
        "infractions:contest",
        "infractions:cycle_close",
        "infractions:my_lots_read",
        "infractions:rule_read",
        "infractions:rule_create",
        "infractions:rule_update",
        "infractions:rule_deactivate",
        "infractions:policy_update",
        "infractions:settings_update",
```

| Permission | Guards |
|---|---|
| `infractions:read` | the management list, one infraction's detail, the next-step suggestion, the cycle-close audit list |
| `infractions:create` | registering an infraction directly |
| `infractions:advance` | appending a stage (applying AVISO / NOTIFICACAO / MULTA) |
| `infractions:promote` | turning an occurrence into an infraction |
| `infractions:contest` | attaching a written contestation |
| `infractions:cycle_close` | closing a responsible's recidivism cycle, with a justification |
| `infractions:my_lots_read` | the resident's read of the infractions of the lots they are linked to |
| `infractions:rule_read` | reading the rule catalogue and the module settings |
| `infractions:rule_create` / `rule_update` / `rule_deactivate` | the catalogue's writes |
| `infractions:policy_update` | replacing a rule's escalation ladder |
| `infractions:settings_update` | writing the condominium-fee reference |

`rule_deactivate`, not `rule_delete`: **`DELETE /api/v1/infraction-rules/{id}`
soft-deactivates** (`is_active = False`) because infractions reference rules
and ER-4 requires the lot's history to stay whole and navigable. The precedent
is `spaces:deactivate` behind `DELETE /api/v1/reservable-spaces/{space_id}`.

**None of the 13 is a `SCOPE_PERMISSION`** — every one guards a route, so
`test_permission_registry.py::test_every_catalogue_permission_is_reachable`,
whose body at `4f952b0` is
`set(ROUTE_PERMISSIONS.values()) | SCOPE_PERMISSIONS == PERMISSIONS`, stays
green with no amendment to the scope-permission exemption (the union's second
term is untouched because all 13 appear as `ROUTE_PERMISSIONS` values).
**None is superuser-only.**
**None goes into `ADMIN_GAP_PERMISSIONS`** — see §3.4.

### 3.3 The module is toggleable, and inherits every module mechanism for free

`MODULES` is derived (APRAS-39 §2.1), so `infractions` becomes a module the
moment the first permission exists, and `TOGGLEABLE_MODULES = MODULES -
CORE_MODULES` picks it up with **no code change**. What *does* need editing:

* APRAS-39 §2.2's toggleable table gains a row — `infractions` | 13 |
  `/infractions`, `/infraction-rules`, `/my-infractions` — and §2.3's
  companion list gains `occurrences → infractions` and `lots → infractions`
  (promotion source and lot reference; both couplings are safe and one
  checkbox to fix, per §2.3's own reasoning).
* APRAS-39 §12.1's asserted totals move (`MODULES` 27→28,
  `TOGGLEABLE_MODULES` 23→24, catalogue size, per-module sum). §11 states
  every one as a delta.
* APRAS-39 §10.3's `/admin/modules` checklist gains the `infractions`
  checkbox, in the `occurrences` cluster.

Turning `infractions` off strips all 13 from every non-superuser answer inside
`get_effective_permissions`; all 18 routes then answer the ordinary permission
refusal and the three frontend routes and their menu entries disappear. **This
task writes none of that** — it is APRAS-39 §5 doing its job.

### 3.4 `infractions:my_lots_read` is a filter, not an inverted gate

The brief points at `packages:my_lots_read` as the mirror. Mirror the *route
shape*, **not** its inversion. `PackageService.get_my_lots` actively *refuses*
the gatekeeper roles, which is why `packages:my_lots_read` is the one
permission `ADMINISTRATOR` does not hold and why it sits in
`ADMIN_GAP_PERMISSIONS`.

Here the route **narrows** instead: `GET /api/v1/infractions/my-lots` returns
the infractions of the lots the caller is linked to through `UserLotLink`, for
every caller, refusing nobody — a staff member with no linked lot gets `[]`.
The precedent is `gate:logs_read`, whose catalogue comment already says
*"Filter, not refusal … at `lot_id=None` no role is refused"*. Consequences,
all of them good: `ADMIN_GAP_PERMISSIONS` stays a one-element set;
`role_service.assert_can_grant` (post-F5) needs no amendment; and the matrix
cell for the `ADMINISTRATOR` profile is a plain **200**, not a bespoke denial
shape needing a `DENIAL_SHAPE_OVERRIDES` entry.

---

## 4. The API — 18 routes, two routers, both tenant-scoped

### 4.1 The routers

Two new endpoint modules, mounted in `app/api/v1/api.py` with
`dependencies=TENANT_SCOPED` (every table is tenant-scoped or inherits a
tenant-scoped parent; nothing here is global):

```python
api_router.include_router(
    infractions.rules_router,
    prefix="/infraction-rules",
    tags=["infraction-rules"],
    dependencies=TENANT_SCOPED,
)
api_router.include_router(
    infractions.settings_router,
    prefix="/infraction-settings",
    tags=["infraction-rules"],
    dependencies=TENANT_SCOPED,
)
api_router.include_router(
    infractions.router,
    prefix="/infractions",
    tags=["infractions"],
    dependencies=TENANT_SCOPED,
)
```

Three mounts, one file (`app/api/v1/endpoints/infractions.py`). The settings
singleton gets its own mount because its two routes hang off the collection
path itself, which a prefix cannot express twice.

### 4.2 `ROUTE_PERMISSIONS` — the 18 new entries, verbatim

```python
    # §4.24 infraction rules & policy -- /api/v1/infraction-rules (APRAS-44)
    ("GET", "/api/v1/infraction-rules"): "infractions:rule_read",
    ("GET", "/api/v1/infraction-rules/{rule_id}"): "infractions:rule_read",
    ("POST", "/api/v1/infraction-rules"): "infractions:rule_create",
    ("PUT", "/api/v1/infraction-rules/{rule_id}"): "infractions:rule_update",
    ("DELETE", "/api/v1/infraction-rules/{rule_id}"): "infractions:rule_deactivate",
    ("PUT", "/api/v1/infraction-rules/{rule_id}/policy"): "infractions:policy_update",
    # §4.24 module settings -- the condominium-fee reference (§5)
    ("GET", "/api/v1/infraction-settings"): "infractions:rule_read",
    ("PUT", "/api/v1/infraction-settings"): "infractions:settings_update",
    # §4.24 infractions -- /api/v1/infractions
    ("GET", "/api/v1/infractions"): "infractions:read",
    ("GET", "/api/v1/infractions/my-lots"): "infractions:my_lots_read",
    ("GET", "/api/v1/infractions/cycles"): "infractions:read",
    ("GET", "/api/v1/infractions/{infraction_id}"): "infractions:read",
    ("GET", "/api/v1/infractions/{infraction_id}/next-step"): "infractions:read",
    ("POST", "/api/v1/infractions"): "infractions:create",
    (
        "POST",
        "/api/v1/infractions/from-occurrence/{occurrence_id}",
    ): "infractions:promote",
    ("POST", "/api/v1/infractions/{infraction_id}/stages"): "infractions:advance",
    (
        "POST",
        "/api/v1/infractions/{infraction_id}/contestation",
    ): "infractions:contest",
    ("POST", "/api/v1/infractions/cycles/close"): "infractions:cycle_close",
```

`UNGUARDED_ROUTES` grows by **zero**: every route is authenticated and makes a
permission decision.

**Route declaration order is a correctness requirement, not style.**
`/my-lots`, `/cycles`, `/cycles/close` and `/from-occurrence/{occurrence_id}`
must be declared **before** `/{infraction_id}` and `/{infraction_id}/…`, or
FastAPI matches the literal segments as a UUID path parameter and answers 422.
This is the `packages.py` precedent, where `/queue` and `/my-lots` precede
`/{package_id}`. A test pins it (§12.2).

### 4.3 Guards

Every handler carries `Depends(deps.require_permission("<the route's own
permission>"))` — the route-level guard, never a role comparison and never a
shared helper that collapses several permissions into one. The
`occurrences.py::_assert_not_porteiro` shape (one helper, each call site
passing *its own* permission) is acceptable only where an in-handler check is
genuinely needed; here the route guard suffices everywhere, so no such helper
is written.

Object-dimension narrowing that is **not** a permission and stays in service
code. The list is **exhaustive**:

1. `GET /infractions/my-lots` filters to the caller's linked lots (§7.6);
2. `POST /infractions/{id}/contestation` **refuses** a caller not linked to the
   infraction's lot — 403, the same predicate as (1), applied to every caller
   including a superuser and a tenant admin (§7.5);
3. the contestation deadline check (§7.5);
4. the cross-tenant impossibility, which `tenant_context`'s loader criteria
   already give for free.

One helper serves (1) and (2), so they cannot drift apart: §7.6.

### 4.4 Request / response schemas — `app/schemas/infraction.py`

```python
class InfractionRuleBase(SQLModel):
    article: str                       # "art. 12, §2º"
    origin: InfractionRuleOrigin       # ESTATUTO | REGIMENTO_INTERNO | CONVENCAO
    description: str
    recidivism_window_days: int        # > 0
    is_active: bool = True

class InfractionRuleCreate(InfractionRuleBase): ...
class InfractionRuleUpdate(SQLModel):            # every field optional
    article: str | None = None
    origin: InfractionRuleOrigin | None = None
    description: str | None = None
    recidivism_window_days: int | None = None
    is_active: bool | None = None

class InfractionPolicyStepWrite(SQLModel):
    step_order: int                    # >= 1, contiguous from 1, unique
    action: InfractionStepAction       # AVISO | NOTIFICACAO | MULTA
    defense_deadline_days: int | None = None   # required iff action is NOTIFICACAO
    fine_mode: InfractionFineMode | None = None  # required iff action is MULTA
    fine_fixed_amount: float | None = None       # required iff fine_mode is FIXED
    fine_fee_multiplier: float | None = None     # required iff fine_mode is MULTIPLE
    note: str | None = None

class InfractionPolicyWrite(SQLModel):
    steps: list[InfractionPolicyStepWrite]      # 1..20, replaces the ladder whole

class InfractionPolicyStepRead(InfractionPolicyStepWrite):   # NEW
    id: UUID

class InfractionRuleRead(InfractionRuleBase):
    id: UUID
    steps: list[InfractionPolicyStepRead]       # ordered by step_order
    created_at: datetime
    updated_at: datetime

class InfractionRuleSummaryRead(SQLModel):      # NEW
    id: UUID
    article: str
    origin: InfractionRuleOrigin
    description: str

class ResidentSummaryRead(SQLModel):            # NEW -- does NOT exist at 4f952b0
    id: UUID                                    # (only ResidentRead does,
    full_name: str                              #  app/schemas/resident.py:75)
    lot_id: UUID

class InfractionSettingsRead(SQLModel):
    condo_fee_amount: float | None
    updated_at: datetime | None
    updated_by: UserSummaryRead | None

class InfractionSettingsWrite(SQLModel):
    condo_fee_amount: float | None      # None clears it

class InfractionCreate(SQLModel):
    rule_id: UUID
    lot_id: UUID
    responsible_resident_id: UUID
    occurred_on: date
    description: str
    evidence_urls: list[str] = []
    # REMOVED in implementation: a field accepted and silently dropped is a
    # lie to the caller. An infraction born of an occurrence is created by
    # POST /infractions/from-occurrence/{id}, which is the route that
    # resolves the effective lot and writes the OccurrenceTimeline note.

class InfractionPromote(SQLModel):
    rule_id: UUID
    responsible_resident_id: UUID
    lot_id: UUID | None = None          # effective-lot rule, §7.4 (B1)
    description: str | None = None      # defaults to the occurrence's description
    occurred_on: date | None = None     # defaults to the occurrence's created_at date

class InfractionStageCreate(SQLModel):
    action: InfractionStepAction | None = None   # None => accept the suggestion
    note: str
    fine_amount: float | None = None             # overrides the computed amount
    evidence_urls: list[str] = []

class ContestationCreate(SQLModel):
    body: str                                    # non-empty
    attachment_urls: list[str] = []

class CycleCloseCreate(SQLModel):
    rule_id: UUID
    responsible_resident_id: UUID
    lot_id: UUID | None = None                   # audit context only, NOT the
                                                 # predicate -- §6.2, §7.2
    justification: str                           # non-empty; ER-9

class NextStepRead(SQLModel):                    # 12 fields
    recidivism_count: int
    window_start: date
    cycle_closed_at: datetime | None
    stages_applied: int
    ladder_index: int
    suggested_step_order: int | None
    suggested_action: InfractionStepAction | None
    reason: NextStepReason        # SUGGESTED | NO_POLICY | CLAMPED -- §6.5
    defense_deadline_days: int | None
    fine_amount: float | None
    fine_amount_unavailable_reason: str | None    # "CONDO_FEE_NOT_SET" | None
    is_saturated: bool

class InfractionRead(SQLModel):
    id: UUID
    rule: InfractionRuleSummaryRead
    lot: LotSummaryRead
    responsible: ResidentSummaryRead
    occurred_on: date
    description: str
    evidence_urls: list[str]
    source_occurrence_id: UUID | None
    source_occurrence_protocol: str | None
    current_stage: InfractionStepAction | None      # DERIVED (§7.3)
    current_stage_at: datetime | None               # DERIVED
    defense_due_on: date | None                     # DERIVED (§7.5)
    timeline: list[InfractionTimelineEntryRead]     # stages + contestations, merged
    created_at: datetime
```

`InfractionTimelineEntryRead` is a flat, discriminated shape —
`{kind: "STAGE" | "CONTESTATION", at, actor, action, note, fine_amount,
defense_due_on, attachment_urls}` — so the frontend timeline renders one list
with no client-side merge.

**The two list shapes, stated so neither is inferred.**
`PaginatedInfractionRead` follows `PaginatedPackageRead` verbatim — `items:
list[InfractionRead]`, `total: int`, `skip: int`, `limit: int` — and is the
declared `response_model` of **`GET /api/v1/infractions`** (§4.5).
**`GET /api/v1/infractions/my-lots` is a bare `list[InfractionRead]`**, not
paginated and not filtered by any query parameter: it is the resident's own
short list, its size is bounded by the caller's lot links, and the packages
precedent (`GET /api/v1/packages/my-lots`) returns a bare list too. A staff
member with no linked lot gets `[]`; nobody is refused (§3.4).

**Evidence reuses the existing media pipeline, adding no table.**
`EntityType` gains `INFRACTION = "INFRACTION"`; the client uploads through the
existing `POST /api/v1/uploads/photo` and passes the returned URLs in
`evidence_urls`. Storage mirrors `Occurrence.photo_urls_json` exactly: a
`str | None` JSON column, serialised by the service. No new upload route, no
new upload permission, no change to `MediaService`.

### 4.5 `GET /api/v1/infractions` — the full query contract

The management list is the only route in this module with query parameters.
**Every one is optional**, and the signature follows the tree's own convention
verbatim — `skip`/`limit`, **not** `page`/`page_size`: `packages.py:38–45` and
`occurrences.py:47–53` at `4f952b0` both declare
`skip: int = Query(default=0, ge=0)` and a bounded `limit`, and both return a
`Paginated…Read` carrying `items`/`total`/`skip`/`limit`. *(Corrected in
implementation: `uploads.py:40` does declare a `page` parameter, so "there is
no `page`/`page_size` route anywhere" was an overstatement. `page_size` exists
nowhere, every paginated collection in the codebase is `skip`/`limit`, and
introducing a second convention here would still make this the only endpoint a
client paginates differently — the conclusion is unchanged.)*

```python
@router.get("", response_model=PaginatedInfractionRead)
def list_infractions(
    ...,
    rule_id: UUID | None = Query(default=None),
    lot_id: UUID | None = Query(default=None),
    responsible_id: UUID | None = Query(default=None),   # -> responsible_resident_id
    stage: InfractionStageFilter | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> PaginatedInfractionRead:
```

| Parameter | Type | Meaning |
|---|---|---|
| `rule_id` | `UUID?` | `infraction.rule_id == rule_id` |
| `lot_id` | `UUID?` | `infraction.lot_id == lot_id` — **the parameter ER-4 asserts** |
| `responsible_id` | `UUID?` | `infraction.responsible_resident_id == responsible_id` |
| `stage` | `InfractionStageFilter?` | the **derived** current stage — `AVISO` \| `NOTIFICACAO` \| `MULTA` \| `NONE` (no stage applied yet) |
| `date_from` | `date?` | `infraction.created_at >= datetime.combine(date_from, time.min)` |
| `date_to` | `date?` | `infraction.created_at < datetime.combine(date_to + 1 day, time.min)` — inclusive of the whole end day |
| `skip` | `int = 0`, `ge=0` | offset |
| `limit` | `int = 50`, `ge=1`, `le=100` | page size |

Ordering is `created_at DESC, id DESC` (stable, so `skip`/`limit` cannot skip
or repeat a row). `total` is the count **after** every filter and **before**
`skip`/`limit`. Present filters compose with `AND`; absent ones add no clause.
An unknown `stage` value is FastAPI's ordinary 422.

**`InfractionStageFilter` is a new `StrEnum`** (§7.1) rather than a reuse of
`InfractionStepAction`, because `NONE` is not a step action and putting it in
`InfractionStepAction` would make an unappliable action storable in
`infraction_stage.action`.

**The `stage` filter is computed, never stored.** Decision 5 of §2 stands:
there is no `current_stage` column and this filter does not create one. It is a
correlated subquery selecting the id of the latest stage row per infraction,
ordered exactly as §7.3 orders it:

```python
latest_stage_id = (
    select(InfractionStage.id)
    .where(InfractionStage.infraction_id == Infraction.id)   # correlated
    .order_by(
        InfractionStage.applied_on.desc(),
        InfractionStage.created_at.desc(),
        InfractionStage.id.desc(),
    )
    .limit(1)
    .correlate(Infraction)
    .scalar_subquery()
)

if stage is InfractionStageFilter.NONE:
    statement = statement.where(~exists().where(
        InfractionStage.infraction_id == Infraction.id
    ))
else:
    statement = statement.where(
        select(InfractionStage.action)
        .where(InfractionStage.id == latest_stage_id)
        .scalar_subquery() == stage.value
    )
```

Both branches are one statement, evaluated by the database; neither
materialises a Python list of ids and neither writes anything. The
`ix_infraction_stage_infraction_id` index of §7.2 is what makes the correlated
lookup cheap.

**`matrix_world.QUERY_PARAMS` is untouched** — it exists only for routes with a
**required** query parameter, and every parameter here is optional, so the
matrix cell for `GET /api/v1/infractions` sends no query string and answers 200
(§8.4). Stated again in §12.6 so the implementer does not add an entry
defensively.

---

## 5. The condominium-fee reference — an explicit parameter, because there is none to read

ER-2 requires a fine expressed as a *multiple of the condominium fee*. §0
established that no such value exists anywhere in the tree. Three options were
considered and two rejected:

* **Store the fee on the policy step.** Rejected: `MULTIPLE` would then be
  arithmetically identical to `FIXED`, which is a lie in the schema.
* **Add `tenant.condo_fee_amount`.** Rejected: `tenant` is a global,
  superuser-managed table (APRAS-39 §6, APRAS-40 §3), and the condominium fee
  is operational data owned by the síndico, not by the SaaS operator. Writing
  it would need a superuser-only route on the global tenants router — the
  wrong audience.
* **Adopted: a tenant-scoped singleton `infraction_settings` row**, owned by
  the `infractions` module, written by `infractions:settings_update`
  (recommended: ADMINISTRATOR/DIRECTOR). It is toggled off with the module,
  isolated from Financeiro, and reachable by exactly the people who configure
  the ladder.

`GET /api/v1/infraction-settings` **never 404s**: an absent row reads as
`{condo_fee_amount: null, updated_at: null, updated_by: null}`. `PUT` upserts
and answers 200. The row is materialised lazily, on first `PUT`, so no seed
and no migration data step exist.

**The applied amount is frozen.** When a `MULTA` stage is written, the
computed value is stored on `infraction_stage.fine_amount`. A later change to
`condo_fee_amount` therefore never rewrites history — the same reason
`defense_due_on` is frozen (§7.5).

---

## 6. The next-step suggestion algorithm, stated as arithmetic

`InfractionService.suggest_next_step(session, infraction) -> NextStepRead`.
Pure with respect to the database: it reads and computes, never writes.

### 6.1 Two escalations, one ordinal

The domain has two escalations that must not be modelled twice:

* **across infractions** — a repeat offender starts further up the ladder
  ("dois avisos antes", CC art. 1337 *reiteradamente*);
* **within one process** — staff advance AVISO → NOTIFICACAO → MULTA on a
  single infraction.

They are collapsed into one 1-based ordinal:

```
ladder_index(I) = recidivism_count(I) + stages_applied(I) + 1
suggested_step  = steps_by_order[min(ladder_index, n)]   # n = len(steps)
is_saturated    = n > 0 and ladder_index >= n
```

`steps_by_order` is **keyed by `step_order`, which is 1-based and contiguous
from 1** (§4.4's `InfractionPolicyStepWrite`), so `min(ladder_index, n)` is a
`step_order` and never a Python list index. Written as a list lookup it would
be `steps[min(ladder_index, n) - 1]`; the dict spelling is used precisely so
the off-by-one cannot be introduced. `n = 0` is a real, reachable state and is
handled in §6.5, not here.

* First infraction, nothing applied → index 1 → step 1 (AVISO).
* Advance it once → index 2 → step 2 (NOTIFICACAO).
* A **second** infraction of the same rule by the same person, nothing applied
  → `recidivism_count = 1` → index 2 → NOTIFICACAO directly: the ladder is not
  climbed twice from the bottom.
* The ladder **saturates** at the last step: `min(...)` means the final
  sanction repeats indefinitely. No `repeat_last_step` column is added — a
  condominium cannot run out of sanctions, and a flag whose only false value
  means "the process becomes unadvanceable" is not a real choice.

`stages_applied(I)` counts rows of `infraction_stage` for `I`. Contestations
live in their own table and never move the ladder (decision 3 of §2).

### 6.2 `recidivism_count` — the exact predicate

For infraction `I` with rule `R`, responsible `P` and date `D = I.occurred_on`:

```
window_start   = D - timedelta(days=R.recidivism_window_days)
cycle_closed_at = max(C.closed_at for C in InfractionCycleClose
                      if C.rule_id == R.id
                     and C.responsible_resident_id == P.id
                     and C.closed_at <= I.created_at)          # or None

recidivism_count = count of Infraction J where
      J.rule_id                 == R.id
  and J.responsible_resident_id == P.id
  and J.id                      != I.id
  and J.occurred_on             >= window_start
  and J.occurred_on             <  D                 # strictly earlier
  and (cycle_closed_at is None or J.created_at > cycle_closed_at)
```

Six properties, each of which is a test in `tests/test_infraction_escalation.py`
(§12.1):

1. **`lot_id` is absent from the predicate.** This is ER-4's core claim and
   the legal addendum's: the count is `(rule, responsible)`, never
   `(rule, lot)`. A sale or a tenant change means a different
   `responsible_resident_id`, so the ladder resets **with no code path that
   resets anything** — and the lot's history stays whole, because
   `GET /api/v1/infractions?lot_id=…` still lists every infraction of the lot.
2. **The window is anchored on `I.occurred_on`, not on today**, so a
   suggestion computed twice on different days for the same infraction gives
   the same answer.
3. **Strict `<`** on the date, so same-day infractions do not count each
   other symmetrically. Ties are unordered by design and the assertion is that
   neither counts the other.
4. **A closed cycle is a cutoff, not a deletion**: `J.created_at >
   cycle_closed_at` excludes prior infractions from the count while every row
   stays readable (ER-9). It is a **cutoff on `I.created_at` too**
   (`C.closed_at <= I.created_at`), so an infraction that already existed when
   the cycle was closed is unaffected by it and keeps its `recidivism_count`,
   its `stages_applied` and its `ladder_index`. Only an infraction **registered
   after** the close starts from `recidivism_count == 0` /
   `ladder_index == 1`. This is deliberate: the close ends a cycle going
   forward, it does not retroactively rewrite a process already under way.
   ER-9 says so in those words.
5. **`InfractionCycleClose.lot_id` is audit context and is deliberately absent
   from the predicate.** Decision 4 of §2 makes recidivism personal — per
   `(rule, responsible)` — so matching on the lot as well would silently make
   it `propter rem` again for anyone who moved. The column is therefore
   **optional** (§7.2, §4.4): it records *where* the síndico observed the
   change of responsible, and nothing reads it but the audit list. An
   implementer adding `C.lot_id == I.lot_id` to the match above is changing the
   product decision, not fixing an omission.
6. Every `J` counts regardless of how far its own process advanced. An
   infraction is a recorded infraction; requiring it to have reached some
   stage would make the count depend on staff diligence rather than on facts.

The whole query runs under the session's acting tenant, so cross-tenant rows
are structurally invisible (`tenant_context._apply_tenant_filter`); the
service adds no `tenant_id` clause of its own.

### 6.3 The fine amount

```
step.fine_mode == FIXED     -> amount = step.fine_fixed_amount
step.fine_mode == MULTIPLE  -> amount = round(step.fine_fee_multiplier
                                              * settings.condo_fee_amount, 2)
```

If `fine_mode == MULTIPLE` and `condo_fee_amount is None`, `NextStepRead`
answers `fine_amount = null` and
`fine_amount_unavailable_reason = "CONDO_FEE_NOT_SET"`, and
`POST /api/v1/infractions/{id}/stages` with a `MULTA` action and **no explicit
`fine_amount`** answers **409** with detail
`"The condominium fee reference is not set"`. Staff may always pass an
explicit `fine_amount`, which wins over the computed one and is recorded as
such (`infraction_stage.fine_amount_overridden = True`).

### 6.4 What the algorithm never does

It never writes, never advances a process, never sends anything. ER-4's *"quem
avança pode confirmar a sugestão"* is implemented as: `POST /stages` with
`action = null` applies the suggestion; `POST /stages` with an explicit
`action` applies that one and records `suggestion_followed = False` on the
stage row, so a deviation from policy is itself auditable.

### 6.5 `reason`, and the empty ladder (`n = 0`)

A rule with **zero** policy steps is a normal, reachable state, not an error to
be designed around: `InfractionRuleCreate` has no `steps` field (§4.4), the
ladder is written by a separate route (`PUT …/policy`), and nothing forbids
registering an infraction the moment the rule exists. Forbidding it would mean
a rule that cannot be used until a second, unrelated call succeeds. So the
empty ladder is **answered**, not prevented, and `NextStepRead.reason` says
which of the three cases the caller is in.

```python
class NextStepReason(StrEnum):
    SUGGESTED = "SUGGESTED"    # n > 0 and ladder_index <= n
    NO_POLICY = "NO_POLICY"    # n == 0 -- the rule has no ladder
    CLAMPED   = "CLAMPED"      # n > 0 and ladder_index > n -- the last step repeats
```

`reason` is total: exactly one value holds for any infraction, and it is
derivable from `n` and `ladder_index` alone.

**`reason` and `is_saturated` are not the same predicate, and neither replaces
the other.** `is_saturated` is `n > 0 and ladder_index >= n` (§6.1); `CLAMPED`
is `ladder_index > n`. They disagree at exactly `ladder_index == n`: the last
step **is** the suggestion — saturated, because there is nothing above it, but
not clamped, because nothing was truncated. Collapsing the two would make the
UI say "a política acabou" on the very first application of the last step.

**`GET /infractions/{id}/next-step` with `n = 0` answers 200**, never 404 and
never 409 — a read of a legitimate state — with this exact payload:

| Field | Value at `n = 0` |
|---|---|
| `recidivism_count`, `window_start`, `cycle_closed_at`, `stages_applied` | computed normally (§6.2); they do not depend on the ladder |
| `ladder_index` | computed normally — `recidivism_count + stages_applied + 1` |
| `suggested_step_order` | `null` |
| `suggested_action` | `null` |
| `reason` | `"NO_POLICY"` |
| `defense_deadline_days` | `null` |
| `fine_amount` | `null` |
| `fine_amount_unavailable_reason` | `null` — the fee is not the reason; there is no step to price |
| `is_saturated` | `false` — an absent ladder is not an exhausted one (`n > 0` is in the definition, §6.1) |

**`POST /infractions/{id}/stages` distinguishes the two intents.**

* `action = null` means *"apply the suggestion"*. With `n = 0` there is no
  suggestion, so the request cannot be honoured: **409**, detail
  `"Rule has no escalation policy"`. Not 422 — the body is shape-valid; it is
  the world that has no answer, exactly as the `MULTA`-without-a-fee case is a
  409 (§6.3).
* An **explicit `action` is always accepted**, at `n = 0` as at any other `n`.
  ER-3 is that staff advance the process; the ladder is a suggestion engine,
  not a gate on staff judgement. The stage is written with
  `policy_step_order = null` and `suggestion_followed = False`.

The same 409 shape, and the same explicit-action escape, is why `CLAMPED` needs
no special handling: at `ladder_index > n` there **is** a suggestion — the last
step, repeated (§6.1) — so `action = null` applies it.

---

## 7. The model — `app/models/infraction.py`

All seven tables follow the house shape: `id: UUID` primary key with
`default_factory=uuid4`, `created_at` via `default_factory=datetime.utcnow`,
enums typed as the Python `StrEnum` and stored as `sa.String()`.
**`updated_at` is on six of the seven**: `infraction_stage` deliberately has
none, because the history is append-only in the schema and not only in the
handlers (§12.2). *(Corrected in implementation: the original sentence said
"all seven" and contradicted both §12.2 and §7.2's own column lists. The
`server_default` clause is also dropped — none of the three persisted enums has
a Python-side default either, and migration `0035`'s precedent is to add one
only where the model has one, so that the SQLite schema `create_all()` builds
and the Postgres schema Alembic builds stay identical.)*

### 7.1 Enums — `app/models/enums.py`

```python
class InfractionRuleOrigin(StrEnum):
    ESTATUTO = "ESTATUTO"
    REGIMENTO_INTERNO = "REGIMENTO_INTERNO"
    CONVENCAO = "CONVENCAO"

class InfractionStepAction(StrEnum):
    AVISO = "AVISO"
    NOTIFICACAO = "NOTIFICACAO"
    MULTA = "MULTA"

class InfractionFineMode(StrEnum):
    FIXED = "FIXED"
    MULTIPLE = "MULTIPLE"

class NextStepReason(StrEnum):          # response-only, no column (§6.5)
    SUGGESTED = "SUGGESTED"
    NO_POLICY = "NO_POLICY"
    CLAMPED = "CLAMPED"

class InfractionStageFilter(StrEnum):   # query-only, no column (§4.5)
    AVISO = "AVISO"
    NOTIFICACAO = "NOTIFICACAO"
    MULTA = "MULTA"
    NONE = "NONE"
```

plus `EntityType.INFRACTION = "INFRACTION"` (§4.4).

`NextStepReason` and `InfractionStageFilter` are **not stored anywhere**: the
first is a response field, the second a query parameter. Neither appears in a
column, so neither needs a `server_default` and neither reaches the migration.
Only `InfractionRuleOrigin`, `InfractionStepAction` and `InfractionFineMode`
are persisted, as `sa.String()` (§9).

### 7.2 The tables

| Table | Scope | Key columns |
|---|---|---|
| `infraction_rule` | **direct** (`tenant_id_field()`) | `article`, `origin`, `description`, `recidivism_window_days`, `is_active`, `created_at`, `updated_at` |
| `infraction_policy_step` | **inherited** via `rule_id` NOT NULL → `infraction_rule.id` `ondelete="CASCADE"` | `step_order`, `action`, `defense_deadline_days`, `fine_mode`, `fine_fixed_amount`, `fine_fee_multiplier`, `note` |
| `infraction` | **direct** | `rule_id` → `infraction_rule.id` `RESTRICT`; `lot_id` → `lot.id` `RESTRICT`; `responsible_resident_id` → `resident.id` `RESTRICT`; `source_occurrence_id` → `occurrence.id` `SET NULL`, nullable; `registered_by_id` → `user.id` `RESTRICT`; `occurred_on: date`, `description`, `evidence_urls_json` |
| `infraction_stage` | **inherited** via `infraction_id` NOT NULL → `infraction.id` CASCADE | `action`, `applied_on: date`, `note`, `actor_id` → `user.id` `RESTRICT`, `fine_amount: float \| None`, `fine_amount_overridden: bool`, `defense_due_on: date \| None`, `policy_step_order: int \| None`, `suggestion_followed: bool`, `evidence_urls_json`, `created_at` |
| `infraction_contestation` | **inherited** via `infraction_id` NOT NULL | `stage_id` → `infraction_stage.id` `RESTRICT` (the NOTIFICACAO it answers), `body`, `attachment_urls_json`, `submitted_by_id` → `user.id` `RESTRICT`, `created_at` |
| `infraction_cycle_close` | **direct** | `rule_id` → `infraction_rule.id` `RESTRICT`, `lot_id` → `lot.id` `RESTRICT`, **nullable** (audit context only — §6.2 property 5), `responsible_resident_id` → `resident.id` `RESTRICT`, `justification`, `closed_by_id` → `user.id` `RESTRICT`, `closed_at: datetime` |
| `infraction_settings` | **direct**, one row per tenant | `condo_fee_amount: float \| None`, `updated_by_id` → `user.id` `SET NULL`, `updated_at` |

**Why `infraction_cycle_close` and `infraction_settings` are directly scoped**,
per AGENTS.md's stated rule (*"a table carries its own `tenant_id` when it is
reachable by a route that lists it or fetches it by its own id without a
scoped parent's id in the path"*): `GET /api/v1/infractions/cycles` lists cycle
closes with no parent id in the path, and `GET /api/v1/infraction-settings`
fetches the singleton with no path parameter at all. `infraction_policy_step`,
`infraction_stage` and `infraction_contestation` are reached only through
their parent's id and therefore carry **no** `tenant_id`: duplicating it would
create a second, forgeable source of truth that can disagree with the parent.

Indexes: `tenant_id` (from `tenant_id_field()`), plus
`ix_infraction_rule_id`, `ix_infraction_lot_id`,
`ix_infraction_responsible_resident_id`, `ix_infraction_occurred_on`,
`ix_infraction_source_occurrence_id`, `ix_infraction_stage_infraction_id`,
`ix_infraction_contestation_infraction_id`,
`ix_infraction_cycle_close_rule_id`,
`ix_infraction_cycle_close_responsible_resident_id`. The composite
`ix_infraction_recidivism` on `(tenant_id, rule_id, responsible_resident_id,
occurred_on)` is what §6.2's count reads.

Uniqueness, all per-tenant (the AGENTS.md convention):

```python
UniqueConstraint("tenant_id", "origin", "article",
                 name="uq_infraction_rule_tenant_origin_article")
UniqueConstraint("rule_id", "step_order",
                 name="uq_infraction_policy_step_rule_order")
UniqueConstraint("tenant_id", name="uq_infraction_settings_tenant")
```

Two condominiums may both cite "art. 12 do Regimento Interno"; one may not
cite it twice.

### 7.3 The derived current stage

`InfractionService._current_stage(infraction)` = the last row of
`infraction_stage` ordered by `(applied_on, created_at, id)`. `InfractionRead`
carries `current_stage` and `current_stage_at` computed at serialisation time.
`Infraction` has **no** `status` and **no** `current_stage` column, and there
is **no** route that updates or deletes a stage. Both are asserted (§12.2).

### 7.4 The occurrence bridge

`POST /api/v1/infractions/from-occurrence/{occurrence_id}` reads the
occurrence (404 if absent in the acting tenant), resolves the **effective lot**
(below), defaults `description` and `occurred_on` from it, sets
`source_occurrence_id`, and writes an `OccurrenceTimeline` note recording the
promotion, using the occurrence module's existing timeline shape and its
existing service. **The same occurrence may be promoted more than once** (one
incident can breach two rules); the link is 1:N from the occurrence's side.

**The effective lot, because `Occurrence.lot_id` is nullable.** At `4f952b0`,
`app/models/occurrence.py:36` declares `lot_id: UUID | None = Field(default=None,
foreign_key="lot.id", ondelete="SET NULL", nullable=True, index=True)` — a
common-area or public occurrence legitimately has no lot — while
`infraction.lot_id` is **NOT NULL** (§7.2), because an infraction is always
against a unit. The promotion therefore cannot simply "copy `lot_id`".
`InfractionPromote.lot_id` is optional (§4.4) and the rule is:

| `body.lot_id` | `occurrence.lot_id` | Result |
|---|---|---|
| absent | present | **effective lot = `occurrence.lot_id`** — the ordinary case, the caller types nothing |
| present | absent | **effective lot = `body.lot_id`** — a common-area occurrence attributed to a unit |
| present | present, **equal** | effective lot = that lot |
| present | present, **different** | **422**, detail `"lot_id does not match the occurrence's lot"` |
| absent | absent | **422**, detail `"The occurrence has no lot; lot_id is required"` |

Both mismatches are **422 and not a silent override**: the promotion is an
attribution of responsibility to a unit, and a caller who names a different
unit from the one the occurrence records has either mis-clicked or is
correcting the occurrence — and correcting the occurrence is the occurrence
module's job, not this route's. `responsible_resident_id` stays **required** in
the body either way (an occurrence names no responsible person), and §7.7's two
create-time validations — active rule, responsible belongs to the effective
lot — apply here exactly as they do on `POST /infractions`.

`OccurrenceDetailRead` gains `infraction_ids: list[UUID]` — a read-only,
additive field, so no existing occurrence test changes. `InfractionRead`
carries `source_occurrence_id` and `source_occurrence_protocol`, which is what
makes the link navigable in both directions in the UI without a second fetch.

### 7.5 Deadline and contestation

Applying a `NOTIFICACAO` stage freezes
`defense_due_on = applied_on + timedelta(days=step.defense_deadline_days)` on
the stage row. `InfractionRead.defense_due_on` is the `defense_due_on` of the
**most recent** `NOTIFICACAO` stage, or `null`.

`POST /api/v1/infractions/{id}/contestation`, **in this order**:

* **404** when the infraction is not visible in the acting tenant;
* **403** `"Only the notified unit may contest this infraction"` when the
  caller is not linked to `infraction.lot_id` (§7.6);
* **409** `"No open defense deadline"` when there is no `NOTIFICACAO` stage;
* **409** `"The defense deadline has passed"` when `date.today() >
  defense_due_on`;
* **201** otherwise, appending an entry visible in `timeline` with
  `kind = "CONTESTATION"`.

**Who may contest: the notified unit, and nobody else.** Decision 3 of §2 says
*"the notified unit attaches a written contestation inside the deadline"*, and
`infractions:contest` alone does not say *which* infraction — without the
object check any resident holding it could post onto a neighbour's process
given only its UUID. So the permission is necessary and **not sufficient**: the
caller must also be linked to the infraction's lot, by the **same predicate
`my-lots` uses** (§7.6), or the route answers 403 before it looks at the
deadline.

**This applies to every caller, including `is_superuser` and
`is_tenant_admin`.** Those two short-circuit `get_effective_permissions` and
therefore always hold `infractions:contest` — but the check here is not a
permission check, it is an object check, and a contestation is *the unit's own
act*: signing one on a unit's behalf is a different thing from being allowed to
administer the condominium. An implementer must **not** add a superuser
bypass to this branch. The staff members who legitimately need it are already
covered in practice, because staff who live in the condominium have their own
`UserLotLink` / `Resident` rows.

**Staff registering a contestation on the unit's behalf** — a defense that
arrives on paper at the office — is **Out of Scope** (§13). It needs a
different route with its own permission and an on-behalf-of field for the
audit trail, and quietly allowing staff through this route instead would make
the timeline claim the resident filed something they did not.

There is no adjudication: nothing about the contestation changes the process's
stage, its ladder index or any suggestion.

### 7.6 One linked-lots predicate, used twice

```python
class InfractionService:
    @staticmethod
    def linked_lot_ids(session: Session, user: User) -> set[UUID]:
        """Lots this user is the unit for. No permission short-circuit."""
        links = session.exec(
            select(UserLotLink.lot_id).where(UserLotLink.user_id == user.id)
        ).all()
        residents = session.exec(
            select(Resident.lot_id).where(
                Resident.user_id == user.id, Resident.is_active.is_(True)
            )
        ).all()
        return set(links) | set(residents)
```

`GET /infractions/my-lots` filters to `Infraction.lot_id.in_(linked_lot_ids)`;
`POST /infractions/{id}/contestation` refuses with 403 when
`infraction.lot_id not in linked_lot_ids`. **One helper, so the two cannot
drift**: a lot linkage that shows a resident an infraction is exactly the
linkage that lets them contest it, which is the property ER-7 and ER-8 read
from opposite ends.

It is deliberately **not** `VisitorService.get_user_linked_lot_ids`, which is
otherwise the same query: that helper opens with
`if has_permission(current_user, session, "visitors:manage_any_lot"): return
[every lot]` (`app/services/visitor_service.py:95–99` at `4f952b0`), a
gatekeeper short-circuit that would hand every lot in the condominium to
anyone holding an unrelated visitors permission — turning the 403 above into a
no-op for exactly the callers it exists to stop. Both branches of the union are
kept, though (`UserLotLink` **and** active `Resident.user_id`), because that is
what "the unit" means in this codebase and it is what `matrix_world` seeds.

### 7.7 The two create-time validations, decided

Both apply to `POST /api/v1/infractions` **and** to
`POST /api/v1/infractions/from-occurrence/{occurrence_id}`, checked after the
404s and before anything is written:

1. **A deactivated rule cannot start a new infraction.** `rule.is_active is
   False` → **422**, detail `"The rule is not active"`. `is_active = False`
   means the article stopped being enforceable (§3.2's soft deactivation);
   registering a *new* breach of it would be registering a breach of a rule the
   condominium withdrew. This does **not** touch existing infractions: §12.1's
   `test_delete_deactivates_and_keeps_the_rule_readable` still holds — the rule
   stays readable, existing infractions still resolve it, and their processes
   still advance along its ladder. Deactivation is forward-looking only.
2. **The responsible must be a resident of the effective lot.** `resident.lot_id
   != lot_id` or `resident.is_active is False` → **422**, detail
   `"The responsible resident does not belong to this lot"`. Without it,
   §6.2's `(rule, responsible)` count and §4.5's `lot_id` filter can disagree
   about the same infraction, and the lot history ER-4 promises stops being
   coherent. `Resident.lot_id` is NOT NULL in the tree, so the check is one
   comparison.

Both are **422 and not 409**: they are validation of the submitted references,
the same class as an unparseable UUID, and the frontend forms (§10.1) already
pick the responsible from the residents *of the chosen lot* and the rule from
the *active* catalogue, so a well-behaved client never sees either.

---

## 8. Authorization outcomes, and how the ERs' role names are honoured

### 8.1 The post-F5 reality, stated plainly

After APRAS-49 there is **no `UserRole` enum** and **no
`LEGACY_ROLE_PERMISSIONS`**. Roles are data, and — the no-seeds doctrine —
**nothing is seeded**: a permission added to the catalogue after F5 is held by
**no role** until an operator grants it. The role names in the nine Expected
Results are therefore read as **the recommended bundle**, documented and
asserted, not as a set of rows this task writes.

### 8.2 What this task must NOT touch

* `tests/data/legacy_role_bundles.json` — F5's recording of what the enum used
  to mean, made *before* the map was deleted. APRAS-44's permissions did not
  exist then and must not be back-dated into it. Pinned byte-identical (§12.4).
* `backend/tests/data/parity_matrix_baseline.json` — the frozen F2 artefact,
  1080 cells, `_meta.merge_base_sha == 02c2025…`, and the two prose anchors
  that quote that sha (APRAS-40 §9.2.1). Untouched, and pinned by the sha256
  test APRAS-40 introduces.
* `app/api/deps.py::get_effective_permissions` — no line.
* Anything under `app/*/finance*` — ER-5, `tests/test_infraction_isolation.py`
  (§12.1).

### 8.3 The recommended bundle (documented in AGENTS.md, asserted in tests)

The distillation of ER-1, ER-3, ER-6, ER-8 and ER-9's role language, using the
legacy names F5 gives the migrated role rows:

| Permission | ADMINISTRATOR | DIRECTOR | MANAGER | RESIDENT | PORTEIRO | GUEST |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| `infractions:read` | ✓ | ✓ | ✓ | | | |
| `infractions:create` | ✓ | ✓ | ✓ | | | |
| `infractions:advance` | ✓ | ✓ | ✓ | | | |
| `infractions:promote` | ✓ | ✓ | ✓ | | | |
| `infractions:cycle_close` | ✓ | ✓ | ✓ | | | |
| `infractions:contest` | ✓ | ✓ | ✓ | ✓ | | |
| `infractions:my_lots_read` | ✓ | ✓ | ✓ | ✓ | | |
| `infractions:rule_read` | ✓ | ✓ | ✓ | | | |
| `infractions:rule_create` | ✓ | ✓ | | | | |
| `infractions:rule_update` | ✓ | ✓ | | | | |
| `infractions:rule_deactivate` | ✓ | ✓ | | | | |
| `infractions:policy_update` | ✓ | ✓ | | | | |
| `infractions:settings_update` | ✓ | ✓ | | | | |

Three readings that are decisions, not accidents:

* **`cycle_close` is MANAGER-level, not DIRECTOR-level.** The board's
  justification defines staff as ADMINISTRATOR/DIRECTOR/MANAGER — *"(4)
  ADMINISTRATOR/DIRECTOR/MANAGER registram infrações E avançam o processo"* —
  and ER-9 says *"O staff pode encerrar"*. It is auditable and additive
  (§7.2's `justification` is NOT NULL and non-empty), never a deletion, so the
  wider set is the honest reading of the contract.
* **PORTEIRO and GUEST hold nothing** (ER-8), so all 18 routes refuse them.
* **`contest` is staff-and-resident, but the permission is not sufficient.**
  Staff hold it because staff who *live* in the condominium contest their own
  infractions like anyone else, and because withholding it would make the
  bundle table lie about who can reach the route at all. §7.5's object check
  applies on top, to staff and superusers alike: holding `infractions:contest`
  gets you to the route, being linked to the lot gets you past it. Staff
  filing a defense **on another unit's behalf** is Out of Scope (§13) — it is
  a different route with a different audit trail.

### 8.4 Parity-matrix prediction — 108 cells

`tests/matrix_world.py` builds its six profiles from
`legacy_role_bundles.json ∪ NEW_TIER` (APRAS-49 §11.1) and builds the
`ADMINISTRATOR` profile with `is_superuser=True` (APRAS-49 §11.1, APRAS-47
§3.3, restated at APRAS-40 §9.2.4). Therefore:

* the **five non-`ADMINISTRATOR` profiles** hold no `infractions:*` permission
  and answer **403** on all 18 routes — **90 cells**, the plain denial shape,
  needing no `DENIAL_SHAPE_OVERRIDES` entry;
* the **`ADMINISTRATOR` profile** short-circuits to the whole catalogue and
  measures the handlers — **18 cells**.

The **semantic oracle needs no new branch.** `holds()` reads the recorded
bundles for the five and the superuser branch APRAS-40 §9.2.4.1 adds for the
sixth; an `infractions:*` permission is in no bundle, so the oracle predicts
403, which is what is recorded. **Verify this rather than assume it**: if the
landed `matrix_world` does *not* give `ADMINISTRATOR` `is_superuser=True`, all
18 of its cells become 403 too, and the PR body must say so.

The 18 `ADMINISTRATOR` predictions, given a world that seeds one row of every
object the new path parameters name (§12.6):

| Route | Predicted |
|---|---|
| `GET /api/v1/infraction-rules` | 200 |
| `GET /api/v1/infraction-rules/{rule_id}` | 200 |
| `POST /api/v1/infraction-rules` | 201 |
| `PUT /api/v1/infraction-rules/{rule_id}` | 200 |
| `DELETE /api/v1/infraction-rules/{rule_id}` | 204 (soft deactivate, §3.2) |
| `PUT /api/v1/infraction-rules/{rule_id}/policy` | 200 |
| `GET /api/v1/infraction-settings` | 200 (`condo_fee_amount: null`, §5) |
| `PUT /api/v1/infraction-settings` | 200 |
| `GET /api/v1/infractions` | 200 (no query string — every parameter is optional, §4.5) |
| `GET /api/v1/infractions/my-lots` | 200 — a one-element list, **not** `[]` (below) |
| `GET /api/v1/infractions/cycles` | 200 |
| `GET /api/v1/infractions/{infraction_id}` | 200 |
| `GET /api/v1/infractions/{infraction_id}/next-step` | 200 |
| `POST /api/v1/infractions` | 201 |
| `POST /api/v1/infractions/from-occurrence/{occurrence_id}` | 201 |
| `POST /api/v1/infractions/{infraction_id}/stages` | 201 |
| `POST /api/v1/infractions/{infraction_id}/contestation` | 201 |
| `POST /api/v1/infractions/cycles/close` | 201 |

**The two rows that depend on the seeded world, not on the permission** — both
verified against `matrix_world.build_world` at `4f952b0`, which already links
**every** profile user to `world.lot` with both a `UserLotLink` and an active
`Resident` row (`tests/matrix_world.py:350–364`):

* `GET /infractions/my-lots` is **200 with one item**, because §12.6 seeds
  `world.infraction` on `world.lot` and the profile user is linked to it. The
  status code is what the matrix records, so 200 either way — but the
  parenthetical must not claim `[]`, or the next reader will conclude the
  narrowing is untested here. (The `[]`-for-an-unlinked-staff-member property
  of §3.4 is real and is asserted in `tests/test_infractions_rbac.py`, where
  the world is built for it.)
* `POST /infractions/{id}/contestation` is **201 only if** the seeded
  infraction carries a `NOTIFICACAO` stage with an open `defense_due_on`
  **and** the acting profile is linked to `world.infraction.lot_id` (§7.5's
  403, §7.6). Both hold by construction: the stage is seeded (§12.6) and the
  link is pre-existing. If either failed, the cell would record 409 or 403 and
  would be measuring state or object-narrowing instead of authorization.

**A recorded value that disagrees with this table is a bug in the code, not a
new prediction** (APRAS-40 §9.2.3 step 3).

### 8.5 The additive baseline file

Mirroring APRAS-40 §9.2 exactly:
`backend/tests/data/parity_matrix_baseline_44.json`, same shape, same five
`_meta` keys (so `META_KEYS` is reused verbatim), `cell_count: 18 * 6 = 108`,
and `merge_base_sha` = **APRAS-44's own merge base — the commit at which
APRAS-40 landed**, i.e. this task's branch point, the sha at which the 18
routes do *not* yet exist and from which the `+18` delta is measured. It is
**not** the value APRAS-40 wrote in its own file (that is APRAS-40's branch
point, the APRAS-39 landing point, APRAS-40 §9.2.2); the two files record two
different shas, each its own. The APRAS-40 test only checks the field is 40 hex
and appears in `regenerate`, so a wrong sha here is silent — read it with
`git merge-base` at branch time and paste it into both places. Then a
`regenerate` string that is the literal scoped invocation:

```
cd backend && POSTGRES_URL=sqlite:// SECRET_KEY=parity-matrix \
uv run python -m tests.tools.record_parity_baseline \
  --out tests/data/parity_matrix_baseline_44.json \
  --merge-base <APRAS-44's own merge base: the commit at which APRAS-40 landed> \
  --routes 'GET /api/v1/infraction-rules' \
  ... (all 18)
```

The recorder needs **no** further change: APRAS-40 §9.2.3 already adds
`--routes`, `--merge-base` and the `FROZEN` guard, and
`assert_clean_production_tree` is untouched. **The commit ordering is a
constraint**: write and commit all of `backend/app/` first (the recorder exits
`2` on a dirty `app/`), then record, then read the 108 numbers against §8.4,
then commit the baseline, then the test-side changes. `--overwrite` is never
passed and `--out` never names a frozen file.

`tests/test_permission_parity_matrix.py` gains `APRAS_44_CELL_COUNT = 108` and
extends `EXPECTED_CELL_COUNT` to `F2_CELL_COUNT + APRAS_40_CELL_COUNT +
APRAS_44_CELL_COUNT`, reading a third file through the same loader APRAS-40
§9.2.5 introduces.

---

## 9. Migration `0036_add_infraction_tables`

* **Revision id**: `0036_add_infraction_tables` — **26 characters**, within
  the 32-character limit the Alembic `version_num` column imposes. Every id in
  this repository is `NNNN_snake_case`; keeping under 32 is a hard constraint,
  not a style note.
* **`down_revision`**: APRAS-40's migration — predicted
  `"0035_add_subscription_tables"`. **Read the landed head** with
  `uv run alembic heads` at the merge base and use it; §0 rule 1 governs.
* **Follows `0027_add_purchase_quotation.py` field for field**: `sa.Uuid()`
  ids, enums as `sa.Column(..., sa.String(), nullable=False,
  server_default="…")` with **no Postgres `ENUM` type** (so `downgrade()` has
  no type to drop), money as `sa.Float()`, `sa.Text()` for long free text,
  `sa.JSON()` with `server_default="[]"` for the URL lists, explicit
  `op.create_index(...)` calls, `sa.ForeignKeyConstraint` with the `ondelete`
  of §7.2.
* **`tenant_id` on the four directly-scoped tables** reproduces
  `tenant_id_field()`'s four properties by hand, because a migration cannot
  call it: `sa.Uuid(), nullable=False, server_default=sa.text("'00000000-0000-0000-0000-000000000001'")`,
  `sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="RESTRICT")`,
  and `op.create_index("ix_<table>_tenant_id", "<table>", ["tenant_id"])`.
* **Reversible.** `downgrade()` drops the seven tables in reverse dependency
  order — `infraction_contestation`, `infraction_stage`,
  `infraction_cycle_close`, `infraction`, `infraction_policy_step`,
  `infraction_rule`, `infraction_settings` — dropping each table's indexes
  first, exactly as `0027` does. **No data step in either direction**: no
  seeded rule, no seeded policy, no backfill (ER contract and the no-seeds
  doctrine).
* **Two nullability facts the migration must get right**, both of them
  decisions and not oversights: `infraction.lot_id` is
  `nullable=False` (§7.4's effective-lot rule exists so it can be), and
  `infraction_cycle_close.lot_id` is `nullable=True` (§6.2 property 5 — audit
  context, not part of the recidivism match). Both are pinned by §12.2.
* `EntityType.INFRACTION` needs no DDL: `media_asset.entity_type` is already a
  `String` column. `NextStepReason` and `InfractionStageFilter` reach no
  column either (§7.1), so the migration creates **three** string-backed enum
  vocabularies, not five.
* `tests/test_migrations_postgres.py` gains the `0036` up/down round trip
  against real Postgres, following the module's existing pattern. **Renumber
  at merge time if 47/48/49/39/40 landed different numbers**, and re-verify
  against real Postgres, never against SQLite alone.

---

## 10. Frontend

### 10.1 Files — `src/features/infraction-management/`

| File | Contents |
|---|---|
| `pages/InfractionRulesPage.tsx` | the catalogue table (artigo, origem, descrição, janela, ativa) with create/edit forms, and the inline policy-ladder editor: add/remove/reorder steps, per-step action, deadline, fine mode and value; saves via `PUT …/policy` |
| `pages/InfractionsPage.tsx` | the management list with the five filters of §4.5 — regra (`rule_id`), lote (`lot_id`), responsável (`responsible_id`), estágio atual (`stage`, including the `NONE` option) and período (`date_from`/`date_to`) — `skip`/`limit` paging, and the "Registrar infração" action |
| `pages/MyInfractionsPage.tsx` | the resident view: own lots' infractions, the open deadline highlighted, the contestation form |
| `components/InfractionDetailsView.tsx` | header (regra, lote, responsável, ocorrência de origem as a link), evidence, timeline, next-step panel |
| `components/InfractionStageTimeline.tsx` | the merged, **read-only** append-only history — stages and contestations, author, date, note, fine value. No edit and no delete control exists (ER-3) |
| `components/NextStepPanel.tsx` | renders `NextStepRead`: recidivism count, window, suggested action and value, an "Aplicar sugestão" primary button and an override select. The button is **disabled** when `reason === "NO_POLICY"`, with a message pointing at the rule's empty ladder; the override select stays enabled, because an explicit action is always accepted (§6.5) |
| `components/NewInfractionModal.tsx` | rule / lot / responsible (residents of the chosen lot) / date / description / evidence upload |
| `components/ContestationForm.tsx` | body + attachments, disabled with an explanatory message when no deadline is open. Rendered **only inside `/my-infractions`**, which already lists nothing but the caller's own lots — so the 403 of §7.5 is unreachable from the UI and needs no client-side lot check |
| `components/CycleCloseModal.tsx` | rule + responsible + a **required** justification, an **optional** lot (audit context, §6.2 property 5), with a confirmation that says nothing is deleted |
| `hooks/useInfractions.ts`, `hooks/useInfractionRules.ts` | TanStack Query hooks (`useQuery` / `useMutation`, invalidation on mutate) |
| `types/infraction.ts` | the TS mirrors of §4.4 |

`OccurrenceDetailsView.tsx` gains a "Promover a infração" button, shown by
`useCanShowMenu({anyOf:["infractions:promote"]})`, and a link list to the
infractions already promoted from that occurrence.

### 10.2 `ROUTE_ACCESS` / `NAV_ITEMS` (APRAS-48 §5.2)

| Route | Rule |
|---|---|
| `/infractions` | `{anyOf:["infractions:read"]}` |
| `/infraction-rules` | `{anyOf:["infractions:rule_create","infractions:rule_update","infractions:rule_deactivate"]}` |
| `/my-infractions` | `{anyOf:["infractions:my_lots_read"]}` |

**`{module:"infractions"}` is specifically wrong for `/infractions`** and the
reason must not be lost: a module rule means "holds any `infractions:*`", so a
resident holding only `my_lots_read` would be offered the management list the
API answers 403 for. `anyOf` is the shape APRAS-48 already uses for exactly
this situation on `/gate` and `/spaces`.

Three `NAV_ITEMS` entries with `labelKey` `nav.infractions`,
`nav.infractionRules`, `nav.myInfractions`; each entry's `access` **is** the
`ROUTE_ACCESS` entry of its path, which APRAS-48's test already asserts. Three
`<Route>` elements in `App.tsx`, each wrapped in `<ProtectedRoute
requiredAccess={ROUTE_ACCESS["…"]}>`. No `requiredRole`, `requiredRoles`,
`requiredCapability` or `requiredMenu` prop is introduced — F4 deleted them and
`tsc -b` fails on an unknown prop.

### 10.3 i18n

* One `infractions.*` block in **both** `src/i18n/locales/pt.json` and
  `en.json`, pt-BR first (the product language): page titles, column headers,
  the three enum label sets (origem, ação do passo, modo da multa), the
  next-step panel's explanatory sentence, the deadline states, the cycle-close
  confirmation, and every error detail the API can return.
* Three `nav.*` keys.
* **26 permission labels** — 13 permissions × 2 locales — in the block APRAS-48
  §2.8 introduces for the role editor.
* Parity is **mechanically asserted**: reuse the deep-key-set equality test if
  APRAS-39 §11 landed one; otherwise add
  `src/i18n/__tests__/parity.test.ts` asserting that the flattened key sets of
  `en.json` and `pt.json` are equal, and that no value is the empty string.
  The existing `src/i18n/__tests__/index.test.ts` checks initialisation only
  and does not cover this.

---

## 11. Accounting — every pinned number, as a delta

Relative to **APRAS-44's own merge base — the commit at which APRAS-40 landed**
(i.e. after 47, 48, 49, 39 and 40 land). Same sha as §8.5's
`merge_base_sha`, and *not* the sha APRAS-40 recorded in its own baseline
file. Predicted bases are APRAS-40 §9.1's own predictions carried forward;
**the deltas are the contract** (§0 rule 2).

| Constant | Predicted base | Delta | Predicted final |
|---|---|---|---|
| `len(PERMISSIONS)` | 161 | **+13** | **174** |
| `len(ROUTE_PERMISSIONS)` | 183 | **+18** | **201** |
| `len(UNGUARDED_ROUTES)` | 22 | **0** | **22** |
| total routes | 205 | **+18** | **223** |
| `len(GLOBAL_ROUTES)` (`test_tenant_route_scope.py`) | 27 | **0** | **27** |
| `ADMIN_ONLY_ROUTES` (both copies) | 14 | **0** | **14** |
| `MODULES` | 27 | **+1** | **28** |
| `CORE_MODULES` | 4 | **0** | **4** |
| `TOGGLEABLE_MODULES` | 23 | **+1** | **24** |
| `len(REQUEST_BODIES)` (`tests/matrix_world.py`) | 90 | **+9** | **99** |
| `EXPECTED_REQUEST_BODY_COUNT` | 90 | **+9** | **99** |
| `matrix_world.py` docstring's write-route count | 90 | **+9** | **99** |
| `F2_CELL_COUNT` (frozen) | 1080 | **0** | **1080** |
| `APRAS_40_CELL_COUNT` | 18 | **0** | **18** |
| `APRAS_44_CELL_COUNT` (new file) | — | **+108** | **108** |
| `EXPECTED_CELL_COUNT` | 1098 | **+108** | **1206** |
| `ADMIN_GAP_PERMISSIONS` | 1 | **0** | **1** |
| `SUPERUSER_ONLY_PERMISSIONS` | 4 | **0** | **4** |

The **nine** new `REQUEST_BODIES` entries — every `POST`/`PUT`/`PATCH` key of
the 18: `POST /api/v1/infraction-rules`, `PUT /api/v1/infraction-rules/{rule_id}`,
`PUT /api/v1/infraction-rules/{rule_id}/policy`, `PUT /api/v1/infraction-settings`,
`POST /api/v1/infractions`, `POST /api/v1/infractions/from-occurrence/{occurrence_id}`,
`POST /api/v1/infractions/{infraction_id}/stages`,
`POST /api/v1/infractions/{infraction_id}/contestation`,
`POST /api/v1/infractions/cycles/close`. The **one** `DELETE`
(`/api/v1/infraction-rules/{rule_id}`) and the **eight** `GET`s contribute
none — 1 + 8 + 9 = the 18 of §4.2. **Every body must be shape-valid**: a missing or
invalid entry answers 422 and masks the authorization answer, which
`test_every_write_route_has_a_request_body` and
`test_request_bodies_covers_exactly_the_write_routes` both refuse. Bodies that
name objects (`rule_id`, `lot_id`, `responsible_resident_id`,
`source_occurrence_id`) resolve them from the seeded world, not from literals —
and must satisfy §7.7, so `responsible_resident_id` is a resident **of**
`world.lot` and `rule_id` names the **active** `world.infraction_rule`, or the
create cells record 422 instead of 201. The `cycles/close` body may set
`lot_id` or omit it (§4.4 makes it optional); the promotion body omits it, so
the promotion cell exercises §7.4's ordinary case
(`world.occurrence.lot_id` is set).
No absolute datetime anywhere — `occurred_on` is an offset from
`datetime.utcnow()` computed at build time
(`test_no_absolute_datetime_in_the_harness`).

### 11.1 The table partition — 53 → 60

`tests/test_tenant_models.py` reads the directly-scoped list out of migration
`0028`'s frozen `_TENANT_SCOPED_TABLES` literal, which is **not edited**;
post-`0028` scoped tables register in `POST_0028_SCOPED_TABLES`, the constant
APRAS-40 §9.3 introduces. It grows by four:

```python
POST_0028_SCOPED_TABLES = {
    "tenant_subscription",                 # APRAS-40
    "infraction_rule",                     # APRAS-44
    "infraction",
    "infraction_cycle_close",
    "infraction_settings",
}
```

| Group | Base | Delta | Final |
|---|---|---|---|
| directly scoped | 28 | +4 | 32 |
| inherited | 21 | +3 (`infraction_policy_step`→`infraction_rule`, `infraction_stage`→`infraction`, `infraction_contestation`→`infraction`) | 24 |
| unscoped | 4 | 0 | 4 |
| **total tables** | **53** | **+7** | **60** |

**Two cases union the constant, not one** (APRAS-40 §9.3's warning applies
verbatim): `test_partition_of_metadata_is_exhaustive` and
`test_scoped_tables_have_a_not_null_tenant_id_fk` must both iterate
`set(scoped_tables) | POST_0028_SCOPED_TABLES`, or the four new scoped tables'
`tenant_id` shape is never checked. `INHERITED_TABLES` gains its three
`child: parent` entries. `test_scoped_tables_list_has_27_real_tables` stays at
**27** and stays unedited — it asserts a property of migration `0028`'s frozen
literal. `tenant_context.TENANT_SCOPED_MODELS` grows 28 → 32 by derivation,
with no code change; its docstring's count moves.

---

## 12. Tests, by layer

### 12.1 New backend modules

Case counts are stated per file so a reviewer can check the round-1 additions
landed: **8 + 22 + 17 = 47** named cases across the three tables below (31 at
round 0, **+16** in round 1), plus `test_infractions_rbac.py` and
`test_infraction_isolation.py`, plus §12.2's **four** structural assertions.

**`tests/test_infraction_rules.py`** — catalogue and policy. **8 cases**,
unchanged in round 1: §7.7's two validations are on `POST /infractions`, not on
the catalogue's own routes, so they live in `test_infractions.py`.

| Test | Asserts |
|---|---|
| `test_create_and_list_a_rule` | 201; the rule reads back with origin, article, description, window |
| `test_duplicate_article_and_origin_is_rejected` | 409, detail names the article; the same pair in a *second tenant* is 201 |
| `test_delete_deactivates_and_keeps_the_rule_readable` | `DELETE` → 204; `is_active` false; `GET /{id}` still 200; a referencing infraction still resolves its rule |
| `test_policy_write_replaces_the_whole_ladder` | `PUT …/policy` with 3 steps then 2 steps leaves exactly 2 |
| `test_policy_rejects_non_contiguous_step_order` | **422**, detail names the gap *(fixed in implementation: this was the spec's only either-or status; 422 is the module's single "the body names something wrong" code)* |
| `test_notificacao_requires_a_deadline` | 422 without `defense_deadline_days` |
| `test_multa_requires_a_coherent_fine_mode` | 422 for `MULTA` without `fine_mode`; for `FIXED` without an amount; for `MULTIPLE` without a multiplier |
| `test_settings_read_on_an_absent_row_is_200_with_nulls` | never 404 (§5) |

**`tests/test_infractions.py`** — the process. **22 cases** (12 at round 0,
**+10** in round 1: three promotion cases from B1 — one 201, two 422 — two
contestation 403s from B2, three list-filter cases from B4, and §7.7's two
create validations).

| Test | Asserts |
|---|---|
| `test_register_an_infraction_directly` | 201; `source_occurrence_id is None`; `current_stage is None` |
| `test_register_against_a_deactivated_rule_is_422` | **§7.7 (1)**: 422 `"The rule is not active"`; an infraction created *before* the deactivation still advances along the same rule's ladder |
| `test_responsible_must_belong_to_the_lot` | **§7.7 (2)**: 422 `"The responsible resident does not belong to this lot"` for a resident of another lot, and for an inactive resident of the right lot |
| `test_promote_an_occurrence` | 201; `source_occurrence_id` set; `OccurrenceDetailRead.infraction_ids` contains it; an `OccurrenceTimeline` note was written; the effective lot is the occurrence's |
| `test_promote_a_lotless_occurrence_with_an_explicit_lot` | **B1**: occurrence with `lot_id is None` + `body.lot_id` → 201, `infraction.lot_id == body.lot_id` |
| `test_promote_a_lotless_occurrence_without_a_lot_is_422` | **B1**: both absent → 422 `"The occurrence has no lot; lot_id is required"` |
| `test_promote_with_a_conflicting_lot_is_422` | **B1**: `body.lot_id != occurrence.lot_id` → 422 `"lot_id does not match the occurrence's lot"`; no infraction row was written; the equal-lot case is 201 |
| `test_one_occurrence_promotes_twice` | two infractions, both linked |
| `test_list_filters_by_rule_lot_and_responsible` | **§4.5**: each filter alone narrows; two together compose with `AND`; `total` counts after the filters and before `skip`/`limit`; `?lot_id=` returns both responsibles' infractions on one lot (the ER-4 half of §6.2 property 1) |
| `test_list_filters_by_the_derived_current_stage` | **§4.5**: `?stage=NONE` returns only infractions with no stage row; after a `POST /stages` the same infraction moves to `?stage=AVISO` and out of `NONE`; after a second stage it is in `?stage=NOTIFICACAO` only — the correlated subquery reads the *latest* stage, and no `current_stage` column exists (§12.2) |
| `test_list_filters_by_date_range_and_paginates` | **§4.5**: `date_from`/`date_to` are inclusive of both end days over `created_at`; `skip`/`limit` walk a stable `created_at DESC, id DESC` order with no repeated and no skipped row; `limit=101` is 422 |
| `test_stage_history_is_append_only_and_derives_the_current_stage` | after two `POST /stages`, `current_stage` is the second action and `timeline` has both, in order |
| `test_no_route_edits_or_deletes_a_stage` | no `("PUT"\|"PATCH"\|"DELETE", ".../stages…")` key in `ROUTE_PERMISSIONS` |
| `test_notificacao_freezes_the_deadline` | `defense_due_on == applied_on + days`; changing the rule afterwards does not move it |
| `test_contestation_inside_the_deadline` | 201 for a caller linked to the lot; appears in `timeline` with `kind == "CONTESTATION"`; the infraction's `current_stage` is unchanged |
| `test_contestation_after_the_deadline` | 409 `"The defense deadline has passed"` |
| `test_contestation_without_a_notificacao` | 409 `"No open defense deadline"` |
| `test_contestation_from_an_unlinked_caller_is_403` | **B2**: a resident of *another* lot, holding `infractions:contest`, gets 403 `"Only the notified unit may contest this infraction"` on a neighbour's infraction — **before** the deadline branch, so it is 403 and not 409 even when the deadline has also passed; no `infraction_contestation` row is written |
| `test_contestation_by_a_superuser_is_also_object_narrowed` | **B2**: a user with `is_superuser=True` and one with `is_tenant_admin=True`, neither linked to the lot, both get 403 on the same request an unlinked resident gets 403 on; linking either one makes the same call 201 |
| `test_fine_amount_is_frozen_on_the_stage` | applying `MULTIPLE`, then changing `condo_fee_amount`, leaves the stage's `fine_amount` unchanged |
| `test_multa_without_a_fee_reference` | 409 `"The condominium fee reference is not set"`; the same call with an explicit `fine_amount` is 201 with `fine_amount_overridden is True` |
| `test_route_order_puts_the_literal_segments_first` | `GET /api/v1/infractions/my-lots` and `/cycles` are 200/403, never 422 |

**`tests/test_infraction_escalation.py`** — §6, table-driven. **17 cases**
(11 at round 0, **+6** in round 1: three empty-ladder cases from B3, and three
that make §6.2's *"six properties, each of which is a test"* literally true —
properties 3, 5 and 6 had no named case).

| Test | Asserts |
|---|---|
| `test_first_infraction_suggests_step_one` | `ladder_index == 1`, `suggested_step_order == 1`, `reason == "SUGGESTED"` |
| `test_advancing_moves_one_step_within_the_process` | index 2 after one stage |
| `test_a_repeat_offender_starts_higher` | second infraction, no stages → index 2 |
| `test_recidivism_is_per_responsible_not_per_lot` | **ER-4's star test**: two infractions of the same rule on the *same lot* with *different* responsibles → both `recidivism_count == 0`; `GET /infractions?lot_id=` returns both |
| `test_outside_the_window_does_not_count` | `occurred_on` one day before `window_start` → not counted; one day after → counted |
| `test_same_day_infractions_do_not_count_each_other` | **§6.2 property 3**: two infractions with the same `occurred_on` → **both** `recidivism_count == 0`; the strict `<` is symmetric and neither ordering wins |
| `test_an_unadvanced_prior_infraction_still_counts` | **§6.2 property 6**: a prior infraction with **zero** stage rows raises the next one's `recidivism_count` to 1 — the count reads facts, not staff diligence |
| `test_a_closed_cycle_is_a_cutoff_not_a_deletion` | **B5, and it names whose count**: with two prior infractions in the window, close the cycle, then register a **new** infraction of the same `(rule, responsible)` → the **new** one has `recidivism_count == 0` and `ladder_index == 1`; the **pre-existing** infraction's `next-step` is byte-identical before and after the close (its `recidivism_count`, `stages_applied` and `ladder_index` are unchanged, and its `cycle_closed_at` stays `null`); `infraction` and `infraction_stage` row counts are unchanged; the close is listed by `GET /infractions/cycles` |
| `test_a_cycle_close_ignores_the_lot` | **§6.2 property 5**: a close recorded with `lot_id` = lot A still cuts off an infraction of the same `(rule, responsible)` on lot B, and a close with `lot_id` omitted entirely behaves identically — the lot is audit context, never part of the match |
| `test_the_ladder_saturates_at_the_last_step` | index 7 on a 3-step ladder → step 3, `is_saturated is True`, `reason == "CLAMPED"` |
| `test_an_empty_ladder_answers_no_policy` | **B3**: a rule with **zero** policy steps → `next-step` is **200** with `suggested_step_order is None`, `suggested_action is None`, `reason == "NO_POLICY"`, `is_saturated is False`, `fine_amount is None`, `fine_amount_unavailable_reason is None`, and `recidivism_count` / `window_start` / `stages_applied` / `ladder_index` computed normally |
| `test_accepting_a_suggestion_with_no_policy_is_409` | **B3**: `POST /stages` with `action = null` against a rule with no ladder → 409 `"Rule has no escalation policy"`; no `infraction_stage` row is written |
| `test_an_explicit_action_is_accepted_with_no_policy` | **B3**: the same call with an explicit `action` → **201**, `policy_step_order is None`, `suggestion_followed is False` |
| `test_two_rules_of_one_tenant_escalate_differently` | **ER-2's star test**: rule A = `[MULTA]`, rule B = `[AVISO, AVISO, MULTA]`; a first infraction of A suggests MULTA, a first of B suggests AVISO |
| `test_fixed_and_multiple_fine_values` | FIXED returns the literal; MULTIPLE returns `multiplier * condo_fee_amount` rounded to 2 places |
| `test_suggestion_is_stable_across_days` | the same infraction computed on two `date.today()` values gives the same answer (window anchored on `occurred_on`) |
| `test_explicit_action_records_a_deviation` | `suggestion_followed is False` |

**`tests/test_infractions_rbac.py`** — §8.3 × the 18 routes, driven with real
role rows built to the recommended bundles. Includes the ER-8 pair:

* a role with **no** `infractions:*` gets **403 on all 18 routes** — the whole
  module, `my-lots` and the contestation included (ER-8, §8.4);
* a role with exactly `{my_lots_read, contest}` gets 200 on
  `GET /infractions/my-lots` and 403 on `GET /infractions`, and its `my-lots`
  answer contains only infractions of lots the caller is linked to, with
  `defense_due_on` populated;
* the **`[]` case §3.4 promises**: a *staff* caller holding `my_lots_read` with
  **no** `UserLotLink` and no active `Resident` row gets **200 with `[]`** —
  a filter, never a refusal, and never the 403 `packages:my_lots_read` would
  give (§3.4). This is the property `matrix_world` cannot show, because every
  matrix profile is linked to `world.lot` (§8.4).

**`tests/test_infraction_isolation.py`** — ER-5, modelled on
`tests/test_purchase_isolation.py`:

* **Static (AST).** Parse `app/models/infraction.py`,
  `app/schemas/infraction.py`, `app/services/infraction_service.py`,
  `app/api/v1/endpoints/infractions.py` and
  `alembic/versions/0036_add_infraction_tables.py`; assert no import node
  names `app.models.finance`, `app.schemas.finance`,
  `app.services.finance_service` or `app.api.v1.endpoints.finance`, and no
  `Name`/`Attribute` resolves to `FinanceCategory`, `BudgetLine`,
  `FinancialTransaction` or `FinanceService`. Assert no
  `sa.ForeignKeyConstraint` argument in the migration targets
  `financial_transaction.*`, `finance_category.*` or `budget_line.*`. A
  substring scan is deliberately not used — the same false-positive /
  false-negative argument `test_purchase_isolation.py` documents.
* **Runtime (row counts).** Drive the whole flow through the API — settings →
  rule → policy → infraction → advance to `MULTA` — and assert
  `select(func.count())` over `FinancialTransaction`, `FinanceCategory` and
  `BudgetLine` is **identical before and after**, and zero in a virgin world.
* **Diff.** `test_no_finance_source_file_is_in_this_module` asserts the five
  scanned paths are disjoint from the finance file set; and the PR body must
  show `git diff --stat <merge-base>..HEAD -- backend/app/models/finance.py
  backend/app/schemas/finance.py backend/app/services/finance_service.py
  backend/app/api/v1/endpoints/finance.py` as **empty**.

### 12.2 Structural assertions (in `tests/test_infractions.py`)

* `set(Infraction.__table__.columns.keys())` contains neither `status` nor
  `current_stage` — decision 5 of §2, pinned so a later convenience column is
  a test failure.
* `infraction_stage` has no `updated_at` column and no update route: the
  history is append-only in the schema, not only in the handlers.
* `infraction_cycle_close.justification` is `nullable=False`, and an empty or
  whitespace-only justification answers 422 (ER-9); `infraction_cycle_close.lot_id`
  is `nullable=True`, and a close posted **without** it is 201 (§6.2 property 5).
* `Infraction.lot_id` is `nullable=False` while `Occurrence.lot_id` is
  `nullable=True` — the asymmetry §7.4's effective-lot rule exists for, pinned
  so a later "fix" to either column silently breaks promotion.

### 12.3 Amended backend modules

**Nine modules**, each with the literal that moves:

| Module | What moves |
|---|---|
| `test_permission_registry.py` | the §11 counts, the new `infractions` module, the naming-convention regex over the 13 new strings, `UNGUARDED_ROUTES` unchanged |
| `test_permission_parity_matrix.py` | `APRAS_44_CELL_COUNT`, the third baseline file, `EXPECTED_REQUEST_BODY_COUNT` 90→99, the frozen-file tests still green |
| `test_module_vocabulary.py` (APRAS-39) | **all three hard literals move**: `len(MODULES)` 27→28, `len(TOGGLEABLE_MODULES)` 23→24, `len(PERMISSIONS)` 161→174. Goes red the moment the 13 permissions land |
| `test_tenant_modules_api.py` (APRAS-39) | `test_get_lists_every_module_with_its_state` ("26 rows" → the new total) and `test_a_new_tenant_starts_with_every_module_active` ("26 active" → the new total). Both read `len(MODULES)`-shaped literals and both move with it |
| `test_tenant_route_scope.py` | all 18 routes tenant-scoped, `GLOBAL_ROUTES` unchanged |
| `test_tenant_models.py` | §11.1 |
| `test_tenant_isolation.py` | a rule, an infraction, a stage and a cycle-close created in tenant A are invisible in tenant B, and a forged `tenant_id` in a create body is overwritten by `before_flush` |
| `test_migrations_postgres.py` | `0036` up/down against real Postgres |
| `test_occurrences.py` | `OccurrenceDetailRead.infraction_ids` is additive and defaults to `[]` |

Plus `matrix_world.py` itself (§12.6), which is a harness and not a test module.

**The two APRAS-39 modules are the easy ones to miss**: §3.3 says APRAS-39
§12.1's totals move, but the totals are asserted in *those two files*, whose
literals are written out longhand rather than derived. Find them at the merge
base with `grep -rn "len(MODULES)\|len(TOGGLEABLE_MODULES)\|len(PERMISSIONS)\|26"
backend/tests/test_module_vocabulary.py backend/tests/test_tenant_modules_api.py`
and move each one, quoting old and new in the PR body (§0 rule 2).

### 12.4 Frozen-artefact assertions

`test_the_f2_baseline_is_untouched` (APRAS-40 §9.2.1) and its APRAS-40 sibling
stay green untouched. One new case,
`test_the_legacy_role_bundles_are_untouched_by_apras_44`, asserts the sha256
of `tests/data/legacy_role_bundles.json` is unchanged and that no bundle
contains a string starting with `"infractions:"` — §8.2, made mechanical.

### 12.5 Frontend tests

`src/features/infraction-management/__tests__/`:

| File | Covers |
|---|---|
| `InfractionRules.test.tsx` | catalogue render, create form, the ladder editor's add/remove/reorder, the conditional fine fields |
| `Infractions.test.tsx` | list render + the five §4.5 filters (each one puts its own query parameter on the request, `stage=NONE` included); detail render; the timeline renders stages and contestations in order and exposes **no** edit or delete control |
| `NextStepPanel.test.tsx` | renders the suggestion, the recidivism count and the window; the override select; the "fee not set" message; and the **`reason == "NO_POLICY"`** state — no suggested action, the "Aplicar sugestão" button disabled, and a message pointing at the rule's empty ladder (§6.5) |
| `MyInfractions.test.tsx` | resident list; contestation form enabled inside the deadline and disabled with an explanatory message outside it |
| `CycleCloseModal.test.tsx` | the submit button stays disabled until a justification is typed |
| `access.test.ts` | the three `ROUTE_ACCESS` rules evaluate as §10.2 says for four permission sets (full staff, rules-only, resident, none) |

Every test that mounts a component reading `useMyPermissions()` provides a
`QueryClientProvider` — APRAS-48 §8.2's general rule.

### 12.6 The matrix world's new objects

`tests/matrix_world.py` seeds, once, in the default tenant:

* `world.infraction_rule_id` — an active rule with a **3-step** ladder
  `[AVISO, NOTIFICACAO(defense_deadline_days=30), MULTA(FIXED, 100.0)]` and
  `recidivism_window_days=365`;
* `world.infraction_id` — on `world.lot_id`, responsible `world.resident_id`, already
  carrying **one `NOTIFICACAO` stage** whose `defense_due_on` is
  `utcnow() + 30 days` computed at build time, so the contestation cell
  measures authorization and not state (§8.4);
* no `infraction_settings` row, so `GET /infraction-settings` exercises the
  §5 absent-row read.

**Nothing needs to be seeded for §7.5's object check**, and that is worth
stating rather than discovering: `world.infraction` sits on `world.lot`, and
`build_world` at `4f952b0` already gives **every** profile user both a
`UserLotLink` to `world.lot` and an active `Resident` row on it
(`tests/matrix_world.py:350–364`). So §7.6's predicate is satisfied for all six
profiles, the 403 never fires, and the contestation cell measures
authorization. The same fact makes `GET /infractions/my-lots` return **one
item, not `[]`** — §8.4's row says so.

**`PATH_PARAMS` is derived, not written.** At `4f952b0` it is
`PATH_PARAMS = _path_params()`, and `_path_params()` walks
`ROUTE_PERMISSIONS`, resolving each `{name}` through an `overrides` dict keyed
by `(path, name)`, then — **for the literal name `id` only** — a `by_prefix`
tuple, then a `by_name` dict keyed by the **parameter name alone**. So the
implementer adds **three `by_name` entries**, not six `(path, name)` pairs:

```python
    by_name: dict[str, str] = {
        ...
        "infraction_id": "infraction_id",    # APRAS-44
        "occurrence_id": "occurrence_id",    # APRAS-44
        "rule_id": "infraction_rule_id",     # APRAS-44
        ...
    }
```

The **derived** `(path, name)` pairs are then **7**, not 6: `{rule_id}` on 2
paths (`/infraction-rules/{rule_id}` — one path for GET, PUT and DELETE alike —
and `/infraction-rules/{rule_id}/policy`), `{infraction_id}` on 4
(`/{infraction_id}`, `/{infraction_id}/next-step`, `/{infraction_id}/stages`,
`/{infraction_id}/contestation`), `{occurrence_id}` on 1. `PATH_PARAMS` is
keyed by path, so three routes sharing one path contribute one entry.

**`occurrence_id` needs its own binder and does not inherit one.** The existing
`("/api/v1/occurrences/", "occurrence_id")` entry is in `by_prefix`, and
`by_prefix` is consulted **only when the parameter is literally named `id`**
(`if attribute is None and name == "id":`). `/api/v1/infractions/from-occurrence/{occurrence_id}`
neither is named `id` nor starts with that prefix, so without the `by_name`
entry above `_path_params()` raises `KeyError` at import and the whole matrix
module fails to collect.

**`QUERY_PARAMS` is not touched.** It exists for the routes that declare a
**required** query parameter; §4.5 makes every parameter of
`GET /api/v1/infractions` optional, and no other route in this module has any.
Adding an entry would be harmless but misleading, and the count of routes with
required query parameters stays where APRAS-40 left it.

### 12.7 Gates

* `cd backend && uv run pytest --cov=app --cov-fail-under=90` — the 90 %
  gate; the new service and endpoint modules must each be individually
  covered, not carried by the suite average.
* `cd backend && uv run ruff check .` and `uv run ruff format --check .` —
  clean, all rules, line length 88.
* `cd frontend && npm run lint && npm run build && npm run test -- --coverage`
  — ESLint clean, `tsc -b` clean, Vitest ≥ 75 %.
* `uv run alembic upgrade head && uv run alembic downgrade -1 && uv run
  alembic upgrade head` against **real Postgres**, not SQLite.

---

## 13. Out of Scope

* **Any ledger integration.** No `FinancialTransaction`, no receivable, no
  charge, no link from a fine to any finance row — ER-5,
  `tests/test_infraction_isolation.py` (§12.1). When APRAS
  eventually grows per-lot billing, a separate task connects them; the point
  of the isolation test is that the connection must be a *decision*, not a
  drift.
* **Adjudication.** No accept/reject of a contestation, no adjudicator role,
  no state a contestation moves the process into, no deadline for answering
  it. Decision 3 of §2.
* **Staff filing a contestation on a unit's behalf.** A defense that arrives on
  paper at the office cannot be typed in by the office: §7.5 refuses any caller
  not linked to the infraction's lot, superusers and tenant admins included.
  Supporting it properly means a second route with its own permission and an
  on-behalf-of field on `infraction_contestation`, so the timeline can say who
  actually typed it — otherwise the record claims the resident filed something
  they did not. That is a decision the user has not made, and quietly widening
  §7.5 to allow it would make the audit trail wrong rather than absent.
* **Notifications outside the app.** No e-mail, no SMS, no WhatsApp, no
  printable notification PDF. The unit learns of a notification by opening
  `/my-infractions`. APRAS has no outbound channel today, and adding one is a
  larger, cross-cutting task.
* **Automatic advancement.** The system suggests; a human confirms (§6.4).
  Nothing is scheduled, no job advances a process when a deadline lapses.
* **Seeded rules or policies.** No condominium's regimento is shipped in
  code, and a fresh tenant starts with an empty catalogue — the explicit
  no-seeds doctrine (APRAS-49) applied to this module.
* **A reset button for recidivism.** The legal addendum makes it unnecessary:
  the count is personal, so a change of responsible resets it by
  construction. `POST /infractions/cycles/close` covers only the case the
  addendum names — a resident change *not reflected in the cadastre in time* —
  and it is an auditable, justified event, never a deletion.
* **Cross-rule escalation.** The ladder is per rule. "Three different
  breaches of three different articles" does not escalate; that is a policy
  choice the user has not made.
* **Editing or deleting a stage.** The history is append-only. A mistaken
  stage is corrected by a subsequent stage whose note says so.
* **Bulk infraction registration** and **CSV/PDF export**. Both are
  presentation features orthogonal to the model.
* **A per-lot infractions panel inside `/lots`.** `/infractions?lot_id=` and
  the detail's lot link cover the need; a fourth surface is a later task.

---

## Expected Results

- [ ] **ER-1 — Catálogo de regras por tenant.** `POST/GET/PUT/DELETE /api/v1/infraction-rules` gravam e leem artigo, origem (`ESTATUTO` | `REGIMENTO_INTERNO` | `CONVENCAO`) e descrição; um papel com `infractions:rule_create` / `rule_update` / `rule_deactivate` (bundle recomendado: ADMINISTRATOR/DIRECTOR, §8.3) obtém 201 / 200 / 204 e um papel sem essas permissões obtém 403 em cada uma; o mesmo par (origem, artigo) é 409 no mesmo tenant e 201 em outro; `backend/tests/test_infraction_rules.py` passa.
- [ ] **ER-2 — Política de escalonamento por regra.** `PUT /api/v1/infraction-rules/{rule_id}/policy` grava uma sequência ordenada de passos `AVISO` | `NOTIFICACAO` | `MULTA`, cada `MULTA` com `fine_mode` `FIXED` (valor) ou `MULTIPLE` (multiplicador × a taxa condominial de `GET /api/v1/infraction-settings`), e a regra grava `recidivism_window_days`; duas regras do mesmo tenant com políticas diferentes produzem sugestões diferentes para a primeira infração — `test_infraction_escalation.py::test_two_rules_of_one_tenant_escalate_differently` passa.
- [ ] **ER-3 — Registro e avanço append-only, com estágio derivado.** `POST /api/v1/infractions` exige `rule_id`, `lot_id`, `responsible_resident_id`, `occurred_on` e `description`, aceita `evidence_urls`, e responde 422 `"The rule is not active"` para uma regra desativada e 422 `"The responsible resident does not belong to this lot"` para um responsável que não é morador ativo do lote; `POST /api/v1/infractions/{id}/stages` responde 201 gravando autor, data e observação; `InfractionRead.current_stage` é o último estágio do histórico, `Infraction.__table__.columns` não contém `status` nem `current_stage`, e mesmo assim `GET /api/v1/infractions?stage=NONE` (e `=AVISO` / `=NOTIFICACAO` / `=MULTA`) filtra pelo estágio atual derivado; nenhuma chave de `ROUTE_PERMISSIONS` edita ou apaga um estágio; as asserções estão em `backend/tests/test_infractions.py`.
- [ ] **ER-4 — Sugestão por (regra, responsável), nunca por lote.** `GET /api/v1/infractions/{id}/next-step` responde 200 e o corpo **contém pelo menos** as chaves `recidivism_count`, `window_start`, `cycle_closed_at`, `stages_applied`, `ladder_index`, `suggested_step_order`, `suggested_action`, `reason`, `fine_amount` e `is_saturated`, calculadas pelo §6; quando a regra não tem nenhum passo de política a resposta continua 200 com `suggested_step_order == null`, `suggested_action == null` e `reason == "NO_POLICY"`, e nesse caso `POST /api/v1/infractions/{id}/stages` sem `action` responde 409 `"Rule has no escalation policy"` enquanto o mesmo POST com `action` explícito responde 201; duas infrações da mesma regra no mesmo lote com responsáveis diferentes têm ambas `recidivism_count == 0` enquanto `GET /api/v1/infractions?lot_id=…` continua devolvendo as duas; `POST /stages` sem `action` aplica a sugestão e com `action` explícito grava `suggestion_followed = false`.
- [ ] **ER-5 — MULTA registrada e isolada do Financeiro.** Um estágio `MULTA` grava `fine_amount`, `applied_on` e o `responsible_resident_id` da infração, e o valor fica congelado quando a taxa muda depois; `backend/tests/test_infraction_isolation.py` passa, provando por AST que nenhum dos 5 arquivos do módulo importa `app.models.finance`, `app.schemas.finance`, `app.services.finance_service` ou `app.api.v1.endpoints.finance` nem nomeia `FinancialTransaction`/`FinanceCategory`/`BudgetLine`/`FinanceService`, e por contagem de linhas que essas três tabelas têm exatamente o mesmo número de linhas antes e depois do fluxo completo; `git diff --stat` dos quatro arquivos de Financeiro é vazio.
- [ ] **ER-6 — Promoção de ocorrência, com vínculo navegável nos dois sentidos.** `POST /api/v1/infractions/from-occurrence/{occurrence_id}` responde 201 com `source_occurrence_id` preenchido e escreve uma entrada na `OccurrenceTimeline`; `InfractionRead.source_occurrence_id`/`source_occurrence_protocol` e `OccurrenceDetailRead.infraction_ids` expõem o vínculo dos dois lados; como `Occurrence.lot_id` é anulável e `infraction.lot_id` não é, o lote efetivo é `body.lot_id` quando enviado e o da ocorrência quando não, com 422 `"The occurrence has no lot; lot_id is required"` se ambos faltarem e 422 `"lot_id does not match the occurrence's lot"` se ambos existirem e forem diferentes; a rota é 403 sem `infractions:promote`; `POST /api/v1/infractions` cria com `source_occurrence_id is None`.
- [ ] **ER-7 — Prazo de defesa e contestação pela unidade notificada.** Aplicar um passo `NOTIFICACAO` congela `defense_due_on = applied_on + defense_deadline_days` da regra no próprio estágio; `POST /api/v1/infractions/{id}/contestation` responde 201 dentro do prazo para um chamador ligado ao lote da infração via `UserLotLink` ou `Resident` ativo, 409 `"The defense deadline has passed"` depois do prazo e 409 `"No open defense deadline"` se não houver `NOTIFICACAO`; um chamador **não** ligado àquele lote recebe 403 `"Only the notified unit may contest this infraction"` mesmo detendo `infractions:contest` e mesmo sendo `is_superuser` ou `is_tenant_admin`, e nenhuma linha de `infraction_contestation` é gravada; a contestação aparece em `InfractionRead.timeline` com `kind == "CONTESTATION"` e não altera `current_stage`.
- [ ] **ER-8 — Papéis sem acesso, e a visão do morador.** Um papel sem nenhuma permissão `infractions:*` (PORTEIRO/GUEST no bundle recomendado) recebe 403 em **todas as 18 rotas do módulo** — o módulo inteiro, incluindo `/my-lots` e a contestação — o que corresponde às **90 células** (18 rotas × 5 perfis não-`ADMINISTRATOR`) do baseline de paridade; um papel com exatamente `infractions:my_lots_read` + `infractions:contest` recebe 200 em `GET /api/v1/infractions/my-lots` — devolvendo somente infrações dos lotes ligados ao chamador via `UserLotLink`, com `defense_due_on`, e `[]` (nunca 403) quando não há lote ligado — e 403 em `GET /api/v1/infractions`; no frontend, `/infractions` só aparece no menu com `infractions:read` e `/my-infractions` só com `infractions:my_lots_read`.
- [ ] **ER-9 — Encerramento manual de ciclo, como evento auditável.** `POST /api/v1/infractions/cycles/close` exige `rule_id`, `responsible_resident_id` e `justification` não vazia (422 se vazia) e aceita `lot_id` **opcional**, gravado só como contexto de auditoria e nunca usado no predicado de reincidência; responde 201 gravando autor e data; **a próxima infração registrada depois do encerramento** para aquele (regra, responsável) recebe sugestão com `recidivism_count == 0` e `ladder_index == 1`, enquanto **uma infração já existente mantém** `recidivism_count`, `stages_applied` e `ladder_index` inalterados (o encerramento é um corte para a frente, não uma reescrita); as contagens de linhas de `infraction` e `infraction_stage` são idênticas antes e depois, e o encerramento é listado por `GET /api/v1/infractions/cycles`; a rota é 403 sem `infractions:cycle_close`.
