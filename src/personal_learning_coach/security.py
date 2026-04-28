"""API authentication helpers."""

from __future__ import annotations

import logging

from fastapi import Header, HTTPException

from personal_learning_coach.config import load_config
from personal_learning_coach.monitoring import record_runtime_event

logger = logging.getLogger(__name__)


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
