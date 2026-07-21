# alembic/versions/0018_form4_issuer_cik.py
"""Add issuer_cik to foresight_form4_transactions for CIK-keyed crawling.

The survivor-free risk validation keys insider selling against adverse 8-K
events by *issuer CIK* (delisted tickers are unstable). The original Form 4
table identifies the issuer only by ticker. This adds a nullable issuer_cik
column (existing survivor-universe rows stay NULL — the CIK-keyed path only
reads rows crawled via the submissions API with issuer_cik populated) plus an
index for the (issuer_cik, filing_date) lookup the detector does.

Revision ID: 0018_form4_issuer_cik
Revises: 0017_foresight_universe_hist
Create Date: 2026-06-04
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0018_form4_issuer_cik"
down_revision = "0017_foresight_universe_hist"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "foresight_form4_transactions",
        sa.Column("issuer_cik", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_form4_issuer_cik_date",
        "foresight_form4_transactions",
        ["issuer_cik", sa.text("filing_date DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_form4_issuer_cik_date",
                  table_name="foresight_form4_transactions")
    op.drop_column("foresight_form4_transactions", "issuer_cik")
