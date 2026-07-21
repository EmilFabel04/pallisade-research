from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0024_watchlist_items"
down_revision = "0023_run_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "watchlist_items",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("conviction", sa.String(length=16), nullable=False, server_default="watch"),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("user_id", "ticker", name="uq_watchlist_items_user_ticker"),
        sa.CheckConstraint(
            "conviction in ('bull','bear','watch')",
            name="watchlist_items_conviction_check",
        ),
    )
    op.create_index(
        "ix_watchlist_items_user_created",
        "watchlist_items",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_watchlist_items_user_created", table_name="watchlist_items")
    op.drop_table("watchlist_items")
