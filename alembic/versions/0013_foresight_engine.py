"""foresight_engine: factor snapshots, severity buckets, calibrator storage

Revision ID: 0013_foresight_engine
Revises: 0012_foresight_raw_tier3_and_news_caches
Create Date: 2026-05-28
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "0013_foresight_engine"
down_revision = "0012_foresight_raw_tier3_and_news_caches"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # foresight_events: factor snapshot + severity bucket
    op.add_column(
        "foresight_events",
        sa.Column("factor_snapshot_jsonb", postgresql.JSONB(astext_type=sa.Text()),
                  nullable=True),
    )
    op.add_column(
        "foresight_events",
        sa.Column("severity_bucket", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_foresight_events_type_severity",
        "foresight_events",
        ["event_type", "severity_bucket", sa.text("occurred_at DESC")],
    )
    op.create_check_constraint(
        "foresight_events_severity_bucket_check",
        "foresight_events",
        "severity_bucket IS NULL OR severity_bucket IN ('low','medium','high')",
    )

    # foresight_backtest_cohorts: is_active + calibrator JSONB
    op.add_column(
        "foresight_backtest_cohorts",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "foresight_backtest_cohorts",
        sa.Column("calibrator_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    # Only one cohort active at a time
    op.create_index(
        "uq_foresight_backtest_cohorts_one_active",
        "foresight_backtest_cohorts",
        ["is_active"],
        unique=True,
        postgresql_where=sa.text("is_active = true"),
    )

    # foresight_paper_trades: allow NULL on entry prices (filled at outcome time)
    op.alter_column("foresight_paper_trades", "entry_price", nullable=True)
    op.alter_column("foresight_paper_trades", "entry_index_price", nullable=True)


def downgrade() -> None:
    # Downgrade is operationally destructive: re-adding NOT NULL requires
    # backfilling any NULL entry prices with a sentinel (0). Real callers
    # should restore from backup before running this; this backfill exists
    # so the migration itself doesn't fail mid-flight.
    op.execute("""
        UPDATE foresight_paper_trades
        SET entry_price = 0 WHERE entry_price IS NULL
    """)
    op.execute("""
        UPDATE foresight_paper_trades
        SET entry_index_price = 0 WHERE entry_index_price IS NULL
    """)
    op.alter_column("foresight_paper_trades", "entry_index_price", nullable=False)
    op.alter_column("foresight_paper_trades", "entry_price", nullable=False)
    op.drop_index("uq_foresight_backtest_cohorts_one_active",
                  table_name="foresight_backtest_cohorts")
    op.drop_column("foresight_backtest_cohorts", "calibrator_jsonb")
    op.drop_column("foresight_backtest_cohorts", "is_active")
    op.drop_constraint("foresight_events_severity_bucket_check",
                       "foresight_events", type_="check")
    op.drop_index("ix_foresight_events_type_severity", table_name="foresight_events")
    op.drop_column("foresight_events", "severity_bucket")
    op.drop_column("foresight_events", "factor_snapshot_jsonb")
