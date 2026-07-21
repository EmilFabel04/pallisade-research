from pallisade_research.models import Provenance, Record
from pallisade_research.relevance import rank_articles
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
