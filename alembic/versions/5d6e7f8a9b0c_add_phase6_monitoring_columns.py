"""add phase6 monitoring columns

Revision ID: 5d6e7f8a9b0c
Revises: 4b5c6d7e8f9a
Create Date: 2026-03-08 23:40:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "5d6e7f8a9b0c"
down_revision: Union[str, Sequence[str], None] = "4b5c6d7e8f9a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("channels", sa.Column("last_crawled_at", sa.DateTime(), nullable=True))
    op.create_index(op.f("ix_channels_last_crawled_at"), "channels", ["last_crawled_at"], unique=False)

    op.add_column("channel_crawl_stats", sa.Column("llm_prompt_tokens", sa.Integer(), nullable=True))
    op.add_column("channel_crawl_stats", sa.Column("llm_completion_tokens", sa.Integer(), nullable=True))
    op.add_column("channel_crawl_stats", sa.Column("llm_provider", sa.String(length=20), nullable=True))
    op.add_column("channel_crawl_stats", sa.Column("llm_cost_usd", sa.Numeric(10, 6), nullable=True))


def downgrade() -> None:
    op.drop_column("channel_crawl_stats", "llm_cost_usd")
    op.drop_column("channel_crawl_stats", "llm_provider")
    op.drop_column("channel_crawl_stats", "llm_completion_tokens")
    op.drop_column("channel_crawl_stats", "llm_prompt_tokens")

    op.drop_index(op.f("ix_channels_last_crawled_at"), table_name="channels")
    op.drop_column("channels", "last_crawled_at")
