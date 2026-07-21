# alembic/versions/0019_surveillance_verdicts.py
"""Surveillance verdict cache table.

Stores Claude-generated risk-surveillance verdicts keyed by (source,
external_id) so the demo serves instant, deterministic verdicts without
re-calling the model. Upsert on the composite primary key keeps the cache
idempotent across re-runs.

Revision ID: 0019_surveillance_verdicts
Revises: 0018_form4_issuer_cik
Create Date: 2026-06-05
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0019_surveillance_verdicts"
down_revision = "0018_form4_issuer_cik"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "surveillance_verdicts",
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=False),
        sa.Column("headline", sa.Text(), nullable=False),
        sa.Column("what_happened", sa.Text(), nullable=False),
        sa.Column("what_it_means", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("suggested_action", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("source", "external_id"),
    )


def downgrade() -> None:
    op.drop_table("surveillance_verdicts")
