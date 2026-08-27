"""Global exception handlers."""

from app.core.exceptions import (
    AccessDeviceNotFoundError,
    AccessLogNotFoundError,
    AnnouncementCommentNotFoundError,
    AnnouncementMediaNotFoundError,
    AnnouncementMediaTooLargeError,
    AnnouncementNotFoundError,
    AnnouncementPermissionError,
    AuthorizationNotFoundError,
    DocumentFolderNotFoundError,
    DocumentNotFoundError,
    DomainError,
    FolderAccessDeniedError,
    ForbiddenError,
    InvalidAnnouncementMediaFormatError,
    InvalidDeviceKeyError,
    InvalidFolderHierarchyError,
    InvalidPhotoFormatError,
    LotAlreadyExistsError,
    LotNotFoundError,
    MediaAssetNotFoundError,
    OccurrenceAccessForbiddenError,
    OccurrenceNotFoundError,
    PhotoApprovalPermissionError,
    PhotoFileTooLargeError,
    PhotoRejectionReasonRequiredError,
    ResidentAlreadyLinkedError,
    ResidentCPFConflictError,
    ResidentNotFoundError,
    TaskNotFoundError,
    UserLotLinkAlreadyExistsError,
    UserLotLinkNotFoundError,
    VisitorNotFoundError,
)
from fastapi import Request, status
from fastapi.responses import JSONResponse


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
            AnnouncementNotFoundError,
            AnnouncementCommentNotFoundError,
            AnnouncementMediaNotFoundError,
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
            AnnouncementPermissionError,
        ),
    ):
        status_code = status.HTTP_403_FORBIDDEN
    elif isinstance(exc, ResidentCPFConflictError):
        status_code = status.HTTP_409_CONFLICT
    elif isinstance(exc, InvalidDeviceKeyError):
        status_code = status.HTTP_401_UNAUTHORIZED
    elif isinstance(
        exc,
        (
            InvalidFolderHierarchyError,
            PhotoFileTooLargeError,
            InvalidPhotoFormatError,
            PhotoRejectionReasonRequiredError,
            InvalidAnnouncementMediaFormatError,
            AnnouncementMediaTooLargeError,
        ),
    ):
        status_code = status.HTTP_400_BAD_REQUEST

    return JSONResponse(
        status_code=status_code,
        content={"detail": exc.message},
    )



