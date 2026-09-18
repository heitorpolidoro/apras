# APRAS-65 — Sanitise the upload filename everywhere, and split generated output off the hardened mount

## Scope

Move the filename defence APRAS-63 built for the purchase-quote attachment into
the one place every upload passes through — `LocalStorageProvider.save_file` —
so the on-disk extension is derived from the already-validated `content_type`
at **every** call site; harden the unauthenticated `/static/uploads` mount for
files already on disk with an attacker-chosen extension; and, so that hardening
does not break the Document Center, move **server-generated** output (assembly
minutes, works reports) to its own `static/generated/` location served without
the restriction. Output generated **before** this change is deliberately not
migrated (D5); it stays on the hardened mount and downloads instead of
rendering inline until it is re-generated.

Covers: `storage_service` (suffix derivation plus a `url_prefix` pairing and a
generated-output factory), a shared sanitiser module, two static mounts, the two
generator call sites, removal of the local copy in `purchase_service`, the raw
`thumb_` prefix in `media_service`, and a per-call-site regression test for the
five vulnerable paths.

Does **not** cover: migrating or rewriting any existing document row (D5),
constraining the free-form `mime_type` / `file_url` fields of
`AssociationDocumentCreate` (a separate hardening task; the hardened mount
neutralises the planted-file case meanwhile), widening or narrowing any MIME
allowlist, accepting SVG,
authenticating either mount, the `VercelBlob`/`S3`/`Cloudinary` stubs (still
`NotImplementedError`), any Alembic revision, or any frontend change (there is
none — payload shapes are unchanged and no stored URL is rewritten).

## Approach

### Decisions this spec makes

**D1 — the fix lives in `save_file`, not in five services.** `save_file`
already receives `content_type` at every call site, so no signature changes and
no caller churn. The suffix is derived from `content_type` through a canonical
map; the `filename` argument stops influencing the on-disk name entirely and is
documented as display metadata only. An unmapped `content_type` yields `.bin`.
The map includes `text/html -> .html` for the two generator call sites.

**D2 — one shared sanitiser, and APRAS-63's local copy goes away.** The new
module owns `canonical_extension(content_type)` and
`sanitise_upload_filename(filename, content_type, *, max_length, fallback_stem)`
with exactly the behaviour APRAS-63 implemented (basename across POSIX and
Windows separators, drop non-printables, force the extension, truncate). The
body of `PurchaseService._sanitise_attachment_filename` is deleted and the call
site calls the shared function, passing the existing
`ATTACHMENT_FILENAME_MAX_LENGTH` / `ATTACHMENT_FALLBACK_STEM` so
purchase-visible behaviour is byte-identical. Only the two unit-level tests
that reach for the private classmethod are repointed at the shared function;
every HTTP-level assertion in `test_purchase_quote_attachment.py` stays as it
is and must still pass. `attachment_filename` is the only persisted display
name in the schema, so no other service needs a sanitised name.

**D3 — two mounts, one `StaticFiles` subclass, a flag between them.** A single
`HardenedStaticFiles(StaticFiles)` adds `X-Content-Type-Options: nosniff` to
every response and takes a `force_download: bool` constructor flag. With the
flag on, any extension outside the inline-safe set
(`.jpg`, `.jpeg`, `.png`, `.webp`, `.pdf`) is served as
`application/octet-stream` with `Content-Disposition: attachment`; with it off,
the guessed content type is served as-is. One subclass rather than two classes
or a narrowed rule: the two mounts differ in exactly one predicate, and the
nosniff header is correct for both.

**D4 — generated output gets its own directory, produced by the same provider
class with a different prefix.** `LocalStorageProvider.__init__` gains
`url_prefix: str = "/static/uploads"`, paired with `base_dir` and used to mint
the returned URL (today the prefix is a hardcoded f-string, which is why a
second `base_dir` alone would mint a wrong URL). `storage_service` then exposes
a factory `generated_storage_provider()` returning
`LocalStorageProvider(base_dir="static/generated", url_prefix="/static/generated")`,
and `voting_service.save_minutes` / `project_report_service` call it in place of
their inline `LocalStorageProvider()` default. Not a subclass and not a
`save_file` parameter: the two locations differ only in configuration already
expressed by the constructor, `delete_file` and the year/month/uuid layout are
identical, and both services keep their injected `storage_provider` override, so
the fakes in `tests/matrix_world.py` and `tests/test_voting_minutes.py` are
untouched. The default argument values keep every other caller byte-identical.

**D5 — nothing is migrated; pre-existing rows stay on the hardened mount, and
we say so.** The obvious move — select `mime_type == "text/html"` rows and
relocate their files to `static/generated/` — is **unsafe and is rejected**.
Every column such a selector could read is client-writable by the very role the
threat model is about: `AssociationDocumentCreate.mime_type` and
`AssociationDocumentVersionCreate.mime_type`
(`backend/app/schemas/document.py:46,57`) are free-form strings with no
allowlist, `file_url` beside them is a free-form string (`min_length=1`, no
prefix check), and `document_service.create_document` / `create_document_version`
persist both verbatim (`document_service.py:377,425`) behind
`_check_admin_or_director` — the same director who can upload. `folder_id`,
`title` and `uploaded_by_id` are no better: a director can post into the
minutes or obras folder under any title. There is therefore **no** database
signal that separates a generated report from a row a director forged, so any
automatic mover would take an attacker-planted file out from under the hardened
mount and place it on the one mount that serves HTML inline — re-opening this
task's own vulnerability. On-disk extension is no signal either: an
attacker-chosen `.html` suffix is precisely the bug D1 fixes.

So this task moves **no** file and rewrites **no** `file_url`. There is no
migration script. The consequence, stated plainly: **assembly minutes and works
reports generated before this change keep their `/static/uploads/…` URL and,
from this change on, download as `application/octet-stream` with
`Content-Disposition: attachment` instead of rendering in the browser tab that
`DocumentCenterPage` opens.** Nothing is lost or 404s — the row, the file and
the download all still work; only inline rendering stops. The remedy is
re-generation, which both features already support: `save_report` can be run
again at any time, and `save_minutes` re-files an assembly's minutes. Both then
write to `static/generated/` and render inline as before. No Alembic revision
and no data migration of any kind is added.

**D6 — nothing else writes generated output.** The `save_file` callers are
`tenant_service` (logo), `media_service` (photo and thumbnail),
`announcement_service` (media), `finance_service` (invoice),
`purchase_service` (quote attachment) — all user-supplied — plus
`voting_service:1168` and `project_report_service:716`. `document_service`
stores a `file_url` it is given and never writes a file. The delete helpers in
`tenant_service` and `purchase_service` map only a `/static/uploads/` URL back
to a path and are correct unchanged; no code deletes generated output today.

### Files touched

- `backend/app/core/uploads.py` *(new)* — canonical `content_type -> extension`
  map, `canonical_extension`, `sanitise_upload_filename`, inline-safe set.
- `backend/app/services/storage_service.py` — `save_file` derives the suffix
  from `content_type`; `__init__` gains `url_prefix`; `generated_storage_provider()`.
- `backend/app/main.py` — `HardenedStaticFiles`; mount
  `/static/uploads` → `HardenedStaticFiles(directory="static/uploads", force_download=True)`,
  name `uploads`, and `/static/generated` →
  `HardenedStaticFiles(directory="static/generated", force_download=False)`,
  name `generated`. Both directories are created in the same `try/except OSError`
  block, and **both** mounts are skipped together on a read-only filesystem.
- `backend/app/services/voting_service.py`, `project_report_service.py` — the
  default provider becomes `generated_storage_provider()`.
- `backend/app/services/purchase_service.py` — local sanitiser removed, call
  site delegates to the shared function.
- `backend/app/services/media_service.py` — the `thumb_{filename}` prefix drops.
- `backend/app/services/tenant_service.py`, `announcement_service.py`,
  `finance_service.py` — **unchanged**; fixed by D1 alone.
- `.gitignore` — add `static/generated/` and `backend/static/generated/`.
- `backend/tests/test_upload_filename_safety.py` *(new)* — sanitiser unit tests
  and both mounts' HTTP behaviour.
- `backend/tests/test_tenant_profile.py`, `test_uploads.py`,
  `test_announcements.py`, `test_finance.py` — one regression test each.
- `backend/tests/test_purchase_quote_attachment.py` — two unit-level tests
  repointed at the shared function.
- `backend/tests/test_project_report.py` — the `storage` fixture monkeypatches
  `report.generated_storage_provider` instead of `report.LocalStorageProvider`,
  and URL assertions expect `/static/generated/`.
- `backend/tests/test_main_readonly_fs.py` — asserts both mount names.

### Test criteria

Per call site, upload valid bytes of an allowed type under a hostile name
(`payload.svg`, and `payload.html` for at least one) and assert the stored path
and returned URL end in the extension canonical for the declared type: tenant
logo, media photo **and** its thumbnail, announcement media (PNG), finance
invoice (PDF named `payload.svg`). Unit-test the sanitiser for basename
reduction, control-character stripping, extension forcing, truncation, empty
stem. Mount tests: a `.png` under `/static/uploads` is served `image/png`
inline with nosniff; a planted `.svg` there is `application/octet-stream` with
`Content-Disposition: attachment`; a `.html` under `/static/generated` is served
`text/html` with nosniff and **no** `Content-Disposition`. Generator tests: both
services return a `/static/generated/...` `.html` URL and write under
`static/generated`, and nothing lands in `static/uploads`. Legacy-row criterion
(D5): a planted `.html` under `static/uploads` — indistinguishable from a
pre-existing generated report — is served `application/octet-stream` with
`Content-Disposition: attachment`, and no code path moves a file between
`static/uploads` and `static/generated` or rewrites an existing
`AssociationDocument.file_url` — the generator call sites reach the generated
directory only through `generated_storage_provider()`, never by naming the path
themselves.

## Expected Results

- [ ] `LocalStorageProvider.save_file` derives the on-disk suffix from
      `content_type` only; no code path reads `Path(filename).suffix`, and the
      `save_file` signature is unchanged.
- [ ] A regression test per previously vulnerable call site (tenant logo, media
      photo, media thumbnail, announcement media, finance invoice) uploads
      valid bytes named `payload.svg` and asserts the stored file and returned
      URL end in the canonical extension for the declared type.
- [ ] `backend/app/core/uploads.py` exposes the shared sanitiser;
      `PurchaseService._sanitise_attachment_filename` no longer exists, the
      purchase call site uses the shared function, and every HTTP-level
      assertion in `tests/test_purchase_quote_attachment.py` still passes
      unchanged.
- [ ] `LocalStorageProvider` accepts a `url_prefix` paired with `base_dir`,
      defaulting to `/static/uploads` so every existing caller's URLs are
      unchanged, and `generated_storage_provider()` returns one rooted at
      `static/generated` with prefix `/static/generated`.
- [ ] Saving assembly minutes and saving a works report each write under
      `static/generated/YYYY/MM/` and return a `/static/generated/...html` URL,
      writing nothing under `static/uploads`, proven by a test per service.
- [ ] `backend/app/main.py` mounts `/static/uploads` with `force_download=True`
      and `/static/generated` with `force_download=False`; both are skipped
      together when the directories cannot be created, proven by
      `tests/test_main_readonly_fs.py`.
- [ ] Every response from both mounts carries `X-Content-Type-Options: nosniff`;
      a file under `/static/uploads` whose extension is outside
      `{.jpg,.jpeg,.png,.webp,.pdf}` is served `application/octet-stream` with
      `Content-Disposition: attachment` (proven with a planted `.svg`), while a
      `.html` under `/static/generated` is served `text/html` with no
      `Content-Disposition` (proven with a planted file).
- [ ] No data migration ships: no file in `backend/app` or `backend/scripts`
      moves a file between `static/uploads` and `static/generated` or assigns to
      an existing `AssociationDocument.file_url`, and the branch adds no script,
      task or startup hook that would; the only occurrences of the literal
      `static/generated` outside comments and docstrings are in
      `backend/app/main.py` (the mount) and
      `backend/app/services/storage_service.py` (the
      `generated_storage_provider` factory), the two generator call sites
      reaching that directory only through the factory.
- [ ] A document row whose `file_url` still points at `/static/uploads/…` and
      whose `mime_type` is `text/html` is left byte-identical by the whole test
      suite, and fetching that file returns `application/octet-stream` with
      `Content-Disposition: attachment` — proven by one test that plants the
      file, creates the row, exercises the mount and re-reads the row.
- [ ] Re-running works-report generation after this change creates a **new**
      document row with a `/static/generated/…html` `file_url`, leaving the
      older `/static/uploads/…` row untouched, proven by a test.
- [ ] No Alembic revision is added or edited and no schema change is made.
- [ ] `.gitignore` ignores `static/generated/` and `backend/static/generated/`.
- [ ] `cd backend && uv run pytest` passes with the 90% coverage gate, and
      `uv run ruff check . && uv run ruff format --check .` report zero
      findings.

## Out of Scope

Authenticating either mount; content-sniffing validation beyond the existing
Pillow/MIME checks; any change to the accepted MIME sets; deleting generated
output (no service does today); the Vercel Blob, S3 and Cloudinary stubs;
adding an allowlist to `AssociationDocumentCreate.mime_type` or a prefix check
to its `file_url`; migrating pre-existing generated reports and minutes.
