"""tenant invitation

The administrator invitation of APRAS-71: a single-use, hashed token that
lets a superuser hand one condominium to the person who will administer it
in the system. One new table, no edit to any existing one.

This is an **ordinary new revision on top of** ``0002_tenant_slug``, not an
edit of ``0001_initial_schema``. Declaring a new table inside ``0001`` was
the rule only while ``0001`` had never been applied anywhere; production
applied it on 2026-09-19 (APRAS-59), so editing it now would put the
deployed database out of step with its own history.

``revision`` is 20 characters. ``alembic_version.version_num`` is
``VARCHAR(32)``, and a longer slug fails on the first real ``upgrade``
rather than at import time -- which is how the retired ``0037`` learnt it.

This file imports **nothing** from ``app/``: a revision is replayed verbatim
against production years from now, so a live import silently rewrites what a
replay produces the day the imported code changes. ``0001`` re-declares
``DEFAULT_TENANT_ID`` and ``LEGACY_ROLE_NAMES`` as local literals and
``0002`` carries a frozen copy of ``app/core/slug.py``; there is nothing to
copy here, and there is nothing to import either.

**There is no ``token`` column and there never will be.** The table stores
``token_hash``, the SHA-256 hex of the raw token, so a database dump is not
an account takeover. ``tests/test_migrations_postgres.py`` asserts the
absence of a raw-credential column against the live schema.

Revision ID: 0003_tenant_invitation
Revises: 0002_tenant_slug
Create Date: 2026-09-21 18:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '0003_tenant_invitation'
down_revision: Union[str, Sequence[str], None] = '0002_tenant_slug'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('tenant_invitation',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('tenant_id', sa.Uuid(), nullable=False),
    sa.Column('email', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('token_hash', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.Column('accepted_at', sa.DateTime(), nullable=True),
    sa.Column('accepted_user_id', sa.Uuid(), nullable=True),
    sa.Column('invited_by_user_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['accepted_user_id'], ['user.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['invited_by_user_id'], ['user.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tenant_invitation_email'), 'tenant_invitation', ['email'], unique=False)
    op.create_index(op.f('ix_tenant_invitation_tenant_id'), 'tenant_invitation', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_tenant_invitation_token_hash'), 'tenant_invitation', ['token_hash'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_tenant_invitation_token_hash'), table_name='tenant_invitation')
    op.drop_index(op.f('ix_tenant_invitation_tenant_id'), table_name='tenant_invitation')
    op.drop_index(op.f('ix_tenant_invitation_email'), table_name='tenant_invitation')
    op.drop_table('tenant_invitation')
