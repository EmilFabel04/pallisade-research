from __future__ import annotations

from datetime import date

from pallisade_research.models import CitedAnswer, Provenance


def _age(as_of: date, today: date) -> str:
    days = (today - as_of).days
    if days <= 0:
        return "today"
    if days == 1:
        return "1 day ago"
    return f"{days} days ago"


def format_citation(prov: Provenance, *, today: date) -> str:
    """One-line citation reflecting the answering tier + liveness."""
    if prov.tier == 1:
        name = prov.detail or prov.locator
        if prov.as_of is not None:
            return f"per {name}, modified {_age(prov.as_of, today)}"
        return f"per {name}"
    return f"per {prov.source} (live)"


def tiered_sources_line(answer: CitedAnswer, *, today: date) -> str:
    """Dedup provenances across the answer's records, tier-ordered, as one citation line."""
    seen: dict[str, Provenance] = {}
    for r in answer.records:
        key = f"{r.provenance.tier}:{r.provenance.source}:{r.provenance.detail or r.provenance.locator}"
        seen.setdefault(key, r.provenance)
    provs = sorted(seen.values(), key=lambda p: (p.tier, p.source))
    return "; ".join(format_citation(p, today=today) for p in provs)
