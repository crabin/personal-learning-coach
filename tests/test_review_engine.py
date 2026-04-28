"""Tests for the review engine."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from personal_learning_coach import data_store
from personal_learning_coach.models import (
    EvaluationRecord,
    TopicProgress,
    TopicStatus,
)
from personal_learning_coach.review_engine import (
    generate_weekly_summary,
    get_due_reviews,
    reset_to_ready,
    schedule_review,
)


def test_get_due_reviews_returns_overdue(tmp_data_dir: Path) -> None:
    past = datetime.now(UTC) - timedelta(hours=1)
    p = TopicProgress(
        user_id="u1", topic_id="t1", domain="ai_agent",
        status=TopicStatus.REVIEW_DUE, next_review_at=past
    )
    data_store.topic_progress.save(p)

    due = get_due_reviews("u1", "ai_agent")
    assert len(due) == 1
    assert due[0].topic_id == "t1"


def test_get_due_reviews_skips_future(tmp_data_dir: Path) -> None:
    future = datetime.now(UTC) + timedelta(days=3)
    p = TopicProgress(
        user_id="u1", topic_id="t1", domain="ai_agent",
        status=TopicStatus.REVIEW_DUE, next_review_at=future
    )
    data_store.topic_progress.save(p)

    due = get_due_reviews("u1", "ai_agent")
    assert len(due) == 0


def test_get_due_reviews_skips_non_review_status(tmp_data_dir: Path) -> None:
    p = TopicProgress(
        user_id="u1", topic_id="t1", domain="ai_agent",
        status=TopicStatus.MASTERED, next_review_at=datetime.now(UTC) - timedelta(hours=1)
    )
    data_store.topic_progress.save(p)

    due = get_due_reviews("u1", "ai_agent")
    assert len(due) == 0


def test_schedule_review_sets_next_date(tmp_data_dir: Path) -> None:
    p = TopicProgress(user_id="u1", topic_id="t1", domain="ai_agent", attempts=0)
    data_store.topic_progress.save(p)

    updated = schedule_review(p)
    assert updated.status == TopicStatus.REVIEW_DUE
    assert updated.next_review_at is not None
    # First interval is 1 day
    assert updated.next_review_at > datetime.now(UTC)


def test_reset_to_ready(tmp_data_dir: Path) -> None:
    p = TopicProgress(user_id="u1", topic_id="t1", domain="ai_agent", status=TopicStatus.REVIEW_DUE)
    data_store.topic_progress.save(p)

    updated = reset_to_ready(p)
    assert updated.status == TopicStatus.READY


def test_generate_weekly_summary(tmp_data_dir: Path) -> None:
    p1 = TopicProgress(user_id="u1", topic_id="t1", domain="ai_agent", status=TopicStatus.MASTERED, mastery_score=90.0, attempts=2)
    p2 = TopicProgress(user_id="u1", topic_id="t2", domain="ai_agent", status=TopicStatus.REVIEW_DUE, mastery_score=50.0, attempts=1)
    data_store.topic_progress.save(p1)
    data_store.topic_progress.save(p2)

    e1 = EvaluationRecord(submission_id="s1", user_id="u1", topic_id="t1", domain="ai_agent", overall_score=90.0)
    e2 = EvaluationRecord(submission_id="s2", user_id="u1", topic_id="t2", domain="ai_agent", overall_score=50.0)
    data_store.evaluation_records.save(e1)
    data_store.evaluation_records.save(e2)

    summary = generate_weekly_summary("u1", "ai_agent")

    assert summary["total_topics"] == 2
    assert summary["mastered_topics"] == 1
    assert summary["review_due_topics"] == 1
    assert summary["mastery_rate"] == 0.5
    assert summary["avg_score"] == 70.0
    assert len(summary["topic_summaries"]) == 2
