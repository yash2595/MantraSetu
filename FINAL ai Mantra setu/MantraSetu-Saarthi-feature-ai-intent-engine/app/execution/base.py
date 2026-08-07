"""Abstract base class and error types for the Execution Engine.

Defines the public interface that all concrete Execution Engine
implementations must satisfy. Consumers depend only on this contract —
never on concrete classes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.execution.models import ExecutionResult
from app.services.workflow.models import WorkflowPlan


class ExecutionEngineError(Exception):
    """Raised when the Execution Engine receives an invalid workflow plan.

    This exception is raised only on malformed input (e.g., None).
    A failed execution returns an ExecutionResult with status=FAILED.
    """


class ExecutionEngine(ABC):
    """Abstract interface for all Execution Engine implementations.

    Responsibility:
        Receive a ``WorkflowPlan`` and coordinate its execution across
        downstream services. Returns an ``ExecutionResult``.
        It does not implement business logic, browser automation, or
        direct LLM calls.

    Contract:
        - Must be async.
        - Must never return ``None``.
        - Must never modify the incoming ``WorkflowPlan``.
        - Raises ``ExecutionEngineError`` only on invalid input.

    Future integrations (Parallel execution, Retry policy, Rollback,
    Compensation, Timeout handling, BrowserService, Playwright,
    Streaming execution, Progress events, Cancellation) can be wired
    into concrete subclasses without changing this interface.
    """

    @abstractmethod
    async def execute(self, workflow: WorkflowPlan) -> ExecutionResult:
        """Execute the given workflow plan.

        Args:
            workflow: ``WorkflowPlan`` produced by the Workflow Planner.

        Returns:
            ExecutionResult: Immutable execution result. Never ``None``.

        Raises:
            ExecutionEngineError: Only when ``workflow`` is invalid.
        """
        ...
