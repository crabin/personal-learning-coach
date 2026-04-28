import "./styles.css";

import { ApiError, LearningCoachApi, type ApiResponse } from "./apiClient";

type JsonValue = Record<string, unknown> | unknown[] | string | number | boolean | null;

interface ResultState {
  title: string;
  request?: ApiResponse<unknown>["request"];
  data?: unknown;
  error?: string;
  reportHtml?: string;
}

const app = document.querySelector<HTMLDivElement>("#app");

if (!app) {
  throw new Error("App root not found");
}

app.innerHTML = `
  <main class="shell">
    <header class="topbar">
      <div>
        <p class="eyebrow">Personal Learning Coach</p>
        <h1>学习教练控制台</h1>
      </div>
      <button id="healthButton" class="command primary" type="button">检查健康状态</button>
    </header>

    <section class="control-strip" aria-label="全局配置">
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

    <section class="status-band" aria-live="polite">
      <div>
        <span class="status-dot" id="healthDot"></span>
        <strong id="healthStatus">尚未检查</strong>
      </div>
      <span id="healthMeta">点击右上角按钮读取 /health</span>
    </section>

    <div class="workspace">
      <section class="panel learning-panel" aria-labelledby="learningTitle">
        <div class="section-heading">
          <div>
            <p class="eyebrow">Learning Loop</p>
            <h2 id="learningTitle">学习闭环</h2>
          </div>
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
            推送时间
            <input id="deliveryTime" value="20:30" />
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

        <div class="button-grid">
          <button id="enrollButton" class="command primary" type="button">报名/初始化</button>
          <button id="statusButton" class="command" type="button">查看状态</button>
          <button id="pushButton" class="command" type="button">手动推送</button>
          <button id="reportButton" class="command" type="button">查看报告</button>
        </div>

        <div class="answer-block">
          <label>
            Push ID
            <input id="pushId" placeholder="手动推送后会自动填入" />
          </label>
          <label>
            作答内容
            <textarea id="rawAnswer" rows="5" placeholder="输入你的练习答案、实践记录或反思"></textarea>
          </label>
          <label>
            实践结果
            <input id="practiceResult" placeholder="例如：完成一个小原型" />
          </label>
          <label>
            规范化答案
            <input id="normalizedAnswer" placeholder="可选，留空则后端自动使用作答内容" />
          </label>
          <label>
            解析备注
            <input id="parsingNotes" placeholder="可选，例如：从自由文本回复中提取" />
          </label>
          <button id="submitButton" class="command primary" type="button">提交答案并评估</button>
        </div>
      </section>

      <section class="panel operations-panel" aria-labelledby="operationsTitle">
        <div class="section-heading">
          <div>
            <p class="eyebrow">Operations</p>
            <h2 id="operationsTitle">管理与运维</h2>
          </div>
        </div>

        <div class="button-grid compact">
          <button id="pauseButton" class="command" type="button">暂停领域</button>
          <button id="resumeButton" class="command" type="button">恢复领域</button>
          <button id="archiveButton" class="command" type="button">归档领域</button>
          <button id="backupButton" class="command" type="button">创建备份</button>
          <button id="eventsButton" class="command" type="button">运行事件</button>
          <button id="alertsButton" class="command" type="button">当前告警</button>
        </div>

        <div class="final-box">
          <h3>结业评估</h3>
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
          <button id="finalButton" class="command primary" type="button">提交结业评估</button>
        </div>

        <details class="danger-zone">
          <summary>高级危险操作</summary>
          <div class="danger-content">
            <label class="toggle-row">
              <input id="deleteConfirm" type="checkbox" />
              确认删除当前用户和领域的所有相关数据
            </label>
            <button id="deleteButton" class="command danger" type="button" disabled>删除领域</button>

            <label>
              备份路径
              <input id="restorePath" placeholder="./data/backups/..." />
            </label>
            <label class="toggle-row">
              <input id="restoreConfirm" type="checkbox" />
              确认用该备份恢复数据
            </label>
            <button id="restoreButton" class="command danger" type="button" disabled>恢复备份</button>
          </div>
        </details>
      </section>
    </div>

    <section class="result-layout" aria-labelledby="resultTitle">
      <div class="panel result-panel">
        <div class="section-heading">
          <div>
            <p class="eyebrow">Response</p>
            <h2 id="resultTitle">最近请求</h2>
          </div>
          <button id="clearResultButton" class="command subtle" type="button">清空</button>
        </div>
        <div id="requestLine" class="request-line">等待请求</div>
        <pre id="resultOutput">{}</pre>
      </div>
      <div class="panel report-panel">
        <div class="section-heading">
          <div>
            <p class="eyebrow">HTML Report</p>
            <h2>报告预览</h2>
          </div>
        </div>
        <iframe id="reportFrame" title="学习报告预览"></iframe>
      </div>
    </section>
  </main>
`;

const api = new LearningCoachApi({ baseUrl: getInput("apiBaseUrl").value });

bindGlobalState();
bindActions();

function bindGlobalState(): void {
  getInput("apiBaseUrl").addEventListener("input", () => {
    api.setBaseUrl(getInput("apiBaseUrl").value);
  });
  getInput("adminApiKey").addEventListener("input", () => {
    api.setAdminApiKey(getInput("adminApiKey").value);
  });
  getInput("deleteConfirm").addEventListener("change", syncDangerButtons);
  getInput("restoreConfirm").addEventListener("change", syncDangerButtons);
  getInput("restorePath").addEventListener("input", syncDangerButtons);
  getInput("userId").addEventListener("input", syncDangerButtons);
  getInput("domain").addEventListener("input", syncDangerButtons);
  syncDangerButtons();
}

function bindActions(): void {
  onClick("healthButton", checkHealth);
  onClick("enrollButton", enrollDomain);
  onClick("statusButton", getDomainStatus);
  onClick("pushButton", triggerPush);
  onClick("submitButton", submitAnswer);
  onClick("reportButton", loadReport);
  onClick("pauseButton", () => lifecycle("pause"));
  onClick("resumeButton", () => lifecycle("resume"));
  onClick("archiveButton", () => lifecycle("archive"));
  onClick("deleteButton", deleteDomain);
  onClick("backupButton", createBackup);
  onClick("eventsButton", listRuntimeEvents);
  onClick("alertsButton", listAlerts);
  onClick("restoreButton", restoreBackup);
  onClick("finalButton", submitFinalAssessment);
  onClick("clearResultButton", () => {
    renderResult({ title: "已清空", data: {} });
    getFrame("reportFrame").srcdoc = "";
  });
}

async function checkHealth(): Promise<void> {
  await runJson("健康检查", () => api.request<JsonValue>("/health"));
}

async function enrollDomain(): Promise<void> {
  await runJson("报名/初始化", () =>
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
  await runJson("手动推送", async () => {
    const response = await api.request<JsonValue>("/schedules/trigger", {
      method: "POST",
      body: { user_id: userId(), domain: domain() },
    });
    if (isRecord(response.data) && typeof response.data.push_id === "string") {
      getInput("pushId").value = response.data.push_id;
    }
    return response;
  });
}

async function submitAnswer(): Promise<void> {
  await runJson("提交答案", () =>
    api.request<JsonValue>("/submissions", {
      method: "POST",
      body: {
        user_id: userId(),
        push_id: value("pushId"),
        raw_answer: value("rawAnswer"),
        practice_result: value("practiceResult"),
        normalized_answer: value("normalizedAnswer"),
        parsing_notes: value("parsingNotes"),
      },
    }),
  );
}

async function loadReport(): Promise<void> {
  await runText("学习报告", async () => {
    const response = await api.request<string>(`/reports/${domain()}`, {
      query: { user_id: userId() },
      responseType: "text",
    });
    getFrame("reportFrame").srcdoc = response.data;
    return response;
  });
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
  await runJson("创建备份", () =>
    api.request<JsonValue>("/admin/backup", {
      method: "POST",
      admin: true,
    }),
  );
}

async function listRuntimeEvents(): Promise<void> {
  await runJson("运行事件", () =>
    api.request<JsonValue>("/admin/runtime-events", {
      query: { limit: 20 },
      admin: true,
    }),
  );
}

async function listAlerts(): Promise<void> {
  await runJson("当前告警", () =>
    api.request<JsonValue>("/admin/alerts", {
      admin: true,
    }),
  );
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

async function runText(title: string, action: () => Promise<ApiResponse<string>>): Promise<void> {
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
      reportHtml: typeof response.data === "string" ? response.data : undefined,
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
  document.querySelector("#resultTitle")!.textContent = state.title;
  const requestLine = document.querySelector<HTMLDivElement>("#requestLine")!;
  requestLine.textContent = state.request
    ? `${state.request.method} ${state.request.url}`
    : state.error
      ? "请求失败"
      : "等待请求";

  const output = document.querySelector<HTMLPreElement>("#resultOutput")!;
  if (state.error) {
    output.textContent = state.error;
    output.classList.add("error-text");
    return;
  }
  output.classList.remove("error-text");
  output.textContent =
    typeof state.data === "string" && state.reportHtml
      ? state.data.slice(0, 1200)
      : JSON.stringify(state.data ?? {}, null, 2);
}

function updateHealth(data: unknown): void {
  const status = isRecord(data) && typeof data.status === "string" ? data.status : "unknown";
  const dot = document.querySelector<HTMLSpanElement>("#healthDot")!;
  const label = document.querySelector<HTMLElement>("#healthStatus")!;
  const meta = document.querySelector<HTMLSpanElement>("#healthMeta")!;
  dot.dataset.status = status;
  label.textContent = status;
  meta.textContent = isRecord(data)
    ? `delivery=${String(data.delivery_mode ?? "-")} auth=${String(data.auth_enabled ?? "-")}`
    : "健康状态不可解析";
}

function syncDangerButtons(): void {
  const deleteEnabled = getInput("deleteConfirm").checked;
  const restoreEnabled = getInput("restoreConfirm").checked && value("restorePath").trim().length > 0;
  const deleteButton = getButton("deleteButton");
  deleteButton.disabled = !deleteEnabled;
  deleteButton.textContent = `删除 ${userId()} / ${domain()}`;
  getButton("restoreButton").disabled = !restoreEnabled;
}

function onClick(id: string, handler: () => void | Promise<void>): void {
  getButton(id).addEventListener("click", () => {
    void handler();
  });
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
  return Number(getInput(id).value);
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

function getFrame(id: string): HTMLIFrameElement {
  const element = document.getElementById(id);
  if (element instanceof HTMLIFrameElement) {
    return element;
  }
  throw new Error(`Frame not found: ${id}`);
}

function isRecord(valueToCheck: unknown): valueToCheck is Record<string, unknown> {
  return typeof valueToCheck === "object" && valueToCheck !== null && !Array.isArray(valueToCheck);
}
