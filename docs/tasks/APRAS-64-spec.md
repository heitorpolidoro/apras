# APRAS-64 — Money becomes `Decimal` / `Numeric(12,2)` in the 12 monetary fields

## Scope

Change the internal type of money from binary `float` to `decimal.Decimal`,
backed by `NUMERIC` columns, in the twelve monetary fields of six models, and
make every schema, service, aggregate and test that touches them agree. The
wire format does not change: the API keeps emitting JSON numbers in reais
(`1200.00` → `1200.0`), so no endpoint, field name or status code moves.

**Second deliverable, added by the operator decision of 2026-09-18 (Q3):** the
money **input fields in the frontend** constrain entry to at most two decimal
places, so a value like `2,675` is never typed and never sent. See *Decision 5*
and *Scope widening* below.

The defect being fixed is **rounding on multiplication**, not accumulation
drift. `round()` over a float rounds the binary representation, so
`round(2.675, 2)` is `2.67` and `round(1.005, 2)` is `1.0`. Money is multiplied
in exactly two places — `app/schemas/purchase.py:138`
(`round(unit_price * quantity, 2)`) and `app/services/infraction_service.py:941`
(`round((fine_fee_multiplier or 0.0) * fee, 2)`). The second one prices a fine,
which is a legal document.

Not in scope: integer cents (rejected — with `Numeric(12,2)` only the internal
type changes, while cents would turn every payload into `120000` and drag every
`formatCurrency`, test and consumer along for the same correctness gain); any
change to `physical_progress_pct` or the `planned_progress_json` curve (these
are percentages, not money); `plan.module_prices` (see *Out of Scope*); any new
Alembic revision (see *Migration rule*); any visual redesign, new component
library, currency mask (`R$ 1.234,56` formatting-as-you-type) or locale-aware
separator handling beyond accepting both `.` and `,` in the guard.

### Scope widening — operator decision of 2026-09-18

This task was specified backend-only. The operator's answer to Q3 rejected both
offered options (accept-and-round vs. 422) and gave a third: *"Limitar as casas
decimais no input"*. The task is therefore now **backend plus a frontend input
constraint across four domains** (finance, infractions, purchases, projects —
plus assets and plans, which share the same helper).

Judgement: this stays **one PR-sized deliverable**, not a split. The frontend
half is one new pure helper (~25 lines), one attribute plus one wrapped
`onChange` at each of eleven call sites, and one new test file. It introduces
no new component tree, no new state management, no routing and no API call; it
is not coupled to the backend half at all, which means it adds review surface
but no review *entanglement*. The backend half's indivisibility argument below
is unchanged.

### Why this is one deliverable, not a split

The six domains cannot be retyped one at a time: the moment
`FinancialTransaction.amount` is `Decimal` while a sibling stays `float`, every
mixed expression in `finance_service` and `subscription_service` raises
`TypeError` at runtime, and all twelve columns live in the *same* migration
file, so per-domain PRs would serially rewrite `0001_initial_schema.py`. The
change is wide but mechanical and has a single, indivisible acceptance
condition: no money is a float anywhere.

## Approach

### Migration rule — binding operator decision of 2026-09-17

**Do not create a new Alembic revision.** The repository now holds exactly one
migration, `backend/alembic/versions/0001_initial_schema.py` (the APRAS-58
consolidation, merged to master today and **not yet pushed**). The twelve
columns are edited **inside that file** so they are born with the right type.
Resetting local and development databases is authorised and expected; there is
no `op.alter_column` anywhere and no second revision file — the repository must
still contain exactly one revision module afterwards
(`tests/test_migrations_postgres.py::test_versions_holds_exactly_one_revision_module`
keeps that true). This task must therefore land **before** APRAS-59's
production reset and `git push`; after the push, editing `0001` would be schema
drift fixable only by a second production reset. AGENTS.md's "migrations are
never edited" rule is suspended for this file only, by that same decision, and
the file stays excluded from `ruff format`.

### Decision 1 — rounding policy: `ROUND_HALF_UP`

Every money value produced by a multiplication or a division is quantized with
`Decimal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)`. Python's
`Decimal` default is `ROUND_HALF_EVEN` (banker's rounding); the Brazilian
commercial convention, and the one a resident checks a fine against with a
pocket calculator, is half away from zero. The single implementation is
`quantize_money()` in the new `backend/app/core/money.py`; no other module
calls `.quantize(` or `round(` on money. Rounding is **explicit in the
service**, never delegated to the column scale: SQLite's `Numeric` processor
and PostgreSQL's `NUMERIC(12,2)` do not agree on a third decimal (measured:
writing `Decimal("2.675")` through SQLite stores `2.67`, PostgreSQL stores
`2.68`), so a value must already be quantized before it is assigned.

This is potentially a matter for the association's own rules — recorded as
operator question Q1, with `ROUND_HALF_UP` as the implemented answer unless the
operator rules otherwise.

### Decision 2 — serialisation: JSON number, not string

Measured on this repository's pinned Pydantic (2.13.3): a bare `Decimal` field
serialises to the **string** `"1200.00"` through `model_dump_json()` and
through `fastapi.encoders.jsonable_encoder`, and Pydantic exposes no
`ser_json_decimal` config key. The frontend would break silently. The mechanism
is therefore one shared annotated type in `backend/app/core/money.py`:

`Money = Annotated[Decimal, Field(max_digits=12, decimal_places=2, ge=0),
MONEY_SER]`, where `MONEY_SER = PlainSerializer(float, return_type=float,
when_used="json")` is a module-level singleton in `app/core/money.py` (a named
singleton, not an inline call, so the exhaustive scan can recognise it by
identity — see *Test criteria*).

Measured end to end through a FastAPI route with a `response_model`: the body
is `{"amount":1200.0}`, a JSON number, and `return_type=float` keeps the
OpenAPI schema `number`. A bare `Decimal` field on the same route emits
`"2.68"`, a string — so the annotation, not the Python type, is the load-bearing
part. Every monetary field in `app/models/**` and `app/schemas/**` — including
the derived totals — is annotated `Money` or `MoneyIn` (Decision 4), never bare
`Decimal`, and a test enforces that exhaustively (see *Test criteria*). `Money`
is also what carries `max_digits=12, decimal_places=2` on table models, which
is what makes SQLModel emit `NUMERIC(12, 2)` (measured).

### Decision 4 — request bodies accept more than two decimals; the service quantizes

`Money`'s `decimal_places=2` makes Pydantic reject `Decimal("2.675")` with
`decimal_max_places`, i.e. a **422** (measured on the pinned Pydantic 2.13.3).
Today `PurchaseQuoteCreate.unit_price` is `float = Field(..., ge=0)`
(`app/schemas/purchase.py:69`) and `2.675` is accepted, so putting `Money` on
request schemas would be a new rejection of input the API accepts today — a
wire-contract change this task has ruled out of scope.

Request-side monetary fields therefore use a second annotated type that has no
scale bound:

`MoneyIn = Annotated[Decimal, Field(ge=0), MONEY_IN_SER]`, where
`MONEY_IN_SER` is a **second, distinct** `PlainSerializer(float,
return_type=float, when_used="json")` instance in `app/core/money.py`. It
behaves identically; being a separate object is what lets the scan tell a
`MoneyIn` field from a `Money` one by identity alone.

Consequence, stated plainly because it is user-visible at the infraction input
boundary: a fine amount or unit price typed with three decimals is **accepted
and rounded half-up** by `quantize_money()` before it is persisted — `2.675`
becomes `2.68` — it is not a 422. Only a value wider than the column
(`max_digits`, e.g. thirteen integer digits) is rejected, and it is rejected by
Pydantic on the response/table side rather than surfacing as a database error.
Rounding is silent by design here: it preserves today's behaviour and only
corrects its direction (the float path yields `2.67`).

**This backend behaviour is confirmed and unchanged by the Q3 decision.**
`MoneyIn` stays on request schemas, `quantize_money` stays `ROUND_HALF_UP`, and
the `2.675 → 2.68` regression (ER 5) stays valid. The operator's ruling adds a
*screen-side* constraint in front of it (Decision 5); it does not introduce a
new 422 and does not move the API contract. The backend remains the tolerant
layer — a third decimal arriving from curl, an integration or an older client
is still accepted and quantized.

`MoneyIn` is used only on `*Create` / `*Update` request schemas. Every read
schema, every derived total and every table-model column uses `Money`.

### Decision 3 — `fine_fee_multiplier` is `Numeric(8,4)`, not `Numeric(12,2)`

It is a ratio, not an amount, and it must be `Decimal` because
`Decimal * float` is a `TypeError` at the one site that uses it. Scale 2 would
cap a bylaw at whole percents of the condo fee (`0.20`), silently truncating
`12,5% = 0.125`; scale 4 covers hundredths of a percent. It carries the `Money`
serializer (so it still reaches the frontend as a number) but its own
`max_digits=8, decimal_places=4`. Its *product* with the condo fee is quantized
to two decimals with `ROUND_HALF_UP`, like every other amount. Recorded as
operator question Q2.

### Decision 5 — the frontend money inputs limit entry to two decimals

**Operator decision of 2026-09-18, answering Q3.** The screen prevents the
third decimal before it reaches the API.

**Mechanism — an `onChange` guard built on one pure helper, not `step` alone.**
A new `frontend/src/lib/money.ts` exports

- `MONEY_DECIMALS = 2` and `RATIO_DECIMALS = 4`;
- `limitDecimals(raw: string, places: number): string`, a pure function that
  **truncates** (never rounds) the fractional part: it returns `raw` unchanged
  when there is no separator or at most `places` fractional digits, and cuts
  the surplus digits otherwise. `"2.675" → "2.67"`, `"2,675" → "2,67"` (both
  `.` and `,` are accepted as separator and the typed separator is preserved),
  `"1200" → "1200"`, `"2.6" → "2.6"`. `""`, `"2."`, `"-"` and `"2,"` pass
  through unchanged so a half-typed value is never destroyed mid-keystroke.

Each money input then becomes
`onChange={(e) => setX(limitDecimals(e.target.value, MONEY_DECIMALS))}` where
the state is a string, and `Number(limitDecimals(e.target.value,
MONEY_DECIMALS))` where the state is a number (both shapes exist in the call
sites below — do not unify them, that is a refactor this task does not fund).

**Why a guard and not the native `step`.** `step="0.01"` is already present on
seven of these inputs and does nothing here: `step` is consulted only by native
constraint validation (`:invalid`, native form submit), and every one of these
modals submits through an `onClick` handler on a `<Button>`, never through a
native `<form>` submit — so a step violation blocks nothing today. `step` also
never prevents a character from being typed or pasted. It is kept (and added
where missing) as the widget hint that drives the spinner increment and the
mobile keypad; the guard is what enforces the rule.

**Paste.** No `onPaste` handler is added and none is needed: pasting into a
controlled input fires `onChange` with the pasted text, so the same guard runs.
A pasted `2,675` lands in the field as `2,67`.

**What the user sees.** The surplus digit simply never appears in the field —
no error message, no toast, no red border, no blocked submit. The value shown
is the value sent.

**The multiplier is not money.** `fine_fee_multiplier` is a ratio stored
`Numeric(8,4)` (Decision 3), so its input uses `limitDecimals(raw,
RATIO_DECIMALS)` and `step="0.0001"`. Limiting it to two decimals would undo
Decision 3 and truncate a 12,5% bylaw. This is the one input where `places` is
not `2`.

**Shared component — deliberately not used.** A `<MoneyInput>` wrapper would
have to absorb eleven different state shapes, three different className
conventions and two different label idioms (`<Label htmlFor>` vs bare
`<label>`), touching far more of each file than the constraint warrants. The
pure helper gives the same single point of truth with a one-line diff per call
site.

**The eleven money inputs, verified against the tree** (line numbers are from
master at the time of writing; locate by the `value=` binding, not the line):

| File | Line | Field | `places` |
|---|---|---|---|
| `frontend/src/features/finance/components/TransactionFormModal.tsx` | 141 | `amount` | 2 |
| `frontend/src/features/finance/components/BudgetLineFormModal.tsx` | 111 | `planned_amount` | 2 |
| `frontend/src/features/purchase-management/components/QuoteFormModal.tsx` | 205 | `unit_price` | 2 |
| `frontend/src/features/infraction-management/pages/InfractionRulesPage.tsx` | 105 | `condo_fee_amount` | 2 |
| `frontend/src/features/infraction-management/pages/InfractionRulesPage.tsx` | 331 | `fine_fixed_amount` | 2 |
| `frontend/src/features/infraction-management/pages/InfractionRulesPage.tsx` | 344 | `fine_fee_multiplier` | **4** |
| `frontend/src/features/project-management/components/ProjectFormModal.tsx` | 151 | `total_budget` | 2 |
| `frontend/src/features/project-management/components/ProjectFormModal.tsx` | 172 | `executed_budget` | 2 |
| `frontend/src/features/project-management/components/ProjectUpdateModal.tsx` | 115 | `cost_impact` | 2 |
| `frontend/src/features/asset-management/components/AssetFormModal.tsx` | 312 | `acquisition_value` | 2 |
| `frontend/src/features/user-administration/pages/PlansAdminPage.tsx` | 210 | `base_price` | 2 |
| `frontend/src/features/user-administration/pages/PlansAdminPage.tsx` | 257 | `module_prices[module]` | 2 |

(Twelve rows: eleven money fields plus the ratio. `module_prices` is a money
input even though its *column* is out of scope for the `Decimal` work.)

**Non-money `type="number"` inputs that must be left alone** — naming them so
the developer does not over-apply the guard: `AssetFormModal` 357
(`current_quantity`) and 376 (`min_quantity`), `BudgetLineFormModal` 97
(`year`), `QuoteFormModal` 221 (`quantity`), `InfractionRulesPage` 175
(`recidivism_window_days`) and 295 (`defense_deadline_days`),
`ProjectFormModal` 190 (`physical_progress_pct`), plus everything in
`LotFormModal`, `StockMovementModal`, `ReservableSpacesPage`,
`DocumentCenterPage`, `DocumentUploadModal`, `MilestoneFormModal` and
`AvatarCropEditor`.

### Behaviour that must be true afterwards

- The twelve fields are `Decimal` in the model, in every request/response
  schema, and `NUMERIC` in PostgreSQL: `budget_line.planned_amount`,
  `financial_transaction.amount`, `infraction_policy_step.fine_fixed_amount`,
  `infraction_policy_step.fine_fee_multiplier`, `infraction.fine_amount`,
  `infraction_settings.condo_fee_amount`, `construction_project.total_budget`,
  `construction_project.executed_budget`, `project_change_order.cost_impact`,
  `purchase_quote.unit_price`, `plan.base_price`, `asset.acquisition_value`.
- Every value **derived** from them is `Decimal` too — the finance summary,
  monthly series and budget-vs-executed report, the asset patrimonial total,
  the purchase quote `total_price` / `lowest_quote_total` /
  `selected_quote_total` / `total_selected_value`, and the subscription
  `monthly_price` / `estimated_monthly_total` — so no expression ever mixes the
  two numeric types.
- Payload compatibility is exact: a request may send `1200`, `1200.00` or
  `"1200.00"` and every response field is a JSON **number**. No endpoint path,
  field name, status code or validation bound (`ge=0`, `gt=0`) changes.
- The API contract for input is unchanged (Decision 4): a request value with
  more than two decimals is still **accepted**, and is quantized half-up before
  it is stored; no input accepted today starts returning 422. A value wider
  than the column is a 422 from Pydantic, not a database error.
- No money input on any screen can hold a third decimal: typing or pasting
  `2,675` leaves the field at `2,67`, and the request body therefore carries
  `2.67`. The one exception is `fine_fee_multiplier`, which holds four
  decimals. Interactive demonstration: `docs/tasks/APRAS-64-mock.html`.

### Files touched

- `backend/app/core/money.py` — **new**: the `Money` and `MoneyIn` annotated
  types, their two serializer singletons `MONEY_SER` / `MONEY_IN_SER`, `CENTS`,
  and `quantize_money()` (the only `ROUND_HALF_UP` call in the codebase).
- `backend/alembic/versions/0001_initial_schema.py` — the twelve `sa.Float()`
  columns become `sa.Numeric(12, 2)` (eleven) and `sa.Numeric(8, 4)`
  (`fine_fee_multiplier`); no new revision, no `alter_column`.
- `backend/app/models/finance.py`, `infraction.py`, `project.py`,
  `purchase.py`, `plan.py`, `asset.py` — the twelve field annotations, plus the
  two module docstrings that currently assert "Money is `float`"
  (`infraction.py:38`, `plan.py:27`).
- `backend/app/schemas/finance.py`, `infraction.py`, `project.py`,
  `purchase.py`, `plan.py`, `asset.py`, `subscription.py` — every monetary and
  derived-total field retyped; `purchase.py`'s `_compute_total` validator uses
  `quantize_money(unit_price * quantity)`.
- `backend/app/services/finance_service.py` (the `func.sum` coalesces and the
  `float(...)` coercions around lines 419–435 and 533),
  `infraction_service.py` (`_price`, line ~941),
  `purchase_service.py`, `project_service.py`, `project_report_service.py`,
  `asset_service.py`, `plan_service.py` (`_validate_base_price` stops calling
  `float()`), `subscription_service.py` (`estimated_monthly_total`).
- `backend/app/seed_demo.py` — monetary literals become `Decimal`.
- `backend/tests/test_money_typing.py` — **new** (see below).
- `backend/tests/test_migrations_postgres.py` — one new case asserting the live
  column types.
- The existing suites that assert monetary values —
  `test_finance.py`, `test_assets.py`, `test_projects.py`,
  `test_project_report.py`, `test_purchase_quotes.py`,
  `test_purchase_decision.py`, `test_purchase_requests.py`,
  `test_infractions.py`, `test_infraction_escalation.py`,
  `test_infraction_rules.py`, `test_plans_api.py`, `test_subscription_api.py`,
  `test_subscription_admin_api.py`, their `_rbac` / `_isolation` siblings, and
  the `matrix_world.py` / `subscription_helpers.py` fixtures — updated where a
  float literal or a float assertion no longer holds.
- `frontend/src/lib/money.ts` — **new**: `limitDecimals`, `MONEY_DECIMALS`,
  `RATIO_DECIMALS`.
- `frontend/src/lib/__tests__/money.test.ts` — **new**: the helper's table of
  cases.
- The eight components holding the twelve inputs of the Decision 5 table —
  `features/finance/components/TransactionFormModal.tsx`,
  `features/finance/components/BudgetLineFormModal.tsx`,
  `features/purchase-management/components/QuoteFormModal.tsx`,
  `features/infraction-management/pages/InfractionRulesPage.tsx`,
  `features/project-management/components/ProjectFormModal.tsx`,
  `features/project-management/components/ProjectUpdateModal.tsx`,
  `features/asset-management/components/AssetFormModal.tsx`,
  `features/user-administration/pages/PlansAdminPage.tsx` — each: wrap the
  money `onChange` in `limitDecimals`, and add `step` / `min="0"` /
  `inputMode="decimal"` where missing (`PlansAdminPage` and
  `InfractionRulesPage` carry no `step` today).
- `frontend/src/features/purchase-management/__tests__/` and
  `frontend/src/features/infraction-management/__tests__/` — the two
  component-level wiring tests (see *Test criteria*).

### Test criteria

- `backend/tests/test_money_typing.py` (new): asserts, for each of the twelve
  fields, that the Python annotation is not `float`. It makes **no assertion
  about precision or scale**. Precision and scale are verified in exactly one
  place — the real-PostgreSQL case below, which reads the schema the migration
  actually created. Neither the annotation metadata nor
  `Table.columns[...].type` is used as a precision oracle: the latter is
  unreliable (SQLModel emits a bare `NUMERIC` without precision for a nullable
  money column — measured on the pinned stack: `amount: Money` gives
  `NUMERIC(12, 2)` but `opt: Money | None` gives `NUMERIC`), and the former
  nests `max_digits`/`decimal_places` at different depths depending on
  nullability (measured on pydantic 2.13.3: flattened into `__metadata__` for
  `a: Money`, but one level deeper inside a `FieldInfo.metadata` for
  `b: Money | None`). The annotation walk described below therefore has exactly
  one job: finding the serializer by identity on every `Decimal` leaf. Asserts
  **exhaustively** — by importing every module under
  `app/models/` and `app/schemas/` and walking `model_fields` of every
  `BaseModel`/`SQLModel` subclass defined there — that no field mentioning
  `Decimal` is left bare. The scan is a **recursive walk of the field's
  annotation**, seeded with `tuple(FieldInfo.metadata)` and accumulating each
  `Annotated` member's `__metadata__`: unwrap `Annotated` via
  `typing.get_origin`/`get_args`, recurse into every non-`NoneType` argument of
  a union/list/dict, and stop at each leaf type; a leaf that is `Decimal` must
  carry `MONEY_SER` or `MONEY_IN_SER` **by identity** in its accumulated
  metadata, otherwise the field is bare and the test fails. Both halves are
  load-bearing: Pydantic 2.13.3 flattens `x: Money` so the metadata lands on
  `FieldInfo.metadata` while the annotation is a plain `Decimal`, but keeps
  `x: Money | None` as `Optional[Annotated[...]]` with `FieldInfo.metadata`
  empty. Measured on the pinned interpreter, the walk classifies all four
  shapes correctly — `Money` → Money, `Money | None` → Money, `Decimal` → bare,
  `Decimal | None` → bare — and likewise `MoneyIn`, `MoneyIn | None`,
  `list[Money]`, `dict[str, Money]` and `list[Decimal]` (bare), which the flat
  `FieldInfo.metadata` check cannot do. The same walk asserts each
  request-schema (`*Create`/`*Update`) money field resolves to `MONEY_IN_SER`
  and every other resolves to `MONEY_SER`. Also asserts
  `quantize_money(Decimal("2.675")) == Decimal("2.68")` and
  `quantize_money(Decimal("1.005")) == Decimal("1.01")` (both wrong under the
  old float path); asserts a response body parsed with
  `json.loads(response.text)` yields `float`/`int`, never `str`, for a money
  field on at least one endpoint per affected domain; and asserts by text scan
  that no module under `app/` rounds money with the builtin `round(`.
- `backend/tests/test_migrations_postgres.py` (new case): against the real
  PostgreSQL named by `TEST_POSTGRES_URL`, this is the **sole** precision check
  in the task. Reading `information_schema.columns`, all twelve columns report
  `data_type = 'numeric'`; eleven of them report
  `numeric_precision = 12, numeric_scale = 2` —
  `budget_line.planned_amount`, `financial_transaction.amount`,
  `infraction_policy_step.fine_fixed_amount` (nullable),
  `infraction.fine_amount` (nullable),
  `infraction_settings.condo_fee_amount` (nullable),
  `construction_project.total_budget`,
  `construction_project.executed_budget`,
  `project_change_order.cost_impact` (nullable),
  `purchase_quote.unit_price`, `plan.base_price`,
  `asset.acquisition_value` (nullable) — and
  `infraction_policy_step.fine_fee_multiplier` (nullable) reports
  `numeric_precision = 8, numeric_scale = 4`. Nullability does not weaken the
  assertion: the check reads the database, not the Python annotation. A
  round-trip of `Decimal("1234.56")` through insert/select returns an equal
  `Decimal`, with `func.sum()` over two rows exact. CI's `backend-migrations`
  job is the source of truth (the module self-skips without the env var).
- The two multiplication regressions are pinned where they live: a purchase
  quote created with `unit_price=2.675, quantity=1` is accepted (not 422,
  Decision 4) and reads back `total_price = 2.68` — the float path returns
  `2.67`; and a fine priced from `fine_fee_multiplier=0.5` over a
  `condo_fee_amount=1200.01` reads back `600.01`, not `600.0`.
- `cd backend && uv run pytest` passes with the existing 90% coverage gate, and
  `uv run ruff check . && uv run ruff format --check .` reports zero findings.
- `frontend/src/lib/__tests__/money.test.ts` (new) drives `limitDecimals`
  through a table: `("2.675", 2) === "2.67"`, `("2,675", 2) === "2,67"`,
  `("2.6", 2) === "2.6"`, `("1200", 2) === "1200"`, `("", 2) === ""`,
  `("2.", 2) === "2."`, `("-", 2) === "-"`, `("0.129", 4) === "0.129"`,
  `("0.12345", 4) === "0.1234"`. Truncation, not rounding, is asserted
  explicitly: `("2.999", 2) === "2.99"`.
- Wiring is proven at the component level in at least two places, one of them
  the four-decimal exception: with `@testing-library/react`, firing
  `change` with `"2.675"` on `QuoteFormModal`'s unit-price input leaves the
  input's displayed value `"2.67"` (and `fireEvent.paste`/a `change` carrying
  pasted text behaves identically, since both route through `onChange`); firing
  `change` with `"0.12345"` on `InfractionRulesPage`'s fine-multiplier input
  leaves `"0.1234"`, proving the multiplier keeps four decimals.
- Frontend gates, all four: `cd frontend && npx tsc -b` is clean;
  `npm run test -- --coverage` passes the thresholds declared in
  `frontend/vitest.config.ts` — **lines 80, functions 78, branches 76,
  statements 80** (these are the real numbers; do not quote 75); and `eslint`
  is **diff-scoped** — the repository carries roughly 375 pre-existing errors,
  so the gate is that no *new* finding appears on the files this task touches,
  not a clean global run.

## Expected Results

- [ ] All twelve fields are `decimal.Decimal` in `app/models/**` and in every
      request/response schema; no monetary field is annotated `float`.
- [ ] `backend/alembic/versions/0001_initial_schema.py` declares those columns
      `sa.Numeric(12, 2)` (and `sa.Numeric(8, 4)` for `fine_fee_multiplier`),
      and the repository still contains exactly one Alembic revision module —
      no new revision, no `alter_column`.
- [ ] Against real PostgreSQL (`TEST_POSTGRES_URL`, CI job
      `backend-migrations`) — the only place precision and scale are checked —
      `information_schema.columns` reports `data_type = 'numeric'` for all
      twelve columns, with `numeric_precision = 12, numeric_scale = 2` for
      `budget_line.planned_amount`, `financial_transaction.amount`,
      `infraction_policy_step.fine_fixed_amount`, `infraction.fine_amount`,
      `infraction_settings.condo_fee_amount`,
      `construction_project.total_budget`,
      `construction_project.executed_budget`,
      `project_change_order.cost_impact`, `purchase_quote.unit_price`,
      `plan.base_price` and `asset.acquisition_value` (the six nullable ones
      included), and `numeric_precision = 8, numeric_scale = 4` for
      `infraction_policy_step.fine_fee_multiplier`; and a `Decimal`
      round-trips unchanged, including through `func.sum()`.
- [ ] Money multiplication is quantized with `ROUND_HALF_UP`:
      `quantize_money(Decimal("2.675")) == Decimal("2.68")` and
      `quantize_money(Decimal("1.005")) == Decimal("1.01")`, and both call
      sites (`schemas/purchase.py` total, `infraction_service._price`) go
      through it; no `round(` over money remains under `app/`.
- [ ] A purchase quote created with `unit_price = 2.675, quantity = 1` is
      accepted (201, not 422) and reads back `total_price = 2.68` (the old
      float path returned `2.67`); a fine priced from
      `fine_fee_multiplier = 0.5` over `condo_fee_amount = 1200.01` reads back
      `600.01` (the old float path returned `600.0`).
- [ ] `test_money_typing.py` proves exhaustively that no bare `Decimal` field
      survives: for every `BaseModel`/`SQLModel` subclass defined under
      `app/models/` and `app/schemas/`, a recursive walk of each field's
      annotation (seeded with `FieldInfo.metadata`, unwrapping `Annotated` and
      recursing through unions, lists and dicts) finds `MONEY_SER` or
      `MONEY_IN_SER` from `app/core/money.py` by identity on every `Decimal`
      leaf — `MONEY_IN_SER` on `*Create`/`*Update` request schemas, `MONEY_SER`
      everywhere else — and the test fails if a single `Decimal` leaf is bare.
      The walk classifies `Money`, `Money | None`, `Decimal` and
      `Decimal | None` distinctly (nullable money is annotated correctly and
      still detected).
- [ ] Monetary fields reach the client as JSON **numbers**, not strings: a test
      parses `response.text` with `json.loads` for at least one endpoint per
      affected domain and asserts `float`/`int` (end-to-end confirmation of the
      exhaustive scan above).
- [ ] `frontend/src/lib/money.ts` exports a pure `limitDecimals(raw, places)`
      that **truncates** rather than rounds, and
      `frontend/src/lib/__tests__/money.test.ts` proves it:
      `limitDecimals("2.675", 2) === "2.67"`, `limitDecimals("2,675", 2) ===
      "2,67"`, `limitDecimals("2.999", 2) === "2.99"`,
      `limitDecimals("0.12345", 4) === "0.1234"`, and `""`, `"2."`, `"2.6"`,
      `"1200"` pass through unchanged.
- [ ] All twelve money inputs listed in *Decision 5* route their `onChange`
      through `limitDecimals` — the finance transaction `amount` and budget
      line `planned_amount`, the purchase quote `unit_price`, the infraction
      `condo_fee_amount` and `fine_fixed_amount`, the project `total_budget`,
      `executed_budget` and `cost_impact`, the asset `acquisition_value`, and
      the plan `base_price` and `module_prices` — with `places = 2`, and each
      carries `step` (`0.01`), `min="0"` and `inputMode="decimal"`.
      `fine_fee_multiplier` uses `places = 4` and `step="0.0001"`. The
      non-money `type="number"` inputs named in *Decision 5* are unchanged.
- [ ] A vitest component test proves the wiring end to end: a `change` event
      carrying `"2.675"` (typed or pasted — both fire `onChange`) on
      `QuoteFormModal`'s unit-price input leaves the input showing `"2.67"`,
      with no error message rendered; and `"0.12345"` on
      `InfractionRulesPage`'s fine-multiplier input leaves `"0.1234"`.
- [ ] `cd backend && uv run pytest` passes with the 90% coverage gate, and
      `ruff check` + `ruff format --check` report zero findings.
- [ ] Frontend gates pass: `npx tsc -b` clean; vitest meets
      `frontend/vitest.config.ts`'s thresholds of **80 lines / 78 functions /
      76 branches / 80 statements**; and eslint, scored diff-scoped against the
      repository's ~375 pre-existing errors, reports no new finding on the
      files this task touches.

## Out of Scope

- `plan.module_prices` (a portable `JSON` dict of `str -> float`): JSON has no
  decimal type, so the value cannot be stored as `Numeric` without a table of
  its own. It is read back as `Decimal(str(value))` at the one place that sums
  it (`subscription_service.estimated_monthly_total`) so the total is exact and
  no expression mixes types, and the column itself is left alone. Prices are
  inert in this project — nothing is charged.
- `physical_progress_pct`, `variance_pct` and the `planned_progress_json`
  curve: percentages, not money.
- Integer cents, currency codes beyond the existing `currency` string, any
  payment provider, and any `formatCurrency` / display-formatting change. The
  only frontend change in this task is the Decision 5 input constraint.
- `plan.module_prices`'s **column** stays `JSON` (above), but its **input** is
  in scope for Decision 5 — limiting what is typed costs nothing and keeps the
  plan form self-consistent.
- The production reset and push: that is APRAS-59, which this task must precede.

## Operator Questions — answered 2026-09-18

- **Q1 — `ROUND_HALF_UP` for fines: CONFIRMED** ("Sim"). No change to the spec.
- **Q2 — `fine_fee_multiplier` as `Numeric(8,4)`: CONFIRMED** ("Sim"). No
  change to the spec; and Decision 5 respects it by limiting that one input to
  four decimals rather than two.
- **Q3 — three decimals in a money field: neither 422 nor silent rounding —
  "limitar as casas decimais no input".** The operator rejected both offered
  options and ruled a third: the money input fields in the frontend accept at
  most two decimal places, so `2,675` is never typed and never sent. The
  backend is unchanged — `MoneyIn` keeps accepting three decimals and
  `quantize_money` keeps rounding them half-up, so no input accepted today
  starts returning 422 and the `2.675 → 2.68` regression stays valid. See
  *Decision 5* for the mechanism and *Scope widening* for the consequence.

### Original wording of the questions

- **Q1 — rounding policy for a fine.** Python rounds half-to-even by default;
  Brazilian commercial practice is half-up. Implemented answer:
  **`ROUND_HALF_UP`** everywhere, via `quantize_money()`, because the fine is a
  legal document a resident recomputes by hand and half-up is the convention
  they will use. If the association's regimento states otherwise, the single
  constant in `app/core/money.py` is the only line to change.
- **Q2 — precision of `fine_fee_multiplier`.** Implemented answer:
  `Numeric(8, 4)` rather than `(12, 2)`, so a bylaw can say 12,5% of the condo
  fee (`0.125`) instead of being silently truncated to whole percents. Confirm
  that a multiplier finer than four decimals is not needed.
- **Q3 — three decimals in a money field: 422 or silent rounding?** A fine
  amount or unit price typed as `2.675` is accepted today and will keep being
  accepted, rounded half-up to `2.68` before storage (Decision 4), because
  refusing it would be a new 422 on input the API accepts today. The
  alternative is to annotate request schemas `Money` instead of `MoneyIn`, so
  the operator typing a third decimal gets an explicit validation error rather
  than a silently adjusted fine. Implemented answer: **accept and round**.
  Confirm, or rule for the 422 — it is one annotation to change.
