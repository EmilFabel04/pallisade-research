from __future__ import annotations

import io
import time

import pytest

from pallisade_core.storage.backend import sign_url_token, verify_url_token
from pallisade_core.storage.local_disk import LocalDiskStorage


@pytest.fixture()
def storage(tmp_path):
    return LocalDiskStorage(root=str(tmp_path))


def test_put_get_delete(storage):
    storage.put("a/b/file.txt", io.BytesIO(b"hello"), content_type="text/plain")
    buf = storage.get("a/b/file.txt")
    assert buf.read() == b"hello"
    storage.delete("a/b/file.txt")
    with pytest.raises(FileNotFoundError):
        storage.get("a/b/file.txt")


def test_list_prefix(storage):
    for k in ["x/1.txt", "x/2.txt", "y/1.txt"]:
        storage.put(k, io.BytesIO(b"x"), content_type="text/plain")
    assert sorted(storage.list("x/")) == ["x/1.txt", "x/2.txt"]


def test_signed_url_round_trip(storage):
    storage.put("file.txt", io.BytesIO(b"d"), content_type="text/plain")
    url = storage.signed_url("file.txt", expires_in=60)
    assert url.startswith("/storage/file.txt?sig=") and "exp=" in url
    sig = url.split("sig=")[1].split("&")[0]
    exp = int(url.split("exp=")[1])
    assert verify_url_token("file.txt", sig=sig, exp=exp) is True


def test_signed_url_expired():
    sig = sign_url_token("file.txt", exp=int(time.time()) - 5)
    assert verify_url_token("file.txt", sig=sig, exp=int(time.time()) - 5) is False


def test_signed_url_tampered():
    exp = int(time.time()) + 60
    sig = sign_url_token("file.txt", exp=exp)
    assert verify_url_token("other.txt", sig=sig, exp=exp) is False


def test_traversal_blocked(storage):
    with pytest.raises(ValueError):
        storage.put("../escape.txt", io.BytesIO(b"x"), content_type="text/plain")
