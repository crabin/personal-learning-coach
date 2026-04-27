"""Tests for the migrations module."""

from __future__ import annotations

import json
from pathlib import Path

from personal_learning_coach.migrations import migrate_all, migrate_file


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
