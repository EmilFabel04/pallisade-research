from __future__ import annotations

import re
from dataclasses import dataclass

import tiktoken

from pallisade_core.documents.parsers.xlsx import SheetText

_ENC = tiktoken.get_encoding("cl100k_base")
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")


@dataclass(frozen=True)
class Chunk:
    chunk_index: int
    text: str
    token_count: int
    page_from: int | None = None
    page_to: int | None = None
    sheet_name: str | None = None


def _tok(text: str) -> int:
    return len(_ENC.encode(text))


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT_SPLIT.split(text) if s.strip()]


def _pack_sentences(
    sentences: list[str], *, target: int, overlap: int,
) -> list[tuple[str, int]]:
    """Pack sentences into windows of ~target tokens with ~overlap-token tail."""
    out: list[tuple[str, int]] = []
    buf: list[str] = []
    buf_tokens = 0
    i = 0
    while i < len(sentences):
        s = sentences[i]
        st = _tok(s)
        if buf_tokens + st > target and buf:
            text = " ".join(buf)
            out.append((text, buf_tokens))
            # Build overlap tail from the end of buf.
            tail: list[str] = []
            tail_tokens = 0
            for prev in reversed(buf):
                pt = _tok(prev)
                if tail_tokens + pt > overlap:
                    break
                tail.insert(0, prev)
                tail_tokens += pt
            buf = list(tail)
            buf_tokens = tail_tokens
            continue
        buf.append(s)
        buf_tokens += st
        i += 1
    if buf:
        out.append((" ".join(buf), buf_tokens))
    return out


def chunk_pages(
    pages: list[tuple[int, str]], *, target_tokens: int = 500, overlap_tokens: int = 80,
) -> list[Chunk]:
    """Chunk extracted PDF pages.

    Chunks never cross a page boundary unless a page is itself oversized — then
    that page is split mid-page with both ``page_from`` and ``page_to`` set to
    the page number.
    """
    chunks: list[Chunk] = []
    idx = 0
    for page_no, text in pages:
        text = text.strip()
        if not text:
            continue
        sentences = _split_sentences(text) or [text]
        packed = _pack_sentences(sentences, target=target_tokens, overlap=overlap_tokens)
        if not packed:
            continue
        for piece, tk in packed:
            chunks.append(Chunk(
                chunk_index=idx, text=piece, token_count=tk,
                page_from=page_no, page_to=page_no,
            ))
            idx += 1
    return chunks


def chunk_sheets(sheets: list[SheetText], *, target_tokens: int = 1500) -> list[Chunk]:
    """Chunk extracted XLSX sheets. One chunk per sheet unless the sheet is too large."""
    chunks: list[Chunk] = []
    idx = 0
    for s in sheets:
        total_tk = _tok(s.text)
        if total_tk <= target_tokens:
            chunks.append(Chunk(
                chunk_index=idx, text=s.text, token_count=total_tk,
                sheet_name=s.sheet_name,
            ))
            idx += 1
            continue
        # Split by line, preserving the header on the first chunk only; subsequent
        # chunks get a synthesized continuation header.
        lines = s.text.split("\n")
        header = lines[0] if lines and lines[0].startswith("[Sheet:") else f"[Sheet: {s.sheet_name}]"
        body = lines[1:] if lines and lines[0].startswith("[Sheet:") else lines
        cur: list[str] = []
        cur_tokens = 0
        part_no = 1

        def _flush(part_no_: int) -> int:
            nonlocal cur, cur_tokens, idx
            if not cur:
                return part_no_
            cont_header = header if part_no_ == 1 else f"{header} (cont. {part_no_})"
            text = cont_header + "\n" + "\n".join(cur)
            chunks.append(Chunk(
                chunk_index=idx, text=text, token_count=_tok(text),
                sheet_name=s.sheet_name,
            ))
            idx += 1
            cur = []
            cur_tokens = 0
            return part_no_ + 1

        for line in body:
            lt = _tok(line)
            if cur_tokens + lt > target_tokens and cur:
                part_no = _flush(part_no)
            cur.append(line)
            cur_tokens += lt
        _flush(part_no)
    return chunks
