"""chat_conversations + chat_messages

Revision ID: 0007_chat
Revises: 0006_processing_jobs
Create Date: 2026-05-25 14:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0007_chat'
down_revision: Union[str, Sequence[str], None] = '0006_processing_jobs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'chat_conversations',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('deal_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('deal_id', 'user_id', name='uq_chat_conv_deal_user'),
        sa.ForeignKeyConstraint(['deal_id'], ['deals.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'chat_messages',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('conversation_id', sa.UUID(), nullable=False),
        sa.Column('ordinal', sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('citations', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("role in ('user','assistant')", name='chat_messages_role_check'),
        sa.ForeignKeyConstraint(['conversation_id'], ['chat_conversations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_chat_messages_conv_created', 'chat_messages', ['conversation_id', 'created_at'])
    op.create_index('ix_chat_messages_conv_ordinal', 'chat_messages', ['conversation_id', 'ordinal'])


def downgrade() -> None:
    op.drop_index('ix_chat_messages_conv_ordinal', table_name='chat_messages')
    op.drop_index('ix_chat_messages_conv_created', table_name='chat_messages')
    op.drop_table('chat_messages')
    op.drop_table('chat_conversations')
