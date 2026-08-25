"""add_visitor_tables

Revision ID: 0008_add_visitor_tables
Revises: 0007_add_resident_table
Create Date: 2026-08-25 15:10:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0008_add_visitor_tables"
down_revision: Union[str, Sequence[str], None] = "0007_add_resident_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "visitor",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("cpf", sa.String(), nullable=True),
        sa.Column("rg", sa.String(), nullable=True),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("company_name", sa.String(), nullable=True),
        sa.Column("vehicle_plate", sa.String(), nullable=True),
        sa.Column("vehicle_model", sa.String(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_visitor_full_name"), "visitor", ["full_name"], unique=False)
    op.create_index(op.f("ix_visitor_cpf"), "visitor", ["cpf"], unique=False)
    op.create_index(op.f("ix_visitor_company_name"), "visitor", ["company_name"], unique=False)
    op.create_index(op.f("ix_visitor_vehicle_plate"), "visitor", ["vehicle_plate"], unique=False)

    op.create_table(
        "visitor_authorization",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("visitor_id", sa.Uuid(), nullable=False),
        sa.Column("lot_id", sa.Uuid(), nullable=False),
        sa.Column("authorizer_user_id", sa.Uuid(), nullable=False),
        sa.Column("auth_type", sa.String(), nullable=False, server_default="SINGLE"),
        sa.Column("allowed_days_json", sa.String(), nullable=False, server_default='["MON","TUE","WED","THU","FRI","SAT","SUN"]'),
        sa.Column("allowed_shifts_json", sa.String(), nullable=False, server_default='["MORNING","AFTERNOON","NIGHT","FULL_DAY"]'),
        sa.Column("valid_from", sa.DateTime(), nullable=True),
        sa.Column("valid_until", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="ACTIVE"),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["visitor_id"], ["visitor.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lot_id"], ["lot.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["authorizer_user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_visitor_authorization_visitor_id"), "visitor_authorization", ["visitor_id"], unique=False)
    op.create_index(op.f("ix_visitor_authorization_lot_id"), "visitor_authorization", ["lot_id"], unique=False)
    op.create_index(op.f("ix_visitor_authorization_authorizer_user_id"), "visitor_authorization", ["authorizer_user_id"], unique=False)
    op.create_index(op.f("ix_visitor_authorization_status"), "visitor_authorization", ["status"], unique=False)

    op.create_table(
        "access_log",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("authorization_id", sa.Uuid(), nullable=True),
        sa.Column("visitor_id", sa.Uuid(), nullable=False),
        sa.Column("lot_id", sa.Uuid(), nullable=False),
        sa.Column("entry_time", sa.DateTime(), nullable=False),
        sa.Column("exit_time", sa.DateTime(), nullable=True),
        sa.Column("gatekeeper_user_id", sa.Uuid(), nullable=True),
        sa.Column("entry_notes", sa.String(), nullable=True),
        sa.Column("exit_notes", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["authorization_id"], ["visitor_authorization.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["visitor_id"], ["visitor.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lot_id"], ["lot.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["gatekeeper_user_id"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_access_log_authorization_id"), "access_log", ["authorization_id"], unique=False)
    op.create_index(op.f("ix_access_log_visitor_id"), "access_log", ["visitor_id"], unique=False)
    op.create_index(op.f("ix_access_log_lot_id"), "access_log", ["lot_id"], unique=False)
    op.create_index(op.f("ix_access_log_entry_time"), "access_log", ["entry_time"], unique=False)
    op.create_index(op.f("ix_access_log_exit_time"), "access_log", ["exit_time"], unique=False)
    op.create_index(op.f("ix_access_log_gatekeeper_user_id"), "access_log", ["gatekeeper_user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_access_log_gatekeeper_user_id"), table_name="access_log")
    op.drop_index(op.f("ix_access_log_exit_time"), table_name="access_log")
    op.drop_index(op.f("ix_access_log_entry_time"), table_name="access_log")
    op.drop_index(op.f("ix_access_log_lot_id"), table_name="access_log")
    op.drop_index(op.f("ix_access_log_visitor_id"), table_name="access_log")
    op.drop_index(op.f("ix_access_log_authorization_id"), table_name="access_log")
    op.drop_table("access_log")

    op.drop_index(op.f("ix_visitor_authorization_status"), table_name="visitor_authorization")
    op.drop_index(op.f("ix_visitor_authorization_authorizer_user_id"), table_name="visitor_authorization")
    op.drop_index(op.f("ix_visitor_authorization_lot_id"), table_name="visitor_authorization")
    op.drop_index(op.f("ix_visitor_authorization_visitor_id"), table_name="visitor_authorization")
    op.drop_table("visitor_authorization")

    op.drop_index(op.f("ix_visitor_vehicle_plate"), table_name="visitor")
    op.drop_index(op.f("ix_visitor_company_name"), table_name="visitor")
    op.drop_index(op.f("ix_visitor_cpf"), table_name="visitor")
    op.drop_index(op.f("ix_visitor_full_name"), table_name="visitor")
    op.drop_table("visitor")
