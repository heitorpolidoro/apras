"""add_access_control_tables

Revision ID: 0012_add_access_control_tables
Revises: 0011_add_media_asset_table
Create Date: 2026-08-26 00:10:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0012_add_access_control_tables"
down_revision: Union[str, Sequence[str], None] = "0011_add_media_asset_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "access_device",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("location", sa.String(), nullable=True),
        sa.Column("device_key", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="OFFLINE"),
        sa.Column("last_seen_at", sa.DateTime(), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_access_device_name"),
        sa.UniqueConstraint("device_key", name="uq_access_device_device_key"),
    )
    op.create_index("ix_access_device_name", "access_device", ["name"])
    op.create_index("ix_access_device_device_key", "access_device", ["device_key"])
    op.create_index("ix_access_device_status", "access_device", ["status"])
    op.create_index("ix_access_device_created_by_id", "access_device", ["created_by_id"])

    op.create_table(
        "facial_template",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("resident_id", sa.Uuid(), sa.ForeignKey("resident.id", ondelete="CASCADE"), nullable=False),
        sa.Column("media_asset_id", sa.Uuid(), sa.ForeignKey("media_asset.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sync_status", sa.String(), nullable=False, server_default="PENDING"),
        sa.Column("synced_at", sa.DateTime(), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("resident_id", name="uq_facial_template_resident_id"),
    )
    op.create_index("ix_facial_template_resident_id", "facial_template", ["resident_id"])
    op.create_index("ix_facial_template_sync_status", "facial_template", ["sync_status"])

    op.create_table(
        "facial_access_event",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.Uuid(), sa.ForeignKey("access_device.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resident_id", sa.Uuid(), sa.ForeignKey("resident.id", ondelete="SET NULL"), nullable=True),
        sa.Column("matched", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("access_granted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("event_time", sa.DateTime(), nullable=False),
        sa.Column("raw_payload", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_facial_access_event_device_id", "facial_access_event", ["device_id"])
    op.create_index("ix_facial_access_event_resident_id", "facial_access_event", ["resident_id"])
    op.create_index("ix_facial_access_event_event_time", "facial_access_event", ["event_time"])


def downgrade() -> None:
    op.drop_index("ix_facial_access_event_event_time", table_name="facial_access_event")
    op.drop_index("ix_facial_access_event_resident_id", table_name="facial_access_event")
    op.drop_index("ix_facial_access_event_device_id", table_name="facial_access_event")
    op.drop_table("facial_access_event")

    op.drop_index("ix_facial_template_sync_status", table_name="facial_template")
    op.drop_index("ix_facial_template_resident_id", table_name="facial_template")
    op.drop_table("facial_template")

    op.drop_index("ix_access_device_created_by_id", table_name="access_device")
    op.drop_index("ix_access_device_status", table_name="access_device")
    op.drop_index("ix_access_device_device_key", table_name="access_device")
    op.drop_index("ix_access_device_name", table_name="access_device")
    op.drop_table("access_device")
