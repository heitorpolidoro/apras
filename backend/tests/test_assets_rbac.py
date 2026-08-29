"""RBAC tests for Asset and Inventory Management endpoints (APRAS-34)."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.security import create_access_token
from app.models.enums import UserRole
from app.models.user import User


def _make_user(session: Session, role: UserRole, email: str, cpf: str) -> User:
    user = User(
        id=uuid.uuid4(),
        email=email,
        full_name=f"User {email}",
        hashed_password="hash",
        role=role,
        cpf=cpf,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _headers(user: User) -> dict[str, str]:
    token = create_access_token(user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin(session: Session) -> User:
    return _make_user(session, UserRole.ADMINISTRATOR, "admin_rbac@test.com", "11111111111")


@pytest.fixture
def director(session: Session) -> User:
    return _make_user(session, UserRole.DIRECTOR, "director_rbac@test.com", "22222222222")


@pytest.fixture
def manager(session: Session) -> User:
    return _make_user(session, UserRole.MANAGER, "manager_rbac@test.com", "33333333333")


@pytest.fixture
def resident(session: Session) -> User:
    return _make_user(session, UserRole.RESIDENT, "resident_rbac@test.com", "44444444444")


@pytest.fixture
def porteiro(session: Session) -> User:
    return _make_user(session, UserRole.PORTEIRO, "porteiro_rbac@test.com", "55555555555")


@pytest.fixture
def guest(session: Session) -> User:
    return _make_user(session, UserRole.GUEST, "guest_rbac@test.com", "66666666666")


def test_director_full_crud_and_movements(session: Session, client: TestClient, director: User):
    # Create
    create_res = client.post(
        "/api/v1/assets",
        json={
            "name": "Bomba D'água Submersa",
            "category": "MANUTENCAO",
            "location": "Casa de Bombas",
            "is_consumable": False,
            "current_quantity": 1,
        },
        headers=_headers(director),
    )
    assert create_res.status_code == 201
    asset_id = create_res.json()["id"]

    # Update
    up_res = client.put(
        f"/api/v1/assets/{asset_id}",
        json={"location": "Casa de Bombas 2"},
        headers=_headers(director),
    )
    assert up_res.status_code == 200

    # Adjustment
    adj_res = client.post(
        f"/api/v1/assets/{asset_id}/movements",
        json={"movement_type": "AJUSTE_INVENTARIO", "quantity": 2, "reason": "Correção"},
        headers=_headers(director),
    )
    assert adj_res.status_code == 201

    # Delete
    del_res = client.delete(f"/api/v1/assets/{asset_id}", headers=_headers(director))
    assert del_res.status_code == 204


def test_manager_permissions(session: Session, client: TestClient, admin: User, manager: User):
    # Create an asset as admin
    create_res = client.post(
        "/api/v1/assets",
        json={
            "name": "Álcool 70% 1L",
            "category": "LIMPEZA",
            "location": "DML",
            "is_consumable": True,
            "current_quantity": 20,
            "min_quantity": 5,
        },
        headers=_headers(admin),
    )
    asset_id = create_res.json()["id"]

    # 1. Manager CAN list assets
    list_res = client.get("/api/v1/assets", headers=_headers(manager))
    assert list_res.status_code == 200

    # 2. Manager CAN get asset detail
    get_res = client.get(f"/api/v1/assets/{asset_id}", headers=_headers(manager))
    assert get_res.status_code == 200

    # 3. Manager CAN get summary
    sum_res = client.get("/api/v1/assets/summary", headers=_headers(manager))
    assert sum_res.status_code == 200

    # 4. Manager CAN record ENTRADA
    ent_res = client.post(
        f"/api/v1/assets/{asset_id}/movements",
        json={"movement_type": "ENTRADA", "quantity": 5, "reason": "Recebimento"},
        headers=_headers(manager),
    )
    assert ent_res.status_code == 201

    # 5. Manager CAN record SAIDA
    sai_res = client.post(
        f"/api/v1/assets/{asset_id}/movements",
        json={"movement_type": "SAIDA", "quantity": 2, "reason": "Limpeza do hall"},
        headers=_headers(manager),
    )
    assert sai_res.status_code == 201

    # 6. Manager CANNOT create assets (403)
    cant_create = client.post(
        "/api/v1/assets",
        json={
            "name": "Novo Item",
            "category": "LIMPEZA",
            "location": "DML",
            "is_consumable": True,
        },
        headers=_headers(manager),
    )
    assert cant_create.status_code == 403

    # 7. Manager CANNOT update assets (403)
    cant_update = client.put(
        f"/api/v1/assets/{asset_id}",
        json={"location": "Novo local"},
        headers=_headers(manager),
    )
    assert cant_update.status_code == 403

    # 8. Manager CANNOT delete assets (403)
    cant_delete = client.delete(f"/api/v1/assets/{asset_id}", headers=_headers(manager))
    assert cant_delete.status_code == 403

    # 9. Manager CANNOT record AJUSTE_INVENTARIO (403)
    cant_ajuste = client.post(
        f"/api/v1/assets/{asset_id}/movements",
        json={"movement_type": "AJUSTE_INVENTARIO", "quantity": 10, "reason": "Ajuste"},
        headers=_headers(manager),
    )
    assert cant_ajuste.status_code == 403

    # 10. Manager CANNOT record BAIXA_PATRIMONIAL (403)
    cant_baixa = client.post(
        f"/api/v1/assets/{asset_id}/movements",
        json={"movement_type": "BAIXA_PATRIMONIAL", "quantity": 1, "reason": "Baixa"},
        headers=_headers(manager),
    )
    assert cant_baixa.status_code == 403


@pytest.mark.parametrize("blocked_role_fixture", ["resident", "porteiro", "guest"])
def test_blocked_roles_cannot_access_any_asset_endpoints(
    session: Session, client: TestClient, admin: User, request: pytest.FixtureRequest, blocked_role_fixture: str
):
    blocked_user: User = request.getfixturevalue(blocked_role_fixture)

    # Pre-create an asset
    create_res = client.post(
        "/api/v1/assets",
        json={
            "name": "Equipamento Teste",
            "category": "ELETRONICOS",
            "location": "Portaria",
            "is_consumable": False,
            "current_quantity": 1,
        },
        headers=_headers(admin),
    )
    asset_id = create_res.json()["id"]

    headers = _headers(blocked_user)

    assert client.get("/api/v1/assets", headers=headers).status_code == 403
    assert client.get("/api/v1/assets/summary", headers=headers).status_code == 403
    assert client.get(f"/api/v1/assets/{asset_id}", headers=headers).status_code == 403
    assert (
        client.post(
            "/api/v1/assets",
            json={
                "name": "Novo",
                "category": "LIMPEZA",
                "location": "DML",
                "is_consumable": True,
            },
            headers=headers,
        ).status_code
        == 403
    )
    assert (
        client.put(
            f"/api/v1/assets/{asset_id}",
            json={"name": "Atualizado"},
            headers=headers,
        ).status_code
        == 403
    )
    assert client.delete(f"/api/v1/assets/{asset_id}", headers=headers).status_code == 403
    assert (
        client.post(
            f"/api/v1/assets/{asset_id}/movements",
            json={"movement_type": "ENTRADA", "quantity": 1, "reason": "R"},
            headers=headers,
        ).status_code
        == 403
    )
    assert client.get("/api/v1/inventory-movements", headers=headers).status_code == 403
