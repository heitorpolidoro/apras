import pytest
from pydantic import ValidationError

from app.models.enums import TaskPriority, TaskStatus
from app.schemas.task import TaskCreate, TaskUpdate
from app.schemas.user import UserCreate, UserRead, UserUpdate


def test_task_create_validation():
    # Título é obrigatório
    with pytest.raises(ValidationError):
        TaskCreate(description="No title")

    # Enums válidos
    import uuid
    task = TaskCreate(title="Valid", priority=TaskPriority.HIGH, category_id=uuid.uuid4())
    assert task.priority == "HIGH"


def test_task_update_partial():
    # Update deve permitir apenas um campo
    update = TaskUpdate(status=TaskStatus.COMPLETED)
    assert update.status == TaskStatus.COMPLETED
    assert update.title is None


def test_user_create_accepts_request_without_profile_fields():
    """phone/address are optional and default to None on UserCreate."""
    user = UserCreate(
        email="noprofile@test.com",
        full_name="No Profile",
        password="Password123!",
        cpf="52998224725",
    )
    assert user.phone is None
    assert user.address is None


def test_user_create_accepts_request_with_profile_fields():
    """phone/address are accepted as free text on UserCreate."""
    user = UserCreate(
        email="withprofile@test.com",
        full_name="With Profile",
        password="Password123!",
        cpf="11144477735",
        phone="+55 11 91234-5678",
        address="Rua das Flores, 123",
    )
    assert user.phone == "+55 11 91234-5678"
    assert user.address == "Rua das Flores, 123"


def test_user_update_accepts_request_without_profile_fields():
    """phone/address remain optional (None) on UserUpdate."""
    update = UserUpdate(full_name="Renamed")
    assert update.phone is None
    assert update.address is None


def test_user_update_accepts_request_with_profile_fields():
    """phone/address are accepted as free text on UserUpdate."""
    update = UserUpdate(
        phone="+55 11 98888-0000",
        address="Av. Paulista, 1000",
    )
    assert update.phone == "+55 11 98888-0000"
    assert update.address == "Av. Paulista, 1000"


def test_user_read_serializes_profile_fields():
    """UserRead exposes phone/address when reading from a User model."""
    from app.models.user import User

    user = User(
        email="serialize@test.com",
        hashed_password="hash",
        full_name="Serialize Me",
        cpf="52998224725",
        phone="+55 11 91234-5678",
        address="Rua das Flores, 123",
    )
    read = UserRead.model_validate(user)
    assert read.phone == "+55 11 91234-5678"
    assert read.address == "Rua das Flores, 123"
    assert read.id == user.id
