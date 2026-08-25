import json
import uuid
import pytest
from app.core.exceptions import (
    DocumentFolderNotFoundError,
    DocumentNotFoundError,
    FolderAccessDeniedError,
    ForbiddenError,
    InvalidFolderHierarchyError,
)
from app.core.security import create_access_token
from app.models.document import DocumentFolder
from app.models.enums import UserRole
from app.models.user import User


@pytest.fixture
def admin_headers(admin_user: User):
    token = create_access_token(subject=admin_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def director_headers(normal_user: User):
    token = create_access_token(subject=normal_user.id)
    return {"Authorization": f"Bearer {token}"}


def test_folder_crud_flow(client, admin_headers):
    # 1. Create root folder
    res = client.post(
        "/api/v1/documents/folders",
        json={
            "name": "Financeiro",
            "description": "Documentos financeiros",
            "allowed_roles": ["ADMINISTRATOR", "DIRECTOR", "MANAGER", "RESIDENT"],
        },
        headers=admin_headers,
    )
    assert res.status_code == 201
    root_folder = res.json()
    assert root_folder["name"] == "Financeiro"
    assert root_folder["parent_id"] is None
    assert root_folder["document_count"] == 0
    assert "ADMINISTRATOR" in root_folder["allowed_roles"]

    folder_id = root_folder["id"]

    # 2. Create subfolder
    res_sub = client.post(
        "/api/v1/documents/folders",
        json={
            "name": "Balancetes 2026",
            "description": "Balancetes do ano 2026",
            "parent_id": folder_id,
            "allowed_roles": ["ADMINISTRATOR", "DIRECTOR", "MANAGER"],
        },
        headers=admin_headers,
    )
    assert res_sub.status_code == 201
    subfolder = res_sub.json()
    assert subfolder["parent_id"] == folder_id

    # 3. Update folder name, parent_id and allowed_roles
    res_up = client.put(
        f"/api/v1/documents/folders/{subfolder['id']}",
        json={
            "name": "Balancetes 2026 Renovado",
            "description": "Documentos financeiros atualizados",
            "allowed_roles": ["ADMINISTRATOR", "DIRECTOR"],
        },
        headers=admin_headers,
    )
    assert res_up.status_code == 200
    assert res_up.json()["name"] == "Balancetes 2026 Renovado"
    assert res_up.json()["description"] == "Documentos financeiros atualizados"

    # Update parent_id of root folder to subfolder -> Should fail with 400 (cycle detection)
    res_parent_up = client.put(
        f"/api/v1/documents/folders/{folder_id}",
        json={"parent_id": subfolder["id"]},
        headers=admin_headers,
    )
    assert res_parent_up.status_code == 400

    # 4. Get folder tree
    res_tree = client.get("/api/v1/documents/folders", headers=admin_headers)
    assert res_tree.status_code == 200
    tree = res_tree.json()
    assert len(tree) >= 1

    # 5. Delete subfolder
    res_del = client.delete(f"/api/v1/documents/folders/{subfolder['id']}", headers=admin_headers)
    assert res_del.status_code == 204

    # Verify deleted
    res_tree2 = client.get("/api/v1/documents/folders", headers=admin_headers)
    tree2 = res_tree2.json()
    root_in_tree2 = next(f for f in tree2 if f["id"] == folder_id)
    assert len(root_in_tree2["children"]) == 0


def test_folder_validation_errors(client, admin_headers):
    # Non-existent parent_id on create
    res = client.post(
        "/api/v1/documents/folders",
        json={
            "name": "Orfan Folder",
            "parent_id": str(uuid.uuid4()),
        },
        headers=admin_headers,
    )
    assert res.status_code == 404

    # Create a valid folder
    res_valid = client.post(
        "/api/v1/documents/folders",
        json={"name": "Valid Folder"},
        headers=admin_headers,
    )
    valid_id = res_valid.json()["id"]

    # Self parent_id on update
    res_self = client.put(
        f"/api/v1/documents/folders/{valid_id}",
        json={"parent_id": valid_id},
        headers=admin_headers,
    )
    assert res_self.status_code == 400

    # Parent folder not found on update
    res_nof = client.put(
        f"/api/v1/documents/folders/{valid_id}",
        json={"parent_id": str(uuid.uuid4())},
        headers=admin_headers,
    )
    assert res_nof.status_code == 404

    # Update non-existent folder
    res_nf_up = client.put(
        f"/api/v1/documents/folders/{uuid.uuid4()}",
        json={"name": "Ghost"},
        headers=admin_headers,
    )
    assert res_nf_up.status_code == 404

    # Delete non-existent folder
    res_nf_del = client.delete(
        f"/api/v1/documents/folders/{uuid.uuid4()}",
        headers=admin_headers,
    )
    assert res_nf_del.status_code == 404


def test_document_crud_and_search(client, admin_headers):
    # Create folder
    res_f = client.post(
        "/api/v1/documents/folders",
        json={"name": "Atas de Reunião"},
        headers=admin_headers,
    )
    folder_id = res_f.json()["id"]

    # Create doc in non-existent folder
    res_err = client.post(
        "/api/v1/documents",
        json={
            "folder_id": str(uuid.uuid4()),
            "title": "Ata Error",
            "file_url": "https://storage.example.com/docs/err.pdf",
            "file_size_bytes": 100,
        },
        headers=admin_headers,
    )
    assert res_err.status_code == 404

    # Create document
    res_doc = client.post(
        "/api/v1/documents",
        json={
            "folder_id": folder_id,
            "title": "Ata Assembleia Geral 2026",
            "description": "Ata da reunião ordinária de janeiro",
            "file_url": "https://storage.example.com/docs/ata_2026_01.pdf",
            "file_size_bytes": 1024500,
            "mime_type": "application/pdf",
            "publication_year": 2026,
            "publication_month": 1,
            "tags": ["ata", "assembleia", "2026"],
        },
        headers=admin_headers,
    )
    assert res_doc.status_code == 201
    doc = res_doc.json()
    assert doc["title"] == "Ata Assembleia Geral 2026"
    assert doc["version_number"] == 1
    assert doc["previous_version_id"] is None
    assert "ata" in doc["tags"]

    doc_id = doc["id"]

    # List documents in folder
    res_list = client.get(f"/api/v1/documents?folder_id={folder_id}", headers=admin_headers)
    assert res_list.status_code == 200
    paged = res_list.json()
    assert paged["total"] == 1
    assert paged["items"][0]["id"] == doc_id

    # Filter by tag
    res_tag = client.get("/api/v1/documents?tag=assembleia", headers=admin_headers)
    assert res_tag.status_code == 200
    assert res_tag.json()["total"] == 1

    # Filter by search
    res_search = client.get("/api/v1/documents?search=Janeiro", headers=admin_headers)
    assert res_search.status_code == 200
    assert res_search.json()["total"] == 1

    # Filter by year and month
    res_ym = client.get("/api/v1/documents?year=2026&month=1", headers=admin_headers)
    assert res_ym.status_code == 200
    assert res_ym.json()["total"] == 1

    # Delete document
    res_del = client.delete(f"/api/v1/documents/{doc_id}", headers=admin_headers)
    assert res_del.status_code == 204

    # Delete non-existent document
    res_nf_doc_del = client.delete(f"/api/v1/documents/{uuid.uuid4()}", headers=admin_headers)
    assert res_nf_doc_del.status_code == 404

    # Verify deleted
    res_list2 = client.get(f"/api/v1/documents?folder_id={folder_id}", headers=admin_headers)
    assert res_list2.json()["total"] == 0


def test_document_versioning(client, admin_headers):
    # Create folder & document
    res_f = client.post(
        "/api/v1/documents/folders",
        json={"name": "Regulamento Interno"},
        headers=admin_headers,
    )
    folder_id = res_f.json()["id"]

    res_doc1 = client.post(
        "/api/v1/documents",
        json={
            "folder_id": folder_id,
            "title": "Regulamento Interno v1",
            "file_url": "https://storage.example.com/docs/reg_v1.pdf",
            "file_size_bytes": 500000,
            "tags": ["reg"],
        },
        headers=admin_headers,
    )
    v1_id = res_doc1.json()["id"]

    # Upload new version inheriting title/tags
    res_doc2 = client.post(
        f"/api/v1/documents/{v1_id}/versions",
        json={
            "file_url": "https://storage.example.com/docs/reg_v2.pdf",
            "file_size_bytes": 550000,
        },
        headers=admin_headers,
    )
    assert res_doc2.status_code == 201
    v2 = res_doc2.json()
    assert v2["version_number"] == 2
    assert v2["previous_version_id"] == v1_id
    assert v2["title"] == "Regulamento Interno v1"
    assert "reg" in v2["tags"]

    # Version of non-existent doc
    res_v_err = client.post(
        f"/api/v1/documents/{uuid.uuid4()}/versions",
        json={
            "file_url": "https://storage.example.com/docs/reg_v3.pdf",
            "file_size_bytes": 600000,
        },
        headers=admin_headers,
    )
    assert res_v_err.status_code == 404


def test_document_download_logging(client, admin_headers):
    # Create folder & document
    res_f = client.post(
        "/api/v1/documents/folders",
        json={"name": "Publicações"},
        headers=admin_headers,
    )
    folder_id = res_f.json()["id"]

    res_doc = client.post(
        "/api/v1/documents",
        json={
            "folder_id": folder_id,
            "title": "Edital de Convocação",
            "file_url": "https://storage.example.com/docs/edital.pdf",
            "file_size_bytes": 120000,
        },
        headers=admin_headers,
    )
    doc_id = res_doc.json()["id"]

    # Download document
    res_dl = client.post(f"/api/v1/documents/{doc_id}/download", headers=admin_headers)
    assert res_dl.status_code == 200
    assert res_dl.json()["file_url"] == "https://storage.example.com/docs/edital.pdf"

    # Download non-existent document
    res_dl_nf = client.post(f"/api/v1/documents/{uuid.uuid4()}/download", headers=admin_headers)
    assert res_dl_nf.status_code == 404


def test_invalid_json_roles_and_non_existent_folder_query(client, admin_headers, session):
    # Insert folder with malformed allowed_roles_json manually
    folder = DocumentFolder(
        name="Bad Roles Folder",
        allowed_roles_json="INVALID_JSON",
    )
    session.add(folder)
    session.commit()

    # Get tree should not crash
    res_tree = client.get("/api/v1/documents/folders", headers=admin_headers)
    assert res_tree.status_code == 200

    # Query docs with non-existent folder_id
    res_no_f = client.get(f"/api/v1/documents?folder_id={uuid.uuid4()}", headers=admin_headers)
    assert res_no_f.status_code == 404
