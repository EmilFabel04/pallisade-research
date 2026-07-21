import pytest
from sqlalchemy.exc import IntegrityError

from pallisade_core.chat.models import ChatConversation, ChatMessage
from pallisade_core.deals.models import Deal


def _deal(db, lead):
    d = Deal(name="x", target_company="y", deal_type="lbo",
             deal_lead_id=lead.id, status="screening")
    db.add(d); db.flush()
    return d


def test_one_conversation_per_deal_user(db, make_user):
    u = make_user()
    d = _deal(db, u)
    db.add(ChatConversation(deal_id=d.id, user_id=u.id))
    db.flush()
    db.add(ChatConversation(deal_id=d.id, user_id=u.id))
    with pytest.raises(IntegrityError):
        db.flush()


def test_chat_message_with_citations_jsonb(db, make_user):
    u = make_user()
    d = _deal(db, u)
    conv = ChatConversation(deal_id=d.id, user_id=u.id)
    db.add(conv); db.flush()
    msg = ChatMessage(
        conversation_id=conv.id, role="assistant", content="hi",
        citations=[{"filename": "a.pdf", "page_from": 1, "page_to": 1}],
    )
    db.add(msg); db.flush()
    db.refresh(msg)
    assert msg.citations[0]["filename"] == "a.pdf"
