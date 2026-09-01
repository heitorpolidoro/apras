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
from app.models.user import User
from app.models.user_type import UserType


def assert_can_grant(
    session: Session, author: User, permissions: Iterable[str]
) -> None:
    """The author may only put permissions they themselves hold into a group.

    `is_tenant_admin` needs no special case: the author's *effective* set
    already includes the §3.3 bridge, so a capability holder can grant
    exactly what they hold -- and when F3 widens that bridge to the whole
    tenant, this rule widens with it, with no edit here.

    An ADMINISTRATOR holds `PERMISSIONS - ADMIN_GAP_PERMISSIONS`, so the only
    string they cannot put in a group is `packages:my_lots_read` -- a real,
    documented consequence of APRAS-45 §11.5.

    Args:
        session: Database session carrying the acting tenant.
        author: The user performing the grant.
        permissions: The resulting permission bundle of the group.

    Raises:
        ForbiddenError: If the bundle contains anything the author lacks.
    """
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
