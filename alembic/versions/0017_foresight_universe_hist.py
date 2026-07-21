# alembic/versions/0017_foresight_universe_hist.py
"""Survivor-free operating-company universe from EDGAR quarterly full indexes.

One row per CIK that filed an 8-K or Form 4 in 2013Q1–2026Q2, including
companies later delisted/acquired/bankrupt. `first_filing`/`last_filing` bound
the CIK's observed activity window. This is the unbiased denominator for risk-
event validation (no survivorship bias from a current-constituent list).

Revision ID: 0017_foresight_universe_hist
Revises: 0016_foresight_8k_events
Create Date: 2026-06-04
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0017_foresight_universe_hist"
down_revision = "0016_foresight_8k_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "foresight_universe_hist",
        sa.Column("cik", sa.Text(), primary_key=True),
        sa.Column("company_name", sa.Text(), nullable=True),
        sa.Column("first_filing", sa.Date(), nullable=True),
        sa.Column("last_filing", sa.Date(), nullable=True),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("foresight_universe_hist")
