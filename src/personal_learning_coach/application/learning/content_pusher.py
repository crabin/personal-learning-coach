"""Select the next topic and generate + deliver daily push content."""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any, cast

from personal_learning_coach.infrastructure import data_store
from personal_learning_coach.infrastructure.delivery.base import DeliveryAdapter
from personal_learning_coach.infrastructure.delivery.local import LocalDelivery
from personal_learning_coach.infrastructure.delivery.telegram import TelegramDelivery
from personal_learning_coach.infrastructure.llm_client import generate_text
from personal_learning_coach.domain.models import (
    DomainEnrollment,
    DomainStatus,
    EvaluationRecord,
    LearnerLevel,
    LearningPlan,
    PushRecord,
    TopicNode,
    TopicProgress,
    TopicStatus,
)
from personal_learning_coach.application.learning.online_resource import OnlineResourceService
from personal_learning_coach.prompts import CONTENT_GENERATION_PROMPT, CONTENT_SYSTEM
from personal_learning_coach.application.learning.question_history import previous_questions, record_generated_push

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
    learning_context: dict[str, Any] | None = None,
    client: Any | None = None,
) -> dict[str, Any]:
    """Generate theory + 3 basics + practice + reflection content.

    Returns:
        Dict with keys: theory, basic_questions, practice_question, reflection_question.
    """
    prompt = CONTENT_GENERATION_PROMPT.format(
        domain=domain,
        topic_title=topic.title,
        topic_description=topic.description,
        level=level.value,
        learning_context=_format_learning_context(learning_context),
    )
    raw = generate_text(
        system=CONTENT_SYSTEM,
        prompt=prompt,
        max_tokens=2048,
        client=client,
    )
    content = cast(dict[str, Any], _parse_json(raw))
    avoid_questions = (learning_context or {}).get("previous_questions", [])
    content["basic_questions"] = _normalize_basic_questions(
        content.get("basic_questions"),
        topic.title,
        avoid_questions if isinstance(avoid_questions, list) else [],
    )
    content["theory"] = str(content.get("theory", "")).strip()
    content["practice_question"] = str(content.get("practice_question", "")).strip()
    content["reflection_question"] = str(content.get("reflection_question", "")).strip()
    return content


def _enum_value(value: Any) -> Any:
    return getattr(value, "value", value)


def _topic_titles(plan: LearningPlan) -> dict[str, str]:
    return {topic.topic_id: topic.title for topic in plan.topics}


def _build_learning_context(
    user_id: str,
    domain: str,
    plan: LearningPlan,
    topic: TopicNode,
    progress: TopicProgress,
    enrollment: DomainEnrollment | None,
) -> dict[str, Any]:
    titles = _topic_titles(plan)
    evaluations = _recent_evaluations(user_id, domain, titles)
    return {
        "enrollment": _enrollment_context(enrollment),
        "current_topic": {"topic_id": topic.topic_id, "title": topic.title, "order": topic.order},
        "current_topic_progress": _progress_context(progress),
        "overall_progress": _overall_progress(user_id, domain),
        "recent_evaluations": evaluations,
        "recent_submissions": _recent_submissions(user_id, domain, titles),
        "recent_assessments": _recent_assessments(user_id, domain),
        "previous_questions": previous_questions(user_id, domain),
        "generation_guidance": _generation_guidance(progress, evaluations),
    }


def _enrollment_context(enrollment: DomainEnrollment | None) -> dict[str, Any]:
    if enrollment is None:
        return {}
    return {
        "level": _enum_value(enrollment.level),
        "target_level": _enum_value(enrollment.target_level),
        "current_level": _enum_value(enrollment.current_level),
        "daily_minutes": enrollment.daily_minutes,
        "learning_style": enrollment.learning_style,
        "learning_category": enrollment.learning_category,
        "learning_category_confidence": enrollment.learning_category_confidence,
        "learning_tone_guidance": enrollment.learning_tone_guidance,
        "language": enrollment.language,
    }


def _progress_context(progress: TopicProgress) -> dict[str, Any]:
    return {
        "status": _enum_value(progress.status),
        "mastery_score": progress.mastery_score,
        "attempts": progress.attempts,
        "last_review_at": progress.last_review_at.isoformat() if progress.last_review_at else None,
    }


def _overall_progress(user_id: str, domain: str) -> dict[str, Any]:
    progress_records: list[TopicProgress] = data_store.topic_progress.filter(user_id=user_id, domain=domain)
    if not progress_records:
        return {"total_topics": 0, "average_mastery": 0.0, "status_counts": {}}
    status_counts: dict[str, int] = {}
    for item in progress_records:
        status = str(_enum_value(item.status))
        status_counts[status] = status_counts.get(status, 0) + 1
    average = sum(item.mastery_score for item in progress_records) / len(progress_records)
    return {
        "total_topics": len(progress_records),
        "average_mastery": round(average, 2),
        "status_counts": status_counts,
    }


def _recent_evaluations(user_id: str, domain: str, titles: dict[str, str]) -> list[dict[str, Any]]:
    evaluations: list[EvaluationRecord] = data_store.evaluation_records.filter(user_id=user_id, domain=domain)
    recent = sorted(evaluations, key=lambda item: item.evaluated_at, reverse=True)[:5]
    return [
        {
            "topic_title": titles.get(item.topic_id, item.topic_id),
            "overall_score": item.overall_score,
            "next_action": item.next_action,
            "feedback": item.llm_feedback,
            "strengths": item.strengths[:3],
            "weaknesses": item.weaknesses[:3],
            "missed_concepts": item.missed_concepts[:3],
            "improvement_suggestions": item.improvement_suggestions[:3],
        }
        for item in recent
    ]


def _recent_submissions(user_id: str, domain: str, titles: dict[str, str]) -> list[dict[str, Any]]:
    submissions = data_store.submission_records.filter(user_id=user_id, domain=domain)
    recent = sorted(submissions, key=lambda item: item.submitted_at, reverse=True)[:3]
    return [
        {
            "topic_title": titles.get(item.topic_id, item.topic_id),
            "answer_excerpt": item.normalized_answer[:240],
            "practice_result": item.practice_result[:240],
        }
        for item in recent
    ]


def _recent_assessments(user_id: str, domain: str) -> list[dict[str, Any]]:
    assessments = data_store.assessment_records.filter(user_id=user_id, domain=domain)
    recent = sorted(assessments, key=lambda item: item.evaluated_at, reverse=True)[:3]
    return [
        {
            "assessment_type": item.assessment_type,
            "level": _enum_value(item.level),
            "feedback": item.llm_feedback,
            "strengths": item.strengths[:3],
            "weaknesses": item.weaknesses[:3],
            "scores": item.structured_scores,
        }
        for item in recent
    ]


def _generation_guidance(
    progress: TopicProgress,
    evaluations: list[dict[str, Any]],
) -> str:
    if progress.status == TopicStatus.REVIEW_DUE:
        return "Generate supplemental review questions focused on weak and missed concepts."
    if evaluations and evaluations[0]["next_action"] in {"review", "consolidate"}:
        return "Generate consolidation questions before moving to new difficulty."
    return "Generate the next-stage questions while still checking prerequisite understanding."


def _format_learning_context(context: dict[str, Any] | None) -> str:
    if not context:
        return "No prior learning history is available. Generate an appropriate first lesson."

    lines = [_format_enrollment_line(context), _format_current_progress_line(context)]
    lines.extend(_format_assessment_lines(context.get("recent_assessments", [])))
    lines.extend(_format_evaluation_lines(context.get("recent_evaluations", [])))
    lines.extend(_format_submission_lines(context.get("recent_submissions", [])))
    lines.extend(_format_previous_question_lines(context.get("previous_questions", [])))
    lines.append(f"Guidance: {context.get('generation_guidance', '')}")
    return "\n".join(line for line in lines if line)


def _format_enrollment_line(context: dict[str, Any]) -> str:
    enrollment = context.get("enrollment", {})
    if not enrollment:
        return ""
    return (
        "Enrollment: "
        f"level={enrollment.get('level')}, "
        f"target_level={enrollment.get('target_level')}, "
        f"current_level={enrollment.get('current_level')}, "
        f"daily_minutes={enrollment.get('daily_minutes')}, "
        f"learning_style={enrollment.get('learning_style')}, "
        f"learning_category={enrollment.get('learning_category')}, "
        f"learning_category_confidence={enrollment.get('learning_category_confidence')}, "
        f"learning_tone_guidance={enrollment.get('learning_tone_guidance')}"
    )


def _format_current_progress_line(context: dict[str, Any]) -> str:
    progress = context.get("current_topic_progress", {})
    overall = context.get("overall_progress", {})
    return (
        "Current topic progress: "
        f"status={progress.get('status')}, "
        f"mastery_score={progress.get('mastery_score')}, "
        f"attempts={progress.get('attempts')}; "
        f"overall_average_mastery={overall.get('average_mastery')}, "
        f"status_counts={overall.get('status_counts')}"
    )


def _format_assessment_lines(assessments: list[dict[str, Any]]) -> list[str]:
    return [
        (
            f"Assessment {item['assessment_type']}: level={item['level']}; "
            f"feedback={item['feedback']}; "
            f"strengths={', '.join(item['strengths'])}; "
            f"weaknesses={', '.join(item['weaknesses'])}"
        )
        for item in assessments
    ]


def _format_evaluation_lines(evaluations: list[dict[str, Any]]) -> list[str]:
    return [
        (
            f"Evaluation for {item['topic_title']}: score={item['overall_score']}, "
            f"next_action={item['next_action']}, feedback={item['feedback']}, "
            f"weaknesses: {', '.join(item['weaknesses'])}, "
            f"missed concepts: {', '.join(item['missed_concepts'])}, "
            f"suggestions: {', '.join(item['improvement_suggestions'])}"
        )
        for item in evaluations
    ]


def _format_submission_lines(submissions: list[dict[str, Any]]) -> list[str]:
    return [
        (
            f"Submission for {item['topic_title']}: "
            f"answer_excerpt={item['answer_excerpt']}; "
            f"practice_result={item['practice_result']}"
        )
        for item in submissions
    ]


def _format_previous_question_lines(questions: list[Any]) -> list[str]:
    normalized = [str(question).strip() for question in questions if str(question).strip()]
    if not normalized:
        return []
    return ["Previously asked questions to avoid repeating: " + " | ".join(normalized[:12])]


def _normalize_basic_questions(
    raw_questions: Any,
    topic_title: str,
    avoid_questions: list[Any] | None = None,
) -> list[str]:
    normalized: list[str] = []
    blocked = {str(question).strip().casefold() for question in (avoid_questions or [])}

    if isinstance(raw_questions, list):
        for item in raw_questions:
            if isinstance(item, str):
                value = item.strip()
            elif isinstance(item, dict):
                candidate = item.get("question") or item.get("q") or item.get("text") or ""
                value = str(candidate).strip()
            else:
                value = str(item).strip()

            if value and value.casefold() not in blocked and value not in normalized:
                normalized.append(value)

    fallback_questions = [
        f"{topic_title} 的核心概念是什么？请用 1-2 句话说明。",
        f"{topic_title} 中最重要的术语或组成部分有哪些？",
        f"{topic_title} 在实际使用中主要解决什么问题？",
    ]

    for question in fallback_questions:
        if len(normalized) >= 3:
            break
        if question.casefold() not in blocked and question not in normalized:
            normalized.append(question)

    index = 1
    while len(normalized) < 3:
        normalized.append(f"{topic_title} 的补充理解问题 {index}：请结合一个新例子说明。")
        index += 1

    return normalized[:3]


def _basic_questions_from_push(push: PushRecord) -> list[str]:
    questions = push.content_snapshot.get("basic_questions", [])
    if not isinstance(questions, list):
        return []
    return [str(question).strip() for question in questions if str(question).strip()]


def _is_answerable_push(push: PushRecord) -> bool:
    return bool(
        push.theory.strip()
        and len(_basic_questions_from_push(push)) >= 3
        and push.practice_question.strip()
        and push.reflection_question.strip()
    )


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
        if not _is_answerable_push(push):
            progress.status = TopicStatus.READY
            data_store.topic_progress.save(progress)
            logger.warning(
                "Skipped incomplete interrupted push for user=%s domain=%s topic=%s push=%s",
                user_id,
                domain,
                push.topic_id,
                push.push_id,
            )
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

    learning_context = _build_learning_context(user_id, domain, plan, topic, progress, enrollment)
    content = generate_push_content(domain, topic, level, learning_context, client)
    content["learning_context"] = learning_context
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
    record_generated_push(push, topic.title)

    # Advance topic status to pushed
    progress.status = TopicStatus.PUSHED
    progress.attempts += 1
    data_store.topic_progress.save(progress)

    if enrollment:
        enrollment.status = DomainStatus.AWAITING_SUBMISSION
        data_store.domain_enrollments.save(enrollment)

    logger.info("Push delivered for user=%s topic=%s", user_id, topic.title)
    return push
