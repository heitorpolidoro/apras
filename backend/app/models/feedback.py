"""Feedback SQLModel entity definition."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

from app.models.enums import FeedbackCategory, FeedbackStatus

if TYPE_CHECKING:
    from app.models.user import User


class Feedback(SQLModel, table=True):
    """SQLModel representing a feedback/suggestion/complaint submission."""

    __tablename__ = "feedback"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    reporter_user_id: UUID | None = Field(
        default=None, foreign_key="user.id", ondelete="SET NULL", nullable=True, index=True
    )
    is_anonymous: bool = Field(default=False, nullable=False)
    category: FeedbackCategory = Field(nullable=False, index=True)
    message: str = Field(nullable=False)
    status: FeedbackStatus = Field(
        default=FeedbackStatus.PENDING, nullable=False, index=True
    )
    board_response: str | None = Field(default=None, nullable=True)
    responded_by_id: UUID | None = Field(
        default=None, foreign_key="user.id", ondelete="SET NULL", nullable=True
    )
    responded_at: datetime | None = Field(default=None, nullable=True)
    response_seen_by_reporter: bool = Field(default=False, nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    # Relationships
    reporter: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Feedback.reporter_user_id]"}
    )
    responded_by: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Feedback.responded_by_id]"}
    )
