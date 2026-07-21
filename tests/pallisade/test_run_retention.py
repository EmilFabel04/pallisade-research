from __future__ import annotations

from pallisade_core.runs import service as runs_service
from pallisade_core.runs.events import RunEvent


def _mk(db, user, *, analysts_only):
    return runs_service.create_public_run(
        db, user=user, ticker="NVDA",
        params={"analysts": ["market"], "analysts_only": analysts_only},
    )


def test_prune_keeps_five_newest_of_kind(db, make_user):
    user = make_user()
    for _ in range(8):
        _mk(db, user, analysts_only=False)
    db.flush()
    deleted = runs_service.prune_runs(db, user=user, kind="debate", keep=5)
    db.flush()
    assert deleted == 3
    assert len(runs_service.list_for_user(db, user=user, kind="debate")) == 5


def test_prune_is_per_kind(db, make_user):
    user = make_user()
    for _ in range(6):
        _mk(db, user, analysts_only=True)
    for _ in range(2):
        _mk(db, user, analysts_only=False)
    db.flush()
    runs_service.prune_runs(db, user=user, kind="analysts", keep=5)
    db.flush()
    assert len(runs_service.list_for_user(db, user=user, kind="analysts")) == 5
    assert len(runs_service.list_for_user(db, user=user, kind="debate")) == 2


def test_prune_cascades_run_events(db, make_user):
    user = make_user()
    for _ in range(7):
        r = _mk(db, user, analysts_only=False)
        db.flush()
        db.add(RunEvent(run_id=r.id, seq=1, type="status", payload={}))
    db.flush()
    deleted = runs_service.prune_runs(db, user=user, kind="debate", keep=5)
    db.flush()
    assert deleted == 2
    remaining_runs = {r.id for r in runs_service.list_for_user(db, user=user, kind="debate")}
    remaining_events = db.query(RunEvent).all()
    assert all(e.run_id in remaining_runs for e in remaining_events)


def test_prune_does_not_touch_private_deal_runs(db, make_user):
    """A private (deal) run has no `analysts_only` key, so it must never be
    swept into kind="debate" or "analysts" — and prune_runs must never delete
    it. Regression for the mode='public' scoping bug found in review.
    """
    from pallisade_core.deals.models import Deal
    from pallisade_core.documents.models import Document

    user = make_user()
    deal = Deal(
        name="X", target_company="Y", deal_type="lbo",
        deal_lead_id=user.id, status="screening",
    )
    db.add(deal)
    db.flush()
    doc = Document(
        deal_id=deal.id, uploader_id=user.id, filename="cim.pdf",
        storage_key=f"deals/{deal.id}/cim.pdf",
        content_type="application/pdf", byte_size=1024,
        sha256="f" * 64, source_kind="pdf_text", status="ready",
    )
    db.add(doc)
    db.commit()

    priv = runs_service.create_private_run(
        db, user=user, deal=deal, thesis="test thesis", params={"foo": "bar"},
    )
    db.flush()

    for _ in range(6):
        _mk(db, user, analysts_only=False)
    db.flush()

    runs_service.prune_runs(db, user=user, kind="debate", keep=5)
    db.flush()

    assert runs_service.get_run(db, priv.id) is not None
    assert len(runs_service.list_for_user(db, user=user, kind="debate")) == 5
