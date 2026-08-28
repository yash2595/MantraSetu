"""Infrastructure Liveness, Readiness & Startup Health Aggregator v1.0."""

from __future__ import annotations

import logging
import time
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.infrastructure.runtime_models import RuntimeHealth
from app.infrastructure.service_registry import ServiceRegistry

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "RuntimeHealthAggregator"
_COMPONENT_VERSION = "1.0.0"


class RuntimeHealthAggregator:
    """Enterprise thread-safe aggregator verifying infrastructure liveness and readiness probes (<2ms target)."""

    def __init__(self, registry: ServiceRegistry | None = None) -> None:
        self._registry = registry or ServiceRegistry()
        self._lock = RLock()
        self._health_probes_count = 0

    def get_runtime_health(self) -> RuntimeHealth:
        """Aggregate liveness and readiness probe status (<2ms target)."""
        start_ts = time.perf_counter()
        with self._lock:
            self._health_probes_count += 1
            stats = self._registry.statistics()
            active_count = stats.get("registered_endpoints_count", 0)

            health = RuntimeHealth(
                status="HEALTHY" if active_count > 0 else "DEGRADED",
                liveness=True,
                readiness=active_count > 0,
                active_services_count=active_count,
            )
            duration_ms = (time.perf_counter() - start_ts) * 1000
            logger.debug("RuntimeHealthAggregator probed health in %.2fms", duration_ms)
            return health

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose runtime health aggregator operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "health_probes_count": self._health_probes_count,
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
