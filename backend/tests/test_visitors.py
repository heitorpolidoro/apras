"""Unit and integration tests for Visitor master profile management."""

import uuid
import pytest
from app.core.exceptions import VisitorNotFoundError
from app.models.enums import UserRole
from app.models.user import User
from app.models.visitor import Visitor
from app.schemas.visitor import VisitorCreate, VisitorUpdate
from app.services.visitor_service import VisitorService
from fastapi.testclient import TestClient
from sqlmodel import Session


def test_create_visitor_with_valid_cpf(session: Session):
    visitor_in = VisitorCreate(
        full_name="Carlos Silva",
        cpf="529.982.247-25",
        rg="12.345.678-9",
        phone="(11) 98765-4321",
        company_name="Tech Services",
        vehicle_plate="ABC-1234",
        vehicle_model="Civic",
        notes="Electrician",
    )
    visitor = VisitorService.create_visitor(session, visitor_in)

    assert visitor.id is not None
    assert visitor.full_name == "Carlos Silva"
    assert visitor.cpf == "52998224725"  # Normalized to digits
    assert visitor.company_name == "Tech Services"
    assert visitor.vehicle_plate == "ABC-1234"


def test_create_visitor_invalid_cpf_raises_validation_error():
    with pytest.raises(ValueError, match="Invalid CPF"):
        VisitorCreate(
            full_name="Bad CPF Visitor",
            cpf="111.111.111-11",
        )

    with pytest.raises(ValueError, match="CPF must have exactly 11 digits"):
        VisitorCreate(
            full_name="Short CPF Visitor",
            cpf="12345",
        )


def test_create_visitor_without_cpf(session: Session):
    visitor_in = VisitorCreate(
        full_name="Maria Santos",
        company_name="Paint Co",
    )
    visitor = VisitorService.create_visitor(session, visitor_in)
    assert visitor.id is not None
    assert visitor.cpf is None


def test_get_and_update_visitor(session: Session):
    visitor = VisitorService.create_visitor(
        session, VisitorCreate(full_name="Joao Souza", phone="11999999999")
    )
    fetched = VisitorService.get_visitor_by_id(session, visitor.id)
    assert fetched.id == visitor.id

    updated = VisitorService.update_visitor(
        session, visitor.id, VisitorUpdate(notes="Updated notes", phone="11888888888")
    )
    assert updated.notes == "Updated notes"
    assert updated.phone == "11888888888"


def test_get_visitor_not_found_raises_error(session: Session):
    with pytest.raises(VisitorNotFoundError):
        VisitorService.get_visitor_by_id(session, uuid.uuid4())


def test_search_visitors(session: Session):
    VisitorService.create_visitor(
        session,
        VisitorCreate(full_name="Roberto Santos", cpf="52998224725", company_name="Alfa Plumbing"),
    )
    VisitorService.create_visitor(
        session,
        VisitorCreate(full_name="Ana Oliveira", vehicle_plate="XYZ-9876", company_name="Beta Construction"),
    )

    results, total = VisitorService.search_visitors(session, q="Santos")
    assert total == 1
    assert results[0].full_name == "Roberto Santos"

    results_plate, total_plate = VisitorService.search_visitors(session, q="XYZ-9876")
    assert total_plate == 1
    assert results_plate[0].full_name == "Ana Oliveira"

    results_cpf, total_cpf = VisitorService.search_visitors(session, q="52998224725")
    assert total_cpf == 1
    assert results_cpf[0].full_name == "Roberto Santos"


def test_api_visitor_crud(client: TestClient, admin_user: User):
    from app.core.security import create_access_token
    token = create_access_token(admin_user.id)
    headers = {"Authorization": f"Bearer {token}"}

    # Create
    create_payload = {
        "full_name": "Pedro Lima",
        "cpf": "529.982.247-25",
        "company_name": "Services Inc",
        "vehicle_plate": "FFF-5555",
    }
    res_create = client.post("/api/v1/visitors", json=create_payload, headers=headers)
    assert res_create.status_code == 201
    v_data = res_create.json()
    v_id = v_data["id"]
    assert v_data["cpf"] == "52998224725"

    # List & Search
    res_list = client.get("/api/v1/visitors?q=Pedro", headers=headers)
    assert res_list.status_code == 200
    assert res_list.json()["total"] == 1

    # Get by ID
    res_get = client.get(f"/api/v1/visitors/{v_id}", headers=headers)
    assert res_get.status_code == 200
    assert res_get.json()["full_name"] == "Pedro Lima"

    # Update
    res_put = client.put(f"/api/v1/visitors/{v_id}", json={"notes": "Vip guest"}, headers=headers)
    assert res_put.status_code == 200
    assert res_put.json()["notes"] == "Vip guest"
