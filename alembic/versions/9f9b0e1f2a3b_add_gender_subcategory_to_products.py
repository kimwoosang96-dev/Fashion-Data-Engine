"""add gender/subcategory to products

Revision ID: 9f9b0e1f2a3b
Revises: 7b6619f9d1ad
Create Date: 2026-02-28 07:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9f9b0e1f2a3b"
down_revision: Union[str, Sequence[str], None] = "7b6619f9d1ad"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("products", sa.Column("gender", sa.String(length=20), nullable=True))
    op.add_column("products", sa.Column("subcategory", sa.String(length=100), nullable=True))
    op.create_index("idx_products_gender", "products", ["gender"], unique=False)
    op.create_index("idx_products_subcategory", "products", ["subcategory"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_products_subcategory", table_name="products")
    op.drop_index("idx_products_gender", table_name="products")
    op.drop_column("products", "subcategory")
    op.drop_column("products", "gender")
