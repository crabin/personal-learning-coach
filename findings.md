# Personal Learning Coach Findings

更新日期：2026-04-28
范围：基于当前仓库实现与项目文档对照所得出的事实性发现。

## 1. 实现覆盖度高于“骨架阶段”

当前仓库并不是空壳，已经包含下列核心模块：

- 数据层：`models.py`、`data_store.py`、`migrations.py`
- 学习初始化：`level_tester.py`、`coach.py`
- 计划生成：`plan_generator.py`
- 推送链路：`content_pusher.py`、`scheduler_adapter.py`、`delivery/local.py`
- 评估与推进：`evaluator.py`、`mastery_engine.py`
- 复习与总结：`review_engine.py`、`report_generator.py`
- 服务接口：`api/main.py` + `domains/submissions/reports/schedules` routes
- 测试：共 60 个测试，目前已全量通过

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
- 阶段 4 每日推送：具备选择、生成、持久化、local delivery、scheduler 雏形，且已补齐核心 push 元数据字段
- 阶段 6 复习与回顾：已实现 1/3/7/14/30 天基础间隔，但未与推送主流程完整融合
- 阶段 7 报告：已可生成 HTML 报告，但“趋势图、强弱项、常错点、阶段/结业报告”仍不足

### 3.3 仍明显缺失的部分

- 最终综测 / 结业判断
- 在线资源增强
- 真实消息渠道（如 Telegram）
- 认证、监控、备份、README、CI

## 4. 与需求规格说明书的关键差距

### 4.1 模型字段状态

已补齐的字段：

- enrollment / domain：`target_level`、`current_level`、`daily_minutes`、`learning_style`、`delivery_time`、`language`、`allow_online_resources`、`schedule_config`
- assessment：`confidence`、`strengths`、`weaknesses`、`structured_scores`、`recommended_plan_style`
- push：`push_type`、`resource_snapshot`、`delivery_channel`、`delivery_result`
- submission：`practice_result`、`normalized_answer`、`parsing_notes`

仍未完成或未完全对齐的点：

- 更复杂的长期运行策略还未建立，例如最终综测、资源增强、真实投递
- CLI/API 虽已支持最小配置，但还没有更完整的管理工作流与帮助文档

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

- `pytest -q`：`67 passed`
- 覆盖率：`93%`
- Phase 2 本轮新增契约测试已通过：
  - `tests/test_models.py`
  - `tests/test_api.py`
  - `tests/test_coach.py`

### 已解决问题

1. `pytest -q` 默认导入失败
2. `content_pusher.py` 残留旧接口调用
3. 测试 mock 与运行时代码响应结构不一致

结论：Phase 1 的主干阻塞已经解除，当前优先级应转向需求规格中的字段补全与流程完整性。

## 6. 仓库状态补充

- 当前工作区不是干净状态
- 已修改但未提交文件包括：
  - `AGENTS.md`
  - `src/personal_learning_coach/content_pusher.py`
  - `src/personal_learning_coach/evaluator.py`
  - `src/personal_learning_coach/level_tester.py`
  - `src/personal_learning_coach/models.py`
  - `src/personal_learning_coach/plan_generator.py`
  - `src/personal_learning_coach/api/routes/domains.py`
  - `src/personal_learning_coach/api/routes/submissions.py`
  - `tests/conftest.py`
  - `tests/test_api.py`
  - `tests/test_models.py`
- 未跟踪文件包括：
  - `.omc/`
  - `src/personal_learning_coach/llm_client.py`

结论：后续修复应基于现有改动继续推进，避免误回滚用户正在进行的迁移工作。
