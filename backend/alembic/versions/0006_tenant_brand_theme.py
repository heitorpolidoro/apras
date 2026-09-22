"""tenant brand theme

The condominium's brand colours (APRAS-68): one nullable JSON column on
``tenant``, holding either ``{"mode": "simple", "primary": …, "accent": …}``
or ``{"mode": "advanced", "light": {…13…}, "dark": null | {…13…}}``. No new
table, no backfill, no server default and no data step -- ``NULL`` means "this
condominium has no colours" and renders exactly today's ``index.css``.

This is an **ordinary new revision on top of** ``0003_tenant_invitation``, not
an edit of ``0001_initial_schema``. Declaring a new column inside ``0001`` was
the rule only while ``0001`` had never been applied anywhere; production
applied it on 2026-09-19 (APRAS-59), so editing it now would put the deployed
database out of step with its own history.

It chains onto ``0005_purchase_line_items``, which is the real Alembic head
**in git**: the committed module no other committed module names as its
``down_revision``. The spec wrote this revision as ``0004_tenant_brand_theme``
on ``0003_tenant_invitation`` and carried a conditional clause for whichever
sibling landed first; while this task was interrupted, APRAS-71 landed
``0003_tenant_invitation`` (``f599012``) and APRAS-73 landed
``0005_purchase_line_items`` on top of it (``516e529``). Chaining onto
``0003`` now would be **two Alembic heads** -- ``alembic upgrade head`` would
fail and ``EXPECTED_HISTORY`` would stop being a single chain -- so the
incoming revision is the one that yields, renumbers itself and re-points its
own ``down_revision``. No committed revision is touched. The history stays the
line ``0001 -> 0002 -> 0003 -> 0005 -> 0006``; the digits skip ``0004``
because a slug is a name and Alembic orders a history by ``down_revision``,
never by the digits in it.

``revision`` is 23 characters. ``alembic_version.version_num`` is
``VARCHAR(32)``, and a longer slug fails on the first real ``upgrade`` rather
than at import time -- which is how the retired ``0037`` learnt it.

This file imports **nothing** from ``app/``: a revision is replayed verbatim
against production years from now, so a live import silently rewrites what a
replay produces the day the imported code changes. ``0001`` re-declares
``DEFAULT_TENANT_ID`` and ``LEGACY_ROLE_NAMES`` as local literals and ``0002``
carries a frozen copy of the slug derivation; this revision needs no helper at
all, and a later change that gives it one copies the helper in as a frozen
local literal rather than importing it.

Revision ID: 0006_tenant_brand_theme
Revises: 0005_purchase_line_items
Create Date: 2026-09-22 09:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0006_tenant_brand_theme'
down_revision: Union[str, Sequence[str], None] = '0005_purchase_line_items'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('tenant', sa.Column('brand_theme', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('tenant', 'brand_theme')
