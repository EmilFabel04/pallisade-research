"""Plain, DB-free view models the PDF renderer consumes.

The router assembles these from ORM rows; render.py has zero DB/HTTP knowledge,
so every renderer is unit-testable with hand-built fixtures.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RecordView:
    capability: str
    key: str
    value: str
    source: str
    locator: str
    as_of: str | None
    detail: str


@dataclass
class ClaimView:
    text: str
    records: list[RecordView] = field(default_factory=list)


@dataclass
class AnswerView:
    question: str
    claims: list[ClaimView] = field(default_factory=list)
    sources_used: list[str] = field(default_factory=list)
    sources_unavailable: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)


@dataclass
class MessageView:
    role: str            # "user" | "assistant"
    content: str         # narrative markdown
    answer: AnswerView | None = None


@dataclass
class ResearchConversationView:
    title: str
    generated_at: str    # ISO date string, supplied by the router
    messages: list[MessageView] = field(default_factory=list)


@dataclass
class ReportView:
    key: str
    label: str
    markdown: str


@dataclass
class TurnView:
    speaker: str   # "bull" | "bear"
    round: int
    text: str


@dataclass
class DebateView:
    ticker: str
    trade_date: str
    generated_at: str
    verdict: dict = field(default_factory=dict)   # {Rating, Conviction, "Fair Value", "Time Horizon", raw?}
    reports: list[ReportView] = field(default_factory=list)
    turns: list[TurnView] = field(default_factory=list)
