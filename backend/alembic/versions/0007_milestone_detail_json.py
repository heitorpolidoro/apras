"""milestone stage detail json

The stage detail the obras report needs (APRAS-114): one nullable JSON column on
``project_milestone``, holding
``{"pct": float, "start": "YYYY-MM-DD", "leaves": [{"name": str, "pct": float,
"start": ISO date | null, "finish": ISO date | null}]}``.

No new table, no child table, no backfill, no server default and no data step.
``NULL`` means "this stage has no detail" and is what **every** row holds until
the operator re-runs the untracked sync script, which is the only writer there
will ever be; the report renders that state exactly as it does today. One JSON
column rather than a child table is a recorded operator decision: the sync
deletes and recreates the whole dataset on every run, nothing queries these
values in SQL, and ``construction_project.planned_progress_json`` already
stores a contractor curve exactly this way.

This is an **ordinary new revision on top of** ``0006_tenant_brand_theme``, not
an edit of ``0001_initial_schema``. Declaring a new column inside ``0001`` was
the rule only while ``0001`` had never been applied anywhere; production applied
it on 2026-09-19 (APRAS-59), so editing it now would put the deployed database
out of step with its own history.

The history stays a line: ``0001 -> 0002 -> 0003 -> 0005 -> 0006 -> 0007``. The
digits skip ``0004`` and always will -- a slug is a name, Alembic orders a
history by ``down_revision`` and never by the digits in it, and renaming a
committed revision would rewrite history a deployed database has already
recorded.

``revision`` is 26 characters. ``alembic_version.version_num`` is
``VARCHAR(32)``, and a longer slug fails on the first real ``upgrade`` rather
than at import time -- which is how the retired ``0037`` learnt it.

This file imports **nothing** from ``app/``: a revision is replayed verbatim
against production years from now, so a live import silently rewrites what a
replay produces the day the imported code changes. This revision needs no
helper at all, and a later change that gives it one copies the helper in as a
frozen local literal rather than importing it.

Revision ID: 0007_milestone_detail_json
Revises: 0006_tenant_brand_theme
Create Date: 2026-09-28 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0007_milestone_detail_json'
down_revision: Union[str, Sequence[str], None] = '0006_tenant_brand_theme'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('project_milestone', sa.Column('detail_json', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('project_milestone', 'detail_json')
