from __future__ import annotations

import hashlib
import logging
from typing import Literal, Protocol, runtime_checkable

log = logging.getLogger(__name__)

InputType = Literal["document", "query"]


@runtime_checkable
class Embedder(Protocol):
    def embed(self, texts: list[str], *, input_type: InputType) -> list[list[float]]: ...


class FakeEmbedder:
    """Deterministic test embedder — hash → vector in [-1, 1].

    Different input_types yield different vectors for the same text, so tests
    catch accidental query/document collisions.
    """
    def __init__(self, *, dim: int):
        self.dim = dim

    def embed(self, texts: list[str], *, input_type: InputType) -> list[list[float]]:
        out: list[list[float]] = []
        for t in texts:
            seed = hashlib.sha256(f"{input_type}::{t}".encode("utf-8")).digest()
            # Stretch seed bytes deterministically to fill dim.
            vec: list[float] = []
            i = 0
            while len(vec) < self.dim:
                b = seed[i % len(seed)]
                vec.append((b / 127.5) - 1.0)
                i += 1
            out.append(vec[: self.dim])
        return out


class VoyageEmbedder:
    """Real-API embedder wrapping the voyageai client."""

    def __init__(self, *, api_key: str, model: str):
        import voyageai
        self._client = voyageai.Client(api_key=api_key)
        self._model = model

    def embed(self, texts: list[str], *, input_type: InputType) -> list[list[float]]:
        if not texts:
            return []
        resp = self._client.embed(texts, model=self._model, input_type=input_type)
        return list(resp.embeddings)


def embed_documents(texts: list[str], *, embedder: Embedder) -> list[list[float]]:
    return embedder.embed(texts, input_type="document")


def embed_query(text: str, *, embedder: Embedder) -> list[float]:
    return embedder.embed([text], input_type="query")[0]


def build_default_embedder() -> Embedder:
    """Lazy real-Voyage embedder factory (use from production code paths)."""
    from pallisade_core.settings import get_settings
    s = get_settings()
    return VoyageEmbedder(api_key=s.voyage_api_key, model=s.embed_model)
