from datetime import date

from pallisade_research.web.fetch import FetchedDoc, fetch_url

_HTML = """
<html><head><title>Naspers H1 Results</title>
<meta property="article:published_time" content="2026-03-14T09:00:00Z"></head>
<body>
<p>Revenue rose 12% to R80bn.</p>
<p>   </p>
<p>Management guided margins higher for FY27.</p>
<p>Revenue rose 12% to R80bn.</p>
</body></html>
"""


def test_fetch_url_extracts_title_date_and_dedup_passages():
    doc = fetch_url("https://ex.com/a", http_get=lambda u: _HTML)
    assert doc.url == "https://ex.com/a"
    assert doc.title == "Naspers H1 Results"
    assert doc.published == date(2026, 3, 14)
    assert doc.passages == ("Revenue rose 12% to R80bn.", "Management guided margins higher for FY27.")


def test_fetch_url_truncates_to_280_chars():
    long = "A" * 400
    doc = fetch_url("https://ex.com/b", http_get=lambda u: f"<html><body><p>{long}</p></body></html>")
    assert len(doc.passages[0]) == 280


def test_fetch_url_error_returns_empty_passages():
    def boom(u):
        raise RuntimeError("timeout")
    doc = fetch_url("https://ex.com/c", http_get=boom)
    assert doc == FetchedDoc(url="https://ex.com/c", title="", published=None, passages=())
