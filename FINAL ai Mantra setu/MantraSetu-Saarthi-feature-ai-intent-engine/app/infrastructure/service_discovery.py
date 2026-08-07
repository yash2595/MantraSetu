"""Provider-Independent Dynamic Service Discovery Engine v1.0."""

from __future__ import annotations

import logging
import time
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.infrastructure.runtime_models import ServiceEndpoint, ServiceState
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.infrastructure.service_registry import ServiceRegistry
from app.infrastructure.service_registry import ServiceRegistry
from app.infrastructure.runtime_telemetry import RuntimeTelemetryEngine

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "ServiceDiscovery"
_COMPONENT_VERSION = "1.0.0"


class ServiceDiscovery:
    """Enterprise thread-safe engine discovering healthy service endpoints (<2ms target)."""

    def __init__(
        self,
        registry: ServiceRegistry | None = None,
        telemetry: RuntimeTelemetryEngine | None = None,
    ) -> None:
        self._registry = registry or ServiceRegistry()
        self._telemetry = telemetry or RuntimeTelemetryEngine()
        self._lock = RLock()
        self._discoveries_count = 0

    def discover_service(self, service_name: str) -> list[ServiceEndpoint]:
        """Discover active healthy service endpoints for service_name (<2ms target)."""
        start_ts = time.perf_counter()
        with self._lock:
            self._discoveries_count += 1
            candidates = self._registry.list_endpoints_by_name(service_name)
            healthy = [e for e in candidates if e.state == ServiceState.HEALTHY]

            duration_ms = (time.perf_counter() - start_ts) * 1000
            self._telemetry.record_service_discovery(duration_ms)
            logger.debug("ServiceDiscovery found %d healthy endpoints for '%s' in %.2fms", len(healthy), service_name, duration_ms)
            return healthy

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose service discovery operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "discoveries_count": self._discoveries_count,
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
