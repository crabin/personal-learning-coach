export interface EvaluationSummary {
  overall_score: number;
  next_action: string;
  feedback: string;
}

export type ScoreTone = "strong" | "steady" | "review";

export function formatScore(score: number): string {
  return Number.isFinite(score) ? String(Math.round(score)) : "--";
}

export function scoreTone(score: number): ScoreTone {
  if (score >= 80) {
    return "strong";
  }
  if (score >= 60) {
    return "steady";
  }
  return "review";
}

export function nextActionLabel(nextAction: string): string {
  const labels: Record<string, string> = {
    continue: "继续推进",
    consolidate: "巩固后推进",
    review: "进入复习",
    final_test: "准备结业评估",
  };
  const normalized = nextAction.trim();
  if (labels[normalized]) {
    return labels[normalized];
  }
  return normalized || "等待建议";
}

export function feedbackText(feedback: string): string {
  return feedback.trim() || "系统暂未返回详细反馈。";
}
