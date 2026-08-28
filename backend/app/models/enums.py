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


class EntityType(StrEnum):
    """Enumeration for photo asset target entity types."""

    RESIDENT = "RESIDENT"
    VISITOR = "VISITOR"
    EMPLOYEE = "EMPLOYEE"
    LOT = "LOT"
    ANNOUNCEMENT = "ANNOUNCEMENT"
    OCCURRENCE = "OCCURRENCE"


class StorageProvider(StrEnum):
    """Enumeration for photo storage backend providers."""

    LOCAL_DISK = "LOCAL_DISK"
    VERCEL_BLOB = "VERCEL_BLOB"
    AWS_S3 = "AWS_S3"
    CLOUDINARY = "CLOUDINARY"


class PhotoApprovalStatus(StrEnum):
    """Enumeration for photo asset approval workflow status."""

    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class AccessDeviceStatus(StrEnum):
    """Enumeration for facial-recognition access device status."""

    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    MAINTENANCE = "MAINTENANCE"


class FacialTemplateSyncStatus(StrEnum):
    """Enumeration for facial template sync status."""

    PENDING = "PENDING"
    SYNCED = "SYNCED"
    FAILED = "FAILED"


class ProjectStatus(StrEnum):
    """Enumeration for construction project lifecycle status."""

    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"


class MilestoneStatus(StrEnum):
    """Enumeration for project milestone status."""

    DONE = "DONE"
    IN_PROGRESS = "IN_PROGRESS"
    NEXT_STEPS = "NEXT_STEPS"


class AnnouncementMediaType(StrEnum):
    """Enumeration for announcement media attachment types."""

    IMAGE = "IMAGE"
    PDF = "PDF"


class TransactionType(StrEnum):
    """Enumeration for financial transaction / category direction."""

    INCOME = "INCOME"
    EXPENSE = "EXPENSE"


class MenuKey(StrEnum):
    """Enumeration for menus/features gated by UserType.allowed_menus."""

    TASKS = "tasks"
    CATEGORIES = "categories"


class FeedbackCategory(StrEnum):
    """Enumeration for feedback/suggestion/complaint categories."""

    CRITICISM = "CRITICISM"
    SUGGESTION = "SUGGESTION"
    COMPLIMENT = "COMPLIMENT"
    OTHER = "OTHER"


class FeedbackStatus(StrEnum):
    """Enumeration for feedback response status."""

    PENDING = "PENDING"
    ANSWERED = "ANSWERED"





