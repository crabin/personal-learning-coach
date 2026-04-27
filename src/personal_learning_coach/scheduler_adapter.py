"""Scheduler wrapper — daily push orchestration via APScheduler."""

from __future__ import annotations

import logging
import os

from apscheduler.schedulers.blocking import BlockingScheduler

logger = logging.getLogger(__name__)


def _build_scheduler(user_id: str, domain: str) -> BlockingScheduler:
    from personal_learning_coach.content_pusher import push_today

    scheduler = BlockingScheduler()
    hour = int(os.environ.get("DAILY_PUSH_HOUR", "9"))
    minute = int(os.environ.get("DAILY_PUSH_MINUTE", "0"))

    scheduler.add_job(
        func=push_today,
        trigger="cron",
        hour=hour,
        minute=minute,
        kwargs={"user_id": user_id, "domain": domain},
        id="daily_push",
        replace_existing=True,
    )
    logger.info("Scheduled daily push at %02d:%02d for user=%s domain=%s", hour, minute, user_id, domain)
    return scheduler


def start_scheduler(user_id: str, domain: str) -> None:
    """Start the blocking daily push scheduler. Runs forever."""
    scheduler = _build_scheduler(user_id, domain)
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("Scheduler stopped.")
