"""Form 4 acceptance datetimes (side table for tradeable-entry re-test).

Per-accession SEC acceptance instant, keyed by accession_number. Stored as a
side table rather than a column on foresight_form4_transactions because
acceptance time is one value per *filing* (accession), not per transaction row
(a filing can carry many transactions). Source of truth for re-anchoring the
insider large_buy/large_sell entry on a realistically tradeable price instead
of the hardcoded filing_date 16:00 UTC.

Revision ID: 0015_foresight_form4_acceptance
Revises: 0014_foresight_3b
Create Date: 2026-06-03
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0015_foresight_form4_acceptance"
down_revision = "0014_foresight_3b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "foresight_form4_acceptance",
        sa.Column("accession_number", sa.Text(), primary_key=True),
        # The SEC acceptance instant, stored timezone-aware (UTC). The ET
        # wall-clock used by the entry rule is derived at read time via zoneinfo
        # so DST is handled correctly across the 2013-2026 history.
        sa.Column("acceptance_datetime", sa.DateTime(timezone=True), nullable=False),
        # 'submissions' (data.sec.gov bulk JSON, UTC) or 'header' (per-accession
        # .txt SGML <ACCEPTANCE-DATETIME>, ET) — records provenance per row.
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("foresight_form4_acceptance")
