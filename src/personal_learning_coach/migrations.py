"""Schema version upgrade logic for JSON data files."""

from __future__ import annotations

import json
import logging
from pathlib import Path

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
    """Run migrations on every JSON file in data_dir."""
    for json_file in data_dir.glob("*.json"):
        try:
            migrate_file(json_file)
        except Exception as exc:
            logger.error("Migration failed for %s: %s", json_file, exc)
