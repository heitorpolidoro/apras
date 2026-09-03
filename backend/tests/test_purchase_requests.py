"""Tests for purchase request CRUD, filters and summary (APRAS-37)."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.security import create_access_token
from app.models.user import User
from tests.conftest import make_user


def _make_user(session: Session, role: str, email: str, cpf: str) -> User:
    user = make_user(
        session,
        id=uuid.uuid4(),
        email=email,
        full_name=f"User {email}",
        hashed_password="hash",
        profile=role,
        cpf=cpf,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


@pytest.fixture
def admin(session: Session) -> User:
    return _make_user(session, "ADMINISTRATOR", "admin_pr@test.com", "11111111111")


@pytest.fixture
def director(session: Session) -> User:
    return _make_user(session, "DIRECTOR", "director_pr@test.com", "22222222222")


@pytest.fixture
def manager(session: Session) -> User:
    return _make_user(session, "MANAGER", "manager_pr@test.com", "33333333333")


def _create_request(client: TestClient, user: User, **overrides) -> dict:
    payload = {
        "title": "Troca das bombas d'água",
        "description": "Substituir as duas bombas do reservatório inferior.",
        "general_notes": "Prazo até o fim do mês. Falar com o zelador.",
    }
    payload.update(overrides)
    res = client.post("/api/v1/purchase-requests", json=payload, headers=_headers(user))
    assert res.status_code == 201, res.text
    return res.json()


def test_create_purchase_request_returns_201_with_texts(
    client: TestClient, admin: User
) -> None:
    body = _create_request(client, admin)

    assert body["id"]
    assert body["status"] == "OPEN"
    assert body["description"] == "Substituir as duas bombas do reservatório inferior."
    assert body["general_notes"] == "Prazo até o fim do mês. Falar com o zelador."
    assert body["requested_by_name"] == "User admin_pr@test.com"
    assert body["quote_count"] == 0
    assert body["lowest_quote_total"] is None
    assert body["selected_quote_id"] is None


@pytest.mark.parametrize("role_fixture", ["admin", "director", "manager"])
def test_all_write_roles_can_create(
    client: TestClient, request: pytest.FixtureRequest, role_fixture: str
) -> None:
    user = request.getfixturevalue(role_fixture)
    body = _create_request(client, user)
    assert body["status"] == "OPEN"


def test_title_is_required_and_non_empty(client: TestClient, admin: User) -> None:
    res = client.post(
        "/api/v1/purchase-requests", json={"title": ""}, headers=_headers(admin)
    )
    assert res.status_code == 422


def test_list_requests_paginates_and_filters(
    client: TestClient, admin: User, manager: User
) -> None:
    _create_request(client, admin, title="Compra de lâmpadas LED")
    _create_request(client, manager, title="Compra de tinta acrílica")

    res = client.get("/api/v1/purchase-requests", headers=_headers(admin))
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 2
    assert body["skip"] == 0
    assert body["limit"] == 100
    assert len(body["items"]) == 2

    res = client.get(
        "/api/v1/purchase-requests",
        params={"requested_by_id": str(manager.id)},
        headers=_headers(admin),
    )
    assert res.json()["total"] == 1
    assert res.json()["items"][0]["title"] == "Compra de tinta acrílica"

    res = client.get(
        "/api/v1/purchase-requests",
        params={"status": "OPEN"},
        headers=_headers(admin),
    )
    assert res.json()["total"] == 2

    res = client.get(
        "/api/v1/purchase-requests", params={"limit": 1}, headers=_headers(admin)
    )
    assert res.json()["total"] == 2
    assert len(res.json()["items"]) == 1


def test_search_matches_title_and_description_case_insensitively(
    client: TestClient, admin: User
) -> None:
    _create_request(client, admin, title="Compra de lâmpadas LED", description="galpão")
    _create_request(client, admin, title="Pintura", description="Tinta ACRILICA branca")

    res = client.get(
        "/api/v1/purchase-requests",
        params={"search": "lâmpadas"},
        headers=_headers(admin),
    )
    assert res.json()["total"] == 1

    # Case-insensitive match on `description` (ASCII folding is all SQLite's
    # LIKE offers; Postgres ILIKE is a superset of it).
    res = client.get(
        "/api/v1/purchase-requests",
        params={"search": "acrilica"},
        headers=_headers(admin),
    )
    assert res.json()["total"] == 1
    assert res.json()["items"][0]["title"] == "Pintura"


def test_get_request_detail_returns_empty_collections(
    client: TestClient, admin: User
) -> None:
    created = _create_request(client, admin)

    res = client.get(
        f"/api/v1/purchase-requests/{created['id']}", headers=_headers(admin)
    )
    assert res.status_code == 200
    body = res.json()
    assert body["quotes"] == []
    assert body["decisions"] == []
    assert body["current_decision"] is None


def test_get_unknown_request_returns_404(client: TestClient, admin: User) -> None:
    res = client.get(
        f"/api/v1/purchase-requests/{uuid.uuid4()}", headers=_headers(admin)
    )
    assert res.status_code == 404


def test_update_and_delete_request(client: TestClient, admin: User) -> None:
    created = _create_request(client, admin)

    res = client.put(
        f"/api/v1/purchase-requests/{created['id']}",
        json={"title": "Troca das bombas (revisado)", "general_notes": "Urgente"},
        headers=_headers(admin),
    )
    assert res.status_code == 200
    assert res.json()["title"] == "Troca das bombas (revisado)"
    assert res.json()["general_notes"] == "Urgente"

    res = client.delete(
        f"/api/v1/purchase-requests/{created['id']}", headers=_headers(admin)
    )
    assert res.status_code == 204

    res = client.get(
        f"/api/v1/purchase-requests/{created['id']}", headers=_headers(admin)
    )
    assert res.status_code == 404


def test_update_and_delete_unknown_request_returns_404(
    client: TestClient, admin: User
) -> None:
    unknown = uuid.uuid4()
    res = client.put(
        f"/api/v1/purchase-requests/{unknown}",
        json={"title": "x"},
        headers=_headers(admin),
    )
    assert res.status_code == 404
    res = client.delete(
        f"/api/v1/purchase-requests/{unknown}", headers=_headers(admin)
    )
    assert res.status_code == 404


def test_cancel_request(client: TestClient, admin: User) -> None:
    created = _create_request(client, admin)

    res = client.post(
        f"/api/v1/purchase-requests/{created['id']}/cancel", headers=_headers(admin)
    )
    assert res.status_code == 200
    assert res.json()["status"] == "CANCELLED"

    # Cancelling twice is rejected with 400.
    res = client.post(
        f"/api/v1/purchase-requests/{created['id']}/cancel", headers=_headers(admin)
    )
    assert res.status_code == 400

    res = client.post(
        f"/api/v1/purchase-requests/{uuid.uuid4()}/cancel", headers=_headers(admin)
    )
    assert res.status_code == 404


def test_summary_counts_by_status(client: TestClient, admin: User) -> None:
    open_req = _create_request(client, admin, title="Aberto")
    cancelled = _create_request(client, admin, title="Cancelado")
    client.post(
        f"/api/v1/purchase-requests/{cancelled['id']}/cancel", headers=_headers(admin)
    )

    decided = _create_request(client, admin, title="Decidido")
    quote = client.post(
        f"/api/v1/purchase-requests/{decided['id']}/quotes",
        json={"supplier_name": "Fornecedor A", "unit_price": 100.0, "quantity": 3},
        headers=_headers(admin),
    ).json()
    client.post(
        f"/api/v1/purchase-requests/{decided['id']}/decision",
        json={
            "quote_id": quote["id"],
            "justification": "Melhor preço e prazo de entrega curto.",
        },
        headers=_headers(admin),
    )

    res = client.get("/api/v1/purchase-requests/summary", headers=_headers(admin))
    assert res.status_code == 200
    body = res.json()
    assert body["open_count"] == 1
    assert body["decided_count"] == 1
    assert body["cancelled_count"] == 1
    assert body["total_selected_value"] == 300.0
    assert open_req["id"]


def test_list_row_carries_decision_projection(client: TestClient, admin: User) -> None:
    created = _create_request(client, admin)
    cheap = client.post(
        f"/api/v1/purchase-requests/{created['id']}/quotes",
        json={"supplier_name": "Barato", "unit_price": 10.0, "quantity": 2},
        headers=_headers(admin),
    ).json()
    client.post(
        f"/api/v1/purchase-requests/{created['id']}/quotes",
        json={"supplier_name": "Caro", "unit_price": 50.0, "quantity": 2},
        headers=_headers(admin),
    )
    client.post(
        f"/api/v1/purchase-requests/{created['id']}/decision",
        json={"quote_id": cheap["id"], "justification": "Menor preço do mercado."},
        headers=_headers(admin),
    )

    res = client.get("/api/v1/purchase-requests", headers=_headers(admin))
    row = res.json()["items"][0]
    assert row["quote_count"] == 2
    assert row["lowest_quote_total"] == 20.0
    assert row["selected_quote_id"] == cheap["id"]
    assert row["selected_quote_total"] == 20.0
    assert row["decision_justification"] == "Menor preço do mercado."
    assert row["decided_at"] is not None
