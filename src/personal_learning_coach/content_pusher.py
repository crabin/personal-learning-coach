"""Select the next topic and generate + deliver daily push content."""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

import anthropic

from personal_learning_coach import data_store
from personal_learning_coach.delivery.base import DeliveryAdapter
from personal_learning_coach.delivery.local import LocalDelivery
from personal_learning_coach.models import (
    LearnerLevel,
    LearningPlan,
    PushRecord,
    TopicNode,
    TopicProgress,
    TopicStatus,
)
from personal_learning_coach.prompts.generation import CONTENT_GENERATION_PROMPT, CONTENT_SYSTEM

logger = logging.getLogger(__name__)

MODEL = "claude-haiku-4-5-20251001"


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def _parse_json(text: str) -> Any:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def _get_delivery_adapter() -> DeliveryAdapter:
    mode = os.environ.get("DELIVERY_MODE", "local")
    if mode == "local":
        return LocalDelivery()
    raise ValueError(f"Unknown DELIVERY_MODE: {mode}")


def select_next_topic(user_id: str, plan: LearningPlan) -> tuple[TopicNode, TopicProgress] | None:
    """Find the next topic the user should study.

    Returns:
        (TopicNode, TopicProgress) tuple or None if no topic is ready.
    """
    progress_list = data_store.topic_progress.filter(user_id=user_id)
    progress_map = {p.topic_id: p for p in progress_list}

    for topic in sorted(plan.topics, key=lambda t: t.order):
        progress = progress_map.get(topic.topic_id)
        if progress is None:
            continue
        if progress.status in (TopicStatus.READY, TopicStatus.REVIEW_DUE):
            return topic, progress
    return None


def generate_push_content(
    domain: str,
    topic: TopicNode,
    level: LearnerLevel,
    client: anthropic.Anthropic | None = None,
) -> dict[str, str]:
    """Call Claude to generate theory + practice + reflection content.

    Returns:
        Dict with keys: theory, practice_question, reflection_question.
    """
    cl = client or _client()
    prompt = CONTENT_GENERATION_PROMPT.format(
        domain=domain,
        topic_title=topic.title,
        topic_description=topic.description,
        level=level.value,
    )
    response = cl.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=CONTENT_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text  # type: ignore[union-attr]
    return _parse_json(raw)


def push_today(
    user_id: str,
    domain: str,
    client: anthropic.Anthropic | None = None,
    adapter: DeliveryAdapter | None = None,
) -> PushRecord | None:
    """Select, generate, deliver, and persist today's push.

    Args:
        user_id: Learner's ID.
        domain: Target learning domain.
        client: Optional Anthropic client (for testing).
        adapter: Optional delivery adapter (for testing).

    Returns:
        PushRecord if a push was delivered, None if nothing to push.
    """
    plans = data_store.learning_plans.filter(user_id=user_id, domain=domain)
    if not plans:
        logger.warning("No learning plan found for user=%s domain=%s", user_id, domain)
        return None

    plan = plans[0]

    result = select_next_topic(user_id, plan)
    if result is None:
        logger.info("No ready topic for user=%s domain=%s", user_id, domain)
        return None

    topic, progress = result

    enrollments = data_store.domain_enrollments.filter(user_id=user_id, domain=domain)
    level = enrollments[0].level if enrollments else plan.level

    content = generate_push_content(domain, topic, level, client)

    push = PushRecord(
        user_id=user_id,
        topic_id=topic.topic_id,
        domain=domain,
        theory=content.get("theory", ""),
        practice_question=content.get("practice_question", ""),
        reflection_question=content.get("reflection_question", ""),
        scheduled_at=datetime.now(UTC),
        content_snapshot=content,
    )

    delivery = adapter or _get_delivery_adapter()
    delivery.deliver(push)
    push.delivered_at = datetime.now(UTC)

    data_store.push_records.save(push)

    # Advance topic status to pushed
    progress.status = TopicStatus.PUSHED
    progress.attempts += 1
    data_store.topic_progress.save(progress)

    logger.info("Push delivered for user=%s topic=%s", user_id, topic.title)
    return push
