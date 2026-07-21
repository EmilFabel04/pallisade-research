"""enable pgvector

Revision ID: 0004_pgvector_extension
Revises: 0003_evaluation_runs
Create Date: 2026-05-25 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '0004_pgvector_extension'
down_revision: Union[str, Sequence[str], None] = '0003_evaluation_runs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP EXTENSION IF EXISTS vector")
