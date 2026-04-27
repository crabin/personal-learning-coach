"""Prompt templates for learning plan and content generation."""

from __future__ import annotations

PLAN_SYSTEM = """\
You are an expert curriculum designer creating personalized learning plans.
Respond ONLY with valid JSON matching the specified schema.
"""

PLAN_GENERATION_PROMPT = """\
Domain: {domain}
Learner level: {level}
Learner preferences: {preferences}

Create a structured learning plan for this domain.
Each topic should build on the previous ones.
Return JSON with this exact schema:

{{
  "total_weeks": <integer>,
  "topics": [
    {{
      "title": "...",
      "description": "...",
      "order": <integer starting at 0>,
      "prerequisites": []
    }},
    ...
  ]
}}

Generate 6-12 topics appropriate for the learner's level.
"""

CONTENT_SYSTEM = """\
You are an expert teacher creating focused daily learning content.
Respond ONLY with valid JSON matching the specified schema.
"""

CONTENT_GENERATION_PROMPT = """\
Domain: {domain}
Topic: {topic_title}
Topic description: {topic_description}
Learner level: {level}

Create today's learning content for this topic.
Return JSON with this exact schema:

{{
  "theory": "Comprehensive explanation (300-500 words) covering the key concepts",
  "practice_question": "A specific practical exercise the learner should attempt",
  "reflection_question": "A deeper question to encourage critical thinking"
}}
"""
