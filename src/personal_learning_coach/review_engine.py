"""Spaced repetition review scheduling and weekly summary generation."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import TypedDict

from personal_learning_coach import data_store
from personal_learning_coach.models import (
    EvaluationRecord,
    LearningPlan,
    PushRecord,
    SubmissionRecord,
    TopicProgress,
    TopicStatus,
)

logger = logging.getLogger(__name__)

# Spaced repetition intervals in days
REVIEW_INTERVALS = [1, 3, 7, 14, 30]


class TopicSummary(TypedDict):
    topic_id: str
    status: str
    mastery_score: float
    avg_eval_score: float | None
    attempts: int


class WeeklySummary(TypedDict):
    user_id: str
    domain: str
    generated_at: str
    total_topics: int
    mastered_topics: int
    review_due_topics: int
    mastery_rate: float
    avg_score: float
    topic_summaries: list[TopicSummary]


def _review_interval_days(attempt: int) -> int:
    """Return the review interval for a given attempt number (0-indexed)."""
    idx = min(attempt, len(REVIEW_INTERVALS) - 1)
    return REVIEW_INTERVALS[idx]


def get_due_reviews(user_id: str, domain: str) -> list[TopicProgress]:
    """Return topics that are due for review right now.

    A topic is due when its next_review_at is in the past and status is REVIEW_DUE.
    """
    now = datetime.now(UTC)
    candidates: list[TopicProgress] = data_store.topic_progress.filter(user_id=user_id, domain=domain)
    due: list[TopicProgress] = []
    for p in candidates:
        if p.status == TopicStatus.REVIEW_DUE:
            if p.next_review_at is None or p.next_review_at <= now:
                due.append(p)
    return due


def schedule_review(progress: TopicProgress) -> TopicProgress:
    """Compute and set the next review date based on attempt count.

    Returns:
        Updated and persisted TopicProgress.
    """
    interval = _review_interval_days(progress.attempts)
    progress.next_review_at = datetime.now(UTC) + timedelta(days=interval)
    progress.status = TopicStatus.REVIEW_DUE
    data_store.topic_progress.save(progress)
    logger.info(
        "Review scheduled for topic=%s in %d days", progress.topic_id, interval
    )
    return progress


def reset_to_ready(progress: TopicProgress) -> TopicProgress:
    """Mark a review-due topic as READY so it gets pushed again."""
    progress.status = TopicStatus.READY
    data_store.topic_progress.save(progress)
    return progress


def select_active_plan(user_id: str, domain: str) -> LearningPlan | None:
    """Return the plan that best matches the learner's active work."""
    plans: list[LearningPlan] = data_store.learning_plans.filter(user_id=user_id, domain=domain)
    if not plans:
        return None

    activity_topic_ids = _activity_topic_ids(user_id, domain)
    plans_by_date = sorted(plans, key=lambda plan: plan.generated_at, reverse=True)
    for plan in plans_by_date:
        plan_topic_ids = {topic.topic_id for topic in plan.topics}
        if plan_topic_ids.intersection(activity_topic_ids):
            return plan
    return plans_by_date[0]


def _activity_topic_ids(user_id: str, domain: str) -> set[str]:
    evaluations: list[EvaluationRecord] = data_store.evaluation_records.filter(
        user_id=user_id, domain=domain
    )
    submissions: list[SubmissionRecord] = data_store.submission_records.filter(
        user_id=user_id, domain=domain
    )
    pushes: list[PushRecord] = data_store.push_records.filter(user_id=user_id, domain=domain)
    progress_records: list[TopicProgress] = data_store.topic_progress.filter(
        user_id=user_id, domain=domain
    )
    active_progress_statuses = {
        TopicStatus.PUSHED,
        TopicStatus.STUDYING,
        TopicStatus.SUBMITTED,
        TopicStatus.EVALUATED,
        TopicStatus.REVIEW_DUE,
        TopicStatus.MASTERED,
    }
    return {
        *{evaluation.topic_id for evaluation in evaluations},
        *{submission.topic_id for submission in submissions},
        *{push.topic_id for push in pushes},
        *{
            progress.topic_id
            for progress in progress_records
            if progress.attempts > 0 or progress.status in active_progress_statuses
        },
    }


def _active_plan_topic_ids(user_id: str, domain: str) -> set[str] | None:
    active_plan = select_active_plan(user_id, domain)
    if active_plan is None:
        return None
    return {topic.topic_id for topic in active_plan.topics}


def generate_weekly_summary(user_id: str, domain: str) -> WeeklySummary:
    """Generate a weekly learning summary for the user.

    Returns:
        Dict with keys: topics_covered, avg_score, mastery_rate, review_count.
    """
    progress_list: list[TopicProgress] = data_store.topic_progress.filter(user_id=user_id, domain=domain)
    evals: list[EvaluationRecord] = data_store.evaluation_records.filter(user_id=user_id, domain=domain)
    active_topic_ids = _active_plan_topic_ids(user_id, domain)

    if active_topic_ids is not None:
        progress_list = [progress for progress in progress_list if progress.topic_id in active_topic_ids]
        evals = [evaluation for evaluation in evals if evaluation.topic_id in active_topic_ids]

    total_topics = len(progress_list)
    mastered = sum(1 for p in progress_list if p.status == TopicStatus.MASTERED)
    review_due = sum(1 for p in progress_list if p.status == TopicStatus.REVIEW_DUE)
    avg_score = (
        round(sum(e.overall_score for e in evals) / len(evals), 1) if evals else 0.0
    )
    mastery_rate = round(mastered / total_topics, 2) if total_topics > 0 else 0.0

    # Collect per-topic scores
    topic_summaries: list[TopicSummary] = []
    for p in progress_list:
        topic_evals = [e for e in evals if e.topic_id == p.topic_id]
        topic_avg = (
            round(sum(e.overall_score for e in topic_evals) / len(topic_evals), 1)
            if topic_evals
            else None
        )
        topic_summaries.append(
            {
                "topic_id": p.topic_id,
                "status": p.status.value,
                "mastery_score": p.mastery_score,
                "avg_eval_score": topic_avg,
                "attempts": p.attempts,
            }
        )

    return {
        "user_id": user_id,
        "domain": domain,
        "generated_at": datetime.now(UTC).isoformat(),
        "total_topics": total_topics,
        "mastered_topics": mastered,
        "review_due_topics": review_due,
        "mastery_rate": mastery_rate,
        "avg_score": avg_score,
        "topic_summaries": topic_summaries,
    }
