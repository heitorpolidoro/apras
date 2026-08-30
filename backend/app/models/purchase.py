"""Models for purchase requests, supplier quotes and the justified choice (APRAS-37)."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column
from sqlmodel import Field, Relationship, SQLModel

from app.models.enums import PurchaseRequestStatus


class PurchaseRequest(SQLModel, table=True):
    """A request to buy something, against which supplier quotes are collected."""

    __tablename__ = "purchase_request"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str = Field(nullable=False, index=True)
    description: str | None = Field(default=None, nullable=True)
    # "Anotações gerais do pedido" — free-text scratchpad for the request as a
    # whole (deadlines, who to call, board remarks), distinct from `description`
    # (what is to be bought) and from each quote's own `notes`.
    general_notes: str | None = Field(default=None, nullable=True)
    status: PurchaseRequestStatus = Field(
        default=PurchaseRequestStatus.OPEN, nullable=False, index=True
    )
    requested_by_id: UUID = Field(foreign_key="user.id", nullable=False, index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), nullable=False, index=True
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), nullable=False
    )

    quotes: list["PurchaseQuote"] = Relationship(
        back_populates="purchase_request",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "PurchaseQuote.created_at",
        },
    )
    decisions: list["PurchaseQuoteDecision"] = Relationship(
        back_populates="purchase_request",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "PurchaseQuoteDecision.decided_at.desc()",
        },
    )


class PurchaseQuote(SQLModel, table=True):
    """One supplier quote for a purchase request."""

    __tablename__ = "purchase_quote"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    purchase_request_id: UUID = Field(
        foreign_key="purchase_request.id",
        nullable=False,
        index=True,
        ondelete="CASCADE",
    )
    supplier_name: str = Field(nullable=False, index=True)
    supplier_contact: str | None = Field(default=None, nullable=True)
    unit_price: float = Field(nullable=False)
    quantity: int = Field(nullable=False)
    notes: str | None = Field(default=None, nullable=True)
    # Caller-defined extra fields, stored as an ordered list of
    # {"label": str, "value": str} objects. Portable JSON column (NOT Postgres
    # JSONB/ARRAY): tests/conftest.py builds the schema with
    # SQLModel.metadata.create_all() against sqlite:// in memory, exactly as
    # documented on UserType.allowed_menus.
    extra_fields: list[dict[str, str]] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, server_default="[]"),
    )
    created_by_id: UUID = Field(foreign_key="user.id", nullable=False, index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), nullable=False
    )

    purchase_request: PurchaseRequest = Relationship(back_populates="quotes")


class PurchaseQuoteDecision(SQLModel, table=True):
    """An append-only record of a board member choosing one quote, with reasons."""

    __tablename__ = "purchase_quote_decision"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    purchase_request_id: UUID = Field(
        foreign_key="purchase_request.id",
        nullable=False,
        index=True,
        ondelete="CASCADE",
    )
    quote_id: UUID = Field(
        foreign_key="purchase_quote.id",
        nullable=False,
        index=True,
        ondelete="CASCADE",
    )
    justification: str = Field(nullable=False)
    decided_by_id: UUID = Field(foreign_key="user.id", nullable=False, index=True)
    decided_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), nullable=False, index=True
    )

    purchase_request: PurchaseRequest = Relationship(back_populates="decisions")
