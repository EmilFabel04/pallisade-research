"""Jinja2 + WeasyPrint rendering of the PDF views. Pure: no DB, no clock."""
from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import weasyprint
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .markdown_ext import render_markdown
from .views import DebateView, ResearchConversationView

_DIR = Path(__file__).parent
_CSS = (_DIR / "static" / "print.css").read_text(encoding="utf-8")

_env = Environment(
    loader=FileSystemLoader(str(_DIR / "templates")),
    autoescape=select_autoescape(["html"]),
)
_env.filters["markdown"] = render_markdown


def _safe_url_fetcher(url: str):
    """Block server-side resource fetching during PDF render (SSRF / local-file
    read). Templates embed no external resources, so only data: URIs are allowed."""
    if urlparse(url).scheme.lower() == "data":
        return weasyprint.default_url_fetcher(url)
    raise ValueError(f"external resource blocked in PDF export: {url!r}")


def render_research_html(view: ResearchConversationView) -> str:
    return _env.get_template("research.html").render(
        view=view, css=_CSS, generated_at=view.generated_at
    )


def render_research_pdf(view: ResearchConversationView) -> bytes:
    return weasyprint.HTML(
        string=render_research_html(view), url_fetcher=_safe_url_fetcher
    ).write_pdf()


def render_debate_html(view: DebateView) -> str:
    return _env.get_template("debate.html").render(
        view=view, css=_CSS, generated_at=view.generated_at
    )


def render_debate_pdf(view: DebateView) -> bytes:
    return weasyprint.HTML(
        string=render_debate_html(view), url_fetcher=_safe_url_fetcher
    ).write_pdf()
