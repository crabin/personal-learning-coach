"""Prompt templates for baseline assessment."""

from __future__ import annotations

ASSESSMENT_SYSTEM = """\
You are an expert learning coach conducting a baseline assessment.
Your task is to evaluate the learner's current level in the given domain.
Respond ONLY with valid JSON matching the specified schema.
"""

ASSESSMENT_QUESTIONS_PROMPT = """\
Domain: {domain}

Generate 3 assessment questions that span beginner, intermediate, and advanced levels
for this domain. Return JSON with this exact schema:

{{
  "questions": [
    {{"level": "beginner", "text": "..."}},
    {{"level": "intermediate", "text": "..."}},
    {{"level": "advanced", "text": "..."}}
  ]
}}
"""

ASSESSMENT_EVALUATE_PROMPT = """\
Domain: {domain}

Assessment questions and learner answers:
{qa_pairs}

Evaluate the learner's overall level based on their answers.
Return JSON with this exact schema:

{{
  "level": "beginner" | "intermediate" | "advanced",
  "feedback": "2-3 sentence explanation of the level determination",
  "strengths": ["...", "..."],
  "gaps": ["...", "..."]
}}
"""


def build_qa_pairs(questions: list[str], answers: list[str]) -> str:
    parts = []
    for i, (q, a) in enumerate(zip(questions, answers), 1):
        parts.append(f"Q{i}: {q}\nA{i}: {a}")
    return "\n\n".join(parts)
