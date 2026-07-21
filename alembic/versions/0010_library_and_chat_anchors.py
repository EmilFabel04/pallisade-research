"""library_documents + library_chunks + chat anchor discriminator

Revises: 0009_evaluation_results
Create Date: 2026-05-27
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

from pallisade_core.settings import get_settings

revision: str = "0010_library_and_chat_anchors"
down_revision: Union[str, Sequence[str], None] = "0009_evaluation_results"
branch_labels = None
depends_on = None


def upgrade() -> None:
    dim = get_settings().embed_dim

    op.create_table(
        "library_documents",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True),
                  server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("run_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("evaluation_runs.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("ticker", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("body_md", sa.Text(), nullable=False),
        sa.Column("storage_key", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "kind in ('market_report','sentiment_report','news_report',"
            "'fundamentals_report','investment_plan','trader_investment_plan',"
            "'final_trade_decision')",
            name="library_documents_kind_check",
        ),
        sa.UniqueConstraint("run_id", "kind", name="uq_library_run_kind"),
    )
    op.create_index("ix_library_ticker_created", "library_documents",
                    ["ticker", "created_at"], unique=False,
                    postgresql_using="btree",
                    postgresql_ops={"created_at": "DESC"})
    op.create_index("ix_library_kind_created", "library_documents",
                    ["kind", "created_at"], unique=False,
                    postgresql_using="btree",
                    postgresql_ops={"created_at": "DESC"})

    op.create_table(
        "library_chunks",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True),
                  server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("library_doc_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("library_documents.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(dim), nullable=True),
    )
    op.execute(
        "CREATE INDEX ix_library_chunks_hnsw ON library_chunks "
        "USING hnsw (embedding vector_cosine_ops)"
    )

    # Chat anchor discriminator
    op.add_column(
        "chat_conversations",
        sa.Column("library_doc_id", sa.dialects.postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("library_documents.id", ondelete="CASCADE"),
                  nullable=True),
    )
    op.add_column(
        "chat_conversations",
        sa.Column("kind", sa.String(), nullable=False,
                  server_default="deal"),
    )
    # Existing unique on (deal_id, user_id) must go — deal_id is now nullable in
    # practice for library/global rows. Replace with partial uniques per kind.
    op.drop_constraint("uq_chat_conv_deal_user", "chat_conversations",
                       type_="unique")
    # Allow deal_id NULL by altering nullability.
    op.alter_column("chat_conversations", "deal_id", nullable=True)

    op.create_check_constraint(
        "chat_anchor_exclusive",
        "chat_conversations",
        "(kind='deal'        AND deal_id IS NOT NULL AND library_doc_id IS NULL) "
        "OR (kind='library_doc' AND library_doc_id IS NOT NULL AND deal_id IS NULL) "
        "OR (kind='global'      AND deal_id IS NULL AND library_doc_id IS NULL)",
    )
    op.create_index(
        "uq_chat_conv_deal_user_partial",
        "chat_conversations", ["deal_id", "user_id"],
        unique=True, postgresql_where=sa.text("kind = 'deal'"),
    )
    op.create_index(
        "uq_chat_conv_libdoc_user_partial",
        "chat_conversations", ["library_doc_id", "user_id"],
        unique=True, postgresql_where=sa.text("kind = 'library_doc'"),
    )
    op.create_index(
        "uq_chat_conv_global_user_partial",
        "chat_conversations", ["user_id"],
        unique=True, postgresql_where=sa.text("kind = 'global'"),
    )


def downgrade() -> None:
    op.drop_index("uq_chat_conv_global_user_partial", table_name="chat_conversations")
    op.drop_index("uq_chat_conv_libdoc_user_partial", table_name="chat_conversations")
    op.drop_index("uq_chat_conv_deal_user_partial", table_name="chat_conversations")
    op.drop_constraint("chat_anchor_exclusive", "chat_conversations", type_="check")
    op.alter_column("chat_conversations", "deal_id", nullable=False)
    op.create_unique_constraint("uq_chat_conv_deal_user",
                                "chat_conversations", ["deal_id", "user_id"])
    op.drop_column("chat_conversations", "kind")
    op.drop_column("chat_conversations", "library_doc_id")

    op.execute("DROP INDEX IF EXISTS ix_library_chunks_hnsw")
    op.drop_table("library_chunks")
    op.drop_index("ix_library_kind_created", table_name="library_documents")
    op.drop_index("ix_library_ticker_created", table_name="library_documents")
    op.drop_table("library_documents")
