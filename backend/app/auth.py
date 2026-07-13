"""Authentication & RBAC.

Mints/verifies HS256 JWTs. Roles: admin / credit_officer / rm. No secrets in code — the signing
key comes from settings (MSME_JWT_SECRET), with an ephemeral per-process fallback for dev.

Passwords use PBKDF2-HMAC-SHA256 (stdlib) to avoid native bcrypt build friction.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import os

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from .config import get_settings

_settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

_PBKDF2_ROUNDS = 120_000


def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ROUNDS)
    return f"{salt.hex()}${dk.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, dk_hex = stored.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), _PBKDF2_ROUNDS)
        return hmac.compare_digest(dk.hex(), dk_hex)
    except Exception:
        return False


ROLE_HIERARCHY = {"admin": 3, "credit_officer": 2, "rm": 1}
VALID_ROLES = tuple(ROLE_HIERARCHY)


def authenticate(username: str, password: str) -> dict | None:
    """Verify credentials against the users table."""
    from sqlalchemy import select

    from .db import session_scope
    from .models import User

    with session_scope() as s:
        user = s.execute(select(User).where(User.username == username)).scalar_one_or_none()
        if not user or not _verify_password(password, user.password_hash):
            return None
        return {"username": user.username, "role": user.role}


def create_user(username: str, password: str, role: str = "rm") -> dict:
    """Create a user. Raises ValueError on invalid input or a duplicate username."""
    from sqlalchemy import select

    from .db import session_scope
    from .models import User

    username = username.strip()
    if len(username) < 3:
        raise ValueError("Username must be at least 3 characters.")
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters.")
    if role not in ROLE_HIERARCHY:
        raise ValueError(f"Invalid role; choose one of: {', '.join(VALID_ROLES)}")

    with session_scope() as s:
        exists = s.execute(select(User).where(User.username == username)).scalar_one_or_none()
        if exists:
            raise ValueError("That username is already taken.")
        s.add(User(username=username, password_hash=_hash_password(password), role=role))
    return {"username": username, "role": role}


def create_access_token(username: str, role: str) -> tuple[str, int]:
    expires_in = _settings.jwt_expiry_minutes * 60
    now = dt.datetime.now(dt.UTC)
    payload = {"sub": username, "role": role, "iat": now,
               "exp": now + dt.timedelta(minutes=_settings.jwt_expiry_minutes)}
    token = jwt.encode(payload, _settings.effective_jwt_secret(), algorithm=_settings.jwt_algorithm)
    return token, expires_in


async def current_user(token: str | None = Depends(oauth2_scheme)) -> dict:
    if not _settings.auth_enabled:
        return {"username": "dev", "role": "admin"}
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated",
                            headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, _settings.effective_jwt_secret(),
                             algorithms=[_settings.jwt_algorithm])
        return {"username": payload.get("sub"), "role": payload.get("role", "rm")}
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token",
                            headers={"WWW-Authenticate": "Bearer"}) from None


def require_role(min_role: str):
    """Dependency factory enforcing a minimum role."""
    required = ROLE_HIERARCHY[min_role]

    async def _dep(user: dict = Depends(current_user)) -> dict:
        if ROLE_HIERARCHY.get(user["role"], 0) < required:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail=f"Requires role >= {min_role}")
        return user

    return _dep
