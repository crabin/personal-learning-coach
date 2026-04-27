"""File-based delivery adapter for offline / development use."""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from pathlib import Path

from personal_learning_coach.delivery.base import DeliveryAdapter
from personal_learning_coach.models import PushRecord

logger = logging.getLogger(__name__)


class LocalDelivery(DeliveryAdapter):
    """Writes push content to data/pushes/<date>_<push_id>.md."""

    def __init__(self, output_dir: Path | None = None) -> None:
        if output_dir is None:
            data_dir = Path(os.environ.get("DATA_DIR", "./data"))
            output_dir = data_dir / "pushes"
        self._output_dir = output_dir
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def deliver(self, push: PushRecord) -> None:
        date_str = datetime.now(UTC).strftime("%Y-%m-%d")
        filename = f"{date_str}_{push.push_id}.md"
        path = self._output_dir / filename
        content = self.format_push(push)
        path.write_text(content, encoding="utf-8")
        logger.info("Push delivered locally: %s", path)
