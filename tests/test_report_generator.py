"""Tests for report_generator."""

from __future__ import annotations

from pathlib import Path

from personal_learning_coach import data_store
from personal_learning_coach.models import (
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

    p = TopicProgress(user_id=user_id, topic_id=t1.topic_id, domain=domain, status=TopicStatus.MASTERED, mastery_score=88.0, attempts=2)
    data_store.topic_progress.save(p)

    ev = EvaluationRecord(submission_id="s1", user_id=user_id, topic_id=t1.topic_id, domain=domain, overall_score=88.0, llm_feedback="Excellent work.")
    data_store.evaluation_records.save(ev)


def test_generate_report_structure(tmp_data_dir: Path) -> None:
    _setup()
    report = generate_report("u1", "ai_agent")
    assert report["user_id"] == "u1"
    assert report["domain"] == "ai_agent"
    assert len(report["topic_rows"]) == 1
    assert report["topic_rows"][0].title == "Intro to LLMs"


def test_render_html_contains_key_fields(tmp_data_dir: Path) -> None:
    _setup()
    html = render_html("u1", "ai_agent")
    assert "Learning Report" in html
    assert "ai_agent" in html
    assert "Intro to LLMs" in html
    assert "mastered" in html


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
