from datetime import date

from pallisade_research.models import Derivation, Provenance, Record
from pallisade_research.sources.base import ALL_CAPABILITIES, CAP_METRICS


def test_record_defaults_are_backward_compatible():
    r = Record(id="x", capability="fundamentals", key="k", value=1,
               provenance=Provenance(source="s", locator="", as_of=None))
    assert r.derivation is None
    assert r.evidence_only is False


def test_record_carries_derivation_and_evidence_flag():
    d = Derivation(operation="yoy", input_ids=("s1",), formula="YoY = ...")
    series = Record(id="s1", capability=CAP_METRICS, key="metrics.revenue.series",
                    value=((date(2024, 12, 31), 100.0), (date(2025, 12, 31), 120.0)),
                    provenance=Provenance(source="eodhd_fundamentals", locator="", as_of=None),
                    evidence_only=True)
    derived = Record(id="s1-yoy", capability=CAP_METRICS, key="metrics.revenue.yoy",
                     value=20.0,
                     provenance=Provenance(source="eodhd_fundamentals", locator="", as_of=None),
                     derivation=d)
    assert series.evidence_only is True
    assert derived.derivation.operation == "yoy"
    assert derived.derivation.input_ids == ("s1",)


def test_cap_metrics_registered():
    assert CAP_METRICS == "metrics"
    assert CAP_METRICS in ALL_CAPABILITIES
