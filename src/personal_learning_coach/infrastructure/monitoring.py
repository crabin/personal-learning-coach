"""Runtime monitoring helpers and structured logging."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from personal_learning_coach.infrastructure import data_store
from personal_learning_coach.infrastructure.config import load_config
from personal_learning_coach.domain.models import RuntimeEvent


class JsonFormatter(logging.Formatter):
    """Serialize log records as one-line JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> None:
    config = load_config()
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    root = logging.getLogger()
    root.setLevel(log_level)

    logs_dir = Path(config.data_dir) / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / "app.log"

    if not any(isinstance(handler, logging.FileHandler) and handler.baseFilename == str(log_path) for handler in root.handlers):
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(JsonFormatter())
        root.addHandler(file_handler)

    if not root.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        root.addHandler(console_handler)


def record_runtime_event(level: str, category: str, message: str, details: dict[str, Any] | None = None) -> RuntimeEvent:
    event = RuntimeEvent(level=level, category=category, message=message, details=details or {})
    data_store.runtime_events.save(event)
    return event


def recent_runtime_events(limit: int = 20) -> list[RuntimeEvent]:
    events = data_store.runtime_events.all()
    return sorted(events, key=lambda event: event.created_at, reverse=True)[:limit]


def current_alerts() -> list[dict[str, Any]]:
    events = recent_runtime_events(limit=100)
    auth_failures = [event for event in events if event.category == "auth" and event.level == "warning"]
    errors = [event for event in events if event.level == "error"]
    alerts: list[dict[str, Any]] = []

    if auth_failures:
        alerts.append(
            {
                "severity": "warning",
                "category": "auth",
                "message": f"{len(auth_failures)} recent authentication failures detected",
            }
        )
    if errors:
        alerts.append(
            {
                "severity": "critical",
                "category": "exception",
                "message": f"{len(errors)} unhandled application errors recorded",
            }
        )
    return alerts
