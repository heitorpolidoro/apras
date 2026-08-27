"""Database model for UserType."""

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column
from sqlmodel import Field, Relationship, SQLModel

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

    users: list["User"] = Relationship(
        back_populates="user_types", link_model=UserUserTypeLink
    )
