"""FastAPI application entry point."""

from __future__ import annotations

import logging

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from personal_learning_coach.api.routes import admin, domains, reports, schedules, submissions
from personal_learning_coach.config import load_config
from personal_learning_coach.monitoring import configure_logging, record_runtime_event

load_dotenv()
configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Personal Learning Coach",
    description="Closed-loop AI learning coaching API",
    version="0.1.0",
)

app.include_router(domains.router)
app.include_router(submissions.router)
app.include_router(reports.router)
app.include_router(schedules.router)
app.include_router(admin.router)


@app.get("/boom")
def boom() -> dict[str, str]:
    raise RuntimeError("boom")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled application error on %s", request.url.path)
    record_runtime_event(
        level="error",
        category="exception",
        message=str(exc),
        details={"path": request.url.path},
    )
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health")
def health() -> dict[str, object]:
    config = load_config()
    issues = config.validate_runtime()
    return {
        "status": "ok" if not issues else "degraded",
        "delivery_mode": config.delivery_mode,
        "auth_enabled": bool(config.api_auth_token or config.admin_read_token or config.admin_write_token),
        "backup_dir": str(config.backup_dir),
        "issues": issues,
    }
