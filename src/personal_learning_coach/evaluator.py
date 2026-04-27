"""Evaluate learner submissions using a 4-dimension rubric via Claude."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import anthropic

from personal_learning_coach import data_store
from personal_learning_coach.models import (
    DimensionScore,
    EvaluationRecord,
    PushRecord,
    SubmissionRecord,
)

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"

EVAL_SYSTEM = """\
You are an expert learning coach evaluating a student's submission.
Score the answer on 4 dimensions and provide actionable feedback.
Respond ONLY with valid JSON matching the specified schema.
"""

EVAL_PROMPT = """\
Domain: {domain}
Topic: {topic_title}

Today's learning content:
Theory: {theory}
Practice question: {practice_question}

Student's answer:
{raw_answer}

Evaluate the answer on these 4 dimensions (score 0-100 each):
1. concept_coverage (weight 0.30) — Did the student cover the key concepts?
2. understanding_depth (weight 0.25) — Did they demonstrate genuine understanding?
3. logic_clarity (weight 0.25) — Is the reasoning clear and well-structured?
4. practical_application (weight 0.20) — Did they apply concepts practically?

Return JSON with this exact schema:
{{
  "dimensions": {{
    "concept_coverage": {{"score": <0-100>, "feedback": "..."}},
    "understanding_depth": {{"score": <0-100>, "feedback": "..."}},
    "logic_clarity": {{"score": <0-100>, "feedback": "..."}},
    "practical_application": {{"score": <0-100>, "feedback": "..."}}
  }},
  "overall_feedback": "2-3 sentence overall assessment",
  "strengths": ["...", "..."],
  "weaknesses": ["...", "..."],
  "missed_concepts": ["..."],
  "improvement_suggestions": ["..."],
  "mastery_estimate": <0.0-1.0>
}}
"""

DIMENSION_WEIGHTS = {
    "concept_coverage": 0.30,
    "understanding_depth": 0.25,
    "logic_clarity": 0.25,
    "practical_application": 0.20,
}


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


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
    client: anthropic.Anthropic | None = None,
) -> EvaluationRecord:
    """Evaluate a submission against its push context.

    Args:
        submission: The learner's submission.
        push: The push that prompted the submission.
        client: Optional Anthropic client (for testing).

    Returns:
        Persisted EvaluationRecord.
    """
    cl = client or _client()

    # Resolve topic title from the plan
    plans = data_store.learning_plans.filter(user_id=submission.user_id, domain=submission.domain)
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
    response = cl.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=EVAL_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text  # type: ignore[union-attr]
    data = _parse_json(raw)

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
