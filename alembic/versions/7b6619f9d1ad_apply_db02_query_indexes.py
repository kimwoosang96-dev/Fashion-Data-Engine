"""apply db02 query indexes

Revision ID: 7b6619f9d1ad
Revises: 25da360cc994
Create Date: 2026-02-27 02:07:00.000000
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "7b6619f9d1ad"
down_revision: Union[str, Sequence[str], None] = "25da360cc994"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # DB_02: crawl_audit 보고서 기반 인덱스 적용
    # NOTE: ix_products_product_key 가 이미 존재해도 동일 목적 인덱스를 명시 이름으로 보장한다.
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_products_sale_active "
        "ON products (is_sale, is_active, id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_products_product_key "
        "ON products (product_key)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_price_history_product_crawled "
        "ON price_history (product_id, crawled_at DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_brands_slug "
        "ON brands (slug)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_products_brand_sale "
        "ON products (brand_id, is_sale, id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_channel_brands_channel_brand "
        "ON channel_brands (channel_id, brand_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_channel_brands_channel_brand")
    op.execute("DROP INDEX IF EXISTS idx_products_brand_sale")
    op.execute("DROP INDEX IF EXISTS idx_brands_slug")
    op.execute("DROP INDEX IF EXISTS idx_price_history_product_crawled")
    op.execute("DROP INDEX IF EXISTS idx_products_product_key")
    op.execute("DROP INDEX IF EXISTS idx_products_sale_active")
