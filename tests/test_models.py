"""Tests for core domain models — serialization round-trips."""

from __future__ import annotations

from personal_learning_coach.domain.models import (
    AssessmentRecord,
    DimensionScore,
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
    UserProfile,
)
from personal_learning_coach.application.learning.online_resource import OnlineResourceService


def test_user_profile_round_trip() -> None:
    profile = UserProfile(name="Alice", email="alice@example.com")
    data = profile.model_dump(mode="json")
    restored = UserProfile.model_validate(data)
    assert restored.name == "Alice"
    assert restored.user_id == profile.user_id


def test_domain_enrollment_defaults() -> None:
    enroll = DomainEnrollment(user_id="u1", domain="ai_agent")
    assert enroll.status == DomainStatus.NOT_STARTED
    assert enroll.level == LearnerLevel.BEGINNER
    assert enroll.current_level == LearnerLevel.BEGINNER
    assert enroll.target_level == LearnerLevel.BEGINNER
    assert enroll.daily_minutes == 60
    assert enroll.learning_style == "blended"
    assert enroll.learning_category == "serious"
    assert enroll.learning_category_confidence == 0.0
    assert enroll.learning_tone_guidance == ""
    assert enroll.delivery_time == "09:00"
    assert enroll.language == "zh"
    assert enroll.allow_online_resources is True
    assert enroll.schedule_config["delivery_time"] == "09:00"


def test_learning_plan_round_trip() -> None:
    plan = LearningPlan(
        user_id="u1",
        domain="ai_agent",
        level=LearnerLevel.BEGINNER,
        topics=[TopicNode(title="Intro to LLMs", order=0)],
    )
    data = plan.model_dump(mode="json")
    restored = LearningPlan.model_validate(data)
    assert len(restored.topics) == 1
    assert restored.topics[0].title == "Intro to LLMs"


def test_topic_progress_defaults() -> None:
    tp = TopicProgress(user_id="u1", topic_id="t1", domain="ai_agent")
    assert tp.status == TopicStatus.LOCKED
    assert tp.mastery_score == 0.0
    assert tp.attempts == 0


def test_push_record_round_trip() -> None:
    pr = PushRecord(
        user_id="u1",
        topic_id="t1",
        domain="ai_agent",
        theory="LLMs use transformer architectures.",
        practice_question="Explain attention mechanisms.",
        reflection_question="How does self-attention differ from cross-attention?",
    )
    data = pr.model_dump(mode="json")
    restored = PushRecord.model_validate(data)
    assert restored.theory == pr.theory
    assert restored.push_id == pr.push_id
    assert restored.push_type == "new_topic"
    assert restored.delivery_channel == "local"


def test_submission_record() -> None:
    sub = SubmissionRecord(
        user_id="u1",
        push_id="p1",
        topic_id="t1",
        domain="ai_agent",
        raw_answer="Attention is a mechanism...",
        practice_result="Implemented a toy attention example.",
        parsing_notes="Parsed as free-text response.",
    )
    data = sub.model_dump(mode="json")
    restored = SubmissionRecord.model_validate(data)
    assert restored.raw_answer == sub.raw_answer
    assert restored.normalized_answer == sub.raw_answer
    assert restored.practice_result == "Implemented a toy attention example."


def test_evaluation_record_weighted_score() -> None:
    dims = [
        DimensionScore(name="concept_coverage", weight=0.30, score=80.0),
        DimensionScore(name="understanding_depth", weight=0.25, score=70.0),
        DimensionScore(name="logic_clarity", weight=0.25, score=90.0),
        DimensionScore(name="practical_application", weight=0.20, score=60.0),
    ]
    overall = sum(d.weight * d.score for d in dims)
    ev = EvaluationRecord(
        submission_id="s1",
        user_id="u1",
        topic_id="t1",
        domain="ai_agent",
        dimension_scores=dims,
        overall_score=overall,
        llm_feedback="Good effort.",
    )
    # 0.30*80 + 0.25*70 + 0.25*90 + 0.20*60 = 24+17.5+22.5+12 = 76.0
    assert abs(ev.overall_score - 76.0) < 0.01
    assert ev.progress_applied is False


def test_assessment_record() -> None:
    rec = AssessmentRecord(
        user_id="u1",
        domain="ai_agent",
        level=LearnerLevel.INTERMEDIATE,
        questions=["What is a transformer?"],
        raw_answers=["A transformer is a neural network architecture."],
        confidence=0.82,
        strengths=["Understands model architecture basics"],
        weaknesses=["Needs stronger systems intuition"],
        structured_scores={"concept_coverage": 82.0, "practical_application": 68.0},
        recommended_plan_style="practice",
    )
    data = rec.model_dump(mode="json")
    restored = AssessmentRecord.model_validate(data)
    assert restored.level == LearnerLevel.INTERMEDIATE
    assert len(restored.raw_answers) == 1
    assert restored.confidence == 0.82
    assert restored.strengths == ["Understands model architecture basics"]
    assert restored.recommended_plan_style == "practice"


def test_online_resource_service_dedupes_and_caches() -> None:
    calls: list[tuple[str, str, str, int]] = []

    def fetcher(domain: str, topic: str, language: str, limit: int) -> list[dict[str, str]]:
        calls.append((domain, topic, language, limit))
        return [
            {"title": "Transformer", "url": "https://example.com/a", "summary": "One"},
            {"title": "Transformer", "url": "https://example.com/a/", "summary": "Duplicate"},
            {"title": "Attention", "url": "https://example.com/b", "summary": "Two"},
        ]

    service = OnlineResourceService(fetcher=fetcher)
    first = service.recommend_resources("ai_agent", "Transformers", language="en", limit=3)
    second = service.recommend_resources("ai_agent", "Transformers", language="en", limit=3)

    assert calls == [("ai_agent", "Transformers", "en", 3)]
    assert first["source"] == "online"
    assert second["source"] == "cache"
    assert len(first["items"]) == 2


def test_telegram_delivery_raises_without_required_env() -> None:
    from personal_learning_coach.infrastructure.delivery.telegram import TelegramDelivery

    try:
        TelegramDelivery(bot_token="", chat_id="")
    except ValueError as exc:
        assert "TELEGRAM_BOT_TOKEN" in str(exc)
    else:
        raise AssertionError("Expected missing Telegram config to raise ValueError")


def test_telegram_delivery_posts_message() -> None:
    import httpx

    from personal_learning_coach.infrastructure.delivery.telegram import TelegramDelivery

    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    delivery = TelegramDelivery(bot_token="token", chat_id="chat", client=client)
    push = PushRecord(
        user_id="u1",
        topic_id="t1",
        domain="ai_agent",
        theory="Test theory.",
        practice_question="Practice?",
        reflection_question="Reflect?",
    )

    delivery.deliver(push)

    assert len(requests) == 1
    assert requests[0].url.path.endswith("/bottoken/sendMessage")
    assert b"Practice?" in requests[0].content
