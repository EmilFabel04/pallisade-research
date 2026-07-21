from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0026_documents_org_scope"
down_revision = "0025_prune_old_runs_backfill"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "document_chunks",
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.alter_column("documents", "deal_id", existing_type=postgresql.UUID(as_uuid=True),
                    nullable=True)
    op.alter_column("document_chunks", "deal_id", existing_type=postgresql.UUID(as_uuid=True),
                    nullable=True)
    op.create_foreign_key(
        "documents_org_id_fkey", "documents", "organizations",
        ["org_id"], ["id"], ondelete="CASCADE",
    )
    op.create_foreign_key(
        "document_chunks_org_id_fkey", "document_chunks", "organizations",
        ["org_id"], ["id"], ondelete="CASCADE",
    )
    op.create_index(
        "ux_documents_org_sha256_active", "documents", ["org_id", "sha256"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL AND org_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ux_documents_org_sha256_active", table_name="documents")
    op.drop_constraint("document_chunks_org_id_fkey", "document_chunks", type_="foreignkey")
    op.drop_constraint("documents_org_id_fkey", "documents", type_="foreignkey")
    # Org-scoped documents (deal_id IS NULL) only exist because of this migration;
    # they cannot survive a downgrade that drops org_id and re-requires deal_id.
    op.execute("DELETE FROM documents WHERE deal_id IS NULL")
    op.alter_column("document_chunks", "deal_id", existing_type=postgresql.UUID(as_uuid=True),
                    nullable=False)
    op.alter_column("documents", "deal_id", existing_type=postgresql.UUID(as_uuid=True),
                    nullable=False)
    op.drop_column("document_chunks", "org_id")
    op.drop_column("documents", "org_id")
