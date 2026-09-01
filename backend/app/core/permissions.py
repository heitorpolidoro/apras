"""The APRAS permission registry (IAM F1, APRAS-45).

Slice 1 of the GCP-style IAM chain: **fine permissions in code -> roles
(permission bundles) as data -> users N:N roles**. This module is the
vocabulary and the wiring; it changes no authorization outcome. Enforcement
is IAM F4.

Deliberately dependency-free apart from `app.models.enums.UserRole`: no
FastAPI, no SQLModel, no session. It must stay importable from Alembic, from
a script and from a test that has no database.

Naming convention (§3)::

    <module>:<action>        e.g. tasks:read, purchases:decide, gate:checkin

matching ``^[a-z][a-z0-9_]*:[a-z][a-z0-9_]*$`` -- exactly one colon,
snake_case on both sides. ``read`` / ``create`` / ``update`` / ``delete`` for
plain CRUD on the module's main resource; a named domain action for anything
else (``purchases:decide``, ``votes:close``, ``gate:checkin``). Sub-resource
CRUD carries the sub-resource in the action (``projects:milestone_create``),
never a second colon.

The module segment is the domain that owns the guard, which is not always the
URL prefix: the three ``/lots/{lot_id}/voter-eligibility`` routes are guarded
by ``voting_service._assert_can_manage_eligibility`` and are therefore
``votes:eligibility_*``.

``ROUTE_PERMISSIONS`` keys use the FastAPI route template exactly as
``APIRoute.path`` yields it, the same key shape ``test_tenant_route_scope.py``
already uses.
"""

from app.models.enums import UserRole

A = UserRole.ADMINISTRATOR
D = UserRole.DIRECTOR
M = UserRole.MANAGER
G = UserRole.GUEST
R = UserRole.RESIDENT
P = UserRole.PORTEIRO

#: Every role there is. Spelled once so the "all six" rows below cannot drift.
ALL_ROLES: frozenset[UserRole] = frozenset(UserRole)


# ---------------------------------------------------------------------------
# Scope permissions (IAM F2, APRAS-46 §4.2)
# ---------------------------------------------------------------------------

#: The only vocabulary IAM F2 adds. Each replaces an *object*-dimension staff
#: bypass whose role set matches no route permission in the right module;
#: forcing one (gating "see every lot's residents" on `assets:read` because
#: both happen to be `{A, D, M}`) would break the day someone edits
#: `assets:read`. They are deliberately **not** route-mapped, which is why
#: `test_every_catalogue_permission_is_reachable` is amended rather than
#: quietly satisfied.
SCOPE_PERMISSIONS: frozenset[str] = frozenset(
    {
        # ResidentService._check_lot_access staff bypass.
        "residents:read_any_lot",
        # VisitorService._check_lot_access / get_user_linked_lot_ids /
        # revoke_authorization / get_access_logs staff bypasses -- one
        # predicate, four sites, the same {A, D, M} tuple today.
        "visitors:manage_any_lot",
        # occurrence_service A/D branches: see every occurrence, see
        # internal-only timeline entries, unmask anonymous reporters, update
        # status without being assigned.
        "occurrences:manage_all",
        # MediaService.upload_photo's auto-approval branch -- publishing
        # without review is a real privilege, not a display rule.
        "uploads:auto_approve",
    }
)


# ---------------------------------------------------------------------------
# The catalogue (§4)
# ---------------------------------------------------------------------------

PERMISSIONS: frozenset[str] = SCOPE_PERMISSIONS | frozenset(
    {
        # §4.1 tasks
        "tasks:read",
        "tasks:create",
        "tasks:update",
        "tasks:delete",
        "tasks:comment",
        # §4.2 categories
        "categories:read",
        "categories:create",
        "categories:update",
        "categories:delete",
        # §4.3 users
        "users:read",
        "users:update",
        "users:update_contact",
        # §4.4 user_types
        "user_types:read",
        "user_types:create",
        "user_types:update",
        "user_types:delete",
        # §4.5 tenants
        "tenants:read",
        "tenants:create",
        "tenants:update",
        "tenants:members_read",
        "tenants:members_manage",
        "tenants:members_set_admin",
        # §4.6 lots
        "lots:read",
        "lots:create",
        "lots:update",
        "lots:delete",
        "lots:link_user",
        "lots:unlink_user",
        "lots:set_delinquency",
        # §4.7 residents
        "residents:read",
        "residents:create",
        "residents:update",
        "residents:delete",
        "residents:link_user",
        "residents:unlink_user",
        # §4.8 visitors
        "visitors:read",
        "visitors:create",
        "visitors:update",
        # §4.9 authorizations
        "authorizations:read",
        "authorizations:create",
        "authorizations:revoke",
        "authorizations:gate_lookup",
        # §4.10 gate
        "gate:checkin",
        "gate:checkout",
        "gate:logs_read",
        # §4.11 occurrences
        "occurrences:read",
        "occurrences:create",
        "occurrences:update_status",
        "occurrences:add_note",
        # §4.12 documents
        "documents:read",
        "documents:create",
        "documents:delete",
        "documents:download",
        "documents:version_create",
        "documents:folder_read",
        "documents:folder_create",
        "documents:folder_update",
        "documents:folder_delete",
        # §4.13 assemblies & votes
        "assemblies:read",
        "assemblies:create",
        "assemblies:update",
        "assemblies:close",
        "assemblies:minutes_read",
        "assemblies:minutes_save",
        "votes:read",
        "votes:create",
        "votes:update",
        "votes:close",
        "votes:cast",
        "votes:retract",
        "votes:tally_read",
        "votes:my_ballot_read",
        "votes:eligible_lots_read",
        "votes:eligibility_read",
        "votes:eligibility_manage",
        # §4.14 finance
        "finance:read",
        "finance:category_create",
        "finance:category_update",
        "finance:budget_create",
        "finance:budget_update",
        "finance:budget_delete",
        "finance:transaction_create",
        "finance:transaction_update",
        "finance:transaction_delete",
        "finance:invoice_upload",
        "finance:invoice_delete",
        # §4.15 projects
        "projects:read",
        "projects:create",
        "projects:update",
        "projects:delete",
        "projects:milestone_create",
        "projects:milestone_update",
        "projects:milestone_delete",
        "projects:update_create",
        "projects:update_delete",
        # §4.16 announcements
        "announcements:read",
        "announcements:create",
        "announcements:update",
        "announcements:delete",
        "announcements:media_upload",
        "announcements:media_delete",
        "announcements:comment",
        "announcements:comment_delete",
        "announcements:mark_read",
        "announcements:read_receipts_read",
        # §4.17 feedback
        "feedback:read",
        "feedback:create",
        "feedback:respond",
        # §4.18 spaces & reservations
        "spaces:read",
        "spaces:create",
        "spaces:update",
        "spaces:deactivate",
        "reservations:read",
        "reservations:create",
        "reservations:approve",
        "reservations:reject",
        "reservations:cancel",
        # §4.19 packages
        "packages:read",
        "packages:create",
        "packages:pickup",
        "packages:queue_read",
        "packages:my_lots_read",
        # §4.20 assets & inventory
        "assets:read",
        "assets:summary_read",
        "assets:create",
        "assets:update",
        "assets:delete",
        "assets:movement_record",
        "inventory:movements_read",
        # §4.21 purchases
        "purchases:read",
        "purchases:summary_read",
        "purchases:create",
        "purchases:update",
        "purchases:delete",
        "purchases:quote_create",
        "purchases:quote_update",
        "purchases:quote_delete",
        "purchases:decide",
        "purchases:cancel",
        # §4.22 uploads (media)
        "uploads:photo_create",
        "uploads:photo_read",
        "uploads:pending_read",
        "uploads:approve",
        "uploads:reject",
        "uploads:delete",
        # §4.23 access_control
        "access_control:devices_read",
        "access_control:device_create",
        "access_control:device_update_status",
        "access_control:device_regenerate_key",
        "access_control:facial_template_read",
        "access_control:facial_template_sync",
        "access_control:events_read",
    }
)


# ---------------------------------------------------------------------------
# (METHOD, path) -> permission (§4)
# ---------------------------------------------------------------------------

ROUTE_PERMISSIONS: dict[tuple[str, str], str] = {
    # §4.1 tasks -- /api/v1/tasks
    ("GET", "/api/v1/tasks/"): "tasks:read",
    ("GET", "/api/v1/tasks/{task_id}/history"): "tasks:read",
    ("GET", "/api/v1/tasks/{task_id}/comments"): "tasks:read",
    ("POST", "/api/v1/tasks/"): "tasks:create",
    ("PATCH", "/api/v1/tasks/{task_id}"): "tasks:update",
    ("DELETE", "/api/v1/tasks/{task_id}"): "tasks:delete",
    ("POST", "/api/v1/tasks/{task_id}/comments"): "tasks:comment",
    ("PATCH", "/api/v1/tasks/{task_id}/comments/{comment_id}"): "tasks:comment",
    # §4.2 categories -- /api/v1/categories
    ("GET", "/api/v1/categories/"): "categories:read",
    ("POST", "/api/v1/categories/"): "categories:create",
    ("PATCH", "/api/v1/categories/{category_id}"): "categories:update",
    ("DELETE", "/api/v1/categories/{category_id}"): "categories:delete",
    # §4.3 users -- /api/v1/users
    ("GET", "/api/v1/users/"): "users:read",
    ("PATCH", "/api/v1/users/{user_id}"): "users:update",
    ("PATCH", "/api/v1/users/{user_id}/contact-info"): "users:update_contact",
    # §4.4 user_types -- /api/v1/user-types
    ("GET", "/api/v1/user-types/"): "user_types:read",
    ("POST", "/api/v1/user-types/"): "user_types:create",
    ("PATCH", "/api/v1/user-types/{user_type_id}"): "user_types:update",
    ("DELETE", "/api/v1/user-types/{user_type_id}"): "user_types:delete",
    # §4.5 tenants -- /api/v1/tenants
    ("GET", "/api/v1/tenants"): "tenants:read",
    ("GET", "/api/v1/tenants/{tenant_id}"): "tenants:read",
    ("POST", "/api/v1/tenants"): "tenants:create",
    ("PATCH", "/api/v1/tenants/{tenant_id}"): "tenants:update",
    ("GET", "/api/v1/tenants/{tenant_id}/members"): "tenants:members_read",
    ("POST", "/api/v1/tenants/{tenant_id}/members"): "tenants:members_manage",
    (
        "DELETE",
        "/api/v1/tenants/{tenant_id}/members/{user_id}",
    ): "tenants:members_manage",
    (
        "PATCH",
        "/api/v1/tenants/{tenant_id}/members/{user_id}",
    ): "tenants:members_set_admin",
    # §4.6 lots -- /api/v1/lots
    ("GET", "/api/v1/lots/"): "lots:read",
    ("GET", "/api/v1/lots/{lot_id}"): "lots:read",
    ("POST", "/api/v1/lots/"): "lots:create",
    ("PUT", "/api/v1/lots/{lot_id}"): "lots:update",
    ("DELETE", "/api/v1/lots/{lot_id}"): "lots:delete",
    ("POST", "/api/v1/lots/{lot_id}/users"): "lots:link_user",
    ("DELETE", "/api/v1/lots/{lot_id}/users/{user_id}"): "lots:unlink_user",
    ("PATCH", "/api/v1/lots/{lot_id}/delinquency"): "lots:set_delinquency",
    # §4.7 residents
    ("GET", "/api/v1/lots/{lot_id}/residents"): "residents:read",
    ("GET", "/api/v1/residents/{resident_id}"): "residents:read",
    ("POST", "/api/v1/lots/{lot_id}/residents"): "residents:create",
    ("PUT", "/api/v1/residents/{resident_id}"): "residents:update",
    ("DELETE", "/api/v1/residents/{resident_id}"): "residents:delete",
    ("POST", "/api/v1/residents/{resident_id}/link-user"): "residents:link_user",
    ("POST", "/api/v1/residents/{resident_id}/unlink-user"): "residents:unlink_user",
    # §4.8 visitors -- /api/v1/visitors
    ("GET", "/api/v1/visitors"): "visitors:read",
    ("GET", "/api/v1/visitors/{visitor_id}"): "visitors:read",
    ("POST", "/api/v1/visitors"): "visitors:create",
    ("PUT", "/api/v1/visitors/{visitor_id}"): "visitors:update",
    # §4.9 authorizations
    ("GET", "/api/v1/lots/{lot_id}/authorizations"): "authorizations:read",
    ("POST", "/api/v1/lots/{lot_id}/authorizations"): "authorizations:create",
    ("PUT", "/api/v1/authorizations/{auth_id}/revoke"): "authorizations:revoke",
    (
        "GET",
        "/api/v1/authorizations/{authorization_id}",
    ): "authorizations:gate_lookup",
    (
        "GET",
        "/api/v1/authorizations/{authorization_id}/qr-code",
    ): "authorizations:gate_lookup",
    # §4.10 gate -- /api/v1/access-logs
    ("POST", "/api/v1/access-logs/check-in"): "gate:checkin",
    ("POST", "/api/v1/access-logs/check-out"): "gate:checkout",
    ("GET", "/api/v1/access-logs"): "gate:logs_read",
    # §4.11 occurrences -- /api/v1/occurrences
    ("GET", "/api/v1/occurrences"): "occurrences:read",
    ("GET", "/api/v1/occurrences/{id}"): "occurrences:read",
    ("POST", "/api/v1/occurrences"): "occurrences:create",
    ("PUT", "/api/v1/occurrences/{id}/status"): "occurrences:update_status",
    ("POST", "/api/v1/occurrences/{id}/timeline"): "occurrences:add_note",
    # §4.12 documents -- /api/v1/documents
    ("GET", "/api/v1/documents"): "documents:read",
    ("POST", "/api/v1/documents"): "documents:create",
    ("DELETE", "/api/v1/documents/{id}"): "documents:delete",
    ("POST", "/api/v1/documents/{id}/download"): "documents:download",
    ("POST", "/api/v1/documents/{id}/versions"): "documents:version_create",
    ("GET", "/api/v1/documents/folders"): "documents:folder_read",
    ("POST", "/api/v1/documents/folders"): "documents:folder_create",
    ("PUT", "/api/v1/documents/folders/{id}"): "documents:folder_update",
    ("DELETE", "/api/v1/documents/folders/{id}"): "documents:folder_delete",
    # §4.13 assemblies -- /api/v1/assemblies
    ("GET", "/api/v1/assemblies/"): "assemblies:read",
    ("GET", "/api/v1/assemblies/{assembly_id}"): "assemblies:read",
    ("POST", "/api/v1/assemblies/"): "assemblies:create",
    ("PATCH", "/api/v1/assemblies/{assembly_id}"): "assemblies:update",
    ("POST", "/api/v1/assemblies/{assembly_id}/close"): "assemblies:close",
    ("GET", "/api/v1/assemblies/{assembly_id}/minutes"): "assemblies:minutes_read",
    (
        "POST",
        "/api/v1/assemblies/{assembly_id}/minutes/save",
    ): "assemblies:minutes_save",
    # §4.13 votes -- /api/v1/votes
    ("GET", "/api/v1/votes/"): "votes:read",
    ("GET", "/api/v1/votes/{vote_id}"): "votes:read",
    ("POST", "/api/v1/votes/"): "votes:create",
    ("PATCH", "/api/v1/votes/{vote_id}"): "votes:update",
    ("POST", "/api/v1/votes/{vote_id}/close"): "votes:close",
    ("POST", "/api/v1/votes/{vote_id}/ballots"): "votes:cast",
    ("POST", "/api/v1/votes/{vote_id}/ballots/retract"): "votes:retract",
    ("GET", "/api/v1/votes/{vote_id}/tally"): "votes:tally_read",
    ("GET", "/api/v1/votes/{vote_id}/my-ballot"): "votes:my_ballot_read",
    ("GET", "/api/v1/votes/{vote_id}/eligible-lots"): "votes:eligible_lots_read",
    # §4.13 voter eligibility -- guarded by voting_service, hence votes:*
    ("GET", "/api/v1/lots/{lot_id}/voter-eligibility"): "votes:eligibility_read",
    ("POST", "/api/v1/lots/{lot_id}/voter-eligibility"): "votes:eligibility_manage",
    (
        "DELETE",
        "/api/v1/lots/{lot_id}/voter-eligibility/{user_id}",
    ): "votes:eligibility_manage",
    # §4.14 finance -- /api/v1/finance
    ("GET", "/api/v1/finance/categories"): "finance:read",
    ("GET", "/api/v1/finance/budget-lines"): "finance:read",
    ("GET", "/api/v1/finance/transactions"): "finance:read",
    ("GET", "/api/v1/finance/transactions/{id}"): "finance:read",
    ("GET", "/api/v1/finance/balance"): "finance:read",
    ("GET", "/api/v1/finance/statement"): "finance:read",
    ("GET", "/api/v1/finance/budget-vs-actual"): "finance:read",
    (
        "GET",
        "/api/v1/finance/budget-vs-actual/{category_id}/transactions",
    ): "finance:read",
    ("POST", "/api/v1/finance/categories"): "finance:category_create",
    ("PUT", "/api/v1/finance/categories/{id}"): "finance:category_update",
    ("POST", "/api/v1/finance/budget-lines"): "finance:budget_create",
    ("PUT", "/api/v1/finance/budget-lines/{id}"): "finance:budget_update",
    ("DELETE", "/api/v1/finance/budget-lines/{id}"): "finance:budget_delete",
    ("POST", "/api/v1/finance/transactions"): "finance:transaction_create",
    ("PUT", "/api/v1/finance/transactions/{id}"): "finance:transaction_update",
    ("DELETE", "/api/v1/finance/transactions/{id}"): "finance:transaction_delete",
    ("POST", "/api/v1/finance/transactions/{id}/invoice"): "finance:invoice_upload",
    ("DELETE", "/api/v1/finance/transactions/{id}/invoice"): "finance:invoice_delete",
    # §4.15 projects -- /api/v1/projects
    ("GET", "/api/v1/projects"): "projects:read",
    ("GET", "/api/v1/projects/{id}"): "projects:read",
    ("POST", "/api/v1/projects"): "projects:create",
    ("PUT", "/api/v1/projects/{id}"): "projects:update",
    ("DELETE", "/api/v1/projects/{id}"): "projects:delete",
    ("POST", "/api/v1/projects/{id}/milestones"): "projects:milestone_create",
    (
        "PUT",
        "/api/v1/projects/{id}/milestones/{milestone_id}",
    ): "projects:milestone_update",
    (
        "DELETE",
        "/api/v1/projects/{id}/milestones/{milestone_id}",
    ): "projects:milestone_delete",
    ("POST", "/api/v1/projects/{id}/updates"): "projects:update_create",
    (
        "DELETE",
        "/api/v1/projects/{id}/updates/{update_id}",
    ): "projects:update_delete",
    # §4.16 announcements -- /api/v1/announcements
    ("GET", "/api/v1/announcements"): "announcements:read",
    ("GET", "/api/v1/announcements/{id}"): "announcements:read",
    ("GET", "/api/v1/announcements/{id}/comments"): "announcements:read",
    ("POST", "/api/v1/announcements"): "announcements:create",
    ("PUT", "/api/v1/announcements/{id}"): "announcements:update",
    ("DELETE", "/api/v1/announcements/{id}"): "announcements:delete",
    ("POST", "/api/v1/announcements/{id}/media"): "announcements:media_upload",
    (
        "DELETE",
        "/api/v1/announcements/{id}/media/{media_id}",
    ): "announcements:media_delete",
    ("POST", "/api/v1/announcements/{id}/comments"): "announcements:comment",
    (
        "DELETE",
        "/api/v1/announcements/comments/{comment_id}",
    ): "announcements:comment_delete",
    ("POST", "/api/v1/announcements/{id}/read"): "announcements:mark_read",
    (
        "GET",
        "/api/v1/announcements/{id}/read-receipts",
    ): "announcements:read_receipts_read",
    # §4.17 feedback -- /api/v1/feedback
    ("GET", "/api/v1/feedback"): "feedback:read",
    ("GET", "/api/v1/feedback/{id}"): "feedback:read",
    ("POST", "/api/v1/feedback"): "feedback:create",
    ("PUT", "/api/v1/feedback/{id}/respond"): "feedback:respond",
    # §4.18 spaces -- /api/v1/reservable-spaces
    ("GET", "/api/v1/reservable-spaces/"): "spaces:read",
    ("POST", "/api/v1/reservable-spaces/"): "spaces:create",
    ("PATCH", "/api/v1/reservable-spaces/{space_id}"): "spaces:update",
    ("DELETE", "/api/v1/reservable-spaces/{space_id}"): "spaces:deactivate",
    # §4.18 reservations -- /api/v1/space-reservations
    ("GET", "/api/v1/space-reservations/"): "reservations:read",
    ("GET", "/api/v1/space-reservations/{reservation_id}"): "reservations:read",
    ("POST", "/api/v1/space-reservations/"): "reservations:create",
    (
        "POST",
        "/api/v1/space-reservations/{reservation_id}/approve",
    ): "reservations:approve",
    (
        "POST",
        "/api/v1/space-reservations/{reservation_id}/reject",
    ): "reservations:reject",
    (
        "POST",
        "/api/v1/space-reservations/{reservation_id}/cancel",
    ): "reservations:cancel",
    # §4.19 packages -- /api/v1/packages
    ("GET", "/api/v1/packages"): "packages:read",
    ("GET", "/api/v1/packages/{package_id}"): "packages:read",
    ("POST", "/api/v1/packages"): "packages:create",
    ("POST", "/api/v1/packages/{package_id}/pickup"): "packages:pickup",
    ("GET", "/api/v1/packages/queue"): "packages:queue_read",
    ("GET", "/api/v1/packages/my-lots"): "packages:my_lots_read",
    # §4.20 assets & inventory
    ("GET", "/api/v1/assets"): "assets:read",
    ("GET", "/api/v1/assets/{asset_id}"): "assets:read",
    ("GET", "/api/v1/assets/summary"): "assets:summary_read",
    ("POST", "/api/v1/assets"): "assets:create",
    ("PUT", "/api/v1/assets/{asset_id}"): "assets:update",
    ("DELETE", "/api/v1/assets/{asset_id}"): "assets:delete",
    ("POST", "/api/v1/assets/{asset_id}/movements"): "assets:movement_record",
    ("GET", "/api/v1/inventory-movements"): "inventory:movements_read",
    # §4.21 purchases -- /api/v1/purchase-requests
    ("GET", "/api/v1/purchase-requests"): "purchases:read",
    ("GET", "/api/v1/purchase-requests/{request_id}"): "purchases:read",
    ("GET", "/api/v1/purchase-requests/summary"): "purchases:summary_read",
    ("POST", "/api/v1/purchase-requests"): "purchases:create",
    ("PUT", "/api/v1/purchase-requests/{request_id}"): "purchases:update",
    ("DELETE", "/api/v1/purchase-requests/{request_id}"): "purchases:delete",
    (
        "POST",
        "/api/v1/purchase-requests/{request_id}/quotes",
    ): "purchases:quote_create",
    (
        "PUT",
        "/api/v1/purchase-requests/{request_id}/quotes/{quote_id}",
    ): "purchases:quote_update",
    (
        "DELETE",
        "/api/v1/purchase-requests/{request_id}/quotes/{quote_id}",
    ): "purchases:quote_delete",
    (
        "POST",
        "/api/v1/purchase-requests/{request_id}/decision",
    ): "purchases:decide",
    ("POST", "/api/v1/purchase-requests/{request_id}/cancel"): "purchases:cancel",
    # §4.22 uploads (media) -- /api/v1/uploads
    ("POST", "/api/v1/uploads/photo"): "uploads:photo_create",
    ("GET", "/api/v1/uploads/photos/{photo_id}"): "uploads:photo_read",
    ("GET", "/api/v1/uploads/photos/pending"): "uploads:pending_read",
    ("PUT", "/api/v1/uploads/photos/{photo_id}/approve"): "uploads:approve",
    ("PUT", "/api/v1/uploads/photos/{photo_id}/reject"): "uploads:reject",
    ("DELETE", "/api/v1/uploads/photos/{photo_id}"): "uploads:delete",
    # §4.23 access_control -- /api/v1/access-control
    ("GET", "/api/v1/access-control/devices"): "access_control:devices_read",
    ("POST", "/api/v1/access-control/devices"): "access_control:device_create",
    (
        "PUT",
        "/api/v1/access-control/devices/{device_id}/status",
    ): "access_control:device_update_status",
    (
        "POST",
        "/api/v1/access-control/devices/{device_id}/regenerate-key",
    ): "access_control:device_regenerate_key",
    (
        "GET",
        "/api/v1/access-control/residents/{resident_id}/facial-template",
    ): "access_control:facial_template_read",
    (
        "POST",
        "/api/v1/access-control/residents/{resident_id}/facial-template/sync",
    ): "access_control:facial_template_sync",
    ("GET", "/api/v1/access-control/events"): "access_control:events_read",
}


# ---------------------------------------------------------------------------
# §4.24 -- the routes that map to no permission
# ---------------------------------------------------------------------------

#: Growing this list is a reviewable decision: `test_permission_registry`
#: asserts its exact length, exactly like `test_tenant_route_scope`'s
#: `GLOBAL_ROUTES`.
UNGUARDED_ROUTES: frozenset[tuple[str, str]] = frozenset(
    {
        ("GET", "/"),  # liveness
        ("GET", "/api/v1/health"),  # liveness
        ("POST", "/api/v1/auth/login"),  # unauthenticated
        ("POST", "/api/v1/auth/signup"),  # unauthenticated
        ("POST", "/api/v1/auth/forgot-password"),  # unauthenticated
        ("POST", "/api/v1/auth/reset-password"),  # unauthenticated
        ("GET", "/api/v1/auth/dev-users"),  # unauthenticated dev helper
        ("POST", "/api/v1/auth/dev-login"),  # unauthenticated dev helper
        ("GET", "/api/v1/auth/me"),  # strictly self-scoped
        # Authenticated by X-Device-Key, no user in the request at all.
        ("POST", "/api/v1/access-control/webhook/verification"),
    }
)


# ---------------------------------------------------------------------------
# The legacy role map (§6)
# ---------------------------------------------------------------------------

#: The §4 "Legacy roles" column, permission by permission. Private: the
#: public shape is `LEGACY_ROLE_PERMISSIONS`, which is this table transposed.
#: `tests/test_legacy_role_permissions.py` derives every row from the live
#: production guard and fails on any drift, so this is a recording of what
#: production decides today, never a second source of truth.
_LEGACY_ROLES_BY_PERMISSION: dict[str, frozenset[UserRole]] = {
    # §4.1 tasks
    "tasks:read": frozenset({A, D, M, R, P}),
    "tasks:create": frozenset({A, D, M, R, P}),
    "tasks:update": frozenset({A, D, M, R, P}),
    "tasks:delete": frozenset({A}),
    "tasks:comment": frozenset({A, D, M, R, P}),
    # §4.2 categories
    "categories:read": ALL_ROLES,
    "categories:create": frozenset({A, D}),
    "categories:update": frozenset({A, D}),
    "categories:delete": frozenset({A, D}),
    # §4.3 users
    "users:read": ALL_ROLES,
    "users:update": frozenset({A}),
    "users:update_contact": frozenset({A, M}),
    # §4.4 user_types
    "user_types:read": ALL_ROLES,
    "user_types:create": frozenset({A}),
    "user_types:update": frozenset({A}),
    "user_types:delete": frozenset({A}),
    # §4.5 tenants
    "tenants:read": ALL_ROLES,
    "tenants:create": frozenset({A}),
    "tenants:update": frozenset({A}),
    "tenants:members_read": ALL_ROLES,
    "tenants:members_manage": frozenset({A}),
    "tenants:members_set_admin": frozenset({A}),
    # §4.6 lots
    "lots:read": frozenset({A, D, M, P}),
    "lots:create": frozenset({A, D}),
    "lots:update": frozenset({A, D}),
    "lots:delete": frozenset({A}),
    "lots:link_user": frozenset({A, D}),
    "lots:unlink_user": frozenset({A, D}),
    "lots:set_delinquency": frozenset({A, D}),
    # §4.7 residents
    "residents:read": ALL_ROLES,
    "residents:create": frozenset({A, D}),
    "residents:update": frozenset({A, D}),
    "residents:delete": frozenset({A, D}),
    "residents:link_user": frozenset({A, D}),
    "residents:unlink_user": frozenset({A, D}),
    # §4.8 visitors
    "visitors:read": ALL_ROLES,
    "visitors:create": ALL_ROLES,
    "visitors:update": ALL_ROLES,
    # §4.9 authorizations
    "authorizations:read": frozenset({A, D, M, G, R}),
    "authorizations:create": frozenset({A, D, M, G, R}),
    "authorizations:revoke": frozenset({A, D, M, G, R}),
    "authorizations:gate_lookup": ALL_ROLES,
    # §4.10 gate
    "gate:checkin": frozenset({A, D, M, P}),
    "gate:checkout": frozenset({A, D, M, P}),
    # Filter, not refusal: `VisitorService.get_access_logs` narrows the query
    # to the caller's linked lots and raises only on an explicit foreign
    # `lot_id`, so at `lot_id=None` no role is refused (§4.10).
    "gate:logs_read": ALL_ROLES,
    # §4.11 occurrences
    "occurrences:read": frozenset({A, D, M, G, R}),
    "occurrences:create": frozenset({A, D, M, G, R}),
    "occurrences:update_status": frozenset({A, D, M, G, R}),
    "occurrences:add_note": frozenset({A, D, M, G, R}),
    # §4.12 documents
    "documents:read": frozenset({A, D, M, G, R}),
    "documents:create": frozenset({A, D}),
    "documents:delete": frozenset({A, D}),
    "documents:download": frozenset({A, D, M, G, R}),
    "documents:version_create": frozenset({A, D}),
    "documents:folder_read": frozenset({A, D, M, G, R}),
    "documents:folder_create": frozenset({A, D}),
    "documents:folder_update": frozenset({A, D}),
    "documents:folder_delete": frozenset({A, D}),
    # §4.13 assemblies & votes
    "assemblies:read": frozenset({A, D, M, R}),
    "assemblies:create": frozenset({A, D}),
    "assemblies:update": frozenset({A, D}),
    "assemblies:close": frozenset({A, D}),
    "assemblies:minutes_read": frozenset({A, D}),
    "assemblies:minutes_save": frozenset({A, D}),
    "votes:read": frozenset({A, D, M, R}),
    "votes:create": frozenset({A, D, M}),
    "votes:update": frozenset({A, D, M}),
    "votes:close": frozenset({A, D, M}),
    "votes:cast": frozenset({A, D, M, R}),
    "votes:retract": frozenset({A, D, M, R}),
    "votes:tally_read": frozenset({A, D, M, R}),
    "votes:my_ballot_read": frozenset({A, D, M, R}),
    "votes:eligible_lots_read": frozenset({A, D, M, R}),
    "votes:eligibility_read": frozenset({A, D, M}),
    "votes:eligibility_manage": frozenset({A, D, M}),
    # §4.14 finance
    "finance:read": frozenset({A, D, M, R}),
    "finance:category_create": frozenset({A, D}),
    "finance:category_update": frozenset({A, D}),
    "finance:budget_create": frozenset({A, D}),
    "finance:budget_update": frozenset({A, D}),
    "finance:budget_delete": frozenset({A, D}),
    "finance:transaction_create": frozenset({A, D, M}),
    "finance:transaction_update": frozenset({A, D, M}),
    "finance:transaction_delete": frozenset({A, D}),
    "finance:invoice_upload": frozenset({A, D, M}),
    "finance:invoice_delete": frozenset({A, D, M}),
    # §4.15 projects
    "projects:read": frozenset({A, D, M, R}),
    "projects:create": frozenset({A, D}),
    "projects:update": frozenset({A, D}),
    "projects:delete": frozenset({A, D}),
    "projects:milestone_create": frozenset({A, D}),
    "projects:milestone_update": frozenset({A, D}),
    "projects:milestone_delete": frozenset({A, D}),
    "projects:update_create": frozenset({A, D, M}),
    "projects:update_delete": frozenset({A, D}),
    # §4.16 announcements
    "announcements:read": frozenset({A, D, M, G, R}),
    "announcements:create": frozenset({A, D}),
    "announcements:update": frozenset({A, D}),
    "announcements:delete": frozenset({A, D}),
    "announcements:media_upload": frozenset({A, D}),
    "announcements:media_delete": frozenset({A, D}),
    "announcements:comment": frozenset({A, D, M, R}),
    "announcements:comment_delete": frozenset({A, D, M, G, R}),
    "announcements:mark_read": frozenset({A, D, M, G, R}),
    "announcements:read_receipts_read": frozenset({A, D}),
    # §4.17 feedback
    "feedback:read": ALL_ROLES,
    "feedback:create": ALL_ROLES,
    "feedback:respond": frozenset({A, D}),
    # §4.18 spaces & reservations
    "spaces:read": ALL_ROLES,
    "spaces:create": frozenset({A, D}),
    "spaces:update": frozenset({A, D}),
    "spaces:deactivate": frozenset({A, D}),
    "reservations:read": frozenset({A, D, M, R, P}),
    "reservations:create": frozenset({A, D, M, R, P}),
    "reservations:approve": frozenset({A, D}),
    "reservations:reject": frozenset({A, D}),
    "reservations:cancel": frozenset({A, D, M, R, P}),
    # §4.19 packages
    "packages:read": frozenset({A, D, M, R, P}),
    "packages:create": frozenset({A, D, M, P}),
    "packages:pickup": frozenset({A, D, M, R, P}),
    "packages:queue_read": frozenset({A, D, M, P}),
    # Inverted gate: `PackageService.get_my_lots` refuses every
    # `_GATEKEEPER_ROLES` member *and* GUEST, leaving RESIDENT alone. This is
    # the one permission ADMINISTRATOR does not hold (§4.19, §11.5).
    "packages:my_lots_read": frozenset({R}),
    # §4.20 assets & inventory
    "assets:read": frozenset({A, D, M}),
    "assets:summary_read": frozenset({A, D, M}),
    "assets:create": frozenset({A, D}),
    "assets:update": frozenset({A, D}),
    "assets:delete": frozenset({A, D}),
    "assets:movement_record": frozenset({A, D, M}),
    "inventory:movements_read": frozenset({A, D, M}),
    # §4.21 purchases
    "purchases:read": frozenset({A, D, M}),
    "purchases:summary_read": frozenset({A, D, M}),
    "purchases:create": frozenset({A, D, M}),
    "purchases:update": frozenset({A, D, M}),
    "purchases:delete": frozenset({A, D, M}),
    "purchases:quote_create": frozenset({A, D, M}),
    "purchases:quote_update": frozenset({A, D, M}),
    "purchases:quote_delete": frozenset({A, D, M}),
    "purchases:decide": frozenset({A, D}),
    # Cancel is a decide-level action today, not a write-level one (§11.3).
    "purchases:cancel": frozenset({A, D}),
    # §4.22 uploads (media)
    "uploads:photo_create": ALL_ROLES,
    "uploads:photo_read": ALL_ROLES,
    "uploads:pending_read": frozenset({A, D}),
    "uploads:approve": frozenset({A, D}),
    "uploads:reject": frozenset({A, D}),
    # Owner-or-staff: `MediaService.delete_photo`'s owner branch admits every
    # role, so on one's own photo no role is refused (§4.22).
    "uploads:delete": ALL_ROLES,
    # §4.23 access_control
    "access_control:devices_read": frozenset({A, D, M}),
    "access_control:device_create": frozenset({A, D}),
    "access_control:device_update_status": frozenset({A, D}),
    "access_control:device_regenerate_key": frozenset({A, D}),
    "access_control:facial_template_read": frozenset({A, D, M}),
    "access_control:facial_template_sync": frozenset({A, D}),
    "access_control:events_read": frozenset({A, D, M}),
    # §4.2 (F2) scope permissions -- the role set each staff bypass has today
    "residents:read_any_lot": frozenset({A, D, M}),
    "visitors:manage_any_lot": frozenset({A, D, M}),
    "occurrences:manage_all": frozenset({A, D}),
    "uploads:auto_approve": frozenset({A, D, M}),
}


# TRANSITIONAL (IAM F1 -> F5). Delete this map, and every reference to it,
# in slice F5. It exists so that F1..F4 can compute permissions for users who
# hold no role rows at all, because NOTHING is seeded: a fresh tenant's roles
# carry no permissions, by the user's explicit decision.
#
# It answers exactly one question: *can a user whose only relevant attribute
# is `role` pass the role-dimension gate of this operation, in the most
# favourable object situation?* It is a coarse upper bound. Every narrowing
# production has today -- the `allowed_menus` menu gate, `Task.visible_to`,
# per-lot linkage, ownership/authorship, per-folder `allowed_roles_json`,
# payload-dependent rules -- stays in code, which is why F4's enforcement
# must be additive (role gate AND permission), never a replacement.
LEGACY_ROLE_PERMISSIONS: dict[UserRole, frozenset[str]] = {
    role: frozenset(
        permission
        for permission, roles in _LEGACY_ROLES_BY_PERMISSION.items()
        if role in roles
    )
    for role in UserRole
}

#: Permissions ADMINISTRATOR does NOT hold. Every entry needs a comment
#: naming the production gate that excludes it. Lived in
#: `tests/test_legacy_role_permissions.py` in F1; moved here by IAM F2 so
#: production (`user_type_service.assert_can_grant`) can read it without
#: importing a test module.
ADMIN_GAP_PERMISSIONS: frozenset[str] = frozenset(
    {
        # PackageService.get_my_lots raises for the gatekeeper roles (incl.
        # ADMINISTRATOR): staff use GET /packages/queue instead.
        "packages:my_lots_read",
    }
)

#: Permissions whose routes are gated by `deps.get_current_superuser` and not
#: by a permission (IAM F3, APRAS-47 §6.1). They stay in the catalogue because
#: they still *name* those routes:
#: `test_permission_registry.py::test_every_catalogue_permission_is_reachable`
#: asserts `set(ROUTE_PERMISSIONS.values()) == PERMISSIONS`, so removing them
#: from the catalogue while their routes remain mapped would turn that test
#: red. They can never be put into a group -- `user_type_service.assert_can_grant`
#: refuses them to every author, superuser included -- because superuser is a
#: column, not a bundle, and a group carrying them would be a lie.
#:
#: `tenants:read` and `tenants:members_read` are deliberately absent: they are
#: ALL_ROLES in the legacy map and gate the two read routes every member
#: reaches, so they stay ordinary, grantable (and inert) permissions.
SUPERUSER_ONLY_PERMISSIONS: frozenset[str] = frozenset(
    {
        "tenants:create",
        "tenants:update",
        "tenants:members_manage",
        "tenants:members_set_admin",
    }
)

#: The slice that deletes `LEGACY_ROLE_PERMISSIONS`. Asserted by
#: `tests/test_legacy_role_permissions.py` so removing the marker is a test
#: failure rather than a silent inheritance.
LEGACY_MAP_REMOVAL_SLICE: str = "IAM F5"


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def permission_for_route(method: str, path: str) -> str | None:
    """The permission guarding `(method, path)`, or None if it has none.

    None covers both the `UNGUARDED_ROUTES` allowlist and an unknown route:
    neither maps to a permission, and this module deliberately knows nothing
    about routing.
    """
    return ROUTE_PERMISSIONS.get((method.upper(), path))


def module_of(permission: str) -> str:
    """The `<module>` segment of a `<module>:<action>` permission string."""
    return permission.split(":", 1)[0]
