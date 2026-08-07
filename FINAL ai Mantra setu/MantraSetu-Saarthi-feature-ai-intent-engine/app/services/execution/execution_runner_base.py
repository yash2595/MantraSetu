"""Abstract base class and error types for the Execution Runner abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.services.execution.execution_plan_models import ExecutionPlan
from app.services.execution.execution_runner_models import ExecutionResult


class ExecutionRunnerError(Exception):
    """Raised when the Execution Runner encounters an invalid operation or input."""
    pass


class ExecutionRunner(ABC):
    """Abstract interface for executing an ExecutionPlan."""

    @abstractmethod
    async def run(self, plan: ExecutionPlan) -> ExecutionResult:
        """Run an execution plan step by step.

        Args:
            plan: The execution plan to run.

        Returns:
            ExecutionResult: The outcome of the execution.
            
        Raises:
            ExecutionRunnerError: On validation failures (e.g., plan is None).
        """
        ...
