"""Default implementation of the Execution Pipeline abstraction."""

from __future__ import annotations

import logging
import time

from app.services.execution.execution_pipeline_base import (
    ExecutionPipeline,
    ExecutionPipelineError,
)
from app.services.execution.execution_runner_base import ExecutionRunner
from app.services.execution.execution_runner_models import ExecutionResult
from app.services.execution.workflow_planner_base import WorkflowPlanner

logger = logging.getLogger(__name__)


class DefaultExecutionPipeline(ExecutionPipeline):
    """Lightweight orchestration service connecting Planner and Execution Runner.

    This service performs no business logic, AI reasoning, or browser interactions.
    It simply wires the outputs of the WorkflowPlanner to the inputs of the ExecutionRunner.
    """

    def __init__(self, planner: WorkflowPlanner, runner: ExecutionRunner) -> None:
        """Initialize the pipeline with required dependencies.

        Args:
            planner: The workflow planner dependency.
            runner: The execution runner dependency.
        """
        self._planner = planner
        self._runner = runner

    async def execute(self, intent: str) -> ExecutionResult:
        """Execute the user intent through planning and running phases."""
        if intent is None:
            raise ExecutionPipelineError("Intent cannot be None.")
            
        intent_stripped = intent.strip()
        if not intent_stripped:
            raise ExecutionPipelineError("Intent cannot be empty or whitespace.")

        logger.info("Execution pipeline started")
        start_time = time.monotonic()

        # Phase 1: Planning
        logger.info("Planning started")
        plan = await self._planner.plan(intent_stripped)
        logger.info("Planning completed")

        # Phase 2: Execution
        logger.info("Execution started")
        result = await self._runner.run(plan)
        logger.info("Execution completed")

        elapsed_ms = (time.monotonic() - start_time) * 1000
        logger.info("Total processing time | processing_time_ms=%.2f", elapsed_ms)

        return result
