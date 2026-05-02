# Personal Learning Coach Task Plan

更新日期：2026-04-28
目的：基于当前仓库实现，与 [`docs/personal_learning_coach_项目整体设计与需求规格说明书.md`](docs/personal_learning_coach_项目整体设计与需求规格说明书.md) 和 [`docs/personal_learning_coach_项目实施计划.md`](docs/personal_learning_coach_项目实施计划.md) 做差异对照，形成可执行的项目推进路线。

## 当前结论

项目已经完成了“单用户、本地文件存储、基础 API、学习闭环核心模块”的主体骨架，但还没有达到文档要求中的“稳定可运行闭环”。当前最主要的剩余问题已经从工程接线转向需求完整性：

1. Phase 1 已完成，`pytest -q` 与主干 LLM 调用已打通
2. Phase 2 已完成：关键字段、领域生命周期操作、API/CLI 最小配置输入输出都已补齐
3. 若按“需求规格说明书”验收，在线资源与更完整的长期运行能力仍未完成
4. Phase 3 已完成：复习优先、报告增强、final assessment 提交链路与中断恢复验证都已补齐

## 里程碑状态总览

| 里程碑 | 文档目标 | 当前状态 | 结论 |
|---|---|---|---|
| M0 | 需求冻结与工程骨架 | `docs/`、`pyproject.toml`、`src/`、`tests/` 已有；`README.md` 为空；未见 CI | 部分完成 |
| M1 | 数据模型与存储层 | `models.py`、`data_store.py`、`migrations.py`、对应测试已存在 | 基本完成 |
| M2 | 学习初始化与水平测试 | `level_tester.py`、`coach.py` 已有，但测试未通过，偏好收集未实现 | 部分完成 |
| M3 | 学习计划生成 | `plan_generator.py` 已有，topic progress 初始化已写，动态调整未实现 | 部分完成 |
| M4 | 每日推送闭环 | `content_pusher.py`、`scheduler_adapter.py`、`delivery/local.py` 已有；投递能力和稳定性不足 | 部分完成 |
| M5 | 提交评估闭环 | `submissions` API、`evaluator.py`、`mastery_engine.py` 已有 | 基本完成 |
| M6 | 复习与总结 | `review_engine.py`、`report_generator.py` 已有；总结与趋势数据较弱 | 部分完成 |
| M7 | 增强与工程化 | API 已有雏形；认证、监控、备份、资源增强、README/运维文档缺失 | 刚起步 |

## 阶段任务

### Phase 11: 学习报告 JSON 导出修复
状态：`complete`

目标：
- 修复前端“导出 JSON”按钮点击无效的问题
- 保证报告页可以把当前报告数据下载为本地 JSON 文件

验收标准：
- 报告页“导出 JSON”按钮已接入点击事件
- 已加载报告时可直接导出；未提前加载时会先拉取报告再导出
- 前端测试与构建通过

完成情况：
- 已为报告页导出按钮补齐 `id` 和事件绑定
- 已新增 `reportExport.ts`，统一负责导出文件名与 JSON 序列化
- 已缓存当前报告数据，避免重复请求；无缓存时会自动拉取后再导出
- 已补充前端测试覆盖文件名与序列化行为
- 已完成验证：`npm test -- --run` 34 passed，`npm run build` 通过

### Phase 10: 用户认证、角色权限与管理员系统管理
状态：`complete`

目标：
- 补齐注册、登录、退出和 Bearer token 会话
- 区分普通用户与管理员，普通用户只能访问自己的学习数据
- 管理员可访问开发控制台、系统管理页和全部用户/领域/进度管理能力

验收标准：
- `/auth/register`、`/auth/login`、`/auth/logout`、`/auth/me` 可用
- 学习业务接口必须登录，普通用户跨用户访问返回 403
- `/admin/*` 支持管理员 Bearer token，并兼容旧 `x-api-key`
- 前端未登录显示登录/注册页，普通用户隐藏管理页和开发控制台，管理员显示系统管理页
- 后端测试、ruff、mypy、前端测试与构建通过

完成情况：
- 已新增 `UserRole`、`AuthSession`、密码哈希、会话签发/撤销、环境变量种子管理员配置
- 已新增 auth 路由并接入 FastAPI app
- 已给 domains、reports、schedules、submissions 路由加当前用户鉴权和用户范围校验
- 已修复提交答案时 `body.user_id` 与 `push.user_id` 不一致的越权风险
- 已扩展 admin 路由：用户列表、角色/启停更新、用户领域查看、归档、重置进度、删除领域
- 已扩展前端 ApiClient Bearer token、登录/注册/退出 UI、角色控制导航与系统管理页面
- 已补充后端 auth/权限/管理员测试和前端 token 注入测试
- 已完成验证：`uv run pytest -q` 120 passed，`uv run ruff check .` 通过，`uv run mypy src` 通过，`npm test -- --run` 22 passed，`npm run build` 通过

### Phase 9: 提交评估进度同步标记
状态：`complete`

目标：
- 每次提交答案完成评价后，明确记录该评价是否已经应用到学习进度
- 正常提交链路立即更新 topic progress
- 如果历史数据或中断导致评价未应用，刷新学习报告时自动补偿同步

验收标准：
- `EvaluationRecord` 有 `progress_applied` flag，默认未应用
- `apply_evaluation(...)` 成功更新 topic progress 后会把 flag 标为已应用
- 生成/刷新报告前会同步未应用的 evaluation
- 同步后 Topic Details 展示最新 status、mastery score、attempts/avg score
- 后端测试、ruff、mypy 通过

完成情况：
- 已为 `EvaluationRecord` 增加 `progress_applied`，默认 `False`
- 已让 `apply_evaluation(...)` 先持久化评价，再计算并更新 topic progress，最后标记 `progress_applied=True`
- 已新增 `sync_unapplied_evaluations(...)`，用于补偿同步历史或中断状态下未应用的评价
- 已在 `generate_report(...)` 开始时自动同步未应用评价，报告刷新会修复学习进度
- 已补充测试覆盖提交即更新、报告刷新补偿同步、flag 默认值
- 已完成验证：`uv run pytest -q` 106 passed，`uv run ruff check .` 通过，`uv run mypy src` 通过

补充修复：
- 已修复报告总是选择最新 plan 的问题：现在会优先选择包含提交、评价、推送或非初始进度活动的学习计划
- 你的当前数据中，报告会展示已有提交记录的 12-topic 计划，而不是后生成但没有学习活动的 10-topic 空计划
- 已完成验证：`uv run pytest -q` 107 passed，`uv run ruff check .` 通过，`uv run mypy src` 通过

### Phase 8: 结构化动态学习报告
状态：`complete`

目标：
- 后端报告 API 返回结构化学习进度数据，而不是预渲染 HTML
- 前端学习报告页直接渲染报告 UI，Topic Details 随提交评估后的最新 topic progress / evaluation 更新
- 点击“学习报告”标签时自动加载报告和领域状态，不再需要手动点击“生成报告预览/同步领域状态”

验收标准：
- `/reports/{domain}` 返回 JSON，包含 summary、topic_rows、recent_evals、insights 和 enrollment_status
- 前端报告页不再使用 iframe/srcdoc 渲染后端 HTML
- 切换到报告页会自动请求报告与领域状态
- 提交答案成功后，如果在报告页或随后进入报告页，能看到最新学习进度
- 后端测试、前端测试、构建与类型检查通过

完成情况：
- 已新增 `generate_report_payload(...)`，将报告转换成可 JSON 序列化的结构化数据
- 已将 `/reports/{domain}` 从 HTMLResponse 改为 JSON API
- 已新增前端 `reportView.ts`，由前端渲染 Summary、Topic Details、Learning Insights 和 Recent Evaluations
- 已移除报告页 iframe/srcdoc 主路径，改为 `reportContent` 动态渲染
- 已让切换到“学习报告”标签时自动同步报告与领域状态，保留刷新按钮作为手动补偿
- 已完成验证：`uv run pytest -q` 105 passed，`uv run ruff check .` 通过，`uv run mypy src` 通过，`npm test -- --run` 13 passed，`npm run build` 通过

### Phase 7: 历史感知的题目生成
状态：`complete`

目标：
- 点击生成题目时，先读取该用户在该领域的历史答题、题目评价、整体评价和学习进度
- 将历史上下文和当前学习阶段一起交给 LLM，让下一次推送生成补充题或下一阶段题
- 保留生成时使用的上下文摘要，便于排查为什么生成了这些题目

验收标准：
- `push_today` 生成新题时会把 evaluation、submission、assessment、topic progress 和 enrollment 信息纳入 prompt
- review due 场景会显式要求补弱；正常 ready 场景会根据掌握情况推进下一阶段
- 推送记录的 `content_snapshot` 包含本次生成所用的学习上下文摘要
- 定向测试与全量测试通过

完成情况：
- 已在 `content_pusher.py` 中新增学习上下文构建，汇总 enrollment、当前 topic progress、整体 topic 状态、最近 submission、最近 evaluation 和 assessment
- 已将学习上下文格式化后注入 `CONTENT_GENERATION_PROMPT`
- 已把本次生成使用的 `learning_context` 保存进 `PushRecord.content_snapshot`
- 已补充测试验证 prompt 会包含历史评价、整体 baseline、missed concepts、当前 mastery 和目标水平
- 已完成验证：`uv run pytest -q` 105 passed，`uv run ruff check .` 通过，`uv run mypy src` 通过

### Phase 6: 前端学习流程落地页
状态：`complete`

目标：
- 将单页控制台拆成按学习创建逻辑组织的前端落地页
- 覆盖学习目标创建、问题查看与回答、学习报告展示、管理与运维
- 保留 API 请求调试视图，方便开发和运营排查

完成情况：
- 已将 `src/web/main.ts` 改为四页签工作台：学习目标、问题回答、学习报告、管理运维
- 已重做 `src/web/styles.css`，补齐桌面与移动端响应式布局
- 已保留现有 API 操作：enroll、status、trigger、submit、report、lifecycle、backup、events、alerts、restore、final assessment
- 已补齐提交答案后的回答质量评估组件，展示分数、下一步动作、评估 ID 和反馈文本
- 已通过浏览器自动化验证四个页面可切换，桌面与 390px 移动端布局可读
- 已验证 `npm run build` 与 `npm test` 通过

### Phase 5: SQLite 持久层迁移
状态：`complete`

目标：
- 将运行期结构化数据从 `data/*.json` 切换到 `data/personal_learning_coach.sqlite3`
- 保持现有 `data_store.<collection>.save/get/all/filter/delete` 调用方式兼容
- 将当前真实 JSON 数据导入 SQLite，保证 CLI/API/报告/推送主链路继续可用

任务：
1. 用测试定义 SQLite store、JSON 导入、备份恢复的目标行为
2. 将 `data_store.py` 改为基于标准库 `sqlite3` 的持久层
3. 扩展 `migrations.py`，支持 schema 初始化与 JSON collection 幂等导入
4. 更新 `backup_service.py`、admin API 和 CLI 文案，从 JSON 文件备份切换到 SQLite 数据库备份
5. 更新 README 和相关测试，执行真实 `data/*.json` 到 `data/personal_learning_coach.sqlite3` 的迁移

验收标准：
- `uv run pytest` 全量通过
- 临时 `DATA_DIR` 下会自动创建 SQLite 数据库文件
- 旧 JSON collection 可重复导入且不产生重复记录
- `/admin/backup`、`/admin/restore` 和 `coach backup/restore` 操作 SQLite 数据库
- 当前真实数据可在 SQLite store 中通过现有接口读取

完成情况：
- 已将 `data_store.py` 切换为 SQLite 后端，保留原 store 公共接口与旧 `*.json` 构造参数兼容
- 已新增 schema 初始化、collection 表、常用字段索引和 `payload_json` 兜底存储
- 已扩展 `migrations.py`，支持旧 JSON collection 幂等导入 SQLite
- 已将备份/恢复切换为复制 `personal_learning_coach.sqlite3`
- 已执行真实数据迁移，生成 `data/personal_learning_coach.sqlite3`
- 已验证 `uv run pytest -q`、`uv run ruff check .`、`uv run mypy src` 全部通过

### Phase 1: 打通当前主干闭环
状态：`complete`

目标：
- 让默认开发环境下的测试、导入、LLM 客户端约定恢复一致
- 将“评估 -> 计划 -> 推送 -> 提交 -> 报告”闭环变为可验证状态

任务：
1. 修复 `pytest -q` 默认导入失败问题
2. 将 `level_tester.py`、`plan_generator.py`、`content_pusher.py`、`evaluator.py` 的主干调用统一到共享 `llm_client.py`
3. 修复 `content_pusher.py` 中残留的旧接口引用
4. 让测试 mock 与运行时代码通过共享响应解析兼容
5. 重新跑全量测试并记录结果

验收标准：
- `pytest -q` 无需手工加 `PYTHONPATH=src`
- 当前 60 个测试全部通过
- CLI/API 基础闭环可以在本地跑通

完成情况：
- 已在 `tests/conftest.py` 中补齐 `src/` 导入路径
- 已在 `src/personal_learning_coach/llm_client.py` 中增加统一文本生成与响应解析辅助函数
- 已修复 `content_pusher.py` 的旧 `Anthropic` 风格残留调用
- 已将 `level_tester.py`、`plan_generator.py`、`content_pusher.py`、`evaluator.py` 改为复用共享 LLM 调用层
- 已验证 `pytest -q` 结果为 `60 passed`

### Phase 2: 补齐需求文档中的核心缺口
状态：`complete`

目标：
- 从“模块存在”推进到“需求字段和流程完整”

任务：
1. 为 assessment 增加结构化结果字段：`confidence`、`strengths`、`weaknesses`、`recommended_plan_style`
2. 为 enrollment / preferences 增加：`daily_minutes`、`learning_style`、`delivery_time`、`target_level`、`language`、`allow_online_resources`
3. 为 push record 增加：`push_type`、`resource_snapshot`、`delivery_channel`、`delivery_result`
4. 为 submission record 增加：`normalized_answer`、`practice_result`、`parsing_notes`
5. 明确 domain 生命周期操作：暂停、恢复、归档、删除

验收标准：
- 关键模型字段与规格说明书保持一致
- API/CLI 至少支持最小配置项传入与读取

本轮完成：
- 已为 `AssessmentRecord` 增加 `confidence`、`strengths`、`weaknesses`、`structured_scores`、`recommended_plan_style`
- 已为 `DomainEnrollment` 增加学习偏好与投递配置字段，并在 `plan_generator.py` 写入持久化
- 已为 `PushRecord` 增加 `push_type`、`resource_snapshot`、`delivery_channel`、`delivery_result`
- 已为 `SubmissionRecord` 增加 `normalized_answer`、`practice_result`、`parsing_notes`
- 已扩展 `/domains/{domain}/enroll` 与 `/submissions` 接口以接受/返回这些核心字段

剩余：
- 无。Phase 2 验收项已完成。

### Phase 3: 完善复习、报告和最终结业
状态：`complete`

目标：
- 提升“长期教学闭环”完整度

任务：
1. 在每日推送中显式插入 review due 逻辑，而不只是状态记录
2. 增强报告：趋势、强弱项、常错点、阶段总结文本
3. 实现 final assessment 触发规则和结业判断
4. 增加中断恢复场景验证

验收标准：
- 低分话题可以进入复习并重新回到主线
- 报告能展示趋势和阶段总结
- 达标用户可被标记完成

本轮完成：
- 已让 `review due` 任务在 `content_pusher.py` 中优先于新课推送
- 已将“全话题掌握后”的领域状态从直接 `COMPLETED` 调整为 `FINAL_ASSESSMENT_DUE`
- 已在 `mastery_engine.py` 中加入 `complete_final_assessment(...)`，支持通过/未通过后的状态流转
- 已增强 `report_generator.py`，补充分数趋势、强弱项、常错点、final assessment readiness 与阶段总结文本
- 已新增并通过相关测试：`tests/test_content_pusher.py`、`tests/test_evaluator.py`、`tests/test_report_generator.py`

剩余：
- 无。Phase 3 当前验收项已完成。

### Phase 4: 工程化与集成
状态：`complete`

目标：
- 让项目具备可交付、可维护、可部署条件

任务：
1. 完成 `README.md`
2. 补充 CI、lint、type check、测试说明
3. 增加认证、配置校验、日志规范、错误监控
4. 增加 Telegram 或其他真实投递适配器
5. 引入在线资源增强与失败降级

验收标准：
- 新开发者可按 README 在本地启动
- 核心质量检查可自动执行
- 至少有一个真实消息渠道可用

本轮完成：
- 已新增 `src/personal_learning_coach/online_resource.py`，提供可注入的在线资源抓取服务
- 已实现资源去重、内存缓存、抓取失败降级三项主能力
- 已将在线资源推荐接入 `content_pusher.py`，并写入 `PushRecord.resource_snapshot`
- 已尊重 enrollment 中的 `allow_online_resources` 偏好；未显式启用时默认不联网
- 已让 `delivery/base.py` 在推送内容中渲染推荐资源区块
- 已补充并通过资源增强相关测试
- 已新增 `src/personal_learning_coach/delivery/telegram.py`，支持 Telegram Bot API 真实投递
- 已让 `content_pusher.py` 支持 `DELIVERY_MODE=telegram`
- 已补齐“投递失败也保留 PushRecord”的错误记录行为
- 已补充并通过 Telegram 投递与失败记录相关测试
- 已补齐 `README.md`，覆盖环境变量、CLI/API 启动、质量检查和已知限制
- 已新增 `.github/workflows/ci.yml`，自动执行 `ruff check .` 和 `pytest -q`
- 已将依赖与环境变量模板对齐到当前 OpenAI 主干实现
- 已清理当前 `ruff` 问题并验证通过
- 已清理当前 `mypy` 严格模式问题并验证 `mypy src` 通过
- 已将 CI 升级为自动执行 `ruff check .`、`mypy src`、`pytest -q`
- 已新增 `src/personal_learning_coach/config.py`，统一加载与校验运行配置
- 已新增 `src/personal_learning_coach/security.py`，支持 `API_AUTH_TOKEN` 驱动的简易 API Key 认证
- 已新增 `src/personal_learning_coach/backup_service.py` 与 `/admin/backup` 路由，支持 JSON 数据备份
- 已为 CLI 增加 `backup` 命令
- 已增强 `/health`，返回 `delivery_mode`、`auth_enabled`、`backup_dir` 与配置问题列表
- 已补充并通过配置校验、认证与备份测试
- 已新增 `src/personal_learning_coach/monitoring.py`，提供 runtime event 记录与日志配置
- 已新增 `/admin/runtime-events`，可读取最近运行事件
- 已将认证失败与备份成功接入 runtime event 记录
- 已将 API/CLI 日志接到 `DATA_DIR/logs/app.log`
- 已新增 `/admin/alerts`，提供基于 runtime event 的轻量告警视图
- 已新增 `restore_backup(...)`、`/admin/restore` 与 `coach restore`
- 已支持 `ADMIN_READ_TOKEN` / `ADMIN_WRITE_TOKEN` 读写分离
- 已补充未处理异常记录测试、告警测试与备份恢复演练测试
- 已完成全量验证：`ruff check .`、`mypy src`、`pytest -q`

剩余：
- 无。Phase 4 当前验收项已完成。

### Phase 11: README 前端优先化与 GitHub 同步
状态：`in_progress`

目标：
- 将 README 调整为以前端 Web 使用为主的项目介绍和上手路径
- 明确登录/注册、学习流程、管理员运维和前后端联调方式
- 将 README 改动单独提交并推送到用户提供的 GitHub 仓库

验收标准：
- README 首页优先展示 Web 界面启动与使用
- 保留后端 API、CLI、鉴权、环境变量和开发检查说明
- 提交时只包含本次 README 相关改动，不带入其他未提交文件

### Phase 12: QQ 邮箱验证码注册
状态：`complete`

目标：
- 注册流程改为图片验证码、QQ 邮箱验证码、后端校验后创建账号并自动登录
- 使用 QQ 个人邮箱 SMTP 配置发送验证码邮件
- 防止旧 `/auth/register` 直接绕过邮箱验证

验收标准：
- `/auth/register/captcha`、`/auth/register/start`、`/auth/register/complete` 可用
- SMTP 未配置时明确返回服务不可用
- 验证码错误、过期或超过尝试次数时注册失败
- 邮箱验证码通过后创建普通用户并返回 Bearer token
- 前端注册 UI 支持图片验证码、发送邮件验证码、完成注册并登录
- 后端测试、ruff、mypy、前端测试与构建通过

完成情况：
- 已新增图片验证码、邮箱验证码 challenge 模型与 SQLite store
- 已新增注册验证码工具和 QQ SMTP 邮件发送 helper
- 已将旧 `/auth/register` 改为 `410 Gone`，防止绕过邮箱验证
- 已新增 `/auth/register/captcha`、`/auth/register/start`、`/auth/register/complete`
- 已改造前端注册面板，支持刷新图片验证码、发送邮箱验证码、完成注册并自动登录
- 已补充 QQ 邮箱 SMTP 环境变量模板与 README 说明
- 已完成验证：`uv run pytest -q` 126 passed，`uv run ruff check .` 通过，`uv run mypy src` 通过，`npm test -- --run` 29 passed，`npm run build` 通过

## 决策记录

1. 当前项目适合按“先修通主干，再补字段和增强能力”的顺序推进，而不是继续平铺新模块。
2. 现阶段判断：M1、M5 最接近完成；M2、M3、M4、M6 均已进入实现但未收口；M7 仍需明显补强。
3. 当前已有未提交改动，后续修复阶段需要谨慎处理 `src/personal_learning_coach/content_pusher.py`、`src/personal_learning_coach/level_tester.py`、`src/personal_learning_coach/plan_generator.py`、`src/personal_learning_coach/llm_client.py`。

## 风险与阻塞

| 风险/阻塞 | 影响 | 建议 |
|---|---|---|
| 默认测试导入失败 | 开发体验差，CI 无法稳定搭建 | 先修 `pyproject` / pytest import path |
| LLM SDK 双栈混用 | 核心流程不可预测，测试失真 | 统一到单一 provider 抽象 |
| README 为空 | 难以交接和复现 | 在工程化阶段优先补齐 |
| 数据层缺少原子写入/备份 | 与实施计划不一致 | 在 M1 收尾阶段补上 |
| README/CI 仍缺失 | 影响交付与新成员接入 | 下一步优先补工程化文档与质量检查 |
| 更细粒度的权限模型仍未实现 | 未来多角色场景扩展受限 | 进入后续增强阶段时再拆分 |

## 错误记录

| 错误 | 观察 | 结论 |
|---|---|---|
| `pytest -q` 导入失败 | 报 `ModuleNotFoundError: personal_learning_coach` | 默认测试入口未配置完成 |
| `PYTHONPATH=src pytest -q` 失败 9 项 | 51 通过，9 失败，覆盖率 88% | 已作为 Phase 1 输入问题修复 |
| `content_pusher.py` 报 `NameError: MODEL` | 文件内仍保留旧 Anthropic 风格调用 | LLM 迁移未完成 |
| `MagicMock` 响应解析误判 | `hasattr()` 在 mock 上过于宽松 | 通过调整共享解析优先级解决 |
