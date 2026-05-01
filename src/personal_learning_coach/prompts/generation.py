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

Learning history context:
{learning_context}

Create today's learning content for this topic.
Return JSON with this exact schema:

{{
  "theory": "Comprehensive explanation (300-500 words) covering the key concepts",
  "basic_questions": [
    "A short foundational knowledge question",
    "A short foundational knowledge question",
    "A short foundational knowledge question"
  ],
  "practice_question": "A specific practical exercise the learner should attempt",
  "reflection_question": "A deeper question to encourage critical thinking"
}}

Requirements:
- `basic_questions` must contain exactly 3 concise foundational questions.
- The 3 foundational questions should check core concepts, terminology, and understanding.
- `practice_question` must ask the learner to build, write, test, compare, or demonstrate something practical.
- Adapt the questions to the learning history: reinforce weak concepts when recent work is low-scoring, otherwise progress to the next suitable challenge.
- Avoid repeating previous questions unless this is a review or consolidation push.
- If the learning history lists "Previously asked questions to avoid repeating", generate semantically new questions instead of rewording those same prompts.
"""
