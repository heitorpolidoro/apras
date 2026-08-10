import uuid

import pytest
from app.core.security import get_password_hash
from app.db import get_session
from app.main import app
from app.models.enums import UserRole
from app.models.user import User
from app.models.category import Category
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, StaticPool, create_engine

# Disable rate limiting for tests
app.state.limiter.enabled = False


@pytest.fixture(name="session")
def session_fixture():
    """Provide an isolated in-memory SQLite session for each test."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="client")
def client_fixture(session: Session):
    """Provide a FastAPI test client that uses the test session."""

    def get_session_override():
        """Override the DB session dependency with the test session."""
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="admin_user")
def admin_user_fixture(session: Session):
    """Create and persist an ADMINISTRATOR user for tests."""
    user = User(
        id=uuid.uuid4(),
        email="admin@test.com",
        full_name="Admin User",
        hashed_password=get_password_hash("test_admin_password"),
        role=UserRole.ADMINISTRATOR,
        cpf="52998224725",
    )
    session.add(user)
    session.commit()
    return user


@pytest.fixture(name="normal_user")
def normal_user_fixture(session: Session):
    """Create and persist a DIRECTOR user for tests."""
    user = User(
        id=uuid.uuid4(),
        email="user1@test.com",
        full_name="Normal User",
        hashed_password=get_password_hash("test_user_password"),
        role=UserRole.DIRECTOR,
        cpf="11144477735",
    )
    session.add(user)
    session.commit()
    return user


@pytest.fixture(name="default_category")
def default_category_fixture(session: Session):
    """Create and persist a default category for tests."""
    category = Category(
        name="General",
        color="#808080",
    )
    session.add(category)
    session.commit()
    return category
