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
        # pgvector 확장 시도 — Railway 무료 플랜은 미지원 가능
        # 실패 시 Text 컬럼으로 대체 (의미 검색만 비활성화, 서버는 정상 기동)
        try:
            op.execute("CREATE EXTENSION IF NOT EXISTS vector")
            op.execute(
                "ALTER TABLE products ADD COLUMN IF NOT EXISTS name_embedding vector(384)"
            )
            op.execute(
                "CREATE INDEX IF NOT EXISTS ix_products_name_embedding "
                "ON products USING ivfflat (name_embedding vector_cosine_ops) "
                "WITH (lists = 100)"
            )
        except Exception:
            bind.execute(
                sa.text(
                    "ALTER TABLE products ADD COLUMN IF NOT EXISTS name_embedding TEXT"
                )
            )
    else:
        op.add_column(
            "products", sa.Column("name_embedding", sa.Text(), nullable=True)
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS ix_products_name_embedding")
        op.execute("ALTER TABLE products DROP COLUMN IF EXISTS name_embedding")
    else:
        op.drop_column("products", "name_embedding")
