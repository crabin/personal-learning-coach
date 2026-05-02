"""Runtime configuration loading and validation."""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, ValidationError, field_validator


class AppConfig(BaseModel):
    data_dir: Path = Path("./data")
    delivery_mode: str = "local"
    openai_api_key: str = ""
    openai_model: str = "gpt-4.5"
    openai_base_url: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    api_auth_token: str = ""
    admin_read_token: str = ""
    admin_write_token: str = ""
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    api_reload: bool = False
    admin_seed_email: str = ""
    admin_seed_password: str = ""
    admin_seed_name: str = "System Admin"
    smtp_host: str = ""
    smtp_port: int = 465
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_from_name: str = "Personal Learning Coach"
    smtp_use_ssl: bool = True
    smtp_use_tls: bool = False
    smtp_timeout_seconds: int = 10
    backup_dir: Path = Path("./data/backups")

    @field_validator("delivery_mode")
    @classmethod
    def _validate_delivery_mode(cls, value: str) -> str:
        allowed = {"local", "telegram"}
        if value not in allowed:
            raise ValueError(f"Unsupported DELIVERY_MODE: {value}")
        return value

    def validate_runtime(self) -> list[str]:
        issues: list[str] = []
        if self.delivery_mode == "telegram":
            if not self.telegram_bot_token:
                issues.append("TELEGRAM_BOT_TOKEN is required when DELIVERY_MODE=telegram")
            if not self.telegram_chat_id:
                issues.append("TELEGRAM_CHAT_ID is required when DELIVERY_MODE=telegram")
        return issues

    def validate_smtp(self) -> list[str]:
        issues: list[str] = []
        if not self.smtp_host:
            issues.append("SMTP_HOST is required to send registration email codes")
        if not self.smtp_username:
            issues.append("SMTP_USERNAME is required to send registration email codes")
        if not self.smtp_password:
            issues.append("SMTP_PASSWORD is required to send registration email codes")
        if not self.smtp_from_email:
            issues.append("SMTP_FROM_EMAIL is required to send registration email codes")
        return issues


def load_config() -> AppConfig:
    try:
        return AppConfig(
            data_dir=Path(os.environ.get("DATA_DIR", "./data")),
            delivery_mode=os.environ.get("DELIVERY_MODE", "local"),
            openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
            openai_model=os.environ.get("OPENAI_MODEL", "gpt-4.5"),
            openai_base_url=os.environ.get("OPENAI_BASE_URL", os.environ.get("BASE_URL", "")),
            telegram_bot_token=os.environ.get("TELEGRAM_BOT_TOKEN", ""),
            telegram_chat_id=os.environ.get("TELEGRAM_CHAT_ID", ""),
            api_auth_token=os.environ.get("API_AUTH_TOKEN", ""),
            admin_read_token=os.environ.get("ADMIN_READ_TOKEN", ""),
            admin_write_token=os.environ.get("ADMIN_WRITE_TOKEN", ""),
            api_host=os.environ.get("API_HOST", "127.0.0.1"),
            api_port=int(os.environ.get("API_PORT", "8000")),
            api_reload=_env_bool("API_RELOAD", False),
            admin_seed_email=os.environ.get("ADMIN_SEED_EMAIL", ""),
            admin_seed_password=os.environ.get("ADMIN_SEED_PASSWORD", ""),
            admin_seed_name=os.environ.get("ADMIN_SEED_NAME", "System Admin"),
            smtp_host=os.environ.get("SMTP_HOST", ""),
            smtp_port=int(os.environ.get("SMTP_PORT", "465")),
            smtp_username=os.environ.get("SMTP_USERNAME", ""),
            smtp_password=os.environ.get("SMTP_PASSWORD", ""),
            smtp_from_email=os.environ.get("SMTP_FROM_EMAIL", ""),
            smtp_from_name=os.environ.get("SMTP_FROM_NAME", "Personal Learning Coach"),
            smtp_use_ssl=_env_bool("SMTP_USE_SSL", True),
            smtp_use_tls=_env_bool("SMTP_USE_TLS", False),
            smtp_timeout_seconds=int(os.environ.get("SMTP_TIMEOUT_SECONDS", "10")),
            backup_dir=Path(os.environ.get("BACKUP_DIR", "./data/backups")),
        )
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}
