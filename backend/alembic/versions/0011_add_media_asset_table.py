"""add_media_asset_table

Revision ID: 0011_add_media_asset_table
Revises: 0010_add_document_tables
Create Date: 2026-08-25 16:40:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0011_add_media_asset_table"
down_revision: Union[str, Sequence[str], None] = "0010_add_document_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "media_asset",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("storage_provider", sa.String(), nullable=False, server_default="LOCAL_DISK"),
        sa.Column("file_path", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("thumbnail_url", sa.String(), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("mime_type", sa.String(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="PENDING_APPROVAL"),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("uploaded_by_id", sa.Uuid(), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False),
        sa.Column("approved_by_id", sa.Uuid(), sa.ForeignKey("user.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_media_asset_entity_type", "media_asset", ["entity_type"])
    op.create_index("ix_media_asset_entity_id", "media_asset", ["entity_id"])
    op.create_index("ix_media_asset_entity_type_id", "media_asset", ["entity_type", "entity_id"])
    op.create_index("ix_media_asset_status", "media_asset", ["status"])
    op.create_index("ix_media_asset_uploaded_by_id", "media_asset", ["uploaded_by_id"])


def downgrade() -> None:
    op.drop_index("ix_media_asset_uploaded_by_id", table_name="media_asset")
    op.drop_index("ix_media_asset_status", table_name="media_asset")
    op.drop_index("ix_media_asset_entity_type_id", table_name="media_asset")
    op.drop_index("ix_media_asset_entity_id", table_name="media_asset")
    op.drop_index("ix_media_asset_entity_type", table_name="media_asset")
    op.drop_table("media_asset")
