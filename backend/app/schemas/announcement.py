"""Pydantic schemas for Announcement Feed data transfer objects."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AnnouncementMediaType


class AnnouncementCreate(BaseModel):
    """Schema for creating a new announcement."""

    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)


class AnnouncementUpdate(BaseModel):
    """Schema for updating an existing announcement."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    content: str | None = Field(default=None, min_length=1)


class AnnouncementMediaRead(BaseModel):
    """Schema for reading an announcement media attachment."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    announcement_id: UUID
    media_type: AnnouncementMediaType
    url: str
    mime_type: str
    file_size_bytes: int
    order_index: int
    created_at: datetime


class AnnouncementCommentCreate(BaseModel):
    """Schema for creating a comment on an announcement."""

    content: str = Field(min_length=1)


class AnnouncementCommentRead(BaseModel):
    """Schema for reading a comment on an announcement."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    announcement_id: UUID
    user_id: UUID
    author_name: str | None = None
    content: str
    created_at: datetime


class AnnouncementReadReceiptRead(BaseModel):
    """Schema for reading a read receipt entry."""

    user_id: UUID
    user_name: str | None = None
    read_at: datetime


class MarkReadResponse(BaseModel):
    """Schema for the response of marking an announcement as read."""

    read_at: datetime


class AnnouncementRead(BaseModel):
    """Schema for reading an announcement feed item."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    content: str
    author_id: UUID
    author_name: str | None = None
    media: list[AnnouncementMediaRead] = []
    comment_count: int = 0
    is_read: bool = False
    created_at: datetime
    updated_at: datetime


class AnnouncementDetailRead(AnnouncementRead):
    """Schema for reading a single announcement with its comments."""

    comments: list[AnnouncementCommentRead] = []


class PaginatedAnnouncementRead(BaseModel):
    """Schema for a paginated list of announcements."""

    items: list[AnnouncementRead]
    total: int
    skip: int
    limit: int
