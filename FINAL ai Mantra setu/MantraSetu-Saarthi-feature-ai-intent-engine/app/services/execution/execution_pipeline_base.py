"""Abstract base class and error types for the Execution Pipeline abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.services.execution.execution_runner_models import ExecutionResult


class ExecutionPipelineError(Exception):
    """Raised when the Execution Pipeline encounters an invalid operation or input."""
    pass


class ExecutionPipeline(ABC):
    """Abstract interface for the lightweight orchestration service."""

    @abstractmethod
    async def execute(self, intent: str) -> ExecutionResult:
        """Execute a user intent by orchestrating planning and running.

        Args:
            intent: The driving user intent string.

        Returns:
            ExecutionResult: The final outcome of the execution.

        Raises:
            ExecutionPipelineError: On validation failures (e.g., empty intent).
        """
        ...
