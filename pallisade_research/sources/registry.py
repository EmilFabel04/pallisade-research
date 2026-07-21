from __future__ import annotations

from dataclasses import dataclass

from pallisade_research.sources.base import ResearchSource


@dataclass(frozen=True)
class ClientConfig:
    client_id: str
    enabled_sources: frozenset[str]


def resolve_sources(
    config: ClientConfig, registry: dict[str, ResearchSource]
) -> list[ResearchSource]:
    """Return the client's enabled sources, ordered by tier (1=docs, 2=BYOK, 3=public).

    Ties keep registry insertion order (stable sort)."""
    enabled = [src for name, src in registry.items() if name in config.enabled_sources]
    return sorted(enabled, key=lambda s: getattr(s, "tier", 3))
