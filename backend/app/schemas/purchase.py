"""Pydantic schemas for purchase requests, quotes and decisions (APRAS-37)."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.money import ZERO, Money, MoneyIn, quantize_money
from app.models.enums import PurchaseRequestStatus

MAX_EXTRA_FIELDS = 20
MIN_JUSTIFICATION_LENGTH = 10

#: Longest enumeration a request may carry (APRAS-73 D6). A 422, never a
#: truncation -- the style :data:`MAX_EXTRA_FIELDS` set.
MAX_REQUEST_ITEMS = 50

#: Longest list of priced lines one quote may carry (APRAS-73 D6).
MAX_QUOTE_ITEMS = 50

#: Longest description of a line, on both sides of the grid.
_ITEM_DESCRIPTION_MAX_LENGTH = 255

#: Longest offered model a quote line may name.
_ITEM_MODEL_MAX_LENGTH = 120


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


class PurchaseRequestItemIn(BaseModel):
    """One enumerated line on the way in (APRAS-73 D1).

    ``id`` is what makes an update a *rewrite by identity* rather than a
    delete-and-recreate: a resubmitted id keeps the row, and every quote cell
    attached to it (D7). ``position`` is deliberately absent -- the server
    assigns it from the submitted index and never trusts the client.
    """

    id: UUID | None = None
    # No `min_length=1`: a field-level constraint runs before the
    # after-validator, so it would accept "   " and store an empty line. The
    # emptiness check is below, after stripping -- the same ordering
    # `QuoteExtraField` documents.
    description: str = Field(..., max_length=_ITEM_DESCRIPTION_MAX_LENGTH)
    quantity: int = Field(..., gt=0)

    @model_validator(mode="after")
    def _normalize(self) -> "PurchaseRequestItemIn":
        self.description = self.description.strip()
        if not self.description:
            raise ValueError("A descrição do item não pode ser vazia.")
        return self


def _validate_request_items(items: list[PurchaseRequestItemIn]) -> None:
    """The list-level rule on an already-normalized request enumeration."""
    if len(items) > MAX_REQUEST_ITEMS:
        raise ValueError(f"Um pedido aceita no máximo {MAX_REQUEST_ITEMS} itens.")


class PurchaseRequestItemRead(BaseModel):
    """One enumerated line on the way out."""

    id: UUID
    description: str
    quantity: int
    position: int

    model_config = ConfigDict(from_attributes=True)


class PurchaseRequestCreate(BaseModel):
    """Schema for creating a purchase request."""

    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    general_notes: str | None = Field(default=None, max_length=4000)
    #: Optional: a request may enumerate **zero** lines (D6) -- the
    #: pre-APRAS-73 world, and what the migration produces.
    items: list[PurchaseRequestItemIn] | None = None

    @model_validator(mode="after")
    def _check_items(self) -> "PurchaseRequestCreate":
        if self.items is not None:
            _validate_request_items(self.items)
        return self


class PurchaseRequestUpdate(BaseModel):
    """Schema for updating a purchase request. All fields optional."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    general_notes: str | None = Field(default=None, max_length=4000)
    #: When present, it **replaces** the whole enumeration (D7).
    items: list[PurchaseRequestItemIn] | None = None

    @model_validator(mode="after")
    def _check_items(self) -> "PurchaseRequestUpdate":
        if self.items is not None:
            _validate_request_items(self.items)
        return self


class PurchaseQuoteItemIn(BaseModel):
    """One priced line on the way in (APRAS-73 D2, D3).

    ``request_item_id`` and the ``description``/``quantity`` pair are an
    **exclusive-or**, so no fact is stored twice: a line answering a request
    line reads *what* and *how many* through that line, and only a supplier's
    own extra line carries them itself. Any other combination is a 422.
    """

    request_item_id: UUID | None = None
    model: str | None = Field(default=None, max_length=_ITEM_MODEL_MAX_LENGTH)
    unit_price: MoneyIn = Field(..., ge=0)
    description: str | None = Field(
        default=None, max_length=_ITEM_DESCRIPTION_MAX_LENGTH
    )
    quantity: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def _check_exclusive_or(self) -> "PurchaseQuoteItemIn":
        if self.model is not None:
            self.model = self.model.strip() or None
        if self.description is not None:
            self.description = self.description.strip()

        if self.request_item_id is not None:
            if self.description is not None or self.quantity is not None:
                raise ValueError(
                    "Um item ligado a uma linha do pedido não pode ter "
                    "descrição nem quantidade próprias."
                )
            return self

        if not self.description or self.quantity is None:
            raise ValueError(
                "Um item avulso do orçamento precisa de descrição e quantidade."
            )
        return self


class PurchaseQuoteItemRead(BaseModel):
    """One priced line on the way out.

    ``description`` and ``quantity`` are **echoed** -- copied from the
    request line when the item is linked -- so the grid renders from the
    quote payload alone while storage stays normalised (D3).
    """

    id: UUID
    request_item_id: UUID | None = None
    model: str | None = None
    unit_price: Money
    description: str
    quantity: int
    position: int
    line_total: Money = ZERO

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def _compute_line_total(self) -> "PurchaseQuoteItemRead":
        self.line_total = quantize_money(self.unit_price * self.quantity)
        return self


def _validate_quote_items(items: list[PurchaseQuoteItemIn]) -> None:
    """The list-level rules on an already-normalized list of priced lines."""
    if len(items) > MAX_QUOTE_ITEMS:
        raise ValueError(f"Um orçamento aceita no máximo {MAX_QUOTE_ITEMS} itens.")
    seen: set[UUID] = set()
    for item in items:
        if item.request_item_id is None:
            continue
        if item.request_item_id in seen:
            raise ValueError(
                "O mesmo item do pedido foi cotado duas vezes neste orçamento."
            )
        seen.add(item.request_item_id)


class PurchaseQuoteCreate(BaseModel):
    """Schema for adding a supplier quote to a purchase request."""

    supplier_name: str = Field(..., min_length=1, max_length=255)
    supplier_contact: str | None = Field(default=None, max_length=255)
    #: Required, and never empty (D6): a zero-line quote would have no price
    #: and would make `is_lowest_price` and the gap panel meaningless.
    items: list[PurchaseQuoteItemIn] = Field(..., min_length=1)
    notes: str | None = Field(default=None, max_length=4000)
    extra_fields: list[QuoteExtraField] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_lists(self) -> "PurchaseQuoteCreate":
        _validate_extra_fields(self.extra_fields)
        _validate_quote_items(self.items)
        return self


class PurchaseQuoteUpdate(BaseModel):
    """Schema for updating a supplier quote. All fields optional."""

    supplier_name: str | None = Field(default=None, min_length=1, max_length=255)
    supplier_contact: str | None = Field(default=None, max_length=255)
    #: When present it **replaces** the whole list, and ``[]`` is a 422 --
    #: not a way to empty a quote (D6).
    items: list[PurchaseQuoteItemIn] | None = Field(default=None, min_length=1)
    notes: str | None = Field(default=None, max_length=4000)
    extra_fields: list[QuoteExtraField] | None = None

    @model_validator(mode="after")
    def _check_lists(self) -> "PurchaseQuoteUpdate":
        if self.extra_fields is not None:
            _validate_extra_fields(self.extra_fields)
        if self.items is not None:
            _validate_quote_items(self.items)
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
    items: list[PurchaseQuoteItemRead] = Field(default_factory=list)
    #: Linked items **only** (D5): a supplier's own extra line counts toward
    #: the total and never toward coverage.
    quoted_item_count: int = 0
    #: ``quoted_item_count == len(request.items)``. Set by the service, which
    #: is the only layer that knows the request's enumeration; the default is
    #: the trivially-complete case of a request that enumerates nothing.
    is_complete: bool = True
    notes: str | None = None
    extra_fields: list[QuoteExtraField] = Field(default_factory=list)
    # The supplier document (APRAS-63 D1). Read-only: `PurchaseQuoteCreate`
    # and `PurchaseQuoteUpdate` deliberately carry neither, because the file
    # only ever arrives as multipart on the two attachment routes.
    attachment_url: str | None = None
    attachment_filename: str | None = None
    total_price: Money = Decimal("0.00")
    created_by_id: UUID
    created_by_name: str | None = None
    is_selected: bool = False
    is_lowest_price: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def _compute_total(self) -> "PurchaseQuoteRead":
        """The total, derived from the lines and from nothing else (D8).

        The sum is seeded with :data:`~app.core.money.ZERO` so an (impossible)
        empty list yields ``Decimal("0.00")`` rather than ``int`` 0, and the
        result is quantized **once more**. That second call is deliberately
        redundant over exact cents -- every ``line_total`` is already at
        scale -- and is kept as a defence, not as live rounding: do not
        remove it as dead code, and do not read it as rounding anything.
        """
        self.quoted_item_count = sum(
            1 for item in self.items if item.request_item_id is not None
        )
        self.total_price = quantize_money(
            sum((item.line_total for item in self.items), ZERO)
        )
        return self


class PurchaseDecisionRead(BaseModel):
    """Schema for reading a recorded decision."""

    id: UUID
    quote_id: UUID
    quote_supplier_name: str | None = None
    quote_total_price: Money | None = None
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
    #: The enumeration the quotes price, in ``position`` order (D1). Empty on
    #: every request migrated from before APRAS-73.
    items: list[PurchaseRequestItemRead] = Field(default_factory=list)
    quote_count: int = 0
    #: Since APRAS-73 D10 this is the lowest total among the **complete**
    #: quotes, and ``None`` when no quote covers the whole enumeration.
    lowest_quote_total: Money | None = None
    selected_quote_id: UUID | None = None
    selected_quote_total: Money | None = None
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
    total_selected_value: Money
