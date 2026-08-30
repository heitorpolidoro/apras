"""add purchase quotation tables (APRAS-37)

Revision ID: 0027_add_purchase_quotation
Revises: 0026_add_asset_and_inventory
Create Date: 2026-08-30

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0027_add_purchase_quotation"
down_revision: str | Sequence[str] | None = "0026_add_asset_and_inventory"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "purchase_request",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("general_notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="OPEN"),
        sa.Column("requested_by_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["requested_by_id"], ["user.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_purchase_request_title", "purchase_request", ["title"])
    op.create_index("ix_purchase_request_status", "purchase_request", ["status"])
    op.create_index("ix_purchase_request_requested_by_id", "purchase_request", ["requested_by_id"])
    op.create_index("ix_purchase_request_created_at", "purchase_request", ["created_at"])

    op.create_table(
        "purchase_quote",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("purchase_request_id", sa.Uuid(), nullable=False),
        sa.Column("supplier_name", sa.String(), nullable=False),
        sa.Column("supplier_contact", sa.String(), nullable=True),
        sa.Column("unit_price", sa.Float(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("extra_fields", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["purchase_request_id"], ["purchase_request.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["created_by_id"], ["user.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_purchase_quote_purchase_request_id", "purchase_quote", ["purchase_request_id"])
    op.create_index("ix_purchase_quote_supplier_name", "purchase_quote", ["supplier_name"])
    op.create_index("ix_purchase_quote_created_by_id", "purchase_quote", ["created_by_id"])

    op.create_table(
        "purchase_quote_decision",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("purchase_request_id", sa.Uuid(), nullable=False),
        sa.Column("quote_id", sa.Uuid(), nullable=False),
        sa.Column("justification", sa.Text(), nullable=False),
        sa.Column("decided_by_id", sa.Uuid(), nullable=False),
        sa.Column("decided_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["purchase_request_id"], ["purchase_request.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["quote_id"], ["purchase_quote.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["decided_by_id"], ["user.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_purchase_quote_decision_purchase_request_id",
        "purchase_quote_decision",
        ["purchase_request_id"],
    )
    op.create_index("ix_purchase_quote_decision_quote_id", "purchase_quote_decision", ["quote_id"])
    op.create_index(
        "ix_purchase_quote_decision_decided_by_id", "purchase_quote_decision", ["decided_by_id"]
    )
    op.create_index(
        "ix_purchase_quote_decision_decided_at", "purchase_quote_decision", ["decided_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_purchase_quote_decision_decided_at", table_name="purchase_quote_decision")
    op.drop_index("ix_purchase_quote_decision_decided_by_id", table_name="purchase_quote_decision")
    op.drop_index("ix_purchase_quote_decision_quote_id", table_name="purchase_quote_decision")
    op.drop_index(
        "ix_purchase_quote_decision_purchase_request_id", table_name="purchase_quote_decision"
    )
    op.drop_table("purchase_quote_decision")

    op.drop_index("ix_purchase_quote_created_by_id", table_name="purchase_quote")
    op.drop_index("ix_purchase_quote_supplier_name", table_name="purchase_quote")
    op.drop_index("ix_purchase_quote_purchase_request_id", table_name="purchase_quote")
    op.drop_table("purchase_quote")

    op.drop_index("ix_purchase_request_created_at", table_name="purchase_request")
    op.drop_index("ix_purchase_request_requested_by_id", table_name="purchase_request")
    op.drop_index("ix_purchase_request_status", table_name="purchase_request")
    op.drop_index("ix_purchase_request_title", table_name="purchase_request")
    op.drop_table("purchase_request")
