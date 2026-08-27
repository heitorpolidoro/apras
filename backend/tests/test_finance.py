"""Business-logic tests for the Association Financial Area & Dashboard (APRAS-22)."""

from datetime import date
import uuid

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.security import create_access_token, get_password_hash
from app.models.enums import TransactionType, UserRole
from app.models.finance import BudgetLine, FinanceCategory, FinancialTransaction
from app.models.user import User


@pytest.fixture
def admin_headers(admin_user: User) -> dict:
    token = create_access_token(subject=str(admin_user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def manager_user(session: Session) -> User:
    user = User(
        id=uuid.uuid4(),
        email="manager_fin@test.com",
        full_name="Manager Financeiro",
        hashed_password=get_password_hash("password123"),
        role=UserRole.MANAGER,
        cpf="12260662058",
    )
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def manager_headers(manager_user: User) -> dict:
    token = create_access_token(subject=str(manager_user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def income_category(session: Session) -> FinanceCategory:
    category = FinanceCategory(name="Taxa Condominial", type=TransactionType.INCOME)
    session.add(category)
    session.commit()
    session.refresh(category)
    return category


@pytest.fixture
def expense_category(session: Session) -> FinanceCategory:
    category = FinanceCategory(name="Manutenção", type=TransactionType.EXPENSE)
    session.add(category)
    session.commit()
    session.refresh(category)
    return category


def _make_pdf_bytes() -> bytes:
    return b"%PDF-1.4 fake invoice content"


# -----------------------------------------------------------------------------
# Category Tests
# -----------------------------------------------------------------------------


def test_create_category_success(client: TestClient, admin_headers: dict):
    resp = client.post(
        "/api/v1/finance/categories",
        headers=admin_headers,
        json={"name": "Água", "type": "EXPENSE"},
    )
    assert resp.status_code == status.HTTP_201_CREATED
    data = resp.json()
    assert data["name"] == "Água"
    assert data["type"] == "EXPENSE"
    assert data["is_active"] is True


def test_create_category_duplicate_name_and_type(
    client: TestClient, admin_headers: dict, expense_category: FinanceCategory
):
    resp = client.post(
        "/api/v1/finance/categories",
        headers=admin_headers,
        json={"name": expense_category.name, "type": "EXPENSE"},
    )
    assert resp.status_code == status.HTTP_409_CONFLICT


def test_list_categories_default_excludes_inactive(
    client: TestClient, admin_headers: dict, session: Session
):
    active = FinanceCategory(name="Ativa", type=TransactionType.INCOME)
    inactive = FinanceCategory(
        name="Inativa", type=TransactionType.INCOME, is_active=False
    )
    session.add_all([active, inactive])
    session.commit()

    resp = client.get("/api/v1/finance/categories", headers=admin_headers)
    assert resp.status_code == status.HTTP_200_OK
    names = [c["name"] for c in resp.json()]
    assert "Ativa" in names
    assert "Inativa" not in names


def test_list_categories_include_inactive_for_admin(
    client: TestClient, admin_headers: dict, session: Session
):
    inactive = FinanceCategory(
        name="Inativa2", type=TransactionType.INCOME, is_active=False
    )
    session.add(inactive)
    session.commit()

    resp = client.get(
        "/api/v1/finance/categories?include_inactive=true", headers=admin_headers
    )
    assert resp.status_code == status.HTTP_200_OK
    names = [c["name"] for c in resp.json()]
    assert "Inativa2" in names


def test_list_categories_type_filter(
    client: TestClient,
    admin_headers: dict,
    income_category: FinanceCategory,
    expense_category: FinanceCategory,
):
    resp = client.get(
        "/api/v1/finance/categories?type=INCOME", headers=admin_headers
    )
    assert resp.status_code == status.HTTP_200_OK
    types = {c["type"] for c in resp.json()}
    assert types == {"INCOME"}


def test_update_category_rename_and_deactivate(
    client: TestClient, admin_headers: dict, expense_category: FinanceCategory
):
    resp = client.put(
        f"/api/v1/finance/categories/{expense_category.id}",
        headers=admin_headers,
        json={"name": "Manutenção Predial", "is_active": False},
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["name"] == "Manutenção Predial"
    assert data["is_active"] is False


def test_update_category_not_found(client: TestClient, admin_headers: dict):
    resp = client.put(
        f"/api/v1/finance/categories/{uuid.uuid4()}",
        headers=admin_headers,
        json={"name": "Nada"},
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND


# -----------------------------------------------------------------------------
# Budget Line Tests
# -----------------------------------------------------------------------------


def test_create_budget_line_success(
    client: TestClient, admin_headers: dict, expense_category: FinanceCategory
):
    resp = client.post(
        "/api/v1/finance/budget-lines",
        headers=admin_headers,
        json={
            "category_id": str(expense_category.id),
            "fiscal_year": 2026,
            "planned_amount": 12000.0,
            "notes": "Orçamento anual de manutenção",
        },
    )
    assert resp.status_code == status.HTTP_201_CREATED
    data = resp.json()
    assert data["category_id"] == str(expense_category.id)
    assert data["category_name"] == expense_category.name
    assert data["fiscal_year"] == 2026
    assert data["planned_amount"] == 12000.0


def test_create_budget_line_duplicate_returns_409(
    client: TestClient, admin_headers: dict, expense_category: FinanceCategory
):
    payload = {
        "category_id": str(expense_category.id),
        "fiscal_year": 2026,
        "planned_amount": 1000.0,
    }
    resp1 = client.post(
        "/api/v1/finance/budget-lines", headers=admin_headers, json=payload
    )
    assert resp1.status_code == status.HTTP_201_CREATED

    resp2 = client.post(
        "/api/v1/finance/budget-lines", headers=admin_headers, json=payload
    )
    assert resp2.status_code == status.HTTP_409_CONFLICT


def test_create_budget_line_category_not_found(client: TestClient, admin_headers: dict):
    resp = client.post(
        "/api/v1/finance/budget-lines",
        headers=admin_headers,
        json={
            "category_id": str(uuid.uuid4()),
            "fiscal_year": 2026,
            "planned_amount": 1000.0,
        },
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_list_budget_lines_by_fiscal_year(
    client: TestClient, admin_headers: dict, expense_category: FinanceCategory, session: Session
):
    bl_2026 = BudgetLine(
        category_id=expense_category.id, fiscal_year=2026, planned_amount=500.0
    )
    bl_2025 = BudgetLine(
        category_id=expense_category.id, fiscal_year=2025, planned_amount=400.0
    )
    session.add_all([bl_2026, bl_2025])
    session.commit()

    resp = client.get(
        "/api/v1/finance/budget-lines?fiscal_year=2026", headers=admin_headers
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert len(data) == 1
    assert data[0]["fiscal_year"] == 2026


def test_update_and_delete_budget_line(
    client: TestClient, admin_headers: dict, expense_category: FinanceCategory, session: Session
):
    bl = BudgetLine(
        category_id=expense_category.id, fiscal_year=2026, planned_amount=100.0
    )
    session.add(bl)
    session.commit()
    session.refresh(bl)

    resp = client.put(
        f"/api/v1/finance/budget-lines/{bl.id}",
        headers=admin_headers,
        json={"planned_amount": 250.0, "notes": "Revisado"},
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["planned_amount"] == 250.0
    assert resp.json()["notes"] == "Revisado"

    resp_del = client.delete(
        f"/api/v1/finance/budget-lines/{bl.id}", headers=admin_headers
    )
    assert resp_del.status_code == status.HTTP_204_NO_CONTENT
    assert session.get(BudgetLine, bl.id) is None


def test_budget_line_update_and_delete_not_found(client: TestClient, admin_headers: dict):
    fake_id = uuid.uuid4()
    resp = client.put(
        f"/api/v1/finance/budget-lines/{fake_id}",
        headers=admin_headers,
        json={"planned_amount": 1.0},
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND

    resp_del = client.delete(
        f"/api/v1/finance/budget-lines/{fake_id}", headers=admin_headers
    )
    assert resp_del.status_code == status.HTTP_404_NOT_FOUND


# -----------------------------------------------------------------------------
# Transaction Tests
# -----------------------------------------------------------------------------


def test_create_transaction_success(
    client: TestClient, admin_headers: dict, admin_user: User, expense_category: FinanceCategory
):
    resp = client.post(
        "/api/v1/finance/transactions",
        headers=admin_headers,
        json={
            "type": "EXPENSE",
            "category_id": str(expense_category.id),
            "description": "Troca de lâmpadas",
            "amount": 350.0,
            "transaction_date": "2026-03-10",
            "payment_method": "PIX",
        },
    )
    assert resp.status_code == status.HTTP_201_CREATED
    data = resp.json()
    assert data["type"] == "EXPENSE"
    assert data["category_name"] == expense_category.name
    assert data["amount"] == 350.0
    assert data["created_by_name"] == admin_user.full_name
    assert "invoice_file_path" not in data
    assert data["invoice_file_url"] is None


def test_create_transaction_type_mismatch_returns_422(
    client: TestClient, admin_headers: dict, expense_category: FinanceCategory
):
    resp = client.post(
        "/api/v1/finance/transactions",
        headers=admin_headers,
        json={
            "type": "INCOME",
            "category_id": str(expense_category.id),
            "description": "Errado",
            "amount": 10.0,
            "transaction_date": "2026-03-10",
        },
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_create_transaction_category_not_found(client: TestClient, admin_headers: dict):
    resp = client.post(
        "/api/v1/finance/transactions",
        headers=admin_headers,
        json={
            "type": "EXPENSE",
            "category_id": str(uuid.uuid4()),
            "description": "X",
            "amount": 10.0,
            "transaction_date": "2026-03-10",
        },
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_get_transaction_success(
    client: TestClient,
    admin_headers: dict,
    admin_user: User,
    expense_category: FinanceCategory,
    session: Session,
):
    txn = FinancialTransaction(
        type=TransactionType.EXPENSE,
        category_id=expense_category.id,
        description="Buscar por id",
        amount=42.0,
        transaction_date=date(2026, 1, 1),
        created_by_id=admin_user.id,
    )
    session.add(txn)
    session.commit()
    session.refresh(txn)

    resp = client.get(
        f"/api/v1/finance/transactions/{txn.id}", headers=admin_headers
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["id"] == str(txn.id)
    assert resp.json()["description"] == "Buscar por id"


def test_get_transaction_not_found(client: TestClient, admin_headers: dict):
    resp = client.get(
        f"/api/v1/finance/transactions/{uuid.uuid4()}", headers=admin_headers
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_update_transaction_revalidates_type_category(
    client: TestClient,
    admin_headers: dict,
    admin_user: User,
    expense_category: FinanceCategory,
    income_category: FinanceCategory,
    session: Session,
):
    txn = FinancialTransaction(
        type=TransactionType.EXPENSE,
        category_id=expense_category.id,
        description="Original",
        amount=100.0,
        transaction_date=date(2026, 1, 1),
        created_by_id=admin_user.id,
    )
    session.add(txn)
    session.commit()
    session.refresh(txn)

    # Changing category to an INCOME category without changing type -> mismatch
    resp = client.put(
        f"/api/v1/finance/transactions/{txn.id}",
        headers=admin_headers,
        json={"category_id": str(income_category.id)},
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Changing both type and category consistently -> success
    resp2 = client.put(
        f"/api/v1/finance/transactions/{txn.id}",
        headers=admin_headers,
        json={"type": "INCOME", "category_id": str(income_category.id)},
    )
    assert resp2.status_code == status.HTTP_200_OK
    assert resp2.json()["type"] == "INCOME"
    assert resp2.json()["category_id"] == str(income_category.id)


def test_list_transactions_filters_and_pagination(
    client: TestClient,
    admin_headers: dict,
    admin_user: User,
    expense_category: FinanceCategory,
    income_category: FinanceCategory,
    session: Session,
):
    for i in range(3):
        session.add(
            FinancialTransaction(
                type=TransactionType.EXPENSE,
                category_id=expense_category.id,
                description=f"Despesa {i}",
                amount=10.0 + i,
                transaction_date=date(2026, 1, i + 1),
                created_by_id=admin_user.id,
            )
        )
    session.add(
        FinancialTransaction(
            type=TransactionType.INCOME,
            category_id=income_category.id,
            description="Receita",
            amount=500.0,
            transaction_date=date(2026, 1, 5),
            created_by_id=admin_user.id,
        )
    )
    session.commit()

    resp = client.get(
        "/api/v1/finance/transactions?type=EXPENSE", headers=admin_headers
    )
    assert resp.status_code == status.HTTP_200_OK
    body = resp.json()
    assert body["total"] == 3
    assert all(t["type"] == "EXPENSE" for t in body["items"])

    resp_paginated = client.get(
        "/api/v1/finance/transactions?type=EXPENSE&skip=1&limit=1",
        headers=admin_headers,
    )
    assert resp_paginated.status_code == status.HTTP_200_OK
    assert len(resp_paginated.json()["items"]) == 1

    resp_date_range = client.get(
        "/api/v1/finance/transactions?start_date=2026-01-01&end_date=2026-01-01",
        headers=admin_headers,
    )
    assert resp_date_range.status_code == status.HTTP_200_OK
    assert resp_date_range.json()["total"] == 1

    resp_category = client.get(
        f"/api/v1/finance/transactions?category_id={income_category.id}",
        headers=admin_headers,
    )
    assert resp_category.status_code == status.HTTP_200_OK
    body_category = resp_category.json()
    assert body_category["total"] == 1
    assert body_category["items"][0]["category_id"] == str(income_category.id)


def test_statement_handles_year_rollover(
    client: TestClient,
    admin_headers: dict,
    admin_user: User,
    income_category: FinanceCategory,
    session: Session,
):
    session.add_all(
        [
            FinancialTransaction(
                type=TransactionType.INCOME,
                category_id=income_category.id,
                description="Receita Dezembro",
                amount=100.0,
                transaction_date=date(2025, 12, 15),
                created_by_id=admin_user.id,
            ),
            FinancialTransaction(
                type=TransactionType.INCOME,
                category_id=income_category.id,
                description="Receita Janeiro",
                amount=200.0,
                transaction_date=date(2026, 1, 15),
                created_by_id=admin_user.id,
            ),
        ]
    )
    session.commit()

    resp = client.get(
        "/api/v1/finance/statement?start_date=2025-12-01&end_date=2026-01-31",
        headers=admin_headers,
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert [(e["year"], e["month"]) for e in data["entries"]] == [
        (2025, 12),
        (2026, 1),
    ]
    assert data["entries"][0]["income"] == 100.0
    assert data["entries"][1]["income"] == 200.0


def test_delete_transaction_removes_invoice_from_disk(
    client: TestClient,
    admin_headers: dict,
    admin_user: User,
    expense_category: FinanceCategory,
    session: Session,
):
    resp = client.post(
        "/api/v1/finance/transactions",
        headers=admin_headers,
        json={
            "type": "EXPENSE",
            "category_id": str(expense_category.id),
            "description": "Com nota",
            "amount": 200.0,
            "transaction_date": "2026-02-01",
        },
    )
    txn_id = resp.json()["id"]

    upload_resp = client.post(
        f"/api/v1/finance/transactions/{txn_id}/invoice",
        headers=admin_headers,
        files={"file": ("nota.pdf", _make_pdf_bytes(), "application/pdf")},
    )
    assert upload_resp.status_code == status.HTTP_200_OK
    invoice_url = upload_resp.json()["invoice_file_url"]
    assert invoice_url is not None

    txn_row = session.get(FinancialTransaction, uuid.UUID(txn_id))
    stored_path = txn_row.invoice_file_path
    assert stored_path is not None
    from pathlib import Path

    assert Path(stored_path).exists()

    del_resp = client.delete(
        f"/api/v1/finance/transactions/{txn_id}", headers=admin_headers
    )
    assert del_resp.status_code == status.HTTP_204_NO_CONTENT
    assert not Path(stored_path).exists()
    assert session.get(FinancialTransaction, uuid.UUID(txn_id)) is None


def test_delete_transaction_not_found(client: TestClient, admin_headers: dict):
    resp = client.delete(
        f"/api/v1/finance/transactions/{uuid.uuid4()}", headers=admin_headers
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND


# -----------------------------------------------------------------------------
# Invoice Upload/Delete Tests
# -----------------------------------------------------------------------------


def test_upload_invoice_success_and_reachable_via_static_url(
    client: TestClient, admin_headers: dict, admin_user: User, expense_category: FinanceCategory, session: Session
):
    txn = FinancialTransaction(
        type=TransactionType.EXPENSE,
        category_id=expense_category.id,
        description="Nota fiscal",
        amount=99.0,
        transaction_date=date(2026, 4, 1),
        created_by_id=admin_user.id,
    )
    session.add(txn)
    session.commit()
    session.refresh(txn)

    resp = client.post(
        f"/api/v1/finance/transactions/{txn.id}/invoice",
        headers=admin_headers,
        files={"file": ("nota.pdf", _make_pdf_bytes(), "application/pdf")},
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert "invoice_file_path" not in data
    assert data["invoice_file_url"].startswith("/static/uploads/")
    assert data["invoice_mime_type"] == "application/pdf"
    assert data["invoice_file_size_bytes"] == len(_make_pdf_bytes())

    # The static mount serves the uploaded file directly.
    static_resp = client.get(data["invoice_file_url"])
    assert static_resp.status_code == status.HTTP_200_OK


def test_upload_invoice_rejects_non_pdf(
    client: TestClient, admin_headers: dict, admin_user: User, expense_category: FinanceCategory, session: Session
):
    txn = FinancialTransaction(
        type=TransactionType.EXPENSE,
        category_id=expense_category.id,
        description="Nota fiscal",
        amount=99.0,
        transaction_date=date(2026, 4, 1),
        created_by_id=admin_user.id,
    )
    session.add(txn)
    session.commit()
    session.refresh(txn)

    resp = client.post(
        f"/api/v1/finance/transactions/{txn.id}/invoice",
        headers=admin_headers,
        files={"file": ("nota.png", b"fake-image", "image/png")},
    )
    assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_upload_invoice_rejects_oversized_file(
    client: TestClient, admin_headers: dict, admin_user: User, expense_category: FinanceCategory, session: Session
):
    txn = FinancialTransaction(
        type=TransactionType.EXPENSE,
        category_id=expense_category.id,
        description="Nota fiscal",
        amount=99.0,
        transaction_date=date(2026, 4, 1),
        created_by_id=admin_user.id,
    )
    session.add(txn)
    session.commit()
    session.refresh(txn)

    big_file = b"0" * (10 * 1024 * 1024 + 1)
    resp = client.post(
        f"/api/v1/finance/transactions/{txn.id}/invoice",
        headers=admin_headers,
        files={"file": ("big.pdf", big_file, "application/pdf")},
    )
    assert resp.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE


def test_upload_invoice_replaces_existing_file(
    client: TestClient, admin_headers: dict, admin_user: User, expense_category: FinanceCategory, session: Session
):
    txn = FinancialTransaction(
        type=TransactionType.EXPENSE,
        category_id=expense_category.id,
        description="Nota fiscal",
        amount=99.0,
        transaction_date=date(2026, 4, 1),
        created_by_id=admin_user.id,
    )
    session.add(txn)
    session.commit()
    session.refresh(txn)

    from pathlib import Path

    first = client.post(
        f"/api/v1/finance/transactions/{txn.id}/invoice",
        headers=admin_headers,
        files={"file": ("nota1.pdf", _make_pdf_bytes(), "application/pdf")},
    )
    session.refresh(txn)
    first_path = Path(txn.invoice_file_path)
    assert first_path.exists()

    second = client.post(
        f"/api/v1/finance/transactions/{txn.id}/invoice",
        headers=admin_headers,
        files={"file": ("nota2.pdf", _make_pdf_bytes(), "application/pdf")},
    )
    assert second.status_code == status.HTTP_200_OK
    session.refresh(txn)
    assert not first_path.exists()
    assert Path(txn.invoice_file_path).exists()


def test_delete_invoice_clears_fields_and_removes_file(
    client: TestClient, admin_headers: dict, admin_user: User, expense_category: FinanceCategory, session: Session
):
    txn = FinancialTransaction(
        type=TransactionType.EXPENSE,
        category_id=expense_category.id,
        description="Nota fiscal",
        amount=99.0,
        transaction_date=date(2026, 4, 1),
        created_by_id=admin_user.id,
    )
    session.add(txn)
    session.commit()
    session.refresh(txn)

    client.post(
        f"/api/v1/finance/transactions/{txn.id}/invoice",
        headers=admin_headers,
        files={"file": ("nota.pdf", _make_pdf_bytes(), "application/pdf")},
    )
    session.refresh(txn)
    from pathlib import Path

    stored_path = Path(txn.invoice_file_path)
    assert stored_path.exists()

    resp = client.delete(
        f"/api/v1/finance/transactions/{txn.id}/invoice", headers=admin_headers
    )
    assert resp.status_code == status.HTTP_204_NO_CONTENT
    assert not stored_path.exists()

    session.refresh(txn)
    assert txn.invoice_file_path is None
    assert txn.invoice_file_url is None
    assert txn.invoice_file_size_bytes is None
    assert txn.invoice_mime_type is None


# -----------------------------------------------------------------------------
# Reporting Tests: Balance, Statement, Budget vs Actual
# -----------------------------------------------------------------------------


def test_cash_balance_computation(
    client: TestClient,
    admin_headers: dict,
    admin_user: User,
    income_category: FinanceCategory,
    expense_category: FinanceCategory,
    session: Session,
):
    session.add_all(
        [
            FinancialTransaction(
                type=TransactionType.INCOME,
                category_id=income_category.id,
                description="Receita 1",
                amount=1000.0,
                transaction_date=date(2026, 1, 10),
                created_by_id=admin_user.id,
            ),
            FinancialTransaction(
                type=TransactionType.EXPENSE,
                category_id=expense_category.id,
                description="Despesa 1",
                amount=400.0,
                transaction_date=date(2026, 1, 15),
                created_by_id=admin_user.id,
            ),
            # After the as_of date - should not count
            FinancialTransaction(
                type=TransactionType.INCOME,
                category_id=income_category.id,
                description="Receita futura",
                amount=999.0,
                transaction_date=date(2026, 3, 1),
                created_by_id=admin_user.id,
            ),
        ]
    )
    session.commit()

    resp = client.get(
        "/api/v1/finance/balance?as_of=2026-01-31", headers=admin_headers
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["as_of_date"] == "2026-01-31"
    assert data["total_income"] == 1000.0
    assert data["total_expense"] == 400.0
    assert data["balance"] == 600.0


def test_statement_reconciles_with_balance(
    client: TestClient,
    admin_headers: dict,
    admin_user: User,
    income_category: FinanceCategory,
    expense_category: FinanceCategory,
    session: Session,
):
    session.add_all(
        [
            FinancialTransaction(
                type=TransactionType.INCOME,
                category_id=income_category.id,
                description="Receita Jan",
                amount=1000.0,
                transaction_date=date(2026, 1, 5),
                created_by_id=admin_user.id,
            ),
            FinancialTransaction(
                type=TransactionType.EXPENSE,
                category_id=expense_category.id,
                description="Despesa Jan",
                amount=200.0,
                transaction_date=date(2026, 1, 20),
                created_by_id=admin_user.id,
            ),
            FinancialTransaction(
                type=TransactionType.INCOME,
                category_id=income_category.id,
                description="Receita Fev",
                amount=500.0,
                transaction_date=date(2026, 2, 10),
                created_by_id=admin_user.id,
            ),
        ]
    )
    session.commit()

    resp = client.get(
        "/api/v1/finance/statement?start_date=2026-01-01&end_date=2026-03-31",
        headers=admin_headers,
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()

    # 3 months present even though March has no transactions
    assert len(data["entries"]) == 3
    jan_entry = data["entries"][0]
    assert jan_entry["year"] == 2026
    assert jan_entry["month"] == 1
    assert jan_entry["income"] == 1000.0
    assert jan_entry["expense"] == 200.0
    assert jan_entry["net"] == 800.0

    march_entry = data["entries"][2]
    assert march_entry["income"] == 0.0
    assert march_entry["expense"] == 0.0

    balance_resp = client.get(
        "/api/v1/finance/balance?as_of=2026-03-31", headers=admin_headers
    )
    assert data["closing_balance"] == balance_resp.json()["balance"]


def test_budget_vs_actual_computed_live_from_transactions(
    client: TestClient,
    admin_headers: dict,
    admin_user: User,
    expense_category: FinanceCategory,
    session: Session,
):
    budget_line = BudgetLine(
        category_id=expense_category.id, fiscal_year=2026, planned_amount=1000.0
    )
    session.add(budget_line)
    session.add_all(
        [
            FinancialTransaction(
                type=TransactionType.EXPENSE,
                category_id=expense_category.id,
                description="Despesa 1",
                amount=300.0,
                transaction_date=date(2026, 2, 1),
                created_by_id=admin_user.id,
            ),
            FinancialTransaction(
                type=TransactionType.EXPENSE,
                category_id=expense_category.id,
                description="Despesa 2",
                amount=400.0,
                transaction_date=date(2026, 5, 1),
                created_by_id=admin_user.id,
            ),
            # Different year - should not count
            FinancialTransaction(
                type=TransactionType.EXPENSE,
                category_id=expense_category.id,
                description="Despesa ano passado",
                amount=999.0,
                transaction_date=date(2025, 12, 1),
                created_by_id=admin_user.id,
            ),
        ]
    )
    session.commit()

    resp = client.get(
        "/api/v1/finance/budget-vs-actual?fiscal_year=2026", headers=admin_headers
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    row = next(r for r in data["rows"] if r["category_id"] == str(expense_category.id))
    assert row["planned_amount"] == 1000.0
    assert row["executed_amount"] == 700.0
    assert row["variance_amount"] == -300.0
    assert row["variance_pct"] == pytest.approx(-30.0)
    assert row["transaction_count"] == 2

    # Adding a new transaction changes the executed amount on next read (never stored/stale)
    session.add(
        FinancialTransaction(
            type=TransactionType.EXPENSE,
            category_id=expense_category.id,
            description="Despesa 3",
            amount=100.0,
            transaction_date=date(2026, 6, 1),
            created_by_id=admin_user.id,
        )
    )
    session.commit()

    resp2 = client.get(
        "/api/v1/finance/budget-vs-actual?fiscal_year=2026", headers=admin_headers
    )
    row2 = next(
        r for r in resp2.json()["rows"] if r["category_id"] == str(expense_category.id)
    )
    assert row2["executed_amount"] == 800.0


def test_budget_vs_actual_includes_category_without_budget_line(
    client: TestClient,
    admin_headers: dict,
    admin_user: User,
    expense_category: FinanceCategory,
    session: Session,
):
    session.add(
        FinancialTransaction(
            type=TransactionType.EXPENSE,
            category_id=expense_category.id,
            description="Despesa sem orçamento",
            amount=50.0,
            transaction_date=date(2026, 1, 1),
            created_by_id=admin_user.id,
        )
    )
    session.commit()

    resp = client.get(
        "/api/v1/finance/budget-vs-actual?fiscal_year=2026", headers=admin_headers
    )
    row = next(
        r for r in resp.json()["rows"] if r["category_id"] == str(expense_category.id)
    )
    assert row["planned_amount"] == 0.0
    assert row["executed_amount"] == 50.0
    assert row["variance_pct"] is None


def test_category_transaction_drilldown_includes_invoice_url(
    client: TestClient,
    admin_headers: dict,
    admin_user: User,
    expense_category: FinanceCategory,
    session: Session,
):
    txn = FinancialTransaction(
        type=TransactionType.EXPENSE,
        category_id=expense_category.id,
        description="Com nota",
        amount=150.0,
        transaction_date=date(2026, 1, 1),
        created_by_id=admin_user.id,
    )
    session.add(txn)
    session.commit()
    session.refresh(txn)

    client.post(
        f"/api/v1/finance/transactions/{txn.id}/invoice",
        headers=admin_headers,
        files={"file": ("nota.pdf", _make_pdf_bytes(), "application/pdf")},
    )

    resp = client.get(
        f"/api/v1/finance/budget-vs-actual/{expense_category.id}/transactions?fiscal_year=2026",
        headers=admin_headers,
    )
    assert resp.status_code == status.HTTP_200_OK
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["invoice_file_url"] is not None
