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
from app.models.enums import UserRole
from app.models.tenant import Tenant, UserTenantLink
from app.models.user import User
from app.schemas.tenant import TenantCreate, TenantMemberRead, TenantUpdate


class TenantService:
    """Service class for tenant and tenant-membership operations.

    This slice deliberately does **not** seed role-linked ``UserType`` rows
    for a newly created tenant. ``get_effective_user_type_ids``
    (``app/api/deps.py``) resolves a role's UserType with a tenant-blind
    ``.first()``; seeding per-tenant role types here would immediately make
    that call non-deterministic. Doing both — tenant-aware resolution and
    per-tenant seeding — is APRAS-42's job.
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
        return tenant

    @staticmethod
    def list_tenants(session: Session, current_user: User) -> list[Tenant]:
        """List tenants visible to the caller, ordered by name.

        ADMINISTRATOR sees every tenant; every other role sees only the
        tenants it is linked to. A user with no memberships gets an empty
        list, not an error.
        """
        if current_user.role == UserRole.ADMINISTRATOR:
            statement = select(Tenant).order_by(Tenant.name)
        else:
            statement = (
                select(Tenant)
                .join(UserTenantLink, UserTenantLink.tenant_id == Tenant.id)
                .where(UserTenantLink.user_id == current_user.id)
                .order_by(Tenant.name)
            )
        return list(session.exec(statement).all())

    @classmethod
    def get_visible_tenant(
        cls, session: Session, tenant_id: UUID, current_user: User
    ) -> Tenant:
        """Return a tenant the caller may read, or raise TenantNotFoundError.

        A non-administrator that is not a member gets a 404, never a 403 —
        the existence of another condominium's tenant is not information the
        caller is entitled to.
        """
        tenant = cls.get_tenant(session, tenant_id)
        if current_user.role == UserRole.ADMINISTRATOR:
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
        cls, session: Session, tenant_id: UUID, user_id: UUID
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

        link = UserTenantLink(user_id=user_id, tenant_id=tenant_id)
        session.add(link)
        session.commit()
        session.refresh(link)
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
            role=user.role,
            linked_at=link.created_at,
        )
