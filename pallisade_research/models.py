from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any


@dataclass(frozen=True)
class Provenance:
    source: str
    locator: str
    as_of: date | None
    detail: str = ""
    tier: int = 3
    liveness: str = "live"


@dataclass(frozen=True)
class Derivation:
    operation: str                 # key into COMPUTE_OPS, e.g. "yoy"
    input_ids: tuple[str, ...]     # record ids this value was computed from
    formula: str                   # human-readable, e.g. "YoY = (rev[2025]-rev[2024])/rev[2024]"


@dataclass(frozen=True)
class Record:
    id: str
    capability: str
    key: str
    value: Any
    provenance: Provenance
    derivation: "Derivation | None" = None
    evidence_only: bool = False


@dataclass(frozen=True)
class ResearchQuery:
    question: str
    ticker: str | None
    capabilities: tuple[str, ...]
    entity: str | None = None
    entity_type: str | None = None


@dataclass(frozen=True)
class Claim:
    text: str
    record_ids: tuple[str, ...]


@dataclass(frozen=True)
class CoverageGap:
    note: str


@dataclass(frozen=True)
class CitedAnswer:
    question: str
    claims: tuple[Claim, ...]
    records: tuple[Record, ...]
    gaps: tuple[CoverageGap, ...]
    sources_used: tuple[str, ...]
    sources_unavailable: tuple[str, ...]
