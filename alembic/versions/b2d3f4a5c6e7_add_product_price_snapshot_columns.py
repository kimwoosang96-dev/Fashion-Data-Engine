"""add product price snapshot columns

Revision ID: b2d3f4a5c6e7
Revises: f1a2b3c4d5e6
Create Date: 2026-03-08 00:50:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b2d3f4a5c6e7"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _backfill_sqlite() -> None:
    op.execute(
        """
        UPDATE products
        SET
            price_krw = (
                SELECT CAST(ph.price AS INTEGER)
                FROM price_history ph
                WHERE ph.product_id = products.id
                ORDER BY ph.crawled_at DESC
                LIMIT 1
            ),
            original_price_krw = (
                SELECT CAST(ph.original_price AS INTEGER)
                FROM price_history ph
                WHERE ph.product_id = products.id
                ORDER BY ph.crawled_at DESC
                LIMIT 1
            ),
            discount_rate = (
                SELECT ph.discount_rate
                FROM price_history ph
                WHERE ph.product_id = products.id
                ORDER BY ph.crawled_at DESC
                LIMIT 1
            ),
            currency = COALESCE((
                SELECT ph.currency
                FROM price_history ph
                WHERE ph.product_id = products.id
                ORDER BY ph.crawled_at DESC
                LIMIT 1
            ), 'KRW'),
            raw_price = (
                SELECT ph.price
                FROM price_history ph
                WHERE ph.product_id = products.id
                ORDER BY ph.crawled_at DESC
                LIMIT 1
            ),
            price_updated_at = (
                SELECT ph.crawled_at
                FROM price_history ph
                WHERE ph.product_id = products.id
                ORDER BY ph.crawled_at DESC
                LIMIT 1
            )
        WHERE EXISTS (
            SELECT 1
            FROM price_history ph
            WHERE ph.product_id = products.id
        )
        """
    )


def _backfill_postgresql() -> None:
    op.execute(
        """
        UPDATE products p
        SET
            price_krw = CAST(ph.price AS INTEGER),
            original_price_krw = CAST(ph.original_price AS INTEGER),
            discount_rate = ph.discount_rate,
            currency = COALESCE(ph.currency, 'KRW'),
            raw_price = ph.price,
            price_updated_at = ph.crawled_at
        FROM (
            SELECT DISTINCT ON (product_id)
                product_id,
                price,
                original_price,
                discount_rate,
                currency,
                crawled_at
            FROM price_history
            ORDER BY product_id, crawled_at DESC
        ) ph
        WHERE p.id = ph.product_id
        """
    )


def upgrade() -> None:
    op.add_column("products", sa.Column("price_krw", sa.Integer(), nullable=True))
    op.add_column("products", sa.Column("original_price_krw", sa.Integer(), nullable=True))
    op.add_column("products", sa.Column("discount_rate", sa.SmallInteger(), nullable=True))
    op.add_column("products", sa.Column("currency", sa.String(length=3), nullable=True))
    op.add_column("products", sa.Column("raw_price", sa.Numeric(12, 2), nullable=True))
    op.add_column("products", sa.Column("price_updated_at", sa.DateTime(), nullable=True))
    op.add_column("products", sa.Column("sale_started_at", sa.DateTime(), nullable=True))

    op.create_index("ix_products_price_krw", "products", ["price_krw"], unique=False)
    op.create_index("ix_products_sale_started_at", "products", ["sale_started_at"], unique=False)

    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        _backfill_sqlite()
    else:
        _backfill_postgresql()


def downgrade() -> None:
    op.drop_index("ix_products_sale_started_at", table_name="products")
    op.drop_index("ix_products_price_krw", table_name="products")
    op.drop_column("products", "sale_started_at")
    op.drop_column("products", "price_updated_at")
    op.drop_column("products", "raw_price")
    op.drop_column("products", "currency")
    op.drop_column("products", "discount_rate")
    op.drop_column("products", "original_price_krw")
    op.drop_column("products", "price_krw")
