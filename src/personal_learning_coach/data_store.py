"""SQLite-backed persistence layer. Single source of structured data access."""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from personal_learning_coach.models import (
    AssessmentRecord,
    AuthSession,
    DomainEnrollment,
    EvaluationRecord,
    LearningPlan,
    PushRecord,
    QuestionHistoryRecord,
    RegistrationCaptchaChallenge,
    RegistrationEmailChallenge,
    RuntimeEvent,
    SubmissionRecord,
    TopicProgress,
    UserProfile,
)

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1
DATABASE_FILENAME = "personal_learning_coach.sqlite3"
INDEXED_FIELDS = {
    "user_id",
    "domain",
    "topic_id",
    "push_id",
    "submission_id",
    "session_id",
    "status",
    "level",
    "category",
    "created_at",
    "updated_at",
    "scheduled_at",
    "delivered_at",
    "submitted_at",
    "evaluated_at",
    "generated_at",
    "enrolled_at",
}

T = TypeVar("T", bound=BaseModel)


def _data_dir() -> Path:
    raw = os.environ.get("DATA_DIR", "./data")
    path = Path(raw)
    path.mkdir(parents=True, exist_ok=True)
    return path


def database_path() -> Path:
    """Return the active SQLite database path."""
    return _data_dir() / DATABASE_FILENAME


def initialize_database() -> None:
    """Create base schema metadata and tables for every known collection."""
    with _connect() as conn:
        _ensure_schema_meta(conn)
        for table in STORE_MODELS:
            _ensure_table(conn, table)


class _Store(Generic[T]):
    """Generic typed store backed by one SQLite table per entity collection."""

    def __init__(self, filename: str, model: type[T]) -> None:
        self._filename = filename
        self._table = _table_name(filename)
        self._model = model

    def all(self) -> list[T]:
        with _connect() as conn:
            _ensure_schema_meta(conn)
            _ensure_table(conn, self._table)
            rows = conn.execute(
                f"SELECT payload_json FROM {self._table} ORDER BY rowid"
            ).fetchall()
        return self._records_from_rows(rows)

    def get(self, record_id: str) -> T | None:
        with _connect() as conn:
            _ensure_schema_meta(conn)
            _ensure_table(conn, self._table)
            row = conn.execute(
                f"SELECT payload_json FROM {self._table} WHERE record_id = ?",
                (record_id,),
            ).fetchone()
        if row is None:
            return None
        return self._model.model_validate(json.loads(str(row["payload_json"])))

    def save(self, record: T) -> T:
        key = _primary_key(record)
        payload = record.model_dump(mode="json")
        columns = _indexed_values(payload)
        with _connect() as conn:
            _ensure_schema_meta(conn)
            _ensure_table(conn, self._table)
            conn.execute(
                f"""
                INSERT INTO {self._table} (
                    record_id, payload_json, user_id, domain, topic_id, push_id,
                    submission_id, status, level, category, created_at, updated_at,
                    scheduled_at, delivered_at, submitted_at, evaluated_at,
                    generated_at, enrolled_at, session_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(record_id) DO UPDATE SET
                    payload_json = excluded.payload_json,
                    user_id = excluded.user_id,
                    domain = excluded.domain,
                    topic_id = excluded.topic_id,
                    push_id = excluded.push_id,
                    submission_id = excluded.submission_id,
                    status = excluded.status,
                    level = excluded.level,
                    category = excluded.category,
                    created_at = excluded.created_at,
                    updated_at = excluded.updated_at,
                    scheduled_at = excluded.scheduled_at,
                    delivered_at = excluded.delivered_at,
                    submitted_at = excluded.submitted_at,
                    evaluated_at = excluded.evaluated_at,
                    generated_at = excluded.generated_at,
                    enrolled_at = excluded.enrolled_at,
                    session_id = excluded.session_id
                """,
                (
                    key,
                    json.dumps(payload, ensure_ascii=False),
                    columns.get("user_id"),
                    columns.get("domain"),
                    columns.get("topic_id"),
                    columns.get("push_id"),
                    columns.get("submission_id"),
                    columns.get("status"),
                    columns.get("level"),
                    columns.get("category"),
                    columns.get("created_at"),
                    columns.get("updated_at"),
                    columns.get("scheduled_at"),
                    columns.get("delivered_at"),
                    columns.get("submitted_at"),
                    columns.get("evaluated_at"),
                    columns.get("generated_at"),
                    columns.get("enrolled_at"),
                    columns.get("session_id"),
                ),
            )
        return record

    def delete(self, record_id: str) -> bool:
        with _connect() as conn:
            _ensure_schema_meta(conn)
            _ensure_table(conn, self._table)
            cursor = conn.execute(f"DELETE FROM {self._table} WHERE record_id = ?", (record_id,))
        return cursor.rowcount > 0

    def filter(self, **kwargs: Any) -> list[T]:
        if not kwargs:
            return self.all()
        if not set(kwargs).issubset(INDEXED_FIELDS):
            return [record for record in self.all() if _matches(record, kwargs)]

        clauses = [f"{key} = ?" for key in kwargs]
        params = tuple(_sqlite_value(value) for value in kwargs.values())
        with _connect() as conn:
            _ensure_schema_meta(conn)
            _ensure_table(conn, self._table)
            rows = conn.execute(
                f"SELECT payload_json FROM {self._table} WHERE {' AND '.join(clauses)} ORDER BY rowid",
                params,
            ).fetchall()
        return self._records_from_rows(rows)

    def _records_from_rows(self, rows: list[sqlite3.Row]) -> list[T]:
        results: list[T] = []
        for row in rows:
            try:
                payload = json.loads(str(row["payload_json"]))
                results.append(self._model.model_validate(payload))
            except Exception as exc:
                logger.warning("Skipping corrupt record in %s: %s", self._filename, exc)
        return results


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(database_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _ensure_schema_meta(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        INSERT INTO schema_meta (key, value)
        VALUES ('schema_version', ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (str(SCHEMA_VERSION),),
    )


def _ensure_table(conn: sqlite3.Connection, table: str) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table} (
            record_id TEXT PRIMARY KEY,
            payload_json TEXT NOT NULL,
            user_id TEXT,
            domain TEXT,
            topic_id TEXT,
            push_id TEXT,
            submission_id TEXT,
            status TEXT,
            level TEXT,
            category TEXT,
            created_at TEXT,
            updated_at TEXT,
            scheduled_at TEXT,
            delivered_at TEXT,
            submitted_at TEXT,
            evaluated_at TEXT,
            generated_at TEXT,
            enrolled_at TEXT,
            session_id TEXT
        )
        """
    )
    _ensure_column(conn, table, "session_id")
    for field in ("user_id", "domain", "topic_id", "status", "category", "session_id"):
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_{field} ON {table} ({field})")
    conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_user_domain ON {table} (user_id, domain)")


def _ensure_column(conn: sqlite3.Connection, table: str, column: str) -> None:
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} TEXT")


def _table_name(filename: str) -> str:
    return filename.removesuffix(".json")


def _indexed_values(payload: dict[str, Any]) -> dict[str, str | None]:
    return {field: _sqlite_value(payload.get(field)) for field in INDEXED_FIELDS}


def _sqlite_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)


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


STORE_MODELS: dict[str, type[BaseModel]] = {
    "user_profiles": UserProfile,
    "auth_sessions": AuthSession,
    "registration_captcha_challenges": RegistrationCaptchaChallenge,
    "registration_email_challenges": RegistrationEmailChallenge,
    "domain_enrollments": DomainEnrollment,
    "learning_plans": LearningPlan,
    "topic_progress": TopicProgress,
    "push_records": PushRecord,
    "question_history": QuestionHistoryRecord,
    "submission_records": SubmissionRecord,
    "evaluation_records": EvaluationRecord,
    "assessment_records": AssessmentRecord,
    "runtime_events": RuntimeEvent,
}

JSON_COLLECTIONS: dict[str, _Store[BaseModel]] = {
    f"{table}.json": _Store(f"{table}.json", model) for table, model in STORE_MODELS.items()
}

# ---------------------------------------------------------------------------
# Public store singletons
# ---------------------------------------------------------------------------

user_profiles = _Store("user_profiles.json", UserProfile)
auth_sessions = _Store("auth_sessions.json", AuthSession)
registration_captcha_challenges = _Store(
    "registration_captcha_challenges.json", RegistrationCaptchaChallenge
)
registration_email_challenges = _Store(
    "registration_email_challenges.json", RegistrationEmailChallenge
)
domain_enrollments = _Store("domain_enrollments.json", DomainEnrollment)
learning_plans = _Store("learning_plans.json", LearningPlan)
topic_progress = _Store("topic_progress.json", TopicProgress)
push_records = _Store("push_records.json", PushRecord)
question_history = _Store("question_history.json", QuestionHistoryRecord)
submission_records = _Store("submission_records.json", SubmissionRecord)
evaluation_records = _Store("evaluation_records.json", EvaluationRecord)
assessment_records = _Store("assessment_records.json", AssessmentRecord)
runtime_events = _Store("runtime_events.json", RuntimeEvent)
