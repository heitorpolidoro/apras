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

    `landing_path` (IAM F5, APRAS-49 §10.4) is the first non-null
    `Role.landing_path` among the caller's roles in the acting tenant,
    ordered by role name for determinism, or None. It rides on *this*
    endpoint because it follows the **effective** (simulation-aware)
    identity: landing is a preference, not authorization, so simulating a
    porteiro should show you the porteiro's landing -- and that is safe
    precisely because route *access* stays on the real set.

    `disabled_modules` (APRAS-39 §7) is the acting tenant's turned-off
    modules, sorted. `permissions` is **already** stripped by
    `deps.get_effective_permissions`, so gating never reads this field —
    which is what keeps a superuser (unstripped, §5.3) fully functional in a
    tenant that has modules off while still being *told* which ones are. It
    exists because two consumers cannot derive it: the simulation arm of
    `useEffectivePermissionSet`, which builds its set from the role rows
    rather than from this payload, and the "module not enabled" variant of
    the restricted-access message.
    """

    tenant_id: UUID
    permissions: list[str]  # sorted
    landing_path: str | None = None
    disabled_modules: list[str] = []  # sorted; APRAS-39
