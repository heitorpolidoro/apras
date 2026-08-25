"""Database model for Resident."""

from datetime import date, datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel


from .enums import ResidentRelationship

if TYPE_CHECKING:
    from .lot import Lot
    from .user import User


class Resident(SQLModel, table=True):
    __tablename__ = "resident"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    lot_id: UUID = Field(
        foreign_key="lot.id", ondelete="CASCADE", nullable=False, index=True
    )
    user_id: UUID | None = Field(
        default=None, foreign_key="user.id", ondelete="SET NULL", nullable=True, index=True
    )
    full_name: str = Field(nullable=False)
    cpf: str = Field(index=True, nullable=False)
    rg: str | None = Field(default=None)
    birth_date: date | None = Field(default=None)
    phone: str | None = Field(default=None)
    email: str | None = Field(default=None, index=True)
    relationship_type: ResidentRelationship = Field(
        default=ResidentRelationship.TITULAR, nullable=False
    )
    is_active: bool = Field(default=True, nullable=False)
    notes: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    # Relationships
    lot: "Lot" = Relationship(back_populates="residents")
    user: Optional["User"] = Relationship(back_populates="residents")

