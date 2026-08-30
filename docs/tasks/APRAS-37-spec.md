# APRAS-37 — Implementar cotação de compras com orçamentos e escolha justificada

## Scope

This task delivers a **self-contained purchase-quotation module**: a purchase request
("pedido de compra") that collects several supplier quotes ("orçamentos") and records a
single, justified choice among them.

### What this task covers

1. **Domain model** — three new tables (`purchase_request`, `purchase_quote`,
   `purchase_quote_decision`) and one new enum (`PurchaseRequestStatus`).
2. **Alembic migration** `0027_add_purchase_quotation` on top of the current head
   `0026_add_asset_and_inventory`.
3. **Service layer + RBAC** (`PurchaseService`) with the role matrix decided below.
4. **REST API** under `/api/v1/purchase-requests`.
5. **Frontend SPA** — feature `purchase-management`, route `/purchases`, Navbar entry,
   full pt/en i18n.
6. **Tests** — pytest (backend) and Vitest (frontend), including an explicit
   *isolation* test suite (§8) that mechanically proves the no-integration constraint
   stated below.

### What this task explicitly does NOT cover

See [Out of Scope](#out-of-scope). The headline non-goal, restated because it is a hard
constraint and not a preference: **no integration with Financeiro, Patrimônio & Estoque
or Obras.** Choosing a quote creates no `FinancialTransaction`, no `InventoryMovement`,
and no link to any `ConstructionProject`. No existing table, model, schema, service,
endpoint or frontend feature of those three modules may be touched by this task.

---

## Decision: who may do what (the open question)

The dispatch left the role matrix open. Decision and reasoning:

| Action | ADMINISTRATOR | DIRECTOR | MANAGER | RESIDENT / PORTEIRO / GUEST |
|---|---|---|---|---|
| List / read purchase requests and quotes | ✅ | ✅ | ✅ | ❌ 403 |
| Create purchase request | ✅ | ✅ | ✅ | ❌ 403 |
| Edit / delete purchase request | ✅ any | ✅ any | ✅ **own, while `OPEN`** | ❌ 403 |
| Add / edit / delete quote | ✅ any | ✅ any | ✅ **own quote, while request is `OPEN`** | ❌ 403 |
| **Choose a quote (record decision)** | ✅ | ✅ | ❌ 403 | ❌ 403 |
| Cancel a purchase request | ✅ | ✅ | ❌ 403 | ❌ 403 |

**Reasoning.**

- *Collecting quotes is legwork, not authority.* Phoning suppliers and typing three
  budgets into the system is exactly the síndico/Manager's operational job. Blocking
  Managers from entering quotes would push the data collection back into WhatsApp,
  which is the problem APRAS exists to solve. This mirrors the precedent set by
  APRAS-34, where a MANAGER may record `ENTRADA`/`SAIDA` stock movements but may not
  define or delete the assets themselves.
- *Choosing is the spending decision, and that is why the justification exists.* The
  operator's stated purpose for requiring a justification is accountability toward the
  association. An accountability record is only worth keeping if the person signing it
  is the person answerable for the spend — the board. Therefore `POST .../decision` is
  restricted to `ADMINISTRATOR` and `DIRECTOR`. A MANAGER attempting it gets `403`.
- *Ownership scoping for Managers* (edit/delete only their own rows, only while the
  request is `OPEN`) keeps one Manager from silently rewriting another's collected
  quote, without needing a new permission concept.
- *Residents are excluded entirely, for now.* Quotes carry supplier prices under
  negotiation. Publishing them to residents is a governance choice (an assembly/
  transparency decision), not a default; the operator has not made it. Read-only
  resident visibility is listed as an explicit follow-up in
  [Out of Scope](#out-of-scope), not implemented here.
- *No `UserType`/`MenuKey` gate.* `MenuKey` currently has exactly two members
  (`tasks`, `categories`) and every module since APRAS-8 (finance, packages, voting,
  assets) gates on role alone. Adding a `purchases` menu key would touch
  `UserType.allowed_menus` semantics and the admin UI — out of proportion for this PR.

---

## Approach

### 1. Enum — `backend/app/models/enums.py`

Append (keeping the file's existing style):

```python
class PurchaseRequestStatus(StrEnum):
    """Enumeration for purchase request lifecycle status."""

    OPEN = "OPEN"
    DECIDED = "DECIDED"
    CANCELLED = "CANCELLED"
```

Export it from `app/models/__init__.py` (both the import block and `__all__`).

### 2. Models — `backend/app/models/purchase.py` (new file)

```python
"""Models for purchase requests, supplier quotes and the justified choice (APRAS-37)."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column
from sqlmodel import Field, Relationship, SQLModel

from app.models.enums import PurchaseRequestStatus


class PurchaseRequest(SQLModel, table=True):
    """A request to buy something, against which supplier quotes are collected."""

    __tablename__ = "purchase_request"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str = Field(nullable=False, index=True)
    description: str | None = Field(default=None, nullable=True)
    # "Anotações gerais do pedido" — free-text scratchpad for the request as a
    # whole (deadlines, who to call, board remarks), distinct from `description`
    # (what is to be bought) and from each quote's own `notes`.
    general_notes: str | None = Field(default=None, nullable=True)
    status: PurchaseRequestStatus = Field(
        default=PurchaseRequestStatus.OPEN, nullable=False, index=True
    )
    requested_by_id: UUID = Field(foreign_key="user.id", nullable=False, index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), nullable=False, index=True
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), nullable=False
    )

    quotes: list["PurchaseQuote"] = Relationship(
        back_populates="purchase_request",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "PurchaseQuote.created_at",
        },
    )
    decisions: list["PurchaseQuoteDecision"] = Relationship(
        back_populates="purchase_request",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "PurchaseQuoteDecision.decided_at.desc()",
        },
    )


class PurchaseQuote(SQLModel, table=True):
    """One supplier quote for a purchase request."""

    __tablename__ = "purchase_quote"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    purchase_request_id: UUID = Field(
        foreign_key="purchase_request.id",
        nullable=False,
        index=True,
        ondelete="CASCADE",
    )
    supplier_name: str = Field(nullable=False, index=True)
    supplier_contact: str | None = Field(default=None, nullable=True)
    unit_price: float = Field(nullable=False)
    quantity: int = Field(nullable=False)
    notes: str | None = Field(default=None, nullable=True)
    # Caller-defined extra fields, stored as an ordered list of
    # {"label": str, "value": str} objects. Portable JSON column (NOT Postgres
    # JSONB/ARRAY): tests/conftest.py builds the schema with
    # SQLModel.metadata.create_all() against sqlite:// in memory, exactly as
    # documented on UserType.allowed_menus.
    extra_fields: list[dict[str, str]] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, server_default="[]"),
    )
    created_by_id: UUID = Field(foreign_key="user.id", nullable=False, index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), nullable=False
    )

    purchase_request: PurchaseRequest = Relationship(back_populates="quotes")


class PurchaseQuoteDecision(SQLModel, table=True):
    """An append-only record of a board member choosing one quote, with reasons."""

    __tablename__ = "purchase_quote_decision"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    purchase_request_id: UUID = Field(
        foreign_key="purchase_request.id",
        nullable=False,
        index=True,
        ondelete="CASCADE",
    )
    quote_id: UUID = Field(
        foreign_key="purchase_quote.id",
        nullable=False,
        index=True,
        ondelete="CASCADE",
    )
    justification: str = Field(nullable=False)
    decided_by_id: UUID = Field(foreign_key="user.id", nullable=False, index=True)
    decided_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), nullable=False, index=True
    )

    purchase_request: PurchaseRequest = Relationship(back_populates="decisions")
```

**Why a decision *table* rather than `PurchaseRequest.selected_quote_id`.** Three
reasons, in order of weight:

1. *No circular FK.* A `selected_quote_id` on `purchase_request` pointing at
   `purchase_quote`, which itself points back at `purchase_request`, forces
   `use_alter`/post-hoc `create_foreign_key` in the migration and `foreign_keys=`
   disambiguation on every relationship. The decision table makes the graph a strict
   DAG: `purchase_request` → `purchase_quote` → `purchase_quote_decision`.
2. *Append-only preserves accountability.* If the board changes its mind, the
   superseded justification is not overwritten — it stays in the history. An
   `UPDATE`-in-place design silently destroys precisely the record the feature exists
   to keep.
3. *It matches existing convention.* `InventoryMovement` (APRAS-34) and `TaskHistory`
   are both insert-only ledgers; this is the same shape.

The **current decision** is the row with the greatest `decided_at` (ties broken by
insertion order). `PurchaseQuote` deliberately gets **no** `decisions` relationship —
only the FK column — to avoid two overlapping cascade paths onto the same child.

### 3. Migration — `backend/alembic/versions/0027_add_purchase_quotation.py`

- `revision = "0027_add_purchase_quotation"`, `down_revision = "0026_add_asset_and_inventory"`
  (verified current single head).
- Creates exactly the three tables above, using `sa.Uuid()`, `sa.String()`, `sa.Text()`
  for the long free-text columns (`description`, `general_notes`, `notes`,
  `justification`), `sa.Float()` for `unit_price` (matches `Asset.acquisition_value`
  and `BudgetLine.planned_amount`), `sa.JSON()` with `server_default="[]"` for
  `extra_fields`, and `sa.DateTime()` for timestamps — mirroring
  `0026_add_asset_and_inventory` line for line.
- FKs: `purchase_quote.purchase_request_id → purchase_request.id ON DELETE CASCADE`;
  `purchase_quote_decision.purchase_request_id → purchase_request.id ON DELETE CASCADE`;
  `purchase_quote_decision.quote_id → purchase_quote.id ON DELETE CASCADE`;
  every `*_by_id` → `user.id ON DELETE RESTRICT`.
- Indexes: `ix_purchase_request_title`, `ix_purchase_request_status`,
  `ix_purchase_request_requested_by_id`, `ix_purchase_request_created_at`,
  `ix_purchase_quote_purchase_request_id`, `ix_purchase_quote_supplier_name`,
  `ix_purchase_quote_created_by_id`, `ix_purchase_quote_decision_purchase_request_id`,
  `ix_purchase_quote_decision_quote_id`, `ix_purchase_quote_decision_decided_by_id`,
  `ix_purchase_quote_decision_decided_at`.
- `downgrade()` drops the indexes and the three tables in reverse order and nothing else.
- The migration must not reference any table outside `user` and the three new ones.
  No `ALTER` of `financial_transaction`, `asset`, `inventory_movement`,
  `construction_project` or anything else.
- **The Alembic chain identifiers are not module references.** The file's docstring will
  read `Revises: 0026_add_asset_and_inventory` and the module will assign
  `down_revision: str | Sequence[str] | None = "0026_add_asset_and_inventory"`, exactly
  as `0026` does for `0025`. The substring `asset` inside that revision *name* is
  mandatory and is **exempt** from the isolation scan by construction: the scan in §8 is
  AST-based and inspects only import statements and the table-name arguments of
  `op.*` / `sa.ForeignKey*` calls, so the module docstring and the `revision` / `down_revision` /
  `branch_labels` / `depends_on` assignments are never examined. No implementation may
  rename the revision or exclude the migration from the scan to work around this.

### 4. Schemas — `backend/app/schemas/purchase.py` (new file)

```python
class QuoteExtraField(BaseModel):
    """One caller-defined extra field on a quote."""

    # NOTE: deliberately no `min_length=1` on `label`. Field-level constraints run
    # *before* any after-validator, so `min_length=1` would accept "   " and the
    # subsequent strip would silently store an empty label. Emptiness is therefore
    # checked below, after stripping, which is the only ordering that makes
    # `{"label": "   "}` a 422.
    label: str = Field(..., max_length=60)
    value: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def _normalize(self) -> "QuoteExtraField":
        self.label = self.label.strip()
        self.value = self.value.strip()
        if not self.label:
            raise ValueError("O rótulo do campo extra não pode ser vazio.")
        return self
```

**Normalization and ordering rules for `extra_fields` (normative).**

1. `max_length` on `label` / `value` is evaluated on the **raw** string, before
   stripping. A 60-character label wrapped in spaces is therefore a `422`. This is
   intentional and deterministic; do not move the length check after the strip.
2. `label` is stripped, then rejected with `ValueError` (→ HTTP `422`) if it is empty
   **after** stripping. Both `{"label": ""}` and `{"label": "   "}` are `422`.
3. `value` is stripped as well; an empty or whitespace-only `value` is **valid** and is
   stored as `""` (a label with no value yet is a legitimate row in the editor).
4. `QuoteExtraField`'s own `model_validator(mode="after")` runs while the parent model's
   `extra_fields` field is being validated, i.e. **strictly before** the parent's
   `model_validator(mode="after")`. Consequently the parent validator always sees
   already-stripped labels, and `[{"label": "Prazo"}, {"label": " prazo "}]` collides on
   the duplicate rule. This ordering is a requirement, not an incidental effect: the
   duplicate check must never be implemented on raw, unstripped labels.

- `PurchaseRequestCreate`: `title` (1..255), `description` (≤4000, optional),
  `general_notes` (≤4000, optional).
- `PurchaseRequestUpdate`: all three optional.
- `PurchaseQuoteCreate`: `supplier_name` (1..255), `supplier_contact` (≤255, optional),
  `unit_price: float = Field(..., ge=0)`, `quantity: int = Field(..., gt=0)`,
  `notes` (≤4000, optional), `extra_fields: list[QuoteExtraField] = []`.
  A `model_validator(mode="after")` on the *parent* model enforces, on the
  already-normalized list: at most **20** entries, and no two labels equal under
  `str.casefold()` (both raise `ValueError`, which FastAPI surfaces as HTTP `422`).
  Input order is preserved as given.
- `PurchaseQuoteUpdate`: every field optional, same `QuoteExtraField` type and same
  parent-level validator; when `extra_fields` is omitted the stored list is untouched,
  when it is supplied it replaces the stored list wholesale.
- `PurchaseDecisionCreate`: `quote_id: UUID`, `justification: str = Field(..., min_length=10, max_length=2000)`
  plus a validator rejecting whitespace-only text. Ten characters is the smallest bar
  that rejects `"ok"`/`"-"`-style non-justifications while staying mechanically checkable.
- `PurchaseQuoteRead`: model fields + `total_price` (computed, `round(unit_price * quantity, 2)`),
  `created_by_name`, `is_selected` (equals the current decision's `quote_id`),
  `is_lowest_price` (its `total_price` is the minimum among the request's quotes).
  `total_price` is computed in a `model_validator(mode="after")`, exactly as
  `AssetRead.is_low_stock` is; `is_selected` / `is_lowest_price` are populated by the
  service, which is the only place that knows the sibling rows.
- `PurchaseDecisionRead`: `id`, `quote_id`, `quote_supplier_name`, `quote_total_price`,
  `justification`, `decided_by_id`, `decided_by_name`, `decided_at`, `is_current`.
- `PurchaseRequestRead` (list row): model fields + `requested_by_name`, `quote_count`,
  `lowest_quote_total: float | None`, `selected_quote_id: UUID | None`,
  `selected_quote_total: float | None`, `decision_justification: str | None`,
  `decided_at: datetime | None`.
- `PurchaseRequestDetailRead(PurchaseRequestRead)`: `quotes: list[PurchaseQuoteRead]`
  (ordered by `total_price` ascending, then `created_at`),
  `decisions: list[PurchaseDecisionRead]` (newest first),
  `current_decision: PurchaseDecisionRead | None`.
- `PaginatedPurchaseRequestRead`: `items`, `total`, `skip`, `limit`.
- `PurchaseSummaryRead`: `open_count`, `decided_count`, `cancelled_count`,
  `total_selected_value` (sum of `total_price` of the current decisions' quotes).

### 5. Exceptions — `backend/app/core/exceptions.py` + `exception_handlers.py`

Add, in the existing style (Portuguese messages, as the recent modules use):

| Exception | Mapped status | Raised when |
|---|---|---|
| `PurchaseRequestNotFoundError` | 404 | unknown request id |
| `PurchaseQuoteNotFoundError` | 404 | unknown quote id **or** quote belongs to another request |
| `PurchaseAccessForbiddenError` | 403 | role/ownership rule violated |
| `PurchaseRequestNotOpenError` | 400 | decision or cancel on a `CANCELLED` request; cancel on a `DECIDED` one |
| `PurchaseQuoteFrozenError` | 409 | add/edit/delete a quote on a request that is no longer `OPEN` |

Register each in the corresponding tuple in `handle_domain_error`
(`exception_handlers.py`), following how the `Asset*` errors were wired.

### 6. Service — `backend/app/services/purchase_service.py` (new file)

`PurchaseService`, static methods, same signature shape as `AssetService`
(`session`, `current_user`, …). Module-level constants:

```python
_DECIDE_ROLES = {UserRole.ADMINISTRATOR, UserRole.DIRECTOR}
_WRITE_ROLES = {UserRole.ADMINISTRATOR, UserRole.DIRECTOR, UserRole.MANAGER}
_VIEW_ROLES = _WRITE_ROLES
```

Methods:

- `list_requests(...)` — filters `status`, `requested_by_id`, `search` (case-insensitive
  `title` / `description` match, using `or_` + `ilike`, as `AssetService.list_assets`
  does), `skip`, `limit` (`ge=1, le=100`); ordered by `created_at DESC`.
- `get_summary(...)`.
- `create_request(...)` — sets `requested_by_id = current_user.id`, `status = OPEN`.
- `get_request(...)` — returns `PurchaseRequestDetailRead` with quotes sorted by
  `total_price` ASC, `is_lowest_price` / `is_selected` decorated, decisions newest-first
  with `is_current` on the newest.
- `update_request(...)` / `delete_request(...)` — `_assert_can_write_request` helper:
  Admin/Director always; Manager only if `requested_by_id == current_user.id` **and**
  `status == OPEN`; otherwise `PurchaseAccessForbiddenError`. Delete is a hard delete
  and relies on the ORM relationship cascade (so it also works on SQLite, whose FK
  enforcement is off by default in the test engine).
- `add_quote(...)` / `update_quote(...)` / `delete_quote(...)` — request must be `OPEN`
  (else `PurchaseQuoteFrozenError`, 409); Manager may only touch quotes where
  `created_by_id == current_user.id`. Quote lookup is always by
  `(id, purchase_request_id)`, so a quote id from another request yields 404.
- `select_quote(...)` — role must be in `_DECIDE_ROLES`; request must not be
  `CANCELLED`; quote must belong to the request; inserts a `PurchaseQuoteDecision` and
  sets `status = DECIDED` (idempotent when already `DECIDED`). A second call **is
  allowed** and supersedes: both justifications remain in `decisions`, the newest is
  `is_current`. Quotes stay frozen throughout, so a recorded justification can never
  come to describe a quote that was edited afterwards.
- `cancel_request(...)` — `_DECIDE_ROLES` only; `OPEN → CANCELLED`; any other source
  status raises `PurchaseRequestNotOpenError` (400).

`created_by_name` / `decided_by_name` / `requested_by_name` are resolved with a single
`select(User).where(User.id.in_(ids))` lookup per call, mirroring how
`AssetService` resolves `performed_by_name`.

**Isolation constraint on this file:** `purchase_service.py` must not import
`app.models.finance`, `app.models.asset`, `app.models.project`, or their schemas/
services. This is asserted by a test (§8).

### 7. Endpoints — `backend/app/api/v1/endpoints/purchases.py` (new file)

Mounted in `app/api/v1/api.py`:

```python
api_router.include_router(
    purchases.router, prefix="/purchase-requests", tags=["purchase-requests"]
)
```

| Method & path | Body / query | Success | Roles |
|---|---|---|---|
| `GET /api/v1/purchase-requests` | `status`, `requested_by_id`, `search`, `skip`, `limit` | 200 `PaginatedPurchaseRequestRead` | Admin, Director, Manager |
| `GET /api/v1/purchase-requests/summary` | — | 200 `PurchaseSummaryRead` | Admin, Director, Manager |
| `POST /api/v1/purchase-requests` | `PurchaseRequestCreate` | 201 `PurchaseRequestRead` | Admin, Director, Manager |
| `GET /api/v1/purchase-requests/{request_id}` | — | 200 `PurchaseRequestDetailRead` | Admin, Director, Manager |
| `PUT /api/v1/purchase-requests/{request_id}` | `PurchaseRequestUpdate` | 200 `PurchaseRequestRead` | Admin, Director; Manager (own + OPEN) |
| `DELETE /api/v1/purchase-requests/{request_id}` | — | 204 | Admin, Director; Manager (own + OPEN) |
| `POST /api/v1/purchase-requests/{request_id}/quotes` | `PurchaseQuoteCreate` | 201 `PurchaseQuoteRead` | Admin, Director, Manager |
| `PUT /api/v1/purchase-requests/{request_id}/quotes/{quote_id}` | `PurchaseQuoteUpdate` | 200 `PurchaseQuoteRead` | Admin, Director; Manager (own quote) |
| `DELETE /api/v1/purchase-requests/{request_id}/quotes/{quote_id}` | — | 204 | Admin, Director; Manager (own quote) |
| `POST /api/v1/purchase-requests/{request_id}/decision` | `PurchaseDecisionCreate` | 201 `PurchaseDecisionRead` | **Admin, Director only** |
| `POST /api/v1/purchase-requests/{request_id}/cancel` | — | 200 `PurchaseRequestRead` | Admin, Director only |

`/summary` must be declared **before** `/{request_id}` in the module, or FastAPI will
try to parse `"summary"` as a UUID — the same ordering `assets.py` relies on. Quote
routes are nested under the request id so there is no ambiguity with `/{request_id}`.

### 8. Backend tests — `backend/tests/`

- `test_purchase_requests.py` — request CRUD, filters, search, pagination, summary,
  cancel, 404s.
- `test_purchase_quotes.py` — multiple quotes per request; `total_price` arithmetic;
  ordering by `total_price`; `is_lowest_price`; `extra_fields` round-trip (order and
  content preserved); casos de `extra_fields` que devem retornar 422, cada um asserido
  separadamente: `{"label": ""}`; `{"label": "   "}` (só espaços — exatamente o caso que
  um `min_length=1` no nível do campo deixaria passar); rótulos duplicados diferindo só
  na caixa (`"Prazo"` / `"prazo"`); rótulos duplicados diferindo só nos espaços das
  pontas (`"Prazo"` / `" Prazo "`); e 21 entradas. Mais o caso positivo:
  `{"label": " Prazo ", "value": "  "}` é aceito e relido como
  `{"label": "Prazo", "value": ""}`. Também: quote of another request -> 404; quotes
  frozen after decision -> 409.
- `test_purchase_decision.py` — happy path (201, `status=DECIDED`, `is_selected`,
  `current_decision`); missing/blank/9-char justification → 422 with **no** decision row
  created; decision on a cancelled request → 400; re-decision supersedes and both
  justifications remain, newest `is_current: true`.
- `test_purchases_rbac.py` — the full matrix from the Decision section, including
  MANAGER → 403 on `/decision` and `/cancel`, RESIDENT/PORTEIRO/GUEST → 403 everywhere,
  Manager editing another Manager's request/quote → 403, Manager editing own request
  after it is `DECIDED` → 403/409.
- `test_purchase_isolation.py` — the mechanical proof of the isolation constraint. **No
  raw substring/`in`-check over file text anywhere in this module**: a naive
  `"asset" in source` scan is both a false positive (the mandatory `down_revision`
  identifier `0026_add_asset_and_inventory`, and the unrelated legitimate module
  `app.models.media_asset`) and a false negative (`from app.models import Asset` contains
  no lowercase `asset`). The scan is defined structurally, over `ast.parse()` of each
  file, as follows.

  **Scanned files** (all five, the migration included — excluding it is not an
  acceptable implementation):

  ```python
  SCANNED = [
      "app/models/purchase.py",
      "app/schemas/purchase.py",
      "app/services/purchase_service.py",
      "app/api/v1/endpoints/purchases.py",
      "alembic/versions/0027_add_purchase_quotation.py",
  ]
  ```

  **Rule 1 — forbidden module imports.** Walk the AST; collect `node.name` for every
  `ast.Import` alias and `node.module` for every `ast.ImportFrom` with `level == 0`.
  Assert the collected set is disjoint from:

  ```python
  FORBIDDEN_MODULES = {
      "app.models.finance", "app.models.asset", "app.models.project",
      "app.schemas.finance", "app.schemas.asset", "app.schemas.project",
      "app.services.finance_service", "app.services.asset_service",
      "app.services.project_service",
      "app.api.v1.endpoints.finance", "app.api.v1.endpoints.assets",
      "app.api.v1.endpoints.inventory_movements", "app.api.v1.endpoints.projects",
  }
  ```

  Equality on the full dotted module path, not substring containment — `app.models.media_asset`
  and `app.schemas.media_asset` are legal and must not trip the test.

  **Rule 2 — forbidden names re-exported through the aggregate packages.** For every
  `ast.ImportFrom` whose `module` is `app.models`, `app.schemas` or `app.services`,
  assert the set of `alias.name` values is disjoint from:

  ```python
  FORBIDDEN_NAMES = {
      "FinanceCategory", "BudgetLine", "FinancialTransaction",
      "Asset", "InventoryMovement",
      "ConstructionProject", "ProjectMilestone", "ProjectUpdate",
      "FinanceService", "AssetService", "ProjectService",
  }
  ```

  **Rule 3 — forbidden tables touched by the migration.** Over the migration AST only,
  collect table names from every `ast.Call`, keyed on `ast.unparse(node.func)`:

  | Call renders as | Table name taken from |
  |---|---|
  | `op.create_table`, `op.drop_table`, `op.add_column`, `op.drop_column`, `op.alter_column`, `op.execute`*, `op.rename_table` | 1st positional arg (a `str` constant) |
  | `op.create_index`, `op.drop_index` | 2nd positional arg, or the `table_name=` keyword |
  | `sa.ForeignKeyConstraint` | every element of the **2nd** positional arg (a list of `"table.column"` constants), taking the part before the first `"."` |
  | `sa.ForeignKey` | 1st positional arg, part before the first `"."` |
  | `op.create_foreign_key` | `source_table` / `referent_table` (2nd and 3rd positional args, or the same-named keywords) |

  \* `op.execute` with a non-constant or non-`str` argument must fail the test outright —
  raw SQL is not statically checkable and is not needed by this migration.

  `sa.ForeignKeyConstraint` is the form this repo actually uses
  (`0026_add_asset_and_inventory` declares
  `sa.ForeignKeyConstraint(["performed_by_id"], ["user.id"], ondelete="RESTRICT")`), so
  omitting it from the rule would let every cross-module FK slip past the scan. Assert
  the resulting set of table names is a subset of:

  ```python
  ALLOWED_TABLES = {"purchase_request", "purchase_quote", "purchase_quote_decision", "user"}
  ```

  **Explicit exemptions.** Because rules 1–3 read only import nodes and `op.*` /
  `sa.ForeignKey` call arguments, the module docstring (`Revises: 0026_add_asset_and_inventory`)
  and the module-level `revision`, `down_revision`, `branch_labels` and `depends_on`
  assignments are outside the scan's reach and are never inspected. The test must
  additionally assert positively that
  `down_revision == "0026_add_asset_and_inventory"` in the new migration, so that the
  chain link is proven rather than merely tolerated.

  **Runtime half.** Run the full flow (create request → 2 quotes → decision) through the
  API client against the test session, then assert
  `session.exec(select(func.count()).select_from(X)).one() == 0` for
  `FinancialTransaction`, `InventoryMovement`, `Asset` and `ConstructionProject`.

Fixtures follow `conftest.py` (in-memory SQLite, `client` with the session override).
Manager and Resident/Porteiro/Guest users are built locally in the test module the way
`test_packages_rbac.py` does.

New backend modules must reach **≥ 90 % line coverage** and the whole suite must stay
green (`cd backend && uv run pytest`).

### 9. Frontend

**Types** — `frontend/src/types/purchase.ts`: `PurchaseRequestStatus` const-object +
type (same pattern as `types/asset.ts`), `QuoteExtraField`, `PurchaseQuote`,
`PurchaseDecision`, `PurchaseRequest`, `PurchaseRequestDetail`, `PurchaseSummary`,
`PaginatedPurchaseRequests`, `PurchaseRequestFormData`, `QuoteFormData`,
`DecisionFormData`, `PurchaseFilterParams`.

**API client** — `frontend/src/api/purchases.ts`: `getPurchaseRequests`,
`getPurchaseSummary`, `getPurchaseRequestById`, `createPurchaseRequest`,
`updatePurchaseRequest`, `deletePurchaseRequest`, `addQuote`, `updateQuote`,
`deleteQuote`, `selectQuote`, `cancelPurchaseRequest` — all through `apiClient`.

**Hooks** — `frontend/src/features/purchase-management/hooks/usePurchaseRequests.ts`:
TanStack Query hooks with query keys `["purchase-requests", params]`,
`["purchase-requests", id]`, `["purchase-summary"]`; every mutation invalidates the
list, the affected detail, and the summary (same shape as `useAssets.ts`).

**Components** — `frontend/src/features/purchase-management/components/`:

| Component | Responsibility |
|---|---|
| `PurchaseRequestsPage.tsx` | Summary cards, status tabs (todos / abertos / decididos / cancelados), search box, request list, "Novo pedido" button. Gets the acting role from `useEffectiveIdentity()`. |
| `PurchaseRequestFormModal.tsx` | Create/edit `title`, `description`, `general_notes`. |
| `PurchaseRequestDetailModal.tsx` | Request header + general notes; quotes table sorted by total ascending with "menor preço" and "escolhido" badges and each quote's extra fields rendered as label/value pairs; decision panel showing the current justification, its author and date, plus superseded ones. |
| `QuoteFormModal.tsx` | Supplier, contact, unit price, quantity, live computed total, notes, and a dynamic extra-fields editor (add row / remove row, label + value inputs). |
| `SelectQuoteModal.tsx` | Quote summary + justification textarea; submit disabled while the trimmed justification is under 10 characters, with an inline hint. Rendered only when the acting role is ADMINISTRATOR or DIRECTOR. |

**Routing & nav** — `App.tsx` gains `/purchases` wrapped in
`<ProtectedRoute requiredRoles={[ADMINISTRATOR, DIRECTOR, MANAGER]}>`; `Navbar.tsx`
gains a link guarded by the same three effective roles, label
`t("nav.purchases", "Cotações de Compra")`.

**i18n** — new top-level `purchases` namespace in `frontend/src/i18n/locales/pt.json`
and `en.json` (page title/subtitle, status labels, table headers, action labels,
extra-fields editor labels, decision panel labels, validation hints), plus
`nav.purchases` in both files. No hard-coded user-facing strings.

**Frontend tests** — `frontend/src/features/purchase-management/__tests__/` with one
file per component plus `usePurchaseRequests.test.tsx`, covering at minimum: the page
renders a request list; the quote form adds and removes extra-field rows and submits
them; the detail modal shows quotes ordered by total with the lowest-price badge; the
select-quote control is absent for a MANAGER and present for a DIRECTOR; the submit
button stays disabled for a short justification. The repo-wide Vitest thresholds
(lines 80 / functions 78 / branches 76 / statements 80) must stay green, and
`npm run build` must pass with no TypeScript errors.

---

## Expected Results

- [ ] `POST /api/v1/purchase-requests` com `{title, description, general_notes}` como ADMINISTRATOR, DIRECTOR ou MANAGER retorna `201` e o corpo traz `id`, `status: "OPEN"` e os textos de `description` e `general_notes` gravados; o mesmo POST como RESIDENT, PORTEIRO ou GUEST retorna `403`.
- [ ] `POST /api/v1/purchase-requests/{id}/quotes` aceita vários orçamentos no mesmo pedido; cada resposta `201` traz `supplier_name`, `unit_price`, `quantity` e `total_price` igual a `unit_price × quantity`; `GET /api/v1/purchase-requests/{id}` devolve todos eles em `quotes`, ordenados por `total_price` crescente, com `is_lowest_price: true` apenas no mais barato.
- [ ] Um orçamento aceita `extra_fields` como lista ordenada de pares `{label, value}` (ex.: `{"label": "Prazo de entrega", "value": "15 dias"}`), devolvidos íntegros e na mesma ordem pelo `GET` do pedido, com `label` e `value` já sem espaços nas pontas; retornam `422`: rótulo vazio (`{"label": ""}`), rótulo só com espaços (`{"label": "   "}`), rótulos repetidos ignorando caixa e espaços (`[{"label": "Prazo"}, {"label": " prazo "}]`) e mais de 20 itens. Um `value` vazio ou só com espaços é **aceito** e gravado como `""`.
- [ ] `POST /api/v1/purchase-requests/{id}/decision` com `{quote_id, justification}` como ADMINISTRATOR ou DIRECTOR retorna `201`; o pedido passa a `status: "DECIDED"` e o `GET` do pedido mostra `current_decision` com a justificativa, o nome de quem decidiu e a data, e o orçamento escolhido com `is_selected: true`.
- [ ] A mesma chamada sem justificativa, com justificativa em branco ou com menos de 10 caracteres retorna `422` e nenhuma decisão é registrada (`decisions` continua vazio); a mesma chamada como MANAGER retorna `403`.
- [ ] Com o pedido já decidido, `POST /{id}/quotes`, `PUT /{id}/quotes/{quote_id}` e `DELETE /{id}/quotes/{quote_id}` retornam `409`; uma segunda decisão sobre o mesmo pedido é aceita e o `GET` passa a listar as duas justificativas em `decisions`, a mais recente com `is_current: true` e a anterior preservada com `is_current: false`.
- [ ] `GET /api/v1/purchase-requests` como RESIDENT, PORTEIRO ou GUEST retorna `403`; um MANAGER que tenta `PUT`/`DELETE` em pedido ou orçamento criado por outro usuário recebe `403`.
- [ ] A migração `0027_add_purchase_quotation` aplica-se sobre a head `0026_add_asset_and_inventory`, cria apenas as tabelas `purchase_request`, `purchase_quote` e `purchase_quote_decision`, e `alembic heads` continua reportando uma única head; `alembic downgrade -1` remove exatamente essas três tabelas.
- [ ] O teste `backend/tests/test_purchase_isolation.py` passa e cobre os cinco arquivos do módulo — `app/models/purchase.py`, `app/schemas/purchase.py`, `app/services/purchase_service.py`, `app/api/v1/endpoints/purchases.py` e `alembic/versions/0027_add_purchase_quotation.py` (a migração **não** pode ser excluída da varredura) — via `ast.parse()`, verificando que: (a) nenhum `import`/`from ... import` tem módulo igual a um de `FORBIDDEN_MODULES` (§8, comparação por caminho pontilhado completo, de modo que `app.models.media_asset` continua permitido); (b) nenhum `from app.models|app.schemas|app.services import ...` importa um nome de `FORBIDDEN_NAMES` (§8); (c) os nomes de tabela usados como argumento de `op.create_table`/`op.drop_table`/`op.add_column`/`op.drop_column`/`op.alter_column`/`op.create_index`/`op.drop_index`/`sa.ForeignKey`/`sa.ForeignKeyConstraint`/`op.create_foreign_key` na migração são subconjunto de `{purchase_request, purchase_quote, purchase_quote_decision, user}`. Docstring do módulo e as atribuições `revision`/`down_revision`/`branch_labels`/`depends_on` ficam fora da varredura por construção — o teste ainda afirma positivamente que `down_revision == "0026_add_asset_and_inventory"`. Além disso, depois de criar pedido + orçamentos + decisão, as tabelas `financial_transaction`, `inventory_movement`, `asset` e `construction_project` continuam com zero linhas.
- [ ] O diff da tarefa não altera nenhum arquivo de Financeiro, Patrimônio & Estoque ou Obras — no backend (`app/models/finance.py`, `app/models/asset.py`, `app/models/project.py`, `app/services/finance_service.py`, `app/services/asset_service.py`, `app/services/project_service.py`, `app/api/v1/endpoints/{finance,assets,inventory_movements,projects}.py`) nem no frontend (`src/features/{finance,asset-management,project-management}`, `src/api/{finance,assets,projects}.ts`).
- [ ] No frontend, a rota `/purchases` renderiza a página para ADMINISTRATOR, DIRECTOR e MANAGER e redireciona os demais papéis para `/dashboard`; o item de menu "Cotações de Compra" aparece só para esses três papéis; o controle de escolher orçamento não é renderizado para MANAGER e, para DIRECTOR/ADMINISTRATOR, o botão de confirmar fica desabilitado enquanto a justificativa tiver menos de 10 caracteres.
- [ ] `cd backend && uv run pytest` passa com os módulos novos em ≥ 90 % de cobertura de linhas; `cd frontend && npm run test:coverage` passa dentro dos limiares atuais (80/78/76/80) e `npm run build` termina sem erros de TypeScript.

---

## Out of Scope

- **Financeiro / Patrimônio & Estoque / Obras integration — hard non-goal.** No
  `FinancialTransaction`, no `BudgetLine` consumption, no `InventoryMovement`, no
  `Asset` creation, no `ConstructionProject` link, no columns added to any of their
  tables, no changes to their endpoints or frontend features. A later task may add a
  one-way "gerar lançamento a partir da compra" bridge; it is not this one.
- **Resident/assembly visibility of quotations.** Residents get `403`. Publishing
  quotes for transparency is a governance decision the operator has not made.
- **Supplier registry.** `supplier_name` is free text on each quote; there is no
  `supplier` table, no supplier CRUD, no deduplication across quotes.
- **File attachments** (PDF of the supplier's proposal). No upload, no `MediaAsset`
  link. Extra fields are text-only.
- **Approval workflow / multi-signature.** One decision by one board member; no
  second approver, no threshold by amount, no assembly vote link (APRAS-33 is not
  touched).
- **Notifications / e-mail** to suppliers or to the board.
- **Reopening a cancelled request**, and deletion of decision records. Cancellation is
  terminal within this task; decisions are append-only and never deleted through the API.
- **`MenuKey`/`UserType` gating** for this module — role-based only, as with every
  module since APRAS-8 except tasks/categories.
- **Currency handling.** Values are plain `float` in the single implicit currency
  (BRL), consistent with `Asset.acquisition_value` and `BudgetLine.planned_amount`.
