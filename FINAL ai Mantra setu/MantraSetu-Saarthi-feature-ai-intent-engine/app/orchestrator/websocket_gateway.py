"""Bidirectional WebSocket Gateway for MantraSetu AgentOS."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "WebSocketGateway"
_COMPONENT_VERSION = "4.1"


@dataclass(frozen=True)
class WebSocketMessage:
    """Immutable WebSocket message frame model."""

    message_type: str
    session_id: str
    payload: dict[str, Any] = field(default_factory=dict)
    sequence: int = 1
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_type": self.message_type,
            "session_id": self.session_id,
            "payload": dict(self.payload),
            "sequence": self.sequence,
            "timestamp": self.timestamp,
        }


class WebSocketGateway:
    """Gateway handling frame serialization, heartbeat ping/pong, and session reconnect framing."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()
        self._messages_framed_count = 0

    def format_frame(self, message_type: str, session_id: str, payload: dict[str, Any], sequence: int = 1) -> WebSocketMessage:
        """Format a structured WebSocketMessage frame."""
        with self._lock:
            self._messages_framed_count += 1
            return WebSocketMessage(
                message_type=message_type.upper(),
                session_id=session_id,
                payload=payload,
                sequence=sequence,
            )

    def handle_ping(self, session_id: str) -> WebSocketMessage:
        """Construct pong heartbeat frame."""
        return self.format_frame("PONG", session_id, {"status": "ALIVE"})

    # ------------------------------------------------------------------
    # Telemetry, Diagnostics & Health APIs
    # ------------------------------------------------------------------

    def statistics(self) -> dict[str, Any]:
        """Return gateway statistics."""
        with self._lock:
            uptime = time.perf_counter() - self._start_time
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "started_at": self._started_at,
                "uptime_seconds": round(uptime, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "messages_framed_count": self._messages_framed_count,
                "thread_safe": True,
            }

    def metrics(self) -> dict[str, Any]:
        """Expose performance metrics."""
        return self.statistics()

    def health(self) -> ComponentHealth:
        """Report component health."""
        return ComponentHealth(
            component_name=_COMPONENT_NAME,
            status=SystemHealthStatus.HEALTHY,
            message="WebSocketGateway operational.",
        )
