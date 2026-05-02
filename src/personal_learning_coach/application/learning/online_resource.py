"""Fetch and curate lightweight online learning resources with graceful fallback."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any, Callable
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)

ResourceFetcher = Callable[[str, str, str, int], list[dict[str, str]]]


def _normalize_url(url: str) -> str:
    return url.rstrip("/").lower()


def _dedupe_resources(resources: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    deduped: list[dict[str, str]] = []
    for item in resources:
        title = item.get("title", "").strip()
        url = item.get("url", "").strip()
        summary = item.get("summary", "").strip()
        if not title or not url:
            continue
        key = (_normalize_url(url), title.lower())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(
            {
                "title": title,
                "url": url,
                "summary": summary,
                "source": item.get("source", "web"),
            }
        )
    return deduped


def _fetch_from_wikipedia(domain: str, topic_title: str, language: str, limit: int) -> list[dict[str, str]]:
    lang = "zh" if language.startswith("zh") else "en"
    query = f"{domain} {topic_title}".strip()
    url = f"https://{lang}.wikipedia.org/w/rest.php/v1/search/title?q={quote(query)}&limit={limit}"
    response = httpx.get(url, timeout=5.0)
    response.raise_for_status()
    payload = response.json()

    items: list[dict[str, str]] = []
    for page in payload.get("pages", []):
        key = page.get("key")
        title = page.get("title", "").strip()
        if not key or not title:
            continue
        items.append(
            {
                "title": title,
                "url": f"https://{lang}.wikipedia.org/wiki/{quote(str(key))}",
                "summary": page.get("excerpt", "").replace("<span class=\"searchmatch\">", "").replace(
                    "</span>",
                    "",
                ),
                "source": "wikipedia",
            }
        )
    return items


class OnlineResourceService:
    """Fetch recommended resources with in-memory caching and failure downgrade."""

    def __init__(
        self,
        fetcher: ResourceFetcher | None = None,
        ttl_seconds: int = 6 * 60 * 60,
        now_fn: Callable[[], datetime] | None = None,
    ) -> None:
        self._fetcher = fetcher or _fetch_from_wikipedia
        self._ttl = timedelta(seconds=ttl_seconds)
        self._now_fn = now_fn or (lambda: datetime.now(UTC))
        self._cache: dict[tuple[str, str, str, int], tuple[datetime, dict[str, Any]]] = {}

    def recommend_resources(
        self,
        domain: str,
        topic_title: str,
        *,
        language: str = "zh",
        limit: int = 3,
    ) -> dict[str, Any]:
        cache_key = (domain.strip().lower(), topic_title.strip().lower(), language.lower(), limit)
        now = self._now_fn()
        cached = self._cache.get(cache_key)
        if cached is not None and cached[0] > now:
            snapshot = dict(cached[1])
            snapshot["source"] = "cache"
            return snapshot

        try:
            raw_items = self._fetcher(domain, topic_title, language, limit)
            items = _dedupe_resources(raw_items)[:limit]
            snapshot = {
                "enabled": True,
                "query": f"{domain} {topic_title}".strip(),
                "items": items,
                "source": "online",
                "fetched_at": now.isoformat(),
            }
        except Exception as exc:
            logger.warning(
                "Online resource fetch failed for domain=%s topic=%s: %s",
                domain,
                topic_title,
                exc,
            )
            snapshot = {
                "enabled": True,
                "query": f"{domain} {topic_title}".strip(),
                "items": [],
                "source": "fallback",
                "error": str(exc),
                "fetched_at": now.isoformat(),
            }

        self._cache[cache_key] = (now + self._ttl, snapshot)
        return dict(snapshot)
