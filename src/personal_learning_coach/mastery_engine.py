"""Calculate mastery scores and manage topic state transitions."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from personal_learning_coach import data_store
from personal_learning_coach.models import (
    AssessmentRecord,
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
    evals: list[EvaluationRecord] = data_store.evaluation_records.filter(user_id=user_id, topic_id=topic_id)
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
            progress_list: list[TopicProgress] = data_store.topic_progress.filter(
                user_id=user_id, topic_id=next_topic.topic_id
            )
            if progress_list and progress_list[0].status == TopicStatus.LOCKED:
                progress_list[0].status = TopicStatus.READY
                data_store.topic_progress.save(progress_list[0])
                logger.info("Unlocked next topic: %s", next_topic.title)
            break


def _all_topics_mastered(user_id: str, plan: LearningPlan) -> bool:
    for topic in plan.topics:
        progress: list[TopicProgress] = data_store.topic_progress.filter(
            user_id=user_id, topic_id=topic.topic_id
        )
        if not progress or progress[0].status != TopicStatus.MASTERED:
            return False
    return True


def complete_final_assessment(user_id: str, domain: str, passed: bool) -> DomainEnrollment:
    """Update the domain after a final assessment result."""
    enrollments: list[DomainEnrollment] = data_store.domain_enrollments.filter(user_id=user_id, domain=domain)
    if not enrollments:
        raise ValueError(f"Domain enrollment not found for user={user_id} domain={domain}")
    enrollment = enrollments[0]
    enrollment.status = DomainStatus.COMPLETED if passed else DomainStatus.ACTIVE
    enrollment.updated_at = datetime.now(UTC)
    data_store.domain_enrollments.save(enrollment)
    return enrollment


def submit_final_assessment(
    user_id: str,
    domain: str,
    passed: bool,
    score: float = 0.0,
    feedback: str = "",
) -> tuple[AssessmentRecord, DomainEnrollment]:
    """Persist a final assessment result and update domain status."""
    enrollments: list[DomainEnrollment] = data_store.domain_enrollments.filter(user_id=user_id, domain=domain)
    if not enrollments:
        raise ValueError(f"Domain enrollment not found for user={user_id} domain={domain}")
    enrollment = enrollments[0]
    if enrollment.status != DomainStatus.FINAL_ASSESSMENT_DUE:
        raise RuntimeError(
            f"Domain {domain} for user {user_id} is not ready for final assessment"
        )

    record = AssessmentRecord(
        user_id=user_id,
        domain=domain,
        assessment_type="final",
        passed=passed,
        level=enrollment.current_level or enrollment.level,
        llm_feedback=feedback,
        structured_scores={"final_score": score},
        confidence=1.0 if passed else 0.5,
    )
    data_store.assessment_records.save(record)

    updated = complete_final_assessment(user_id, domain, passed)
    if passed and updated.target_level is not None:
        updated.current_level = updated.target_level
        updated.updated_at = datetime.now(UTC)
        data_store.domain_enrollments.save(updated)
    return record, updated


def apply_evaluation(
    evaluation: EvaluationRecord,
    progress: TopicProgress,
) -> TopicProgress:
    """Apply an evaluation result to topic progress.

    Updates mastery score, status, and next_review scheduling.

    Returns:
        Updated and persisted TopicProgress.
    """
    data_store.evaluation_records.save(evaluation)
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
    evaluation.progress_applied = True
    data_store.evaluation_records.save(evaluation)

    # If mastered, try to unlock the next topic
    if progress.status == TopicStatus.MASTERED:
        plans: list[LearningPlan] = data_store.learning_plans.filter(
            user_id=evaluation.user_id, domain=evaluation.domain
        )
        if plans:
            plan = max(plans, key=lambda item: item.generated_at)
            _unlock_next_topic(evaluation.user_id, plan, evaluation.topic_id)

            # Check if all topics are mastered → learner is ready for final assessment
            if _all_topics_mastered(evaluation.user_id, plan):
                enrollments: list[DomainEnrollment] = data_store.domain_enrollments.filter(
                    user_id=evaluation.user_id, domain=evaluation.domain
                )
                if enrollments:
                    enrollments[0].status = DomainStatus.FINAL_ASSESSMENT_DUE
                    enrollments[0].updated_at = datetime.now(UTC)
                    data_store.domain_enrollments.save(enrollments[0])
                    logger.info(
                        "Domain %s ready for final assessment for user %s",
                        evaluation.domain,
                        evaluation.user_id,
                    )

    return progress


def sync_unapplied_evaluations(user_id: str, domain: str) -> int:
    """Apply any saved evaluations that have not yet updated topic progress."""
    evaluations: list[EvaluationRecord] = data_store.evaluation_records.filter(
        user_id=user_id, domain=domain
    )
    synced = 0
    for evaluation in sorted(evaluations, key=lambda item: item.evaluated_at):
        if evaluation.progress_applied:
            continue
        progress_list: list[TopicProgress] = data_store.topic_progress.filter(
            user_id=user_id, topic_id=evaluation.topic_id
        )
        if not progress_list:
            logger.warning(
                "Cannot sync evaluation=%s because topic progress is missing",
                evaluation.eval_id,
            )
            continue
        apply_evaluation(evaluation, progress_list[0])
        synced += 1
    return synced
