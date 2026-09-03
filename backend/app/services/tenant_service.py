"""Tenant service layer for business logic (APRAS-41)."""

from datetime import datetime
from uuid import UUID

from sqlmodel import Session, select

from app.core.exceptions import (
    TenantAlreadyExistsError,
    TenantMembershipAlreadyExistsError,
    TenantMembershipNotFoundError,
    TenantNotFoundError,
)
from app.core.tenant_context import acting_tenant_scope
from app.models.role import Role
from app.models.tenant import Tenant, UserTenantLink
from app.models.user import User
from app.schemas.tenant import (
    TenantCreate,
    TenantMemberRead,
    TenantMembershipSummary,
    TenantUpdate,
)
from app.services.role_service import role_names_in

#: The six historically-named ``Role`` rows every tenant gets: the five
#: migration ``0018`` seeded into the default tenant plus ``Porteiro
#: (papel)``, added afterwards by ``0020``.
#:
#: A plain tuple of **names** since IAM F5 (APRAS-49 §9.2): it was a
#: ``dict`` keyed on the retired role enum, and idempotency was keyed on
#: the ``role`` column migration ``0033`` dropped. Names are the key now.
#: They are ordinary rows -- editable, renamable, deletable -- and this tuple
#: is only what ``ensure_legacy_roles`` inserts when they are absent.
LEGACY_ROLE_NAMES: tuple[str, ...] = (
    "Administrador (papel)",
    "Diretor (papel)",
    "Gerente (papel)",
    "Convidado (papel)",
    "Morador (papel)",
    "Porteiro (papel)",
)


class TenantService:
    """Service class for tenant and tenant-membership operations.

    ``create_tenant`` seeds the six historically-named ``Role`` rows into
    every new tenant (``ensure_legacy_roles``, APRAS-42 §7.2). They carry
    **no permissions** and grant nobody anything: they exist so that an
    operator opening a fresh tenant finds the same six names every other
    tenant has, and so that a migration or a script can address them by name.
    """

    @staticmethod
    def get_tenant(session: Session, tenant_id: UUID) -> Tenant:
        """Return a tenant by id or raise TenantNotFoundError."""
        tenant = session.get(Tenant, tenant_id)
        if not tenant:
            raise TenantNotFoundError(tenant_id)
        return tenant

    @staticmethod
    def is_member(session: Session, tenant_id: UUID, user_id: UUID) -> bool:
        """Return whether the user is linked to the tenant."""
        link = session.exec(
            select(UserTenantLink).where(
                UserTenantLink.tenant_id == tenant_id,
                UserTenantLink.user_id == user_id,
            )
        ).first()
        return link is not None

    @classmethod
    def create_tenant(cls, session: Session, tenant_in: TenantCreate) -> Tenant:
        """Create a tenant, rejecting a duplicate (globally unique) name."""
        existing = session.exec(
            select(Tenant).where(Tenant.name == tenant_in.name)
        ).first()
        if existing:
            raise TenantAlreadyExistsError(tenant_in.name)

        tenant = Tenant(name=tenant_in.name, is_active=tenant_in.is_active)
        session.add(tenant)
        session.commit()
        session.refresh(tenant)

        cls.ensure_legacy_roles(session, tenant.id)

        session.refresh(tenant)
        return tenant

    @staticmethod
    def ensure_legacy_roles(session: Session, tenant_id: UUID) -> int:
        """Insert the six ``LEGACY_ROLE_NAMES`` rows ``tenant_id`` is missing.

        It inserts rows with ``permissions = []`` and **grants nobody
        anything**. Idempotent by construction: it reads the names already
        present and inserts only the gap, so it is safe to call on every
        tenant of an install (``app/seed.py``) and on a brand-new one
        (``create_tenant``).

        Keyed on **name** since IAM F5 (APRAS-49 §9.2): the ``role`` column
        it used to key on was dropped by migration ``0033``, and
        ``ix_role_tenant_name`` is what now guarantees at most one row per
        ``(tenant, name)``.

        The acting tenant is swapped for the duration so both the read and
        the write see exactly ``tenant_id``: the ambient filter constrains
        the existence check and the write stamp puts the right id on every
        inserted row. This is the one production caller of
        ``acting_tenant_scope``.

        Returns:
            int: how many rows were inserted (0 on a complete tenant).
        """
        with acting_tenant_scope(session, tenant_id):
            existing = {role.name for role in session.exec(select(Role)).all()}
            missing = [
                Role(name=name)
                for name in LEGACY_ROLE_NAMES
                if name not in existing
            ]
            if missing:
                session.add_all(missing)
                session.commit()
        return len(missing)

    @staticmethod
    def list_tenants(session: Session, current_user: User) -> list[Tenant]:
        """List tenants visible to the caller, ordered by name.

        A superuser sees every tenant (APRAS-47 §5.1); everyone else sees only
        the tenants they are linked to. A user with no memberships gets an
        empty list, not an error.
        """
        if current_user.is_superuser:
            statement = select(Tenant).order_by(Tenant.name)
        else:
            statement = (
                select(Tenant)
                .join(UserTenantLink, UserTenantLink.tenant_id == Tenant.id)
                .where(UserTenantLink.user_id == current_user.id)
                .order_by(Tenant.name)
            )
        return list(session.exec(statement).all())

    @staticmethod
    def list_memberships(
        session: Session, user: User
    ) -> list[TenantMembershipSummary]:
        """List the *caller's own* memberships, ordered by tenant name.

        Unlike :meth:`list_tenants`, this never widens for a superuser: it
        answers "which tenants is this user a member
        of, and where does the ``is_tenant_admin`` capability apply", which is
        what ``GET /api/v1/auth/me`` needs (APRAS-38 §3.2). A user with no
        memberships gets ``[]`` — never an error and never a synthesised
        default-tenant entry, because a zero-membership user must keep the
        backend's own header-less fallback rather than a client-invented one.

        Ordered by ``Tenant.name``, the same order as :meth:`list_tenants`,
        which is what makes the frontend's "first membership" pre-selection
        deterministic. ``UserTenantLink`` is outside ``TENANT_SCOPED_MODELS``,
        so this query is unaffected by the ambient filter and works on a
        global route.
        """
        statement = (
            select(Tenant, UserTenantLink)
            .join(UserTenantLink, UserTenantLink.tenant_id == Tenant.id)
            .where(UserTenantLink.user_id == user.id)
            .order_by(Tenant.name)
        )
        return [
            TenantMembershipSummary(
                tenant_id=tenant.id,
                name=tenant.name,
                is_active=tenant.is_active,
                is_tenant_admin=link.is_tenant_admin,
            )
            for tenant, link in session.exec(statement).all()
        ]

    @classmethod
    def get_visible_tenant(
        cls, session: Session, tenant_id: UUID, current_user: User
    ) -> Tenant:
        """Return a tenant the caller may read, or raise TenantNotFoundError.

        A non-superuser that is not a member gets a 404, never a 403 — the
        existence of another condominium's tenant is not information the
        caller is entitled to (APRAS-47 §5.1).
        """
        tenant = cls.get_tenant(session, tenant_id)
        if current_user.is_superuser:
            return tenant
        if not cls.is_member(session, tenant_id, current_user.id):
            raise TenantNotFoundError(tenant_id)
        return tenant

    @classmethod
    def update_tenant(
        cls, session: Session, tenant_id: UUID, tenant_in: TenantUpdate
    ) -> Tenant:
        """Update a tenant's name and/or active flag."""
        tenant = cls.get_tenant(session, tenant_id)
        update_data = tenant_in.model_dump(exclude_unset=True)

        new_name = update_data.get("name")
        if new_name is not None and new_name != tenant.name:
            collision = session.exec(
                select(Tenant).where(Tenant.name == new_name)
            ).first()
            if collision:
                raise TenantAlreadyExistsError(new_name)

        for key, value in update_data.items():
            setattr(tenant, key, value)
        tenant.updated_at = datetime.utcnow()

        session.add(tenant)
        session.commit()
        session.refresh(tenant)
        return tenant

    @classmethod
    def list_members(
        cls, session: Session, tenant_id: UUID, current_user: User
    ) -> list[TenantMemberRead]:
        """List a tenant's members; visible to an administrator or a member."""
        cls.get_visible_tenant(session, tenant_id, current_user)
        rows = session.exec(
            select(UserTenantLink, User)
            .join(User, User.id == UserTenantLink.user_id)
            .where(UserTenantLink.tenant_id == tenant_id)
            .order_by(User.full_name)
        ).all()
        return [cls._to_member_read(link, user) for link, user in rows]

    @classmethod
    def add_member(
        cls,
        session: Session,
        tenant_id: UUID,
        user_id: UUID,
        is_tenant_admin: bool = False,
    ) -> TenantMemberRead:
        """Link a user to a tenant.

        Multi-membership is supported: only the same ``(user, tenant)`` pair
        a second time is a conflict.
        """
        cls.get_tenant(session, tenant_id)
        user = session.get(User, user_id)
        if not user:
            # An unknown user id is a 404 too, and reported as a missing
            # membership rather than a missing user: the statement "user X
            # is not a member of tenant Y" is exactly true, and it avoids
            # turning this route into a user-id enumeration oracle.
            raise TenantMembershipNotFoundError(user_id, tenant_id)
        if cls.is_member(session, tenant_id, user_id):
            raise TenantMembershipAlreadyExistsError(user_id, tenant_id)

        link = UserTenantLink(
            user_id=user_id, tenant_id=tenant_id, is_tenant_admin=is_tenant_admin
        )
        session.add(link)
        session.commit()
        session.refresh(link)
        return cls._to_member_read(link, user)

    @classmethod
    def set_member_admin(
        cls,
        session: Session,
        tenant_id: UUID,
        user_id: UUID,
        is_tenant_admin: bool,
    ) -> TenantMemberRead:
        """Grant or revoke the tenant_admin capability on one membership.

        An unknown tenant, an unknown user or a user with no membership in
        the tenant are all the same 404 (``TenantMembershipNotFoundError``),
        for the reason ``add_member`` already documents: the statement "user
        X is not a member of tenant Y" is exactly true and it keeps this
        route from becoming an id-enumeration oracle.
        """
        cls.get_tenant(session, tenant_id)
        link = session.exec(
            select(UserTenantLink).where(
                UserTenantLink.tenant_id == tenant_id,
                UserTenantLink.user_id == user_id,
            )
        ).first()
        if not link:
            raise TenantMembershipNotFoundError(user_id, tenant_id)

        link.is_tenant_admin = is_tenant_admin
        session.add(link)
        session.commit()
        session.refresh(link)

        user = session.get(User, user_id)
        return cls._to_member_read(link, user)

    @classmethod
    def remove_member(cls, session: Session, tenant_id: UUID, user_id: UUID) -> None:
        """Unlink a user from a tenant."""
        cls.get_tenant(session, tenant_id)
        link = session.exec(
            select(UserTenantLink).where(
                UserTenantLink.tenant_id == tenant_id,
                UserTenantLink.user_id == user_id,
            )
        ).first()
        if not link:
            raise TenantMembershipNotFoundError(user_id, tenant_id)
        session.delete(link)
        session.commit()

    @staticmethod
    def _to_member_read(link: UserTenantLink, user: User) -> TenantMemberRead:
        """Flatten a membership row plus its user into the read schema."""
        return TenantMemberRead(
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            roles=role_names_in(user, link.tenant_id),
            linked_at=link.created_at,
            is_tenant_admin=link.is_tenant_admin,
        )
