from __future__ import annotations

import logging
import os
import socket
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Callable

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from pallisade_core.documents.models import Document, ProcessingJob

log = logging.getLogger(__name__)

Handler = Callable[[Session, ProcessingJob, "Document | None"], None]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def default_worker_id() -> str:
    return f"{socket.gethostname()}:{os.getpid()}"


def claim_one(session: Session, *, worker_id: str) -> ProcessingJob | None:
    """SELECT FOR UPDATE SKIP LOCKED, mark as running, return the job or None."""
    job = session.execute(
        select(ProcessingJob)
        .where(ProcessingJob.status == "queued")
        .order_by(ProcessingJob.created_at)
        .limit(1)
        .with_for_update(skip_locked=True)
    ).scalar_one_or_none()
    if job is None:
        return None
    now = _now()
    job.status = "running"
    job.locked_by = worker_id
    job.locked_at = now
    job.heartbeat_at = now
    job.started_at = job.started_at or now
    job.attempts = job.attempts + 1
    session.flush()
    return job


def heartbeat(session: Session, *, job: ProcessingJob) -> None:
    job.heartbeat_at = _now()
    session.flush()


def reap_zombies(session: Session, *, stale_after_seconds: int = 60) -> int:
    """Requeue jobs whose heartbeat is older than the threshold. Returns count."""
    cutoff = _now() - timedelta(seconds=stale_after_seconds)
    rows = session.execute(
        update(ProcessingJob)
        .where(
            ProcessingJob.status == "running",
            ProcessingJob.heartbeat_at.is_not(None),
            ProcessingJob.heartbeat_at < cutoff,
        )
        .values(status="queued", locked_by=None, locked_at=None, heartbeat_at=None)
        .returning(ProcessingJob.id)
    ).all()
    session.flush()
    return len(rows)


def _heartbeat_thread(
    job_id: int,
    stop_event: threading.Event,
    interval: float,
) -> None:
    """Background thread: refreshes heartbeat_at every `interval` seconds."""
    from pallisade_core.db.session import get_engine
    from sqlalchemy.orm import sessionmaker

    SessionLocal = sessionmaker(bind=get_engine(), expire_on_commit=False, future=True)
    while not stop_event.wait(interval):
        try:
            with SessionLocal() as hb_session:
                hb_session.execute(
                    update(ProcessingJob)
                    .where(ProcessingJob.id == job_id)
                    .values(heartbeat_at=_now())
                )
                hb_session.commit()
        except Exception:                              # noqa: BLE001
            log.warning("heartbeat update failed for job %s", job_id)


def run_once(
    session: Session, *, handlers: dict[str, Handler], worker_id: str,
    heartbeat_interval_seconds: float = 10.0,
) -> bool:
    """Claim one job and run its handler. Returns True if a job was processed."""
    job = claim_one(session, worker_id=worker_id)
    if job is None:
        return False
    if job.document_id is not None:
        doc = session.get(Document, job.document_id)
        if doc is None:
            job.status = "failed"
            job.error_message = "document not found"
            job.completed_at = _now()
            session.flush()
            return True
    else:
        doc = None
    handler = handlers.get(job.job_type)
    if handler is None:
        job.status = "failed"
        job.error_message = f"no handler for job_type={job.job_type}"
        job.completed_at = _now()
        session.flush()
        return True

    stop_event = threading.Event()
    hb_thread = threading.Thread(
        target=_heartbeat_thread,
        args=(job.id, stop_event, heartbeat_interval_seconds),
        daemon=True,
    )
    hb_thread.start()
    try:
        handler(session, job, doc)
        job.status = "done"
        job.completed_at = _now()
        session.flush()
    except Exception as exc:                          # noqa: BLE001
        log.exception("job %s failed", job.id)
        from pallisade_core.errors import HardError
        is_hard = isinstance(exc, HardError)
        if not is_hard and job.attempts < job.max_attempts:
            job.status = "queued"
            job.locked_by = None
            job.locked_at = None
            job.heartbeat_at = None
            job.error_message = str(exc)
        else:
            job.status = "failed"
            job.completed_at = _now()
            job.error_message = str(exc)
            if doc is not None:
                doc.status = "failed"
                doc.error_message = str(exc)
        session.flush()
    finally:
        stop_event.set()
        hb_thread.join(timeout=heartbeat_interval_seconds + 2)
    return True


def run_forever(
    *, handlers: dict[str, Handler], poll_seconds: int = 2,
    stale_after_seconds: int = 60, worker_id: str | None = None,
) -> None:
    """Production entrypoint. Opens its own session per loop iteration."""
    from pallisade_core.db.session import get_engine
    from sqlalchemy.orm import sessionmaker

    wid = worker_id or default_worker_id()
    SessionLocal = sessionmaker(bind=get_engine(), expire_on_commit=False, future=True)
    log.info("pallisade-worker starting id=%s", wid)
    while True:
        with SessionLocal() as session:
            try:
                reap_zombies(session, stale_after_seconds=stale_after_seconds)
                session.commit()
            except Exception:                          # noqa: BLE001
                log.exception("reaper failed")
                session.rollback()
        with SessionLocal() as session:
            try:
                did_work = run_once(session, handlers=handlers, worker_id=wid)
                session.commit()
            except Exception:                          # noqa: BLE001
                log.exception("run_once failed")
                session.rollback()
                did_work = False
        if not did_work:
            time.sleep(poll_seconds)
