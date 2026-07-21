"""run_debate handler — resolves run_id and delegates to the debate runner.

Mirrors handlers/evaluation.py::handle_evaluate_deal. Intentionally thin.
"""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from pallisade_core.documents.models import ProcessingJob
from pallisade_core.errors import HardError


def handle_run_debate(session: Session, job: ProcessingJob, doc=None) -> None:
    """`doc` is always None for run_debate jobs; ignored.

    The runner deliberately does NOT use `session`: it opens its own committed
    sessions so events stream live (spec §5.2).
    """
    if not isinstance(job.payload, dict) or "run_id" not in job.payload:
        raise HardError("run_debate job missing payload.run_id")
    try:
        run_id = uuid.UUID(job.payload["run_id"])
    except (TypeError, ValueError) as exc:
        raise HardError(f"run_debate job has malformed run_id: {exc}") from exc

    from pallisade_worker.debate_runner import run_debate
    run_debate(run_id=run_id)
