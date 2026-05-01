"""Domain enrollment, lifecycle, and status routes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from personal_learning_coach import data_store
from personal_learning_coach.models import DomainEnrollment, DomainStatus, LearnerLevel
from personal_learning_coach.review_engine import WeeklySummary

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
def enroll_domain_route(domain: str, body: EnrollRequest) -> EnrollResponse:
    from personal_learning_coach.plan_generator import enroll_domain

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


@router.get("/{domain}/status", response_model=DomainStatusResponse)
def get_domain_status(domain: str, user_id: str) -> DomainStatusResponse:
    from personal_learning_coach.review_engine import generate_weekly_summary

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


@router.post("/{domain}/pause", response_model=DomainLifecycleResponse)
def pause_domain(domain: str, body: DomainLifecycleRequest) -> DomainLifecycleResponse:
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
def resume_domain(domain: str, body: DomainLifecycleRequest) -> DomainLifecycleResponse:
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
def archive_domain(domain: str, body: DomainLifecycleRequest) -> DomainLifecycleResponse:
    enrollment = _get_enrollment_or_404(body.user_id, domain)
    enrollment.status = DomainStatus.ARCHIVED
    data_store.domain_enrollments.save(enrollment)
    return DomainLifecycleResponse(
        domain=domain,
        user_id=body.user_id,
        status=enrollment.status.value,
        message="Domain archived.",
    )


@router.delete("/{domain}", response_model=DeleteDomainResponse)
def delete_domain(domain: str, body: DeleteDomainRequest) -> DeleteDomainResponse:
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
    domain: str, body: FinalAssessmentRequest
) -> FinalAssessmentResponse:
    from personal_learning_coach.mastery_engine import submit_final_assessment

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
