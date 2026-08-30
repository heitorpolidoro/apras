"""Pydantic schemas for purchase requests, quotes and decisions (APRAS-37)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import PurchaseRequestStatus

MAX_EXTRA_FIELDS = 20
MIN_JUSTIFICATION_LENGTH = 10


class QuoteExtraField(BaseModel):
    """One caller-defined extra field on a quote."""

    # NOTE: deliberately no `min_length=1` on `label`. Field-level constraints run
    # *before* any after-validator, so `min_length=1` would accept "   " and the
    # subsequent strip would silently store an empty label. Emptiness is therefore
    # checked below, after stripping, which is the only ordering that makes
    # `{"label": "   "}` a 422.
    label: str = Field(..., max_length=60)
    value: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def _normalize(self) -> "QuoteExtraField":
        self.label = self.label.strip()
        self.value = self.value.strip()
        if not self.label:
            raise ValueError("O rótulo do campo extra não pode ser vazio.")
        return self


def _validate_extra_fields(fields: list[QuoteExtraField]) -> None:
    """Enforce the list-level rules on an already-normalized extra-field list."""
    if len(fields) > MAX_EXTRA_FIELDS:
        raise ValueError(
            f"Um orçamento aceita no máximo {MAX_EXTRA_FIELDS} campos extras."
        )
    seen: set[str] = set()
    for field in fields:
        key = field.label.casefold()
        if key in seen:
            raise ValueError(f"Rótulo de campo extra duplicado: '{field.label}'.")
        seen.add(key)


class PurchaseRequestCreate(BaseModel):
    """Schema for creating a purchase request."""

    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    general_notes: str | None = Field(default=None, max_length=4000)


class PurchaseRequestUpdate(BaseModel):
    """Schema for updating a purchase request. All fields optional."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    general_notes: str | None = Field(default=None, max_length=4000)


class PurchaseQuoteCreate(BaseModel):
    """Schema for adding a supplier quote to a purchase request."""

    supplier_name: str = Field(..., min_length=1, max_length=255)
    supplier_contact: str | None = Field(default=None, max_length=255)
    unit_price: float = Field(..., ge=0)
    quantity: int = Field(..., gt=0)
    notes: str | None = Field(default=None, max_length=4000)
    extra_fields: list[QuoteExtraField] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_extra_fields(self) -> "PurchaseQuoteCreate":
        _validate_extra_fields(self.extra_fields)
        return self


class PurchaseQuoteUpdate(BaseModel):
    """Schema for updating a supplier quote. All fields optional."""

    supplier_name: str | None = Field(default=None, min_length=1, max_length=255)
    supplier_contact: str | None = Field(default=None, max_length=255)
    unit_price: float | None = Field(default=None, ge=0)
    quantity: int | None = Field(default=None, gt=0)
    notes: str | None = Field(default=None, max_length=4000)
    extra_fields: list[QuoteExtraField] | None = None

    @model_validator(mode="after")
    def _check_extra_fields(self) -> "PurchaseQuoteUpdate":
        if self.extra_fields is not None:
            _validate_extra_fields(self.extra_fields)
        return self


class PurchaseDecisionCreate(BaseModel):
    """Schema for recording the justified choice of one quote."""

    quote_id: UUID
    justification: str = Field(
        ..., min_length=MIN_JUSTIFICATION_LENGTH, max_length=2000
    )

    @model_validator(mode="after")
    def _check_justification(self) -> "PurchaseDecisionCreate":
        if len(self.justification.strip()) < MIN_JUSTIFICATION_LENGTH:
            raise ValueError(
                "A justificativa deve ter ao menos "
                f"{MIN_JUSTIFICATION_LENGTH} caracteres."
            )
        return self


class PurchaseQuoteRead(BaseModel):
    """Schema for reading a supplier quote."""

    id: UUID
    purchase_request_id: UUID
    supplier_name: str
    supplier_contact: str | None = None
    unit_price: float
    quantity: int
    notes: str | None = None
    extra_fields: list[QuoteExtraField] = Field(default_factory=list)
    total_price: float = 0.0
    created_by_id: UUID
    created_by_name: str | None = None
    is_selected: bool = False
    is_lowest_price: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def _compute_total(self) -> "PurchaseQuoteRead":
        self.total_price = round(self.unit_price * self.quantity, 2)
        return self


class PurchaseDecisionRead(BaseModel):
    """Schema for reading a recorded decision."""

    id: UUID
    quote_id: UUID
    quote_supplier_name: str | None = None
    quote_total_price: float | None = None
    justification: str
    decided_by_id: UUID
    decided_by_name: str | None = None
    decided_at: datetime
    is_current: bool = False

    model_config = ConfigDict(from_attributes=True)


class PurchaseRequestRead(BaseModel):
    """Schema for reading a purchase request as a list row."""

    id: UUID
    title: str
    description: str | None = None
    general_notes: str | None = None
    status: PurchaseRequestStatus
    requested_by_id: UUID
    requested_by_name: str | None = None
    quote_count: int = 0
    lowest_quote_total: float | None = None
    selected_quote_id: UUID | None = None
    selected_quote_total: float | None = None
    decision_justification: str | None = None
    decided_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PurchaseRequestDetailRead(PurchaseRequestRead):
    """Purchase request detail with quotes and the decision history."""

    quotes: list[PurchaseQuoteRead] = Field(default_factory=list)
    decisions: list[PurchaseDecisionRead] = Field(default_factory=list)
    current_decision: PurchaseDecisionRead | None = None


class PaginatedPurchaseRequestRead(BaseModel):
    """Paginated list of purchase requests."""

    items: list[PurchaseRequestRead]
    total: int
    skip: int
    limit: int


class PurchaseSummaryRead(BaseModel):
    """Summary metrics for the purchase quotation dashboard."""

    open_count: int
    decided_count: int
    cancelled_count: int
    total_selected_value: float
