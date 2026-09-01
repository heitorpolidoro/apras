"""Database models for Tenant and UserTenantLink (APRAS-41).

This module introduces the **tenant boundary** — the first slice of the
multi-tenant SaaS chain APRAS-41 → APRAS-42 → APRAS-43 → APRAS-38. It is a
*data-layer only* change: every existing endpoint keeps behaving exactly as
it did before it landed.

The tenancy rule, stated once so the partition of the schema is reviewable:

* A table carries a **direct ``tenant_id``** if a request-scoped filter will
  have to constrain it itself — i.e. it is reachable by at least one route
  that lists it or fetches it by its own id without a tenant-scoped parent's
  id already in the path, or it has no NOT NULL FK to a directly-scoped
  table. Those 27 tables use :func:`tenant_id_field`.
* A table **inherits** its tenant when it is only ever reached through a
  scoped parent and holds a NOT NULL FK to a directly-scoped parent. Adding
  ``tenant_id`` there would be a denormalisation with a second, forgeable
  source of truth (a child row whose ``tenant_id`` disagrees with its
  parent's) and no query it makes cheaper.
* ``user`` is **global**: a user is one identity that belongs to zero or more
  tenants through :class:`UserTenantLink`, so ``user.email`` and ``user.cpf``
  stay globally unique.

Hand-offs deliberately left open by this slice:

* **APRAS-42** owns request-scoped tenant resolution. It replaces the
  Python-side :data:`DEFAULT_TENANT_ID` default on every scoped model with a
  server-resolved acting tenant, and may then drop the matching
  ``server_default``.
* **APRAS-42** also owns making ``get_effective_user_type_ids``
  (``app/api/deps.py``) tenant-aware. It is tenant-blind today
  (``select(UserType).where(UserType.role == user.role)).first()``) and is
  deliberately **not** touched here: after this migration's backfill every
  ``user_type`` row lives in the default tenant with exactly one row per
  role, so ``.first()`` returns exactly what it returns today. For the same
  reason ``POST /api/v1/tenants`` does **not** seed role-linked ``UserType``
  rows for a new tenant — that would make ``.first()`` non-deterministic.
* **APRAS-43** added the ``is_tenant_admin`` column to
  :class:`UserTenantLink` (migration ``0029``); that is why the link table
  has a surrogate ``id`` primary key (mirroring ``UserLotLink``) rather than
  a composite one. The capability is deliberately a property of the
  *membership*, not of ``user.role``: one global identity needs a different
  answer per tenant, and a new ``UserRole`` value would silently alter the
  54 role comparisons spread over 22 service modules.
"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import UniqueConstraint, text
from sqlmodel import Field, SQLModel

# The well-known, fixed id of the tenant every pre-existing row is migrated
# into. It is a literal (never generated) so the migration's backfill, the
# columns' server_default and the models' Python-side default can all agree
# on the same value without a lookup.
DEFAULT_TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")
DEFAULT_TENANT_NAME = "Condomínio Padrão"


def tenant_id_field() -> Any:
    """Return the ``tenant_id`` Field shared by every directly-scoped model.

    Both defaults are deliberate and do different jobs:

    * the Python-side ``default`` keeps every ORM insert that omits
      ``tenant_id`` — i.e. all of today's application code and all of today's
      tests — landing in the default tenant;
    * the ``server_default`` keeps raw-SQL / ``bulk_insert`` paths and any
      not-yet-updated writer from violating ``NOT NULL``, and makes the
      SQLite schema built by ``SQLModel.metadata.create_all()`` match the one
      Alembic builds on Postgres.

    ``ondelete="RESTRICT"`` is what makes tenant deletion impossible while
    data exists; deactivation is ``PATCH /api/v1/tenants/{id}``
    ``{"is_active": false}`` instead.
    """
    return Field(
        default=DEFAULT_TENANT_ID,
        foreign_key="tenant.id",
        ondelete="RESTRICT",
        nullable=False,
        index=True,
        sa_column_kwargs={"server_default": text(f"'{DEFAULT_TENANT_ID}'")},
    )


class Tenant(SQLModel, table=True):
    """One condominium/association installation.

    ``name`` is globally unique on purpose, so the administrator's tenant
    list is unambiguous. ``is_active`` is a soft-deactivation flag: there is
    no ``DELETE /api/v1/tenants/{id}``, both because the scoped foreign keys
    are ``RESTRICT`` and because deactivation is the intended operation.
    Nothing consumes ``is_active`` in this slice — APRAS-42 does.
    """

    __tablename__ = "tenant"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True, unique=True, nullable=False)
    is_active: bool = Field(default=True, nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)


class UserTenantLink(SQLModel, table=True):
    """Membership of a (global) user in a tenant.

    Multi-membership is first class: the same user may be linked to any
    number of tenants. Only the same ``(user_id, tenant_id)`` pair twice is a
    conflict, enforced by ``uq_user_tenant_link_user_tenant``.
    """

    __tablename__ = "user_tenant_link"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "tenant_id", name="uq_user_tenant_link_user_tenant"
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(
        foreign_key="user.id", ondelete="CASCADE", nullable=False, index=True
    )
    tenant_id: UUID = Field(
        foreign_key="tenant.id", ondelete="CASCADE", nullable=False, index=True
    )
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    # Administrator-level permission restricted to this one tenant
    # (APRAS-43). The ``server_default`` mirrors what ``tenant_id_field()``
    # does and for the same reason: the SQLite schema built by
    # ``SQLModel.metadata.create_all()`` in the test harness and the Postgres
    # schema built by Alembic must agree, and no pre-existing writer of this
    # row (``app/seed.py``, ``POST /auth/signup``, migration ``0028``) passes
    # the field.
    is_tenant_admin: bool = Field(
        default=False,
        nullable=False,
        sa_column_kwargs={"server_default": text("false")},
    )
