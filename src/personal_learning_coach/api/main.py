"""FastAPI application entry point."""

from __future__ import annotations

import logging
from hashlib import sha1
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from PIL import Image

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


@app.get("/data/images/{image_path:path}")
def serve_learning_image(
    image_path: str,
    variant: Literal["original", "preview"] = "original",
) -> FileResponse:
    config = load_config()
    images_dir = (config.data_dir / "images").resolve()
    requested = (images_dir / image_path).resolve()
    if not requested.is_file() or not requested.is_relative_to(images_dir):
        raise HTTPException(status_code=404, detail="Image not found")

    file_to_serve = requested if variant == "original" else _preview_image_path(requested, images_dir)
    headers = {
        "Cache-Control": "public, max-age=86400, stale-while-revalidate=604800",
    }
    return FileResponse(file_to_serve, headers=headers)


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


def _preview_image_path(image_path: Path, images_dir: Path) -> Path:
    if image_path.stat().st_size <= 2 * 1024 * 1024:
        return image_path

    cache_dir = images_dir / ".cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_key = sha1(
        f"{image_path.relative_to(images_dir)}::{image_path.stat().st_mtime_ns}".encode("utf-8")
    ).hexdigest()
    preview_path = cache_dir / f"{cache_key}.webp"
    if preview_path.is_file():
        return preview_path

    with Image.open(image_path) as source:
        source.thumbnail((1600, 900))
        preview = source.convert("RGB") if source.mode not in {"RGB", "L"} else source
        preview.save(preview_path, format="WEBP", quality=82, method=6)

    return preview_path
