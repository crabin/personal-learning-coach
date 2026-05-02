export interface BasicQuestionField {
  answerId: string;
  index: number;
  question: string;
}

const EMPTY_QUESTION_TEXT = "等待今日问题。";

export function normalizeBasicQuestions(valueToCheck: string[] | undefined): string[] {
  const questions = Array.isArray(valueToCheck) ? valueToCheck.map((item) => String(item).trim()) : [];
  return questions.filter(Boolean);
}

export function buildBasicQuestionFields(questions: string[]): BasicQuestionField[] {
  const normalized = normalizeBasicQuestions(questions);
  const source = normalized.length > 0 ? normalized : [EMPTY_QUESTION_TEXT];
  return source.map((question, index) => ({
    answerId: `basicAnswer${index + 1}`,
    index: index + 1,
    question,
  }));
}

export function buildSubmissionAnswer(
  basicAnswers: string[],
  practiceAnswer: string,
  reflectionPrompt: string,
): string {
  const basics = basicAnswers
    .map((answer, index) => `基础问题 ${index + 1}:\n${answer.trim() || "未作答"}`)
    .join("\n\n");
  const practice = practiceAnswer.trim() || "未填写实践答案";
  return `${basics}\n\n实践答案:\n${practice}\n\n实践复盘提示:\n${reflectionPrompt}`;
}
