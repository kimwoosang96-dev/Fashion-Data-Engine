"""add activity_feed table

Revision ID: c3e4f5a6b7d8
Revises: b2d3f4a5c6e7
Create Date: 2026-03-08 00:56:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3e4f5a6b7d8"
down_revision: Union[str, Sequence[str], None] = "b2d3f4a5c6e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "activity_feed",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=30), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("channel_id", sa.Integer(), nullable=True),
        sa.Column("brand_id", sa.Integer(), nullable=True),
        sa.Column("product_name", sa.String(length=500), nullable=True),
        sa.Column("price_krw", sa.Integer(), nullable=True),
        sa.Column("discount_rate", sa.Integer(), nullable=True),
        sa.Column("source_url", sa.String(length=2000), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("detected_at", sa.DateTime(), nullable=False),
        sa.Column("notified", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"]),
        sa.ForeignKeyConstraint(["channel_id"], ["channels.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_activity_feed_detected_at", "activity_feed", ["detected_at"], unique=False)
    op.create_index(
        "ix_activity_feed_event_type_detected_at",
        "activity_feed",
        ["event_type", "detected_at"],
        unique=False,
    )
    op.create_index("ix_activity_feed_brand_id", "activity_feed", ["brand_id"], unique=False)
    op.create_index("ix_activity_feed_event_type", "activity_feed", ["event_type"], unique=False)
    op.create_index("ix_activity_feed_product_id", "activity_feed", ["product_id"], unique=False)
    op.create_index("ix_activity_feed_channel_id", "activity_feed", ["channel_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_activity_feed_channel_id", table_name="activity_feed")
    op.drop_index("ix_activity_feed_product_id", table_name="activity_feed")
    op.drop_index("ix_activity_feed_event_type", table_name="activity_feed")
    op.drop_index("ix_activity_feed_brand_id", table_name="activity_feed")
    op.drop_index("ix_activity_feed_event_type_detected_at", table_name="activity_feed")
    op.drop_index("ix_activity_feed_detected_at", table_name="activity_feed")
    op.drop_table("activity_feed")
