from pallisade_research.chat import converse
from pallisade_research.models import ResearchQuery
from pallisade_research.sources.registry import ClientConfig


class _FakeSDK:
    """Planner returns a fixed plan; narrator returns fixed prose; loop sdk unused here."""
    def __init__(self):
        self.messages = self

    def create(self, **kw):
        # planner path uses tool_choice; narrator path does not.
        if kw.get("tool_choice"):
            class B:
                type = "tool_use"
                input = {"ticker": "NPN.JO", "standalone_question": "news?", "capabilities": ["research"]}
            return type("M", (), {"content": [B()]})()
        return type("M", (), {"content": [type("T", (), {"type": "text", "text": "Summary."})()]})()


def test_converse_appends_web_records_when_enabled(monkeypatch):
    captured = {}

    def fake_research(query, **kw):
        captured["depth"] = kw["depth"]
        from pallisade_research.models import Provenance, Record
        from pallisade_research.web.loop import WebResearchResult
        rec = Record(id="web-0", capability="research", key="web.0", value="Analyst note.",
                     provenance=Provenance(source="web", locator="https://ex.com", as_of=None, tier=3))
        return WebResearchResult(records=(rec,), used=True, unavailable=False)

    monkeypatch.setattr("pallisade_research.chat.web_research", fake_research)
    config = ClientConfig(client_id="c", enabled_sources=frozenset())
    turn = converse([], "any news?", config=config, registry={}, known_tickers=frozenset({"NPN.JO"}),
                    sdk=_FakeSDK(), plan_model="p", narrate_model="n",
                    depth="deep", web_enabled=True, web_model="w")
    assert captured["depth"] == "deep"
    ans = turn["answer"]
    assert "web" in ans.sources_used
    assert any("web" in c.text for c in ans.claims)


def test_converse_skips_web_when_disabled(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("web loop must not run when disabled")
    monkeypatch.setattr("pallisade_research.chat.web_research", boom)
    config = ClientConfig(client_id="c", enabled_sources=frozenset())
    turn = converse([], "hi", config=config, registry={}, known_tickers=frozenset(),
                    sdk=None, plan_model="p", narrate_model="n", web_enabled=False)
    assert turn["answer"].sources_used == ()


def test_converse_caps_web_by_depth(monkeypatch):
    """Web records are capped by depth (shallow=5, deep=12) before grounding."""
    def fake_research(query, **kw):
        from pallisade_research.models import Provenance, Record
        from pallisade_research.web.loop import WebResearchResult
        recs = tuple(
            Record(id=f"web-{i}", capability="research", key=f"web.{i}",
                   value=f"Analyst note number {i}.",
                   provenance=Provenance(source="web", locator="https://ex.com", as_of=None, tier=3))
            for i in range(10)
        )
        return WebResearchResult(records=recs, used=True, unavailable=False)

    monkeypatch.setattr("pallisade_research.chat.web_research", fake_research)
    config = ClientConfig(client_id="c", enabled_sources=frozenset())

    shallow = converse([], "any news?", config=config, registry={}, known_tickers=frozenset({"NPN.JO"}),
                        sdk=_FakeSDK(), plan_model="p", narrate_model="n",
                        depth="shallow", web_enabled=True, web_model="w")
    web_records_shallow = [r for r in shallow["answer"].records if r.provenance.source == "web"]
    assert len(web_records_shallow) <= 5

    deep = converse([], "any news?", config=config, registry={}, known_tickers=frozenset({"NPN.JO"}),
                     sdk=_FakeSDK(), plan_model="p", narrate_model="n",
                     depth="deep", web_enabled=True, web_model="w")
    web_records_deep = [r for r in deep["answer"].records if r.provenance.source == "web"]
    assert len(web_records_deep) <= 12
    assert len(web_records_deep) == 10  # all 10 survive under the deep cap
