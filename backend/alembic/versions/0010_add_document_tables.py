"""add_document_tables

Revision ID: 0010_add_document_tables
Revises: 0009_add_occurrence_tables
Create Date: 2026-08-25 16:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0010_add_document_tables"
down_revision: Union[str, Sequence[str], None] = "0009_add_occurrence_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "document_folder",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column(
            "allowed_roles_json",
            sa.String(),
            nullable=False,
            server_default='["ADMINISTRATOR", "DIRECTOR", "MANAGER", "RESIDENT"]',
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["parent_id"], ["document_folder.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_document_folder_name", "document_folder", ["name"])
    op.create_index("ix_document_folder_parent_id", "document_folder", ["parent_id"])

    op.create_table(
        "association_document",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("folder_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("file_url", sa.String(), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("mime_type", sa.String(), nullable=False, server_default="application/pdf"),
        sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("previous_version_id", sa.Uuid(), nullable=True),
        sa.Column("publication_year", sa.Integer(), nullable=True),
        sa.Column("publication_month", sa.Integer(), nullable=True),
        sa.Column("tags_json", sa.Text(), nullable=True),
        sa.Column("uploaded_by_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["folder_id"], ["document_folder.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["previous_version_id"], ["association_document.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["uploaded_by_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_association_document_folder_id", "association_document", ["folder_id"])
    op.create_index("ix_association_document_title", "association_document", ["title"])
    op.create_index("ix_association_document_previous_version_id", "association_document", ["previous_version_id"])
    op.create_index("ix_association_document_publication_year", "association_document", ["publication_year"])
    op.create_index("ix_association_document_publication_month", "association_document", ["publication_month"])
    op.create_index("ix_association_document_uploaded_by_id", "association_document", ["uploaded_by_id"])
    op.create_index("ix_assoc_doc_folder_created", "association_document", ["folder_id", "created_at"])
    op.create_index("ix_assoc_doc_pub_year_month", "association_document", ["publication_year", "publication_month"])

    op.create_table(
        "document_download_log",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("downloaded_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_id"], ["association_document.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_document_download_log_document_id", "document_download_log", ["document_id"])
    op.create_index("ix_document_download_log_user_id", "document_download_log", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_document_download_log_user_id", table_name="document_download_log")
    op.drop_index("ix_document_download_log_document_id", table_name="document_download_log")
    op.drop_table("document_download_log")

    op.drop_index("ix_assoc_doc_pub_year_month", table_name="association_document")
    op.drop_index("ix_assoc_doc_folder_created", table_name="association_document")
    op.drop_index("ix_association_document_uploaded_by_id", table_name="association_document")
    op.drop_index("ix_association_document_publication_month", table_name="association_document")
    op.drop_index("ix_association_document_publication_year", table_name="association_document")
    op.drop_index("ix_association_document_previous_version_id", table_name="association_document")
    op.drop_index("ix_association_document_title", table_name="association_document")
    op.drop_index("ix_association_document_folder_id", table_name="association_document")
    op.drop_table("association_document")

    op.drop_index("ix_document_folder_parent_id", table_name="document_folder")
    op.drop_index("ix_document_folder_name", table_name="document_folder")
    op.drop_table("document_folder")
