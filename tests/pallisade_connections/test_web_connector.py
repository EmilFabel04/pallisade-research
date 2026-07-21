import os

from pallisade_connections.registry import get_connector


def test_web_connector_registered_and_capabilities():
    c = get_connector("web")
    assert c.type_id == "web"
    assert c.requires_credentials is False
    assert c.capabilities == frozenset({"news", "research", "estimates", "transcripts"})


def test_web_connector_test_reflects_env(monkeypatch):
    monkeypatch.delenv("WEB_SEARCH_API_KEY", raising=False)
    assert get_connector("web").test(None, {})["ok"] is False
    monkeypatch.setenv("WEB_SEARCH_API_KEY", "k")
    assert get_connector("web").test(None, {})["ok"] is True


def test_web_connector_noop_source_fetches_nothing():
    src = get_connector("web").as_research_source(None, {})
    assert src.source == "web" and src.tier == 3
    assert src.fetch(object()) == []
