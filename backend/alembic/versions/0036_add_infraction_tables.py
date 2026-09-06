"""add the seven infraction tables (APRAS-44)

Revision ID: 0036_add_infraction_tables
Revises: 0035_add_subscription_tables
Create Date: 2026-09-05

Seven tables, created in foreign-key order, and nothing else.

Four are **directly scoped** -- ``infraction_rule``, ``infraction``,
``infraction_cycle_close`` and ``infraction_settings`` -- because each is
reached by a route that lists it or fetches it without a scoped parent's id in
the path (``GET /api/v1/infractions/cycles`` and
``GET /api/v1/infraction-settings`` are the two non-obvious ones). Their
``tenant_id`` reproduces ``tenant_id_field()``'s four properties by hand,
because a migration cannot call it, and the FK is **named**
``fk_<table>_tenant_id`` to the convention migration ``0028`` established:
``tests/test_migrations_postgres.py::test_every_scoped_table_has_not_null_tenant_id``
looks that exact name up for every registered scoped table.

Three **inherit** their tenant through a NOT NULL FK to a scoped parent --
``infraction_policy_step`` → ``infraction_rule``, ``infraction_stage`` and
``infraction_contestation`` → ``infraction``. A second ``tenant_id`` copy
would be a forgeable source of truth that can disagree with the parent.

Two nullability facts are **decisions, not oversights**, and are pinned by
``tests/test_infractions.py``:

* ``infraction.lot_id`` is ``nullable=False`` while ``occurrence.lot_id`` is
  nullable -- an infraction is always against a unit, a common-area occurrence
  legitimately has no lot. §7.4's effective-lot rule exists so this can be
  NOT NULL.
* ``infraction_cycle_close.lot_id`` is ``nullable=True``: audit context only,
  never part of the recidivism match (§6.2 property 5).

``infraction_contestation.stage_id`` is ``nullable=True`` with ``SET NULL``,
and that resolves a real FK-lifetime collision the spec left open: its parent
``infraction_stage.infraction_id`` is ``CASCADE``, so a ``RESTRICT`` on
``stage_id`` would have an infraction's deletion cascade the stages out from
under a restricting child. The contestation still belongs to its infraction
through its own NOT NULL, CASCADE ``infraction_id``.

Enums are ``AutoString`` columns, never a Postgres ``ENUM`` type, so
``downgrade()`` has no type to drop -- and they carry **no** ``server_default``
because none of them has a Python-side default either: matching
``SQLModel.metadata.create_all()`` exactly is what keeps the SQLite schema the
test harness builds and the Postgres schema Alembic builds identical. The URL
lists are ``AutoString`` JSON payloads, mirroring
``occurrence.photo_urls_json``. Money is ``sa.Float()``, the type every other
amount in this codebase uses.

**No data statement in either direction.** No seeded rule, no seeded policy,
no settings row -- the settings singleton is materialised lazily on the first
``PUT`` (§5), which is what makes this migration exactly reversible and keeps
the no-seeds doctrine intact.
"""

import sqlalchemy as sa
import sqlmodel

from alembic import op

revision = "0036_add_infraction_tables"
down_revision = "0035_add_subscription_tables"
branch_labels = None
depends_on = None

#: The literal every directly-scoped table's ``tenant_id`` defaults to. Spelled
#: here rather than imported, because a migration must keep meaning what it
#: meant on the day it ran.
_DEFAULT_TENANT = sa.text("'00000000-0000-0000-0000-000000000001'")


def _tenant_id_column() -> sa.Column:
    """``tenant_id_field()``'s column half, by hand."""
    return sa.Column(
        "tenant_id", sa.Uuid(), nullable=False, server_default=_DEFAULT_TENANT
    )


def _tenant_fk(table: str) -> sa.ForeignKeyConstraint:
    """``tenant_id_field()``'s constraint half, named to `0028`'s convention."""
    return sa.ForeignKeyConstraint(
        ["tenant_id"],
        ["tenant.id"],
        ondelete="RESTRICT",
        name=f"fk_{table}_tenant_id",
    )


def upgrade() -> None:
    # --- infraction_settings: the per-tenant condominium-fee reference -----
    op.create_table(
        "infraction_settings",
        sa.Column("id", sa.Uuid(), nullable=False),
        _tenant_id_column(),
        sa.Column("condo_fee_amount", sa.Float(), nullable=True),
        sa.Column("updated_by_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["updated_by_id"], ["user.id"], ondelete="SET NULL"
        ),
        _tenant_fk("infraction_settings"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", name="uq_infraction_settings_tenant"),
    )
    op.create_index(
        op.f("ix_infraction_settings_tenant_id"),
        "infraction_settings",
        ["tenant_id"],
    )
    op.create_index(
        op.f("ix_infraction_settings_updated_by_id"),
        "infraction_settings",
        ["updated_by_id"],
    )

    # --- infraction_rule: the per-tenant catalogue -------------------------
    op.create_table(
        "infraction_rule",
        sa.Column("id", sa.Uuid(), nullable=False),
        _tenant_id_column(),
        sa.Column(
            "article", sqlmodel.sql.sqltypes.AutoString(), nullable=False
        ),
        sa.Column("origin", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column(
            "description", sqlmodel.sql.sqltypes.AutoString(), nullable=False
        ),
        sa.Column("recidivism_window_days", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        _tenant_fk("infraction_rule"),
        sa.PrimaryKeyConstraint("id"),
        # Two condominiums may both cite "art. 12 do Regimento Interno"; one
        # may not cite it twice.
        sa.UniqueConstraint(
            "tenant_id",
            "origin",
            "article",
            name="uq_infraction_rule_tenant_origin_article",
        ),
    )
    op.create_index(
        op.f("ix_infraction_rule_is_active"), "infraction_rule", ["is_active"]
    )
    op.create_index(
        op.f("ix_infraction_rule_origin"), "infraction_rule", ["origin"]
    )
    op.create_index(
        op.f("ix_infraction_rule_tenant_id"), "infraction_rule", ["tenant_id"]
    )

    # --- infraction_policy_step: one rule's ordered ladder -----------------
    op.create_table(
        "infraction_policy_step",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("rule_id", sa.Uuid(), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("action", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("defense_deadline_days", sa.Integer(), nullable=True),
        sa.Column(
            "fine_mode", sqlmodel.sql.sqltypes.AutoString(), nullable=True
        ),
        sa.Column("fine_fixed_amount", sa.Float(), nullable=True),
        sa.Column("fine_fee_multiplier", sa.Float(), nullable=True),
        sa.Column("note", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.ForeignKeyConstraint(
            ["rule_id"], ["infraction_rule.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "rule_id", "step_order", name="uq_infraction_policy_step_rule_order"
        ),
    )
    op.create_index(
        op.f("ix_infraction_policy_step_rule_id"),
        "infraction_policy_step",
        ["rule_id"],
    )

    # --- infraction: the process. No `status`, no `current_stage`. ---------
    op.create_table(
        "infraction",
        sa.Column("id", sa.Uuid(), nullable=False),
        _tenant_id_column(),
        sa.Column("rule_id", sa.Uuid(), nullable=False),
        sa.Column("lot_id", sa.Uuid(), nullable=False),
        sa.Column("responsible_resident_id", sa.Uuid(), nullable=False),
        sa.Column("source_occurrence_id", sa.Uuid(), nullable=True),
        sa.Column("registered_by_id", sa.Uuid(), nullable=False),
        sa.Column("occurred_on", sa.Date(), nullable=False),
        sa.Column(
            "description", sqlmodel.sql.sqltypes.AutoString(), nullable=False
        ),
        sa.Column(
            "evidence_urls_json",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["lot_id"], ["lot.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["registered_by_id"], ["user.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["responsible_resident_id"], ["resident.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["rule_id"], ["infraction_rule.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["source_occurrence_id"], ["occurrence.id"], ondelete="SET NULL"
        ),
        _tenant_fk("infraction"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_infraction_lot_id"), "infraction", ["lot_id"])
    op.create_index(
        op.f("ix_infraction_occurred_on"), "infraction", ["occurred_on"]
    )
    # What §6.2's `(rule, responsible)` count reads, in the order it reads it.
    op.create_index(
        "ix_infraction_recidivism",
        "infraction",
        ["tenant_id", "rule_id", "responsible_resident_id", "occurred_on"],
    )
    op.create_index(
        op.f("ix_infraction_registered_by_id"), "infraction", ["registered_by_id"]
    )
    op.create_index(
        op.f("ix_infraction_responsible_resident_id"),
        "infraction",
        ["responsible_resident_id"],
    )
    op.create_index(op.f("ix_infraction_rule_id"), "infraction", ["rule_id"])
    op.create_index(
        op.f("ix_infraction_source_occurrence_id"),
        "infraction",
        ["source_occurrence_id"],
    )
    op.create_index(
        op.f("ix_infraction_tenant_id"), "infraction", ["tenant_id"]
    )

    # --- infraction_stage: append-only. No `updated_at`, and no route -----
    #     that edits or deletes a row.
    op.create_table(
        "infraction_stage",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("infraction_id", sa.Uuid(), nullable=False),
        sa.Column("action", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("applied_on", sa.Date(), nullable=False),
        sa.Column("note", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("fine_amount", sa.Float(), nullable=True),
        sa.Column("fine_amount_overridden", sa.Boolean(), nullable=False),
        sa.Column("defense_due_on", sa.Date(), nullable=True),
        # Symmetric with `fine_amount_overridden`: the audit trail must be able
        # to tell a policy-derived deadline from one a human typed.
        sa.Column("defense_deadline_overridden", sa.Boolean(), nullable=False),
        sa.Column("policy_step_order", sa.Integer(), nullable=True),
        sa.Column("suggestion_followed", sa.Boolean(), nullable=False),
        sa.Column(
            "evidence_urls_json",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["user.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["infraction_id"], ["infraction.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_infraction_stage_action"), "infraction_stage", ["action"]
    )
    op.create_index(
        op.f("ix_infraction_stage_actor_id"), "infraction_stage", ["actor_id"]
    )
    op.create_index(
        op.f("ix_infraction_stage_infraction_id"),
        "infraction_stage",
        ["infraction_id"],
    )

    # --- infraction_contestation: the notified unit's written defense -----
    op.create_table(
        "infraction_contestation",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("infraction_id", sa.Uuid(), nullable=False),
        sa.Column("stage_id", sa.Uuid(), nullable=True),
        sa.Column("body", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column(
            "attachment_urls_json",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=True,
        ),
        sa.Column("submitted_by_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["infraction_id"], ["infraction.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["stage_id"], ["infraction_stage.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["submitted_by_id"], ["user.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_infraction_contestation_infraction_id"),
        "infraction_contestation",
        ["infraction_id"],
    )
    op.create_index(
        op.f("ix_infraction_contestation_stage_id"),
        "infraction_contestation",
        ["stage_id"],
    )
    op.create_index(
        op.f("ix_infraction_contestation_submitted_by_id"),
        "infraction_contestation",
        ["submitted_by_id"],
    )

    # --- infraction_cycle_close: the auditable, justified cut -------------
    op.create_table(
        "infraction_cycle_close",
        sa.Column("id", sa.Uuid(), nullable=False),
        _tenant_id_column(),
        sa.Column("rule_id", sa.Uuid(), nullable=False),
        # Nullable on purpose: audit context, never part of the recidivism
        # match. Matching on it would silently make the count propter rem
        # again for anyone who moved.
        sa.Column("lot_id", sa.Uuid(), nullable=True),
        sa.Column("responsible_resident_id", sa.Uuid(), nullable=False),
        sa.Column(
            "justification", sqlmodel.sql.sqltypes.AutoString(), nullable=False
        ),
        sa.Column("closed_by_id", sa.Uuid(), nullable=False),
        sa.Column("closed_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["closed_by_id"], ["user.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["lot_id"], ["lot.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["responsible_resident_id"], ["resident.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["rule_id"], ["infraction_rule.id"], ondelete="RESTRICT"
        ),
        _tenant_fk("infraction_cycle_close"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_infraction_cycle_close_closed_by_id"),
        "infraction_cycle_close",
        ["closed_by_id"],
    )
    op.create_index(
        op.f("ix_infraction_cycle_close_lot_id"),
        "infraction_cycle_close",
        ["lot_id"],
    )
    op.create_index(
        op.f("ix_infraction_cycle_close_responsible_resident_id"),
        "infraction_cycle_close",
        ["responsible_resident_id"],
    )
    op.create_index(
        op.f("ix_infraction_cycle_close_rule_id"),
        "infraction_cycle_close",
        ["rule_id"],
    )
    op.create_index(
        op.f("ix_infraction_cycle_close_tenant_id"),
        "infraction_cycle_close",
        ["tenant_id"],
    )


def downgrade() -> None:
    """Drop the seven tables in reverse dependency order, indexes first."""
    op.drop_index(
        op.f("ix_infraction_cycle_close_tenant_id"),
        table_name="infraction_cycle_close",
    )
    op.drop_index(
        op.f("ix_infraction_cycle_close_rule_id"),
        table_name="infraction_cycle_close",
    )
    op.drop_index(
        op.f("ix_infraction_cycle_close_responsible_resident_id"),
        table_name="infraction_cycle_close",
    )
    op.drop_index(
        op.f("ix_infraction_cycle_close_lot_id"),
        table_name="infraction_cycle_close",
    )
    op.drop_index(
        op.f("ix_infraction_cycle_close_closed_by_id"),
        table_name="infraction_cycle_close",
    )
    op.drop_table("infraction_cycle_close")

    op.drop_index(
        op.f("ix_infraction_contestation_submitted_by_id"),
        table_name="infraction_contestation",
    )
    op.drop_index(
        op.f("ix_infraction_contestation_stage_id"),
        table_name="infraction_contestation",
    )
    op.drop_index(
        op.f("ix_infraction_contestation_infraction_id"),
        table_name="infraction_contestation",
    )
    op.drop_table("infraction_contestation")

    op.drop_index(
        op.f("ix_infraction_stage_infraction_id"), table_name="infraction_stage"
    )
    op.drop_index(
        op.f("ix_infraction_stage_actor_id"), table_name="infraction_stage"
    )
    op.drop_index(
        op.f("ix_infraction_stage_action"), table_name="infraction_stage"
    )
    op.drop_table("infraction_stage")

    op.drop_index(op.f("ix_infraction_tenant_id"), table_name="infraction")
    op.drop_index(
        op.f("ix_infraction_source_occurrence_id"), table_name="infraction"
    )
    op.drop_index(op.f("ix_infraction_rule_id"), table_name="infraction")
    op.drop_index(
        op.f("ix_infraction_responsible_resident_id"), table_name="infraction"
    )
    op.drop_index(
        op.f("ix_infraction_registered_by_id"), table_name="infraction"
    )
    op.drop_index("ix_infraction_recidivism", table_name="infraction")
    op.drop_index(op.f("ix_infraction_occurred_on"), table_name="infraction")
    op.drop_index(op.f("ix_infraction_lot_id"), table_name="infraction")
    op.drop_table("infraction")

    op.drop_index(
        op.f("ix_infraction_policy_step_rule_id"),
        table_name="infraction_policy_step",
    )
    op.drop_table("infraction_policy_step")

    op.drop_index(
        op.f("ix_infraction_rule_tenant_id"), table_name="infraction_rule"
    )
    op.drop_index(op.f("ix_infraction_rule_origin"), table_name="infraction_rule")
    op.drop_index(
        op.f("ix_infraction_rule_is_active"), table_name="infraction_rule"
    )
    op.drop_table("infraction_rule")

    op.drop_index(
        op.f("ix_infraction_settings_updated_by_id"),
        table_name="infraction_settings",
    )
    op.drop_index(
        op.f("ix_infraction_settings_tenant_id"),
        table_name="infraction_settings",
    )
    op.drop_table("infraction_settings")
