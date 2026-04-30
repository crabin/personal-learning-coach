export interface ReportSummary {
  total_topics: number;
  mastered_topics: number;
  review_due_topics: number;
  mastery_rate: number;
  avg_score: number;
}

export interface ReportTopicRow {
  title: string;
  status: string;
  mastery_score: number;
  avg_score: number | null;
  attempts: number;
}

export interface ReportEvaluation {
  evaluated_at: string;
  overall_score: number;
  next_action: string;
  feedback: string;
}

export interface ReportPayload {
  user_id: string;
  domain: string;
  generated_at: string;
  enrollment_status: string | null;
  summary: ReportSummary;
  topic_rows: ReportTopicRow[];
  recent_evals: ReportEvaluation[];
  insights: {
    score_trend: string;
    top_strengths: string[];
    top_weaknesses: string[];
    common_missed_concepts: string[];
    final_assessment_ready: boolean;
    stage_summary: string;
  };
}

export function renderReport(data: ReportPayload): string {
  return `
    <section class="report-board" aria-live="polite">
      <div class="report-status-row">
        <div>
          <span class="eyebrow">Report</span>
          <h3>${escapeHtml(data.domain)} / ${escapeHtml(data.user_id)}</h3>
        </div>
        <span class="report-status">${statusLabel(data.enrollment_status)}</span>
      </div>
      <div class="report-metrics">
        ${metric("总主题", String(data.summary.total_topics))}
        ${metric("已掌握", String(data.summary.mastered_topics))}
        ${metric("掌握率", `${Math.round(data.summary.mastery_rate * 100)}%`)}
        ${metric("平均分", formatNumber(data.summary.avg_score))}
      </div>
      <section class="report-section">
        <div class="surface-heading compact-heading">
          <h3>Topic Details</h3>
          <span class="report-generated">更新于 ${formatDate(data.generated_at)}</span>
        </div>
        ${renderTopicTable(data.topic_rows)}
      </section>
      <section class="report-section insight-band">
        <h3>学习进度</h3>
        <p>${escapeHtml(data.insights.stage_summary)}</p>
        <div class="insight-grid">
          ${insight("趋势", data.insights.score_trend)}
          ${insight("强项", listText(data.insights.top_strengths))}
          ${insight("弱项", listText(data.insights.top_weaknesses))}
          ${insight("常错概念", listText(data.insights.common_missed_concepts))}
        </div>
      </section>
      <section class="report-section">
        <h3>Recent Evaluations</h3>
        ${renderEvaluations(data.recent_evals)}
      </section>
    </section>
  `;
}

export function emptyReport(message = "正在加载学习报告..."): string {
  return `<div class="report-empty">${escapeHtml(message)}</div>`;
}

function renderTopicTable(rows: ReportTopicRow[]): string {
  if (rows.length === 0) {
    return emptyReport("当前领域还没有可展示的学习进度。");
  }
  return `
    <div class="report-table-wrap">
      <table class="report-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Topic</th>
            <th>Status</th>
            <th>Mastery</th>
            <th>Avg Score</th>
            <th>Attempts</th>
          </tr>
        </thead>
        <tbody>
          ${rows
            .map(
              (row, index) => `
                <tr>
                  <td>${index + 1}</td>
                  <td>${escapeHtml(row.title)}</td>
                  <td><span class="topic-status" data-status="${escapeHtml(row.status)}">${escapeHtml(row.status)}</span></td>
                  <td>${formatNumber(row.mastery_score)}</td>
                  <td>${row.avg_score === null ? "--" : formatNumber(row.avg_score)}</td>
                  <td>${row.attempts}</td>
                </tr>
              `,
            )
            .join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderEvaluations(evaluations: ReportEvaluation[]): string {
  if (evaluations.length === 0) {
    return emptyReport("还没有提交后的评价记录。");
  }
  return `
    <div class="evaluation-timeline">
      ${evaluations
        .map(
          (evaluation) => `
            <article class="evaluation-item">
              <strong>${formatNumber(evaluation.overall_score)} / 100</strong>
              <span>${escapeHtml(evaluation.next_action || "continue")} · ${formatDate(evaluation.evaluated_at)}</span>
              <p>${escapeHtml(evaluation.feedback || "系统暂未返回详细反馈。")}</p>
            </article>
          `,
        )
        .join("")}
    </div>
  `;
}

function metric(label: string, value: string): string {
  return `
    <article class="report-metric">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
    </article>
  `;
}

function insight(label: string, value: string): string {
  return `
    <article>
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
    </article>
  `;
}

function listText(items: string[]): string {
  return items.length > 0 ? items.join("、") : "--";
}

function statusLabel(status: string | null): string {
  return status ? `领域状态：${status}` : "领域状态：未创建";
}

function formatNumber(value: number): string {
  return Number.isFinite(value) ? String(Math.round(value)) : "--";
}

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("zh-CN");
}

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
