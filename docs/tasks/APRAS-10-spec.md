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

All three checks below use the user's **real** role (`user?.role` from `useAuth()`), never the simulated role from `useEffectiveIdentity`/`SimulationContext` — except item 3, which is explicitly the one exception (see below). A real Administrator's own root-redirect and post-login navigation must never be affected by an active simulation of another role; this matches how `ProtectedRoute`'s existing `requiredRole`/`requiredRoles` checks already use the real identity.

1. **Root redirect**: `App.tsx`'s existing `<Route path="/" element={<Navigate to="/dashboard" replace />} />` (line 198-201) becomes role-aware, using the real role: `GUEST` → `/welcome`, everyone else → `/dashboard` (unchanged). Note the `isLoading` window in `AuthContext` (before `fetchUser` resolves) means `user` may briefly be `undefined` here; treat that case the same as "everyone else" (default to `/dashboard`) — this isn't a correctness bug because item 3's `ProtectedRoute` check on `/dashboard` acts as a safety net and will still catch a `GUEST` and redirect to `/welcome` once the user loads.
2. **Post-login navigation**: `LoginPage.tsx` (line 38) currently computes `const from = location.state?.from?.pathname || "/dashboard";` and navigates there after `login()` resolves. **Do not change the `from`-based logic** — `location.state.from` is populated by `ProtectedRoute.tsx:49`'s `<Navigate to="/login" state={{ from: location }} replace />` whenever an unauthenticated user is bounced from *any* protected route, not just `/dashboard`, so preserving it is required to keep "return to originally-requested page" working for every role. The only change is the **fallback default**, from `"/dashboard"` to `"/"`:
   ```ts
   const from = location.state?.from?.pathname || "/";
   ```
   This way, an explicit deep-link target is always honored as before, and only the no-deep-link case falls through to the root route, whose role-aware redirect (item 1, using the real role) then decides between `/dashboard` and `/welcome`.
3. **Direct navigation to `/dashboard` or `/categories`**: an active `GUEST` typing either URL directly is redirected to `/welcome` rather than seeing APRAS-8's generic restricted-access message. Concretely, add a new branch in `ProtectedRoute.tsx` immediately before the existing `requiredMenu` restricted-message check:
   ```tsx
   if (requiredMenu && effectiveRole === UserRole.GUEST) {
     return <Navigate to="/welcome" replace />;
   }

   if (requiredMenu && !hasMenuAccess) {
     return <RestrictedAccessMessage />;
   }
   ```
   where `effectiveRole` comes from `useEffectiveIdentity()` (the same hook `useMenuAccess` already uses internally) — i.e. this check uses the **effective/simulated** role, not the real one. This is the deliberate exception to the real-role rule above: it matches `useMenuAccess`'s existing convention on these same two routes, so an Administrator simulating `GUEST` sees the `/welcome` redirect consistently with how they already see the restricted-message behavior today for other simulated roles. The new branch is gated on `requiredMenu` being set, so it can only fire on the two routes that pass `requiredMenu` (`/dashboard`, `/categories`) and never affects any of the ~13 other routes that use `requiredRole`/`requiredRoles` instead.

### i18n

New keys under a `guestWelcome` namespace in `en.json`/`pt.json`:
- `guestWelcome.heading` — page heading (e.g. "Welcome" / "Bem-vindo(a)").
- `guestWelcome.body` — explanatory body text about the account being approved and awaiting role assignment.

Logout button reuses the existing `common.logout` key rather than duplicating it.

## Non-Goals

- No backend changes.
- No dynamic content (announcements, profile editing, etc.) on the welcome page.
- Not changing APRAS-8's generic "Acesso restrito" message or its behavior for any role other than the `GUEST`-specific redirect described above.
- Not auditing or changing every other route's behavior for `GUEST` — scope is limited to the login-landing experience and the two routes (`/dashboard`, `/categories`) most likely to be hit directly.

## Testing

- **Frontend**: `GuestWelcomePage` renders the user's name/email and logout works. Root-redirect / post-login navigation test: a `GUEST` user is sent to `/welcome`, a non-`GUEST` user is sent to `/dashboard` (existing behavior unchanged). A `GUEST` user with an explicit deep-link (`location.state.from`) to some other protected route still returns to that route after login, not to `/welcome` or `/dashboard` (regression check for the `from`-fallback change). Direct navigation to `/dashboard`/`/categories` as `GUEST` redirects to `/welcome` rather than rendering the restricted-access message; the same routes for a non-`GUEST` blocked user (e.g. a Director with no qualifying UserType, per APRAS-8) still render the restricted-access message as before — this is the key regression check, since the fix must not change behavior for any role other than `GUEST`. **Administrator simulating `GUEST` navigating to `/dashboard` is redirected to `/welcome`** (effective-identity check), while that same real Administrator's own root-redirect and post-login navigation are unaffected by the active simulation (real-identity check).

## Expected Results

1. An active `GUEST` logging in lands on `/welcome`, not `/dashboard`.
2. `/welcome` shows the user's name/email and an explanatory message about pending role assignment.
3. An active `GUEST` navigating directly to `/dashboard` or `/categories` is redirected to `/welcome`.
4. No other role's behavior on `/dashboard`, `/categories`, or the root route changes.
