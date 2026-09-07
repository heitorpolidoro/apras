"""The APRAS permission registry (IAM F1, APRAS-45).

Slice 1 of the GCP-style IAM chain: **fine permissions in code -> roles
(permission bundles) as data -> users N:N roles**. This module is the
vocabulary and the wiring; it changes no authorization outcome. Enforcement
is IAM F4.

Deliberately **dependency-free**: no FastAPI, no SQLModel, no session, and
since IAM F5 (APRAS-49) not even a model import. It must stay importable from
Alembic, from a script and from a test that has no database.

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

from collections.abc import Collection, Iterable

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
# Tier permissions (IAM F5, APRAS-49 §3.0)
# ---------------------------------------------------------------------------

#: The three strings that replace the last `role == <enum>.MANAGER`
#: comparisons. They are **grants, not restrictions** -- holding more is never
#: less access -- which is what makes the two legacy tiers expressible in a
#: model with no negative permissions.
#:
#: Like `SCOPE_PERMISSIONS` they are deliberately **not** route-mapped: they
#: are in-code object predicates, so `test_permission_registry`'s reachability
#: rule admits them explicitly rather than being quietly satisfied.
TIER_PERMISSIONS: frozenset[str] = frozenset(
    {
        # deps.assert_manager_can_see_task, endpoints/tasks.py::list_tasks,
        # task_service.create_task and task_service.update_task: see every
        # task regardless of its `visible_to` targets, and author a task
        # without the targets defaulting to the author's own roles.
        # Legacy holders {A, D, R, P} -- i.e. everyone but MANAGER.
        "tasks:read_all",
        # deps.assert_can_edit_task: edit a task assigned to someone else.
        # Legacy holders {A, D, R, P}.
        "tasks:update_any",
        # occurrence_service._check_user_access / get_occurrences: see
        # occurrences assigned to me even without `occurrences:manage_all`.
        # Legacy holders {M} exactly -- MANAGER's whole tier, as data.
        "occurrences:read_assigned",
    }
)


# ---------------------------------------------------------------------------
# The catalogue (§4)
# ---------------------------------------------------------------------------

PERMISSIONS: frozenset[str] = SCOPE_PERMISSIONS | TIER_PERMISSIONS | frozenset(
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
        # §4.4 roles
        "roles:read",
        "roles:create",
        "roles:update",
        "roles:delete",
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
        # §4.24 billing (APRAS-40) -- the subscription area
        # `billing:read` is the *area*; `billing:manage` is the *act of
        # contracting*. Two strings, not one, because a condominium that wants
        # its treasurer to see the plan without being able to contract modules
        # needs exactly this split. Neither implies the other.
        "billing:read",
        "billing:manage",
        # §4.23 access_control
        "access_control:devices_read",
        "access_control:device_create",
        "access_control:device_update_status",
        "access_control:device_regenerate_key",
        "access_control:facial_template_read",
        "access_control:facial_template_sync",
        "access_control:events_read",
        # §4.25 infractions (APRAS-44)
        #
        # **One** module for the whole surface, never a second
        # `infraction_rules` one: `MODULES` is derived from this catalogue, so
        # a second module segment would produce a second independently
        # toggleable feature -- and a tenant with `infractions` on and
        # `infraction_rules` off would own a module it cannot configure. The
        # rule catalogue is a sub-resource, so it carries the sub-resource in
        # the action, on the `projects:milestone_create` precedent.
        "infractions:read",
        "infractions:create",
        "infractions:advance",
        "infractions:promote",
        "infractions:contest",
        "infractions:cycle_close",
        # A **filter**, not an inverted gate: `GET /infractions/my-lots`
        # narrows to the caller's linked lots and refuses nobody, so a staff
        # member with no linked lot gets `[]`. The precedent is
        # `gate:logs_read`, not `packages:my_lots_read` -- which is why
        # `ADMIN_GAP_PERMISSIONS` stays a one-element set.
        "infractions:my_lots_read",
        "infractions:rule_read",
        "infractions:rule_create",
        "infractions:rule_update",
        # `rule_deactivate`, not `rule_delete`: `DELETE` soft-deactivates
        # because infractions reference rules and the lot's history has to
        # stay whole and navigable. The precedent is `spaces:deactivate`.
        "infractions:rule_deactivate",
        "infractions:policy_update",
        "infractions:settings_update",
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
    # §4.4 roles -- /api/v1/roles
    ("GET", "/api/v1/roles/"): "roles:read",
    ("POST", "/api/v1/roles/"): "roles:create",
    ("PATCH", "/api/v1/roles/{role_id}"): "roles:update",
    ("DELETE", "/api/v1/roles/{role_id}"): "roles:delete",
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
    # §4.24 billing -- /api/v1/subscription (APRAS-40 §5.1)
    #
    # No `{tenant_id}` in these paths, on purpose: the subject is the acting
    # tenant, resolved from `X-Tenant-Id` by `get_current_tenant`. A path
    # parameter would be a second, forgeable source of truth. The router is
    # TENANT_SCOPED because a permission-guarded route must resolve an acting
    # tenant -- `get_effective_role_ids` returns the empty set without one.
    ("GET", "/api/v1/subscription"): "billing:read",
    ("GET", "/api/v1/subscription/history"): "billing:read",
    ("PUT", "/api/v1/subscription/modules"): "billing:manage",
    # §4.25 infraction rules & policy -- /api/v1/infraction-rules (APRAS-44)
    ("GET", "/api/v1/infraction-rules"): "infractions:rule_read",
    ("GET", "/api/v1/infraction-rules/{rule_id}"): "infractions:rule_read",
    ("POST", "/api/v1/infraction-rules"): "infractions:rule_create",
    ("PUT", "/api/v1/infraction-rules/{rule_id}"): "infractions:rule_update",
    (
        "DELETE",
        "/api/v1/infraction-rules/{rule_id}",
    ): "infractions:rule_deactivate",
    (
        "PUT",
        "/api/v1/infraction-rules/{rule_id}/policy",
    ): "infractions:policy_update",
    # §4.25 module settings -- the condominium-fee reference (§5). Read is
    # `rule_read` because it is part of configuring the ladder; writing it is
    # its own permission, so a condominium can let a wider group read the
    # policy than can change what a MULTIPLE fine multiplies.
    ("GET", "/api/v1/infraction-settings"): "infractions:rule_read",
    ("PUT", "/api/v1/infraction-settings"): "infractions:settings_update",
    # §4.25 infractions -- /api/v1/infractions
    ("GET", "/api/v1/infractions"): "infractions:read",
    ("GET", "/api/v1/infractions/my-lots"): "infractions:my_lots_read",
    ("GET", "/api/v1/infractions/cycles"): "infractions:read",
    ("GET", "/api/v1/infractions/{infraction_id}"): "infractions:read",
    (
        "GET",
        "/api/v1/infractions/{infraction_id}/next-step",
    ): "infractions:read",
    ("POST", "/api/v1/infractions"): "infractions:create",
    (
        "POST",
        "/api/v1/infractions/from-occurrence/{occurrence_id}",
    ): "infractions:promote",
    (
        "POST",
        "/api/v1/infractions/{infraction_id}/stages",
    ): "infractions:advance",
    (
        "POST",
        "/api/v1/infractions/{infraction_id}/contestation",
    ): "infractions:contest",
    ("POST", "/api/v1/infractions/cycles/close"): "infractions:cycle_close",
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
        # Strictly self-scoped, like /auth/me: "what do I hold here".
        ("GET", "/api/v1/permissions/me"),
        # The static permission vocabulary. No tenant data, no user data;
        # identical for every authenticated caller (IAM F4).
        ("GET", "/api/v1/permissions/"),
        # Authenticated by X-Device-Key, no user in the request at all.
        ("POST", "/api/v1/access-control/webhook/verification"),
        # superuser-only, guarded by deps.get_current_superuser (IAM F5,
        # APRAS-49 §8.4). It maps to no catalogue permission on purpose:
        # `is_superuser` is a column, not a bundle, so minting a permission
        # whose only job is to be refused by `assert_can_grant` -- and paying
        # six parity-baseline cells for it -- would be the wrong trade.
        ("PATCH", "/api/v1/users/{user_id}/superuser"),
        # Per-tenant module activation: superuser-only, guarded by
        # deps.get_current_superuser (APRAS-39 §6.4). Same convention and
        # same reason as the line above -- minting two catalogue strings
        # whose only purpose is to be refused by `assert_can_grant` would
        # cost 12 parity cells (2 routes x 6 profiles) that cannot exist at
        # the baseline sha, and would move the golden file.
        ("GET", "/api/v1/tenants/{tenant_id}/modules"),
        ("PUT", "/api/v1/tenants/{tenant_id}/modules"),
        # The commercial surfaces of APRAS-40: the install-wide plan
        # catalogue and the three per-tenant subscription routes. Same
        # convention and same reason as the two lines above -- minting seven
        # catalogue strings whose only purpose is to be refused by
        # `assert_can_grant` would cost 42 parity cells for nothing.
        # superuser-only, guarded by deps.get_current_superuser (APRAS-40)
        ("GET", "/api/v1/plans/"),
        # superuser-only, guarded by deps.get_current_superuser (APRAS-40)
        ("POST", "/api/v1/plans/"),
        # superuser-only, guarded by deps.get_current_superuser (APRAS-40)
        ("GET", "/api/v1/plans/{plan_id}"),
        # superuser-only, guarded by deps.get_current_superuser (APRAS-40)
        ("PATCH", "/api/v1/plans/{plan_id}"),
        # superuser-only, guarded by deps.get_current_superuser (APRAS-40)
        ("GET", "/api/v1/tenants/{tenant_id}/subscription"),
        # superuser-only, guarded by deps.get_current_superuser (APRAS-40)
        ("PUT", "/api/v1/tenants/{tenant_id}/subscription"),
        # superuser-only, guarded by deps.get_current_superuser (APRAS-40)
        ("PUT", "/api/v1/tenants/{tenant_id}/subscription/courtesy"),
        # APRAS-52: the fourth per-tenant subscription route, the operator's
        # change-history read. Same convention and same reason as the three
        # lines above -- it maps to no catalogue permission, so it adds no
        # parity cell and no baseline file.
        # superuser-only, guarded by deps.get_current_superuser (APRAS-52)
        ("GET", "/api/v1/tenants/{tenant_id}/subscription/history"),
    }
)


# ---------------------------------------------------------------------------
# Permissions no bundle can usefully carry (§8)
# ---------------------------------------------------------------------------

#: Permissions whose production gate refuses the staff tiers, so putting one
#: in a staff bundle grants that member nothing. Every entry needs a comment
#: naming the gate that excludes it.
#:
#: IAM F5 (APRAS-49 §8) keeps the constant and drops its **role framing**: it
#: used to be spelled "permissions ADMINISTRATOR does not hold" and was
#: derived from `LEGACY_ROLE_PERMISSIONS`, which no longer exists. What it
#: records is a property of the *code*, not of a retired enum — and that
#: property is what makes it survive the enum. It is pinned by
#: `tests/test_permission_registry.py`.
ADMIN_GAP_PERMISSIONS: frozenset[str] = frozenset(
    {
        # PackageService.get_my_lots refuses every caller holding
        # `packages:queue_read`: staff use GET /packages/queue instead, and
        # "my lots" is meaningless for a caller with no lot link.
        "packages:my_lots_read",
    }
)

#: Permissions whose routes are gated by `deps.get_current_superuser` and not
#: by a permission (IAM F3, APRAS-47 §6.1). They stay in the catalogue because
#: they still *name* those routes:
#: `test_permission_registry.py::test_every_catalogue_permission_is_reachable`
#: asserts `set(ROUTE_PERMISSIONS.values()) == PERMISSIONS`, so removing them
#: from the catalogue while their routes remain mapped would turn that test
#: red. They can never be put into a group -- `role_service.assert_can_grant`
#: refuses them to every author, superuser included -- because superuser is a
#: column, not a bundle, and a group carrying them would be a lie.
#:
#: `tenants:read` and `tenants:members_read` are deliberately absent: they
#: gate the two read routes every member reaches, so they stay ordinary,
#: grantable (and inert) permissions.
SUPERUSER_ONLY_PERMISSIONS: frozenset[str] = frozenset(
    {
        "tenants:create",
        "tenants:update",
        "tenants:members_manage",
        "tenants:members_set_admin",
    }
)

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


# ---------------------------------------------------------------------------
# The per-tenant module vocabulary (APRAS-39 §2)
# ---------------------------------------------------------------------------

#: Every module named by the catalogue. Derived, never hand-listed: a module
#: introduced by a future task is toggleable (and active) the day its first
#: permission exists, with nobody having to remember a second list.
MODULES: frozenset[str] = frozenset(module_of(permission) for permission in PERMISSIONS)

#: The modules a tenant can never turn off: identity, membership, the
#: authorization vocabulary itself and the subscription area. Disabling any of
#: them would make the tenant unadministrable from inside -- no user list, no
#: role editor, no tenant switcher -- and would strip the very permissions the
#: operator needs to turn it back on from the tenant side.
#:
#: `billing` is core and it is load-bearing (APRAS-40 §2.1): `MODULES` is
#: derived from `PERMISSIONS`, so `billing` became a module the day
#: `billing:read` existed. If it were toggleable, a plan (or an operator)
#: could turn it off and the condominium would lose the only surface from
#: which it can contract anything back on -- the exact lock-out this constant
#: exists to prevent.
CORE_MODULES: frozenset[str] = frozenset(
    {"tenants", "users", "roles", "billing"}
)

#: The 23 billable features.
TOGGLEABLE_MODULES: frozenset[str] = MODULES - CORE_MODULES


def filter_by_modules(
    permissions: Iterable[str], disabled: Collection[str]
) -> frozenset[str]:
    """`permissions` minus every string whose module is in `disabled`.

    Pure and session-free, like everything else in this module. Strings whose
    module is not a catalogue module (a hand-edited row) are *kept*: the
    filter removes only what an operator explicitly turned off, which is what
    preserves `deps.get_effective_permissions`'s documented "unknown strings
    are kept as is" property.
    """
    return frozenset(
        permission
        for permission in permissions
        if module_of(permission) not in disabled
    )
