import uuid
import pytest
from app.core.security import create_access_token, get_password_hash
from app.models.enums import UserRole
from app.models.user import User
from sqlmodel import Session


@pytest.fixture
def resident_user(session: Session):
    user = User(
        id=uuid.uuid4(),
        email="resident@test.com",
        full_name="Resident User",
        hashed_password=get_password_hash("password"),
        role=UserRole.RESIDENT,
        cpf="12345678909",
    )
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def manager_user(session: Session):
    user = User(
        id=uuid.uuid4(),
        email="manager@test.com",
        full_name="Manager User",
        hashed_password=get_password_hash("password"),
        role=UserRole.MANAGER,
        cpf="98765432100",
    )
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def guest_user(session: Session):
    user = User(
        id=uuid.uuid4(),
        email="guest@test.com",
        full_name="Guest User",
        hashed_password=get_password_hash("password"),
        role=UserRole.GUEST,
        cpf="11122233344",
    )
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def admin_headers(admin_user: User):
    token = create_access_token(subject=admin_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def resident_headers(resident_user: User):
    token = create_access_token(subject=resident_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def manager_headers(manager_user: User):
    token = create_access_token(subject=manager_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def guest_headers(guest_user: User):
    token = create_access_token(subject=guest_user.id)
    return {"Authorization": f"Bearer {token}"}


def test_folder_visibility_filtering(client, admin_headers, resident_headers, manager_headers, guest_headers):
    # Admin creates 2 folders: one for Manager only, one for Resident & Manager
    res_m = client.post(
        "/api/v1/documents/folders",
        json={
            "name": "Gestão Interna",
            "allowed_roles": ["ADMINISTRATOR", "DIRECTOR", "MANAGER"],
        },
        headers=admin_headers,
    )
    assert res_m.status_code == 201
    manager_folder_id = res_m.json()["id"]

    res_r = client.post(
        "/api/v1/documents/folders",
        json={
            "name": "Transparência Geral",
            "allowed_roles": ["ADMINISTRATOR", "DIRECTOR", "MANAGER", "RESIDENT"],
        },
        headers=admin_headers,
    )
    assert res_r.status_code == 201
    resident_folder_id = res_r.json()["id"]

    # Resident lists folders: should only see Transparência Geral
    res_res_tree = client.get("/api/v1/documents/folders", headers=resident_headers)
    assert res_res_tree.status_code == 200
    res_folders = res_res_tree.json()
    folder_ids = [f["id"] for f in res_folders]
    assert resident_folder_id in folder_ids
    assert manager_folder_id not in folder_ids

    # Manager lists folders: should see both
    res_man_tree = client.get("/api/v1/documents/folders", headers=manager_headers)
    assert res_man_tree.status_code == 200
    man_folder_ids = [f["id"] for f in res_man_tree.json()]
    assert resident_folder_id in man_folder_ids
    assert manager_folder_id in man_folder_ids

    # Guest lists folders: should see empty tree
    res_gst_tree = client.get("/api/v1/documents/folders", headers=guest_headers)
    assert res_gst_tree.status_code == 200
    assert len(res_gst_tree.json()) == 0

    # Guest queries documents: should get empty paginated list
    res_gst_docs = client.get("/api/v1/documents", headers=guest_headers)
    assert res_gst_docs.status_code == 200
    assert res_gst_docs.json()["total"] == 0


def test_non_admin_cannot_mutate_folders_or_documents(
    client, admin_headers, resident_headers
):
    # Create folder as admin
    res_f = client.post(
        "/api/v1/documents/folders",
        json={"name": "Folder", "allowed_roles": ["RESIDENT"]},
        headers=admin_headers,
    )
    folder_id = res_f.json()["id"]

    # Resident tries to create subfolder
    res_sub = client.post(
        "/api/v1/documents/folders",
        json={"name": "Sub", "parent_id": folder_id},
        headers=resident_headers,
    )
    assert res_sub.status_code == 403

    # Resident tries to update folder
    res_up = client.put(
        f"/api/v1/documents/folders/{folder_id}",
        json={"name": "Changed"},
        headers=resident_headers,
    )
    assert res_up.status_code == 403

    # Resident tries to delete folder
    res_del = client.delete(f"/api/v1/documents/folders/{folder_id}", headers=resident_headers)
    assert res_del.status_code == 403

    # Resident tries to upload document
    res_doc = client.post(
        "/api/v1/documents",
        json={
            "folder_id": folder_id,
            "title": "Doc",
            "file_url": "https://example.com/doc.pdf",
            "file_size_bytes": 100,
        },
        headers=resident_headers,
    )
    assert res_doc.status_code == 403


def test_document_access_denied_for_forbidden_folder(
    client, admin_headers, resident_headers
):
    # Admin creates folder restricted to MANAGER
    res_f = client.post(
        "/api/v1/documents/folders",
        json={
            "name": "Manager Secret",
            "allowed_roles": ["ADMINISTRATOR", "DIRECTOR", "MANAGER"],
        },
        headers=admin_headers,
    )
    folder_id = res_f.json()["id"]

    # Admin uploads document
    res_doc = client.post(
        "/api/v1/documents",
        json={
            "folder_id": folder_id,
            "title": "Secret Strategy",
            "file_url": "https://example.com/secret.pdf",
            "file_size_bytes": 500,
        },
        headers=admin_headers,
    )
    doc_id = res_doc.json()["id"]

    # Resident tries to version document
    res_ver = client.post(
        f"/api/v1/documents/{doc_id}/versions",
        json={
            "file_url": "https://example.com/hack.pdf",
            "file_size_bytes": 100,
        },
        headers=resident_headers,
    )
    assert res_ver.status_code == 403

    # Resident tries to delete document
    res_del = client.delete(f"/api/v1/documents/{doc_id}", headers=resident_headers)
    assert res_del.status_code == 403

    # Resident tries to list docs in that folder directly
    res_list = client.get(f"/api/v1/documents?folder_id={folder_id}", headers=resident_headers)
    assert res_list.status_code == 403

    # Resident tries to download document
    res_dl = client.post(f"/api/v1/documents/{doc_id}/download", headers=resident_headers)
    assert res_dl.status_code == 403
