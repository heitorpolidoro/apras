# APRAS-40 — Área de pagamento/assinatura com contratação de módulos pelo tenant

> **One deliverable.** A subscription model (plans, per-tenant subscription,
> append-only change history), the four API surfaces that read and write it,
> and the two frontend areas (tenant-side and superuser-side). **No charging.**

---

## 0. Preconditions, and how to read this spec against a moving tree

This spec is written against **contracts**, not against a tree that exists.
At the spec sha (`aa8953d`) only IAM F1/F2 (`APRAS-45`/`APRAS-46`) have landed.
Everything else this task composes with is an **approved spec**:

| Task | Spec | What this task consumes from it |
|---|---|---|
| `APRAS-47` (IAM F3) | `docs/tasks/APRAS-47-spec.md` | `user.is_superuser` (migration `0031`), `deps.get_current_superuser`, `is_tenant_admin` = the whole catalogue in the acting tenant |
| `APRAS-48` (IAM F4) | `docs/tasks/APRAS-48-spec.md` | `GET /api/v1/permissions/me`, `AccessRule` / `ROUTE_ACCESS` / `NAV_ITEMS`, `useCanAccess` / `useCanShowMenu` |
| `APRAS-49` (IAM F5) | `docs/tasks/APRAS-49-spec.md` | roles as data (`role` table, no `UserRole` enum, no `allowed_menus`), `PATCH /users/{id}/superuser`, `role.landing_path`, the no-seeds doctrine, `PERMISSIONS == 159` |
| `APRAS-39` | `docs/tasks/APRAS-39-spec.md` | `MODULES` / `CORE_MODULES` / `TOGGLEABLE_MODULES`, `tenant.disabled_modules`, the strip inside `get_effective_permissions`, `GET`/`PUT /api/v1/tenants/{id}/modules`, migration `0034` |

**All four land before this task.** `APRAS-47`'s developer lane runs
concurrently with this spec; nothing here may be implemented until 47, 48, 49
and 39 are merged.

**Rules for the implementer when the tree disagrees with this document.**

1. **Follow the landed name, not the predicted one.** Every symbol, path,
   revision id and test-case name below is what the four specs say they will
   land. If the tree spells one differently, use the tree's spelling and
   record the deviation in the PR body. `role` vs `user_type` is the most
   likely one.
2. **Follow the invariant, not the constant.** Every count in §9 is written
   as *merge-base ± N*. The predicted absolute values are guidance; the
   deltas are the contract. Measure the base at the actual merge base and
   quote **both** numbers in the PR body for every row.
3. **Never relitigate a landed decision.** In particular `APRAS-39`'s choice
   to store modules negatively on the `tenant` row and to strip inside
   `get_effective_permissions` is a precondition of this task, not an open
   question. This task **adds no line to the permission resolver** (§4).

---

## 1. Scope

### 1.1 What this task delivers

* **A. The model.** `Plan` (global catalogue), `TenantSubscription` (one per
  tenant), `SubscriptionChange` (append-only history). Migration `0035`.
* **B. The ceiling.** One stated, mechanically testable rule (§4) binding
  `tenant.disabled_modules` — which stays `APRAS-39`'s single read-time
  authority — to the tenant's subscription entitlement at **write** time.
* **C. The tenant-side area.** `GET /api/v1/subscription`,
  `PUT /api/v1/subscription/modules`, `GET /api/v1/subscription/history`,
  gated by two new catalogue permissions `billing:read` / `billing:manage` in
  a new **core** module `billing`.
* **D. The superuser side.** A global plan catalogue
  (`/api/v1/plans`, four routes) and three per-tenant subscription routes on
  the existing global `tenants` router: read, assign/change plan, grant or
  revoke courtesy modules.
* **E. The frontend.** `/subscription` (tenant), `/admin/plans` and
  `/admin/subscriptions` (superuser), with pt/en parity.
* **F. Documentation.** An `AGENTS.md` *Assinatura e planos* subsection and
  the endpoint-table rows, plus one amendment to the *Módulos por tenant*
  subsection `APRAS-39` writes.

### 1.2 What this task explicitly does NOT deliver

**No payment provider, and no charging of any kind.** This is the same
blocker class as `APRAS-13`: real billing needs a payment-provider account
(Stripe / Pagar.me / Asaas / …) that **does not exist** for this project. So:

* every price field is **inert display metadata** — stored, returned,
  summed for display, and **never** used to move money;
* **no SDK, no API key, no webhook receiver, no outbound HTTP call** is added
  by this task, and no dependency is added to `backend/pyproject.toml` or
  `frontend/package.json`;
* `subscription.status` (`ACTIVE` / `SUSPENDED` / `CANCELED`) is recorded and
  displayed but **gates nothing** (§4.3) — enforcing suspension is a
  consequence of charging, and charging is out of scope;
* a follow-up task wires a provider once an account exists. It will consume
  this model; it is not this task.

Also out of scope (each with its reason, so it is not rediscovered in review):

| Not here | Why |
|---|---|
| invoices, receipts, proration, dunning, trials, coupons | all are provider-shaped |
| tenant-initiated **plan** change (upgrade/downgrade self-service) | a plan change is a commercial negotiation; without a provider it cannot be paid for. Plan assignment stays superuser-only |
| any edit to `deps.get_effective_permissions`, `deps.disabled_modules`, `filter_by_modules` | §4: the resolver is untouched, which is what keeps the parity story cheap |
| any edit to `APRAS-39`'s `/admin/modules` page | that page is the *raw* operator switch; this task adds the *commercial* surfaces beside it (§8.4) |
| a module dependency graph (`assets` requires `inventory`, …) | `APRAS-39` §2.3 already declares companions as documentation only |
| per-tenant plan rows / custom plans | the catalogue is global, the SaaS norm (§3.1) |
| deleting a `Plan` | soft-deactivation only (`is_active`), matching `Tenant` and `Category` |
| retiring `PUT /api/v1/tenants/{id}/modules` | it stays as the operator's raw lever (§4.2) |

---

## 2. The vocabulary: a new **core** module, and two permissions

### 2.1 `billing` is core

```python
# app/core/permissions.py, in PERMISSIONS
        # §4.x billing (APRAS-40) -- the subscription area
        "billing:read",     # see the tenant's own subscription and its history
        "billing:manage",   # contract or cancel modules within the plan
```

```python
# app/core/permissions.py, CORE_MODULES (APRAS-39 §2.1) grows by one
CORE_MODULES: frozenset[str] = frozenset({"tenants", "users", "roles", "billing"})
```

**`billing` must be core, and this is load-bearing.** `MODULES` is derived
from `PERMISSIONS` (`APRAS-39` §2.1), so `billing` becomes a module the day
these two strings exist. If it were toggleable, a superuser (or a plan) could
turn `billing` off and the condominium would lose the only surface from which
it can turn anything back on — the exact lock-out `CORE_MODULES` exists to
prevent, and the exact reason `roles` is core. `deps.disabled_modules`
subtracts `CORE_MODULES` from the stored row (`APRAS-39` §5.1), so even a
hand-edited `tenant.disabled_modules` containing `"billing"` cannot strip
`billing:*`.

Consequence, stated because it changes a landed route's behaviour:
`PUT /api/v1/tenants/{id}/modules {"disabled_modules": ["billing"]}` now
answers **400** `"Core modules cannot be disabled: billing"`, via
`APRAS-39`'s existing `CoreModuleCannotBeDisabledError` and **no new code**.

### 2.2 Why two permissions and not one

`billing:read` is the *area*; `billing:manage` is the *act of contracting*.
The board's ER-2 separates seeing the subscription from changing what is
charged, and a condominium that wants its treasurer to see the plan without
being able to contract modules needs exactly this split. `billing:manage`
does **not** imply `billing:read` — the two are independent strings, as
everywhere else in the catalogue; the frontend route rule is
`{module: "billing"}` (holds *any* `billing:*`), so a manage-only holder
still reaches the page and the read endpoint is what refuses them. That is a
degenerate configuration nobody will create; it is documented rather than
special-cased.

### 2.3 Who actually holds them — stated honestly

The board's framing is "tenant_admin **and** DIRECTOR". Post-`APRAS-49` there
is no `DIRECTOR` enum, so "DIRECTOR" must become a permission:

* **`is_tenant_admin` reaches it for free.** `APRAS-47` makes an acting
  tenant_admin hold **every** permission in the catalogue in the granting
  tenant, and `billing` is core so `APRAS-39`'s strip never removes it.
  Therefore `require_permission("billing:manage")` admits a tenant_admin with
  **no special case and no `or is_tenant_admin` clause anywhere in this
  task**. This is the whole reason the gate is a permission and not a flag
  check.
* **A superuser reaches it for free** by `APRAS-47`'s short-circuit.
* **A "Diretor" reaches it only when the condominium grants it.**
  `APRAS-49` §9.2 keeps the no-seeds doctrine: `ensure_legacy_roles` inserts
  the six historically-named rows with `permissions = []`, and migration
  `0033` backfills only the *recorded legacy bundles* — which, having been
  recorded before this task existed, contain neither `billing:read` nor
  `billing:manage`. **So on the day this task lands, no role row anywhere
  holds either string.** A director gets the subscription area when a
  tenant_admin (or superuser) ticks the two boxes in the role editor, which
  is the same way a director gets every other post-F5 capability.

  This is deliberate and is **not** a gap to be closed by seeding. Seeding
  `billing:manage` into `Diretor (papel)` would (a) violate F1's no-seeds
  decision, (b) hand commercial authority to every director of every existing
  condominium without the síndico asking for it, and (c) move
  `tests/data/legacy_role_bundles.json`, the recorded artefact `0033` is
  verified against. The spec records the decision so review does not read the
  empty bundle as an oversight.

  Pinned by `test_subscription_access.py::test_no_role_row_holds_billing_permissions_on_a_fresh_install`
  and `..._a_director_reaches_the_area_once_the_role_grants_it`.

---

## 3. The model

Three new tables. Money is `float`, following `finance.FinancialTransaction.amount`
and `BudgetLine.planned_amount`; the usual objection (binary float for
currency) does not bite here **precisely because nothing is charged** — the
values are display metadata (§1.2) and never enter an arithmetic that must
balance to the cent. A follow-up provider task that does move money changes
the column type in its own migration.

### 3.1 `Plan` — a **global** catalogue, superuser-managed

```python
# app/models/plan.py  (new)

class Plan(SQLModel, table=True):
    """One commercial plan in the install-wide catalogue (APRAS-40).

    Global, not per-tenant: the SaaS norm, and the thing that makes
    "which plan is this condominium on" a comparable answer across the
    install. `name` is globally unique for the same reason `tenant.name` is.

    Every price field is INERT: it is displayed and summed for display and
    never charges anything, because no payment provider exists (§1.2).
    """

    __tablename__ = "plan"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True, unique=True, nullable=False)
    description: str | None = Field(default=None, nullable=True)
    #: The toggleable modules this plan lets a tenant contract. Portable JSON,
    #: not a Postgres ARRAY: tests/conftest.py builds the schema with
    #: SQLModel.metadata.create_all() on sqlite:// (the reason
    #: user_type.allowed_menus and tenant.disabled_modules record).
    included_modules: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, server_default="[]"),
    )
    #: INERT. Monthly base price of the plan.
    base_price: float = Field(default=0.0, nullable=False)
    #: INERT. {module: monthly price} for the modules this plan lets a tenant
    #: contract. A module in `included_modules` with no entry here is bundled
    #: at no extra cost. Keys must be a subset of `included_modules` (§6.2).
    module_prices: dict[str, float] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False, server_default="{}"),
    )
    currency: str = Field(default="BRL", max_length=3, nullable=False)
    #: Soft deactivation. There is deliberately no DELETE route: a plan a
    #: tenant is subscribed to must not vanish, and `tenant_subscription.plan_id`
    #: is ON DELETE RESTRICT.
    is_active: bool = Field(default=True, nullable=False)
    created_at / updated_at: datetime, NOT NULL
```

`plan` carries **no** `tenant_id`; it joins `user`, `tenant` and
`user_tenant_link` in `test_tenant_models.UNSCOPED_TABLES` (§9.3).

### 3.2 `TenantSubscription` — one per tenant, directly scoped

```python
# app/models/subscription.py  (new)

class TenantSubscription(SQLModel, table=True):
    """The commercial state of one tenant (APRAS-40). At most one per tenant."""

    __tablename__ = "tenant_subscription"
    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_tenant_subscription_tenant"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    #: Directly scoped (APRAS-41 doctrine): the tenant-side routes read and
    #: write this row through the acting tenant, so `tenant_context`'s loader
    #: criteria make a cross-tenant read structurally impossible. The
    #: superuser routes are on the GLOBAL_SCOPED tenants router, where
    #: `acting_tenant_id(session) is None`, so neither the filter nor
    #: `_stamp_tenant_on_write` applies and the explicit `tenant_id` survives.
    tenant_id: UUID = tenant_id_field()
    #: A plain FK column and deliberately **no** `Relationship`: the one place
    #: that needs the plan beside the subscription is
    #: `SubscriptionService.entitlement`, which joins them explicitly in one
    #: query (§6.3). A lazy relationship would make the plan reachable from any
    #: caller holding the row, which is exactly what §6.3's `build_read` scan
    #: exists to prevent, and it would change nothing in §7's migration.
    plan_id: UUID = Field(
        foreign_key="plan.id", ondelete="RESTRICT", nullable=False, index=True
    )
    status: SubscriptionStatus = Field(
        default=SubscriptionStatus.ACTIVE, nullable=False, index=True
    )
    #: Modules the global operator granted outside the plan (courtesy, trial,
    #: negotiation). Distinguishable from a contracted module by construction:
    #: it is a named column, written only by the superuser courtesy route,
    #: and it is free — it never enters `estimated_monthly_total` (§6.4).
    courtesy_modules: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, server_default="[]"),
    )
    notes: str | None = Field(default=None, nullable=True)
    started_at / created_at / updated_at: datetime, NOT NULL
```

**Why a table and not five more columns on `tenant`** (the shape `APRAS-39`
chose for modules): 39's column stores one boolean-ish fact with no history
and no foreign key. This stores a FK to `plan`, a status, a courtesy set, a
start date and notes, and it needs an append-only child table — five columns
and a child table hung off `tenant` is a subscription entity wearing a
disguise. Recorded so the asymmetry with 39 is not read as an inconsistency.

**Why directly scoped and not unscoped.** The high-frequency path is
tenant-side (`GET /api/v1/subscription` on every load of the area), and on
that path a `tenant_id` column buys structural isolation for free: no service
can forget the filter. This makes `APRAS-40` the **first task to add a
directly-scoped table after migration `0028`**, whose `_TENANT_SCOPED_TABLES`
literal is frozen history — §9.3 says exactly how `test_tenant_models.py`
absorbs that.

### 3.3 `SubscriptionChange` — append-only, inherits its tenant

```python
class SubscriptionChange(SQLModel, table=True):
    """An append-only record of one change to a tenant's subscription.

    The pattern is `PurchaseQuoteDecision` (APRAS-37): a child of a scoped
    parent, never updated, never deleted, ordered by its own timestamp. It
    carries NO `tenant_id` — it reaches its tenant through the NOT NULL FK to
    `tenant_subscription`, and a second copy would be a forgeable source of
    truth that can disagree with the parent (APRAS-41 doctrine).
    """

    __tablename__ = "subscription_change"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    subscription_id: UUID = Field(
        foreign_key="tenant_subscription.id",
        ondelete="CASCADE", nullable=False, index=True,
    )
    kind: SubscriptionChangeKind = Field(nullable=False, index=True)
    modules_added: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False, server_default="[]"))
    modules_removed: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False, server_default="[]"))
    from_plan_id: UUID | None = Field(default=None, foreign_key="plan.id", nullable=True)
    to_plan_id: UUID | None = Field(default=None, foreign_key="plan.id", nullable=True)
    reason: str | None = Field(default=None, nullable=True)
    changed_by_id: UUID = Field(foreign_key="user.id", nullable=False, index=True)
    changed_at: datetime = Field(default_factory=lambda: datetime.now(UTC), nullable=False, index=True)
```

`changed_by_id` is NOT NULL: all five write paths are authenticated requests,
and a history row whose author is unknown is worse than no row.

**Append-only is enforced structurally, not by convention.** There is no
`PATCH`, no `DELETE` and no update route for this table; the service only ever
`session.add()`s one. Pinned by a source scan
(`test_subscription_history.py::test_the_history_is_never_updated_or_deleted`)
asserting `SubscriptionChange` never appears as an argument to
`session.delete(` in `backend/app/**/*.py` and that no service function
assigns to an attribute of a loaded `SubscriptionChange`, in the style of
`APRAS-39`'s `test_the_unstripped_resolver_is_used_only_by_the_escalation_guards`.

### 3.4 Enums — `app/models/enums.py`

```python
class SubscriptionStatus(StrEnum):
    """Commercial state of a subscription. INERT: gates nothing (§4.3)."""
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    CANCELED = "CANCELED"


class SubscriptionChangeKind(StrEnum):
    """What produced a history row. This is what makes ER-4 mechanical."""
    CONTRACTED = "CONTRACTED"          # tenant-side, within the plan
    PLAN_CHANGE = "PLAN_CHANGE"        # superuser assigned/changed the plan
    COURTESY_GRANT = "COURTESY_GRANT"  # superuser granted a module outside the plan
    COURTESY_REVOKE = "COURTESY_REVOKE"
    OVERRIDE = "OVERRIDE"              # superuser used APRAS-39's raw module switch
```

---

## 4. THE RULE — how APRAS-40 composes with APRAS-39

This is the single most important section of the spec. It is stated once, as
one rule, and everything else follows from it.

### 4.1 The rule

> **`tenant.disabled_modules` remains the only input to permission
> resolution. `APRAS-40` changes no line of `deps.get_effective_permissions`,
> `deps.disabled_modules` or `permissions.filter_by_modules`. What `APRAS-40`
> adds is a constraint on *who may write that column and to what value*:**
>
> ```
> active(tenant)      := MODULES - set(tenant.disabled_modules)
> entitlement(tenant) := Entitlement(subscription, plan, included, courtesy)  # §6.3
>   .managed  := subscription is not None                           # a property
>   .included := set(plan.included_modules)  & TOGGLEABLE_MODULES   # ∅ when unmanaged
>   .courtesy := set(sub.courtesy_modules)   & TOGGLEABLE_MODULES   # ∅ when unmanaged
>   .all      := TOGGLEABLE_MODULES                    if not managed
>                .included | .courtesy                 otherwise
> ```
>
> `entitlement()` is the **single place that loads the subscription and its
> plan** (§6.3, one query), and it carries both loaded rows in its result, so
> `build_read` reads the database not at all.
>
> **No write made through an APRAS-40 route ever activates a module outside
> `entitlement(tenant).all`** — stated exactly, as the three-part
> post-condition of §4.5, because §4.4 (a) *preserves* an activation
> `APRAS-39`'s raw lever put outside the ceiling rather than repairing it.

So: 40 does **not** subsume 39's toggle. 39's superuser `PUT
/api/v1/tenants/{id}/modules` survives verbatim as the operator's **raw
lever**, deliberately *not* constrained by the ceiling; 40 gives tenant-side
actors a **second, ceiling-constrained lever on the same column**, and gives
the superuser a **third, entitlement-expanding lever** (courtesy). Three
writers, one column, one reader.

### 4.2 The four levers, and what each may do

| Lever | Actor | Constrained by the ceiling? | History row |
|---|---|---|---|
| `PUT /api/v1/subscription/modules` | `billing:manage` (⊇ tenant_admin, superuser) acting in own tenant | **yes** — 400 outside the entitlement | `CONTRACTED` |
| `PUT /api/v1/tenants/{id}/subscription` (plan) | superuser | **applies** the ceiling: `active := active ∩ entitlement` | `PLAN_CHANGE` |
| `PUT /api/v1/tenants/{id}/subscription/courtesy` | superuser | **expands** the entitlement, and activates | `COURTESY_GRANT` / `COURTESY_REVOKE` |
| `PUT /api/v1/tenants/{id}/modules` (**APRAS-39, unchanged**) | superuser | **no** — the raw lever | `OVERRIDE` (§4.5) |

Why the raw lever stays unconstrained: it is the operator's repair tool. A
tenant whose subscription data is wrong must still be fixable, and 39 §5.3
already grants the superuser an unfiltered view for exactly that reason.

### 4.3 `status` gates nothing

`SUSPENDED` and `CANCELED` are recorded, displayed and returned by the API,
and change **no** entitlement and **no** access. Enforcing suspension is a
consequence of a failed charge, and there is no charging (§1.2). Pinned by
`test_subscription_ceiling.py::test_status_does_not_change_the_entitlement`:
the same tenant's `active` set and `/permissions/me` are byte-identical with
`status` `ACTIVE`, `SUSPENDED` and `CANCELED`.

### 4.4 The three state transitions, exactly

**(a) Tenant contracts** — `PUT /api/v1/subscription/modules {"active_modules": [...]}`.

1. 404 `SubscriptionNotFoundError` if the tenant has no subscription row
   (§4.6). 
2. 400 `UnknownModuleError` (APRAS-39's class) for any string outside
   `MODULES`.
3. Core modules present in the body are **accepted and ignored** — they are
   always active; the request set is intersected with `TOGGLEABLE_MODULES`
   before anything else. (39's `PUT` rejects a core module because it appears
   in the *disabled* list; here it appears in the *active* list, where it is
   simply true.)
4. 400 `ModuleNotEntitledError` if `requested - ent.all != ∅`, where `ent`
   is `SubscriptionService.entitlement(session, tenant)` (§6.3, structured).
   The detail names the offending modules, sorted:
   `"Modules not covered by the subscription: finance, purchases"`.
5. **The merge preserves what the tenant does not govern.** The body is the
   *contracted set*, not the whole active set (§8.4): a module the tenant is
   not offered a checkbox for must not be switched off by being omitted.

   ```
   ent        := entitlement(session, tenant)              # §6.3
   requested  := set(active_modules) & TOGGLEABLE_MODULES  # ⊆ ent.all, by step 4
   preserved  := (active(tenant) & TOGGLEABLE_MODULES) - ent.included
   new_active := requested | preserved
   tenant.disabled_modules = sorted(TOGGLEABLE_MODULES - new_active)
   tenant.updated_at       = utcnow()
   ```

   `preserved` is exactly the courtesy-active and override-active modules, so
   **omission deactivates only plan-covered modules**, and a courtesy grant or
   an `APRAS-39` raw override survives every tenant-side write. A courtesy
   module *named* in the body is accepted (it is in `ent.all`) and is already
   in `preserved` when active, so the call is a no-op for it. Pinned by
   `test_subscription_ceiling.py::test_a_tenant_side_write_preserves_courtesy_and_override_activations`.
6. If and only if `tenant.disabled_modules` actually changed, append one
   `SubscriptionChange(kind=CONTRACTED, modules_added=…, modules_removed=…,
   changed_by_id=caller)`. A no-op `PUT` is a 200 that writes **no** history
   row — idempotence is what lets the UI re-save safely.

**(b) Superuser assigns or changes the plan** — `PUT /api/v1/tenants/{id}/subscription
{"plan_id": …, "status": …, "notes": …}`.

1. 404 for an unknown tenant (`TenantNotFoundError`) or unknown plan
   (`PlanNotFoundError`); 400 `InactivePlanError` when the plan
   `is_active is False` **and** it is not the plan already assigned.
2. Creates the row when absent, else updates `plan_id` / `status` / `notes`.
3. **Then applies the ceiling, shrink-only**: `disabled_modules :=
   sorted(TOGGLEABLE_MODULES - (active ∩ entitlement))`. Modules that leave
   the entitlement are **deactivated**; modules that newly enter it are
   **not** auto-activated — contracting them is the tenant's explicit act
   (ER-2), and that is what makes the contracting screen meaningful.
4. Appends `SubscriptionChange(kind=PLAN_CHANGE, from_plan_id, to_plan_id,
   modules_removed=<deactivated>)`.

   **First adoption is this same rule.** A tenant with no subscription is
   all-on (`disabled_modules == []`, 39's backfill). Assigning it a plan
   therefore deactivates every toggleable module the plan does not cover, in
   one visible, history-recorded event. Adopting billing is opt-in and
   explicit; an install with no `plan` rows behaves exactly as it does today.

**(c) Superuser grants or revokes courtesy** — `PUT
/api/v1/tenants/{id}/subscription/courtesy {"courtesy_modules": [...], "reason": "..."}`.

1. 404 for an unknown tenant (`TenantNotFoundError`) or a tenant with no
   subscription row (`SubscriptionNotFoundError`); 400 `UnknownModuleError`
   (APRAS-39's class) for any string outside `MODULES`; 400
   `CoreModuleNotContractableError`, detail
   `"Core modules are always active: billing"`, for any **core** module —
   granting as courtesy something that is never off is meaningless, and
   `APRAS-39`'s `CoreModuleCannotBeDisabledError` is the wrong class here
   because nothing is being disabled. Duplicates collapse; the list is stored
   `sorted(set(...))`.
2. Declarative replace of `subscription.courtesy_modules`.
3. **Newly granted modules are activated** — removed from
   `tenant.disabled_modules`. This is what makes "o ADMINISTRATOR global
   continua podendo ativar um módulo à revelia do plano" **one call**.
4. **Revoked modules that the plan does not cover are deactivated** — added
   back to `tenant.disabled_modules`. Revoking a courtesy on a module the
   plan also covers changes nothing but the label.
5. Appends up to two rows: `COURTESY_GRANT` (with `modules_added` and
   `reason`) and/or `COURTESY_REVOKE` (with `modules_removed` and `reason`),
   one per kind that actually occurred; a no-op call appends nothing.

*Why courtesy activates while a plan change does not:* courtesy names one or
more specific modules as a deliberate per-module operator act — "turn this on
for them" — whereas a plan names a bundle and says nothing about what the
condominium wants switched on. The asymmetry is stated so it is not read as
an inconsistency, and both halves are pinned by named tests.

### 4.5 The invariant, and the one place it may be broken

The invariant is a **post-condition of the APRAS-40 write paths**, not a
database constraint and not a read-time filter. It is stated in three parts,
because §4.4 (a) now *preserves* an out-of-entitlement activation rather than
repairing it (B3), and a single `⊆ entitlement` statement would be false:

```
over(t) := (active(t) & TOGGLEABLE_MODULES) - entitlement(t).all

I1  no APRAS-40 write escalates:
    over(t)_after ⊆ over(t)_before          for all three write paths
I2  the plan-change path repairs:
    over(t)_after == ∅                      after §4.4 (b)
I3  the tenant-side path is neutral on what it does not govern:
    over(t)_after == over(t)_before         after §4.4 (a)
```

`over(t)` is non-empty **only** because `APRAS-39`'s raw `PUT
/tenants/{id}/modules` may put it there, deliberately (§4.2). When it does,
the subscription area reports those modules with `source: "OVERRIDE"` — so
the state is visible, named and distinguishable from both a contracted and a
courtesy activation, which is the courtesy the board's ER-4 asks for. I1/I2/I3
are pinned by `test_subscription_ceiling.py::test_the_invariant_holds_after_every_apras_40_write`,
one assertion per part per path.

To make the raw lever appear in the history at all, `TenantService.set_modules`
(APRAS-39 §6.2) gains **an actor parameter and one appended block**. The block
is appended, not woven in: no line of `APRAS-39`'s body is removed, reordered
or re-indented, and the two `before` / `after` captures exist because 39's body
binds no `added` / `removed` of its own — it writes
`tenant.disabled_modules = sorted(set(payload))` and returns:

```python
# app/services/tenant_service.py  -- APRAS-39 §6.2's signature grows one kw-only arg
@staticmethod
def set_modules(
    *, session: Session, tenant_id: UUID, modules_in: TenantModulesUpdate,
    actor: User,                       # <-- added by APRAS-40, keyword-only, required
) -> TenantModulesRead:
    ...                                # APRAS-39's load + validation, unchanged
    before = set(tenant.disabled_modules)   # APRAS-40, before 39's assignment
    ...                                # APRAS-39's assignment + commit, unchanged
    after = set(tenant.disabled_modules)
    # APRAS-40 §4.5: the raw lever is the fourth writer, so it is historied too.
    # The column is NEGATIVE, so a module that LEFT `disabled_modules` was
    # activated: `added` is `before - after`, not the other way round.
    added = sorted(before - after)
    removed = sorted(after - before)
    subscription = SubscriptionService.get_subscription(session=session, tenant_id=tenant_id)
    if subscription is not None and (added or removed):
        SubscriptionService.record(
            session=session, subscription=subscription,
            kind=SubscriptionChangeKind.OVERRIDE,
            added=added, removed=removed, actor=actor,
        )
```

The `before` capture is the one statement that lands *inside* 39's existing
flow (immediately before the assignment); everything else is appended after the
commit. If the landed 39 already binds an added/removed pair, reuse it and drop
the two captures — `test_the_raw_switch_records_an_override_history_row` is the
contract, not the line count.

and `APRAS-39`'s handler `set_tenant_modules` renames its guard binding from
`_` to `current_user` and forwards it as `actor=current_user`. That rename is
**the whole of the endpoint edit**; the route path, the guard
(`Depends(api_deps.get_current_superuser)`), the status code and the response
model are byte-identical, so `ROUTE_PERMISSIONS`, `UNGUARDED_ROUTES`,
`ADMIN_ONLY_ROUTES` and the parity matrix are all unmoved by it.

This is the **only** edit `APRAS-40` makes to an `APRAS-39` code path, and
`tests/test_tenant_modules_api.py` needs **no** change for it (those fixtures
have no subscription row, so the guard is `subscription is None` and nothing
is appended) — see §10.2 for the cases in that module that *do* change, and
why. `SubscriptionService.get_subscription` returns `None` rather than raising,
precisely so this call site stays a guard rather than a try/except and 39's
status codes cannot move.

**Import direction, stated so it is not discovered in review:**
`tenant_service.py` imports `SubscriptionService` from
`app/services/subscription_service.py`, and `subscription_service.py` must
therefore **not** import `TenantService` at module level. It does not need to:
it loads `Tenant` from the session directly.

### 4.6 No subscription — the semantics, spelled out

A fresh install has **no plans and no subscriptions** (no-seeds doctrine;
migration `0035` inserts no rows). For a tenant with no subscription row:

| Surface | Answer |
|---|---|
| `GET /api/v1/subscription` | **200**, `plan: null`, `status: null`, `estimated_monthly_total: null`, every toggleable module `in_plan: false`, `courtesy: false`, **`can_contract: false`** and `source: "UNMANAGED"` when active |
| `GET /api/v1/subscription/history` | **200**, `[]` |
| `PUT /api/v1/subscription/modules` | **404** `"This tenant has no subscription"` — contracting is meaningless without one, and a history row has nowhere to live |
| module availability | unchanged from today: 39's `disabled_modules` is `[]`, everything is on |

So the tenant-side lever **exists only once a subscription exists**, and
until then module control is exactly `APRAS-39`'s superuser switch. That is
the whole of "adopting billing is opt-in".

**Why `can_contract` is `false` and not `true` on this surface.** `.all` is
`TOGGLEABLE_MODULES` when unmanaged (§4.1), so a naive
`module in ent.all and module not in CORE_MODULES` would answer `true` — and
promise a button whose `PUT` is a **404**. `can_contract` is therefore defined
with an explicit `ent.managed` conjunct (§4.7), which makes it exactly "the
`PUT` would accept this module" and nothing looser. It is what §8.4's
no-subscription state renders from when it disables Save, and it is asserted by
`test_subscription_api.py::test_get_without_a_subscription_is_200_and_unmanaged`.

### 4.7 `source` — the six values, in priority order

Computed per module in `GET /api/v1/subscription` (and in the superuser read):

| # | `source` | Condition |
|---|---|---|
| 1 | `"CORE"` | `module in CORE_MODULES` |
| 2 | `null` | not in `active(tenant)` |
| 3 | `"UNMANAGED"` | active, and the tenant has **no** subscription row |
| 4 | `"PLAN"` | active, and `module in plan.included_modules` |
| 5 | `"COURTESY"` | active, and `module in subscription.courtesy_modules` |
| 6 | `"OVERRIDE"` | active, subscription exists, in neither |

Evaluated top to bottom, so a module that is both in the plan and in the
courtesy set reads `"PLAN"` — deterministic, and pinned by
`test_subscription_api.py::test_source_priority_is_plan_over_courtesy`.

Rules 4 and 5 read `ent.included` and `ent.courtesy` from the **structured**
result of `SubscriptionService.entitlement` (§6.3) — never `plan.included_modules`
directly. That is what keeps the two facts distinguishable inside `build_read`
while leaving exactly one definition of the ceiling, and it is what makes
§6.3's grep pin satisfiable. `ModuleEntitlementRead.in_plan` is
`module in ent.included`; `.courtesy` is `module in ent.courtesy`;
`.can_contract` is
`ent.managed and module in ent.all and module not in CORE_MODULES` — the
`ent.managed` conjunct is load-bearing, not defensive: without it every
toggleable module of an **unmanaged** tenant would read `can_contract: true`
while `PUT /api/v1/subscription/modules` answers 404 (§4.6);
`.monthly_price` is `ent.plan.module_prices.get(module)` and is `None` when
`ent.plan is None`. Every one of them comes out of the `Entitlement` result and
nothing else — `build_read` issues no query of its own (§6.3).

---

## 5. The API surface

Ten new routes. Three are permission-guarded; seven are superuser-guarded and
therefore carry **no** catalogue permission, following the convention
`APRAS-49` §8.4 established and `APRAS-39` §6.4 repeated (minting catalogue
strings whose only purpose is to be refused by `assert_can_grant` costs
parity cells for nothing).

### 5.1 The tenant-side router — `app/api/v1/endpoints/subscription.py` (new)

Mounted `TENANT_SCOPED` (`app/api/v1/api.py`), prefix `/subscription`,
because a permission-guarded route **must** resolve an acting tenant:
post-F5 `get_effective_role_ids` returns the empty set with no acting tenant,
so a `billing:read` holder on a global route would be 403'd.

There is **no `{tenant_id}` in these paths, on purpose.** The subject is the
acting tenant, resolved from `X-Tenant-Id` by `get_current_tenant`. A path
parameter would be a second, forgeable source of truth and would hand a
tenant_admin of A a way to name B.

| Method | Path | Guard | Handler |
|---|---|---|---|
| `GET` | `/api/v1/subscription` | `require_permission("billing:read")` | `get_my_subscription` |
| `PUT` | `/api/v1/subscription/modules` | `require_permission("billing:manage")` | `set_my_modules` |
| `GET` | `/api/v1/subscription/history` | `require_permission("billing:read")` | `get_my_history` |

```python
@router.get("", response_model=SubscriptionRead)
def get_my_subscription(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.require_permission("billing:read"))],
) -> SubscriptionRead: ...
```

**Route templates are what FastAPI yields, not what this table guesses.** The
implementer prints `route.path` for the three and uses those exact strings as
`ROUTE_PERMISSIONS` keys; `test_subscription_api.py::test_the_three_tenant_routes_are_route_mapped`
asserts the three keys exist and map to the two permissions. The frontend
writes the same strings verbatim (no trailing slash where FastAPI has none) —
`api/client.ts` documents why a 307 is fatal here: it drops `X-Tenant-Id`.

### 5.2 The plan catalogue — `app/api/v1/endpoints/plans.py` (new)

Mounted **`GLOBAL_SCOPED`**, prefix `/plans`. Every route is superuser-only
(`Depends(api_deps.get_current_superuser)`), so no acting tenant is needed
and the router joins `tenants` in the global set.

| Method | Path |
|---|---|
| `GET` | `/api/v1/plans/` — list, including inactive |
| `POST` | `/api/v1/plans/` — create |
| `GET` | `/api/v1/plans/{plan_id}` |
| `PATCH` | `/api/v1/plans/{plan_id}` — update, including `is_active` |

**No `DELETE`.** `tenant_subscription.plan_id` is `ON DELETE RESTRICT` and a
plan a tenant is on must not vanish; deactivation is the operation, exactly
as for `Tenant`.

**Why the catalogue is not readable by tenant-side actors.** A permission-
guarded `GET /api/v1/plans/` would need the router to be tenant-scoped, which
would put a `get_current_superuser` guard on a tenant-scoped route and trip
`test_tenant_admin.py::test_no_tenant_scoped_route_keeps_a_global_admin_guard`.
It would also be a *sales* surface, and self-service plan change is out of
scope (§1.2). The tenant sees its own plan — name, description, included
modules, prices — **embedded** in `GET /api/v1/subscription`, which is
everything ER-1 and ER-5 require.

### 5.3 The superuser per-tenant routes — `app/api/v1/endpoints/tenants.py`

Added to the **existing global `tenants` router**, beside `APRAS-39`'s
`/modules` pair and for its reasons: the subject is a tenant named in the
path, written from outside it, by an actor whose authority is global.

| Method | Path |
|---|---|
| `GET` | `/api/v1/tenants/{tenant_id}/subscription` |
| `PUT` | `/api/v1/tenants/{tenant_id}/subscription` — assign/change plan, status, notes |
| `PUT` | `/api/v1/tenants/{tenant_id}/subscription/courtesy` |

All three `Depends(api_deps.get_current_superuser)`.

**FORBIDDEN, explicitly** (repeating `APRAS-39` §6.4, because the pins are
the same): implementing any of these seven superuser guards as an in-handler
`if not user.is_superuser: raise …` in order to keep `ADMIN_ONLY_ROUTES` from
moving. The three structural walkers
(`test_permission_enforcement.py`, `test_tenant_admin.py`,
`test_tenant_route_scope.py`) discover guards by traversing
`route.dependant`; an inlined check is invisible to all three. The pins move
by +7; they are not to be dodged.

### 5.4 Schemas — `app/schemas/plan.py`, `app/schemas/subscription.py` (new)

```python
# plan.py
class PlanCreate(BaseModel):
    name: str; description: str | None = None
    included_modules: list[str] = []
    base_price: float = 0.0
    module_prices: dict[str, float] = {}
    currency: str = "BRL"

class PlanUpdate(BaseModel):        # every field optional
    name / description / included_modules / base_price / module_prices / currency / is_active

class PlanRead(BaseModel):
    id, name, description, included_modules, base_price, module_prices,
    currency, is_active, created_at, updated_at
```

```python
# subscription.py
class ModuleEntitlementRead(BaseModel):
    module: str
    is_core: bool
    is_active: bool                  # from tenant.disabled_modules — APRAS-39's truth
    in_plan: bool
    courtesy: bool
    can_contract: bool               # ent.managed and in ent.all and not core (§4.7)
    monthly_price: float | None      # INERT; ent.plan.module_prices.get(module);
                                     # None when unmanaged or unpriced
    source: str | None               # §4.7

class SubscriptionRead(BaseModel):
    tenant_id: UUID
    plan: PlanRead | None                  # PlanRead.model_validate(ent.plan)
    status: SubscriptionStatus | None       # from ent.subscription; None when unmanaged
    started_at: datetime | None             # idem
    notes: str | None                       # idem
    modules: list[ModuleEntitlementRead]   # one per MODULES entry (predicted 27),
                                           # sorted by `module`
    estimated_monthly_total: float | None  # INERT (§6.4)
    currency: str | None                    # ent.plan.currency; None when unmanaged

class SubscriptionModulesUpdate(BaseModel):
    active_modules: list[str]              # complete desired state

class SubscriptionAdminUpdate(BaseModel):
    plan_id: UUID
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    notes: str | None = None

class CourtesyUpdate(BaseModel):
    courtesy_modules: list[str]            # complete desired state
    reason: str | None = None

class SubscriptionChangeRead(BaseModel):
    id, kind, modules_added, modules_removed, from_plan_name, to_plan_name,
    reason, changed_by_id, changed_by_name, changed_at
```

`PUT` everywhere, never `PATCH`, for the module and courtesy sets: the body
is the **complete desired state**, so the operation is idempotent and the
response is the same body the `GET` returns (`APRAS-39` §6.2's reasoning).

---

## 6. Services — `app/services/plan_service.py`, `app/services/subscription_service.py`

Both new, both in the shape of `TenantService` (module-level class,
`@staticmethod`s taking `session=`). All validation lives **in the service**,
never in a Pydantic `field_validator` — the schema validates *shape*, the
service validates *vocabulary*, and a schema-level rejection would surface as
FastAPI's 422 where the ERs pin **400** (`APRAS-39` §6.3's rule).

### 6.1 New domain errors — `app/core/exceptions.py`

| Class | Status | Detail |
|---|---|---|
| `PlanNotFoundError` | **404** (added to `domain_exception_handler`'s 404 tuple) | `"Plan not found: <id>"` |
| `SubscriptionNotFoundError` | **404** (same tuple) | `"This tenant has no subscription"` |
| `PlanAlreadyExistsError` | 409 (added to the 409 tuple) | `"A plan named '<name>' already exists"` |
| `ModuleNotEntitledError` | 400 (default) | `"Modules not covered by the subscription: a, b"` |
| `InactivePlanError` | 400 (default) | `"Plan '<name>' is not active"` |
| `CoreModuleNotContractableError` | 400 (default) | `"Core modules are always active: billing"` |
| `InvalidModulePriceError` | 400 (default) | `"Priced modules must be included in the plan: finance"` |

`UnknownModuleError` is reused verbatim from `APRAS-39`.

**On the name `CoreModuleNotContractableError`.** One class serves two call
sites — a core module in a plan's `included_modules` (§6.2) and a core module
in a courtesy grant (§4.4 c) — because both are the same refusal: *a core
module is never off, so it cannot be part of a commercial grant of any kind.*
The earlier name `CoreModuleNotCourtesyableError` named only the second call
site and read as a misuse at the first; the class is named for the rule, and
its one detail string (`"Core modules are always active: <names>"`) is true on
both paths. It is a distinct class from `APRAS-39`'s
`CoreModuleCannotBeDisabledError`, which is about the *disabled* list; nothing
here disables anything.

### 6.2 `PlanService`

* `list_plans`, `get_plan`, `create_plan`, `update_plan`.
* Validation on create **and** update: `included_modules ⊆ TOGGLEABLE_MODULES`
  (`UnknownModuleError` for a non-catalogue string, `CoreModuleNotContractableError`
  for a core one — a plan cannot "include" what is always on);
  `set(module_prices) ⊆ set(included_modules)` (`InvalidModulePriceError`);
  every price `>= 0`; `currency` exactly 3 uppercase letters; duplicate
  `name` → `PlanAlreadyExistsError`.
* `included_modules` and `module_prices` are stored deduplicated and sorted /
  key-sorted, so a `GET` after a `PUT` is byte-stable.

### 6.3 `SubscriptionService`

```python
@dataclass(frozen=True)
class Entitlement:
    """The structured ceiling of one tenant (APRAS-40 §4.1), **and the whole
    input of `build_read`**.

    Structured, not a flat set, because `build_read` has to tell *why* a
    module is entitled — `in_plan` and `courtesy` are two different columns of
    §5.4's read model and two different `source` values in §4.7 — while the
    ceiling itself must stay one definition. `.all` is the ceiling; the two
    frozensets are the provenance.

    It carries the two **loaded rows** as well, because §5.4's read model needs
    `status` / `started_at` / `notes` from the subscription and
    `base_price` / `module_prices` / `currency` and the embedded `PlanRead`
    from the plan (§6.4). `entitlement()` is the single place that loads
    either of them, in one query, so `build_read` touches the session not at
    all — which is what makes its source-scan pin below satisfiable and ER-6's
    "from that result alone" literally true.
    """

    subscription: TenantSubscription | None   # None iff the tenant has no row
    plan: Plan | None                         # None iff `subscription is None`
    included: frozenset[str]     # plan.included_modules & TOGGLEABLE_MODULES; ∅ when unmanaged
    courtesy: frozenset[str]     # sub.courtesy_modules  & TOGGLEABLE_MODULES; ∅ when unmanaged

    def __post_init__(self) -> None:
        # `plan_id` is NOT NULL (§3.2), so the two are absent together or
        # present together. Anything else is a loader bug, not a state.
        assert (self.subscription is None) == (self.plan is None)

    @property
    def managed(self) -> bool:
        """False iff the tenant has no subscription row (§4.6)."""
        return self.subscription is not None

    @property
    def all(self) -> frozenset[str]:
        """§4.1's `entitlement(tenant)`. The ONLY ceiling in the codebase."""
        if not self.managed:
            return TOGGLEABLE_MODULES
        return self.included | self.courtesy


entitlement(session, tenant) -> Entitlement         # §4.1, the one definition
build_read(session, tenant) -> SubscriptionRead     # §4.7 source, §6.4 total
set_modules(session, tenant, active_modules, actor) -> SubscriptionRead   # §4.4 (a)
set_plan(session, tenant_id, payload, actor) -> SubscriptionRead          # §4.4 (b)
set_courtesy(session, tenant_id, payload, actor) -> SubscriptionRead      # §4.4 (c)
get_subscription(session, tenant_id) -> TenantSubscription | None         # §4.5's helper; never raises
list_history(session, tenant) -> list[SubscriptionChangeRead]             # changed_at DESC
record(session, subscription, kind, added, removed, actor, reason=None,
       from_plan_id=None, to_plan_id=None) -> None                        # the only writer of history
```

**`entitlement` is the one loader.** Its body is a single statement — a join,
not two round trips and not a lazy relationship (§3.2):

```python
row = session.exec(
    select(TenantSubscription, Plan)
    .join(Plan, Plan.id == TenantSubscription.plan_id)
    .where(TenantSubscription.tenant_id == tenant.id)   # explicit: the
).first()                                               # superuser routes are
                                                        # GLOBAL_SCOPED, so
                                                        # tenant_context adds
                                                        # no criteria there
if row is None:
    return Entitlement(subscription=None, plan=None, included=frozenset(), courtesy=frozenset())
subscription, plan = row
return Entitlement(
    subscription=subscription,
    plan=plan,
    included=frozenset(plan.included_modules) & TOGGLEABLE_MODULES,
    courtesy=frozenset(subscription.courtesy_modules) & TOGGLEABLE_MODULES,
)
```

`entitlement` has **exactly one definition** and every ceiling check and every
read-model field calls it. Pinned by two source scans in
`test_subscription_ceiling.py` (the shape of `APRAS-39` §5.5's grep pin):

* `test_included_modules_has_at_most_four_homes` — an **upper bound**, and the
  name says so. The scan is over the AST of every file in `backend/app/**`, and
  it counts a file as a home when the name `included_modules` appears there
  either as an **attribute access** (`ast.Attribute`, e.g. `plan.included_modules`)
  **or** as a **field declaration** (an `ast.AnnAssign` / `ast.arg` whose target
  is that name). Both forms are counted because `models/plan.py` and
  `schemas/plan.py` contain *declarations only* — they never access the
  attribute — so an attribute-access-only scan would not see them and an
  *equality* over four files would be unsatisfiable. The assertion is therefore:

  ```
  homes ⊆ {"app/models/plan.py", "app/schemas/plan.py",
           "app/services/plan_service.py", "app/services/subscription_service.py"}
  and, in subscription_service.py, every occurrence is inside the body of
  `SubscriptionService.entitlement`
  and "build_read" is not among the enclosing function names anywhere
  ```

  An upper bound is the property that matters: a second, divergent ceiling
  cannot be introduced silently, while a legitimate refactor that drops one of
  the four (a schema that stops restating the field, say) does not turn the pin
  red for no reason. The scan is over the **AST**, never over source text: the
  field comments in this section and in `models/plan.py` contain the literal
  string and must not count. `build_read` is *not* one of the homes, and does
  not need to be: it reads `ent.included`.
* `test_build_read_derives_everything_from_the_entitlement_result` — the body
  of `build_read` **touches the session not at all**. AST-scoped to that
  function: no `session.` attribute access of any kind (no `session.exec`, no
  `session.get`, no `session.query`), no `select(` call, no reference to the
  names `Plan`, `TenantSubscription` or `SubscriptionChange`, and no
  `.included_modules` / `.courtesy_modules` attribute access. It calls
  `entitlement` exactly once and reads `ent.subscription`, `ent.plan`,
  `ent.included`, `ent.courtesy`, `ent.all` and `ent.managed`.

This is the resolution of the previous round's B4 and of round 2's F2: the
distinction between "included by the plan" and "granted as courtesy" is
reachable inside the read model *because* the ceiling is returned structured,
the plan the read model embeds and prices from arrives on the same result, and
the two pins are therefore satisfiable together rather than jointly
contradictory. `build_read` becomes a pure function of `(tenant, ent)`.

### 6.4 `estimated_monthly_total` — inert, and courtesy is free

```
estimated_monthly_total = ent.plan.base_price
                        + Σ ent.plan.module_prices.get(m, 0.0)
                          for m in active(tenant) & TOGGLEABLE_MODULES
                          if m not in ent.courtesy
```

(`ent.plan` and `ent.courtesy`, never a `Plan` lookup and never
`subscription.courtesy_modules`: §6.3's second scan forbids `build_read` from
querying anything or from reading either JSON column directly. `ent.plan` is
the row `entitlement` already loaded, so the whole read costs one query.)

`None` when there is no subscription. **Courtesy modules are excluded** —
that is what "cortesia" means, and it is what makes the courtesy grant
mechanically distinguishable from a contracted one in a second, independent
way (the total does not move). Contracting or cancelling a module **does**
move it, which is the board's "ajustando o que é cobrado", satisfied without
charging anything.

Pinned by `test_subscription_api.py::test_contracting_a_module_raises_the_estimated_total`
and `..._a_courtesy_module_is_free`.

---

## 7. Migration `0035_add_subscription_tables`

* `revision = "0035_add_subscription_tables"` — **28** characters
  (`python -c 'print(len("0035_add_subscription_tables"))'` → `28`), inside
  the 32-char `alembic_version.version_num` limit.
* `down_revision = "0034_add_tenant_modules"` (`APRAS-39`'s head). **Read
  `alembic heads` at the merge base first** and chain onto whatever single
  head it actually reports; if it differs, say so in the PR body.
* `upgrade()`: three `op.create_table` calls, in FK order — `plan`,
  `tenant_subscription`, `subscription_change`. JSON columns get
  `server_default="[]"` / `"{}"` exactly as the models declare (portable
  `sa.JSON`, never `JSONB` or `ARRAY`: `tests/conftest.py` builds this schema
  on `sqlite://`). `tenant_subscription.tenant_id` is
  `ForeignKey("tenant.id", ondelete="RESTRICT")` + the unique constraint
  `uq_tenant_subscription_tenant`; `plan_id` is `ondelete="RESTRICT"`;
  `subscription_change.subscription_id` is `ondelete="CASCADE"`.
* `downgrade()`: `op.drop_table` in reverse order.
* **No data statement in either direction, and no seeded plan.** This is what
  makes `0035` exactly reversible, and it is the no-seeds doctrine
  (`APRAS-49` §9.2): a fresh install has no plans, therefore no subscriptions,
  therefore every tenant keeps `APRAS-39`'s all-on default (§4.6).
* `alembic heads` reports exactly one head afterwards.
* Run it for real against the **throwaway Postgres on port 5436** and quote
  `upgrade head` → `downgrade -1` → `upgrade head`, plus `\d plan`,
  `\d tenant_subscription`, `\d subscription_change` and the `pg_constraint`
  listing, in the PR body. **`nexdom` is protected — never point a migration
  run at it.**

---

## 8. Frontend

### 8.1 Types — `src/types/subscription.ts` (new)

`Plan`, `ModuleEntitlement`, `Subscription`, `SubscriptionChange`,
`SubscriptionSource = "CORE" | "UNMANAGED" | "PLAN" | "COURTESY" | "OVERRIDE"`,
mirroring §5.4 field for field.

### 8.2 Data — `src/api/subscription.ts`, `src/api/plans.ts`, hooks

* `src/api/subscription.ts` — `getSubscription()`, `putSubscriptionModules(active)`,
  `getSubscriptionHistory()`.
* `src/api/plans.ts` — `listPlans()`, `createPlan()`, `updatePlan(id, patch)`,
  `getTenantSubscription(tenantId)`, `putTenantSubscription(tenantId, body)`,
  `putTenantCourtesy(tenantId, body)`.
* `src/hooks/useSubscription.ts` — `useSubscription()` (`queryKey:
  ["subscription"]`), `useSubscriptionHistory()`
  (`["subscription","history"]`), `useSetSubscriptionModules()`.
* `src/hooks/usePlans.ts` — `usePlans()` (`["plans"]`), `useCreatePlan`,
  `useUpdatePlan`, `useTenantSubscription(tenantId)`
  (`["tenants", tenantId, "subscription"]`, `enabled: !!tenantId`),
  `useSetTenantPlan`, `useSetTenantCourtesy`.

**Cache-key discipline, and why it matters here.** `["subscription"]` starts
with `"subscription"`, so `setActingTenant`'s `resetQueries` predicate
(`queryKey[0] !== "tenants"`, APRAS-38/39) **resets** it on a tenant switch —
correct, it is acting-tenant data. `["tenants", id, "subscription"]` starts
with `"tenants"` and is **preserved** — correct, it is keyed by an explicit
tenant id. Pinned by `useSubscription.test.ts`.

**Every mutation that can change `tenant.disabled_modules` must invalidate
`["me","permissions"]`** — `useSetSubscriptionModules`, `useSetTenantPlan`
and `useSetTenantCourtesy` all do. Without it the navbar keeps showing a menu
the API has just started refusing. Pinned by a named test per hook.

### 8.3 Routes and menu

```ts
ROUTE_ACCESS["/subscription"]          = { module: "billing" };
ROUTE_ACCESS["/admin/plans"]           = { superuser: true };
ROUTE_ACCESS["/admin/subscriptions"]   = { superuser: true };
```

`{ superuser: true }` is `APRAS-39` §10.1's third `AccessRule` shape, for its
reason: these routes are superuser-guarded and carry **no** catalogue
permission, so no `{anyOf}` rule can express them, and
`{anyOf:["tenants:update"]}` is specifically wrong (a tenant_admin holds it
through the whole-catalogue short-circuit but the API answers 403).

`NAV_ITEMS` gains three entries — `nav.subscription` → `/subscription`,
`nav.plans` → `/admin/plans`, `nav.tenantSubscriptions` → `/admin/subscriptions` —
each carrying the same rule object as its `ROUTE_ACCESS` entry, so F4's
"every nav item's access *is* its route's rule" test keeps passing.

### 8.4 Pages

* **`src/features/user-administration/pages/SubscriptionPage.tsx`** (tenant).
  Current plan card (name, description, status badge, `started_at`,
  `estimated_monthly_total` + currency, with an explicit "valores
  informativos — nenhuma cobrança é feita" note); a list of the toggleable
  modules grouped by `APRAS-39` §2.3's clusters; a Save button; and a
  **history table** below (kind badge, modules, who, when, reason).

  **The module row has exactly four states, chosen by a stated precedence.**
  The four conditions of the previous round overlapped and had no order; this
  is the total, disjoint replacement, evaluated **top to bottom, first match
  wins** — `OVERRIDE > COURTESY > PLAN > out-of-plan`:

  | # | Condition | Rendering | In the `PUT` payload? |
  |---|---|---|---|
  | 1 | `source === "OVERRIDE"` | **no checkbox**; an "ativo por decisão do operador" badge; read-only | **never** |
  | 2 | `courtesy && !in_plan` | **no checkbox**; a "cortesia" badge; "gratuito" in place of the price; read-only | **never** |
  | 3 | `in_plan` | a **checkbox**, checked iff `is_active`, enabled iff `can_contract`; the module's `monthly_price` beside it | **yes**, iff checked |
  | 4 | otherwise | **no checkbox**; unchecked-looking, greyed, "fora do plano" hint | **never** |

  Rules 1 and 2 are already mutually exclusive by §4.7 (`OVERRIDE` means
  active and in neither set), and rule 2 is written on `courtesy && !in_plan`
  rather than `source === "COURTESY"` so that a courtesy module which is
  *inactive* (source `null`) still renders as a courtesy row instead of
  falling through to rule 4. Stating the order anyway is what makes the
  mapping a function rather than four competing predicates.

  **The payload derivation, exactly.**

  ```ts
  const active_modules = modules
    .filter((m) => !m.is_core && m.in_plan && m.source !== "OVERRIDE")
    .filter((m) => checked[m.module])
    .map((m) => m.module);
  ```

  So the body is **the contracted set only** — the plan-covered checkboxes and
  nothing else. Courtesy and override modules are display-only rows, are never
  sent, and are never dropped: §4.4 (a)'s `preserved` term keeps them active
  on the server. This closes both halves of the previous round's B3 hazard —
  Save can no longer be a permanent 400 (an out-of-entitlement module is never
  in the payload) and can no longer silently kill an override (omission does
  not deactivate anything the tenant does not govern).

  The no-subscription state (`plan === null`) renders the plan card as an
  empty state, renders **every** module as a read-only rule-4 row, and
  disables Save.
* **`.../pages/PlansAdminPage.tsx`** (superuser). Plan table + create/edit
  form with the module checklist, base price, per-module prices, currency and
  `is_active`.
* **`.../pages/TenantSubscriptionsPage.tsx`** (superuser). A tenant `<select>`
  (from `GET /api/v1/tenants`), the tenant's current subscription, a plan
  `<select>` + status + notes with Save, a courtesy checklist with a required
  `reason` field, and the tenant's history.

**`APRAS-39`'s `/admin/modules` page is not touched.** It is the raw switch;
these are the commercial surfaces. Both are reachable, they write the same
column, and `/admin/modules` remains the repair tool (§4.2). Stated here so
the overlap reads as a decision.

### 8.5 i18n — `en.json` and `pt.json`, both

* `nav.subscription` — "Subscription" / "Assinatura";
  `nav.plans` — "Plans" / "Planos";
  `nav.tenantSubscriptions` — "Tenant subscriptions" / "Assinaturas dos condomínios".
* `subscription.*` — title, currentPlan, noPlan, status labels (3), startedAt,
  estimatedTotal, inertPriceNotice, contract, cancel, save, saved, saveError,
  notEntitled, historyTitle, empty, and `subscription.source.*` (the six §4.7
  values) and `subscription.kind.*` (the five §3.4 kinds).
* `plans.*` — title, new, name, description, includedModules, basePrice,
  modulePrices, currency, isActive, save, saved, saveError, inactiveBadge.
* `modules.names.billing` — "Billing" / "Assinatura", added to `APRAS-39`'s
  26 module labels, taking them to **27**.

`src/i18n/__tests__/index.test.ts` already asserts (from `APRAS-39` §11) that
the `en`/`pt` key sets are identical and that `modules.names` carries exactly
the module labels; its local constant goes **26 → 27**. Re-measure the leaf
count at the merge base and quote baseline and final in the PR body. If the
key sets have drifted apart, **fix the drift** rather than weakening the
assertion.

---

## 9. Accounting — every pinned number, as a delta

All values are relative to the **`APRAS-39` merge base** (i.e. after 47, 48,
49 and 39 land). The predicted absolute values are `APRAS-39`'s own
predictions carried forward; **the deltas are the contract** (§0 rule 2).

### 9.1 Routes, permissions and the matrix

| Constant | Predicted base | Delta | Predicted final |
|---|---|---|---|
| `len(PERMISSIONS)` | 159 | **+2** | **161** |
| `len(ROUTE_PERMISSIONS)` | 180 | **+3** | **183** |
| `len(UNGUARDED_ROUTES)` | 15 | **+7** | **22** |
| total routes | 195 | **+10** | **205** |
| `len(GLOBAL_ROUTES)` (`test_tenant_route_scope.py`) | 20 | **+7** | **27** |
| `ADMIN_ONLY_ROUTES` (`test_permission_enforcement.py`) | 7 | **+7** | **14** |
| `ADMIN_ONLY_ROUTES` (`test_tenant_admin.py`, independent copy) | 7 | **+7** | **14** |
| `MODULES` | 26 | **+1** | **27** |
| `CORE_MODULES` | 3 | **+1** | **4** |
| `TOGGLEABLE_MODULES` | 23 | **0** | **23** |
| `len(REQUEST_BODIES)` (`tests/matrix_world.py`) | 89 | **+1** | **90** |
| `EXPECTED_REQUEST_BODY_COUNT` (`test_permission_parity_matrix.py`) | 89 | **+1** | **90** |
| `matrix_world.py` docstring's write-route count | 89 | **+1** | **90** |
| `F2_CELL_COUNT` (frozen, §9.2) | 1080 | **0** | **1080** |
| `APRAS_40_CELL_COUNT` (new file, §9.2) | — | **+18** | **18** |
| `EXPECTED_CELL_COUNT` = `F2_CELL_COUNT + APRAS_40_CELL_COUNT` | 1080 | **+18** | **1098** |

The three new `ROUTE_PERMISSIONS` entries:

```python
    # §5.1 billing -- /api/v1/subscription (APRAS-40)
    ("GET", "/api/v1/subscription"): "billing:read",
    ("GET", "/api/v1/subscription/history"): "billing:read",
    ("PUT", "/api/v1/subscription/modules"): "billing:manage",
```

**`PUT /api/v1/subscription/modules` is a mapped write route, so the harness
owes it a request body.** `tests/matrix_world.py`'s `REQUEST_BODIES` covers
*exactly* the `POST`/`PUT`/`PATCH` keys of `ROUTE_PERMISSIONS`
(`test_request_bodies_covers_exactly_the_write_routes`), and a missing entry
is never allowed to default to `{}` — the cell would answer **422**, which the
§9.2 semantic oracle forbids for a profile that holds the permission. One
entry is added:

```python
    # APRAS-40 §5.1 -- the complete desired CONTRACTED set (§4.4 a). An empty
    # list is shape-valid and semantically the "cancel everything the plan
    # covers" request, so the cell measures authorization and nothing else.
    ("PUT", "/api/v1/subscription/modules"): _static({"active_modules": []}),
```

and with it move, in the same commit, `EXPECTED_REQUEST_BODY_COUNT` (89 → 90,
`tests/test_permission_parity_matrix.py`) and the sentence in
`tests/matrix_world.py`'s module docstring that reads *"for exactly the 89
POST/PUT/PATCH routes of `ROUTE_PERMISSIONS`"* (→ 90). The two existing tests
`test_every_write_route_has_a_request_body` and
`test_request_bodies_covers_exactly_the_write_routes` pin all three; leaving
any one of them behind is a red suite, not a warning.

The two `GET`s take no body and the seven superuser routes are unguarded
(`UNGUARDED_ROUTES`), so they contribute **no** `REQUEST_BODIES` entry: the
delta is exactly **+1**, not +4.

The seven new `UNGUARDED_ROUTES` entries, each with the file's required
comment (`# superuser-only, guarded by deps.get_current_superuser (APRAS-40)`):
`GET`/`POST` `/api/v1/plans/`, `GET`/`PATCH` `/api/v1/plans/{plan_id}`,
`GET`/`PUT` `/api/v1/tenants/{tenant_id}/subscription`,
`PUT` `/api/v1/tenants/{tenant_id}/subscription/courtesy`. The same seven go
into `GLOBAL_ROUTES` (both routers are `GLOBAL_SCOPED`) and into **both**
copies of `ADMIN_ONLY_ROUTES`, and both `test_get_current_superuser_is_exactly_the_seven_tenant_routes`
cases are renamed `..._is_exactly_the_fourteen_operator_routes` (the name
`APRAS-39` leaves them at, +7).

**`test_tenant_admin.py::test_no_tenant_scoped_route_keeps_a_global_admin_guard`
stays green for free**: all seven superuser routes are on `GLOBAL_SCOPED`
routers and depend on no `get_current_tenant`. This task must not be the one
that breaks it. (If `APRAS-49` §8.4's tenant-scoped `PATCH
/users/{id}/superuser` already amended or retired that case, follow the tree.)

### 9.2 The parity baseline: **the F2 file is frozen, a second file carries the 18 new cells**

The previous round tried to re-record `tests/data/parity_matrix_baseline.json`
and that was wrong four ways: its `_meta.regenerate` copies only `tests/` into
a worktree at `02c2025` and derives `CELLS` from *that* tree's
`ROUTE_PERMISSIONS`, so it can emit 1080 cells and no `/api/v1/subscription`
leaf ever; `record()` stamps both `merge_base_sha` and `regenerate` from
`git rev-parse HEAD`, so any re-record moves the sha off `02c2025` — the
anchor `tests/test_legacy_role_permissions.py` and
`tests/test_permission_enforcement.py` assert in prose — turning F2's star
test into a tautology, silently; the recorder's dirty-tree guard means it can
only run after `app/` is committed, an ordering nothing stated; and "0 modified
leaves" is false for `_meta` by construction.

**Decision (orchestrator, round 1): the F2 baseline is not touched at all.**

#### 9.2.1 The frozen file

`backend/tests/data/parity_matrix_baseline.json` stays **byte-identical**:

* 1080 cells, `_meta.cell_count == 1080`;
* `_meta.merge_base_sha == "02c2025abcda4626569921eafb3863dfc540eb9e"`;
* `_meta.regenerate` unchanged, `git worktree add` and all;
* the prose anchors that quote that sha stay valid and stay quoted:
  `tests/test_legacy_role_permissions.py`'s module docstring ("1080 real HTTP
  cells recorded against unswapped production at merge base **02c2025…** — the
  same sha as `_meta.merge_base_sha`") and `tests/test_permission_enforcement.py`'s
  `RULE_C_BASELINE` / `RULE_N_BASELINE` comment. **Neither sentence is edited
  by this task.**

Pinned mechanically, not by good intentions, in
`tests/test_permission_parity_matrix.py`:

```python
F2_CELL_COUNT = 1080
F2_MERGE_BASE_SHA = "02c2025abcda4626569921eafb3863dfc540eb9e"
#: Measure once at the merge base with
#: `shasum -a 256 backend/tests/data/parity_matrix_baseline.json` and quote
#: base-beside-final in the PR body. At the spec sha (aa8953d) it is
#: 3691cea1cddfa13ddcba4cf9b5c1c3e8b7bbac7c295bae4bbd4e3e8c45c016cd.
F2_BASELINE_SHA256 = "<measured at the merge base>"


def test_the_f2_baseline_is_untouched_by_apras_40():
    raw = BASELINE_PATH.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == F2_BASELINE_SHA256
    meta = json.loads(raw)["_meta"]
    assert meta["merge_base_sha"] == F2_MERGE_BASE_SHA
    assert meta["cell_count"] == F2_CELL_COUNT == 1080
    assert "git worktree add" in meta["regenerate"]


def test_the_f2_sha_anchors_still_agree_with_the_frozen_file():
    # The two prose anchors quote the sha the frozen file declares.
    for name in ("test_legacy_role_permissions.py", "test_permission_enforcement.py"):
        assert F2_MERGE_BASE_SHA in (BACKEND_ROOT / "tests" / name).read_text(
            encoding="utf-8"
        )
```

If the 47/48/49/39 chain has legitimately moved the F2 file (it should not —
each of those specs pins it byte-identical), re-measure the sha256 at the
actual merge base, quote both values in the PR body, and say why.

#### 9.2.2 The additive file

`backend/tests/data/parity_matrix_baseline_40.json` — **new**, same shape,
**same five `_meta` keys**, so `META_KEYS` is reused verbatim and needs no
edit:

```json
{
  "_meta": {
    "merge_base_sha": "<the APRAS-39 merge base, 40 hex>",
    "generator": "tests/tools/record_parity_baseline.py",
    "harness": "tests/matrix_world.py",
    "cell_count": 18,
    "regenerate": "cd backend && POSTGRES_URL=sqlite:// SECRET_KEY=parity-matrix uv run python -m tests.tools.record_parity_baseline --out tests/data/parity_matrix_baseline_40.json --merge-base <sha> --routes 'GET /api/v1/subscription' --routes 'GET /api/v1/subscription/history' --routes 'PUT /api/v1/subscription/modules'"
  },
  "cells": { "<profile>": { "GET": { "/api/v1/subscription": 403 } } }
}
```

**What `merge_base_sha` means here, stated because it is not what it means in
the F2 file.** The three routes **do not exist** at the `APRAS-39` merge base,
so no worktree at that sha can reproduce these cells and this file is *not* a
pre-swap recording. The sha names the **branch point the `+3` route delta is
measured from** — the provenance of the accounting, not of the statuses — and
`regenerate` is correspondingly a plain scoped recorder invocation, run from
the APRAS-40 branch with a clean `app/`, with **no** `git worktree add`. That
is honest, and it is the only coherent reading. The file's independent check is
therefore not "re-record and diff" but the semantic oracle of §9.2.4, which
derives the expected answers from the permission map rather than from the file
— which is what keeps it from being a tautology.

**The additive file gets F2's hygiene checks too, not only its provenance
check.** The F2 file is guarded by three cases that never look at semantics:
`test_baseline_file_exists`, `test_baseline_carries_no_absolute_path_and_no_timestamp`
and `test_baseline_records_only_integer_status_codes`. A second recorded
artefact with none of them would be a second place a machine-specific path, a
timestamp or a stringified status could enter the repository unnoticed — the
recorder is the same program, so the same hazards apply. §9.2.5 therefore adds
`test_the_apras_40_baseline_carries_no_absolute_path_and_no_timestamp` and
`test_the_apras_40_baseline_records_only_integer_status_codes`, each the F2
case's body with `BASELINE_PATH` → `BASELINE_40_PATH` and `load_baseline()` →
`load_apras_40_baseline()`, beside
`test_the_apras_40_baseline_declares_its_provenance`. The F2 three are **not**
edited, generalised or parametrised over both files: they are pinned green and
unedited by §10.2, and duplicating two short bodies is cheaper than moving a
case the F2 freeze depends on.

#### 9.2.3 Recorder parameterisation, and the commit ordering

`backend/tests/tools/record_parity_baseline.py` gains two flags and one guard.
Nothing else in it changes; `assert_clean_production_tree` is untouched.

```python
#: The frozen F2 artefact. The recorder refuses to write it, full stop
#: (APRAS-40 §9.2.1): new routes get their own additive file. F2's own
#: `_meta.regenerate` writes to /tmp/regen.json, so it is unaffected.
FROZEN = "tests/data/parity_matrix_baseline.json"


def select_cells(routes: list[str] | None) -> list[tuple[str, str, str]]:
    # `CELLS` filtered to the named routes. `None`/empty means all of them.
    if not routes:
        return list(CELLS)
    wanted = {tuple(spec.split(" ", 1)) for spec in routes}
    unknown = sorted(wanted - set(ROUTE_PERMISSIONS))
    if unknown:
        print(f"unknown routes: {unknown}", file=sys.stderr)
        raise SystemExit(2)
    return [cell for cell in CELLS if (cell[1], cell[2]) in wanted]


def record(sha: str, cells=None, regenerate: str | None = None) -> dict:
    cells = list(CELLS) if cells is None else cells
    ...                                    # the existing body, iterating `cells`
    "cell_count": len(cells),
    "regenerate": regenerate or REGENERATE.format(sha=sha),
```

* `--routes` — repeatable, `"METHOD /path"`. An unknown route is
  `SystemExit(2)` naming it. Omitted → today's behaviour, all of `CELLS`.
* `--merge-base` — a 40-hex sha, defaulting to `head_sha()`. Used for the
  scoped file, whose cells are recorded on the APRAS-40 branch while the sha
  names the branch point (§9.2.2). Validated with
  `git rev-parse --verify <sha>^{commit}`; a sha the repository does not know
  is `SystemExit(2)`.
* **The `FROZEN` guard**: if the resolved `--out` equals
  `<backend>/tests/data/parity_matrix_baseline.json`, print and
  `raise SystemExit(2)` **before** anything is built, `--overwrite` or not.
* When `--routes` is given, the emitted `_meta.regenerate` is the literal
  invocation that produced the file — `--out`, `--merge-base` and every
  `--routes` argument — so `meta["merge_base_sha"] in meta["regenerate"]`
  holds and the string is executable exactly as written.

`tests/test_permission_parity_matrix.py::test_the_recorder_has_no_allow_dirty_escape`
AST-scans the recorder's `add_argument` literals and asserts they are exactly
`{"--out", "--overwrite"}`. It becomes
`{"--out", "--overwrite", "--routes", "--merge-base"}`, and its docstring keeps
saying what it is for: **there is still no `--allow-dirty`, and neither new
flag weakens the dirty-tree refusal.** A new sibling,
`test_the_recorder_refuses_to_write_the_frozen_f2_baseline`, pins the `FROZEN`
guard on both branches.

**The commit ordering is a constraint, not a suggestion.** The recorder exits
`2` while `git status --porcelain -- app/` is non-empty, so the scoped file
cannot be produced from a working tree that still holds uncommitted backend
code. The implementer therefore:

1. writes **all** of `backend/app/` — models, schemas, services, endpoints,
   `permissions.py`, `exceptions.py`, the migration — and **commits it**. The
   three routes now exist in `ROUTE_PERMISSIONS`; `tests/` may be dirty, the
   guard only looks at `app/`.
2. runs, from `backend/`, with `app/` clean:

   ```
   POSTGRES_URL=sqlite:// SECRET_KEY=parity-matrix \
   uv run python -m tests.tools.record_parity_baseline \
     --out tests/data/parity_matrix_baseline_40.json \
     --merge-base <the APRAS-39 merge base sha> \
     --routes 'GET /api/v1/subscription' \
     --routes 'GET /api/v1/subscription/history' \
     --routes 'PUT /api/v1/subscription/modules'
   ```

3. **reads the 18 recorded numbers against §9.2.4 before committing them.** A
   recorded value that disagrees with the prediction is a bug in the code, not
   a new prediction.
4. commits the new baseline, then the test-side changes.

`--overwrite` is never passed and `--out` never names the frozen file; the
`FROZEN` guard makes step 4 unable to clobber it even by typo. **No step of
this task ever runs the recorder unscoped.**

#### 9.2.4 The 18 predicted values

The matrix world is one tenant (`DEFAULT_TENANT_ID`) and `run_cell` always
sends `Authorization: Bearer <profile token>` **and**
`X-Tenant-Id: DEFAULT_TENANT_ID`. The three routes are `TENANT_SCOPED`
(§5.1), so the acting tenant *does* resolve and the cells measure the
permission decision rather than a missing header — which is exactly why the
routes are on a tenant-scoped router in the first place. That tenant has **no
subscription row** and no `disabled_modules`, so §4.6 governs the permitted
answers.

| Profile | `GET /subscription` | `GET /subscription/history` | `PUT /subscription/modules` |
|---|---|---|---|
| the five non-`ADMINISTRATOR` profiles | **403** | **403** | **403** |
| `ADMINISTRATOR` | **200** | **200** | **404** |

* the five: no recorded legacy bundle holds `billing:read` or `billing:manage`
  (§2.3), so `require_permission` refuses — the plain denial shape, needing no
  `DENIAL_SHAPE_OVERRIDES` entry;
* `ADMINISTRATOR`: `matrix_world._seed_world` builds that profile with
  `is_superuser=True` (`APRAS-49` §11.1, `APRAS-47` §3.3), so `APRAS-47`'s
  short-circuit grants the whole catalogue; the two `GET`s answer the §4.6
  unmanaged read, and the `PUT` answers **404 `"This tenant has no
  subscription"`** — *not* 422, which is why §9.1's `REQUEST_BODIES` entry is
  mandatory rather than optional.

**Verify, do not assume, how the post-F5 world builds its profiles.** If the
landed `matrix_world` does not give `ADMINISTRATOR` `is_superuser=True`, the
three `ADMINISTRATOR` cells become 403 and `NON_ROLE_403` is *not* where that
gets recorded: say so in the PR body and stop, because it would mean §2.3's
access story is wrong.

#### 9.2.4.1 The oracle predicate gains a superuser branch

The prediction above and the module's semantic oracle disagree unless `holds()`
is told about the flag, and **the oracle is what moves, not the artefact**:
`tests/data/parity_matrix_baseline.json` is frozen (§9.2.1);
`tests/test_permission_parity_matrix.py` is ordinary test code and always was.

The disagreement, exactly. Today
(`test_permission_parity_matrix.py:254-255`):

```python
def holds(role: str, method: str, path: str) -> bool:
    return ROUTE_PERMISSIONS[(method, path)] in LEGACY_ROLE_PERMISSIONS[UserRole(role)]
```

No recorded legacy bundle carries `billing:read` or `billing:manage` (§2.3 —
that is the *point* of §2.3), so all six profiles are `not holds(...)` on all
three routes. `test_every_denied_cell_is_denied_in_the_baseline` then demands
403 from the three `ADMINISTRATOR` cells, which are 200 / 200 / 404 — three
offenders, a red suite, and no escape: `DENIAL_SHAPE_OVERRIDES` is pinned at
exactly six with `{role …} == {"GUEST"}`
(`test_denial_shape_overrides_is_exactly_six`), so it cannot hold them even if
this task were willing to grow it, which it is not.

`APRAS-40` is the first task where this can happen at all: `billing:read` /
`billing:manage` are the first **permission-guarded** catalogue strings minted
after the legacy bundles were recorded (every earlier superuser-only route went
into `UNGUARDED_ROUTES`, and every string in `SUPERUSER_ONLY_PERMISSIONS` *is*
in `ADMINISTRATOR`'s recorded bundle, so `holds()` is already `True` there).

**The predicate becomes superuser-aware**, in the same terms `APRAS-49` §11.1
uses (post-F5 the bundle comes from `tests/data/legacy_role_bundles.json` ∪
`NEW_TIER` rather than from `LEGACY_ROLE_PERMISSIONS`; the branch is written
against `bundle()` so it survives that swap unedited):

```python
#: The profiles `matrix_world._seed_world` builds with `is_superuser=True`
#: — the ADMINISTRATOR profile only (APRAS-49 §11.1). Not asserted by fiat:
#: `test_the_superuser_profiles_are_the_ones_the_world_seeds` reads the flag
#: back off the seeded users.
SUPERUSER_PROFILES: frozenset[str] = frozenset({"ADMINISTRATOR"})

#: The one permission the recorded ADMINISTRATOR bundle does not carry, and
#: the one place the superuser branch must NOT fire. See below: production
#: refuses `GET /packages/my-lots` to an administrator in the *service*
#: (`PackageService.get_my_lots`, a routing message), not at the permission
#: gate, so that cell answers 403 with the flag set or unset -- APRAS-47 §4.1
#: says exactly this ("it costs zero matrix cells"). Read from
#: `app.core.permissions.ADMIN_GAP_PERMISSIONS`; if IAM F5 removed that
#: constant, inline the one-element frozenset here with this comment.
#: At the spec sha this is exactly {"packages:my_lots_read"}. It may grow:
#: APRAS-49 §3.0 adds `occurrences:read_assigned` to the same tier, unmapped.
#: Read the constant, never a literal — the branch and both new cases below are
#: written so an *unmapped* addition changes nothing.
MATRIX_ADMIN_GAP: frozenset[str] = ADMIN_GAP_PERMISSIONS


def bundle(profile: str) -> frozenset[str]:
    """The recorded legacy bundle of one profile — `LEGACY_ROLE_PERMISSIONS`
    pre-F5, `legacy_role_bundles.json` ∪ `NEW_TIER` after it."""


def holds_by_bundle(profile: str, method: str, path: str) -> bool:
    """The F2 predicate, verbatim. Kept so the branch below is provably inert."""
    return ROUTE_PERMISSIONS[(method, path)] in bundle(profile)


def holds(profile: str, method: str, path: str) -> bool:
    """Does this profile pass the *authorization* gate of this route?

    APRAS-40 §9.2.4.1: a superuser profile passes it for every catalogue
    permission, by APRAS-47's short-circuit -- except the recorded admin gap,
    whose route refuses an administrator for a non-permission reason and whose
    recorded 403 is therefore right either way.
    """
    if (
        profile in SUPERUSER_PROFILES
        and ROUTE_PERMISSIONS[(method, path)] not in MATRIX_ADMIN_GAP
    ):
        return True
    return holds_by_bundle(profile, method, path)
```

**The `MATRIX_ADMIN_GAP` clause is not decoration, and the orchestrator's
"ADMINISTRATOR already holds every legacy permission" is off by exactly one
cell — measured, not assumed.** At the spec sha:

```
$ uv run python -c "from app.core.permissions import *; from app.models.enums import UserRole; \
  a = LEGACY_ROLE_PERMISSIONS[UserRole.ADMINISTRATOR]; \
  print(sorted(set(PERMISSIONS) - a)); \
  print([(m, p) for (m, p), q in ROUTE_PERMISSIONS.items() if q not in a])"
['packages:my_lots_read']
[('GET', '/api/v1/packages/my-lots')]
```

and that cell's recorded status is **403**, with no `NON_ROLE_403` entry. An
*unqualified* superuser branch would turn it from "denied and 403" into
"permitted and 403", and `test_no_permitted_cell_is_403_in_the_baseline`
asserts `excused == set(NON_ROLE_403)` by **set equality** — so it would go red
and the only repair would be a new `NON_ROLE_403` entry, i.e. exactly the F2
collection this task must not move. Excluding the recorded gap is the minimal
correction, it is the one this task takes, and it is the reason the invariant
below is provable rather than hopeful. **Re-run the two-line measurement at the
actual merge base and paste it in the PR body**; if the gap has grown, the
clause still holds (it reads the constant) and the PR body says so.

**Why the branch is inert over all 1080 F2 cells.** `holds` differs from
`holds_by_bundle` only where `holds_by_bundle` is `False`, the profile is
`ADMINISTRATOR` and the permission is outside `MATRIX_ADMIN_GAP` — and the
measurement above shows the *only* F2 route ADMINISTRATOR's bundle misses is
the gap route itself. So every F2 cell keeps its verdict, every one of the six
`holds()` callers keeps its current answer on those cells, and the branch
changes nothing except making the three new `ADMINISTRATOR` billing cells
permitted. (Keeping its *answer* is not the same as keeping its *body*: all six
also take §9.2.5's one-line loader switch. §9.2.5 is the authority on which
bodies move.) Pinned, not argued, by three new cases (§9.2.5):

```python
def test_the_superuser_branch_changes_no_f2_verdict():
    """APRAS-40's superuser branch is additive on the 18 new cells and inert
    on the 1080 recorded ones."""
    moved = sorted(
        cell
        for cell in CELLS
        if (cell[1], cell[2]) not in APRAS_40_ROUTES
        and holds(*cell) != holds_by_bundle(*cell)
    )
    assert not moved, f"the superuser branch moved an F2 verdict: {moved}"


def test_the_admin_gap_is_the_only_bundle_gap_the_superuser_branch_excludes():
    unheld = sorted(
        (method, path)
        for method, path in ROUTE_PERMISSIONS
        if (method, path) not in APRAS_40_ROUTES
        and not holds_by_bundle("ADMINISTRATOR", method, path)
    )
    assert unheld == [("GET", "/api/v1/packages/my-lots")]
    # Intersected, deliberately. `ADMIN_GAP_PERMISSIONS` is defined over
    # *permissions* ADMINISTRATOR does not hold, mapped or not: APRAS-49 §3.0
    # adds `occurrences:read_assigned` to that tier as an in-code object
    # predicate that never enters `ROUTE_PERMISSIONS` (APRAS-49 §3.0: "none is
    # added to ROUTE_PERMISSIONS"). Only the *routed* part of the gap can ever
    # appear in `unheld`, so only the routed part is what this case is about;
    # a bare `== MATRIX_ADMIN_GAP` would go red for an unrouted addition, for a
    # reason having nothing to do with the superuser branch.
    assert {ROUTE_PERMISSIONS[cell] for cell in unheld} == (
        MATRIX_ADMIN_GAP & set(ROUTE_PERMISSIONS.values())
    )


def test_the_superuser_profiles_are_the_ones_the_world_seeds(matrix_run):
    """`SUPERUSER_PROFILES` is read back off the world, never declared at it."""
    engine, world = matrix_run
    with Session(engine) as session:
        seeded = {
            profile
            for profile, user_id in world.users.items()
            if session.get(User, user_id).is_superuser
        }
    assert seeded == SUPERUSER_PROFILES
```

The first is the invariant; the second is why the first can be true, and it
goes red the day a new mapped route lands that `ADMINISTRATOR`'s bundle misses
— which is exactly when a human should look again; the third is §9.2.4's
"verify, do not assume" turned into a test.

**What the third case's failure actually looks like, stated precisely.** The
branch keys off the hardcoded `SUPERUSER_PROFILES`, **not** off the seeded
flag, so an unflagged world does *not* make it unreachable: `holds()` still
returns `True` for the three `ADMINISTRATOR` billing cells, while an unflagged
`ADMINISTRATOR` would record **403** on all three. The consequence is therefore
two simultaneous red cases naming one cause —
`test_no_permitted_cell_is_403_in_the_baseline` (whose `excused` gains three
cells and breaks its set equality with `NON_ROLE_403`) **beside**
`test_the_superuser_profiles_are_the_ones_the_world_seeds` (whose `seeded` is
empty and `SUPERUSER_PROFILES` is not). That is loud, and it is the intended
shape; §9.2.4's instruction stands unchanged — **stop and report, do not
repair by adding `NON_ROLE_403` entries.** Note that seeding the flag is
genuinely `APRAS-49` §11.1's to land: at the spec's reference sha
`tests/matrix_world.py` contains **no** `is_superuser` at all (`_seed_world`
builds the six users with `role=` and `user_types=` and nothing else), so this
is a real precondition to verify, not a formality.

`MatrixWorld.users` is `dict[profile, UUID]` and carries ids only, which is why
the case re-opens a `Session` on the matrix engine rather than holding rows.

**The three bound collections keep their current size, unedited.** **No
`DENIAL_SHAPE_OVERRIDES`, `NON_ROLE_403` or `PERMITTED_422` entry is added or
removed by this task**; `test_denial_shape_overrides_is_exactly_six` (`len == 6`
and `{role …} == {"GUEST"}`), `test_non_role_403_is_bounded`,
`test_permitted_422_is_bounded` and the three `..._has_a_reason` cases stay
green **and unedited** — they load no baseline, so §9.2.5's loader switch does
not reach them. The predicate is what this task changes; the exception tables
are not, and neither is any recorded byte.

For the record, on the 18 new cells the extended oracle predicts exactly the
table above: the five non-`ADMINISTRATOR` profiles are `not holds(...)` and
403, so `test_every_denied_cell_is_denied_in_the_baseline` is satisfied with no
override; `ADMINISTRATOR` is `holds(...)` and 200 / 200 / **404**, which is
neither 403 nor 422 nor 5xx, so `test_no_permitted_cell_is_403_in_the_baseline`,
`test_no_permitted_cell_is_422_in_the_baseline` and `test_no_cell_is_5xx_in_the_baseline`
are all satisfied with no entry in any collection.

#### 9.2.5 How the test module reads two files

`tests/test_permission_parity_matrix.py` gains a union loader; every semantic
oracle switches to it, and the provenance and hygiene cases stay one-per-file.

```python
BASELINE_PATH    = BACKEND_ROOT / "tests" / "data" / "parity_matrix_baseline.json"
BASELINE_40_PATH = BACKEND_ROOT / "tests" / "data" / "parity_matrix_baseline_40.json"

F2_CELL_COUNT       = 1080
APRAS_40_CELL_COUNT = 18
EXPECTED_CELL_COUNT = F2_CELL_COUNT + APRAS_40_CELL_COUNT      # 1098

APRAS_40_ROUTES = frozenset({
    ("GET", "/api/v1/subscription"),
    ("GET", "/api/v1/subscription/history"),
    ("PUT", "/api/v1/subscription/modules"),
})

SUPERUSER_PROFILES = frozenset({"ADMINISTRATOR"})       # §9.2.4.1
MATRIX_ADMIN_GAP   = ADMIN_GAP_PERMISSIONS              # §9.2.4.1

#: Declared by APRAS-49 §11.1, NOT by this task. Named here because both
#: helpers below apply it; if F5 landed it under another name, follow the tree.
F5_PATH_RENAMES: dict[str, str]                         # existing, unedited


def load_file(path: Path) -> dict:
    """One recorded baseline document. Missing means **fail**, never skip.

    This is `load_baseline()`'s existing body, parameterised by path; the
    missing-file assertion and its message move here verbatim.
    """
    assert path.exists(), (
        f"the parity baseline {path} is missing; it is recorded by "
        "`uv run python -m tests.tools.record_parity_baseline` and a deleted "
        "baseline must be a red run, not a green one"
    )
    return json.loads(path.read_text(encoding="utf-8"))


def load_baseline() -> dict:
    """The F2 golden file, and only ever that (§9.2.1)."""
    return load_file(BASELINE_PATH)


def load_apras_40_baseline() -> dict:
    """The additive file of §9.2.2, and only ever that."""
    return load_file(BASELINE_40_PATH)


def cells_of(baseline: dict) -> set[tuple[str, str, str]]:
    """Every `(role, method, path)` a baseline document records, keyed the way
    `CELLS` is keyed — i.e. with `F5_PATH_RENAMES` already applied."""
    return {
        (role, method, F5_PATH_RENAMES.get(path, path))
        for role, by_method in baseline["cells"].items()
        for method, by_path in by_method.items()
        for path in by_path
    }


def load_union() -> dict[tuple[str, str, str], int]:
    """Both baselines as one `CELLS`-keyed cell map. Overlap is an error, not
    a merge."""
    merged: dict[tuple[str, str, str], int] = {}
    for path in (BASELINE_PATH, BASELINE_40_PATH):
        for role, by_method in load_file(path)["cells"].items():
            for method, by_path in by_method.items():
                for route, status in by_path.items():
                    key = (role, method, F5_PATH_RENAMES.get(route, route))
                    assert key not in merged, f"the two baselines overlap at {key}"
                    merged[key] = status
    return merged


def baseline_status(union, role, method, path) -> int:   # same arity, new first arg
    return union[(role, method, path)]
```

**`F5_PATH_RENAMES` is applied by both helpers, and that is not optional.**
`APRAS-49` §11.1 declares
`{"/api/v1/user-types/": "/api/v1/roles/", "/api/v1/user-types/{user_type_id}":
"/api/v1/roles/{role_id}"}` and re-keys **24** F2 cells (4 `(method, path)`
entries × 6 profiles) at comparison time rather than re-recording the frozen
file. A union loader that skipped the map would key those 24 cells under paths
`CELLS` no longer contains, and `set(union) == set(CELLS)` would fail with 24
missing and 24 spurious keys. The map is applied to **both** files, not only to
the F2 one: it is the identity on every path it does not name (the additive
file is recorded on this branch, after F5, so its three paths are already
current), and one keying rule is cheaper to keep true than two. If the landed
F5 applied the renames somewhere else — inside `load_baseline()` itself, or in
a `CELLS`-side adapter — **follow the tree and do not add a second
application**; the contract is that `load_union()`'s keys equal `set(CELLS)`,
and `test_the_two_baselines_partition_route_permissions_exactly` is what proves
it either way.

`load_baseline()` keeps its **name** and its **meaning** (the F2 file); only
its body changes, to a one-line delegation to `load_file`. Of its **twelve**
call sites at the merge base, **three** stay — `test_baseline_file_exists`,
`test_baseline_declares_its_provenance` and
`test_baseline_records_only_integer_status_codes`, the cases that are *about*
the frozen document rather than about the matrix — and one **new** case adds a
fourth, `test_the_two_baselines_partition_route_permissions_exactly`, which
reads the F2 file precisely in order to prove the partition.
(`test_baseline_carries_no_absolute_path_and_no_timestamp` reads
`BASELINE_PATH` directly and is not a call site at all.) The call sites that
switch from
`load_baseline()` to `load_union()` are **exactly nine**, named here so none is
missed: `test_baseline_covers_exactly_the_matrix`,
`test_every_denied_cell_is_denied_in_the_baseline`,
`test_every_denial_shape_override_is_needed`,
`test_no_cell_is_5xx_in_the_baseline`,
`test_no_permitted_cell_is_403_in_the_baseline`,
`test_every_non_role_403_is_needed`,
`test_no_permitted_cell_is_422_in_the_baseline`,
`test_every_permitted_422_is_needed`, and the parametrised
`test_cell_matches_the_recorded_baseline`.

**How much of each of the nine moves, and why — stated exactly, because §10.2
and ER-10 are held to it.**

* **Eight of the nine change exactly one line**: `baseline = load_baseline()`
  becomes `baseline = load_union()`. Every assertion, every `holds()` call,
  every collection iterated and every `baseline_status(baseline, …)` call is
  byte-identical, because `baseline_status` keeps its arity and only its first
  argument's type changes (dict-of-dicts → flat cell map).
* **`test_baseline_covers_exactly_the_matrix` is the one exception**: its body
  rebuilds the recorded key set from `baseline["cells"]`, which the flat map
  does not have, so the comprehension collapses to
  `assert set(load_union()) == set(CELLS)`. That is a shrink, not a
  weakening — the union loader already normalises the keys the comprehension
  used to normalise by hand.
* **Five of the nine would `KeyError`** on the 18 new cells if left on
  `load_baseline()`: `test_every_denied_cell_is_denied_in_the_baseline`,
  `test_no_cell_is_5xx_in_the_baseline`,
  `test_no_permitted_cell_is_403_in_the_baseline`,
  `test_no_permitted_cell_is_422_in_the_baseline` and
  `test_cell_matches_the_recorded_baseline` — all five iterate `CELLS`, which
  now includes the three new routes.
* **`test_baseline_covers_exactly_the_matrix` would fail its set equality**
  (18 cells short), not `KeyError`.
* **The three `..._is_needed` cases would stay green.**
  `test_every_denial_shape_override_is_needed`,
  `test_every_non_role_403_is_needed` and `test_every_permitted_422_is_needed`
  iterate their **own** dicts, every key of which is a recorded F2 cell, so
  `load_baseline()` would still resolve every lookup. They switch anyway, for
  uniformity: after this task every semantic oracle in the module reads the
  same map, and a future task that adds a `NON_ROLE_403` entry on an
  `APRAS-40` route does not have to rediscover which oracle reads which file.
  This is stated rather than glossed because "leaving it on `load_baseline()`
  is a `KeyError`" is **false** for these three, and a justification that is
  false in three of nine cases is not a justification.

**Four** existing cases take a small named edit of their own and the oracle
predicate takes §9.2.4.1's edit. Together with the nine loader switches above,
that is the **complete** list of existing cases this task touches in the
module — thirteen cases in all, nine of them by one line; **no other existing
case is edited**, and §10.2's must-not-change column is the same statement from
the other side:

| Case | Edit |
|---|---|
| `test_baseline_file_exists` | `== EXPECTED_CELL_COUNT` → `== F2_CELL_COUNT` |
| `test_baseline_declares_its_provenance` | `meta["cell_count"] == len(CELLS) == EXPECTED_CELL_COUNT` → `meta["cell_count"] == F2_CELL_COUNT`, plus a separate `len(CELLS) == EXPECTED_CELL_COUNT` |
| `test_the_ten_unguarded_routes_are_the_only_ones_excluded` | renamed to its new count (base + 7) and the literal with it |
| `test_the_recorder_has_no_allow_dirty_escape` | §9.2.3: the asserted `add_argument` literal set `{"--out", "--overwrite"}` → `{"--out", "--overwrite", "--routes", "--merge-base"}`; its docstring keeps saying there is still no `--allow-dirty` and that neither new flag weakens the dirty-tree refusal |
| `holds()` (not a case: the oracle predicate at l.254-255) | §9.2.4.1: split into `bundle()` / `holds_by_bundle()` / `holds()`, the last gaining the superuser branch. Every existing caller (`test_every_denied_cell_is_denied_in_the_baseline`, `test_every_denial_shape_override_is_needed`, `test_no_permitted_cell_is_403_in_the_baseline`, `test_every_non_role_403_is_needed`, `test_no_permitted_cell_is_422_in_the_baseline`, `test_every_permitted_422_is_needed`) keeps calling `holds()` with the same arguments — **the `holds()` call sites themselves are unedited**; those six bodies change only in the loader line above |

and ten cases are new:

| New case | Asserts |
|---|---|
| `test_the_f2_baseline_is_untouched_by_apras_40` | §9.2.1's sha256 + `_meta` pins |
| `test_the_f2_sha_anchors_still_agree_with_the_frozen_file` | §9.2.1's prose-anchor scan |
| `test_the_superuser_branch_changes_no_f2_verdict` | §9.2.4.1: `holds` and `holds_by_bundle` agree on every cell outside `APRAS_40_ROUTES` — the 1080 F2 verdicts are untouched by the predicate change |
| `test_the_admin_gap_is_the_only_bundle_gap_the_superuser_branch_excludes` | §9.2.4.1: `GET /api/v1/packages/my-lots` is the only mapped route `ADMINISTRATOR`'s recorded bundle misses, and its permission is exactly `MATRIX_ADMIN_GAP & set(ROUTE_PERMISSIONS.values())` — the **routed** part of the gap, so an unrouted F5 addition cannot break it |
| `test_the_superuser_profiles_are_the_ones_the_world_seeds` | §9.2.4.1: `SUPERUSER_PROFILES` equals the set of profiles the seeded world gives `is_superuser=True` |
| `test_the_apras_40_baseline_declares_its_provenance` | `set(meta) == META_KEYS`; `cell_count == APRAS_40_CELL_COUNT == 18`; `merge_base_sha` is 40 hex and appears in `regenerate`; `"--routes" in regenerate`; `"git worktree add" not in regenerate` (§9.2.2's stated difference, asserted rather than assumed); generator and harness paths exist |
| `test_the_apras_40_baseline_carries_no_absolute_path_and_no_timestamp` | §9.2.2's hygiene pair: `str(BACKEND_ROOT)` is absent from the raw text and no `\d{4}-\d{2}-\d{2}T\d{2}:\d{2}` matches — F2's case body with `BASELINE_40_PATH` |
| `test_the_apras_40_baseline_records_only_integer_status_codes` | idem: every recorded status `isinstance(..., int)`, over `load_apras_40_baseline()` |
| `test_the_two_baselines_partition_route_permissions_exactly` | coverage and no overlap, below |
| `test_the_recorder_refuses_to_write_the_frozen_f2_baseline` | §9.2.3's `FROZEN` guard, both branches |

```python
def test_the_two_baselines_partition_route_permissions_exactly():
    f2 = {(m, p) for _r, m, p in cells_of(load_baseline())}
    new = {(m, p) for _r, m, p in cells_of(load_apras_40_baseline())}
    assert new == APRAS_40_ROUTES
    assert not (f2 & new), "the two baselines must not overlap"
    assert f2 | new == set(ROUTE_PERMISSIONS)             # covers, exactly
    assert f2 == set(ROUTE_PERMISSIONS) - APRAS_40_ROUTES
    union = load_union()
    assert set(union) == set(CELLS)
    assert len(union) == EXPECTED_CELL_COUNT == len(CELLS)
```

`f2 | new == set(ROUTE_PERMISSIONS)` is exact rather than `⊆` because
`APRAS-49`'s three new F5 permissions are deliberately **not** in
`ROUTE_PERMISSIONS` (`APRAS-49` §3.0: in-code object predicates), so the map
stays at its base size plus this task's `+3` and nothing else creeps in.

`test_the_harness_is_shared_by_the_recorder_and_this_module` stays green and
unedited: the recorder still imports `CELLS`, `run_cell` and `seed_once` from
`matrix_world`, and `select_cells` filters that same list rather than building
a second one.

Finally, `tests/matrix_world.py`'s module docstring names the cell count
(`6 x 180 == 1080`) and the count of excluded unguarded routes; both move with
`len(ROUTE_PERMISSIONS)` and `len(UNGUARDED_ROUTES)`, alongside the write-route
count of §9.1. That docstring is prose about the *live* `CELLS`, not about the
frozen file, so editing it does not touch the F2 anchors.

### 9.3 The table partition — 50 → 53

`tests/test_tenant_models.py` reads the directly-scoped table list out of
migration `0028`'s frozen `_TENANT_SCOPED_TABLES` literal. `APRAS-40` is the
first task to add a directly-scoped table **after** `0028`, so the module
gains one constant and its docstring gains one paragraph:

```python
# Directly-scoped tables created after migration 0028, whose `tenant_id` is
# therefore absent from that migration's frozen `_TENANT_SCOPED_TABLES`
# literal. 0028 records history and must not be edited; new scoped tables
# register here. APRAS-40 is the first.
POST_0028_SCOPED_TABLES = {"tenant_subscription"}
```

| Group | Base | Delta | Final |
|---|---|---|---|
| directly scoped | 27 | +1 (`tenant_subscription`) | 28 |
| inherited | 20 | +1 (`subscription_change` → `tenant_subscription`) | 21 |
| unscoped | 3 | +1 (`plan`) | 4 |
| **total tables** | **50** | **+3** | **53** |

**Two cases union the constant, not one.** `test_partition_of_metadata_is_exhaustive`
unions `POST_0028_SCOPED_TABLES` into `scoped_tables` and asserts `== 53`;
and — the case it would be easy to miss —
`test_scoped_tables_have_a_not_null_tenant_id_fk` must iterate
`set(scoped_tables) | POST_0028_SCOPED_TABLES` too, or `tenant_subscription`
is the first directly-scoped table in the codebase whose `tenant_id` column
shape (NOT NULL, `server_default`, FK to `tenant.id`, `ix_tenant_subscription_tenant_id`)
is never checked by anything. `tenant_id_field()` supplies all four, so the
case passes as written once it sees the table — but it has to see it.

`test_scoped_tables_list_has_27_real_tables` stays at **27** and stays
unedited: it is an assertion *about migration 0028's frozen literal*, and 0028
is not amended (§7, and the Out of Scope list). `tenant_context.TENANT_SCOPED_MODELS`
grows 27 → 28 by derivation, with no code change; its module docstring's "27"
moves.

---

## 10. Tests

### 10.1 New backend test modules

**`backend/tests/test_plans_api.py`**

| Test | Asserts |
|---|---|
| `test_superuser_creates_and_lists_a_plan` | `POST /api/v1/plans/` → 201; `GET` lists it with sorted `included_modules` |
| `test_plan_rejects_an_unknown_module` | 400, detail names the string |
| `test_plan_rejects_a_core_module` | 400 for `billing`, `users`, `roles`, `tenants` |
| `test_plan_rejects_a_price_for_an_uncovered_module` | 400 `InvalidModulePriceError` |
| `test_duplicate_plan_name_is_409` | `PlanAlreadyExistsError` |
| `test_patch_deactivates_a_plan_and_there_is_no_delete_route` | `is_active` false; no `DELETE` in `ROUTE_PERMISSIONS` or the app's routes for `/api/v1/plans/{plan_id}` |
| `test_a_tenant_admin_and_an_ordinary_user_get_403_on_every_plan_route` | 403 `"The user doesn't have enough privileges"` × 4 routes × 2 actors |
| `test_unauthenticated_is_401` / `test_unknown_plan_is_404` | 401 / 404 |

**`backend/tests/test_subscription_api.py`** (tenant-side)

| Test | Asserts |
|---|---|
| `test_get_without_a_subscription_is_200_and_unmanaged` | `plan is None`, `len(body["modules"]) == len(MODULES)` (predicted 27), every active toggleable one `source == "UNMANAGED"`, every module `can_contract is False` (§4.6), `estimated_monthly_total is None` |
| `test_history_without_a_subscription_is_an_empty_list` | 200 `[]` |
| `test_put_modules_without_a_subscription_is_404` | detail `"This tenant has no subscription"` |
| `test_contracting_a_covered_module_activates_it` | 200; `tenant.disabled_modules` loses it; `GET /permissions/me` gains its permissions |
| `test_cancelling_a_module_deactivates_it` | the inverse; the module's endpoints 403 afterwards |
| `test_contracting_an_uncovered_module_is_400` | `ModuleNotEntitledError`, detail names it sorted; **the row is unchanged** |
| `test_core_modules_in_the_body_are_ignored` | sending `billing` in `active_modules` is a 200 no-op |
| `test_a_no_op_put_writes_no_history_row` | history length unchanged |
| `test_source_priority_is_plan_over_courtesy` | §4.7 |
| `test_contracting_a_module_raises_the_estimated_total` | delta == that module's `module_prices` entry |
| `test_a_courtesy_module_is_free` | courtesy module active, total unchanged (§6.4) |
| `test_the_three_tenant_routes_are_route_mapped` | the exact `ROUTE_PERMISSIONS` keys and values of §9.1 |

**`backend/tests/test_subscription_admin_api.py`** (superuser side)

| Test | Asserts |
|---|---|
| `test_assigning_a_plan_creates_the_subscription_and_applies_the_ceiling` | an all-on tenant keeps exactly the plan's modules; the rest land in `disabled_modules`; one `PLAN_CHANGE` row |
| `test_a_plan_change_that_widens_does_not_auto_activate` | modules entering the entitlement stay inactive, `can_contract: true` (§4.4 b) |
| `test_a_plan_change_that_narrows_deactivates` | modules leaving the entitlement are deactivated and named in `modules_removed` |
| `test_courtesy_grant_activates_a_module_outside_the_plan` | one call → `GET /tenants/{id}/modules` (APRAS-39) shows it active, `source == "COURTESY"` |
| `test_courtesy_revoke_deactivates_unless_the_plan_covers_it` | both branches |
| `test_courtesy_rejects_unknown_and_core_modules` | 400 each |
| `test_assigning_an_inactive_plan_is_400` | `InactivePlanError`; re-assigning the already-current inactive plan is allowed |
| `test_a_tenant_admin_gets_403_on_all_three_routes_including_own_tenant` | 403 × 3 |
| `test_unknown_tenant_is_404_and_a_missing_subscription_is_404_on_courtesy` | 404 / 404 |
| `test_the_subscription_of_one_tenant_is_written_and_the_other_is_untouched` | writing A leaves B's subscription and `disabled_modules` unchanged |

**`backend/tests/test_subscription_ceiling.py`** — §4, the composition

| Test | Asserts |
|---|---|
| `test_the_invariant_holds_after_every_apras_40_write` | §4.5's I1 for all three paths, I2 after the plan change, I3 after the tenant-side write — one assertion each, `over(t)` computed before and after |
| `test_a_module_outside_the_plan_cannot_be_activated_by_a_tenant_admin` | 400, and the module stays inactive and 403 at its endpoint |
| `test_a_module_outside_the_plan_cannot_be_activated_by_a_billing_manage_holder` | the same for a non-admin role granted `billing:manage` (the "DIRECTOR" case) |
| `test_a_tenant_side_write_preserves_courtesy_and_override_activations` | §4.4 (a) step 5: a `PUT` whose body omits a courtesy module and an override module leaves **both** active, and appends a `CONTRACTED` row naming neither |
| `test_included_modules_has_at_most_four_homes` | §6.3's AST pin, an **upper bound** over attribute accesses *and* field declarations; `build_read` is not one of them, and in `subscription_service.py` every occurrence is inside `entitlement`'s body |
| `test_build_read_derives_everything_from_the_entitlement_result` | §6.3: `build_read` calls `entitlement` exactly once and its body has **no `session.` access of any kind, no `select(`, no reference to `Plan` / `TenantSubscription` / `SubscriptionChange`**, no `.included_modules`, no `.courtesy_modules` |
| `test_entitlement_is_the_only_loader_and_costs_one_query` | `entitlement` joins `TenantSubscription` and `Plan` in one statement; `ent.plan is None` iff `ent.subscription is None` (§6.3's `__post_init__`); a `GET /api/v1/subscription` on a managed tenant issues exactly one subscription/plan query (counted with a SQLAlchemy `before_cursor_execute` listener) |
| `test_the_superuser_raw_switch_is_not_constrained_by_the_ceiling` | `PUT /tenants/{id}/modules` activates an uncovered module → 200, module active, `source == "OVERRIDE"` |
| `test_the_raw_switch_records_an_override_history_row` | §4.5's appended block; kind `OVERRIDE`, actor recorded, `modules_added` = what left `disabled_modules` |
| `test_status_does_not_change_the_entitlement` | §4.3, three statuses, identical `/permissions/me` |
| `test_billing_is_core_and_cannot_be_disabled` | `PUT /tenants/{id}/modules {"disabled_modules":["billing"]}` → 400; a hand-written row containing `"billing"` still yields `billing:*` |
| `test_the_resolver_is_untouched` | source scan: `git diff` touches no line of `deps.get_effective_permissions` / `deps.disabled_modules` / `permissions.filter_by_modules`, and `entitlement` is referenced only inside `subscription_service.py` |
| `test_entitlement_isolation_between_tenants` | one user in A (plan without `finance`) and B (plan with it): 403 with `X-Tenant-Id: A`, 200 with B, nothing else differing |

**`backend/tests/test_subscription_history.py`**

| Test | Asserts |
|---|---|
| `test_every_write_path_appends_exactly_one_kind` | the five kinds, one operation each |
| `test_history_is_ordered_newest_first_and_names_the_actor` | `changed_at DESC`, `changed_by_name` resolved |
| `test_the_history_is_never_updated_or_deleted` | the source scan of §3.3; and no route exists that mutates a `subscription_change` row |
| `test_a_tenant_only_sees_its_own_history` | the acting-tenant filter; A's history has zero rows from B |
| `test_plan_change_records_both_plan_ids` | `from_plan_id` / `to_plan_id` |

**`backend/tests/test_subscription_access.py`**

| Test | Asserts |
|---|---|
| `test_no_role_row_holds_billing_permissions_on_a_fresh_install` | §2.3: `billing:read` / `billing:manage` in no role's bundle in any tenant, and absent from `tests/data/legacy_role_bundles.json` |
| `test_a_tenant_admin_reaches_the_area_with_no_special_case` | 200 on all three tenant routes with only `is_tenant_admin` |
| `test_a_director_reaches_the_area_once_the_role_grants_it` | 403 before the grant, 200 after ticking `billing:read`/`billing:manage` on the role |
| `test_billing_read_alone_cannot_contract` | 403 on `PUT /subscription/modules` |
| `test_a_superuser_reaches_everything` | all ten routes |

**`backend/tests/test_migrations_postgres.py`** — one new `0035` section
(see §10.2).

### 10.2 Pre-existing test modules that legitimately change

Named exhaustively, with what must **not** change:

| Module | Change | Must not change |
|---|---|---|
| `tests/test_module_vocabulary.py` (APRAS-39) | `len(MODULES)` 26 → **27**; `test_core_modules_are_three_and_real` → `..._are_four_and_real` with `CORE_MODULES == {"tenants","users","roles","billing"}`; `len(PERMISSIONS)` 159 → **161** in `test_every_permission_belongs_to_a_declared_module` | `len(TOGGLEABLE_MODULES) == 23`; the partition/disjointness assertions; `filter_by_modules`'s cases |
| `tests/test_tenant_modules_api.py` (APRAS-39) | `test_get_lists_every_module_with_its_state` 26 → **27** rows, `is_core` true for **four**; `test_put_rejects_a_core_module` iterates **four**; `test_a_new_tenant_starts_with_every_module_active` 26 → 27. **Nothing for §4.5's `actor`**: the handler passes `current_user` and the fixtures have no subscription row | every status code, every 403/401/404 case, the declarative/dedup cases |
| any direct caller of `TenantService.set_modules` | the new required keyword-only `actor=` argument (§4.5). `grep -rn 'set_modules(' backend/app backend/tests` at the merge base enumerates every call site; the handler is one of them and each other is a one-argument edit | the assertions themselves; no status code, no response body |
| `tests/test_permission_registry.py` | `len(UNGUARDED_ROUTES)` base+7 and the case-name literal; total routes base+10; `len(ROUTE_PERMISSIONS)` base+3; the docstring's `195/180/15` triple | every other entry and every other case |
| `tests/test_permission_parity_matrix.py` | §9.2.5 in full: `BASELINE_40_PATH`, `F2_CELL_COUNT`/`APRAS_40_CELL_COUNT`/`EXPECTED_CELL_COUNT = 1080 + 18`, `APRAS_40_ROUTES`, `SUPERUSER_PROFILES`, `MATRIX_ADMIN_GAP`, `load_file()`/`load_apras_40_baseline()`/`cells_of()`/`load_union()` (all applying `F5_PATH_RENAMES`), `baseline_status`'s first argument, the **nine** named `load_union()` call sites, **four** further named case edits (including `test_the_recorder_has_no_allow_dirty_escape`'s flag set, §9.2.3), **§9.2.4.1's `holds()` split and superuser branch**, **ten** new cases (§9.2.5), `EXPECTED_REQUEST_BODY_COUNT` 89 → **90**, the unguarded-count case name and literal | `tests/data/parity_matrix_baseline.json` itself (byte-identical, sha256-pinned); `load_baseline()`'s **name and meaning** (the F2 file — only its body becomes `return load_file(BASELINE_PATH)`), and its three surviving existing call sites `test_baseline_file_exists` / `test_baseline_declares_its_provenance` / `test_baseline_records_only_integer_status_codes` (the new `test_the_two_baselines_partition_route_permissions_exactly` is a fourth); the **contents and sizes** of `DENIAL_SHAPE_OVERRIDES`, `NON_ROLE_403` and `PERMITTED_422`, and the six cases that read none of the baselines — `test_denial_shape_overrides_is_exactly_six`, `test_non_role_403_is_bounded`, `test_permitted_422_is_bounded` and the three `..._has_a_reason` cases — **green and wholly unedited**. Note what is deliberately **not** claimed here: the six `holds()` callers (`test_every_denied_cell_is_denied_in_the_baseline`, `test_every_denial_shape_override_is_needed`, `test_no_permitted_cell_is_403_in_the_baseline`, `test_every_non_role_403_is_needed`, `test_no_permitted_cell_is_422_in_the_baseline`, `test_every_permitted_422_is_needed`) are all among §9.2.5's nine and each changes in **exactly one line** — `load_baseline()` → `load_union()`. What must not change in them is everything else: every assertion, every `holds()` call and argument, and the collection each iterates. Also unedited: `test_baseline_carries_no_absolute_path_and_no_timestamp`; `test_the_harness_is_shared_by_the_recorder_and_this_module`; `test_no_absolute_datetime_in_the_harness`; `test_the_matrix_module_never_skips`; `test_the_matrix_world_runs_with_every_module_active` (APRAS-39 §9) — this task adds no `disabled_modules` to the world |
| `tests/matrix_world.py` | one `REQUEST_BODIES` entry (§9.1); the module docstring's write-route count 89 → **90**, its cell count `6 x 180 == 1080` and its excluded-unguarded-route count | `PARITY_PROFILES`, `CELLS`'s derivation, `_seed_world`, `run_cell`, the bundle source, every other body spec |
| `tests/tools/record_parity_baseline.py` | §9.2.3: `--routes`, `--merge-base`, `select_cells()`, `record()`'s two new parameters, the `FROZEN` guard | `assert_clean_production_tree` and its exit code; `head_sha`; `serialise`; `GENERATOR`/`HARNESS`/`REGENERATE`; the absence of any `--allow-dirty` |
| `tests/data/parity_matrix_baseline.json` | **none — frozen.** It must not appear in `git diff --name-only <merge-base>..HEAD` | every byte, `_meta.merge_base_sha`, `_meta.regenerate`, all 1080 cells |
| `tests/test_legacy_role_permissions.py` | **none** — its `02c2025…` prose anchor stays true because §9.2.1 freezes the file | the module docstring, verbatim |
| `tests/test_tenant_route_scope.py` | `GLOBAL_ROUTES` gains the seven, with comments | its computed accounting test |
| `tests/test_permission_enforcement.py` | `ADMIN_ONLY_ROUTES` +7 and the exact-set case rename | the `ROUTE_PERMISSIONS_*` allowlists, `GLOBAL_PREFIXES`/`GLOBAL_EXTRA`, every other case |
| `tests/test_tenant_admin.py` | the **independent duplicate** of `ADMIN_ONLY_ROUTES`, +7, and the identical rename. Both copies move or the suite is red | `test_no_tenant_scoped_route_keeps_a_global_admin_guard` — green unchanged (§9.1) |
| `tests/test_tenant_models.py` | `POST_0028_SCOPED_TABLES` (§9.3), `INHERITED_TABLES["subscription_change"] = "tenant_subscription"`, `UNSCOPED_TABLES |= {"plan"}`, `50 → 53` in `test_partition_of_metadata_is_exhaustive`, **and the same union in `test_scoped_tables_have_a_not_null_tenant_id_fk`** (§9.3), plus the docstring paragraph explaining why `0028`'s literal is not edited | the 0028 literal itself; `test_scoped_tables_list_has_27_real_tables` (still **27**); every other classification |
| `tests/test_permissions_api.py` (APRAS-48) | any catalogue-size assertion 159 → **161** | the `/permissions/me` cases, `disabled_modules` |
| `tests/test_role_rename.py` (APRAS-49) | `the catalogue has 159 permissions in 26 modules` → **161** in **27** | every rename assertion |
| `tests/test_migrations_postgres.py` | head literal `"0034_add_tenant_modules"` → `"0035_add_subscription_tables"` wherever the module pins the head; a new `0035` section: the three tables exist with their constraints, `plan` and `tenant_subscription` are **empty** after upgrade (no seeding), `downgrade -1` drops all three and a re-`upgrade` succeeds | every earlier revision's assertions |
| `tests/test_effective_permissions.py` | **none expected** — `billing` is core and every existing fixture has no subscription | every existing assertion |
| `tests/test_module_gating.py`, `tests/test_module_gating_grants.py` (APRAS-39) | **none** — those fixtures have no subscription row, so `set_modules`' appended block (§4.5) short-circuits on `subscription is None` | every assertion, verbatim |

If a module in the "none" rows does move, that is a signal the composition is
wrong; investigate before editing it.

### 10.3 Frontend tests

| File | Cases |
|---|---|
| `SubscriptionPage.test.tsx` (**new**) | renders the plan card and the grouped module list; **one case per §8.4 row state** — a rule-4 out-of-plan module has no checkbox and the "fora do plano" hint, a rule-2 courtesy module has no checkbox, the "cortesia" badge and "gratuito" in place of a price, a rule-1 override module has no checkbox and the override badge, a rule-3 in-plan module has an enabled checkbox; `test_the_payload_carries_only_the_contracted_set` — with one checked in-plan module, one active courtesy module and one active override module in the fixture, Save `PUT`s `{"active_modules": ["<the in-plan one>"]}` and **nothing else**; a module in both plan and courtesy (`source === "PLAN"`) renders as a rule-3 checkbox and *is* in the payload; a 400 renders `subscription.notEntitled`; the no-subscription state renders every module read-only and disables Save; the history table renders one row per kind |
| `PlansAdminPage.test.tsx` (**new**) | create/edit round trip; the module checklist excludes core modules; a 400 on an uncovered price renders the error |
| `TenantSubscriptionsPage.test.tsx` (**new**) | tenant `<select>` refetches; assigning a plan `PUT`s; granting courtesy `PUT`s with the reason; the history renders |
| `useSubscription.test.ts` (**new**) | `["subscription"]` is reset and `["tenants",id,"subscription"]` preserved by `setActingTenant`; each of the three mutations invalidates `["me","permissions"]` (§8.2) |
| `useCanAccess.superuser.test.tsx` (APRAS-39) | one case per new `{superuser:true}` route |
| the `routeAccess` / `NAV_ITEMS` parity test (F4 name) | the three new entries; every nav item's access is its route's rule |
| `Navbar` test (F4 name) | the `/subscription` link appears for a `billing:read` holder and is absent otherwise |
| `src/i18n/__tests__/index.test.ts` | `modules.names` 26 → **27**; the en/pt key-set parity case stays green |

Every test that mounts a component reading `useSubscription` or
`useMyPermissions` provides a `QueryClientProvider` with a payload carrying
the new fields (F4 §8.2's rule).

---

## 11. `AGENTS.md`

* A new **Assinatura e planos** subsection under *Domain Concepts*, after
  *Módulos por tenant*: the three tables; the global plan catalogue and why
  it is not per-tenant; **the one rule of §4.1 quoted verbatim**, including
  that `tenant.disabled_modules` stays the single read-time authority and
  that the resolver is untouched; the four levers table of §4.2; the six
  `source` values of §4.7; the no-subscription semantics of §4.6; `billing`
  as the fourth core module and why; and, in bold, **prices are inert and
  nothing is charged — no payment provider exists**.
* One amendment to `APRAS-39`'s *Módulos por tenant* subsection: `CORE_MODULES`
  is four, `MODULES` is 27, and the superuser `PUT` is now one of **three**
  writers of `disabled_modules` (pointing at the new subsection).
* The endpoint table gains `/api/v1/plans` and `/api/v1/subscription`, and
  the three `/api/v1/tenants/{tenant_id}/subscription*` rows.
* One `curl` per surface: a tenant contracting a module, a superuser
  assigning a plan, a superuser granting courtesy.

---

## 12. Gates, baselines and the PR body

| Metric | Gate | Requirement |
|---|---|---|
| `pytest` (backend) | `--cov-fail-under=90` | green, ≥ 90 **and** ≥ the merge-base measurement |
| `npm run test` | — | all pass; the PR body says how file/test counts moved |
| Vitest statements / branches / functions / lines | 80 / 76 / 78 / 80 | ≥ gate **and** ≥ the merge-base measurement for each |
| `npm run lint` | — | ≤ the merge-base problem count; **0** new findings in non-test `src/**` |
| `npm run build` | — | passes (`tsc -b` included) |
| `ruff check backend` | — | **0** new findings |
| `alembic heads` | — | exactly one: `0035_add_subscription_tables` |
| dependency manifests | pinned | `backend/pyproject.toml` and `frontend/package.json` **absent** from `git diff --stat` |
| provider grep | pinned | `grep -rniE "stripe|pagarme|pagar\.me|mercadopago|iugu|asaas|paypal|payment_gateway|checkout_session" backend/app frontend/src` returns **nothing** — byte-identical to ER-8's command, run and pasted as-is |
| `len(PERMISSIONS)` / `ROUTE_PERMISSIONS` / `UNGUARDED_ROUTES` / total routes / `GLOBAL_ROUTES` / `ADMIN_ONLY_ROUTES` ×2 | pinned | base **+2 / +3 / +7 / +10 / +7 / +7 / +7** |
| `len(REQUEST_BODIES)` / `EXPECTED_REQUEST_BODY_COUNT` | pinned | base **+1** each (predicted 89 → 90), with `matrix_world.py`'s docstring moved to match |
| `tests/data/parity_matrix_baseline.json` | **frozen** | absent from `git diff --name-only <merge-base>..HEAD`; sha256 unchanged and quoted base-beside-final; `_meta.merge_base_sha` still `02c2025…`; `_meta.cell_count` still 1080 |
| `tests/data/parity_matrix_baseline_40.json` | pinned | **new**, 18 cells, five `_meta` keys, produced by one scoped recorder run (§9.2.3) whose exact command line is quoted in the PR body; its 18 statuses equal §9.2.4's prediction |
| the two baselines together | pinned | disjoint, and their route keys union to `set(ROUTE_PERMISSIONS)` exactly; `EXPECTED_CELL_COUNT == 1080 + 18 == len(CELLS) == len(load_union())`, with `APRAS-49`'s `F5_PATH_RENAMES` applied so `set(load_union()) == set(CELLS)` |
| the nine `load_union()` call sites | pinned | `grep -n 'load_baseline()' backend/tests/test_permission_parity_matrix.py` returns **exactly five** hits — the `def` line, `test_baseline_file_exists`, `test_baseline_declares_its_provenance`, `test_baseline_records_only_integer_status_codes` and the new `test_the_two_baselines_partition_route_permissions_exactly` — against thirteen (`def` + twelve call sites) at the merge base; both greps pasted in the PR body |
| the `holds()` oracle (§9.2.4.1) | pinned | gains the superuser branch and is **inert on all 1080 F2 cells** (`test_the_superuser_branch_changes_no_f2_verdict` green); `DENIAL_SHAPE_OVERRIDES` still `len == 6` with `{"GUEST"}`, `NON_ROLE_403` and `PERMITTED_422` unchanged entry for entry; the ADMINISTRATOR bundle-gap measurement re-run at the merge base and pasted |
| table partition | pinned | base **+3** (28 / 21 / 4 = 53) |

**The PR body must carry:** the measured merge-base value beside the final
value for every row above; `alembic heads`; a real `upgrade head` /
`downgrade -1` / `upgrade head` cycle against the throwaway Postgres on
**5436** (never `nexdom`) with the three `\d` listings and the
`pg_constraint` listing; the **two** baseline proofs — `git diff --name-only
<merge-base>..HEAD` showing `parity_matrix_baseline.json` **absent**, with its
sha256 before and after, and the scoped recorder's exact command line and its
18 recorded statuses beside §9.2.4's predicted table; the two greps (provider
names, dependency manifests); §4.1's
rule restated in one line; §2.3's "no role holds `billing:*` on a fresh
install" restated in one line; the i18n parity output with the measured
en/pt leaf count; and any name deviation from the 47/48/49/39 contracts.

---

## Expected Results

- [ ] **ER-1 — a plan governs what a tenant may activate.** `Plan` (global,
  superuser-managed via four `/api/v1/plans` routes) and `TenantSubscription`
  (at most one per tenant, `uq_tenant_subscription_tenant`) exist.
  `PUT /api/v1/tenants/{tenant_id}/subscription {"plan_id": …}` as a
  superuser returns **200** and, for a tenant that was all-on, leaves exactly
  the plan's `included_modules` active: `GET /api/v1/tenants/{tenant_id}/modules`
  (APRAS-39) reports every uncovered toggleable module `is_active: false` and
  `tenant.disabled_modules == sorted(TOGGLEABLE_MODULES - plan.included_modules)`.
  A tenant with **no** subscription answers `GET /api/v1/subscription` with
  **200**, `plan: null`, **one module row per `MODULES` entry**
  (`len(body["modules"]) == len(app.core.permissions.MODULES)`, predicted 27 —
  the derived expression is the assertion, the number is the prediction),
  every active toggleable one `source: "UNMANAGED"` and every one
  `can_contract: false` (the contracting `PUT` is a 404 there, §4.6) — i.e.
  today's all-on behaviour is preserved and adopting billing is opt-in. Pinned
  by `tests/test_subscription_admin_api.py` and `tests/test_subscription_api.py`.

- [ ] **ER-2 — tenant-side actors contract and cancel within the plan, and
  what is charged moves with them.** `GET /api/v1/subscription`,
  `PUT /api/v1/subscription/modules` and `GET /api/v1/subscription/history`
  exist, take **no** `{tenant_id}` path parameter (they act on the
  `X-Tenant-Id` tenant), and are guarded by
  `require_permission("billing:read" / "billing:manage")` against the new
  catalogue strings. A user holding `is_tenant_admin` on the acting tenant
  reaches all three with **no special case in the code** (APRAS-47's
  whole-catalogue short-circuit, `billing` being core), and a
  "Diretor"-profile user reaches them **exactly when the condominium's role
  row carries the two permissions** — asserted 403-before / 200-after in
  `test_subscription_access.py::test_a_director_reaches_the_area_once_the_role_grants_it`.
  `PUT {"active_modules": [... + "finance"]}` returns 200, `finance` becomes
  active, `GET /api/v1/permissions/me` gains the 11 `finance:*` strings, and
  `estimated_monthly_total` rises by exactly `plan.module_prices["finance"]`;
  removing it reverses all three. A no-op `PUT` is a 200 that appends **no**
  history row. The body is **the contracted set only**: with a courtesy module
  and an `OVERRIDE` module also active, a `PUT` that names neither leaves both
  active (`test_subscription_ceiling.py::test_a_tenant_side_write_preserves_courtesy_and_override_activations`),
  and `SubscriptionPage.test.tsx::test_the_payload_carries_only_the_contracted_set`
  asserts the frontend sends exactly the checked plan-covered modules.

- [ ] **ER-3 — a module outside the subscription cannot be activated from
  inside the tenant.** `PUT /api/v1/subscription/modules` naming a module not
  in `plan.included_modules ∪ subscription.courtesy_modules` returns **400**
  with detail `"Modules not covered by the subscription: <sorted names>"` and
  leaves `tenant.disabled_modules` **byte-identical** — for a tenant_admin
  and for a plain `billing:manage` holder alike. `PUT` with no subscription
  row returns **404** `"This tenant has no subscription"`. Unknown module
  strings return 400; core modules in `active_modules` are a silent no-op.
  Pinned by `tests/test_subscription_ceiling.py`.

- [ ] **ER-4 — the superuser overrides the plan, and the override is
  distinguishable three ways.** `PUT /api/v1/tenants/{tenant_id}/subscription/courtesy
  {"courtesy_modules": ["finance"], "reason": "negociação"}` returns **200**
  and, in one call, activates `finance` outside the plan: `GET
  /api/v1/tenants/{tenant_id}/modules` shows it `is_active: true`. It is
  distinguishable from a contracted activation by (a) `source: "COURTESY"` in
  `GET /api/v1/subscription` — never `"PLAN"`, per §4.7's priority; (b) a
  `SubscriptionChange` row with `kind: "COURTESY_GRANT"`, its `reason` and
  its author; and (c) `estimated_monthly_total`, which does **not** move,
  because courtesy is free. Revoking it deactivates the module unless the
  plan covers it. APRAS-39's raw `PUT /api/v1/tenants/{tenant_id}/modules`
  survives unchanged, is **not** bounded by the plan, and any module it
  activates outside the entitlement reads `source: "OVERRIDE"` and appends a
  `kind: "OVERRIDE"` history row. All three superuser subscription routes
  answer **403** for a tenant_admin — including of that very tenant — **401**
  unauthenticated and **404** for an unknown tenant.

- [ ] **ER-5 — the area shows current state and the full change history.**
  `GET /api/v1/subscription` returns `{plan, status, started_at, notes,
  modules, estimated_monthly_total, currency}`, where `modules` has
  **`len(app.core.permissions.MODULES)` entries** (predicted 27), one per
  catalogue module, sorted by `module`, each carrying
  `{is_core, is_active, in_plan, courtesy, can_contract, monthly_price,
  source}` — and `can_contract` is `false` for every module of a tenant with
  no subscription, because that tenant's contracting `PUT` is a 404 (§4.6). `GET /api/v1/subscription/history` returns the tenant's
  `SubscriptionChange` rows newest-first, each with `kind` ∈
  `{CONTRACTED, PLAN_CHANGE, COURTESY_GRANT, COURTESY_REVOKE, OVERRIDE}`,
  the modules added/removed, both plan ids on a plan change, the reason and
  the author's name — and **only** that tenant's rows. The history is
  append-only: no route updates or deletes a `subscription_change` row, and
  `tests/test_subscription_history.py::test_the_history_is_never_updated_or_deleted`
  proves `SubscriptionChange` is never passed to `session.delete` anywhere in
  `backend/app/**`. Vitest: `SubscriptionPage.test.tsx` renders the plan card,
  one history row per kind, and the module list in **exactly four mutually
  exclusive row states, resolved by the stated precedence
  `OVERRIDE > COURTESY > PLAN > out-of-plan`** (§8.4): an `OVERRIDE` row and a
  courtesy row carry a badge and **no checkbox**, an out-of-plan row carries
  the "fora do plano" hint and no checkbox, and only an `in_plan` row is a
  checkbox — one named case per state.

- [ ] **ER-6 — one rule composes with APRAS-39, and the resolver is
  untouched.** `git diff` touches **no line** of
  `deps.get_effective_permissions`, `deps.disabled_modules` or
  `permissions.filter_by_modules`; `tenant.disabled_modules` remains the only
  input to permission resolution. With
  `over(t) := (active(t) & TOGGLEABLE_MODULES) - entitlement(t).all`, §4.5's
  three-part invariant holds and is asserted per part per path: **I1** no
  APRAS-40 write escalates (`over(t)` never grows, all three paths), **I2**
  the plan-change path leaves `over(t) == ∅`, **I3** the tenant-side path
  leaves `over(t)` unchanged. `SubscriptionService.entitlement` is the **single
  loader**: one query joining `TenantSubscription` and `Plan` (no
  `Relationship` on the model), returning the frozen
  `Entitlement(subscription, plan, included, courtesy)` with `.managed` and
  `.all` as properties, `.all` being the single ceiling and `plan is None` iff
  `subscription is None`. `build_read` derives **everything it returns** —
  `plan`, `status`, `started_at`, `notes`, `currency`, and per module
  `in_plan` / `courtesy` / `can_contract` / `source` / `monthly_price`, plus
  `estimated_monthly_total` — from that result alone, and its body touches the
  session not at all: `test_build_read_derives_everything_from_the_entitlement_result`
  asserts (AST-scoped to the function) no `session.` access of any kind, no
  `select(`, no reference to `Plan` / `TenantSubscription` /
  `SubscriptionChange`, and no `.included_modules` / `.courtesy_modules`, with
  exactly one call to `entitlement`; `test_included_modules_has_at_most_four_homes`
  asserts (over AST attribute accesses **and** field declarations) that the
  name `included_modules` occurs in `backend/app/**` in **at most** the four
  declared places — `models/plan.py`, `schemas/plan.py`,
  `services/plan_service.py` and, inside `services/subscription_service.py`,
  only within `entitlement`'s body — and in none of them is `build_read`.
  `billing` is the **fourth** core
  module: `CORE_MODULES == {"tenants","users","roles","billing"}`,
  `len(MODULES) == 27`, `len(TOGGLEABLE_MODULES) == 23` (unchanged),
  `PUT /api/v1/tenants/{id}/modules {"disabled_modules":["billing"]}` → 400,
  and a hand-written row containing `"billing"` still yields every
  `billing:*`. `subscription.status` gates nothing: the same tenant's
  `/permissions/me` is byte-identical under `ACTIVE`, `SUSPENDED` and
  `CANCELED`. Entitlement is isolated per tenant: one user in A (plan without
  `finance`) and B (plan with it) gets 403 with `X-Tenant-Id: A` and 200 with
  `X-Tenant-Id: B`, nothing else differing.

- [ ] **ER-7 — one reversible migration, no seeded plan.** `alembic heads`
  reports exactly one head, `0035_add_subscription_tables`. Against a real
  throwaway Postgres on port **5436** (never `nexdom`), `upgrade head`
  creates `plan`, `tenant_subscription` and `subscription_change` with the
  declared constraints (`uq_tenant_subscription_tenant`, `plan_id` and
  `tenant_id` `ON DELETE RESTRICT`, `subscription_id` `ON DELETE CASCADE`),
  **both `plan` and `tenant_subscription` are empty afterwards** (no-seeds
  doctrine — a fresh install has no plans, so every tenant keeps APRAS-39's
  all-on default), `downgrade -1` drops all three and a re-`upgrade`
  succeeds. No data statement in either direction. `tests/test_tenant_models.py`
  classifies the three new tables — `tenant_subscription` directly scoped via
  the new `POST_0028_SCOPED_TABLES` constant, `subscription_change` inherited
  from it, `plan` unscoped — with **both**
  `test_partition_of_metadata_is_exhaustive` (**53** tables, base + 3) and
  `test_scoped_tables_have_a_not_null_tenant_id_fk` iterating
  `scoped_tables | POST_0028_SCOPED_TABLES`, so `tenant_subscription.tenant_id`
  is shape-checked (NOT NULL, `server_default`, FK to `tenant.id`,
  `ix_tenant_subscription_tenant_id`); and without editing migration `0028`'s
  frozen literal, `test_scoped_tables_list_has_27_real_tables` staying at 27.

- [ ] **ER-8 — no payment provider, and it is provable.** `git diff --stat`
  shows **no** change to `backend/pyproject.toml` or `frontend/package.json`;
  `grep -rniE "stripe|pagarme|pagar\.me|mercadopago|iugu|asaas|paypal|payment_gateway|checkout_session" backend/app frontend/src`
  returns **nothing**; no code in `backend/app/**` makes an outbound HTTP
  call for billing. Every price field is inert: `base_price`,
  `module_prices`, `currency` and `estimated_monthly_total` are stored,
  returned and summed for display only, and the tenant-side page renders an
  explicit "valores informativos — nenhuma cobrança é feita" notice in both
  languages. Charging, invoices, proration, dunning, trials and tenant-
  initiated plan changes are out of scope and named as such in
  `AGENTS.md` — a follow-up task wires a provider once an account exists
  (same blocker class as `APRAS-13`).

- [ ] **ER-9 — the accounting moves by exactly the declared deltas, and every
  superuser route declares a real guard.** (The F2 baseline freeze is ER-10's,
  not this one's.) Measured at the actual merge base and
  quoted base-beside-final in the PR body: `len(PERMISSIONS)` **+2**,
  `len(ROUTE_PERMISSIONS)` **+3**, `len(UNGUARDED_ROUTES)` **+7**, total
  routes **+10**, `len(GLOBAL_ROUTES)` **+7**, `ADMIN_ONLY_ROUTES` **+7** in
  **both** independent copies (`tests/test_permission_enforcement.py` and
  `tests/test_tenant_admin.py`), and `len(REQUEST_BODIES)` /
  `EXPECTED_REQUEST_BODY_COUNT` **+1** each (predicted 89 → **90**) with
  `tests/matrix_world.py`'s docstring write-route count moved to match — each
  exact-set case renamed to its new count, and every one of the seven
  superuser routes satisfying its pin by **declaring
  `Depends(api_deps.get_current_superuser)`**; an inlined
  `if not user.is_superuser` that keeps the pins from moving is a rejection,
  not an implementation.
  `test_tenant_admin.py::test_no_tenant_scoped_route_keeps_a_global_admin_guard`
  stays green.

- [ ] **ER-10 — the F2 baseline is byte-identical and the 18 new cells live
  in a second file.** `git diff --name-only <merge-base>..HEAD` does **not**
  contain `backend/tests/data/parity_matrix_baseline.json`; its sha256 is
  quoted before and after and is the same string;
  `test_the_f2_baseline_is_untouched_by_apras_40` pins that sha256 plus
  `_meta.merge_base_sha == "02c2025abcda4626569921eafb3863dfc540eb9e"`,
  `_meta.cell_count == 1080` and `"git worktree add" in _meta.regenerate`; and
  `test_the_f2_sha_anchors_still_agree_with_the_frozen_file` proves that sha
  still appears verbatim in `tests/test_legacy_role_permissions.py` and
  `tests/test_permission_enforcement.py`, neither of which this task edits.
  The 18 new cells (6 profiles × 3 billing routes) are in the **new**
  `backend/tests/data/parity_matrix_baseline_40.json`, with its own `_meta`
  carrying the same five keys, `cell_count: 18`, its own `merge_base_sha` (the
  `APRAS-39` merge base) and its own `regenerate` — the literal scoped
  recorder invocation, which contains `--routes` and **no** `git worktree add`
  — produced by exactly one run of
  `python -m tests.tools.record_parity_baseline --out tests/data/parity_matrix_baseline_40.json --merge-base <sha> --routes 'GET /api/v1/subscription' --routes 'GET /api/v1/subscription/history' --routes 'PUT /api/v1/subscription/modules'`
  issued **after `backend/app/` was committed** (the recorder exits 2 on a
  dirty `app/`), with the command line and its 18 recorded statuses pasted in
  the PR body. The recorder declares exactly
  `{"--out", "--overwrite", "--routes", "--merge-base"}`, still has no
  `--allow-dirty`, and refuses with exit 2 to write the frozen F2 path at all
  (`test_the_recorder_refuses_to_write_the_frozen_f2_baseline`).
  `test_the_two_baselines_partition_route_permissions_exactly` asserts the two
  files are **disjoint** and that their route keys union to
  `set(ROUTE_PERMISSIONS)` **exactly**, with
  `EXPECTED_CELL_COUNT == 1080 + 18 == len(CELLS) == len(load_union())`; the
  union loader keys both files the way `CELLS` is keyed, applying `APRAS-49`'s
  `F5_PATH_RENAMES`, and the additive file carries hygiene checks of its own —
  `test_the_apras_40_baseline_carries_no_absolute_path_and_no_timestamp` and
  `test_the_apras_40_baseline_records_only_integer_status_codes`, the F2 pair's
  bodies over `BASELINE_40_PATH`, with the F2 pair itself unedited. The
  18 recorded values equal §9.2.4's prediction — 403 on all three routes for
  the five non-`ADMINISTRATOR` profiles, and 200 / 200 / **404** (never 422)
  for `ADMINISTRATOR`. Those three `ADMINISTRATOR` cells are reconciled with the
  matrix's semantic oracle by **extending the predicate, not the exception
  tables** (§9.2.4.1): `holds()` splits into **three** functions —
  `bundle()` (the recorded legacy bundle of a profile, the seam `APRAS-49` §11.1
  re-sources), `holds_by_bundle()` (the F2 predicate, verbatim, over `bundle()`)
  and `holds()` = "a `SUPERUSER_PROFILES` profile holds every catalogue
  permission outside `MATRIX_ADMIN_GAP`, else `holds_by_bundle()` decides". The
  extension is proven inert on the recorded matrix:
  `test_the_superuser_branch_changes_no_f2_verdict` asserts `holds` and
  `holds_by_bundle` agree on **every** cell outside the three new routes, so all
  **1080** F2 verdicts are unchanged, and
  `test_the_admin_gap_is_the_only_bundle_gap_the_superuser_branch_excludes`
  asserts `GET /api/v1/packages/my-lots` (`packages:my_lots_read`, recorded 403)
  is the only mapped route `ADMINISTRATOR`'s bundle misses and that its
  permission equals `MATRIX_ADMIN_GAP & set(ROUTE_PERMISSIONS.values())` — the
  single cell the gap clause exists for, whose measurement is re-run at the
  merge base and pasted in the PR body.
  `test_the_superuser_profiles_are_the_ones_the_world_seeds`
  reads `SUPERUSER_PROFILES` back off the seeded world. **No
  `DENIAL_SHAPE_OVERRIDES`, `NON_ROLE_403` or `PERMITTED_422` entry is added or
  removed**, all three keep their current size and contents, and
  `test_denial_shape_overrides_is_exactly_six` (`len == 6`, roles `== {"GUEST"}`),
  `test_non_role_403_is_bounded`, `test_permitted_422_is_bounded` and the three
  `..._has_a_reason` cases stay green **wholly unedited** — they read no
  baseline, so §9.2.5's loader switch does not reach them.
  The six `holds()` callers are **not** in that group and are **not** claimed
  unedited: each is one of §9.2.5's nine `load_union()` call sites, so each
  changes in **exactly one line** — `baseline = load_baseline()` becomes
  `baseline = load_union()` — and in no other line: every assertion, every
  `holds()` call and argument, and the collection each iterates are
  byte-identical. Three of them
  (`test_every_denied_cell_is_denied_in_the_baseline`,
  `test_no_permitted_cell_is_403_in_the_baseline`,
  `test_no_permitted_cell_is_422_in_the_baseline`) iterate `CELLS` and would
  `KeyError` on the 18 new cells without the switch; the other three
  (`test_every_denial_shape_override_is_needed`,
  `test_every_non_role_403_is_needed`, `test_every_permitted_422_is_needed`)
  iterate their own dicts, whose keys are all recorded F2 cells, and would stay
  green on `load_baseline()` — they switch for uniformity, so that every
  semantic oracle in the module reads one map. A diff showing those six bodies
  otherwise modified, or showing any of the nine still on `load_baseline()`, is
  a fail.

- [ ] **ER-11 — gates green and pt/en at parity.** `pytest` ≥ 90 % and ≥ the
  merge-base measurement; `ruff check backend` with **zero** new findings;
  `npm run build` passes; Vitest statements/branches/functions/lines ≥
  80/76/78/80 **and** ≥ the merge-base measurement for each; `npm run lint`
  with no new non-test `src/**` findings; and
  `src/i18n/__tests__/index.test.ts` stays green with `en`/`pt` key sets
  identical and `modules.names` carrying all **27** module labels in both
  languages, including `modules.names.billing`. `AGENTS.md` carries the
  *Assinatura e planos* subsection with §4.1's rule quoted verbatim, the
  amended *Módulos por tenant* note, the four new endpoint rows and the three
  `curl` examples.

---

## Out of Scope

Charging of any kind and every provider-shaped artefact (SDK, API key,
webhook receiver, invoices, receipts, proration, dunning, trials, coupons,
tax); tenant-initiated plan changes; per-tenant or custom plans; deleting a
plan; a module dependency graph; any edit to `deps.get_effective_permissions`,
`deps.disabled_modules` or `permissions.filter_by_modules`; any edit to
`APRAS-39`'s `/admin/modules` page or to `ROUTE_PERMISSIONS` entries other
than the three declared; retiring `PUT /api/v1/tenants/{id}/modules`; seeding
`billing:*` into any role bundle; any change to migration `0028`'s
`_TENANT_SCOPED_TABLES` literal; a `Relationship` on `TenantSubscription`
(§3.2 — `entitlement()`'s join is the one loader); **any change to
`backend/tests/data/parity_matrix_baseline.json`, to the `02c2025…` sha
anchors in `tests/test_legacy_role_permissions.py` and
`tests/test_permission_enforcement.py`, or to the entries or sizes of
`DENIAL_SHAPE_OVERRIDES`, `NON_ROLE_403` and `PERMITTED_422`** (§9.2.1,
§9.2.4.1); and any unscoped run of
`tests/tools/record_parity_baseline.py`.

**What is explicitly *in* scope, stated here so it is not read as a violation
of the line above:** §9.2.4.1's edit to the `holds()` predicate in
`tests/test_permission_parity_matrix.py`. The **frozen artefact is the F2
baseline JSON**, not the test module: the file records what production
answered, the predicate records what production *should* answer, and a
superuser flag that did not exist when the file was recorded is a change to the
second, never to the first. The edit is admissible precisely because it is
proven inert on the 1080 recorded cells
(`test_the_superuser_branch_changes_no_f2_verdict`), which is what keeps F2 a
result rather than a rewritten one.
