"""The durable debate engine. Runs on the worker; streams every event to run_events.

Replaces slice 1's in-process API thread (`web/api/routers/runs.py::_execute_run`).
"""
from __future__ import annotations

import logging
import traceback
import uuid

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from sqlalchemy import update

from pallisade_core.db.session import get_session_factory
from pallisade_core.errors import HardError
from pallisade_core.library import service as lib_service
from pallisade_core.runs import service as runs_service
from pallisade_core.runs.events import RunEventEmitter
from pallisade_core.runs.models import EvaluationRun
from pallisade_core.runs.turns import extract_turns

log = logging.getLogger("pallisade.debate")

REPORT_KEYS = [
    "market_report", "sentiment_report", "news_report", "fundamentals_report",
    "investment_plan", "trader_investment_plan", "final_trade_decision",
]


class _EmitterCallback(BaseCallbackHandler):
    """Slice 1's _WebStreamCallback, rewired from the in-memory list to the log."""

    def __init__(self, emitter: RunEventEmitter) -> None:
        super().__init__()
        self.emitter = emitter
        self.llm_calls = 0
        self.tool_calls = 0

    def _label(self, kwargs: dict) -> str:
        tags = kwargs.get("tags") or []
        if tags:
            return tags[-1]
        meta = kwargs.get("metadata") or {}
        return meta.get("langgraph_node") or "agent"

    def _status(self, message: str) -> None:
        try:
            self.emitter.emit("status", {"state": "running", "message": message})
        except Exception:  # noqa: BLE001 — status noise must never kill a debate
            log.warning("failed to emit status event", exc_info=True)

    def on_chat_model_start(self, serialized, messages, **kw):
        self.llm_calls += 1
        self._status(f"→ LLM call #{self.llm_calls} ({self._label(kw)})")

    def on_llm_start(self, serialized, prompts, **kw):
        self.llm_calls += 1
        self._status(f"→ LLM call #{self.llm_calls} ({self._label(kw)})")

    def on_llm_end(self, response: LLMResult, **kw):
        toks_in = toks_out = 0
        try:
            gen = response.generations[0][0]
            msg = getattr(gen, "message", None)
            usage = getattr(msg, "usage_metadata", None) if msg else None
            if usage:
                toks_in = usage.get("input_tokens", 0)
                toks_out = usage.get("output_tokens", 0)
        except (IndexError, TypeError, AttributeError):
            pass
        self._status(f"✓ LLM done · {toks_in} in / {toks_out} out")

    def on_tool_start(self, serialized, input_str, **kw):
        self.tool_calls += 1
        name = (serialized or {}).get("name", "tool")
        snippet = (input_str or "").strip().replace("\n", " ")
        if len(snippet) > 80:
            snippet = snippet[:77] + "…"
        self._status(f"🔧 tool: {name}({snippet})")

    def on_tool_end(self, output, **kw):
        self._status("✓ tool returned")

    def on_tool_error(self, error, **kw):
        self._status(f"✗ tool error: {error}")


def _build_config(params: dict) -> dict:
    from tradingagents.default_config import DEFAULT_CONFIG
    cfg = DEFAULT_CONFIG.copy()
    for key in ("llm_provider", "deep_think_llm", "quick_think_llm"):
        if params.get(key):
            cfg[key] = params[key]
    if params.get("max_debate_rounds") is not None:
        cfg["max_debate_rounds"] = params["max_debate_rounds"]
    if params.get("org_id"):
        cfg["org_id"] = params["org_id"]
    return cfg


def _default_graph_factory(*, analysts, analysts_only, config, callbacks):
    from tradingagents.graph.trading_graph import TradingAgentsGraph
    return TradingAgentsGraph(
        selected_analysts=analysts, analysts_only=analysts_only,
        debug=False, config=config, callbacks=callbacks,
    )


def _persist_report(sf, run_id, key: str, content: str) -> None:
    try:
        with sf() as s:
            row = runs_service.get_run(s, run_id)
            if row is None:
                return
            runs_service.append_report(s, run=row, key=key, content=content)
            s.commit()
    except Exception:  # noqa: BLE001
        log.exception("failed to persist report %s for run %s", key, run_id)


def _ingest_library(s, row, result: dict) -> None:
    lib_service.ingest_run(s, run=row, reports=result or {})


def _finalize(sf, run_id, *, result: dict | None, success: bool, error: str | None = None) -> None:
    """Mark the run terminal. MUST be called only after the terminal event is emitted (§5.3)."""
    with sf() as s:
        row = runs_service.get_run(s, run_id)
        if row is None:
            return
        if success:
            runs_service.save_result(s, run=row, result=result or {})
            runs_service.mark_status(
                s, run=row, status="done", artifacts_root_key=f"runs/{row.id}/"
            )
            try:
                _ingest_library(s, row, result or {})
            except Exception as exc:  # noqa: BLE001
                log.exception("library ingest failed for run %s", run_id)
                runs_service.mark_status(
                    s, run=row, status="done",
                    error_message=f"library_ingest_failed: {exc!r}",
                )
        else:
            runs_service.mark_status(s, run=row, status="failed", error_message=error)
        s.commit()


def run_debate(*, run_id: uuid.UUID, session_factory=None, graph_factory=None) -> None:
    sf = session_factory or get_session_factory()

    with sf() as s:
        row = runs_service.get_run(s, run_id)
        if row is None:
            raise HardError(f"run_debate: run {run_id} not found")

        # Atomic claim: only the transition queued -> running may proceed. This is a
        # compare-and-set rather than a read-then-check because reap_zombies (loop.py)
        # can requeue a stale job WITHOUT consulting max_attempts, so a second worker
        # may legitimately claim the job. Re-running would append a second copy of the
        # argument at fresh seqs (the UI dedupes by seq, so BOTH would render) and
        # re-spend the LLM budget. Do not weaken this to a SELECT-then-check: that
        # would depend on claim_one's job-row lock, an invariant this module does not own.
        claimed = s.execute(
            update(EvaluationRun)
            .where(EvaluationRun.id == run_id, EvaluationRun.status == "queued")
            .values(status="running")
        ).rowcount

        if not claimed:
            # `row` may be stale — it could have shown "queued" and lost the
            # compare-and-set race to a concurrent claim. Re-read to find the
            # ACTUAL current status before deciding what to do.
            s.refresh(row)
            if row.status == "running":
                # An interrupted, re-claimed run with no live worker (reap_zombies
                # requeued the job without checking max_attempts). The guard above
                # correctly refuses to re-run it, but nothing was finalizing the RUN:
                # stream_run's SSE loop only terminates on a terminal status, so an
                # open/reopened tab would poll forever. Finalize it as failed instead.
                emitter = RunEventEmitter(run_id=run_id, session_factory=sf)
                err = (
                    "run was interrupted and re-claimed; refusing to re-run "
                    "(would duplicate the argument and re-spend the LLM budget)"
                )
                try:
                    emitter.emit("error", {"error": err})
                except Exception:  # noqa: BLE001
                    log.exception("failed to emit error event for run %s", run_id)
                # §5.3: terminal event BEFORE the status flip.
                _finalize(sf, run_id, result=None, success=False, error=err)
                raise HardError(
                    f"run_debate: run {run_id} was left running by an interrupted "
                    f"attempt — finalized as failed, refusing re-entry."
                )
            # Already terminal (done/failed) — a completed run must never be
            # overwritten. Leave it exactly as is.
            raise HardError(
                f"run_debate: run {run_id} already {row.status} — refusing re-entry. "
                f"reap_zombies can requeue a stale job without checking max_attempts; "
                f"re-running would append a second copy of the argument and re-spend the LLM budget."
            )

        ticker = row.ticker
        params = dict(row.params or {})
        s.commit()

    emitter = RunEventEmitter(run_id=run_id, session_factory=sf)
    make_graph = graph_factory or _default_graph_factory

    try:
        emitter.emit("status", {"state": "running", "message": "Initializing graph"})
        cb = _EmitterCallback(emitter)
        analysts = params.get("analysts") or ["market", "social", "news", "fundamentals"]
        analysts_only = bool(params.get("analysts_only"))
        graph = make_graph(
            analysts=analysts, analysts_only=analysts_only,
            config=_build_config(params), callbacks=[cb],
        )
        emitter.emit("status", {"state": "running", "message": "Starting agent pipeline"})

        trade_date = params.get("trade_date")
        asset_type = params.get("asset_type", "stock")
        init_state = graph.propagator.create_initial_state(
            ticker, trade_date, asset_type=asset_type,
            past_context=graph.memory_log.get_past_context(ticker),
        )
        args = graph.propagator.get_graph_args(callbacks=[cb])

        final_state: dict = {}
        prev_state: dict = {}
        seen: set[str] = set()
        for chunk in graph.graph.stream(init_state, **args):
            if not isinstance(chunk, dict):
                continue
            for turn in extract_turns(prev_state, chunk):
                emitter.emit("turn", turn.as_payload())
            prev_state = chunk
            final_state.update(chunk)
            for key in REPORT_KEYS:
                if key in chunk and chunk[key] and key not in seen:
                    seen.add(key)
                    value = chunk[key]
                    content = value if isinstance(value, str) else str(value)
                    emitter.emit("report", {"key": key, "content": content})
                    _persist_report(sf, run_id, key, content)

        graph.curr_state = final_state
        try:
            graph._log_state(trade_date, final_state)
            graph.memory_log.store_decision(
                ticker=ticker, trade_date=trade_date,
                final_trade_decision=final_state.get("final_trade_decision", ""),
            )
        except Exception:  # noqa: BLE001
            log.exception("post-run logging failed (non-fatal)")

        result = {k: final_state.get(k) for k in REPORT_KEYS if k in final_state}
        # §5.3: terminal event FIRST, status second.
        emitter.emit("done", {"reports": sorted(seen)})
        _finalize(sf, run_id, result=result, success=True)
    except Exception as exc:  # noqa: BLE001
        err = f"{type(exc).__name__}: {exc}"
        log.exception("debate run %s failed", run_id)
        try:
            emitter.emit("error", {"error": err, "traceback": traceback.format_exc()})
        except Exception:  # noqa: BLE001
            log.exception("failed to emit error event for run %s", run_id)
        _finalize(sf, run_id, result=None, success=False, error=err)
        # HardError so the loop marks the job failed without retrying (spec §D4).
        raise HardError(err) from exc
