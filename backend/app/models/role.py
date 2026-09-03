"""Database model for Role."""

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column, Index
from sqlmodel import Field, Relationship, SQLModel

from .role_link import UserRoleLink
from .tenant import tenant_id_field

if TYPE_CHECKING:
    from .user import User


class Role(SQLModel, table=True):
    """A named, per-tenant bundle of permissions, managed by administrators.

    There are no system roles: every row is editable and deletable, including
    the six historically-named ones migration `0033` filled with the bundles
    the retired role enum used to grant.
    """

    __tablename__ = "role"
    # Per-tenant unique name (APRAS-41). IAM F5 (APRAS-49 §7.4) dropped the
    # second index with the `role` column it covered: there is no enum left
    # for a row to be "linked" to, and a role is now an ordinary, editable,
    # deletable row like any other.
    __table_args__ = (
        Index("ix_role_tenant_name", "tenant_id", "name", unique=True),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    # Tenant boundary (APRAS-41). Defaults to DEFAULT_TENANT_ID so ORM
    # inserts that omit it keep working; APRAS-42 replaces this with a
    # request-scoped acting tenant.
    tenant_id: UUID = tenant_id_field()
    name: str = Field(index=True)
    # A role's permission bundle (IAM F1). Portable JSON, NOT a Postgres
    # ARRAY: ARRAY does not compile against SQLite, and tests/conftest.py
    # builds the schema with SQLModel.metadata.create_all() on sqlite://.
    # NOTHING seeds this: every row - including the six historically-named
    # rows TenantService.ensure_legacy_roles creates - starts and stays [].
    # Migration `0033` is the one writer that ever put permissions in a row,
    # and it did it once, to preserve the sets the enum used to compute.
    permissions: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, server_default="[]"),
    )
    # Where a member of this role lands after login, or None (IAM F5,
    # APRAS-49 §10.4). Landing is a *preference*, not authorization: no
    # predicate over the catalogue separates "pin the gatekeeper to the gate"
    # from "the board can also open the gate", so the two role-shaped
    # redirects the enum switch expressed became data on the row. Validated
    # against a small allowlist of in-app paths on the write schemas -- an
    # open string would be an open redirect the moment `RootRedirect`
    # consumes it.
    landing_path: str | None = Field(default=None, nullable=True)

    users: list["User"] = Relationship(
        back_populates="roles", link_model=UserRoleLink
    )
