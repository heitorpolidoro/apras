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


