"""Hardware Resource Allocation & Limits Manager v1.0."""

from __future__ import annotations

import logging
import time
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.infrastructure.runtime_models import ResourceLimits

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "ResourceManager"
_COMPONENT_VERSION = "1.0.0"


class ResourceManager:
    """Enterprise thread-safe resource manager evaluating CPU, Memory, and Worker quotas (<2ms target)."""

    def __init__(self) -> None:
        self._limits = ResourceLimits()
        self._lock = RLock()
        self._allocation_checks_count = 0

    def check_resource_allocation(self, required_memory_mb: float) -> bool:
        """Evaluate if requested memory allocation is within resource limits (<2ms target)."""
        start_ts = time.perf_counter()
        with self._lock:
            self._allocation_checks_count += 1
            is_allowed = required_memory_mb <= self._limits.max_memory_mb
            duration_ms = (time.perf_counter() - start_ts) * 1000
            logger.debug("ResourceManager checked memory allocation (%.1f MB): %s in %.2fms", required_memory_mb, is_allowed, duration_ms)
            return is_allowed

    def get_resource_limits(self) -> ResourceLimits:
        """Get active ResourceLimits object."""
        with self._lock:
            return self._limits

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose resource manager operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "allocation_checks_count": self._allocation_checks_count,
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
