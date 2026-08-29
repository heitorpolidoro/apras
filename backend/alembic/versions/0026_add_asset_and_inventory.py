"""add asset and inventory tables (APRAS-34)

Revision ID: 0026_add_asset_and_inventory
Revises: 0025_add_voting_tables
Create Date: 2026-08-29

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0026_add_asset_and_inventory"
down_revision: str | Sequence[str] | None = "0025_add_voting_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "asset",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("serial_number", sa.String(), nullable=True),
        sa.Column("asset_tag", sa.String(), nullable=True),
        sa.Column("location", sa.String(), nullable=False),
        sa.Column("acquisition_date", sa.Date(), nullable=True),
        sa.Column("acquisition_value", sa.Float(), nullable=True),
        sa.Column("condition", sa.String(), nullable=False),
        sa.Column("is_consumable", sa.Boolean(), nullable=False),
        sa.Column("current_quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("min_quantity", sa.Integer(), nullable=True),
        sa.Column("unit_of_measure", sa.String(), nullable=True, server_default="un"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_tag", name="uq_asset_asset_tag"),
    )
    op.create_index("ix_asset_name", "asset", ["name"])
    op.create_index("ix_asset_category", "asset", ["category"])
    op.create_index("ix_asset_serial_number", "asset", ["serial_number"])
    op.create_index("ix_asset_asset_tag", "asset", ["asset_tag"])
    op.create_index("ix_asset_location", "asset", ["location"])
    op.create_index("ix_asset_condition", "asset", ["condition"])
    op.create_index("ix_asset_is_consumable", "asset", ["is_consumable"])

    op.create_table(
        "inventory_movement",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("movement_type", sa.String(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("previous_quantity", sa.Integer(), nullable=False),
        sa.Column("new_quantity", sa.Integer(), nullable=False),
        sa.Column("performed_by_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("document_number", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["asset.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["performed_by_id"], ["user.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_inventory_movement_asset_id", "inventory_movement", ["asset_id"])
    op.create_index("ix_inventory_movement_movement_type", "inventory_movement", ["movement_type"])
    op.create_index("ix_inventory_movement_performed_by_id", "inventory_movement", ["performed_by_id"])
    op.create_index("ix_inventory_movement_created_at", "inventory_movement", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_inventory_movement_created_at", table_name="inventory_movement")
    op.drop_index("ix_inventory_movement_performed_by_id", table_name="inventory_movement")
    op.drop_index("ix_inventory_movement_movement_type", table_name="inventory_movement")
    op.drop_index("ix_inventory_movement_asset_id", table_name="inventory_movement")
    op.drop_table("inventory_movement")

    op.drop_index("ix_asset_is_consumable", table_name="asset")
    op.drop_index("ix_asset_condition", table_name="asset")
    op.drop_index("ix_asset_location", table_name="asset")
    op.drop_index("ix_asset_asset_tag", table_name="asset")
    op.drop_index("ix_asset_serial_number", table_name="asset")
    op.drop_index("ix_asset_category", table_name="asset")
    op.drop_index("ix_asset_name", table_name="asset")
    op.drop_table("asset")
