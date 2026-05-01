import { describe, expect, it } from "vitest";

import {
  buildBasicQuestionFields,
  buildSubmissionAnswer,
  normalizeBasicQuestions,
} from "./questionView";

describe("question view helpers", () => {
  it("keeps every backend-provided basic question instead of truncating the list", () => {
    expect(normalizeBasicQuestions([" Q1 ", "", "Q2", "Q3", "Q4 "])).toEqual([
      "Q1",
      "Q2",
      "Q3",
      "Q4",
    ]);
  });

  it("builds one field per returned question and falls back to a waiting placeholder", () => {
    expect(buildBasicQuestionFields(["Q1?", "Q2?"])).toEqual([
      { answerId: "basicAnswer1", index: 1, question: "Q1?" },
      { answerId: "basicAnswer2", index: 2, question: "Q2?" },
    ]);
    expect(buildBasicQuestionFields([])).toEqual([
      { answerId: "basicAnswer1", index: 1, question: "等待今日问题。" },
    ]);
  });

  it("formats submission text from the currently rendered question count", () => {
    expect(
      buildSubmissionAnswer(["第一题答案", "", "第三题答案"], "实现过程", "请复盘关键取舍"),
    ).toBe(
      "基础问题 1:\n第一题答案\n\n基础问题 2:\n未作答\n\n基础问题 3:\n第三题答案\n\n实践答案:\n实现过程\n\n实践复盘提示:\n请复盘关键取舍",
    );
  });
});
