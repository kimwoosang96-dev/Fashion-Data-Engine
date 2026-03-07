"""add channel poll priority

Revision ID: f6a7b8c9d0e1
Revises: c3e4f5a6b7d8
Create Date: 2026-03-08 01:20:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "c3e4f5a6b7d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "channels",
        sa.Column("poll_priority", sa.Integer(), nullable=False, server_default="2"),
    )
    op.create_index("ix_channels_poll_priority", "channels", ["poll_priority"], unique=False)
    op.execute("UPDATE channels SET poll_priority = 2 WHERE poll_priority IS NULL")
    op.alter_column("channels", "poll_priority", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_channels_poll_priority", table_name="channels")
    op.drop_column("channels", "poll_priority")
