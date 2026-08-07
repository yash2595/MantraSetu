"""Internal Event Bus for Orchestrator loose-coupling in MantraSetu AgentOS."""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Callable

from app.core.models import ComponentHealth, SystemHealthStatus
from app.orchestrator.orchestrator_models import OrchestratorEventType

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "OrchestratorEventBus"
_COMPONENT_VERSION = "4.1"


@dataclass(frozen=True)
class EventPayload:
    """Immutable event payload container."""

    event_type: OrchestratorEventType
    session_id: str
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class OrchestratorEventBus:
    """Internal event bus facilitating decoupled asynchronous event publishing and subscription."""

    def __init__(self) -> None:
        self._subscribers: dict[OrchestratorEventType, list[Callable[[EventPayload], None]]] = defaultdict(list)
        self._lock = RLock()
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()
        self._events_published_count = 0

    def subscribe(self, event_type: OrchestratorEventType, callback: Callable[[EventPayload], None]) -> None:
        """Subscribe a callback to an OrchestratorEventType."""
        with self._lock:
            self._subscribers[event_type].append(callback)

    def publish(self, event_type: OrchestratorEventType, session_id: str, data: dict[str, Any] | None = None) -> None:
        """Publish an event to all registered subscribers."""
        payload = EventPayload(event_type=event_type, session_id=session_id, data=data or {})
        with self._lock:
            self._events_published_count += 1
            callbacks = list(self._subscribers.get(event_type, []))

        for cb in callbacks:
            try:
                cb(payload)
            except Exception as e:
                logger.error("Error executing subscriber callback for event '%s': %s", event_type.value, e)

    # ------------------------------------------------------------------
    # Telemetry, Diagnostics & Health APIs
    # ------------------------------------------------------------------

    def statistics(self) -> dict[str, Any]:
        """Return event bus statistics."""
        with self._lock:
            uptime = time.perf_counter() - self._start_time
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "started_at": self._started_at,
                "uptime_seconds": round(uptime, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "events_published_count": self._events_published_count,
                "subscribers_count": sum(len(cbs) for cbs in self._subscribers.values()),
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
            message="OrchestratorEventBus operational.",
        )
