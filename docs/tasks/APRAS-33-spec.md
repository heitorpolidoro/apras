# APRAS-33 — Implementar votação de assembleia e enquete

**Status:** Spec de implementação. Substitui as decisões em aberto de `docs/tasks/APRAS-33-scope.md`.

## Source

`docs/tasks/APRAS-33-scope.md` (documento de escopo) levantou seis perguntas em aberto e recomendou uma abordagem. Todas as seis foram decididas com o usuário; **várias decisões contrariam o esboço do documento de escopo**, e onde houver divergência **esta spec vence**. As divergências relevantes estão marcadas com "⚠️ diverge do scope doc" ao longo do texto.

## Problem

O condomínio precisa deliberar formalmente (aprovação de orçamento, obras, despesas extraordinárias) e o APRAS não tem nada nesse espaço. Hoje o síndico roda a votação fora da plataforma — papel, enquete de WhatsApp, planilha — sem trilha de auditoria e sem produzir um registro que sustente a ata.

Esta task entrega duas coisas distintas:

1. **Assembleia** — votação formal, um voto por lote, restrita a proprietários adimplentes, atribuída, agrupada por pauta, com geração de **minuta de ata**.
2. **Enquete** — consulta informal, um voto por usuário, aberta a qualquer morador, opcionalmente anônima, sem valor deliberativo.

## Scope

**Entra:** modelo `Assembly` (container mínimo), `Vote`, `VoteOption`, `Ballot` (append-only), `BallotRejection`, flag de inadimplência no `Lot`, apuração com janela fechada, geração de minuta em HTML, salvamento da minuta no Document Center existente, RBAC, frontend das duas modalidades.

**Não entra:** ver **Non-Goals** ao final. Em especial: sem agendamento/calendário, sem quórum, sem presença/check-in, sem procuração, sem voto ponderado, sem voto secreto real, sem assinatura digital.

---

## Data Model

### `backend/app/models/enums.py` — adicionar

```python
class AssemblyType(StrEnum):
    """Enumeration for assembly type."""

    AGO = "AGO"  # Assembleia Geral Ordinária
    AGE = "AGE"  # Assembleia Geral Extraordinária


class AssemblyStatus(StrEnum):
    """Enumeration for assembly status."""

    DRAFT = "DRAFT"
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class VoteKind(StrEnum):
    """Enumeration for vote kind."""

    ASSEMBLEIA = "ASSEMBLEIA"
    ENQUETE = "ENQUETE"


class VoteType(StrEnum):
    """Enumeration for vote answer type."""

    SINGLE_CHOICE = "SINGLE_CHOICE"
    MULTIPLE_CHOICE = "MULTIPLE_CHOICE"


class VoteStatus(StrEnum):
    """Enumeration for vote status."""

    OPEN = "OPEN"
    CLOSED = "CLOSED"


class BallotRejectionReason(StrEnum):
    """Enumeration for why a ballot attempt was refused."""

    DELINQUENT_LOT = "DELINQUENT_LOT"
    NOT_OWNER = "NOT_OWNER"
    NO_ACTIVE_LOT_LINK = "NO_ACTIVE_LOT_LINK"
    VOTE_NOT_OPEN = "VOTE_NOT_OPEN"
    ROLE_FORBIDDEN = "ROLE_FORBIDDEN"
```

⚠️ **diverge do scope doc:** não existe `VoteType.FREE_TEXT`. Foi cortado deliberadamente — texto livre não apura, não congela em snapshot, se autoidentifica em enquete anônima, e duplica o módulo de Feedback, que já faz texto livre com anonimato e resposta do board. **Não deixar campo, hook ou ponto de extensão preparado para texto livre**: se a necessidade aparecer, é decisão futura, não estrutura antecipada.

### `backend/app/models/voting.py` (arquivo novo)

Um arquivo para os cinco modelos, seguindo o precedente de `finance.py`, que agrupa `FinanceCategory`/`BudgetLine`/`FinancialTransaction`.

```python
class Assembly(SQLModel, table=True):
    """Container mínimo que agrupa as votações de uma pauta e emite a minuta."""

    __tablename__ = "assembly"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str = Field(nullable=False, index=True)
    type: AssemblyType = Field(nullable=False, index=True)
    held_on: date = Field(nullable=False, index=True)
    agenda: str | None = Field(default=None, nullable=True)
    status: AssemblyStatus = Field(
        default=AssemblyStatus.DRAFT, nullable=False, index=True
    )
    created_by_id: UUID = Field(
        foreign_key="user.id", ondelete="RESTRICT", nullable=False, index=True
    )
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    closed_at: datetime | None = Field(default=None, nullable=True)

    votes: list["Vote"] = Relationship(back_populates="assembly")
    created_by: "User" = Relationship()


class Vote(SQLModel, table=True):
    __tablename__ = "vote"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    assembly_id: UUID | None = Field(
        default=None,
        foreign_key="assembly.id",
        ondelete="CASCADE",
        nullable=True,
        index=True,
    )
    kind: VoteKind = Field(nullable=False, index=True)
    title: str = Field(nullable=False)
    description: str | None = Field(default=None, nullable=True)
    vote_type: VoteType = Field(nullable=False)
    status: VoteStatus = Field(default=VoteStatus.OPEN, nullable=False, index=True)
    # Só tem efeito quando kind == ENQUETE. Em ASSEMBLEIA é sempre False e o
    # service rejeita a criação com True (ver RBAC / Visibilidade).
    is_anonymous: bool = Field(default=False, nullable=False)
    opens_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    closes_at: datetime = Field(nullable=False)
    # Apuração congelada, materializada no fechamento. NULL enquanto aberta.
    tally_snapshot_json: str | None = Field(default=None, nullable=True)
    created_by_id: UUID = Field(
        foreign_key="user.id", ondelete="RESTRICT", nullable=False, index=True
    )
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    closed_at: datetime | None = Field(default=None, nullable=True)

    assembly: Optional[Assembly] = Relationship(back_populates="votes")
    options: list["VoteOption"] = Relationship(
        back_populates="vote", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    ballots: list["Ballot"] = Relationship(
        back_populates="vote", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class VoteOption(SQLModel, table=True):
    __tablename__ = "vote_option"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    vote_id: UUID = Field(
        foreign_key="vote.id", ondelete="CASCADE", nullable=False, index=True
    )
    label: str = Field(nullable=False)
    order_index: int = Field(default=0, nullable=False)

    vote: Vote = Relationship(back_populates="options")


class Ballot(SQLModel, table=True):
    """Cédula. APPEND-ONLY: nunca sofre UPDATE nem DELETE.

    Trocar o voto insere uma nova linha; a apuração considera a última linha
    por `voter_key` (maior `cast_at`, desempate por `id`).
    """

    __tablename__ = "ballot"
    __table_args__ = (
        Index("ix_ballot_vote_voter_cast", "vote_id", "voter_key", "cast_at"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    vote_id: UUID = Field(
        foreign_key="vote.id", ondelete="CASCADE", nullable=False, index=True
    )
    # "lot:<uuid>" em ASSEMBLEIA, "user:<uuid>" em ENQUETE.
    voter_key: str = Field(nullable=False, index=True)
    lot_id: UUID | None = Field(
        default=None, foreign_key="lot.id", ondelete="SET NULL", nullable=True, index=True
    )
    voter_user_id: UUID | None = Field(
        default=None, foreign_key="user.id", ondelete="SET NULL", nullable=True, index=True
    )
    # Congela a fração ideal do lote no instante do voto. Voto ponderado não é
    # implementado no v1, mas fica recalculável depois mesmo que a fração mude.
    fraction_ideal_at_cast: float | None = Field(default=None, nullable=True)
    selected_option_ids_json: str = Field(nullable=False)
    cast_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    vote: Vote = Relationship(back_populates="ballots")
```

⚠️ **diverge do scope doc:** **não existe** `UniqueConstraint("vote_id", "voter_key")`. A troca de voto é permitida, então o mesmo votante gera N linhas legitimamente. A unicidade é regra de leitura ("a última por `voter_key`"), não de esquema. Um índice não-único cobre a consulta.

⚠️ **diverge do scope doc:** **não existe** `Ballot.free_text_response`.

```python
class BallotRejection(SQLModel, table=True):
    """Log de tentativa de voto barrada.

    Necessário porque a validação de adimplência acontece no ato do voto: o
    estado que causou a recusa pode não existir mais quando alguém contestar
    "me impediram de votar".
    """

    __tablename__ = "ballot_rejection"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    vote_id: UUID = Field(
        foreign_key="vote.id", ondelete="CASCADE", nullable=False, index=True
    )
    user_id: UUID | None = Field(
        default=None, foreign_key="user.id", ondelete="SET NULL", nullable=True, index=True
    )
    lot_id: UUID | None = Field(
        default=None, foreign_key="lot.id", ondelete="SET NULL", nullable=True, index=True
    )
    reason: BallotRejectionReason = Field(nullable=False, index=True)
    attempted_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
```

### `backend/app/models/lot.py` — alterar

Três campos novos em `Lot`:

```python
    is_delinquent: bool = Field(default=False, nullable=False, index=True)
    delinquency_updated_at: datetime | None = Field(default=None, nullable=True)
    delinquency_updated_by_id: UUID | None = Field(
        default=None, foreign_key="user.id", ondelete="SET NULL", nullable=True
    )
```

**Fonte do dado:** manual. O APRAS não tem cobrança por lote — `FinancialTransaction` é contabilidade do condomínio e não tem `lot_id`; não existe `LotCharge`, boleto ou mensalidade. A flag é mantida à mão por Administrator/Director. Integrar com uma fonte externa (planilha, sistema de cobrança) é decisão adiada, fora desta task.

**Não há tabela de histórico da flag.** O `BallotRejection` já registra o momento que importa — a recusa efetiva, com motivo e timestamp — que é o que é contestado depois.

### Migration

`backend/alembic/versions/0025_add_voting_tables.py` (a última existente é `0024_task_visible_to_m2m.py`).

- Cria os seis enums (`AssemblyType`, `AssemblyStatus`, `VoteKind`, `VoteType`, `VoteStatus`, `BallotRejectionReason`) e as cinco tabelas: `assembly`, `vote`, `vote_option`, `ballot`, `ballot_rejection`.
- `ALTER TABLE lot` adicionando `is_delinquent` (`server_default='false'`, `nullable=False`), `delinquency_updated_at`, `delinquency_updated_by_id`.
- `downgrade()` derruba as cinco tabelas, as três colunas e os enums.

Enums como `sa.Enum(..., native_enum=False)` ou `sa.String`, conforme o que as migrations existentes já fazem — a suíte de testes cria o schema via `SQLModel.metadata.create_all()` contra SQLite em memória (ver o comentário em `user_type.py` sobre `ARRAY` não compilar em SQLite), então nada específico de Postgres.

---

## Elegibilidade e adimplência — regras exatas

Guard de service layer, seguindo o padrão de `_assert_gatekeeper_access` em `access_logs.py`.

`_assert_can_cast(user, vote, lot_id)` avalia **nesta ordem**, e **toda recusa grava uma linha em `BallotRejection`** antes de levantar o erro:

1. **Janela** — `vote.status == OPEN` e `opens_at <= now < closes_at`. Senão `VOTE_NOT_OPEN`.
2. **Papel** — `user.role` não pode ser `GUEST` nem `PORTEIRO`, em nenhuma das duas modalidades. Senão `ROLE_FORBIDDEN`.
3. **Se `kind == ASSEMBLEIA`:**
   - `lot_id` é obrigatório no corpo da requisição.
   - Existe `UserLotLink` para `(user, lot)` com `association_type == PROPRIETARIO`, ativo na data (`start_date` nulo ou `<= now`, e `end_date` nulo ou `> now`). Senão `NOT_OWNER`.
   - `lot.is_deleted == False`. Senão `NOT_OWNER`.
   - **`lot.is_delinquent == False`. Senão `DELINQUENT_LOT`.**
   - `voter_key = f"lot:{lot_id}"`, `fraction_ideal_at_cast = lot.fraction_ideal`.
4. **Se `kind == ENQUETE`:**
   - Existe algum `UserLotLink` ativo para o usuário, de **qualquer** `association_type` — inclusive `INQUILINO`. Senão `NO_ACTIVE_LOT_LINK`.
   - Sem checagem de adimplência.
   - `voter_key = f"user:{user.id}"`, `lot_id` e `fraction_ideal_at_cast` ficam nulos.

### Momento da validação

A adimplência é verificada **no ato de cada voto**, não em snapshot na abertura. Isso é a regra do Art. 1.335, III do Código Civil — o direito de voto fica suspenso *enquanto* o condômino está em débito, e é restaurado quando quita.

Consequências, que caem todas da mesma regra e **não são exceções codificadas**:

- Votou adimplente e depois ficou inadimplente → o voto original **permanece válido e apurado**, mas a tentativa de troca é recusada, porque trocar é um novo ato de votar e passa pela mesma validação.
- Estava inadimplente e quitou durante a janela → passa a poder votar normalmente.

⚠️ **diverge do scope doc:** o esboço da seção 4 do scope doc previa "qualquer autenticado com standing de `RESIDENT`". Isso é juridicamente errado: **inquilino não vota em assembleia**. A modalidade `ENQUETE` é onde o inquilino participa.

### Um proprietário, vários lotes

Cai naturalmente do `voter_key`: um proprietário de dois lotes tem duas cédulas, `lot:<A>` e `lot:<B>`, e conta 2 na apuração. Nenhuma regra especial.

---

## RBAC — regras exatas por ação

| Ação | Papéis |
|---|---|
| Criar / editar / fechar `Assembly` | `ADMINISTRATOR`, `DIRECTOR` |
| Criar votação com `kind == ASSEMBLEIA` | `ADMINISTRATOR`, `DIRECTOR` |
| Criar votação com `kind == ENQUETE` | `ADMINISTRATOR`, `DIRECTOR`, `MANAGER` |
| Editar votação | Mesmos da criação, **e só enquanto não houver nenhuma cédula**. Depois da primeira, a votação está congelada — resta fechar antecipadamente. |
| Fechar votação antecipadamente | Mesmos da criação |
| Votar em `ASSEMBLEIA` | Proprietário de lote ativo e adimplente (ver Elegibilidade) |
| Votar em `ENQUETE` | Qualquer vínculo ativo a lote, inclusive `INQUILINO` |
| Ver apuração | Quem podia votar + `ADMINISTRATOR`/`DIRECTOR` — **só após o fechamento** |
| Ver contagem de participação | Os mesmos, a qualquer momento |
| Ver o próprio voto | O próprio votante, sempre |
| Alterar `Lot.is_delinquent` | `ADMINISTRATOR`, `DIRECTOR` |
| Gerar / salvar minuta | `ADMINISTRATOR`, `DIRECTOR` |

`GUEST` e `PORTEIRO` nunca votam, nas duas modalidades — mesmo carve-out que o gatekeeper já tem em ações de governança.

Criar votação com `kind == ASSEMBLEIA` e `is_anonymous == True` é rejeitado com `400`: assembleia é sempre atribuída.

Criar votação com `kind == ASSEMBLEIA` exige `assembly_id` não-nulo. `kind == ENQUETE` exige `assembly_id` nulo.

### Semântica de `Assembly.status`

O status da assembleia é distinto do status de cada votação, e governa o que a assembleia permite:

- **`DRAFT`** — pauta em montagem. Votações podem ser criadas, editadas e removidas. Nenhuma aceita cédula ainda: `POST /votes/{id}/ballots` responde `400` (`VoteNotOpenError`) enquanto a assembleia estiver em `DRAFT`, mesmo que a janela da votação já tenha começado.
- **`OPEN`** — pauta liberada. As votações passam a aceitar cédulas conforme as próprias janelas. Editar votação continua sujeito à regra de congelamento (nenhuma cédula lançada).
- **`CLOSED`** — encerrada. Nenhuma cédula é aceita, e **só neste estado a minuta pode ser gerada ou salva**; antes disso `GET /{id}/minutes` responde `400`.

`POST /assemblies/{id}/close` **fecha em cascata todas as votações da assembleia que ainda estiverem abertas**, materializando o snapshot de cada uma, e depois marca a assembleia como `CLOSED` com `closed_at`. É a operação que torna a minuta disponível.

---

## Visibilidade e mascaramento

**Não existe voto secreto persistente.** Para garantir voto único por lote é obrigatório gravar qual lote votou, então a cédula é intrinsecamente ligável. Sigilo real exigiria não guardar esse vínculo, o que quebra a prevenção de voto duplo — e esquema criptográfico é não-objetivo declarado.

⚠️ **diverge do scope doc:** o campo `is_anonymous` do esboço, que se aplicaria a qualquer votação com semântica do `Feedback`, foi substituído pelas duas regras abaixo.

### Regra 1 — janela fechada (as duas modalidades)

Enquanto a votação está aberta, o endpoint de apuração devolve **apenas a contagem de votantes** — nunca o resultado por opção, nunca atribuição. **Inclusive para `ADMINISTRATOR` e `DIRECTOR`**: não há carve-out para o criador. Se o síndico enxerga a parcial, ele articula com ela em mãos, e foi ele quem abriu a votação.

O gate é **servidor**. Um cliente chamando o endpoint direto recebe a mesma resposta reduzida. Esconder no frontend não conta.

### Regra 2 — anonimato de enquete (só `ENQUETE`)

Quando `kind == ENQUETE and is_anonymous`, a resposta da apuração **não emite `voter_user_id` nem `lot_id`**, nem depois do fechamento. O mascaramento é **no serializer**, não no componente de frontend: a API não envia o dado. Enquete anônima fica agregada para sempre.

Isso **não** é sigilo criptográfico — o vínculo continua no banco, e quem tem acesso ao banco vê. A copy da UI deve dizer **"sua resposta não é exibida com seu nome"**, nunca "ninguém sabe quem votou".

### Regra 3 — o próprio voto

O votante sempre enxerga a própria cédula, aberta ou fechada, anônima ou não, via endpoint dedicado. É necessário para poder trocar o voto, e não é vazamento.

### Após o fechamento

| | durante a janela | após fechar |
|---|---|---|
| assembleia | contagem de votantes | agregado + atribuição **por unidade (Bloco/Lote)** |
| enquete normal | contagem de votantes | agregado + atribuição por usuário |
| enquete anônima | contagem de votantes | **só agregado, permanentemente** |

Assembleia identifica por **unidade**, não por nome de pessoa: o voto é do lote. `voter_user_id` fica gravado para auditoria interna, mas não é o que a apuração nem a minuta exibem.

---

## Fechamento e snapshot

`Vote.tally_snapshot_json` é materializado uma única vez, e a partir daí a apuração é lida dele — não recalculada.

Duas portas de entrada, **sem depender de scheduler** (não introduzir um nesta task):

1. **Fechamento explícito** — `POST /votes/{id}/close` por Administrator/Director antes de `closes_at`.
2. **Materialização preguiçosa** — a primeira leitura de qualquer endpoint da votação depois de `closes_at` calcula o snapshot, grava, marca `status = CLOSED` e `closed_at`, e responde já com ele. Idempotente: se `tally_snapshot_json` não é nulo, apenas lê.

Conteúdo do snapshot: contagem por opção, total de votantes, total de lotes ativos (denominador), e a lista atribuída (omitida quando enquete anônima).

**Denominador = total de lotes com `is_deleted == False`.** Com validação no ato, não existe "lista de aptos" no fechamento — a elegibilidade foi móvel a votação inteira. A apuração reporta "22 votos de 40 lotes"; inadimplência governa quem conseguiu votar, não o denominador.

---

## Backend Changes

### `backend/app/core/exceptions.py` — adicionar

`AssemblyNotFoundError`, `VoteNotFoundError`, `VoteNotOpenError`, `VoteAlreadyClosedError`, `VoteFrozenError` (edição após a primeira cédula), `DelinquentLotError`, `NotLotOwnerError`, `NoActiveLotLinkError`, `TallyNotAvailableError`, `AnonymousAssemblyError`. Todas herdam `DomainError`, seguindo o formato das existentes.

### `backend/app/core/exception_handlers.py`

Mapear: `*NotFoundError` → `404`; `DelinquentLotError`, `NotLotOwnerError`, `NoActiveLotLinkError`, `TallyNotAvailableError` → `403`; `VoteNotOpenError`, `VoteAlreadyClosedError`, `VoteFrozenError`, `AnonymousAssemblyError` → `400`.

### `backend/app/schemas/voting.py` (arquivo novo)

`AssemblyCreate/Update/Read`, `VoteCreate/Update/Read`, `VoteOptionCreate/Read`, `BallotCreate` (`lot_id: UUID | None`, `selected_option_ids: list[UUID]`), `BallotRead`, `TallyRead`.

`TallyRead` é **um schema com dois modos**, e o service escolhe qual preencher:

- votação aberta → `status`, `voters_count`, `total_lots`; `results` e `attributions` **ausentes**.
- votação fechada → `results` (por opção) e `attributions` (omitido em enquete anônima).

`MULTIPLE_CHOICE` valida `len(selected_option_ids) >= 1`; `SINGLE_CHOICE` valida `== 1`. Todos os ids têm que pertencer à votação.

### `backend/app/services/voting_service.py` (arquivo novo)

- `_assert_board(user)` — Administrator/Director.
- `_assert_can_create_vote(user, kind)` — inclui Manager quando `ENQUETE`.
- `_assert_can_cast(user, vote, lot_id)` — a cadeia da seção Elegibilidade, gravando `BallotRejection` em toda recusa.
- `cast_ballot(...)` — sempre `INSERT`, nunca `UPDATE`.
- `get_latest_ballots(vote)` — última linha por `voter_key`.
- `compute_tally(vote)` / `materialize_snapshot(vote)`.
- `render_minutes_html(assembly)`.

### `backend/app/api/v1/endpoints/voting.py` (arquivo novo)

Dois routers no mesmo módulo, como `reservations.py` já faz com `spaces_router`/`reservations_router`.

`assemblies_router`:
- `POST /` · `GET /` · `GET /{id}` · `PATCH /{id}` · `POST /{id}/close`
- `GET /{id}/minutes` → HTML da minuta
- `POST /{id}/minutes/save` → grava no Document Center

`votes_router`:
- `POST /` · `GET /` (filtros `kind`, `status`, `assembly_id`) · `GET /{id}` · `PATCH /{id}` · `POST /{id}/close`
- `POST /{id}/ballots` → votar
- `GET /{id}/my-ballot` → a cédula do usuário autenticado
- `GET /{id}/tally` → contagem se aberta, apuração se fechada

### `backend/app/api/v1/endpoints/lots.py`

- `PATCH /lots/{id}/delinquency` (Administrator/Director) — altera `is_delinquent` e carimba `delinquency_updated_at` / `delinquency_updated_by_id`. Endpoint dedicado, não campo no `PATCH /lots/{id}` genérico, porque é ele que barra voto e merece superfície própria.

### `backend/app/api/v1/api.py`

```python
api_router.include_router(voting.assemblies_router, prefix="/assemblies", tags=["assemblies"])
api_router.include_router(voting.votes_router, prefix="/votes", tags=["votes"])
```

---

## Minuta de ata

**O sistema gera uma minuta, não uma ata.** Ata com validade precisa de assinatura do síndico e do secretário, e o app não tem assinatura digital. A minuta elimina a transcrição manual da apuração — que é onde está o valor — sem o app alegar formalidade que não entrega.

**Formato: HTML por template**, servido para o navegador imprimir em PDF. O projeto **não tem lib de PDF** (`pyproject.toml` traz só `qrcode`), e `weasyprint`/`reportlab` seriam dependência nova para um documento que será revisado e reassinado fora da plataforma. Não adicionar dependência de PDF nesta task.

Conteúdo, por `Assembly`:

- Cabeçalho: título, tipo (AGO/AGE), `held_on`, janela de abertura e fechamento das votações.
- Pauta (`agenda`).
- Por votação: título, descrição, opções e resultado por opção.
- Tabela atribuída: **Bloco/Lote → escolha → data-hora**.
- Denominador: total de lotes ativos, quantos votaram, quantos não votaram.
- **Lotes barrados por inadimplência**, lidos de `BallotRejection` com `reason == DELINQUENT_LOT`. Obrigatório — sem isso a minuta parece ter perdido gente, e é o que responde "por que a unidade 12 não consta".
- Rodapé: espaço de assinatura e nota de que o documento foi gerado pelo sistema e não substitui ata registrada.

**Salvamento:** `POST /assemblies/{id}/minutes/save` grava a minuta como `AssociationDocument` numa pasta do Document Center, com `mime_type = "text/html"`. O `AssociationDocument` já tem versionamento via `previous_version_id`, então o síndico pode subir a versão final assinada como nova versão do mesmo documento.

---

## Frontend Changes

- `frontend/src/types/voting.ts` — tipos espelhando os schemas.
- `frontend/src/api/voting.ts` — cliente.
- `frontend/src/features/assembly-voting/` — nova feature, seguindo a estrutura de `space-reservation-management/`:
  - lista de assembleias e enquetes;
  - criação de assembleia e de votação (Administrator/Director; Manager só enquete);
  - tela de votação com as opções, o próprio voto destacado quando já votou, e botão de trocar enquanto a janela estiver aberta;
  - tela de apuração, que durante a janela mostra **apenas** a contagem de votantes;
  - visualização da minuta.
- `App.tsx` — rotas com `ProtectedRoute` gatilhado por papel; `PORTEIRO` e `GUEST` não alcançam nenhuma delas.
- `Navbar.tsx` — item de menu.
- i18n em `frontend/src/i18n/locales/` para todas as strings novas, incluindo a copy de anonimato ("sua resposta não é exibida com seu nome").

---

## Non-Goals

Explicitamente fora, e a serem recusados se aparecerem no review:

- **Voto secreto real.** Consequência declarada: **eleição e destituição de síndico por voto secreto não são suportadas pelo APRAS** — fazem-se no papel. Isto é limite conhecido, não bug.
- Quórum: sem cálculo, sem enforcement, sem registro de presença ou check-in.
- Agendamento e calendário compartilhado. `Assembly` tem `held_on` e nada mais; não existe view de calendário nem lembrete.
- Procuração / voto por representante.
- Voto ponderado por `fraction_ideal`. O valor é congelado na cédula para permitir recálculo futuro, mas nenhuma apuração o utiliza no v1.
- `FREE_TEXT` em votação, e **qualquer estrutura preparatória para ele**.
- Geração de PDF no servidor e qualquer dependência de PDF.
- Assinatura digital, ICP-Brasil, registro em cartório, numeração legal de ata.
- Cobrança por lote / derivação automática de inadimplência. A flag é manual nesta task.
- Notificações de abertura e fechamento (push, e-mail, WhatsApp) — infraestrutura ausente e gapada em separado.
- Votação recorrente ou por template.
- Multi-tenancy. Confirmado single-tenant: nenhum modelo do APRAS tem escopo de organização.

---

## Testing

Os testes abaixo cobrem as regras decididas e são obrigatórios. Cobertura genérica de CRUD segue o padrão do repo.

**Backend**

1. Proprietário com dois lotes vota nos dois; a apuração conta 2.
2. Segundo voto do mesmo lote substitui o primeiro; a apuração conta 1 e considera a cédula mais recente.
3. Inquilino é recusado em assembleia (`403`, `BallotRejection` com `NOT_OWNER`) e aceito em enquete.
4. Lote inadimplente é recusado no ato (`403`) **e** grava `BallotRejection` com `DELINQUENT_LOT`.
5. Votou adimplente → lote marcado inadimplente → tentativa de troca é recusada e **o voto original permanece na apuração**.
6. Lote inadimplente → quitado durante a janela → passa a conseguir votar.
7. `GET /votes/{id}/tally` com votação aberta devolve só a contagem — **inclusive quando o requisitante é `ADMINISTRATOR`**.
8. Ao fechar, `tally_snapshot_json` é gravado; leituras seguintes saem do snapshot e não recalculam.
9. `fraction_ideal_at_cast` congela: alterar `Lot.fraction_ideal` depois não altera cédula já lançada.
10. Enquete anônima fechada: a resposta de `/tally` **não contém `voter_user_id` nem `lot_id`** — o teste que separa mascaramento no serializer de esconder no frontend.
11. `GUEST` e `PORTEIRO` são recusados nas duas modalidades.
12. A minuta inclui a lista de lotes barrados por inadimplência.

Complementares: `PATCH` em votação com cédula existente devolve `400` (`VoteFrozenError`); criar votação de assembleia com `is_anonymous=True` devolve `400`; `GET /my-ballot` devolve a própria cédula com a votação aberta; votar numa assembleia em `DRAFT` devolve `400` mesmo com a janela da votação aberta; `POST /assemblies/{id}/close` fecha em cascata as votações abertas e materializa o snapshot de cada uma; `GET /{id}/minutes` antes do fechamento devolve `400`.

**Frontend**

Testes de componente para: a tela de apuração não renderizar resultado por opção com a votação aberta; o botão de trocar voto aparecer só dentro da janela; a rota ser inacessível a `PORTEIRO`.

---

## Expected Results

1. Administrator/Director cria uma assembleia (AGO/AGE) com N votações de pauta, e cada votação aceita exatamente um voto por lote.
2. Proprietário de dois lotes vota duas vezes, uma por lote, e a apuração conta os dois.
3. Lote marcado como inadimplente é impedido de votar no momento do voto, com a recusa registrada e visível na minuta; se quitar durante a janela, passa a votar.
4. Com a votação aberta, o endpoint de apuração devolve apenas a contagem de votantes para qualquer papel, incluindo Administrator; o resultado por opção só aparece depois do fechamento.
5. Enquete com anonimato ligado não devolve identificação do votante na resposta da API nem depois de fechar, e o votante continua vendo o próprio voto.
6. A minuta da assembleia é gerada em HTML com resultado por pauta, atribuição por Bloco/Lote, denominador de lotes ativos e lista de lotes barrados por inadimplência, e pode ser salva no Document Center.
