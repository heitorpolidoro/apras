# APRAS-14 — QR Code Passes for Visitor Check-In

**Date:** 2026-08-27
**Status:** Approved for implementation

## Problem

A Gatekeeper today finds a visitor's authorization by manually searching name/CPF/plate in `GatekeeperDashboard.tsx`. There's no way to generate a shareable pass for a pre-authorized visitor, or to speed up check-in via a quick scan instead of a manual search.

## Scope Decision (from brainstorming)

"Validation at turnstiles/gates" is **not** physical turnstile hardware integration (no such hardware/protocol exists or is planned) — it's a Gatekeeper (human) scanning a QR code with their device's camera in `GatekeeperDashboard.tsx`, as a faster alternative to manual search. The QR encodes a reference to an existing `VisitorAuthorization`; all of the real access rules (day/shift window, single-vs-permanent, expiration) remain enforced exactly as today by the existing check-in logic (`VisitorService.check_in`) — the QR is a lookup shortcut, not a new authorization or security mechanism. No new signing/token infrastructure is needed: the QR simply encodes the authorization's UUID as plain text, since knowing that UUID alone does not bypass any existing check (the check-in endpoint still validates the window/status rules regardless of how the gatekeeper arrived at the authorization).

## Backend Changes

### New endpoint: `GET /authorizations/{authorization_id}`

`backend/app/api/v1/endpoints/authorizations.py` currently has no single-fetch-by-id endpoint (only `list_lot_authorizations` scoped to a lot, `create_lot_authorization`, `revoke_authorization`). Add one, returning `VisitorAuthorizationRead` (reuse `_to_authorization_read`), 404 if not found. **No role check** — matches this module's existing convention (every route in `authorizations.py` today is reachable by any authenticated user; this is a pre-existing, out-of-scope gap this task does not fix, only follows for consistency).

### New endpoint: `GET /authorizations/{authorization_id}/qr-code`

Returns a QR code image (PNG, `image/png` response) encoding the authorization's `id` (its UUID, as a plain string — no signing, no expiry, no extra payload). 404 if the authorization doesn't exist. Add the `qrcode` Python package (with the `[pil]` extra for PNG rendering) as a new backend dependency.

### `backend/app/schemas/visitor.py`

No new schema needed for the QR endpoint itself (it returns a raw image response, not JSON); the new `GET /authorizations/{id}` endpoint reuses the existing `VisitorAuthorizationRead` schema.

## Frontend Changes

### `VisitorAuthPage.tsx` — "show QR" affordance

Wherever an authorization is listed (the existing per-lot authorization list), add a "Ver QR" button/icon per row, opening a small modal that displays `<img src="{API_BASE}/authorizations/{id}/qr-code" />` — no new API client method needed beyond the base URL construction already used elsewhere for direct image endpoints (check how, e.g., media/photo endpoints are referenced directly by URL elsewhere in this codebase and follow the same pattern for auth-header handling, since this is likely behind the same JWT-protected API — if the existing pattern for direct-image endpoints doesn't already handle auth headers on an `<img>` tag, e.g. via a signed/public URL scheme, resolve this concretely at implementation time using whichever approach this codebase's existing image-serving code already uses, rather than inventing a new one).

### `GatekeeperDashboard.tsx` — "scan QR" affordance

Add a "Escanear QR" button opening a camera view. Use the `html5-qrcode` npm package (handles camera access + continuous frame decoding out of the box, avoiding custom `getUserMedia`/canvas-frame-extraction code). On a successful scan:
1. Parse the decoded text as a UUID (reject/show an error for anything that doesn't look like one — e.g. a QR code from an unrelated source).
2. Call `GET /authorizations/{id}` to fetch the full authorization + visitor details.
3. If found, open the existing `GatekeeperEntryModal` pre-filled with that authorization/visitor — the gatekeeper still reviews and confirms before submitting check-in, identical to today's manual-search flow from that point forward. No new check-in code path.
4. If not found (404) or the authorization's status/window rules would reject it, surface the same error messaging `VisitorService.check_in` already produces for those cases today — no new error-handling logic, reuse what exists.

### New dependency

`html5-qrcode` (frontend). No new backend Python dependency beyond `qrcode[pil]`.

## Non-Goals

- No physical turnstile/hardware integration.
- No expiring, rotating, or cryptographically signed QR tokens — the QR is a stable, non-secret reference to an authorization; all real security enforcement remains exactly where it already lives (`VisitorService.check_in`'s existing validation).
- Not adding RBAC to `authorizations.py` as a whole (pre-existing gap, out of scope — the new endpoints match the module's current no-role-check convention for consistency, not as an endorsement of it).
- No bulk/batch QR generation or printing workflow — one QR per authorization, generated on demand.
- Not wiring QR sharing into WhatsApp (that's APRAS-13, currently blocked on provider setup) — this task only makes the QR code viewable/downloadable in the UI.

## Testing

- **Backend**: `GET /authorizations/{id}` returns the correct authorization / 404 for a missing one. `GET /authorizations/{id}/qr-code` returns a valid PNG (decode it in the test and confirm the embedded text matches the authorization's id) / 404 for a missing one.
- **Frontend**: `VisitorAuthPage`'s QR modal renders the image element with the correct URL. `GatekeeperDashboard`'s scan flow: a successful scan of a valid UUID opens `GatekeeperEntryModal` pre-filled with the fetched authorization; a scan of a non-UUID string shows an error and does not attempt an API call; a scan of a well-formed but non-existent UUID shows a 404-appropriate error.

## Expected Results

1. Any existing visitor authorization has a corresponding QR code image, viewable/downloadable from `VisitorAuthPage`.
2. A Gatekeeper can scan that QR code with their device camera in `GatekeeperDashboard` and reach the same check-in confirmation modal they'd reach via manual search.
3. All existing check-in validation rules (day/shift window, single-vs-permanent, status) are unaffected — scanning is purely a faster path to the same confirmation step, not a bypass.
