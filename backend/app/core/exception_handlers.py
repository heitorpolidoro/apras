"""Global exception handlers."""

from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    AccessDeviceNotFoundError,
    AccessLogNotFoundError,
    AnnouncementCommentNotFoundError,
    AnnouncementMediaNotFoundError,
    AnnouncementMediaTooLargeError,
    AnnouncementNotFoundError,
    AnnouncementPermissionError,
    AuthorizationNotFoundError,
    BudgetLineAlreadyExistsError,
    BudgetLineNotFoundError,
    DocumentFolderNotFoundError,
    DocumentNotFoundError,
    DomainError,
    FeedbackAccessForbiddenError,
    FeedbackNotFoundError,
    FinanceAccessForbiddenError,
    FinanceCategoryAlreadyExistsError,
    FinanceCategoryNotFoundError,
    FinanceCategoryTypeMismatchError,
    FinancialTransactionNotFoundError,
    FolderAccessDeniedError,
    ForbiddenError,
    InvalidAnnouncementMediaFormatError,
    InvalidDeviceKeyError,
    InvalidFolderHierarchyError,
    InvalidInvoiceFormatError,
    InvalidPhotoFormatError,
    InvoiceFileTooLargeError,
    LotNotFoundError,
    MediaAssetNotFoundError,
    MilestoneNotFoundError,
    OccurrenceAccessForbiddenError,
    OccurrenceNotFoundError,
    PhotoApprovalPermissionError,
    PhotoFileTooLargeError,
    PhotoRejectionReasonRequiredError,
    ProjectAccessForbiddenError,
    ProjectInvalidProgressError,
    ProjectNotFoundError,
    ProjectUpdateNotFoundError,
    ReservableSpaceNotFoundError,
    ResidentCPFConflictError,
    ResidentNotFoundError,
    SpaceReservationConflictError,
    SpaceReservationNotFoundError,
    TaskNotFoundError,
    UserLotLinkNotFoundError,
    VisitorNotFoundError,
)


async def domain_exception_handler(_: Request, exc: DomainError) -> JSONResponse:
    """
    Global handler for domain-specific exceptions.
    Converts DomainError subclasses to appropriate HTTP responses.

    Args:
        _: The incoming FastAPI request (unused).
        exc: The raised DomainError.

    Returns:
        JSONResponse: A response with appropriate status code and error message.
    """
    status_code = status.HTTP_400_BAD_REQUEST

    if isinstance(
        exc,
        (
            TaskNotFoundError,
            LotNotFoundError,
            UserLotLinkNotFoundError,
            ResidentNotFoundError,
            VisitorNotFoundError,
            AuthorizationNotFoundError,
            AccessLogNotFoundError,
            OccurrenceNotFoundError,
            DocumentFolderNotFoundError,
            DocumentNotFoundError,
            MediaAssetNotFoundError,
            AccessDeviceNotFoundError,
            ProjectNotFoundError,
            MilestoneNotFoundError,
            ProjectUpdateNotFoundError,
            AnnouncementNotFoundError,
            AnnouncementCommentNotFoundError,
            AnnouncementMediaNotFoundError,
            FinanceCategoryNotFoundError,
            BudgetLineNotFoundError,
            FinancialTransactionNotFoundError,
            FeedbackNotFoundError,
            ReservableSpaceNotFoundError,
            SpaceReservationNotFoundError,
        ),
    ):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(
        exc,
        (
            ForbiddenError,
            OccurrenceAccessForbiddenError,
            FolderAccessDeniedError,
            PhotoApprovalPermissionError,
            ProjectAccessForbiddenError,
            AnnouncementPermissionError,
            FinanceAccessForbiddenError,
            FeedbackAccessForbiddenError,
        ),
    ):
        status_code = status.HTTP_403_FORBIDDEN
    elif isinstance(
        exc,
        (
            ResidentCPFConflictError,
            BudgetLineAlreadyExistsError,
            FinanceCategoryAlreadyExistsError,
            SpaceReservationConflictError,
        ),
    ):
        status_code = status.HTTP_409_CONFLICT
    elif isinstance(exc, InvalidDeviceKeyError):
        status_code = status.HTTP_401_UNAUTHORIZED
    elif isinstance(exc, InvoiceFileTooLargeError):
        status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    elif isinstance(
        exc,
        (
            FinanceCategoryTypeMismatchError,
            InvalidInvoiceFormatError,
        ),
    ):
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    elif isinstance(
        exc,
        (
            InvalidFolderHierarchyError,
            PhotoFileTooLargeError,
            InvalidPhotoFormatError,
            PhotoRejectionReasonRequiredError,
            ProjectInvalidProgressError,
            InvalidAnnouncementMediaFormatError,
            AnnouncementMediaTooLargeError,
        ),
    ):
        status_code = status.HTTP_400_BAD_REQUEST

    return JSONResponse(
        status_code=status_code,
        content={"detail": exc.message},
    )



