"""add phase3 quality tracking

Revision ID: 3a4b5c6d7e8f
Revises: b7c8d9e0f1a2
Create Date: 2026-03-08 13:25:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3a4b5c6d7e8f"
down_revision: Union[str, Sequence[str], None] = "b7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("channels", sa.Column("last_probe_at", sa.DateTime(), nullable=True))
    op.create_index(op.f("ix_channels_last_probe_at"), "channels", ["last_probe_at"], unique=False)

    op.add_column("products", sa.Column("image_verified_at", sa.DateTime(), nullable=True))
    op.create_index(op.f("ix_products_image_verified_at"), "products", ["image_verified_at"], unique=False)

    op.add_column(
        "product_catalog",
        sa.Column("channel_count", sa.Integer(), nullable=False, server_default="1"),
    )
    op.execute("UPDATE product_catalog SET channel_count = COALESCE(listing_count, 1)")
    op.alter_column("product_catalog", "channel_count", server_default=None)

    op.create_table(
        "channel_crawl_stats",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("crawl_run_id", sa.Integer(), nullable=False),
        sa.Column("channel_id", sa.Integer(), nullable=False),
        sa.Column("products_found", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("parse_method", sa.String(length=30), nullable=True),
        sa.Column("error_msg", sa.Text(), nullable=True),
        sa.Column("crawled_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["channel_id"], ["channels.id"]),
        sa.ForeignKeyConstraint(["crawl_run_id"], ["crawl_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_channel_crawl_stats_channel_id"), "channel_crawl_stats", ["channel_id"], unique=False)
    op.create_index(op.f("ix_channel_crawl_stats_crawl_run_id"), "channel_crawl_stats", ["crawl_run_id"], unique=False)
    op.create_index(op.f("ix_channel_crawl_stats_crawled_at"), "channel_crawl_stats", ["crawled_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_channel_crawl_stats_crawled_at"), table_name="channel_crawl_stats")
    op.drop_index(op.f("ix_channel_crawl_stats_crawl_run_id"), table_name="channel_crawl_stats")
    op.drop_index(op.f("ix_channel_crawl_stats_channel_id"), table_name="channel_crawl_stats")
    op.drop_table("channel_crawl_stats")

    op.drop_column("product_catalog", "channel_count")

    op.drop_index(op.f("ix_products_image_verified_at"), table_name="products")
    op.drop_column("products", "image_verified_at")

    op.drop_index(op.f("ix_channels_last_probe_at"), table_name="channels")
    op.drop_column("channels", "last_probe_at")
