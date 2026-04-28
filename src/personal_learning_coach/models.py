"""Core domain entities for the Personal Learning Coach."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


def _now() -> datetime:
    return datetime.now(UTC)


def _uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class DomainStatus(str, Enum):
    NOT_STARTED = "not_started"
    ASSESSING = "assessing"
    PLANNING = "planning"
    ACTIVE = "active"
    REVIEW_DUE = "review_due"
    AWAITING_SUBMISSION = "awaiting_submission"
    PAUSED = "paused"
    FINAL_ASSESSMENT_DUE = "final_assessment_due"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class TopicStatus(str, Enum):
    LOCKED = "locked"
    READY = "ready"
    PUSHED = "pushed"
    STUDYING = "studying"
    SUBMITTED = "submitted"
    EVALUATED = "evaluated"
    REVIEW_DUE = "review_due"
    MASTERED = "mastered"


class LearnerLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


# ---------------------------------------------------------------------------
# Core entity models
# ---------------------------------------------------------------------------


class UserProfile(BaseModel):
    """Learner identity and preferences."""

    user_id: str = Field(default_factory=_uuid)
    name: str
    email: str = ""
    level_default: LearnerLevel = LearnerLevel.BEGINNER
    preferences: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class DomainEnrollment(BaseModel):
    """A learner's enrollment in a specific learning domain."""

    enrollment_id: str = Field(default_factory=_uuid)
    user_id: str
    domain: str
    status: DomainStatus = DomainStatus.NOT_STARTED
    level: LearnerLevel = LearnerLevel.BEGINNER
    target_level: LearnerLevel | None = None
    current_level: LearnerLevel | None = None
    daily_minutes: int = 60
    learning_style: str = "blended"
    delivery_time: str = "09:00"
    language: str = "zh"
    allow_online_resources: bool = True
    schedule_config: dict[str, Any] = Field(default_factory=dict)
    enrolled_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)

    @model_validator(mode="after")
    def _apply_defaults(self) -> DomainEnrollment:
        if self.current_level is None:
            self.current_level = self.level
        if self.target_level is None:
            self.target_level = self.level
        if not self.schedule_config:
            self.schedule_config = {"delivery_time": self.delivery_time}
        else:
            self.schedule_config.setdefault("delivery_time", self.delivery_time)
        return self


class TopicNode(BaseModel):
    """A single topic within a learning plan."""

    topic_id: str = Field(default_factory=_uuid)
    title: str
    description: str = ""
    order: int = 0
    prerequisites: list[str] = Field(default_factory=list)


class LearningPlan(BaseModel):
    """Personalized learning plan for a domain."""

    plan_id: str = Field(default_factory=_uuid)
    user_id: str
    domain: str
    level: LearnerLevel
    topics: list[TopicNode] = Field(default_factory=list)
    total_weeks: int = 4
    generated_at: datetime = Field(default_factory=_now)


class TopicProgress(BaseModel):
    """Progress tracking for a single topic."""

    progress_id: str = Field(default_factory=_uuid)
    user_id: str
    topic_id: str
    domain: str
    status: TopicStatus = TopicStatus.LOCKED
    mastery_score: float = 0.0
    attempts: int = 0
    last_review_at: datetime | None = None
    next_review_at: datetime | None = None
    updated_at: datetime = Field(default_factory=_now)


class PushRecord(BaseModel):
    """Snapshot of a single daily content push."""

    push_id: str = Field(default_factory=_uuid)
    user_id: str
    topic_id: str
    domain: str
    push_type: str = "new_topic"
    theory: str = ""
    practice_question: str = ""
    reflection_question: str = ""
    scheduled_at: datetime = Field(default_factory=_now)
    delivered_at: datetime | None = None
    resource_snapshot: dict[str, Any] = Field(default_factory=dict)
    delivery_channel: str = "local"
    delivery_result: str = "pending"
    content_snapshot: dict[str, Any] = Field(default_factory=dict)


class SubmissionRecord(BaseModel):
    """A learner's answer submission for a push."""

    submission_id: str = Field(default_factory=_uuid)
    user_id: str
    push_id: str
    topic_id: str
    domain: str
    raw_answer: str
    practice_result: str = ""
    normalized_answer: str = ""
    parsing_notes: str = ""
    submitted_at: datetime = Field(default_factory=_now)

    @model_validator(mode="after")
    def _normalize_answer(self) -> SubmissionRecord:
        if not self.normalized_answer:
            self.normalized_answer = self.raw_answer.strip()
        return self


class DimensionScore(BaseModel):
    """Score for a single evaluation dimension."""

    name: str
    weight: float
    score: float  # 0–100
    feedback: str = ""


class EvaluationRecord(BaseModel):
    """Structured evaluation of a submission."""

    eval_id: str = Field(default_factory=_uuid)
    submission_id: str
    user_id: str
    topic_id: str
    domain: str
    dimension_scores: list[DimensionScore] = Field(default_factory=list)
    overall_score: float = 0.0  # weighted average, 0–100
    llm_feedback: str = ""
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    missed_concepts: list[str] = Field(default_factory=list)
    improvement_suggestions: list[str] = Field(default_factory=list)
    mastery_estimate: float = 0.0
    next_action: str = "continue"  # continue | review | consolidate | final_test
    evaluated_at: datetime = Field(default_factory=_now)


class AssessmentRecord(BaseModel):
    """Baseline or periodic assessment result."""

    assessment_id: str = Field(default_factory=_uuid)
    user_id: str
    domain: str
    assessment_type: str = "baseline"
    passed: bool | None = None
    level: LearnerLevel = LearnerLevel.BEGINNER
    raw_answers: list[str] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    structured_scores: dict[str, float] = Field(default_factory=dict)
    recommended_plan_style: str = "blended"
    llm_feedback: str = ""
    evaluated_at: datetime = Field(default_factory=_now)


class RuntimeEvent(BaseModel):
    """Operational event for monitoring, auditing, and debugging."""

    event_id: str = Field(default_factory=_uuid)
    level: str = "info"
    category: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_now)
