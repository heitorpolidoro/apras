"""Database model for User."""

from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

from .enums import UserRole
from .user_type import UserType
from .user_type_link import UserUserTypeLink

if TYPE_CHECKING:
    from .task import Task


class User(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(index=True, unique=True)
    hashed_password: str
    full_name: str
    role: UserRole = Field(default=UserRole.DIRECTOR)
    is_active: bool = Field(default=True)
    cpf: str = Field(unique=True, index=True)

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
