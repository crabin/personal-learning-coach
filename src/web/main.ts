import "./styles.css";

import { ApiError, LearningCoachApi, type ApiResponse } from "./apiClient";
import {
  feedbackText,
  formatScore,
  nextActionLabel,
  scoreTone,
  type EvaluationSummary,
} from "./evaluationView";
import { emptyReport, renderReport, type ReportPayload } from "./reportView";

type JsonValue = Record<string, unknown> | unknown[] | string | number | boolean | null;
type ViewId = "goals" | "questions" | "reports" | "operations";

interface ResultState {
  title: string;
  request?: ApiResponse<unknown>["request"];
  data?: unknown;
  error?: string;
}

interface TriggerResponse {
  push_id: string | null;
  delivered: boolean;
  message: string;
  push_type?: string;
  topic_id?: string;
  theory?: string;
  basic_questions?: string[];
  practice_question?: string;
  reflection_question?: string;
}

interface SubmitResponse extends EvaluationSummary {
  submission_id: string;
  eval_id: string;
}

interface DomainStatusResponse {
  status: string;
  total_topics: number;
  mastered_topics: number;
  mastery_rate: number;
}

let currentView: ViewId = "goals";

const app = document.querySelector<HTMLDivElement>("#app");

if (!app) {
  throw new Error("App root not found");
}

app.innerHTML = `
  <main class="app-shell">
    <header class="hero">
      <div class="hero-copy">
        <p class="eyebrow">Personal Learning Coach</p>
        <h1>从学习目标到每日反馈的个人教练工作台</h1>
      </div>
      <div class="hero-actions">
        <button id="healthButton" class="command primary" type="button">检查健康状态</button>
        <div class="health-pill" aria-live="polite">
          <span id="healthDot" class="status-dot"></span>
          <span id="healthStatus">尚未检查</span>
        </div>
      </div>
    </header>

    <section class="config-bar" aria-label="全局配置">
      <label>
        API 地址
        <input id="apiBaseUrl" value="/" placeholder="/" />
      </label>
      <label>
        用户 ID
        <input id="userId" value="u1" />
      </label>
      <label>
        学习领域
        <input id="domain" value="ai_agent" />
      </label>
      <label>
        Admin API Key
        <input id="adminApiKey" type="password" placeholder="未启用鉴权可留空" />
      </label>
    </section>

    <nav class="landing-tabs" aria-label="学习流程页面">
      <button class="tab-button" data-view="goals" type="button" aria-selected="true">学习目标</button>
      <button class="tab-button" data-view="questions" type="button" aria-selected="false">问题回答</button>
      <button class="tab-button" data-view="reports" type="button" aria-selected="false">学习报告</button>
      <button class="tab-button" data-view="operations" type="button" aria-selected="false">管理运维</button>
    </nav>

    <section id="goalsView" class="landing-page active" aria-labelledby="goalsTitle">
      <div class="page-intro">
        <p class="eyebrow">Step 01</p>
        <h2 id="goalsTitle">创建学习目标</h2>
        <p>把用户、领域、当前水平、目标水平和学习偏好一起写入报名流程，生成后续每日推送的上下文。</p>
      </div>
      <div class="page-grid">
        <section class="work-surface">
          <div class="surface-heading">
            <h3>学习配置</h3>
            <button id="enrollButton" class="command primary" type="button">创建学习目标</button>
          </div>
          <div class="form-grid">
            <label>
              当前水平
              <select id="level">
                <option value="beginner">beginner</option>
                <option value="intermediate">intermediate</option>
                <option value="advanced">advanced</option>
              </select>
            </label>
            <label>
              目标水平
              <select id="targetLevel">
                <option value="beginner">beginner</option>
                <option value="intermediate">intermediate</option>
                <option value="advanced" selected>advanced</option>
              </select>
            </label>
            <label>
              每日分钟
              <input id="dailyMinutes" type="number" min="10" max="240" value="45" />
            </label>
            <label>
              学习风格
              <select id="learningStyle">
                <option value="practice">practice</option>
                <option value="blended" selected>blended</option>
                <option value="reading">reading</option>
                <option value="project">project</option>
              </select>
            </label>
            <label>
              推送时间
              <input id="deliveryTime" value="20:30" />
            </label>
            <label>
              语言
              <select id="language">
                <option value="zh" selected>zh</option>
                <option value="en">en</option>
              </select>
            </label>
          </div>
          <label class="toggle-row">
            <input id="allowOnlineResources" type="checkbox" checked />
            允许在线资源推荐
          </label>
        </section>

        <aside class="side-panel">
          <div class="metric-grid">
            <article class="metric-card">
              <span>路径</span>
              <strong>目标 → 推送 → 提交 → 反馈</strong>
            </article>
            <article class="metric-card accent">
              <span>当前领域</span>
              <strong id="domainPreview">ai_agent</strong>
            </article>
          </div>
          <button id="statusButton" class="command full" type="button">查看当前状态</button>
        </aside>
      </div>
    </section>

    <section id="questionsView" class="landing-page" aria-labelledby="questionsTitle">
      <div class="page-intro">
        <p class="eyebrow">Step 02</p>
        <h2 id="questionsTitle">查看问题并提交回答</h2>
        <p>获取今天的理论、基础题、实践题和复盘题，完成后把结构化答案提交到评估链路。</p>
      </div>
      <div class="question-layout">
        <section class="work-surface question-surface">
          <div class="surface-heading">
            <h3>今日推送</h3>
            <span id="questionBadge" class="question-badge">尚未获取</span>
          </div>
          <article class="prompt-card theory-card">
            <span>理论讲解</span>
            <p id="theoryContent">点击“获取今日问题”后，这里会展示今天的理论内容。</p>
          </article>
          <div class="basic-grid">
            <article class="prompt-card">
              <span>基础问题 1</span>
              <p id="basicQuestion1Text">等待获取今日问题。</p>
              <textarea id="basicAnswer1" rows="3" placeholder="回答基础问题 1"></textarea>
            </article>
            <article class="prompt-card">
              <span>基础问题 2</span>
              <p id="basicQuestion2Text">等待获取今日问题。</p>
              <textarea id="basicAnswer2" rows="3" placeholder="回答基础问题 2"></textarea>
            </article>
            <article class="prompt-card">
              <span>基础问题 3</span>
              <p id="basicQuestion3Text">等待获取今日问题。</p>
              <textarea id="basicAnswer3" rows="3" placeholder="回答基础问题 3"></textarea>
            </article>
          </div>
          <article class="prompt-card practice-card">
            <span>实践题</span>
            <p id="practiceQuestionContent">这里会展示系统推送的练习题。</p>
            <textarea id="practiceAnswer" rows="7" placeholder="写下实践思路、步骤、代码或结论"></textarea>
          </article>
          <article class="prompt-card reflection-card">
            <span>实践复盘</span>
            <p id="reflectionQuestionContent">这里会展示系统推送的反思题。</p>
          </article>
        </section>

        <aside class="side-panel answer-panel">
          <button id="pushButton" class="command full" type="button">获取今日问题</button>
          <label>
            Push ID
            <input id="pushId" placeholder="获取今日问题后会自动填入" />
          </label>
          <label>
            实践产出摘要
            <input id="practiceResult" placeholder="例如：完成了一个命令行原型" />
          </label>
          <label>
            规范化答案
            <input id="normalizedAnswer" placeholder="可选，最终精简答案" />
          </label>
          <label>
            解析备注
            <input id="parsingNotes" placeholder="可选，记录答案解析情况" />
          </label>
          <button id="submitButton" class="command primary full" type="button">提交答案并评估</button>
          <section class="evaluation-panel" aria-labelledby="evaluationTitle" aria-live="polite">
            <div class="surface-heading compact-heading">
              <div>
                <span class="eyebrow">Evaluation</span>
                <h3 id="evaluationTitle">回答质量评估</h3>
              </div>
              <div id="evaluationScoreCard" class="score-card" data-tone="empty">
                <strong id="evaluationScore">--</strong>
                <span>/100</span>
              </div>
            </div>
            <dl class="evaluation-list">
              <div>
                <dt>下一步</dt>
                <dd id="evaluationAction">提交答案后显示系统建议</dd>
              </div>
              <div>
                <dt>评估 ID</dt>
                <dd id="evaluationId">--</dd>
              </div>
            </dl>
            <p id="evaluationFeedback" class="evaluation-feedback">这里会展示系统对回答质量、理解深度和改进方向的反馈。</p>
          </section>
        </aside>
      </div>
    </section>

    <section id="reportsView" class="landing-page" aria-labelledby="reportsTitle">
      <div class="page-intro">
        <p class="eyebrow">Step 03</p>
        <h2 id="reportsTitle">学习报告展示</h2>
        <p>打开页面时自动读取当前领域的结构化进度数据，由前端渲染趋势、强弱项、常错点和 Topic Details。</p>
      </div>
      <div class="report-toolbar" aria-live="polite">
        <span id="reportSyncStatus" class="question-badge">切换到本页后自动同步</span>
        <button id="refreshReportButton" class="command" type="button">刷新</button>
      </div>
      <div id="reportContent" class="report-content">${emptyReport("切换到学习报告后会自动加载。")}</div>
    </section>

    <section id="operationsView" class="landing-page" aria-labelledby="operationsTitle">
      <div class="page-intro">
        <p class="eyebrow">Step 04</p>
        <h2 id="operationsTitle">管理与运维</h2>
        <p>集中处理领域生命周期、备份恢复、运行事件、告警和结业评估。</p>
      </div>
      <div class="ops-grid">
        <section class="work-surface">
          <div class="surface-heading"><h3>领域生命周期</h3></div>
          <div class="button-grid">
            <button id="pauseButton" class="command" type="button">暂停领域</button>
            <button id="resumeButton" class="command" type="button">恢复领域</button>
            <button id="archiveButton" class="command" type="button">归档领域</button>
          </div>
        </section>
        <section class="work-surface">
          <div class="surface-heading"><h3>运行保障</h3></div>
          <div class="button-grid">
            <button id="backupButton" class="command" type="button">创建备份</button>
            <button id="eventsButton" class="command" type="button">运行事件</button>
            <button id="alertsButton" class="command" type="button">当前告警</button>
          </div>
        </section>
        <section class="work-surface">
          <div class="surface-heading"><h3>结业评估</h3></div>
          <div class="form-grid two">
            <label>
              是否通过
              <select id="finalPassed">
                <option value="true" selected>通过</option>
                <option value="false">未通过</option>
              </select>
            </label>
            <label>
              分数
              <input id="finalScore" type="number" min="0" max="100" value="90" />
            </label>
          </div>
          <label>
            反馈
            <textarea id="finalFeedback" rows="3" placeholder="结业表现反馈"></textarea>
          </label>
          <button id="finalButton" class="command primary full" type="button">提交结业评估</button>
        </section>
        <section class="work-surface danger-surface">
          <div class="surface-heading"><h3>高级危险操作</h3></div>
          <label class="toggle-row">
            <input id="deleteConfirm" type="checkbox" />
            确认删除当前用户和领域的所有相关数据
          </label>
          <button id="deleteButton" class="command danger full" type="button" disabled>删除领域</button>
          <label>
            备份路径
            <input id="restorePath" placeholder="./data/backups/..." />
          </label>
          <label class="toggle-row">
            <input id="restoreConfirm" type="checkbox" />
            确认用该备份恢复数据
          </label>
          <button id="restoreButton" class="command danger full" type="button" disabled>恢复备份</button>
        </section>
      </div>
    </section>

    <section class="console-layout" aria-labelledby="resultTitle">
      <div class="console-card">
        <div class="surface-heading">
          <h2 id="resultTitle">最近请求</h2>
          <button id="clearResultButton" class="command subtle" type="button">清空</button>
        </div>
        <div id="requestLine" class="request-line">等待请求</div>
        <pre id="resultOutput">{}</pre>
      </div>
    </section>
  </main>
`;

const api = new LearningCoachApi({ baseUrl: getInput("apiBaseUrl").value });

bindGlobalState();
bindViews();
bindActions();
syncPreview();

function bindGlobalState(): void {
  onInput("apiBaseUrl", () => api.setBaseUrl(value("apiBaseUrl")));
  onInput("adminApiKey", () => api.setAdminApiKey(value("adminApiKey")));
  onInput("domain", syncPreview);
  onInput("userId", syncDangerButtons);
  onInput("restorePath", syncDangerButtons);
  onChange("deleteConfirm", syncDangerButtons);
  onChange("restoreConfirm", syncDangerButtons);
  syncDangerButtons();
}

function bindViews(): void {
  document.querySelectorAll<HTMLButtonElement>("[data-view]").forEach((button) => {
    button.addEventListener("click", () => showView(button.dataset.view as ViewId));
  });
}

function bindActions(): void {
  onClick("healthButton", checkHealth);
  onClick("enrollButton", enrollDomain);
  onClick("statusButton", getDomainStatus);
  onClick("pushButton", triggerPush);
  onClick("submitButton", submitAnswer);
  onClick("refreshReportButton", refreshReportPage);
  onClick("pauseButton", () => lifecycle("pause"));
  onClick("resumeButton", () => lifecycle("resume"));
  onClick("archiveButton", () => lifecycle("archive"));
  onClick("deleteButton", deleteDomain);
  onClick("backupButton", createBackup);
  onClick("eventsButton", listRuntimeEvents);
  onClick("alertsButton", listAlerts);
  onClick("restoreButton", restoreBackup);
  onClick("finalButton", submitFinalAssessment);
  onClick("clearResultButton", () => renderResult({ title: "已清空", data: {} }));
}

function showView(view: ViewId): void {
  currentView = view;
  document.querySelectorAll<HTMLElement>(".landing-page").forEach((page) => {
    page.classList.toggle("active", page.id === `${view}View`);
  });
  document.querySelectorAll<HTMLButtonElement>(".tab-button").forEach((button) => {
    button.setAttribute("aria-selected", String(button.dataset.view === view));
  });
  if (view === "reports") {
    void refreshReportPage();
  }
}

async function checkHealth(): Promise<void> {
  await runJson("健康检查", () => api.request<JsonValue>("/health"));
}

async function enrollDomain(): Promise<void> {
  await runJson("创建学习目标", () =>
    api.request<JsonValue>(`/domains/${domain()}/enroll`, {
      method: "POST",
      body: {
        user_id: userId(),
        level: value("level"),
        target_level: value("targetLevel"),
        daily_minutes: numberValue("dailyMinutes"),
        learning_style: value("learningStyle"),
        delivery_time: value("deliveryTime"),
        language: value("language"),
        allow_online_resources: getInput("allowOnlineResources").checked,
      },
    }),
  );
}

async function getDomainStatus(): Promise<void> {
  await runJson("领域状态", () =>
    api.request<JsonValue>(`/domains/${domain()}/status`, {
      query: { user_id: userId() },
    }),
  );
}

async function triggerPush(): Promise<void> {
  await runJson("获取今日问题", async () => {
    const response = await api.request<TriggerResponse>("/schedules/trigger", {
      method: "POST",
      body: { user_id: userId(), domain: domain() },
    });
    if (response.data.push_id) {
      getInput("pushId").value = response.data.push_id;
    }
    renderQuestionContent(response.data);
    return response;
  });
}

async function submitAnswer(): Promise<void> {
  await runJson("提交答案", async () => {
    const response = await api.request<SubmitResponse>("/submissions", {
      method: "POST",
      body: {
        user_id: userId(),
        push_id: value("pushId"),
        raw_answer: buildSubmissionAnswer(),
        practice_result: value("practiceResult"),
        normalized_answer: value("normalizedAnswer") || value("practiceAnswer"),
        parsing_notes: value("parsingNotes"),
      },
    });
    renderEvaluation(response.data);
    if (currentView === "reports") {
      void refreshReportPage();
    }
    return response;
  });
}

async function loadReport(): Promise<void> {
  await runJson("学习报告", async () => {
    text("reportSyncStatus", "正在同步报告...");
    const response = await api.request<ReportPayload>(`/reports/${domain()}`, {
      query: { user_id: userId() },
    });
    renderReportContent(response.data);
    text("reportSyncStatus", "报告已同步");
    return response;
  });
}

async function refreshReportPage(): Promise<void> {
  getReportContent().innerHTML = emptyReport("正在同步学习报告...");
  await loadReport();
  await syncReportDomainStatus();
}

async function syncReportDomainStatus(): Promise<void> {
  try {
    const response = await api.request<DomainStatusResponse>(`/domains/${domain()}/status`, {
      query: { user_id: userId() },
    });
    text(
      "reportSyncStatus",
      `报告已同步 · 状态 ${response.data.status} · 掌握率 ${Math.round(response.data.mastery_rate * 100)}%`,
    );
  } catch (error) {
    const message = error instanceof ApiError ? error.message : String(error);
    text("reportSyncStatus", `状态同步失败：${message}`);
  }
}

async function lifecycle(action: "pause" | "resume" | "archive"): Promise<void> {
  await runJson(`领域${action}`, () =>
    api.request<JsonValue>(`/domains/${domain()}/${action}`, {
      method: "POST",
      body: { user_id: userId() },
    }),
  );
}

async function deleteDomain(): Promise<void> {
  await runJson("删除领域", () =>
    api.request<JsonValue>(`/domains/${domain()}`, {
      method: "DELETE",
      body: { user_id: userId(), confirm: true },
    }),
  );
}

async function submitFinalAssessment(): Promise<void> {
  await runJson("结业评估", () =>
    api.request<JsonValue>(`/domains/${domain()}/final-assessment`, {
      method: "POST",
      body: {
        user_id: userId(),
        passed: value("finalPassed") === "true",
        score: numberValue("finalScore"),
        feedback: value("finalFeedback"),
      },
    }),
  );
}

async function createBackup(): Promise<void> {
  await runJson("创建备份", () => api.request<JsonValue>("/admin/backup", { method: "POST", admin: true }));
}

async function listRuntimeEvents(): Promise<void> {
  await runJson("运行事件", () =>
    api.request<JsonValue>("/admin/runtime-events", { query: { limit: 20 }, admin: true }),
  );
}

async function listAlerts(): Promise<void> {
  await runJson("当前告警", () => api.request<JsonValue>("/admin/alerts", { admin: true }));
}

async function restoreBackup(): Promise<void> {
  await runJson("恢复备份", () =>
    api.request<JsonValue>("/admin/restore", {
      method: "POST",
      admin: true,
      body: { backup_path: value("restorePath") },
    }),
  );
}

async function runJson<T>(title: string, action: () => Promise<ApiResponse<T>>): Promise<void> {
  await runAction(title, action);
}

async function runAction<T>(title: string, action: () => Promise<ApiResponse<T>>): Promise<void> {
  renderResult({ title, data: "请求中..." });
  try {
    const response = await action();
    renderResult({
      title,
      request: response.request,
      data: response.data,
    });
    if (title === "健康检查") {
      updateHealth(response.data);
    }
  } catch (error) {
    const message = error instanceof ApiError ? error.message : String(error);
    renderResult({ title, error: message });
    if (title === "健康检查") {
      updateHealth({ status: "error", issues: [message] });
    }
  }
}

function renderResult(state: ResultState): void {
  text("resultTitle", state.title);
  const requestLine = document.querySelector<HTMLDivElement>("#requestLine")!;
  requestLine.textContent = state.request
    ? `${state.request.method} ${state.request.url}`
    : state.error
      ? "请求失败"
      : "等待请求";

  const output = document.querySelector<HTMLPreElement>("#resultOutput")!;
  output.classList.toggle("error-text", Boolean(state.error));
  output.textContent = state.error ? state.error : JSON.stringify(state.data ?? {}, null, 2);
}

function renderQuestionContent(data: TriggerResponse): void {
  text("questionBadge", data.delivered ? `${data.push_type ?? "topic"} 已获取` : "暂无可推送内容");
  text("theoryContent", data.delivered ? data.theory || "本次没有返回理论讲解。" : data.message);
  const basicQuestions = data.delivered ? normalizeBasicQuestions(data.basic_questions) : [];
  text("basicQuestion1Text", basicQuestions[0] ?? "等待获取今日问题。");
  text("basicQuestion2Text", basicQuestions[1] ?? "等待获取今日问题。");
  text("basicQuestion3Text", basicQuestions[2] ?? "等待获取今日问题。");
  text("practiceQuestionContent", data.delivered ? data.practice_question || "本次没有返回实践题。" : "等待获取今日问题。");
  text("reflectionQuestionContent", data.delivered ? data.reflection_question || "本次没有返回反思题。" : "等待获取今日问题。");
  if (data.delivered) {
    clearQuestionAnswers();
  }
}

function renderEvaluation(data: SubmitResponse): void {
  text("evaluationScore", formatScore(data.overall_score));
  text("evaluationAction", nextActionLabel(data.next_action));
  text("evaluationId", data.eval_id || "--");
  text("evaluationFeedback", feedbackText(data.feedback));
  const scoreCard = document.querySelector<HTMLDivElement>("#evaluationScoreCard")!;
  scoreCard.dataset.tone = scoreTone(data.overall_score);
}

function renderReportContent(data: ReportPayload): void {
  getReportContent().innerHTML = renderReport(data);
}

function updateHealth(data: unknown): void {
  const status = isRecord(data) && typeof data.status === "string" ? data.status : "unknown";
  const dot = document.querySelector<HTMLSpanElement>("#healthDot")!;
  dot.dataset.status = status;
  text("healthStatus", status);
}

function syncDangerButtons(): void {
  getButton("deleteButton").disabled = !getInput("deleteConfirm").checked;
  getButton("deleteButton").textContent = `删除 ${userId()} / ${domain()}`;
  getButton("restoreButton").disabled =
    !getInput("restoreConfirm").checked || value("restorePath").trim().length === 0;
}

function syncPreview(): void {
  text("domainPreview", domain());
  if (currentView === "reports") {
    void refreshReportPage();
  }
}

function buildSubmissionAnswer(): string {
  const basics = [
    ["基础问题 1", value("basicAnswer1")],
    ["基础问题 2", value("basicAnswer2")],
    ["基础问题 3", value("basicAnswer3")],
  ]
    .map(([label, answer]) => `${label}:\n${answer.trim() || "未作答"}`)
    .join("\n\n");
  const practice = value("practiceAnswer").trim() || "未填写实践答案";
  return `${basics}\n\n实践答案:\n${practice}\n\n实践复盘提示:\n${textContent("reflectionQuestionContent")}`;
}

function normalizeBasicQuestions(valueToCheck: string[] | undefined): string[] {
  const questions = Array.isArray(valueToCheck) ? valueToCheck.map((item) => String(item).trim()) : [];
  return questions.filter(Boolean).slice(0, 3);
}

function clearQuestionAnswers(): void {
  ["basicAnswer1", "basicAnswer2", "basicAnswer3", "practiceAnswer"].forEach((id) => {
    getInput(id).value = "";
  });
}

function onClick(id: string, handler: () => void | Promise<void>): void {
  getButton(id).addEventListener("click", () => void handler());
}

function onInput(id: string, handler: () => void): void {
  getInput(id).addEventListener("input", handler);
}

function onChange(id: string, handler: () => void): void {
  getInput(id).addEventListener("change", handler);
}

function userId(): string {
  return value("userId").trim();
}

function domain(): string {
  return value("domain").trim();
}

function value(id: string): string {
  return getInput(id).value;
}

function numberValue(id: string): number {
  return Number(value(id));
}

function getInput(id: string): HTMLInputElement {
  const element = document.getElementById(id);
  if (
    element instanceof HTMLInputElement ||
    element instanceof HTMLTextAreaElement ||
    element instanceof HTMLSelectElement
  ) {
    return element as HTMLInputElement;
  }
  throw new Error(`Input not found: ${id}`);
}

function getButton(id: string): HTMLButtonElement {
  const element = document.getElementById(id);
  if (element instanceof HTMLButtonElement) {
    return element;
  }
  throw new Error(`Button not found: ${id}`);
}

function getReportContent(): HTMLDivElement {
  const element = document.getElementById("reportContent");
  if (element instanceof HTMLDivElement) {
    return element;
  }
  throw new Error("Report content root not found");
}

function text(id: string, valueToSet: string): void {
  const element = document.getElementById(id);
  if (!(element instanceof HTMLElement)) {
    throw new Error(`Element not found: ${id}`);
  }
  element.textContent = valueToSet;
}

function textContent(id: string): string {
  const element = document.getElementById(id);
  if (!(element instanceof HTMLElement)) {
    throw new Error(`Element not found: ${id}`);
  }
  return element.textContent ?? "";
}

function isRecord(valueToCheck: unknown): valueToCheck is Record<string, unknown> {
  return typeof valueToCheck === "object" && valueToCheck !== null && !Array.isArray(valueToCheck);
}
