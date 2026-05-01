"""Generate HTML and JSON learning progress reports."""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, BaseLoader

from personal_learning_coach import data_store
from personal_learning_coach.mastery_engine import sync_unapplied_evaluations
from personal_learning_coach.models import DomainEnrollment, DomainStatus, EvaluationRecord
from personal_learning_coach.review_engine import WeeklySummary, generate_weekly_summary, select_active_plan

logger = logging.getLogger(__name__)

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Learning Report — {{ domain }}</title>
  <style>
    body { font-family: sans-serif; max-width: 800px; margin: 2rem auto; color: #333; }
    h1 { color: #2c5282; }
    h2 { color: #2d3748; border-bottom: 1px solid #e2e8f0; padding-bottom: 0.25rem; }
    .stat { display: inline-block; margin: 0.5rem 1rem 0.5rem 0; }
    .stat span { font-size: 1.8rem; font-weight: bold; color: #3182ce; }
    table { border-collapse: collapse; width: 100%; margin-top: 1rem; }
    th, td { text-align: left; padding: 0.5rem 0.75rem; border-bottom: 1px solid #e2e8f0; }
    th { background: #ebf8ff; }
    .mastered { color: #276749; }
    .review_due { color: #c05621; }
    .ready { color: #2b6cb0; }
    .locked { color: #718096; }
  </style>
</head>
<body>
  <h1>Learning Report</h1>
  <p><strong>Domain:</strong> {{ domain }} &nbsp;|&nbsp;
     <strong>User:</strong> {{ user_id }} &nbsp;|&nbsp;
     <strong>Generated:</strong> {{ generated_at }}</p>

  <h2>Summary</h2>
  <div>
    <div class="stat">Total topics <span>{{ summary.total_topics }}</span></div>
    <div class="stat">Mastered <span>{{ summary.mastered_topics }}</span></div>
    <div class="stat">Mastery rate <span>{{ "%.0f"|format(summary.mastery_rate * 100) }}%</span></div>
    <div class="stat">Avg score <span>{{ summary.avg_score }}</span></div>
  </div>

  <h2>Topic Details</h2>
  <table>
    <thead>
      <tr>
        <th>#</th><th>Topic</th><th>Status</th><th>Mastery</th><th>Avg Score</th><th>Attempts</th>
      </tr>
    </thead>
    <tbody>
    {% for i, t in topic_rows %}
      <tr>
        <td>{{ i }}</td>
        <td>{{ t.title }}</td>
        <td class="{{ t.status }}">{{ t.status }}</td>
        <td>{{ "%.1f"|format(t.mastery_score) }}</td>
        <td>{{ t.avg_score if t.avg_score is not none else "—" }}</td>
        <td>{{ t.attempts }}</td>
      </tr>
    {% endfor %}
    </tbody>
  </table>

  <h2>Recent Evaluations</h2>
  <table>
    <thead><tr><th>Date</th><th>Score</th><th>Action</th><th>Feedback</th></tr></thead>
    <tbody>
    {% for ev in recent_evals %}
      <tr>
        <td>{{ ev.evaluated_at.strftime("%Y-%m-%d %H:%M") }}</td>
        <td>{{ ev.overall_score }}</td>
        <td>{{ ev.next_action }}</td>
        <td>{{ ev.llm_feedback[:100] }}{% if ev.llm_feedback|length > 100 %}…{% endif %}</td>
      </tr>
    {% endfor %}
    {% if not recent_evals %}
      <tr><td colspan="4">No evaluations yet.</td></tr>
    {% endif %}
    </tbody>
  </table>

  <h2>Stage Summary</h2>
  <p>{{ insights.stage_summary }}</p>

  <h2>Learning Insights</h2>
  <p><strong>Trend:</strong> {{ insights.score_trend }}</p>
  <p><strong>Top strengths:</strong> {{ insights.top_strengths|join(", ") if insights.top_strengths else "—" }}</p>
  <p><strong>Top weaknesses:</strong> {{ insights.top_weaknesses|join(", ") if insights.top_weaknesses else "—" }}</p>
  <p><strong>Common missed concepts:</strong> {{ insights.common_missed_concepts|join(", ") if insights.common_missed_concepts else "—" }}</p>
  <p><strong>Final assessment ready:</strong> {{ "yes" if insights.final_assessment_ready else "no" }}</p>
</body>
</html>
"""


def _resolve_topic_titles(user_id: str, domain: str) -> dict[str, str]:
    active_plan = select_active_plan(user_id, domain)
    if active_plan is None:
        return {}
    return {t.topic_id: t.title for t in active_plan.topics}


class _TopicRow:
    def __init__(
        self,
        title: str,
        status: str,
        mastery_score: float,
        avg_score: float | None,
        attempts: int,
    ) -> None:
        self.title = title
        self.status = status
        self.mastery_score = mastery_score
        self.avg_score = avg_score
        self.attempts = attempts


def _score_trend(recent_evals: list[EvaluationRecord]) -> str:
    if len(recent_evals) < 2:
        return "stable"
    chronological = sorted(recent_evals, key=lambda e: e.evaluated_at)
    if chronological[-1].overall_score > chronological[0].overall_score:
        return "improving"
    if chronological[-1].overall_score < chronological[0].overall_score:
        return "declining"
    return "stable"


def _top_items(values: list[str], limit: int = 3) -> list[str]:
    counts: dict[str, int] = {}
    for value in values:
        if value:
            counts[value] = counts.get(value, 0) + 1
    return [item for item, _count in sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))[:limit]]


def _stage_summary(
    enrollment_status: str | None,
    mastery_rate: float,
    score_trend: str,
    review_due_topics: int,
) -> str:
    if enrollment_status == DomainStatus.FINAL_ASSESSMENT_DUE.value:
        return "The learner has mastered all planned topics and is ready for final assessment."
    if enrollment_status == DomainStatus.COMPLETED.value:
        return "The learner has completed the domain and passed the final assessment milestone."
    if review_due_topics > 0:
        return "The learner is progressing, but review tasks are due and should be prioritized."
    if mastery_rate >= 0.75 and score_trend == "improving":
        return "The learner is making strong progress with an improving score trend."
    return "The learner is actively progressing through the plan and building mastery incrementally."


def generate_report(user_id: str, domain: str) -> dict[str, Any]:
    """Build a full progress report dict (used for both HTML and JSON).

    Returns:
        Dict containing summary, topic details, and recent evaluations.
    """
    synced_evaluations = sync_unapplied_evaluations(user_id, domain)
    if synced_evaluations:
        logger.info(
            "Synced %d unapplied evaluations before report user=%s domain=%s",
            synced_evaluations,
            user_id,
            domain,
        )
    summary: WeeklySummary = generate_weekly_summary(user_id, domain)
    titles = _resolve_topic_titles(user_id, domain)

    topic_rows: list[_TopicRow] = []
    for ts in summary["topic_summaries"]:
        topic_rows.append(
            _TopicRow(
                title=titles.get(ts["topic_id"], ts["topic_id"]),
                status=ts["status"],
                mastery_score=ts["mastery_score"],
                avg_score=ts["avg_eval_score"],
                attempts=ts["attempts"],
            )
        )

    evals: list[EvaluationRecord] = data_store.evaluation_records.filter(user_id=user_id, domain=domain)
    recent_evals = sorted(evals, key=lambda e: e.evaluated_at, reverse=True)[:10]
    enrollments: list[DomainEnrollment] = data_store.domain_enrollments.filter(user_id=user_id, domain=domain)
    enrollment_status = enrollments[0].status.value if enrollments else None
    score_trend = _score_trend(recent_evals)
    strengths = [item for ev in evals for item in ev.strengths]
    weaknesses = [item for ev in evals for item in ev.weaknesses]
    missed_concepts = [item for ev in evals for item in ev.missed_concepts]
    final_assessment_ready = enrollment_status == DomainStatus.FINAL_ASSESSMENT_DUE.value or (
        summary["total_topics"] > 0 and summary["mastery_rate"] >= 1.0
    )
    insights = {
        "score_trend": score_trend,
        "top_strengths": _top_items(strengths),
        "top_weaknesses": _top_items(weaknesses),
        "common_missed_concepts": _top_items(missed_concepts),
        "final_assessment_ready": final_assessment_ready,
        "stage_summary": _stage_summary(
            DomainStatus.FINAL_ASSESSMENT_DUE.value if final_assessment_ready else enrollment_status,
            summary["mastery_rate"],
            score_trend,
            summary["review_due_topics"],
        ),
    }

    return {
        "user_id": user_id,
        "domain": domain,
        "generated_at": datetime.now(UTC).isoformat(),
        "enrollment_status": enrollment_status,
        "summary": summary,
        "topic_rows": topic_rows,
        "recent_evals": recent_evals,
        "insights": insights,
    }


def generate_report_payload(user_id: str, domain: str) -> dict[str, Any]:
    """Build a JSON-serializable report payload for the API and web UI."""
    report = generate_report(user_id, domain)
    return {
        "user_id": report["user_id"],
        "domain": report["domain"],
        "generated_at": report["generated_at"],
        "enrollment_status": report["enrollment_status"],
        "summary": report["summary"],
        "topic_rows": [
            {
                "title": row.title,
                "status": row.status,
                "mastery_score": row.mastery_score,
                "avg_score": row.avg_score,
                "attempts": row.attempts,
            }
            for row in report["topic_rows"]
        ],
        "recent_evals": [
            {
                "evaluated_at": evaluation.evaluated_at.isoformat(),
                "overall_score": evaluation.overall_score,
                "next_action": evaluation.next_action,
                "feedback": evaluation.llm_feedback,
                "strengths": evaluation.strengths,
                "weaknesses": evaluation.weaknesses,
                "missed_concepts": evaluation.missed_concepts,
            }
            for evaluation in report["recent_evals"]
        ],
        "insights": report["insights"],
    }


def render_html(user_id: str, domain: str) -> str:
    """Render the progress report as an HTML string."""
    report = generate_report(user_id, domain)
    env = Environment(loader=BaseLoader())
    template = env.from_string(_HTML_TEMPLATE)
    return template.render(
        domain=domain,
        user_id=user_id,
        generated_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
        summary=report["summary"],
        topic_rows=list(enumerate(report["topic_rows"], 1)),
        recent_evals=report["recent_evals"],
        insights=report["insights"],
    )


def save_report(user_id: str, domain: str) -> Path:
    """Render and save the HTML report to data/reports/.

    Returns:
        Path to the saved HTML file.
    """
    data_dir = Path(os.environ.get("DATA_DIR", "./data"))
    reports_dir = data_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now(UTC).strftime("%Y-%m-%d")
    filename = f"{domain}_{date_str}.html"
    path = reports_dir / filename
    html = render_html(user_id, domain)
    path.write_text(html, encoding="utf-8")
    logger.info("Report saved: %s", path)
    return path
