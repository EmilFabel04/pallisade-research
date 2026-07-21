import pytest

from pallisade_core.rag.embeddings import Embedder, FakeEmbedder, embed_documents, embed_query


def test_fake_embedder_returns_correct_dim():
    e = FakeEmbedder(dim=1024)
    out = e.embed(["alpha", "beta"], input_type="document")
    assert len(out) == 2
    assert all(len(v) == 1024 for v in out)


def test_fake_embedder_is_deterministic_for_same_text():
    e = FakeEmbedder(dim=64)
    a = e.embed(["hello"], input_type="document")[0]
    b = e.embed(["hello"], input_type="document")[0]
    assert a == b


def test_fake_embedder_differs_between_input_types():
    e = FakeEmbedder(dim=64)
    doc = e.embed(["hello"], input_type="document")[0]
    qry = e.embed(["hello"], input_type="query")[0]
    assert doc != qry


def test_embed_documents_and_embed_query_route_correctly():
    e = FakeEmbedder(dim=32)
    docs = embed_documents(["a", "b"], embedder=e)
    qry = embed_query("a", embedder=e)
    assert len(docs) == 2 and len(qry) == 32


def test_protocol_isinstance_check():
    assert isinstance(FakeEmbedder(dim=8), Embedder)
