from __future__ import annotations

from typing import Protocol, TypedDict, runtime_checkable

CAPABILITIES = ("prices", "fundamentals", "estimates", "news",
                "transcripts", "research", "holdings", "macro", "markets", "metrics")

# Map a canonical capability to the debate engine's data_vendors category.
DEBATE_CATEGORY = {
    "prices": "core_stock_apis",
    "fundamentals": "fundamental_data",
    "news": "news_data",
    # estimates/transcripts/research/holdings have no debate-engine category in v1
}


class TestResult(TypedDict):
    ok: bool
    kind: str      # "ok" | "auth" | "network" | "unsupported"
    detail: str


class FieldSpec(TypedDict):
    name: str
    label: str
    kind: str      # "password" | "text"
    required: bool


@runtime_checkable
class Connector(Protocol):
    type_id: str
    requires_credentials: bool
    config_fields: list[FieldSpec]
    capabilities: frozenset[str]

    def test(self, creds: str | None, config: dict) -> TestResult: ...

    def as_research_source(self, creds: str | None, config: dict): ...
