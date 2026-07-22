from pallisade_research.models import Provenance, Record
from pallisade_research.relevance import rank_articles, rank_web_records
from pallisade_research.sources.base import (
    CAP_FUNDAMENTALS,
    CAP_NEWS,
    CAP_RESEARCH,
)


def _news(i: int, title: str) -> Record:
    return Record(
        id=f"news-{i}",
        capability=CAP_NEWS,
        key=f"news.{i}",
        value=title,
        provenance=Provenance(source="eodhd", locator="", as_of=None),
    )


def _web(i: int, value: str, capability: str = CAP_NEWS) -> Record:
    return Record(
        id=f"web-{i}",
        capability=capability,
        key=f"web.{i}",
        value=value,
        provenance=Provenance(source="web", locator="https://ex.com", as_of=None, tier=3),
    )


def _fundamental(key: str, value) -> Record:
    return Record(
        id=f"f-{key}",
        capability=CAP_FUNDAMENTALS,
        key=key,
        value=value,
        provenance=Provenance(source="yfinance", locator="", as_of=None),
    )


def test_keeps_only_top_k_most_relevant_articles():
    """Articles are ranked by overlap with the question; only top_k survive."""
    records = [
        _news(0, "Company announces new dividend policy"),
        _news(1, "Bank margins compress as rates fall"),
        _news(2, "CEO discusses margin outlook and lending margins"),
        _news(3, "Sports roundup unrelated to finance"),
    ]
    out = rank_articles(records, "what is happening with the bank's margins?", top_k=2)
    kept = {r.id for r in out}
    # the two margin-heavy headlines win; dividend + sports drop
    assert kept == {"news-1", "news-2"}


def test_non_article_records_pass_through_untouched():
    """Fundamentals/markets/holdings are never filtered, regardless of question."""
    records = [
        _fundamental("fundamentals.marketCap", 5.2e11),
        _fundamental("fundamentals.trailingPE", 10.7),
        _news(0, "Some unrelated headline"),
    ]
    out = rank_articles(records, "what is the market cap", top_k=0 or 3)
    ids = {r.id for r in out}
    assert "f-fundamentals.marketCap" in ids
    assert "f-fundamentals.trailingPE" in ids


def test_generic_question_keeps_most_recent_top_k():
    """With no topical overlap, ties preserve source order (newest-first)."""
    records = [_news(i, f"Headline number {i}") for i in range(5)]
    out = rank_articles(records, "any news?", top_k=3)
    assert [r.id for r in out] == ["news-0", "news-1", "news-2"]


def test_fewer_articles_than_k_keeps_all():
    records = [_news(0, "Only headline")]
    out = rank_articles(records, "unrelated question", top_k=3)
    assert [r.id for r in out] == ["news-0"]


def test_articles_ranked_per_capability_independently():
    """News and research each keep their own top_k so a source is never zeroed out."""
    news = [_news(i, "generic news") for i in range(4)]
    research = [
        Record(id=f"r-{i}", capability=CAP_RESEARCH, key=f"research.{i}",
               value="generic insight", provenance=Provenance(source="smartkarma", locator="", as_of=None))
        for i in range(4)
    ]
    out = rank_articles(news + research, "anything?", top_k=2)
    assert sum(1 for r in out if r.capability == CAP_NEWS) == 2
    assert sum(1 for r in out if r.capability == CAP_RESEARCH) == 2


def test_rank_web_records_keeps_top_k_by_relevance():
    """Web records are ranked by token overlap with the question; only top_k survive."""
    web = [
        _web(0, "Company announces new dividend policy"),
        _web(1, "Bank margins compress as rates fall"),
        _web(2, "CEO discusses margin outlook and lending margins"),
        _web(3, "Sports roundup unrelated to finance"),
        _web(4, "Analyst raises margin estimate on bank"),
        _web(5, "Weather forecast for the region"),
    ]
    non_web = _fundamental("fundamentals.marketCap", 5.2e11)
    records = web + [non_web]

    out = rank_web_records(records, "what is happening with the bank's margins?", top_k=3)

    web_ids = {r.id for r in out if r.provenance.source == "web"}
    assert web_ids == {"web-1", "web-2", "web-4"}
    # the non-web record passes through untouched
    assert non_web.id in {r.id for r in out}
    assert len(out) == 4


def test_rank_articles_exempts_web_records():
    """Web news/research records are never capped by rank_articles; only non-web is."""
    web_news = [_web(i, "generic web note") for i in range(5)]
    non_web_news = [_news(i, "generic feed headline") for i in range(5)]
    records = web_news + non_web_news

    out = rank_articles(records, "anything?", top_k=3)

    kept_web = {r.id for r in out if r.provenance.source == "web"}
    kept_non_web = {r.id for r in out if r.provenance.source != "web"}
    assert kept_web == {r.id for r in web_news}  # all 5 web records survive
    assert len(kept_non_web) == 3  # non-web news is capped to top_k
