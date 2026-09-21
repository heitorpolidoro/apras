"""tenant slug

The condominium's stable address (APRAS-66): the ``<slug>`` of the
``/c/<slug>`` entry APRAS-69 will route. Added nullable, backfilled from
``tenant.name``, then set ``NOT NULL`` with a unique index -- in that order,
because the column cannot be born ``NOT NULL`` on a table that already has
rows in production.

This is an **ordinary new revision on top of** ``0001_initial_schema``, not an
edit of it. Declaring a new column inside ``0001`` was the rule only while
``0001`` had never been applied anywhere; production applied it on
2026-09-19 (APRAS-59), so editing it now would put the deployed database out
of step with its own history and cost another reset.

``revision`` is 16 characters. ``alembic_version.version_num`` is
``VARCHAR(32)``, and a longer slug fails on the first real ``upgrade`` rather
than at import time -- which is how the retired ``0037`` learnt it.

--------------------------------------------------------------------------
THE DERIVATION BELOW IS A DELIBERATE, FROZEN COPY of ``app/core/slug.py``.
--------------------------------------------------------------------------

Do **not** "fix" it by writing ``from app.core.slug import slugify``. A
revision is replayed verbatim against production years from now, so a live
import silently rewrites history the day a later task changes ``slugify``:
the rows this file created would no longer be the rows it creates. Importing
under ``alembic/`` also shadows the third-party library, which is why
``_run_alembic`` in ``tests/test_migrations_postgres.py`` shells out.

``0001`` sets exactly this precedent -- it re-declares ``DEFAULT_TENANT_ID``
and ``LEGACY_ROLE_NAMES`` as local literals rather than importing them.
Copying a dozen lines is the cheaper mistake than an un-replayable migration,
and APRAS-58's clean-up is what the alternative costs. The two copies are
kept honest while this revision is the head: ``tests/test_slug.py`` pins
``slugify``'s behaviour and ``tests/test_migrations_postgres.py`` pins this
copy's output (``condominio-padrao``).

Revision ID: 0002_tenant_slug
Revises: 0001_initial_schema
Create Date: 2026-09-21 15:40:00.000000

"""
import re
import unicodedata
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '0002_tenant_slug'
down_revision: Union[str, Sequence[str], None] = '0001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

#: The frozen copy of ``app/core/slug.py``'s constants and rule. See the
#: module docstring: the duplication is the point.
_SLUG_MIN_LENGTH = 3
_SLUG_MAX_LENGTH = 64
_SLUG_MAX_BASE_LENGTH = 60
_SLUG_FALLBACK_BASE = 'condominio'
_SEPARATOR_RUN = re.compile(r'[^a-z0-9]+')


def _slugify(name: str) -> str:
    """Frozen copy of ``app.core.slug.slugify`` -- do not import the live one."""
    folded = unicodedata.normalize('NFKD', name)
    ascii_only = ''.join(ch for ch in folded if not unicodedata.combining(ch))
    ascii_only = ascii_only.encode('ascii', 'ignore').decode('ascii')

    hyphenated = _SEPARATOR_RUN.sub('-', ascii_only.lower()).strip('-')
    truncated = hyphenated[:_SLUG_MAX_BASE_LENGTH].strip('-')

    if len(truncated) < _SLUG_MIN_LENGTH:
        return _SLUG_FALLBACK_BASE
    return truncated


def _first_free_slug(base: str, taken: set) -> str:
    """Frozen copy of ``TenantService.first_free_slug``: smallest free ``-<n>``."""
    if base not in taken:
        return base
    n = 2
    while True:
        suffix = f'-{n}'
        head = base[:_SLUG_MAX_LENGTH - len(suffix)].rstrip('-')
        candidate = head + suffix
        if candidate not in taken:
            return candidate
        n += 1


def upgrade() -> None:
    """Add the column nullable, backfill, then constrain it."""
    op.add_column(
        'tenant',
        sa.Column('slug', sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True),
    )

    connection = op.get_bind()
    # Ordered by `(created_at, id)`, not by insertion order: the walk hands
    # out `-2` and `-3` in a fixed sequence, so two databases holding the same
    # rows are backfilled with the same slugs.
    rows = connection.execute(
        sa.text('SELECT id, name FROM tenant ORDER BY created_at, id')
    ).all()

    taken = set()
    for row in rows:
        slug = _first_free_slug(_slugify(row.name or ''), taken)
        taken.add(slug)
        connection.execute(
            sa.text('UPDATE tenant SET slug = :slug WHERE id = :id'),
            {'slug': slug, 'id': row.id},
        )

    op.alter_column(
        'tenant',
        'slug',
        existing_type=sqlmodel.sql.sqltypes.AutoString(length=64),
        nullable=False,
    )
    op.create_index(op.f('ix_tenant_slug'), 'tenant', ['slug'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_tenant_slug'), table_name='tenant')
    op.drop_column('tenant', 'slug')
