"""Database models for Visitor, VisitorAuthorization, and AccessLog."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

from .enums import AuthorizationStatus, AuthorizationType

if TYPE_CHECKING:
    from .lot import Lot
    from .user import User


class Visitor(SQLModel, table=True):
    __tablename__ = "visitor"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    full_name: str = Field(nullable=False, index=True)
    cpf: str | None = Field(default=None, index=True)
    rg: str | None = Field(default=None)
    phone: str | None = Field(default=None)
    company_name: str | None = Field(default=None, index=True)
    vehicle_plate: str | None = Field(default=None, index=True)
    vehicle_model: str | None = Field(default=None)
    notes: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    # Relationships
    authorizations: list["VisitorAuthorization"] = Relationship(back_populates="visitor")
    access_logs: list["AccessLog"] = Relationship(back_populates="visitor")


class VisitorAuthorization(SQLModel, table=True):
    __tablename__ = "visitor_authorization"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    visitor_id: UUID = Field(
        foreign_key="visitor.id", ondelete="CASCADE", nullable=False, index=True
    )
    lot_id: UUID = Field(
        foreign_key="lot.id", ondelete="CASCADE", nullable=False, index=True
    )
    authorizer_user_id: UUID = Field(
        foreign_key="user.id", ondelete="CASCADE", nullable=False, index=True
    )
    auth_type: AuthorizationType = Field(default=AuthorizationType.SINGLE, nullable=False)
    allowed_days_json: str = Field(
        default='["MON","TUE","WED","THU","FRI","SAT","SUN"]', nullable=False
    )
    allowed_shifts_json: str = Field(
        default='["MORNING","AFTERNOON","NIGHT","FULL_DAY"]', nullable=False
    )
    valid_from: datetime | None = Field(default=None)
    valid_until: datetime | None = Field(default=None)
    status: AuthorizationStatus = Field(
        default=AuthorizationStatus.ACTIVE, nullable=False, index=True
    )
    notes: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    # Relationships
    visitor: Optional["Visitor"] = Relationship(back_populates="authorizations")
    lot: Optional["Lot"] = Relationship()
    authorizer: Optional["User"] = Relationship()
    access_logs: list["AccessLog"] = Relationship(back_populates="authorization")


class AccessLog(SQLModel, table=True):
    __tablename__ = "access_log"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    authorization_id: UUID | None = Field(
        default=None, foreign_key="visitor_authorization.id", ondelete="SET NULL", nullable=True, index=True
    )
    visitor_id: UUID = Field(
        foreign_key="visitor.id", ondelete="CASCADE", nullable=False, index=True
    )
    lot_id: UUID = Field(
        foreign_key="lot.id", ondelete="CASCADE", nullable=False, index=True
    )
    entry_time: datetime = Field(default_factory=datetime.utcnow, nullable=False, index=True)
    exit_time: datetime | None = Field(default=None, index=True)
    gatekeeper_user_id: UUID | None = Field(
        default=None, foreign_key="user.id", nullable=True, index=True
    )
    entry_notes: str | None = Field(default=None)
    exit_notes: str | None = Field(default=None)

    # Relationships
    authorization: Optional["VisitorAuthorization"] = Relationship(back_populates="access_logs")
    visitor: Optional["Visitor"] = Relationship(back_populates="access_logs")
    lot: Optional["Lot"] = Relationship()
    gatekeeper: Optional["User"] = Relationship()
