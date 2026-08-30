"""Tests for supplier quotes and their extra fields (APRAS-37)."""

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
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


@pytest.fixture
def admin(session: Session) -> User:
    return _make_user(session, UserRole.ADMINISTRATOR, "admin_q@test.com", "11111111111")


@pytest.fixture
def manager(session: Session) -> User:
    return _make_user(session, UserRole.MANAGER, "manager_q@test.com", "33333333333")


@pytest.fixture
def purchase_request(client: TestClient, admin: User) -> dict:
    res = client.post(
        "/api/v1/purchase-requests",
        json={"title": "Reforma do playground"},
        headers=_headers(admin),
    )
    assert res.status_code == 201
    return res.json()


def _add_quote(client: TestClient, user: User, request_id: str, **overrides):
    payload = {"supplier_name": "Fornecedor A", "unit_price": 100.0, "quantity": 2}
    payload.update(overrides)
    return client.post(
        f"/api/v1/purchase-requests/{request_id}/quotes",
        json=payload,
        headers=_headers(user),
    )


def test_add_quote_returns_201_with_computed_total(
    client: TestClient, admin: User, purchase_request: dict
) -> None:
    res = _add_quote(
        client,
        admin,
        purchase_request["id"],
        supplier_name="Playground Kids",
        supplier_contact="(11) 99999-0000",
        unit_price=1250.5,
        quantity=4,
        notes="Inclui instalação",
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["supplier_name"] == "Playground Kids"
    assert body["unit_price"] == 1250.5
    assert body["quantity"] == 4
    assert body["total_price"] == 5002.0
    assert body["created_by_name"] == "User admin_q@test.com"


def test_multiple_quotes_sorted_by_total_with_lowest_flag(
    client: TestClient, admin: User, manager: User, purchase_request: dict
) -> None:
    request_id = purchase_request["id"]
    _add_quote(client, admin, request_id, supplier_name="Caro", unit_price=90.0, quantity=10)
    _add_quote(client, manager, request_id, supplier_name="Barato", unit_price=10.0, quantity=10)
    _add_quote(client, admin, request_id, supplier_name="Medio", unit_price=50.0, quantity=10)

    res = client.get(f"/api/v1/purchase-requests/{request_id}", headers=_headers(admin))
    quotes = res.json()["quotes"]
    assert [q["supplier_name"] for q in quotes] == ["Barato", "Medio", "Caro"]
    assert [q["total_price"] for q in quotes] == [100.0, 500.0, 900.0]
    assert [q["is_lowest_price"] for q in quotes] == [True, False, False]
    assert all(q["is_selected"] is False for q in quotes)
    assert quotes[0]["created_by_name"] == "User manager_q@test.com"


def test_extra_fields_round_trip_preserves_order_and_strips_whitespace(
    client: TestClient, admin: User, purchase_request: dict
) -> None:
    res = _add_quote(
        client,
        admin,
        purchase_request["id"],
        extra_fields=[
            {"label": " Prazo de entrega ", "value": " 15 dias "},
            {"label": "Garantia", "value": "12 meses"},
            {"label": "Frete", "value": "Incluso"},
        ],
    )
    assert res.status_code == 201
    assert res.json()["extra_fields"] == [
        {"label": "Prazo de entrega", "value": "15 dias"},
        {"label": "Garantia", "value": "12 meses"},
        {"label": "Frete", "value": "Incluso"},
    ]

    detail = client.get(
        f"/api/v1/purchase-requests/{purchase_request['id']}", headers=_headers(admin)
    ).json()
    assert detail["quotes"][0]["extra_fields"] == [
        {"label": "Prazo de entrega", "value": "15 dias"},
        {"label": "Garantia", "value": "12 meses"},
        {"label": "Frete", "value": "Incluso"},
    ]


def test_extra_field_blank_value_is_accepted_and_stored_empty(
    client: TestClient, admin: User, purchase_request: dict
) -> None:
    res = _add_quote(
        client,
        admin,
        purchase_request["id"],
        extra_fields=[{"label": " Prazo ", "value": "  "}],
    )
    assert res.status_code == 201
    assert res.json()["extra_fields"] == [{"label": "Prazo", "value": ""}]

    detail = client.get(
        f"/api/v1/purchase-requests/{purchase_request['id']}", headers=_headers(admin)
    ).json()
    assert detail["quotes"][0]["extra_fields"] == [{"label": "Prazo", "value": ""}]


def test_extra_field_omitted_value_defaults_to_empty(
    client: TestClient, admin: User, purchase_request: dict
) -> None:
    res = _add_quote(
        client, admin, purchase_request["id"], extra_fields=[{"label": "Prazo"}]
    )
    assert res.status_code == 201
    assert res.json()["extra_fields"] == [{"label": "Prazo", "value": ""}]


def test_extra_field_empty_label_is_422(
    client: TestClient, admin: User, purchase_request: dict
) -> None:
    res = _add_quote(
        client, admin, purchase_request["id"], extra_fields=[{"label": ""}]
    )
    assert res.status_code == 422


def test_extra_field_whitespace_only_label_is_422(
    client: TestClient, admin: User, purchase_request: dict
) -> None:
    res = _add_quote(
        client, admin, purchase_request["id"], extra_fields=[{"label": "   "}]
    )
    assert res.status_code == 422


def test_extra_field_duplicate_labels_differing_by_case_is_422(
    client: TestClient, admin: User, purchase_request: dict
) -> None:
    res = _add_quote(
        client,
        admin,
        purchase_request["id"],
        extra_fields=[{"label": "Prazo"}, {"label": "prazo"}],
    )
    assert res.status_code == 422


def test_extra_field_duplicate_labels_differing_by_whitespace_is_422(
    client: TestClient, admin: User, purchase_request: dict
) -> None:
    res = _add_quote(
        client,
        admin,
        purchase_request["id"],
        extra_fields=[{"label": "Prazo"}, {"label": " prazo "}],
    )
    assert res.status_code == 422


def test_extra_field_label_too_long_is_422(
    client: TestClient, admin: User, purchase_request: dict
) -> None:
    # max_length runs on the raw string, before stripping: a 60-char label
    # wrapped in spaces is over the limit and rejected.
    res = _add_quote(
        client,
        admin,
        purchase_request["id"],
        extra_fields=[{"label": " " + "P" * 60 + " "}],
    )
    assert res.status_code == 422


def test_extra_fields_over_twenty_entries_is_422(
    client: TestClient, admin: User, purchase_request: dict
) -> None:
    res = _add_quote(
        client,
        admin,
        purchase_request["id"],
        extra_fields=[{"label": f"Campo {i}", "value": "x"} for i in range(21)],
    )
    assert res.status_code == 422

    ok = _add_quote(
        client,
        admin,
        purchase_request["id"],
        extra_fields=[{"label": f"Campo {i}", "value": "x"} for i in range(20)],
    )
    assert ok.status_code == 201
    assert len(ok.json()["extra_fields"]) == 20


def test_quote_validation_rejects_bad_price_and_quantity(
    client: TestClient, admin: User, purchase_request: dict
) -> None:
    assert _add_quote(client, admin, purchase_request["id"], unit_price=-1).status_code == 422
    assert _add_quote(client, admin, purchase_request["id"], quantity=0).status_code == 422
    assert _add_quote(client, admin, purchase_request["id"], supplier_name="").status_code == 422


def test_update_quote_replaces_extra_fields_wholesale(
    client: TestClient, admin: User, purchase_request: dict
) -> None:
    quote = _add_quote(
        client,
        admin,
        purchase_request["id"],
        extra_fields=[{"label": "Prazo", "value": "10 dias"}],
    ).json()

    res = client.put(
        f"/api/v1/purchase-requests/{purchase_request['id']}/quotes/{quote['id']}",
        json={"unit_price": 200.0, "extra_fields": [{"label": "Garantia", "value": "2 anos"}]},
        headers=_headers(admin),
    )
    assert res.status_code == 200
    assert res.json()["unit_price"] == 200.0
    assert res.json()["total_price"] == 400.0
    assert res.json()["extra_fields"] == [{"label": "Garantia", "value": "2 anos"}]


def test_update_quote_without_extra_fields_leaves_stored_list_untouched(
    client: TestClient, admin: User, purchase_request: dict
) -> None:
    quote = _add_quote(
        client,
        admin,
        purchase_request["id"],
        extra_fields=[{"label": "Prazo", "value": "10 dias"}],
    ).json()

    res = client.put(
        f"/api/v1/purchase-requests/{purchase_request['id']}/quotes/{quote['id']}",
        json={"supplier_name": "Fornecedor B"},
        headers=_headers(admin),
    )
    assert res.status_code == 200
    assert res.json()["supplier_name"] == "Fornecedor B"
    assert res.json()["extra_fields"] == [{"label": "Prazo", "value": "10 dias"}]


def test_update_quote_rejects_invalid_extra_fields(
    client: TestClient, admin: User, purchase_request: dict
) -> None:
    quote = _add_quote(client, admin, purchase_request["id"]).json()
    res = client.put(
        f"/api/v1/purchase-requests/{purchase_request['id']}/quotes/{quote['id']}",
        json={"extra_fields": [{"label": "A"}, {"label": " a "}]},
        headers=_headers(admin),
    )
    assert res.status_code == 422


def test_delete_quote(client: TestClient, admin: User, purchase_request: dict) -> None:
    quote = _add_quote(client, admin, purchase_request["id"]).json()
    res = client.delete(
        f"/api/v1/purchase-requests/{purchase_request['id']}/quotes/{quote['id']}",
        headers=_headers(admin),
    )
    assert res.status_code == 204

    detail = client.get(
        f"/api/v1/purchase-requests/{purchase_request['id']}", headers=_headers(admin)
    ).json()
    assert detail["quotes"] == []


def test_quote_from_another_request_returns_404(
    client: TestClient, admin: User, purchase_request: dict
) -> None:
    other = client.post(
        "/api/v1/purchase-requests",
        json={"title": "Outro pedido"},
        headers=_headers(admin),
    ).json()
    quote = _add_quote(client, admin, other["id"]).json()

    res = client.put(
        f"/api/v1/purchase-requests/{purchase_request['id']}/quotes/{quote['id']}",
        json={"unit_price": 1.0},
        headers=_headers(admin),
    )
    assert res.status_code == 404

    res = client.delete(
        f"/api/v1/purchase-requests/{purchase_request['id']}/quotes/{quote['id']}",
        headers=_headers(admin),
    )
    assert res.status_code == 404


def test_quote_endpoints_on_unknown_request_return_404(
    client: TestClient, admin: User
) -> None:
    unknown = uuid.uuid4()
    assert _add_quote(client, admin, str(unknown)).status_code == 404
    assert (
        client.put(
            f"/api/v1/purchase-requests/{unknown}/quotes/{uuid.uuid4()}",
            json={"unit_price": 1.0},
            headers=_headers(admin),
        ).status_code
        == 404
    )
    assert (
        client.delete(
            f"/api/v1/purchase-requests/{unknown}/quotes/{uuid.uuid4()}",
            headers=_headers(admin),
        ).status_code
        == 404
    )


def test_quotes_are_frozen_after_a_decision(
    client: TestClient, admin: User, purchase_request: dict
) -> None:
    request_id = purchase_request["id"]
    quote = _add_quote(client, admin, request_id).json()
    client.post(
        f"/api/v1/purchase-requests/{request_id}/decision",
        json={"quote_id": quote["id"], "justification": "Único fornecedor disponível."},
        headers=_headers(admin),
    )

    assert _add_quote(client, admin, request_id).status_code == 409
    assert (
        client.put(
            f"/api/v1/purchase-requests/{request_id}/quotes/{quote['id']}",
            json={"unit_price": 1.0},
            headers=_headers(admin),
        ).status_code
        == 409
    )
    assert (
        client.delete(
            f"/api/v1/purchase-requests/{request_id}/quotes/{quote['id']}",
            headers=_headers(admin),
        ).status_code
        == 409
    )


def test_quotes_are_frozen_on_a_cancelled_request(
    client: TestClient, admin: User, purchase_request: dict
) -> None:
    request_id = purchase_request["id"]
    client.post(
        f"/api/v1/purchase-requests/{request_id}/cancel", headers=_headers(admin)
    )
    assert _add_quote(client, admin, request_id).status_code == 409
