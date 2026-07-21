from __future__ import annotations

import time
import uuid

from pallisade_core.auth import sessions


def test_round_trip():
    uid = uuid.uuid4()
    token = sessions.create_session_token(uid)
    out = sessions.read_session_token(token)
    assert out == uid


def test_tampered_token_rejected():
    uid = uuid.uuid4()
    token = sessions.create_session_token(uid)
    bad = token[:-2] + "xx"
    assert sessions.read_session_token(bad) is None


def test_expired_token_rejected():
    uid = uuid.uuid4()
    token = sessions.create_session_token(uid)
    time.sleep(2.1)
    assert sessions.read_session_token(token, max_age_seconds=1) is None
