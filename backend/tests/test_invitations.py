"""The administrator invitation flow (APRAS-71).

Four routes: two superuser-only (issue, list) and two public ones (preview,
accept). The invited person is the condominium's **administrator in the
system** -- `user_tenant_link.is_tenant_admin`: a system role, not one of the
condominium's own elected offices, whose name appears nowhere here.

The raw token is never stored and never returned by any route: the table
holds its SHA-256 hex only. These tests obtain a token the same way the
invitee does -- by reading the accept URL the sender printed, since the suite
runs with `RESEND_API_KEY` unset (D11).
"""

import re
import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core import clock
from app.core.permissions import ROUTE_PERMISSIONS, UNGUARDED_ROUTES
from app.core.tenant_context import TENANT_SCOPED_MODELS
from app.models.role_link import UserRoleLink
from app.models.tenant import DEFAULT_TENANT_ID, Tenant, UserTenantLink
from app.models.tenant_invitation import TenantInvitation
from app.models.user import User
from app.services.invitation_service import InvitationService
from tests.subscription_helpers import (
    TENANT_A,
    auth,
    make_superuser,
    make_tenant_admin,
    new_user,
)
from tests.test_tenant_route_scope import GLOBAL_ROUTES

INVITATIONS = "/api/v1/invitations"
PREVIEW = "/api/v1/invitations/preview"
ACCEPT = "/api/v1/invitations/accept"

INVITATION_ROUTES = (
    ("POST", "/api/v1/invitations"),
    ("GET", "/api/v1/invitations"),
    ("POST", "/api/v1/invitations/preview"),
    ("POST", "/api/v1/invitations/accept"),
)

_ACCEPT_URL = re.compile(r"/invite\?token=(\S+)")


@pytest.fixture(name="superuser")
def superuser_fixture(session: Session):
    return make_superuser(session)


def printed_token(capsys) -> str:
    """The raw token, read out of the accept URL the sender printed (D11)."""
    out = capsys.readouterr().out
    match = _ACCEPT_URL.search(out)
    assert match is not None, f"no accept URL was printed:\n{out}"
    return match.group(1)


def issue(
    client: TestClient, superuser: User, *, email: str, tenant_id=TENANT_A, **extra
):
    return client.post(
        INVITATIONS,
        json={"tenant_id": str(tenant_id), "email": email, **extra},
        headers=auth(superuser),
    )


def seed_invitation(
    session: Session,
    *,
    invited_by: User,
    email: str = "convidada@example.com",
    tenant_id=TENANT_A,
    expires_in: timedelta = timedelta(hours=1),
    accepted: bool = False,
) -> tuple[TenantInvitation, str]:
    """An invitation row written directly, with its raw token handed back.

    The only way to obtain a *past* `expires_at` or an already-consumed row
    without waiting or replaying, and the reason the hashing lives in a
    service function the test can call.
    """
    raw = InvitationService.new_token()
    now = clock.db_now()
    invitation = TenantInvitation(
        tenant_id=tenant_id,
        email=email,
        token_hash=InvitationService.hash_token(raw),
        expires_at=now + expires_in,
        accepted_at=now if accepted else None,
        invited_by_user_id=invited_by.id,
    )
    session.add(invitation)
    session.commit()
    session.refresh(invitation)
    return invitation, raw


def only_invitation(session: Session) -> TenantInvitation:
    session.expire_all()
    rows = session.exec(select(TenantInvitation)).all()
    assert len(rows) == 1
    return rows[0]


# ---------------------------------------------------------------------------
# Registry: four unguarded, global routes and no catalogue permission (D6)
# ---------------------------------------------------------------------------


def test_the_four_routes_are_unguarded_global_and_map_to_no_permission():
    """D6: superuser-only or public, so none of them mints a catalogue string.

    Consequence, checkable in one line: `tests/data/parity_matrix_baseline.json`
    gains no cell and needs no additive companion.
    """
    for key in INVITATION_ROUTES:
        assert key in UNGUARDED_ROUTES, key
        assert key in GLOBAL_ROUTES, key
        assert key not in ROUTE_PERMISSIONS, key


def test_the_invitation_table_is_not_a_tenant_scoped_entity():
    """Like `user_tenant_link`, its `tenant_id` names a tenant from outside.

    It is issued by a superuser on a route with no acting tenant and consumed
    by an anonymous caller, so the column is a reference and not a
    request-scoping key. Were it discovered as scoped, both public routes
    would read nothing at all.
    """
    assert TenantInvitation not in TENANT_SCOPED_MODELS
    assert "tenant_invitation" not in {m.__tablename__ for m in TENANT_SCOPED_MODELS}


# ---------------------------------------------------------------------------
# 1. Issuance
# ---------------------------------------------------------------------------


def test_superuser_issuance_stores_a_hash_and_returns_no_token(
    tenant_client: TestClient, session: Session, superuser, capsys
):
    response = issue(tenant_client, superuser, email="  Nova@Example.COM ")

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "nova@example.com"
    assert body["tenant_id"] == str(TENANT_A)
    assert body["accepted_at"] is None
    assert "token" not in body
    assert "token_hash" not in body

    raw = printed_token(capsys)
    invitation = only_invitation(session)
    assert re.fullmatch(r"[0-9a-f]{64}", invitation.token_hash)
    assert invitation.token_hash == InvitationService.hash_token(raw)
    assert raw not in response.text
    assert invitation.expires_at > clock.db_now()


def test_issuance_refuses_a_tenant_admin_a_plain_user_and_an_anonymous_caller(
    tenant_client: TestClient, session: Session
):
    tenant_admin = make_tenant_admin(session)
    plain = new_user(session, "GUEST", is_superuser=False)

    assert issue(tenant_client, tenant_admin, email="a@example.com").status_code == 403
    assert issue(tenant_client, plain, email="b@example.com").status_code == 403

    anonymous = tenant_client.post(
        INVITATIONS, json={"tenant_id": str(TENANT_A), "email": "c@example.com"}
    )
    assert anonymous.status_code == 401
    assert session.exec(select(TenantInvitation)).all() == []


def test_issuance_for_an_unknown_tenant_is_404(tenant_client: TestClient, superuser):
    response = issue(
        tenant_client, superuser, email="a@example.com", tenant_id=uuid.uuid4()
    )

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# 2. Re-issuing supersedes (D4)
# ---------------------------------------------------------------------------


def test_reissuing_expires_the_previous_invitation(
    tenant_client: TestClient, session: Session, superuser, capsys
):
    assert issue(tenant_client, superuser, email="dupla@example.com").status_code == 201
    first = printed_token(capsys)

    assert issue(tenant_client, superuser, email="dupla@example.com").status_code == 201
    second = printed_token(capsys)

    assert first != second
    session.expire_all()
    rows = session.exec(
        select(TenantInvitation).order_by(TenantInvitation.created_at)
    ).all()
    assert len(rows) == 2
    superseded = next(
        row for row in rows if row.token_hash == InvitationService.hash_token(first)
    )
    assert superseded.expires_at <= clock.db_now()

    stale = tenant_client.post(PREVIEW, json={"token": first})
    assert stale.status_code == 410
    live = tenant_client.post(PREVIEW, json={"token": second})
    assert live.status_code == 200


# ---------------------------------------------------------------------------
# 3-4. Preview, and the three distinguishable failures (D7)
# ---------------------------------------------------------------------------


def test_preview_returns_the_condominium_and_the_inviter(
    tenant_client: TestClient, session: Session, superuser, capsys
):
    tenant = session.get(Tenant, DEFAULT_TENANT_ID)
    issue(tenant_client, superuser, email="convidada@example.com")
    raw = printed_token(capsys)

    response = tenant_client.post(PREVIEW, json={"token": raw})

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "convidada@example.com"
    assert body["tenant_name"] == tenant.name
    assert body["tenant_slug"] == tenant.slug
    assert body["invited_by_name"] == superuser.full_name
    assert body["account_exists"] is False
    assert "token" not in body


@pytest.mark.parametrize("route", [PREVIEW, ACCEPT])
def test_unknown_expired_and_consumed_are_404_410_and_409(
    tenant_client: TestClient, session: Session, superuser, route
):
    expired, expired_raw = seed_invitation(
        session,
        invited_by=superuser,
        email="expirada@example.com",
        expires_in=timedelta(hours=-1),
    )
    used, used_raw = seed_invitation(
        session,
        invited_by=superuser,
        email="usada@example.com",
        accepted=True,
    )

    unknown = tenant_client.post(route, json={"token": InvitationService.new_token()})
    gone = tenant_client.post(route, json={"token": expired_raw})
    consumed = tenant_client.post(route, json={"token": used_raw})

    assert unknown.status_code == 404
    assert gone.status_code == 410
    assert consumed.status_code == 409
    for response, invited in (
        (unknown, None),
        (gone, expired.email),
        (consumed, used.email),
    ):
        assert "detail" in response.json()
        if invited is not None:
            assert invited not in response.text


# ---------------------------------------------------------------------------
# 5-7. Accepting into a new account (D9)
# ---------------------------------------------------------------------------


def valid_cpf(seed: int) -> str:
    """A check-digit-valid CPF derived from `seed` (the `matrix_world` recipe).

    The accept body goes through the very validators `UserCreate` enforces,
    so `subscription_helpers.next_cpf` -- a zero-padded counter with no valid
    check digits -- is not usable here. Deriving keeps the module free of
    magic strings and free of collisions.
    """
    base = f"{seed:09d}"
    total = sum(int(base[i]) * (10 - i) for i in range(9))
    d1 = 0 if (total % 11) < 2 else 11 - (total % 11)
    nine = base + str(d1)
    total = sum(int(nine[i]) * (11 - i) for i in range(10))
    d2 = 0 if (total % 11) < 2 else 11 - (total % 11)
    return nine + str(d2)


#: A password `UserCreate` accepts: 8+ characters, a letter, a digit, a symbol.
STRONG_PASSWORD = "Senha-Forte1!"


def accept_body(token: str, **overrides) -> dict:
    return {
        "token": token,
        "full_name": "Nova Administradora",
        "cpf": valid_cpf(701),
        "password": STRONG_PASSWORD,
        **overrides,
    }


def test_accept_creates_an_active_administrator_with_one_membership(
    tenant_client: TestClient, session: Session, superuser, capsys
):
    issue(tenant_client, superuser, email="nova@example.com")
    raw = printed_token(capsys)

    response = tenant_client.post(ACCEPT, json=accept_body(raw))

    assert response.status_code == 201
    token = response.json()["access_token"]
    assert response.json()["token_type"] == "bearer"

    session.expire_all()
    created = session.exec(select(User).where(User.email == "nova@example.com")).one()
    assert created.is_active is True
    assert created.full_name == "Nova Administradora"

    links = session.exec(
        select(UserTenantLink).where(UserTenantLink.user_id == created.id)
    ).all()
    assert len(links) == 1
    assert links[0].tenant_id == TENANT_A
    assert links[0].is_tenant_admin is True

    role_links = session.exec(
        select(UserRoleLink).where(UserRoleLink.user_id == created.id)
    ).all()
    assert role_links == []

    invitation = only_invitation(session)
    assert invitation.accepted_at is not None
    assert invitation.accepted_user_id == created.id

    me = tenant_client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert me.status_code == 200
    assert me.json()["email"] == "nova@example.com"


def test_accepting_twice_is_409_and_writes_nothing_the_second_time(
    tenant_client: TestClient, session: Session, superuser, capsys
):
    issue(tenant_client, superuser, email="nova@example.com")
    raw = printed_token(capsys)

    assert tenant_client.post(ACCEPT, json=accept_body(raw)).status_code == 201

    session.expire_all()
    users_before = len(session.exec(select(User)).all())
    links_before = len(session.exec(select(UserTenantLink)).all())

    replay = tenant_client.post(ACCEPT, json=accept_body(raw))

    assert replay.status_code == 409
    session.expire_all()
    assert len(session.exec(select(User)).all()) == users_before
    assert len(session.exec(select(UserTenantLink)).all()) == links_before


def test_the_new_account_branch_refuses_a_body_missing_a_field(
    tenant_client: TestClient, session: Session, superuser, capsys
):
    """422, and nothing consumed: the three fields are optional in the schema
    only because the existing-account branch ignores them (D8)."""
    issue(tenant_client, superuser, email="nova@example.com")
    raw = printed_token(capsys)

    response = tenant_client.post(ACCEPT, json={"token": raw, "cpf": valid_cpf(702)})

    assert response.status_code == 422
    assert only_invitation(session).accepted_at is None
    session.expire_all()
    assert (
        session.exec(select(User).where(User.email == "nova@example.com")).all() == []
    )


def test_an_expired_token_creates_no_account(
    tenant_client: TestClient, session: Session, superuser
):
    _invitation, raw = seed_invitation(
        session,
        invited_by=superuser,
        email="tarde@example.com",
        expires_in=timedelta(hours=-1),
    )
    before = len(session.exec(select(User)).all())

    response = tenant_client.post(ACCEPT, json=accept_body(raw))

    assert response.status_code == 410
    session.expire_all()
    assert len(session.exec(select(User)).all()) == before


def test_a_duplicate_cpf_is_409_and_consumes_nothing(
    tenant_client: TestClient, session: Session, superuser, capsys
):
    existing = new_user(session, "GUEST", is_superuser=False)
    existing.cpf = valid_cpf(703)
    session.add(existing)
    session.commit()
    issue(tenant_client, superuser, email="nova@example.com")
    raw = printed_token(capsys)

    response = tenant_client.post(ACCEPT, json=accept_body(raw, cpf=existing.cpf))

    assert response.status_code == 409
    invitation = only_invitation(session)
    assert invitation.accepted_at is None
    assert invitation.accepted_user_id is None
    session.expire_all()
    assert (
        session.exec(select(User).where(User.email == "nova@example.com")).all() == []
    )


# ---------------------------------------------------------------------------
# 8. An email that already has an account (D8)
# ---------------------------------------------------------------------------


def test_an_existing_account_is_linked_and_gets_no_session(
    tenant_client: TestClient, session: Session, superuser, tenant_b: Tenant, capsys
):
    existing = new_user(session, "GUEST", is_superuser=False)
    session.add(UserTenantLink(user_id=existing.id, tenant_id=tenant_b.id))
    session.commit()
    password_before = existing.hashed_password
    users_before = len(session.exec(select(User)).all())

    issue(tenant_client, superuser, email=existing.email)
    raw = printed_token(capsys)

    preview = tenant_client.post(PREVIEW, json={"token": raw})
    assert preview.status_code == 200
    assert preview.json()["account_exists"] is True

    response = tenant_client.post(ACCEPT, json=accept_body(raw))

    assert response.status_code == 200
    body = response.json()
    assert body["account_exists"] is True
    assert body["email"] == existing.email
    for credential in ("access_token", "refresh_token", "token"):
        assert credential not in body
    assert "set-cookie" not in {name.lower() for name in response.headers}

    session.expire_all()
    assert len(session.exec(select(User)).all()) == users_before
    reloaded = session.get(User, existing.id)
    assert reloaded.hashed_password == password_before
    assert reloaded.full_name != "Nova Administradora"

    links = {
        link.tenant_id: link
        for link in session.exec(
            select(UserTenantLink).where(UserTenantLink.user_id == existing.id)
        ).all()
    }
    assert set(links) == {TENANT_A, tenant_b.id}
    assert links[TENANT_A].is_tenant_admin is True
    assert links[tenant_b.id].is_tenant_admin is False
    assert only_invitation(session).accepted_user_id == existing.id


# ---------------------------------------------------------------------------
# 10. The superuser list
# ---------------------------------------------------------------------------


def test_the_list_returns_a_tenants_invitations_newest_first(
    tenant_client: TestClient, session: Session, superuser, tenant_b: Tenant
):
    older, _ = seed_invitation(session, invited_by=superuser, email="um@example.com")
    newer, _ = seed_invitation(session, invited_by=superuser, email="dois@example.com")
    older.created_at = clock.db_now() - timedelta(days=1)
    session.add(older)
    session.commit()
    seed_invitation(
        session, invited_by=superuser, email="outro@example.com", tenant_id=tenant_b.id
    )

    everything = tenant_client.get(INVITATIONS, headers=auth(superuser))
    scoped = tenant_client.get(
        INVITATIONS, params={"tenant_id": str(TENANT_A)}, headers=auth(superuser)
    )

    assert everything.status_code == 200
    assert len(everything.json()) == 3
    assert scoped.status_code == 200
    assert [row["email"] for row in scoped.json()] == [newer.email, older.email]
    assert "token_hash" not in scoped.json()[0]


def test_the_list_refuses_a_non_superuser(tenant_client: TestClient, session: Session):
    tenant_admin = make_tenant_admin(session)

    response = tenant_client.get(INVITATIONS, headers=auth(tenant_admin))

    assert response.status_code == 403
    assert tenant_client.get(INVITATIONS).status_code == 401


# ---------------------------------------------------------------------------
# 11. The account this path mints is the account signup would accept
# ---------------------------------------------------------------------------
#
# Both public and superuser entry points share `UserCreate`'s validators
# (`app/schemas/user.py`): `EmailStr`, the CPF check digits *and* their
# normalisation to 11 digits, and the password floor of 8 characters with a
# letter, a digit and a symbol. Without the normalisation the D9 duplicate-CPF
# 409 does not fire at all, because signup stores digits and a typed
# "529.982.247-25" would never equal them.


def test_issuance_refuses_a_malformed_email_and_writes_no_row(
    tenant_client: TestClient, session: Session, superuser
):
    response = issue(tenant_client, superuser, email="not-an-email")

    assert response.status_code == 422
    session.expire_all()
    assert session.exec(select(TenantInvitation)).all() == []


def test_issuance_refuses_a_malformed_email_before_printing_any_link(
    tenant_client: TestClient, superuser, capsys
):
    """No token is minted for an address no mail can reach."""
    issue(tenant_client, superuser, email="quem@@example..com")

    assert "[INVITE]" not in capsys.readouterr().out


def test_accept_normalises_a_formatted_cpf_to_the_digits_signup_stores(
    tenant_client: TestClient, session: Session, superuser, capsys
):
    issue(tenant_client, superuser, email="nova@example.com")
    raw = printed_token(capsys)

    response = tenant_client.post(ACCEPT, json=accept_body(raw, cpf="529.982.247-25"))

    assert response.status_code == 201
    session.expire_all()
    created = session.exec(select(User).where(User.email == "nova@example.com")).one()
    assert created.cpf == "52998224725"


def test_the_same_cpf_in_two_spellings_is_one_person_and_the_second_is_409(
    tenant_client: TestClient, session: Session, superuser, capsys
):
    """The reviewer's reproduction: two formats, two accounts, one person."""
    issue(tenant_client, superuser, email="primeira@example.com")
    first = printed_token(capsys)
    assert (
        tenant_client.post(
            ACCEPT, json=accept_body(first, cpf="529.982.247-25")
        ).status_code
        == 201
    )

    issue(tenant_client, superuser, email="segunda@example.com")
    second = printed_token(capsys)
    response = tenant_client.post(ACCEPT, json=accept_body(second, cpf="52998224725"))

    assert response.status_code == 409
    session.expire_all()
    holders = session.exec(select(User).where(User.cpf == "52998224725")).all()
    assert len(holders) == 1
    assert (
        session.exec(select(User).where(User.email == "segunda@example.com")).all()
        == []
    )


@pytest.mark.parametrize(
    "cpf",
    ["12345678900", "529.982.247-24", "00000000000", "5299822472"],
    ids=["bad-check-digits", "bad-check-digits-formatted", "repeated", "too-short"],
)
def test_accept_refuses_a_cpf_signup_would_refuse(
    tenant_client: TestClient, session: Session, superuser, capsys, cpf
):
    issue(tenant_client, superuser, email="nova@example.com")
    raw = printed_token(capsys)

    response = tenant_client.post(ACCEPT, json=accept_body(raw, cpf=cpf))

    assert response.status_code == 422
    assert only_invitation(session).accepted_at is None
    session.expire_all()
    assert (
        session.exec(select(User).where(User.email == "nova@example.com")).all() == []
    )


@pytest.mark.parametrize(
    "password",
    ["x", "curta1!", "semdigitos!", "semsimbolo1", "12345678!"],
    ids=["one-char", "seven-chars", "no-digit", "no-symbol", "no-letter"],
)
def test_accept_refuses_a_password_signup_would_refuse(
    tenant_client: TestClient, session: Session, superuser, capsys, password
):
    """A one-character password on a privileged account was the live defect."""
    issue(tenant_client, superuser, email="nova@example.com")
    raw = printed_token(capsys)

    response = tenant_client.post(ACCEPT, json=accept_body(raw, password=password))

    assert response.status_code == 422
    assert only_invitation(session).accepted_at is None
    session.expire_all()
    assert (
        session.exec(select(User).where(User.email == "nova@example.com")).all() == []
    )


def test_a_row_carrying_a_malformed_email_still_mints_no_account(
    tenant_client: TestClient, session: Session, superuser
):
    """The service is the second gate, not only the schema.

    `EmailStr` on `InvitationCreate` means no route can write such a row, so
    the only way to reach this is to write one directly -- which is exactly
    what a future caller of `InvitationService.issue` would do. The account
    is still not created.
    """
    _invitation, raw = seed_invitation(
        session, invited_by=superuser, email="not-an-email"
    )

    response = tenant_client.post(ACCEPT, json=accept_body(raw))

    assert response.status_code == 422
    # The refusal names the field, never the value: D7's no-enumeration rule
    # holds here too.
    assert "not-an-email" not in response.text
    assert only_invitation(session).accepted_at is None
    session.expire_all()
    assert session.exec(select(User).where(User.email == "not-an-email")).all() == []
