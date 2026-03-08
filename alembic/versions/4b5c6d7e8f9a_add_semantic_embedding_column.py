"""add semantic embedding column

Revision ID: 4b5c6d7e8f9a
Revises: 3a4b5c6d7e8f
Create Date: 2026-03-08 22:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4b5c6d7e8f9a"
down_revision: Union[str, None] = "3a4b5c6d7e8f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
        op.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS name_embedding vector(384)")
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_products_name_embedding "
            "ON products USING ivfflat (name_embedding vector_cosine_ops)"
        )
    else:
        op.add_column("products", sa.Column("name_embedding", sa.Text(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS ix_products_name_embedding")
        op.execute("ALTER TABLE products DROP COLUMN IF EXISTS name_embedding")
    else:
        op.drop_column("products", "name_embedding")
