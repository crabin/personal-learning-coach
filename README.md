# Personal Learning Coach

Closed-loop AI learning coach for domain enrollment, baseline assessment, plan generation, daily pushes, submission evaluation, review scheduling, final assessment, and progress reports.

## Current Scope

- CLI flow for `assess -> plan -> push -> submit -> report`
- FastAPI endpoints for enrollment, submission, reports, schedules, and final assessment
- Local JSON persistence under `DATA_DIR`
- Local delivery and Telegram delivery
- Online resource recommendation with cache, dedupe, and graceful fallback

## Requirements

- Python `3.12+`
- An OpenAI API key for LLM-backed assessment, planning, push generation, and evaluation
- Optional Telegram bot token and chat ID for real delivery

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Set these variables in `.env`:

```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4.5
DATA_DIR=./data
DELIVERY_MODE=local
LOG_LEVEL=INFO
```

For Telegram delivery:

```env
DELIVERY_MODE=telegram
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

For optional API protection and backups:

```env
API_AUTH_TOKEN=your-shared-token
ADMIN_READ_TOKEN=read-token
ADMIN_WRITE_TOKEN=write-token
BACKUP_DIR=./data/backups
```

## CLI Usage

Generate a plan:

```bash
coach --user-id u1 plan --domain ai_agent --daily-minutes 45 --learning-style practice
```

Push today's content:

```bash
coach --user-id u1 push --domain ai_agent
```

Submit an answer:

```bash
coach --user-id u1 submit --push-id <push_id> --answer "My answer"
```

Generate a report:

```bash
coach --user-id u1 report --domain ai_agent
```

Submit final assessment:

```bash
coach --user-id u1 final-assessment --domain ai_agent --passed --score 92 --feedback "Strong finish"
```

Pause / resume / archive / delete:

```bash
coach --user-id u1 pause --domain ai_agent
coach --user-id u1 resume --domain ai_agent
coach --user-id u1 archive --domain ai_agent
coach --user-id u1 delete-domain --domain ai_agent --confirm-delete
coach backup
coach restore --backup-path ./data/backups/20260428T120000Z
```

## API Usage

Start the API:

```bash
uvicorn personal_learning_coach.api.main:app --reload
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Enroll in a domain:

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

## Quality Checks

Run tests:

```bash
pytest -q
```

Run lint:

```bash
ruff check .
```

Run type checks:

```bash
mypy src
```

CI now runs `ruff`, `mypy`, and `pytest` on GitHub Actions.

## Data and Delivery

- Runtime data is stored under `DATA_DIR` as JSON collections.
- `coach backup` or `POST /admin/backup` creates timestamped JSON backups under `BACKUP_DIR`.
- `GET /admin/runtime-events` returns recent operational events such as auth failures and backup creation.
- `GET /admin/alerts` returns lightweight derived alerts from recent runtime events.
- `POST /admin/restore` restores JSON store files from a backup directory.
- Local delivery writes Markdown files to `DATA_DIR/pushes/`.
- Telegram delivery uses the Bot API and records both success and failure in `PushRecord.delivery_result`.
- Online resources are only fetched when enrollment preferences allow them.
- When `API_AUTH_TOKEN` is set, administrative routes require the `x-api-key` header.
- If `ADMIN_READ_TOKEN` / `ADMIN_WRITE_TOKEN` are set, admin read/write actions can be separated.
- Runtime logs are also written as JSON lines to `DATA_DIR/logs/app.log`.

## Known Gaps

- Deployment and operations guidance is still minimal.
- Alert delivery and automated recovery drills are still basic.
