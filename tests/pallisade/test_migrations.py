from __future__ import annotations

from sqlalchemy import inspect

from pallisade_core.db.session import get_engine


def test_migrations_create_users_table(_migrate):
    insp = inspect(get_engine())
    assert "users" in insp.get_table_names()
    cols = {c["name"] for c in insp.get_columns("users")}
    assert {"id", "email", "password_hash", "name", "role", "must_change_password",
            "created_at", "last_login_at"} <= cols
