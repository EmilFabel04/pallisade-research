from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from pallisade_core.auth.hashing import hash_password, verify_password
from pallisade_core.users.models import User


def create_user(
    session: Session,
    *,
    email: str,
    name: str,
    role: str,
    password: str,
    must_change_password: bool = True,
) -> User:
    from pallisade_connections.models import default_org_id
    org_id = default_org_id(session)

    user = User(
        email=email.strip().lower(),
        name=name.strip(),
        role=role,
        password_hash=hash_password(password),
        must_change_password=must_change_password,
        org_id=org_id,
    )
    session.add(user)
    return user


def find_by_email(session: Session, email: str) -> User | None:
    stmt = select(User).where(User.email == email.strip().lower())
    return session.execute(stmt).scalar_one_or_none()


def get_by_id(session: Session, user_id) -> User | None:
    return session.get(User, user_id)


def set_password(session: Session, user: User, new_password: str) -> None:
    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    session.add(user)


def verify_credentials(session: Session, email: str, password: str) -> User | None:
    user = find_by_email(session, email)
    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def count_users(session: Session) -> int:
    return session.query(User).count()
