# alembic/versions/0016_foresight_8k_events.py
"""Form 8-K events (item codes) for risk detectors + adverse-event labels.

One row per 8-K filing, keyed by accession_number. `items` holds the SEC item
codes (e.g. {'4.02','9.01'}) sourced from the data.sec.gov submissions `items`
field. Powers both the sec_8k coincident detector and the validation
ground-truth labels (restatement/auditor/bankruptcy/delisting).

Revision ID: 0016_foresight_8k_events
Revises: 0015_foresight_form4_acceptance
Create Date: 2026-06-04
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0016_foresight_8k_events"
down_revision = "0015_foresight_form4_acceptance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "foresight_8k_events",
        sa.Column("accession_number", sa.Text(), primary_key=True),
        sa.Column("cik", sa.Text(), nullable=False),
        sa.Column("ticker", sa.Text(), nullable=False),
        sa.Column("filed_at", sa.Date(), nullable=False),
        sa.Column("acceptance_datetime", sa.DateTime(timezone=True), nullable=True),
        sa.Column("items", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_8k_ticker_filed", "foresight_8k_events",
                    ["ticker", sa.text("filed_at DESC")])
    op.create_index("ix_8k_items_gin", "foresight_8k_events",
                    ["items"], postgresql_using="gin")


def downgrade() -> None:
    op.drop_index("ix_8k_items_gin", table_name="foresight_8k_events")
    op.drop_index("ix_8k_ticker_filed", table_name="foresight_8k_events")
    op.drop_table("foresight_8k_events")
