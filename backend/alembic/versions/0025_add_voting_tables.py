"""add assembly voting and poll tables (APRAS-33)

Revision ID: 0025_add_voting_tables
Revises: 0024_task_visible_to_m2m
Create Date: 2026-08-28

Creates the six voting tables (`assembly`, `vote`, `vote_option`,
`ballot`, `ballot_rejection`, `lot_voter_eligibility`) and adds the three
manual delinquency columns to `lot`.

Enum columns are plain `sa.String` (no native Postgres enum type), matching
what `0023_add_reservation_tables` does for `space_reservation.status`: the
test suite builds the schema with `SQLModel.metadata.create_all()` against
in-memory SQLite, so nothing Postgres-specific may leak into the models.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "0025_add_voting_tables"
down_revision: Union[str, Sequence[str], None] = "0024_task_visible_to_m2m"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "assembly",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("held_on", sa.Date(), nullable=False),
        sa.Column("agenda", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["created_by_id"], ["user.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_assembly_title", "assembly", ["title"])
    op.create_index("ix_assembly_type", "assembly", ["type"])
    op.create_index("ix_assembly_held_on", "assembly", ["held_on"])
    op.create_index("ix_assembly_status", "assembly", ["status"])
    op.create_index("ix_assembly_created_by_id", "assembly", ["created_by_id"])

    op.create_table(
        "vote",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("assembly_id", sa.Uuid(), nullable=True),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("vote_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column(
            "is_anonymous",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("opens_at", sa.DateTime(), nullable=False),
        sa.Column("closes_at", sa.DateTime(), nullable=False),
        sa.Column("tally_snapshot_json", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["assembly_id"], ["assembly.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_id"], ["user.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vote_assembly_id", "vote", ["assembly_id"])
    op.create_index("ix_vote_kind", "vote", ["kind"])
    op.create_index("ix_vote_status", "vote", ["status"])
    op.create_index("ix_vote_created_by_id", "vote", ["created_by_id"])

    op.create_table(
        "vote_option",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("vote_id", sa.Uuid(), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["vote_id"], ["vote.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vote_option_vote_id", "vote_option", ["vote_id"])

    op.create_table(
        "lot_voter_eligibility",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("lot_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("added_by_id", sa.Uuid(), nullable=True),
        sa.Column("added_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["lot_id"], ["lot.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["added_by_id"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lot_id", "user_id", name="uq_lot_voter_eligibility"),
    )
    op.create_index(
        "ix_lot_voter_eligibility_lot_id", "lot_voter_eligibility", ["lot_id"]
    )
    op.create_index(
        "ix_lot_voter_eligibility_user_id", "lot_voter_eligibility", ["user_id"]
    )

    op.create_table(
        "ballot",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("vote_id", sa.Uuid(), nullable=False),
        sa.Column("voter_key", sa.String(), nullable=False),
        sa.Column("lot_id", sa.Uuid(), nullable=True),
        sa.Column("voter_user_id", sa.Uuid(), nullable=True),
        sa.Column("fraction_ideal_at_cast", sa.Float(), nullable=True),
        sa.Column(
            "is_retraction",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("selected_option_ids_json", sa.Text(), nullable=True),
        sa.Column("cast_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["vote_id"], ["vote.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lot_id"], ["lot.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["voter_user_id"], ["user.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ballot_vote_id", "ballot", ["vote_id"])
    op.create_index("ix_ballot_voter_key", "ballot", ["voter_key"])
    op.create_index("ix_ballot_lot_id", "ballot", ["lot_id"])
    op.create_index("ix_ballot_voter_user_id", "ballot", ["voter_user_id"])
    # Deliberately NOT unique: changing a vote appends a new row for the same
    # voter_key, so "one active ballot" is a read rule, not a schema rule.
    op.create_index(
        "ix_ballot_vote_voter_cast", "ballot", ["vote_id", "voter_key", "cast_at"]
    )

    op.create_table(
        "ballot_rejection",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("vote_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("lot_id", sa.Uuid(), nullable=True),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("attempted_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["vote_id"], ["vote.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["lot_id"], ["lot.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ballot_rejection_vote_id", "ballot_rejection", ["vote_id"])
    op.create_index("ix_ballot_rejection_user_id", "ballot_rejection", ["user_id"])
    op.create_index("ix_ballot_rejection_lot_id", "ballot_rejection", ["lot_id"])
    op.create_index("ix_ballot_rejection_reason", "ballot_rejection", ["reason"])

    op.add_column(
        "lot",
        sa.Column(
            "is_delinquent",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "lot", sa.Column("delinquency_updated_at", sa.DateTime(), nullable=True)
    )
    op.add_column(
        "lot", sa.Column("delinquency_updated_by_id", sa.Uuid(), nullable=True)
    )
    op.create_foreign_key(
        "fk_lot_delinquency_updated_by_id",
        "lot",
        "user",
        ["delinquency_updated_by_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_lot_is_delinquent", "lot", ["is_delinquent"])


def downgrade() -> None:
    op.drop_index("ix_lot_is_delinquent", table_name="lot")
    op.drop_constraint("fk_lot_delinquency_updated_by_id", "lot", type_="foreignkey")
    op.drop_column("lot", "delinquency_updated_by_id")
    op.drop_column("lot", "delinquency_updated_at")
    op.drop_column("lot", "is_delinquent")

    op.drop_index("ix_ballot_rejection_reason", table_name="ballot_rejection")
    op.drop_index("ix_ballot_rejection_lot_id", table_name="ballot_rejection")
    op.drop_index("ix_ballot_rejection_user_id", table_name="ballot_rejection")
    op.drop_index("ix_ballot_rejection_vote_id", table_name="ballot_rejection")
    op.drop_table("ballot_rejection")

    op.drop_index("ix_ballot_vote_voter_cast", table_name="ballot")
    op.drop_index("ix_ballot_voter_user_id", table_name="ballot")
    op.drop_index("ix_ballot_lot_id", table_name="ballot")
    op.drop_index("ix_ballot_voter_key", table_name="ballot")
    op.drop_index("ix_ballot_vote_id", table_name="ballot")
    op.drop_table("ballot")

    op.drop_index(
        "ix_lot_voter_eligibility_user_id", table_name="lot_voter_eligibility"
    )
    op.drop_index("ix_lot_voter_eligibility_lot_id", table_name="lot_voter_eligibility")
    op.drop_table("lot_voter_eligibility")

    op.drop_index("ix_vote_option_vote_id", table_name="vote_option")
    op.drop_table("vote_option")

    op.drop_index("ix_vote_created_by_id", table_name="vote")
    op.drop_index("ix_vote_status", table_name="vote")
    op.drop_index("ix_vote_kind", table_name="vote")
    op.drop_index("ix_vote_assembly_id", table_name="vote")
    op.drop_table("vote")

    op.drop_index("ix_assembly_created_by_id", table_name="assembly")
    op.drop_index("ix_assembly_status", table_name="assembly")
    op.drop_index("ix_assembly_held_on", table_name="assembly")
    op.drop_index("ix_assembly_type", table_name="assembly")
    op.drop_index("ix_assembly_title", table_name="assembly")
    op.drop_table("assembly")
