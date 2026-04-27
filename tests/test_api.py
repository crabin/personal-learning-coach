"""Integration tests for the FastAPI routes."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from personal_learning_coach.api.main import app
from personal_learning_coach import data_store
from personal_learning_coach.models import (
    DomainEnrollment,
    DomainStatus,
    LearnerLevel,
    LearningPlan,
    PushRecord,
    TopicNode,
    TopicProgress,
    TopicStatus,
)

client = TestClient(app)


def _mock_enroll(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch enroll_domain to avoid Claude API calls."""
    from personal_learning_coach import plan_generator

    def fake_enroll(user_id, domain, level, preferences=None, client=None):
        t = TopicNode(title="Mock Topic", order=0)
        plan = LearningPlan(user_id=user_id, domain=domain, level=level, topics=[t])
        data_store.learning_plans.save(plan)
        p = TopicProgress(user_id=user_id, topic_id=t.topic_id, domain=domain, status=TopicStatus.READY)
        data_store.topic_progress.save(p)
        enrollment = DomainEnrollment(
            user_id=user_id,
            domain=domain,
            level=level,
            status=DomainStatus.ACTIVE,
            target_level=preferences.get("target_level", level) if preferences else level,
            current_level=level,
            daily_minutes=preferences.get("daily_minutes", 60) if preferences else 60,
            learning_style=preferences.get("learning_style", "blended") if preferences else "blended",
            delivery_time=preferences.get("delivery_time", "09:00") if preferences else "09:00",
            language=preferences.get("language", "zh") if preferences else "zh",
            allow_online_resources=preferences.get("allow_online_resources", True)
            if preferences
            else True,
        )
        data_store.domain_enrollments.save(enrollment)
        return enrollment, plan

    monkeypatch.setattr(plan_generator, "enroll_domain", fake_enroll)


def test_health(tmp_data_dir: Path) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_enroll_domain(tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_enroll(monkeypatch)
    resp = client.post(
        "/domains/ai_agent/enroll",
        json={
            "user_id": "u1",
            "daily_minutes": 45,
            "learning_style": "practice",
            "delivery_time": "20:30",
            "language": "zh",
            "allow_online_resources": False,
            "target_level": "advanced",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["domain"] == "ai_agent"
    assert data["topic_count"] == 1
    assert data["daily_minutes"] == 45
    assert data["learning_style"] == "practice"
    assert data["delivery_time"] == "20:30"
    assert data["allow_online_resources"] is False
    assert data["target_level"] == "advanced"


def test_get_domain_status(tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_enroll(monkeypatch)
    client.post("/domains/ai_agent/enroll", json={"user_id": "u1"})
    resp = client.get("/domains/ai_agent/status", params={"user_id": "u1"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "active"
    assert data["total_topics"] == 1


def test_get_domain_status_not_found(tmp_data_dir: Path) -> None:
    resp = client.get("/domains/ai_agent/status", params={"user_id": "nobody"})
    assert resp.status_code == 404


def test_pause_domain(tmp_data_dir: Path) -> None:
    enrollment = DomainEnrollment(user_id="u1", domain="ai_agent", status=DomainStatus.ACTIVE)
    data_store.domain_enrollments.save(enrollment)

    resp = client.post("/domains/ai_agent/pause", json={"user_id": "u1"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "paused"


def test_resume_domain(tmp_data_dir: Path) -> None:
    enrollment = DomainEnrollment(user_id="u1", domain="ai_agent", status=DomainStatus.PAUSED)
    data_store.domain_enrollments.save(enrollment)

    resp = client.post("/domains/ai_agent/resume", json={"user_id": "u1"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"


def test_archive_domain(tmp_data_dir: Path) -> None:
    enrollment = DomainEnrollment(user_id="u1", domain="ai_agent", status=DomainStatus.COMPLETED)
    data_store.domain_enrollments.save(enrollment)

    resp = client.post("/domains/ai_agent/archive", json={"user_id": "u1"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "archived"


def test_delete_domain_requires_confirm(tmp_data_dir: Path) -> None:
    enrollment = DomainEnrollment(user_id="u1", domain="ai_agent", status=DomainStatus.ACTIVE)
    data_store.domain_enrollments.save(enrollment)

    resp = client.request("DELETE", "/domains/ai_agent", json={"user_id": "u1", "confirm": False})
    assert resp.status_code == 400


def test_delete_domain_removes_related_records(tmp_data_dir: Path) -> None:
    enrollment = DomainEnrollment(user_id="u1", domain="ai_agent", status=DomainStatus.ACTIVE)
    data_store.domain_enrollments.save(enrollment)
    topic = TopicNode(title="T1", order=0)
    plan = LearningPlan(user_id="u1", domain="ai_agent", level=LearnerLevel.BEGINNER, topics=[topic])
    data_store.learning_plans.save(plan)
    progress = TopicProgress(user_id="u1", topic_id=topic.topic_id, domain="ai_agent")
    data_store.topic_progress.save(progress)
    push = PushRecord(user_id="u1", topic_id=topic.topic_id, domain="ai_agent")
    data_store.push_records.save(push)

    resp = client.request("DELETE", "/domains/ai_agent", json={"user_id": "u1", "confirm": True})
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True
    assert data_store.domain_enrollments.filter(user_id="u1", domain="ai_agent") == []
    assert data_store.learning_plans.filter(user_id="u1", domain="ai_agent") == []
    assert data_store.topic_progress.filter(user_id="u1", domain="ai_agent") == []
    assert data_store.push_records.filter(user_id="u1", domain="ai_agent") == []


def test_trigger_push_no_plan(tmp_data_dir: Path) -> None:
    resp = client.post("/schedules/trigger", json={"user_id": "u1", "domain": "ai_agent"})
    assert resp.status_code == 200
    assert resp.json()["delivered"] is False


def test_get_report(tmp_data_dir: Path) -> None:
    resp = client.get("/reports/ai_agent", params={"user_id": "u1"})
    assert resp.status_code == 200
    assert "Learning Report" in resp.text


def test_submit_answer(tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from personal_learning_coach.models import EvaluationRecord

    push = PushRecord(
        user_id="u1", topic_id="t1", domain="ai_agent",
        theory="Theory.", practice_question="Q?", reflection_question="R?"
    )
    data_store.push_records.save(push)

    progress = TopicProgress(user_id="u1", topic_id="t1", domain="ai_agent", status=TopicStatus.PUSHED)
    data_store.topic_progress.save(progress)

    fake_eval = EvaluationRecord(
        submission_id="s1", user_id="u1", topic_id="t1", domain="ai_agent",
        overall_score=82.0, next_action="continue", llm_feedback="Great answer."
    )

    from personal_learning_coach.api.routes import submissions as sub_mod
    monkeypatch.setattr(sub_mod, "evaluate_submission", lambda *a, **kw: fake_eval)
    monkeypatch.setattr(sub_mod, "apply_evaluation", lambda *a, **kw: progress)

    resp = client.post("/submissions", json={
        "user_id": "u1",
        "push_id": push.push_id,
        "raw_answer": "My detailed answer here.",
        "practice_result": "Built a small prototype.",
        "parsing_notes": "Captured from a free-form text reply.",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["overall_score"] == 82.0
    assert data["next_action"] == "continue"

    saved = data_store.submission_records.filter(user_id="u1", push_id=push.push_id)
    assert len(saved) == 1
    assert saved[0].normalized_answer == "My detailed answer here."
    assert saved[0].practice_result == "Built a small prototype."


def test_submit_push_not_found(tmp_data_dir: Path) -> None:
    resp = client.post("/submissions", json={
        "user_id": "u1",
        "push_id": "nonexistent-push",
        "raw_answer": "Answer.",
    })
    assert resp.status_code == 404
