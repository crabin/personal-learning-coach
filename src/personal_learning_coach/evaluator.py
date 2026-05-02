"""Evaluate learner submissions using a 4-dimension rubric via Claude."""

from __future__ import annotations

import json
import logging
from typing import Any, cast

from personal_learning_coach import data_store
from personal_learning_coach.llm_client import generate_text
from personal_learning_coach.models import (
    DimensionScore,
    EvaluationRecord,
    LearningPlan,
    PushRecord,
    SubmissionRecord,
)
from personal_learning_coach.prompts import EVAL_PROMPT, EVAL_SYSTEM

logger = logging.getLogger(__name__)

DIMENSION_WEIGHTS = {
    "concept_coverage": 0.30,
    "understanding_depth": 0.25,
    "logic_clarity": 0.25,
    "practical_application": 0.20,
}


def _parse_json(text: str) -> Any:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def _compute_overall(dims: dict[str, dict[str, Any]]) -> float:
    total = 0.0
    for name, weight in DIMENSION_WEIGHTS.items():
        score = dims.get(name, {}).get("score", 0)
        total += weight * score
    return round(total, 2)


def evaluate_submission(
    submission: SubmissionRecord,
    push: PushRecord,
    client: Any | None = None,
) -> EvaluationRecord:
    """Evaluate a submission against its push context.

    Args:
        submission: The learner's submission.
        push: The push that prompted the submission.
        client: Optional LLM client or test double.

    Returns:
        Persisted EvaluationRecord.
    """
    # Resolve topic title from the plan
    plans: list[LearningPlan] = data_store.learning_plans.filter(
        user_id=submission.user_id, domain=submission.domain
    )
    topic_title = submission.topic_id
    if plans:
        plan = plans[0]
        for t in plan.topics:
            if t.topic_id == submission.topic_id:
                topic_title = t.title
                break

    prompt = EVAL_PROMPT.format(
        domain=submission.domain,
        topic_title=topic_title,
        theory=push.theory,
        practice_question=push.practice_question,
        raw_answer=submission.raw_answer,
    )
    raw = generate_text(
        system=EVAL_SYSTEM,
        prompt=prompt,
        max_tokens=2048,
        client=client,
    )
    data = cast(dict[str, Any], _parse_json(raw))

    dims_raw: dict[str, dict[str, Any]] = data["dimensions"]
    dimension_scores = [
        DimensionScore(
            name=name,
            weight=DIMENSION_WEIGHTS[name],
            score=dims_raw[name]["score"],
            feedback=dims_raw[name].get("feedback", ""),
        )
        for name in DIMENSION_WEIGHTS
        if name in dims_raw
    ]

    overall = _compute_overall(dims_raw)

    # Determine next action based on score
    if overall >= 80:
        next_action = "continue"
    elif overall >= 60:
        next_action = "consolidate"
    else:
        next_action = "review"

    record = EvaluationRecord(
        submission_id=submission.submission_id,
        user_id=submission.user_id,
        topic_id=submission.topic_id,
        domain=submission.domain,
        dimension_scores=dimension_scores,
        overall_score=overall,
        llm_feedback=data.get("overall_feedback", ""),
        strengths=data.get("strengths", []),
        weaknesses=data.get("weaknesses", []),
        missed_concepts=data.get("missed_concepts", []),
        improvement_suggestions=data.get("improvement_suggestions", []),
        mastery_estimate=data.get("mastery_estimate", 0.0),
        next_action=next_action,
    )
    data_store.evaluation_records.save(record)
    logger.info(
        "Evaluation complete submission=%s score=%.1f action=%s",
        submission.submission_id,
        overall,
        next_action,
    )
    return record
