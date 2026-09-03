"""Anti-escalation for the two permission-grant surfaces (APRAS-46 §9).

"Granting or editing a role containing a permission the author does not hold"
is exactly this check, applied to the **resulting** set rather than the
delta: the resulting-set reading also closes "author edits a role that
already carries X and keeps X while renaming it".

The cost of that reading, recorded rather than fixed here (APRAS-49 §8): an
editor who cannot grant something a role *already* holds cannot save that
role at all -- even a pure rename answers 403. Validating the delta instead
would make the rename saveable but would reopen the "keep X while renaming"
hole this rule exists to close, so the resulting-set reading stands and the
consequence is documented.

Also home to `role_names_in`, the one serialiser behind the three summary
schemas that used to carry a single enum `role` (APRAS-49 §8.2).
"""

from collections.abc import Iterable
from uuid import UUID

from sqlmodel import Session

from app.api.deps import get_grantable_permissions
from app.core import tenant_context
from app.core.exceptions import ForbiddenError
from app.core.permissions import SUPERUSER_ONLY_PERMISSIONS
from app.models.role import Role
from app.models.tenant import DEFAULT_TENANT_ID
from app.models.user import User


def assert_can_grant(
    session: Session, author: User, permissions: Iterable[str]
) -> None:
    """The author may only put permissions they themselves hold into a group,
    and nobody may put a superuser-only permission into one at all.

    "What they hold" is `deps.get_grantable_permissions` — the author's
    authority **before** APRAS-39's per-tenant module strip, and this is the
    one deliberate exception to that strip in the whole codebase (§5.5). The
    switch governs what a user may *do*; it must not freeze who may
    administer roles. The two readings differ only in a tenant with a
    disabled module, and the difference is exactly what keeps a pure rename
    of a `finance:read`-carrying role saveable while `finance` is off.

    `is_tenant_admin` needs no special case: the author's set is the whole
    catalogue of the granting tenant (APRAS-47 §4.2), so a capability holder
    can grant exactly what they hold.

    The `SUPERUSER_ONLY_PERMISSIONS` branch runs **first** and applies to
    every author, superuser included: those four strings name routes gated by
    `deps.get_current_superuser`, so a group carrying them would grant
    nothing. The point is that the group would be a lie, not that the author
    is untrusted. They stay *valid* (422 is for unknown strings) and become
    *un-grantable* (403), which is what makes the two answers distinguishable.

    Args:
        session: Database session carrying the acting tenant.
        author: The user performing the grant.
        permissions: The resulting permission bundle of the group.

    Raises:
        ForbiddenError: If the bundle carries a superuser-only permission, or
            anything the author lacks.
    """
    forbidden = sorted(set(permissions) & SUPERUSER_ONLY_PERMISSIONS)
    if forbidden:
        raise ForbiddenError(
            "These permissions are granted by is_superuser only: "
            + ", ".join(forbidden)
        )
    # APRAS-39 §5.5: the author's authority **ignoring** the tenant's module
    # switch. A disabled module must not freeze role administration — this
    # check reads the *whole resulting bundle*, so a stripped comparison
    # would 403 a pure rename of any of the four seeded roles that carry
    # `finance:read`. The grant is harmless: the strings are inert until the
    # operator re-enables the module, at which point the author holds them
    # too, so a grant can never exceed what the author holds with every
    # module on.
    missing = sorted(set(permissions) - get_grantable_permissions(author, session))
    if missing:
        raise ForbiddenError(
            "You cannot grant permissions you do not hold: " + ", ".join(missing)
        )


def assert_can_assign_roles(
    session: Session, author: User, roles: Iterable[Role]
) -> None:
    """The same rule for the *assignment* surface (§9.3).

    Without it, an author who cannot create a group carrying
    `finance:category_create` could still hand an existing one to a
    confederate.
    """
    granted: set[str] = set()
    for role in roles:
        granted.update(role.permissions)
    assert_can_grant(session, author, granted)


def role_names_in(user: User, tenant_id: UUID | None) -> list[str]:
    """The user's role **names** in `tenant_id`, sorted (APRAS-49 §8.2).

    The one serialisation helper behind `UserSummaryRead.roles`,
    `TenantMemberRead.roles` and `ResidentUserSummary.roles`: three schemas
    that each carried a single enum `role` before IAM F5 and now carry one shape,
    computed one way.

    Sorted so a payload is stable between two requests, and narrowed to one
    tenant because a role of another tenant is not part of this answer --
    relationship loads are exempt from the ambient filter (APRAS-42 §4.2), so
    the narrowing has to be explicit.
    """
    if tenant_id is None:
        return []
    return sorted(role.name for role in user.roles if role.tenant_id == tenant_id)


def role_names_here(user: User, session: Session) -> list[str]:
    """`role_names_in` for the session's acting tenant.

    The lot and resident serialisers reach this shape from an object that
    carries no `tenant_id` of its own (`UserLotLink` is an *inherited* table,
    scoped through its parent), so they ask the session instead.
    """
    tenant_id = tenant_context.acting_tenant_id(session) or DEFAULT_TENANT_ID
    return role_names_in(user, tenant_id)
