from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class DocumentFolderCreate(BaseModel):
    name: str = Field(..., min_length=1)
    description: str | None = None
    parent_id: UUID | None = None
    allowed_roles: list[str] = Field(
        default=["ADMINISTRATOR", "DIRECTOR", "MANAGER", "RESIDENT"]
    )


class DocumentFolderUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    parent_id: UUID | None = None
    allowed_roles: list[str] | None = None


class DocumentFolderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None = None
    parent_id: UUID | None = None
    allowed_roles: list[str] = []
    document_count: int = 0
    created_at: datetime
    updated_at: datetime


class DocumentFolderTreeRead(DocumentFolderRead):
    children: list["DocumentFolderTreeRead"] = []


class AssociationDocumentCreate(BaseModel):
    folder_id: UUID
    title: str = Field(..., min_length=1)
    description: str | None = None
    file_url: str = Field(..., min_length=1)
    file_size_bytes: int = Field(..., ge=0)
    mime_type: str = "application/pdf"
    publication_year: int | None = None
    publication_month: int | None = None
    tags: list[str] | None = None


class AssociationDocumentVersionCreate(BaseModel):
    title: str | None = None
    description: str | None = None
    file_url: str = Field(..., min_length=1)
    file_size_bytes: int = Field(..., ge=0)
    mime_type: str = "application/pdf"
    tags: list[str] | None = None


class AssociationDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    folder_id: UUID
    folder_name: str | None = None
    title: str
    description: str | None = None
    file_url: str
    file_size_bytes: int
    mime_type: str
    version_number: int
    previous_version_id: UUID | None = None
    publication_year: int | None = None
    publication_month: int | None = None
    tags: list[str] = []
    uploaded_by_id: UUID
    uploader_name: str | None = None
    created_at: datetime
    updated_at: datetime


class DocumentDownloadLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    user_id: UUID
    user_name: str | None = None
    downloaded_at: datetime


class PaginatedDocumentRead(BaseModel):
    items: list[AssociationDocumentRead]
    total: int
    skip: int
    limit: int
