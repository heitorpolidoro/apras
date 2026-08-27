# APRAS-22 — Área e Dashboard Financeiro da Associação

## Scope

This task implements the Association Financial Area & Dashboard module for APRAS: financial transaction and budget-line data models, a cash-balance / inflows-and-outflows statement, and a budget-vs-actual execution table with one-click PDF invoice drill-down. It gives HOA administrators, directors, and managers a way to record income and expense transactions against budgeted categories, and gives all roles (including residents, per HOA financial-transparency expectations) a read-only dashboard of the association's cash position.

### In Scope

1. **Database Schema & SQLModels** (`backend/app/models/finance.py`):
   - `FinanceCategory`: A budget/accounting category (e.g. "Água", "Manutenção", "Taxa Condominial", "Salários"), typed as `INCOME` or `EXPENSE`, soft-deactivatable (no hard delete).
   - `BudgetLine`: The planned amount for one `FinanceCategory` in one fiscal year. Unique per `(category_id, fiscal_year)`.
   - `FinancialTransaction`: A single recorded inflow or outflow — amount, date, category, description, optional payment method, optional attached invoice PDF (`invoice_file_path` / `invoice_file_url` / `invoice_file_size_bytes` / `invoice_mime_type`), and the user who recorded it.
   - New enum `TransactionType` (`INCOME`, `EXPENSE`) in `backend/app/models/enums.py`.
   - Alembic migration creating `finance_category`, `budget_line`, and `financial_transaction` tables with FKs, unique constraint, and indexes.

2. **RBAC & Security Matrix** (four-tier role model, consistent with T007/T009 precedent):
   - `ADMINISTRATOR` & `DIRECTOR`: Full CRUD on categories, budget lines, and transactions (including deleting any transaction and its invoice).
   - `MANAGER`: Read everything; create transactions and attach/replace/delete invoices on transactions **they created**; cannot edit or delete transactions created by others; cannot manage categories or budget lines; cannot delete any transaction.
   - `RESIDENT`: Read-only — cash balance, statement, budget-vs-actual table, and transaction/invoice drill-down. No write access anywhere in this module. (This mirrors the read-transparency access residents already have to `ConstructionProject` budgets in T007, and reflects the legal expectation that HOA members can inspect association accounts.)
   - `GUEST`: `403 Forbidden` on every endpoint.

3. **Backend REST API under `/api/v1/finance`**: category CRUD (soft-deactivate only), budget-line CRUD, transaction CRUD with pagination/filtering, invoice upload/delete on a transaction, cash-balance endpoint, monthly statement endpoint, and budget-vs-actual endpoint with a per-category transaction drill-down endpoint.

4. **Frontend UI** under `frontend/src/features/finance/`: a `/finance` dashboard route with cash-balance summary cards, an inflows/outflows statement chart+table, a budget-vs-actual table with expandable rows, and an invoice-preview modal reused/parallel to `PDFViewerModal` from the Document Center (T009).

5. **Testing**: backend pytest suite (≥ 90% coverage) and frontend vitest suite (≥ 75% coverage).

### Out of Scope

- Per-unit (lot) billing, condo-fee invoicing, delinquency/inadimplência tracking, or accounts receivable — this task tracks association-level cash movements only, not what each `Lot` owes. A future task may link `FinancialTransaction` to `Lot`.
- Bank statement (OFX) reconciliation or integration with accounting/ERP software.
- Multi-currency support (BRL / float only, consistent with `ConstructionProject.total_budget`).
- Recurring/scheduled transaction automation (e.g. auto-generating monthly utility expenses).
- Budget approval workflows or multi-year budget planning UI (a `BudgetLine` is just a flat planned amount per category/year, created directly by Admin/Director).
- Reusing the Document Center's `AssociationDocument`/folder/versioning machinery for invoices — invoices are stored as simple file fields directly on `FinancialTransaction` (see Approach) to keep this task PR-sized; cross-linking a transaction to an existing Document Center file is a possible follow-up, not required here.

---

## Approach

### 1. Enums (`backend/app/models/enums.py`)

```python
class TransactionType(StrEnum):
    """Enumeration for financial transaction / category direction."""

    INCOME = "INCOME"
    EXPENSE = "EXPENSE"
```

### 2. SQLModel Entities (`backend/app/models/finance.py`)

```python
import uuid
from datetime import date, datetime
from sqlmodel import Field, Relationship, SQLModel
from sqlalchemy import UniqueConstraint
from app.models.enums import TransactionType


class FinanceCategory(SQLModel, table=True):
    __tablename__ = "finance_category"
    __table_args__ = (
        UniqueConstraint("name", "type", name="uq_finance_category_name_type"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(nullable=False, index=True)
    type: TransactionType = Field(nullable=False, index=True)
    is_active: bool = Field(default=True, nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    budget_lines: list["BudgetLine"] = Relationship(back_populates="category")
    transactions: list["FinancialTransaction"] = Relationship(back_populates="category")


class BudgetLine(SQLModel, table=True):
    __tablename__ = "budget_line"
    __table_args__ = (
        UniqueConstraint("category_id", "fiscal_year", name="uq_budget_line_category_year"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    category_id: uuid.UUID = Field(
        foreign_key="finance_category.id", ondelete="RESTRICT", nullable=False, index=True
    )
    fiscal_year: int = Field(nullable=False, index=True)
    planned_amount: float = Field(default=0.0, nullable=False)
    notes: str | None = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    category: FinanceCategory = Relationship(back_populates="budget_lines")


class FinancialTransaction(SQLModel, table=True):
    __tablename__ = "financial_transaction"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    type: TransactionType = Field(nullable=False, index=True)
    category_id: uuid.UUID = Field(
        foreign_key="finance_category.id", ondelete="RESTRICT", nullable=False, index=True
    )
    description: str = Field(nullable=False)
    amount: float = Field(nullable=False)  # always > 0; sign implied by `type`
    transaction_date: date = Field(nullable=False, index=True)
    payment_method: str | None = Field(default=None, nullable=True)
    invoice_file_path: str | None = Field(default=None, nullable=True)
    invoice_file_url: str | None = Field(default=None, nullable=True)
    invoice_file_size_bytes: int | None = Field(default=None, nullable=True)
    invoice_mime_type: str | None = Field(default=None, nullable=True)
    created_by_id: uuid.UUID = Field(
        foreign_key="user.id", ondelete="RESTRICT", nullable=False, index=True
    )
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    category: FinanceCategory = Relationship(back_populates="transactions")
    created_by: "User" = Relationship()
```

Composite indexes: `(category_id, transaction_date)` and `(type, transaction_date)` to support the statement and budget-vs-actual aggregate queries.

**Invoice file fields**: `invoice_file_path` stores the *internal* filesystem path returned as the first element of `storage_service.LocalStorageProvider.save_file()` (e.g. `static/uploads/2026/08/<uuid>.pdf`) and is the value passed to `delete_file()`; `invoice_file_url` stores the second, public-facing `/static/uploads/...` URL served to the frontend. This mirrors `AnnouncementMedia.file_path`/`file_url` (`backend/app/models/announcement.py`) and `MediaAsset.file_path`/`file_url` (`backend/app/models/media_asset.py`) — the two existing consumers of the same storage abstraction — so `invoice_file_path` must never be exposed in `FinancialTransactionRead` or any API response; only `invoice_file_url` is public.

**Design note on "executed" amounts**: unlike `ConstructionProject.executed_budget` (a manually-edited scalar), `BudgetLine` does **not** store an executed/actual amount. The actual amount is always computed on read as `SUM(FinancialTransaction.amount)` for the matching category and fiscal year, so it can never drift from the underlying transactions.

### 3. Pydantic Schemas (`backend/app/schemas/finance.py`)

- `FinanceCategoryCreate`: `name: str`, `type: TransactionType`.
- `FinanceCategoryUpdate`: `name: str | None`, `is_active: bool | None`.
- `FinanceCategoryRead`: `id, name, type, is_active, created_at, updated_at`.
- `BudgetLineCreate`: `category_id: UUID`, `fiscal_year: int = Field(ge=2000, le=2100)`, `planned_amount: float = Field(ge=0.0)`, `notes: str | None`.
- `BudgetLineUpdate`: `planned_amount: float | None`, `notes: str | None`.
- `BudgetLineRead`: `id, category_id, category_name, category_type, fiscal_year, planned_amount, notes, created_at, updated_at`.
- `FinancialTransactionCreate`: `type: TransactionType`, `category_id: UUID`, `description: str = Field(min_length=1)`, `amount: float = Field(gt=0.0)`, `transaction_date: date`, `payment_method: str | None`.
- `FinancialTransactionUpdate`: same fields, all optional.
- `FinancialTransactionRead`: all model fields plus `category_name: str`, `created_by_name: str`.
- `PaginatedTransactions`: `items: list[FinancialTransactionRead]`, `total, skip, limit`.
- `CashBalanceRead`: `as_of_date: date`, `total_income: float`, `total_expense: float`, `balance: float`.
- `MonthlyStatementEntry`: `year: int`, `month: int`, `income: float`, `expense: float`, `net: float`, `running_balance: float`.
- `FinancialStatementRead`: `start_date: date`, `end_date: date`, `opening_balance: float`, `closing_balance: float`, `entries: list[MonthlyStatementEntry]`.
- `BudgetVsActualRow`: `category_id: UUID`, `category_name: str`, `category_type: TransactionType`, `planned_amount: float`, `executed_amount: float`, `variance_amount: float`, `variance_pct: float | None`, `transaction_count: int`.
- `BudgetVsActualRead`: `fiscal_year: int`, `rows: list[BudgetVsActualRow]`, `total_planned: float`, `total_executed: float`.

### 4. Domain Exceptions (`backend/app/core/exceptions.py`)

```python
class FinanceCategoryNotFoundError(DomainError): ...      # 404
class FinanceCategoryTypeMismatchError(DomainError): ...   # 422 — transaction.type != category.type
class BudgetLineNotFoundError(DomainError): ...             # 404
class BudgetLineAlreadyExistsError(DomainError): ...        # 409 — duplicate (category_id, fiscal_year)
class FinancialTransactionNotFoundError(DomainError): ...   # 404
class FinanceAccessForbiddenError(DomainError): ...          # 403
class InvalidInvoiceFormatError(DomainError): ...            # 422 — mime_type != application/pdf
class InvoiceFileTooLargeError(DomainError): ...             # 413 — exceeds 10MB
```
All registered in `app/core/exception_handlers.py` following the existing status-code mapping pattern used for `ProjectNotFoundError`, `ForbiddenError`, etc.

### 5. Service Layer (`backend/app/services/finance_service.py`)

Static-method class `FinanceService`, mirroring the `ProjectService` convention from T007:

- `list_categories(session, type_filter=None, include_inactive=False) -> list[FinanceCategory]`
- `create_category(session, category_in) -> FinanceCategory` — raises on duplicate `(name, type)`.
- `update_category(session, category_id, category_in) -> FinanceCategory` — rename and/or toggle `is_active`; no delete endpoint (soft-deactivate only, consistent with `Category.is_active` for tasks).
- `list_budget_lines(session, fiscal_year) -> list[BudgetLine]`
- `create_budget_line(session, budget_in) -> BudgetLine` — validates category exists and is active; raises `BudgetLineAlreadyExistsError` on duplicate `(category_id, fiscal_year)`.
- `update_budget_line(session, budget_line_id, budget_in) -> BudgetLine`
- `delete_budget_line(session, budget_line_id) -> None`
- `list_transactions(session, type_filter, category_id, start_date, end_date, skip, limit) -> tuple[list[FinancialTransaction], int]` — ordered by `transaction_date DESC`.
- `create_transaction(session, created_by_id, transaction_in) -> FinancialTransaction` — fetches category, raises `FinanceCategoryTypeMismatchError` if `transaction_in.type != category.type`; sets `created_by_id`.
- `get_transaction_by_id(session, transaction_id) -> FinancialTransaction` — raises `FinancialTransactionNotFoundError`.
- `update_transaction(session, transaction, transaction_in) -> FinancialTransaction` — applies non-None fields; re-validates type/category match if either changes.
- `delete_transaction(session, transaction) -> None` — if `transaction.invoice_file_path` is set, calls `storage_service.LocalStorageProvider.delete_file(transaction.invoice_file_path)` before deleting the row (`delete_file` takes the internal path, not `invoice_file_url`).
- `upload_invoice(session, transaction, file_bytes, filename, mime_type) -> FinancialTransaction`:
  - Rejects non-`application/pdf` MIME types with `InvalidInvoiceFormatError`.
  - Rejects files over `10 * 1024 * 1024` bytes with `InvoiceFileTooLargeError` (same 10MB ceiling as `AnnouncementMediaTooLargeError`).
  - If `transaction.invoice_file_path` is already set, calls `delete_file(transaction.invoice_file_path)` to remove the previously-attached file.
  - Saves the new file via `storage_service.LocalStorageProvider.save_file()` (same abstraction used by `media_service`/announcements), which returns `(internal_file_path, public_url)`; sets `invoice_file_path = internal_file_path`, `invoice_file_url = public_url`, plus `invoice_file_size_bytes` / `invoice_mime_type`.
- `delete_invoice(session, transaction) -> FinancialTransaction` — calls `delete_file(transaction.invoice_file_path)` and clears all four invoice fields (`invoice_file_path`, `invoice_file_url`, `invoice_file_size_bytes`, `invoice_mime_type`).
- `get_cash_balance(session, as_of: date | None) -> CashBalanceRead` — `as_of` defaults to today; sums `INCOME` and `EXPENSE` transactions with `transaction_date <= as_of`; `balance = total_income - total_expense`.
- `get_statement(session, start_date, end_date) -> FinancialStatementRead`:
  - `opening_balance` = `get_cash_balance(as_of = start_date - 1 day).balance`.
  - Groups transactions within `[start_date, end_date]` by `(year, month)`, computing `income`, `expense`, `net = income - expense` per month, and a `running_balance` that accumulates from `opening_balance` month over month. Months with no transactions still appear with zeros.
- `get_budget_vs_actual(session, fiscal_year) -> BudgetVsActualRead`:
  - Left-joins all `BudgetLine` rows for `fiscal_year` with their `FinanceCategory`.
  - For each category with a budget line (and, additionally, any category with transactions in that year but no budget line — reported with `planned_amount = 0`), computes `executed_amount = SUM(amount)` and `transaction_count = COUNT(*)` from `FinancialTransaction` where `category_id` matches and `extract(year, transaction_date) == fiscal_year`.
  - `variance_amount = executed_amount - planned_amount`; `variance_pct = variance_amount / planned_amount * 100` if `planned_amount > 0` else `None`.
- `list_category_transactions(session, category_id, fiscal_year, skip, limit) -> tuple[list[FinancialTransaction], int]` — the drill-down query backing the budget-vs-actual table's expandable rows; filtered to the given category and fiscal year, ordered by `transaction_date DESC`.

### 6. Endpoint & Security Layer (`backend/app/api/v1/endpoints/finance.py`)

Role-guard helper sets, mirroring `projects.py`:

```python
_FINANCE_READ_ROLES = {UserRole.ADMINISTRATOR, UserRole.DIRECTOR, UserRole.MANAGER, UserRole.RESIDENT}
_FINANCE_ADMIN_ROLES = {UserRole.ADMINISTRATOR, UserRole.DIRECTOR}
_FINANCE_WRITE_ROLES = {UserRole.ADMINISTRATOR, UserRole.DIRECTOR, UserRole.MANAGER}
```

- `_require_read_permission`, `_require_admin_permission`, `_require_write_permission` raise `FinanceAccessForbiddenError` (→ `403`) when the role isn't in the corresponding set.
- `_require_transaction_edit_permission(current_user, transaction)`: Admin/Director may edit or delete-invoice on any transaction; Manager may only act on a transaction where `transaction.created_by_id == current_user.id`; otherwise raises `FinanceAccessForbiddenError`.

Routes (all under `/api/v1/finance`, all requiring `get_current_user`):

| Method & Path | Roles | Notes |
|---|---|---|
| `GET /categories` | read roles | `?type=&include_inactive=` (inactive list restricted to admin roles) |
| `POST /categories` | admin roles | `201` |
| `PUT /categories/{id}` | admin roles | rename / toggle `is_active` |
| `GET /budget-lines?fiscal_year=` | read roles | |
| `POST /budget-lines` | admin roles | `201`, `409` on duplicate |
| `PUT /budget-lines/{id}` | admin roles | |
| `DELETE /budget-lines/{id}` | admin roles | `204` |
| `GET /transactions` | read roles | `?type=&category_id=&start_date=&end_date=&skip=&limit=` |
| `POST /transactions` | write roles | `201` |
| `GET /transactions/{id}` | read roles | |
| `PUT /transactions/{id}` | write roles + ownership rule | |
| `DELETE /transactions/{id}` | admin roles only | `204` |
| `POST /transactions/{id}/invoice` | write roles + ownership rule | multipart `UploadFile`, PDF only, ≤10MB |
| `DELETE /transactions/{id}/invoice` | write roles + ownership rule | `204` |
| `GET /balance?as_of=` | read roles | defaults to today |
| `GET /statement?start_date=&end_date=` | read roles | |
| `GET /budget-vs-actual?fiscal_year=` | read roles | |
| `GET /budget-vs-actual/{category_id}/transactions?fiscal_year=&skip=&limit=` | read roles | drill-down list backing the "1-click" PDF preview |

### 7. "1-click" Invoice PDF Drill-Down Mechanism

- `FinancialTransactionRead` (returned by both the transaction list and the drill-down endpoint) already embeds `invoice_file_url` when present — the frontend never needs a second round-trip to know whether/where an invoice exists.
- Invoice files are served statically from `/static/uploads/{year}/{month}/{uuid}.pdf` via the existing `app.mount("/static/uploads", StaticFiles(...))` in `main.py` (same mechanism used for photo/media uploads) — no new static-serving code needed.
- On the `BudgetVsActualTable`, clicking a category row expands it (via `list_category_transactions`) into its transaction list; each transaction with a non-null `invoice_file_url` renders a PDF icon button. **A single click on that icon opens `InvoicePreviewModal`**, which renders `<iframe src={invoice_file_url}>` immediately (the URL is already loaded in memory) plus a "Baixar" (download) link — no extra confirmation dialog or additional fetch, satisfying the "1-click drill-down" requirement.
- Transactions without an invoice show a disabled/greyed icon with a tooltip ("Nenhuma nota fiscal anexada").

### 8. Database Migration

- New Alembic revision (`00XX_add_finance_tables.py`) creating `finance_category`, `budget_line`, and `financial_transaction` tables, the `TransactionType` Postgres enum (registering it the same way `0014_add_resident_userrole.py` extended the `userrole` enum — i.e. a plain `sa.Enum` created via `op.execute`/`sa.Enum(...).create(...)` bound at migration time, not relying on SQLAlchemy's implicit auto-create), unique constraints, FKs (`ON DELETE RESTRICT` for `category_id` and `created_by_id`), and the composite indexes described above.
- The `financial_transaction` table must include the `invoice_file_path` column (nullable `String`, alongside `invoice_file_url`, `invoice_file_size_bytes`, `invoice_mime_type`) — this is the internal storage path required by `storage_service.LocalStorageProvider.delete_file()`; omitting it (as `AnnouncementMedia`/`MediaAsset` do not) would make invoice deletion on this table impossible.

### 9. Frontend Layer (`frontend/src/features/finance/`)

1. **Types** (`frontend/src/types/finance.ts`): `TransactionType`, `FinanceCategory`, `BudgetLine`, `FinancialTransaction`, `CashBalance`, `FinancialStatement`, `MonthlyStatementEntry`, `BudgetVsActualRow`, `BudgetVsActual`, plus `*CreatePayload`/`*UpdatePayload` types.
2. **API Client** (`frontend/src/api/finance.ts`): thin Axios wrappers for every endpoint above, including `uploadInvoice(transactionId, file)` using `FormData`.
3. **React Hooks** (`frontend/src/hooks/useFinance.ts`): `useCategories`, `useBudgetLines(year)`, `useTransactions(filters)`, `useCashBalance(asOf)`, `useStatement(range)`, `useBudgetVsActual(year)`, `useCategoryTransactions(categoryId, year)`, plus mutation hooks (`useCreateTransaction`, `useUpdateTransaction`, `useDeleteTransaction`, `useUploadInvoice`, `useDeleteInvoice`, `useCreateCategory`, `useCreateBudgetLine`, `useUpdateBudgetLine`, `useDeleteBudgetLine`) that invalidate the relevant query keys.
4. **Components** (`frontend/src/features/finance/components/`):
   - `FinanceDashboardPage.tsx`: page shell with fiscal-year selector, `CashBalanceCard`, `StatementChart`, and `BudgetVsActualTable`; "Nova Transação" / "Nova Categoria" / "Novo Orçamento" action buttons gated to write/admin roles.
   - `CashBalanceCard.tsx`: current balance, total income, total expense for the selected period.
   - `StatementChart.tsx` + `StatementTable.tsx`: monthly inflow/outflow bar chart and matching data table with running balance column.
   - `BudgetVsActualTable.tsx`: one row per category (planned, executed, variance, variance %, over-budget badge when `variance_amount > 0` on an `EXPENSE` category), expandable to a `CategoryTransactionDrilldown` sub-table.
   - `CategoryTransactionDrilldown.tsx`: paginated transaction list for the expanded category/year with the invoice PDF icon button described in §7.
   - `InvoicePreviewModal.tsx`: PDF iframe viewer + download link (structurally parallel to T009's `PDFViewerModal`, but a standalone component in this feature folder — no cross-feature import).
   - `TransactionFormModal.tsx`: create/edit transaction (type, category select filtered by type, amount, date, description, payment method) with an inline invoice file input.
   - `CategoryFormModal.tsx` / `BudgetLineFormModal.tsx`: admin-only forms for categories and budget lines.
5. **Routing & Navigation**: register `/finance` (`FinanceDashboardPage`) in `App.tsx` wrapped in `ProtectedRoute` (allowed: `ADMINISTRATOR`, `DIRECTOR`, `MANAGER`, `RESIDENT`); add "Financeiro" link to `Navbar.tsx`.
6. **i18n**: add keys under `finance.*` in `pt.json` and `en.json`.

---

## Expected Results

- [ ] Alembic migration creates `finance_category`, `budget_line`, and `financial_transaction` tables with the `TransactionType` enum, FKs (`ON DELETE RESTRICT`), the `(category_id, fiscal_year)` unique constraint, and the `(category_id, transaction_date)` / `(type, transaction_date)` indexes.
- [ ] `FinanceCategory`, `BudgetLine`, and `FinancialTransaction` SQLModels are defined with the fields and relationships specified above, including `financial_transaction.invoice_file_path` as a distinct nullable column from `invoice_file_url`.
- [ ] `GET /api/v1/finance/categories?include_inactive=true` returns `403` for `RESIDENT`/`MANAGER`/`GUEST` and succeeds for `ADMINISTRATOR`/`DIRECTOR`; `include_inactive` omitted or `false` behaves identically for all read roles.
- [ ] `POST /api/v1/finance/categories` and `POST /api/v1/finance/budget-lines` are restricted to `ADMINISTRATOR`/`DIRECTOR`; duplicate `(category_id, fiscal_year)` returns `409`.
- [ ] `POST /api/v1/finance/transactions` succeeds for `ADMINISTRATOR`, `DIRECTOR`, and `MANAGER`; rejects `RESIDENT`/`GUEST` with `403`; rejects a `type` that doesn't match the target category's `type` with `422`.
- [ ] `PUT` / `DELETE /api/v1/finance/transactions/{id}`: `MANAGER` can only edit transactions they created (attempting to edit another user's transaction returns `403`); only `ADMINISTRATOR`/`DIRECTOR` can delete any transaction.
- [ ] `GET /api/v1/finance/balance` returns `{as_of_date, total_income, total_expense, balance}` correctly computed from all transactions up to (and including) the given date, accessible to all authenticated non-`GUEST` roles.
- [ ] `GET /api/v1/finance/statement?start_date=&end_date=` returns monthly `income`/`expense`/`net`/`running_balance` entries that reconcile: `closing_balance == get_cash_balance(end_date).balance`.
- [ ] `GET /api/v1/finance/budget-vs-actual?fiscal_year=` returns one row per category with `planned_amount`, `executed_amount` computed live from transactions (never a stored/stale value), `variance_amount`, and `variance_pct`.
- [ ] `GET /api/v1/finance/budget-vs-actual/{category_id}/transactions?fiscal_year=` returns the paginated transaction list backing the drill-down, each including `invoice_file_url` when an invoice is attached.
- [ ] `POST /api/v1/finance/transactions/{id}/invoice` accepts only `application/pdf` (`422` otherwise) and rejects files over 10MB (`413`); the returned transaction's `invoice_file_url` is reachable via the app's `/static/uploads/...` mount, and the stored row's `invoice_file_path` matches the internal path on disk (not exposed in the API response).
- [ ] `DELETE /api/v1/finance/transactions/{id}/invoice` calls `storage_service.LocalStorageProvider.delete_file()` with `invoice_file_path`, removes the file from disk, and clears all four invoice fields (`invoice_file_path`, `invoice_file_url`, `invoice_file_size_bytes`, `invoice_mime_type`).
- [ ] `DELETE /api/v1/finance/transactions/{id}` on a transaction with an attached invoice removes the invoice file from disk (via `invoice_file_path`) in addition to deleting the transaction row.
- [ ] `GUEST` requests to any `/api/v1/finance/*` endpoint return `403 Forbidden`; unauthenticated requests return `401 Unauthorized`.
- [ ] Non-existent category/budget-line/transaction IDs return structured `404` domain errors.
- [ ] Frontend route `/finance` renders `FinanceDashboardPage` with `CashBalanceCard`, `StatementChart`/`StatementTable`, and `BudgetVsActualTable`.
- [ ] Clicking a category row in `BudgetVsActualTable` expands `CategoryTransactionDrilldown`; clicking a transaction's invoice icon opens `InvoicePreviewModal` and renders the PDF in a single click (no intermediate confirmation step).
- [ ] `TransactionFormModal`, `CategoryFormModal`, and `BudgetLineFormModal` are only reachable/actionable for roles permitted to write (buttons hidden for `RESIDENT`/`GUEST`; `MANAGER` cannot see category/budget-line management actions).
- [ ] All user-facing UI text uses i18n keys in `pt.json` and `en.json`.
- [ ] Backend pytest suite (`backend/tests/test_finance.py`, `backend/tests/test_finance_rbac.py`) passes with ≥ 90% coverage for new models, services, and endpoints.
- [ ] Frontend vitest suite (`frontend/src/features/finance/__tests__/`) passes with ≥ 75% coverage for new components and hooks.

---

## Out of Scope

- Per-unit (lot) billing, condo-fee invoicing/delinquency tracking, and accounts receivable (separate future module; no `lot_id` on `FinancialTransaction`).
- Bank statement (OFX) import/reconciliation and third-party accounting/ERP integration.
- Multi-currency support.
- Recurring/scheduled transaction automation.
- Multi-year budget planning workflows or budget approval/versioning (a `BudgetLine` is a single flat planned amount per category/year).
- Linking transactions to Document Center (`AssociationDocument`) records; invoices are stored as simple file fields directly on `FinancialTransaction` for this task.
