from __future__ import annotations

from pallisade_research.models import CitedAnswer, Record, ResearchQuery
from pallisade_research.reconcile import reconcile
from pallisade_research.sources.base import ResearchSource
from pallisade_research.sources.registry import ClientConfig, resolve_sources
from pallisade_research.verify import verify


def answer(
    query: ResearchQuery,
    config: ClientConfig,
    registry: dict[str, ResearchSource],
) -> CitedAnswer:
    wanted = set(query.capabilities)
    records: list[Record] = []
    used: list[str] = []
    unavailable: list[str] = []
    covered: set[str] = set()

    for src in resolve_sources(config, registry):   # tier-ordered
        if not (src.capabilities & wanted):
            continue
        try:
            recs = src.fetch(query)
        except Exception:
            unavailable.append(src.source)
            continue
        # Drop records for a capability a STRICTLY higher tier already produced.
        kept = [r for r in recs if r.capability not in covered]
        if kept:
            used.append(src.source)
            records.extend(kept)
            covered |= {r.capability for r in kept}

    claims = reconcile(records)
    kept_claims, gaps = verify(claims, records, query.capabilities)

    return CitedAnswer(
        question=query.question,
        claims=tuple(kept_claims),
        records=tuple(records),
        gaps=tuple(gaps),
        sources_used=tuple(used),
        sources_unavailable=tuple(unavailable),
    )
