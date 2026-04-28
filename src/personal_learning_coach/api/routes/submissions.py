"""Submission intake and evaluation routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from personal_learning_coach import data_store
from personal_learning_coach.evaluator import evaluate_submission
from personal_learning_coach.mastery_engine import apply_evaluation
from personal_learning_coach.models import DomainStatus, SubmissionRecord, TopicStatus

router = APIRouter(prefix="/submissions", tags=["submissions"])


class SubmitRequest(BaseModel):
    user_id: str
    push_id: str
    raw_answer: str
    practice_result: str = ""
    normalized_answer: str = ""
    parsing_notes: str = ""


class SubmitResponse(BaseModel):
    submission_id: str
    eval_id: str
    overall_score: float
    next_action: str
    feedback: str


@router.post("", response_model=SubmitResponse)
def submit_answer(body: SubmitRequest) -> SubmitResponse:
    push = data_store.push_records.get(body.push_id)
    if push is None:
        raise HTTPException(status_code=404, detail="Push not found")

    submission = SubmissionRecord(
        user_id=body.user_id,
        push_id=body.push_id,
        topic_id=push.topic_id,
        domain=push.domain,
        raw_answer=body.raw_answer,
        practice_result=body.practice_result,
        normalized_answer=body.normalized_answer,
        parsing_notes=body.parsing_notes,
    )
    data_store.submission_records.save(submission)

    evaluation = evaluate_submission(submission, push)

    progress_list = data_store.topic_progress.filter(
        user_id=body.user_id, topic_id=push.topic_id
    )
    if progress_list:
        progress_list[0].status = TopicStatus.SUBMITTED
        data_store.topic_progress.save(progress_list[0])
        apply_evaluation(evaluation, progress_list[0])

    enrollments = data_store.domain_enrollments.filter(user_id=body.user_id, domain=push.domain)
    if enrollments and enrollments[0].status == DomainStatus.AWAITING_SUBMISSION:
        enrollments[0].status = DomainStatus.ACTIVE
        data_store.domain_enrollments.save(enrollments[0])

    return SubmitResponse(
        submission_id=submission.submission_id,
        eval_id=evaluation.eval_id,
        overall_score=evaluation.overall_score,
        next_action=evaluation.next_action,
        feedback=evaluation.llm_feedback,
    )
