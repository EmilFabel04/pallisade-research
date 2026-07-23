"""Markdown -> safe HTML for use inside autoescaped Jinja templates."""
from __future__ import annotations

import markdown as _md
from markupsafe import Markup


def render_markdown(text: str | None) -> Markup:
    if not text:
        return Markup("")
    html = _md.markdown(text, extensions=["tables", "fenced_code", "sane_lists"])
    return Markup(html)
