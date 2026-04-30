import { describe, expect, it } from "vitest";

import { emptyReport, renderReport, type ReportPayload } from "./reportView";

function report(overrides: Partial<ReportPayload> = {}): ReportPayload {
  return {
    user_id: "u1",
    domain: "ai_agent",
    generated_at: "2026-04-30T10:00:00Z",
    enrollment_status: "active",
    summary: {
      total_topics: 2,
      mastered_topics: 1,
      review_due_topics: 0,
      mastery_rate: 0.5,
      avg_score: 82,
    },
    topic_rows: [
      {
        title: "Prompt Debugging",
        status: "mastered",
        mastery_score: 86,
        avg_score: 82,
        attempts: 2,
      },
    ],
    recent_evals: [
      {
        evaluated_at: "2026-04-30T09:30:00Z",
        overall_score: 82,
        next_action: "continue",
        feedback: "Good progress.",
      },
    ],
    insights: {
      score_trend: "improving",
      top_strengths: ["clear reasoning"],
      top_weaknesses: ["depth"],
      common_missed_concepts: ["rubrics"],
      final_assessment_ready: false,
      stage_summary: "The learner is progressing.",
    },
    ...overrides,
  };
}

describe("report view", () => {
  it("renders dynamic topic details from the report payload", () => {
    const html = renderReport(report());

    expect(html).toContain("Topic Details");
    expect(html).toContain("Prompt Debugging");
    expect(html).toContain("mastered");
    expect(html).toContain("86");
    expect(html).toContain("领域状态：active");
  });

  it("escapes backend-provided report text before inserting HTML", () => {
    const html = renderReport(
      report({
        domain: "<script>alert(1)</script>",
        topic_rows: [
          {
            title: "<img src=x onerror=alert(1)>",
            status: "ready",
            mastery_score: 0,
            avg_score: null,
            attempts: 0,
          },
        ],
      }),
    );

    expect(html).not.toContain("<script>");
    expect(html).not.toContain("<img");
    expect(html).toContain("&lt;script&gt;");
  });

  it("renders an empty state when there is no report data yet", () => {
    expect(emptyReport("加载中")).toContain("加载中");
  });
});
