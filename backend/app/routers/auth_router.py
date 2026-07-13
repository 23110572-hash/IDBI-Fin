"""Auth endpoints — user registration + OAuth2 password login, issuing HS256 JWTs. Users are
stored in the database and created through Sign Up (no built-in accounts)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from ..auth import authenticate, create_access_token, create_user, current_user
from ..schemas import RegisterRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest):
    try:
        user = create_user(req.username, req.password, req.role)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None
    token, expires_in = create_access_token(user["username"], user["role"])
    return TokenResponse(access_token=token, role=user["role"], expires_in=expires_in)


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
