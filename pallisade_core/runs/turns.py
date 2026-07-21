"""Extract individual debate turns from langgraph 'values'-mode state chunks.

Pure: dicts in, dataclasses out. No DB, no langgraph import, no network — so the
riskiest logic in slice 2 is exhaustively testable without an LLM call.

The graph streams with stream_mode="values", so every chunk carries the FULL
state. A turn happened when the debate's `count` increased.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Turn:
    phase: str    # "invest" | "risk"
    speaker: str  # bull|bear | aggressive|conservative|neutral
    round: int
    text: str

    def as_payload(self) -> dict:
        return {
            "phase": self.phase,
            "speaker": self.speaker,
            "round": self.round,
            "text": self.text,
        }


# Prefixes the agent nodes write, e.g. bull_researcher.py: f"Bull Analyst: {...}"
_INVEST_PREFIXES = {"Bull Analyst:": "bull", "Bear Analyst:": "bear"}
_RISK_PREFIXES = {
    "Aggressive Analyst:": "aggressive",
    "Conservative Analyst:": "conservative",
    "Neutral Analyst:": "neutral",
}
# risk_debate_state["latest_speaker"] values, set by the risk_mgmt nodes.
_RISK_SPEAKERS = {
    "Aggressive": "aggressive",
    "Conservative": "conservative",
    "Neutral": "neutral",
}
_RISK_RESPONSE_KEY = {
    "aggressive": "current_aggressive_response",
    "conservative": "current_conservative_response",
    "neutral": "current_neutral_response",
}


def _count(state: dict | None, key: str) -> int:
    sub = (state or {}).get(key) or {}
    return sub.get("count") or 0


def _strip_prefix(text: str, mapping: dict[str, str]) -> tuple[str | None, str]:
    for prefix, speaker in mapping.items():
        if text.startswith(prefix):
            return speaker, text[len(prefix):].strip()
    return None, text


def _invest_turn(prev: dict | None, curr: dict) -> Turn | None:
    count = _count(curr, "investment_debate_state")
    if count <= _count(prev, "investment_debate_state"):
        return None
    raw = ((curr.get("investment_debate_state") or {}).get("current_response") or "").strip()
    if not raw:
        return None
    speaker, body = _strip_prefix(raw, _INVEST_PREFIXES)
    if speaker is None or not body:
        return None
    # 2 speakers per round: counts 1,2 -> round 1; 3,4 -> round 2.
    return Turn(phase="invest", speaker=speaker, round=(count + 1) // 2, text=body)


def _risk_turn(prev: dict | None, curr: dict) -> Turn | None:
    count = _count(curr, "risk_debate_state")
    if count <= _count(prev, "risk_debate_state"):
        return None
    state = curr.get("risk_debate_state") or {}
    speaker = _RISK_SPEAKERS.get(state.get("latest_speaker") or "")
    if speaker is None:
        return None
    raw = (state.get(_RISK_RESPONSE_KEY[speaker]) or "").strip()
    if not raw:
        return None
    _, body = _strip_prefix(raw, _RISK_PREFIXES)
    if not body:
        return None
    # 3 speakers per round: counts 1,2,3 -> round 1; 4 -> round 2.
    return Turn(phase="risk", speaker=speaker, round=(count + 2) // 3, text=body)


def extract_turns(prev: dict | None, curr: dict) -> list[Turn]:
    """Return the turns newly present in *curr* relative to *prev*. Invest first."""
    turns: list[Turn] = []
    for fn in (_invest_turn, _risk_turn):
        turn = fn(prev, curr)
        if turn is not None:
            turns.append(turn)
    return turns
