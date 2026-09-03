import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlmodel import Field, Relationship, SQLModel
from app.models.tenant import tenant_id_field

if TYPE_CHECKING:
    from app.models.user import User


class DocumentFolder(SQLModel, table=True):
    __tablename__ = "document_folder"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # Tenant boundary (APRAS-41). Defaults to DEFAULT_TENANT_ID so ORM
    # inserts that omit it keep working; APRAS-42 replaces this with a
    # request-scoped acting tenant.
    tenant_id: uuid.UUID = tenant_id_field()
    name: str = Field(nullable=False, index=True)
    description: str | None = Field(default=None, nullable=True)
    parent_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="document_folder.id",
        ondelete="CASCADE",
        nullable=True,
        index=True,
    )
    # A JSON list of **role ids** (IAM F5, APRAS-49 §6). It stored the retired
    # role enum's value strings until migration `0033` rewrote every row and
    # renamed the column; renaming rather than reusing the name is deliberate,
    # so a reader that was not updated fails loudly instead of silently
    # matching nothing.
    #
    # The Python-side default is `'[]'` and the column's `server_default` is
    # `'[]'` too: a `server_default` is a constant expression and role ids
    # differ per tenant and per install, so neither can name "the four legacy
    # roles" any more. `DocumentFolderCreate.allowed_role_ids` is therefore
    # **required** — a folder created without an explicit ACL would otherwise
    # be invisible to everyone, so the caller is made to say.
    allowed_role_ids_json: str = Field(default="[]", nullable=False)
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
    # Tenant boundary (APRAS-41). Defaults to DEFAULT_TENANT_ID so ORM
    # inserts that omit it keep working; APRAS-42 replaces this with a
    # request-scoped acting tenant.
    tenant_id: uuid.UUID = tenant_id_field()
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
