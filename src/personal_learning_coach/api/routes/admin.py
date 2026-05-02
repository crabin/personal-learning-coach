"""Administrative routes for operational tasks."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from personal_learning_coach import data_store
from personal_learning_coach.api.routes.domains import _delete_records_for_domain
from personal_learning_coach.backup_service import create_backup, restore_backup
from personal_learning_coach.data_store import DATABASE_FILENAME
from personal_learning_coach.models import DomainStatus, UserProfile, UserRole
from personal_learning_coach.monitoring import current_alerts, recent_runtime_events, record_runtime_event
from personal_learning_coach.review_engine import generate_weekly_summary
from personal_learning_coach.security import (
    optional_api_key_admin_read,
    optional_api_key_admin_write,
    user_from_authorization,
)

router = APIRouter(prefix="/admin", tags=["admin"])


class BackupResponse(BaseModel):
    backup_path: str
    file_count: int
    message: str


class RuntimeEventResponse(BaseModel):
    event_id: str
    level: str
    category: str
    message: str
    details: dict[str, object]
    created_at: str


class AlertResponse(BaseModel):
    severity: str
    category: str
    message: str


class RestoreRequest(BaseModel):
    backup_path: str = ""


class RestoreResponse(BaseModel):
    restored_from: str
    file_count: int
    message: str


class AdminUserResponse(BaseModel):
    user_id: str
    name: str
    email: str
    role: str
    is_active: bool
    domain_count: int


class AdminDomainResponse(BaseModel):
    domain: str
    status: str
    total_topics: int
    mastered_topics: int
    review_due_topics: int
    avg_score: float


class UpdateUserRequest(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None


class AdminActionResponse(BaseModel):
    message: str


def require_admin_read_or_key(
    authorization: Annotated[str | None, Header()] = None,
    x_api_key: Annotated[str | None, Header()] = None,
) -> UserProfile | None:
    if optional_api_key_admin_read(x_api_key):
        return None
    if x_api_key:
        _record_admin_auth_failure()
    user = user_from_authorization(authorization)
    if user is None:
        raise HTTPException(status_code=401, detail="Login required")
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin role required")
    return user


def require_admin_write_or_key(
    authorization: Annotated[str | None, Header()] = None,
    x_api_key: Annotated[str | None, Header()] = None,
) -> UserProfile | None:
    if optional_api_key_admin_write(x_api_key):
        return None
    if x_api_key:
        _record_admin_auth_failure()
    user = user_from_authorization(authorization)
    if user is None:
        raise HTTPException(status_code=401, detail="Login required")
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin role required")
    return user


def _record_admin_auth_failure() -> None:
    record_runtime_event(
        level="warning",
        category="auth",
        message="Rejected admin request due to invalid API key",
    )


@router.post("/backup", response_model=BackupResponse)
def backup_data(_: Annotated[UserProfile | None, Depends(require_admin_write_or_key)]) -> BackupResponse:
    backup_path = create_backup()
    file_count = int((backup_path / DATABASE_FILENAME).exists())
    return BackupResponse(
        backup_path=str(backup_path),
        file_count=file_count,
        message="Backup created.",
    )


@router.get("/runtime-events", response_model=list[RuntimeEventResponse])
def list_runtime_events(
    limit: int = 20,
    _: Annotated[UserProfile | None, Depends(require_admin_read_or_key)] = None,
) -> list[RuntimeEventResponse]:
    events = recent_runtime_events(limit=limit)
    return [
        RuntimeEventResponse(
            event_id=event.event_id,
            level=event.level,
            category=event.category,
            message=event.message,
            details=event.details,
            created_at=event.created_at.isoformat(),
        )
        for event in events
    ]


@router.get("/alerts", response_model=list[AlertResponse])
def list_alerts(
    _: Annotated[UserProfile | None, Depends(require_admin_read_or_key)],
) -> list[AlertResponse]:
    return [AlertResponse(**alert) for alert in current_alerts()]


@router.post("/restore", response_model=RestoreResponse)
def restore_data(
    body: RestoreRequest,
    _: Annotated[UserProfile | None, Depends(require_admin_write_or_key)],
) -> RestoreResponse:
    restored_from = restore_backup(body.backup_path or None)
    file_count = int((restored_from / DATABASE_FILENAME).exists())
    return RestoreResponse(
        restored_from=str(restored_from),
        file_count=file_count,
        message="Backup restored.",
    )


@router.get("/users", response_model=list[AdminUserResponse])
def list_users(
    _: Annotated[UserProfile | None, Depends(require_admin_read_or_key)],
) -> list[AdminUserResponse]:
    users = sorted(data_store.user_profiles.all(), key=lambda user: user.created_at)
    return [
        AdminUserResponse(
            user_id=user.user_id,
            name=user.name,
            email=user.email,
            role=user.role.value,
            is_active=user.is_active,
            domain_count=len(data_store.domain_enrollments.filter(user_id=user.user_id)),
        )
        for user in users
    ]


@router.patch("/users/{user_id}", response_model=AdminUserResponse)
def update_user(
    user_id: str,
    body: UpdateUserRequest,
    _: Annotated[UserProfile | None, Depends(require_admin_write_or_key)],
) -> AdminUserResponse:
    user = _user_or_404(user_id)
    if body.role is not None:
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active
    data_store.user_profiles.save(user)
    return AdminUserResponse(
        user_id=user.user_id,
        name=user.name,
        email=user.email,
        role=user.role.value,
        is_active=user.is_active,
        domain_count=len(data_store.domain_enrollments.filter(user_id=user.user_id)),
    )


@router.get("/users/{user_id}/domains", response_model=list[AdminDomainResponse])
def list_user_domains(
    user_id: str,
    _: Annotated[UserProfile | None, Depends(require_admin_read_or_key)],
) -> list[AdminDomainResponse]:
    _user_or_404(user_id)
    return [_domain_response(user_id, enrollment.domain) for enrollment in data_store.domain_enrollments.filter(user_id=user_id)]


@router.post("/users/{user_id}/domains/{domain}/archive", response_model=AdminActionResponse)
def archive_user_domain(
    user_id: str,
    domain: str,
    _: Annotated[UserProfile | None, Depends(require_admin_write_or_key)],
) -> AdminActionResponse:
    enrollments = data_store.domain_enrollments.filter(user_id=user_id, domain=domain)
    if not enrollments:
        raise HTTPException(status_code=404, detail="Domain enrollment not found")
    enrollment = enrollments[0]
    enrollment.status = DomainStatus.ARCHIVED
    data_store.domain_enrollments.save(enrollment)
    return AdminActionResponse(message="Domain archived.")


@router.post("/users/{user_id}/domains/{domain}/reset", response_model=AdminActionResponse)
def reset_user_domain(
    user_id: str,
    domain: str,
    _: Annotated[UserProfile | None, Depends(require_admin_write_or_key)],
) -> AdminActionResponse:
    for progress in data_store.topic_progress.filter(user_id=user_id, domain=domain):
        data_store.topic_progress.delete(progress.progress_id)
    for submission in data_store.submission_records.filter(user_id=user_id, domain=domain):
        data_store.submission_records.delete(submission.submission_id)
    for evaluation in data_store.evaluation_records.filter(user_id=user_id, domain=domain):
        data_store.evaluation_records.delete(evaluation.eval_id)
    return AdminActionResponse(message="Domain progress reset.")


@router.delete("/users/{user_id}/domains/{domain}", response_model=AdminActionResponse)
def delete_user_domain(
    user_id: str,
    domain: str,
    _: Annotated[UserProfile | None, Depends(require_admin_write_or_key)],
) -> AdminActionResponse:
    _delete_records_for_domain(user_id, domain)
    return AdminActionResponse(message="Domain deleted.")


def _user_or_404(user_id: str) -> UserProfile:
    user = data_store.user_profiles.get(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def _domain_response(user_id: str, domain: str) -> AdminDomainResponse:
    summary = generate_weekly_summary(user_id, domain)
    enrollments = data_store.domain_enrollments.filter(user_id=user_id, domain=domain)
    status = enrollments[0].status.value if enrollments else DomainStatus.NOT_STARTED.value
    return AdminDomainResponse(
        domain=domain,
        status=status,
        total_topics=summary["total_topics"],
        mastered_topics=summary["mastered_topics"],
        review_due_topics=summary["review_due_topics"],
        avg_score=summary["avg_score"],
    )
