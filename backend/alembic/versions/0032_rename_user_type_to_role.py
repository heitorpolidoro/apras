"""rename user_type to role (IAM F5, APRAS-49 §2.3)

Revision ID: 0032_rename_user_type_to_role
Revises: 0031_add_user_is_superuser
Create Date: 2026-09-02

Deliverable **A** of IAM F5: the pure rename. ``user_type`` becomes ``role``
everywhere — table, link table, link columns, indexes and constraint names —
and **nothing else changes**.

It moves no data and drops nothing, which is what makes it *exactly*
reversible: ``downgrade()`` is the inverse step for step, and an operator can
back the rename out while keeping (or without ever having applied) the
semantic change ``0033`` carries. That separation is the whole reason F5 ships
two migrations instead of one (§5).

Postgres carries primary-key and foreign-key constraint names across
``ALTER TABLE ... RENAME TO`` unchanged, so a plain ``rename_table`` leaves
six constraints and four indexes still spelling ``user_type``. They are
renamed explicitly here so ``\\d role`` and ``\\d user_role_link`` on a
migrated install say nothing about the retired name (§2.3 step 6).

The identifier renames are Postgres DDL and are guarded by the dialect check
``0012``/``0020`` already use: no workflow in this repository runs Alembic
against SQLite (``backend/tests/conftest.py`` builds its schema with
``SQLModel.metadata.create_all()``), and the guard keeps that true by
construction rather than by luck.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "0032_rename_user_type_to_role"
down_revision = "0031_add_user_is_superuser"
branch_labels = None
depends_on = None


#: (old, new) for every index whose *name* carries the retired word. The two
#: `_pkey` indexes are renamed implicitly, by their constraints below.
_INDEX_RENAMES: tuple[tuple[str, str], ...] = (
    ("ix_user_type_name", "ix_role_name"),
    ("ix_user_type_tenant_id", "ix_role_tenant_id"),
    ("ix_user_type_tenant_name", "ix_role_tenant_name"),
    # Renamed rather than dropped so this migration stays independently
    # reversible; `0033` is what drops it, together with the column it covers.
    ("ix_user_type_tenant_role", "ix_role_tenant_role"),
)

#: (table, old constraint, new constraint). The table is the *post*-rename
#: name on upgrade and the *pre*-rename name on downgrade, so each direction
#: names the table as it exists at that moment.
_CONSTRAINT_RENAMES: tuple[tuple[str, str, str], ...] = (
    ("role", "user_type_pkey", "role_pkey"),
    ("role", "fk_user_type_tenant_id", "fk_role_tenant_id"),
    ("user_role_link", "user_user_type_link_pkey", "user_role_link_pkey"),
    (
        "user_role_link",
        "user_user_type_link_user_id_fkey",
        "user_role_link_user_id_fkey",
    ),
    (
        "user_role_link",
        "user_user_type_link_user_type_id_fkey",
        "user_role_link_role_id_fkey",
    ),
    (
        "task_visible_to_link",
        "task_visible_to_link_user_type_id_fkey",
        "task_visible_to_link_role_id_fkey",
    ),
)


def _is_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    op.rename_table("user_type", "role")
    op.rename_table("user_user_type_link", "user_role_link")
    op.alter_column("user_role_link", "user_type_id", new_column_name="role_id")
    op.alter_column("task_visible_to_link", "user_type_id", new_column_name="role_id")

    if not _is_postgres():
        return
    for old, new in _INDEX_RENAMES:
        op.execute(f'ALTER INDEX "{old}" RENAME TO "{new}"')
    for table, old, new in _CONSTRAINT_RENAMES:
        op.execute(f'ALTER TABLE "{table}" RENAME CONSTRAINT "{old}" TO "{new}"')


def downgrade() -> None:
    if _is_postgres():
        for table, old, new in _CONSTRAINT_RENAMES:
            # `table` is the post-rename name; the tables are still renamed at
            # this point, so it is the right one to address.
            op.execute(f'ALTER TABLE "{table}" RENAME CONSTRAINT "{new}" TO "{old}"')
        for old, new in _INDEX_RENAMES:
            op.execute(f'ALTER INDEX "{new}" RENAME TO "{old}"')

    op.alter_column("task_visible_to_link", "role_id", new_column_name="user_type_id")
    op.alter_column("user_role_link", "role_id", new_column_name="user_type_id")
    op.rename_table("user_role_link", "user_user_type_link")
    op.rename_table("role", "user_type")
