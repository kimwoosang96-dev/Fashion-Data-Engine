"""add size_availability and stock_status to products

Revision ID: b7c8d9e0f1a2
Revises: 29c0d1e2f3a4
Create Date: 2026-03-08

Phase 1 리포지셔닝: "지금 어디서 살 수 있나 + 사이즈 재고" 중심 데이터 구조.
- size_availability: Shopify variant별 사이즈 재고 (JSONB)
- stock_status: 빠른 필터용 재고 상태 문자열 (in_stock / low_stock / sold_out)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "b7c8d9e0f1a2"
down_revision = "29c0d1e2f3a4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column("size_availability", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "products",
        sa.Column("stock_status", sa.String(20), nullable=True),
    )
    op.create_index(
        "ix_products_stock_status",
        "products",
        ["stock_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_products_stock_status", table_name="products")
    op.drop_column("products", "stock_status")
    op.drop_column("products", "size_availability")
