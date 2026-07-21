from __future__ import annotations

from collections import defaultdict

from pallisade_research.models import Claim, Record


def reconcile(records: list[Record]) -> list[Claim]:
    by_key: dict[str, list[Record]] = defaultdict(list)
    for rec in records:
        by_key[rec.key].append(rec)

    claims: list[Claim] = []
    for key in sorted(by_key):
        group = by_key[key]
        by_value: dict[str, list[Record]] = defaultdict(list)
        for rec in group:
            by_value[repr(rec.value)].append(rec)

        for value_repr in sorted(by_value):
            recs = by_value[value_repr]
            sources = ", ".join(sorted({r.provenance.source for r in recs}))
            value = recs[0].value
            claims.append(
                Claim(
                    text=f"{key}: {value} [{sources}]",
                    record_ids=tuple(r.id for r in recs),
                )
            )
    return claims
