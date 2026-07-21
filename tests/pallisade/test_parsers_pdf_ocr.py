import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from pallisade_core.documents.parsers import pdf_ocr


class _FakeVisionClient:
    """Returns scripted text per page index (0-based)."""
    def __init__(self, by_index: dict[int, str]):
        self.by_index = by_index
        self.calls: list[int] = []

    async def transcribe_page(self, *, page_index: int, png_bytes: bytes) -> str:
        self.calls.append(page_index)
        return self.by_index[page_index]


@pytest.mark.asyncio
async def test_ocr_iterates_pages_and_returns_text():
    # Use the 2-page text fixture from Task 8 — pages will still render to PNG.
    from pathlib import Path
    fx = Path(__file__).parent / "fixtures" / "text_cim.pdf"
    fake = _FakeVisionClient({0: "page one ocr", 1: "page two ocr"})
    pages = await pdf_ocr.extract_text_pages(
        data=fx.read_bytes(), client=fake, concurrency=2,
    )
    assert pages == [(1, "page one ocr"), (2, "page two ocr")]
    assert sorted(fake.calls) == [0, 1]


def test_module_exports_anthropic_client_factory():
    client = pdf_ocr.AnthropicVisionClient(api_key="test-key", model="claude-haiku-4-5-20251001")
    assert hasattr(client, "transcribe_page")
