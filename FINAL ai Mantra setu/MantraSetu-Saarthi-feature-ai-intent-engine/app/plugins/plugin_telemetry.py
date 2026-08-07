"""Dedicated Telemetry Aggregator Engine for Plugin Ecosystem v1.0."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "PluginTelemetryEngine"
_COMPONENT_VERSION = "1.0.0"


class PluginTelemetryEngine:
    """Enterprise thread-safe telemetry aggregator tracking plugin load times, execution latencies, permission checks, and cache hits."""

    def __init__(self) -> None:
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()
        self._lock = RLock()

        # Telemetry metrics
        self._plugin_load_latencies: dict[str, list[float]] = {}
        self._plugin_execution_latencies: dict[str, list[float]] = {}
        self._success_counts: dict[str, int] = {}
        self._failure_counts: dict[str, int] = {}
        self._cache_hits_count = 0
        self._permission_denials_count = 0

    def record_plugin_loaded(self, plugin_id: str, load_time_ms: float) -> None:
        """Record a plugin loading latency."""
        with self._lock:
            if plugin_id not in self._plugin_load_latencies:
                self._plugin_load_latencies[plugin_id] = []
            self._plugin_load_latencies[plugin_id].append(load_time_ms)

    def record_plugin_executed(self, plugin_id: str, execution_time_ms: float, is_success: bool) -> None:
        """Record a plugin task execution outcome and latency."""
        with self._lock:
            if plugin_id not in self._plugin_execution_latencies:
                self._plugin_execution_latencies[plugin_id] = []
                self._success_counts[plugin_id] = 0
                self._failure_counts[plugin_id] = 0

            self._plugin_execution_latencies[plugin_id].append(execution_time_ms)
            if len(self._plugin_execution_latencies[plugin_id]) > 1000:
                self._plugin_execution_latencies[plugin_id].pop(0)

            if is_success:
                self._success_counts[plugin_id] += 1
            else:
                self._failure_counts[plugin_id] += 1

    def record_cache_hit(self) -> None:
        """Record execution cache hit event."""
        with self._lock:
            self._cache_hits_count += 1

    def record_permission_denial(self) -> None:
        """Record permission validation denial event."""
        with self._lock:
            self._permission_denials_count += 1

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Compute plugin telemetry operational statistics."""
        with self._lock:
            plugin_stats = {}
            for p_id, l_list in self._plugin_execution_latencies.items():
                succ = self._success_counts.get(p_id, 0)
                fail = self._failure_counts.get(p_id, 0)
                tot = succ + fail
                avg_l = (sum(l_list) / len(l_list)) if l_list else 0.0
                plugin_stats[p_id] = {
                    "total_executions": tot,
                    "success_count": succ,
                    "failure_count": fail,
                    "average_latency_ms": round(avg_l, 2),
                }

            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "started_at": self._started_at,
                "uptime_seconds": round(time.perf_counter() - self._start_time, 2),
                "cache_hits_count": self._cache_hits_count,
                "permission_denials_count": self._permission_denials_count,
                "plugin_statistics": plugin_stats,
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
