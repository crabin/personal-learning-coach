# Personal Learning Coach 项目整体设计与需求规格说明书

版本：v1.0
状态：可实施草案（已结合现有对话、已实现原型能力与后续独立项目化目标整理）
适用对象：产品设计者、架构师、后端工程师、前端工程师、LLM/Agent 工程师、测试工程师、运维工程师

## 1. 文档目的

本文档用于将“私人学习教练”能力从当前对话式能力/技能，设计为一个可独立实现、可长期运行、可维护、可扩展的正式项目。文档覆盖以下内容：

1. 项目背景与目标
2. 用户需求与业务边界
3. 核心功能设计
4. 系统架构设计
5. 数据模型与持久化设计
6. AI/评估/学习推进机制
7. 定时任务与推送机制
8. 风险与约束
9. 验收标准
10. 项目实施输入要求

本设计特别围绕我们已讨论过的能力范围整理，包括但不限于：
- 开始前提问与水平测试
- 学习计划生成
- 每日知识学习推送
- 实践任务与思考题
- 用户提交答案
- 知识回顾/复习
- 自动评估与反馈
- 总结与报告
- 阶段测试与最终综测
- 定时推送任务
- 全量学习数据持久化
- 在线资源增强

---

## 2. 项目背景

### 2.1 背景问题

通用聊天机器人可以回答问题，但不天然具备“长期教学闭环”能力。用户希望的是一个真正持续工作的“私人学习教练”：

- 能针对某一领域建立长期学习计划
- 能判断用户起点，而不是假设用户水平
- 能每日推送学习内容，而不是被动等待提问
- 能接收用户练习提交并做结构化评估
- 能依据学习表现动态推进或回退内容
- 能记录完整历史，而不是只保存最终分数
- 能生成阶段总结、复盘和可视化报告
- 能支持多学习领域并长期运行

### 2.2 已知用户目标

从历史对话和当前需求可归纳出以下明确目标：

1. 学习某个领域（例如 AI Agent）
2. 学习开始前先进行水平测试
3. 学习内容要理论与实践结合
4. 每天推送对应学习内容与问题
5. 用户提交后要评估回答质量并给反馈
6. 系统据此调整后续学习内容
7. 持续直到达到“掌握该领域”的目标
8. 生成可视化学习报告
9. 支持多领域学习
10. 学习数据、用户答案、模型评估都必须持久化
11. 结合最新在线资源增强学习内容
12. 支持定时任务自动推送

### 2.3 项目化目标

将该能力设计为一个正式项目，使其具备：
- 独立代码仓库
- 可配置的数据目录
- 可作为库/API/CLI/机器人服务运行
- 可与 Telegram 等消息平台集成
- 可由 cron/scheduler 自动驱动
- 可增量扩展学习领域模板、评估器和报告模块

---

## 3. 产品定位

### 3.1 产品定义

Personal Learning Coach 是一个面向个人长期学习的 AI 驱动教学系统。它不是单次问答工具，而是一个围绕“目标、计划、推送、练习、评估、复习、总结、掌握认证”构建的闭环学习系统。

### 3.2 产品形态

推荐支持四种使用形态：

1. SDK/Library
   - 供其他 Agent/应用内嵌调用
2. 服务端 API
   - 提供计划、推送、提交、评估、报告等接口
3. 后台任务系统
   - 负责每日推送、复习提醒、报告生成等异步任务
4. 管理端/用户端 UI
   - 用户查看学习进度、历史评估、报告

### 3.3 目标用户

1. 想系统化学习单个或多个知识领域的个人用户
2. 希望通过对话方式长期学习的人
3. 希望把学习流程自动化的人
4. 希望构建 AI 教学产品的开发者/研究者

### 3.4 非目标

以下不作为第一阶段目标：

1. 面向万人规模的公开教育平台
2. 完整 LMS（Learning Management System）替代品
3. 大规模教师协同平台
4. 高并发在线视频课堂系统
5. 企业级复杂权限教学平台

---

## 4. 核心设计原则

### 4.1 长期记忆优先
所有教学行为必须建立在历史学习上下文之上，而不是每次重新开始。

### 4.2 原始记录优先
不能只保存分数或结论，必须保存：
- 用户原始回答
- 模型反馈原文
- 结构化评分结果
- 评估上下文
- 每次推送的学习内容快照

### 4.3 可解释的推进逻辑
用户应能知道：
- 为什么今天学这个
- 为什么系统判断掌握不足
- 为什么需要复习或补学
- 为什么能进入下一阶段

### 4.4 领域可扩展
AI Agent 只是第一领域，项目应天然支持新增 Python、机器学习、系统设计等领域。

### 4.5 推送与对话分离
“推送生成”和“用户提交评估”应是可独立运行的两个流程，避免耦合在一次对话中。

### 4.6 兼容旧数据
数据结构升级时必须向后兼容，自动补齐缺失字段。

---

## 5. 项目范围

### 5.1 In Scope

1. 学习领域初始化
2. 水平测试/分级
3. 学习计划生成
4. 每日学习推送
5. 知识讲解内容生成/读取
6. 实践任务与思考题生成
7. 用户提交记录
8. 提交评估
9. 知识回顾/复习调度
10. 学习进度跟踪
11. 阶段总结
12. 综合测试
13. 学习报告生成
14. 定时任务调度
15. 在线学习资源推荐
16. 多领域并行学习
17. 全量持久化
18. 管理配置

### 5.2 Out of Scope（首版）

1. 多人协作班级管理
2. 教学直播
3. 视频作业自动批改
4. 外部考试平台深度对接
5. 社交化学习社区
6. 复杂付费系统

---

## 6. 业务流程总览

### 6.1 主闭环流程

1. 用户发起“开始学习某领域”
2. 系统检查是否已有该领域学习档案
3. 若无，则触发水平测试
4. 用户完成测试
5. 系统评估水平并询问/确定学习参数
6. 生成个性化学习计划
7. 创建每日推送任务
8. 到点推送当天学习内容
9. 用户提交答案/实践结果
10. 系统评估提交质量
11. 写入持久化记录
12. 更新掌握度与学习进度
13. 决定下一步：
   - 进入下一话题
   - 继续巩固当前话题
   - 插入复习任务
   - 阶段测试
14. 定期生成周报/月报/阶段报告
15. 达成掌握条件后进行综测
16. 综测通过后标记该领域学习目标达成

### 6.2 每日推送子流程

1. 触发定时任务
2. 读取用户领域学习档案
3. 判断当前状态：未开始/进行中/待复习/待综测/已完成
4. 选择今日任务类型：
   - 新知识推进
   - 巩固练习
   - 复习回顾
   - 阶段小测
5. 生成或读取对应内容
6. 补充在线资源
7. 记录本次推送快照
8. 将任务发送到消息渠道

### 6.3 用户提交评估子流程

1. 接收用户回答与实践结果
2. 匹配对应领域、话题、推送批次
3. 提取本次评估上下文
4. 运行评估器
5. 生成结构化评分 + 文本反馈
6. 写入 submission_history / evaluations
7. 更新 topic mastery / domain progress
8. 给出反馈与下一步建议

---

## 7. 功能需求详述

## 7.1 学习领域管理

### 7.1.1 功能目标
支持用户管理多个学习领域，每个领域独立建档、独立进度、独立报告。

### 7.1.2 功能点
1. 创建学习领域
2. 列出所有学习领域
3. 查看单领域状态
4. 暂停领域学习
5. 恢复领域学习
6. 删除领域学习档案（需确认）
7. 归档已完成领域

### 7.1.3 核心字段
- domain_id
- domain_name
- status
- created_at
- updated_at
- target_level
- current_level
- daily_minutes
- learning_style
- schedule_config

---

## 7.2 水平测试模块

### 7.2.1 目标
在学习开始前评估用户初始水平，避免内容过难或过浅。

### 7.2.2 功能点
1. 根据领域生成测试题
2. 支持分层题目（初级/中级/高级）
3. 支持主观题 + 简答题
4. 接收用户回答
5. 结构化评估回答
6. 输出初始水平结论
7. 将水平测试完整记录持久化

### 7.2.3 设计要求
- 题目数量可配置，默认 6 题
- 覆盖基础概念、应用理解、推理能力、实践经验
- 评估不只输出总分，还输出维度分
- 必须记录 raw_answers、llm_feedback、structured_scores
- 必须将每次测试写入 assessment_history

### 7.2.4 输出结果
- initial_level: beginner/intermediate/advanced
- confidence
- strengths
- weaknesses
- recommended_plan_style

---

## 7.3 学习偏好与约束收集模块

### 7.3.1 目标
收集影响学习计划生成的关键参数。

### 7.3.2 参数
- 每日可用学习时间（如 30/60/90 分钟）
- 学习风格（理论/实践/结合）
- 推送时间
- 目标掌握水平
- 偏好语言（中文）
- 是否允许联网查最新资源

### 7.3.3 默认值
若自动化任务无法交互确认，使用默认值：
- daily_minutes = 60
- learning_style = blended
- language = zh
- delivery_time = 09:00
- domain = ai_agent

---

## 7.4 学习计划生成模块

### 7.4.1 目标
根据用户水平和约束生成结构化学习路径。

### 7.4.2 功能点
1. 定义领域课程地图
2. 根据水平裁剪路径
3. 将课程拆分为模块/话题/日程
4. 为每个话题定义：
   - 学习目标
   - 关键概念
   - 预计时长
   - 先修关系
   - 理论内容模板
   - 实践任务模板
   - 思考题模板
   - 复习触发规则
5. 输出完整计划并持久化

### 7.4.3 计划模型建议
- DomainPlan
  - modules[]
  - topics[]
  - prerequisites[]
  - pacing_strategy
  - review_strategy
  - assessment_strategy

### 7.4.4 动态调整
计划并非一次生成后固定不变，应支持：
- 插入复习节点
- 调整难度
- 跳过已掌握话题
- 重新排序部分话题

---

## 7.5 每日学习内容推送模块

### 7.5.1 目标
定时生成并推送连续学习任务。

### 7.5.2 推送内容结构
每次推送至少包含：
1. 今日主题
2. 当前进度（模块/话题/完成度）
3. 本次学习目标
4. 理论学习内容
5. 实践任务
6. 思考题（2-3 个）
7. 推荐资源
8. 回复说明

### 7.5.3 推送类型
- 新课推进
- 复习巩固
- 阶段总结
- 阶段测验
- 综合测试
- 中断恢复提醒

### 7.5.4 推送持久化
每次推送都应保存：
- push_id
- generated_at
- domain
- topic_id
- push_type
- content_snapshot
- resource_snapshot
- delivery_channel
- delivery_result

---

## 7.6 用户提交与作业接收模块

### 7.6.1 目标
接收用户对学习任务的回应，并将其纳入学习闭环。

### 7.6.2 输入类型
1. 纯文字回答
2. 结构化答题
3. 实践结果描述
4. 多题答案组合
5. 未来可扩展附件/代码片段

### 7.6.3 记录要求
每次提交必须保存：
- submission_id
- related_push_id
- raw_answers
- practice_result
- submitted_at
- normalized_answer
- parsing_notes

### 7.6.4 交互要求
- 若用户未显式指定领域，应尽量根据上下文推断
- 若有多个活跃领域且无法推断，应提示选择
- 能识别“补交昨天作业”“继续刚才那题”等场景

---

## 7.7 评估与反馈模块

### 7.7.1 目标
判断用户对当前知识点的掌握程度，并提供可操作反馈。

### 7.7.2 评估维度
建议沿用并正式化以下 4 维结构：
1. 关键概念覆盖度（30%）
2. 理解深度（25%）
3. 逻辑清晰度（25%）
4. 实践应用能力（20%）

### 7.7.3 评分输出
- total_score
- dimension_scores
- strengths
- weaknesses
- missed_concepts
- improvement_suggestions
- mastery_estimate
- recommended_next_action

### 7.7.4 持久化要求
每次评估必须记录：
- raw_answer
- llm_feedback
- structured_scores
- evaluator_version
- rubric_version
- evidence_quotes

### 7.7.5 决策输出
评估器必须给出后续动作建议：
- advance_to_next_topic
- repeat_same_topic
- insert_review
- ask_followup_question
- trigger_mini_test

---

## 7.8 知识回顾与复习模块

### 7.8.1 目标
避免“学过即忘”，建立节奏化回顾机制。

### 7.8.2 触发条件
1. 某话题得分低于阈值
2. 用户连续多次遗漏关键概念
3. 到达预设复习间隔（如 1 天、3 天、7 天）
4. 阶段性知识整合前

### 7.8.3 复习内容形式
- 概念回顾卡片
- 快速问答
- 错题重练
- 应用型小任务
- 跨主题对比题

### 7.8.4 复习调度策略
建议采用“规则 + 简化间隔重复”混合策略：
- 低分话题优先复习
- 高遗忘风险概念提前回顾
- 与新话题穿插安排，避免连续纯复习造成疲劳

---

## 7.9 学习总结模块

### 7.9.1 目标
在不同粒度上帮助用户做复盘。

### 7.9.2 总结层级
1. 单次学习总结
2. 周总结
3. 模块总结
4. 阶段总结
5. 终局总结

### 7.9.3 总结内容
- 本阶段完成内容
- 高分项/低分项
- 常错概念
- 建议复习方向
- 下一阶段重点

---

## 7.10 综合测试模块

### 7.10.1 目标
在领域学习末期验证是否达到掌握标准。

### 7.10.2 触发条件
建议默认：
- 完成度 > 90%
- 平均分 > 80
- 实践完成度 > 85%

### 7.10.3 输出
- pass/fail
- final_score
- domain_mastery_level
- still_weak_topics
- next_recommendation

### 7.10.4 持久化
最终综测同样写入 assessment_history，并保留原始题目与原始作答。

---

## 7.11 学习报告模块

### 7.11.1 目标
为用户提供可视化与可追溯的学习成果报告。

### 7.11.2 报告类型
1. 即时进度报告
2. 周报
3. 阶段报告
4. 领域结业报告

### 7.11.3 报告内容
- 完成度
- 平均分趋势
- 各维度能力趋势
- 学习时长
- 推送/提交频率
- 高低分话题分布
- 掌握度热力图
- 个性化建议

### 7.11.4 输出形式
- HTML 报告（首选）
- JSON 原始数据
- 未来可扩展 PDF

---

## 7.12 在线资源增强模块

### 7.12.1 目标
将静态课程内容与最新在线资源结合，提升时效性。

### 7.12.2 能力范围
1. 搜索相关文章/教程/文档/视频/论文/代码
2. 针对当前话题补充最新资源
3. 资源分类与去重
4. 资源缓存

### 7.12.3 约束
- 在线资源获取失败不能阻断主学习流程
- 应有缓存与超时控制
- 需要保留资源来源、标题、URL、摘要

---

## 7.13 定时任务模块

### 7.13.1 目标
支持每日自动推送及其他定期学习任务。

### 7.13.2 支持的任务类型
1. 每日学习内容推送
2. 复习提醒
3. 周总结推送
4. 阶段报告生成
5. 中断学习唤醒提醒

### 7.13.3 调度需求
- 支持 cron 表达式
- 支持用户维度任务
- 支持领域维度任务
- 支持暂停/恢复/立即执行
- 支持失败重试
- 支持状态查询

### 7.13.4 推送渠道
- Telegram
- 其他消息平台（后续扩展）
- 本地文件输出（调试/离线）

---

## 8. 非功能需求

## 8.1 可用性
- 推送失败要可追踪
- 用户提交后应尽快反馈
- 核心学习档案不可轻易损坏

## 8.2 可维护性
- 模块边界清晰
- 数据模型版本化
- 评估器与计划生成器解耦
- 支持新领域快速接入

## 8.3 可观测性
需要记录：
- 任务执行日志
- 推送成功率
- 评估耗时
- 资源抓取成功率
- 数据读写异常

## 8.4 性能
个人使用场景下不追求极端高并发，但要求：
- 单次推送生成可在合理时间内完成
- 提交评估延迟可接受
- 报告生成不阻塞主流程

## 8.5 数据可靠性
- 写入尽量原子化
- 数据升级有迁移逻辑
- 关键文件损坏可恢复
- 有备份策略

## 8.6 安全性
- 保护用户学习数据隐私
- 减少敏感日志泄露
- 定时任务不应误投递到错误渠道

## 8.7 国际化
首版以中文为主，但内部数据结构应为多语言扩展预留字段。

---

## 9. 系统架构设计

## 9.1 架构总览

推荐采用“分层 + 工作流驱动”架构：

1. Interface Layer
   - Telegram Bot / CLI / Web UI / API
2. Application Layer
   - 学习编排服务、提交处理服务、报告服务、任务调度服务
3. Domain Layer
   - 计划、评估、复习、掌握度、报告等核心领域逻辑
4. Infrastructure Layer
   - 存储、LLM、调度器、消息投递、资源抓取、缓存

### 9.1.1 核心服务建议
1. learner_profile_service
2. domain_plan_service
3. content_push_service
4. submission_service
5. evaluation_service
6. review_scheduler_service
7. report_service
8. delivery_service
9. cron_orchestrator
10. online_resource_service

---

## 9.2 模块拆分建议

### 9.2.1 核心领域模块
- coach.py
  - 主编排入口
- level_tester.py
  - 水平测试与分级
- plan_generator.py
  - 学习计划生成
- content_pusher.py
  - 推送内容选择与生成
- evaluator.py
  - 提交评估
- review_engine.py
  - 复习策略
- mastery_engine.py
  - 掌握度计算
- report_generator.py
  - 报告生成
- online_resource.py
  - 在线资源抓取
- scheduler_adapter.py
  - 对接 cron/scheduler

### 9.2.2 基础设施模块
- data_store.py
- models.py
- migrations.py
- cache.py
- llm_client.py
- delivery_clients/
  - telegram.py
  - local.py

### 9.2.3 API / 接口模块
- api/routes/domains.py
- api/routes/submissions.py
- api/routes/reports.py
- api/routes/schedules.py

---

## 10. 数据模型设计

## 10.1 数据组织建议

可采用以下目录组织（本地文件版）：

```text
learning_coach/
├── users/
│   └── {user_id}/
│       ├── profile.json
│       ├── domains/
│       │   └── {domain}/
│       │       ├── plan.json
│       │       ├── progress.json
│       │       ├── records.json
│       │       ├── evaluations.json
│       │       ├── pushes.json
│       │       ├── reviews.json
│       │       ├── assessments.json
│       │       ├── reports/
│       │       └── cache/
└── shared/
    ├── domain_catalog/
    └── prompt_templates/
```

## 10.2 核心实体

### 10.2.1 UserProfile
- user_id
- display_name
- preferred_language
- timezone
- default_daily_minutes
- preferred_learning_style
- created_at
- updated_at

### 10.2.2 DomainEnrollment
- user_id
- domain
- status
- started_at
- target_mastery_level
- delivery_schedule
- last_push_at
- next_push_at

### 10.2.3 LearningPlan
- domain
- version
- initial_level
- modules
- topics
- pacing_strategy
- review_strategy
- generated_at

### 10.2.4 TopicProgress
- topic_id
- status
- attempts
- average_score
- mastery_score
- last_studied_at
- next_review_at

### 10.2.5 SubmissionRecord
- submission_id
- push_id
- topic_id
- raw_answers
- practice_result
- submitted_at
- parsed_content

### 10.2.6 EvaluationRecord
- evaluation_id
- submission_id
- raw_answer
- llm_feedback
- structured_scores
- total_score
- recommended_next_action
- evaluated_at

### 10.2.7 AssessmentRecord
- assessment_id
- assessment_type
- questions
- raw_answers
- llm_feedback
- structured_scores
- result_level
- created_at

### 10.2.8 PushRecord
- push_id
- topic_id
- push_type
- content_snapshot
- resources
- deliver_to
- deliver_status
- created_at

## 10.3 必保兼容字段

为了与我们已讨论过的持久化要求一致，以下字段必须长期保留：
- assessment_history
- submission_history
- raw_answers
- raw_answer
- llm_feedback
- structured_scores
- created_at
- updated_at

## 10.4 数据版本与迁移

每份主要 JSON/数据库记录建议保留：
- schema_version
- migrated_from_version
- migration_notes

系统读取旧数据时自动补齐缺失字段。

---

## 11. 状态机设计

## 11.1 领域状态
- not_started
- assessing
- planning
- active
- review_due
- awaiting_submission
- paused
- final_assessment_due
- completed
- archived

## 11.2 话题状态
- locked
- ready
- pushed
- studying
- submitted
- evaluated
- review_due
- mastered

## 11.3 推送状态
- generated
- delivering
- delivered
- failed
- retrying
- skipped

---

## 12. AI/Agent 设计

## 12.1 LLM 参与环节
1. 水平测试评估
2. 个性化反馈生成
3. 学习内容润色/组织
4. 实践任务生成
5. 思考题生成
6. 资源摘要
7. 报告总结

## 12.2 规则与模型混合
为了提高稳定性，建议“规则 + LLM”混合架构：

- 规则负责：
  - 任务推进逻辑
  - 状态机
  - 评分阈值判定
  - 复习调度
  - 调度任务触发
- LLM 负责：
  - 评估自然语言回答
  - 生成反馈文本
  - 补充讲解内容
  - 总结与归纳

## 12.3 Prompt 设计要求
每类 LLM 调用应有独立模板，模板中需要明确：
- 输入上下文
- 输出 JSON schema
- 评分 rubric
- 禁止胡编评语
- 必须引用用户原回答证据

---

## 13. 定时任务与消息投递设计

## 13.1 调度器职责
1. 维护任务定义
2. 到点触发生成推送
3. 执行失败重试
4. 写回执行状态
5. 支持手动立即运行
6. 支持暂停与恢复

## 13.2 推荐任务定义结构
- job_id
- user_id
- domain
- schedule
- enabled
- next_run_at
- last_run_at
- last_status
- deliver_target
- task_type

## 13.3 投递幂等性
为避免重复发送：
- 每次执行生成 execution_id
- 同一 push_id 成功投递后不重复发送
- 重试时检查是否已成功

## 13.4 失败处理
- 投递失败记录错误信息
- 网络故障自动重试
- 业务错误进入人工/日志排查

---

## 14. API 设计建议

## 14.1 用户/领域相关
- POST /domains/start
- GET /domains
- GET /domains/{domain}
- POST /domains/{domain}/pause
- POST /domains/{domain}/resume

## 14.2 测试与计划相关
- POST /domains/{domain}/assessment/start
- POST /domains/{domain}/assessment/submit
- GET /domains/{domain}/plan

## 14.3 推送与提交相关
- POST /domains/{domain}/push/run
- POST /domains/{domain}/submission
- GET /domains/{domain}/submissions

## 14.4 报告相关
- GET /domains/{domain}/progress
- POST /domains/{domain}/report/generate
- GET /domains/{domain}/report/latest

## 14.5 调度相关
- POST /schedules
- GET /schedules
- POST /schedules/{job_id}/run
- POST /schedules/{job_id}/pause
- POST /schedules/{job_id}/resume

---

## 15. 前端/用户界面建议

## 15.1 用户视图
1. 领域总览页
2. 单领域学习主页
3. 今日任务页
4. 提交记录页
5. 评估反馈页
6. 报告页
7. 计划与设置页

## 15.2 核心组件
- 进度条
- 模块导航
- 题目卡片
- 提交表单
- 评分面板
- 趋势图表
- 复习提醒卡片

---

## 16. 验收标准

### 16.1 功能验收
系统必须能够：
1. 为新用户发起水平测试
2. 生成并保存学习计划
3. 按时间自动推送当天学习任务
4. 接收用户回答并评估
5. 持久化原始答案、评估反馈与结构化评分
6. 按得分决定推进/复习
7. 生成可视化学习报告
8. 支持至少一个完整领域（ai_agent）
9. 支持定时任务暂停/恢复/立即执行
10. 在在线资源失败时仍完成推送

### 16.2 数据验收
必须验证以下记录真实落盘：
- plan
- assessment_history
- submission_history
- pushes
- evaluations
- reports

### 16.3 质量验收
- 不因单个模块失败导致整条学习链路中断
- 旧数据可读
- 推送内容可读性良好
- 评估输出结构化稳定

---

## 17. 风险与难点

### 17.1 评估稳定性风险
LLM 对主观题评估可能波动，需要：
- rubric 固化
- 结构化输出
- 版本化评估器

### 17.2 内容推进合理性风险
如果完全依赖 LLM 规划，可能导致节奏不稳定，因此建议课程骨架预定义，动态调整仅在局部进行。

### 17.3 数据膨胀风险
长期运行会产生大量历史记录，需要归档与压缩策略。

### 17.4 推送丢失或误投递风险
必须对 deliver target 做严格校验和审计。

### 17.5 多领域上下文混淆风险
需要强领域隔离的数据结构和交互识别逻辑。

---

## 18. 版本规划建议

### v1
- 单用户
- 单消息平台优先（Telegram）
- 至少支持 ai_agent
- JSON 文件持久化
- 每日推送 + 提交评估 + 报告

### v1.5
- 多领域稳定支持
- 复习调度增强
- 周报/月报
- 更完善的在线资源抓取

### v2
- Web UI
- 数据库持久化
- 多用户
- 更丰富图表
- 更强复习算法

---

## 19. 建议的代码仓库结构

```text
personal-learning-coach/
├── README.md
├── docs/
│   ├── architecture.md
│   ├── requirements.md
│   ├── data-model.md
│   └── rollout-plan.md
├── src/
│   └── personal_learning_coach/
│       ├── coach.py
│       ├── models.py
│       ├── data_store.py
│       ├── level_tester.py
│       ├── plan_generator.py
│       ├── content_pusher.py
│       ├── evaluator.py
│       ├── review_engine.py
│       ├── mastery_engine.py
│       ├── report_generator.py
│       ├── online_resource.py
│       ├── scheduler_adapter.py
│       ├── delivery/
│       ├── prompts/
│       └── api/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
└── pyproject.toml
```

---

## 20. 结论

这个项目的本质不是“做一个会回答问题的机器人”，而是“做一个有长期记忆、能推进课程、能评估掌握度、能做复习与总结、还能自动定时推送的个人教学系统”。

项目成功的关键不在于一次回答有多聪明，而在于：
1. 数据是否持续可靠保存
2. 学习状态是否连续可追踪
3. 推送、提交、评估、复习、总结是否形成闭环
4. 评估是否可解释
5. 定时任务是否稳定可信

只要这五点成立，这个项目就具备从原型能力演进为真正产品的基础。

---

## 21. 文档自检记录（第 1 轮）

已检查覆盖项：
- 提问/水平测试
- 学习计划
- 每日学习
- 知识回顾
- 评估
- 总结
- 综测
- 定时任务
- 持久化
- 在线资源
- 多领域
- 报告

发现并已补充：
- 推送快照持久化要求
- 幂等投递要求
- 兼容旧数据要求
- 状态机说明

## 22. 文档自检记录（第 2 轮）

再次检查后确认已覆盖：
- 功能边界
- 非功能要求
- 领域模型
- API 轮廓
- 风险与版本规划
- 项目目录结构
- 验收标准

当前仍建议在实施阶段补充：
- 更细粒度 JSON schema / DB schema
- 评估 prompt 样例
- ai_agent 领域完整课程清单
