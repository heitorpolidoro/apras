"""add tenant.logo_url and construction_project.planned_progress_json (APRAS-60)

Revision ID: 0037_add_logo_and_planned_progress
Revises: 0036_add_infraction_tables
Create Date: 2026-09-14

Two nullable columns and nothing else. The construction-projects report
(APRAS-60) renders a masthead logo and a "previsto até hoje" bar, and the
schema held neither value.

``tenant.logo_url`` is the masthead image of the acting tenant. Nullable with
**no backfill and no server default**: an install that has not set one renders
the masthead without an ``<img>``, which is the documented degradation, and a
``''`` default would instead produce a broken image on every existing tenant.

``construction_project.planned_progress_json`` holds the contractor's planned
physical-progress curve as an ordered list of ``{"month": "YYYY-MM", "pct":
float}`` points. ``sa.JSON``, not a Postgres type, for the reason ``0030`` and
``0034`` record: the test harness builds this schema on ``sqlite://`` with
``SQLModel.metadata.create_all()``, so a Postgres-only type would not compile
there. ``None`` and ``[]`` both mean *no curve* and are read, never written,
by this task -- there is no API and no UI for the column, only SQL/seed.

The revision id drops the ``add_`` the file name carries: ``alembic_version``
holds 32 characters and ``0037_add_logo_and_planned_progress`` is 34, which
would fail on the first ``upgrade`` against a real database rather than in a
test. ``down_revision`` of a later migration must therefore name
``0037_logo_and_planned_progress``.

**No table is created**, so the 53-table partition asserted by
``tests/test_tenant_models.py`` and ``tests/test_migrations_postgres.py`` is
unchanged, and **no data statement runs in either direction**, which is what
makes this exactly reversible.
"""

import sqlalchemy as sa

from alembic import op

revision = "0037_logo_and_planned_progress"
down_revision = "0036_add_infraction_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tenant", sa.Column("logo_url", sa.String(), nullable=True))
    op.add_column(
        "construction_project",
        sa.Column("planned_progress_json", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("construction_project", "planned_progress_json")
    op.drop_column("tenant", "logo_url")
