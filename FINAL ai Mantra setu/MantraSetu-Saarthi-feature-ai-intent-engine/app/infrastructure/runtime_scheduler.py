"""Infrastructure Background Task Scheduler v1.0."""

from __future__ import annotations

import logging
import time
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "RuntimeScheduler"
_COMPONENT_VERSION = "1.0.0"


class RuntimeScheduler:
    """Enterprise thread-safe infrastructure scheduler managing background maintenance and periodic tasks (<3ms target)."""

    def __init__(self) -> None:
        self._scheduled_tasks: dict[str, float] = {}  # task_name -> interval
        self._lock = RLock()
        self._tasks_scheduled_count = 0

    def schedule_task(self, task_name: str, interval_seconds: float) -> bool:
        """Schedule a background maintenance task (<3ms target)."""
        start_ts = time.perf_counter()
        with self._lock:
            self._tasks_scheduled_count += 1
            self._scheduled_tasks[task_name] = interval_seconds
            duration_ms = (time.perf_counter() - start_ts) * 1000
            logger.debug("RuntimeScheduler scheduled task '%s' (every %.1fs) in %.2fms", task_name, interval_seconds, duration_ms)
            return True

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose runtime scheduler operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "scheduled_tasks_count": len(self._scheduled_tasks),
                "tasks_scheduled_count": self._tasks_scheduled_count,
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
