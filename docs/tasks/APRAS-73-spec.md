# APRAS-73 — The purchase request enumerates the line items; each quote prices them

## Scope

The priced line stops belonging to the **quote** and starts belonging to the
**request**. Whoever opens the purchase enumerates the lines — `description`
+ `quantity` ("4 × câmeras") — and every quote fills in, per line, the
**offered model** (optional) and the **unit price**. The comparison becomes a
**grid**: rows are the request's lines, columns are the quotes, cells hold
model + unit price + line total. `unit_price` and `quantity` **leave**
`purchase_quote`; a quote's total is derived from its own priced lines. One
new Alembic revision creates both tables, folds every existing quote into a
single quote-owned line and drops the two columns. The request form gains the
line editor, the quote form fills the grid column, and the APRAS-63
comparison table and decision modal are adapted (D8/D9/D10), including one
deliberate change to an APRAS-63 contract: the `Menor preço` badge and the gap
baseline are now disputed among **complete** quotes only (D10).

**Not** in scope: per-line attachments or extra fields, per-line REST
endpoints (lines travel inside the request and quote payloads), units of
measure, line categories, drag-and-drop reordering, copying lines between
requests, automatic matching of a supplier's extra line onto a request line,
and any change to the purchase permissions, the request statuses or the
freeze rule.

## Decisions

**D1 — New table `purchase_request_item`, owned by the request.** Columns:
`id` UUID pk; `purchase_request_id` UUID FK `purchase_request.id`
`ON DELETE CASCADE`, indexed; `description` `str` NOT NULL (1..255, stripped,
non-blank); `quantity` int NOT NULL (`> 0`, enforced in the schema);
`position` int NOT NULL. No timestamps, no `tenant_id`: owned rows rewritten
wholesale with their request, `request.updated_at` is the audit point, the
tenant is inherited exactly as `purchase_request`'s children inherit it. The
table joins `TENANT_INHERITED_TABLES` in `tests/test_migrations_postgres.py`,
never `TENANT_SCOPED_TABLES` (`test_inherited_tables_have_no_tenant_id`
asserts the exact set). `PurchaseRequest.items` relationship with
`cascade="all, delete-orphan"` and
`order_by="PurchaseRequestItem.position, PurchaseRequestItem.id"`.

**D2 — New table `purchase_quote_item`, owned by the quote.** Columns: `id`
UUID pk; `quote_id` UUID FK `purchase_quote.id` `ON DELETE CASCADE`, indexed;
`request_item_id` UUID **nullable** FK `purchase_request_item.id`
`ON DELETE CASCADE`, indexed; `model` `str | None` (≤ 120, stripped, blank
normalised to `NULL`); `unit_price` `Money` NOT NULL (`NUMERIC(12, 2)`, `≥ 0`);
`description` `str | None` (1..255 when present); `quantity` int | None
(`> 0` when present); `position` int NOT NULL. Unique constraint
`(quote_id, request_item_id)` — a quote prices each request line at most once;
Postgres does not collide `NULL`s, so a quote may carry several extra lines.
Relationship on `PurchaseQuote` with `cascade="all, delete-orphan"` and
`order_by="PurchaseQuoteItem.position, PurchaseQuoteItem.id"`; second entry in
`TENANT_INHERITED_TABLES`.

**D3 — `description`/`quantity` on a quote line are an exclusive-or with
`request_item_id`, so no fact is stored twice.** A line that answers a request
line carries `request_item_id` and **neither** `description` nor `quantity` —
both are read through the request line, which is the single source of truth
for *what* and *how many*, and which is exactly what makes the grid rows
align. A supplier's own extra line (the operator's case 2) carries
`request_item_id = NULL` and **both** `description` and `quantity`. Any other
combination is a 422 from a `model_validator`, on create and on update. A
`request_item_id` that exists but belongs to a different request, or does not
exist at all, is a **400** — a new `PurchaseQuoteItemUnknownLineError`
(`DomainError`, so the family's default 400 handler applies), not a 422,
because it is a cross-entity fact the schema cannot see. `PurchaseQuoteItemRead`
**echoes** the resolved `description` and `quantity` (copied from the request
line when linked) so the grid renders from the quote payload alone; storage
stays normalised.

**D4 — `unit_price`/`quantity` are removed from `PurchaseQuote`.** Two sources
of truth for a total is the defect this task exists to delete. The full reader
set is the output of
`grep -rln 'unit_price\|unitPrice' backend/app backend/tests frontend/src`
(26 non-`__pycache__` files, re-verified while writing this revision), and the
diff must not reach past it — backend: `app/models/purchase.py`,
`app/schemas/purchase.py` (`PurchaseQuoteCreate`, `PurchaseQuoteUpdate`,
`PurchaseQuoteRead._compute_total` at ~145), `app/services/purchase_service.py`
(`_quote_total` ~63, `_build_quote_read` ~235, the `quantize_money` calls at
~568 and ~604), `app/seed_demo.py` (~2127/2138/2173); tests
`matrix_world.py` (~670, ~1275 — the shared fixture world, so omitting it
breaks many suites at once), `test_purchase_quotes.py`,
`test_purchase_decision.py`, `test_purchase_isolation.py`,
`test_purchase_quote_attachment.py` (~144, 242, 365),
`test_purchase_requests.py` (~242, 268, 273), `test_purchases_rbac.py` (~76,
123, 131, 183, 259, 311, 336), `test_tenant_isolation.py` (~296),
`test_money_typing.py` (its `(model, attribute)` list),
`test_migrations_postgres.py` (`MONEY_COLUMNS`). Frontend:
`types/purchase.ts` (~19-20, ~99-100), `QuoteFormModal.tsx`,
`QuoteComparisonTable.tsx` (~291), `SelectQuoteModal.tsx` (~87), their three
sibling tests (`QuoteFormModal.test.tsx`, `QuoteComparisonTable.test.tsx`,
`SelectQuoteModal.test.tsx`), `__tests__/usePurchaseRequests.test.tsx` (~34,
142, 153), `__tests__/PurchaseRequestDetailModal.test.tsx` (~70, 89),
`api/__tests__/purchases.test.ts` (~80), `i18n/locales/pt.json` and `en.json`.

**D5 — A supplier may leave a line unpriced, and the total says so.** The
absence of a `purchase_quote_item` for a request line is the representation:
no row, no zero. The quote's total is the sum over the lines it *did* price.
`PurchaseQuoteRead.quoted_item_count` counts **only** the quote's items with a
**non-null `request_item_id`** — a supplier's own extra line is never counted
toward coverage (it *is* counted toward the total), so a quote pricing 2 of 3
request lines plus 1 extra has `quoted_item_count == 2` and 3 entries in
`items`, not `3 == 3`. `is_complete` is
`quoted_item_count == len(request.items)` (trivially `true` when the request
enumerates nothing — load-bearing for D10's ranking on migrated data), and the grid cell renders `Não cotado` — never `R$ 0,00`,
which reads as "free". No line is ever synthesised at zero anywhere in the
stack. A quote with **no** lines at all is still a 422 on create (D6).

**D6 — Cardinalities.** A request may have **zero** lines (the pre-APRAS-73
world, and what the migration produces): `items` is optional on
`PurchaseRequestCreate`/`Update`, `MAX_REQUEST_ITEMS = 50`, and when present
on update it replaces the whole list. A quote must have **at least one**
line: `items` is required on create with `min_length=1`, and when present on
update `min_length=1` (an empty list is a 422, not a way to empty a quote);
`MAX_QUOTE_ITEMS = 50`. Both caps follow the style of `MAX_EXTRA_FIELDS = 20`
— a 422, never a truncation. A zero-line quote would have no price and would
make `is_lowest_price` and the gap panel meaningless.

**D7 — Editing the request's lines after quotes exist.** Allowed while the
request is OPEN, refused otherwise by the **existing**
`_assert_quotes_unfrozen` guard, now also called from `update_request` when
`items` is present (a decided request's grid is immutable; today's
free-text-only update keeps its current behaviour when `items` is absent).
Replacing the list is a wholesale rewrite by `id`: a submitted line carrying
an existing `id` keeps it (and keeps every quote cell attached to it), a line
without an `id` is created, and a line the payload omits is **deleted** —
which cascades away the quote cells that priced it. That deletion is real and
the form states it before submitting (`Ao remover este item, os preços já
lançados por N orçamento(s) para ele serão apagados.`). `position` is
0-based and assigned **by the server** from the submitted index, never
trusted from the client; ordering is `position, id` for determinism, with no
unique constraint on `(request_id, position)` — the rewrite would fight it.
Quote lines are replaced by the same wholesale rule, keyed by
`request_item_id` for linked lines and re-created for extras — so an extra
line's `id` churns on every quote edit even when nothing about it changed.
Known and accepted: nothing in this task addresses an extra line by id.

**D8 — The total, computed in one place.** A line total is
`quantize_money(unit_price * quantity)` over the **effective** quantity (the
request line's, or the extra line's own). The quote total is the `sum` of the
line totals seeded with `money.ZERO`, quantized once more on the way out —
deliberately redundant over exact cents, kept as a defence and documented as
such so a later reader neither removes it as dead code nor believes it rounds
something. `PurchaseQuoteItemRead.line_total` comes from a `model_validator`;
`PurchaseQuoteRead._compute_total` sums `self.items` and nothing else; the
service's `_quote_total(quote)` sums the ORM items. No total is stored and no
total is ever typed by a user. `Decimal`/`NUMERIC(12,2)` throughout — never
float, never cents-as-int.

**D9 — The comparison becomes a grid (the design decision, replacing the
rejected round-1 D7).** Alignment by *free-text description* was rejected
before and is still rejected; alignment by **request line identity** is what
the operator asked for and is exact, because both suppliers point at the same
`purchase_request_item` row. The wide table therefore gains, above the
existing attribute rows, an **items grid**: one row per request line in
`position` order, its header cell reading `<quantidade> × <descrição>`
(`4 × Câmeras IP 4MP`), then one cell per quote column holding that
supplier's `model` (rendered only when present — an absent model renders
**nothing at all**, no dash and no placeholder, because most lines have none
and a gap glyph would read as missing data), its unit price and the line
total. A cell with no row for that line renders the literal `Não cotado` in
muted type with `data-quoted="false"`. Below the request lines come the
supplier **extra lines**, one row each, header cell
`<quantidade> × <descrição>` plus an `Extra` badge, filled only in the column
of the quote that added it and `—`-free empty (`Não cotado` is reserved for a
request line; an extra line's other columns render a plain empty cell with
`data-quoted="false"` and no text, because those suppliers were never asked
for it). Each cell is addressable as
`data-testid="grid-cell-${rowKey}-${quoteId}"`, where `rowKey` is the
`request_item_id` for a request-line row and the quote item's own `id` for a
supplier extra row. The existing rows — Total,
Contato, Observações, Documento and the union'd `extra_fields` — are
unchanged, and the `Unitário × qtd.` row is deleted. Sorting still sorts
columns by `total_price`, and `data-testid="quote-row-${id}"` survives in both
variants. The narrow variant, where each supplier is its own card, renders the
same information as a per-card list: one `<dt>` per line
(`4 × Câmeras IP 4MP`) with model/price/total beneath, `Não cotado` for the
lines that supplier skipped, and a `Cobertura: N de M itens` term.

**D10 — Ranking is over complete quotes only (this CHANGES the APRAS-63
contract).** An incomplete quote is cheaper *because it delivers less*, so
calling it the lowest price compares two different things and points at the
wrong choice on the very screen built for choosing. Therefore: a quote with
`is_complete == false` is **not** eligible for the `Menor preço` badge and is
**never** the baseline of the gap percentage. This is a deliberate,
operator-ruled change to the APRAS-63 behaviour, where `is_lowest_price` was a
pure minimum over totals; the spec states it so nobody restores the old
contract as a "regression fix".

- *Server.* `purchase_service.py:211` —
  `lowest_quote_total=min(totals) if totals else None` — narrows `totals` to
  the totals of **complete** quotes, and `purchase_service.py:244` —
  `is_lowest_price=lowest_total is not None and total == lowest_total` —
  therefore marks only a complete quote. Completeness is the same predicate
  D5/B3 define (`quoted_item_count == len(request.items)` over linked items
  only), computed once per request and reused, so the schema's `is_complete`
  and the service's ranking cannot disagree.
- *No complete quote.* `lowest_quote_total` is `None`, `is_lowest_price` is
  `false` on **every** quote, and no `Menor preço` badge is rendered anywhere.
  The comparison header still renders each column's total and its
  `Cobertura: N de M itens`; the totals row highlights nothing. The decision
  modal renders **no** `decision-gap` (there is no comparable baseline) and
  renders the coverage warning below, so the decision is still possible — it
  is simply made without a percentage.
- *Legacy data.* After the migration every request has **zero** lines, so
  `len(request.items) == 0`, `is_complete` is trivially `true` for every
  existing quote (D5), every quote stays eligible, and ranking on pre-APRAS-73
  data is bit-for-bit what APRAS-63 produced. The migration deletes no badge.
- *Gap, client side.* `lowestQuote` keeps being selected in
  `PurchaseRequestDetailModal.tsx:61-62` as
  `quotes.find((q) => q.is_lowest_price)`, so it inherits the server's
  restriction with no change at the call site. `computeGap` itself gains one
  guard and is no longer unchanged: it returns `null` when
  `quote.is_complete === false`, because a partial offer's distance from a
  full one is not a price difference. Its existing guards
  (`is_lowest_price`, same id, non-positive difference, non-positive baseline)
  are kept.
- *`decision-coverage-warning`, repurposed.* It no longer means "the cheapest
  quote is incomplete" — under this ruling the cheapest quote never is. It now
  fires on **the quote being decided**: when that quote has
  `is_complete === false`, the modal renders
  `data-testid="decision-coverage-warning"` naming its coverage
  (`2 de 3 itens`) and stating that it does not cover the whole request, and
  renders no `decision-gap`. The two panels are mutually exclusive. The
  testid survives; only its trigger and its copy change.
- *Header.* The comparison header shows `Cobertura: N de M itens` under any
  quote with `is_complete === false`, and the decision modal's head panel
  prints the supplier, the coverage and the total (the `qtd × unitário` pair
  is gone).

**D11 — The attachment is untouched.** It stays two columns on
`purchase_quote`, addressed by quote id on routes that do not mention lines;
`_delete_stored_attachment` still runs before the quote delete and the new FKs
cascade the lines with the row. No per-line file.

**D12 — The migration, chained by rule and not by a reserved number.** One
new ordinary revision. Its number and its `down_revision` are **not** literals
in this spec, because three tasks (APRAS-68, APRAS-71, APRAS-73) are racing
for the same parent and a number written today is stale tomorrow.

*The reconciliation rule.* At implementation time the implementer **re-reads
the real head from `backend/alembic/versions/`** — the module whose `revision`
no other module names as its `down_revision` — and chains this revision
immediately after it, numbering it one above the current highest. **No number
is ever reserved ahead of the tree**: a revision numbered `0005` whose
`down_revision` is `0002` is a second head, `alembic upgrade head` fails with
multiple heads, and `test_migrations_postgres.py:302-318` fails before
Postgres is reached. Whichever of the three tasks lands second (and third)
renumbers **its own** file and re-points **its own** `down_revision` at merge
time; the history is asserted to be a single line from one root.

*The head is the head **in git**, not the head on disk.* The rule above says
to re-read the real head; what makes a `down_revision` correct is the history
`alembic upgrade head` will replay after this lands, so the module it names
has to be **committed**. A revision that chains onto a neighbouring task's
still-untracked file commits a pointer to something nobody else has, and
every checkout dies on `Can't locate revision`.

*What shipped.* At implementation time `0003_tenant_invitation` (APRAS-71,
commit `f599012`) was the head in git, and APRAS-68's
`0004_tenant_brand_theme` was in flight and unversioned. This revision is
therefore **`0005_purchase_line_items` with
`down_revision = "0003_tenant_invitation"`** — a deliberate gap in the
numbering, kept so the id cannot collide with APRAS-68's file while both are
open. Alembic orders a history by `down_revision` and never by the digits in
a slug, so the gap costs nothing. Whichever of the two lands second renumbers
**its own** file and re-points **its own** `down_revision`. The slug is 24
characters, inside the 32-char `alembic_version.version_num` limit that
`test_migrations_postgres.py` pins.

`0001_initial_schema.py` is **not** edited (that rule expired when production
applied 0001 on 2026-09-19; editing it now causes drift). The revision imports
nothing from `app/` (asserted by `ast`); any helper is a frozen local literal,
as `0002_tenant_slug.py:20-31` and `0003_tenant_invitation.py:18-23` both do.

- *upgrade*: create `purchase_request_item` and `purchase_quote_item`; then
  `INSERT ... SELECT` **one quote-owned line per existing quote** —
  `request_item_id = NULL`, `quantity` and `unit_price` copied from the quote,
  `position = 0`, `model = NULL`, and as `description` the parent request's
  title, **truncated to 255** — `purchase_request.title` is declared
  `title: str` with no `max_length` (`app/models/purchase.py:25`), so it is an
  unbounded column in Postgres while `purchase_quote_item.description` is
  capped at 255 (D2), and one over-long production title would fail the
  `INSERT ... SELECT` mid-upgrade. The literal the revision carries (spelled
  inline, not imported) is therefore
  `left(COALESCE(NULLIF(btrim(pr.title), ''), 'Item do orçamento'), 255)`. Then drop
  `purchase_quote.unit_price` and `purchase_quote.quantity`.
  **No `purchase_request_item` row is created.** This is the deliberate
  choice: the legacy schema records no shared enumeration, only one free-form
  price per supplier, so inventing a request line would force a quantity to be
  picked out of quotes that may disagree and would silently change the
  suppliers' totals. As a quote-owned extra line, every legacy total is
  **bit-identical** after the upgrade (`quantize_money(unit_price × quantity)`,
  the same product the old `_compute_total` computed), `lowest_quote_total`
  and `selected_quote_total` do not move, and no fact is invented. Requests
  migrate with zero enumerated lines, which D6 explicitly allows; the operator
  gets the grid by enumerating lines on the next purchase. The description
  will read redundantly against its own request's title ("Instalação de 4
  câmeras · 4 × R$ 1.450,00") — redundant-and-true beats generic-and-empty,
  it affects only pre-existing rows, and the first edit of the quote replaces
  it.
- *downgrade*: **lossy, and the spec says so rather than leaving it to be
  found in the data.** It re-adds the two columns nullable, backfills each
  quote from its lowest-`position` line —
  `unit_price` from that line and quantity from
  `COALESCE(qi.quantity, ri.quantity, 1)`, with `COALESCE(..., 0.00)` for the
  impossible empty quote so NOT NULL can be restored — sets NOT NULL, then
  drops both tables. This **discards lines 1..N-1 of every multi-line quote
  and silently reduces that quote's total from the sum of its lines to its
  first line alone** (the mock's 3-line quote falls from R$ 7.480,00 to
  R$ 4.720,00), and **destroys the request's line enumeration entirely**. The
  revision's `downgrade()` docstring must state this in those terms — the
  words *perda* and *backup* must appear in it, so the test can pin a
  substring and the loss is visible to whoever types the command. An operator
  undoing this task after quotes have gained lines **must restore from a
  database backup taken before the upgrade**; no forward-only path recovers
  the dropped lines.
- Proven against real PostgreSQL by the recipe in AGENTS.md (~line 200):
  throwaway cluster on port 55432, UTF-8, `TEST_POSTGRES_URL` **never**
  pointed at the dev database on 5436.

**D13 — The APRAS-64 invariants.** `PurchaseQuoteItem.unit_price` is `Money`;
`PurchaseQuoteItemIn.unit_price` is `MoneyIn`; `line_total` is `Money`.
`test_money_typing.py`'s exhaustive **walk** must pass unchanged, but the
module itself changes in two places. (1) Its explicit `(model, attribute)`
list (`test_money_typing.py:304`) gains
`("app.models.purchase", "PurchaseQuoteItem", "unit_price")` in place of the
`PurchaseQuote` entry. (2) The JSON-number round-trip fixture
(`test_money_typing.py:~392-398`) constructs
`PurchaseQuote(..., unit_price=Decimal("2.68"), quantity=1, ...)` directly and
breaks at construction once those columns are dropped: it becomes a
`PurchaseQuote` with no price fields plus one `PurchaseQuoteItem`
(`unit_price=Decimal("2.68")`, `quantity=1`, `request_item_id=None`,
`description`, `position=0`), so the money-reaches-JSON-as-a-number claim
keeps a live subject and the same asserted value. `MONEY_COLUMNS` in `test_migrations_postgres.py`
likewise swaps `("purchase_quote", "unit_price", 12, 2)` for
`("purchase_quote_item", "unit_price", 12, 2)` — still twelve. Every money
input in the grid editor goes through `limitDecimals(value, MONEY_DECIMALS)`.

**D14 — `MIN_CASES`.** `tests/test_migrations_postgres.py` gains cases, so
`backend/scripts/assert_no_skips.py`'s `MIN_CASES` (26 today) is re-pinned to
the number `uv run pytest --collect-only -q tests/test_migrations_postgres.py`
actually reports — measured, never guessed.
`tests/test_assert_no_skips.py:117` compares it by **equality**, so a stale
value fails the build.

## Files Touched

- `backend/app/models/purchase.py` — `PurchaseRequestItem`,
  `PurchaseQuoteItem`, the two relationships; `unit_price`/`quantity` removed
  from `PurchaseQuote`.
- `backend/app/schemas/purchase.py` — `PurchaseRequestItemIn/Read`,
  `PurchaseQuoteItemIn/Read` (`line_total`, the XOR validator), `items` on
  the request create/update/read and on the quote create/update/read,
  `quoted_item_count`/`is_complete`, `MAX_REQUEST_ITEMS`, `MAX_QUOTE_ITEMS`,
  total from lines.
- `backend/app/core/exceptions.py` — `PurchaseQuoteItemUnknownLineError`.
- `backend/app/services/purchase_service.py` — build/replace request lines and
  quote lines, resolve linked description/quantity, `_quote_total` over lines,
  `_build_quote_read`/`_build_request_read` carry the new fields, the freeze
  guard on `update_request` when `items` is present, and the ranking at ~211
  (`lowest_quote_total`) and ~244 (`is_lowest_price`) restricted to complete
  quotes (D10).
- `backend/alembic/versions/<NNNN>_purchase_line_items.py` — new revision,
  numbered and chained by D12's reconciliation rule
  (`0004_purchase_line_items` on `0003_tenant_invitation` as of today).
- `backend/app/seed_demo.py` — the demo request enumerates lines and the three
  seeded quotes fill them, with one line left unquoted and one supplier extra
  line, so the demo shows the feature.
- `backend/scripts/assert_no_skips.py` — `MIN_CASES` re-pinned.
- `backend/tests/test_migrations_postgres.py` — following the module's own
  documented design (`test_migrations_postgres.py:55-63`): **append** the new
  revision to `EXPECTED_HISTORY` and **move** `HEAD_REVISION` onto it,
  whatever the tree's real length is at the time (four revisions today, since
  APRAS-71 already appended `0003_tenant_invitation`) — no literal hunting, no
  fixed tuple length. Also `TENANT_INHERITED_TABLES` (both tables),
  `MONEY_COLUMNS`, new backfill / dropped-column / over-long-title /
  downgrade cases.
- `backend/tests/test_money_typing.py` — the `(model, attribute)` field list
  **and** the JSON round-trip fixture at ~392-398 (D13).
- `backend/tests/test_purchase_quotes.py`, `test_purchase_decision.py`,
  `test_purchase_isolation.py`, `test_purchase_requests.py` — lines in every
  payload; the new cases of §Test Criteria.
- `backend/tests/matrix_world.py` (~670, ~1275),
  `backend/tests/test_purchases_rbac.py`,
  `backend/tests/test_purchase_quote_attachment.py`,
  `backend/tests/test_tenant_isolation.py` — fixture quotes carry `items`;
  assertions unchanged in intent.
- `frontend/src/types/purchase.ts` — `PurchaseRequestItem`,
  `PurchaseQuoteItem`, `items` on request/quote and on both form data types,
  `quoted_item_count`, `is_complete`; the two removed fields.
- `frontend/src/features/purchase-management/components/PurchaseRequestFormModal.tsx`
  — the request line editor (add/remove/edit, the removal warning of D7).
- `.../components/QuoteFormModal.tsx` — the request lines rendered as fixed
  rows to price (model + unit price, both skippable), plus add/remove of the
  supplier's own extra lines, with live line and quote totals.
- `.../components/QuoteComparisonTable.tsx` — the items grid of D9 in both
  variants.
- `.../components/SelectQuoteModal.tsx` — the head panel and the repurposed
  `decision-coverage-warning`, mutually exclusive with `decision-gap` (D10).
- `.../components/PurchaseRequestDetailModal.tsx` — the request's line list.
- `.../utils/comparison.ts` — `computeGap` gains the incomplete-quote guard
  (D10); a pure
  `buildComparisonGrid(request, quotes)` returning the ordered rows and their
  per-quote cells, so the grid can be tested without rendering.
- `frontend/src/features/purchase-management/__tests__/*` and
  `frontend/src/api/__tests__/purchases.test.ts` — mocks and payloads carry
  `items`; new grid cases.
- `frontend/src/i18n/locales/pt.json`, `en.json` — new keys, key-identical.

## Test Criteria

**Backend.** A request created with three lines returns them in submitted
order with server-assigned `position` 0,1,2. A quote pricing two of those
three lines returns two items, each echoing the request line's `description`
and `quantity` and carrying its own `model` and `line_total`, a `total_price`
equal to their sum, `quoted_item_count == 2` and `is_complete == false`; the
third line simply has no item and nothing anywhere is `0.00`. A quote that
prices all three plus one extra line of its own returns four items, the extra
one with `request_item_id is None` and its own description/quantity, and
`is_complete == true`. The discriminating coverage case: a quote pricing
**2 of 3** request lines **plus one extra** returns 3 items but
`quoted_item_count == 2` and `is_complete == false` — extras never count
toward coverage. A `model` of `null`, `""` and `"   "` all read back as
`null`. Shape errors are 422: a linked line that also sends `description` or
`quantity`; an extra line missing either; `quantity: 0`; a negative price;
a blank description; 51 request lines; 51 quote lines; `items: []` on quote
create or update; `items` missing on quote create. A `request_item_id` from
another request, or unknown, is **400** with
`PurchaseQuoteItemUnknownLineError`'s message. Two lines of one quote pointing
at the same `request_item_id` is refused. Rounding: `(2.675 × 3)` and
`(1.005 × 1)` produce half-up line totals and a total that is their sum, not a
re-rounding of a product. Updating a request's lines keeps the `id`s it
resubmits (the quote cells survive) and deletes the omitted one together with
its cells; the same update on a non-OPEN request is `PurchaseQuoteFrozenError`.
Deleting a quote deletes its lines; deleting a request deletes both.
`lowest_quote_total`, `selected_quote_total`, `total_selected_value` and
`PurchaseDecisionRead.quote_total_price` are asserted over quotes with
**different** coverage. Ranking (D10): with three quotes whose **cheapest is
incomplete**, `is_lowest_price` is `true` only on the cheapest **complete**
quote and `lowest_quote_total` equals that quote's total, not the incomplete
one's; with **no** complete quote, `lowest_quote_total is None` and
`is_lowest_price` is `false` on every quote; with a request that enumerates
**zero** lines (the migrated world), every quote is complete and ranking is
the plain minimum, unchanged from APRAS-63.

**Migration, against real PostgreSQL.** `purchase_quote` no longer has
`unit_price`/`quantity`; a quote inserted before the upgrade becomes exactly
one `purchase_quote_item` with `request_item_id IS NULL`, its old price and
quantity, `position = 0`, `model IS NULL` and the parent request's title as
description; the request has **zero** `purchase_request_item` rows; the
quote's computed total equals the product the old columns implied. A request
whose title is **300 characters** upgrades without error and yields a
description of exactly its first 255 characters; a request with a blank
(`'   '`) title yields `Item do orçamento`.
Upgrade → downgrade → upgrade succeeds; a downgrade over a three-line quote
leaves exactly the `position = 0` line's price and quantity — the loss of D12
asserted, not discovered — and `downgrade.__doc__` contains both `perda` and
`backup`. The money-column and inherited-table assertions pass with the two
new tables.

**Frontend.** The request form adds two lines and posts
`items: [{description, quantity}, …]`; removing a line that quotes priced
shows the warning text before submit. The quote form renders one fixed row per
request line, posts only the rows the user priced, and a row left blank sends
no item at all (not a zero); adding an extra line posts it with its own
description and quantity and no `request_item_id`; typing `2.675` in a price
leaves `2.67` (`limitDecimals`); line and quote totals update live. The
comparison grid renders one row per request line labelled
`4 × Câmeras IP 4MP`, one row per supplier extra line carrying an `Extra`
badge, a cell with `Não cotado` and `data-quoted="false"` for the line a
supplier skipped, no model element at all in a cell whose `model` is null, and
`quote-row-${id}` still present per supplier in both variants; the narrow
variant shows the same lines per card with `Cobertura: N de M itens`. The
comparison marks `Menor preço` on the cheapest **complete** quote even when a
cheaper incomplete quote is present, and marks no column at all when no quote
is complete. The decision modal renders `decision-gap` with the right
difference and percentage when the quote being decided is complete and is not
the lowest; it renders `decision-coverage-warning` (and **no**
`decision-gap`) exactly when the quote being decided has
`is_complete === false`. `computeGap` is unit-tested to return `null` for an
incomplete quote. `buildComparisonGrid` is unit-tested directly for row
order, extras placement and empty cells.

**Gates.** Backend `pytest` at the 90% gate, `ruff check` and
`ruff format --check` clean; `assert_no_skips` green with the re-pinned
`MIN_CASES`. Frontend `tsc -b` clean, `vitest` at 80 lines / 78 functions /
76 branches / 80 statements, `eslint` diff-scoped against the baseline of 375
errors + 2 warnings across 64 files; `pt.json` and `en.json` key-identical.

![Mockup](APRAS-73-mock.html)

## Expected Results

- [ ] A purchase request holds an ordered list of line items, each with a
      description and a quantity (`4 × Câmeras IP 4MP`); a request with zero
      lines is still valid.
- [ ] Each quote prices the request's lines, filling an **optional** offered
      model and a unit price per line, and a line whose model is empty renders
      with no model element, no dash and no placeholder.
- [ ] A line a supplier did not quote has **no** stored row, renders as
      `Não cotado` in the grid with `data-quoted="false"`, and is excluded
      from that quote's total — it never contributes `0.00`.
- [ ] A quote may add its own extra line (description + quantity + price) with
      no `request_item_id`; it appears as its own grid row, marked `Extra`,
      empty in every other quote's column.
- [ ] Each quote read carries `quoted_item_count` (linked items only; a
      supplier's extra lines never count toward coverage) and `is_complete`,
      and the comparison shows `Cobertura: N de M itens` for any incomplete
      quote.
- [ ] Ranking is over complete quotes only, changing the APRAS-63 pure-minimum
      contract: `is_lowest_price` and the `Menor preço` badge land on the
      cheapest quote with `is_complete == true` even when a cheaper incomplete
      quote exists; when no quote is complete `lowest_quote_total` is `None`
      and no quote is badged; on a request whose enumeration is empty every
      quote is complete and ranking is unchanged.
- [ ] The decision modal renders `decision-coverage-warning` exactly when the
      quote **being decided** is incomplete, and renders no `decision-gap` in
      that case; the two panels never appear together.
- [ ] Every quote total is derived as the sum of
      `quantize_money(unit_price × quantity)` over its priced lines, in
      `Decimal`/`NUMERIC(12,2)`, and is never typed by a user;
      `test_money_typing.py`'s exhaustive annotation **walk** still passes,
      with `PurchaseQuoteItem.unit_price` in its field list and its JSON
      round-trip fixture rebuilt on a `PurchaseQuoteItem` (the file itself
      changes).
- [ ] A linked line carrying `description` or `quantity`, an extra line
      missing either, `quantity: 0`, a negative price, a blank description,
      51 lines and an empty quote `items` are all 422; an unknown or
      cross-request `request_item_id` is 400.
- [ ] One new revision `<NNNN>_purchase_line_items`, chained onto the **real
      head of `backend/alembic/versions/` at implementation time** (so
      `alembic upgrade head` reports exactly one head, and `EXPECTED_HISTORY`
      is appended to and `HEAD_REVISION` moved rather than rewritten to a
      fixed length), creates both tables, folds every existing quote into
      exactly one quote-owned line described by its request's title truncated
      to 255 characters, with the same price, quantity and total as before,
      creates no request line, drops
      `purchase_quote.unit_price` and `.quantity`, and round-trips on real
      PostgreSQL; `0001_initial_schema.py` is not edited and the revision
      imports nothing from `app`.
- [ ] The downgrade is documented as lossy for multi-line quotes and for the
      request enumeration (recovery is a restore from backup) both in this
      spec and in `downgrade()`'s docstring, which contains `perda` and
      `backup`, and a test asserts the surviving row.
- [ ] The comparison table renders the grid: one row per request line, one row
      per supplier extra line, one cell per quote, `Unitário × qtd.` gone, and
      `quote-row-${id}` still present per supplier in both variants.
- [ ] `MIN_CASES` is re-pinned to the measured collection count.
- [ ] All backend and frontend gates green (`tsc -b`; vitest 80 lines / 78
      functions / 76 branches / 80 statements; eslint diff-scoped against 375
      errors + 2 warnings across 64 files); locale files key-identical.

## Out of Scope

Per-line attachments and extra fields, per-line REST endpoints, units of
measure, drag-and-drop reordering, automatic matching of supplier extra lines
onto request lines, copying lines between requests.
