"""Database model for Package (encomendas) tracking."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

from .enums import PackageStatus

if TYPE_CHECKING:
    from .lot import Lot
    from .user import User


class Package(SQLModel, table=True):
    """A package received at the gatekeeper's desk on behalf of a lot."""

    __tablename__ = "package"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    lot_id: UUID = Field(
        foreign_key="lot.id", ondelete="CASCADE", nullable=False, index=True
    )
    received_by_id: UUID | None = Field(
        default=None, foreign_key="user.id", ondelete="SET NULL", nullable=True
    )
    description: str | None = Field(default=None)
    carrier: str | None = Field(default=None)
    received_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    status: PackageStatus = Field(
        default=PackageStatus.AWAITING_PICKUP, nullable=False, index=True
    )
    picked_up_at: datetime | None = Field(default=None)
    picked_up_by_id: UUID | None = Field(
        default=None, foreign_key="user.id", ondelete="SET NULL", nullable=True
    )
    picked_up_by_notes: str | None = Field(default=None)

    # Relationships
    lot: "Lot" = Relationship()
    received_by: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Package.received_by_id]"}
    )
    picked_up_by: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Package.picked_up_by_id]"}
    )
