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
    InsufficientContrastError,
    InsufficientStockError,
    InvalidAnnouncementMediaFormatError,
    InvalidBrandThemeError,
    InvalidDeviceKeyError,
    InvalidFolderHierarchyError,
    InvalidInvoiceFormatError,
    InvalidPhotoFormatError,
    InvalidSlugError,
    InvitationAlreadyUsedError,
    InvitationCpfConflictError,
    InvitationExpiredError,
    InvitationIncompleteError,
    InvitationInvalidAccountError,
    InvitationNotFoundError,
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
    QuoteAttachmentInvalidFormatError,
    QuoteAttachmentTooLargeError,
    ReservableSpaceNotFoundError,
    ResidentCPFConflictError,
    ResidentNotFoundError,
    SlugAlreadyTakenError,
    SpaceReservationConflictError,
    SpaceReservationNotFoundError,
    SubscriptionNotFoundError,
    TallyNotAvailableError,
    TaskNotFoundError,
    TenantAlreadyExistsError,
    TenantLogoInvalidFormatError,
    TenantLogoTooLargeError,
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
            # APRAS-71 D7: an unknown or malformed invitation token. Generic
            # on purpose -- the body never names the invited address.
            InvitationNotFoundError,
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
            # APRAS-66 D-C.3: a typed slug another tenant holds. Never a
            # suffix walk -- that rule exists only where the *system* invents
            # the value.
            SlugAlreadyTakenError,
            # APRAS-40 §6.1
            PlanAlreadyExistsError,
            # APRAS-44: the duplicate article, and the three states in
            # which a shape-valid request has no answer (§6.3, §6.5, §7.5).
            InfractionRuleConflictError,
            InfractionStateError,
            # APRAS-71 D7/D9: a consumed invitation, and the duplicate CPF
            # of the new-account branch. Neither consumes anything.
            InvitationAlreadyUsedError,
            InvitationCpfConflictError,
        ),
    ):
        status_code = status.HTTP_409_CONFLICT
    elif isinstance(exc, InvitationExpiredError):
        # APRAS-71 D7: distinguishable from both 404 and 409, so the invitee
        # learns whether to ask for a new link or simply sign in.
        status_code = status.HTTP_410_GONE
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
            # APRAS-61 D5: a refused condominium logo. Their own classes
            # rather than the media pipeline's Photo* pair, which is mapped
            # to 400 below and is a published contract.
            TenantLogoInvalidFormatError,
            TenantLogoTooLargeError,
            # APRAS-63 D3: a refused supplier document on a quote, by the
            # same precedent and for the same reason.
            QuoteAttachmentInvalidFormatError,
            QuoteAttachmentTooLargeError,
            # APRAS-66 D-C.4: a typed slug outside `^[a-z0-9]+(-[a-z0-9]+)*$`
            # or the 3-64 bound. Refused, never folded into a valid one.
            InvalidSlugError,
            # APRAS-71 D9: the new-account branch with a field missing, or
            # with an email, CPF or password `UserCreate` refuses. The body
            # names something wrong, so 422 and never 400.
            InvitationIncompleteError,
            InvitationInvalidAccountError,
            # APRAS-68 D-B: an unusable brand-colour object, and an advanced
            # palette carrying an illegible pair. The refusal lives in the
            # API, not only on the screen, so a request that bypasses the UI
            # is refused all the same.
            InvalidBrandThemeError,
            InsufficientContrastError,
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

    content: dict[str, object] = {"detail": exc.message}
    if isinstance(exc, InsufficientContrastError):
        # The only error that carries structured data beside its message
        # (APRAS-68 D-B): every failing pair, its measured ratio and the 4.5
        # minimum, so a caller outside the screen learns exactly what a
        # person editing the palette would have seen.
        content["failures"] = exc.failures

    return JSONResponse(status_code=status_code, content=content)
