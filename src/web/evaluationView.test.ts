import { describe, expect, it } from "vitest";

import { feedbackText, formatScore, nextActionLabel, scoreTone } from "./evaluationView";

describe("evaluation view helpers", () => {
  it("formats 0-100 evaluation scores for display", () => {
    expect(formatScore(82.4)).toBe("82");
    expect(formatScore(Number.NaN)).toBe("--");
  });

  it("maps score ranges to visual tones", () => {
    expect(scoreTone(91)).toBe("strong");
    expect(scoreTone(70)).toBe("steady");
    expect(scoreTone(45)).toBe("review");
  });

  it("localizes known next actions and falls back to raw actions", () => {
    expect(nextActionLabel("continue")).toBe("继续推进");
    expect(nextActionLabel("review")).toBe("进入复习");
    expect(nextActionLabel("custom")).toBe("custom");
    expect(nextActionLabel("")).toBe("等待建议");
  });

  it("keeps the feedback panel meaningful when feedback is empty", () => {
    expect(feedbackText("  Great answer. ")).toBe("Great answer.");
    expect(feedbackText("")).toBe("系统暂未返回详细反馈。");
  });
});
