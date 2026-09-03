"""Domain exceptions."""

from collections.abc import Iterable
from uuid import UUID


class DomainError(Exception):
    """Base class for domain exceptions."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)


class TaskNotFoundError(DomainError):
    """Raised when a task is not found."""

    def __init__(self, task_id: UUID) -> None:
        super().__init__(f"Task with ID {task_id} not found")


class ForbiddenError(DomainError):
    """Raised when a user does not have permission for an action."""

    def __init__(self, message: str = "Not enough privileges") -> None:
        super().__init__(message)


class LotNotFoundError(DomainError):
    """Raised when a lot is not found."""

    def __init__(self, lot_id: UUID) -> None:
        super().__init__(f"Lot with ID {lot_id} not found")


class LotAlreadyExistsError(DomainError):
    """Raised when a lot with given block and lot_number already exists."""

    def __init__(self, block: str, lot_number: str) -> None:
        super().__init__(f"Lot with block '{block}' and lot number '{lot_number}' already exists")


class UserLotLinkAlreadyExistsError(DomainError):
    """Raised when a user is already linked to a lot."""

    def __init__(self, user_id: UUID, lot_id: UUID) -> None:
        super().__init__(f"User {user_id} is already linked to lot {lot_id}")


class UserLotLinkNotFoundError(DomainError):
    """Raised when a user lot link is not found."""

    def __init__(self, user_id: UUID, lot_id: UUID) -> None:
        super().__init__(f"Link between user {user_id} and lot {lot_id} not found")


class ResidentNotFoundError(DomainError):
    """Raised when a resident is not found."""

    def __init__(self, resident_id: UUID) -> None:
        super().__init__(f"Resident with ID {resident_id} not found")


class ResidentAlreadyLinkedError(DomainError):
    """Raised when a resident is already linked to a user account."""

    def __init__(self, message: str = "Resident is already linked to a user account") -> None:
        super().__init__(message)


class ResidentCPFConflictError(DomainError):
    """Raised when an active resident with given CPF already exists in lot."""

    def __init__(self, cpf: str) -> None:
        super().__init__(f"Active resident with CPF '{cpf}' already exists in this lot")


class VisitorNotFoundError(DomainError):
    """Raised when a visitor is not found."""

    def __init__(self, visitor_id: UUID | str) -> None:
        super().__init__(f"Visitor with ID {visitor_id} not found")


class AuthorizationNotFoundError(DomainError):
    """Raised when an authorization is not found."""

    def __init__(self, auth_id: UUID | str) -> None:
        super().__init__(f"Authorization with ID {auth_id} not found")


class AuthorizationExpiredError(DomainError):
    """Raised when authorization is expired."""

    def __init__(self, message: str = "Authorization has expired") -> None:
        super().__init__(message)


class AuthorizationRevokedError(DomainError):
    """Raised when authorization has been revoked."""

    def __init__(self, message: str = "Authorization has been revoked") -> None:
        super().__init__(message)


class AuthorizationInvalidShiftError(DomainError):
    """Raised when entry check-in shift is invalid."""

    def __init__(self, message: str = "Entry denied: shift window not allowed") -> None:
        super().__init__(message)


AccessDeniedShiftError = AuthorizationInvalidShiftError


class AuthorizationInvalidDayError(DomainError):
    """Raised when entry check-in day of week is invalid."""

    def __init__(self, message: str = "Entry denied: day of week not allowed") -> None:
        super().__init__(message)


AccessDeniedDayError = AuthorizationInvalidDayError


class AccessLogNotFoundError(DomainError):
    """Raised when access log is not found."""

    def __init__(self, message: str = "Access log not found") -> None:
        super().__init__(message)


NoActiveCheckInError = AccessLogNotFoundError


class OpenEntryExistsError(DomainError):
    """Raised when visitor already has an active open check-in."""

    def __init__(self, message: str = "Visitor already has an active check-in") -> None:
        super().__init__(message)


VisitorAlreadyCheckedInError = OpenEntryExistsError


class OccurrenceNotFoundError(DomainError):
    """Raised when an occurrence is not found."""

    def __init__(self, occurrence_id: UUID | str) -> None:
        super().__init__(f"Occurrence with ID {occurrence_id} not found")


class OccurrenceAccessForbiddenError(DomainError):
    """Raised when access to an occurrence is forbidden."""

    def __init__(self, message: str = "Access to occurrence forbidden") -> None:
        super().__init__(message)


OccurrencePermissionError = OccurrenceAccessForbiddenError


class FeedbackNotFoundError(DomainError):
    """Raised when a feedback submission is not found."""

    def __init__(self, feedback_id: UUID | str) -> None:
        super().__init__(f"Feedback with ID {feedback_id} not found")


class FeedbackAccessForbiddenError(DomainError):
    """Raised when access to a feedback submission or action is forbidden."""

    def __init__(self, message: str = "Access to feedback forbidden") -> None:
        super().__init__(message)


class DocumentFolderNotFoundError(DomainError):
    """Raised when a document folder is not found."""

    def __init__(self, folder_id: UUID | str) -> None:
        super().__init__(f"Document folder with ID {folder_id} not found")


FolderNotFoundError = DocumentFolderNotFoundError


class DocumentNotFoundError(DomainError):
    """Raised when a document is not found."""

    def __init__(self, document_id: UUID | str) -> None:
        super().__init__(f"Document with ID {document_id} not found")


class FolderAccessDeniedError(DomainError):
    """Raised when access to a document folder is denied."""

    def __init__(self, message: str = "Access to document folder forbidden") -> None:
        super().__init__(message)


FolderAccessForbiddenError = FolderAccessDeniedError


class UnknownRoleIdsError(DomainError):
    """Raised when a payload names role ids that do not resolve.

    "Do not resolve" means either of the two ways an id can be wrong, and
    they are deliberately not distinguished in the message: an id that
    belongs to no role at all, and one that belongs to a role of *another*
    tenant. Telling the two apart would answer "does role X exist somewhere
    on this install?" for a caller who is not entitled to know.
    """

    def __init__(
        self, role_ids: Iterable[object], field: str = "allowed_role_ids"
    ) -> None:
        listed = ", ".join(sorted(str(item) for item in role_ids))
        super().__init__(f"Unknown {field}: {listed}")


class InvalidFolderHierarchyError(DomainError):
    """Raised when folder hierarchy is invalid or folder is not empty upon deletion."""

    def __init__(self, message: str = "Invalid folder operation or folder hierarchy") -> None:
        super().__init__(message)


FolderNotEmptyError = InvalidFolderHierarchyError


class MediaAssetNotFoundError(DomainError):
    """Raised when a photo asset is not found."""

    def __init__(self, photo_id: UUID | str = "") -> None:
        msg = f"Foto {photo_id} não encontrada." if photo_id else "Foto não encontrada."
        super().__init__(msg)


class PhotoFileTooLargeError(DomainError):
    """Raised when uploaded photo file exceeds 5MB limit."""

    def __init__(self, message: str = "Arquivo excede o limite máximo permitido de 5MB.") -> None:
        super().__init__(message)


ImageSizeExceededError = PhotoFileTooLargeError


class InvalidPhotoFormatError(DomainError):
    """Raised when uploaded photo file has invalid MIME type or corrupted binary."""

    def __init__(self, message: str = "Formato de imagem inválido. Formatos aceitos: JPEG, PNG, WebP.") -> None:
        super().__init__(message)


InvalidImageFormatError = InvalidPhotoFormatError


class PhotoApprovalPermissionError(DomainError):
    """Raised when user lacks permission to approve or reject photos."""

    def __init__(self, message: str = "Apenas Administradores e Diretores podem aprovar ou rejeitar fotos.") -> None:
        super().__init__(message)


class PhotoRejectionReasonRequiredError(DomainError):
    """Raised when rejection reason is empty or missing."""

    def __init__(self, message: str = "Motivo de rejeição é obrigatório.") -> None:
        super().__init__(message)


class AccessDeviceNotFoundError(DomainError):
    """Raised when an access control device is not found."""

    def __init__(self, device_id: UUID | str = "") -> None:
        msg = (
            f"Dispositivo de acesso {device_id} não encontrado."
            if device_id
            else "Dispositivo de acesso não encontrado."
        )
        super().__init__(msg)


class DuplicateDeviceNameError(DomainError):
    """Raised when registering a device with a name already in use."""

    def __init__(self, name: str = "") -> None:
        msg = (
            f"Já existe um dispositivo com o nome '{name}'."
            if name
            else "Já existe um dispositivo com esse nome."
        )
        super().__init__(msg)


class InvalidDeviceKeyError(DomainError):
    """Raised when a webhook call presents a missing or unknown device key."""

    def __init__(self, message: str = "Chave de dispositivo inválida ou ausente.") -> None:
        super().__init__(message)


class NoApprovedPhotoError(DomainError):
    """Raised when attempting to sync a facial template without an approved photo."""

    def __init__(
        self,
        message: str = "Morador não possui foto aprovada para sincronização facial.",
    ) -> None:
        super().__init__(message)


class ProjectNotFoundError(DomainError):
    """Raised when a construction project is not found."""

    def __init__(self, project_id: UUID | str = "") -> None:
        msg = f"Projeto de obra {project_id} não encontrado." if project_id else "Projeto de obra não encontrado."
        super().__init__(msg)


class MilestoneNotFoundError(DomainError):
    """Raised when a milestone is not found."""

    def __init__(self, milestone_id: UUID | str = "") -> None:
        msg = f"Marco da obra {milestone_id} não encontrado." if milestone_id else "Marco da obra não encontrado."
        super().__init__(msg)


class ProjectUpdateNotFoundError(DomainError):
    """Raised when a project update log is not found."""

    def __init__(self, update_id: UUID | str = "") -> None:
        msg = f"Atualização de obra {update_id} não encontrada." if update_id else "Atualização de obra não encontrada."
        super().__init__(msg)


class ProjectAccessForbiddenError(DomainError):
    """Raised when access to a project or project action is forbidden."""

    def __init__(self, message: str = "Acesso ao projeto de obra negado.") -> None:
        super().__init__(message)


ProjectPermissionError = ProjectAccessForbiddenError


class ProjectInvalidProgressError(DomainError):
    """Raised when progress percentage or budget configuration is invalid."""

    def __init__(self, message: str = "Porcentagem de progresso inválida (deve estar entre 0% e 100%).") -> None:
        super().__init__(message)


class AnnouncementNotFoundError(DomainError):
    """Raised when an announcement is not found."""

    def __init__(self, announcement_id: UUID | str = "") -> None:
        msg = (
            f"Comunicado {announcement_id} não encontrado."
            if announcement_id
            else "Comunicado não encontrado."
        )
        super().__init__(msg)


class AnnouncementCommentNotFoundError(DomainError):
    """Raised when an announcement comment is not found."""

    def __init__(self, comment_id: UUID | str = "") -> None:
        msg = (
            f"Comentário {comment_id} não encontrado." if comment_id else "Comentário não encontrado."
        )
        super().__init__(msg)


class AnnouncementMediaNotFoundError(DomainError):
    """Raised when an announcement media item is not found."""

    def __init__(self, media_id: UUID | str = "") -> None:
        msg = f"Mídia {media_id} não encontrada." if media_id else "Mídia não encontrada."
        super().__init__(msg)


class AnnouncementPermissionError(DomainError):
    """Raised when a user lacks permission for an announcement action."""

    def __init__(
        self, message: str = "Apenas Administradores e Diretores podem publicar comunicados."
    ) -> None:
        super().__init__(message)


class InvalidAnnouncementMediaFormatError(DomainError):
    """Raised when uploaded announcement media has an unsupported MIME type or is corrupted."""

    def __init__(
        self,
        message: str = "Formato de mídia inválido. Formatos aceitos: JPEG, PNG, WebP, PDF.",
    ) -> None:
        super().__init__(message)


class AnnouncementMediaTooLargeError(DomainError):
    """Raised when uploaded announcement media exceeds the 10MB limit."""

    def __init__(
        self, message: str = "Arquivo excede o limite máximo permitido de 10MB."
    ) -> None:
        super().__init__(message)


class FinanceCategoryNotFoundError(DomainError):
    """Raised when a finance category is not found."""

    def __init__(self, category_id: UUID | str = "") -> None:
        msg = (
            f"Categoria financeira {category_id} não encontrada."
            if category_id
            else "Categoria financeira não encontrada."
        )
        super().__init__(msg)


class FinanceCategoryAlreadyExistsError(DomainError):
    """Raised when a finance category with the same (name, type) already exists."""

    def __init__(
        self,
        message: str = "Já existe uma categoria financeira com este nome e tipo.",
    ) -> None:
        super().__init__(message)


class FinanceCategoryTypeMismatchError(DomainError):
    """Raised when a transaction's type does not match its category's type."""

    def __init__(
        self,
        message: str = "O tipo da transação não corresponde ao tipo da categoria.",
    ) -> None:
        super().__init__(message)


class BudgetLineNotFoundError(DomainError):
    """Raised when a budget line is not found."""

    def __init__(self, budget_line_id: UUID | str = "") -> None:
        msg = (
            f"Linha de orçamento {budget_line_id} não encontrada."
            if budget_line_id
            else "Linha de orçamento não encontrada."
        )
        super().__init__(msg)


class BudgetLineAlreadyExistsError(DomainError):
    """Raised when a budget line for the same category/fiscal year already exists."""

    def __init__(
        self,
        message: str = "Já existe uma linha de orçamento para esta categoria e ano fiscal.",
    ) -> None:
        super().__init__(message)


class FinancialTransactionNotFoundError(DomainError):
    """Raised when a financial transaction is not found."""

    def __init__(self, transaction_id: UUID | str = "") -> None:
        msg = (
            f"Transação financeira {transaction_id} não encontrada."
            if transaction_id
            else "Transação financeira não encontrada."
        )
        super().__init__(msg)


class FinanceAccessForbiddenError(DomainError):
    """Raised when access to a finance module action is forbidden."""

    def __init__(
        self, message: str = "Acesso ao módulo financeiro negado."
    ) -> None:
        super().__init__(message)


class InvalidInvoiceFormatError(DomainError):
    """Raised when uploaded invoice file has an unsupported MIME type."""

    def __init__(
        self,
        message: str = "Formato de nota fiscal inválido. Apenas arquivos PDF são aceitos.",
    ) -> None:
        super().__init__(message)


class InvoiceFileTooLargeError(DomainError):
    """Raised when uploaded invoice file exceeds the 10MB limit."""

    def __init__(
        self, message: str = "Arquivo excede o limite máximo permitido de 10MB."
    ) -> None:
        super().__init__(message)


class ReservableSpaceNotFoundError(DomainError):
    """Raised when a reservable space is not found."""

    def __init__(self, space_id: UUID) -> None:
        super().__init__(f"Reservable space with ID {space_id} not found")


class SpaceReservationNotFoundError(DomainError):
    """Raised when a space reservation is not found or not visible to the caller."""

    def __init__(self, reservation_id: UUID) -> None:
        super().__init__(f"Reservation with ID {reservation_id} not found")


class SpaceReservationConflictError(DomainError):
    """Raised when a reservation would overlap an existing CONFIRMED/PENDING booking."""

    def __init__(self) -> None:
        super().__init__("This space is already booked for the requested time window")


class PackageNotFoundError(DomainError):
    """Raised when a package is not found."""

    def __init__(self, package_id: UUID | str = "") -> None:
        msg = f"Encomenda {package_id} não encontrada." if package_id else "Encomenda não encontrada."
        super().__init__(msg)


class PackageAccessForbiddenError(DomainError):
    """Raised when access to a package or lot's packages is forbidden."""

    def __init__(self, message: str = "Acesso negado às encomendas deste lote.") -> None:
        super().__init__(message)


class PackageAlreadyPickedUpError(DomainError):
    """Raised when attempting to mark an already-picked-up package as picked up again."""

    def __init__(self, message: str = "Esta encomenda já foi retirada.") -> None:
        super().__init__(message)








class AssemblyNotFoundError(DomainError):
    """Raised when an assembly is not found."""

    def __init__(self, assembly_id: UUID | str = "") -> None:
        msg = (
            f"Assembleia {assembly_id} não encontrada."
            if assembly_id
            else "Assembleia não encontrada."
        )
        super().__init__(msg)


class AssemblyNotClosedError(DomainError):
    """Raised when the minutes are requested for an assembly still running.

    Minutes may only be generated or saved once the assembly is CLOSED
    (see APRAS-33 spec, "Semântica de `Assembly.status`").
    """

    def __init__(
        self,
        message: str = "A minuta só pode ser gerada depois do fechamento da assembleia.",
    ) -> None:
        super().__init__(message)


class AssemblyStatusTransitionError(DomainError):
    """Raised when an edit tries to move an assembly to CLOSED.

    Closing is not an attribute edit: it cascades into every open vote and
    freezes each tally snapshot, which is what unlocks the minutes. Only
    `POST /assemblies/{id}/close` may reach CLOSED — otherwise a plain
    `PATCH` would be a carve-out around the closed-window gate (see
    APRAS-33 spec, "Visibilidade e mascaramento", Regra 1).
    """

    def __init__(
        self,
        message: str = (
            "A assembleia só pode ser fechada pelo endpoint de fechamento, "
            "que apura e congela cada votação."
        ),
    ) -> None:
        super().__init__(message)


class VoteNotFoundError(DomainError):
    """Raised when a vote is not found."""

    def __init__(self, vote_id: UUID | str = "") -> None:
        msg = (
            f"Votação {vote_id} não encontrada." if vote_id else "Votação não encontrada."
        )
        super().__init__(msg)


class VoteNotOpenError(DomainError):
    """Raised when a ballot is cast outside the voting window."""

    def __init__(self, message: str = "Esta votação não está aberta.") -> None:
        super().__init__(message)


class VoteAlreadyClosedError(DomainError):
    """Raised when closing a vote that is already closed."""

    def __init__(self, message: str = "Esta votação já está fechada.") -> None:
        super().__init__(message)


class VoteFrozenError(DomainError):
    """Raised when editing a vote that already received at least one ballot."""

    def __init__(
        self,
        message: str = "A votação não pode ser editada depois da primeira cédula.",
    ) -> None:
        super().__init__(message)


class DelinquentLotError(DomainError):
    """Raised when a delinquent lot attempts to cast an assembly ballot."""

    def __init__(
        self, message: str = "Lote inadimplente: direito de voto suspenso."
    ) -> None:
        super().__init__(message)


class NotLotOwnerError(DomainError):
    """Raised when the user is not in the lot's eligible voter set."""

    def __init__(
        self, message: str = "Você não pode votar em nome deste lote."
    ) -> None:
        super().__init__(message)


class NoActiveLotLinkError(DomainError):
    """Raised when a poll ballot is cast by someone with no active lot link."""

    def __init__(
        self, message: str = "É necessário ter vínculo ativo com um lote para votar."
    ) -> None:
        super().__init__(message)


class TallyNotAvailableError(DomainError):
    """Raised when the caller may not read a vote's tally."""

    def __init__(
        self, message: str = "Você não tem permissão para ver esta apuração."
    ) -> None:
        super().__init__(message)


class AnonymousAssemblyError(DomainError):
    """Raised when an assembly vote is created with anonymity enabled."""

    def __init__(
        self, message: str = "Votação de assembleia é sempre nominal."
    ) -> None:
        super().__init__(message)


class LotAlreadyVotedError(DomainError):
    """Raised when another eligible voter already holds the lot's active ballot."""

    def __init__(
        self,
        message: str = "Outro elegível deste lote já lançou a cédula ativa.",
    ) -> None:
        super().__init__(message)


class NoActiveBallotError(DomainError):
    """Raised when retracting without an active ballot to retract."""

    def __init__(
        self, message: str = "Não há cédula ativa para retirar."
    ) -> None:
        super().__init__(message)


class AssetNotFoundError(DomainError):
    """Raised when an asset is not found."""

    def __init__(self, asset_id: UUID | str = "") -> None:
        msg = f"Ativo {asset_id} não encontrado." if asset_id else "Ativo não encontrado."
        super().__init__(msg)


class InsufficientStockError(DomainError):
    """Raised when an inventory exit exceeds available stock balance."""

    def __init__(self, message: str = "Saldo insuficiente em estoque.") -> None:
        super().__init__(message)


class AssetAccessForbiddenError(DomainError):
    """Raised when access to an asset or inventory action is forbidden."""

    def __init__(self, message: str = "Acesso ao ativo ou movimentação negado.") -> None:
        super().__init__(message)


class AssetTagAlreadyExistsError(DomainError):
    """Raised when an asset tag is already in use."""

    def __init__(self, asset_tag: str) -> None:
        super().__init__(f"Já existe um ativo com a etiqueta patrimonial '{asset_tag}'.")


class PurchaseRequestNotFoundError(DomainError):
    """Raised when a purchase request is not found."""

    def __init__(self, request_id: UUID | str = "") -> None:
        msg = (
            f"Pedido de compra {request_id} não encontrado."
            if request_id
            else "Pedido de compra não encontrado."
        )
        super().__init__(msg)


class PurchaseQuoteNotFoundError(DomainError):
    """Raised when a quote is unknown or belongs to another purchase request."""

    def __init__(self, quote_id: UUID | str = "") -> None:
        msg = (
            f"Orçamento {quote_id} não encontrado neste pedido."
            if quote_id
            else "Orçamento não encontrado neste pedido."
        )
        super().__init__(msg)


class PurchaseAccessForbiddenError(DomainError):
    """Raised when a role or ownership rule blocks a purchase action."""

    def __init__(
        self, message: str = "Acesso à cotação de compras negado."
    ) -> None:
        super().__init__(message)


class PurchaseRequestNotOpenError(DomainError):
    """Raised when an action requires a purchase request that is still open."""

    def __init__(
        self, message: str = "O pedido de compra não está aberto."
    ) -> None:
        super().__init__(message)


class PurchaseQuoteFrozenError(DomainError):
    """Raised when quotes are edited on a request that is no longer open."""

    def __init__(
        self,
        message: str = (
            "Os orçamentos deste pedido estão congelados e não podem ser alterados."
        ),
    ) -> None:
        super().__init__(message)


class TenantNotFoundError(DomainError):
    """Raised when a tenant is not found, or is hidden from a non-member.

    Deliberately also used for the "exists but you are not a member" case on
    `GET /api/v1/tenants/{id}`: a 403 there would leak the existence of a
    tenant the caller has no business knowing about.
    """

    def __init__(self, tenant_id: UUID) -> None:
        super().__init__(f"Tenant with ID {tenant_id} not found")


class TenantAlreadyExistsError(DomainError):
    """Raised when a tenant with the given name already exists.

    `tenant.name` is globally unique on purpose, so the administrator's
    tenant list is unambiguous.
    """

    def __init__(self, name: str) -> None:
        super().__init__(f"Tenant with name '{name}' already exists")


class TenantMembershipAlreadyExistsError(DomainError):
    """Raised when a user is already linked to the given tenant.

    Only the *same* (user, tenant) pair twice is a conflict — linking a user
    to a second tenant is supported multi-membership, not an error.
    """

    def __init__(self, user_id: UUID, tenant_id: UUID) -> None:
        super().__init__(f"User {user_id} is already a member of tenant {tenant_id}")


class TenantMembershipNotFoundError(DomainError):
    """Raised when a (user, tenant) membership does not exist."""

    def __init__(self, user_id: UUID, tenant_id: UUID) -> None:
        super().__init__(f"User {user_id} is not a member of tenant {tenant_id}")


class UnknownModuleError(DomainError):
    """Raised when a module string is not in the permission catalogue.

    A plain :class:`DomainError`, so it falls through to
    ``domain_exception_handler``'s ``status_code = 400`` initialisation with
    no edit of that module (APRAS-39 §6.3). It is deliberately *not* a
    Pydantic ``field_validator`` on ``TenantModulesUpdate``: FastAPI answers
    a schema-level rejection ``422``, and ER-2 pins ``400``.
    """

    def __init__(self, module: str) -> None:
        super().__init__(f"Unknown module: '{module}'")


class CoreModuleCannotBeDisabledError(DomainError):
    """Raised when a core module is listed as disabled (APRAS-39 §6.3).

    ``tenants``, ``users`` and ``roles`` are identity, membership and the
    authorization vocabulary itself: disabling any of them would make the
    tenant unadministrable from inside and would strip the very permissions
    an operator needs to turn it back on.
    """

    def __init__(self, modules: list[str]) -> None:
        super().__init__(
            "Core modules cannot be disabled: " + ", ".join(sorted(modules))
        )


class CrossTenantWriteError(DomainError):
    """Raised when a flush would persist a row belonging to another tenant.

    The write stamp (``app/core/tenant_context.py``) overwrites ``tenant_id``
    on every *new* scoped instance, so this can only fire for an already
    persistent instance of a foreign tenant that was mutated — a state a
    request session can never reach through the ambient read filter.
    """

    def __init__(self, model_name: str) -> None:
        super().__init__(
            f"Cannot write a {model_name} belonging to another tenant"
        )


class TenantScopeNotResolvedError(RuntimeError):
    """Raised when a request-scoped session queries a tenant-scoped model
    before its acting tenant has been resolved.

    Deliberately **not** a :class:`DomainError`: this is a programming error
    (a route that was never classified as tenant-scoped or global), so it
    must surface as a 500 rather than as a tidy 4xx. The static route test
    ``tests/test_tenant_route_scope.py`` catches the same mistake in CI,
    before it can ever run.
    """

    def __init__(self, model_name: str) -> None:
        super().__init__(
            f"Tenant scope was not resolved before querying {model_name}"
        )
