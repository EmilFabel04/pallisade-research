"""evaluation_runs

Revision ID: 0003_evaluation_runs
Revises: 0002_deals
Create Date: 2026-05-25 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0003_evaluation_runs'
down_revision: Union[str, Sequence[str], None] = '0002_deals'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'evaluation_runs',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('mode', sa.String(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('deal_id', sa.UUID(), nullable=True),
        sa.Column('ticker', sa.String(), nullable=True),
        sa.Column('status', sa.String(), server_default=sa.text("'queued'"), nullable=False),
        sa.Column('artifacts_root_key', sa.String(), nullable=True),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("mode in ('public','private')", name='runs_mode_check'),
        sa.CheckConstraint(
            "status in ('queued','running','done','failed')", name='runs_status_check'
        ),
        sa.CheckConstraint(
            "(mode = 'public' and ticker is not null and deal_id is null) "
            "or (mode = 'private' and deal_id is not null)",
            name='runs_mode_consistency_check',
        ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['deal_id'], ['deals.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_runs_user_created', 'evaluation_runs', ['user_id', 'created_at'], unique=False)
    op.create_index('ix_runs_deal_created', 'evaluation_runs', ['deal_id', 'created_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_runs_deal_created', table_name='evaluation_runs')
    op.drop_index('ix_runs_user_created', table_name='evaluation_runs')
    op.drop_table('evaluation_runs')
