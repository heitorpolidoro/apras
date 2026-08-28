"""Pydantic schemas for Feedback data transfer objects."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import FeedbackCategory, FeedbackStatus


class FeedbackCreate(BaseModel):
    """Schema for creating a new feedback submission."""

    category: FeedbackCategory
    message: str = Field(min_length=1)
    is_anonymous: bool = False


class FeedbackRespond(BaseModel):
    """Schema for the board's response to a feedback submission."""

    board_response: str = Field(min_length=1)


class FeedbackRead(BaseModel):
    """Schema for reading feedback details."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    reporter_user_id: UUID | None = None
    reporter_name: str | None = None
    is_anonymous: bool
    category: FeedbackCategory
    message: str
    status: FeedbackStatus
    board_response: str | None = None
    responded_by_id: UUID | None = None
    responded_by_name: str | None = None
    responded_at: datetime | None = None
    response_seen_by_reporter: bool
    created_at: datetime


class PaginatedFeedbackRead(BaseModel):
    """Schema for paginated feedback listings."""

    items: list[FeedbackRead]
    total: int
    skip: int
    limit: int
