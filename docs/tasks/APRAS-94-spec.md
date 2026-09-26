# APRAS-94 — Store uploads in Vercel Blob so they survive a serverless deploy

## The defect, and the evidence

Uploading a condominium logo in production fails. The browser reports a CORS
error; that is a symptom and not the cause. Probed from outside the browser,
CORS is healthy: `GET /api/v1/health`, the `OPTIONS` preflight for
`PUT /api/v1/tenant-profile/logo` and the *unauthenticated* `PUT` (401) all
answer with `Access-Control-Allow-Origin: https://apras.vercel.app`. The
failing authenticated `PUT` carries no such header.

Facts checked against this tree (all confirmed):

- `backend/app/services/storage_service.py:79` — `LocalStorageProvider.save_file`
  calls `target_dir.mkdir(parents=True, exist_ok=True)` and then `open(..., "wb")`
  under `static/uploads/{year}/{month}/`.
- `backend/vercel.json` routes `/(.*)` to `index.py`: the backend is one Vercel
  serverless function, whose filesystem is read-only outside `/tmp`. So the
  `mkdir` raises `OSError(30, "Read-only file system")`.
- `VercelBlobStorageProvider`, `S3StorageProvider` and `CloudinaryStorageProvider`
  (`storage_service.py:116-149`) are stubs raising `NotImplementedError`.
- Five modules bind `LocalStorageProvider()` themselves: `tenant_service.py:89`,
  `finance_service.py:50`, `purchase_service.py:71`,
  `announcement_service.py:47` and `media_service.py:32`.

One correction to the reading of the CORS symptom, established by experiment
rather than inference: **no platform-level crash is required to lose the
header.** Starlette mounts `ServerErrorMiddleware` *outside* the user
middleware stack, so an unhandled exception inside a route bypasses
`CORSMiddleware` entirely. A minimal FastAPI app with the same CORS
configuration and a route raising `OSError` returns `500` with
`content-type: text/plain` and no `access-control-allow-origin` at all —
byte-for-byte the observed symptom. The missing header is therefore a
*reliable signature of an unhandled exception*, and the fix must guarantee
that no storage failure is ever unhandled (§6 below).

Also confirmed, and relevant: `backend/app/main.py` already tolerates the
read-only filesystem at import time — the `mkdir` for both static trees is
wrapped in `try/except OSError` and the two mounts are skipped. So the
function boots; only the write path dies.

## Scope

Make every write that currently goes to `static/uploads` and `static/generated`
work on Vercel by routing it through a configured storage provider, with Vercel
Blob implemented against its REST API using `httpx`, and with
`LocalStorageProvider` remaining the behaviour whenever no Blob token is
configured.

In scope:

1. One configuration-driven decision point for the upload tree and one for the
   generated tree, replacing the five hard-coded `LocalStorageProvider()`
   bindings.
2. A working `VercelBlobStorageProvider` (save + delete) over the Blob REST API.
3. Preserving APRAS-65 (the client filename never decides the stored suffix)
   and closing the `HardenedStaticFiles` gap for Blob-served objects (§3).
4. Tenant-namespaced object paths.
5. `static/generated` (obras report, assembly minutes) — **in scope**, see §5.
6. A clear, mapped error for every storage failure; no `NotImplementedError`
   and no unhandled exception reaching the client.

Out of scope:

- S3 and Cloudinary. Their stubs stay unimplemented, but must stop raising
  `NotImplementedError` in favour of the same mapped error (§6).
- Any backfill or rewriting of URLs already stored in the database (§4).
- Frontend changes. `TenantProfilePage.tsx:239` and `BrandedEntryPage.tsx:195`
  render `src={logo_url}` verbatim, so an absolute Blob URL works with no
  change; a relative `/static/uploads/...` value never worked in production
  anyway, because it resolves against the *frontend* origin.
- Serving Blob objects through the backend, or private/signed Blob access. The
  current `/static/uploads` mount is unauthenticated, so public Blob URLs are
  not a confidentiality regression.
- Migrating `voting_service.save_minutes`' or `project_report_service.save_report`'s
  rendering, folder logic or document records. Their only changes are the
  provider they obtain and the new `tenant_id` keyword they pass (§4).

## Approach

### 1. The provider seam (config key and decision point)

Behaviour: exactly two functions in
`backend/app/services/storage_service.py` decide which provider is used, and
nothing else instantiates a provider.

- Add `BLOB_READ_WRITE_TOKEN: str | None = None` to `Settings` in
  `backend/app/core/config.py`. The name is Vercel's own: linking a Blob store
  to the project injects that environment variable, so production needs no
  extra configuration step, and `pydantic-settings` picks it up with no parsing.
- Add `upload_storage_provider()` beside the existing
  `generated_storage_provider()`. Each returns `VercelBlobStorageProvider`
  configured for its own path namespace when `settings.BLOB_READ_WRITE_TOKEN`
  is set, and otherwise the `LocalStorageProvider` it returns today, with the
  same `base_dir`/`url_prefix` pair. No token configured ⇒ byte-for-byte
  today's behaviour, which is what keeps local development and the whole test
  suite unchanged.
- The five modules keep their module-level `_storage_provider` /
  `self.storage_provider` attribute names — every test double substitutes those
  names — but bind them from `upload_storage_provider()` instead of
  `LocalStorageProvider()`.
- `media_service.upload_photo` currently hard-codes
  `storage_provider=StorageProvider.LOCAL_DISK` on the `MediaAsset` row
  (`media_service.py:133`). Providers expose a `provider_kind: StorageProvider`
  attribute (`LOCAL_DISK` / `VERCEL_BLOB`) and the row records the provider that
  actually stored the bytes.

### 2. APRAS-65 survives

`LocalStorageProvider.save_file`'s docstring is the rule and it carries over
unchanged to the Blob path: `filename` is display metadata and nothing else,
and the stored suffix comes from the already-validated `content_type` via
`app.core.uploads.canonical_extension`. The Blob object name is
`{uuid4}{canonical_extension(content_type)}`; no part of the client's name
reaches the stored pathname. The `filename` argument stays in the signature
(services still persist a sanitised copy as display metadata) and stays unused
by the Blob provider for the same reason it is unused by the local one.

### 3. The `HardenedStaticFiles` protection, per MIME type

`backend/app/main.py`'s `HardenedStaticFiles` adds
`X-Content-Type-Options: nosniff` to every response and, on the uploads mount,
forces `application/octet-stream` + `Content-Disposition: attachment` for
anything outside `INLINE_SAFE_EXTENSIONS` (`.jpg .jpeg .png .webp .pdf`).
**Blob objects are served by Vercel's CDN on
`<store>.public.blob.vercel-storage.com` and never pass through that class.**

Every content type any caller can reach `save_file` with, and what each does
from a Blob URL:

| `content_type` | callers | today on the hardened mount | from a Blob URL | verdict |
| --- | --- | --- | --- | --- |
| `image/jpeg`, `image/png`, `image/webp` | media, tenant logo, announcement, infraction evidence | inline (inline-safe) | inline, same declared type | equivalent — nothing lost |
| `application/pdf` | finance invoice, quote attachment, announcement | inline (inline-safe) | inline in the browser's PDF viewer, which is not the APRAS origin | equivalent |
| `text/html` | **generated tree only** (minutes, obras report) | uploads mount forces download; generated mount renders inline *by design* | inline, executing on the blob host | not equivalent → constrained, see below |
| anything unmapped | none today; a future allowlist entry | `.bin`, forced to `application/octet-stream` + attachment | would be served with whatever type we sent, e.g. `image/svg+xml` executing on the blob host | not equivalent → refused, see below |

Decision — constrain what can be stored, so the mount's protection is not
needed for Blob objects:

- The Blob provider sends `x-content-type` derived from
  `app.core.uploads`' own map, never the raw string the client sent: add a
  `canonical_content_type(content_type) -> str | None` helper there that
  normalises (lower-case, parameters dropped, reusing the existing
  `_normalise`) and returns the value only if it is a key of
  `CONTENT_TYPE_EXTENSIONS`.
- A content type that helper rejects is **refused with an error** (§6) rather
  than stored as `.bin`. The local provider's inert-`.bin` fallback exists
  because a mount it does not control guesses from the extension; on Blob there
  is no such fallback available, so an unmapped type must not be storable at
  all. This is stricter than today and cannot regress any current caller: every
  service allowlist is a subset of `CONTENT_TYPE_EXTENSIONS`, which
  `tests/test_upload_filename_safety.py` already enforces.
- The refusal lives in the **provider**, not in the services. Consequence,
  recorded deliberately: with no token an unmapped type still lands as an inert
  `.bin` locally, while with a token it is refused with a 4xx — dev and
  production disagree on that input's acceptability. It is accepted because the
  divergence is unreachable from any endpoint: every service allowlist is a
  subset of `CONTENT_TYPE_EXTENSIONS` (verified by
  `tests/test_upload_filename_safety.py`), so no request can carry an unmapped
  type to `save_file` in either environment. Duplicating the check in the five
  services would restate five allowlists to close a gap only a future,
  deliberately widened allowlist could open — and that future change is exactly
  when the provider's refusal should be the thing that stops it.
- `text/html` is accepted **only** by the provider instance
  `generated_storage_provider()` returns, and refused by the one
  `upload_storage_provider()` returns. That reproduces, on Blob, exactly the
  split the two mounts express today, and keeps "what can land next to
  inline-rendered HTML" answerable by reading one function's callers.

Residual risks, recorded rather than implied:

- **Generated HTML executes on the blob host.** That host is a third-party
  origin: it shares no cookie, no `localStorage` and no session with
  `apras-back.vercel.app` or `apras.vercel.app`, so script there cannot reach
  an APRAS session. Its bytes are server-rendered by APRAS and no client
  supplies them. The residual exposure is confined to other objects of the same
  Blob store, whose URLs are public and unguessable either way.
- **`nosniff` on Blob responses cannot be established from this repository.**
  Whether Vercel's CDN sends `X-Content-Type-Options` is a property of their
  service. With the type set closed to the five entries above, the worst case is
  HTML bytes declared `image/png` (the tenant-logo and quote-attachment paths
  validate size and MIME but not bytes — only `media_service` runs them through
  Pillow), which current browsers render according to the declared type and do
  not sniff on a top-level navigation. Accepted as residual; a post-deploy
  `curl -I` on one stored object, recorded in the PR, is the cheap confirmation.

### 4. Tenant namespacing, and the URLs already in the database

Namespacing: `BaseStorageProvider.save_file` gains a keyword-only
`tenant_id: UUID | None = None`. `LocalStorageProvider` ignores it, so the
`{year}/{month}/` layout and every existing assertion about it are untouched.
The Blob provider builds the pathname
`{namespace}/{tenant_id or "shared"}/{year}/{month}/{uuid}{ext}`, where
`namespace` is `uploads` or `generated`. **All seven call sites pass
`app.core.tenant_context.acting_tenant_id(session)` — the five upload services
and both generated writers (`project_report_service.py:700-701`,
`voting_service.py:1159-1160`), each of which already has a `Session` in
scope**; generated objects are therefore attributed to the acting tenant
exactly as uploaded ones are, and `shared` appears in a pathname only when
`acting_tenant_id` returns `None`. The acting tenant is a session-level fact
and there is no `ContextVar` to read it from, which is why this is an argument and not
ambient state. The value is operational (offboarding, attribution, debugging)
and is *not* a security boundary — Blob public URLs are unguessable and
namespacing does not make them less readable.

Deletion, and APRAS-61: `tenant_service._delete_previous_logo` and
`purchase_service`'s equivalent reconstruct a local path by stripping the
`/static/uploads/` prefix and deliberately leave any other URL alone. That
predicate would silently skip every Blob URL, orphaning objects. Replace it
with a provider method — `resolve_stored_path(url) -> str | None` on
`BaseStorageProvider`: the local implementation reproduces today's
prefix-plus-`base_dir` logic (and today's `None` for a foreign or
hand-written URL, `getattr(_storage_provider, "base_dir", None)` included) but
keys off **`self.url_prefix`, never the module-level `/static/uploads`
literal**, so the generated-tree instance resolves its own URLs too — the two
helpers being consolidated (`tenant_service.py:743-761`,
`purchase_service.py:921-938`) are byte-identical, so nothing is lost. The
Blob implementation returns the URL when its host is a
`*.blob.vercel-storage.com` host and `None` otherwise; consequently the Blob
`delete_file` **short-circuits to `False` with no HTTP call** when handed a
value `resolve_stored_path` rejects, which is what keeps a filesystem path
written before the token was configured from being POSTed to the delete
endpoint as a URL. APRAS-61's rule — "an externally hosted or hand-written URL
is left alone" — is preserved by construction.

Existing rows: **whether any production row holds a `/static/uploads/...`
value cannot be determined from this repository.** The columns that could are
`tenants.logo_url`, `financial_transactions.invoice_file_path` /
`invoice_file_url`, `purchase_quotes.attachment_url`,
`announcement_media.file_path`/`url`, `media_assets.file_path`/`url`/
`thumbnail_url`, `infractions.evidence_urls_json` /
`attachment_urls_json`, and `association_documents.file_url`. What settles it
is a read-only query against the Neon production database, e.g.
`SELECT count(*) FROM tenants WHERE logo_url LIKE '/static/uploads/%'` and the
equivalent per column. Two facts make a backfill very unlikely to be needed and
put it out of scope regardless: writes have been failing in production since the
serverless deploy, so few or no such rows can exist; and any that do point at a
file that no longer exists (an ephemeral function filesystem) *and* at a path the
frontend resolves against its own origin, so it has never rendered. After this
task, such a row shows a broken image exactly as it does now — no new breakage.

### 5. `static/generated` — in scope

Confirmed broken in production for the same reason, on two endpoints:
`project_report_service.save_report` (`POST /api/v1/projects/report/save`) and
`voting_service.save_minutes` both call `generated_storage_provider()`, whose
`LocalStorageProvider.save_file` performs the same `mkdir` under
`static/generated`. Both therefore return the same unhandled-500-without-CORS.

It is in scope because it is the *same seam*: `generated_storage_provider()`
already exists as the single decision point for that tree and is reached by
every generator, so the change is the same one-line factory decision plus one
namespace, and the `text/html` constraint of §3 is the only additional thought
required. Leaving it out would knowingly ship a release that fixes one half of
a single bug.

### 6. Failure behaviour

No path may raise `NotImplementedError` and none may let an exception escape to
`ServerErrorMiddleware`, because §"The defect" shows that is exactly what
produces the bodiless, header-less 500 the browser mislabels as CORS.

- Add `StorageUnavailableError(DomainError)` in `backend/app/core/exceptions.py`
  and map it to `503 SERVICE_UNAVAILABLE` in
  `backend/app/core/exception_handlers.py`, so the response is JSON, has a
  message, and — because it leaves the route normally — carries the CORS header.
- Raise it when: the Blob token is absent or malformed at the point of use (the
  message names `BLOB_READ_WRITE_TOKEN`); the Blob API answers non-2xx or the
  request fails; **the Blob API answers 2xx with a body that does not parse as
  JSON, or parses without a non-empty string `url`**; and from the
  `S3`/`Cloudinary` stubs, replacing their `NotImplementedError`.
- That 2xx-with-an-unexpected-body rule is not defensive padding: it is the one
  drift signature the version pin cannot make loud. A rejected `x-api-version`
  comes back non-2xx and is already mapped; a *response shape* change on a 2xx
  would otherwise raise `JSONDecodeError`/`KeyError` out of `save_file`, escape
  to `ServerErrorMiddleware`, and reproduce byte-for-byte the bodiless,
  header-less 500 this whole task exists to eliminate. No `json()` result may be
  subscripted before it has been validated.
- Every `StorageUnavailableError` raised from a Blob HTTP failure carries the
  Blob API's own `error.code` and `error.message` (the documented error body
  shape) in its message when the body supplies them, and the response status
  always. Without that, "a 4xx naming the API version is the signal to bump the
  constant" is a guess rather than an observable production signal.
- Refused content types (§3) raise a validation-shaped error, not
  `StorageUnavailableError`: reuse `app.core.exceptions`' existing
  invalid-format vocabulary or add one `DomainError` mapped to `422`.
- `LocalStorageProvider.save_file` translates `OSError` into
  `StorageUnavailableError` whose message says storage is not configured for a
  read-only filesystem. This is the belt to the braces: even with no token
  configured, a Vercel deploy answers with a diagnosable body instead of a
  crash.
- `delete_file` keeps its best-effort contract on both providers: it returns
  `bool` and never raises, so a failed cleanup cannot fail the request.

### The Vercel Blob REST contract (no new dependency)

`httpx` is already a dependency (`backend/pyproject.toml:21`) and the REST API
suffices, so **no package is added**. The contract below was read out of
`@vercel/blob` 2.6.1's own compiled client in
`/Users/heitor/workspace/repertoire_hero/node_modules/@vercel/blob/dist`
(`getApiUrl`, `requestApi`, `createPutHeaders`, `del`), which is what
`repertoire_hero`'s `src/app/actions/bands.ts` and `tabs.ts` call through
`put(filePath, buffer, { access: 'public', contentType: file.type })`:

- Save: `PUT https://vercel.com/api/blob/?pathname=<url-encoded pathname>`,
  raw bytes as the body, headers `authorization: Bearer <token>`,
  `x-api-version: 12`, `x-vercel-blob-store-id: <store id>`,
  `x-vercel-blob-access: public`, `x-content-type: <canonical type>`,
  `x-add-random-suffix: 0` (the object name is already a UUID). The response is
  JSON containing `url`, `downloadUrl`, `pathname`, `contentType`.
- Delete: `POST https://vercel.com/api/blob/delete` with
  `content-type: application/json` and body `{"urls": [<url>]}`.
- Store id: the fourth `_`-separated field of a
  `vercel_blob_rw_<storeId>_<random>` token — `token.split("_")[3]` is exactly
  what the SDK's `parseStoreIdFromReadWriteToken` does. A token that does not
  yield one raises `StorageUnavailableError`.
- The API version and the base URL are single module constants, commented with
  their provenance (`@vercel/blob` 2.6.1, `BLOB_API_VERSION = 12`); a 4xx
  naming the API version is the signal to bump the constant.
- `x-allow-overwrite` is **deliberately not sent**, even though `put` allows
  the option: object names are freshly minted UUIDs, so an overwrite cannot
  occur and a collision must stay an error rather than silently replace a
  stored object. The omission is a decision, not an oversight.
- Use the **synchronous** `httpx.Client` with an explicit, bounded timeout
  (connect and read both set; no unbounded default), because every `save_file`
  caller is a synchronous service function.

**The blocking call, decided explicitly.** All five upload routes are
`async def` (they `await UploadFile.read()`), so a synchronous `httpx` PUT
inside `save_file` occupies the event loop for the duration of the upload.
This is accepted, not overlooked, for three reasons. First, it is not a new
class of behaviour on these routes: they already call synchronous SQLAlchemy
`Session` work inline, which blocks the same loop on every query. Second,
offloading cannot be done inside `save_file`: a synchronous function running on
the loop thread cannot await `run_in_threadpool`, so honouring S5 by offloading
would mean making `save_file` (and the five service functions above it, and
their routes) `async` — a signature ripple across the whole upload stack, far
beyond this task's one deliverable. Third, the exposure is small and bounded:
on Vercel each function invocation serves one request, so there is nothing to
stall, and the bounded `httpx` timeout caps the worst case for a single local
uvicorn worker. The cheap upgrade, if local latency ever matters, is to wrap
the *route*'s service call in `starlette.concurrency.run_in_threadpool`, which
needs no provider change; it is recorded as a known limitation rather than
done here.

`save_file` returns `(internal_path, public_url)` as it does today; the Blob
provider returns the blob URL for both, which is what makes `delete_file` work
uniformly for callers that stored `file_path` (finance, announcement, media).

### Known limitations (named, not fixed here)

- **Vercel's 4.5 MB request-body limit is below the limits this codebase
  enforces.** `MAX_MEDIA_FILE_SIZE` and `MAX_INVOICE_FILE_SIZE` are both 10 MiB
  (`announcement_service.py:39`, `finance_service.py:47`), so a 6 MB invoice
  still fails in production after this task — at the platform edge, before the
  function runs, most likely as another header-less error an operator will again
  read as "CORS". This task does not widen to fix it: the cure is a different
  shape of feature, a client-direct upload where the backend mints a signed
  client token and the browser PUTs to Blob without traversing the function.
  Recorded so this fix is not mistaken for a complete one for large files.
- **The synchronous Blob call blocks the event loop** for the duration of an
  upload; see the decision above. Closing it means `run_in_threadpool` at the
  route boundary.

### Files touched

- `backend/app/core/config.py` — add `BLOB_READ_WRITE_TOKEN`.
- `backend/app/core/uploads.py` — add `canonical_content_type`; document that it
  is the Blob path's gate.
- `backend/app/services/storage_service.py` — `upload_storage_provider()`;
  implemented `VercelBlobStorageProvider`; `resolve_stored_path` and
  `provider_kind` on the base and both providers; `tenant_id` keyword on
  `save_file`; `OSError` translation in `LocalStorageProvider`;
  `generated_storage_provider()` becomes configuration-driven; `S3`/`Cloudinary`
  stubs raise the mapped error.
- `backend/app/core/exceptions.py`, `backend/app/core/exception_handlers.py` —
  `StorageUnavailableError` and its 503 mapping.
- `backend/app/services/tenant_service.py`, `finance_service.py`,
  `purchase_service.py`, `announcement_service.py`, `media_service.py` — obtain
  the provider from the factory; pass `tenant_id`; delete through
  `resolve_stored_path`; `media_service` records the real `provider_kind`.
- `backend/app/services/project_report_service.py`,
  `backend/app/services/voting_service.py` — one change each and no other: pass
  `tenant_id=acting_tenant_id(session)` on their existing
  `generated_storage_provider().save_file(...)` call. Rendering, folder logic
  and document records are untouched.
- `backend/tests/` — new `tests/test_storage_blob.py`; and exactly **three**
  files define a hand-written `save_file` double that must accept the new
  keyword: `tests/matrix_world.py:222`, `tests/test_tenant_profile.py:992`,
  `tests/test_voting_minutes.py:39`. `test_finance.py`,
  `test_purchase_quote_attachment.py`, `test_announcements.py` and
  `test_project_report.py` inject a **real** `LocalStorageProvider` (or
  monkeypatch the factory to return one), which absorbs a keyword-only
  `tenant_id` on the base class with no edit — they must stay untouched.
- `backend/.env.example` (if present) and `docs/` deployment notes — record
  `BLOB_READ_WRITE_TOKEN`.

### Test criteria

All Blob tests patch `httpx.Client.request` (or `.send`) in the manner
`tests/test_mail.py` already patches `httpx.AsyncClient.post`. **No test may
reach the live Blob API**, and a test proving the token-absent path must assert
no HTTP call is attempted at all.

- With no `BLOB_READ_WRITE_TOKEN`, both factories return `LocalStorageProvider`
  with today's `base_dir`/`url_prefix` pairs, and the existing suite passes
  unmodified apart from the double-signature updates listed above.
- With a fake token, `upload_storage_provider()` returns the Blob provider; a
  captured fake request asserts method, URL, every header above, the body bytes,
  and a pathname of the documented shape with a UUID stem and the canonical
  extension.
- The client filename never appears in the captured pathname, including for a
  hostile name such as `../../evil.svg` posted as `image/png` (APRAS-65).
- The upload-namespace provider refuses `text/html` and refuses an unmapped type
  such as `image/svg+xml`, raising before any HTTP call; the generated-namespace
  provider accepts `text/html`.
- A non-2xx Blob response, an `httpx` transport error, **a 200 whose body is
  not JSON, and a 200 whose body is `{}`** each raise `StorageUnavailableError`
  — never `JSONDecodeError` or `KeyError`; an absent/malformed token raises it
  with a message naming `BLOB_READ_WRITE_TOKEN`. A non-2xx carrying
  `{"error": {"code": ..., "message": ...}}` produces an exception message
  containing both.
- Both generated writers store under the acting tenant's id segment, asserted
  from the captured pathname, and `shared` appears only when the session has no
  acting tenant.
- The Blob `delete_file` makes no HTTP call when handed a non-blob value such as
  `static/uploads/2026/09/x.png`, and returns `False`.
- `PUT /api/v1/tenant-profile/logo` with a storage failure returns `503` with a
  JSON body and, with an allowed `Origin`, the
  `access-control-allow-origin` header — the regression test for the misleading
  CORS symptom.
- `delete_file` returns `False` rather than raising on a failed Blob delete;
  `resolve_stored_path` returns the URL for a blob host and `None` for
  `https://cdn.example.com/x.png` (APRAS-61's leave-it-alone rule).
- `media_assets.storage_provider` is `VERCEL_BLOB` when the Blob provider stored
  the bytes and `LOCAL_DISK` otherwise.
- Coverage and lint gates for the backend stay green.

## Expected Results

- [ ] `backend/app/core/config.py`'s `Settings` declares
      `BLOB_READ_WRITE_TOKEN: str | None = None`.
- [ ] `backend/app/services/storage_service.py` exposes `upload_storage_provider()`
      and `generated_storage_provider()`, and these are the only places a storage
      provider class is instantiated:
      `grep -rn "LocalStorageProvider(" backend/app` returns **no matches outside**
      `backend/app/services/storage_service.py`.
- [ ] With `BLOB_READ_WRITE_TOKEN` unset, `upload_storage_provider()` returns a
      `LocalStorageProvider` with `base_dir == Path("static/uploads")` and
      `url_prefix == "/static/uploads"`, and `generated_storage_provider()` one
      with `static/generated` and `/static/generated`.
- [ ] With `BLOB_READ_WRITE_TOKEN` set, both factories return a
      `VercelBlobStorageProvider`.
- [ ] `VercelBlobStorageProvider.save_file` issues one `PUT` to
      `https://vercel.com/api/blob/?pathname=...` with headers
      `authorization: Bearer <token>`, `x-api-version: 12`,
      `x-vercel-blob-store-id` equal to the fourth `_`-separated field of the
      token, `x-vercel-blob-access: public`, `x-add-random-suffix: 0` and
      `x-content-type` equal to the canonical content type, carrying the raw
      bytes as the body, and returns the `url` from the JSON response. No
      `x-allow-overwrite` header is sent.
- [ ] `VercelBlobStorageProvider.delete_file` issues one `POST` to
      `https://vercel.com/api/blob/delete` with body `{"urls": [<url>]}`,
      returns `True` on success and `False` (never raising) on any failure; when
      handed a value that is not one of its own blob URLs (for example
      `static/uploads/2026/09/x.png`) it returns `False` **without making any
      HTTP request**.
- [ ] No new runtime dependency is added: `backend/pyproject.toml`'s
      `dependencies` list is unchanged, and the Blob provider uses `httpx`.
- [ ] Every new test double patches `httpx`; no test in `backend/tests` performs
      a real request to `vercel.com` or `blob.vercel-storage.com`, and the
      token-absent test asserts that no HTTP request is attempted.
- [ ] For a session whose acting tenant id is a known UUID, the pathname the Blob
      provider sends — for an upload write **and** for a generated write — matches
      `^(uploads|generated)/<T>/\d{4}/\d{2}/<U>\.(jpg|png|webp|pdf|html)$`, where
      `<T>` is that exact tenant id string and `<U>` is
      `[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}`. The literal
      segment `shared` appears in place of `<T>` **only** in a test where the
      session has no acting tenant.
- [ ] Given a client filename of `../../evil.svg` and content type `image/png`,
      the stored pathname contains no part of that filename and ends in `.png`.
- [ ] The provider returned by `upload_storage_provider()` raises a mapped
      domain error, before any HTTP request, for content type `text/html` and
      for `image/svg+xml`; the provider returned by
      `generated_storage_provider()` accepts `text/html`.
- [ ] Each of these raises `StorageUnavailableError` and never
      `JSONDecodeError`, `KeyError` or `NotImplementedError`: a non-2xx Blob
      response; **a non-2xx response whose body is not JSON at all**, such as an
      edge 502 or 504 HTML page; an `httpx` transport error; **a fake response
      with status `200` and body `{}`**; **a fake response with status `200` and
      a body that is not valid JSON**; **a fake response with status `200` and
      body `{"url": ""}`**; a missing token; a malformed token. The missing-token message
      contains the string `BLOB_READ_WRITE_TOKEN`, and the message for a non-2xx
      whose body is `{"error": {"code": "bad_request", "message": "..."}}`
      contains both that `code` and that `message`. Also
      `grep -rn "NotImplementedError" backend/app/services/storage_service.py`
      returns nothing.
- [ ] `StorageUnavailableError` is mapped to HTTP `503` by
      `backend/app/core/exception_handlers.py`.
- [ ] A test drives `PUT /api/v1/tenant-profile/logo` with a failing storage
      backend and asserts the response is `503`, has a JSON body, and — with an
      allowed `Origin` request header — carries
      `access-control-allow-origin`.
- [ ] A test drives `PUT /api/v1/tenant-profile/logo` with a Blob token
      configured and a fake successful Blob response, and asserts the response
      body's `logo_url` is an absolute URL beginning `https://` on a
      `blob.vercel-storage.com` host — not a relative `/static/uploads/...` path.
- [ ] `LocalStorageProvider.save_file` raises `StorageUnavailableError` (not a
      bare `OSError`) when the target directory cannot be created, proven by a
      test that makes `mkdir` fail.
- [ ] `BaseStorageProvider.resolve_stored_path` returns a path/URL for a URL the
      provider itself minted — for the local provider derived from that
      instance's own `url_prefix`, so the `static/generated` instance resolves
      `/static/generated/...` values — and `None` for
      `https://cdn.example.com/logo.png`; `tenant_service` and
      `purchase_service` delete previous files through it instead of a hard-coded
      `/static/uploads/` prefix check.
- [ ] `media_assets.storage_provider` is written as `VERCEL_BLOB` when the Blob
      provider stored the bytes, and `LOCAL_DISK` when the local one did.
- [ ] `project_report_service.save_report` and `voting_service.save_minutes`
      store through the configured provider, proven by a test in which a
      configured Blob token results in a `file_url` on a
      `blob.vercel-storage.com` host for both.
- [ ] `backend/tests/test_finance.py`,
      `backend/tests/test_purchase_quote_attachment.py`,
      `backend/tests/test_announcements.py` and
      `backend/tests/test_project_report.py` are unchanged by this task. Determine
      that from this task's own commits — `git log --format='%H %s' | grep -E
      '^[0-9a-f]{40} [a-z]+\(APRAS-94\):' | cut -d' ' -f1 | xargs -n1 git show
      --pretty=format: --name-only | sort -u` — and not from a bare
      `git diff --stat`, which has no comparison base and passes vacuously once
      the work is committed, nor from `git merge-base HEAD origin/master`, which
      resolves many commits and files away from this task's branch point.
- [ ] `cd backend && uv run pytest` passes, and `uv run ruff check .` reports no
      findings.

## Out of Scope

- S3 and Cloudinary implementations.
- Backfilling or rewriting `/static/uploads/...` values already in the database.
- Frontend changes; private or signed Blob access; proxying Blob objects through
  the backend.
- Changing what the two `HardenedStaticFiles` mounts do for files served from
  disk in local development.
