from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from pallisade_core.memo_checks.extract import ExtractedFigure

ADJUDICATE_TOOL = {
    "name": "adjudicate_figure",
    "description": "Decide whether a memo figure is backed by one of the source passages.",
    "input_schema": {
        "type": "object",
        "properties": {
            "found": {"type": "boolean",
                      "description": "True if a passage states this figure's quantity."},
            "agrees": {"type": "boolean",
                       "description": "True if the source value matches the memo value "
                                      "(allow rounding/units within ~1%)."},
            "candidate_index": {"type": ["integer", "null"],
                                "description": "Index of the passage that backs it, or null."},
            "source_value": {"type": ["string", "null"],
                             "description": "The value as stated in the source, or null."},
            "rationale": {"type": "string"},
        },
        "required": ["found", "agrees", "candidate_index", "source_value", "rationale"],
    },
}

_SYSTEM = (
    "You fact-check one figure from an analyst's memo against source passages from "
    "the analyst's own documents. Decide only whether a passage states the same "
    "quantity (found) and whether it matches within rounding/unit tolerance (agrees). "
    "Never use outside knowledge; judge only from the passages provided."
)


@dataclass(frozen=True)
class SourceCandidate:
    document_id: str | None
    text: str
    filename: str
    locator: str
    as_of: date | None


@dataclass(frozen=True)
class ClaimVerdict:
    verdict: str
    source_document_id: str | None
    source_value: str | None
    locator: str | None
    source_as_of: date | None
    rationale: str


def _prompt(figure: ExtractedFigure, candidates: list[SourceCandidate]) -> str:
    passages = "\n".join(
        f"[{i}] ({c.filename}) {c.text}" for i, c in enumerate(candidates)
    )
    return (
        f'MEMO FIGURE: "{figure.claim_text}" (value={figure.value} {figure.unit})\n\n'
        f"SOURCE PASSAGES:\n{passages}\n\n"
        "Adjudicate this figure against the passages."
    )


def adjudicate(
    figure: ExtractedFigure, candidates: list[SourceCandidate], *,
    sdk: Any, model: str, memo_date: date, stale_days: int,
) -> ClaimVerdict:
    if not candidates:
        return ClaimVerdict(
            "unsupported", None, None, None, None,
            "No backing document contained this figure.",
        )

    msg = sdk.messages.create(
        model=model,
        max_tokens=512,
        system=[{"type": "text", "text": _SYSTEM}],
        tools=[ADJUDICATE_TOOL],
        tool_choice={"type": "tool", "name": "adjudicate_figure"},
        messages=[{"role": "user", "content": _prompt(figure, candidates)}],
    )
    payload = next(
        (b.input for b in msg.content if getattr(b, "type", "") == "tool_use"), None
    )
    if payload is None or not payload.get("found"):
        return ClaimVerdict("unsupported", None, None, None, None,
                            (payload or {}).get("rationale", "Not found in sources."))

    idx = payload.get("candidate_index")
    cand = candidates[idx] if isinstance(idx, int) and 0 <= idx < len(candidates) else candidates[0]
    rationale = payload.get("rationale", "")

    if not payload.get("agrees"):
        return ClaimVerdict("mismatch", cand.document_id, payload.get("source_value"),
                            cand.locator, cand.as_of, rationale)

    # agrees → match, unless the source is materially older than the memo.
    if cand.as_of is not None and (memo_date - cand.as_of).days > stale_days:
        return ClaimVerdict("stale", cand.document_id, payload.get("source_value"),
                            cand.locator, cand.as_of, rationale)
    return ClaimVerdict("match", cand.document_id, payload.get("source_value"),
                        cand.locator, cand.as_of, rationale)
