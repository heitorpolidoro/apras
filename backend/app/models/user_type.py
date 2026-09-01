"""Database model for UserType."""

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column, Index
from sqlmodel import Field, Relationship, SQLModel

from .enums import UserRole
from .user_type_link import UserUserTypeLink
from .tenant import tenant_id_field

if TYPE_CHECKING:
    from .user import User


class UserType(SQLModel, table=True):
    """Database model for user type labels managed by administrators."""

    __tablename__ = "user_type"
    # Both uniques are per-tenant (APRAS-41). `role` previously carried an
    # anonymous column-level UNIQUE in the model but a named unique index in
    # Postgres (migration 0018); it is now an explicit named index in both,
    # so the SQLite schema built by create_all() and the migrated Postgres
    # schema agree. A composite unique still allows many NULL `role` values
    # (NULLs never collide in a unique index on Postgres or SQLite) and still
    # rejects a duplicate role within one tenant.
    __table_args__ = (
        Index("ix_user_type_tenant_name", "tenant_id", "name", unique=True),
        Index("ix_user_type_tenant_role", "tenant_id", "role", unique=True),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    # Tenant boundary (APRAS-41). Defaults to DEFAULT_TENANT_ID so ORM
    # inserts that omit it keep working; APRAS-42 replaces this with a
    # request-scoped acting tenant.
    tenant_id: UUID = tenant_id_field()
    name: str = Field(index=True)
    # Portable JSON column (NOT a Postgres ARRAY): ARRAY does not compile
    # against SQLite, and tests/conftest.py creates the schema via
    # SQLModel.metadata.create_all() against a sqlite:// in-memory engine
    # for every test in the backend suite.
    allowed_menus: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, server_default="[]"),
    )
    # A role's permission bundle (IAM F1). Portable JSON, NOT a Postgres
    # ARRAY, for the same reason `allowed_menus` is: tests/conftest.py builds
    # the schema with SQLModel.metadata.create_all() on sqlite://.
    # NOTHING seeds this: every row - including the six role-linked rows
    # TenantService.ensure_role_types creates - starts and stays [].
    permissions: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, server_default="[]"),
    )
    # Identifies a UserType implicitly linked to a UserRole (APRAS-9): at
    # most one row per role value, enforced by `unique=True`. NULL (the
    # default, for regular admin-created types) is never counted as a
    # duplicate by a UNIQUE constraint on either Postgres or SQLite, so
    # this does not limit the number of admin-created types. Only ever set
    # by the seeding migration, never through the create/update API.
    role: UserRole | None = Field(default=None, nullable=True)

    users: list["User"] = Relationship(
        back_populates="user_types", link_model=UserUserTypeLink
    )
