# Personal Learning Coach Findings

更新日期：2026-04-28
范围：基于当前仓库实现与项目文档对照所得出的事实性发现。

## 8. 历史感知题目生成发现

- `/schedules/trigger` 通过 `content_pusher.push_today(...)` 触发生成和投递。
- 当前 `generate_push_content(...)` 只把 `domain`、`topic_title`、`topic_description`、`level` 放进 prompt，因此同一 topic/level 下 prompt 基本固定。
- 可用于个性化的历史数据已经存在：`evaluation_records` 保存题目评价、分数、强弱项、missed concepts、next_action；`submission_records` 保存原始答案和实践结果；`assessment_records` 保存阶段/最终整体评价；`topic_progress` 保存 topic 状态、mastery、attempts；`domain_enrollments` 保存当前水平、目标水平和学习偏好。
- `PushRecord.content_snapshot` 已保存 LLM 返回内容，适合追加轻量的 `learning_context` 摘要用于追溯。

## 9. 报告预览与进度同步发现

- 当前 `/reports/{domain}` 直接返回 `HTMLResponse`，前端 `loadReport()` 以 text 读取后写入 iframe `srcdoc`。
- 前端报告页当前有两个手动按钮：`生成报告预览` 和 `同步领域状态`，切换到“学习报告”标签不会自动请求。
- `report_generator.generate_report(...)` 已经能生成结构化 dict，但其中 `topic_rows` 是 `_TopicRow` 对象、`recent_evals` 是 Pydantic 模型，尚未作为 API JSON 直接返回。
- Topic Details 的真实数据来自 `review_engine.generate_weekly_summary(...)`，会读取最新 `topic_progress` 和 `evaluation_records`；问题主要在 API/前端载荷与触发逻辑，而不是后端没有进度数据。

## 1. 实现覆盖度高于“骨架阶段”

当前仓库并不是空壳，已经包含下列核心模块：

- 数据层：`models.py`、`data_store.py`、`migrations.py`
- 学习初始化：`level_tester.py`、`coach.py`
- 计划生成：`plan_generator.py`
- 推送链路：`content_pusher.py`、`scheduler_adapter.py`、`delivery/local.py`
- 评估与推进：`evaluator.py`、`mastery_engine.py`
- 复习与总结：`review_engine.py`、`report_generator.py`
- 服务接口：`api/main.py` + `domains/submissions/reports/schedules` routes
- 测试：当前共 89 个测试，已全量通过
- 在线资源：`online_resource.py` 已接入推送主链路，并覆盖缓存、去重、失败降级
- 真实投递：`delivery/telegram.py` 已落地，并可通过 `DELIVERY_MODE=telegram` 启用

结论：项目已进入“功能收口与工程化修复阶段”，不是“从零设计阶段”。

## 2. 当前最大问题是接线不一致，不是模块缺失

### 2.1 测试与导入入口

- 直接运行 `pytest -q` 会在收集阶段失败
- 失败原因是默认导入路径未包含 `src`
- 这说明打包配置存在，但本地测试体验未闭环

### 2.2 LLM 客户端与 SDK 混用

- `level_tester.py` 使用 `OpenAI` `chat.completions.create(...)`
- `plan_generator.py` 使用 `OpenAI` `chat.completions.create(...)`
- `llm_client.py` 返回 `OpenAI` 客户端
- `evaluator.py` 仍使用 `anthropic.Anthropic`
- `content_pusher.py` 头部已改为 `OpenAI` / `get_client()` / `get_model()`，但函数内部仍调用 `anthropic.Anthropic` 风格的 `messages.create(...)`，且依赖未定义的 `MODEL` 与 `_client`

结论：项目正在从 Anthropic 风格迁移到 OpenAI 风格，但迁移尚未完成。

更新：

- 主干链路现已统一通过 `src/personal_learning_coach/llm_client.py` 调用
- 共享层兼容两类响应结构：
  - `chat.completions.create(...)`
  - `messages.create(...)`
- `evaluator.py` 也已切到共享 LLM 调用层

结论修正：主干调用抽象已统一，剩余差距主要转移到“需求字段与功能完整性”，而不再是 SDK 接线问题。

## 3. 与实施计划的对照结论

### 3.1 已基本满足的部分

- 阶段 1 数据模型与存储层：已有模型、存储、迁移和测试
- 阶段 5 提交与评估：已有 submission、evaluation、mastery update
- 阶段 10 API 基础接口：已有 start/enroll、submit、report、trigger、health

### 3.2 已实现但未验收收口的部分

- 阶段 2 水平测试：代码已通过测试，并新增 assessment 结构化字段，但完整引导式偏好采集仍未实现
- 阶段 3 计划生成：可生成 topics 和 topic progress，但动态调整能力未落地
- 阶段 4 每日推送：具备选择、生成、持久化、local delivery、scheduler 雏形，已补齐核心 push 元数据字段，并支持 `review due` 优先
- 阶段 6 复习与回顾：已实现 1/3/7/14/30 天基础间隔，并在中断场景下支持 `interruption_recovery` 唤醒提醒
- 阶段 7 报告：已可生成 HTML 报告，并已补充趋势、强弱项、常错点与阶段总结

### 3.3 仍明显缺失的部分

- 更完整的认证/授权模型
- 更细的部署与运维手册

## 4. 与需求规格说明书的关键差距

### 4.1 模型字段状态

已补齐的字段：

- enrollment / domain：`target_level`、`current_level`、`daily_minutes`、`learning_style`、`delivery_time`、`language`、`allow_online_resources`、`schedule_config`
- assessment：`confidence`、`strengths`、`weaknesses`、`structured_scores`、`recommended_plan_style`
- push：`push_type`、`resource_snapshot`、`delivery_channel`、`delivery_result`
- submission：`practice_result`、`normalized_answer`、`parsing_notes`

仍未完成或未完全对齐的点：

- 当前认证已支持 admin 读写分离 token，但还不是用户/角色级授权
- 当前告警仍是查询式轻量视图，还没有主动通知通道

### 4.2 流程完整性不足

- 需求要求“开始前提问与偏好收集”，当前 CLI/API 主要直接接收 `level` 或走测试，不含完整引导问答
- 需求要求“推送与对话分离”，当前结构方向正确，但调度/状态能力仍偏简化
- 需求要求“可解释推进逻辑”，当前 `mastery_engine.py` 主要以阈值驱动，解释信息仍主要依赖 LLM 文本

### 4.3 工程保障不足

- `README.md` 为空
- 未看到 CI 定义
- `data_store.py` 没有原子写入与备份策略
- `migrations.py` 只有框架，未见实际 migration 注册

## 5. 当前测试与质量信号

### 测试结果

- `pytest -q`：`94 passed`
- 覆盖率：`91%`
- 覆盖率：`92%`
- `ruff check .`：通过
- `mypy src`：通过
- Phase 2 本轮新增契约测试已通过：
  - `tests/test_models.py`
  - `tests/test_api.py`
  - `tests/test_coach.py`
- Phase 3 本轮新增行为测试已通过：
  - `tests/test_content_pusher.py`
  - `tests/test_evaluator.py`
  - `tests/test_report_generator.py`
  - `tests/test_api.py` 中 final assessment 场景
  - `tests/test_coach.py` 中 final assessment CLI 场景
  - `tests/test_content_pusher.py` 中 interruption recovery 场景
  - `tests/test_api.py` 中 AWAITING_SUBMISSION -> ACTIVE 恢复场景
- Phase 4 当前新增资源增强测试已通过：
  - `tests/test_models.py` 中资源缓存与去重场景
  - `tests/test_content_pusher.py` 中在线资源成功、关闭、失败降级场景
  - `tests/test_content_pusher.py` 中本地投递资源区块渲染场景
- Phase 4 当前新增真实投递测试已通过：
  - `tests/test_models.py` 中 Telegram 配置校验与请求发送场景
  - `tests/test_content_pusher.py` 中投递失败记录持久化场景
- Phase 4 当前新增工程化产物已落地：
  - `README.md`
  - `.github/workflows/ci.yml`
  - `.env.example` 与 `pyproject.toml` 已对齐 OpenAI 主干
  - `mypy` 严格模式已打通并可进入 CI
- Phase 4 当前新增运行保障能力已落地：
  - `config.py` 统一配置校验
  - `security.py` 简易 API Key 认证
  - `backup_service.py` 与 `/admin/backup`
  - `coach backup` CLI 入口
  - `monitoring.py`、`/admin/runtime-events` 与 JSON 日志文件
  - `/admin/alerts` 轻量告警视图
  - `/admin/restore` 与 `coach restore` 恢复入口
  - admin 读写 token 分离

### 已解决问题

1. `pytest -q` 默认导入失败
2. `content_pusher.py` 残留旧接口调用
3. 测试 mock 与运行时代码响应结构不一致

结论：Phase 4 已完成。主干阻塞、工程化交付、真实投递、资源增强、质量检查与基础运行保障都已落地；后续优先级应转向更高阶的授权、主动告警和运维手册增强。

## 6. 仓库状态补充

- 当前工作区不是干净状态
- 已修改但未提交文件包括：
  - `AGENTS.md`
  - `src/personal_learning_coach/content_pusher.py`
  - `src/personal_learning_coach/evaluator.py`
  - `src/personal_learning_coach/level_tester.py`
  - `src/personal_learning_coach/models.py`
  - `src/personal_learning_coach/plan_generator.py`
  - `src/personal_learning_coach/report_generator.py`
  - `src/personal_learning_coach/mastery_engine.py`
  - `src/personal_learning_coach/api/routes/domains.py`
  - `src/personal_learning_coach/api/routes/submissions.py`
  - `src/personal_learning_coach/coach.py`
  - `src/personal_learning_coach/content_pusher.py`
  - `tests/conftest.py`
  - `tests/test_api.py`
  - `tests/test_content_pusher.py`
  - `tests/test_evaluator.py`
  - `tests/test_coach.py`
  - `tests/test_models.py`
  - `tests/test_report_generator.py`
- 未跟踪文件包括：
  - `.omc/`
  - `src/personal_learning_coach/llm_client.py`
  - `src/personal_learning_coach/online_resource.py`
  - `src/personal_learning_coach/delivery/telegram.py`
  - `src/personal_learning_coach/config.py`
  - `src/personal_learning_coach/security.py`
  - `src/personal_learning_coach/backup_service.py`
  - `src/personal_learning_coach/api/routes/admin.py`

结论：后续修复应基于现有改动继续推进，避免误回滚用户正在进行的迁移工作。

## 7. SQLite 迁移发现

- 当前结构化持久层集中在 `src/personal_learning_coach/data_store.py`，业务层通过统一 store 单例访问，适合底层替换。
- 现有模型均为 Pydantic `BaseModel`，主键可沿用第一个 `*_id` 字段的规则。
- 当前真实 `data/*.json` collection 包含：domain enrollments、learning plans、topic progress、push records、submission records、evaluation records、runtime events；另有 `data/pushes/` Markdown 和 `data/logs/` 不属于结构化数据迁移范围。
- 项目当前未依赖 SQLAlchemy，使用标准库 `sqlite3` 能满足需求且改动面最小。
- 工作区已有与本任务无关的未提交业务/前端修改，本轮应避免回滚或格式化这些文件。

## 8. 用户认证与权限实现发现

- 当前应用原本只有 admin API key，普通学习接口通过请求里的 `user_id` 区分用户，缺少登录态和服务端用户范围校验。
- SQLite 通用 collection 表可直接承载 `AuthSession`，无需新增专用 SQL schema。
- `UserProfile` 已存在但只表达学习者资料；扩展 `password_hash`、`role`、`is_active` 可保持旧测试构造兼容。
- 管理接口需要兼容旧 `x-api-key` 测试和运维用法，同时前端切换到 Bearer token。
- 前端当前是单文件工作台，最小可行改法是在现有 shell 外增加 auth shell，并通过角色隐藏管理页与开发控制台。
