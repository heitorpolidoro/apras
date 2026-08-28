"""add_role_to_user_type

Revision ID: 0018_add_role_to_user_type
Revises: 0017_add_user_type_allowed_menus
Create Date: 2026-08-27 13:00:00.000000

"""
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0018_add_role_to_user_type"
down_revision: Union[str, Sequence[str], None] = "0017_add_user_type_allowed_menus"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Human-readable names for the 5 seeded role-linked UserType rows, one per
# UserRole value (ADMINISTRATOR/DIRECTOR/MANAGER/GUEST/RESIDENT). Distinct
# from admin-created type names via the "(papel)" suffix.
_ROLE_TYPE_NAMES = {
    "ADMINISTRATOR": "Administrador (papel)",
    "DIRECTOR": "Diretor (papel)",
    "MANAGER": "Gerente (papel)",
    "GUEST": "Convidado (papel)",
    "RESIDENT": "Morador (papel)",
}

# Deliberately a plain VARCHAR, NOT a reuse of the native Postgres "userrole"
# enum type used by user.role: this migration INSERTs a row with
# role='RESIDENT', a value added to the "userrole" enum by an earlier
# migration (0014_add_resident_userrole) via `ALTER TYPE ... ADD VALUE`.
# Postgres forbids using a newly-added enum value in the same transaction
# that added it ("unsafe use of new value ... New enum values must be
# committed before they can be used"). Since Alembic runs an entire
# `upgrade head` invocation in a single transaction by default, a fresh
# database migrating from base to head would hit that error if this column
# reused the native enum type. A portable VARCHAR sidesteps the issue
# entirely (and matches this project's existing precedent of avoiding
# Postgres-specific column types for portability, see
# UserType.allowed_menus using JSON instead of ARRAY).
_ROLE_COLUMN_TYPE = sa.String()


def upgrade() -> None:
    """Add UserType.role and seed one role-linked row per UserRole value.

    `role` identifies a UserType implicitly linked to a UserRole (APRAS-9):
    permission-evaluation code (`get_effective_user_type_ids`) treats a
    user's own role as an implicit UserType membership by matching against
    this column, without ever inserting a row into the
    `user_user_type_link` join table.

    A unique index (not a raw UNIQUE column constraint, matching this
    project's established pattern, see `ix_user_type_name`) enforces at
    most one row per non-null role value; NULL values (regular
    admin-created types) are never counted as duplicates of each other by
    a UNIQUE index on either Postgres or SQLite.

    Each seeded row starts with `allowed_menus = []`, matching APRAS-8's
    disruptive-by-default rollout: this migration provides the *mechanism*
    for an Administrator to configure baseline-by-role permissions, it does
    not use it on their behalf.
    """
    op.add_column(
        "user_type",
        sa.Column("role", _ROLE_COLUMN_TYPE, nullable=True),
    )
    op.create_index("ix_user_type_role", "user_type", ["role"], unique=True)

    user_type_table = sa.table(
        "user_type",
        sa.column("id", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("allowed_menus", sa.JSON()),
        sa.column("role", _ROLE_COLUMN_TYPE),
    )
    op.bulk_insert(
        user_type_table,
        [
            {
                "id": uuid.uuid4(),
                "name": name,
                "allowed_menus": [],
                "role": role,
            }
            for role, name in _ROLE_TYPE_NAMES.items()
        ],
    )


def downgrade() -> None:
    """Remove the seeded role-linked rows (matched by role IS NOT NULL) and
    drop the column."""
    op.execute("DELETE FROM user_type WHERE role IS NOT NULL")
    op.drop_index("ix_user_type_role", table_name="user_type")
    op.drop_column("user_type", "role")
