"""Inter-Agent Event Distribution & Message Bus v1.0."""

from __future__ import annotations

import logging
import time
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.agents.agent_models import AgentMessage, MessageType
from app.agents.agent_telemetry import AgentTelemetryEngine

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "AgentMessageBus"
_COMPONENT_VERSION = "1.0.0"


class AgentMessageBus:
    """Enterprise thread-safe event bus distributing structured AgentMessage frames (<2ms target)."""

    def __init__(self, telemetry: AgentTelemetryEngine | None = None) -> None:
        self._telemetry = telemetry or AgentTelemetryEngine()
        # agent_id -> list of AgentMessage
        self._inboxes: dict[str, list[AgentMessage]] = {}
        self._lock = RLock()
        self._messages_sent_count = 0

    def send_message(self, message: AgentMessage) -> bool:
        """Send a structured AgentMessage to a target receiver inbox (<2ms target)."""
        start_ts = time.perf_counter()
        with self._lock:
            self._messages_sent_count += 1
            rec_id = message.receiver_id

            if rec_id not in self._inboxes:
                self._inboxes[rec_id] = []

            self._inboxes[rec_id].append(message)
            self._telemetry.record_message_sent(message.sender_id)

            duration_ms = (time.perf_counter() - start_ts) * 1000
            logger.debug("AgentMessageBus dispatched message '%s' [%s -> %s] in %.2fms", message.message_id, message.sender_id, rec_id, duration_ms)
            return True

    def broadcast(self, sender_id: str, payload: dict[str, Any]) -> int:
        """Broadcast a message frame to all registered agent inboxes."""
        with self._lock:
            msg = AgentMessage(
                sender_id=sender_id,
                receiver_id="BROADCAST",
                msg_type=MessageType.BROADCAST,
                payload=dict(payload),
            )
            count = 0
            for inbox_key in list(self._inboxes.keys()):
                self._inboxes[inbox_key].append(msg)
                count += 1
            self._messages_sent_count += count
            return count

    def subscribe(self, agent_id: str) -> list[AgentMessage]:
        """Poll and retrieve all unread messages for agent_id."""
        with self._lock:
            msgs = self._inboxes.pop(agent_id, [])
            broadcasts = self._inboxes.get("BROADCAST", [])
            return msgs + list(broadcasts)

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose message bus operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "messages_sent_count": self._messages_sent_count,
                "active_inboxes_count": len(self._inboxes),
            }

    def metrics(self) -> dict[str, Any]:
        """Expose metrics."""
        return self.statistics()

    def health(self) -> ComponentHealth:
        """Report component health status."""
        return ComponentHealth(
            component_name=_COMPONENT_NAME,
            status=SystemHealthStatus.HEALTHY,
            details=self.statistics(),
        )
