"""phase3: evaluation_runs thesis/params/current_node + processing_jobs evaluate_deal

Revision ID: 0008_phase3_runs_jobs
Revises: 0007_chat
Create Date: 2026-05-26 00:00:00.000000

Note on downgrade: this is a one-way migration in practice. Once any
'evaluate_deal' jobs have been inserted with NULL document_id, restoring
NOT NULL on processing_jobs.document_id will fail until those rows are
cleaned up. The downgrade() reverses the schema for fresh databases only.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0008_phase3_runs_jobs"
down_revision: Union[str, Sequence[str], None] = "0007_chat"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # evaluation_runs additions
    op.add_column("evaluation_runs", sa.Column("thesis", sa.Text(), nullable=True))
    op.add_column(
        "evaluation_runs",
        sa.Column("params", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column("evaluation_runs", sa.Column("current_node", sa.String(), nullable=True))

    # processing_jobs: relax document_id, add payload, extend job_type CHECK
    op.alter_column("processing_jobs", "document_id", nullable=True)
    op.add_column(
        "processing_jobs",
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.drop_constraint("jobs_type_check", "processing_jobs", type_="check")
    op.create_check_constraint(
        "jobs_type_check",
        "processing_jobs",
        "job_type in ('parse_document','embed_document','evaluate_deal')",
    )


def downgrade() -> None:
    op.drop_constraint("jobs_type_check", "processing_jobs", type_="check")
    op.create_check_constraint(
        "jobs_type_check",
        "processing_jobs",
        "job_type in ('parse_document','embed_document')",
    )
    op.drop_column("processing_jobs", "payload")
    op.alter_column("processing_jobs", "document_id", nullable=False)

    op.drop_column("evaluation_runs", "current_node")
    op.drop_column("evaluation_runs", "params")
    op.drop_column("evaluation_runs", "thesis")
