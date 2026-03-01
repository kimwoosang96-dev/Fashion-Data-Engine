"""add_crawl_run_and_channel_log

Revision ID: 66351b967c70
Revises: b9c0d1e2f3a4
Create Date: 2026-03-01 15:46:07.813351

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '66351b967c70'
down_revision: Union[str, Sequence[str], None] = 'b9c0d1e2f3a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # crawl_runs / crawl_channel_logs 테이블 신규 생성
    # NOTE: autogenerate가 제안한 idx_* 인덱스 drop/recreate는 제거.
    #       기존 인덱스가 유효하므로 재생성 불필요; Railway 운영 DB 락 충돌 방지.
    op.create_table('crawl_runs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('started_at', sa.DateTime(), nullable=False),
    sa.Column('finished_at', sa.DateTime(), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('total_channels', sa.Integer(), nullable=False),
    sa.Column('done_channels', sa.Integer(), nullable=False),
    sa.Column('new_products', sa.Integer(), nullable=False),
    sa.Column('updated_products', sa.Integer(), nullable=False),
    sa.Column('error_channels', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_crawl_runs_started_at'), 'crawl_runs', ['started_at'], unique=False)
    op.create_table('crawl_channel_logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('run_id', sa.Integer(), nullable=False),
    sa.Column('channel_id', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('products_found', sa.Integer(), nullable=False),
    sa.Column('products_new', sa.Integer(), nullable=False),
    sa.Column('products_updated', sa.Integer(), nullable=False),
    sa.Column('error_msg', sa.String(length=500), nullable=True),
    sa.Column('strategy', sa.String(length=50), nullable=True),
    sa.Column('duration_ms', sa.Integer(), nullable=False),
    sa.Column('crawled_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['channel_id'], ['channels.id'], ),
    sa.ForeignKeyConstraint(['run_id'], ['crawl_runs.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_crawl_channel_logs_channel_id'), 'crawl_channel_logs', ['channel_id'], unique=False)
    op.create_index(op.f('ix_crawl_channel_logs_run_id'), 'crawl_channel_logs', ['run_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_crawl_channel_logs_run_id'), table_name='crawl_channel_logs')
    op.drop_index(op.f('ix_crawl_channel_logs_channel_id'), table_name='crawl_channel_logs')
    op.drop_table('crawl_channel_logs')
    op.drop_index(op.f('ix_crawl_runs_started_at'), table_name='crawl_runs')
    op.drop_table('crawl_runs')
