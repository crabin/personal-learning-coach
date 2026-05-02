"""Tests for content_pusher with mocked Claude and delivery."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from personal_learning_coach.infrastructure import data_store
from personal_learning_coach.application.learning.content_pusher import (
    generate_push_content,
    push_today,
    select_next_topic,
)
from personal_learning_coach.infrastructure.delivery.base import DeliveryAdapter
from personal_learning_coach.domain.models import (
    AssessmentRecord,
    DomainEnrollment,
    DomainStatus,
    EvaluationRecord,
    LearnerLevel,
    LearningPlan,
    PushRecord,
    SubmissionRecord,
    TopicNode,
    TopicProgress,
    TopicStatus,
)
from personal_learning_coach.application.learning.online_resource import OnlineResourceService


class _CapturingDelivery(DeliveryAdapter):
    """Test adapter that captures delivered pushes."""

    def __init__(self) -> None:
        self.delivered: list[PushRecord] = []

    def deliver(self, push: PushRecord) -> None:
        self.delivered.append(push)


class _FailingDelivery(DeliveryAdapter):
    """Test adapter that simulates downstream send failure."""

    def deliver(self, push: PushRecord) -> None:
        raise RuntimeError("delivery down")


def _mock_client(response_text: str) -> MagicMock:
    client = MagicMock()
    msg = MagicMock()
    msg.content = [MagicMock(text=response_text)]
    client.messages.create.return_value = msg
    return client


def _setup_plan(user_id: str = "u1") -> LearningPlan:
    t1 = TopicNode(title="Intro to LLMs", order=0)
    t2 = TopicNode(title="Prompt Engineering", order=1)
    plan = LearningPlan(user_id=user_id, domain="ai_agent", level=LearnerLevel.BEGINNER, topics=[t1, t2])
    data_store.learning_plans.save(plan)

    p1 = TopicProgress(user_id=user_id, topic_id=t1.topic_id, domain="ai_agent", status=TopicStatus.READY)
    p2 = TopicProgress(user_id=user_id, topic_id=t2.topic_id, domain="ai_agent", status=TopicStatus.LOCKED)
    data_store.topic_progress.save(p1)
    data_store.topic_progress.save(p2)
    return plan


def test_select_next_topic_returns_ready(tmp_data_dir: Path) -> None:
    plan = _setup_plan()
    result = select_next_topic("u1", plan)
    assert result is not None
    topic, progress = result
    assert topic.title == "Intro to LLMs"
    assert progress.status == TopicStatus.READY


def test_select_next_topic_prioritizes_review_due(tmp_data_dir: Path) -> None:
    t1 = TopicNode(title="Ready Topic", order=0)
    t2 = TopicNode(title="Review Topic", order=1)
    plan = LearningPlan(user_id="u1", domain="ai_agent", level=LearnerLevel.BEGINNER, topics=[t1, t2])
    data_store.learning_plans.save(plan)

    ready = TopicProgress(user_id="u1", topic_id=t1.topic_id, domain="ai_agent", status=TopicStatus.READY)
    review = TopicProgress(
        user_id="u1",
        topic_id=t2.topic_id,
        domain="ai_agent",
        status=TopicStatus.REVIEW_DUE,
    )
    data_store.topic_progress.save(ready)
    data_store.topic_progress.save(review)

    result = select_next_topic("u1", plan)
    assert result is not None
    topic, progress = result
    assert topic.title == "Review Topic"
    assert progress.status == TopicStatus.REVIEW_DUE


def test_select_next_topic_skips_locked(tmp_data_dir: Path) -> None:
    t1 = TopicNode(title="T1", order=0)
    t2 = TopicNode(title="T2", order=1)
    plan = LearningPlan(user_id="u1", domain="ai_agent", level=LearnerLevel.BEGINNER, topics=[t1, t2])
    data_store.learning_plans.save(plan)

    # Both locked — no ready topic
    p1 = TopicProgress(user_id="u1", topic_id=t1.topic_id, domain="ai_agent", status=TopicStatus.LOCKED)
    p2 = TopicProgress(user_id="u1", topic_id=t2.topic_id, domain="ai_agent", status=TopicStatus.LOCKED)
    data_store.topic_progress.save(p1)
    data_store.topic_progress.save(p2)

    result = select_next_topic("u1", plan)
    assert result is None


def test_generate_push_content(tmp_data_dir: Path) -> None:
    content = {
        "theory": "LLMs are language models...",
        "basic_questions": [
            "What is an LLM?",
            "What is a prompt?",
            "What is a token?",
        ],
        "practice_question": "Describe how attention works.",
        "reflection_question": "What are the limits of LLMs?",
    }
    client = _mock_client(json.dumps(content))
    topic = TopicNode(title="Intro to LLMs", order=0)
    result = generate_push_content("ai_agent", topic, LearnerLevel.BEGINNER, client=client)
    assert result["theory"] == content["theory"]
    assert result["basic_questions"] == content["basic_questions"]
    assert "practice_question" in result


def test_generate_push_content_normalizes_basic_questions(tmp_data_dir: Path) -> None:
    content = {
        "theory": "LLMs are language models...",
        "basic_questions": [{"question": "What is an LLM?"}, 2],
        "practice_question": "Describe how attention works.",
        "reflection_question": "What are the limits of LLMs?",
    }
    client = _mock_client(json.dumps(content))
    topic = TopicNode(title="Intro to LLMs", order=0)
    result = generate_push_content("ai_agent", topic, LearnerLevel.BEGINNER, client=client)
    assert len(result["basic_questions"]) == 3
    assert result["basic_questions"][0] == "What is an LLM?"
    assert result["basic_questions"][1] == "2"


def test_generate_push_content_avoids_repeated_basic_questions(tmp_data_dir: Path) -> None:
    duplicate = "AI Agent 的五个核心组成分别是什么？"
    content = {
        "theory": "Agent systems use tools and memory.",
        "basic_questions": [
            duplicate,
            "Agent 的工具调用如何工作？",
            "记忆模块有什么作用？",
        ],
        "practice_question": "Improve an agent prompt.",
        "reflection_question": "How did you avoid repeating prior mistakes?",
    }
    client = _mock_client(json.dumps(content))
    topic = TopicNode(title="AI Agent 基础", order=0)

    result = generate_push_content(
        "ai_agent",
        topic,
        LearnerLevel.BEGINNER,
        learning_context={"previous_questions": [duplicate]},
        client=client,
    )

    prompt = client.messages.create.call_args.kwargs["messages"][0]["content"]
    assert duplicate in prompt
    assert duplicate not in result["basic_questions"]
    assert len(result["basic_questions"]) == 3


def test_push_today_delivers_and_persists(tmp_data_dir: Path) -> None:
    _setup_plan()
    content = {
        "theory": "LLMs use transformers.",
        "basic_questions": ["Q1?", "Q2?", "Q3?"],
        "practice_question": "Explain self-attention.",
        "reflection_question": "How do embeddings help?",
    }
    client = _mock_client(json.dumps(content))
    adapter = _CapturingDelivery()

    push = push_today("u1", "ai_agent", client=client, adapter=adapter)

    assert push is not None
    assert len(adapter.delivered) == 1
    assert adapter.delivered[0].push_id == push.push_id

    saved = data_store.push_records.get(push.push_id)
    assert saved is not None
    assert saved.theory == "LLMs use transformers."
    assert saved.content_snapshot["basic_questions"] == ["Q1?", "Q2?", "Q3?"]
    history = data_store.question_history.filter(user_id="u1", push_id=push.push_id)
    assert len(history) == 1
    assert history[0].status == "generated"
    assert Path(history[0].json_path).exists()


def test_push_today_generates_with_learning_history_context(tmp_data_dir: Path) -> None:
    plan = _setup_plan()
    current_topic = plan.topics[0]
    prior_topic = plan.topics[1]
    enrollment = DomainEnrollment(
        user_id="u1",
        domain="ai_agent",
        status=DomainStatus.ACTIVE,
        level=LearnerLevel.BEGINNER,
        target_level=LearnerLevel.INTERMEDIATE,
        daily_minutes=45,
        learning_style="practice",
        allow_online_resources=False,
    )
    data_store.domain_enrollments.save(enrollment)
    prior_push = PushRecord(
        user_id="u1",
        topic_id=prior_topic.topic_id,
        domain="ai_agent",
        theory="Prior theory",
        practice_question="Build a retrieval prompt?",
    )
    data_store.push_records.save(prior_push)
    submission = SubmissionRecord(
        user_id="u1",
        push_id=prior_push.push_id,
        topic_id=prior_topic.topic_id,
        domain="ai_agent",
        raw_answer="I built a prompt but forgot evaluation criteria.",
        practice_result="Prototype failed on ambiguous requests.",
    )
    data_store.submission_records.save(submission)
    data_store.evaluation_records.save(
        EvaluationRecord(
            submission_id=submission.submission_id,
            user_id="u1",
            topic_id=prior_topic.topic_id,
            domain="ai_agent",
            overall_score=55.0,
            llm_feedback="Needs clearer evaluation criteria.",
            strengths=["clear examples"],
            weaknesses=["evaluation criteria"],
            missed_concepts=["rubrics"],
            improvement_suggestions=["add explicit scoring rules"],
            next_action="review",
        )
    )
    data_store.assessment_records.save(
        AssessmentRecord(
            user_id="u1",
            domain="ai_agent",
            assessment_type="baseline",
            level=LearnerLevel.BEGINNER,
            strengths=["hands-on experiments"],
            weaknesses=["systematic evaluation"],
            llm_feedback="Overall baseline: strong builder, weak evaluator.",
        )
    )
    progress = data_store.topic_progress.filter(user_id="u1", topic_id=current_topic.topic_id)[0]
    progress.mastery_score = 42.0
    data_store.topic_progress.save(progress)
    content = {
        "theory": "Adaptive lesson.",
        "basic_questions": ["Q1?", "Q2?", "Q3?"],
        "practice_question": "Create a rubric-backed prompt.",
        "reflection_question": "How will you validate it?",
    }
    client = _mock_client(json.dumps(content))

    push = push_today("u1", "ai_agent", client=client, adapter=_CapturingDelivery())

    assert push is not None
    prompt = client.messages.create.call_args.kwargs["messages"][0]["content"]
    assert "Learning history context" in prompt
    assert "Overall baseline: strong builder, weak evaluator." in prompt
    assert "Needs clearer evaluation criteria." in prompt
    assert "missed concepts: rubrics" in prompt
    assert "Current topic progress: status=ready, mastery_score=42.0, attempts=0" in prompt
    assert "target_level=intermediate" in prompt
    assert push.content_snapshot["learning_context"]["recent_evaluations"][0]["overall_score"] == 55.0
    assert push.content_snapshot["learning_context"]["current_topic_progress"]["mastery_score"] == 42.0


def test_push_today_includes_playful_learning_intent_context(tmp_data_dir: Path) -> None:
    _setup_plan()
    enrollment = DomainEnrollment(
        user_id="u1",
        domain="ai_agent",
        status=DomainStatus.ACTIVE,
        learning_category="playful",
        learning_category_confidence=0.88,
        learning_tone_guidance="用脑洞问题训练真实能力，不能变成纯段子。",
    )
    data_store.domain_enrollments.save(enrollment)
    content = {
        "theory": "Playful but useful lesson.",
        "basic_questions": ["Q1?", "Q2?", "Q3?"],
        "practice_question": "Design a focus protocol as a fake mission briefing.",
        "reflection_question": "Which part still improves a real skill?",
    }
    client = _mock_client(json.dumps(content))

    push = push_today("u1", "ai_agent", client=client, adapter=_CapturingDelivery())

    assert push is not None
    prompt = client.messages.create.call_args.kwargs["messages"][0]["content"]
    assert "learning_category=playful" in prompt
    assert "用脑洞问题训练真实能力" in prompt
    assert "每题都要训练一个真实能力" in prompt
    assert "纯搞笑" in prompt
    assert push.content_snapshot["learning_context"]["enrollment"]["learning_category"] == "playful"
    assert push.content_snapshot["learning_context"]["enrollment"]["learning_tone_guidance"] == (
        "用脑洞问题训练真实能力，不能变成纯段子。"
    )


def test_push_today_updates_topic_status(tmp_data_dir: Path) -> None:
    plan = _setup_plan()
    content = {
        "theory": "...",
        "basic_questions": ["Q1?", "Q2?", "Q3?"],
        "practice_question": "Q?",
        "reflection_question": "R?",
    }
    client = _mock_client(json.dumps(content))
    adapter = _CapturingDelivery()
    push_today("u1", "ai_agent", client=client, adapter=adapter)

    first_topic_id = plan.topics[0].topic_id
    progress = data_store.topic_progress.filter(user_id="u1", topic_id=first_topic_id)
    assert progress[0].status == TopicStatus.PUSHED


def test_push_today_no_plan_returns_none(tmp_data_dir: Path) -> None:
    result = push_today("u1", "ai_agent")
    assert result is None


def test_push_today_resends_interruption_recovery(tmp_data_dir: Path) -> None:
    plan = _setup_plan()
    first_topic = plan.topics[0]
    progress = data_store.topic_progress.filter(user_id="u1", topic_id=first_topic.topic_id)[0]
    progress.status = TopicStatus.PUSHED
    data_store.topic_progress.save(progress)

    original_push = PushRecord(
        user_id="u1",
        topic_id=first_topic.topic_id,
        domain="ai_agent",
        push_type="new_topic",
        theory="Resume this theory",
        practice_question="Resume practice?",
        reflection_question="Resume reflection?",
        content_snapshot={
            "theory": "Resume this theory",
            "basic_questions": ["Q1?", "Q2?", "Q3?"],
            "practice_question": "Resume practice?",
            "reflection_question": "Resume reflection?",
        },
    )
    data_store.push_records.save(original_push)

    adapter = _CapturingDelivery()
    push = push_today("u1", "ai_agent", adapter=adapter)

    assert push is not None
    assert push.push_type == "interruption_recovery"
    assert push.topic_id == first_topic.topic_id
    assert push.theory == "Resume this theory"
    assert len(adapter.delivered) == 1


def test_push_today_regenerates_incomplete_interruption_recovery(tmp_data_dir: Path) -> None:
    plan = _setup_plan()
    first_topic = plan.topics[0]
    progress = data_store.topic_progress.filter(user_id="u1", topic_id=first_topic.topic_id)[0]
    progress.status = TopicStatus.PUSHED
    data_store.topic_progress.save(progress)
    data_store.push_records.save(
        PushRecord(
            user_id="u1",
            topic_id=first_topic.topic_id,
            domain="ai_agent",
            push_type="new_topic",
            theory="Old theory without answerable questions",
            content_snapshot={"theory": "Old theory without answerable questions"},
        )
    )
    content = {
        "theory": "Fresh theory",
        "basic_questions": ["Q1?", "Q2?", "Q3?"],
        "practice_question": "Fresh practice?",
        "reflection_question": "Fresh reflection?",
    }
    client = _mock_client(json.dumps(content))
    adapter = _CapturingDelivery()

    push = push_today("u1", "ai_agent", client=client, adapter=adapter)

    assert push is not None
    assert push.push_type == "new_topic"
    assert push.theory == "Fresh theory"
    assert push.content_snapshot["basic_questions"] == ["Q1?", "Q2?", "Q3?"]
    refreshed_progress = data_store.topic_progress.filter(user_id="u1", topic_id=first_topic.topic_id)[0]
    assert refreshed_progress.status == TopicStatus.PUSHED
    assert len(adapter.delivered) == 1


def test_push_today_persists_failed_delivery_record(tmp_data_dir: Path) -> None:
    _setup_plan()
    content = {
        "theory": "LLMs use transformers.",
        "basic_questions": ["Q1?", "Q2?", "Q3?"],
        "practice_question": "Explain self-attention.",
        "reflection_question": "How do embeddings help?",
    }
    client = _mock_client(json.dumps(content))

    with pytest.raises(RuntimeError, match="delivery down"):
        push_today("u1", "ai_agent", client=client, adapter=_FailingDelivery())

    saved = data_store.push_records.all()
    assert len(saved) == 1
    assert saved[0].delivery_channel == "failing"
    assert saved[0].delivery_result == "failed: delivery down"


def test_push_today_persists_failed_recovery_delivery_record(tmp_data_dir: Path) -> None:
    plan = _setup_plan()
    first_topic = plan.topics[0]
    progress = data_store.topic_progress.filter(user_id="u1", topic_id=first_topic.topic_id)[0]
    progress.status = TopicStatus.PUSHED
    data_store.topic_progress.save(progress)
    data_store.push_records.save(
        PushRecord(
            user_id="u1",
            topic_id=first_topic.topic_id,
            domain="ai_agent",
            push_type="new_topic",
            theory="Resume this theory",
            practice_question="Resume practice?",
            reflection_question="Resume reflection?",
            content_snapshot={
                "theory": "Resume this theory",
                "basic_questions": ["Q1?", "Q2?", "Q3?"],
                "practice_question": "Resume practice?",
                "reflection_question": "Resume reflection?",
            },
        )
    )

    with pytest.raises(RuntimeError, match="delivery down"):
        push_today("u1", "ai_agent", adapter=_FailingDelivery())

    saved = data_store.push_records.all()
    assert len(saved) == 2
    latest = sorted(saved, key=lambda record: record.scheduled_at)[-1]
    assert latest.push_type == "interruption_recovery"
    assert latest.delivery_result == "failed: delivery down"


def test_push_today_skips_when_domain_paused(tmp_data_dir: Path) -> None:
    _setup_plan()
    enrollment = DomainEnrollment(user_id="u1", domain="ai_agent", status=DomainStatus.PAUSED)
    data_store.domain_enrollments.save(enrollment)

    result = push_today("u1", "ai_agent")
    assert result is None


def test_push_today_includes_online_resources(tmp_data_dir: Path) -> None:
    _setup_plan()
    enrollment = DomainEnrollment(user_id="u1", domain="ai_agent", status=DomainStatus.ACTIVE)
    data_store.domain_enrollments.save(enrollment)
    content = {
        "theory": "LLMs use transformers.",
        "basic_questions": ["Q1?", "Q2?", "Q3?"],
        "practice_question": "Explain self-attention.",
        "reflection_question": "How do embeddings help?",
    }
    client = _mock_client(json.dumps(content))
    adapter = _CapturingDelivery()
    service = OnlineResourceService(
        fetcher=lambda domain, topic, language, limit: [
            {
                "title": "Transformer",
                "url": "https://en.wikipedia.org/wiki/Transformer_(deep_learning_architecture)",
                "summary": "Architecture overview.",
                "source": "wikipedia",
            }
        ]
    )

    push = push_today("u1", "ai_agent", client=client, adapter=adapter, resource_service=service)

    assert push is not None
    assert push.resource_snapshot["source"] == "online"
    assert len(push.resource_snapshot["items"]) == 1
    assert push.resource_snapshot["items"][0]["title"] == "Transformer"


def test_push_today_skips_online_resources_when_disabled(tmp_data_dir: Path) -> None:
    _setup_plan()
    enrollment = DomainEnrollment(
        user_id="u1",
        domain="ai_agent",
        status=DomainStatus.ACTIVE,
        allow_online_resources=False,
    )
    data_store.domain_enrollments.save(enrollment)
    content = {
        "theory": "LLMs use transformers.",
        "basic_questions": ["Q1?", "Q2?", "Q3?"],
        "practice_question": "Explain self-attention.",
        "reflection_question": "How do embeddings help?",
    }
    client = _mock_client(json.dumps(content))
    adapter = _CapturingDelivery()

    push = push_today("u1", "ai_agent", client=client, adapter=adapter)

    assert push is not None
    assert push.resource_snapshot["enabled"] is False
    assert push.resource_snapshot["items"] == []


def test_push_today_degrades_when_online_resource_fetch_fails(tmp_data_dir: Path) -> None:
    _setup_plan()
    enrollment = DomainEnrollment(user_id="u1", domain="ai_agent", status=DomainStatus.ACTIVE)
    data_store.domain_enrollments.save(enrollment)
    content = {
        "theory": "LLMs use transformers.",
        "basic_questions": ["Q1?", "Q2?", "Q3?"],
        "practice_question": "Explain self-attention.",
        "reflection_question": "How do embeddings help?",
    }
    client = _mock_client(json.dumps(content))
    adapter = _CapturingDelivery()
    service = OnlineResourceService(fetcher=lambda domain, topic, language, limit: (_ for _ in ()).throw(RuntimeError("boom")))

    push = push_today("u1", "ai_agent", client=client, adapter=adapter, resource_service=service)

    assert push is not None
    assert push.resource_snapshot["source"] == "fallback"
    assert push.resource_snapshot["items"] == []
    assert len(adapter.delivered) == 1


def test_local_delivery_writes_file(tmp_data_dir: Path) -> None:
    from personal_learning_coach.infrastructure.delivery.local import LocalDelivery

    output_dir = tmp_data_dir / "pushes"
    adapter = LocalDelivery(output_dir=output_dir)
    push = PushRecord(
        user_id="u1",
        topic_id="t1",
        domain="ai_agent",
        theory="Test theory.",
        practice_question="Practice?",
        reflection_question="Reflect?",
    )
    adapter.deliver(push)

    files = list(output_dir.glob("*.md"))
    assert len(files) == 1
    content = files[0].read_text()
    assert "Test theory." in content


def test_local_delivery_renders_resource_block(tmp_data_dir: Path) -> None:
    from personal_learning_coach.infrastructure.delivery.local import LocalDelivery

    output_dir = tmp_data_dir / "pushes"
    adapter = LocalDelivery(output_dir=output_dir)
    push = PushRecord(
        user_id="u1",
        topic_id="t1",
        domain="ai_agent",
        theory="Test theory.",
        practice_question="Practice?",
        reflection_question="Reflect?",
        resource_snapshot={
            "items": [
                {
                    "title": "Transformer",
                    "url": "https://example.com/transformer",
                    "summary": "Quick reference.",
                }
            ]
        },
    )
    adapter.deliver(push)

    files = list(output_dir.glob("*.md"))
    assert len(files) == 1
    content = files[0].read_text()
    assert "Recommended Resources" in content
    assert "https://example.com/transformer" in content
