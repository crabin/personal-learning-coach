"""Report generation routes."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/{domain}")
def get_report(domain: str, user_id: str) -> dict[str, object]:
    from personal_learning_coach.report_generator import generate_report_payload

    return generate_report_payload(user_id, domain)
