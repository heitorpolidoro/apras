"""Tests for the justified choice of a supplier quote (APRAS-37)."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.security import create_access_token
from app.models.enums import UserRole
from app.models.purchase import PurchaseQuoteDecision
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
    return _make_user(session, UserRole.ADMINISTRATOR, "admin_d@test.com", "11111111111")


@pytest.fixture
def director(session: Session) -> User:
    return _make_user(session, UserRole.DIRECTOR, "director_d@test.com", "22222222222")


@pytest.fixture
def manager(session: Session) -> User:
    return _make_user(session, UserRole.MANAGER, "manager_d@test.com", "33333333333")


@pytest.fixture
def scenario(client: TestClient, admin: User) -> dict:
    """A purchase request with two quotes: cheap (200) and expensive (900)."""
    request_id = client.post(
        "/api/v1/purchase-requests",
        json={"title": "Manutenção do elevador"},
        headers=_headers(admin),
    ).json()["id"]

    cheap = client.post(
        f"/api/v1/purchase-requests/{request_id}/quotes",
        json={"supplier_name": "Barato", "unit_price": 100.0, "quantity": 2},
        headers=_headers(admin),
    ).json()
    expensive = client.post(
        f"/api/v1/purchase-requests/{request_id}/quotes",
        json={"supplier_name": "Caro", "unit_price": 300.0, "quantity": 3},
        headers=_headers(admin),
    ).json()
    return {"request_id": request_id, "cheap": cheap, "expensive": expensive}


def _decide(client: TestClient, user: User, request_id: str, **payload):
    return client.post(
        f"/api/v1/purchase-requests/{request_id}/decision",
        json=payload,
        headers=_headers(user),
    )


def test_director_decision_marks_request_decided(
    client: TestClient, director: User, admin: User, scenario: dict
) -> None:
    res = _decide(
        client,
        director,
        scenario["request_id"],
        quote_id=scenario["expensive"]["id"],
        justification="Único fornecedor com peça original e garantia de 2 anos.",
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["quote_id"] == scenario["expensive"]["id"]
    assert body["quote_supplier_name"] == "Caro"
    assert body["quote_total_price"] == 900.0
    assert body["is_current"] is True

    detail = client.get(
        f"/api/v1/purchase-requests/{scenario['request_id']}", headers=_headers(admin)
    ).json()
    assert detail["status"] == "DECIDED"
    current = detail["current_decision"]
    assert current["justification"] == (
        "Único fornecedor com peça original e garantia de 2 anos."
    )
    assert current["decided_by_name"] == "User director_d@test.com"
    assert current["decided_at"]
    assert current["is_current"] is True

    selected = [q for q in detail["quotes"] if q["is_selected"]]
    assert len(selected) == 1
    assert selected[0]["id"] == scenario["expensive"]["id"]
    # The cheapest quote is still flagged as such even though it lost.
    assert detail["quotes"][0]["id"] == scenario["cheap"]["id"]
    assert detail["quotes"][0]["is_lowest_price"] is True
    assert detail["quotes"][0]["is_selected"] is False


def test_administrator_may_decide(
    client: TestClient, admin: User, scenario: dict
) -> None:
    res = _decide(
        client,
        admin,
        scenario["request_id"],
        quote_id=scenario["cheap"]["id"],
        justification="Menor preço com a mesma especificação técnica.",
    )
    assert res.status_code == 201


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"justification": ""},
        {"justification": "         "},
        {"justification": "curtinha1"},
    ],
    ids=["missing", "empty", "blank", "nine-chars"],
)
def test_invalid_justification_is_422_and_records_nothing(
    client: TestClient, admin: User, session: Session, scenario: dict, payload: dict
) -> None:
    res = _decide(
        client, admin, scenario["request_id"], quote_id=scenario["cheap"]["id"], **payload
    )
    assert res.status_code == 422, res.text

    assert session.exec(select(PurchaseQuoteDecision)).all() == []
    detail = client.get(
        f"/api/v1/purchase-requests/{scenario['request_id']}", headers=_headers(admin)
    ).json()
    assert detail["decisions"] == []
    assert detail["current_decision"] is None
    assert detail["status"] == "OPEN"


def test_manager_cannot_decide(
    client: TestClient, manager: User, session: Session, scenario: dict
) -> None:
    res = _decide(
        client,
        manager,
        scenario["request_id"],
        quote_id=scenario["cheap"]["id"],
        justification="Achei melhor esse fornecedor mesmo.",
    )
    assert res.status_code == 403
    assert session.exec(select(PurchaseQuoteDecision)).all() == []


def test_decision_on_unknown_request_or_quote_is_404(
    client: TestClient, admin: User, scenario: dict
) -> None:
    res = _decide(
        client,
        admin,
        str(uuid.uuid4()),
        quote_id=scenario["cheap"]["id"],
        justification="Justificativa suficientemente longa.",
    )
    assert res.status_code == 404

    res = _decide(
        client,
        admin,
        scenario["request_id"],
        quote_id=str(uuid.uuid4()),
        justification="Justificativa suficientemente longa.",
    )
    assert res.status_code == 404


def test_decision_on_cancelled_request_is_400(
    client: TestClient, admin: User, scenario: dict
) -> None:
    client.post(
        f"/api/v1/purchase-requests/{scenario['request_id']}/cancel",
        headers=_headers(admin),
    )
    res = _decide(
        client,
        admin,
        scenario["request_id"],
        quote_id=scenario["cheap"]["id"],
        justification="Justificativa suficientemente longa.",
    )
    assert res.status_code == 400


def test_second_decision_supersedes_and_preserves_the_first(
    client: TestClient, admin: User, director: User, scenario: dict
) -> None:
    request_id = scenario["request_id"]
    first = _decide(
        client,
        admin,
        request_id,
        quote_id=scenario["cheap"]["id"],
        justification="Primeira escolha: menor preço absoluto.",
    )
    assert first.status_code == 201

    second = _decide(
        client,
        director,
        request_id,
        quote_id=scenario["expensive"]["id"],
        justification="Revisão da diretoria: o mais barato não atende a NBR.",
    )
    assert second.status_code == 201

    detail = client.get(
        f"/api/v1/purchase-requests/{request_id}", headers=_headers(admin)
    ).json()
    assert detail["status"] == "DECIDED"
    assert len(detail["decisions"]) == 2

    newest, previous = detail["decisions"]
    assert newest["justification"] == (
        "Revisão da diretoria: o mais barato não atende a NBR."
    )
    assert newest["is_current"] is True
    assert newest["decided_by_name"] == "User director_d@test.com"
    assert previous["justification"] == "Primeira escolha: menor preço absoluto."
    assert previous["is_current"] is False
    assert previous["decided_by_name"] == "User admin_d@test.com"

    assert detail["current_decision"]["id"] == newest["id"]
    selected = [q["id"] for q in detail["quotes"] if q["is_selected"]]
    assert selected == [scenario["expensive"]["id"]]


def test_cancel_after_decision_is_400(
    client: TestClient, admin: User, scenario: dict
) -> None:
    _decide(
        client,
        admin,
        scenario["request_id"],
        quote_id=scenario["cheap"]["id"],
        justification="Justificativa suficientemente longa.",
    )
    res = client.post(
        f"/api/v1/purchase-requests/{scenario['request_id']}/cancel",
        headers=_headers(admin),
    )
    assert res.status_code == 400
