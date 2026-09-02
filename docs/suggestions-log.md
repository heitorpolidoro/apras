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

## [APRAS-39] Modularizar features por tenant — 2026-09-01

- S1: ER-7 diz '5 -> 7' flat enquanto vizinhos usam 'predicted'; a 49 pode levar a base a 6 (PATCH superuser) - aplicar o mesmo hedge para 6 -> 8 nao ler como falha.
- S2: dizer que GET /permissions/ fica sem strip (por construcao) e precisa, para o resend do 5.5.
- S3: registrar que has_admin_capability nao esta em nenhum lado do split (le flags, nunca permissao; a 49 o deleta).
- S4: docstring de assert_can_grant fica obsoleta apos o swap - incluir no diff do 5.5.
- S5: 'referenced nowhere else' do ER-4 lido literalmente exclui o def; usar a forma precisa do 12.1.
- S6: snippet do 5.1 reescreve o branch que o spec manda mover verbatim.
- S7: pinar precedencia 404-vs-400 para PUT com tenant e modulo ambos desconhecidos.

## [APRAS-40] Área de assinatura com contratação de módulos pelo tenant — 2026-09-01

- 9.2.2 (~l.1360): 'os tres da F2 nao sao editados' contradiz a tabela do 9.2.5 (test_baseline_file_exists muda para F2_CELL_COUNT); dizer 'o par' e nomear os dois.
- 9.2.5 (~l.1845): 'treze casos, nove por uma linha' vs 'oito dos nove' (~l.1810) - alinhar; ER-10 ja escopa a afirmacao aos seis callers de holds().
- 9.2.5 (~l.1810): a forma de linha de test_cell_matches_the_recorded_baseline e `expected = baseline_status(load_baseline(), ...)`, nao `baseline = load_baseline()`.
- 9.1/10.2/12: a string '89 POST/PUT/PATCH routes' vive no comentario `#:` acima de REQUEST_BODIES e no docstring de _NoBody (dois lugares), nao no docstring do modulo.
- can_contract com conjunto ent.managed agora em quatro sites; test_baseline_covers_exactly_the_matrix duplica a assercao de particao - candidato a colapsar na implementacao.

## [APRAS-44] Gestão de infrações com regras e escalonamento por condomínio — 2026-09-02

- 7 diz 'as sete tabelas carregam created_at/updated_at' mas 12.2 afirma que infraction_stage nao tem updated_at (as listas de colunas do 7.2 concordam com 12.2) - alinhar a frase.
- 12.6/8.4/11 escrevem world.infraction / world.lot / world.occurrence.lot_id; MatrixWorld em 4f952b0 so carrega ids (lot_id, resident_id, occurrence_id); o bloco de codigo do 12.6 ja usa a grafia certa.
- 4.5 'nao ha rota page/page_size em lugar nenhum' e exagero: uploads.py:40 declara page; page_size nao existe; skip/limit segue correto.
- Precificacao de acao explicita fora da escada nao declarada (fine_amount de MULTA explicita, defense_due_on de NOTIFICACAO explicita sem passo correspondente) - decidir na implementacao: usar o ultimo passo do mesmo tipo da escada ou exigir os campos no corpo.
- infraction_contestation.stage_id: declarar nulabilidade (7.2); e colisao latente de FK: infraction_stage.infraction_id CASCADE vs infraction_contestation.stage_id RESTRICT.
- test_policy_rejects_non_contiguous_step_order diz '422/400' - unico ou-ou de status no spec; fixar 422.
- InfractionCreate.source_occurrence_id e aceito e ignorado silenciosamente - remover do schema ou validar.
- 7.7(2) usa uma unica string de detail tambem para residente inativo; citacoes de linha do 4.5 derivaram; citacao do AGENTS.md no 7.2 esta abreviada.
