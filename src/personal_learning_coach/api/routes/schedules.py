"""Manual schedule trigger routes."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

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


@router.post("/trigger", response_model=TriggerResponse)
def trigger_push(body: TriggerRequest) -> TriggerResponse:
    from personal_learning_coach.content_pusher import push_today

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
    )
