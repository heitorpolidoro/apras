"""Assembly voting and poll models (APRAS-33).

One module for the six models, following the `finance.py` precedent of
grouping a bounded context's tables together.
"""

from datetime import date, datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlalchemy import Index, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

from app.models.enums import (
    AssemblyStatus,
    AssemblyType,
    BallotRejectionReason,
    VoteKind,
    VoteStatus,
    VoteType,
)

if TYPE_CHECKING:
    from app.models.user import User


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
    """A single ballot question — an assembly agenda item or a standalone poll."""

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
    # service rejeita a criação com True.
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
    """One selectable answer of a `Vote`."""

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
        default=None,
        foreign_key="lot.id",
        ondelete="SET NULL",
        nullable=True,
        index=True,
    )
    # Quem efetivamente lançou ESTA linha (não é "o lote", é a pessoa). Em
    # ASSEMBLEIA, é quem detém a cédula ativa do lote enquanto ela não for
    # retirada — só essa pessoa pode trocar ou retirar.
    voter_user_id: UUID | None = Field(
        default=None,
        foreign_key="user.id",
        ondelete="SET NULL",
        nullable=True,
        index=True,
    )
    # Congela a fração ideal do lote no instante do voto. Voto ponderado não é
    # implementado no v1, mas fica recalculável depois mesmo que a fração mude.
    fraction_ideal_at_cast: float | None = Field(default=None, nullable=True)
    is_retraction: bool = Field(default=False, nullable=False)
    # Vazio/null quando is_retraction=True.
    selected_option_ids_json: str | None = Field(default=None, nullable=True)
    cast_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    vote: Vote = Relationship(back_populates="ballots")


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
        default=None,
        foreign_key="user.id",
        ondelete="SET NULL",
        nullable=True,
        index=True,
    )
    lot_id: UUID | None = Field(
        default=None,
        foreign_key="lot.id",
        ondelete="SET NULL",
        nullable=True,
        index=True,
    )
    reason: BallotRejectionReason = Field(nullable=False, index=True)
    attempted_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
