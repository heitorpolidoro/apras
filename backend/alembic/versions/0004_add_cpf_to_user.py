"""add_cpf_to_user

Revision ID: 0004_add_cpf_to_user
Revises: 3f75bcd3d49f
Create Date: 2026-08-10 17:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0004_add_cpf_to_user"
down_revision: Union[str, Sequence[str], None] = "3f75bcd3d49f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def generate_valid_cpf(seq: int) -> str:
    """Generate a mathematically valid 11-digit CPF for a given integer sequence."""
    base = f"{seq:09d}"
    total1 = sum(int(base[i]) * (10 - i) for i in range(9))
    d1 = 0 if (total1 % 11) < 2 else 11 - (total1 % 11)

    base_d1 = base + str(d1)
    total2 = sum(int(base_d1[i]) * (11 - i) for i in range(10))
    d2 = 0 if (total2 % 11) < 2 else 11 - (total2 % 11)

    return f"{base}{d1}{d2}"


def upgrade() -> None:
    # 1. Add cpf column as nullable
    op.add_column("user", sa.Column("cpf", sa.String(), nullable=True))

    # 2. Fetch all existing users and assign a unique valid CPF
    conn = op.get_bind()
    results = conn.execute(sa.text('SELECT id FROM "user" ORDER BY id')).fetchall()

    for idx, row in enumerate(results, start=1):
        cpf_val = generate_valid_cpf(idx)
        user_id = str(row[0])
        conn.execute(
            sa.text('UPDATE "user" SET cpf = :cpf WHERE id = :id'),
            {"cpf": cpf_val, "id": user_id},
        )

    # 3. Alter column to NOT NULL, create index and unique constraint
    op.alter_column("user", "cpf", nullable=False)
    op.create_index(op.f("ix_user_cpf"), "user", ["cpf"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_user_cpf"), table_name="user")
    op.drop_column("user", "cpf")
