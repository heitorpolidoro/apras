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
