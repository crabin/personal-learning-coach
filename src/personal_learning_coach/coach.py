"""CLI entry point for the Personal Learning Coach."""

from __future__ import annotations

import argparse
import logging
import sys

from dotenv import load_dotenv
from personal_learning_coach.monitoring import configure_logging

load_dotenv()
configure_logging()
logger = logging.getLogger(__name__)


def _plan_preferences(args: argparse.Namespace, level: object) -> dict[str, object]:
    target_level = getattr(args, "target_level", None) or level
    target_level_value = target_level.value if hasattr(target_level, "value") else str(target_level)
    return {
        "target_level": target_level_value,
        "daily_minutes": args.daily_minutes,
        "learning_style": args.learning_style,
        "delivery_time": args.delivery_time,
        "language": args.language,
        "allow_online_resources": args.allow_online_resources,
    }


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
    from personal_learning_coach.models import AssessmentRecord, LearnerLevel
    from personal_learning_coach.plan_generator import enroll_domain

    # Determine level from latest assessment or default
    assessments: list[AssessmentRecord] = data_store.assessment_records.filter(
        user_id=args.user_id, domain=args.domain
    )
    if assessments:
        latest = sorted(assessments, key=lambda a: a.evaluated_at, reverse=True)[0]
        level = latest.level
    else:
        level = LearnerLevel.BEGINNER

    preferences = _plan_preferences(args, level)
    enrollment, plan = enroll_domain(
        user_id=args.user_id,
        domain=args.domain,
        level=level,
        preferences=preferences,
    )
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


def _cmd_pause(args: argparse.Namespace) -> None:
    from personal_learning_coach import data_store
    from personal_learning_coach.models import DomainEnrollment, DomainStatus

    enrollments: list[DomainEnrollment] = data_store.domain_enrollments.filter(
        user_id=args.user_id, domain=args.domain
    )
    if not enrollments:
        print(f"Domain enrollment not found: {args.domain}", file=sys.stderr)
        sys.exit(1)
    enrollment = enrollments[0]
    enrollment.status = DomainStatus.PAUSED
    data_store.domain_enrollments.save(enrollment)
    print(f"Domain paused: {args.domain}")


def _cmd_resume(args: argparse.Namespace) -> None:
    from personal_learning_coach import data_store
    from personal_learning_coach.models import DomainEnrollment, DomainStatus

    enrollments: list[DomainEnrollment] = data_store.domain_enrollments.filter(
        user_id=args.user_id, domain=args.domain
    )
    if not enrollments:
        print(f"Domain enrollment not found: {args.domain}", file=sys.stderr)
        sys.exit(1)
    enrollment = enrollments[0]
    enrollment.status = DomainStatus.ACTIVE
    data_store.domain_enrollments.save(enrollment)
    print(f"Domain resumed: {args.domain}")


def _cmd_archive(args: argparse.Namespace) -> None:
    from personal_learning_coach import data_store
    from personal_learning_coach.models import DomainEnrollment, DomainStatus

    enrollments: list[DomainEnrollment] = data_store.domain_enrollments.filter(
        user_id=args.user_id, domain=args.domain
    )
    if not enrollments:
        print(f"Domain enrollment not found: {args.domain}", file=sys.stderr)
        sys.exit(1)
    enrollment = enrollments[0]
    enrollment.status = DomainStatus.ARCHIVED
    data_store.domain_enrollments.save(enrollment)
    print(f"Domain archived: {args.domain}")


def _cmd_delete_domain(args: argparse.Namespace) -> None:
    from personal_learning_coach.api.routes.domains import _delete_records_for_domain
    from personal_learning_coach import data_store
    from personal_learning_coach.models import DomainEnrollment

    enrollments: list[DomainEnrollment] = data_store.domain_enrollments.filter(
        user_id=args.user_id, domain=args.domain
    )
    if not enrollments:
        print(f"Domain enrollment not found: {args.domain}", file=sys.stderr)
        sys.exit(1)
    if not args.confirm_delete:
        print("Domain deletion requires --confirm-delete", file=sys.stderr)
        sys.exit(1)
    _delete_records_for_domain(args.user_id, args.domain)
    print(f"Domain deleted: {args.domain}")


def _cmd_final_assessment(args: argparse.Namespace) -> None:
    from personal_learning_coach.mastery_engine import submit_final_assessment

    if not args.passed and not args.failed:
        print("Final assessment requires either --passed or --failed", file=sys.stderr)
        sys.exit(1)

    try:
        _record, enrollment = submit_final_assessment(
            user_id=args.user_id,
            domain=args.domain,
            passed=bool(args.passed),
            score=args.score,
            feedback=args.feedback,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

    print(f"Final assessment submitted. Domain status: {enrollment.status.value}")


def _cmd_backup(args: argparse.Namespace) -> None:
    from personal_learning_coach.backup_service import create_backup

    path = create_backup()
    print(f"Backup created: {path}")


def _cmd_restore(args: argparse.Namespace) -> None:
    from personal_learning_coach.backup_service import restore_backup

    path = restore_backup(args.backup_path or None)
    print(f"Backup restored: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Personal Learning Coach CLI")
    parser.add_argument("--user-id", default="default_user", help="Learner user ID")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_assess = subparsers.add_parser("assess", help="Run baseline assessment")
    p_assess.add_argument("--domain", required=True)
    p_assess.add_argument("--answers", default="", help="Pipe-separated answers")

    p_plan = subparsers.add_parser("plan", help="Generate learning plan")
    p_plan.add_argument("--domain", required=True)
    p_plan.add_argument("--target-level", choices=["beginner", "intermediate", "advanced"])
    p_plan.add_argument("--daily-minutes", type=int, default=60)
    p_plan.add_argument("--learning-style", default="blended")
    p_plan.add_argument("--delivery-time", default="09:00")
    p_plan.add_argument("--language", default="zh")
    p_plan.add_argument("--allow-online-resources", dest="allow_online_resources", action="store_true")
    p_plan.add_argument("--no-online-resources", dest="allow_online_resources", action="store_false")
    p_plan.set_defaults(allow_online_resources=True)

    p_push = subparsers.add_parser("push", help="Deliver today's push")
    p_push.add_argument("--domain", required=True)

    p_submit = subparsers.add_parser("submit", help="Submit an answer")
    p_submit.add_argument("--push-id", required=True)
    p_submit.add_argument("--answer", required=True)

    p_report = subparsers.add_parser("report", help="Generate progress report")
    p_report.add_argument("--domain", required=True)

    p_pause = subparsers.add_parser("pause", help="Pause a domain enrollment")
    p_pause.add_argument("--domain", required=True)

    p_resume = subparsers.add_parser("resume", help="Resume a domain enrollment")
    p_resume.add_argument("--domain", required=True)

    p_archive = subparsers.add_parser("archive", help="Archive a domain enrollment")
    p_archive.add_argument("--domain", required=True)

    p_delete = subparsers.add_parser("delete-domain", help="Delete a domain and related records")
    p_delete.add_argument("--domain", required=True)
    p_delete.add_argument("--confirm-delete", action="store_true")

    p_final = subparsers.add_parser("final-assessment", help="Submit a final assessment result")
    p_final.add_argument("--domain", required=True)
    p_final.add_argument("--passed", action="store_true")
    p_final.add_argument("--failed", action="store_true")
    p_final.add_argument("--score", type=float, default=0.0)
    p_final.add_argument("--feedback", default="")

    subparsers.add_parser("backup", help="Create a backup of JSON data files")
    p_restore = subparsers.add_parser("restore", help="Restore JSON data files from a backup")
    p_restore.add_argument("--backup-path", default="")

    args = parser.parse_args()

    commands = {
        "assess": _cmd_assess,
        "plan": _cmd_plan,
        "push": _cmd_push,
        "submit": _cmd_submit,
        "report": _cmd_report,
        "pause": _cmd_pause,
        "resume": _cmd_resume,
        "archive": _cmd_archive,
        "delete-domain": _cmd_delete_domain,
        "final-assessment": _cmd_final_assessment,
        "backup": _cmd_backup,
        "restore": _cmd_restore,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
