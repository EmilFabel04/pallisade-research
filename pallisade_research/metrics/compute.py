"""Deterministic trend/ratio compute engine.

Pure functions over a metric's own series (oldest->newest). Each derived number
is produced here and re-checked by the Phase-2A reviewer (see
`unverified_derivations`). No LLM arithmetic anywhere.
"""
from __future__ import annotations

from datetime import date
from statistics import mean
from typing import Callable

from pallisade_research.models import Derivation, Provenance, Record
from pallisade_research.sources.base import CAP_METRICS

Series = tuple[tuple[date, float], ...]


def yoy(series: Series) -> float:
    """Latest-vs-prior-period growth, in percent. Base = second-to-last point."""
    if len(series) < 2:
        raise ValueError("yoy requires >=2 points")
    base = series[-2][1]
    if base == 0:
        raise ValueError("yoy base is zero")
    return (series[-1][1] - base) / base * 100


def cagr(series: Series) -> float:
    """Compound annual growth rate first->last point, in percent."""
    if len(series) < 2:
        raise ValueError("cagr requires >=2 points")
    (d0, v0), (d1, v1) = series[0], series[-1]
    if v0 <= 0:
        raise ValueError("cagr requires a positive start value")
    years = (d1 - d0).days / 365.25
    if years <= 0:
        raise ValueError("cagr requires a positive time span")
    ratio = v1 / v0
    if ratio <= 0:
        raise ValueError("cagr requires a positive end value")
    return (ratio ** (1 / years) - 1) * 100


def ratio_vs_history(series: Series) -> float:
    """Latest value vs its own historical mean, in percent."""
    if len(series) < 2:
        raise ValueError("ratio_vs_history requires >=2 points")
    avg = mean(v for _, v in series)
    if avg == 0:
        raise ValueError("ratio_vs_history requires a nonzero mean")
    return (series[-1][1] / avg - 1) * 100


COMPUTE_OPS: dict[str, Callable[[Series], float]] = {
    "yoy": yoy,
    "cagr": cagr,
    "ratio_vs_history": ratio_vs_history,
}


def _fmt_yoy(name: str, s: Series) -> str:
    (d0, v0), (d1, v1) = s[-2], s[-1]
    return (f"YoY {name} = ({name}[{d1.isoformat()}]={v1:g} − "
            f"{name}[{d0.isoformat()}]={v0:g}) / {v0:g} = {yoy(s):.2f}%")


def _fmt_cagr(name: str, s: Series) -> str:
    (d0, v0), (d1, v1) = s[0], s[-1]
    years = (d1 - d0).days / 365.25
    return (f"CAGR {name} = ({v1:g}/{v0:g})^(1/{years:.2f}yr) − 1 = {cagr(s):.2f}%")


def _fmt_ratio(name: str, s: Series) -> str:
    avg = mean(v for _, v in s)
    (d1, v1) = s[-1]
    return (f"{name} vs history = {name}[{d1.isoformat()}]={v1:g} / mean={avg:.2f} "
            f"− 1 = {ratio_vs_history(s):.2f}%")


FORMULAS: dict[str, Callable[[str, Series], str]] = {
    "yoy": _fmt_yoy,
    "cagr": _fmt_cagr,
    "ratio_vs_history": _fmt_ratio,
}


def _metric_name(key: str) -> str:
    # "metrics.revenue.series" -> "revenue"
    return key[len("metrics."):-len(".series")]


def compute_metrics(records: list[Record]) -> list[Record]:
    """Derive scalar metric records from every evidence-only `.series` record.

    Applies each COMPUTE_OP to each series; a degenerate (series, op) pair is
    skipped silently (its absence surfaces only as a coverage gap if the whole
    capability produced nothing). Deterministic; no LLM.
    """
    derived: list[Record] = []
    for rec in records:
        if not rec.evidence_only or not rec.key.endswith(".series"):
            continue
        series: Series = rec.value
        name = _metric_name(rec.key)
        for op, fn in COMPUTE_OPS.items():
            try:
                result = fn(series)
            except ValueError:
                continue
            formula = FORMULAS[op](name, series)
            derived.append(
                Record(
                    id=f"{rec.id}-{op}",
                    capability=CAP_METRICS,
                    key=f"metrics.{name}.{op}",
                    value=round(result, 2),
                    provenance=Provenance(
                        source=rec.provenance.source,
                        locator=rec.provenance.locator,
                        as_of=rec.provenance.as_of,
                        detail=formula,
                        tier=rec.provenance.tier,
                        liveness=rec.provenance.liveness,
                    ),
                    derivation=Derivation(operation=op, input_ids=(rec.id,), formula=formula),
                )
            )
    return derived
