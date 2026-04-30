"""Simple filesystem backups for the SQLite data store."""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path

from personal_learning_coach.config import load_config
from personal_learning_coach.data_store import DATABASE_FILENAME, database_path, initialize_database
from personal_learning_coach.monitoring import record_runtime_event


def create_backup() -> Path:
    config = load_config()
    initialize_database()
    config.backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = config.backup_dir / timestamp
    backup_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy2(database_path(), backup_dir / DATABASE_FILENAME)
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
    source = selected / DATABASE_FILENAME
    if not source.exists():
        raise FileNotFoundError(f"Backup does not contain {DATABASE_FILENAME}")

    config.data_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, database_path())
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
