"""Models for purchase requests, supplier quotes and the justified choice (APRAS-37)."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

from app.core import clock
from app.core.money import Money
from app.models.enums import PurchaseRequestStatus
from app.models.tenant import tenant_id_field


class PurchaseRequest(SQLModel, table=True):
    """A request to buy something, against which supplier quotes are collected."""

    __tablename__ = "purchase_request"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    # Tenant boundary (APRAS-41). Defaults to DEFAULT_TENANT_ID so ORM
    # inserts that omit it keep working; APRAS-42 replaces this with a
    # request-scoped acting tenant.
    tenant_id: UUID = tenant_id_field()
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
        default_factory=clock.db_now, nullable=False, index=True
    )
    updated_at: datetime = Field(default_factory=clock.db_now, nullable=False)

    quotes: list["PurchaseQuote"] = Relationship(
        back_populates="purchase_request",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "PurchaseQuote.created_at",
        },
    )
    items: list["PurchaseRequestItem"] = Relationship(
        back_populates="purchase_request",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "PurchaseRequestItem.position, PurchaseRequestItem.id",
        },
    )
    decisions: list["PurchaseQuoteDecision"] = Relationship(
        back_populates="purchase_request",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "PurchaseQuoteDecision.decided_at.desc()",
        },
    )


class PurchaseRequestItem(SQLModel, table=True):
    """One enumerated line of a purchase request (APRAS-73 D1).

    The request says *what* and *how many*; each quote prices it. No
    timestamps and no ``tenant_id``: the rows are rewritten wholesale with
    their request, ``PurchaseRequest.updated_at`` is the audit point, and the
    tenant is inherited through the NOT NULL FK exactly as ``purchase_quote``
    inherits it.
    """

    __tablename__ = "purchase_request_item"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    purchase_request_id: UUID = Field(
        foreign_key="purchase_request.id",
        nullable=False,
        index=True,
        ondelete="CASCADE",
    )
    description: str = Field(nullable=False)
    quantity: int = Field(nullable=False)
    #: 0-based and assigned by the service from the submitted index, never
    #: trusted from the client. Deliberately **not** unique per request: the
    #: wholesale rewrite of D7 would fight a unique constraint.
    position: int = Field(nullable=False)

    purchase_request: PurchaseRequest = Relationship(back_populates="items")


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
    # APRAS-73 D4: `unit_price` and `quantity` left this table. A quote is a
    # list of priced lines and its total is derived from them; two sources of
    # truth for one total is the defect that task exists to delete.
    notes: str | None = Field(default=None, nullable=True)
    # Caller-defined extra fields, stored as an ordered list of
    # {"label": str, "value": str} objects. Portable JSON column (NOT Postgres
    # JSONB/ARRAY): tests/conftest.py builds the schema with
    # SQLModel.metadata.create_all() against sqlite:// in memory, exactly as
    # documented on Role.permissions.
    extra_fields: list[dict[str, str]] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, server_default="[]"),
    )
    # The supplier's own document (APRAS-63 D1). Two nullable columns and no
    # `MediaAsset` row: a document is a property of the quote, exactly as
    # APRAS-61 treated the tenant logo. `attachment_url` is the public
    # `/static/uploads/...` URL `LocalStorageProvider.save_file` mints, and
    # the on-disk path is derived from it -- only when it carries that
    # prefix -- rather than stored a second time.
    attachment_url: str | None = Field(default=None, nullable=True)
    #: The original file name, shown as the link text so the reader sees
    #: `orcamento-acme.pdf` rather than a uuid.
    attachment_filename: str | None = Field(default=None, nullable=True)
    created_by_id: UUID = Field(foreign_key="user.id", nullable=False, index=True)
    created_at: datetime = Field(default_factory=clock.db_now, nullable=False)
    updated_at: datetime = Field(default_factory=clock.db_now, nullable=False)

    purchase_request: PurchaseRequest = Relationship(back_populates="quotes")
    items: list["PurchaseQuoteItem"] = Relationship(
        back_populates="quote",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "PurchaseQuoteItem.position, PurchaseQuoteItem.id",
        },
    )


class PurchaseQuoteItem(SQLModel, table=True):
    """One priced line of a supplier quote (APRAS-73 D2).

    Either it answers a request line -- ``request_item_id`` set, and
    ``description``/``quantity`` read through that line, which is what makes
    the comparison grid's rows align -- or it is the supplier's own extra
    line, with ``request_item_id IS NULL`` and both fields of its own (D3).
    """

    __tablename__ = "purchase_quote_item"
    __table_args__ = (
        UniqueConstraint(
            "quote_id",
            "request_item_id",
            name="uq_purchase_quote_item_quote_request_item",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    quote_id: UUID = Field(
        foreign_key="purchase_quote.id",
        nullable=False,
        index=True,
        ondelete="CASCADE",
    )
    #: Nullable on purpose: PostgreSQL does not collide ``NULL``s in a unique
    #: constraint, so one quote may carry several extra lines while still
    #: pricing each request line at most once.
    request_item_id: UUID | None = Field(
        default=None,
        foreign_key="purchase_request_item.id",
        nullable=True,
        index=True,
        ondelete="CASCADE",
    )
    #: The offered model, optional: most lines have none (operator, 2026-09-22).
    model: str | None = Field(default=None, nullable=True)
    unit_price: Money = Field(nullable=False)
    #: Set only on an extra line; ``NULL`` on a linked one, whose text lives
    #: on the request line it points at.
    description: str | None = Field(default=None, nullable=True)
    quantity: int | None = Field(default=None, nullable=True)
    position: int = Field(nullable=False)

    quote: PurchaseQuote = Relationship(back_populates="items")
    #: One-way and eagerly joined: the effective description and quantity of
    #: a linked line are read through it on every total and every read, and a
    #: lazy load would be one query per line. Deliberately **no**
    #: ``back_populates``: a second ``delete-orphan`` collection over the same
    #: row would make its lifetime depend on two parents. The request line's
    #: children are deleted explicitly by the service and by the FK's
    #: ``ON DELETE CASCADE``.
    request_item: PurchaseRequestItem | None = Relationship(
        sa_relationship_kwargs={"lazy": "joined"},
    )


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
        default_factory=clock.db_now, nullable=False, index=True
    )

    purchase_request: PurchaseRequest = Relationship(back_populates="decisions")
