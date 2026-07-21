from pallisade_research.web.search import SearchHit, web_search


def _fake_post(payload):
    def post(url, body):
        assert url == "https://api.tavily.com/search"
        assert body["query"] == "naspers earnings"
        assert body["max_results"] == 3
        return payload
    return post


def test_web_search_maps_results_to_hits():
    payload = {"results": [
        {"title": "Naspers H1", "url": "https://ex.com/a", "content": "Revenue rose 12%."},
        {"title": "Prosus note", "url": "https://ex.com/b", "content": "Margins expanded."},
    ]}
    hits = web_search("naspers earnings", k=3, http_post=_fake_post(payload), api_key="k")
    assert hits == [
        SearchHit(title="Naspers H1", url="https://ex.com/a", snippet="Revenue rose 12%."),
        SearchHit(title="Prosus note", url="https://ex.com/b", snippet="Margins expanded."),
    ]


def test_web_search_no_key_returns_empty():
    assert web_search("x", api_key="") == []


def test_web_search_bad_payload_returns_empty():
    hits = web_search("x", http_post=lambda u, b: {"unexpected": 1}, api_key="k")
    assert hits == []
