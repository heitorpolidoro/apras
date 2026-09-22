"""Service layer for purchase requests, supplier quotes and decisions (APRAS-37).

Deliberately isolated: this module knows nothing about Financeiro, Patrimônio
& Estoque or Obras. Choosing a quote records a justification and nothing else.
"""

import io
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from PIL import Image
from sqlalchemy import func, or_
from sqlmodel import Session, select

from app.api.deps import has_permission
from app.core import clock
from app.core.exceptions import (
    PurchaseAccessForbiddenError,
    PurchaseQuoteFrozenError,
    PurchaseQuoteItemUnknownLineError,
    PurchaseQuoteNotFoundError,
    PurchaseRequestNotFoundError,
    PurchaseRequestNotOpenError,
    QuoteAttachmentInvalidFormatError,
    QuoteAttachmentTooLargeError,
)
from app.core.money import ZERO, quantize_money
from app.core.uploads import sanitise_upload_filename
from app.models.enums import PurchaseRequestStatus
from app.models.purchase import (
    PurchaseQuote,
    PurchaseQuoteDecision,
    PurchaseQuoteItem,
    PurchaseRequest,
    PurchaseRequestItem,
)
from app.models.user import User
from app.schemas.purchase import (
    PaginatedPurchaseRequestRead,
    PurchaseDecisionCreate,
    PurchaseDecisionRead,
    PurchaseQuoteCreate,
    PurchaseQuoteItemIn,
    PurchaseQuoteItemRead,
    PurchaseQuoteRead,
    PurchaseQuoteUpdate,
    PurchaseRequestCreate,
    PurchaseRequestDetailRead,
    PurchaseRequestItemIn,
    PurchaseRequestItemRead,
    PurchaseRequestRead,
    PurchaseRequestUpdate,
    PurchaseSummaryRead,
)
from app.services.media_service import MAX_FILE_SIZE
from app.services.storage_service import BaseStorageProvider, LocalStorageProvider

#: The public URL prefix :class:`LocalStorageProvider` mints, and the only
#: prefix a stored ``attachment_url`` is ever mapped back to a file we own.
#: Any other value is somebody else's file and is left alone (APRAS-63 D6).
LOCAL_UPLOAD_URL_PREFIX = "/static/uploads/"

#: The first bytes of every PDF. The declared MIME type is a claim the client
#: makes; this is the check (APRAS-63 D2).
_PDF_MAGIC = b"%PDF-"

#: Module level and bound once, exactly like ``tenant_service``: a test (or a
#: future non-local backend) substitutes this one name rather than threading a
#: provider through the router.
_storage_provider: BaseStorageProvider = LocalStorageProvider()


def _effective_quantity(item: PurchaseQuoteItem) -> int:
    """How many the line prices (APRAS-73 D8).

    Its own ``quantity`` for a supplier's extra line; the request line's for
    a linked one, which is the single source of truth for *how many*.
    """
    if item.quantity is not None:
        return item.quantity
    return item.request_item.quantity


def _effective_description(item: PurchaseQuoteItem) -> str:
    """What the line prices: its own text, or the request line's."""
    if item.request_item is not None:
        return item.request_item.description
    return item.description or ""


def _line_total(item: PurchaseQuoteItem) -> Decimal:
    """``quantize_money(unit_price * quantity)`` over the effective quantity."""
    return quantize_money(item.unit_price * _effective_quantity(item))


def _quote_total(quote: PurchaseQuote) -> Decimal:
    """Total price of a quote: the sum of its line totals (APRAS-73 D8).

    Seeded with :data:`~app.core.money.ZERO` so a quote with no line yields
    ``Decimal("0.00")`` and never ``int`` 0, and quantized once more on the
    way out. That last call is deliberately redundant over exact cents and is
    kept as a defence, mirroring ``PurchaseQuoteRead._compute_total``; it
    rounds nothing and is not dead code.
    """
    return quantize_money(sum((_line_total(item) for item in quote.items), ZERO))


def _quoted_item_count(quote: PurchaseQuote) -> int:
    """Request lines this quote priced -- **linked** items only (D5).

    A supplier's own extra line counts toward the total and never toward
    coverage, which is what makes ``2 of 3 plus one extra`` read as 2 and not
    as 3.
    """
    return sum(1 for item in quote.items if item.request_item_id is not None)


def _is_quote_complete(quote: PurchaseQuote, request_item_count: int) -> bool:
    """Does the quote price every line the request enumerates? (D5)

    Trivially ``True`` when the request enumerates nothing, which is what
    keeps ranking on pre-APRAS-73 data bit-for-bit what APRAS-63 produced.
    """
    return _quoted_item_count(quote) == request_item_count


class PurchaseService:
    """Business logic for the purchase-quotation module."""

    #: 5 MiB, **imported** from ``media_service`` rather than re-typed
    #: (APRAS-63 D2), and mirrored by
    #: ``QUOTE_ATTACHMENT_MAX_FILE_SIZE_BYTES`` in
    #: ``frontend/src/api/purchases.ts``, pinned from both sides.
    ATTACHMENT_MAX_FILE_SIZE = MAX_FILE_SIZE

    #: What a supplier actually sends. ``image/webp`` is out because no
    #: supplier sends one; ``image/svg+xml`` is out for the same
    #: active-content reason as APRAS-61 D2 -- an SVG served same-origin from
    #: ``/static/uploads/`` is a stored-XSS surface without a sanitiser.
    ATTACHMENT_ALLOWED_MIME_TYPES = frozenset(
        {"application/pdf", "image/png", "image/jpeg"}
    )

    #: Longest ``attachment_filename`` kept. Display text, not a path.
    ATTACHMENT_FILENAME_MAX_LENGTH = 128

    #: Used when the client sends no usable name at all.
    ATTACHMENT_FALLBACK_STEM = "documento"

    # ------------------------------------------------------------------ #
    # Guards
    # ------------------------------------------------------------------ #

    @staticmethod
    def _assert_can_view(current_user: User, session: Session, permission: str) -> None:
        if not has_permission(current_user, session, permission):
            raise PurchaseAccessForbiddenError("Acesso às cotações de compra negado.")

    @staticmethod
    def _assert_can_decide(
        current_user: User, session: Session, permission: str
    ) -> None:
        if not has_permission(current_user, session, permission):
            raise PurchaseAccessForbiddenError(
                "Apenas Administradores e Diretores podem escolher um orçamento."
            )

    @staticmethod
    def _assert_can_write_request(
        current_user: User, purchase_request: PurchaseRequest, session: Session
    ) -> None:
        """Decide-level short-circuit, then the MANAGER own-row narrowing.

        `purchases:decide` is `{A, D}` and `purchases:update` is `{A, D, M}`,
        so "holds update but not decide" is exactly "is a MANAGER" -- the
        same partition the two role comparisons drew, message for message.
        """
        if has_permission(current_user, session, "purchases:decide"):
            return
        if not has_permission(current_user, session, "purchases:update"):
            raise PurchaseAccessForbiddenError("Acesso às cotações de compra negado.")
        if purchase_request.requested_by_id != current_user.id:
            raise PurchaseAccessForbiddenError(
                "Gerentes só podem alterar os pedidos que criaram."
            )
        if purchase_request.status != PurchaseRequestStatus.OPEN:
            raise PurchaseAccessForbiddenError(
                "Gerentes só podem alterar pedidos ainda abertos."
            )

    @staticmethod
    def _assert_can_write_quote(
        current_user: User, quote: PurchaseQuote, session: Session
    ) -> None:
        """The same partition as `_assert_can_write_request`, for a quote."""
        if has_permission(current_user, session, "purchases:decide"):
            return
        if not has_permission(current_user, session, "purchases:quote_update"):
            raise PurchaseAccessForbiddenError("Acesso às cotações de compra negado.")
        if quote.created_by_id != current_user.id:
            raise PurchaseAccessForbiddenError(
                "Gerentes só podem alterar os orçamentos que registraram."
            )

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _get_request_or_404(session: Session, request_id: UUID) -> PurchaseRequest:
        purchase_request = session.get(PurchaseRequest, request_id)
        if not purchase_request:
            raise PurchaseRequestNotFoundError(request_id)
        return purchase_request

    @staticmethod
    def _get_quote_or_404(
        session: Session, request_id: UUID, quote_id: UUID
    ) -> PurchaseQuote:
        quote = session.exec(
            select(PurchaseQuote).where(
                PurchaseQuote.id == quote_id,
                PurchaseQuote.purchase_request_id == request_id,
            )
        ).first()
        if not quote:
            raise PurchaseQuoteNotFoundError(quote_id)
        return quote

    @staticmethod
    def _assert_quotes_unfrozen(purchase_request: PurchaseRequest) -> None:
        if purchase_request.status != PurchaseRequestStatus.OPEN:
            raise PurchaseQuoteFrozenError

    @staticmethod
    def _resolve_user_names(session: Session, user_ids: set[UUID]) -> dict[UUID, str]:
        if not user_ids:
            return {}
        rows = session.exec(select(User).where(User.id.in_(user_ids))).all()
        return {u.id: (u.full_name or u.email) for u in rows}

    @staticmethod
    def _current_decision(
        decisions: list[PurchaseQuoteDecision],
    ) -> PurchaseQuoteDecision | None:
        if not decisions:
            return None
        return max(decisions, key=lambda d: d.decided_at)

    @staticmethod
    def _lowest_complete_total(
        quotes: list[PurchaseQuote], request_item_count: int
    ) -> Decimal | None:
        """The baseline of the ranking, over **complete** quotes only (D10).

        A deliberate, operator-ruled change to the APRAS-63 contract, where
        this was a pure minimum over every total: an incomplete quote is
        cheaper *because it delivers less*, so calling it the lowest price
        compares two different things on the very screen built for choosing.
        ``None`` when no quote covers the whole enumeration -- then no quote
        is badged at all.
        """
        totals = [
            _quote_total(q) for q in quotes if _is_quote_complete(q, request_item_count)
        ]
        return min(totals) if totals else None

    @staticmethod
    def _build_request_read(
        purchase_request: PurchaseRequest,
        quotes: list[PurchaseQuote],
        current: PurchaseQuoteDecision | None,
        user_names: dict[UUID, str],
    ) -> PurchaseRequestRead:
        items = list(purchase_request.items)
        selected_quote = None
        if current is not None:
            selected_quote = next((q for q in quotes if q.id == current.quote_id), None)
        return PurchaseRequestRead(
            id=purchase_request.id,
            title=purchase_request.title,
            description=purchase_request.description,
            general_notes=purchase_request.general_notes,
            status=purchase_request.status,
            requested_by_id=purchase_request.requested_by_id,
            requested_by_name=user_names.get(purchase_request.requested_by_id),
            items=[PurchaseRequestItemRead.model_validate(i) for i in items],
            quote_count=len(quotes),
            lowest_quote_total=PurchaseService._lowest_complete_total(
                quotes, len(items)
            ),
            selected_quote_id=current.quote_id if current else None,
            selected_quote_total=(
                _quote_total(selected_quote) if selected_quote else None
            ),
            decision_justification=current.justification if current else None,
            decided_at=current.decided_at if current else None,
            created_at=purchase_request.created_at,
            updated_at=purchase_request.updated_at,
        )

    @staticmethod
    def _build_quote_item_reads(quote: PurchaseQuote) -> list[PurchaseQuoteItemRead]:
        """The quote's lines, each echoing its effective text and quantity.

        Storage stays normalised -- a linked line stores neither -- and the
        payload still renders the grid on its own (D3).
        """
        return [
            PurchaseQuoteItemRead(
                id=item.id,
                request_item_id=item.request_item_id,
                model=item.model,
                unit_price=item.unit_price,
                description=_effective_description(item),
                quantity=_effective_quantity(item),
                position=item.position,
            )
            for item in quote.items
        ]

    @staticmethod
    def _build_quote_read(
        quote: PurchaseQuote,
        user_names: dict[UUID, str],
        lowest_total: Decimal | None = None,
        selected_quote_id: UUID | None = None,
        request_item_count: int = 0,
    ) -> PurchaseQuoteRead:
        total = _quote_total(quote)
        is_complete = _is_quote_complete(quote, request_item_count)
        return PurchaseQuoteRead(
            id=quote.id,
            purchase_request_id=quote.purchase_request_id,
            supplier_name=quote.supplier_name,
            supplier_contact=quote.supplier_contact,
            items=PurchaseService._build_quote_item_reads(quote),
            is_complete=is_complete,
            notes=quote.notes,
            extra_fields=quote.extra_fields or [],
            attachment_url=quote.attachment_url,
            attachment_filename=quote.attachment_filename,
            created_by_id=quote.created_by_id,
            created_by_name=user_names.get(quote.created_by_id),
            is_selected=selected_quote_id is not None and selected_quote_id == quote.id,
            # D10: `lowest_total` is already a complete quote's total, and the
            # `is_complete` conjunct is what stops an incomplete quote that
            # happens to *tie* with it from wearing the badge anyway.
            is_lowest_price=(
                lowest_total is not None and is_complete and total == lowest_total
            ),
            created_at=quote.created_at,
            updated_at=quote.updated_at,
        )

    # ------------------------------------------------------------------ #
    # The lines, on both sides of the grid (APRAS-73 D7)
    # ------------------------------------------------------------------ #

    @staticmethod
    def _replace_request_items(
        session: Session,
        purchase_request: PurchaseRequest,
        items_in: list[PurchaseRequestItemIn],
    ) -> None:
        """Rewrite the enumeration wholesale, by ``id`` (D7).

        A submitted line carrying an existing ``id`` keeps it -- and keeps
        every quote cell attached to it; a line without one is created; a
        line the payload omits is **deleted**, taking the cells that priced
        it with it. An ``id`` this request does not own is treated as a new
        line: it names no row that could be kept, and honouring it would let
        one request address another's.
        """
        existing = {item.id: item for item in purchase_request.items}
        result: list[PurchaseRequestItem] = []
        survivors: set[UUID] = set()

        for position, item_in in enumerate(items_in):
            row = existing.get(item_in.id) if item_in.id is not None else None
            if row is None:
                row = PurchaseRequestItem(
                    description=item_in.description,
                    quantity=item_in.quantity,
                    position=position,
                )
            else:
                row.description = item_in.description
                row.quantity = item_in.quantity
                row.position = position
                survivors.add(row.id)
            result.append(row)

        removed_ids = [row_id for row_id in existing if row_id not in survivors]
        if removed_ids:
            # The cells first, and flushed before the parents go:
            # `purchase_quote_item.request_item_id` is nullable, so deleting
            # the request line alone would have the ORM null the column out
            # and silently turn a linked cell into a malformed extra line.
            for cell in session.exec(
                select(PurchaseQuoteItem).where(
                    PurchaseQuoteItem.request_item_id.in_(removed_ids)
                )
            ).all():
                session.delete(cell)
            session.flush()

        # `cascade="all, delete-orphan"` turns the assignment into the delete
        # of every line the payload omitted.
        purchase_request.items = result
        session.flush()

    @staticmethod
    def _replace_quote_items(
        session: Session,
        purchase_request: PurchaseRequest,
        quote: PurchaseQuote,
        items_in: list[PurchaseQuoteItemIn],
    ) -> None:
        """Rewrite a quote's priced lines wholesale, keyed by the request line.

        A linked line the payload still carries keeps its row, so its id is
        stable; a supplier's own extra line is re-created every time, which
        means an extra line's ``id`` churns on every quote edit even when
        nothing about it changed. Known and accepted (D7): nothing in this
        task addresses an extra line by id.
        """
        request_items = {item.id: item for item in purchase_request.items}
        for item_in in items_in:
            if (
                item_in.request_item_id is not None
                and item_in.request_item_id not in request_items
            ):
                raise PurchaseQuoteItemUnknownLineError

        by_link = {
            item.request_item_id: item
            for item in quote.items
            if item.request_item_id is not None
        }
        result: list[PurchaseQuoteItem] = []

        for position, item_in in enumerate(items_in):
            row = (
                by_link.get(item_in.request_item_id)
                if item_in.request_item_id is not None
                else None
            )
            if row is None:
                row = PurchaseQuoteItem(
                    request_item_id=item_in.request_item_id,
                    request_item=request_items.get(item_in.request_item_id),
                    model=item_in.model,
                    unit_price=quantize_money(item_in.unit_price),
                    description=item_in.description,
                    quantity=item_in.quantity,
                    position=position,
                )
            else:
                row.model = item_in.model
                row.unit_price = quantize_money(item_in.unit_price)
                row.position = position
            result.append(row)

        # `cascade="all, delete-orphan"`: what the payload dropped is deleted,
        # which is what makes an extra line's id churn on every edit (D7).
        quote.items = result
        session.flush()

    # ------------------------------------------------------------------ #
    # Requests
    # ------------------------------------------------------------------ #

    @staticmethod
    def create_request(
        session: Session, current_user: User, request_in: PurchaseRequestCreate
    ) -> PurchaseRequestRead:
        """Create a new purchase request in the OPEN status."""
        if not has_permission(current_user, session, "purchases:create"):
            raise PurchaseAccessForbiddenError(
                "Apenas Administradores, Diretores e Gerentes podem abrir pedidos."
            )

        now = clock.db_now()
        data = request_in.model_dump()
        # The lines are rows of their own, never columns of the request.
        data.pop("items", None)
        purchase_request = PurchaseRequest(
            **data,
            status=PurchaseRequestStatus.OPEN,
            requested_by_id=current_user.id,
            created_at=now,
            updated_at=now,
        )
        session.add(purchase_request)
        session.flush()
        if request_in.items:
            PurchaseService._replace_request_items(
                session, purchase_request, request_in.items
            )
        session.commit()
        session.refresh(purchase_request)

        return PurchaseService._build_request_read(
            purchase_request,
            [],
            None,
            {current_user.id: current_user.full_name or current_user.email},
        )

    @staticmethod
    def list_requests(
        session: Session,
        current_user: User,
        status: PurchaseRequestStatus | None = None,
        requested_by_id: UUID | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> PaginatedPurchaseRequestRead:
        """List purchase requests with filters, search and pagination."""
        PurchaseService._assert_can_view(current_user, session, "purchases:read")

        statement = select(PurchaseRequest)
        if status:
            statement = statement.where(PurchaseRequest.status == status)
        if requested_by_id:
            statement = statement.where(
                PurchaseRequest.requested_by_id == requested_by_id
            )
        if search:
            pattern = f"%{search}%"
            statement = statement.where(
                or_(
                    PurchaseRequest.title.ilike(pattern),
                    PurchaseRequest.description.ilike(pattern),
                )
            )

        total = session.exec(
            select(func.count()).select_from(statement.subquery())
        ).one()

        statement = (
            statement.order_by(PurchaseRequest.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        requests = session.exec(statement).all()
        request_ids = [r.id for r in requests]

        quotes_by_request: dict[UUID, list[PurchaseQuote]] = {
            rid: [] for rid in request_ids
        }
        decisions_by_request: dict[UUID, list[PurchaseQuoteDecision]] = {
            rid: [] for rid in request_ids
        }
        if request_ids:
            for quote in session.exec(
                select(PurchaseQuote).where(
                    PurchaseQuote.purchase_request_id.in_(request_ids)
                )
            ).all():
                quotes_by_request[quote.purchase_request_id].append(quote)
            for decision in session.exec(
                select(PurchaseQuoteDecision).where(
                    PurchaseQuoteDecision.purchase_request_id.in_(request_ids)
                )
            ).all():
                decisions_by_request[decision.purchase_request_id].append(decision)

        user_names = PurchaseService._resolve_user_names(
            session, {r.requested_by_id for r in requests}
        )

        items = [
            PurchaseService._build_request_read(
                r,
                quotes_by_request[r.id],
                PurchaseService._current_decision(decisions_by_request[r.id]),
                user_names,
            )
            for r in requests
        ]
        return PaginatedPurchaseRequestRead(
            items=items, total=total, skip=skip, limit=limit
        )

    @staticmethod
    def get_summary(session: Session, current_user: User) -> PurchaseSummaryRead:
        """Compute aggregate metrics for the purchase dashboard."""
        PurchaseService._assert_can_view(
            current_user, session, "purchases:summary_read"
        )

        requests = session.exec(select(PurchaseRequest)).all()
        counts = dict.fromkeys(PurchaseRequestStatus, 0)
        for purchase_request in requests:
            counts[purchase_request.status] += 1

        # Quotes and decisions inherit their tenant from `PurchaseRequest`,
        # so they are constrained by the ids of the already-filtered
        # `requests` above rather than read wholesale (APRAS-42 §6.2).
        request_ids = [r.id for r in requests]
        quotes = {
            q.id: q
            for q in session.exec(
                select(PurchaseQuote).where(
                    PurchaseQuote.purchase_request_id.in_(request_ids)
                )
            ).all()
        }
        decisions_by_request: dict[UUID, list[PurchaseQuoteDecision]] = {}
        for decision in session.exec(
            select(PurchaseQuoteDecision).where(
                PurchaseQuoteDecision.purchase_request_id.in_(request_ids)
            )
        ).all():
            decisions_by_request.setdefault(decision.purchase_request_id, []).append(
                decision
            )

        total_selected_value = ZERO
        for purchase_request in requests:
            if purchase_request.status != PurchaseRequestStatus.DECIDED:
                continue
            current = PurchaseService._current_decision(
                decisions_by_request.get(purchase_request.id, [])
            )
            if current and current.quote_id in quotes:
                total_selected_value += _quote_total(quotes[current.quote_id])

        return PurchaseSummaryRead(
            open_count=counts[PurchaseRequestStatus.OPEN],
            decided_count=counts[PurchaseRequestStatus.DECIDED],
            cancelled_count=counts[PurchaseRequestStatus.CANCELLED],
            total_selected_value=quantize_money(total_selected_value),
        )

    @staticmethod
    def get_request(
        session: Session, current_user: User, request_id: UUID
    ) -> PurchaseRequestDetailRead:
        """Return a purchase request with its quotes and decision history."""
        PurchaseService._assert_can_view(current_user, session, "purchases:read")
        purchase_request = PurchaseService._get_request_or_404(session, request_id)

        quotes = list(purchase_request.quotes)
        decisions = sorted(
            purchase_request.decisions, key=lambda d: d.decided_at, reverse=True
        )
        current = decisions[0] if decisions else None

        user_ids = {purchase_request.requested_by_id}
        user_ids.update(q.created_by_id for q in quotes)
        user_ids.update(d.decided_by_id for d in decisions)
        user_names = PurchaseService._resolve_user_names(session, user_ids)

        # Computed once per request and handed to both the ranking and the
        # schema's `is_complete`, so the two cannot disagree (D10).
        request_item_count = len(purchase_request.items)
        lowest_total = PurchaseService._lowest_complete_total(
            quotes, request_item_count
        )
        quotes_sorted = sorted(quotes, key=lambda q: (_quote_total(q), q.created_at))
        quote_reads = [
            PurchaseService._build_quote_read(
                q,
                user_names,
                lowest_total=lowest_total,
                selected_quote_id=current.quote_id if current else None,
                request_item_count=request_item_count,
            )
            for q in quotes_sorted
        ]

        quotes_by_id = {q.id: q for q in quotes}
        decision_reads = [
            PurchaseDecisionRead(
                id=d.id,
                quote_id=d.quote_id,
                quote_supplier_name=(
                    quotes_by_id[d.quote_id].supplier_name
                    if d.quote_id in quotes_by_id
                    else None
                ),
                quote_total_price=(
                    _quote_total(quotes_by_id[d.quote_id])
                    if d.quote_id in quotes_by_id
                    else None
                ),
                justification=d.justification,
                decided_by_id=d.decided_by_id,
                decided_by_name=user_names.get(d.decided_by_id),
                decided_at=d.decided_at,
                is_current=current is not None and d.id == current.id,
            )
            for d in decisions
        ]

        base = PurchaseService._build_request_read(
            purchase_request, quotes, current, user_names
        )
        return PurchaseRequestDetailRead(
            **base.model_dump(),
            quotes=quote_reads,
            decisions=decision_reads,
            current_decision=decision_reads[0] if decision_reads else None,
        )

    @staticmethod
    def update_request(
        session: Session,
        current_user: User,
        request_id: UUID,
        request_in: PurchaseRequestUpdate,
    ) -> PurchaseRequestRead:
        """Update the free-text fields, and optionally the lines, of a request."""
        PurchaseService._assert_can_view(current_user, session, "purchases:update")
        purchase_request = PurchaseService._get_request_or_404(session, request_id)
        PurchaseService._assert_can_write_request(
            current_user, purchase_request, session
        )
        # D7: a decided request's grid is immutable, because rewriting it
        # would rewrite the quotes that were compared to reach the decision.
        # A free-text-only update keeps its current behaviour.
        if request_in.items is not None:
            PurchaseService._assert_quotes_unfrozen(purchase_request)

        update_data = request_in.model_dump(exclude_unset=True)
        update_data.pop("items", None)
        for key, value in update_data.items():
            setattr(purchase_request, key, value)
        if request_in.items is not None:
            PurchaseService._replace_request_items(
                session, purchase_request, request_in.items
            )
        purchase_request.updated_at = clock.db_now()
        session.add(purchase_request)
        session.commit()
        session.refresh(purchase_request)

        return PurchaseService._reload_request_read(session, purchase_request)

    @staticmethod
    def _reload_request_read(
        session: Session, purchase_request: PurchaseRequest
    ) -> PurchaseRequestRead:
        quotes = list(purchase_request.quotes)
        current = PurchaseService._current_decision(list(purchase_request.decisions))
        user_names = PurchaseService._resolve_user_names(
            session, {purchase_request.requested_by_id}
        )
        return PurchaseService._build_request_read(
            purchase_request, quotes, current, user_names
        )

    @staticmethod
    def delete_request(session: Session, current_user: User, request_id: UUID) -> None:
        """Delete a purchase request and cascade its quotes and decisions."""
        PurchaseService._assert_can_view(current_user, session, "purchases:delete")
        purchase_request = PurchaseService._get_request_or_404(session, request_id)
        PurchaseService._assert_can_write_request(
            current_user, purchase_request, session
        )

        # D6: the cascade takes the rows, so this has to take the bytes.
        for quote in list(purchase_request.quotes):
            PurchaseService._delete_stored_attachment(quote.attachment_url)
        session.delete(purchase_request)
        session.commit()

    @staticmethod
    def cancel_request(
        session: Session, current_user: User, request_id: UUID
    ) -> PurchaseRequestRead:
        """Cancel an open purchase request."""
        PurchaseService._assert_can_decide(current_user, session, "purchases:cancel")
        purchase_request = PurchaseService._get_request_or_404(session, request_id)

        if purchase_request.status != PurchaseRequestStatus.OPEN:
            raise PurchaseRequestNotOpenError(
                "Apenas pedidos abertos podem ser cancelados."
            )

        purchase_request.status = PurchaseRequestStatus.CANCELLED
        purchase_request.updated_at = clock.db_now()
        session.add(purchase_request)
        session.commit()
        session.refresh(purchase_request)

        return PurchaseService._reload_request_read(session, purchase_request)

    # ------------------------------------------------------------------ #
    # Quotes
    # ------------------------------------------------------------------ #

    @staticmethod
    def add_quote(
        session: Session,
        current_user: User,
        request_id: UUID,
        quote_in: PurchaseQuoteCreate,
    ) -> PurchaseQuoteRead:
        """Add a supplier quote to an open purchase request."""
        if not has_permission(current_user, session, "purchases:quote_create"):
            raise PurchaseAccessForbiddenError("Acesso às cotações de compra negado.")
        purchase_request = PurchaseService._get_request_or_404(session, request_id)
        PurchaseService._assert_quotes_unfrozen(purchase_request)

        now = clock.db_now()
        data = quote_in.model_dump()
        extra_fields = data.pop("extra_fields", [])
        # The priced lines are rows of their own (D2), so they never reach
        # the quote's constructor.
        data.pop("items", None)
        quote = PurchaseQuote(
            **data,
            purchase_request_id=purchase_request.id,
            extra_fields=extra_fields,
            created_by_id=current_user.id,
            created_at=now,
            updated_at=now,
        )
        session.add(quote)
        session.flush()
        PurchaseService._replace_quote_items(
            session, purchase_request, quote, quote_in.items
        )
        session.commit()
        session.refresh(quote)

        return PurchaseService._build_quote_read(
            quote,
            {current_user.id: current_user.full_name or current_user.email},
            request_item_count=len(purchase_request.items),
        )

    @staticmethod
    def update_quote(
        session: Session,
        current_user: User,
        request_id: UUID,
        quote_id: UUID,
        quote_in: PurchaseQuoteUpdate,
    ) -> PurchaseQuoteRead:
        """Update a supplier quote on an open purchase request."""
        PurchaseService._assert_can_view(
            current_user, session, "purchases:quote_update"
        )
        purchase_request = PurchaseService._get_request_or_404(session, request_id)
        quote = PurchaseService._get_quote_or_404(session, request_id, quote_id)
        PurchaseService._assert_can_write_quote(current_user, quote, session)
        PurchaseService._assert_quotes_unfrozen(purchase_request)

        update_data = quote_in.model_dump(exclude_unset=True)
        if "extra_fields" in update_data and update_data["extra_fields"] is None:
            update_data.pop("extra_fields")
        update_data.pop("items", None)
        for key, value in update_data.items():
            setattr(quote, key, value)
        if quote_in.items is not None:
            PurchaseService._replace_quote_items(
                session, purchase_request, quote, quote_in.items
            )
        quote.updated_at = clock.db_now()
        session.add(quote)
        session.commit()
        session.refresh(quote)

        user_names = PurchaseService._resolve_user_names(session, {quote.created_by_id})
        return PurchaseService._build_quote_read(
            quote, user_names, request_item_count=len(purchase_request.items)
        )

    @staticmethod
    def delete_quote(
        session: Session, current_user: User, request_id: UUID, quote_id: UUID
    ) -> None:
        """Delete a supplier quote from an open purchase request."""
        PurchaseService._assert_can_view(
            current_user, session, "purchases:quote_delete"
        )
        purchase_request = PurchaseService._get_request_or_404(session, request_id)
        quote = PurchaseService._get_quote_or_404(session, request_id, quote_id)
        PurchaseService._assert_can_write_quote(current_user, quote, session)
        PurchaseService._assert_quotes_unfrozen(purchase_request)

        # D6: the bytes go with the row. Best-effort and before the delete,
        # so a provider failure never leaves a row pointing at nothing.
        PurchaseService._delete_stored_attachment(quote.attachment_url)
        session.delete(quote)
        session.commit()

    # ------------------------------------------------------------------ #
    # The supplier document (APRAS-63)
    # ------------------------------------------------------------------ #

    @classmethod
    def _validate_attachment(cls, file_bytes: bytes, content_type: str) -> None:
        """Size, then declared MIME, then a content sniff -- in that order.

        A refusal writes **no** file and **no** column (D2), which is why
        every check runs before ``save_file`` is reached rather than beside
        it.
        """
        if len(file_bytes) > cls.ATTACHMENT_MAX_FILE_SIZE:
            raise QuoteAttachmentTooLargeError
        if content_type not in cls.ATTACHMENT_ALLOWED_MIME_TYPES:
            raise QuoteAttachmentInvalidFormatError
        if content_type == "application/pdf":
            if not file_bytes.startswith(_PDF_MAGIC):
                raise QuoteAttachmentInvalidFormatError
            return
        try:
            Image.open(io.BytesIO(file_bytes)).verify()
        except Exception as exc:
            raise QuoteAttachmentInvalidFormatError from exc

    @staticmethod
    def _delete_stored_attachment(url: str | None) -> None:
        """Best-effort removal of the file a stored ``attachment_url`` names.

        Only a ``/static/uploads/`` value is mapped back to a path, and it is
        mapped **relative to the provider's own** ``base_dir`` rather than by
        stripping the leading slash: identical for the production provider
        and honest for any other one. ``delete_file`` already swallows, so a
        failure here never fails the request that replaced the document.
        """
        if url is None or not url.startswith(LOCAL_UPLOAD_URL_PREFIX):
            return
        base = getattr(_storage_provider, "base_dir", None)
        if base is None:
            return
        relative = url[len(LOCAL_UPLOAD_URL_PREFIX) :]
        _storage_provider.delete_file(str(Path(base) / relative))

    @classmethod
    def set_quote_attachment(
        cls,
        session: Session,
        current_user: User,
        request_id: UUID,
        quote_id: UUID,
        *,
        file_bytes: bytes,
        filename: str,
        content_type: str,
    ) -> PurchaseQuoteRead:
        """Store one supplier document on one quote of one request.

        The same guard ladder as ``update_quote`` -- uploading a supplier's
        PDF *is* editing that quote (D4) -- so no new permission string
        exists and a Manager may only touch a quote they may already edit.
        """
        cls._assert_can_view(current_user, session, "purchases:quote_update")
        purchase_request = cls._get_request_or_404(session, request_id)
        quote = cls._get_quote_or_404(session, request_id, quote_id)
        cls._assert_can_write_quote(current_user, quote, session)
        cls._assert_quotes_unfrozen(purchase_request)

        cls._validate_attachment(file_bytes, content_type)

        # Display metadata only -- `save_file` derives the on-disk suffix from
        # `content_type` itself (APRAS-65) -- but `attachment_filename` is
        # persisted and rendered, so it is still sanitised, by the one shared
        # implementation rather than a copy living here.
        safe_name = sanitise_upload_filename(
            filename,
            content_type,
            max_length=cls.ATTACHMENT_FILENAME_MAX_LENGTH,
            fallback_stem=cls.ATTACHMENT_FALLBACK_STEM,
        )

        previous = quote.attachment_url
        _, url = _storage_provider.save_file(file_bytes, safe_name, content_type)
        quote.attachment_url = url
        quote.attachment_filename = safe_name
        quote.updated_at = clock.db_now()
        session.add(quote)
        session.commit()
        session.refresh(quote)

        cls._delete_stored_attachment(previous)
        user_names = cls._resolve_user_names(session, {quote.created_by_id})
        return cls._build_quote_read(
            quote, user_names, request_item_count=len(purchase_request.items)
        )

    @classmethod
    def clear_quote_attachment(
        cls,
        session: Session,
        current_user: User,
        request_id: UUID,
        quote_id: UUID,
    ) -> PurchaseQuoteRead:
        """Drop the document. Idempotent: an already-null pair is still 200."""
        cls._assert_can_view(current_user, session, "purchases:quote_update")
        purchase_request = cls._get_request_or_404(session, request_id)
        quote = cls._get_quote_or_404(session, request_id, quote_id)
        cls._assert_can_write_quote(current_user, quote, session)
        cls._assert_quotes_unfrozen(purchase_request)

        user_names = cls._resolve_user_names(session, {quote.created_by_id})
        request_item_count = len(purchase_request.items)
        previous = quote.attachment_url
        if previous is None and quote.attachment_filename is None:
            return cls._build_quote_read(
                quote, user_names, request_item_count=request_item_count
            )

        quote.attachment_url = None
        quote.attachment_filename = None
        quote.updated_at = clock.db_now()
        session.add(quote)
        session.commit()
        session.refresh(quote)

        cls._delete_stored_attachment(previous)
        return cls._build_quote_read(
            quote, user_names, request_item_count=request_item_count
        )

    # ------------------------------------------------------------------ #
    # Decision
    # ------------------------------------------------------------------ #

    @staticmethod
    def select_quote(
        session: Session,
        current_user: User,
        request_id: UUID,
        decision_in: PurchaseDecisionCreate,
    ) -> PurchaseDecisionRead:
        """Record the justified choice of one quote for a purchase request."""
        PurchaseService._assert_can_decide(current_user, session, "purchases:decide")
        purchase_request = PurchaseService._get_request_or_404(session, request_id)

        if purchase_request.status == PurchaseRequestStatus.CANCELLED:
            raise PurchaseRequestNotOpenError(
                "Não é possível decidir sobre um pedido cancelado."
            )

        quote = PurchaseService._get_quote_or_404(
            session, request_id, decision_in.quote_id
        )

        now = clock.db_now()
        decision = PurchaseQuoteDecision(
            purchase_request_id=purchase_request.id,
            quote_id=quote.id,
            justification=decision_in.justification.strip(),
            decided_by_id=current_user.id,
            decided_at=now,
        )
        session.add(decision)
        purchase_request.status = PurchaseRequestStatus.DECIDED
        purchase_request.updated_at = now
        session.add(purchase_request)
        session.commit()
        session.refresh(decision)

        return PurchaseDecisionRead(
            id=decision.id,
            quote_id=decision.quote_id,
            quote_supplier_name=quote.supplier_name,
            quote_total_price=_quote_total(quote),
            justification=decision.justification,
            decided_by_id=decision.decided_by_id,
            decided_by_name=current_user.full_name or current_user.email,
            decided_at=decision.decided_at,
            is_current=True,
        )
