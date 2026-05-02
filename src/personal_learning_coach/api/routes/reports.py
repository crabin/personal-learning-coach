"""Report generation routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from personal_learning_coach.models import UserProfile
from personal_learning_coach.security import authorize_user_scope, require_current_user

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/{domain}")
def get_report(
    domain: str,
    user_id: str,
    current_user: Annotated[UserProfile, Depends(require_current_user)],
) -> dict[str, object]:
    from personal_learning_coach.report_generator import generate_report_payload

    authorize_user_scope(user_id, current_user)
    return generate_report_payload(user_id, domain)
