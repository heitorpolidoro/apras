import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.user import User


class DocumentFolder(SQLModel, table=True):
    __tablename__ = "document_folder"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(nullable=False, index=True)
    description: str | None = Field(default=None, nullable=True)
    parent_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="document_folder.id",
        ondelete="CASCADE",
        nullable=True,
        index=True,
    )
    allowed_roles_json: str = Field(
        default='["ADMINISTRATOR", "DIRECTOR", "MANAGER", "RESIDENT"]',
        nullable=False,
    )
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    # Relationships
    parent_folder: Optional["DocumentFolder"] = Relationship(
        sa_relationship_kwargs={"remote_side": "DocumentFolder.id"}
    )
    subfolders: list["DocumentFolder"] = Relationship(
        back_populates="parent_folder",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    documents: list["AssociationDocument"] = Relationship(
        back_populates="folder",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class AssociationDocument(SQLModel, table=True):
    __tablename__ = "association_document"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    folder_id: uuid.UUID = Field(
        foreign_key="document_folder.id",
        ondelete="CASCADE",
        nullable=False,
        index=True,
    )
    title: str = Field(nullable=False, index=True)
    description: str | None = Field(default=None, nullable=True)
    file_url: str = Field(nullable=False)
    file_size_bytes: int = Field(nullable=False)
    mime_type: str = Field(default="application/pdf", nullable=False)
    version_number: int = Field(default=1, nullable=False)
    previous_version_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="association_document.id",
        ondelete="SET NULL",
        nullable=True,
        index=True,
    )
    publication_year: int | None = Field(default=None, nullable=True, index=True)
    publication_month: int | None = Field(default=None, nullable=True, index=True)
    tags_json: str | None = Field(default=None, nullable=True)
    uploaded_by_id: uuid.UUID = Field(
        foreign_key="user.id",
        nullable=False,
        index=True,
    )
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    # Relationships
    folder: DocumentFolder = Relationship(back_populates="documents")
    uploaded_by: "User" = Relationship()
    previous_version: Optional["AssociationDocument"] = Relationship(
        sa_relationship_kwargs={"remote_side": "AssociationDocument.id"}
    )
    download_logs: list["DocumentDownloadLog"] = Relationship(
        back_populates="document",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class DocumentDownloadLog(SQLModel, table=True):
    __tablename__ = "document_download_log"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    document_id: uuid.UUID = Field(
        foreign_key="association_document.id",
        ondelete="CASCADE",
        nullable=False,
        index=True,
    )
    user_id: uuid.UUID = Field(
        foreign_key="user.id",
        ondelete="CASCADE",
        nullable=False,
        index=True,
    )
    downloaded_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    # Relationships
    document: AssociationDocument = Relationship(back_populates="download_logs")
    user: "User" = Relationship()
