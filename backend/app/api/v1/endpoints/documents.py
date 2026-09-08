from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from app.api.deps import get_current_user, has_permission
from app.db import get_session
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


def _assert_not_porteiro(current_user: User, session: Session, permission: str) -> None:
    """Raise 403 unless the caller holds this route's own permission.

    Named for the rule it used to spell (PORTEIRO is a gate-only role and
    never reaches this module); each call site now passes the permission of
    *its* route, so a helper shared by a dozen routes does not collapse a
    dozen permissions into one.
    """
    if not has_permission(current_user, session, permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough privileges",
        )


@router.get("/folders")
def list_folder_tree(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[DocumentFolderTreeRead]:
    _assert_not_porteiro(current_user, session, "documents:folder_read")
    return document_service.get_folder_tree(session, current_user)


@router.post("/folders", status_code=status.HTTP_201_CREATED)
def create_folder(
    folder_in: DocumentFolderCreate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> DocumentFolderRead:
    _assert_not_porteiro(current_user, session, "documents:folder_create")
    return document_service.create_folder(session, current_user, folder_in)


@router.put("/folders/{id}")
def update_folder(
    id: UUID,
    folder_in: DocumentFolderUpdate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> DocumentFolderRead:
    _assert_not_porteiro(current_user, session, "documents:folder_update")
    return document_service.update_folder(session, current_user, id, folder_in)


@router.delete("/folders/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_folder(
    id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    _assert_not_porteiro(current_user, session, "documents:folder_delete")
    document_service.delete_folder(session, current_user, id)


@router.get("")
def list_documents(
    # The two dependencies lead because `Annotated[..., Depends(...)]` carries
    # no default, and a parameter without one may not follow parameters that
    # have one. Neither is an OpenAPI parameter, so the query string's own
    # order -- and the generated document -- is unaffected.
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    folder_id: UUID | None = None,
    tag: str | None = None,
    year: int | None = None,
    month: int | None = None,
    search: str | None = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> PaginatedDocumentRead:
    _assert_not_porteiro(current_user, session, "documents:read")
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


@router.post("", status_code=status.HTTP_201_CREATED)
def create_document(
    doc_in: AssociationDocumentCreate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AssociationDocumentRead:
    _assert_not_porteiro(current_user, session, "documents:create")
    return document_service.create_document(session, current_user, doc_in)


@router.post(
    "/{id}/versions",
    status_code=status.HTTP_201_CREATED,
)
def create_document_version(
    id: UUID,
    version_in: AssociationDocumentVersionCreate,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AssociationDocumentRead:
    _assert_not_porteiro(current_user, session, "documents:version_create")
    return document_service.create_document_version(
        session, current_user, id, version_in
    )


@router.post("/{id}/download")
def download_document(
    id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, str]:
    _assert_not_porteiro(current_user, session, "documents:download")
    file_url = document_service.log_download(session, current_user, id)
    return {"file_url": file_url}


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    _assert_not_porteiro(current_user, session, "documents:delete")
    document_service.delete_document(session, current_user, id)
