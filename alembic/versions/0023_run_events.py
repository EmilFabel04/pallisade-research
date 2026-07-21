from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0023_run_events"
down_revision = "0022_debate_run_reports"
branch_labels = None
depends_on = None

_OLD_TYPES = "job_type in ('parse_document','embed_document','evaluate_deal')"
_NEW_TYPES = "job_type in ('parse_document','embed_document','evaluate_deal','run_debate')"


def upgrade() -> None:
    op.create_table(
        "run_events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("evaluation_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("run_id", "seq", name="uq_run_events_run_seq"),
    )
    op.create_index("ix_run_events_run_seq", "run_events", ["run_id", "seq"])

    op.drop_constraint("jobs_type_check", "processing_jobs", type_="check")
    op.create_check_constraint("jobs_type_check", "processing_jobs", _NEW_TYPES)


def downgrade() -> None:
    op.drop_constraint("jobs_type_check", "processing_jobs", type_="check")
    op.create_check_constraint("jobs_type_check", "processing_jobs", _OLD_TYPES)
    op.drop_index("ix_run_events_run_seq", table_name="run_events")
    op.drop_table("run_events")
