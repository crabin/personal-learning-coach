"""Baseline assessment: determine a learner's starting level in a domain."""

from __future__ import annotations

import json
import logging
from typing import Any, cast

from personal_learning_coach.infrastructure import data_store
from personal_learning_coach.infrastructure.llm_client import generate_text
from personal_learning_coach.domain.models import AssessmentRecord, LearnerLevel
from personal_learning_coach.prompts import (
    ASSESSMENT_EVALUATE_PROMPT,
    ASSESSMENT_QUESTIONS_PROMPT,
    ASSESSMENT_SYSTEM,
    build_qa_pairs,
)

logger = logging.getLogger(__name__)


def _chat(system: str, prompt: str, client: Any | None = None) -> str:
    return generate_text(
        system=system,
        prompt=prompt,
        max_tokens=2048,
        client=client,
    )


def _parse_json(text: str) -> Any:
    # Strip markdown code fences if present
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def _evaluate_answers_payload(
    domain: str,
    questions: list[str],
    answers: list[str],
    client: Any | None = None,
) -> dict[str, Any]:
    qa_text = build_qa_pairs(questions, answers)
    prompt = ASSESSMENT_EVALUATE_PROMPT.format(domain=domain, qa_pairs=qa_text)
    raw = _chat(ASSESSMENT_SYSTEM, prompt, client)
    return cast(dict[str, Any], _parse_json(raw))


def generate_assessment_questions(
    domain: str, client: Any | None = None
) -> list[str]:
    """Ask the LLM to generate assessment questions for the domain."""
    prompt = ASSESSMENT_QUESTIONS_PROMPT.format(domain=domain)
    raw = _chat(ASSESSMENT_SYSTEM, prompt, client)
    data = cast(dict[str, Any], _parse_json(raw))
    return [q["text"] for q in data["questions"]]


def evaluate_answers(
    domain: str,
    questions: list[str],
    answers: list[str],
    client: Any | None = None,
) -> tuple[LearnerLevel, str]:
    """Ask the LLM to evaluate answers and determine the learner's level."""
    data = _evaluate_answers_payload(domain, questions, answers, client)
    level = LearnerLevel(data["level"])
    feedback = data.get("feedback", "")
    return level, feedback


def run_assessment(
    user_id: str,
    domain: str,
    answers: list[str],
    questions: list[str] | None = None,
    client: Any | None = None,
) -> AssessmentRecord:
    """Run a full baseline assessment and persist the result.

    Args:
        user_id: Learner's ID.
        domain: Learning domain (e.g. 'ai_agent').
        answers: Learner's answers to the assessment questions.
        questions: If provided, use these instead of generating new ones.
        client: Optional pre-configured OpenAI client (for testing).

    Returns:
        Persisted AssessmentRecord.
    """
    if questions is None:
        questions = generate_assessment_questions(domain, client)

    payload = _evaluate_answers_payload(domain, questions, answers, client)
    level = LearnerLevel(payload["level"])
    feedback = payload.get("feedback", "")

    record = AssessmentRecord(
        user_id=user_id,
        domain=domain,
        level=level,
        questions=questions,
        raw_answers=answers,
        confidence=float(payload.get("confidence", 0.0)),
        strengths=payload.get("strengths", []),
        weaknesses=payload.get("weaknesses", payload.get("gaps", [])),
        structured_scores=payload.get("structured_scores", {}),
        recommended_plan_style=payload.get("recommended_plan_style", "blended"),
        llm_feedback=feedback,
    )
    data_store.assessment_records.save(record)
    logger.info("Assessment complete for user=%s domain=%s level=%s", user_id, domain, level)
    return record
