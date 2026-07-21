"""evaluation_results

Revision ID: 0009_evaluation_results
Revises: 0008_phase3_runs_jobs
Create Date: 2026-05-26 00:00:01.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0009_evaluation_results"
down_revision: Union[str, Sequence[str], None] = "0008_phase3_runs_jobs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "evaluation_results",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"), nullable=False,
        ),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recommendation", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("final_thesis_md", sa.Text(), nullable=False),
        sa.Column("key_risks_md", sa.Text(), nullable=False),
        sa.Column("financial_summary_md", sa.Text(), nullable=False),
        sa.Column(
            "agent_outputs",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("tokens_in", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("tokens_out", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "cost_usd", sa.Numeric(10, 4),
            nullable=False, server_default=sa.text("0"),
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["run_id"], ["evaluation_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", name="uq_eval_results_run"),
        sa.CheckConstraint(
            "recommendation in ('approve','decline','conditional')",
            name="eval_results_recommendation_check",
        ),
        sa.CheckConstraint(
            "confidence >= 0 and confidence <= 1",
            name="eval_results_confidence_check",
        ),
    )


def downgrade() -> None:
    op.drop_table("evaluation_results")
