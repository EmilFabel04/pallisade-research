"""Jinja2 + WeasyPrint rendering of the PDF views. Pure: no DB, no clock."""
from __future__ import annotations

from pathlib import Path

import weasyprint
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .markdown_ext import render_markdown
from .views import ResearchConversationView

_DIR = Path(__file__).parent
_CSS = (_DIR / "static" / "print.css").read_text(encoding="utf-8")

_env = Environment(
    loader=FileSystemLoader(str(_DIR / "templates")),
    autoescape=select_autoescape(["html"]),
)
_env.filters["markdown"] = render_markdown


def render_research_html(view: ResearchConversationView) -> str:
    return _env.get_template("research.html").render(
        view=view, css=_CSS, generated_at=view.generated_at
    )


def render_research_pdf(view: ResearchConversationView) -> bytes:
    return weasyprint.HTML(string=render_research_html(view)).write_pdf()
