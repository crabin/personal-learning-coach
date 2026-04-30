"""Schema and data migration helpers."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, cast

from personal_learning_coach import data_store

logger = logging.getLogger(__name__)

CURRENT_VERSION = 1

# Maps (from_version, to_version) -> migration function
_MIGRATIONS: dict[tuple[int, int], object] = {}


def _register(from_v: int, to_v: int):  # type: ignore[no-untyped-def]
    def decorator(fn):  # type: ignore[no-untyped-def]
        _MIGRATIONS[(from_v, to_v)] = fn
        return fn

    return decorator


def migrate_file(path: Path) -> None:
    """Upgrade a single JSON data file to CURRENT_VERSION in-place."""
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    version = data.get("schema_version", 0)
    if version == CURRENT_VERSION:
        return

    while version < CURRENT_VERSION:
        next_v = version + 1
        fn = _MIGRATIONS.get((version, next_v))
        if fn is None:
            logger.warning("No migration from v%d to v%d for %s", version, next_v, path)
            break
        logger.info("Migrating %s: v%d -> v%d", path, version, next_v)
        data = fn(data)  # type: ignore[operator]
        data["schema_version"] = next_v
        version = next_v

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def migrate_all(data_dir: Path) -> None:
    """Run JSON file migrations and import known collections into SQLite."""
    data_store.initialize_database()
    for json_file in data_dir.glob("*.json"):
        try:
            migrate_file(json_file)
            import_json_collection(json_file)
        except Exception as exc:
            logger.error("Migration failed for %s: %s", json_file, exc)


def import_json_collection(path: Path) -> int:
    """Import one legacy JSON collection into SQLite.

    Unknown JSON files are ignored. Known records are validated through their
    Pydantic model and upserted, so this function is safe to run repeatedly.
    """
    store = data_store.JSON_COLLECTIONS.get(path.name)
    if store is None or not path.exists():
        return 0

    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    records = cast(dict[str, Any], raw.get("records", {}))

    imported = 0
    for record in records.values():
        try:
            store.save(store._model.model_validate(record))
            imported += 1
        except Exception as exc:
            logger.warning("Skipping invalid legacy record in %s: %s", path, exc)
    return imported
