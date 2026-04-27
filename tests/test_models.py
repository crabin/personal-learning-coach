"""Tests for core domain models — serialization round-trips."""

from __future__ import annotations

from personal_learning_coach.models import (
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
