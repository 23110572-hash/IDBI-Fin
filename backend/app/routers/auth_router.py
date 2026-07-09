"""Auth endpoints — OAuth2 password flow (local Cognito stand-in)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from ..auth import authenticate, create_access_token, current_user
from ..schemas import TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(form: OAuth2PasswordRequestForm = Depends()):
    user = authenticate(form.username, form.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Incorrect username or password")
    token, expires_in = create_access_token(user["username"], user["role"])
    return TokenResponse(access_token=token, role=user["role"], expires_in=expires_in)


@router.get("/me")
async def me(user: dict = Depends(current_user)):
    return user
