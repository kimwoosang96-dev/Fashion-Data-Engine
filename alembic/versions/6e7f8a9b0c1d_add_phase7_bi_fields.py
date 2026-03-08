"""add phase7 bi fields

Revision ID: 6e7f8a9b0c1d
Revises: 5d6e7f8a9b0c
Create Date: 2026-03-09 00:40:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6e7f8a9b0c1d"
down_revision: Union[str, Sequence[str], None] = "5d6e7f8a9b0c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("products", sa.Column("size_scarcity", sa.Float(), nullable=True))
    op.add_column(
        "products",
        sa.Column("is_all_time_low", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("drops", sa.Column("expected_drop_at", sa.DateTime(), nullable=True))
    op.create_index(
        op.f("ix_products_is_all_time_low"),
        "products",
        ["is_all_time_low"],
        unique=False,
    )
    op.create_index(
        op.f("ix_drops_expected_drop_at"),
        "drops",
        ["expected_drop_at"],
        unique=False,
    )
    op.alter_column("products", "is_all_time_low", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_drops_expected_drop_at"), table_name="drops")
    op.drop_index(op.f("ix_products_is_all_time_low"), table_name="products")
    op.drop_column("drops", "expected_drop_at")
    op.drop_column("products", "is_all_time_low")
    op.drop_column("products", "size_scarcity")
