"""Relevance ranking for article-type records (news/research).

The news/research sources return the latest N items for a *ticker* with no regard
for what the user actually asked. Left unfiltered, every headline becomes its own
claim card and the dossier fills with off-topic articles. This module keeps only
the few articles that best match the user's standalone question; non-article
records (fundamentals, markets, holdings, macro) pass through untouched.
"""
from __future__ import annotations

import re

from pallisade_research.models import Record
from pallisade_research.sources.base import CAP_NEWS, CAP_RESEARCH

_ARTICLE_CAPS = frozenset({CAP_NEWS, CAP_RESEARCH})

# Generic words that carry no topical signal — stripped before scoring so overlap
# reflects the *subject* of the question, not its phrasing. Short tokens (<=2
# chars) are dropped separately.
_STOP = frozenset({
    "the", "and", "for", "are", "was", "its", "what", "how", "why", "who", "when",
    "tell", "about", "any", "latest", "recent", "give", "show", "does", "did",
    "will", "would", "should", "could", "can", "with", "from", "into", "this",
    "that", "these", "those", "there", "their", "them", "they", "you", "your",
    "our", "has", "have", "had", "get", "got", "current", "currently", "now",
    "please", "some", "more", "most", "than", "then", "over", "under",
})

_WORD = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return {t for t in _WORD.findall(text.lower()) if len(t) > 2 and t not in _STOP}


def _score(record: Record, question_tokens: set[str]) -> int:
    return len(question_tokens & _tokens(str(record.value)))


def rank_articles(records: list[Record], question: str, top_k: int) -> list[Record]:
    """Return `records` with only the top_k most question-relevant articles kept.

    Articles (news/research) are scored by token overlap between their title and
    the question; per capability, the top_k survive and the rest are dropped.
    Non-article records are never touched. Ties preserve the source's original
    order (newest-first for our feeds), so a generic question still yields the
    most recent items rather than an arbitrary subset. Keeping >=1 per capability
    that had any article means coverage of that capability is never lost.
    """
    if top_k < 1:
        return records
    q = _tokens(question)

    by_cap: dict[str, list[Record]] = {}
    for r in records:
        if r.capability in _ARTICLE_CAPS and r.provenance.source != "web":
            by_cap.setdefault(r.capability, []).append(r)
    if not by_cap:
        return records

    keep: set[str] = set()
    for recs in by_cap.values():
        order = sorted(range(len(recs)), key=lambda i: (-_score(recs[i], q), i))
        for i in order[:top_k]:
            keep.add(recs[i].id)

    return [r for r in records if r.provenance.source == "web" or r.capability not in _ARTICLE_CAPS or r.id in keep]


def rank_web_records(records: list[Record], question: str, top_k: int) -> list[Record]:
    """Keep only the top_k most question-relevant web records; non-web records pass untouched.

    Web passages all carry distinct keys (each becomes its own claim), so without a
    cap a deep dive would flood the narrator. Ranked by token overlap with the
    question; ties preserve fetch order. Applied per-turn with a depth-scaled top_k."""
    if top_k < 1:
        return records
    web = [r for r in records if r.provenance.source == "web"]
    if len(web) <= top_k:
        return records
    q = _tokens(question)
    order = sorted(range(len(web)), key=lambda i: (-_score(web[i], q), i))
    keep = {web[i].id for i in order[:top_k]}
    return [r for r in records if r.provenance.source != "web" or r.id in keep]
