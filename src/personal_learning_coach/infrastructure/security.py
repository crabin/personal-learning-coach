"""API authentication helpers."""

from __future__ import annotations

import logging
import secrets
from datetime import UTC, datetime, timedelta
from hashlib import pbkdf2_hmac, sha256
from typing import Annotated

from fastapi import Depends, Header, HTTPException

from personal_learning_coach.infrastructure import data_store
from personal_learning_coach.infrastructure.config import load_config
from personal_learning_coach.domain.models import AuthSession, UserProfile, UserRole
from personal_learning_coach.infrastructure.monitoring import record_runtime_event

logger = logging.getLogger(__name__)
SESSION_TTL_DAYS = 14
PASSWORD_ITERATIONS = 210_000


def _reject(message: str) -> None:
    logger.warning(message)
    record_runtime_event(level="warning", category="auth", message=message)
    raise HTTPException(status_code=401, detail="Invalid or missing API key")


def require_admin_read(x_api_key: str | None = Header(default=None)) -> None:
    config = load_config()
    expected = config.admin_read_token or config.api_auth_token
    if not expected:
        return
    if x_api_key != expected and x_api_key != config.admin_write_token:
        _reject("Rejected admin read request due to invalid API key")


def require_admin_write(x_api_key: str | None = Header(default=None)) -> None:
    config = load_config()
    expected = config.admin_write_token or config.api_auth_token or config.admin_read_token
    if not expected:
        return
    if x_api_key != expected:
        _reject("Rejected admin write request due to invalid API key")


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_password(password: str, salt: str | None = None) -> str:
    actual_salt = salt or secrets.token_hex(16)
    digest = pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        actual_salt.encode("utf-8"),
        PASSWORD_ITERATIONS,
    ).hex()
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${actual_salt}${digest}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        scheme, iterations, salt, expected = stored_hash.split("$", 3)
    except ValueError:
        return False
    if scheme != "pbkdf2_sha256":
        return False
    digest = pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        int(iterations),
    ).hex()
    return secrets.compare_digest(digest, expected)


def create_session(user_id: str) -> tuple[str, AuthSession]:
    token = secrets.token_urlsafe(32)
    session = AuthSession(
        user_id=user_id,
        token_hash=_hash_token(token),
        expires_at=datetime.now(UTC) + timedelta(days=SESSION_TTL_DAYS),
    )
    data_store.auth_sessions.save(session)
    return token, session


def revoke_session(token: str) -> None:
    session = _session_from_token(token)
    if session is None:
        return
    session.revoked_at = datetime.now(UTC)
    data_store.auth_sessions.save(session)


def find_user_by_email(email: str) -> UserProfile | None:
    normalized = normalize_email(email)
    for profile in data_store.user_profiles.all():
        if normalize_email(profile.email) == normalized:
            return profile
    return None


def seed_admin_from_environment() -> None:
    config = load_config()
    if not config.admin_seed_email or not config.admin_seed_password:
        return
    if find_user_by_email(config.admin_seed_email) is not None:
        return
    profile = UserProfile(
        name=config.admin_seed_name,
        email=normalize_email(config.admin_seed_email),
        password_hash=hash_password(config.admin_seed_password),
        role=UserRole.ADMIN,
    )
    data_store.user_profiles.save(profile)


def require_current_user(
    authorization: Annotated[str | None, Header()] = None,
) -> UserProfile:
    user = user_from_authorization(authorization)
    if user is None:
        raise HTTPException(status_code=401, detail="Login required")
    return user


def user_from_authorization(authorization: str | None) -> UserProfile | None:
    token = _bearer_token(authorization)
    if token is None:
        return None
    session = _session_from_token(token)
    if session is None or session.revoked_at is not None:
        return None
    if session.expires_at <= datetime.now(UTC):
        return None
    user = data_store.user_profiles.get(session.user_id)
    if user is None or not user.is_active:
        return None
    return user


def require_admin_user(
    current_user: Annotated[UserProfile, Depends(require_current_user)],
) -> UserProfile:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin role required")
    return current_user


def authorize_user_scope(requested_user_id: str, current_user: UserProfile) -> None:
    if current_user.role == UserRole.ADMIN:
        return
    if requested_user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Cannot access another user's data")


def optional_api_key_admin_write(x_api_key: str | None) -> bool:
    config = load_config()
    expected = config.admin_write_token or config.api_auth_token or config.admin_read_token
    return bool(expected and x_api_key == expected)


def optional_api_key_admin_read(x_api_key: str | None) -> bool:
    config = load_config()
    expected = config.admin_read_token or config.api_auth_token
    return bool(expected and (x_api_key == expected or x_api_key == config.admin_write_token))


def _hash_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


def _session_from_token(token: str) -> AuthSession | None:
    token_hash = _hash_token(token)
    for session in data_store.auth_sessions.filter(token_hash=token_hash):
        return session
    return None


def _bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()
