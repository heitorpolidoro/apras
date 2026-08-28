"""Database model for UserType."""

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column
from sqlmodel import Field, Relationship, SQLModel

from .enums import UserRole
from .user_type_link import UserUserTypeLink

if TYPE_CHECKING:
    from .user import User


class UserType(SQLModel, table=True):
    """Database model for user type labels managed by administrators."""

    __tablename__ = "user_type"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True, unique=True)
    # Portable JSON column (NOT a Postgres ARRAY): ARRAY does not compile
    # against SQLite, and tests/conftest.py creates the schema via
    # SQLModel.metadata.create_all() against a sqlite:// in-memory engine
    # for every test in the backend suite.
    allowed_menus: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, server_default="[]"),
    )
    # Identifies a UserType implicitly linked to a UserRole (APRAS-9): at
    # most one row per role value, enforced by `unique=True`. NULL (the
    # default, for regular admin-created types) is never counted as a
    # duplicate by a UNIQUE constraint on either Postgres or SQLite, so
    # this does not limit the number of admin-created types. Only ever set
    # by the seeding migration, never through the create/update API.
    role: UserRole | None = Field(default=None, nullable=True, unique=True)

    users: list["User"] = Relationship(
        back_populates="user_types", link_model=UserUserTypeLink
    )
