from __future__ import annotations

import pytest

from pallisade_core.users import service as users
from pallisade_core.users.models import User


def test_create_and_find_by_email(db):
    u = users.create_user(db, email="a@example.com", name="Ada", role="member", password="Pass!1234567")
    db.flush()
    assert isinstance(u, User) and u.id is not None
    assert users.find_by_email(db, "a@example.com").id == u.id
    assert users.find_by_email(db, "missing@example.com") is None


def test_unique_email(db):
    users.create_user(db, email="dup@example.com", name="A", role="member", password="Pass!1234567")
    db.flush()
    with pytest.raises(Exception):
        users.create_user(db, email="dup@example.com", name="B", role="member", password="Pass!1234567")
        db.flush()


def test_set_password_clears_must_change(db):
    u = users.create_user(db, email="b@example.com", name="B", role="member", password="Pass!1234567")
    db.flush()
    assert u.must_change_password is True
    users.set_password(db, u, "NewPass!1234567")
    assert u.must_change_password is False
    assert users.verify_credentials(db, "b@example.com", "NewPass!1234567") is not None
    assert users.verify_credentials(db, "b@example.com", "wrong") is None
