"""add tenant, user membership and the default-tenant backfill (APRAS-41)

Revision ID: 0028_add_tenant_and_membership
Revises: 0027_add_purchase_quotation
Create Date: 2026-08-31

First slice of the multi-tenant SaaS chain APRAS-41 -> APRAS-42 -> APRAS-43.
This is the **data layer only**: after it runs, every existing endpoint still
behaves exactly as it did before, because every pre-existing row (and every
row inserted by code that predates tenant awareness) lands in one well-known
default tenant.

Why a well-known literal default tenant id
------------------------------------------
``DEFAULT_TENANT_ID`` is a fixed uuid, never generated. It is used in three
places that must agree without a lookup: this migration's backfill, each
scoped column's ``server_default``, and the SQLModel Python-side default.
That is what lets ~68 existing test modules keep constructing models
directly (``Category(name="General")``) and every existing writer keep
inserting without knowing tenants exist.

Direct vs inherited scope
-------------------------
The 27 tables in ``_TENANT_SCOPED_TABLES`` get a ``tenant_id``: each is
reachable by a route that lists it or fetches it by its own id *without* a
tenant-scoped parent's id in the path, or has no NOT NULL FK to a scoped
table. The remaining 20 tables inherit their tenant through a NOT NULL FK to
a scoped parent, and deliberately get **no** ``tenant_id``: duplicating it
would create a second source of truth that can disagree with the parent.
``user`` stays global.

Three notes the follow-up slice (APRAS-42) will trip on otherwise:

* ``ballot`` and ``ballot_rejection`` have no ``tenant_id`` even though they
  also carry a nullable ``lot_id``. A ballot only exists inside a vote, and
  the vote is the tenant boundary. Duplicating ``tenant_id`` onto a ballot
  would put a second, forgeable source of truth on the most audit-sensitive
  table in the system.
* ``announcement_comment`` is the one exception to the rule as written: it
  has a parent-free route, ``DELETE /api/v1/announcements/comments/{id}``. It
  stays inherited anyway — a comment has no meaning outside its announcement
  — so APRAS-42 must join to ``announcement`` on that single route.
* ``user_user_type_link`` spans a global entity (``user``) and a scoped one
  (``user_type``); the scoped side is the tenant boundary.

Uniques left global on purpose
------------------------------
* ``user.email`` / ``user.cpf`` — a user is one identity across tenants.
* ``access_device.device_key`` — a hardware credential that authenticates
  ``POST /access-control/webhook/verification``. It must be unique across the
  whole install, or one condominium's device could impersonate another's.
* ``tenant.name`` — so the administrator's tenant list is unambiguous.
* ``budget_line.uq_budget_line_category_year``,
  ``user_lot_link.uq_user_lot_link_user_lot``,
  ``lot_voter_eligibility.uq_lot_voter_eligibility`` and
  ``announcement_read_receipt.uq_announcement_read_receipt_user`` are already
  keyed on an already-scoped column, so there is nothing to change.

Following the 0026/0027 precedent, StrEnum-backed columns use ``sa.String()``
and never ``sa.Enum()``; ``tenant_id`` is ``sa.Uuid()`` like every other id.
"""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

revision: str = "0028_add_tenant_and_membership"
down_revision: str | Sequence[str] | None = "0027_add_purchase_quotation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001"
DEFAULT_TENANT_NAME = "Condomínio Padrão"

_TENANT_DEFAULT = sa.text(f"'{DEFAULT_TENANT_ID}'")

# The 27 directly tenant-scoped tables. Kept as a module-level constant so it
# is readable in review and assertable in tests (see
# tests/test_tenant_models.py, which parses this tuple out of this file).
_TENANT_SCOPED_TABLES: tuple[str, ...] = (
    "task",
    "category",
    "user_type",
    "lot",
    "resident",
    "visitor",
    "visitor_authorization",
    "access_log",
    "announcement",
    "document_folder",
    "association_document",
    "occurrence",
    "package",
    "reservable_space",
    "space_reservation",
    "construction_project",
    "purchase_request",
    "asset",
    "inventory_movement",
    "access_device",
    "finance_category",
    "budget_line",
    "financial_transaction",
    "assembly",
    "vote",
    "feedback",
    "media_asset",
)

_tenant_table = sa.table(
    "tenant",
    sa.column("id", sa.Uuid()),
    sa.column("name", sa.String()),
    sa.column("is_active", sa.Boolean()),
    sa.column("created_at", sa.DateTime()),
    sa.column("updated_at", sa.DateTime()),
)

_user_tenant_link_table = sa.table(
    "user_tenant_link",
    sa.column("id", sa.Uuid()),
    sa.column("user_id", sa.Uuid()),
    sa.column("tenant_id", sa.Uuid()),
    sa.column("created_at", sa.DateTime()),
)


def _now() -> datetime:
    """Return a naive UTC timestamp, matching every other DateTime column."""
    return datetime.now(UTC).replace(tzinfo=None)


def upgrade() -> None:
    """Create the tenancy tables, scope 27 tables and backfill everything."""
    op.create_table(
        "tenant",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tenant_name", "tenant", ["name"], unique=True)

    op.create_table(
        "user_tenant_link",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "tenant_id", name="uq_user_tenant_link_user_tenant"
        ),
    )
    op.create_index("ix_user_tenant_link_user_id", "user_tenant_link", ["user_id"])
    op.create_index("ix_user_tenant_link_tenant_id", "user_tenant_link", ["tenant_id"])

    # The one and only tenant row this migration ever creates.
    now = _now()
    op.bulk_insert(
        _tenant_table,
        [
            {
                "id": uuid.UUID(DEFAULT_TENANT_ID),
                "name": DEFAULT_TENANT_NAME,
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            }
        ],
    )

    for table in _TENANT_SCOPED_TABLES:
        op.add_column(table, sa.Column("tenant_id", sa.Uuid(), nullable=True))
        # Expressed as SQLAlchemy Core rather than an f-string of SQL, and
        # a no-op (0 rows) on the fresh-install base -> head path.
        op.execute(
            sa.update(sa.table(table, sa.column("tenant_id", sa.Uuid()))).values(
                tenant_id=uuid.UUID(DEFAULT_TENANT_ID)
            )
        )
        op.alter_column(
            table,
            "tenant_id",
            nullable=False,
            server_default=_TENANT_DEFAULT,
        )
        op.create_foreign_key(
            f"fk_{table}_tenant_id",
            table,
            "tenant",
            ["tenant_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])

    # Membership backfill: every pre-existing user becomes a member of the
    # default tenant. Ids are generated Python-side rather than with
    # gen_random_uuid() so the migration carries no pgcrypto/Postgres-version
    # assumption; tolerates zero users on a fresh install.
    bind = op.get_bind()
    user_ids = bind.execute(sa.text('SELECT id FROM "user"')).scalars().all()
    if user_ids:
        op.bulk_insert(
            _user_tenant_link_table,
            [
                {
                    "id": uuid.uuid4(),
                    "user_id": user_id,
                    "tenant_id": uuid.UUID(DEFAULT_TENANT_ID),
                    "created_at": now,
                }
                for user_id in user_ids
            ],
        )

    _relax_global_uniques()


def _relax_global_uniques() -> None:
    """Turn the 8 cross-tenant-colliding uniques into tenant composites.

    With a single tenant these are behaviour-identical, which is why they
    belong in this slice: they are schema, not behaviour.
    """
    # category.name -> (tenant_id, name); the plain lookup index survives.
    op.drop_index("ix_category_name", table_name="category")
    op.create_index("ix_category_name", "category", ["name"])
    op.create_index(
        "ix_category_tenant_name", "category", ["tenant_id", "name"], unique=True
    )

    # user_type.name -> (tenant_id, name)
    op.drop_index("ix_user_type_name", table_name="user_type")
    op.create_index("ix_user_type_name", "user_type", ["name"])
    op.create_index(
        "ix_user_type_tenant_name", "user_type", ["tenant_id", "name"], unique=True
    )

    # user_type.role -> (tenant_id, role). NULL roles still never collide, so
    # admin-created types remain unlimited and a duplicate role *within* a
    # tenant is still rejected.
    op.drop_index("ix_user_type_role", table_name="user_type")
    op.create_index(
        "ix_user_type_tenant_role", "user_type", ["tenant_id", "role"], unique=True
    )

    # lot.(block, lot_number) -> (tenant_id, block, lot_number)
    op.drop_constraint("uq_lot_block_lot_number", "lot", type_="unique")
    op.create_unique_constraint(
        "uq_lot_tenant_block_lot_number", "lot", ["tenant_id", "block", "lot_number"]
    )

    # occurrence.protocol_number -> (tenant_id, protocol_number). The
    # constraint dropped here carries Postgres' auto-generated name because
    # migration 0009 declared `sa.UniqueConstraint("protocol_number")`
    # without one.
    op.drop_constraint(
        "occurrence_protocol_number_key", "occurrence", type_="unique"
    )
    op.create_index(
        "ix_occurrence_tenant_protocol",
        "occurrence",
        ["tenant_id", "protocol_number"],
        unique=True,
    )

    # reservable_space.name -> (tenant_id, name); also auto-named, by 0023.
    op.drop_constraint(
        "reservable_space_name_key", "reservable_space", type_="unique"
    )
    op.create_index(
        "ix_reservable_space_tenant_name",
        "reservable_space",
        ["tenant_id", "name"],
        unique=True,
    )

    # asset.asset_tag -> (tenant_id, asset_tag)
    op.drop_constraint("uq_asset_asset_tag", "asset", type_="unique")
    op.create_index(
        "ix_asset_tenant_asset_tag", "asset", ["tenant_id", "asset_tag"], unique=True
    )

    # finance_category.(name, type) -> (tenant_id, name, type)
    op.drop_constraint(
        "uq_finance_category_name_type", "finance_category", type_="unique"
    )
    op.create_unique_constraint(
        "uq_finance_category_tenant_name_type",
        "finance_category",
        ["tenant_id", "name", "type"],
    )


def _restore_global_uniques() -> None:
    """Exact inverse of :func:`_relax_global_uniques`."""
    op.drop_constraint(
        "uq_finance_category_tenant_name_type", "finance_category", type_="unique"
    )
    op.create_unique_constraint(
        "uq_finance_category_name_type", "finance_category", ["name", "type"]
    )

    op.drop_index("ix_asset_tenant_asset_tag", table_name="asset")
    op.create_unique_constraint("uq_asset_asset_tag", "asset", ["asset_tag"])

    op.drop_index("ix_reservable_space_tenant_name", table_name="reservable_space")
    op.create_unique_constraint(
        "reservable_space_name_key", "reservable_space", ["name"]
    )

    op.drop_index("ix_occurrence_tenant_protocol", table_name="occurrence")
    op.create_unique_constraint(
        "occurrence_protocol_number_key", "occurrence", ["protocol_number"]
    )

    op.drop_constraint("uq_lot_tenant_block_lot_number", "lot", type_="unique")
    op.create_unique_constraint(
        "uq_lot_block_lot_number", "lot", ["block", "lot_number"]
    )

    op.drop_index("ix_user_type_tenant_role", table_name="user_type")
    op.create_index("ix_user_type_role", "user_type", ["role"], unique=True)

    op.drop_index("ix_user_type_tenant_name", table_name="user_type")
    op.drop_index("ix_user_type_name", table_name="user_type")
    op.create_index("ix_user_type_name", "user_type", ["name"], unique=True)

    op.drop_index("ix_category_tenant_name", table_name="category")
    op.drop_index("ix_category_name", table_name="category")
    op.create_index("ix_category_name", "category", ["name"], unique=True)


def downgrade() -> None:
    """Drop the tenancy schema and restore the original global uniques."""
    _restore_global_uniques()

    for table in reversed(_TENANT_SCOPED_TABLES):
        op.drop_index(f"ix_{table}_tenant_id", table_name=table)
        op.drop_constraint(f"fk_{table}_tenant_id", table, type_="foreignkey")
        op.drop_column(table, "tenant_id")

    op.drop_index("ix_user_tenant_link_tenant_id", table_name="user_tenant_link")
    op.drop_index("ix_user_tenant_link_user_id", table_name="user_tenant_link")
    op.drop_table("user_tenant_link")

    op.drop_index("ix_tenant_name", table_name="tenant")
    op.drop_table("tenant")
