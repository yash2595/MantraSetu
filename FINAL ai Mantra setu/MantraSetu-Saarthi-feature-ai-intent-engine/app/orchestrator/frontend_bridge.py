"""Frontend Integration Layer Bridge for MantraSetu AgentOS."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.orchestrator.orchestrator_contracts import IFrontendBridge

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "FrontendIntegrationBridge"
_COMPONENT_VERSION = "4.1"


class FrontendIntegrationBridge(IFrontendBridge):
    """Bridge synchronizing React Router, navigation events, and execution directives with frontend clients."""

    def __init__(self) -> None:
        self._events_history: list[dict[str, Any]] = []
        self._lock = RLock()
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()
        self._published_events_count = 0

    def publish_navigation_event(self, session_id: str, payload: dict[str, Any]) -> None:
        """Publish structured navigation event for React client consumption."""
        with self._lock:
            self._published_events_count += 1
            evt = {"session_id": session_id, "type": "NAVIGATION", "payload": payload, "ts": time.time()}
            self._events_history.append(evt)

    def publish_execution_directive(self, session_id: str, directive: dict[str, Any]) -> None:
        """Publish structured execution directive for frontend runner consumption."""
        with self._lock:
            self._published_events_count += 1
            evt = {"session_id": session_id, "type": "EXECUTION", "directive": directive, "ts": time.time()}
            self._events_history.append(evt)

    # ------------------------------------------------------------------
    # Telemetry, Diagnostics & Health APIs
    # ------------------------------------------------------------------

    def statistics(self) -> dict[str, Any]:
        """Return frontend bridge statistics."""
        with self._lock:
            uptime = time.perf_counter() - self._start_time
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "started_at": self._started_at,
                "uptime_seconds": round(uptime, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "published_events_count": self._published_events_count,
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
            message="FrontendIntegrationBridge operational.",
        )
