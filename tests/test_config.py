"""Tests for runtime config and LLM client environment wiring."""

from __future__ import annotations

from personal_learning_coach.config import load_config
from personal_learning_coach import llm_client


def test_load_config_reads_openai_base_url(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.com/v1")

    config = load_config()

    assert config.openai_base_url == "https://example.com/v1"


def test_load_config_falls_back_to_base_url(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.setenv("BASE_URL", "https://fallback.example/v1")

    config = load_config()

    assert config.openai_base_url == "https://fallback.example/v1"


def test_get_client_passes_base_url(monkeypatch) -> None:
    captured: dict[str, str | None] = {}

    class FakeOpenAI:
        def __init__(self, *, api_key: str, base_url: str | None = None) -> None:
            captured["api_key"] = api_key
            captured["base_url"] = base_url

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://proxy.example/v1")
    monkeypatch.setattr(llm_client, "OpenAI", FakeOpenAI)

    llm_client.get_client()

    assert captured == {
        "api_key": "test-key",
        "base_url": "https://proxy.example/v1",
    }
