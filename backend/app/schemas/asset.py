"""Pydantic schemas for assets and inventory movements."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import AssetCategory, AssetCondition, MovementType


class AssetBase(BaseModel):
    """Base fields for an asset."""

    name: str = Field(..., min_length=1, max_length=255)
    category: AssetCategory
    serial_number: str | None = Field(default=None, max_length=100)
    asset_tag: str | None = Field(default=None, max_length=100)
    location: str = Field(..., min_length=1, max_length=255)
    acquisition_date: date | None = None
    acquisition_value: float | None = Field(default=None, ge=0)
    condition: AssetCondition = AssetCondition.BOM
    is_consumable: bool = False
    current_quantity: int = Field(default=1, ge=0)
    min_quantity: int | None = Field(default=None, ge=0)
    unit_of_measure: str | None = Field(default="un", max_length=50)
    notes: str | None = None


class AssetCreate(AssetBase):
    """Schema for creating a new asset."""


class AssetUpdate(BaseModel):
    """Schema for updating an existing asset. All fields optional."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    category: AssetCategory | None = None
    serial_number: str | None = Field(default=None, max_length=100)
    asset_tag: str | None = Field(default=None, max_length=100)
    location: str | None = Field(default=None, min_length=1, max_length=255)
    acquisition_date: date | None = None
    acquisition_value: float | None = Field(default=None, ge=0)
    condition: AssetCondition | None = None
    is_consumable: bool | None = None
    min_quantity: int | None = Field(default=None, ge=0)
    unit_of_measure: str | None = Field(default=None, max_length=50)
    notes: str | None = None


class AssetRead(AssetBase):
    """Schema for reading an asset."""

    id: UUID
    is_low_stock: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def _compute_low_stock(self) -> "AssetRead":
        if self.is_consumable and self.min_quantity is not None:
            self.is_low_stock = self.current_quantity <= self.min_quantity
        else:
            self.is_low_stock = False
        return self


class InventoryMovementCreate(BaseModel):
    """Schema for recording a new inventory or asset movement."""

    movement_type: MovementType
    quantity: int = Field(..., description="Quantity to move or adjust to")
    reason: str = Field(..., min_length=1)
    document_number: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def _validate_quantity(self) -> "InventoryMovementCreate":
        if self.movement_type == MovementType.AJUSTE_INVENTARIO:
            if self.quantity < 0:
                raise ValueError("quantity must be non-negative for AJUSTE_INVENTARIO")
        elif self.quantity <= 0:
            raise ValueError(
                "quantity must be greater than 0 for ENTRADA, SAIDA, "
                "and BAIXA_PATRIMONIAL"
            )
        return self


class InventoryMovementRead(BaseModel):
    """Schema for reading an inventory movement."""

    id: UUID
    asset_id: UUID
    movement_type: MovementType
    quantity: int
    previous_quantity: int
    new_quantity: int
    performed_by_id: UUID
    performed_by_name: str | None = None
    asset_name: str | None = None
    reason: str
    document_number: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedAssetRead(BaseModel):
    """Paginated list of assets."""

    items: list[AssetRead]
    total: int
    skip: int
    limit: int


class PaginatedInventoryMovementRead(BaseModel):
    """Paginated list of inventory movements."""

    items: list[InventoryMovementRead]
    total: int
    skip: int
    limit: int


class AssetDetailRead(AssetRead):
    """Asset detail including its movement history."""

    movements: list[InventoryMovementRead] = []


class AssetSummaryRead(BaseModel):
    """Summary metrics for asset and inventory dashboard."""

    total_assets: int
    total_consumables: int
    low_stock_count: int
    total_patrimonial_value: float
