"""Database model for User."""

from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlmodel import Field, Relationship, SQLModel

from .role import Role
from .role_link import UserRoleLink

if TYPE_CHECKING:
    from .lot import UserLotLink
    from .resident import Resident
    from .task import Task


class User(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(index=True, unique=True)
    hashed_password: str
    full_name: str
    is_active: bool = Field(default=True)
    cpf: str = Field(unique=True, index=True)
    phone: str | None = Field(default=None)
    address: str | None = Field(default=None)
    # Global, install-wide administrator (APRAS-47). The counterpart of
    # `user_tenant_link.is_tenant_admin`, which is the same power scoped to
    # one tenant (APRAS-43). `server_default` mirrors `is_tenant_admin`'s, and
    # for the same reason: the SQLite schema `SQLModel.metadata.create_all()`
    # builds in `backend/tests/conftest.py` and the Postgres schema Alembic
    # builds must agree, and no pre-existing writer of this row passes the
    # field.
    is_superuser: bool = Field(
        default=False,
        nullable=False,
        sa_column_kwargs={"server_default": text("false")},
    )

    @property
    def username(self) -> str:
        return self.email.split("@")[0]

    # Relationships
    created_tasks: list["Task"] = Relationship(
        back_populates="creator",
        sa_relationship_kwargs={"foreign_keys": "Task.created_by_id"},
    )
    assigned_tasks: list["Task"] = Relationship(
        back_populates="assignee",
        sa_relationship_kwargs={"foreign_keys": "Task.assigned_to_id"},
    )
    roles: list[Role] = Relationship(
        back_populates="users", link_model=UserRoleLink
    )
    lot_links: list["UserLotLink"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    residents: list["Resident"] = Relationship(
        back_populates="user",
    )


