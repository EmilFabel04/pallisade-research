import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from pallisade_core.chat import service as chat_service
from pallisade_core.chat.service import DealAnchor, GlobalAnchor, LibraryDocAnchor
from pallisade_core.chat.models import ChatConversation
from pallisade_core.deals.models import Deal


def _deal(db, lead):
    d = Deal(name=f"Deal-{uuid.uuid4().hex[:6]}", target_company="TargetCo",
             deal_type="lbo", deal_lead_id=lead.id, status="screening")
    db.add(d)
    db.flush()
    return d


def test_global_anchor_get_or_create_is_singleton(db, make_user):
    user = make_user()
    a = chat_service.get_or_create_conversation(
        db, user=user, anchor=GlobalAnchor()
    )
    db.commit()
    b = chat_service.get_or_create_conversation(
        db, user=user, anchor=GlobalAnchor()
    )
    assert a.id == b.id
    assert a.kind == "global"
    assert a.deal_id is None and a.library_doc_id is None


def test_library_doc_anchor_per_user(db, make_user, make_library_document):
    user = make_user()
    doc = make_library_document()
    a = chat_service.get_or_create_conversation(
        db, user=user, anchor=LibraryDocAnchor(library_doc_id=doc.id)
    )
    db.commit()
    b = chat_service.get_or_create_conversation(
        db, user=user, anchor=LibraryDocAnchor(library_doc_id=doc.id)
    )
    assert a.id == b.id
    assert a.kind == "library_doc"


def test_db_rejects_two_anchors_set(db, make_user, make_library_document):
    user = make_user()
    deal = _deal(db, make_user())
    doc = make_library_document()
    bad = ChatConversation(
        kind="deal", deal_id=deal.id, library_doc_id=doc.id, user_id=user.id,
    )
    db.add(bad)
    with pytest.raises(IntegrityError):
        db.flush()
