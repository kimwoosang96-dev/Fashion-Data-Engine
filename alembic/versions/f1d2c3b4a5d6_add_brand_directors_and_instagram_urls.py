"""add brand directors and instagram urls

Revision ID: f1d2c3b4a5d6
Revises: 9f9b0e1f2a3b
Create Date: 2026-02-28 08:05:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f1d2c3b4a5d6"
down_revision: Union[str, Sequence[str], None] = "9f9b0e1f2a3b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    brand_cols = {c["name"] for c in inspector.get_columns("brands")}
    if "instagram_url" not in brand_cols:
        op.add_column("brands", sa.Column("instagram_url", sa.String(length=500), nullable=True))

    channel_cols = {c["name"] for c in inspector.get_columns("channels")}
    if "instagram_url" not in channel_cols:
        op.add_column("channels", sa.Column("instagram_url", sa.String(length=500), nullable=True))

    tables = set(inspector.get_table_names())
    if "brand_directors" not in tables:
        op.create_table(
            "brand_directors",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("brand_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("role", sa.String(length=100), nullable=False),
            sa.Column("start_year", sa.Integer(), nullable=True),
            sa.Column("end_year", sa.Integer(), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["brand_id"], ["brands.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    idx_names = {i["name"] for i in inspector.get_indexes("brand_directors")}
    if "idx_brand_directors_brand_id" not in idx_names:
        op.create_index("idx_brand_directors_brand_id", "brand_directors", ["brand_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    tables = set(inspector.get_table_names())
    if "brand_directors" in tables:
        idx_names = {i["name"] for i in inspector.get_indexes("brand_directors")}
        if "idx_brand_directors_brand_id" in idx_names:
            op.drop_index("idx_brand_directors_brand_id", table_name="brand_directors")
        op.drop_table("brand_directors")

    channel_cols = {c["name"] for c in inspector.get_columns("channels")}
    if "instagram_url" in channel_cols:
        op.drop_column("channels", "instagram_url")

    brand_cols = {c["name"] for c in inspector.get_columns("brands")}
    if "instagram_url" in brand_cols:
        op.drop_column("brands", "instagram_url")
