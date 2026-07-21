from __future__ import annotations

from datetime import date

from pallisade_core.deals.models import Deal, DealTeamMember


def test_create_deal(db, make_user):
    lead = make_user()
    deal = Deal(
        name="Project Falcon",
        target_company="Acme Co",
        deal_type="lbo",
        sector="industrials",
        status="screening",
        description="d",
        check_size_usd=10_000_000_00,
        expected_close_date=date(2026, 9, 1),
        deal_lead_id=lead.id,
    )
    db.add(deal)
    db.flush()
    assert deal.id is not None
    assert deal.created_at is not None


def test_team_membership_cascade(db, make_user):
    lead, alice = make_user(), make_user()
    d = Deal(name="P", target_company="t", deal_type="lbo", deal_lead_id=lead.id)
    db.add(d); db.flush()
    db.add(DealTeamMember(deal_id=d.id, user_id=alice.id))
    db.flush()
    db.delete(d)
    db.flush()
    from sqlalchemy import select
    rows = db.execute(select(DealTeamMember).where(DealTeamMember.deal_id == d.id)).all()
    assert rows == []
