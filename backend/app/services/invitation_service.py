"""Administrator invitations (APRAS-71 §6).

In the shape of :class:`~app.services.plan_service.PlanService`: a
module-level class of ``@staticmethod``s taking ``session=``. It owns the
token, its hash, the supersede rule and the acceptance transaction; the
router owns nothing but the HTTP shape.

The invited person becomes the condominium's **administrator in the
system** -- ``user_tenant_link.is_tenant_admin``. That is a system role, not
one of the condominium's own elected offices, which this flow never grants.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta
from typing import TYPE_CHECKING

from pydantic import ValidationError
from sqlmodel import Session, select

from app.core import clock, security
from app.core.config import settings
from app.core.exceptions import (
    InvitationAlreadyUsedError,
    InvitationCpfConflictError,
    InvitationExpiredError,
    InvitationIncompleteError,
    InvitationInvalidAccountError,
    InvitationNotFoundError,
    TenantNotFoundError,
)
from app.models.tenant import Tenant, UserTenantLink
from app.models.tenant_invitation import TenantInvitation
from app.models.user import User
from app.schemas.user import UserCreate

if TYPE_CHECKING:  # pragma: no cover
    from uuid import UUID

#: ``secrets.token_urlsafe(32)`` is 32 random bytes -- 256 bits of entropy,
#: which is what makes the token unguessable and therefore not an enumerable
#: identifier (D1, D7).
_TOKEN_BYTES = 32


def _first_error(exc: ValidationError) -> str:
    """The first pydantic complaint, as one line for the 422 body."""
    first = exc.errors()[0]
    field = ".".join(str(part) for part in first["loc"]) or "body"
    return f"{field}: {first['msg']}"


class InvitationService:
    """Issue, list, resolve and accept administrator invitations."""

    # -- the token ---------------------------------------------------------

    @staticmethod
    def new_token() -> str:
        """A fresh raw token. It is never stored and never returned."""
        return secrets.token_urlsafe(_TOKEN_BYTES)

    @staticmethod
    def hash_token(raw_token: str) -> str:
        """The SHA-256 hex of a raw token: 64 characters, exact-match indexed.

        SHA-256 and not bcrypt: the input is 256 bits of entropy, so it needs
        no work factor, and an unindexable lookup would turn every preview
        into a table scan.
        """
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    @staticmethod
    def normalize_email(email: str) -> str:
        """The spelling the table stores and every lookup compares."""
        return email.strip().lower()

    @staticmethod
    def _ttl() -> timedelta:
        return timedelta(hours=settings.INVITATION_EXPIRE_HOURS)

    # -- issuance ----------------------------------------------------------

    @staticmethod
    def issue(
        session: Session, *, tenant_id: UUID, email: str, invited_by: User
    ) -> tuple[TenantInvitation, str, Tenant]:
        """Create an invitation, superseding any live one for the same pair.

        Returns the row, the **raw** token (for the mail sender and nobody
        else) and the tenant, so the caller needs no second query.

        D4: issuing supersedes. An earlier pending, unexpired row for the
        same ``(tenant_id, email)`` has its ``expires_at`` set to now, which
        is why a superseded token previews as *expired* rather than as
        unknown -- and why no ``revoked_at`` column is needed.

        The "at most one live token per pair" this gives is **best-effort,
        not an invariant**: the supersede reads with a plain ``select``
        before inserting, so two issues racing for the same pair each read
        before the other commits and both insert, leaving two live tokens.
        The window is not closable with ``with_for_update()`` (there is no
        row to lock against a phantom) nor with a partial unique index (the
        condition involves ``now()``), and it would take an advisory lock on
        a hash of the pair. It is left open deliberately: both tokens were
        minted by a superuser, for the same address, on purpose, and each is
        still single-use.
        """
        tenant = session.get(Tenant, tenant_id)
        if tenant is None:
            raise TenantNotFoundError(tenant_id)

        normalized = InvitationService.normalize_email(email)
        now = clock.db_now()

        live = session.exec(
            select(TenantInvitation).where(
                TenantInvitation.tenant_id == tenant_id,
                TenantInvitation.email == normalized,
                TenantInvitation.accepted_at.is_(None),
                TenantInvitation.expires_at > now,
            )
        ).all()
        for previous in live:
            previous.expires_at = now
            previous.updated_at = now
            session.add(previous)

        raw_token = InvitationService.new_token()
        invitation = TenantInvitation(
            tenant_id=tenant_id,
            email=normalized,
            token_hash=InvitationService.hash_token(raw_token),
            expires_at=now + InvitationService._ttl(),
            invited_by_user_id=invited_by.id,
            created_at=now,
            updated_at=now,
        )
        session.add(invitation)
        session.commit()
        session.refresh(invitation)
        return invitation, raw_token, tenant

    @staticmethod
    def list_invitations(
        session: Session, *, tenant_id: UUID | None = None
    ) -> list[TenantInvitation]:
        """Every invitation, newest first, optionally narrowed to one tenant."""
        statement = select(TenantInvitation).order_by(
            TenantInvitation.created_at.desc(), TenantInvitation.id.desc()
        )
        if tenant_id is not None:
            statement = statement.where(TenantInvitation.tenant_id == tenant_id)
        return list(session.exec(statement).all())

    # -- resolution --------------------------------------------------------

    @staticmethod
    def resolve(
        session: Session, raw_token: str, *, lock: bool = False
    ) -> TenantInvitation:
        """The usable invitation behind a raw token, or one of D7's three errors.

        One indexed lookup by ``token_hash`` for all three outcomes, so
        unknown, expired and consumed are indistinguishable by timing. With
        ``lock=True`` the row is read ``FOR UPDATE``, so two concurrent
        accepts serialise on Postgres (a no-op on the single-writer SQLite
        test engine).
        """
        statement = select(TenantInvitation).where(
            TenantInvitation.token_hash == InvitationService.hash_token(raw_token)
        )
        if lock:
            statement = statement.with_for_update()
        invitation = session.exec(statement).first()

        if invitation is None:
            raise InvitationNotFoundError
        if invitation.accepted_at is not None:
            raise InvitationAlreadyUsedError
        if invitation.expires_at <= clock.db_now():
            raise InvitationExpiredError
        return invitation

    @staticmethod
    def describe(
        session: Session, invitation: TenantInvitation
    ) -> tuple[Tenant, User, bool]:
        """The tenant, the inviter and whether the address already has a user."""
        tenant = session.get(Tenant, invitation.tenant_id)
        inviter = session.get(User, invitation.invited_by_user_id)
        account_exists = (
            session.exec(select(User).where(User.email == invitation.email)).first()
            is not None
        )
        return tenant, inviter, account_exists

    # -- acceptance --------------------------------------------------------

    @staticmethod
    def accept(
        session: Session,
        *,
        raw_token: str,
        full_name: str | None = None,
        cpf: str | None = None,
        password: str | None = None,
    ) -> tuple[TenantInvitation, User, bool]:
        """Consume the invitation. Returns ``(invitation, user, created)``.

        D9, the new-account branch: a ``User`` with ``is_active=True``,
        exactly **one** ``UserTenantLink`` (the invited tenant,
        ``is_tenant_admin=True``) and **zero** ``user_role_link`` rows.
        Active rather than pending, because the invitation *is* the approval
        signup waits for and there is no administrator in that condominium
        to give a second one; no default-tenant membership, or the invited
        administrator would appear in a condominium nobody invited them to;
        no role row, because ``deps.is_acting_tenant_admin`` already grants
        the whole catalogue inside the acting tenant.

        D8, the existing-account branch: the account is **linked**, never
        recreated, and ``full_name``, ``cpf`` and ``password`` are ignored.
        Resetting an existing account's password from an invitation someone
        else issued is an account takeover, so it is refused.

        The consumption (``accepted_at``, ``accepted_user_id``) happens in
        the same transaction as the write.
        """
        invitation = InvitationService.resolve(session, raw_token, lock=True)
        now = clock.db_now()

        user = session.exec(select(User).where(User.email == invitation.email)).first()
        created = user is None
        if created:
            user = InvitationService._create_user(
                session,
                email=invitation.email,
                full_name=full_name,
                cpf=cpf,
                password=password,
            )
        else:
            user.is_active = True
            session.add(user)

        InvitationService._grant_administration(
            session, user=user, tenant_id=invitation.tenant_id
        )

        invitation.accepted_at = now
        invitation.accepted_user_id = user.id
        invitation.updated_at = now
        session.add(invitation)
        session.commit()
        session.refresh(invitation)
        session.refresh(user)
        return invitation, user, created

    @staticmethod
    def _create_user(
        session: Session,
        *,
        email: str,
        full_name: str | None,
        cpf: str | None,
        password: str | None,
    ) -> User:
        missing = [
            name
            for name, value in (
                ("full_name", full_name),
                ("cpf", cpf),
                ("password", password),
            )
            if not (value or "").strip()
        ]
        if missing:
            raise InvitationIncompleteError(missing)

        # The single account-minting gate: whatever signup refuses, this
        # refuses. `UserCreate` also *normalises* the CPF to 11 digits, which
        # is what makes the conflict lookup below an equality match against
        # the spelling signup stores (D9).
        try:
            account = UserCreate(
                email=email, full_name=full_name, cpf=cpf, password=password
            )
        except ValidationError as exc:
            raise InvitationInvalidAccountError(_first_error(exc)) from exc

        if (
            session.exec(select(User).where(User.cpf == account.cpf)).first()
            is not None
        ):
            raise InvitationCpfConflictError

        user = User(
            email=account.email,
            full_name=account.full_name,
            cpf=account.cpf,
            hashed_password=security.get_password_hash(account.password),
            is_active=True,
        )
        session.add(user)
        session.flush()
        return user

    @staticmethod
    def _grant_administration(
        session: Session, *, user: User, tenant_id: UUID
    ) -> UserTenantLink:
        """The invited tenant's membership, created or promoted. Nothing else.

        Every other membership the user holds is left exactly as it was: an
        invitation to administer one condominium says nothing about any
        other.
        """
        link = session.exec(
            select(UserTenantLink).where(
                UserTenantLink.user_id == user.id,
                UserTenantLink.tenant_id == tenant_id,
            )
        ).first()
        if link is None:
            link = UserTenantLink(user_id=user.id, tenant_id=tenant_id)
        link.is_tenant_admin = True
        session.add(link)
        return link
