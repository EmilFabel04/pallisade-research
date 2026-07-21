from __future__ import annotations

from pallisade_core.research_history import service as svc

MSGS = [
    {"id": 1, "role": "user", "content": "overview of AAPL"},
    {"id": 2, "role": "assistant", "content": "Apple is...", "answer": {"claims": []}},
]


def test_upsert_creates_then_updates_same_row(db, make_user):
    u = make_user()
    row = svc.upsert_conversation(db, user=u, conversation_id=None, title="overview of AAPL", messages=MSGS)
    db.flush()
    assert row.id is not None
    assert row.title == "overview of AAPL"
    assert len(row.payload) == 2

    updated = svc.upsert_conversation(
        db, user=u, conversation_id=row.id, title="overview of AAPL",
        messages=MSGS + [{"id": 3, "role": "user", "content": "and its margins?"}],
    )
    db.flush()
    assert updated.id == row.id  # same row, not a new one
    assert len(updated.payload) == 3
    assert len(svc.list_conversations(db, user=u)) == 1


def test_list_is_user_scoped_newest_first(db, make_user):
    a, b = make_user(), make_user()
    c1 = svc.upsert_conversation(db, user=a, conversation_id=None, title="first", messages=MSGS)
    db.flush()
    c2 = svc.upsert_conversation(db, user=a, conversation_id=None, title="second", messages=MSGS)
    db.flush()
    svc.upsert_conversation(db, user=b, conversation_id=None, title="bob", messages=MSGS)
    db.flush()

    rows = svc.list_conversations(db, user=a)
    assert {r.id for r in rows} == {c1.id, c2.id}  # never sees bob's
    assert rows[0].updated_at >= rows[1].updated_at  # newest first


def test_get_is_user_scoped(db, make_user):
    a, b = make_user(), make_user()
    row = svc.upsert_conversation(db, user=a, conversation_id=None, title="a", messages=MSGS)
    db.flush()
    assert svc.get_conversation(db, user=a, conversation_id=row.id) is not None
    assert svc.get_conversation(db, user=b, conversation_id=row.id) is None


def test_upsert_with_foreign_id_creates_new_not_hijack(db, make_user):
    a, b = make_user(), make_user()
    bob_row = svc.upsert_conversation(db, user=b, conversation_id=None, title="bob", messages=MSGS)
    db.flush()
    # user A passes bob's id — must NOT overwrite bob's; creates A's own instead
    a_row = svc.upsert_conversation(db, user=a, conversation_id=bob_row.id, title="hijack?", messages=MSGS)
    db.flush()
    assert a_row.id != bob_row.id
    assert svc.get_conversation(db, user=b, conversation_id=bob_row.id).title == "bob"


def test_delete_is_user_scoped(db, make_user):
    a, b = make_user(), make_user()
    row = svc.upsert_conversation(db, user=a, conversation_id=None, title="a", messages=MSGS)
    db.flush()
    assert svc.delete_conversation(db, user=b, conversation_id=row.id) is False  # not bob's
    assert svc.delete_conversation(db, user=a, conversation_id=row.id) is True
    assert svc.get_conversation(db, user=a, conversation_id=row.id) is None
