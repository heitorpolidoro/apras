"""Anti-escalation for the two permission-grant surfaces (APRAS-46 §9).

`user_type` rows *are* the groups until IAM F5 renames them, so "granting or
editing a group containing a permission the author does not hold" is exactly
this check, applied to the **resulting** set rather than the delta: the
resulting-set reading also closes "author edits a group that already carries
X and keeps X while renaming it".
"""

from collections.abc import Iterable

from sqlmodel import Session

from app.api.deps import get_effective_permissions
from app.core.exceptions import ForbiddenError
from app.core.permissions import SUPERUSER_ONLY_PERMISSIONS
from app.models.user import User
from app.models.user_type import UserType


def assert_can_grant(
    session: Session, author: User, permissions: Iterable[str]
) -> None:
    """The author may only put permissions they themselves hold into a group,
    and nobody may put a superuser-only permission into one at all.

    `is_tenant_admin` needs no special case: the author's *effective* set is
    the whole catalogue of the granting tenant (APRAS-47 §4.2), so a
    capability holder can grant exactly what they hold.

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
    missing = sorted(set(permissions) - get_effective_permissions(author, session))
    if missing:
        raise ForbiddenError(
            "You cannot grant permissions you do not hold: " + ", ".join(missing)
        )


def assert_can_assign_user_types(
    session: Session, author: User, user_types: Iterable[UserType]
) -> None:
    """The same rule for the *assignment* surface (§9.3).

    Without it, an author who cannot create a group carrying
    `finance:category_create` could still hand an existing one to a
    confederate.
    """
    granted: set[str] = set()
    for user_type in user_types:
        granted.update(user_type.permissions)
    assert_can_grant(session, author, granted)
