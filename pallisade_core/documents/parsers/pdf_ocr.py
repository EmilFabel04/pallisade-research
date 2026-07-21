from __future__ import annotations

import asyncio
import base64
import io
import logging
from typing import Protocol

import pypdfium2 as pdfium
from PIL import Image

log = logging.getLogger(__name__)


class VisionClient(Protocol):
    async def transcribe_page(self, *, page_index: int, png_bytes: bytes) -> str: ...


class AnthropicVisionClient:
    """Wraps the anthropic SDK for page-image OCR.

    Kept thin so tests stub `transcribe_page` directly via the VisionClient Protocol.
    """

    def __init__(self, *, api_key: str, model: str):
        from anthropic import AsyncAnthropic
        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model

    async def transcribe_page(self, *, page_index: int, png_bytes: bytes) -> str:
        b64 = base64.standard_b64encode(png_bytes).decode("ascii")
        msg = await self._client.messages.create(
            model=self._model,
            max_tokens=4000,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {
                            "type": "base64", "media_type": "image/png", "data": b64,
                        }},
                        {"type": "text", "text":
                            "Transcribe ALL text visible on this document page. "
                            "Preserve tables row by row using ' | ' separators. "
                            "Return only the transcription — no commentary."},
                    ],
                }
            ],
        )
        parts: list[str] = []
        for block in msg.content:
            if getattr(block, "type", None) == "text":
                parts.append(block.text)
        return "\n".join(parts).strip()


def _render_pages_to_png(data: bytes, *, dpi: int = 150) -> list[bytes]:
    pdf = pdfium.PdfDocument(data)
    scale = dpi / 72.0
    pngs: list[bytes] = []
    try:
        for i in range(len(pdf)):
            page = pdf[i]
            bitmap = page.render(scale=scale)
            pil: Image.Image = bitmap.to_pil()
            buf = io.BytesIO()
            pil.save(buf, format="PNG", optimize=True)
            pngs.append(buf.getvalue())
            page.close()
    finally:
        pdf.close()
    return pngs


async def extract_text_pages(
    *, data: bytes, client: VisionClient, concurrency: int = 4,
) -> list[tuple[int, str]]:
    """OCR every page via the given VisionClient, bounded by ``concurrency``."""
    pngs = _render_pages_to_png(data)
    sem = asyncio.Semaphore(concurrency)

    async def _one(i: int, png: bytes) -> tuple[int, str]:
        async with sem:
            text = await client.transcribe_page(page_index=i, png_bytes=png)
        return (i + 1, text)

    tasks = [_one(i, png) for i, png in enumerate(pngs)]
    results = await asyncio.gather(*tasks)
    return sorted(results, key=lambda t: t[0])
