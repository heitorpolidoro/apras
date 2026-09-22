# APRAS-72 — Add invitation UI and public acceptance page

Part 3 of the APRAS-67 split. Design:
`docs/superpowers/specs/2026-09-21-tenant-onboarding-and-branded-entry-design.md`,
Deliverable 2. Builds on the approved specs of **APRAS-70** (the
`/admin/tenants` screen, whose three reserved slots this task fills) and
**APRAS-71** (the four invitation routes, whose statuses and response shapes
this task consumes verbatim).

## Scope

**Frontend only.** Two things: (a) the invite action and the per-tenant
invitation list attached to the existing `/admin/tenants` screen, and (b) a
public, unauthenticated acceptance page at `/invite?token=…` that handles both
of APRAS-71's accept branches.

**Not in scope, asserted below:** any file under `backend/`, any Alembic
revision, any new or changed API route, revoking an invitation (D4), the
landing page and `/c/<slug>` (APRAS-74/69), brand colours (APRAS-68), inviting
anyone who is not the condominium's administrator in the system, and any edit
to `ROUTE_PERMISSIONS`, `UNGUARDED_ROUTES` or the parity-matrix baseline.

**Vocabulary.** The invited person is the condominium's **administrator in the
system** (`user_tenant_link.is_tenant_admin`) — *administrador* in pt,
*administrator* in en. *Síndico* is an office of the condominium, a different
thing; the word appears in no string this task adds.

## Decisions

**D1 — the invite action fills APRAS-70's three reserved slots; the screen is
not redesigned.** APRAS-70 D7 reserved (a) an **Administrator** column, (b) a
per-row actions cell, (c) a secondary slot in the post-create success panel.
This task fills exactly those:

- **(a) Administrator column** renders the state of that tenant's **most recent**
  invitation as a badge — *pending* / *accepted* / *expired* — or an em dash
  when the tenant has none. The cell is a button that opens the invitation
  panel (D2).
- **(b) actions cell** carries **“Invite administrator”**, opening a modal with
  a required email field and an optional full name, posting
  `POST /api/v1/invitations` with `{ tenant_id, email, full_name? }`. On `201`
  the modal shows a success state naming the invited email and the tenant, and
  invalidates the invitation queries. `422` renders a translated
  invalid-email message under the field; anything else falls back to
  `parseApiError` with the page's generic key. The submit button is disabled
  while pending and for an empty email.
- **(c) the post-create success panel** gains **“Invite the administrator now”**,
  which opens the same modal with the freshly created tenant preselected.

**D2 — the invitation list is a per-tenant side panel, not a second table on
the page.** `GET /api/v1/invitations?tenant_id=<id>` is the only list APRAS-71
offers, and rendering every tenant's invitations inline would multiply the
requests by the row count for information that is one badge wide. The panel
lists that tenant's invitations **newest first** (the order the endpoint
returns) with, per row: invited email, status badge, sent date (`created_at`),
expiry date (`expires_at`), acceptance date when accepted (`accepted_at`), and
the resend action of D4. Dates render date-only via
`toLocaleDateString(i18n.language)`, the convention APRAS-70 D9 fixed. Loading,
error and empty states mirror the page's existing ones.

**D3 — status is derived in the browser, from the same two timestamps the
backend derives it from.** APRAS-71 D1 stores **no** `status` column:
`accepted_at != null` → accepted, else `new Date(expires_at) <= new Date()` →
expired, else pending. The frontend applies exactly that rule to
`InvitationRead` and never reads a `status` field, so the two cannot disagree.
Clock skew can only mislabel an invitation in the minutes around its expiry,
and the authoritative answer is the `410` the accept call returns anyway.

**D4 — resend is re-issuing; revoke is out of scope.** The pending and expired
rows carry a **“Resend invitation”** action that calls the *same*
`POST /api/v1/invitations` with the same `(tenant_id, email)`. APRAS-71 D4
makes that supersede: the previous row's `expires_at` is set to now and a new
row is inserted, so after invalidation the panel shows the old row as
*expired* and a new *pending* one. This adds no endpoint. **Revoke is
explicitly out of scope and no control for it is drawn:** there is no
`revoked_at` column and no route to call, so it needs a backend change this
task must not make. It is recorded here as a follow-up.

**D5 — the public page is `/invite?token=<raw token>`, and the route is not a
choice this task gets to make.** APRAS-71 D10 already prints and mails
`<origin>/invite?token=…`; picking anything else would break every link the
backend sends. `/invite` collides with none of the 39 paths in `App.tsx` and is
not under `/c/` (APRAS-74). It sits **outside** `ProtectedRoute`, beside
`/login`, `/signup`, `/forgot-password` and `/reset-password`, and therefore
gets **no** `ROUTE_ACCESS` entry, **no** `NAV_ITEMS` entry and **no**
`NAV_GROUPS` membership — exactly like those four. Consequence a reviewer can
check in one line: `routeAccess.ts` and `routeAccess.test.ts` are **not
touched**, and APRAS-70 D8's `NAV_ITEMS.length` restatement stands unchanged.
`Navbar` already returns `null` when unauthenticated, so the page renders
chrome-free like `ResetPasswordPage`. Calls go through `apiClient` as the other
public pages do; its interceptors attach a stale `Authorization` /
`X-Tenant-Id` only when present, and both routes are unguarded and global, so
the headers are inert.

**D6 — the page previews before it asks for anything; `account_exists` chooses
the FORM, the accept response STATUS chooses the OUTCOME.** On mount it posts
the token to
`POST /api/v1/invitations/preview` and renders the invited email, the tenant
name, the tenant slug, the inviter's name and the expiry **before** any input.

**The rule, stated once and binding on both branches:** the preview's
`account_exists` decides **only which form is rendered**. What the page does
**after** a successful accept is decided **solely by the accept response
status**, never by the preview flag:

- **`201`** → a `Token` body is present → `login(access_token, false)` →
  `navigate("/", { replace: true })`.
- **`200`** → no token is returned → the terminal existing-account panel of
  the second bullet below, **no call to `login`, no storage write**.

Both crossings are reachable and both must behave as the table says, because
`account_exists` is computed at preview time and APRAS-71 D8 decides at accept
time: the invitee can sign up at `/signup`, or accept another invitation for
the same address, between the two calls (`200` arriving in the
`account_exists === false` branch), and — symmetrically — an account seen at
preview time can be gone or the backend can decide to provision one (`201`
arriving in the `account_exists === true` branch, which then signs the person
in and lands on `/` exactly like the `201` above). An implementation that
branches on `account_exists` instead of the status is wrong even when it
appears to work. Concretely, `login(undefined, false)` is not a no-op and does
not throw: `AuthContext.login` writes the literal string `"undefined"` into
`sessionStorage.accessToken`, `apiClient` then sends
`Authorization: Bearer undefined` on `/auth/me`, `fetchUser`'s `catch` clears
the key and sets `user` to `null`, and the `navigate("/")` bounces off
`ProtectedRoute` to `/login` — a silent, unexplained failure that looks like a
rejected acceptance.

Then, and only then:

- **`account_exists === false` — new account form.** Fields: full name, CPF,
  password, confirm password. Submit → `POST /api/v1/invitations/accept` →
  status rule above (the expected answer is `201` `Token` →
  `login(access_token, false)` from `AuthContext` → `navigate("/",
  { replace: true })`; a `200` renders the terminal existing-account panel
  instead). `login` clears any previously stored token before
  writing the new one, so an already-signed-in visitor is simply replaced. The
  invited administrator has exactly one membership (APRAS-71 D9), so
  `TenantContext` resolves the acting tenant with no switch gesture.
- **`account_exists === true` — existing-account confirmation.** **No password field, no
  full name, no CPF is rendered at all.** The page states that this email
  already has an APRAS account and that accepting grants it access to the
  condominium; a single confirm button posts `{ token }` to the same accept
  route. On `200` the page renders a terminal success panel — “you now
  administer *<tenant>*; sign in with your current password” — and its only
  action is a link to `/login`. It stores nothing, calls `login` nowhere, and
  **must not say or imply that the person is signed in**: APRAS-71 D8 returns
  no `access_token` and no `Set-Cookie` here on purpose, because mailbox
  possession is a weaker factor than the password that account already holds
  and the key-absent fallback prints the link to stdout.

**D7 — the four failure states, and how the two meanings of `409` are told
apart.** Preview answers (APRAS-71 D7) map one-to-one onto terminal states,
each rendering a message and **no form of any kind**:

| case | state |
|---|---|
| no `token` query param | invalid link (no request is made) |
| `404` | invalid link, “ask the condominium's superuser for a new invitation” |
| `410` | expired link, same recovery text |
| `409` | already used, with a link to `/login` |

On **accept**, `409` is ambiguous: it is either a duplicate CPF (APRAS-71 D9)
or a token consumed meanwhile. The page disambiguates without reading the
backend's English `detail`: it re-issues the **preview** call. If the preview
now answers `409`, the token was consumed and the page switches to the
already-used terminal state; if the preview still answers `200`, the conflict
was the CPF and a translated message renders under the CPF field with every
typed value kept and the form open. A `410` on accept switches to the expired
state. Only the rare conflict path costs the extra request.

**D8 — the superuser gate is inherited, not re-implemented.** The invite
action and the invitation panel live inside `TenantsAdminPage`, which
APRAS-70 puts behind `ROUTE_ACCESS["/admin/tenants"] = { superuser: true }`
read from the real auth user. A non-superuser therefore sees
`RestrictedAccessMessage` in place of the whole screen — the invite control is
not rendered at all — and this task adds no second gate that could drift from
the first.

## Approach

### Behavior

- A superuser on `/admin/tenants` invites an administrator from a row or from
  the post-create panel, sees a `201` success state, and finds the invitation
  as *pending* in that tenant's panel and in the Administrator column.
- Pending and expired invitations can be resent, which supersedes the previous
  one; accepted ones cannot.
- An anonymous visitor opening the mailed `/invite?token=…` sees the invitation
  described, then either the new-account form (and ends up signed in on `/`) or
  the existing-account confirmation (and ends up sent to `/login`, unsigned in).
- Unknown, expired and consumed tokens each render their own message and no
  form.

### Files touched

- `frontend/src/types/invitations.ts` *(new)* — `Invitation` (mirroring
  `InvitationRead`: `id`, `tenant_id`, `email`, `expires_at`, `accepted_at`,
  `accepted_user_id`, `invited_by_user_id`, `created_at`), `InvitationPreview`
  (`email`, `tenant_name`, `tenant_slug`, `inviter_name`, `expires_at`,
  `account_exists`), `InvitationStatus = "pending" | "accepted" | "expired"`
  and the D3 derivation helper.
- `frontend/src/api/invitations.ts` *(new)* — `issueInvitation`,
  `listInvitations(tenantId)`, `previewInvitation(token)`,
  `acceptInvitation(payload)`; paths written exactly as FastAPI mounts them,
  no trailing slash.
- `frontend/src/hooks/useInvitations.ts` *(new)* —
  `useTenantInvitations(tenantId)` on `["invitations", tenantId]`, enabled only
  while a panel is open, and `useIssueInvitation()` invalidating
  `["invitations"]`.
- `frontend/src/features/user-administration/components/InviteAdministratorDialog.tsx`
  *(new)* — the modal of D1(b).
- `frontend/src/features/user-administration/components/TenantInvitationsPanel.tsx`
  *(new)* — the list of D2 with the resend action of D4.
- `frontend/src/features/user-administration/pages/TenantsAdminPage.tsx` — the
  three APRAS-70 placeholders replaced by the real controls; nothing else on
  the screen changes.
- `frontend/src/features/user-administration/pages/AcceptInvitationPage.tsx`
  *(new)* — the public page of D5–D7.
- `frontend/src/App.tsx` — `<Route path="/invite" element={<AcceptInvitationPage />} />`
  beside `/reset-password`, outside `ProtectedRoute`.
- `frontend/src/i18n/locales/en.json`, `frontend/src/i18n/locales/pt.json` — an
  `invitations.*` block (statuses, dialog, panel, resend) and an
  `acceptInvitation.*` block (both branches, the four terminal states, field
  labels and errors), identical key sets, the role named *administrator*.
- `frontend/src/features/user-administration/__tests__/TenantsAdminPage.invitations.test.tsx`
  *(new)*, `…/__tests__/AcceptInvitationPage.test.tsx` *(new)*, and one case
  appended to `frontend/src/__tests__/AppRouting.smoke.test.tsx`.

### Test criteria

`TenantsAdminPage.invitations.test.tsx` (API module mocked):

1. the invite action posts `{ tenant_id, email }` and renders the success state
   on `201`;
2. the panel renders three fixtures — one with `accepted_at` set, one with a
   past `expires_at`, one with neither — as three **distinct** badges;
3. resend on a pending row calls `issueInvitation` with the same tenant and
   email and invalidates `["invitations"]`; the accepted row offers no resend;
4. a non-superuser at `/admin/tenants` sees `RestrictedAccessMessage` and no
   invite control (queried by its label, absent from the document).

`AcceptInvitationPage.test.tsx`:

5. with `account_exists: false`, the preview's email, tenant name and inviter
   render, the password field is present, submitting calls accept and, on
   `201`, stores the token and navigates to `/`;
6. with `account_exists: true`, **no** password field is rendered, accept is
   called with the token alone, the `200` response produces the sign-in-with-
   your-existing-password panel, `localStorage`/`sessionStorage` hold no
   `accessToken`, and the panel links to `/login`;
7. `404`, `410` and `409` from preview each render their own message, and in
   every one of the three `queryByLabelText(password)` is `null`;
8. a missing `token` param renders the invalid-link state and calls no API;
9. with `account_exists: false`, an accept answering **`200`** with an
   `InvitationPreview` body (no `access_token`) renders the terminal
   existing-account panel, calls `login` **never** (the context's `login` is
   spied and asserted not called), writes **no** `accessToken` key in either
   storage — in particular not the string `"undefined"` — and does not
   navigate to `/`; the mirror case, `account_exists: true` with an accept
   answering `201`, stores the token and navigates to `/`;
10. a `409` from accept whose follow-up preview still answers `200` renders the
   CPF conflict under the field and keeps the typed values; a `409` whose
   follow-up preview answers `409` switches to the already-used state.

`AppRouting.smoke.test.tsx`: an unauthenticated visit to `/invite?token=x`
renders the acceptance page and is **not** redirected to the login form.

Gates: `tsc -b` clean; Vitest **80 lines / 78 functions / 76 branches / 80
statements**; ESLint diff-scoped against the baseline of **375 errors +
2 warnings across 64 files**, with no new finding.

## Expected Results

- [ ] The `/admin/tenants` row action and the post-create success panel both open an invite modal that posts `POST /api/v1/invitations` with `{ tenant_id, email }` and renders a success state on `201` (asserted by test).
- [ ] The per-tenant invitation panel derives each row's status from `accepted_at` and `expires_at` only, and renders *pending*, *accepted* and *expired* as three visually distinct badges; a test asserts all three render distinctly and that no `status` field is read from the response.
- [ ] `GET /api/v1/invitations?tenant_id=<id>` is the only list call made, and it is issued only while a tenant's panel is open (not once per table row).
- [ ] Pending and expired rows expose a resend action that re-calls `POST /api/v1/invitations` with the same `(tenant_id, email)` and invalidates `["invitations"]`; accepted rows expose none; no revoke control exists anywhere (asserted by test).
- [ ] `/invite` is registered in `App.tsx` outside `ProtectedRoute`, matching the backend's `<origin>/invite?token=…` accept URL; an unauthenticated visit renders the acceptance page instead of the login form (asserted in `AppRouting.smoke.test.tsx`).
- [ ] `frontend/src/features/user-administration/access/routeAccess.ts` and `…/__tests__/routeAccess.test.ts` appear in **no** diff of this task, and no `NAV_ITEMS` or `NAV_GROUPS` entry is added.
- [ ] Before any input is requested, the page renders the preview's invited email, tenant name, tenant slug, inviter name and expiry, and chooses its branch from `account_exists` (asserted by test).
- [ ] With `account_exists: false`, a successful accept (`201`) stores the returned `access_token` through `AuthContext.login` and navigates to `/`; a test asserts the redirect target.
- [ ] The post-accept outcome is chosen by the accept **response status**, not by the preview's `account_exists`: a test drives the `account_exists: false` form to an accept answering `200` (an `InvitationPreview` body, no `access_token`) and asserts the terminal existing-account panel renders, `AuthContext.login` is not called, no `accessToken` key exists in `localStorage` or `sessionStorage` (in particular not the string `"undefined"`), and no navigation to `/` occurs; the mirror case (`account_exists: true` receiving `201`) signs the person in and navigates to `/`.
- [ ] With `account_exists: true`, the page renders **no** password, full-name or CPF field, accepts with the token alone, and on `200` shows a panel that directs the person to sign in with their existing password and links to `/login`; a test asserts no `accessToken` is written to `localStorage` or `sessionStorage` and that no copy claims the person is signed in.
- [ ] Preview answers `404`, `410` and `409` each render a distinct message with **no** password form; a test asserts the form is absent for all three, and for a missing `token` query param, which makes no API call.
- [ ] A `409` on accept is disambiguated by re-previewing: a duplicate CPF renders inline under the CPF field with the typed values kept, and a consumed token switches to the already-used state (asserted by test).
- [ ] A non-superuser cannot reach the invite action or the invitation list: `/admin/tenants` renders `RestrictedAccessMessage` and neither control is in the document (asserted by test).
- [ ] `docs/tasks/APRAS-72-mock.html` exists, opens standalone, and shows the invite action, the invitation list with all three statuses, and both branches plus the error states of the public acceptance page.
- [ ] `en.json` and `pt.json` remain key-identical after the new `invitations.*` and `acceptInvitation.*` blocks, the key-parity test passes, and `grep -ri "síndico\|sindico"` over the added strings returns nothing.
- [ ] `git diff --name-only` for the task contains no path under `backend/`, no file under `backend/alembic/versions/`, and no change to `tests/data/parity_matrix_baseline.json`.
- [ ] `npx tsc -b` reports no error; `npm run test -- --coverage` meets 80 lines / 78 functions / 76 branches / 80 statements; diff-scoped ESLint reports nothing beyond the 375 errors + 2 warnings across 64 files baseline.

## Out of Scope

Revoking an invitation (needs a backend route this task must not add — D4);
inviting non-administrator members; invitation expiry sweeps; a self-service
“request a new link” from the acceptance page (there is no unauthenticated
issuance route); `/c/<slug>` and the landing page; brand colours; anything
under `backend/`.
