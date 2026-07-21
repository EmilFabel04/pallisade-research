"""Plan 3b — digest snapshots + seed flag on cohorts.

Revision ID: 0014_foresight_3b
Revises: 0013_foresight_engine
Create Date: 2026-05-29
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0014_foresight_3b"
down_revision = "0013_foresight_engine"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "foresight_daily_digest_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("as_of", sa.Date(), nullable=False),
        sa.Column("region", sa.Text(), nullable=False),
        sa.Column("payload_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("region IN ('SAST', 'BST', 'ET')",
                           name="foresight_digest_region_check"),
    )
    op.create_index(
        "ix_foresight_digest_region_as_of",
        "foresight_daily_digest_snapshots",
        ["region", sa.text("as_of DESC")],
    )

    op.add_column(
        "foresight_backtest_cohorts",
        sa.Column("seed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("foresight_backtest_cohorts", "seed")
    op.drop_index("ix_foresight_digest_region_as_of",
                  table_name="foresight_daily_digest_snapshots")
    op.drop_table("foresight_daily_digest_snapshots")
