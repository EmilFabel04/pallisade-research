from datetime import date

import pytest

from pallisade_research.web.fetch import FetchedDoc, _SafeRedirectHandler, _is_safe_url, fetch_url
from urllib.request import Request

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


def test_fetch_url_dedups_after_truncation():
    # Two paragraphs with identical first 280 chars but different tails
    prefix = "A" * 280
    suffix1 = "B" * 50
    suffix2 = "C" * 50
    html = f"""<html><body>
    <p>{prefix}{suffix1}</p>
    <p>{prefix}{suffix2}</p>
    </body></html>"""
    doc = fetch_url("https://ex.com/d", http_get=lambda u: html)
    # After truncation to 280 chars, both become identical, should deduplicate to 1
    assert len(doc.passages) == 1
    assert doc.passages[0] == prefix


def test_fetch_url_date_falls_through_nonISO_meta_to_time():
    # HTML with non-ISO meta content but valid <time datetime>
    html = """<html><head>
    <meta property="article:published_time" content="not-a-date">
    </head><body>
    <time datetime="2026-05-09T00:00:00Z">May 9, 2026</time>
    </body></html>"""
    doc = fetch_url("https://ex.com/e", http_get=lambda u: html)
    assert doc.published == date(2026, 5, 9)


def test_is_safe_url_rejects_non_http_schemes():
    assert _is_safe_url("file:///etc/passwd") is False
    assert _is_safe_url("ftp://x/y") is False


def test_is_safe_url_rejects_loopback_and_metadata():
    assert _is_safe_url("http://127.0.0.1/") is False
    assert _is_safe_url("http://169.254.169.254/latest/meta-data/") is False
    assert _is_safe_url("http://localhost/") is False


def test_is_safe_url_rejects_private():
    assert _is_safe_url("http://10.0.0.5/") is False
    assert _is_safe_url("http://192.168.1.1/") is False


def test_is_safe_url_allows_public_https():
    assert _is_safe_url("https://example.com/article") is True


def test_default_get_blocks_unsafe_redirect():
    handler = _SafeRedirectHandler()
    req = Request("https://example.com/")

    with pytest.raises(ValueError):
        handler.redirect_request(req, None, 302, "Found", {}, "http://169.254.169.254/")

    # A safe redirect target must not raise (base handler returns a Request or None).
    result = handler.redirect_request(req, None, 302, "Found", {}, "https://example.com/next")
    assert result is None or isinstance(result, Request)
