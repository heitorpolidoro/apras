"""Pydantic schemas for the Association Financial Area & Dashboard (APRAS-22)."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import TransactionType


class FinanceCategoryCreate(BaseModel):
    """Schema for creating a finance category."""

    name: str = Field(..., min_length=1, max_length=255)
    type: TransactionType


class FinanceCategoryUpdate(BaseModel):
    """Schema for renaming and/or toggling a finance category."""

    name: str | None = Field(None, min_length=1, max_length=255)
    is_active: bool | None = None


class FinanceCategoryRead(BaseModel):
    """Schema for reading a finance category."""

    id: uuid.UUID
    name: str
    type: TransactionType
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BudgetLineCreate(BaseModel):
    """Schema for creating a budget line."""

    category_id: uuid.UUID
    fiscal_year: int = Field(..., ge=2000, le=2100)
    planned_amount: float = Field(..., ge=0.0)
    notes: str | None = None


class BudgetLineUpdate(BaseModel):
    """Schema for updating a budget line."""

    planned_amount: float | None = Field(None, ge=0.0)
    notes: str | None = None


class BudgetLineRead(BaseModel):
    """Schema for reading a budget line."""

    id: uuid.UUID
    category_id: uuid.UUID
    category_name: str
    category_type: TransactionType
    fiscal_year: int
    planned_amount: float
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FinancialTransactionCreate(BaseModel):
    """Schema for creating a financial transaction."""

    type: TransactionType
    category_id: uuid.UUID
    description: str = Field(..., min_length=1)
    amount: float = Field(..., gt=0.0)
    transaction_date: date
    payment_method: str | None = None


class FinancialTransactionUpdate(BaseModel):
    """Schema for updating a financial transaction."""

    type: TransactionType | None = None
    category_id: uuid.UUID | None = None
    description: str | None = Field(None, min_length=1)
    amount: float | None = Field(None, gt=0.0)
    transaction_date: date | None = None
    payment_method: str | None = None


class FinancialTransactionRead(BaseModel):
    """Schema for reading a financial transaction.

    Note: `invoice_file_path` is intentionally excluded — it is the internal
    storage path used by `LocalStorageProvider.delete_file()` and must never
    be exposed in API responses. Only `invoice_file_url` is public.
    """

    id: uuid.UUID
    type: TransactionType
    category_id: uuid.UUID
    category_name: str
    description: str
    amount: float
    transaction_date: date
    payment_method: str | None = None
    invoice_file_url: str | None = None
    invoice_file_size_bytes: int | None = None
    invoice_mime_type: str | None = None
    created_by_id: uuid.UUID
    created_by_name: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedTransactions(BaseModel):
    """Paginated list of financial transactions."""

    items: list[FinancialTransactionRead]
    total: int
    skip: int
    limit: int


class CashBalanceRead(BaseModel):
    """Schema for the cash balance summary."""

    as_of_date: date
    total_income: float
    total_expense: float
    balance: float


class MonthlyStatementEntry(BaseModel):
    """One monthly entry in the inflows/outflows statement."""

    year: int
    month: int
    income: float
    expense: float
    net: float
    running_balance: float


class FinancialStatementRead(BaseModel):
    """Schema for the cash inflows/outflows statement over a date range."""

    start_date: date
    end_date: date
    opening_balance: float
    closing_balance: float
    entries: list[MonthlyStatementEntry]


class BudgetVsActualRow(BaseModel):
    """One row of the budget-vs-actual execution table."""

    category_id: uuid.UUID
    category_name: str
    category_type: TransactionType
    planned_amount: float
    executed_amount: float
    variance_amount: float
    variance_pct: float | None = None
    transaction_count: int


class BudgetVsActualRead(BaseModel):
    """Schema for the budget-vs-actual execution table."""

    fiscal_year: int
    rows: list[BudgetVsActualRow]
    total_planned: float
    total_executed: float
