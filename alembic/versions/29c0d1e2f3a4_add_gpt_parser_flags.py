"""add gpt parser flags

Revision ID: 29c0d1e2f3a4
Revises: 18b9c0d1e2f3
Create Date: 2026-03-08 01:40:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "29c0d1e2f3a4"
down_revision: Union[str, Sequence[str], None] = "18b9c0d1e2f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "channels",
        sa.Column("use_gpt_parser", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("channels", "use_gpt_parser", server_default=None)


def downgrade() -> None:
    op.drop_column("channels", "use_gpt_parser")
