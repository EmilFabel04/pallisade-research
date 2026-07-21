from pallisade_core.chat import service as chat_service
from pallisade_core.chat.models import ChatConversation, ChatMessage
from pallisade_core.deals.models import Deal


def _deal(db, lead):
    d = Deal(name="X", target_company="Y", deal_type="lbo",
             deal_lead_id=lead.id, status="screening")
    db.add(d); db.flush()
    return d


def test_get_or_create_returns_same_row_for_same_pair(db, make_user):
    u = make_user()
    deal = _deal(db, u)
    c1 = chat_service.get_or_create_conversation_for_deal(db, deal=deal, user=u)
    c2 = chat_service.get_or_create_conversation_for_deal(db, deal=deal, user=u)
    assert c1.id == c2.id


def test_append_user_and_assistant_messages_in_order(db, make_user):
    u = make_user()
    deal = _deal(db, u)
    conv = chat_service.get_or_create_conversation_for_deal(db, deal=deal, user=u)
    chat_service.append_message(db, conversation=conv, role="user", content="hi")
    chat_service.append_message(db, conversation=conv, role="assistant",
                                content="hello", citations=[{"filename": "a.pdf"}])
    msgs = chat_service.list_messages(db, conversation=conv)
    assert [m.role for m in msgs] == ["user", "assistant"]
    assert msgs[1].citations[0]["filename"] == "a.pdf"


def test_reset_drops_all_messages_but_keeps_conversation(db, make_user):
    u = make_user()
    deal = _deal(db, u)
    conv = chat_service.get_or_create_conversation_for_deal(db, deal=deal, user=u)
    chat_service.append_message(db, conversation=conv, role="user", content="hi")
    chat_service.reset_conversation(db, conversation=conv)
    assert chat_service.list_messages(db, conversation=conv) == []
    # Conversation row still exists:
    assert db.get(ChatConversation, conv.id) is not None
