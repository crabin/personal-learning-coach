"""Administrative routes for operational tasks."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from personal_learning_coach.backup_service import create_backup, restore_backup
from personal_learning_coach.monitoring import current_alerts, recent_runtime_events
from personal_learning_coach.security import require_admin_read, require_admin_write

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


@router.post("/backup", response_model=BackupResponse)
def backup_data(_: None = Depends(require_admin_write)) -> BackupResponse:
    backup_path = create_backup()
    file_count = len(list(backup_path.glob("*.json")))
    return BackupResponse(
        backup_path=str(backup_path),
        file_count=file_count,
        message="Backup created.",
    )


@router.get("/runtime-events", response_model=list[RuntimeEventResponse])
def list_runtime_events(limit: int = 20, _: None = Depends(require_admin_read)) -> list[RuntimeEventResponse]:
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
def list_alerts(_: None = Depends(require_admin_read)) -> list[AlertResponse]:
    return [AlertResponse(**alert) for alert in current_alerts()]


@router.post("/restore", response_model=RestoreResponse)
def restore_data(body: RestoreRequest, _: None = Depends(require_admin_write)) -> RestoreResponse:
    restored_from = restore_backup(body.backup_path or None)
    file_count = len(list(restored_from.glob("*.json")))
    return RestoreResponse(
        restored_from=str(restored_from),
        file_count=file_count,
        message="Backup restored.",
    )
