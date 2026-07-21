# alembic/versions/0011_foresight_tables.py
"""foresight_tables

Revision ID: 0011_foresight_tables
Revises: 0010_library_and_chat_anchors
Create Date: 2026-05-27 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0011_foresight_tables"
down_revision: Union[str, Sequence[str], None] = "0010_library_and_chat_anchors"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- foresight_events ----------------------------------------------------
    op.create_table(
        "foresight_events",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.text("now()")),
        sa.Column("tier", sa.SmallInteger(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("reach_tickers", postgresql.ARRAY(sa.Text()),
                  nullable=False, server_default=sa.text("'{}'::text[]")),
        sa.Column("severity", sa.SmallInteger(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("tier IN (1,3,4,5)", name="foresight_events_tier_check"),
    )
    op.create_index("ix_foresight_events_occurred", "foresight_events",
                    [sa.text("occurred_at DESC")])
    op.create_index("ix_foresight_events_type", "foresight_events",
                    ["event_type", sa.text("occurred_at DESC")])
    op.create_index("ix_foresight_events_reach", "foresight_events",
                    ["reach_tickers"], postgresql_using="gin")

    # --- foresight_calls -----------------------------------------------------
    op.create_table(
        "foresight_calls",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.text("now()")),
        sa.Column("as_of", sa.Date(), nullable=False),
        sa.Column("ticker", sa.Text(), nullable=False),
        sa.Column("exchange", sa.Text(), nullable=False),
        sa.Column("horizon_days", sa.SmallInteger(), nullable=False),
        sa.Column("direction", sa.Text(), nullable=False),
        sa.Column("magnitude_bps", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("triggering_event_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
                  nullable=False),
        sa.Column("analogues", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("factor_contributions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("suppression_checks", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("explanation_md", sa.Text(), nullable=False),
        sa.Column("backtest_cohort_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_paper_trade", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("horizon_days IN (1,3,5,10)", name="foresight_calls_horizon_check"),
        sa.CheckConstraint("direction IN ('long','short')", name="foresight_calls_direction_check"),
        sa.CheckConstraint("confidence BETWEEN 0 AND 1", name="foresight_calls_confidence_check"),
    )
    op.create_index("ix_foresight_calls_as_of",  "foresight_calls", [sa.text("as_of DESC")])
    op.create_index("ix_foresight_calls_ticker", "foresight_calls",
                    ["ticker", sa.text("as_of DESC")])
    op.create_index("ix_foresight_calls_conf",   "foresight_calls",
                    [sa.text("confidence DESC")])

    # --- foresight_paper_trades ---------------------------------------------
    op.create_table(
        "foresight_paper_trades",
        sa.Column("call_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fired_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("entry_price", sa.Numeric(), nullable=False),
        sa.Column("entry_index_price", sa.Numeric(), nullable=False),
        sa.Column("horizon_ends_on", sa.Date(), nullable=False),
        sa.Column("realized_return_bps", sa.Integer(), nullable=True),
        sa.Column("realized_alpha_bps", sa.Integer(), nullable=True),
        sa.Column("outcome", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("call_id"),
        sa.ForeignKeyConstraint(["call_id"], ["foresight_calls.id"], ondelete="CASCADE"),
    )

    # --- foresight_backtest_cohorts -----------------------------------------
    op.create_table(
        "foresight_backtest_cohorts",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.text("now()")),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("window_start", sa.Date(), nullable=False),
        sa.Column("window_end", sa.Date(), nullable=False),
        sa.Column("config_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("hit_rate_overall", sa.Float(), nullable=True),
        sa.Column("calibration_brier", sa.Float(), nullable=True),
        sa.Column("by_tier_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- foresight_market_series --------------------------------------------
    op.create_table(
        "foresight_market_series",
        sa.Column("series_id", sa.Text(), nullable=False),
        sa.Column("as_of", sa.Date(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("series_id", "as_of"),
    )

    # --- foresight_prices ---------------------------------------------------
    op.create_table(
        "foresight_prices",
        sa.Column("ticker", sa.Text(), nullable=False),
        sa.Column("exchange", sa.Text(), nullable=False),
        sa.Column("as_of", sa.Date(), nullable=False),
        sa.Column("open", sa.Numeric(), nullable=True),
        sa.Column("high", sa.Numeric(), nullable=True),
        sa.Column("low", sa.Numeric(), nullable=True),
        sa.Column("close", sa.Numeric(), nullable=True),
        sa.Column("adj_close", sa.Numeric(), nullable=True),
        sa.Column("volume", sa.BigInteger(), nullable=True),
        sa.Column("ingested_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("ticker", "exchange", "as_of"),
    )

    # --- FK from foresight_calls.backtest_cohort_id (added now that table exists)
    op.create_foreign_key(
        "fk_foresight_calls_backtest_cohort",
        "foresight_calls", "foresight_backtest_cohorts",
        ["backtest_cohort_id"], ["id"],
        ondelete="SET NULL",
    )

    # --- Extend chat_conversations ------------------------------------------
    op.add_column("chat_conversations",
                  sa.Column("foresight_call_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_chat_conversations_foresight_call",
        "chat_conversations", "foresight_calls",
        ["foresight_call_id"], ["id"],
        ondelete="SET NULL",
    )
    # Extend the kind CHECK constraint to allow 'foresight'.
    op.execute("ALTER TABLE chat_conversations DROP CONSTRAINT IF EXISTS chat_conversations_kind_check")
    op.execute(
        "ALTER TABLE chat_conversations ADD CONSTRAINT chat_conversations_kind_check "
        "CHECK (kind IN ('deal','library_doc','global','foresight'))"
    )
    op.execute("ALTER TABLE chat_conversations DROP CONSTRAINT IF EXISTS chat_anchor_exclusive")
    op.execute("""
        ALTER TABLE chat_conversations ADD CONSTRAINT chat_anchor_exclusive CHECK (
             (kind='deal'         AND deal_id IS NOT NULL AND library_doc_id IS NULL AND foresight_call_id IS NULL)
          OR (kind='library_doc'  AND library_doc_id IS NOT NULL AND deal_id IS NULL AND foresight_call_id IS NULL)
          OR (kind='global'       AND deal_id IS NULL AND library_doc_id IS NULL AND foresight_call_id IS NULL)
          OR (kind='foresight'    AND foresight_call_id IS NOT NULL AND deal_id IS NULL AND library_doc_id IS NULL)
        )
    """)

    # --- Extend library_documents.kind to allow 'call_memo' -----------------
    op.execute("ALTER TABLE library_documents DROP CONSTRAINT IF EXISTS library_documents_kind_check")
    op.execute("""
        ALTER TABLE library_documents ADD CONSTRAINT library_documents_kind_check
        CHECK (kind IN (
            'market_report','sentiment_report','news_report',
            'fundamentals_report','investment_plan',
            'trader_investment_plan','final_trade_decision',
            'call_memo'
        ))
    """)


def downgrade() -> None:
    # Plan 2 patch: any foresight conversations must be removed before we shrink
    # the chat_anchor_exclusive CHECK constraint back to a 3-branch shape.
    op.execute("DELETE FROM chat_conversations WHERE kind = 'foresight'")
    op.execute("ALTER TABLE library_documents DROP CONSTRAINT IF EXISTS library_documents_kind_check")
    op.execute("""
        ALTER TABLE library_documents ADD CONSTRAINT library_documents_kind_check
        CHECK (kind IN (
            'market_report','sentiment_report','news_report',
            'fundamentals_report','investment_plan',
            'trader_investment_plan','final_trade_decision'
        ))
    """)
    op.execute("ALTER TABLE chat_conversations DROP CONSTRAINT IF EXISTS chat_anchor_exclusive")
    op.execute("""
        ALTER TABLE chat_conversations ADD CONSTRAINT chat_anchor_exclusive CHECK (
             (kind='deal'         AND deal_id IS NOT NULL AND library_doc_id IS NULL)
          OR (kind='library_doc'  AND library_doc_id IS NOT NULL AND deal_id IS NULL)
          OR (kind='global'       AND deal_id IS NULL AND library_doc_id IS NULL)
        )
    """)
    op.execute("ALTER TABLE chat_conversations DROP CONSTRAINT IF EXISTS chat_conversations_kind_check")
    op.drop_constraint("fk_chat_conversations_foresight_call",
                       "chat_conversations", type_="foreignkey")
    op.drop_column("chat_conversations", "foresight_call_id")

    op.drop_constraint("fk_foresight_calls_backtest_cohort",
                       "foresight_calls", type_="foreignkey")
    op.drop_table("foresight_prices")
    op.drop_table("foresight_market_series")
    op.drop_table("foresight_backtest_cohorts")
    op.drop_table("foresight_paper_trades")
    op.drop_index("ix_foresight_calls_conf", table_name="foresight_calls")
    op.drop_index("ix_foresight_calls_ticker", table_name="foresight_calls")
    op.drop_index("ix_foresight_calls_as_of", table_name="foresight_calls")
    op.drop_table("foresight_calls")
    op.drop_index("ix_foresight_events_reach", table_name="foresight_events")
    op.drop_index("ix_foresight_events_type", table_name="foresight_events")
    op.drop_index("ix_foresight_events_occurred", table_name="foresight_events")
    op.drop_table("foresight_events")
