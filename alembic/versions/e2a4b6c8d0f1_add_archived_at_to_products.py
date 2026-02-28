"""add archived_at to products

Revision ID: e2a4b6c8d0f1
Revises: f1d2c3b4a5d6
Create Date: 2026-02-28 13:50:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e2a4b6c8d0f1"
down_revision: Union[str, Sequence[str], None] = "f1d2c3b4a5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    product_cols = {c["name"] for c in inspector.get_columns("products")}
    if "archived_at" not in product_cols:
        op.add_column("products", sa.Column("archived_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    product_cols = {c["name"] for c in inspector.get_columns("products")}
    if "archived_at" in product_cols:
        op.drop_column("products", "archived_at")

