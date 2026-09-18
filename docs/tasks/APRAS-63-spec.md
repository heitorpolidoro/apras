# APRAS-63 — Purchase quotes screen: comparison, decision context, attachment

## Scope

Finishing the **"Cotações de Compra"** screen
(`frontend/src/features/purchase-management`) at the point where someone
actually decides. Three gaps, one deliverable:

1. **Comparison** — the quotes (*orçamentos*) of one request are read in a
   single table with supplier columns and aligned `extra_fields` labels,
   instead of stacked cards each carrying its own `<dl>`
   (`PurchaseRequestDetailModal.tsx:165`).
2. **Context at the decision** — the "Escolher Orçamento" modal
   (`SelectQuoteModal.tsx:77-87`) states what a non-lowest choice costs
   against the lowest quote, so the mandatory justification is written against
   the real gap.
3. **Attachment** — a quote can carry the supplier's document (one file),
   stored through the existing `LocalStorageProvider`, with two new columns on
   `purchase_quote` and two new routes.

**Not in scope**

- **No `MediaAsset` row, no thumbnail, no photo-moderation workflow.** A
  supplier document is a property of the quote, exactly as APRAS-61 treated the
  tenant logo.
- **No new permission string.** `PERMISSIONS` stays **175**.
- **No monetary type change.** `unit_price` stays `float` here; that is
  APRAS-64.
- **No new Alembic revision** (see *Migration rule*).
- No multi-file attachments, no attachment on `PurchaseRequest` itself, no
  change to the eleven existing purchase routes' contracts, no change to
  `MIN_JUSTIFICATION_LENGTH` or to the decision history rendering.
- No non-local storage provider (`VercelBlob`/`S3`/`Cloudinary` stay stubs).

## Migration rule (binding operator decision, 2026-09-17)

The two new `purchase_quote` columns are declared **inside**
`backend/alembic/versions/0001_initial_schema.py`, in that file's
`op.create_table('purchase_quote', …)` block (line ~850). The implementer
**edits 0001; it does not create 0002**, and `versions/` must still hold
exactly one revision module afterwards
(`tests/test_migrations_postgres.py::test_versions_holds_exactly_one_revision_module`).
Resetting local and CI databases is authorised and expected. **This task must
be merged to master before APRAS-59 pushes and applies 0001 in production** —
editing 0001 after it has been applied would leave `alembic_version` pointing
at a changed file, i.e. schema drift correctable only by a second production
reset.

## Decisions

**D1 — Two columns, not a table.** `purchase_quote` gains
`attachment_url: str | None` and `attachment_filename: str | None`, both
nullable with no server default. `attachment_url` is the public
`/static/uploads/<year>/<month>/<uuid><ext>` URL returned by
`LocalStorageProvider.save_file`; `attachment_filename` is the sanitised
original name, used as the link text so the reader sees
`orcamento-acme.pdf`, not a uuid. No separate `file_path` column: as in
APRAS-61, the on-disk path is derived from the URL and only when it starts with
`/static/uploads/`.

**D2 — Accepted types: `application/pdf`, `image/png`, `image/jpeg`.
Maximum size: 5 MiB** (`media_service.MAX_FILE_SIZE`, reused by import, not
re-typed). WebP is excluded — no supplier sends one — and SVG is excluded for
the same active-content reason as APRAS-61 D2. Validation order: size → declared
MIME → content sniff (PDF must start with `%PDF-`; an image must decode with
Pillow). A refusal writes **no** file and **no** column.

**D3 — A refused file is 422**, through two new `DomainError` subclasses
(`QuoteAttachmentTooLargeError`, `QuoteAttachmentInvalidFormatError`)
registered in the 422 branch of `app/core/exception_handlers.py` — the
APRAS-61 D5 precedent, and the reason `PhotoFileTooLargeError` (400) is not
reused.

**D4 — No new permission: both routes carry `purchases:quote_update`.**
Uploading a supplier's PDF is editing that quote. Enforcement stays exactly
where the sibling quote routes put it — inside `PurchaseService`
(`_assert_can_view` → `_assert_can_write_quote` → `_assert_quotes_unfrozen`) —
so a Manager may only touch quotes they may already edit.

**D5 — Frozen means frozen.** A request whose status is not `OPEN` answers the
existing `PurchaseQuoteFrozenError` (**409**) on both the upload and the
removal; the already-stored file stays readable forever, which is the whole
point of the accountability trail. A decision therefore never deletes a file.

**D6 — Deleting deletes the bytes.** `delete_quote` deletes the quote's stored
file before `session.delete`, and `delete_request` deletes every quote's file
before deleting the request. A replacement upload deletes the previous file.
All three are best-effort (`LocalStorageProvider.delete_file` already swallows)
and only touch paths derived from a `/static/uploads/` URL.

**D7 — The comparison table replaces the stacked cards** as the quote surface
of the detail modal; the per-quote actions (choose, edit, delete, attach) move
into an action cell at the foot of each supplier column. The element carrying
each supplier keeps `data-testid="quote-row-${quote.id}"` so the existing
`PurchaseRequestDetailModal.test.tsx` assertions keep meaning.

**D8 — The gap is computed client-side** from the quotes already in
`PurchaseRequestDetailRead`; `is_lowest_price` is already on every quote and
no endpoint changes. When two quotes tie at the lowest total, both carry
`is_lowest_price` and neither shows a warning.

## Approach

### Behavior — backend

Two routes on the existing purchases router, both acting on one quote of one
request:

| Route | Answers |
|---|---|
| `PUT /api/v1/purchase-requests/{request_id}/quotes/{quote_id}/attachment` (multipart `file`) | 200 `PurchaseQuoteRead` with the new `attachment_url`/`attachment_filename`; 403 without `purchases:quote_update` or on another Manager's quote; 404 unknown request/quote; 409 frozen; 422 type/size/undecodable |
| `DELETE …/attachment` | 200 `PurchaseQuoteRead` with both fields `null`, idempotent when already null; same 403/404/409 |

- `PurchaseQuoteRead` gains `attachment_url` and `attachment_filename`
  (both `str | None = None`); `PurchaseQuoteCreate`/`Update` do **not** — the
  file only ever arrives as multipart.
- Service logic lives on `PurchaseService` as `set_quote_attachment` /
  `clear_quote_attachment`, reusing `_get_request_or_404`,
  `_get_quote_or_404`, `_assert_can_write_quote`, `_assert_quotes_unfrozen`
  and `_build_quote_read`; the storage provider is a module-level
  `LocalStorageProvider()` instance so a test can monkeypatch its `base_dir`.

### Registry bookkeeping (check line by line)

- `app/core/permissions.py`: `ROUTE_PERMISSIONS` **206 → 208** (both mapped to
  `purchases:quote_update`, in the `§4.21 purchases` block);
  `UNGUARDED_ROUTES` stays **24**; `PERMISSIONS` stays **175**; total
  **230 → 232**.
- `tests/test_permission_registry.py`: the `206`/`230` literals move; the `24`
  and `175` literals do not.
- `tests/test_permission_alignment.py`: the two routes enforce in the same
  form as the sibling quote routes, so exactly one form literal grows by 2
  (expected `EXPECTED_IN_HANDLER_FORM` **137 → 139**); the implementer runs the
  test and moves whichever literal it names, and the other four stay put.
- `tests/test_permission_parity_matrix.py`: new `APRAS_63_ROUTES` (the two
  routes), folded into `ADDITIVE_ROUTES`, `APRAS_63_CELL_COUNT = 12` added to
  `EXPECTED_CELL_COUNT`, recorded into the **new additive**
  `tests/data/parity_matrix_baseline_63.json` via
  `uv run python -m tests.tools.record_parity_baseline`. The seven files
  already in `backend/tests/data/` stay **byte-identical**
  (`git status --porcelain backend/tests/data/` must list
  `parity_matrix_baseline_63.json` as its single, untracked entry).
- `AGENTS.md`: the machine-checked route counts
  (`tests/test_docs_agents_md.py`) and one paragraph under *Purchases*
  recording D2, D4, D5 and D6.

### Behavior — frontend

- **`QuoteComparisonTable.tsx` (new).** Supplier columns (source order),
  fixed rows — total, unit price × quantity, contact, notes, attachment —
  then one row per `extra_fields` label, the label set being the union across
  quotes in first-seen order. A label a supplier did not fill renders a literal
  `—` with a translated `title`, never an empty cell. The lowest total keeps the
  existing "Menor preço" badge, the chosen quote the "Escolhido" badge. A header
  control orders columns by total (ascending ⇄ descending ⇄ original order).
  Below `md` the table transposes: one block per supplier, labels in the left
  column.
- **`SelectQuoteModal.tsx`.** New `lowestQuote: PurchaseQuote | null` prop.
  When the quote being decided is not lowest, an amber panel above the
  justification names the lowest supplier, its total, the difference in BRL and
  the difference in percent of the lowest total (one decimal). When it is
  lowest, nothing is rendered and the flow is byte-for-byte the one that exists
  today.
- **Attachment control.** In the attachment row of each supplier column: a link
  (`attachment_filename`, opens in a new tab) when set; an upload button when
  `quotesEditable` and the caller may edit that quote; a replace and a remove
  action when both a file and edit rights exist. The client refuses a file
  before any request when its type is outside the set or it exceeds 5 MiB,
  showing a translated message. When the request is frozen, the link is still
  shown and no upload control is rendered.
- Constants exported from `src/api/purchases.ts`
  (`QUOTE_ATTACHMENT_MAX_FILE_SIZE_BYTES`, `QUOTE_ATTACHMENT_ALLOWED_MIME_TYPES`,
  `QUOTE_ATTACHMENT_ACCEPT`), pinned from the backend side by a test naming that
  file — the two-sided pin `src/api/tenantProfile.ts` established.
- `uploadQuoteAttachment` / `deleteQuoteAttachment` in `src/api/purchases.ts`,
  `useUploadQuoteAttachment` / `useDeleteQuoteAttachment` in
  `usePurchaseRequests.ts`, both invalidating through the existing
  `useInvalidator(requestId)`.

### Files touched

**Backend**
- `alembic/versions/0001_initial_schema.py` — two columns inside the existing
  `purchase_quote` `create_table`; no new revision.
- `app/models/purchase.py` — the two nullable fields on `PurchaseQuote`.
- `app/schemas/purchase.py` — the two read fields on `PurchaseQuoteRead`.
- `app/core/exceptions.py` — the two new errors.
- `app/core/exception_handlers.py` — both in the 422 branch.
- `app/services/purchase_service.py` — `set_quote_attachment`,
  `clear_quote_attachment`, the accepted-type constants, file deletion in
  `delete_quote` and `delete_request`.
- `app/api/v1/endpoints/purchases.py` — the two routes.
- `app/core/permissions.py` — two `ROUTE_PERMISSIONS` entries.
- `tests/test_purchase_quote_attachment.py` — new.
- `tests/test_permission_registry.py`, `test_permission_alignment.py`,
  `test_permission_parity_matrix.py` — the moved literals.
- `tests/data/parity_matrix_baseline_63.json` — new, recorded.
- `AGENTS.md` — counts and one paragraph.

**Frontend**
- `src/types/purchase.ts` — the two fields on `PurchaseQuote`.
- `src/api/purchases.ts` — two calls and the three exported constants.
- `src/features/purchase-management/hooks/usePurchaseRequests.ts` — two
  mutations.
- `src/features/purchase-management/components/QuoteComparisonTable.tsx` — new.
- `src/features/purchase-management/components/PurchaseRequestDetailModal.tsx`
  — the card list gives way to the table; passes `lowestQuote` to the decision
  modal.
- `src/features/purchase-management/components/SelectQuoteModal.tsx` — the gap
  panel.
- `src/i18n/locales/pt.json`, `en.json` — the new `purchases.comparison.*`,
  `purchases.decision.gap*` and `purchases.attachment.*` keys, key-identical.
- `src/features/purchase-management/__tests__/QuoteComparisonTable.test.tsx` —
  new; `PurchaseRequestDetailModal.test.tsx`, `SelectQuoteModal.test.tsx` —
  extended.

### Test criteria

`backend/tests/test_purchase_quote_attachment.py`, one real request each:

1. `PUT …/attachment` with a small valid PDF answers 200; `attachment_url`
   starts with `/static/uploads/`, `attachment_filename` is the sent name, and
   the file exists on disk.
2. A PNG and a JPEG are accepted the same way; `text/plain`, `image/svg+xml`,
   a 6 MiB body, a `application/pdf` body not starting with `%PDF-` and an
   undecodable `image/png` each answer **422** and leave both columns `null`.
3. A second upload replaces: the column holds a different URL and the previous
   file is gone from disk.
4. `DELETE …/attachment` answers 200 with both fields `null`, removes the file,
   and a second `DELETE` is still 200.
5. Deleting the quote deletes the file; deleting the whole request deletes the
   files of all its quotes.
6. On a `DECIDED` request both routes answer **409** and the stored file
   survives; `GET /{request_id}` still returns its `attachment_url`.
7. A caller without `purchases:quote_update` gets **403**; a Manager gets
   **403** on another user's quote and 200 on their own.
8. `GET /{request_id}` exposes `attachment_url`/`attachment_filename` on every
   quote.
9. The contract case naming `frontend/src/api/purchases.ts` asserts the same
   accepted set and the same 5 MiB cap.
10. `tests/test_migrations_postgres.py::test_every_column_name_and_nullability_matches_the_model`
    passes against real Postgres (`TEST_POSTGRES_URL`) with the edited 0001.

Frontend: the table renders one row per union label with `—` in the cells a
supplier left empty; ordering by total reorders the columns and restores the
source order on the third click; the lowest column carries the badge; the
decision modal shows the gap in BRL and percent naming the lowest supplier for
a non-lowest quote and renders no gap panel for the lowest one; selecting a
6 MiB or `text/plain` file shows the translated error and issues **no**
request; a successful upload calls `PUT …/attachment` with
`multipart/form-data` and re-renders the link; a caller without
`purchases:decide` sees the table but no choose control, and a frozen request
shows the link but no upload control. `vitest` must stay above the thresholds
declared in `frontend/vitest.config.ts` (lines 80, functions 78, branches 76,
statements 80).

## Expected Results

- [ ] The request detail compares quotes side by side in one table, suppliers
      as columns (rows on a phone), with unit price, quantity, total and every
      `extra_fields` label aligned on the same line across suppliers; a label a
      supplier did not fill renders an explicit `—`, never a blank.
- [ ] The lowest total stays marked in the comparison and the table can be
      ordered by total.
- [ ] Opening the decision modal on a quote that is not the lowest states the
      difference in reais and in percent against the lowest quote, naming that
      supplier; choosing the lowest shows no such panel and the flow is
      unchanged.
- [ ] `PUT /api/v1/purchase-requests/{request_id}/quotes/{quote_id}/attachment`
      accepts one `application/pdf`, `image/png` or `image/jpeg` file up to
      5 MiB, stores it through `LocalStorageProvider`, and returns the quote
      with `attachment_url` under `/static/uploads/` and the original
      `attachment_filename`; the file is linked in the comparison and in the
      detail.
- [ ] A refused file (wrong type, over 5 MiB, or contents that do not match the
      declared type) answers **422**, writes no file and leaves both columns
      `null`; the frontend refuses the same files before sending, with a
      pt/en translated message.
- [ ] Replacing an attachment deletes the previous file; deleting a quote, or
      the whole request, deletes the stored file(s); a request whose quotes are
      frozen answers **409** on upload and on removal while keeping the stored
      file readable.
- [ ] Permission behaviour is unchanged: `purchases:quote_update` guards both
      new routes with no new permission string (`PERMISSIONS` stays 175), a
      caller without `purchases:decide` sees the comparison but no choose-quote
      control, and a caller without `purchases:quote_update` sees no upload
      control.
- [ ] The two routes are in `ROUTE_PERMISSIONS` (**206 → 208**, total
      **230 → 232**, `UNGUARDED_ROUTES` still 24), their 12 parity cells live
      in the new additive `backend/tests/data/parity_matrix_baseline_63.json`
      while the seven existing files in `backend/tests/data/` stay
      byte-identical, and `test_permission_registry.py`,
      `test_permission_alignment.py` and `test_docs_agents_md.py` pass.
- [ ] The two columns are declared **inside**
      `backend/alembic/versions/0001_initial_schema.py` — no `0002` file,
      `versions/` still holds exactly one revision — and
      `test_migrations_postgres.py` passes against real Postgres.
- [ ] The recorded decision keeps showing its justification, its author and its
      date in the detail, unchanged by this work.
- [ ] `backend`: `uv run pytest` green with the 90% gate, `ruff check .` and
      `ruff format --check .` clean. `frontend`: `tsc -b`, `vitest` with its
      declared coverage thresholds (lines 80, functions 78, branches 76,
      statements 80, per `frontend/vitest.config.ts`) and `eslint` pass (eslint diff-scoped against the repo's pre-existing
      errors); `pt.json` and `en.json` stay key-identical.

## Out of Scope

A new Alembic revision; `MediaAsset`/moderation/thumbnails; more than one file
per quote; attachments on the request itself; any new permission string;
monetary typing (APRAS-64); non-local storage providers; changing the eleven
existing purchase endpoints' contracts.

![Mockup](APRAS-63-mock.html)
