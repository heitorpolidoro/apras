"""Permission catalogue and self-scoped effective-permission endpoints.

IAM F4 (APRAS-48). Two authenticated, read-only routes that add **zero**
authorization outcomes to the 180 mapped ones: both are on
`UNGUARDED_ROUTES`, so `tests/data/parity_matrix_baseline.json` stays
byte-identical (§3.3).
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api import deps as api_deps
from app.core.permissions import PERMISSIONS, SUPERUSER_ONLY_PERMISSIONS, module_of
from app.db import get_session
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.permission import MyPermissionsRead, PermissionDescriptorRead

router = APIRouter()


# No `response_model=`: the return annotation is the same type, and ruff's
# FAST001 rejects declaring it twice. FastAPI derives the response model
# from the annotation, so the serialisation contract is unchanged.
@router.get("/me")
def read_my_permissions(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_user)],
    tenant: Annotated[Tenant, Depends(api_deps.get_current_tenant)],
) -> MyPermissionsRead:
    """The caller's own effective permissions, in the acting tenant.

    Strictly self-scoped, exactly like `GET /api/v1/auth/me`, and therefore
    on the unguarded allowlist: there is no permission that could gate
    "tell me what I hold". The acting tenant is resolved by the same
    router-level `get_current_tenant` every scoped route uses, which is what
    makes the answer per-tenant (APRAS-42); re-declaring it here is free
    (one solve per request) and gives the body its `tenant_id`.
    """
    return MyPermissionsRead(
        tenant_id=tenant.id,
        permissions=sorted(api_deps.get_effective_permissions(current_user, session)),
    )


@router.get("/")
def read_permission_catalogue(
    current_user: Annotated[User, Depends(api_deps.get_current_user)],  # noqa: ARG001
) -> list[PermissionDescriptorRead]:
    """The whole catalogue, sorted, identical for every caller.

    Static vocabulary that lives in this repository's source; it carries no
    tenant data and no user data, so it is authenticated and unguarded. The
    group editor needs it to render the permissions the author does *not*
    hold as disabled rather than absent (APRAS-48 ER-4).

    Sorted by `permission` ascending: the UI groups by module and the matrix
    must not reorder between two requests.
    """
    return [
        PermissionDescriptorRead(
            permission=permission,
            module=module_of(permission),
            action=permission.split(":", 1)[1],
            superuser_only=permission in SUPERUSER_ONLY_PERMISSIONS,
        )
        for permission in sorted(PERMISSIONS)
    ]
