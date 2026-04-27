"""FastAPI application entry point."""

from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI

from personal_learning_coach.api.routes import domains, reports, schedules, submissions

load_dotenv()

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

app = FastAPI(
    title="Personal Learning Coach",
    description="Closed-loop AI learning coaching API",
    version="0.1.0",
)

app.include_router(domains.router)
app.include_router(submissions.router)
app.include_router(reports.router)
app.include_router(schedules.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
