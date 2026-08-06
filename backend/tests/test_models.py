from uuid import uuid4

from app.models.enums import TaskPriority, TaskStatus, UserRole
from app.models.task import Task, TaskHistory
from app.models.user import User


def test_user_model_creation():
    """Test that a User model is created with correct field defaults."""
    user = User(
        email="testuser@test.com",
        hashed_password="hash",
        full_name="Test User",
        role=UserRole.DIRECTOR,
    )
    assert user.username == "testuser"
    assert user.role == UserRole.DIRECTOR
    assert user.is_active is True


def test_task_model_defaults():
    """Test that a Task model applies the correct status/priority defaults."""
    task = Task(
        title="New Task",
        created_by_id=uuid4(),
    )
    assert task.status == TaskStatus.PENDING
    assert task.priority == TaskPriority.MEDIUM
    assert task.created_at is not None


def test_task_history_model():
    """Test that a TaskHistory record stores field-change values correctly."""
    history = TaskHistory(
        task_id=uuid4(),
        changed_by_id=uuid4(),
        field_name="status",
        old_value="PENDING",
        new_value="IN_PROGRESS",
    )
    assert history.field_name == "status"
    assert history.old_value == "PENDING"
