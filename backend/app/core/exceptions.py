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






