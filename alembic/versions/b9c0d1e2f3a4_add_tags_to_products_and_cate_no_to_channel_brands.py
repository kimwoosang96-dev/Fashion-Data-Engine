"""add tags to products and cate_no to channel_brands

Revision ID: b9c0d1e2f3a4
Revises: 8a58dd5a2358
Create Date: 2026-03-01 07:05:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b9c0d1e2f3a4"
down_revision: Union[str, Sequence[str], None] = "8a58dd5a2358"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("products", sa.Column("tags", sa.Text(), nullable=True))
    op.add_column("channel_brands", sa.Column("cate_no", sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column("channel_brands", "cate_no")
    op.drop_column("products", "tags")
