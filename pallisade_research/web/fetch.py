from __future__ import annotations

import ipaddress
import re
import socket
from dataclasses import dataclass
from datetime import date
from typing import Callable
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from bs4 import BeautifulSoup

_SNIPPET_LEN = 280
_MAX_PASSAGES = 12
_ISO = re.compile(r"(\d{4}-\d{2}-\d{2})")
_ALLOWED_SCHEMES = {"http", "https"}


@dataclass(frozen=True)
class FetchedDoc:
    url: str
    title: str
    published: date | None
    passages: tuple[str, ...]


def _is_unsafe_address(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return (
        ip.is_loopback
        or ip.is_private
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_unspecified
        or ip.is_multicast
    )


def _is_safe_url(url: str) -> bool:
    """Reject URLs that could be used for SSRF or local-file reads.

    Only http/https to a resolvable, publicly-routable host are allowed.
    Untrusted (model-chosen, prompt-injectable) URLs must pass this check
    before any network access happens.
    """
    try:
        parsed = urlparse(url)
    except ValueError:
        return False

    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        return False

    host = parsed.hostname
    if not host:
        return False

    try:
        addrinfo = socket.getaddrinfo(host, None)
    except (socket.gaierror, socket.herror, UnicodeError, OSError):
        return False

    if not addrinfo:
        return False

    for family, _, _, _, sockaddr in addrinfo:
        addr = sockaddr[0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            return False
        if _is_unsafe_address(ip):
            return False

    return True


class _SafeRedirectHandler(HTTPRedirectHandler):
    """Re-validate every redirect hop against `_is_safe_url`.

    `urlopen`/`urllib`'s default redirect handling follows `Location`
    headers without re-checking them, so a public page can 302 to an
    internal/loopback/metadata address and bypass the initial guard.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        if not _is_safe_url(newurl):
            raise ValueError(f"unsafe redirect: {newurl}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_OPENER = build_opener(_SafeRedirectHandler)


def _default_get(url: str) -> str:
    if not _is_safe_url(url):
        raise ValueError(f"unsafe url: {url}")
    req = Request(url, headers={"User-Agent": "pallisade-research/1.0"})
    with _OPENER.open(req, timeout=20) as resp:  # noqa: S310 (user-provided URL, best-effort fetch)
        return resp.read().decode("utf-8", "replace")


def _find_published(soup: BeautifulSoup) -> date | None:
    # Try meta first
    meta = soup.find("meta", attrs={"property": "article:published_time"})
    raw = meta.get("content") if meta and meta.get("content") else None
    if raw:
        m = _ISO.search(raw)
        if m:
            try:
                return date.fromisoformat(m.group(1))
            except ValueError:
                pass

    # Fall back to <time> if meta didn't yield an ISO date
    t = soup.find("time")
    raw = t.get("datetime") if t and t.get("datetime") else None
    if raw:
        m = _ISO.search(raw)
        if m:
            try:
                return date.fromisoformat(m.group(1))
            except ValueError:
                pass

    return None


def fetch_url(url: str, *, http_get: Callable[[str], str] | None = None) -> FetchedDoc:
    get = http_get or _default_get
    try:
        html = get(url)
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.get_text(strip=True) if soup.title else ""
        published = _find_published(soup)
        seen: set[str] = set()
        passages: list[str] = []
        for p in soup.find_all("p"):
            text = p.get_text(" ", strip=True)[:_SNIPPET_LEN]
            if not text or text in seen:
                continue
            seen.add(text)
            passages.append(text)
            if len(passages) >= _MAX_PASSAGES:
                break
        return FetchedDoc(url=url, title=title, published=published, passages=tuple(passages))
    except Exception:  # noqa: BLE001 — a bad page must not break the loop
        return FetchedDoc(url=url, title="", published=None, passages=())
