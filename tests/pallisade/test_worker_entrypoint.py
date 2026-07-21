from pallisade_worker.__main__ import build_handlers


def test_build_handlers_includes_parse_and_embed():
    handlers = build_handlers()
    assert {"parse_document", "embed_document"} <= set(handlers.keys())
    assert callable(handlers["parse_document"])
    assert callable(handlers["embed_document"])
