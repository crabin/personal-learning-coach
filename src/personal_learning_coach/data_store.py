"""JSON-based persistence layer. Single source of filesystem access."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from personal_learning_coach.models import (
    AssessmentRecord,
    DomainEnrollment,
    EvaluationRecord,
    LearningPlan,
    PushRecord,
    SubmissionRecord,
    TopicProgress,
    UserProfile,
)

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1

T = TypeVar("T", bound=BaseModel)


def _data_dir() -> Path:
    raw = os.environ.get("DATA_DIR", "./data")
    path = Path(raw)
    path.mkdir(parents=True, exist_ok=True)
    return path


class _Store:
    """Generic typed JSON store backed by a single file per entity collection."""

    def __init__(self, filename: str, model: type[T]) -> None:
        self._filename = filename
        self._model = model

    def _path(self) -> Path:
        return _data_dir() / self._filename

    def _load_raw(self) -> dict[str, Any]:
        path = self._path()
        if not path.exists():
            return {"schema_version": SCHEMA_VERSION, "records": {}}
        try:
            with path.open("r", encoding="utf-8") as f:
                data: dict[str, Any] = json.load(f)
            return data
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Failed to load %s: %s", path, exc)
            return {"schema_version": SCHEMA_VERSION, "records": {}}

    def _save_raw(self, data: dict[str, Any]) -> None:
        path = self._path()
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=_json_default, ensure_ascii=False)

    def all(self) -> list[T]:
        raw = self._load_raw()
        results: list[T] = []
        for record in raw.get("records", {}).values():
            try:
                results.append(self._model.model_validate(record))
            except Exception as exc:
                logger.warning("Skipping corrupt record in %s: %s", self._filename, exc)
        return results

    def get(self, record_id: str) -> T | None:
        raw = self._load_raw()
        entry = raw.get("records", {}).get(record_id)
        if entry is None:
            return None
        return self._model.model_validate(entry)

    def save(self, record: T) -> T:
        raw = self._load_raw()
        key = _primary_key(record)
        raw.setdefault("records", {})[key] = record.model_dump(mode="json")
        self._save_raw(raw)
        return record

    def delete(self, record_id: str) -> bool:
        raw = self._load_raw()
        records = raw.get("records", {})
        if record_id not in records:
            return False
        del records[record_id]
        self._save_raw(raw)
        return True

    def filter(self, **kwargs: Any) -> list[T]:
        return [r for r in self.all() if _matches(r, kwargs)]


def _json_default(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _primary_key(record: BaseModel) -> str:
    """Extract the primary key from a Pydantic model (first *_id field)."""
    for field in type(record).model_fields:
        if field.endswith("_id"):
            value = getattr(record, field)
            if isinstance(value, str):
                return value
    raise ValueError(f"No *_id field found on {type(record).__name__}")


def _matches(record: BaseModel, criteria: dict[str, Any]) -> bool:
    for key, value in criteria.items():
        if getattr(record, key, None) != value:
            return False
    return True


# ---------------------------------------------------------------------------
# Public store singletons
# ---------------------------------------------------------------------------

user_profiles = _Store("user_profiles.json", UserProfile)
domain_enrollments = _Store("domain_enrollments.json", DomainEnrollment)
learning_plans = _Store("learning_plans.json", LearningPlan)
topic_progress = _Store("topic_progress.json", TopicProgress)
push_records = _Store("push_records.json", PushRecord)
submission_records = _Store("submission_records.json", SubmissionRecord)
evaluation_records = _Store("evaluation_records.json", EvaluationRecord)
assessment_records = _Store("assessment_records.json", AssessmentRecord)
