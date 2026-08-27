"""add_announcement_tables

Revision ID: 0013_add_announcement_tables
Revises: 0012_add_access_control_tables
Create Date: 2026-08-27 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0013_add_announcement_tables"
down_revision: Union[str, Sequence[str], None] = "0012_add_access_control_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "announcement",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("author_id", sa.Uuid(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_announcement_title", "announcement", ["title"])
    op.create_index("ix_announcement_author_id", "announcement", ["author_id"])
    op.create_index("ix_announcement_is_deleted", "announcement", ["is_deleted"])
    op.create_index("ix_announcement_created_at", "announcement", ["created_at"])

    op.create_table(
        "announcement_media",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "announcement_id", sa.Uuid(), sa.ForeignKey("announcement.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("media_type", sa.String(), nullable=False),
        sa.Column("file_path", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("mime_type", sa.String(), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_announcement_media_announcement_id", "announcement_media", ["announcement_id"])
    op.create_index(
        "ix_announcement_media_announcement_id_created_at",
        "announcement_media",
        ["announcement_id", "created_at"],
    )

    op.create_table(
        "announcement_comment",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "announcement_id", sa.Uuid(), sa.ForeignKey("announcement.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_announcement_comment_announcement_id", "announcement_comment", ["announcement_id"])
    op.create_index("ix_announcement_comment_user_id", "announcement_comment", ["user_id"])
    op.create_index(
        "ix_announcement_comment_announcement_id_created_at",
        "announcement_comment",
        ["announcement_id", "created_at"],
    )

    op.create_table(
        "announcement_read_receipt",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "announcement_id", sa.Uuid(), sa.ForeignKey("announcement.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False),
        sa.Column("read_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("announcement_id", "user_id", name="uq_announcement_read_receipt_user"),
    )
    op.create_index("ix_announcement_read_receipt_announcement_id", "announcement_read_receipt", ["announcement_id"])
    op.create_index("ix_announcement_read_receipt_user_id", "announcement_read_receipt", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_announcement_read_receipt_user_id", table_name="announcement_read_receipt")
    op.drop_index("ix_announcement_read_receipt_announcement_id", table_name="announcement_read_receipt")
    op.drop_table("announcement_read_receipt")

    op.drop_index("ix_announcement_comment_announcement_id_created_at", table_name="announcement_comment")
    op.drop_index("ix_announcement_comment_user_id", table_name="announcement_comment")
    op.drop_index("ix_announcement_comment_announcement_id", table_name="announcement_comment")
    op.drop_table("announcement_comment")

    op.drop_index("ix_announcement_media_announcement_id_created_at", table_name="announcement_media")
    op.drop_index("ix_announcement_media_announcement_id", table_name="announcement_media")
    op.drop_table("announcement_media")

    op.drop_index("ix_announcement_created_at", table_name="announcement")
    op.drop_index("ix_announcement_is_deleted", table_name="announcement")
    op.drop_index("ix_announcement_author_id", table_name="announcement")
    op.drop_index("ix_announcement_title", table_name="announcement")
    op.drop_table("announcement")
