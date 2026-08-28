from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from app.api.deps import get_current_user
from app.db import get_session
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.document import (
    AssociationDocumentCreate,
    AssociationDocumentRead,
    AssociationDocumentVersionCreate,
    DocumentFolderCreate,
    DocumentFolderRead,
    DocumentFolderTreeRead,
    DocumentFolderUpdate,
    PaginatedDocumentRead,
)
from app.services import document_service

router = APIRouter()


def _assert_not_porteiro(current_user: User) -> None:
    """Raise 403 if the caller is PORTEIRO (gate-only role, no access here)."""
    if current_user.role == UserRole.PORTEIRO:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough privileges",
        )


@router.get("/folders", response_model=list[DocumentFolderTreeRead])
def list_folder_tree(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[DocumentFolderTreeRead]:
    _assert_not_porteiro(current_user)
    return document_service.get_folder_tree(session, current_user)


@router.post(
    "/folders", response_model=DocumentFolderRead, status_code=status.HTTP_201_CREATED
)
def create_folder(
    folder_in: DocumentFolderCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> DocumentFolderRead:
    _assert_not_porteiro(current_user)
    return document_service.create_folder(session, current_user, folder_in)


@router.put("/folders/{id}", response_model=DocumentFolderRead)
def update_folder(
    id: UUID,
    folder_in: DocumentFolderUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> DocumentFolderRead:
    _assert_not_porteiro(current_user)
    return document_service.update_folder(session, current_user, id, folder_in)


@router.delete("/folders/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_folder(
    id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    _assert_not_porteiro(current_user)
    document_service.delete_folder(session, current_user, id)


@router.get("", response_model=PaginatedDocumentRead)
def list_documents(
    folder_id: UUID | None = None,
    tag: str | None = None,
    year: int | None = None,
    month: int | None = None,
    search: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> PaginatedDocumentRead:
    _assert_not_porteiro(current_user)
    return document_service.get_documents(
        session=session,
        user=current_user,
        folder_id=folder_id,
        tag=tag,
        year=year,
        month=month,
        search=search,
        skip=skip,
        limit=limit,
    )


@router.post(
    "", response_model=AssociationDocumentRead, status_code=status.HTTP_201_CREATED
)
def create_document(
    doc_in: AssociationDocumentCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> AssociationDocumentRead:
    _assert_not_porteiro(current_user)
    return document_service.create_document(session, current_user, doc_in)


@router.post(
    "/{id}/versions",
    response_model=AssociationDocumentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_document_version(
    id: UUID,
    version_in: AssociationDocumentVersionCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> AssociationDocumentRead:
    _assert_not_porteiro(current_user)
    return document_service.create_document_version(session, current_user, id, version_in)


@router.post("/{id}/download")
def download_document(
    id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    _assert_not_porteiro(current_user)
    file_url = document_service.log_download(session, current_user, id)
    return {"file_url": file_url}


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> None:
    _assert_not_porteiro(current_user)
    document_service.delete_document(session, current_user, id)
