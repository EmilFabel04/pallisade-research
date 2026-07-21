from pallisade_research.chat import PLAN_TOOL, _plan_with_llm


def test_plan_tool_exposes_entity_fields():
    props = PLAN_TOOL["input_schema"]["properties"]
    assert "entity" in props and "entity_type" in props
    caps = props["capabilities"]["items"]["enum"]
    assert "macro" in caps and "markets" in caps


class _Block:
    type = "tool_use"

    def __init__(self, inp):
        self.input = inp


class _Message:
    def __init__(self, inp):
        self.content = [_Block(inp)]


class _Messages:
    def __init__(self, inp):
        self._inp = inp

    def create(self, **kwargs):
        return _Message(self._inp)


class _SDK:
    def __init__(self, inp):
        self.messages = _Messages(inp)


def test_plan_reads_entity():
    inp = {"ticker": None, "standalone_question": "Nigeria GDP",
           "capabilities": ["macro"], "entity": "Nigeria", "entity_type": "country"}
    q = _plan_with_llm(_SDK(inp), "m", [], "how's Nigeria's economy?")
    assert q.entity == "Nigeria" and q.entity_type == "country"
    assert "macro" in q.capabilities
    assert q.ticker is None


def test_plan_equity_leaves_entity_none():
    inp = {"ticker": "AAPL", "standalone_question": "Apple valuation",
           "capabilities": ["fundamentals"], "entity": None, "entity_type": None}
    q = _plan_with_llm(_SDK(inp), "m", [], "how's apple valued?")
    assert q.ticker == "AAPL"
    assert q.entity is None and q.entity_type is None
