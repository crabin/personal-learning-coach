"""Tests for content_pusher with mocked Claude and delivery."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from personal_learning_coach import data_store
from personal_learning_coach.content_pusher import (
    generate_push_content,
    push_today,
    select_next_topic,
)
from personal_learning_coach.delivery.base import DeliveryAdapter
from personal_learning_coach.models import (
    DomainEnrollment,
    DomainStatus,
    LearnerLevel,
    LearningPlan,
    PushRecord,
    TopicNode,
    TopicProgress,
    TopicStatus,
)
from personal_learning_coach.online_resource import OnlineResourceService


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
        "practice_question": "Describe how attention works.",
        "reflection_question": "What are the limits of LLMs?",
    }
    client = _mock_client(json.dumps(content))
    topic = TopicNode(title="Intro to LLMs", order=0)
    result = generate_push_content("ai_agent", topic, LearnerLevel.BEGINNER, client=client)
    assert result["theory"] == content["theory"]
    assert "practice_question" in result


def test_push_today_delivers_and_persists(tmp_data_dir: Path) -> None:
    _setup_plan()
    content = {
        "theory": "LLMs use transformers.",
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


def test_push_today_updates_topic_status(tmp_data_dir: Path) -> None:
    plan = _setup_plan()
    content = {
        "theory": "...",
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


def test_push_today_persists_failed_delivery_record(tmp_data_dir: Path) -> None:
    _setup_plan()
    content = {
        "theory": "LLMs use transformers.",
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
    from personal_learning_coach.delivery.local import LocalDelivery

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
    from personal_learning_coach.delivery.local import LocalDelivery

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
