"""Dedicated Telemetry Aggregator Engine for AI Memory Framework v1.0."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "MemoryTelemetryEngine"
_COMPONENT_VERSION = "1.0.0"


class MemoryTelemetryEngine:
    """Enterprise thread-safe telemetry aggregator tracking memory growth, retrieval latencies, recall hits, and purge events."""

    def __init__(self) -> None:
        self._started_at = datetime.now(timezone.utc).isoformat()
        self._start_time = time.perf_counter()
        self._lock = RLock()

        # Telemetry metrics
        self._store_latencies: list[float] = []
        self._retrieval_latencies: list[float] = []
        self._total_stores = 0
        self._total_recalls = 0
        self._total_recall_hits = 0
        self._total_purged_items = 0

    def record_store_operation(self, execution_time_ms: float) -> None:
        """Record a memory store operation latency."""
        with self._lock:
            self._total_stores += 1
            self._store_latencies.append(execution_time_ms)
            if len(self._store_latencies) > 1000:
                self._store_latencies.pop(0)

    def record_retrieval_operation(self, execution_time_ms: float, hits_count: int) -> None:
        """Record a memory retrieval operation latency and recall hits count."""
        with self._lock:
            self._total_recalls += 1
            self._total_recall_hits += hits_count
            self._retrieval_latencies.append(execution_time_ms)
            if len(self._retrieval_latencies) > 1000:
                self._retrieval_latencies.pop(0)

    def record_forget_operation(self, purged_count: int) -> None:
        """Record a memory purge/forget operation count."""
        with self._lock:
            self._total_purged_items += purged_count

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Compute telemetry operational statistics."""
        with self._lock:
            avg_store_l = round(sum(self._store_latencies) / len(self._store_latencies), 2) if self._store_latencies else 0.0
            avg_ret_l = round(sum(self._retrieval_latencies) / len(self._retrieval_latencies), 2) if self._retrieval_latencies else 0.0
            hit_rate = round(self._total_recall_hits / self._total_recalls, 4) if self._total_recalls > 0 else 1.0

            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "started_at": self._started_at,
                "uptime_seconds": round(time.perf_counter() - self._start_time, 2),
                "total_stores": self._total_stores,
                "total_recalls": self._total_recalls,
                "total_recall_hits": self._total_recall_hits,
                "recall_hit_rate": hit_rate,
                "average_store_latency_ms": avg_store_l,
                "average_retrieval_latency_ms": avg_ret_l,
                "total_purged_items": self._total_purged_items,
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
