"""Structured domain events and abstract event publishing system for AIOrchestrator."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any
from uuid import UUID

from app.interfaces.chat_orchestrator import IEventPublisher

logger = logging.getLogger("app.orchestrator.events")


@dataclass(frozen=True, slots=True)
class OrchestrationEvent:
    """Immutable domain event emitted during orchestration pipeline lifecycle."""

    event_type: str
    request_id: UUID
    session_id: str | None = None
    conversation_id: UUID | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


class LoggingEventPublisher(IEventPublisher):
    """Default event publisher logging lifecycle domain events with correlation fields."""

    def publish(self, event: Any) -> None:
        """Publish a domain event to structured logging system."""
        if not isinstance(event, OrchestrationEvent):
            return

        log_payload = {
            "event_type": event.event_type,
            "request_id": str(event.request_id),
            "session_id": event.session_id,
            "conversation_id": str(event.conversation_id) if event.conversation_id else None,
            "timestamp": event.timestamp.isoformat(),
            **event.metadata,
        }
        if "error" in event.event_type.lower() or "failed" in event.event_type.lower():
            logger.warning(event.event_type, extra=log_payload)
        else:
            logger.info(event.event_type, extra=log_payload)
