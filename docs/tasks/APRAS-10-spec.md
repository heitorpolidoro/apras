# APRAS-10 — Dedicated Welcome Page for Active Guest Users

**Date:** 2026-08-27
**Status:** Approved for implementation

## Problem

An account starts inactive with role `GUEST` at signup and cannot log in at all until an Administrator activates it (login returns 400 "Inactive user"; the frontend already shows a friendly `login.pendingApproval` message for this case — no change needed there). Once activated, an active `GUEST` who hasn't yet been assigned a proper role by an Administrator can log in successfully, but lands on `/dashboard` like everyone else. Since APRAS-8, that route shows a generic "Acesso restrito" message (the same text any role/menu combination sees when blocked) rather than a blank task board — an improvement, but still generic and not guest-specific.

## Goal

Give an active `GUEST` a purpose-built landing experience after login instead of a generic restricted-access message: land them on a dedicated `/welcome` page explaining their account is approved and awaiting role assignment.

## Scope Decisions (from brainstorming)

| Question | Decision |
|---|---|
| Still worth building, given APRAS-8's generic message already helps? | Yes — the generic message is the same for every blocked role/menu combination; a guest-specific page is more welcoming and can explain the specific next step (wait for an Administrator to assign a role/UserType). |
| Routing mechanism | A new dedicated route `/welcome` + role-based redirect, not conditional content on the existing `/dashboard` route. |
| Content | Static: user's own name/email, an explanatory message, a logout button. No dynamic backend data, no announcements feed or other content — kept deliberately minimal. |

## Frontend Changes

### New page: `frontend/src/features/user-administration/pages/GuestWelcomePage.tsx`

Reads `user` from `useAuth()` (existing `AuthContext`) for name/email display. Static explanatory text (new i18n keys, see below) plus a logout button reusing the existing logout action already used in `Navbar.tsx`. No new API calls.

### New route in `App.tsx`

```tsx
<Route
  path="/welcome"
  element={
    <ProtectedRoute>
      <GuestWelcomePage />
    </ProtectedRoute>
  }
/>
```

No `requiredRole`/`requiredMenu` — any authenticated user can reach `/welcome` directly (there's no harm in a non-Guest visiting it, though nothing routes them there automatically).

### Redirect logic — three places send an active `GUEST` to `/welcome` instead of `/dashboard`

1. **Root redirect**: `App.tsx`'s `<Route path="/" element={<Navigate to="/dashboard" />} />` (or wherever this lives — confirm the exact current implementation) becomes role-aware: `GUEST` → `/welcome`, everyone else → `/dashboard` (unchanged).
2. **Post-login navigation**: `LoginPage.tsx`'s success handler currently navigates to `/dashboard` (or wherever it navigates post-auth) — becomes role-aware the same way. Since the user object isn't available until after `AuthContext`'s `fetchUser` resolves inside `login()`, check the actual current flow (`AuthContext.tsx`'s `login` function) to place this correctly — it may be cleaner to make the root-redirect role-aware (item 1) and have `LoginPage` simply navigate to `/` post-login, letting the root redirect decide, rather than duplicating the role check in two places. Prefer this single-source-of-truth approach if the current code allows it without a larger refactor.
3. **Direct navigation to `/dashboard` or `/categories`**: an active `GUEST` typing either URL directly is redirected to `/welcome` rather than seeing APRAS-8's generic restricted-access message. This is an addition to `ProtectedRoute.tsx`'s existing `requiredMenu` handling, or a small role check at the top of those two routes specifically — do not change `requiredMenu`'s generic behavior for any other role, only add a `GUEST`-specific redirect that takes precedence over it for these two routes.

### i18n

New keys (e.g. under a `guestWelcome` namespace) in `en.json`/`pt.json`: page heading, explanatory body text, logout button label (can reuse the existing `common.logout` key rather than duplicating it).

## Non-Goals

- No backend changes.
- No dynamic content (announcements, profile editing, etc.) on the welcome page.
- Not changing APRAS-8's generic "Acesso restrito" message or its behavior for any role other than the `GUEST`-specific redirect described above.
- Not auditing or changing every other route's behavior for `GUEST` — scope is limited to the login-landing experience and the two routes (`/dashboard`, `/categories`) most likely to be hit directly.

## Testing

- **Frontend**: `GuestWelcomePage` renders the user's name/email and logout works. Root-redirect / post-login navigation test: a `GUEST` user is sent to `/welcome`, a non-`GUEST` user is sent to `/dashboard` (existing behavior unchanged). Direct navigation to `/dashboard`/`/categories` as `GUEST` redirects to `/welcome` rather than rendering the restricted-access message; the same routes for a non-`GUEST` blocked user (e.g. a Director with no qualifying UserType, per APRAS-8) still render the restricted-access message as before — this is the key regression check, since the fix must not change behavior for any role other than `GUEST`.

## Expected Results

1. An active `GUEST` logging in lands on `/welcome`, not `/dashboard`.
2. `/welcome` shows the user's name/email and an explanatory message about pending role assignment.
3. An active `GUEST` navigating directly to `/dashboard` or `/categories` is redirected to `/welcome`.
4. No other role's behavior on `/dashboard`, `/categories`, or the root route changes.
