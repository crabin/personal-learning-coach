"""Telegram delivery adapter for real push notifications."""

from __future__ import annotations

import os

import httpx

from personal_learning_coach.infrastructure.delivery.base import DeliveryAdapter
from personal_learning_coach.domain.models import PushRecord


class TelegramDelivery(DeliveryAdapter):
    """Send push content through the Telegram Bot API."""

    def __init__(
        self,
        bot_token: str | None = None,
        chat_id: str | None = None,
        base_url: str | None = None,
        timeout: float = 10.0,
        client: httpx.Client | None = None,
    ) -> None:
        self._bot_token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self._chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID", "")
        self._base_url = (base_url or "https://api.telegram.org").rstrip("/")
        self._timeout = timeout
        self._client = client

        if not self._bot_token:
            raise ValueError("Missing TELEGRAM_BOT_TOKEN for Telegram delivery")
        if not self._chat_id:
            raise ValueError("Missing TELEGRAM_CHAT_ID for Telegram delivery")

    def deliver(self, push: PushRecord) -> None:
        payload = {
            "chat_id": self._chat_id,
            "text": self.format_push(push),
            "disable_web_page_preview": False,
        }
        endpoint = f"{self._base_url}/bot{self._bot_token}/sendMessage"

        if self._client is not None:
            response = self._client.post(endpoint, json=payload)
        else:
            response = httpx.post(endpoint, json=payload, timeout=self._timeout)
        response.raise_for_status()

