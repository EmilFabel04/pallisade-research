from __future__ import annotations

import logging
import uuid
from dataclasses import asdict
from typing import AsyncIterator, Protocol

from sqlalchemy.orm import Session

from pallisade_core.deals.models import Deal
from pallisade_core.rag.retrieve import (
    LibraryPassage, Passage, retrieve_for_library_doc, retrieve_for_global,
    retrieve_passages,
)

log = logging.getLogger(__name__)


class ChatLLM(Protocol):
    async def stream(self, *, system: str, messages: list[dict]) -> AsyncIterator[str]: ...


class RewriteLLM(Protocol):
    async def rewrite(self, *, history: list[dict], message: str) -> list[str]: ...


def build_system_prompt(*, deal: Deal) -> str:
    return (
        f"You are a senior PE analyst supporting diligence on deal {deal.name} "
        f"(target: {deal.target_company}, type: {deal.deal_type}). You work for "
        "Pallisade Data. Your audience is the IC: sharp, time-poor, sceptical.\n"
        "\n"
        "GROUNDING\n"
        "- Answer using ONLY the passages provided in the user message. Do not "
        "rely on outside knowledge of the company, sector, or comparable deals.\n"
        "- If the passages don't contain the answer, say so in one short sentence "
        "(e.g. \"Not in the provided materials.\") and stop. Do not speculate, "
        "do not list adjacent things you do know, and do not pad.\n"
        "- Never invent or round numbers. Quote figures exactly as they appear.\n"
        "\n"
        "CITATIONS\n"
        "- Cite every quantitative claim and every direct quote inline at the end "
        "of the sentence: [filename p.PAGE] for PDFs, [filename · SheetName] for "
        "spreadsheets. Multiple citations: [a.pdf p.3][b.xlsx · Model].\n"
        "- Cite the passages you actually used, not all of them.\n"
        "\n"
        "STRUCTURE\n"
        "- Open with a one- or two-sentence direct answer in plain prose. No "
        "preamble, no restating the question, no \"Great question\".\n"
        "- Then, if useful, add a short evidence section. Prefer compact bullets "
        "or a small markdown table to long paragraphs.\n"
        "- If you genuinely cannot answer part of the question, end with a single "
        "line: \"Gap: <what's missing>\". One gap line max.\n"
        "\n"
        "FORMAT\n"
        "- Markdown is rendered. Use it lightly: **bold** for the key number or "
        "verdict, bullets for lists of three+ items, GFM tables for any data with "
        "two+ columns. Use `###` (not `##`) if you must add a sub-heading; most "
        "answers need no heading at all.\n"
        "- Never use horizontal rules (`---`). Never use `##` or `#` headings. "
        "Don't quote long blockquotes — paraphrase and cite instead, unless the "
        "user explicitly asked for the verbatim passage.\n"
        "- Keep answers under ~200 words unless the user asks for depth."
    )


def _label(p: Passage) -> str:
    if p.sheet_name:
        return f"[{p.filename} · {p.sheet_name}]"
    if p.page_from is not None:
        return f"[{p.filename} p.{p.page_from}]"
    return f"[{p.filename}]"


def build_user_prompt(*, history: list[dict], passages: list[Passage], message: str) -> str:
    blocks = []
    blocks.append("=== PASSAGES ===")
    for p in passages:
        blocks.append(f"{_label(p)}\n{p.text}\n")
    blocks.append("=== END PASSAGES ===")
    if history:
        blocks.append("\nConversation so far (no passages):")
        for h in history:
            blocks.append(f"{h['role']}: {h['content']}")
    blocks.append(f"\nUser: {message}")
    return "\n".join(blocks)


async def stream_answer(
    session: Session, *, deal: Deal, history: list[dict], message: str,
    chat_llm: ChatLLM, rewrite_llm: RewriteLLM | None = None,
    k_per_query: int = 8, merge_top: int = 12,
) -> AsyncIterator[dict]:
    """Yields dict events: {'type':'token','text':...}, then 'citations', then 'done'."""
    if rewrite_llm is not None and history:
        queries = await rewrite_llm.rewrite(history=history, message=message)
    else:
        queries = [message]

    seen: dict[str, Passage] = {}
    for q in queries:
        for p in retrieve_passages(session, deal_id=deal.id, query=q, k=k_per_query):
            prev = seen.get(p.chunk_id)
            if prev is None or p.score > prev.score:
                seen[p.chunk_id] = p
    passages = sorted(seen.values(), key=lambda p: p.score, reverse=True)[:merge_top]

    system = build_system_prompt(deal=deal)
    user_prompt = build_user_prompt(history=history, passages=passages, message=message)
    messages = [{"role": "user", "content": user_prompt}]

    async for tok in chat_llm.stream(system=system, messages=messages):
        yield {"type": "token", "text": tok}

    yield {
        "type": "citations",
        "citations": [
            {
                "chunk_id": p.chunk_id, "document_id": p.document_id,
                "filename": p.filename, "page_from": p.page_from, "page_to": p.page_to,
                "sheet_name": p.sheet_name, "score": p.score,
            }
            for p in passages
        ],
    }
    yield {"type": "done"}


def build_library_system_prompt() -> str:
    return (
        "You are a senior PE research analyst answering questions about "
        "Pallisade-generated investment memos. Ground every claim in the passages "
        "provided. If the passages don't contain the answer, say so in one short "
        "sentence and stop. Cite each passage you use inline at the end of the "
        "sentence using [{ticker} · {kind}]. Never invent numbers."
    )


def _library_label(p: LibraryPassage) -> str:
    return f"[{p.ticker} · {p.kind}]"


def build_library_user_prompt(
    *, history: list[dict], passages: list[LibraryPassage], message: str
) -> str:
    blocks = []
    blocks.append("=== PASSAGES ===")
    for p in passages:
        blocks.append(f"{_library_label(p)}\n{p.text}\n")
    blocks.append("=== END PASSAGES ===")
    if history:
        blocks.append("\nConversation so far (no passages):")
        for h in history:
            blocks.append(f"{h['role']}: {h['content']}")
    blocks.append(f"\nUser: {message}")
    return "\n".join(blocks)


async def stream_answer_for_library(
    session: Session, *, history: list[dict], message: str,
    chat_llm: ChatLLM,
    library_doc_id: "uuid.UUID | None" = None,
    mentioned_doc_ids: "tuple[uuid.UUID, ...] | list[uuid.UUID]" = (),
    rewrite_llm: RewriteLLM | None = None,
    k_per_query: int = 6, merge_top: int = 10,
) -> AsyncIterator[dict]:
    """Yields dict events: {'type':'token','text':...}, then 'citations', then 'done'.

    If library_doc_id is given, retrieves only from that document's chunks.
    Otherwise falls back to global retrieval (optionally filtered by mentioned_doc_ids).
    """
    if rewrite_llm is not None and history:
        queries = await rewrite_llm.rewrite(history=history, message=message)
    else:
        queries = [message]

    seen: dict[str, LibraryPassage] = {}
    for q in queries:
        if library_doc_id is not None:
            results = retrieve_for_library_doc(session, library_doc_id=library_doc_id, query=q, k=k_per_query)
        else:
            results = retrieve_for_global(
                session, query=q, k=k_per_query,
                mentioned_doc_ids=list(mentioned_doc_ids) or None,
            )
        for p in results:
            prev = seen.get(p.chunk_id)
            if prev is None or p.score > prev.score:
                seen[p.chunk_id] = p

    passages = sorted(seen.values(), key=lambda p: p.score, reverse=True)[:merge_top]

    system = build_library_system_prompt()
    user_prompt = build_library_user_prompt(history=history, passages=passages, message=message)
    messages = [{"role": "user", "content": user_prompt}]

    async for tok in chat_llm.stream(system=system, messages=messages):
        yield {"type": "token", "text": tok}

    yield {
        "type": "citations",
        "citations": [
            {
                "chunk_id": p.chunk_id,
                "library_doc_id": p.library_doc_id,
                "kind": p.kind,
                "ticker": p.ticker,
                "title": p.title,
                "score": p.score,
            }
            for p in passages
        ],
    }
    yield {"type": "done"}


# --- Production adapters ---------------------------------------------------

class AnthropicChatLLM:
    """langchain-anthropic-backed implementation."""

    def __init__(self, *, api_key: str, model: str):
        from langchain_anthropic import ChatAnthropic
        self._llm = ChatAnthropic(model=model, api_key=api_key, streaming=True, max_tokens=2048)

    async def stream(self, *, system: str, messages: list[dict]) -> AsyncIterator[str]:
        from langchain_core.messages import HumanMessage, SystemMessage
        lc_messages = [SystemMessage(content=system)]
        for m in messages:
            lc_messages.append(HumanMessage(content=m["content"]))
        async for chunk in self._llm.astream(lc_messages):
            text = getattr(chunk, "content", "")
            if isinstance(text, list):
                for part in text:
                    if isinstance(part, dict) and part.get("type") == "text":
                        yield part.get("text", "")
            elif text:
                yield text


class AnthropicRewriteLLM:
    """Cheap Haiku-backed query rewriter returning 1-3 standalone search queries."""

    def __init__(self, *, api_key: str, model: str):
        from anthropic import AsyncAnthropic
        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model

    async def rewrite(self, *, history: list[dict], message: str) -> list[str]:
        import json
        recent = history[-6:]
        convo = "\n".join(f"{h['role']}: {h['content']}" for h in recent)
        prompt = (
            "Given this conversation and the user's latest message, output 1-3 "
            "standalone search queries (no pronouns, self-contained) that should "
            "be used to retrieve passages from a document store. Return JSON "
            "{\"queries\": [\"...\", ...]} only.\n\n"
            f"Conversation:\n{convo}\n\nUser: {message}"
        )
        msg = await self._client.messages.create(
            model=self._model, max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(getattr(b, "text", "") for b in msg.content)
        try:
            data = json.loads(text)
            queries = data.get("queries") or []
        except Exception:                              # noqa: BLE001
            queries = [message]
        if not queries:
            queries = [message]
        return queries[:3]
