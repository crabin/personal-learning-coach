"""CLI tests for coach command wiring."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from personal_learning_coach import coach, data_store
from personal_learning_coach.models import DomainEnrollment, DomainStatus, LearnerLevel, LearningPlan


def test_plan_command_passes_preferences(
    tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    captured: dict[str, object] = {}

    def fake_enroll_domain(user_id, domain, level, preferences=None, client=None):
        captured["user_id"] = user_id
        captured["domain"] = domain
        captured["level"] = level
        captured["preferences"] = preferences
        plan = LearningPlan(user_id=user_id, domain=domain, level=level)
        enrollment = DomainEnrollment(user_id=user_id, domain=domain, level=level, status=DomainStatus.ACTIVE)
        return enrollment, plan

    import personal_learning_coach.plan_generator as plan_generator

    monkeypatch.setattr(plan_generator, "enroll_domain", fake_enroll_domain)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "coach",
            "--user-id",
            "u1",
            "plan",
            "--domain",
            "ai_agent",
            "--target-level",
            "advanced",
            "--daily-minutes",
            "45",
            "--learning-style",
            "practice",
            "--delivery-time",
            "20:30",
            "--language",
            "zh",
            "--no-online-resources",
        ],
    )

    coach.main()

    prefs = captured["preferences"]
    assert isinstance(prefs, dict)
    assert prefs["target_level"] == "advanced"
    assert prefs["daily_minutes"] == 45
    assert prefs["learning_style"] == "practice"
    assert prefs["delivery_time"] == "20:30"
    assert prefs["language"] == "zh"
    assert prefs["allow_online_resources"] is False
    assert "Plan generated" in capsys.readouterr().out


def test_pause_command_updates_status(
    tmp_data_dir: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    enrollment = DomainEnrollment(user_id="u1", domain="ai_agent", status=DomainStatus.ACTIVE)
    data_store.domain_enrollments.save(enrollment)
    monkeypatch.setattr(sys, "argv", ["coach", "--user-id", "u1", "pause", "--domain", "ai_agent"])

    coach.main()

    saved = data_store.domain_enrollments.filter(user_id="u1", domain="ai_agent")
    assert saved[0].status == DomainStatus.PAUSED
    assert "paused" in capsys.readouterr().out.lower()
