"""Concrete Execution Engine implementation.

DefaultExecutionEngine is a placeholder that satisfies the ExecutionEngine
interface. It enables the full pipeline to be wired up and tested before
the real execution logic (parallel execution, retries, service dispatch)
is implemented.

Placeholder behaviour:
    - Always returns ExecutionResult(executed=False, status=NOT_EXECUTED,
      message="", confidence=0.0, metadata=None).
"""

from __future__ import annotations

import logging
import time

from app.execution.base import ExecutionEngine, ExecutionEngineError
from app.execution.models import ExecutionResult, ExecutionStatus
from app.services.workflow.models import WorkflowPlan

logger = logging.getLogger(__name__)


class DefaultExecutionEngine(ExecutionEngine):
    """Placeholder Execution Engine.

    Always returns a 'not executed' result without performing any real execution.
    Replace this with a concrete engine (e.g. ParallelExecutionEngine,
    ResilientExecutionEngine) inside the ServiceContainer.
    """

    async def execute(self, workflow: WorkflowPlan) -> ExecutionResult:
        """Return a placeholder 'not executed' result.

        Args:
            workflow: ``WorkflowPlan`` to execute.

        Returns:
            ExecutionResult: Always ``executed=False`` in this placeholder.
            Never ``None``.

        Raises:
            ExecutionEngineError: If ``workflow`` is invalid.
        """
        if not isinstance(workflow, WorkflowPlan):
            raise ExecutionEngineError(
                "workflow must be a valid WorkflowPlan instance."
            )

        logger.info(
            "Execution started | workflow_type=%s steps=%d",
            workflow.workflow_type.value,
            len(workflow.steps),
        )

        t_start = time.monotonic()

        # Placeholder — no execution performed
        result = ExecutionResult(
            executed=False,
            status=ExecutionStatus.NOT_EXECUTED,
            message="",
            confidence=0.0,
            metadata=None,
        )

        elapsed_ms = (time.monotonic() - t_start) * 1000

        logger.info(
            "Execution completed | executed=%s status=%s processing_time_ms=%.2f",
            result.executed,
            result.status.value,
            elapsed_ms,
        )

        return result
