import "./styles.css";

import { ApiError, LearningCoachApi, type ApiResponse } from "./apiClient";
import { buildDraftDomainOption } from "./domainForm";
import {
  feedbackText,
  formatScore,
  nextActionLabel,
  scoreTone,
  type EvaluationSummary,
} from "./evaluationView";
import {
  buildBasicQuestionFields,
  buildSubmissionAnswer as formatSubmissionAnswer,
  normalizeBasicQuestions,
} from "./questionView";
import { emptyReport, renderReport, type ReportPayload, type ReportTopicRow } from "./reportView";

type JsonValue = Record<string, unknown> | unknown[] | string | number | boolean | null;
type ViewId = "goals" | "questions" | "reports" | "operations";
const DEV_CONSOLE_ENABLED = import.meta.env.DEV;

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
  visual_url?: string;
}

interface SubmitResponse extends EvaluationSummary {
  submission_id: string;
  eval_id: string;
}

interface DomainStatusResponse {
  status: string;
  total_topics: number;
  mastered_topics: number;
  mastery_rate?: number;
}

interface DomainSummaryTopic {
  title: string;
  mastery_percent: number;
}

interface DomainSummaryResponse {
  domain: string;
  user_id: string;
  status: string;
  current_level: string;
  target_level: string;
  mastery_percent: number;
  avg_score: number;
  active_topic_title: string;
  active_topic_id: string;
  topic_progress: DomainSummaryTopic[];
}

interface DomainOptionResponse {
  domain: string;
  label: string;
}

const DEFAULT_LEARNING_VISUAL = "/data/images/backgroud1.png";

let currentView: ViewId = "goals";
let loadedQuestionContext = "";
let pushRequestInFlight = false;
let consoleVisible = false;
let currentBasicAnswerIds: string[] = [];
let goalSummaryRequestId = 0;
let questionSidebarRequestId = 0;
let reportRequestId = 0;

const app = document.querySelector<HTMLDivElement>("#app");

if (!app) {
  throw new Error("App root not found");
}

app.innerHTML = `
  <main class="app-shell">
    <header class="topbar">
      <div class="brand">学习教练</div>
      <nav class="landing-tabs" aria-label="学习流程页面">
        <button class="tab-button" data-view="goals" type="button" aria-selected="true">
          <span class="material-symbols-outlined">track_changes</span>
          目标
        </button>
        <button class="tab-button" data-view="questions" type="button" aria-selected="false">
          <span class="material-symbols-outlined">forum</span>
          问答
        </button>
        <button class="tab-button" data-view="reports" type="button" aria-selected="false">
          <span class="material-symbols-outlined">query_stats</span>
          进度
        </button>
        <button class="tab-button" data-view="operations" type="button" aria-selected="false">
          <span class="material-symbols-outlined">settings_system_daydream</span>
          管理
        </button>
      </nav>
      <section class="config-bar" aria-label="全局配置">
        <label>
          API 地址
          <input id="apiBaseUrl" value="/" placeholder="/" />
        </label>
        <label>
          用户
          <input id="userId" value="u1" />
        </label>
        <label>
          领域
          <select id="domain">
            <option value="ai_agent" selected>AI Agent</option>
          </select>
        </label>
        <label class="admin-key">
          管理密钥
          <input id="adminApiKey" type="password" placeholder="可选" />
        </label>
        <button id="healthButton" class="icon-button" type="button" aria-label="检查健康状态" title="检查健康状态">
          <span class="material-symbols-outlined">monitor_heart</span>
        </button>
        ${
          DEV_CONSOLE_ENABLED
            ? `
        <button
          id="consoleToggleButton"
          class="icon-button"
          type="button"
          aria-label="打开开发控制台"
          title="打开开发控制台"
          aria-expanded="false"
        >
          <span class="material-symbols-outlined">terminal</span>
        </button>
        `
            : ""
        }
        <span class="icon-button ghost" aria-hidden="true">
          <span class="material-symbols-outlined">account_circle</span>
        </span>
      </section>
    </header>

    <section id="goalsView" class="landing-page active" aria-labelledby="goalsTitle">
      <div class="page-header">
        <div>
          <h1 id="goalsTitle">学习目标</h1>
          <p>配置系统化学习路径与进度追踪参数。</p>
        </div>
        <div class="health-pill" aria-live="polite">
          <span id="healthDot" class="status-dot"></span>
          <span>系统状态：<strong id="healthStatus">未检查</strong></span>
        </div>
      </div>
      <div class="page-grid">
        <section class="work-surface">
          <div class="surface-heading">
            <div>
              <h3><span class="material-symbols-outlined">edit_note</span> 报名参数</h3>
              <p class="surface-meta">当前学习领域：<strong id="currentDomainLabel">AI Agent</strong></p>
            </div>
          </div>
          <div class="form-grid">
            <label>
              新学习领域
              <input id="customDomainLabel" placeholder="例如：Python 基础 / 系统设计" />
            </label>
            <label>
              当前水平
              <select id="level">
                <option value="beginner" selected>初级</option>
                <option value="intermediate">中级</option>
                <option value="advanced">高级</option>
              </select>
            </label>
            <label>
              目标水平
              <select id="targetLevel">
                <option value="beginner">初级</option>
                <option value="intermediate">中级</option>
                <option value="advanced" selected>高级</option>
              </select>
            </label>
            <label>
              每日分钟
              <input id="dailyMinutes" type="number" min="10" max="240" value="45" />
            </label>
            <label>
              推送时间
              <input id="deliveryTime" value="09:00" />
            </label>
            <label>
              语言
              <select id="language">
                <option value="zh" selected>中文（ZH）</option>
                <option value="en">英文（EN）</option>
              </select>
            </label>
          </div>
          <div class="style-picker" role="group" aria-label="学习风格">
            <span>学习风格</span>
            <label><input id="learningStyle" name="learningStyle" type="radio" value="practice" checked /> 练习</label>
            <label><input name="learningStyle" type="radio" value="blended" /> 混合</label>
            <label><input name="learningStyle" type="radio" value="reading" /> 阅读</label>
            <label><input name="learningStyle" type="radio" value="project" /> 项目</label>
          </div>
          <label class="resource-toggle">
            <span class="material-symbols-outlined">language</span>
            <span>
              <strong>在线资源发现</strong>
              <small>允许 AI 搜索外部文档与论文。</small>
            </span>
            <input id="allowOnlineResources" type="checkbox" checked />
          </label>
          <div class="action-row">
            <button id="enrollButton" class="command primary" type="button">创建学习目标</button>
            <button id="statusButton" class="command" type="button">查看状态</button>
          </div>
        </section>

        <aside class="side-panel">
          <article class="domain-card">
            <span>领域状态</span>
            <strong id="domainMasteryPercent">--%</strong>
            <small>掌握：<span id="domainPreview">ai_agent</span></small>
            <div id="goalProgressList" class="progress-list"></div>
          </article>
          <article class="active-domain">
            <span>活跃领域</span>
            <div>
              <span class="material-symbols-outlined">model_training</span>
              <strong id="activeTopicTitle">等待同步</strong>
              <small id="activeTopicId">ID: --</small>
            </div>
          </article>
        </aside>
      </div>
    </section>

    <section id="questionsView" class="landing-page" aria-labelledby="questionsTitle">
      <div class="page-header">
        <div>
          <h1 id="questionsTitle">每日学习工作台</h1>
          <p>围绕理论、验证与反思推进结构化学习。</p>
        </div>
        <div class="toolbar">
          <button id="pushButton" class="command" type="button">
            <span class="material-symbols-outlined">refresh</span>
            获取今日问题
          </button>
          <button id="submitButton" class="command primary" type="button">
            <span class="material-symbols-outlined">send</span>
            提交并评估
          </button>
        </div>
      </div>
      <div class="question-layout">
        <section class="work-surface question-surface">
          <article class="learning-visual">
            <img
              id="learningVisualImage"
              class="learning-visual-image"
              alt="课程配图"
              decoding="async"
              fetchpriority="high"
              hidden
            />
            <div id="learningVisualPlaceholder" class="learning-visual-placeholder" aria-hidden="true">
              <span class="material-symbols-outlined">image</span>
              <span id="learningVisualPlaceholderLabel">课程配图加载中</span>
            </div>
          </article>
          <div class="surface-heading">
            <span id="questionBadge" class="question-badge">等待中</span>
          </div>
          <article class="theory-card">
            <span>课程理论</span>
            <h2>今日概念</h2>
            <p id="theoryContent">点击“获取今日问题”加载当前课程理论。</p>
          </article>
          <article class="input-card">
            <div class="form-grid two">
              <label>
                推送 ID
                <input id="pushId" placeholder="自动生成" />
              </label>
              <label>
                实践产出
                <input id="practiceResult" placeholder="原型、笔记或产物摘要" />
              </label>
            </div>
            <div id="basicQuestionsList" class="basic-question-list" aria-live="polite"></div>
            <div class="practice-card">
              <span><span class="material-symbols-outlined">code_blocks</span> 实践：实现摘要</span>
              <p id="practiceQuestionContent">实践任务会显示在这里。</p>
              <textarea id="practiceAnswer" rows="5" placeholder="在这里写下实现逻辑或伪代码..."></textarea>
            </div>
            <div class="reflection-card">
              <span><span class="material-symbols-outlined">psychology</span> 反思</span>
              <p id="reflectionQuestionContent">复盘提示会显示在这里。</p>
              <textarea rows="3" placeholder="写下对今日学习的关键反思..."></textarea>
            </div>
            <div class="form-grid two">
              <label>
                规范化答案
                <input id="normalizedAnswer" placeholder="可选，最终精简答案" />
              </label>
              <label>
                解析备注
                <input id="parsingNotes" placeholder="可选，答案解析备注" />
              </label>
            </div>
          </article>
        </section>

        <aside class="side-panel answer-panel">
          <section class="evaluation-panel" aria-labelledby="evaluationTitle" aria-live="polite">
            <div class="surface-heading compact-heading">
              <div>
                <h3 id="evaluationTitle">本次状态</h3>
                <p>等待评估</p>
              </div>
              <span class="status-chip">进行中</span>
            </div>
            <div id="evaluationScoreCard" class="score-ring" data-tone="empty">
                <strong id="evaluationScore">--</strong>
                <span>/ 100</span>
            </div>
            <dl class="evaluation-list">
              <div>
                <dt>建议的下一步</dt>
                <dd id="evaluationAction">提交答案后显示系统建议。</dd>
              </div>
              <div>
                <dt>评估 ID</dt>
                <dd id="evaluationId">--</dd>
              </div>
            </dl>
            <p id="evaluationFeedback" class="evaluation-feedback">评估后会显示反馈摘要。</p>
          </section>
          <article class="debug-card">
            <span>调试节点</span>
            <p id="questionDebugMetric">&gt; 最近掌握估计：--</p>
            <p id="questionDebugAction">&gt; 下一步：等待评估</p>
          </article>
          <article class="mastery-mini">
            <h3>领域掌握度</h3>
            <div id="questionMasteryList"></div>
          </article>
        </aside>
      </div>
    </section>

    <section id="reportsView" class="landing-page" aria-labelledby="reportsTitle">
      <div class="page-header">
        <div>
          <h1 id="reportsTitle">学习进度报告</h1>
          <p id="reportSyncStatus" aria-live="polite">等待同步数据</p>
        </div>
        <div class="toolbar">
          <button id="refreshReportButton" class="command" type="button">
            <span class="material-symbols-outlined">refresh</span>
            刷新数据
          </button>
          <button class="command primary" type="button">
            <span class="material-symbols-outlined">file_download</span>
            导出 JSON
          </button>
        </div>
      </div>
      <div id="reportContent" class="report-content">${emptyReport("打开本页后会加载报告。")}</div>
    </section>

    <section id="operationsView" class="landing-page" aria-labelledby="operationsTitle">
      <div class="page-header">
        <div>
          <h1 id="operationsTitle">管理与运维</h1>
          <p>系统级控制与领域生命周期管理。</p>
        </div>
        <button id="backupButton" class="command primary" type="button">
          <span class="material-symbols-outlined">cloud_upload</span>
          运行系统备份
        </button>
      </div>
      <div class="ops-grid">
        <section class="work-surface">
          <div class="surface-heading">
            <div>
              <h3>领域生命周期</h3>
              <p>管理学习领域的活跃状态。</p>
            </div>
            <span class="status-chip success">活跃</span>
          </div>
          <div class="button-grid">
            <button id="pauseButton" class="command tile-command" type="button"><span class="material-symbols-outlined">pause_circle</span>暂停</button>
            <button id="resumeButton" class="command tile-command" type="button"><span class="material-symbols-outlined">play_circle</span>恢复</button>
            <button id="archiveButton" class="command tile-command" type="button"><span class="material-symbols-outlined">archive</span>归档</button>
          </div>
        </section>
        <section class="work-surface">
          <div class="surface-heading"><h3><span class="material-symbols-outlined warning">warning</span> 当前告警</h3></div>
          <div class="alert-stack">
            <div class="alert-card danger"><strong>高优先级</strong><span>推理延迟超过阈值。</span></div>
            <div class="alert-card"><strong>提醒</strong><span>系统备份计划在 2 小时后执行。</span></div>
          </div>
          <div class="button-grid">
            <button id="eventsButton" class="command" type="button">运行事件</button>
            <button id="alertsButton" class="command" type="button">当前告警</button>
          </div>
        </section>
        <section class="work-surface wide">
          <div class="surface-heading"><h3>最终质量评估</h3></div>
          <div class="form-grid two">
            <label>
              结果状态
              <select id="finalPassed">
                <option value="true" selected>通过</option>
                <option value="false">需要复习</option>
              </select>
            </label>
            <label>
              综合分数
              <input id="finalScore" type="number" min="0" max="100" value="90" />
            </label>
          </div>
          <label>
            反馈
            <textarea id="finalFeedback" rows="5" placeholder="结业评估备注"></textarea>
          </label>
          <button id="finalButton" class="command primary full" type="button">提交结业评估</button>
        </section>
        <section class="work-surface danger-surface">
          <div class="surface-heading"><h3><span class="material-symbols-outlined">shield</span> 高级风险操作</h3></div>
          <label class="toggle-row">
            <input id="deleteConfirm" type="checkbox" />
            确认删除当前用户和领域数据
          </label>
          <button id="deleteButton" class="command danger full" type="button" disabled>删除领域</button>
          <label>
            恢复点路径
            <input id="restorePath" placeholder="./data/backups/..." />
          </label>
          <label class="toggle-row">
            <input id="restoreConfirm" type="checkbox" />
            确认从该备份恢复
          </label>
          <button id="restoreButton" class="command danger full" type="button" disabled>恢复备份</button>
        </section>
      </div>
    </section>

    ${
      DEV_CONSOLE_ENABLED
        ? `
    <section id="consoleLayout" class="console-layout" aria-labelledby="consoleTitle" aria-hidden="true">
      <div class="console-card">
        <div class="surface-heading">
          <div class="console-title-group">
            <h2 id="consoleTitle">开发控制台</h2>
            <p id="resultTitle">最近操作：等待请求</p>
          </div>
          <div>
            <span>API 状态：活跃</span>
            <button id="closeConsoleButton" class="command subtle" type="button">收起</button>
            <button id="clearResultButton" class="command subtle" type="button">清空日志</button>
          </div>
        </div>
        <div id="requestLine" class="request-line">等待请求</div>
        <pre id="resultOutput">{}</pre>
      </div>
    </section>
    `
        : ""
    }
  </main>
`;

const api = new LearningCoachApi({ baseUrl: getInput("apiBaseUrl").value });

bindLearningVisualEvents();
renderBasicQuestionFields([]);
bindGlobalState();
bindViews();
bindActions();
syncPreview();
void syncAvailableDomains();

function bindGlobalState(): void {
  onInput("apiBaseUrl", () => api.setBaseUrl(value("apiBaseUrl")));
  onInput("adminApiKey", () => api.setAdminApiKey(value("adminApiKey")));
  onChange("customDomainLabel", syncCustomDomainDraft);
  onChange("domain", () => {
    syncPreview();
    resetQuestionContext();
  });
  onChange("userId", () => {
    syncDangerButtons();
    syncPreview();
    resetQuestionContext();
  });
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
  if (DEV_CONSOLE_ENABLED) {
    onClick("consoleToggleButton", toggleConsole);
    onClick("closeConsoleButton", closeConsole);
    onClick("clearResultButton", () => renderResult({ title: "已清空", data: {} }));
  }
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
  if (view === "questions") {
    void ensureQuestionPushLoaded();
    void syncQuestionSidebar();
  }
  if (view === "goals") {
    void syncGoalSummary();
  }
}

async function checkHealth(): Promise<void> {
  await runJson("健康检查", () => api.request<JsonValue>("/health"));
}

async function enrollDomain(): Promise<void> {
  await withButtonLoading("enrollButton", "创建学习目标", "创建中...", async () => {
    await runJson("创建学习目标", () =>
      api.request<JsonValue>(`/domains/${domain()}/enroll`, {
        method: "POST",
        body: {
          user_id: userId(),
          level: value("level"),
          target_level: value("targetLevel"),
          daily_minutes: numberValue("dailyMinutes"),
          learning_style: learningStyleValue(),
          delivery_time: value("deliveryTime"),
          language: value("language"),
          allow_online_resources: getInput("allowOnlineResources").checked,
        },
      }),
    );
    await syncGoalSummary();
  });
}

async function getDomainStatus(): Promise<void> {
  await withButtonLoading("statusButton", "查看状态", "同步中...", async () => {
    await runJson("领域状态", () =>
      api.request<JsonValue>(`/domains/${domain()}/status`, {
        query: { user_id: userId() },
      }),
    );
    await syncGoalSummary();
  });
}

async function triggerPush(): Promise<void> {
  if (pushRequestInFlight) {
    return;
  }
  pushRequestInFlight = true;
  setQuestionContentLoading(true, "正在准备今日问题...");
  try {
    await withButtonLoading("pushButton", "获取今日问题", "准备中...", async () => {
      await runJson("获取今日问题", async () => {
        const response = await api.request<TriggerResponse>("/schedules/trigger", {
          method: "POST",
          body: { user_id: userId(), domain: domain() },
        });
        if (response.data.push_id) {
          getInput("pushId").value = response.data.push_id;
          loadedQuestionContext = questionContextKey();
        }
        renderQuestionContent(response.data);
        return response;
      });
    });
  } finally {
    pushRequestInFlight = false;
    setQuestionContentLoading(false);
  }
}

async function submitAnswer(): Promise<void> {
  setEvaluationLoading(true);
  try {
    await withButtonLoading("submitButton", "提交并评估", "评估中...", async () => {
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
        void syncQuestionSidebar();
        if (currentView === "reports") {
          void refreshReportPage();
        }
        return response;
      });
    });
  } finally {
    setEvaluationLoading(false);
  }
}

async function loadReport(): Promise<void> {
  const requestId = ++reportRequestId;
  setPanelLoading("#reportContent", true);
  try {
    await runJson("学习报告", async () => {
      text("reportSyncStatus", "正在同步报告...");
      const response = await api.request<ReportPayload>(`/reports/${domain()}`, {
        query: { user_id: userId() },
      });
      if (requestId !== reportRequestId) {
        return response;
      }
      renderReportContent(response.data);
      text("reportSyncStatus", "报告已同步");
      return response;
    });
  } finally {
    if (requestId === reportRequestId) {
      setPanelLoading("#reportContent", false);
    }
  }
}

async function syncAvailableDomains(): Promise<void> {
  const select = document.querySelector<HTMLSelectElement>("#domain");
  if (!select) {
    throw new Error("Domain select not found");
  }
  const currentDomain = domain();
  const customOption = currentDraftDomainOption();
  try {
    const response = await api.request<DomainOptionResponse[]>("/domains");
    const options = response.data.length > 0 ? response.data : [{ domain: currentDomain, label: currentDomain }];
    select.replaceChildren(
      ...options.map((item) => {
        const option = document.createElement("option");
        option.value = item.domain;
        option.textContent = item.label;
        option.selected = item.domain === currentDomain;
        return option;
      }),
    );
    if (customOption) {
      upsertDomainOption(select, customOption);
    }
    if ([...select.options].some((item) => item.value === currentDomain)) {
      select.value = currentDomain;
    } else {
      select.value = customOption?.domain ?? options[0]?.domain ?? "ai_agent";
      syncPreview();
      resetQuestionContext();
    }
  } catch {
    select.replaceChildren();
    const option = document.createElement("option");
    option.value = currentDomain || "ai_agent";
    option.textContent = currentDomain || "AI Agent";
    option.selected = true;
    select.append(option);
    if (customOption) {
      upsertDomainOption(select, customOption);
      select.value = currentDomain || customOption.domain;
    }
  }
}

async function refreshReportPage(): Promise<void> {
  getReportContent().innerHTML = emptyReport("正在同步学习报告...");
  await withButtonLoading("refreshReportButton", "刷新数据", "同步中...", async () => {
    await loadReport();
    await syncReportDomainStatus();
  });
}

async function syncReportDomainStatus(): Promise<void> {
  try {
    const response = await api.request<DomainStatusResponse>(`/domains/${domain()}/status`, {
      query: { user_id: userId() },
    });
    const masteryRate =
      typeof response.data.mastery_rate === "number"
        ? response.data.mastery_rate
        : response.data.total_topics > 0
          ? response.data.mastered_topics / response.data.total_topics
          : 0;
    text(
      "reportSyncStatus",
      `报告已同步 · 状态 ${domainStatusLabel(response.data.status)} · 掌握率 ${Math.round(masteryRate * 100)}%`,
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
  const deletedDomain = domain();
  await withButtonLoading("deleteButton", `删除 ${userId()} / ${deletedDomain}`, "删除中...", async () => {
    await runJson("删除领域", () =>
      api.request<JsonValue>(`/domains/${deletedDomain}`, {
        method: "DELETE",
        body: { user_id: userId(), confirm: true },
      }),
    );
  });
  getInput("deleteConfirm").checked = false;
  syncDangerButtons();
  await syncAvailableDomains();
  if (domain() === deletedDomain) {
    resetQuestionContext();
    syncPreview();
  }
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
  if (!DEV_CONSOLE_ENABLED) {
    return;
  }
  text("resultTitle", `最近操作：${state.title}`);
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

function toggleConsole(): void {
  setConsoleVisible(!consoleVisible);
}

function closeConsole(): void {
  setConsoleVisible(false);
}

function setConsoleVisible(visible: boolean): void {
  if (!DEV_CONSOLE_ENABLED) {
    return;
  }
  consoleVisible = visible;
  const layout = document.querySelector<HTMLElement>("#consoleLayout");
  const toggleButton = document.querySelector<HTMLButtonElement>("#consoleToggleButton");
  if (!layout || !toggleButton) {
    return;
  }
  layout.classList.toggle("open", visible);
  layout.setAttribute("aria-hidden", String(!visible));
  toggleButton.setAttribute("aria-expanded", String(visible));
  toggleButton.classList.toggle("active", visible);
  toggleButton.title = visible ? "隐藏开发控制台" : "打开开发控制台";
  toggleButton.setAttribute("aria-label", visible ? "隐藏开发控制台" : "打开开发控制台");
}

function renderQuestionContent(data: TriggerResponse): void {
  text("questionBadge", data.delivered ? `${pushTypeLabel(data.push_type ?? "topic")}已获取` : "暂无可推送内容");
  text("theoryContent", data.delivered ? data.theory || "本次没有返回理论讲解。" : data.message);
  renderLearningVisual(data.delivered ? data.visual_url ?? DEFAULT_LEARNING_VISUAL : DEFAULT_LEARNING_VISUAL);
  const basicQuestions = data.delivered ? normalizeBasicQuestions(data.basic_questions) : [];
  renderBasicQuestionFields(basicQuestions);
  text("practiceQuestionContent", data.delivered ? data.practice_question || "本次没有返回实践题。" : "等待今日问题。");
  text("reflectionQuestionContent", data.delivered ? data.reflection_question || "本次没有返回反思题。" : "等待今日问题。");
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
  text("healthStatus", healthStatusLabel(status));
}

function syncDangerButtons(): void {
  getButton("deleteButton").disabled = !getInput("deleteConfirm").checked;
  getButton("deleteButton").textContent = `删除 ${userId()} / ${domain()}`;
  getButton("restoreButton").disabled =
    !getInput("restoreConfirm").checked || value("restorePath").trim().length === 0;
}

function syncPreview(): void {
  text("domainPreview", domain());
  text("currentDomainLabel", selectedDomainLabel());
  void syncGoalSummary();
  void syncQuestionSidebar();
  if (currentView === "reports") {
    void refreshReportPage();
  }
}

function syncCustomDomainDraft(): void {
  const select = document.querySelector<HTMLSelectElement>("#domain");
  if (!select) {
    return;
  }

  const customOption = currentDraftDomainOption();
  if (!customOption) {
    syncPreview();
    return;
  }

  upsertDomainOption(select, customOption);
  select.value = customOption.domain;
  syncPreview();
}

async function syncGoalSummary(): Promise<void> {
  const requestId = ++goalSummaryRequestId;
  setPanelLoading(".domain-card", true);
  setPanelLoading(".active-domain", true);
  try {
    const response = await api.request<DomainSummaryResponse>(`/domains/${domain()}/summary`, {
      query: { user_id: userId() },
    });
    if (requestId !== goalSummaryRequestId) {
      return;
    }
    renderGoalSummary(response.data);
  } catch {
    if (requestId !== goalSummaryRequestId) {
      return;
    }
    renderGoalSummary({
      domain: domain(),
      user_id: userId(),
      status: "not_started",
      current_level: "beginner",
      target_level: "beginner",
      mastery_percent: 0,
      avg_score: 0,
      active_topic_title: domain(),
      active_topic_id: "",
      topic_progress: [],
    });
  } finally {
    if (requestId === goalSummaryRequestId) {
      setPanelLoading(".domain-card", false);
      setPanelLoading(".active-domain", false);
    }
  }
}

async function syncQuestionSidebar(): Promise<void> {
  const requestId = ++questionSidebarRequestId;
  setQuestionSidebarLoading(true);
  try {
    const response = await api.request<ReportPayload>(`/reports/${domain()}`, {
      query: { user_id: userId() },
    });
    if (requestId !== questionSidebarRequestId) {
      return;
    }
    renderQuestionSidebar(response.data);
  } catch {
    if (requestId !== questionSidebarRequestId) {
      return;
    }
    renderQuestionSidebar({
      user_id: userId(),
      domain: domain(),
      generated_at: new Date().toISOString(),
      enrollment_status: null,
      summary: {
        total_topics: 0,
        mastered_topics: 0,
        review_due_topics: 0,
        mastery_rate: 0,
        avg_score: 0,
      },
      topic_rows: [],
      recent_evals: [],
      insights: {
        score_trend: "stable",
        top_strengths: [],
        top_weaknesses: [],
        common_missed_concepts: [],
        final_assessment_ready: false,
        stage_summary: "",
      },
    });
  } finally {
    if (requestId === questionSidebarRequestId) {
      setQuestionSidebarLoading(false);
    }
  }
}

function ensureQuestionPushLoaded(): Promise<void> | void {
  if (pushRequestInFlight) {
    return;
  }
  if (value("pushId").trim() && loadedQuestionContext === questionContextKey()) {
    return;
  }
  return triggerPush();
}

function resetQuestionContext(): void {
  loadedQuestionContext = "";
  getInput("pushId").value = "";
  renderQuestionContent({ push_id: null, delivered: false, message: "切换用户或领域后会自动重新获取今日问题。" });
}

function questionContextKey(): string {
  return `${userId()}::${domain()}`;
}

function renderBasicQuestionFields(questions: string[]): void {
  const container = document.querySelector<HTMLDivElement>("#basicQuestionsList");
  if (!container) {
    throw new Error("Basic questions container not found");
  }

  const fields = buildBasicQuestionFields(questions);
  currentBasicAnswerIds = fields.map((field) => field.answerId);
  container.replaceChildren(
    ...fields.map((field) => {
      const label = document.createElement("label");
      label.className = "basic-question-card";

      const title = document.createElement("span");
      title.className = "basic-question-title";
      title.textContent = `${field.index}. ${field.question}`;

      const textarea = document.createElement("textarea");
      textarea.id = field.answerId;
      textarea.rows = 3;
      textarea.placeholder = "输入你的回答...";

      label.append(title, textarea);
      return label;
    }),
  );
}

function renderLearningVisual(visualUrl: string): void {
  const card = document.querySelector<HTMLElement>(".learning-visual");
  const image = document.querySelector<HTMLImageElement>("#learningVisualImage");
  const placeholderLabel = document.querySelector<HTMLSpanElement>("#learningVisualPlaceholderLabel");
  if (!card || !image || !placeholderLabel) {
    throw new Error("Learning visual elements not found");
  }

  const resolvedUrl = visualUrl.trim();
  const hasVisual = resolvedUrl.length > 0;
  const optimizedUrl = hasVisual ? optimizeLearningVisualUrl(resolvedUrl) : "";
  card.dataset.state = hasVisual ? "loading" : "empty";
  image.hidden = !hasVisual;
  placeholderLabel.textContent = hasVisual ? "课程配图加载中" : "暂无课程配图";
  image.src = optimizedUrl;
  if (!hasVisual) {
    image.removeAttribute("src");
    return;
  }
  if (image.complete && image.naturalWidth > 0) {
    card.dataset.state = "ready";
  }
}

function renderGoalSummary(data: DomainSummaryResponse): void {
  text("domainPreview", data.domain);
  text("domainMasteryPercent", `${data.mastery_percent}%`);
  text("activeTopicTitle", data.active_topic_title || data.domain);
  text("activeTopicId", data.active_topic_id ? `ID: ${data.active_topic_id}` : "ID: --");

  const progressList = document.querySelector<HTMLDivElement>("#goalProgressList");
  if (!progressList) {
    throw new Error("Goal progress list not found");
  }

  const items = data.topic_progress.length > 0 ? data.topic_progress : [{ title: "等待学习主题", mastery_percent: 0 }];
  progressList.replaceChildren(
    ...items.map((item) => {
      const row = document.createElement("div");
      const title = document.createElement("span");
      title.textContent = item.title;
      const value = document.createElement("b");
      value.textContent = `${item.mastery_percent}%`;
      const bar = document.createElement("i");
      bar.style.setProperty("--value", `${item.mastery_percent}%`);
      row.append(title, value, bar);
      return row;
    }),
  );
}

function renderQuestionSidebar(data: ReportPayload): void {
  const latestEvaluation = data.recent_evals[0];
  const masteryEstimate =
    latestEvaluation && typeof latestEvaluation.mastery_estimate === "number"
      ? `${Math.round(latestEvaluation.mastery_estimate * 100)}%`
      : "--";
  text("questionDebugMetric", `> 最近掌握估计：${masteryEstimate}`);
  text(
    "questionDebugAction",
    `> 下一步：${latestEvaluation ? nextActionLabel(latestEvaluation.next_action) : "等待评估"}`,
  );

  const masteryList = document.querySelector<HTMLDivElement>("#questionMasteryList");
  if (!masteryList) {
    throw new Error("Question mastery list not found");
  }

  const items = data.topic_rows.length > 0 ? data.topic_rows.slice(0, 3) : [{ title: "等待学习主题", mastery_score: 0 }];
  masteryList.replaceChildren(
    ...items.map((item) => {
      const row = document.createElement("article");
      row.className = "question-mastery-item";

      const header = document.createElement("div");
      header.className = "question-mastery-header";

      const title = document.createElement("span");
      title.className = "question-mastery-title";
      title.textContent = item.title;

      const value = document.createElement("b");
      value.className = "question-mastery-level";
      value.textContent = `等级 ${masteryLevel(item)}`;

      const bar = document.createElement("i");
      bar.className = "question-mastery-bar";
      bar.style.setProperty("--value", `${normalizedMasteryScore(item)}%`);

      header.append(title, value);
      row.append(header, bar);
      return row;
    }),
  );
}

function setQuestionContentLoading(isLoading: boolean, badgeText = "等待中"): void {
  setPanelLoading(".question-surface", isLoading);
  text("questionBadge", badgeText);
  const button = getButton("pushButton");
  button.dataset.loading = String(isLoading);
  if (!isLoading && !value("pushId").trim()) {
    text("questionBadge", "等待中");
  }
}

function setEvaluationLoading(isLoading: boolean): void {
  setPanelLoading(".evaluation-panel", isLoading);
  const statusChip = document.querySelector<HTMLElement>(".evaluation-panel .status-chip");
  if (statusChip) {
    statusChip.textContent = isLoading ? "评估中" : "进行中";
  }
  if (isLoading) {
    text("evaluationAction", "系统正在分析答案...");
    text("evaluationFeedback", "评估进行中，结果会在响应返回后更新。");
  }
}

function setQuestionSidebarLoading(isLoading: boolean): void {
  setPanelLoading(".debug-card", isLoading);
  setPanelLoading(".mastery-mini", isLoading);
  const masteryList = document.querySelector<HTMLDivElement>("#questionMasteryList");
  if (!masteryList) {
    throw new Error("Question mastery list not found");
  }
  masteryList.dataset.state = isLoading ? "loading" : "ready";
  if (isLoading) {
    text("questionDebugMetric", "> 最近掌握估计：准备中...");
    text("questionDebugAction", "> 下一步：正在同步...");
    masteryList.replaceChildren(...Array.from({ length: 3 }, () => createQuestionMasterySkeleton()));
  }
}

function createQuestionMasterySkeleton(): HTMLElement {
  const row = document.createElement("article");
  row.className = "question-mastery-item question-mastery-item-skeleton";

  const header = document.createElement("div");
  header.className = "question-mastery-header";

  const title = document.createElement("span");
  title.className = "question-mastery-title";
  title.textContent = "正在同步主题掌握度";

  const value = document.createElement("b");
  value.className = "question-mastery-level";
  value.textContent = "等级 --";

  const bar = document.createElement("i");
  bar.className = "question-mastery-bar";
  bar.style.setProperty("--value", "32%");

  header.append(title, value);
  row.append(header, bar);
  return row;
}

function setPanelLoading(target: string, isLoading: boolean): void {
  const element = document.querySelector<HTMLElement>(target);
  if (!element) {
    return;
  }
  element.dataset.loading = String(isLoading);
  element.setAttribute("aria-busy", String(isLoading));
}

async function withButtonLoading<T>(
  buttonId: string,
  idleLabel: string,
  loadingLabel: string,
  action: () => Promise<T>,
): Promise<T> {
  const button = getButton(buttonId);
  const previous = button.innerHTML;
  button.disabled = true;
  button.dataset.loading = "true";
  button.textContent = loadingLabel;
  try {
    return await action();
  } finally {
    button.disabled = false;
    button.dataset.loading = "false";
    button.innerHTML = previous;
    if (!button.textContent?.trim()) {
      button.textContent = idleLabel;
    }
  }
}

function normalizedMasteryScore(item: Pick<ReportTopicRow, "mastery_score">): number {
  return Math.max(0, Math.min(100, Math.round(item.mastery_score)));
}

function masteryLevel(item: Pick<ReportTopicRow, "mastery_score">): number {
  const score = normalizedMasteryScore(item);
  return Math.max(1, Math.min(5, Math.ceil(score / 20) || 1));
}

function bindLearningVisualEvents(): void {
  const card = document.querySelector<HTMLElement>(".learning-visual");
  const image = document.querySelector<HTMLImageElement>("#learningVisualImage");
  const placeholderLabel = document.querySelector<HTMLSpanElement>("#learningVisualPlaceholderLabel");
  if (!card || !image || !placeholderLabel) {
    throw new Error("Learning visual elements not found");
  }

  image.addEventListener("load", () => {
    card.dataset.state = "ready";
  });
  image.addEventListener("error", () => {
    card.dataset.state = "empty";
    image.hidden = true;
    image.removeAttribute("src");
    placeholderLabel.textContent = "课程配图加载失败";
  });
}

function optimizeLearningVisualUrl(url: string): string {
  if (!url.startsWith("/data/images/")) {
    return url;
  }
  const resolved = new URL(url, window.location.origin);
  resolved.searchParams.set("variant", "preview");
  return `${resolved.pathname}${resolved.search}`;
}

function clearQuestionAnswers(): void {
  [...currentBasicAnswerIds, "practiceAnswer"].forEach((id) => {
    getInput(id).value = "";
  });
}

function buildSubmissionAnswer(): string {
  return formatSubmissionAnswer(
    currentBasicAnswerIds.map((id) => value(id)),
    value("practiceAnswer"),
    textContent("reflectionQuestionContent"),
  );
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

function selectedDomainLabel(): string {
  const select = document.querySelector<HTMLSelectElement>("#domain");
  if (!select) {
    return domain();
  }
  return select.selectedOptions[0]?.textContent?.trim() || domain();
}

function currentDraftDomainOption(): DomainOptionResponse | null {
  return buildDraftDomainOption(value("customDomainLabel"));
}

function upsertDomainOption(select: HTMLSelectElement, option: DomainOptionResponse): void {
  const existing = [...select.options].find((item) => item.value === option.domain);
  if (existing) {
    existing.textContent = option.label;
    return;
  }

  const created = document.createElement("option");
  created.value = option.domain;
  created.textContent = option.label;
  select.append(created);
}

function value(id: string): string {
  return getInput(id).value;
}

function numberValue(id: string): number {
  return Number(value(id));
}

function learningStyleValue(): string {
  const selected = document.querySelector<HTMLInputElement>('input[name="learningStyle"]:checked');
  return selected?.value ?? value("learningStyle");
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

function healthStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    ok: "正常",
    degraded: "降级",
    error: "错误",
    unknown: "未知",
  };
  return labels[status] ?? status;
}

function domainStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    active: "活跃",
    paused: "已暂停",
    archived: "已归档",
    awaiting_submission: "等待提交",
    final_assessment_due: "待结业评估",
    completed: "已完成",
  };
  return labels[status] ?? status;
}

function pushTypeLabel(pushType: string): string {
  const labels: Record<string, string> = {
    topic: "主题",
    review: "复习",
    final_assessment: "结业评估",
  };
  return labels[pushType] ?? pushType;
}
