from __future__ import annotations

from pallisade_core.auth.hashing import hash_password, verify_password


def test_hash_and_verify():
    h = hash_password("hunter2-correcthorse")
    assert h.startswith("$2") and len(h) > 20
    assert verify_password("hunter2-correcthorse", h) is True
    assert verify_password("wrong", h) is False


def test_hash_is_salted():
    a = hash_password("same")
    b = hash_password("same")
    assert a != b
