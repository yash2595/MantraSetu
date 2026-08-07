"""Multi-Dimensional Metrics Collection & Aggregation Registry v1.0."""

from __future__ import annotations

import logging
import time
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.observability.observability_models import MetricRecord, MetricType
from app.observability.observability_telemetry import ObservabilityTelemetryEngine

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "MetricsManager"
_COMPONENT_VERSION = "1.0.0"


class MetricsManager:
    """Enterprise thread-safe metrics registry collecting multi-dimensional Counter, Gauge, Histogram, and Summary metrics (<1ms target)."""

    def __init__(self, telemetry: ObservabilityTelemetryEngine | None = None) -> None:
        self._telemetry = telemetry or ObservabilityTelemetryEngine()
        self._metrics_by_name: dict[str, list[MetricRecord]] = {}
        self._lock = RLock()
        self._total_records_count = 0

    def record_metric(
        self,
        name: str,
        value: float,
        metric_type: MetricType = MetricType.COUNTER,
        labels: dict[str, str] | None = None,
    ) -> MetricRecord:
        """Record a multi-dimensional metric sample (<1ms target)."""
        start_ts = time.perf_counter()
        with self._lock:
            self._total_records_count += 1
            labels = labels or {}

            rec = MetricRecord(
                name=name,
                metric_type=metric_type,
                value=value,
                labels=dict(labels),
            )
            if name not in self._metrics_by_name:
                self._metrics_by_name[name] = []
            self._metrics_by_name[name].append(rec)

            if len(self._metrics_by_name[name]) > 1000:
                self._metrics_by_name[name].pop(0)

            self._telemetry.record_metric_collected()
            duration_ms = (time.perf_counter() - start_ts) * 1000
            logger.debug("MetricsManager recorded metric '%s' = %.2f in %.2fms", name, value, duration_ms)
            return rec

    def get_metric(self, name: str) -> list[MetricRecord]:
        """Retrieve defensive copy of metric records for name."""
        with self._lock:
            return list(self._metrics_by_name.get(name, []))

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose metrics manager operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "unique_metrics_count": len(self._metrics_by_name),
                "total_records_count": self._total_records_count,
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
