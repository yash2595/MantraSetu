"""Goal Decomposition & DAG Task Dependency Planner v1.0."""

from __future__ import annotations

import logging
import time
from threading import RLock
from typing import Any

from app.core.models import ComponentHealth, SystemHealthStatus
from app.agents.agent_models import AgentExecutionPlan, AgentTask, TaskPriority, TaskStatus

logger = logging.getLogger(__name__)

_COMPONENT_NAME = "TaskPlanner"
_COMPONENT_VERSION = "1.0.0"


class TaskPlanner:
    """Enterprise thread-safe task planner decomposing user goals into executable AgentTask DAG plans (<3ms target)."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._plans_created_count = 0

    def decompose_goal(self, goal: str) -> list[AgentTask]:
        """Decompose a high-level user goal into atomic sub-tasks (<3ms target)."""
        goal_clean = goal.lower()
        tasks: list[AgentTask] = []

        if "book" in goal_clean or "puja" in goal_clean:
            t1 = AgentTask(
                title="Search Puja Catalog",
                description="Search catalog for requested Puja service details.",
                priority=TaskPriority.HIGH,
                payload={"goal_type": "PUJA_SEARCH"},
            )
            t2 = AgentTask(
                title="Match Pandit",
                description="Find available certified Pandits for booking date.",
                priority=TaskPriority.HIGH,
                dependencies=[t1.task_id],
                payload={"goal_type": "PANDIT_MATCHING"},
            )
            tasks.extend([t1, t2])
        elif "kundali" in goal_clean or "horoscope" in goal_clean:
            t1 = AgentTask(
                title="Calculate Kundali Chart",
                description="Compute Vedic planetary positions for birth details.",
                priority=TaskPriority.MEDIUM,
                payload={"goal_type": "KUNDALI_CALC"},
            )
            tasks.append(t1)
        else:
            t1 = AgentTask(
                title="General Assistance Query",
                description="Process general inquiry user request.",
                priority=TaskPriority.LOW,
                payload={"goal_type": "GENERAL_INQUIRY"},
            )
            tasks.append(t1)

        return tasks

    def create_execution_plan(self, goal: str, context: dict[str, Any] | None = None) -> AgentExecutionPlan:
        """Create a full AgentExecutionPlan containing DAG task dependencies (<3ms target)."""
        start_ts = time.perf_counter()
        with self._lock:
            self._plans_created_count += 1
            context = context or {}

            tasks = self.decompose_goal(goal)
            dep_graph = {t.task_id: list(t.dependencies) for t in tasks}

            plan = AgentExecutionPlan(
                goal=goal,
                tasks=tasks,
                is_parallel=len(tasks) > 1 and len(tasks[0].dependencies) == 0,
                dependency_graph=dep_graph,
            )

            duration_ms = (time.perf_counter() - start_ts) * 1000
            logger.debug("TaskPlanner created plan for goal '%s' with %d tasks in %.2fms", goal[:30], len(tasks), duration_ms)
            return plan

    # Operational Diagnostics
    def statistics(self) -> dict[str, Any]:
        """Expose task planner operational statistics."""
        with self._lock:
            return {
                "component_name": _COMPONENT_NAME,
                "component_version": _COMPONENT_VERSION,
                "plans_created_count": self._plans_created_count,
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
