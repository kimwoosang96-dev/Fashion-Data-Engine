"""add push subscriptions

Revision ID: 18b9c0d1e2f3
Revises: 07a8b9c0d1e2
Create Date: 2026-03-08 02:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "18b9c0d1e2f3"
down_revision: Union[str, Sequence[str], None] = "07a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "push_subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("endpoint", sa.String(length=2000), nullable=False),
        sa.Column("p256dh", sa.String(length=512), nullable=False),
        sa.Column("auth", sa.String(length=512), nullable=False),
        sa.Column("brand_ids", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("endpoint"),
    )


def downgrade() -> None:
    op.drop_table("push_subscriptions")
