"""Abstract delivery adapter interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from personal_learning_coach.models import PushRecord


class DeliveryAdapter(ABC):
    """Base class for all delivery channels."""

    @abstractmethod
    def deliver(self, push: PushRecord) -> None:
        """Deliver push content to the learner."""

    def format_push(self, push: PushRecord) -> str:
        """Render a PushRecord to a human-readable string."""
        return (
            f"# Daily Learning Push\n\n"
            f"**Topic:** {push.topic_id}\n\n"
            f"## Theory\n{push.theory}\n\n"
            f"## Practice\n{push.practice_question}\n\n"
            f"## Reflection\n{push.reflection_question}\n"
        )
