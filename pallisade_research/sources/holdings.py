from __future__ import annotations

from datetime import date

from pallisade_research.models import Provenance, Record, ResearchQuery
from pallisade_research.sources.base import CAP_HOLDINGS


class HoldingsSource:
    """Holdings from an ingested book (the SA LISPs have no API — this is the
    file/statement-ingestion path). `rows` are plain dicts."""

    source = "holdings"
    tier = 2
    capabilities = frozenset({CAP_HOLDINGS})

    def __init__(self, rows: list[dict]):
        self._rows = rows

    def fetch(self, query: ResearchQuery) -> list[Record]:
        out: list[Record] = []
        for row in self._rows:
            if query.ticker is not None and row["ticker"] != query.ticker:
                continue
            out.append(
                Record(
                    id=f"holdings-{row['ticker']}",
                    capability=CAP_HOLDINGS,
                    key=f"holdings.{row['ticker']}",
                    value={"units": row["units"], "value": row["value"]},
                    provenance=Provenance(
                        source="holdings",
                        locator=f"holdings://{row['ticker']}",
                        as_of=date.fromisoformat(row["as_of"]),
                        detail=f"Book holding: {row['ticker']}",
                    ),
                )
            )
        return out
