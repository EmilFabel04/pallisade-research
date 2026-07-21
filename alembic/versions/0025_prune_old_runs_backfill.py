from __future__ import annotations

from alembic import op

revision = "0025_prune_old_runs_backfill"
down_revision = "0024_watchlist_items"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Per user, per kind (analysts_only true vs not), keep the 5 newest runs;
    # delete the rest. Cascades to run_events + library_documents. (spec §Backend.3)
    op.execute(
        """
        DELETE FROM evaluation_runs e
        USING (
            SELECT id, row_number() OVER (
                PARTITION BY user_id,
                    (COALESCE(params->>'analysts_only', 'false') = 'true')
                ORDER BY created_at DESC
            ) AS rn
            FROM evaluation_runs
            WHERE mode = 'public'
        ) ranked
        WHERE e.id = ranked.id AND ranked.rn > 5
        """
    )


def downgrade() -> None:
    # Irreversible data cleanup — no-op.
    pass
