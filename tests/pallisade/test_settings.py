from __future__ import annotations

import pytest


def test_settings_loads_required_vars(monkeypatch):
    from pallisade_core.settings import Settings

    monkeypatch.setenv("PALLISADE_DATABASE_URL", "postgresql+psycopg://u:p@h/d")
    monkeypatch.setenv("PALLISADE_SESSION_SECRET", "x" * 32)
    monkeypatch.setenv("PALLISADE_STORAGE_SIGNING_KEY", "y" * 32)

    s = Settings()
    assert s.database_url == "postgresql+psycopg://u:p@h/d"
    assert s.session_secret == "x" * 32
    assert s.storage_signing_key == "y" * 32
    assert s.storage_backend == "local"
    assert s.storage_root.endswith("var/storage")
    assert s.env == "dev"


def test_settings_missing_secret_fails(monkeypatch):
    from pallisade_core.settings import Settings

    monkeypatch.delenv("PALLISADE_SESSION_SECRET", raising=False)
    monkeypatch.delenv("PALLISADE_STORAGE_SIGNING_KEY", raising=False)
    monkeypatch.setenv("PALLISADE_DATABASE_URL", "postgresql+psycopg://u:p@h/d")
    with pytest.raises(Exception):
        Settings()


def test_phase2_settings_have_expected_defaults(monkeypatch):
    monkeypatch.setenv("PALLISADE_SESSION_SECRET", "x" * 40)
    monkeypatch.setenv("PALLISADE_STORAGE_SIGNING_KEY", "y" * 40)
    monkeypatch.setenv("PALLISADE_VOYAGE_API_KEY", "vo-test")
    monkeypatch.setenv("PALLISADE_ANTHROPIC_API_KEY", "sk-test")

    from pallisade_core.settings import Settings
    s = Settings()
    assert s.voyage_api_key == "vo-test"
    assert s.anthropic_api_key == "sk-test"
    assert s.embed_model == "voyage-3"
    assert s.embed_dim == 1024
    assert s.ocr_model.startswith("claude-")
    assert s.chat_model.startswith("claude-")
    assert s.query_rewrite_model.startswith("claude-")
    assert s.ocr_concurrency == 4
    assert s.embed_concurrency == 2
    assert s.max_upload_mb == 100
    assert s.worker_poll_seconds == 2
    assert s.worker_heartbeat_seconds == 10


def test_phase3_settings_have_expected_defaults(monkeypatch):
    monkeypatch.setenv("PALLISADE_VOYAGE_API_KEY", "x")
    monkeypatch.setenv("PALLISADE_ANTHROPIC_API_KEY", "x")
    monkeypatch.setenv("PALLISADE_SESSION_SECRET", "a" * 32)
    monkeypatch.setenv("PALLISADE_STORAGE_SIGNING_KEY", "b" * 32)
    from pallisade_core.settings import Settings
    s = Settings()
    assert s.pe_analyst_model == "claude-sonnet-4-6"
    assert s.pe_decision_model == "claude-opus-4-7"
    assert s.pe_max_debate_rounds == 2
    assert s.pe_analyst_top_k == 6
    assert s.pe_analyst_parallel is True
    assert s.pe_max_run_seconds == 1800
