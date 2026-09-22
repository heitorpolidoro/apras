# APRAS-71 — Administrator invitation backend with single-use tokens

Part 2 of the APRAS-67 split. Design:
`docs/superpowers/specs/2026-09-21-tenant-onboarding-and-branded-entry-design.md`,
Deliverable 2. Siblings: APRAS-70 (superuser condominium screen, frontend
only), APRAS-72 (invitation UI + public acceptance page, which consumes every
route below).

## Scope

**Backend only.** A `tenant_invitation` table, a reusable mail sender extracted
from the inline Resend block in `app/api/v1/endpoints/auth.py:261-293`, four
routes (superuser issuance, superuser list, public preview, public accept), and
their registration in the permission and tenant-scope registries.

**Vocabulary.** The invited person is the condominium's **administrator in the
system** — `user_tenant_link.is_tenant_admin`. That is a system role, not one of
the condominium's own elected offices, which this task neither grants nor names;
the name of that office appears nowhere in this task's files.

**Not in scope:** any file under `frontend/` (APRAS-72), revoking or resending
an invitation from the UI, inviting anyone who is not an administrator,
`/c/<slug>` and the landing page (APRAS-69), brand colours (APRAS-68), any edit
to `0001_initial_schema.py`, and any new catalogue permission string.

## Decisions

**D1 — the table stores a hash, never the token.**
`tenant_invitation`, a **global** (unscoped) table like `tenant` and
`user_tenant_link`:

| column | type | notes |
|---|---|---|
| `id` | UUID PK | |
| `tenant_id` | UUID NOT NULL | FK `tenant.id`, `ondelete="RESTRICT"`, indexed |
| `email` | str NOT NULL, indexed | stored `.strip().lower()` |
| `token_hash` | str(64) NOT NULL **unique** | SHA-256 hex of the raw token |
| `expires_at` | datetime NOT NULL | naive UTC, written by `clock.db_now()` + TTL |
| `accepted_at` | datetime NULL | **the single-use marker**: NULL = not yet consumed |
| `accepted_user_id` | UUID NULL | FK `user.id`, `ondelete="SET NULL"` |
| `invited_by_user_id` | UUID NOT NULL | FK `user.id`, `ondelete="RESTRICT"` |
| `created_at`, `updated_at` | datetime NOT NULL | `clock.db_now` |

The raw token is 32 random bytes from `secrets.token_urlsafe(32)`, returned from
the service **only** to the mail sender and never stored, never logged to the
database, never in any response body. SHA-256 rather than bcrypt: the token is
256 bits of entropy, so it is not guessable and needs an indexable exact-match
lookup; bcrypt would force a table scan. A stored raw credential would turn any
database dump into an account takeover, which is why it is not stored.

**No `status` column.** State is derived — `accepted_at IS NOT NULL` → accepted,
else `expires_at <= db_now()` → expired, else pending. A second stored field can
disagree with the two timestamps; these cannot disagree with themselves.

**D2 — lifetime is 7 days**, from a new `INVITATION_EXPIRE_HOURS: int = 168` in
`app/core/config.py` (env-overridable). Not the 15 minutes of
`create_password_reset_token`: a person has to receive mail and pick a moment.

**D3 — a stored row, not a JWT.** `security.create_password_reset_token`
(`app/core/security.py:79`) is a stateless JWT: replayable until expiry,
unrevocable, and carrying no tenant. Single use requires state, so it is a row.
That token flow is otherwise untouched.

**D4 — re-issuing supersedes.** Issuing for a `(tenant_id, email)` pair that
already has a pending, unexpired invitation sets that row's `expires_at` to
`db_now()` before inserting the new one, so a superseded token previews as
*expired* rather than as unknown, without a `revoked_at` column.

"At most one live token per pair" is the intent and is **best-effort, not an
invariant**: the supersede reads with a plain `select` before inserting, so two
issues racing for the same pair each read before the other commits and both
insert. The window is not closable with `with_for_update()` (there is no row to
lock against a phantom) nor with a partial unique index (the condition involves
`now()`); it would take an advisory lock on a hash of the pair. It is left open
deliberately — both tokens were minted by a superuser for the same address, on
purpose, and each is still single-use.

**D5 — the token travels in a request body, never in a URL.** Both public routes
are `POST` (the preview included, despite being a read) because a token in a
path or query string lands in access logs, in `Referer` headers and in browser
history.

**D6 — four routes, all in `UNGUARDED_ROUTES`, zero new `ROUTE_PERMISSIONS`
entries.** New module `app/api/v1/endpoints/invitations.py`, mounted at
`/invitations` with `GLOBAL_SCOPED` dependencies:

| route | guard | success |
|---|---|---|
| `POST /api/v1/invitations` | `deps.get_current_superuser` | `201` `InvitationRead` |
| `GET /api/v1/invitations` | `deps.get_current_superuser`, optional `tenant_id` query | `200` `list[InvitationRead]` |
| `POST /api/v1/invitations/preview` | none, `@limiter.limit("5/minute")` | `200` `InvitationPreview` |
| `POST /api/v1/invitations/accept` | none, `@limiter.limit("5/minute")` | `201` `Token` (new account) / `200` `InvitationPreview` (existing account, **no token** — D8) |

The two superuser routes follow the `/api/v1/plans/*` and
`/api/v1/tenants/{id}/modules` precedent recorded in
`app/core/permissions.py:698`: a superuser-only route maps to **no** catalogue
permission, because `is_superuser` is a column and not a bundle, and minting a
string whose only job is to be refused by `assert_can_grant` costs six parity
cells for nothing. The two public routes are unauthenticated, like
`/auth/forgot-password`. Consequence, stated so a reviewer can check it in one
line: **`tests/data/parity_matrix_baseline.json` is not modified at all** — the
"additive only" requirement is met by adding nothing, and any diff to that file
is a defect of this task.

`InvitationRead` never contains `token_hash` and never contains a raw token.

Because all four routes are unguarded, the new `invitations` tag has **zero**
`ROUTE_PERMISSIONS` entries and therefore becomes a *fully unguarded tag* in the
sense of `tests/test_permission_registry.py:43`. That constant
(`FULLY_UNGUARDED_TAGS`) must gain `"invitations"`, or
`test_every_router_module_has_at_least_one_permission` (`:220-229`) fails on the
exact-set assertion `silent == sorted(FULLY_UNGUARDED_TAGS)`. The tag qualifies
for the same reason `plans` does: every route in it is either superuser-only (a
column, not a catalogue bundle) or deliberately public.

**D7 — expired, consumed and unknown are three distinguishable HTTP statuses,
and none of them echoes the invited email.**

| case | status | body `detail` |
|---|---|---|
| unknown or malformed token | `404` | generic "convite inválido" |
| `expires_at <= db_now()` | `410` | "convite expirado" |
| `accepted_at IS NOT NULL` | `409` | "convite já utilizado" |

This does not contradict the design's D6 existence-leak rule: that rule protects
*enumerable* identifiers (emails, slugs). A 256-bit token is not enumerable, and
whoever holds a real one is the invitee, who needs to know whether to ask for a
new link or simply sign in. All three follow the same single indexed lookup by
`token_hash`, so there is no timing oracle, and no failing response carries the
email, the tenant name or the inviter.

**D8 — an email that already has an account is linked, not recreated, and its
password is not touched.** Issuance still returns `201` (inviting an existing
user to administer another condominium is a real case). On accept, if a `user`
row with that email exists: no user is created, `full_name`, `cpf` and
`password` in the body are **ignored**, the existing `UserTenantLink` for that
tenant is created or updated with `is_tenant_admin=True`, `is_active` is forced
`True`, and the response is `200`. Silently resetting an existing account's
password from an invitation someone else issued is an account-takeover path and
is refused.

**No session is minted in this branch.** The `200` response carries the
`InvitationPreview` shape (invited email, tenant name and slug, `expires_at`,
`account_exists=True`) and **no `access_token`, no refresh token, no
`Set-Cookie`**. The existing user then signs in normally with the password that
account already has; APRAS-72 sends them to the login screen. Three reasons,
written here so the decision is not re-litigated in review:

1. Returning a token would be a *strictly stronger* takeover than the password
   reset this same decision refuses — it hands the bearer an authenticated
   session for an account they may not control at all.
2. Mailbox possession is a weaker factor than the password that account already
   holds, and an invitation must not be able to bypass the stronger factor.
3. With `RESEND_API_KEY` absent, D10's fallback prints the accept URL — token
   included — to stdout, so in exactly the environments where it is most likely
   to leak, the token is readable by anyone with log access.

Granting a membership to an account you do not control is recoverable by an
administrator; handing out a live session for it is not. The new-account branch
answers `201` with a `Token`, so the two branches remain distinguishable by
status alone. `InvitationPreview` carries
`account_exists: bool` so APRAS-72 can drop the password field in that branch.

**D9 — what accepting does, and how it differs from signup.** The new-account
branch creates a `User` with the submitted `full_name`, `cpf` and password hash
and **`is_active=True`**, plus exactly one `UserTenantLink`
(`tenant_id = invitation.tenant_id`, `is_tenant_admin=True`) and **zero**
`user_role_link` rows. Three deliberate differences from
`POST /api/v1/auth/signup`:

1. *Active, not pending.* Signup is unvetted self-service, so an administrator
   approves it. An invitation **is** that approval — issued by a superuser to an
   address they chose and delivered to that mailbox. Requiring a second approval
   would deadlock: the condominium has no administrator yet, so nobody could
   give it.
2. *No default-tenant membership.* Signup adds a `DEFAULT_TENANT_ID` link; this
   flow must not, or the invited administrator would appear in a condominium
   nobody invited them to. A test asserts exactly one membership row.
3. *No role rows.* Since IAM F5 / APRAS-49, `is_acting_tenant_admin`
   (`app/api/deps.py:283`) already grants the whole catalogue inside the acting
   tenant, so a role row would be a second, divergent source of authority.

The account this branch mints is held to exactly the rules signup enforces,
by reusing them rather than restating them: `InvitationCreate.email` is an
`EmailStr`, and `InvitationAcceptRequest.cpf` / `.password` call the same
`normalize_cpf` and `validate_password_strength` helpers that back
`UserCreate`'s field validators, guarded on `None` so the existing-account
branch that ignores the three fields still works. `InvitationService._create_user`
then *builds* a `UserCreate`, so the gate also covers values that never passed
through the body — the invited address comes from the stored row — and a
failure there is `InvitationInvalidAccountError` (422). The CPF normalisation to
11 digits is load-bearing and not cosmetic: a duplicate `cpf` in the
new-account branch is a `409` **matching signup's existing conflict** only
because both paths store the same 11 digits, so `529.982.247-25` and
`52998224725` are one person. The invitation is consumed (`accepted_at`,
`accepted_user_id`) in the same transaction as the write, and the row is read
with `SELECT ... FOR UPDATE` so two concurrent accepts serialise on Postgres
(a no-op on the SQLite test engine, which is single-writer anyway).

**D10 — one mail sender, used by both flows.** New `app/core/mail.py`:
`async def send_email(to, subject, html) -> bool`, plus
`password_reset_html(...)` and `invitation_html(...)`. It reads `RESEND_API_KEY`
with `os.getenv` at call time (as today, so tests need no settings surgery), and
with the key absent — or on **any** exception from Resend — it prints instead of
raising, exactly as today. `forgot_password` becomes a call to it and keeps its
two printed lines (`[AUTH] Password reset requested for user: …`,
`[AUTH] Reset URL: …`) byte-for-byte, so `tests/test_password_recovery.py`
passes **unedited**. The invitation prints `[INVITE] Invitation for <email> to
<tenant name>` and `[INVITE] Accept URL: <origin>/invite?token=<raw token>`.
The accept URL is built from `request.headers.get("origin") or
"http://localhost:5173"`, the existing convention; `/invite` is the page
APRAS-72 builds.

Every value either template interpolates is `html.escape`d, including inside
the `href`. `accept_url` derives from the caller's `Origin` header and
`password_reset_html`'s `full_name` is self-service-settable at signup and
rendered by the *unauthenticated* `/auth/forgot-password`, so both are
attacker-influenced in the general case — and the message they land in is the
one that asks its reader to click a link and set a password, where a forged
body is costliest.

**D11 — tests assert a send without sending.** The suite runs with
`RESEND_API_KEY` unset, so the print branch is the tested one: `capsys` captures
the accept URL, and the raw token is parsed out of it — which is also how the
round-trip tests obtain a token without any route ever returning one.
`httpx.AsyncClient.post` is monkeypatched to fail the test if called, proving no
HTTP request is made. One further test sets `RESEND_API_KEY` via `monkeypatch`
and asserts the sender posts to `https://api.resend.com/emails` with the
expected `Authorization` header, against a patched `post`.

**D12 — migration numbering.** New revision `0003_tenant_invitation` (20
characters, within Alembic's 32-char `alembic_version.version_num` limit),
`down_revision = "0002_tenant_slug"`, importing **nothing** from `app/` and
never editing `0001`. APRAS-68's approved spec proposes `0003_tenant_brand_color`
on the same parent: whichever lands second renumbers at merge time to `0004_…`
and re-points its `down_revision`; if APRAS-68 is already on `master` when this
is implemented, this revision is `0004_tenant_invitation` with
`down_revision = "0003_tenant_brand_color"`. `EXPECTED_HISTORY` in
`tests/test_migrations_postgres.py` records whichever line is real.

## Approach

### Behavior

- A superuser posts `{tenant_id, email, full_name?}` and gets `201` plus a mail
  (or a printed link) containing a single-use accept URL; a non-superuser gets
  `403` and an anonymous caller `401`, both from `get_current_superuser`.
- An unknown `tenant_id` is `404`.
- Preview returns the invited email, the tenant name and slug, the inviter's
  full name, `expires_at` and `account_exists`; the three failure cases are
  D7's `404` / `410` / `409`.
- Accept creates or links per D8/D9 and consumes the invitation: the
  new-account branch returns `201` with a `Token` the caller can use
  immediately; the existing-account branch returns `200` with the preview shape
  and **no credential of any kind** (D8). Replaying the token is `409` and
  writes nothing.

### Files touched

- `backend/alembic/versions/0003_tenant_invitation.py` *(new)* — `create_table` /
  `drop_table` per D1 and D12, no `app` import.
- `backend/app/models/tenant_invitation.py` *(new)* — the `TenantInvitation`
  SQLModel matching the revision column for column.
- `backend/app/models/__init__.py` — export it, so
  `SQLModel.metadata.create_all()` builds it for the SQLite test harness.
- `backend/app/core/config.py` — `INVITATION_EXPIRE_HOURS`.
- `backend/app/core/mail.py` *(new)* — D10's sender and the two templates.
- `backend/app/core/exceptions.py` — `InvitationNotFoundError`,
  `InvitationExpiredError`, `InvitationAlreadyUsedError`.
- `backend/app/core/exception_handlers.py` — map them to `404`, `410`, `409`;
  `410` is a new branch in the existing status chain.
- `backend/app/core/permissions.py` — the four routes added to
  `UNGUARDED_ROUTES`, each with the one-line reason the neighbouring entries
  carry.
- `backend/app/services/invitation_service.py` *(new)* — issue, supersede (D4),
  resolve-by-token, accept; owns the hashing and the transaction.
- `backend/app/schemas/invitation.py` *(new)* — `InvitationCreate`,
  `InvitationRead`, `InvitationPreviewRequest`, `InvitationPreview`,
  `InvitationAcceptRequest`.
- `backend/app/api/v1/endpoints/invitations.py` *(new)* — the four routes.
- `backend/app/api/v1/api.py` — include the router at `/invitations`,
  `GLOBAL_SCOPED`, tag `invitations`.
- `backend/app/api/v1/endpoints/auth.py` — `forgot_password`'s inline block
  replaced by the `app.core.mail` call; the now-unused `httpx`/`os` imports
  dropped if nothing else in the module uses them.
- `backend/tests/test_invitations.py` *(new)* — the API and service tests below.
- `backend/tests/test_mail.py` *(new)* — the sender's two branches.
- `backend/tests/test_migrations_postgres.py` — `EXPECTED_HISTORY` gains the new
  revision; the "imports nothing from `app`" case loops over **every** revision
  module instead of only `HEAD_REVISION` (still one case, so the count is
  unchanged by it); three new cases per the test criteria.
- `backend/tests/test_tenant_models.py` — `UNSCOPED_TABLES` gains
  `"tenant_invitation"`, and the three literals in
  `test_partition_of_metadata_is_exhaustive` become `4 → 5` and `60 → 61`.
- `backend/tests/test_migrations_postgres.py`'s
  `test_inherited_tables_have_no_tenant_id` — its exact-set assertion becomes
  `scoped == set(TENANT_SCOPED_TABLES) | {"user_tenant_link",
  "tenant_invitation"}`, with the reason in the docstring: like
  `user_tenant_link`, this table's `tenant_id` names a tenant from **outside**
  it (issued by a superuser on a route with no acting tenant, consumed by an
  anonymous caller), so it is a reference and not a request-scoping key. It is
  therefore **not** added to `TENANT_SCOPED_TABLES` or `TENANT_SCOPED_MODELS`,
  and the migration's `_TENANT_SCOPED_TABLES` literal in `0001` is untouched.
- **`UNGUARDED_ROUTES` count: `24 → 28`, in SIX assertions across FOUR files** —
  `backend/tests/test_permission_registry.py:161`, `:211` and `:212` (the third
  spelled `len(ROUTE_PERMISSIONS) == total - 24`, so the literal `24` there
  becomes `28` too), `backend/tests/test_tenant_modules_api.py:405`,
  `backend/tests/test_permission_parity_matrix.py:655`, and
  `backend/tests/test_superuser_grant.py:294`. `len(ROUTE_PERMISSIONS) == 208`
  (`test_permission_registry.py:213`, `test_tenant_modules_api.py:401`,
  `test_superuser_grant.py:295`) is **unchanged** — this task adds no catalogue
  permission.
- **`GLOBAL_ROUTES` count: `28 → 32`, in THREE assertions across THREE files** —
  `backend/tests/test_tenant_route_scope.py:142` (which also gains the four new
  routes in the `GLOBAL_ROUTES` allowlist itself, each with its reason),
  `backend/tests/test_tenant_modules_api.py:406`, and
  `backend/tests/test_superuser_grant.py:327`.
- `backend/tests/test_permission_registry.py:43` — `FULLY_UNGUARDED_TAGS` gains
  `"invitations"`. Without it,
  `test_every_router_module_has_at_least_one_permission` (`:220-229`) fails: the
  new tag has zero `ROUTE_PERMISSIONS` entries, so it appears in `silent`, and
  that test compares `silent` to `sorted(FULLY_UNGUARDED_TAGS)` as an exact set.
  The tag qualifies under the same rule as `plans` (superuser-only or public
  routes only), and the loop at `:228` then also requires all four routes to be
  in `UNGUARDED_ROUTES`, which they are.
- `backend/scripts/assert_no_skips.py` — `MIN_CASES` re-pinned to the count the
  module really collects (`uv run pytest tests/test_migrations_postgres.py
  --collect-only -q`), with the raising comment the file's convention requires.
  It is `26` today; do not guess the new value, measure it.

### Test criteria

`tests/test_invitations.py`:

1. superuser issuance returns `201`, writes one row whose `token_hash` is
   64 hex characters, and the response body contains neither a token nor
   `token_hash`; a tenant admin and a plain user get `403`, anonymous `401`;
   an unknown `tenant_id` is `404`;
2. re-issuing for the same `(tenant, email)` leaves the earlier row with
   `expires_at <= db_now()` and the earlier token then previews `410` (D4);
3. preview with the token parsed from the printed accept URL returns `200` with
   the email, tenant name, tenant slug, inviter name and `account_exists=False`;
4. preview and accept return `404` for a random token, `410` for a row written
   with a past `expires_at`, `409` for one already accepted — and no failure
   body contains the invited email;
5. accept creates the user with `is_active=True`, **exactly one**
   `UserTenantLink` with `is_tenant_admin=True` on the invited tenant, and
   **zero** `user_role_link` rows; the returned `access_token` authenticates a
   `GET /api/v1/auth/me`; the invitation has `accepted_at` set and
   `accepted_user_id` equal to the new user;
6. accepting twice: the second call is `409`, `select(User)` count is unchanged,
   and the membership row count is unchanged;
7. an expired token creates no account (user count unchanged);
8. accept for an email that already has a user returns `200`, creates no second
   user, leaves `hashed_password` byte-identical, and sets `is_tenant_admin` on
   the invited tenant while leaving the user's other memberships untouched;
   the response JSON contains **no** `access_token`, `refresh_token` or `token`
   key and the response carries no `Set-Cookie` header (D8);
9. a duplicate `cpf` in the new-account branch is `409` and consumes nothing
   (`accepted_at` stays NULL);
10. the superuser list returns the tenant's invitations, newest first, and `403`
    for a non-superuser.

`tests/test_mail.py`: with `RESEND_API_KEY` unset, `send_email` prints and
returns without an HTTP call (`httpx.AsyncClient.post` patched to fail the
test); with it set, it posts to `https://api.resend.com/emails` with the bearer
header; a raising `post` is swallowed and falls back to printing.
`tests/test_password_recovery.py` passes with **no edit**.

`tests/test_migrations_postgres.py`, against the throwaway Postgres on 55432 per
AGENTS.md (`initdb -E UTF8`, never the dev database), three new cases:
`tenant_invitation` exists at head with `token_hash` uniquely indexed,
`expires_at` NOT NULL and `accepted_at` nullable; the table is **absent** after
`downgrade` to `0002_tenant_slug`; and the live table has **no** column named
`token` (the mechanical guard against reintroducing raw-credential storage).
The existing upgrade → downgrade-to-base → upgrade case must still pass.

Gates: `uv run pytest` green at the 90% coverage gate, `ruff check .` and
`ruff format --check .` clean, `NOQA_CAP` in `tests/test_lint_hygiene.py` not
raised, and `tests/test_assert_no_skips.py` passing on equality with the
re-pinned `MIN_CASES`.

## Out of Scope

Revoking an invitation, resend-from-UI, invitation expiry sweeps, inviting
non-administrator members, and any frontend file.
