# APRAS-52 — Expor o histórico de assinatura do tenant com rota e tabela na página do superuser

Merge base for every measurement below: **`e188866`** (APRAS-44), tree clean,
measured by running the real application and the real registry through
`backend/.venv/bin/python`. No count in this spec is an estimate.

**`blockedBy: [APRAS-51]`.** APRAS-51 lands first. Its ER-4 pins
`ROUTE_PERMISSIONS` at 201, `PERMISSIONS` at 174 and `UNGUARDED_ROUTES` at 22,
and it adds no route, so every registry number measured at `e188866` is also
the number this task starts from. What APRAS-51 *does* add and this task must
stay consistent with — `tests/test_permission_alignment.py`'s five declared
enforcement forms (D/S/M/E/H = 53/5/3/5/135 = 201), the empty `UNENFORCED`
set, `REFUSAL_SHAPES`, and the overriding `tests/data/parity_matrix_baseline_51.json`
with its derived `OVERRIDDEN_CELLS` — is answered in §2.3 and §4.

## 1. Scope

APRAS-40 §8.4 and §10.3 asked for a change-history table on the superuser
subscription screen, but §5.3 pinned **exactly three** operator routes and
none of them returns history. The screen shipped without the table (deviation
D10, accepted at code review on 2026-09-03) and
`TenantSubscriptionsPage.tsx`'s own header comment records the gap in so many
words: *"The change history lives on the tenant-side `/subscription` page […]
this task deliberately adds no fourth"*. The rows exist — every plan change,
courtesy grant/revoke, tenant contracting act and raw operator override
already writes one through `SubscriptionService.record`.

This task adds:

1. a **fourth** superuser per-tenant subscription route that returns one
   tenant's `subscription_change` rows, newest first, paginated;
2. the **history table** on the existing superuser page, with an empty state
   and a pagination control;
3. the registry, structural-walker and documentation accounting that a new
   superuser route moves — and the *proof*, at the level of the six legacy
   parity profiles, that it moves no parity cell.

It does **not** add a migration, a tenant-side history route (one already
exists: `GET /api/v1/subscription/history`, APRAS-40 §5.1), an export, a
filter, or any permission. See §9.

## 2. The route, and its classification

### 2.1 The path

```
GET /api/v1/tenants/{tenant_id}/subscription/history
```

on the **existing global `tenants` router**
(`app/api/v1/endpoints/tenants.py`), in the §5.3 block, immediately after
`PUT /{tenant_id}/subscription/courtesy`.

The board's ER-1 writes the path as `/api/v1/subscriptions/{tenant_id}/history`.
That shorthand names the *subject*, not a mount: there is no
`/api/v1/subscriptions` router in this codebase (the tenant-side area is
singular `/api/v1/subscription` and carries no `{tenant_id}` on purpose), and
minting one would mean a new router, a new `GLOBAL_ROUTES` /
`TENANT_SCOPED` classification decision, and a per-tenant operator path shaped
unlike every other one in the tree. The dispatch's binding instruction is
"mirror the three sibling routes exactly", and the mirror is the path above.
§10 records this as the one reversible decision an operator may want to
overrule; it costs one string in three places if so.

### 2.2 The guard, in the sibling form, verbatim

```python
@router.get("/{tenant_id}/subscription/history")
def get_tenant_subscription_history(
    tenant_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    _: Annotated[User, Depends(api_deps.get_current_superuser)],
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> list[SubscriptionChangeRead]:
```

**FORBIDDEN, explicitly**, repeating APRAS-40 §5.3 because the pins are the
same: implementing this guard as an in-handler `if not user.is_superuser:
raise …` in order to keep `ADMIN_ONLY_ROUTES` from moving. The three
structural walkers (`test_permission_enforcement.py`, `test_tenant_admin.py`,
`test_tenant_route_scope.py`) discover guards by traversing `route.dependant`;
an inlined check is invisible to all three. The pins move by +1 and are not to
be dodged.

`skip`/`limit` are the tree's convention, in the spelling the two most recent
slices use (`infractions.py:238`, `finance.py:195`):
`Query(default=0, ge=0)` and `Query(default=50, ge=1, le=100)`. An out-of-range
value is FastAPI's **422**, with no handler code.

### 2.3 The classification, and the counts that move

The route carries **no catalogue permission** — the convention
`PATCH /users/{id}/superuser` established and APRAS-39/40 followed for all
nine of their operator routes — so it joins `UNGUARDED_ROUTES` and
`ROUTE_PERMISSIONS` does not move. Concretely it lands in the same class as
its three siblings: **unmapped, superuser-guarded by dependency**, which is
the class of ten routes today (`/plans/` × 4, `/tenants/{id}/modules` × 2,
`/tenants/{id}/subscription*` × 3, `/users/{id}/superuser`), all ten in
`UNGUARDED_ROUTES` **and** in `ADMIN_ONLY_ROUTES`.

**It is deliberately not APRAS-51's form `S`.** Form `S` is *mapped* +
`get_current_superuser` + `P ∈ SUPERUSER_ONLY_PERMISSIONS`; its five members
are the five global `/tenants` writes. Reaching it would require minting a
sixth superuser-only permission (`PERMISSIONS` 174 → 175,
`ROUTE_PERMISSIONS` 201 → 202), which contradicts the sibling mirror, widens
the role editor's vocabulary with a string no role may ever hold, and is
exactly what APRAS-39 §6.4's convention exists to avoid. Consequently the new
route is **outside** `test_permission_alignment.py`'s walk, which iterates
`ROUTE_PERMISSIONS`, and:

* the five form counts stay **53 / 5 / 3 / 5 / 135 = 201**;
* the complement sweep stays **193** cases;
* the new route must **not** be added to `UNENFORCED`, `MEMBERSHIP_GATED`,
  `SERVICE_ENFORCED` or `REFUSAL_SHAPES` — each is asserted to be a subset of
  the mapped routes, so any of those additions is a red test, not an oversight.

| Constant | `e188866` (measured) | after APRAS-51 | after this task |
|---|---|---|---|
| `len(PERMISSIONS)` | 174 | 174 | **174** (unchanged) |
| `len(ROUTE_PERMISSIONS)` | 201 | 201 | **201** (unchanged) |
| `len(UNGUARDED_ROUTES)` | 22 | 22 | **23** (+1) |
| registry total (`RP + UR`, incl. the root `GET /`) | 223 | 223 | **224** (+1) |
| application routes | 223 | 223 | **224** (+1) |
| `ADMIN_ONLY_ROUTES` (`test_permission_enforcement.py`) | 15 | 15 | **16** (+1) |
| `ADMIN_ONLY_ROUTES` (`test_tenant_admin.py`, independent copy) | 15 | 15 | **16** (+1) |
| `GLOBAL_ROUTES` (`test_tenant_route_scope.py`) | 27 | 27 | **28** (+1) |
| D / S / M / E / H (`test_permission_alignment.py`) | — | 53/5/3/5/135 | **unchanged** |
| swept routes (`test_permission_alignment.py`) | — | 193 | **unchanged** |
| `EXPECTED_CELL_COUNT` / `len(load_union())` | 1206 | 1206 | **1206** (unchanged) |
| baseline files under `tests/data/` | 3 | 4 | **4**, all byte-identical |
| `REQUEST_BODIES` / `EXPECTED_REQUEST_BODY_COUNT` | — | — | **unchanged** (a `GET`, and unmapped) |

Every literal below must be edited, with a one-line reason each, or the suite
is red (these are the exact sites, measured):

* `tests/test_permission_registry.py:165-166` — rename
  `test_unguarded_allowlist_is_twenty_two_routes` → `…_twenty_three_routes`,
  `== 22` → `== 23`; `:193-196` — `== 22` → `== 23`, `total - 22` →
  `total - 23`; the docstring's `205/183/22 → 223/201/22` narrative gains
  `→ 224/201/23`;
* `tests/test_permission_parity_matrix.py:468,480` — rename
  `test_the_twenty_two_unguarded_routes_are_the_only_ones_excluded` →
  `…_twenty_three_…`, `== 22` → `== 23`, and one sentence in its docstring:
  *"APRAS-52 grows this list by one — the operator-side history read — and by
  zero cells, for the same reason as APRAS-40's nine: it maps to no catalogue
  permission."*;
* `tests/test_permission_enforcement.py:120-157` — the `ADMIN_ONLY_ROUTES`
  literal gains the key; `:309,317,326` — rename
  `test_get_current_superuser_is_exactly_the_fifteen_operator_routes` →
  `…_sixteen_…`, `== 15` → `== 16`;
* `tests/test_tenant_admin.py:709-808` — the independent copy, same three
  edits. It stays an independent copy: the duplication is deliberate;
* `tests/test_tenant_route_scope.py:25-…` — the `GLOBAL_ROUTES` literal gains
  the key, in the APRAS-40 comment block; `:135` — `== 27` → `== 28`;
* `tests/test_superuser_grant.py:296,328` and
  `tests/test_tenant_modules_api.py:406-407` — the same two constants,
  asserted again in two more modules; `22 → 23`, `27 → 28`.

## 3. Backend

### 3.1 Service — `app/services/subscription_service.py`

`list_history` today takes a `Tenant`, returns **every** row and resolves plan
and author names. Two changes, both minimal:

```python
@classmethod
def list_history(
    cls, *, session: Session, tenant: Tenant,
    skip: int = 0, limit: int | None = None,
) -> list[SubscriptionChangeRead]:
```

* `limit=None` means *no `LIMIT`*, so the tenant-side route
  (`GET /api/v1/subscription/history`) keeps today's behaviour **byte for
  byte** and its call site is not edited;
* the `order_by` gains a deterministic tiebreak —
  `.order_by(SubscriptionChange.changed_at.desc(), SubscriptionChange.id.desc())`.
  Without it, two rows written in one call (a courtesy grant plus its revoke)
  can share a `changed_at` and page unstably. Checked: no existing test
  depends on the tie order — `test_a_grant_and_a_revoke_in_one_call_append_one_row_each`
  compares `sorted(kinds)`, and
  `test_history_is_ordered_newest_first_and_names_the_actor` uses two
  separate requests;
* `skip`/`limit` are applied in **SQL** (`.offset(...).limit(...)`), not by
  slicing a fully materialised list, so the name-resolution loops stay O(page).

and the operator-side entry point, mirroring `read_for_tenant` line for line:

```python
@classmethod
def list_history_for_tenant(
    cls, *, session: Session, tenant_id: UUID, skip: int = 0, limit: int = 50,
) -> list[SubscriptionChangeRead]:
    """The same rows `GET /api/v1/subscription/history` returns, named by path."""
    return cls.list_history(
        session=session, tenant=cls._get_tenant(session, tenant_id),
        skip=skip, limit=limit,
    )
```

`_get_tenant` raises `TenantNotFoundError` → **404** through the existing
global handler, which is where ER-1's "404 for an unknown tenant" comes from —
no new error class, no new handler, and the same status the sibling
`GET /{tenant_id}/subscription` gives.

**Why the tenant filter is safe at global scope**, stated so review does not
have to rediscover it: `TenantSubscription` is directly scoped, but the
`tenants` router is `GLOBAL_SCOPED`, so `acting_tenant_id(session) is None`
and the ambient filter does not apply — the explicit
`where(TenantSubscription.tenant_id == tenant_id)` in `get_subscription` is
the whole of the scoping, exactly as for `read_for_tenant` today.
`SubscriptionChange` carries no `tenant_id` and is reached only through its
parent's id, so cross-tenant leakage is structurally impossible.

### 3.2 Route — `app/api/v1/endpoints/tenants.py`

The signature of §2.2, a docstring naming the sibling block, and one line:

```python
return SubscriptionService.list_history_for_tenant(
    session=session, tenant_id=tenant_id, skip=skip, limit=limit
)
```

### 3.3 Schema

**`SubscriptionChangeRead` is reused unchanged.** It already carries `kind`
(the five `SubscriptionChangeKind` values), `modules_added`,
`modules_removed`, `from_plan_name`, `to_plan_name`, `reason`,
`changed_by_id`, `changed_by_name` and `changed_at` — i.e. every field ER-1
asks for: author, type, affected modules and notes. No new schema class, no
envelope: the response is a bare `list[SubscriptionChangeRead]`, like its
tenant-side twin, so the two bodies are comparable cell by cell (§6.1 pins
that they are equal).

### 3.4 Status codes, complete

| Situation | Answer |
|---|---|
| superuser, tenant with history | **200**, newest first, at most `limit` rows |
| superuser, tenant with a subscription but no rows | **200** `[]` |
| superuser, tenant with **no subscription row** | **200** `[]` (APRAS-40 §4.6: adopting billing is opt-in; never a 404) |
| unknown `tenant_id` | **404** (`TenantNotFoundError`) |
| authenticated non-superuser, including a `tenant_admin` of that very tenant | **403** (`get_current_superuser`) |
| unauthenticated | **401** |
| `skip < 0` or `limit` outside `1..100` | **422** |

The 404-vs-403 ordering matches the siblings: the superuser dependency is
solved before the handler runs, so a non-superuser naming an unknown tenant
gets **403**, not 404.

## 4. Parity accounting (ER-3) — the honest answer

ER-3 offers a choice between "an additive baseline of its own" and "a
documented re-record of `_40`". **Neither is possible, and neither is
needed**, because the parity matrix measures exactly `ROUTE_PERMISSIONS`,
which this task does not move. The evidence, measured rather than argued:

1. `test_permission_parity_matrix.py:462-465` —
   `{(method, path) for _role, method, path in CELLS} == set(ROUTE_PERMISSIONS)`,
   an **exact set**, plus `len(CELLS) == len(PARITY_PROFILES) * len(ROUTE_PERMISSIONS)`;
2. `record_parity_baseline.select_cells` filters that same `CELLS` list, and
   `test_the_recorder_scopes_by_route_and_validates_the_merge_base` pins that
   an unknown route is `SystemExit(2)`. **The committed recorder — the only
   sanctioned producer, named in every `_meta.generator` — physically cannot
   record a route that is not in `ROUTE_PERMISSIONS`.** A hand-written
   `parity_matrix_baseline_52.json` would have no reproducible provenance,
   which is the one property the whole baseline mechanism exists to have;
3. `test_the_three_baselines_partition_route_permissions_exactly` asserts
   `f2 | forty | forty_four == set(ROUTE_PERMISSIONS)`. A fifth file naming an
   unmapped route would break that equality, and APRAS-51 extends rather than
   relaxes this test.

So the parity contract of this task is, in full:

* **no new cells.** `EXPECTED_CELL_COUNT` stays 1206, no `APRAS_52_CELL_COUNT`
  addend is introduced, and no baseline file is created;
* **all four baseline files stay byte-identical** —
  `parity_matrix_baseline.json` (F2, sha pinned by `F2_BASELINE_SHA256`),
  `_40`, `_44` and APRAS-51's `_51`. Asserted by the existing sha/`_meta`
  cases, which must pass unmodified;
* **the accounting that does move is the exclusion ledger**:
  `test_the_twenty_two_unguarded_routes_are_the_only_ones_excluded` becomes
  `…twenty_three…` with the one-sentence reason of §2.3. That test is
  precisely "no cell may be dropped for any reason other than being
  unguarded", i.e. it *is* the matrix's accounting for a route like this one.

**The six cells, kept as a test rather than as a file.** The board's "six
cells" is a real requirement — the six legacy profiles must be shown to be
refused — and it survives as a parametrised assertion instead of a JSON
artefact (§6.1's `test_the_history_route_refuses_the_six_legacy_profiles`).
It is strictly stronger than a recorded 403 would be: a recorded cell is a
number in a file, while this issues six real requests and pins the answer.

## 5. Frontend

### 5.1 API — `src/api/plans.ts`

```ts
export const getTenantSubscriptionHistory = async (
  tenantId: string, skip: number, limit: number,
): Promise<SubscriptionChange[]> => {
  const response = await apiClient.get<SubscriptionChange[]>(
    `/tenants/${tenantId}/subscription/history`,
    { params: { skip, limit } },
  );
  return response.data;
};
```

Path written exactly as FastAPI mounts it, **no trailing slash** — the module
docstring already explains why (a mismatch is a 307 and a 307 drops headers).
`SubscriptionChange` already exists in `src/types/subscription.ts` and needs
no field: the operator body is the tenant body.

### 5.2 Hook — `src/hooks/usePlans.ts`

```ts
export const useTenantSubscriptionHistory = (
  tenantId: string | null, skip: number, limit: number,
) =>
  useQuery({
    queryKey: ["tenants", tenantId, "subscription", "history", skip, limit],
    enabled: !!tenantId,
    queryFn: () => getTenantSubscriptionHistory(tenantId as string, skip, limit),
  });
```

The key starts with `"tenants"`, so `setActingTenant`'s eviction sweep
(`queryKey[0] !== "tenants"`) **preserves** it — correct, and the same reason
`useTenantSubscription` is keyed that way: this is data named by an explicit
tenant id, not acting-tenant data.

**`useSetTenantPlan` and `useSetTenantCourtesy` gain one invalidation each**:

```ts
void queryClient.invalidateQueries({
  queryKey: ["tenants", tenantId, "subscription", "history"],
});
```

The prefix match invalidates every page. Without it the operator grants a
courtesy and the table below the button keeps showing the pre-grant history —
the exact failure `useSetSubscriptionModules` already guards against on the
tenant side.

### 5.3 The table — `TenantSubscriptionsPage.tsx`

A new `<section>` at the bottom of the `{data && (…)}` block, after the
courtesy section, mirroring `SubscriptionPage.tsx`'s history table so the two
screens do not drift:

* `<h2>` — `t("tenantSubscriptions.historyTitle")`;
* six columns, in this order and with these headers: kind
  (`t("subscription.historyTitle")` as the column header, as on the tenant
  page), `subscription.added`, `subscription.removed`, `subscription.author`,
  `subscription.when`, `subscription.reason`;
* one `<tr key={row.id}>` per row: `t(\`subscription.kind.${row.kind}\`)`,
  `row.modules_added.join(", ")`, `row.modules_removed.join(", ")`,
  `row.changed_by_name`, `row.changed_at`, `row.reason`;
* **empty state**: when the query resolved and `history.length === 0`, a
  `<p>{t("tenantSubscriptions.historyEmpty")}</p>` and **no table**;
* **pagination**: module-level `const HISTORY_PAGE_SIZE = 20;` and a
  `const [historyPage, setHistoryPage] = useState(0)`, with
  `skip = historyPage * HISTORY_PAGE_SIZE`. Two buttons below the table —
  `t("tenantSubscriptions.previous")` (disabled at `historyPage === 0`) and
  `t("tenantSubscriptions.next")` (disabled when
  `history.length < HISTORY_PAGE_SIZE`, the last-page signal a bare list
  gives) — plus `t("tenantSubscriptions.page", { page: historyPage + 1 })`.
  There is deliberately **no total count**: adding one means a second query
  and a `{items, total}` envelope on a route whose twin returns a bare list;
* `setHistoryPage(0)` is called in the tenant `<select>`'s `onChange`, beside
  the existing `setCourtesyEdits({})` / `setReason("")` reset, for the same
  reason: a page number belongs to the tenant it was paged in.

**The page's header comment must be corrected.** Its lines 30-33 currently
say the history lives only on the tenant-side page and that "this task
deliberately adds no fourth [route]". That sentence is now false; it is
replaced by one recording that APRAS-52 added the fourth operator route and
why (APRAS-40 §8.4/§10.3 asked for the table; D10 deferred it).

### 5.4 i18n — both `en.json` and `pt.json`

Five new keys under `tenantSubscriptions.*`, and **no others**:

| Key | en | pt |
|---|---|---|
| `historyTitle` | "Change history" | "Histórico de alterações" |
| `historyEmpty` | "No changes yet." | "Nenhuma alteração ainda." |
| `previous` | "Previous" | "Anterior" |
| `next` | "Next" | "Próxima" |
| `page` | "Page {{page}}" | "Página {{page}}" |

The column headers and the five kind labels are **reused**, not duplicated:
`subscription.added/removed/author/when/reason` and `subscription.kind.*`
already exist in both files (all five kinds), which is what keeps the two
history tables reading identically. `src/i18n/__tests__/index.test.ts`'s
"identical key sets for en and pt" case must stay green with no edit.

## 6. Tests, by layer

### 6.1 Backend — the route (`tests/test_subscription_admin_api.py`)

Built on `tests/subscription_helpers.py`'s existing vocabulary
(`make_superuser`, `make_tenant_admin`, `make_role_holder`, `make_plan`,
`subscribe`, `auth`), beside the three sibling route modules:

* `test_the_history_route_returns_the_rows_newest_first_with_author_and_kind`
  — a plan change, a courtesy grant and a tenant-side contracting act against
  the same tenant; asserts the three `kind`s in reverse-chronological order,
  `changed_by_name` per row, `modules_added`/`modules_removed`, `reason`, and
  `from_plan_name`/`to_plan_name` on the `PLAN_CHANGE` row;
* `test_the_history_route_paginates_with_skip_and_limit` — ≥ 3 rows;
  `?limit=2` returns the two newest, `?skip=2&limit=2` returns the rest, the
  pages are disjoint, and their concatenation equals the unpaginated read;
* `test_the_history_route_rejects_an_out_of_range_page` — `?skip=-1` and
  `?limit=0` and `?limit=101` are **422**;
* `test_the_history_route_is_empty_for_a_tenant_with_no_subscription` — 200
  `[]`, never 404;
* `test_the_history_route_is_404_for_an_unknown_tenant`;
* `test_the_history_route_shows_only_that_tenants_rows` — two tenants, each
  with its own subscription and rows; neither body contains the other's ids;
* `test_a_tenant_admin_gets_403_on_all_four_routes_including_own_tenant` —
  the existing `…_on_all_three_routes_…` case, extended to four (rename
  included);
* `test_unauthenticated_is_401` — extended with the new URL;
* `test_the_superuser_history_matches_the_tenant_side_history` — the twin of
  the existing `test_the_superuser_read_matches_the_tenant_side_read`: the
  operator body with `limit=100` equals `GET /api/v1/subscription/history`
  read by the same superuser with `X-Tenant-Id`, so the two surfaces cannot
  drift;
* **`test_the_history_route_refuses_the_six_legacy_profiles`** — §4's six
  cells. Parametrised over `matrix_world.PARITY_PROFILES` (imported
  read-only; `matrix_world.py` is not edited and its sha does not move), each
  actor built with `make_role_holder(session, permissions=bundle(profile))`
  from `tests.conftest.bundle`; every one of the six answers **403**. This is
  the assertion that stands in for a parity baseline, and it is named in the
  PR body as such.

### 6.2 Backend — the registry and the walkers

* the eight literal/name edits of §2.3, each of which is itself an assertion;
* `tests/test_permission_registry.py`'s existing "every route is classified"
  case covers the new route with no edit beyond the counts;
* `test_permission_alignment.py` (APRAS-51) is **not edited**: a case is added
  there only if it would otherwise pass vacuously — the correct statement,
  asserted in `tests/test_subscription_history.py`, is
  `test_the_operator_history_route_is_not_permission_mapped`: the key is in
  `UNGUARDED_ROUTES`, absent from `ROUTE_PERMISSIONS`, absent from
  `MEMBERSHIP_GATED`, `SERVICE_ENFORCED` and `REFUSAL_SHAPES`, and present in
  both `ADMIN_ONLY_ROUTES` copies;
* `tests/test_subscription_history.py`'s
  `test_the_history_is_never_updated_or_deleted` passes unchanged and is
  load-bearing here: it forbids any live route with `history` in its path
  whose method is `PATCH`/`PUT`/`DELETE`. The new route is a `GET`, and that
  is the mechanical guarantee that "expose" did not become "edit".

### 6.3 Backend — the service

In `tests/test_subscription_history.py`:

* `test_the_tenant_side_history_is_unpaginated_by_default` — `limit=None`
  still returns every row, so APRAS-40's route is untouched;
* `test_the_history_order_is_deterministic_for_rows_sharing_a_timestamp` —
  two rows written with an identical `changed_at`; two identical reads return
  the same order, and the two pages of a `limit=1` walk are disjoint.

### 6.4 Frontend — `TenantSubscriptionsPage.test.tsx`

The module already mocks `apiClient` and routes by URL; the mock gains
`/tenants/t-1/subscription/history` (and `t-2`). Cases:

* **one per change type**, five of them — `CONTRACTED`, `PLAN_CHANGE`,
  `COURTESY_GRANT`, `COURTESY_REVOKE`, `OVERRIDE` — each asserting the row
  renders the **translated** label from `pt.json`
  (`subscription.kind.<KIND>`), its added/removed modules and its author;
* `renders the empty state when the tenant has no history` — the empty-state
  text is present and no `table` role is rendered;
* `pages with skip and limit` — Next issues a request with
  `{ skip: 20, limit: 20 }`, Previous is disabled on the first page, Next is
  disabled when a short page comes back;
* `resets the history page when the tenant changes` — after paging forward,
  choosing `t-2` re-requests with `skip: 0`;
* `refreshes the history after a courtesy grant` — the `PUT` is followed by a
  refetch of the history key.

## 7. Documentation

`AGENTS.md`, three edits, all mechanical:

1. the endpoint table's `/api/v1/tenants/{id}/subscription` row → `(GET/PUT,
   plus GET /history, superuser only)`;
2. *Assinatura e planos*: one sentence recording the fourth operator route —
   what it returns, that it is superuser-only and maps to no catalogue
   permission, and that it therefore takes `UNGUARDED_ROUTES` to **23** and
   `ADMIN_ONLY_ROUTES` to **16** while `ROUTE_PERMISSIONS`/`PERMISSIONS` stay
   201/174 and all four parity baselines stay byte-identical;
3. *Módulos por tenant*'s parenthetical "(`APRAS-40` then took the registry
   to **183/22**…)" gains "; `APRAS-52` takes it to **201/23**, still with no
   new cell".

`tests/test_docs_agents_md.py` asserts 174/28 and the endpoint table's shape;
both survive. No new doc test is added — the counts it would assert are
already asserted in the registry modules.

## 8. Gates

* `cd backend && TEST_POSTGRES_URL=… SECRET_KEY=test uv run pytest` — whole
  suite green, coverage ≥ 90%. The URL is required:
  `test_migrations_postgres.py` asserts against a live schema and self-skips
  without it (recipes in `AGENTS.md`). **No migration is added, so its case
  count does not move** — a changed count there is a bug in this task.
* `cd backend && uv run ruff check . && uv run ruff format --check .`.
* `cd frontend && npm run lint && npm run build && npm run test` — coverage ≥
  the base run (75% gate).
* i18n: `src/i18n/__tests__/index.test.ts` green with the five new keys
  present in **both** `en.json` and `pt.json` and the key sets identical.
* `git diff` under `backend/alembic/` is **empty**.

## 9. Out of scope

* **A tenant-side history route.** `GET /api/v1/subscription/history` already
  exists (APRAS-40 §5.1) and is not touched, beyond the strictly
  behaviour-preserving default arguments of §3.1.
* **Any migration.** The rows, the table and the indexes
  (`subscription_change.changed_at` is already indexed) exist since `0035`.
* **Export** (CSV/PDF), print view, or any download.
* **Filtering** by kind, author or date range, and **sorting** by anything but
  `changed_at desc`. The pagination control is the whole navigation surface;
  a filter is a follow-up with its own query parameters and its own tests.
* **A total-count envelope** (`{items, total}`) on either history route. §5.3.
* **Any new permission**, any change to `ROUTE_PERMISSIONS`, to
  `get_effective_permissions`, or to the entitlement ceiling. THE RULE of
  APRAS-40 is untouched: `tenant.disabled_modules` remains the only input to
  permission resolution.
* **Re-recording any parity baseline**, editing `tests/matrix_world.py`, or
  touching `legacy_role_bundles.json`. §4.
* **Showing the history on `/admin/modules`.** That page is the raw repair
  lever; the commercial surface is this one.

## 10. The one open question

The board's ER-1 spells the path `/api/v1/subscriptions/{tenant_id}/history`
while this spec mounts it at `/api/v1/tenants/{tenant_id}/subscription/history`
(§2.1), on the reasoning that the dispatch's "mirror the three siblings
exactly" outranks a shorthand and that no `/api/v1/subscriptions` router
exists. If the operator wants the literal path instead, it is a new router
mount plus a `GLOBAL_ROUTES` entry and one string in `permissions.py`,
`plans.ts` and the two walker literals — cheap, but it is a decision, not a
detail, and it should be made before implementation starts rather than at code
review.

## Expected Results

- [ ] **ER-1 — The operator-side history route exists, is superuser-only, and
  is paginated.** `GET /api/v1/tenants/{tenant_id}/subscription/history`
  (§2.1) answers **200** with the tenant's `subscription_change` rows ordered
  `changed_at` **descending** (id descending as tiebreak), each row carrying
  `kind` (one of `CONTRACTED`/`PLAN_CHANGE`/`COURTESY_GRANT`/`COURTESY_REVOKE`/`OVERRIDE`),
  `modules_added`, `modules_removed`, `from_plan_name`/`to_plan_name`,
  `reason`, `changed_by_id` and `changed_by_name`; honours
  `?skip=`(`ge=0`, default 0) and `?limit=`(`ge=1,le=100`, default 50) with
  disjoint pages whose concatenation equals the unpaginated read; answers
  **200 `[]`** for a tenant with no subscription, **404** for an unknown
  tenant, **422** out of range, **403** for every authenticated non-superuser
  including a `tenant_admin` of that very tenant, and **401**
  unauthenticated — each asserted by a named case in
  `backend/tests/test_subscription_admin_api.py`, plus
  `test_the_superuser_history_matches_the_tenant_side_history` proving the
  operator body equals `GET /api/v1/subscription/history` for the same rows.
- [ ] **ER-2 — The superuser page renders the history, with an empty state,
  pagination, and one Vitest case per change type.**
  `TenantSubscriptionsPage.tsx` renders a table for the selected tenant with
  the six columns of §5.3 (kind, added, removed, author, when, reason); it
  renders `tenantSubscriptions.historyEmpty` and no table when the history is
  empty; it pages with a 20-row Previous/Next control that resets to page 1
  when the tenant `<select>` changes and re-requests with
  `{skip: 20, limit: 20}` on Next; and the history refetches after a plan or
  courtesy save. `TenantSubscriptionsPage.test.tsx` carries **five** cases,
  one per `SubscriptionChangeKind`, each asserting the translated `pt.json`
  label of that kind renders in its row, plus the empty-state, pagination,
  page-reset and refetch-after-save cases. `en.json` and `pt.json` both gain
  exactly the five `tenantSubscriptions.*` keys of §5.4 and the i18n key-set
  parity case stays green.
- [ ] **ER-3 — The route is registered exactly like its three siblings, and
  no parity cell moves.** The handler declares a real
  `Depends(api_deps.get_current_superuser)` (never an in-handler
  `is_superuser` check) and the key
  `("GET", "/api/v1/tenants/{tenant_id}/subscription/history")` is in
  `UNGUARDED_ROUTES` (22 → **23**), in `GLOBAL_ROUTES` (27 → **28**) and in
  **both** `ADMIN_ONLY_ROUTES` copies (15 → **16**, in
  `test_permission_enforcement.py` and `test_tenant_admin.py`), while
  `ROUTE_PERMISSIONS` stays **201**, `PERMISSIONS` stays **174**, and
  APRAS-51's `test_permission_alignment.py` is unedited with its forms still
  53/5/3/5/135 and its sweep still 193. **No `parity_matrix_baseline_52.json`
  is created and `EXPECTED_CELL_COUNT` stays 1206** — the matrix measures
  exactly `ROUTE_PERMISSIONS` and the committed recorder rejects an unmapped
  route (§4); the accounting update is
  `test_the_twenty_three_unguarded_routes_are_the_only_ones_excluded` (renamed,
  `== 23`) with its stated reason, and the six legacy profiles are pinned
  instead by `test_the_history_route_refuses_the_six_legacy_profiles`, which
  answers **403** for all six. `parity_matrix_baseline.json`, `_40`, `_44`
  and `_51` are byte-identical (existing sha/`_meta` cases pass unmodified)
  and `sha256(backend/tests/matrix_world.py)` is unchanged.
- [ ] **ER-4 — No migration, and every gate green.** `git diff` under
  `backend/alembic/` is empty and `test_migrations_postgres.py`'s case count
  is unchanged; `cd backend && TEST_POSTGRES_URL=… uv run pytest` is green at
  ≥ 90% coverage; `ruff check .` and `ruff format --check .` report no new
  finding; `cd frontend && npm run lint && npm run build && npm run test` are
  green with coverage ≥ the base run; `en.json` and `pt.json` have identical
  key sets; and `AGENTS.md` carries §7's three edits (endpoint table row, the
  *Assinatura e planos* sentence naming 23/16 with 201/174 unchanged, and the
  `201/23` registry note) with `test_docs_agents_md.py` still green.
