# APRAS-53 — Upload de evidências e anexos de contestação no cliente de infrações

> Origem: QA da APRAS-44 (2026-09-06). A API já aceita `evidence_urls` na
> infração e `attachment_urls` na contestação, e o detalhe já renderiza os
> primeiros — mas `NewInfractionModal` não tem controle de upload,
> `ContestationForm` é só corpo, e `InfractionStageTimeline` ignora
> `attachment_urls`. A APRAS-44 §10.1 descreve os três. Esta task fecha a
> lacuna **no frontend**: nenhum arquivo de produção do backend muda. A única
> coisa que ela escreve fora de `frontend/` é um caso pytest — a outra ponta do
> pino de contrato descrito em §3.6(c) — mais uma nota de documentação em
> `AGENTS.md`.
>
> **Precondição de board:** `blockedBy: ["APRAS-51"]`. A APRAS-51 entra
> **antes** desta task e converte `POST /api/v1/uploads/photo` de
> `get_current_active_user` para `require_permission("uploads:photo_create")`.
> Todo este documento — §2.3 em especial, e as quatro ERs — está escrito
> **contra a árvore pós-51**, não contra o `master` de hoje. §2.3 diz
> explicitamente o que é verdade em cada uma das duas.

---

## 1. Scope

**Cobre:** o controle de anexos que falta nos dois formulários do módulo de
infrações, o gating desse controle pela permissão que a APRAS-51 passa a
exigir, o preenchimento dos dois campos que já existem e já fazem round-trip, e
a exibição dos anexos nas duas superfícies de leitura.

Caminhos completos, porque o módulo vive sob `features/infraction-management/`:

| Entrega | Superfície |
|---|---|
| Controle de anexos em `NewInfractionModal` (modo *create*), preenchendo `InfractionCreate.evidence_urls` | `frontend/src/features/infraction-management/components/NewInfractionModal.tsx` |
| Controle de anexos em `ContestationForm`, preenchendo `ContestationCreate.attachment_urls` | `.../components/ContestationForm.tsx` + `.../pages/MyInfractionsPage.tsx` |
| **Gating por `uploads:photo_create`** nos dois formulários, com aviso somente-leitura no ramo negado | `.../components/AttachmentUploader.tsx` (novo) |
| Exibição das evidências no detalhe (hoje uma lista de links crus) | `.../components/InfractionDetailsView.tsx` |
| Exibição dos anexos da contestação no histórico (hoje **não renderizados**) | `.../components/InfractionStageTimeline.tsx` |
| `EntityType` do cliente ganha `'INFRACTION'` — o backend já tem, o TS não | `frontend/src/types/media_asset.ts` |
| Os limites do endpoint expostos como constantes exportadas, metade frontend de um pino de duas pontas | `frontend/src/api/uploads.ts` |
| Rótulos pt/en dos itens acima, incluindo o aviso do ramo negado | `frontend/src/i18n/locales/{pt,en}.json` |
| **O gêmeo backend do pino de duas pontas** (§3.6(c)): um caso pytest que afirma `MAX_FILE_SIZE`, `ALLOWED_MIME_TYPES`, `EntityType.INFRACTION`, o mapeamento de `ROUTE_PERMISSIONS` e — pós-51 — a guarda na assinatura de `upload_photo`, falhando com o nome do arquivo frontend na mensagem | `backend/tests/test_uploads.py` |
| Nota **só de documentação** na tabela de bundle recomendado: um papel de morador que contesta precisa de `uploads:photo_create` | `AGENTS.md` |

**Não cobre — e a razão, em cada caso:**

* **Nenhuma rota, schema, serviço, model ou migração no backend.** ER-3 é
  explícita e nada disso é necessário: `POST /api/v1/uploads/photo` existe (e é
  a APRAS-51, não esta task, que muda a guarda dele),
  `evidence_urls`/`attachment_urls` existem e são `list[str]` com
  `default_factory=list`, e `EntityType.INFRACTION` já foi adicionado pela
  APRAS-44 (`backend/app/models/enums.py:131`) exatamente para isto. O diff
  desta task em **`backend/app/` e `backend/alembic/` é vazio** — é essa a
  fronteira que ER-3 pede, e ela é verificável por um comando.
  **A única exceção, deliberada, é `backend/tests/`:** o gêmeo de §3.6(c), um
  caso pytest e nada mais. Ele existe porque o repositório já decidiu como se
  fixa um contrato que cruza a fronteira de linguagem — cada lado declara a
  constante e nomeia o outro (`lotSelectContract.test.tsx` ↔
  `test_infractions.py::test_the_lots_route_ceiling_matches_the_lot_selects_limit`;
  `test_module_vocabulary.py:83-133` ↔ `i18n/__tests__/index.test.ts`) — e um
  teste que não muda nada de produção não é "mudança de backend" no sentido que
  ER-3 protege. A edição em `AGENTS.md` é de documentação e não está sob
  `backend/`.
* **Nenhum hook novo.** O padrão de upload já tem hook — `useUploadPhoto`
  (`features/media-management/hooks/useMediaAssets.ts`) — e o de permissão
  também: `usePermissionSet()`
  (`features/user-administration/access/useCanAccess.ts`). Reusam-se ambos.
  Criar um segundo seria um segundo cache key para o mesmo estado de servidor, e
  a APRAS-44 já pagou esse preço uma vez (round 2, `useSelectableLots`).
* **Anexos no modo *promote*** de `NewInfractionModal`. `InfractionPromote`
  (`backend/app/schemas/infraction.py:195`) **não tem** `evidence_urls`; a rota
  descartaria o campo em silêncio. O controle fica escondido em modo promote,
  com o mesmo raciocínio da APRAS-44 §7.4: o formulário nunca manda o que a
  rota não aceita.
* **Anexos em `NextStepPanel`** (`InfractionStageCreate.evidence_urls`). É um
  terceiro formulário, com sua própria ER na APRAS-44, e não está nas quatro ERs
  desta task.
* **PDF.** O endpoint aceita **só imagem** (§2.2), e a v1 aceita isso — §5.
* **Aprovação/moderação** dos assets criados: o fluxo `uploads:approve` /
  `uploads:reject` / fila de pendentes já existe em `media-management` e não é
  tocado.
* **Excluir o arquivo do storage** ao remover um chip do formulário. Remover um
  anexo antes de submeter tira a URL da lista; o `MediaAsset` já criado
  permanece, órfão, exatamente como no `PhotoUploadModal` de hoje.
  `DELETE /uploads/photos/{id}` exige `uploads:delete`, que o morador que
  contesta pode não ter — chamá-lo produziria um 403 no caminho feliz.

---

## 2. O que já existe, medido (não presumido)

### 2.1 O endpoint reusado

`POST /api/v1/uploads/photo` — `backend/app/api/v1/endpoints/uploads.py:16`.

```
file:        UploadFile = File(...)          multipart
entity_type: EntityType = Form(...)          obrigatório, enum
entity_id:   Optional[UUID] = Form(None)     opcional
→ 201 MediaAssetRead   (campos usados aqui: url, thumbnail_url, status, id)
```

Cliente já existente e já testado: `frontend/src/api/uploads.ts::uploadPhoto`,
que monta o `FormData` com exatamente esses três campos e o header
`Content-Type: multipart/form-data`. **É este par (rota + cliente) que a task
reusa. Nada além dele.** A APRAS-51 não muda assinatura, corpo, status de
sucesso nem `response_model` — muda **só a guarda** (§2.3), então o cliente
segue byte-idêntico e não há nada a versionar aqui.

### 2.2 Os limites, na fonte

`backend/app/services/media_service.py:25-26`:

```python
MAX_FILE_SIZE = 5 * 1024 * 1024                                   # 5 MiB
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
```

Violá-los produz, via `domain_exception_handler`
(`backend/app/core/exception_handlers.py:221-241`), **HTTP 400** com
`{"detail": "<frase>"}`:

| Erro | Status | `detail` |
|---|:-:|---|
| `PhotoFileTooLargeError` | 400 | `"Arquivo excede o limite máximo permitido de 5MB."` |
| `InvalidPhotoFormatError` | 400 | `"Formato de imagem inválido. Formatos aceitos: JPEG, PNG, WebP."` |

Há ainda uma terceira porta: Pillow abre os bytes, então um `.png` corrompido
com MIME correto também cai em `InvalidPhotoFormatError` → 400. Um pré-check de
cliente **não** cobre esse caso, o que é precisamente por que a UI tem de
mostrar a recusa do servidor e não apenas se antecipar a ela.

Nenhuma das duas validações muda de ordem ou de forma com a APRAS-51: elas
rodam *dentro* do handler, e a guarda nova roda *antes* dele. Para um portador
de `uploads:photo_create`, o comportamento é o de hoje, sem delta.

### 2.3 A permissão — o antes e o depois, declarados

Esta é a seção que a revisão pré-review existe para consertar. Há **dois**
estados, e a task se implementa contra o segundo.

**O que é verdade em `e188866` (commit da APRAS-44) e ainda no `master` de
hoje:**

| Camada | O que diz |
|---|---|
| **Runtime**, `uploads.py:16-22` | `current_user: User = Depends(get_current_active_user)` e mais nada. **Nenhum `require_permission`.** Qualquer usuário autenticado do tenant ativo sobe arquivo. |
| **Registro**, `backend/app/core/permissions.py:575` | `("POST", "/api/v1/uploads/photo"): "uploads:photo_create"` |
| **Enforcement de rota**, `backend/tests/test_permission_enforcement.py:371` | `require_permission` está nas *"APRAS-43 seven plus billing"* (+ as 18 de infrações). `uploads` **não** está entre elas. |

Ou seja, hoje `ROUTE_PERMISSIONS` é para esta rota **catálogo** (matriz de
paridade, gating de UI) e não guarda de runtime.

**O que a APRAS-51 torna verdade, e que é a precondição desta task:**

A APRAS-51 (`docs/tasks/APRAS-51-spec.md` §3, tabela das 25 rotas, linha
`uploads | POST /api/v1/uploads/photo | uploads:photo_create | c`; §4.1, o
parágrafo "The three `uploads` routes are spelled the older way") converte o
handler para

```python
current_user: User = Depends(require_permission("uploads:photo_create"))
```

Consequências que esta task herda, todas afirmadas na APRAS-51 §4.1 e §4.4:

1. **A rota passa a exigir `uploads:photo_create`.** Ela **não** está na lista
   `SERVICE_ENFORCED` da APRAS-51 §4.4 (essa lista tem cinco rotas: os dois
   `POST /votes/{vote_id}/ballots*` e as três de `packages`); está entre as 25
   que ganham a forma `Depends`.
2. **A recusa é 403 com corpo fixo.** `PermissionRequired.__call__`
   (`backend/app/api/deps.py:583-595`) levanta
   `HTTPException(403, detail="The user doesn't have enough privileges")`. A
   APRAS-51 §4.2 registra que esta rota **não** precisa de entrada em
   `REFUSAL_SHAPES` justamente porque a guarda passa a resolver na árvore de
   dependências, antes do handler — o 400 de formato que a varredura via em
   `e188866` vira 403.
3. **Nada é semeado (doutrina pós-F5).** Um papel RESIDENT só detém
   `uploads:photo_create` se um operador conceder. Portanto a UI **não pode**
   presumir que o morador que contesta o tenha.

**Decisão desta task, revisada (era a decisão oposta antes desta revisão):** o
controle de anexos **é gateado no cliente por `uploads:photo_create`**. Quando
a permissão está ausente do conjunto efetivo, o formulário renderiza um aviso
somente-leitura em vez do controle — nunca um upload que quebraria com 403 no
meio de uma defesa com prazo correndo. A decisão anterior ("espelhar o runtime,
que é só autenticação") era correta contra `e188866` e passa a estar errada no
instante em que a APRAS-51 entra; como a APRAS-51 entra **antes**, ela nunca
chega a estar certa na árvore em que esta task é implementada.

**Qual conjunto é lido, exatamente.** `usePermissionSet()`
(`features/user-administration/access/useCanAccess.ts:60`), que é o wrapper de
`useMyPermissions()` → `GET /permissions/me` — o conjunto **efetivo** que o
backend computa (já stripado por módulos desativados). Deliberadamente **não**
`useEffectivePermissionSet()`, o irmão que reflete a simulação "view-as": o
upload é feito com o token real, então uma simulação de morador que mostrasse o
controle produziria exatamente o 403 que este gating existe para evitar, e uma
simulação de administrador que o escondesse mentiria sobre o que o usuário real
pode fazer. É a mesma repartição já documentada naquele arquivo — autorização
lê o conjunto real, exibição lê o simulado — e anexar arquivo é autorização.

**Enquanto o `/permissions/me` carrega** (`isLoading`), o controle não é
renderizado e o aviso também não: mostra-se o placeholder de carregamento
(`data-testid="attachment-gate-loading"`). Falha fechada, como
`useCanAccess` — nunca um controle que aparece e some.

Duas obrigações continuam valendo, sem mudança:

1. **A recusa do servidor é renderizada onde o usuário está.** O gating é
   conveniência de UI, nunca garantia: uma permissão revogada entre o load e o
   clique produz o 403, e ele aparece inline no mesmo lugar que o 400 de
   tamanho/formato — nenhum caso especial no código, é o mesmo `parseApiError`.
2. **O gating de rota permanece intocado no resto do módulo.**
   `ROUTE_ACCESS` / `NAV_ITEMS` de `/infractions`, `/infraction-rules` e
   `/my-infractions`, e as 13 permissões `infractions:*`, não recebem uma
   linha. `uploads:photo_create` gateia **um controle dentro de dois
   formulários**, não uma rota e não um item de menu.

### 2.4 A forma da URL

`LocalStorageProvider.save_file` devolve `"/static/uploads/{ano}/{mês}/{uuid}{ext}"`
— caminho relativo, servido pelo `app.mount("/static/uploads", …)` do backend.
Todo o resto do sistema (mídia de comunicados, nota fiscal do financeiro,
`media-management`) renderiza essa string **crua**, e esta task faz o mesmo. Não
inventa prefixo, não resolve origem: divergir aqui criaria um segundo padrão
para o mesmo dado.

---

## 3. Approach

### 3.1 `frontend/src/types/media_asset.ts` — a união que falta

```ts
export type EntityType =
  | 'RESIDENT' | 'VISITOR' | 'EMPLOYEE' | 'LOT'
  | 'ANNOUNCEMENT' | 'OCCURRENCE'
  | 'INFRACTION';   // já existe em app/models/enums.py:131 (APRAS-44 §4.4)
```

Sem isso, `uploadPhoto(file, 'INFRACTION')` não compila. Com um valor fora do
enum do servidor, seria um **422 do FastAPI antes do handler** — a mesma classe
de defeito que a APRAS-44 CR3 (`limit: 200` contra `le=100`). Por isso o membro
é fixado dos dois lados: §3.6(b) declara a string no frontend e §3.6(c) afirma,
no backend, que `EntityType.INFRACTION` existe e vale exatamente `"INFRACTION"`.

### 3.2 `frontend/src/api/uploads.ts` — os limites e a permissão, exportados

```ts
/** O valor de `media_service.MAX_FILE_SIZE`, declarado deste lado da fronteira.
 *  Metade de um pino de duas pontas: a outra é
 *  `backend/tests/test_uploads.py::test_the_upload_contract_matches_the_infraction_uploader`. */
export const UPLOAD_MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024;

/** O conjunto de `media_service.ALLOWED_MIME_TYPES`. Mesmo pino. */
export const UPLOAD_ALLOWED_MIME_TYPES = [
  "image/jpeg", "image/png", "image/webp",
] as const;

/** O `accept=` do `<input type="file">`, derivado — nunca redigitado. */
export const UPLOAD_ACCEPT = UPLOAD_ALLOWED_MIME_TYPES.join(",");

/** A permissão que `POST /uploads/photo` exige a partir da APRAS-51
 *  (`core/permissions.py:575` ↔ `require_permission` em `uploads.py`).
 *  Mesmo pino: o gêmeo backend afirma o mapeamento e a guarda. */
export const UPLOAD_PHOTO_PERMISSION = "uploads:photo_create";
```

Constantes exportadas, e não literais espalhados, pelo mesmo motivo que
`LOT_SELECT_LIMIT` é exportado: um número — ou uma string — que é contrato com
uma rota precisa ser afirmável por um teste, não pela memória de quem lê.
`PhotoUploadModal.tsx:36` tem hoje `5 * 1024 * 1024` inline; **fica como está**
(refatorá-lo esconderia esta mudança num diff alheio) — mas as constantes ficam
disponíveis para quando alguém o tocar.

### 3.3 `components/AttachmentUploader.tsx` — o controle, um só, com dois ramos

Um componente, usado pelos dois formulários, porque eles diferem em nada além
do rótulo e do `entityId`.

```tsx
/** Ambos os formulários anexam a uma infração; o vocabulário é este. */
export const INFRACTION_ENTITY_TYPE = "INFRACTION" as const;

export const AttachmentUploader: React.FC<{
  /** URLs já subidas — estado controlado pelo formulário pai. */
  value: string[];
  onChange: (urls: string[]) => void;
  /** Ausente na criação (a infração ainda não existe); o id na contestação. */
  entityId?: string;
  /** Rótulo i18n já resolvido pelo pai (evidências × anexos). */
  label: string;
  disabled?: boolean;
}>
```

**Ramo 0 — o gate (§2.3).** Antes de qualquer outra coisa:

```tsx
const { has, isLoading } = usePermissionSet();
if (isLoading) return <p data-testid="attachment-gate-loading">…</p>;
if (!has(UPLOAD_PHOTO_PERMISSION))
  return (
    <p className="text-sm text-gray-500" data-testid="attachment-unavailable">
      {t("infractions.attachments.permissionRequired")}
    </p>
  );
```

O ramo negado é **texto e nada mais**: nenhum `<input type="file">`, nenhum
botão, nada desabilitado-mas-presente. Um controle desabilitado convida o
usuário a procurar como habilitá-lo; uma frase diz o que é verdade. O
formulário em volta continua submetível — a contestação sem anexo é uma
contestação válida (`attachment_urls` tem `default_factory=list`), e bloquear o
submit transformaria uma permissão de anexo em uma permissão de contestar.

**Ramo 1 — o controle**, quando a permissão está presente:

1. `<input type="file" multiple accept={UPLOAD_ACCEPT}>`, rotulado por
   `aria-label={label}`, `data-testid="attachment-file-input"`.
2. Para cada arquivo escolhido, **pré-check de cliente** antes de qualquer
   requisição: MIME fora de `UPLOAD_ALLOWED_MIME_TYPES` →
   `infractions.attachments.unsupportedType`; `size > UPLOAD_MAX_FILE_SIZE_BYTES`
   → `infractions.attachments.tooLarge`. O arquivo é rejeitado localmente, os
   demais seguem. (Um pré-check é conveniência, nunca garantia: o servidor
   valida de novo, e o binário corrompido de §2.2 só ele pega.)
3. Os aprovados sobem **sequencialmente** via `useUploadPhoto().mutateAsync({ file, entityType: INFRACTION_ENTITY_TYPE, entityId })`.
   Sequencial e não `Promise.all`: dá ordem determinística à lista resultante e
   torna o teste legível sem `act` aninhado.
4. Enquanto sobe: `data-testid="attachment-uploading"` com
   `infractions.attachments.uploading` e o `<input>`/botão desabilitados.
5. Sucesso → `onChange([...value, asset.url])`.
6. Falha → a frase do servidor via `parseApiError(err, t, { validationError:
   "infractions.errors.validation", genericError: "infractions.errors.generic" })`,
   renderizada em `data-testid="attachment-error"` com `role="alert"`. É o
   helper que o módulo já usa (`InfractionsPage.tsx:96`), então 400, 403, 413 e
   422 saem todos pela mesma porta, sem `if` por status — inclusive o 403 de
   §2.3 quando a permissão é revogada entre o load e o clique.
7. Cada URL vira um chip (`data-testid="attachment-chip"`): miniatura
   `<img src={url}>`, link para a URL, e botão remover
   (`data-testid="attachment-remove"`) que só edita o array (§1, out of scope).
8. Nota: sem `uploads:auto_approve`, o `MediaAsset` nasce
   `PENDING_APPROVAL` — a `url` já é válida e servida, então **nada é gateado
   por `status` aqui** (§5).

**Nenhum hook novo é criado.** `AttachmentUploader` é o *production caller* de
`useUploadPhoto` (lição APRAS-44: nada de hook sem chamador em produção), e o
único artefato novo desta task além dos testes.

### 3.4 Os dois formulários

**`NewInfractionModal.tsx`** — modo *create* apenas:

* `const [evidenceUrls, setEvidenceUrls] = useState<string[]>([])`;
* `{!isPromotion && <AttachmentUploader value={evidenceUrls} onChange={setEvidenceUrls} label={t("infractions.attachments.evidenceLabel")} disabled={isSubmitting} />}`
  — posicionado depois da descrição, antes do bloco de erro. O gate de §3.3
  fica **dentro** do `AttachmentUploader`, não replicado aqui: um só lugar
  decide, e os dois formulários não podem divergir;
* `onSubmit({ …os cinco campos de hoje…, evidence_urls: evidenceUrls })`.
  `canSubmit` **não** muda: evidência é opcional na rota
  (`default_factory=list`) e continuar exigindo-a inventaria uma regra — e, com
  o gate, transformaria `uploads:photo_create` em pré-requisito de
  `infractions:create`.
* O corpo de *promote* segue byte-idêntico ao de hoje.

**`ContestationForm.tsx`** — a assinatura de `onSubmit` ganha o segundo
argumento:

```tsx
onSubmit: (body: string, attachmentUrls: string[]) => void;
```

* uploader entre o `<textarea>` e o botão, rotulado
  `infractions.attachments.label`, com `entityId={infractionId}` — a infração
  **existe** aqui, então o `MediaAsset` fica ligado a ela pelo campo que a rota
  oferece para isso;
* nova prop obrigatória `infractionId: string`, passada por
  `MyInfractionsPage`;
* `submit-contestation` continua habilitado por `body.trim()` só. Um morador
  com `infractions:contest` e sem `uploads:photo_create` vê o aviso de §3.3 e
  **contesta mesmo assim**, por texto;
* o ramo "prazo fechado" (`data-testid="contestation-unavailable"`) é
  intocado e tem precedência: sem prazo aberto não há formulário, logo não há
  gate de anexo a avaliar.

**`MyInfractionsPage.tsx`**:

```tsx
<ContestationForm
  infractionId={infraction.id}
  defenseDueOn={infraction.defense_due_on}
  isSubmitting={contest.isPending}
  onSubmit={(body, attachmentUrls) =>
    contest.mutate({ id: infraction.id, data: { body, attachment_urls: attachmentUrls } })
  }
/>
```

### 3.5 As duas superfícies de leitura

**`InfractionDetailsView.tsx`** — `evidence_urls` já é renderizado como lista de
links crus (`data-testid="evidence-list"`). O testid e o `<a href={url}>`
**permanecem** (são o contrato dos testes existentes); cada `<li>` passa a
conter também `<img src={url} alt={t("infractions.attachments.imageAlt", { index })}>`.
Tudo o que a rota aceita é imagem, então a miniatura nunca é um link quebrado
por tipo. **Leitura não é gateada por `uploads:photo_create`**: quem pode ver a
infração pode ver a prova dela, e a permissão de criar não governa exibição.

**`InfractionStageTimeline.tsx`** — `entry.attachment_urls` existe no tipo
(`types/infraction.ts:110`) e **não é renderizado por linha nenhuma hoje**.
Passa a: quando `entry.attachment_urls.length > 0`, um bloco
`data-testid="timeline-attachments"` com o título
`infractions.attachments.timelineTitle` e a mesma dupla miniatura+link. Vale
para os dois `kind` — uma etapa também pode carregar evidência —, e o
componente segue **read-only**: nenhum controle de editar ou excluir aparece
(ER-3 da APRAS-44), e nenhum gate de permissão, pelo mesmo motivo do parágrafo
anterior.

### 3.6 Testes

Regras que a APRAS-44 deixou e que valem aqui: **nenhum hook sem chamador de
produção**, **nenhum teste que passe sem medir**, **nenhuma dependência de
fuso**. Datas de teste continuam relativas a `Date.now()`, como
`MyInfractions.test.tsx:11-16` já faz.

Uma quarta regra, do repositório e não da APRAS-44, decidida nesta revisão:
**nenhum arquivo sob `frontend/src/` importa um builtin do Node** (`node:fs`,
`node:url`, `node:path`, `process`, `Buffer`). Nenhum importa hoje, e
`tsconfig.app.json` está escrito para que continue assim (§3.6(b)). Um contrato
que cruza a fronteira de linguagem se fixa com um pino de duas pontas — §3.6(b)
declara a ponta frontend, §3.6(c) escreve a ponta backend.

#### (a) As personas

Duas, e nenhuma delas construída por `permissionsOf("RESIDENT")` sozinho — o
bundle legado daquele fixture **já contém** `uploads:photo_create`
(`src/test/permissionFixtures.ts`, bloco `"RESIDENT"`), então ele não consegue
expressar o ramo negado. As duas são listas explícitas, via o padrão que
`features/assembly-voting/__tests__/VotingRouteAccess.test.tsx:19-43` já usa
(`vi.mock("../../../hooks/usePermissionQueries")` +
`vi.mocked(useMyPermissions).mockReturnValue(settledPermissions([...]) as never)`):

| Persona | Conjunto | Ramo esperado |
|---|---|---|
| morador que contesta **com** anexo | `["infractions:contest", "infractions:my_lots_read", "uploads:photo_create"]` | controle presente |
| morador que contesta **sem** anexo | `["infractions:contest", "infractions:my_lots_read"]` | `attachment-unavailable` |
| staff que registra infração | `["infractions:create", "infractions:read", "uploads:photo_create"]` | controle presente |

A primeira é a persona nomeada pela ER-2: `infractions:contest` **e**
`uploads:photo_create` juntos, que é exatamente a combinação que a nota de
AGENTS.md (§3.8) passa a recomendar.

#### (b) `__tests__/uploadContract.test.tsx` — o teste de contrato

Um por chamada nova de cliente, e **sem mockar a API por atacado**. Mocka
**apenas** `api/client` (a instância axios, última camada antes da rede) e
`hooks/usePermissionQueries` (a persona) — o módulo real `api/uploads` roda.
Mesma forma de `lotSelectContract.test.tsx`, **e a mesma forma também na
metade 2**: aquele arquivo é o precedente das duas metades, não só da primeira.

O arquivo envolve tudo num `QueryClientProvider`
(`new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })`)
e num `MemoryRouter`, como `lotSelectContract.test.tsx:46-59`:
`AttachmentUploader` chama `useUploadPhoto()`, que é um `useMutation`, e sem
provider o render lança.

**Pré-requisitos de fixture para chegar ao submit** (o precedente não os
carrega, porque `lotSelectContract.test.tsx` nunca submete). `canSubmit` do
`NewInfractionModal` é `ruleId && residentId && occurredOn &&
description.trim() && lotId`, então os casos de submit precisam de: a prop
`rules` **não vazia** (uma regra basta), e stubs de `apiClient.get` para
**`/lots/`** (`{ items: [{ id, block, lot_number }], total: 1, skip: 0, limit }`)
e para **`/lots/{id}/residents`** (um morador), além do preenchimento de data e
descrição. Sem os dois `get`, o `<select>` de lote e o de morador ficam vazios,
`canSubmit` nunca fica verdadeiro e o caso mediria a ausência do botão em vez
do corpo submetido.

Metade 1 — *o que vai para o fio*, renderizando os componentes reais:

| Caso | Persona | Asserção |
|---|---|---|
| `NewInfractionModal` (create) sobe evidência | staff | `apiClient.post` chamado com `"/uploads/photo"`, corpo `FormData`, `body.get("entity_type") === "INFRACTION"`, **`body.has("entity_id") === false`** (a infração não existe, e `uploadPhoto` só faz `append` `if (entityId)`; afirmar `get("entity_id") === null` passaria por coincidência da API do DOM — chave ausente também devolve `null` — e não por construção), config `{ headers: { "Content-Type": "multipart/form-data" } }` |
| ...e o submit leva a URL | staff | `onSubmit` recebe `evidence_urls: ["/static/uploads/…"]` — a `url` devolvida pelo mock do 201 |
| `ContestationForm` sobe anexo | morador **com** | mesmo POST, mas `body.get("entity_id") === "<infractionId>"` — aqui a chave **está** presente |
| ...e o submit leva a URL | morador **com** | `onSubmit` recebe `(body, ["/static/uploads/…"])` |
| **ramo negado, criação** | staff sem `uploads:photo_create` | `queryByTestId("attachment-file-input") === null`, `attachment-unavailable` presente com a frase pt, e **zero** chamadas a `apiClient.post` para `/uploads/photo` |
| **ramo negado, contestação** | morador **sem** | idem, **e** `submit-contestation` ainda habilitado e capaz de submeter `(body, [])` — a defesa por texto não é bloqueada |
| gate carregando | `isPending: true` | `attachment-gate-loading` presente, os outros dois testids ausentes |
| modo *promote* | staff **com** | **nenhum** controle de anexo no DOM, mesmo com a permissão |

Os dois ramos ("com" e "sem") vivem no mesmo arquivo de propósito: é a
asserção de que uma única condição decide os dois, e um regression que remova o
gate faz falhar a linha "ramo negado" em vez de passar silenciosamente.

Metade 2 — *o contrato com o servidor, na forma que o repositório já usa*.
**Nada é lido do disco, e nenhum builtin do Node aparece em `frontend/src/`.**
`tsconfig.app.json` faz `"include": ["src"]` com `"types": ["vite/client"]` e
sem `exclude`, então `tsc -b` (a primeira metade de `npm run build`) type-checka
os arquivos de teste com os tipos do Node **deliberadamente fora** do programa —
`"types": ["node"]` vive só em `tsconfig.node.json`, confinado a
`vite.config.ts`. Hoje nenhum arquivo sob `src/` importa `node:fs`, `node:url`,
`process` ou `Buffer`; esta task não é a que abre essa porta, porque abri-la
significaria expor os globais do Node a **todo** arquivo de produção só para
alimentar um teste.

O que substitui a leitura de disco é a convenção que o repositório já escolheu
e documentou, no docblock do próprio arquivo que esta seção toma como modelo:

> **This is one half of a two-sided pin** … neither side can import the other
> across the language boundary, so each states the constant and names the other.
> — `lotSelectContract.test.tsx:25-32`

Duas instâncias já existentes dessa forma: `lotSelectContract.test.tsx` ↔
`backend/tests/test_infractions.py::test_the_lots_route_ceiling_matches_the_lot_selects_limit`,
e `frontend/src/i18n/__tests__/index.test.ts` ↔
`backend/tests/test_module_vocabulary.py:83-133`. Esta é a terceira, escrita
igual às duas.

Portanto, **deste lado**, as constantes são declaradas como literais locais e
comparadas com o que o cliente exporta — e cada mensagem de falha nomeia o
gêmeo:

| Constante local do teste | Asserção | Mensagem de falha nomeia |
|---|---|---|
| `DOCUMENTED_MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024` | `=== UPLOAD_MAX_FILE_SIZE_BYTES` | `backend/app/services/media_service.py` e o gêmeo em `backend/tests/test_uploads.py` |
| `DOCUMENTED_MIME_TYPES = ["image/jpeg", "image/png", "image/webp"]` | `new Set(...)` `===` `new Set(UPLOAD_ALLOWED_MIME_TYPES)` | idem |
| `DOCUMENTED_ENTITY_TYPE = "INFRACTION"` | `=== INFRACTION_ENTITY_TYPE` | `backend/app/models/enums.py` e o gêmeo |
| `DOCUMENTED_UPLOAD_ROUTE = "/uploads/photo"` | é o path que a metade 1 viu em `apiClient.post` | `backend/app/api/v1/endpoints/uploads.py` e o gêmeo |
| `DOCUMENTED_UPLOAD_PERMISSION = "uploads:photo_create"` | `=== UPLOAD_PHOTO_PERMISSION`, e é a string que o gate de §3.3 consulta | `backend/app/core/permissions.py`, a APRAS-51, e o gêmeo |

Um literal comparado com a constante exportada não é tautologia: a constante
exportada é o que a **produção** usa (o `accept=`, o pré-check de tamanho, o
argumento de `has()`), e o literal é o que este arquivo declara como sendo a
verdade do servidor. Quem mudar a constante de produção sem mudar o servidor
faz falhar aqui; quem mudar o servidor sem mudar nenhum dos dois faz falhar no
gêmeo. É exatamente o par que `DOCUMENTED_ROUTE_CEILING = 100`
(`lotSelectContract.test.tsx:44`) forma com o `assert declared == 100` de
`test_infractions.py:1235`.

O docblock do arquivo declara isso em uma frase, como o precedente faz, e nomeia
`backend/tests/test_uploads.py::test_the_upload_contract_matches_the_infraction_uploader`.

#### (c) O gêmeo backend — `backend/tests/test_uploads.py`

**Um** caso pytest novo, `test_the_upload_contract_matches_the_infraction_uploader`,
acrescentado ao arquivo que já cobre esta rota. Nenhum arquivo de produção do
backend é tocado (§1). O caso lê os **objetos vivos**, não texto de arquivo —
seguindo `test_infractions.py:1213` ("this half reads the **live route object**
rather than the source text, so it follows a refactor of the signature") — e
afirma cinco coisas:

| Lê | Afirma |
|---|---|
| `app.services.media_service.MAX_FILE_SIZE` | `== 5 * 1024 * 1024` |
| `app.services.media_service.ALLOWED_MIME_TYPES` | `== {"image/jpeg", "image/png", "image/webp"}` |
| `app.models.enums.EntityType.INFRACTION` | existe e `.value == "INFRACTION"` |
| `app.core.permissions.ROUTE_PERMISSIONS[("POST", "/api/v1/uploads/photo")]` | `== "uploads:photo_create"` |
| a rota viva `POST /api/v1/uploads/photo` de `app.main.app` | **a assinatura do handler carrega a guarda**: percorrendo `route.dependant` recursivamente, existe um `deps.PermissionRequired` com `.permission == "uploads:photo_create"` |

A quinta linha é a **asserção da precondição**. Ela lê o objeto de rota, e não
uma fatia de texto de `endpoints/uploads.py`, por dois motivos:
`require_permission` aparece na **assinatura** de `upload_photo`, não no corpo;
e `endpoints/uploads.py` hospeda
outras cinco rotas, de modo que um `includes()` no arquivo inteiro passaria se a
string caísse numa rota de moderação. Percorrer o `dependant` da rota chaveada
por `("POST", "/api/v1/uploads/photo")` mede a assinatura **daquele** handler e
de nenhum outro. O walk é local ao arquivo (três linhas recursivas, como
`_permission_guards` em `test_permission_enforcement.py:281-287`), não um import
entre arquivos de teste.

**Este caso é vermelho enquanto a APRAS-51 não tiver entrado**, porque hoje o
handler depende de `get_current_active_user` (`uploads.py:21`). Isso é o
comportamento pretendido, não um defeito do plano: é a precondição de §2.3
falhando ruidosamente, com a APRAS-51 nomeada na mensagem, em vez de o gate de
UI virar uma restrição sem causa (§6, risco 1). A task só é implementável — e o
gate de §7 só fica verde — sobre a árvore pós-51, que é o que `blockedBy` já
declara.

A mensagem de falha nomeia, em todos os cinco casos,
`frontend/src/api/uploads.ts`, `frontend/src/features/infraction-management/__tests__/uploadContract.test.tsx`
e o que fazer.

#### (d) `__tests__/AttachmentUploader.test.tsx` — o fluxo, com a API mockada

`vi.mock("../../../api/uploads")` para o cliente e a persona "com permissão"
como padrão do `beforeEach`, como a ER-1 descreve. Aqui também o render é
envolvido num `QueryClientProvider` — `useUploadPhoto()` é um `useMutation` e
não existe fora de um `QueryClient`; sem o provider **todos** os casos abaixo
falham no render, e não na asserção. Casos:

* dois arquivos escolhidos → duas chamadas a `uploadPhoto`, duas miniaturas,
  `onChange` com as duas URLs **na ordem escolhida**;
* arquivo de 6 MiB → **nenhuma** chamada a `uploadPhoto` e
  `attachment-error` com o texto de `tooLarge` (medido: contar
  `vi.mocked(uploadPhoto).mock.calls.length === 0`, não só olhar o DOM);
* `application/pdf` → nenhuma chamada, texto de `unsupportedType`;
* `uploadPhoto` rejeita com `{ response: { data: { detail: "Arquivo excede o
  limite máximo permitido de 5MB." } } }` → **essa frase** aparece em
  `attachment-error` (ER-3: o limite vem do endpoint e a UI mostra o erro);
* rejeição com `{ response: { status: 403, data: { detail: "The user doesn't
  have enough privileges" } } }` — a forma exata de `PermissionRequired`
  (`deps.py:590-593`) — → a frase aparece, e nenhum chip é criado (§2.3,
  obrigação 1: permissão revogada entre o load e o clique);
* persona **sem** a permissão → `attachment-unavailable`, nenhum
  `attachment-file-input`, zero chamadas a `uploadPhoto`;
* remover um chip → `onChange` sem aquela URL, e **nenhuma** chamada a
  `deletePhoto`;
* `disabled` → input desabilitado.

#### (e) Edições nos testes existentes

* `NewInfractionModal.test.tsx`: o caso "submits the five create fields" passa
  a afirmar `evidence_urls: []` quando nada foi anexado (a rota recebe a chave,
  e é isso que o backend documenta como default) e um caso novo com uma URL. O
  `beforeEach` do arquivo passa a mockar `usePermissionQueries` com a persona
  staff (do contrário o gate esconde o controle e os casos novos mediriam a
  ausência dele por acidente).
* `MyInfractions.test.tsx`: `addContestation` passa a ser afirmado com
  `{ body, attachment_urls: [...] }`; `beforeEach` mocka a persona "morador com
  anexo"; um caso novo renderiza um `timeline` com `attachment_urls` não-vazio
  numa entrada `CONTESTATION` e espera `timeline-attachments`.

#### (f) i18n

`i18n/__tests__/parity.test.ts` já falha em chave presente num locale e ausente
no outro, e em valor vazio. As chaves novas vivem em `infractions.attachments.*`
— **fora** de `permissions.modules.*` / `permissions.actions.*` —, então as
contagens fixadas de 27 e 94 daquele arquivo **não mudam** e não devem ser
tocadas.

### 3.7 Chaves i18n (pt e en, mesmas chaves)

Sob `infractions.attachments`: `label`, `evidenceLabel`, `add`, `hint`,
`uploading`, `remove`, `none`, `tooLarge`, `unsupportedType`, `imageAlt`,
`timelineTitle`, `permissionRequired`, `loading`. Interpolações: `tooLarge` usa
`{{name}}`/`{{size}}`/`{{limit}}`, `unsupportedType` usa `{{name}}`,
`uploading` usa `{{name}}`, `imageAlt` usa `{{index}}`, e **`hint` usa
`{{types}}`/`{{limit}}`** — as duas variáveis sem as quais um implementador
poderia digitar "JPEG, PNG ou WebP, até 5 MB" direto na string e não falhar em
nada. `hint` é, portanto:

| Locale | Valor |
|---|---|
| `pt` | `"{{types}}, até {{limit}} por arquivo."` |
| `en` | `"{{types}}, up to {{limit}} per file."` |

`types` vem de `UPLOAD_ALLOWED_MIME_TYPES` (os três MIME reduzidos a rótulos —
`image/jpeg → JPEG` etc. — e unidos por vírgula) e `limit` de
`UPLOAD_MAX_FILE_SIZE_BYTES` formatado em MB, ambos calculados no componente a
partir das constantes de §3.2. Se o servidor passar a aceitar 10 MiB e a
constante acompanhar, a frase acompanha sem edição de locale; um número
redigitado na string não acompanharia, e é essa a razão da interpolação.

`permissionRequired` é a frase do ramo negado de §3.3:

| Locale | Valor |
|---|---|
| `pt` | `"Anexos indisponíveis para o seu perfil."` |
| `en` | `"Attachments are unavailable for your profile."` |

Sem menção à string de permissão: `uploads:photo_create` é vocabulário de
operador, não de morador, e a tabela de bundle recomendado (§3.8) é onde o
operador a encontra.

### 3.8 `AGENTS.md` — a nota de bundle recomendado (só documentação)

Na tabela **"Recommended permission bundle"** da seção de infrações
(`AGENTS.md`, o bloco com as 13 linhas `infractions:*`), acrescentar **uma
linha** e **uma frase**:

| Permission | ADMINISTRATOR | DIRECTOR | MANAGER | RESIDENT | PORTEIRO | GUEST |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| `uploads:photo_create` | ✓ | ✓ | ✓ | ✓ | | |

e, logo abaixo da tabela, a frase que explica por que uma permissão de outro
módulo aparece nela:

> `uploads:photo_create` não é do módulo `infractions`, mas entra no bundle
> porque a partir da APRAS-51 `POST /api/v1/uploads/photo` a exige: um papel
> que contesta (`infractions:contest`) sem ela consegue escrever a defesa e não
> consegue anexar prova — o cliente mostra o aviso de
> `infractions.attachments.permissionRequired` em vez de um upload que tomaria
> 403. Um papel que registra infração (`infractions:create`) precisa dela pelo
> mesmo motivo, para a evidência.
>
> **Os ✓ desta linha são o recorte do fluxo de infrações, não uma recomendação
> de catálogo.** Só marcam os papéis que esta tabela já lista como registrando
> ou contestando infração; PORTEIRO fica em branco **aqui** porque nenhuma das
> 13 linhas `infractions:*` acima lhe dá `infractions:create` nem
> `infractions:contest`, e não porque se recomende negar-lhe upload em geral —
> os bundles legados de `frontend/src/test/permissionFixtures.ts` concedem
> `uploads:photo_create` a quase todos os perfis (linhas 153, 304, 389, 434,
> 480, 519), e nada nesta task os altera. Um operador que queira o porteiro
> fotografando ocorrências concede a permissão pelo módulo `uploads`, que é de
> onde ela é.

É decisão tomada, não pergunta em aberto, e é **só documentação**: nenhuma
migração semeia essa linha (doutrina pós-F5), nenhum teste do backend a lê
(nem o gêmeo de §3.6(c), que afirma `ROUTE_PERMISSIONS` e a guarda, não
bundles), e `git diff --stat -- backend/app backend/alembic` continua vazio.

---

## 4. Expected Results

- [ ] **ER-1 — Evidência na abertura da infração, gateada pela permissão que a APRAS-51 exige.** `NewInfractionModal`, em modo *create*, renderiza um controle de anexos **quando, e somente quando,** o conjunto efetivo de `GET /permissions/me` (via `usePermissionSet()`) contém `uploads:photo_create`; cada arquivo sobe por `POST /api/v1/uploads/photo` (endpoint já existente, via o cliente já existente `api/uploads.ts::uploadPhoto`) e as `url` devolvidas entram em `InfractionCreate.evidence_urls` no submit. `InfractionDetailsView` exibe as evidências da infração, sem gate de permissão. Um caso Vitest cobre o fluxo com `api/uploads` mockado, **e** `__tests__/uploadContract.test.tsx` — mockando somente `api/client` e a persona — prova que o cliente real põe no fio `/uploads/photo` com `entity_type = "INFRACTION"` e `body.has("entity_id") === false`. Os cinco fatos do servidor (5 MiB, os três MIME, `INFRACTION`, a rota e `uploads:photo_create`) são fixados por um **pino de duas pontas**, na forma que o repositório já usa em `lotSelectContract.test.tsx` ↔ `test_infractions.py`: o arquivo frontend declara cada constante como literal local, compara com o que `api/uploads.ts` exporta e **nomeia** o gêmeo; e o gêmeo — um caso pytest novo em `backend/tests/test_uploads.py` — afirma `media_service.MAX_FILE_SIZE`/`ALLOWED_MIME_TYPES`, `EntityType.INFRACTION == "INFRACTION"`, `ROUTE_PERMISSIONS[("POST", "/api/v1/uploads/photo")] == "uploads:photo_create"` e, percorrendo o `dependant` da rota viva, que a assinatura de `upload_photo` carrega `PermissionRequired("uploads:photo_create")` (a asserção da precondição APRAS-51). **Nenhum builtin do Node aparece em `frontend/src/`**, e `npm run build` (`tsc -b` com `types: ["vite/client"]`) sucede.
- [ ] **ER-2 — Anexos na contestação, com o ramo negado provado.** `ContestationForm` renderiza o mesmo controle, com `entity_id` = id da infração, e preenche `ContestationCreate.attachment_urls`; `InfractionStageTimeline` passa a exibir `attachment_urls` das entradas do histórico (hoje nenhuma linha os renderiza), somente-leitura. O teste de contrato exercita **os dois ramos com personas nomeadas**: um morador que contesta com `["infractions:contest", "infractions:my_lots_read", "uploads:photo_create"]` vê `attachment-file-input` e sobe o anexo; o mesmo morador **sem** `uploads:photo_create` vê `attachment-unavailable` com a frase pt/en de `infractions.attachments.permissionRequired`, não vê `attachment-file-input`, faz **zero** chamadas ao endpoint, e **ainda assim** submete a contestação por texto com `attachment_urls: []`.
- [ ] **ER-3 — Nenhuma rota nova e nenhuma migração; os limites e a recusa são os do endpoint pós-51, e a UI os mostra.** `git diff --stat -- backend/app backend/alembic` do PR é **vazio**: nenhuma rota, schema, serviço, model ou migração muda. As únicas mudanças fora de `frontend/` são o caso pytest novo em `backend/tests/test_uploads.py` (o gêmeo de ER-1, §3.6(c)) e a nota de documentação em `AGENTS.md` (§3.8) — `git diff --name-only -- backend/` lista **exatamente um** arquivo, e ele está sob `backend/tests/`. Tamanho (5 MiB) e tipos (`image/jpeg`, `image/png`, `image/webp`) são os de `media_service.MAX_FILE_SIZE`/`ALLOWED_MIME_TYPES`, e o pino de duas pontas falha — de um lado ou do outro — se cliente e servidor divergirem. As três recusas do servidor — HTTP 400 `{"detail": "Arquivo excede o limite máximo permitido de 5MB."}`, HTTP 400 `{"detail": "Formato de imagem inválido. Formatos aceitos: JPEG, PNG, WebP."}` e, pós-51, HTTP 403 `{"detail": "The user doesn't have enough privileges"}` de `PermissionRequired` — são renderizadas inline pelo `parseApiError` do módulo, sem `if` por status, provado por um caso por corpo que rejeita a promise do upload.
- [ ] **ER-4 — Gates verdes e a recomendação documentada.** `npm run test:coverage` passa com os thresholds de `vitest.config.ts` inalterados (nunca abaixados) e com as métricas **medidas antes e depois** registradas no relatório do PR, sendo as de depois ≥ as de antes; `npm run lint` sem finding novo; `npm run build` sucede; `i18n/__tests__/parity.test.ts` verde com pt/en em paridade e as contagens de 27/94 intocadas; a tabela de bundle recomendado do `AGENTS.md` ganha a linha `uploads:photo_create` (✓ para ADMINISTRATOR/DIRECTOR/MANAGER/RESIDENT) e a frase que a justifica, com os ✓ declarados como recorte do fluxo de infrações; e a suíte do backend roda verde com `TEST_POSTGRES_URL` definido (`uv run pytest`, gate de 90%), **incluindo o caso novo** `test_the_upload_contract_matches_the_infraction_uploader` de `backend/tests/test_uploads.py` — o único arquivo de `backend/` no diff, e nenhum arquivo de produção do backend entre eles.

---

## 5. Out of Scope

Reafirmado, para não voltar em review: qualquer arquivo sob `backend/app/` ou
`backend/alembic/` — a **única** entrada desta task em `backend/` é o caso
pytest de §3.6(c) em `backend/tests/test_uploads.py`, e nem esse pode tocar
código de produção; hook novo de upload ou de permissão; anexos em modo
*promote* e em `NextStepPanel`;
exclusão física do `MediaAsset` ao remover um chip; moderação de fotos;
refatorar `PhotoUploadModal`; qualquer mudança em `ROUTE_ACCESS`, `NAV_ITEMS`,
nas 13 permissões `infractions:*`, ou na guarda de
`POST /api/v1/uploads/photo` (que é da APRAS-51, não desta task).

Mais três, decididas em vez de deixadas em aberto:

* **Anexo nasce `PENDING_APPROVAL` — a v1 aceita.** Sem `uploads:auto_approve`,
  o asset cai na fila de moderação (`uploads:pending_read`) embora a `url` já
  funcione e já esteja anexada ao processo. A UI **não gateia por `status`** e
  **não mexe em permissão de moderação**: uma evidência recém-subida aparece na
  lista e no submit imediatamente. As duas consequências conhecidas — a fila de
  moderação passa a conter prova de infração e peça de defesa, e um moderador
  pode *rejeitar* uma peça de defesa — são aceitas para a v1. Tirar evidência e
  defesa da moderação é mudança de backend (`media_service` + o fluxo de
  aprovação) e, se for desejada, vira task própria.
* **Só imagem — a v1 aceita.** `ALLOWED_MIME_TYPES` tem três tipos de imagem e
  o Pillow abre os bytes, então um PDF é recusado com 400. Uma defesa costuma
  vir com PDF (laudo, ata, protocolo), mas ampliar isso exige mudar
  `media_service` (validação, geração de thumbnail, provider de storage), o que
  ER-3/ER-4 proíbem. **Follow-up proposto:** uma task *"suporte a documento
  (PDF) no `media_service`"*, escopo backend — estender `ALLOWED_MIME_TYPES`,
  substituir a validação via Pillow por uma que reconheça PDF, decidir o
  thumbnail (ícone ou primeira página) e reexpor os limites. O frontend
  acompanharia editando as constantes de §3.2 e o literal do pino, e o gêmeo de
  §3.6(c) é o que **obriga** essa edição: mudar `ALLOWED_MIME_TYPES` sem mexer
  no cliente deixa o gêmeo vermelho, com o arquivo frontend nomeado na mensagem.
* **Gate por `status` do `MediaAsset` e por `uploads:approve`/`reject`.** O
  único gate de permissão desta task é o de §3.3, sobre
  `uploads:photo_create`, em dois formulários.

---

## 6. Risks

1. **A precondição pode escorregar.** Se a APRAS-51 não entrar antes desta
   task, o gate de §3.3 esconde o controle de usuários que a rota (ainda) aceita
   — a UI fica mais restritiva que o servidor. Mitigação: o gêmeo de §3.6(c),
   que percorre o `dependant` da rota viva e exige um
   `PermissionRequired("uploads:photo_create")` na assinatura de `upload_photo`,
   **falha ruidosamente** nesse cenário, nomeando a APRAS-51, em vez de deixar o
   gate virar uma restrição sem causa. É por isso que essa linha existe — e é
   por isso que ela mora no backend, onde o objeto de rota é inspecionável, e
   não numa leitura de texto feita do frontend.
2. **`entity_id` ausente na criação.** A infração não existe quando a evidência
   sobe, então o `MediaAsset` nasce com `entity_id = NULL`. É o que a rota
   permite (`Optional`) e o que a APRAS-44 §4.4 previu; o vínculo real é a URL
   dentro de `infraction.evidence_urls`. Um upload seguido de um formulário
   abandonado deixa o asset órfão — igual ao `PhotoUploadModal` de hoje.
3. **URL relativa.** `/static/uploads/…` é servida pelo backend. Se o frontend
   estiver em outra origem sem proxy, a miniatura quebra — condição
   **pré-existente e sistêmica** (comunicados, financeiro, media-management), e
   divergir aqui criaria um segundo padrão. Não é resolvida por esta task.
4. **`LocalStorageProvider` em serverless.** Disco efêmero; o provider Vercel
   Blob é um stub que levanta `NotImplementedError`. Pré-existente, vale para
   toda mídia do sistema.
5. **Operador que não concede `uploads:photo_create`.** Um morador com
   `infractions:contest` e sem ela contesta por texto e não anexa — degradação
   deliberada (§3.4), não defeito. A nota de §3.8 no `AGENTS.md` é a mitigação
   documental.

---

## 7. Gates

```bash
# frontend/ — medir ANTES de tocar em qualquer arquivo, e guardar o resultado
npm run test:coverage       # baseline: lines/functions/branches/statements
npm run lint
npm run build
npm run test:coverage       # depois: cada métrica >= a baseline registrada

# backend/ — produção byte-idêntica; só backend/tests/ pode mudar
git diff --stat -- backend/app backend/alembic   # exige saída VAZIA
git diff --name-only -- backend/                 # exige exatamente:
                                                 #   backend/tests/test_uploads.py
# a suíte inteira, com o Postgres real ligado (simetria com a APRAS-51 §11:
# test_migrations_postgres.py:57-60 se auto-pula sem esta variável, e um
# `uv run pytest` pelado fica verde sem estar completo)
TEST_POSTGRES_URL=postgresql+psycopg://... uv run pytest   # verde, gate de 90%
uv run pytest backend/tests/test_uploads.py \
  -k the_upload_contract_matches_the_infraction_uploader   # o gêmeo, explícito
```

O gêmeo é **vermelho até a APRAS-51 entrar** (§3.6(c)), o que é o
comportamento pretendido: estes gates só ficam verdes sobre a árvore pós-51.
