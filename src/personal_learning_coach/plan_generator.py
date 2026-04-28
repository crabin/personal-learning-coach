"""Generate personalized learning plans for a domain."""

from __future__ import annotations

import json
import logging
from typing import Any, cast

from personal_learning_coach import data_store
from personal_learning_coach.llm_client import generate_text
from personal_learning_coach.models import (
    DomainEnrollment,
    DomainStatus,
    LearnerLevel,
    LearningPlan,
    TopicNode,
    TopicProgress,
    TopicStatus,
)
from personal_learning_coach.prompts.generation import PLAN_GENERATION_PROMPT, PLAN_SYSTEM

logger = logging.getLogger(__name__)


def _parse_json(text: str) -> Any:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def _apply_enrollment_preferences(
    enrollment: DomainEnrollment,
    level: LearnerLevel,
    preferences: dict[str, Any] | None,
) -> DomainEnrollment:
    prefs = preferences or {}
    enrollment.level = level
    enrollment.current_level = level
    enrollment.target_level = LearnerLevel(prefs.get("target_level", level))
    enrollment.daily_minutes = int(prefs.get("daily_minutes", enrollment.daily_minutes))
    enrollment.learning_style = str(prefs.get("learning_style", enrollment.learning_style))
    enrollment.delivery_time = str(prefs.get("delivery_time", enrollment.delivery_time))
    enrollment.language = str(prefs.get("language", enrollment.language))
    enrollment.allow_online_resources = bool(
        prefs.get("allow_online_resources", enrollment.allow_online_resources)
    )
    enrollment.schedule_config = {
        **enrollment.schedule_config,
        "delivery_time": enrollment.delivery_time,
    }
    return enrollment


def generate_plan(
    user_id: str,
    domain: str,
    level: LearnerLevel,
    preferences: dict[str, Any] | None = None,
    client: Any | None = None,
) -> LearningPlan:
    """Call the LLM to create a structured learning plan.

    Args:
        user_id: Learner's ID.
        domain: Learning domain.
        level: Assessed learner level.
        preferences: Optional learner preferences dict.
        client: Optional pre-configured OpenAI client (for testing).

    Returns:
        Persisted LearningPlan with initialised TopicProgress entries.
    """
    prefs_str = json.dumps(preferences or {})
    prompt = PLAN_GENERATION_PROMPT.format(domain=domain, level=level.value, preferences=prefs_str)
    raw = generate_text(
        system=PLAN_SYSTEM,
        prompt=prompt,
        max_tokens=4096,
        client=client,
    )
    data = cast(dict[str, Any], _parse_json(raw))

    topics = [
        TopicNode(
            title=t["title"],
            description=t.get("description", ""),
            order=t.get("order", i),
            prerequisites=t.get("prerequisites", []),
        )
        for i, t in enumerate(data["topics"])
    ]

    plan = LearningPlan(
        user_id=user_id,
        domain=domain,
        level=level,
        topics=topics,
        total_weeks=data.get("total_weeks", 4),
    )
    data_store.learning_plans.save(plan)

    # Initialise topic progress — first topic is ready, rest locked
    for i, topic in enumerate(topics):
        status = TopicStatus.READY if i == 0 else TopicStatus.LOCKED
        tp = TopicProgress(
            user_id=user_id,
            topic_id=topic.topic_id,
            domain=domain,
            status=status,
        )
        data_store.topic_progress.save(tp)

    logger.info(
        "Plan generated for user=%s domain=%s topics=%d", user_id, domain, len(topics)
    )
    return plan


def enroll_domain(
    user_id: str,
    domain: str,
    level: LearnerLevel,
    preferences: dict[str, Any] | None = None,
    client: Any | None = None,
) -> tuple[DomainEnrollment, LearningPlan]:
    """Enroll a user in a domain and generate their learning plan.

    Returns:
        Tuple of (DomainEnrollment, LearningPlan).
    """
    # Update or create enrollment
    existing = data_store.domain_enrollments.filter(user_id=user_id, domain=domain)
    if existing:
        enrollment = existing[0]
        enrollment.status = DomainStatus.PLANNING
    else:
        enrollment = DomainEnrollment(user_id=user_id, domain=domain, level=level)
        enrollment.status = DomainStatus.PLANNING
    enrollment = _apply_enrollment_preferences(enrollment, level, preferences)

    data_store.domain_enrollments.save(enrollment)

    plan = generate_plan(user_id, domain, level, preferences, client)

    enrollment.status = DomainStatus.ACTIVE
    data_store.domain_enrollments.save(enrollment)

    return enrollment, plan
