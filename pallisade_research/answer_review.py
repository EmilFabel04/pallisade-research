from __future__ import annotations

import re

from pallisade_research.models import CitedAnswer

# Regex to match numeric magnitudes: thousands-separated, plain decimal, or leading-dot decimal, with optional %
# Examples: 1234, 1,234, 12.5, .5, 24%, 1,234.56%
_NUM = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?%?|\d+(?:\.\d+)?%?|\.\d+%?")


def _normalize_num(tok: str) -> str:
    """Normalize a numeric token for magnitude comparison (sign-agnostic).

    Strips leading sign (± is direction; this is magnitude-only grounding).
    Removes commas, trailing %, and redundant trailing zeros.

    Examples:
        "-12.5" -> "12.5"
        "1,234.0" -> "1234"
        "24%" -> "24"
        ".5" -> ".5"
    """
    # Strip leading sign: magnitude check is sign-agnostic (sign correctness is the auditor's job)
    t = tok.lstrip("+-")
    t = t.replace(",", "").rstrip("%")
    if "." in t:
        t = t.rstrip("0").rstrip(".")  # 24.0 -> 24, 24.50 -> 24.5
    return t


def _numbers_in(text: str) -> list[str]:
    return [_normalize_num(m) for m in _NUM.findall(text)]


def unsupported_numbers(draft: str, answer: CitedAnswer) -> list[str]:
    """Check that every numeric MAGNITUDE in draft is grounded in the answer.

    **This is a MAGNITUDE-ONLY check, intentionally sign-agnostic.**

    Design: narration expresses direction in words ("revenue declined 12.5%", a bare positive token)
    while grounded values carry explicit signs ("-12.5"). Matching by magnitude ensures no
    fabricated magnitudes are displayed; sign/direction correctness is verified separately
    by the independent LLM auditor.

    Args:
        draft: text containing draft narration (may include fabricated numbers)
        answer: structured answer with grounded claims and records

    Returns:
        list of unsupported magnitude strings (sign-stripped), deduplicated and order-preserving
    """
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
