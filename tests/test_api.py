"""Integration tests for the FastAPI routes."""

from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta
from io import BytesIO
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from personal_learning_coach.entrypoints.api.routes import auth as auth_routes
from personal_learning_coach.entrypoints.api.main import app
from personal_learning_coach.infrastructure import data_store
from personal_learning_coach.domain.models import (
    DomainEnrollment,
    DomainStatus,
    EvaluationRecord,
    LearnerLevel,
    LearningPlan,
    PushRecord,
    QuestionHistoryRecord,
    RegistrationCaptchaChallenge,
    RegistrationEmailChallenge,
    TopicNode,
    TopicProgress,
    TopicStatus,
    UserProfile,
    UserRole,
)
from personal_learning_coach.infrastructure.security import create_session, hash_password
from personal_learning_coach.infrastructure.registration_verification import hash_verification_code

client = TestClient(app)


def _auth_headers(user_id: str = "u1", role: UserRole = UserRole.LEARNER) -> dict[str, str]:
    existing = data_store.user_profiles.get(user_id)
    if existing is None:
        data_store.user_profiles.save(
            UserProfile(
                user_id=user_id,
                name=f"User {user_id}",
                email=f"{user_id}@example.com",
                password_hash=hash_password("password123"),
                role=role,
            )
        )
    elif existing.role != role:
        existing.role = role
        data_store.user_profiles.save(existing)
    token, _ = create_session(user_id)
    return {"Authorization": f"Bearer {token}"}


def _admin_headers(user_id: str = "admin") -> dict[str, str]:
    return _auth_headers(user_id, UserRole.ADMIN)


def _mock_enroll(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch enroll_domain to avoid Claude API calls."""
    from personal_learning_coach.application.learning import plan_generator

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


def test_register_login_me_and_logout(tmp_data_dir: Path) -> None:
    registered = client.post(
        "/auth/register",
        json={"name": "Learner", "email": "learner@example.com", "password": "password123"},
    )
    assert registered.status_code == 410
    assert data_store.user_profiles.all() == []


def test_register_captcha_returns_image_and_saves_challenge(tmp_data_dir: Path) -> None:
    resp = client.get("/auth/register/captcha")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["captcha_id"]
    assert payload["expires_in_seconds"] == 300
    assert payload["image_data_url"].startswith("data:image/png;base64,")

    encoded = payload["image_data_url"].split(",", 1)[1]
    with Image.open(BytesIO(base64.b64decode(encoded))) as image:
        assert image.format == "PNG"
        assert image.width >= 160
        assert image.height >= 60

    challenge = data_store.registration_captcha_challenges.get(payload["captcha_id"])
    assert challenge is not None


def test_register_start_rejects_wrong_captcha_without_email(
    tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sent: list[tuple[str, str]] = []
    monkeypatch.setattr(auth_routes, "send_registration_email_code", lambda email, code: sent.append((email, code)))
    challenge = RegistrationCaptchaChallenge(
        code_hash=hash_verification_code("ABCDE"),
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )
    data_store.registration_captcha_challenges.save(challenge)

    resp = client.post(
        "/auth/register/start",
        json={
            "name": "Learner",
            "email": "learner@example.com",
            "password": "password123",
            "captcha_id": challenge.captcha_id,
            "captcha_code": "WRONG",
        },
    )

    assert resp.status_code == 400
    assert sent == []
    assert data_store.user_profiles.all() == []


def test_register_start_requires_smtp_config(tmp_data_dir: Path) -> None:
    challenge = RegistrationCaptchaChallenge(
        code_hash=hash_verification_code("ABCDE"),
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )
    data_store.registration_captcha_challenges.save(challenge)

    resp = client.post(
        "/auth/register/start",
        json={
            "name": "Learner",
            "email": "learner@example.com",
            "password": "password123",
            "captcha_id": challenge.captcha_id,
            "captcha_code": "ABCDE",
        },
    )

    assert resp.status_code == 503
    assert data_store.user_profiles.all() == []


def test_register_start_sends_email_without_creating_user(
    tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure_smtp(monkeypatch)
    sent: list[tuple[str, str]] = []
    monkeypatch.setattr(auth_routes, "send_registration_email_code", lambda email, code: sent.append((email, code)))
    challenge = RegistrationCaptchaChallenge(
        code_hash=hash_verification_code("ABCDE"),
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )
    data_store.registration_captcha_challenges.save(challenge)

    resp = client.post(
        "/auth/register/start",
        json={
            "name": "Learner",
            "email": "learner@example.com",
            "password": "password123",
            "captcha_id": challenge.captcha_id,
            "captcha_code": "ABCDE",
        },
    )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["verification_id"]
    assert payload["email"] == "learner@example.com"
    assert payload["expires_in_seconds"] == 600
    assert sent == [("learner@example.com", sent[0][1])]
    assert len(sent[0][1]) == 6
    assert data_store.user_profiles.all() == []
    assert data_store.registration_email_challenges.get(payload["verification_id"]) is not None


def test_register_complete_validates_email_code_and_logs_in(
    tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure_smtp(monkeypatch)
    sent: list[str] = []
    monkeypatch.setattr(auth_routes, "send_registration_email_code", lambda _email, code: sent.append(code))
    captcha = RegistrationCaptchaChallenge(
        code_hash=hash_verification_code("ABCDE"),
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )
    data_store.registration_captcha_challenges.save(captcha)
    started = client.post(
        "/auth/register/start",
        json={
            "name": "Learner",
            "email": "learner@example.com",
            "password": "password123",
            "captcha_id": captcha.captcha_id,
            "captcha_code": "ABCDE",
        },
    )
    verification_id = started.json()["verification_id"]

    wrong = client.post(
        "/auth/register/complete",
        json={"verification_id": verification_id, "email_code": "000000"},
    )
    assert wrong.status_code == 400

    completed = client.post(
        "/auth/register/complete",
        json={"verification_id": verification_id, "email_code": sent[0]},
    )
    assert completed.status_code == 200
    assert completed.json()["user"]["role"] == "learner"
    token = completed.json()["token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "learner@example.com"
    assert data_store.registration_email_challenges.get(verification_id) is None

    duplicate = client.post(
        "/auth/register/complete",
        json={"verification_id": verification_id, "email_code": sent[0]},
    )
    assert duplicate.status_code == 400

    login = client.post(
        "/auth/login",
        json={"email": "learner@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    token = login.json()["token"]

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "learner@example.com"

    logout = client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout.status_code == 200
    expired = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert expired.status_code == 401


def test_register_complete_rejects_expired_email_code(tmp_data_dir: Path) -> None:
    challenge = RegistrationEmailChallenge(
        name="Learner",
        email="learner@example.com",
        password_hash=hash_password("password123"),
        code_hash=hash_verification_code("123456"),
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    data_store.registration_email_challenges.save(challenge)

    resp = client.post(
        "/auth/register/complete",
        json={"verification_id": challenge.verification_id, "email_code": "123456"},
    )

    assert resp.status_code == 400
    assert data_store.user_profiles.all() == []


def _configure_smtp(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMTP_HOST", "smtp.qq.com")
    monkeypatch.setenv("SMTP_PORT", "465")
    monkeypatch.setenv("SMTP_USE_SSL", "true")
    monkeypatch.setenv("SMTP_USE_TLS", "false")
    monkeypatch.setenv("SMTP_USERNAME", "sender@qq.com")
    monkeypatch.setenv("SMTP_PASSWORD", "authorization-code")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "sender@qq.com")


def test_learning_routes_require_login(tmp_data_dir: Path) -> None:
    resp = client.get("/domains")
    assert resp.status_code == 401


def test_user_cannot_access_another_users_report(tmp_data_dir: Path) -> None:
    resp = client.get(
        "/reports/ai_agent",
        headers=_auth_headers("u1"),
        params={"user_id": "u2"},
    )
    assert resp.status_code == 403


def test_enroll_domain(tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_enroll(monkeypatch)
    resp = client.post(
        "/domains/ai_agent/enroll",
        headers=_auth_headers("u1"),
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
    headers = _auth_headers("u1")
    client.post("/domains/ai_agent/enroll", headers=headers, json={"user_id": "u1"})
    resp = client.get("/domains/ai_agent/status", headers=headers, params={"user_id": "u1"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "active"
    assert data["total_topics"] == 1


def test_get_domain_status_not_found(tmp_data_dir: Path) -> None:
    resp = client.get(
        "/domains/ai_agent/status",
        headers=_auth_headers("u1"),
        params={"user_id": "nobody"},
    )
    assert resp.status_code == 403


def test_list_domains_returns_known_domain_options(tmp_data_dir: Path) -> None:
    data_store.domain_enrollments.save(DomainEnrollment(user_id="u1", domain="model_training"))
    data_store.learning_plans.save(
        LearningPlan(user_id="u1", domain="fullstack_development", level=LearnerLevel.BEGINNER)
    )

    resp = client.get("/domains", headers=_auth_headers("u1"))

    assert resp.status_code == 200
    data = resp.json()
    assert {"domain": "ai_agent", "label": "AI Agent"} not in data
    assert {"domain": "model_training", "label": "模型训练"} in data
    assert {"domain": "fullstack_development", "label": "全栈开发"} in data


def test_list_domains_returns_empty_for_user_without_domains(tmp_data_dir: Path) -> None:
    resp = client.get("/domains", headers=_auth_headers("new-user"))

    assert resp.status_code == 200
    assert resp.json() == []


def test_get_domain_summary_returns_real_goal_sidebar_data(tmp_data_dir: Path) -> None:
    topic1 = TopicNode(title="数据结构", order=0)
    topic2 = TopicNode(title="算法", order=1)
    plan = LearningPlan(
        user_id="u1",
        domain="ai_agent",
        level=LearnerLevel.INTERMEDIATE,
        topics=[topic1, topic2],
    )
    data_store.learning_plans.save(plan)
    enrollment = DomainEnrollment(
        user_id="u1",
        domain="ai_agent",
        level=LearnerLevel.INTERMEDIATE,
        current_level=LearnerLevel.INTERMEDIATE,
        target_level=LearnerLevel.ADVANCED,
        status=DomainStatus.ACTIVE,
    )
    data_store.domain_enrollments.save(enrollment)
    data_store.topic_progress.save(
        TopicProgress(
            user_id="u1",
            topic_id=topic1.topic_id,
            domain="ai_agent",
            status=TopicStatus.STUDYING,
            mastery_score=84,
        )
    )
    data_store.topic_progress.save(
        TopicProgress(
            user_id="u1",
            topic_id=topic2.topic_id,
            domain="ai_agent",
            status=TopicStatus.READY,
            mastery_score=62,
        )
    )

    resp = client.get(
        "/domains/ai_agent/summary",
        headers=_auth_headers("u1"),
        params={"user_id": "u1"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["domain"] == "ai_agent"
    assert data["mastery_percent"] == 0
    assert data["active_topic_title"] == "数据结构"
    assert data["active_topic_id"] == topic1.topic_id
    assert data["topic_progress"] == [
        {"title": "数据结构", "mastery_percent": 84},
        {"title": "算法", "mastery_percent": 62},
    ]


def test_pause_domain(tmp_data_dir: Path) -> None:
    enrollment = DomainEnrollment(user_id="u1", domain="ai_agent", status=DomainStatus.ACTIVE)
    data_store.domain_enrollments.save(enrollment)

    resp = client.post("/domains/ai_agent/pause", headers=_auth_headers("u1"), json={"user_id": "u1"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "paused"


def test_resume_domain(tmp_data_dir: Path) -> None:
    enrollment = DomainEnrollment(user_id="u1", domain="ai_agent", status=DomainStatus.PAUSED)
    data_store.domain_enrollments.save(enrollment)

    resp = client.post("/domains/ai_agent/resume", headers=_auth_headers("u1"), json={"user_id": "u1"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"


def test_archive_domain(tmp_data_dir: Path) -> None:
    enrollment = DomainEnrollment(user_id="u1", domain="ai_agent", status=DomainStatus.COMPLETED)
    data_store.domain_enrollments.save(enrollment)

    resp = client.post("/domains/ai_agent/archive", headers=_auth_headers("u1"), json={"user_id": "u1"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "archived"


def test_submit_final_assessment_marks_completed(tmp_data_dir: Path) -> None:
    enrollment = DomainEnrollment(user_id="u1", domain="ai_agent", status=DomainStatus.FINAL_ASSESSMENT_DUE)
    data_store.domain_enrollments.save(enrollment)

    resp = client.post(
        "/domains/ai_agent/final-assessment",
        headers=_auth_headers("u1"),
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
        headers=_auth_headers("u1"),
        json={"user_id": "u1", "passed": False, "feedback": "Needs more practice."},
    )
    assert resp.status_code == 409


def test_delete_domain_requires_confirm(tmp_data_dir: Path) -> None:
    enrollment = DomainEnrollment(user_id="u1", domain="ai_agent", status=DomainStatus.ACTIVE)
    data_store.domain_enrollments.save(enrollment)

    resp = client.request(
        "DELETE",
        "/domains/ai_agent",
        headers=_auth_headers("u1"),
        json={"user_id": "u1", "confirm": False},
    )
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
    history_path = tmp_data_dir / "question_history" / "u1" / "ai_agent" / "h1.json"
    history_path.parent.mkdir(parents=True)
    history_path.write_text("{}", encoding="utf-8")
    history = QuestionHistoryRecord(
        user_id="u1",
        domain="ai_agent",
        topic_id=topic.topic_id,
        push_id=push.push_id,
        session_id=push.push_id,
        json_path=str(history_path),
    )
    data_store.question_history.save(history)

    resp = client.request(
        "DELETE",
        "/domains/ai_agent",
        headers=_auth_headers("u1"),
        json={"user_id": "u1", "confirm": True},
    )
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True
    assert data_store.domain_enrollments.filter(user_id="u1", domain="ai_agent") == []
    assert data_store.learning_plans.filter(user_id="u1", domain="ai_agent") == []
    assert data_store.topic_progress.filter(user_id="u1", domain="ai_agent") == []
    assert data_store.push_records.filter(user_id="u1", domain="ai_agent") == []
    assert data_store.question_history.filter(user_id="u1", domain="ai_agent") == []
    assert not history_path.exists()


def test_trigger_push_no_plan(tmp_data_dir: Path) -> None:
    resp = client.post(
        "/schedules/trigger",
        headers=_auth_headers("u1"),
        json={"user_id": "u1", "domain": "ai_agent"},
    )
    assert resp.status_code == 200
    assert resp.json()["delivered"] is False


def test_trigger_push_returns_generated_question_content(
    tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from personal_learning_coach.application.learning import content_pusher
    from personal_learning_coach.domain.models import PushRecord

    fake_push = PushRecord(
        user_id="u1",
        topic_id="topic-1",
        domain="ai_agent",
        push_type="new_topic",
        theory="Theory body",
        practice_question="Practice prompt?",
        reflection_question="Reflection prompt?",
        content_snapshot={
            "basic_questions": ["Q1?", "Q2?", "Q3?"],
            "visual_url": "data/images/agent.png",
        },
    )
    monkeypatch.setattr(content_pusher, "push_today", lambda **_: fake_push)

    resp = client.post(
        "/schedules/trigger",
        headers=_auth_headers("u1"),
        json={"user_id": "u1", "domain": "ai_agent"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["delivered"] is True
    assert data["theory"] == "Theory body"
    assert data["basic_questions"] == ["Q1?", "Q2?", "Q3?"]
    assert data["practice_question"] == "Practice prompt?"
    assert data["reflection_question"] == "Reflection prompt?"
    assert data["visual_url"] == "/data/images/agent.png"


def test_trigger_push_falls_back_to_local_learning_visual(
    tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from personal_learning_coach.application.learning import content_pusher
    from personal_learning_coach.domain.models import PushRecord

    image_path = tmp_data_dir / "images" / "fallback.png"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image_path.write_bytes(b"fallback-image")

    fake_push = PushRecord(
        user_id="u1",
        topic_id="topic-2",
        domain="ai_agent",
        push_type="new_topic",
        theory="Theory body",
        practice_question="Practice prompt?",
        reflection_question="Reflection prompt?",
        content_snapshot={"basic_questions": ["Q1?", "Q2?", "Q3?"]},
    )
    monkeypatch.setattr(content_pusher, "push_today", lambda **_: fake_push)

    resp = client.post(
        "/schedules/trigger",
        headers=_auth_headers("u1"),
        json={"user_id": "u1", "domain": "ai_agent"},
    )

    assert resp.status_code == 200
    assert resp.json()["visual_url"] == "/data/images/fallback.png"


def test_data_images_route_serves_learning_visual(tmp_data_dir: Path) -> None:
    image_path = tmp_data_dir / "images" / "lesson.png"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image_path.write_bytes(b"fake-image")

    resp = client.get("/data/images/lesson.png")

    assert resp.status_code == 200
    assert resp.content == b"fake-image"
    assert resp.headers["cache-control"] == "public, max-age=86400, stale-while-revalidate=604800"


def test_data_images_route_can_serve_preview_variant(tmp_data_dir: Path) -> None:
    image_path = tmp_data_dir / "images" / "large.png"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    with Image.effect_noise((2400, 1400), 120).convert("RGB") as image:
        image.save(image_path, format="PNG")

    original_size = image_path.stat().st_size
    resp = client.get("/data/images/large.png", params={"variant": "preview"})

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/webp"
    assert len(resp.content) < original_size


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
    data_store.evaluation_records.save(
        EvaluationRecord(
            submission_id="s1",
            user_id="u1",
            topic_id=topic.topic_id,
            domain="ai_agent",
            overall_score=86.0,
            mastery_estimate=0.86,
            progress_applied=True,
        )
    )

    resp = client.get("/reports/ai_agent", headers=_auth_headers("u1"), params={"user_id": "u1"})

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/json")
    data = resp.json()
    assert data["domain"] == "ai_agent"
    assert data["enrollment_status"] == "active"
    assert data["summary"]["total_topics"] == 1
    assert data["topic_rows"][0]["title"] == "Prompt Debugging"
    assert data["topic_rows"][0]["status"] == "mastered"
    assert data["topic_rows"][0]["mastery_score"] == 86.0
    assert data["recent_evals"][0]["mastery_estimate"] == 0.86


def test_submit_answer(tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from personal_learning_coach.domain.models import EvaluationRecord

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

    from personal_learning_coach.entrypoints.api.routes import submissions as sub_mod
    monkeypatch.setattr(sub_mod, "evaluate_submission", lambda *a, **kw: fake_eval)

    resp = client.post(
        "/submissions",
        headers=_auth_headers("u1"),
        json={
            "user_id": "u1",
            "push_id": push.push_id,
            "raw_answer": "My detailed answer here.",
            "practice_result": "Built a small prototype.",
            "parsing_notes": "Captured from a free-form text reply.",
        },
    )
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
    history = data_store.question_history.filter(user_id="u1", push_id=push.push_id)
    assert len(history) == 1
    assert history[0].status == "evaluated"
    history_payload = json.loads(Path(history[0].json_path).read_text(encoding="utf-8"))
    assert history_payload["session_id"] == push.push_id
    assert history_payload["submission"]["raw_answer"] == "My detailed answer here."
    assert history_payload["evaluation"]["overall_score"] == 82.0
    updated_progress = data_store.topic_progress.filter(user_id="u1", topic_id="t1")
    assert updated_progress[0].status == TopicStatus.MASTERED
    assert updated_progress[0].mastery_score == 82.0
    enrollments = data_store.domain_enrollments.filter(user_id="u1", domain="ai_agent")
    assert enrollments[0].status == DomainStatus.ACTIVE


def test_submit_push_not_found(tmp_data_dir: Path) -> None:
    resp = client.post(
        "/submissions",
        headers=_auth_headers("u1"),
        json={
            "user_id": "u1",
            "push_id": "nonexistent-push",
            "raw_answer": "Answer.",
        },
    )
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
    history_dir = tmp_data_dir / "question_history" / "u1" / "ai_agent"
    history_dir.mkdir(parents=True)
    (history_dir / "history.json").write_text("{}", encoding="utf-8")

    resp = client.post("/admin/backup", headers=_admin_headers())

    assert resp.status_code == 200
    data = resp.json()
    assert data["file_count"] >= 1
    backup_path = Path(data["backup_path"])
    assert backup_path.exists()
    assert (backup_path / "personal_learning_coach.sqlite3").exists()
    assert (backup_path / "question_history" / "u1" / "ai_agent" / "history.json").exists()


def test_admin_user_management_lists_and_updates_users(tmp_data_dir: Path) -> None:
    _auth_headers("u1")

    listed = client.get("/admin/users", headers=_admin_headers())
    assert listed.status_code == 200
    users = listed.json()
    learner = next(item for item in users if item["user_id"] == "u1")
    assert learner["role"] == "learner"

    updated = client.patch(
        "/admin/users/u1",
        headers=_admin_headers(),
        json={"role": "admin", "is_active": False},
    )
    assert updated.status_code == 200
    assert updated.json()["role"] == "admin"
    assert updated.json()["is_active"] is False


def test_admin_can_manage_user_domain_progress(tmp_data_dir: Path) -> None:
    _auth_headers("u1")
    enrollment = DomainEnrollment(user_id="u1", domain="ai_agent", status=DomainStatus.ACTIVE)
    data_store.domain_enrollments.save(enrollment)
    progress = TopicProgress(user_id="u1", topic_id="t1", domain="ai_agent", status=TopicStatus.MASTERED)
    data_store.topic_progress.save(progress)

    domains = client.get("/admin/users/u1/domains", headers=_admin_headers())
    assert domains.status_code == 200
    assert domains.json()[0]["domain"] == "ai_agent"

    reset = client.post("/admin/users/u1/domains/ai_agent/reset", headers=_admin_headers())
    assert reset.status_code == 200
    assert data_store.topic_progress.filter(user_id="u1", domain="ai_agent") == []

    archive = client.post("/admin/users/u1/domains/ai_agent/archive", headers=_admin_headers())
    assert archive.status_code == 200
    assert data_store.domain_enrollments.filter(user_id="u1", domain="ai_agent")[0].status == DomainStatus.ARCHIVED


def test_learner_cannot_open_admin_routes(tmp_data_dir: Path) -> None:
    resp = client.get("/admin/users", headers=_auth_headers("u1"))
    assert resp.status_code == 403


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
