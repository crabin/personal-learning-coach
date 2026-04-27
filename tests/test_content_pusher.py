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
    LearnerLevel,
    LearningPlan,
    PushRecord,
    TopicNode,
    TopicProgress,
    TopicStatus,
)


class _CapturingDelivery(DeliveryAdapter):
    """Test adapter that captures delivered pushes."""

    def __init__(self) -> None:
        self.delivered: list[PushRecord] = []

    def deliver(self, push: PushRecord) -> None:
        self.delivered.append(push)


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
