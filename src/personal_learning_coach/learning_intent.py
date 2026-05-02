"""Hidden semantic classification for learning intent."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, cast

from personal_learning_coach.llm_client import generate_text
from personal_learning_coach.prompts import INTENT_PROMPT, INTENT_SYSTEM

logger = logging.getLogger(__name__)

PLAYFUL_KEYWORDS = (
    "摸鱼",
    "整活",
    "搞怪",
    "不正经",
    "沙雕",
    "发疯",
    "偷懒",
    "摆烂",
    "meme",
    "silly",
    "weird",
    "goofy",
)

CONFIDENCE_THRESHOLD = 0.55

SERIOUS_TONE_GUIDANCE = "保持清晰、结构化和实践导向，围绕真实知识与能力增长生成内容。"
PLAYFUL_TONE_GUIDANCE = (
    "可以使用搞怪、脑洞和反常识场景，但必须保留明确学习价值；"
    "把主题转译为注意力管理、沟通、判断、复盘或实践能力训练。"
)


@dataclass(frozen=True)
class LearningIntent:
    """Normalized hidden learning intent classification."""

    learning_category: str
    confidence: float
    reason: str
    tone_guidance: str


def classify_learning_intent(
    domain: str,
    *,
    language: str,
    learning_style: str,
    preferences: dict[str, Any] | None = None,
    client: Any | None = None,
) -> LearningIntent:
    """Classify a learning goal as serious or playful for hidden personalization."""
    prompt = INTENT_PROMPT.format(
        domain=domain,
        language=language,
        learning_style=learning_style,
        preferences=json.dumps(preferences or {}, ensure_ascii=False),
    )
    try:
        raw = generate_text(system=INTENT_SYSTEM, prompt=prompt, max_tokens=512, client=client)
        return _normalize_payload(cast(dict[str, Any], _parse_json(raw)), domain)
    except Exception as exc:
        logger.warning("Learning intent classification failed for domain=%s: %s", domain, exc)
        return _fallback_intent(domain)


def _parse_json(text: str) -> Any:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def _normalize_payload(payload: dict[str, Any], domain: str) -> LearningIntent:
    category = str(payload.get("learning_category", "serious")).strip().lower()
    confidence = _bounded_confidence(payload.get("confidence", 0.0))
    if category not in {"serious", "playful"}:
        return _fallback_intent(domain)
    if confidence < CONFIDENCE_THRESHOLD:
        return LearningIntent(
            learning_category="serious",
            confidence=0.0,
            reason="Low-confidence classification defaulted to serious.",
            tone_guidance=SERIOUS_TONE_GUIDANCE,
        )

    guidance = str(payload.get("tone_guidance", "")).strip()
    if not guidance:
        guidance = PLAYFUL_TONE_GUIDANCE if category == "playful" else SERIOUS_TONE_GUIDANCE
    return LearningIntent(
        learning_category=category,
        confidence=confidence,
        reason=str(payload.get("reason", "")).strip(),
        tone_guidance=guidance,
    )


def _fallback_intent(domain: str) -> LearningIntent:
    if _has_playful_keyword(domain):
        return LearningIntent(
            learning_category="playful",
            confidence=0.65,
            reason="Keyword fallback detected a playful learning topic.",
            tone_guidance=PLAYFUL_TONE_GUIDANCE,
        )
    return LearningIntent(
        learning_category="serious",
        confidence=0.0,
        reason="Defaulted to serious learning intent.",
        tone_guidance=SERIOUS_TONE_GUIDANCE,
    )


def _has_playful_keyword(domain: str) -> bool:
    normalized = domain.casefold()
    return any(keyword.casefold() in normalized for keyword in PLAYFUL_KEYWORDS)


def _bounded_confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    return min(max(confidence, 0.0), 1.0)
