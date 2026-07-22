from web.api.services.pdf import (
    AnswerView,
    ClaimView,
    MessageView,
    RecordView,
    ResearchConversationView,
    render_research_html,
    render_research_pdf,
)


def _sample() -> ResearchConversationView:
    rec = RecordView(
        capability="fundamentals", key="marketCap", value="100",
        source="yfinance", locator="AAPL/marketCap", as_of="2026-06-20", detail="",
    )
    ans = AnswerView(
        question="is AAPL worth holding?",
        claims=[ClaimView(text="Market cap is 100.", records=[rec])],
        sources_used=["yfinance", "holdings"],
        sources_unavailable=["edgar"],
        gaps=["No margin history."],
    )
    return ResearchConversationView(
        title="AAPL overview",
        generated_at="2026-07-22",
        messages=[
            MessageView(role="user", content="is AAPL worth holding?"),
            MessageView(role="assistant", content="**Yes** — strong balance sheet.", answer=ans),
        ],
    )


def test_research_html_contains_content():
    html = render_research_html(_sample())
    assert "AAPL overview" in html
    assert "Market cap is 100." in html
    assert "yfinance" in html
    assert "edgar" in html            # unavailable source
    assert "No margin history." in html  # gap


def test_research_pdf_is_pdf_bytes():
    pdf = render_research_pdf(_sample())
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 1000
