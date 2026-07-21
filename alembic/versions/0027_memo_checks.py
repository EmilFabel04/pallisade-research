from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0027_memo_checks"
down_revision = "0026_documents_org_scope"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "memo_checks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("memo_document_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("memo_text", sa.Text(), nullable=False),
        sa.Column("backing_document_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
                  nullable=False, server_default=sa.text("'{}'::uuid[]")),
        sa.Column("scope", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="queued"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.CheckConstraint("scope in ('attached','folder','both')", name="memo_checks_scope_check"),
        sa.CheckConstraint("status in ('queued','running','done','failed')",
                           name="memo_checks_status_check"),
    )
    op.create_index("ix_memo_checks_org_created", "memo_checks", ["org_id", "created_at"])
    op.create_table(
        "memo_claim_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("check_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("memo_checks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_text", sa.Text(), nullable=False),
        sa.Column("claim_value", sa.Text(), nullable=False),
        sa.Column("verdict", sa.String(), nullable=False),
        sa.Column("source_document_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("locator", sa.Text(), nullable=True),
        sa.Column("source_value", sa.Text(), nullable=True),
        sa.Column("source_as_of", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tier", sa.String(), nullable=False, server_default="doc"),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("char_start", sa.Integer(), nullable=True),
        sa.Column("char_end", sa.Integer(), nullable=True),
        sa.CheckConstraint("verdict in ('match','mismatch','stale','unsupported')",
                           name="memo_claim_results_verdict_check"),
    )
    op.create_index("ix_memo_claim_results_check", "memo_claim_results", ["check_id"])
    op.drop_constraint("jobs_type_check", "processing_jobs", type_="check")
    op.create_check_constraint(
        "jobs_type_check", "processing_jobs",
        "job_type in ('parse_document','embed_document','evaluate_deal',"
        "'run_debate','check_memo')",
    )


def downgrade() -> None:
    op.drop_constraint("jobs_type_check", "processing_jobs", type_="check")
    op.create_check_constraint(
        "jobs_type_check", "processing_jobs",
        "job_type in ('parse_document','embed_document','evaluate_deal','run_debate')",
    )
    op.drop_table("memo_claim_results")
    op.drop_table("memo_checks")
