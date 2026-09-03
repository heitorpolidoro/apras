"""RBAC matrix for the purchase quotation module (APRAS-37)."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.security import create_access_token
from app.models.user import User
from tests.conftest import make_user

BLOCKED_ROLES = ["RESIDENT", "PORTEIRO", "GUEST"]


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
    return _make_user(session, "ADMINISTRATOR", "admin_rb@test.com", "11111111111")


@pytest.fixture
def director(session: Session) -> User:
    return _make_user(session, "DIRECTOR", "director_rb@test.com", "22222222222")


@pytest.fixture
def manager(session: Session) -> User:
    return _make_user(session, "MANAGER", "manager_rb@test.com", "33333333333")


@pytest.fixture
def other_manager(session: Session) -> User:
    return _make_user(session, "MANAGER", "manager2_rb@test.com", "77777777777")


@pytest.fixture
def blocked_users(session: Session) -> list[User]:
    return [
        _make_user(session, "RESIDENT", "resident_rb@test.com", "44444444444"),
        _make_user(session, "PORTEIRO", "porteiro_rb@test.com", "55555555555"),
        _make_user(session, "GUEST", "guest_rb@test.com", "66666666666"),
    ]


def _create_request(client: TestClient, user: User, title: str = "Pedido") -> dict:
    res = client.post(
        "/api/v1/purchase-requests", json={"title": title}, headers=_headers(user)
    )
    assert res.status_code == 201, res.text
    return res.json()


def _add_quote(client: TestClient, user: User, request_id: str) -> dict:
    res = client.post(
        f"/api/v1/purchase-requests/{request_id}/quotes",
        json={"supplier_name": "Fornecedor", "unit_price": 10.0, "quantity": 1},
        headers=_headers(user),
    )
    assert res.status_code == 201, res.text
    return res.json()


def test_unauthenticated_access_is_401(client: TestClient) -> None:
    assert client.get("/api/v1/purchase-requests").status_code == 401


def test_blocked_roles_get_403_on_every_read_and_write(
    client: TestClient, admin: User, blocked_users: list[User]
) -> None:
    purchase_request = _create_request(client, admin)
    quote = _add_quote(client, admin, purchase_request["id"])
    rid = purchase_request["id"]

    for user in blocked_users:
        h = _headers(user)
        assert client.get("/api/v1/purchase-requests", headers=h).status_code == 403
        assert client.get("/api/v1/purchase-requests/summary", headers=h).status_code == 403
        assert client.get(f"/api/v1/purchase-requests/{rid}", headers=h).status_code == 403
        assert (
            client.post(
                "/api/v1/purchase-requests", json={"title": "x"}, headers=h
            ).status_code
            == 403
        )
        assert (
            client.put(
                f"/api/v1/purchase-requests/{rid}", json={"title": "x"}, headers=h
            ).status_code
            == 403
        )
        assert client.delete(f"/api/v1/purchase-requests/{rid}", headers=h).status_code == 403
        assert (
            client.post(
                f"/api/v1/purchase-requests/{rid}/quotes",
                json={"supplier_name": "F", "unit_price": 1.0, "quantity": 1},
                headers=h,
            ).status_code
            == 403
        )
        assert (
            client.put(
                f"/api/v1/purchase-requests/{rid}/quotes/{quote['id']}",
                json={"unit_price": 1.0},
                headers=h,
            ).status_code
            == 403
        )
        assert (
            client.delete(
                f"/api/v1/purchase-requests/{rid}/quotes/{quote['id']}", headers=h
            ).status_code
            == 403
        )
        assert (
            client.post(
                f"/api/v1/purchase-requests/{rid}/decision",
                json={"quote_id": quote["id"], "justification": "Justificativa longa."},
                headers=h,
            ).status_code
            == 403
        )
        assert (
            client.post(f"/api/v1/purchase-requests/{rid}/cancel", headers=h).status_code
            == 403
        )


def test_manager_may_read_create_and_quote(
    client: TestClient, manager: User
) -> None:
    purchase_request = _create_request(client, manager, "Pedido do gerente")
    rid = purchase_request["id"]

    assert client.get("/api/v1/purchase-requests", headers=_headers(manager)).status_code == 200
    assert (
        client.get("/api/v1/purchase-requests/summary", headers=_headers(manager)).status_code
        == 200
    )
    assert client.get(f"/api/v1/purchase-requests/{rid}", headers=_headers(manager)).status_code == 200

    quote = _add_quote(client, manager, rid)
    assert (
        client.put(
            f"/api/v1/purchase-requests/{rid}/quotes/{quote['id']}",
            json={"unit_price": 99.0},
            headers=_headers(manager),
        ).status_code
        == 200
    )
    assert (
        client.put(
            f"/api/v1/purchase-requests/{rid}",
            json={"title": "Pedido do gerente (rev)"},
            headers=_headers(manager),
        ).status_code
        == 200
    )
    assert (
        client.delete(
            f"/api/v1/purchase-requests/{rid}/quotes/{quote['id']}",
            headers=_headers(manager),
        ).status_code
        == 204
    )
    assert client.delete(f"/api/v1/purchase-requests/{rid}", headers=_headers(manager)).status_code == 204


def test_manager_cannot_decide_or_cancel(
    client: TestClient, manager: User
) -> None:
    purchase_request = _create_request(client, manager)
    rid = purchase_request["id"]
    quote = _add_quote(client, manager, rid)

    assert (
        client.post(
            f"/api/v1/purchase-requests/{rid}/decision",
            json={"quote_id": quote["id"], "justification": "Justificativa longa o bastante."},
            headers=_headers(manager),
        ).status_code
        == 403
    )
    assert (
        client.post(f"/api/v1/purchase-requests/{rid}/cancel", headers=_headers(manager)).status_code
        == 403
    )


def test_manager_cannot_touch_another_managers_request_or_quote(
    client: TestClient, manager: User, other_manager: User
) -> None:
    purchase_request = _create_request(client, other_manager, "Pedido do outro gerente")
    rid = purchase_request["id"]
    quote = _add_quote(client, other_manager, rid)

    assert (
        client.put(
            f"/api/v1/purchase-requests/{rid}", json={"title": "roubado"}, headers=_headers(manager)
        ).status_code
        == 403
    )
    assert client.delete(f"/api/v1/purchase-requests/{rid}", headers=_headers(manager)).status_code == 403
    assert (
        client.put(
            f"/api/v1/purchase-requests/{rid}/quotes/{quote['id']}",
            json={"unit_price": 1.0},
            headers=_headers(manager),
        ).status_code
        == 403
    )
    assert (
        client.delete(
            f"/api/v1/purchase-requests/{rid}/quotes/{quote['id']}", headers=_headers(manager)
        ).status_code
        == 403
    )
    # ...but a Manager may still add their own quote to someone else's request.
    assert _add_quote(client, manager, rid)["created_by_id"] == str(manager.id)


def test_manager_cannot_edit_own_request_after_decision(
    client: TestClient, manager: User, director: User
) -> None:
    purchase_request = _create_request(client, manager)
    rid = purchase_request["id"]
    quote = _add_quote(client, manager, rid)
    assert (
        client.post(
            f"/api/v1/purchase-requests/{rid}/decision",
            json={"quote_id": quote["id"], "justification": "Justificativa longa o bastante."},
            headers=_headers(director),
        ).status_code
        == 201
    )

    assert (
        client.put(
            f"/api/v1/purchase-requests/{rid}", json={"title": "novo"}, headers=_headers(manager)
        ).status_code
        == 403
    )
    assert client.delete(f"/api/v1/purchase-requests/{rid}", headers=_headers(manager)).status_code == 403
    # Quote edits are blocked by the freeze rule (409) before ownership matters.
    assert (
        client.put(
            f"/api/v1/purchase-requests/{rid}/quotes/{quote['id']}",
            json={"unit_price": 1.0},
            headers=_headers(manager),
        ).status_code
        == 409
    )


def test_admin_and_director_may_edit_a_managers_request(
    client: TestClient, admin: User, director: User, manager: User
) -> None:
    purchase_request = _create_request(client, manager)
    rid = purchase_request["id"]
    quote = _add_quote(client, manager, rid)

    assert (
        client.put(
            f"/api/v1/purchase-requests/{rid}",
            json={"title": "Ajustado pela diretoria"},
            headers=_headers(director),
        ).status_code
        == 200
    )
    assert (
        client.put(
            f"/api/v1/purchase-requests/{rid}/quotes/{quote['id']}",
            json={"unit_price": 5.0},
            headers=_headers(admin),
        ).status_code
        == 200
    )
    assert client.delete(f"/api/v1/purchase-requests/{rid}", headers=_headers(admin)).status_code == 204
