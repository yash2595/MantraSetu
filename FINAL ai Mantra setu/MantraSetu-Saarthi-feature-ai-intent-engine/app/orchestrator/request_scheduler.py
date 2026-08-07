"""Lightweight Request Scheduler for MantraSetu AgentOS."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.orchestrator.orchestrator_exceptions import ValidationError
from app.orchestrator.orchestrator_models import OrchestratorRequest

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "RequestScheduler"
_COMPONENT_VERSION = "4.1"


class RequestScheduler:
    """Lightweight request concurrency, queueing, and prioritization scheduler."""

    def __init__(self, max_concurrency: int = 10) -> None:
        self._max_concurrency = max_concurrency
        self._active_requests: dict[str, OrchestratorRequest] = {}
        self._cancelled_requests: set[str] = set()
        self._lock = RLock()
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()
        self._scheduled_count = 0
        self._cancelled_count = 0

    def schedule_request(self, request: OrchestratorRequest) -> bool:
        """Schedule and admit a request if concurrency limit permits."""
        with self._lock:
            if len(self._active_requests) >= self._max_concurrency:
                logger.warning("Request concurrency limit (%d) reached. Scheduling throttled.", self._max_concurrency)
                raise ValidationError(f"Concurrency limit ({self._max_concurrency}) reached. Throttled.")

            self._active_requests[request.request_id] = request
            self._scheduled_count += 1
            return True

    def cancel_request(self, request_id: str) -> None:
        """Mark a request ID as cancelled for cancellation propagation."""
        with self._lock:
            self._cancelled_requests.add(request_id)
            self._active_requests.pop(request_id, None)
            self._cancelled_count += 1

    def is_cancelled(self, request_id: str) -> bool:
        """Check if a request ID has been cancelled."""
        with self._lock:
            return request_id in self._cancelled_requests

    def complete_request(self, request_id: str) -> None:
        """Complete and remove request from active tracking."""
        with self._lock:
            self._active_requests.pop(request_id, None)
            self._cancelled_requests.discard(request_id)

    # ------------------------------------------------------------------
    # Diagnostics, Telemetry & Health
    # ------------------------------------------------------------------

    def statistics(self) -> dict[str, Any]:
        """Return scheduler statistics."""
        with self._lock:
            uptime = time.perf_counter() - self._start_time
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "started_at": self._started_at,
                "uptime_seconds": round(uptime, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "active_requests": len(self._active_requests),
                "scheduled_count": self._scheduled_count,
                "cancelled_count": self._cancelled_count,
                "max_concurrency": self._max_concurrency,
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
            message="RequestScheduler operational.",
        )
