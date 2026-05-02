"""Abstract delivery adapter interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from personal_learning_coach.domain.models import PushRecord


class DeliveryAdapter(ABC):
    """Base class for all delivery channels."""

    @abstractmethod
    def deliver(self, push: PushRecord) -> None:
        """Deliver push content to the learner."""

    def format_push(self, push: PushRecord) -> str:
        """Render a PushRecord to a human-readable string."""
        resources = self._format_resources(push.resource_snapshot)
        resources_block = f"\n## Recommended Resources\n{resources}\n" if resources else ""
        return (
            f"# Daily Learning Push\n\n"
            f"**Topic:** {push.topic_id}\n\n"
            f"## Theory\n{push.theory}\n\n"
            f"## Practice\n{push.practice_question}\n\n"
            f"## Reflection\n{push.reflection_question}\n"
            f"{resources_block}"
        )

    def _format_resources(self, resource_snapshot: dict[str, object]) -> str:
        items = resource_snapshot.get("items") if isinstance(resource_snapshot, dict) else None
        if not isinstance(items, list) or not items:
            return ""

        lines: list[str] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title", "")).strip()
            url = str(item.get("url", "")).strip()
            summary = str(item.get("summary", "")).strip()
            if not title or not url:
                continue
            line = f"- {title}: {url}"
            if summary:
                line += f" - {summary}"
            lines.append(line)
        return "\n".join(lines)
