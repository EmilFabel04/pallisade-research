from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from pallisade_core.runs.models import EvaluationRun
from pallisade_core.users.models import User


def create_public_run(
    session: Session, *, user: User, ticker: str, params: dict | None = None
) -> EvaluationRun:
    if not ticker or not ticker.strip():
        raise ValueError("ticker required for public runs")
    run = EvaluationRun(
        mode="public",
        user_id=user.id,
        ticker=ticker.strip().upper(),
        status="queued",
        params=params,
    )
    session.add(run)
    return run


def append_report(session: Session, *, run: EvaluationRun, key: str, content: str) -> None:
    """Add/overwrite one report key. Reassigns the dict so JSONB change is flushed."""
    run.reports = {**(run.reports or {}), key: content}
    session.add(run)


def save_result(session: Session, *, run: EvaluationRun, result: dict) -> None:
    run.result = result
    session.add(run)


def get_run(session: Session, run_id) -> EvaluationRun | None:
    return session.get(EvaluationRun, run_id)


def list_for_user(
    session: Session, *, user: User,
    kind: str | None = None, limit: int | None = None,
) -> list[EvaluationRun]:
    stmt = select(EvaluationRun).where(EvaluationRun.user_id == user.id)
    if kind == "analysts":
        # kind is a public-run concept; scope out private (deal) runs, which
        # have no `analysts_only` key and would otherwise be misclassified.
        stmt = stmt.where(
            EvaluationRun.mode == "public",
            EvaluationRun.params["analysts_only"].astext == "true",
        )
    elif kind == "debate":
        # NULL params or missing/false flag ⇒ debate run.
        stmt = stmt.where(
            EvaluationRun.mode == "public",
            func.coalesce(EvaluationRun.params["analysts_only"].astext, "false") != "true",
        )
    stmt = stmt.order_by(EvaluationRun.created_at.desc())
    if limit is not None:
        stmt = stmt.limit(limit)
    return list(session.execute(stmt).scalars().all())


def prune_runs(session: Session, *, user: User, kind: str, keep: int = 5) -> int:
    """Hard-delete this user's runs of `kind` beyond the `keep` newest.

    Deletion cascades to run_events and library_documents via ondelete=CASCADE.
    Returns the number of runs deleted.
    """
    rows = list_for_user(session, user=user, kind=kind)  # newest-first
    stale = rows[keep:]
    for run in stale:
        session.delete(run)
    return len(stale)


def mark_status(
    session: Session,
    *,
    run: EvaluationRun,
    status: str,
    artifacts_root_key: str | None = None,
    error_message: str | None = None,
) -> EvaluationRun:
    run.status = status
    if artifacts_root_key is not None:
        run.artifacts_root_key = artifacts_root_key
    if error_message is not None:
        run.error_message = error_message
    if status in {"done", "failed"}:
        run.completed_at = datetime.now(timezone.utc)
    session.add(run)
    return run


def can_view_public_run(*, viewer: User, run: EvaluationRun) -> bool:
    return viewer.role == "admin" or run.user_id == viewer.id


def _has_ready_documents(session, *, deal):
    from pallisade_core.documents.models import Document
    from sqlalchemy import select
    n = session.scalar(
        select(Document)
        .where(
            Document.deal_id == deal.id,
            Document.status == "ready",
            Document.deleted_at.is_(None),
        )
        .limit(1)
    )
    return n is not None


def _has_inflight_private_run(session, *, deal):
    from pallisade_core.runs.models import EvaluationRun
    from sqlalchemy import select
    row = session.execute(
        select(EvaluationRun)
        .where(
            EvaluationRun.deal_id == deal.id,
            EvaluationRun.mode == "private",
            EvaluationRun.status.in_(("queued", "running")),
        )
        .limit(1)
    ).scalar_one_or_none()
    return row is not None


def create_private_run(session, *, user, deal, thesis, params):
    """Insert evaluation_runs + processing_jobs in one transaction.

    Raises HardError on precondition failures so the API can map them to 409.
    """
    from pallisade_core.documents.models import ProcessingJob
    from pallisade_core.errors import HardError
    from pallisade_core.runs.models import EvaluationRun

    if not _has_ready_documents(session, deal=deal):
        raise HardError("deal has no processed documents — upload + wait for ingestion")
    if _has_inflight_private_run(session, deal=deal):
        raise HardError("evaluation already in flight; wait or refresh")

    run = EvaluationRun(
        mode="private",
        user_id=user.id,
        deal_id=deal.id,
        ticker=None,
        status="queued",
        thesis=thesis,
        params=params,
    )
    session.add(run)
    session.flush()
    run.artifacts_root_key = f"runs/{run.id}/"

    job = ProcessingJob(
        job_type="evaluate_deal",
        document_id=None,
        payload={"run_id": str(run.id)},
        status="queued",
        max_attempts=1,
    )
    session.add(job)
    session.flush()
    return run


def list_private_runs_for_deal(session, *, deal):
    from pallisade_core.runs.models import EvaluationRun
    from sqlalchemy import desc, select
    return list(session.execute(
        select(EvaluationRun)
        .where(EvaluationRun.deal_id == deal.id, EvaluationRun.mode == "private")
        .order_by(desc(EvaluationRun.created_at))
    ).scalars())


def create_public_run_job(session, *, run):
    """Enqueue the durable debate job for a public run.

    max_attempts=1: a retry re-spends real LLM money and would append a second
    copy of the argument to the same event log (spec §D4).
    """
    from pallisade_core.documents.models import ProcessingJob

    job = ProcessingJob(
        job_type="run_debate",
        document_id=None,
        payload={"run_id": str(run.id)},
        status="queued",
        max_attempts=1,
    )
    session.add(job)
    session.flush()
    return job
