"""add plan, tenant_subscription and subscription_change (APRAS-40)

Revision ID: 0035_add_subscription_tables
Revises: 0034_add_tenant_modules
Create Date: 2026-09-02

Three tables, created in FK order, and nothing else.

``plan`` is **global**: it carries no ``tenant_id``. A per-tenant catalogue
would make "which plan is this condominium on" incomparable across the
install, which is the whole point of a catalogue.

``tenant_subscription`` is **directly scoped** and is the first such table
added after migration ``0028``, whose ``_TENANT_SCOPED_TABLES`` literal is
frozen history and is deliberately *not* amended here;
``tests/test_tenant_models.py`` absorbs the new table through its own
``POST_0028_SCOPED_TABLES`` constant. ``uq_tenant_subscription_tenant``
enforces "at most one per tenant".

``subscription_change`` is **append-only** and inherits its tenant through the
NOT NULL FK to ``tenant_subscription``; a second ``tenant_id`` copy would be a
forgeable source of truth that can disagree with the parent.

``sa.JSON``, never ``JSONB`` or ``ARRAY``, for the reason ``0030`` and ``0034``
record: the test harness builds this schema on ``sqlite://`` with
``SQLModel.metadata.create_all()``.

**No data statement in either direction, and no seeded plan.** That is what
makes this migration exactly reversible, and it is the no-seeds doctrine: a
fresh install has no plans, therefore no subscriptions, therefore every tenant
keeps APRAS-39's all-on default and adopting billing is opt-in.
"""

import sqlalchemy as sa
import sqlmodel

from alembic import op

revision = "0035_add_subscription_tables"
down_revision = "0034_add_tenant_modules"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "plan",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column(
            "description", sqlmodel.sql.sqltypes.AutoString(), nullable=True
        ),
        sa.Column(
            "included_modules", sa.JSON(), nullable=False, server_default="[]"
        ),
        sa.Column("base_price", sa.Float(), nullable=False),
        sa.Column(
            "module_prices", sa.JSON(), nullable=False, server_default="{}"
        ),
        sa.Column(
            "currency", sqlmodel.sql.sqltypes.AutoString(length=3), nullable=False
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_plan_name"), "plan", ["name"], unique=True)

    op.create_table(
        "tenant_subscription",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "tenant_id",
            sa.Uuid(),
            nullable=False,
            server_default=sa.text("'00000000-0000-0000-0000-000000000001'"),
        ),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status", sqlmodel.sql.sqltypes.AutoString(), nullable=False
        ),
        sa.Column(
            "courtesy_modules", sa.JSON(), nullable=False, server_default="[]"
        ),
        sa.Column("notes", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["plan_id"], ["plan.id"], ondelete="RESTRICT"
        ),
        # Named explicitly, to the convention migration ``0028`` established
        # for all 27 directly-scoped tables: ``fk_<table>_tenant_id``. Left
        # unnamed, Postgres would generate ``tenant_subscription_tenant_id_fkey``
        # and ``test_every_scoped_table_has_the_four_properties`` -- which
        # iterates ``TENANT_SCOPED_TABLES`` and asserts that exact name carries
        # ``ON DELETE RESTRICT`` -- would go red the moment this table is
        # registered there, which it must be: it is the 28th scoped table.
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenant.id"],
            ondelete="RESTRICT",
            name="fk_tenant_subscription_tenant_id",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", name="uq_tenant_subscription_tenant"),
    )
    op.create_index(
        op.f("ix_tenant_subscription_plan_id"),
        "tenant_subscription",
        ["plan_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tenant_subscription_status"),
        "tenant_subscription",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tenant_subscription_tenant_id"),
        "tenant_subscription",
        ["tenant_id"],
        unique=False,
    )

    op.create_table(
        "subscription_change",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("subscription_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column(
            "modules_added", sa.JSON(), nullable=False, server_default="[]"
        ),
        sa.Column(
            "modules_removed", sa.JSON(), nullable=False, server_default="[]"
        ),
        sa.Column("from_plan_id", sa.Uuid(), nullable=True),
        sa.Column("to_plan_id", sa.Uuid(), nullable=True),
        sa.Column("reason", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("changed_by_id", sa.Uuid(), nullable=False),
        sa.Column("changed_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["changed_by_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["from_plan_id"], ["plan.id"]),
        sa.ForeignKeyConstraint(["to_plan_id"], ["plan.id"]),
        sa.ForeignKeyConstraint(
            ["subscription_id"],
            ["tenant_subscription.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_subscription_change_changed_at"),
        "subscription_change",
        ["changed_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_subscription_change_changed_by_id"),
        "subscription_change",
        ["changed_by_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_subscription_change_kind"),
        "subscription_change",
        ["kind"],
        unique=False,
    )
    op.create_index(
        op.f("ix_subscription_change_subscription_id"),
        "subscription_change",
        ["subscription_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_subscription_change_subscription_id"),
        table_name="subscription_change",
    )
    op.drop_index(
        op.f("ix_subscription_change_kind"), table_name="subscription_change"
    )
    op.drop_index(
        op.f("ix_subscription_change_changed_by_id"),
        table_name="subscription_change",
    )
    op.drop_index(
        op.f("ix_subscription_change_changed_at"),
        table_name="subscription_change",
    )
    op.drop_table("subscription_change")

    op.drop_index(
        op.f("ix_tenant_subscription_tenant_id"), table_name="tenant_subscription"
    )
    op.drop_index(
        op.f("ix_tenant_subscription_status"), table_name="tenant_subscription"
    )
    op.drop_index(
        op.f("ix_tenant_subscription_plan_id"), table_name="tenant_subscription"
    )
    op.drop_table("tenant_subscription")

    op.drop_index(op.f("ix_plan_name"), table_name="plan")
    op.drop_table("plan")
