from datetime import date

from pallisade_core.memo_checks.adjudicate import (
    ClaimVerdict, SourceCandidate, adjudicate,
)
from pallisade_core.memo_checks.extract import ExtractedFigure


class _Block:
    def __init__(self, inp):
        self.type = "tool_use"
        self.input = inp


class _Msg:
    def __init__(self, inp):
        self.content = [_Block(inp)]


class FakeSdk:
    def __init__(self, payload):
        self._payload = payload
        self.messages = self

    def create(self, **kwargs):
        return _Msg(self._payload)


FIG = ExtractedFigure("Revenue is R42.1bn", "42.1", "R bn", 0, 18)


def _cand(as_of):
    return SourceCandidate(document_id="doc-1", text="Revenue: R42.1bn",
                           filename="model.xlsx", locator="Sheet Model", as_of=as_of)


def test_match_when_found_and_agrees_and_fresh():
    sdk = FakeSdk({"found": True, "agrees": True, "candidate_index": 0,
                   "source_value": "R42.1bn", "rationale": "agrees"})
    v = adjudicate(FIG, [_cand(date(2026, 7, 15))], sdk=sdk, model="m",
                   memo_date=date(2026, 7, 20), stale_days=30)
    assert v.verdict == "match"
    assert v.source_document_id == "doc-1"
    assert v.source_value == "R42.1bn"


def test_stale_when_agrees_but_source_too_old():
    sdk = FakeSdk({"found": True, "agrees": True, "candidate_index": 0,
                   "source_value": "R42.1bn", "rationale": "agrees"})
    v = adjudicate(FIG, [_cand(date(2026, 5, 1))], sdk=sdk, model="m",
                   memo_date=date(2026, 7, 20), stale_days=30)
    assert v.verdict == "stale"


def test_mismatch_when_found_but_disagrees():
    sdk = FakeSdk({"found": True, "agrees": False, "candidate_index": 0,
                   "source_value": "R40.0bn", "rationale": "differs"})
    v = adjudicate(FIG, [_cand(date(2026, 7, 19))], sdk=sdk, model="m",
                   memo_date=date(2026, 7, 20), stale_days=30)
    assert v.verdict == "mismatch"
    assert v.source_value == "R40.0bn"


def test_unsupported_when_not_found():
    sdk = FakeSdk({"found": False, "agrees": False, "candidate_index": None,
                   "source_value": None, "rationale": "no backing figure"})
    v = adjudicate(FIG, [_cand(date(2026, 7, 19))], sdk=sdk, model="m",
                   memo_date=date(2026, 7, 20), stale_days=30)
    assert v.verdict == "unsupported"
    assert v.source_document_id is None


def test_unsupported_when_no_candidates_skips_llm():
    # No candidates => no LLM call is needed; must still return unsupported.
    class Boom:
        messages = property(lambda self: (_ for _ in ()).throw(AssertionError("called")))
    v = adjudicate(FIG, [], sdk=Boom(), model="m",
                   memo_date=date(2026, 7, 20), stale_days=30)
    assert v == ClaimVerdict("unsupported", None, None, None, None,
                             "No backing document contained this figure.")
