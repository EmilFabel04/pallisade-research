from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from pallisade_core.settings import get_settings

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(get_settings().database_url, pool_pre_ping=True, future=True)
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), expire_on_commit=False, autoflush=False, future=True)
    return _SessionLocal


def reset_engine_for_tests(url: str) -> Engine:
    """Reset the cached engine to one pointed at `url`. Test-only."""
    global _engine, _SessionLocal
    _engine = create_engine(url, pool_pre_ping=True, future=True)
    _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False, autoflush=False, future=True)
    return _engine


def db_session() -> Iterator[Session]:
    """FastAPI dependency: yields a session, closes on exit."""
    factory = get_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()
