"""processing_jobs

Revision ID: 0006_processing_jobs
Revises: 0005_documents
Create Date: 2026-05-25 14:20:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0006_processing_jobs'
down_revision: Union[str, Sequence[str], None] = '0005_documents'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'processing_jobs',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('job_type', sa.String(), nullable=False),
        sa.Column('document_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(), server_default=sa.text("'queued'"), nullable=False),
        sa.Column('attempts', sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column('max_attempts', sa.Integer(), server_default=sa.text("3"), nullable=False),
        sa.Column('locked_by', sa.String(), nullable=True),
        sa.Column('locked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('heartbeat_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("job_type in ('parse_document','embed_document')", name='jobs_type_check'),
        sa.CheckConstraint("status in ('queued','running','done','failed')", name='jobs_status_check'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_jobs_queued_created', 'processing_jobs', ['status', 'created_at'],
        unique=False, postgresql_where=sa.text("status = 'queued'"),
    )
    op.create_index('ix_jobs_heartbeat', 'processing_jobs', ['heartbeat_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_jobs_heartbeat', table_name='processing_jobs')
    op.drop_index('ix_jobs_queued_created', table_name='processing_jobs')
    op.drop_table('processing_jobs')
