"""Simple filesystem backups for JSON data stores."""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path

from personal_learning_coach.config import load_config
from personal_learning_coach.monitoring import record_runtime_event


def create_backup() -> Path:
    config = load_config()
    config.backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = config.backup_dir / timestamp
    backup_dir.mkdir(parents=True, exist_ok=True)

    for json_file in config.data_dir.glob("*.json"):
        shutil.copy2(json_file, backup_dir / json_file.name)
    record_runtime_event(
        level="info",
        category="backup",
        message="Backup created",
        details={"backup_path": str(backup_dir)},
    )
    return backup_dir


def restore_backup(backup_path: str | None = None) -> Path:
    config = load_config()
    selected = Path(backup_path) if backup_path else _latest_backup_dir(config.backup_dir)
    if selected is None or not selected.exists():
        raise FileNotFoundError("No backup directory available to restore")

    config.data_dir.mkdir(parents=True, exist_ok=True)
    for json_file in selected.glob("*.json"):
        shutil.copy2(json_file, config.data_dir / json_file.name)
    record_runtime_event(
        level="info",
        category="restore",
        message="Backup restored",
        details={"backup_path": str(selected)},
    )
    return selected


def _latest_backup_dir(backups_root: Path) -> Path | None:
    if not backups_root.exists():
        return None
    candidates = [path for path in backups_root.iterdir() if path.is_dir()]
    if not candidates:
        return None
    return sorted(candidates)[-1]
