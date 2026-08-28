# APRAS-33 — Implementar votação de assembleia e enquete

**Status:** Spec de implementação. Substitui as decisões em aberto de `docs/tasks/APRAS-33-scope.md`.

## Source

`docs/tasks/APRAS-33-scope.md` (documento de escopo) levantou seis perguntas em aberto e recomendou uma abordagem. Todas as seis foram decididas com o usuário; **várias decisões contrariam o esboço do documento de escopo**, e onde houver divergência **esta spec vence**. As divergências relevantes estão marcadas com "⚠️ diverge do scope doc" ao longo do texto.

## Problem

O condomínio precisa deliberar formalmente (aprovação de orçamento, obras, despesas extraordinárias) e o APRAS não tem nada nesse espaço. Hoje o síndico roda a votação fora da plataforma — papel, enquete de WhatsApp, planilha — sem trilha de auditoria e sem produzir um registro que sustente a ata.

Esta task entrega duas coisas distintas:

1. **Assembleia** — votação formal, um voto por lote (lançável por qualquer elegível do lote — proprietário(s) ou cadastro manual extra), restrita a lotes adimplentes, atribuída, agrupada por pauta, com geração de **minuta de ata**.
2. **Enquete** — consulta informal, um voto por usuário, aberta a qualquer morador, opcionalmente anônima, sem valor deliberativo.

## Scope

**Entra:** modelo `Assembly` (container mínimo), `Vote`, `VoteOption`, `Ballot` (append-only, com retirada), `BallotRejection`, `LotVoterEligibility`, flag de inadimplência no `Lot`, apuração com janela fechada, geração de minuta em HTML, salvamento da minuta no Document Center existente, RBAC, frontend das duas modalidades.

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
    LOT_ALREADY_VOTED = "LOT_ALREADY_VOTED"
```

`LOT_ALREADY_VOTED` — adicionado após a revisão do usuário sobre múltiplos elegíveis por lote (ver seção Elegibilidade): tentativa de um elegível votar por um lote enquanto outro elegível do mesmo lote já tem cédula ativa.

⚠️ **diverge do scope doc:** não existe `VoteType.FREE_TEXT`. Foi cortado deliberadamente — texto livre não apura, não congela em snapshot, se autoidentifica em enquete anônima, e duplica o módulo de Feedback, que já faz texto livre com anonimato e resposta do board. **Não deixar campo, hook ou ponto de extensão preparado para texto livre**: se a necessidade aparecer, é decisão futura, não estrutura antecipada.

### `backend/app/models/voting.py` (arquivo novo)

Um arquivo para os **seis** modelos, seguindo o precedente de `finance.py`, que agrupa `FinanceCategory`/`BudgetLine`/`FinancialTransaction`.

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


class LotVoterEligibility(SQLModel, table=True):
    """Elegível extra de assembleia para um lote, além dos `UserLotLink` com
    `association_type == PROPRIETARIO` (que já cobrem sozinhos o caso de
    co-propriedade — o modelo já permite mais de um `PROPRIETARIO` por lote,
    sem constraint que limite a um só).

    Cadastro manual porque depende de documento que o APRAS não verifica
    (certidão de casamento, por exemplo): quem administra decide, fora do
    sistema, se aquela pessoa realmente tem direito de representar o lote.
    """

    __tablename__ = "lot_voter_eligibility"
    __table_args__ = (
        UniqueConstraint("lot_id", "user_id", name="uq_lot_voter_eligibility"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    lot_id: UUID = Field(
        foreign_key="lot.id", ondelete="CASCADE", nullable=False, index=True
    )
    user_id: UUID = Field(
        foreign_key="user.id", ondelete="CASCADE", nullable=False, index=True
    )
    added_by_id: UUID | None = Field(
        default=None, foreign_key="user.id", ondelete="SET NULL", nullable=True
    )
    added_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)


class Ballot(SQLModel, table=True):
    """Cédula. APPEND-ONLY: nunca sofre UPDATE nem DELETE — nem a retirada é
    um UPDATE, é uma nova linha com `is_retraction=True`.

    "Cédula ativa" de um `voter_key` = última linha por `cast_at` (desempate
    por `id`). Se essa última linha tem `is_retraction=True`, o `voter_key`
    está **sem voto ativo no momento** — não conta na apuração e (em
    ASSEMBLEIA) libera o lote para qualquer outro elegível votar.
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
    # Quem efetivamente lançou ESTA linha (não é "o lote", é a pessoa). Em
    # ASSEMBLEIA, é quem detém a cédula ativa do lote enquanto ela não for
    # retirada — só essa pessoa pode trocar ou retirar (ver Elegibilidade).
    voter_user_id: UUID | None = Field(
        default=None, foreign_key="user.id", ondelete="SET NULL", nullable=True, index=True
    )
    # Congela a fração ideal do lote no instante do voto. Voto ponderado não é
    # implementado no v1, mas fica recalculável depois mesmo que a fração mude.
    fraction_ideal_at_cast: float | None = Field(default=None, nullable=True)
    is_retraction: bool = Field(default=False, nullable=False)
    # Vazio/null quando is_retraction=True.
    selected_option_ids_json: str | None = Field(default=None, nullable=True)
    cast_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    vote: Vote = Relationship(back_populates="ballots")
```

⚠️ **diverge do scope doc:** **não existe** `UniqueConstraint("vote_id", "voter_key")`. A troca de voto é permitida, então o mesmo votante gera N linhas legitimamente. A unicidade é regra de leitura ("a última por `voter_key`"), não de esquema. Um índice não-único cobre a consulta.

⚠️ **diverge do scope doc:** **não existe** `Ballot.free_text_response`.

**Adicionado após revisão do usuário, além das seis perguntas originais:** `LotVoterEligibility` e `Ballot.is_retraction` — ver seção Elegibilidade para a mecânica completa de retirada/bloqueio de voto por lote.

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

`backend/alembic/versions/0025_add_voting_tables.py` — **checar `alembic heads` no momento da implementação**; a última existente nesta revisão da spec é `0024_task_visible_to_m2m.py`, mas várias tasks concorrentes têm mexido no fim da cadeia de migrations neste repo, então não assumir o número sem checar.

- Cria os seis enums (`AssemblyType`, `AssemblyStatus`, `VoteKind`, `VoteType`, `VoteStatus`, `BallotRejectionReason`) e as **seis** tabelas: `assembly`, `vote`, `vote_option`, `ballot`, `ballot_rejection`, `lot_voter_eligibility`.
- `ALTER TABLE lot` adicionando `is_delinquent` (`server_default='false'`, `nullable=False`), `delinquency_updated_at`, `delinquency_updated_by_id`.
- `downgrade()` derruba as seis tabelas, as três colunas e os enums.

Enums como `sa.Enum(..., native_enum=False)` ou `sa.String`, conforme o que as migrations existentes já fazem — a suíte de testes cria o schema via `SQLModel.metadata.create_all()` contra SQLite em memória (ver o comentário em `user_type.py` sobre `ARRAY` não compilar em SQLite), então nada específico de Postgres.

---

## Elegibilidade e adimplência — regras exatas

Guard de service layer, seguindo o padrão de `_assert_gatekeeper_access` em `access_logs.py`.

`_assert_can_cast(user, vote, lot_id)` avalia **nesta ordem**, e **toda recusa grava uma linha em `BallotRejection` com `session.commit()` explícito antes de levantar o erro** — mesmo padrão de `visitor_service.py` para expirar-e-recusar: se só desse `session.add` e a request abortasse depois, a linha de recusa sumiria com o rollback:

1. **Janela** — `vote.status == OPEN` e `opens_at <= now < closes_at`; **se `kind == ASSEMBLEIA`, também `vote.assembly.status == AssemblyStatus.OPEN`** (uma votação pode estar com `status == OPEN` mas pertencer a uma `Assembly` ainda em `DRAFT` — ver "Semântica de `Assembly.status`" — e nesse caso nenhuma cédula é aceita). Senão `VOTE_NOT_OPEN`.
2. **Papel** — `user.role` não pode ser `GUEST` nem `PORTEIRO`, em nenhuma das duas modalidades. Senão `ROLE_FORBIDDEN`.
3. **Se `kind == ASSEMBLEIA` e `is_retraction == False`** (votar/trocar):
   - `lot_id` é obrigatório no corpo da requisição.
   - `lot.is_deleted == False`. Senão `NOT_OWNER`.
   - O usuário está no **conjunto elegível do lote** (ver subseção abaixo). Senão `NOT_OWNER`. **Checar antes da adimplência** — quem nem é elegível não deve ver um erro de inadimplência, só de "não é elegível".
   - **`lot.is_delinquent == False`. Senão `DELINQUENT_LOT`.**
   - **Trava por lote** (ver subseção "Um voto por lote, vários elegíveis" abaixo). Se já existe cédula ativa de OUTRO elegível para este lote nesta votação, recusa com `LOT_ALREADY_VOTED`.
   - `voter_key = f"lot:{lot_id}"`, `fraction_ideal_at_cast = lot.fraction_ideal`.
3b. **Se `kind == ASSEMBLEIA` e `is_retraction == True`** (`POST /{id}/ballots/retract`, corpo `BallotRetract{lot_id: UUID}`) — **cadeia deliberadamente mais curta**, ver "Retirada não reavalia elegibilidade" abaixo:
   - `lot_id` é **obrigatório no corpo** desta chamada também — um usuário pode deter cédulas ativas em mais de um lote na mesma votação (ver "Um proprietário, vários lotes"), então a retirada precisa dizer qual. **`BallotRetract` não é um corpo vazio** (correção de uma versão anterior desta spec, que dizia "corpo vazio" — estava errada): carrega exatamente `lot_id`.
   - `get_active_ballot_holder(vote, lot_id)` precisa ser o próprio `user`. Se não houver cédula ativa nenhuma para o lote → `NoActiveBallotError` (`404`). Se houver, mas de outro elegível → `LotAlreadyVotedError` (`403`).
   - **Não reavalia** `lot.is_deleted`, conjunto elegível nem `is_delinquent` — quem já detém a cédula pode sempre retirá-la, mesmo que tenha perdido elegibilidade depois de votar (ver justificativa abaixo). Ainda passa pelas checagens 1 (Janela) e 2 (Papel) no topo.
4. **Se `kind == ENQUETE` e `is_retraction == False`** (votar/trocar):
   - Existe algum `UserLotLink` ativo para o usuário, de **qualquer** `association_type` — inclusive `INQUILINO`. Senão `NO_ACTIVE_LOT_LINK`.
   - Sem checagem de adimplência.
   - `voter_key = f"user:{user.id}"`, `lot_id` e `fraction_ideal_at_cast` ficam nulos.
4b. **Se `kind == ENQUETE` e `is_retraction == True`** (`POST /{id}/ballots/retract`, corpo `BallotRetract{lot_id: None}` — `lot_id` deve vir nulo/ausente, é rejeitado com `422` se vier preenchido numa votação `ENQUETE`) — mais simples que 3b porque `voter_key = user:<id>` já é exclusivo do próprio usuário, não existe conceito de "detentora" diferente de quem pergunta:
   - Existe alguma linha para `voter_key = f"user:{user.id}"` cuja última entrada (por `cast_at`) **não** é `is_retraction=True`. Senão (nunca votou, ou já retirou) → `NoActiveBallotError` (`404`).
   - **Não reavalia** `NO_ACTIVE_LOT_LINK` — mesma justificativa da 3b: quem já votou pode sempre retirar o próprio voto, mesmo tendo perdido o vínculo ao lote depois (ex: inquilino que já se mudou). Ainda passa pelas checagens 1 (Janela) e 2 (Papel) no topo.

### Conjunto elegível do lote (`ASSEMBLEIA`)

⚠️ **Adicionado após revisão do usuário** (não estava na primeira versão desta spec): elegível para votar por um lote em assembleia é a **união** de:

1. Todo `UserLotLink` ativo com `association_type == PROPRIETARIO` para aquele lote — **cobre co-propriedade automaticamente**: o modelo já permite mais de um `PROPRIETARIO` por lote (sem constraint que limite a um só), então dois donos do mesmo lote já caem aqui sem nenhuma estrutura nova.
2. Toda entrada em `LotVoterEligibility` para aquele lote (cadastro manual, para gente que representa o lote mas não está registrada como `PROPRIETARIO` no sistema — ex: cônjuge, por documento que o APRAS não verifica).

Editar `LotVoterEligibility` (adicionar/remover elegível extra de um lote): `ADMINISTRATOR`, `DIRECTOR`, **`MANAGER`**.

### Um voto por lote, vários elegíveis — mecânica de posse e retirada

⚠️ **Adicionado após revisão do usuário.** O voto continua sendo **um por lote** (não um por pessoa do conjunto elegível), mas mais de uma pessoa pode ter o direito de lançá-lo. A mecânica:

- **Ninguém do conjunto votou ainda para esta votação** → qualquer elegível do lote pode lançar a primeira cédula. Essa pessoa passa a ser a **detentora** da cédula ativa do lote.
- **Alguém já votou** → só a **detentora** pode trocar a opção escolhida (nova linha, `is_retraction=False`) ou **retirar o voto** (nova linha, `is_retraction=True`, sem opções). Qualquer outro elegível do lote que tentar votar recebe `403 LOT_ALREADY_VOTED` — grava `BallotRejection` como qualquer outra recusa.
- **Depois de retirada** → a última linha do `voter_key` do lote é `is_retraction=True`, então o lote está **sem cédula ativa**, e **qualquer** elegível do lote (inclusive quem retirou) pode lançar a próxima, tornando-se a nova detentora.
- "Detentora" é lida dinamicamente: é `voter_user_id` da última linha não-retratada daquele `voter_key`. Não existe coluna separada de "dono da cédula" — cai direto de `get_latest_ballots`.

Isso não muda a contagem: a apuração por lote (`voter_key = lot:<id>`) continua contando 1 por lote, é só que agora "quem pode lançar/trocar/retirar aquele 1 voto" é um conjunto de pessoas em vez de uma só.

### Retirada não reavalia elegibilidade — por quê

⚠️ **Adicionado após review: sem isso, o lote trava.** Se a detentora perde elegibilidade **depois** de votar (deixa de ser `PROPRIETARIO`, é removida de `LotVoterEligibility`, ou — em enquete — seu `UserLotLink` expira) e a cadeia de retirada reavaliasse "conjunto elegível" como a cadeia de voto reavalia, ela não conseguiria mais nem retirar o próprio voto (falha na checagem de elegibilidade) nem ninguém mais conseguiria votar por aquele lote (`LOT_ALREADY_VOTED` ainda aponta pra ela) — o lote fica travado pelo resto da janela, sem saída, sem endpoint de admin para forçar a liberação.

Por isso as checagens 3b e 4b são deliberadamente mais curtas que 3 e 4: **retirar o próprio voto não exige continuar elegível**, nem em assembleia nem em enquete. Quem já votou pode sempre tirar o próprio voto do jogo — não é um novo ato de representar o lote (ou de participar), é o oposto, é abrir mão dele. Isso não abre brecha: em `ASSEMBLEIA` só afeta quem **já era** a detentora (identidade verificada via `get_active_ballot_holder`), nunca um terceiro qualquer; em `ENQUETE` o `voter_key` já é exclusivo do próprio usuário, então a mesma garantia vem de graça.

### Momento da validação

A adimplência é verificada **no ato de cada voto**, não em snapshot na abertura. Isso é a regra do Art. 1.335, III do Código Civil — o direito de voto fica suspenso *enquanto* o condômino está em débito, e é restaurado quando quita.

Consequências, que caem todas da mesma regra e **não são exceções codificadas**:

- Votou adimplente e depois ficou inadimplente → o voto original **permanece válido e apurado**, mas a tentativa de troca é recusada, porque trocar é um novo ato de votar e passa pela mesma validação.
- Estava inadimplente e quitou durante a janela → passa a poder votar normalmente.

⚠️ **diverge do scope doc:** o esboço da seção 4 do scope doc previa "qualquer autenticado com standing de `RESIDENT`". Isso é juridicamente errado: **inquilino não vota em assembleia**. A modalidade `ENQUETE` é onde o inquilino participa.

### Um proprietário, vários lotes

Cai naturalmente do `voter_key`: um elegível de dois lotes (dono de ambos, ou dono de um e `LotVoterEligibility` no outro) tem duas cédulas possíveis, `lot:<A>` e `lot:<B>`, e conta até 2 na apuração — uma por lote em que ele efetivamente detém a cédula ativa. Nenhuma regra especial além da mecânica de posse já descrita.

---

## RBAC — regras exatas por ação

| Ação | Papéis |
|---|---|
| Criar / editar / fechar `Assembly` | `ADMINISTRATOR`, `DIRECTOR` |
| Criar votação com `kind == ASSEMBLEIA` | `ADMINISTRATOR`, `DIRECTOR` |
| Criar votação com `kind == ENQUETE` | `ADMINISTRATOR`, `DIRECTOR`, `MANAGER` |
| Editar votação | Mesmos da criação, **e só enquanto não houver nenhuma cédula**. Depois da primeira, a votação está congelada — resta fechar antecipadamente. |
| Fechar votação antecipadamente | Mesmos da criação |
| Votar em `ASSEMBLEIA` | Conjunto elegível do lote — `PROPRIETARIO` ativo ∪ `LotVoterEligibility` (ver Elegibilidade) |
| Votar em `ENQUETE` | Qualquer vínculo ativo a lote, inclusive `INQUILINO` |
| Ver apuração | Quem podia votar + `ADMINISTRATOR`/`DIRECTOR`/**`MANAGER`** — **só após o fechamento** |
| Ver contagem de participação | Os mesmos, a qualquer momento |
| Ver o próprio voto | O próprio votante, sempre (ver Visibilidade, Regra 3, para a extensão a outros elegíveis do mesmo lote) |
| Alterar `Lot.is_delinquent` | `ADMINISTRATOR`, `DIRECTOR` |
| Editar `LotVoterEligibility` (elegível extra do lote) | `ADMINISTRATOR`, `DIRECTOR`, `MANAGER` |
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

### Regra 3 — o próprio voto e o voto de quem divide o lote

O votante sempre enxerga a própria cédula, aberta ou fechada, via endpoint dedicado. É necessário para poder trocar/retirar o voto, e não é vazamento.

⚠️ **Adicionado após revisão do usuário:** essa visibilidade se estende a **outros elegíveis do mesmo lote**, a qualquer momento (mesmo com a votação aberta) — transparência de "quem mora junto":

- **`ASSEMBLEIA`**: trivial — o voto já é do lote, um único registro. Qualquer elegível do conjunto do lote (ver Elegibilidade) enxerga a cédula ativa via `GET /votes/{id}/my-ballot`, mesmo não tendo sido quem a lançou. Só a **detentora** (quem lançou a cédula ativa) pode trocar ou retirar.
- **`ENQUETE`, `is_anonymous == False`**: cada pessoa vota individualmente (`voter_key = user:<id>`), mas qualquer morador (`UserLotLink` ativo) do **mesmo lote** de outro votante consegue ver o voto individual dele, mesmo antes do fechamento — não só o próprio. Só quem lançou aquela cédula específica pode trocá-la.
- **`ENQUETE`, `is_anonymous == True`**: **não se aplica** — a Regra 2 (mascaramento no serializer) prevalece. Ninguém, nem morador do mesmo lote, vê a identidade por trás de um voto anônimo; só o próprio votante vê a própria cédula.

Endpoint: `GET /votes/{id}/my-ballot` deixa de ser "só a minha", vira "a cédula que eu tenho direito de ver" — em `ASSEMBLEIA` é a cédula ativa do(s) lote(s) em que sou elegível; em `ENQUETE` não anônima é a lista de cédulas de quem divide lote comigo (incluindo a minha); em `ENQUETE` anônima é só a minha.

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

Conteúdo do snapshot: contagem por opção, total de votantes, e a lista atribuída (omitida quando enquete anônima). **Denominador só existe em `ASSEMBLEIA`.**

**`ASSEMBLEIA` — denominador = total de lotes com `is_deleted == False`.** Com validação no ato, não existe "lista de aptos" no fechamento — a elegibilidade foi móvel a votação inteira. A apuração reporta "22 votos de 40 lotes"; inadimplência governa quem conseguiu votar, não o denominador.

⚠️ **Adicionado após revisão do usuário: `ENQUETE` não tem denominador.** A primeira versão desta spec generalizava "total de lotes ativos" para as duas modalidades, mas isso não faz sentido em enquete — o voto é por pessoa, não por lote, e um lote pode ter 1 (o proprietário, sempre) ou vários moradores elegíveis (cônjuge, inquilino), então "contar lotes" não responde "de quantos". Calcular "total de pessoas elegíveis" (soma de `UserLotLink` ativos distintos) foi cogitado e descartado — não agrega valor suficiente para o custo de calcular. `TallyRead` de enquete só tem `voters_count`, sem denominador nenhum: "12 pessoas votaram", ponto.

---

## Backend Changes

### `backend/app/core/exceptions.py` — adicionar

`AssemblyNotFoundError`, `VoteNotFoundError`, `VoteNotOpenError`, `VoteAlreadyClosedError`, `VoteFrozenError` (edição após a primeira cédula), `DelinquentLotError`, `NotLotOwnerError`, `NoActiveLotLinkError`, `TallyNotAvailableError`, `AnonymousAssemblyError`, **`LotAlreadyVotedError`** (outro elegível já detém a cédula ativa do lote), **`NoActiveBallotError`** (`POST /{id}/ballots/retract` sem nenhuma cédula ativa do usuário para retirar — nunca votou, ou já retirou antes). Todas herdam `DomainError`, seguindo o formato das existentes.

### `backend/app/core/exception_handlers.py`

Mapear: `*NotFoundError` → `404`, incluindo `NoActiveBallotError`; `DelinquentLotError`, `NotLotOwnerError`, `NoActiveLotLinkError`, `TallyNotAvailableError`, `LotAlreadyVotedError` → `403`; `VoteNotOpenError`, `VoteAlreadyClosedError`, `VoteFrozenError`, `AnonymousAssemblyError` → `400`.

**Mapeamento exato de `POST /{id}/ballots/retract`** (a ambiguidade apontada no review): três casos, três respostas diferentes, iguais para `ASSEMBLEIA` (regra 3b) e `ENQUETE` (regra 4b) —
- Ninguém do `voter_key` do usuário (o lote informado, em `ASSEMBLEIA`; o próprio usuário, em `ENQUETE`) tem cédula ativa (nunca votou, ou a última já é retirada) → `NoActiveBallotError`, `404`.
- `ASSEMBLEIA` apenas: existe cédula ativa do lote, mas de **outro** elegível (não é o usuário quem detém) → `LotAlreadyVotedError`, `403`. Não existe equivalente em `ENQUETE`, já que `voter_key = user:<id>` nunca é compartilhado.
- Papel proibido (`GUEST`/`PORTEIRO`) ou janela fechada → `ROLE_FORBIDDEN`/`VOTE_NOT_OPEN` como em qualquer outra ação, `400`/`403` conforme o mapeamento já existente. Essas duas checagens (1 e 2 da cadeia) rodam **antes** das duas acima, então janela fechada vence sobre "sem cédula ativa" se ambas seriam verdade.

### `backend/app/schemas/voting.py` (arquivo novo)

`AssemblyCreate/Update/Read`, `VoteCreate/Update/Read`, `VoteOptionCreate/Read`, `LotVoterEligibilityCreate/Read`, `BallotCreate` (`lot_id: UUID | None`, `selected_option_ids: list[UUID]`), `BallotRetract` (**`lot_id: UUID | None`** — obrigatório e deve apontar para um lote em que o usuário detém cédula ativa quando `kind == ASSEMBLEIA`; deve vir nulo/ausente quando `kind == ENQUETE`, `422` se vier preenchido nesse caso), `BallotRead` (inclui `is_retraction`), `MyBallotRead`, `TallyRead`.

`MyBallotRead` — schema de resposta de `GET /votes/{id}/my-ballot`, **uma lista de `BallotRead`**, não um objeto único: em `ASSEMBLEIA` traz a cédula ativa do(s) lote(s) em que o usuário é elegível (0 ou 1 por lote, já que só existe uma cédula ativa por lote); em `ENQUETE` não anônima traz a própria cédula **e** a de quem mais divide algum lote com o usuário; em `ENQUETE` anônima traz só a própria. Cada item tem um campo `can_edit: bool` calculado pelo service (verdadeiro só para quem detém aquela cédula especificamente).

`TallyRead` é **um schema com dois modos**, e o service escolhe qual preencher:

- votação aberta → `status`, `voters_count`, `total_lots` (**só presente quando `kind == ASSEMBLEIA`**, ausente em `ENQUETE`); `results` e `attributions` **ausentes**.
- votação fechada → `voters_count` e (só `ASSEMBLEIA`) `total_lots` **continuam presentes** — fechar não os remove, só acrescenta `results` (por opção) e `attributions` (omitido em enquete anônima).

`MULTIPLE_CHOICE` valida `len(selected_option_ids) >= 1`; `SINGLE_CHOICE` valida `== 1`. Todos os ids têm que pertencer à votação. Não se aplica a uma retirada (`BallotRetract` não carrega opções).

### `backend/app/services/voting_service.py` (arquivo novo)

- `_assert_board(user)` — Administrator/Director.
- `_assert_can_create_vote(user, kind)` — inclui Manager quando `ENQUETE`.
- `_assert_can_view_tally(user, vote)` — quem podia votar + Administrator/Director/Manager (ver RBAC).
- `get_lot_eligible_user_ids(lot)` — união de `UserLotLink` ativo com `association_type == PROPRIETARIO` e `LotVoterEligibility` do lote. Usado tanto por `_assert_can_cast` quanto pela Regra 3 de visibilidade.
- `get_active_ballot_holder(vote, lot_id)` — `voter_user_id` da última linha do `voter_key` do lote, ordenando por `cast_at` e desempatando por `id` (mesmo critério do docstring de `Ballot`), ou `None` se não existe nenhuma linha ou a última é `is_retraction=True`. Base da trava por lote (regra 3) e da autorização de retirada (regra 3b) — os dois call sites usam exatamente esta função, não reimplementam a ordenação cada um a seu modo.
- `_assert_can_cast(user, vote, lot_id, *, is_retraction=False)` — a cadeia da seção Elegibilidade, incluindo a trava por lote via `get_active_ballot_holder`, gravando `BallotRejection` (com commit explícito) em toda recusa.
- `cast_ballot(...)` — sempre `INSERT`, nunca `UPDATE`; aceita `is_retraction` para a linha de retirada.
- `get_latest_ballots(vote)` — última linha por `voter_key`, filtrando fora as `is_retraction=True` (essas representam "sem voto ativo", não contam).
- `get_my_ballots(user, vote)` — implementa a Regra 3 estendida: monta a lista de `MyBallotRead` conforme `kind`/`is_anonymous`, calculando `can_edit` por item.
- `compute_tally(vote)` / `materialize_snapshot(vote)` — denominador só para `ASSEMBLEIA`.
- `render_minutes_html(assembly)`.
- `set_lot_voter_eligibility(lot, user, added_by)` / `remove_lot_voter_eligibility(...)`.

### `backend/app/api/v1/endpoints/voting.py` (arquivo novo)

Dois routers no mesmo módulo, como `reservations.py` já faz com `spaces_router`/`reservations_router`.

`assemblies_router`:
- `POST /` · `GET /` · `GET /{id}` · `PATCH /{id}` (bloqueado depois de `status == CLOSED`, mesma lógica do congelamento de votação) · `POST /{id}/close`
- `GET /{id}/minutes` → HTML da minuta
- `POST /{id}/minutes/save` → grava no Document Center

`votes_router`:
- `POST /` · `GET /` (filtros `kind`, `status`, `assembly_id`) · `GET /{id}` · `PATCH /{id}` · `POST /{id}/close`
- `POST /{id}/ballots` → votar ou trocar voto (corpo `BallotCreate`)
- `POST /{id}/ballots/retract` → retirar a cédula ativa que o usuário detém (corpo `BallotRetract{lot_id}` — obrigatório em `ASSEMBLEIA`, nulo em `ENQUETE`, ver schemas) — mapeamento exato de erros em Backend Changes → exceptions (`NoActiveBallotError` 404 / `LotAlreadyVotedError` 403, este último só em `ASSEMBLEIA`)
- `GET /{id}/my-ballot` → lista conforme a Regra 3 estendida (ver Backend Changes → schemas)
- `GET /{id}/tally` → contagem se aberta, apuração se fechada

**Materialização preguiçosa (ver Fechamento e snapshot) fica restrita a `GET /{id}` e `GET /{id}/tally`** — não dispara em `GET /` (listagem), para não gravar N snapshots numa única chamada de lista.

### `backend/app/api/v1/endpoints/lots.py`

- `PATCH /lots/{id}/delinquency` (Administrator/Director) — altera `is_delinquent` e carimba `delinquency_updated_at` / `delinquency_updated_by_id`. Endpoint dedicado, não campo no `PATCH /lots/{id}` genérico, porque é ele que barra voto e merece superfície própria.
- `POST /lots/{id}/voter-eligibility` / `DELETE /lots/{id}/voter-eligibility/{user_id}` (Administrator/Director/Manager) — gerencia `LotVoterEligibility`.

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

**Salvamento — mecanismo exato** (não estava especificado na primeira versão desta spec, corrigido após review): `POST /assemblies/{id}/minutes/save` (sem corpo) segue o mesmo caminho que `media_service.py` já usa para persistir conteúdo gerado no servidor:

1. `render_minutes_html(assembly)` gera a string HTML.
2. Grava os bytes via `storage_service` (o mesmo `LocalStorageProvider.save_file` que `media_service.py` usa) — recebe de volta `(file_path, url)`, não um par `(file_url, file_size_bytes)`; `file_size_bytes` é `len()` dos bytes do HTML, calculado à parte, mesmo padrão de `media_service.py:125`. Não inventar um mecanismo de storage novo.
3. `folder_id`: `AssociationDocumentCreate.folder_id` é obrigatório e não existe convenção de pasta padrão hoje. Resolver com find-or-create: procurar (ou, na primeira vez, criar via `document_service.create_folder`) uma pasta de nome fixo `"Atas de Assembleia"` na raiz do Document Center, e usar o `id` dela. Não expor escolha de pasta ao usuário nesta task — é sempre essa.
4. Cria o `AssociationDocument` com `mime_type = "text/html"`, `file_url = url` (o segundo item da tupla do passo 2) e `file_size_bytes` (calculado no passo 2), `folder_id` do passo 3.

`AssociationDocument` já tem versionamento via `previous_version_id`, então o síndico pode subir a versão final assinada como nova versão do mesmo documento (fora desta task — a UI de upload de nova versão já existe no Document Center).

---

## Frontend Changes

- `frontend/src/types/voting.ts` — tipos espelhando os schemas.
- `frontend/src/api/voting.ts` — cliente.
- `frontend/src/features/assembly-voting/` — nova feature, seguindo a estrutura de `space-reservation-management/`:
  - lista de assembleias e enquetes;
  - criação de assembleia e de votação (Administrator/Director; Manager só enquete);
  - gestão de `LotVoterEligibility` por lote (Administrator/Director/Manager) — tela simples de adicionar/remover elegível extra, na área de gestão de lotes ou dentro da própria feature de votação;
  - tela de votação com as opções; quando o lote/usuário já tem cédula ativa, mostra quem votou (se `can_edit == true`, botões de trocar e **retirar voto**; se `can_edit == false` mas o usuário é elegível do mesmo lote, mostra o voto em modo leitura com aviso "votado por [nome], você também pode votar se ele retirar");
  - tela de apuração, que durante a janela mostra **apenas** a contagem de votantes, sem denominador em enquete;
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
- Procuração / voto por representante formal (documento de poderes para uma assembleia específica, por terceiro que não mora no lote). `LotVoterEligibility` é diferente: uma designação permanente de quem, dentro do próprio lote, pode representar o voto daquela unidade (ex: cônjuge) — não substitui procuração para casos como "meu advogado vota por mim nesta AGE".
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
2. Detentora da cédula ativa de um lote troca a opção escolhida (nova linha, mesmo `voter_key`); a apuração conta 1 e considera a cédula mais recente não-retratada.
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
13. **Lote com dois `PROPRIETARIO`** (co-propriedade, sem `LotVoterEligibility`): o segundo dono vota primeiro; o primeiro dono tentando votar depois recebe `403 LOT_ALREADY_VOTED`, gravando `BallotRejection`.
14. **`LotVoterEligibility`**: usuário adicionado manualmente (não `PROPRIETARIO`) consegue votar pelo lote; removido da lista, um voto seu anterior permanece na apuração, mas uma nova tentativa de voto é recusada com `NOT_OWNER`.
15. **Retirada libera o lote**: A vota pelo lote → A retira o voto (`POST /{id}/ballots/retract`) → B, outro elegível do mesmo lote, consegue votar em seguida. A tentando trocar ou retirar de novo depois de já ter retirado (sem votar de novo) recebe `404 NoActiveBallotError` (não tem mais cédula ativa nenhuma). A tentando votar de novo pelo lote depois que B já votou recebe `403 LotAlreadyVotedError`.
15b. **Retirada não reavalia elegibilidade**: A vota pelo lote enquanto é `PROPRIETARIO` → A é removida do `UserLotLink` (ou de `LotVoterEligibility`, no caso de elegível extra) → A ainda consegue `POST /{id}/ballots/retract` com sucesso (o voto original permanece na apuração até a retirada, depois some da contagem) → depois da retirada, outro elegível do lote consegue votar normalmente. Sem essa exceção, o lote ficaria travado — este é o teste que prova que a trava não é permanente.
16. **`GET /votes/{id}/my-ballot`**: para `ASSEMBLEIA`, um segundo elegível do mesmo lote (que não votou) recebe a cédula ativa lançada pelo primeiro, com `can_edit=False`; para `ENQUETE` não anônima, um morador vê a lista incluindo o voto de outro morador do mesmo lote, também com `can_edit=False` no item alheio; para `ENQUETE` anônima, só o próprio item aparece.
17. `MANAGER` sem nenhum vínculo a lote consegue `GET /votes/{id}/tally` e ver a contagem de uma `ENQUETE` que criou (mesmo antes do fechamento) e a apuração completa de uma `ASSEMBLEIA` (depois do fechamento).
18. `ENQUETE` fechada: `TallyRead` não tem campo de denominador/`total_lots` (só `voters_count` e `results`).
19. **Retirada em `ENQUETE`**: usuário vota → `POST /{id}/ballots/retract` com `lot_id=null` retira com sucesso, apuração deixa de contá-lo; tentando retirar de novo (sem votar antes) recebe `404 NoActiveBallotError`; enviar `lot_id` preenchido numa votação `ENQUETE` devolve `422`. Depois de retirar, um inquilino que perdeu o `UserLotLink` (mudou-se) ainda consegue essa retirada — prova que 4b não reavalia `NO_ACTIVE_LOT_LINK`, espelhando o teste 15b para assembleia.
20. **Retirada em lote errado (multi-lote)**: usuário elegível em dois lotes vota nos dois; `POST /{id}/ballots/retract` com `lot_id` do lote A retira só a cédula de A — a de B permanece ativa e contando na apuração.

Complementares: `PATCH` em votação com cédula existente devolve `400` (`VoteFrozenError`); `PATCH` em `Assembly` com `status == CLOSED` devolve `400`; criar votação de assembleia com `is_anonymous=True` devolve `400`; votar numa assembleia em `DRAFT` devolve `400` mesmo com a janela da votação aberta; `POST /assemblies/{id}/close` fecha em cascata as votações abertas e materializa o snapshot de cada uma; `GET /{id}/minutes` antes do fechamento devolve `400`; janela fechada some com `VOTE_NOT_OPEN` mesmo quando o usuário também não tem cédula ativa (checagem 1 vence sobre `NoActiveBallotError`); a materialização preguiçosa não dispara em `GET /votes/` (listagem), só em `GET /{id}` e `GET /{id}/tally`.

**Frontend**

Testes de componente para: a tela de apuração não renderizar resultado por opção com a votação aberta; a tela de apuração de enquete não renderizar denominador; o botão de trocar/retirar voto aparecer só para quem detém a cédula (`can_edit=True`) e só dentro da janela; um segundo elegível do mesmo lote ver o voto em modo leitura quando `can_edit=False`; a rota ser inacessível a `PORTEIRO` e `GUEST`.

---

## Expected Results

1. Administrator/Director cria uma assembleia (AGO/AGE) com N votações de pauta, e cada votação aceita exatamente um voto por lote.
2. Elegível de dois lotes (dono de ambos, ou dono de um e cadastrado via `LotVoterEligibility` no outro) vota nos dois, uma cédula por lote, e a apuração conta os dois.
3. Lote marcado como inadimplente é impedido de votar no momento do voto, com a recusa registrada e visível na minuta; se quitar durante a janela, passa a votar.
4. Com a votação aberta, o endpoint de apuração devolve apenas a contagem de votantes para qualquer papel, incluindo Administrator, e em `ENQUETE` sem denominador; o resultado por opção só aparece depois do fechamento.
5. Enquete com anonimato ligado não devolve identificação do votante na resposta da API nem depois de fechar, e o votante continua vendo o próprio voto.
6. Um lote com mais de um elegível (co-proprietários, ou proprietário + `LotVoterEligibility`) tem exatamente um voto ativo por vez: qualquer elegível pode lançar o primeiro; depois disso, só quem lançou pode trocar ou retirar; a retirada libera o lote para qualquer elegível votar de novo; qualquer elegível do lote enxerga a cédula ativa mesmo sem ser quem a lançou.
7. Em `ENQUETE` não anônima, moradores do mesmo lote enxergam o voto individual uns dos outros (não só o próprio), mesmo com a votação aberta; em `ENQUETE` anônima, ninguém vê a identidade de ninguém, nem morador do mesmo lote.
8. `MANAGER` vê apuração e contagem de participação nas duas modalidades, mesmo sem vínculo a nenhum lote.
9. A minuta da assembleia é gerada em HTML com resultado por pauta, atribuição por Bloco/Lote, denominador de lotes ativos e lista de lotes barrados por inadimplência, e é salva no Document Center numa pasta "Atas de Assembleia" criada automaticamente na primeira vez.
