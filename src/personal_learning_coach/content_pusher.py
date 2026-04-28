"""Select the next topic and generate + deliver daily push content."""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any, cast

from personal_learning_coach import data_store
from personal_learning_coach.delivery.base import DeliveryAdapter
from personal_learning_coach.delivery.local import LocalDelivery
from personal_learning_coach.delivery.telegram import TelegramDelivery
from personal_learning_coach.llm_client import generate_text
from personal_learning_coach.models import (
    DomainStatus,
    LearnerLevel,
    LearningPlan,
    PushRecord,
    TopicNode,
    TopicProgress,
    TopicStatus,
)
from personal_learning_coach.online_resource import OnlineResourceService
from personal_learning_coach.prompts.generation import CONTENT_GENERATION_PROMPT, CONTENT_SYSTEM

logger = logging.getLogger(__name__)
_ONLINE_RESOURCE_SERVICE = OnlineResourceService()


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
    if mode == "telegram":
        return TelegramDelivery()
    raise ValueError(f"Unknown DELIVERY_MODE: {mode}")


def _delivery_channel_name(delivery: DeliveryAdapter) -> str:
    name = delivery.__class__.__name__.replace("Delivery", "").strip("_").lower()
    return name or "local"


def _deliver_and_record(push: PushRecord, delivery: DeliveryAdapter) -> PushRecord:
    push.delivery_channel = _delivery_channel_name(delivery)
    try:
        delivery.deliver(push)
    except Exception as exc:
        push.delivery_result = f"failed: {exc}"
        data_store.push_records.save(push)
        logger.exception("Push delivery failed for user=%s topic=%s", push.user_id, push.topic_id)
        raise

    push.delivered_at = datetime.now(UTC)
    push.delivery_result = "delivered"
    data_store.push_records.save(push)
    return push


def select_next_topic(user_id: str, plan: LearningPlan) -> tuple[TopicNode, TopicProgress] | None:
    """Find the next topic the user should study.

    Returns:
        (TopicNode, TopicProgress) tuple or None if no topic is ready.
    """
    progress_list: list[TopicProgress] = data_store.topic_progress.filter(user_id=user_id)
    progress_map = {p.topic_id: p for p in progress_list}

    # Review tasks take precedence over new content so weak areas are reinforced.
    for topic in sorted(plan.topics, key=lambda t: t.order):
        progress = progress_map.get(topic.topic_id)
        if progress is not None and progress.status == TopicStatus.REVIEW_DUE:
            return topic, progress

    for topic in sorted(plan.topics, key=lambda t: t.order):
        progress = progress_map.get(topic.topic_id)
        if progress is None:
            continue
        if progress.status == TopicStatus.READY:
            return topic, progress
    return None


def generate_push_content(
    domain: str,
    topic: TopicNode,
    level: LearnerLevel,
    client: Any | None = None,
) -> dict[str, str]:
    """Generate theory + practice + reflection content.

    Returns:
        Dict with keys: theory, practice_question, reflection_question.
    """
    prompt = CONTENT_GENERATION_PROMPT.format(
        domain=domain,
        topic_title=topic.title,
        topic_description=topic.description,
        level=level.value,
    )
    raw = generate_text(
        system=CONTENT_SYSTEM,
        prompt=prompt,
        max_tokens=2048,
        client=client,
    )
    return cast(dict[str, str], _parse_json(raw))


def _find_interrupted_push(user_id: str, domain: str) -> tuple[PushRecord, TopicProgress] | None:
    pushes: list[PushRecord] = data_store.push_records.filter(user_id=user_id, domain=domain)
    if not pushes:
        return None

    for push in sorted(pushes, key=lambda p: p.delivered_at or p.scheduled_at, reverse=True):
        progress_list: list[TopicProgress] = data_store.topic_progress.filter(
            user_id=user_id, topic_id=push.topic_id
        )
        if not progress_list:
            continue
        progress = progress_list[0]
        if progress.status not in (TopicStatus.PUSHED, TopicStatus.STUDYING):
            continue
        submissions = data_store.submission_records.filter(user_id=user_id, push_id=push.push_id)
        if submissions:
            continue
        return push, progress
    return None


def _build_resource_snapshot(
    content: dict[str, Any],
    domain: str,
    topic: TopicNode,
    enrollment_language: str,
    allow_online_resources: bool,
    resource_service: OnlineResourceService | None,
) -> dict[str, Any]:
    llm_resources = content.get("resources")
    if not allow_online_resources:
        if isinstance(llm_resources, dict):
            return llm_resources
        return {"enabled": False, "items": [], "source": "disabled"}

    service = resource_service or _ONLINE_RESOURCE_SERVICE
    snapshot = service.recommend_resources(domain, topic.title, language=enrollment_language)
    if llm_resources:
        snapshot["llm_resources"] = llm_resources
    return snapshot


def push_today(
    user_id: str,
    domain: str,
    client: Any | None = None,
    adapter: DeliveryAdapter | None = None,
    resource_service: OnlineResourceService | None = None,
) -> PushRecord | None:
    """Select, generate, deliver, and persist today's push.

    Args:
        user_id: Learner's ID.
        domain: Target learning domain.
        client: Optional LLM client or test double.
        adapter: Optional delivery adapter (for testing).

    Returns:
        PushRecord if a push was delivered, None if nothing to push.
    """
    enrollments = data_store.domain_enrollments.filter(user_id=user_id, domain=domain)
    if enrollments and enrollments[0].status == DomainStatus.PAUSED:
        logger.info("Domain is paused for user=%s domain=%s", user_id, domain)
        return None

    interrupted = _find_interrupted_push(user_id, domain)
    if interrupted is not None:
        previous_push, progress = interrupted
        reminder = PushRecord(
            user_id=user_id,
            topic_id=previous_push.topic_id,
            domain=domain,
            push_type="interruption_recovery",
            theory=previous_push.theory,
            practice_question=previous_push.practice_question,
            reflection_question=previous_push.reflection_question,
            scheduled_at=datetime.now(UTC),
            resource_snapshot=previous_push.resource_snapshot,
            content_snapshot=previous_push.content_snapshot,
        )
        delivery = adapter or _get_delivery_adapter()
        _deliver_and_record(reminder, delivery)
        logger.info("Recovery push delivered for user=%s topic=%s", user_id, previous_push.topic_id)
        return reminder

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

    enrollment = enrollments[0] if enrollments else None
    level = enrollment.level if enrollment else plan.level

    content = generate_push_content(domain, topic, level, client)
    resource_snapshot = _build_resource_snapshot(
        content,
        domain,
        topic,
        enrollment.language if enrollment else "zh",
        enrollment.allow_online_resources if enrollment else False,
        resource_service,
    )

    push = PushRecord(
        user_id=user_id,
        topic_id=topic.topic_id,
        domain=domain,
        push_type="review" if progress.status == TopicStatus.REVIEW_DUE else "new_topic",
        theory=content.get("theory", ""),
        practice_question=content.get("practice_question", ""),
        reflection_question=content.get("reflection_question", ""),
        scheduled_at=datetime.now(UTC),
        resource_snapshot=resource_snapshot,
        content_snapshot=content,
    )

    delivery = adapter or _get_delivery_adapter()
    _deliver_and_record(push, delivery)

    # Advance topic status to pushed
    progress.status = TopicStatus.PUSHED
    progress.attempts += 1
    data_store.topic_progress.save(progress)

    if enrollment:
        enrollment.status = DomainStatus.AWAITING_SUBMISSION
        data_store.domain_enrollments.save(enrollment)

    logger.info("Push delivered for user=%s topic=%s", user_id, topic.title)
    return push
