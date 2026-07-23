import pytest

from web.api.services.pdf.render import _safe_url_fetcher


def test_blocks_file_scheme():
    with pytest.raises(ValueError):
        _safe_url_fetcher("file:///etc/passwd")


def test_blocks_http_scheme():
    with pytest.raises(ValueError):
        _safe_url_fetcher("http://169.254.169.254/latest/meta-data/")


def test_allows_data_uri():
    # Installed weasyprint (69.0, pinned as `weasyprint>=62`) returns a
    # URLFetcherResponse object here rather than the older dict shape, so we
    # assert on intent (data: URIs pass through, unlike other schemes) rather
    # than an internal return type that has since changed upstream.
    result = _safe_url_fetcher("data:text/plain;base64,aGk=")
    assert result is not None
