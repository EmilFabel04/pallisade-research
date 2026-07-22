from pallisade_research.answer_review import unsupported_numbers
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
