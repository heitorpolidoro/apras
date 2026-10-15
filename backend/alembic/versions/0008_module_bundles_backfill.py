"""module bundles backfill

APRAS-128 groups coupled modules into bundles that are always entirely on or
entirely off. New writes are refused when they split a bundle; this revision
repairs the data that was written before that rule existed.

Data only, no schema change. For every bundle, UPWARD (the operator's
decision): a bundle that is partly on becomes entirely on.

* ``tenant.disabled_modules`` -- when some members are disabled and some are
  not, every member leaves the list (the missing members are switched ON).
* ``plan.included_modules`` and ``tenant_subscription.courtesy_modules`` --
  when some members are listed and some are not, the missing members are
  added.

A bundle that is entirely on or entirely off is untouched, so the revision is
idempotent. No ``role.permissions`` row is touched. The downgrade is a no-op:
the data is not re-split.

The bundle declaration below is a frozen copy of ``MODULE_BUNDLES`` in
``app/core/permissions.py`` as of APRAS-128. This file imports nothing from
``app/``: a revision is replayed verbatim years from now and a live import
would silently change what a replay does.

``revision`` is 28 characters (``alembic_version.version_num`` is
``VARCHAR(32)``).

Revision ID: 0008_module_bundles_backfill
Revises: 0007_milestone_detail_json
Create Date: 2026-10-15 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0008_module_bundles_backfill"
down_revision: Union[str, Sequence[str], None] = "0007_milestone_detail_json"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

BUNDLES = (
    frozenset({"tasks", "categories"}),
    frozenset({"reservations", "spaces"}),
    frozenset({"assets", "inventory"}),
    frozenset({"visitors", "authorizations", "gate"}),
)

_TENANT = sa.table("tenant", sa.column("id"), sa.column("disabled_modules", sa.JSON()))
_PLAN = sa.table("plan", sa.column("id"), sa.column("included_modules", sa.JSON()))
_SUBSCRIPTION = sa.table(
    "tenant_subscription",
    sa.column("id"),
    sa.column("courtesy_modules", sa.JSON()),
)


def _is_split(listed: set) -> bool:
    return any(0 < len(listed & bundle) < len(bundle) for bundle in BUNDLES)


def backfill(bind) -> None:
    """Make every stored module list whole, upward. Idempotent."""
    for row in bind.execute(sa.select(_TENANT.c.id, _TENANT.c.disabled_modules)):
        disabled = set(row.disabled_modules or [])
        if not _is_split(disabled):
            continue
        for bundle in BUNDLES:
            if 0 < len(disabled & bundle) < len(bundle):
                disabled -= bundle
        bind.execute(
            sa.update(_TENANT)
            .where(_TENANT.c.id == row.id)
            .values(disabled_modules=sorted(disabled))
        )

    for table, column in (
        (_PLAN, _PLAN.c.included_modules),
        (_SUBSCRIPTION, _SUBSCRIPTION.c.courtesy_modules),
    ):
        for row in bind.execute(sa.select(table.c.id, column)):
            listed = set(row[1] or [])
            if not _is_split(listed):
                continue
            for bundle in BUNDLES:
                if 0 < len(listed & bundle) < len(bundle):
                    listed |= bundle
            bind.execute(
                sa.update(table)
                .where(table.c.id == row.id)
                .values({column.name: sorted(listed)})
            )


def upgrade() -> None:
    backfill(op.get_bind())


def downgrade() -> None:
    """No-op: the data is not re-split."""
