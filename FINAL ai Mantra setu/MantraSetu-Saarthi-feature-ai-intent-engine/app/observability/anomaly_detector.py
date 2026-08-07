"""Operational Anomaly Detection & Performance Deviation Engine v1.0."""

from __future__ import annotations

import logging
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "OperationalAnomalyDetector"
_COMPONENT_VERSION = "1.0.0"


class OperationalAnomalyDetector:
    """Enterprise thread-safe engine analyzing performance deviations and error spikes."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._evaluations_count = 0

    def detect_anomalies(
        self,
        latency_samples: list[float],
        error_rate: float,
        latency_threshold_ms: float = 50.0,
        error_threshold_rate: float = 0.05,
    ) -> list[str]:
        """Detect operational performance anomalies in latency or error rates."""
        with self._lock:
            self._evaluations_count += 1
            anomalies = []

            if latency_samples:
                avg_l = sum(latency_samples) / len(latency_samples)
                if avg_l > latency_threshold_ms:
                    anomalies.append(f"High average latency detected: {avg_l:.2f}ms (threshold: {latency_threshold_ms}ms)")

            if error_rate > error_threshold_rate:
                anomalies.append(f"High error rate detected: {error_rate*100:.1f}% (threshold: {error_threshold_rate*100:.1f}%)")

            if anomalies:
                logger.warning("OperationalAnomalyDetector found %d anomalies", len(anomalies))
            return anomalies

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose anomaly detector operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "evaluations_count": self._evaluations_count,
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
