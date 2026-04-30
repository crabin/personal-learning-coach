# Personal Learning Coach Progress

更新日期：2026-04-28

## 当前项目状态

整体状态：`green`

判断依据：
- 核心模块覆盖较全，说明项目已经越过“纯设计/纯脚手架”阶段
- 默认测试入口已打通，LLM 主干调用已统一，核心开发闭环可验证
- 但按需求规格说明书衡量，更完整的工程化交付仍未完成

## 里程碑进度

| 模块 | 进度 | 说明 |
|---|---|---|
| 工程骨架 | 100% | 目录、依赖、测试、导入入口、README、CI、类型检查、运行配置与基础日志已可用 |
| 数据模型与持久化 | 92% | 基本模型、JSON store、备份与恢复能力可用，原子写入未完成 |
| 水平测试 | 82% | 主流程与测试已打通，并补齐 assessment 结构化字段 |
| 学习计划生成 | 84% | 计划、偏好持久化与 CLI 参数已打通，动态调整未完成 |
| 每日推送 | 94% | 选择、生成、投递、调度骨架已可用，并支持 review due、interruption recovery、资源推荐与 Telegram 投递 |
| 提交评估 | 86% | 提交、评估、mastery 更新已形成闭环，并补齐 submission 扩展字段 |
| 领域生命周期 | 82% | 暂停、恢复、归档、删除已在 API/CLI 打通 |
| 复习机制 | 82% | 间隔复习存在，已优先处理 review due，并覆盖中断恢复提醒 |
| 报告生成 | 82% | HTML 报告已补充趋势、强弱项、常错点和阶段总结 |
| 最终综测/结业 | 72% | readiness 状态、API/CLI 提交入口和完成/失败流转已打通 |
| 在线资源增强 | 72% | 已实现 fetcher、缓存、去重、失败降级和推送资源块接入，尚未做独立缓存层与更丰富来源 |
| 真实投递渠道 | 82% | Telegram adapter 已接入，失败记录可落库，并有 README 说明；主动告警仍未对接 |
| API/服务化 | 88% | FastAPI 已有基础接口、健康检查、读写分离 admin token、备份/恢复/事件/告警入口 |
| 运行保障 | 92% | 已有配置校验、读写分离 token、备份恢复、runtime event、日志和轻量告警 |

## 本次梳理记录

### Session 2026-04-28

已完成：
- 读取 `CLAUDE.md`、`AGENTS.md`、实施计划、需求规格说明书
- 盘点仓库代码结构与测试分布
- 验证当前测试状态
- 识别主干风险：默认导入失败、LLM SDK 双栈混用、README 缺失
- 创建项目级进度文件：`task_plan.md`、`findings.md`、`progress.md`
- 修复 `tests/conftest.py` 导入路径，使默认 `pytest -q` 可运行
- 在 `llm_client.py` 中增加共享文本生成与响应解析
- 将 `level_tester.py`、`plan_generator.py`、`content_pusher.py`、`evaluator.py` 统一到共享 LLM 调用层
- 修复 `MagicMock` 响应解析顺序问题
- 回归验证全量测试通过
- 补齐 `AssessmentRecord`、`DomainEnrollment`、`PushRecord`、`SubmissionRecord` 的第一批规格字段
- 扩展 `/domains/{domain}/enroll` 与 `/submissions` 的请求/响应契约
- 回归验证字段补齐后的全量测试仍通过
- 新增 domain 生命周期 API：暂停、恢复、归档、删除
- 为 CLI 增加 plan 偏好参数与 `pause` / `resume` / `archive` / `delete-domain` 命令
- 回归验证生命周期与 CLI 改动后的全量测试仍通过
- 让 `review due` 任务在推送选择中优先
- 将全话题掌握后的状态调整为 `FINAL_ASSESSMENT_DUE`
- 在报告中加入趋势、强弱项、常错点、final assessment readiness 和阶段总结
- 回归验证 Phase 3 本轮改动后的全量测试通过
- 新增 final assessment 的 API 提交入口与 CLI 命令
- 为 final assessment 增加最小持久化记录与状态校验
- 回归验证 final assessment 链路接入后的全量测试通过
- 为未完成已推送任务增加 `interruption_recovery` 重发逻辑
- 暂停域不再触发推送；提交成功后领域状态从 `AWAITING_SUBMISSION` 恢复为 `ACTIVE`
- 回归验证 interruption recovery 场景接入后的全量测试通过
- 新增 `online_resource.py`，提供资源抓取、去重、缓存和失败降级
- 将资源推荐接入 `content_pusher.py`，并写入 `PushRecord.resource_snapshot`
- 让本地投递格式渲染推荐资源区块
- 回归验证在线资源增强接入后的全量测试通过
- 新增 `delivery/telegram.py`，提供 Telegram Bot API 真实投递能力
- 让 `content_pusher.py` 支持 `DELIVERY_MODE=telegram`
- 为投递失败场景补齐 `PushRecord.delivery_result` 持久化
- 回归验证 Telegram 投递接入后的全量测试通过
- 补齐 `README.md`，覆盖环境变量、CLI、API、Telegram、质量检查
- 新增 GitHub Actions CI，执行 `ruff check .` 和 `pytest -q`
- 将 `.env.example` 与 `pyproject.toml` 对齐到 OpenAI 主干
- 清理现有 `ruff` 问题并验证通过
- 清理当前 `mypy` 严格模式问题并验证 `mypy src` 通过
- 将 CI 升级为执行 `ruff check .`、`mypy src`、`pytest -q`
- 新增 `config.py`，统一配置加载与运行校验
- 新增 `security.py`，支持 `API_AUTH_TOKEN` 控制的 admin 路由认证
- 新增 `backup_service.py`、`/admin/backup` 和 `coach backup`
- 增强 `/health` 返回运行配置状态与问题列表
- 新增 `monitoring.py`，记录 runtime event 并输出 JSON 日志
- 新增 `/admin/runtime-events`，可查看认证失败和备份事件
- 新增 `/admin/alerts`，提供轻量错误与认证告警视图
- 新增 `/admin/restore` 与 `coach restore`，完成备份恢复闭环
- 新增 admin 读写 token 分离能力
- 补充未处理异常记录测试、告警测试与恢复演练测试

### Session 2026-04-28 SQLite migration

已完成：
- 读取现有 planning 文件并追加 Phase 5
- 确认当前工作区存在与本任务无关的未提交改动，将限制修改范围
- 已确认 SQLite 迁移采用标准库 `sqlite3`，目标数据库路径为 `DATA_DIR/personal_learning_coach.sqlite3`
- 已用测试锁定 SQLite store 自动建库、兼容旧 `_Store("*.json")` 构造、JSON 导入幂等、SQLite 备份文件创建
- 已将 `data_store.py` 改为 SQLite-backed store
- 已扩展 `migrations.py`，支持 JSON collection 导入 SQLite
- 已将 `backup_service.py`、admin route、CLI help 和 README 文案切换到 SQLite
- 已执行真实迁移，当前 SQLite 数据库包含：2 enrollment、3 plan、33 topic progress、8 push、2 submission、2 evaluation、2 runtime event
- 已完成验证：`uv run pytest -q` 104 passed，`uv run ruff check .` 通过，`uv run mypy src` 通过

### Session 2026-04-30 frontend learning pages

已完成：
- 使用 Huashu-Design 的高保真原型思路，把单一控制台拆成四个按学习流程组织的页面
- 新增学习目标创建页，集中处理报名、目标水平、每日时间、学习风格、推送时间和在线资源偏好
- 新增问题查看与回答页，独立展示理论、基础题、实践题、复盘题和提交侧栏
- 新增学习报告页，保留 HTML 报告 iframe 预览和状态同步入口
- 新增管理与运维页，集中放置生命周期、备份、事件、告警、恢复、删除和结业评估
- 新增提交答案后的回答质量评估组件，可展示 overall score、next action、evaluation id 与反馈正文
- 新增 `evaluationView.ts` 和对应单元测试，覆盖分数格式、视觉状态、下一步动作文案和空反馈兜底
- 已做桌面与 390px 移动端浏览器验证，四个页面切换正常，标签高亮使用 `aria-selected` 驱动
- 已用浏览器模拟 `/submissions` 响应，确认评估组件能在提交后刷新
- 已完成验证：`npm run build` 通过，`npm test` 10 passed

### Session 2026-04-30 adaptive question generation

已完成：
- 读取 `CLAUDE.md`、`task_plan.md`、`findings.md`、`progress.md` 和当前推送/评估/模型代码
- 确认当前题目生成 prompt 只使用领域、主题、描述和水平，未加载历史答题与整体评价
- 在 `task_plan.md` 中新增 Phase 7，并记录本轮发现
- 用测试定义生成题目时应携带历史学习上下文
- 新增学习上下文构建逻辑，汇总 enrollment、topic progress、submission、evaluation、assessment 和整体进度
- 将学习上下文接入 LLM 题目生成 prompt，并写入 `PushRecord.content_snapshot.learning_context`
- 完成代码审查：未发现阻断问题；保持现有 API 返回结构兼容

错误记录：
- 定向测试首次运行按预期失败：`Learning history context` 未出现在 LLM prompt 中，证明当前生成路径未加载历史上下文。
- 未重复失败动作；实现上下文注入后同一测试通过。

验证：
- `uv run pytest tests/test_content_pusher.py::test_push_today_generates_with_learning_history_context -q`：通过
- `uv run pytest tests/test_content_pusher.py tests/test_api.py -q`：41 passed
- `uv run pytest -q`：105 passed
- `uv run ruff check .`：通过
- `uv run mypy src`：通过

### Session 2026-04-30 structured report preview

已完成：
- 读取当前报告 API、报告生成器、前端 API client、前端主页面和样式
- 确认报告页当前用 iframe 渲染后端 HTML，并且需要手动点击报告与状态按钮
- 确认 Topic Details 数据本身来自最新 topic progress / evaluation，适合改成结构化 JSON 后由前端动态渲染
- 在 `task_plan.md` 中新增 Phase 8，并记录本轮发现
- 用测试定义 `/reports/{domain}` 返回结构化 JSON 的新契约
- 新增 `generate_report_payload(...)` 并将 `/reports/{domain}` 改为 JSON API
- 新增前端 `reportView.ts` 和测试，由前端渲染 Topic Details、学习进度、洞察和最近评价
- 将报告页从 iframe/srcdoc 改为 `reportContent` 动态渲染
- 切换到“学习报告”标签时自动同步报告与领域状态，刷新按钮仅保留为手动补偿
- 本地验证 Vite 页面可访问，`/reports/ai_agent?user_id=u1` 返回 JSON

错误记录：
- 定向 API 测试首次按预期失败：`/reports/{domain}` 返回 `text/html`。改为结构化 JSON API 后通过。

验证：
- `uv run pytest tests/test_api.py::test_get_report -q`：通过
- `uv run pytest tests/test_api.py::test_get_report tests/test_report_generator.py -q`：7 passed
- `uv run pytest -q`：105 passed
- `uv run ruff check .`：通过
- `uv run mypy src`：通过
- `npm test -- --run`：13 passed
- `npm run build`：通过

### Session 2026-04-30 progress sync flag

已完成：
- 确认当前提交链路会调用 `apply_evaluation(...)`，但没有持久化记录“评价是否已应用到进度”
- 新增 `EvaluationRecord.progress_applied` flag，默认 `False`
- 修改 `apply_evaluation(...)`：先保存评价，再重新计算 mastery，更新 topic progress 后标记 `progress_applied=True`
- 新增 `sync_unapplied_evaluations(...)`，报告生成前自动补偿同步未应用评价
- 修改 `generate_report(...)`，刷新报告前先同步未应用评价
- 收紧提交 API 测试，验证提交后 topic progress 和 flag 都已更新
- 新增报告补偿同步测试，验证未应用评价会在刷新报告时更新 Topic Details

错误记录：
- 定向测试首次按预期失败：`EvaluationRecord` 没有 `progress_applied` 字段，报告刷新也不会应用未同步评价。
- 收紧提交测试后发现 `apply_evaluation(...)` 先计算 mastery 再保存 fake evaluation，导致本次分数未参与计算；已改为先保存评价再计算。

验证：
- `uv run pytest tests/test_api.py::test_submit_answer tests/test_report_generator.py::test_generate_report_payload_syncs_unapplied_evaluations tests/test_models.py::test_evaluation_record_weighted_score -q`：3 passed
- `uv run pytest -q`：106 passed
- `uv run ruff check .`：通过
- `uv run mypy src`：通过
关键证据：
- `pytest -q` 结果为：
  - 94 个测试通过
  - 覆盖率 92%
- `ruff check .` 结果为：
  - All checks passed
- `mypy src` 结果为：
  - Success: no issues found in 29 source files
- 定向测试均已恢复：
  - `tests/test_plan_generator.py`
  - `tests/test_content_pusher.py`
  - `tests/test_evaluator.py`
  - `tests/test_api.py`
  - `tests/test_models.py`
  - `tests/test_coach.py`
  - `tests/test_report_generator.py`

## 下一步建议

1. Phase 4 已完成，进入后续增强阶段。
2. 下一步优先补更丰富的在线资源来源与运行验证。
3. 然后补更细的部署、主动告警与运维文档。

## 备注

- 本次文档以“当前代码事实”为准，不假设未提交改动已经完成。
- 后续若代码继续演进，应在每次阶段收口后同步更新这三份文件。
