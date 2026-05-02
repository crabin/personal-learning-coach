"""Centralized prompt templates for the Personal Learning Coach."""

from __future__ import annotations

PLAN_SYSTEM = """\
You are an expert curriculum designer creating personalized learning plans.
Respond ONLY with valid JSON matching the specified schema.
"""

PLAN_GENERATION_PROMPT = """\
Domain: {domain}
Learner level: {level}
Learner preferences: {preferences}
Hidden learning category: {learning_category}
Tone guidance: {learning_tone_guidance}

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
If the hidden category is "serious", keep the plan rigorous, structured, and directly skill-focused.
If the hidden category is "playful", topics may use humorous or imaginative framing, but every topic must still train a real concept, judgment, communication skill, or practical capability.
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
- If `learning_category=playful`, the style can be 搞怪 and imaginative, but 每题都要训练一个真实能力.
- For playful learning, avoid 纯搞笑 output and do not encourage cheating, evading responsibility, deception, or harmful workplace behavior.
"""

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

INTENT_SYSTEM = """\
You classify a learner's hidden intent for personalization.
Respond ONLY with valid JSON matching the requested schema.
"""

INTENT_PROMPT = """\
Domain: {domain}
Language: {language}
Learning style preference: {learning_style}
Preferences JSON: {preferences}

Classify whether the learner is asking for serious learning or a playful/non-standard learning topic.
Return JSON with this exact schema:

{{
  "learning_category": "serious" | "playful",
  "confidence": <number from 0 to 1>,
  "reason": "short explanation",
  "tone_guidance": "short guidance for downstream lesson generation"
}}

Rules:
- Use "serious" for ordinary academic, professional, technical, or skill-building goals.
- Use "playful" when the learner clearly asks for humorous, weird, mischievous, or non-standard topics.
- Playful learning must still preserve real learning value and must not encourage cheating, evasion of responsibility, or harmful workplace behavior.
"""


def build_qa_pairs(questions: list[str], answers: list[str]) -> str:
    parts = []
    for i, (q, a) in enumerate(zip(questions, answers), 1):
        parts.append(f"Q{i}: {q}\nA{i}: {a}")
    return "\n\n".join(parts)
