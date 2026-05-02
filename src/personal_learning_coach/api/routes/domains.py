"""Domain enrollment, lifecycle, and status routes."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from personal_learning_coach import data_store
from personal_learning_coach.models import (
    DomainEnrollment,
    DomainStatus,
    LearnerLevel,
    TopicStatus,
    UserProfile,
    UserRole,
)
from personal_learning_coach.review_engine import WeeklySummary, generate_weekly_summary, select_active_plan
from personal_learning_coach.security import authorize_user_scope, require_current_user

router = APIRouter(prefix="/domains", tags=["domains"])


class EnrollRequest(BaseModel):
    user_id: str
    level: LearnerLevel = LearnerLevel.BEGINNER
    target_level: LearnerLevel | None = None
    daily_minutes: int = 60
    learning_style: str = "blended"
    delivery_time: str = "09:00"
    language: str = "zh"
    allow_online_resources: bool = True
    preferences: dict[str, Any] = Field(default_factory=dict)


class EnrollResponse(BaseModel):
    enrollment_id: str
    plan_id: str
    domain: str
    level: str
    status: str
    topic_count: int
    current_level: str
    target_level: str
    daily_minutes: int
    learning_style: str
    delivery_time: str
    language: str
    allow_online_resources: bool


@router.post("/{domain}/enroll", response_model=EnrollResponse)
def enroll_domain_route(
    domain: str,
    body: EnrollRequest,
    current_user: Annotated[UserProfile, Depends(require_current_user)],
) -> EnrollResponse:
    from personal_learning_coach.plan_generator import enroll_domain

    authorize_user_scope(body.user_id, current_user)
    preferences = {
        **body.preferences,
        "target_level": (body.target_level or body.level).value,
        "daily_minutes": body.daily_minutes,
        "learning_style": body.learning_style,
        "delivery_time": body.delivery_time,
        "language": body.language,
        "allow_online_resources": body.allow_online_resources,
    }
    enrollment, plan = enroll_domain(
        user_id=body.user_id,
        domain=domain,
        level=body.level,
        preferences=preferences,
    )
    return EnrollResponse(
        enrollment_id=enrollment.enrollment_id,
        plan_id=plan.plan_id,
        domain=domain,
        level=enrollment.level.value,
        status=enrollment.status.value,
        topic_count=len(plan.topics),
        current_level=(enrollment.current_level or enrollment.level).value,
        target_level=(enrollment.target_level or enrollment.level).value,
        daily_minutes=enrollment.daily_minutes,
        learning_style=enrollment.learning_style,
        delivery_time=enrollment.delivery_time,
        language=enrollment.language,
        allow_online_resources=enrollment.allow_online_resources,
    )


class DomainStatusResponse(BaseModel):
    domain: str
    user_id: str
    status: str
    level: str
    total_topics: int
    mastered_topics: int
    review_due_topics: int
    avg_score: float


class DomainSummaryTopic(BaseModel):
    title: str
    mastery_percent: int


class DomainSummaryResponse(BaseModel):
    domain: str
    user_id: str
    status: str
    current_level: str
    target_level: str
    mastery_percent: int
    avg_score: float
    active_topic_title: str
    active_topic_id: str
    topic_progress: list[DomainSummaryTopic] = Field(default_factory=list)


class DomainOptionResponse(BaseModel):
    domain: str
    label: str


class DomainLifecycleRequest(BaseModel):
    user_id: str


class DeleteDomainRequest(BaseModel):
    user_id: str
    confirm: bool = False


class DomainLifecycleResponse(BaseModel):
    domain: str
    user_id: str
    status: str
    message: str


class DeleteDomainResponse(BaseModel):
    domain: str
    user_id: str
    deleted: bool
    message: str


class FinalAssessmentRequest(BaseModel):
    user_id: str
    passed: bool
    score: float = 0.0
    feedback: str = ""


class FinalAssessmentResponse(BaseModel):
    domain: str
    user_id: str
    status: str
    passed: bool
    assessment_id: str
    score: float
    message: str


def _get_enrollment_or_404(user_id: str, domain: str) -> DomainEnrollment:
    enrollments: list[DomainEnrollment] = data_store.domain_enrollments.filter(user_id=user_id, domain=domain)
    if not enrollments:
        raise HTTPException(status_code=404, detail="Domain enrollment not found")
    return enrollments[0]


def _delete_records_for_domain(user_id: str, domain: str) -> None:
    history_records = data_store.question_history.filter(user_id=user_id, domain=domain)
    for history_record in history_records:
        Path(history_record.json_path).unlink(missing_ok=True)

    stores = (
        data_store.domain_enrollments,
        data_store.learning_plans,
        data_store.topic_progress,
        data_store.push_records,
        data_store.question_history,
        data_store.submission_records,
        data_store.evaluation_records,
        data_store.assessment_records,
    )
    for store in stores:
        records = store.filter(user_id=user_id, domain=domain)
        for record in records:
            record_id = getattr(record, next(f for f in type(record).model_fields if f.endswith("_id")))
            store.delete(record_id)


@router.get("", response_model=list[DomainOptionResponse])
def list_domains(
    current_user: Annotated[UserProfile, Depends(require_current_user)],
) -> list[DomainOptionResponse]:
    if current_user.role == UserRole.ADMIN:
        enrollments = data_store.domain_enrollments.all()
        plans = data_store.learning_plans.all()
    else:
        enrollments = data_store.domain_enrollments.filter(user_id=current_user.user_id)
        plans = data_store.learning_plans.filter(user_id=current_user.user_id)
    domains = sorted({*(enrollment.domain for enrollment in enrollments), *(plan.domain for plan in plans)})
    return [DomainOptionResponse(domain=domain, label=_domain_label(domain)) for domain in domains]


@router.get("/{domain}/status", response_model=DomainStatusResponse)
def get_domain_status(
    domain: str,
    user_id: str,
    current_user: Annotated[UserProfile, Depends(require_current_user)],
) -> DomainStatusResponse:
    from personal_learning_coach.review_engine import generate_weekly_summary

    authorize_user_scope(user_id, current_user)
    enrollment = _get_enrollment_or_404(user_id, domain)
    summary: WeeklySummary = generate_weekly_summary(user_id, domain)

    return DomainStatusResponse(
        domain=domain,
        user_id=user_id,
        status=enrollment.status.value,
        level=enrollment.level.value,
        total_topics=summary["total_topics"],
        mastered_topics=summary["mastered_topics"],
        review_due_topics=summary["review_due_topics"],
        avg_score=summary["avg_score"],
    )


@router.get("/{domain}/summary", response_model=DomainSummaryResponse)
def get_domain_summary(
    domain: str,
    user_id: str,
    current_user: Annotated[UserProfile, Depends(require_current_user)],
) -> DomainSummaryResponse:
    authorize_user_scope(user_id, current_user)
    summary: WeeklySummary = generate_weekly_summary(user_id, domain)
    enrollment_list: list[DomainEnrollment] = data_store.domain_enrollments.filter(user_id=user_id, domain=domain)
    enrollment = enrollment_list[0] if enrollment_list else None
    active_plan = select_active_plan(user_id, domain)
    ordered_topics = active_plan.topics if active_plan else []
    progress_by_topic = {
        progress.topic_id: progress
        for progress in data_store.topic_progress.filter(user_id=user_id, domain=domain)
    }
    summary_by_topic = {item["topic_id"]: item for item in summary["topic_summaries"]}

    topic_progress = [
        DomainSummaryTopic(
            title=topic.title,
            mastery_percent=_topic_mastery_percent(topic.topic_id, summary_by_topic, progress_by_topic),
        )
        for topic in ordered_topics[:3]
    ]
    active_topic = _select_active_topic(ordered_topics, progress_by_topic)

    default_level = LearnerLevel.BEGINNER.value
    return DomainSummaryResponse(
        domain=domain,
        user_id=user_id,
        status=enrollment.status.value if enrollment else DomainStatus.NOT_STARTED.value,
        current_level=(enrollment.current_level or enrollment.level).value if enrollment else default_level,
        target_level=(enrollment.target_level or enrollment.level).value if enrollment else default_level,
        mastery_percent=round(summary["mastery_rate"] * 100),
        avg_score=summary["avg_score"],
        active_topic_title=active_topic.title if active_topic else domain,
        active_topic_id=active_topic.topic_id if active_topic else "",
        topic_progress=topic_progress,
    )


@router.post("/{domain}/pause", response_model=DomainLifecycleResponse)
def pause_domain(
    domain: str,
    body: DomainLifecycleRequest,
    current_user: Annotated[UserProfile, Depends(require_current_user)],
) -> DomainLifecycleResponse:
    authorize_user_scope(body.user_id, current_user)
    enrollment = _get_enrollment_or_404(body.user_id, domain)
    enrollment.status = DomainStatus.PAUSED
    data_store.domain_enrollments.save(enrollment)
    return DomainLifecycleResponse(
        domain=domain,
        user_id=body.user_id,
        status=enrollment.status.value,
        message="Domain paused.",
    )


@router.post("/{domain}/resume", response_model=DomainLifecycleResponse)
def resume_domain(
    domain: str,
    body: DomainLifecycleRequest,
    current_user: Annotated[UserProfile, Depends(require_current_user)],
) -> DomainLifecycleResponse:
    authorize_user_scope(body.user_id, current_user)
    enrollment = _get_enrollment_or_404(body.user_id, domain)
    enrollment.status = DomainStatus.ACTIVE
    data_store.domain_enrollments.save(enrollment)
    return DomainLifecycleResponse(
        domain=domain,
        user_id=body.user_id,
        status=enrollment.status.value,
        message="Domain resumed.",
    )


@router.post("/{domain}/archive", response_model=DomainLifecycleResponse)
def archive_domain(
    domain: str,
    body: DomainLifecycleRequest,
    current_user: Annotated[UserProfile, Depends(require_current_user)],
) -> DomainLifecycleResponse:
    authorize_user_scope(body.user_id, current_user)
    enrollment = _get_enrollment_or_404(body.user_id, domain)
    enrollment.status = DomainStatus.ARCHIVED
    data_store.domain_enrollments.save(enrollment)
    return DomainLifecycleResponse(
        domain=domain,
        user_id=body.user_id,
        status=enrollment.status.value,
        message="Domain archived.",
    )


def _topic_mastery_percent(
    topic_id: str,
    summary_by_topic: dict[str, Any],
    progress_by_topic: dict[str, Any],
) -> int:
    if topic_id in summary_by_topic:
        return round(float(summary_by_topic[topic_id]["mastery_score"]))
    progress = progress_by_topic.get(topic_id)
    if progress is None:
        return 0
    return round(float(progress.mastery_score))


def _select_active_topic(topics: list[Any], progress_by_topic: dict[str, Any]) -> Any | None:
    active_statuses = {
        TopicStatus.PUSHED.value,
        TopicStatus.STUDYING.value,
        TopicStatus.SUBMITTED.value,
        TopicStatus.EVALUATED.value,
        TopicStatus.REVIEW_DUE.value,
        TopicStatus.READY.value,
        TopicStatus.MASTERED.value,
    }
    for topic in topics:
        progress = progress_by_topic.get(topic.topic_id)
        if progress and progress.status.value in active_statuses:
            return topic
    return topics[0] if topics else None


def _domain_label(domain: str) -> str:
    predefined = {
        "ai_agent": "AI Agent",
        "fullstack_development": "全栈开发",
        "model_training": "模型训练",
        "data_structure": "数据结构",
        "system_design": "系统设计",
    }
    if domain in predefined:
        return predefined[domain]
    return domain.replace("_", " ").strip().title() or domain


@router.delete("/{domain}", response_model=DeleteDomainResponse)
def delete_domain(
    domain: str,
    body: DeleteDomainRequest,
    current_user: Annotated[UserProfile, Depends(require_current_user)],
) -> DeleteDomainResponse:
    authorize_user_scope(body.user_id, current_user)
    _get_enrollment_or_404(body.user_id, domain)
    if not body.confirm:
        raise HTTPException(status_code=400, detail="Deletion requires confirm=true")
    _delete_records_for_domain(body.user_id, domain)
    return DeleteDomainResponse(
        domain=domain,
        user_id=body.user_id,
        deleted=True,
        message="Domain data deleted.",
    )


@router.post("/{domain}/final-assessment", response_model=FinalAssessmentResponse)
def submit_final_assessment_route(
    domain: str,
    body: FinalAssessmentRequest,
    current_user: Annotated[UserProfile, Depends(require_current_user)],
) -> FinalAssessmentResponse:
    from personal_learning_coach.mastery_engine import submit_final_assessment

    authorize_user_scope(body.user_id, current_user)
    try:
        record, enrollment = submit_final_assessment(
            user_id=body.user_id,
            domain=domain,
            passed=body.passed,
            score=body.score,
            feedback=body.feedback,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return FinalAssessmentResponse(
        domain=domain,
        user_id=body.user_id,
        status=enrollment.status.value,
        passed=body.passed,
        assessment_id=record.assessment_id,
        score=body.score,
        message="Final assessment submitted.",
    )
