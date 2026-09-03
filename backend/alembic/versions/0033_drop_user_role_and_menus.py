"""drop user.role, role.role, allowed_menus and the userrole type (APRAS-49)

Revision ID: 0033_drop_user_role_and_menus
Revises: 0032_rename_user_type_to_role
Create Date: 2026-09-02

Deliverable **B** of IAM F5, and the end of the IAM chain: the `UserRole`
enum, `role.allowed_menus` and the role-implicit membership stop existing,
and every permission a user holds becomes a row.

**It imports nothing from `app/`.** A migration is a historical artefact; if
it read `app.core.permissions` its behaviour would change every time the
catalogue changes. The legacy bundle is inlined below as a literal and its
correctness is pinned against `tests/data/legacy_role_bundles.json`, the
recording made from `LEGACY_ROLE_PERMISSIONS` in this same PR, one last time,
before that map was deleted (§7.6).

Order (§7), and the order is load-bearing:

  0.  the **pre**-condition refuse-guard -- refuse a *widening*, before a
      single write (§7.0 a), and open the downgrade journal (§7.0 b);
  1.  create the legacy role rows a tenant is missing (§7.1);
  2.  backfill bundles, then memberships, then the folder ACL, then add
      `role.landing_path` (§7.2);
  3.  the **post**-condition refuse-guard -- refuse a *narrowing*, after the
      backfill and before any drop (§7.3);
  4.  the drops (§7.4).

**Reversibility (§7.5).** `downgrade()` restores the schema exactly, restores
everything this migration *wrote* exactly (from the journal, with the one
stated exception of §7.1's empty role rows, which stay), and restores what it
*dropped* best-effort. `role.allowed_menus` comes back `[]` for every row --
the pre-drop values are deliberately not journaled and that is the whole of
the loss.

`f5_backfill_journal` **is required** by `downgrade()`, not merely helpful:
with the table missing the downgrade refuses by name and changes nothing, so
`DROP TABLE f5_backfill_journal` is a one-way door. The table has no SQLModel
model and is invisible to `Base.metadata`, so `alembic revision
--autogenerate` at head would propose dropping it; no workflow in this
repository runs autogenerate, and this line exists so that stays a known fact
rather than a lost rollback.
"""

import json

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0033_drop_user_role_and_menus"
down_revision = "0032_rename_user_type_to_role"
branch_labels = None
depends_on = None


#: The six historically-named rows, by legacy role value. Frozen here: it is
#: what `downgrade()` step 3 recomputes `role.role` from, and what §7.1
#: inserts under.
_LEGACY_ROLE_NAMES: dict[str, str] = {
    "ADMINISTRATOR": "Administrador (papel)",
    "DIRECTOR": "Diretor (papel)",
    "MANAGER": "Gerente (papel)",
    "GUEST": "Convidado (papel)",
    "RESIDENT": "Morador (papel)",
    "PORTEIRO": "Porteiro (papel)",
}

#: `downgrade()` step 4's precedence order for recomputing the global
#: `user.role` from per-tenant memberships. Most privileged first.
_ROLE_PRECEDENCE: tuple[str, ...] = (
    "ADMINISTRATOR",
    "DIRECTOR",
    "MANAGER",
    "PORTEIRO",
    "RESIDENT",
    "GUEST",
)

#: The landing preferences the retired enum switch hard-coded (§7.2 step 4).
_LANDING_PATHS: dict[str, str] = {"PORTEIRO": "/gate", "GUEST": "/welcome"}

#: `LEGACY_ROLE_PERMISSIONS[r] | NEW_TIER[r]`, inlined (§5, §7.6). Pinned
#: against `tests/data/legacy_role_bundles.json` by
#: `tests/test_migrations_postgres.py::test_0033_literal_matches_the_recording`.
_LEGACY_BUNDLES: dict[str, list[str]] = {
    "ADMINISTRATOR": [
        "access_control:device_create", "access_control:device_regenerate_key",
        "access_control:device_update_status", "access_control:devices_read",
        "access_control:events_read", "access_control:facial_template_read",
        "access_control:facial_template_sync", "announcements:comment",
        "announcements:comment_delete", "announcements:create",
        "announcements:delete", "announcements:mark_read",
        "announcements:media_delete", "announcements:media_upload",
        "announcements:read", "announcements:read_receipts_read",
        "announcements:update", "assemblies:close", "assemblies:create",
        "assemblies:minutes_read", "assemblies:minutes_save", "assemblies:read",
        "assemblies:update", "assets:create", "assets:delete",
        "assets:movement_record", "assets:read", "assets:summary_read",
        "assets:update", "authorizations:create", "authorizations:gate_lookup",
        "authorizations:read", "authorizations:revoke", "categories:create",
        "categories:delete", "categories:read", "categories:update",
        "documents:create", "documents:delete", "documents:download",
        "documents:folder_create", "documents:folder_delete",
        "documents:folder_read", "documents:folder_update", "documents:read",
        "documents:version_create", "feedback:create", "feedback:read",
        "feedback:respond", "finance:budget_create", "finance:budget_delete",
        "finance:budget_update", "finance:category_create",
        "finance:category_update", "finance:invoice_delete",
        "finance:invoice_upload", "finance:read", "finance:transaction_create",
        "finance:transaction_delete", "finance:transaction_update", "gate:checkin",
        "gate:checkout", "gate:logs_read", "inventory:movements_read",
        "lots:create", "lots:delete", "lots:link_user", "lots:read",
        "lots:set_delinquency", "lots:unlink_user", "lots:update",
        "occurrences:add_note", "occurrences:create", "occurrences:manage_all",
        "occurrences:read", "occurrences:update_status", "packages:create",
        "packages:pickup", "packages:queue_read", "packages:read",
        "projects:create", "projects:delete", "projects:milestone_create",
        "projects:milestone_delete", "projects:milestone_update", "projects:read",
        "projects:update", "projects:update_create", "projects:update_delete",
        "purchases:cancel", "purchases:create", "purchases:decide",
        "purchases:delete", "purchases:quote_create", "purchases:quote_delete",
        "purchases:quote_update", "purchases:read", "purchases:summary_read",
        "purchases:update", "reservations:approve", "reservations:cancel",
        "reservations:create", "reservations:read", "reservations:reject",
        "residents:create", "residents:delete", "residents:link_user",
        "residents:read", "residents:read_any_lot", "residents:unlink_user",
        "residents:update", "roles:create", "roles:delete", "roles:read",
        "roles:update", "spaces:create", "spaces:deactivate", "spaces:read",
        "spaces:update", "tasks:comment", "tasks:create", "tasks:delete",
        "tasks:read", "tasks:read_all", "tasks:update", "tasks:update_any",
        "tenants:create", "tenants:members_manage", "tenants:members_read",
        "tenants:members_set_admin", "tenants:read", "tenants:update",
        "uploads:approve", "uploads:auto_approve", "uploads:delete",
        "uploads:pending_read", "uploads:photo_create", "uploads:photo_read",
        "uploads:reject", "users:read", "users:update", "users:update_contact",
        "visitors:create", "visitors:manage_any_lot", "visitors:read",
        "visitors:update", "votes:cast", "votes:close", "votes:create",
        "votes:eligibility_manage", "votes:eligibility_read",
        "votes:eligible_lots_read", "votes:my_ballot_read", "votes:read",
        "votes:retract", "votes:tally_read", "votes:update",
    ],
    "DIRECTOR": [
        "access_control:device_create", "access_control:device_regenerate_key",
        "access_control:device_update_status", "access_control:devices_read",
        "access_control:events_read", "access_control:facial_template_read",
        "access_control:facial_template_sync", "announcements:comment",
        "announcements:comment_delete", "announcements:create",
        "announcements:delete", "announcements:mark_read",
        "announcements:media_delete", "announcements:media_upload",
        "announcements:read", "announcements:read_receipts_read",
        "announcements:update", "assemblies:close", "assemblies:create",
        "assemblies:minutes_read", "assemblies:minutes_save", "assemblies:read",
        "assemblies:update", "assets:create", "assets:delete",
        "assets:movement_record", "assets:read", "assets:summary_read",
        "assets:update", "authorizations:create", "authorizations:gate_lookup",
        "authorizations:read", "authorizations:revoke", "categories:create",
        "categories:delete", "categories:read", "categories:update",
        "documents:create", "documents:delete", "documents:download",
        "documents:folder_create", "documents:folder_delete",
        "documents:folder_read", "documents:folder_update", "documents:read",
        "documents:version_create", "feedback:create", "feedback:read",
        "feedback:respond", "finance:budget_create", "finance:budget_delete",
        "finance:budget_update", "finance:category_create",
        "finance:category_update", "finance:invoice_delete",
        "finance:invoice_upload", "finance:read", "finance:transaction_create",
        "finance:transaction_delete", "finance:transaction_update", "gate:checkin",
        "gate:checkout", "gate:logs_read", "inventory:movements_read",
        "lots:create", "lots:link_user", "lots:read", "lots:set_delinquency",
        "lots:unlink_user", "lots:update", "occurrences:add_note",
        "occurrences:create", "occurrences:manage_all", "occurrences:read",
        "occurrences:update_status", "packages:create", "packages:pickup",
        "packages:queue_read", "packages:read", "projects:create",
        "projects:delete", "projects:milestone_create", "projects:milestone_delete",
        "projects:milestone_update", "projects:read", "projects:update",
        "projects:update_create", "projects:update_delete", "purchases:cancel",
        "purchases:create", "purchases:decide", "purchases:delete",
        "purchases:quote_create", "purchases:quote_delete",
        "purchases:quote_update", "purchases:read", "purchases:summary_read",
        "purchases:update", "reservations:approve", "reservations:cancel",
        "reservations:create", "reservations:read", "reservations:reject",
        "residents:create", "residents:delete", "residents:link_user",
        "residents:read", "residents:read_any_lot", "residents:unlink_user",
        "residents:update", "roles:read", "spaces:create", "spaces:deactivate",
        "spaces:read", "spaces:update", "tasks:comment", "tasks:create",
        "tasks:read", "tasks:read_all", "tasks:update", "tasks:update_any",
        "tenants:members_read", "tenants:read", "uploads:approve",
        "uploads:auto_approve", "uploads:delete", "uploads:pending_read",
        "uploads:photo_create", "uploads:photo_read", "uploads:reject",
        "users:read", "visitors:create", "visitors:manage_any_lot", "visitors:read",
        "visitors:update", "votes:cast", "votes:close", "votes:create",
        "votes:eligibility_manage", "votes:eligibility_read",
        "votes:eligible_lots_read", "votes:my_ballot_read", "votes:read",
        "votes:retract", "votes:tally_read", "votes:update",
    ],
    "GUEST": [
        "announcements:comment_delete", "announcements:mark_read",
        "announcements:read", "authorizations:create", "authorizations:gate_lookup",
        "authorizations:read", "authorizations:revoke", "categories:read",
        "documents:download", "documents:folder_read", "documents:read",
        "feedback:create", "feedback:read", "gate:logs_read",
        "occurrences:add_note", "occurrences:create", "occurrences:read",
        "occurrences:update_status", "residents:read", "roles:read", "spaces:read",
        "tenants:members_read", "tenants:read", "uploads:delete",
        "uploads:photo_create", "uploads:photo_read", "users:read",
        "visitors:create", "visitors:read", "visitors:update",
    ],
    "MANAGER": [
        "access_control:devices_read", "access_control:events_read",
        "access_control:facial_template_read", "announcements:comment",
        "announcements:comment_delete", "announcements:mark_read",
        "announcements:read", "assemblies:read", "assets:movement_record",
        "assets:read", "assets:summary_read", "authorizations:create",
        "authorizations:gate_lookup", "authorizations:read",
        "authorizations:revoke", "categories:read", "documents:download",
        "documents:folder_read", "documents:read", "feedback:create",
        "feedback:read", "finance:invoice_delete", "finance:invoice_upload",
        "finance:read", "finance:transaction_create", "finance:transaction_update",
        "gate:checkin", "gate:checkout", "gate:logs_read",
        "inventory:movements_read", "lots:read", "occurrences:add_note",
        "occurrences:create", "occurrences:read", "occurrences:read_assigned",
        "occurrences:update_status", "packages:create", "packages:pickup",
        "packages:queue_read", "packages:read", "projects:read",
        "projects:update_create", "purchases:create", "purchases:delete",
        "purchases:quote_create", "purchases:quote_delete",
        "purchases:quote_update", "purchases:read", "purchases:summary_read",
        "purchases:update", "reservations:cancel", "reservations:create",
        "reservations:read", "residents:read", "residents:read_any_lot",
        "roles:read", "spaces:read", "tasks:comment", "tasks:create", "tasks:read",
        "tasks:update", "tenants:members_read", "tenants:read",
        "uploads:auto_approve", "uploads:delete", "uploads:photo_create",
        "uploads:photo_read", "users:read", "users:update_contact",
        "visitors:create", "visitors:manage_any_lot", "visitors:read",
        "visitors:update", "votes:cast", "votes:close", "votes:create",
        "votes:eligibility_manage", "votes:eligibility_read",
        "votes:eligible_lots_read", "votes:my_ballot_read", "votes:read",
        "votes:retract", "votes:tally_read", "votes:update",
    ],
    "PORTEIRO": [
        "authorizations:gate_lookup", "categories:read", "feedback:create",
        "feedback:read", "gate:checkin", "gate:checkout", "gate:logs_read",
        "lots:read", "packages:create", "packages:pickup", "packages:queue_read",
        "packages:read", "reservations:cancel", "reservations:create",
        "reservations:read", "residents:read", "roles:read", "spaces:read",
        "tasks:comment", "tasks:create", "tasks:read", "tasks:read_all",
        "tasks:update", "tasks:update_any", "tenants:members_read", "tenants:read",
        "uploads:delete", "uploads:photo_create", "uploads:photo_read",
        "users:read", "visitors:create", "visitors:read", "visitors:update",
    ],
    "RESIDENT": [
        "announcements:comment", "announcements:comment_delete",
        "announcements:mark_read", "announcements:read", "assemblies:read",
        "authorizations:create", "authorizations:gate_lookup",
        "authorizations:read", "authorizations:revoke", "categories:read",
        "documents:download", "documents:folder_read", "documents:read",
        "feedback:create", "feedback:read", "finance:read", "gate:logs_read",
        "occurrences:add_note", "occurrences:create", "occurrences:read",
        "occurrences:update_status", "packages:my_lots_read", "packages:pickup",
        "packages:read", "projects:read", "reservations:cancel",
        "reservations:create", "reservations:read", "residents:read", "roles:read",
        "spaces:read", "tasks:comment", "tasks:create", "tasks:read",
        "tasks:read_all", "tasks:update", "tasks:update_any",
        "tenants:members_read", "tenants:read", "uploads:delete",
        "uploads:photo_create", "uploads:photo_read", "users:read",
        "visitors:create", "visitors:read", "visitors:update", "votes:cast",
        "votes:eligible_lots_read", "votes:my_ballot_read", "votes:read",
        "votes:retract", "votes:tally_read",
    ],
}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _journal(bind, kind: str, ref_id: str, payload: str, ref_id2=None) -> None:
    """Record one pre-write value. Called immediately *before* each write."""
    bind.execute(
        sa.text(
            "INSERT INTO f5_backfill_journal (kind, ref_id, ref_id2, payload) "
            "VALUES (:kind, :ref_id, :ref_id2, :payload)"
        ),
        {"kind": kind, "ref_id": ref_id, "ref_id2": ref_id2, "payload": payload},
    )


def _refuse_foreign_legacy_links(bind) -> None:
    """§7.0 (a) -- the pre-condition guard, refusing a *widening*.

    Today the six legacy rows carry `permissions = []`, so an **explicit**
    membership in `Diretor (papel)` grants a legacy MANAGER nothing; it only
    widens the id set `Task.visible_to` intersects. After the backfill that
    same row carries DIRECTOR's whole bundle, and that user would silently
    acquire it -- including `tasks:read_all`, i.e. they would stop being
    scoped by `visible_to` at all.

    The state is reachable through the shipped API and through the role
    editor, so it is refused rather than accepted, as the very first
    statement, before a single write. There is deliberately **no override
    flag**: an env var would let the widening ship silently, which is the one
    thing this guard exists to prevent, and the state is always resolvable
    with the SQL the guard itself prints.

    Two neighbouring cases are deliberately **not** refused: a link to a
    non-legacy row (`role IS NULL`, whose bundle this migration never
    touches) and a link to the legacy row that *matches* the user's own enum
    (not a widening; §7.2 step 2 then skips it as already present).
    """
    rows = bind.execute(
        sa.text(
            """
            SELECT u.email, r.name AS role_name, r.role AS legacy_role,
                   t.name AS tenant, u.id AS user_id, r.id AS role_id
            FROM user_role_link l
            JOIN "user"  u ON u.id = l.user_id
            JOIN role    r ON r.id = l.role_id
            JOIN tenant  t ON t.id = r.tenant_id
            WHERE r.role IS NOT NULL
              -- Both sides cast to text: `role.role` is a plain VARCHAR
              -- (migration `0018` chose one deliberately) while `user.role`
              -- is the native `userrole` enum, and Postgres has no operator
              -- between the two.
              AND r.role::text <> u.role::text
            ORDER BY u.email, t.name, r.name
            """
        )
    ).fetchall()
    if not rows:
        return
    listing = "\n".join(
        f"  {row.email} - {row.role_name} ({row.tenant})" for row in rows
    )
    # Not a query: this is the copy-pasteable SQL the guard *prints* as
    # remediation (a), which is why the ids are interpolated into it.
    remediation = "\n".join(
        "  DELETE FROM user_role_link "  # noqa: S608
        f"WHERE user_id = '{row.user_id}' AND role_id = '{row.role_id}';"
        for row in rows
    )
    raise RuntimeError(
        "0033 refuses to run: these users are explicitly linked to a legacy "
        "role row that is not their own role, and the backfill would widen "
        "their permissions.\n"
        f"{listing}\n\n"
        "Nothing has been written. Two remediations, both of which preserve "
        "today's effective permission set exactly:\n"
        "  (1) drop the link -- permissions are unchanged (the row grants "
        "nothing today); the user stops matching tasks targeted at that "
        "legacy row:\n"
        f"{remediation}\n"
        "  (2) move the targeting off the legacy row -- create an ordinary "
        "role in that tenant with permissions = [], link the affected users "
        "to it, add it to the visible_to of the tasks that need them, then "
        "drop the legacy link. Preserves permissions AND targeting."
    )


def _refuse_users_with_no_way_in(bind) -> None:
    """§7.3 -- the post-condition guard, refusing a *narrowing*.

    Run **after** the backfill and before any drop. A pre-condition guard
    would be satisfied by luck (the enum is NOT NULL, so every user trivially
    has a role); as a post-condition it asserts the backfill was complete,
    and it is genuinely reachable: a user with zero `user_tenant_link` rows
    gets zero memberships from §7.2 step 2 and trips it.
    """
    rows = bind.execute(
        sa.text(
            """
            SELECT u.email
            FROM "user" u
            WHERE u.is_active
              AND NOT u.is_superuser
              AND NOT EXISTS (
                  SELECT 1 FROM user_role_link l WHERE l.user_id = u.id
              )
              AND NOT EXISTS (
                  SELECT 1 FROM user_tenant_link t
                  WHERE t.user_id = u.id AND t.is_tenant_admin
              )
            ORDER BY u.email
            """
        )
    ).fetchall()
    if not rows:
        return
    listing = "\n".join(f"  {row.email}" for row in rows)
    raise RuntimeError(
        "0033 refuses to drop the enum: these active users would be left "
        "with no way in -- no role, no tenant_admin capability and no "
        "is_superuser flag.\n"
        f"{listing}\n\n"
        "Give the user a tenant membership and re-run, or set "
        "is_superuser = true."
    )


# ---------------------------------------------------------------------------
# upgrade
# ---------------------------------------------------------------------------


def upgrade() -> None:
    bind = op.get_bind()

    # -- §7.0 (a): refuse the one widening, before a single write -----------
    _refuse_foreign_legacy_links(bind)

    # -- §7.0 (b): open the downgrade journal -------------------------------
    op.create_table(
        "f5_backfill_journal",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("ref_id", sa.String(), nullable=False),
        sa.Column("ref_id2", sa.String(), nullable=True),
        sa.Column("payload", sa.String(), nullable=False),
    )

    # -- §7.1: create the legacy role rows a tenant is missing --------------
    # `0018` seeded five rows in the default tenant; PORTEIRO arrived with
    # `0020` and only ever through `TenantService.ensure_role_types`, so a
    # production tenant can be missing it. Idempotent by the (tenant_id, role)
    # unique index, which still exists at this point.
    #
    # These inserts are deliberately **not** journaled and not reversed: a row
    # created here is an empty legacy role in a tenant that was missing it, it
    # grants nothing, and `ensure_legacy_roles` would have created it on the
    # tenant's next touch anyway. Deleting them on downgrade would be the more
    # surprising behaviour.
    for legacy_role, name in _LEGACY_ROLE_NAMES.items():
        bind.execute(
            sa.text(
                """
                INSERT INTO role (id, tenant_id, name, role, allowed_menus,
                                  permissions)
                SELECT gen_random_uuid(), t.id, :name, :legacy_role,
                       '[]'::json, '[]'::json
                FROM tenant t
                WHERE NOT EXISTS (
                    SELECT 1 FROM role r
                    WHERE r.tenant_id = t.id AND r.role = :legacy_role
                )
                """
            ),
            {"name": name, "legacy_role": legacy_role},
        )

    # -- §7.2 step 1: backfill bundles onto the six legacy rows -------------
    # Unioned, never replaced: an operator may have edited a legacy row
    # through the role editor before this migration ran, and this migration
    # must not be able to revoke.
    legacy_rows = bind.execute(
        sa.text("SELECT id, role, permissions FROM role WHERE role IS NOT NULL")
    ).fetchall()
    for row in legacy_rows:
        current = row.permissions or []
        if isinstance(current, str):
            current = json.loads(current)
        _journal(bind, "role_permissions", str(row.id), json.dumps(current))
        merged = sorted(set(current) | set(_LEGACY_BUNDLES[row.role]))
        bind.execute(
            sa.text("UPDATE role SET permissions = CAST(:perms AS json) WHERE id = :id"),
            {"perms": json.dumps(merged), "id": str(row.id)},
        )

    # -- §7.2 step 2: the implicit membership becomes explicit --------------
    # One row per (user, tenant the user is linked to), joining **only** the
    # legacy role row of that tenant whose `role` equals the user's own --
    # never any other legacy row. That, plus §7.0 (a) having already refused
    # every user whose explicit links point elsewhere, plus non-legacy bundles
    # being untouched, is what makes the backfill effective-set-preserving for
    # the whole population and not merely for the seeded cases.
    new_links = bind.execute(
        sa.text(
            """
            SELECT u.id AS user_id, r.id AS role_id
            FROM "user" u
            JOIN user_tenant_link tl ON tl.user_id = u.id
            JOIN role r ON r.tenant_id = tl.tenant_id
                       AND r.role::text = u.role::text
            WHERE NOT EXISTS (
                SELECT 1 FROM user_role_link l
                WHERE l.user_id = u.id AND l.role_id = r.id
            )
            """
        )
    ).fetchall()
    for link in new_links:
        _journal(
            bind,
            "user_role_link",
            str(link.user_id),
            "{}",
            ref_id2=str(link.role_id),
        )
        bind.execute(
            sa.text(
                "INSERT INTO user_role_link (user_id, role_id) "
                "VALUES (:user_id, :role_id)"
            ),
            {"user_id": str(link.user_id), "role_id": str(link.role_id)},
        )

    # -- §7.2 step 3: the document-folder ACL, forward ----------------------
    # Numbered because the order inside this step matters too: **rename the
    # column, then rewrite its contents, then move the server_default**. The
    # rewrite has to address the new name (a reader that was not updated must
    # fail loudly), and the default must not be moved before a row that still
    # carries strings has been converted.
    #
    # The join key is `role.role`, never `role.name` -- in both directions.
    # `allowed_roles_json` stores enum **values** ("DIRECTOR"); the legacy
    # rows' name is the pt-BR label ("Diretor (papel)"), so a name join
    # matches nothing and would silently empty every folder ACL in every
    # tenant. `role.role` is still present here; §7.4 drops it strictly later,
    # and that ordering is load-bearing.
    op.alter_column(
        "document_folder",
        "allowed_roles_json",
        new_column_name="allowed_role_ids_json",
    )
    role_id_by_tenant_and_role = {
        (str(row.tenant_id), row.role): str(row.id)
        for row in bind.execute(
            sa.text("SELECT id, tenant_id, role FROM role WHERE role IS NOT NULL")
        ).fetchall()
    }
    dropped_unknown = 0
    folders = bind.execute(
        sa.text(
            "SELECT id, tenant_id, allowed_role_ids_json FROM document_folder"
        )
    ).fetchall()
    for folder in folders:
        raw = folder.allowed_role_ids_json
        _journal(bind, "folder_acl", str(folder.id), raw if raw is not None else "")
        try:
            values = json.loads(raw) if raw else []
        except (TypeError, ValueError):
            values = []
        if not isinstance(values, list):
            values = []
        ids: list[str] = []
        for value in values:
            if value not in _LEGACY_ROLE_NAMES:
                # Hand-edited or foreign data: dropped and counted, never a
                # hard failure. A string that *is* a legacy value and finds no
                # row is the opposite case and raises below, because §7.1 makes
                # it impossible and a fallback there is exactly what would
                # swallow the name-vs-value mistake.
                dropped_unknown += 1
                continue
            key = (str(folder.tenant_id), value)
            if key not in role_id_by_tenant_and_role:
                raise RuntimeError(
                    f"0033: folder {folder.id} of tenant {folder.tenant_id} "
                    f"names legacy role {value!r}, which has no role row. "
                    "§7.1 should have made this impossible."
                )
            ids.append(role_id_by_tenant_and_role[key])
        bind.execute(
            sa.text(
                "UPDATE document_folder SET allowed_role_ids_json = :ids "
                "WHERE id = :id"
            ),
            {"ids": json.dumps(ids), "id": str(folder.id)},
        )
    op.alter_column(
        "document_folder", "allowed_role_ids_json", server_default="[]"
    )
    print(
        f"0033: rewrote {len(folders)} document folder ACLs "
        f"({dropped_unknown} unknown role strings dropped)"
    )

    # -- §7.2 step 4: landing_path, the slice's only additive schema --------
    op.add_column("role", sa.Column("landing_path", sa.String(), nullable=True))
    for legacy_role, path in _LANDING_PATHS.items():
        bind.execute(
            sa.text("UPDATE role SET landing_path = :path WHERE role = :role"),
            {"path": path, "role": legacy_role},
        )

    # -- §7.3: refuse a narrowing, after the backfill, before any drop ------
    _refuse_users_with_no_way_in(bind)

    # -- §7.4: the drops, in this order -------------------------------------
    op.drop_index("ix_role_tenant_role", table_name="role")
    op.drop_column("role", "role")
    op.drop_column("role", "allowed_menus")
    op.drop_column("user", "role")
    if bind.dialect.name == "postgresql":
        op.execute("DROP TYPE userrole")


# ---------------------------------------------------------------------------
# downgrade -- the order below is load-bearing (§7.5)
# ---------------------------------------------------------------------------


def downgrade() -> None:
    bind = op.get_bind()

    # -- step 0: refuse if the journal is gone, changing nothing ------------
    if bind.dialect.name == "postgresql":
        present = bind.execute(
            sa.text("SELECT to_regclass('f5_backfill_journal')")
        ).scalar()
    else:  # pragma: no cover - Alembic never runs against SQLite here
        present = sa.inspect(bind).has_table("f5_backfill_journal") or None
    if present is None:
        raise RuntimeError(
            "f5_backfill_journal is missing; 0033 cannot be reversed without "
            "it. Restore the table from a backup, or stay at head."
        )

    # -- step 1: recreate the schema this migration dropped -----------------
    #
    # The two `role` columns had **different types** before `0033`, and the
    # downgrade has to reproduce that rather than tidy it up:
    #
    # * `user.role` is the native `userrole` enum (`0001`, extended by
    #   `0003`/`0014`/`0020`);
    # * `role.role` is a plain VARCHAR, and deliberately so — `0018` explains
    #   why in as many words: it INSERTs `role='RESIDENT'`, a value `0014` had
    #   added with `ALTER TYPE ... ADD VALUE`, and Postgres forbids using a
    #   newly-added enum value in the same transaction that added it. Alembic
    #   runs a whole `upgrade head` in one transaction, so a fresh
    #   base-to-head migration would fail if that column reused the type.
    #
    # `upgrade()`'s two guards already cast around the mismatch
    # (`r.role::text <> u.role::text`), which is the tell. Recreating
    # `role.role` as the enum here would leave a schema that is *not* the
    # pre-`0033` schema and, worse, one that base-to-head could not rebuild.
    userrole = sa.Enum(*_ROLE_PRECEDENCE, name="userrole")
    userrole.create(bind, checkfirst=True)
    op.add_column("role", sa.Column("role", sa.String(), nullable=True))
    op.add_column(
        "role",
        sa.Column(
            "allowed_menus",
            sa.JSON(),
            nullable=False,
            server_default="[]",
        ),
    )
    op.create_index(
        "ix_role_tenant_role", "role", ["tenant_id", "role"], unique=True
    )
    op.add_column(
        "user",
        sa.Column(
            "role", userrole, nullable=False, server_default="GUEST"
        ),
    )

    # -- step 2: the folder-ACL column name and `0010`'s server_default -----
    # Must precede step 5, which writes to a column that does not exist under
    # that name until now. Nothing has touched the *contents* yet: the column
    # still holds role ids, and step 5 is what makes it hold role strings
    # again.
    op.alter_column(
        "document_folder",
        "allowed_role_ids_json",
        new_column_name="allowed_roles_json",
    )
    op.alter_column(
        "document_folder",
        "allowed_roles_json",
        server_default='["ADMINISTRATOR", "DIRECTOR", "MANAGER", "RESIDENT"]',
    )

    # -- step 3: recompute role.role from the frozen name literal -----------
    # Must precede steps 4 and 5: step 4 keys its precedence order on
    # `role.role`, and the folder-ACL restore for post-0033 folders maps ids
    # back through it. A renamed row comes back with `role = NULL`, i.e. as an
    # ordinary role.
    for legacy_role, name in _LEGACY_ROLE_NAMES.items():
        # Plain VARCHAR, per step 1 -- no cast.
        bind.execute(
            sa.text("UPDATE role SET role = :role WHERE name = :name"),
            {"role": legacy_role, "name": name},
        )

    # -- step 4: recompute user.role from the POST-backfill memberships -----
    # **Before** the journal replay of step 5 removes them, and that is the
    # whole point. §7.2 step 2 is precisely the step that turned the implicit
    # role-linked membership into a row: before this migration an ordinary
    # DIRECTOR had *no* `user_role_link` row at all. Reading memberships after
    # the replay would see an empty set for the whole ordinary population and
    # write GUEST -- demoting every non-superuser DIRECTOR/MANAGER/RESIDENT/
    # PORTEIRO in the install on the rollback path.
    #
    # The column is global and memberships are per tenant, so the answer is
    # "the highest-precedence legacy role the user is a member of **in any
    # tenant**"; inventing a per-tenant answer for a global column is not an
    # option. `ADMINISTRATOR` if `is_superuser` (the flag survives untouched);
    # otherwise the precedence order; otherwise `GUEST` (least privilege,
    # chosen over the model's old `DIRECTOR` default on purpose).
    bind.execute(sa.text("""UPDATE "user" SET role = 'GUEST'"""))
    for legacy_role in reversed(_ROLE_PRECEDENCE):
        bind.execute(
            sa.text(
                """
                UPDATE "user" u SET role = CAST(:role AS userrole)
                WHERE EXISTS (
                    SELECT 1 FROM user_role_link l
                    JOIN role r ON r.id = l.role_id
                    WHERE l.user_id = u.id AND r.role = :role
                )
                """
            ),
            {"role": legacy_role},
        )
    bind.execute(
        sa.text("""UPDATE "user" SET role = 'ADMINISTRATOR' WHERE is_superuser""")
    )

    # -- step 5: replay the journal by descending id, then drop it ----------
    # Descending `id` is the only total order available across the three
    # kinds and is the exact inverse of the write order, which matters because
    # the `folder_acl` and `role_permissions` restores are not commutative
    # with a row rewritten more than once.
    entries = bind.execute(
        sa.text(
            "SELECT id, kind, ref_id, ref_id2, payload "
            "FROM f5_backfill_journal ORDER BY id DESC"
        )
    ).fetchall()
    for entry in entries:
        if entry.kind == "folder_acl":
            bind.execute(
                sa.text(
                    "UPDATE document_folder SET allowed_roles_json = :payload "
                    "WHERE id = :id"
                ),
                {"payload": entry.payload, "id": entry.ref_id},
            )
        elif entry.kind == "user_role_link":
            # Backfill-created links go; pre-existing links stay.
            bind.execute(
                sa.text(
                    "DELETE FROM user_role_link "
                    "WHERE user_id = :user_id AND role_id = :role_id"
                ),
                {"user_id": entry.ref_id, "role_id": entry.ref_id2},
            )
        elif entry.kind == "role_permissions":
            # The backfilled bundles are emptied, without discarding
            # permissions an operator had granted a legacy row beforehand.
            bind.execute(
                sa.text(
                    "UPDATE role SET permissions = CAST(:payload AS json) "
                    "WHERE id = :id"
                ),
                {"payload": entry.payload, "id": entry.ref_id},
            )

    # Folders created *after* 0033 have no journal row: map each id back
    # through `role.role` (restored by step 3) and drop any id whose row is an
    # ordinary, non-legacy role.
    journaled = {entry.ref_id for entry in entries if entry.kind == "folder_acl"}
    role_value_by_id = {
        str(row.id): row.role
        for row in bind.execute(
            sa.text("SELECT id, role FROM role WHERE role IS NOT NULL")
        ).fetchall()
    }
    for folder in bind.execute(
        sa.text("SELECT id, allowed_roles_json FROM document_folder")
    ).fetchall():
        if str(folder.id) in journaled:
            continue
        try:
            ids = json.loads(folder.allowed_roles_json or "[]")
        except (TypeError, ValueError):
            ids = []
        values = [
            role_value_by_id[str(item)]
            for item in (ids if isinstance(ids, list) else [])
            if str(item) in role_value_by_id
        ]
        bind.execute(
            sa.text(
                "UPDATE document_folder SET allowed_roles_json = :payload "
                "WHERE id = :id"
            ),
            {"payload": json.dumps(values), "id": str(folder.id)},
        )

    op.drop_table("f5_backfill_journal")

    # -- steps 6 and 7 ------------------------------------------------------
    # `role.allowed_menus` is back as `[]` for every row: the pre-drop values
    # are deliberately not journaled (§7.0 b) and that is the whole of the
    # loss. `landing_path` is dropped.
    op.drop_column("role", "landing_path")
