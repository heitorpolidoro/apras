# User Profile Fields UI — Design Spec

**Meridian task:** `APRAS-7` (originally `user-profile-fields-ui`)
**Date:** 2026-08-10, revised 2026-08-27
**Status:** Approved for planning (revised)

## Revision note (2026-08-27)

Between the original design (2026-08-10) and picking this task up for implementation, the Lot/Resident subsystem shipped (`APRAS-15`/`APRAS-16`, i.e. former `T001`/`T002`): `Lot` now has its own `address`/`block`/`lot_number`, and `Resident` has its own `phone`, both properly structured and already manageable via the existing Lot/Resident admin screens. This made `User.block_lot` — a free-text field meant to informally capture "which unit does this person live in" — redundant with, and strictly worse than, the real `Lot`/`UserLotLink` relationship for anyone who actually lives in a unit.

**Decision**: drop `block_lot` from this UI's scope entirely. The contact-info screen now edits only `phone` and `address` — generic contact fields useful for any user (most relevantly staff — Administrator/Director/Manager — who have no `Lot` to hang a phone number off of; residents' authoritative contact info lives on their `Resident` record). `User.block_lot` becomes an orphaned column with no UI ever writing to it; removing the column itself is out of scope here and tracked separately as a new backlog task (see `.meridian/tasks.json`).

Everything else in this document — who edits, why a separate endpoint, no self-service, no signup changes, no validation — is unchanged from the original design and still holds.

## Problem

The data-layer task ([`2026-08-10-user-profile-fields-design.md`](2026-08-10-user-profile-fields-design.md)) added `phone`, `address`, and (now-superseded) `block_lot` to the `User` model and API schemas, but nothing can read or write `phone`/`address` yet — there's no screen and no permission for anyone but a raw API call to set these values.

## Goal

Give Administrators and Managers a dedicated screen to view and edit any user's `phone` and `address`, without touching the existing admin-only `AdminUserDashboard` (role, active status, user types, name) or the signup flow.

## Scope Decisions (from brainstorming)

| Question | Decision |
|---|---|
| Who can edit these fields? | Administrator and Manager only. No self-service — end users never edit their own profile (no "my profile" page exists or is added). Director and Guest cannot access this. |
| Does this reuse `AdminUserDashboard` / `PATCH /users/{id}`? | No — a separate page and a separate, narrowly-scoped backend endpoint. `AdminUserDashboard` and the existing `PATCH /users/{id}` (admin-only, full field set) are untouched. |
| Do these fields get added to the signup form? | No. Since there's no self-service, there's no reason for the signer-upper to fill them in — they're only ever set afterward by an Administrator or Manager on the new screen. |
| Validation / masking (e.g. Brazilian phone mask)? | None. Free text, optional, matching the already-nullable/unvalidated data layer exactly — no field is required to save. |

## Why a separate endpoint instead of extending `PATCH /users/{id}`

`PATCH /users/{id}` is guarded by `get_current_active_admin` and accepts the full `UserUpdate` schema (role, is_active, user_type_ids, full_name, cpf). Opening it to Managers would require either loosening that guard (risky — Managers would gain a path to touch role/status/type fields unless every field is defensively re-checked at runtime) or bolting a manager-specific field allowlist onto an endpoint whose contract today is "admin, full access." A dedicated endpoint with a dedicated schema makes the restriction structural: `UserContactInfoUpdate` simply has no `role`/`is_active`/`user_type_ids`/`full_name`/`cpf` fields, so a Manager cannot send them regardless of request body — no runtime allowlist logic to get wrong or drift out of sync.

## Backend Changes

### `backend/app/schemas/user.py`

New schema, all fields optional (mirrors the model exactly):

```python
class UserContactInfoUpdate(BaseModel):
    phone: str | None = None
    address: str | None = None
```

### `backend/app/api/deps.py`

New dependency, alongside the existing `get_current_active_admin`:

```python
def get_current_admin_or_manager(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """Verify the current user has ADMINISTRATOR or MANAGER role."""
    if current_user.role not in (UserRole.ADMINISTRATOR, UserRole.MANAGER):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="The user doesn't have enough privileges")
    return current_user
```

### `backend/app/api/v1/endpoints/users.py`

New endpoint, separate from `update_user`:

```python
@router.patch("/{user_id}/contact-info", response_model=UserRead)
def update_user_contact_info(
    *,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(api_deps.get_current_admin_or_manager)],  # noqa: ARG001
    user_id: UUID,
    user_in: UserContactInfoUpdate,
) -> User:
    """Update a user's phone and address. Administrator or Manager only."""
```

Same 404-if-missing behavior as `update_user`; no self-edit safety checks are needed (those exist on `update_user` only to prevent an admin from locking themselves out of role/active-status, which don't apply here).

`GET /users/` is unchanged — it's already available to any authenticated user (`read_users`), so the new page reuses it as-is to list users.

## Frontend Changes

### `ProtectedRoute.tsx`

`requiredRole` widens from `UserRole` to `UserRole | UserRole[]`, backward compatible with every existing single-role usage:

```ts
interface ProtectedRouteProps {
  children: React.ReactElement;
  requiredRole?: UserRole | UserRole[];
}
// ...
const allowed = Array.isArray(requiredRole) ? requiredRole : requiredRole ? [requiredRole] : null;
if (allowed && !allowed.includes(user?.role as UserRole)) {
  return <Navigate to="/dashboard" replace />;
}
```

### New route: `/users/contact-info`

Registered in `App.tsx`, wrapped in `<ProtectedRoute requiredRole={[UserRole.ADMINISTRATOR, UserRole.MANAGER]}>`.

### New page: `frontend/src/features/user-administration/pages/ContactInfoDashboard.tsx`

- Fetches users via the existing `GET /users/` (same query pattern as `AdminUserDashboard`).
- Table columns: full name, email (identification only, read-only), phone, address, and an "Editar" action.
- Edit modal (same visual pattern as `AdminUserDashboard`'s edit modal: `Input` fields, `Button` actions, escape/backdrop-to-close) with two plain text inputs (no mask, no required attribute) for phone/address, saved via `PATCH /users/{id}/contact-info` through a `useMutation`, invalidating the `["users"]` query key on success — same invalidation key `AdminUserDashboard` uses, so both screens stay in sync if open in different tabs.
- No status filter, no search — lists all users. (Can be added later if the user list grows large enough to need it; out of scope now.)

### Navbar

New link (i18n key `nav.contactInfo`) next to "Administração", visible when `user?.role === UserRole.ADMINISTRATOR || user?.role === UserRole.MANAGER`. The existing "Administração" link's visibility rule (`ADMINISTRATOR` only) is unchanged.

### i18n

New keys in `en.json` / `pt.json` for: nav link label, page heading, table column headers, edit modal labels, save/cancel buttons, success/error messages. No changes to existing `signup.*` or `admin.*` keys.

## Non-Goals

- No self-service "my profile" page.
- No changes to `SignupPage`, `AdminUserDashboard`, or the existing `PATCH /users/{id}` endpoint.
- No field validation or input masking.
- No search/filter on the new page.

## Testing

- **Backend**: `update_user_contact_info` — Administrator can update; Manager can update; Director and Guest get 403. None of the project's schemas set `extra="forbid"` (confirmed in `backend/app/schemas/*.py` — default Pydantic v2 behavior applies), so a request body containing `role`/`is_active`/etc. is silently dropped rather than rejected with a 422; add a test asserting a contact-info update leaves the target user's `role`/`is_active`/`user_types` unchanged even when those keys are included in the request body.
- **Frontend**: `ContactInfoDashboard` renders the user list, opens the edit modal, submits the mutation, and invalidates the users query; `ProtectedRoute` correctly allows an array of roles and rejects others; Navbar shows/hides the new link per role (Administrator, Manager, Director, Guest).

## Files Touched (expected)

**Backend — new:**
- Nothing new-file; additions land in existing `schemas/user.py`, `api/deps.py`, `api/v1/endpoints/users.py`.

**Backend — modified:**
- `backend/app/schemas/user.py` (add `UserContactInfoUpdate`)
- `backend/app/api/deps.py` (add `get_current_admin_or_manager`)
- `backend/app/api/v1/endpoints/users.py` (add `update_user_contact_info`)

**Frontend — new:**
- `frontend/src/features/user-administration/pages/ContactInfoDashboard.tsx`

**Frontend — modified:**
- `frontend/src/App.tsx` (new route)
- `frontend/src/features/user-administration/components/ProtectedRoute.tsx` (multi-role support)
- `frontend/src/features/user-administration/components/Navbar.tsx` (new nav link)
- `frontend/src/i18n/locales/en.json`, `pt.json` (new strings)
