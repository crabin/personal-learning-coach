---
name: Personal Learning Coach Design System
colors:
  surface: '#faf8ff'
  surface-dim: '#d9d9e5'
  surface-bright: '#faf8ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f3f3fe'
  surface-container: '#ededf9'
  surface-container-high: '#e7e7f3'
  surface-container-highest: '#e1e2ed'
  on-surface: '#191b23'
  on-surface-variant: '#434655'
  inverse-surface: '#2e3039'
  inverse-on-surface: '#f0f0fb'
  outline: '#737686'
  outline-variant: '#c3c6d7'
  surface-tint: '#0053db'
  primary: '#004ac6'
  on-primary: '#ffffff'
  primary-container: '#2563eb'
  on-primary-container: '#eeefff'
  inverse-primary: '#b4c5ff'
  secondary: '#712ae2'
  on-secondary: '#ffffff'
  secondary-container: '#8a4cfc'
  on-secondary-container: '#fffbff'
  tertiary: '#943700'
  on-tertiary: '#ffffff'
  tertiary-container: '#bc4800'
  on-tertiary-container: '#ffede6'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dbe1ff'
  primary-fixed-dim: '#b4c5ff'
  on-primary-fixed: '#00174b'
  on-primary-fixed-variant: '#003ea8'
  secondary-fixed: '#eaddff'
  secondary-fixed-dim: '#d2bbff'
  on-secondary-fixed: '#25005a'
  on-secondary-fixed-variant: '#5a00c6'
  tertiary-fixed: '#ffdbcd'
  tertiary-fixed-dim: '#ffb596'
  on-tertiary-fixed: '#360f00'
  on-tertiary-fixed-variant: '#7d2d00'
  background: '#faf8ff'
  on-background: '#191b23'
  surface-variant: '#e1e2ed'
  status-success: '#10B981'
  status-warning: '#F59E0B'
  status-error: '#EF4444'
  status-info: '#3B82F6'
  surface-console: '#1E293B'
  text-console: '#F8FAFC'
  border-danger: '#FECACA'
typography:
  headline-xl:
    fontFamily: Manrope
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
  headline-md:
    fontFamily: Manrope
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-base:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  mono-label:
    fontFamily: Space Grotesk
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.05em
  console-text:
    fontFamily: Space Grotesk
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  container-max: 1280px
  gutter: 1.5rem
  margin-page: 2rem
  stack-sm: 0.5rem
  stack-md: 1rem
  stack-lg: 2rem
---

# Web 功能清单

本文档仅整理当前 Web 端需要覆盖的功能、页面模块、按钮动作、输入项与状态反馈，暂不涉及任何视觉设计、交互风格、配色、排版或品牌表达。

## 1. 产品目标

Web 端需要作为 Personal Learning Coach 的统一工作台，支持用户完成以下闭环：

1. 创建学习目标与学习偏好
2. 获取当天学习内容与题目
3. 提交答案并查看评估反馈
4. 查看当前领域学习报告
5. 执行领域生命周期与基础运维操作

## 2. 全局功能

### 2.1 全局配置区

页面顶部需要提供以下全局输入项，供所有页面共用：

- `API 地址`
- `用户 ID`
- `学习领域`
- `Admin API Key`

要求：

- 修改 `API 地址` 后，后续所有请求都基于新的地址发送
- 修改 `用户 ID` 或 `学习领域` 后，需要切换当前上下文
- 修改 `Admin API Key` 后，管理类接口请求需要自动带上该值

### 2.2 健康检查

需要提供 `检查健康状态` 按钮。

点击后执行：

- 请求系统健康状态
- 显示健康结果
- 更新健康状态标记

健康结果至少应包含：

- 系统状态
- 当前投递模式
- 是否启用鉴权
- 备份目录
- 问题列表

### 2.3 页面导航

需要提供以下 4 个主页面入口：

- `学习目标`
- `问题回答`
- `学习报告`
- `管理运维`

要求：

- 支持在四个页面之间切换
- 当前页面需要有明确状态
- 切换页面时保留当前全局上下文

### 2.4 最近请求控制台

页面底部需要提供一个统一的请求结果展示区。

需要展示：

- 最近一次操作名称
- 最近一次请求方法与请求地址
- 返回结果 JSON
- 错误信息

需要提供：

- `清空` 按钮

## 3. 学习目标页

### 3.1 页面目标

用于创建一个新的学习领域目标，并写入用户的基础学习偏好。

### 3.2 输入项

需要提供以下字段：

- `当前水平`
- `目标水平`
- `每日分钟`
- `学习风格`
- `推送时间`
- `语言`
- `允许在线资源推荐`

字段说明：

- 当前水平：至少支持 `beginner`、`intermediate`、`advanced`
- 目标水平：至少支持 `beginner`、`intermediate`、`advanced`
- 每日分钟：数值型输入
- 学习风格：至少支持 `practice`、`blended`、`reading`、`project`
- 推送时间：时间字符串
- 语言：至少支持 `zh`、`en`
- 允许在线资源推荐：布尔开关

### 3.3 功能按钮

需要提供以下按钮：

- `创建学习目标`
- `查看当前状态`

### 3.4 创建学习目标

点击 `创建学习目标` 后，需要完成：

- 创建该用户在当前领域下的 enrollment
- 生成学习计划
- 返回 enrollment 与计划摘要

返回内容至少包含：

- enrollment ID
- plan ID
- domain
- 当前 level
- 当前状态
- topic 数量
- current level
- target level
- daily minutes
- learning style
- delivery time
- language
- allow online resources

### 3.5 查看当前状态

点击 `查看当前状态` 后，需要展示当前领域状态信息。

至少包括：

- 领域状态
- 当前 level
- topic 总数
- 已掌握 topic 数
- 待复习 topic 数
- 平均分

### 3.6 辅助信息

页面可展示但不局限于以下只读信息：

- 当前领域名称预览
- 当前学习路径摘要

## 4. 问题回答页

### 4.1 页面目标

用于获取当日学习推送，并提交本次回答。

### 4.2 今日推送内容区

页面需要能展示以下内容：

- 推送状态
- 理论讲解
- 基础问题 1
- 基础问题 2
- 基础问题 3
- 实践题
- 实践复盘题

要求：

- 当尚未获取内容时，展示默认提示
- 获取成功后，用最新推送内容覆盖默认提示
- 新推送到达后，旧答案输入框应被清空

### 4.3 回答输入区

需要提供以下输入项：

- `基础问题 1 回答`
- `基础问题 2 回答`
- `基础问题 3 回答`
- `实践答案`
- `Push ID`
- `实践产出摘要`
- `规范化答案`
- `解析备注`

说明：

- `Push ID` 在成功获取今日问题后应自动写入
- `规范化答案` 可为空
- `解析备注` 可为空
- 若 `规范化答案` 为空，可使用实践答案作为默认值

### 4.4 功能按钮

需要提供以下按钮：

- `获取今日问题`
- `提交答案并评估`

### 4.5 获取今日问题

点击后需要：

- 根据当前 `用户 ID` 与 `学习领域` 请求今日推送
- 返回 `push_id`
- 返回是否成功推送
- 返回 push type
- 返回理论内容
- 返回基础题列表
- 返回实践题
- 返回反思题

若当前没有可推送内容，需要明确展示：

- 未推送成功
- 原因说明

额外要求：

- 进入该页面时，如果当前上下文还没有加载过题目，可自动触发一次获取
- 若正在请求中，应防止重复点击

### 4.6 提交答案并评估

点击后需要：

- 组装本次回答内容
- 提交答案
- 触发评估
- 返回本次评估结果

提交内容至少包括：

- user_id
- push_id
- raw_answer
- practice_result
- normalized_answer
- parsing_notes

其中 `raw_answer` 需要由以下内容组合形成：

- 三个基础题回答
- 实践答案
- 当前复盘提示文本

### 4.7 评估结果区

提交成功后，页面需要展示：

- 总分
- 下一步动作
- 评估 ID
- 反馈文本

下一步动作至少支持以下语义：

- `continue`
- `consolidate`
- `review`
- `final_test`

如果用户当前停留在学习报告页，提交成功后应能同步刷新报告数据。

## 5. 学习报告页

### 5.1 页面目标

用于查看当前用户在当前领域下的结构化学习报告。

### 5.2 自动加载

进入该页面时需要自动执行：

- 读取学习报告
- 读取领域状态
- 更新页面中的同步状态提示

### 5.3 功能按钮

需要提供：

- `刷新`

点击后需要再次执行报告与状态同步。

### 5.4 报告展示内容

报告页至少需要展示以下内容：

- user_id
- domain
- report 生成时间
- enrollment status
- 总 topic 数
- 已掌握 topic 数
- 待复习 topic 数
- 掌握率
- 平均分

### 5.5 Topic Details

需要展示 topic 维度明细列表，至少包括：

- 序号
- topic 标题
- status
- mastery score
- avg score
- attempts

### 5.6 学习进度洞察

需要展示以下结构化内容：

- 分数趋势
- 强项列表
- 弱项列表
- 常错概念列表
- 是否达到结业评估准备状态
- 阶段总结

### 5.7 Recent Evaluations

需要展示最近评估记录列表，至少包括：

- 评估时间
- overall score
- next action
- feedback

### 5.8 空状态与失败状态

报告页需要覆盖以下状态：

- 正在加载
- 当前领域还没有可展示的学习进度
- 还没有提交后的评价记录
- 状态同步失败

## 6. 管理运维页

### 6.1 页面目标

用于处理领域生命周期、运维保障、结业评估和高风险操作。

### 6.2 领域生命周期

需要提供以下按钮：

- `暂停领域`
- `恢复领域`
- `归档领域`

点击后分别执行：

- 将领域状态变为 `PAUSED`
- 将领域状态变为 `ACTIVE`
- 将领域状态变为 `ARCHIVED`

返回结果至少包括：

- domain
- user_id
- status
- message

### 6.3 运行保障

需要提供以下按钮：

- `创建备份`
- `运行事件`
- `当前告警`

#### 创建备份

点击后需要：

- 创建当前数据库备份
- 返回备份路径
- 返回备份文件数
- 返回结果说明

#### 运行事件

点击后需要：

- 获取最近运行事件列表
- 默认支持 limit 参数

每条事件至少包含：

- event_id
- level
- category
- message
- details
- created_at

#### 当前告警

点击后需要：

- 获取当前告警列表

每条告警至少包含：

- severity
- category
- message

### 6.4 结业评估

需要提供以下输入项：

- `是否通过`
- `分数`
- `反馈`

需要提供按钮：

- `提交结业评估`

点击后需要：

- 提交该用户当前领域的结业评估结果
- 返回新的领域状态
- 返回 passed
- 返回 assessment ID
- 返回 score
- 返回结果说明

### 6.5 高级危险操作

需要提供以下输入与按钮：

- `确认删除当前用户和领域的所有相关数据` 复选框
- `删除领域` 按钮
- `备份路径` 输入框
- `确认用该备份恢复数据` 复选框
- `恢复备份` 按钮

约束要求：

- 未勾选删除确认时，`删除领域` 按钮必须禁用
- `删除领域` 按钮文案中应显示当前 `用户 ID / 学习领域`
- 未勾选恢复确认，或 `备份路径` 为空时，`恢复备份` 按钮必须禁用

#### 删除领域

点击后需要：

- 删除当前 `user_id + domain` 相关的所有数据

删除范围至少包括：

- domain enrollments
- learning plans
- topic progress
- push records
- question history
- submission records
- evaluation records
- assessment records

#### 恢复备份

点击后需要：

- 使用指定备份路径恢复数据库
- 返回恢复来源路径
- 返回恢复文件数
- 返回结果说明

## 7. 页面联动规则

### 7.1 全局上下文联动

- 修改 `学习领域` 后，需要同步更新当前领域预览
- 修改 `学习领域` 或 `用户 ID` 后，需要重置已加载的题目上下文
- 题目上下文重置后，`Push ID` 需要清空

### 7.2 问题页自动刷新规则

- 首次进入问题回答页时，如果当前上下文没有已加载题目，需要自动获取今日问题
- 如果已经存在当前 `user_id + domain` 对应的题目上下文，则不重复获取

### 7.3 报告页自动刷新规则

- 进入学习报告页时自动刷新
- 修改领域且当前停留在学习报告页时，自动刷新报告
- 提交答案成功后，如果当前就在报告页，应刷新报告

### 7.4 危险操作联动

- 修改 `用户 ID` 或 `学习领域` 后，删除按钮文案同步更新
- 修改恢复路径或确认状态后，恢复按钮可用性实时更新

## 8. API 对应关系

当前 Web 功能至少需要覆盖以下接口：

- `GET /health`
- `POST /domains/{domain}/enroll`
- `GET /domains/{domain}/status`
- `POST /domains/{domain}/pause`
- `POST /domains/{domain}/resume`
- `POST /domains/{domain}/archive`
- `DELETE /domains/{domain}`
- `POST /domains/{domain}/final-assessment`
- `POST /schedules/trigger`
- `POST /submissions`
- `GET /reports/{domain}`
- `POST /admin/backup`
- `GET /admin/runtime-events`
- `GET /admin/alerts`
- `POST /admin/restore`

## 9. 权限与约束

### 9.1 普通学习流程

以下功能默认不需要管理员权限：

- 健康检查
- 创建学习目标
- 查看当前状态
- 获取今日问题
- 提交答案并评估
- 查看学习报告
- 暂停领域
- 恢复领域
- 归档领域
- 提交结业评估
- 删除领域

### 9.2 管理接口

以下功能需要支持管理员凭证：

- 创建备份
- 查看运行事件
- 查看当前告警
- 恢复备份

页面需要支持通过 `Admin API Key` 传入管理员权限信息。

## 10. 文档边界

本文档只定义当前 Web 改版必须覆盖的功能清单，不包含以下内容：

- 视觉风格
- UI 布局方案
- 色彩、字体、动效
- 品牌语气
- 组件外观规范

后续如果进入正式改版，可在本文件基础上再补充信息架构、交互流程和视觉设计文档。
