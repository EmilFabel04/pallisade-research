from pallisade_research.planner import plan
from pallisade_research.sources.base import (
    CAP_FUNDAMENTALS,
    CAP_HOLDINGS,
    CAP_NEWS,
    CAP_RESEARCH,
    ALL_CAPABILITIES,
)

KNOWN = frozenset({"AAPL", "NPN.JO"})


def test_plan_extracts_ticker_and_default_caps():
    """Base keyword rule: a plain overview selects fundamentals ONLY.

    News/research are scoped to questions that ask about developments (the "news"
    branch), so an ordinary overview must not drag in off-topic articles — nor
    holdings, which would manufacture a coverage gap.
    """
    q = plan("give me an overview of AAPL please", KNOWN)
    assert q.ticker == "AAPL"
    assert set(q.capabilities) == {CAP_FUNDAMENTALS}
    assert CAP_RESEARCH not in q.capabilities
    assert CAP_HOLDINGS not in q.capabilities


def test_plan_conviction_question_requests_all_caps():
    """Base keyword rule: conviction keywords select all capabilities."""
    q = plan("is NPN.JO worth holding?", KNOWN)
    assert q.ticker == "NPN.JO"
    assert set(q.capabilities) == set(ALL_CAPABILITIES)


def test_plan_news_question():
    """Base keyword rule: news keyword selects news+research (no holdings)."""
    q = plan("any news on AAPL?", KNOWN)
    assert set(q.capabilities) == {CAP_NEWS, CAP_RESEARCH}
    assert CAP_HOLDINGS not in q.capabilities


def test_plan_no_known_ticker():
    """Base case: no ticker identified."""
    q = plan("what is the market doing", KNOWN)
    assert q.ticker is None
    # Holdings not injected without a ticker
    assert CAP_HOLDINGS not in q.capabilities


def test_plan_no_holdings_on_plain_ticker_question():
    """Holdings is NOT auto-injected on a plain ticker overview."""
    q = plan("overview of AAPL", KNOWN)
    assert q.ticker == "AAPL"
    assert CAP_HOLDINGS not in q.capabilities


def test_plan_conviction_still_includes_holdings():
    """A conviction ('worth holding') question legitimately pulls all caps, incl. holdings."""
    q = plan("is AAPL worth holding?", KNOWN)
    assert q.ticker == "AAPL"
    assert CAP_HOLDINGS in q.capabilities
