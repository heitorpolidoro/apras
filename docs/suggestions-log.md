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
