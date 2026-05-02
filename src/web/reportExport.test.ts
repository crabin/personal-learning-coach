import { describe, expect, it } from "vitest";

import { buildReportExportFilename, serializeReportExport } from "./reportExport";
import type { ReportPayload } from "./reportView";

function report(overrides: Partial<ReportPayload> = {}): ReportPayload {
  return {
    user_id: "user-1",
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

describe("report export", () => {
  it("builds a stable filename from the report metadata", () => {
    expect(buildReportExportFilename(report())).toBe(
      "learning-report-ai_agent-user-1-2026-04-30T10-00-00-000Z.json",
    );
  });

  it("serializes the full report payload as readable json", () => {
    const json = serializeReportExport(report());

    expect(json).toContain('"domain": "ai_agent"');
    expect(json).toContain('"mastery_score": 86');
    expect(json.endsWith("\n")).toBe(true);
  });
});
