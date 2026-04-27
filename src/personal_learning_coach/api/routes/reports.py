"""Report generation routes."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/{domain}", response_class=HTMLResponse)
def get_report(domain: str, user_id: str) -> HTMLResponse:
    from personal_learning_coach.report_generator import render_html

    html = render_html(user_id, domain)
    return HTMLResponse(content=html)
