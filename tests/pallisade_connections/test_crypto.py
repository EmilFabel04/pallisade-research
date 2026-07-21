from __future__ import annotations

import pytest

from pallisade_connections.crypto import EncryptionUnavailable, decrypt, encrypt


def test_round_trip(enc_key):
    token = encrypt("super-secret-api-key")
    assert token.startswith("v1:")
    assert token != "super-secret-api-key"
    assert decrypt(token) == "super-secret-api-key"


def test_missing_key_raises(monkeypatch):
    # Force the crypto module to see no configured key, independent of any
    # on-disk .env (pydantic reads env_file, so delenv alone can't neutralize it).
    from types import SimpleNamespace

    monkeypatch.setattr(
        "pallisade_connections.crypto.get_settings",
        lambda: SimpleNamespace(connections_enc_key=None),
    )
    with pytest.raises(EncryptionUnavailable):
        encrypt("x")
