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
def admin_user_local(session: Session) -> User:
    return _make_user(session, UserRole.ADMINISTRATOR, "admin_asset@test.com", "12345678909")


@pytest.fixture
def manager_user_local(session: Session) -> User:
    return _make_user(session, UserRole.MANAGER, "manager_asset@test.com", "98765432100")


def test_create_fixed_asset_success(session: Session, client: TestClient, admin_user_local: User):
    payload = {
        "name": "Cortador de Grama Gasolina",
        "category": "FERRAMENTAS",
        "serial_number": "SN-98765",
        "asset_tag": "PAT-00101",
        "location": "Almoxarifado Central",
        "acquisition_date": "2026-01-15",
        "acquisition_value": 2500.0,
        "condition": "NOVO",
        "is_consumable": False,
        "current_quantity": 1,
        "unit_of_measure": "un",
        "notes": "Motor 4 tempos",
    }
    response = client.post("/api/v1/assets", json=payload, headers=_headers(admin_user_local))
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Cortador de Grama Gasolina"
    assert data["category"] == "FERRAMENTAS"
    assert data["asset_tag"] == "PAT-00101"
    assert data["acquisition_value"] == 2500.0
    assert data["is_consumable"] is False
    assert data["current_quantity"] == 1
    assert data["is_low_stock"] is False
    asset_id = data["id"]

    # Verify initial movement was recorded
    detail_res = client.get(f"/api/v1/assets/{asset_id}", headers=_headers(admin_user_local))
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert len(detail_data["movements"]) == 1
    assert detail_data["movements"][0]["movement_type"] == "ENTRADA"
    assert detail_data["movements"][0]["quantity"] == 1
    assert detail_data["movements"][0]["new_quantity"] == 1


def test_create_consumable_asset_with_min_quantity(session: Session, client: TestClient, admin_user_local: User):
    payload = {
        "name": "Lâmpada LED Tubular 18W",
        "category": "MANUTENCAO",
        "location": "Depósito de Elétrica",
        "condition": "NOVO",
        "is_consumable": True,
        "current_quantity": 5,
        "min_quantity": 10,
        "unit_of_measure": "un",
    }
    response = client.post("/api/v1/assets", json=payload, headers=_headers(admin_user_local))
    assert response.status_code == 201
    data = response.json()
    assert data["is_consumable"] is True
    assert data["current_quantity"] == 5
    assert data["min_quantity"] == 10
    assert data["is_low_stock"] is True


def test_create_asset_duplicate_tag_returns_409(session: Session, client: TestClient, admin_user_local: User):
    payload = {
        "name": "Câmera Bullet IP",
        "category": "SEGURANCA",
        "asset_tag": "PAT-CAM-01",
        "location": "Portaria 1",
        "is_consumable": False,
        "current_quantity": 1,
    }
    res1 = client.post("/api/v1/assets", json=payload, headers=_headers(admin_user_local))
    assert res1.status_code == 201

    res2 = client.post("/api/v1/assets", json=payload, headers=_headers(admin_user_local))
    assert res2.status_code == 409
    assert "Já existe um ativo com a etiqueta patrimonial" in res2.json()["detail"]


def test_get_asset_by_id_and_not_found(session: Session, client: TestClient, admin_user_local: User):
    # Nonexistent ID
    fake_id = uuid.uuid4()
    res = client.get(f"/api/v1/assets/{fake_id}", headers=_headers(admin_user_local))
    assert res.status_code == 404

    # Existing
    create_res = client.post(
        "/api/v1/assets",
        json={
            "name": "Furadeira de Impacto",
            "category": "FERRAMENTAS",
            "location": "Oficina",
            "is_consumable": False,
            "current_quantity": 1,
        },
        headers=_headers(admin_user_local),
    )
    asset_id = create_res.json()["id"]

    get_res = client.get(f"/api/v1/assets/{asset_id}", headers=_headers(admin_user_local))
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Furadeira de Impacto"


def test_update_asset_metadata(session: Session, client: TestClient, admin_user_local: User):
    create_res = client.post(
        "/api/v1/assets",
        json={
            "name": "Mesa de Reunião",
            "category": "MOBILIARIO",
            "location": "Sala da Administração",
            "asset_tag": "PAT-MESA-01",
            "is_consumable": False,
            "current_quantity": 1,
        },
        headers=_headers(admin_user_local),
    )
    asset_id = create_res.json()["id"]

    # Update location and condition
    update_res = client.put(
        f"/api/v1/assets/{asset_id}",
        json={"location": "Sala de Reuniões Principal", "condition": "REGULAR"},
        headers=_headers(admin_user_local),
    )
    assert update_res.status_code == 200
    assert update_res.json()["location"] == "Sala de Reuniões Principal"
    assert update_res.json()["condition"] == "REGULAR"

    # Updating with another existing asset_tag returns 409
    client.post(
        "/api/v1/assets",
        json={
            "name": "Cadeira Giratória",
            "category": "MOBILIARIO",
            "location": "Sala",
            "asset_tag": "PAT-CAD-01",
            "is_consumable": False,
        },
        headers=_headers(admin_user_local),
    )
    conflict_res = client.put(
        f"/api/v1/assets/{asset_id}",
        json={"asset_tag": "PAT-CAD-01"},
        headers=_headers(admin_user_local),
    )
    assert conflict_res.status_code == 409

    # Updating nonexistent asset
    not_found_res = client.put(
        f"/api/v1/assets/{uuid.uuid4()}",
        json={"location": "X"},
        headers=_headers(admin_user_local),
    )
    assert not_found_res.status_code == 404


def test_delete_asset_cascades(session: Session, client: TestClient, admin_user_local: User):
    create_res = client.post(
        "/api/v1/assets",
        json={
            "name": "Item Para Excluir",
            "category": "OUTROS",
            "location": "Depósito",
            "is_consumable": False,
            "current_quantity": 2,
        },
        headers=_headers(admin_user_local),
    )
    asset_id = create_res.json()["id"]

    del_res = client.delete(f"/api/v1/assets/{asset_id}", headers=_headers(admin_user_local))
    assert del_res.status_code == 204

    # Verify deleted
    get_res = client.get(f"/api/v1/assets/{asset_id}", headers=_headers(admin_user_local))
    assert get_res.status_code == 404

    # Delete nonexistent asset
    del_404 = client.delete(f"/api/v1/assets/{uuid.uuid4()}", headers=_headers(admin_user_local))
    assert del_404.status_code == 404


def test_list_assets_and_filters(session: Session, client: TestClient, admin_user_local: User):
    # Seed various assets
    client.post(
        "/api/v1/assets",
        json={
            "name": "Detergente Neutro 5L",
            "category": "LIMPEZA",
            "location": "DML Bloco A",
            "is_consumable": True,
            "current_quantity": 2,
            "min_quantity": 5,
        },
        headers=_headers(admin_user_local),
    )
    client.post(
        "/api/v1/assets",
        json={
            "name": "Desinfetante Floral 5L",
            "category": "LIMPEZA",
            "location": "DML Bloco B",
            "is_consumable": True,
            "current_quantity": 10,
            "min_quantity": 3,
        },
        headers=_headers(admin_user_local),
    )
    client.post(
        "/api/v1/assets",
        json={
            "name": "Furadeira Bosch GSB 13",
            "category": "FERRAMENTAS",
            "location": "Oficina Geral",
            "serial_number": "BOSCH-7788",
            "is_consumable": False,
            "current_quantity": 1,
            "condition": "BOM",
        },
        headers=_headers(admin_user_local),
    )

    # 1. Filter by category
    res_cat = client.get("/api/v1/assets?category=LIMPEZA", headers=_headers(admin_user_local))
    assert res_cat.status_code == 200
    assert res_cat.json()["total"] == 2

    # 2. Filter by consumable
    res_cons = client.get("/api/v1/assets?is_consumable=true", headers=_headers(admin_user_local))
    assert res_cons.status_code == 200
    assert res_cons.json()["total"] == 2

    # 3. Filter by low_stock_only
    res_low = client.get("/api/v1/assets?low_stock_only=true", headers=_headers(admin_user_local))
    assert res_low.status_code == 200
    assert res_low.json()["total"] == 1
    assert res_low.json()["items"][0]["name"] == "Detergente Neutro 5L"

    # 4. Search query
    res_search = client.get("/api/v1/assets?search=Bosch", headers=_headers(admin_user_local))
    assert res_search.status_code == 200
    assert res_search.json()["total"] == 1
    assert res_search.json()["items"][0]["name"] == "Furadeira Bosch GSB 13"

    # 5. Filter by condition
    res_cond = client.get("/api/v1/assets?condition=BOM", headers=_headers(admin_user_local))
    assert res_cond.status_code == 200
    assert res_cond.json()["total"] >= 1

    # 6. Filter by location
    res_loc = client.get("/api/v1/assets?location=Oficina", headers=_headers(admin_user_local))
    assert res_loc.status_code == 200
    assert res_loc.json()["total"] == 1


def test_asset_summary_metrics(session: Session, client: TestClient, admin_user_local: User):
    client.post(
        "/api/v1/assets",
        json={
            "name": "Projetor Epson",
            "category": "ELETRONICOS",
            "location": "Salão de Festas",
            "is_consumable": False,
            "acquisition_value": 3200.0,
            "current_quantity": 1,
        },
        headers=_headers(admin_user_local),
    )
    client.post(
        "/api/v1/assets",
        json={
            "name": "Sabonete Líquido 5L",
            "category": "LIMPEZA",
            "location": "DML",
            "is_consumable": True,
            "acquisition_value": 50.0,
            "current_quantity": 1,
            "min_quantity": 4,
        },
        headers=_headers(admin_user_local),
    )

    summary_res = client.get("/api/v1/assets/summary", headers=_headers(admin_user_local))
    assert summary_res.status_code == 200
    data = summary_res.json()
    assert data["total_assets"] >= 1
    assert data["total_consumables"] >= 1
    assert data["low_stock_count"] >= 1
    assert data["total_patrimonial_value"] >= 3200.0


def test_record_movements_entrada_saida_ajuste_baixa(
    session: Session, client: TestClient, admin_user_local: User, manager_user_local: User
):
    create_res = client.post(
        "/api/v1/assets",
        json={
            "name": "Saco de Cimento 50kg",
            "category": "MANUTENCAO",
            "location": "Galpão",
            "is_consumable": True,
            "current_quantity": 10,
            "min_quantity": 5,
        },
        headers=_headers(admin_user_local),
    )
    asset_id = create_res.json()["id"]

    # 1. ENTRADA (Manager records incoming goods)
    entrada_res = client.post(
        f"/api/v1/assets/{asset_id}/movements",
        json={
            "movement_type": "ENTRADA",
            "quantity": 15,
            "reason": "Compra NF 4589",
            "document_number": "NF-4589",
        },
        headers=_headers(manager_user_local),
    )
    assert entrada_res.status_code == 201
    assert entrada_res.json()["previous_quantity"] == 10
    assert entrada_res.json()["new_quantity"] == 25
    assert entrada_res.json()["movement_type"] == "ENTRADA"

    # 2. SAIDA (Consumption)
    saida_res = client.post(
        f"/api/v1/assets/{asset_id}/movements",
        json={
            "movement_type": "SAIDA",
            "quantity": 8,
            "reason": "Reforma calçada bloco C",
        },
        headers=_headers(manager_user_local),
    )
    assert saida_res.status_code == 201
    assert saida_res.json()["previous_quantity"] == 25
    assert saida_res.json()["new_quantity"] == 17

    # 3. SAIDA exceeding available stock returns 400 InsufficientStockError
    excess_res = client.post(
        f"/api/v1/assets/{asset_id}/movements",
        json={
            "movement_type": "SAIDA",
            "quantity": 50,
            "reason": "Uso excessivo",
        },
        headers=_headers(manager_user_local),
    )
    assert excess_res.status_code == 400
    assert "Saldo insuficiente em estoque" in excess_res.json()["detail"]

    # 4. AJUSTE_INVENTARIO (Admin counts exact balance)
    ajuste_res = client.post(
        f"/api/v1/assets/{asset_id}/movements",
        json={
            "movement_type": "AJUSTE_INVENTARIO",
            "quantity": 12,
            "reason": "Contagem física de inventário",
        },
        headers=_headers(admin_user_local),
    )
    assert ajuste_res.status_code == 201
    assert ajuste_res.json()["previous_quantity"] == 17
    assert ajuste_res.json()["new_quantity"] == 12

    # 5. BAIXA_PATRIMONIAL on fixed asset
    camera_res = client.post(
        "/api/v1/assets",
        json={
            "name": "Câmera Portaria Antiga",
            "category": "SEGURANCA",
            "location": "Portaria 2",
            "is_consumable": False,
            "current_quantity": 1,
            "condition": "DANIFICADO",
        },
        headers=_headers(admin_user_local),
    )
    camera_id = camera_res.json()["id"]

    baixa_res = client.post(
        f"/api/v1/assets/{camera_id}/movements",
        json={
            "movement_type": "BAIXA_PATRIMONIAL",
            "quantity": 1,
            "reason": "Queima por descarga atmosférica / descarte",
        },
        headers=_headers(admin_user_local),
    )
    assert baixa_res.status_code == 201
    assert baixa_res.json()["new_quantity"] == 0

    # Verify asset condition changed to BAIXADO
    cam_detail = client.get(f"/api/v1/assets/{camera_id}", headers=_headers(admin_user_local))
    assert cam_detail.json()["condition"] == "BAIXADO"
    assert cam_detail.json()["current_quantity"] == 0


def test_global_inventory_movements_audit_log(session: Session, client: TestClient, admin_user_local: User):
    create_res = client.post(
        "/api/v1/assets",
        json={
            "name": "Item Movimento Global",
            "category": "OUTROS",
            "location": "Almoxarifado",
            "is_consumable": True,
            "current_quantity": 5,
        },
        headers=_headers(admin_user_local),
    )
    asset_id = create_res.json()["id"]

    # Record ENTRADA
    client.post(
        f"/api/v1/assets/{asset_id}/movements",
        json={"movement_type": "ENTRADA", "quantity": 10, "reason": "Compra"},
        headers=_headers(admin_user_local),
    )

    # Filter by asset_id
    res_asset = client.get(
        f"/api/v1/inventory-movements?asset_id={asset_id}",
        headers=_headers(admin_user_local),
    )
    assert res_asset.status_code == 200
    assert res_asset.json()["total"] == 2

    # Filter by movement_type
    res_type = client.get(
        f"/api/v1/inventory-movements?asset_id={asset_id}&movement_type=ENTRADA",
        headers=_headers(admin_user_local),
    )
    assert res_type.status_code == 200
    assert res_type.json()["total"] == 2


def test_movement_on_nonexistent_asset_returns_404(session: Session, client: TestClient, admin_user_local: User):
    res = client.post(
        f"/api/v1/assets/{uuid.uuid4()}/movements",
        json={"movement_type": "ENTRADA", "quantity": 5, "reason": "Teste"},
        headers=_headers(admin_user_local),
    )
    assert res.status_code == 404


def test_movement_invalid_quantities(session: Session, client: TestClient, admin_user_local: User):
    create_res = client.post(
        "/api/v1/assets",
        json={
            "name": "Item Qty Test",
            "category": "OUTROS",
            "location": "Almoxarifado",
            "is_consumable": True,
            "current_quantity": 5,
        },
        headers=_headers(admin_user_local),
    )
    asset_id = create_res.json()["id"]

    # Negative quantity for ENTRADA
    res_neg = client.post(
        f"/api/v1/assets/{asset_id}/movements",
        json={"movement_type": "ENTRADA", "quantity": -5, "reason": "Invalido"},
        headers=_headers(admin_user_local),
    )
    assert res_neg.status_code == 422

    # Zero quantity for SAIDA
    res_zero = client.post(
        f"/api/v1/assets/{asset_id}/movements",
        json={"movement_type": "SAIDA", "quantity": 0, "reason": "Zero"},
        headers=_headers(admin_user_local),
    )
    assert res_zero.status_code == 422

    # Negative quantity for AJUSTE_INVENTARIO
    res_adj_neg = client.post(
        f"/api/v1/assets/{asset_id}/movements",
        json={"movement_type": "AJUSTE_INVENTARIO", "quantity": -1, "reason": "Negativo"},
        headers=_headers(admin_user_local),
    )
    assert res_adj_neg.status_code == 422

    # Zero quantity for AJUSTE_INVENTARIO is allowed (means 0 balance)
    res_adj_zero = client.post(
        f"/api/v1/assets/{asset_id}/movements",
        json={"movement_type": "AJUSTE_INVENTARIO", "quantity": 0, "reason": "Zerou estoque"},
        headers=_headers(admin_user_local),
    )
    assert res_adj_zero.status_code == 201
    assert res_adj_zero.json()["new_quantity"] == 0

