"""add vendor to products

Revision ID: a7c9d1e3f5b7
Revises: e2a4b6c8d0f1
Create Date: 2026-03-01 00:20:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a7c9d1e3f5b7"
down_revision: Union[str, Sequence[str], None] = "e2a4b6c8d0f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    product_cols = {c["name"] for c in inspector.get_columns("products")}
    if "vendor" not in product_cols:
        op.add_column("products", sa.Column("vendor", sa.String(length=255), nullable=True))

    idx_names = {i["name"] for i in inspector.get_indexes("products")}
    if "ix_products_vendor" not in idx_names:
        op.create_index("ix_products_vendor", "products", ["vendor"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    idx_names = {i["name"] for i in inspector.get_indexes("products")}
    if "ix_products_vendor" in idx_names:
        op.drop_index("ix_products_vendor", table_name="products")

    product_cols = {c["name"] for c in inspector.get_columns("products")}
    if "vendor" in product_cols:
        op.drop_column("products", "vendor")
