"""Schema for the durable run_events log (slice 2)."""
from __future__ import annotations

from sqlalchemy import inspect, text


def test_run_events_table_exists_with_columns(_migrate, db):
    cols = {c["name"] for c in inspect(db.get_bind()).get_columns("run_events")}
    assert {"id", "run_id", "seq", "type", "payload", "created_at"} <= cols


def test_run_events_unique_run_seq(_migrate, db):
    uniques = inspect(db.get_bind()).get_unique_constraints("run_events")
    names = {u["name"] for u in uniques}
    assert "uq_run_events_run_seq" in names


def test_processing_jobs_accepts_run_debate(_migrate, db):
    # The CHECK constraint must admit the new job type.
    db.execute(
        text(
            "INSERT INTO processing_jobs (job_type, status, payload) "
            "VALUES ('run_debate', 'queued', '{}'::jsonb)"
        )
    )
    db.flush()
