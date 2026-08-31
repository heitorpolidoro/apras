"""Database model for Category."""

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Index
from sqlmodel import Field, Relationship, SQLModel

from app.models.tenant import tenant_id_field

if TYPE_CHECKING:
    from .task import Task


class Category(SQLModel, table=True):
    """
    SQLModel for the Category entity.

    Attributes:
        id: Unique identifier for the category.
        name: Unique name.
        color: Hex code for the category.
        is_active: Whether the category is active.
    """

    # `name` is unique *within a tenant*, not globally (APRAS-41): two
    # condominiums may both have a "Manutenção" category. The plain
    # `ix_category_name` index survives for lookups by name.
    __table_args__ = (Index("ix_category_tenant_name", "tenant_id", "name", unique=True),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    # Tenant boundary (APRAS-41). Defaults to DEFAULT_TENANT_ID so ORM
    # inserts that omit it keep working; APRAS-42 replaces this with a
    # request-scoped acting tenant.
    tenant_id: UUID = tenant_id_field()
    name: str = Field(index=True)
    color: str = Field(default="#808080")
    is_active: bool = Field(default=True)

    # Relationships
    tasks: list["Task"] = Relationship(back_populates="category")
