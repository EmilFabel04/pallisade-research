from web.api.services.pdf import (
    DebateView,
    ReportView,
    TurnView,
    render_debate_html,
    render_debate_pdf,
)


def _sample() -> DebateView:
    return DebateView(
        ticker="AAPL",
        trade_date="2026-06-20",
        generated_at="2026-07-22",
        verdict={"Rating": "Buy", "Conviction": "High", "Fair Value": "$260", "Time Horizon": "12m"},
        reports=[ReportView(key="market_report", label="Market", markdown="**Uptrend** intact.")],
        turns=[
            TurnView(speaker="bull", round=1, text="Margins are expanding."),
            TurnView(speaker="bear", round=1, text="Valuation is stretched."),
            TurnView(speaker="bull", round=2, text="Services offsets hardware."),
        ],
    )


def test_debate_html_contains_content():
    html = render_debate_html(_sample())
    assert "AAPL" in html
    assert "Buy" in html                    # verdict rating
    assert "Margins are expanding." in html # bull turn
    assert "Valuation is stretched." in html  # bear turn
    assert "Round 2" in html                # round grouping
    assert "Market" in html                 # report label


def test_debate_pdf_is_pdf_bytes():
    pdf = render_debate_pdf(_sample())
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 1000
