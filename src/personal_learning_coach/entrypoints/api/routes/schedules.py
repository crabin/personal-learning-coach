"""Manual schedule trigger routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from personal_learning_coach.infrastructure.config import load_config
from personal_learning_coach.domain.models import PushRecord, UserProfile
from personal_learning_coach.infrastructure.security import authorize_user_scope, require_current_user

router = APIRouter(prefix="/schedules", tags=["schedules"])


class TriggerRequest(BaseModel):
    user_id: str
    domain: str


class TriggerResponse(BaseModel):
    push_id: str | None
    delivered: bool
    message: str
    push_type: str = ""
    topic_id: str = ""
    theory: str = ""
    basic_questions: list[str] = []
    practice_question: str = ""
    reflection_question: str = ""
    visual_url: str = ""


@router.post("/trigger", response_model=TriggerResponse)
def trigger_push(
    body: TriggerRequest,
    current_user: Annotated[UserProfile, Depends(require_current_user)],
) -> TriggerResponse:
    from personal_learning_coach.application.learning.content_pusher import push_today

    authorize_user_scope(body.user_id, current_user)
    push = push_today(user_id=body.user_id, domain=body.domain)
    if push is None:
        return TriggerResponse(push_id=None, delivered=False, message="No topic ready to push.")
    return TriggerResponse(
        push_id=push.push_id,
        delivered=True,
        message=f"Push delivered for topic {push.topic_id}.",
        push_type=push.push_type,
        topic_id=push.topic_id,
        theory=push.theory,
        basic_questions=[
            str(item)
            for item in push.content_snapshot.get("basic_questions", [])
            if isinstance(push.content_snapshot, dict)
        ],
        practice_question=push.practice_question,
        reflection_question=push.reflection_question,
        visual_url=_extract_visual_url(push),
    )


def _extract_visual_url(push: PushRecord) -> str:
    for snapshot in (push.content_snapshot, push.resource_snapshot):
        if not isinstance(snapshot, dict):
            continue
        for key in ("visual_url", "image_url", "cover_image_url"):
            value = snapshot.get(key)
            if isinstance(value, str) and value.strip():
                return _normalize_visual_url(value)
        for key in ("visual", "image", "cover_image"):
            nested = snapshot.get(key)
            if not isinstance(nested, dict):
                continue
            value = nested.get("url")
            if isinstance(value, str) and value.strip():
                return _normalize_visual_url(value)
    return _fallback_visual_url(push)


def _normalize_visual_url(value: str) -> str:
    normalized = value.strip().replace("\\", "/")
    if not normalized:
        return ""
    if normalized.startswith(("http://", "https://", "/data/images/")):
        return normalized
    if normalized.startswith("./data/images/"):
        return f"/{normalized[2:]}"
    if normalized.startswith("data/images/"):
        return f"/{normalized}"
    if normalized.startswith("images/"):
        return f"/data/{normalized}"
    return normalized


def _fallback_visual_url(push: PushRecord) -> str:
    images_dir = load_config().data_dir / "images"
    candidates = sorted(
        path
        for path in images_dir.iterdir()
        if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
    ) if images_dir.exists() else []
    if not candidates:
        return ""

    seed = (push.topic_id or push.push_id or push.domain).encode("utf-8")
    index = sum(seed) % len(candidates)
    relative = candidates[index].relative_to(images_dir).as_posix()
    return f"/data/images/{relative}"
