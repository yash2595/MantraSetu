"""Master Telemetry Aggregator for AI Orchestrator in MantraSetu AgentOS."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "OrchestratorTelemetryManager"
_COMPONENT_VERSION = "4.1"


class OrchestratorTelemetryManager:
    """Thread-safe aggregator for diagnostic statistics, metrics, and health reporting across all orchestrator components."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()

        self._requests_processed = 0
        self._successful_requests = 0
        self._failed_requests = 0
        self._total_latency_ms = 0.0

    def record_request(self, is_success: bool, latency_ms: float) -> None:
        """Record completed request metrics."""
        with self._lock:
            self._requests_processed += 1
            self._total_latency_ms += latency_ms
            if is_success:
                self._successful_requests += 1
            else:
                self._failed_requests += 1

    # ------------------------------------------------------------------
    # Telemetry, Diagnostics & Health APIs
    # ------------------------------------------------------------------

    def statistics(self) -> dict[str, Any]:
        """Return orchestrator telemetry statistics."""
        with self._lock:
            uptime = time.perf_counter() - self._start_time
            avg_lat = (self._total_latency_ms / self._requests_processed) if self._requests_processed > 0 else 0.0
            success_rate = round((self._successful_requests / self._requests_processed), 3) if self._requests_processed > 0 else 1.0

            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "started_at": self._started_at,
                "uptime_seconds": round(uptime, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "requests_processed": self._requests_processed,
                "successful_requests": self._successful_requests,
                "failed_requests": self._failed_requests,
                "success_rate": success_rate,
                "average_latency_ms": round(avg_lat, 2),
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
            message="OrchestratorTelemetryManager operational.",
        )
