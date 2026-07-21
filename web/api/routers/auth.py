from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from pallisade_core.auth.hashing import verify_password
from pallisade_core.auth.sessions import (
    SESSION_COOKIE_NAME,
    cookie_attrs,
    create_session_token,
)
from pallisade_core.users import service as users_service
from pallisade_core.users.models import User
from web.api.deps import get_current_user, get_db

router = APIRouter(tags=["auth"])


class LoginBody(BaseModel):
    email: str
    password: str = Field(..., min_length=1)


class ChangePasswordBody(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=12)


class UserOut(BaseModel):
    id: str
    email: str
    name: str
    role: str
    must_change_password: bool

    @classmethod
    def from_model(cls, u: User) -> "UserOut":
        return cls(
            id=str(u.id), email=u.email, name=u.name,
            role=u.role, must_change_password=u.must_change_password,
        )


@router.post("/login", response_model=UserOut)
def login(body: LoginBody, response: Response, db: Session = Depends(get_db)) -> UserOut:
    user = users_service.verify_credentials(db, body.email, body.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")
    user.last_login_at = datetime.now(timezone.utc)
    db.add(user)
    db.commit()
    token = create_session_token(user.id)
    response.set_cookie(SESSION_COOKIE_NAME, token, **cookie_attrs())
    return UserOut.from_model(user)


@router.post("/logout", status_code=204)
def logout(response: Response) -> Response:
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    response.status_code = 204
    return response


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.from_model(user)


@router.post("/change-password", status_code=204)
def change_password(
    body: ChangePasswordBody,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="current password incorrect")
    users_service.set_password(db, user, body.new_password)
    db.commit()
    return Response(status_code=204)
