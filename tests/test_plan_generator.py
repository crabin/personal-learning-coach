"""Tests for level_tester and plan_generator with mocked Claude API."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from personal_learning_coach.infrastructure import data_store
from personal_learning_coach.application.assessment.level_tester import (
    evaluate_answers,
    generate_assessment_questions,
    run_assessment,
)
from personal_learning_coach.domain.models import LearnerLevel
from personal_learning_coach.application.learning.plan_generator import enroll_domain, generate_plan


def _mock_client(response_text: str) -> MagicMock:
    client = MagicMock()
    msg = MagicMock()
    msg.content = [MagicMock(text=response_text)]
    client.messages.create.return_value = msg
    return client


# ---------------------------------------------------------------------------
# level_tester tests
# ---------------------------------------------------------------------------


def test_generate_assessment_questions(tmp_data_dir: Path) -> None:
    payload = {
        "questions": [
            {"level": "beginner", "text": "What is an LLM?"},
            {"level": "intermediate", "text": "Explain prompt engineering."},
            {"level": "advanced", "text": "How do RAG systems work?"},
        ]
    }
    client = _mock_client(json.dumps(payload))
    questions = generate_assessment_questions("ai_agent", client=client)
    assert len(questions) == 3
    assert questions[0] == "What is an LLM?"


def test_evaluate_answers_returns_level(tmp_data_dir: Path) -> None:
    payload = {
        "level": "intermediate",
        "feedback": "Good foundational knowledge.",
        "strengths": ["understands basics"],
        "gaps": ["advanced topics"],
    }
    client = _mock_client(json.dumps(payload))
    level, feedback = evaluate_answers(
        "ai_agent", ["Q1", "Q2"], ["A1", "A2"], client=client
    )
    assert level == LearnerLevel.INTERMEDIATE
    assert "foundational" in feedback


def test_run_assessment_persists(tmp_data_dir: Path) -> None:
    payload = {
        "level": "beginner",
        "feedback": "Needs foundational work.",
        "strengths": [],
        "gaps": ["everything"],
    }
    client = _mock_client(json.dumps(payload))
    record = run_assessment(
        user_id="u1",
        domain="ai_agent",
        answers=["I don't know much."],
        questions=["What is an LLM?"],
        client=client,
    )
    assert record.level == LearnerLevel.BEGINNER
    saved = data_store.assessment_records.get(record.assessment_id)
    assert saved is not None
    assert saved.user_id == "u1"


# ---------------------------------------------------------------------------
# plan_generator tests
# ---------------------------------------------------------------------------


def test_generate_plan_creates_topics(tmp_data_dir: Path) -> None:
    payload = {
        "total_weeks": 4,
        "topics": [
            {"title": "Intro to LLMs", "description": "Basics", "order": 0, "prerequisites": []},
            {"title": "Prompt Engineering", "description": "Techniques", "order": 1, "prerequisites": []},
        ],
    }
    client = _mock_client(json.dumps(payload))
    plan = generate_plan("u1", "ai_agent", LearnerLevel.BEGINNER, client=client)
    assert len(plan.topics) == 2
    assert plan.topics[0].title == "Intro to LLMs"
    assert plan.total_weeks == 4


def test_generate_plan_prompt_includes_learning_intent(tmp_data_dir: Path) -> None:
    payload = {
        "total_weeks": 2,
        "topics": [{"title": "摸鱼心理学入门", "order": 0}],
    }
    client = _mock_client(json.dumps(payload))

    generate_plan(
        "u1",
        "上班摸鱼",
        LearnerLevel.BEGINNER,
        preferences={
            "learning_category": "playful",
            "learning_tone_guidance": "使用脑洞案例，但每个主题都要训练真实能力。",
        },
        client=client,
    )

    prompt = client.messages.create.call_args.kwargs["messages"][0]["content"]
    assert "Hidden learning category: playful" in prompt
    assert "使用脑洞案例" in prompt


def test_generate_plan_initialises_topic_progress(tmp_data_dir: Path) -> None:
    payload = {
        "total_weeks": 4,
        "topics": [
            {"title": "Topic A", "order": 0},
            {"title": "Topic B", "order": 1},
            {"title": "Topic C", "order": 2},
        ],
    }
    client = _mock_client(json.dumps(payload))
    plan = generate_plan("u1", "ai_agent", LearnerLevel.BEGINNER, client=client)

    from personal_learning_coach.domain.models import TopicStatus

    progress_list = data_store.topic_progress.filter(user_id="u1")
    assert len(progress_list) == 3
    first = next(p for p in progress_list if p.topic_id == plan.topics[0].topic_id)
    others = [p for p in progress_list if p.topic_id != plan.topics[0].topic_id]
    assert first.status == TopicStatus.READY
    for p in others:
        assert p.status == TopicStatus.LOCKED


def test_generate_plan_normalizes_non_string_prerequisites(tmp_data_dir: Path) -> None:
    payload = {
        "total_weeks": 4,
        "topics": [
            {"title": "Topic A", "order": 0, "prerequisites": []},
            {"title": "Topic B", "order": 1, "prerequisites": [0, "Topic A"]},
        ],
    }
    client = _mock_client(json.dumps(payload))

    plan = generate_plan("u1", "ai_agent", LearnerLevel.BEGINNER, client=client)

    assert plan.topics[1].prerequisites == ["0", "Topic A"]


def test_enroll_domain_sets_active_status(tmp_data_dir: Path) -> None:
    payload = {
        "total_weeks": 2,
        "topics": [{"title": "T1", "order": 0}],
    }
    client = _mock_client(json.dumps(payload))
    enrollment, plan = enroll_domain("u1", "ai_agent", LearnerLevel.BEGINNER, client=client)

    from personal_learning_coach.domain.models import DomainStatus

    assert enrollment.status == DomainStatus.ACTIVE
    saved = data_store.domain_enrollments.filter(user_id="u1", domain="ai_agent")
    assert len(saved) == 1
    assert saved[0].status == DomainStatus.ACTIVE


def test_enroll_domain_persists_hidden_learning_intent(tmp_data_dir: Path) -> None:
    payload = {
        "total_weeks": 2,
        "topics": [{"title": "摸鱼心理学入门", "order": 0}],
    }
    classify_payload = {
        "learning_category": "playful",
        "confidence": 0.92,
        "reason": "Humorous workplace topic.",
        "tone_guidance": "用轻松荒诞的例子训练注意力管理和边界沟通。",
    }
    client = MagicMock()
    classification_response = _mock_client(json.dumps(classify_payload)).messages.create.return_value
    plan_response = _mock_client(json.dumps(payload)).messages.create.return_value
    client.messages.create.side_effect = [classification_response, plan_response]

    enrollment, _plan = enroll_domain("u1", "上班摸鱼", LearnerLevel.BEGINNER, client=client)

    assert enrollment.learning_category == "playful"
    assert enrollment.learning_category_confidence == 0.92
    assert "注意力管理" in enrollment.learning_tone_guidance
    saved = data_store.domain_enrollments.filter(user_id="u1", domain="上班摸鱼")
    assert saved[0].learning_category == "playful"
