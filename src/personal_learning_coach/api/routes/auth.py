"""User registration and session routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field, field_validator

from personal_learning_coach import data_store
from personal_learning_coach.models import UserProfile
from personal_learning_coach.security import (
    create_session,
    find_user_by_email,
    hash_password,
    normalize_email,
    require_current_user,
    revoke_session,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class AuthUserResponse(BaseModel):
    user_id: str
    name: str
    email: str
    role: str


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=256)

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        normalized = normalize_email(value)
        if "@" not in normalized:
            raise ValueError("Invalid email")
        return normalized


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        normalized = normalize_email(value)
        if "@" not in normalized:
            raise ValueError("Invalid email")
        return normalized


class AuthResponse(BaseModel):
    token: str
    user: AuthUserResponse


@router.post("/register", response_model=AuthResponse)
def register(body: RegisterRequest) -> AuthResponse:
    if find_user_by_email(body.email) is not None:
        raise HTTPException(status_code=409, detail="Email already registered")
    user = UserProfile(
        name=body.name.strip(),
        email=normalize_email(body.email),
        password_hash=hash_password(body.password),
    )
    data_store.user_profiles.save(user)
    token, _ = create_session(user.user_id)
    return AuthResponse(token=token, user=_user_response(user))


@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest) -> AuthResponse:
    user = find_user_by_email(body.email)
    if user is None or not user.is_active or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token, _ = create_session(user.user_id)
    return AuthResponse(token=token, user=_user_response(user))


@router.post("/logout")
def logout(authorization: Annotated[str | None, Header()] = None) -> dict[str, str]:
    if authorization:
        _, _, token = authorization.partition(" ")
        revoke_session(token.strip())
    return {"message": "Logged out."}


@router.get("/me", response_model=AuthUserResponse)
def me(current_user: Annotated[UserProfile, Depends(require_current_user)]) -> AuthUserResponse:
    return _user_response(current_user)


def _user_response(user: UserProfile) -> AuthUserResponse:
    return AuthUserResponse(
        user_id=user.user_id,
        name=user.name,
        email=user.email,
        role=user.role.value,
    )
