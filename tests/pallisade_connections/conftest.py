from __future__ import annotations

import os

import pytest
from cryptography.fernet import Fernet

# Re-export the shared DB fixtures (_pg_container, database_url, _env,
# _migrate, db, make_user, make_library_document, client_for) so that
# tests in this package can depend on them without duplicating the setup.
#
# Import them explicitly rather than declaring `pytest_plugins`: pytest 8
# forbids `pytest_plugins` in a non-top-level conftest, which broke
# `pytest tests/` collection entirely. Explicit imports (a star-import skips
# the underscore-prefixed session fixtures) keep them scoped to this subtree.
from tests.pallisade.conftest import (  # noqa: F401,E402
    _pg_container,
    database_url,
    _env,
    _migrate,
    db,
    make_user,
    make_library_document,
    client_for,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture()
def enc_key(monkeypatch) -> str:
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("PALLISADE_CONNECTIONS_ENC_KEY", key)
    from pallisade_core import settings as settings_mod
    settings_mod.get_settings.cache_clear()
    yield key
    settings_mod.get_settings.cache_clear()
