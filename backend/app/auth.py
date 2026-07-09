"""Authentication & RBAC.

In AWS this is AWS Cognito (OAuth2/JWT). Locally we mint/verify our own HS256 JWTs behind the same
interface so the app runs without live AWS. Roles: admin / credit_officer / rm. No secrets in code —
the signing key comes from settings (env), with an ephemeral per-process fallback for dev.

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


# Dev user store (local Cognito stand-in). Credentials overridable via env; documented in README.
# These are DEV-ONLY defaults for local sign-in, not production credentials.
def _dev_users() -> dict[str, dict]:
    creds = {
        "admin": (os.environ.get("MSME_ADMIN_PASSWORD", "admin123!"), "admin"),
        "officer": (os.environ.get("MSME_OFFICER_PASSWORD", "officer123!"), "credit_officer"),
        "rm": (os.environ.get("MSME_RM_PASSWORD", "rm123!"), "rm"),
    }
    return {u: {"role": role, "password_hash": _hash_password(pw)} for u, (pw, role) in creds.items()}


_USERS = _dev_users()

ROLE_HIERARCHY = {"admin": 3, "credit_officer": 2, "rm": 1}


def authenticate(username: str, password: str) -> dict | None:
    user = _USERS.get(username)
    if not user or not _verify_password(password, user["password_hash"]):
        return None
    return {"username": username, "role": user["role"]}


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
