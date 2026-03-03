"""add intel hub tables

Revision ID: f1a2b3c4d5e6
Revises: e5f6a7b8c9d0
Create Date: 2026-03-03 01:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "intel_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=30), nullable=False),
        sa.Column("layer", sa.String(length=30), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("event_time", sa.DateTime(), nullable=True),
        sa.Column("detected_at", sa.DateTime(), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("confidence", sa.String(length=20), nullable=False),
        sa.Column("brand_id", sa.Integer(), nullable=True),
        sa.Column("channel_id", sa.Integer(), nullable=True),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("product_key", sa.String(length=300), nullable=True),
        sa.Column("geo_country", sa.String(length=2), nullable=True),
        sa.Column("geo_city", sa.String(length=120), nullable=True),
        sa.Column("geo_lat", sa.Float(), nullable=True),
        sa.Column("geo_lng", sa.Float(), nullable=True),
        sa.Column("geo_precision", sa.String(length=20), nullable=False),
        sa.Column("source_url", sa.String(length=1000), nullable=True),
        sa.Column("source_domain", sa.String(length=255), nullable=True),
        sa.Column("source_type", sa.String(length=30), nullable=False),
        sa.Column("dedup_key", sa.String(length=400), nullable=False),
        sa.Column("details_json", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"]),
        sa.ForeignKeyConstraint(["channel_id"], ["channels.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dedup_key"),
    )
    op.create_index(op.f("ix_intel_events_event_type"), "intel_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_intel_events_layer"), "intel_events", ["layer"], unique=False)
    op.create_index(op.f("ix_intel_events_event_time"), "intel_events", ["event_time"], unique=False)
    op.create_index(op.f("ix_intel_events_detected_at"), "intel_events", ["detected_at"], unique=False)
    op.create_index(op.f("ix_intel_events_brand_id"), "intel_events", ["brand_id"], unique=False)
    op.create_index(op.f("ix_intel_events_channel_id"), "intel_events", ["channel_id"], unique=False)
    op.create_index(op.f("ix_intel_events_product_id"), "intel_events", ["product_id"], unique=False)
    op.create_index(op.f("ix_intel_events_product_key"), "intel_events", ["product_key"], unique=False)
    op.create_index(op.f("ix_intel_events_last_seen_at"), "intel_events", ["last_seen_at"], unique=False)

    op.create_table(
        "intel_ingest_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_name", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("inserted_count", sa.Integer(), nullable=False),
        sa.Column("updated_count", sa.Integer(), nullable=False),
        sa.Column("error_count", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_intel_ingest_runs_job_name"), "intel_ingest_runs", ["job_name"], unique=False)
    op.create_index(op.f("ix_intel_ingest_runs_status"), "intel_ingest_runs", ["status"], unique=False)
    op.create_index(op.f("ix_intel_ingest_runs_started_at"), "intel_ingest_runs", ["started_at"], unique=False)

    op.create_table(
        "intel_ingest_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("level", sa.String(length=20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("source_table", sa.String(length=50), nullable=True),
        sa.Column("source_pk", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["intel_ingest_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_intel_ingest_logs_run_id"), "intel_ingest_logs", ["run_id"], unique=False)
    op.create_index(op.f("ix_intel_ingest_logs_created_at"), "intel_ingest_logs", ["created_at"], unique=False)

    op.create_table(
        "intel_event_sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=True),
        sa.Column("source_table", sa.String(length=50), nullable=False),
        sa.Column("source_pk", sa.Integer(), nullable=False),
        sa.Column("source_url", sa.String(length=1000), nullable=True),
        sa.Column("source_published_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["intel_events.id"]),
        sa.ForeignKeyConstraint(["run_id"], ["intel_ingest_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_table", "source_pk", name="uq_intel_event_sources_source"),
    )
    op.create_index(op.f("ix_intel_event_sources_event_id"), "intel_event_sources", ["event_id"], unique=False)
    op.create_index(op.f("ix_intel_event_sources_run_id"), "intel_event_sources", ["run_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_intel_event_sources_run_id"), table_name="intel_event_sources")
    op.drop_index(op.f("ix_intel_event_sources_event_id"), table_name="intel_event_sources")
    op.drop_table("intel_event_sources")

    op.drop_index(op.f("ix_intel_ingest_logs_created_at"), table_name="intel_ingest_logs")
    op.drop_index(op.f("ix_intel_ingest_logs_run_id"), table_name="intel_ingest_logs")
    op.drop_table("intel_ingest_logs")

    op.drop_index(op.f("ix_intel_ingest_runs_started_at"), table_name="intel_ingest_runs")
    op.drop_index(op.f("ix_intel_ingest_runs_status"), table_name="intel_ingest_runs")
    op.drop_index(op.f("ix_intel_ingest_runs_job_name"), table_name="intel_ingest_runs")
    op.drop_table("intel_ingest_runs")

    op.drop_index(op.f("ix_intel_events_last_seen_at"), table_name="intel_events")
    op.drop_index(op.f("ix_intel_events_product_key"), table_name="intel_events")
    op.drop_index(op.f("ix_intel_events_product_id"), table_name="intel_events")
    op.drop_index(op.f("ix_intel_events_channel_id"), table_name="intel_events")
    op.drop_index(op.f("ix_intel_events_brand_id"), table_name="intel_events")
    op.drop_index(op.f("ix_intel_events_detected_at"), table_name="intel_events")
    op.drop_index(op.f("ix_intel_events_event_time"), table_name="intel_events")
    op.drop_index(op.f("ix_intel_events_layer"), table_name="intel_events")
    op.drop_index(op.f("ix_intel_events_event_type"), table_name="intel_events")
    op.drop_table("intel_events")
