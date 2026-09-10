"""Password hashing + JWT issuance/verification.

Self-contained local identity provider with **no native dependencies**: JWT via PyJWT (HS256,
stdlib ``hmac``) and password hashing via stdlib :func:`hashlib.scrypt`. To swap in
OIDC/Auth0/Keycloak, replace :func:`decode_token` with JWKS validation of the IdP's tokens;
nothing else in the app depends on the mechanism. See docs/auth.md.
"""
from __future__ import annotations

import hashlib
import hmac
import os
from datetime import UTC, datetime, timedelta

import jwt
from pydantic import BaseModel

from app.core.config import settings

ROLES = ("admin", "analyst", "viewer")
ROLE_CAPS: dict[str, set[str]] = {
    "admin": {"scan:start", "scan:cancel", "settings:write", "report:generate", "read"},
    "analyst": {"scan:start", "scan:cancel", "report:generate", "read"},
    "viewer": {"read"},
}

_SCRYPT_N, _SCRYPT_R, _SCRYPT_P, _DKLEN = 2**14, 8, 1, 32


class TokenPayload(BaseModel):
    sub: str
    email: str
    role: str
    org_id: str
    type: str  # "access" | "refresh"
    exp: int


def hash_password(raw: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.scrypt(raw.encode(), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=_DKLEN)
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${salt.hex()}${dk.hex()}"


def verify_password(raw: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt_hex, dk_hex = stored.split("$")
        if scheme != "scrypt":
            return False
        dk = hashlib.scrypt(
            raw.encode(), salt=bytes.fromhex(salt_hex),
            n=int(n), r=int(r), p=int(p), dklen=len(dk_hex) // 2,
        )
        return hmac.compare_digest(dk.hex(), dk_hex)
    except (ValueError, AttributeError):
        return False


def _make_token(*, sub: str, email: str, role: str, org_id: str, kind: str, ttl_min: int) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": sub, "email": email, "role": role, "org_id": org_id, "type": kind,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ttl_min)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(*, sub: str, email: str, role: str, org_id: str) -> str:
    return _make_token(sub=sub, email=email, role=role, org_id=org_id,
                       kind="access", ttl_min=settings.jwt_access_ttl_minutes)


def create_refresh_token(*, sub: str, email: str, role: str, org_id: str) -> str:
    return _make_token(sub=sub, email=email, role=role, org_id=org_id,
                       kind="refresh", ttl_min=settings.jwt_refresh_ttl_minutes)


def decode_token(token: str) -> TokenPayload | None:
    try:
        raw = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return TokenPayload(**raw)
    except (jwt.PyJWTError, ValueError, TypeError):
        return None
