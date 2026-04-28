"""Tests for report_generator."""

from __future__ import annotations

from pathlib import Path

from personal_learning_coach import data_store
from personal_learning_coach.models import (
    DomainEnrollment,
    DomainStatus,
    EvaluationRecord,
    LearnerLevel,
    LearningPlan,
    TopicNode,
    TopicProgress,
    TopicStatus,
)
from personal_learning_coach.report_generator import generate_report, render_html, save_report


def _setup(user_id: str = "u1", domain: str = "ai_agent") -> None:
    t1 = TopicNode(title="Intro to LLMs", order=0)
    plan = LearningPlan(user_id=user_id, domain=domain, level=LearnerLevel.BEGINNER, topics=[t1])
    data_store.learning_plans.save(plan)
    enrollment = DomainEnrollment(
        user_id=user_id,
        domain=domain,
        level=LearnerLevel.BEGINNER,
        status=DomainStatus.ACTIVE,
    )
    data_store.domain_enrollments.save(enrollment)

    p = TopicProgress(user_id=user_id, topic_id=t1.topic_id, domain=domain, status=TopicStatus.MASTERED, mastery_score=88.0, attempts=2)
    data_store.topic_progress.save(p)

    ev = EvaluationRecord(
        submission_id="s1",
        user_id=user_id,
        topic_id=t1.topic_id,
        domain=domain,
        overall_score=88.0,
        llm_feedback="Excellent work.",
        strengths=["Clear reasoning", "Strong fundamentals"],
        weaknesses=["Needs more system design detail"],
        missed_concepts=["retrieval orchestration"],
    )
    data_store.evaluation_records.save(ev)


def test_generate_report_structure(tmp_data_dir: Path) -> None:
    _setup()
    report = generate_report("u1", "ai_agent")
    assert report["user_id"] == "u1"
    assert report["domain"] == "ai_agent"
    assert len(report["topic_rows"]) == 1
    assert report["topic_rows"][0].title == "Intro to LLMs"
    assert report["insights"]["top_strengths"][0] == "Clear reasoning"
    assert report["insights"]["final_assessment_ready"] is True


def test_render_html_contains_key_fields(tmp_data_dir: Path) -> None:
    _setup()
    html = render_html("u1", "ai_agent")
    assert "Learning Report" in html
    assert "ai_agent" in html
    assert "Intro to LLMs" in html
    assert "mastered" in html
    assert "Stage Summary" in html
    assert "Clear reasoning" in html


def test_render_html_empty_data(tmp_data_dir: Path) -> None:
    html = render_html("u1", "ai_agent")
    assert "Learning Report" in html
    assert "No evaluations yet." in html


def test_save_report_writes_file(tmp_data_dir: Path) -> None:
    _setup()
    path = save_report("u1", "ai_agent")
    assert path.exists()
    content = path.read_text()
    assert "Intro to LLMs" in content


def test_generate_report_trend_and_summary(tmp_data_dir: Path) -> None:
    t1 = TopicNode(title="Topic A", order=0)
    plan = LearningPlan(user_id="u1", domain="ai_agent", level=LearnerLevel.BEGINNER, topics=[t1])
    data_store.learning_plans.save(plan)
    enrollment = DomainEnrollment(
        user_id="u1",
        domain="ai_agent",
        level=LearnerLevel.BEGINNER,
        status=DomainStatus.FINAL_ASSESSMENT_DUE,
    )
    data_store.domain_enrollments.save(enrollment)
    progress = TopicProgress(
        user_id="u1",
        topic_id=t1.topic_id,
        domain="ai_agent",
        status=TopicStatus.MASTERED,
        mastery_score=85.0,
        attempts=3,
    )
    data_store.topic_progress.save(progress)

    for i, score in enumerate([60.0, 75.0, 90.0], 1):
        ev = EvaluationRecord(
            submission_id=f"s{i}",
            user_id="u1",
            topic_id=t1.topic_id,
            domain="ai_agent",
            overall_score=score,
            llm_feedback=f"Feedback {i}",
            strengths=["clarity"],
            weaknesses=["depth"],
            missed_concepts=["tool use"],
        )
        data_store.evaluation_records.save(ev)

    report = generate_report("u1", "ai_agent")
    assert report["insights"]["score_trend"] == "improving"
    assert report["insights"]["final_assessment_ready"] is True
    assert "ready for final assessment" in report["insights"]["stage_summary"].lower()
