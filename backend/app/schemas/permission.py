"""Permission schemas (IAM F4, APRAS-48).

The two read-only shapes the browser needs and cannot compute for itself:
*what permissions exist* and *which ones I hold in the tenant I am acting in*.
"""

from uuid import UUID

from pydantic import BaseModel


class PermissionDescriptorRead(BaseModel):
    """One catalogue entry, pre-split so the UI needs no string surgery.

    `module` and `action` are the two halves of the `<module>:<action>` key
    (`app.core.permissions.module_of`); the UI groups by the first and labels
    by the second (APRAS-48 §2.8), so splitting here keeps exactly one parser
    of the convention in the codebase.
    """

    permission: str  # "finance:transaction_create"
    module: str  # "finance"
    action: str  # "transaction_create"
    # In SUPERUSER_ONLY_PERMISSIONS: the four strings `assert_can_grant`
    # refuses to every author, superuser included (APRAS-47). This is the
    # field the group editor's disabled checkbox reads.
    superuser_only: bool


class MyPermissionsRead(BaseModel):
    """The caller's effective permissions in the acting tenant.

    `tenant_id` echoes the tenant the answer was computed for, so a client
    can never mistake a stale payload for the current tenant's.
    """

    tenant_id: UUID
    permissions: list[str]  # sorted
