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
    AnonymousAssemblyError,
    AssemblyNotClosedError,
    AssemblyNotFoundError,
    AssemblyStatusTransitionError,
    AssetAccessForbiddenError,
    AssetNotFoundError,
    AssetTagAlreadyExistsError,
    AuthorizationNotFoundError,
    BudgetLineAlreadyExistsError,
    BudgetLineNotFoundError,
    CrossTenantWriteError,
    DelinquentLotError,
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
    InfractionContestationForbiddenError,
    InfractionNotFoundError,
    InfractionRuleConflictError,
    InfractionRuleNotFoundError,
    InfractionStateError,
    InfractionValidationError,
    InsufficientStockError,
    InvalidAnnouncementMediaFormatError,
    InvalidDeviceKeyError,
    InvalidFolderHierarchyError,
    InvalidInvoiceFormatError,
    InvalidPhotoFormatError,
    InvoiceFileTooLargeError,
    LotAlreadyVotedError,
    LotNotFoundError,
    MediaAssetNotFoundError,
    MilestoneNotFoundError,
    NoActiveBallotError,
    NoActiveLotLinkError,
    NotLotOwnerError,
    OccurrenceAccessForbiddenError,
    OccurrenceNotFoundError,
    PackageAccessForbiddenError,
    PackageAlreadyPickedUpError,
    PackageNotFoundError,
    PhotoApprovalPermissionError,
    PhotoFileTooLargeError,
    PhotoRejectionReasonRequiredError,
    PlanAlreadyExistsError,
    PlanNotFoundError,
    ProjectAccessForbiddenError,
    ProjectInvalidProgressError,
    ProjectNotFoundError,
    ProjectUpdateNotFoundError,
    PurchaseAccessForbiddenError,
    PurchaseQuoteFrozenError,
    PurchaseQuoteNotFoundError,
    PurchaseRequestNotFoundError,
    PurchaseRequestNotOpenError,
    ReservableSpaceNotFoundError,
    ResidentCPFConflictError,
    ResidentNotFoundError,
    SpaceReservationConflictError,
    SpaceReservationNotFoundError,
    SubscriptionNotFoundError,
    TallyNotAvailableError,
    TaskNotFoundError,
    TenantAlreadyExistsError,
    TenantMembershipAlreadyExistsError,
    TenantMembershipNotFoundError,
    TenantNotFoundError,
    UnknownRoleIdsError,
    UserLotLinkNotFoundError,
    VisitorNotFoundError,
    VoteAlreadyClosedError,
    VoteFrozenError,
    VoteNotFoundError,
    VoteNotOpenError,
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
            PackageNotFoundError,
            AssemblyNotFoundError,
            VoteNotFoundError,
            NoActiveBallotError,
            AssetNotFoundError,
            PurchaseRequestNotFoundError,
            PurchaseQuoteNotFoundError,
            TenantNotFoundError,
            TenantMembershipNotFoundError,
            # APRAS-40 §6.1
            PlanNotFoundError,
            SubscriptionNotFoundError,
            # APRAS-44 §7.4, §7.5
            InfractionRuleNotFoundError,
            InfractionNotFoundError,
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
            PackageAccessForbiddenError,
            DelinquentLotError,
            NotLotOwnerError,
            NoActiveLotLinkError,
            TallyNotAvailableError,
            LotAlreadyVotedError,
            AssetAccessForbiddenError,
            PurchaseAccessForbiddenError,
            CrossTenantWriteError,
            # APRAS-44 §7.5: an object check, applied to every caller
            # including a superuser and a tenant admin.
            InfractionContestationForbiddenError,
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
            PackageAlreadyPickedUpError,
            AssetTagAlreadyExistsError,
            PurchaseQuoteFrozenError,
            TenantAlreadyExistsError,
            TenantMembershipAlreadyExistsError,
            # APRAS-40 §6.1
            PlanAlreadyExistsError,
            # APRAS-44: the duplicate article, and the three states in
            # which a shape-valid request has no answer (§6.3, §6.5, §7.5).
            InfractionRuleConflictError,
            InfractionStateError,
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
            UnknownRoleIdsError,
            # APRAS-44 §7.7: the module's single 'the body names
            # something wrong' code -- never 400, never 409.
            InfractionValidationError,
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
            VoteNotOpenError,
            VoteAlreadyClosedError,
            VoteFrozenError,
            AnonymousAssemblyError,
            AssemblyNotClosedError,
            AssemblyStatusTransitionError,
            InsufficientStockError,
            PurchaseRequestNotOpenError,
        ),
    ):
        status_code = status.HTTP_400_BAD_REQUEST

    return JSONResponse(
        status_code=status_code,
        content={"detail": exc.message},
    )



