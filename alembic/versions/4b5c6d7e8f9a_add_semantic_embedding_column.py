"""add semantic embedding column

Revision ID: 4b5c6d7e8f9a
Revises: 3a4b5c6d7e8f
Create Date: 2026-03-08 22:30:00.000000

pgvector는 Railway 무료 플랜 미지원 → TEXT 컬럼으로 저장.
pgvector 환경에서는 generate_embeddings.py 실행 후
수동으로 ALTER COLUMN ... TYPE vector(384) 가능.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4b5c6d7e8f9a"
down_revision: Union[str, None] = "3a4b5c6d7e8f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # name_embedding: pgvector 없는 환경에서는 TEXT로 저장 (의미 검색 비활성화).
    # search_service_v2.py가 vector 타입 없으면 키워드 검색으로 자동 fallback함.
    op.add_column(
        "products",
        sa.Column("name_embedding", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("products", "name_embedding")
