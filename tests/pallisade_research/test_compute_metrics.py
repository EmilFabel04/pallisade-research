from datetime import date

import pytest

from pallisade_research.metrics.compute import (
    COMPUTE_OPS, cagr, compute_metrics, ratio_vs_history, yoy,
)
from pallisade_research.models import Provenance, Record
from pallisade_research.sources.base import CAP_METRICS


def _series_record(name, points, rid="s1"):
    return Record(id=rid, capability=CAP_METRICS, key=f"metrics.{name}.series",
                  value=tuple(points),
                  provenance=Provenance(source="eodhd_fundamentals", locator="loc", as_of=points[-1][0]),
                  evidence_only=True)


REV = [(date(2023, 12, 31), 80.0), (date(2024, 12, 31), 100.0), (date(2025, 12, 31), 120.0)]


def test_yoy_correct():
    assert yoy(tuple(REV)) == pytest.approx(20.0)  # (120-100)/100*100


def test_cagr_correct():
    # (120/80)^(1/2yrs) - 1; ~2.0 years between 2023-12-31 and 2025-12-31
    result = cagr(tuple(REV))
    assert result == pytest.approx(22.47, abs=0.1)


def test_ratio_vs_history_correct():
    # latest 120 vs mean(80,100,120)=100 -> +20%
    assert ratio_vs_history(tuple(REV)) == pytest.approx(20.0)


def test_ops_raise_on_short_series():
    one = ((date(2025, 12, 31), 120.0),)
    for op in COMPUTE_OPS.values():
        with pytest.raises(ValueError):
            op(one)


def test_yoy_raises_on_zero_base():
    with pytest.raises(ValueError):
        yoy(((date(2024, 12, 31), 0.0), (date(2025, 12, 31), 120.0)))


def test_cagr_raises_on_nonpositive_start():
    with pytest.raises(ValueError):
        cagr(((date(2023, 12, 31), 0.0), (date(2025, 12, 31), 120.0)))


def test_ratio_raises_on_zero_mean():
    with pytest.raises(ValueError):
        ratio_vs_history(((date(2024, 12, 31), -60.0), (date(2025, 12, 31), 60.0)))


def test_compute_metrics_emits_derived_records():
    derived = compute_metrics([_series_record("revenue", REV)])
    by_key = {r.key: r for r in derived}
    assert by_key["metrics.revenue.yoy"].value == pytest.approx(20.0)
    d = by_key["metrics.revenue.yoy"].derivation
    assert d.operation == "yoy"
    assert d.input_ids == ("s1",)
    assert "revenue[2025-12-31]" in d.formula
    assert by_key["metrics.revenue.yoy"].capability == CAP_METRICS
    assert by_key["metrics.revenue.yoy"].evidence_only is False
    assert by_key["metrics.revenue.yoy"].id == "s1-yoy"
    assert by_key["metrics.revenue.yoy"].provenance.source == "eodhd_fundamentals"


def test_compute_metrics_skips_degenerate_ops_silently():
    short = _series_record("eps", [(date(2025, 12, 31), 1.2)])
    assert compute_metrics([short]) == []


def test_compute_metrics_ignores_non_series_and_non_evidence_records():
    scalar = Record(id="f1", capability="fundamentals", key="fundamentals.pe", value=15,
                    provenance=Provenance(source="yfinance", locator="", as_of=None))
    not_evidence = Record(id="x", capability=CAP_METRICS, key="metrics.revenue.series",
                          value=tuple(REV),
                          provenance=Provenance(source="s", locator="", as_of=None),
                          evidence_only=False)
    assert compute_metrics([scalar, not_evidence]) == []
