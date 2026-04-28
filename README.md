# Personal Learning Coach

一个基于 FastAPI 和 OpenAI 的个人学习教练项目，用来完成学习闭环：

- 领域报名与初始化
- 基线测评
- 学习计划生成
- 每日学习内容推送
- 作答提交与评估
- 复习调度
- 阶段性报告与结业评估

当前项目同时提供：

- `CLI` 命令行使用方式
- `FastAPI` HTTP 接口方式

## 项目结构

```text
src/personal_learning_coach/
  api/                FastAPI 入口与路由
  coach.py            CLI 入口
  config.py           环境变量与运行配置
  data_store.py       本地 JSON 数据存储
  plan_generator.py   学习计划生成
  evaluator.py        作答评估
  report_generator.py 学习报告生成
data/                 运行期数据目录
tests/                测试
```

## 运行环境

- Python `3.12+`
- 推荐使用 `uv`
- 需要可用的 `OPENAI_API_KEY`

本地已经存在 `uv.lock`，因此优先推荐用 `uv` 安装和运行。

## 快速开始

### 1. 安装依赖

```bash
cd /Users/lpb/workspace/myProjects/personal-learning-coach
uv sync --dev
```

如果你不用 `uv`，也可以：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

至少需要在 `.env` 中配置这些字段：

```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4.5
OPENAI_BASE_URL=
DATA_DIR=./data
DELIVERY_MODE=local
LOG_LEVEL=INFO
```

如果你使用 OpenAI 兼容网关，也可以配置：

```env
OPENAI_BASE_URL=https://your-openai-compatible-endpoint/v1
```

如需 Telegram 推送，再补充：

```env
DELIVERY_MODE=telegram
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

如需接口鉴权和备份能力，可补充：

```env
API_AUTH_TOKEN=your-shared-token
ADMIN_READ_TOKEN=read-token
ADMIN_WRITE_TOKEN=write-token
BACKUP_DIR=./data/backups
```

## 如何启动项目

### 方式一：启动 API 服务

这是最常用的方式，适合本地调试接口和联调前端。

```bash
uv run uvicorn personal_learning_coach.api.main:app --reload
```

启动后访问：

- Swagger 文档: `http://127.0.0.1:8000/docs`
- 健康检查: `http://127.0.0.1:8000/health`

健康检查命令：

```bash
curl http://127.0.0.1:8000/health
```

### 方式二：使用 CLI

项目定义了一个命令行入口 `coach`：

```bash
uv run coach --help
```

常见命令如下。

生成学习计划：

```bash
uv run coach --user-id u1 plan --domain ai_agent --daily-minutes 45 --learning-style practice
```

推送今天的学习内容：

```bash
uv run coach --user-id u1 push --domain ai_agent
```

提交答案：

```bash
uv run coach --user-id u1 submit --push-id <push_id> --answer "My answer"
```

生成报告：

```bash
uv run coach --user-id u1 report --domain ai_agent
```

提交结业评估：

```bash
uv run coach --user-id u1 final-assessment --domain ai_agent --passed --score 92 --feedback "Strong finish"
```

暂停、恢复、归档、删除领域：

```bash
uv run coach --user-id u1 pause --domain ai_agent
uv run coach --user-id u1 resume --domain ai_agent
uv run coach --user-id u1 archive --domain ai_agent
uv run coach --user-id u1 delete-domain --domain ai_agent --confirm-delete
```

备份与恢复：

```bash
uv run coach backup
uv run coach restore --backup-path ./data/backups/20260428T120000Z
```

### 方式三：启动 Web 控制台

Web 控制台位于 `src/web`，用于在浏览器中操作报名、推送、提交、报告、结业评估、备份和告警等 API 功能。

先启动后端 API：

```bash
uv run uvicorn personal_learning_coach.api.main:app --reload
```

再启动前端：

```bash
cd src/web
npm install
npm run dev
```

默认访问：

- Web 控制台: `http://127.0.0.1:5173`
- API 代理目标: `http://127.0.0.1:8000`

如果后端不在默认地址，可以在控制台顶部修改 API 地址，或启动前设置：

```bash
VITE_API_PROXY_TARGET=http://127.0.0.1:8000 npm run dev
```

## 最小可运行示例

### 1. 启动 API

```bash
uv run uvicorn personal_learning_coach.api.main:app --reload
```

### 2. 创建一个学习领域

```bash
curl -X POST http://127.0.0.1:8000/domains/ai_agent/enroll \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "u1",
    "daily_minutes": 45,
    "learning_style": "practice",
    "delivery_time": "20:30",
    "language": "zh",
    "allow_online_resources": true,
    "target_level": "advanced"
  }'
```

### 3. 查看健康状态

```bash
curl http://127.0.0.1:8000/health
```

### 4. 查看接口文档

在浏览器打开：

```text
http://127.0.0.1:8000/docs
```

## 数据与输出

- 运行数据默认保存在 `DATA_DIR`，通常是 `./data`
- 本地推送内容会写入 `DATA_DIR/pushes/`
- 日志会写入 `DATA_DIR/logs/app.log`
- 备份目录默认是 `./data/backups`

## 开发检查

运行测试：

```bash
uv run pytest -q
```

运行 lint：

```bash
uv run ruff check .
```

运行类型检查：

```bash
uv run mypy src
```

运行 Web 控制台检查：

```bash
cd src/web
npm run test
npm run build
```

## 当前注意事项

- 如果没有配置 `OPENAI_API_KEY`，涉及 LLM 生成和评估的功能可能无法正常工作
- 如果 `DELIVERY_MODE=telegram`，必须同时提供 `TELEGRAM_BOT_TOKEN` 和 `TELEGRAM_CHAT_ID`
- 管理接口在设置 `API_AUTH_TOKEN`、`ADMIN_READ_TOKEN`、`ADMIN_WRITE_TOKEN` 后需要带鉴权请求头
- Web 控制台不会保存 Admin API Key；刷新页面后需要重新输入
