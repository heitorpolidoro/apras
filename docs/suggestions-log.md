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

## [APRAS-82] Migrate document and occurrence management to semantic theme tokens — 2026-09-24
1. `frontend/src/__tests__/themeTokenMigration.test.ts` — the `byPath` index replacing
   `files.find(...)` is a second optimisation beyond the memo hoist the spec names, and it
   quietly changes a tie-break: `find` was first-wins, `new Map(files.map(...))` is
   last-wins if a caller passes two entries for one path. `pinnedFiles()` de-duplicates
   through a `Set`, so this cannot happen today, and the replaced code carried a comment
   explicitly worrying about `violations` being exported and taking an arbitrary array. A
   one-line note on `byPath` recording the tie-break would preserve that reasoning.
2. Same file — the `MIGRATED_DIRECTORIES` doc comment still reads "each sibling appends
   exactly one", now contradicted by the inline comment two lines below it. Harmless, and
   APRAS-85 replaces the list wholesale; worth reconciling whenever that lands.
3. `SCAN_MEMO` is never cleared and now retains every distinct source the mutated-argument
   tests synthesise. Bounded by the test count and measured at 325 ms, so this is a note
   rather than a concern — but if a future child pushes the exception count much higher,
   the memory profile is the thing to look at, not the time.
4. The spec's Expected Results asks the declared sub-AA list to carry the emerald-700/800/900
   and amber-700 figures; the implementation puts them in a sibling `it.each` instead,
   because they are all above 4.5:1 and `DECLARED` asserts sub-AA membership. That is the
   better reading of the two, and I mention it only so the divergence is on the record.

## [APRAS-81] Migrate project and asset management to semantic theme tokens — 2026-09-24
- The marker's second guard ("exactly one sentence in the §1f Case 1 paragraph
  begins `The second clause of the rule is`") closes the near-duplicate case only
  while APRAS-83 carries the verbatim sentence its spec mandates. A paraphrase of
  the ruling with neither the marker nor that opening would leave the file
  stating the ruling twice while `grep -c -F` still prints `1`. Not blocking —
  no mechanical check catches a paraphrase — but worth a sentence in APRAS-83's
  spec forbidding any restatement of the §1f case 1 page-root extension other
  than the verbatim one.
- Once `BASE` is fixed, consider stating it once in a preamble the results
  reference rather than repeating the full definition inside two results; the
  repetition is what let the two copies drift from the spec body's own (correct)
  primary definition, `git rev-parse HEAD` before the first commit.
- `frontend/src/components/__tests__/TenantBrandReach.test.tsx` is claimed by
  this task's path-scope result and is plausibly also touched by APRAS-83. The
  result is content-identified ("two added cases that mount MilestoneTimeline and
  AssetSummaryCards"), so it survives either order, but the implementer should
  expect a textual merge conflict there.

## [APRAS-81] Migrate project and asset management to semantic theme tokens — 2026-09-24
- One sentence, cheap to add at implementation time and worth folding into the
  results if they are ever touched again: say that an EMPTY commit-filter result
  fails rather than passes. As written, the three filter-only results ("no
  commit whose subject matches `[a-z]+\(APRAS-81\):` touches …", and the
  path-scope set) pass vacuously if the implementer mis-subjects the commits, so
  the scope guard would go quiet exactly when the convention it rests on was
  broken. The mitigation already present is that the three `BASE`-anchored
  results fail loudly in the same scenario (`git rev-parse "^"` → exit 128), so
  QA cannot plausibly complete the list without noticing — which is why this is
  a suggestion, not a blocking finding.
- The two soft before/after claims noted in point 3 (`getConditionBadgeClass` /
  `STATUS_BADGES` / `COLUMNS` "retain their original classes", and "the only red
  that moves") would read more crisply if they named `git show "$BASE:<path>"`
  inline the way the three explicit baseline results do, rather than leaving the
  reader to infer it.
- The spec asserts the commit convention holds project-wide; it holds for recent
  history and is mandatory going forward, but 179 of 384 historical subjects do
  not follow it. Softening that sentence to "the convention `CLAUDE.md`
  mandates, followed by every recent commit" would keep the claim true without
  weakening the mechanism, which only needs this task's own commits.

## [APRAS-82] Migrate document and occurrence management to semantic theme tokens — 2026-09-24
- Result 14 names an "APRAS-81 ledger arithmetic" block that does not exist:
  APRAS-81 has not shipped (no commit, no ledger row, no exceptions entry, no
  `describe`). The clause is vacuously true and nothing here is wrong, but the
  three shipped children's blocks are the real coverage. If APRAS-81 lands
  after this task, whoever writes it should note that APRAS-82 already appended
  two `MIGRATED_DIRECTORIES` entries where the guard's own comment says "each
  sibling appends exactly one" — the comment is now slightly behind its code,
  even though the APRAS-82 block below it explains the exception.
- `it("splits no status set…")` keys its mixed-span detection on GAP-TINT rows
  only. That is faithful to the expected result, but it means an equivalent
  split of a GAP-NO-TOKEN unit (the rose pair at `DocumentGridTable.tsx:166`,
  say) would go unreported by this particular test. I confirmed the gap
  experimentally — injecting `bg-card` into the rose span leaves the test
  green. The guard proper and the status-set test still cover those classes, so
  this is not a hole in the deliverable, but a future child widening the check
  to "any kept tint unit" would close it.
- `documentOccurrenceContrast.test.ts` re-derives palette luminances by reading
  `node_modules/tailwindcss/theme.css`. That is the right source, but it ties
  the fixture numbers to the installed Tailwind version; a minor bump that
  nudges a palette entry would fail these tests with a confusing diff. A
  one-line comment naming the Tailwind version the figures were measured
  against would make that failure self-explaining.

## [APRAS-84] Migrate media, feedback, announcements and packages to semantic tokens — 2026-09-24
- §1e's trailing paragraph (`docs/frontend/theme-token-mapping.md:218`) says
  "Every `bg-`, `border-`, `ring-` and `accent-` figure is unchanged." It reads
  as APRAS-88 history and so survives the amendment, but an `accent-` figure
  does change. State in §7 that this sentence is deliberately left as a record
  of APRAS-88's edit, so a reviewer does not read the omission as a sixth,
  forgotten place.
- §1a line 115 reads "The **four** named moves are"; growing the list to five
  means editing that numeral too. It falls inside amendment place (a), but say
  so, since result (d) forbids any sixth place.
- Result 11 calls all six rows "the `oklch()` strings `build_theme` emits". The
  first row is the product default, hand-written in `frontend/src/index.css`;
  `build_theme` does not emit it (the mock's own comment says this correctly).
- The mock never names the overhang in words. One sentence beside the red /
  blue / purple panels would keep the operator from having to spot the
  near-white sliver themselves.
- The board's `expected_results` are the pre-decision set and must be replaced
  by the spec's before dispatch; board result 16 in particular would fail the
  task for amending `theme-token-mapping.md`, which is the decision itself.

## [APRAS-84] Migrate media, feedback, announcements and packages to semantic tokens — 2026-09-24
- Item 4 and Out of scope both say "`build_theme`'s refusal contract". §7 is
  now precise that `build_theme` never raises and that the 422 is
  `TenantService.validated_brand_theme`'s. The two remaining phrases are about
  the track and about a hypothetical ninth pair, so they are not wrong in
  substance, but "the refusal contract `validated_brand_theme` enforces over
  `build_theme`'s output" would keep the whole document consistent with the
  section that now defines it.
- The lattice sweep samples hue every 5° while stepping lightness and chroma at
  the full 0.01 grid. That is the test's own pre-existing design and the spec is
  accurate in describing it ("H every 5°"), but §7 also calls it "every
  `(lightness, chroma, hue)` triple `_clamp_input` can produce", which is true
  of two axes out of three. Dropping the word "every" for hue would leave the
  claim exactly as strong as the assertion behind it.
- §7 could name `frontend/src/index.css:39` and `:55` where it gives the
  product-default figures, which would make the distinction the blocking
  finding asks for self-evident at the point the numbers are introduced.

## [APRAS-84] Migrate media, feedback, announcements and packages to semantic tokens — 2026-09-24
- Result 9 cross-references "the five typed tenant brands of results 11 and
  13". Result 13 (zero-based, the kept-foreground result) names no brand; the
  brands appear in results 11 and 12. Fix the reference in the same edit as the
  blocking finding.
- The mock's lede at line 159 says the other four combinations "cada uma traz,
  em vermelho, a razão pela qual foi recusada", but the first of those four is
  the HOJE panel, whose `why` is "Estado atual", not a rejection. Pre-existing
  and cosmetic.

## [APRAS-84] Migrate media, feedback, announcements and packages to semantic tokens — 2026-09-24
- **Not blocking.** Result 9's phrase "the `oklch()` strings `build_theme` emits for that brand as its `--primary` …" could say "in its `light` scheme", since `build_theme` returns `{"light": …, "dark": …}` and both schemes carry those three keys. As written the rule admits the dark-scheme strings too. This is harmless slack, not a defect: it cannot fail a correct file, and the values results 12 and 13 assert are pinned numerically to the light scheme. Fold it in only if the spec is edited for another reason — it does not justify a fifth round.
- **Not blocking.** `build_theme`'s simple mode also takes an `accent`, which the spec never names for these five brands. I verified the three tokens in question are independent of it, so the set is well defined; a parenthetical to that effect would save the developer the same check.

## APRAS-87 — brand text off the graphical token (2026-09-25, landed 0815915)

- **Navbar's own active markup is untested.** Three assertions in
  `frontend/src/features/user-administration/__tests__/Navbar.test.tsx` resolve
  through `<Navbar />` to the *Sidebar* label `<span>` that `Navbar.tsx:64`
  renders; Navbar's own markup contains no nav links, and its active language
  button is `bg-primary text-primary-foreground`. They were renamed to say what
  they actually assert, but the coverage gap is open. Worth its own task.
- **The graphical guard has one narrow escape.** Within a single file,
  converting a declared graphical site to `text-primary-text` while adding a
  bare `text-primary` to a character site keeps the per-file count equal and
  passes. Inherent to the deliberate no-line-number design that lets sibling
  migrations land without turning it red; a comment, not a fix.
- **`frontend/src/test/` is swept by the guard.** It is neither `__tests__/`
  nor `*.test.ts`, so a doc comment containing the bare token fails the sweep.
  Fixed in the comment rather than by narrowing the sweep, which would have
  opened a permanent hole for any source placed there.
- **The mock uses a before/after toggle rather than a two-column layout**, so
  the two tokens are never adjacent in one view at the same call site. Both
  ratios are carried per pair, so the comparison is available.
- **`lotManagementContrast.test.ts`'s `it("has none left to declare")` loops
  over an empty array**, so its body never executes. Kept as a frame for future
  entries.

## APRAS-83 — spec revision (2026-09-25)

- **`§1f case 3 — emerald 500-700` overstated the band**: 17/14 where the tree
  holds 15 (3 migrate, 12 stay). Corrected in place; the gap-code table was
  already right and is authoritative.
- **Stale line citation**: the §1k surface table cited `App.tsx:112`; the shell
  is at `App.tsx:122`. Corrected.

## APRAS-69 — spec (2026-09-25)

- **APRAS-74 was marked done with its own ER-5 unproven.** "A successful login
  lands the user inside that condominium" has no coverage: `BrandedEntryPage.test.tsx`
  mocks `AuthContext`, `useTenant` and `useNavigate` wholesale and stops at
  `expect(mockLogin).toHaveBeenCalledWith(...)`. APRAS-69 closes it.
- **A card's `expected_results` are overwritten in place and `.meridian/` is
  gitignored**, so the original list is unrecoverable from the repository once
  a spec run replaces it. Fetch and keep the originals before writing.

## APRAS-81 / 83 / 84 — migration chain (2026-09-25)

- **Every spec written before APRAS-87 carries an allowed-path set that cannot
  know about `frontend/src/__tests__/brandTextRole.test.ts`.** That guard
  reconciles a live scan of bare `text-primary` against a declared set, so any
  migration moving an icon onto the token must append a declaration there — and
  the path set then rejects it. Found in APRAS-81 and APRAS-83 during handoff,
  corrected pre-emptively in APRAS-84 and APRAS-85. APRAS-85's set also omitted
  its own spec file.
- **The `.dark` hazard in `frontend/src/index.css` was being explained wrongly**,
  including by the orchestrator in every dispatch. The real reason a bare
  `indexOf(".dark")` fails as a block delimiter: the substring first occurs at
  character 51 inside `@custom-variant dark (&:is(.dark *));` on line 3, before
  the `:root {` block on line 32. The `.dark {` block itself is at line 90,
  *after* `:root {`. One child shipped the false justification in a comment and
  it was corrected in place.
- **APRAS-84's ledger reason cells are per-class templates, not per-site
  descriptions.** Every `text-gray-700` row reads "form field label" and every
  `text-gray-800` row "panel body weight", which is wrong at
  `FeedbackInboxTable.tsx:82` (a table cell), `MediaCarousel.tsx:56`/`:64` and
  `AnnouncementFormModal.tsx:127` (a cancel button). Gap codes and budget
  rationale are right everywhere; only the leading noun phrase drifts.
- **APRAS-81's spec prose carried three stale contrast figures** that the test
  had already corrected: `AssetSummaryCards:52`'s today figure (7.2164 is
  `indigo-700`, the site is `indigo-600` at 5.7621), the `bg-red-500` movement
  ("under 0.05" and "already below 3:1" are both wrong — 0.0712, and it passes),
  and `ProjectUpdateFeed:92`'s attribution. Corrected in place.
- **APRAS-83's §1f case 3 emerald paragraph overstated the band** (17/14 where
  the tree holds 15, 3 migrating and 12 kept) and cited `App.tsx:112` for a
  shell that is at `:122`. Corrected in place.
- **`mediaFeedbackAnnouncementsPackagesContrast.test.ts:543`** asserts a
  recorded literal below today's computed figure; using the computed ratio on
  both sides would close the last literal-vs-computation gap.
- **Four `text-muted-foreground hover:text-muted-foreground` redundancies**
  survive in APRAS-83's files under §1i, which forbids removing a class. Dead
  declarations; worth folding into a follow-up.

## [APRAS-120] Decide how the naive datetime columns survive sqlmodel 0.0.47 — 2026-10-01 (APRAS-120-spec_review-0)

- **T1 as a wall against route 2.** T1 asserts *every* `datetime` column is
  `timezone=False`, and T5 asserts the live schema agrees. A later deliberate
  partial migration of one table to `timezone=True` therefore reddens both. That
  is defensible — a partial migration genuinely breaks every naive reader and
  `clock.db_now()` — but it is the second wall in front of the move APRAS-54
  deferred, and nothing in the test says so. Have T1's assertion message name
  route 2 explicitly: "a task that migrates these columns to `timezone=True`
  must rewrite this assertion and `clock`'s contract together". The `>= 100`
  floor is already correctly written as free to rise.
- **Eleven of the twelve coerced fields are unverified.** Part 4 applies the
  alias to twelve input fields; only `VisitorAuthorizationCreate.valid_from` is
  asserted (T3). A cheap reflective assertion — the twelve named fields carry
  the alias — would make part 4's extent checkable from the repository instead
  of from the spec's file list.
- **Criterion 3 is the only unpinned contract claim.** Every other clock rule in
  this tree is enforced by a test; the docstring wording is left to review. Not
  blocking (QA can read the docstring for the three named clauses), but a
  one-line assertion in `test_lint_hygiene.py` that the docstring names
  `NaiveDatetime` would match the module's own house style.
- **`default_tenant_fixture` becomes dead code** once `autouse` is removed and
  no test requests it by name. Say whether it is deleted or deliberately kept as
  a named lookup for future tests.
- **Fix the frontend citation** to the full path
  `frontend/src/features/visitor-management/components/AuthorizationFormModal.tsx:102-103`.
- Criterion 1 (7-12 min full suite) and criterion 7 (CI-only Postgres) are both
  specified precisely enough to be checked: the lock pin and coverage gate from a
  local run, T5 from the `backend-migrations` job with `assert_no_skips.py`
  guarding against a silent skip. No change needed.

## [APRAS-120] Decide how the naive datetime columns survive sqlmodel 0.0.47 — 2026-10-01 (APRAS-120-spec_review-1)

- §"Files touched" says `backend/app/schemas/` (6 files); the twelve fields live
  in five (`task.py`, `lot.py`, `reservation.py`, `visitor.py`, `voting.py`).
  `app/schemas/__init__.py` is empty, so there is no sixth.
- §"The decision" still says route 2 would "migrate **110** columns"; the
  measured figure the rest of the document now uses is 108. Not blocking — the
  sentence describes a deferred route and no expected result depends on it — but
  it is the last survivor of B3's family and costs one character to fix.
- Expected result 7 refers to `AWARE_COLUMNS` without naming where it lives.
  The spec body pins the home (`tests/test_clock.py`), but QA reads only the
  result strings; adding "the `AWARE_COLUMNS` imported from
  `tests/test_clock.py`" makes the shared-ledger property checkable from the
  criterion alone.
- What is worth asserting about `to_db` is not purity in the immutability sense
  (`datetime` is immutable, so that cannot be violated) but *determinism*: it
  must not read the clock. A one-line test calling it twice, or the existing
  `tzinfo`-scan rule, can carry that.

## [APRAS-120] Decide how the naive datetime columns survive sqlmodel 0.0.47 — 2026-10-01 (APRAS-120-spec_review-2)
- T7's teardown says "restoring the previous value". On this machine `TZ` is
  **unset** in the environment, so a literal `os.environ["TZ"] = saved` where
  `saved` is `None` raises `TypeError` in teardown. `monkeypatch.setenv` /
  `delenv` handles the unset case for free; worth naming in the implementation so
  the developer does not discover it as a teardown error.
- Part 4 claims the coercion fixes the live `visitor_service.py:391` `TypeError`,
  but no criterion pins that fix. T3 covers the storage shape, not the comparison.
  A one-line regression assertion on the authorization-validity path would keep
  the claimed fix from silently regressing — non-blocking, since the fix follows
  structurally from T3's stored value.
- The twelve coerced fields now split by what the client happens to send:
  `valid_from` arrives as `Z` from `toISOString()` and lands in UTC, while
  `start_time` arrives bare from `datetime-local` and lands in wall clock. Both
  are consistent with each service's own `db_now()` comparison and both match
  today's behavior, so nothing regresses — but the frontend asymmetry (same
  widget, two storage meanings) is the thing a future reader will trip over, and
  one sentence in §Out of scope naming it as the follow-up task's real subject
  would help.

## [APRAS-120] Decide how the naive datetime columns survive sqlmodel 0.0.47 — 2026-10-01 (APRAS-120-spec_review-3)

- Part 6 credits only the 33 `toLocaleString` sites. The offset also fixes the
  comparison sites (`VoteBallotCard.tsx:22`, `SpaceBookingPage.tsx:32,116`,
  `AccessLogTimeline.tsx:21-22`, `types/invitations.ts:87`), where today a vote's
  closing deadline is evaluated against a UTC instant parsed as local. Worth one
  sentence, because it is behaviour change, not just display.
- The four excluded calendar-date fields still receive *aware* values from the
  client (`UserLotAssignmentModal.tsx:54-55` sends `new Date(x).toISOString()`,
  `TaskForm.tsx:125-126` sends a `Date`), and they take no `to_db`. Part 4's own
  argument for `to_db` is that an aware value into a `NaiveDatetime` column is
  discarded uncoverted on SQLite and converted through the session zone on
  Postgres — so these four remain the one place where the stored value depends on
  the backend. This is pre-existing and unchanged by the task, so it is not a
  blocking finding, but it belongs in `clock`'s docstring beside the
  column-type follow-up rather than being rediscovered later.
- T9 says "AST scan" and also "has `ApiModel` somewhere in its MRO". An MRO is
  not available from an AST; either resolve bases textually within the file or
  import the modules. Say which, so the implementer does not have to choose.

## [APRAS-120] Decide how the naive datetime columns survive sqlmodel 0.0.47 — 2026-10-01 (APRAS-120-spec_review-4)

- T9's recursion through `list`/`dict` args currently selects no class that a
  declaration scan plus inheritance would not already select (verified: no
  `list[datetime]` or `dict[..., datetime]` field exists in `app/schemas/`). One
  clause in the `Why T9 counts 74` section saying the container recursion is
  future-proofing and contributes 0 of the 11 today would stop a reader inferring
  that `ApiModel` converts datetimes nested in containers — which part 6 measured
  that it does not.
- `Files touched` says 28 schema files while T9 says 27 modules. Both are right
  for what they count, but one half-sentence ("27 defining modules plus the empty
  `__init__.py`") would save the next reviewer the `ls | grep -v` I just ran.

## [APRAS-93] Decide how to make the public obras report cheap to serve without going stale — 2026-10-01
- The board must be refreshed with the new 13-entry `expected_results` list before QA runs. The list the board served predated the latest revision and lacked the D3-reversal entry. Since QA sees only `expected_results`, the reversal gate is only real once the current list is what the board serves. (Done at review time; recorded because the same gap will recur whenever a spec is revised while paused.)
- Two line references have gone stale while the task was paused, and so, more weakly, have the measurements. `_select_milestones` is now at `backend/app/services/project_report_service.py:935`, not `585-596` as §1 says; `_acting_projects` is at `:1513`, not `836-852` as §6 says. The file grew to 1,658 lines under `06333cf`, `37e3f60` and `9d4cf24` (APRAS-113/115/104 — including a new stage detail section that adds rendered bytes), all landed after these numbers were taken. Expect §1's byte sizes to read low against today's renderer, and have the follow-up `selectinload` task re-locate `_acting_projects` rather than trust the quoted range.
- §1's A/B subsection carries a fair amount of method self-correction ("the earlier version of this document said the opposite"). Useful for the operator reading it once; if the document is kept as a reference, consider demoting that narrative to a short footnote so the current numbers lead.

## [APRAS-111] Audit the test suites for tests that prove nothing — 2026-10-01

- ER9 asks whether moving a pin "in the safe direction" keeps the suite green.
  "Safe" is a per-member judgement (lowering `NOQA_CAP` vs. raising a coverage
  threshold vs. raising `BCRYPT_ROUNDS`). Require the `Over-pins` section to
  state, per member, which direction was judged contract-allowed and why —
  otherwise the reviewer can check the mutation but not the claim.
- The backend baseline command is given as `cd backend && SECRET_KEY=test uv run
  pytest`. Nothing in `backend/CLAUDE.md` or `pytest.ini` documents that
  `SECRET_KEY` prefix; worth confirming it is the project's canonical
  invocation (and recording the version/plugin header line in the document), so
  the quoted coverage summary is comparable to what CI produces.
- Record the pristine SHA-256 of each snapshotted file alongside the `cmp`
  result. It makes B3's abort condition trivially checkable and gives the ledger
  a restore proof a reviewer can verify after the scratchpad is gone.
- The `Findings` section would be easier for the follow-up tasks to consume if
  each entry carried the production lines the test is sole cover for (the spec
  already requires this for proposed deletions under ER6 — hoisting it into the
  finding entry avoids the information living in two places).
- Consider stating that the ER8 instrumentation must attribute errors to the
  *currently running case* by Vitest task context rather than by timing, since
  unhandled errors from timers commonly surface after the case that armed them
  has ended — this is exactly the MediaAssets shape.

## [APRAS-119] Find why the backend test job hangs after the tests have already passed — 2026-10-01
- Approach §3 asks to "record the count" of `ResourceWarning: unclosed database` under `-W error::ResourceWarning`, but `-W error` aborts at the first one, so a count is unobtainable from that invocation. The expected result's own wording (outcome verbatim, name the emitting fixture) is fine; the Approach sentence should drop "count" or add a separate non-erroring run with `-W always::ResourceWarning`.
- `-W error::ResourceWarning` promotes *any* `ResourceWarning`, including third-party ones unrelated to SQLite, which can fail the result for a reason that is not the suspect. Worth narrowing with `-W 'error:unclosed database:ResourceWarning'`.
- The spec twice says the two `7cbe5c5` jobs were "killed at 55m by APRAS-107's `timeout-minutes: 45`". A 45-minute job cap cannot end a job at 55m0s unless the extra ten minutes are queue/setup outside the counter. That ten-minute gap is itself evidence bearing on `68f249a`'s decision rule and deserves an explicit line in the findings rather than being carried forward as a rounding.
- The result pinning the `npm run lint` error count against `cd8de18` can be failed by another task's uncommitted edits, since concurrent agents hold work in this tree. Scope it to this task's own diff ("no path under `frontend/` appears in this task's changes").
- The only durable proof that the watchdog fires is a stack dump pasted into prose from an experiment the spec discards. Consider keeping the wedge as a skipped/opt-in test (marker-gated) so the demonstration is re-runnable rather than quoted.

## [APRAS-120] Decide how the naive datetime columns survive sqlmodel 0.0.47 — 2026-10-01
- `backend/pyproject.toml:122` — the justification says "all 22 findings" and "22 per-line suppressions". Measured with the ignore removed, `ruff check` reports 23 (`announcement` 2, `asset` 1, `document` 3, `lot` 2, `permission` 1, `plan` 2, `resident` 1, `role` 2, `task` 3, `tenant` 1, `user` 2, `voting` 3). In a repo whose comments are load-bearing counts, worth correcting to 23.
- `backend/pyproject.toml:122` — a third option existed and was not named in the escalation: `= Field(default_factory=list)` silences RUF012 without any config change (verified on a minimal case against this `ApiModel`), and is the more idiomatic pydantic spelling. The blanket is still defensible, but the residual cost is that a future *non*-pydantic class with a mutable class attribute under `app/schemas/` goes unflagged.
- `backend/app/schemas/base.py:35` — "a field that declares its own serialiser later keeps it" is true for every type **except** `datetime`, whose per-field serialiser output the wrap overwrites unconditionally. No such field exists today; narrowing the sentence would keep the comment honest.
- `backend/tests/test_lint_hygiene.py` — rule 4's raw-text scan for `tzinfo` means no module under `app/` can *document* timezone handling, which already bent `base.py`'s docstring into naming neither spelling. Consistent with rule 3's deliberate precedent, so not a defect, but stripping comments and docstrings before the scan would let the next author explain themselves.

## [APRAS-100] Turn the brand contrast failure into a warning instead of a hard block — 2026-10-01

(see the returned message; identical text)

## [APRAS-119] Find why the backend test job hangs after the tests have already passed — 2026-10-01 (round 2)

- Result 8 should say what a spurious fire looks like in CI (failed step with a
  dump whose stacks show an ordinary shutdown), so the first such occurrence is
  not misread as the hang reproducing.
- Pin the dump destination. At `sessionfinish` pytest's fd-level capture is still
  installed, and `_pytest/faulthandler.py`'s `pytest_unconfigure` calls
  `faulthandler.disable()` and `os.close()`s the dup'd stderr fd it installed —
  so a dump armed with the default `file=sys.stderr` can land in a captured
  buffer or on a closed descriptor. Result 9's wedge experiment would expose this
  locally, but naming the fd in `conftest.py` saves a round.
- §1b names four APRAS-117 commits plus four run ids — nine identifiers for ten
  runs, because `eb4b67c4` has two cancelled runs (`36726903030` push and
  `36659990810` pull_request). Result 2's one-row-per-run-id table makes this
  verifiable regardless; worth fixing the prose.
- `ci.yml`'s steady states for the three jobs needing `timeout-minutes` are
  readable from `gh api .../runs/<id>/jobs` rather than by eye; worth naming the
  command in §7 so the justification is reproducible.

## [APRAS-120] Decide how the naive datetime columns survive sqlmodel 0.0.47 — 2026-10-01 (QA round 1)

- Criterion 8's census wording says "27 modules" and "239 defined"; the scan as written
  covers 28 modules and 240 classes, the extra one being `app/schemas/base.py` / `ApiModel`.
  Worth restating the two numbers in the spec so the next person re-measuring does not go
  looking for a module the scan is missing. The figures the test actually depends on
  (74 dated, floor 70, 63 declaring, 203 rewritten) all reproduce exactly.
- `backend/app/core/__pycache__/clock.cpython-313.pyc` shows up in a naive
  `grep -rln tzinfo app/`. The repo's own scan is `.py`-only so this is harmless, but it
  cost me a second look.
- Follow-ups 1–3 recorded in `clock.py`'s docstring (the three calendar-date columns that
  should be `Date`, datetimes nested in `dict`/`Any` response fields, and
  `TaskForm.tsx`'s off-by-one-day prefill) are correctly scoped out here and are worth
  carrying into tasks of their own rather than leaving only in a docstring.

## [APRAS-111] Audit the test suites for tests that prove nothing — 2026-10-01 (round 2)
- Narrow backend ledger commands inherit `--cov-fail-under=90`. `backend/pytest.ini` sets `addopts = --cov=app --cov-fail-under=90`, so every per-module run ends `FAIL Required test coverage of 90% not reached. Total coverage: 49.69%` and exits non-zero whatever the tests did. Require `--no-cov` on ledger rows (keeping the full-suite baseline command as-is), so a row's outcome is unambiguous to a reviewer re-running it.
- Define whether `N` is per-suite or combined for S2/S3. Both strata print two enumeration commands and carry a "≥ n per suite" split; the stride is described over "the sorted candidate list of size `N`". A single combined list of 593 S2 hits at `k=24` is not guaranteed to yield ≥ 12 per suite. Say "one stride per suite, `k` = the per-suite floor".
- Close the shortfall escape by substitution. Nothing requires the stride to advance past a skipped-unclean candidate to the next clean one, so a single dirty file can legitimately shrink a budget. Require advancing to the next clean candidate and only declaring a shortfall when the clean candidate set itself is smaller than `k`.
- Budget adequacy. S3's candidate set is the largest (563 backend + 551 frontend) and vacuous absence is the cheapest species to create, yet it carries the smallest per-candidate budget (20 of 1114, 1.8%). S2 is 24 of 593. The floors will find a defect only if the defect rate is a few percent. Consider raising S3's floor, or state in the document the detection reasoning so the follow-up sweep is sized from evidence.
- Name S2's mandatory modules by path. "escaping/interpolation, branding/contrast, RBAC parity, infraction escalation, media" is a category list; two auditors would pick different files.
- The probe's "restore" is not a `cmp`. `frontend/src/test/__audit_probe__/leak.test.ts` has no pristine copy, so the restore step does not apply and "leave the file exactly as found, do not re-restore" is the wrong rule for a file the audit itself created. Say that the probe's restore is deletion verified by absence, and that it is deleted even on an abort — otherwise an abort between creation and deletion leaves it in the tree, where the porcelain diff correctly fails the task but nothing removes it.
- The bcrypt premise is stale. S1 states as current "a source anchor spelling `BCRYPT_ROUNDS = 12` literally, and an equality assertion on the floor". Neither is in the module today: the anchor is `assert f"BCRYPT_ROUNDS = {security.BCRYPT_ROUNDS}" in code` and the ratchet is `>= PRODUCTION_FLOOR`. The conditional clause saves the requirement, but drop the stale description and keep the raise-to-13 evidence requirement.
- Collected counts. Frontend is 188 files / 2496 cases as measured today, not "~2457"; the spec's "~" covers it, but the census will record the real figure.

## [APRAS-100] Turn the brand contrast failure into a warning instead of a hard block — 2026-10-01 (round 2)
- `npm run build` is a CI gate and is not in the test criteria. `frontend/package.json` has `"build": "tsc -b && vite build"` and `.github/workflows/ci.yml:240` runs it. Declaring `contrast_warnings: BrandContrastFailure[] | null` as a *required* field breaks three existing typed fixtures the spec does not list: `TenantProfilePage.brand.test.tsx:111`, `components/__tests__/TenantBrandTheme.test.tsx:71`, `components/__tests__/TenantBrandReach.test.tsx:100` (all `const PROFILE: TenantProfile = {…}`). `vitest run` does not typecheck, so the stated criteria would all pass while CI fails. Either name those three fixtures in Files touched, or add `cd frontend && npm run build` to the criteria (preferably both).
- Name the announcement's source explicitly. The Behaviour section establishes "one list, one source" for the panel, then describes case 2 as "the number of failing pairs and the worst measured ratio" without saying whether that is the displayed single list or `clientFailures`. The practical risk is small — with `dark: null` the derived dark is `_simple_scheme` (`branding.py:815-818`), which cannot fail — but one clause ("count and worst come from the same single list the panel renders") removes the choice.
- `role="status"` is already used in this section, by the `savedKey` paragraph (`:990`). It only mounts after a successful save, so `getByRole("status")` is unambiguous in the specified test, but since the live paragraph needs an `id` anyway for `aria-describedby`, say the test locates it by that `id`.
- Say what happens to the two existing all-pass nodes. The emerald panel at `:1036-1041` is gated on `clientFailures.length === 0 && apiFailures.length === 0`; `apiFailures` disappears, so that condition must be re-expressed against the single-source list, and there is a third `allPass` copy at `:1091` (`<p className="sr-only">`). With the live paragraph also carrying `allPass`, that string will render up to three times — harmless for the specified test, worth one line so the implementer does not leave the sr-only duplicate beside a real live region.
- The default-palette consequence is still unrecorded, and it is acceptable. `DEFAULT_PALETTE` (`TenantBrandColors.tsx:72-86`) through `build_theme` fails three light pairs — `primary-foreground/primary` 4.26, `muted-foreground/muted` 4.11, `muted-foreground/background` 4.47 — so a tenant with no stored palette who switches to advanced mode gets the warning panel and an immediate polite announcement. No operator decision is needed: today that same state *disables Save outright*, so this task strictly improves it. But the spec should state it, because the "once every pair clears" arm of the live-region test cannot be reached from the default palette — it must type the `READABLE` fixture, the way `"keeps the save enabled for a palette every pair of which clears AA"` already does.
- `pairFail` drops `scheme`. Server entries carry `scheme`, the copy does not, so a palette failing the same pair in both schemes renders two identical lines — in tension with "shows every failing pair once". Either render the scheme or say the omission is deliberate and inherited from the 422 renderer.
- Two counting/wording slips in text QA reads. The rewrite result says "Four named frontend tests" and then names five (two rewrites plus three assertion re-pointings), and it says "none deleted" while the Test criteria *replaces* `"renders the API's 422 failures even though the client check passed"`; reconcile those. Separately, "the file's six grandfathered `amber`/`emerald` entries" reads as a claim about `themeTokenMigration.exceptions.json`, which holds 882 entries of which 309 mention `amber`/`emerald`; the six are the `TenantBrandColors.tsx` ones (all `task: APRAS-85`) — say so.
- Stale refusal prose in files the spec protects. `backend/tests/test_branding.py:141` and `:937` and the section header `backend/tests/test_tenant_profile.py:473` describe the 422 refusal contract in comments. The spec forbids editing those tests' assertions, which is right; a line permitting comment-only edits there would keep the repo honest.
- Mock residual lean, disclosed rather than hidden: the interactive form, the paste "DEPOIS" box and the API "DEPOIS" label all paint option A, with a note saying B turns those red too. The spec's "if no answer arrives, build A" fallback also names a preference, though now after both options and their costs. If strict neutrality is wanted, paint the interactive panel in a third, token-free grey or offer a toggle.

## [APRAS-119] Find why the backend test job hangs after the tests have already passed — 2026-10-01 (round 3)
- Scope of the result list (21 entries): acceptable as one PR, but three merges would reduce it without losing a requirement. Results 1, 2 and 5 all describe the same occurrence block and could be one row; results 11 and 12 should merge, because read side by side they conflict on their face ("a grace period of 120 seconds" vs "`conftest.py` carries that raised value instead of 120"). The command-level prescriptions (the §4a probe string, `-W error::ResourceWarning`, the anchored `grep -cE`) are worth keeping — for an investigation the exact command *is* the deliverable.
- `wrapper=True` is new-style: the wrapper must `return` the value it received from `yield`, or the hook result becomes `None`. Harmless for `pytest_runtestloop` (pytest ignores it, and pytest-cov's outer wrapper returns its own captured result — confirmed by running it), but naming the return avoids an implementer discovering it the hard way.
- The 19/40 split is a snapshot that drifts hourly — seven of those 19 failures were created today. Phrase the census result as "one row per post-`68f249a` run concluding `failure` as of the census timestamp, with the count stated (19 as of `cd8de18`)", so the result does not go false while the task is in flight.
- Exit code 124 on job `110381880180` is verifiable without the 31 MB log: `gh api repos/:owner/:repo/check-runs/110381880180/annotations` returns `Process completed with exit code 124.` Naming that makes the claim checkable under the spec's own download ban.
- The §4a probe item (iii) is under-specified: "whether the downstream pipe reader saw EOF" does not say what the reader is or how EOF is observed. Name it concretely (e.g. `| cat > out.txt`, then check whether `cat` exited). GNU `timeout` is present locally (`/opt/homebrew/bin/timeout`), so the probe is runnable, but it runs on darwin against an ubuntu fault — §4a should say that a local `cleared` does not clear the CI case.
- Occurrence (a)'s identification is wrong in a small way: "the commit before `13868f7`" is `bd9bd11b`, which has no CI run; (a) is run `36370971185` / job `108767062588` on `e2ccb45b` (two commits earlier). Cite the run and job ids, as the spec does for the others.
- The `ci.yml`-comment result IS mechanically verifiable as phrased, because it requires the comment to name job `110381880180` against `110014916546`/`110405490008` — a grep for three ids. Keep that phrasing rather than softening it.
- The hygiene guards would redden. An AST match on the `faulthandler.dump_traceback_later(...)` call node reached from the arming hook fails when the call is deleted, and the anchored `timeout-minutes:` regex fails when a declaration is removed. These two mutations are real tests, not prose.

## [APRAS-120] Decide how the naive datetime columns survive sqlmodel 0.0.47 — 2026-10-01 (code review round 2)
- The guard would block a switch to `--no-dev`. `pyproject.toml` has a `dev` dependency group and the export includes it, so `requirements.txt` ships `pytest`, `ruff`, `coverage`, `pytest-cov`, `pytest-timeout` to Vercel. Trimming that with `uv export --no-dev` is a legitimate and arguably better change, and `test_every_locked_package_is_pinned_in_the_export` would then fail on those five. Worth either a comment in `backend/tests/test_requirements_export.py` stating that the test is bound to the exact command in the file header, or deriving the lock-side set from the exported groups instead of all `[[package]]` entries.
- Marker-forked resolutions would make the pin-parity test unsound. Both `_export_pins()` and `_lock_versions()` build a dict keyed on canonical name, so if a future resolution forks a package by marker (two `[[package]]` entries, two pinned lines at different versions — uv does this routinely for Python-version splits), each side silently keeps whichever entry came last. The comparison would then fail, or pass, by ordering accident on a correctly regenerated export. Not reachable today (no duplicate names in the lock); keying on `(name, marker)` or asserting no duplicates would make it future-proof.
- Dependabot export drift belongs in its own task. The parity test is the right fix *for this task*: it turns the drift into a red CI job wherever it comes from. The cause — dependabot's `uv` ecosystem writing a lock and an export that disagree in the same commit (twice now, #47 being the second) — is a `.github` infrastructure change and does not belong in a 65-path schema sweep. File it before the next dependabot run: from now on every grouped backend PR will fail this test until `requirements.txt` is regenerated.

## [APRAS-100] Turn the brand contrast failure into a warning instead of a hard block — 2026-10-01 (round 3)
- The "numbers agree across the switch by construction" claim overclaims. `clientFailures` (`TenantBrandColors.tsx:762`) is `auditHexPalette(current.light)` plus the *authored* dark only when `deriveDark` is false, while `profile.contrast_warnings` covers both server-derived schemes. For a stored advanced theme with `deriveDark` true, every dark-scheme warning vanishes from the panel on the first keystroke rather than agreeing at the same number. No expected result depends on the claim; one qualifying clause would do.
- The replacement clean-draft test should say the served profile is `brand_theme.mode === "advanced"` — otherwise the advanced panel is not on screen and, by the spec's own rule, `contrast_warnings` would be `[]`.
- That same test would be far more discriminating if it also asserted the *client's* reading of the prefilled palette is absent: on a clean draft `current = draftFor(profile)`, and `clientFailures` is gated on `current.mode`, not on the draft, so it is non-empty too. Only a pair/ratio the client would not produce proves the server list won.
- The single chosen list is `ContrastFailure[]` (client, no `scheme`) in one arm and `BrandContrastFailure[]` (server, with `scheme`) in the other. Naming the three fields the renderer reads (`pair`, `ratio`, `minimum`) would keep `tsc` from pushing the implementer into a cast.
- The two-`allPass`-nodes result is counted most safely with `getAllByText` (which does not filter `aria-hidden`); naming the query would stop it being attempted with a role query that hides the `aria-hidden` node and collapses the count to one.

## [APRAS-111] Audit the test suites for tests that prove nothing — 2026-10-01 (round 3)
- The ledger's "verified present" is an unbacked y/n, and that is the shape this task exists to catch. Step 2 requires asserting that the new text is present and the original absent, and the ledger records a "verification result"; a single word satisfies it. A mutation that silently failed to apply produces exactly the observation the spec reads as a class-1 finding ("stays green"), so the one field that distinguishes a real finding from a vacuous one is the one field carrying no evidence. Restores are backstopped by the porcelain diff; mutation application has no backstop. Suggested fix: require the row to quote the read-back (the `grep -n` hit on the mutated line, and the empty output of the original-text search) and a checksum pair for the pristine copy and the restored file.
- Baseline reuse is unaddressed, and step 0 doubles the run count. The budgets stay feasible — a narrow backend module run is ~2–4 s (`test_bcrypt_cost.py` ran in 2.30 s) and a single frontend spec is seconds, so ≥74 sampled mutations plus the exhaustive S1 subset, each with a baseline, is tens of minutes of machine time. But the spec says nothing about whether one baseline may serve several mutations of the same module. Literal compliance means one baseline per mutation; the ledger requirement would then be satisfied by pasting the same baseline into several rows, undetectably. Either forbid reuse, or permit it within one module in one session on stated conditions (cleanliness re-asserted, `cmp` clean since, dependency snapshot unchanged) and require the row to name the baseline run it reuses.
- "or whatever the audit's own run finds failing pre-mutation" is acceptable but loose. It lets an audit that found a *different* failure satisfy the result without explaining why the named one stopped failing. Add: if `test_passlib_is_not_installed` is not among the pre-mutation failures, the document says so and reports the `passlib` presence check that explains it.
- 21 expected results is past comfortable, though not past honest. No contradiction found among them, but four pairs are substantially the same gate stated twice and could merge to ~16 without losing a check: the step-0 baseline result and the `Mutation ledger` row-contents result; the derived-config result and the parity-gate result; the no-change-proof result and the three not-examined/abort subsections result; the budgets result and the S3-reasoning result. The per-stratum method detail inside them belongs in Approach, which already carries it.
- Backend collected total: the Scope says "~4155 collected cases"; `pytest --collect-only -q --no-cov` reports 4181 today.

## [APRAS-119] Find why the backend test job hangs after the tests have already passed — 2026-10-01 (round 4)
- Job 109628456192's span is 2758 s = **45m58s**, not the 46m00s the §1a table, §4a and expected result #6 state, while every other row in the table is exact to the second. Either state 45m58s or say the figure is rounded to the minute.
- §2 and expected result #7 describe "three distinct refs wedging inside two minutes on 2026-09-29 (21:26–21:29Z)". Four refs wedged in that window — imgbot 21:26:26Z, types/node 21:27:27Z, jsdom 21:27:47Z, dependabot 2ed8 21:28:56Z — inside 2m30s. Three inside 1m21s is defensible, so this is an understatement rather than an error, but "four refs inside two and a half minutes" is both true and stronger support for the tree-independent reading.
- Add to expected result #14 (or #15) that the **first CI run after the watchdog lands** is recorded in the findings document with its `Backend Tests` conclusion and coverage-gate outcome. As written, the only before/after evidence is local, so nothing in the spec would detect the watchdog firing spuriously on a slower, loaded runner — the one scenario the grace-period arithmetic is extrapolating into.
- The new "every `ci.yml` job carries a `timeout-minutes` declaration" assertion makes the pre-existing `test_the_backend_job_still_carries_its_job_level_backstop` redundant (that test passes as long as any one declaration exists anywhere in the file, so it would survive mutation (b)). Say in §6b whether the old test is replaced or kept.

## [APRAS-120] Decide how the naive datetime columns survive sqlmodel 0.0.47 — 2026-10-01 (QA round 2)
- `backend/tests/test_requirements_export.py` has no explicit count floor, unlike `DATED_COLUMN_FLOOR` (100) and `DATED_SCHEMA_FLOOR` (70) elsewhere in this change. It is not vacuously satisfiable today — both degenerate shapes were probed and each is red — but a local `assert len(locked) >= 40` would make the anti-vacuity property intrinsic rather than resting on `tomllib` raising on an empty lock.
- The export command lives in three places that must agree (generated header, test failure message, developer's shell). A script or make target would prevent regenerating with different flags.

## [APRAS-100] Turn the brand contrast failure into a warning instead of a hard block — 2026-10-01 (round 4, approved)
- Three stale expected-result cross-references. The Test criteria paste bullet says "so expected result 14 is unreachable without it" — result 14 is `public_branding.py` unchanged; the intended target is 12 (tests rewritten in place) or 15 (`npm test` green). The `0.2126` bullet opens "Expected result 12 gets a mechanical guard" — that guard *is* result 13. And the mock's `lum()` comment says "expected result 6 forbids anything like it"; result 6 is the Save button. The numbers read as leftovers from an earlier ordering.
- `TriangleAlert` is already imported at `TenantBrandColors.tsx:11` (used by the paste panel at `:908`). Files touched describes the change as a swap of `OctagonX` for `TriangleAlert` in the `lucide-react` import; the actual edit is only *removing* `OctagonX`. A literal reading produces a duplicate identifier, which `tsc -b` catches immediately, so this is cosmetic.
- "Assert the `sr-only` class" pins a utility name, not the behaviour. It is the only option jsdom affords (no layout, and `clip: rect(0,0,0,0)` is invisible to jest-dom's `toBeVisible`, which is why the prohibition is right), and `sr-only` is already the project's convention here — but a future rename of the utility breaks the test for a non-regression. Worth a one-line comment in the test saying the class is a proxy for "no visual presence".
- Where the section panel's "you can save anyway" sentence lives is left implicit. The mock renders it inside the `{{count}}` paragraph, and Files touched enumerates the i18n keys exhaustively (no third section key), so it must become part of `warningBody`'s new wording. Saying so in one clause removes the only place an implementer could invent an undeclared key — and would also be invisible to the anchor, which uses `toContain`.

## [APRAS-119] Find why the backend test job hangs after the tests have already passed — 2026-10-01 (round 5, approved)
- The census table's `created` column gives `2026-09-29 21:29Z` for job `109628456192` while §2 gives its start as `21:28:56Z`. That is a rounding of the same instant, not a contradiction, but the findings document should carry the second-resolution timestamps since the 2m30s-cluster argument depends on them.
- §4a's phrase "13 jobs, 7 refs and three days" is correct but leaves the reader to re-derive 14 − 1; the findings document would be clearer stating "14 post-`62a136c` occurrences, 13 of them at 55m00s–55m01s".

## [APRAS-111] Audit the test suites for tests that prove nothing — 2026-10-01 (round 4)
- Say explicitly that baseline-reuse condition (c) is discharged by an interim read-only `uv pip freeze` compared against `freeze.before`, since `freeze.after` does not exist until the audit ends.
- Consider capturing `uv pip freeze` per step-0 baseline run rather than only at the two ends, narrowing the resync-then-revert window the before/after pair cannot see.
- Step 0 points to the pre-mutation-baseline section as being "below"; it is above.
- The mutation volume is large for one PR, but it is one coherent deliverable, so not a split.

## [APRAS-111] Audit the test suites for tests that prove nothing — 2026-10-01 (round 5, approved)

- Step 2 (lines 207–208): "Mutations are in-place single-line replacements, so one line number
  serves both" and "where a mutation changes the file's line count" are in mild tension — an
  in-place single-line replacement cannot change the line count. The implementer can read this
  as written (record both numbers when they differ); no ledger field depends on resolving it.
- Have `Census and method` record `shasum -a 256` of `freeze.before` and `freeze.after` as well, so
  the per-baseline-run fingerprints are comparable to the end captures by the same metric rather
  than by re-hashing a quoted block.
- "Each baseline run" captures `cd backend && uv pip freeze`, so frontend baselines will carry a
  backend fingerprint. Harmless; a future task could give the npm dependency set its own equivalent.
- "`toHaveLength(0)` or `assert not ` recurs in almost every S3 module" is 93 of 112 frontend S3
  files as measured — "most" would be exact. Rationale prose only.

## [APRAS-121] Make dependabot's uv runs regenerate requirements.txt with the lock — 2026-10-01

- Place the regenerate-and-diff and dry-run steps **before** the 30-minute
  wrapped pytest step in `Backend Tests`. They are seconds-to-a-minute of work
  and, placed first, they still report when the known hang recurs. Say so in
  §3, and cross-reference APRAS-119 so the two tasks do not conflict over that
  job's step order.
- State in §3 that the dry-run's network dependency is accepted, and whether a
  retry is wanted. A PyPI blip currently becomes a red required check with no
  code cause.
- Say explicitly in §2 that the job is a no-op when the regenerated export is
  byte-identical to the committed one, and that this is what makes the
  `synchronize` event its own push fires terminate. Also consider a
  `concurrency` group keyed on the PR number with
  `cancel-in-progress: true`.
- Add to §4 that the demonstration PR is **closed and its branch deleted**, never
  merged: its committed export is deliberately unsatisfiable.
- Add one sentence to §3 naming what the regenerate-and-diff step adds over the
  existing `test_requirements_export.py` parity assertions (header, ordering,
  markers — i.e. byte-level rather than pin-level), so the step is not later
  removed as duplicated coverage.
- Result 8's "~375 errors" baseline is a moving number for a task that touches
  no frontend file. Consider replacing it with the stricter and more stable "no
  file under `frontend/` is modified" alone.


## [APRAS-98] Give the slug-change dialog Escape and a focus trap — 2026-10-01

- Result 8's "~375 errors across 64 files" is approximate and therefore not checkable. Pin the
  baseline to the commit it was measured on (25e9dc6) or state the criterion purely as "no error
  the base run does not also report".
- `skipcq` staleness: the comment's removal condition ("once the threshold has landed on `master`
  and a run there confirms which of the two explanations held") is now half-satisfied —
  `cyclomatic_complexity_threshold = "medium"` reached master at e71664f. The spec's claim that the
  condition "remain[s] accurate" is weaker than stated. Either note that no master DeepSource run has
  been consulted, or make consulting it a one-line step; do not silently carry a condition whose
  first clause has fired.
- "a `panelRef` on the dialog's panel `<div>`" is ambiguous between the outer `role="dialog"` div and
  the inner `max-w-md ... bg-card` div. It happens not to matter here (this dialog has no focusable
  scrim, unlike ObraPrintDialog), but name the element.
- `ObraPrintDialog`'s component docstring (lines 17-30) describes the focus/Escape/restore behaviour
  as something the component owns. After the extraction it should point at the hook. (The inline
  comment at line 56 pointing to `../lib/focusTrap` disappears with the effect, so no action there.)
- The moved module's docstring opens "Extracted from `ObraPrintDialog` for two reasons" and describes
  "the dialog's keydown handler". That stays true as history, and result 4 requires it verbatim — just
  be aware the file will read as project-management-specific from its new generic home.
- Consider having the guard also assert the *positive* fact — that `ObraPrintDialog.tsx` and
  `TenantProfilePage.tsx` each import from `src/lib/focusTrap` (directly or via the hook). A guard
  that only forbids duplicates passes trivially if both consumers lose the trap entirely.

## [APRAS-91] Cover Navbar's own active markup, which no test reaches — 2026-10-01 (code review)
- Result 5's cited evidence proves the wrong half. Removing `...base` from `stubI18n` reddens exactly the 3 stubbed cases — that proves stubs keep setup's `t`, which is real, but it is not a no-leak proof; a leak manifests in *other* cases. The mutation that actually tests result 5 is deleting the `useTranslation` restore from `afterEach`: green in declared order and at 12 of 13 seeds, **red at `--sequence.seed=42`**. So the restore is genuinely load-bearing and correctly present, but the submission's evidence does not establish it and declaration order alone would never catch its removal. Cite the restore-removal mutation with seed 42 instead.
- `useRoles` is overridden without restore in the new "paints the role subtitle amber while simulating" case (`vi.mocked(useRoles).mockReturnValue(...)` inside the `it`). That is a fresh instance of the exact defect class the spec's hazard list names, for the one mock it omitted. Benign across 13 seeds, and the pattern is pre-existing in the file, so not blocking — but `afterEach` should restore a captured `setupUseRoles` alongside the other two.
- The header-margin exception to result 11 is a legitimate reading but should have been raised. `within(banner)` cannot return the banner itself, so result 11 as written is unsatisfiable for any assertion about the banner's own class — which result 8 requires. The developer's reading is the only one under which both results hold. An inline comment at that case noting it would stop the next reader re-litigating it.
- One permanently-true assertion: `expect(classTokens(subtitle)).not.toContain("text-primary/90")` in the superuser-subtitle case. `Navbar.tsx:155` emits no such token at that site and never has, so no mutation of the subtitle branch can make it fail. Harmless, but it is the shape of assertion this project's nineteen are made of; drop it or justify it.

## [APRAS-102] Show the report's balance cylinder and planned-vs-actual bar in the internal project view — 2026-10-01

## [APRAS-98] Give the slug-change dialog Escape and a focus trap — 2026-10-01 (round 2)
- A is not a ratifiable option — it is the WCAG 2.4.7 gap this task introduces, as the spec itself says. Decision 4 is closed and the mock is really a before/after, so label it "Today" / "After (the house ring)" rather than A / B; an A/B invites an answer of "A", which the spec cannot accept. If an A/B is wanted, both options should be compliant (e.g. `ring-2` vs `ring-2 ring-offset-2`).
- Say which exit paths actually prove restoration. `document.activeElement === document.body` on the Confirm path is determinate but has no discriminating power — it also passes if the hook never restores focus at all. Escape and Cancel are the cases that fail on a regression. Worth stating, so QA does not credit the Confirm case with proving restoration. The Out-of-Scope line for post-settle restoration is honest: today a mouse user clicking Confirm already lands on `<body>`, so nothing regresses.
- Give `M2` an exact pattern. "`querySelectorAll` followed, within the same call's parentheses, by `tabindex`" is not expressible as a regex (unbalanced parens), and case-sensitivity is unstated — `focusTrap.ts:39` is `querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)`, so the generic parameter sits between the two. Something like `/querySelectorAll\s*(<[^>]*>)?\s*\([^)]*tabindex/i` would make two implementers write the same test.
- Add `__tests__/` to the guard's admitted blind spots. The sweep's own exclusion means a second trap, or a second `skipcq: JS-R1005`, placed in a test helper under `__tests__/` is invisible to assertions 1 and 2.
- Assertion 4's "every entry matches the sweep's own filename filter" is self-referential and can only fail on a walk bug. The load-bearing halves are the `>20` count and `M1` → exactly one file.
- Line-number drift: the two dialog buttons open at 447 and 454 (their `className` lines are 450 and 457), not 449 and 456; `alert-modal.tsx`'s Escape effect is 57-65, not 56-63.
- "All three are semantic theme tokens" is loose: `focus-visible:outline-none` and `focus-visible:ring-2` carry no colour at all; only `ring-ring` is a token. The conclusion (no raw palette class) holds.
- One side effect of carrying the `skipcq` comment over verbatim: its "this branch could never see its own fix" is now stale prose on `master`, in the same way the module docstring is — worth adding to the same follow-up the spec already parks in Out of Scope.

## [APRAS-121] Make dependabot's uv runs regenerate requirements.txt with the lock — 2026-10-01 (round 2)

- Say that the whole mechanism only exists once this task's commit is on
  `master`, because `pull_request_target` takes the workflow from the base ref —
  i.e. results 1–5, 7, 8 land first, and result 6 is demonstrated against
  `master` afterwards. Implied by the repository's land-on-master habit, never
  stated.
- Dependabot stops force-pushing a branch it detects as modified by another
  author. That is harmless here (the PR is reviewed and merged, not re-driven),
  but a line in §2 saying so would stop a later reader from reading the bot push
  as interference with dependabot's own updates.
- Require the `$RUNNER_TEMP` copy to be invoked as `bash "$RUNNER_TEMP/…"` (or
  `chmod +x` then execute by absolute path) so nothing resolves the script name
  through `PATH` or the work tree.
- `uv venv --python 3.13` reads `backend/.python-version` (`3.13`) when run from
  `backend/`; harmless, but the explicit `--python 3.13` the spec already
  prescribes is what keeps it so. Worth one clause saying the version is
  explicit and not inherited.
- Rephrase result 5's "offline" per the question above.
- Result 2's "line 2 of the committed export quotes the script's command
  exactly" is true only because `uv` writes its argv verbatim. Add that the
  script must therefore pass a fixed argument list with no conditional flags and
  no `--directory`, or the header differs by invocation site and result 3's
  byte-for-byte claim becomes environment-dependent (related to N1, but a
  distinct cause).

## [APRAS-91] Cover Navbar's own active markup, which no test reaches — 2026-10-01 (QA)

1. **The `afterEach` restore of `useTranslation` is not itself pinned.**
   Deleting the `if (setupUseTranslation) { … }` block from `afterEach`
   (`Navbar.test.tsx:140-142`) leaves the suite fully green: 30/30 still pass.
   The reason is declaration order — the only case that depends on *no*
   `resolvedLanguage` being set ("marks PT active … with the default fixture")
   runs before the three cases that call `stubI18n`, so a leaked
   `resolvedLanguage: "en"` has nothing left to corrupt. Under a different
   declaration order (or a future case appended after the stubbed ones that
   depends on the default `i18n`) the leak would bite, and nothing in the file
   would have warned. This does not make result 5 unmet: the stub always carries
   setup's `t`, so no leak can break a translation lookup — which is exactly
   what result 5 claims, and it is pinned (removing `...base` reddens three
   cases). The gap is narrower: the hygiene that keeps *`i18n` values* from
   leaking is correct but unenforced. Cheapest fix if you want it enforced:
   re-assert the default-fixture PT/EN state in a case declared *after* the
   stubbed ones, or enable `restoreMocks`/`clearMocks` in `vitest.config.ts` so
   the hand-rolled capture-and-restore is no longer load-bearing.
2. **A test that proved nothing was deleted — worth recording as such.** The
   removed case `"fires language change when a language button is clicked"`
   clicked `PT` and then asserted only
   `expect(screen.getByText("Tarefas")).toBeInTheDocument()` — it clicked the
   button and never looked at `changeLanguage`. Its replacement (result 4) does
   assert the call and the argument and the count. This is a genuine improvement
   and a candidate for `docs/suggestions-log.md` / the project's
   "tests that prove nothing" tally rather than a defect in this submission.
3. The `not.toContain("text-primary")` negatives would be slightly more robust
   spelled against the token list helper's intent if the brand-tint form were
   centralised (only one `text-primary/N` occurrence exists in `src` today,
   inside this very test). Purely cosmetic.

## [APRAS-98] Give the slug-change dialog Escape and a focus trap — 2026-10-01 (round 3)

- Flip § 2's default from A to B while keeping the question. A's own stated
  measurement puts a 1.43:1 edge on the irreversible destructive button, the
  margin is machine-checked nowhere (`src/lib/contrast.ts:59` excludes `ring`),
  and for a `<button>` `button.tsx` is the stronger precedent than
  `alert-modal.tsx`'s hand-rolled one. If the operator never answers, the spec
  should ship the stronger indicator.
- Say that option B as specified is *better* than `button.tsx`'s form rather than
  equal to it: `button.tsx:7` and `GeneralDashboardPage.tsx:162` both use bare
  `ring-offset-2` with no offset colour, which resolves to Tailwind v4's
  hard-coded `#fff` and paints a white gap on a dark card. Adding
  `ring-offset-card` is the fix those two sites lack. The mock's "matches
  `button.tsx`" caption undersells it.
- Add a `.dark` row or panel to the mock. Dark mode inverts both figures (ring on
  dark card 6.44:1, ring on dark destructive 1.81:1), and it is the mode where
  `ring-offset-card` versus the `#fff` default is visible.
- Add the clause that `M2` deliberately does not match
  `focusTrap.ts:39`'s `querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)`, so
  nobody "repairs" the regex until it does, and state that `M2` is unproven over
  the real tree.
- Result 8 is conditional on an answer QA cannot see. Once the operator answers,
  edit the result to one unconditional class list rather than leaving the
  disjunction for QA to resolve.

## [APRAS-102] Show the report's balance cylinder and planned-vs-actual bar — 2026-10-01 (round 2)

- §5: "`toFixed` fails three of the six" should read **four** (56.5, 2.5, 42.5,
  42.25 differ; 57.5 and 2.675 agree). The spec's credibility rests on its
  measured numbers; this one is off by one.
- `formatPercent`'s domain is unstated. The `toFixed(20)` approach is sound for
  percentages (the ULP of any value in `0..100` is ≥ ~1e-14, far above the
  20th decimal, so no true non-tie can be flattened into a tie), but it is
  worth saying so, and worth saying what the helper does for `NaN`,
  `±Infinity` and `decimals` outside `0..2` — `Math.abs(NaN).toFixed(20)` has
  no `"."`, and the mock's index arithmetic would silently produce garbage.
  Expected result 2 already forbids `NaN` reaching it from `budgetFigures`, so
  this is defensive only.
- The pinned rounding pairs are all positive, yet the cylinder now prints
  negative percentages. `format(-20.5, '.0f')` is `-20` and `toFixed` gives
  `-21`; the mock already matches Python (`-20`, and `-0` for `-0.5`). Pinning
  one negative tie, e.g. `(-20.5, 0) → "-20"`, would guard the sign path the
  new unclamped text actually exercises.
- B5's test should restore `process.env.TZ` (an `afterAll`, or `vi.stubEnv`).
  The default Vitest pool isolates files today, so nothing leaks, but this
  tree has many TZ-sensitive date suites and no `process.env.TZ` precedent —
  the day someone sets `isolate: false` for speed, the failure appears
  somewhere else entirely.
- §5's bar bullets assert the gap's `left`/`width` "equal `min` and
  `max − min`" without saying in what unit or attribute (the mock uses
  `style.left`/`style.width` in `%`). Naming the percent-string form would
  remove the last implementation choice.
- The `bg-primary/30` ahead-gap composites to roughly a 1.3–1.4:1 difference
  against the `bg-muted` track. The spec correctly argues no contrast minimum
  applies (both numbers are printed and the marker is `bg-foreground`), but it
  is worth a sentence confirming the ahead gap is *expected* to be faint, so a
  reviewer of the implementation does not read it as a missing fill.
- If the operator answers **A** to question 2, the in-tank number would print
  the *unclamped* percentage, whereas `_cylinder_svg` prints the clamped
  `{filled:.0f}%` inside the tank — a second appearance divergence beyond the
  marker, which §2 says is the only one. Worth naming now so answer A does not
  silently contradict §2. Relatedly, in the mock's A2 card the "Saldo restante"
  caption is left with no number beneath it, which makes option A look
  defective in a way the real component would not be.

## [APRAS-121] Make dependabot's uv runs regenerate requirements.txt with the lock — 2026-10-01 (round 3)

- §1/§3 describe dropping `pyproject-file:` as if the input were selecting a uv
  version. In `setup-uv@v8.1.0` it is not a declared input at all (the input is
  `version-file`), so the current steps install **latest** and log an
  unrecognised-input warning. Saying that is strictly stronger than the current
  wording and removes a wrong mental model for whoever next reads the pin.
- The pin test's locator needs narrowing. `ci.yml` has three `setup-uv` blocks
  and only `Backend Tests` gains `version:`; it also contains
  `node-version: 24`, which a naive search for `version:` matches. Say the test
  reads the `version:` input of the `setup-uv` step in the `backend` job (the
  test is N1's whole backstop, so its locator should not be left to taste).
- Give the needle a word boundary and keep it line-scoped. "`uv`, whitespace,
  `export`" matched loosely across newlines false-positives on
  `astral-sh/setup-uv` followed by a shell `export FOO=…` line — plausible in
  exactly the two workflows this task writes. `\buv[ \t]+export\b` per line
  keeps the intent and cannot collide.
- Consider pinning `checksum:` alongside `version:` on the privileged job's
  `setup-uv`, or using a `setup-uv` release that knows `0.12.19`. With the
  default manifest, `download-version.ts` validates only against user input or
  the baked `KNOWN_CHECKSUMS` table, and `validateChecksum` **returns silently**
  (debug-level log) when neither has an entry. `v8.1.0` was published
  `2026-04-16` and `uv 0.12.19` on `2026-09-25`, so the table has no entry: the
  pin names a version but not bytes. This is the repository's existing ambient
  baseline for every other `setup-uv` step, so it is not a regression and not
  blocking — but this is the one job holding a push credential.
- Say who bumps the pin. `uv` ships roughly weekly, dependabot does not update
  a `version:` string input, and a stale pin is safe but silently ages; one
  sentence ("the pin is bumped deliberately, by editing the three literals
  together") closes the question before someone reads the red pin test as a
  bug.
- §2 could note the head's remaining influence on the privileged job for
  completeness: a head `[tool.uv] required-version` (or malformed
  `pyproject.toml`) makes uv refuse to run, so the job fails closed and the
  export is not regenerated. Harmless, and knowing it is a *possible* failure
  mode keeps it from being mistaken for a broken mechanism during the §4 demo.
- Spell out the push refspec. The head checkout is detached at `head.sha`
  (and, with `fetch-depth: 0` now dropped, shallow), so the push must be
  `git push origin HEAD:refs/heads/"$HEAD_REF"`; a bare `git push` on a
  detached HEAD fails. Pushing from a depth-1 clone is fine against GitHub, so
  dropping `fetch-depth: 0` costs nothing else.
- Record in §2 that the repository being **public** is what makes the
  `git fetch --no-tags --depth=1 origin "$BASE_SHA"` variant work with
  `persist-credentials: false`. If visibility ever changes, that variant stops
  working and only the checkout form remains.
- LIVE REPOSITORY FACT found while reviewing this task, independent of it: `astral-sh/setup-uv@v8.1.0` declares `version` and `version-file` and has **no `pyproject-file` input**. All three `setup-uv` steps in `.github/workflows/ci.yml` (lines 45, 135, 188) pass `pyproject-file: backend/pyproject.toml`, which the action therefore ignores — so every CI job installs floating-latest uv, not a pinned one, and has done so silently. Worth a task of its own: either switch to `version-file:` (which does exist) or pin a literal, and decide whether a uv upgrade should ever arrive unannounced in CI.

## [APRAS-98] Give the slug-change dialog Escape and a focus trap — 2026-10-01 (round 4)

- The mock's two "copied VERBATIM from `src/index.css` (lines 32-66 / 90-115)"
  comments describe a *selective* copy: `.dark` carries 12 of the block's 21
  declarations (`--card-foreground`, `--popover`, `--popover-foreground`,
  `--primary-text`, `--secondary`, `--secondary-foreground`, `--accent`,
  `--accent-foreground` are absent), and `:root` likewise. Every value present is
  exact, so nothing is wrong — but "the tokens this mock uses, copied verbatim
  from …" would stop a future reader believing the block is complete and
  reasoning about a token that is not there.
- § Test criteria's 3b tests cannot use bare `renderHook`: RTL's
  `TestComponent` renders `null`, so there is no panel. Both need a small test
  component that renders the panel and calls the hook. Worth one clause, since
  (a)'s premise is "at least two focusable controls in the panel".
- `src/test/setup.ts` and `vitest.config.ts` set no `reactStrictMode` and
  register no document listeners, so "must not wrap the hook in `<StrictMode>`"
  is the default rather than something to arrange. Saying so would keep an
  implementer from adding a defensive opt-out.
- Result 8's disjunction is mechanically checkable (two exact class lists), so it
  is not a gate failure — but collapsing it the moment § 2 is answered remains
  the right move, and the note inside the result is the right place for the
  instruction.
- PROCESS LESSON worth keeping beyond this task: three agents agreed on five wrong contrast figures because all three used the same wrong method (per-channel clip instead of CSS Color 4 chroma reduction). Independence of *agent* is not independence of *method*. `frontend/src/lib/contrast.ts` exists precisely to be the one implementation, and `backend/tests/data/contrast_fixtures.json` carries two anti-clipping cases — so any spec or mock quoting a ratio should be required to derive it by importing that module, never by hand or by a reimplementation, and to say which it did.

## [APRAS-121] Make dependabot's uv runs regenerate requirements.txt with the lock — 2026-10-01 (round 4, approved)

- State explicitly in §2 that `github.head_ref` and
  `github.event.pull_request.base.sha` reach the shell only through a step-level
  `env:` binding, never as `${{ … }}` interpolated inside a `run:` block. The
  spec already writes the safe form (`"$HEAD_REF"`, `"$BASE_SHA"`), but a git
  ref name may legally contain backticks and `$(…)`, so the interpolated
  spelling would be command injection in the one job holding a credential that
  can push to `master` past every required check. Exploiting it needs an actor
  who already has push access, which is why this is a suggestion and not a
  blocking finding — but it is the last head-controlled-text path into the
  privileged shell and code review must verify it.
- Broaden result 8's failure clause from the two named cases to the general one
  already stated in §2, and add that no step in
  `.github/workflows/requirements-export.yml` uses `continue-on-error` or
  otherwise masks a non-zero exit (`|| true`, a trailing `exit 0`). Every other
  unreachable path — `UV_PIN` mismatch, a head-added `required-version`, an
  unreachable `$BASE_SHA`, a rejected push — already fails closed on its own;
  a masked exit status is the only remaining way back to a green run that did
  nothing, and QA reading result 8 alone would not think to look for it.
- Give the summary line one full template rather than a sha plus two outcome
  fragments. §2 says the line names the base sha *and* one of the two outcomes,
  but neither template contains a base-sha placeholder, so its position is
  unspecified. A single written-out shape makes both the grep and any test
  exact.
- Consider requiring, in result 9's *outstanding* branch, a cheap trigger proof
  that needs no credential: a dependabot-shaped PR on which the run exists,
  reaches the export, and then fails at the push step naming the absent
  `REQUIREMENTS_EXPORT_TOKEN` — recording the run id. §2 already mandates that
  failure, so this costs one PR and closes the one case result 8 cannot see:
  the workflow never triggering at all. Without it, the no-secret path lets the
  task finish with the trigger, the branch gate and the base-script fetch never
  exercised.
- Line 118's parenthetical "(the declared inputs are `version` and
  `version-file`)" reads as a complete enumeration and is not one —
  `setup-uv@v8.1.0` declares two dozen inputs, including the `checksum:` this
  same section relies on. "the declared version-selection inputs" would be
  accurate. The load-bearing claim around it, that `pyproject-file:` is not an
  input at all, is correct.
- Record in §2 that the base fetch requires the full 40-character sha: an
  abbreviated id fails with `couldn't find remote ref`, not with anything that
  hints at the cause. `base.sha` is always full, so this is a note for whoever
  next edits that step rather than a change to it.
- Round-4 reviewer's one residual on APRAS-121, flagged for CODE REVIEW rather than the spec: `github.head_ref` reaches the shell. The spec writes the safe form (`"$HEAD_REF"` via `env:`) but never *forbids* `${{ }}` interpolation inside `run:`, and ref names may legally contain backticks. Exploiting it needs an actor who already has push access, so it is not a hole — but code review must check that no `run:` block interpolates `github.head_ref` directly.

## [APRAS-98] Give the slug-change dialog Escape and a focus trap — 2026-10-01 (round 5, approved)

1. The durable fix for the B11 class of defect is not prose in one spec. Either
   add a short rule to `AGENTS.md` ("any contrast ratio or hex published in a
   spec, mock or token comment is produced by importing
   `frontend/src/lib/contrast.ts`; a per-channel clip is forbidden") or file a
   guard task that re-derives hex comments in `docs/tasks/*-mock.html` through
   `contrast.ts`, in the family of `themeContrast.test.ts`. Out of scope for
   APRAS-98.
2. Mock §1: once the operator answers, re-draw the "After" panel in the chosen
   form (`.ring-b` if B stands) so the picture labelled "After" is the thing
   that ships. Harmless today because the caption says which form it is.
3. Mock §1 caption could name the two forms the way the operator sees them
   ("ring touching the button" / "ring with a thin gap") rather than only
   "option A"/"option B", matching §2's plain-language framing.

## [APRAS-102] Show the report's balance cylinder and planned-vs-actual bar — 2026-10-01 (round 3)

- §5 and expected result 9 say "the four selectors" where five nodes are read
  (four `.budget-row` rows plus `.cyl .txt strong`). The cylinder's `58%` node is
  outside the cardinality precondition and outside the named-error clause; the
  digit check still catches its disappearance, so this is wording only.
- Add an explicit presence precondition to the clamp case, in the same spirit as
  result 5's: "exactly one fill node matched". Today a never-rendered fill fails
  by erroring during the parse rather than by a stated assertion, which is right
  but accidental.
- The mock's `formatPercent` **throws** on `NaN` and `Infinity`
  (`kept[cut]` is `undefined` because `Math.abs(NaN).toFixed(20)` has no `"."`),
  while §5 requires the helper to "not emit garbage" for those and to have the
  test pin whatever it returns. An implementer who copies the reference inherits
  a throw. Worth one line in §5 (or a guard in the mock) saying the reference
  implementation deliberately omits that guard.
- §5's behind-state bullet uses `planned = 64, realized = 42.5` while its
  `left`/`width` example uses `realized = 42`; at `42.5` the strings are
  `left: "42.5%"`, `width: "21.5%"`. Harmless, but stating the `42.5` pair
  alongside the example would stop an implementer from pinning `"42%"` there.

## [APRAS-102] Show the report's balance cylinder and planned-vs-actual bar — 2026-10-01 (round 4, approved)

- §5 (line 440) and result 2 (line 557) both say "the arc's `rx 50 ry 12` are
  absolute lengths **outside that range**". `rx = 50` lies *inside* `20..140`;
  only `ry = 12` is outside. The sentence constrains no assertion, so it is not
  blocking, but it is the third round in a row that this one aside has carried a
  false statement. Replacing "outside that range, by design" with "lengths, not
  coordinates" removes the claim entirely rather than correcting it.
- Result 4 opens "Percentages are formatted half-to-even, mirroring Python's
  `format`" without the domain §5 states (`decimals` documented as `0..2`; the
  `toFixed(20)` soundness argument holds for `-100..100`). I verified the claim
  is true across 12,066 cases spanning that whole domain, so nothing fails today;
  the only constructible divergence is `|value| ≥ 1e21`, where `toFixed(20)` goes
  exponential and the non-finite guard does not catch it. Repeating "for
  `decimals` in `0..2`" in result 4 closes the last sweeping phrasing in the
  document.
- §5 is silent on whether `"nan"`/`"inf"`/`"-inf"` may ever reach the screen. They
  cannot — `ProjectDetail`'s three numeric fields are required and non-nullable,
  and `MONEY_SER` serialises `Decimal` to a JSON number — but one sentence saying
  so would stop a later reader from "fixing" the guard to render an em dash and
  breaking a pinned test.
- Under the guard's shape, `formatPercent(undefined, 0)` returns `"-inf"`
  (`Number.isFinite(undefined)` is `false`, `undefined > 0` is `false`) rather
  than throwing. The types close this today; a `Number.isFinite` precondition
  that distinguishes "not a number at all" from "±Infinity" would close it
  structurally.
- §6 requires a comment naming APRAS-102 at the bumped line-number pins, but
  nothing requires one at the two `data-testid` sites. A one-line comment naming
  the clamp test at each id would keep a future tidy-up from reading them as noise
  before it runs the suite. (The convention itself is well established — 168
  non-test `data-testid` occurrences already exist in `frontend/src`.)
- Result 2's lead clause, "a balance cylinder whose filled proportion is the
  remaining-budget percentage", reads unclamped two sentences before the bullet
  pins the clamp. Adding "clamped to `0..100`" to the lead would make the bullet
  self-consistent from its first line.

## [APRAS-97] Give the language buttons a state a screen reader can hear — 2026-10-02 (approved, round 1)

- **Result 2's "same single evaluation" is a structural requirement stated in
  behavioural language.** No test can tell one evaluation from two that agree.
  Consider phrasing it as the inspectable artifact it actually is — "a single
  local binding inside the `map` callback is read by both the `aria-pressed`
  attribute and the `cn(...)` ternary; the predicate text
  `currentLang.startsWith(lang.code)` appears exactly once in the file" — which
  a QA agent can decide by `grep -c` rather than by judging intent.
- **The element-map range `128–143` is the wrapper `<div>` block, not the
  button.** The button element is 130–141 (`LANGUAGES.map` at 129, `))}` at
  142). Since the whole point of that table is to stop an implementer verifying
  against the wrong element, the precise range would serve it better. The
  spec's prose identification ("the element inside the `LANGUAGES.map`
  callback") is unambiguous, so nothing is actually at risk.
- **Result 7 quotes four of the six protected case names.** Inlining all six,
  or replacing the enumeration with the stronger and simpler "no pre-existing
  `it(...)` block in `Navbar.test.tsx` is modified — the diff is additions
  only", would make the result fully self-contained for a QA agent that never
  sees the spec.
- **Result 9 bundles three independent gates in one checkbox** (tsc, coverage,
  per-file lint). Each is decidable, but as one checkbox a partial pass has no
  way to be recorded. Splitting into three results would cost nothing.
- **The grouping relationship can be conveyed with no keyboard obligation,
  and Out of Scope could say so.** The spec rightly declines `role="radiogroup"`
  because of the roving-`tabindex`/arrow-key debt. Worth noting for a follow-up:
  `role="group"` plus an accessible name on the **existing** wrapper `<div>`
  (line 128) conveys "these two belong to one set" without implying any
  keyboard pattern — `role="group"` carries no interaction contract. It would
  need one new i18n key, which is why it belongs in a later task, not this one.
  Mentioning it in Out of Scope would record that the exclusivity gap was seen
  and deferred deliberately, rather than leaving the next reader to re-litigate
  the radiogroup question.
- **The suite is the real guard on the "existing tests still pass" claim.** The
  spec cites an APRAS-91 reviewer who ran it. I confirmed the structural reason
  it is safe (no snapshot or raw-HTML assertions anywhere in the file), which is
  a stronger argument than the citation and could replace it.

## [APRAS-122] Pin uv in CI — 2026-10-02

- **Justify the literal, don't only inherit it.** §D1 explains *which task
  owns* the pin but never why **0.12.19** rather than CI's current 0.12.19↔
  0.12.21 delta. The real reason lives in APRAS-121 (the export's bytes are a
  uv-version artefact and the local script refuses on mismatch, so the
  producing uv must be the developer's). That reason applies to the `Backend
  Tests` step only — `backend-lint`, `backend-migrations` and `migrate.yml` do
  not produce the export, and the spec gives no reason for them to track the
  export's version rather than the newest. One sentence saying "one literal
  everywhere, because the agreement assertion is only meaningful if all four
  are the same string" would close it.
- **"Both specs write the same bytes" is not guaranteed.** Neither spec fixes
  the key order inside the `with:` mapping, so one may produce
  `enable-cache` → `version` and the other `version` → `enable-cache`.
  Harmless (the land-order rules mean only one of them writes the block), but
  the byte-identity claim should either be dropped or made true by fixing the
  key order for all four blocks.
- **§D1's "disjoint inputs" claim is inaccurate.** APRAS-121's agreement test
  reads `ci.yml` too, so the two tests' *inputs* overlap; what is disjoint is
  the two test *modules*. The conclusion ("neither needs editing when the other
  lands") still holds because both read the same value and expect the same
  literal — just state it that way.
- **Make the four mutations committed tests, not a one-time record.** The two
  anti-vacuity assertions in §D3 are adequate as far as they go: a parser that
  returns empty mappings fails the `enable-cache`/non-empty check, and one that
  misses `migrate.yml`'s bare `- uses:` form fails the count equality. But
  neither assertion requires the parser to ever *see* an input outside the
  allow-list — a parser that extracts only `version` and `enable-cache` passes
  both and passes the undeclared-input guard vacuously. Today the only thing
  that catches that is the manual mutation observation in the audit document,
  which does not survive a later refactor. A negative test over an inline
  fixture string (a four-line fake step carrying `pyproject-file:`, asserting
  the detector flags it) needs no dependency and no network, and converts the
  strongest part of the design into something the suite re-checks forever.
  Given this repository's recorded history of guards that passed while
  examining nothing, this is the change I would most like to see.
- **The count-equality assertion is partly self-referential** — both sides are
  derived from the same grep over the same text. Asserting that the discovered
  steps include at least one from `ci.yml` *and* one from `migrate.yml` (i.e.
  both spellings exercised) is cheap and catches the one regression the
  equality cannot.
- **Result 1's `grep -rc 'pyproject-file'`** counts matches in comments too and
  its exit status is nonzero when nothing matches, which makes it awkward as a
  pass condition; `grep -rn … | wc -l` equal to 0 is less surprising to QA.
- **Result 10's `AGENTS.md` claims** are prose assertions with no committed
  check, while this repository already has the convention for exactly that
  (`backend/tests/test_docs_agents_md.py` asserts literal claim strings).
  Optional, but the convention exists.
- **The third-party audit could be its own task.** It is the one part of
  APRAS-122 that is a separate, independently shippable deliverable (a
  document inventorying 12 refs, each verified via `gh api`). It is bounded
  and read-only, so it does not make the task un-reviewable — which is why
  this is a suggestion and not `NEEDS_SPLIT`.


## [APRAS-122] — 2026-10-02 (round 2)

- **S1.** Reword §D1's second justification to the precise claim. `backend-lint`,
  `backend-migrations` and `migrate.yml` run `uv sync --all-groups` with **no
  `--frozen`/`--locked`**, so a newer uv there may re-lock and install something the
  `--frozen` export can never surface; in the ordinary fresh-lock case the uv version only
  affects *reading* the lock. "`backend/uv.lock` is resolved by uv" as written overstates it,
  and the precise version is the stronger argument. Worth adding that APRAS-121's
  `uv lock --check` lands only in `Backend Tests`, so the other three jobs keep an ungated
  non-frozen `uv sync`.
- **S2.** Close the post-hoc gap on production cheaply: `ci.yml` already declares
  `workflow_dispatch`, so a dispatched CI run on the pin commit *before* it lands on `master`
  would observe `Backend Tests`, `Backend Migration Tests (Postgres)` and `Backend Lint (ruff)`
  green on 0.12.19 while `migrate.yml` (which has no `workflow_dispatch` and no `paths:`
  filter, and fires on every push to `master`) has not yet run against production. Recording
  that pre-landing run id alongside the after-state would make the backwards pin verified
  rather than merely witnessed.
- **S3.** Have §D3.4 and result 7 name the shared entry point: the fixture test and the
  real-tree scan must call the same text → steps parser, so a later refactor cannot satisfy the
  fixture through a separate helper while the file-reading path drifts.
- **S4.** Result 3 is satisfiable by a re-run of a job that failed on its first attempt, which
  §D4's "not a flake to re-run away" forbids in prose only. Requiring the recorded conclusion
  to be from `run_attempt` 1 would make that mechanical.
- **S5.** §D6's table gives the `setup-uv` row's `with:` keys as `enable-cache`,
  `pyproject-file` — the **pre-fix** state, while the audit document lands *after* the fix,
  where the keys are `version`, `enable-cache` (plus `checksum` on APRAS-121's step). Say which
  state the inventory records, or give both.

## [APRAS-123] — 2026-10-02 (round 1)

- **S1** — §4's "123 tracked documents (96 `.md`, 27 `.html`)" counts
  `docs/tasks/` only. The scanned set also includes `docs/frontend/**/*.md`,
  which at `2cb0d48` holds `theme-token-mapping.md` and `unmapped-colours.md`:
  the true figure is **125 (98 `.md`, 27 `.html`)**. The `≥ 100` floor holds
  either way, but a measurement-provenance slip inside a spec about measurement
  provenance is worth correcting on principle.
- **S2** — "compares to **4 decimal places**" is implementable two ways:
  `derived.toFixed(4) === marker` (rounding equality) or
  `toBeCloseTo(marker, 4)` (|diff| < 5e-5). They differ at the boundary. Name
  one. All four seeded figures pass under either, so this is not blocking.
- **S3** — Close the hole B2's needle list leaves open by pinning the guard's
  imports in the same assertion: the file's `import` specifiers are exactly
  `node:fs`, `node:url` (or `node:path`), `vitest` and `../lib/contrast`. That
  catches both a reimplementation with differently-written constants and
  `import Color from "colorjs.io"`, neither of which any needle sees, and it is
  as mechanical as the needle scan.
- **S4** — Reword result 6 so it does not overclaim. The `≥ 4` marker assertion
  is a regression pin on four stated figures, not coverage of prose ratios;
  §5's body is honest about this but the result reads as though ratios are now
  handled. Say "four marked ratios are pinned and re-derived; unmarked prose
  ratios remain unguarded, per §5".
- **S5** — §2 names only two of the four naive false positives. Name the other
  two as well: `docs/tasks/APRAS-68-spec.md:477` pairs an unrelated `oklch()`
  with an unrelated hex inside one sentence, and
  `docs/tasks/APRAS-92-spec.md:717` carries the hex inside a "contains none of"
  assertion. Neither is excluded by the ordering rule — only by connector
  anchoring — so they are the stronger argument against the naive shape.
- **S6** — Three floors sit exactly at the committed measurement (8 contributing
  documents, 17 claims, 5 shape-A in `APRAS-90-mock.html`, 4 shape-B in
  `APRAS-76-mock.html`). Correct for floors, and the spec already permits
  raising them to the landing commit's figures — worth noting in §4 that the
  new provenance document's own inventory and markers will raise the real count
  well above 17, so the landing figures should be re-measured rather than
  copied from §4.
- **S7** — The provenance document should carry the derived hex beside each of
  the 19 inventory entries (result 8 already asks for this); the list in §0 of
  this review is the measured set and can be used verbatim.

## [APRAS-122] — 2026-10-02 (round 3)

- Result 4, even in its preferred branch, does not require the dispatched run's
  head sha to equal the landing commit sha. Add that equality; "the pin commit"
  implies it but QA reads the sentence, not the implication.
- `§D1`'s second argument would survive the next round better with one clause
  marking it unmeasured — e.g. "not observed on today's lock; stated as a
  possibility the pin forecloses" — since the re-resolution path cannot be
  demonstrated under this task's constraints.
- `§D1` says `uv lock --check` leaves "those three jobs" with an ungated
  non-frozen `uv sync`. Note that it gates only the staleness branch, not the
  lock-format branch, so `Backend Tests` is not fully gated either.
- A narrow relaxation of `run_attempt` 1 that keeps the gate honest: allow a
  later attempt **only** when attempt 1's conclusion is also recorded, with the
  failing job, step and log excerpt, and an explicit statement of why the
  failure is not uv-related. Silence about attempt 1 stays inadmissible.

## [APRAS-123] — 2026-10-02 (round 2)

- **§7 — soften or close the dynamic-import hole.** "It is strictly stronger
  than the needle list" is not quite true: `const C = await
  import("colorjs.io")` is a fourth dependency that the `^\s*import` anchor does
  not reject, and a bare `import "x";` with no `from` clause escapes a
  `from`-requiring regex. Either add `await import(`, `require(` and the bare
  `import "<specifier>";` form to what the pin rejects, or say "stronger in the
  cases that matter, and static-import-only" and record the residual risk as §5
  does for prose ratios. The threat model here is an honest agent, so the hole
  is theoretical — but this spec's subject is criteria that overclaim.
- **§7 — pin the formatting assumption in one clause.** The line anchor depends
  on each `import` statement sitting on a single line. That is this
  repository's actual style (no Prettier config; imports up to 388 characters),
  but the four-name `../lib/contrast` import is 83 characters and any future
  formatter would wrap it and break the required-member half of the pin. One
  sentence — "each import is written on a single line, which the anchor
  requires" — removes the trap.
- **Result 11 vs result 12 — one word.** Result 12 says "the **only** permitted
  edit to an existing `docs/tasks/` document is §8's repair", while result 11
  requires a temporary edit to `docs/tasks/APRAS-90-mock.html` for the
  proven-to-fail run. Both implementers would do the same thing, so this is not
  blocking, but "the only permitted **committed** edit" removes a literal
  contradiction of the same family as round 1's B5.
- **§4's "well above these figures" is wrong as written.** Per the blocking
  finding, the inventory table contributes no claims, so the landing counts rise
  by roughly one document and whatever claims the provenance document's prose
  happens to carry. The instruction to re-measure rather than copy is right and
  should stay; the justification should be corrected (and will change anyway if
  the table becomes machine-checked).
- **§10's quoted line.** `docs/tasks/APRAS-90-mock.html:16` is
  `--primary: #009f68;       /* oklch(0.62 0.15 160) */` with run-in
  whitespace; the spec quotes it with single spaces. Harmless, since only the
  hex is replaced, but the shape-A matcher must tolerate multiple spaces before
  the comment — worth noting since that is how the real sentinel is written.
- **Positive note, no action.** My independent three-shape implementation
  reproduced §4 and §8 exactly — 17 claims, 8 documents, 125 documents, 0
  mismatches committed; 0 mismatches over the whole working tree — and the 19-row
  inventory, the four ratios and the gamut asymmetry are all exact. Apart from
  the finding above, this spec's figures are the best-substantiated of the chain.

## [APRAS-122] — 2026-10-02 (round 4)

- Add one sentence to §D4 step 4: if `master` has advanced and the fast-forward
  is no longer possible, the dispatch is repeated on the new commit — the sha
  equality is not to be reconciled by rebasing. This makes explicit what the
  equality requirement already enforces implicitly, and matches the operator's
  `git push origin <sha>:master` landing path.
- §D4 could name `git push origin <sha>:master` as the concrete form of step 4,
  since that is how these commits are actually landed here and it satisfies
  "no amend, no rebase, no squash" by construction.
- Result 12: consider "for one reason, with one consequence" phrasing rather than
  "those two reasons", to match §D1's one-argument-carries-it structure.
- PROCESS GAP found 2026-10-02: the Meridian server DOES accept a `questions` array on `PUT /api/projects/tasks/<id>` (`server.js:1840-1841` validates and writes it), but the schema reference's "Update accepts" list omits the field. Agents reading only the schema therefore believe operator questions cannot be persisted and leave them in chat, where QA and the board cannot see them — which is exactly how APRAS-122 ended up with an expected result whose escape branch quoted a refusal that existed nowhere checkable. Worth correcting in the schema doc, or worth a task.

## [APRAS-122] Pin uv in CI — 2026-10-02 (round 5, approved)
- §D4's "the implementer reads but never writes `questions`" is a convention, not a lock — the array is writable through the ordinary update endpoint and the schema has no per-answer authorship field, so no change to this spec can make it enforceable. The risk is bounded by visibility rather than by mechanism: a forged refusal appears on the operator's own card, under a question they never answered. Worth a task if the project ever wants operator decisions to be cryptographically attributable.
- Result 4's "the sha `master` landed" admits a merge-commit reading in which the pin commit's sha is recorded while `master`'s tip is a new merge commit. §D4 step 4 forbids that by requiring a fast-forward, and results 3 and 5 still cover the landing tree, so it was left as written.
- Branch 2 of result 4 names the record but no read command, unlike branch 1's `gh run view --json headSha`. The read path is `questions` on the task line in `.meridian/tasks.jsonl` (only `expected_results` lives in the per-id detail file), which works even with the Meridian API down — worth naming in the result.

## [APRAS-123] — 2026-10-02 (round 3)

## [APRAS-123] — 2026-10-02 (round 4)

- **§4's post-landing expectation undercounts by this spec's own 8 claims.** §4
  says "Expected post-landing measurement, for comparison: 126 documents read, 9
  contributing, 20 claims", reasoning only from
  `docs/frontend/contrast-provenance.md` entering the scanned set. But §9 lands
  `docs/tasks/APRAS-123-spec.md` too, and that file contributes 8 claims (table
  above). The expectation should read **127 documents, 10 contributing, 28
  claims** (17 committed + 3 from the provenance document + 8 from this spec).
  Non-blocking because no expected result asserts it, the floors (≥ 100 / ≥ 8 /
  ≥ 17) all still hold, and the spec tells the implementer to re-measure rather
  than copy. Worth fixing anyway: an implementer who measures 28 against an
  expected 20 has no guidance for a surplus and may go looking for a shape-C
  over-match that is not there.
- **Name where QA reads the 19 pairs from.** Result 8 lists the rows by token
  name; the `oklch()`/hex values live in `docs/frontend/contrast-provenance.md`.
  One clause ("read from the provenance document's table") makes the grep
  self-contained for an agent holding only the results.
- **Close the non-awaited dynamic import.** Replacing `/await\s+import\s*\(/`
  with `/import\s*\(/` catches `import("colorjs.io").then(…)` as well as the
  awaited form, and I verified it is still self-safe: `/import\s*\(/` does not
  match its own source text `import\s*\(` (the character after `import` is `\`,
  neither whitespace nor `(`), and it does not match `import.meta.url`, which §3
  requires the file to carry. If kept as-is, say in §7 that the non-awaited form
  is a third stated hole, so the list of admitted holes is complete.
- **Split result 10.** It covers the import pin, the two dynamic-import regexes,
  two files being unchanged, and a conditional interaction with APRAS-100's
  guard. Three results would each be verifiable on its own and would make a
  partial implementation visible.

## [APRAS-123] Guard the hex and ratio comments in docs/tasks mocks — 2026-10-02 (round 5, approved)
- STRUCTURAL RECOMMENDATION, worth more than the five textual fixes it would have replaced: state result 5's sentinel as a pair **parsed from the provenance document** rather than written as a literal in the test. Then the test holds no inventory value at all, result 8's grep becomes total, and the exemption plus its quantifier clause disappear. §7 already reached exactly this conclusion for its own needles in round 2 (regex literals whose source is not what they match); result 8 did not inherit it. This is the general shape of the defect family that cost this spec five rounds: every instrument in the task examines text that contains it, so each fix relocates the self-reference instead of removing it. Deriving the sentinel rather than quoting it is the move that ends the family.
- §4's "Expected post-landing measurement … 126 documents read, 9 contributing, 20 claims" forgets that this spec is itself a committed deliverable under `docs/tasks/` contributing 1 document and 8 claims (lines 50, 51, 52, 317, 318, 319, 455, 514 — all correct values). Real figure ≈ 127 / 10 / 28. Non-blocking: the binding floors are `≥` and §4 orders re-measurement at landing, so the error is in the safe direction — but it is the fifth instance of the same family, in the spec's own arithmetic about itself.
- Five stale `result N` cross-references (§4 "result 4", §5 "result 2", §6 "result 5", §10 "result 3", §8 "result 11"/"result 12") track an earlier numbering; harmless but worth a renumbering pass.
- The round-5 reviewer reported that the Meridian record carries no `expected_results`. It does — 15 items in `.meridian/tasks/APRAS-123.json` and on the hydrated route. The field deliberately does not travel on the `tasks.jsonl` line (schema: "`expected_results` does not travel on the line"), so a reviewer reading the line sees nothing. Worth knowing before someone "fixes" a non-problem.

## [APRAS-111] Audit the test suites for tests that prove nothing — 2026-10-02 (code review)

- **S-01** — Give each of the three invalidated S4 rows an in-row marker.
  `docs/audits/APRAS-111-test-suite-audit.md:4184` (`S4-FE-04`), and the
  corresponding `S4-FE-08` and `S4-FE-10` row bodies. Add
  `**INVALIDATED — measured nothing (0 tests collected, exit 1); see -04r**` to
  the row, and replace the reasoned `no — expected: …` in the
  `Was it among the reddened?` field, which currently reads like a real
  adjudication. The agent's own sentence in EK-15 is the argument for this:
  a row that collected nothing looks, in a summary, exactly like a row whose
  mutation nothing caught — and that is true of these three rows read on their
  own, which is how a follow-up will read them.

- **S-02** — Two summary miscounts, both understating the work, with the
  authoritative per-row data correct in each case:
  - line 167: "**96** interim captures (`freeze.i01` … `freeze.i96`)". The
    ledger carries 99, `freeze.i01`…`freeze.i99`, each named exactly once
    against 99 reusing rows. Should read 99 / `i99`.
  - line 731: "the 68 backend mutation rows' modules". Backend rows are
    43 (S1) + 25 (S2) + 22 (S3) = 90; 68 omits S3 backend entirely. 90 + 93
    frontend = 183, which is the figure that reconciles.

- **S-03** — The 99 reuse rows state the interim capture was "compared against
  `freeze.before`", but `freeze.before` is the pre-resync capture containing
  `sqlmodel==0.0.38`. A genuine comparison against it would have shown the
  `sqlmodel` line in all 99 rows, and none did, so the comparisons were against
  `freeze.before2` and the filename in the rows is wrong. Worth correcting
  because the whole point of the capture is to name which set was compared.

- **S-04** — Add one sentence to "The bare load: observed, not assumed" naming
  APRAS-123 and stating that the preexisting `node_modules` symlink and
  `{"type":"module"}` `package.json` dated 2026-10-01 17:02 are the plausible
  explanation of the earlier round's contrary observation. The observation is
  already recorded correctly; this turns it into evidence the sibling task can
  cite without re-deriving the inference.

- **S-05** — Record the one limit of the ER8 positive control: the probe was run
  alone, not as an extra file inside the full instrumented run, so the control
  does not strictly exclude a full-run-only suppression of the recorder (a
  write race on the single append path being the realistic one). `setupFiles`
  run per file, so the inference carries; a sentence stating the limit is
  cheaper than re-running and keeps the zero honest about its own support.

- **S-06** — `frontend/vitest.config.ts`'s `test.coverage.thresholds` is the one
  S1 threshold-subset member with no mutation behind it, excluded because
  expected result 14 forbids editing that file. The document discloses this
  twice (lines 338-340, 5376) and routes it to FU-02 without claiming a
  finding, which is the correct handling of a spec that asks for exhaustive
  bidirectional mutation of config thresholds while also forbidding edits to
  that file. Worth noting that the prohibition was written for the ER8
  instrumented run, and the ordinary protocol — `cp` aside, mutate, run,
  `cp` back, `cmp` — would have applied to it as safely as to `pytest.ini`.
  A future spec should resolve the conflict rather than leave the auditor to.


## [APRAS-111] Audit the test suites for tests that prove nothing — 2026-10-02 (code review round 2, approved)

1. **Numeric collision between "183 figures" and "183 rows."** Line 358 says
   "183 figures changed" while lines 14, 298, 824, 839 and 845 use 183 for the
   row count. The two are unrelated quantities that coincide. In a document whose
   entire subject is a number that was mistaken for a different number, a reader
   skimming the note may read line 358 as "every row changed." Disambiguating it
   — e.g. "183 of the 186 file figures changed" — would cost six words. Context
   makes it recoverable today, so this is not blocking.
2. **The note's population count could name its own denominator.** The note says
   "every one of the 186 frontend run summaries," which is right, but the document
   also contains four further `(files N)` strings (three banners, one prose
   sentence). A half-sentence noting that the quotations outside the ledger were
   updated with their sources would close the gap between "186 summaries" and the
   190 occurrences a reviewer's `grep` returns — which is the arithmetic I had to
   reconstruct to satisfy myself nothing had been missed.
3. Optional, for the follow-up sweeps: the per-row validation I ran is eight lines
   of Python over the retained `runs/*.json`. Retaining it beside the artefacts
   would let FU-13/FU-14 re-assert the row-to-artefact mapping without rebuilding
   the parser.

## [APRAS-97] Give the language buttons a state a screen reader can hear — 2026-10-05 (code review, approved)

- `2cb0d48` is on local `master` but **not pushed**. Nothing in APRAS-97 depends
  on that, but while it is unpushed it is rewritable, and rewriting it would
  orphan this change's base. Push `master` before (or right after) landing
  APRAS-97, and in the meantime do not rebase or amend `2cb0d48`.
- `Navbar.test.tsx` has six pre-existing `prettier --check` disagreements and 26
  pre-existing `@typescript-eslint/no-explicit-any` errors, several of them
  avoidable now that `directorUser()` and `renderBanner` exist. Both are worth a
  dedicated cleanup task — and the formatting one is worth doing *before* any
  future task adds cases to this file, so the next author is not forced into the
  same choice between `--write` and a byte-identical-cases requirement. Neither
  belongs in APRAS-97.
- The `pt-BR` case could add `expect(classTokens(en)).not.toContain("bg-primary")`
  for symmetry with the other two cases. Cosmetic.
- The logout button (lines 164–169) still has no `type="button"`, correctly left
  alone by this spec. The sweep task the Out of Scope section anticipates is
  worth creating so it is not forgotten.

---

**VERDICT: APPROVED**

Blocking findings: **None.**

## [APRAS-110] Show the acting condominium logo in the header — 2026-10-05 (spec review round 1, rejected)

- `Navbar.tsx:65` has no literal `role="banner"`; the role is implicit. Write it
  as "the `<header>` (implicitly `role="banner"`)" so nobody greps for an
  attribute that is not there.
- "the other four `<header>` elements in `src` are page-section headings" is
  true of three. `LandingPage.tsx:29` is a direct child of a `div` on a public
  route outside `AppChrome`, so it is a `banner` landmark too. Inconsequential
  (it never co-renders with `Navbar`), but the sentence as written is wrong.
- Write the `vi.mock` default **inside** the factory (`useTenantProfile: vi.fn(() => NO_LOGO)`),
  not via a later `mockReturnValue`. `Navbar.tenantAdmin.test.tsx:89` calls
  `vi.restoreAllMocks()` in `beforeEach`, and `Navbar.test.tsx:52-56` documents
  that the config sets neither `restoreMocks` nor `clearMocks`. On the installed
  Vitest 4.1.11 an implementation passed to `vi.fn(impl)` survives the restore
  and one installed afterwards does not — worth one sentence in §Files touched
  so the developer does not lose a round to it.
- Say explicitly that a logo which loads but is transparent or blank is accepted
  and undetectable (no `onError`, and distinguishing it would mean sampling
  pixels). The visible result is an empty slot that looks like a bug, so it is
  better acknowledged than silent.
- `w-auto` is already the `<img>` default; asserting it documents intent but
  guards nothing. Keep it, and say that is why.
- The measured lint baseline on this checkout is `370 problems (368 errors, 2
  warnings)`, not "roughly 375 errors across 64 files". The "not worse" framing
  is right; the number should match what the command prints.
- ER1 says `grep -c … returns 0`. `grep -c` *prints* 0 and *exits* 1 when there
  is no match. Write it as "prints 0" so the criterion is not read as an exit
  status.
- The mock renders five cards for six states, merging no-logo/loading/error into
  one (correctly — the output is identical). ER15 enumerates six states; either
  say the three share a card or have ER15 list what is actually drawn.
- Mock lines 7-8 load Tailwind and Lucide from CDNs, so "opens standalone" means
  "needs no build step", not "works offline". Fine as the house convention, but
  ER15's "opens standalone" is worth qualifying.
- Neither existing renderer handles `onError` (`TenantProfilePage.tsx:239`,
  `BrandedEntryPage.tsx:195`), so today a broken logo shows the browser's broken
  image icon on both. This task's state 5 is strictly better; saying so would
  make clear it is a deliberate improvement rather than an inconsistency with
  the two precedents the spec otherwise follows closely.

VERDICT: REJECTED

1. The logo bytes are a new app-wide request against an uncached,
   rate-limited (`@limiter.limit("30/minute")` per IP, no `Cache-Control`, no
   `ETag`) public route whose own docstring names this amplification as the open
   concern; §Approach's "the header adds no network request" is true only of the
   `/tenant-profile` JSON, §Out of Scope disclaims only cache *staleness*, no
   429 state is enumerated, and ER14 forecloses fixing it in-task — so the
   decision must be recorded.
2. The `onError` latch wedges permanently for a single-condominium user: the
   switcher does not render below two memberships, so the slug never changes,
   and `Navbar` is mounted above the `<Outlet/>` so it never unmounts. The
   spec's stated escape ("switching condominium retries") is unreachable for
   exactly the user the task exists for. A second clearing condition and a
   criterion driving it are needed.
3. ER8 requires "a fixed height token" and "a `max-w-*` token" without naming
   either, so QA holding only the expected results cannot decide pass or fail.
   The mock already fixes `h-7 w-auto max-w-32 object-contain`; state those
   literals, and say the mock's extreme-aspect card is where letterboxing is
   actually demonstrated.
4. "The fallback mark is present" (ER4, ER5, ER6, ER7) names an element with no
   stated selector — a decorative `div` with no role, name, text or test id. The
   obvious `querySelector(".size-3.5")` is the cheap presence assertion this
   project's audit exists to prevent. Bind the phrase to the discriminating pair
   already in ER4 (`getByRole("link", { name: "APRAS" })` plus no `img` in the
   banner), and use one noun for it across all four criteria.
5. "keyed on the `src` it failed for" is implementable two ways — the URL of the
   current render, or `event.currentTarget.src` — which differ when the slug
   changes mid-flight, and ER7 passes under both. State which URL is stored and
   that the comparison is against the render, not the element.

## [APRAS-97] — 2026-10-05 (QA, approved; shipped at 1f0079b)
- QA re-ran every gate and both mutations independently; nothing to carry forward.

## [APRAS-111] — 2026-10-05 (QA round 2, approved; shipped at e1d19f2)
- QA round 1 caught 99 ledger rows asserting an empty freeze diff that was not empty; fixed by naming freeze.before2 and disclosing the sqlmodel delta. Lesson already recorded: a comparison stated as empty is worth re-running.
- QA hit two of its own false-zero greps (mid-phrase bolding, and a label that reads `Step-2 read-back (line-scoped)`); positive controls caught both before they became findings. Keep requiring positive controls on every zero-hit search.

## [APRAS-110] Show the acting condominium logo in the header — 2026-10-05 (spec review round 2, approved)

- ER8 asserts `vi.advanceTimersByTime(59_000)` and `vi.advanceTimersByTime(2_000)`
  bare. A `setState` inside a `setTimeout` callback is not wrapped by anything
  RTL provides, so under React 19 the update is scheduled rather than flushed and
  a synchronous assertion immediately after the advance can read a pre-update DOM
  (and will at minimum emit an act warning). Write the advances as
  `act(() => { vi.advanceTimersByTime(59_000); })`. The assertions are right; only
  the mechanics need naming, and naming them saves a developer round.
- ER3's parenthetical — "the banner still exposes exactly one link
  (`getAllByRole("link")` has length 1)" — is unscoped, while ER2, ER7 and ER10
  scope their queries with `within(screen.getByRole("banner"))`. `Navbar` renders
  `<Sidebar />` as a sibling of the `<header>`, and the sidebar's links are why
  `Navbar.test.tsx`'s existing one-link case scopes to the banner. Write it as
  `within(screen.getByRole("banner")).getAllByRole("link")` so no reader has to
  reconcile a criterion that needs a banner in scope with one that counts every
  link on the screen.
- The spec cites `Navbar.test.tsx:912` for the "exposes exactly one link in the
  banner, the appName logo pointing at /" case. It is now at **line 995** — two
  commits landed test cases in that file since round 1 (`2cb0d48` APRAS-91,
  `1f0079b` APRAS-97). The quoted case title is exact and unique, so nothing is
  lost; drop the line number, or expect it to drift again while the task sits in
  the queue.
- ER8 opens with "(a) after the error of the previous result", inside a criterion
  that also says "one case". §Test criteria describes the same thing as a
  four-step sequence that includes the error. Restate the error as step (a) of
  this case so a QA agent holding only the expected results does not have to
  infer that ER7's `fireEvent.error` is re-performed here.
- §"The cost of the logo bytes" says the `<img>` "mounts once per full document
  load". The public routes sit outside `AppChrome` by design (`App.tsx:157-161`),
  so navigating to `/c/<slug>/…` and back unmounts and remounts `Navbar` and buys
  a second pair of requests within one document load. Still bounded by a small
  constant and nowhere near the 30/minute budget — worth a half-sentence so the
  figure is not read as a hard invariant.
- §"The latch and its recovery" says "no refetch of `["tenantProfile"]` occurs for
  a user who stays on the app". Two paths exist: `refetchOnReconnect` defaults to
  `true` in react-query v5 and is not overridden in `main.tsx`, and
  `pages/TenantProfilePage.tsx:80` mounts the hook itself, so visiting that screen
  after `staleTime` refetches. Neither is reachable by a user sitting on the
  dashboard, so the alternative is still correctly rejected — as *unreliable*
  rather than impossible. Soften the sentence rather than drop the paragraph; the
  structural-sharing half of the argument is airtight on its own.
- The spec says the retry fires "60 seconds after the first failure", which is the
  right anchor (a mount-anchored timer could fire only seconds after a slow
  failure, inside the limiter's window, and would not heal the 429 the section is
  about). ER8 cannot discriminate the two, because the case fires the error
  immediately after mount. No criterion is available for it in jsdom; leaving it
  as a stated implementation rule is correct, and worth knowing it is unasserted.
- The mock's no-logo card and broken card both call `fallbackMark(true)` and so
  render identically, for opposite reasons under the three-way `md:hidden` rule.
  The notes explain it, but the subtlest decision in the spec is the one the mock
  cannot draw. A pair of narrow strips at a simulated desktop width, or a single
  line of caption reading "same picture, different rule", would close it. Not
  needed for the operator's two questions.
- ER18 says the broken card shows "the latch and its 60 s retry", while the mock
  deliberately uses a 3 s stand-in and labels it. The spec's header line says this
  correctly; ER18 does not. Add "on a 3 s stand-in for the app's 60 s, labelled as
  such" so the criterion matches the artefact.
- §Accessible name offers `Navbar.test.tsx`'s existing `APRAS` assertion as a
  reason for keeping `common.appName` in the latched state. That case renders the
  no-logo fixture, so it would not have broken either way. The real argument — one
  visually identical element, one accessible name, regardless of why it shows — is
  sufficient and does not need the weaker one beside it.

## [APRAS-98] Give the slug-change dialog Escape and a focus trap — 2026-10-05 (code review, approved)

- Rebase onto current `master` before landing and re-run the frontend suite: the
  branch base is `25e9dc6`, three commits behind, and two of those commits
  (APRAS-91, APRAS-97) touched frontend tests.
- `useDialogFocus.ts` exports both a named and a default binding, and it is the
  only file in `src/hooks/` with a default export. Pick one — the named export,
  to match the eleven siblings — and update the two call sites.
- *carries every exception with a reason and a task* iterates an empty array and
  therefore asserts nothing in the shipped tree. The loop does work (I reddened
  it with a blank-`reason` entry), but consider validating a synthetic entry in a
  table-driven case so the validator is exercised by the committed test rather
  than only by a reviewer's decoy.
- Add the unmount-restore case back in the shape that can prove it: an opener
  created outside the rendered container, focused, then the dialog unmounted,
  asserting `document.activeElement` is that opener by identity. I verified it
  passes against the current hook. That closes escalation 2's gap honestly.
- The guard's header says `M2` "has never fired against a real file in this
  repository". It has now, against a decoy file in a review run. Consider
  rewording to "never fires against the shipped tree, by design", which is the
  durable claim, and recording that the regex was exercised.
- Guard assertion 3 pins the consumers by the import string only, so it survives
  a change that keeps the import but drops the `cycleTabWithin` call (verified —
  it stayed green through that mutation). The hook and page tests do catch it, so
  this is only about not over-reading assertion 3; a sentence in the "does not
  detect" list would cover it.
- `src/features/user-administration/components/TenantBrandColors.tsx:384` also
  registers a document-level `keydown`. The spec's "two document-level Escape
  effects exist after this task" is therefore an undercount of document keydown
  listeners overall (three). Worth naming in whatever task eventually unifies
  `AlertModal`'s trap.

VERDICT: APPROVED

Blocking findings: None

## [APRAS-98] — 2026-10-05 (QA, approved; shipped at 2124432)
- The absolute eslint figure disagrees across measurements this session: 377 errors/2 warnings/66 files (code review, base 25e9dc6), 372 problems (QA, base e1d19f2), 370 problems/368 errors/64 files (APRAS-110 reviewer). Each verified "no worse than its own base", which is the criterion, but no single absolute number is portable. Stop quoting a remembered figure in specs; make every lint criterion relative to a baseline the implementer measures on the branch base, and say so.

## [APRAS-123] Guard the hex and ratio comments against the clip method — 2026-10-05 (code review, approved)

1. **Name the provenance document as a third sentinel.** The claim floor is
   `≥ 17` and the measurement is 20, with the provenance document contributing
   exactly 3. All three of its connector-form hexes could be de-connectored or
   deleted and the aggregate floor would still pass, quietly removing the only
   mechanical check that the authoritative page's three published hexes are
   written in guarded form. One line in
   `it("finds the named sentinels…")` —
   `expect(inFile("docs/frontend/contrast-provenance.md")).toBeGreaterThanOrEqual(3)` —
   closes it by exact analogy with the two existing named sentinels, at no
   fragility cost. (The figures themselves are still protected by the inventory
   set equality, which is why this is a suggestion and not a finding.)
2. **`it("scans no document that an exclusion rule names")` is a tautology
   today.** `SCANNED_DIRECTORIES` is an allowlist of `docs/tasks` and
   `docs/frontend`, and none of the five `EXCLUDED_PATHS` lives under either, so
   the assertion cannot fail as currently configured. It is not pointless — it
   is a tripwire that becomes meaningful the moment someone broadens the scanned
   set to `docs/` — but after APRAS-111's audit of tests that prove nothing, the
   comment above it should say that explicitly, so the next reader does not
   mistake it for live protection of the review-document exclusion. The
   exclusion of `docs/reviews/**` is in fact achieved structurally by the
   allowlist.
3. **`flatten` strips `_` and `*` and collapses `<…>` spans, which can only hide
   a claim, never invent one.** Worth one sentence in the `flatten` doc comment:
   a prose `<` … `>` pair (an inequality, a placeholder) swallows the text
   between them, so a legitimate claim written inside such a span would go
   unguarded. False-negative direction only, so it is a documentation gap rather
   than a defect.
4. **`AGENTS.md` slightly over-claims scope.** It says the provenance page is
   the only permitted source "for a hex or a contrast ratio quoted anywhere in
   this repository", while the guard reaches only `docs/tasks/` and
   `docs/frontend/`, and the page itself names `themeContrast.test.ts` as a
   standing exception and `backend/tests/test_branding.py` holds figures of its
   own. The sentence would be truer as "anywhere in this repository's
   documentation", leaving the mechanical reach to the sentence that follows it.

---

VERDICT: APPROVED

Blocking findings: None.

## [APRAS-123] — 2026-10-05 (QA, approved; shipped at ab54bf8)
- QA ran 12 mutation probes, not the 3 the criterion required, and each failed by its named mechanism. The pattern worth keeping: a guard is only as good as the failures someone has actually witnessed.
- Lint discrepancy closed: 370 errors / 2 warnings / 66 files is the figure in a worktree via `npx eslint . -f json`; the earlier 377 is most likely cwd plus untracked lintable files in the main checkout, not a real difference in the tree.

## [APRAS-102] Show the balance cylinder and planned-vs-actual bar — 2026-10-05 (code review, approved)

1. **Derive the file census instead of hand-bumping it**
   (`frontend/src/__tests__/themeTokenMigration.test.ts:1648-1653`). A count
   that must be edited by hand every time a directory gains a file costs a
   round of review attention each time (this is its third bump: APRAS-92,
   APRAS-118, now APRAS-102) while catching nothing a human bump would not
   simply absorb. Its real job is non-degeneracy — proving the two directories
   are actually being scanned, so a broken glob cannot make the whole suite
   vacuously green. That job is served better by a lower bound plus an identity
   check: `expect(projectsFiles.length).toBeGreaterThanOrEqual(10)` together
   with an assertion that a few known-pinned filenames
   (`ConstructionTrackerPage.tsx`, `BudgetVsActualProgressBar.tsx`,
   `AssetsInventoryPage.tsx`) are present. A broken glob still fails loudly; a
   new component does not. Same shape for the `FINANCE`/`PURCHASES` and
   `DOCUMENTS`/`OCCURRENCES` censuses in the same file, which carry the
   identical maintenance cost.
2. **`formatPercent(-0, d)` returns `"0"` where Python's `format(-0.0, '.0f')`
   is `"-0"`** (`lib/budgetFigures.ts:84`, `negative = value < 0` is `false`
   for `-0`). This is the only divergence my 19,206-case differential against
   CPython found, and it is unreachable through `budgetFigures` (`100 -
   executedPct` is never `-0`). Since the module's docstring claims to mirror
   `format` “across its whole domain”, either use `Object.is(value, -0)` in the
   sign test or add a sentence excluding signed zero from the claim.
3. **`plannedProgress` is stricter than `planned_to_date` on `pct: NaN`**
   (`lib/plannedProgress.ts:59` refuses it; the backend's
   `isinstance(pct, (int, float))` accepts it and would render `nan%`).
   Unreachable through a JSON column in practice, and the frontend's behaviour
   is the better one, but a module documented as a strict mirror should say
   where it deliberately differs. One line in the docstring.
4. **`decimals` is documented as `0..2` but not enforced**
   (`lib/budgetFigures.ts:69`). A negative or large `decimals` would walk the
   index arithmetic off the expansion. Both call sites pass `0` or `1`, so this
   is only a guard against a future caller: either narrow the parameter type to
   `0 | 1 | 2` or add a one-line clamp.
5. **The em dash for “no curve” as a literal constant** (`NO_CURVE_LABEL` in
   `PhysicalProgressPlannedVsActualBar.tsx:40`) is, in my view, right as it
   stands — it is a typographic placeholder, not prose, and it reads identically
   in both locales — so the developer's open question 5 can be closed as “leave
   it”. Raising it here only so the decision is recorded rather than re-asked.
6. **Record the one unreproduced flake.** One `npm run test:coverage` run
   reported `1 failed | 2561 passed`; it did not recur in five further full runs
   or in eight runs of this task's 13 files. Not attributable to this diff and
   not a finding against it, but if QA or CI sees a lone failure in a coverage
   run, this is a prior sighting and not a new regression.

### Lint baseline: discrepancy closed
The 377 vs 370 figure was a DIFFERENT BASE COMMIT, not a different invocation. eslint error counts are per-file, no changed path in APRAS-102 or APRAS-98 carries an error, so the count is invariant across those diffs. `npx eslint . -f json` from `frontend/` is identical to `npm run lint` (script is `eslint .`). Current figure on ab54bf8: 370 errors / 2 warnings / 66 files. Earlier note in this log guessing at cwd and untracked files was wrong.

## [APRAS-102] — 2026-10-05 (QA, approved; shipped at 6be21c8)
- The lone unreproduced coverage failure did not recur in three further full runs (197 files / 2576 tests). Treat it as noise unless it returns.

## [APRAS-119] Find why the backend test job hangs — 2026-10-05 (code review, approved)

1. **Fix the one wrong gap figure.** `docs/tasks/APRAS-119-findings.md` §8's
   timestamp table gives the `15 602 → 15 603` gap as **68.81 min**; the log's own
   timestamps (`06:28:58.295Z → 07:37:44.167Z`) give **68.76 min**. The stated
   range "68.77–68.81 minutes" should be "**68.76–68.80 minutes**". The same wrong
   range is replicated in two committed comments — `.github/workflows/ci.yml`
   (backend pytest step, "five consecutive gaps of 68.77-68.81 min") and
   `backend/tests/test_project_report_branding.py`'s `ids=` comment. The
   conclusion is unaffected and in fact strengthened: all five gaps fall within
   2.0 s of each other. Worth correcting because APRAS-123 just set the precedent
   in this repo that published figures must be re-derivable.

2. **Note that the before/after collection byte figures are from different tree
   snapshots.** §8's table pairs `2 524 431 B` (before) with `427 396 B` (after).
   I reproduce `427 396` exactly but get `2 524 767` for the reverted tree — a
   336-byte difference, which is the two *net new* hygiene test node ids (three
   added, one removed) that did not exist when the pre-fix reading was taken: the
   document's own `4195 tests collected` against today's `4197`. Not a defect —
   the load-bearing figure (2 097 259 characters) is exact — but a one-line note
   that the pre-fix byte count predates the new hygiene tests would stop the next
   reader from thinking they had failed to reproduce it.

3. **Correct `AGENTS.md:247–265` in this task rather than tracking it
   separately.** Three claims there are now stale, two of them disproved by this
   very change: (a) line 250–252's "cancelled at 55m0s **twice in a row** on a
   commit whose backend tree was **byte-identical**" — the census found 15
   occurrences on 8 refs and the spec withdrew that framing; (b) line 248–250's
   absolute "GitHub publishes **no logs for a cancelled job**" — 4 of the 15
   publish logs, including the 8 MB one this root cause rests on; (c) guard 1's
   unconditional "It fails a **step**, and a failed step keeps its log", which is
   the exact sentence R17 required be corrected in `ci.yml` and which is left
   standing in the file agents actually read. `AGENTS.md`'s "three guards" list
   should also become four, naming the `faulthandler` shutdown watchdog, and
   could reference the node-id guard. Left as a suggestion only because it is
   documentation outside the spec's "Files touched" — but it should be fixed
   before this lands, not after, since an agent reading it post-merge is told the
   hang is an unsolved runner mystery.

4. **Rebase onto `ab54bf8` and re-run the full suite before landing.** The
   worktree is 5 commits behind. No commit touches any of the five staged paths,
   so a clean rebase is expected, but `test_no_collected_node_id_can_carry_a_payload`
   collects the whole tree and three of the five commits add tests — re-run the
   module (not just the full suite) after rebasing to confirm the collection
   count stays above `MIN_COLLECTED = 4000`. It sees 4197 today.

5. **Track the watchdog's capture-teardown gap as a low-priority follow-up.** A
   dump firing in the *early* armed window — the `coverage.xml` write or the
   warnings summary, which is where the root cause actually lived — lands in the
   fd-level capture buffer and is lost, so the stack is only guaranteed for the
   interpreter-shutdown shape. `exit=True` means the *backstop* still works in
   both cases (bounded failing step with a readable log), so this is a
   degradation of the secondary benefit only. The engineered fix is
   `capman.suspend_global_capture()` + `os.dup(2)`, which is not worth inlining
   here.

6. **For QA:** one expected result cannot be satisfied by this change — "the
   first CI run after the watchdog lands: its run id, its `Backend Tests` job
   conclusion, and whether the 90% coverage gate passed". The document records it
   as explicitly **pending** because the task deliberately triggers no CI run.
   That is the correct handling, but it means the 150 s grace period has never
   been exercised on a loaded ubuntu runner. Projected CI armed-window latency is
   ~26 s (2× the measured 12.95 s), giving 5.8× headroom, so the risk is low —
   but the findings document should be updated with that run's id once it exists,
   and a spurious `exit=1` on a green suite is the failure mode to watch for.

---

VERDICT: APPROVED

Blocking findings: None.

## [APRAS-119] — 2026-10-05 (QA, approved; shipped at a33f26a)
- QA re-derived the census from scratch and proved both detector choices differentially (filter=all, non-null step test), rather than taking the document's word. Six mutations, including three the criterion did not ask for (exit=True, return result, trylast=True).
- PENDING, and deliberately so: R14's last clause -- the first CI run after the watchdog lands. The 150 s grace period has never run on a loaded ubuntu runner. Projected CI armed-window latency ~26 s, so ~5.8x headroom, but the failure mode to watch is a spurious exit 1 on a green suite. Update docs/tasks/APRAS-119-findings.md with that run id once it exists.

## [APRAS-122] Pin uv in CI — 2026-10-05 (code review, approved)

1. `docs/tasks/APRAS-122-action-audit.md` — the third `setup-uv` step's line
   number is stale in two places: §6's table row reads `ci.yml` ×3 (55, 160,
   **225**) and §5.2's pasted pytest output reads `'ci.yml:225': '"0.12.19"'`.
   The committed tree puts that step's `uses:` line at **221** (225 is its
   `version:` line); reproducing mutation 2 against the committed tree yields
   `{'ci.yml:55', 'ci.yml:160', 'ci.yml:221', 'migrate.yml:17'}`. The capture
   predates the trimming of the second step's comment block by exactly 4 lines.
   Fix both occurrences to `221` — or re-run the four mutations and re-paste — in
   a docs-only amendment to `c597527`. This touches **only** the document, never
   `40d40a2`, so the gate sha is unaffected. Worth doing before QA, which will
   otherwise re-derive 221 and see a document that disagrees with the tree.
2. `docs/tasks/APRAS-122-action-audit.md` §3 — the table row labelled "The sha
   `master` lands" reads as a claim about the tip, which is `c597527`. The
   paragraph below the table explains the two-commit shape correctly; relabel the
   row to match it, e.g. "The pin sha `master` lands (parent of the docs-only
   tip; `git diff 40d40a2 HEAD --stat` is one file under `docs/`)". Pure wording,
   same docs-only commit as suggestion 1.
3. `AGENTS.md` — the UV_PIN sentence points at
   `backend/scripts/export_requirements.sh`, which does not exist yet
   (APRAS-121 has not landed; `grep -rn UV_PIN backend/` finds only this task's
   own test module). The claim string is mandated verbatim by ER-12, so this is
   correct as written, but it is a forward reference that will read as a broken
   one until APRAS-121 lands. Either leave it and let APRAS-121 resolve it, or
   add four words marking it as APRAS-121's. No action required.
4. `backend/tests/test_workflow_actions.py:205` — `_parse_with_block` matches any
   `key: value` line below `with:` at any depth, so a nested or block-scalar
   input value (`cache-dependency-glob: |` with `key: value`-shaped content
   under it) could contribute a spurious key to `inputs` and trip the
   undeclared-input guard. No step in this repository has such a value and the
   failure direction is conservative (loud false positive, never a silent pass),
   so this is a note for whoever adds the first multi-line input, not a defect.
5. `backend/tests/test_workflow_actions.py` — `discovered_steps()` re-reads and
   re-parses every workflow file in each of the seven tests that call it. Four
   small files, immeasurable cost; a module-scoped fixture or `functools.cache`
   would be tidier if the module grows.
6. For the orchestrator, not the developer: ER-5 is an open item by construction.
   After the push to `master`, fill in §4's `migrate.yml` subsection with the run
   id, the `Run DB Migrations` job id, `conclusion: success`, the `0.12.19` line,
   zero `Falling back to latest` and `grep -c 'Unexpected input'` at 0, in a
   docs-only follow-up commit, before the task reaches `done`. And §7's
   sha-pinning / dependabot-ecosystem follow-up needs to reach the task report
   and the operator, per ER-11.

---

VERDICT: APPROVED

Blocking findings: None

## [APRAS-122] — 2026-10-05 (QA, approved; landed at 40d40a2 + ea37e9a, R5 PENDING)
- R5 cannot be met before the operator pushes: the migrate.yml run is fired BY the push to master. docs/tasks/APRAS-122-action-audit.md section 4 carries the subsection, the commands and the four values to fill in, marked outstanding. Fill them after pushing.
- R4 has two readings. QA applied the substantive one (the gate ran on the exact object carrying the change CI can see, with no amendment between observation and landing) and verified ea37e9a is CI-inert: a 1-file docs/tasks addition, nothing under backend reads docs/, and sonar.sources is backend/app,frontend/src. Under a strict tip-to-tip reading the shas differ -- that reading makes R4 unsatisfiable for any task whose evidence document is committed. Worth rewording the criterion if this shape recurs.

## [APRAS-93] Make the public obras report cheap to serve — 2026-10-05 (code review round 1, rejected)

- **Pin the fixture's text lengths, not just its row counts.** The "Measurement
  environment" paragraph fixes projects / milestones / bulletins / photos, but every
  absolute byte figure also scales with title, description and bulletin-body length. My
  independent fixture reproduced every *slope* exactly (115→119 B/front against the
  document's 115→119; 13,039 B shell against 13,062 B) while landing 5-10% low on
  absolute response sizes. Recording the generator's string lengths — or the one-line
  fixture recipe — would make the absolute figures reproducible rather than merely
  directionally reproducible.
- **The 109 B / 0.55% logo figure depends on an unstated base URL.** I measured
  `_logo_html` at **86 B** and 0.46%, because the emitted
  `<img src="http://localhost:8000/api/v1/public/tenants/sintetico/logo" alt="Sintetico">`
  varies with the configured public base URL and the tenant name, neither of which the
  environment paragraph pins. The claim that matters — well under 1% of the response —
  is robust either way; consider stating it as "~100 bytes, under 1%" with the URL
  dependency noted.
- **`_logo_html`'s docstring says 89%, this document now says 88%.** I measured **88.5%**.
  The docstring (`project_report_service.py:1321`) cites this document as its source, so
  the two should not disagree. Since ER13 forbids touching the service file here, the
  cleanest fix is a note in §1.6 that the production docstring carries the earlier
  rounding, and a line in Task A or a follow-up to reconcile it.
- **Attribute the "twelve cover requests" figure.** §3.1 says "One report view costs one
  report request and up to twelve cover requests" as though it were a property of the
  system. It is APRAS-104's *planning* figure ("the largest report to plan for carries
  12 obras", `public_projects.py:60`); in code `_project_hero` emits one cover per
  project, uncapped, so a 20-project report triggers twenty. The real fan-out is `N`.
  This understates rather than overstates, so it carries no decision risk — but a
  measurement document should not let an inherited assumption read as a measured bound.
  Suggest: "one per project — twelve on the report APRAS-104 sized its limiter for, and
  uncapped in general".
- **The upload inventory count does not reproduce.** §1.6 reports "Embeddable uploads
  inspected under `backend/static/uploads/`: **8,090**"; I count **9,859** files there
  now. The load-bearing figures match exactly (largest 108,018 B; zero over 512 KiB), and
  the gap is probably either the "embeddable" filter (mine was unfiltered) or growth in a
  gitignored, operator-managed directory. Stating the filter would settle it.
- **§5's "~5.5 MiB/s" is 5.5 MB/s.** 661,750 B / 0.1195 s = 5.54 **MB**/s = 5.28 MiB/s.
  Trivial unit slip in an otherwise scrupulous document.
- **The H1 and the board title disagree.** The document's heading ends "without going
  **private**"; the Meridian card reads "without going **stale**". Both themes are
  covered (§5 for exposure, the binding constraint for staleness), but the titles should
  match whichever the operator considers canonical.
- **Add one sentence so §3.2 is not mis-cited against APRAS-124.** The
  `(logo_url, ETag)` bullet rejects an `ETag` over the *report* response, not caching of
  the public logo *route*. A clause noting that the logo route's own caching is out of
  scope here and now owned by APRAS-124 would prevent a future reader citing this
  document as having declined it.
- **The cover route's `Cache-Control` question is about to be unowned.**
  `public_projects.py:77-79` assigns it to APRAS-93; this document does not address it.
  Worth explicitly reassigning in §6.2's "not in either task" list, so it does not fall
  through when APRAS-93 closes.
- **Consider promoting the `_stage_detail_html` dimension to a backlog task**, per §6 —
  a reopening condition with no detector and a one-command path out of dormancy.
- **Use paired/interleaved timing for any future A-vs-B figure in this document.** The
  blocked design (all A reps, then all B reps) is what produced the reversed
  `selectinload` sign; it cannot resolve differences under ~20% on this machine. The
  single-state figures (§1.1, §1.5, the sweep) are unaffected and reproduced well.

---

VERDICT: REJECTED

1. `docs/tasks/APRAS-93-spec.md:141-146` (and `:28-29`, `:537-543`) — the claim that
   `selectinload` is *not* faster at 200 projects does not reproduce and its sign is
   reversed. Under a paired interleaved design (12 counted paired reps, two independent
   runs) eager measured **350 ms against cold 406 ms, winning 12/12 paired reps in both
   runs** — a 14% CPU improvement — with my cold figure matching the document's 402.9 ms
   to within 1% and my 20-project control matching its 23.1/14.1 ms closely. The document
   publishes this as a *correction* of a previous draft, so a correct earlier figure has
   been replaced with an incorrect one, in the section that opens by invoking APRAS-111's
   audit as being "about exactly this failure mode". The supporting causal claim at
   `:143-146` ("two `IN (…)` queries … cost at least as much as 400 small ones") is also
   wrong, since avoided per-statement overhead is what makes eager win at both sizes.
   Fix three sites: §1.3's "Note the sign" paragraph and its figures, the intro's
   correction bullet 3 (which retracts a correct claim), and §6.2 Task B's "not a CPU win
   at 200 projects" sentence. §6.2's narrowed headline ("constant statement count") and
   the §3 decision are unaffected — correcting this strengthens the document's case.

### Lesson: a blocked design cannot resolve a 10% difference
APRAS-93 published a CORRECTION that was sign-reversed: eager vs cold selectinload at 200 projects, measured as all-cold-reps-then-all-eager-reps (two overlapping ranges). A paired interleaved design gave the opposite sign, 12/12 paired wins, twice. Whenever a figure decides a claim about which of two things is faster, interleave and pair; report paired differences and win counts, never two ranges.
### Resolved: specs DO belong in the repository
docs/tasks/ is not gitignored and carries 124 tracked files against 19 untracked, all recent. The untracked specs are commit lag, not an unsettled policy. Stop flagging this as an open question; commit them.

## APRAS-110 — code review round 1 (APPROVED)

### Suggestions (non-blocking, from `docs/reviews/APRAS-110-code-review.md`)
1. **Close the dynamic-token hole with a compile-based check, as its own task.** The reviewer confirmed `` `dark:bg-${"foreground"}` `` passes all 18 cases and all three theme guards while generating no CSS. The fix is not a lint rule but a CSS-output assertion: Tailwind's `compile()` is already a dependency and already used by `frontend/src/__tests__/themeTokenCompile.test.ts`. A case that compiles `src/index.css` over a fixture carrying the plate's literal class list and asserts the emitted sheet contains `.dark\:bg-foreground:is(.dark *)` with a non-empty `background-color` fails for any assembled token, because an assembled token never reaches Tailwind's scanner. The real build does emit that rule (pulled from `dist/assets/*.css`). This protects every `dark:`-gated paint token in the tree, not just this one.
2. **`frontend/.vitest/` belongs in `frontend/.gitignore`**, beside `dist` and `coverage`. Standalone chore, not this commit.
3. **The lint baseline is `372 problems (370 errors, 2 warnings)` across 79 files**, and it requires a `node_modules` matching `package-lock.json` (eslint `10.11.0`). The older 370/368 figure is what a stale eslint `9.39.4` install produces, and it reads as "this change added two errors" to whoever measures next. *(Applied to the spec and to the board's expected results.)*
4. **The `logo_url: null` criterion must be banner-scoped**: `within(screen.getByRole("banner")).getByRole("link", { name: "APRAS" })`. The unscoped form is unsatisfiable by any implementation — `Sidebar` renders a sibling appName link — and it contradicted the sentence it sat in. *(Applied to the spec and to the board.)*
5. **Three card-absence cases would each be one line stronger** with `expect(screen.getByTestId("tenant-header-fallback")).toBeInTheDocument();` added, so each asserts its subject rendered at all. They already kill the realistic mutant and seven siblings kill the render-nothing mutant, so this is tidiness over coverage — but given `e1d19f2`, three self-identified vacuous cases are worth one line each.
6. **The latch's unmount `clearTimeout` is the one branch no case exercises.** Correct by construction; a stray timer would surface as a React warning, not a failure. Worth pinning only if a future task touches that effect.
7. **Orchestrator-side drift, now fixed.** The board carried 18 `expected_results` and none was the card criterion, while the spec specified the plate in full with two dedicated results — QA receives only `expected_results`, so both card criteria would have gone unchecked. Synced to 20 results before QA was dispatched.

### Lesson: the toolchain version is part of a baseline figure
APRAS-110's lint baseline was quoted inconsistently all week — 370/368 in one place, 372/370 in another — and the cause was neither cwd nor untracked files (my own earlier guess, wrong, corrected in this log). The worktrees install eslint `10.11.0`, which `package-lock.json` pins; the main checkout had a stale `9.39.4`. Same tree, same lockfile, two different totals. A baseline figure that does not name the tool version that produced it is not a baseline; it is a number that will read as a regression to the next measurer.

### Lesson: a class-list equality is not a CSS assertion
The plate's five-token equality is the strongest assertion available in jsdom and it still cannot tell a literal `dark:bg-foreground` from an assembled one, because nothing in the suite reads a computed background and Tailwind never runs. The discipline ("one literal string, never assembled") is observed by the implementation and enforced by nothing. Where a token's value depends on a build-time scanner, only a build-time assertion closes it.

### Correction: a compiled-CSS guard does not close the dynamic-token hole on its own
The APRAS-110 code review proposed a Tailwind `compile()` check as the cheap fix for the assembled-token hole. QA, executing it, found the proposal defeats itself: the *test file's own literal* `dark:bg-foreground` is in Tailwind's scanned set, so the rule stays alive in the emitted sheet even when the component assembles its token. The guard would pass on exactly the mutant it exists to kill. A compile-based guard has to scan non-test sources only, and must assert that the scanned set excludes the tests — otherwise the fixture is the thing keeping the assertion green. Recorded in APRAS-125's expected results as a named criterion rather than left as an implementation detail, because the vacuous form here is the one that looks correct.

## APRAS-93 — code review round 2 (REJECTED)

### Suggestions
- `t_states.py` **prints** its byte check where `dh.paired` **asserts** it. The reviewer proved `dh.paired`'s assertion is real by mutating the eager arm to drop one project — it died on the first pair with `AssertionError: (171507, 163584)`. A printed check in the same harness, next to an asserting one, is the shape that gets read as verified. Converted to an assertion in round 3.

### Lesson: two rejections on reproducibility is a process signal, not two incidents
APRAS-93 has now been rejected twice for figures that do not reproduce: round 1 a **sign reversal**, round 2 a magnitude **50% off** (warm at 200 projects published as 63.51 ms against 41.4–42.4 ms measured five times) plus a **causal artefact that does not exist** (eager at 779.5 ms in a combined process, "which is why" the states are measured one process each — three runs gave 395.37 / 394.37 / 396.12 ms against 395.34 ms own-process, agreement to 0.5%). Both rounds, the retracted figure was nearer reproducible than its replacement.

The pattern is specific and worth naming: this document's subject is *figures published as corrections that were wrong*, and it keeps producing them. A correction is not a safer claim than the thing it corrects — it is a claim with the same burden and less scrutiny, because the act of correcting reads as diligence. Every figure in a document like this needs re-derivation from the harness each round, with the report stating which were re-measured and which were carried forward. A conclusion whose stated premise has just been withdrawn must go with it; softening the wording keeps the error and hides it.

### Lesson: the fan-out poisons its own timing measurements
APRAS-93 round 3 disclosed a load average of **21.86** on this machine, with `t_sizes` at N=200 giving 438.80 / 1258.18 / 1990.87 ms — a **4.5× spread** on identical code — and `t_sweep` running 6–7× high. That load is us: this pipeline runs several agents concurrently by design, and the user's standing instruction is to parallelize freely. The orchestration choice that makes the pipeline fast makes every wall-clock figure any agent takes **unusable as an absolute**.

Consequences to apply, not just note:
- A task whose deliverable includes absolute timing figures should not be measured while the fan-out is running. Either serialize it, or measure only what survives contention.
- What survives: byte counts, statement counts, within-process ratios, and paired interleaved differences. What does not: throughput (`reports/s`, `renders/s`), single-arm latencies, and any self-declared drift band — APRAS-93's own ±15% band was unsupportable by a factor of 30.
- A dispatch prompt that asks for timing evidence must say which of the two kinds it wants. Round 1's sign reversal, round 2's 50%-off magnitude and round 3's withdrawn drift band are all the same error arriving three times: an absolute figure taken on a contended machine and published as a property of the code.

## APRAS-93 — code review round 3 (REJECTED)

### Lesson: an explanation that excludes its own subject
The strongest finding of three rounds is the cheapest to check and nobody checked it. §1.3.2 published the warm arm as bimodal — 41.0–44.9 ms or 72.2–128.2 ms, "with nothing in between" — and invoked that bimodality to explain **63.51 ms**, the very figure round 2 rejected. 63.51 falls in neither mode. The explanation excludes the thing it exists to explain, and the gap it declares empty is where its own subject lives. Before accepting any mechanism claim, substitute the number it was written to account for and check that the mechanism actually accounts for it.

Two corroborating defects in the same section, both arithmetic: the document says fourteen measurements (nine fast, five slow) where the report tabulates eighteen (thirteen fast, five slow), and §1.3 says "seven trials" where §1.3.2 says nine. A claim whose own sample count moves between paragraphs has not been re-derived.

### Lesson: "ruled out" needs a design that could have implicated
`t_warmdist.py` runs both `gc` regimes **inside one process** on a graph built once — so under the document's own premise that the mode is fixed per process, both regimes inherit it by construction and the result is predetermined. It also differs in more than one variable (`gc.disable()` suppresses only cyclic collection, and the gc-off arm runs after a `gc.collect()`), and the slow mode was observed **once**; the reviewer never reached it in six runs. That design cannot implicate the garbage collector, so its silence is not evidence. **"Failed to implicate" is true and publishable; "ruled out" is not** — and the weaker sentence costs nothing, which is what makes reaching for the stronger one gratuitous.

The same section's "not machine load alone" fails on the reviewer's own data in the opposite direction: all 18 warm-only and all 8 quiet combined runs were fast, while both non-fast warm medians came from the two busiest runs (load 16.90, 14.18). Load is the live hypothesis, not the excluded one — see the fan-out lesson above.

### Note: the reviewer flagged its own earlier reasoning
Round 2's inference "cold and eager reproduced, therefore drift is excluded" was itself a single quiet session's observation — the same pattern it was rejecting. The round-2 *conclusions* stand (26 further runs), but that drift argument should not be leaned on. Worth recording because a reviewer auditing its own prior rounds is what kept this from becoming a fourth incident instead of a caveat.

## APRAS-93 — round 4: the withdrawal that explained the figure

Round 4 answered both round-3 findings **by retracting** them, and in doing so produced the thing three rounds of defending could not: an account of 63.51 ms that holds up.

The retracted bimodality was replaced by the pooled distribution of 139 warm medians across three sessions — 104 at 37.7–44.9 ms, 35 above, **no gap exceeding 10 ms**. That is a tail, not a second mode, and once it is described as a tail, 63.51 ms stops needing a special explanation: it is an ordinary draw. A new paired interleaved experiment then made it *predictable* — 18/18 pairs slower under contention at ≥6 competitors, 0/6 below, eight-competitor median **63.11 ms** against the 63.51 that round 2 rejected as unreproducible.

### Lesson: withdrawing a claim can be what explains the data
The figure that survived two rejections became reproducible the moment the mechanism invented to explain it was dropped. The bimodality was not merely unsupported — it was *in the way*. Declaring a gap empty made the document's own subject anomalous, and so long as 63.51 had to be an anomaly, nobody looked for the ordinary condition that produces it. The weaker description (a tail, cause not isolated) had more predictive power than the stronger one (two fixed modes, collector excluded).

Operationally: when a figure resists explanation across rounds, suspect the explanatory frame before suspecting the measurement. And the corollary for review prompts — telling an agent that withdrawal is a legitimate and probably correct answer, and explicitly forbidding the weaker-but-still-unsupported middle road, is what got a clean retraction instead of a fourth softening.

## APRAS-93 — code review round 4 (REJECTED, six findings)

### Lesson: correction 7's error, committed again by the document that records it
Finding 3 is the one worth remembering. `loadpair.sh:14` invokes `t_states.py` with a **single state**, which makes `assert len(b) == 1` a **tautology over a one-element set** — and the document published "the byte count was 1,738,448 B in every one of these runs, **asserted**" on the strength of it. The reviewer mutation-proved the vacuity: every render 11 bytes short still printed `bytes 171496` and exited **0**. The script also discards the byte column (`$3` only), so nothing downstream could have caught it either.

This is correction 7's own error, in the document that records correction 7. An assertion-shaped line that cannot fail reads exactly like one that can, and reusing an asserting harness in a new invocation **changes whether its assertions assert**. A check is vacuous or not as a property of the *call*, not of the script: `assert len(set) == 1` over one element, a `grep -c` on text that moved, a class-list equality with no CSS — this project now has four instances of the same shape. The rule that follows: whenever an existing harness is invoked in a new configuration, re-run the mutation that proved its assertion, in **that** configuration.

### The other five, all one kind
- `:552-556` "no gap exceeds 10 ms" — **false on the document's own 35 published values**: four gaps exceed it, one at 28.7 ms, 2.9× the bound. And it is the sole justification for "a tail and not a second mode", the claim that replaced the retracted bimodality. A replacement claim inherits the burden of the claim it replaces; it does not inherit its predecessor's scrutiny.
- `:606-607` — the probe is described as applying the regime "before the object graph is built"; the graph is pinned at `t_warmdist.py:48-51` and `gc.disable()` runs at `:56-57`, after. The code answers round 3 correctly; only the sentence is wrong.
- `:286-291` — mutation counts attributed to the wrong fixture (20/40/60/8's figures presented as 20/20/20/6's). The assertion is genuinely proven at both; only the attribution is wrong. **The reviewer carried this error forward from its own round-3 review** — a figure that passes a review is not thereby verified.
- `:578-580` — "monotone in the number of competitors", contradicted by the sequence printed **in the same sentence** (38.7 → 38.4 → 38.9).
- `:582` — "within half a millisecond", a one-session artefact; two runs at the same competitor count gave 53.73 and 60.78 ms, pooling to 58.22 over 12 pairs. Direction and band reproduce; the precision does not.

### Lesson: four rounds of one defect is a property of the writing, not of six lines
Rounds 1–4 rejected a sign, a magnitude, two mechanisms and now six sentences — every one a claim stated **one notch stronger than its evidence**. At that point the fix is not another round of corrections but a sweep over every absolute word in the document (`asserted`, `every`, `never`, `always`, `no`, `monotone`, `within X of`, `rules out`), tightening each to what its evidence supports. Round 5's dispatch asks for the count of such sentences checked and changed, because that number — not the six fixes — is what tells whether the defect was addressed.

## APRAS-93 — round 5: the sweep

Round 5 answered the six findings 3 by deleting a claim, 2 by correcting a fact, 1 by fixing the harness and deleting the word — then did the thing the round was actually for: **~60 distinct claims judged, 33 passages changed (27 beyond the six findings), 7 claims deleted outright and named in the document.**

Four claims it found false on its own, none of which any of four review rounds had flagged:
- §1.1's "4–5% larger" — actually 2.3–5.5%.
- §1.4's "every render regardless of identity-map state" — contradicted by its own warm arm.
- §3.1's "every cache degrades the other way" — contradicted by §3.2, in the same document.
- §1.5's "`detail_json` is NULL on every production row" — unmeasurable from here at all.

Plus four stale internal counts. And the gap bound's deletion took the "tail not a second mode" conclusion with it, replaced by the true bounds and an explicit **"the shape above 97.7 ms is not established"** — with the honest footnote that only 7 of the 8 upper values reproduced and **128.2 ms never did**.

### Lesson: a vacuity audit has to cover the harness, not just the suite
Fixing `loadpair.sh`'s tautological byte check turned up **a fifth instance of the same shape in the same harness**: `t_sweep.py` asserts only the HTTP status, while §5 leaned on it for more. Four review rounds, each executing the harness, had not found either. The scripts that *produce* evidence get far less scrutiny than the tests that *are* evidence — nobody mutation-tests their measurement tooling — and that is exactly where a vacuous check does the most damage, because every figure downstream inherits it.

### Lesson: ask for the count, not the corrections
The six findings produced six fixes. The instruction that produced the 27 *other* changes was asking for a number — how many absolute claims were checked and how many changed — rather than asking for the six lines to be fixed. A dispatch that names the defect's *shape* and demands a census gets the systematic pass; one that lists the instances gets the instances.

## APRAS-93 — code review round 5: APPROVED

Final round of the cap, no blocking findings. The verifications behind it are worth recording because they are the standard this project should keep:

- **The byte check was re-proved with a different mutant.** The reviewer did not re-run the developer's 11-byte truncation; it built its own 7-byte one — `bytes=1738441`, `BYTE MISMATCH` on every arm, exit 1, control exit 0 at 1,738,448 B. Re-running someone else's mutation proves the mutation; building your own proves the check.
- **All replacement arithmetic recomputed exactly**: the 9.4 / 5.0 ms gaps, the 27/8 split, the four gaps over 10 ms, the 78.1 ms span, eight group medians, pooled band 50.6–74.4 ms, pooled median 59.620 → 59.6 over 24 pairs, and run 1's 1.89 ms shortfall.
- **The deletions were verified as deletions.** Targeted greps for every withdrawn phrasing resolved only to the correction history or to corrected sentences; `128.2` appears nowhere load-bearing. The withdrawn mechanism now reads "**No claim is made here about what caused them**" — which is the sentence four rounds of review were trying to get written.
- **Sweep sample: 20 claims checked, 19 clean.** The single miss was an off-by-one in a citation tally.

### Lesson: the end state of an honest analysis document is a named limit
Five rounds, and what shipped is a document that says *less* than every rejected draft: the shape of the warm distribution above 97.7 ms is **not established**, the cause of the losing pairs is **not claimed**, contention is **sufficient but not exclusive**, 128.2 ms **never reproduced**, and §5's figures are **printed and observed, not asserted**. Every one of those sentences is a retreat, and together they are the first version that is correct. The reviewer's own instruction for the final round said it: do not reject a document for admitting a limit — four rounds of findings were all about claiming more than the evidence supports, and the fix for that is a document that claims less.

### Note: the miscount that produced "four read sites" had a cause worth keeping
The round-5 follow-up fixed §1.5's read-site tally, and the fix was not a digit swap. `git grep detail_json -- backend` (tests excluded) gives seven hits in `project_report_service.py`: **three code reads** (`:1006`, `:1060`, `:1248`, each `decode_stage_detail(milestone.detail_json)`) and **four prose mentions** in docstrings and comments (`:721`, `:944`, `:1219`, `:1227`). Draft 6 had counted the prose mentions as reads — a grep's hit count is not a count of call sites, and nobody had looked at which hits were which. The sentence now lists both groups with line numbers so the next reader can re-run the grep and match it line for line, which is the right shape for any claim derived from a grep: publish the hits and their classification, not the total.

## APRAS-121 — implementation

### My own error: I read a file mode as a line count
I dispatched the developer telling it the spec was "644 lines, committed on `master`". Both halves were wrong, from one misreading: `ls -la` printed `644  docs/tasks/APRAS-121-spec.md  34.6K` and I took the **permission bits** for a line count. The spec is **489 lines** and **was never committed anywhere** — `git log --all -- docs/tasks/APRAS-121-spec.md` returns nothing, and it sat untracked in the main checkout. The developer caught it, read the real file, and said so in its report.

Two things to carry: a number in `ls -la`'s first column is a mode, never a size or a count — use `wc -l`; and "committed on master" is a claim to verify with `git log --all --`, not to infer from a file existing in the working tree. Worth noting the untracked-spec pattern is now three for three in a row (APRAS-93's main-checkout copy was a stale 426-line draft, APRAS-110's was *newer* than the committed one, APRAS-121's was never committed at all) — an untracked file bearing the deliverable's name tells you nothing about which version is authoritative. I staged this one into the worktree so it ships with the implementation.

### Note: the harness branches worktrees from `origin/master`, not local `master`
APRAS-121's worktree came up at `25e9dc6` — **eleven commits behind** the local `master` the task was supposed to build on. The developer found it clean and `reset --hard 8487258`. With a long run of unpushed commits this will happen on every new worktree, so a dispatch must state the intended base sha and tell the agent to verify it rather than assume the worktree is current. Stating it is what made this one recoverable.

### Credit where it is due: the harness that reported its own accident
The developer's mutation harness aborted M3 *before* restoring the file, briefly leaving `ci.yml` with two mutated pins. It found that with `grep -c`, restored, and rewrote the effect check as a count comparison **inside** the `try`. It recorded the incident rather than quietly fixing it. That is the right shape for a mutation harness: the restore belongs in a `finally`, and an effect check that can abort before the restore is a bug in the instrument, not a detail.

## APRAS-121 — code review round 1 (REJECTED)

### Lesson: a comment in the file satisfies a substring guard
Both findings are the same defect and it is a new shape for this log. The guard tests asserted on the **raw text** of `.github/workflows/requirements-export.yml`, so `"pull_request_target"` and `"contents: write"` were satisfied by **the file's own explanatory comments** (`:22`, `:47`, `:158`) — prose written to document the security design was holding up the test that checks the security design. Mutating the trigger to `pull_request:` and the permissions to `write-all` left all 27 tests green.

The second finding is the same mechanism across five security-critical deletions, each leaving the suite green: `persist-credentials: false`, the fork gate, the `dependabot/uv/` branch gate, `ref: head.sha` swapped for `head_ref`, and the `checksum:` pin. **The fork gate is the single control keeping a fork PR out of a job that holds a `master`-capable PAT** — and the test could not notice its deletion.

The fix is structural, not a tighter regex: **parse the workflow as YAML and assert on the parsed structure.** `on`'s keys, `permissions`' scopes, the checkout step's `with`, the job-level `if`, the `ref:` expression, the `setup-uv` step's `checksum:`. A comment cannot satisfy a parsed mapping. Where text matching is unavoidable, anchor it so prose cannot satisfy it, and say in the test why the anchoring suffices.

This is instance six of the vacuity family, and the first where the *documentation of the property* was what made the test vacuous — which makes it the most insidious, because the better-commented the file, the weaker the guard. Any assertion over a file that also contains prose about the thing asserted is suspect by construction.

### The counterweight: the workflow itself reviewed clean
Worth recording separately, because the rejection could read as "the security work was bad". It was not. The reviewer found no template injection into any `run:` body, the privileged script taken from the base sha rather than the head checkout, the push refspec confined to `refs/heads/dependabot/uv/*`, and the secret present in exactly one `env:`. Both of the developer's self-flagged divergences were accepted, the cwd-guard one after the reviewer ran the script from five different working directories. The defect was entirely in the suite's ability to keep the workflow that way.

## APRAS-121 — round 2: the sweep found more than the review did

Round 2 reproduced both findings first (all 13 of the reviewer's mutants left the round-1 suite at `27 passed`), then replaced the greps with a parsed-YAML assertion layer. The suite went 27 → 42 tests, 94 → 114 assertions, with **31 of the 94 round-1 assertions changed** across five classes and 63 left alone with reasons recorded.

### Lesson: the audit is worth more than the fix, and here it proved it twice
The review named two findings. The developer's own sweep found two more that no review round had listed, and one of them was worse than either finding:

- **`ci.yml`'s three new steps had no assertion at all.** Deleting the regenerate-and-diff step — R4's own subject, and the only thing that makes a hand-edited export a red required check — left the suite green. The test that was supposed to protect the task's central mechanism did not exist.
- **`set -euo pipefail` was unasserted** in both the workflow and the script. Dropping `-e` was invisible, and in the push step a failing commit then falls through to the push *and* to the `export regenerated; pushed <sha>` summary — the job reporting an outcome it never reached. A missing shell flag turning a failure into a success report is the kind of defect no amount of asserting on the *right* lines would have caught.

This is the second task in a row (APRAS-93 round 5 was the first) where asking for a **census** — how many assertions were examined, how many changed, with the untouched ones justified — produced findings the targeted fixes would have missed. The instruction that works is "audit every assertion of this shape and report the count", not "fix these two".

### Note: a hand-rolled YAML parser is now load-bearing
`pyyaml` was deliberately not added, because it would land in `backend/requirements.txt` — the file this task exists to keep honest — and therefore in the Vercel install. Defensible, and the ~130-line subset parser is guarded by four anti-vacuity tests including a decoy workflow carrying every asserted property **only** in a comment and in a `run:` body. But the parser's own correctness is now a dependency of every workflow assertion, which is a cost worth remembering next time something wants to assert on YAML.

### Note: two process hazards surfaced
- **A shadowed duplicate test.** Two definitions of `test_the_export_workflow_pins_the_scripts_uv_version` existed in round 1; Python ran only the later one, so the earlier assertions had never executed. A duplicate `def` in a test module is silent, and nothing in the suite or the linter flagged it.
- **The session scratchpad collided.** Four round-1 harness files were overwritten mid-run by another agent sharing the directory. No worktree damage and nothing left mutated, but concurrent agents writing harnesses to one shared scratchpad is a real hazard: a mutation harness interrupted between mutate and restore leaves the tree wrong. Agents should namespace their scratch files per dispatch.

## APRAS-121 — code review round 2: APPROVED

**66 mutants, built fresh by the reviewer in a privately-named directory, 60 of 66 caught.** The six green ones were each shown to be correct: a renamed push step (it is located by which step carries the secret), and five where the clean tree is red for a different reason.

What closed the two findings, worth keeping because these are the mutations a substring guard never catches:

- **`&&` → `||` between the job-gate conjuncts** — every literal still present, the gate inert. A text assertion looking for the conjuncts passes; the exact-set-of-conjuncts assertion fails.
- **the fork conjunct rewritten to `head.repo.full_name != ''`** — same shape, trivially true.
- **the branch prefix widened from `dependabot/uv/` to `dependabot/`.**
- **`persist-credentials: false` deleted**, which the developer argued only an *exact mapping* assertion can catch. The reviewer confirms the argument and names that mutant as the proof.
- **the token moved to a job-level `env:`**, and separately **onto the push command line**.
- **`-e` dropped from `set -euo pipefail`**, and **`set -x` added**.

### Lesson: a deletion needs an exact-mapping assertion, not a presence assertion
The general form, now proved on this repository: asserting a key is *present* cannot notice its *absence* elsewhere in the structure, and asserting on text cannot notice a logical operator flip that preserves every token. Assert the whole mapping or the whole conjunct set, exactly, so that both adding and dropping an element fails. This is the third distinct mechanism in the vacuity family (after moved text and comment prose) and the one with the cleanest fix.

### Note: the parser trade-off was checked, not waved through
The reviewer verified the `pyyaml` rationale is real rather than a rationalisation — the spec keeps the dev group in the export, and `backend/requirements.txt` does pin `pytest`, `ruff` and `coverage`, so a dev-only `pyyaml` really would reach the Vercel install. And it established the property that makes a hand-rolled parser tolerable: because every structural assertion compares **exact** values, parser information loss makes the **clean tree red**, not green — confirmed by eight mutants, with unsupported YAML (flow `on:`, `run: >`, a wrongly-indented step, a second job, an anchor) refusing or failing loudly rather than guessing into a pass. A parser that fails safe is a dependency you can live with; one that degrades to "no finding" is not.

### Note: the AST sweep for shadowed tests came back clean
Round 1's duplicate `def` was the only instance — the reviewer walked every module-level name. Worth adding as a standing check somewhere: a duplicate test name is silent in pytest and invisible to ruff.

## APRAS-122 — QA round 1: I briefed the verifier with a false premise

I told QA that four results were unverifiable before the push, and three of the four were already met. The pre-landing dispatched run **exists**: `37315213778`, `head_sha` `40d40a2` = the landing sha, every job `success` at attempt 1, logs showing `0.12.19`. So **R4, R2 and R3 are met**, only **R5** is genuinely pending, and the "closing window" I warned the operator about twice — the claim that the throwaway-branch run had to happen before the push or R4 would fail — was wrong. The run had already been done.

### Lesson: a deferral is a claim, and I never checked mine
I inferred from the recorded answer (`yes`, not a refusal) that R4's second path was closed, which is true — and then **assumed** the first path was unsatisfied without once running `gh run list`. One `gh` read would have settled it. Deferring a result is as much an assertion as asserting one, and it is the kind nobody audits, because "we cannot check this yet" sounds like caution rather than a claim. Worse, it propagates: I put the false premise into the dispatch prompt, so the verifier had to overcome its own briefing to get the right answer. **Verify before you defer, and write a deferral into a prompt only with the evidence that it is one.** The QA agent was right to contradict its instructions and say so in the first line of its report.

### The finding itself: a transcript that does not reproduce
R10 rejected. The audit's §6 lists 6 rows where the tree has **12 distinct third-party refs across 10 files, 43 occurrences**, omitting six — including the two `actions/github-script` refs that R10 names by sha prefix and demands as separate rows. The omission is justified by a recorded `$ ls -1 .github/workflows/ | wc -l` → `3`, which prints **10** today and printed **9** at landing.

The cause is precise and worth keeping: the six `gemini-*.yml` files have been in the working tree since 2026-05-14 and are untracked only because `.gitignore:132` carries `.github/workflows/gemini-*.yml`. The audit's `git ls-tree` and `git log --all` evidence is **true but off-target** — it proves not-committed, not not-there. A reasoned exclusion (gitignored, never pushed, therefore never executes) would have been fine; reaching the smaller row set through an unreproducible transcript is not.

**A `$ command` → output block inside a document is a claim with the same burden as any other**, and it carries more authority than prose because it looks like evidence. This is the second APRAS-93-shaped defect in a second document: a census whose scope was decided by a command nobody re-ran. The rework asks for every transcript in the file to be re-run and the count of corrections reported.

## APRAS-122 — round 2: the transcript ledger

The rework completed the census to all **12 rows** rather than excluding the gitignored files, on a good argument: the exclusion path lands on **7 refs across 4 files**, a number R10 never names, and it would make R10's "two separate `github-script` rows" requirement vacuous — the same shrinking move QA had just rejected. It kept the exclusion's reason as context but replaced the inference with evidence: `gh api 'repos/:owner/:repo/contents/.github/workflows?ref=master'` returns only `ci.yml`, `migrate.yml`, `release.yml`, so the six gemini files genuinely never execute on GitHub. **Prove the property, do not reason about it from a proxy** — "not in `git ls-tree`" was the proxy; "not in the contents API at `master`" is the property.

### 22 transcripts, 18 re-run, 6 corrected
Five more wrong blocks than the one QA found. Beyond the `ls -1` (3→10): the `grep … uniq -c` (6 rows→12), the `sort -u | wc -l` (6→12), the reusable-workflow exclusion `wc -l` (**claimed 0, actually 4**), and both §2 `setup-uv` step scans (3 files→10, and 4→5). The document now carries a §9 ledger with one row per transcript and its status.

That ratio is the lesson: **one unreproducible transcript in a document predicts others.** A command block is copied, adapted and re-pasted as a document grows, and nothing re-executes it, so the first stale one is a sample rather than an incident. The useful ask is never "fix this block" but "re-run every block and report the count".

### The old scan was wrong twice over, independently
Its `sed` also failed to strip the quotes the gemini files wrap `uses:` values in. So even on the right file set it would have under-counted. Two independent defects producing one plausible-looking number is the reason a census must publish the command *and* its output, re-runnable, rather than the total.

### Two claims checked unprompted; one false
- The spec's claim that the two `actions/github-script` refs' "declared inputs are not the same set" is **false**: both declare the identical nine, the only `action.yml` difference being `using: node24` vs `node20`.
- `checkout@8e8c483` is `refs/tags/v6.0.1` with 20 inputs while floating `@v6` now declares 21 — **the tag has moved** and gained `allow-unsafe-pr-checkout`. Nothing passes it, so not a finding, but a measured instance of exactly the drift the sha-pinning follow-up exists for.

And one honest note worth copying: the developer caught the second of those while correcting **its own draft**, which had guessed "v4.1.x-era", and recorded that rather than quietly fixing it.

### Note: a pre-existing suite failure, not ours
`4217 passed, 1 failed, 38 skipped` — the failure is `test_bcrypt_cost.py::test_passlib_is_not_installed`, because `passlib` is present in the local venv. Unreachable by a markdown edit, pre-existing, and worth its own cleanup at some point: a test asserting a package is *absent* fails on any machine where something else installed it.

## APRAS-125 — spec round 1

### My own error, caught by the spec author: `compile()` emits nested CSS
I briefed the generator that the real build emits `.dark\:bg-foreground:is(.dark *)`, citing the reviewer's pull from `dist/assets/*.css`. True of the **shipped** sheet, false of what this task will assert against: Tailwind's `compile()` emits **nested** CSS — `.dark\:bg-foreground { &:is(.dark *) { background-color: var(--color-foreground); } }` — and the flattened selector is **Lightning CSS's**, downstream. R1's assertion therefore has to compose outer + nested to arrive at the flattened form. The author probed it rather than taking my word, and the board's R1 now says so explicitly.

Second time this session that an evidence-shaped claim of mine was true of a different artefact than the one in question (the first: `git ls-tree` proving not-committed rather than not-there). The shape to watch: **a figure observed in one stage of a pipeline, quoted as a property of another.**

### The design that escapes the self-defeating guard
`compiler.build(candidates)` takes the candidate list **as an argument**, so Tailwind never scans the filesystem — which is what defuses APRAS-110's trap. Two compiles over **disjoint candidate sets** from one helper: a fixture compile whose candidates are a literal array in the test file (a positive control on the harness only), and a scanned compile whose candidates are exactly the extracted tokens. The non-merge is stated as an invariant and asserted.

The sharper half is the **provenance map** (token → the scanned files it came from). Asserting `dark:bg-foreground`'s provenance is exactly `[TenantHeaderLogo.tsx]` is direct evidence the test literal is outside the scanned set — because that token also exists in `TenantHeaderLogo.test.tsx`. A path-exclusion assertion says the filter was configured; a provenance assertion says the filter worked.

### The trap the spec named, which is instance seven of the family
**`dark:bg-foreground` appears twice in `TenantHeaderLogo.tsx`**: the `className` at line 91 and a **doc comment** at line 85. A mutation that kills only the `className` leaves the guard green — so the mutation proof itself would look diligent and prove nothing. Comment prose satisfying an assertion is now the third time in this log, and the first time it would corrupt a *mutation*, not an assertion. Mutation proofs need the same scrutiny as the assertions they validate: **grep the count before and after, and kill every occurrence.**

### Measured, not assumed
59 distinct tokens across 276 files, all 59 compiling to the expected property with a non-empty value, including `dark:hover:bg-white/10` (doubly nested, with an `@supports` fallback). And the existing `declarations()` helper is **depth-0 by design**, returning nothing for any `dark:` rule — so the naive reuse I implicitly suggested ("build on `themeTokenCompile.test.ts`") would have failed on every token.

## APRAS-125 — spec review round 1 (REJECTED)

### The stale-`node_modules` pattern, now twice in one week and once per toolchain
Finding 1 is the eslint discrepancy again, in a different tool, and this time it would have shipped a suite **green locally and red in CI**. `node -p "require('tailwindcss/package.json').version"` in `frontend/` prints **4.2.4**; `package-lock.json` pins **4.3.3**; `npm ci` in CI installs the lockfile's. And the two versions **emit different CSS**: 4.2.4 nests (`.dark\:bg-foreground { &:is(.dark *) { … } }`), 4.3.3 flattens (`.dark\:bg-foreground:is(.dark *)`). The spec's checker matched the selector by **string equality** against the nested shape, so under the pinned version it would match **0 of 59** tokens.

Note the spec author documented the eslint version split in its own §R6 — and then made the identical mistake about Tailwind one section later, reporting the installed version as 4.3.3 when it is 4.2.4. Knowing the failure mode does not protect you from it; **reading the version out of the running toolchain does.** The standing rule for this repository: any figure or shape derived from a tool must name the tool's version, read from the installed package at the moment of measurement, and say whether that matches the lockfile.

### Lesson: a positive control is not evidence a checker can fail
Finding 2 is the cleanest statement of this repo's recurring defect so far. The spec's anti-vacuity machinery — `it.each` naming every token, floors of ≥25 tokens and ≥200 files, a throw on the empty list — is **entirely satisfied by a checker that returns `true` unconditionally**. Every one of those devices proves the *inputs* are non-trivial; none proves the *verdict* discriminates. The missing piece is a **negative control**: a candidate that compiles *without* the expected property and must be rejected. The reviewer measured two — `dark:text-sm` (emits `font-size`/`line-height` only) and `dark:bg-[url('/x.png')]` (emits no rule).

Generalised: for every guard, ship a case that **fails** the checker on purpose. Floors, counts and naming are hygiene; a negative control is the proof.

### Lesson: shared mutable compiler state re-creates the leak you designed around
Finding 3 is subtle and would have been invisible in review. One Tailwind compiler instance **accumulates** candidates across `build()` calls — after `build(["dark:bg-foreground"])`, a later `build(["dark:bg-red-500"])` still contains `.dark\:bg-foreground`, on both versions. The spec's `compileIndexCss` is an obvious memoization target, and the moment someone memoizes it, the fixture compile's literals leak into the scanned compile and **APRAS-110's exact defeat returns through a performance optimisation**. Mandated fix: a fresh `compile()` per candidate list, asserted with a fixture-only sentinel token proven absent from the scanned sheet.

The general shape: when a design's correctness depends on two things being **disjoint**, the disjointness must be mechanised and asserted, not merely described — because the next person's reasonable refactor is what breaks it.

### Ruling worth keeping: the doc comment here is NOT the vacuity failure mode
I had flagged `TenantHeaderLogo.tsx:85`'s doc-comment occurrence as instance seven of the comment-prose family. The reviewer corrected that: **Tailwind's production scan reads comment text**, so a comment literal genuinely emits the class and genuinely paints. The guarded property is the real property. The spec's demand to remove *both* literals in the mutation proof is correct for a different reason — not because the comment is a false positive, but because it is a true one.

### APRAS-125 spec round 2: the reviewer's own control was misclassified
The revision accepted all four findings and installed 4.3.3 into a scratchpad to re-run the probes on both versions rather than trusting the review's figures — which caught one: **`dark:bg-[url('/x.png')]` does emit a rule** on both versions (`background-image`), so it exercises the *wrong-property* branch, not the *missing-rule* branch the review assigned it. `dark:bg-nosuchcolour` is the real missing-rule control.

Worth keeping because of who made the error: the reviewer that had just correctly diagnosed "nothing proves the checker can fail" then proposed a negative control that tests a different branch than it thought. **A negative control is itself a claim about behaviour and needs the same execution as anything else.** Three agents in a row this session have had an evidence-shaped claim corrected by the next one running it — my `git ls-tree`, my flattened-selector briefing, and now this. The pattern holds: the error survives exactly as long as nobody executes.

### Note: APRAS-127 created for the version drift
The spec author declined to reconcile `node_modules` with the lockfile, keeping APRAS-125 small and making the guard robust across both emission shapes, and flagged that two documented drifts (tailwindcss 4.2.4 vs 4.3.3, eslint 9.39.4 vs 10.11.0) predict a third found the same way. Created **APRAS-127** (`high`) to close them, with an expected result that a check must **fail** when an installed version diverges from the lockfile — so the drift cannot return silently. Asked the reviewer to rule on whether a guard specified against two emission shapes is carrying complexity that belongs in the reconciliation instead.

## APRAS-125 — spec review round 2: APPROVED

The reviewer re-implemented §2's reader exactly as specified and re-ran every figure on **both** Tailwind versions, accepting no 59/59 claim on trust: 59/59 matched, **0** per-token failures, **59** dark-gated, R1's exact string holding on both (4.2.4 resolves two effective selectors for that token, 4.3.3 one; both contain it). It also established the depth-blind harvest is **necessary, not stylistic** — a depth-0 variant of the same reader fails exactly the 8 stacked tokens on 4.2.4.

### It withdrew its own round-1 control, and named the cause
`dark:bg-[url('/x.png')]` does emit `background-image` on both versions. Its round-1 "no rule" reading was an artefact of **its own probe's `escape`**, which covered only `:`, `/`, `.` and so never matched `.dark\:bg-\[url\(\'\/x\.png\'\)\]:is(.dark *)`. So the spec author's correction stands, and the `escape` definition adding `[ ] ( ) ' #` is doing real work.

That is the fourth evidence-shaped claim corrected by execution this session, and the most instructive: **the reviewer's probe was less correct than the spec it was reviewing**, and the defect was in the reviewer's *instrument*, not its reasoning. A probe written to check someone else's work needs the same scrutiny as the work.

### The version split upheld on a better argument than the one offered
The author kept APRAS-125 green on both versions and pushed reconciliation to APRAS-127, arguing it keeps the task small. The reviewer accepted — but on the ground that the dual-version requirement adds **zero marginal complexity**, verified: its implementation has no version check and no branch, because the stacked tokens nest their declarations inside `@media (hover: hover)` on **both** versions, so a reader that handles that handles `&:is(.dark *)` for free. There is nothing to move. And the asymmetry runs the other way: this task is itself the evidence that a Tailwind *minor* changes emitted CSS, so pinning the guard to one version makes it hostage to the next bump.

Worth keeping as a decision rule: **"support both" is cheap when the general mechanism was required anyway, and expensive only when it forces a branch.** Check which before paying to avoid it.

### The free strengthening taken
§2 as approved let the paint and the gate be satisfied by **different matched rules** — a token dark-gated by one rule and painted by another would be accepted. Requiring the paint to come from the **subtree of the gated rule** costs one `.filter()`, and the reviewer measured the stricter form at 59/59 with 0 failures on both versions, controls unchanged. Folding it in.

## APRAS-127 — spec round 1: the drift is 129 packages, not two

I created this task for two tool-version drifts. The spec author measured the real scope by `npm ci`-ing byte-identical manifests into a scratch clone, and my brief understated it by two orders of magnitude:

| | real tree | after `npm ci` |
|---|---|---|
| non-optional lock entries compared | 335 | 335 |
| version mismatches | **129** | **0** |
| non-optional top-level absent | **12** | **0** |

**30 of the 38 declared direct dependencies are wrong**, with four majors nobody had noticed: `vitest` 4.1.11→5.0.3, `@vitest/coverage-v8` likewise, `jsdom` 29.1.1→30.1.1, and the known eslint 9→10. The installed tree also violates `package.json`'s own ranges — the manifest asks `eslint: ^10.11.0`.

### What this means for every frontend figure measured this session
The `198 files / 2594 tests` baseline, the coverage percentages, the lint counts, APRAS-125's 59-token census — all were taken under **vitest 4.1.11 and jsdom 29** while CI runs vitest 5 and jsdom 30. The author measured the lockfile's side as green (`npm run build` 0, 198/2594, coverage 0 at 91.64%), so nothing is actually broken, and APRAS-125 happens to be safe because its reviewer insisted on measuring both Tailwind versions. But the general case was luck, not discipline: **a local measurement in this repository has been a measurement of a different dependency tree than CI's for an unknown number of weeks.**

The honest reading of the two earlier incidents is that eslint and tailwindcss were not two drifts — they were the two drifts that happened to be *version-sensitive in a way someone noticed*. 127 others sat silent.

### Lesson: refusing a CI check because it would be tautological
The author declined to add a CI step for the version guard, and the reason is worth keeping: **CI installs with `npm ci`, so a CI assertion that the installed versions match the lockfile is green by construction.** It would read as coverage and prove nothing — the eighth vacuous check here, and this one proposed by me. The guard belongs where the drift actually lives, which is a developer's local tree, so it is a vitest case that a developer runs.

### The judgement call I want to remember either way
The spec records the lint major and the **re-derivation command** in `AGENTS.md` but asserts the **count nowhere**, arguing that a count assertion goes red on every unrelated commit and gets bumped reflexively — which is precisely how `368` went stale and then got quoted for a week. That is a real tension: an unasserted figure can drift silently, an asserted one trains people to update it without looking. Recording the command rather than the number is the better side of that trade, and it generalises: **publish the derivation, not the result.**

### And the comment-prose family again, pre-empted
`frontend/src/__tests__/themeTokenCompile.test.ts` — the one suite calling Tailwind's `compile()`, so the most drift-exposed file in the tree — opens by claiming "Tailwind **4.2.4**'s own `compile()`", which the lockfile contradicts. The spec **deletes the number rather than asserting it**, explicitly because this repo has twice shipped a guard satisfiable by comment prose in its own asserted file. First time a spec here has designed around that failure mode before committing it.

## APRAS-127 — spec review round 1 (REJECTED): the vacuity moved instead of leaving

The spec answered APRAS-125's "nothing proves the checker can fail" lesson with an exported pure comparison function plus a committed case feeding it a divergent pair. The reviewer accepted that the **comparison** is now provably failable — and found the hole had **relocated one layer down**, into the *acquisition*:

> A harness that resolves each version out of the lockfile object it already holds, instead of reading `node_modules/<path>/package.json` from disk, satisfies both negative controls, the empty-input throw and the count assertion — while reporting **0 mismatches on a tree that has 129**.

That is the sharpest instance in this log. The guard compares A against B; if both A and B are read from the same source, every control still passes and the comparison is between a thing and itself. The hand-run end-to-end mutation catches it exactly once and **commits nothing**, so it protects the first run and no later one.

**The rule: a negative control must cover the step that could be wrong, not the step that is easy to isolate.** A pure function is the easy half to test and the unlikely half to break. Where a guard's correctness depends on reading real state, the committed control has to feed it an **on-disk fixture** with a known-wrong value.

### A refusal contradicted by its own placement
The spec declined a CI step on the (good) ground that CI installs with `npm ci`, so the assertion would be green by tautology. But it put the guard in a vitest case under `frontend/src/__tests__/`, and `ci.yml:348` runs `npm run test:coverage` over the whole suite — so **CI runs that tautology anyway**. The reasoning and the placement had to agree; stating a principle does not implement it.

### The other three
- The "compared count equals the lockfile's own count" control compares **two results of the same predicate over the same file** — unfailable; and its only non-tautological reading contradicts the spec's own nested-entry leniency, which **7 real nested entries** exercise today (a number the spec never stated).
- `AGENTS.md:380` says **"Vitest 4"** against a lockfile pinning 5.0.3 — the same drift, in the same table, **one line above** the `ESLint 9` row the spec was fixing. Fixing a falsified line while its neighbour stays falsified is how a stale document keeps its authority.
- The `AGENTS.md` major check had **no defined behaviour when the prose matches nothing** — which is this repository's *first* vacuous check, verbatim: a grep whose text had moved. Eight instances in, the family's founding member was about to be re-committed inside the task designed to stop that family.

### APRAS-127 round 2: making the wrong design unspecifiable
The fix for the relocated vacuity is the best shape this log has recorded. Rather than adding a test that would catch a lockfile-resolving reader, the spec makes that reader **impossible to specify**: the installed-version reader **takes a root directory as a parameter**, stated as the only way a committed test can point it anywhere but the real `node_modules`. A reader hard-wired to one path now fails the *spec*, not just the suite.

And the control's load-bearing clause is chosen with the same care: the reported *installed* value must equal **the fixture's own version string**, which kills both the harness that reads from the lockfile and the harness that fails for the wrong reason. Asserting "it reports a failure" would have accepted the second.

**The generalisation: when a guard can be built two ways and one of them is silently useless, change the interface so the useless one cannot be written.** A parameter where a constant would do is cheap, and it moves the protection from the test suite into the type of the function.

### A cost priced rather than argued
The CI tautology was resolved by **measuring both sides** instead of reasoning about them: **125 ms** to read the 316 present entries, against a frontend job with a **2.55-minute median**. The guard stays, CI runs it, and the spec says plainly that the earlier draft's reasoning was wrong. The alternative — an `exclude` or env-gated skip — was rejected as a second mechanism that can rot, and because it would make the one place the guard is *not* exercised the only place anyone reads a red suite. That last clause is the real argument: a skip in CI means the guard only ever runs where nobody is watching.

### Note: the reconciliation creates one divergence it cannot fix
jsdom 30.1.1 declares `^22.22.2 || ^24.15.0 || >=26.0.0`; local node is **v24.13.0**, so `npm ci` will emit `EBADENGINE`. The spec records it in its own section and fixes it nowhere, because raising local node is an operator action on a machine. Correct call — but worth flagging to the operator rather than burying, since it is the one part of this task that will not go green on its own.

### Still unsettled, and worth someone's curiosity eventually
Why `node_modules` is **older than any recent local install would leave it**. Dependabot explains the lockfile moving forward; it does not explain the installed tree being 129 packages behind. The spec declines to chase it as unnecessary for the fix, which is right, but the answer would tell us whether this recurs.

## APRAS-127 — spec review round 2 (REJECTED): both defects inside the fix

The structural fix to the relocated vacuity **works** — the reviewer rebuilt all three pieces plus two deliberately bad harnesses against a real on-disk fixture and showed the control catches the lockfile-resolving reader (0 findings) and the disk-touching-but-misreporting one (placeholder version on *both* packages). It calls making the root parameter a **specification** requirement the right move.

Both new findings are in that fix, and both were measured rather than argued.

### Lesson: a fixture is a scope, not just a file
The guard derives **335** locked entries; the fixture holds **three**. Pointing the reader at the fixture therefore yields **320 findings — 319 absent, 1 mismatch** — not the two the spec describes. The control only behaves as written when the **locked map is also restricted** to the fixture's packages, which the spec never said. As worded, the result is satisfied by a guard that buries the one finding that matters among 319 that do not.

The general shape: a negative control substitutes a *small* world for the real one, and every input the guard reads must be substituted together. Swapping the installed side while the locked side stays full-size does not produce a smaller test — it produces a different, noisier one that happens to contain the right answer.

### The fixture could not be committed, which would have been instance eight
`frontend/.gitignore:10` is a bare `node_modules`, and `git check-ignore -v` confirms it ignores the fixture at any depth:

```
frontend/.gitignore:10:node_modules	frontend/src/__tests__/fixtures/node_modules/eslint/package.json
```

So the anti-vacuity control would have been **green locally and absent in CI** — vacuous in the file whose only job is to stop that. And the obvious remedy fails: `!…/node_modules/**` alone leaves it ignored, because **git will not descend into an excluded directory**; only the layered `!…/node_modules/` plus `!…/node_modules/**` works, which the reviewer tested in a throwaway repo rather than asserting from memory.

Two things to carry. **A committed fixture is a claim that it is committed** — "the fixture files are tracked" has to be asserted, because their absence is silent and leaves the suite green. And more generally: when a test's data lives at a path shaped like a build artefact, check `git check-ignore` before designing around it.

I also asked whether the fixture needs to sit under a `node_modules` path at all — if the reader takes a root parameter, the layout only has to look like a package tree relative to that root, and any other directory name sidesteps the ignore rule entirely.

### APRAS-127 round 3: both maps become parameters, and a correction to the reviewer
The fix generalises the previous one. Round 2 made the **root** a parameter so the reader could be pointed off the real tree; round 3 makes the **locked map** a parameter too, so the control can restrict *both* sides. Each parameter carries its own stated reason in the spec, which is what stops the next person from collapsing one back into a constant.

The detail that keeps the control honest: the restricted locked map holds **each fixture package's real version read from the real `package-lock.json`**, so the mismatch's locked side still binds to this repository rather than to an invented number. A control built on two fabricated versions would pass while testing nothing about the repo.

### The author corrected the reviewer, and the correction is better than the finding
I had relayed "fixture absence is silent". It is not, once result 2 demands exactness: a fixture missing in CI makes all three packages read absent, so the control goes **red**. What it would be is red with a **misdiagnosis** — a reader bug and an untracked fixture produce an identical failure. So trackedness is asserted not to convert silence into noise, but to **separate two causes that share one symptom**, via `git ls-files --error-unmatch` per path, failing rather than skipping when git is unavailable.

Worth keeping as a distinction: "this failure is silent" and "this failure is indistinguishable from another" call for different remedies, and only the second one was true here. A guard that fails for the wrong stated reason still wastes the next person's hour.

### Why the fixture keeps the `node_modules` name
I suggested renaming the fixture directory to sidestep the ignore rule entirely. The author declined with a fidelity argument: **the lockfile's keys *are* `node_modules/`-prefixed paths** — the nested ones carry the segment internally — and the reader resolves `<root>/<lock key>` verbatim. A differently-named directory would force a path rewrite the production run never performs, so the control would exercise a **different path construction** from the one it exists to protect.

That is the right instinct and a good rule: a negative control may shrink the world, but it must not change the code path. Paying two lines of `.gitignore` to keep the construction identical is the cheaper side of that trade.

## APRAS-127 — spec review round 3: APPROVED

Measured rather than reasoned, which is why this one closes. With both maps restricted at the fixture root:

```
  conformant   findings=2  exactly-two-and-nothing-else=PASS
  LOCKBUG      findings=0  FAIL
  MISREPORT    findings=3  FAIL   (installed "0.0.0-unknown")
  fixture root MISSING / conformant  findings=3  FAIL
```

Result 2 is satisfiable by a conformant implementation and unsatisfiable by both bad harnesses — the first guard in this log whose anti-vacuity property was *demonstrated on an executable artefact* before any code shipped.

### The reviewer's own figure was wrong by one, in the direction that flatters the design
The spec said a lockfile-resolving reader "produces one finding, not two". It produces **zero** — the same bug also hands the absent package a version, so nothing is reported at all. Non-blocking, and the conclusion stands, but it matters in a spec whose authority is "measured rather than quoted": a number asserted while adjacent to real measurements borrows their credibility. Corrected in the spec and on the board.

### Two risks foreclosed by checks nobody asked for
The reviewer noticed result 1 runs `npm ci` while result 2 needs a fixture on disk, planted the fixture in a scratch clone and ran `npm ci`: **exit 0, fixture untouched.** And it tested a module-shadowing hazard it was about to raise, found node falls through to the real package, and **recorded the negative result so it is not raised again.** Writing down what you checked and found fine is cheap and saves the next reviewer a round — this log should carry more of it.

### The looseness worth generalising
Decision 3 still never says where the installed reader gets its path set, and the reviewer calls that harmless: result 2's exactness makes both implementations correct. **An assertion that pins observable behaviour makes the unstated implementation detail irrelevant** — which is the opposite of this repository's usual failure, where under-specified behaviour let a vacuous implementation satisfy a described one. Specify the observable outcome tightly enough and you need fewer rules about the mechanism.

## APRAS-125 — implementation: the strengthening I asked for was itself unfalsifiable

The implementation landed with 199 files / 2669 tests green (74 new cases), coverage 91.73/85.67/87.95/92.44 against the 80/78/76/80 gate, build 0, eslint printed as v9.39.4 first and unchanged at 370/368/2. Eleven mutations, including R6's 2 → 0 → 2 transcript with APRAS-110's 18 cases green on the same mutant — which is the point of the whole task: the old suite cannot see the mutant, the new file can.

### The part worth remembering
The developer found **two of the spec's own assertions unfalsifiable as written** — the gate filter and the same-rule paint requirement — **both deletable with all 59 cases still green**. The same-rule requirement is the strengthening *I* asked for in spec round 2, after the reviewer measured it at 59/59 and called it a free improvement.

So the sequence was: a reviewer proposes a strengthening, measures that the stricter form still passes 59/59, I fold it in, the spec is approved by two rounds of review — and the assertion could be deleted without any test noticing. **Measuring that a stricter check still passes is not evidence that it does anything.** 59/59 before and 59/59 after is exactly what a no-op produces. The missing step, every time, is the mutation: delete the clause and see whether anything goes red.

That is instance nine, and the first one introduced by a *review* rather than by an implementation. Four distinct mechanisms in the family now: text that moved, comment prose in the asserted file, a comparison between a thing and itself, and an anti-vacuity apparatus satisfied by a checker that returns `true`. This adds a fifth: **a strengthening validated by "it still passes".**

Each of the two now carries a negative control that kills its deletion, which is what the spec should have demanded in the first place.

### Also: a prose figure off by five
§5's "dropping `text` loses 31" measures **26**. Prose, not an assertion, so not a defect — but the spec's authority rests on measured figures, and an unmeasured one sitting among them borrows their credibility. Same shape as APRAS-127's "one finding" that was zero.

### Four things stated as unverified rather than glossed
Tailwind 4.3.3 and eslint 10.11.0 directly (both need `npm ci`, which I forbade, since the reconciliation is APRAS-127's job and awaiting sign-off), §5's token-loss figure, and the `@supports` prelude trap — which the developer says **no input in this tree can exercise**. Naming the last one is better than inventing an input to cover it; a test for a case the codebase cannot produce is a test of the test.

## APRAS-125 — code review round 1 (REJECTED): instance ten, in the task's own hinge

One finding, and it is mechanism #3 again — a thing compared with itself. `darkVariantCompile.test.ts:344-349` asserts `SCANNED_FILES` against **the same `EXCLUDED` constant that produced it**, so it cannot fail for a wrong exclusion set. The reviewer demonstrated it on the shipped tree: three separate arm deletions each leave the suite **75/75 green**, including the case titled *"excludes every test, mock, story and declaration path"* — and dropping the `test` segment arm quietly admits `src/test/setup.ts`, `classTokens.ts` and `permissionFixtures.ts`, taking the scanned set from 276 to **279** files.

That is R2, the hinge of the entire task: a silently widening exclusion set is precisely how APRAS-110's self-defeating guard returns. Fix is a **literal path table** — one path per arm plus a kept-path control, so the table cannot pass by excluding everything.

**Three unfalsifiable assertions in one task** — two the developer found in the spec, one the reviewer found in the implementation. The question that catches all three is the same and takes one line to ask: **is either side of this comparison derived from the thing it is meant to check?** Worth making that a standing review question rather than rediscovering it per task.

### What the review got right beyond the finding
- Built **17** of its own mutants rather than re-running the developer's eleven, and ran the mandatory R6 one itself: `grep -c` 2 → 0 → 2, new suite red, **APRAS-110 green at 18/18 on the same mutant** — the clearest statement of why this task exists.
- Diffed the moved helpers against `HEAD` and confirmed `rules`/`declarations` are **byte-identical**, so "`themeTokenCompile.test.ts` stays green" really is a proof about unchanged code.
- **Closed the 4.3.3 gap** by installing the pinned version in its own scratch dir instead of accepting the substitute on trust: 276 files / 59 tokens / 8 stacked, **59/59 gated and painted**, flattened shape and the exact selector confirmed, all controls identical. The substitute was adequate *and* the real version is now measured — which is the right order: accept the workaround, then remove the need for it.
- Corrected two counts: the suite is **75** cases, not 74, and §5's token-loss figure is **26** (bg 33 / text 26), not 31.

### APRAS-125 round 2: the sweep found a fourth, and it was the subtlest
37 `expect(` call sites examined, 3 changed — two the reviewer's, one the developer's own: **the sentinel case asserted only that `dark:bg-fuchsia-300` has no rule in the scanned sheet**, which a *misspelled* sentinel satisfies for entirely the wrong reason. Measured: `dark:bg-fuchsia-3000` leaves the suite 97/97 green. The case existed to prove the fixture compile does not leak into the scanned compile, and it would have passed just as well if the sentinel had never been a real token.

That is the shape worth naming: **an assertion of absence is satisfied by anything that cannot be present**, including a typo, a renamed constant, or a token the compiler would reject anyway. Every absence assertion needs a paired presence assertion somewhere — here, that the sentinel *is* painted in the fixture sheet. The developer added exactly that, and the misspelling now reddens.

The same reasoning fixed the provenance case: each named file is now asserted to **exist** and to **really carry a token** before its absence from the scanned set means anything. Otherwise the absence is the same vacuity one level down.

### And the helper this task introduced had carried the comment-prose defect
`tailwindSheet.ts` held `dark:hover:bg-white/10` in a doc comment while its own header claimed it carried none — the mechanism that has now appeared in APRAS-121, APRAS-127 and here. The requirement now has a case asserting the helper matches zero tokens, so the claim is checked rather than stated.

### Note: four exclusion arms have no possible real input
`src` contains **no** `__mocks__`, `__fixtures__`, `*.stories.tsx` or `*.d.ts` at all, so four arms of `EXCLUDED` had no real file to name and their table rows are synthetic. The developer disclosed this rather than quietly inventing paths. It raises a question worth answering once: an exclusion arm that nothing in the tree can trigger is either future-proofing or dead code, and the choice should be deliberate — asked the reviewer to rule.

## APRAS-125 — code review round 2: APPROVED

Fourteen fresh mutants from the reviewer, and the before/after table is the clearest evidence in this log that the fix worked:

| mutant | round 1 | round 2 |
|---|---|---|
| drop `test` segment arm | 75/75 green | `testing/helpers.ts` row red |
| drop `\.(test\|spec)\.[^/]+$` | 75/75 green | two rows red |
| drop `\.stories\.tsx$` | 75/75 green | `button.stories.tsx` row red |
| drop `\.d\.ts$` | 75/75 green | two rows red |

Plus `SCANNABLE` losing `css`, the wiring ceasing to call the predicate (7 red), and the wiring diverging from the predicate for one untabled path (provenance case red). One mutant was classed **equivalent rather than surviving** — unanchoring `SCANNABLE` changes no verdict, since no path under `src` contains `.ts/.tsx/.css` other than as a suffix. Naming that distinction matters: a surviving mutant is a hole, an equivalent one is noise, and conflating them inflates a mutation score.

### Ruling worth keeping: synthetic rows are the strongest test of a pure predicate
Four exclusion arms have no possible real input in this tree, so their table rows are synthetic — and the reviewer ruled that *better* than dropping the arms: `isScanned` is a pure predicate, a hand-written input table is the strongest form of test for it, and each synthetic arm's deletion reddens exactly its own row. Dropping the arms would be worse, because `.d.ts` returns with any vendored types file and `*.stories.tsx` with Storybook — and both are **literal-bearing files written for tools**, which is the APRAS-110 leak vector. The near-miss keepers turned out to be the only thing catching the substring widening.

### The silent-narrowing twin, still open
Non-blocking but logged: an exclusion arm that swallows a **token-bearing directory** is silent — `|^features\/lot-management\//` drops **14 of 59** guarded tokens with the suite **83/83 green**. Round 1's finding was an exclusion set that could *widen* unnoticed; this is the same shape one level up, a set that can *narrow* unnoticed. No assertion claims coverage of the token set, so it is not a vacuity — it is a missing floor. Asked the developer to close it with a real floor (mutation-proved against that exact arm) or say why it is out of scope.

### Two factual errors shipping in the commit
The §5 token-loss figure was fixed in the test comment but **not** in the staged spec (`docs/tasks/APRAS-125-spec.md:247` still says "loses 31 (59→28)"; measured 26), and `darkVariantCompile.test.ts:362` credits APRAS-127, which is the `node_modules` reconciliation task. Both cheap, both shipping — a correction applied in one of two places is how a figure gets quoted wrong later, which is this session's recurring story.

### Carried forward rather than fixed now
The non-empty-value clauses at `:131` and `:309` remain unfalsifiable; `declarationsDeep`'s prelude-discard comment overstates its necessity and its own comment strip is dead; `verdicts()` is called only by its own throw test. Real, but not worth another round in this task.

### APRAS-125: the silent-narrowing hole closed by directory coverage, not a count floor
The developer judged the swallowing hole in scope and closed it — and the reasoning for *how* is the part worth keeping. It added a case asserting that **every immediate subdirectory of `src/` and of `src/features/` holding a scannable file contributes at least one file** to the scanned set, with the oracle built independently of the scanner (`sourceDirectories()` consults `SCANNABLE` and a literal list of the four excluded directory names, **never** `EXCLUDED`) and its own `>= 5` floor so it cannot be green over an empty list.

It chose that over the token-count floor I suggested, with a measurement: a floor of 50 catches swallowing `lot-management` (59→45) but **not** `features/dashboard` (59→51) — and it is a number the palette→token migration would force someone to keep lowering. A count floor tracks a quantity that legitimately moves; directory coverage tracks the structural property that must not. Mutation-proved three ways: the exact `^features\/lot-management\//` arm reddens with a named message (and the suite drops to 85 cases, confirming the reviewer's 14-of-59), `features/dashboard` reddens too, and forcing `sourceDirectories` to `[]` reddens both rows on the floor.

**The general rule: prefer a floor on structure over a floor on a count, when the count is something a legitimate change will move.** A threshold people have to keep lowering stops being a guard and becomes a chore.

### And an honest refusal to guess
The comment at `darkVariantCompile.test.ts:362` credited APRAS-127 for a lesson that is not APRAS-127's. The developer could not establish the right id — it grepped `docs/reviews/` and this log, and the nearest hits (APRAS-119, APRAS-110, APRAS-98) are different findings — so it **de-attributed** the comment rather than swapping one wrong id for another. Right call: a confident wrong citation is worse than none, because the next reader follows it.

## [APRAS-124] Cache the public tenant logo route so repeat page loads do not re-fetch the bytes — 2026-10-12
- `_if_none_match_matches` splits on "," naively. An ETag containing a comma inside quotes would split wrongly. This is harmless here because our own tag is hex only.
- The `InsufficientContrastError` removal and the `validated_brand_theme` rewrite are in the same file's diff but belong to another task (APRAS-100). They were not reviewed.

## [APRAS-124] Cache the public tenant logo route so repeat page loads do not re-fetch the bytes — QA — 2026-10-12
- The mutation log's diffs are compacted renderings, not raw git diff. The log says so, and the hunks are intact and sufficient.
- test_passlib_is_not_installed fails in the local venv. Re-syncing the venv would clear it, but that is outside this task.

## [APRAS-77] Migrate hard-coded palette classes to semantic theme tokens — 2026-10-12
- Results 3 and 4 are already satisfied. Keep them labelled as verification-only so the developer does not invent work.
- The reconciliation of the byte-identity claim (umbrella Result 2) is sound. Make sure the report states it explicitly to the operator.
- The fallback clause in the Approach lets the developer swap the asserted token when a row's token is not emitted. A reviewer should confirm the substitute is a tenant-bound primary-family token.

## [APRAS-126] Add frontend/.vitest/ to frontend/.gitignore — 2026-10-12
- The reviewer claimed `frontend/.gitignore` already contains `.vitest/`; the orchestrator's grep found no `vitest` line in that file, so the claim looks wrong. The developer should check the file itself before concluding the task is a no-op.
- "Alongside `dist` and `coverage`" is loose, since placement does not matter to git. Not blocking.
- Expected result 2 depends on vitest actually writing to `frontend/.vitest/`. The spec's `git check-ignore frontend/.vitest/x` fallback covers this.

## [APRAS-77] Migrate hard-coded palette classes to semantic theme tokens — 2026-10-12
- (code review) ReservableSpacesPage and AssemblyMinutesView tests only prove the Button primitive carries the token, not that the page uses the default variant. Spec-sanctioned; a note in the test titles would help, optional.
- (code review) Run eslint and tsc --noEmit on the two files before commit; not verified by the reviewer.

## [APRAS-100] Turn the brand contrast failure into a warning instead of a hard block — 2026-10-14 (QA)
- The work was swept into 2767f15 (titled APRAS-127), so `git log --grep APRAS-100` misses it; note it in the task record.
- Expected result 8's "public_branding.py unchanged" is ambiguous now that APRAS-124 edited the file; scope it to the branding handler.
- Expected result 2 depends on vitest actually writing to `frontend/.vitest/`. The spec's `git check-ignore frontend/.vitest/x` fallback covers this.

## [APRAS-100] Turn the brand contrast failure into a warning instead of a hard block — 2026-10-14 (QA, round 2)
- One frontend test failed on a run that overlapped with pytest and passed on rerun, which suggests a timing-sensitive test somewhere. Its identity is unknown.
