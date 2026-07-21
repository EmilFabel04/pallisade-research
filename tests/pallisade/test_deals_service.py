from __future__ import annotations

import pytest

from pallisade_core.deals import service as deals
from pallisade_core.deals.status import DealStatus, IllegalStatusTransition


def test_create_and_list(db, make_user):
    lead = make_user()
    d = deals.create_deal(db, lead=lead, name="P1", target_company="T1", deal_type="lbo")
    db.flush()
    listed = deals.list_visible(db, viewer=lead)
    assert [x.id for x in listed] == [d.id]


def test_visibility_lead_team_admin(db, make_user):
    lead = make_user()
    alice = make_user()
    bob = make_user()
    admin = make_user(role="admin")
    d = deals.create_deal(db, lead=lead, name="P", target_company="T", deal_type="lbo")
    db.flush()
    deals.add_team_member(db, deal=d, user=alice)
    db.flush()

    assert deals.can_view(db, viewer=lead, deal=d) is True
    assert deals.can_view(db, viewer=alice, deal=d) is True
    assert deals.can_view(db, viewer=bob, deal=d) is False
    assert deals.can_view(db, viewer=admin, deal=d) is True

    assert {x.id for x in deals.list_visible(db, viewer=alice)} == {d.id}
    assert deals.list_visible(db, viewer=bob) == []
    assert {x.id for x in deals.list_visible(db, viewer=admin)} == {d.id}


def test_transition_status(db, make_user):
    lead = make_user()
    d = deals.create_deal(db, lead=lead, name="P", target_company="T", deal_type="lbo")
    db.flush()
    deals.transition_status(db, deal=d, target=DealStatus.loi, actor=lead)
    db.flush()
    assert d.status == "loi"
    with pytest.raises(IllegalStatusTransition):
        deals.transition_status(db, deal=d, target=DealStatus.ic, actor=lead)


def test_soft_delete_hides(db, make_user):
    lead = make_user()
    d = deals.create_deal(db, lead=lead, name="P", target_company="T", deal_type="lbo")
    db.flush()
    deals.soft_delete(db, deal=d)
    db.flush()
    assert deals.list_visible(db, viewer=lead) == []
    admin = make_user(role="admin")
    assert {x.id for x in deals.list_visible(db, viewer=admin, include_deleted=True)} == {d.id}


def test_add_remove_team_idempotent(db, make_user):
    lead = make_user(); alice = make_user()
    d = deals.create_deal(db, lead=lead, name="P", target_company="T", deal_type="lbo")
    db.flush()
    deals.add_team_member(db, deal=d, user=alice); db.flush()
    deals.add_team_member(db, deal=d, user=alice); db.flush()
    deals.remove_team_member(db, deal=d, user=alice); db.flush()
    assert deals.can_view(db, viewer=alice, deal=d) is False
