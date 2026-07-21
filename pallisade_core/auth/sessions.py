from __future__ import annotations

import uuid
from typing import Final

from itsdangerous import BadSignature, SignatureExpired, TimestampSigner

from pallisade_core.settings import get_settings

SESSION_COOKIE_NAME: Final = "pallisade_session"
SESSION_MAX_AGE_SECONDS: Final = 60 * 60 * 24 * 7  # 7 days


def _signer() -> TimestampSigner:
    return TimestampSigner(get_settings().session_secret, salt="pallisade.session.v1")


def create_session_token(user_id: uuid.UUID) -> str:
    return _signer().sign(str(user_id)).decode("utf-8")


def read_session_token(token: str, max_age_seconds: int = SESSION_MAX_AGE_SECONDS) -> uuid.UUID | None:
    try:
        raw = _signer().unsign(token, max_age=max_age_seconds).decode("utf-8")
        return uuid.UUID(raw)
    except (BadSignature, SignatureExpired, ValueError):
        return None


def cookie_attrs() -> dict:
    secure = get_settings().env != "dev"
    return {
        "httponly": True,
        "secure": secure,
        "samesite": "lax",
        "max_age": SESSION_MAX_AGE_SECONDS,
        "path": "/",
    }
