"""Tests for evaluator and mastery_engine."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from personal_learning_coach import data_store
from personal_learning_coach.evaluator import _compute_overall, evaluate_submission
from personal_learning_coach.mastery_engine import apply_evaluation, recalculate_mastery
from personal_learning_coach.models import (
    DimensionScore,
    DomainEnrollment,
    DomainStatus,
    EvaluationRecord,
    LearnerLevel,
    LearningPlan,
    PushRecord,
    SubmissionRecord,
    TopicNode,
    TopicProgress,
    TopicStatus,
)


def _mock_client(response_text: str) -> MagicMock:
    client = MagicMock()
    msg = MagicMock()
    msg.content = [MagicMock(text=response_text)]
    client.messages.create.return_value = msg
    return client


def _eval_payload(score: float = 75.0) -> dict:
    return {
        "dimensions": {
            "concept_coverage": {"score": score, "feedback": "OK"},
            "understanding_depth": {"score": score, "feedback": "OK"},
            "logic_clarity": {"score": score, "feedback": "OK"},
            "practical_application": {"score": score, "feedback": "OK"},
        },
        "overall_feedback": "Good job.",
        "strengths": ["Clear"],
        "weaknesses": ["Shallow"],
        "missed_concepts": [],
        "improvement_suggestions": ["Go deeper"],
        "mastery_estimate": score / 100,
    }


# ---------------------------------------------------------------------------
# evaluator tests
# ---------------------------------------------------------------------------


def test_compute_overall_weighted() -> None:
    dims = {
        "concept_coverage": {"score": 80},
        "understanding_depth": {"score": 60},
        "logic_clarity": {"score": 90},
        "practical_application": {"score": 70},
    }
    # 0.30*80 + 0.25*60 + 0.25*90 + 0.20*70 = 24+15+22.5+14 = 75.5
    assert _compute_overall(dims) == 75.5


def test_evaluate_submission_persists(tmp_data_dir: Path) -> None:
    payload = _eval_payload(80.0)
    client = _mock_client(json.dumps(payload))

    sub = SubmissionRecord(
        user_id="u1", push_id="p1", topic_id="t1", domain="ai_agent",
        raw_answer="Transformers use attention."
    )
    push = PushRecord(
        user_id="u1", topic_id="t1", domain="ai_agent",
        theory="Theory...", practice_question="Q?", reflection_question="R?"
    )

    record = evaluate_submission(sub, push, client=client)

    assert record.overall_score == 80.0
    assert record.next_action == "continue"
    saved = data_store.evaluation_records.get(record.eval_id)
    assert saved is not None


def test_evaluate_submission_review_action(tmp_data_dir: Path) -> None:
    payload = _eval_payload(50.0)
    client = _mock_client(json.dumps(payload))

    sub = SubmissionRecord(
        user_id="u1", push_id="p1", topic_id="t1", domain="ai_agent", raw_answer="I'm not sure."
    )
    push = PushRecord(
        user_id="u1", topic_id="t1", domain="ai_agent",
        theory="Theory...", practice_question="Q?", reflection_question="R?"
    )
    record = evaluate_submission(sub, push, client=client)
    assert record.next_action == "review"


def test_evaluate_submission_consolidate_action(tmp_data_dir: Path) -> None:
    payload = _eval_payload(70.0)
    client = _mock_client(json.dumps(payload))

    sub = SubmissionRecord(
        user_id="u1", push_id="p1", topic_id="t1", domain="ai_agent", raw_answer="Somewhat clear."
    )
    push = PushRecord(
        user_id="u1", topic_id="t1", domain="ai_agent",
        theory="Theory...", practice_question="Q?", reflection_question="R?"
    )
    record = evaluate_submission(sub, push, client=client)
    assert record.next_action == "consolidate"


# ---------------------------------------------------------------------------
# mastery_engine tests
# ---------------------------------------------------------------------------


def test_recalculate_mastery_empty(tmp_data_dir: Path) -> None:
    assert recalculate_mastery("u1", "t1") == 0.0


def test_recalculate_mastery_averages_last_3(tmp_data_dir: Path) -> None:
    for score in [60.0, 80.0, 90.0, 40.0]:  # oldest first
        ev = EvaluationRecord(
            submission_id="s1", user_id="u1", topic_id="t1", domain="ai_agent",
            overall_score=score,
        )
        data_store.evaluation_records.save(ev)
    # Last 3: 40, 90, 80 → average = (40+90+80)/3 = 70.0
    mastery = recalculate_mastery("u1", "t1")
    assert 69.0 < mastery < 71.0


def test_apply_evaluation_mastered(tmp_data_dir: Path) -> None:
    t1 = TopicNode(title="T1", order=0)
    t2 = TopicNode(title="T2", order=1)
    plan = LearningPlan(user_id="u1", domain="ai_agent", level=LearnerLevel.BEGINNER, topics=[t1, t2])
    data_store.learning_plans.save(plan)

    progress = TopicProgress(user_id="u1", topic_id=t1.topic_id, domain="ai_agent", status=TopicStatus.PUSHED)
    data_store.topic_progress.save(progress)

    next_progress = TopicProgress(user_id="u1", topic_id=t2.topic_id, domain="ai_agent", status=TopicStatus.LOCKED)
    data_store.topic_progress.save(next_progress)

    ev = EvaluationRecord(
        submission_id="s1", user_id="u1", topic_id=t1.topic_id, domain="ai_agent",
        overall_score=85.0,
    )
    data_store.evaluation_records.save(ev)

    updated = apply_evaluation(ev, progress)
    assert updated.status == TopicStatus.MASTERED

    # Next topic should be unlocked
    next_p = data_store.topic_progress.filter(user_id="u1", topic_id=t2.topic_id)
    assert next_p[0].status == TopicStatus.READY


def test_apply_evaluation_review_due(tmp_data_dir: Path) -> None:
    progress = TopicProgress(user_id="u1", topic_id="t1", domain="ai_agent", status=TopicStatus.PUSHED)
    data_store.topic_progress.save(progress)

    ev = EvaluationRecord(
        submission_id="s1", user_id="u1", topic_id="t1", domain="ai_agent",
        overall_score=45.0,
    )
    data_store.evaluation_records.save(ev)

    updated = apply_evaluation(ev, progress)
    assert updated.status == TopicStatus.REVIEW_DUE
    assert updated.next_review_at is not None


def test_domain_completed_when_all_mastered(tmp_data_dir: Path) -> None:
    t1 = TopicNode(title="T1", order=0)
    plan = LearningPlan(user_id="u1", domain="ai_agent", level=LearnerLevel.BEGINNER, topics=[t1])
    data_store.learning_plans.save(plan)

    enrollment = DomainEnrollment(user_id="u1", domain="ai_agent", level=LearnerLevel.BEGINNER)
    data_store.domain_enrollments.save(enrollment)

    progress = TopicProgress(user_id="u1", topic_id=t1.topic_id, domain="ai_agent", status=TopicStatus.PUSHED)
    data_store.topic_progress.save(progress)

    ev = EvaluationRecord(
        submission_id="s1", user_id="u1", topic_id=t1.topic_id, domain="ai_agent",
        overall_score=95.0,
    )
    data_store.evaluation_records.save(ev)

    apply_evaluation(ev, progress)

    updated_enrollment = data_store.domain_enrollments.filter(user_id="u1", domain="ai_agent")
    assert updated_enrollment[0].status == DomainStatus.COMPLETED
