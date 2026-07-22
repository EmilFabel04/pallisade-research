import pytest

from pallisade_research.answer_review import (
    unsupported_numbers,
    llm_objections,
    ReviewedAnswer,
    review_answer,
    _AUDIT_SYSTEM,
)
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
    # (even though .5 is supported). Leading-dot decimals normalize with a "0" prefix.
    assert unsupported_numbers("The coefficient was .9.", ans) == ["0.9"]


def test_leading_dot_matches_zero_prefixed():
    """.5 in the draft should match a grounded 0.5 — leading-dot normalization is symmetric."""
    ans = _answer(("market_impact: 0.5 [src]",), record_values=(0.5,))
    assert unsupported_numbers("It moved .5 points.", ans) == []


# LLM objections tests with mocked SDK


class _Block:
    def __init__(self, **kw): self.__dict__.update(kw)


class _Msg:
    def __init__(self, content): self.content = content


class _SDK:
    def __init__(self, msg=None, err=None):
        self._msg, self._err = msg, err
        self.messages = self
        self.last_kwargs = None

    def create(self, **kw):
        self.last_kwargs = kw
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


def test_llm_objections_raises_on_missing_tool_block():
    """A response with no tool_use block must raise, not silently be treated as 'clean'."""
    msg = _Msg([_Block(type="text", text="I have thoughts but no tool call.")])
    with pytest.raises(ValueError):
        llm_objections(_SDK(msg=msg), "m", "draft", _answer(("x: 1 [s]",)))


def test_llm_objections_sends_adversarial_system_and_forced_tool():
    """The auditor call must be independent/adversarial: forced tool + auditor system prompt."""
    sdk = _clean_sdk()
    llm_objections(sdk, "m", "draft", _answer(("x: 1 [s]",)))
    kw = sdk.last_kwargs
    assert kw is not None
    assert kw["tool_choice"] == {"type": "tool", "name": "report_issues"}
    system_text = kw["system"][0]["text"] if isinstance(kw["system"], list) else kw["system"]
    assert "auditor" in system_text
    assert "DIRECTION" in system_text
    assert system_text == _AUDIT_SYSTEM


# Review orchestrator tests


def _clean_sdk():
    return _SDK(msg=_Msg([_Block(type="tool_use", name="report_issues", input={"issues": []})]))


def test_review_clean_draft_is_verified():
    ans = _answer(("x: 5 [s]",), record_values=(5,))
    calls = []
    r = review_answer(_clean_sdk(), "m", ans, "The value is 5 [s].",
                      narrate=lambda o: calls.append(o) or "x", template=lambda: "TEMPLATE")
    assert r == ReviewedAnswer("The value is 5 [s].", "verified", ())
    assert calls == []  # no regeneration


def test_review_regenerates_then_passes():
    ans = _answer(("x: 5 [s]",), record_values=(5,))
    # first draft has a fabricated number → number check flags it; regen returns clean draft
    def narrate(obj):
        return "The value is 5 [s]."
    r = review_answer(_clean_sdk(), "m", ans, "It jumped 99%.",
                      narrate=narrate, template=lambda: "TEMPLATE")
    assert r.status == "regenerated"
    assert r.text == "The value is 5 [s]."


def test_review_falls_back_after_retries():
    ans = _answer(("x: 5 [s]",), record_values=(5,))
    r = review_answer(_clean_sdk(), "m", ans, "It jumped 99%.",
                      narrate=lambda o: "Still 99% wrong.", template=lambda: "TEMPLATE",
                      max_retries=2)
    assert r.status == "fallback"
    assert r.text == "TEMPLATE"


def test_review_fails_closed_when_verifier_errors():
    ans = _answer(("x: 5 [s]",), record_values=(5,))
    r = review_answer(_SDK(err=RuntimeError("down")), "m", ans, "The value is 5 [s].",
                      narrate=lambda o: "x", template=lambda: "TEMPLATE")
    assert r.status == "fallback"
    assert r.text == "TEMPLATE"


def _metric_answer(stored_yoy=20.0):
    from datetime import date
    from pallisade_research.models import (
        CitedAnswer, Claim, Derivation, Provenance, Record,
    )
    from pallisade_research.sources.base import CAP_METRICS

    prov = Provenance(source="eodhd_fundamentals", locator="", as_of=None)
    series = Record(id="s1", capability=CAP_METRICS, key="metrics.revenue.series",
                    value=((date(2024, 12, 31), 100.0), (date(2025, 12, 31), 120.0)),
                    provenance=prov, evidence_only=True)
    derived = Record(id="s1-yoy", capability=CAP_METRICS, key="metrics.revenue.yoy",
                     value=stored_yoy, provenance=prov,
                     derivation=Derivation("yoy", ("s1",), "YoY = ..."))
    claim = Claim(text=f"metrics.revenue.yoy: {stored_yoy} [eodhd_fundamentals]",
                  record_ids=("s1-yoy",))
    return CitedAnswer(question="has revenue grown?", claims=(claim,),
                       records=(series, derived), gaps=(), sources_used=("eodhd_fundamentals",),
                       sources_unavailable=())


def test_unsupported_numbers_grounds_derived_and_ignores_series_tuples():
    from pallisade_research.answer_review import unsupported_numbers
    answer = _metric_answer(stored_yoy=20.0)
    # 20 is grounded (derived value); 999 is not; the series numbers (100, 120,
    # 2024, 2025...) must NOT ground a fabricated "100".
    assert unsupported_numbers("revenue grew 20% year on year", answer) == []
    assert "999" in unsupported_numbers("revenue grew 999%", answer)
    assert "100" in unsupported_numbers("revenue was 100", answer)


def test_unverified_derivations_passes_correct_and_flags_tampered():
    from pallisade_research.answer_review import unverified_derivations
    assert unverified_derivations(_metric_answer(stored_yoy=20.0)) == []
    flagged = unverified_derivations(_metric_answer(stored_yoy=99.0))
    assert len(flagged) == 1
    assert "does not reproduce" in flagged[0]
