"""add normalized_key, match_confidence to products and platform to channels

Revision ID: a1b2c3d4e5f6
Revises: f1d2c3b4a5d6
Create Date: 2026-03-01 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "f1d2c3b4a5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # products: normalized_key (교차채널 매칭용)
    op.add_column("products", sa.Column("normalized_key", sa.String(300), nullable=True))
    op.create_index("ix_products_normalized_key", "products", ["normalized_key"])

    # products: match_confidence (normalized_key 신뢰도)
    op.add_column("products", sa.Column("match_confidence", sa.Float(), nullable=True))

    # channels: platform (shopify / cafe24 / custom)
    op.add_column("channels", sa.Column("platform", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_index("ix_products_normalized_key", table_name="products")
    op.drop_column("products", "normalized_key")
    op.drop_column("products", "match_confidence")
    op.drop_column("channels", "platform")
