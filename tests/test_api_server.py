"""Tests for serving the API process."""

from __future__ import annotations

from typing import Any

from personal_learning_coach.entrypoints.api import main as api_main


def test_serve_uses_loopback_host_by_default(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_run(app_path: str, **kwargs: Any) -> None:
        captured["app_path"] = app_path
        captured.update(kwargs)

    monkeypatch.delenv("API_HOST", raising=False)
    monkeypatch.delenv("API_PORT", raising=False)
    monkeypatch.delenv("API_RELOAD", raising=False)
    monkeypatch.setattr(api_main.uvicorn, "run", fake_run)

    api_main.serve()

    assert captured == {
        "app_path": "personal_learning_coach.entrypoints.api.main:app",
        "host": "127.0.0.1",
        "port": 8000,
        "reload": False,
    }
