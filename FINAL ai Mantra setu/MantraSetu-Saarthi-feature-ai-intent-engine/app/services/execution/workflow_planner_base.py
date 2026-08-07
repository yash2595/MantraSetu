"""Abstract base class and error types for the Workflow Planner."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.services.browser_intelligence.task_context_models import TaskContext
from app.services.execution.execution_plan_models import ExecutionPlan


class PlannerError(Exception):
    """Raised when the Workflow Planner encounters an invalid intent or operation."""
    pass


class WorkflowPlanner(ABC):
    """Abstract interface for a Workflow Planner."""

    @abstractmethod
    async def plan(self, intent: str, task_context: TaskContext | None = None) -> ExecutionPlan:
        """Convert a user intent into an ordered ExecutionPlan.

        Args:
            intent: The driving user intent string.
            task_context: Optional TaskContext for intelligence-driven optimization.

        Returns:
            ExecutionPlan: The resulting execution plan.

        Raises:
            PlannerError: On validation failures (e.g., empty intent).
        """
        ...
