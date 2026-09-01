"""User directory scoping (APRAS-43 §6).

`user` is a **global** table: one identity belongs to zero or more tenants
through `UserTenantLink`, so the ambient tenant filter of
`app/core/tenant_context.py` neither helps nor interferes here — there is no
`user.tenant_id` to constrain. This module is what makes the three
user-directory routes tenant-scoped anyway, with a single rule that applies
to **every** caller, `ADMINISTRATOR` included.

The rule (§6.2): a user is visible in the acting tenant ``T`` when

* they hold a `UserTenantLink` to ``T``; **or**
* they hold **no** `UserTenantLink` at all and ``T`` is the default tenant.

The second clause is the mirror image of APRAS-42's resolution ladder, where
a caller with zero memberships *acts* in the default tenant
(`deps._resolve_without_header`): saying they are also *visible* there is the
only consistent reading, and it is what keeps the ~70 pre-existing test
modules — whose fixtures build `User(...)` rows with no membership — passing
untouched. In production, migration `0028` gave every real user exactly one
membership, so the clause is inert there.
"""

from uuid import UUID

from sqlalchemy import or_
from sqlmodel import Session, select

from app.models.tenant import DEFAULT_TENANT_ID, UserTenantLink
from app.models.user import User


class UserService:
    """Visibility helpers shared by the three user-directory routes."""

    @staticmethod
    def visible_users_statement(tenant_id: UUID):
        """Return a `select(User)` narrowed to the users visible in a tenant.

        Returned as a statement rather than a list so the callers can keep
        composing their own filters (`GET /api/v1/users/?is_active=`).
        """
        linked = select(UserTenantLink.user_id).where(
            UserTenantLink.tenant_id == tenant_id
        )
        statement = select(User)
        if tenant_id == DEFAULT_TENANT_ID:
            return statement.where(
                or_(
                    User.id.in_(linked),
                    User.id.not_in(select(UserTenantLink.user_id)),
                )
            )
        return statement.where(User.id.in_(linked))

    @classmethod
    def get_visible_user(
        cls, session: Session, user_id: UUID, tenant_id: UUID
    ) -> User | None:
        """Return the user if visible in ``tenant_id``, else ``None``.

        The ``None`` is a **404** at every call site, for every role: acting
        in tenant A, an administrator does not see a B-only user any more
        than a tenant_admin of A does. Administrator power is not removed,
        it is *relocated* to `X-Tenant-Id` — the global-vision mechanism
        APRAS-42 established.
        """
        statement = cls.visible_users_statement(tenant_id).where(User.id == user_id)
        return session.exec(statement).first()

    @staticmethod
    def membership_tenant_ids(session: Session, user_id: UUID) -> set[UUID]:
        """Return every tenant id the user holds a membership in."""
        links = session.exec(
            select(UserTenantLink).where(UserTenantLink.user_id == user_id)
        ).all()
        return {link.tenant_id for link in links}
