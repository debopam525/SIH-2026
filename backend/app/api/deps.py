"""Auth / RBAC dependencies. RBAC is enforced here (server-side), not just hidden in the UI."""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import ROLE_CAPS, TokenPayload, decode_token
from app.models.user import User

_bearer = HTTPBearer(auto_error=False)


def get_current_payload(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> TokenPayload:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    payload = decode_token(creds.credentials)
    if payload is None or payload.type != "access":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    return payload


def get_current_user(
    payload: TokenPayload = Depends(get_current_payload),
    db: Session = Depends(get_db),
) -> User:
    user = db.get(User, payload.sub)
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found or inactive")
    return user


def require_cap(capability: str):
    def _dep(user: User = Depends(get_current_user)) -> User:
        caps = ROLE_CAPS.get(user.role, set())
        if capability not in caps:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"Role '{user.role}' lacks capability '{capability}'",
            )
        return user

    return _dep
