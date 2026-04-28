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
