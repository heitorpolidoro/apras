import json
from datetime import datetime
from uuid import UUID

from sqlmodel import Session, func, select

from app.api.deps import get_effective_role_ids, has_permission
from app.core import tenant_context
from app.core.exceptions import (
    DocumentFolderNotFoundError,
    DocumentNotFoundError,
    FolderAccessDeniedError,
    ForbiddenError,
    InvalidFolderHierarchyError,
    UnknownRoleIdsError,
)
from app.models.document import AssociationDocument, DocumentDownloadLog, DocumentFolder
from app.models.role import Role
from app.models.tenant import DEFAULT_TENANT_ID
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


def _check_admin_or_director(user: User, session: Session, permission: str) -> None:
    if not has_permission(user, session, permission):
        raise ForbiddenError("Not enough privileges")


def _assert_role_ids_resolve(session: Session, role_ids: list[str]) -> None:
    """Refuse an ACL naming ids that are not roles of the acting tenant.

    The sibling of `endpoints/users.py::_assign_roles`' own check, and made
    necessary by the same change: since IAM F5 (APRAS-49 §6) the ACL holds
    role **ids**, so a wrong entry no longer looks wrong. A name typo used
    to be visible in the stored JSON; a mistyped, stale or foreign uuid is
    not, and it produces a folder that is simply invisible to everyone --
    the exact outcome the required-field decision in `DocumentFolderCreate`
    already exists to prevent.

    Two shapes of "not a role of this tenant" are refused together:

    * a string that is not a uuid at all -- which includes `'ADMINISTRATOR'`
      and the five other legacy `UserRole` values, i.e. what an un-migrated
      client still sends;
    * a uuid that resolves to no role, or to a role of another tenant. The
      tenant narrowing is explicit because the id arrives in a request body
      rather than through a relationship, and the ambient filter covers
      neither (APRAS-42 §4.2).

    An empty list is legal and deliberately so: it means "staff only", the
    `documents:folder_create` bypass still reaches the folder, and the
    required-field rule already forced the author to say it out loud.
    """
    if not role_ids:
        return

    parsed: dict[UUID, str] = {}
    unresolved: set[str] = set()
    for raw in role_ids:
        try:
            parsed[UUID(str(raw))] = str(raw)
        except (ValueError, AttributeError, TypeError):
            unresolved.add(str(raw))

    if parsed:
        tenant_id = tenant_context.acting_tenant_id(session) or DEFAULT_TENANT_ID
        found = session.exec(
            select(Role.id).where(
                Role.id.in_(parsed.keys()), Role.tenant_id == tenant_id
            )
        ).all()
        unresolved |= {
            original
            for role_id, original in parsed.items()
            if role_id not in set(found)
        }

    if unresolved:
        raise UnknownRoleIdsError(unresolved)


def get_accessible_folder_ids(session: Session, user: User) -> set[UUID]:
    """Folder ids `user` may see: the staff bypass, else the per-folder ACL.

    IAM F5 (APRAS-49 §6): the ACL is a list of **role ids** and is
    intersected with the caller's own roles, replacing the `user.role.value`
    string match the enum made possible. The staff bypass is verbatim.
    """
    folders = session.exec(select(DocumentFolder)).all()
    # The all-folders staff bypass. `documents:folder_create` is the module's
    # authoring permission; the per-folder ACL below is the object dimension.
    if has_permission(user, session, "documents:folder_create"):
        return {f.id for f in folders}

    my_role_ids = {str(role_id) for role_id in get_effective_role_ids(user, session)}
    accessible_ids: set[UUID] = set()

    for folder in folders:
        try:
            allowed = json.loads(folder.allowed_role_ids_json)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(allowed, list) and {str(item) for item in allowed} & my_role_ids:
            accessible_ids.add(folder.id)

    return accessible_ids


def get_folder_tree(session: Session, user: User) -> list[DocumentFolderTreeRead]:
    accessible_ids = get_accessible_folder_ids(session, user)
    if not accessible_ids:
        return []

    folders = session.exec(
        select(DocumentFolder).where(DocumentFolder.id.in_(accessible_ids))
    ).all()

    # Document counts per folder
    doc_counts_query = (
        select(AssociationDocument.folder_id, func.count(AssociationDocument.id))
        .where(AssociationDocument.folder_id.in_(accessible_ids))
        .group_by(AssociationDocument.folder_id)
    )
    doc_counts = dict(session.exec(doc_counts_query).all())

    folder_map: dict[UUID, DocumentFolderTreeRead] = {}
    for f in folders:
        try:
            raw = f.allowed_role_ids_json
            roles = json.loads(raw) if raw else []
        except (json.JSONDecodeError, TypeError):
            roles = []

        folder_map[f.id] = DocumentFolderTreeRead(
            id=f.id,
            name=f.name,
            description=f.description,
            parent_id=f.parent_id,
            allowed_role_ids=roles,
            document_count=doc_counts.get(f.id, 0),
            created_at=f.created_at,
            updated_at=f.updated_at,
            children=[],
        )

    root_folders: list[DocumentFolderTreeRead] = []
    for f_id, folder_tree_node in folder_map.items():
        p_id = folder_tree_node.parent_id
        if p_id and p_id in folder_map:
            folder_map[p_id].children.append(folder_tree_node)
        else:
            root_folders.append(folder_tree_node)

    return root_folders


def create_folder(
    session: Session, user: User, folder_in: DocumentFolderCreate
) -> DocumentFolderRead:
    _check_admin_or_director(user, session, "documents:folder_create")
    _assert_role_ids_resolve(session, folder_in.allowed_role_ids)

    if folder_in.parent_id:
        parent = session.get(DocumentFolder, folder_in.parent_id)
        if not parent:
            raise DocumentFolderNotFoundError(folder_in.parent_id)

    role_ids_json = json.dumps(folder_in.allowed_role_ids)
    folder = DocumentFolder(
        name=folder_in.name,
        description=folder_in.description,
        parent_id=folder_in.parent_id,
        allowed_role_ids_json=role_ids_json,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(folder)
    session.commit()
    session.refresh(folder)

    return DocumentFolderRead(
        id=folder.id,
        name=folder.name,
        description=folder.description,
        parent_id=folder.parent_id,
        allowed_role_ids=folder_in.allowed_role_ids,
        document_count=0,
        created_at=folder.created_at,
        updated_at=folder.updated_at,
    )


def update_folder(
    session: Session, user: User, folder_id: UUID, folder_in: DocumentFolderUpdate
) -> DocumentFolderRead:
    _check_admin_or_director(user, session, "documents:folder_update")

    folder = session.get(DocumentFolder, folder_id)
    if not folder:
        raise DocumentFolderNotFoundError(folder_id)

    if folder_in.parent_id is not None:
        if folder_in.parent_id == folder_id:
            raise InvalidFolderHierarchyError("Folder cannot be its own parent")
        parent = session.get(DocumentFolder, folder_in.parent_id)
        if not parent:
            raise DocumentFolderNotFoundError(folder_in.parent_id)

        # Check for circular hierarchy
        curr_id: UUID | None = folder_in.parent_id
        while curr_id:
            if curr_id == folder_id:
                raise InvalidFolderHierarchyError("Cannot set descendant as parent folder")
            curr_obj = session.get(DocumentFolder, curr_id)
            curr_id = curr_obj.parent_id if curr_obj else None

        folder.parent_id = folder_in.parent_id

    if folder_in.name is not None:
        folder.name = folder_in.name
    if folder_in.description is not None:
        folder.description = folder_in.description
    if folder_in.allowed_role_ids is not None:
        _assert_role_ids_resolve(session, folder_in.allowed_role_ids)
        folder.allowed_role_ids_json = json.dumps(folder_in.allowed_role_ids)

    folder.updated_at = datetime.utcnow()
    session.add(folder)
    session.commit()
    session.refresh(folder)

    try:
        raw = folder.allowed_role_ids_json
        roles = json.loads(raw) if raw else []
    except (json.JSONDecodeError, TypeError):
        roles = []

    doc_count = session.exec(
        select(func.count(AssociationDocument.id)).where(
            AssociationDocument.folder_id == folder.id
        )
    ).one()

    return DocumentFolderRead(
        id=folder.id,
        name=folder.name,
        description=folder.description,
        parent_id=folder.parent_id,
        allowed_role_ids=roles,
        document_count=doc_count,
        created_at=folder.created_at,
        updated_at=folder.updated_at,
    )


def delete_folder(session: Session, user: User, folder_id: UUID) -> None:
    _check_admin_or_director(user, session, "documents:folder_delete")

    folder = session.get(DocumentFolder, folder_id)
    if not folder:
        raise DocumentFolderNotFoundError(folder_id)

    session.delete(folder)
    session.commit()


def _format_doc_read(session: Session, doc: AssociationDocument) -> AssociationDocumentRead:
    tags = json.loads(doc.tags_json) if doc.tags_json else []
    folder = session.get(DocumentFolder, doc.folder_id)
    uploader = session.get(User, doc.uploaded_by_id)

    return AssociationDocumentRead(
        id=doc.id,
        folder_id=doc.folder_id,
        folder_name=folder.name if folder else None,
        title=doc.title,
        description=doc.description,
        file_url=doc.file_url,
        file_size_bytes=doc.file_size_bytes,
        mime_type=doc.mime_type,
        version_number=doc.version_number,
        previous_version_id=doc.previous_version_id,
        publication_year=doc.publication_year,
        publication_month=doc.publication_month,
        tags=tags,
        uploaded_by_id=doc.uploaded_by_id,
        uploader_name=uploader.full_name if uploader else None,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


def get_documents(
    session: Session,
    user: User,
    folder_id: UUID | None = None,
    tag: str | None = None,
    year: int | None = None,
    month: int | None = None,
    search: str | None = None,
    skip: int = 0,
    limit: int = 50,
) -> PaginatedDocumentRead:
    accessible_ids = get_accessible_folder_ids(session, user)

    if folder_id:
        folder = session.get(DocumentFolder, folder_id)
        if not folder:
            raise DocumentFolderNotFoundError(folder_id)
        if folder_id not in accessible_ids:
            raise FolderAccessDeniedError("Access to document folder forbidden")
        target_folder_ids = [folder_id]
    else:
        target_folder_ids = list(accessible_ids)

    if not target_folder_ids:
        return PaginatedDocumentRead(items=[], total=0, skip=skip, limit=limit)

    query = select(AssociationDocument).where(
        AssociationDocument.folder_id.in_(target_folder_ids)
    )

    if tag:
        query = query.where(AssociationDocument.tags_json.ilike(f"%{tag}%"))
    if year:
        query = query.where(AssociationDocument.publication_year == year)
    if month:
        query = query.where(AssociationDocument.publication_month == month)
    if search:
        pattern = f"%{search}%"
        query = query.where(
            (AssociationDocument.title.ilike(pattern))
            | (AssociationDocument.description.ilike(pattern))
        )

    # Count total
    total_query = select(func.count()).select_from(query.subquery())
    total = session.exec(total_query).one()

    # Pagination & sorting
    docs = session.exec(
        query.order_by(AssociationDocument.created_at.desc())
        .offset(skip)
        .limit(limit)
    ).all()

    items = [_format_doc_read(session, d) for d in docs]
    return PaginatedDocumentRead(items=items, total=total, skip=skip, limit=limit)


def create_document(
    session: Session, user: User, doc_in: AssociationDocumentCreate
) -> AssociationDocumentRead:
    _check_admin_or_director(user, session, "documents:create")

    folder = session.get(DocumentFolder, doc_in.folder_id)
    if not folder:
        raise DocumentFolderNotFoundError(doc_in.folder_id)

    tags_json = json.dumps(doc_in.tags) if doc_in.tags else None
    doc = AssociationDocument(
        folder_id=doc_in.folder_id,
        title=doc_in.title,
        description=doc_in.description,
        file_url=doc_in.file_url,
        file_size_bytes=doc_in.file_size_bytes,
        mime_type=doc_in.mime_type,
        version_number=1,
        previous_version_id=None,
        publication_year=doc_in.publication_year,
        publication_month=doc_in.publication_month,
        tags_json=tags_json,
        uploaded_by_id=user.id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(doc)
    session.commit()
    session.refresh(doc)

    return _format_doc_read(session, doc)


def create_document_version(
    session: Session,
    user: User,
    doc_id: UUID,
    version_in: AssociationDocumentVersionCreate,
) -> AssociationDocumentRead:
    _check_admin_or_director(user, session, "documents:version_create")

    prev_doc = session.get(AssociationDocument, doc_id)
    if not prev_doc:
        raise DocumentNotFoundError(doc_id)

    title = version_in.title if version_in.title else prev_doc.title
    description = (
        version_in.description if version_in.description is not None else prev_doc.description
    )
    tags = (
        version_in.tags
        if version_in.tags is not None
        else (json.loads(prev_doc.tags_json) if prev_doc.tags_json else None)
    )
    tags_json = json.dumps(tags) if tags else None

    new_doc = AssociationDocument(
        folder_id=prev_doc.folder_id,
        title=title,
        description=description,
        file_url=version_in.file_url,
        file_size_bytes=version_in.file_size_bytes,
        mime_type=version_in.mime_type,
        version_number=prev_doc.version_number + 1,
        previous_version_id=prev_doc.id,
        publication_year=prev_doc.publication_year,
        publication_month=prev_doc.publication_month,
        tags_json=tags_json,
        uploaded_by_id=user.id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(new_doc)
    session.commit()
    session.refresh(new_doc)

    return _format_doc_read(session, new_doc)


def log_download(session: Session, user: User, doc_id: UUID) -> str:
    doc = session.get(AssociationDocument, doc_id)
    if not doc:
        raise DocumentNotFoundError(doc_id)

    accessible_ids = get_accessible_folder_ids(session, user)
    if doc.folder_id not in accessible_ids:
        raise FolderAccessDeniedError("Access to document folder forbidden")

    log_entry = DocumentDownloadLog(
        document_id=doc.id,
        user_id=user.id,
        downloaded_at=datetime.utcnow(),
    )
    session.add(log_entry)
    session.commit()

    return doc.file_url


def delete_document(session: Session, user: User, doc_id: UUID) -> None:
    _check_admin_or_director(user, session, "documents:delete")

    doc = session.get(AssociationDocument, doc_id)
    if not doc:
        raise DocumentNotFoundError(doc_id)

    session.delete(doc)
    session.commit()
