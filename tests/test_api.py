"""Integration tests for the FastAPI routes."""

from __future__ import annotations

from pathlib import Path

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
    assert "auth_enabled" in resp.json()


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


def test_submit_final_assessment_marks_completed(tmp_data_dir: Path) -> None:
    enrollment = DomainEnrollment(user_id="u1", domain="ai_agent", status=DomainStatus.FINAL_ASSESSMENT_DUE)
    data_store.domain_enrollments.save(enrollment)

    resp = client.post(
        "/domains/ai_agent/final-assessment",
        json={
            "user_id": "u1",
            "passed": True,
            "score": 91.0,
            "feedback": "Strong end-to-end performance.",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["passed"] is True

    saved = data_store.assessment_records.filter(user_id="u1", domain="ai_agent")
    assert len(saved) == 1
    assert saved[0].assessment_type == "final"
    assert saved[0].passed is True
    assert saved[0].structured_scores["final_score"] == 91.0


def test_submit_final_assessment_requires_ready_status(tmp_data_dir: Path) -> None:
    enrollment = DomainEnrollment(user_id="u1", domain="ai_agent", status=DomainStatus.ACTIVE)
    data_store.domain_enrollments.save(enrollment)

    resp = client.post(
        "/domains/ai_agent/final-assessment",
        json={"user_id": "u1", "passed": False, "feedback": "Needs more practice."},
    )
    assert resp.status_code == 409


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


def test_trigger_push_returns_generated_question_content(
    tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from personal_learning_coach import content_pusher
    from personal_learning_coach.models import PushRecord

    fake_push = PushRecord(
        user_id="u1",
        topic_id="topic-1",
        domain="ai_agent",
        push_type="new_topic",
        theory="Theory body",
        practice_question="Practice prompt?",
        reflection_question="Reflection prompt?",
        content_snapshot={"basic_questions": ["Q1?", "Q2?", "Q3?"]},
    )
    monkeypatch.setattr(content_pusher, "push_today", lambda **_: fake_push)

    resp = client.post("/schedules/trigger", json={"user_id": "u1", "domain": "ai_agent"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["delivered"] is True
    assert data["theory"] == "Theory body"
    assert data["basic_questions"] == ["Q1?", "Q2?", "Q3?"]
    assert data["practice_question"] == "Practice prompt?"
    assert data["reflection_question"] == "Reflection prompt?"


def test_get_report(tmp_data_dir: Path) -> None:
    topic = TopicNode(title="Prompt Debugging", order=0)
    plan = LearningPlan(user_id="u1", domain="ai_agent", level=LearnerLevel.BEGINNER, topics=[topic])
    data_store.learning_plans.save(plan)
    enrollment = DomainEnrollment(user_id="u1", domain="ai_agent", status=DomainStatus.ACTIVE)
    data_store.domain_enrollments.save(enrollment)
    progress = TopicProgress(
        user_id="u1",
        topic_id=topic.topic_id,
        domain="ai_agent",
        status=TopicStatus.MASTERED,
        mastery_score=86.0,
        attempts=2,
    )
    data_store.topic_progress.save(progress)

    resp = client.get("/reports/ai_agent", params={"user_id": "u1"})

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/json")
    data = resp.json()
    assert data["domain"] == "ai_agent"
    assert data["enrollment_status"] == "active"
    assert data["summary"]["total_topics"] == 1
    assert data["topic_rows"][0]["title"] == "Prompt Debugging"
    assert data["topic_rows"][0]["status"] == "mastered"
    assert data["topic_rows"][0]["mastery_score"] == 86.0


def test_submit_answer(tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from personal_learning_coach.models import EvaluationRecord

    push = PushRecord(
        user_id="u1", topic_id="t1", domain="ai_agent",
        theory="Theory.", practice_question="Q?", reflection_question="R?"
    )
    data_store.push_records.save(push)
    enrollment = DomainEnrollment(user_id="u1", domain="ai_agent", status=DomainStatus.AWAITING_SUBMISSION)
    data_store.domain_enrollments.save(enrollment)

    progress = TopicProgress(user_id="u1", topic_id="t1", domain="ai_agent", status=TopicStatus.PUSHED)
    data_store.topic_progress.save(progress)

    fake_eval = EvaluationRecord(
        submission_id="s1", user_id="u1", topic_id="t1", domain="ai_agent",
        overall_score=82.0, next_action="continue", llm_feedback="Great answer."
    )

    from personal_learning_coach.api.routes import submissions as sub_mod
    monkeypatch.setattr(sub_mod, "evaluate_submission", lambda *a, **kw: fake_eval)

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
    saved_eval = data_store.evaluation_records.get(fake_eval.eval_id)
    assert saved_eval is not None
    assert saved_eval.progress_applied is True
    updated_progress = data_store.topic_progress.filter(user_id="u1", topic_id="t1")
    assert updated_progress[0].status == TopicStatus.MASTERED
    assert updated_progress[0].mastery_score == 82.0
    enrollments = data_store.domain_enrollments.filter(user_id="u1", domain="ai_agent")
    assert enrollments[0].status == DomainStatus.ACTIVE


def test_submit_push_not_found(tmp_data_dir: Path) -> None:
    resp = client.post("/submissions", json={
        "user_id": "u1",
        "push_id": "nonexistent-push",
        "raw_answer": "Answer.",
    })
    assert resp.status_code == 404


def test_health_reports_degraded_when_telegram_config_incomplete(
    tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DELIVERY_MODE", "telegram")
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    resp = client.get("/health")

    assert resp.status_code == 200
    assert resp.json()["status"] == "degraded"
    assert len(resp.json()["issues"]) == 2


def test_admin_backup_creates_files(tmp_data_dir: Path) -> None:
    enrollment = DomainEnrollment(user_id="u1", domain="ai_agent", status=DomainStatus.ACTIVE)
    data_store.domain_enrollments.save(enrollment)

    resp = client.post("/admin/backup")

    assert resp.status_code == 200
    data = resp.json()
    assert data["file_count"] >= 1
    backup_path = Path(data["backup_path"])
    assert backup_path.exists()
    assert (backup_path / "personal_learning_coach.sqlite3").exists()


def test_admin_backup_requires_api_key_when_enabled(
    tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ADMIN_READ_TOKEN", "read-token")
    monkeypatch.setenv("ADMIN_WRITE_TOKEN", "write-token")

    no_header = client.post("/admin/backup")
    assert no_header.status_code == 401

    wrong_header = client.post("/admin/backup", headers={"x-api-key": "wrong"})
    assert wrong_header.status_code == 401

    read_only = client.post("/admin/backup", headers={"x-api-key": "read-token"})
    assert read_only.status_code == 401

    ok = client.post("/admin/backup", headers={"x-api-key": "write-token"})
    assert ok.status_code == 200


def test_admin_runtime_events_lists_backup_and_auth_events(
    tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ADMIN_READ_TOKEN", "read-token")
    monkeypatch.setenv("ADMIN_WRITE_TOKEN", "write-token")

    client.post("/admin/backup", headers={"x-api-key": "wrong"})
    client.post("/admin/backup", headers={"x-api-key": "write-token"})

    resp = client.get("/admin/runtime-events", headers={"x-api-key": "read-token"})

    assert resp.status_code == 200
    data = resp.json()
    categories = [item["category"] for item in data]
    assert "auth" in categories
    assert "backup" in categories


def test_admin_alerts_surface_auth_failures(tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADMIN_READ_TOKEN", "read-token")
    monkeypatch.setenv("ADMIN_WRITE_TOKEN", "write-token")

    client.post("/admin/backup", headers={"x-api-key": "wrong"})
    resp = client.get("/admin/alerts", headers={"x-api-key": "read-token"})

    assert resp.status_code == 200
    alerts = resp.json()
    assert any(alert["category"] == "auth" for alert in alerts)


def test_admin_restore_recovers_deleted_data(tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADMIN_READ_TOKEN", "read-token")
    monkeypatch.setenv("ADMIN_WRITE_TOKEN", "write-token")
    enrollment = DomainEnrollment(user_id="u1", domain="ai_agent", status=DomainStatus.ACTIVE)
    data_store.domain_enrollments.save(enrollment)

    backup = client.post("/admin/backup", headers={"x-api-key": "write-token"})
    assert backup.status_code == 200
    backup_path = backup.json()["backup_path"]

    for record in data_store.domain_enrollments.all():
        data_store.domain_enrollments.delete(record.enrollment_id)
    assert data_store.domain_enrollments.all() == []

    restore = client.post(
        "/admin/restore",
        headers={"x-api-key": "write-token"},
        json={"backup_path": backup_path},
    )
    assert restore.status_code == 200
    restored = data_store.domain_enrollments.filter(user_id="u1", domain="ai_agent")
    assert len(restored) == 1


def test_unhandled_exception_records_runtime_event(tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADMIN_READ_TOKEN", "read-token")
    failing_client = TestClient(app, raise_server_exceptions=False)

    boom = failing_client.get("/boom")
    assert boom.status_code == 500

    events = failing_client.get("/admin/runtime-events", headers={"x-api-key": "read-token"})
    assert events.status_code == 200
    assert any(item["category"] == "exception" for item in events.json())
