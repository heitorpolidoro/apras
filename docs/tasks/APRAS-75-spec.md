# APRAS-75 — Serve a public landing page at `/` to anonymous visitors

Child 2 of the APRAS-69 split (reasoning: `.meridian/reports/APRAS-69-backlog-1.md`).
Deliverable 3 of `docs/superpowers/specs/2026-09-21-tenant-onboarding-and-branded-entry-design.md`,
landing half only. Carries APRAS-69's ER-1.

## Scope

`/` stops being wrapped in `ProtectedRoute`. An anonymous visitor gets a new
public `LandingPage`; an authenticated visitor keeps today's behaviour at `/`,
byte-for-byte. The page's **structure**, **concrete copy**, and **UI screen
previews** are all specified here — a minimal header with brand and login link,
hero, an interactive screen preview showcase section ("prints" of system interfaces),
exactly six capability blocks grounded in APRAS's core features (Tasks & Maintenance,
Gatekeeper & Access Control, Occurrences & Infractions, Projects & Finance,
Asset Inventory & Purchases, and Documents & Governance), a repeat-CTA band,
and a footer.

### Concrete copy provided in spec

Following operator revision request `rev-1790214283625`, the landing page copy
and structure have been expanded to showcase more of APRAS's core features and
incorporate rich visual UI previews ("prints de telas"). The concrete text for
all visible slots is provided directly in this spec across both supported locales
(`pt-BR` and `en`). The implementer writes these exact strings into
`frontend/src/i18n/locales/pt.json` and `frontend/src/i18n/locales/en.json` under
the `landing.*` namespace (exactly 48 keys).

`LANDING_COPY_TODO` remains a strict tripwire: a PR that still carries the
marker in any locale value is **not done** (ER-7). The marker test in
`parity.test.ts` is green in the PR that closes this task. The task does not
ship with any marker token and does not weaken or skip the test.

Not covered: the branding endpoint, `/c/<slug>`, the branded login and the
tenant switch (all APRAS-74, which this task is blocked by because both edit
`App.tsx`'s route table and the landing's CTAs link at routes APRAS-74 adds);
white-label theming (APRAS-68); any change to the other 38 routes; any change
to `Navbar` or `AppLayoutContent`; any backend change.

## Approach

### Behavior

1. **The route.** The `/` route in `frontend/src/App.tsx` (lines 441-448,
   `<Route path="/" element={<ProtectedRoute><RootRedirect /></ProtectedRoute>} />`)
   loses its `ProtectedRoute` wrapper and becomes
   `<Route path="/" element={<RootRedirect />} />`. No other route is touched.

2. **The branch lives inside `RootRedirect`** (`App.tsx:65-71`), not around it.
   `RootRedirect` additionally reads `useAuth()`:
   - `isLoading` → the existing `<Spinner />`;
   - `!isAuthenticated` → `<LandingPage />`;
   - authenticated → today's body verbatim: `<Spinner />` while
     `usePermissionSet()` is loading, then `<GeneralDashboardPage />`.

   `usePermissionSet()` is a hook and must still be called unconditionally, at
   the top of the component, before any of the three returns.

3. **No redirect is introduced anywhere.** AGENTS.md's "no route ever bounces a
   caller" invariant holds: no `<Navigate>`, no `navigate()`, no
   `window.location` assignment is added by this task. The anonymous visitor
   stays on `/` and sees the landing; only the CTA, on click, navigates.

4. **Chrome.** `Navbar` returns `null` when `!isAuthenticated` and
   `AppLayoutContent` already omits the sidebar offset on the same condition,
   so the landing renders chrome-free with no change to either file. Do not
   edit them.

5. **Page structure** (`LandingPage`), in DOM order:
   - a top `<header>`: product brand mark/name (`APRAS`) and a login link
     (`<Link to="/login">`);
   - a hero `<section>`: feature badge, product headline (`<h1>`), sub-headline,
     primary CTA link (`<Link to="/login">`), and secondary link anchoring to previews;
   - an interactive UI previews showcase `<section data-testid="landing-previews">`:
     heading (`<h2>`), sub-headline, tab navigation bar for 4 interactive screen
     previews ("prints de telas"), and responsive container rendering realistic
     mock UI window components styled with Tailwind:
     1. Tasks & Maintenance (Kanban card with priority, status, assignee, and audit trail snippet)
     2. Gatekeeper & Access Control (QR code scanner check-in badge with visitor & unit info)
     3. Occurrences & Infractions (Incident report card with status stage, photos, and defense deadline)
     4. Projects, Works & Finance (Renovation progress tracker with budget breakdown and milestone)
   - **exactly six** capability blocks, each a heading (`<h2>`) plus one short
     paragraph and a Lucide icon, all six inside a single
     `<section data-testid="landing-capabilities">`:
     1. Tasks & Maintenance (icon: `clipboard-list`)
     2. Gatekeeper & Access Control (icon: `shield-check`)
     3. Occurrences & Infractions (icon: `alert-circle`)
     4. Projects, Works & Finance (icon: `hard-hat`)
     5. Asset Inventory & Purchases (icon: `wallet`)
     6. Documents & Governance (icon: `file-text`)
   - a repeat-CTA band below that section, whose heading **is an `<h2>`** and
     is deliberately **outside** `landing-capabilities`, accompanied by a
     `<Link to="/login">`;
   - a footer (`<footer>`) with copyright / info text and brand mark.

   Semantics are load-bearing for the tests: one `<h1>` in the hero, one `<h2>`
   in the UI previews section, one `<h2>` per capability block inside
   `landing-capabilities` (exactly six), one `<h2>` in the repeat-CTA band,
   and `<footer>` for the footer. The page therefore contains eight `<h2>`
   elements in total, but **exactly six within `[data-testid="landing-capabilities"]`**
   — every capability assertion is scoped to that section
   (`within(screen.getByTestId("landing-capabilities"))`), never to the document.
   The page is responsive (single column below `md`) and uses the existing
   Tailwind/shadcn tokens (`bg-background`, `text-foreground`, `--primary`,
   `--muted-foreground`, `--border`) — no new colour literals, so APRAS-68's
   runtime theme override applies to it for free.

6. **Copy and i18n keys.** Every visible string comes from `useTranslation()`
   under a new `landing.*` namespace in both `src/i18n/locales/pt.json` and
   `src/i18n/locales/en.json`. The keys and translations are specified below:

   | Key | Portuguese (`pt.json`) | English (`en.json`) |
   |---|---|---|
   | `landing.brand` | `APRAS` | `APRAS` |
   | `landing.loginButton` | `Entrar` | `Sign in` |
   | `landing.hero.badge` | `Plataforma Integrada de Gestão Condominial` | `Integrated Condominium Management Platform` |
   | `landing.hero.title` | `Gestão inteligente e transparente para condomínios e associações` | `Smart and transparent management for condominiums and HOAs` |
   | `landing.hero.subtitle` | `Centralize tarefas operacionais, portaria, ocorrências, obras e prestação de contas em uma plataforma moderna, segura e com auditoria completa.` | `Centralize operational tasks, access control, occurrences, projects, and accountability in a modern, secure platform with complete audit trails.` |
   | `landing.hero.cta` | `Acessar o sistema` | `Access the system` |
   | `landing.hero.secondaryCta` | `Ver demonstração` | `View demo` |
   | `landing.capabilities.tasks.title` | `Gestão de Tarefas e Manutenção` | `Task & Maintenance Management` |
   | `landing.capabilities.tasks.description` | `Acompanhe manutenções preventivas e rotinas operacionais com prioridades, prazos e histórico de auditoria.` | `Track preventative maintenance and operational routines with priorities, deadlines, and audit trails.` |
   | `landing.capabilities.access.title` | `Portaria e Controle de Acesso` | `Gatekeeper & Access Control` |
   | `landing.capabilities.access.description` | `Autorização de visitantes com QR code, controle de portaria, encomendas e permissões personalizadas.` | `Visitor authorization with QR codes, gate control, package logging, and custom permissions.` |
   | `landing.capabilities.infractions.title` | `Ocorrências e Notificações` | `Occurrences & Infractions` |
   | `landing.capabilities.infractions.description` | `Registre incidentes com evidências fotográficas, emita notificações automáticas e gerencie prazos e reincidências.` | `Log incidents with photo evidence, issue automated notices, and manage defense deadlines and recidivism.` |
   | `landing.capabilities.finance.title` | `Obras, Projetos e Finanças` | `Projects, Works & Finance` |
   | `landing.capabilities.finance.description` | `Acompanhe cronogramas de reformas, aprove orçamentos e monitore despesas e rateios com total transparência.` | `Track renovation timelines, approve budgets, and monitor expenses and cost-sharing with total transparency.` |
   | `landing.capabilities.purchases.title` | `Patrimônio e Compras` | `Asset Inventory & Purchases` |
   | `landing.capabilities.purchases.description` | `Inventário digital de bens e comparativo de orçamentos item a item entre diferentes fornecedores.` | `Digital asset inventory and itemized quote comparisons between multiple suppliers.` |
   | `landing.capabilities.documents.title` | `Documentos e Governança` | `Documents & Governance` |
   | `landing.capabilities.documents.description` | `Atas de assembleia, convenções e relatórios financeiros centralizados com busca rápida para moradores e conselho.` | `Meeting minutes, bylaws, and financial reports centralized with quick search for residents and board.` |
   | `landing.previews.badge` | `Telas do Sistema` | `System Screens` |
   | `landing.previews.title` | `Interface intuitiva para cada momento da gestão` | `Intuitive interface for every management routine` |
   | `landing.previews.subtitle` | `Veja como o APRAS simplifica a rotina operacional do síndico, da equipe de portaria e dos moradores.` | `See how APRAS simplifies daily operations for managers, gatekeeper staff, and residents.` |
   | `landing.previews.tabTasks` | `Tarefas & Manutenção` | `Tasks & Maintenance` |
   | `landing.previews.tabAccess` | `Portaria & Acesso` | `Gatekeeper & Access` |
   | `landing.previews.tabInfractions` | `Ocorrências & Livro` | `Occurrences & Logbook` |
   | `landing.previews.tabFinance` | `Obras & Projetos` | `Works & Projects` |
   | `landing.previews.tasks.cardTitle` | `Manutenção Preventiva — Elevador Social Bloco A` | `Preventative Maintenance — Passenger Elevator Tower A` |
   | `landing.previews.tasks.status` | `Em Andamento` | `In Progress` |
   | `landing.previews.tasks.priority` | `Prioridade Alta` | `High Priority` |
   | `landing.previews.tasks.dueDate` | `Vencimento: Amanhã às 14:00` | `Due: Tomorrow at 2:00 PM` |
   | `landing.previews.tasks.audit` | `3 alterações registradas no histórico de auditoria` | `3 changes logged in the audit trail` |
   | `landing.previews.access.cardTitle` | `Liberação de Acesso por QR Code` | `QR Code Access Authorization` |
   | `landing.previews.access.visitor` | `Carlos Eduardo (Técnico de Fibra Óptica)` | `Carlos Eduardo (Fiber Optic Technician)` |
   | `landing.previews.access.unit` | `Unidade: Apto 402 — Bloco B` | `Unit: Apt 402 — Tower B` |
   | `landing.previews.access.status` | `Autorizado pelo morador via app` | `Authorized by resident via app` |
   | `landing.previews.access.time` | `Entrada autorizada até 18:00` | `Access authorized until 6:00 PM` |
   | `landing.previews.infractions.cardTitle` | `Ocorrência #1042 — Vazamento em Vaga de Garagem` | `Occurrence #1042 — Water Leak in Parking Space` |
   | `landing.previews.infractions.unit` | `Local: Subsolo 1 — Vaga 45 (Unidade 301)` | `Location: Basement 1 — Spot 45 (Unit 301)` |
   | `landing.previews.infractions.status` | `Notificação Emitida com Fotos` | `Notification Issued with Photos` |
   | `landing.previews.infractions.deadline` | `Prazo de manifestação: 5 dias úteis` | `Response deadline: 5 business days` |
   | `landing.previews.infractions.evidence` | `2 fotos e laudo da zeladoria anexados` | `2 photos and inspection report attached` |
   | `landing.previews.finance.cardTitle` | `Reforma da Fachada & Impermeabilização` | `Facade Renovation & Waterproofing` |
   | `landing.previews.finance.progress` | `68% concluído — Fase 3: Pintura e Vedação` | `68% completed — Stage 3: Painting and Sealing` |
   | `landing.previews.finance.budget` | `Orçamento aprovado em assembleia: R$ 210.000` | `Assembly-approved budget: R$ 210,000` |
   | `landing.previews.finance.milestone` | `Próxima vistoria técnica agendada para 05/10` | `Next technical inspection scheduled for Oct 5` |
   | `landing.ctaBand.title` | `Pronto para simplificar a administração do seu condomínio?` | `Ready to simplify your condominium management?` |
   | `landing.ctaBand.cta` | `Entrar no APRAS` | `Sign in to APRAS` |
   | `landing.footer.text` | `APRAS — Aplicativo de Planejamento e Resoluções para Associações e Síndicos. Todos os direitos reservados.` | `APRAS — Planning and Resolution Application for Associations and Managers. All rights reserved.` |

   There are **exactly 48 keys** under `landing.*`. No hard-coded user-visible
   string in the TSX.

7. **Locale parity and marker assertion.** A test in
   `frontend/src/i18n/__tests__/parity.test.ts` asserts:
   - (a) **negative** — no value in either locale file contains `LANDING_COPY_TODO`;
   - (b) **positive** — the flattened `landing.*` key set is non-empty, contains
     exactly 48 keys, and is identical in `pt.json` and `en.json`.
   Skipping this test is forbidden.

### Files touched

- `frontend/src/App.tsx` — drop `ProtectedRoute` from the `/` route only; add
  the `useAuth()` branch and the `LandingPage` import inside `RootRedirect`.
- `frontend/src/features/public-site/pages/LandingPage.tsx` — new; the page
  described above. `frontend/src/features/public-site/` is the agreed
  directory name for anonymous-facing screens; if APRAS-74 landed first it must
  already exist — reuse it, and do not mint a second public directory under
  another name.
- `frontend/src/i18n/locales/pt.json` — add `landing` namespace with the 48
  Portuguese keys and strings.
- `frontend/src/i18n/locales/en.json` — add `landing` namespace with the 48
  English keys and strings.
- `frontend/src/__tests__/RootRedirect.test.tsx` — the file holds **four**
  cases today (lines 63, 79, 88, 99), all four authenticated: three dashboard
  cases and "holds a spinner while the query is still settling", which is a
  `usePermissionSet()` loading case (`useMyPermissions` → `isPending: true`,
  `useAuth` → `isAuthenticated: true`). **All four stay exactly as they are
  and keep passing.** Two cases are *added*:
  - **anonymous**: `useAuth()` → `{ isAuthenticated: false, isLoading: false }`
    renders the landing;
  - **auth-loading**: `useAuth()` → `{ isLoading: true }` renders the spinner
    and not the landing. This is a *new, distinct* case — it exercises the
    `useAuth` loading branch, not the pre-existing `usePermissionSet` one, and
    must not be folded into or replace the case at line 99.
- `frontend/src/__tests__/AppRouting.smoke.test.tsx` — the case at line 136,
  `it("redirects an unauthenticated visit to / onto the login form", ...)`,
  asserts the behaviour this task deliberately reverses. It is **rewritten,
  not deleted**: same position, renamed to describe the landing, asserting
  `window.location.pathname === "/"`, the landing-exclusive elements
  `screen.getByTestId("landing-capabilities")` and
  `screen.getByTestId("landing-previews")` present, and no login form
  (`screen.queryByLabelText("E-mail")` is null). The sibling cases at line 118
  (`/dashboard`) and line 127 (`/tasks`) are **not touched and must stay green**
  — they are the mechanical proof that only `/` lost its guard.
- `frontend/src/features/public-site/__tests__/LandingPage.test.tsx` — new.
- `frontend/src/i18n/__tests__/parity.test.ts` — add the 48-key parity and
  `LANDING_COPY_TODO` negative assertion.

### Test criteria

- `RootRedirect` with `useAuth()` → `{isAuthenticated: false, isLoading: false}`
  renders the landing (asserted by `getByTestId("landing-capabilities")` and
  `getByTestId("landing-previews")`) and renders neither `GeneralDashboardPage`
  nor any routed destination — proving no redirect.
- `RootRedirect` with `useAuth()` → `{ isLoading: true }` renders the spinner
  (`container.querySelector(".animate-spin")`) and not the landing.
- All **four** pre-existing `RootRedirect` cases (lines 63, 79, 88, 99),
  including the `usePermissionSet` loading case, still pass unmodified.
- `AppRouting.smoke.test.tsx`: the rewritten case at line 136 shows `/`
  unauthenticated rendering the landing with `window.location.pathname === "/"`
  and `screen.getByTestId("landing-capabilities")` present with no login form;
  the `/dashboard` and `/tasks` cases still pass unmodified.
- `LandingPage` renders a top header with brand and login link, exactly one
  `<h1>`, an interactive UI preview section with `[data-testid="landing-previews"]`,
  exactly six `<h2>` elements **within `[data-testid="landing-capabilities"]`**,
  at least one link to `/login`, and a `<footer>`.
- Locale parity: the `landing.*` key set contains exactly 48 keys and is
  identical in pt and en; no value in `pt.json` or `en.json` contains
  `LANDING_COPY_TODO`.

### Gates

No Alembic migration — this task is presentational frontend and stores nothing.
No backend route: `UNGUARDED_ROUTES` and `GLOBAL_ROUTES` are untouched here.
`backend/scripts/assert_no_skips.py` holds `MIN_CASES`, compared by **equality**
in `test_assert_no_skips.py` — it must still match if the case count moves.
Frontend: `tsc -b` clean; vitest coverage thresholds 80 lines / 78 functions /
76 branches / 80 statements; eslint diff-scoped against the baseline of 375
errors + 2 warnings across 64 files.

### Mockup

`docs/tasks/APRAS-75-mock.html`.
It renders the complete proposed Portuguese copy across all sections and states
(anonymous landing with 6 feature blocks and interactive screen previews,
loading spinner, and authenticated dashboard).

## Expected Results

- [ ] Visiting `/` while unauthenticated renders the landing page at URL `/`,
      with no redirect and no login form.
- [ ] Visiting `/` while authenticated still renders `GeneralDashboardPage`,
      after a spinner while the permission set settles.
- [ ] `/` is the only route whose definition changes; no `ProtectedRoute` is
      removed from any other route, and no `<Navigate>` or `navigate()` call is
      added anywhere by this task.
- [ ] `LandingPage` renders a header with brand mark and login link, exactly one
      `<h1>`, a preview section with `[data-testid="landing-previews"]`, exactly
      six `<h2>` elements inside `[data-testid="landing-capabilities"]`
      (the preview section and repeat-CTA band `<h2>` elements sit outside that
      section and are not counted), at least one link to `/login`, and a `<footer>`.
- [ ] `frontend/src/__tests__/AppRouting.smoke.test.tsx`: the `/` case is
      rewritten to assert the landing (via `screen.getByTestId("landing-capabilities")`
      and `screen.getByTestId("landing-previews")`) at `window.location.pathname === "/"`
      with no login form, and the `/dashboard` and `/tasks` unauthenticated redirect
      cases pass unmodified.
- [ ] Every user-visible string on the landing page resolves through
      `useTranslation()` from the `landing.*` namespace, present with an
      identical set of exactly 48 keys in both `pt.json` and `en.json` using the
      copy defined in the spec.
- [ ] A test asserts both that no value in either locale file contains
      `LANDING_COPY_TODO` and that the `landing.*` key set has exactly 48 keys
      and is identical in pt and en, and that test passes.
- [ ] `frontend/src/__tests__/RootRedirect.test.tsx` adds a `useAuth`
      anonymous case and a `useAuth` `isLoading: true` case, and its four
      pre-existing cases (lines 63, 79, 88, 99) pass unmodified.
- [ ] `npx tsc -b` is clean and `npm run test:coverage` passes the 80 lines /
      78 functions / 76 branches / 80 statements thresholds.
- [ ] `npx eslint .` in `frontend/` reports no new violation against the
      baseline of 375 errors + 2 warnings across 64 files.
- [ ] `backend/tests/test_assert_no_skips.py` passes, i.e. `MIN_CASES` still
      equals the collected case count.
- [ ] No Alembic migration is added; `UNGUARDED_ROUTES` and `GLOBAL_ROUTES`
      counts are unchanged by this task.

## Out of Scope

- The public branding endpoint, `/c/<slug>`, the branded login, the tenant
  switch and the no-access panel (APRAS-74).
- White-label theming and `build_theme` (APRAS-68).
- Any change to `Navbar`, `AppLayoutContent`, `ProtectedRoute`, `ROUTE_ACCESS`
  or `NAV_ITEMS`.
- Subdomain-based tenant entry (recorded future study, D2).
