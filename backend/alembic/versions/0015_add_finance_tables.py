"""add_finance_tables

Revision ID: 0015_add_finance_tables
Revises: 0014_add_resident_userrole
Create Date: 2026-08-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0015_add_finance_tables"
down_revision: Union[str, Sequence[str], None] = "0014_add_resident_userrole"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# The `transactiontype` Postgres enum is shared by `finance_category.type` and
# `financial_transaction.type`. It is created explicitly (once) rather than
# relying on SQLAlchemy's implicit auto-create on the first `create_table()`
# call, since that implicit path would try to `CREATE TYPE` a second time
# when the second table is created and fail with a duplicate-type error.
transaction_type_enum = postgresql.ENUM(
    "INCOME", "EXPENSE", name="transactiontype", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    transaction_type_enum.create(bind, checkfirst=True)

    op.create_table(
        "finance_category",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("type", transaction_type_enum, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", "type", name="uq_finance_category_name_type"),
    )
    op.create_index("ix_finance_category_name", "finance_category", ["name"])
    op.create_index("ix_finance_category_type", "finance_category", ["type"])

    op.create_table(
        "budget_line",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "category_id",
            sa.Uuid(),
            sa.ForeignKey("finance_category.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("fiscal_year", sa.Integer(), nullable=False),
        sa.Column("planned_amount", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "category_id", "fiscal_year", name="uq_budget_line_category_year"
        ),
    )
    op.create_index("ix_budget_line_category_id", "budget_line", ["category_id"])
    op.create_index("ix_budget_line_fiscal_year", "budget_line", ["fiscal_year"])

    op.create_table(
        "financial_transaction",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("type", transaction_type_enum, nullable=False),
        sa.Column(
            "category_id",
            sa.Uuid(),
            sa.ForeignKey("finance_category.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("payment_method", sa.String(), nullable=True),
        sa.Column("invoice_file_path", sa.String(), nullable=True),
        sa.Column("invoice_file_url", sa.String(), nullable=True),
        sa.Column("invoice_file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("invoice_mime_type", sa.String(), nullable=True),
        sa.Column(
            "created_by_id",
            sa.Uuid(),
            sa.ForeignKey("user.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_financial_transaction_type", "financial_transaction", ["type"]
    )
    op.create_index(
        "ix_financial_transaction_category_id",
        "financial_transaction",
        ["category_id"],
    )
    op.create_index(
        "ix_financial_transaction_transaction_date",
        "financial_transaction",
        ["transaction_date"],
    )
    op.create_index(
        "ix_financial_transaction_created_by_id",
        "financial_transaction",
        ["created_by_id"],
    )
    op.create_index(
        "ix_financial_transaction_category_date",
        "financial_transaction",
        ["category_id", "transaction_date"],
    )
    op.create_index(
        "ix_financial_transaction_type_date",
        "financial_transaction",
        ["type", "transaction_date"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_financial_transaction_type_date", table_name="financial_transaction"
    )
    op.drop_index(
        "ix_financial_transaction_category_date", table_name="financial_transaction"
    )
    op.drop_index(
        "ix_financial_transaction_created_by_id", table_name="financial_transaction"
    )
    op.drop_index(
        "ix_financial_transaction_transaction_date",
        table_name="financial_transaction",
    )
    op.drop_index(
        "ix_financial_transaction_category_id", table_name="financial_transaction"
    )
    op.drop_index("ix_financial_transaction_type", table_name="financial_transaction")
    op.drop_table("financial_transaction")

    op.drop_index("ix_budget_line_fiscal_year", table_name="budget_line")
    op.drop_index("ix_budget_line_category_id", table_name="budget_line")
    op.drop_table("budget_line")

    op.drop_index("ix_finance_category_type", table_name="finance_category")
    op.drop_index("ix_finance_category_name", table_name="finance_category")
    op.drop_table("finance_category")

    bind = op.get_bind()
    transaction_type_enum.drop(bind, checkfirst=True)
