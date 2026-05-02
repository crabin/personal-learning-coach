import "./styles/styles.css";

import { ApiError, LearningCoachApi, type ApiResponse } from "./api/apiClient";
import { buildDraftDomainOption } from "./features/domains/domainForm";
import { buildDomainSelectState } from "./features/domains/domainSelection";
import {
  feedbackText,
  formatScore,
  nextActionLabel,
  scoreTone,
  type EvaluationSummary,
} from "./features/evaluation/evaluationView";
import {
  buildBasicQuestionFields,
  buildSubmissionAnswer as formatSubmissionAnswer,
  normalizeBasicQuestions,
} from "./features/questions/questionView";
import {
  createProjectBackgroundController,
  getStoredProjectBackground,
  getFirstPaletteForGroup,
  getPaletteGroupForPalette,
  getProjectPaletteColors,
  getStoredProjectPalette,
  PROJECT_PALETTE_GROUPS,
  parseProjectBackgroundId,
  parseProjectPaletteId,
  PROJECT_BACKGROUND_PRESETS,
  saveProjectBackground,
  saveProjectPalette,
  type ProjectBackgroundId,
  type ProjectPaletteGroupId,
  type ProjectPaletteId,
} from "./shared/background/projectBackground";
import { buildReportExportFilename, serializeReportExport } from "./features/reports/reportExport";
import { emptyReport, renderReport, type ReportPayload, type ReportTopicRow } from "./features/reports/reportView";

type JsonValue = Record<string, unknown> | unknown[] | string | number | boolean | null;
type ViewId = "goals" | "questions" | "reports" | "settings" | "operations";
const DEV_CONSOLE_ENABLED = import.meta.env.DEV;
const AUTH_TOKEN_STORAGE_KEY = "personal-learning-coach.authToken";

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

interface AuthUser {
  user_id: string;
  name: string;
  email: string;
  role: "learner" | "admin";
}

interface AuthResponse {
  token: string;
  user: AuthUser;
}

interface RegisterCaptchaResponse {
  captcha_id: string;
  image_data_url: string;
  expires_in_seconds: number;
}

interface RegisterStartResponse {
  verification_id: string;
  email: string;
  expires_in_seconds: number;
}

interface AdminUser {
  user_id: string;
  name: string;
  email: string;
  role: "learner" | "admin";
  is_active: boolean;
  domain_count: number;
}

interface AdminDomain {
  domain: string;
  status: string;
  total_topics: number;
  mastered_topics: number;
  review_due_topics: number;
  avg_score: number;
}

const DEFAULT_LEARNING_VISUAL = "/data/images/backgroud1.png";
const NO_DOMAIN_MESSAGE = "你还没有创建学习领域，请先在学习目标页创建。";

let currentView: ViewId = "goals";
let currentUser: AuthUser | null = null;
let currentAuthPage: "login" | "register" = "login";
let currentRegisterCaptchaId = "";
let currentRegisterVerificationId = "";
let loadedQuestionContext = "";
let pushRequestInFlight = false;
let consoleVisible = false;
let currentBasicAnswerIds: string[] = [];
let goalSummaryRequestId = 0;
let questionSidebarRequestId = 0;
let reportRequestId = 0;
let hasExistingDomains = false;
let currentReport: ReportPayload | null = null;

const app = document.querySelector<HTMLDivElement>("#app");

if (!app) {
  throw new Error("App root not found");
}

app.innerHTML = `
  <div id="projectBackgroundHost" class="project-background" aria-hidden="true"></div>

  <section id="authShell" class="auth-shell" aria-labelledby="authTitle">
    <div class="auth-card">
      <div>
        <span class="auth-kicker">Personal Learning Coach</span>
        <h1 id="authTitle">登录后进入学习系统</h1>
        <p>注册会创建普通学习用户；管理员账号由系统环境种子创建。</p>
      </div>
      <div class="auth-panels">
        <section id="loginPanel" class="auth-panel">
          <h2>登录</h2>
          <label>
            邮箱
            <input id="loginEmail" type="email" autocomplete="email" />
          </label>
          <label>
            密码
            <input id="loginPassword" type="password" autocomplete="current-password" />
          </label>
          <button id="loginButton" class="command primary full" type="button">登录</button>
          <p class="auth-switch">
            还没有账号？
            <button id="showRegisterButton" class="auth-link-button" type="button">去注册</button>
          </p>
        </section>
        <section id="registerPanel" class="auth-panel" hidden>
          <h2>注册普通用户</h2>
          <label>
            姓名
            <input id="registerName" autocomplete="name" />
          </label>
          <label>
            邮箱
            <input id="registerEmail" type="email" autocomplete="email" />
          </label>
          <label>
            密码
            <input id="registerPassword" type="password" autocomplete="new-password" />
          </label>
          <label id="registerCaptchaLabel">
            图片验证码
            <span class="captcha-control">
              <img id="registerCaptchaImage" class="captcha-image" alt="图片验证码" />
              <button id="refreshRegisterCaptchaButton" class="command subtle" type="button">刷新</button>
            </span>
            <input id="registerCaptchaCode" autocomplete="off" inputmode="text" />
          </label>
          <label id="registerEmailCodeLabel" hidden>
            邮箱验证码
            <input id="registerEmailCode" autocomplete="one-time-code" inputmode="numeric" />
          </label>
          <button id="sendRegisterEmailButton" class="command full" type="button">发送邮箱验证码</button>
          <button id="registerButton" class="command primary full" type="button" hidden>
            完成注册并登录
          </button>
          <p class="auth-switch">
            已有账号？
            <button id="showLoginButton" class="auth-link-button" type="button">去登录</button>
          </p>
        </section>
      </div>
      <p id="authMessage" class="auth-message" aria-live="polite"></p>
    </div>
  </section>

  <main id="appShell" class="app-shell" hidden>
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
        <div class="config-cluster">
          <label class="config-field config-field-api">
            <span>API 地址</span>
            <input id="apiBaseUrl" value="/" placeholder="/" />
          </label>
          <label class="config-field config-field-user">
            <span>用户</span>
            <input id="userId" value="u1" />
          </label>
          <label class="config-field config-field-domain">
            <span>领域</span>
            <select id="domain">
              <option value="" selected>没有领域</option>
            </select>
          </label>
          <label class="config-field admin-key">
            <span>管理密钥</span>
            <input id="adminApiKey" type="password" placeholder="可选" />
          </label>
        </div>
        <div class="config-actions">
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
          <button
            id="settingsButton"
            class="icon-button"
            data-view="settings"
            type="button"
            aria-label="个人设置"
            title="个人设置"
          >
            <span class="material-symbols-outlined">account_circle</span>
          </button>
          <button id="logoutButton" class="icon-button" type="button" aria-label="退出登录" title="退出登录">
            <span class="material-symbols-outlined">logout</span>
          </button>
        </div>
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
              <p class="surface-meta">当前学习领域：<strong id="currentDomainLabel">没有领域</strong></p>
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
            <small>掌握：<span id="domainPreview">没有领域</span></small>
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
          <button id="exportReportButton" class="command primary" type="button">
            <span class="material-symbols-outlined">file_download</span>
            导出 JSON
          </button>
        </div>
      </div>
      <div id="reportContent" class="report-content">${emptyReport("打开本页后会加载报告。")}</div>
    </section>

    <section id="settingsView" class="landing-page" aria-labelledby="settingsTitle">
      <div class="page-header">
        <div>
          <h1 id="settingsTitle">个人设置</h1>
          <p>查看你当前名下的全部学习领域，并按需清理不再学习的内容。</p>
        </div>
        <button id="refreshSettingsButton" class="command" type="button">
          <span class="material-symbols-outlined">refresh</span>
          刷新领域
        </button>
      </div>
      <div class="settings-layout">
        <section class="work-surface background-settings-surface">
          <div class="surface-heading">
            <div>
              <h3><span class="material-symbols-outlined">palette</span> 项目背景</h3>
              <p>选择工作台的动态背景风格，仅保存在当前浏览器。</p>
            </div>
          </div>
          <label class="project-background-picker">
            背景风格
            <select id="projectBackgroundSelect">
              ${renderProjectBackgroundOptions()}
            </select>
          </label>
          <label class="project-background-picker">
            主颜色
            <select id="projectPaletteGroupSelect">
              ${renderProjectPaletteGroupOptions()}
            </select>
          </label>
          <label class="project-background-picker">
            颜色组合
            <select id="projectPaletteSelect"></select>
          </label>
          <div id="projectPalettePreview" class="project-palette-preview" aria-label="当前颜色组合预览"></div>
          <div id="projectBackgroundHint" class="project-background-hint" aria-live="polite"></div>
        </section>
        <section class="work-surface">
          <div class="surface-heading">
            <div>
              <h3><span class="material-symbols-outlined">account_circle</span> 账号信息</h3>
              <p>当前登录用户与可访问的数据范围。</p>
            </div>
          </div>
          <div id="settingsProfileCard" class="settings-profile-card"></div>
        </section>
        <section class="work-surface">
          <div class="surface-heading">
            <div>
              <h3><span class="material-symbols-outlined">inventory_2</span> 我的学习领域</h3>
              <p>仅展示当前账号可访问的领域。删除后会移除该领域下的学习记录。</p>
            </div>
          </div>
          <div id="settingsDomainList" class="settings-domain-list" aria-live="polite"></div>
        </section>
      </div>
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
        <section class="work-surface wide">
          <div class="surface-heading">
            <div>
              <h3><span class="material-symbols-outlined">admin_panel_settings</span> 用户管理</h3>
              <p>管理员可查看全部用户与学习领域，并执行角色、启停和进度管理。</p>
            </div>
            <button id="loadUsersButton" class="command" type="button">刷新用户</button>
          </div>
          <div id="adminUsersList" class="admin-list" aria-live="polite"></div>
          <div id="adminDomainsList" class="admin-list compact-admin-list" aria-live="polite"></div>
        </section>
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

const api = new LearningCoachApi({
  baseUrl: getInput("apiBaseUrl").value,
  authToken: localStorage.getItem(AUTH_TOKEN_STORAGE_KEY) ?? "",
});
const projectBackgroundController = createProjectBackgroundController(getProjectBackgroundHost());

bindAuthActions();
bindLearningVisualEvents();
renderBasicQuestionFields([]);
initializeProjectBackground();
bindGlobalState();
bindViews();
bindActions();
void bootstrapSession();

function bindAuthActions(): void {
  onClick("loginButton", login);
  onClick("sendRegisterEmailButton", startRegister);
  onClick("registerButton", completeRegister);
  onClick("refreshRegisterCaptchaButton", () => {
    void loadRegisterCaptcha();
  });
  onClick("showRegisterButton", () => showAuthPage("register"));
  onClick("showLoginButton", () => showAuthPage("login"));
  onClick("logoutButton", logout);
}

async function bootstrapSession(): Promise<void> {
  const token = localStorage.getItem(AUTH_TOKEN_STORAGE_KEY);
  if (!token) {
    showAuthShell("请先登录或注册。");
    return;
  }
  api.setAuthToken(token);
  try {
    const response = await api.request<AuthUser>("/auth/me");
    setAuthenticated(response.data, token);
  } catch {
    localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
    api.setAuthToken("");
    showAuthShell("登录已过期，请重新登录。");
  }
}

async function login(): Promise<void> {
  await authenticate("loginButton", "登录", "登录中...", () =>
    api.request<AuthResponse>("/auth/login", {
      method: "POST",
      body: { email: value("loginEmail"), password: value("loginPassword") },
    }),
  );
}

async function startRegister(): Promise<void> {
  await withButtonLoading("sendRegisterEmailButton", "发送邮箱验证码", "发送中...", async () => {
    try {
      if (!currentRegisterCaptchaId) {
        await loadRegisterCaptcha();
      }
      const response = await api.request<RegisterStartResponse>("/auth/register/start", {
        method: "POST",
        body: {
          name: value("registerName"),
          email: value("registerEmail"),
          password: value("registerPassword"),
          captcha_id: currentRegisterCaptchaId,
          captcha_code: value("registerCaptchaCode"),
        },
      });
      currentRegisterVerificationId = response.data.verification_id;
      setRegisterVerificationMode(true);
      text("authMessage", `验证码已发送到 ${response.data.email}。`);
    } catch (error) {
      const message = error instanceof ApiError ? error.message : String(error);
      text("authMessage", message);
      await loadRegisterCaptcha();
    }
  });
}

async function completeRegister(): Promise<void> {
  await authenticate("registerButton", "完成注册并登录", "注册中...", () =>
    api.request<AuthResponse>("/auth/register/complete", {
      method: "POST",
      body: {
        verification_id: currentRegisterVerificationId,
        email_code: value("registerEmailCode"),
      },
    }),
  );
}

async function authenticate(
  buttonId: string,
  idleLabel: string,
  loadingLabel: string,
  action: () => Promise<ApiResponse<AuthResponse>>,
): Promise<void> {
  await withButtonLoading(buttonId, idleLabel, loadingLabel, async () => {
    try {
      const response = await action();
      setAuthenticated(response.data.user, response.data.token);
    } catch (error) {
      const message = error instanceof ApiError ? error.message : String(error);
      text("authMessage", message);
    }
  });
}

async function logout(): Promise<void> {
  try {
    await api.request<JsonValue>("/auth/logout", { method: "POST" });
  } finally {
    currentUser = null;
    localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
    api.setAuthToken("");
    showAuthShell("已退出登录。");
  }
}

function setAuthenticated(user: AuthUser, token: string): void {
  currentUser = user;
  localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token);
  api.setAuthToken(token);
  getInput("userId").value = user.user_id;
  getInput("userId").readOnly = !isCurrentAdmin();
  document.querySelector<HTMLElement>("#authShell")!.hidden = true;
  document.querySelector<HTMLElement>("#appShell")!.hidden = false;
  document.querySelector<HTMLElement>(".config-bar")?.classList.toggle("config-bar-admin", isCurrentAdmin());
  document.querySelectorAll<HTMLElement>('[data-view="operations"]').forEach((item) => {
    item.hidden = !isCurrentAdmin();
  });
  const adminKey = document.querySelector<HTMLElement>(".admin-key");
  if (adminKey) {
    adminKey.hidden = !isCurrentAdmin();
  }
  const healthButton = document.querySelector<HTMLElement>("#healthButton");
  if (healthButton) {
    healthButton.hidden = !isCurrentAdmin();
  }
  const healthPill = document.querySelector<HTMLElement>(".health-pill");
  if (healthPill) {
    healthPill.hidden = !isCurrentAdmin();
  }
  const consoleButton = document.querySelector<HTMLElement>("#consoleToggleButton");
  if (consoleButton) {
    consoleButton.hidden = !isCurrentAdmin();
  }
  if (!isCurrentAdmin() && currentView === "operations") {
    showView("goals");
  }
  syncPreview();
  void syncAvailableDomains();
}

function showAuthShell(message: string): void {
  document.querySelector<HTMLElement>("#authShell")!.hidden = false;
  document.querySelector<HTMLElement>("#appShell")!.hidden = true;
  document.querySelector<HTMLElement>(".config-bar")?.classList.remove("config-bar-admin");
  showAuthPage(currentAuthPage, message);
}

function showAuthPage(page: "login" | "register", message = ""): void {
  currentAuthPage = page;
  const loginPanel = document.querySelector<HTMLElement>("#loginPanel");
  const registerPanel = document.querySelector<HTMLElement>("#registerPanel");
  if (loginPanel) {
    loginPanel.hidden = page !== "login";
  }
  if (registerPanel) {
    registerPanel.hidden = page !== "register";
  }
  text("authMessage", message);
  if (page === "register") {
    resetRegisterFlow();
    void loadRegisterCaptcha();
  }
}

async function loadRegisterCaptcha(): Promise<void> {
  try {
    const response = await api.request<RegisterCaptchaResponse>("/auth/register/captcha");
    currentRegisterCaptchaId = response.data.captcha_id;
    const image = document.querySelector<HTMLImageElement>("#registerCaptchaImage");
    if (image) {
      image.src = response.data.image_data_url;
    }
    getInput("registerCaptchaCode").value = "";
  } catch (error) {
    const message = error instanceof ApiError ? error.message : String(error);
    text("authMessage", message);
  }
}

function resetRegisterFlow(): void {
  currentRegisterVerificationId = "";
  setRegisterVerificationMode(false);
  getInput("registerCaptchaCode").value = "";
  getInput("registerEmailCode").value = "";
}

function setRegisterVerificationMode(isVerifyingEmail: boolean): void {
  currentRegisterCaptchaId = isVerifyingEmail ? currentRegisterCaptchaId : "";
  ["registerName", "registerEmail", "registerPassword", "registerCaptchaCode"].forEach((id) => {
    getInput(id).readOnly = isVerifyingEmail;
  });
  document.querySelector<HTMLElement>("#registerCaptchaLabel")!.hidden = isVerifyingEmail;
  document.querySelector<HTMLElement>("#registerEmailCodeLabel")!.hidden = !isVerifyingEmail;
  document.querySelector<HTMLElement>("#sendRegisterEmailButton")!.hidden = isVerifyingEmail;
  document.querySelector<HTMLElement>("#registerButton")!.hidden = !isVerifyingEmail;
}

function isCurrentAdmin(): boolean {
  return currentUser?.role === "admin";
}

function bindGlobalState(): void {
  onInput("apiBaseUrl", () => api.setBaseUrl(value("apiBaseUrl")));
  onInput("adminApiKey", () => api.setAdminApiKey(value("adminApiKey")));
  onChange("projectBackgroundSelect", () => {
    const selected = parseProjectBackgroundId(value("projectBackgroundSelect"));
    applyProjectBackground(selected, currentProjectPalette(), true);
  });
  onChange("projectPaletteGroupSelect", () => {
    const group = currentProjectPaletteGroup();
    const palette = getFirstPaletteForGroup(group);
    renderProjectPaletteOptions(group, palette);
    applyProjectBackground(currentProjectBackground(), palette, true);
  });
  onChange("projectPaletteSelect", () => {
    applyProjectBackground(currentProjectBackground(), currentProjectPalette(), true);
  });
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
  onClick("exportReportButton", exportReportJson);
  onClick("pauseButton", () => lifecycle("pause"));
  onClick("resumeButton", () => lifecycle("resume"));
  onClick("archiveButton", () => lifecycle("archive"));
  onClick("deleteButton", deleteDomain);
  onClick("backupButton", createBackup);
  onClick("eventsButton", listRuntimeEvents);
  onClick("alertsButton", listAlerts);
  onClick("restoreButton", restoreBackup);
  onClick("finalButton", submitFinalAssessment);
  onClick("loadUsersButton", loadAdminUsers);
  onClick("refreshSettingsButton", loadSettingsPage);
}

function showView(view: ViewId): void {
  currentView = view;
  document.querySelectorAll<HTMLElement>(".landing-page").forEach((page) => {
    page.classList.toggle("active", page.id === `${view}View`);
  });
  document.querySelectorAll<HTMLButtonElement>(".tab-button").forEach((button) => {
    button.setAttribute("aria-selected", String(button.dataset.view === view));
  });
  document.querySelectorAll<HTMLButtonElement>(".icon-button[data-view]").forEach((button) => {
    button.classList.toggle("active", button.dataset.view === view);
  });
  if (view === "reports") {
    if (canUseExistingDomain()) {
      void refreshReportPage();
    } else {
      renderNoDomainReport();
    }
  }
  if (view === "questions") {
    if (canUseExistingDomain()) {
      void ensureQuestionPushLoaded();
      void syncQuestionSidebar();
    } else {
      renderNoDomainQuestionState();
    }
  }
  if (view === "goals") {
    void syncGoalSummary();
  }
  if (view === "settings") {
    void loadSettingsPage();
  }
  if (view === "operations" && isCurrentAdmin()) {
    void loadAdminUsers();
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
    await syncAvailableDomains();
    await syncGoalSummary();
  });
}

async function getDomainStatus(): Promise<void> {
  if (!domain()) {
    renderNoDomainGoalSummary();
    return;
  }
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
  if (!canUseExistingDomain()) {
    renderNoDomainQuestionState();
    return;
  }
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
  if (!canUseExistingDomain()) {
    renderNoDomainQuestionState();
    return;
  }
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
  if (!canUseExistingDomain()) {
    renderNoDomainReport();
    return;
  }
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
    const state = buildDomainSelectState(response.data, currentDomain, customOption);
    hasExistingDomains = state.hasExistingDomains;
    select.replaceChildren(
      ...state.options.map((item) => {
        const option = document.createElement("option");
        option.value = item.domain;
        option.textContent = item.label;
        option.selected = item.domain === state.selectedDomain;
        return option;
      }),
    );
    const domainChanged = currentDomain !== state.selectedDomain;
    select.value = state.selectedDomain;
    syncPreview();
    if (domainChanged) {
      resetQuestionContext();
    }
  } catch {
    select.replaceChildren();
    const option = document.createElement("option");
    option.value = currentDomain;
    option.textContent = currentDomain || "没有领域";
    option.selected = true;
    select.append(option);
    hasExistingDomains = currentDomain.length > 0;
    if (customOption) {
      upsertDomainOption(select, customOption);
      select.value = currentDomain || customOption.domain;
    }
    syncPreview();
  }
}

async function refreshReportPage(): Promise<void> {
  if (!canUseExistingDomain()) {
    renderNoDomainReport();
    return;
  }
  currentReport = null;
  getReportContent().innerHTML = emptyReport("正在同步学习报告...");
  await withButtonLoading("refreshReportButton", "刷新数据", "同步中...", async () => {
    await loadReport();
    await syncReportDomainStatus();
  });
}

async function exportReportJson(): Promise<void> {
  if (!canUseExistingDomain()) {
    renderNoDomainReport();
    return;
  }
  await withButtonLoading("exportReportButton", "导出 JSON", "导出中...", async () => {
    const report = currentReport ?? (await fetchReportForExport());
    downloadReportJson(report);
    text("reportSyncStatus", `JSON 已导出：${buildReportExportFilename(report)}`);
  });
}

async function fetchReportForExport(): Promise<ReportPayload> {
  text("reportSyncStatus", "正在准备导出数据...");
  const response = await api.request<ReportPayload>(`/reports/${domain()}`, {
    query: { user_id: userId() },
  });
  renderReportContent(response.data);
  return response.data;
}

function downloadReportJson(data: ReportPayload): void {
  const blob = new Blob([serializeReportExport(data)], { type: "application/json;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = buildReportExportFilename(data);
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

async function syncReportDomainStatus(): Promise<void> {
  if (!canUseExistingDomain()) {
    renderNoDomainReport();
    return;
  }
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

async function loadAdminUsers(): Promise<void> {
  await withButtonLoading("loadUsersButton", "刷新用户", "同步中...", async () => {
    await runJson("管理员用户列表", async () => {
      const response = await api.request<AdminUser[]>("/admin/users", { admin: true });
      renderAdminUsers(response.data);
      return response;
    });
  });
}

async function loadSettingsPage(): Promise<void> {
  if (!currentUser) {
    return;
  }
  const user = currentUser;
  await withButtonLoading("refreshSettingsButton", "刷新领域", "同步中...", async () => {
    const response = await api.request<DomainOptionResponse[]>("/domains");
    const domains = response.data.filter((item) => item.domain.trim().length > 0);
    const summaries = await Promise.all(
      domains.map(async (item) => {
        try {
          const summary = await api.request<DomainSummaryResponse>(`/domains/${item.domain}/summary`, {
            query: { user_id: user.user_id },
          });
          return { option: item, summary: summary.data };
        } catch {
          return { option: item, summary: null };
        }
      }),
    );
    const realDomains = summaries.filter(
      ({ summary }) =>
        summary !== null &&
        (summary.status !== "not_started" ||
          summary.active_topic_id.length > 0 ||
          summary.topic_progress.length > 0 ||
          summary.mastery_percent > 0),
    );
    renderSettingsProfile(realDomains.length);
    renderSettingsDomains(realDomains);
  });
}

async function deleteOwnDomainFromSettings(domainToDelete: string): Promise<void> {
  if (!currentUser) {
    return;
  }
  const user = currentUser;
  if (!window.confirm(`确认删除领域 ${domainToDelete}？该领域下的学习记录会一起移除。`)) {
    return;
  }
  await runJson("删除我的领域", () =>
    api.request<JsonValue>(`/domains/${domainToDelete}`, {
      method: "DELETE",
      body: { user_id: user.user_id, confirm: true },
    }),
  );
  await syncAvailableDomains();
  if (domain() === domainToDelete) {
    resetQuestionContext();
    syncPreview();
  }
  await loadSettingsPage();
}

async function loadAdminDomains(userIdToLoad: string): Promise<void> {
  await runJson("管理员用户领域", async () => {
    const response = await api.request<AdminDomain[]>(`/admin/users/${userIdToLoad}/domains`, {
      admin: true,
    });
    renderAdminDomains(userIdToLoad, response.data);
    return response;
  });
}

async function updateAdminUser(user: AdminUser, patch: Partial<Pick<AdminUser, "role" | "is_active">>): Promise<void> {
  await runJson("更新用户", async () => {
    const response = await api.request<AdminUser>(`/admin/users/${user.user_id}`, {
      method: "PATCH",
      admin: true,
      body: patch,
    });
    await loadAdminUsers();
    return response;
  });
}

async function adminDomainAction(userIdToUpdate: string, domainToUpdate: string, action: "archive" | "reset" | "delete"): Promise<void> {
  const destructive = action === "reset" || action === "delete";
  if (destructive && !window.confirm(`确认${action === "reset" ? "重置进度" : "删除领域"}：${userIdToUpdate} / ${domainToUpdate}？`)) {
    return;
  }
  await runJson("管理员领域操作", async () => {
    const response = await api.request<JsonValue>(
      `/admin/users/${userIdToUpdate}/domains/${domainToUpdate}${action === "delete" ? "" : `/${action}`}`,
      {
        method: action === "delete" ? "DELETE" : "POST",
        admin: true,
      },
    );
    await loadAdminDomains(userIdToUpdate);
    return response;
  });
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
  currentReport = data;
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
  text("domainPreview", domain() || "没有领域");
  text("currentDomainLabel", selectedDomainLabel());
  void syncGoalSummary();
  if (canUseExistingDomain()) {
    void syncQuestionSidebar();
  } else {
    renderNoDomainQuestionState();
  }
  if (currentView === "reports") {
    if (canUseExistingDomain()) {
      void refreshReportPage();
    } else {
      renderNoDomainReport();
    }
  }
  if (currentView === "settings") {
    void loadSettingsPage();
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
  if (!domain()) {
    renderNoDomainGoalSummary();
    return;
  }
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
      active_topic_title: domain() || "没有领域",
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
  if (!canUseExistingDomain()) {
    renderNoDomainQuestionState();
    return;
  }
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
  if (!canUseExistingDomain()) {
    renderNoDomainQuestionState();
    return;
  }
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

function renderNoDomainGoalSummary(): void {
  renderGoalSummary({
    domain: "没有领域",
    user_id: userId(),
    status: "not_started",
    current_level: "beginner",
    target_level: "beginner",
    mastery_percent: 0,
    avg_score: 0,
    active_topic_title: NO_DOMAIN_MESSAGE,
    active_topic_id: "",
    topic_progress: [],
  });
}

function renderNoDomainQuestionState(): void {
  setQuestionContentLoading(false);
  renderQuestionContent({ push_id: null, delivered: false, message: NO_DOMAIN_MESSAGE });
  text("questionDebugMetric", "> 最近掌握估计：没有领域");
  text("questionDebugAction", "> 下一步：先创建学习领域");
  const masteryList = document.querySelector<HTMLDivElement>("#questionMasteryList");
  if (!masteryList) {
    throw new Error("Question mastery list not found");
  }
  const row = document.createElement("article");
  row.className = "question-mastery-item";
  const title = document.createElement("span");
  title.className = "question-mastery-title";
  title.textContent = NO_DOMAIN_MESSAGE;
  row.append(title);
  masteryList.replaceChildren(row);
}

function renderNoDomainReport(): void {
  currentReport = null;
  getReportContent().innerHTML = emptyReport(NO_DOMAIN_MESSAGE);
  text("reportSyncStatus", "没有学习领域");
  setPanelLoading("#reportContent", false);
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

function renderSettingsProfile(domainCount: number): void {
  const container = document.querySelector<HTMLDivElement>("#settingsProfileCard");
  if (!container) {
    throw new Error("Settings profile card not found");
  }
  if (!currentUser) {
    container.textContent = "未登录。";
    return;
  }

  const roleLabel = currentUser.role === "admin" ? "管理员" : "普通用户";
  const profile = document.createElement("article");
  profile.className = "settings-profile-block";
  const name = document.createElement("strong");
  name.textContent = currentUser.name;
  const email = document.createElement("span");
  email.textContent = currentUser.email;
  profile.append(name, email);

  const metrics = document.createElement("article");
  metrics.className = "settings-profile-metrics";
  [
    ["身份", roleLabel],
    ["用户 ID", currentUser.user_id],
    ["学习领域", `${domainCount} 个`],
  ].forEach(([label, metricValue]) => {
    const item = document.createElement("div");
    const small = document.createElement("small");
    small.textContent = label;
    const strong = document.createElement("b");
    strong.textContent = metricValue;
    item.append(small, strong);
    metrics.append(item);
  });

  container.replaceChildren(profile, metrics);
}

function initializeProjectBackground(): void {
  const storedPalette = getStoredProjectPalette();
  const storedGroup = getPaletteGroupForPalette(storedPalette)?.id ?? PROJECT_PALETTE_GROUPS[0].id;
  getProjectPaletteGroupSelect().value = storedGroup;
  renderProjectPaletteOptions(storedGroup, storedPalette);
  applyProjectBackground(getStoredProjectBackground(), storedPalette, false);
}

function applyProjectBackground(id: ProjectBackgroundId, paletteId: ProjectPaletteId, persist: boolean): void {
  const selected = projectBackgroundController.apply(id, paletteId);
  const palette = parseProjectPaletteId(paletteId);
  const select = getProjectBackgroundSelect();
  select.value = selected;
  getProjectPaletteSelect().value = palette;
  renderProjectPalettePreview(palette);
  applyProjectPaletteTheme(palette);
  if (persist) {
    saveProjectBackground(selected);
    saveProjectPalette(palette);
  }
  const preset = PROJECT_BACKGROUND_PRESETS.find((item) => item.id === selected);
  const paletteLabel = PROJECT_PALETTE_GROUPS.flatMap((group) => group.palettes).find(
    (item) => item.id === palette,
  )?.label;
  text("projectBackgroundHint", `${preset?.description ?? "已应用项目背景。"} 当前组合：${paletteLabel ?? "默认色板"}`);
}

function applyProjectPaletteTheme(paletteId: ProjectPaletteId): void {
  const colors = getProjectPaletteColors(paletteId);
  const [primary, secondary, soft, surface, accent, glow] = colors;
  const root = document.documentElement;
  root.style.setProperty("--primary", primary ?? "#004ac6");
  root.style.setProperty("--primary-bright", secondary ?? "#2563eb");
  root.style.setProperty("--primary-soft", soft ?? "#dbe1ff");
  root.style.setProperty("--secondary-soft", surface ?? "#eaddff");
  root.style.setProperty("--tertiary", accent ?? "#bc4800");
  root.style.setProperty("--palette-glow", glow ?? secondary ?? "#7dd5ff");
  root.style.setProperty("--palette-glow-rgb", hexToRgb(glow ?? secondary ?? "#7dd5ff"));
  root.style.setProperty("--palette-primary-rgb", hexToRgb(primary ?? "#004ac6"));
}

function renderProjectBackgroundOptions(): string {
  return PROJECT_BACKGROUND_PRESETS.map(
    (preset) => `<option value="${preset.id}">${preset.label}</option>`,
  ).join("");
}

function renderProjectPaletteGroupOptions(): string {
  return PROJECT_PALETTE_GROUPS.map(
    (group) => `<option value="${group.id}">${group.label}</option>`,
  ).join("");
}

function renderProjectPaletteOptions(groupId: ProjectPaletteGroupId, selectedPalette: ProjectPaletteId): void {
  const group = PROJECT_PALETTE_GROUPS.find((item) => item.id === groupId) ?? PROJECT_PALETTE_GROUPS[0];
  const select = getProjectPaletteSelect();
  select.replaceChildren(
    ...group.palettes.map((palette) => {
      const option = document.createElement("option");
      option.value = palette.id;
      option.textContent = palette.label;
      option.selected = palette.id === selectedPalette;
      return option;
    }),
  );
}

function renderProjectPalettePreview(paletteId: ProjectPaletteId): void {
  const palette = PROJECT_PALETTE_GROUPS.flatMap((group) => group.palettes).find(
    (item) => item.id === paletteId,
  );
  const container = document.querySelector<HTMLDivElement>("#projectPalettePreview");
  if (!container) {
    throw new Error("Project palette preview not found");
  }
  container.replaceChildren(
    ...(palette?.colors ?? []).map((color) => {
      const swatch = document.createElement("span");
      swatch.style.background = color;
      return swatch;
    }),
  );
}

function getProjectBackgroundHost(): HTMLElement {
  const element = document.querySelector<HTMLElement>("#projectBackgroundHost");
  if (!element) {
    throw new Error("Project background host not found");
  }
  return element;
}

function getProjectBackgroundSelect(): HTMLSelectElement {
  const element = document.querySelector<HTMLSelectElement>("#projectBackgroundSelect");
  if (!element) {
    throw new Error("Project background select not found");
  }
  return element;
}

function getProjectPaletteGroupSelect(): HTMLSelectElement {
  const element = document.querySelector<HTMLSelectElement>("#projectPaletteGroupSelect");
  if (!element) {
    throw new Error("Project palette group select not found");
  }
  return element;
}

function getProjectPaletteSelect(): HTMLSelectElement {
  const element = document.querySelector<HTMLSelectElement>("#projectPaletteSelect");
  if (!element) {
    throw new Error("Project palette select not found");
  }
  return element;
}

function currentProjectBackground(): ProjectBackgroundId {
  return parseProjectBackgroundId(value("projectBackgroundSelect"));
}

function currentProjectPaletteGroup(): ProjectPaletteGroupId {
  const selected = value("projectPaletteGroupSelect");
  return PROJECT_PALETTE_GROUPS.some((group) => group.id === selected)
    ? (selected as ProjectPaletteGroupId)
    : PROJECT_PALETTE_GROUPS[0].id;
}

function currentProjectPalette(): ProjectPaletteId {
  return parseProjectPaletteId(value("projectPaletteSelect"));
}

function hexToRgb(hex: string): string {
  const normalized = hex.replace("#", "");
  const value = normalized.length === 3
    ? normalized.split("").map((part) => `${part}${part}`).join("")
    : normalized;
  const parsed = Number.parseInt(value, 16);
  if (Number.isNaN(parsed)) {
    return "0, 74, 198";
  }
  return `${(parsed >> 16) & 255}, ${(parsed >> 8) & 255}, ${parsed & 255}`;
}

function renderSettingsDomains(
  items: Array<{ option: DomainOptionResponse; summary: DomainSummaryResponse | null }>,
): void {
  const container = document.querySelector<HTMLDivElement>("#settingsDomainList");
  if (!container) {
    throw new Error("Settings domain list not found");
  }
  if (items.length === 0) {
    const empty = document.createElement("article");
    empty.className = "settings-empty";
    empty.textContent = "你还没有创建学习领域。";
    container.replaceChildren(empty);
    return;
  }

  container.replaceChildren(
    ...items.map(({ option, summary }) => {
      const row = document.createElement("article");
      row.className = "settings-domain-row";

      const header = document.createElement("div");
      header.className = "settings-domain-header";

      const titleGroup = document.createElement("div");
      const title = document.createElement("strong");
      title.textContent = option.label;
      const meta = document.createElement("span");
      meta.textContent = summary
        ? `${domainStatusLabel(summary.status)} · 掌握率 ${summary.mastery_percent}% · 当前主题 ${summary.active_topic_title || option.label}`
        : "领域状态暂时无法加载";
      titleGroup.append(title, meta);

      const actions = document.createElement("div");
      actions.className = "settings-domain-actions";
      actions.append(
        adminButton("切换到此领域", () => {
          getInput("domain").value = option.domain;
          showView("goals");
          syncPreview();
          resetQuestionContext();
        }),
        adminButton("删除领域", () => void deleteOwnDomainFromSettings(option.domain), true),
      );

      header.append(titleGroup, actions);

      const progress = document.createElement("div");
      progress.className = "settings-domain-progress";
      if (summary && summary.topic_progress.length > 0) {
        progress.replaceChildren(
          ...summary.topic_progress.map((topic) => {
            const rowItem = document.createElement("div");
            const label = document.createElement("span");
            label.textContent = topic.title;
            const value = document.createElement("b");
            value.textContent = `${topic.mastery_percent}%`;
            const bar = document.createElement("i");
            bar.style.setProperty("--value", `${topic.mastery_percent}%`);
            rowItem.append(label, value, bar);
            return rowItem;
          }),
        );
      } else {
        progress.innerHTML = `<div><span>等待学习主题</span><b>0%</b><i style="--value: 0%"></i></div>`;
      }

      row.append(header, progress);
      return row;
    }),
  );
}

function renderAdminUsers(users: AdminUser[]): void {
  const container = document.querySelector<HTMLDivElement>("#adminUsersList");
  if (!container) {
    throw new Error("Admin users list not found");
  }
  if (users.length === 0) {
    container.textContent = "暂无用户。";
    return;
  }
  container.replaceChildren(
    ...users.map((user) => {
      const row = document.createElement("article");
      row.className = "admin-row";

      const summary = document.createElement("div");
      const title = document.createElement("strong");
      title.textContent = `${user.name} · ${user.email}`;
      const meta = document.createElement("span");
      meta.textContent = `${user.role === "admin" ? "管理员" : "普通用户"} · ${user.is_active ? "启用" : "停用"} · ${user.domain_count} 个领域`;
      summary.append(title, meta);

      const actions = document.createElement("div");
      actions.className = "admin-actions";
      actions.append(
        adminButton("领域", () => void loadAdminDomains(user.user_id)),
        adminButton(user.role === "admin" ? "设为普通" : "设为管理员", () =>
          void updateAdminUser(user, { role: user.role === "admin" ? "learner" : "admin" }),
        ),
        adminButton(user.is_active ? "停用" : "启用", () =>
          void updateAdminUser(user, { is_active: !user.is_active }),
        ),
      );
      row.append(summary, actions);
      return row;
    }),
  );
}

function renderAdminDomains(userIdToRender: string, domains: AdminDomain[]): void {
  const container = document.querySelector<HTMLDivElement>("#adminDomainsList");
  if (!container) {
    throw new Error("Admin domains list not found");
  }
  if (domains.length === 0) {
    container.textContent = `${userIdToRender} 暂无学习领域。`;
    return;
  }
  container.replaceChildren(
    ...domains.map((item) => {
      const row = document.createElement("article");
      row.className = "admin-row";

      const summary = document.createElement("div");
      const title = document.createElement("strong");
      title.textContent = item.domain;
      const meta = document.createElement("span");
      meta.textContent = `${domainStatusLabel(item.status)} · ${item.mastered_topics}/${item.total_topics} 已掌握 · 均分 ${Math.round(item.avg_score)}`;
      summary.append(title, meta);

      const actions = document.createElement("div");
      actions.className = "admin-actions";
      actions.append(
        adminButton("归档", () => void adminDomainAction(userIdToRender, item.domain, "archive")),
        adminButton("重置", () => void adminDomainAction(userIdToRender, item.domain, "reset")),
        adminButton("删除", () => void adminDomainAction(userIdToRender, item.domain, "delete"), true),
      );
      row.append(summary, actions);
      return row;
    }),
  );
}

function adminButton(label: string, handler: () => void, danger = false): HTMLButtonElement {
  const button = document.createElement("button");
  button.type = "button";
  button.className = danger ? "command danger" : "command";
  button.textContent = label;
  button.addEventListener("click", handler);
  return button;
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

function canUseExistingDomain(): boolean {
  return hasExistingDomains && domain().length > 0;
}

function selectedDomainLabel(): string {
  const select = document.querySelector<HTMLSelectElement>("#domain");
  if (!select) {
    return domain() || "没有领域";
  }
  return select.selectedOptions[0]?.textContent?.trim() || domain() || "没有领域";
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
