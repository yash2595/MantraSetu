"""Enterprise Tool Scheduler for Priority Queuing & Execution Ordering v1.1."""

from __future__ import annotations

import logging
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.tools.tool_models import ScheduledTask, ToolInvocation

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "ToolScheduler"
_COMPONENT_VERSION = "1.1.0"


class ToolScheduler:
    """Enterprise thread-safe scheduler managing priority queuing, dependency ordering, and tasks scheduling without executing tools."""

    def __init__(self) -> None:
        self._scheduled_tasks: dict[str, ScheduledTask] = {}
        self._cancellation_queue: set[str] = set()
        self._lock = RLock()
        self._scheduled_count = 0

    def schedule(self, invocation: ToolInvocation, priority: int = 5, delay_seconds: float = 0.0) -> ScheduledTask:
        """Schedule a tool invocation task in the priority queue."""
        with self._lock:
            self._scheduled_count += 1
            task = ScheduledTask(
                invocation=invocation,
                priority=priority,
                delay_seconds=delay_seconds,
            )
            self._scheduled_tasks[task.task_id] = task
            logger.debug("Scheduled task '%s' for tool '%s' [Priority: %d]", task.task_id, invocation.tool_name, priority)
            return task

    def schedule_parallel(self, invocations: list[ToolInvocation]) -> list[ScheduledTask]:
        """Schedule multiple tool invocations for parallel execution."""
        with self._lock:
            return [self.schedule(inv, priority=5) for inv in invocations]

    def schedule_sequential(self, invocations: list[ToolInvocation]) -> list[ScheduledTask]:
        """Schedule multiple tool invocations for sequential execution."""
        with self._lock:
            tasks = []
            for idx, inv in enumerate(invocations):
                tasks.append(self.schedule(inv, priority=10 - idx))
            return tasks

    def cancel_schedule(self, task_id: str) -> bool:
        """Cancel a scheduled task."""
        with self._lock:
            if task_id in self._scheduled_tasks:
                self._scheduled_tasks[task_id].is_cancelled = True
                self._cancellation_queue.add(task_id)
                logger.info("Cancelled scheduled task '%s'", task_id)
                return True
            return False

    def reschedule(self, task_id: str, delay_seconds: float) -> ScheduledTask | None:
        """Reschedule a task with a delay."""
        with self._lock:
            task = self._scheduled_tasks.get(task_id)
            if task and not task.is_cancelled:
                task.delay_seconds = delay_seconds
                return task
            return None

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose scheduler operational statistics."""
        with self._lock:
            active_count = sum(1 for t in self._scheduled_tasks.values() if not t.is_cancelled)
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "total_scheduled_count": self._scheduled_count,
                "active_tasks_count": active_count,
                "cancelled_tasks_count": len(self._cancellation_queue),
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
