# APRAS-105 — Upload to the private Blob store and serve the logo through a public route

## Scope

Two halves that must ship in one PR, because either alone leaves the product
broken:

1. **Uploads succeed against a Blob store configured with private access.**
   The production 400 is already diagnosed and must not be re-derived:
   `VercelBlobStorageProvider.save_file` sends `x-vercel-blob-access: public`
   and the store answers `{"error":{"code":"bad_request","message":"Cannot use
   public access on a private store. The store is configured with private
   access."}}`, which `storage_service` turns into the 503 the admin screen
   shows. Nothing is missing from the request; one header carries the wrong
   value.
2. **A public, unauthenticated route serves a tenant's logo bytes by slug**,
   reading the object out of the private store with the application's own
   credential. Every surface that displays a logo — the obras report and the
   two frontend screens — points at that route with an **absolute** URL, and
   the report stops embedding the image as a data URI.

**The operator's decision, recorded because it constrains the design.** They
chose to keep the store private and make the *route* public, rather than
switch the store to public access. With a public store the exposed thing is a
permanent Vercel Blob URL outside the application: it cannot be rate-limited,
measured or revoked without deleting the object. With a public route the
exposed thing is an endpoint we own, and every other object in the store —
assembly minutes, generated reports, the documents still to land there — stays
unreachable without our token. The logo ends up publicly readable either way,
since `/c/<slug>/obras` is already open on the internet by an earlier decision
(APRAS-92 D1) and the logo on that page is no more private than the page
carrying it. What the decision buys is ownership of the public door.

Out of scope: switching the store's access mode; the three headers the official
client sends and we do not (`x-content-length`, `x-api-blob-request-id`,
`x-api-blob-request-attempt`) — APRAS-101 ruled all three out as the cause of
the 400, and none may be added here (see Recommendations); caching, `ETag`
or signed URLs on the new route; the cover-photo upload
(APRAS-104, which follows this task's shape); any change to what is stored in
`tenant.logo_url`.

## Approach

### A. The access value (`backend/app/services/storage_service.py`)

`save_file` sends the access value as a literal `"public"` inline in its
headers dict. Replace it with a **module-level named constant**, e.g.
`BLOB_STORE_ACCESS = "private"`, documented with the production error it fixes,
and reference that constant from `save_file`.

Argued against the alternatives:

- **Not configuration.** A setting would introduce a value that can be wrong in
  production with no signal until an upload fails — which is precisely the
  failure being fixed — and it cannot vary per environment anyway: without
  `BLOB_READ_WRITE_TOKEN` (local development, CI, the test suite) no Blob
  provider is built at all and every write goes to `LocalStorageProvider`. One
  store, one access mode, one value.
- **Not derived.** The store's access mode is not discoverable from the token
  or from any cheap request; deriving it would mean an extra round trip per
  upload to learn a constant of the deployment.
- **Not omitted.** The header is part of the write contract; dropping it trades
  a known-good value for an undocumented default.

A test must pin the value that reaches the wire, asserting the request's
`x-vercel-blob-access` header equals `private` — written so that restoring
`public`, the value which produced the production 400, fails it. This is the
guard against somebody quietly reverting it in six months.

`resolve_own_url` already accepts both `public` and `private` as the host's
access label and needs no change; leave it accepting both, because the store's
mode is deployment configuration and a one-value predicate would break on the
day it changes.

### B. Reading an object out of a private store

`read_file(url, *, max_bytes=...)` exists from APRAS-96 and is the mechanism,
but `_read_object` deliberately sends **no** `authorization` header, on the
stated grounds that "everything this provider writes is `public`-access and
needs no credential to be read". That premise is now false: an object in a
private store is not readable anonymously. The read must carry the store's own
credential.

This is safe for exactly the reason `resolve_own_url` was written the way it
was: the credential is only ever attached to a URL whose host has passed all
four clauses (five labels, first equal to *this* deployment's store id, second
an access label, last three exactly the Blob suffix), so it cannot be sent to a
host somebody else named. Update that docstring and the `_read_object` comment
so the premise stated in the code is the one that holds. Three further places
state the old premise or the old caller and must be swept in the same pass, so
the module does not contradict itself:

- the module docstring at `storage_service.py:28–37`, which asserts the store
  is **"write-only"** and that the read **"carries no credential"** — both
  become false here;
- `storage_service.py:148`, which names `TenantService.logo_data_uri` as
  `read_file`'s one caller, a method §E replaces;
- the `read_file` base-class docstring's surrounding claims about the read
  being anonymous, wherever they recur. Keep every other
property of `read_file` intact: never raises, one warning per failure shape,
bounded body, `follow_redirects=False` — and if a redirect is what the API
answers for a private object, handle it without ever forwarding the credential
to the redirect target.

The developer verifies the exact private-read mechanism against Vercel's Blob
REST documentation. The behavioural requirement is what this spec pins: the
bytes of an object in a private store come back, the request carries our
credential, and the credential never appears in anything we return.

### C. The public route

Path: **`GET /api/v1/public/tenants/{slug}/logo`**. Chosen for consistency with
the two unauthenticated surfaces already mounted under the same prefix —
`/api/v1/public/tenants/{slug}/branding` and
`/api/v1/public/tenants/{slug}/projects/report`. Same shape (`/public`, tenant
named by slug in the path, subject of the read), so a reviewer reads the route
table and sees at once that it authenticates nobody.

Lives in `app/api/v1/endpoints/public_branding.py`: it is branding, keyed by
the same slug, and already mounted `GLOBAL_SCOPED` under `/public` for exactly
the reason this route needs — the caller sends no `Authorization` and no
`X-Tenant-Id`. It maps to no catalogue permission and therefore joins
`UNGUARDED_ROUTES` in `app/core/permissions.py`, with the same comment shape
the neighbouring public entries carry. It adds no parity-baseline row.

Behaviour:

- 200 with the stored bytes and a `Content-Type` derived from the stored
  object's suffix, restricted to `TenantService.LOGO_ALLOWED_MIME_TYPES` —
  the same derivation `logo_data_uri` performs today.
- **404**, indistinguishably and deliberately, for: unknown slug; inactive
  tenant (matching the report route, so an inactive condominium is not
  published); no `logo_url`; a suffix outside the allowed image types; and any
  read that comes back empty or refused. No 5xx on a storage failure — the
  route answers 404 and the storage layer logs the reason.
- **No `Cache-Control` and no `ETag`**, consistent with APRAS-92 D3 and for the
  same reason stated there: a browser-held copy cannot be invalidated, and a
  logo replaced on the admin screen must not stay stale at a slug-stable URL.
  The gain this task is after is that the bytes leave the HTML document, not
  that they are cached. See Recommendations.
- **Rate-limited: `@limiter.limit("30/minute")`**, the same limit the sibling
  route in this module already carries (`public_branding.py:54`), applied with
  the same shape — `from app.core.limiter import limiter` and the `request:
  Request` parameter slowapi requires by name. **This is the operator's
  decision**, taken on the amplification question this route raises and
  recorded here so it is not re-litigated. The reason it is needed, in the
  words the code already uses: `project_report_service._logo_html`'s docstring
  warns that "on a public, unlimited, uncached route (D3) a per-request fetch
  to an arbitrary host would be both an amplification vector and an SSRF
  surface". `resolve_own_url` answers the SSRF half; nothing answered the
  amplification half, and this route is public, unauthenticated, explicitly
  uncached, and performs an outbound Blob GET buffering up to 2 MiB inside a
  serverless invocation on **every** hit.

  **This does not reverse APRAS-92 D3.** D3 decided not to rate-limit the
  *obras report* route, and that decision stands untouched. This is a
  different route with a different cost profile: a report hit runs a local
  render, while a logo hit runs outbound network I/O and buffers the response,
  so an unlimited logo route turns one cheap inbound request into one
  outbound fetch we pay for. Same prefix, different economics — nobody should
  later read this line as a silent change of mind about D3.
- **Bounded.** The read passes `max_bytes=TenantService.LOGO_MAX_FILE_SIZE`
  (2 MiB, the configured upload ceiling) explicitly; it does not rely on
  `BLOB_MAX_READ_BYTES`'s default. An object above the bound is not streamed
  and the route answers 404.
- The response body and headers carry no credential, no store token and no
  upstream Blob URL.

The byte-reading logic belongs in `TenantService` beside `LOGO_MAX_FILE_SIZE`
and `LOGO_ALLOWED_MIME_TYPES`, which already own every logo rule:
`logo_data_uri` is **replaced** by a method that returns the bytes and their
content type (or `None`), bounded by the ceiling, with the base64 step deleted.
The route is a thin handler over it.

### D. Absolute URLs, on every surface

The report is served by `apras-back.vercel.app`; the page the visitor opens is
`apras.vercel.app`, and `PublicObrasReportPage` injects the document into an
`<iframe srcDoc>`, whose relative URLs resolve against the *parent* document's
base — i.e. the frontend. A relative `src` therefore fails silently. The same
defect exists today on `TenantProfilePage`, which renders `logo_url` verbatim,
so a relative stored URL never displays. Both surfaces must be cured.

Backend: add a small helper (new `app/core/urls.py`) that builds the absolute
public logo URL from a base resolved in this order — an explicit
`PUBLIC_API_BASE_URL` setting in `app/core/config.py`; else
`https://{VERCEL_PROJECT_PRODUCTION_URL}`; else `https://{VERCEL_URL}`; else
`http://localhost:8000`.

**All three rungs are `Settings` fields, not `os.environ` reads.** `Settings`
is a pydantic `BaseSettings` with `case_sensitive=True`, so declaring
`VERCEL_PROJECT_PRODUCTION_URL: str = ""` and `VERCEL_URL: str = ""` makes
pydantic read the variables Vercel injects, under those exact names, with no
extra code — and keeps every rung overridable in a test by the same mechanism
the rest of the suite already uses to override settings. Neither field exists
in `config.py` today; this task adds all three there, alongside
`PUBLIC_API_BASE_URL`. `app/core/urls.py` reads `settings` only and imports
`os` nowhere.

The Vercel fallbacks mean production is correct with
no new environment variable to forget, and the explicit setting is the override
when the backend is served from a domain of our own. Trailing slashes are
normalised so the joined URL never doubles a slash. Each rung gets a test.

Frontend: a `tenantLogoUrl(slug)` helper built off `apiClient.defaults.baseURL`
— the same technique `publicReportUrl` already uses, so the frontend does not
grow a second definition of where the API lives. `TenantProfilePage` and
`BrandedEntryPage` both display through it (`BrandedEntryPage` has the same
verbatim-`logo_url` defect and the fix is the same one line). `logo_url`
remains untouched in both API payloads: it is storage truth and the
`has a logo` flag; it is no longer a display source.

### E. The embedding is removed

`project_report_service._logo_html` currently tries `TenantService.logo_data_uri`
first and falls back to linking. Delete that rung. The masthead emits
`<img src="{absolute public logo route for tenant.slug}">` when the tenant has
a `logo_url`, and no `<img>` at all when it does not — today's no-logo masthead,
unchanged. APRAS-93 measured the cost this removes: a 105 KiB logo becomes
~140 KiB of base64 and about **89%** of a single-project report's bytes, on
every render of a route with no cache. The now-false "No outbound request is
made." comment at line 675 of `project_report_service.py` goes with the rung
that made it false, and the report performs no storage read at all: the read
moves behind the route, where the browser makes it once and caches it on its
own terms.

**Accepted trade-off: archived reports point at the route.** Rung 1's stated
purpose was self-containment — "a report printed or filed in the Document
Center carries its own logo instead of depending on a URL staying reachable" —
and `save_report` really does persist the rendered HTML as an
`AssociationDocument`. Deleting the rung costs that property, and the operator
was asked and **chose to have archived reports point at the route**. The
consequences, named rather than left to be discovered: a logo later replaced
silently changes the logo inside reports already filed; a logo removed leaves
a broken image in them; and if the deployment's base URL ever changes, an
archived file stops resolving its own masthead. This is accepted because the
archive stores **HTML, not a PDF** — it was never a frozen artefact — and it
already links project photos by URL in exactly this way, so the logo is not
introducing a dependency the document did not already have. No migration or
rewrite of existing archived reports is part of this task.

**This task subsumes APRAS-99.** APRAS-99 exists to pass `max_bytes` from
`TenantService.logo_data_uri` and to correct that comment; here the method is
replaced by a bounded one and the comment's line is deleted. APRAS-99 should be
closed as subsumed rather than worked — there must not be two tasks for one
line.

### Files touched

- `backend/app/services/storage_service.py` — access value becomes a named
  constant set to `private`; the read attaches the store credential to an
  own-store URL; the docstrings that assert the old premise are corrected
  (module docstring lines 28–37, the stale caller name at line 148, and
  `_read_object`'s comment at line 638).
- `backend/app/services/tenant_service.py` — `logo_data_uri` replaced by a
  bounded bytes-plus-content-type reader passing `max_bytes=LOGO_MAX_FILE_SIZE`.
- `backend/app/api/v1/endpoints/public_branding.py` — new unauthenticated,
  `30/minute` rate-limited `GET /tenants/{slug}/logo`.
- `backend/app/core/permissions.py` — the new route joins `UNGUARDED_ROUTES`.
- `backend/app/core/config.py` — `PUBLIC_API_BASE_URL`,
  `VERCEL_PROJECT_PRODUCTION_URL` and `VERCEL_URL` settings fields.
- `backend/app/core/urls.py` (new) — absolute public-URL builder and its base
  resolution.
- `backend/app/services/project_report_service.py` — masthead links the route;
  data-URI rung and the false comment removed.
- `frontend/src/api/publicBranding.ts` — `tenantLogoUrl(slug)`.
- `frontend/src/features/user-administration/pages/TenantProfilePage.tsx` —
  displays through the helper.
- `frontend/src/features/user-administration/pages/BrandedEntryPage.tsx` —
  same.
- Tests: `backend/tests/` (storage access value and private read, the new
  route's 200/404/bound/credential cases, the report's markup and size,
  `test_tenant_profile.py`'s `UNGUARDED_ROUTES` assertions, the URL builder),
  `frontend/src/**/__tests__/` (the two screens and the helper).
- `docs/tasks/APRAS-105-spec.md` (this file).

### Test criteria

- A `save_file` test intercepting the outbound request asserts
  `x-vercel-blob-access == "private"`; substituting `"public"` fails it.
- A read test asserts the outbound GET to an own-store URL carries the store
  credential and returns the object's bytes against an intercepted store that
  refuses anonymous reads; that a URL `resolve_own_url` rejects produces no
  request at all; and that a redirect target never receives the credential.
- A structural test asserts the logo route is decorated
  `@limiter.limit("30/minute")` — not a 31-request test, which the suite-wide
  `app.state.limiter.enabled = False` (`tests/conftest.py:24`) would render
  vacuous.
- Route tests: 200 with the right `Content-Type` and body; 404 for unknown
  slug, inactive tenant, absent logo, disallowed suffix and unreadable object;
  an oversized object is refused rather than streamed; the response body and
  headers contain no credential.
- Report tests: the rendered document contains the absolute route URL, contains
  no `data:image`, and a report for a tenant with a logo and one for a tenant
  without differ by under 2 KiB.
- URL-builder tests cover each fallback rung and the trailing-slash
  normalisation.
- Frontend tests: both screens render an `src` starting with the API base and
  ending in the logo path; the no-logo case renders no `<img>`.
- The whole existing backend and frontend suites pass.

### Allowed paths

```
backend/app/api/v1/endpoints/public_branding.py
backend/app/core/config.py
backend/app/core/permissions.py
backend/app/core/urls.py
backend/app/services/project_report_service.py
backend/app/services/storage_service.py
backend/app/services/tenant_service.py
backend/tests/**
frontend/src/api/publicBranding.ts
frontend/src/features/user-administration/pages/BrandedEntryPage.tsx
frontend/src/features/user-administration/pages/TenantProfilePage.tsx
frontend/src/features/user-administration/__tests__/**
frontend/src/api/__tests__/**
docs/tasks/APRAS-105-spec.md
```

Nothing else. In particular: do not touch `docs/suggestions-log.md`,
`docs/tasks/APRAS-82-mock.html`, `docs/tasks/APRAS-91-spec.md` or
`docs/tasks/APRAS-93-spec.md`, which carry another task's uncommitted work.

## Expected Results

- [ ] Uploading a tenant logo succeeds against a Blob store whose access mode
      is private, proven against a **test double** — an intercepted/faked Blob
      HTTP layer, never the production store, which must not be touched: the
      upload call answers 2xx and `logo_url` points at an object in that store.
      The real gate is the next sentence. A test pins the outbound
      `x-vercel-blob-access` value such that the value meaning public — the one
      that produced the production 400 — fails the test.
- [ ] `GET /api/v1/public/tenants/{slug}/logo` serves the tenant's logo bytes
      with no authentication, with a `Content-Type` matching the stored image,
      and answers 404 when the tenant is unknown, inactive, or has no logo.
- [ ] Reading an object that lives in a private-access store returns its bytes:
      against an intercepted Blob layer that refuses an anonymous GET and
      serves the body only when the store credential is present, the read
      returns the object's exact bytes rather than `None`.
- [ ] The store credential is sent **only** to a URL that `resolve_own_url`
      accepts. Tests prove all three: (a) a read of an own-store URL carries
      the credential on the outbound request; (b) a URL `resolve_own_url`
      rejects — a foreign host, a different store id, a wrong label count —
      produces **no outbound request at all**, not a credential-free one; and
      (c) when the Blob API answers a redirect, the redirect target receives no
      request carrying the credential.
- [ ] The route reads the object from the private store using the
      application's own credential, and a test proves the credential appears in
      neither the response body nor the response headers.
- [ ] The public logo route carries a `30/minute` rate limit: a test asserts
      the limit **structurally** — that the route handler is wrapped by
      `@limiter.limit("30/minute")`, e.g. by inspecting the decorated
      function's slowapi marker — because `backend/tests/conftest.py:24` sets
      `app.state.limiter.enabled = False` for the whole suite, so a test that
      fires 31 requests and expects a 429 would pass while asserting nothing.
- [ ] The route answers 404 for an object larger than the 2 MiB configured logo limit
      instead of streaming it unbounded; a test drives an oversized object and
      asserts the refusal.
- [ ] The obras report references the logo with an `<img>` whose `src` is the
      absolute URL of that public route: a test asserts the rendered HTML
      contains the absolute backend URL and contains no `data:image`.
- [ ] The rendered obras report for a tenant that has a logo and the one for a
      tenant that has none differ by less than 2 KiB.
- [ ] The tenant-profile admin screen and the branded entry screen display the
      logo through that same absolute route URL, so the image loads when
      frontend and backend are served from different hosts.
- [ ] A tenant with no logo renders the report and both screens without error
      and with no broken image element.
- [ ] The whole existing backend and frontend test suites pass.

## Out of Scope

- Switching the Blob store to public access.
- Adding `x-content-length`, `x-api-blob-request-id` or
  `x-api-blob-request-attempt` to the upload.
- `Cache-Control`, `ETag` or signed URLs on the new route. (Rate limiting is
  **in** scope by operator decision — see §C.)
- The obra cover photo (APRAS-104).

## Recommendations (not part of this change)

- The three headers ruled out by APRAS-101 may still be worth sending for
  parity with the official client's diagnostics. If so, that is its own task.
- A short `max-age` plus an `ETag` on the logo route would save a round trip
  per page view, at the cost of a replaced logo staying stale for the TTL. It
  needs an operator decision, like APRAS-92 D3 did.
- **APRAS-99 is subsumed by this task and should be closed, not worked.**
