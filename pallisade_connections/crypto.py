from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from pallisade_core.settings import get_settings

_PREFIX = "v1:"


class EncryptionUnavailable(Exception):
    """Raised when the connections encryption key is missing or invalid."""


def _fernet() -> Fernet:
    key = get_settings().connections_enc_key
    if not key:
        raise EncryptionUnavailable("connections encryption key not configured")
    try:
        return Fernet(key.encode())
    except (ValueError, TypeError) as exc:
        raise EncryptionUnavailable("connections encryption key is invalid") from exc


def encrypt(plaintext: str) -> str:
    token = _fernet().encrypt(plaintext.encode()).decode()
    return _PREFIX + token


def decrypt(token: str) -> str:
    if not token.startswith(_PREFIX):
        raise EncryptionUnavailable("unrecognized ciphertext format")
    try:
        return _fernet().decrypt(token[len(_PREFIX):].encode()).decode()
    except InvalidToken as exc:
        raise EncryptionUnavailable("ciphertext could not be decrypted") from exc
