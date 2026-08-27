"""Database models for the Announcement Feed module."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint

from app.models.enums import AnnouncementMediaType

if TYPE_CHECKING:
    from app.models.user import User


class Announcement(SQLModel, table=True):
    """SQLModel table representing an HOA announcement/news post."""

    __tablename__ = "announcement"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    title: str = Field(nullable=False, index=True)
    content: str = Field(nullable=False)
    author_id: uuid.UUID = Field(foreign_key="user.id", nullable=False, index=True)
    is_deleted: bool = Field(default=False, nullable=False, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    author: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Announcement.author_id]"}
    )
    media: list["AnnouncementMedia"] = Relationship(
        back_populates="announcement",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    comments: list["AnnouncementComment"] = Relationship(
        back_populates="announcement",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    read_receipts: list["AnnouncementReadReceipt"] = Relationship(
        back_populates="announcement",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class AnnouncementMedia(SQLModel, table=True):
    """SQLModel table representing an image/PDF attachment on an announcement."""

    __tablename__ = "announcement_media"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    announcement_id: uuid.UUID = Field(
        foreign_key="announcement.id", ondelete="CASCADE", nullable=False, index=True
    )
    media_type: AnnouncementMediaType = Field(nullable=False)
    file_path: str = Field(nullable=False)
    url: str = Field(nullable=False)
    mime_type: str = Field(nullable=False)
    file_size_bytes: int = Field(nullable=False)
    order_index: int = Field(default=0, nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    announcement: Announcement = Relationship(back_populates="media")


class AnnouncementComment(SQLModel, table=True):
    """SQLModel table representing a comment on an announcement."""

    __tablename__ = "announcement_comment"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    announcement_id: uuid.UUID = Field(
        foreign_key="announcement.id", ondelete="CASCADE", nullable=False, index=True
    )
    user_id: uuid.UUID = Field(foreign_key="user.id", ondelete="CASCADE", nullable=False, index=True)
    content: str = Field(nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    announcement: Announcement = Relationship(back_populates="comments")
    user: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[AnnouncementComment.user_id]"}
    )


class AnnouncementReadReceipt(SQLModel, table=True):
    """SQLModel table recording that a user has read an announcement."""

    __tablename__ = "announcement_read_receipt"
    __table_args__ = (
        UniqueConstraint("announcement_id", "user_id", name="uq_announcement_read_receipt_user"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    announcement_id: uuid.UUID = Field(
        foreign_key="announcement.id", ondelete="CASCADE", nullable=False, index=True
    )
    user_id: uuid.UUID = Field(foreign_key="user.id", ondelete="CASCADE", nullable=False, index=True)
    read_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    announcement: Announcement = Relationship(back_populates="read_receipts")
    user: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[AnnouncementReadReceipt.user_id]"}
    )
