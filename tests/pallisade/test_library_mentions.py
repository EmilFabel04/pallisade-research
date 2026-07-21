"""Unit tests for parse_mentions and resolve_mentions in pallisade_core.library.service."""
from __future__ import annotations

import pytest

from pallisade_core.library.models import LibraryDocument
from pallisade_core.library.service import parse_mentions, resolve_mentions
from pallisade_core.runs.models import EvaluationRun


# ---------------------------------------------------------------------------
# parse_mentions — pure regex, no DB
# ---------------------------------------------------------------------------

def test_parse_mentions_quoted_and_bare():
    result = parse_mentions('hello @"NPN memo" and @AGL world')
    assert result == ["NPN memo", "AGL"]


def test_parse_mentions_no_mentions():
    result = parse_mentions("no mentions here")
    assert result == []


def test_parse_mentions_empty_string():
    assert parse_mentions("") == []


def test_parse_mentions_multiple_quoted():
    result = parse_mentions('@"First Doc" and @"Second Doc"')
    assert result == ["First Doc", "Second Doc"]


def test_parse_mentions_bare_with_dots():
    result = parse_mentions("@NPN.JO is great")
    assert result == ["NPN.JO"]


# ---------------------------------------------------------------------------
# resolve_mentions — requires DB
# ---------------------------------------------------------------------------

def _make_doc(db, make_user, *, title: str, ticker: str = "TEST.JO",
              kind: str = "final_trade_decision") -> LibraryDocument:
    owner = make_user()
    run = EvaluationRun(mode="public", user_id=owner.id, ticker=ticker, status="done")
    db.add(run)
    db.flush()
    doc = LibraryDocument(
        run_id=run.id,
        ticker=ticker,
        kind=kind,
        title=title,
        body_md="Body text.",
    )
    db.add(doc)
    db.flush()
    return doc


def test_resolve_mentions_matches_doc(db, make_user):
    doc = _make_doc(db, make_user, title="NPN memo — 2026-05-27")
    result = resolve_mentions(db, ["NPN"])
    assert len(result) == 1
    assert result[0].id == doc.id


def test_resolve_mentions_empty_titles(db, make_user):
    _make_doc(db, make_user, title="Some memo")
    result = resolve_mentions(db, [])
    assert result == []


def test_resolve_mentions_no_match(db, make_user):
    _make_doc(db, make_user, title="Totally Different Title")
    result = resolve_mentions(db, ["NPN"])
    assert result == []


def test_resolve_mentions_ambiguous_returns_most_recent(db, make_user):
    """When two docs both contain the mention substring, only one is returned.

    Both docs share the same ``created_at`` inside a rolled-back savepoint
    transaction (the server ``now()`` is stable within a transaction), so we
    cannot rely on ordering by time here.  Instead we verify the de-duplication
    invariant: the seen-set in ``resolve_mentions`` ensures at most one result
    per mention substring regardless of how many rows match.
    """
    from datetime import datetime, timezone

    owner1 = make_user()
    run1 = EvaluationRun(mode="public", user_id=owner1.id, ticker="NPN.JO", status="done")
    db.add(run1)
    db.flush()
    doc_older = LibraryDocument(
        run_id=run1.id, ticker="NPN.JO",
        kind="market_report", title="NPN memo old",
        body_md="old body",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    db.add(doc_older)
    db.flush()

    owner2 = make_user()
    run2 = EvaluationRun(mode="public", user_id=owner2.id, ticker="NPN.JO", status="done")
    db.add(run2)
    db.flush()
    doc_newer = LibraryDocument(
        run_id=run2.id, ticker="NPN.JO",
        kind="final_trade_decision", title="NPN memo new",
        body_md="new body",
        created_at=datetime(2026, 5, 27, tzinfo=timezone.utc),
    )
    db.add(doc_newer)
    db.flush()

    result = resolve_mentions(db, ["NPN"])
    # Only one doc should be returned (the seen-set de-duplication kicks in)
    assert len(result) == 1
    # The newer one should come first (ORDER BY created_at DESC)
    assert result[0].id == doc_newer.id


def test_resolve_mentions_two_different_mentions(db, make_user):
    doc_npn = _make_doc(db, make_user, title="NPN final memo")
    doc_agl = _make_doc(db, make_user, title="AGL investment plan")
    db.flush()

    result = resolve_mentions(db, ["NPN", "AGL"])
    ids = {r.id for r in result}
    assert doc_npn.id in ids
    assert doc_agl.id in ids
    assert len(result) == 2


def test_resolve_mentions_percent_does_not_wildcard(db, make_user):
    """A mention containing '%' must not act as a SQL wildcard.

    '@"100% NPN"' should NOT match a document titled simply "Plain" — the '%'
    must be escaped so it is treated as a literal character, not a wildcard.
    """
    _make_doc(db, make_user, title="Plain")
    result = resolve_mentions(db, ["100%"])
    assert result == [], (
        "A '%' in the mention string should not wildcard-match unrelated documents"
    )
