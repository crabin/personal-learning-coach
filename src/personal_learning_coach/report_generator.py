"""Generate HTML and JSON learning progress reports."""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, BaseLoader

from personal_learning_coach import data_store
from personal_learning_coach.review_engine import generate_weekly_summary

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
</body>
</html>
"""


def _resolve_topic_titles(user_id: str, domain: str) -> dict[str, str]:
    plans = data_store.learning_plans.filter(user_id=user_id, domain=domain)
    if not plans:
        return {}
    return {t.topic_id: t.title for t in plans[0].topics}


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


def generate_report(user_id: str, domain: str) -> dict[str, Any]:
    """Build a full progress report dict (used for both HTML and JSON).

    Returns:
        Dict containing summary, topic details, and recent evaluations.
    """
    summary = generate_weekly_summary(user_id, domain)
    titles = _resolve_topic_titles(user_id, domain)

    topic_rows = []
    for ts in summary["topic_summaries"]:  # type: ignore[union-attr]
        topic_rows.append(
            _TopicRow(
                title=titles.get(ts["topic_id"], ts["topic_id"]),
                status=ts["status"],
                mastery_score=ts["mastery_score"],
                avg_score=ts["avg_eval_score"],
                attempts=ts["attempts"],
            )
        )

    evals = data_store.evaluation_records.filter(user_id=user_id, domain=domain)
    recent_evals = sorted(evals, key=lambda e: e.evaluated_at, reverse=True)[:10]

    return {
        "user_id": user_id,
        "domain": domain,
        "generated_at": datetime.now(UTC).isoformat(),
        "summary": summary,
        "topic_rows": topic_rows,
        "recent_evals": recent_evals,
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
