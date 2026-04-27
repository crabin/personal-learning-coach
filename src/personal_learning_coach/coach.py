"""CLI entry point for the Personal Learning Coach."""

from __future__ import annotations

import argparse
import logging
import os
import sys

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _cmd_assess(args: argparse.Namespace) -> None:
    from personal_learning_coach.level_tester import run_assessment

    print(f"Starting baseline assessment for domain: {args.domain}")
    questions = None  # generate via Claude
    print("Enter your answers to the assessment questions.")
    print("(In non-interactive mode, pass --answers 'a1|a2|a3')")

    if args.answers:
        answers = args.answers.split("|")
    else:
        from personal_learning_coach.level_tester import generate_assessment_questions

        questions = generate_assessment_questions(args.domain)
        answers = []
        for i, q in enumerate(questions, 1):
            print(f"\nQ{i}: {q}")
            answers.append(input("Your answer: ").strip())

    record = run_assessment(
        user_id=args.user_id,
        domain=args.domain,
        answers=answers,
        questions=questions,
    )
    print(f"\nAssessment complete. Level: {record.level.value}")
    print(f"Feedback: {record.llm_feedback}")


def _cmd_plan(args: argparse.Namespace) -> None:
    from personal_learning_coach import data_store
    from personal_learning_coach.models import LearnerLevel
    from personal_learning_coach.plan_generator import enroll_domain

    # Determine level from latest assessment or default
    assessments = data_store.assessment_records.filter(user_id=args.user_id, domain=args.domain)
    if assessments:
        latest = sorted(assessments, key=lambda a: a.evaluated_at, reverse=True)[0]
        level = latest.level
    else:
        level = LearnerLevel.BEGINNER

    enrollment, plan = enroll_domain(user_id=args.user_id, domain=args.domain, level=level)
    print(f"Plan generated: {len(plan.topics)} topics over {plan.total_weeks} weeks")
    for i, topic in enumerate(plan.topics, 1):
        print(f"  {i}. {topic.title}")


def _cmd_push(args: argparse.Namespace) -> None:
    from personal_learning_coach.content_pusher import push_today

    push = push_today(user_id=args.user_id, domain=args.domain)
    if push is None:
        print("No topic ready to push.")
        return
    print(f"Push delivered: {push.push_id}")
    print(f"Theory: {push.theory[:200]}...")


def _cmd_submit(args: argparse.Namespace) -> None:
    from personal_learning_coach import data_store
    from personal_learning_coach.evaluator import evaluate_submission
    from personal_learning_coach.mastery_engine import apply_evaluation
    from personal_learning_coach.models import SubmissionRecord, TopicStatus

    push = data_store.push_records.get(args.push_id)
    if push is None:
        print(f"Push not found: {args.push_id}", file=sys.stderr)
        sys.exit(1)

    submission = SubmissionRecord(
        user_id=args.user_id,
        push_id=args.push_id,
        topic_id=push.topic_id,
        domain=push.domain,
        raw_answer=args.answer,
    )
    data_store.submission_records.save(submission)

    evaluation = evaluate_submission(submission, push)

    progress_list = data_store.topic_progress.filter(user_id=args.user_id, topic_id=push.topic_id)
    if progress_list:
        progress_list[0].status = TopicStatus.SUBMITTED
        data_store.topic_progress.save(progress_list[0])
        apply_evaluation(evaluation, progress_list[0])

    print(f"Score: {evaluation.overall_score:.1f}")
    print(f"Next action: {evaluation.next_action}")
    print(f"Feedback: {evaluation.llm_feedback}")


def _cmd_report(args: argparse.Namespace) -> None:
    from personal_learning_coach.report_generator import save_report

    path = save_report(user_id=args.user_id, domain=args.domain)
    print(f"Report saved: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Personal Learning Coach CLI")
    parser.add_argument("--user-id", default="default_user", help="Learner user ID")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_assess = subparsers.add_parser("assess", help="Run baseline assessment")
    p_assess.add_argument("--domain", required=True)
    p_assess.add_argument("--answers", default="", help="Pipe-separated answers")

    p_plan = subparsers.add_parser("plan", help="Generate learning plan")
    p_plan.add_argument("--domain", required=True)

    p_push = subparsers.add_parser("push", help="Deliver today's push")
    p_push.add_argument("--domain", required=True)

    p_submit = subparsers.add_parser("submit", help="Submit an answer")
    p_submit.add_argument("--push-id", required=True)
    p_submit.add_argument("--answer", required=True)

    p_report = subparsers.add_parser("report", help="Generate progress report")
    p_report.add_argument("--domain", required=True)

    args = parser.parse_args()

    commands = {
        "assess": _cmd_assess,
        "plan": _cmd_plan,
        "push": _cmd_push,
        "submit": _cmd_submit,
        "report": _cmd_report,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
