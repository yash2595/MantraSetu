"""Central Infrastructure Service Instance Registry v1.0."""

from __future__ import annotations

import logging
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.infrastructure.runtime_models import ServiceEndpoint, ServiceState

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "ServiceRegistry"
_COMPONENT_VERSION = "1.0.0"


class ServiceRegistry:
    """Enterprise thread-safe registry tracking active service endpoints and health states."""

    def __init__(self) -> None:
        self._endpoints: dict[str, ServiceEndpoint] = {}
        self._lock = RLock()
        self._registrations_count = 0
        self._register_default_services()

    def _register_default_services(self) -> None:
        """Register default core system endpoints."""
        ep1 = ServiceEndpoint(
            endpoint_id="ep_api_01",
            service_name="api_gateway",
            host="127.0.0.1",
            port=8000,
            state=ServiceState.HEALTHY,
        )
        self.register_service(ep1)

    def register_service(self, endpoint: ServiceEndpoint) -> None:
        """Register or update a ServiceEndpoint."""
        with self._lock:
            self._registrations_count += 1
            self._endpoints[endpoint.endpoint_id] = endpoint
            logger.info("ServiceRegistry registered service '%s' [%s:%d]", endpoint.service_name, endpoint.host, endpoint.port)

    def deregister_service(self, endpoint_id: str) -> bool:
        """Deregister a ServiceEndpoint."""
        with self._lock:
            if endpoint_id in self._endpoints:
                del self._endpoints[endpoint_id]
                logger.info("ServiceRegistry deregistered service endpoint '%s'", endpoint_id)
                return True
            return False

    def get_service_endpoint(self, endpoint_id: str) -> ServiceEndpoint | None:
        """Retrieve ServiceEndpoint by endpoint_id."""
        with self._lock:
            return self._endpoints.get(endpoint_id)

    def list_endpoints_by_name(self, service_name: str) -> list[ServiceEndpoint]:
        """List active endpoints matching target service_name."""
        with self._lock:
            return [e for e in self._endpoints.values() if e.service_name == service_name]

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose service registry operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "registered_endpoints_count": len(self._endpoints),
                "registrations_count": self._registrations_count,
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
