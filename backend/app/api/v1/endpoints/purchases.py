"""API endpoints for purchase quotation management (APRAS-37)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlmodel import Session

from app.api import deps
from app.models.enums import PurchaseRequestStatus
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
from app.services.purchase_service import PurchaseService

router = APIRouter()


@router.get("")
def list_purchase_requests(
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
    status_filter: Annotated[PurchaseRequestStatus | None, Query(alias="status")] = None,
    requested_by_id: Annotated[UUID | None, Query()] = None,
    search: Annotated[str | None, Query()] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> PaginatedPurchaseRequestRead:
    """List purchase requests with filters, search and pagination."""
    return PurchaseService.list_requests(
        session=session,
        current_user=current_user,
        status=status_filter,
        requested_by_id=requested_by_id,
        search=search,
        skip=skip,
        limit=limit,
    )


# Declared before /{request_id} so "summary" is never parsed as a UUID.
@router.get("/summary")
def get_purchase_summary(
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> PurchaseSummaryRead:
    """Aggregate metrics for the purchase quotation dashboard."""
    return PurchaseService.get_summary(session=session, current_user=current_user)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_purchase_request(
    request_in: PurchaseRequestCreate,
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> PurchaseRequestRead:
    """Open a new purchase request (Administrator / Director / Manager)."""
    return PurchaseService.create_request(
        session=session, current_user=current_user, request_in=request_in
    )


@router.get("/{request_id}")
def get_purchase_request(
    request_id: UUID,
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> PurchaseRequestDetailRead:
    """Get a purchase request with its quotes and decision history."""
    return PurchaseService.get_request(
        session=session, current_user=current_user, request_id=request_id
    )


@router.put("/{request_id}")
def update_purchase_request(
    request_id: UUID,
    request_in: PurchaseRequestUpdate,
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> PurchaseRequestRead:
    """Update a purchase request (Managers only on their own open requests)."""
    return PurchaseService.update_request(
        session=session,
        current_user=current_user,
        request_id=request_id,
        request_in=request_in,
    )


@router.delete("/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_purchase_request(
    request_id: UUID,
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> Response:
    """Delete a purchase request and its quotes and decisions."""
    PurchaseService.delete_request(
        session=session, current_user=current_user, request_id=request_id
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{request_id}/quotes", status_code=status.HTTP_201_CREATED)
def add_quote(
    request_id: UUID,
    quote_in: PurchaseQuoteCreate,
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> PurchaseQuoteRead:
    """Add a supplier quote to an open purchase request."""
    return PurchaseService.add_quote(
        session=session,
        current_user=current_user,
        request_id=request_id,
        quote_in=quote_in,
    )


@router.put("/{request_id}/quotes/{quote_id}")
def update_quote(
    request_id: UUID,
    quote_id: UUID,
    quote_in: PurchaseQuoteUpdate,
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> PurchaseQuoteRead:
    """Update a supplier quote on an open purchase request."""
    return PurchaseService.update_quote(
        session=session,
        current_user=current_user,
        request_id=request_id,
        quote_id=quote_id,
        quote_in=quote_in,
    )


@router.delete(
    "/{request_id}/quotes/{quote_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_quote(
    request_id: UUID,
    quote_id: UUID,
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> Response:
    """Delete a supplier quote from an open purchase request."""
    PurchaseService.delete_quote(
        session=session,
        current_user=current_user,
        request_id=request_id,
        quote_id=quote_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{request_id}/decision", status_code=status.HTTP_201_CREATED)
def select_quote(
    request_id: UUID,
    decision_in: PurchaseDecisionCreate,
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> PurchaseDecisionRead:
    """Record the justified choice of one quote (Administrator / Director)."""
    return PurchaseService.select_quote(
        session=session,
        current_user=current_user,
        request_id=request_id,
        decision_in=decision_in,
    )


@router.post("/{request_id}/cancel")
def cancel_purchase_request(
    request_id: UUID,
    session: Annotated[Session, Depends(deps.get_session)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
) -> PurchaseRequestRead:
    """Cancel an open purchase request (Administrator / Director)."""
    return PurchaseService.cancel_request(
        session=session, current_user=current_user, request_id=request_id
    )
