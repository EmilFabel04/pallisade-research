from __future__ import annotations

from sqlalchemy import text


def test_pgvector_extension_present(db):
    """Verify pgvector extension is installed by migration 0004."""
    rows = db.execute(text("SELECT extname FROM pg_extension WHERE extname='vector'")).all()
    assert len(rows) == 1, "pgvector extension should be installed by migration 0004"
