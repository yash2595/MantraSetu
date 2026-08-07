"""Circuit Breaker & Runtime Failover Recovery Manager v1.0."""

from __future__ import annotations

import logging
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.infrastructure.runtime_models import ServiceEndpoint, ServiceState
from app.infrastructure.service_registry import ServiceRegistry
from app.infrastructure.runtime_telemetry import RuntimeTelemetryEngine

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "FailoverManager"
_COMPONENT_VERSION = "1.0.0"


class FailoverManager:
    """Enterprise thread-safe failover manager isolating failing endpoints and routing traffic to healthy backups."""

    def __init__(
        self,
        registry: ServiceRegistry | None = None,
        telemetry: RuntimeTelemetryEngine | None = None,
    ) -> None:
        self._registry = registry or ServiceRegistry()
        self._telemetry = telemetry or RuntimeTelemetryEngine()
        self._lock = RLock()
        self._failover_events_count = 0

    def handle_service_failure(self, endpoint_id: str) -> ServiceEndpoint | None:
        """Handle endpoint failure by setting state to UNHEALTHY and returning backup endpoint."""
        with self._lock:
            self._failover_events_count += 1
            ep = self._registry.get_service_endpoint(endpoint_id)
            if not ep:
                return None

            ep.state = ServiceState.UNHEALTHY
            self._telemetry.record_failover_event(ep.service_name)
            logger.warning("FailoverManager marked endpoint '%s' as UNHEALTHY", endpoint_id)

            # Discover backup healthy endpoint
            backups = [e for e in self._registry.list_endpoints_by_name(ep.service_name) if e.state == ServiceState.HEALTHY]
            return backups[0] if backups else None

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose failover manager operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "failover_events_count": self._failover_events_count,
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
