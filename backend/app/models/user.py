"""Database model for User."""

from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlmodel import Field, Relationship, SQLModel

from .enums import UserRole
from .user_type import UserType
from .user_type_link import UserUserTypeLink

if TYPE_CHECKING:
    from .lot import UserLotLink
    from .resident import Resident
    from .task import Task


class User(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(index=True, unique=True)
    hashed_password: str
    full_name: str
    role: UserRole = Field(default=UserRole.DIRECTOR)
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

    def __init__(self, **data: Any) -> None:
        """TRANSITIONAL (IAM F3 -> F5).

        While `User.role` still exists, creating a user with role
        ADMINISTRATOR defaults `is_superuser` to True — exactly the rule
        migration 0031 applies to the rows that predate it, so the two paths
        agree and the column is complete. An explicit `is_superuser=` always
        wins, and SQLAlchemy does **not** call `__init__` when loading a row,
        so the column stays the single source of truth for every reader: a row
        stored with role ADMINISTRATOR and `is_superuser=False` reads back as a
        non-superuser. F5 deletes this together with the enum.

        `__init__` rather than a `before_insert` mapper event because it also
        covers users built in memory and never flushed (unit-level calls into
        `app.api.deps`), and because not being reached on DB load is exactly
        what keeps the negative case constructible.
        """
        if "is_superuser" not in data and data.get("role") == UserRole.ADMINISTRATOR:
            data["is_superuser"] = True
        super().__init__(**data)

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
    user_types: list[UserType] = Relationship(
        back_populates="users", link_model=UserUserTypeLink
    )
    lot_links: list["UserLotLink"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    residents: list["Resident"] = Relationship(
        back_populates="user",
    )


