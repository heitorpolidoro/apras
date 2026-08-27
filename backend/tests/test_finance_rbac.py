"""RBAC permission tests for the Association Financial Area & Dashboard (APRAS-22)."""

from datetime import date
import uuid

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.security import create_access_token, get_password_hash
from app.models.enums import TransactionType, UserRole
from app.models.finance import FinanceCategory, FinancialTransaction
from app.models.user import User


@pytest.fixture
def director_user(session: Session) -> User:
    user = User(
        id=uuid.uuid4(),
        email="director_fin_rbac@test.com",
        full_name="Director User",
        hashed_password=get_password_hash("password123"),
        role=UserRole.DIRECTOR,
        cpf="84411604085",
    )
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def manager_user(session: Session) -> User:
    user = User(
        id=uuid.uuid4(),
        email="manager_fin_rbac@test.com",
        full_name="Manager User",
        hashed_password=get_password_hash("password123"),
        role=UserRole.MANAGER,
        cpf="12260662058",
    )
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def other_manager_user(session: Session) -> User:
    user = User(
        id=uuid.uuid4(),
        email="manager2_fin_rbac@test.com",
        full_name="Second Manager",
        hashed_password=get_password_hash("password123"),
        role=UserRole.MANAGER,
        cpf="79398261034",
    )
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def resident_user(session: Session) -> User:
    user = User(
        id=uuid.uuid4(),
        email="resident_fin_rbac@test.com",
        full_name="Resident User",
        hashed_password=get_password_hash("password123"),
        role=UserRole.RESIDENT,
        cpf="46816405073",
    )
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def guest_user(session: Session) -> User:
    user = User(
        id=uuid.uuid4(),
        email="guest_fin_rbac@test.com",
        full_name="Guest User",
        hashed_password=get_password_hash("password123"),
        role=UserRole.GUEST,
        cpf="38411475019",
    )
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def admin_token(admin_user: User) -> str:
    return create_access_token(subject=str(admin_user.id))


@pytest.fixture
def director_token(director_user: User) -> str:
    return create_access_token(subject=str(director_user.id))


@pytest.fixture
def manager_token(manager_user: User) -> str:
    return create_access_token(subject=str(manager_user.id))


@pytest.fixture
def other_manager_token(other_manager_user: User) -> str:
    return create_access_token(subject=str(other_manager_user.id))


@pytest.fixture
def resident_token(resident_user: User) -> str:
    return create_access_token(subject=str(resident_user.id))


@pytest.fixture
def guest_token(guest_user: User) -> str:
    return create_access_token(subject=str(guest_user.id))


@pytest.fixture
def expense_category(session: Session) -> FinanceCategory:
    category = FinanceCategory(name="Manutenção RBAC", type=TransactionType.EXPENSE)
    session.add(category)
    session.commit()
    session.refresh(category)
    return category


@pytest.fixture
def manager_transaction(
    session: Session, manager_user: User, expense_category: FinanceCategory
) -> FinancialTransaction:
    txn = FinancialTransaction(
        type=TransactionType.EXPENSE,
        category_id=expense_category.id,
        description="Criada pelo gerente",
        amount=100.0,
        transaction_date=date(2026, 1, 1),
        created_by_id=manager_user.id,
    )
    session.add(txn)
    session.commit()
    session.refresh(txn)
    return txn


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# -----------------------------------------------------------------------------
# Read Access: Categories, Budget Lines, Transactions, Reports
# -----------------------------------------------------------------------------


def test_read_endpoints_allowed_roles_and_guest_forbidden(
    client: TestClient,
    admin_token: str,
    director_token: str,
    manager_token: str,
    resident_token: str,
    guest_token: str,
):
    read_urls = [
        "/api/v1/finance/categories",
        "/api/v1/finance/budget-lines?fiscal_year=2026",
        "/api/v1/finance/transactions",
        "/api/v1/finance/balance",
        "/api/v1/finance/statement?start_date=2026-01-01&end_date=2026-01-31",
        "/api/v1/finance/budget-vs-actual?fiscal_year=2026",
    ]
    for url in read_urls:
        for token in [admin_token, director_token, manager_token, resident_token]:
            resp = client.get(url, headers=_auth(token))
            assert resp.status_code == status.HTTP_200_OK, url

        resp_guest = client.get(url, headers=_auth(guest_token))
        assert resp_guest.status_code == status.HTTP_403_FORBIDDEN, url

        resp_unauth = client.get(url)
        assert resp_unauth.status_code == status.HTTP_401_UNAUTHORIZED, url


def test_list_categories_include_inactive_restricted_to_admin_roles(
    client: TestClient,
    admin_token: str,
    director_token: str,
    manager_token: str,
    resident_token: str,
    guest_token: str,
):
    for token in [manager_token, resident_token, guest_token]:
        resp = client.get(
            "/api/v1/finance/categories?include_inactive=true", headers=_auth(token)
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    for token in [admin_token, director_token]:
        resp = client.get(
            "/api/v1/finance/categories?include_inactive=true", headers=_auth(token)
        )
        assert resp.status_code == status.HTTP_200_OK


def test_list_categories_omitted_or_false_include_inactive_ok_for_all_read_roles(
    client: TestClient,
    admin_token: str,
    director_token: str,
    manager_token: str,
    resident_token: str,
):
    for token in [admin_token, director_token, manager_token, resident_token]:
        resp_omitted = client.get("/api/v1/finance/categories", headers=_auth(token))
        assert resp_omitted.status_code == status.HTTP_200_OK

        resp_false = client.get(
            "/api/v1/finance/categories?include_inactive=false", headers=_auth(token)
        )
        assert resp_false.status_code == status.HTTP_200_OK


# -----------------------------------------------------------------------------
# Category & Budget Line Mutations: Admin/Director only
# -----------------------------------------------------------------------------


def test_create_category_restricted_to_admin_roles(
    client: TestClient,
    admin_token: str,
    director_token: str,
    manager_token: str,
    resident_token: str,
    guest_token: str,
):
    payload = {"name": "Nova Categoria", "type": "EXPENSE"}
    assert (
        client.post(
            "/api/v1/finance/categories", headers=_auth(admin_token), json=payload
        ).status_code
        == status.HTTP_201_CREATED
    )
    payload2 = {"name": "Nova Categoria 2", "type": "EXPENSE"}
    assert (
        client.post(
            "/api/v1/finance/categories", headers=_auth(director_token), json=payload2
        ).status_code
        == status.HTTP_201_CREATED
    )

    for token in [manager_token, resident_token, guest_token]:
        resp = client.post(
            "/api/v1/finance/categories",
            headers=_auth(token),
            json={"name": "Não Permitido", "type": "EXPENSE"},
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_update_category_restricted_to_admin_roles(
    client: TestClient,
    admin_token: str,
    manager_token: str,
    resident_token: str,
    expense_category: FinanceCategory,
):
    for token in [manager_token, resident_token]:
        resp = client.put(
            f"/api/v1/finance/categories/{expense_category.id}",
            headers=_auth(token),
            json={"name": "Tentativa"},
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    resp_admin = client.put(
        f"/api/v1/finance/categories/{expense_category.id}",
        headers=_auth(admin_token),
        json={"name": "Renomeada"},
    )
    assert resp_admin.status_code == status.HTTP_200_OK


def test_create_budget_line_restricted_to_admin_roles(
    client: TestClient,
    admin_token: str,
    director_token: str,
    manager_token: str,
    resident_token: str,
    expense_category: FinanceCategory,
):
    payload = {
        "category_id": str(expense_category.id),
        "fiscal_year": 2026,
        "planned_amount": 1000.0,
    }
    for token in [manager_token, resident_token]:
        resp = client.post(
            "/api/v1/finance/budget-lines", headers=_auth(token), json=payload
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    resp_admin = client.post(
        "/api/v1/finance/budget-lines", headers=_auth(admin_token), json=payload
    )
    assert resp_admin.status_code == status.HTTP_201_CREATED

    # Duplicate returns 409
    resp_duplicate = client.post(
        "/api/v1/finance/budget-lines", headers=_auth(director_token), json=payload
    )
    assert resp_duplicate.status_code == status.HTTP_409_CONFLICT


def test_budget_line_update_delete_restricted_to_admin_roles(
    client: TestClient,
    admin_token: str,
    manager_token: str,
    resident_token: str,
    expense_category: FinanceCategory,
):
    resp = client.post(
        "/api/v1/finance/budget-lines",
        headers=_auth(admin_token),
        json={
            "category_id": str(expense_category.id),
            "fiscal_year": 2027,
            "planned_amount": 500.0,
        },
    )
    bl_id = resp.json()["id"]

    for token in [manager_token, resident_token]:
        assert (
            client.put(
                f"/api/v1/finance/budget-lines/{bl_id}",
                headers=_auth(token),
                json={"planned_amount": 10.0},
            ).status_code
            == status.HTTP_403_FORBIDDEN
        )
        assert (
            client.delete(
                f"/api/v1/finance/budget-lines/{bl_id}", headers=_auth(token)
            ).status_code
            == status.HTTP_403_FORBIDDEN
        )

    assert (
        client.delete(
            f"/api/v1/finance/budget-lines/{bl_id}", headers=_auth(admin_token)
        ).status_code
        == status.HTTP_204_NO_CONTENT
    )


# -----------------------------------------------------------------------------
# Transaction Mutations: Manager can create; ownership rules on edit/delete
# -----------------------------------------------------------------------------


def test_create_transaction_rbac(
    client: TestClient,
    admin_token: str,
    director_token: str,
    manager_token: str,
    resident_token: str,
    guest_token: str,
    expense_category: FinanceCategory,
):
    payload = {
        "type": "EXPENSE",
        "category_id": str(expense_category.id),
        "description": "Teste RBAC",
        "amount": 10.0,
        "transaction_date": "2026-01-01",
    }
    for token in [admin_token, director_token, manager_token]:
        resp = client.post(
            "/api/v1/finance/transactions", headers=_auth(token), json=payload
        )
        assert resp.status_code == status.HTTP_201_CREATED

    for token in [resident_token, guest_token]:
        resp = client.post(
            "/api/v1/finance/transactions", headers=_auth(token), json=payload
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_manager_can_only_edit_own_transactions(
    client: TestClient,
    manager_token: str,
    other_manager_token: str,
    manager_transaction: FinancialTransaction,
):
    # Manager who created it can edit
    resp_owner = client.put(
        f"/api/v1/finance/transactions/{manager_transaction.id}",
        headers=_auth(manager_token),
        json={"description": "Atualizada pelo dono"},
    )
    assert resp_owner.status_code == status.HTTP_200_OK

    # A different manager cannot edit someone else's transaction
    resp_other = client.put(
        f"/api/v1/finance/transactions/{manager_transaction.id}",
        headers=_auth(other_manager_token),
        json={"description": "Tentativa indevida"},
    )
    assert resp_other.status_code == status.HTTP_403_FORBIDDEN


def test_only_admin_director_can_delete_any_transaction(
    client: TestClient,
    admin_token: str,
    director_token: str,
    manager_token: str,
    other_manager_token: str,
    resident_token: str,
    manager_transaction: FinancialTransaction,
):
    # Manager (even the creator) cannot delete
    resp_owner_delete = client.delete(
        f"/api/v1/finance/transactions/{manager_transaction.id}",
        headers=_auth(manager_token),
    )
    assert resp_owner_delete.status_code == status.HTTP_403_FORBIDDEN

    resp_other_delete = client.delete(
        f"/api/v1/finance/transactions/{manager_transaction.id}",
        headers=_auth(other_manager_token),
    )
    assert resp_other_delete.status_code == status.HTTP_403_FORBIDDEN

    resp_resident_delete = client.delete(
        f"/api/v1/finance/transactions/{manager_transaction.id}",
        headers=_auth(resident_token),
    )
    assert resp_resident_delete.status_code == status.HTTP_403_FORBIDDEN

    resp_admin_delete = client.delete(
        f"/api/v1/finance/transactions/{manager_transaction.id}",
        headers=_auth(admin_token),
    )
    assert resp_admin_delete.status_code == status.HTTP_204_NO_CONTENT


def test_invoice_upload_delete_ownership_rules(
    client: TestClient,
    manager_token: str,
    other_manager_token: str,
    admin_token: str,
    resident_token: str,
    manager_transaction: FinancialTransaction,
):
    pdf_bytes = b"%PDF-1.4 fake"

    # Resident cannot upload invoices at all (not a write role)
    resp_resident = client.post(
        f"/api/v1/finance/transactions/{manager_transaction.id}/invoice",
        headers=_auth(resident_token),
        files={"file": ("nota.pdf", pdf_bytes, "application/pdf")},
    )
    assert resp_resident.status_code == status.HTTP_403_FORBIDDEN

    # Another manager cannot upload an invoice on a transaction they didn't create
    resp_other = client.post(
        f"/api/v1/finance/transactions/{manager_transaction.id}/invoice",
        headers=_auth(other_manager_token),
        files={"file": ("nota.pdf", pdf_bytes, "application/pdf")},
    )
    assert resp_other.status_code == status.HTTP_403_FORBIDDEN

    # The owning manager can upload
    resp_owner = client.post(
        f"/api/v1/finance/transactions/{manager_transaction.id}/invoice",
        headers=_auth(manager_token),
        files={"file": ("nota.pdf", pdf_bytes, "application/pdf")},
    )
    assert resp_owner.status_code == status.HTTP_200_OK

    # Another manager cannot delete that invoice either
    resp_other_delete = client.delete(
        f"/api/v1/finance/transactions/{manager_transaction.id}/invoice",
        headers=_auth(other_manager_token),
    )
    assert resp_other_delete.status_code == status.HTTP_403_FORBIDDEN

    # Admin (not the creator) can still manage the invoice
    resp_admin_delete = client.delete(
        f"/api/v1/finance/transactions/{manager_transaction.id}/invoice",
        headers=_auth(admin_token),
    )
    assert resp_admin_delete.status_code == status.HTTP_204_NO_CONTENT


def test_guest_forbidden_on_every_endpoint(
    client: TestClient, guest_token: str, expense_category: FinanceCategory
):
    endpoints = [
        ("get", "/api/v1/finance/categories", None),
        ("post", "/api/v1/finance/categories", {"name": "X", "type": "EXPENSE"}),
        ("get", "/api/v1/finance/budget-lines?fiscal_year=2026", None),
        (
            "post",
            "/api/v1/finance/budget-lines",
            {
                "category_id": str(expense_category.id),
                "fiscal_year": 2026,
                "planned_amount": 10.0,
            },
        ),
        ("get", "/api/v1/finance/transactions", None),
        (
            "post",
            "/api/v1/finance/transactions",
            {
                "type": "EXPENSE",
                "category_id": str(expense_category.id),
                "description": "X",
                "amount": 10.0,
                "transaction_date": "2026-01-01",
            },
        ),
        ("get", "/api/v1/finance/balance", None),
        ("get", "/api/v1/finance/statement?start_date=2026-01-01&end_date=2026-01-31", None),
        ("get", "/api/v1/finance/budget-vs-actual?fiscal_year=2026", None),
    ]
    for method, url, body in endpoints:
        kwargs = {"headers": _auth(guest_token)}
        if body is not None:
            kwargs["json"] = body
        resp = getattr(client, method)(url, **kwargs)
        assert resp.status_code == status.HTTP_403_FORBIDDEN, (method, url)


def test_transaction_not_found_returns_404(client: TestClient, admin_token: str):
    fake_id = uuid.uuid4()
    resp = client.get(
        f"/api/v1/finance/transactions/{fake_id}", headers=_auth(admin_token)
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND
