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
from app.models.enums import UserRole
from app.models.tenant import Tenant, UserTenantLink
from app.models.user import User
from app.models.user_type import UserType
from app.schemas.tenant import TenantCreate, TenantMemberRead, TenantUpdate

# Human-readable names of the role-linked UserType rows seeded into every new
# tenant, matching the five migration 0018 seeded into the default tenant plus
# PORTEIRO, the role added afterwards by 0020.
ROLE_TYPE_NAMES: dict[UserRole, str] = {
    UserRole.ADMINISTRATOR: "Administrador (papel)",
    UserRole.DIRECTOR: "Diretor (papel)",
    UserRole.MANAGER: "Gerente (papel)",
    UserRole.GUEST: "Convidado (papel)",
    UserRole.RESIDENT: "Morador (papel)",
    UserRole.PORTEIRO: "Porteiro (papel)",
}


class TenantService:
    """Service class for tenant and tenant-membership operations.

    ``create_tenant`` seeds one role-linked ``UserType`` per ``UserRole``
    into the new tenant (APRAS-42 §7.2). APRAS-41 deliberately did not,
    because ``get_effective_user_type_ids`` resolved a role's UserType with a
    tenant-blind ``.first()``; now that resolution is tenant-scoped the
    opposite holds — without these rows a non-``ADMINISTRATOR`` member of a
    new tenant has an empty effective-UserType set and is 403'd by
    ``assert_menu_access`` on every gated menu.
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

        cls.ensure_role_types(session, tenant.id)

        session.refresh(tenant)
        return tenant

    @staticmethod
    def ensure_role_types(session: Session, tenant_id: UUID) -> int:
        """Insert the role-linked ``UserType`` rows ``tenant_id`` is missing.

        Idempotent by construction: it reads the roles already present and
        inserts only the gap, so it is safe to call on every tenant of an
        install (``app/seed.py``) and on a brand-new one
        (``create_tenant``). Tenants created before APRAS-42 have no
        role-linked rows at all, and without them a non-``ADMINISTRATOR``
        member has an empty effective-UserType set and is 403'd by
        ``assert_menu_access`` on every gated menu; ``python -m app.seed`` is
        the documented recovery path rather than a data step inside an
        otherwise reversible migration (APRAS-43 §7).

        The acting tenant is swapped for the duration so both the read and
        the write see exactly ``tenant_id``: the ambient filter constrains
        the existence check and the write stamp puts the right id on every
        inserted row. `ix_user_type_tenant_role` guarantees at most one row
        per (tenant, role). This is the one production caller of
        ``acting_tenant_scope``.

        Returns:
            int: how many rows were inserted (0 on a complete tenant).
        """
        with acting_tenant_scope(session, tenant_id):
            existing = {
                user_type.role
                for user_type in session.exec(
                    select(UserType).where(UserType.role.is_not(None))
                ).all()
            }
            missing = [
                UserType(name=name, role=role, allowed_menus=[])
                for role, name in ROLE_TYPE_NAMES.items()
                if role not in existing
            ]
            if missing:
                session.add_all(missing)
                session.commit()
        return len(missing)

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
            role=user.role,
            linked_at=link.created_at,
            is_tenant_admin=link.is_tenant_admin,
        )
