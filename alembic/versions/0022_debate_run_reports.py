from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0022_debate_run_reports"
down_revision = "0021_organizations_and_data_connections"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "evaluation_runs",
        sa.Column(
            "reports",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.add_column(
        "evaluation_runs",
        sa.Column("result", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("evaluation_runs", "result")
    op.drop_column("evaluation_runs", "reports")
