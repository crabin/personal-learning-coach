"""Tests for the migrations module."""

from __future__ import annotations

import json
from pathlib import Path

from personal_learning_coach.infrastructure import data_store
from personal_learning_coach.infrastructure.migrations import migrate_all, migrate_file
from personal_learning_coach.domain.models import LearnerLevel, LearningPlan, TopicNode, UserProfile


def test_migrate_file_skips_missing(tmp_path: Path) -> None:
    # Should not raise even if file doesn't exist
    migrate_file(tmp_path / "nonexistent.json")


def test_migrate_file_noop_when_current(tmp_path: Path) -> None:
    data = {"schema_version": 1, "records": {}}
    path = tmp_path / "test.json"
    path.write_text(json.dumps(data))
    migrate_file(path)
    result = json.loads(path.read_text())
    assert result["schema_version"] == 1


def test_migrate_all_processes_directory(tmp_path: Path) -> None:
    # Two JSON files, both already at current version
    for name in ["a.json", "b.json"]:
        (tmp_path / name).write_text(json.dumps({"schema_version": 1, "records": {}}))
    migrate_all(tmp_path)
    for name in ["a.json", "b.json"]:
        data = json.loads((tmp_path / name).read_text())
        assert data["schema_version"] == 1


def test_migrate_all_skips_non_json(tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_text("hello")
    migrate_all(tmp_path)  # should not raise


def test_migrate_all_imports_json_records_to_sqlite(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    profile = UserProfile(name="Alice")
    topic = TopicNode(title="Intro", order=0)
    plan = LearningPlan(
        user_id=profile.user_id,
        domain="ai_agent",
        level=LearnerLevel.BEGINNER,
        topics=[topic],
    )
    (tmp_path / "user_profiles.json").write_text(
        json.dumps({"schema_version": 1, "records": {profile.user_id: profile.model_dump(mode="json")}})
    )
    (tmp_path / "learning_plans.json").write_text(
        json.dumps({"schema_version": 1, "records": {plan.plan_id: plan.model_dump(mode="json")}})
    )

    migrate_all(tmp_path)
    migrate_all(tmp_path)

    profiles = data_store.user_profiles.all()
    plans = data_store.learning_plans.filter(user_id=profile.user_id, domain="ai_agent")
    assert len(profiles) == 1
    assert profiles[0].name == "Alice"
    assert len(plans) == 1
    assert plans[0].topics[0].title == "Intro"
