"""Financial models for the Association Financial Area & Dashboard (APRAS-22)."""

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Index, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

from app.models.enums import TransactionType

if TYPE_CHECKING:
    from app.models.user import User


class FinanceCategory(SQLModel, table=True):
    """A budget/accounting category (e.g. "Água", "Salários"), typed INCOME/EXPENSE."""

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
    transactions: list["FinancialTransaction"] = Relationship(
        back_populates="category"
    )


class BudgetLine(SQLModel, table=True):
    """The planned amount for one FinanceCategory in one fiscal year."""

    __tablename__ = "budget_line"
    __table_args__ = (
        UniqueConstraint(
            "category_id", "fiscal_year", name="uq_budget_line_category_year"
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    category_id: uuid.UUID = Field(
        foreign_key="finance_category.id",
        ondelete="RESTRICT",
        nullable=False,
        index=True,
    )
    fiscal_year: int = Field(nullable=False, index=True)
    planned_amount: float = Field(default=0.0, nullable=False)
    notes: str | None = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    category: FinanceCategory = Relationship(back_populates="budget_lines")


class FinancialTransaction(SQLModel, table=True):
    """A single recorded inflow or outflow against a FinanceCategory."""

    __tablename__ = "financial_transaction"
    __table_args__ = (
        Index(
            "ix_financial_transaction_category_date",
            "category_id",
            "transaction_date",
        ),
        Index(
            "ix_financial_transaction_type_date",
            "type",
            "transaction_date",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    type: TransactionType = Field(nullable=False, index=True)
    category_id: uuid.UUID = Field(
        foreign_key="finance_category.id",
        ondelete="RESTRICT",
        nullable=False,
        index=True,
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
