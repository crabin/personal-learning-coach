"""Calculate mastery scores and manage topic state transitions."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from personal_learning_coach import data_store
from personal_learning_coach.models import (
    DomainEnrollment,
    DomainStatus,
    EvaluationRecord,
    LearningPlan,
    TopicProgress,
    TopicStatus,
)

logger = logging.getLogger(__name__)

MASTERY_THRESHOLD = 80.0  # score >= this → mastered
REVIEW_THRESHOLD = 60.0   # score < this → review_due


def recalculate_mastery(user_id: str, topic_id: str) -> float:
    """Compute mastery score as the average of last 3 evaluation scores.

    Returns:
        Mastery score 0–100.
    """
    evals = data_store.evaluation_records.filter(user_id=user_id, topic_id=topic_id)
    if not evals:
        return 0.0
    sorted_evals = sorted(evals, key=lambda e: e.evaluated_at, reverse=True)
    recent = sorted_evals[:3]
    return round(sum(e.overall_score for e in recent) / len(recent), 2)


def _unlock_next_topic(user_id: str, plan: LearningPlan, current_topic_id: str) -> None:
    """Unlock the topic that follows the current one in the plan."""
    topics = sorted(plan.topics, key=lambda t: t.order)
    for i, topic in enumerate(topics):
        if topic.topic_id == current_topic_id and i + 1 < len(topics):
            next_topic = topics[i + 1]
            progress_list = data_store.topic_progress.filter(user_id=user_id, topic_id=next_topic.topic_id)
            if progress_list and progress_list[0].status == TopicStatus.LOCKED:
                progress_list[0].status = TopicStatus.READY
                data_store.topic_progress.save(progress_list[0])
                logger.info("Unlocked next topic: %s", next_topic.title)
            break


def _all_topics_mastered(user_id: str, plan: LearningPlan) -> bool:
    for topic in plan.topics:
        progress = data_store.topic_progress.filter(user_id=user_id, topic_id=topic.topic_id)
        if not progress or progress[0].status != TopicStatus.MASTERED:
            return False
    return True


def apply_evaluation(
    evaluation: EvaluationRecord,
    progress: TopicProgress,
) -> TopicProgress:
    """Apply an evaluation result to topic progress.

    Updates mastery score, status, and next_review scheduling.

    Returns:
        Updated and persisted TopicProgress.
    """
    mastery = recalculate_mastery(evaluation.user_id, evaluation.topic_id)
    progress.mastery_score = mastery

    if mastery >= MASTERY_THRESHOLD:
        progress.status = TopicStatus.MASTERED
        logger.info("Topic %s mastered with score %.1f", evaluation.topic_id, mastery)
    elif mastery < REVIEW_THRESHOLD:
        progress.status = TopicStatus.REVIEW_DUE
        progress.next_review_at = datetime.now(UTC) + timedelta(days=1)
        logger.info("Topic %s needs review, score %.1f", evaluation.topic_id, mastery)
    else:
        progress.status = TopicStatus.EVALUATED

    progress.last_review_at = datetime.now(UTC)
    progress.updated_at = datetime.now(UTC)
    data_store.topic_progress.save(progress)

    # If mastered, try to unlock the next topic
    if progress.status == TopicStatus.MASTERED:
        plans = data_store.learning_plans.filter(
            user_id=evaluation.user_id, domain=evaluation.domain
        )
        if plans:
            _unlock_next_topic(evaluation.user_id, plans[0], evaluation.topic_id)

            # Check if all topics are mastered → complete domain
            if _all_topics_mastered(evaluation.user_id, plans[0]):
                enrollments = data_store.domain_enrollments.filter(
                    user_id=evaluation.user_id, domain=evaluation.domain
                )
                if enrollments:
                    enrollments[0].status = DomainStatus.COMPLETED
                    data_store.domain_enrollments.save(enrollments[0])
                    logger.info(
                        "Domain %s completed for user %s", evaluation.domain, evaluation.user_id
                    )

    return progress
