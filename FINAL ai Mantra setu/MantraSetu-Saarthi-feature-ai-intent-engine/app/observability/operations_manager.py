"""Operational Summary & Incident Management Engine v1.0."""

from __future__ import annotations

import logging
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.observability.observability_models import ServiceStatus

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "OperationsManager"
_COMPONENT_VERSION = "1.0.0"


class OperationsManager:
    """Enterprise thread-safe operations manager tracking deployment modes and operational status summaries."""

    def __init__(self) -> None:
        self._status = ServiceStatus.ONLINE
        self._lock = RLock()
        self._mode_toggles_count = 0

    def set_maintenance_mode(self, enabled: bool) -> ServiceStatus:
        """Toggle maintenance mode status."""
        with self._lock:
            self._mode_toggles_count += 1
            self._status = ServiceStatus.MAINTENANCE if enabled else ServiceStatus.ONLINE
            logger.info("OperationsManager set service status to '%s'", self._status)
            return self._status

    def get_operational_summary(self) -> dict[str, Any]:
        """Return operational summary dictionary."""
        with self._lock:
            return {
                "service_status": str(self._status),
                "is_maintenance_mode": self._status == ServiceStatus.MAINTENANCE,
                "mode_toggles_count": self._mode_toggles_count,
            }

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose operations manager operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "service_status": str(self._status),
                "mode_toggles_count": self._mode_toggles_count,
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
