from __future__ import annotations

import os
import uuid
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from testcontainers.postgres import PostgresContainer


@pytest.fixture(scope="session")
def _pg_container() -> Iterator[PostgresContainer]:
    with PostgresContainer("pgvector/pgvector:pg16") as pg:
        yield pg


@pytest.fixture(scope="session")
def database_url(_pg_container: PostgresContainer) -> str:
    raw = _pg_container.get_connection_url()  # postgresql+psycopg2://...
    return raw.replace("postgresql+psycopg2://", "postgresql+psycopg://")


@pytest.fixture(scope="session", autouse=True)
def _env(database_url, tmp_path_factory):
    base_dir = tmp_path_factory.mktemp("storage")
    # The storage root must end with "var/storage" so that test_settings
    # (which checks `s.storage_root.endswith("var/storage")`) still passes.
    storage_root = base_dir / "var" / "storage"
    storage_root.mkdir(parents=True, exist_ok=True)

    os.environ["PALLISADE_DATABASE_URL"] = database_url
    os.environ["PALLISADE_SESSION_SECRET"] = "test-session-secret-" + "x" * 32
    os.environ["PALLISADE_STORAGE_SIGNING_KEY"] = "test-signing-key-" + "y" * 32
    os.environ["PALLISADE_STORAGE_BACKEND"] = "local"
    os.environ["PALLISADE_STORAGE_ROOT"] = str(storage_root)
    os.environ["PALLISADE_ENV"] = "dev"
    os.environ["PALLISADE_VOYAGE_API_KEY"] = "test-voyage-key"
    os.environ["PALLISADE_ANTHROPIC_API_KEY"] = "test-anthropic-key"
    os.environ.setdefault("PALLISADE_FORESIGHT_FRED_API_KEY", "test-fred-key")
    os.environ.setdefault("PALLISADE_FORESIGHT_NEWS_API_KEY", "test-news-key")
    os.environ.setdefault("PALLISADE_FORESIGHT_SEC_CONTACT_EMAIL", "test@example.com")
    os.environ.setdefault("PALLISADE_FORESIGHT_LLM_PROVIDER", "anthropic")
    os.environ.setdefault("PALLISADE_FORESIGHT_LLM_MODEL", "claude-haiku-4-5")
    os.environ.setdefault("PALLISADE_FORESIGHT_LLM_DAILY_CAP", "10000")

    # Reset cached settings + engine
    from pallisade_core import settings as settings_mod
    settings_mod.get_settings.cache_clear()
    from pallisade_core.db import session as db_session_mod
    db_session_mod.reset_engine_for_tests(database_url)


@pytest.fixture(scope="session", autouse=True)
def _migrate(_env, database_url):
    from alembic import command
    from alembic.config import Config
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(cfg, "head")


@pytest.fixture(autouse=True)
def _reset_settings_cache_between_tests():
    yield
    from pallisade_core import settings as _settings_mod
    _settings_mod.get_settings.cache_clear()


@pytest.fixture()
def db(_migrate) -> Iterator[Session]:
    """Per-test session wrapped in a SAVEPOINT-rolled-back nested transaction."""
    from pallisade_core.db.session import get_engine
    engine = get_engine()
    connection = engine.connect()
    trans = connection.begin()
    SessionLocal = sessionmaker(bind=connection, expire_on_commit=False, autoflush=False, future=True)
    session = SessionLocal()
    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess, transaction):
        nonlocal nested
        if transaction.nested and not transaction._parent.nested:
            nested = connection.begin_nested()

    try:
        yield session
    finally:
        session.close()
        trans.rollback()
        connection.close()


@pytest.fixture()
def make_user(db):
    from pallisade_core.auth.hashing import hash_password
    from pallisade_core.users.models import User
    from pallisade_connections.models import default_org_id

    def _make(*, email: str | None = None, name: str = "Test User", role: str = "member",
              password: str = "TestPass!12345", must_change: bool = False) -> User:
        u = User(
            email=email or f"u{uuid.uuid4().hex[:8]}@example.com",
            name=name,
            role=role,
            password_hash=hash_password(password),
            must_change_password=must_change,
            org_id=default_org_id(db),
        )
        db.add(u)
        db.flush()
        return u

    return _make


@pytest.fixture()
def make_library_document(db, make_user):
    import uuid
    from pallisade_core.library.models import LibraryDocument
    from pallisade_core.runs.models import EvaluationRun

    def _make(*, ticker: str = "TEST.JO", kind: str = "final_trade_decision",
              title: str | None = None, body_md: str = "Dummy report body.") -> LibraryDocument:
        owner = make_user()
        run = EvaluationRun(
            mode="public",
            user_id=owner.id,
            ticker=ticker,
            status="done",
        )
        db.add(run)
        db.flush()
        doc = LibraryDocument(
            run_id=run.id,
            ticker=ticker,
            kind=kind,
            title=title or f"{ticker} — {kind}",
            body_md=body_md,
        )
        db.add(doc)
        db.flush()
        return doc

    return _make


@pytest.fixture()
def session_factory_for_db(db):
    """A session factory that yields the TEST session.

    Production code under test opens its own sessions via a factory (spec §5.2).
    A real factory would open a new connection, which cannot see this test's
    uncommitted SAVEPOINT rows — so tests inject this instead.
    """
    from contextlib import contextmanager

    @contextmanager
    def _ctx():
        yield db

    class _Factory:
        def __call__(self):
            return _ctx()

    return _Factory()


@pytest.fixture()
def client_for(db):
    """Builds an httpx AsyncClient bound to an app, with DB-session override."""
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient
    from web.api.deps import get_db

    def _build(routers_with_prefix: list[tuple[str, object]]):
        app = FastAPI()
        for prefix, r in routers_with_prefix:
            app.include_router(r, prefix=prefix)

        def _override_db():
            yield db

        app.dependency_overrides[get_db] = _override_db
        return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    return _build
