"""Persist question, answer, and evaluation history as JSON artifacts."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from personal_learning_coach import data_store
from personal_learning_coach.models import EvaluationRecord, PushRecord, QuestionHistoryRecord, SubmissionRecord


def record_generated_push(push: PushRecord, topic_title: str = "") -> QuestionHistoryRecord:
    """Create or update the JSON history artifact for a generated push."""
    payload = _base_payload(push, topic_title)
    return _write_history(push, payload, status="generated")


def record_submission_evaluation(
    push: PushRecord,
    submission: SubmissionRecord,
    evaluation: EvaluationRecord,
) -> QuestionHistoryRecord:
    """Attach the learner answer and evaluation to the push history artifact."""
    existing = _load_payload(push)
    payload = existing or _base_payload(push)
    payload["submission"] = submission.model_dump(mode="json")
    payload["evaluation"] = evaluation.model_dump(mode="json")
    payload["status"] = "evaluated"
    payload["updated_at"] = datetime.now(UTC).isoformat()
    return _write_history(push, payload, status="evaluated")


def previous_questions(user_id: str, domain: str, limit: int = 20) -> list[str]:
    """Return recent question text for prompt de-duplication."""
    records = sorted(
        data_store.question_history.filter(user_id=user_id, domain=domain),
        key=lambda item: item.updated_at,
        reverse=True,
    )
    questions: list[str] = []
    for record in records:
        payload = _read_json(Path(record.json_path))
        for question in _questions_from_payload(payload):
            if question and question not in questions:
                questions.append(question)
            if len(questions) >= limit:
                return questions
    return questions


def _base_payload(push: PushRecord, topic_title: str = "") -> dict[str, Any]:
    return {
        "session_id": push.push_id,
        "user_id": push.user_id,
        "domain": push.domain,
        "topic_id": push.topic_id,
        "topic_title": topic_title,
        "push": push.model_dump(mode="json"),
        "questions": {
            "basic_questions": push.content_snapshot.get("basic_questions", []),
            "practice_question": push.practice_question,
            "reflection_question": push.reflection_question,
        },
        "submission": None,
        "evaluation": None,
        "status": "generated",
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
    }


def _write_history(push: PushRecord, payload: dict[str, Any], status: str) -> QuestionHistoryRecord:
    path = _history_path(push)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    existing = data_store.question_history.filter(user_id=push.user_id, push_id=push.push_id)
    record = existing[0] if existing else QuestionHistoryRecord(
        user_id=push.user_id,
        domain=push.domain,
        topic_id=push.topic_id,
        push_id=push.push_id,
        session_id=push.push_id,
        json_path=str(path),
    )
    record.status = status
    record.json_path = str(path)
    record.updated_at = datetime.now(UTC)
    return data_store.question_history.save(record)


def _load_payload(push: PushRecord) -> dict[str, Any] | None:
    records = data_store.question_history.filter(user_id=push.user_id, push_id=push.push_id)
    if not records:
        return None
    return _read_json(Path(records[0].json_path))


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return raw if isinstance(raw, dict) else {}


def _questions_from_payload(payload: dict[str, Any]) -> list[str]:
    questions = payload.get("questions", {})
    if not isinstance(questions, dict):
        return []
    basic = questions.get("basic_questions", [])
    values = [str(item).strip() for item in basic if str(item).strip()] if isinstance(basic, list) else []
    for key in ("practice_question", "reflection_question"):
        value = str(questions.get(key, "")).strip()
        if value:
            values.append(value)
    return values


def _history_path(push: PushRecord) -> Path:
    safe_domain = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in push.domain)
    data_dir = Path(os.environ.get("DATA_DIR", "./data"))
    return data_dir / "question_history" / push.user_id / safe_domain / f"{push.push_id}.json"
