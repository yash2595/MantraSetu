"""Infrastructure Request Load Balancer & Traffic Router v1.0."""

from __future__ import annotations

import logging
import random
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.infrastructure.runtime_models import LoadBalancingAlgorithm, ServiceEndpoint

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "LoadBalancer"
_COMPONENT_VERSION = "1.0.0"


class LoadBalancer:
    """Enterprise thread-safe load balancer distributing requests using Round-Robin, Least-Connections, or Random routing."""

    def __init__(self) -> None:
        self._rr_indices: dict[str, int] = {}
        self._lock = RLock()
        self._routings_count = 0

    def select_endpoint(
        self,
        endpoints: list[ServiceEndpoint],
        algorithm: LoadBalancingAlgorithm = LoadBalancingAlgorithm.ROUND_ROBIN,
    ) -> ServiceEndpoint | None:
        """Select an optimal healthy endpoint from candidates using routing algorithm."""
        with self._lock:
            self._routings_count += 1
            if not endpoints:
                return None

            if algorithm == LoadBalancingAlgorithm.RANDOM:
                return random.choice(endpoints)
            elif algorithm == LoadBalancingAlgorithm.LEAST_CONNECTIONS:
                return min(endpoints, key=lambda e: e.active_connections)
            else:  # ROUND_ROBIN
                svc_key = endpoints[0].service_name
                idx = self._rr_indices.get(svc_key, 0)
                selected = endpoints[idx % len(endpoints)]
                self._rr_indices[svc_key] = (idx + 1) % len(endpoints)
                return selected

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose load balancer operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "routings_count": self._routings_count,
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
