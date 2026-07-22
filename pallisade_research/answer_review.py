from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from pallisade_research.metrics.compute import COMPUTE_OPS
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
        ".5" -> "0.5"
    """
    # Strip leading sign: magnitude check is sign-agnostic (sign correctness is the auditor's job)
    t = tok.lstrip("+-")
    t = t.replace(",", "").rstrip("%")
    if t.startswith("."):
        t = "0" + t  # .5 -> 0.5, so it compares equal to an explicit 0.5
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
        # Skip series inputs: their tuple stringifies to a bag of dates/values
        # that would falsely ground fabricated magnitudes. Derived records are
        # scalar and not evidence_only, so they stay grounded here.
        if r.evidence_only or isinstance(r.value, (tuple, list)):
            continue
        # Intentionally permissive: matches on magnitude alone, so a record value grounds
        # any draft number with the same magnitude regardless of which metric it's attached
        # to. Catching misattribution to the wrong metric is the independent auditor's job.
        grounded.update(_numbers_in(str(r.value)))

    out: list[str] = []
    seen: set[str] = set()
    for n in _numbers_in(draft):
        if n and n not in grounded and n not in seen:
            seen.add(n)
            out.append(n)
    return out


def unverified_derivations(answer: CitedAnswer) -> list[str]:
    """Re-run every derived record's operation on its cited inputs; flag mismatches.

    Fails closed: a missing op, an unresolvable input, or a value that does not
    reproduce within 0.01 all produce an objection. This is the machine-checkable
    half of the grounding guarantee for computed numbers.
    """
    by_id = {r.id: r for r in answer.records}
    objections: list[str] = []
    for r in answer.records:
        if r.derivation is None:
            continue
        d = r.derivation
        fn = COMPUTE_OPS.get(d.operation)
        recomputed = None
        if fn is not None and d.input_ids:
            try:
                series = by_id[d.input_ids[0]].value
                recomputed = round(fn(series), 2)
            except (KeyError, IndexError, ValueError, TypeError):
                recomputed = None
        if recomputed is None or abs(recomputed - r.value) > 0.01:
            objections.append(
                f"derived '{r.key}' = {r.value} does not reproduce (recomputed {recomputed})"
            )
    return objections


_AUDIT_SYSTEM = (
    "You are an auditor for an equity-research tool. Your ONLY job is to find "
    "statements in the DRAFT that are NOT fully supported by the FINDINGS, or "
    "that attribute a fact to the wrong source. Assume the writer may have "
    "hallucinated. Judge only against the FINDINGS given — no outside knowledge. "
    "List every unsupported or misattributed statement. If every statement is "
    "fully supported, return an empty issues list. "
    "Numeric DIRECTION is your responsibility: if the draft states a rise/gain/positive value but the finding is a decline/loss/negative value (or vice-versa), flag it as unsupported even when the magnitude matches."
)

_AUDIT_TOOL = {
    "name": "report_issues",
    "description": "Report statements in the draft not supported by the findings.",
    "input_schema": {
        "type": "object",
        "properties": {
            "issues": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "span": {"type": "string", "description": "the exact offending text"},
                        "kind": {"type": "string", "enum": ["unsupported", "misattributed"]},
                        "why": {"type": "string", "description": "why it is not supported"},
                    },
                    "required": ["span", "kind", "why"],
                },
            }
        },
        "required": ["issues"],
    },
}


def llm_objections(sdk, model: str, draft: str, answer: CitedAnswer) -> list[str]:
    findings = "\n".join(f"- {c.text}" for c in answer.claims) or "(none)"
    gaps = "; ".join(g.note for g in answer.gaps) or "none"
    unavailable = ", ".join(answer.sources_unavailable) or "none"
    prompt = (
        f"FINDINGS (the only supported facts):\n{findings}\n\n"
        f"Coverage gaps: {gaps}\nUnavailable sources: {unavailable}\n\n"
        f"DRAFT to audit:\n{draft}"
    )
    msg = sdk.messages.create(
        model=model,
        max_tokens=512,
        system=[{"type": "text", "text": _AUDIT_SYSTEM}],
        tools=[_AUDIT_TOOL],
        tool_choice={"type": "tool", "name": "report_issues"},
        messages=[{"role": "user", "content": prompt}],
    )
    payload = next((b.input for b in msg.content if getattr(b, "type", "") == "tool_use"), None)
    if payload is None:
        raise ValueError("auditor returned no tool_use block")
    issues = payload.get("issues") or []
    return [f"{i.get('kind','unsupported')}: '{i.get('span','')}' — {i.get('why','')}" for i in issues]


@dataclass(frozen=True)
class ReviewedAnswer:
    text: str
    status: str  # "verified" | "regenerated" | "fallback"
    objections: tuple[str, ...] = ()


def review_answer(
    sdk,
    model: str,
    answer: CitedAnswer,
    draft: str,
    *,
    narrate: Callable[[str], str],
    template: Callable[[], str],
    max_retries: int = 2,
) -> ReviewedAnswer:
    current = draft
    last_issues: list[str] = []
    deriv_issues = unverified_derivations(answer)
    for attempt in range(max_retries + 1):
        nums = unsupported_numbers(current, answer)
        try:
            objs = llm_objections(sdk, model, current, answer)
        except Exception:  # noqa: BLE001 — reviewer unavailable → fail closed
            return ReviewedAnswer(template(), "fallback", ())
        issues = [f"number '{n}' is not in the findings" for n in nums] + deriv_issues + objs
        if not issues:
            return ReviewedAnswer(current, "verified" if attempt == 0 else "regenerated", ())
        last_issues = issues
        if attempt == max_retries:
            break
        try:
            current = narrate("; ".join(issues))
        except Exception:  # noqa: BLE001 — regeneration failed → fall back
            break
    return ReviewedAnswer(template(), "fallback", tuple(last_issues))
