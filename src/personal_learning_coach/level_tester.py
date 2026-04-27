"""Baseline assessment: determine a learner's starting level in a domain."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import anthropic

from personal_learning_coach import data_store
from personal_learning_coach.models import AssessmentRecord, LearnerLevel
from personal_learning_coach.prompts.assessment import (
    ASSESSMENT_EVALUATE_PROMPT,
    ASSESSMENT_QUESTIONS_PROMPT,
    ASSESSMENT_SYSTEM,
    build_qa_pairs,
)

logger = logging.getLogger(__name__)

MODEL = "claude-haiku-4-5-20251001"


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def _chat(system: str, prompt: str, client: anthropic.Anthropic | None = None) -> str:
    cl = client or _client()
    response = cl.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text  # type: ignore[union-attr]


def _parse_json(text: str) -> Any:
    # Strip markdown code fences if present
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def generate_assessment_questions(
    domain: str, client: anthropic.Anthropic | None = None
) -> list[str]:
    """Ask Claude to generate assessment questions for the domain."""
    prompt = ASSESSMENT_QUESTIONS_PROMPT.format(domain=domain)
    raw = _chat(ASSESSMENT_SYSTEM, prompt, client)
    data = _parse_json(raw)
    return [q["text"] for q in data["questions"]]


def evaluate_answers(
    domain: str,
    questions: list[str],
    answers: list[str],
    client: anthropic.Anthropic | None = None,
) -> tuple[LearnerLevel, str]:
    """Ask Claude to evaluate answers and determine the learner's level."""
    qa_text = build_qa_pairs(questions, answers)
    prompt = ASSESSMENT_EVALUATE_PROMPT.format(domain=domain, qa_pairs=qa_text)
    raw = _chat(ASSESSMENT_SYSTEM, prompt, client)
    data = _parse_json(raw)
    level = LearnerLevel(data["level"])
    feedback = data.get("feedback", "")
    return level, feedback


def run_assessment(
    user_id: str,
    domain: str,
    answers: list[str],
    questions: list[str] | None = None,
    client: anthropic.Anthropic | None = None,
) -> AssessmentRecord:
    """Run a full baseline assessment and persist the result.

    Args:
        user_id: Learner's ID.
        domain: Learning domain (e.g. 'ai_agent').
        answers: Learner's answers to the assessment questions.
        questions: If provided, use these instead of generating new ones.
        client: Optional pre-configured Anthropic client (for testing).

    Returns:
        Persisted AssessmentRecord.
    """
    if questions is None:
        questions = generate_assessment_questions(domain, client)

    level, feedback = evaluate_answers(domain, questions, answers, client)

    record = AssessmentRecord(
        user_id=user_id,
        domain=domain,
        level=level,
        questions=questions,
        raw_answers=answers,
        llm_feedback=feedback,
    )
    data_store.assessment_records.save(record)
    logger.info("Assessment complete for user=%s domain=%s level=%s", user_id, domain, level)
    return record
