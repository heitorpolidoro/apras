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

Returns a QR code image (PNG, `image/png` response) encoding the authorization's `id` (its UUID, as a plain string — no signing, no expiry, no extra payload). 404 if the authorization doesn't exist. Add the `qrcode` Python package as a new backend dependency — the `[pil]` extra is unnecessary since `pillow>=11.0.0` is already a direct backend dependency.

### `backend/app/schemas/visitor.py`

No new schema needed for the QR endpoint itself (it returns a raw image response, not JSON); the new `GET /authorizations/{id}` endpoint reuses the existing `VisitorAuthorizationRead` schema.

## Frontend Changes

### `VisitorAuthPage.tsx` — "show QR" affordance

Wherever an authorization is listed (the existing per-lot authorization list), add a "Ver QR" button/icon per row, opening a small modal that displays the QR image. There is **no existing precedent in this codebase for a JWT-protected `<img>` tag**: the only direct-image-URL pattern here is `/static/uploads/...` (bare `StaticFiles` mount in `backend/app/main.py`), which is deliberately public with no auth, and this app's auth is exclusively Bearer-token-in-header (no cookies) — so a bare `<img src="{API_BASE}/authorizations/{id}/qr-code">` cannot carry the token, and the new endpoint (protected by `deps.get_current_user`) would 401. Implement instead as: on opening the modal, call `apiClient.get(url, { responseType: 'blob' })` (the same `apiClient` used elsewhere in the codebase, which attaches the auth header), then `URL.createObjectURL(blob)` on the response and set that as the `<img>` element's `src`. Revoke the object URL (`URL.revokeObjectURL`) when the modal closes/unmounts to avoid leaking memory.

### `GatekeeperDashboard.tsx` — "scan QR" affordance

Add a "Escanear QR" button opening a camera view. Use the `html5-qrcode` npm package (handles camera access + continuous frame decoding out of the box, avoiding custom `getUserMedia`/canvas-frame-extraction code). At implementation time, do a quick sanity-check of `html5-qrcode`'s recent release history/issues for browser-compatibility regressions before pinning a version — its release cadence has slowed, though this is not reason to pick a different library. On a successful scan:
1. Parse the decoded text as a UUID (reject/show an error for anything that doesn't look like one — e.g. a QR code from an unrelated source).
2. Call `GET /authorizations/{id}` to fetch the full authorization + visitor details.
3. If found, store the scanned `authorization_id` in component state (e.g. a new `scannedAuthorizationId` state variable), and **set `selectedLotId` to the scanned authorization's `lot_id`** — overwriting whatever is currently selected in the manual lot dropdown. The scanned authorization is more specific/authoritative than a stale manual dropdown selection, so this overwrite happens unconditionally on every successful scan, not just when nothing was previously selected.
4. Open the existing `GatekeeperEntryModal` pre-filled with that authorization/visitor — the gatekeeper still reviews and confirms before submitting check-in, identical to today's manual-search flow from that point forward.
5. `handleConfirmCheckIn` must pass the stored `authorization_id` through explicitly to `checkInMutation.mutateAsync` when the check-in originated from a scan (today it calls `checkInMutation.mutateAsync({ visitor_id, lot_id, entry_notes })` and never passes `authorization_id`, even though `AccessLogCheckIn`/`useCheckIn` already supports the field). Without this, `VisitorService.check_in` falls back to the visitor's most-recently-created ACTIVE authorization for that visitor+lot — not necessarily the one actually scanned — silently defeating the purpose of scanning a specific QR when a visitor has more than one active authorization for the same lot. `GatekeeperEntryModal.tsx` already declares an `authorizationId?: string | null` prop in its interface, but it is currently unused/never wired up — this is dead scaffolding to actually wire up (pass it from `GatekeeperDashboard`'s scanned-state through the modal and into `handleConfirmCheckIn`'s call to `mutateAsync`), not evidence this flow already works today.
6. If not found (404) or the authorization's status/window rules would reject it, surface the same error messaging `VisitorService.check_in` already produces for those cases today — no new error-handling logic, reuse what exists.
7. Clear `scannedAuthorizationId` (and stop overriding `selectedLotId` from a scan) once the modal is closed/cancelled or check-in completes, so a subsequent manual-search check-in doesn't accidentally reuse a stale scanned `authorization_id`.

### New dependency

`html5-qrcode` (frontend). No new backend Python dependency beyond `qrcode`.

## Non-Goals

- No physical turnstile/hardware integration.
- No expiring, rotating, or cryptographically signed QR tokens — the QR is a stable, non-secret reference to an authorization; all real security enforcement remains exactly where it already lives (`VisitorService.check_in`'s existing validation).
- Not adding RBAC to `authorizations.py` as a whole (pre-existing gap, out of scope — the new endpoints match the module's current no-role-check convention for consistency, not as an endorsement of it).
- No bulk/batch QR generation or printing workflow — one QR per authorization, generated on demand.
- Not wiring QR sharing into WhatsApp (that's APRAS-13, currently blocked on provider setup) — this task only makes the QR code viewable/downloadable in the UI.

## Testing

- **Backend**: `GET /authorizations/{id}` returns the correct authorization / 404 for a missing one. `GET /authorizations/{id}/qr-code` returns a valid PNG (decode it in the test and confirm the embedded text matches the authorization's id) / 404 for a missing one.
- **Frontend**: `VisitorAuthPage`'s QR modal fetches the image via `apiClient.get(..., { responseType: 'blob' })` and renders the `<img>` with an object URL (mock the blob response and assert the `src` is set, not that a raw URL string is used). `GatekeeperDashboard`'s scan flow: a successful scan of a valid UUID opens `GatekeeperEntryModal` pre-filled with the fetched authorization, sets `selectedLotId` to the scanned authorization's `lot_id`, and confirming check-in calls `checkInMutation.mutateAsync` with the scanned `authorization_id` included; a scan of a non-UUID string shows an error and does not attempt an API call; a scan of a well-formed but non-existent UUID shows a 404-appropriate error; a scan followed by cancelling the modal clears the scanned state so a subsequent manual-search check-in does not pass a stale `authorization_id`.

## Expected Results

1. Any existing visitor authorization has a corresponding QR code image, viewable/downloadable from `VisitorAuthPage`.
2. A Gatekeeper can scan that QR code with their device camera in `GatekeeperDashboard` and reach the same check-in confirmation modal they'd reach via manual search, with the lot selector automatically synced to the scanned authorization's lot.
3. All existing check-in validation rules (day/shift window, single-vs-permanent, status) are unaffected — scanning is purely a faster path to the same confirmation step, not a bypass.
4. Check-in submitted from a scan passes the scanned authorization's specific `authorization_id` to the check-in call, so a visitor with multiple active authorizations for the same lot is checked in against the one actually scanned, not an arbitrary most-recent one.
