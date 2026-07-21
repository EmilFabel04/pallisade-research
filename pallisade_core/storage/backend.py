from __future__ import annotations

import hashlib
import hmac
import time
from typing import BinaryIO, Protocol, runtime_checkable

from pallisade_core.settings import get_settings


@runtime_checkable
class StorageBackend(Protocol):
    def put(self, key: str, data: BinaryIO, content_type: str) -> None: ...
    def get(self, key: str) -> BinaryIO: ...
    def delete(self, key: str) -> None: ...
    def list(self, prefix: str) -> list[str]: ...
    def signed_url(self, key: str, expires_in: int = 3600) -> str: ...


def sign_url_token(key: str, *, exp: int) -> str:
    msg = f"{key}:{exp}".encode("utf-8")
    secret = get_settings().storage_signing_key.encode("utf-8")
    return hmac.new(secret, msg, hashlib.sha256).hexdigest()


def verify_url_token(key: str, *, sig: str, exp: int) -> bool:
    if exp < int(time.time()):
        return False
    expected = sign_url_token(key, exp=exp)
    return hmac.compare_digest(expected, sig)
