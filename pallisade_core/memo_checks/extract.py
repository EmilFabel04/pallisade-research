from __future__ import annotations

from dataclasses import dataclass
from typing import Any

EXTRACT_TOOL = {
    "name": "list_figures",
    "description": "List every cited numeric figure in the memo the analyst wrote.",
    "input_schema": {
        "type": "object",
        "properties": {
            "figures": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "claim_text": {"type": "string",
                                       "description": "The clause containing the figure, verbatim."},
                        "value": {"type": "string",
                                  "description": "The numeric value as written, e.g. '42.1'."},
                        "unit": {"type": "string",
                                 "description": "Unit/currency/scale, e.g. 'R bn', '%'. '' if none."},
                        "char_start": {"type": "integer"},
                        "char_end": {"type": "integer"},
                    },
                    "required": ["claim_text", "value", "unit", "char_start", "char_end"],
                },
            }
        },
        "required": ["figures"],
    },
}

_SYSTEM = (
    "You extract cited numeric figures from an investment memo for fact-checking. "
    "Return every quantitative claim (revenue, margins, multiples, growth rates, "
    "price targets, dates-as-figures). char_start/char_end are the 0-indexed span "
    "of claim_text within the memo. Do not invent figures not present in the text."
)


@dataclass(frozen=True)
class ExtractedFigure:
    claim_text: str
    value: str
    unit: str
    char_start: int
    char_end: int


def extract_figures(memo_text: str, *, sdk: Any, model: str) -> list[ExtractedFigure]:
    msg = sdk.messages.create(
        model=model,
        max_tokens=2048,
        system=[{"type": "text", "text": _SYSTEM}],
        tools=[EXTRACT_TOOL],
        tool_choice={"type": "tool", "name": "list_figures"},
        messages=[{"role": "user", "content": memo_text}],
    )
    payload = next(
        (b.input for b in msg.content if getattr(b, "type", "") == "tool_use"), None
    )
    if payload is None:
        return []
    return [
        ExtractedFigure(
            claim_text=f["claim_text"], value=f["value"], unit=f.get("unit", ""),
            char_start=int(f["char_start"]), char_end=int(f["char_end"]),
        )
        for f in payload.get("figures", [])
    ]
