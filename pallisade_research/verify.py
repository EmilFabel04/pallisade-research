from __future__ import annotations

from pallisade_research.models import Claim, CoverageGap, Record


def verify(
    claims: list[Claim],
    records: list[Record],
    requested_capabilities: tuple[str, ...],
) -> tuple[list[Claim], list[CoverageGap]]:
    valid_ids = {r.id for r in records}
    kept = [
        c for c in claims
        if c.record_ids and all(rid in valid_ids for rid in c.record_ids)
    ]

    covered = {r.capability for r in records}
    gaps = [
        CoverageGap(note=f"No coverage for '{cap}' from the connected sources.")
        for cap in requested_capabilities
        if cap not in covered
    ]
    return kept, gaps
