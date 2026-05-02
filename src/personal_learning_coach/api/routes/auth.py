"""User registration and session routes."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field, field_validator

from personal_learning_coach import data_store
from personal_learning_coach.email_sender import (
    EmailConfigurationError,
    EmailDeliveryError,
    send_registration_email_code,
)
from personal_learning_coach.models import (
    RegistrationCaptchaChallenge,
    RegistrationEmailChallenge,
    UserProfile,
)
from personal_learning_coach.registration_verification import (
    CAPTCHA_TTL_SECONDS,
    EMAIL_CODE_TTL_SECONDS,
    MAX_VERIFICATION_ATTEMPTS,
    generate_captcha_code,
    generate_email_code,
    hash_verification_code,
    is_expired,
    render_captcha_data_url,
    verification_code_matches,
)
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


class RegisterCaptchaResponse(BaseModel):
    captcha_id: str
    image_data_url: str
    expires_in_seconds: int


class RegisterStartRequest(RegisterRequest):
    captcha_id: str = Field(min_length=1)
    captcha_code: str = Field(min_length=1, max_length=16)


class RegisterStartResponse(BaseModel):
    verification_id: str
    email: str
    expires_in_seconds: int


class RegisterCompleteRequest(BaseModel):
    verification_id: str = Field(min_length=1)
    email_code: str = Field(min_length=1, max_length=16)


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


@router.get("/register/captcha", response_model=RegisterCaptchaResponse)
def create_register_captcha() -> RegisterCaptchaResponse:
    code = generate_captcha_code()
    challenge = RegistrationCaptchaChallenge(
        code_hash=hash_verification_code(code),
        expires_at=datetime.now(UTC) + timedelta(seconds=CAPTCHA_TTL_SECONDS),
    )
    data_store.registration_captcha_challenges.save(challenge)
    return RegisterCaptchaResponse(
        captcha_id=challenge.captcha_id,
        image_data_url=render_captcha_data_url(code),
        expires_in_seconds=CAPTCHA_TTL_SECONDS,
    )


@router.post("/register/start", response_model=RegisterStartResponse)
def start_register(body: RegisterStartRequest) -> RegisterStartResponse:
    _verify_captcha(body.captcha_id, body.captcha_code)
    email = normalize_email(body.email)
    if find_user_by_email(email) is not None:
        raise HTTPException(status_code=409, detail="Email already registered")

    email_code = generate_email_code()
    try:
        send_registration_email_code(email, email_code)
    except EmailConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except EmailDeliveryError as exc:
        raise HTTPException(status_code=503, detail="Failed to send verification email") from exc

    challenge = RegistrationEmailChallenge(
        name=body.name.strip(),
        email=email,
        password_hash=hash_password(body.password),
        code_hash=hash_verification_code(email_code),
        expires_at=datetime.now(UTC) + timedelta(seconds=EMAIL_CODE_TTL_SECONDS),
    )
    data_store.registration_email_challenges.save(challenge)
    return RegisterStartResponse(
        verification_id=challenge.verification_id,
        email=email,
        expires_in_seconds=EMAIL_CODE_TTL_SECONDS,
    )


@router.post("/register/complete", response_model=AuthResponse)
def complete_register(body: RegisterCompleteRequest) -> AuthResponse:
    challenge = data_store.registration_email_challenges.get(body.verification_id)
    if challenge is None:
        raise HTTPException(status_code=400, detail="Invalid or expired email verification code")
    if _challenge_unusable(challenge.expires_at, challenge.attempts):
        data_store.registration_email_challenges.delete(challenge.verification_id)
        raise HTTPException(status_code=400, detail="Invalid or expired email verification code")
    if not verification_code_matches(body.email_code, challenge.code_hash):
        challenge.attempts += 1
        data_store.registration_email_challenges.save(challenge)
        raise HTTPException(status_code=400, detail="Invalid or expired email verification code")
    if find_user_by_email(challenge.email) is not None:
        data_store.registration_email_challenges.delete(challenge.verification_id)
        raise HTTPException(status_code=409, detail="Email already registered")

    user = UserProfile(
        name=challenge.name,
        email=challenge.email,
        password_hash=challenge.password_hash,
    )
    data_store.user_profiles.save(user)
    data_store.registration_email_challenges.delete(challenge.verification_id)
    token, _ = create_session(user.user_id)
    return AuthResponse(token=token, user=_user_response(user))


@router.post("/register", response_model=AuthResponse)
def register(_: RegisterRequest) -> AuthResponse:
    raise HTTPException(status_code=410, detail="Use /auth/register/start and /auth/register/complete")


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


def _verify_captcha(captcha_id: str, captcha_code: str) -> None:
    challenge = data_store.registration_captcha_challenges.get(captcha_id)
    if challenge is None:
        raise HTTPException(status_code=400, detail="Invalid or expired captcha")
    if _challenge_unusable(challenge.expires_at, challenge.attempts):
        data_store.registration_captcha_challenges.delete(challenge.captcha_id)
        raise HTTPException(status_code=400, detail="Invalid or expired captcha")
    if not verification_code_matches(captcha_code, challenge.code_hash):
        challenge.attempts += 1
        data_store.registration_captcha_challenges.save(challenge)
        raise HTTPException(status_code=400, detail="Invalid or expired captcha")
    data_store.registration_captcha_challenges.delete(challenge.captcha_id)


def _challenge_unusable(expires_at: datetime, attempts: int) -> bool:
    return is_expired(expires_at) or attempts >= MAX_VERIFICATION_ATTEMPTS
