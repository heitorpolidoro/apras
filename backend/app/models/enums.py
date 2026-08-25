"""Enumerations for the domain models."""

from enum import StrEnum


class TaskStatus(StrEnum):
    """Enumeration for task status."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"
    CANCELED = "CANCELED"


class TaskPriority(StrEnum):
    """Enumeration for task priority."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class UserRole(StrEnum):
    """Enumeration for user roles."""

    ADMINISTRATOR = "ADMINISTRATOR"
    DIRECTOR = "DIRECTOR"
    MANAGER = "MANAGER"
    GUEST = "GUEST"
    RESIDENT = "RESIDENT"


class LotStatus(StrEnum):
    """Enumeration for lot status."""

    VACANT = "VACANT"
    OCCUPIED = "OCCUPIED"
    UNDER_CONSTRUCTION = "UNDER_CONSTRUCTION"


class LotAssociationType(StrEnum):
    """Enumeration for user to lot association type."""

    PROPRIETARIO = "PROPRIETARIO"
    INQUILINO = "INQUILINO"
    RESPONSAVEL_FINANCEIRO = "RESPONSAVEL_FINANCEIRO"
    OUTRO = "OUTRO"


class ResidentRelationship(StrEnum):
    """Enumeration for resident relationship to lot owner/head."""

    TITULAR = "TITULAR"
    CONJUGE = "CONJUGE"
    FILHO_DEPENDENTE = "FILHO_DEPENDENTE"
    INQUILINO = "INQUILINO"
    PARENTE = "PARENTE"
    OUTRO = "OUTRO"


class AuthorizationType(StrEnum):
    """Enumeration for authorization type."""

    SINGLE = "SINGLE"
    PERMANENT = "PERMANENT"


class AuthorizationStatus(StrEnum):
    """Enumeration for authorization status."""

    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class DayOfWeek(StrEnum):
    """Enumeration for days of week."""

    MON = "MON"
    TUE = "TUE"
    WED = "WED"
    THU = "THU"
    FRI = "FRI"
    SAT = "SAT"
    SUN = "SUN"


class ShiftType(StrEnum):
    """Enumeration for shift types."""

    MORNING = "MORNING"
    AFTERNOON = "AFTERNOON"
    NIGHT = "NIGHT"
    FULL_DAY = "FULL_DAY"


class OccurrenceCategory(StrEnum):
    """Enumeration for occurrence categories."""

    NOISE = "NOISE"
    MAINTENANCE = "MAINTENANCE"
    SECURITY = "SECURITY"
    PARKING = "PARKING"
    RULES_VIOLATION = "RULES_VIOLATION"
    OTHER = "OTHER"


class OccurrenceStatus(StrEnum):
    """Enumeration for occurrence status workflow."""

    OPEN = "OPEN"
    UNDER_REVIEW = "UNDER_REVIEW"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    REJECTED = "REJECTED"


class OccurrencePriority(StrEnum):
    """Enumeration for occurrence priority levels."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"




