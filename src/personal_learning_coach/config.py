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
            backup_dir=Path(os.environ.get("BACKUP_DIR", "./data/backups")),
        )
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc
