"""Dedicated Telemetry Aggregator Engine for Voice AI Framework v1.0."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "VoiceTelemetryEngine"
_COMPONENT_VERSION = "1.0.0"


class VoiceTelemetryEngine:
    """Enterprise thread-safe telemetry aggregator tracking voice latencies, interruptions, dropped chunks, and provider usage."""

    def __init__(self) -> None:
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()
        self._lock = RLock()

        # Telemetry metrics
        self._latencies: dict[str, list[float]] = {}
        self._interruption_counts: dict[str, int] = {}
        self._dropped_chunks_counts: dict[str, int] = {}
        self._provider_usage: dict[str, int] = {}
        self._total_chunks_processed = 0

    def record_latency(self, metric_name: str, latency_ms: float) -> None:
        """Record processing latency in milliseconds."""
        with self._lock:
            if metric_name not in self._latencies:
                self._latencies[metric_name] = []
            self._latencies[metric_name].append(latency_ms)
            if len(self._latencies[metric_name]) > 1000:
                self._latencies[metric_name].pop(0)

    def record_interruption(self, session_id: str) -> None:
        """Record a barge-in interruption event."""
        with self._lock:
            self._interruption_counts[session_id] = self._interruption_counts.get(session_id, 0) + 1

    def record_dropped_chunk(self, session_id: str) -> None:
        """Record a dropped audio chunk event due to buffer overflow."""
        with self._lock:
            self._dropped_chunks_counts[session_id] = self._dropped_chunks_counts.get(session_id, 0) + 1

    def record_provider_usage(self, provider_name: str) -> None:
        """Record voice provider usage count."""
        with self._lock:
            self._provider_usage[provider_name] = self._provider_usage.get(provider_name, 0) + 1

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Compute telemetry operational statistics."""
        with self._lock:
            avg_latencies = {
                k: round(sum(v) / len(v), 2) if v else 0.0 for k, v in self._latencies.items()
            }
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "started_at": self._started_at,
                "uptime_seconds": round(time.perf_counter() - self._start_time, 2),
                "average_latencies_ms": avg_latencies,
                "total_interruptions": sum(self._interruption_counts.values()),
                "total_dropped_chunks": sum(self._dropped_chunks_counts.values()),
                "provider_usage": dict(self._provider_usage),
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
