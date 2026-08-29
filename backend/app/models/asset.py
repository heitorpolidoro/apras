"""Models for assets and inventory management."""

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

from app.models.enums import AssetCategory, AssetCondition, MovementType


class Asset(SQLModel, table=True):
    """Asset or consumable inventory item."""

    __tablename__ = "asset"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(nullable=False, index=True)
    category: AssetCategory = Field(nullable=False, index=True)
    serial_number: str | None = Field(default=None, nullable=True, index=True)
    asset_tag: str | None = Field(default=None, nullable=True, unique=True, index=True)
    location: str = Field(nullable=False, index=True)
    acquisition_date: date | None = Field(default=None, nullable=True)
    acquisition_value: float | None = Field(default=None, nullable=True)
    condition: AssetCondition = Field(
        default=AssetCondition.BOM, nullable=False, index=True
    )
    is_consumable: bool = Field(default=False, nullable=False, index=True)
    current_quantity: int = Field(default=1, nullable=False)
    min_quantity: int | None = Field(default=None, nullable=True)
    unit_of_measure: str | None = Field(default="un", nullable=True)
    notes: str | None = Field(default=None, nullable=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), nullable=False
    )

    # Relationships
    movements: list["InventoryMovement"] = Relationship(
        back_populates="asset",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "InventoryMovement.created_at.desc()",
        },
    )


class InventoryMovement(SQLModel, table=True):
    """Audit log of stock entries, exits, adjustments, and asset write-offs."""

    __tablename__ = "inventory_movement"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    asset_id: UUID = Field(
        foreign_key="asset.id", nullable=False, index=True, ondelete="CASCADE"
    )
    movement_type: MovementType = Field(nullable=False, index=True)
    quantity: int = Field(nullable=False)
    previous_quantity: int = Field(nullable=False)
    new_quantity: int = Field(nullable=False)
    performed_by_id: UUID = Field(foreign_key="user.id", nullable=False, index=True)
    reason: str = Field(nullable=False)
    document_number: str | None = Field(default=None, nullable=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), nullable=False, index=True
    )

    # Relationships
    asset: Asset = Relationship(back_populates="movements")
