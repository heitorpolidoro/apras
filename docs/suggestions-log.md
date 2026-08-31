# Suggestions Log

## [T006] Blog/Feed de Comunicados e Notícias — 2026-08-27 (QA)

- QA finding (non-blocking, pre-existing, out of scope for T006): the frontend global
  Vitest coverage threshold for `functions` (75%, set in `vitest.config.ts`) was already
  failing on `master` before this task started (baseline ~70.99%). Root cause: every
  `frontend/src/api/*.ts` client module (`occurrences.ts`, `documents.ts`, `lots.ts`,
  `visitors.ts`, and now `announcements.ts`) shows 0% function coverage because component
  tests always `vi.mock()` the api layer rather than exercising it directly — a convention
  used consistently since at least T003/T009/T010. Recommend a dedicated follow-up task to
  either add direct unit tests for `api/*.ts` modules or adjust the threshold/exclude list
  to reflect the intended testing boundary (component/integration tests only).

## [T006] Blog/Feed de Comunicados e Notícias — 2026-08-27

- Spec review (round 1, APPROVED): Announcement media uses a dedicated, unmoderated upload
  path distinct from the T004 `MediaAsset` approval pipeline (publishers are already trusted
  Admin/Director roles). Consider a follow-up if a future requirement needs moderation of
  announcement attachments (e.g. multi-publisher orgs) — at that point reusing `MediaAsset`
  with `EntityType.ANNOUNCEMENT` (already reserved in the enum) would be worth revisiting.

## [T005] Controle de Acesso e Integração de Reconhecimento Facial — 2026-08-26

- Spec review (round 1, APPROVED): Consider a dedicated follow-up task for real biometric
  vector extraction / third-party facial-recognition SDK integration once a hardware vendor
  is chosen — T005 intentionally trusts the device's own `resident_id` claim for the
  verification webhook and does not perform actual face matching.

## [APRAS-35] Fix frontend TypeScript errors that break npm run build and the Vite dev app — 2026-08-29

- Group F header arithmetic (spec line 141): "13x TS2741, 22x TS2322" double-counts Group E. Group F's files hold 20 TS2322 (TaskList.test.tsx 13, TaskBoard.test.tsx 7); the remaining 2 belong to Group E. Label typo only — the explicit file/line list is correct.
- Expected result 4 is the only one requiring a live browser and human console inspection. Results 1-3 already prove the build and the absence of MISSING_EXPORT. Consider dropping it as redundant or restating it headlessly.
- Expected result 11's second clause ("the CI run for the PR shows that step passing") is undecidable until a PR exists. The grep half is checkable at any time.
- Expected result 5's command as literally written (`grep -n "str" .../media_asset.ts`) matches ~20 lines, since every `: string` contains `str`. `grep -n "url: str;"` would make the command itself the test.
- src/api/packages.ts:7 imports PackageStatus as a value while using it only in a type position. Legal before and after the const-object conversion — must NOT be "helpfully" converted to `import type`.
- Group E's new badge variants change the rendered output of BudgetVsActualProgressBar and ProjectUpdateFeed (cva previously resolved the unknown variant to no classes). Intended, but a real visual change worth calling out in the PR description.

## [APRAS-36] Raise frontend test coverage above the 75% functions gate — 2026-08-29

- Expected result 2 gives branches zero headroom: baseline is exactly 76.00% and the result demands >= 76%. Loading ten src/api/*.ts modules that v8 has so far only measured as AST-derived empty coverage can shift the branch denominator once they actually execute, so a correct implementation could land at 75.9x and fail a criterion meant only to catch regressions. `branches >= 75.5` would be safer (still far above the configured gate of 70).
- Expected result 9's diff command can pass vacuously: this repo's Meridian commits land on `master` directly, so if the implementation is committed on master, `git diff --name-only master -- frontend/` prints nothing and the "no production source file changed" guard silently passes. Pinning it to the baseline commit (`git diff --name-only 4169bde -- frontend/`) works whether or not a branch is used.
- Spec item 5's arithmetic undershoots expected result 4 for the modal: it estimates ~11 newly covered functions for AuthorizationFormModal.tsx, but 3 + 11 = 14/24 = 58.3%, below the >= 60% required (needs +12, i.e. 15/24). The ConstructionTrackerPage figure (~14 -> 20/32 = 62.5%) is fine.
- The /dashboard-while-unauthenticated smoke case is async too: AuthProvider clears isLoading inside an effect and ProtectedRoute renders a spinner while isLoading, so it needs findBy* just like /reset-password?token=. Spec item 3 calls out the async requirement only for the reset-password form.
- AGENTS.md:102 names the "75% coverage gate". If the optional ratchet raises vitest.config.ts thresholds, that line drifts. Expected result 9 is scoped to frontend/, so updating the root AGENTS.md is permitted — say so explicitly if the ratchet is taken.
- "The gap is exactly 28 more covered functions" treats 1528 as a fixed denominator; it can move slightly once previously-unloaded modules execute under v8. The >= 78% target has enough headroom that it does not matter — wording nit only.
- Expected result 8's "clean" for new files would be sharper as "zero errors and zero warnings", since the baseline it contrasts against is itself a warning count.

## [APRAS-37] Implementar cotação de compras com orçamentos e escolha justificada — 2026-08-30

- Secoes 1/2 exportam so o enum em app/models/__init__.py; adicionar `from .purchase import PurchaseQuote, PurchaseQuoteDecision, PurchaseRequest` (+ __all__) como todo outro modulo de model faz (`from .asset import Asset, InventoryMovement`, linha 10).
- A secao 3 nunca declara o tipo de coluna de `status`; a 0026 usa `sa.String()` para colunas StrEnum (asset.category, asset.condition) — dizer isso explicitamente para ninguem alcancar `sa.Enum()`.
- "Manager editando o proprio pedido apos DECIDED -> 403/409" oferece duas respostas; a secao 6 na verdade resolve separadamente (PUT/DELETE de pedido -> 403 via _assert_can_write_request; mutacoes de orcamento -> 409, freeze checado antes da propriedade). Reescrever como duas afirmacoes.
- `is_lowest_price` em empate: a secao 4 ("igual ao minimo") marca todos os empatados, enquanto o expected result 2 ("apenas no mais barato") le no singular. Acrescentar uma frase sobre empate.
- A regra dos 10 caracteres da justificativa se aplica a strings diferentes de cada lado: backend `min_length=10` na string crua, frontend na string ja aparada — entao "        abc" e barrado pela UI e aceito pela API. Considerar aparar no servidor antes de medir.
- Dar os caminhos de Navbar.tsx (frontend/src/features/user-administration/components/Navbar.tsx, nao src/components/) e de App.tsx.
- Nomear o comando de verificacao do expected result 8: `alembic upgrade head` / `downgrade -1` precisa do Postgres do docker-compose.yml e nao roda contra o engine sqlite dos testes.
- Fora deste spec: AGENTS.md:102 ainda diz que o gate do frontend e 75%, enquanto a config aplica 80/78/76/80 desde a APRAS-36. O spec cita a config viva, que esta correta.

## [APRAS-41] Add Tenant model, multi-tenant user membership, and default-tenant backfill migration — 2026-08-31

- Escrever o campo do model como `Field(default=DEFAULT_TENANT_ID, foreign_key="tenant.id", ondelete="RESTRICT", index=True, nullable=False, sa_column_kwargs={"server_default": sa.text("'00000000-0000-0000-0000-000000000001'")})` para o schema sqlite do create_all() casar com o Postgres; o trecho da secao 1.1 omite ondelete e server_default.
- `access_device.name` continua `unique=True` no model (backend/app/models/access_control.py:23) mas nao-unico no Postgres via 0012 — um unique global nao auditado na 20a tabela direta, que os testes de isolamento da APRAS-42 vao atingir. Decidir explicitamente.
- A assercao de `alembic current` em test_downgrade_removes_tenant_schema precisa de stdout que _run_alembic descarta; usar `SELECT version_num FROM alembic_version` para manter o modulo estritamente aditivo.
- Scope bullet 3 ainda diz "7 global unique constraints"; secao 2.3 e o expected result 5 dizem 8.
- Secao 2.2 diz "Two footnotes" e lista tres bullets.
- Secao 3 passo 5 ainda oferece duas implementacoes de id do backfill; fixar o bulk_insert com id gerado em Python.
- test_tenant_no_behaviour_change.py nao e nomeado no expected result 10 (conteudo coberto pelo 9).
- O inventario "already scoped" da secao 2.3 omite o unique ix_facial_template_resident_id.

## [APRAS-42] Enforce request-scoped tenant resolution and per-tenant query isolation — 2026-08-31

- Secao 9.1 item 1 diz "at least these 28 collection endpoints" mas lista 27 (ER-4 nomeia 26; /api/v1/uploads/photos/pending so aparece na 9.1) — corrigir a conta.
- Secao 4.2 subestima o residuo de relationship-load: user.user_types alimenta get_effective_user_type_ids em toda rota escopada, entao os UserTypes explicitos de um usuario de dois tenants compoem entre tenants na avaliacao de permissao. Tratar como residuo nomeado levado para a APRAS-43.
- Derivar a matriz by-id do ER-6 de app.routes em vez de lista manual.
- Secao 9.1 item 5 hesita num resultado deterministico ("4xx, or the FK is rejected") — fixar o status code.
- Dois nomes para o mesmo helper: use_global_tenant_scope (3.3) vs use_global_scope (4.4).
- Tornar explicita a dependencia global-scope do webhook no mount: a primeira query e select(AccessDevice) e access_device e escopada.
- Adicionar o idioma de paginacao select(func.count()).select_from(<select>.subquery()) a tabela medida da 4.2 (verificado: e filtrado).
- GLOBAL_ROUTES e nome enganoso; o predicado real e "nao depende de get_current_tenant" (contem signup e o webhook).
