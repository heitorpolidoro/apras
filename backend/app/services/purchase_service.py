"""Service layer for purchase requests, supplier quotes and decisions (APRAS-37).

Deliberately isolated: this module knows nothing about Financeiro, Patrimônio
& Estoque or Obras. Choosing a quote records a justification and nothing else.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, or_
from sqlmodel import Session, select

from app.api.deps import has_permission
from app.core.exceptions import (
    PurchaseAccessForbiddenError,
    PurchaseQuoteFrozenError,
    PurchaseQuoteNotFoundError,
    PurchaseRequestNotFoundError,
    PurchaseRequestNotOpenError,
)
from app.models.enums import PurchaseRequestStatus
from app.models.purchase import PurchaseQuote, PurchaseQuoteDecision, PurchaseRequest
from app.models.user import User
from app.schemas.purchase import (
    PaginatedPurchaseRequestRead,
    PurchaseDecisionCreate,
    PurchaseDecisionRead,
    PurchaseQuoteCreate,
    PurchaseQuoteRead,
    PurchaseQuoteUpdate,
    PurchaseRequestCreate,
    PurchaseRequestDetailRead,
    PurchaseRequestRead,
    PurchaseRequestUpdate,
    PurchaseSummaryRead,
)


def _quote_total(quote: PurchaseQuote) -> float:
    """Total price of a quote (unit price times quantity, rounded to cents)."""
    return round(quote.unit_price * quote.quantity, 2)


class PurchaseService:
    """Business logic for the purchase-quotation module."""

    # ------------------------------------------------------------------ #
    # Guards
    # ------------------------------------------------------------------ #

    @staticmethod
    def _assert_can_view(current_user: User, session: Session, permission: str) -> None:
        if not has_permission(current_user, session, permission):
            raise PurchaseAccessForbiddenError(
                "Acesso às cotações de compra negado."
            )

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
            raise PurchaseAccessForbiddenError(
                "Acesso às cotações de compra negado."
            )
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
            raise PurchaseAccessForbiddenError(
                "Acesso às cotações de compra negado."
            )
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
    def _resolve_user_names(
        session: Session, user_ids: set[UUID]
    ) -> dict[UUID, str]:
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
    def _build_request_read(
        purchase_request: PurchaseRequest,
        quotes: list[PurchaseQuote],
        current: PurchaseQuoteDecision | None,
        user_names: dict[UUID, str],
    ) -> PurchaseRequestRead:
        totals = [_quote_total(q) for q in quotes]
        selected_quote = None
        if current is not None:
            selected_quote = next(
                (q for q in quotes if q.id == current.quote_id), None
            )
        return PurchaseRequestRead(
            id=purchase_request.id,
            title=purchase_request.title,
            description=purchase_request.description,
            general_notes=purchase_request.general_notes,
            status=purchase_request.status,
            requested_by_id=purchase_request.requested_by_id,
            requested_by_name=user_names.get(purchase_request.requested_by_id),
            quote_count=len(quotes),
            lowest_quote_total=min(totals) if totals else None,
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
    def _build_quote_read(
        quote: PurchaseQuote,
        user_names: dict[UUID, str],
        lowest_total: float | None = None,
        selected_quote_id: UUID | None = None,
    ) -> PurchaseQuoteRead:
        total = _quote_total(quote)
        return PurchaseQuoteRead(
            id=quote.id,
            purchase_request_id=quote.purchase_request_id,
            supplier_name=quote.supplier_name,
            supplier_contact=quote.supplier_contact,
            unit_price=quote.unit_price,
            quantity=quote.quantity,
            notes=quote.notes,
            extra_fields=quote.extra_fields or [],
            created_by_id=quote.created_by_id,
            created_by_name=user_names.get(quote.created_by_id),
            is_selected=selected_quote_id is not None
            and selected_quote_id == quote.id,
            is_lowest_price=lowest_total is not None and total == lowest_total,
            created_at=quote.created_at,
            updated_at=quote.updated_at,
        )

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

        now = datetime.now(UTC)
        purchase_request = PurchaseRequest(
            **request_in.model_dump(),
            status=PurchaseRequestStatus.OPEN,
            requested_by_id=current_user.id,
            created_at=now,
            updated_at=now,
        )
        session.add(purchase_request)
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
            decisions_by_request.setdefault(
                decision.purchase_request_id, []
            ).append(decision)

        total_selected_value = 0.0
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
            total_selected_value=round(total_selected_value, 2),
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

        totals = [_quote_total(q) for q in quotes]
        lowest_total = min(totals) if totals else None
        quotes_sorted = sorted(quotes, key=lambda q: (_quote_total(q), q.created_at))
        quote_reads = [
            PurchaseService._build_quote_read(
                q,
                user_names,
                lowest_total=lowest_total,
                selected_quote_id=current.quote_id if current else None,
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
        """Update the free-text fields of a purchase request."""
        PurchaseService._assert_can_view(current_user, session, "purchases:update")
        purchase_request = PurchaseService._get_request_or_404(session, request_id)
        PurchaseService._assert_can_write_request(
            current_user, purchase_request, session
        )

        for key, value in request_in.model_dump(exclude_unset=True).items():
            setattr(purchase_request, key, value)
        purchase_request.updated_at = datetime.now(UTC)
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
    def delete_request(
        session: Session, current_user: User, request_id: UUID
    ) -> None:
        """Delete a purchase request and cascade its quotes and decisions."""
        PurchaseService._assert_can_view(current_user, session, "purchases:delete")
        purchase_request = PurchaseService._get_request_or_404(session, request_id)
        PurchaseService._assert_can_write_request(
            current_user, purchase_request, session
        )

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
        purchase_request.updated_at = datetime.now(UTC)
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
            raise PurchaseAccessForbiddenError(
                "Acesso às cotações de compra negado."
            )
        purchase_request = PurchaseService._get_request_or_404(session, request_id)
        PurchaseService._assert_quotes_unfrozen(purchase_request)

        now = datetime.now(UTC)
        data = quote_in.model_dump()
        extra_fields = data.pop("extra_fields", [])
        quote = PurchaseQuote(
            **data,
            purchase_request_id=purchase_request.id,
            extra_fields=extra_fields,
            created_by_id=current_user.id,
            created_at=now,
            updated_at=now,
        )
        session.add(quote)
        session.commit()
        session.refresh(quote)

        return PurchaseService._build_quote_read(
            quote, {current_user.id: current_user.full_name or current_user.email}
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
        for key, value in update_data.items():
            setattr(quote, key, value)
        quote.updated_at = datetime.now(UTC)
        session.add(quote)
        session.commit()
        session.refresh(quote)

        user_names = PurchaseService._resolve_user_names(
            session, {quote.created_by_id}
        )
        return PurchaseService._build_quote_read(quote, user_names)

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

        session.delete(quote)
        session.commit()

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

        now = datetime.now(UTC)
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
