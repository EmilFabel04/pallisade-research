from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PALLISADE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(
        default="postgresql+psycopg://pallisade:pallisade@localhost:5432/pallisade"
    )
    session_secret: str = Field(..., min_length=32)
    storage_backend: Literal["local", "s3", "gcs"] = "local"
    storage_root: str = "./var/storage"
    storage_signing_key: str = Field(..., min_length=32)
    env: Literal["dev", "prod"] = "dev"

    # Phase 2 — RAG / ingestion
    voyage_api_key: str = Field(..., min_length=1)
    anthropic_api_key: str = Field(..., min_length=1)
    embed_model: str = "voyage-3"
    embed_dim: int = 1024
    ocr_model: str = "claude-haiku-4-5-20251001"
    chat_model: str = "claude-sonnet-4-6"
    memo_check_model: str = "claude-sonnet-4-6"
    memo_stale_days: int = 30
    query_rewrite_model: str = "claude-haiku-4-5-20251001"
    ocr_concurrency: int = 4
    embed_concurrency: int = 2
    max_upload_mb: int = 100
    worker_poll_seconds: int = 2
    worker_heartbeat_seconds: int = 10

    # Phase 3 — PE pipeline
    pe_analyst_model: str = "claude-sonnet-4-6"
    pe_decision_model: str = "claude-opus-4-7"
    pe_max_debate_rounds: int = 2
    pe_analyst_top_k: int = 6
    pe_analyst_parallel: bool = True
    pe_max_run_seconds: int = 1800

    # Data connections — BYO API keys (Fernet key, urlsafe base64, 44 chars)
    connections_enc_key: str | None = None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
