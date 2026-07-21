from datetime import date

from pallisade_research.citations import format_citation
from pallisade_research.models import Provenance


TODAY = date(2026, 7, 20)


def test_tier1_document_cites_file_and_modified_age():
    p = Provenance(source="documents", locator="Aswan-FactSet-model.xlsx p.3",
                   as_of=date(2026, 7, 17), detail="Aswan-FactSet-model.xlsx", tier=1, liveness="static")
    assert format_citation(p, today=TODAY) == "per Aswan-FactSet-model.xlsx, modified 3 days ago"


def test_tier1_document_without_date():
    p = Provenance(source="documents", locator="notes.pdf", as_of=None,
                   detail="notes.pdf", tier=1, liveness="static")
    assert format_citation(p, today=TODAY) == "per notes.pdf"


def test_tier2_and_tier3_live():
    byok = Provenance(source="smartkarma", locator="x", as_of=None, tier=2, liveness="live")
    public = Provenance(source="yfinance", locator="x", as_of=None, tier=3, liveness="live")
    assert format_citation(byok, today=TODAY) == "per smartkarma (live)"
    assert format_citation(public, today=TODAY) == "per yfinance (live)"
