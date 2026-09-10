from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.core.security import (
    ROLE_CAPS,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.models.user import User
from app.schemas import LoginRequest, MeResponse, RefreshRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


def _issue(user: User) -> TokenResponse:
    kw = {"sub": user.user_id, "email": user.email, "role": user.role, "org_id": user.org_id}
    return TokenResponse(
        access_token=create_access_token(**kw),
        refresh_token=create_refresh_token(**kw),
        role=user.role,
        email=user.email,
    )


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User disabled")
    return _issue(user)


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    payload = decode_token(body.refresh_token)
    if payload is None or payload.type != "refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    user = db.get(User, payload.sub)
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return _issue(user)


@router.post("/logout")
def logout(_: User = Depends(get_current_user)) -> dict:
    # Stateless JWT: client discards tokens. A denylist/rotation store would go here.
    return {"detail": "Logged out. Discard your tokens."}


# Mounted at /api/v1/me (see router.py)
me_router = APIRouter(tags=["auth"])


@me_router.get("/me", response_model=MeResponse)
def me(user: User = Depends(get_current_user)) -> MeResponse:
    return MeResponse(
        user_id=user.user_id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        org_id=user.org_id,
        capabilities=sorted(ROLE_CAPS.get(user.role, set())),
    )
