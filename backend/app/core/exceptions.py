"""Domain exceptions."""

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






