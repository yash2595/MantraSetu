"""Auto-Scaling Policy & Replicas Trigger Engine v1.0."""

from __future__ import annotations

import logging
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.infrastructure.runtime_models import ScalingPolicy, ScalingStrategy
from app.infrastructure.runtime_telemetry import RuntimeTelemetryEngine

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "ScalingManager"
_COMPONENT_VERSION = "1.0.0"


class ScalingManager:
    """Enterprise thread-safe manager evaluating horizontal/vertical auto-scaling policy triggers."""

    def __init__(self, telemetry: RuntimeTelemetryEngine | None = None) -> None:
        self._telemetry = telemetry or RuntimeTelemetryEngine()
        self._lock = RLock()
        self._scaling_evaluations_count = 0

    def evaluate_scaling(
        self,
        policy: ScalingPolicy,
        current_cpu_percent: float,
    ) -> tuple[bool, int]:
        """Evaluate if auto-scaling action should trigger (returns (should_scale, target_replicas))."""
        with self._lock:
            self._scaling_evaluations_count += 1
            if current_cpu_percent > policy.target_cpu_percent:
                self._telemetry.record_scaling_event(str(policy.strategy))
                target = min(policy.max_replicas, policy.min_replicas + 2)
                logger.info("ScalingManager triggered scale-up to %d replicas (CPU: %.1f%%)", target, current_cpu_percent)
                return (True, target)
            return (False, policy.min_replicas)

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose scaling manager operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "scaling_evaluations_count": self._scaling_evaluations_count,
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
