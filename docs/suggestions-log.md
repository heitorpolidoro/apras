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

## [APRAS-43] Add tenant_admin capability composed with the existing RBAC layers — 2026-08-31

- ER-17 armazenado enfraquece o "ruff check is clean" do spec para "clean nos arquivos tocados"; mantido o mais fraco de propósito (o repo carrega ~1200 findings pre-existentes e o CI nao roda ruff) - alinhar o SPEC ao ER, nao o contrario.
- test_migrations_postgres.py:302 (test_downgrade_is_a_safe_noop) tem um segundo downgrade -1 com docstring ja obsoleta; continua verde com a 0029 em cima, mas fixar o alvo remove o proximo drift.
- O "small helper" da secao 6.2 que filtra UserRead.user_types pelo tenant ativo nao tem lar na lista de arquivos da 8.1 - nomear.
- Acrescentar um ER para o caso header-less em formato de producao (membro unico do tenant default ve a mesma lista GET /users/ do master); hoje so implicito em "test_user_admin.py passes unmodified".
- Levar a nota da regra 3 da 6.3 ("per-tenant roles are not in this chain") verbatim para a tarefa seguinte.
- (rodada 1) TenantMemberCreate.is_tenant_admin sem ER proprio; ER-3 chama GET /users/ de "admin-gated" mas e aberto a autenticados; piso de cobertura 90% esta 8pt abaixo do baseline 98.21%; ensure_role_types e o item sem acoplamento causal com o resto da fatia.
- (rodada 1) Racional da regra 4 da 6.3 contradito pelo codigo: signup sempre vincula ao DEFAULT_TENANT_ID e nao ha fluxo de convite, entao todo morador fora do tenant default e permanentemente dual-membership e imutavel pelo proprio sindico - regra segura, mas metade da capacidade fica inerte fora do default; corrigir o racional e nomear o follow-up.

## [APRAS-38] Integrate multi-tenancy end to end: tenant switcher UI — 2026-09-01

- O sentinel do terceiro caso do TenantBootstrapOrder precisa de mecanismo definido: segundo mock (TaskDashboard), texto do proprio TaskDashboard, ou window.location.pathname - os tres dao o mesmo veredito; nomear um.
- Dizer o que o mock do ER-18 responde para /users/ (o branch de erro do AdminUserDashboard so renderiza admin.errorLoadingUsers) e o que /user-types/ devolve no segundo caso do ER-17 com tenant nao-nulo (precisa carregar a linha que concede tasks).
- O mock do ER-18 responde /tenants com A e B para fixture de membership unica - estado que o backend real nao produz; inofensivo, mas renderiza switcher de 2 opcoes para usuario de 1 tenant.
- O frontend nao estende a isencao do menu-gate ao tenant_admin (useMenuAccess so curto-circuita ADMINISTRATOR); comportamento igual ao de hoje e a experiencia /admin/users fica intacta, mas e um follow-up nomeado - a cadeia IAM (F4) resolve por definicao (menus derivam de permissoes).
- (rodada 2) staleTime de 5min pode servir linhas de outra identidade por ate 5 minutos apos login/logout; useActingTenantReady em TenantContext.tsx arrasta o grafo do modulo para useUserTypes; canto 'todas as memberships inativas' da escada sem nome; TenantContextValue.isLoading declarado e nunca consumido.

## [APRAS-45] IAM F1: catálogo de permissões e grupos — 2026-09-01

- O exemplo de partial da 6.5(a) e um TypeError como escrito (User chega posicional; bind session= por keyword colide). Regra correta: bind posicional para args antes do user, keyword so depois. Falha alto e todo reparo da o mesmo conjunto - nao bloqueante.
- '~130 worlds' na 6.5(a) deveria ser ~152 (152 permissoes distintas no catalogo).
- 7.3 deveria pinar o column_default exato do Postgres ('[]'::json) como o precedente da 0029 pina "false".
- 5.2 teste 8 agrupa por primeira tag; ("GET","/") e a unica rota sem tags - agrupar defensivamente.
- Nota opcional no AGENTS.md para o registry (precedente APRAS-43; o 'Nothing else' da secao 2 le como proibindo, embora o ER-6 nao proiba).

## [APRAS-46] IAM F2: enforcement por permissoes com matriz de paridade — 2026-09-01

- 6.3 'sorted diff' le como teste agregador enquanto ER-9 pina caso parametrizado por celula - meia frase resolve.
- NON_ROLE_403 <= 40 sem clausula de desvio (ao contrario de DENIAL_SHAPE_OVERRIDES e PERMITTED_422); aplicar a mesma disciplina 'nomeia no PR body e sobe o literal'.
- Dizer que o engine + outer transaction + create_savepoint mora em matrix_world.py (o recorder script nao usa tmp_path_factory).
- git status --short -uall no ER-8 para nao colapsar diretorios untracked.
- module::function do 8.2 funde metodos homonimos num modulo - parentese (nenhum dos 22 sites afetado).
- (QA da 45) alinhar 'ruff check is clean' com a regra operativa 'touched files must add none'; teste rotulado de baseline drift para total==190; lembrete na F2 de estender _LEGACY_ROLES_BY_PERMISSION ao adicionar permissoes.

## [APRAS-47] IAM F3: is_superuser e is_tenant_admin como atalho — 2026-09-01

- Registrar o lar observado do pin TENANT_ADMIN_PERMISSIONS: na arvore em voo da F2 e test_permission_enforcement.py:393 (modulo ja autorizado); deletar aquele teste nao perde nada (PERMISSION_GUARDED_ROUTES duplicado na l.359).
- O grep -c 'not\*\* grant the domain-service' do ER-9 e frouxo como BRE; parear com grep -in 'does not grant' sobre a secao extraida, enumerado no PR body.
- Tabela 'Files touched' da secao 2 omite a linha condicional de test_permission_registry.py - marcar (conditional - deletion only).
- Nota na secao 0 de que a F2 esta em voo e varios contratos ja confirmados contra a working tree (CONVERTED_COMPARE == 85, split 15/7/8, guards deletadas), mantendo o spec da F2 como contrato.
- (QA) ruff nos 14 arquivos tocados reporta 25 findings, todos pre-existentes em aa8953d (arquivos novos limpos). Dois sao triviais e ja estao em linhas editadas pela F3: `typing.Optional` nao usado em models/user.py e I001 em users.py - dobrar na F5 ou numa tarefa de divida de lint.
- (QA) PR body deve trazer os numeros exatos do ER-8: collected 2241 -> 2270, cobertura 98.443 -> 98.445 %, CONVERTED_COMPARE 85 -> 92, F2_SHA = aa8953d.
- (QA) `_meta.regenerate` da baseline F2 fixa /tmp/apras-parity e /tmp/regen.json - parametrizar quando a F5 regenerar a baseline legitimamente.

## [APRAS-48] IAM F4: UI de grupos e gating por permissao — 2026-09-01

- Tabela de consumidores da 2.7 lista useMenuAccess na linha do effective permission set; ele le identidade simulada e allowed_menus - um parentese evita fiacao errada.
- ER-3 sem caso nomeado na primeira metade; nomear o caso de AdminUserDashboard.test.tsx que a 8.2 ja implica.
- Baselines de cobertura da secao 10 divergem levemente do comentario do ratchet no vitest.config.ts; dizer no PR body qual comando produziu.
- Parametrizar test_me_matches_get_effective_permissions tambem sobre superuser e tenant-admin.
- Atualizar de fato matrix_world.py l.15 ('The ten UNGUARDED_ROUTES') em vez de deixar opcional.
- Revisabilidade: 3 commits limpos dentro do PR (3; 4-5; 6-7).
- (code review) ProtectedRoute.porteiroRouteGating.test.tsx foi reescrito muito alem da linha 'prop rename' do 8.2 (48 casos parametrizados, melhoria) - desvio nao declarado; registrar no PR body.
- (code review) useCanAccess.ts:33 constroi um Set por item de nav (23/render), nao 'um por render' como o 4.3 promete; e o sentinel `?? "tasks"` (l.124/136) passado ao useMenuAccess para as 22 regras sem legacyMenu.
- (code review) routeAccess.ts:72 AUTHENTICATED_ONLY_PATHS e codigo de producao com consumidor so em teste e serve de escape ao invariante 'toda rota tem regra'.
- (code review) MyPermissionsRead.tenant_id (schemas/permission.py:31) sem consumidor no frontend apesar do docstring.
- (code review) test/permissionFixtures.ts e copia exata do mapa do backend hoje, mas nada os mantem em sincronia - gerar do backend ou pinar com um teste que compare ao /permissions.

- (QA) assert_can_grant valida o bundle resultante inteiro: um grupo que ja tem permissao que o editor nao pode conceder fica insalvavel por ele - ate um rename puro da 403 (reproduzido ao vivo). Letra do ER-4 atendida, mas o 6.3 so trocou strip silencioso por beco visivel. F5: validar o delta ou desabilitar Salvar com dica.
- (QA) permissions.errors.cannotGrant em en.json e o prefixo literal da frase do backend - reescrever a copia em ingles.
- (QA) bypass ADMINISTRATOR do useMenuAccess le user.role legado, nao is_superuser: Tasks/Categories somem para superuser cujo role nao e ADMINISTRATOR (backend recusa igual, correto pelo 2.3) - resolver na F5.

## [APRAS-49] IAM F5: rename para role, drop do enum — 2026-09-01

- Acrescentar o rename forward da coluna de ACL como sub-passo numerado no 7.2 (rename -> rewrite -> server_default).
- Heading '14 feature components' do 10.2 esta obsoleto (tabela tem 16); a tabela e o contrato.
- ER-1 da RoleRead sem tenant_id?; 8.1 tem - leitura estrita de campos exaustivos flagraria.
- 11.2 explicita is_superuser nas dez personas mas nao is_tenant_admin (falha alta, nao silenciosa) - uma linha fecha.
- Honrar o split em dois commits (A=rename, B=drop do enum) e dizer no PR body qual e qual.
- Gravar tests/data/legacy_role_bundles.json em commit proprio antes de qualquer delecao - depois desta fatia e a unica declaracao sobrevivente do que o enum significava.
- (da revisao da APRAS-40) 11.1 (~l.1288-1301): expressar 'bundles de legacy_role_bundles.json ∪ NEW_TIER' como fonte de um helper bundle(profile), porque a APRAS-40 divide holds() em bundle()/holds_by_bundle()/holds() com branch de superuser; lookup inlined no call site obriga a 40 a re-dividir.
- (da revisao da APRAS-40) l.90 apaga o 'role framing' de ADMIN_GAP_PERMISSIONS - a constante em si precisa sobreviver a F5 (a 40 le para MATRIX_ADMIN_GAP; ha fallback, clareza e nao bloqueio).

- (code review) 11 virgulas finais soltas deixadas pelo sweep dos kwargs allowed_menus (test_guest_rbac.py:38, test_tasks_coverage.py:27, test_tenant_isolation.py:131, test_task_visible_to_multi_target.py:38,39,111,166,202, test_tasks_rbac.py:210,225, test_tenant_models.py:133) - proximo ruff format expande cada chamada.
- (code review) test_user_admin.py:302: sem caso para payload superset cross-tenant role_ids=[a_role.id, b_role.id] - o unico cujo veredito mudou com o estreitamento S3; pinar.
- (code review) LANDING_PATHS duplicado em RoleDetailPage.tsx:25 vs schemas/role.py:15, com teste assertando copia hardcoded - servir do backend ou pinar contra a API.
- (code review) roles.py PATCH gravava landing_path=NULL quando omitido (corrigido na F5); padrao a vigiar em todo schema Update com default None.

- (QA) greps do ER-3/ER-6 nao ficam literalmente vazios apos word-boundary: document_service.py:52, permissions.py:610, deps.py:203 e comentarios/assercoes de ausencia em testes - nenhum simbolo sobrevive; corrigir a afirmacao no relatorio.
- (QA) ruff COM819 2 -> 17, tudo em backend/tests (virgulas do sweep), --fix-avel; test_tenant_isolation.py tem 4 assercoes mudadas (2 inevitaveis, colunas dropadas) nao registradas nos desvios.
- (QA, pre-existente) PATCH /roles/{id} da 500 em nome duplicado (ix_role_tenant_name) onde POST da 409 - tratar IntegrityError no PATCH.
- (QA) RoleUpdate exige name, entao PATCH so de permissions da 422 - tornar name opcional (sentinel None como os demais).
- (QA, pre-existente) GET /roles/ esta em ROUTE_PERMISSIONS como roles:read mas guardado so por get_current_user - alinhar guard ou mapeamento (candidato a tarefa de divida IAM junto com os itens da F3/F4).

## [APRAS-39] Modularizar features por tenant — 2026-09-01

- S1: ER-7 diz '5 -> 7' flat enquanto vizinhos usam 'predicted'; a 49 pode levar a base a 6 (PATCH superuser) - aplicar o mesmo hedge para 6 -> 8 nao ler como falha.
- S2: dizer que GET /permissions/ fica sem strip (por construcao) e precisa, para o resend do 5.5.
- S3: registrar que has_admin_capability nao esta em nenhum lado do split (le flags, nunca permissao; a 49 o deleta).
- S4: docstring de assert_can_grant fica obsoleta apos o swap - incluir no diff do 5.5.
- S5: 'referenced nowhere else' do ER-4 lido literalmente exclui o def; usar a forma precisa do 12.1.
- S6: snippet do 5.1 reescreve o branch que o spec manda mover verbatim.
- S7: pinar precedencia 404-vs-400 para PUT com tenant e modulo ambos desconhecidos.

- (code review) ProtectedRoute.tsx:122-124: excecao deliberada de optional chaining sem teste - um caso respondendo /permissions/me sem disabled_modules pina e resolve a tensao com o docstring de types/permissions.ts:33.
- (code review) types/permissions.ts:19 landing_path? segue opcional enquanto disabled_modules virou obrigatorio; ambos sempre enviados.
- (code review) useCanAccess.ts:179 ROUTE_ACCESS[path] tipa como AccessRule nunca undefined, mas o terminal /welcome depende do undefined em runtime - explicitar a opcionalidade.
- (code review) RootRedirect.landing.test.tsx: propriedade sem-loop so argumentada em comentario - caso tabelado por persona sobre Object.keys(ROUTE_ACCESS) pina.
- (code review, round 1) developer reportou 0 falhas com 1 falhando (tabela medida antes da ultima edicao) - exigir medicao apos a ultima alteracao no briefing padrao.

- (QA) response_model= omitido nos dois handlers novos (annotation-only, ruff FAST001) deixa o arquivo misto; moduleOfRule le so a primeira entrada de anyOf (seguro hoje, todas single-module); <select> de tenant em /admin/modules sem busca/paginacao; rate limit de login 5/min complica E2E multi-persona.

## [APRAS-40] Área de assinatura com contratação de módulos pelo tenant — 2026-09-01

- 9.2.2 (~l.1360): 'os tres da F2 nao sao editados' contradiz a tabela do 9.2.5 (test_baseline_file_exists muda para F2_CELL_COUNT); dizer 'o par' e nomear os dois.
- 9.2.5 (~l.1845): 'treze casos, nove por uma linha' vs 'oito dos nove' (~l.1810) - alinhar; ER-10 ja escopa a afirmacao aos seis callers de holds().
- 9.2.5 (~l.1810): a forma de linha de test_cell_matches_the_recorded_baseline e `expected = baseline_status(load_baseline(), ...)`, nao `baseline = load_baseline()`.
- 9.1/10.2/12: a string '89 POST/PUT/PATCH routes' vive no comentario `#:` acima de REQUEST_BODIES e no docstring de _NoBody (dois lugares), nao no docstring do modulo.
- can_contract com conjunto ent.managed agora em quatro sites; test_baseline_covers_exactly_the_matrix duplica a assercao de particao - candidato a colapsar na implementacao.

- (code review, lacuna de spec) 8.4/10.3 pedem tabela de historico de assinatura na pagina do superuser, mas 5.3 pina exatamente tres rotas e nenhuma devolve o historico - a pagina foi entregue sem a tabela (D10 aceito); tarefa de follow-up: GET /api/v1/subscriptions/{tenant_id}/history + tabela.

- (code review r2, backlog) .github/workflows/ci.yml nao tem services: - os 45 casos de tests/test_migrations_postgres.py nunca rodam no CI (self-skip sem TEST_POSTGRES_URL); foi assim que B1/B2 da 40 teriam passado verdes. Tarefa: servico Postgres no workflow + TEST_POSTGRES_URL.
- (code review r2) plan_service PATCH so de nome: os ramos else caem no valor armazenado sem validar - S-6 nao tem comportamento observavel; docstrings corrigidas, candidato a simplificar.

- (code review r3) plan_service.py:174-178: os dois guards `if "..." in data` sao inertes (a escopagem nao tem efeito observavel) - simplificar quando o arquivo for tocado; cobertura do backend deve ser citada como faixa (98.52-98.55 %, depende da ordem), nao como ponto.

- (QA) linhas de modulo core em /subscription mostram a dica 'fora do plano' embora a API reporte is_active true / source CORE - ligar ao rotulo subscription.source.CORE (as 5 chaves subscription.source.* estao sem consumidor) resolve os dois.
- (QA) GET /api/v1/subscription/ com barra final e 307 que perde X-Tenant-Id; frontend emite sem barra, mas redirect_slashes=False tornaria estrutural.
- (QA, pre-existente, backlog) GET /api/v1/tasks/ guardado so por get_current_user apesar de ROUTE_PERMISSIONS mapear tasks:read - usuario com zero permissoes efetivas recebeu 200 com o modulo tasks desligado pelo teto. Mesmo padrao do GET /roles/ (APRAS-49 QA): tarefa 'alinhar guard e mapeamento em todas as rotas de ROUTE_PERMISSIONS' com teste que percorra o mapa.
- (QA) ER-10 diz nove call sites de load_union(); a arvore tem dez (a metade contratual - seis callers de holds() - esta exata).

## [APRAS-44] Gestão de infrações com regras e escalonamento por condomínio — 2026-09-02

- 7 diz 'as sete tabelas carregam created_at/updated_at' mas 12.2 afirma que infraction_stage nao tem updated_at (as listas de colunas do 7.2 concordam com 12.2) - alinhar a frase.
- 12.6/8.4/11 escrevem world.infraction / world.lot / world.occurrence.lot_id; MatrixWorld em 4f952b0 so carrega ids (lot_id, resident_id, occurrence_id); o bloco de codigo do 12.6 ja usa a grafia certa.
- 4.5 'nao ha rota page/page_size em lugar nenhum' e exagero: uploads.py:40 declara page; page_size nao existe; skip/limit segue correto.
- Precificacao de acao explicita fora da escada nao declarada (fine_amount de MULTA explicita, defense_due_on de NOTIFICACAO explicita sem passo correspondente) - decidir na implementacao: usar o ultimo passo do mesmo tipo da escada ou exigir os campos no corpo.
- infraction_contestation.stage_id: declarar nulabilidade (7.2); e colisao latente de FK: infraction_stage.infraction_id CASCADE vs infraction_contestation.stage_id RESTRICT.
- test_policy_rejects_non_contiguous_step_order diz '422/400' - unico ou-ou de status no spec; fixar 422.
- InfractionCreate.source_occurrence_id e aceito e ignorado silenciosamente - remover do schema ou validar.
- 7.7(2) usa uma unica string de detail tambem para residente inativo; citacoes de linha do 4.5 derivaram; citacao do AGENTS.md no 7.2 esta abreviada.
- (code review r1-r3) padrao recorrente: hooks/modais entregues sem chamador em producao (usePromoteOccurrence, CycleCloseModal) e testes que mockam a API inteira (api/lots) escondendo um 422 de limite - exigir no briefing do developer um grep de 'sem chamador' por hook/componente novo e ao menos um teste de contrato por client novo que nao mocke a API.
- (QA) NewInfractionModal sem controle de upload de evidencias (10.1 descreve um; API aceita evidence_urls e o detalhe renderiza) e ContestationForm so com corpo (10.1 diz corpo + anexos; attachment_urls faz round-trip) - follow-up: entradas de anexo no cliente reutilizando o padrao de upload existente.
- (QA) mensagem do 409 de regra duplicada le mais estreita que a constraint (tenant, origin, article) - citar a origem.
- (QA) +50 findings ruff nos quatro arquivos de producao novos (FAST001/FAST002/DTZ003/B008/DTZ011, todos com precedente); DTZ003 num modulo de auditoria datada merece revisao.

## [APRAS-50] Testes de migração em Postgres real no CI — 2026-09-06

- 1.2: gemini-scheduled-triage.yml tambem tem push (main / release/**/*, paths-gated) e workflow_dispatch - estreitar a afirmacao para 'nenhum workflow dispara em push para apras-50-proof'.
- 'roughly sixteen' (4.4) e '~16' (3) contradizem o '≈ 17' do proprio 4.4 (17 e o correto).
- 4.1: dizer se os runs de prova precisam ser recapturados apos uma rodada de revisao que altere ci.yml ou o guard.
- Citacao de create_index derivou (l.223-228, nao l.226).
- Higiene do orquestrador: .meridian/reports/ com 125 arquivos vs trim de 50 do pipeline.md.
- (code review) ci.yml:139 `if: always()` tambem dispara em cancelamento (timeout) e o guard imprime 'no JUnit XML' em vez da verdade - `if: !cancelled()` mantem a semantica (spec/ER-2 nomeiam always() literalmente).
- (code review) ci.yml:100 pg_isready responde OK ao servidor bootstrap socket-only do initdb; `-h 127.0.0.1` forca TCP se um dia flakear.
- (code review) test_assert_no_skips.py:152-154 afirma != 0 onde o script devolve exatamente 2 - pinar == 2; `# noqa: S314` sem motivo em assert_no_skips.py:64.
- (code review) sem upload-artifact de migration-test-results.xml - evidencia do run vermelho transcrita do log a mao; follow-up barato.
- (code review) AGENTS.md diz '24 test modules'; ha 111 - deriva pre-existente.
- (QA) subir migration-test-results.xml como artifact `if: always()` para triagem de run vermelho; MIN_CASES = 53 duplicado em script e teste (deliberado); protecao de branch exigindo o check novo continua sendo passo manual do operador no GitHub.

## [APRAS-51] Alinhar guard e mapeamento de permissão em todas as rotas — 2026-09-06

- 2/6.1: '15 das 16 permissoes sao detidas pelos seis bundles' esta errado nos dois numeros: 25 rotas carregam 20 permissoes distintas e cinco nao sao detidas por todos (tasks:read, tasks:comment, reservations:cancel para GUEST; reservations:reject para GUEST/MANAGER/PORTEIRO/RESIDENT; votes:tally_read para GUEST/PORTEIRO); o delta 3 segue correto - as outras 147 celulas sao inertes por duas razoes (perfil detem a permissao, ou a celula ja registra 403).
- 4.4: 'todos os seis bundles detem packages:read e packages:pickup' e falso para GUEST; a razao certa da cegueira da matriz e que nenhum bundle detem packages:queue_read sem a permissao mapeada.
- 4.1: a 'afirmacao geral' e literalmente falsa para GET /tasks/ (tasks.py:52 consulta tasks:read para devolver []) - reescrever como 'consulta a permissao mapeada para RECUSAR o chamador'.
- 4.3: nomear run_cell/resolve_path/REQUEST_BODIES/QUERY_PARAMS como importados sem modificacao; token do ator sob nova chave de world.tokens do proprio modulo; dizer como o modulo obtem a sessao (cell_client so entrega o TestClient).
- 4.2: predicado S sem 'and not in D'; afirmar disjuncao par a par das cinco formas.
- (code review) POST /space-reservations/{id}/reject fica duplamente gateado: reservations:reject na rota (APRAS-51) + reservations:approve no servico (reservation_service.py:298), sem celula de paridade que note - follow-up: decidir se rejeitar exige approve ou se o servico deve checar reject.
- (code review) request_as em test_permission_alignment.py duplica matrix_world.run_cell; importa _FILE_BYTES/_NoBody privados.
- (code review r2) test_docs_agents_md.py:18 passa a importar app.main transitivamente via o modulo de alinhamento - acoplamento correto, mas o arquivo perde a propriedade 'sem import da app'.
- (code review r2) secao 'Permissions are in code' do AGENTS.md esta virando changelog; na proxima edicao, subsecao 'Permission enforcement'.
- (QA) ER-4 'ruff check/format --check limpos' e falso repo-wide (1145 erros, 183 arquivos reformatariam), igual na base - ruff nao roda em nenhum workflow; este diff adiciona zero e remove quatro (assunto da APRAS-54).
- (QA) caso degenerado {module:X} com permissao de escrita mostra 403 como 'Erro de conexao / Could not connect to the server', nao o texto de autorizacao que o §9 promete - corrigir o mapeamento no parseApiError do frontend.
- (QA) direcao positiva de POST /uploads/photo nao assertavel porque matrix_world._FILE_BYTES nao e imagem decodificavel - trocar por um PNG minimo valido.

## [APRAS-52] Histórico de assinatura com rota e tabela na página do superuser — 2026-09-06

- 2.3: renomear test_allowlist_is_twenty_seven_routes (test_tenant_route_scope.py:124) junto com o == 28, como os outros quatro walkers.
- 2.3: numeros de linha sao pre-APRAS-51 (a 51 insere constantes e o loader _51 acima da l.468 de test_permission_parity_matrix.py) - localizar por nome de funcao/constante.
- Apagar a secao 10 (pergunta do caminho ja decidida: espelho das irmas em /tenants/{id}/subscription/history).
- 6.4: adicionar caso de refetch apos troca de plano (5.2 invalida em useSetTenantPlan e useSetTenantCourtesy).
- ER-1: test_the_superuser_history_matches_the_tenant_side_history compara limit=100 com leitura sem teto - so vale com fixture < 100 linhas; docstring.
- ER-3 do board foi substituido (baseline _52 impossivel para rota nao mapeada) - registrar no PR body.
- (code review) subscription_service.py:325-337 resolve nomes de plano/autor com um session.get por id distinto (23 queries para 20 linhas, 2*limit+2) - dois selects in_() deixariam O(1) por pagina.
- (code review) AGENTS.md:541-543 atribui o crescimento 183->201 de rotas mapeadas (108 celulas) a esta tarefa, que so moveu 22->23; texto literal pedido pela spec 7.3.
- (code review) TenantSubscriptionsPage.tsx:337 mostra changed_at ISO cru (espelho de SubscriptionPage.tsx:272) - formatar ambos ou nenhum; considerar keepPreviousData no paginador.
- (QA) tabela sem <caption> e paginador sem aria-live (troca de pagina nao anunciada); ao cair numa pagina 2 esvaziada apos um save, mostra estado vazio com Previous habilitado sem dica.

## [APRAS-53] Upload de evidências e anexos de contestação no cliente de infrações — 2026-09-06

- 2.2 cita media_service.py:25-26; as constantes estao em :23-24 (valores corretos).
- 3.6(b): linha do conjunto MIME escreve `new Set(...) === new Set(...)`; a assercao e toEqual.
- ER-3: 'as unicas mudancas fora de frontend/' e contradito pelos artefatos do pipeline (spec, tasks.json, suggestions-log) - dizer 'fora de frontend/ e de docs/'.
- 3.6(c): 'tres linhas recursivas' - o modelo _permission_guards tem sete (l.281-287).
- Board ER-4 carregava um '---' final copiado da regua horizontal; removido pelo orquestrador ao aprovar.
- (code review) markup thumbnail+link duplicado 3x (AttachmentUploader.tsx:201, InfractionDetailsView.tsx:80, InfractionStageTimeline.tsx:70) - extrair um AttachmentThumb.
- (code review, backend follow-up) attachment_urls e evidence_urls sao list[str] sem validacao server-side (schemas/infraction.py:230,303) e agora sao renderizados como href de conteudo enviado por morador; React 19 bloqueia javascript: mas validar esquema/host de URL na escrita e o certo.
- (code review) AttachmentUploader.tsx:23 mostra 'WEBP' onde o servidor diz 'WebP'; personas redeclaradas em seis arquivos de teste (permissionFixtures.ts poderia hospedar); raise AssertionError morto apos pytest.fail em test_uploads.py:216.
- (QA, pre-existente desde a 44) ContestationForm nao e gateado por infractions:contest: morador com uploads:photo_create + my_lots_read mas sem contest ve o formulario inteiro, sobe o MediaAsset, submete e recebe 403 silencioso sem erro renderizado - gatear o formulario e renderizar a recusa.
- (QA, backend follow-up) POST /uploads/photo nao valida entity_id: chamador do tenant A armazena asset apontando para infracao do tenant B (201); a rota de contestacao esta corretamente escopada (404), nada cruza - validar entity_id contra o tenant na escrita.

## [APRAS-54] Dívida de lint do backend e ruff como gate de CI — 2026-09-07

- 4.4 linha 7: cinco reimplementacoes privadas de _now() em app/ (models/plan.py:18, models/subscription.py:23, services/subscription_service.py:59, services/tenant_service.py:48, services/plan_service.py:38), nao duas - a guarda forca todas, mas a lista esta curta.
- Piso real de # noqa ~89 (o slice 3 apaga seis `# noqa: DTZ003` que RUF100 nao conta); gate <= 108 inalterado.
- 2: cadeia pos-automacao medida em replay 953 -> 868 -> 780 -> 414 -> 303 (o 695 omite o ruff format que o 4.3 roda apos o fix de FAST); 3.2 manda re-medir.
- Unica ocorrencia em prosa que a guarda textual vai pegar: docstring de _next_cast_at em voting_service.py:437.
- 7: a generalizacao do refresh e mais ampla que a evidencia (asset_service.py:313/331, purchase_service.py:623/636 - conclusao vale porque os bodies nao leem o timestamp nao-refrescado).
- 5.0: tabela por slice sem coluna para as quatro cercas de diff do 5.5.
- (code review) re-wraps manuais de E501 que partem frases de docstring/comentario (finance_service.py:314-316, package_service.py:1-2 e :89-90 com `# not` sozinho, visitor_service.py:86-87) - so estilo.
- (code review) app/seed_demo.py deveria entrar em [tool.coverage.run].omit ao lado de app/seed.py (pre-existente, explica a base 96.3 % vs 98.6 %).
- (QA) a afirmacao do 4.4 sobre o psycopg2 estava errada: o Postgres converte o valor aware para o TimeZone da sessao antes do cast para TIMESTAMP WITHOUT TIME ZONE (sessao nao-UTC gravava 10:13 onde UTC grava 13:13); db_now() e o lado correto (inconsistencia pre-existente corrigida) - spec e docstring do clock.py corrigidos pelo orquestrador no fechamento.
- (QA) ARG002 em tests/** e um quinto codigo alem dos quatro enumerados no ER-1 (27 ocorrencias, irmao do ARG001 existente, justificado em comentario) - e por isso NOQA_CAP fechou em 68 e nao 95.
- (QA) backend/.venv_qa/ untracked e fora do .gitignore (pre-existente).

## [APRAS-55] Reorganizar navegação com menu lateral colapsável agrupado por áreas funcionais — 2026-09-07

1. **Localize mobile hamburger `aria-label` (`nav.openMenu`)**:
   - In § 1.2 and § 3.5, the hamburger toggle button specifies static `aria-label="Abrir menu"`. While desktop collapse/expand controls are localized via `t("nav.collapseMenu")` and `t("nav.expandMenu")`, adding a dedicated translation key `nav.openMenu` (`"Abrir menu"` / `"Open menu"`) in `pt.json` and `en.json` ensures full bilingual coverage for all navigation controls per ER-7.

2. **Clarify test boundaries between `Sidebar.test.tsx` and `Navbar.test.tsx`**:
   - In § 4.1, "Mobile Drawer Behavior" is listed under `Sidebar.test.tsx` with "Verify hamburger opens the mobile drawer". Since the hamburger toggle button lives in `Navbar.tsx`, testing the complete hamburger-to-drawer opening interaction is best performed in `Navbar.test.tsx` (which renders both `Navbar` and `Sidebar` within `SidebarProvider`), while testing backdrop clicks and close buttons can remain in `Sidebar.test.tsx`.

## [APRAS-55] Reorganizar navegação com menu lateral colapsável agrupado por áreas funcionais — 2026-09-07

1. **Mid-file imports in `frontend/src/App.tsx:121-125`**:
   `useMyPermissions` was originally placed at line 121 (below `RootRedirect`), and lines 122–125 append `useAuth`, `SidebarProvider`, `useSidebar`, and `cn`. Furthermore, `AuthProvider` is already imported from `./features/user-administration/context/AuthContext` at line 14, creating duplicate import statements from the same module. Moving these imports to the top of `App.tsx` and consolidating `useAuth` with `AuthProvider` would improve file structure and cleanliness.

2. **Generic fallback icon in `frontend/src/features/user-administration/components/Sidebar.tsx:94`**:
   `ICON_MAP[item.iconName] || CheckSquare` uses `CheckSquare` as a default fallback. While all 30 current routes in `NAV_ITEMS` have explicit mappings in `ICON_MAP`, using a more neutral layout icon (e.g. `Folder` or `LayoutGrid`) as the default could avoid confusing a generic link with a task checkbox if any future route icon name is mistyped or missing.

---


## [APRAS-60] Relatório geral de obras em HTML imprimível, salvo em Documentos — 2026-09-14

- There are **four** parity baseline files on disk
  (`parity_matrix_baseline.json`, `_40`, `_44`, `_51`), not three. `_51` is an
  *override* layer, not an addend, so it needs no change, but the spec's
  phrase "the three pre-existing baselines stay byte-identical" should say
  four files stay untouched to avoid an implementer "fixing" `_51`. Note also
  that only the F2 file and `legacy_role_bundles.json` carry pinned sha256
  assertions; `_40`/`_44`/`_51` are pinned by provenance tests instead, so
  "their pinned sha256 assertions must still pass" is only true of F2.
- The new baseline will need a `_meta` block with a `merge_base_sha` and will
  have to be produced by `tests/tools/record_parity_baseline.py`; the spec's
  file list names the constants but not the recorder invocation. Adding it
  would save a round.
- `matrix_world.neutralised_storage` swaps only the three *module-level*
  providers (`media_service`, `announcement_service`, `finance_service`). If
  the new service constructs `LocalStorageProvider()` inline the way
  `save_minutes` does, the ADMINISTRATOR/DIRECTOR parity cells will write real
  files under `backend/static/uploads` (gitignored, so harmless, but contrary
  to the harness's "every non-role dimension neutralised" contract). Exposing
  a module-level `_storage_provider` and adding it to `neutralised_storage`
  would keep the matrix side-effect free — it is one more edit inside the
  `matrix_world.py` change the spec already budgets a sha re-pin for.
- Because the world is shared across all cells, the new POST cell mutates it
  (a folder and a document row). Worth stating in the spec that the full
  parity run must be executed once end-to-end to prove the F2 file really
  stays byte-identical.
- Test criterion 5 asserts the body contains no `nan`; that substring occurs
  in ordinary Portuguese proper names (e.g. "Fernanda"), so the fixture data
  for that case should be chosen deliberately, or the assertion made
  case-sensitive on `NaN`.
- The route-ordering note says "declared before `GET /api/v1/projects/{project_id}`";
  the actual path parameter in `projects.py` is `{id}`. Cosmetic, but the
  registry key is `("GET", "/api/v1/projects/{id}")`.
- The model field is `contractor_name`, not `contractor`.

## [APRAS-60] Relatório geral de obras em HTML imprimível, salvo em Documentos — 2026-09-14

- "in the project's display timezone" (line 121) names a mechanism that does
  not exist in the tree: `app.core.clock` returns naive UTC and the precedent
  `voting_service._fmt_datetime` (`voting_service.py:994`) formats it directly
  with `strftime`. Nothing hangs on it — the ER asserts the format, not the
  value — but spelling it as `clock.db_now().strftime("%d/%m/%Y %H:%M:%S")`
  would remove an invitation to invent a timezone conversion.
- The spec does not name `publication_year`/`publication_month` for the
  `AssociationDocumentCreate` it builds; `save_minutes` fills them from the
  assembly date (`voting_service.py:1185–1186`). The generation date is the
  obvious analogue; saying so costs one clause.
- Worth a line in the new helper's docstring cross-referencing
  `voting_service._find_or_create_minutes_folder`, so a future reader who
  notices the two folder helpers differ finds the reason at the divergence
  rather than in this spec.

## [APRAS-60] Relatório geral de obras em HTML imprimível, salvo em Documentos — 2026-09-14

* `backend/tests/matrix_world.py`'s `REQUEST_BODIES` is length-asserted against
  `EXPECTED_REQUEST_BODY_COUNT = 99` in `test_permission_parity_matrix.py:608`.
  The spec lists the `NO_BODY` entry and the `HARNESS_SHA256` re-pin but not
  this constant; add "`EXPECTED_REQUEST_BODY_COUNT` 99 → 100" to the file list.
* The migration's `down_revision` is unstated. The committed head is
  `0036_add_infraction_tables`; `0037_remove_papel_suffix` is **untracked** in
  this worktree (same class as `sync_drive_obras.py`, which the spec does call
  out). Chaining onto `0037` breaks a clean checkout; chaining onto `0036`
  alongside a later-committed `0037` produces two heads. Say explicitly that
  `down_revision` is the head at implementation time and that the number is
  renumbered at merge.
* "the three pre-existing parity baselines stay byte-identical": there are
  **four** files — `parity_matrix_baseline_51.json` exists but is an *override*,
  not an addend (see the comment at `test_permission_parity_matrix.py:103-109`).
  Wording is harmless for the partition claim but should say "four files
  untouched, three of them addends".
* The bar labels: the ported `one_bar()` markup is
  `<span>previsto</span><b>13%</b>`, so the spec's "reading `previsto X%`" and
  the criterion-6 assertion "the label `previsto —`" are not contiguous strings
  in a mock-faithful document. State the assertion as the `<b>` content inside
  `div.tag.plan`, so the test does not push the implementer away from the mock.
* Criterion 4 cannot distinguish "**all** IN_PROGRESS" from the generator's
  `items[:3]` cap, because it uses only 2 IN_PROGRESS milestones. Use 4 so the
  deliberate divergence from `groups_html()` is actually pinned.
* The presentation order *within* the `Concluídos` card is unspecified
  (selection order is). The mock renders oldest→newest (`items[-3:]`); say
  whether the rendered list is newest-first.
* `AssociationDocument.title` "using `app.core.clock` in the project's display
  timezone": no display-timezone concept exists — `voting_service._fmt_datetime`
  is a plain `strftime` over a naive value, and `AGENTS.md`'s clock rule keeps
  every stored datetime naive. Drop the phrase.
* Every recent feature commit updates `AGENTS.md` (APRAS-51/52/53/44/40), and
  this task falsifies its literal "`ROUTE_PERMISSIONS` maps **201** routes".
  Add `AGENTS.md` to the files-touched list.
* Cosmetic: the route the new ones must precede is
  `GET /api/v1/projects/{id}`, not `{project_id}`.
* The mock emits `<title>Relatório de Obras — <tenant></title>`; the spec never
  mentions the document `<title>`.

## [APRAS-60] Relatório geral de obras em HTML imprimível, salvo em Documentos — 2026-09-14

- Test criterion 9 spells the resolution as
  `session.get(Tenant, tenant_context.acting_tenant_id(session))`, omitting the
  `or DEFAULT_TENANT_ID` fallback that "Tenant scoping" and expected result 4
  both carry. It is harmless as written — that test sets the acting tenant on the
  session, so the fallback never fires — but repeating the full expression would
  keep a single spelling of the rule across the document.
- "Tenant scoping" permits either the relationship route or the
  `project_id.in_(...)` route for milestones and bulletins. Both are correct; if
  the implementer picks the relationship route, a `selectinload` on the projects
  query would avoid N+1 on an install with many projects. Worth a line in the
  service docstring either way, since the choice is invisible in the output.

## [APRAS-60] Relatório geral de obras em HTML imprimível, salvo em Documentos — 2026-09-14

- `backend/pyproject.toml:109-114` — the `E501` per-file ignore is granted to
  the whole of `project_report_service.py`, while the justification (the ported
  CSS constant) covers only one string. A future long *Python* line in that
  module now goes unnoticed. Non-blocking; if you want the narrower version,
  `# noqa: E501` on the `CSS` assignment alone would do it, at the cost of one
  more line against `NOQA_CAP`.
- `project_report_service.py:487` and `:559` — `getattr(tenant, "logo_url", None)`
  / `getattr(tenant, "name", None)` are being used as a `None`-guard on the
  *object*, not as attribute discovery. `tenant.logo_url if tenant else None`
  says the same thing and would still fail loudly if the attribute were ever
  renamed away. Purely a readability point; the behaviour under test is correct.
- `project_report_service.py:637-640` — `get_report_html` is a one-line
  passthrough to `render_report_html`. It mirrors `voting_service.get_minutes_html`,
  so I am not calling it duplication, but the endpoint could call the renderer
  directly.
- `project_report_service.py:702` — `save_report` is annotated `-> Any` while
  the route declares `AssociationDocumentRead`. Narrowing the return annotation
  (as the route already does) would let the type checker connect the two.
- `ConstructionTrackerPage.tsx:163-166` — the object URL is never
  `URL.revokeObjectURL`'d. On a page where an operator generates the report
  repeatedly this leaks one blob per click for the lifetime of the document.
  Revoking it on the new tab's `load`, or after a timeout, is the usual fix.

## [APRAS-60] Relatório geral de obras em HTML imprimível, salvo em Documentos — 2026-09-15

- `planned_to_date` accepts a lexically well-formed but calendrically impossible month (`"2026-13"`) because the
  guard is `re.fullmatch(r"\d{4}-\d{2}", month)` and the comparison is string-based. Such a point is treated as
  "in the future" rather than as a malformed curve, so a schedule containing it silently renders `previsto 0%`
  instead of degrading to "no curve". A `01 <= mm <= 12` check would make the strictness the docstring claims exact.
  Not blocking: no writer of the column can currently produce that value (there is no API or UI for it).
- `_find_or_create_obras_folder` matches the folder by `name == "Obras" AND parent_id IS NULL` within the ambient
  tenant scope. That is correct today, but an operator who renames the tenant's "Obras" folder will silently get a
  second one on the next save. A stable marker (a system-folder flag or a fixed id per tenant) would make the
  "created once" property independent of the display name.

## [APRAS-57] Remover landing_path do modelo de papel — 2026-09-15

- The spec says `ProtectedRoute.guestWelcome.test.tsx` has "one non-landing case". It
  has five cases, two of which are permission cases ("lets a DIRECTOR through…",
  "shows the restricted-access message to a caller holding no tasks permission"). Both
  are already covered by `ProtectedRoute.permissions.test.tsx` ("renders the page when
  the rule's module permission is held" / 'renders "Acesso restrito" when it is not'),
  so the spec's "if it is not already covered there" escape hatch keeps the outcome
  correct — but the count is wrong and should be corrected so the developer does not go
  looking for a single case.
- While removing `landingRedirect` from `routeAccess.ts` and `permissions.ts`, the
  neighbouring comments say the flag marks "the two routes"; it marks three. Worth
  noting in the spec that those comments disappear with the flag rather than being
  repaired.
- `ProtectedRoute.tsx` keeps `useMyPermissions` for `disabled_modules`; spelling that
  out in the "Files touched" bullet would remove the small chance a developer strips the
  hook wholesale and breaks the module-off copy.

## [APRAS-57] Remover landing_path do modelo de papel — 2026-09-15 (spec_review round 2)

- Result 2's third grep path, `frontend/src/**/__tests__`, is shell-dependent:
  it recurses under zsh, but under bash without `globstar` it degrades to
  `frontend/src/*/__tests__`, which matches no existing directory and makes
  grep error out rather than report cleanly. A shell-agnostic form —
  e.g. `grep -rln <pattern> backend/tests frontend/src --include='*.test.ts'
  --include='*.test.tsx' --include='permissionFixtures.ts'`, or simply grepping
  `frontend/src` and allowlisting — would verify the same thing without
  depending on the operator's shell.
- Result 14 requires `AGENTS.md` to contain zero occurrences of `landing_path`
  or `landingRedirect`, while the Files-touched entry says the paragraphs are
  "rewritten to describe the post-removal behaviour". A rewrite phrased as
  "roles no longer carry a `landing_path`" would satisfy the prose intent and
  fail the grep. Result 14 is the binding criterion, so the developer should
  drop the terms entirely rather than describe their absence.

## [APRAS-61] Perfil do condomínio com upload do logo — 2026-09-15 (spec_review round 1)

- §"Test criteria", frontend: "the page renders `RestrictedAccessMessage` for a caller
  without `tenants:profile_update`" is loosely worded — that component is a
  module-private const inside
  `frontend/src/features/user-administration/components/ProtectedRoute.tsx:37`, is not
  exported, and the page itself carries no gate (D6 is explicit that the gate is the
  `ROUTE_ACCESS` rule). State that the test renders the page *through* `ProtectedRoute`,
  so an implementer does not export the component or duplicate an in-page gate.
- §"Behavior — backend": `TenantProfileUpdate = {name: str | None}` does not say what
  `PATCH` with `name: null` (or an empty body) answers. A 200 no-op is the natural
  reading, but one sentence removes the choice.
- `AGENTS.md:738` ("**201/174** and all four parity baselines stay byte-identical") is
  prose that `test_docs_agents_md.py` does not check, and it is already stale. Not this
  task's debt, but the paragraph is being edited anyway.
- Consider naming the follow-up from D4 ("show the tenant logo in the sidebar header")
  as a concrete backlog item when this ships.


## [APRAS-61] Perfil do condomínio com upload do logo — 2026-09-15 (spec_review round 2)

None.

## [APRAS-57] Remover landing_path do modelo de papel — 2026-09-15 (code_review round 1)

- `backend/tests/test_roles.py` — the new
  `test_update_role_ignores_an_unknown_landing_path_key` ends with
  `assert not hasattr(session.get(Role, ut.id), "landing_path")`. That is an
  assertion about the *mapped class*, already pinned exactly by
  `test_role_schemas_expose_permissions`; it cannot observe the still-present
  DB column, so the docstring's "nothing about a landing is persisted" claims
  slightly more than the code shows. The 200 + exact-response-keys assertions
  above it are the load-bearing ones and they are right. Non-blocking.
- `frontend/src/__tests__/RootRedirect.test.tsx` — the case "renders the
  general dashboard for a caller whose role formerly carried /welcome" drives
  `withPermissions([])`, i.e. it is distinguished from the `/gate` case only by
  its title. Harmless, but the guest persona's identity is now carried by the
  test name alone.


## [APRAS-57] Remover landing_path do modelo de papel — 2026-09-15 (code_review round 2)

* `frontend/src/__tests__/RootRedirect.test.tsx` — the second case is titled
  "…formerly carried /welcome" but is driven by `withPermissions([])`, identical in
  substance to the third ordinary-caller case save for the empty permission set.
  It is not wrong, just nearly redundant; a comment naming the guest persona
  explicitly (as the `/gate` case does) would carry the intent better.
* `backend/tests/test_role_permissions.py:332` — the function is still named
  `test_role_read_carries_no_role_and_no_allowed_menus` while its docstring now
  describes a three-key set. Renaming it to match what it pins today would help
  the next reader.


## [APRAS-57] Remover landing_path do modelo de papel — 2026-09-15 (code_review round 3)

* `frontend/src/__tests__/RootRedirect.test.tsx` — the second case
  ("…formerly carried /welcome") asserts only that `Painel Geral` renders; its
  sibling also asserts the routed pages are absent. Adding
  `expect(screen.queryByText("Welcome Page")).toBeNull()` there would make the
  "no navigation" claim symmetric across both persona cases. It is already
  covered transitively by the `/gate` case.
* `backend/tests/test_roles.py` — `assert not hasattr(session.get(Role, ut.id),
  "landing_path")` pins the *model* shape rather than the stored row. That is
  the stronger assertion for as long as the column survives APRAS-58, so this
  is a note rather than a change request.

## [APRAS-61] Perfil do condomínio com upload do logo — 2026-09-15 (code_review round 1)
- `backend/app/services/tenant_service.py` — `set_logo` passes the client-supplied
  `filename` straight to `LocalStorageProvider.save_file`, which derives the stored
  extension from `Path(filename).suffix`. There is no traversal (the basename is a
  uuid4 and only the suffix survives), but the *extension* is attacker-controlled, so
  `logo.html` with PNG-polyglot bytes would be written under `/static/uploads/` and
  served same-origin — the exact class D2 exists to close. This is **pre-existing**
  behaviour shared by all five `save_file` call sites (`media_service`,
  `announcement_service`, `finance_service`, `voting_service`, and now this one), so
  it is not a regression introduced here and not blocking. Worth a follow-up task
  that derives the extension from the validated MIME type in `save_file` itself,
  fixing all five at once.
- `frontend/src/hooks/useTenantProfile.ts` — the spec's Approach says the TanStack key
  is "invalidated by all three mutations"; the implementation instead writes the
  response body in with `setQueryData`. The rationale in the file (the body *is* the
  new state; an invalidation would flash the old logo) is sound and, in my view,
  better than the spec text. Flagging only so the divergence from the written spec is
  on record, not as a defect.
- `frontend/src/features/user-administration/pages/TenantProfilePage.tsx:122` —
  `clearLogo.mutate(undefined as never, …)`. Typing `useProfileMutation`'s variables
  as `void` for the clear mutation would drop the cast.
- `frontend/src/i18n/locales/{pt,en}.json` — `tenantProfile.errors.size` hard-codes
  "2 MB" while `tenantProfile.hint` interpolates `{{size}}` from the pinned constant.
  If the cap ever moves, the hint follows and the error message silently lies. Reuse
  the interpolation.


## [APRAS-61] Perfil do condomínio com upload do logo — 2026-09-15 (qa_review round 1)

- I ran the backend suite with `-p no:randomly` for a deterministic single pass. The CI invocation (`uv run pytest`) randomizes order; nothing in the diff looks order-sensitive, but the ordinary randomized run is the one that ships.
- `TenantService._delete_stored_logo` maps a `/static/uploads/…` URL back to a path relative to the provider's `base_dir`, which is the cwd-relative default `static/uploads`. That is correct today and matches the rest of the media pipeline, but it makes logo deletion silently a no-op if the process is ever started from a different working directory. `delete_file` already swallows, so the failure mode is an orphaned file rather than a broken request — worth an absolute `base_dir` at some point, not for this task.
- `set_logo` validates size before MIME, so a 3 MB SVG reports "too large" rather than "wrong format". Both are 422 and both are correct; only the copy the operator reads differs.

## [APRAS-58] Consolidar as 40 migrações em uma única 0001_initial_schema — 2026-09-17 (spec_review round 1)

- §Approach 5 / §Files touched: `.github/workflows/ci.yml` is listed as touched
  only for a comment re-statement ("roughly 30 of the 53 cases"), but no
  expected result covers it, so the edit is invisible to QA. Either fold it
  into the `MIN_CASES` result or accept it as incidental.
- `assert_no_skips.py` documents `MIN_CASES` as "a **floor**, not an equality",
  with the stated virtue that adding a case must not require touching the file.
  Expected Result 6 demands equality with the collected count. That is a
  deliberate tightening, and the spec does say to re-state the docstring — worth
  making explicit that the floor-vs-equality doctrine is being changed, so a
  later reader does not treat the new value as a floor again.
- §Test criteria case 9 says `TENANT_SCOPED_TABLES` where §Approach 4 says
  `_TENANT_SCOPED_TABLES`. The underscored spelling is the one
  `test_tenant_models.py` / `test_tenant_context.py` parse for; align the two
  mentions to avoid the implementer writing the un-underscored name.
- §Files touched, `backend/pyproject.toml`: the "only if the coverage gate
  fails, add `app/seed_demo.py` to the omit list" escape hatch is bounded and
  justified, but it makes Expected Result 8 pass by two different routes. A
  one-line note on which route was taken, in the commit body, would keep the
  record honest.

## [APRAS-58] Consolidar as 40 migrações em uma única 0001_initial_schema — 2026-09-17 (spec_review round 2)

- §Approach 4 names the literal `_TENANT_SCOPED_TABLES` (leading underscore)
  while §Test criteria case 9 writes `TENANT_SCOPED_TABLES`. Not blocking —
  Expected Result 6 is phrased over test outcomes, not the identifier — but
  picking one spelling would spare the implementer a guess when writing the
  `ast` lookup in `test_tenant_models.py`/`test_tenant_context.py`.
- §Files touched lists `backend/pyproject.toml` as conditional ("only if the
  coverage gate fails"). Conditional file edits are fine here because Expected
  Result 8 judges the gate, not the file, but a note in the commit body about
  whether the omit entry was needed would help the APRAS-59 operator.

## [APRAS-58] Consolidar as 40 migrações em uma única 0001_initial_schema — 2026-09-17 (code_review round 1)

1. **`AGENTS.md:449-456` — the partition total is now self-contradicting.**
   The diff correctly updated the two group counts (28 → **32** directly
   scoped, 21 → **24** inherited) but left the sentence's closing total at
   "Four tables are unscoped ... — **for 53 in all**". 32 + 24 + 4 = **60**,
   which is exactly `len(SQLModel.metadata.tables)` (verified live: 60). The
   arithmetic was internally consistent *before* this diff (28 + 21 + 4 = 53)
   and is wrong after it. One-word fix: `53` → `60`. Not blocking — it is
   prose, no test asserts it, and a second stale "53-table partition" already
   predates this diff at `AGENTS.md:1216` (out of this task's scope) — but the
   next reader of that paragraph will trip on it.
2. **`backend/app/seed_demo.py` (+2219/-733) rides in on a migration-squash
   commit.** The spec authorised committing the working-tree version "as-is",
   and the spec's own acceptance criterion anticipates it (I verified it: see
   Evidence §6). Still, ~2200 lines of demo-data expansion unrelated to the
   squash will be indistinguishable from the squash in `git log -p`. Worth one
   sentence in the commit body saying the file arrived from an earlier demo
   session, so a later bisect does not read it as part of the migration work.
3. **Unstaged working-tree noise must not be swept into the commit.**
   `AGENTS.md` is `MM`: the *unstaged* hunk is a 22-line "Running locally"
   section belonging to `f72e94e` (dev-env), not to this task, and
   `docs/suggestions-log.md` is modified and unstaged. The spec requires a
   clean `git status --porcelain` at the end; resolve those two separately
   rather than with a blanket `git add -A`.
4. **`_ENUM_TYPES` (`0001_initial_schema.py:100-140`) is a hand-maintained
   list of 38 native enum types**, and nothing but the Postgres round-trip
   case keeps it complete. That case self-skips without `TEST_POSTGRES_URL`,
   so a future task adding an enum gets no local signal — only CI's
   `Backend Migration Tests (Postgres)` job will catch it. The file's own
   docstring says this; it is the right design given `op.drop_table` does not
   drop types, and `assert_no_skips.py` keeps the CI side armed. Flagging it
   only so the next author knows the list is a manual obligation.
5. **On APRAS-63 / APRAS-64 folding into this same file (asked explicitly,
   not part of the verdict): nothing in the structure makes it hard.**
   `upgrade()` is 60 flat `op.create_table(...)` blocks in dependency order.
   - APRAS-63's `purchase_quote` attachment column is a one-line insertion in
     the block at `0001_initial_schema.py:850`.
   - APRAS-64's twelve float → `Numeric(12, 2)` moves are twelve in-place
     substitutions among the file's 17 `sa.Float()` occurrences.
   - `downgrade()` needs **no** corresponding edit in either case: it is
     `drop_table`-based, so an added column and a changed column type are both
     absorbed.
   - `[tool.ruff.format] exclude` covers `alembic/versions/**`, so hand edits
     will not be reflowed by the formatter.
   The one discipline to keep: change the **models first**, then mirror them
   here, because the compare I ran below (and the module's cases 3-4) is what
   proves the two agree.


## [APRAS-58] Consolidar as 40 migrações em uma única 0001_initial_schema — 2026-09-17 (qa_review round 1)

- `tests/test_migrations_postgres.py` still narrates history by bare ordinal ("the retired
  `0033`", "`0037`'s two columns", "which is how the retired `0037` learnt it"). Those are
  not revision ids and nothing resolves them, but a reader a year from now has no way to
  look them up since the modules are gone. Consider naming what the ordinal *did*
  ("the pre-squash revision that dropped `user.role`") instead of its number.
- Unrelated to the task, and out of scope for these expected results: the working tree
  carries unstaged edits to `AGENTS.md` (+22) and `docs/suggestions-log.md` (+84) that are
  not part of the staged change under test. Worth confirming they are intentional leftovers
  from another process before the branch is committed.

## [APRAS-62] Acabamento da tela de tarefas — 2026-09-17 (spec_review round 1)

- The spec's own "Expected Results" checklist is a condensed paraphrase of the
  task's `expected_results` and silently drops verifiable clauses that the body
  does cover: *"vence hoje"*, `<mark>` **in the list** as well as the card,
  summary and chips staying on screen when the result is empty, dropping on the
  origin column firing nothing, a `readOnly` card not being draggable, the
  overdue counter rendering as a *removable* chip, and
  `assigned_to_id: null` / unchanged payload shape. Restate the task's
  `expected_results` verbatim so the implementer builds to the same list QA
  checks.
- Nothing is said about what the user sees when the optimistic PATCH fails: the
  spec covers the cache rollback but not whether an error message appears (the
  dashboard already has `AlertModal` for the connection error). One sentence.
- `useAssignableUsers` returns `User` objects whose roles are `Role[]`
  (`src/types/auth.ts`), so "the role name(s) on their own line" is satisfiable;
  worth naming the field (`user.roles.map(r => r.name)`) and saying what renders
  for a user with several roles.
- The overdue counter is specified as counting "over the same visible set the
  summary counts" — say explicitly what it reads once `overdueOnly` is on
  (it would then equal the visible count).

## [APRAS-62] Acabamento da tela de tarefas — 2026-09-17 (spec_review round 2)

- Double-fire risk from the B1 fix: `handleKeyDown` is kept on the now-native
  `task-card-open` `<button>`, so in a real browser `Enter` fires both the
  keydown handler and the native click, calling `onClick` twice. jsdom's
  `fireEvent.keyDown` does not synthesise the click, so the existing
  `toHaveBeenCalledTimes(1)` assertions still pass and hide it. Opening a modal
  is idempotent, so this is non-blocking, but dropping the manual
  `Enter`/`Space` handling and relying on native button activation would be
  cleaner.
- Consider asserting the `aria-live` grab/drop announcement in the board drag
  test, not only the visible ring — the spec promises it but no test criterion
  covers it.

## [APRAS-63] Acabamento da tela de orçamentos — 2026-09-17 (spec_review round 1)

- The quote attachment accepts `application/pdf` while
  `media_service.ALLOWED_MIME_TYPES` accepts `image/webp` and no PDF. Two
  neighbouring upload paths with disjoint accepted sets is a future confusion;
  a one-line comment in `purchase_service.py` saying why the sets differ would
  pay for itself.
- D2 reuses `media_service.MAX_FILE_SIZE` by import but the frontend pins its own
  `QUOTE_ATTACHMENT_MAX_FILE_SIZE_BYTES`. The two-sided contract test (Test
  criteria 9) should assert against the imported backend constant, not a
  re-typed 5 MiB literal, or the pin can drift silently if `media_service` changes.
- Test criteria 2 lists the 422 cases inline; naming them as a parametrised case
  id list would make the QA read of "a refused file answers 422" unambiguous.

## [APRAS-63] Acabamento da tela de orçamentos — 2026-09-17 (spec_review round 2)
- None.

## [APRAS-64] Dinheiro em Decimal/Numeric — 2026-09-17 (spec_review round 1)

- §Scope's factual claim "Money is multiplied in exactly two places" is wrong. `app/services/purchase_service.py:41` (`_quote_total`) is a third multiplication of `unit_price * quantity` with a `round(...)`, and `purchase_service.py:362` / `asset_service.py:164` round aggregates. ER 4's "no `round(` over money remains under `app/`" does force all five through `quantize_money()`, so the requirement set still closes — but the prose (and ER 4's "both call sites") understates the surface and should name all five.
- §Decision 2 says "`Money` is also what carries `max_digits=12, decimal_places=2`". `Money` as defined is only `Annotated[Decimal, PlainSerializer(...)]`; the constraints are per-field `Field()` kwargs (as Decision 3 implies for `(8, 4)`). Reword to avoid suggesting a second annotated alias.
- §Test criteria's fine regression — "a `condo_fee_amount` whose product ends in a half-cent rounds up" — is looser than its purchase-quote sibling. Pin the literal values, as ER 4 does.


## [APRAS-64] Dinheiro em Decimal/Numeric — 2026-09-17 (spec_review round 2)

- ER 6 says the rule is `MoneyIn` on `*Create`/`*Update` schemas. If any
  `*Create` schema is also returned as a response anywhere, that field would
  lose its scale bound; worth one sentence confirming the request schemas are
  request-only.
- Decision 4 states request values are quantized "before persisted" but the
  §Files touched list only names `purchase.py`'s `_compute_total` and
  `infraction_service._price` as quantize sites. Naming where an incoming
  `unit_price`/`fine_amount` itself (not just the derived total) is quantized
  would remove an implementation choice.

## [APRAS-64] Dinheiro em Decimal/Numeric — 2026-09-17 (spec_review round 3)

- `test_migrations_postgres.py`'s metadata-vs-live comparison covers names and
  nullability but not types, which is why the `NUMERIC(12,2)` (migration) vs
  bare `NUMERIC` (SQLModel, nullable) divergence passes silently. Worth one
  sentence in §"Approach" recording that the divergence is known, intentional
  and invisible to the existing drift suite, so a later task does not "fix"
  the migration down to bare `NUMERIC` to make the two agree.


## [APRAS-64] Dinheiro em Decimal/Numeric — 2026-09-17 (spec_review round 4)

- §Decision 2, line 96 asserts flatly that `Money` "is what makes SQLModel emit
  `NUMERIC(12, 2)` (measured)", while §Test criteria line 210 records the
  measured counter-case that a nullable `Money | None` column yields a bare
  `NUMERIC`. Both are true in their own context, but read together the earlier
  sentence overstates. Since the DDL is hand-written in
  `0001_initial_schema.py` and PostgreSQL is the precision oracle, this has no
  implementation consequence — worth one qualifying clause ("for non-nullable
  columns") on line 96 the next time the file is edited, not worth a round.
- The spec never says whether the twelve-column PostgreSQL assertion should be
  table-driven (one parametrised case over a literal list of
  `(table, column, precision, scale)`) or a single case with twelve asserts.
  Either satisfies ER 3; a parametrised list makes a missing column visible in
  the test report. Implementation detail.
- Q1/Q2/Q3 remain open operator questions with implemented answers recorded.
  They are decisions, not spec defects; the spec states the one-line change for
  each if the operator rules otherwise.

## [APRAS-62] Acabamento da tela de tarefas — 2026-09-18 (spec_review round 3)
- Verify the drag manually in Firefox and Safari during implementation: the
  jsdom `fireEvent.dragStart` tests cannot detect a browser refusing to start a
  drag from a form-control element. If one refuses, wrapping the unchanged
  `<button>` in a `<div draggable>` preserves both the single-button-role
  invariant and `TaskCard.test.tsx:80`.
- Expected result 4 says "no drag handle" while the spec permits an optional
  decorative grip icon and the mock draws one. Wording it as "no focusable drag
  handle / no second button role" would remove any chance of a QA reading them
  as contradictory.
- The spec does not say whether the decorative grip is hidden when dragging is
  disabled (status filter active, or a `readOnly` card). Showing a grip on a
  card that cannot be dragged is the same dead affordance the header hint
  exists to avoid. Cosmetic, implementer's call.

## [APRAS-64] Dinheiro em Decimal/Numeric — 2026-09-18 (spec_review round 5)

- Decision 5 justifies truncation only on its own terms ("a half-typed value is
  never destroyed mid-keystroke"). Add one sentence stating the asymmetry with
  `quantize_money`'s `ROUND_HALF_UP` and why it is intentional — the two rules
  never observe the same event, and `2.675` can no longer reach the API from a
  browser. A future reader comparing ER 5 with ER 8 will otherwise read it as an
  oversight.
- The Decision 5 table is introduced as "The eleven money inputs" and then
  clarified parenthetically as twelve rows; ER 9 likewise says "All twelve money
  inputs ... with `places = 2`" and then carves out the multiplier. Both are
  unambiguous on a careful read but cost the reader a second pass. Say "twelve
  inputs — eleven money fields at `places = 2` and one ratio at `places = 4`" in
  both places.
- Five of the twelve call sites hold numeric state (`Number(e.target.value)`):
  `AssetFormModal`, `PlansAdminPage` (both), `InfractionRulesPage` (the two
  step fields via `updateStep`). On those, a trailing separator that
  `limitDecimals` deliberately passes through (`"2."`) is still collapsed by
  `Number()` to `2`, so the dot disappears under the cursor. This is
  pre-existing behaviour that the task neither introduces nor is funded to fix —
  and the spec is right to refuse the unification refactor — but it means the
  helper's `"2."` pass-through case only actually protects the string-state call
  sites. Worth one line in Decision 5 so the developer does not chase it as a
  bug during implementation.
- `AvatarCropEditor` is named in the "leave alone" list but contains no
  `type="number"` input. Harmless; drop it for accuracy.


## [APRAS-62] Acabamento da tela de tarefas — 2026-09-18 (code_review round 1)
- `TaskDashboard.tsx:62-77` — `matchingTasks` re-implements a subset of `useTaskFiltering`'s predicate (status / priority / assignee / search) instead of reusing it. It omits the category filter and the simulation visibility rules (`canSeeSimulatedTask`) that `TaskBoard` and `TaskList` do apply, so while simulating a role the summary and the overdue counter can count tasks the board does not render. Reusing `useTaskFiltering` (or extracting its predicate) would make the two agree by construction.
- `TaskDashboard.tsx:281` — `totalCount={loadedTasks.length}`. Because status/priority/assignee/category are *server* filters (`fetchTasks` sends them as query params), `loadedTasks` is already filtered, so with only server filters active the bar reads "Mostrando 12 de 12 tarefas" while chips simultaneously state that filters are on. The spec's example ("12 de 47") implies the unfiltered total. X < Y still happens correctly for search / overdue, which is the main case, so this is cosmetic rather than wrong.
- `en.json` / `pt.json` — `tasks.dashboard.clearSearch` is added to both locales but never referenced in any `.ts`/`.tsx` (YAGNI; the chip's remove control uses `removeFilter`). Separately, `tasks.form.unassigned` lost its last consumer when the `<select>` was replaced (`AssigneePicker` uses `assigneeNone`) and is now orphaned in both locales.
- `AssigneePicker.tsx:127-130` — `blurTimer` is never cleared on unmount, unlike `TaskFilterBar.tsx:73-78` which does clear its debounce timer. Harmless under React 18 (the state update on an unmounted component is a no-op), but the two timers in this task handle the same situation differently.
- `TaskCard.tsx:139-140` — stray double blank line before `export default`.
- `TaskDashboard.test.tsx` ("filters client-side, with no change to the useTasks query key") asserts `vi.mocked(useTasks).mock.calls.length` **toBeGreaterThan** the earlier count. That is true simply because typing re-renders; the assertion that actually proves the test's name is the per-call `expect(options).not.toHaveProperty("search")` loop right after. The count assertion reads as the opposite of what the title claims and could mislead a later reader.

---

# Evidence


## [APRAS-62] Acabamento da tela de tarefas — 2026-09-18 (qa_review round 1)
- `TaskFilterBar` defines `tasks.dashboard.clearSearch` in both locales but never renders it (the search chip's remove button uses `removeFilter`). Harmless, but it is a key with no consumer; either wire it to a clear-button inside the input or drop it.
- `HighlightedText.matchRanges` rebuilds the normalised index map for every render of every card; with long descriptions and fast typing this is O(cards x text). A `useMemo` keyed on `(text, needle)` would make the cost proportional to changes rather than renders. Not measurable at current list sizes.

## [APRAS-63] Acabamento da tela de orçamentos — 2026-09-18 (code_review round 1)

- `frontend/src/features/purchase-management/components/QuoteComparisonTable.tsx:336` and `:412` — the two `{!isNarrow && (` / `{isNarrow && (` blocks break the file's indentation (their children sit at the same level as the guard). Cosmetic only; ESLint does not catch it because formatting is not enforced on the frontend, but it is the one place the file reads as machine-edited.
- `backend/app/services/purchase_service.py:96` — `_delete_stored_attachment` reaches for `getattr(_storage_provider, "base_dir", None)` and silently returns for any provider without one. That is correct today and honest about the non-local stubs, but it means a future S3 provider would silently stop deleting rather than failing loudly. A one-line comment saying so, or an `isinstance(_storage_provider, LocalStorageProvider)` check, would make the silence deliberate rather than incidental.
- `backend/tests/test_permission_alignment.py:24` — the module docstring still reads "That count is unchanged by APRAS-61, whose three new routes are all D-form" immediately after the 137 → 139 sentence was updated. The claim is now about a count that did move; worth a clause naming APRAS-63.
- Not this task's to fix, but worth an entry in the suggestions log: `/static/uploads` is an unauthenticated, tenant-agnostic mount. Every supplier document, invoice and logo in the system is readable by URL alone, forever, by anyone — including after the quote is deleted if the delete's best-effort removal failed. A signed-URL or authenticated-proxy route would close it for all five upload paths at once.


## [APRAS-63] Acabamento da tela de orçamentos — 2026-09-18 (code_review round 2)

- `_sanitise_attachment_filename` is exactly the helper APRAS-65 will want for
  the other five call sites. When that task lands, promote it to a shared module
  (with the type→extension map as a parameter) rather than copying it five
  times. Not a change for this task — the private-classmethod scoping is
  correct precisely because the other sites are *not* fixed yet.
- `ATTACHMENT_EXTENSIONS` and `ATTACHMENT_ALLOWED_MIME_TYPES` are two
  declarations of the same accepted set; the frozenset could be derived as
  `frozenset(ATTACHMENT_EXTENSIONS)`. Minor DRY, and the current form does read
  more explicitly against D2, so either is defensible.

## [APRAS-63] Acabamento da tela de orçamentos — 2026-09-18 (qa_review round 1)

- ER4's wording "the original `attachment_filename`" is satisfied in spirit, not literally: the
  stored display name is the *sanitised* original (`payload.svg` → `payload.png`). That is what
  D1 specifies and it is what makes the security fix airtight; worth keeping in mind only because
  a reader of the expected result alone might expect the byte-for-byte submitted name.
- The corroboration environment was stale during this review: `apras-backend-1` is **not running**
  (`docker ps` shows only `apras-db-1` and `apras-frontend-1`), and whatever answers on
  `http://localhost:8001/openapi.json` does not expose the two new routes. This says nothing about
  the change — the index-materialized run was the authority throughout — but the dev stack needs a
  restart before anyone demos this.

## [APRAS-64] Dinheiro em Decimal/Numeric — 2026-09-18 (code_review round 1)
- `backend/app/models/project.py:121` — `ProjectUpdate.cost_impact` is annotated `Money`
  (which carries `ge=0`), while the request/response schemas for the same value use
  `SignedMoneyIn`/`SignedMoney` (`backend/app/schemas/project.py:92,115`), and
  `app/core/money.py:76` names "a cost impact that is a credit" as the motivating case
  for `SignedMoney`. There is no runtime effect — SQLModel `table=True` classes do not
  validate on assignment, and the read schema is signed — but the table model is the one
  place where the annotation says the opposite of the design note. `SignedMoney` there
  would make the three agree.
- `frontend/src/lib/money.ts:44` — `limitDecimals` picks the separator with
  `Math.max(indexOf("."), indexOf(","))`, i.e. the *last* separator present. This is
  correct for every shape these `type="number"` inputs can produce and for both pt-BR
  and en-US grouped input, but the choice is load-bearing and is not stated in the
  docstring. One sentence would pin it.
- `backend/tests/test_money_typing.py:_numbers_only` flags any JSON string that
  `Decimal()` accepts. `Decimal` also accepts `"nan"`, `"inf"` and `"Infinity"`, so a
  future payload containing one of those words as a plain string field would produce a
  confusing false positive. Excluding non-finite spellings would harden it.
- `inputMode="decimal"` and `min="0"` were added to the money inputs beyond the letter
  of Decision 5 (which only names the guard and `step`). Both are inert widget hints and
  consistent with the spec's own reasoning about `step`; noted only so the widening is
  on the record.

---

# What I reviewed and how

Staged diff: 43 files, +1961/-182 (`git diff --cached --stat`).

Because the task's acceptance condition is "a materialized copy of the index ALONE
passes", I did not test the working tree. I materialized the index with
`git checkout-index -a -f --prefix=<scratchpad>/idx/` (which writes the index's version
of every tracked file, and nothing else), linked in `.venv`/`node_modules`, copied
`backend/.env`, and ran every gate inside that copy. A second identical copy (`mut/`)
was used for mutation testing, and a third (`head/`) materialized from `git archive HEAD`
for the ESLint baseline. The real repository was never modified; `git status --short`
after the run is byte-identical to the one at the start.


## [APRAS-64] Dinheiro em Decimal/Numeric — 2026-09-18 (qa_review round 1)

- `tests/test_migrations_postgres.py::test_a_decimal_round_trips_through_postgres_including_func_sum`
  asserts the round trip with `text("SELECT SUM(total_budget) ...")`, which
  exercises psycopg's numeric adaptation but not SQLAlchemy's `func.sum` result
  processing — the thing its own name promises and the thing
  `finance_service.py:427,433` actually calls. I ran the `func.sum` form myself
  and it returns an exact `Decimal`, so nothing is broken; swapping the raw SQL
  for `select(func.sum(ConstructionProject.total_budget))` would make the test
  cover the code path the service uses.
- `TransactionFormModal`'s amount input keeps `min="0.01"` where the other eleven
  use `min="0"`. That matches the backend's `gt=0` and predates this task, but a
  one-line comment would stop a future reader from "fixing" it into a mismatch
  with the API.

## [APRAS-65] Sanear nome de arquivo em todos os uploads — 2026-09-18 (spec_review round 1)

- ER1's "the `save_file` signature is unchanged" is worth keeping, but consider
  also documenting in `save_file`'s docstring that `filename` is display
  metadata only. Six call sites will keep passing a name that no longer
  influences anything, and the next reader will otherwise re-derive the same
  confusion APRAS-63 did.
- D2 says the shared `sanitise_upload_filename` reproduces APRAS-63's behaviour
  "exactly", but APRAS-63 indexes `ATTACHMENT_EXTENSIONS[content_type]`
  directly and so raises `KeyError` on an unmapped type, while D1 gives
  `canonical_extension` a `.bin` fallback. Today the difference is unobservable
  (the only caller validates first), but the spec should say which of the two
  the shared function does, so the implementer does not have to guess.
- Pre-existing and out of scope, but worth recording somewhere: the `.webp`
  `else` branch at `storage_service.py:56` means extensionless PDF uploads are
  already on disk as `.webp`. They stay inline-safe under the new mount so
  nothing breaks, and D1 fixes it going forward — but no migration touches them.
- `media_service.py:108-112` passes the *original* `mime_type` for the thumbnail
  while the thumbnail bytes may have been re-encoded to JPEG by the
  `save_format` fallback at `:100`. After D1 the on-disk extension follows the
  declared type, so a re-encoded thumbnail could carry a mismatched extension.
  Both types are inline-safe, so this is cosmetic, not a security issue.

## [APRAS-65] Sanear nome de arquivo em todos os uploads — 2026-09-18 (spec_review round 2)

- D5's consequence paragraph should also name the legacy non-canonical-extension
  case (a `.jfif`-named JPEG already on disk now serves as an attachment and
  breaks in an `<img>` tag), so the residual is stated rather than discovered.
- ER 9's "left byte-identical by the whole test suite" reads oddly for a
  database row; "the test re-reads the row and finds `file_url` and `mime_type`
  unchanged" says the same thing without the ambiguity.
- D4/Files-touched: the `test_project_report.py` `storage` fixture will need to
  pass `url_prefix="/static/generated"` as well as `base_dir`, or the rewritten
  URL assertions cannot pass. Worth one clause so the developer does not have to
  rediscover it.

## [APRAS-65] Sanear nome de arquivo em todos os uploads — 2026-09-18 (spec_review round 3)

- ER 8's second clause ("the only occurrences of the literal `static/generated`
  ... are in ...") inherits its directory scope from the sentence's opening "no
  file in `backend/app` or `backend/scripts`". Read without that inheritance it
  would be falsified by artefacts two sibling results mandate: ER 12 requires
  `.gitignore` to list `static/generated/`, and ER 5 requires tests that assert
  on `static/generated` paths. The scoped reading is the only one consistent
  with the list as a whole, so this is not blocking, but repeating the scope
  inside the clause ("the only occurrences ... under `backend/app` and
  `backend/scripts` are ...") would remove the inference a verifier currently
  has to make.
- Consider naming, in the Test criteria, the concrete greps a verifier should
  run for the absence half of ER 8 (file-move calls and `file_url` assignment),
  so round-4 QA does not have to invent them.

## [APRAS-65] Sanear nome de arquivo em todos os uploads — 2026-09-18 (code_review round 1)

- `test_no_module_moves_a_file_between_the_two_trees` greps raw source text for `.rename(`
  across all of `app/` and `scripts/`. A future, entirely unrelated `Path.rename` or a
  dataframe `.rename(` would fail this test with a message that does not explain itself.
  Consider narrowing the scan to modules that also mention `static/`, or asserting on the
  AST rather than the text.
- The five service allowlists compare `content_type` by exact string, so
  `image/png; charset=utf-8` is a 400 rather than an upload. That is fail-closed and fine,
  but `app.core.uploads._normalise` now exists and could be reused at those checks if the
  400s ever prove annoying in the field.
- `media_service` re-encodes the thumbnail to JPEG when Pillow reports a format outside
  `("JPEG","PNG","WEBP")` while still storing it under the declared type's extension, so
  e.g. GIF bytes declared `image/png` yield a `.png` holding JPEG. Harmless here (both are
  inline-safe raster types and `nosniff` is on — it just fails to render), and the spec puts
  sniffing validation out of scope. Worth a line in a future hardening task.
- `Content-Disposition: attachment` carries no `filename=` parameter, so the browser names
  the download after the UUID in the URL. Correct and safest; a `filename*=` derived from a
  persisted display name would be friendlier if that ever matters.
- `HardenedStaticFiles.__init__(self, *args, force_download: bool = False, **kwargs)` is
  untyped on the passthrough. Both call sites use keywords only; a narrower
  `(self, *, directory: str, force_download: bool = False)` would document the contract.

## [APRAS-65] Sanear nome de arquivo em todos os uploads — 2026-09-18 (qa_review round 1)

- `Content-Disposition: attachment` carries no `filename=` parameter, so a downloaded legacy file lands under its UUID name. Harmless for the security property; only a UX nicety if these ever get downloaded in anger.
- `save_file` will still mint `.html` for a caller that passes `text/html`, which is only safe because the two generators that do so use the generated-tree provider and no user-facing allowlist admits that type. An assertion in `LocalStorageProvider` that `text/html` is only accepted when `url_prefix` is the generated one would make that invariant local rather than a property of the call graph.

## [APRAS-66] Slug do condomínio — 2026-09-21 (spec_review round 1)

- **Collision-suffix overflow is undefined.** Base is capped at 60 and the
  column is `VARCHAR(64)`, so `-2` … `-999` fit and `-1000` (65 chars) does
  not. Practically unreachable, but the rule is stated as total; one sentence
  (truncate the base further, or let the bounded retry fail loudly) closes it.
- **Name both `AGENTS.md` places.** The spec's Files-touched row says "the
  migration section". Besides `AGENTS.md:161-166`, `AGENTS.md:1009-1012`
  ("Migrating an existing install") asserts the history is a single
  `0001_initial_schema`; that paragraph also needs the update.
- **Also stale prose:** the `test_migrations_postgres.py` module docstring
  (lines 1-28) and the `assert_no_skips.py:22-29` comment both narrate a
  one-revision history.
- **Say that `test_tenant_context.py` / `test_tenant_models.py` are
  deliberately untouched** — both read `0001` by `ast`, but only for
  `_TENANT_SCOPED_TABLES`, and `tenant` is not scoped. A reader of the spec
  will otherwise assume they were missed.
- **Garbled sentence in Test criteria:** "the third is created after the
  second is deleted-free — the smallest free integer, not a counter" does not
  parse. State the actual case (delete `x-2`, create a fourth tenant, expect
  `x-2` back) or drop the clause.

## [APRAS-66] Slug do condomínio — 2026-09-21 (spec_review round 2)
- D-E slightly recontextualises `0001`'s shadowing note. In `0001` that comment
  explains why *tests* read `_TENANT_SCOPED_TABLES` out of the file with `ast`
  instead of importing it; D-E cites it as a reason a migration should not
  import. Both are consequences of the same packaging fact and the sentence is
  not false, but the implementer may find the original comment does not say
  quite what D-E implies it says. Not blocking.

## [APRAS-66] Slug do condomínio — 2026-09-21 (spec_review round 3)

- D-A/D-B: state the suffix budget explicitly — the base is truncated so that
  base + `-<n>` stays within 64. At 60 characters of base the walk fits up to
  `-999`; `-1000` is 65 characters and would hit the column. Unreachable in
  practice (999 tenants sharing one 60-character base), but naming the
  invariant costs one clause and removes a latent `DataError`.
- D-C.2 says `PATCH /api/v1/tenants/{id}` changes `slug` "only when `slug` is
  present in the request body", while D-D exposes `slug` for writing on
  `TenantProfileUpdate` only and the files table changes
  `backend/app/schemas/tenant.py` accordingly. The two read consistently if
  `TenantUpdate` never carries `slug`, but saying so in one clause would stop
  an implementer adding a second, superuser-facing write path with its own
  validation and collision semantics.
- The "own current slug is a no-op" rule would read more precisely if it said
  the comparison is against the stored value *before* validation ordering is
  decided — see the blocking finding; whichever way that is resolved, fixing
  the order explicitly is cheap.

## [APRAS-66] Slug do condomínio — 2026-09-21 (spec_review round 4)

- **Trim the base to fit the suffix (non-blocking, refinement).** The
  generated path could exceed the 64-character column if a base truncated to 60
  characters ever needed a suffix of `-1000` or higher (65 characters). This is
  not a genuine correctness problem at any plausible scale — it needs 999
  tenants sharing one 60-character base, and it fails loudly rather than
  storing something wrong — but a one-line guarantee in the producer ("shorten
  the base so base + suffix stays <= 64") removes the edge for free. A
  competent developer would settle this at implementation time; it does not
  warrant spending round 5.
- The `MIN_CASES` re-pin criterion adds a migration test case (the
  two-character backfill row); the "measured, not counted by eye" instruction
  already covers it, so no change needed — just noting the count moves for a
  second reason now.

## [APRAS-66] Slug do condomínio — 2026-09-21 (code_review round 1)

1. **`slugErrorKeyOf` can misattribute a *name* 409 to the slug field.**
   `frontend/src/features/user-administration/pages/TenantProfilePage.tsx:68-74`
   maps any error on a slug-carrying submit by status alone. When the person
   changes the **name** and the **slug** in the same Save and the *name*
   collides, the server answers 409 (`TenantAlreadyExistsError`) and the UI
   renders `tenantProfile.errors.slugTaken` beside the slug field — the wrong
   field and the wrong sentence. The repo-wide `{"detail": ...}` envelope is
   what makes the two 409s indistinguishable by status. Cheapest fix without
   touching the envelope: when both fields changed, fall back to the
   page-level banner (`errorKeyOf`) for 409 and keep the field-level message
   only for a slug-only change. Non-blocking: the spec's own test criteria
   only exercise the slug-only path, and the message is wrong rather than the
   write.

2. **`slugifyName` and `slugify` diverge on ASCII control characters.**
   `frontend/src/api/tenantProfile.ts:64-67` strips everything outside
   `[\x20-\x7e]`, so a tab or newline in the name vanishes; Python's
   `slugify` (`backend/app/core/slug.py:76-79`) keeps them through
   `encode("ascii", "ignore")` and the separator run turns them into a `-`.
   `"a\tb"` therefore suggests `ab` in the browser and would derive `a-b` on
   the server. Only the "suggest from name" affordance is affected, both
   outputs satisfy `is_valid_slug`, and the server never folds a typed value,
   so nothing can be stored wrong. Replacing the strip with a fold to `-`
   would close it.

3. **`update_profile` writes the name and the slug in two commits.**
   `backend/app/services/tenant_service.py` — `update_profile` delegates the
   name to `update_tenant` (which commits) and then calls `_write_slug`
   (which commits again). Both slug *checks* do run before any write, as the
   docstring says, but on the race path the `IntegrityError` in `_write_slug`
   surfaces as 409 **after** the name change has already been committed. The
   docstring's "a refused slug stores nothing -- not even the name that rode
   along with it" is exact for the 422/409 pre-check paths and slightly
   optimistic for the race. Either narrow the sentence or wrap the pair in
   one transaction.

4. **`Tenant.slug` carries `default=""`.** `backend/app/models/tenant.py`
   — `__init__` always fills an absent slug, so the default is unreachable
   through construction, but a future `Tenant.model_construct(...)` or a
   direct ORM path that bypasses `__init__` would get `""`, which is
   `NOT NULL`-clean and uniquely indexable exactly once. Nothing in the tree
   does this today (grepped: no `Tenant.model_validate`, no
   `Tenant.model_construct`, no `Tenant(**...)`), so it is latent only.

5. **Spec erratum worth recording.** See "Developer flags" below: the spec's
   test-criteria line listing `"A. B"` as an under-floor name contradicts
   D-A's own steps. Amending that parenthetical in
   `docs/tasks/APRAS-66-spec.md:247` would stop the next reader from
   re-litigating it.

---


## [APRAS-66] Slug do condomínio — 2026-09-21 (qa_review round 1)
- `tenant.slug` has a unique index but no `CHECK` constraint for the 3-64 / character rule. Every
  application path is covered (I could not break it through one), but a future `psql` hotfix or an
  out-of-band script could still write `AB`. A `CHECK (slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$' AND
  char_length(slug) BETWEEN 3 AND 64)` in a later revision would make the database itself the last
  judge. Non-blocking: nothing in the expected results asks for it.
- `TenantService.create_tenant` exhausting `SLUG_INSERT_ATTEMPTS` raises `SlugAlreadyTakenError`,
  which the handler maps to 409 — a reasonable status, but the message names a slug the caller
  never typed. A distinct exception (or a message about retrying) would read better in that very
  rare path. Non-blocking.

## [APRAS-68] Whitelabel — 2026-09-21 (spec_review round 1)

- The 0.01 step loop is dead code for the vast majority of inputs (needed at
  only 3,445 of 120,888 domain points) because the `L ∈ [0.20, 0.92]` clamp
  already guarantees the bar almost everywhere. Worth a sentence in
  `branding.py` noting this so a future reader does not mistake it for the
  primary mechanism, and worth ensuring the hostile-input test includes at least
  one colour that actually *exercises* the loop — every colour in the current
  set clears 4.5:1 at zero steps, so the loop is untested by the stated set.
  A mid-lightness low-chroma colour near `oklch(0.56 0.04 165)` does exercise it.
- Step 4 gives `--ring` the *effective* (contrast-adjusted) primary. For a very
  pale brand the adjusted primary moves dark, which is fine on `--background`,
  but for a very dark brand in light mode it moves lighter and the focus ring
  can lose contrast against `--background`. Focus indicators have their own
  WCAG requirement (1.4.11, 3:1 against adjacent colours). Not blocking for this
  task's stated ERs, but worth a follow-up.
- On the dark derivation: it is cheap and ER-4 asks for it, so keep it. But
  since nothing can apply `.dark` today, the emitted dark block is unverifiable
  in the running app and its contrast guarantee rests entirely on
  `test_branding.py`. Whoever eventually turns dark mode on should re-check it
  against real rendering rather than trusting it has been exercised.
- `docs/tasks/APRAS-68-mock.html` is in Portuguese. That is correct for a UI
  mock (it shows operator-facing copy) and the spec itself is correctly in
  English, so this is not a language-policy finding — noting it only so the
  point is not re-raised later.

## [APRAS-68] Whitelabel — 2026-09-21 (spec_review round 2)
- Step 4 does not say whether the foreground candidate is re-evaluated on each
  loop iteration. Verified inert (0 divergences over 604,440 lattice points),
  but one clause saying "the foreground chosen at the first pick is kept for
  the rest of the loop" would remove the reader's doubt.
- Worst emitted ratio across the whole emittable lattice is 4.500004 — the
  algorithm is correct but has no headroom by construction. If any future
  change to rounding, gamut clamping or the foreground candidates is
  anticipated, raising the loop's exit threshold to e.g. 4.55 would buy margin
  at no visible cost. Alternatively, state explicitly that the contrast test
  uses `app.core.branding`'s own contrast helper, so an implementation that
  lands exactly on the bar can never fail its own assertion.
- Test criteria say `#857046` light is pinned "at ... 4.59"; the measured value
  is 4.5959. Either write 4.596 (as step 4 already does) or drop the figure and
  keep only the emitted-pair pin.
- Because rounding now precedes the loop, the emittable primary set is a finite
  lattice of 73 × 23 lightness/chroma points per hue. A test that sweeps that
  lattice (or a coarse slice of it) would prove ER-4 for all inputs rather than
  for a hostile set of eight; it runs in seconds in pure Python.

## [APRAS-70] Tela de criação de condomínio — 2026-09-21 (spec_review round 1)

- D5 is right that `is_active` is read-only here, but no frontend surface calls
  `PATCH /api/v1/tenants/{id}` at all today (only `/modules` and the
  `/subscription` family exist in `frontend/src/api/`). Worth one sentence in
  D5 saying the badge and the status filter are, for now, reflecting a flag
  only the API can set — otherwise the first reader of the shipped screen will
  file "the filter never does anything" as a bug.
- D6 says a 409 "does **not** invalidate the list", and test criterion 4 phrases
  the same thing as "does not call the list query again". The second wording is
  weaker (a refetch can happen for unrelated reasons); consider asserting on
  `queryClient.invalidateQueries` not being called with `["tenants"]`, matching
  the positive assertion in criterion 3.
- The spec pins `iconName: "Hotel"` in "Files touched" but expected result 1
  only requires that the name exist in `ICON_MAP`. Fine as is; just note that
  `Landmark` is already taken by `/admin/tenant-profile`, so reusing it would
  make the two administration entries visually identical.
- The mock depends on `cdn.tailwindcss.com` and `unpkg.com`; if "opens
  standalone" is ever meant to include offline, that convention needs changing
  repo-wide, not here.

## [APRAS-70] Tela de criação de condomínio — 2026-09-21 (spec_review round 2)

- `expect(navItemPaths).toHaveLength(NAV_ITEMS.length)` is a tautology once
  `navItemPaths` is `NAV_ITEMS.map(…)` — it can never fail. Keeping it is
  harmless and arguably documents the shape, but the assertion doing the work
  is the one on `allGroupPaths`; consider dropping the first and keeping
  `allGroupPaths`, `uniqueGroupPaths.size` and the sorted `toEqual`.
- The `toBeGreaterThanOrEqual(31)` floor decays: at 40 nav items it tolerates
  nine deletions. If the project wants a guard that keeps its strength, the
  durable form is asserting against a snapshot of the path set rather than a
  count — but that is a repo-wide test-convention decision, not this task's.
- `GeneralDashboardPage.test.tsx:38-45`'s `actingTenant` literal already has
  `created_at` but no `slug`, and survives only because of `as never`. Not this
  task's problem, but if the cast is ever removed that fixture is the next one
  to break.

## [APRAS-71] Backend do convite — 2026-09-21 (spec_review round 1)

- Consider `hmac.new(settings.SECRET_KEY, raw_token, "sha256")` instead of a bare
  `sha256`, for domain separation and so a read-only database dump is not by
  itself enough to verify a guessed token offline. It keeps the indexed equality
  lookup, so it costs nothing D1 relies on. Bare SHA-256 is defensible at 256 bits
  and I am not blocking on it — but the spec's D1 could say it considered and
  declined the pepper rather than leaving the reader to wonder.
- Note in D10/D11 that the `RESEND_API_KEY`-absent fallback prints a **7-day
  credential conferring `is_tenant_admin`** to stdout, where `forgot_password`
  printed a 15-minute JWT. Same mechanism, materially different blast radius on a
  misconfigured production deploy.
- `tests/test_password_recovery.py` contains no stdout assertion at all (verified:
  no `capsys`, no `[AUTH]`, no `RESEND`), so "passes unedited" does not actually
  protect D10's byte-for-byte print claim. Pin the two `[AUTH]` lines in
  `tests/test_mail.py` if the claim is meant to be enforced.
- `test_migrations_postgres.py` derives `EXPECTED_HISTORY` from `HEAD_REVISION`
  (`:58`, `:63`), so the edit is "move `HEAD_REVISION` and extend the tuple", not
  "`EXPECTED_HISTORY` gains the new revision". Restate it that way.
- Two test function names encode the old numbers and will read as lies after the
  change: `test_unguarded_allowlist_is_twenty_four_routes`
  (`test_permission_registry.py:160`) and `test_allowlist_is_twenty_eight_routes`
  (`test_tenant_route_scope.py:129`). Renaming them does not move any count.
- `NOQA_CAP` headroom is exactly **2** (measured: 67 effective `# noqa` under
  `app/` + `tests/`, cap 69, self-excluded). The two rate-limited public handlers
  each need slowapi's unused `request: Request` with a `# noqa: ARG001`, which
  consumes the entire headroom. Worth naming in the spec so the implementer does
  not spend a round discovering it.

## [APRAS-71] Backend do convite — 2026-09-21 (spec_review round 2)
- The "Files touched" bullet for `test_migrations_postgres.py` says
  `EXPECTED_HISTORY` gains the new revision but does not mention
  `HEAD_REVISION` (:58), which :318 and :331 also use. The file's own comment at
  :55-56 says a new revision moves both, so it is mechanical, but naming it would
  remove a step the implementer has to infer.
- D8 enumerates the `InvitationPreview` fields as email, tenant name, slug,
  `expires_at`, `account_exists`, while the Approach section's preview bullet also
  lists the inviter's full name. Same schema, so one enumeration is just shorter;
  making the two lists identical would avoid a reviewer asking about it later.

## [APRAS-72] UI do convite — 2026-09-21 (spec_review round 1)

- D7 should say in one clause that the **re**-preview reuses the same D7 mapping in full, so a
  `410` or `404` answer to it lands on the expired / invalid terminal state rather than leaving
  the form open.
- ER9's "no copy claims the person is signed in" is the one clause a machine cannot check.
  Pair it with two mechanical assertions that mean the same thing: the `AuthContext.login` spy
  is never called, and `navigate` is never called with `/`.
- APRAS-71 never enumerates `InvitationRead`'s fields (only the table columns) nor the field
  names inside `InvitationPreview`. This spec commits to `created_at` on `InvitationRead` (the
  panel's "sent date") and to `inviter_name` / `tenant_name` / `tenant_slug` on the preview.
  Worth one sentence saying these names are the contract, so APRAS-71's implementation is held
  to them rather than APRAS-72 discovering a mismatch.
- D4 notes resend is out-of-the-box supersession; consider saying whether the resend action is
  disabled while its mutation is pending, to avoid two superseding issues from a double click.

## [APRAS-72] UI do convite — 2026-09-21 (spec_review round 2)

- Expected result 7 ends "and chooses its branch from `account_exists`". In
  context ("before any input is requested") this plainly means the form choice,
  and result 9 removes any doubt, but "chooses which form to render from
  `account_exists`" would make the two results impossible to read against each
  other.
- In the `200`-in-`false`-branch crossing the visitor has just typed a password
  that was never used, and the terminal panel says "sign in with your current
  password". Consider a sentence of copy guidance acknowledging the discarded
  input, so the implementer does not invent reassurance text of their own.
- The mock shows both branches and the error states; it does not depict the
  crossing outcome. Not required by result 14, but a fourth acceptance-page
  state in the mock would let a reviewer see the panel the crossing produces.

## [APRAS-73] Orçamento com vários itens — 2026-09-21 (spec_review round 1)

- Generalise `test_the_slug_revision_imports_nothing_from_app`
  (`backend/tests/test_migrations_postgres.py:322`) to loop over every entry
  in `EXPECTED_HISTORY` and rename it accordingly. As written it parses only
  `HEAD_REVISION`, so this task's revision inherits the assertion and `0002`
  quietly loses it. APRAS-71 D12 already proposes the same generalisation —
  whichever lands first should do it.
- `EXPECTED_HISTORY = (ROOT_REVISION, HEAD_REVISION)` (line 63) currently
  derives the whole history from two constants; with a third revision it has
  to become an explicit three-tuple. Worth one line in Files Touched so the
  developer does not mistake it for a pure `HEAD_REVISION` edit.
- D3 quantizes the sum of already-quantized line totals ("quantized once
  more on the way out"). That second quantization is a no-op over exact
  cents; keeping it is harmless and defensive, but a sentence saying it is
  deliberately redundant would stop a later reader from removing it as dead
  code — or from assuming it rounds something.
- Consider stating in D10 that the backfilled description is expected to
  read redundantly against its request's title, and that the operator's
  first edit of the quote replaces it. It is the right choice, but the
  reasoning deserves to survive the first "why does this say the same thing
  twice?" from a user.

## [APRAS-73] Orçamento com vários itens — 2026-09-21 (spec_review rounds 2-3)

- Pin the docstring assertion to a substring (e.g. that `downgrade.__doc__`
  contains "perda"/"lossy" and "backup"), so the test cannot pass on a
  docstring that merely exists.
- D2's frontend clause "and their tests" is correct but implicit; naming
  QuoteFormModal.test.tsx, QuoteComparisonTable.test.tsx and
  SelectQuoteModal.test.tsx would make the 26 fully explicit.
- The mock's annotation callouts are in Portuguese while the spec is English.
  This matches the mock convention used across APRAS-68/70/72 and the language
  policy targets specs and technical docs, so it is not a finding — but if the
  mock annotations are ever treated as spec text (as B3 effectively did, since
  a wrong callout would have misled the implementer), keeping them in English
  would remove one class of spec/mock drift.
- ER 7 says "each cell carrying that supplier's item count and lines" without
  naming the `N itens` / `1 item` singular-plural form that the Test Criteria
  and the mock both use. A QA agent holding only `expected_results` would pass
  a cell reading `3` instead of `3 itens`. Non-blocking (the result is still
  mechanically verifiable), but tightening the wording at the next touch would
  close the gap.

## [APRAS-70] Add superuser-only condominium creation screen — 2026-09-21

1. **`useTenants` duplicates an existing hook.**
   `frontend/src/hooks/useTenants.ts:13-14` is
   `useQuery({ queryKey: ["tenants"], queryFn: listTenants })`, which is
   character-for-character what `useAllTenants` already is at
   `frontend/src/hooks/useTenantModules.ts:19-20`. There is no behavioural
   risk — both resolve to the same cache entry, so they cannot disagree — but
   the project now has two names for one query, and a future reader changing
   one will not find the other. The spec's "Files touched" did prescribe the
   new file (and `useCreateTenant` needs a home), so this is not a deviation;
   the tidy follow-up is to delete `useAllTenants`, move its one consumer to
   `useTenants`, and leave `useTenants.ts` as the single owner of the
   `["tenants"]` list query. Non-blocking.

2. **D3's hint is a page footer, not "next to the slug".** D3 says the list
   states *next to the slug* where the address is edited;
   `TenantsAdminPage.tsx:361-363` renders `tenantsAdmin.slugEditHint` as a
   paragraph below the whole table. The information is on the screen and the
   substantive half of D3 (no slug edit, no auto tenant switch) is fully
   honoured, so this is placement, not behaviour. If the mock shows it under
   the slug column header, moving it there — or into the column header's title
   attribute — would match D3's wording more literally.

3. **`expect(navItemPaths).toHaveLength(NAV_ITEMS.length)` is a tautology.**
   `navItemPaths` is `NAV_ITEMS.map(...)`, so that assertion
   (`routeAccess.test.ts:103`) can never fail. It is harmless and it is what D8
   literally prescribed, but the *load-bearing* version of the same idea is the
   one on the next lines — `allGroupPaths` and `uniqueGroupPaths` compared
   against `NAV_ITEMS.length` — which do catch omissions and duplicates.
   Dropping the tautological line would lose nothing. Explicitly a
   disagreement with D8's letter, hence a suggestion rather than a finding.

4. **The loading state is text, not a spinner.** The Approach section says "a
   spinner while the query is pending"; `TenantsAdminPage.tsx:293` renders
   `<p>{t("tenantsAdmin.loading")}</p>`. Functionally equivalent and arguably
   better for screen readers; flagging only so nobody reads it later as an
   oversight.

5. **`copied` is set optimistically.** `copySlug` (`:127-131`) calls
   `setCopied(true)` without awaiting `writeText`, so a rejected clipboard
   write (permission denied, insecure context) still shows "Copied". A
   `.then(() => setCopied(true))` with a `catch` would be truthful. Very minor,
   and the current form is what keeps the code synchronous and easy to test.

6. **The table header renders with an empty body when filters match nothing.**
   `all.length > 0` gates the table and `rows.length === 0` gates the
   `noResults` message (`:298`, `:355`), so a non-matching filter shows column
   headers above nothing, then the message. Rendering the message *inside* a
   full-width `<td>` row would read slightly better, and matches what the spec
   calls "an empty-state row". Cosmetic.

## [APRAS-70] Add superuser-only condominium creation screen — 2026-09-21

- `expect(navItemPaths).toHaveLength(NAV_ITEMS.length)` (routeAccess.test.ts:102) is now
  a tautology — `navItemPaths` is `NAV_ITEMS.map(...)`, so it can never fail. The
  expected result asks for exactly this shape, so it is correct as delivered; if the file
  is touched again, that one line could be dropped without losing any invariant, since
  the real coverage check is `allGroupPaths.length === NAV_ITEMS.length` plus the sorted
  set equality.
- The file still carries `expect(paths.length).toBeGreaterThan(20)` at line 38 from an
  earlier task — the same kind of hard-coded board size the APRAS-70 D8 comment argues
  against. Out of scope here; worth folding into the next edit of that test.
- `frontend/src/api/tenants.ts` `createTenant` takes an inline `{ name: string }` literal
  while the page and hook pass the same shape around. A named `TenantCreatePayload` type
  would give the three call sites one declaration to change when APRAS-72 extends the
  create body.
- The 409 detection in `isDuplicateName` reaches into `(error as { response?: { status?:
  number } })`. `parseApiError` already normalises axios errors elsewhere in the
  codebase; exposing a small `httpStatus(error)` helper next to it would keep that cast
  in one place rather than growing a copy per screen.

## [APRAS-76] Fix the default theme's muted text contrast, which is below WCAG AA — 2026-09-21
- *Test criteria* claims "all 19 dark pairs (worst `--muted-foreground` on
  `--muted`, 5.3726)". The dark worst is actually
  `--destructive-foreground` on `--destructive` at **5.1359**; the muted pair
  is 5.3726 as stated, just not the minimum. Everything still passes, and the
  test derives its own pairs so nothing downstream depends on the sentence, but
  the number is wrong in a spec whose credibility rests on its arithmetic.
- Expected result 6 says "`git diff --name-only` lists exactly ...". The
  working tree currently carries ~30 unrelated modified/untracked files
  (APRAS-71 invitations, other spec/mock files), and QA receives only the
  `expected_results`, never this context — run literally, that command will
  list everything and fail a correct implementation. Consider phrasing it as
  "the commit for this task touches exactly these two files" (verifiable with
  `git show --name-only`), which is just as mechanical and not hostage to a
  dirty tree.
- The 0.01-grid chroma walk is an approximation of CSS Color 4 §13, which
  specifies a binary search on chroma with a deltaE-OK ≤ 0.02 clip. The spec's
  algorithm is fully specified and unambiguous, and the difference does not
  move any pair across 4.5, but expected result 1's wording ("after CSS Color 4
  §13 chroma-reduction gamut mapping") overstates the fidelity. Calling it
  "§13-style chroma reduction on the authored 0.01 grid" would describe what
  the test actually does.
- The ~40-line oracle deliberately duplicates what APRAS-68's
  `frontend/src/lib/contrast.ts` will contain. The independence argument is
  good, but the two can drift silently. Worth a one-line note in the test file
  pointing at the other module so whoever lands second sees the choice.
- Consider having the test assert the two repaired values themselves
  (`--muted-foreground: oklch(0.53 0.02 160)`, `--primary-foreground:
  oklch(0.15 0.02 160)`), not just the ratios. The ratio assertion already
  catches a regression, but naming the value makes the failure message point at
  the fix rather than at the arithmetic.

## [APRAS-76] Fix the default theme's muted text contrast, which is below WCAG AA — 2026-09-21
- *Test criteria* says `git diff --stat` while expected result 6 says
  `git diff --name-only`. They agree in substance; using one command in both
  places would remove a needless diff between the two documents.
- Step 3's phrase "within `[0, 1]` (tolerance 1e-4)" is two-sided in my reading
  and the 0.15 → 0.14 pin confirms it, but writing `[-1e-4, 1 + 1e-4]` would
  make it unmistakable without relying on the pin.

## [APRAS-68] Whitelabel: cores da marca do condominio no perfil e no app — 2026-09-22
- `backend/app/services/tenant_service.py:593-602` — `update_profile` commits in
  three steps (`update_tenant`, then `_write_brand_theme`, then `_write_slug`).
  A `SlugAlreadyTakenError` raised by the last step leaves an already-committed
  brand theme behind while the request fails. This mirrors the pre-existing
  name-then-slug behaviour rather than introducing it, so it is not a new defect,
  but one transaction for the whole profile PATCH would close the whole class.
- `frontend/src/lib/contrast.ts:307-317` — `auditHexPalette` rounds to 2dp via
  `formatOklch` but does not replicate the backend's 0.01-grid chroma snap
  (`branding.snap_to_gamut`) before measuring, so a borderline out-of-gamut
  authored palette can pass the client check and still be refused by the server.
  The design already handles that (the 422 body is rendered verbatim, and a test
  covers it), but one sentence in the module docstring naming this specific
  divergence would stop a future reader treating a mismatch as a port bug.
- `frontend/src/features/user-administration/components/TenantBrandColors.tsx:598-603`
  — the green "all pairs pass" banner renders in simple mode, where by design
  nothing was measured client-side. Consider a mode-specific string so the
  reassurance states the actual reason ("simple mode cannot fail by
  construction") instead of implying a measurement that did not run.
- `backend/app/core/branding.py:93` — `EMITTED_KEYS = (*AUTHORED_KEYS,
  *DERIVED_FROM)` relies on unpacking a dict to its keys. `*DERIVED_FROM` is
  correct but reads as an oversight; `*tuple(DERIVED_FROM)` or
  `*DERIVED_FROM.keys()` says it outright.
- `backend/tests/test_branding.py` — the `_brand_surface` helper imports
  `derive_brand_surface` inside the function body while every other symbol is
  imported at module level. Moving it up would remove the "why is this one
  different?" question.
- Process note, not a code change: `tests/test_migrations_postgres.py` skipped
  all 36 cases here for want of Postgres on 55432, and diff-scoped `eslint`
  could not be invoked in this session. Both need to be green in QA/CI before
  this merges; `MIN_CASES = 36` is exact, so any change to that module's case
  count will trip `assert_no_skips`.

## [APRAS-68] Whitelabel: cores da marca do condominio no perfil e no app — 2026-09-22 (QA)
- **The injected dark selector is `:root:root.dark`, while `index.css` declares
  a bare `.dark`.** Today nothing applies the class — there is no `classList`
  call anywhere in `frontend/src` — so the two cannot disagree. But the day a
  dark-mode toggle ships, if it puts `.dark` on `<body>` or on a wrapper `<div>`
  (a common shadcn pattern) rather than on `<html>`, `index.css`'s rule will
  apply and the tenant's will silently not. Worth a one-line comment in the
  toggle task, or emitting `:root:root.dark, :root:root .dark` when it lands.
- **`oklch(0.98 0 0)` in the spec prose is emitted as `oklch(0.98 0.00 0.00)`.**
  `format_oklch` always writes 2 decimals, which is what the expected results
  require and is valid CSS, but the spec's literal pins (`over oklch(0.98 0 0)`)
  do not match the bytes. Aligning the prose with the emitter would save the
  next reader the double-take I had.
- **`frontend/src/lib/contrast.ts` exports rather more than "the ratio function
  and the gamut predicate".** It also carries `gamutMap`, `hexToOklch`,
  `oklchToHex`, `formatOklch`, `auditScheme` and `auditHexPalette`. None of them
  is a *derivation* — the module cannot build a theme, and `contrast.test.ts`
  explicitly asserts that no export is named `buildTheme` / `deriveScheme` /
  `repairSurface` / `repairText` — so the "one derivation in the repository"
  contract APRAS-74 depends on is intact. But the spec sentence that says
  "contains the contrast ratio function and gamut predicate only" is now
  narrower than the file, and APRAS-74's reviewer will read that sentence.
- **Advanced mode's `"dark": null` fallback is fed the authored `accent`, not
  the authored `secondary`.** The code says so, at length, and the choice is
  defensible (it is what makes the scheme byte-identical to the simple
  derivation, which is the stated contract). It is still surprising: in advanced
  mode `accent` is the pale hover tint, so a derived dark `--secondary` comes
  out near the tint's lightness rather than at the brand's chroma. Nothing
  renders it today. When the dark-mode toggle ships, this is the first thing to
  re-decide.
- **A throwaway container `apras-qa68-pg` (port 55433) is still running.** I
  could not stop it — the sandbox refused `docker stop`/`docker kill`. It holds
  nothing but the migration test's own schema and can be removed with
  `docker kill apras-qa68-pg` (it was started with `--rm`). The pre-existing
  `apras-pgtest73` on 55432 was deliberately left alone.
- **`eslint` could not be executed from this review sandbox** (the shell wrapper
  refused every invocation form: `npm run lint`, `npx eslint`,
  `./node_modules/.bin/eslint`, `node node_modules/eslint/bin/eslint.js`). I
  therefore have no first-hand reading of the "375 errors + 2 warnings"
  baseline. This is not treated as a finding: `.github/workflows/ci.yml` has no
  eslint job — the frontend gates are `npm run build` and `npm run test:coverage`,
  both of which I ran and both of which pass — so nothing that CI enforces is
  unverified. Flagging it only so the gap in *this* report is explicit.

## [APRAS-76] Fix the default theme's muted text contrast, which is below WCAG AA — 2026-09-22

- `frontend/src/__tests__/themeContrast.test.ts:104` — `gamutMap` reduces chroma
  on a 0.01 grid, whereas the production measurement
  (`frontend/src/lib/contrast.ts`, and `backend/app/core/branding.py`) uses the
  JND bisection CSS Color 4 §13 actually specifies. For the shipped palette the
  two agree on the snapped chroma (0.14) and differ by only ~0.004 in the
  resulting ratio, so nothing is at risk today. But a future out-of-gamut
  surface landing within ~0.01 of 4.5 could pass this guard while the product's
  own checker rejects the same palette. Worth one sentence in the header noting
  the grid is deliberately coarser and conservative, or — when the two files are
  eventually unified, as the header already contemplates — adopting the
  bisection.
- `frontend/src/__tests__/themeContrast.test.ts:196` — `MINIMUM_PAIRS` is used
  in `it("declares both schemes")` as a floor on the *token count*
  (`Object.keys(light).length`) and elsewhere as a floor on the *pair count*.
  The two happen to share the number 19 but not the meaning; a second constant
  (`MINIMUM_TOKENS`) would keep the assertion honest if either floor moves.
- `frontend/src/features/user-administration/components/TenantBrandColors.tsx:62-79`
  — `DEFAULT_PALETTE`'s comment claims it is "today's `index.css` light scheme",
  and two of its entries are now stale: `"primary-foreground": "#fafafa"` (the
  token is now `oklch(0.15 0.02 160)` ≈ `#040e08`) and `"muted-foreground":
  "#6b7772"` (now `oklch(0.53 0.02 160)` ≈ `#627068`). That file is explicitly
  out of this task's scope and the mismatch is pre-existing — the advanced-mode
  starting palette already seeded white-on-emerald, which already failed the
  live check — so this is not a finding against APRAS-76. It is a good candidate
  for the follow-up task the spec's *Out of Scope* section already anticipates
  (alongside `text-primary` as body text at 3.3114 on `--background`), since the
  drift is now larger and more visible.

## [APRAS-76] Fix the default theme's muted text contrast, which is below WCAG AA — 2026-09-22

- **Frontend lint is red on `master` and CI does not catch it.** ~200 eslint
  errors across ~40 files, and `.github/workflows/ci.yml` runs only `build` and
  `test:coverage` for the frontend. Worth its own cleanup card plus adding
  `npm run lint` to the `frontend` CI job, otherwise the debt keeps growing
  invisibly and every future task inherits an ambiguous "lint must be green"
  acceptance criterion.
- **`destructive-foreground` on `destructive` is the thinnest pair in the
  theme** at 4.5425:1 light / 5.1359:1 dark. It passes, but a future 0.01 nudge
  to `--destructive` would break AA. Consider a source comment there like the
  two this task added for `--muted-foreground` and `--primary-foreground`, so
  the next editor sees the margin before moving the value.
- **`MINIMUM_PAIRS = 19` is exactly today's pair count**, so the
  `toBeGreaterThanOrEqual` floor is sitting on the boundary. That is fine and
  intentional as an anti-vacuity floor, but if a future task removes a token
  pair the count silently drops below and the failure will read as a parser
  bug. A short comment to that effect, or deriving the floor from the token
  count, would age better.
- **The suite deliberately does not import `src/lib/contrast.ts` (APRAS-68).**
  The reasoning in the file header is sound — an independent oracle is what
  makes the green run evidence — but it does mean two OKLCH implementations now
  live in the repo and can drift. If they are unified later, pin both halves, as
  the header itself already says.
- **Pair coverage is background-surface only.** `--primary` and `--ring` used as
  *text* or as focus indicators against `--background` are not enumerated by the
  naming convention. Out of scope for this card and not part of the expected
  results, but a plausible follow-up if non-text contrast (WCAG 1.4.11) is ever
  in scope.

## [APRAS-86] Build the load-reproduction harness and fix the failures it reproduces — 2026-09-23

- `frontend/src/features/user-administration/__tests__/TenantProfilePage.brand.test.tsx:160-178`: the
  long docblock explaining the ~98-keystroke problem, the two options tried and which one sufficed is
  attached to `hexField` (:179), but it describes `typeHex` (:184). As written, the file's most
  important explanatory comment documents the wrong symbol — a reader jumping to `typeHex` sees no
  rationale, and a reader of `hexField` sees a rationale for something else. Move it onto `typeHex` and
  leave `hexField` with a one-line comment.
- `frontend/scripts/load-test.sh:58`: `trap cleanup EXIT INT TERM` runs cleanup but never exits, so a
  SIGINT directed at the script's own pid (as opposed to a terminal Ctrl-C, which signals the whole
  process group) does not abort the run and the script still exits 0. Measured: hogs were still up five
  seconds after `kill -INT`, the suite ran to completion, exit status 0. Consider
  `trap 'cleanup; exit 130' INT` and `trap 'cleanup; exit 143' TERM`, keeping the bare `trap cleanup EXIT`.
- `frontend/scripts/load-test.sh:80-84`: `SUITE_PIDS` collects the *subshell* pid, not the `npx`/`vitest`
  pid, so `kill "$pid"` in cleanup relies on the signal reaching the grandchildren. It did in my SIGTERM
  test (0 surviving vitest processes), but that is npx's propagation doing the work, not the script's.
  Killing the process group, or `pkill -P "$pid"` before killing the subshell, would make the guarantee
  the script's own.
- `frontend/src/features/user-administration/__tests__/TenantProfilePage.brand.test.tsx:190-191`: add a
  one-line comment that `await user.clear(field)` is retained deliberately — it is the remaining
  userEvent call that enforces the disabled/readonly/interactability checks that a bare
  `fireEvent.change` bypasses. Without the note, a future reader may reasonably read the `clear` as
  redundant with the one-shot change and delete it, silently removing that guard from nine call sites.
- `frontend/src/features/user-administration/__tests__/TenantProfilePage.brand.test.tsx:179-182`:
  `hexField` casts a possibly-null `querySelector` result with `as HTMLInputElement`. A mistyped key
  surfaces as an opaque null-deref inside userEvent rather than as "no brand hex field named X".
  Throwing a named error on null would make the eventual failure legible. Pre-existing behaviour, merely
  now centralised in one place where it is cheap to fix.
- `frontend/scripts/load-test.sh:37-38`: `.load-test-logs/` accumulates one file per suite instance per
  run forever, with no pruning and no documented retention. Twenty invocations during this task's
  development already left a sizeable set. Consider pruning logs older than a day, or noting in the
  header comment that the directory is the operator's to clean.

## [APRAS-86] Build the load-reproduction harness and fix the failures it reproduces (QA) — 2026-09-23

- The level-A gate is not host-independent. On 30 independent `npm run test:load`
  runs of the fixed tree I got 18 green; the 12 reds were entirely category-B
  tests (`Navbar.permissions > shows a morador exactly the links their permissions allow`
  in 11 of 12, `RoleMembersPanel > lists the role's members` in 5) and they track
  the host load average almost perfectly: 9/9 and 8/8 green while `load1` was
  below ~10, 1/10 green while a concurrent process held it above 100, and one
  run degenerated to 32 failures with `LoginPage > renders login form` among
  them. `TenantProfilePage.brand.test.tsx` — the file this task repairs —
  survived 29 of those 30 runs, so the diff is not what makes the gate flaky. If
  `test:load` is ever cited as a pass/fail gate by a later task, it is worth
  either pinning the hog count to `hw.physicalcpu` rather than the literal 12, or
  having the script refuse to run when `sysctl -n vm.loadavg` already exceeds a
  threshold, so a green or red bar means something about the diff rather than
  about who else is on the machine.
- The 64-file eslint baseline carried in the spec's result #12 is wrong: a clean
  `8a915d4` tree measures 77 files carrying the same 375 errors + 2 warnings. The
  developer flagged the discrepancy and could not explain it; the explanation is
  that the baseline figure was mis-derived. Worth correcting at source so the
  next task does not re-litigate it.
- The report's §7d argues that D2's contention relief "had its chance in the
  (1)→(2) column and produced a delta of zero" for the invitation test. In my own
  sample that column moves 6/6 → 4/6, i.e. D2 *does* reduce this test's rate. The
  (2)→(3) inference is unaffected — D2 is held fixed across it, and my (2)→(3) is
  a larger 4/6 → 0/6 — but the "confound measured away" phrasing is stronger than
  a single n=6 sample supports and would read better as "in this sample the
  confound did not fire".

## [APRAS-75] Serve a public landing page at / to anonymous visitors — 2026-09-22

- **Mock has a top header the spec's DOM-order list does not mention.** The mock
  (`APRAS-75-mock.html:111-121`) opens the anonymous state with a minimal
  `<header>` carrying the brand mark and a third "Entrar" CTA, while the spec's
  structure list (lines 62-71) puts the product name inside the hero and names
  only two CTAs (hero + repeat band). Not blocking — ER-4 asks for "at least one
  link to `/login`" and for one `<h1>` and four scoped `<h2>`, all of which the
  mock satisfies — but a sentence in §5 either sanctioning or excluding the top
  bar would remove the last place where spec and mock can be read differently.
- **§7's "holds the expected number of keys" leaves the number to the
  implementer.** Self-consistent (the test and the locale files are written
  together) and ER-7 only requires non-empty plus identical, so it is not a
  verification gap. Worth pinning the count once the operator's copy arrives.
- **"a landing-only element" is named but not fixed** in Test criteria (line 144)
  and in the rewritten smoke case. `getByTestId("landing-capabilities")` is
  already the obvious candidate and is landing-exclusive; naming it explicitly
  would spare the implementer a choice.

## [APRAS-80] Migrate visitor-management components to semantic theme tokens — 2026-09-24

1. **Expected result 12 says "the five existing
   `src/features/visitor-management/__tests__/*.test.tsx` suites".** That glob
   actually matches seven files in the directory — the five component suites
   plus `usePackages.test.tsx` and `useVisitors.test.tsx`. Test criterion 3 in
   the spec body names the five explicitly and is unambiguous; only the
   expected result's glob-plus-count is self-contradictory. Naming the five, or
   saying "all `*.test.tsx` suites in that directory", removes the conflict.
   Not blocking: passing all seven unmodified satisfies both readings.

2. **Name the compositing method for the two `/80` figures.** The spec gives
   4.0551 and 3.2883 and expected result 5 requires asserting them to ±0.001,
   but `src/lib/contrast.ts` exports no alpha-composite helper, so the
   implementer must write one. I confirmed the published numbers come from
   standard CSS sRGB gamma-space blending (round-trip through `oklchToHex`,
   mix the 8-bit channels at α = 0.8 over the background, `hexToOklch`, then
   `contrastRatio`); a plausible alternative — lerping the OKLCH components —
   gives 3.7568 and 3.2685 instead. One sentence naming the space would save a
   round. Related: the spec should point at the APRAS-79 precedent file
   `src/features/lot-management/__tests__/lotManagementContrast.test.ts` for
   the percent-lightness `normalise()` helper, since `parseOklch`'s grammar
   rejects Tailwind's `oklch(55.4% …)` form outright and `hexToOklch` rejects
   `--color-white: #fff` (3-digit shorthand) — both are silent `null`s that
   will cost the implementer time.

3. **Two "Today" figures in the contrast table are labelled against the wrong
   background.** The rows "Selected auth-type chip … Background `--accent`,
   Today 7.2164" and "Counter number … Background `--accent`, Today 7.2164"
   give the ratio of `indigo-700` on `indigo-50`, which is 7.2164; `indigo-700`
   on `--accent` is 7.2080. The §1k table gets this right for AFM:217 by
   writing the surface as "`bg-indigo-50` → `--accent`", and the intent is
   clear from that, but the three rows that abbreviate to just `--accent` are
   off by 0.0084 — more than the ±0.001 the test criterion demands. Write the
   before-background and after-background separately in those rows.

4. **The "guard cannot enforce per-site completeness" list is not exhaustive.**
   It names `AccessLogTimeline.tsx` `text-slate-500` / `text-slate-600` /
   `bg-slate-100` / `dark:text-slate-400`, `GatekeeperEntryModal.tsx` and
   `VisitorTable.tsx` `text-red-600`, and `AuthorizationFormModal.tsx`
   `text-indigo-600`. It omits `dark:border-slate-800`, which is split in four
   files: kept at AFM:115 and :334, AQM:59, GEM:49 and QSM:59 (siblings of
   `border-slate-100`) while being deleted at AFM:114, AQM:58, GEM:48 and
   QSM:58 (siblings of `border-slate-200`). Also, `bg-slate-100` in
   `AccessLogTimeline.tsx` is not actually split — all three occurrences (56,
   59, 82) are kept. Neither error opens a verification hole, because a missed
   deletion would push that file's remaining-match count above its per-file
   figure and fail expected result 2; but the list is presented as the
   reviewer's checklist, so it should be right.

5. **Nit, not load-bearing:** the gatehouse reading says the `/80` label
   "would have been 2.3635" under the old contract. Compositing `--primary`
   at 80% over `--accent` by the same method that reproduces the other two
   `/80` figures gives 2.4499. The counterfactual is not asserted by any
   expected result, so nothing depends on it, but it is the only number in the
   spec I could not reproduce.

## [APRAS-80] Migrate visitor-management components to semantic theme tokens — 2026-09-24
- Expected result 6 opens with "All twelve status sets stay whole: ... and
  `VisitorAuthPage:144` still carry their original classes", and then, in the
  same sentence, says `bg-card` is *migrated* at `:144`. The sentence resolves
  itself — set 12's membership is the two border classes, and the trailing clause
  names the migration explicitly — but a QA agent skimming the first clause could
  read "original classes" as "the whole className at `:144` is untouched". If the
  result is ever edited again, scoping the first clause to the enumerated set
  members ("still carry their original set members") would remove the last bit of
  slack.
- The spec's own recommendation to open a tree-wide follow-up for "drop the `/80`
  from brand text on a brand tint" (gatehouse reading item 2) is worth the
  operator creating before this child ships, so the 3.2883 composite at
  `GatekeeperDashboard:150` is tracked somewhere other than a spec body.
- Expected result 13's "measured wall time reported in the implementation report"
  is a reporting duty, not a pass/fail condition; it rides along with a
  hard threshold in the same bullet so it is not a gate problem, but the
  developer should be reminded that the 2 s per-test ceiling is the criterion.

## [APRAS-80] Migrate visitor-management components to semantic theme tokens — 2026-09-24

- **Form-control fills take `bg-card` here, while the pilot's own `ui/input.tsx`
  and `ui/select.tsx` take `bg-background`.** The sixteen raw `<input>` /
  `<select>` fills at `AuthorizationFormModal:161,170,177,186,194,305,316,330`,
  `GatekeeperDashboard:182,201,276,286,344`, `GatekeeperEntryModal:122`,
  `VisitorAuthPage:80,97` now carry `bg-card`, whereas
  `frontend/src/components/ui/input.tsx:12` and
  `frontend/src/components/ui/select.tsx:11` — migrated under APRAS-78 — carry
  `border-input bg-background` for the same element kind. The two are
  byte-identical in `:root` and diverge only under a tenant theme, so no test
  here can see the difference, and the spec settles the question explicitly
  with its own §1f case-1 reasoning ("a field sits on its panel rather than
  being the page"). I am not blocking on a spec-sanctioned decision, but it is
  a genuine divergence from the pilot's precedent for the identical widget, and
  whichever way it is resolved it should be resolved *once*, tree-wide, before
  children 4–8 replicate the choice across ~95 more files. Worth an operator
  decision now rather than a re-migration later.
- The contrast suite's `it("leaves nothing it moves undeclared")` re-asserts
  the floor loop that `it.each(...)("clears its floor")` already covers, and
  then pins `DECLARED_SUB_AA.length` to 4. The length pin is the load-bearing
  half; the loop above it is dead weight. Non-blocking.
- `describe("the measurement itself")` asserts
  `STYLESHEET.toContain("--primary: oklch(0.65 0.15 160)")` — a literal of the
  `.dark` value, in a file whose stated discipline is that no colour literal
  appears. It is there to prove the `.dark` declaration exists and was *not*
  read, which is a legitimate and well-commented exception, but it will need
  updating if the dark scheme's brand value is ever retuned. Consider asserting
  the structure (two `--primary` declarations, the `:root` one selected)
  instead of the value. Non-blocking.

## [APRAS-80] Migrate visitor-management components to semantic theme tokens — 2026-09-24

- `visitorManagementContrast.test.ts:408` is the single hard-coded colour literal
  in the file: `expect(STYLESHEET).toContain("--primary: oklch(0.65 0.15 160)")`,
  inside `reads --primary from :root and never from .dark`. It is not a colour
  input to any ratio — every measured colour goes through `token()` or
  `palette()`, so the file-derived property expected result 5 asks for is intact
  — but it couples this suite to the exact text of a `.dark` declaration the task
  explicitly does not validate. A retune of the dark scheme would redden this
  test for a reason unrelated to visitor management. The companion assertion on
  the same line above, `expect(token("primary").l).toBeCloseTo(0.62, 2)`, already
  proves the `:root` block is the one being read; asserting merely that
  `STYLESHEET` contains `.dark` and that the two `--primary` lightnesses differ
  would give the same protection without pinning a literal.

- `MIGRATED_TARGETS` in the `splits no status set` test is a hand-maintained list
  of 19 token classes. If a future sibling migration introduces a token not on
  that list, the mixed-span check silently stops seeing those spans rather than
  failing. I re-ran the check with a generic semantic-token pattern and got the
  same answer today, so nothing is wrong now; deriving the pattern from the token
  names in `index.css`'s `:root` would keep it that way without upkeep.

## [APRAS-81] Migrate project and asset management to semantic theme tokens — 2026-09-24

- §"Every status set" row 11 cites `AssetTable:32–43` for
  `getConditionBadgeClass` while §"The one swatch map" cites `:29–45` for the
  same function (the declaration is at 29–45; 32–43 are its `return` lines).
  Use one.
- ER9 enumerates the `dark:` classes that must fall to zero. It is true as
  written, but it silently omits the classes that are *partly* deleted
  (`dark:border-slate-800` 16 of 27, `dark:bg-slate-800` 5 of 7,
  `dark:border-slate-700` 2 of 4 — I verified each site). A reader may take the
  list for the whole deletion set; a one-line note that 60 of the 83 deletions
  are the enumerated classes and 23 are partial would close it.
- §"Declared sub-AA" item 2 says "four sites (`AssetSummaryCards:52`,
  `ConstructionTrackerPage:283,438,359/361`)", which reads as five. `359/361` is
  one site (the gauge track and its fill); say so.
- ER8's opening clause "no `text-red-*` class migrates" is contradicted by its
  own closing clause (`hover:text-red-600` ×3 does migrate). Both are in the
  same sentence so it is decidable, but "no bare `text-red-*`" would be cleaner.
- The re-measurement, the contrast figures, the eslint baseline, the coverage
  thresholds and the three predecessor ledger totals are all exact. The parts of
  this spec that are right are right to the digit; the four findings above are
  local and cheap.

## [APRAS-81] Migrate project and asset management to semantic theme tokens — 2026-09-24

- ER18's 883 ms and ER16's "375 errors + 2 warnings across 64 files" are
  point-in-time measurements of an evolving tree. Both are already framed so the
  decidable clause does not hinge on them ("under 2 s", "at most the 2 errors in
  the touched files"), but if either drifts before implementation the QA agent
  will see a mismatch in the prose half of the result. Worth the implementer
  re-stating the measured figures in the PR body rather than treating the spec's
  as authoritative.
- The spec repeats three times that §1f/§1k verdicts are invisible to every test
  and are a human review duty. That is correct and important; consider having the
  developer surface the §1k site table in the PR description so the reviewer has
  the checklist at hand without opening the spec.

## [APRAS-82] Migrate document and occurrence management to semantic theme tokens — 2026-09-24

- The contrast table's row "Tile and inline glyphs → `text-primary` … `--accent`
  / `--muted` | Today **5.7621 / 6.4414**" has a wrong "Today" cell. 5.7621 is
  right (`text-indigo-600` on `bg-indigo-50`), but the `--muted` sites are
  `NewOccurrenceModal:136,140,154` on `bg-gray-50` and `OccurrenceDetailsView:173`
  on `bg-slate-50`; `text-indigo-600` on `bg-gray-50` measures **6.1708**, not
  6.4414 (6.4414 is the on-white/on-`--card` figure, carried into the wrong row).
  No expected result depends on this cell, so it does not block, but it is the
  one number in the document that does not reproduce and it should be corrected
  in the same revision.
- Expected result 9 says "grouping every grammar match … by `(file, class-context
  span)`", but the badge-map returns in `OccurrenceTable.tsx` are string literals
  outside any `className`/`cn`/`cva` context and so belong to no span. The answer
  is the same either way (I checked), but the result should say what happens to
  matches outside every span — excluded, or one bucket per file.
- Expected result 13 pins "exactly 22 `dark:` classes remain" and lists 17
  classes that must reach zero; those 17 account for 77 of the 78 deletions. The
  78th — the single `dark:text-slate-300` at `DocumentGridTable:89`, whose base
  `text-slate-600` migrates — is pinned only by the count, so an implementation
  that deletes a different one of the 16 `dark:text-slate-300` occurrences still
  satisfies the result. One clause naming `DocumentGridTable.tsx:89` would close
  it.
- The spec amends APRAS-78's "each sibling appends exactly one" comment in
  `MIGRATED_DIRECTORIES` to allow two entries. It says so openly and the
  operator's scope forces it, so it is not a contract extension in substance —
  but it is the one place where "this task consumes the contract and may not
  extend it" is not literally true, and the revision could say that in the
  opening paragraph rather than only in §"The guard suite — what changes".

## [APRAS-82] Migrate document and occurrence management to semantic theme tokens — 2026-09-24
- Spec body, *What this proves, and what it misses*: "the indigo hue shift at
  73 sites (plus **22** deleted `dark:` indigo siblings)" — the tree carries
  **13** `dark:` indigo occurrences (`dark:text-indigo-400` 4,
  `dark:hover:text-indigo-400` 4, `dark:hover:bg-indigo-950/50` 2,
  `dark:bg-indigo-950/50` 2, `dark:bg-indigo-950/60` 1), all of them required
  gone by expected result 13. The 22 appears to be the kept-`dark:` figure
  reused by mistake. Narrative only — no expected result depends on it, so it
  does not block — but it is worth correcting so the implementer does not go
  hunting for nine more `dark:` indigo classes.
- `docs/tasks/APRAS-82-spec.md` line 602 carries a doubled word, "and and
  assert, **per component**". The copy on the task card is already clean;
  only the spec file has it.

## [APRAS-83] Migrate finance, purchases and access control to semantic theme tokens — 2026-09-24

- Spec body, *§1k applied* / consequence 2: the download `<a>` is at
  `InvoicePreviewModal.tsx:47`, not `:58`. The contrast table, the substitution
  bullets and §1f case 3 all say `:47`; only consequence 2 says `:58`.
- Spec body, consequence 4: "`purchase-management` contains no `indigo` class
  at all. Its only brand-family occurrence is set 2's exception above" — set 2
  is `AccessEventFeed:47,48`, which lives in `access-control`. The sentence
  points at the wrong set; the claim it is trying to make (that
  `PurchaseRequestsPage:198` already reads `bg-primary
  text-primary-foreground`) is correct and verified in the source.
- Result 15 would be easier to keep true across future children if it stated,
  once, that each component's token list is over the rendered markup
  *including* the `components/ui` primitives it composes. That single sentence
  is what the SelectQuoteModal finding turns on.
- Result 19's "the repository total stays at 375 errors + 2 warnings across 64
  files" is verified at HEAD, but this task adds a new file
  (`financePurchasesAccessContrast.test.ts`). Worth saying explicitly that the
  new test file must lint clean so the 64-file count is unchanged.

## [APRAS-83] Migrate finance, purchases and access control to semantic theme tokens — 2026-09-24

- Result 15's three inclusion/exclusion lists are now the load-bearing
  statement of which tokens a primitive contributes. When APRAS-90 or the
  dark-mode follow-up changes `buttonVariants`, this test is the one that will
  break in a non-obvious way; a one-line comment in
  `TenantBrandReach.test.tsx` naming `components/ui/button.tsx`'s variant
  strings as the source of `bg-primary`/`text-primary-foreground`/`border-input`
  would save the next reader the derivation.
- `ui/textarea` contributes `placeholder:text-muted-foreground`, and
  `ui/button`'s outline contributes `hover:bg-accent`, both of which differ
  from asserted tokens only by prefix. The result already forbids substring
  matching; an explicit negative assertion that `hover:bg-accent` is present
  but `bg-accent` is not, in `SelectQuoteModal`'s case, would make the strict
  splitting self-evidencing rather than merely stipulated. Non-blocking.

## [APRAS-84] Migrate media, feedback, announcements and packages to semantic tokens — 2026-09-24

- **Result 21's "866 ms" is wall-clock and inherently noisy** — I measured
  910 ms on the same commit. The operative requirement (every individual test
  under 2 s; memo at module scope) is decidable and fine, but a QA agent
  reading the parenthetical as an assertion could fail a correct
  implementation. Phrasing it "≈866 ms, recorded as context, not asserted"
  would remove the trap. Not blocking, because the clause describes a past
  commit's state rather than anything the implementation can make true or
  false.
- **Body contrast table, last row**: `AnnouncementCard:72`'s
  `hover:text-red-600` is attributed to a `--card` surface at 4.8073, but that
  button also carries `hover:bg-gray-100 → hover:bg-accent`, so the glyph is
  only ever painted while its surface is `--accent` — i.e. 4.2953, the same
  number as `CommentThread:62` on `--muted` (`--accent` and `--muted` are
  byte-identical in `:root`). No asserted value changes and result 7 already
  declares the 4.2953 pair, so this is a label, not a number.
- **Result 15 says "the token set is exactly as follows" and then gives
  contains / contains-none lists.** The lists are what is decidable (the full
  rendered set also holds layout tokens and kept palette classes), so "exactly"
  can only mean "these assertions"; saying "asserts the following memberships
  and non-memberships" would close the reading.
- **Result 9** could note what happens to grammar matches that fall outside
  every class-context span (the nine `getStatusBadgeClass` return-string
  occurrences). The answer is zero either way, but an implementer deciding it
  fresh may wonder.
- Worth telling the developer that the guard comment "each sibling appends
  exactly one" is being deliberately superseded by four entries (the spec says
  so in § "The guard suite — what changes" item 1); that comment edit is easy
  to miss in review.

## [APRAS-85] Migrate the remaining feature directories and close the guard — 2026-09-24

- §"The context-dependent cases", §1f case 3 reads "The band holds **3**
  occurrences here, all `bg-emerald-700`" and then names the third as
  `AuditTimeline:111`'s `text-emerald-600`. Measured, `bg-emerald-700` occurs
  **twice** in the six trees. The sentence corrects itself in its own second
  half and no expected result depends on it (result 14's "zero
  `bg-emerald-700` after the change" is correct), so this is not blocking —
  but "3 … all `bg-emerald-700`" should read "3 emerald 500–700 occurrences:
  two `bg-emerald-700` and one `text-emerald-600`".
- The intro (line 22) claims, unqualified, "any new hard-coded palette class
  anywhere in the frontend fails CI by default", which §"What this proves"
  later correctly narrows to "any new hard-coded palette class **matching
  §3b**". Narrow the intro too, so the two sentences do not have to be read
  together.
- Result 8's "the class token `text-primary` appears **zero** times" is
  correct under whitespace-split token equality but would fail a naive
  substring grep, since the diff adds `text-primary-text` (×5) and
  `text-primary-foreground` (×2). Result 18 spells the splitting rule out;
  result 8 does not, and results are read one at a time. Adding "as a
  whitespace-split class token, by exact equality" would make it decidable
  without reading any other result.
- On the operator question about §3b's side-qualified border blind spot
  (`border-t-slate-400` ×5 in `TaskBoard`): the handling is **conservative,
  not dishonest**. The five occurrences are measured, named with line numbers,
  shown to belong to a set this child keeps anyway, the guard's claim is
  narrowed to §3b-matching classes, and widening the grammar is correctly
  identified as an amendment forbidden to every child. I would not block on
  it, and no expected result depends on the answer.

## [APRAS-85] Migrate the remaining feature directories and close the guard — 2026-09-24

- Result 18's `TenantBrandReach` case is by some margin the longest single
  expected result in the split and encodes two component fixtures plus two
  exact token sets. It is decidable as written, so it is not a finding, but a
  future child would be easier to QA if a result of that size were split into
  one result per mounted component.
- The operator question about §3b's blind spot on side-qualified border
  utilities (`border-t-*`, `divide-y-*`; five occurrences today, all inside
  kept set 8) is correctly non-blocking here, but it is the one thing that
  survives "the guard is closed". Worth opening as a successor task to
  APRAS-77 so the claim does not decay silently after this child ships.

## [APRAS-87] Raise the active-tab label contrast, which fails WCAG AA — 2026-09-24

- §3 says "The **17** `.tsx` files listed in §2a"; §2a lists **18** distinct
  files (alert-modal, badge, button, LotDetailsView, Navbar, Sidebar,
  LoginForm, ForgotPasswordPage, LoginPage, SignupPage, ResetPasswordPage,
  BrandedEntryPage, AcceptInvitationPage, TaskCard, TaskBoard, TaskList,
  AssigneePicker, GeneralDashboardPage). The per-line tables are authoritative
  and complete, so nothing is lost — but the count should read 18.
- §2c's `painted` column prints a hex for the *untinted* rows too
  (`--background` `#fcfcfc`). Measuring those rows through that hex, the way
  the tinted rows are measured, yields **5.0778** and **4.6522** instead of
  the published `5.0622` / `4.6547`, which would fail results 4 and 7 while
  looking like a faithful reading of the table. Worth one sentence saying the
  untinted rows are measured on the parsed `oklch()` and the hex is
  illustrative.
- `lotManagementContrast.test.ts` drives `it.each(PRE_EXISTING_SUB_AA)`;
  emptying the array leaves a `describe` with no test. Say whether the
  `describe` is removed or replaced by an explicit
  `expect(PRE_EXISTING_SUB_AA).toHaveLength(0)`, so the implementer does not
  have to choose.
- The mock's `--muted` is `#f2f7f5`; the token's real paint is `#ecf4ef`. No
  sample's ratio depends on it, but matching it costs nothing.
- Navbar.test's three assertions actually run against Sidebar markup
  (`Navbar.tsx:64` renders `<Sidebar />`). Naming that in §3 would save the
  implementer a minute of confusion about why `Navbar.tsx:155` is not the
  element under test.

## [APRAS-87] Raise the active-tab label contrast, which fails WCAG AA — 2026-09-24
- Result 9 inherits the tree-wide `375 errors + 2 warnings` ESLint baseline from
  the APRAS-81…85 family. It is safe today because all six specs assert the same
  ceiling, but it is the only figure left in APRAS-87's results that a task
  *outside* this family could invalidate. If a future non-family task changes the
  baseline, this whole family of results needs re-measuring together; a
  single published baseline constant that all six cite would remove the coupling.
- The implementer should seed `GRAPHICAL_PRIMARY_SITES` by running the §3 scan at
  their own HEAD rather than transcribing §2b, so that a sibling that landed in
  the meantime is picked up automatically instead of turning the guard red on
  first run. §5 implies this; saying it in §3 would make it an instruction rather
  than an inference.

## [APRAS-90] Drop the /80 opacity from brand text sitting on a brand tint — 2026-09-24

- `lotManagementContrast.test.ts` does not currently declare a local
  `composite`, so result 4's consolidation is complete as scoped — but once
  `compositeOver` is exported from `contrast.ts`, a one-line note in
  `docs/frontend/theme-token-mapping.md`'s tooling section would stop the next
  migration child from writing a third copy. Out of scope here (§"Out of
  scope" bars amending that file), so this is a suggestion for a later task, not
  a finding.
- `APRAS-85-spec.md:488` maintains a list of files permitted to contain a
  palette class, and names `src/lib/contrast.ts`. Adding `compositeOver`
  introduces no colour literal, so the list is unaffected — worth a sentence in
  the spec body so the APRAS-85 developer does not re-derive the question.
- The operator note asking whether the counter label should become
  `text-foreground` (17.7626) rather than staying branded at 4.6547 is well
  posed and correctly defaulted. I would nudge toward accepting it: the residual
  the spec itself declares — a tenant brand can land this pair at exactly 4.50
  with no cushion — is real, and a gatehouse caption in daylight is the worst
  place to spend it. This is a judgement for the operator, not a finding.
- The mock is the right artefact for the question asked. Rendering both
  composites at the measured hexes with a brightness slider is a legibility
  instrument, as claimed; no change requested.

## [APRAS-90] Drop the /80 opacity from brand text sitting on a brand tint — 2026-09-24

- Result 2's parenthetical about column counts (74 → 71) is helpful evidence
  but is the one clause in the result set that a future whitespace-only change
  elsewhere in the line could age out of truth. It is not a blocking risk (the
  character-delta clause already pins the change), and it could simply be
  dropped to a spec-body note rather than carried in the QA-visible result.
- The operator question at the end of the spec (keep `text-primary-text` vs.
  switch the caption to `text-foreground`, 17.7626 on `--accent`) is still
  open and is worth a decision before implementation, since answering it
  "yes" after the fact would change results 1, 6 and 8. The spec's documented
  default (keep the brand token) makes this non-blocking.

## [APRAS-90] Drop the /80 opacity from brand text sitting on a brand tint — 2026-09-24

- Approach item 4 lists the sweep's negative controls as "`text-primary-text`,
  `text-primary-foreground`, `text-primary`, `bg-primary/10` or
  `text-muted-foreground/80`", while expected result 7 — correctly — also requires
  `text-foreground`. The result governs, and an implementer satisfying result 7
  automatically satisfies the Approach, so this is prose drift only; adding
  `text-foreground` to the Approach sentence would remove the discrepancy.
- Result 6 names `contrastRatio` and `parseOklch` as the imports it measures
  through, but the composited half of the assertion also needs `compositeOver`
  (Approach item 4 says so). Naming it in result 6 as well would make the result
  fully self-contained for QA rather than relying on result 4 to supply it.
- `docs/tasks/APRAS-90-mock.html`'s `#variant-label` still carries an inline
  `style="color: #177c52"` (the rejected branded option) that the trailing
  `select("foreground")` overwrites at load. Harmless, but changing the inline
  default to `#060a08` would mean the page reads correctly even with scripting off.
- The spec's Residual section is worth keeping verbatim as the task ships: after
  this change 4.6547 is no longer this label's number but still governs
  `AuthorizationFormModal:217,228` as normal text, and that is APRAS-88's
  property. Nothing to change — flagged only so the sentence is not trimmed as
  now-irrelevant during implementation.

## [APRAS-90] Drop the /80 opacity from brand text sitting on a brand tint — 2026-09-24
- `frontend/src/lib/contrast.ts:287-290` — the comment says flatly "Unreachable: three rounded 0-255 channels always render as six hex digits." That is true only because every caller passes `alpha` in `[0,1]`; with `alpha = 80` or `NaN` the channels leave `[0,255]` and the guard fires (verified). Now that the helper is exported and six sibling specs will call it, consider either narrowing the wording ("unreachable for `alpha` in [0,1], which is the only domain this helper accepts") or making the domain explicit in the JSDoc `@param`. Purely a documentation-precision point — the runtime behaviour is already correct and loud.
- `frontend/src/__tests__/brandTextOpacity.test.ts:62,70` — `brandTextOpacityGrammar` and `indigoTextOpacityGrammar` are `export`ed from a test file that nothing imports. Harmless, but `const` would say more accurately that the grammar is private to this guard. (If the intent is for a sibling to reuse them, they belong in a shared helper rather than a test file — but YAGNI says leave that until a sibling actually needs it.)
- Optional: the sweep matches any whitespace-split token in a source file, including one inside a comment or a plain string. That is conservative in the safe direction (false positive, never false negative) and I would not change it, but a future reader may be surprised, so a one-line note on `sweep()` could save them the trip.

## [APRAS-90] Drop the /80 opacity from brand text sitting on a brand tint — 2026-09-24
- Re-run the ER2 check against the real commit once it exists
  (`git show --format= <commit> -- frontend/src/features/visitor-management/components/GatekeeperDashboard.tsx`),
  since it was necessarily verified against the index here. Nothing in the index is
  suspicious — index and worktree agree for every file the task owns — but the result
  is worded against a commit that does not exist yet, and only the commit makes it
  durable.
- The mutation probe (ER5) showed the guard's failure message is already excellent: it
  prints `<file>:<line> <class>`, which points a future author straight at the offending
  site. No change wanted; noting it because it is the reason I could confirm the guard
  is live rather than vacuous.

## [APRAS-85] Migrate the remaining feature directories and close the guard — 2026-09-24
- **S1. Result 19's span claim reads as exclusive and is not.** It says "Of the
  312 occurrences, the five `border-t-*` stripes fall inside **no** class-context
  span at all, because they are values of a `headerColorClass` object property".
  Measured with a faithful port of the guard's own `classContexts()`, **55** of
  the 312 fall inside no span — including, in the same object literal, the ten
  `colorClass` tints (`bg-slate-50/50`, `dark:bg-slate-900/20`, …), plus
  `GeneralDashboardPage`'s 24 swatches, `SpaceBookingPage`'s 8,
  `DueDateBadge`'s 4 and `TenantInvitationsPanel`'s 4. The sentence is literally
  true of the five and the assertion it asks for (that `matchesIn` reports them
  anyway) is right, but a QA agent holding only this text may read "of the 312 …
  the five" as "exactly five" and fail a correct implementation, and an
  implementer may write `expect(outsideSpans).toHaveLength(5)`. Say instead that
  the five are among the 55 occurrences that lie outside every span, and that the
  ten tints beside them are too — which strengthens rather than weakens the
  no-eighteenth-set argument.
- **S2. Name the `accent` alternative explicitly in the §3b prose item.** The
  third load-bearing item already records that the qualifier is one letter and
  applies to `border` and `divide` only; adding "and that no other alternative of
  `prefix` was added or removed" makes B1 unrepeatable by a later child.
- **S3. Result 21's counting convention is unstated.** The four known-gap figures
  (73 / 69 / 41 / 12 = 195) are **bare** occurrences. The tree also holds one
  `dark:text-slate-700` (`finance/CategoryTransactionDrilldown.tsx:79`) and two
  `hover:text-slate-700` (`lot-management/LotDetailsView.tsx:166,177`); the spec
  mentions the `dark:` one but not the two `hover:` ones, so a QA agent grepping
  `text-slate-700` measures 72, not 69. Say "bare, excluding variant-prefixed
  occurrences, of which there are three" and the result becomes reproducible
  without the spec. (Pre-existing; not introduced by job (c).)
- **S4. Say what `task` cell the eight `public-site` rows carry** when APRAS-85 is
  the one landing second. The spec says the rows and entries are added and
  reported rather than folded into 145/126, which is right, but it never names the
  task id they carry — and since results 9 and 11 are both scoped by task id, the
  implementer needs to be told (presumably `APRAS-75`, the owner) rather than left
  to choose.

---

## [APRAS-85] Migrate the remaining feature directories and close the guard — 2026-09-24
- The "979 lines" figure in §"What changes, and what is deliberately left
  alone" is one off (`wc -l` says 978). Purely cosmetic; no expected result
  reads it.
- Result 3's over-reach list does not include `border-2`, which §"Over-reach"
  prose calls out as the specific case the widening could break. It is covered
  indirectly by APRAS-78's untouched `describe("the §3b grammar")` block (also
  required by result 3), so this is not a gap — only a place where the result
  could have been one case stronger.

## [APRAS-75] Serve a public landing page at / to anonymous visitors — 2026-09-24
1. `LandingPageCopy.test.tsx` — drive the three non-default preview tabs before the leak assertion so
   all 48 keys pass through the real instance. Roughly: loop `["tabAccess","tabInfractions","tabFinance"]`,
   `await user.click(screen.getByRole("tab", { name }))`, re-read `container.textContent`, and run the
   same stem check. Three lines, and it retires the last untested key group.
2. `LandingPage.tsx:86-109` — the tab widget is ARIA-incomplete: `role="tab"` buttons with
   `aria-selected`, but no `role="tabpanel"` on the panel container (line 112), no `id`/`aria-controls`
   pairing, and no `type="button"`. A screen reader hears "tab, 1 of 4" and has nothing to move into.
   Adding `role="tabpanel"` + `aria-labelledby` on line 112 and `id`/`aria-controls` on the buttons is
   a handful of attributes; arrow-key roving focus would be the full APG treatment but is optional
   since the buttons are natively focusable and Enter/Space-operable. Given APRAS-88/APRAS-90 were
   both AA fixes, I would fix this in the same revision round — I am leaving it non-blocking only
   because the widget is operable by keyboard as it stands.
3. `LandingPage.test.tsx:8-13` — the local `vi.mock("react-i18next")` is the second of the two layers
   that hid the original defect, and it is redundant with the global mock in `setup.ts` for
   everything except the key-passthrough behaviour. It is defensible now that the copy test exists,
   but the comment above it should say so explicitly ("structural assertions only; copy resolution is
   proved in `LandingPageCopy.test.tsx`") so the next reader does not re-derive the trap.
4. `LandingPage.test.tsx:66-76` — "renders no hard-coded user-visible strings" is the weakest test in
   the diff: under the key-passthrough mock it only asserts two specific prose phrases are absent,
   which a newly hardcoded third string would sail past. A real version asserts every non-empty text
   node matches `/^landing\./`. The spec's ER "no hardcoded visible string" is currently carried by
   the copy test's stem check, not by this one.
5. `LandingPage.tsx:20` — typed `React.FC` without importing `React` as a value works under the new
   JSX transform, and matches nothing in particular; the file's own hooks are imported individually.
   Minor consistency nit only.
6. `parity.test.ts` — `LANDING_KEYS_EN.sort()` mutates the filtered arrays in place. Harmless here
   (both are fresh arrays from `filter`), but `[...x].sort()` is the habit worth keeping.

## [APRAS-75] Serve a public landing page at / to anonymous visitors — 2026-09-24
- `LandingPage.tsx:119,123,143,159` duplicate four class strings that
  `components/ui/badge.tsx:15-30` already owns as named variants. I accept the
  decision not to use `<Badge>` here (its base string forces `uppercase
  tracking-wide`, wrong for sentence-case marketing copy), but the duplication
  is real and now exists in three places counting `TaskDetailsView.tsx`. If a
  fourth consumer appears, the fix is to split the tint pairs out of
  `badgeVariants` into an exported `statusTint(variant)` helper that both
  `<Badge>` and bare spans can call, rather than to keep copying strings.
- `LandingPageStatusTints.test.ts` asserts the class strings against the file's
  *source text* rather than rendered output. That is what makes the whole-file
  palette sweep possible, so it is a reasonable trade, but it means the test
  pins a formatting detail: reformatting the badge onto two lines, or adopting
  the `statusTint()` helper above, breaks the test without changing a pixel. A
  rendered-DOM assertion on `getComputedStyle`-free `className` for the three
  non-default panels would be more durable — and would also close the round-1
  caveat that the three non-default preview panels are never mounted by the
  i18n test.
- `src/features/public-site` is not in `themeTokenMigration.test.ts`'s pinned
  directory list (`:34-35`). Adding it would be a one-line change and would put
  future files in this directory under the same guard the rest of the migrated
  tree gets. Out of scope for APRAS-75; worth a follow-up task.

## [APRAS-75] Serve a public landing page at / to anonymous visitors — 2026-09-24
1. **The "no hardcoded copy" assertion is weaker than its name.** `LandingPage.test.tsx`
   implements it as a two-string denylist (`"Gestão inteligente"`, `"Smart and
   transparent"`) plus one key-presence check. MUTATION: I replaced
   `{t("landing.footer.text")}` with the literal `Todos os direitos reservados a APRAS.`
   and the **entire landing + i18n suite still passed** (38/38). So a future change that
   hardcodes PT prose anywhere outside the hero/two capability titles would ship silently
   and never translate to EN. A cheap exhaustive form: in `LandingPageCopy.test.tsx`,
   collect the rendered text under `pt` and under `en` and assert the two differ for every
   text node — or assert that the set of visible strings is a subset of the 48 locale
   values. (I restored the file; diff is clean.)
2. **`LandingPageCopy.test.tsx` only exercises `pt`.** It calls
   `i18n.changeLanguage("pt")` in `beforeAll` and never checks `en`. The EN bundle is
   currently guarded only by key-set parity, not by rendering. Adding one `en` render
   with a single English assertion would close that and would also give suggestion 1
   for free.
3. **Pre-existing flake, not this task's:** in my first full coverage run,
   `src/__tests__/themeTokenMigration.test.ts > "fails when any single exception is
   removed"` timed out at the 5000 ms default (5391 ms) under parallel load. Run alone
   it passes in 1.28 s (50/50), and the second full run passed 1933/1933. It is an
   O(n·EXCEPTIONS) sweep with the default timeout and nothing to do with APRAS-75, but it
   will intermittently redden CI; worth a per-test `timeout` argument in its own task.
4. The hero's secondary CTA is an in-page `<a href="#landing-previews">`. Harmless, but
   note that it is the one anchor on the page that is not a router `Link`, so a future
   test that asserts "every anchor points at /login" would trip on it.
