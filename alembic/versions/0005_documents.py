"""documents + document_chunks

Revision ID: 0005_documents
Revises: 0004_pgvector_extension
Create Date: 2026-05-25 14:10:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from pallisade_core.settings import get_settings

revision: str = '0005_documents'
down_revision: Union[str, Sequence[str], None] = '0004_pgvector_extension'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'documents',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('deal_id', sa.UUID(), nullable=False),
        sa.Column('uploader_id', sa.UUID(), nullable=False),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('storage_key', sa.String(), nullable=False),
        sa.Column('content_type', sa.String(), nullable=False),
        sa.Column('byte_size', sa.BigInteger(), nullable=False),
        sa.Column('sha256', sa.String(), nullable=False),
        sa.Column('source_kind', sa.String(), nullable=False),
        sa.Column('status', sa.String(), server_default=sa.text("'pending'"), nullable=False),
        sa.Column('page_count', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("source_kind in ('pdf_text','pdf_scan','xlsx')", name='documents_source_kind_check'),
        sa.CheckConstraint(
            "status in ('pending','parsing','embedding','ready','failed')",
            name='documents_status_check',
        ),
        sa.ForeignKeyConstraint(['deal_id'], ['deals.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['uploader_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ux_documents_deal_sha256_active', 'documents', ['deal_id', 'sha256'],
        unique=True, postgresql_where=sa.text('deleted_at IS NULL'),
    )
    op.create_index(
        'ix_documents_deal_status_created', 'documents',
        ['deal_id', 'status', 'created_at'], unique=False,
    )

    dim = get_settings().embed_dim
    op.create_table(
        'document_chunks',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('document_id', sa.UUID(), nullable=False),
        sa.Column('deal_id', sa.UUID(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('page_from', sa.Integer(), nullable=True),
        sa.Column('page_to', sa.Integer(), nullable=True),
        sa.Column('sheet_name', sa.String(), nullable=True),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('token_count', sa.Integer(), nullable=False),
        sa.Column('embedding', Vector(dim), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['deal_id'], ['deals.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_chunks_document_index', 'document_chunks', ['document_id', 'chunk_index'])
    op.create_index('ix_chunks_deal_id', 'document_chunks', ['deal_id'])
    op.execute(
        "CREATE INDEX ix_chunks_embedding_hnsw "
        "ON document_chunks USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.drop_index('ix_chunks_embedding_hnsw', table_name='document_chunks')
    op.drop_index('ix_chunks_deal_id', table_name='document_chunks')
    op.drop_index('ix_chunks_document_index', table_name='document_chunks')
    op.drop_table('document_chunks')
    op.drop_index('ix_documents_deal_status_created', table_name='documents')
    op.drop_index('ux_documents_deal_sha256_active', table_name='documents')
    op.drop_table('documents')
