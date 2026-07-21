from __future__ import annotations

from collections.abc import Generator

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from pallisade_core.auth.sessions import SESSION_COOKIE_NAME, read_session_token
from pallisade_core.db.session import db_session
from pallisade_core.users import service as users_service
from pallisade_core.users.models import User

# Login has been disabled: every request resolves to a default account so the
# app is usable without authentication. A valid session cookie is still honored
# when present (so a real login keeps working), but its absence is no longer an
# error — we fall back to the default user below.
_DEFAULT_EMAIL = "demo@pallisade.local"
_DEFAULT_NAME = "Demo"


def get_db() -> Generator[Session, None, None]:
    yield from db_session()


def _default_user(db: Session) -> User:
    """Return a stable account to act as, creating one if the table is empty."""
    user = users_service.find_by_email(db, _DEFAULT_EMAIL)
    if user is None:
        user = db.execute(select(User).order_by(User.created_at)).scalars().first()
    if user is None:
        user = users_service.create_user(
            db,
            email=_DEFAULT_EMAIL,
            name=_DEFAULT_NAME,
            role="admin",
            password="login-disabled",
            must_change_password=False,
        )
        db.commit()
    return user


def get_current_user(
    db: Session = Depends(get_db),
    session_cookie: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> User:
    if session_cookie:
        user_id = read_session_token(session_cookie)
        if user_id is not None:
            user = users_service.get_by_id(db, user_id)
            if user is not None:
                return user
    return _default_user(db)


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin only")
    return user
