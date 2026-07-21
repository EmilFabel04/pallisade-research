from __future__ import annotations

import io
import logging

from pypdf import PdfReader

log = logging.getLogger(__name__)


def extract_text_pages(data: bytes) -> list[tuple[int, str]]:
    """Return [(page_no_1_indexed, text), ...] from a native-text PDF.

    Pages with no extractable text appear as ``(n, "")``. Caller is responsible
    for routing to OCR if the cumulative text is too small.
    """
    try:
        reader = PdfReader(io.BytesIO(data))
    except Exception as exc:                       # noqa: BLE001 — pypdf raises many types
        log.warning("pdf_text: PdfReader failed: %s", exc)
        return []

    pages: list[tuple[int, str]] = []
    for idx, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception as exc:                   # noqa: BLE001
            log.warning("pdf_text: extract_text on page %d failed: %s", idx, exc)
            text = ""
        pages.append((idx, text))
    return pages
