import uuid
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models.role import Role
from app.models.user import User
from tests.conftest import make_user
from app.core.security import create_access_token, get_password_hash
from app.models.tenant import DEFAULT_TENANT_ID, UserTenantLink


def get_token(client, username, password):
    response = client.post(
        "/api/v1/auth/login", data={"username": username, "password": password}
    )
    return response.json()["access_token"]


def test_signup(client: TestClient, session: Session):
    signup_data = {
        "email": "newuser@test.com",
        "full_name": "New User",
        "password": "Password123!",
        "cpf": "22233344405",
    }
    response = client.post("/api/v1/auth/signup", json=signup_data)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "newuser@test.com"
    assert data["is_active"] is False
    assert "role" not in data
    assert data["roles"] == []

    # Verify in DB
    user = session.exec(select(User).where(User.email == "newuser@test.com")).first()
    assert user is not None
    assert user.is_active is False


def test_signup_duplicate_email(client: TestClient, normal_user):
    signup_data = {
        "email": normal_user.email,
        "full_name": "Duplicate User",
        "password": "Password123!",
        "cpf": "99988877714",
    }
    response = client.post("/api/v1/auth/signup", json=signup_data)
    assert response.status_code == 400
    assert "email already exists" in response.json()["detail"]


def test_me_endpoint(client: TestClient, admin_user):
    token = get_token(client, "admin", "test_admin_password")
    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["username"] == "admin"


def test_list_users_accessible_to_all_authenticated(
    client: TestClient, admin_user, normal_user
):
    """Test that the user list endpoint is accessible to all authenticated users."""
    admin_token = get_token(client, "admin", "test_admin_password")
    user_token = get_token(client, "user1", "test_user_password")

    # Admin can list
    response = client.get(
        "/api/v1/users/", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert len(response.json()) >= 2

    # Director can also list (needed to populate assignee dropdowns)
    response = client.get(
        "/api/v1/users/", headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == 200
    assert len(response.json()) >= 2


def test_update_user_status_and_role(client: TestClient, admin_user, session: Session):
    # Create an inactive user
    new_user = make_user(
        session,
        email="pending@test.com",
        full_name="Pending User",
        hashed_password="...",
        is_active=False,
        profile="DIRECTOR",
        cpf="12345678909",
    )
    session.add(new_user)
    session.commit()
    session.refresh(new_user)

    admin_token = get_token(client, "admin", "test_admin_password")

    # Activate user
    response = client.patch(
        f"/api/v1/users/{new_user.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"is_active": True},
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is True

    # Change the user's **roles**: the only field that widens anyone since
    # IAM F5 (APRAS-49 §8.3). `UserUpdate` carries no `role` any more.
    board = Role(name="Conselho")
    session.add(board)
    session.commit()
    response = client.patch(
        f"/api/v1/users/{new_user.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"role_ids": [str(board.id)]},
    )
    assert response.status_code == 200
    assert [row["name"] for row in response.json()["roles"]] == ["Conselho"]


def test_admin_cannot_deactivate_self(client: TestClient, admin_user):
    admin_token = get_token(client, "admin", "test_admin_password")

    response = client.patch(
        f"/api/v1/users/{admin_user.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"is_active": False},
    )
    assert response.status_code == 400
    assert "Administrators cannot deactivate themselves" in response.json()["detail"]


def test_an_administrator_cannot_change_their_own_role_ids(
    client: TestClient, admin_user
):
    """§8.5's narrowing: `role_ids` is the only thing that edits authority."""
    admin_token = get_token(client, "admin", "test_admin_password")

    response = client.patch(
        f"/api/v1/users/{admin_user.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"role_ids": []},
    )
    assert response.status_code == 400
    assert "Administrators cannot change their own roles" in response.json()["detail"]


def test_an_administrator_can_still_change_another_users_role_ids(
    client: TestClient, admin_user, normal_user, session: Session
):
    """The other half of §8.5: the guard is about *self*, nothing wider."""
    admin_token = get_token(client, "admin", "test_admin_password")
    board = Role(name="Conselho Fiscal")
    session.add(board)
    session.commit()

    response = client.patch(
        f"/api/v1/users/{normal_user.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"role_ids": [str(board.id)]},
    )
    assert response.status_code == 200
    assert [row["name"] for row in response.json()["roles"]] == ["Conselho Fiscal"]


def test_list_users_with_noncanonical_stored_cpf_returns_200(
    client: TestClient, admin_user, session: Session
):
    """A previously-stored CPF that fails the check-digit algorithm must not
    crash UserRead serialization on GET /users/ (APRAS-30)."""
    bad_cpf_user = make_user(
        session,
        email="badcpf@test.com",
        full_name="Bad CPF User",
        hashed_password="...",
        profile="DIRECTOR",
        cpf="11111111111",
    )
    session.add(bad_cpf_user)
    session.commit()

    admin_token = get_token(client, "admin", "test_admin_password")
    response = client.get(
        "/api/v1/users/", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    emails = [u["email"] for u in response.json()]
    assert "badcpf@test.com" in emails


def test_update_user_with_noncanonical_stored_cpf_returns_200(
    client: TestClient, admin_user, session: Session
):
    """Updating an unrelated field on a user with a non-canonical stored CPF
    must not crash UserRead serialization on PATCH /users/{id} (APRAS-30)."""
    bad_cpf_user = make_user(
        session,
        email="badcpf2@test.com",
        full_name="Bad CPF User 2",
        hashed_password="...",
        profile="DIRECTOR",
        cpf="22222222222",
    )
    session.add(bad_cpf_user)
    session.commit()
    session.refresh(bad_cpf_user)

    admin_token = get_token(client, "admin", "test_admin_password")
    response = client.patch(
        f"/api/v1/users/{bad_cpf_user.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"full_name": "Renamed"},
    )
    assert response.status_code == 200
    assert response.json()["full_name"] == "Renamed"


def test_update_user_with_invalid_cpf_in_body_still_rejected(
    client: TestClient, admin_user, normal_user
):
    """Write-path CPF validation on PATCH /users/{id} is unaffected by the
    UserRead read-path fix (APRAS-30)."""
    admin_token = get_token(client, "admin", "test_admin_password")
    response = client.patch(
        f"/api/v1/users/{normal_user.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"cpf": "11111111111"},
    )
    assert response.status_code == 422


def test_update_user_with_short_cpf_in_body_still_rejected(
    client: TestClient, admin_user, normal_user
):
    """A CPF with fewer than 11 digits is still rejected by UserUpdate's
    validator on PATCH /users/{id} (APRAS-30)."""
    admin_token = get_token(client, "admin", "test_admin_password")
    response = client.patch(
        f"/api/v1/users/{normal_user.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"cpf": "12345"},
    )
    assert response.status_code == 422


def test_update_user_with_valid_cpf_in_body_accepted(
    client: TestClient, admin_user, normal_user
):
    """A well-formed, check-digit-valid CPF is accepted and normalized by
    UserUpdate's validator on PATCH /users/{id} (APRAS-30)."""
    admin_token = get_token(client, "admin", "test_admin_password")
    response = client.patch(
        f"/api/v1/users/{normal_user.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"cpf": "987.654.321-00"},
    )
    assert response.status_code == 200
    assert response.json()["cpf"] == "98765432100"


def test_signup_with_invalid_cpf_still_rejected(client: TestClient):
    """Write-path CPF validation on signup is unaffected by the UserRead
    read-path fix (APRAS-30)."""
    signup_data = {
        "email": "badcpfsignup@test.com",
        "full_name": "Bad Cpf Signup",
        "password": "Password123!",
        "cpf": "11111111111",
    }
    response = client.post("/api/v1/auth/signup", json=signup_data)
    assert response.status_code == 422


def test_signup_with_wrong_check_digit_cpf_still_rejected(client: TestClient):
    """CPF with the correct length/distinct digits but a wrong first check
    digit is still rejected by UserCreate's validator (APRAS-30)."""
    signup_data = {
        "email": "badcheckdigit@test.com",
        "full_name": "Bad Check Digit",
        "password": "Password123!",
        "cpf": "90700092900",
    }
    response = client.post("/api/v1/auth/signup", json=signup_data)
    assert response.status_code == 422


def test_signup_with_short_cpf_still_rejected(client: TestClient):
    """A CPF with fewer than 11 digits is still rejected by UserCreate's
    validator (APRAS-30)."""
    signup_data = {
        "email": "shortcpf@test.com",
        "full_name": "Short Cpf",
        "password": "Password123!",
        "cpf": "12345",
    }
    response = client.post("/api/v1/auth/signup", json=signup_data)
    assert response.status_code == 422


def test_a_dual_tenant_administrator_can_resubmit_their_own_acting_tenant_roles(
    client: TestClient, session: Session, tenant_b
):
    """S3: the self-guard compares **within the acting tenant**.

    `_assign_roles` only ever replaces the acting tenant's links and
    preserves the target's rows elsewhere, so "did the caller change their
    own roles?" is a question about one tenant. `db_user.roles` is a
    relationship load and is exempt from the ambient filter, so an unnarrowed
    comparison would 400 a dual-tenant administrator who resubmitted exactly
    their own acting-tenant ids — a no-op.
    """
    admin = make_user(
        session,
        profile="ADMINISTRATOR",
        id=uuid.uuid4(),
        email="dual-admin@test.com",
        full_name="Dual Admin",
        hashed_password=get_password_hash("test_admin_password"),
        cpf="15350946056",
    )
    # Ordinary roles on both sides: `assert_can_assign_roles` refuses the
    # four `SUPERUSER_ONLY_PERMISSIONS` to *every* author, superuser
    # included, so re-submitting `Administrador (papel)` would 403 for a
    # reason that has nothing to do with the self-guard under test.
    a_role = Role(name="Conselho A", permissions=["users:read"])
    b_role = Role(name="Conselho B", tenant_id=tenant_b.id)
    session.add(a_role)
    session.add(b_role)
    session.commit()
    admin.roles = [a_role, b_role]
    session.add(admin)
    session.add(UserTenantLink(user_id=admin.id, tenant_id=DEFAULT_TENANT_ID))
    session.add(UserTenantLink(user_id=admin.id, tenant_id=tenant_b.id))
    session.commit()

    headers = {
        "Authorization": f"Bearer {create_access_token(admin.id)}",
        "X-Tenant-Id": str(DEFAULT_TENANT_ID),
    }

    # A no-op in tenant A: exactly the ids they already hold *there*.
    noop = client.patch(
        f"/api/v1/users/{admin.id}",
        headers=headers,
        json={"role_ids": [str(a_role.id)]},
    )
    assert noop.status_code == 200, noop.text

    # The tenant-B membership is untouched by the acting-tenant write.
    session.expire_all()
    assert {role.id for role in session.get(User, admin.id).roles} == {
        a_role.id,
        b_role.id,
    }

    # And a real self-change in the acting tenant is still refused.
    other = Role(name="Zeladoria A")
    session.add(other)
    session.commit()
    refused = client.patch(
        f"/api/v1/users/{admin.id}",
        headers=headers,
        json={"role_ids": [str(other.id)]},
    )
    assert refused.status_code == 400
    assert "cannot change their own roles" in refused.json()["detail"]
