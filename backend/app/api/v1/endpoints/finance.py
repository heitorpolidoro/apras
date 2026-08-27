"""API endpoints for the Association Financial Area & Dashboard (APRAS-22)."""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlmodel import Session

from app.api import deps as api_deps
from app.core.exceptions import FinanceAccessForbiddenError
from app.db import get_session
from app.models.enums import TransactionType, UserRole
from app.models.finance import FinancialTransaction
from app.models.user import User
from app.schemas.finance import (
    BudgetLineCreate,
    BudgetLineRead,
    BudgetLineUpdate,
    BudgetVsActualRead,
    CashBalanceRead,
    FinanceCategoryCreate,
    FinanceCategoryRead,
    FinanceCategoryUpdate,
    FinancialStatementRead,
    FinancialTransactionCreate,
    FinancialTransactionRead,
    FinancialTransactionUpdate,
    PaginatedTransactions,
)
from app.services.finance_service import FinanceService

router = APIRouter()

_FINANCE_READ_ROLES = {
    UserRole.ADMINISTRATOR,
    UserRole.DIRECTOR,
    UserRole.MANAGER,
    UserRole.RESIDENT,
}
_FINANCE_ADMIN_ROLES = {UserRole.ADMINISTRATOR, UserRole.DIRECTOR}
_FINANCE_WRITE_ROLES = {
    UserRole.ADMINISTRATOR,
    UserRole.DIRECTOR,
    UserRole.MANAGER,
}


def _require_read_permission(current_user: User) -> None:
    if current_user.role not in _FINANCE_READ_ROLES:
        raise FinanceAccessForbiddenError("Access denied to the finance module")


def _require_admin_permission(current_user: User) -> None:
    if current_user.role not in _FINANCE_ADMIN_ROLES:
        raise FinanceAccessForbiddenError(
            "Only ADMINISTRATOR and DIRECTOR can perform this action"
        )


def _require_write_permission(current_user: User) -> None:
    if current_user.role not in _FINANCE_WRITE_ROLES:
        raise FinanceAccessForbiddenError(
            "Not enough privileges to create financial transactions"
        )


def _require_transaction_edit_permission(
    current_user: User, transaction: FinancialTransaction
) -> None:
    if current_user.role in _FINANCE_ADMIN_ROLES:
        return
    if (
        current_user.role == UserRole.MANAGER
        and transaction.created_by_id == current_user.id
    ):
        return
    raise FinanceAccessForbiddenError(
        "You can only edit or manage invoices on transactions you created"
    )


# -----------------------------------------------------------------------------
# Category Endpoints
# -----------------------------------------------------------------------------


@router.get("/categories", response_model=list[FinanceCategoryRead])
def list_categories(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
    type: TransactionType | None = Query(default=None),  # noqa: A002
    include_inactive: bool = Query(default=False),
) -> list[FinanceCategoryRead]:
    """Lists finance categories (inactive list restricted to admin roles)."""
    _require_read_permission(current_user)
    if include_inactive:
        _require_admin_permission(current_user)
    categories = FinanceService.list_categories(
        session=session, type_filter=type, include_inactive=include_inactive
    )
    return [FinanceCategoryRead.model_validate(c) for c in categories]


@router.post(
    "/categories", response_model=FinanceCategoryRead, status_code=status.HTTP_201_CREATED
)
def create_category(
    category_in: FinanceCategoryCreate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> FinanceCategoryRead:
    """Creates a finance category (Admin/Director only)."""
    _require_admin_permission(current_user)
    category = FinanceService.create_category(session, category_in)
    return FinanceCategoryRead.model_validate(category)


@router.put("/categories/{id}", response_model=FinanceCategoryRead)
def update_category(
    id: UUID,
    category_in: FinanceCategoryUpdate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> FinanceCategoryRead:
    """Renames and/or toggles a finance category (Admin/Director only)."""
    _require_admin_permission(current_user)
    category = FinanceService.update_category(session, id, category_in)
    return FinanceCategoryRead.model_validate(category)


# -----------------------------------------------------------------------------
# Budget Line Endpoints
# -----------------------------------------------------------------------------


@router.get("/budget-lines", response_model=list[BudgetLineRead])
def list_budget_lines(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
    fiscal_year: int = Query(...),
) -> list[BudgetLineRead]:
    """Lists budget lines for a fiscal year."""
    _require_read_permission(current_user)
    budget_lines = FinanceService.list_budget_lines(session, fiscal_year)
    return [FinanceService.format_budget_line_read(bl) for bl in budget_lines]


@router.post(
    "/budget-lines", response_model=BudgetLineRead, status_code=status.HTTP_201_CREATED
)
def create_budget_line(
    budget_in: BudgetLineCreate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> BudgetLineRead:
    """Creates a budget line (Admin/Director only)."""
    _require_admin_permission(current_user)
    budget_line = FinanceService.create_budget_line(session, budget_in)
    return FinanceService.format_budget_line_read(budget_line)


@router.put("/budget-lines/{id}", response_model=BudgetLineRead)
def update_budget_line(
    id: UUID,
    budget_in: BudgetLineUpdate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> BudgetLineRead:
    """Updates a budget line's planned amount and/or notes (Admin/Director only)."""
    _require_admin_permission(current_user)
    budget_line = FinanceService.update_budget_line(session, id, budget_in)
    return FinanceService.format_budget_line_read(budget_line)


@router.delete("/budget-lines/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget_line(
    id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> None:
    """Deletes a budget line (Admin/Director only)."""
    _require_admin_permission(current_user)
    FinanceService.delete_budget_line(session, id)


# -----------------------------------------------------------------------------
# Transaction Endpoints
# -----------------------------------------------------------------------------


@router.get("/transactions", response_model=PaginatedTransactions)
def list_transactions(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
    type: TransactionType | None = Query(default=None),  # noqa: A002
    category_id: UUID | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> PaginatedTransactions:
    """Lists financial transactions with optional filters and pagination."""
    _require_read_permission(current_user)
    items, total = FinanceService.list_transactions(
        session=session,
        type_filter=type,
        category_id=category_id,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit,
    )
    return PaginatedTransactions(
        items=[FinanceService.format_transaction_read(session, t) for t in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post(
    "/transactions",
    response_model=FinancialTransactionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_transaction(
    transaction_in: FinancialTransactionCreate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> FinancialTransactionRead:
    """Creates a financial transaction (Admin/Director/Manager only)."""
    _require_write_permission(current_user)
    transaction = FinanceService.create_transaction(
        session, current_user.id, transaction_in
    )
    return FinanceService.format_transaction_read(session, transaction)


@router.get("/transactions/{id}", response_model=FinancialTransactionRead)
def get_transaction(
    id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> FinancialTransactionRead:
    """Retrieves a single financial transaction."""
    _require_read_permission(current_user)
    transaction = FinanceService.get_transaction_by_id(session, id)
    return FinanceService.format_transaction_read(session, transaction)


@router.put("/transactions/{id}", response_model=FinancialTransactionRead)
def update_transaction(
    id: UUID,
    transaction_in: FinancialTransactionUpdate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> FinancialTransactionRead:
    """Updates a financial transaction (write roles + ownership rule for Manager)."""
    _require_write_permission(current_user)
    transaction = FinanceService.get_transaction_by_id(session, id)
    _require_transaction_edit_permission(current_user, transaction)
    updated = FinanceService.update_transaction(session, transaction, transaction_in)
    return FinanceService.format_transaction_read(session, updated)


@router.delete("/transactions/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> None:
    """Deletes a financial transaction and its invoice, if any (Admin/Director only)."""
    _require_admin_permission(current_user)
    transaction = FinanceService.get_transaction_by_id(session, id)
    FinanceService.delete_transaction(session, transaction)


@router.post("/transactions/{id}/invoice", response_model=FinancialTransactionRead)
async def upload_invoice(
    id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
    file: UploadFile = File(...),
) -> FinancialTransactionRead:
    """Uploads/replaces the PDF invoice on a transaction (write roles + ownership)."""
    _require_write_permission(current_user)
    transaction = FinanceService.get_transaction_by_id(session, id)
    _require_transaction_edit_permission(current_user, transaction)

    file_bytes = await file.read()
    filename = file.filename or "invoice.pdf"
    mime_type = file.content_type or "application/octet-stream"

    updated = FinanceService.upload_invoice(
        session=session,
        transaction=transaction,
        file_bytes=file_bytes,
        filename=filename,
        mime_type=mime_type,
    )
    return FinanceService.format_transaction_read(session, updated)


@router.delete("/transactions/{id}/invoice", status_code=status.HTTP_204_NO_CONTENT)
def delete_invoice(
    id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
) -> None:
    """Removes the invoice attached to a transaction (write roles + ownership)."""
    _require_write_permission(current_user)
    transaction = FinanceService.get_transaction_by_id(session, id)
    _require_transaction_edit_permission(current_user, transaction)
    FinanceService.delete_invoice(session, transaction)


# -----------------------------------------------------------------------------
# Reporting Endpoints
# -----------------------------------------------------------------------------


@router.get("/balance", response_model=CashBalanceRead)
def get_balance(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
    as_of: date | None = Query(default=None),
) -> CashBalanceRead:
    """Returns the cash balance as of a given date (defaults to today)."""
    _require_read_permission(current_user)
    return FinanceService.get_cash_balance(session, as_of)


@router.get("/statement", response_model=FinancialStatementRead)
def get_statement(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
    start_date: date = Query(...),
    end_date: date = Query(...),
) -> FinancialStatementRead:
    """Returns the monthly cash inflows/outflows statement for a date range."""
    _require_read_permission(current_user)
    return FinanceService.get_statement(session, start_date, end_date)


@router.get("/budget-vs-actual", response_model=BudgetVsActualRead)
def get_budget_vs_actual(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
    fiscal_year: int = Query(...),
) -> BudgetVsActualRead:
    """Returns the budget-vs-actual execution table for a fiscal year."""
    _require_read_permission(current_user)
    return FinanceService.get_budget_vs_actual(session, fiscal_year)


@router.get(
    "/budget-vs-actual/{category_id}/transactions",
    response_model=PaginatedTransactions,
)
def get_category_transactions(
    category_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
    fiscal_year: int = Query(...),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> PaginatedTransactions:
    """Returns the paginated drill-down transaction list for a category/year."""
    _require_read_permission(current_user)
    items, total = FinanceService.list_category_transactions(
        session=session,
        category_id=category_id,
        fiscal_year=fiscal_year,
        skip=skip,
        limit=limit,
    )
    return PaginatedTransactions(
        items=[FinanceService.format_transaction_read(session, t) for t in items],
        total=total,
        skip=skip,
        limit=limit,
    )
