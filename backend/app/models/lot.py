"""Database models for Lot and UserLotLink."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

from .enums import LotAssociationType, LotStatus

if TYPE_CHECKING:
    from .resident import Resident
    from .user import User


class UserLotLink(SQLModel, table=True):
    __tablename__ = "user_lot_link"
    __table_args__ = (
        UniqueConstraint("user_id", "lot_id", name="uq_user_lot_link_user_lot"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(
        foreign_key="user.id", ondelete="CASCADE", nullable=False, index=True
    )
    lot_id: UUID = Field(
        foreign_key="lot.id", ondelete="CASCADE", nullable=False, index=True
    )
    association_type: LotAssociationType = Field(
        default=LotAssociationType.PROPRIETARIO, nullable=False
    )
    is_primary: bool = Field(default=False, nullable=False)
    start_date: datetime | None = Field(default=None)
    end_date: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    # Relationships
    user: "User" = Relationship(back_populates="lot_links")
    lot: "Lot" = Relationship(back_populates="user_links")


class Lot(SQLModel, table=True):
    __tablename__ = "lot"
    __table_args__ = (
        UniqueConstraint("block", "lot_number", name="uq_lot_block_lot_number"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    block: str = Field(index=True, nullable=False)
    lot_number: str = Field(index=True, nullable=False)
    address: str | None = Field(default=None)
    postal_code: str | None = Field(default=None)
    area_sqm: float | None = Field(default=None)
    fraction_ideal: float | None = Field(default=None)
    status: LotStatus = Field(default=LotStatus.VACANT, nullable=False)
    notes: str | None = Field(default=None)
    is_deleted: bool = Field(default=False, nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    # Relationships
    user_links: list[UserLotLink] = Relationship(
        back_populates="lot", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    residents: list["Resident"] = Relationship(
        back_populates="lot", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

