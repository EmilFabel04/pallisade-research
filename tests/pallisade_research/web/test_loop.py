from pallisade_research.models import ResearchQuery
from pallisade_research.web.fetch import FetchedDoc
from pallisade_research.web.loop import WebResearchResult, research
from pallisade_research.web.search import SearchHit


class _Block:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class _Msg:
    def __init__(self, content, stop_reason):
        self.content = content
        self.stop_reason = stop_reason


class _ScriptedSDK:
    """Yields pre-scripted Anthropic responses in order; records tool inputs seen."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.messages = self

    def create(self, **kw):
        return self._responses.pop(0)


def _tool_use(tid, name, inp):
    return _Block(type="tool_use", id=tid, name=name, input=inp)


def _q(caps=("research",)):
    return ResearchQuery(question="What's new at Naspers?", ticker="NPN.JO", capabilities=caps)


def test_loop_turns_fetched_passages_into_web_records():
    sdk = _ScriptedSDK([
        _Msg([_tool_use("t1", "web_search", {"query": "naspers news"})], "tool_use"),
        _Msg([_tool_use("t2", "fetch_url", {"url": "https://ex.com/a"})], "tool_use"),
        _Msg([_Block(type="text", text="done")], "end_turn"),
    ])
    hits = [SearchHit(title="N", url="https://ex.com/a", snippet="s")]
    doc = FetchedDoc(url="https://ex.com/a", title="Naspers H1", published=None,
                     passages=("Revenue rose 12%.", "Margins expanded."))
    res = research(_q(), sdk=sdk, model="m", depth="shallow",
                   search=lambda *a, **k: hits, fetch=lambda *a, **k: doc)
    assert res.used is True and res.unavailable is False
    assert [r.value for r in res.records] == ["Revenue rose 12%.", "Margins expanded."]
    assert all(r.provenance.source == "web" and r.provenance.tier == 3 for r in res.records)
    assert all(r.capability == "research" and r.provenance.locator == "https://ex.com/a" for r in res.records)


def test_loop_enforces_shallow_fetch_budget():
    # SDK keeps asking to fetch; shallow cap is 3 fetches.
    fetches = [_Msg([_tool_use(f"t{i}", "fetch_url", {"url": f"https://ex.com/{i}"})], "tool_use") for i in range(10)]
    sdk = _ScriptedSDK([_Msg([_tool_use("s", "web_search", {"query": "x"})], "tool_use"), *fetches])
    calls = {"n": 0}

    def fetch(url, **k):
        calls["n"] += 1
        return FetchedDoc(url=url, title="", published=None, passages=("p",))

    res = research(_q(), sdk=sdk, model="m", depth="shallow",
                   search=lambda *a, **k: [SearchHit("", "https://ex.com/0", "")], fetch=fetch)
    assert calls["n"] <= 3


def test_loop_swallows_error_and_flags_unavailable():
    class _Boom:
        messages = property(lambda self: self)
        def create(self, **kw):
            raise RuntimeError("api down")
    res = research(_q(), sdk=_Boom(), model="m")
    assert res == WebResearchResult(records=(), used=False, unavailable=True)


def test_loop_no_results_used_false():
    sdk = _ScriptedSDK([_Msg([_Block(type="text", text="nothing to add")], "end_turn")])
    res = research(_q(), sdk=sdk, model="m", search=lambda *a, **k: [], fetch=lambda *a, **k: None)
    assert res.used is False and res.records == ()


def test_loop_enforces_shallow_search_round_budget():
    # SDK keeps asking to search; shallow cap is 1 search round.
    searches_req = [_Msg([_tool_use(f"s{i}", "web_search", {"query": "x"})], "tool_use") for i in range(3)]
    sdk = _ScriptedSDK([*searches_req, _Msg([_Block(type="text", text="done")], "end_turn")])
    calls = {"n": 0}

    def search(query, **k):
        calls["n"] += 1
        return [SearchHit("N", "https://ex.com/a", "s")]

    res = research(_q(), sdk=sdk, model="m", depth="shallow",
                   search=search, fetch=lambda *a, **k: None)
    assert calls["n"] <= 1


def test_loop_deep_budget_allows_more_fetches():
    # Deep budget allows up to 8 fetches, unlike shallow's cap of 3.
    fetches = [_Msg([_tool_use(f"t{i}", "fetch_url", {"url": f"https://ex.com/{i}"})], "tool_use") for i in range(5)]
    sdk = _ScriptedSDK([_Msg([_tool_use("s", "web_search", {"query": "x"})], "tool_use"), *fetches,
                        _Msg([_Block(type="text", text="done")], "end_turn")])
    calls = {"n": 0}

    def fetch(url, **k):
        calls["n"] += 1
        return FetchedDoc(url=url, title="", published=None, passages=("p",))

    res = research(_q(), sdk=sdk, model="m", depth="deep",
                   search=lambda *a, **k: [SearchHit("", "https://ex.com/0", "")], fetch=fetch)
    assert calls["n"] == 5


def test_loop_malformed_query_returns_unavailable():
    class _Malformed:
        question = "Q"
        ticker = None

        @property
        def capabilities(self):
            raise TypeError("boom")

    res = research(_Malformed(), sdk=_ScriptedSDK([]), model="m")
    assert res == WebResearchResult(records=(), used=False, unavailable=True)
