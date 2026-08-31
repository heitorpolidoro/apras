import uuid

import pytest
from app.core.security import get_password_hash
from app.core.tenant_context import REQUEST_SCOPED_KEY
from app.db import get_session
from app.main import app
from app.models.enums import UserRole
from app.models.user import User
from app.models.category import Category
from app.models.tenant import (
    DEFAULT_TENANT_ID,
    DEFAULT_TENANT_NAME,
    Tenant,
    UserTenantLink,
)
from app.models.user_type import UserType
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


@pytest.fixture(name="default_tenant", autouse=True)
def default_tenant_fixture(session: Session):
    """Seed the well-known default tenant into every test database (APRAS-41).

    Autouse and depending only on `session`, so it runs before any other
    fixture that inserts rows. Every tenant-scoped model defaults its
    `tenant_id` to `DEFAULT_TENANT_ID`, so without this row the foreign key
    would have no target and joins would be meaningless. No other existing
    test module needs to know tenants exist.
    """
    tenant = Tenant(id=DEFAULT_TENANT_ID, name=DEFAULT_TENANT_NAME)
    session.add(tenant)
    session.commit()
    return tenant


@pytest.fixture(name="client")
def client_fixture(session: Session):
    """Provide a FastAPI test client that uses the test session."""

    def get_session_override():
        """Override the DB session dependency with the test session.

        The session is marked *request scoped* exactly as `app.db.get_session`
        does in production, so routes exercised here go through the same
        tenant resolution and the same fail-closed guard (APRAS-42 §8.4).
        Without it the new machinery would be dead code under test.
        """
        session.info[REQUEST_SCOPED_KEY] = True
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
    """Create and persist a DIRECTOR user for tests.

    Since DIRECTOR is subject to the UserType-based menu gate
    (`assert_menu_access`, see APRAS-8), this fixture also creates and
    assigns a UserType granting `allowed_menus: ["tasks", "categories"]`
    so `normal_user` carries forward the standing tasks/categories access
    it previously had unconditionally. Tests that need a user *without*
    menu access (to exercise the 403 path) should build one explicitly.
    """
    user_type = UserType(
        name="Normal User Type", allowed_menus=["tasks", "categories"]
    )
    session.add(user_type)
    session.commit()

    user = User(
        id=uuid.uuid4(),
        email="user1@test.com",
        full_name="Normal User",
        hashed_password=get_password_hash("test_user_password"),
        role=UserRole.DIRECTOR,
        cpf="11144477735",
        user_types=[user_type],
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


# ---------------------------------------------------------------------------
# Multi-tenant fixtures (APRAS-42 §8.4)
# ---------------------------------------------------------------------------


@pytest.fixture(name="tenant_b")
def tenant_b_fixture(session: Session):
    """A second, active tenant. Tenant A is always the default tenant."""
    tenant = Tenant(name="Condomínio B")
    session.add(tenant)
    session.commit()
    session.refresh(tenant)
    return tenant


@pytest.fixture(name="raw_session")
def raw_session_fixture(session: Session):
    """An unfiltered, unstamped Session — the seeding/inspection channel.

    Deliberately a *separate* `Session` on the same engine, never a request
    session: it carries neither `REQUEST_SCOPED_KEY` nor an acting tenant, so
    it behaves exactly like `app/seed.py` or Alembic. Tenant-B rows enter its
    identity map and never a request's, which is what makes the by-id 404s of
    the isolation suite real rather than an artefact of a shared session.

    It must commit before any API call, and `expire_all()` before re-reading a
    row an API request wrote.
    """
    with Session(session.get_bind()) as raw:
        yield raw


@pytest.fixture(name="tenant_client")
def tenant_client_fixture(session: Session):
    """A TestClient that gives every request its own `Session`.

    This is precisely what production does (`app.db.get_session` opens a new
    `Session` per request), and it is what makes a cross-tenant `session.get`
    issue a real filtered SELECT instead of hitting a shared identity map.
    Every yielded session is recorded on `client.request_sessions` (and its
    id on `client.request_session_ids`) so the harness contract itself is
    testable. The list holds a *strong* reference on purpose: `id()` is only
    unique among live objects, and a request session dropped at the end of its
    request frees its address for the next one to reuse — which made the
    harness self-test read two distinct sessions as one shared session.
    """
    engine = session.get_bind()
    request_sessions: list[Session] = []
    session_ids: list[int] = []

    def get_session_override():
        with Session(engine) as request_session:
            request_session.info[REQUEST_SCOPED_KEY] = True
            request_sessions.append(request_session)
            session_ids.append(id(request_session))
            yield request_session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    client.request_sessions = request_sessions
    client.request_session_ids = session_ids
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="user_in_tenant_a")
def user_in_tenant_a_fixture(session: Session):
    """An ADMINISTRATOR whose only membership is the default tenant (A).

    Administrator so RBAC never masks a tenant leak with a 403; a single
    membership so the header-less resolution ladder lands on tenant A.
    Global vision is a property of *sending* `X-Tenant-Id`, not of the role.
    """
    user = User(
        id=uuid.uuid4(),
        email="a-admin@test.com",
        full_name="Tenant A Admin",
        hashed_password=get_password_hash("password"),
        role=UserRole.ADMINISTRATOR,
        cpf="39053344705",
    )
    session.add(user)
    session.commit()
    session.add(UserTenantLink(user_id=user.id, tenant_id=DEFAULT_TENANT_ID))
    session.commit()
    return user


@pytest.fixture(name="user_in_tenant_b")
def user_in_tenant_b_fixture(session: Session, tenant_b: Tenant):
    """An ADMINISTRATOR whose only membership is tenant B."""
    user = User(
        id=uuid.uuid4(),
        email="b-admin@test.com",
        full_name="Tenant B Admin",
        hashed_password=get_password_hash("password"),
        role=UserRole.ADMINISTRATOR,
        cpf="16899535009",
    )
    session.add(user)
    session.commit()
    session.add(UserTenantLink(user_id=user.id, tenant_id=tenant_b.id))
    session.commit()
    return user


@pytest.fixture(name="member_admin")
def member_admin_fixture(session: Session, tenant_b: Tenant):
    """An ADMINISTRATOR that is a member of both tenants.

    Must send `X-Tenant-Id`: with two memberships the header-less ladder is
    deliberately a 400 rather than an arbitrary pick.
    """
    user = User(
        id=uuid.uuid4(),
        email="both-admin@test.com",
        full_name="Both Tenants Admin",
        hashed_password=get_password_hash("password"),
        role=UserRole.ADMINISTRATOR,
        cpf="15350946056",
    )
    session.add(user)
    session.commit()
    session.add(UserTenantLink(user_id=user.id, tenant_id=DEFAULT_TENANT_ID))
    session.add(UserTenantLink(user_id=user.id, tenant_id=tenant_b.id))
    session.commit()
    return user
