"""Domain enrollment and status routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from personal_learning_coach import data_store
from personal_learning_coach.models import LearnerLevel

router = APIRouter(prefix="/domains", tags=["domains"])


class EnrollRequest(BaseModel):
    user_id: str
    level: LearnerLevel = LearnerLevel.BEGINNER
    preferences: dict[str, Any] = {}


class EnrollResponse(BaseModel):
    enrollment_id: str
    plan_id: str
    domain: str
    level: str
    status: str
    topic_count: int


@router.post("/{domain}/enroll", response_model=EnrollResponse)
def enroll_domain_route(domain: str, body: EnrollRequest) -> EnrollResponse:
    from personal_learning_coach.plan_generator import enroll_domain

    enrollment, plan = enroll_domain(
        user_id=body.user_id,
        domain=domain,
        level=body.level,
        preferences=body.preferences,
    )
    return EnrollResponse(
        enrollment_id=enrollment.enrollment_id,
        plan_id=plan.plan_id,
        domain=domain,
        level=enrollment.level.value,
        status=enrollment.status.value,
        topic_count=len(plan.topics),
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


@router.get("/{domain}/status", response_model=DomainStatusResponse)
def get_domain_status(domain: str, user_id: str) -> DomainStatusResponse:
    from personal_learning_coach.review_engine import generate_weekly_summary

    enrollments = data_store.domain_enrollments.filter(user_id=user_id, domain=domain)
    if not enrollments:
        raise HTTPException(status_code=404, detail="Domain enrollment not found")

    enrollment = enrollments[0]
    summary = generate_weekly_summary(user_id, domain)

    return DomainStatusResponse(
        domain=domain,
        user_id=user_id,
        status=enrollment.status.value,
        level=enrollment.level.value,
        total_topics=int(summary["total_topics"]),  # type: ignore[arg-type]
        mastered_topics=int(summary["mastered_topics"]),  # type: ignore[arg-type]
        review_due_topics=int(summary["review_due_topics"]),  # type: ignore[arg-type]
        avg_score=float(summary["avg_score"]),  # type: ignore[arg-type]
    )
