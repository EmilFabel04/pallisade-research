# alembic/versions/0012_foresight_raw_tier3_and_news_caches.py
"""foresight_raw_tier3_and_news_caches

Revision ID: 0012_foresight_raw_tier3_and_news_caches
Revises: 0011_foresight_tables
Create Date: 2026-05-27 12:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0012_foresight_raw_tier3_and_news_caches"
down_revision: Union[str, Sequence[str], None] = "0011_foresight_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Widen alembic_version.version_num to hold long revision IDs ─────────
    op.execute("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(64)")

    # ── 13F filings + positions ─────────────────────────────────────────────
    op.create_table(
        "foresight_filings_13f",
        sa.Column("accession_number", sa.Text(), primary_key=True),
        sa.Column("cik", sa.Text(), nullable=False),
        sa.Column("filer_name", sa.Text(), nullable=False),
        sa.Column("period_of_report", sa.Date(), nullable=False),
        sa.Column("filing_date", sa.Date(), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_13f_cik_period", "foresight_filings_13f",
                    ["cik", "period_of_report"])
    op.create_index("ix_13f_filing_date", "foresight_filings_13f",
                    [sa.text("filing_date DESC")])

    op.create_table(
        "foresight_filings_13f_positions",
        sa.Column("accession_number", sa.Text(), nullable=False),
        sa.Column("cusip", sa.Text(), nullable=False),
        sa.Column("ticker", sa.Text(), nullable=True),
        sa.Column("value_usd", sa.BigInteger(), nullable=False),
        sa.Column("shares", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("accession_number", "cusip"),
        sa.ForeignKeyConstraint(["accession_number"], ["foresight_filings_13f.accession_number"],
                                ondelete="CASCADE"),
    )
    op.create_index("ix_13f_positions_ticker", "foresight_filings_13f_positions",
                    ["ticker"], postgresql_where=sa.text("ticker IS NOT NULL"))

    # ── CUSIP → ticker cache ────────────────────────────────────────────────
    op.create_table(
        "foresight_cusip_ticker",
        sa.Column("cusip", sa.Text(), primary_key=True),
        sa.Column("ticker", sa.Text(), nullable=False),
        sa.Column("exchange", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    # ── Form 4 transactions ─────────────────────────────────────────────────
    op.create_table(
        "foresight_form4_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("accession_number", sa.Text(), nullable=False),
        sa.Column("filing_date", sa.Date(), nullable=False),
        sa.Column("ticker", sa.Text(), nullable=False),
        sa.Column("exchange", sa.Text(), nullable=False),
        sa.Column("insider_cik", sa.Text(), nullable=False),
        sa.Column("insider_name", sa.Text(), nullable=False),
        sa.Column("insider_role", sa.Text(), nullable=False),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("transaction_code", sa.Text(), nullable=False),
        sa.Column("shares", sa.Numeric(), nullable=False),
        sa.Column("price_per_share", sa.Numeric(), nullable=True),
        sa.Column("value_usd", sa.Numeric(), nullable=True),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("accession_number", "ticker", "insider_cik", "transaction_date",
                            "transaction_code", "shares",
                            name="uq_form4_tx_dedup"),
    )
    op.create_index("ix_form4_ticker_date", "foresight_form4_transactions",
                    ["ticker", sa.text("transaction_date DESC")])

    # ── Short interest ──────────────────────────────────────────────────────
    op.create_table(
        "foresight_short_interest",
        sa.Column("ticker", sa.Text(), nullable=False),
        sa.Column("exchange", sa.Text(), nullable=False),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("short_interest", sa.BigInteger(), nullable=False),
        sa.Column("days_to_cover", sa.Numeric(), nullable=True),
        sa.Column("short_pct_float", sa.Numeric(), nullable=True),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("ticker", "exchange", "report_date"),
    )

    # ── Ticker meta ─────────────────────────────────────────────────────────
    op.create_table(
        "foresight_ticker_meta",
        sa.Column("ticker", sa.Text(), nullable=False),
        sa.Column("exchange", sa.Text(), nullable=False),
        sa.Column("float_shares", sa.BigInteger(), nullable=True),
        sa.Column("market_cap_usd", sa.BigInteger(), nullable=True),
        sa.Column("sector", sa.Text(), nullable=True),
        sa.Column("industry", sa.Text(), nullable=True),
        sa.Column("refreshed_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("ticker", "exchange"),
    )

    # ── News articles ───────────────────────────────────────────────────────
    op.create_table(
        "foresight_news_articles",
        sa.Column("url_hash", sa.Text(), primary_key=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("source_domain", sa.Text(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("headline", sa.Text(), nullable=False),
        sa.Column("language", sa.Text(), nullable=True),
        sa.Column("ner_entities", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("finbert_scores", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("classified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_detected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_news_published", "foresight_news_articles",
                    [sa.text("published_at DESC")])
    op.create_index("ix_news_pending_classification", "foresight_news_articles",
                    ["ingested_at"], postgresql_where=sa.text("classified_at IS NULL"))
    op.create_index("ix_news_pending_detection", "foresight_news_articles",
                    ["classified_at"],
                    postgresql_where=sa.text("classified_at IS NOT NULL AND last_detected_at IS NULL"))

    # ── Event idempotency column ────────────────────────────────────────────
    op.add_column("foresight_events",
                  sa.Column("external_id", sa.Text(), nullable=True))
    op.create_index("uq_foresight_events_source_external", "foresight_events",
                    ["source", "external_id"], unique=True,
                    postgresql_where=sa.text("external_id IS NOT NULL"))


def downgrade() -> None:
    # Note: the upgrade widens alembic_version.version_num to VARCHAR(64) to
    # accommodate this revision's 40-char ID. We intentionally do NOT narrow
    # it back here — doing so would truncate this very revision_id, corrupting
    # the alembic_version table the moment Alembic tries to record the
    # downgrade. The wider column is strictly forward-compatible.
    op.drop_index("uq_foresight_events_source_external", table_name="foresight_events")
    op.drop_column("foresight_events", "external_id")

    op.drop_index("ix_news_pending_detection", table_name="foresight_news_articles")
    op.drop_index("ix_news_pending_classification", table_name="foresight_news_articles")
    op.drop_index("ix_news_published", table_name="foresight_news_articles")
    op.drop_table("foresight_news_articles")

    op.drop_table("foresight_ticker_meta")
    op.drop_table("foresight_short_interest")

    op.drop_index("ix_form4_ticker_date", table_name="foresight_form4_transactions")
    op.drop_table("foresight_form4_transactions")

    op.drop_table("foresight_cusip_ticker")

    op.drop_index("ix_13f_positions_ticker", table_name="foresight_filings_13f_positions")
    op.drop_table("foresight_filings_13f_positions")
    op.drop_index("ix_13f_filing_date", table_name="foresight_filings_13f")
    op.drop_index("ix_13f_cik_period", table_name="foresight_filings_13f")
    op.drop_table("foresight_filings_13f")
