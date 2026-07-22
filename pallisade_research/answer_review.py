from __future__ import annotations

import re

from pallisade_research.models import CitedAnswer

# integers/decimals with optional thousands separators and optional trailing %
_NUM = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?%?|\d+(?:\.\d+)?%?")


def _normalize_num(tok: str) -> str:
    t = tok.replace(",", "").rstrip("%")
    if "." in t:
        t = t.rstrip("0").rstrip(".")  # 24.0 -> 24, 24.50 -> 24.5
    return t


def _numbers_in(text: str) -> list[str]:
    return [_normalize_num(m) for m in _NUM.findall(text)]


def unsupported_numbers(draft: str, answer: CitedAnswer) -> list[str]:
    grounded: set[str] = set()
    for c in answer.claims:
        grounded.update(_numbers_in(c.text))
    for r in answer.records:
        grounded.update(_numbers_in(str(r.value)))

    out: list[str] = []
    seen: set[str] = set()
    for n in _numbers_in(draft):
        if n and n not in grounded and n not in seen:
            seen.add(n)
            out.append(n)
    return out
