from __future__ import annotations

import pytest

from pallisade_core.auth import permissions


def test_require_admin_passes(make_user, db):
    admin = make_user(role="admin")
    permissions.require_admin(admin)


def test_require_admin_raises(make_user, db):
    member = make_user(role="member")
    with pytest.raises(permissions.PermissionDenied):
        permissions.require_admin(member)


def test_can_manage_deal(make_user, db):
    from pallisade_core.deals import service as deals
    lead = make_user(); other = make_user(); admin = make_user(role="admin")
    d = deals.create_deal(db, lead=lead, name="P", target_company="T", deal_type="lbo")
    db.flush()
    assert permissions.can_manage_deal(actor=lead, deal=d) is True
    assert permissions.can_manage_deal(actor=admin, deal=d) is True
    assert permissions.can_manage_deal(actor=other, deal=d) is False
