import pytest

from pallisade_research.answer_review import unsupported_numbers, llm_objections
from pallisade_research.models import CitedAnswer, Claim, Provenance, Record


def _answer(claims_text, record_values=()):
    claims = tuple(Claim(text=t, record_ids=("r",)) for t in claims_text)
    records = tuple(
        Record(id=f"r{i}", capability="fundamentals", key="k", value=v,
               provenance=Provenance(source="s", locator="l", as_of=None))
        for i, v in enumerate(record_values)
    )
    return CitedAnswer(question="q", claims=claims, records=records, gaps=(),
                       sources_used=(), sources_unavailable=())


def test_supported_numbers_return_empty():
    ans = _answer(("fundamentals.trailingPE: 24.5 [yfinance]",), record_values=(24.5,))
    assert unsupported_numbers("The P/E is 24.5 per yfinance.", ans) == []


def test_fabricated_number_flagged():
    ans = _answer(("fundamentals.trailingPE: 24.5 [yfinance]",), record_values=(24.5,))
    assert unsupported_numbers("Revenue grew 12% last year.", ans) == ["12"]


def test_normalisation_matches_commas_percent_and_trailing_zero():
    ans = _answer(("markets.change_pct: 24.0 [eodhd]", "fundamentals.rev: 1234 [yf]"),
                  record_values=(24.0, 1234))
    # 24% ~ 24.0, 1,234 ~ 1234 → both supported
    assert unsupported_numbers("Up 24% on revenue of 1,234.", ans) == []


def test_multiple_unsupported_deduped_order_preserving():
    ans = _answer(("x: 5 [s]",), record_values=(5,))
    assert unsupported_numbers("7 then 9 then 7 then 5.", ans) == ["7", "9"]


def test_magnitude_check_is_sign_agnostic_by_design():
    """Magnitude check matches ignoring sign: narration direction is auditor's concern."""
    # Grounded value carries explicit sign (negative record)
    ans = _answer(("fundamentals.rev_change: -12.5 [yf]",), record_values=(-12.5,))
    # Draft uses positive token for same magnitude; sign (decline) is narrated in words
    assert unsupported_numbers("Revenue changed 12.5% this year.", ans) == []
    # This documents the intentional boundary: magnitude-only grounding; auditor verifies direction


def test_fabricated_magnitude_still_flagged_with_negatives_present():
    """Even if grounded values include negatives, unsupported magnitudes are still flagged."""
    ans = _answer(("fundamentals.rev_change: -12.5 [yf]",), record_values=(-12.5,))
    # Draft uses fabricated magnitude 40%, which is NOT grounded (only -12.5 is)
    assert unsupported_numbers("It grew 40%.", ans) == ["40"]


def test_leading_dot_decimal_is_matched():
    """Leading-dot decimals like .5 and .9 are now recognized by the regex."""
    # Grounded value: 0.5 (could be from a record or claim containing ".5")
    ans = _answer(("market_impact: 0.5 [src]",), record_values=(0.5,))
    # Draft contains a different leading-dot number .9; it should be flagged as unsupported
    # (even though .5 is supported)
    assert unsupported_numbers("The coefficient was .9.", ans) == [".9"]


# LLM objections tests with mocked SDK


class _Block:
    def __init__(self, **kw): self.__dict__.update(kw)


class _Msg:
    def __init__(self, content): self.content = content


class _SDK:
    def __init__(self, msg=None, err=None):
        self._msg, self._err = msg, err
        self.messages = self

    def create(self, **kw):
        if self._err:
            raise self._err
        return self._msg


def test_llm_objections_parses_issues():
    msg = _Msg([_Block(type="tool_use", name="report_issues",
                       input={"issues": [
                           {"span": "grew 12%", "kind": "unsupported", "why": "no such figure"},
                           {"span": "per Bloomberg", "kind": "misattributed", "why": "source is yfinance"},
                       ]})])
    objs = llm_objections(_SDK(msg=msg), "m", "draft", _answer(("x: 1 [s]",)))
    assert objs == [
        "unsupported: 'grew 12%' — no such figure",
        "misattributed: 'per Bloomberg' — source is yfinance",
    ]


def test_llm_objections_empty_when_clean():
    msg = _Msg([_Block(type="tool_use", name="report_issues", input={"issues": []})])
    assert llm_objections(_SDK(msg=msg), "m", "draft", _answer(("x: 1 [s]",))) == []


def test_llm_objections_raises_on_sdk_error():
    with pytest.raises(RuntimeError):
        llm_objections(_SDK(err=RuntimeError("down")), "m", "draft", _answer(("x: 1 [s]",)))
