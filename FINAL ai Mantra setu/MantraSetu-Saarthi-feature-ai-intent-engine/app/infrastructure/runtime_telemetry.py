"""Dedicated Telemetry Aggregator Engine for Deployment & Infrastructure Framework v1.0."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "RuntimeTelemetryEngine"
_COMPONENT_VERSION = "1.0.0"


class RuntimeTelemetryEngine:
    """Enterprise thread-safe telemetry aggregator tracking config lookups, service discoveries, scaling events, and failover triggers."""

    def __init__(self) -> None:
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()
        self._lock = RLock()

        # Telemetry counts
        self._config_lookups_count = 0
        self._service_discoveries_count = 0
        self._scaling_events_count = 0
        self._failover_events_count = 0

    def record_config_lookup(self, lookup_time_ms: float) -> None:
        """Record configuration lookup event."""
        with self._lock:
            self._config_lookups_count += 1

    def record_service_discovery(self, lookup_time_ms: float) -> None:
        """Record service discovery query event."""
        with self._lock:
            self._service_discoveries_count += 1

    def record_scaling_event(self, strategy: str) -> None:
        """Record auto-scaling trigger event."""
        with self._lock:
            self._scaling_events_count += 1

    def record_failover_event(self, service_name: str) -> None:
        """Record circuit breaker failover event."""
        with self._lock:
            self._failover_events_count += 1

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Compute infrastructure telemetry operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "started_at": self._started_at,
                "uptime_seconds": round(time.perf_counter() - self._start_time, 2),
                "config_lookups_count": self._config_lookups_count,
                "service_discoveries_count": self._service_discoveries_count,
                "scaling_events_count": self._scaling_events_count,
                "failover_events_count": self._failover_events_count,
            }

    def metrics(self) -> dict[str, Any]:
        """Expose operational metrics."""
        return self.statistics()

    def health(self) -> ComponentHealth:
        """Report component health status."""
        return ComponentHealth(
            component_name=_COMPONENT_NAME,
            status=SystemHealthStatus.HEALTHY,
            details=self.statistics(),
        )
