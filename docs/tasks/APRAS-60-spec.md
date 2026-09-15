# APRAS-60 — Construction-projects report as printable HTML (one project per page)

## Scope

A report over the acting tenant's construction projects, rendered server-side
as one self-contained printable HTML document, plus the ability to file that
HTML into the Documents module. Modelled verbatim on the assembly-minutes
precedent (`voting_service.render_minutes_html` / `get_minutes_html` /
`save_minutes` / `_find_or_create_minutes_folder`, and the two routes
`get_assembly_minutes` / `save_assembly_minutes` in
`app/api/v1/endpoints/voting.py`): same rendering shape, same
`LocalStorageProvider` + `document_service.create_document` storage path, same
"folder created on demand" behaviour.

**The report is one complete "Obra" sheet per project.** There is no tenant
totals header and no aggregate page: `GET /api/v1/projects/report` renders the
projects of the acting tenant as consecutive full pages, each identical in
structure to the approved mock, with a page break before every page after the
first. `POST /api/v1/projects/report/save` stores the same HTML as a document.
PDF is produced by the browser's Print dialog against the report's print CSS.

The task also adds **two nullable columns** in a single additive Alembic
migration, because the approved layout needs data the schema does not hold
today: `tenant.logo_url` (the masthead logo) and
`construction_project.planned_progress_json` (the contractor's planned
physical-progress curve, which the "previsto até hoje" bar reads).

**Not in scope:** any server-side PDF rendering or new dependency (WeasyPrint,
reportlab, wkhtmltopdf and friends are explicitly refused — Vercel's
serverless runtime cannot carry their native binaries); per-project single
report; report filters (status, date range), scheduling, e-mail delivery; **any
UI for uploading a tenant logo or editing the planned curve** (both new columns
are populated by SQL or by a seed/sync script for now); a Gantt chart, a
numbered-stage timeline or an S-curve chart (the generator contains dead code
for all three; they are not part of the approved report and may appear later on
the web screen, not here); any new permission string in the catalogue; any
change to the Documents module's own routes or ACL semantics.
`backend/scripts/sync_drive_obras.py` is untracked work in progress and **must
not be modified by this task**.

## Approach

### Behavior

**Rendering.** A new `project_report_service` (module-level functions in the
style of `voting_service`'s minutes block, or a `ProjectReportService`) renders
one self-contained HTML document for the acting tenant, in pt-BR, with no
navigation, no links back into the SPA, no script, and no external asset except
the Google Fonts `@import`, the tenant logo URL and the photo URLs already
stored on the rows. Every interpolated user string goes through `html.escape`,
exactly as the minutes renderer does. Dates and times come from
`app.core.clock` (`test_lint_hygiene.py` scans for `datetime.utcnow`,
`datetime.now(` and `date.today(`).

Projects are loaded ordered by `created_at` ascending. Each project renders as
one `div.page`, in this order:

1. **Masthead** (`header.mast`) — the tenant logo on the left
   (`logo_url` of the **acting tenant's** row, resolved as "Tenant scoping"
   below prescribes; when it is `None` the `<img>` is **omitted entirely**
   and the rest of the masthead renders unchanged), and on the right the kicker
   `Obras em foco`, the title `Relatório de Obras` and the line
   `<Mês de AAAA> · gerado em DD/MM/AAAA` (month name in pt-BR, from
   `app.core.clock`).
2. **Hero** (`section.hero.project`) — the kicker `Obra NN • <kind>`, the
   project title, its description, two pills, and the hero card on the right.
   * `NN` is the project's **1-based position in the tenant's project list
     ordered by `created_at`**, zero-padded to two digits (`01`, `02`, …).
   * `kind` is derived from a parenthesised suffix on `title`:
     `"Coberturas e Portaria (Edificação)"` renders title
     `Coberturas e Portaria` and kind `Edificação`. With no such suffix the
     title is used as-is and the kicker is just `Obra NN` (no bullet, no empty
     kind).
   * First pill: the project status label in pt-BR with the gold dot
     (`span.pill > i`). Second pill: `Última atualização DD/MM/AAAA`, taken
     from the **latest `ProjectUpdate.created_at`**, falling back to the
     project's `updated_at` when the project has no updates.
   * Hero card: `cover_photo_url` as the image; when it is `None` a neutral
     placeholder box of the same dimensions renders in its place (no broken
     image, no `None` in the markup). Then `Progresso geral`,
     `<physical_progress_pct rounded to integer>% concluído`, the gradient
     `div.progress` bar filled to that percentage, and the
     `Início / <pct> / Conclusão` label row.
3. **Etapas da obra** (`section.section` with the `Desenvolvimento` kicker) —
   three `div.grp` cards in one `div.groups` row, each a bullet list of
   milestone **titles only**:
   * `Concluídos` — the **last 3** milestones with `MilestoneStatus.DONE`,
     ordered by `completion_date` descending with `display_order` as tiebreak
     (a `None` `completion_date` sorts last);
   * `Em andamento` — **all** milestones with `IN_PROGRESS`, ordered by
     `display_order`;
   * `Próximos passos` — the **first 3** milestones with `NEXT_STEPS`, ordered
     by `display_order`.
   An empty group renders `<p class="none">—</p>`. No numbering, no dates, no
   descriptions, no timeline and no Gantt.
4. **Avanço físico bar** (`div.pv` containing the generator's `one_bar()`
   markup) — a single track comparing *previsto até hoje* with *realizado*:
   * `realizado` = `physical_progress_pct`; `previsto até hoje` = the planned
     curve value defined below;
   * `div.seg.a` (green) spans `0 → min(planned, realized)`;
   * `div.seg.b` spans the gap between the two — **gold** when
     `realized >= planned`, and carrying the extra class `behind` (muted red)
     when `realized < planned`;
   * the rest of the track stays empty, and a `div.mark` tick sits at the
     `planned` position;
   * the two labels are absolutely positioned tags (`div.tag.plan`,
     `div.tag.real`) reading `previsto X%` and `realizado Y%`, both **above**
     the bar by default; when `abs(planned - realized) < 8` (compared on the
     unrounded values) the container gains the class `close` and the
     `previsto` tag gains the class `below`, moving it under the bar while
     `realizado` stays above;
   * `Início` / `Conclusão` at the ends, and the one-line source note
     "Previsto conforme o cronograma físico-financeiro da empreiteira;
     realizado conforme a última medição."
   * **No planned curve** (column `None` or an empty list): the bar renders the
     realized segment only — no `seg.b`, no `mark` — and the `previsto` label
     reads `previsto —`.
5. **Orçamento da obra** (`section.section`, **no kicker**) — a `div.two`
   two-column block: on the left a `div.budget-col` with the rows
   `Orçamento previsto` (the highlighted `budget-row total`), `Executado`,
   `Saldo` (= `total_budget - executed_budget`) and `% executado`, all money
   formatted `R$ 1.200.000,00`; on the right a `div.cyl` with the cylinder SVG
   gauge filled to the **remaining-balance** percentage, the caption
   `Saldo restante <pct>%` and `<saldo> ainda disponíveis do orçamento
   previsto.`
   **Zero budget:** `% executado` and the gauge are defined as `0` when
   `total_budget == 0` — the renderer never divides by zero and never prints
   `NaN`; the gauge renders empty and both texts still read correctly.
6. **Últimos boletins** (`section.section` with the `Acompanhamento visual`
   kicker) — up to the **3 latest** `ProjectUpdate` rows by `created_at`
   descending, each a `div.week` card with the title, the date `DD/MM/AAAA`,
   the body text and up to **3** photos decoded from `photos_json` on the
   right. A `None`/malformed/empty `photos_json` renders no `photo-grid` and
   the text takes the full width. `cost_impact` and the author are **not
   shown**. With no updates at all:
   `<p class="empty">Nenhum boletim publicado.</p>`.
7. **Footer** (`footer.foot`) — the dark navy band with the gold top border:
   `<name of the acting tenant, resolved as in "Tenant scoping"> · Relatório de
   Obras` on the left and
   `Gerado em DD/MM/AAAA HH:MM por <user full name>` on the right.

**Planned progress.** `ConstructionProject` gains a nullable JSON column
`planned_progress_json` holding an ordered list of
`{"month": "YYYY-MM", "pct": float}` points taken from the contractor's
physical-financial schedule (for *Coberturas e Portaria*: `2026-09` 13.2,
`2026-10` 44.9, `2026-11` 61.0, `2026-12` 78.4, `2027-01` 92.1, `2027-02` 99.6,
`2027-03` 100). **"Planned to date" is the `pct` of the latest point whose
`month` is ≤ the current month, and `0` when no point qualifies** (every point
in the future). `None`, an empty list or a malformed payload is treated as *no
curve* (see the bar's no-curve behaviour above) and must not raise. The column
is written by seed/SQL only; there is no API and no UI for it in this task.

**Tenant logo.** `Tenant` gains a nullable `logo_url: str | None`. Same
migration, additive, no backfill, no server default; set by SQL/seed for now.
Neither column adds a table, so the 53-table partition asserted by
`tests/test_tenant_models.py` and `tests/test_migrations_postgres.py` is
unchanged.

**Graceful degradation is a behavioural requirement, not a nicety.** A zero
budget, a `None` date, a `None` cover photo, an empty milestone list, an empty
update list and a `None`/malformed `photos_json` must each render an em-dash,
a placeholder or an omitted element. The rendered string must contain no
`None`, `NaN`, `nan` or `null` token in user-visible positions.

**Visual language and print CSS.** The generator's `CSS` string is ported into
the renderer **as a module-level constant**, adapted only where the data
requires it, and emitted in a single inline `<style>`: the palette
(`--navy:#082f2a`, `--green:#174b40`, `--gold:#c6a04a`, `--cream:#f7f1e5`,
`--line:#ddd1b6`, `--soft:#eee6d7`, `--kicker:#9b7327`), the Google Fonts
`@import` for Playfair Display (headings) and DM Sans (text) with the
`Georgia, serif` / `Arial, sans-serif` fallbacks that keep the document
readable offline, `print-color-adjust: exact`, `@page { size:A4; margin:0 }`,
the `@media print` block, and a **page break before every project page after
the first** (the generator's `.project + .project` rule, adapted to the
one-`div.page`-per-project structure this renderer emits). Dead CSS for the
Gantt, the numbered stage cards, the S-curve and the deadline strip may be
dropped; nothing that the emitted markup uses may be.

**Tenant scoping.** The renderer never takes a `tenant_id` argument. Isolation
comes from two different mechanisms, and the spec names which one covers what,
because `tenant_context._discover_scoped_models()` only builds
`with_loader_criteria` for mapped classes that carry their own `tenant_id`
column:

* `ConstructionProject` **has** `tenant_id`, so an ordinary
  `select(ConstructionProject).order_by(created_at)` is filtered to the acting
  tenant by the ambient criteria (`app/core/tenant_context.py`) with no manual
  `where`.
* `ProjectMilestone` and `ProjectUpdate` **do not** carry `tenant_id` — they are
  *inherited* tables, scoped only through their parent (they are listed as such
  in `tests/test_tenant_models.py:74-75`). A bare `select(ProjectMilestone)` or
  `select(ProjectUpdate)` therefore returns **every** tenant's rows and is
  forbidden here. Milestones and bulletins must be reached through the already
  scoped parent: either the `project.milestones` / `project.updates`
  relationships off the loaded projects, or an explicit
  `where(ProjectMilestone.project_id.in_(<ids of the loaded projects>))` /
  `where(ProjectUpdate.project_id.in_(...))` over those same projects. No query
  in the renderer may reach a milestone or an update by any other route.
* The **acting tenant's own row** (needed for `logo_url` in the masthead and the
  name in the footer) is not covered by either: `tenant` carries no `tenant_id`
  and is never filtered by the ambient criteria, so `select(Tenant).first()`
  would render another condominium's logo and name on a multi-tenant install and
  is forbidden. The renderer resolves it with the established precedent
  (`app/services/document_service.py:74`, `app/services/role_service.py:128`):
  `tenant_id = tenant_context.acting_tenant_id(session) or DEFAULT_TENANT_ID`,
  then `session.get(Tenant, tenant_id)`. A `None` result (no such row) degrades
  like a `None` `logo_url`: no `<img>`, and an empty tenant name in the footer
  rather than a raised error.

**Saving.** `save_report` answers with exactly one authorization outcome for a
given caller, never a state-dependent one, and it performs **no side effect
before that answer**. Its first statement is an explicit `documents:create`
assertion (`has_permission(user, session, "documents:create")` → the same
`ForbiddenError`/403 `document_service._check_admin_or_director` raises),
executed *before* the HTML is rendered, before any file is written and before
the "Obras" folder is looked up or created. Only then does it render the HTML,
write it through `LocalStorageProvider.save_file(payload,
"relatorio-obras.html", "text/html")`, resolve the folder and call
`document_service.create_document` (whose own `documents:create` check then
passes by construction). A refused caller leaves no folder and no file on disk.

The permission set of the save route is exactly `projects:read` +
`documents:create` — **`documents:folder_create` is deliberately not
required**. This is the one point where the task diverges from the minutes
precedent and the divergence is required: `_find_or_create_minutes_folder`
calls `document_service.create_folder`, which opens with
`_check_admin_or_director(user, session, "documents:folder_create")`
(`app/services/document_service.py:168`), so a caller holding only the two
permissions above would get 403 on their first save and 201 on the second —
precisely the state-dependent answer forbidden above, and a frontend button
gated on `documents:create` that fails exactly once. Instead,
`_find_or_create_obras_folder` resolves the fixed root folder with the same
`select(DocumentFolder).where(name == OBRAS_FOLDER_NAME, parent_id == None)`
lookup and, when absent, **constructs the `DocumentFolder` row directly inside
`project_report_service`**, field for field as `create_folder` builds it
(`name=OBRAS_FOLDER_NAME`, a pt-BR `description`, `parent_id=None`,
`allowed_role_ids_json` = every role id of the acting tenant, `created_at` /
`updated_at` from `app.core.clock`), without going through
`document_service.create_folder`. No ACL validation is skipped in substance:
the role ids come from `select(Role)` over the acting tenant, so
`_assert_role_ids_resolve`'s invariant holds by construction. The folder is a
fixed, system-managed container, not operator-authored content, which is why
`documents:create` alone is the right gate for it; the reason goes in the
helper's docstring.

Naming, stated exactly because two readings of "timestamped" disagree:
`LocalStorageProvider.save_file` **discards the filename it is given** and
writes `f"{uuid.uuid4()}{ext}"` (`app/services/storage_service.py:39-64`), so
only the `.html` suffix survives and the returned `file_url` is already unique
per call. Therefore:

* the field that is **guaranteed distinct** between any two saves — including
  two in the same second — is `AssociationDocument.file_url`. This is the field
  a distinctness assertion must use.
* `AssociationDocument.title` is `f"Relatório de Obras — {DD/MM/AAAA HH:MM:SS}"`
  using `app.core.clock` in the project's display timezone (the same `_fmt_*`
  style `voting_service` uses). It is asserted by **format** (regex), not by
  distinctness, since two saves inside the same second legitimately share a
  title.

Returns the `AssociationDocumentRead` the Documents module already returns.

**Routes.** Both are added to the existing projects router and both must be
declared **before** `GET /api/v1/projects/{project_id}`, otherwise FastAPI
matches `report` as a `UUID` path parameter and answers 422. `GET
/api/v1/projects/report` returns `HTMLResponse`; `POST
/api/v1/projects/report/save` returns `AssociationDocumentRead` with 201.
Permission checks follow the in-handler form already used in `projects.py`
(`_require_read_permission` → `ProjectAccessForbiddenError`, 403): the report
route requires `projects:read`; the save route requires `projects:read` **and**
`documents:create` and nothing else.

**Registry.** `ROUTE_PERMISSIONS` gains
`("GET", "/api/v1/projects/report"): "projects:read"` and
`("POST", "/api/v1/projects/report/save"): "documents:create"`, taking it from
201 to 203. No new catalogue permission: `PERMISSIONS` stays at 174.

**Frontend.** `ConstructionTrackerPage` gains two buttons beside its existing
header actions, gated with the page's existing `useEffectivePermissionSet().has`:
"Gerar relatório" (`projects:read`) and "Salvar em Documentos"
(`documents:create`). Generation mirrors the minutes page's auth-carrying
fetch (`apiClient.get(..., { responseType: "text" })`) and then opens the
result in a new tab from an object URL built over a `text/html` Blob — a bare
`window.open` of the API URL would send no token. Saving calls the save
endpoint and surfaces a success / error message in the page's existing feedback
style. New strings go into both `src/i18n/locales/pt.json` and `en.json`.

### Files touched

* `backend/app/models/tenant.py` — `Tenant.logo_url: str | None`, nullable.
* `backend/app/models/project.py` — `ConstructionProject.planned_progress_json`,
  nullable JSON (portable `JSON`, not a Postgres type — the test harness builds
  this schema on SQLite).
* `backend/alembic/versions/0037_add_logo_and_planned_progress.py` — new,
  additive, exactly reversible: two nullable `ADD COLUMN`s, no backfill, no
  server default. (Chains on `0036_add_infraction_tables`; renumber at merge time if another branch lands `0037`
  first.)
* `backend/app/services/project_report_service.py` — new: the ported CSS
  constant, the per-project page renderer (masthead, hero, groups, bar, budget,
  bulletins, footer), the planned-to-date computation, the cylinder SVG, folder
  resolution and `save_report`.
* `backend/app/api/v1/endpoints/projects.py` — the two routes, declared above
  the `/{project_id}` route.
* `backend/app/core/permissions.py` — the two `ROUTE_PERMISSIONS` entries.
* `backend/tests/test_permission_alignment.py` — `EXPECTED_IN_HANDLER_FORM`
  135 → 137 (both routes land in the derived in-handler form; neither joins
  `SERVICE_ENFORCED`, `MEMBERSHIP_GATED` or `REFUSAL_SHAPES`, whose length
  assertion of 2 stays).
* `backend/tests/test_permission_registry.py` / `test_permission_enforcement.py`
  — any route-count constant that names 201.
* `backend/tests/matrix_world.py` — a `REQUEST_BODIES` entry `NO_BODY` for the
  POST route. **This edit invalidates `HARNESS_SHA256` in
  `test_permission_alignment.py`; re-pin it with `shasum -a 256` and say so in
  the commit body.**
* `backend/tests/data/parity_matrix_baseline_60.json` (new, 12 cells = 6
  profiles × 2 routes) + `backend/tests/test_permission_parity_matrix.py`
  (`APRAS_60_CELL_COUNT`, `APRAS_60_ROUTES`, `ADDITIVE_ROUTES`,
  `EXPECTED_CELL_COUNT`, the loader and the partition test). **Justification:**
  `test_the_three_baselines_partition_route_permissions_exactly` asserts
  `f2 | forty | forty_four == set(ROUTE_PERMISSIONS)` exactly, so two new
  mapped routes cannot ship without a fourth additive baseline. The three
  existing files stay **byte-identical** — their pinned sha256 assertions must
  still pass.
* `backend/tests/test_migrations_postgres.py` — the two new columns asserted on
  the live schema; if the module's case count changes, `MIN_CASES` in
  `backend/scripts/assert_no_skips.py` moves with it.
* `backend/tests/test_project_report.py` — new test module (below).
* `frontend/src/api/projects.ts` — `getProjectsReport` (text) and
  `saveProjectsReport`.
* `frontend/src/features/project-management/components/ConstructionTrackerPage.tsx`
  — the two gated buttons and their handlers.
* `frontend/src/features/project-management/__tests__/ConstructionTrackerPage.handlers.test.tsx`
  (or a sibling new file) — the gate and handler tests.
* `frontend/src/i18n/locales/pt.json`, `en.json` — the new strings, same keys
  in both files.

### Test criteria

Backend (`backend/tests/test_project_report.py` unless noted):

1. `GET /api/v1/projects/report` answers 200 with
   `content-type: text/html; charset=utf-8`, and the body contains the title of
   every project of the acting tenant and one `div.page` per project. There is
   **no** tenant totals header: the body contains no aggregate count-per-status
   or total-budget block.
2. Isolation, on a **two-tenant** fixture where the *other* tenant owns a
   project with its own milestones, updates, name and `logo_url`, and one
   request is made as a member of the acting tenant. The body must contain:
   none of the other tenant's project titles, **none of its milestone titles**,
   **none of its update titles, bodies or photo URLs** (these prove milestones
   and bulletins are bounded by the scoped parent, not by a bare `select()`),
   and the other tenant's project must not shift the `Obra NN` numbering.
   Additionally the masthead `<img src>` is the **acting** tenant's `logo_url`
   and never the other tenant's, and the footer carries the **acting** tenant's
   name and never the other tenant's — which fails if the tenant row is
   resolved with `select(Tenant).first()`. Fixture ordering must make that
   failure real: the other tenant is created first, so it is what
   `select(Tenant).first()` would return.
3. Kicker: with three projects created in a known `created_at` order, the
   bodies read `Obra 01`, `Obra 02`, `Obra 03`; a project titled
   `"Coberturas e Portaria (Edificação)"` renders the kicker
   `Obra 01 • Edificação` and the `<h1>` `Coberturas e Portaria`; a project
   with no parenthesised suffix renders `Obra 02` with no bullet and its full
   title.
4. Milestone selection: a project with 5 DONE, 2 IN_PROGRESS and 5 NEXT_STEPS
   milestones renders 3 items in `div.grp.done` (the three most recent by
   `completion_date`), **2** in `div.grp.doing` (all of them) and 3 in
   `div.grp.next` (the first by `display_order`); an empty group renders
   `<p class="none">—</p>`.
5. Planned-to-date: unit tests over the computation — a curve whose latest
   qualifying month is the current month returns that `pct`; a curve whose
   points are all in the future returns `0`; `None`, `[]` and a malformed
   payload are treated as *no curve*.
6. Bar rendering, asserted on the emitted HTML/CSS classes:
   `realized > planned` → a `div.seg.b` **without** `behind`;
   `realized < planned` → `div.seg.b.behind`, with `seg.a` width equal to the
   realized value; `abs(planned - realized) < 8` → the container carries
   `class="one close"` and the plan tag carries `class="tag plan below"`, while
   `realizado` stays above; a difference ≥ 8 → neither `close` nor `below`;
   no curve → the label `previsto —` with no `seg b` and no `div.mark`.
7. Budget block: money formatted `R$ 1.200.000,00`, `Saldo` =
   `total_budget - executed_budget`, and the cylinder gauge filled to the
   remaining-balance percentage. A project with `total_budget = 0` renders 200
   with a `0%` gauge, no `NaN` and no `ZeroDivisionError`.
8. Bulletins: a project with 5 updates renders exactly 3 `div.week` cards, the
   newest first; an update with 5 photos renders exactly 3 `<img>`; an update
   with `photos_json = None` renders no `photo-grid`; a project with no updates
   renders `Nenhum boletim publicado.`; the body contains neither the author
   name nor the `cost_impact` value of any update.
9. Masthead and footer: with the acting tenant's `logo_url = None` the masthead
   contains no `<img>` and the rest still renders; with a URL set, that URL
   appears in the `src`. The footer contains the acting tenant's name and
   `Gerado em DD/MM/AAAA HH:MM por <user full name>`. A unit-level test asserts
   the resolution path itself: with the acting tenant set on the session, the
   renderer reads the row returned by
   `session.get(Tenant, tenant_context.acting_tenant_id(session))`, and with no
   matching row it renders no `<img>` and an empty tenant name instead of
   raising. (The cross-tenant case is criterion 2.)
10. Print behaviour: the body contains `@page`, `size:A4`, `margin:0`, a
    `@media print` block and a page-break rule, and the number of page breaks
    between project pages equals `project_count - 1`. The palette hex values
    and both font families with their `Georgia` / `Arial` fallbacks are present.
11. Degradation: a project with `total_budget=0`, `executed_budget=0`, all
    dates `None`, `cover_photo_url=None`, `planned_progress_json=None`, no
    milestones and no updates renders 200, and the body contains none of
    `>None<`, `None</`, `NaN`, `nan`, `null` in rendered text.
12. `POST /api/v1/projects/report/save` answers 201, creates the "Obras" folder
    on first call only (second call reuses the same `folder_id`), and two calls
    produce two `AssociationDocument` rows whose `file_url` values differ, each
    with a `title` matching
    `r"^Relatório de Obras — \d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}$"`.
13. 403 for a caller without `projects:read` on the report route; 403 for a
    caller holding `projects:read` but not `documents:create` on the save
    route — and that 403 leaves **no** "Obras" folder row and **no** new file
    under the storage provider's base dir (asserted after the refused call).
14. A caller holding `projects:read` + `documents:create` but **not**
    `documents:folder_create` gets 201 on *both* the first call (the one that
    creates the folder) and the second, proving the save route's answer does
    not depend on whether the folder already exists.
15. `tests/test_permission_registry.py`, `tests/test_permission_alignment.py`
    (structural placement + the complement sweep, expecting a plain 403 on both
    new routes) and `tests/test_permission_parity_matrix.py` all pass with the
    new counts, and the three pre-existing parity baselines remain
    byte-identical.
16. `tests/test_migrations_postgres.py` (CI, real Postgres) proves
    `tenant.logo_url` and `construction_project.planned_progress_json` exist and
    are nullable after the Alembic chain, and the migration downgrades cleanly;
    `tests/test_tenant_models.py` still passes with the 53-table partition
    unchanged.
17. `tests/test_lint_hygiene.py` stays green — no new `# noqa` beyond the
    `E711` the folder lookup needs (`parent_id == None`), spelled with its code
    and reason exactly as `voting_service` spells it, and `NOQA_CAP` raised by
    at most one if the count requires it.

Frontend:

18. `ConstructionTrackerPage` renders both buttons for a permission set holding
    `projects:read` + `documents:create`; hides "Gerar relatório" without
    `projects:read` and "Salvar em Documentos" without `documents:create`.
19. Clicking "Gerar relatório" calls the report API and opens a new tab
    (`window.open` spied, object URL created from the returned HTML); clicking
    "Salvar em Documentos" calls the save API and shows the success message.
20. `pt.json` and `en.json` declare the same new keys (the existing i18n parity
    test covers this if present; otherwise assert it in the new test).

Gates: `uv run pytest` with the 90% coverage gate, `uv run ruff check .`,
`uv run ruff format --check .`; `npm run build`/`tsc -b`, `npx vitest run`,
`npm run lint`. `backend/pyproject.toml` and `frontend/package.json` gain **no**
dependency.

## Mock

The operator approved the layout on 2026-09-14. `docs/tasks/APRAS-60-mock.html`
is the **source of truth for structure, content and print behaviour**: one
project sheet with `realizado 22%` ahead of `previsto 13.2%`. The behaviour of
the progress bar in the other cases (realized behind planned → `seg.b.behind`,
muted red; `abs(planned - realized) < 8` → `one close` with `tag plan below`)
is pinned by the renderer's tests rather than by extra mock files. The mock's
photos and logo are inline data URIs standing in for the real
`cover_photo_url`, `photos_json` and `tenant.logo_url` values.

## Expected Results

- [ ] `GET /api/v1/projects/report` answers 200 `text/html` rendering one
      `div.page` per project of the acting tenant, ordered by `created_at`,
      with **no tenant totals header**; a two-tenant test proves another
      tenant's project, **its milestones and its bulletins** never appear, never
      shift the `Obra NN` numbering, and that the masthead logo and footer name
      are the acting tenant's and not the other tenant's (the other tenant is
      created first, so a `select(Tenant).first()` resolution fails the test).
- [ ] Milestones and bulletins are reached only through the tenant-scoped
      parent projects — via the `project.milestones` / `project.updates`
      relationships or an explicit `project_id.in_(<loaded project ids>)` —
      since `ProjectMilestone` and `ProjectUpdate` carry no `tenant_id` and are
      not filtered by `with_loader_criteria`; `project_report_service.py`
      contains no unfiltered `select(ProjectMilestone)` / `select(ProjectUpdate)`.
- [ ] Each page carries the kicker `Obra NN • <kind>` with `NN` the 1-based
      zero-padded position; a title `"X (Edificação)"` renders title `X` and
      kind `Edificação`, and a title with no parenthesised suffix renders
      `Obra NN` with no bullet — asserted by test.
- [ ] The masthead renders the logo from the new nullable `tenant.logo_url` of
      the **acting tenant's** row, resolved as
      `session.get(Tenant, tenant_context.acting_tenant_id(session) or DEFAULT_TENANT_ID)`
      and never as `select(Tenant).first()`; when `logo_url` is `None` — or no
      such row exists — it renders **no `<img>`** and the rest of the masthead
      unchanged.
- [ ] The hero renders the title, description, the status pill with its gold
      dot, the `Última atualização DD/MM/AAAA` pill (latest
      `ProjectUpdate.created_at`, falling back to the project's `updated_at`),
      the cover photo or a placeholder box when `cover_photo_url` is `None`,
      and `Progresso geral` / `<pct>% concluído` with the gradient bar and its
      `Início / <pct> / Conclusão` labels.
- [ ] "Etapas da obra" renders exactly three bullet-list cards — last 3 DONE by
      `completion_date` desc then `display_order`, **all** IN_PROGRESS by
      `display_order`, first 3 NEXT_STEPS by `display_order` — titles only,
      `—` for an empty group, and no timeline, numbering or Gantt anywhere in
      the document.
- [ ] `ConstructionProject.planned_progress_json` (nullable JSON, list of
      `{"month":"YYYY-MM","pct":float}`) exists after the new additive
      migration, and "planned to date" is the `pct` of the latest point whose
      month ≤ the current month, `0` when every point is in the future, with
      `None`/`[]`/malformed treated as *no curve* — each case covered by a test.
- [ ] The single `Avanço físico` bar renders `seg.a` green to
      `min(planned, realized)`, `seg.b` **gold** when `realized >= planned` and
      `seg.b.behind` when `realized < planned`, the labels `previsto X%` /
      `realizado Y%` with the tick above the bar, `class="one close"` +
      `class="tag plan below"` exactly when `abs(planned - realized) < 8`, the
      `Início`/`Conclusão` ends and the source note — and, with no curve, the
      realized segment only with the label `previsto —`, no `seg b` and no
      `mark`.
- [ ] "Orçamento da obra" renders the four left-hand rows (`Orçamento previsto`
      highlighted, `Executado`, `Saldo`, `% executado`) in `R$ 1.200.000,00`
      format plus the cylinder gauge filled to the remaining balance with
      `Saldo restante <pct>%`; a project with `total_budget = 0` renders 200
      with a `0%` gauge, no division by zero and no `NaN`.
- [ ] "Últimos boletins" renders at most 3 update cards (newest first) with
      title, `DD/MM/AAAA`, body and at most 3 photos; an empty photo list
      renders the text full width; neither `cost_impact` nor the author appears
      anywhere; with no updates the section reads `Nenhum boletim publicado.`
- [ ] The footer renders `<acting tenant's name> · Relatório de Obras` (same
      resolution as the masthead) and
      `Gerado em DD/MM/AAAA HH:MM por <user full name>`.
- [ ] The document carries the ported CSS: the seven palette hex values,
      Playfair Display + DM Sans via the Google Fonts `@import` with
      `Georgia`/`Arial` fallbacks, `print-color-adjust: exact`,
      `@page { size:A4; margin:0 }`, a `@media print` block, and exactly
      `project_count - 1` page breaks between project pages — all asserted by
      test.
- [ ] A project with zero budgets, null dates, no cover photo, no curve, no
      milestones and no updates renders 200 and the body contains no visible
      `None`, `NaN` or `null`.
- [ ] `POST /api/v1/projects/report/save` answers 201 returning the created
      document, creates the "Obras" folder only on the first call (the second
      reuses the same `folder_id`), and two calls yield two
      `AssociationDocument` rows with **distinct `file_url`** values, each
      `title` matching `^Relatório de Obras — DD/MM/AAAA HH:MM:SS$`.
- [ ] The save route's permission set is exactly `projects:read` +
      `documents:create`: a caller holding those two but not
      `documents:folder_create` gets 201 on both the folder-creating first call
      and the second, and a caller lacking `documents:create` gets 403 with no
      "Obras" folder row and no file written.
- [ ] `GET /api/v1/projects/report` answers 403 without `projects:read`;
      `POST /api/v1/projects/report/save` answers 403 without
      `documents:create`; both routes are in `ROUTE_PERMISSIONS` (201 → 203),
      `PERMISSIONS` stays 174, and
      `tests/test_permission_alignment.py` + `tests/test_permission_registry.py`
      pass with the re-pinned `HARNESS_SHA256`.
- [ ] The parity matrix passes with a new additive
      `tests/data/parity_matrix_baseline_60.json` (12 cells) while the three
      pre-existing baselines stay byte-identical.
- [ ] The additive migration adds `tenant.logo_url` and
      `construction_project.planned_progress_json` as nullable columns, adds no
      table, downgrades cleanly, and `tests/test_migrations_postgres.py`
      (real Postgres, CI) plus `tests/test_tenant_models.py` pass with the
      53-table partition unchanged.
- [ ] `ConstructionTrackerPage` shows "Gerar relatório" and "Salvar em
      Documentos", each hidden when its permission is absent, with vitest gate
      tests; the generate handler opens a new tab from the token-authenticated
      fetch.
- [ ] No dependency added to `backend/pyproject.toml` or
      `frontend/package.json`; backend pytest + coverage, `ruff check`,
      `ruff format --check`, frontend `tsc -b`, vitest and eslint all green;
      the new strings exist in both `pt.json` and `en.json`.

## Out of Scope

Server-side PDF generation; a logo-upload UI or a planned-curve editor (both
new columns are set by SQL/seed); edits to `backend/scripts/sync_drive_obras.py`;
a Gantt chart, a numbered-stage timeline, an S-curve or a deadline strip;
per-project reports; report filtering or scheduling; e-mail delivery; and any
new catalogue permission.
