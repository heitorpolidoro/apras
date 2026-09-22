"""purchase line items

The priced line stops belonging to the **quote** and starts belonging to the
**request** (APRAS-73). Two new tables -- ``purchase_request_item``, the
enumeration whoever opens the purchase writes, and ``purchase_quote_item``,
one supplier's price for one line -- then every existing quote is folded into
exactly one quote-owned line, and ``purchase_quote.unit_price`` and
``purchase_quote.quantity`` are dropped. A quote's total is derived from its
own lines from here on; two sources of truth for one total is the defect this
revision exists to delete.

This is an **ordinary new revision on top of** ``0003_tenant_invitation``,
not an edit of ``0001_initial_schema``. Declaring a change inside ``0001`` was
the rule only while ``0001`` had never been applied anywhere; production
applied it on 2026-09-19 (APRAS-59), so editing it now would put the deployed
database out of step with its own history.

It chains onto ``0003_tenant_invitation``, which is the real Alembic head **in
git** (APRAS-71, commit ``f599012``) -- the committed module no other
committed module names as its ``down_revision``. D12's reconciliation rule
says to re-read the head, and the head that matters for a revision about to be
committed is the one the history will actually replay, not whatever an
untracked file in a neighbouring task's worktree happens to declare. APRAS-68's
``0004_tenant_brand_theme`` is still in flight and unversioned, so chaining
onto it would commit a ``down_revision`` naming a revision that does not exist
and ``alembic upgrade head`` would die on ``Can't locate revision`` for
everyone who checked the commit out.

The number therefore has a gap: this is ``0005`` on ``0003``. Deliberate and
harmless -- Alembic orders by ``down_revision``, never by the digits in a slug
-- and the gap is kept rather than closed so the id cannot collide with
APRAS-68's file while both are in flight. Whichever of the two lands second
renumbers **its own** file and re-points **its own** ``down_revision``. The
committed history is the line ``0001 -> 0002 -> 0003 -> 0005``.

``revision`` is 24 characters. ``alembic_version.version_num`` is
``VARCHAR(32)``, and a longer slug fails on the first real ``upgrade`` rather
than at import time -- which is how the retired ``0037`` learnt it.

This file imports **nothing** from ``app/``: a revision is replayed verbatim
against production years from now, so a live import silently rewrites what a
replay produces the day the imported code changes. The one helper it needs --
the description of a folded line -- is spelled inline as frozen SQL rather
than imported, exactly as ``0002_tenant_slug`` carries its own copy of the
slug derivation.

Revision ID: 0005_purchase_line_items
Revises: 0003_tenant_invitation
Create Date: 2026-09-22 11:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '0005_purchase_line_items'
down_revision: Union[str, Sequence[str], None] = '0003_tenant_invitation'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


#: The description a folded legacy quote gets, spelled as frozen SQL.
#:
#: ``purchase_request.title`` is an unbounded ``VARCHAR`` while
#: ``purchase_quote_item.description`` is capped at 255, so one over-long
#: production title would fail the ``INSERT ... SELECT`` mid-upgrade;
#: ``left(..., 255)`` is what makes the fold total. The ``COALESCE``/``NULLIF``
#: pair covers a request whose title is blank or whitespace-only, which the
#: column allows.
_FOLDED_DESCRIPTION = (
    "left(COALESCE(NULLIF(btrim(pr.title), ''), 'Item do orçamento'), 255)"
)


def upgrade() -> None:
    op.create_table(
        'purchase_request_item',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('purchase_request_id', sa.Uuid(), nullable=False),
        sa.Column('description', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ['purchase_request_id'], ['purchase_request.id'], ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_purchase_request_item_purchase_request_id'),
        'purchase_request_item',
        ['purchase_request_id'],
        unique=False,
    )

    op.create_table(
        'purchase_quote_item',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('quote_id', sa.Uuid(), nullable=False),
        sa.Column('request_item_id', sa.Uuid(), nullable=True),
        sa.Column('model', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('unit_price', sa.Numeric(12, 2), nullable=False),
        sa.Column('description', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('quantity', sa.Integer(), nullable=True),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['quote_id'], ['purchase_quote.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(
            ['request_item_id'], ['purchase_request_item.id'], ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('id'),
        # A quote prices each request line at most once. PostgreSQL does not
        # collide NULLs here, so one quote may still carry several extra lines.
        sa.UniqueConstraint(
            'quote_id',
            'request_item_id',
            name='uq_purchase_quote_item_quote_request_item',
        ),
    )
    op.create_index(
        op.f('ix_purchase_quote_item_quote_id'),
        'purchase_quote_item',
        ['quote_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_purchase_quote_item_request_item_id'),
        'purchase_quote_item',
        ['request_item_id'],
        unique=False,
    )

    # Fold every existing quote into exactly ONE quote-owned line, and create
    # **no** `purchase_request_item` row. Deliberate: the legacy schema records
    # no shared enumeration, only one free-form price per supplier, so
    # inventing a request line would force a quantity to be picked out of
    # quotes that may disagree and would silently change the suppliers'
    # totals. As a quote-owned extra line every legacy total is bit-identical
    # after this upgrade -- `quantize_money(unit_price * quantity)` is the
    # same product the old `_compute_total` computed -- so
    # `lowest_quote_total`, `selected_quote_total` and every recorded decision
    # keep the number they had.
    op.execute(
        sa.text(
            "INSERT INTO purchase_quote_item "  # noqa: S608  # `_FOLDED_DESCRIPTION` is a module literal in this frozen revision, never caller input
            "(id, quote_id, request_item_id, model, unit_price, description, "
            " quantity, position) "
            "SELECT gen_random_uuid(), q.id, NULL, NULL, q.unit_price, "
            f"       {_FOLDED_DESCRIPTION}, q.quantity, 0 "
            "FROM purchase_quote AS q "
            "JOIN purchase_request AS pr ON pr.id = q.purchase_request_id"
        )
    )

    op.drop_column('purchase_quote', 'unit_price')
    op.drop_column('purchase_quote', 'quantity')


def downgrade() -> None:
    """Roll back to the one-price quote -- **com perda de dados**.

    Esta volta é destrutiva e não há caminho para frente que a desfaça.
    Cada orçamento é reconstruído a partir de **uma única** linha, a de menor
    ``position``: as linhas ``1..N-1`` de todo orçamento com várias linhas são
    apagadas e o total daquele orçamento cai da soma das suas linhas para o
    valor da primeira delas (um orçamento de três linhas somando R$ 7.480,00
    volta como R$ 4.720,00). A enumeração de itens do pedido é destruída por
    inteiro. Quem precisar dos dados de volta tem de **restaurar um backup do
    banco anterior ao upgrade**.
    """
    op.add_column(
        'purchase_quote', sa.Column('unit_price', sa.Numeric(12, 2), nullable=True)
    )
    op.add_column('purchase_quote', sa.Column('quantity', sa.Integer(), nullable=True))

    # The lowest-`position` line of each quote (`id` as the tiebreak, the same
    # order the application reads them in), with `COALESCE(..., 0.00)` / 1 for
    # the quote that somehow has no line at all, so NOT NULL can be restored.
    op.execute(
        sa.text(
            "UPDATE purchase_quote AS q SET "
            "  unit_price = COALESCE(first_line.unit_price, 0.00), "
            "  quantity = COALESCE(first_line.quantity, 1) "
            "FROM ( "
            "  SELECT DISTINCT ON (qi.quote_id) qi.quote_id, qi.unit_price, "
            "         COALESCE(qi.quantity, ri.quantity, 1) AS quantity "
            "  FROM purchase_quote_item AS qi "
            "  LEFT JOIN purchase_request_item AS ri ON ri.id = qi.request_item_id "
            "  ORDER BY qi.quote_id, qi.position, qi.id "
            ") AS first_line "
            "WHERE first_line.quote_id = q.id"
        )
    )
    op.execute(
        sa.text(
            "UPDATE purchase_quote SET unit_price = 0.00 WHERE unit_price IS NULL"
        )
    )
    op.execute(sa.text("UPDATE purchase_quote SET quantity = 1 WHERE quantity IS NULL"))

    op.alter_column('purchase_quote', 'unit_price', nullable=False)
    op.alter_column('purchase_quote', 'quantity', nullable=False)

    op.drop_index(
        op.f('ix_purchase_quote_item_request_item_id'), table_name='purchase_quote_item'
    )
    op.drop_index(
        op.f('ix_purchase_quote_item_quote_id'), table_name='purchase_quote_item'
    )
    op.drop_table('purchase_quote_item')
    op.drop_index(
        op.f('ix_purchase_request_item_purchase_request_id'),
        table_name='purchase_request_item',
    )
    op.drop_table('purchase_request_item')
